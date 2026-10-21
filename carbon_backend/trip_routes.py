from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from models import Trip, TripCreate, TripStats, SeriesPoint
from database import get_db
from orm_models import Trip as ORMTrip, EmissionFactor, CreditWallet as ORMCreditWallet
from carbon_metrics import calculate_trip_metrics, emission_factor_for_mode
from gps_route import filter_gps_route

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("", response_model=List[Trip])
async def get_trips(user_id: int, db: Session = Depends(get_db)):
    trips_q = db.query(ORMTrip).filter(ORMTrip.user_id == user_id).all()
    trips = []
    for t in trips_q:
        transport_modes = [ef.mode for ef in t.emission_factors] if t.emission_factors else (t.transport_modes.split(",") if t.transport_modes else [])
        trips.append(Trip(id=t.id, user_id=t.user_id, date=t.date, distance_km=t.distance_km, transport_modes=transport_modes, credits=t.credits))
    trips.sort(key=lambda t: t.date, reverse=True)
    return trips

@router.get("/stats", response_model=TripStats)
async def get_trip_stats(user_id: int, db: Session = Depends(get_db)):
    today = datetime.now()
    trips_q = db.query(ORMTrip).filter(ORMTrip.user_id == user_id).all()
    trips = []
    for t in trips_q:
        transport_modes = [ef.mode for ef in t.emission_factors] if t.emission_factors else (t.transport_modes.split(",") if t.transport_modes else [])
        trips.append(Trip(id=t.id, user_id=t.user_id, date=t.date, distance_km=t.distance_km, transport_modes=transport_modes, credits=t.credits))

    total_trips = sum(len(t.transport_modes) for t in trips)
    total_credits = sum(t.credits for t in trips)
    total_distance = sum(t.distance_km for t in trips)

    # load emission factor map
    ef_records = db.query(EmissionFactor).all()
    ef_map = {r.mode: r.factor for r in ef_records}

    total_co2 = 0.0
    for t in trips:
        if not t.transport_modes:
            continue
        for mode in t.transport_modes:
            factor = emission_factor_for_mode(mode, ef_map)
            per_mode_share = t.distance_km / len(t.transport_modes)
            total_co2 += factor * per_mode_share

    def dparse(s: str) -> datetime:
        return datetime.fromisoformat(s)

    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    daily_map: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"credits": 0, "trips": 0}
    )

    today_date = today.date()
    
    start_of_week = today_date - timedelta(days=today_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    for t in trips:
        d = dparse(t.date).date()  
        
        if start_of_week <= d <= end_of_week:
            idx = (d - start_of_week).days  
            if 0 <= idx < 7:
                key = weekday_labels[idx]   
                daily_map[key]["credits"] += t.credits
                daily_map[key]["trips"] += len(t.transport_modes)

    daily_points: List[SeriesPoint] = [
        SeriesPoint(
            label=lbl,
            credits=daily_map[lbl]["credits"],
            trips=daily_map[lbl]["trips"],
        )
        for lbl in weekday_labels
    ]


    this_year, this_month = today.year, today.month
    weekly_map: Dict[int, Dict[str, int]] = defaultdict(
        lambda: {"credits": 0, "trips": 0}
    )

    for t in trips:
        d = dparse(t.date)
        if d.year == this_year and d.month == this_month:
            week_of_month = (d.day - 1) // 7 + 1  
            week_of_month = min(week_of_month, 4)
            weekly_map[week_of_month]["credits"] += t.credits
            weekly_map[week_of_month]["trips"] += len(t.transport_modes)

    weekly_points: List[SeriesPoint] = [
        SeriesPoint(
            label=f"Week {week}",
            credits=weekly_map[week]["credits"],
            trips=weekly_map[week]["trips"],
        )
        for week in [1, 2, 3, 4]
    ]

    
    monthly_map: Dict[tuple[int, int], Dict[str, int]] = defaultdict(
        lambda: {"credits": 0, "trips": 0}
    )

    for t in trips:
        d = dparse(t.date)
        key = (d.year, d.month)
        monthly_map[key]["credits"] += t.credits
        monthly_map[key]["trips"] += len(t.transport_modes)

    sorted_months = sorted(monthly_map.items())[-6:]
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    monthly_points: List[SeriesPoint] = [
        SeriesPoint(
            label=month_names[month - 1],
            credits=agg["credits"],
            trips=agg["trips"],
        )
        for (year, month), agg in sorted_months
    ]

    return TripStats(
        user_id=user_id,
        total_trips=total_trips,
        total_credits=total_credits,
        total_distance_km=round(total_distance, 2),
        total_co2_kg=round(total_co2, 2),
        daily=daily_points,
        weekly=weekly_points,
        monthly=monthly_points,
    )


@router.get("/{trip_id}", response_model=Trip)
async def get_trip_detail(trip_id: int, db: Session = Depends(get_db)):
    t = db.query(ORMTrip).filter(ORMTrip.id == trip_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trip not found")
    transport_modes = [ef.mode for ef in t.emission_factors] if t.emission_factors else (t.transport_modes.split(",") if t.transport_modes else [])
    return Trip(id=t.id, user_id=t.user_id, date=t.date, distance_km=t.distance_km, transport_modes=transport_modes, credits=t.credits)


@router.post("", response_model=Trip)
async def create_trip(body: TripCreate, db: Session = Depends(get_db)):
    if body.gps_points is not None:
        distance_km = filter_gps_route(
            body.gps_points,
            body.transport_modes[0],
        )
    elif body.distance_km is not None:
        distance_km = body.distance_km
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide GPS route points or a trip distance.",
        )

    configured_factors = {
        record.mode: record.factor for record in db.query(EmissionFactor).all()
    }
    try:
        co2_emitted, co2_saved, credits_earned = calculate_trip_metrics(
            distance_km,
            body.transport_modes,
            configured_factors,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    existing = db.query(ORMTrip).filter(ORMTrip.user_id == body.user_id, ORMTrip.date == body.date).first()

    if existing is not None:
        existing.distance_km += distance_km
        existing.credits += credits_earned
        existing_modes = set(existing.transport_modes.split(",")) if existing.transport_modes else set()
        existing_mode_objects = {ef.mode: ef for ef in existing.emission_factors} if existing.emission_factors else {}
        
        for mode in body.transport_modes:
            if mode not in existing_modes:
                ef = db.query(EmissionFactor).filter(EmissionFactor.mode == mode).first()
                if ef and mode not in existing_mode_objects:
                    existing.emission_factors.append(ef)
                    existing_mode_objects[mode] = ef
                existing_modes.add(mode)
        existing.transport_modes = ",".join(existing_modes)
        wallet_entry = ORMCreditWallet(
            user_id=body.user_id,
            trip_id=existing.id,
            delta=credits_earned,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            note="Trip earned",
        )
        db.add(existing)
        db.add(wallet_entry)
        db.commit()
        db.refresh(existing)
        transport_modes = [ef.mode for ef in existing.emission_factors] if existing.emission_factors else (existing.transport_modes.split(",") if existing.transport_modes else [])
        return Trip(
            id=existing.id,
            user_id=existing.user_id,
            date=existing.date,
            distance_km=existing.distance_km,
            transport_modes=transport_modes,
            credits=existing.credits,
            credits_earned=credits_earned,
            co2_emitted_kg=round(co2_emitted, 4),
            co2_saved_kg=round(co2_saved, 4),
        )

    new_trip = ORMTrip(
        user_id=body.user_id,
        date=body.date,
        distance_km=distance_km,
        transport_modes=",".join(body.transport_modes),
        credits=credits_earned,
    )
    db.add(new_trip)
    db.flush()
    for mode in body.transport_modes:
        ef = db.query(EmissionFactor).filter(EmissionFactor.mode == mode).first()
        if ef:
            new_trip.emission_factors.append(ef)
    wallet_entry = ORMCreditWallet(
        user_id=body.user_id,
        trip_id=new_trip.id,
        delta=credits_earned,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        note="Trip earned",
    )
    db.add(wallet_entry)
    db.commit()
    db.refresh(new_trip)
    transport_modes = [ef.mode for ef in new_trip.emission_factors] if new_trip.emission_factors else (new_trip.transport_modes.split(",") if new_trip.transport_modes else [])
    return Trip(
        id=new_trip.id,
        user_id=new_trip.user_id,
        date=new_trip.date,
        distance_km=new_trip.distance_km,
        transport_modes=transport_modes,
        credits=new_trip.credits,
        credits_earned=credits_earned,
        co2_emitted_kg=round(co2_emitted, 4),
        co2_saved_kg=round(co2_saved, 4),
    )

