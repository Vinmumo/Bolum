"""Declarative base only.

To get every model registered on `Base.metadata` (needed by create_all and
Alembic autogenerate), import the `app.models` package, which imports each
model. Keeping model imports OUT of this file avoids an import cycle
(models import Base from here).
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
