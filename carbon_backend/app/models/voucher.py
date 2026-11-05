from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import VoucherStatus
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.wallet import CreditWalletEntry


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    credits: Mapped[int]
    status: Mapped[VoucherStatus] = mapped_column(
        Enum(VoucherStatus, native_enum=False, length=20, validate_strings=True),
        default=VoucherStatus.pending,
    )
    category: Mapped[str | None] = mapped_column(String)
    rating: Mapped[float] = mapped_column(Float)
    availability: Mapped[str] = mapped_column(String)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime)
    redeemed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    redeemed_by: Mapped[User | None] = relationship(foreign_keys=[redeemed_by_user_id])
    redemptions: Mapped[list[VoucherRedemption]] = relationship(back_populates="voucher", cascade="all, delete-orphan")
    wallet_entries: Mapped[list[CreditWalletEntry]] = relationship(back_populates="voucher", cascade="all, delete-orphan")


class VoucherRedemption(Base):
    __tablename__ = "voucher_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    voucher_id: Mapped[int] = mapped_column(ForeignKey("vouchers.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    redeemed_at: Mapped[datetime] = mapped_column(DateTime)
    credits: Mapped[int]

    voucher: Mapped[Voucher] = relationship(back_populates="redemptions")
    user: Mapped[User] = relationship(back_populates="redemptions")
