"""Backtest endpoints (public): gameweek replay + season accuracy summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_registry, provider_error_to_http, resolve_league_season
from app.db.session import get_db
from app.providers.base import ProviderError
from app.providers.registry import ProviderRegistry
from app.services.backtest import replay_gameweek, season_summary

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/gameweek")
def gameweek_replay(
    season: int = Query(..., description="Season start-year, e.g. 2025"),
    matchday: int = Query(..., ge=1, le=50),
    league_external_id: int | None = Query(None),
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry),
):
    league_ext, _ = resolve_league_season(db, league_external_id, season)
    try:
        provider = registry.get_active_provider()
        return replay_gameweek(
            provider, db,
            league_external_id=league_ext, season=season, matchday=matchday,
            refresh=refresh,
        )
    except ProviderError as exc:
        raise provider_error_to_http(exc)


@router.get("/summary")
def summary(
    season: int = Query(...),
    league_external_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    league_ext, _ = resolve_league_season(db, league_external_id, season)
    return season_summary(db, league_external_id=league_ext, season=season)
