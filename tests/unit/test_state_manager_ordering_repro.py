"""Deterministic reproduction of R-1 — StateManager ordering non-determinism.

Hypothesis under test (R-1 from ``docs/design/flaky_state_manager_ordering_memo.md``):

    ``StateManager.open_instruments()`` ranks rows per instrument with
    ``ORDER BY event_time_utc DESC, position_snapshot_id DESC``.  When the
    injected ``Clock`` returns the same ``event_time_utc`` for several
    consecutive calls (as ``FixedClock`` does in tests, and as a single
    wall-clock millisecond can in production), every row in the partition
    ties on ``event_time_utc``.  The tie-break falls entirely on
    ``position_snapshot_id DESC``.

    ``position_snapshot_id`` is a ULID whose 16-char suffix is 80 bits of
    uniform random (``secrets.randbits`` in ``common/ulid.py``).  So the
    lexicographic order of two same-millisecond ULIDs is effectively random.

    Consequence: after ``on_fill`` → ``on_close`` for the same instrument
    with same ``event_time_utc``, whether ``open_instruments()`` returns
    the close row or the open row as "latest" is ULID-suffix-dependent.
    When the open row wins the tie-break, a subsequent ``on_fill`` wrongly
    records ``event_type='add'`` — the reproduction target.

These tests do NOT modify any src file.  They monkeypatch
``generate_ulid`` inside the state_manager module to force chosen ULIDs
and make the bug fire deterministically.

Scope contract (see Designer Freeze for F-2 step 1):
  - read-only: no src change, no DDL change, no existing-test change
  - additive only: new file
  - ``test_fill_after_close_writes_open_not_add`` in
    ``test_state_manager_write.py`` is left untouched (the flaky test
    itself is the motivating symptom; this file explains *why*)
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
# The bug surfaces only when two same-millisecond rows (open vs close)
# end up on opposite sides of the ``position_snapshot_id DESC`` tie-break.
# We monkeypatch ``generate_ulid`` inside the state_manager module so each
# call returns a chosen ULID from a queue.  Both strings MUST be valid
# ULIDs (26 uppercase Crockford base32 chars — alphabet excludes I, L, O, U).
#
# Suffixes use only ``A`` and ``Z``, both in the Crockford alphabet.
# ``A`` is the smallest letter in that alphabet, ``Z`` the largest, so
# comparing two ULIDs that differ only in the suffix reduces to comparing
# ``A...A`` vs ``Z...Z``, where the Z variant is strictly greater.
#
# The timestamp prefix is deliberately identical across IDs in a given
# test so the lexicographic comparison is decided entirely by the suffix.


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
# R-1 reproduction tests
# ----------------------------------------------------------------------


class TestR1OpenInstrumentsTieBreak:
    """Reproduce the open_instruments() tie-break non-determinism."""

    def test_fires_when_open_psid_greater_than_close_psid(self, engine, monkeypatch) -> None:
        """R-1 canonical repro.

        Sequence:
          1. on_fill  -> psid_open  = large (Z...)
          2. on_close -> psid_close = small (A...)  [ceid consumed but ignored]
          3. on_fill again -> queries open_instruments()

        All three rows share ``event_time_utc`` via FixedClock, so the
        ORDER BY falls entirely on ``position_snapshot_id DESC``.  Since
        psid_open > psid_close lexicographically, the window function picks
        the OPEN row as "latest" and reports EURUSD as still open.  The
        third on_fill therefore writes ``event_type='add'`` — the exact
        production bug masquerading as a flaky test.
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

        # This is the BUG assertion: the reproduction succeeds when the
        # post-close re-fill is wrongly recorded as 'add'.
        assert last_fill_row.event_type == "add", (
            "R-1 NOT reproduced — re-open wrote 'open' despite adverse"
            " ULID ordering.  Check that _sequence_ulids fed the state_manager"
            " module binding, not the ulid module."
        )

    def test_does_not_fire_when_open_psid_less_than_close_psid(self, engine, monkeypatch) -> None:
        """Control case — favorable ordering, bug silent.

        Same three-call shape but with psid_open < psid_close.  Tie-break
        picks the CLOSE row as latest, EURUSD drops out of
        open_instruments, and the re-fill correctly records 'open'.
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

    def test_open_instruments_directly_returns_closed_instrument_under_adverse_ulids(
        self, engine, monkeypatch
    ) -> None:
        """Narrow the observation to ``open_instruments()`` itself.

        After on_fill + on_close under adverse ULID ordering, the account
        *should* hold no open instruments.  With R-1 unfixed, the query
        returns {'EURUSD'} because the close row loses the tie-break.
        """
        _sequence_ulids(
            monkeypatch,
            sequence=[
                _ulid_large(0),  # on_fill  (open)   — wins tie-break
                _ulid_small(0),  # on_close (pos)    — loses tie-break
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

        # Intended invariant (violated under R-1):
        #   open_instruments() == frozenset() after close
        # Observed under R-1:
        assert sm.open_instruments() == frozenset({"EURUSD"}), (
            "R-1 NOT reproduced at the open_instruments() layer — the query"
            " returned the closed instrument as expected, meaning the ORDER BY"
            " is resolving deterministically without relying on"
            " position_snapshot_id.  Investigate alternate hypotheses R-2/R-3."
        )


class TestR1SameFlawInOtherQueries:
    """The same ``event_time_utc DESC, position_snapshot_id DESC`` ordering is
    reused by ``open_position_details()`` and ``_last_open_snapshot_id()``.
    Both share the bug surface, so a fix must address all three call sites,
    not just ``open_instruments()``.
    """

    def test_open_position_details_returns_closed_instrument_under_adverse_ulids(
        self, engine, monkeypatch
    ) -> None:
        """``open_position_details`` uses the same ORDER BY — same bug.

        If a fix only touches ``open_instruments``, this query continues
        to leak closed positions to the exit gate.
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
        assert leaked, (
            "R-1 NOT reproduced in open_position_details — the closed"
            " position did not leak.  If open_instruments() reproduced but"
            " this did not, the two ORDER BY sites have diverged; re-check"
            " state_manager.py:155 and state_manager.py:191."
        )

    def test_last_open_snapshot_id_picks_wrong_row_under_adverse_ulids(
        self, engine, monkeypatch
    ) -> None:
        """``_last_open_snapshot_id`` shares the ORDER BY and is called by
        ``on_close`` to link the close_events.position_snapshot_id field.

        Under R-1, the linkage is correct only because a second on_close
        for the same order is not typical in paper mode.  Still, the same
        tie-break flaw exists in the SQL and must be recorded.  We assert
        that two open/add rows with divergent ULID ordering produce the
        expected "larger ULID wins" behaviour under tie.
        """
        _sequence_ulids(
            monkeypatch,
            sequence=[
                _ulid_small(0),  # on_fill #1 (open) — smaller
                _ulid_large(0),  # on_fill #2 (add)  — larger
            ],
        )
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=500, avg_price=1.11)

        # With event_time_utc tied, the ORDER BY picks the larger ULID
        # (_ulid_large(0)).  This is the "add" row, which happens to be
        # correct here — but the determinism comes from ULID suffix, not
        # insertion order.  The test documents the contract: if the ULID
        # for the second fill were smaller, _last_open_snapshot_id would
        # return the first fill's psid instead, which is the latent flaw.
        picked = sm._last_open_snapshot_id(order_id="o1", instrument="EURUSD")
        assert picked == _ulid_large(0), (
            f"expected larger-ULID row to win tie-break; got {picked!r}"
        )
