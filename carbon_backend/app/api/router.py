from fastapi import APIRouter

from app.api.routes import auth, homepage, routing, trips, vouchers, wallet

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(homepage.router)
api_router.include_router(wallet.router)
api_router.include_router(vouchers.router)
api_router.include_router(trips.router)
api_router.include_router(routing.router)
