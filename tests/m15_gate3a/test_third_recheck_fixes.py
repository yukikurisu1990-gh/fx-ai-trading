"""Regression tests for the second fix round of the third re-check (N-1..N-7, §12.23).

Every test here corresponds to a finding that was **reproduced with real output**
against head ``6e87553`` before the fix, except where a test is explicitly
labelled a *coverage gap*:

* **N-1, N-2, N-3, N-4, N-5** and the **§12.23 writer gap** are defects. Each
  test in those sections fails against the previous implementation — the fix
  note records the failing-before evidence per finding.
* **N-6** is a pair of **coverage gaps**, not defects. The mutation study showed
  the guards at ``path_authority.py:122`` and ``artifacts.py:995-996`` behave
  correctly today but that a mutant of each survives the suite. Those tests
  therefore pass on the previous implementation too, and neither source line was
  changed. Saying so is the point of a file whose purpose is evidence.
* **N-7** is a docstring disclosure with no behaviour change. What is pinned
  instead is the *factual basis* of the disclosure: that all four committed
  aggregate assertions are enforced inline by the TC limb.

Nothing in this module reads real data, derives real M15, computes a real
checksum or spread, trains, validates, evaluates or executes anything.
"""

from __future__ import annotations

import copy
import json
import pickle
from datetime import UTC, datetime
from typing import Any

import pytest

from scripts.m15_gate3a import proof
from scripts.m15_gate3a.aggregation import AggregationError, aggregate_m15
from scripts.m15_gate3a.artifacts import (
    ArtifactScrubError,
    scan_gate3a,
    write_metadata_artifact,
)
from scripts.m15_gate3a.calendar_authority import CalendarConstructionError
from scripts.m15_gate3a.cost_schema import (
    ALL_IN_COST_FORMULA,
    CLAIM_SCOPE,
    DATA_SOURCE_RESTRICTION,
    EXECUTION_PADDING_PIP,
    FLAT_SLIPPAGE_CELL_PIP,
    SESSIONS_UTC,
    SPREAD_UNIT,
    STRESS_FORMS,
    CostSchemaError,
    validate_cost_table,
)
from scripts.m15_gate3a.coverage import (
    BarNotCertifiableError,
    CoverageConstructionError,
    CoverageResult,
    MinuteAccountingError,
    assert_full_coverage,
    measure_pair_coverage,
)
from scripts.m15_gate3a.effective_n import EffectiveNError, effective_n
from scripts.m15_gate3a.guards import (
    FORBIDDEN_STATUSES,
    UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS,
    RealDataRefusedError,
    assert_status_allowed,
    is_forbidden_status,
)
from scripts.m15_gate3a.numeric_authority import (
    NumericAuthorityError,
    pin_float,
    pin_int,
    pin_number,
)
from scripts.m15_gate3a.pair_authority import PAIRS_20, pip_size_for_pair
from scripts.m15_gate3a.path_authority import (
    PathAuthorityError,
    _reject_stream_suffix,
    resolve_candidate,
)
from scripts.m15_gate3a.proof import (
    AGGREGATE_ASSERTIONS,
    BYTE_LEVEL_CLAIM_TOKENS,
    BYTE_LEVEL_CLAIM_WITHHELD_REASON,
    BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
    BYTE_LEVEL_PROOF_PENDING,
    DECLARED_NOT_MEASURED_BY_THIS_LAYER,
    LIMB_EVALUATION_EVIDENCE_BASIS,
    ProofConstructionError,
    ProofContractError,
    ProofLimbUnsatisfiedError,
    ProofNotUsableError,
    ProofPromotionError,
    open_for_consumption,
)
from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError
from tests.m15_gate3a.test_wp_proof_coverage_calendar import (
    EPOCH,
    accounting,
    bars,
    evaluated_proof,
    full_measurements,
    recheck_set,
    valid_calendar,
)

START = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)


# ===========================================================================
# The two-faced numeric objects every N-1 test is built from
# ===========================================================================


class LyingFloat(float):
    """A ``float`` subclass whose ordering comparisons always answer favourably.

    This is the exact shape the lead reproduced N-1 with: the object holds one
    value and answers ``<`` / ``>`` as though it held another. It overrides
    nothing else, so any check that reads the object's real character data sees
    the true number.
    """

    def __lt__(self, other: Any) -> bool:
        return False

    def __gt__(self, other: Any) -> bool:
        return False

    def __le__(self, other: Any) -> bool:
        return True

    def __ge__(self, other: Any) -> bool:
        return True


class LyingInt(int):
    """The ``int`` member of the same family.

    All four ordering dunders are overridden, not just ``<`` / ``>``: the
    package decides some bounds with ``<=`` (``w_bars <= 0``) and some
    eligibility with ``>=`` (``bar_index >= w_bars``), and a subclass that lied
    on only half of them would leave those guards untested.
    """

    def __lt__(self, other: Any) -> bool:
        return False

    def __gt__(self, other: Any) -> bool:
        return False

    def __le__(self, other: Any) -> bool:
        return False

    def __ge__(self, other: Any) -> bool:
        return True


class LyingConversion(float):
    """A ``float`` subclass that lies through ``__float__`` rather than through ``<``.

    ``float(value)`` calls this, so a guard written as ``v = float(value)``
    reports the lie. Only the unbound ``float.__float__`` slot sees the truth.
    """

    def __float__(self) -> float:
        return 0.5


class AgreeableFloat(float):
    """A ``float`` subclass that claims equality with whatever it is compared to.

    The ordering-liar above cannot defeat an ``==`` / ``!=`` guard, so the
    equality half of the family needs its own shape: this is what a caller would
    use against ``pip_size != authority`` or ``execution_padding_pip != 0.3``.
    """

    def __eq__(self, other: Any) -> bool:
        return True

    def __ne__(self, other: Any) -> bool:
        return False

    __hash__ = float.__hash__


