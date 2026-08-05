"""Cached / logged predictions.

We store the full result plus the raw inputs the model used, as JSON, so a past
prediction is reproducible and future-you can see *why* a number came out.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    league_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_team: Mapped[str] = mapped_column(String(120), nullable=False)
    away_team: Mapped[str] = mapped_column(String(120), nullable=False)

    # Headline outputs (denormalised for easy admin listing).
    xg_home: Mapped[float] = mapped_column(Float, nullable=False)
    xg_away: Mapped[float] = mapped_column(Float, nullable=False)
    prob_home: Mapped[float] = mapped_column(Float, nullable=False)
    prob_draw: Mapped[float] = mapped_column(Float, nullable=False)
    prob_away: Mapped[float] = mapped_column(Float, nullable=False)

    # Full result + the inputs used, as JSON.
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False)

    provider_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Prediction {self.home_team} vs {self.away_team} @ {self.created_at}>"
