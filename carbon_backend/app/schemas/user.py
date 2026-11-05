from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.enums import Role
from app.schemas.common import ORMModel


class UserRead(ORMModel):
    id: int
    email: str
    full_name: str
    role: Role


class UserSignup(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class FirebaseLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserRead
