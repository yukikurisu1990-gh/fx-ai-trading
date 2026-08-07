"""Regression tests for the second source-audit re-check (BL-1..BL-5, RF-1..RF-11).

Every **BL-tagged** test fails against the implementation it replaces and passes
against this one; the fix note records the failing-before evidence per blocker.

The **RF-tagged** tests are a different thing and are labelled as such: RF-2,
RF-9, RF-10 and RF-11 were *coverage gaps*, not defects — the source already
behaved correctly and simply had nothing pinning it, so those tests pass on the
previous implementation too. The internal audit caught an earlier version of
this docstring claiming otherwise for the whole module; in a file whose purpose
is evidence, that distinction is the point.

Nothing in this module reads real data, derives real M15, computes a real
checksum or spread, trains, validates, evaluates or executes anything.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a.aggregation import AggregationError, aggregate_m15
from scripts.m15_gate3a.cost_schema import CostSchemaError, validate_cost_table
from scripts.m15_gate3a.no_overlap import (
    NoOverlapError,
    assert_forward_bounds,
    assert_per_file_bounds,
)
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_gate3a.path_authority import (
    PathAuthorityError,
    is_within,
    normalise_spelling,
    resolve_candidate,
)
from scripts.m15_gate3a.timeutil import TimestampError, to_utc, to_utc_minute
from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError
from tests.m15_gate3a.roster_fixtures import design_roster, file_record, forward_roster

START = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
PIP_NON_JPY = 0.0001
# Anchored to this file, never the working directory: a cwd-relative read
# silently yields nothing and makes a source-scanning test pass vacuously.
REPO_ROOT = Path(__file__).resolve().parents[2]


def _row(ts: Any, **over: Any) -> dict[str, Any]:
    row = {
        "ts": ts,
        "bid_o": 1.10,
        "bid_h": 1.1002,
        "bid_l": 1.0998,
        "bid_c": 1.1001,
        "ask_o": 1.1001,
        "ask_h": 1.1003,
        "ask_l": 1.0999,
        "ask_c": 1.1002,
    }
    row.update(over)
    return row


# ==========================================================================
# BL-1 — the T-7 proof must be bound to real, distinct, canonical evidence
# ==========================================================================


class LyingSequence(Sequence):
    """``__len__`` and iteration disagree — the exact BL-1 reproduction.

    ``Sequence`` is an ABC; nothing forces the two to agree. The previous guard
    trusted ``len()`` for ``expected_count`` and counted the loop separately,
    so this container produced ``files_checked=0`` *and* the proof token.
    """

    def __init__(self, declared: int, yields: list[Any]) -> None:
        self._declared = declared
        self._yields = yields

    def __len__(self) -> int:
        return self._declared

    def __getitem__(self, index: int) -> Any:
        return self._yields[index]

    def __iter__(self):
        return iter(self._yields)


class UnstableSequence(Sequence):
    """Yields different records on every pass — evidence that cannot be re-scanned."""

    def __init__(self, records: list[Any]) -> None:
        self._records = records
        self._pass = 0

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, index: int) -> Any:
        return self._records[index]

    def __iter__(self):
        self._pass += 1
        if self._pass > 1:
            return iter([{**r, "pair": "EUR_USD"} for r in self._records])
        return iter(self._records)


def test_bl1_len_and_iteration_disagreement_never_proves_anything() -> None:
    lying = LyingSequence(declared=20, yields=[])
    with pytest.raises(NoOverlapError, match="not self-consistent"):
        assert_per_file_bounds(lying, role="design", expected_count=20)
    with pytest.raises(NoOverlapError, match="not self-consistent"):
        assert_per_file_bounds(lying, role="design")


def test_bl1_expected_count_alone_cannot_produce_the_token() -> None:
    """Twenty copies of one record satisfied a twenty-file inventory."""
    one = design_roster()[0]
    with pytest.raises(NoOverlapError, match="duplicate evidence|roster does not match"):
        assert_per_file_bounds([one] * 20, role="design", expected_count=20)


def test_bl1_empty_and_lazy_inputs_are_refused() -> None:
    with pytest.raises(NoOverlapError, match="empty file list"):
        assert_per_file_bounds([], role="design")
    for lazy in ((f for f in design_roster()), iter(design_roster())):
        with pytest.raises(NoOverlapError, match="concrete sequence"):
            assert_per_file_bounds(lazy, role="design")
    for textish in ("x" * 20, b"x" * 20, bytearray(b"x" * 20)):
        with pytest.raises(NoOverlapError, match="concrete sequence"):
            assert_per_file_bounds(textish, role="design")


class IndexLyingSequence(Sequence):
    """Iteration yields the roster; ``__getitem__`` yields something else."""

    def __init__(self, records: list[Any]) -> None:
        self._records = records

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, index: int) -> Any:
        return {**self._records[index], "pair": "EUR_USD"}

    def __iter__(self):
        return iter(self._records)


def test_bl1_unstable_evidence_is_refused() -> None:
    with pytest.raises(NoOverlapError, match="not stable|indexed access disagrees"):
        assert_per_file_bounds(UnstableSequence(design_roster()), role="design")


def test_bl1_indexed_access_must_agree_with_iteration() -> None:
    with pytest.raises(NoOverlapError, match="indexed access disagrees"):
        assert_per_file_bounds(IndexLyingSequence(design_roster()), role="design")


def test_bl1_duplicate_alone_is_refused_even_when_nothing_is_missing() -> None:
    """A 21st record duplicating a pair leaves ``missing`` empty on purpose.

    Without this case the duplicate limb is only ever reached alongside a
    missing pair, so removing it would look harmless.
    """
    roster = design_roster()
    roster.append(
        file_record(
            "EUR_USD",
            99,
            ts_min="2025-05-01T00:00:00Z",
            ts_max="2025-06-01T00:00:00Z",
            role="dup",
        )
    )
    with pytest.raises(NoOverlapError) as exc:
        assert_per_file_bounds(roster, role="design")
    assert "duplicate=['EUR_USD']" in str(exc.value)
    assert "missing=[]" in str(exc.value)


def test_bl1_unknown_alone_is_refused_even_when_nothing_is_missing() -> None:
    """Same isolation for the unknown limb: a complete roster plus one stranger."""
    roster = design_roster()
    roster.append(
        file_record(
            "EUR_USD",
            98,
            ts_min="2025-05-01T00:00:00Z",
            ts_max="2025-06-01T00:00:00Z",
            role="unk",
        )
    )
    roster[-1]["pair"] = "XAU_USD"
    with pytest.raises(NoOverlapError) as exc:
        assert_per_file_bounds(roster, role="design")
    assert "unknown=" in str(exc.value)
    assert "missing=[]" in str(exc.value)
    assert "duplicate=[]" in str(exc.value)


def test_bl1_alias_spellings_of_one_pair_count_as_a_duplicate() -> None:
    roster = design_roster()
    roster[1] = {**roster[1], "pair": "eur/usd"}  # alias of roster[0]'s EUR_USD
    with pytest.raises(NoOverlapError) as exc:
        assert_per_file_bounds(roster, role="design")
    assert "duplicate=['EUR_USD']" in str(exc.value)
    assert "missing=['GBP_USD']" in str(exc.value)


def test_bl1_missing_pair_is_named_in_the_refusal() -> None:
    roster = design_roster()[:-1]
    with pytest.raises(NoOverlapError) as exc:
        assert_per_file_bounds(roster, role="design")
    assert PAIRS_20[-1] in str(exc.value)
    assert "missing=" in str(exc.value)


def test_bl1_unknown_pair_is_refused_and_reported() -> None:
    roster = design_roster()
    roster[3] = {**roster[3], "pair": "XAU_USD"}
    with pytest.raises(NoOverlapError) as exc:
        assert_per_file_bounds(roster, role="design")
    assert "unknown=" in str(exc.value)
    assert "XAU_USD" in str(exc.value)


def test_bl1_missing_pair_key_entirely_is_unknown_not_ignored() -> None:
    roster = design_roster()
    roster[5] = {k: v for k, v in roster[5].items() if k != "pair"}
    with pytest.raises(NoOverlapError, match="unknown="):
        assert_per_file_bounds(roster, role="design")


def test_bl1_duplicate_filename_or_digest_is_refused() -> None:
    roster = design_roster()
    roster[4] = {**roster[4], "filename": roster[0]["filename"]}
    with pytest.raises(NoOverlapError, match="duplicate evidence"):
        assert_per_file_bounds(roster, role="design")

    roster = design_roster()
    roster[4] = {**roster[4], "sha256": roster[0]["sha256"]}
    with pytest.raises(NoOverlapError, match="duplicate evidence"):
        assert_per_file_bounds(roster, role="design")


def test_bl1_malformed_digest_is_refused() -> None:
    # 65 and 128 matter as much as 63: `!= 64` must not be weakenable to `< 64`.
    for bad in ("", "z" * 64, "ab" * 31, 123, "0" * 63, "0" * 65, "0" * 128, None):
        roster = design_roster()
        roster[2] = {**roster[2], "sha256": bad}
        with pytest.raises(NoOverlapError, match="well-formed 'sha256'"):
            assert_per_file_bounds(roster, role="design")


def test_bl1_identity_keys_are_mandatory_not_opt_in() -> None:
    """Omitting them used to switch the duplicate-evidence guards off entirely.

    Twenty records naming twenty distinct pairs while describing one physical
    file earned the token, because the only guard that would have caught it —
    the sha256 duplicate check — ran only ``if digest is not None``. The
    committed ``required_schema_per_file`` lists both keys as required.
    """
    for key in ("filename", "sha256"):
        roster = [{k: v for k, v in r.items() if k != key} for r in design_roster()]
        with pytest.raises(NoOverlapError, match=f"'{key}'"):
            assert_per_file_bounds(roster, role="design", expected_count=20)


def test_bl1_a_stateful_mapping_cannot_impersonate_twenty_files() -> None:
    """One record whose `.get("pair")` cycles the roster used to earn the token."""

    class CyclingRecord(Mapping):
        """One record that answers as a different file on every read.

        It cycles the *identity* keys too, so the duplicate-filename and
        duplicate-sha256 guards cannot catch it either — only reading each
        record once, into a snapshot, does.
        """

        def __init__(self) -> None:
            self._i = -1

        def __getitem__(self, key):
            if key == "pair":
                self._i += 1
            n = max(self._i, 0) % len(PAIRS_20)
            return {
                "pair": PAIRS_20[n],
                "filename": f"candles_{PAIRS_20[n]}_M15.jsonl",
                "sha256": f"{n:064x}",
                "ts_min_utc": "2025-05-01T00:00:00Z",
                "ts_max_utc": "2025-06-01T00:00:00Z",
            }[key]

        def __iter__(self):
            return iter(("pair", "filename", "sha256", "ts_min_utc", "ts_max_utc"))

        def __len__(self) -> int:
            return 5

        def __eq__(self, other) -> bool:
            return True

        def __hash__(self) -> int:
            return 0

    with pytest.raises(NoOverlapError, match="duplicate evidence|roster does not match"):
        assert_per_file_bounds([CyclingRecord()] * 20, role="design", expected_count=20)


def test_bl1_a_split_view_record_cannot_certify_spans_it_did_not_roster() -> None:
    """Each record is read ONCE, into a snapshot, so both passes see one story.

    Without that, ``_roster_report`` and the bounds loop each re-read the
    record, and twenty *distinct* stateful records can show one pair to the
    roster check and another to the certified-span record — a proof whose
    evidence and whose conclusion describe different files.
    """

    class ShiftingRecord(Mapping):
        def __init__(self, index: int) -> None:
            self._index = index
            self._reads = 0

        def __getitem__(self, key):
            if key == "pair":
                self._reads += 1
                # First read: the true pair, so the roster check is satisfied.
                # Every later read: one fixed pair — a collision, not a rotation,
                # because a rotated roster still sorts equal to PAIRS_20.
                if self._reads > 1:
                    return PAIRS_20[0]
                return PAIRS_20[self._index % len(PAIRS_20)]
            return {
                "filename": f"f{self._index}.jsonl",
                "sha256": f"{self._index:064x}",
                "ts_min_utc": "2025-05-01T00:00:00Z",
                "ts_max_utc": "2025-06-01T00:00:00Z",
            }[key]

        def __iter__(self):
            return iter(("pair", "filename", "sha256", "ts_min_utc", "ts_max_utc"))

        def __len__(self) -> int:
            return 5

    proof = assert_per_file_bounds(
        [ShiftingRecord(i) for i in range(20)], role="design", expected_count=20
    )
    certified = [s["pair"] for s in proof["certified_spans"]]
    assert sorted(certified) == sorted(PAIRS_20), (
        "certified spans must name the same pairs the roster check verified"
    )


def test_bl1_proof_records_what_it_certified() -> None:
    """A token that names no spans cannot be re-checked against its inventory."""
    proof = assert_per_file_bounds(design_roster(), role="design", expected_count=20)
    assert len(proof["certified_spans"]) == 20
    assert {s["pair"] for s in proof["certified_spans"]} == set(PAIRS_20)
    assert all(len(s["sha256"]) == 64 for s in proof["certified_spans"])
    # and it says plainly which committed schema keys it did NOT verify
    assert set(proof["schema_keys_not_verified"]) == {
        "size_bytes",
        "row_count",
        "eligible_event_count",
        "gap_report",
        "pip_size",
    }


def test_bl1_non_canonical_pair_spelling_is_reported_like_cost_schema_does() -> None:
    """One frozen contract must not get two answers from two consumers."""
    roster = design_roster()
    roster[0] = {**roster[0], "pair": "eur/usd"}  # canonicalises, but is not canonical
    with pytest.raises(NoOverlapError, match="non_canonical="):
        assert_per_file_bounds(roster, role="design")


def test_bl1_a_complete_roster_proves_and_records_the_reconciliation() -> None:
    proof = assert_per_file_bounds(design_roster(), role="design", expected_count=20)
    assert proof["result"] == "PROVEN_NO_DEAD_WINDOW_OVERLAP"
    assert proof["files_checked"] == 20
    assert proof["expected_pair_count"] == 20
    assert proof["actual_record_count"] == 20
    assert proof["expected_pairs"] == list(PAIRS_20)
    assert proof["actual_pairs"] == list(PAIRS_20)
    assert proof["missing_pairs"] == []
    assert proof["duplicate_pairs"] == []
    assert proof["unknown_pairs"] == []


def test_bl1_forward_role_is_refused_rather_than_pre_deciding_its_shape() -> None:
    """The design roster may not be projected onto an undecided forward contract.

    ``artifacts/m15_gate3a/forward_epoch_inventory.json`` declares no ``pair``
    key and a per-file ``"role": "validation | holdout"`` split, so requiring 20
    distinct pairs there would invent the forward evidence shape — the same
    thing BL-5 refused to do for the magnitude bound. The forward inventory is
    ``EMPTY__NO_FORWARD_DATA_EXISTS`` with ``file_count: 0``, so nothing is lost.
    """
    for evidence in (forward_roster(), forward_roster()[:10], []):
        with pytest.raises(NoOverlapError, match="Requires separate contract Gate-decision"):
            assert_per_file_bounds(evidence, role="forward")
    # the per-span forward checker is untouched and still enforces the floor
    assert_forward_bounds("2026-05-01T00:00:00Z", "2026-06-30T23:59:59Z")
    with pytest.raises(NoOverlapError):
        assert_forward_bounds("2026-04-24T00:00:00Z", "2026-06-30T23:59:59Z")


def test_bl1_unknown_role_never_carries_the_proof_token() -> None:
    for role in ("holdout_leak", "validation", "", "DESIGN", "design "):
        with pytest.raises(NoOverlapError, match="unknown role"):
            assert_per_file_bounds(design_roster(), role=role)


def test_bl1_records_missing_ts_bounds_still_fail_after_the_roster_check() -> None:
    roster = design_roster()
    roster[9] = {k: v for k, v in roster[9].items() if k != "ts_min_utc"}
    with pytest.raises(NoOverlapError, match="missing ts bounds"):
        assert_per_file_bounds(roster, role="design")


# ==========================================================================
# BL-2 — `tzinfo is None` is not Python's awareness test
# ==========================================================================


class NoOffsetZone(tzinfo):
    """A tzinfo that leaves the datetime NAIVE while ``tzinfo is None`` is False."""

    def utcoffset(self, dt):  # noqa: D102
        return None

    def dst(self, dt):  # noqa: D102
        return None

    def tzname(self, dt):  # noqa: D102
        return "NAIVE"


class RaisingZone(tzinfo):
    def utcoffset(self, dt):  # noqa: D102
        raise RuntimeError("boom")

    def dst(self, dt):  # noqa: D102
        return None


class IllTypedZone(tzinfo):
    def utcoffset(self, dt):  # noqa: D102
        return 3600  # seconds, not a timedelta

    def dst(self, dt):  # noqa: D102
        return None


class DriftingZone(tzinfo):
    """Returns a different offset on each call — non-deterministic."""

    def __init__(self) -> None:
        self._calls = 0

    def utcoffset(self, dt):  # noqa: D102
        self._calls += 1
        return timedelta(hours=self._calls)

    def dst(self, dt):  # noqa: D102
        return None


_PATHOLOGICAL = [
    pytest.param(NoOffsetZone(), "naive", id="utcoffset-None"),
    pytest.param(RaisingZone(), "raised", id="utcoffset-raises"),
    pytest.param(IllTypedZone(), "timedelta", id="utcoffset-not-a-timedelta"),
    pytest.param(DriftingZone(), "deterministic", id="utcoffset-unstable"),
]


@pytest.mark.parametrize("zone,message", _PATHOLOGICAL)
def test_bl2_timeutil_refuses_every_pathological_zone(zone: tzinfo, message: str) -> None:
    bad = datetime(2025, 6, 2, 0, 0, tzinfo=zone)
    with pytest.raises(TimestampError, match=message):
        to_utc(bad)
    with pytest.raises(TimestampError, match=message):
        to_utc_minute(bad)


@pytest.mark.parametrize("zone,message", _PATHOLOGICAL)
def test_bl2_aggregation_refuses_every_pathological_zone(zone: tzinfo, message: str) -> None:
    """Previously ACCEPTED, emitting a bucket read in the host's local zone."""
    with pytest.raises(AggregationError, match="timestamp rejected"):
        aggregate_m15([_row(datetime(2025, 6, 2, 0, 0, tzinfo=zone))], pair="EUR_USD")


