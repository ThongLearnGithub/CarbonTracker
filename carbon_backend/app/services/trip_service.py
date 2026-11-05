from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import InvalidInputError, NotFoundError
from app.models import CreditWalletEntry, EmissionFactor, Trip, User
from app.schemas.trip import SeriesPoint, TripCreate, TripCreated, TripStats
from app.services.carbon_metrics import calculate_trip_metrics
from app.services.gps_filter import filter_gps_route
from app.services.wallet_service import lock_user_ledger

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_IN_STATS = 6


def emission_factor_map(db: Session) -> dict[str, float]:
    return {factor.mode: factor.factor for factor in db.scalars(select(EmissionFactor))}


def trip_co2_kg(trip: Trip, factors: dict[str, float]) -> tuple[float, float]:
    """(emitted, saved) for a stored trip, using the same formula as at logging time."""
    if not trip.transport_modes:
        return 0.0, 0.0
    emitted, saved, _credits = calculate_trip_metrics(trip.distance_km, trip.transport_modes, factors)
    return emitted, saved


def list_user_trips(db: Session, user_id: int, since: date | None = None) -> Sequence[Trip]:
    query = (
        select(Trip)
        .where(Trip.user_id == user_id)
        .options(selectinload(Trip.emission_factors))
        .order_by(Trip.date.desc())
    )
    if since is not None:
        query = query.where(Trip.date >= since)
    return db.scalars(query).all()


def get_user_trip(db: Session, user: User, trip_id: int) -> Trip:
    trip = db.scalar(
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user.id)
        .options(selectinload(Trip.emission_factors))
    )
    if trip is None:
        raise NotFoundError("Trip not found")
    return trip


def log_trip(db: Session, user: User, data: TripCreate) -> TripCreated:
    """Credit a trip. Trips on the same day are merged into that day's row; each call adds a ledger entry."""
    if data.gps_points is not None:
        distance_km = filter_gps_route(data.gps_points, data.transport_modes[0])
    else:
        distance_km = data.distance_km

    factors = emission_factor_map(db)
    try:
        co2_emitted, co2_saved, credits_earned = calculate_trip_metrics(distance_km, data.transport_modes, factors)
    except ValueError as error:
        raise InvalidInputError(str(error)) from error

    lock_user_ledger(db, user.id)
    trip = db.scalar(
        select(Trip)
        .where(Trip.user_id == user.id, Trip.date == data.date)
        .options(selectinload(Trip.emission_factors))
    )
    if trip is None:
        trip = Trip(user_id=user.id, date=data.date, distance_km=0.0, transport_modes_csv="", credits=0)
        db.add(trip)

    trip.distance_km += distance_km
    trip.credits += credits_earned
    modes = trip.transport_modes_csv.split(",") if trip.transport_modes_csv else []
    linked = {factor.mode for factor in trip.emission_factors}
    factor_rows = {row.mode: row for row in db.scalars(select(EmissionFactor).where(EmissionFactor.mode.in_(data.transport_modes)))}
    for mode in data.transport_modes:
        if mode not in modes:
            modes.append(mode)
        if mode in factor_rows and mode not in linked:
            trip.emission_factors.append(factor_rows[mode])
            linked.add(mode)
    trip.transport_modes_csv = ",".join(modes)

    db.flush()
    db.add(
        CreditWalletEntry(
            user_id=user.id,
            trip_id=trip.id,
            delta=credits_earned,
            timestamp=datetime.now().replace(microsecond=0),
            note="Trip earned",
        )
    )
    db.commit()

    return TripCreated(
        id=trip.id,
        user_id=trip.user_id,
        date=trip.date,
        distance_km=trip.distance_km,
        transport_modes=trip.transport_modes,
        credits=trip.credits,
        credits_earned=credits_earned,
        co2_emitted_kg=round(co2_emitted, 4),
        co2_saved_kg=round(co2_saved, 4),
    )


def _empty_bucket() -> dict[str, int]:
    return {"credits": 0, "trips": 0}


def get_trip_stats(db: Session, user: User, today: date | None = None) -> TripStats:
    today = today or date.today()
    trips = list_user_trips(db, user.id)
    factors = emission_factor_map(db)

    # Each transport mode of a day's trip counts as one trip (a day's row merges several legs).
    daily: dict[str, dict[str, int]] = defaultdict(_empty_bucket)
    weekly: dict[int, dict[str, int]] = defaultdict(_empty_bucket)
    monthly: dict[tuple[int, int], dict[str, int]] = defaultdict(_empty_bucket)
    start_of_week = today - timedelta(days=today.weekday())
    total_co2 = 0.0

    for trip in trips:
        legs = len(trip.transport_modes)
        total_co2 += trip_co2_kg(trip, factors)[0]

        if start_of_week <= trip.date <= start_of_week + timedelta(days=6):
            bucket = daily[WEEKDAY_LABELS[(trip.date - start_of_week).days]]
            bucket["credits"] += trip.credits
            bucket["trips"] += legs

        if (trip.date.year, trip.date.month) == (today.year, today.month):
            week_of_month = min((trip.date.day - 1) // 7 + 1, 4)  # days 29-31 fold into week 4
            weekly[week_of_month]["credits"] += trip.credits
            weekly[week_of_month]["trips"] += legs

        month_bucket = monthly[(trip.date.year, trip.date.month)]
        month_bucket["credits"] += trip.credits
        month_bucket["trips"] += legs

    return TripStats(
        user_id=user.id,
        total_trips=sum(len(trip.transport_modes) for trip in trips),
        total_credits=sum(trip.credits for trip in trips),
        total_distance_km=round(sum(trip.distance_km for trip in trips), 2),
        total_co2_kg=round(total_co2, 2),
        daily=[SeriesPoint(label=label, **daily[label]) for label in WEEKDAY_LABELS],
        weekly=[SeriesPoint(label=f"Week {week}", **weekly[week]) for week in (1, 2, 3, 4)],
        monthly=[
            SeriesPoint(label=MONTH_LABELS[month - 1], **bucket)
            for (_year, month), bucket in sorted(monthly.items())[-MONTHS_IN_STATS:]
        ],
    )
