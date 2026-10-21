from database import engine, Base, SessionLocal
from carbon_metrics import DEFAULT_EMISSION_FACTORS
from orm_models import User, Voucher, Trip, EmissionFactor, CreditWallet
from models import Role, UserInDB, Voucher as VoucherSchema, Trip as TripSchema

EMISSION_FACTORS = DEFAULT_EMISSION_FACTORS

MOCK_USERS = [
    UserInDB(id=1, email="khoa@gmail.com", full_name="Khoa Mai", role=Role.user, password="123"),
    UserInDB(id=2, email="duy@gmail.com", full_name="Duy Admin", role=Role.admin, password="123"),
    UserInDB(id=3, email="khanh@gmail.com", full_name="Coffee Shop Merchant", role=Role.merchant, password="123"),
]

MOCK_VOUCHERS = [
    VoucherSchema(id=1, title="50% Off Coffee", description="Apply at partner coffee shops in city center.", credits=500, status="pending", category="shopping", rating=4.8, availability="2 days left", redeemed_at=None),
    VoucherSchema(id=2, title="Free Bus Ticket", description="One-day free ticket for e-bus lines.", credits=300, status="pending", category="transport", rating=4.8, availability="7 days left", redeemed_at=None),
    VoucherSchema(id=3, title="Plant a Tree", description="We plant a tree in your name.", credits=200, status="pending", category="green", rating=5.0, availability="Always available", redeemed_at=None),
    VoucherSchema(id=5, title="Ocean Cleanup Donation", description="$10 donation to clean initiatives", credits=100, status="pending", category="charity", rating=4.9, availability="7 days left", redeemed_at=None),
]

MOCK_TRIPS = [
    TripSchema(id=2, user_id=1, date="2025-12-25", distance_km=15, transport_modes=["Walking"], credits=300),
    TripSchema(id=3, user_id=1, date="2025-12-24", distance_km=5, transport_modes=["Walking"], credits=300),
    TripSchema(id=4, user_id=1, date="2025-12-23", distance_km=10, transport_modes=["E-Bus", "Walking"], credits=250),
    TripSchema(id=5, user_id=1, date="2025-12-12", distance_km=15, transport_modes=["E-Bus", "Walking"], credits=160),
    TripSchema(id=6, user_id=1, date="2025-12-11", distance_km=8, transport_modes=["Bicycle"], credits=160),
    TripSchema(id=7, user_id=1, date="2025-11-20", distance_km=17, transport_modes=["Walking", "Bus", "E-Bus"], credits=120),
    TripSchema(id=8, user_id=1, date="2025-10-22", distance_km=20, transport_modes=["E-Bus", "E-Car"], credits=195),
    TripSchema(id=9, user_id=1, date="2025-09-14", distance_km=6, transport_modes=["Bicycle"], credits=145),
    TripSchema(id=10, user_id=1, date="2025-08-14", distance_km=6, transport_modes=["Bicycle"], credits=245),
]


def recreate_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def import_data():
    db = SessionLocal()
    try:
        # Emission factors
        for mode, factor in EMISSION_FACTORS.items():
            exists = db.query(EmissionFactor).filter(EmissionFactor.mode == mode).first()
            if not exists:
                db.add(EmissionFactor(mode=mode, factor=factor))

        # Users
        for u in MOCK_USERS:
            exists = db.query(User).filter(User.email.ilike(u.email)).first()
            if not exists:
                db.add(User(email=u.email, full_name=u.full_name, password=u.password, role=u.role))

        # Vouchers
        for v in MOCK_VOUCHERS:
            exists = db.query(Voucher).filter(Voucher.id == v.id).first()
            if not exists:
                db.add(Voucher(
                    id=v.id,
                    title=v.title,
                    description=v.description,
                    credits=v.credits,
                    status=v.status,
                    category=v.category,
                    rating=v.rating,
                    availability=v.availability,
                    redeemed_at=v.redeemed_at,
                    redeemed_by_user_id=None,
                ))

        # Trips
        for t in MOCK_TRIPS:
            exists = db.query(Trip).filter(Trip.id == t.id).first()
            if not exists:
                transport = ",".join(t.transport_modes) if getattr(t, "transport_modes", None) else ""
                new_trip = Trip(
                    id=t.id,
                    user_id=t.user_id,
                    date=t.date,
                    distance_km=t.distance_km,
                    transport_modes=transport,
                    credits=t.credits,
                )
                for mode in t.transport_modes:
                    ef = db.query(EmissionFactor).filter(EmissionFactor.mode == mode).first()
                    if ef:
                        new_trip.emission_factors.append(ef)
                db.add(new_trip)
                db.flush()
                wallet_entry = CreditWallet(
                    user_id=t.user_id,
                    trip_id=new_trip.id,
                    delta=t.credits,
                    timestamp=f"{t.date}T00:00:00",
                    note="Trip earned",
                )
                db.add(wallet_entry)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    recreate_db()
    import_data()
    print("Imported mock data into DB")
