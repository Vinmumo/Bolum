"""Fixtures endpoints (public) — gameweeks (calendar) and their fixtures."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_registry, provider_error_to_http, resolve_league_season
from app.db.session import get_db
from app.providers.base import ProviderError, ProviderRound
from app.providers.registry import ProviderRegistry
from app.schemas.prediction import FixtureOut, RoundOut

router = APIRouter(prefix="/api/fixtures", tags=["fixtures"])


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.fromisoformat(value[:10])
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _current_round_name(rounds: list[ProviderRound]) -> str | None:
    """First round whose end (or start) hasn't passed; else the last round."""
    now = datetime.now(timezone.utc)
    for r in rounds:
        end = _parse_dt(r.end_date) or _parse_dt(r.start_date)
        if end and end >= now:
            return r.name
    return rounds[-1].name if rounds else None


@router.get("/rounds", response_model=list[RoundOut])
def list_rounds(
    league_external_id: int | None = Query(None),
    season: int | None = Query(None),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry),
):
    """Gameweeks/matchdays for the league — powers the calendar landing view."""
    league_ext, seas = resolve_league_season(db, league_external_id, season)
    try:
        provider = registry.get_active_provider()
        rounds = provider.get_rounds(league_ext, seas)
        current = _current_round_name(rounds)
        return [
            RoundOut(
                name=r.name,
                start_date=r.start_date,
                end_date=r.end_date,
                fixture_count=r.fixture_count,
                is_current=(r.name == current),
            )
            for r in rounds
        ]
    except ProviderError as exc:
        raise provider_error_to_http(exc)


@router.get("", response_model=list[FixtureOut])
def list_fixtures(
    league_external_id: int | None = Query(None),
    season: int | None = Query(None),
    round: str | None = Query(None),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry),
):
    league_ext, seas = resolve_league_season(db, league_external_id, season)
    try:
        provider = registry.get_active_provider()
        fixtures = provider.get_fixtures(league_ext, seas, round)
        return [FixtureOut(**asdict(f)) for f in fixtures]
    except ProviderError as exc:
        raise provider_error_to_http(exc)
