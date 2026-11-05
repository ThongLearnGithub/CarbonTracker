import logging
import secrets
from datetime import UTC, datetime, timedelta

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_firebase_token
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import Role
from app.core.exceptions import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.security import generate_access_token, hash_access_token, hash_password, verify_password
from app.models import AccessToken, User
from app.schemas.user import UserSignup

logger = logging.getLogger(__name__)

# Reuses one HTTP session for Google's public-key downloads.
_google_request = GoogleRequest()


def find_user_by_email(db: Session, email: str) -> User | None:
    # Case-insensitive exact match. (ilike would treat "%" and "_" in user input as wildcards.)
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def signup(db: Session, data: UserSignup) -> User:
    if find_user_by_email(db, data.email) is not None:
        raise ConflictError("Email already registered")

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=Role.user,
    )
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = find_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")
    return user


def _firebase_failure_reason(error: Exception) -> str:
    message = str(error).lower()
    if "expired" in message or "expiry" in message:
        return "expired"
    if "audience" in message:
        return "audience_mismatch"
    if "issuer" in message:
        return "issuer_mismatch"
    if "signature" in message:
        return "invalid_signature"
    if "early" in message or "clock" in message:
        return "clock_skew"
    return "verification_failed"


def get_or_create_firebase_user(db: Session, id_token: str, settings: Settings) -> User:
    try:
        claims = verify_firebase_token(
            id_token,
            _google_request,
            audience=settings.firebase_project_id,
            clock_skew_in_seconds=60,
        )
    except (ValueError, GoogleAuthError) as error:
        logger.warning(
            "Firebase ID token verification failed (%s: %s) for configured project %s",
            type(error).__name__,
            _firebase_failure_reason(error),
            settings.firebase_project_id,
        )
        raise AuthenticationError("Invalid or expired Firebase token") from error

    email = claims.get("email")
    if not email or not claims.get("sub") or not claims.get("email_verified", False):
        raise PermissionDeniedError("A verified Firebase email is required to access this account")

    user = find_user_by_email(db, email)
    if user is None:
        user = User(
            email=email,
            full_name=claims.get("name") or email.split("@", 1)[0],
            # Firebase accounts sign in through Firebase; this random password is never shown or used.
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            role=Role.user,
        )
        db.add(user)
        db.flush()
    return user


def issue_access_token(db: Session, user: User, settings: Settings) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.access_token_ttl_days)
    token = generate_access_token()

    db.execute(delete(AccessToken).where(AccessToken.user_id == user.id, AccessToken.expires_at <= now))
    db.add(AccessToken(token_hash=hash_access_token(token), user_id=user.id, created_at=now, expires_at=expires_at))
    db.commit()
    return token, expires_at


def get_user_by_token(db: Session, token: str) -> User:
    user = db.scalar(
        select(User)
        .join(AccessToken, AccessToken.user_id == User.id)
        .where(AccessToken.token_hash == hash_access_token(token), AccessToken.expires_at > datetime.now(UTC))
    )
    if user is None:
        raise AuthenticationError("Invalid or expired token")
    return user


def revoke_access_token(db: Session, token: str) -> None:
    db.execute(delete(AccessToken).where(AccessToken.token_hash == hash_access_token(token)))
    db.commit()
