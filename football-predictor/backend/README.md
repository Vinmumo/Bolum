# Backend — developer notes

FastAPI + SQLAlchemy + Alembic. Developer-facing; for the product overview see
the [root README](../README.md) and [docs/](../docs/).

## Layout

```
app/
  main.py            FastAPI app + lifespan (create_all + seed in dev)
  core/              config (pydantic-settings) + security (JWT, Fernet encryption)
  db/                engine/session, declarative base, seed
  models/            SQLAlchemy tables
  schemas/           Pydantic request/response
  providers/         base interface, api_football, sample, registry
  services/          poisson_model, form_analysis, h2h_analysis, predictor, cache
  api/routers/       fixtures, predictions, leagues, teams, admin
  tests/             pytest (services are pure → easy to test)
alembic/             migrations
```

## Running

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # edit it
uvicorn app.main:app --reload
```

Interactive API docs at `http://127.0.0.1:8000/docs`.

## Configuration

All via env / `.env` (see [`.env.example`](../.env.example)). Never hardcode.
Notable:

- `DATABASE_URL` — SQLite by default; set a `postgresql+psycopg://…` URL to swap.
- `SECRET_KEY` — signs JWTs **and** derives the Fernet key that encrypts provider
  API keys. Changing it invalidates existing encrypted keys — re-enter them.
- `API_FOOTBALL_KEY` — blank → offline sample mode.
- `CACHE_TTL_*`, `PROVIDER_MIN_INTERVAL` — provider caching/throttling.

## Database migrations (Alembic)

In dev, `main.py` calls `create_all` + seeds on startup, so you can skip Alembic
entirely. For real schema management:

```bash
# generate a migration after changing models
alembic revision --autogenerate -m "describe change"
# apply
alembic upgrade head
```

`alembic/env.py` pulls `DATABASE_URL` and metadata from the app, so migrations
always match the app's schema. An initial migration is included under
`alembic/versions/`.

## Tests

```bash
pytest              # from backend/
```

Services are pure functions, so the Poisson maths, form, and H2H logic are
unit-tested directly. `test_predictor.py` runs the full pipeline against the
offline `SampleProvider` (no network).

## Auth model

Single admin, credentials in `.env`. `POST /api/admin/login` (form-encoded
`username`/`password`) → JWT. Send `Authorization: Bearer <token>` to
`/api/admin/*`. There is intentionally **no public signup**.

## Adding providers / leagues

See [docs/ADDING_A_PROVIDER.md](../docs/ADDING_A_PROVIDER.md) and
[docs/ADDING_A_LEAGUE.md](../docs/ADDING_A_LEAGUE.md).
