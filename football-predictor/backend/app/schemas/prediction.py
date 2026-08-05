"""Request/response schemas for predictions & fixtures."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    home: str = Field(..., description="Home team name (fuzzy match).")
    away: str = Field(..., description="Away team name (fuzzy match).")
    league_external_id: int | None = Field(
        None, description="Provider league id; defaults to the active league."
    )
    season: int | None = Field(None, description="Season year; defaults to config.")


class Scoreline(BaseModel):
    home: int
    away: int
    probability: float


class PredictionCore(BaseModel):
    xg_home: float
    xg_away: float
    prob_home_win: float
    prob_draw: float
    prob_away_win: float
    prob_over_2_5: float
    prob_under_2_5: float
    prob_btts: float
    top_scorelines: list[Scoreline]


class TeamOut(BaseModel):
    id: int
    name: str
    logo: str | None = None


class H2HOut(BaseModel):
    played: int
    home_wins: int
    away_wins: int
    draws: int
    summary: str


class SourcePrediction(BaseModel):
    provider: str
    prediction: PredictionCore
    form: dict
    h2h: H2HOut


class PredictionResponse(BaseModel):
    home_team: TeamOut
    away_team: TeamOut
    # `consensus` is the averaged headline; `sources` is each API's own take.
    consensus: PredictionCore
    sources: list[SourcePrediction]
    form: dict
    h2h: H2HOut
    meta: dict


class RoundOut(BaseModel):
    name: str
    start_date: str | None = None
    end_date: str | None = None
    fixture_count: int
    is_current: bool = False


class FixtureOut(BaseModel):
    id: int
    league_id: int
    season: int
    round: str | None = None
    date: str | None = None
    status: str
    home: TeamOut
    away: TeamOut
    home_goals: int | None = None
    away_goals: int | None = None


class RecentPredictionOut(BaseModel):
    id: int
    home_team: str
    away_team: str
    xg_home: float
    xg_away: float
    prob_home: float
    prob_draw: float
    prob_away: float
    provider_name: str | None
    created_at: str
