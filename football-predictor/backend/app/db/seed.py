"""Seed sensible defaults on first run.

- One active league: Premier League.
- One active provider: API-Football if API_FOOTBALL_KEY is set, otherwise the
  offline `sample` provider so the app works out of the box.

Idempotent — safe to run on every startup.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import encrypt_secret
from app.models.league import League
from app.models.provider import Provider


def seed_defaults(db: Session) -> None:
    _seed_league(db)
    _seed_provider(db)
    db.commit()


def _seed_league(db: Session) -> None:
    exists = db.execute(select(League).limit(1)).scalars().first()
    if exists:
        return
    db.add(
        League(
            name="Premier League",
            country="England",
            external_provider_id=settings.default_league_external_id,
            season=settings.default_season,
            active=True,
        )
    )


def _seed_provider(db: Session) -> None:
    exists = db.execute(select(Provider).limit(1)).scalars().first()
    if exists:
        return

    if settings.api_football_key:
        db.add(
            Provider(
                name="API-Football",
                provider_type="api_football",
                base_url=settings.api_football_base_url,
                auth_header="x-apisports-key",
                encrypted_api_key=encrypt_secret(settings.api_football_key),
                active=True,
            )
        )
    else:
        # No key -> offline sample mode so the whole app still works.
        db.add(
            Provider(
                name="Sample (offline)",
                provider_type="sample",
                base_url="local://sample",
                auth_header="x-apisports-key",
                encrypted_api_key=None,
                active=True,
            )
        )
