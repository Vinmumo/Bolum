"""Sportmonks Football API adapter — SCAFFOLD.

Docs:  https://docs.sportmonks.com/football
Base:  https://api.sportmonks.com/v3/football
Auth:  api_token query param  (or  Authorization: <token>  header)

Status: the HTTP plumbing (auth, caching, throttling, usage logging, error
mapping) is DONE. The five data methods raise NotImplemented-style errors until
you complete them — the consensus aggregator skips a provider that raises, so
activating this before it's finished is safe (it just won't contribute).

Why scaffolded: Sportmonks' top-league data is on a paid plan, so its exact
response shapes can't be verified here without a key. Fill in the field mappings
against a live response — see docs/ADDING_A_PROVIDER.md § Sportmonks.

To finish:
1. Implement get_team via GET /teams/search/{name} (or /teams filtered by season).
2. get_team_stats: GET /statistics/seasons/teams/{teamId} (season-scoped), then
   map the home/away goal split into ProviderTeamStats.
3. get_fixtures / get_rounds: GET /fixtures with `?filters=fixtureLeagues:{id}`
   and a round include; group by round/stage for gameweeks.
4. get_h2h: GET /fixtures/head-to-head/{team1}/{team2}.
5. Map Bolum's canonical (API-Football) league ids to Sportmonks league ids in
   LEAGUE_MAP below.
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
    ProviderRateLimitError,
    ProviderRound,
    ProviderTeam,
    ProviderTeamStats,
)
from app.services.cache import cache

UsageLogger = Callable[[str, int | None, bool], None]

# canonical (API-Football) league id -> Sportmonks league id. FILL IN.
LEAGUE_MAP: dict[int, int] = {
    39: 8,  # Premier League (verify against your Sportmonks plan)
}

_TODO = (
    "Sportmonks adapter is scaffolded — implement this method against a live "
    "response. See docs/ADDING_A_PROVIDER.md."
)


class SportmonksProvider(FootballDataProvider):
    provider_type = "sportmonks"

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        auth_header: str = "Authorization",
        *,
        provider_id: int | None = None,
        usage_logger: UsageLogger | None = None,
        min_interval: float = 1.0,
        timeout: float = 15.0,
        **_: object,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.auth_header = auth_header
        self.provider_id = provider_id
        self._log = usage_logger
        self.min_interval = min_interval
        self.timeout = timeout

    def _get(self, path: str, params: dict, ttl: int) -> dict:
        """Ready-to-use GET. Sportmonks auth is the `api_token` query param."""
        if not self.api_key:
            raise ProviderAuthError("No Sportmonks token configured.")
        params = {**params, "api_token": self.api_key}
        key = f"sportmonks:{self.provider_id}:{path}?{sorted(params.items())}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        cache.throttle(f"provider:{self.provider_id}", self.min_interval)
        status: int | None = None
        try:
            resp = httpx.get(f"{self.base_url}/{path.lstrip('/')}", params=params, timeout=self.timeout)
            status = resp.status_code
            if status == 429:
                self._record(path, status, False)
                raise ProviderRateLimitError("Sportmonks rate limit reached.")
            if status in (401, 403):
                self._record(path, status, False)
                raise ProviderAuthError("Sportmonks rejected the token.")
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            self._record(path, status, False)
            raise ProviderError(f"Sportmonks request failed: {exc}") from exc
        self._record(path, status, True)
        cache.set(key, payload, ttl)
        return payload

    def _record(self, endpoint: str, status: int | None, success: bool) -> None:
        if self._log is not None:
            try:
                self._log(endpoint, status, success)
            except Exception:
                pass

    def get_team(self, name: str, league_id: int | None = None, season: int | None = None) -> ProviderTeam:
        raise ProviderError(_TODO)

    def get_team_stats(self, team_id: int, season: int, league_id: int) -> ProviderTeamStats:
        raise ProviderError(_TODO)

    def get_h2h(self, team1_id: int, team2_id: int, limit: int = 10) -> list[ProviderH2HMatch]:
        return []

    def get_fixtures(self, league_id: int, season: int, round: str | None = None) -> list[ProviderFixture]:
        raise ProviderError(_TODO)

    def get_rounds(self, league_id: int, season: int) -> list[ProviderRound]:
        raise ProviderError(_TODO)

    def get_leagues(self) -> list[ProviderLeague]:
        raise ProviderError(_TODO)
