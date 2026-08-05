"""Public leagues endpoint — powers the nav league switcher."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.league import League
from app.schemas.league import LeagueOut

router = APIRouter(prefix="/api/leagues", tags=["leagues"])


@router.get("", response_model=list[LeagueOut])
def list_active_leagues(db: Session = Depends(get_db)):
    rows = db.execute(
        select(League).where(League.active.is_(True)).order_by(League.name)
    ).scalars().all()
    return rows
