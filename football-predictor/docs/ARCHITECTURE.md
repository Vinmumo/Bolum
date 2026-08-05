# Architecture

How the pieces fit together. Written for future-you, not end users.

## 10,000-ft view

```
┌────────────┐        HTTP /api        ┌──────────────────────────────┐
│  Vue SPA   │  ───────────────────▶   │  FastAPI backend             │
│ (frontend) │  ◀───────────────────   │                              │
└────────────┘   JSON                  │  routers → services → model  │
                                        │              │               │
                                        │              ▼               │
                                        │        ProviderRegistry      │
                                        │              │               │
                                        │              ▼               │
                                        │   FootballDataProvider(s)    │
                                        │   ├─ api_football (HTTP)     │
                                        │   └─ sample (offline canned) │
                                        └───────────────┬──────────────┘
                                                        │
                                              external football API
```

The golden rule: **nothing above the provider layer knows which API the data
came from.** Routers and services speak in normalised DTOs
(`providers/base.py`); only the concrete provider classes touch a vendor's JSON.

## Request lifecycle (a prediction)

1. `POST /api/predictions/predict` hits `api/routers/predictions.py`.
2. `resolve_league_season` fills league/season from the active `League` row (or
   config defaults).
3. `ProviderRegistry.get_active_provider()` reads the first active `Provider`
   row, decrypts its key, and instantiates the matching adapter class.
4. `services/predictor.py` orchestrates:
   - `provider.get_team()` ×2 → team ids
   - `provider.get_team_stats()` ×2 → season goal splits
   - `services/form_analysis.py` → form multipliers
   - `provider.get_h2h()` → `services/h2h_analysis.py` → H2H summary + multipliers
   - `services/poisson_model.py` → expected goals → full market probabilities
5. The result is logged to the `predictions` table and returned as JSON.

## Layers

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| API | `app/api/routers` | HTTP shape, validation, auth, error→status mapping |
| Schemas | `app/schemas` | Pydantic request/response contracts |
| Services | `app/services` | Pure-ish business logic: the model, form, H2H, orchestration |
| Providers | `app/providers` | Adapters to external APIs + the registry |
| Models | `app/models` | SQLAlchemy tables |
| Core | `app/core` | Settings + security (auth, encryption) |
| DB | `app/db` | Engine/session, declarative base, seed |

## Key design decisions

- **Provider abstraction (adapter pattern).** `FootballDataProvider` is the
  interface; `PROVIDER_CLASSES` in `providers/registry.py` maps a `provider_type`
  slug to a class. Providers are *rows in the DB*, added from the admin UI — no
  redeploy to add one. See [ADDING_A_PROVIDER.md](ADDING_A_PROVIDER.md).
- **Leagues are data, not code.** The `League` table drives everything; the UI
  and API default to the first active league. See [ADDING_A_LEAGUE.md](ADDING_A_LEAGUE.md).
- **Secrets encrypted at rest.** Provider API keys are Fernet-encrypted with a
  key derived from `SECRET_KEY` (`core/security.py`). They are never logged in
  full (`mask_key`) and never returned by the API.
- **Caching + throttling.** `services/cache.py` is an in-process TTL cache. The
  API-Football adapter caches every call (stats 6h, fixtures 1h, H2H 6h) and
  spaces outbound calls by `PROVIDER_MIN_INTERVAL`. Cache hits are *not* logged
  to `api_usage_logs`, so that table reflects real quota consumption.
- **The model is a pure function.** `poisson_model.py` has no I/O, so the maths
  is unit-tested like a calculator (`app/tests/test_poisson_model.py`).
- **Offline sample mode.** With no `API_FOOTBALL_KEY`, the seed installs the
  `sample` provider so the whole stack runs end-to-end with canned PL data.

## Auth

Single admin user; credentials in `.env`. `POST /api/admin/login` (OAuth2
password form) returns a JWT; `require_admin` guards every `/api/admin/*` route.
No public signup — public visitors need no account.

## Provider roles (since the 2026 upgrade)

- Providers have a `priority` (lower = preferred). The **lowest-priority active**
  provider serves single-source endpoints: fixtures, calendar, seasons,
  standings, point-in-time stats. ALL active providers feed the prediction
  consensus.
- **football-data.org is primary** (priority 1): its free tier carries the
  *current* season (fixtures + standings), which API-Football's free tier does
  not (capped at 2023 → priority 2, consensus duty for seasons it can see).
- Early-season fallback: while the current season's table is empty, the
  football-data adapter silently uses last season's stats for predictions.
- Backtesting: `services/backtest.py` + `backtest_results` table + `/api/backtest/*`.
- Odds: `services/odds.py` + `/api/odds/totals` (The Odds API, dormant without
  `THE_ODDS_API_KEY`; league→sport-key map in `SPORT_KEYS`).

## Where state lives

- **SQLite** (dev) via `DATABASE_URL` — swap to Postgres by changing that one
  env var. Tables: `providers`, `leagues`, `teams`, `predictions`,
  `api_usage_logs`.
- **In-process cache** — ephemeral; fine for a single-process personal tool.
  For multi-process, replace `TTLCache` with Redis (the interface is tiny).
