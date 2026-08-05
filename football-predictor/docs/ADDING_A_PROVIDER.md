# Adding a data provider

Two steps: write an adapter class, register its slug. Then add the provider as a
row from the admin UI — no redeploy.

## Multi-provider consensus (important)

**Every _active_ provider is averaged into the consensus prediction** (see
`services/aggregator.py`). Enable two or more (e.g. API-Football +
football-data.org) and the fixture page shows the averaged headline plus each
source's own numbers. A provider that errors (rate limit, team not found,
unfinished scaffold) is skipped and listed under `meta.providers_failed` — it
never breaks the prediction. The **first** active provider also serves the
single-source endpoints (fixtures + calendar), since averaging fixtures makes no
sense.

### League-id translation convention

Each API has its own league ids **and** team ids. Bolum stores **API-Football's
league ids as the canonical id** in the `League` table (e.g. 39 = Premier
League). Non-API-Football adapters translate that canonical id to their own via a
`LEAGUE_MAP` in the adapter (see `football_data_org.py`: `39 -> 2021`). Team
resolution is by **name** (`get_team`), so it's provider-agnostic and needs no map.

When you write a new adapter, add a `LEAGUE_MAP` from canonical id → your API's id.

## Where to get keys

| API | Sign up | Free for dev? | Auth header/param |
|-----|---------|---------------|-------------------|
| API-Football | api-football.com | ✅ 100 req/day | `x-apisports-key` |
| football-data.org | football-data.org/client/register | ✅ ~10 req/min, top leagues | `X-Auth-Token` |
| Sportmonks | sportmonks.com | ⚠️ top leagues paid | `Authorization` / `api_token` |
| Sportradar | developer.sportradar.com | ⚠️ trial only, prod paid | `api_key` (query) |

Provider keys are entered in the **admin UI** (stored encrypted), not in `.env`.
(Exception: `API_FOOTBALL_KEY` in `.env` is only used to *seed* a provider row on
a fresh DB. Once providers exist, the admin UI is the source of truth.)

### API-Football free-tier gotchas (learned the hard way)

The adapter already handles these, but for reference:
- **Seasons** are capped at **2023** on the free plan — use `DEFAULT_SEASON=2023`.
- The `/teams` **`search`** param **cannot** be combined with `league`/`season`
  (team ids are global anyway, so we search by name alone).
- `/fixtures/headtohead` **`last`/`next`** params require a **paid** plan — we
  fetch all meetings and slice to the most recent client-side.
- Free plan is **100 requests/day**. Caching (stats 6h, fixtures 1h, H2H 6h) keeps
  normal browsing well under it; watch **Admin → Usage**.

## Provided adapters

- `api_football.py` — complete.
- `football_data_org.py` — complete (free key; stats via the standings endpoint).
- `sportmonks.py`, `sportradar.py` — **scaffolds**: HTTP/auth/caching done, the
  five data methods raise until you complete them against a live (paid) response.
  Safe to activate early — the aggregator just skips them until finished.

## 1. Write the adapter

Create `backend/app/providers/<yourprovider>.py`. Subclass
`FootballDataProvider` and implement the five methods, translating the vendor's
JSON into the normalised DTOs from `providers/base.py`
(`ProviderTeam`, `ProviderTeamStats`, `ProviderH2HMatch`, `ProviderFixture`,
`ProviderLeague`).

```python
from app.providers.base import FootballDataProvider, ProviderTeam, ProviderTeamStats, ...

class FootballDataOrgProvider(FootballDataProvider):
    provider_type = "football_data_org"

    def __init__(self, base_url, api_key, auth_header="X-Auth-Token", *,
                 provider_id=None, usage_logger=None, min_interval=1.0,
                 ttl_stats=21600, ttl_fixtures=3600, ttl_h2h=21600, **kwargs):
        # store what you need; accept the same kwargs the registry passes
        ...

    def get_team(self, name, league_id=None, season=None): ...
    def get_team_stats(self, team_id, season, league_id): ...
    def get_h2h(self, team1_id, team2_id, limit=10): ...
    def get_fixtures(self, league_id, season, round=None): ...
    def get_leagues(self): ...
```

Use `app.providers.api_football.ApiFootballProvider` as the reference — copy its
`_get` helper for **caching + throttling + usage logging + error normalisation**.
That is the part that keeps you under rate limits, so don't skip it.

### Contract you must honour

- Raise the typed errors from `base.py` so the API maps them correctly:
  `ProviderRateLimitError` → HTTP 429 (friendly UI message),
  `ProviderAuthError` → 502, `ProviderNotFoundError` → 404.
- Only count **real outbound calls** via `usage_logger(endpoint, status, success)`.
  Cache hits must not call it.
- `recent_form` is a list of `"W"/"D"/"L"`, **most-recent-first**.
- Home/away goal splits go in the four `goals_*_home/away` + `games_*` fields.
- **Never log the full API key.** It arrives already decrypted; keep it in memory.

## 2. Register the slug

In `backend/app/providers/registry.py`, add one line:

```python
from app.providers.football_data_org import FootballDataOrgProvider

PROVIDER_CLASSES = {
    "api_football": ApiFootballProvider,
    "sample": SampleProvider,
    "football_data_org": FootballDataOrgProvider,   # ← add
}
```

## 3. Add it in the admin UI

Go to `/admin` → **Providers** → **Add provider**:

- **Type**: the slug you registered (`football_data_org`).
- **Base URL**, **Auth header** (e.g. `X-Auth-Token`), **API key** (stored
  encrypted), **Active**.

Set it Active (and disable the old one if you're switching). Done — the registry
picks it up on the next request.

## 4. Test it

Add a test mirroring `app/tests/test_predictor.py`, or hit
`GET /api/teams/search?name=Arsenal` and `POST /api/predictions/predict` while
the new provider is the active one.
