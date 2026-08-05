"""football-data.org (v4) adapter — a free, real second data source.

Docs:  https://docs.football-data.org/
Base:  https://api.football-data.org/v4
Auth:  header  X-Auth-Token: <token>   (free token at football-data.org/client/register)

Notes / design:
- **League-id translation.** Bolum stores API-Football league ids as the
  canonical id in the League table. football-data uses different competition ids,
  so this adapter translates via `LEAGUE_MAP` (canonical -> football-data). Add a
  row there to support a new competition.
- **Stats come from the standings** endpoint, which conveniently returns separate
  HOME and AWAY tables (exactly the home/away goal split the model needs), plus a
  recent-form string.
- **H2H** returns empty for now (football-data's H2H needs a specific match id);
  the model handles missing H2H gracefully. See docs/ADDING_A_PROVIDER.md to extend.
- Free tier is ~10 requests/minute — caching + throttling keep us under it.
"""
from __future__ import annotations

import re
from collections.abc import Callable

import httpx

from app.providers.base import (
    FootballDataProvider,
    ProviderAuthError,
    ProviderError,
    ProviderFixture,
    ProviderH2HMatch,
    ProviderLeague,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderRound,
    ProviderTeam,
    ProviderTeamStats,
)
from app.services.cache import cache

UsageLogger = Callable[[str, int | None, bool], None]

# canonical (API-Football) league id -> football-data competition id
LEAGUE_MAP: dict[int, int] = {
    39: 2021,   # Premier League
    140: 2014,  # La Liga
    135: 2019,  # Serie A
    78: 2002,   # Bundesliga
    61: 2015,   # Ligue 1
    2: 2001,    # Champions League
    40: 2016,   # Championship
    88: 2003,   # Eredivisie
    94: 2017,   # Primeira Liga
    71: 2013,   # Brasileirão
}


def _matchday_from_round(round_name: str | None) -> int | None:
    if not round_name:
        return None
    m = re.search(r"(\d+)", round_name)
    return int(m.group(1)) if m else None


