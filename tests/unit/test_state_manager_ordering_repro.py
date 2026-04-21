"""Order-independence invariants for StateManager — R-1 fix (Cycle 6.12).

Background (R-1, see ``docs/design/flaky_state_manager_ordering_memo.md``):

    The 6.7c versions of ``open_instruments()``,
    ``open_position_details()`` and ``_last_open_snapshot_id()`` ranked
    rows per (instrument | order_id) with
    ``ORDER BY event_time_utc DESC, position_snapshot_id DESC``.  When
    the injected ``Clock`` returned the same ``event_time_utc`` for
    several consecutive calls (FixedClock in tests, a single wall-clock
    millisecond in production), every row in the partition tied on
    ``event_time_utc``.  The tie-break fell entirely on
    ``position_snapshot_id DESC``, whose last 80 bits are
    ``secrets.randbits`` — non-monotonic and effectively random.

    Adverse ULID orderings made the close row lose the tie-break, so
    the queries returned closed positions as still open and the next
    on_fill recorded ``event_type='add'`` instead of ``'open'``.

Cycle 6.12 fix (方針 B): replace the order-dependent ranking with
order-independent set/count/existence queries:

  * ``open_instruments()``  — ``GROUP BY instrument HAVING SUM(open|add) > SUM(close)``
  * ``open_position_details()`` — open rows whose order_id has no close row
  * ``_last_open_snapshot_id()`` — the unique 'open' row for the order_id

This file was originally added in PR #109 to *reproduce* the bug.  Each
test was authored with the bug-firing assertion (e.g.
``event_type == 'add'``) so a failure proved the fix.  After PR #109
merged and the fix landed, the assertions are flipped here so the same
adversarial ULID sequences instead verify the invariant — the queries
now ignore ULID ordering altogether.

Scope: read-only fixtures over an in-memory SQLite engine, monkeypatch
``generate_ulid`` inside the state_manager module to force chosen ULIDs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.services.state_manager import StateManager

_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


# ----------------------------------------------------------------------
# DDL — copied from test_state_manager_write.py (kept self-contained so
# this file does not depend on the existing test module).
# ----------------------------------------------------------------------

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

_DDL_ORDER_TRANSACTIONS = """
CREATE TABLE order_transactions (
    broker_txn_id        TEXT NOT NULL,
    account_id           TEXT NOT NULL,
    order_id             TEXT,
    transaction_type     TEXT NOT NULL,
    transaction_time_utc TEXT NOT NULL,
    payload              TEXT,
    received_at_utc      TEXT NOT NULL,
    PRIMARY KEY (broker_txn_id, account_id)
)
"""

_DDL_OUTBOX = """
CREATE TABLE secondary_sync_outbox (
    outbox_id       TEXT PRIMARY KEY,
    table_name      TEXT NOT NULL,
    primary_key     TEXT NOT NULL,
    version_no      BIGINT NOT NULL DEFAULT 0,
    payload_json    TEXT NOT NULL,
    enqueued_at     TEXT NOT NULL,
    acked_at        TEXT,
    last_error      TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    run_id          TEXT,
    environment     TEXT,
    code_version    TEXT,
    config_version  TEXT
)
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_CLOSE_EVENTS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
        conn.execute(text(_DDL_OUTBOX))
    yield eng
    eng.dispose()


def _make_sm(engine, account_id: str = "acc-1") -> StateManager:
    return StateManager(engine, account_id=account_id, clock=FixedClock(_NOW))


def _positions_rows(engine, *, account_id: str = "acc-1") -> list:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT position_snapshot_id, event_type, event_time_utc, order_id"
                " FROM positions WHERE account_id = :aid"
                " ORDER BY event_time_utc, position_snapshot_id"
            ),
            {"aid": account_id},
        ).fetchall()


# ----------------------------------------------------------------------
# ULID sequencing helper
# ----------------------------------------------------------------------
#
# The original bug surfaced only when two same-millisecond rows (open vs
# close) ended up on opposite sides of the ``position_snapshot_id DESC``
# tie-break.  We monkeypatch ``generate_ulid`` inside the state_manager
# module so each call returns a chosen ULID from a queue.  Both strings
# MUST be valid ULIDs (26 uppercase Crockford base32 chars — alphabet
# excludes I, L, O, U).
#
# Suffixes use only ``A`` and ``Z``, both in the Crockford alphabet.
# ``A`` is the smallest letter in that alphabet, ``Z`` the largest, so
# comparing two ULIDs that differ only in the suffix reduces to comparing
# ``A...A`` vs ``Z...Z``, where the Z variant is strictly greater.
#
# Post-fix the queries are order-independent, so these adversarial
# orderings now act as REGRESSION GUARDS: any future change that
# reintroduces a ULID-dependent tie-break would re-break these tests.


