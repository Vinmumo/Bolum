"""One row per outbound provider request, so you can watch your rate-limit quota.

Cache hits are NOT logged here (no outbound call happened) — this table reflects
real API consumption only.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ApiUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), index=True
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    provider: Mapped["Provider"] = relationship(back_populates="usage_logs")  # noqa: F821
