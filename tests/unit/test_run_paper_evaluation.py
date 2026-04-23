"""Unit tests for ``scripts/run_paper_evaluation.py``.

Per the strategy-evaluation phase scope, we keep this **minimal** —
three tests that only exercise the *new* surface introduced by this PR:

1. ``aggregate_metrics`` returns the frozen JSON shape with safe
   ``None`` / zero values when the run window contains no closes.
2. ``aggregate_metrics`` reduces seeded ``positions(open)`` /
   ``close_events`` rows into the documented six metrics correctly.
3. ``emit_metrics`` serialises the metrics dict as a JSON document that
   round-trips back to an equivalent dict.

We deliberately do **not** test the live entry+exit cadence
(``run_eval_ticks``) here: that path requires the production paper
stack (OANDA env, supervisor wiring, broker fills) which is already
covered by the ``run_paper_entry_loop`` / ``run_paper_loop``
integration tests.  Re-asserting it would be coverage duplication.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_paper_evaluation.py"


def _load_module():
    """Load ``run_paper_evaluation`` via importlib (scripts/ is not a package)."""
    alias = "_paper_evaluation_under_test"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


_DDL_ORDERS = """
CREATE TABLE orders (
    order_id          TEXT PRIMARY KEY,
    client_order_id   TEXT,
    trading_signal_id TEXT,
    account_id        TEXT NOT NULL,
    instrument        TEXT NOT NULL,
    account_type      TEXT NOT NULL,
    order_type        TEXT NOT NULL,
    direction         TEXT NOT NULL,
    units             NUMERIC(18,4) NOT NULL,
    status            TEXT NOT NULL DEFAULT 'PENDING',
    submitted_at      TEXT,
    filled_at         TEXT,
    canceled_at       TEXT,
    correlation_id    TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_DDL_POSITIONS = """
CREATE TABLE positions (
    position_snapshot_id TEXT PRIMARY KEY,
    order_id             TEXT,
    account_id           TEXT NOT NULL,
    instrument           TEXT NOT NULL,
    event_type           TEXT NOT NULL,
    units                NUMERIC(18,4) NOT NULL,
    avg_price            NUMERIC(18,8),
    unrealized_pl        NUMERIC(18,8),
    realized_pl          NUMERIC(18,8),
    event_time_utc       TEXT NOT NULL,
    correlation_id       TEXT
)
"""

_DDL_CLOSE_EVENTS = """
CREATE TABLE close_events (
    close_event_id       TEXT PRIMARY KEY,
    order_id             TEXT NOT NULL,
    position_snapshot_id TEXT,
    reasons              TEXT NOT NULL,
    primary_reason_code  TEXT NOT NULL,
    closed_at            TEXT NOT NULL,
    pnl_realized         NUMERIC(18,8),
    correlation_id       TEXT
)
"""


_ACCOUNT = "acct-eval"
_INSTRUMENT = "EUR_USD"
_START = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
_END = _START + timedelta(minutes=10)


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_ORDERS))
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_CLOSE_EVENTS))
    yield eng
    eng.dispose()


def _seed_order(conn, *, order_id: str, direction: str = "buy") -> None:
    conn.execute(
        text(
            """
            INSERT INTO orders (
                order_id, account_id, instrument, account_type,
                order_type, direction, units, status
            ) VALUES (
                :oid, :acct, :inst, 'demo', 'market', :dir, 1000, 'FILLED'
            )
            """
        ),
        {"oid": order_id, "acct": _ACCOUNT, "inst": _INSTRUMENT, "dir": direction},
    )


def _seed_open(conn, *, order_id: str, opened_at: datetime) -> None:
    conn.execute(
        text(
            """
            INSERT INTO positions (
                position_snapshot_id, order_id, account_id, instrument,
                event_type, units, avg_price, event_time_utc
            ) VALUES (
                :psid, :oid, :acct, :inst, 'open', 1000, 0.99, :ts
            )
            """
        ),
        {
            "psid": f"psid-{order_id}",
            "oid": order_id,
            "acct": _ACCOUNT,
            "inst": _INSTRUMENT,
            "ts": opened_at.isoformat(),
        },
    )


