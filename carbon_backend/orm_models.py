from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Role(PyEnum):
    user = "user"
    admin = "admin"
    merchant = "merchant"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.user, nullable=False)

    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    vouchers = relationship("Voucher", back_populates="redeemed_by", cascade="all, delete-orphan")
    redemptions = relationship("VoucherRedemption", back_populates="user", cascade="all, delete-orphan")
    credit_wallet = relationship("CreditWallet", back_populates="user", cascade="all, delete-orphan")


class Token(Base):
    __tablename__ = "tokens"

    token = Column(String, primary_key=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="tokens")


class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String, unique=True, nullable=False)
    factor = Column(Float, nullable=False)

    trips = relationship("Trip", secondary="trip_emission_factors", back_populates="emission_factors")


class TripEmissionFactor(Base):
    __tablename__ = "trip_emission_factors"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    emission_factor_id = Column(Integer, ForeignKey("emission_factors.id"), nullable=False)


class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    credits = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    category = Column(String, nullable=True)
    rating = Column(Float, nullable=False)
    availability = Column(String, nullable=False)
    redeemed_at = Column(String, nullable=True)
    redeemed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    redeemed_by = relationship("User", back_populates="vouchers", foreign_keys=[redeemed_by_user_id])
    redemption_records = relationship("VoucherRedemption", back_populates="voucher", cascade="all, delete-orphan")
    credit_wallet_entries = relationship("CreditWallet", back_populates="voucher", cascade="all, delete-orphan")


class VoucherRedemption(Base):
    __tablename__ = "voucher_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    redeemed_at = Column(String, nullable=False)
    credits = Column(Integer, nullable=False)

    voucher = relationship("Voucher", back_populates="redemption_records")
    user = relationship("User", back_populates="redemptions")


class CreditWallet(Base):
    __tablename__ = "credit_wallet"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=True)
    delta = Column(Integer, nullable=False)
    timestamp = Column(String, nullable=False)
    note = Column(String, nullable=True)

    user = relationship("User", back_populates="credit_wallet")
    trip = relationship("Trip", back_populates="credit_wallet_entries")
    voucher = relationship("Voucher", back_populates="credit_wallet_entries")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)
    distance_km = Column(Float, nullable=False)
    transport_modes = Column(String, nullable=False)  # store as comma-separated
    credits = Column(Integer, nullable=False)

    user = relationship("User", back_populates="trips")
    credit_wallet_entries = relationship("CreditWallet", back_populates="trip", cascade="all, delete-orphan")
    emission_factors = relationship("EmissionFactor", secondary="trip_emission_factors", back_populates="trips")
