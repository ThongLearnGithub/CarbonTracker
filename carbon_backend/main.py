from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth_routes import router as auth_router
from homepage_routes import router as homepage_router
from wallet_routes import router as wallet_router
from voucher_routes import router as voucher_router
from trip_routes import router as trip_router
from routing_routes import router as routing_router, get_engine

from database import engine, Base, migrate_trip_distance_precision
import orm_models  # noqa: F401


@asynccontextmanager
async def lifespan(_app):
    get_engine()  # load the routing graph before the first request
    yield


app = FastAPI(
    title="Carbon Tracker Mock API",
    description="Mock API  thesis Carbon Tracker ",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change to specific URLs in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(auth_router)
app.include_router(homepage_router)
app.include_router(wallet_router)
app.include_router(voucher_router)
app.include_router(trip_router)
app.include_router(routing_router)

Base.metadata.create_all(bind=engine)
migrate_trip_distance_precision()

@app.get("/")
async def root():
    return {"message": "Carbon Tracker API is running"}