class AgreeableInt(int):
    """The ``int`` member of the equality-lying family."""

    def __eq__(self, other: Any) -> bool:
        return True

    def __ne__(self, other: Any) -> bool:
        return False

    __hash__ = int.__hash__


# ===========================================================================
# N-1 — the numeric authority itself
# ===========================================================================


def test_n1_pin_number_reads_the_character_data_not_the_conversion_override() -> None:
    """``float()`` is not a pin; ``float.__float__`` is."""
    lying = LyingConversion(5.0)
    assert float(lying) == 0.5
    assert pin_number(lying, what="x") == 5.0
    assert type(pin_number(lying, what="x")) is float


def test_n1_pin_int_reads_the_character_data_not_the_conversion_override() -> None:
    class LyingIndex(int):
        def __index__(self) -> int:
            return 0

        def __int__(self) -> int:
            return 0

    lying = LyingIndex(-100)
    assert int(lying) == 0
    assert pin_int(lying, what="x") == -100
    assert type(pin_int(lying, what="x")) is int


def test_n1_a_lying_comparison_survives_nothing_once_the_value_is_pinned() -> None:
    lying = LyingFloat(-5.0)
    assert (lying < 0) is False  # the lie, as the caller's object tells it
    assert pin_number(lying, what="x") < 0  # the truth, once pinned


def test_n1_pin_number_refuses_a_bool() -> None:
    with pytest.raises(NumericAuthorityError, match="must be a number, not a bool"):
        pin_number(True, what="flag")


def test_n1_pin_int_refuses_a_bool() -> None:
    with pytest.raises(NumericAuthorityError, match="must be an int, not a bool"):
        pin_int(False, what="flag")


def test_n1_pin_number_refuses_a_non_number() -> None:
    with pytest.raises(NumericAuthorityError, match="must be a number, got str"):
        pin_number("1.0", what="value")


def test_n1_pin_int_refuses_a_float_rather_than_rounding_it() -> None:
    """A count is an ``int`` in every schema here; 15.0 does not become 15."""
    with pytest.raises(NumericAuthorityError, match="must be an int, got float"):
        pin_int(15.0, what="count")


def test_n1_pin_float_returns_a_plain_float_for_an_int() -> None:
    assert pin_float(3, what="x") == 3.0
    assert type(pin_float(3, what="x")) is float


# ===========================================================================
# N-1 — aggregation (D-1 defeated by a lying float subclass)
# ===========================================================================


def _crossed_rows(maker: Any) -> list[dict[str, Any]]:
    """Fifteen minutes whose HIGH and LOW are crossed (ask below bid) on every row.

    ``o`` and ``c`` are equal on both sides, so the derived quoted spreads are
    ``0.0`` and the spread-sign guard cannot be what fires: the only thing
    standing between this and a certifiable bucket is the D-1 crossing check.
    """
    out: list[dict[str, Any]] = []
    for minute in range(15):
        out.append(
            {
                "ts": START.replace(minute=minute),
                "bid_o": maker(1.5),
                "bid_h": maker(2.0),
                "bid_l": maker(1.0),
                "bid_c": maker(1.5),
                "ask_o": maker(1.5),
                "ask_h": maker(1.2),
                "ask_l": maker(0.8),
                "ask_c": maker(1.5),
            }
        )
    return out


def test_n1_plain_float_crossed_quotes_refuse() -> None:
    """The control: the identical crossings, spelled with the built-in type."""
    with pytest.raises(AggregationError, match="ask OHLC incoherent"):
        aggregate_m15(_crossed_rows(float), pair="EUR_USD")


def test_n1_a_lying_float_subclass_cannot_certify_a_crossed_bucket() -> None:
    """N-1's headline: this returned ``n_source_bars=15, eligible=True``.

    Failing-before: ``aggregate_m15`` produced a bucket with
    ``complete_bucket=True`` and ``bid_h=2.0`` beside ``ask_h=1.2``, while the
    plain-``float`` spelling of exactly the same rows refused 12 times out of 12.
    """
    with pytest.raises(AggregationError, match="ask OHLC incoherent"):
        aggregate_m15(_crossed_rows(LyingFloat), pair="EUR_USD")


def test_n1_a_lying_float_subclass_cannot_hide_a_crossed_open() -> None:
    """The D-1 crossing check specifically, reached with a coherent per-side OHLC."""
    rows = []
    for minute in range(15):
        rows.append(
            {
                "ts": START.replace(minute=minute),
                "bid_o": LyingFloat(1.5),
                "bid_h": LyingFloat(1.5),
                "bid_l": LyingFloat(1.5),
                "bid_c": LyingFloat(1.5),
                "ask_o": LyingFloat(1.0),
                "ask_h": LyingFloat(1.0),
                "ask_l": LyingFloat(1.0),
                "ask_c": LyingFloat(1.0),
            }
        )
    with pytest.raises(AggregationError, match="bucket and file are not certifiable"):
        aggregate_m15(rows, pair="EUR_USD")


def test_n1_an_accepted_bar_carries_plain_floats_not_the_callers_subclass() -> None:
    """The pin reaches the emitted bar, not only the checks."""
    rows = []
    for minute in range(15):
        rows.append(
            {
                "ts": START.replace(minute=minute),
                "bid_o": LyingFloat(1.0),
                "bid_h": LyingFloat(1.0),
                "bid_l": LyingFloat(1.0),
                "bid_c": LyingFloat(1.0),
                "ask_o": LyingFloat(1.0),
                "ask_h": LyingFloat(1.0),
                "ask_l": LyingFloat(1.0),
                "ask_c": LyingFloat(1.0),
            }
        )
    emitted, _report = aggregate_m15(rows, pair="EUR_USD")
    bar = emitted[0]
    assert bar["complete_bucket"] is True
    for key in ("bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"):
        assert type(bar[key]) is float, key


def test_n1_a_lying_float_cannot_smuggle_a_non_finite_side_value() -> None:
    rows = _crossed_rows(float)
    rows[0]["bid_h"] = LyingFloat(float("inf"))
    with pytest.raises(AggregationError, match="is non-finite"):
        aggregate_m15(rows, pair="EUR_USD")


