# ⚽ Bolum — Football Predictor

A personal football analysis tool. Bolum predicts fixtures with a
**Poisson + Dixon-Coles** model, pulls data from **multiple football APIs at
once** (weighted consensus), compares its overs/unders against **live bookmaker
odds**, and — most importantly — **backtests itself** against past seasons using
only the data that was available at the time.

> For analysis and curiosity only — **not betting advice**.

![stack](https://img.shields.io/badge/backend-FastAPI-009688) ![stack](https://img.shields.io/badge/frontend-Vue_3-42b883) ![stack](https://img.shields.io/badge/db-SQLite%E2%86%92Postgres-informational) ![stack](https://img.shields.io/badge/model-Poisson_%2B_Dixon--Coles-8b5cf6)

## What it does

- **Upcoming season front and centre** — landing page leads with the current
  season's gameweek calendar and countdown to kick-off.
- **Fixture predictions** — expected goals, win/draw/loss meter, overs/unders at
  **1.5 / 2.5 / 3.5**, BTTS, likely scorelines, recent form and head-to-head.
- **Multi-API consensus** — every *active* data provider contributes; the
  headline is a **weighted average** with each source's own numbers shown side
  by side. Adding a provider is an admin-UI action, not a redeploy.
- **Model vs market** — with a (free) The Odds API key, each fixture shows the
  bookmakers' implied over/under probabilities next to the model's, with the
  edge per goal line.
- **Honest backtesting** — replay any past gameweek and see what Bolum *would
  have* predicted using only the league table as it stood back then. Hit rates
  and calibration accumulate per season; finished gameweeks replay
  automatically in the background.
- **Past seasons** — final tables plus the backtest dashboard, back to 2021.

## Quick start

Two terminals. Python 3.10+ (3.11+ recommended) and Node 18+.

**Terminal 1 — backend** (http://127.0.0.1:8000, API docs at `/docs`):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # then fill in keys — see below
uvicorn app.main:app --reload
```

**Terminal 2 — frontend** (http://localhost:5173, proxies `/api` to the backend):

```bash
cd frontend
npm install
npm run dev
```

The admin area is at **/admin** (credentials from `.env`).

## API keys (all free tiers)

| Key | Get it at | Powers |
|---|---|---|
| `API_FOOTBALL_KEY` | [api-football.com](https://www.api-football.com/) | consensus source (historical seasons on free tier) |
| football-data.org token | [football-data.org/client/register](https://www.football-data.org/client/register) | **primary source** — current-season fixtures, standings, backtests. Added via the admin UI, stored encrypted |
| `THE_ODDS_API_KEY` | [the-odds-api.com](https://theoddsapi.com/) | bookmaker over/under lines (optional — panel hides without it) |

No key at all? Enable the built-in `sample` provider in admin and everything
runs offline with canned data.

## Docs (developer)

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the pieces fit, provider roles/priority
- [docs/MODEL_NOTES.md](docs/MODEL_NOTES.md) — the Poisson/Dixon-Coles maths, consensus weights, backtest honesty rules
- [docs/ADDING_A_PROVIDER.md](docs/ADDING_A_PROVIDER.md) — plug in a new data API (+ free-tier gotchas)
- [docs/ADDING_A_LEAGUE.md](docs/ADDING_A_LEAGUE.md) — enable La Liga, Serie A, …
- [backend/README.md](backend/README.md) — migrations, tests, backend layout

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

## Notes

- Secrets live in `.env` (gitignored) or encrypted in the DB — never in source.
- SQLite for dev; point `DATABASE_URL` at Postgres to swap — no code changes.
- Free-tier rate limits are respected via caching (stats 6h / fixtures 1h) and
  per-provider throttling; watch consumption in **Admin → Usage**.
