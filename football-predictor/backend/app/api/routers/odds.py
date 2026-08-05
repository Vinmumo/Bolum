"""Bookmaker odds endpoint (public). Dormant until THE_ODDS_API_KEY is set."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import resolve_league_season
from app.db.session import get_db
from app.services.odds import OddsError, market_totals

router = APIRouter(prefix="/api/odds", tags=["odds"])


@router.get("/totals")
def totals(
    home: str = Query(...),
    away: str = Query(...),
    league_external_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    league_ext, _ = resolve_league_season(db, league_external_id, None)
    try:
        return market_totals(league_ext, home, away)
    except OddsError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