# ===========================================================================
# N-1 — cost_schema (a negative median spread validated)
# ===========================================================================


def _cost_table(**entry_overrides: Any) -> dict[str, Any]:
    entry_defaults: dict[str, Any] = {
        "median_spread": 0.0001,
        "p90_spread": 0.0002,
        "p95_spread": 0.0003,
    }
    entry_defaults.update(entry_overrides)
    return {
        "execution_padding_pip": EXECUTION_PADDING_PIP,
        "flat_slippage_cell_pip": FLAT_SLIPPAGE_CELL_PIP,
        "all_in_cost_formula": ALL_IN_COST_FORMULA,
        "spread_unit": SPREAD_UNIT,
        "claim_scope": CLAIM_SCOPE,
        "stress_forms": list(STRESS_FORMS),
        "data_source_restriction": DATA_SOURCE_RESTRICTION,
        "entries": [
            {
                "pair": pair,
                "session": session,
                "pip_size": pip_size_for_pair(pair),
                **entry_defaults,
            }
            for pair in PAIRS_20
            for session in SESSIONS_UTC
        ],
    }


def test_n1_a_well_formed_cost_table_still_validates() -> None:
    """Reachability control: the refusals below are not refusing everything."""
    summary = validate_cost_table(_cost_table(), max_spread_pips=100.0)
    assert summary["result"] == "COST_TABLE_SCHEMA_VALID"


def test_n1_plain_negative_median_spread_is_refused() -> None:
    with pytest.raises(CostSchemaError, match="must be a finite non-negative number"):
        validate_cost_table(
            _cost_table(median_spread=-5.0, p90_spread=0.0, p95_spread=0.0),
            max_spread_pips=None,
        )


def test_n1_a_lying_float_cannot_validate_a_negative_median_spread() -> None:
    """Failing-before: ``COST_TABLE_SCHEMA_VALID`` with ``min_observed_spread_pips=-50000.0``."""
    with pytest.raises(CostSchemaError, match="must be a finite non-negative number"):
        validate_cost_table(
            _cost_table(
                median_spread=LyingFloat(-5.0),
                p90_spread=LyingFloat(0.0),
                p95_spread=LyingFloat(0.0),
            ),
            max_spread_pips=None,
        )


def test_n1_the_ordering_liar_is_already_powerless_over_the_derived_statistics() -> None:
    """Scope control, NOT a pin.

    ``median <= p90 <= p95`` and the pip-unit ceiling are decided over ``stats``,
    which were already plain floats, so the ordering-liar never reached them.
    Recording that keeps the pin claims above honest about their extent.
    """
    with pytest.raises(CostSchemaError, match="must satisfy"):
        validate_cost_table(
            _cost_table(
                median_spread=LyingFloat(0.9),
                p90_spread=LyingFloat(0.2),
                p95_spread=LyingFloat(0.3),
            ),
            max_spread_pips=None,
        )
    with pytest.raises(CostSchemaError, match="above the caller-declared ceiling"):
        validate_cost_table(
            _cost_table(
                median_spread=LyingFloat(1.0),
                p90_spread=LyingFloat(1.0),
                p95_spread=LyingFloat(1.0),
            ),
            max_spread_pips=100.0,
        )


def test_n1_an_equality_liar_cannot_pass_the_pip_size_authority_check() -> None:
    """``pip_size != authority`` is an ``==`` guard, so it needs the ``__eq__`` liar."""
    table = _cost_table()
    table["entries"][0]["pip_size"] = AgreeableFloat(1.0)
    with pytest.raises(CostSchemaError, match="!= authority"):
        validate_cost_table(table, max_spread_pips=None)


def test_n1_an_equality_liar_cannot_forge_the_pinned_execution_padding() -> None:
    table = _cost_table()
    table["execution_padding_pip"] = AgreeableFloat(99.0)
    with pytest.raises(CostSchemaError, match="execution_padding_pip must be 0.3"):
        validate_cost_table(table, max_spread_pips=None)


def test_n1_an_equality_liar_cannot_forge_the_pinned_slippage_cell() -> None:
    table = _cost_table()
    table["flat_slippage_cell_pip"] = AgreeableFloat(99.0)
    with pytest.raises(CostSchemaError, match="flat_slippage_cell_pip must be 0.5"):
        validate_cost_table(table, max_spread_pips=None)


def test_n1_a_lying_float_magnitude_bound_cannot_be_non_positive() -> None:
    with pytest.raises(CostSchemaError, match="finite positive number of pips"):
        validate_cost_table(_cost_table(), max_spread_pips=LyingFloat(-1.0))


# ===========================================================================
# N-1 — effective_n (a negative raw count was accepted)
# ===========================================================================


def test_n1_plain_negative_raw_event_count_is_refused() -> None:
    with pytest.raises(EffectiveNError, match="must be a non-negative integer"):
        effective_n(
            [{"pair": "EUR_USD", "raw_event_count": -100, "overlap_fraction": 0.0}],
            count_quantity="raw_traded_event_count",
            cross_pair_corr=0.0,
        )


def test_n1_a_lying_int_cannot_supply_a_negative_raw_event_count() -> None:
    """Failing-before: accepted, and the record echoed ``raw_event_count=-100``."""
    with pytest.raises(EffectiveNError, match="must be a non-negative integer"):
        effective_n(
            [{"pair": "EUR_USD", "raw_event_count": LyingInt(-100), "overlap_fraction": 0.0}],
            count_quantity="raw_traded_event_count",
            cross_pair_corr=0.0,
        )


def test_n1_an_accepted_raw_event_count_is_a_plain_int_in_the_record() -> None:
    """The pin reaches the record, so no subclass rides along into the arithmetic."""
    out = effective_n(
        [{"pair": "EUR_USD", "raw_event_count": LyingInt(1200), "overlap_fraction": 0.0}],
        count_quantity="raw_traded_event_count",
        cross_pair_corr=0.0,
    )
    assert type(out["per_pair"][0]["raw_event_count"]) is int
    assert out["raw_event_count"] == 1200


