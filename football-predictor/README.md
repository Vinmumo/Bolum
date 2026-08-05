# ⚽ Football Predictor

A personal tool to analyse football fixtures with a **Poisson-based** model —
win/draw/loss, over/under 2.5, BTTS, and likely scorelines. Starts with the
Premier League via [API-Football](https://www.api-football.com/), but leagues and
data providers are **configurable at runtime**, not hardcoded.

**Multi-source consensus:** enable more than one data API and every prediction
becomes the **average** of all of them, with each source's own numbers shown side
by side so you can see where they agree. Adapters included: API-Football and
football-data.org (both free to develop with); Sportmonks and Sportradar are
scaffolded. See [docs/ADDING_A_PROVIDER.md](docs/ADDING_A_PROVIDER.md) for keys +
how the averaging works.

> Runs fully **offline out of the box** with canned Premier League data — add an
> API-Football key when you're ready for live data.

![stack](https://img.shields.io/badge/backend-FastAPI-009688) ![stack](https://img.shields.io/badge/frontend-Vue_3-42b883) ![stack](https://img.shields.io/badge/db-SQLite%E2%86%92Postgres-informational)

## Quick start

Two terminals. **Python 3.11+ recommended** (works on 3.10).

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# env
cp ../.env.example .env          # then edit .env (SECRET_KEY, ADMIN_PASSWORD…)

# run (dev: tables auto-create + defaults seed on startup)
uvicorn app.main:app --reload    # → http://127.0.0.1:8000  (docs at /docs)
```

Leave `API_FOOTBALL_KEY` blank in `.env` to use offline **sample mode**. Add a
key later and switch the active provider in the admin UI.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                       # → http://localhost:5173  (proxies /api → :8000)
```

Open **http://localhost:5173** — the dashboard shows the gameweek; click a
fixture for the full breakdown. Admin is at **/admin** (log in with the
`ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`).

### Docker (optional)

```bash
docker compose up --build         # backend :8000, frontend :5173
```

## What's where

```
backend/     FastAPI app, Poisson model, provider adapters, admin API
frontend/    Vue 3 + Vite + Pinia + Tailwind (public dashboard + admin)
docs/        Developer docs (read these) ↓
```

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the pieces fit together
- [docs/ADDING_A_PROVIDER.md](docs/ADDING_A_PROVIDER.md) — plug in a new data API
- [docs/ADDING_A_LEAGUE.md](docs/ADDING_A_LEAGUE.md) — enable La Liga, Serie A, …
- [docs/MODEL_NOTES.md](docs/MODEL_NOTES.md) — the Poisson approach & why the weights
- [backend/README.md](backend/README.md) — backend dev notes (migrations, tests)

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

## Notes

- For analysis only — **not betting advice**.
- API keys are stored **encrypted at rest** and never logged in full. `.env` is
  gitignored; never commit real keys.
