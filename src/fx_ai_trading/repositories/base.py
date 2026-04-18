"""RepositoryBase — engine holder with Common Keys hook placeholder.

Scope (M3 Cycle 5):
  - Holds the SQLAlchemy Engine.
  - Declares _apply_common_keys() as a no-op hook; M5 will implement it.
"""

from __future__ import annotations

from sqlalchemy import Engine


class RepositoryBase:
    """Minimal base for all repositories.

    Subclasses gain access to ``self._engine`` and the Common Keys
    hook ``_apply_common_keys()``, which becomes non-trivial in M5.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _apply_common_keys(self, context: object) -> None:
        """No-op placeholder — M5 will propagate CommonKeysContext here."""