def test_n1_an_overlap_fraction_is_pinned_past_a_conversion_override() -> None:
    """``float(value)`` reported 0.5; the true 5.0 is out of ``[0, 1]`` and refuses."""
    with pytest.raises(EffectiveNError, match=r"must be a finite number in \[0, 1\]"):
        effective_n(
            [
                {
                    "pair": "EUR_USD",
                    "raw_event_count": 1200,
                    "overlap_fraction": LyingConversion(5.0),
                }
            ],
            count_quantity="raw_traded_event_count",
            cross_pair_corr=0.0,
        )


def test_n1_a_lying_int_horizon_cannot_evade_the_frozen_contract_value() -> None:
    with pytest.raises(EffectiveNError, match="is frozen at 24 by the contract"):
        effective_n(
            [{"pair": "EUR_USD", "raw_event_count": 1200, "overlap_fraction": 0.0}],
            count_quantity="raw_traded_event_count",
            cross_pair_corr=0.0,
            horizon_bars=LyingInt(48),
        )


def test_n1_a_lying_validation_floor_cannot_be_non_positive() -> None:
    with pytest.raises(EffectiveNError, match="must be a finite positive number"):
        effective_n(
            [{"pair": "EUR_USD", "raw_event_count": 1200, "overlap_fraction": 0.0}],
            count_quantity="raw_traded_event_count",
            cross_pair_corr=0.0,
            role="validation",
            validation_raw_floor=LyingInt(-1),
            validation_neff_floor=1.0,
        )


# ===========================================================================
# N-1 — coverage and proof (the same family, one level up)
# ===========================================================================


def test_n1_a_lying_int_cannot_supply_a_negative_minute_accounting_quantity() -> None:
    counts = accounting()
    counts["rejected_source_minute_count"] = LyingInt(-3)
    with pytest.raises(MinuteAccountingError, match="is negative"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[],
            minute_accounting=counts,
            rejected_slots=[],
        )


def test_n1_an_equality_liar_cannot_satisfy_the_minute_accounting_identity() -> None:
    """``expected == usable + absent + rejected`` is D-3's identity, decided with ``!=``."""
    counts = dict(accounting())
    counts["expected_source_minute_count"] = AgreeableInt(999)
    with pytest.raises(MinuteAccountingError, match="minute accounting identity violated"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[],
            minute_accounting=counts,
            rejected_slots=[],
        )


def test_n1_an_equality_liar_cannot_forge_the_certifiable_source_minute_count() -> None:
    """``n_source_bars != 15`` is what decides D-3.5 certifiability, so it needs ``__eq__``."""
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import SLOTS, bar

    forged = bar(SLOTS[0], n_source_bars=AgreeableInt(1))
    with pytest.raises(BarNotCertifiableError, match="contract-required source minutes"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[forged],
            minute_accounting=accounting(),
            rejected_slots=[],
        )


def test_n1_a_lying_int_cannot_clear_a_proof_record_count_floor() -> None:
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import measurement

    with pytest.raises(ProofContractError, match="size_bytes must be >= 1"):
        measurement("EUR_USD", 0, size_bytes=LyingInt(-4096))


def test_n1_a_lying_int_cannot_shorten_the_t1_warmup_below_the_feature_lookback() -> None:
    """The sweep beyond the named modules: ``warmup.py`` is the same family.

    ``w_bars < longest_feature_lookback_bars`` is the T-1 leakage boundary, and
    it was decided with ``<`` against the caller's own object.
    """
    policy = WarmupPolicy(w_bars=LyingInt(2), longest_feature_lookback_bars=200)
    with pytest.raises(WarmupPolicyError, match="warm-up too short"):
        policy.validate()


def test_n1_a_lying_int_cannot_supply_a_non_positive_warmup() -> None:
    policy = WarmupPolicy(w_bars=LyingInt(-5), longest_feature_lookback_bars=1)
    with pytest.raises(WarmupPolicyError, match="w_bars must be a positive integer"):
        policy.validate()


def test_n1_a_lying_int_bar_index_cannot_escape_the_burn_in() -> None:
    policy = WarmupPolicy(w_bars=100, longest_feature_lookback_bars=10)
    assert policy.is_event_eligible(LyingInt(5)) is False
    assert policy.is_event_eligible(LyingInt(150)) is True


def test_n1_the_warmup_metadata_reports_plain_ints() -> None:
    policy = WarmupPolicy(w_bars=LyingInt(100), longest_feature_lookback_bars=LyingInt(10))
    metadata = policy.as_metadata()
    assert type(metadata["w_bars"]) is int
    assert type(metadata["longest_feature_lookback_bars"]) is int
    assert type(metadata["first_eligible_bar_index"]) is int


def test_n1_a_lying_int_pass_index_cannot_be_negative() -> None:
    with pytest.raises(proof.ProofCoMeasurementError, match="must not be negative"):
        proof.Provenance(stream_id="s", pass_index=LyingInt(-1), artifact_id="a.jsonl")


# ===========================================================================
# N-2 — open_for_consumption re-checks the disclosure it repeats
# ===========================================================================


def test_n2_an_untampered_proof_still_opens_for_consumption() -> None:
    """Reachability control: the re-check refuses tampering, not every proof."""
    approval = open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
    assert approval.byte_level_status == BYTE_LEVEL_PROOF_PENDING
    assert approval.evidence_basis == LIMB_EVALUATION_EVIDENCE_BASIS
    assert approval.files_opened == 0
    assert approval.bytes_measured == 0


