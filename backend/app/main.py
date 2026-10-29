"""backend/app/main.py — FastAPI application entry point with MongoDB support."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routes import (auth_router, drivers_router, trips_router,
                        scores_router, analytics_router, coaching_router)

DATABASE_TYPE = os.getenv("DATABASE_TYPE", "mongodb").lower()

app = FastAPI(
    title="Driver Behavior Scoring System API",
    description="Fleet safety system: trip scoring, risk analysis, coaching workflow with MongoDB.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_router)
app.include_router(drivers_router)
app.include_router(trips_router)
app.include_router(scores_router)
app.include_router(analytics_router)
app.include_router(coaching_router)


@app.on_event("startup")
def on_startup():
    db_type = os.getenv("DATABASE_TYPE", "mongodb").lower()
    if db_type == "mongodb":
        from app.database.mongodb import initialize_mongodb
        initialize_mongodb()
    else:
        from app.services.db_init import initialize_database
        initialize_database()


@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "service": "Driver Behavior Scoring API",
        "database": os.getenv("DATABASE_TYPE", "mongodb"),
        "version": "1.0.0"
    }


@app.get("/", tags=["System"])
def root():
    return {
        "name": "Driver Behavior Scoring System API",
        "version": "1.0.0",
        "database": os.getenv("DATABASE_TYPE", "mongodb"),
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "auth": "/auth/login",
            "drivers": "/drivers",
            "trips": "/trips",
            "scores": "/scores",
            "analytics": "/analytics/dashboard",
            "coaching": "/coaching"
        }
    }
