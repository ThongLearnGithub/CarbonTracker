from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.db.session import get_db
from app.models import User
from app.services import auth_service
from routing.service import RoutingEngine

SessionDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

# auto_error=False: we raise our own 401 with a consistent message (HTTPBearer's default is 403 on older FastAPI).
_bearer = HTTPBearer(auto_error=False, description="Access token returned by /auth/login or /auth/firebase")


def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authorization header missing or invalid")
    return credentials.credentials


BearerTokenDep = Annotated[str, Depends(get_bearer_token)]


def get_current_user(db: SessionDep, token: BearerTokenDep) -> User:
    return auth_service.get_user_by_token(db, token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_routing_engine(request: Request) -> RoutingEngine:
    return request.app.state.routing_engine


RoutingEngineDep = Annotated[RoutingEngine, Depends(get_routing_engine)]
