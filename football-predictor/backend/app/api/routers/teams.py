"""Public team endpoints — name search + raw season stats (handy for debugging)."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_registry, provider_error_to_http, resolve_league_season
from app.db.session import get_db
from app.providers.base import ProviderError
from app.providers.registry import ProviderRegistry

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("/search")
def search_team(
    name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry),
):
    league_ext, season = resolve_league_season(db, None, None)
    try:
        provider = registry.get_active_provider()
        team = provider.get_team(name, league_ext, season)
        return asdict(team)
    except ProviderError as exc:
        raise provider_error_to_http(exc)


@router.get("/{team_id}/stats")
def team_stats(
    team_id: int,
    league_external_id: int | None = Query(None),
    season: int | None = Query(None),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry),
):
    league_ext, seas = resolve_league_season(db, league_external_id, season)
    try:
        provider = registry.get_active_provider()
        return asdict(provider.get_team_stats(team_id, seas, league_ext))
    except ProviderError as exc:
        raise provider_error_to_http(exc)
