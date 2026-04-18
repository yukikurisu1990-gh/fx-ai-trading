"""SQLiteAdapter — SQLAlchemy Engine wrapper for SQLite (D3 §2.9.2, dev only).

Restricted to: single_process_mode × local environment.
Must NOT be used in multi_service_mode or container_ready_mode (D1 §6.11).

SQLite-specific configuration:
  - check_same_thread=False: required for multi-threaded test runners
  - WAL journal mode: enables concurrent reads during writes
  - foreign_keys=ON: enforces FK constraints (disabled by default in SQLite)

Usage:
  adapter = SQLiteAdapter(url="sqlite:///dev.db")
  # or in-memory for tests:
  adapter = SQLiteAdapter(url="sqlite://")
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, create_engine, event


def _set_sqlite_pragmas(dbapi_conn: object, _connection_record: object) -> None:
    cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class SQLiteAdapter:
    """Dev-only SQLite adapter (D3 §2.9.2).

    Invariant: use only in single_process_mode × local environment.
    Pool: StaticPool for in-memory (':memory:'), NullPool for file-based.
    """

    def __init__(self, url: str) -> None:
        connect_args: dict = {"check_same_thread": False}
        self._engine: Engine = create_engine(url, connect_args=connect_args)
        event.listen(self._engine, "connect", _set_sqlite_pragmas)

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
