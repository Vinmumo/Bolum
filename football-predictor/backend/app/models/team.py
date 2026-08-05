"""Lightweight team cache. Full stats are fetched from providers on demand and
cached in-process; this table just gives stable local ids + logos for the UI.
"""
from __future__ import annotations

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("external_provider_id", name="uq_team_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    external_provider_id: Mapped[int] = mapped_column(Integer, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    league_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Team {self.name} ext={self.external_provider_id}>"
