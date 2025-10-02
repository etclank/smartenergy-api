# app/api/routers.py
from fastapi import APIRouter
from . import health, auth, meters

api = APIRouter()
api.include_router(health.router)
api.include_router(auth.router)
api.include_router(meters.router)
