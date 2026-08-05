"""API-Football (v3) adapter.

Docs:  https://www.api-football.com/documentation-v3
Base:  https://v3.football.api-sports.io
Auth:  header  x-apisports-key: <key>

Every outbound call goes through `_get`, which adds caching (to stay under the
rate limit), throttling, usage logging, and error normalisation. The API key is
passed in already-decrypted by the registry and is NEVER logged.
"""
from __future__ import annotations

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


class ApiFootballProvider(FootballDataProvider):
    provider_type = "api_football"

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        auth_header: str = "x-apisports-key",
        *,
        provider_id: int | None = None,
        usage_logger: UsageLogger | None = None,
        min_interval: float = 1.0,
        ttl_stats: int = 6 * 3600,
        ttl_fixtures: int = 3600,
        ttl_h2h: int = 6 * 3600,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.auth_header = auth_header
        self.provider_id = provider_id
        self._log = usage_logger
        self.min_interval = min_interval
        self.ttl_stats = ttl_stats
        self.ttl_fixtures = ttl_fixtures
        self.ttl_h2h = ttl_h2h
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # HTTP core
    # ------------------------------------------------------------------ #
    def _cache_key(self, endpoint: str, params: dict) -> str:
        parts = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"apifootball:{self.provider_id}:{endpoint}?{parts}"

    def _get(self, endpoint: str, params: dict, ttl: int) -> list[dict]:
        if not self.api_key:
            raise ProviderAuthError(
                "No API-Football key configured. Set API_FOOTBALL_KEY in .env "
                "or run in sample mode."
            )

        key = self._cache_key(endpoint, params)
        cached = cache.get(key)
        if cached is not None:
            return cached  # cache hit — no outbound call, no usage logged

        cache.throttle(f"provider:{self.provider_id}", self.min_interval)

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {self.auth_header: self.api_key}
        status: int | None = None
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=self.timeout)
            status = resp.status_code
            if status == 429:
                self._record(endpoint, status, False)
                raise ProviderRateLimitError("API-Football rate limit reached.")
            if status in (401, 403):
                self._record(endpoint, status, False)
                raise ProviderAuthError("API-Football rejected the API key.")
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            self._record(endpoint, status, False)
            raise ProviderError(f"API-Football request failed: {exc}") from exc

        # API-Football signals quota problems inside a 200 body too.
        errors = payload.get("errors")
        if errors:
            self._record(endpoint, status, False)
            text = str(errors).lower()
            if "rate" in text or "limit" in text or "requests" in text:
                raise ProviderRateLimitError(f"API-Football limit: {errors}")
            raise ProviderError(f"API-Football error: {errors}")

        self._record(endpoint, status, True)
        data = payload.get("response", [])
        cache.set(key, data, ttl)
        return data

    def _record(self, endpoint: str, status: int | None, success: bool) -> None:
        if self._log is not None:
            try:
                self._log(endpoint, status, success)
            except Exception:  # logging must never break a request
                pass

    # ------------------------------------------------------------------ #
    # Interface
    # ------------------------------------------------------------------ #
    def get_team(self, name: str, league_id: int | None = None, season: int | None = None) -> ProviderTeam:
        # API-Football's /teams `search` cannot be combined with league/season;
        # team ids are global, so a name search alone is enough.
        params: dict = {"search": name}
        data = self._get("teams", params, self.ttl_stats)
        if not data:
            raise ProviderNotFoundError(f"No team found matching '{name}'.")
        team = data[0]["team"]
        return ProviderTeam(id=team["id"], name=team["name"], logo=team.get("logo"))

    def get_team_stats(self, team_id: int, season: int, league_id: int) -> ProviderTeamStats:
        params = {"team": team_id, "season": season, "league": league_id}
        data = self._get("teams/statistics", params, self.ttl_stats)
        if not data:
            raise ProviderNotFoundError(f"No stats for team {team_id} in season {season}.")

        s = data  # /teams/statistics returns an object, not a list
        played = s["fixtures"]["played"]
        goals_for = s["goals"]["for"]["total"]
        goals_against = s["goals"]["against"]["total"]
        form_str = s.get("form") or ""
        recent_form = list(form_str)[-6:][::-1]  # most-recent-first

        return ProviderTeamStats(
            team_id=team_id,
            name=s["team"]["name"],
            logo=s["team"].get("logo"),
            games_home=played.get("home", 0) or 0,
            games_away=played.get("away", 0) or 0,
            goals_for_home=goals_for.get("home", 0) or 0,
            goals_against_home=goals_against.get("home", 0) or 0,
            goals_for_away=goals_for.get("away", 0) or 0,
            goals_against_away=goals_against.get("away", 0) or 0,
            recent_form=recent_form,
        )

    def get_h2h(self, team1_id: int, team2_id: int, limit: int = 10) -> list[ProviderH2HMatch]:
        # NB: the `last`/`next` params require a paid plan, so we fetch all
        # meetings and slice to the most recent `limit` client-side.
        params = {"h2h": f"{team1_id}-{team2_id}"}
        data = self._get("fixtures/headtohead", params, self.ttl_h2h)
        out: list[ProviderH2HMatch] = []
        for f in data:
            goals = f.get("goals", {})
            if goals.get("home") is None or goals.get("away") is None:
                continue  # unplayed
            out.append(
                ProviderH2HMatch(
                    home_team_id=f["teams"]["home"]["id"],
                    away_team_id=f["teams"]["away"]["id"],
                    home_goals=goals["home"],
                    away_goals=goals["away"],
                    date=f.get("fixture", {}).get("date"),
                )
            )
        out.sort(key=lambda m: m.date or "", reverse=True)  # most recent first
        return out[:limit]

    def get_fixtures(self, league_id: int, season: int, round: str | None = None) -> list[ProviderFixture]:
        params: dict = {"league": league_id, "season": season}
        if round:
            params["round"] = round
        else:
            params["next"] = 15  # upcoming fixtures when no round specified
        data = self._get("fixtures", params, self.ttl_fixtures)
        return [self._to_fixture(f, league_id, season) for f in data]

    def get_rounds(self, league_id: int, season: int) -> list[ProviderRound]:
        # One (cached) call for the whole season, grouped into matchdays by round.
        params = {"league": league_id, "season": season}
        data = self._get("fixtures", params, self.ttl_fixtures)
        groups: dict[str, list[str]] = {}
        for f in data:
            name = f.get("league", {}).get("round") or "Fixtures"
            date = f.get("fixture", {}).get("date")
            groups.setdefault(name, []).append(date)
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

    def get_leagues(self) -> list[ProviderLeague]:
        data = self._get("leagues", {}, self.ttl_stats)
        out: list[ProviderLeague] = []
        for item in data:
            league = item["league"]
            country = item.get("country", {}).get("name", "")
            seasons = item.get("seasons", [])
            current = next((s["year"] for s in seasons if s.get("current")), None)
            out.append(
                ProviderLeague(
                    id=league["id"], name=league["name"], country=country, season=current
                )
            )
        return out

    @staticmethod
    def _to_fixture(f: dict, league_id: int, season: int) -> ProviderFixture:
        fx = f["fixture"]
        teams = f["teams"]
        goals = f.get("goals", {})
        return ProviderFixture(
            id=fx["id"],
            league_id=league_id,
            season=season,
            round=f.get("league", {}).get("round"),
            date=fx.get("date"),
            status=fx.get("status", {}).get("short", "NS"),
            home=ProviderTeam(
                id=teams["home"]["id"], name=teams["home"]["name"], logo=teams["home"].get("logo")
            ),
            away=ProviderTeam(
                id=teams["away"]["id"], name=teams["away"]["name"], logo=teams["away"].get("logo")
            ),
            home_goals=goals.get("home"),
            away_goals=goals.get("away"),
        )
