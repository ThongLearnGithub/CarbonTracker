from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import User
from app.schemas.homepage import HomePageSummary
from app.services.trip_service import emission_factor_map, list_user_trips, trip_co2_kg
from app.services.wallet_service import get_balance


def get_homepage_summary(db: Session, user: User, today: date | None = None) -> HomePageSummary:
    today = today or date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    trips = list_user_trips(db, user.id, since=min(start_of_week, start_of_month))
    month_trips = [trip for trip in trips if start_of_month <= trip.date]
    factors = emission_factor_map(db)

    return HomePageSummary(
        user_id=user.id,
        # Same ledger as /wallet/summary, so spent credits are subtracted.
        balance_credits=get_balance(db, user.id),
        credits_this_week=sum(trip.credits for trip in trips if start_of_week <= trip.date <= today),
        co2_saved_kg=round(sum(trip_co2_kg(trip, factors)[1] for trip in month_trips), 2),
        distance_km=round(sum(trip.distance_km for trip in month_trips), 2),
    )