@pytest.mark.parametrize("zone,message", _PATHOLOGICAL)
def test_bl2_no_overlap_refuses_every_pathological_zone(zone: tzinfo, message: str) -> None:
    roster = design_roster()
    roster[0] = {**roster[0], "ts_min_utc": datetime(2025, 5, 1, tzinfo=zone)}
    with pytest.raises(NoOverlapError):
        assert_per_file_bounds(roster, role="design")


@pytest.mark.parametrize("zone,message", _PATHOLOGICAL)
def test_bl2_warmup_refuses_every_pathological_zone(zone: tzinfo, message: str) -> None:
    policy = WarmupPolicy(w_bars=50, longest_feature_lookback_bars=50)
    with pytest.raises(WarmupPolicyError, match="rejected"):
        policy.assert_load_allowed(datetime(2026, 5, 1, tzinfo=zone))


@pytest.mark.parametrize("hours", [-11, -5, 0, 5, 9, 14])
def test_bl2_conversion_is_pure_offset_arithmetic(hours: int) -> None:
    """Every offset converts to the same instant, by subtraction."""
    zone = timezone(timedelta(hours=hours))
    aware = datetime(2026, 5, 1, 12, 0, tzinfo=zone)
    expected = datetime(2026, 5, 1, 12, 0, tzinfo=UTC) - timedelta(hours=hours)
    assert to_utc(aware) == expected
    assert to_utc(aware).tzinfo is UTC


