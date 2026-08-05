"""Shared FastAPI dependencies: DB session, provider registry, admin auth,
and a single place that turns provider errors into clean HTTP responses.
"""
from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.league import League
from app.providers.base import (
    ProviderAuthError,
    ProviderError,
    ProviderNotFoundError,
    ProviderRateLimitError,
)
from app.providers.registry import ProviderRegistry

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


def get_registry(db: Session = Depends(get_db)) -> ProviderRegistry:
    return ProviderRegistry(db)


def require_admin(token: str = Depends(oauth2_scheme)) -> str:
    subject = decode_access_token(token)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject


def resolve_league_season(
    db: Session, league_external_id: int | None, season: int | None
) -> tuple[int, int]:
    """Fill in league/season from the first active League, then config defaults."""
    if league_external_id is not None and season is not None:
        return league_external_id, season

    active = db.execute(
        select(League).where(League.active.is_(True)).order_by(League.id)
    ).scalars().first()

    ext = league_external_id
    seas = season
    if ext is None:
        ext = active.external_provider_id if active else settings.default_league_external_id
    if seas is None:
        seas = active.season if active else settings.default_season
    return ext, seas


def provider_error_to_http(exc: ProviderError) -> HTTPException:
    """Map a provider exception to the right HTTP status + friendly message."""
    if isinstance(exc, ProviderRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit reached for the data provider. Try again later.",
        )
    if isinstance(exc, ProviderAuthError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Data provider authentication failed. Check the API key in admin.",
        )
    if isinstance(exc, ProviderNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
