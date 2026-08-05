"""League schemas."""
from __future__ import annotations

from pydantic import BaseModel


class LeagueCreate(BaseModel):
    name: str
    country: str = ""
    external_provider_id: int
    season: int = 2023
    active: bool = True


class LeagueUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    external_provider_id: int | None = None
    season: int | None = None
    active: bool | None = None


class LeagueOut(BaseModel):
    id: int
    name: str
    country: str
    external_provider_id: int
    season: int
    active: bool

    model_config = {"from_attributes": True}