def test_bl2_no_module_reaches_for_the_host_zone() -> None:
    """The host clock must not participate, so no gate-3a module may call
    ``astimezone``, ``utcnow``, ``now`` or ``localtime`` on a timestamp path.

    This is the structural half of BL-2: an environment-variable probe cannot
    prove absence (``TZ`` needs ``tzset``, which Windows lacks), but the absence
    of the call itself can be checked directly.
    """
    forbidden = ("astimezone(", "utcnow(", "datetime.now(", "time.localtime(")
    for name in ("timeutil", "aggregation", "no_overlap", "warmup"):
        source = (REPO_ROOT / "scripts" / "m15_gate3a" / f"{name}.py").read_text(encoding="utf-8")
        code = "\n".join(line for line in source.splitlines() if not line.strip().startswith("#"))
        # strip docstrings crudely: they are the only other place the words appear
        code = code.replace("``astimezone``", "").replace("``astimezone(UTC)``", "")
        for call in forbidden:
            assert call not in code, f"{name}.py reaches for the host zone via {call}"


def test_bl2_to_utc_always_returns_a_plain_datetime() -> None:
    class Sub(datetime):
        pass

    out = to_utc(Sub(2025, 6, 2, 0, 0, tzinfo=UTC))
    assert type(out) is datetime


