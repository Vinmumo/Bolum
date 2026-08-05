"""A configurable football-data provider.

Providers are stored in the DB (not hardcoded) so new APIs can be added from
the admin UI. `provider_type` maps to a concrete class in providers/registry.py.
The API key is stored ENCRYPTED (see core.security.encrypt_secret).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    # Which concrete adapter class handles this provider (e.g. "api_football").
    provider_type: Mapped[str] = mapped_column(String(60), nullable=False)

    base_url: Mapped[str] = mapped_column(String(255), nullable=False)

    # HTTP header used for auth, e.g. "x-apisports-key".
    auth_header: Mapped[str] = mapped_column(String(120), default="x-apisports-key")

    # Encrypted at rest; decrypted only when a request is actually made.
    encrypted_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    usage_logs: Mapped[list["ApiUsageLog"]] = relationship(  # noqa: F821
        back_populates="provider", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Provider {self.name} type={self.provider_type} active={self.active}>"
