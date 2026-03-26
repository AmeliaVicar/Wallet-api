from fastapi import APIRouter

from app.api.v1.wallets import router as wallets_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(wallets_router)