def test_bl2_offsetless_strings_and_non_datetimes_still_fail_closed() -> None:
    for bad in ("2025-06-02T00:00:00", "", "   ", "not-a-date", 42, None, object()):
        with pytest.raises(TimestampError):
            to_utc(bad)


# ==========================================================================
# BL-2 / RF-8 — the subclass proof must not depend on pandas being installed
# ==========================================================================


class NanoDatetime(datetime):
    """Stdlib subclass exposing ``.nanosecond``, like ``pandas.Timestamp``."""

    nanosecond = 500


class ShiftedDatetime(datetime):
    """Stdlib subclass whose true instant differs from its component rebuild."""

    def timestamp(self) -> float:  # noqa: D102
        return super().timestamp() + 0.25


def test_rf8_subclass_resolution_is_rejected_without_pandas() -> None:
    """RF-8: the whole B-1 proof used to skip in a pandas-free interpreter."""
    with pytest.raises(TimestampError, match="sub-microsecond"):
        to_utc_minute(NanoDatetime(2025, 6, 2, 0, 0, tzinfo=UTC))
    with pytest.raises(TimestampError, match="disagrees with its own components"):
        to_utc_minute(ShiftedDatetime(2025, 6, 2, 0, 0, tzinfo=UTC))

    with pytest.raises(AggregationError, match="timestamp rejected"):
        aggregate_m15([_row(NanoDatetime(2025, 6, 2, 0, 0, tzinfo=UTC))], pair="EUR_USD")
    with pytest.raises(AggregationError, match="timestamp rejected"):
        aggregate_m15([_row(ShiftedDatetime(2025, 6, 2, 0, 0, tzinfo=UTC))], pair="EUR_USD")


def test_bl2_sub_microsecond_is_refused_by_to_utc_not_only_to_utc_minute() -> None:
    """The T-7 fail-open the internal audit found: truncation, not rejection.

    ``no_overlap`` calls ``to_utc``, so applying the sub-microsecond check only
    on the minute path left the dead-window and DESIGN_END limbs truncating. A
    ``ts_max`` 500 ns past ``DESIGN_END`` rebuilt to exactly ``DESIGN_END`` and
    earned the proof token, where the code this replaced had refused it.
    """
    from scripts.m15_gate3a.no_overlap import DESIGN_END, assert_design_bounds

    past_end = NanoDatetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC)
    assert past_end.nanosecond == 500  # 500 ns PAST DESIGN_END
    assert datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC) == DESIGN_END

    with pytest.raises(TimestampError, match="refused rather than truncated"):
        to_utc(past_end)
    with pytest.raises(NoOverlapError):
        assert_design_bounds("2025-05-01T00:00:00Z", past_end)


