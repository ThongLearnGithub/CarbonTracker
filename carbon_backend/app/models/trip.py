from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.wallet import CreditWalletEntry


class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    mode: Mapped[str] = mapped_column(String, unique=True)
    factor: Mapped[float] = mapped_column(Float)  # kg CO2 per km


class TripEmissionFactor(Base):
    __tablename__ = "trip_emission_factors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    emission_factor_id: Mapped[int] = mapped_column(ForeignKey("emission_factors.id"))


class Trip(Base):
    """One row per user per day; trips logged on the same day are merged into it."""

    __tablename__ = "trips"
    __table_args__ = (Index("ix_trips_user_id_date", "user_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[dt.date] = mapped_column(Date)
    distance_km: Mapped[float] = mapped_column(Float)
    # Comma-separated modes in the order they were logged; `transport_modes` below is the list view.
    transport_modes_csv: Mapped[str] = mapped_column("transport_modes", String)
    credits: Mapped[int]

    user: Mapped[User] = relationship(back_populates="trips")
    wallet_entries: Mapped[list[CreditWalletEntry]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    emission_factors: Mapped[list[EmissionFactor]] = relationship(secondary="trip_emission_factors")

    @property
    def transport_modes(self) -> list[str]:
        if self.emission_factors:
            return [factor.mode for factor in self.emission_factors]
        return self.transport_modes_csv.split(",") if self.transport_modes_csv else []
