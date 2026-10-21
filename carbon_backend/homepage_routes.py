from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import HomePageSummary
from database import get_db
from orm_models import Trip as ORMTrip, EmissionFactor
from carbon_metrics import emission_factor_for_mode

router = APIRouter(prefix="/homepage", tags=["homepage"])
# Router set up: all routes in this router will start with /homepage

# Summary Endpoint
@router.get("/summary", response_model=HomePageSummary) # ex: API=/summary?user_id=1 --> Json: user_id: 1; balance credits: 120,...
async def homepage_summary(user_id: int, db: Session = Depends(get_db)):
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())  
    trips_q = db.query(ORMTrip).filter(ORMTrip.user_id == user_id).all()
    trips = []
    for t in trips_q:
        transport_modes = [ef.mode for ef in t.emission_factors] if t.emission_factors else (t.transport_modes.split(",") if t.transport_modes else [])
        trips.append(type("T", (), {"id": t.id, "user_id": t.user_id, "date": t.date, "distance_km": t.distance_km, "transport_modes": transport_modes, "credits": t.credits}))

    emission_records = db.query(EmissionFactor).all()
    emission_factors = {record.mode: record.factor for record in emission_records}

    balance = sum(t.credits for t in trips) # calculate balance credit


    credits_this_week = 0
    for t in trips:
        d = datetime.fromisoformat(t.date).date()
        if start_of_week <= d <= today: # credit this week
            credits_this_week += t.credits

    
    distance_month = 0.0
    for t in trips:
        d = datetime.fromisoformat(t.date).date()
        if d.year == today.year and d.month == today.month: # distance this month
            distance_month += t.distance_km

    
    co2_saved = 0.0
    for t in trips:
        d = datetime.fromisoformat(t.date).date()
        if d.year == today.year and d.month == today.month:
            for mode in t.transport_modes:
                factor = emission_factor_for_mode(mode, emission_factors)
                co2_saved += max(0.0, 0.5 - factor) * (
                    t.distance_km / len(t.transport_modes)
                )

    return HomePageSummary(
        user_id=user_id,
        balance_credits=balance,
        credits_this_week=credits_this_week,
        co2_saved_kg=round(co2_saved, 2),
        distance_km=round(distance_month, 2),
    )
