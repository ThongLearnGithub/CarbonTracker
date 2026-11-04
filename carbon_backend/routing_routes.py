import json
from functools import lru_cache
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from routing.model import ROOT
from routing.service import ALGORITHMS, RoutingEngine, RoutingError

router = APIRouter(prefix="/routing", tags=["routing"])


@lru_cache(maxsize=1)
def get_engine() -> RoutingEngine:
    """Graph + weights for all vehicles, built once (~2 s); main.py calls this at start-up."""
    return RoutingEngine()


class Point(BaseModel):
    lat: float = Field(..., examples=[10.772])
    lon: float = Field(..., examples=[106.698])


class RouteRequest(BaseModel):
    origin: Point
    destination: Point
    vehicle: str = Field("motorcycle_petrol", description="motorcycle_petrol | car_petrol | motorcycle_electric | bicycle | foot")
    depart_at: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="HH:MM; picks the peak/off-peak weights")
    slot: Optional[Literal["offpeak", "peak"]] = Field(None, description="overrides depart_at")
    algorithm: Literal[ALGORITHMS] = "pareto"
    k: int = Field(3, ge=1, le=10, description="number of routes for pareto / yen")
    max_extra_time: float = Field(0.2, ge=0, le=2, description="csp: allowed extra time as a fraction of the fastest route")


@router.get("/health")
def health():
    return {"status": "ok", "graph_load_seconds": get_engine().load_seconds}


@router.get("/meta")
def meta():
    cfg = get_engine().cfg
    return {
        "vehicles": {k: p["label"] for k, p in cfg["profiles"].items()},
        "slots": {k: s["label"] for k, s in cfg["slots"].items()},
        "peak_hours": cfg["peak_hours"],
        "algorithms": list(ALGORITHMS),
    }


@router.get("/lez")
def lez():
    return json.loads((ROOT / "data" / "lez" / "lez_zones.geojson").read_text(encoding="utf-8"))


# Plain def (not async): route search is CPU work, FastAPI runs it in the thread pool.
@router.post("/routes")
def routes(req: RouteRequest):
    try:
        return get_engine().route((req.origin.lat, req.origin.lon), (req.destination.lat, req.destination.lon),
                                  req.vehicle, depart_at=req.depart_at, slot=req.slot, algorithm=req.algorithm,
                                  k=req.k, max_extra_time=req.max_extra_time)
    except RoutingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/map", include_in_schema=False)
def test_map():
    return FileResponse(ROOT / "static" / "index.html")
