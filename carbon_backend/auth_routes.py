from typing import Optional
import os
import secrets
import logging

from fastapi import APIRouter, HTTPException, Header, Depends
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_firebase_token
from sqlalchemy.orm import Session

from models import UserBase, UserSignup, UserLogin, LoginResponse, Role, FirebaseLoginRequest
from utils import get_user_by_token
from database import get_db
from orm_models import User as ORMUser, Token as ORMToken

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "carbon-tracker-622b1")

# Sign up endpoint: accept email, fullname and password from User Signup class
@router.post("/signup", response_model=UserBase)
async def signup_user(body: UserSignup, db: Session = Depends(get_db)):

    # Check if the email already exists in DB
    existing = db.query(ORMUser).filter(ORMUser.email.ilike(body.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = ORMUser(
        email=body.email,
        full_name=body.full_name,
        role=Role.user,
        password=body.password,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserBase(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
    )

# Login endpoint
@router.post("/login", response_model=LoginResponse)
async def login(body: UserLogin, db: Session = Depends(get_db)):

    user = db.query(ORMUser).filter(ORMUser.email.ilike(body.email)).first()
    if not user or user.password != body.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_hex(16)
    while db.query(ORMToken).filter(ORMToken.token == token).first() is not None:
        token = secrets.token_hex(16)

    db.add(ORMToken(token=token, user_id=user.id))
    db.commit()

    return LoginResponse(
        access_token=token,
        user=UserBase(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        ),
    )


@router.post("/firebase", response_model=LoginResponse)
def login_with_firebase(body: FirebaseLoginRequest, db: Session = Depends(get_db)):
    try:
        claims = verify_firebase_token(
            body.id_token,
            Request(),
            audience=FIREBASE_PROJECT_ID,
            clock_skew_in_seconds=60,
        )
    except (ValueError, GoogleAuthError) as error:
        error_message = str(error).lower()
        if "expired" in error_message or "expiry" in error_message:
            failure_reason = "expired"
        elif "audience" in error_message:
            failure_reason = "audience_mismatch"
        elif "issuer" in error_message:
            failure_reason = "issuer_mismatch"
        elif "signature" in error_message:
            failure_reason = "invalid_signature"
        elif "early" in error_message or "clock" in error_message:
            failure_reason = "clock_skew"
        else:
            failure_reason = "verification_failed"
        logger.warning(
            "Firebase ID token verification failed (%s: %s) for configured project %s",
            type(error).__name__,
            failure_reason,
            FIREBASE_PROJECT_ID,
        )
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase token")

    email = claims.get("email")
    if not email or not claims.get("sub") or not claims.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail="A verified Firebase email is required to access this account",
        )

    user = db.query(ORMUser).filter(ORMUser.email.ilike(email)).first()
    if user is None:
        full_name = claims.get("name") or email.split("@", 1)[0]
        user = ORMUser(
            email=email,
            full_name=full_name,
            password=secrets.token_urlsafe(48),
            role=Role.user,
        )
        db.add(user)
        db.flush()

    token = secrets.token_hex(32)
    while db.query(ORMToken).filter(ORMToken.token == token).first() is not None:
        token = secrets.token_hex(32)

    db.add(ORMToken(token=token, user_id=user.id))
    db.commit()
    db.refresh(user)

    return LoginResponse(
        access_token=token,
        user=UserBase(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        ),
    )


# Get the info of the user who are logging in
@router.get("/me", response_model=UserBase)
async def get_me(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    
    if not authorization or not authorization.startswith("Bearer "): # Check header if the authorization start with Bearer
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or invalid",
        )

    # Split token out of the header ex: Bearer abc123 --> token = abc123
    token = authorization.split(" ", 1)[1]
    user = get_user_by_token(token, db)  # find user from token

    # Return the info of the user
    return UserBase(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )
