"""Stored gameweek-replay results.

One row per backtested fixture. Predictions here were computed from
point-in-time standings only (what was knowable before kick-off), so the season
summary aggregates honestly from these rows without refetching anything.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    __table_args__ = (
        UniqueConstraint(
            "league_id", "season", "fixture_ext_id", name="uq_backtest_fixture"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)  # canonical ext id
    season: Mapped[int] = mapped_column(Integer, index=True)
    matchday: Mapped[int] = mapped_column(Integer, index=True)
    fixture_ext_id: Mapped[int] = mapped_column(Integer)

    home_team: Mapped[str] = mapped_column(String(120))
    away_team: Mapped[str] = mapped_column(String(120))
    home_goals: Mapped[int] = mapped_column(Integer)
    away_goals: Mapped[int] = mapped_column(Integer)

    xg_home: Mapped[float] = mapped_column(Float)
    xg_away: Mapped[float] = mapped_column(Float)

    # {"1.5": {"p_over": 0.78, "pick": "over", "hit": true}, ...}
    lines: Mapped[dict] = mapped_column(JSON)
    # {"pick": "home", "hit": false, "p_home": .., "p_draw": .., "p_away": ..}
    result_1x2: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