_ULID_PREFIX = "01HZ000000"  # 10 chars = timestamp portion (identical across IDs)
_ULID_SUFFIX_SMALL = "A" * 16  # lexicographically smallest letter-only suffix
_ULID_SUFFIX_LARGE = "Z" * 16  # lexicographically largest letter-only suffix


def _ulid_small(index: int = 0) -> str:
    """Return a lex-small ULID with an optional index char for uniqueness.

    We reserve the last char as an index marker so multiple "small" ULIDs
    in one test still have distinct PKs.  The resulting ULID remains
    lexicographically smaller than any ``_ulid_large`` because all other
    suffix chars are ``A`` vs ``Z``.
    """
    return _ULID_PREFIX + "A" * 15 + _crockford_digit(index)


def _ulid_large(index: int = 0) -> str:
    return _ULID_PREFIX + "Z" * 15 + _crockford_digit(index)


_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _crockford_digit(i: int) -> str:
    return _CROCKFORD[i % 32]


def _sequence_ulids(monkeypatch, sequence: list[str]) -> None:
    """Make ``generate_ulid`` inside state_manager return *sequence* in order.

    Extra calls (if any) fall back to the real implementation so a test
    does not accidentally crash if state_manager grows an additional
    internal ULID call.
    """
    import fx_ai_trading.services.state_manager as sm_mod

    real = sm_mod.generate_ulid
    it = iter(sequence)
    used_fallback = count()

    def stub() -> str:
        try:
            return next(it)
        except StopIteration:
            # Fallback to real ULID to keep the test runnable if an extra
            # call appears; the outer assertions target the controlled
            # prefix.
            next(used_fallback)
            return real()

    monkeypatch.setattr(sm_mod, "generate_ulid", stub)


# ----------------------------------------------------------------------
# R-1 fix invariants
# ----------------------------------------------------------------------


class TestR1FixOnFillEventType:
    """``on_fill`` must record ``event_type='open'`` for a re-fill after
    close, regardless of the relative ULID ordering of the open vs close
    rows.  Pre-fix the answer depended on ``position_snapshot_id`` lex
    order under same-millisecond ties; post-fix it depends only on the
    structural open/close balance per instrument.
    """

    def test_re_open_after_close_writes_open_under_adverse_ulids(self, engine, monkeypatch) -> None:
        """Adverse ordering: open psid > close psid (lex-greater).

        Sequence:
          1. on_fill  -> psid_open  = large (Z...)
          2. on_close -> psid_close = small (A...)  [ceid consumed but ignored]
          3. on_fill again -> queries open_instruments()

        All three rows share ``event_time_utc`` via FixedClock.  Under R-1
        (window function + ULID DESC tie-break) the OPEN row would win
        the rank-1 slot and EURUSD would appear "still held", forcing the
        third on_fill to record ``event_type='add'``.  Post-fix the query
        is count-based and order-independent, so the third on_fill
        correctly records ``event_type='open'``.
        """
        _sequence_ulids(
            monkeypatch,
            sequence=[
                _ulid_large(0),  # on_fill #1  (open)
                _ulid_small(0),  # on_close    (positions close row)
                _ulid_small(1),  # on_close    (close_events row)
                _ulid_large(2),  # on_fill #2  (the re-open)
            ],
        )

        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )
        sm.on_fill(order_id="o2", instrument="EURUSD", units=1000, avg_price=1.12)

        rows = _positions_rows(engine)
        last_fill_row = next(r for r in rows if r.order_id == "o2")

        assert last_fill_row.event_type == "open", (
            "R-1 regression: re-open after close recorded 'add' under adverse"
            " ULID ordering.  open_instruments() / on_fill must not depend on"
            " position_snapshot_id lex order."
        )

    def test_re_open_after_close_writes_open_under_favorable_ulids(
        self, engine, monkeypatch
    ) -> None:
        """Favorable ordering: open psid < close psid.  Pre-fix this case
        also produced 'open' (the bug only manifested under adverse
        orderings); the test stays here as a control proving determinism
        across both sides of the original tie-break.
        """
        _sequence_ulids(
            monkeypatch,
            sequence=[
                _ulid_small(0),  # on_fill #1  (open)
                _ulid_large(0),  # on_close    (positions close row)
                _ulid_large(1),  # on_close    (close_events row)
                _ulid_small(2),  # on_fill #2  (the re-open)
            ],
        )

        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )
        sm.on_fill(order_id="o2", instrument="EURUSD", units=1000, avg_price=1.12)

        rows = _positions_rows(engine)
        last_fill_row = next(r for r in rows if r.order_id == "o2")
        assert last_fill_row.event_type == "open"


