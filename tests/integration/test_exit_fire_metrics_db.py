"""Integration tests: ExitFireMetricsService against a real DB (Cycle 6.9b).

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.

Inserts a controlled set of close_events fixture rows (with deterministic
``closed_at`` and ``pnl_realized`` values), exercises each public method,
and asserts the aggregation results match the inserted data. Cleans up
all fixture rows in module teardown.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.services.exit_fire_metrics import ExitFireMetricsService

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL, reason="DATABASE_URL not set — skipping integration tests"
)

_BROKER_ID = "__test_broker_efm__"
_ACCOUNT_ID = "__test_account_efm__"
_INSTRUMENT = "__TEST_EFM_EUR__"
_ORDER_ID = "__test_entry_ord_efm__"

# Window anchor — every fixture closed_at is computed relative to this.
_FIXED_NOW = datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)

# Three close_events rows: two recent (within 1h), one old (24h ago).
# Reason mix: tp x2 (recent + old), sl x1 (recent).
_FIXTURE_EVENTS = [
    {
        "close_event_id": "__efm_evt_recent_tp__",
        "primary_reason_code": "tp",
        "closed_at": _FIXED_NOW - timedelta(minutes=10),
        "pnl_realized": 12.5,
    },
    {
        "close_event_id": "__efm_evt_recent_sl__",
        "primary_reason_code": "sl",
        "closed_at": _FIXED_NOW - timedelta(minutes=30),
        "pnl_realized": -4.0,
    },
    {
        "close_event_id": "__efm_evt_old_tp__",
        "primary_reason_code": "tp",
        "closed_at": _FIXED_NOW - timedelta(hours=24),
        "pnl_realized": 6.5,
    },
]

_CTX = CommonKeysContext(
    run_id="efm-integ-run",
    environment="test",
    code_version="0.0.0",
    config_version="test-efm-cfg",
)


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DATABASE_URL)
    yield e
    e.dispose()


@pytest.fixture(scope="module", autouse=True)
def db_fixture(engine):
    """Insert prerequisite FK rows + the 3 close_events fixtures, clean up after."""
    from fx_ai_trading.repositories.close_events import CloseEventsRepository
    from fx_ai_trading.repositories.orders import OrdersRepository

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO brokers (broker_id, name)"
                " VALUES (:bid, 'test-efm-broker') ON CONFLICT DO NOTHING"
            ),
            {"bid": _BROKER_ID},
        )
        conn.execute(
            text(
                "INSERT INTO accounts (account_id, broker_id, account_type, base_currency)"
                " VALUES (:aid, :bid, 'demo', 'USD') ON CONFLICT DO NOTHING"
            ),
            {"aid": _ACCOUNT_ID, "bid": _BROKER_ID},
        )
        conn.execute(
            text(
                "INSERT INTO instruments (instrument, base_currency, quote_currency, pip_location)"
                " VALUES (:inst, 'EUR', 'USD', -4) ON CONFLICT DO NOTHING"
            ),
            {"inst": _INSTRUMENT},
        )

    orders_repo = OrdersRepository(engine)
    orders_repo.create_order(
        order_id=_ORDER_ID,
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        account_type="demo",
        order_type="market",
        direction="buy",
        units="1000",
        context=_CTX,
    )

    close_repo = CloseEventsRepository(engine=engine)
    for evt in _FIXTURE_EVENTS:
        close_repo.insert(
            close_event_id=evt["close_event_id"],
            order_id=_ORDER_ID,
            primary_reason_code=evt["primary_reason_code"],
            reasons=[{"priority": 1, "reason_code": evt["primary_reason_code"], "detail": ""}],
            closed_at=evt["closed_at"],
            pnl_realized=evt["pnl_realized"],
        )

    yield

    fixture_ids = [evt["close_event_id"] for evt in _FIXTURE_EVENTS]
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM close_events WHERE close_event_id = ANY(:ids)"),
            {"ids": fixture_ids},
        )
        conn.execute(text("DELETE FROM orders WHERE order_id = :oid"), {"oid": _ORDER_ID})
        conn.execute(text("DELETE FROM accounts WHERE account_id = :aid"), {"aid": _ACCOUNT_ID})
        conn.execute(
            text("DELETE FROM instruments WHERE instrument = :inst"), {"inst": _INSTRUMENT}
        )
        conn.execute(text("DELETE FROM brokers WHERE broker_id = :bid"), {"bid": _BROKER_ID})


def _service(engine) -> ExitFireMetricsService:
    return ExitFireMetricsService(engine=engine, clock=FixedClock(_FIXED_NOW))


def _our_fixture_ids() -> set[str]:
    return {evt["close_event_id"] for evt in _FIXTURE_EVENTS}


class TestExitFireMetricsAgainstRealDb:
    def test_recent_fires_orders_by_closed_at_desc_with_parsed_reasons(self, engine) -> None:
        # Take a generous limit and filter to our fixtures so other rows in
        # the table (left over from sibling tests) do not interfere.
        rows = _service(engine).recent_fires(limit=500)
        ours = [r for r in rows if r["close_event_id"] in _our_fixture_ids()]
        assert len(ours) == 3

        ids_in_order = [r["close_event_id"] for r in ours]
        assert ids_in_order == [
            "__efm_evt_recent_tp__",
            "__efm_evt_recent_sl__",
            "__efm_evt_old_tp__",
        ]
        # JSON column is parsed back into a list of dicts.
        assert isinstance(ours[0]["reasons"], list)
        assert ours[0]["reasons"][0]["reason_code"] == "tp"

    def test_count_by_reason_window_excludes_old_rows(self, engine) -> None:
        # 1-hour window: includes the two "recent" fixtures, excludes the old one.
        # Other tests' rows may also fall in the window, so we assert the
        # delta produced by our fixtures rather than absolute equality.
        svc = _service(engine)
        unbounded = svc.count_by_reason()
        windowed = svc.count_by_reason(window=timedelta(hours=1))

        # Within our fixture set: window drops the old tp row (-1 tp).
        assert unbounded.get("tp", 0) - windowed.get("tp", 0) >= 1
        # The recent sl row is inside the window.
        assert windowed.get("sl", 0) >= 1

    def test_summary_span_is_tz_aware_utc(self, engine) -> None:
        result = _service(engine).summary()
        assert result["total_fires"] >= 3
        assert result["distinct_reasons"] >= 2  # tp and sl from our fixtures
        # span endpoints come from TIMESTAMPTZ — must be tz-aware.
        assert result["span_start_utc"] is not None
        assert result["span_end_utc"] is not None
        assert result["span_start_utc"].tzinfo is not None
        assert result["span_end_utc"].tzinfo is not None
        # And our oldest fixture (24h ago) must be within the observed span.
        assert result["span_start_utc"] <= _FIXED_NOW - timedelta(hours=24)

    def test_pnl_summary_aggregates_real_pnl_values(self, engine) -> None:
        # Window scoped to the last 1 hour to make the assertion deterministic
        # against just our 2 recent fixtures (tp +12.5, sl -4.0). The old tp
        # row (24h ago) is excluded, so within the window: tp count=1 sum=12.5,
        # sl count=1 sum=-4.0. We still take a delta-style assertion in case
        # other concurrent tests have inserted within the window.
        svc = _service(engine)
        result = svc.pnl_summary_by_reason(window=timedelta(hours=1))

        assert "tp" in result
        assert "sl" in result
        # Our fixture pnl values must contribute to the aggregate.
        assert result["tp"]["count"] >= 1
        assert result["sl"]["count"] >= 1
        # SUM/AVG must be real floats (not None) since our fixture rows
        # carry non-null pnl_realized.
        assert result["tp"]["pnl_sum"] is not None
        assert result["tp"]["pnl_avg"] is not None
        assert result["sl"]["pnl_sum"] is not None
