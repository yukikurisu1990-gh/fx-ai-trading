"""PostgreSQLAdapter — SQLAlchemy Engine wrapper for PostgreSQL (D3 §2.9.2).

Provides:
  - engine: Engine for direct use by Repository layer
  - transaction(): context manager yielding a write Connection (auto-commit/rollback)
  - connect(): context manager yielding a read-only Connection
  - dispose(): release connection pool (call on shutdown)

Transaction boundary contract (D3 §2.9.2):
  Callers open the transaction; Repositories participate only.
  Repositories must NOT commit or rollback — they execute within the
  connection provided by the caller or by their own begin() call.

Usage:
  adapter = PostgreSQLAdapter(url="postgresql+psycopg2://...")
  repo = OrdersRepository(adapter.engine)

  # Write with explicit transaction boundary:
  with adapter.transaction() as conn:
      conn.execute(...)  # callers that need cross-repo atomicity
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, create_engine


class PostgreSQLAdapter:
    """Production-grade PostgreSQL adapter (D3 §2.9.2).

    Idempotent: safe to call dispose() multiple times.
    Side effects: creates connection pool on __init__; releases on dispose().
    """

    def __init__(self, url: str, *, pool_size: int = 5, max_overflow: int = 10) -> None:
        self._engine: Engine = create_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )

    @property
    def engine(self) -> Engine:
        """Return the underlying SQLAlchemy Engine for use by Repositories."""
        return self._engine

    @contextmanager
    def transaction(self) -> Generator[Connection, None, None]:
        """Yield a Connection with an open transaction (auto-commit on exit).

        Rolls back automatically on exception.
        """
        with self._engine.begin() as conn:
            yield conn

    @contextmanager
    def connect(self) -> Generator[Connection, None, None]:
        """Yield a read-only Connection (no implicit transaction)."""
        with self._engine.connect() as conn:
            yield conn

    def dispose(self) -> None:
        """Release the connection pool. Safe to call multiple times."""
        self._engine.dispose()
