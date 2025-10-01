# routers.py
from fastapi import APIRouter
from . import health, auth, meters

api = APIRouter()
api.include_router(health.router, tags=["health"])
api.include_router(auth.router, prefix="/auth", tags=["auth"])
api.include_router(meters.router, tags=["meters"])