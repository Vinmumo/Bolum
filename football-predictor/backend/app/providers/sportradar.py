"""Sportradar Soccer API adapter — SCAFFOLD.

Docs:  https://developer.sportradar.com/soccer/reference/soccer-overview
Base:  https://api.sportradar.com/soccer/{access_level}/v4/{language}
       (e.g. .../soccer/trial/v4/en  for a trial key)
Auth:  api_key query param  (Sportradar issues trial keys free; production is paid)

Status: HTTP plumbing (auth, caching, throttling, usage logging, errors) is DONE.
The five data methods raise until completed — the consensus aggregator skips a
provider that raises, so activating this early is safe (it just won't contribute).

Why scaffolded: Sportradar production data is enterprise/paid and its v4 response
shapes (and the id-based competitor/season model) can't be verified here without a
key. Complete the mappings against a live trial response.

To finish (Sportradar is very id-driven — you resolve competitors & seasons by id):
1. get_team: GET /competitors/search (or resolve from a season's competitors).
2. get_team_stats: GET /seasons/{season_id}/competitors/{competitor_id}/statistics.
3. get_fixtures / get_rounds: GET /seasons/{season_id}/schedules ; group by round.
4. get_h2h: GET /competitors/{c1}/versus/{c2}/matches.
5. Map Bolum's canonical (API-Football) league ids to Sportradar season/competition
   ids in LEAGUE_MAP.
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

# canonical (API-Football) league id -> Sportradar season/competition id. FILL IN.
LEAGUE_MAP: dict[int, str] = {
    # 39: "sr:season:105353",  # example shape — verify against your Sportradar plan
}

_TODO = (
    "Sportradar adapter is scaffolded — implement this method against a live "
    "trial response. See docs/ADDING_A_PROVIDER.md."
)


class SportradarProvider(FootballDataProvider):
    provider_type = "sportradar"

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        auth_header: str = "x-api-key",
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
        """Ready-to-use GET. Sportradar auth is the `api_key` query param."""
        if not self.api_key:
            raise ProviderAuthError("No Sportradar key configured.")
        params = {**params, "api_key": self.api_key}
        key = f"sportradar:{self.provider_id}:{path}?{sorted(params.items())}"
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
                raise ProviderRateLimitError("Sportradar rate limit reached.")
            if status in (401, 403):
                self._record(path, status, False)
                raise ProviderAuthError("Sportradar rejected the key.")
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            self._record(path, status, False)
            raise ProviderError(f"Sportradar request failed: {exc}") from exc
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
