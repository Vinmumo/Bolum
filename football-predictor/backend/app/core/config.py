"""Application settings, loaded from environment / .env via pydantic-settings.

Nothing here is hardcoded to a single league or provider — those live in the
database. This file only holds process-level configuration and secrets.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "Football Predictor"
    environment: str = "development"
    secret_key: str = "change-me-to-a-long-random-string-at-least-32-chars"

    # ---- Database ----
    database_url: str = "sqlite:///./football_predictor.db"

    # ---- Admin auth ----
    admin_username: str = "admin"
    admin_password: str = "change-me"
    access_token_expire_minutes: int = 60 * 24

    # ---- API-Football ----
    api_football_key: str | None = None
    api_football_base_url: str = "https://v3.football.api-sports.io"

    # ---- The Odds API (bookmaker over/under lines; optional) ----
    the_odds_api_key: str | None = None

    # ---- Auto-backtest (replays finished gameweeks in the background) ----
    auto_backtest_enabled: bool = True
    auto_backtest_interval_hours: int = 12
    auto_backtest_max_per_run: int = 4

    # ---- Defaults ----
    default_league_external_id: int = 39  # Premier League on API-Football
    default_season: int = 2023

    # ---- Caching / throttling ----
    cache_ttl_stats: int = 6 * 3600
    cache_ttl_fixtures: int = 3600
    cache_ttl_h2h: int = 6 * 3600
    provider_min_interval: float = 1.0

    # ---- CORS ----
    frontend_origin: str = "http://localhost:5173"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
