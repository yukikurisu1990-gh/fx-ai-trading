"""Single SQLAlchemy declarative root for all ORM models in fx-ai-trading.

Introduced at Cycle 15 (M2-2). Cycle 15 itself does not declare any model
subclasses — the initial Group A migration uses direct ``op.create_table``.
Cycle 16+ will add model modules (one per schema group) that subclass
``Base``; they become visible to Alembic autogenerate simply by being
imported somewhere reachable from ``migrations/env.py``.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative root for all fx-ai-trading ORM models."""
