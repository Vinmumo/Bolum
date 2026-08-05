"""Public leagues endpoints — nav switcher, seasons list, standings tables."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_registry, provider_error_to_http, resolve_league_season
from app.db.session import get_db
from app.models.league import League
from app.providers.base import ProviderError
from app.providers.registry import ProviderRegistry
from app.schemas.league import LeagueOut

router = APIRouter(prefix="/api/leagues", tags=["leagues"])


@router.get("", response_model=list[LeagueOut])
def list_active_leagues(db: Session = Depends(get_db)):
    rows = db.execute(
        select(League).where(League.active.is_(True)).order_by(League.name)
    ).scalars().all()
    return rows


@router.get("/seasons")
def list_seasons(
    league_external_id: int | None = Query(None),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry),
):
    """Current + past seasons for the league (from the primary provider)."""
    league_ext, current = resolve_league_season(db, league_external_id, None)
    try:
        provider = registry.get_active_provider()
        seasons = provider.get_seasons(league_ext)
    except ProviderError as exc:
        raise provider_error_to_http(exc)
    if current not in seasons:
        seasons = sorted({current, *seasons}, reverse=True)
    return {
        "league_external_id": league_ext,
        "current_season": current,
        "seasons": seasons,
        "past_seasons": [s for s in seasons if s < current],
    }


@router.get("/standings")
def standings(
    season: int = Query(...),
    league_external_id: int | None = Query(None),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry),
):
    """League table for a season — the 'stats' view for past seasons."""
    league_ext, _ = resolve_league_season(db, league_external_id, season)
    try:
        provider = registry.get_active_provider()
        rows = provider.get_standings(league_ext, season)
        return [asdict(r) for r in rows]
    except ProviderError as exc:
        raise provider_error_to_http(exc)
