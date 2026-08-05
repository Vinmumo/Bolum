"""Leagues are data, not code. Enable La Liga / Serie A etc. from the admin UI.

`external_provider_id` is the league id in the active provider's namespace
(e.g. 39 = Premier League on API-Football).
"""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # League id in the provider's namespace.
    external_provider_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Default season to query for this league.
    season: Mapped[int] = mapped_column(Integer, nullable=False, default=2023)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<League {self.name} ext={self.external_provider_id} active={self.active}>"