@pytest.mark.parametrize(
    "bad_ts",
    [
        datetime(2025, 6, 2, 0, 0, 0, 1, tzinfo=UTC),  # 1 microsecond
        datetime(2025, 6, 2, 0, 0, 0, 500_000, tzinfo=UTC),  # half a second
        datetime(2025, 6, 2, 0, 0, 30, tzinfo=UTC),  # 30 seconds
    ],
)
def test_bl2_microsecond_and_second_limbs_of_minute_alignment(bad_ts: datetime) -> None:
    """The microsecond limb had no test at either layer (only whole seconds did)."""
    with pytest.raises(TimestampError, match="not minute-aligned"):
        to_utc_minute(bad_ts)
    with pytest.raises(AggregationError, match="not minute-aligned"):
        aggregate_m15([_row(bad_ts)], pair="EUR_USD")
    # to_utc keeps sub-minute precision — it is only the MINUTE claim that fails
    assert to_utc(bad_ts) == bad_ts


class LyingComponents(datetime):
    """Overrides a component as a property, so a rebuild describes another instant."""

    @property
    def month(self) -> int:  # noqa: D102
        return 1


def test_bl2_a_component_lying_subclass_cannot_walk_past_the_dead_window() -> None:
    """Reproduced by the internal audit: a two-line subclass defeated both gates."""
    from scripts.m15_gate3a.no_overlap import assert_no_dead_window

    inside_dead_window = LyingComponents(2026, 3, 15, 12, 0, tzinfo=UTC)
    with pytest.raises(TimestampError, match="disagrees with its own components"):
        to_utc(inside_dead_window)
    with pytest.raises(NoOverlapError):
        assert_no_dead_window(inside_dead_window, inside_dead_window, role="probe")

    pre_floor = LyingComponents(2020, 1, 1, 0, 0, tzinfo=UTC)
    with pytest.raises(WarmupPolicyError):
        WarmupPolicy(w_bars=50, longest_feature_lookback_bars=50).assert_load_allowed(pre_floor)


def test_bl2_iso_strings_may_not_smuggle_sub_microsecond_resolution() -> None:
    """`datetime.fromisoformat` TRUNCATES past 6 fractional digits.

    So the same instant was refused as a ``pandas.Timestamp`` (``.nanosecond``
    is visible) and accepted as a string — the string being the fail-open side.
    """
    for text in (
        "2026-01-01T00:00:00.000000001+00:00",
        "2026-01-01T00:00:00.0000004+00:00",
        "2026-02-28T23:59:59.000000500Z",
    ):
        with pytest.raises(TimestampError, match="fractional digits"):
            to_utc(text)
    # six digits or fewer is exact, and still accepted
    assert to_utc("2026-01-01T00:00:00.000001+00:00").microsecond == 1
    assert to_utc("2026-01-01T00:00:00.123456Z").microsecond == 123456


def test_bl2_m1_row_timestamps_must_be_datetimes_not_strings() -> None:
    """Widening the M1 row contract to accept `str` was an unrequested loosening."""
    with pytest.raises(AggregationError, match="missing tz-aware 'ts' datetime"):
        aggregate_m15([_row("2026-01-01T00:00:00+00:00")], pair="EUR_USD")


def test_bl2_out_of_range_arithmetic_raises_the_documented_type() -> None:
    """`naive_local - offset` could leak OverflowError past the guard's contract."""
    from scripts.m15_gate3a.no_overlap import assert_design_bounds

    extreme = datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))
    with pytest.raises(TimestampError, match="out of representable range"):
        to_utc(extreme)
    with pytest.raises(NoOverlapError):
        assert_design_bounds(extreme, extreme)
    with pytest.raises(WarmupPolicyError):
        WarmupPolicy(w_bars=50, longest_feature_lookback_bars=50).assert_load_allowed(extreme)


def test_rf8_pandas_is_present_under_the_dev_extra() -> None:
    """The dev extra pins ``pandas>=2.0,<4.0``, so the B-1 tests must RUN in CI.

    RF-8's finding was that a silent skip left all five B-1 mutations alive.
    This makes the skip itself impossible to reach unnoticed.
    """
    assert importlib.util.find_spec("pandas") is not None, (
        "pandas is missing: the B-1 subclass regression tests would silently skip. "
        'Install the dev extra with `pip install -e ".[dev]"`.'
    )


# ==========================================================================
# BL-3 — Windows path aliasing, with no depth at which the guard gives up
# ==========================================================================


def test_bl3_extended_prefix_fold_is_case_insensitive() -> None:
    assert normalise_spelling(r"\\?\UNC\host\share\x") == r"\\host\share\x"
    assert normalise_spelling(r"\\?\unc\host\share\x") == r"\\host\share\x"
    assert normalise_spelling(r"\\?\UnC\host\share\x") == r"\\host\share\x"
    assert normalise_spelling(r"\\?\C:\x") == r"C:\x"
    assert normalise_spelling(r"\\?\c:\x") == r"c:\x"
    assert normalise_spelling(r"C:\x") == r"C:\x"


def test_bl3_no_depth_allows_a_path_under_a_protected_tree(tmp_path: Path) -> None:
    """Depth 63 was REFUSED and depth 64 was ALLOWED — a fixed-cap fail-open."""
    protected = tmp_path / "protected"
    protected.mkdir()
    for depth in (1, 63, 64, 65, 200):
        deep = protected.joinpath(*[f"d{i}" for i in range(depth)]) / "leaf.jsonl"
        assert is_within(deep, protected) is True, depth


def test_bl3_identity_is_reached_at_any_depth_not_just_the_first_64(tmp_path: Path) -> None:
    """The depth guard must be exercised through the IDENTITY limb, not the name limb.

    ``protected/../protected/d0/.../leaf`` is not textually under ``protected``
    — ``pathlib`` keeps the ``..`` component — so the name test fails and the
    walk has to climb the whole chain to the aliasing directory. With the old
    64-iteration cap this returned "allowed" for anything deeper.
    """
    protected = tmp_path / "protected"
    protected.mkdir()
    (tmp_path / "sibling").mkdir()  # POSIX resolves `..` per component, so it must exist
    alias = tmp_path / "sibling" / ".." / "protected"
    assert protected not in (alias / "leaf").parents  # the name limb cannot help
    for depth in (1, 63, 64, 65, 120):
        deep = alias.joinpath(*[f"d{i}" for i in range(depth)]) / "leaf.jsonl"
        assert is_within(deep, protected) is True, depth


