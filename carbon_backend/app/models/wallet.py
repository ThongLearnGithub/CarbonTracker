from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.trip import Trip
    from app.models.user import User
    from app.models.voucher import Voucher


class CreditWalletEntry(Base):
    """Credit ledger: positive delta = earned from a trip, negative = spent on a voucher."""

    __tablename__ = "credit_wallet"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"))
    voucher_id: Mapped[int | None] = mapped_column(ForeignKey("vouchers.id"))
    delta: Mapped[int]
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    note: Mapped[str | None] = mapped_column(String)

    user: Mapped[User] = relationship(back_populates="wallet_entries")
    trip: Mapped[Trip | None] = relationship(back_populates="wallet_entries")
    voucher: Mapped[Voucher | None] = relationship(back_populates="wallet_entries")