def test_n2_a_tampered_byte_level_claim_token_cannot_mint_an_approval() -> None:
    """N-2's headline: this minted a fresh approval asserting a byte measurement.

    Failing-before: ``approval.byte_level_status`` came back as
    ``BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN`` and ``approval.evidence_basis``
    as ``MEASURED_FROM_DERIVED_ARTIFACT_BYTES__...``, beside ``files_opened=0``.
    """
    result = evaluated_proof()
    object.__setattr__(result, "byte_level_status", BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN)
    with pytest.raises(ProofPromotionError, match="carries byte-level claim token"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_n2_a_tampered_non_pending_status_cannot_mint_an_approval() -> None:
    result = evaluated_proof()
    object.__setattr__(result, "byte_level_status", "SOMETHING_ELSE_ENTIRELY")
    with pytest.raises(ProofNotUsableError, match="the only status this reader-free layer"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_n2_a_tampered_evidence_basis_cannot_mint_an_approval() -> None:
    result = evaluated_proof()
    object.__setattr__(result, "evidence_basis", "MEASURED_FROM_THE_ARTIFACTS_OWN_BYTES")
    with pytest.raises(ProofNotUsableError, match="declares evidence_basis"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_n2_a_tampered_withheld_reason_cannot_mint_an_approval() -> None:
    result = evaluated_proof()
    object.__setattr__(result, "claim_withheld_because", "NOTHING_IS_WITHHELD")
    with pytest.raises(ProofNotUsableError, match="not a caller-settable field"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_n2_a_shortened_declared_not_measured_list_cannot_mint_an_approval() -> None:
    result = evaluated_proof()
    object.__setattr__(result, "declared_not_measured", ("sha256",))
    with pytest.raises(ProofNotUsableError, match="declared_not_measured list is not the one"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_n2_a_tampered_non_zero_byte_count_cannot_mint_an_approval() -> None:
    result = evaluated_proof()
    object.__setattr__(result, "bytes_measured", 4096)
    with pytest.raises(ProofNotUsableError, match="this layer opens no file"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_n2_a_non_string_token_field_is_refused_on_its_type() -> None:
    result = evaluated_proof()
    object.__setattr__(result, "byte_level_status", None)
    with pytest.raises(ProofNotUsableError, match="not a token string"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_n2_a_lying_str_subclass_cannot_spell_the_pending_status() -> None:
    class TwoFacedStatus(str):
        def __str__(self) -> str:  # pragma: no cover - never consulted once pinned
            return BYTE_LEVEL_PROOF_PENDING

    result = evaluated_proof()
    object.__setattr__(
        result, "byte_level_status", TwoFacedStatus(BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN)
    )
    with pytest.raises(ProofPromotionError, match="carries byte-level claim token"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


# ===========================================================================
# N-3 — the byte-level claim vocabulary is unwritable by this package
# ===========================================================================


def test_n3_the_predicate_is_symmetric_across_the_byte_level_vocabulary() -> None:
    """Failing-before: ``True`` for ``BYTE_ADMISSIBLE``, ``False`` for the stronger claim."""
    assert is_forbidden_status("BYTE_ADMISSIBLE") is True
    assert is_forbidden_status(BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN) is True
    assert is_forbidden_status("DERIVATION_IDENTITY_BOUND") is True


@pytest.mark.parametrize("spelling", sorted(UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS))
def test_n3_every_registered_claim_spelling_is_refused_as_a_status(spelling: str) -> None:
    with pytest.raises(RealDataRefusedError, match="may not be asserted here"):
        assert_status_allowed(spelling)


def test_n3_the_claim_vocabulary_survives_the_separator_and_case_fold() -> None:
    assert is_forbidden_status("byte-level no dead window overlap proven") is True
    assert is_forbidden_status("bytelevelnodeadwindowoverlapproven") is True


def test_n3_a_self_refuting_proof_payload_no_longer_scans_clean() -> None:
    """N-3's headline, with no tampering at all: this payload scanned ``[]`` and wrote."""
    payload = {
        "artifact": "no_overlap_proof",
        "gate": "gate3a",
        "metadata_only": True,
        "result": BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
        "source": "MEASURED_FROM_DERIVED_ARTIFACT_BYTES__PRODUCER_AND_VERIFIER_AGREE",
    }
    findings = scan_gate3a(payload, artifact="no_overlap_proof.json")
    assert "gate3a_forbidden_status_value:BYTELEVELNODEADWINDOWOVERLAPPROVEN" in findings
    assert "gate3a_forbidden_status_value:MEASUREDFROMDERIVEDARTIFACTBYTES" in findings


def test_n3_the_evidence_basis_root_catches_any_measured_from_bytes_variant() -> None:
    """The ROOT is registered, so a new suffix cannot walk around the list."""
    findings = scan_gate3a({"source": "MEASURED_FROM_DERIVED_ARTIFACT_BYTES__ANY_NEW_SUFFIX"})
    assert "gate3a_forbidden_status_value:MEASUREDFROMDERIVEDARTIFACTBYTES" in findings


def test_n3_a_self_refuting_proof_payload_cannot_be_written(tmp_path: Any) -> None:
    payload = {
        "artifact": "no_overlap_proof",
        "gate": "gate3a",
        "metadata_only": True,
        "result": BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
    }
    with pytest.raises(ArtifactScrubError, match="gate-3a artifact not clean"):
        write_metadata_artifact(tmp_path / "out", "no_overlap_proof.json", payload)
    assert not (tmp_path / "out" / "no_overlap_proof.json").exists()


def test_n3_every_byte_level_claim_token_is_registered_unwritable() -> None:
    """The import-time cross-check, restated as a test so a rename cannot drift."""
    assert BYTE_LEVEL_CLAIM_TOKENS <= UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS


def test_n3_the_prohibition_entry_bound_was_not_loosened_by_the_new_vocabulary() -> None:
    """A fix that widens a neighbouring guard to close its own finding is not a fix."""
    from scripts.m15_gate3a.artifacts import _MAX_PROHIBITION_ENTRY_LEN

    assert _MAX_PROHIBITION_ENTRY_LEN == max(len(s) for s in FORBIDDEN_STATUSES) == 22


def test_n3_the_committed_proof_artifacts_pending_wording_still_scans_clean() -> None:
    """``BYTE_LEVEL_PROOF PENDING`` is a disclaimer and must not be caught."""
    assert (
        scan_gate3a({"overall": "SOURCE_LEVEL_PROOF_PROVEN (A1-A4); BYTE_LEVEL_PROOF PENDING"})
        == []
    )


# ===========================================================================
# N-4 — the R-1 trap: `pairs_measured` asserted a favourable constant
# ===========================================================================


def test_n4_coverage_result_no_longer_carries_a_one_valued_roster_field() -> None:
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    assert not hasattr(result, "pairs_measured")
    assert "pairs_measured" not in {f.name for f in CoverageResult.__dataclass_fields__.values()}


def test_n4_the_roster_is_recoverable_from_the_measurements_instead() -> None:
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    assert tuple(entry.pair for entry in result.per_pair) == PAIRS_20


def test_n4_the_remaining_constants_are_disclaimers_not_favourable_claims() -> None:
    """R-1 keeps a constant that denies something; it deletes one that asserts."""
    result = evaluated_proof()
    assert result.files_opened == 0
    assert result.bytes_measured == 0
    assert result.claim_withheld_because == BYTE_LEVEL_CLAIM_WITHHELD_REASON
    assert result.declared_not_measured == DECLARED_NOT_MEASURED_BY_THIS_LAYER


# ===========================================================================
# N-5 — copy / deepcopy / pickle bypassed the one-shot construction tokens
# ===========================================================================


def _token_bearing_records() -> list[tuple[str, Any, type[Exception]]]:
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import pair_measurement

    return [
        ("ValidatedCalendar", valid_calendar(), CalendarConstructionError),
        ("PairSlotMeasurement", pair_measurement(PAIRS_20[0]), CoverageConstructionError),
        (
            "CoverageResult",
            assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH),
            CoverageConstructionError,
        ),
        ("ProofResult", evaluated_proof(), ProofConstructionError),
        (
            "ConsumptionApproval",
            open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set()),
            ProofConstructionError,
        ),
    ]


@pytest.mark.parametrize("name", [row[0] for row in _token_bearing_records()])
def test_n5_a_token_bearing_record_cannot_be_shallow_copied(name: str) -> None:
    record, error = next((r, e) for n, r, e in _token_bearing_records() if n == name)
    with pytest.raises(error, match="may not be copied, deep-copied or pickled"):
        copy.copy(record)


@pytest.mark.parametrize("name", [row[0] for row in _token_bearing_records()])
def test_n5_a_token_bearing_record_cannot_be_deep_copied(name: str) -> None:
    record, error = next((r, e) for n, r, e in _token_bearing_records() if n == name)
    with pytest.raises(error, match="may not be copied, deep-copied or pickled"):
        copy.deepcopy(record)


@pytest.mark.parametrize("name", [row[0] for row in _token_bearing_records()])
def test_n5_a_token_bearing_record_cannot_be_pickled(name: str) -> None:
    record, error = next((r, e) for n, r, e in _token_bearing_records() if n == name)
    with pytest.raises(error, match="may not be copied, deep-copied or pickled"):
        pickle.dumps(record)


def test_n5_the_audits_forged_calendar_chain_is_closed_at_the_first_link() -> None:
    """Failing-before: two forged calendars were deep-copied into a satisfied result.

    ``authority="THE OBSERVED DATA ITSELF"`` is a calendar refuting D-6.1's
    single "Never" on its own face; ``copy.deepcopy`` minted it for free.
    """
    calendar = valid_calendar()
    with pytest.raises(CalendarConstructionError, match="rebuild it without spending"):
        copy.deepcopy(calendar)


# ===========================================================================
# N-6 — two closed guards that nothing pinned (COVERAGE GAPS, not defects)
# ===========================================================================

# S1 · path_authority.py:122 — the drive-letter exemption from the NTFS
# alternate-data-stream refusal. Dropping `isascii() and isalpha()` flips these
# four spellings from REFUSED to ALLOWED. The refusal is asserted **by message**
# rather than by exception type, because on a POSIX host the mutated code still
# raises — for the unrelated "relative path" reason — and a bare
# `pytest.raises(PathAuthorityError)` would pass against the mutant there.
_NON_DRIVE_COLON_SPELLINGS: tuple[tuple[str, str], ...] = (
    ("1:\\Users\\x", "a digit is not a drive letter"),
    ("\u0421:\\Users\\x", "Cyrillic ES U+0421: isalpha true, isascii false"),
    ("\uff23:\\Users\\x", "fullwidth C U+FF23: isalpha true, isascii false"),
    ("_:\\Users\\x", "underscore: isalpha false"),
)


@pytest.mark.parametrize(
    ("spelling", "why"), _NON_DRIVE_COLON_SPELLINGS, ids=[s for s, _ in _NON_DRIVE_COLON_SPELLINGS]
)
def test_n6_only_an_ascii_letter_earns_the_drive_colon_exemption(spelling: str, why: str) -> None:
    """The limb itself, host-independently: the colon at index 1 is a stream separator."""
    with pytest.raises(PathAuthorityError, match="names an NTFS alternate data stream"):
        _reject_stream_suffix(spelling)


@pytest.mark.parametrize(
    ("spelling", "why"), _NON_DRIVE_COLON_SPELLINGS, ids=[s for s, _ in _NON_DRIVE_COLON_SPELLINGS]
)
def test_n6_the_drive_colon_limb_is_reached_through_the_public_entry_point(
    spelling: str, why: str
) -> None:
    """Reachability: the same refusal, and the same reason, via ``resolve_candidate``."""
    with pytest.raises(PathAuthorityError, match="stream-qualified path"):
        resolve_candidate(spelling)


def test_n6_an_ascii_drive_letter_keeps_its_exemption() -> None:
    """Control: without this the limb could be 'fixed' by refusing every colon."""
    assert _reject_stream_suffix("C:\\Users\\x") is None
    assert _reject_stream_suffix("z:\\Users\\x") is None


def test_n6_a_colon_anywhere_else_is_still_a_stream_separator() -> None:
    """Control on the other side: the exemption is positional, not global."""
    with pytest.raises(PathAuthorityError, match="names an NTFS alternate data stream"):
        _reject_stream_suffix("C:\\Users\\docs:probe_stream")


# S2 · artifacts.py:995-996 — the `_scan_undeclared` non-string-key recursion.
# Its `_scan_declared` twin at :861-870 is pinned; this one is not. Scope, from
# the mutation study and NOT to be over-read: this is a defence-in-depth loss,
# not a route to a clean scan. `gate3a_non_string_key:<key>` is appended
# unconditionally BEFORE the recursion, so such a payload is refused overall
# either way — what a mutant loses is the finding naming *what* was hidden
# beneath the unrenderable key. Each test below therefore asserts the specific
# lost finding, never merely "it was refused".


def _price_row() -> dict[str, float]:
    return {
        "bid_o": 1.1,
        "bid_h": 1.2,
        "bid_l": 1.0,
        "bid_c": 1.15,
        "ask_o": 1.11,
        "ask_h": 1.21,
        "ask_l": 1.01,
        "ask_c": 1.16,
    }


def test_n6_row_like_records_under_a_non_string_key_are_still_named() -> None:
    findings = scan_gate3a({0: {"rows": [_price_row(), _price_row(), _price_row()]}})
    assert "gate3a_non_string_key:0" in findings
    assert "gate3a_row_like_numeric_records" in findings


def test_n6_columnar_series_under_a_non_string_key_are_still_named() -> None:
    payload = {7: {side: [1.0, 1.1, 1.2, 1.3, 1.4] for side in ("bid", "ask", "mid", "spread")}}
    findings = scan_gate3a(payload)
    assert "gate3a_non_string_key:7" in findings
    assert "gate3a_columnar_numeric_series" in findings


def test_n6_a_numeric_budget_breach_under_a_non_string_key_is_still_counted() -> None:
    payload = {3: {f"col_{i}": [float(j) for j in range(10)] for i in range(15)}}
    findings = scan_gate3a(payload)
    assert "gate3a_non_string_key:3" in findings
    assert "gate3a_columnar_numeric_series" in findings
    assert "gate3a_numeric_cardinality_exceeded" in findings


def test_n6_the_finding_under_a_non_string_key_names_that_key_not_the_parent() -> None:
    """The labelling rule the recursion carries, in the undeclared scanner too."""
    findings = scan_gate3a({"pip_size": {0: [float("nan")]}})
    assert "gate3a_non_finite_value:non_string_key(0)" in findings


# ===========================================================================
# N-7 — the unrouted aggregate-assertion guard, and what actually enforces it
# ===========================================================================


def test_n7_the_committed_aggregate_assertion_names_are_unchanged() -> None:
    assert set(AGGREGATE_ASSERTIONS) == {
        "dead_window_bars_present_is_zero",
        "all_ts_max_within_design_end",
        "all_ts_min_within_design_start",
        "file_count_is_20",
    }


def test_n7_the_tc_limb_enforces_the_dead_window_assertion_inline() -> None:
    """The factual basis of the disclosure: the substance moved, it did not vanish.

    Producer and verifier are overridden together, because a one-sided override
    would be caught by the earlier field-by-field agreement check rather than by
    the limb under test.
    """
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import producer_set, verifier_set

    override = {
        "dead_window_bars_by_bucket_start": 1,
        "dead_window_bars_by_contributing_minute": 1,
    }
    with pytest.raises(ProofLimbUnsatisfiedError, match="dead-window bar"):
        evaluated_proof(
            producer_records=producer_set(**override),
            verifier_records=verifier_set(**override),
        )


def test_n7_the_tc_limb_enforces_the_design_span_assertions_inline() -> None:
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import producer_set, verifier_set

    # Three bucket starts, matching the fixture's `bars_scanned`, but placed
    # inside the consumed dead window rather than the design epoch.
    override = {
        "measured_ts_min": "2026-03-05T00:00:00Z",
        "measured_ts_max": "2026-03-05T00:30:00Z",
    }
    with pytest.raises(ProofLimbUnsatisfiedError, match="not inside the frozen design epoch"):
        evaluated_proof(
            producer_records=producer_set(**override),
            verifier_records=verifier_set(**override),
        )


def test_n7_the_bi_limb_enforces_the_file_count_assertion_inline() -> None:
    """``file_count_is_20``: nineteen measured artifacts is not the conjunction."""
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import producer_set, verifier_set

    with pytest.raises(ProofLimbUnsatisfiedError, match="BI limb: no byte measurement for"):
        evaluated_proof(
            producer_records=producer_set()[:-1],
            verifier_records=verifier_set()[:-1],
        )


# ===========================================================================
# §12.23 at the writer — the isoformat spelling must not reach any artifact
# ===========================================================================


def test_1223_an_isoformat_offset_spelling_is_a_finding() -> None:
    """Failing-before: ``findings == []`` and the file WROTE."""
    findings = scan_gate3a(
        {
            "artifact": "design_m15_inventory",
            "gate": "gate3a",
            "metadata_only": True,
            "ts_min_utc": "2025-06-02T00:00:00+00:00",
        },
        artifact="design_m15_inventory.json",
    )
    assert findings == ["gate3a_non_canonical_timestamp:ts_min_utc:2025-06-02T00:00:00+00:00"]


def test_1223_the_canonical_z_spelling_is_clean() -> None:
    assert (
        scan_gate3a(
            {
                "artifact": "design_m15_inventory",
                "gate": "gate3a",
                "metadata_only": True,
                "ts_min_utc": "2025-06-02T00:00:00Z",
            },
            artifact="design_m15_inventory.json",
        )
        == []
    )


def test_1223_the_committed_all_zero_excess_digit_form_stays_clean() -> None:
    """§12.23 expressly accepts all-zero excess; the committed M1 inventory uses it."""
    assert (
        scan_gate3a(
            {
                "artifact": "design_m15_inventory",
                "gate": "gate3a",
                "metadata_only": True,
                "ts_min_utc": "2025-04-24T22:03:00.000000000Z",
            },
            artifact="design_m15_inventory.json",
        )
        == []
    )


@pytest.mark.parametrize(
    "value",
    [
        "2026-07-07",
        "DESIGN span only (2025-04-25..2026-02-28); never validation/holdout",
        "2026-09-25 (validation ~2026-04-25..2026-07-25 + purge + holdout)",
        "<= 2026-02-28T23:59:59Z",
    ],
)
def test_1223_the_rule_is_a_spelling_check_not_a_schema_requirement(value: str) -> None:
    """Bare dates and dates in prose are untouched; only an offset-bearing one fires."""
    assert scan_gate3a({"reason": value}) == []


@pytest.mark.parametrize(
    "spelling",
    [
        "2025-06-02T00:00:00+00:00",
        "2025-06-02T00:00:00-05:00",
        "2025-06-02T00:00:00+0000",
        "2025-06-02T00:00+00:00",
        "2025-06-02T00:00:00.123456+00:00",
        "2025-06-02 00:00:00+00:00",
    ],
)
def test_1223_every_numeric_offset_rendering_is_caught(spelling: str) -> None:
    findings = scan_gate3a({"ts_min_utc": spelling})
    assert any(f.startswith("gate3a_non_canonical_timestamp:") for f in findings), findings


def test_1223_a_non_canonical_timestamp_used_as_a_key_is_caught() -> None:
    findings = scan_gate3a({"2025-06-02T00:00:00+00:00": "note"})
    assert any(f.startswith("gate3a_non_canonical_timestamp:") for f in findings), findings


def test_1223_a_prohibition_list_earns_no_exemption_from_the_spelling_rule() -> None:
    payload = {
        "artifact": "scrub_report",
        "gate": "gate3a",
        "metadata_only": True,
        "forbidden_labels": ["2025-06-02T00:00:00+00:00"],
    }
    findings = scan_gate3a(payload, artifact="scrub_report.json")
    assert any(f.startswith("gate3a_non_canonical_timestamp:") for f in findings), findings


def test_1223_a_non_canonical_timestamp_cannot_be_written(tmp_path: Any) -> None:
    payload = {
        "artifact": "design_m15_inventory",
        "gate": "gate3a",
        "metadata_only": True,
        "ts_min_utc": "2025-06-02T00:00:00+00:00",
    }
    with pytest.raises(ArtifactScrubError, match="gate-3a artifact not clean"):
        write_metadata_artifact(tmp_path / "out", "design_m15_inventory.json", payload)
    assert not (tmp_path / "out" / "design_m15_inventory.json").exists()


# ===========================================================================
# Mandatory regression — the committed evidence must keep scanning clean
# ===========================================================================


def test_regression_every_committed_gate3a_artifact_still_scans_clean() -> None:
    from tests.m15_gate3a.test_second_recheck_fixes import REPO_ROOT

    committed = sorted((REPO_ROOT / "artifacts" / "m15_gate3a").glob("*.json"))
    assert len(committed) == 8, [p.name for p in committed]
    for path in committed:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert scan_gate3a(payload, artifact=path.name) == [], path.name


def test_regression_a_populated_20_record_inventory_is_still_writable(tmp_path: Any) -> None:
    payload = {
        "artifact": "design_m15_inventory",
        "gate": "gate3a",
        "metadata_only": True,
        "raw_rows_committed": False,
        "files": [
            {
                "pair": pair,
                "filename": f"candles_{pair}_M15_365d_BA_DESIGN.jsonl",
                "sha256": f"{index:064x}",
                "ts_min_utc": "2025-04-25T00:00:00Z",
                "ts_max_utc": "2026-02-28T23:45:00Z",
                "complete_bucket_count": 20000 + index,
            }
            for index, pair in enumerate(PAIRS_20)
        ],
    }
    target = write_metadata_artifact(tmp_path / "out", "design_m15_inventory.json", payload)
    written = json.loads(target.read_text(encoding="utf-8"))
    assert len(written["files"]) == len(PAIRS_20)
    assert written["files"][0]["complete_bucket_count"] == 20000


def test_regression_a_scrub_report_listing_its_own_labels_is_still_writable(tmp_path: Any) -> None:
    payload = {
        "artifact": "scrub_report",
        "gate": "gate3a",
        "metadata_only": True,
        "findings": [],
        "forbidden_labels": sorted(FORBIDDEN_STATUSES),
    }
    target = write_metadata_artifact(tmp_path / "out", "scrub_report.json", payload)
    labels = json.loads(target.read_text(encoding="utf-8"))["forbidden_labels"]
    assert sorted(labels) == sorted(FORBIDDEN_STATUSES)


def test_regression_an_ordinary_certifiable_aggregation_is_unaffected() -> None:
    """The N-1 pin must not have turned an honest bucket into a refusal."""
    rows = [
        {
            "ts": START.replace(minute=minute),
            "bid_o": 1.1000,
            "bid_h": 1.1005,
            "bid_l": 1.0995,
            "bid_c": 1.1002,
            "ask_o": 1.1001,
            "ask_h": 1.1006,
            "ask_l": 1.0996,
            "ask_c": 1.1003,
        }
        for minute in range(15)
    ]
    emitted, report = aggregate_m15(rows, pair="EUR_USD")
    assert len(emitted) == 1
    assert emitted[0]["n_source_bars"] == 15
    assert emitted[0]["complete_bucket"] is True
    assert report["complete_bucket_count"] == 1


def test_regression_full_coverage_is_still_reachable_end_to_end() -> None:
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    assert len(result.per_pair) == len(PAIRS_20)
    assert bars  # the fixture builder is exercised above; keep the import honest
