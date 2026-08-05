"""FastAPI application entrypoint.

Run:  uvicorn app.main:app --reload   (from the backend/ directory)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.core.config import settings
from app.db.base import Base
from app.db.seed import seed_defaults
from app.db.session import SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("football_predictor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist. In production use Alembic migrations.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_defaults(db)
    logger.info("Startup complete (env=%s).", settings.environment)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from app.api.routers import (  # noqa: E402
    admin,
    backtest,
    fixtures,
    leagues,
    odds,
    predictions,
    teams,
)

app.include_router(predictions.router)
app.include_router(fixtures.router)
app.include_router(leagues.router)
app.include_router(teams.router)
app.include_router(backtest.router)
app.include_router(odds.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "app": settings.app_name}
