import json
from functools import lru_cache

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import RoutingEngineDep
from app.schemas.routing import RouteRequest, RoutingMeta
from routing.model import ROOT
from routing.service import ALGORITHMS

router = APIRouter(prefix="/routing", tags=["routing"])


@lru_cache(maxsize=1)
def _lez_geojson() -> dict:
    return json.loads((ROOT / "data" / "lez" / "lez_zones.geojson").read_text(encoding="utf-8"))


@router.get("/health")
def health(engine: RoutingEngineDep):
    return {"status": "ok", "graph_load_seconds": engine.load_seconds}


@router.get("/meta", response_model=RoutingMeta)
def meta(engine: RoutingEngineDep):
    cfg = engine.cfg
    return RoutingMeta(
        vehicles={key: profile["label"] for key, profile in cfg["profiles"].items()},
        slots={key: slot["label"] for key, slot in cfg["slots"].items()},
        peak_hours=cfg["peak_hours"],
        algorithms=list(ALGORITHMS),
    )


@router.get("/lez")
def lez():
    return _lez_geojson()


# Plain def: route search is CPU work, so FastAPI runs it in the thread pool.
# RoutingError (bad vehicle, point off the graph, ...) is turned into a 400 by the app's exception handler.
@router.post("/routes")
def routes(req: RouteRequest, engine: RoutingEngineDep):
    return engine.route(
        (req.origin.lat, req.origin.lon),
        (req.destination.lat, req.destination.lon),
        req.vehicle,
        depart_at=req.depart_at,
        slot=req.slot,
        algorithm=req.algorithm,
        k=req.k,
        max_extra_time=req.max_extra_time,
    )


@router.get("/map", include_in_schema=False)
def test_map():
    return FileResponse(ROOT / "static" / "index.html")