def test_bl3_no_fixed_walk_cap_constant_remains() -> None:
    """A numeric ancestor cap is the defect itself; there must be none to tune.

    Scoped to the containment walk rather than the whole module: an earlier
    version asserted ``"range(" not in source``, which constrained every future
    line in the file. The behavioural depth test above is the real guard; this
    only stops the named constant coming back.
    """
    import inspect

    import scripts.m15_gate3a.path_authority as pa

    assert not hasattr(pa, "_MAX_ANCESTOR_WALK")
    walk = inspect.getsource(pa.is_within)
    assert "range(" not in walk
    assert "[:" not in walk  # no slice truncating the ancestor chain


def test_bl3_a_sibling_tree_at_any_depth_is_not_within(tmp_path: Path) -> None:
    protected = tmp_path / "protected"
    protected.mkdir()
    other = tmp_path / "other"
    for depth in (1, 64, 200):
        deep = other.joinpath(*[f"d{i}" for i in range(depth)]) / "leaf.jsonl"
        assert is_within(deep, protected) is False, depth


def test_bl3_identity_catches_a_link_alias(tmp_path: Path) -> None:
    """A junction/symlink alias resolves to a different string, same directory."""
    protected = tmp_path / "protected"
    (protected / "inner").mkdir(parents=True)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(protected, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this host")
    assert is_within((alias / "inner" / "x.jsonl").resolve(), protected) is True


def test_bl3_an_uninterrogable_protected_root_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-3: ``exists()`` reported False for 'absent' AND 'permission denied'."""
    protected = tmp_path / "protected"
    protected.mkdir()
    real_stat = Path.stat

    def boom(self, *a, **k):
        if self == protected:
            raise PermissionError("denied")
        return real_stat(self, *a, **k)

    monkeypatch.setattr(Path, "stat", boom)
    with pytest.raises(PathAuthorityError, match="cannot interrogate protected root"):
        is_within(tmp_path / "elsewhere" / "x.jsonl", protected)


def test_bl3_a_genuinely_absent_protected_root_is_not_a_match(tmp_path: Path) -> None:
    absent = tmp_path / "never-created"
    assert is_within(tmp_path / "elsewhere.jsonl", absent) is False
    assert is_within(absent / "child.jsonl", absent) is True  # name test still applies


def test_bl3_extended_prefix_fold_only_applies_to_a_drive_or_unc(tmp_path: Path) -> None:
    r"""The unconditional strip was itself the bypass.

    ``\\?\Volume{GUID}\...`` and ``\\?\GLOBALROOT\Device\HarddiskVolumeN\...``
    are absolute Win32 spellings. Stripping ``\\?\`` leaves them **relative**,
    so they resolve against the working directory and containment fails open.
    """
    for spelling in (
        r"\\?\Volume{9e556d10-77de-4b32-95e7-d94a2a2868ce}\Users\x\prot\s.json",
        r"\\?\GLOBALROOT\Device\HarddiskVolume4\Users\x\prot\s.json",
        r"\\?\globalroot\Device\HarddiskVolume4\Users\x\prot\s.json",
    ):
        assert normalise_spelling(spelling) == spelling, spelling
        assert Path(normalise_spelling(spelling)).is_absolute() is True, spelling
    # the two spellings that ARE pure aliases of an ordinary path still fold
    assert Path(normalise_spelling(r"\\?\C:\x")).is_absolute()
    assert normalise_spelling(r"\\?\UNC\host\share\x") == r"\\host\share\x"


def test_bl3_an_uninterrogable_candidate_ancestor_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-3's fail-closed rule applies to the probe side too, not just the root."""
    protected = tmp_path / "protected"
    protected.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    real_stat = Path.stat

    def boom(self, *a, **k):
        if self == other:
            raise PermissionError("denied")
        return real_stat(self, *a, **k)

    monkeypatch.setattr(Path, "stat", boom)
    with pytest.raises(PathAuthorityError, match="cannot interrogate"):
        is_within(other / "child" / "x.jsonl", protected)


def test_bl3_a_str_subclass_cannot_show_two_different_paths() -> None:
    """`str(path)` twice would let __str__ answer the checks and the open() differently."""

    class TwoFaced(str):
        def __str__(self) -> str:  # noqa: D105
            return "harmless.json"

    sneaky = TwoFaced("\x00nul-and-more")
    with pytest.raises(PathAuthorityError, match="NUL byte"):
        resolve_candidate(sneaky)


def test_bl3_malformed_and_device_paths_are_refused() -> None:
    for bad in ("", "   ", "x\x00y", 42, None, b"bytes", r"\\.\PhysicalDrive0", r"\\.\NUL"):
        with pytest.raises(PathAuthorityError):
            resolve_candidate(bad)


def test_bl3_resolve_candidate_returns_an_absolute_path(tmp_path: Path) -> None:
    assert resolve_candidate(str(tmp_path)).is_absolute()
    assert resolve_candidate(tmp_path).is_absolute()


# ==========================================================================
# BL-4 — crossed quotes drop-and-count, per the in-repo stage25_0a precedent
# ==========================================================================


def test_bl4_gap_report_exposes_the_full_drop_accounting() -> None:
    rows = [_row(START + timedelta(minutes=i)) for i in range(15)]
    for k in ("o", "h", "l", "c"):
        rows[3][f"ask_{k}"] = rows[3][f"bid_{k}"] - 0.0002
    _, gap = aggregate_m15(rows, pair="EUR_USD")
    for key in ("rows_ingested", "rows_retained", "dropped_crossed_quote_rows"):
        assert key in gap
    assert gap["rows_ingested"] == gap["rows_retained"] + gap["dropped_crossed_quote_rows"]
    assert gap["imputation"] is False  # the drop is never back-filled


def test_bl4_a_fully_dropped_bucket_never_reads_as_a_gapless_file() -> None:
    """Gap metrics describe SOURCE coverage; drop counters describe rejection.

    Computed over retained minutes only, a first bucket that was 100% crossed
    disappeared from the span entirely and the file reported
    ``missing_whole_buckets=0, missing_minute_count=0, max_gap_minutes=0`` —
    gapless and fully eligible, having silently lost half its input.
    """
    rows = []
    for i in range(15):  # bucket 0: every row crossed
        r = _row(START + timedelta(minutes=i))
        for k in ("o", "h", "l", "c"):
            r[f"ask_{k}"] = r[f"bid_{k}"] - 0.0002
        rows.append(r)
    rows += [_row(START + timedelta(minutes=15 + i)) for i in range(15)]  # bucket 1: clean

    bars, gap = aggregate_m15(rows, pair="EUR_USD")
    assert len(bars) == 1 and bars[0]["eligible"] is True
    assert gap["rows_ingested"] == 30
    assert gap["rows_retained"] == 15
    assert gap["dropped_crossed_quote_rows"] == 15
    assert gap["buckets_fully_dropped"] == [START.isoformat()]
    assert gap["all_rows_dropped"] is False
    # the source span still covers both buckets, so the loss is visible
    assert gap["missing_minute_count"] == 0  # every source minute was present
    assert gap["n_buckets_emitted"] == 1


def test_bl4_gap_metrics_describe_source_coverage_not_retained_coverage() -> None:
    """A dropped minute WAS present in the source; it is not a coverage gap.

    Computed over retained minutes only, dropping minute 5 out of a contiguous
    0..14 run invents a one-minute hole that never existed in the data. The
    drop counters are where that loss belongs.
    """
    rows = [_row(START + timedelta(minutes=i)) for i in range(15)]
    for k in ("o", "h", "l", "c"):
        rows[5][f"ask_{k}"] = rows[5][f"bid_{k}"] - 0.0002

    _, gap = aggregate_m15(rows, pair="EUR_USD")
    assert gap["missing_minute_count"] == 0  # the source run was contiguous
    assert gap["max_gap_minutes"] == 0
    assert gap["dropped_crossed_quote_rows"] == 1  # the loss is reported here
    assert gap["rows_retained"] == 14


def test_bl4_row_count_is_what_was_iterated_not_what_len_claimed() -> None:
    """BL-1's lesson: `isinstance(x, list)` admits a subclass with a lying __len__."""

    class LyingList(list):
        def __len__(self) -> int:
            return 15

    rows = LyingList(_row(START + timedelta(minutes=i)) for i in range(3))
    _, gap = aggregate_m15(rows, pair="EUR_USD")
    assert gap["rows_ingested"] == 3, "rows_ingested must count iteration, not __len__"
    assert gap["rows_ingested"] == gap["rows_retained"] + gap["dropped_crossed_quote_rows"]


def test_bl4_all_rows_dropped_is_reported_not_raised() -> None:
    """An acceptance threshold for the drop ratio would be an invented number."""
    rows = []
    for i in range(15):
        r = _row(START + timedelta(minutes=i))
        for k in ("o", "h", "l", "c"):
            r[f"ask_{k}"] = r[f"bid_{k}"] - 0.0002
        rows.append(r)
    bars, gap = aggregate_m15(rows, pair="EUR_USD")
    assert bars == []
    assert gap["all_rows_dropped"] is True
    assert gap["buckets_fully_dropped"] == [START.isoformat()]


def test_bl4_matches_the_committed_stage25_0a_predicate() -> None:
    """The precedent this fix adopts is in the repo, not inferred from real data."""
    source = (REPO_ROOT / "scripts" / "stage25_0a_build_path_quality_dataset.py").read_text(
        encoding="utf-8"
    )
    assert "dropped_invalid_spread" in source
    assert "spread_pip < 0" in source
    assert "data anomaly" in source


# Both sides internally coherent; exactly ONE limb crosses. Without these the
# detector could inspect only the close and nothing would notice.
_BID_SIDE = {"bid_o": 1.1000, "bid_h": 1.1010, "bid_l": 1.0990, "bid_c": 1.1005}
_ASK_UNCROSSED = {"ask_o": 1.1000, "ask_h": 1.1010, "ask_l": 1.0990, "ask_c": 1.1005}
_SINGLE_CROSS = {
    "o": {"ask_o": 1.0999},
    "h": {"ask_h": 1.1009},
    "l": {"ask_l": 1.0989},
    "c": {"ask_c": 1.1004},
}


@pytest.mark.parametrize("limb", ["o", "h", "l", "c"])
def test_bl4_every_ohlc_limb_is_inspected_for_the_cross(limb: str) -> None:
    """A cross on the open, high or low is as real as one on the close."""
    row = {"ts": START, **_BID_SIDE, **_ASK_UNCROSSED}
    clean = dict(row)
    row.update(_SINGLE_CROSS[limb])
    assert sum(row[f"ask_{k}"] < row[f"bid_{k}"] for k in "ohlc") == 1  # exactly one

    bars, gap = aggregate_m15([row], pair="EUR_USD")
    assert gap["dropped_crossed_quote_rows"] == 1, limb
    assert bars == []
    # control: the same row without the single cross is retained
    _, clean_gap = aggregate_m15([clean], pair="EUR_USD")
    assert clean_gap["dropped_crossed_quote_rows"] == 0


def test_bl4_a_single_crossed_row_no_longer_destroys_the_whole_pair() -> None:
    """Failing-before evidence: this call used to raise AggregationError."""
    rows = [_row(START + timedelta(minutes=i)) for i in range(30)]
    for k in ("o", "h", "l", "c"):
        rows[20][f"ask_{k}"] = rows[20][f"bid_{k}"] - 0.0001
    bars, gap = aggregate_m15(rows, pair="EUR_USD")
    assert len(bars) == 2
    assert bars[0]["eligible"] is True  # the untouched bucket keeps its eligibility
    assert bars[1]["eligible"] is False  # only the affected bucket loses it
    assert gap["dropped_crossed_quote_rows"] == 1


# ==========================================================================
# RF residuals with no separate home
# ==========================================================================


def test_rf2_missing_minute_count_semantics_are_pinned() -> None:
    """RF-2: the two figures answer different questions; pin both, assume neither.

    ``missing_minute_count`` counts holes strictly between the first and last
    observed minute. ``total_missing_source_minutes_within_emitted_buckets``
    counts every absent minute of every emitted bucket, including its leading
    and trailing edges. A trailing partial bucket is the case that separates
    them, and it is exactly the case the committed inventory does not define.
    """
    rows = [_row(START + timedelta(minutes=m)) for m in (0, 1, 2)]
    _, gap = aggregate_m15(rows, pair="EUR_USD")
    assert gap["missing_minute_count"] == 0  # no hole BETWEEN 00:00 and 00:02
    assert gap["total_missing_source_minutes_within_emitted_buckets"] == 12

    rows = [_row(START + timedelta(minutes=m)) for m in (0, 10, 14)]
    _, gap = aggregate_m15(rows, pair="EUR_USD")
    assert gap["missing_minute_count"] == 12  # 9 between 0..10, 3 between 10..14
    assert gap["max_gap_minutes"] == 9
    assert gap["total_missing_source_minutes_within_emitted_buckets"] == 12


def test_rf9_emitted_bars_are_chronological_regardless_of_input_order() -> None:
    rows = [_row(START + timedelta(minutes=m)) for m in (45, 0, 30, 15)]
    bars, _ = aggregate_m15(rows, pair="EUR_USD")
    stamps = [b["ts"] for b in bars]
    assert stamps == sorted(stamps)
    assert all(type(s) is datetime for s in stamps)


def test_rf10_high_must_bracket_open_and_close() -> None:
    with pytest.raises(AggregationError, match="OHLC incoherent"):
        aggregate_m15([_row(START, bid_c=1.50, ask_c=1.5001)], pair="EUR_USD")
    with pytest.raises(AggregationError, match="OHLC incoherent"):
        aggregate_m15([_row(START, bid_o=1.00, ask_o=1.0001)], pair="EUR_USD")


def test_bl5_the_magnitude_bound_is_a_required_argument() -> None:
    """Removing the invented ceiling must not silently become "no check"."""
    from tests.m15_gate3a.test_cost_schema import _table

    with pytest.raises(TypeError, match="max_spread_pips"):
        validate_cost_table(_table())  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "observed_pips,ceiling,accepted",
    [(10.0, 11.0, True), (10.0, 10.0, True), (10.0, 9.999, False), (10.0, 9.0, False)],
)
def test_bl5_the_ceiling_comparison_is_pinned_at_its_boundary(
    observed_pips: float, ceiling: float, accepted: bool
) -> None:
    """The only rejection case was an 11x margin, so `>` could be loosened to `> 2*`."""
    from tests.m15_gate3a.test_cost_schema import _table

    price = observed_pips * PIP_NON_JPY
    table = _table(entry={"median_spread": price, "p90_spread": price, "p95_spread": price})
    if accepted:
        summary = validate_cost_table(table, max_spread_pips=ceiling)
        assert summary["magnitude_checked_against_declared_bound"] is True
    else:
        with pytest.raises(CostSchemaError, match="caller-declared ceiling"):
            validate_cost_table(table, max_spread_pips=ceiling)