class TestR1FixOpenReadQueries:
    """``open_instruments()`` and ``open_position_details()`` must report
    "no open positions" once an instrument has been closed, regardless of
    the relative ULID ordering of the open vs close rows.
    """

    def test_open_instruments_excludes_closed_instrument_under_adverse_ulids(
        self, engine, monkeypatch
    ) -> None:
        """Direct narrow-scope check on ``open_instruments()``.

        After on_fill + on_close, the account holds no open instruments.
        Under R-1 the close row could lose the tie-break and the query
        wrongly returned ``{'EURUSD'}``.  Post-fix the count-based query
        returns ``frozenset()`` regardless of ULID layout.
        """
        _sequence_ulids(
            monkeypatch,
            sequence=[
                _ulid_large(0),  # on_fill  (open)   — would have won pre-fix tie-break
                _ulid_small(0),  # on_close (pos)    — would have lost pre-fix tie-break
                _ulid_small(1),  # on_close (ce)
            ],
        )

        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )

        assert sm.open_instruments() == frozenset(), (
            "R-1 regression: open_instruments() leaked a closed instrument"
            " under adverse ULID ordering.  The query must use a count-based"
            " (open|add vs close) comparison, not row ranking."
        )

    def test_open_position_details_excludes_closed_instrument_under_adverse_ulids(
        self, engine, monkeypatch
    ) -> None:
        """``open_position_details`` must drop the closed instrument under
        the same adverse ULID layout that broke ``open_instruments``
        pre-fix.  The two queries share the bug surface and so must share
        the fix.
        """
        _sequence_ulids(
            monkeypatch,
            sequence=[
                _ulid_large(0),  # on_fill
                _ulid_small(0),  # on_close (pos)
                _ulid_small(1),  # on_close (ce)
            ],
        )
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )

        details = sm.open_position_details()
        leaked = [d for d in details if d.instrument == "EURUSD"]
        assert leaked == [], (
            "R-1 regression: open_position_details() leaked a closed position"
            " under adverse ULID ordering.  The query must filter via NOT EXISTS"
            " on a matching close row, not row ranking."
        )


class TestR1FixLastOpenSnapshotId:
    """``_last_open_snapshot_id`` is called by ``on_close`` to populate
    ``close_events.position_snapshot_id``.  Under L2 (1 order = 1 position)
    each order_id has exactly one 'open' row, so the link target must be
    that open row's psid regardless of any later fills.
    """

    def test_returns_open_row_psid_under_adverse_ulids(self, engine, monkeypatch) -> None:
        """Two fills for the same order_id with adverse ULID ordering.

        Sequence:
          1. on_fill #1 -> writes 'open' with the SMALL ULID (smaller psid)
          2. on_fill #2 -> instrument now held → writes 'add' with the
             LARGE ULID (larger psid)

        Pre-fix ``_last_open_snapshot_id`` ordered by
        ``event_time_utc DESC, position_snapshot_id DESC LIMIT 1``,
        picking the LARGER psid (the add row).  The "correct" answer
        depended on which psid happened to be larger.

        Post-fix the function returns the unique 'open' row for the
        order, which is the position's identity event and the natural
        audit anchor — independent of ULID ordering.
        """
        _sequence_ulids(
            monkeypatch,
            sequence=[
                _ulid_small(0),  # on_fill #1 (open) — smaller psid
                _ulid_large(0),  # on_fill #2 (add)  — larger psid
            ],
        )
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=500, avg_price=1.11)

        picked = sm._last_open_snapshot_id(order_id="o1", instrument="EURUSD")
        assert picked == _ulid_small(0), (
            "R-1 regression: _last_open_snapshot_id returned a non-open row"
            f" ({picked!r}) instead of the unique 'open' row for the order."
        )
