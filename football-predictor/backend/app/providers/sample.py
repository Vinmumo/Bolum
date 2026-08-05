"""Offline sample provider — canned Premier League data.

Lets the whole pipeline (provider -> stats -> Poisson model -> UI) run end to
end with NO API key, so you can develop and demo before signing up for
API-Football. Numbers are representative of a recent PL season (per-venue over
~19 games). It also generates a realistic multi-gameweek schedule (round-robin,
one matchday per week) with dates that straddle "today", so the calendar /
gameweek views have something to show. Swap the active provider to
`api_football` in the admin UI once you have a key.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.providers.base import (
    FootballDataProvider,
    ProviderFixture,
    ProviderH2HMatch,
    ProviderLeague,
    ProviderNotFoundError,
    ProviderRound,
    ProviderTeam,
    ProviderTeamStats,
)

# team_id -> canned season stats (home/away split over ~19 games each)
_TEAMS: dict[int, dict] = {
    50: dict(name="Manchester City", gh=51, ah=12, ga=45, aa=22, form="WWWDW"),
    42: dict(name="Arsenal", gh=49, ah=13, ga=42, aa=16, form="WWDWW"),
    40: dict(name="Liverpool", gh=45, ah=15, ga=31, aa=18, form="WDWWL"),
    47: dict(name="Tottenham", gh=43, ah=24, ga=31, aa=37, form="LWWLW"),
    33: dict(name="Manchester United", gh=31, ah=14, ga=26, aa=44, form="LWLDW"),
    49: dict(name="Chelsea", gh=43, ah=24, ga=34, aa=39, form="WDLWD"),
    34: dict(name="Newcastle", gh=52, ah=25, ga=33, aa=37, form="WLWLW"),
    66: dict(name="Aston Villa", gh=44, ah=24, ga=32, aa=37, form="WWLDW"),
    51: dict(name="Brighton", gh=34, ah=27, ga=21, aa=35, form="DLWDL"),
    48: dict(name="West Ham", gh=32, ah=32, ga=28, aa=42, form="LDLWD"),
}

# A few canned head-to-head results, keyed by an unordered pair.
_H2H: dict[frozenset[int], list[tuple[int, int, int, int]]] = {
    # (home_id, away_id, home_goals, away_goals)
    frozenset({50, 42}): [(50, 42, 1, 0), (42, 50, 3, 1), (50, 42, 4, 1), (42, 50, 0, 1)],
    frozenset({40, 47}): [(40, 47, 4, 2), (47, 40, 1, 2), (40, 47, 2, 1), (47, 40, 0, 1)],
    frozenset({33, 49}): [(33, 49, 2, 1), (49, 33, 1, 1), (33, 49, 1, 2), (49, 33, 4, 1)],
}

_NUM_GAMEWEEKS = 8
# Kick-off slots within a gameweek: (day offset from Saturday, hour, minute).
_SLOTS = [(0, 12, 30), (0, 15, 0), (0, 17, 30), (1, 14, 0), (1, 16, 30)]


def _round_robin(ids: list[int]) -> list[list[tuple[int, int]]]:
    """Circle-method schedule: n-1 rounds, n/2 matches each, balanced home/away."""
    ids = list(ids)
    n = len(ids)
    fixed, rest = ids[0], ids[1:]
    rounds: list[list[tuple[int, int]]] = []
    for r in range(n - 1):
        arr = [fixed] + rest
        pairs = []
        for i in range(n // 2):
            home, away = arr[i], arr[n - 1 - i]
            if r % 2 == 1:  # alternate to balance home/away across the season
                home, away = away, home
            pairs.append((home, away))
        rounds.append(pairs)
        rest = [rest[-1]] + rest[:-1]  # rotate
    return rounds


def _gameweek_saturdays(count: int) -> list[datetime]:
    """Consecutive Saturdays anchored so a few gameweeks are past and a few are
    upcoming relative to today (makes the calendar look alive)."""
    today = datetime.now(timezone.utc).date()
    days_since_sat = (today.weekday() - 5) % 7  # Mon=0 .. Sat=5
    last_sat = today - timedelta(days=days_since_sat)
    gw1 = last_sat - timedelta(weeks=3)
    return [
        datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        for d in (gw1 + timedelta(weeks=i) for i in range(count))
    ]


# Build the fixed schedule once at import time.
_SCHEDULE = _round_robin(list(_TEAMS.keys()))[:_NUM_GAMEWEEKS]
_SATURDAYS = _gameweek_saturdays(_NUM_GAMEWEEKS)


def _round_name(i: int) -> str:
    return f"Gameweek {i + 1}"


def _fixture_date(gw_index: int, slot_index: int) -> str:
    day_off, hour, minute = _SLOTS[slot_index % len(_SLOTS)]
    dt = _SATURDAYS[gw_index] + timedelta(days=day_off, hours=hour, minutes=minute)
    return dt.isoformat()


def _current_gw_index() -> int:
    """First gameweek whose Sunday hasn't fully passed; else the last one."""
    now = datetime.now(timezone.utc)
    for i, sat in enumerate(_SATURDAYS):
        if sat + timedelta(days=2) >= now:  # through end of that weekend
            return i
    return len(_SATURDAYS) - 1