class FootballDataOrgProvider(FootballDataProvider):
    provider_type = "football_data_org"

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        auth_header: str = "X-Auth-Token",
        *,
        provider_id: int | None = None,
        usage_logger: UsageLogger | None = None,
        min_interval: float = 6.0,  # free tier ~10/min -> be gentle
        ttl_stats: int = 6 * 3600,
        ttl_fixtures: int = 3600,
        ttl_h2h: int = 6 * 3600,
        timeout: float = 15.0,
        **_: object,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.auth_header = auth_header or "X-Auth-Token"
        self.provider_id = provider_id
        self._log = usage_logger
        # Free tier is ~10 req/min; never go faster than one call per 6s even if
        # the global PROVIDER_MIN_INTERVAL is lower.
        self.min_interval = max(min_interval, 6.0)
        self.ttl_stats = ttl_stats
        self.ttl_fixtures = ttl_fixtures
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    def _competition(self, league_id: int) -> int:
        comp = LEAGUE_MAP.get(league_id)
        if comp is None:
            raise ProviderNotFoundError(
                f"football-data.org has no mapping for league {league_id}. "
                f"Add it to LEAGUE_MAP in football_data_org.py."
            )
        return comp

    def _get(self, path: str, params: dict, ttl: int) -> dict:
        if not self.api_key:
            raise ProviderAuthError("No football-data.org token configured.")

        parts = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        key = f"footballdata:{self.provider_id}:{path}?{parts}"
        cached = cache.get(key)
        if cached is not None:
            return cached

        cache.throttle(f"provider:{self.provider_id}", self.min_interval)
        url = f"{self.base_url}/{path.lstrip('/')}"
        status: int | None = None
        try:
            resp = httpx.get(
                url, params=params, headers={self.auth_header: self.api_key}, timeout=self.timeout
            )
            status = resp.status_code
            if status == 429:
                self._record(path, status, False)
                raise ProviderRateLimitError("football-data.org rate limit reached.")
            if status in (401, 403):
                self._record(path, status, False)
                raise ProviderAuthError("football-data.org rejected the token.")
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            self._record(path, status, False)
            raise ProviderError(f"football-data.org request failed: {exc}") from exc

        self._record(path, status, True)
        cache.set(key, payload, ttl)
        return payload

    def _record(self, endpoint: str, status: int | None, success: bool) -> None:
        if self._log is not None:
            try:
                self._log(endpoint, status, success)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    def get_team(self, name: str, league_id: int | None = None, season: int | None = None) -> ProviderTeam:
        comp = self._competition(league_id or 39)
        params = {"season": season} if season else {}
        data = self._get(f"competitions/{comp}/teams", params, self.ttl_stats)
        needle = name.strip().lower()
        # Best-match scoring. We deliberately avoid loose reverse-substring
        # matches on the short TLA (e.g. Chelsea's "CHE" is a substring of
        # "manCHEster") — those cause wrong-team resolution.
        best, best_score = None, 0
        for t in data.get("teams", []):
            nm = (t.get("name") or "").lower()
            short = (t.get("shortName") or "").lower()
            tla = (t.get("tla") or "").lower()
            if needle in (nm, short, tla):
                score = 4
            elif nm.startswith(needle) or (short and short.startswith(needle)):
                score = 3
            elif needle in nm or (short and needle in short):
                score = 2
            elif short and short in needle:
                score = 1
            else:
                score = 0
            if score > best_score:
                best, best_score = t, score
        if best is None:
            raise ProviderNotFoundError(f"No football-data team matching '{name}'.")
        return ProviderTeam(id=best["id"], name=best["name"], logo=best.get("crest"))

    def get_team_stats(self, team_id: int, season: int, league_id: int) -> ProviderTeamStats:
        comp = self._competition(league_id)
        data = self._get(f"competitions/{comp}/standings", {"season": season}, self.ttl_stats)

        tables = {s.get("type"): s.get("table", []) for s in data.get("standings", [])}
        home_row = _find_row(tables.get("HOME", []), team_id)
        away_row = _find_row(tables.get("AWAY", []), team_id)
        total_row = _find_row(tables.get("TOTAL", []), team_id)
        if not (home_row and away_row):
            raise ProviderNotFoundError(
                f"No football-data standings row for team {team_id} (season {season})."
            )

        name = (total_row or home_row)["team"]["name"]
        logo = (total_row or home_row)["team"].get("crest")
        form_str = (total_row or {}).get("form") or ""
        recent_form = [c for c in form_str.replace(",", "") if c in "WDL"][-6:][::-1]

        return ProviderTeamStats(
            team_id=team_id,
            name=name,
            logo=logo,
            games_home=home_row.get("playedGames", 0) or 0,
            games_away=away_row.get("playedGames", 0) or 0,
            goals_for_home=home_row.get("goalsFor", 0) or 0,
            goals_against_home=home_row.get("goalsAgainst", 0) or 0,
            goals_for_away=away_row.get("goalsFor", 0) or 0,
            goals_against_away=away_row.get("goalsAgainst", 0) or 0,
            recent_form=recent_form,
        )

    def get_h2h(self, team1_id: int, team2_id: int, limit: int = 10) -> list[ProviderH2HMatch]:
        # football-data H2H requires a specific match id; skipped for now.
        return []

    def get_fixtures(self, league_id: int, season: int, round: str | None = None) -> list[ProviderFixture]:
        comp = self._competition(league_id)
        params: dict = {"season": season}
        matchday = _matchday_from_round(round)
        if matchday is not None:
            params["matchday"] = matchday
        data = self._get(f"competitions/{comp}/matches", params, self.ttl_fixtures)
        return [self._to_fixture(m, league_id, season) for m in data.get("matches", [])]

    def get_rounds(self, league_id: int, season: int) -> list[ProviderRound]:
        comp = self._competition(league_id)
        data = self._get(f"competitions/{comp}/matches", {"season": season}, self.ttl_fixtures)
        groups: dict[int, list[str]] = {}
        for m in data.get("matches", []):
            md = m.get("matchday")
            if md is None:
                continue
            groups.setdefault(md, []).append(m.get("utcDate"))
        rounds: list[ProviderRound] = []
        for md in sorted(groups):
            dates = sorted(d for d in groups[md] if d)
            rounds.append(
                ProviderRound(
                    name=f"Gameweek {md}",
                    start_date=dates[0] if dates else None,
                    end_date=dates[-1] if dates else None,
                    fixture_count=len(groups[md]),
                )
            )
        return rounds

    def get_leagues(self) -> list[ProviderLeague]:
        data = self._get("competitions", {}, self.ttl_stats)
        out: list[ProviderLeague] = []
        for c in data.get("competitions", []):
            out.append(
                ProviderLeague(
                    id=c["id"],
                    name=c["name"],
                    country=c.get("area", {}).get("name", ""),
                    season=(c.get("currentSeason") or {}).get("startDate", "")[:4] or None,
                )
            )
        return out

    @staticmethod
    def _to_fixture(m: dict, league_id: int, season: int) -> ProviderFixture:
        score = (m.get("score") or {}).get("fullTime") or {}
        return ProviderFixture(
            id=m["id"],
            league_id=league_id,
            season=season,
            round=f"Gameweek {m['matchday']}" if m.get("matchday") else None,
            date=m.get("utcDate"),
            status=m.get("status", "SCHEDULED"),
            home=ProviderTeam(
                id=m["homeTeam"]["id"], name=m["homeTeam"]["name"], logo=m["homeTeam"].get("crest")
            ),
            away=ProviderTeam(
                id=m["awayTeam"]["id"], name=m["awayTeam"]["name"], logo=m["awayTeam"].get("crest")
            ),
            home_goals=score.get("home"),
            away_goals=score.get("away"),
        )


def _find_row(table: list[dict], team_id: int) -> dict | None:
    for row in table:
        if row.get("team", {}).get("id") == team_id:
            return row
    return None
