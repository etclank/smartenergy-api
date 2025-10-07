# app/api/routers.py
from fastapi import APIRouter
from . import auth, meters, health

api = APIRouter(prefix="/api")

api.include_router(auth.router)
api.include_router(meters.router)
api.include_router(health.router)