class SampleProvider(FootballDataProvider):
    provider_type = "sample"

    def __init__(self, *args, **kwargs) -> None:  # ignore url/key/logger etc.
        pass

    def _find_id_by_name(self, name: str) -> int:
        needle = name.strip().lower()
        for tid, t in _TEAMS.items():
            if needle in t["name"].lower() or t["name"].lower() in needle:
                return tid
        raise ProviderNotFoundError(f"No sample team matching '{name}'.")

    def get_team(self, name: str, league_id: int | None = None, season: int | None = None) -> ProviderTeam:
        tid = self._find_id_by_name(name)
        return ProviderTeam(id=tid, name=_TEAMS[tid]["name"])

    def get_team_stats(self, team_id: int, season: int, league_id: int) -> ProviderTeamStats:
        t = _TEAMS.get(team_id)
        if not t:
            raise ProviderNotFoundError(f"No sample stats for team {team_id}.")
        return ProviderTeamStats(
            team_id=team_id,
            name=t["name"],
            games_home=19,
            games_away=19,
            goals_for_home=t["gh"],
            goals_against_home=t["ah"],
            goals_for_away=t["ga"],
            goals_against_away=t["aa"],
            recent_form=list(t["form"])[::-1],  # most-recent-first
        )

    def get_h2h(self, team1_id: int, team2_id: int, limit: int = 10) -> list[ProviderH2HMatch]:
        rows = _H2H.get(frozenset({team1_id, team2_id}), [])
        return [
            ProviderH2HMatch(home_team_id=h, away_team_id=a, home_goals=hg, away_goals=ag)
            for (h, a, hg, ag) in rows[:limit]
        ]

    def _fixtures_for_gw(self, gw_index: int, league_id: int, season: int) -> list[ProviderFixture]:
        out: list[ProviderFixture] = []
        for slot, (home_id, away_id) in enumerate(_SCHEDULE[gw_index]):
            out.append(
                ProviderFixture(
                    id=100_000 + gw_index * 100 + slot,
                    league_id=league_id,
                    season=season,
                    round=_round_name(gw_index),
                    date=_fixture_date(gw_index, slot),
                    status="NS",
                    home=ProviderTeam(id=home_id, name=_TEAMS[home_id]["name"]),
                    away=ProviderTeam(id=away_id, name=_TEAMS[away_id]["name"]),
                )
            )
        return out

    def get_fixtures(self, league_id: int, season: int, round: str | None = None) -> list[ProviderFixture]:
        if round is None:
            gw = _current_gw_index()
            return self._fixtures_for_gw(gw, league_id, season)
        for i in range(len(_SCHEDULE)):
            if _round_name(i) == round:
                return self._fixtures_for_gw(i, league_id, season)
        return []

    def get_rounds(self, league_id: int, season: int) -> list[ProviderRound]:
        rounds: list[ProviderRound] = []
        for i, sat in enumerate(_SATURDAYS):
            rounds.append(
                ProviderRound(
                    name=_round_name(i),
                    start_date=self._fixtures_for_gw(i, league_id, season)[0].date,
                    end_date=(sat + timedelta(days=1, hours=16, minutes=30)).isoformat(),
                    fixture_count=len(_SCHEDULE[i]),
                )
            )
        return rounds

    def get_leagues(self) -> list[ProviderLeague]:
        return [
            ProviderLeague(id=39, name="Premier League", country="England", season=2023),
            ProviderLeague(id=140, name="La Liga", country="Spain", season=2023),
            ProviderLeague(id=135, name="Serie A", country="Italy", season=2023),
        ]
