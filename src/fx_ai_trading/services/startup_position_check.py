"""Startup position integrity check.

Compares the StateManager's open-position view (derived from the orders
table) against the broker's live open-position list.  Called once at
startup — before the trading loop begins — so any drift accumulated
across a restart is surfaced early.

Mismatch categories
-------------------
db_only
    Instruments tracked as OPEN in the DB but absent from the broker.
    Likely cause: a close event was processed by the broker but the DB
    was not updated (crash between broker fill and state_manager.on_close).
    Risk: loop may attempt a redundant re-entry or calculate exposure
    against a ghost position.

broker_only
    Instruments open at the broker but absent from the DB.
    Likely cause: a fill was accepted by the broker but the DB write
    failed (crash between place_order and on_fill).
    Risk: loop has no knowledge of the position, so it will not manage or
    exit it and will not account for its risk.

Both categories are WARNING-level; neither causes an automatic abort so
that the operator can make a manual decision.  Pass ``halt_on_mismatch``
to raise ``PositionMismatchError`` if any drift is detected (e.g., to
enforce a hard gate in live mode).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

_log = logging.getLogger(__name__)


class PositionMismatchError(Exception):
    """Raised when halt_on_mismatch=True and a mismatch is detected."""


@dataclass
class PositionIntegrityResult:
    """Outcome of a startup position integrity check."""

    db_instruments: frozenset[str]
    broker_instruments: frozenset[str] | None  # None → broker not queried
    db_only: frozenset[str]  # in DB but not at broker
    broker_only: frozenset[str]  # at broker but not in DB

    @property
    def has_mismatch(self) -> bool:
        return bool(self.db_only or self.broker_only)

    @property
    def broker_queried(self) -> bool:
        return self.broker_instruments is not None


def check_position_integrity(
    open_db_instruments: frozenset[str],
    open_broker_instruments: frozenset[str] | None = None,
    *,
    halt_on_mismatch: bool = False,
) -> PositionIntegrityResult:
    """Compare DB open positions against broker open positions.

    Args:
        open_db_instruments: Instruments currently tracked as open in the DB
            (from StateManager.open_instruments()).
        open_broker_instruments: Instruments the broker reports as open.
            Pass None to skip broker comparison (paper / replay mode).
        halt_on_mismatch: When True, raise PositionMismatchError if any
            drift is detected.  Default False (warn-only).

    Returns:
        PositionIntegrityResult with mismatch details.

    Raises:
        PositionMismatchError: If halt_on_mismatch=True and drift exists.
    """
    _log.info(
        "startup_position_check: db_open=%d%s",
        len(open_db_instruments),
        f" broker_open={len(open_broker_instruments)}"
        if open_broker_instruments is not None
        else " (broker not queried)",
    )

    db_only: frozenset[str]
    broker_only: frozenset[str]

    if open_broker_instruments is None:
        db_only = frozenset()
        broker_only = frozenset()
    else:
        db_only = open_db_instruments - open_broker_instruments
        broker_only = open_broker_instruments - open_db_instruments

    result = PositionIntegrityResult(
        db_instruments=open_db_instruments,
        broker_instruments=open_broker_instruments,
        db_only=db_only,
        broker_only=broker_only,
    )

    if not result.has_mismatch:
        _log.info("startup_position_check: OK — no position drift detected")
        return result

    if db_only:
        _log.warning(
            "startup_position_check: DB_ONLY positions (in DB, not at broker) — %s"
            " — possible missed close; manual review recommended",
            sorted(db_only),
        )
    if broker_only:
        _log.warning(
            "startup_position_check: BROKER_ONLY positions (at broker, not in DB) — %s"
            " — possible missed fill; manual review recommended",
            sorted(broker_only),
        )

    if halt_on_mismatch:
        raise PositionMismatchError(
            f"Position drift detected: db_only={sorted(db_only)},"
            f" broker_only={sorted(broker_only)}"
        )

    return result
