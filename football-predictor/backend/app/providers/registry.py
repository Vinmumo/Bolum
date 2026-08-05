"""ProviderRegistry — build provider instances from DB rows, not from hardcode.

`PROVIDER_CLASSES` is the ONE place that maps a `provider_type` slug to its
adapter class. To plug in a new API you add its class here and create a Provider
row from the admin UI (name, base URL, auth header, key, type). Nothing else
changes. See docs/ADDING_A_PROVIDER.md.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models.api_usage_log import ApiUsageLog
from app.models.provider import Provider
from app.providers.api_football import ApiFootballProvider
from app.providers.base import FootballDataProvider, ProviderError
from app.providers.football_data_org import FootballDataOrgProvider
from app.providers.sample import SampleProvider
from app.providers.sportmonks import SportmonksProvider
from app.providers.sportradar import SportradarProvider

# provider_type slug -> adapter class. Extend here when adding a provider.
PROVIDER_CLASSES: dict[str, type[FootballDataProvider]] = {
    "api_football": ApiFootballProvider,
    "football_data_org": FootballDataOrgProvider,
    "sportmonks": SportmonksProvider,  # scaffold — see adapter docstring
    "sportradar": SportradarProvider,  # scaffold — see adapter docstring
    "sample": SampleProvider,
}


class ProviderRegistry:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    def _build(self, row: Provider) -> FootballDataProvider:
        cls = PROVIDER_CLASSES.get(row.provider_type)
        if cls is None:
            raise ProviderError(
                f"Unknown provider_type '{row.provider_type}'. "
                f"Known: {', '.join(PROVIDER_CLASSES)}."
            )

        api_key = decrypt_secret(row.encrypted_api_key) if row.encrypted_api_key else None

        # Bind a usage logger to THIS provider row + a fresh session write.
        def usage_logger(endpoint: str, status: int | None, success: bool) -> None:
            self._log_usage(row.id, endpoint, status, success)

        return cls(
            base_url=row.base_url,
            api_key=api_key,
            auth_header=row.auth_header,
            provider_id=row.id,
            usage_logger=usage_logger,
            min_interval=settings.provider_min_interval,
            ttl_stats=settings.cache_ttl_stats,
            ttl_fixtures=settings.cache_ttl_fixtures,
            ttl_h2h=settings.cache_ttl_h2h,
        )

    def _log_usage(self, provider_id: int, endpoint: str, status: int | None, success: bool) -> None:
        # Own transaction so it can't be rolled back with request work.
        from app.db.session import SessionLocal

        with SessionLocal() as s:
            s.add(
                ApiUsageLog(
                    provider_id=provider_id,
                    endpoint=endpoint,
                    status_code=status,
                    success=success,
                )
            )
            s.commit()

    # ------------------------------------------------------------------ #
    def get_active_provider(self) -> FootballDataProvider:
        """The first active provider, ordered by id. Raises if none enabled.

        Used for single-source endpoints (fixtures/calendar) where averaging
        makes no sense — this is the "primary" provider.
        """
        row = self.db.execute(
            select(Provider).where(Provider.active.is_(True)).order_by(Provider.priority, Provider.id)
        ).scalars().first()
        if row is None:
            raise ProviderError(
                "No active data provider configured. Add one in the admin page."
            )
        return self._build(row)

    def get_active_providers(self) -> list[tuple[str, FootballDataProvider, float]]:
        """All active providers as (name, instance, weight), by priority.

        The predictor runs across every one of these and takes a weighted
        average (consensus). Raises if none are enabled.
        """
        rows = self.db.execute(
            select(Provider).where(Provider.active.is_(True)).order_by(Provider.priority, Provider.id)
        ).scalars().all()
        if not rows:
            raise ProviderError(
                "No active data provider configured. Add one in the admin page."
            )
        return [(row.name, self._build(row), row.weight or 1.0) for row in rows]

    def get_provider_by_id(self, provider_id: int) -> FootballDataProvider:
        row = self.db.get(Provider, provider_id)
        if row is None:
            raise ProviderError(f"Provider {provider_id} not found.")
        return self._build(row)
