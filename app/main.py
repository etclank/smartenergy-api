# app/main.py
from fastapi import FastAPI
from app.api.routers import api

app = FastAPI(title="SmartEnergy API", version="0.1.0")
app.include_router(api)

@app.get("/")
async def root():
    return {"status": "ok", "docs": "/docs", "redoc": "/redoc"}