def _seed_close(conn, *, order_id: str, closed_at: datetime, pnl_realized: float) -> None:
    conn.execute(
        text(
            """
            INSERT INTO close_events (
                close_event_id, order_id, reasons, primary_reason_code,
                closed_at, pnl_realized
            ) VALUES (
                :ceid, :oid, :reasons, 'max_holding', :ts, :pnl
            )
            """
        ),
        {
            "ceid": f"ce-{order_id}",
            "oid": order_id,
            "reasons": '["max_holding"]',
            "ts": closed_at.isoformat(),
            "pnl": pnl_realized,
        },
    )


class TestAggregateMetrics:
    def test_empty_run_window_returns_safe_zero_shape(self, engine) -> None:
        """No close_events in the window → trades_count=0, None/0 elsewhere.

        Every documented key is present and JSON-serialisable so the
        downstream ``emit_metrics`` contract holds even on an empty run.
        """
        mod = _load_module()

        metrics = mod.aggregate_metrics(
            engine=engine,
            account_id=_ACCOUNT,
            instrument=_INSTRUMENT,
            start_time=_START,
            end_time=_END,
            ticks_executed=10,
            no_signal_count=7,
            strategy="minimum",
        )

        assert metrics == {
            "strategy": "minimum",
            "ticks_executed": 10,
            "trades_count": 0,
            "win_rate": None,
            "avg_pnl": None,
            "total_pnl": 0.0,
            "no_signal_rate": 0.7,
            "avg_holding_sec": None,
        }
        # Every value must be JSON-serialisable for emit_metrics(json).
        json.dumps(metrics)

    def test_seeded_three_closes_reduce_to_documented_metrics(self, engine) -> None:
        """3 closes (2 wins / 1 loss) reduce to the documented six metrics.

        Holding times are set per-trade (60s / 120s / 180s) so the mean
        is a clean 120.0; PnLs are 1.0 / 2.0 / -1.0 → total=2.0,
        avg=2/3, win_rate=2/3.
        """
        mod = _load_module()

        with engine.begin() as conn:
            for i, (pnl, hold_sec) in enumerate([(1.0, 60), (2.0, 120), (-1.0, 180)], start=1):
                oid = f"ord-{i}"
                opened_at = _START + timedelta(minutes=i)
                closed_at = opened_at + timedelta(seconds=hold_sec)
                _seed_order(conn, order_id=oid)
                _seed_open(conn, order_id=oid, opened_at=opened_at)
                _seed_close(conn, order_id=oid, closed_at=closed_at, pnl_realized=pnl)

        metrics = mod.aggregate_metrics(
            engine=engine,
            account_id=_ACCOUNT,
            instrument=_INSTRUMENT,
            start_time=_START,
            end_time=_END,
            ticks_executed=20,
            no_signal_count=5,
            strategy="multi",
        )

        assert metrics["strategy"] == "multi"
        assert metrics["ticks_executed"] == 20
        assert metrics["trades_count"] == 3
        assert metrics["total_pnl"] == pytest.approx(2.0)
        assert metrics["avg_pnl"] == pytest.approx(2.0 / 3.0)
        assert metrics["win_rate"] == pytest.approx(2.0 / 3.0)
        assert metrics["no_signal_rate"] == pytest.approx(0.25)
        assert metrics["avg_holding_sec"] == pytest.approx(120.0)


class TestEmitMetrics:
    def test_json_to_stdout_round_trips(self) -> None:
        """``--output json`` (no path) writes one parseable JSON object.

        We avoid writing to the real filesystem here — the file-path
        branch is a thin wrapper over the same ``json.dump`` call and
        offers no additional behaviour worth covering separately.
        """
        mod = _load_module()
        sample = {
            "strategy": "fivepoint",
            "ticks_executed": 100,
            "trades_count": 4,
            "win_rate": 0.5,
            "avg_pnl": 0.25,
            "total_pnl": 1.0,
            "no_signal_rate": 0.6,
            "avg_holding_sec": 90.0,
        }
        buf = io.StringIO()

        mod.emit_metrics(sample, output_format="json", output_path=None, stdout=buf)

        round_tripped = json.loads(buf.getvalue())
        assert round_tripped == sample
