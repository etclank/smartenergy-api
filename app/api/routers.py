# app/api/routers.py
from fastapi import APIRouter
from . import auth, meters, health, sites, energy_imported, energy_exported, energy_reactive, max_power, tariffs

api = APIRouter(prefix="/api")

api.include_router(auth.router)
api.include_router(meters.router)
api.include_router(health.router)
api.include_router(sites.router)
api.include_router(energy_imported.router)
api.include_router(energy_exported.router)
api.include_router(energy_reactive.router)
api.include_router(max_power.router)
api.include_router(tariffs.router)
