from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.trip import TripCreate, TripCreated, TripRead, TripStats
from app.services import trip_service

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("", response_model=list[TripRead])
def list_trips(user: CurrentUser, db: SessionDep):
    return trip_service.list_user_trips(db, user.id)


@router.post("", response_model=TripCreated, status_code=status.HTTP_201_CREATED)
def create_trip(body: TripCreate, user: CurrentUser, db: SessionDep):
    return trip_service.log_trip(db, user, body)


@router.get("/stats", response_model=TripStats)
def get_trip_stats(user: CurrentUser, db: SessionDep):
    return trip_service.get_trip_stats(db, user)


@router.get("/{trip_id}", response_model=TripRead)
def get_trip(trip_id: int, user: CurrentUser, db: SessionDep):
    return trip_service.get_user_trip(db, user, trip_id)
