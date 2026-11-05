"""Load demo data. Run from carbon_backend:

    python -m scripts.seed            # migrate to the latest schema, then add any missing demo rows
    python -m scripts.seed --reset    # DROP every table first (all data is lost), then migrate and seed
"""
import argparse
from datetime import date, datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.core.enums import Role, VoucherStatus
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import CreditWalletEntry, EmissionFactor, Trip, User, Voucher
from app.services.carbon_metrics import DEFAULT_EMISSION_FACTORS

DEMO_PASSWORD = "123"  # demo accounts only

MOCK_USERS = [
    {"email": "khoa@gmail.com", "full_name": "Khoa Mai", "role": Role.user},
    {"email": "duy@gmail.com", "full_name": "Duy Admin", "role": Role.admin},
    {"email": "khanh@gmail.com", "full_name": "Coffee Shop Merchant", "role": Role.merchant},
]

MOCK_VOUCHERS = [
    {"title": "50% Off Coffee", "description": "Apply at partner coffee shops in city center.", "credits": 500, "category": "shopping", "rating": 4.8, "availability": "2 days left"},
    {"title": "Free Bus Ticket", "description": "One-day free ticket for e-bus lines.", "credits": 300, "category": "transport", "rating": 4.8, "availability": "7 days left"},
    {"title": "Plant a Tree", "description": "We plant a tree in your name.", "credits": 200, "category": "green", "rating": 5.0, "availability": "Always available"},
    {"title": "Ocean Cleanup Donation", "description": "$10 donation to clean initiatives", "credits": 100, "category": "charity", "rating": 4.9, "availability": "7 days left"},
]

# (date, distance_km, modes, credits) for khoa@gmail.com
MOCK_TRIPS = [
    (date(2025, 12, 25), 15, ["Walking"], 300),
    (date(2025, 12, 24), 5, ["Walking"], 300),
    (date(2025, 12, 23), 10, ["E-Bus", "Walking"], 250),
    (date(2025, 12, 12), 15, ["E-Bus", "Walking"], 160),
    (date(2025, 12, 11), 8, ["Bicycle"], 160),
    (date(2025, 11, 20), 17, ["Walking", "Bus", "E-Bus"], 120),
    (date(2025, 10, 22), 20, ["E-Bus", "E-Car"], 195),
    (date(2025, 9, 14), 6, ["Bicycle"], 145),
    (date(2025, 8, 14), 6, ["Bicycle"], 245),
]


def reset_database() -> None:
    with engine.begin() as connection:
        # Tables that only exist in older schemas (they reference users, so go first) and Alembic's bookkeeping.
        connection.execute(text("DROP TABLE IF EXISTS tokens, alembic_version"))
    Base.metadata.drop_all(bind=engine)


def migrate() -> None:
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


def seed(db: Session) -> None:
    for mode, factor in DEFAULT_EMISSION_FACTORS.items():
        if db.scalar(select(EmissionFactor).where(EmissionFactor.mode == mode)) is None:
            db.add(EmissionFactor(mode=mode, factor=factor))

    for data in MOCK_USERS:
        if db.scalar(select(User).where(func.lower(User.email) == data["email"])) is None:
            db.add(User(**data, hashed_password=hash_password(DEMO_PASSWORD)))

    for data in MOCK_VOUCHERS:
        if db.scalar(select(Voucher).where(Voucher.title == data["title"])) is None:
            db.add(Voucher(**data, status=VoucherStatus.pending))
    db.flush()

    # IDs are left to the database, so its sequences stay in step and later inserts don't collide.
    factors = {factor.mode: factor for factor in db.scalars(select(EmissionFactor))}
    khoa = db.scalar(select(User).where(User.email == "khoa@gmail.com"))
    for trip_date, distance_km, modes, credits in MOCK_TRIPS:
        if db.scalar(select(Trip).where(Trip.user_id == khoa.id, Trip.date == trip_date)) is not None:
            continue
        trip = Trip(
            user_id=khoa.id,
            date=trip_date,
            distance_km=distance_km,
            transport_modes_csv=",".join(modes),
            credits=credits,
            emission_factors=[factors[mode] for mode in modes if mode in factors],
        )
        db.add(trip)
        db.flush()
        db.add(
            CreditWalletEntry(
                user_id=khoa.id,
                trip_id=trip.id,
                delta=credits,
                timestamp=datetime.combine(trip_date, datetime.min.time()),
                note="Trip earned",
            )
        )
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="drop all tables before seeding (destroys data)")
    args = parser.parse_args()

    if args.reset:
        reset_database()
    migrate()
    with SessionLocal() as db:
        seed(db)
    print(f"Demo data loaded. Demo accounts use the password {DEMO_PASSWORD!r}.")


if __name__ == "__main__":
    main()
