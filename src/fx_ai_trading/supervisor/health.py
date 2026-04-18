"""HealthChecker — periodic component health checks (D4 §6.4 / M7).

Supervisor calls check() every 10 seconds to detect component failures.
In M7, the implemented checks are:
  - DB connectivity (SELECT 1, 2s timeout)

Checks deferred to later milestones:
  - Broker.get_positions() liveness (M8)
  - PriceFeed / Transaction stream heartbeat age (M9)
  - OutboxProcessor last_processed_at (M8)
  - FileNotifier write heartbeat (M12)

Timestamp from injected Clock (no datetime.now() / time.time() here).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import Engine, text

from fx_ai_trading.common.clock import Clock

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health sub-check."""

    name: str
    is_ok: bool
    detail: str = ""


@dataclass(frozen=True)
class HealthStatus:
    """Aggregated health status returned by HealthChecker.check().

    is_ok is True iff all individual checks passed.
    """

    is_ok: bool
    checks: tuple[CheckResult, ...]
    checked_at: object  # datetime — kept as object to avoid import cycle

    @classmethod
    def from_checks(
        cls,
        checks: list[CheckResult],
        checked_at: object,
    ) -> HealthStatus:
        """Construct from a mutable list of CheckResult."""
        return cls(
            is_ok=all(c.is_ok for c in checks),
            checks=tuple(checks),
            checked_at=checked_at,
        )


class HealthChecker:
    """Runs the set of component health checks defined for M7.

    Args:
        clock: Used to timestamp the HealthStatus result.
        db_timeout_s: Maximum seconds for the DB SELECT 1 before marking
            the check failed.
    """

    _DB_CHECK_NAME = "db_connection"

    def __init__(self, clock: Clock, db_timeout_s: float = 2.0) -> None:
        self._clock = clock
        self._db_timeout_s = db_timeout_s

    def check(self, engine: Engine | None = None) -> HealthStatus:
        """Run all health checks and return aggregated HealthStatus.

        Args:
            engine: SQLAlchemy Engine for the DB check.  If None, the DB
                check is skipped (reported as ok with a note).

        Returns:
            HealthStatus with is_ok=True iff every check passed.
        """
        checked_at = self._clock.now()
        results: list[CheckResult] = []

        results.append(self._check_db(engine))

        status = HealthStatus.from_checks(results, checked_at=checked_at)
        if not status.is_ok:
            failed = [c.name for c in status.checks if not c.is_ok]
            _log.warning("HealthChecker: failed checks: %s", failed)
        return status

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_db(self, engine: Engine | None) -> CheckResult:
        if engine is None:
            return CheckResult(
                name=self._DB_CHECK_NAME,
                is_ok=True,
                detail="skipped (no engine)",
            )
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return CheckResult(name=self._DB_CHECK_NAME, is_ok=True)
        except Exception as exc:  # noqa: BLE001
            return CheckResult(
                name=self._DB_CHECK_NAME,
                is_ok=False,
                detail=str(exc),
            )
