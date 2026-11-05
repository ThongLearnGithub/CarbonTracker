from typing import Literal

from pydantic import BaseModel, Field

from routing.service import ALGORITHMS


class Point(BaseModel):
    lat: float = Field(ge=-90, le=90, examples=[10.772])
    lon: float = Field(ge=-180, le=180, examples=[106.698])


class RouteRequest(BaseModel):
    origin: Point
    destination: Point
    vehicle: str = Field("motorcycle_petrol", description="motorcycle_petrol | car_petrol | motorcycle_electric | bicycle | foot")
    depart_at: str | None = Field(None, pattern=r"^\d{2}:\d{2}$", description="HH:MM; picks the peak/off-peak weights")
    slot: Literal["offpeak", "peak"] | None = Field(None, description="overrides depart_at")
    algorithm: Literal[ALGORITHMS] = "pareto"
    k: int = Field(3, ge=1, le=10, description="number of routes for pareto / yen")
    max_extra_time: float = Field(0.2, ge=0, le=2, description="csp: allowed extra time as a fraction of the fastest route")


class RoutingMeta(BaseModel):
    vehicles: dict[str, str]
    slots: dict[str, str]
    peak_hours: list[tuple[str, str]]
    algorithms: list[str]
