"""The contract every football-data provider must satisfy.

Adding a new API (football-data.org, SportMonks, ...) means writing ONE new
subclass of FootballDataProvider that returns these normalised DTOs. Nothing
downstream (services, routers, UI) knows or cares which provider produced the
data. See docs/ADDING_A_PROVIDER.md.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# Normalised DTOs — the common shape all providers translate their JSON into.
# --------------------------------------------------------------------------- #
@dataclass
class ProviderTeam:
    id: int
    name: str
    logo: str | None = None


@dataclass
class ProviderTeamStats:
    team_id: int
    name: str
    games_home: int
    games_away: int
    goals_for_home: int
    goals_against_home: int
    goals_for_away: int
    goals_against_away: int
    recent_form: list[str] = field(default_factory=list)  # most-recent-first
    logo: str | None = None


@dataclass
class ProviderH2HMatch:
    home_team_id: int
    away_team_id: int
    home_goals: int
    away_goals: int
    date: str | None = None


@dataclass
class ProviderFixture:
    id: int
    league_id: int
    season: int
    round: str | None
    date: str | None
    status: str
    home: ProviderTeam
    away: ProviderTeam
    home_goals: int | None = None
    away_goals: int | None = None


@dataclass
class ProviderLeague:
    id: int
    name: str
    country: str
    season: int | None = None


@dataclass
class ProviderRound:
    """A gameweek / matchday: a named round plus the dates it spans."""

    name: str
    start_date: str | None = None
    end_date: str | None = None
    fixture_count: int = 0


# --------------------------------------------------------------------------- #
# Errors — providers raise these; the API layer maps them to HTTP responses.
# --------------------------------------------------------------------------- #
class ProviderError(Exception):
    """Generic provider failure."""


class ProviderAuthError(ProviderError):
    """Missing / invalid API key."""


class ProviderRateLimitError(ProviderError):
    """Provider rate limit hit — surfaced to the UI as a friendly message."""


class ProviderNotFoundError(ProviderError):
    """Requested entity (team/fixture) not found."""


# --------------------------------------------------------------------------- #
# The interface
# --------------------------------------------------------------------------- #
class FootballDataProvider(ABC):
    """Abstract base. Every concrete provider implements these five methods."""

    #: stable slug used in the DB `provider_type` column + registry mapping.
    provider_type: str = "base"

    @abstractmethod
    def get_team(self, name: str, league_id: int | None = None, season: int | None = None) -> ProviderTeam:
        """Resolve a team by (fuzzy) name to a provider team id."""

    @abstractmethod
    def get_team_stats(self, team_id: int, season: int, league_id: int) -> ProviderTeamStats:
        """Aggregated season stats for a team in a league."""

    @abstractmethod
    def get_h2h(self, team1_id: int, team2_id: int, limit: int = 10) -> list[ProviderH2HMatch]:
        """Recent head-to-head meetings, most recent first."""

    @abstractmethod
    def get_fixtures(self, league_id: int, season: int, round: str | None = None) -> list[ProviderFixture]:
        """Fixtures for a league/season, optionally a specific round."""

    @abstractmethod
    def get_leagues(self) -> list[ProviderLeague]:
        """Leagues the provider knows about (for the admin league picker)."""

    def get_rounds(self, league_id: int, season: int) -> list[ProviderRound]:
        """Gameweeks/matchdays for a league+season, ordered by date.

        Default implementation derives rounds from get_fixtures(). Providers can
        override for efficiency (e.g. a dedicated rounds endpoint). Not abstract,
        so existing providers keep working without changes.
        """
        fixtures = self.get_fixtures(league_id, season, round=None)
        groups: dict[str, list[str | None]] = {}
        for f in fixtures:
            groups.setdefault(f.round or "Fixtures", []).append(f.date)
        rounds: list[ProviderRound] = []
        for name, dates in groups.items():
            ds = sorted(d for d in dates if d)
            rounds.append(
                ProviderRound(
                    name=name,
                    start_date=ds[0] if ds else None,
                    end_date=ds[-1] if ds else None,
                    fixture_count=len(dates),
                )
            )
        rounds.sort(key=lambda r: r.start_date or "")
        return rounds
