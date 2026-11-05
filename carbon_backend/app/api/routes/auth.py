from fastapi import APIRouter, status
from sqlalchemy.orm import Session

from app.api.deps import BearerTokenDep, CurrentUser, SessionDep, SettingsDep
from app.core.config import Settings
from app.models import User
from app.schemas.user import FirebaseLoginRequest, LoginResponse, UserLogin, UserRead, UserSignup
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _login_response(db: Session, user: User, settings: Settings) -> LoginResponse:
    token, expires_at = auth_service.issue_access_token(db, user, settings)
    return LoginResponse(access_token=token, expires_at=expires_at, user=UserRead.model_validate(user))


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(body: UserSignup, db: SessionDep):
    return auth_service.signup(db, body)


@router.post("/login", response_model=LoginResponse)
def login(body: UserLogin, db: SessionDep, settings: SettingsDep):
    user = auth_service.authenticate(db, body.email, body.password)
    return _login_response(db, user, settings)


# Plain def: token verification makes a blocking HTTPS call to fetch Google's public keys.
@router.post("/firebase", response_model=LoginResponse)
def login_with_firebase(body: FirebaseLoginRequest, db: SessionDep, settings: SettingsDep):
    user = auth_service.get_or_create_firebase_user(db, body.id_token, settings)
    return _login_response(db, user, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(db: SessionDep, token: BearerTokenDep) -> None:
    auth_service.revoke_access_token(db, token)


@router.get("/me", response_model=UserRead)
def get_me(user: CurrentUser):
    return user
