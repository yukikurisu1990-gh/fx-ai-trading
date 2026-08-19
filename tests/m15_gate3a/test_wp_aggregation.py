"""Targeted-fix regression suite for `scripts/m15_gate3a/aggregation.py`.

Covers the contract Gate-decision rulings this Work PR implements — D-1
(crossed quotes refuse), D-2 (zero rejection tolerance, structurally), D-3 (the
six-field minute accounting and its identity), D-9 (duplicate minutes abort
after canonicalisation, claimed before any quality disposition) — and audit
required fixes RF-3, RF-4, RF-18, RF-24, RF-25, RF-26 and RF-29, plus the R-1
negative-control deletions and the R-2 term pinning.

House rules observed: no regex alternation in `pytest.raises(match=...)`, no
assertions on source text, no vacuous globs, no host state, no fail-open frozen
as expected behaviour, and the module's own exception type throughout.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from scripts.m15_gate3a.aggregation import (
    _SIDE_KEYS,
    AggregationError,
    aggregate_m15,
    to_pips,
)

START = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)


# --------------------------------------------------------------------------
# synthetic fixtures (no file, no real data, no calendar authored here)
# --------------------------------------------------------------------------
def _row(ts: Any, *, base: float = 1.10, half: float = 0.00005) -> dict:
    """One coherent, un-crossed synthetic M1 row on the non-JPY scale."""
    return {
        "ts": ts,
        "bid_o": base - half,
        "bid_h": base + 0.0002 - half,
        "bid_l": base - 0.0002 - half,
        "bid_c": base + 0.0001 - half,
        "ask_o": base + half,
        "ask_h": base + 0.0002 + half,
        "ask_l": base - 0.0002 + half,
        "ask_c": base + 0.0001 + half,
    }


def _jpy_row(ts: Any, *, base: float = 150.0, half: float = 0.01) -> dict:
    """One coherent, un-crossed synthetic M1 row on the JPY scale."""
    return {
        "ts": ts,
        "bid_o": base - half,
        "bid_h": base + 0.05 - half,
        "bid_l": base - 0.05 - half,
        "bid_c": base + 0.02 - half,
        "ask_o": base + half,
        "ask_h": base + 0.05 + half,
        "ask_l": base - 0.05 + half,
        "ask_c": base + 0.02 + half,
    }


def _bucket(start: datetime = START, n: int = 15) -> list[dict]:
    return [_row(start + timedelta(minutes=i), base=1.10 + i * 0.0001) for i in range(n)]


# Each entry crosses EXACTLY ONE bid/ask field pair while leaving both sides
# intra-side coherent, so the crossed-quote guard is the one that fires and the
# four cases are distinguishable without a regex alternation.
_CROSSED_SIDES: dict[str, dict[str, float]] = {
    "o": {
        "bid_o": 1.1,
        "bid_h": 1.2,
        "bid_l": 1.0,
        "bid_c": 1.05,
        "ask_o": 1.0,
        "ask_h": 1.25,
        "ask_l": 1.0,
        "ask_c": 1.1,
    },
    "h": {
        "bid_o": 1.0,
        "bid_h": 1.2,
        "bid_l": 1.0,
        "bid_c": 1.0,
        "ask_o": 1.05,
        "ask_h": 1.1,
        "ask_l": 1.0,
        "ask_c": 1.05,
    },
    "l": {
        "bid_o": 1.0,
        "bid_h": 1.0,
        "bid_l": 1.0,
        "bid_c": 1.0,
        "ask_o": 1.1,
        "ask_h": 1.1,
        "ask_l": 0.9,
        "ask_c": 1.1,
    },
    "c": {
        "bid_o": 1.0,
        "bid_h": 1.2,
        "bid_l": 1.0,
        "bid_c": 1.2,
        "ask_o": 1.05,
        "ask_h": 1.25,
        "ask_l": 1.0,
        "ask_c": 1.1,
    },
}


def _crossed_row(field: str, ts: datetime = START) -> dict:
    return {"ts": ts, **_CROSSED_SIDES[field]}


def _bar(**overrides: Any) -> dict:
    """A coherent CONSTRUCTED bar, as `aggregate_m15` would assemble it."""
    bar = {
        "ts": START,
        "n_source_bars": 15,
        "complete_bucket": True,
        "eligible": True,
        "bid_o": 1.0,
        "bid_h": 1.2,
        "bid_l": 0.9,
        "bid_c": 1.1,
        "ask_o": 1.01,
        "ask_h": 1.21,
        "ask_l": 0.91,
        "ask_c": 1.11,
        "spread_open": 0.01,
        "spread_close": 0.01,
        "pip_size": 0.0001,
    }
    bar.update(overrides)
    return bar


# --------------------------------------------------------------------------
# D-1 / §12.1-2 — crossed quotes are a HARD refusal, one test per field pair
# --------------------------------------------------------------------------
def test_d1_crossed_open_pair_refuses() -> None:
    with pytest.raises(AggregationError, match=r"crossed quote at .*: ask_o 1\.0 < bid_o 1\.1"):
        aggregate_m15([_crossed_row("o")], pair="EUR_USD")


def test_d1_crossed_high_pair_refuses() -> None:
    with pytest.raises(AggregationError, match=r"crossed quote at .*: ask_h 1\.1 < bid_h 1\.2"):
        aggregate_m15([_crossed_row("h")], pair="EUR_USD")


def test_d1_crossed_low_pair_refuses() -> None:
    with pytest.raises(AggregationError, match=r"crossed quote at .*: ask_l 0\.9 < bid_l 1\.0"):
        aggregate_m15([_crossed_row("l")], pair="EUR_USD")


def test_d1_crossed_close_pair_refuses() -> None:
    with pytest.raises(AggregationError, match=r"crossed quote at .*: ask_c 1\.1 < bid_c 1\.2"):
        aggregate_m15([_crossed_row("c")], pair="EUR_USD")


def test_d1_one_crossed_row_makes_the_whole_bucket_uncertifiable() -> None:
    """D-1.4-5: not a bar with `eligible: False`, and never a smaller count."""
    rows = _bucket(START, 15)
    rows[14] = _crossed_row("l", START + timedelta(minutes=14))
    with pytest.raises(AggregationError, match="bucket and file are not certifiable"):
        aggregate_m15(rows, pair="EUR_USD")


def test_d1_zero_spread_is_not_a_crossed_quote() -> None:
    """D-1.7: `ask == bid` is refused only by a separate cost/spread contract."""
    rows = []
    for i in range(15):
        row = _row(START + timedelta(minutes=i), base=1.10 + i * 0.0001, half=0.0)
        rows.append(row)
    bars, gap = aggregate_m15(rows, pair="EUR_USD")
    assert len(bars) == 1
    assert bars[0]["complete_bucket"] is True
    assert bars[0]["spread_open"] == 0.0
    assert bars[0]["spread_close"] == 0.0
    assert gap["complete_bucket_count"] == 1


def test_d1_crossed_quote_refusal_survives_optimised_mode() -> None:
    """D-1's observable outcome list: the refusal must not be a bare `assert`."""
    import subprocess
    import sys

    from scripts.ml_step4.evidence import repo_root

    sides = _CROSSED_SIDES["l"]
    body = "\n".join(
        [
            "from datetime import UTC, datetime",
            "from scripts.m15_gate3a.aggregation import AggregationError, aggregate_m15",
            f"row = {sides!r}",
            "row['ts'] = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)",
            "try:",
            "    aggregate_m15([row], pair='EUR_USD')",
            "except AggregationError as exc:",
            "    print('REFUSED', exc)",
            "else:",
            "    print('ACCEPTED')",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-O", "-c", body],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("REFUSED"), proc.stdout
    assert "ask_l" in proc.stdout


# --------------------------------------------------------------------------
# D-2 / §12.4 — zero rejection tolerance, structurally
# --------------------------------------------------------------------------
def test_d2_entry_point_exposes_no_tolerance_parameter() -> None:
    """No tolerance parameter, no numeric default, nothing to configure."""
    sig = inspect.signature(aggregate_m15)
    assert list(sig.parameters) == ["m1_rows", "pair", "expected_minutes"]
    assert sig.parameters["expected_minutes"].default is None
    for name, param in sig.parameters.items():
        assert param.default in (inspect.Parameter.empty, None), name
        lowered = name.lower()
        for token in ("toler", "threshold", "ratio", "max_drop", "allow", "lenient"):
            assert token not in lowered


def test_d2_rejection_tolerance_is_zero_at_every_scale() -> None:
    """One crossed row in fifteen refuses exactly as fifteen in fifteen do."""
    for crossed_count in (1, 7, 15):
        rows = _bucket(START, 15)
        for i in range(crossed_count):
            rows[i] = _crossed_row("l", START + timedelta(minutes=i))
        with pytest.raises(AggregationError, match="not certifiable"):
            aggregate_m15(rows, pair="EUR_USD")


# --------------------------------------------------------------------------
# D-9 / §12.3 — duplicate minutes
# --------------------------------------------------------------------------
def test_d9_duplicate_minute_aborts_with_no_silent_dedup() -> None:
    rows = _bucket(START, 15) + [_row(START + timedelta(minutes=7), base=1.2)]
    with pytest.raises(AggregationError, match="duplicate source minute"):
        aggregate_m15(rows, pair="EUR_USD")


def test_d9_alias_spelling_duplicates_after_canonicalisation() -> None:
    """Normalise first, then detect: 09:00+09:00 is 00:00Z, not a second minute."""
    jst = timezone(timedelta(hours=9))
    rows = [_row(START), _row(datetime(2025, 6, 2, 9, 0, tzinfo=jst), base=1.2)]
    with pytest.raises(AggregationError, match="duplicate source minute 2025-06-02T00:00:00"):
        aggregate_m15(rows, pair="EUR_USD")


def test_d9_nanosecond_differing_duplicate_never_opens_a_second_window() -> None:
    """The nanosecond variant is refused by the timestamp authority (B-1).

    It therefore never reaches the duplicate guard — which is the point: it can
    neither be silently deduplicated nor split one 15-minute window in two.
    """
    import pandas as pd

    base = pd.Timestamp("2025-06-02T00:00:00Z")
    nudged = base + pd.Timedelta(1, "ns")
    with pytest.raises(AggregationError, match="sub-microsecond resolution"):
        aggregate_m15([_row(base), _row(nudged, base=1.2)], pair="EUR_USD")


def test_d9_minute_is_claimed_before_any_quality_disposition() -> None:
    """A second record for a claimed minute is a duplicate whatever its quality."""
    with pytest.raises(AggregationError, match="duplicate source minute"):
        aggregate_m15([_row(START), _crossed_row("l", START)], pair="EUR_USD")


def test_d1_a_crossed_record_consumes_its_minute_and_still_refuses() -> None:
    """Under drop-and-count this reported `duplicate`; the crossed row is now fatal."""
    with pytest.raises(AggregationError, match=r"ask_l 0\.9 < bid_l 1\.0"):
        aggregate_m15([_crossed_row("l", START), _row(START)], pair="EUR_USD")


# --------------------------------------------------------------------------
# D-3 / §12.5-7 — six-field minute accounting
# --------------------------------------------------------------------------
_ACCOUNTING_KEYS = {
    "expected_source_minute_count",
    "observed_source_minute_count",
    "absent_source_minute_count",
    "rejected_source_minute_count",
    "usable_source_minute_count",
    "max_unavailable_gap_minutes",
}


def test_d3_without_a_calendar_the_expected_fields_are_none_not_zero() -> None:
    """D-6.1: closure is never inferred from absent data."""
    _, gap = aggregate_m15(_bucket(START, 15), pair="EUR_USD")
    acc = gap["minute_accounting"]
    assert set(acc) == _ACCOUNTING_KEYS
    assert acc["expected_source_minute_count"] is None
    assert acc["absent_source_minute_count"] is None
    assert acc["max_unavailable_gap_minutes"] is None
    assert acc["observed_source_minute_count"] == 15
    assert acc["usable_source_minute_count"] == 15
    assert acc["rejected_source_minute_count"] == 0


def test_d3_identity_holds_against_an_injected_expected_minute_set() -> None:
    expected = {START + timedelta(minutes=i) for i in range(30)}
    absent = {5, 6, 7, 8, 9, 20}
    rows = [_row(START + timedelta(minutes=i)) for i in range(30) if i not in absent]
    _, gap = aggregate_m15(rows, pair="EUR_USD", expected_minutes=expected)
    acc = gap["minute_accounting"]
    assert acc["expected_source_minute_count"] == 30
    assert acc["observed_source_minute_count"] == 24
    assert acc["usable_source_minute_count"] == 24
    assert acc["rejected_source_minute_count"] == 0
    assert acc["absent_source_minute_count"] == 6
    assert acc["expected_source_minute_count"] == (
        acc["usable_source_minute_count"]
        + acc["absent_source_minute_count"]
        + acc["rejected_source_minute_count"]
    )
    # longest run of consecutive EXPECTED-but-not-usable minutes: 5..9
    assert acc["max_unavailable_gap_minutes"] == 5


def test_d3_present_but_rejected_is_a_different_field_from_absent() -> None:
    """D-3.1-2: coverage deficit spans BOTH; a rejected minute is never 'missing'."""
    from scripts.m15_gate3a.aggregation import _build_minute_accounting

    expected = frozenset(START + timedelta(minutes=i) for i in range(3))
    acc = _build_minute_accounting(
        observed={START, START + timedelta(minutes=1)},
        usable={START},
        expected=expected,
    )
    assert acc["rejected_source_minute_count"] == 1
    assert acc["absent_source_minute_count"] == 1
    assert acc["usable_source_minute_count"] == 1
    assert acc["observed_source_minute_count"] == 2
    assert acc["expected_source_minute_count"] == 3
    assert acc["max_unavailable_gap_minutes"] == 2

    only_absent = _build_minute_accounting(observed={START}, usable={START}, expected=expected)
    assert only_absent["absent_source_minute_count"] == 2
    assert only_absent["rejected_source_minute_count"] == 0


def test_d3_a_rejected_minute_inside_the_calendar_refuses_rather_than_reporting_absent() -> None:
    expected = {START + timedelta(minutes=i) for i in range(15)}
    rows = _bucket(START, 15)
    rows[7] = _crossed_row("c", START + timedelta(minutes=7))
    with pytest.raises(AggregationError, match=r"ask_c 1\.1 < bid_c 1\.2"):
        aggregate_m15(rows, pair="EUR_USD", expected_minutes=expected)


def test_d3_accounting_identity_is_asserted_and_fails_closed() -> None:
    expected = {START + timedelta(minutes=i) for i in range(15)}
    rows = _bucket(START, 16)  # minute 15 is outside the injected authority
    with pytest.raises(AggregationError, match="minute accounting identity violated") as excinfo:
        aggregate_m15(rows, pair="EUR_USD", expected_minutes=expected)
    assert "outside the expected-slot authority" in str(excinfo.value)


def test_d3_usable_must_be_a_subset_of_observed() -> None:
    from scripts.m15_gate3a.aggregation import _build_minute_accounting

    with pytest.raises(AggregationError, match="not a subset of observed minutes"):
        _build_minute_accounting(observed=set(), usable={START}, expected=None)


def test_d3_expected_minutes_must_be_an_injected_set_of_utc_minutes() -> None:
    rows = _bucket(START, 15)
    with pytest.raises(AggregationError, match="must be a set or frozenset"):
        aggregate_m15(rows, pair="EUR_USD", expected_minutes=[START])
    with pytest.raises(AggregationError, match="must be a tz-aware datetime"):
        aggregate_m15(rows, pair="EUR_USD", expected_minutes={"2025-06-02T00:00:00Z"})
    with pytest.raises(AggregationError, match="expected_minutes entry rejected"):
        aggregate_m15(rows, pair="EUR_USD", expected_minutes={datetime(2025, 6, 2, 0, 0)})


def test_d3_expected_minutes_alias_duplicates_are_refused_after_canonicalisation() -> None:
    """Two set members that are one minute once canonicalised are a contradiction."""

    class _Alias(datetime):
        # Equal-by-instant datetimes collapse inside a `set`; this subclass keeps
        # both spellings distinct so the canonicalising guard is reachable.
        def __hash__(self) -> int:
            return 0

        def __eq__(self, other: object) -> bool:
            return self is other

    utc_spelling = _Alias(2025, 6, 2, 0, 0, tzinfo=UTC)
    jst_spelling = _Alias(2025, 6, 2, 9, 0, tzinfo=timezone(timedelta(hours=9)))
    with pytest.raises(AggregationError, match="twice after canonicalisation"):
        aggregate_m15(
            _bucket(START, 15),
            pair="EUR_USD",
            expected_minutes={utc_spelling, jst_spelling},
        )


def test_d3_max_unavailable_gap_is_measured_against_the_calendar_not_the_data() -> None:
    """Minutes the calendar does not expect neither start nor extend a run."""
    expected = {START + timedelta(minutes=i) for i in (0, 1, 2, 30, 31, 32)}
    rows = [_row(START), _row(START + timedelta(minutes=32))]
    _, gap = aggregate_m15(rows, pair="EUR_USD", expected_minutes=expected)
    acc = gap["minute_accounting"]
    assert acc["expected_source_minute_count"] == 6
    assert acc["absent_source_minute_count"] == 4
    # 1, 2, 30, 31 are consecutive EXPECTED slots even though 3..29 are not
    # expected at all; the observed-data gap between them is 31 minutes.
    assert acc["max_unavailable_gap_minutes"] == 4
    assert gap["max_gap_minutes"] == 31


# --------------------------------------------------------------------------
# §12.6 — `missing_minute_count` is a diagnostic, never coverage authority
# --------------------------------------------------------------------------
def test_missing_minute_count_is_an_observed_span_diagnostic_only() -> None:
    expected = {START + timedelta(minutes=i) for i in range(15)}
    rows = [_row(START + timedelta(minutes=i)) for i in range(2, 15)]  # 0,1 absent
    bars, gap = aggregate_m15(rows, pair="EUR_USD", expected_minutes=expected)
    # Nothing is missing BETWEEN the first and last observed minute...
    assert gap["missing_minute_count"] == 0
    assert gap["max_gap_minutes"] == 0
    # ...yet the coverage authority sees the two absent leading minutes.
    acc = gap["minute_accounting"]
    assert acc["absent_source_minute_count"] == 2
    assert acc["max_unavailable_gap_minutes"] == 2
    assert bars[0]["complete_bucket"] is False


# --------------------------------------------------------------------------
# §12.7 — a certifiable bar needs every contract-required minute usable
# --------------------------------------------------------------------------
def test_certifiable_bar_requires_all_fifteen_usable_minutes() -> None:
    bars, gap = aggregate_m15(_bucket(START, 15), pair="EUR_USD")
    assert bars[0]["ts"] == START
    assert bars[0]["n_source_bars"] == 15
    assert bars[0]["complete_bucket"] is True
    assert bars[0]["eligible"] is True
    assert gap["complete_bucket_count"] == 1
    assert gap["incomplete_bucket_count"] == 0

    bars14, gap14 = aggregate_m15(_bucket(START, 14), pair="EUR_USD")
    assert bars14[0]["n_source_bars"] == 14
    assert bars14[0]["complete_bucket"] is False
    assert bars14[0]["eligible"] is False
    assert gap14["complete_bucket_count"] == 0
    assert gap14["incomplete_bucket_count"] == 1


def test_accounting_identities_hold_over_two_buckets() -> None:
    rows = [_row(START + timedelta(minutes=i)) for i in range(22)]
    bars, gap = aggregate_m15(rows, pair="EUR_USD")
    acc = gap["minute_accounting"]
    assert gap["n_buckets_emitted"] == 2
    assert gap["complete_bucket_count"] + gap["incomplete_bucket_count"] == 2
    assert sum(b["n_source_bars"] for b in bars) == acc["usable_source_minute_count"] == 22
    assert gap["rows_ingested"] == acc["observed_source_minute_count"] == 22


# --------------------------------------------------------------------------
# RF-3 — the bar-level guard must enforce what it documents
# --------------------------------------------------------------------------
def test_rf3_bar_level_high_below_low_refuses() -> None:
    from scripts.m15_gate3a.aggregation import _assert_bar_coherent

    _assert_bar_coherent(_bar())  # non-vacuity floor: the coherent bar passes
    with pytest.raises(AggregationError, match=r"derived bar bid high 1\.0 < low 1\.2"):
        _assert_bar_coherent(_bar(bid_h=1.0, bid_l=1.2))


def test_rf3_bar_level_ohlc_bracket_failure_refuses() -> None:
    from scripts.m15_gate3a.aggregation import _assert_bar_coherent

    with pytest.raises(AggregationError, match="derived bar bid OHLC incoherent"):
        _assert_bar_coherent(_bar(bid_h=1.05))


def test_rf3_bar_level_crossed_relation_refuses() -> None:
    from scripts.m15_gate3a.aggregation import _assert_bar_coherent

    with pytest.raises(AggregationError, match=r"derived bar crossed: ask_h 1\.15 < bid_h 1\.2"):
        _assert_bar_coherent(_bar(ask_h=1.15))


def test_rf3_the_audits_exact_bar_is_refused() -> None:
    """`eligible: True`, `bid_h=1.0 < bid_l=1.2`, `ask_h=0.9 < bid_h` — was emitted."""
    from scripts.m15_gate3a.aggregation import _assert_bar_coherent

    with pytest.raises(AggregationError, match="derived bar bid high"):
        _assert_bar_coherent(_bar(bid_h=1.0, bid_l=1.2, ask_h=0.9))


def test_rf3_rf4_every_required_row_key_is_read_exactly_once() -> None:
    """A row that answers differently on each read cannot reach the bar."""

    class _CountingRow(dict):
        def __init__(self, base: dict) -> None:
            super().__init__(base)
            self.reads: dict[str, int] = {}

        def __getitem__(self, key: str) -> Any:
            self.reads[key] = self.reads.get(key, 0) + 1
            value = super().__getitem__(key)
            if key in _SIDE_KEYS and self.reads[key] > 1:
                return value + 10.0 * self.reads[key]
            return value

    honest = _bucket(START, 15)
    rows = _bucket(START, 15)
    two_faced = _CountingRow(rows[0])
    rows[0] = two_faced

    bars, _ = aggregate_m15(rows, pair="EUR_USD")
    assert [two_faced.reads[k] for k in _SIDE_KEYS] == [1] * len(_SIDE_KEYS)
    assert bars[0]["bid_o"] == honest[0]["bid_o"]
    assert bars[0]["ask_o"] == honest[0]["ask_o"]
    assert bars[0]["bid_h"] == max(r["bid_h"] for r in honest)
    assert bars[0]["ask_h"] == max(r["ask_h"] for r in honest)
    assert bars[0]["bid_l"] == min(r["bid_l"] for r in honest)


# --------------------------------------------------------------------------
# RF-4 — one record object is one source minute
# --------------------------------------------------------------------------
def test_rf4_one_row_object_presented_fifteen_times_refuses() -> None:
    class _RepeatedRow(list):
        """Yields ONE row object 15 times, walking its `ts` between yields."""

        def __init__(self, row: dict, n: int = 15) -> None:
            super().__init__([row] * n)
            self._row = row
            self._n = n

        def __iter__(self) -> Any:
            for i in range(self._n):
                self._row["ts"] = START + timedelta(minutes=i)
                yield self._row

    with pytest.raises(AggregationError, match="same row object appears at indices 0 and 1"):
        aggregate_m15(_RepeatedRow(_row(START)), pair="EUR_USD")


def test_rf4_distinct_row_objects_for_the_same_minute_still_refuse() -> None:
    """The identity guard does not replace the duplicate-minute guard."""
    with pytest.raises(AggregationError, match="duplicate source minute"):
        aggregate_m15([_row(START), _row(START, base=1.2)], pair="EUR_USD")


# --------------------------------------------------------------------------
# RF-18 — `spread_open` is emitted, value-pinned and guarded
# --------------------------------------------------------------------------
def test_rf18_spread_open_value_pinned_non_jpy() -> None:
    rows = [_row(START + timedelta(minutes=i), base=1.10, half=0.00005) for i in range(15)]
    bars, _ = aggregate_m15(rows, pair="EUR_USD")
    bar = bars[0]
    assert bar["pip_size"] == 0.0001
    assert bar["spread_open"] == pytest.approx(0.0001, rel=1e-9)
    assert bar["spread_close"] == pytest.approx(0.0001, rel=1e-9)
    assert bar["spread_open"] == bar["ask_o"] - bar["bid_o"]
    assert to_pips(bar["spread_open"], "EUR_USD") == pytest.approx(1.0, rel=1e-9)


def test_rf18_spread_open_value_pinned_jpy() -> None:
    rows = [_jpy_row(START + timedelta(minutes=i), base=150.0, half=0.01) for i in range(15)]
    bars, _ = aggregate_m15(rows, pair="USD_JPY")
    bar = bars[0]
    assert bar["pip_size"] == 0.01
    assert bar["spread_open"] == pytest.approx(0.02, rel=1e-9)
    assert bar["spread_close"] == pytest.approx(0.02, rel=1e-9)
    assert bar["spread_open"] == bar["ask_o"] - bar["bid_o"]
    assert to_pips(bar["spread_open"], "USD_JPY") == pytest.approx(2.0, rel=1e-9)


def test_rf18_spread_open_comes_from_the_buckets_first_usable_minute() -> None:
    rows = [_row(START + timedelta(minutes=i), base=1.10) for i in range(1, 15)]
    rows.append(_row(START, base=1.10, half=0.0003))  # widest spread, earliest minute
    rows.reverse()  # supplied out of order on purpose
    bars, _ = aggregate_m15(rows, pair="EUR_USD")
    bar = bars[0]
    assert bar["ts"] == START
    assert bar["spread_open"] == pytest.approx(0.0006, rel=1e-9)
    assert bar["spread_close"] == pytest.approx(0.0001, rel=1e-9)


def test_rf18_non_finite_spread_open_refuses_through_the_public_api() -> None:
    """Finite, coherent, un-crossed inputs whose OPEN-side spread overflows."""
    row = {
        "ts": START,
        "bid_o": -1.7e308,
        "bid_h": 0.0,
        "bid_l": -1.7e308,
        "bid_c": 0.0,
        "ask_o": 1.7e308,
        "ask_h": 1.7e308,
        "ask_l": 0.0,
        "ask_c": 0.0,
    }
    with pytest.raises(AggregationError, match="'spread_open' is non-finite"):
        aggregate_m15([row], pair="EUR_USD")


# --------------------------------------------------------------------------
# RF-24 — one-minute gaps are counted
# --------------------------------------------------------------------------
def test_rf24_one_minute_gaps_are_counted() -> None:
    rows = [_row(START + timedelta(minutes=i)) for i in range(0, 15, 2)]
    _, gap = aggregate_m15(rows, pair="EUR_USD")
    assert gap["missing_minute_count"] == 7
    assert gap["max_gap_minutes"] == 1
    assert gap["total_missing_source_minutes_within_emitted_buckets"] == 7


# --------------------------------------------------------------------------
# RF-25 — the spread sign guards
# --------------------------------------------------------------------------
def test_rf25_negative_spread_close_refuses() -> None:
    from scripts.m15_gate3a.aggregation import _assert_bar_coherent

    with pytest.raises(AggregationError, match="negative quoted spread_close"):
        _assert_bar_coherent(_bar(spread_close=-0.01))


def test_rf25_negative_spread_open_refuses() -> None:
    from scripts.m15_gate3a.aggregation import _assert_bar_coherent

    with pytest.raises(AggregationError, match="negative quoted spread_open"):
        _assert_bar_coherent(_bar(spread_open=-0.01))


def test_rf25_non_finite_derived_values_refuse() -> None:
    from scripts.m15_gate3a.aggregation import _assert_bar_coherent

    with pytest.raises(AggregationError, match="'spread_close' is non-finite"):
        _assert_bar_coherent(_bar(spread_close=float("inf")))
    with pytest.raises(AggregationError, match="'bid_h' is non-finite"):
        _assert_bar_coherent(_bar(bid_h=float("nan")))


# --------------------------------------------------------------------------
# RF-26 / RF-29 — input shape and the documented exception type
# --------------------------------------------------------------------------
def test_rf26_lazy_row_evidence_is_refused() -> None:
    rows = _bucket(START, 15)
    for lazy in ((r for r in rows), iter(rows), tuple(rows)):
        with pytest.raises(AggregationError, match="must be a list of synthetic M1 dicts"):
            aggregate_m15(lazy, pair="EUR_USD")  # type: ignore[arg-type]


def test_rf29_missing_side_key_raises_the_documented_exception_type() -> None:
    for key in _SIDE_KEYS:
        row = _row(START)
        del row[key]
        with pytest.raises(AggregationError, match="missing side key"):
            aggregate_m15([row], pair="EUR_USD")


def test_rf29_missing_timestamp_raises_the_documented_exception_type() -> None:
    row = _row(START)
    del row["ts"]
    with pytest.raises(AggregationError, match="has no 'ts' key"):
        aggregate_m15([row], pair="EUR_USD")


def test_rf29_a_non_mapping_row_raises_the_documented_exception_type() -> None:
    with pytest.raises(AggregationError, match="M1 row must be a mapping"):
        aggregate_m15([("ts", START)], pair="EUR_USD")  # type: ignore[list-item]


def test_rf29_an_unreadable_row_key_raises_the_documented_exception_type() -> None:
    """A mapping that fails on read fails closed as an `AggregationError`."""

    class _UnreadableRow(dict):
        def __getitem__(self, key: str) -> Any:
            if key == "bid_h":
                raise RuntimeError("storage unavailable")
            return super().__getitem__(key)

    with pytest.raises(AggregationError, match="could not be read"):
        aggregate_m15([_UnreadableRow(_row(START))], pair="EUR_USD")


# --------------------------------------------------------------------------
# empty and calendar-only edges
# --------------------------------------------------------------------------
def test_no_rows_yields_no_bars_and_a_zeroed_observed_accounting() -> None:
    bars, gap = aggregate_m15([], pair="EUR_USD")
    assert bars == []
    assert gap["n_buckets_emitted"] == 0
    assert gap["complete_bucket_count"] == 0
    assert gap["rows_ingested"] == 0
    acc = gap["minute_accounting"]
    assert acc["observed_source_minute_count"] == 0
    assert acc["usable_source_minute_count"] == 0
    assert acc["rejected_source_minute_count"] == 0
    assert acc["expected_source_minute_count"] is None
    assert acc["absent_source_minute_count"] is None


def test_a_calendar_with_no_source_rows_reports_absence_not_closure() -> None:
    expected = {START + timedelta(minutes=i) for i in range(15)}
    bars, gap = aggregate_m15([], pair="EUR_USD", expected_minutes=expected)
    assert bars == []
    acc = gap["minute_accounting"]
    assert acc["expected_source_minute_count"] == 15
    assert acc["absent_source_minute_count"] == 15
    assert acc["usable_source_minute_count"] == 0
    assert acc["rejected_source_minute_count"] == 0
    assert acc["max_unavailable_gap_minutes"] == 15


# --------------------------------------------------------------------------
# R-1 / R-2 — deletions and pinned terms
# --------------------------------------------------------------------------
def test_r1_single_valued_self_attestations_are_deleted_not_reported() -> None:
    bars, gap = aggregate_m15(_bucket(START, 15), pair="EUR_USD")
    for key in (
        "imputation",
        "synthetic_weekend_bars",
        "mid_price_constructed",
        "dropped_crossed_quote_rows",
        "rows_retained",
        "buckets_fully_dropped",
        "all_rows_dropped",
        "n_eligible",
        "n_incomplete",
    ):
        assert key not in gap, key
    # The property `mid_price_constructed: False` asserted, measured instead.
    for key in ("mid", "mid_o", "mid_h", "mid_l", "mid_c", "open", "close"):
        assert key not in bars[0], key


def test_r1_no_imputation_and_no_synthetic_bars_are_observable() -> None:
    fri = datetime(2025, 5, 30, 20, 45, tzinfo=UTC)
    mon = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    bars, gap = aggregate_m15([_row(fri), _row(mon, base=1.2)], pair="EUR_USD")
    # Only the two windows that actually held a source minute exist.
    assert [b["ts"] for b in bars] == [fri, mon]
    assert [b["n_source_bars"] for b in bars] == [1, 1]
    assert gap["missing_whole_buckets"] > 0  # counted, never fabricated
    assert gap["minute_accounting"]["usable_source_minute_count"] == 2


def test_r2_n_source_bars_counts_distinct_usable_minutes_not_reads() -> None:
    rows = _bucket(START, 15)
    rows.reverse()
    bars, gap = aggregate_m15(rows, pair="EUR_USD")
    assert bars[0]["n_source_bars"] == 15
    assert gap["rows_ingested"] == 15
    assert gap["minute_accounting"]["usable_source_minute_count"] == 15
    assert bars[0]["n_source_bars"] == gap["minute_accounting"]["usable_source_minute_count"]


def test_r2_gap_report_key_set_is_pinned() -> None:
    _, gap = aggregate_m15(_bucket(START, 15), pair="EUR_USD")
    assert set(gap) == {
        "pair",
        "pip_size",
        "n_buckets_emitted",
        "complete_bucket_count",
        "incomplete_bucket_count",
        "missing_minute_count",
        "max_gap_minutes",
        "total_missing_source_minutes_within_emitted_buckets",
        "missing_whole_buckets",
        "rows_ingested",
        "minute_accounting",
    }
    assert gap["pair"] == "EUR_USD"
