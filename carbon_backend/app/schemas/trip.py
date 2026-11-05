import datetime as dt

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel

MAX_TRIP_DISTANCE_KM = 500  # sanity cap: credits are derived from distance


class GpsRoutePoint(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy: float = Field(ge=0, allow_inf_nan=False)
    timestamp: dt.datetime
    is_mocked: bool = False


class TripCreate(BaseModel):
    date: dt.date = Field(default_factory=dt.date.today)
    distance_km: float | None = Field(default=None, ge=0, le=MAX_TRIP_DISTANCE_KM, allow_inf_nan=False)
    transport_modes: list[str] = Field(min_length=1, max_length=10)
    gps_points: list[GpsRoutePoint] | None = Field(default=None, max_length=50_000)

    @model_validator(mode="after")
    def require_distance_source(self) -> "TripCreate":
        if self.gps_points is None and self.distance_km is None:
            raise ValueError("Provide GPS route points or a trip distance.")
        return self


class TripRead(ORMModel):
    id: int
    user_id: int
    date: dt.date
    distance_km: float
    transport_modes: list[str]
    credits: int


class TripCreated(TripRead):
    """Trip after logging, plus what this particular submission earned."""

    credits_earned: int
    co2_emitted_kg: float
    co2_saved_kg: float


class SeriesPoint(BaseModel):
    label: str
    credits: int
    trips: int


class TripStats(BaseModel):
    user_id: int
    total_trips: int
    total_credits: int
    total_distance_km: float
    total_co2_kg: float
    daily: list[SeriesPoint]
    weekly: list[SeriesPoint]
    monthly: list[SeriesPoint]
