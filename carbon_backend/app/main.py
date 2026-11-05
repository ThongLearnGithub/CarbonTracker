from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from app.api.deps import SessionDep
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from routing.service import RoutingEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the routing graph and weights once (~2 s) before serving the first request.
    app.state.routing_engine = RoutingEngine()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        description="Backend API for the Carbon Tracker thesis apps (Flutter and web).",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Starlette runs the last-added middleware first, so CORS wraps everything (error responses included).
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)  # route geometries are large
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,  # auth uses the Authorization header, not cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/", tags=["meta"])
    def root():
        return {"message": "Carbon Tracker API is running"}

    @app.get("/health", tags=["meta"])
    def health(db: SessionDep):
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
