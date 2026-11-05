from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import Role
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.trip import Trip
    from app.models.voucher import VoucherRedemption
    from app.models.wallet import CreditWalletEntry


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), default=Role.user)

    tokens: Mapped[list[AccessToken]] = relationship(back_populates="user", cascade="all, delete-orphan")
    trips: Mapped[list[Trip]] = relationship(back_populates="user", cascade="all, delete-orphan")
    wallet_entries: Mapped[list[CreditWalletEntry]] = relationship(back_populates="user", cascade="all, delete-orphan")
    redemptions: Mapped[list[VoucherRedemption]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AccessToken(Base):
    """Opaque bearer token issued at login. Only its SHA-256 digest is stored."""

    __tablename__ = "access_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship(back_populates="tokens")
