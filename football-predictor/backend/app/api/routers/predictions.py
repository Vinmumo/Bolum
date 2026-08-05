"""Prediction endpoints (public)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_registry,
    provider_error_to_http,
    resolve_league_season,
)
from app.db.session import get_db
from app.models.prediction import Prediction
from app.providers.base import ProviderError
from app.providers.registry import ProviderRegistry
from app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    RecentPredictionOut,
)
from app.services.aggregator import predict_fixture_consensus

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.post("/predict", response_model=PredictionResponse)
def predict(
    body: PredictionRequest,
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry),
):
    """Consensus prediction: runs across every active provider and averages."""
    league_ext, season = resolve_league_season(db, body.league_external_id, body.season)
    try:
        providers = registry.get_active_providers()
        return predict_fixture_consensus(
            providers,
            home_name=body.home,
            away_name=body.away,
            league_external_id=league_ext,
            season=season,
            db=db,
            persist=True,
        )
    except ProviderError as exc:
        raise provider_error_to_http(exc)


@router.get("/recent", response_model=list[RecentPredictionOut])
def recent(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Prediction).order_by(Prediction.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        RecentPredictionOut(
            id=r.id,
            home_team=r.home_team,
            away_team=r.away_team,
            xg_home=r.xg_home,
            xg_away=r.xg_away,
            prob_home=r.prob_home,
            prob_draw=r.prob_draw,
            prob_away=r.prob_away,
            provider_name=r.provider_name,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