def test_bl5_a_declared_bound_that_excludes_nothing_is_still_visible() -> None:
    """The flag says a bound was checked, not that the magnitude is sane."""
    from tests.m15_gate3a.test_cost_schema import _table

    summary = validate_cost_table(_table(), max_spread_pips=1e12)
    assert summary["magnitude_checked_against_declared_bound"] is True
    assert summary["max_spread_pips_declared"] == 1e12  # the giveaway is reported alongside
    assert summary["magnitude_authority"] == "CALLER_DECLARED"


def test_rf1_duplicate_pair_session_cell_is_refused() -> None:
    from tests.m15_gate3a.test_cost_schema import _table

    table = _table()
    table["entries"] = table["entries"] * 3
    with pytest.raises(CostSchemaError, match="duplicate"):
        validate_cost_table(table, max_spread_pips=None)


def test_rf1_the_session_partition_check_runs_at_import_and_can_fail() -> None:
    """The pin must be *invoked*, not merely defined, and must actually reject."""
    import ast

    import scripts.m15_gate3a.cost_schema as cs

    source = (REPO_ROOT / "scripts" / "m15_gate3a" / "cost_schema.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_level_calls = {
        node.value.func.id
        for node in tree.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
    }
    assert "_check_session_partition" in module_level_calls

    for broken, why in (
        ({"a": "00:00-12:00", "b": "11:00-23:59"}, "overlaps"),
        ({"a": "00:00-11:59", "b": "13:00-23:59"}, "tile"),
        ({"a": "00:00-23:59", "b": "00:00-23:59"}, "overlaps"),
        ({"a": "00:00-24:00"}, "out of range"),
    ):
        original = cs.SESSIONS_UTC
        try:
            cs.SESSIONS_UTC = broken
            with pytest.raises(RuntimeError, match=why):
                cs._check_session_partition()
        finally:
            cs.SESSIONS_UTC = original


def test_rf11_fullwidth_status_spellings_fold_to_the_forbidden_key() -> None:
    from scripts.m15_gate3a.guards import is_forbidden_status, normalise_status

    assert normalise_status("ＰＡＳＳ") == "PASS"
    assert is_forbidden_status("ＰＡＳＳ") is True
    assert is_forbidden_status("ＰＲＯＤＵＣＴＩＯＮ＿ＲＥＡＤＹ") is True
    assert is_forbidden_status("Ｔｉｅｒ　１") is True


def test_roster_fixture_records_carry_the_committed_schema_keys() -> None:
    record = file_record(
        "EUR_USD", 1, ts_min="2025-05-01T00:00:00Z", ts_max="2025-06-01T00:00:00Z", role="design"
    )
    assert set(record) >= {"pair", "filename", "sha256", "ts_min_utc", "ts_max_utc"}
    assert len(record["sha256"]) == 64
