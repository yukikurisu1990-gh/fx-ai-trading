"""Cost-schema / effective-N / warm-up / package-status regression tests.

Closes the third independent re-check's **RF-16, RF-17, RF-19, RF-23, RF-26,
RF-27, RF-28, RF-29** and **B-7(b)**, plus the contract Gate-decision's **D-10
(NR-J)**, **R-1** (negative control) and **R-2** (pinned terms) as they fall in
``cost_schema.py``, ``effective_n.py``, ``warmup.py`` and the package
``__init__``.

Method notes, each grounded in an anti-pattern the audit found in this suite:

* every expectation is behavioural — no test here asserts on source text;
* no ``pytest.raises(match=...)`` alternation: each refusal is identified by a
  substring only that guard emits, so a test cannot pass because *some other*
  guard fired;
* the committed authority is re-read from the artifact JSON rather than restated
  from the module under test, so a module constant that drifts from the plan
  fails here;
* every deleted self-attestation is replaced by a two-valued demonstration, not
  by an assertion that the field is gone alone;
* nothing here reads market data, computes a spread, or touches validation,
  holdout, training or execution.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a import (
    EXECUTION_STATUS,
    FORWARD_EPOCH_STATUS,
    IMPLEMENTATION_STATUS,
    PRODUCTION_STATUS,
)
from scripts.m15_gate3a.cost_schema import (
    CLAIM_SCOPE,
    DATA_SOURCE_RESTRICTION,
    SESSIONS_UTC,
    STRESS_FORMS,
    CostSchemaError,
    validate_cost_table,
)
from scripts.m15_gate3a.effective_n import (
    COMPLETE_BUCKET_COUNT,
    COST_HURDLE_ELIGIBLE_BAR_COUNT,
    INSUFFICIENT_SAMPLE,
    RAW_TRADED_EVENT_COUNT,
    SUFFICIENT,
    CountQuantityError,
    EffectiveNError,
    effective_n,
)
from scripts.m15_gate3a.no_overlap import FORWARD_FLOOR
from scripts.m15_gate3a.pair_authority import PAIRS_20, pip_size_for_pair
from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError

REPO_ROOT = Path(__file__).resolve().parents[2]
COST_PLAN_PATH = REPO_ROOT / "artifacts" / "m15_gate3a" / "cost_table_plan_or_metadata.json"

# Restated independently of the modules under test (the point of the pin).
PLAN_CLAIM_SCOPE = "quote-cost-validity research claim; NOT a live-fill claim"
PLAN_STRESS_FORMS = ["2x modelled cost", "p90 session spread substituted for median"]
PLAN_DATA_SOURCE_RESTRICTION = (
    "DESIGN span only (2025-04-25..2026-02-28); never validation/holdout; "
    "frozen and committed as metadata"
)
PLAN_FORMULA = "cost(pair, session) = median_spread(pair, session) + 0.3 + 0.5 (primary)"
SESSION_NAMES = ("asia", "europe", "us")
EXPECTED_CELLS = 60  # 20 canonical pairs x 3 UTC sessions, both operands frozen


def _committed_plan() -> dict:
    text = COST_PLAN_PATH.read_text(encoding="utf-8")
    assert len(text) > 200, "committed cost plan is missing or truncated"  # non-vacuity floor
    return json.loads(text)["must_produce_before_gate7_authorisation"]


def _cell(pair: str, session: str) -> dict:
    """One synthetic (pair, session) cost cell. Spreads are invented test numbers."""
    pip = pip_size_for_pair(pair)
    return {
        "pair": pair,
        "session": session,
        "median_spread": 1.0 * pip,
        "p90_spread": 2.0 * pip,
        "p95_spread": 3.0 * pip,
        "pip_size": pip,
    }


def _full_table(**overrides: Any) -> dict:
    """A complete 20 x 3 synthetic table that satisfies every frozen requirement."""
    table = {
        "execution_padding_pip": 0.3,
        "flat_slippage_cell_pip": 0.5,
        "all_in_cost_formula": PLAN_FORMULA,
        "spread_unit": "price",
        "claim_scope": PLAN_CLAIM_SCOPE,
        "stress_forms": list(PLAN_STRESS_FORMS),
        "data_source_restriction": PLAN_DATA_SOURCE_RESTRICTION,
        "entries": [_cell(p, s) for p in PAIRS_20 for s in SESSION_NAMES],
    }
    table.update(overrides)
    return table


def _pp(pair: str, raw: int, overlap: float) -> dict:
    return {"pair": pair, "raw_event_count": raw, "overlap_fraction": overlap}


# ---------------------------------------------------------------- sanity floor


def test_the_synthetic_full_table_is_the_shape_the_other_tests_assume() -> None:
    """If this fixture stopped being complete, every refusal test below would be vacuous."""
    table = _full_table()
    assert len(table["entries"]) == EXPECTED_CELLS
    assert len({(e["pair"], e["session"]) for e in table["entries"]}) == EXPECTED_CELLS
    assert sorted(SESSIONS_UTC) == sorted(SESSION_NAMES)
    assert len(PAIRS_20) * len(SESSION_NAMES) == EXPECTED_CELLS


# ------------------------------------------------------- RF-17: claim scope


def test_rf17_claim_scope_is_the_committed_plan_spelling_not_a_code_minted_one() -> None:
    """The validator used to refuse the very spelling the committed plan declares."""
    assert CLAIM_SCOPE == PLAN_CLAIM_SCOPE
    assert _committed_plan()["claim_scope"] == CLAIM_SCOPE
    # FR-5: the one-valued ``result`` token is gone. That the committed spelling
    # is accepted is shown by the call returning at all, and by the refusal of the
    # code-minted spelling in the next test.
    assert validate_cost_table(_full_table(), max_spread_pips=None)["spread_unit"] == "price"


def test_rf17_the_code_minted_claim_scope_is_now_refused() -> None:
    with pytest.raises(CostSchemaError, match="claim_scope"):
        validate_cost_table(_full_table(claim_scope="quote_cost_validity"), max_spread_pips=None)


def test_rf17_a_live_fill_claim_scope_is_still_refused() -> None:
    with pytest.raises(CostSchemaError, match="claim_scope"):
        validate_cost_table(_full_table(claim_scope="live_fill_validity"), max_spread_pips=None)


# ------------------------- RF-16: stress forms and the data-source restriction


def test_rf16_module_constants_match_the_committed_plan_verbatim() -> None:
    plan = _committed_plan()
    assert list(STRESS_FORMS) == plan["stress_forms"] == PLAN_STRESS_FORMS
    assert plan["data_source_restriction"] == DATA_SOURCE_RESTRICTION
    assert DATA_SOURCE_RESTRICTION == PLAN_DATA_SOURCE_RESTRICTION


@pytest.mark.parametrize("key", ["stress_forms", "data_source_restriction"])
def test_rf16_the_plan_keys_are_required(key: str) -> None:
    table = _full_table()
    del table[key]
    with pytest.raises(CostSchemaError, match=f"missing global key '{key}'"):
        validate_cost_table(table, max_spread_pips=None)


def test_rf16_a_table_omitting_both_no_longer_validates() -> None:
    """The exact RF-16 finding: such a table returned COST_TABLE_SCHEMA_VALID."""
    table = _full_table()
    del table["stress_forms"]
    del table["data_source_restriction"]
    with pytest.raises(CostSchemaError, match="missing global key"):
        validate_cost_table(table, max_spread_pips=None)


@pytest.mark.parametrize("dropped", [0, 1])
def test_rf16_each_stress_form_is_individually_mandatory(dropped: int) -> None:
    kept = [f for i, f in enumerate(PLAN_STRESS_FORMS) if i != dropped]
    with pytest.raises(CostSchemaError, match="missing the mandatory form"):
        validate_cost_table(_full_table(stress_forms=kept), max_spread_pips=None)


def test_rf16_an_unauthorised_stress_form_is_refused() -> None:
    forms = [*PLAN_STRESS_FORMS, "0.5x modelled cost"]
    with pytest.raises(CostSchemaError, match="unauthorised form"):
        validate_cost_table(_full_table(stress_forms=forms), max_spread_pips=None)


def test_rf16_a_repeated_stress_form_is_refused() -> None:
    forms = [PLAN_STRESS_FORMS[0], PLAN_STRESS_FORMS[0], PLAN_STRESS_FORMS[1]]
    with pytest.raises(CostSchemaError, match="repeat a stress form"):
        validate_cost_table(_full_table(stress_forms=forms), max_spread_pips=None)


@pytest.mark.parametrize("bad", ["2x modelled cost", None, 2, {"a": 1}])
def test_rf16_stress_forms_must_be_a_list(bad: Any) -> None:
    with pytest.raises(CostSchemaError, match="stress_forms must be a list"):
        validate_cost_table(_full_table(stress_forms=bad), max_spread_pips=None)


@pytest.mark.parametrize("bad_element", [None, 2, True, ["2x modelled cost"]])
def test_rf16_stress_form_entries_must_be_strings(bad_element: Any) -> None:
    forms = [PLAN_STRESS_FORMS[0], bad_element]
    with pytest.raises(CostSchemaError, match="entries must be strings"):
        validate_cost_table(_full_table(stress_forms=forms), max_spread_pips=None)


@pytest.mark.parametrize(
    "restriction",
    [
        "VALIDATION span only (2026-04-25..2026-07-25)",
        "DESIGN span only (2025-04-25..2026-02-28)",  # truncated: drops "never validation/holdout"
        "design span only (2025-04-25..2026-02-28); never validation/holdout; "
        "frozen and committed as metadata",  # casing drift
        "",
    ],
)
def test_rf16_a_non_committed_data_source_restriction_is_refused(restriction: str) -> None:
    with pytest.raises(CostSchemaError, match="data_source_restriction"):
        validate_cost_table(_full_table(data_source_restriction=restriction), max_spread_pips=None)


# ------------------------------ RF-19 / D-10 (NR-J) / §12.16: 20 x 3 coverage


def test_rf19_the_complete_60_cell_grid_validates() -> None:
    """FR-5: ``entries_validated``, ``pairs_covered`` and ``result`` are deleted.

    All three held one value on every returning path, which R-1 forbids. The
    property this test names — the complete grid validates — is now expressed by
    the call returning, against the refusals of the incomplete grids below.
    """
    summary = validate_cost_table(_full_table(), max_spread_pips=None)
    assert "entries_validated" not in summary
    assert "pairs_covered" not in summary
    assert "result" not in summary
    assert len(_full_table()["entries"]) == EXPECTED_CELLS


def test_rf19_a_one_entry_table_is_refused_and_names_the_missing_cells() -> None:
    """R-8's fourth limb: "a one-entry table validates, so 20 x 3 is unenforced"."""
    table = _full_table(entries=[_cell("EUR_USD", "europe")])
    with pytest.raises(CostSchemaError, match="59 missing") as exc:
        validate_cost_table(table, max_spread_pips=None)
    message = str(exc.value)
    assert "USD_JPY/asia" in message  # a named missing cell, not just a count
    assert "EUR_USD/europe" not in message  # the one present cell is not reported missing


def test_rf19_the_59_vs_60_boundary_raises_and_names_the_single_missing_cell() -> None:
    entries = [_cell(p, s) for p in PAIRS_20 for s in SESSION_NAMES]
    dropped = entries.pop(entries.index(_cell("GBP_JPY", "us")))
    assert len(entries) == EXPECTED_CELLS - 1
    with pytest.raises(CostSchemaError, match="1 missing: GBP_JPY/us") as exc:
        validate_cost_table(_full_table(entries=entries), max_spread_pips=None)
    assert "AUD_USD" not in str(exc.value)  # only the genuinely absent cell is named
    entries.append(dropped)
    assert len(entries) == EXPECTED_CELLS
    # FR-5: restoring the cell makes the call return instead of raising; there is
    # no longer a one-valued count field to read the same fact off.
    validate_cost_table(_full_table(entries=entries), max_spread_pips=None)


def test_rf19_a_full_pair_roster_with_one_session_missing_is_refused() -> None:
    """20 pairs are present, so a pair-count check would have passed this table."""
    entries = [_cell(p, s) for p in PAIRS_20 for s in ("asia", "europe")]
    with pytest.raises(CostSchemaError, match="20 missing") as exc:
        validate_cost_table(_full_table(entries=entries), max_spread_pips=None)
    assert "EUR_USD/us" in str(exc.value)


def test_rf19_a_full_session_roster_with_one_pair_missing_is_refused() -> None:
    entries = [_cell(p, s) for p in PAIRS_20[:-1] for s in SESSION_NAMES]
    with pytest.raises(CostSchemaError, match="3 missing") as exc:
        validate_cost_table(_full_table(entries=entries), max_spread_pips=None)
    assert "GBP_CHF/asia" in str(exc.value)


def test_rf19_the_duplicate_cell_refusal_survives_the_coverage_requirement() -> None:
    """A 60-entry table can still be short of 60 cells; duplicates must fire first."""
    entries = [_cell(p, s) for p in PAIRS_20 for s in SESSION_NAMES]
    entries[-1] = _cell("EUR_USD", "asia")  # 60 entries, 59 distinct cells
    assert len(entries) == EXPECTED_CELLS
    with pytest.raises(CostSchemaError, match="duplicate"):
        validate_cost_table(_full_table(entries=entries), max_spread_pips=None)


def test_rf19_no_coverage_flag_is_reported_at_all() -> None:
    """D-10: recording a coverage flag never permits continuation, so none is recorded."""
    summary = validate_cost_table(_full_table(), max_spread_pips=None)
    assert "full_20x3_coverage" not in summary


# ------------------------------------------- RF-27 / RF-29: vacuous and mistyped input


def test_rf27_an_empty_entries_list_is_refused_as_such() -> None:
    with pytest.raises(CostSchemaError, match="non-empty list"):
        validate_cost_table(_full_table(entries=[]), max_spread_pips=None)


@pytest.mark.parametrize("bad", [[], ["entries"], 42, None, 0.5, ("a", "b"), {"a"}, "table"])
def test_rf29_a_non_dict_cost_table_raises_the_modules_own_error(bad: Any) -> None:
    """Bare ``TypeError`` is not "fails closed with the documented exception type"."""
    with pytest.raises(CostSchemaError, match="cost table must be a dict"):
        validate_cost_table(bad, max_spread_pips=None)


def test_rf29_the_entry_level_refusals_keep_their_own_error_type() -> None:
    entries = [_cell(p, s) for p in PAIRS_20 for s in SESSION_NAMES]
    entries[0] = "EUR_USD/asia"
    with pytest.raises(CostSchemaError, match="cost entry must be a dict"):
        validate_cost_table(_full_table(entries=entries), max_spread_pips=None)


# ------------------------------------------------ R-1: cost-summary attestations


def test_r1_the_vacuous_cost_summary_attestations_are_deleted() -> None:
    summary = validate_cost_table(_full_table(), max_spread_pips=None)
    assert "p95_diagnostic_present" not in summary
    assert "real_spreads_computed" not in summary


def test_r1_the_p95_property_is_enforced_by_refusal_rather_than_attested() -> None:
    """The negative control the deleted boolean never had."""
    entries = [_cell(p, s) for p in PAIRS_20 for s in SESSION_NAMES]
    del entries[0]["p95_spread"]
    with pytest.raises(CostSchemaError, match="p95_spread"):
        validate_cost_table(_full_table(entries=entries), max_spread_pips=None)


def test_r1_the_magnitude_flag_that_survives_is_genuinely_two_valued() -> None:
    unbounded = validate_cost_table(_full_table(), max_spread_pips=None)
    bounded = validate_cost_table(_full_table(), max_spread_pips=50.0)
    assert unbounded["magnitude_checked_against_declared_bound"] is False
    assert bounded["magnitude_checked_against_declared_bound"] is True
    assert unbounded["magnitude_authority"] == "REQUIRES_SEPARATE_CONTRACT_GATE_DECISION"
    assert bounded["magnitude_authority"] == "CALLER_DECLARED"


# ----------------------------------- R-2 / §12.20: which count is being passed


def test_r2_the_three_pinned_count_quantity_names_are_the_contract_ones() -> None:
    assert COMPLETE_BUCKET_COUNT == "complete_bucket_count"
    assert COST_HURDLE_ELIGIBLE_BAR_COUNT == "cost_hurdle_eligible_bar_count"
    assert RAW_TRADED_EVENT_COUNT == "raw_traded_event_count"


def test_r2_count_quantity_is_mandatory_and_has_no_default() -> None:
    """Omitting it cannot proceed: the call never enters the estimator."""
    with pytest.raises(TypeError, match="count_quantity"):
        effective_n([_pp("EUR_USD", 1200, 0.0)], cross_pair_corr=0.0)  # type: ignore[call-arg]


def test_r2_the_traded_event_quantity_is_admissible() -> None:
    result = effective_n(
        [_pp("EUR_USD", 1200, 0.0)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
    )
    assert result["raw_event_count"] == 1200
    assert result["verdict"] == SUFFICIENT


def test_r2_the_complete_bucket_count_is_refused_by_name() -> None:
    with pytest.raises(CountQuantityError, match="not traded events"):
        effective_n(
            [_pp("EUR_USD", 1200, 0.0)],
            count_quantity=COMPLETE_BUCKET_COUNT,
            cross_pair_corr=0.0,
        )


def test_r2_the_cost_hurdle_eligible_bar_count_is_refused_by_name() -> None:
    with pytest.raises(CountQuantityError, match="EV-gated trades that fired"):
        effective_n(
            [_pp("EUR_USD", 1200, 0.0)],
            count_quantity=COST_HURDLE_ELIGIBLE_BAR_COUNT,
            cross_pair_corr=0.0,
        )


@pytest.mark.parametrize(
    "declared",
    ["raw_event_count", "eligible_event_count", "RAW_TRADED_EVENT_COUNT", "", "n_raw"],
)
def test_r2_an_unpinned_declaration_is_refused(declared: str) -> None:
    with pytest.raises(CountQuantityError, match="unknown count_quantity"):
        effective_n(
            [_pp("EUR_USD", 1200, 0.0)],
            count_quantity=declared,
            cross_pair_corr=0.0,
        )


@pytest.mark.parametrize("declared", [None, 1, True, b"raw_traded_event_count", ["x"]])
def test_r2_a_non_string_declaration_is_refused(declared: Any) -> None:
    with pytest.raises(CountQuantityError, match="exact str"):
        effective_n(
            [_pp("EUR_USD", 1200, 0.0)],
            count_quantity=declared,
            cross_pair_corr=0.0,
        )


def test_r2_a_lying_str_subclass_declaration_is_refused() -> None:
    """``__eq__`` is overridable; the one literal guarding the floors may not trust it."""

    class AlwaysEqual(str):
        def __eq__(self, other: object) -> bool:
            return True

        def __hash__(self) -> int:
            return hash(str(self))

    with pytest.raises(CountQuantityError, match="exact str"):
        effective_n(
            [_pp("EUR_USD", 1200, 0.0)],
            count_quantity=AlwaysEqual("complete_bucket_count"),
            cross_pair_corr=0.0,
        )


def test_r2_the_bucket_count_would_have_disarmed_insufficient_sample() -> None:
    """Why the declaration exists, stated as an executable comparison.

    Same 20 pairs, same span, two different quantities: complete 15-minute
    buckets clear the frozen floors by two orders of magnitude, while the traded
    events that actually fired do not. Only the second is admissible, so the
    first can no longer be fed in by accident.
    """
    buckets = [_pp(p, 5_000, 0.0) for p in PAIRS_20]
    traded = [_pp(p, 30, 0.0) for p in PAIRS_20]

    with pytest.raises(CountQuantityError):
        effective_n(buckets, count_quantity=COMPLETE_BUCKET_COUNT, cross_pair_corr=0.0)

    honest = effective_n(traded, count_quantity=RAW_TRADED_EVENT_COUNT, cross_pair_corr=0.0)
    assert honest["raw_event_count"] == 600
    assert honest["verdict"] == INSUFFICIENT_SAMPLE

    # The same numbers, mislabelled, are what the floors would have seen.
    mislabelled = effective_n(buckets, count_quantity=RAW_TRADED_EVENT_COUNT, cross_pair_corr=0.0)
    assert mislabelled["raw_event_count"] == 100_000
    assert mislabelled["verdict"] == SUFFICIENT


# ------------------------------------------- RF-23: the validation floor conjunction


def test_rf23_validation_is_insufficient_when_only_the_raw_floor_is_violated() -> None:
    """raw 500 < 1000, but N_eff 500 >= 100. An ``and`` conjunction flips this."""
    result = effective_n(
        [_pp("EUR_USD", 500, 0.0)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
        role="validation",
        validation_raw_floor=1000,
        validation_neff_floor=100.0,
    )
    assert result["raw_event_count"] == 500
    assert result["effective_n"] == pytest.approx(500.0)
    assert result["verdict"] == INSUFFICIENT_SAMPLE


def test_rf23_validation_is_insufficient_when_only_the_neff_floor_is_violated() -> None:
    """The audit's own case: raw 500 >= 100, N_eff 500 < 1000."""
    result = effective_n(
        [_pp("EUR_USD", 500, 0.0)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
        role="validation",
        validation_raw_floor=100,
        validation_neff_floor=1000.0,
    )
    assert result["verdict"] == INSUFFICIENT_SAMPLE


def test_rf23_validation_is_sufficient_only_when_both_floors_are_cleared() -> None:
    """Without this limb an "always INSUFFICIENT" mutant would pass the two above."""
    result = effective_n(
        [_pp("EUR_USD", 500, 0.0)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
        role="validation",
        validation_raw_floor=100,
        validation_neff_floor=100.0,
    )
    assert result["verdict"] == SUFFICIENT


def test_rf23_the_holdout_conjunction_is_pinned_on_both_limbs_too() -> None:
    raw_only = effective_n(
        [_pp("EUR_USD", 900, 0.0)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
    )
    neff_only = effective_n(
        [_pp("EUR_USD", 1200, 1.0)],  # raw >= 1000, N_eff = 1200/24 = 50 < 400
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
    )
    assert raw_only["verdict"] == INSUFFICIENT_SAMPLE
    assert neff_only["effective_n"] == pytest.approx(50.0)
    assert neff_only["verdict"] == INSUFFICIENT_SAMPLE


# ------------------------------------------------- RF-26 / RF-29: input discipline


def test_rf26_a_generator_of_per_pair_records_is_refused() -> None:
    """Lazy evidence cannot be re-read, so it is not evidence (the BL-1 lesson)."""
    records = (_pp(p, 1200, 0.0) for p in PAIRS_20)
    with pytest.raises(EffectiveNError, match="must be a sequence"):
        effective_n(records, count_quantity=RAW_TRADED_EVENT_COUNT, cross_pair_corr=0.0)


def test_rf26_an_iterator_over_a_list_is_refused_as_well() -> None:
    with pytest.raises(EffectiveNError, match="must be a sequence"):
        effective_n(
            iter([_pp("EUR_USD", 1200, 0.0)]),
            count_quantity=RAW_TRADED_EVENT_COUNT,
            cross_pair_corr=0.0,
        )


def test_rf26_the_equivalent_list_is_accepted() -> None:
    """Otherwise the two refusals above could be satisfied by refusing everything."""
    result = effective_n(
        [_pp(p, 1200, 0.0) for p in PAIRS_20],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
    )
    assert result["n_pairs"] == len(PAIRS_20)


@pytest.mark.parametrize("key", ["pair", "raw_event_count", "overlap_fraction"])
def test_rf29_a_per_pair_record_missing_a_key_raises_effective_n_error(key: str) -> None:
    """A bare ``KeyError`` is not the documented exception type."""
    record = _pp("EUR_USD", 1200, 0.0)
    del record[key]
    with pytest.raises(EffectiveNError, match=f"missing key '{key}'"):
        effective_n([record], count_quantity=RAW_TRADED_EVENT_COUNT, cross_pair_corr=0.0)


# ----------------------------------------------------------- R-1: effective-N


def test_r1_the_vacuous_effective_n_attestation_is_deleted() -> None:
    result = effective_n(
        [_pp("EUR_USD", 1200, 0.0)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
    )
    assert "strategy_metrics_computed" not in result
    # The verdict, which *is* two-valued, is still reported.
    assert result["verdict"] in {SUFFICIENT, INSUFFICIENT_SAMPLE}


# -------------------------------------------------------- RF-28: warm-up floors


@pytest.mark.parametrize("lookback", [0, -1, -100])
def test_rf28_a_non_positive_lookback_is_refused(lookback: int) -> None:
    """``<= 0`` mutated to ``< 0`` yielded valid warm-up metadata for a zero lookback."""
    with pytest.raises(WarmupPolicyError, match="longest_feature_lookback_bars must be a positive"):
        WarmupPolicy(w_bars=5, longest_feature_lookback_bars=lookback).validate()


@pytest.mark.parametrize("lookback", [0, -1])
def test_rf28_a_non_positive_lookback_cannot_produce_metadata(lookback: int) -> None:
    with pytest.raises(WarmupPolicyError, match="longest_feature_lookback_bars must be a positive"):
        WarmupPolicy(w_bars=5, longest_feature_lookback_bars=lookback).as_metadata()


@pytest.mark.parametrize("w_bars", [0, -1, -100])
def test_rf28_a_non_positive_w_bars_is_refused_in_isolation(w_bars: int) -> None:
    """Paired with an equally invalid lookback, so only the ``w_bars`` limb can answer."""
    with pytest.raises(WarmupPolicyError, match=r"\bw_bars must be a positive integer"):
        WarmupPolicy(w_bars=w_bars, longest_feature_lookback_bars=w_bars).validate()


def test_rf28_a_zero_lookback_cannot_authorise_a_load() -> None:
    with pytest.raises(WarmupPolicyError, match="longest_feature_lookback_bars must be a positive"):
        WarmupPolicy(w_bars=5, longest_feature_lookback_bars=0).assert_load_allowed(
            FORWARD_FLOOR + timedelta(days=1)
        )


# ------------------------------------------------------------ R-1: warm-up claims


def test_r1_warmup_metadata_no_longer_asserts_the_t1_leakage_claim() -> None:
    metadata = WarmupPolicy(w_bars=300, longest_feature_lookback_bars=200).as_metadata()
    assert "dead_window_loaded" not in metadata
    assert "first_w_bars_event_eligible" not in metadata
    assert metadata["first_eligible_bar_index"] == 300


@pytest.mark.parametrize(
    "bar_index,eligible", [(0, False), (1, False), (299, False), (300, True), (301, True)]
)
def test_r1_event_eligibility_is_measured_and_takes_both_values(
    bar_index: int, eligible: bool
) -> None:
    policy = WarmupPolicy(w_bars=300, longest_feature_lookback_bars=200)
    assert policy.is_event_eligible(bar_index) is eligible


@pytest.mark.parametrize("bad", [-1, 1.0, True, None, "0"])
def test_r1_event_eligibility_refuses_an_unusable_bar_index(bad: Any) -> None:
    policy = WarmupPolicy(w_bars=300, longest_feature_lookback_bars=200)
    with pytest.raises(WarmupPolicyError, match="bar_index"):
        policy.is_event_eligible(bad)


def test_r1_the_pre_forward_predicate_takes_both_values() -> None:
    policy = WarmupPolicy(w_bars=50, longest_feature_lookback_bars=50)
    assert policy.loads_pre_forward(FORWARD_FLOOR - timedelta(seconds=1)) is True
    assert policy.loads_pre_forward(FORWARD_FLOOR) is False
    assert policy.loads_pre_forward(FORWARD_FLOOR + timedelta(days=30)) is False


def test_r1_the_measured_predicate_and_the_refusal_agree() -> None:
    policy = WarmupPolicy(w_bars=50, longest_feature_lookback_bars=50)
    pre_forward = FORWARD_FLOOR - timedelta(seconds=1)
    forward = FORWARD_FLOOR + timedelta(seconds=1)
    assert policy.loads_pre_forward(pre_forward) is True
    with pytest.raises(WarmupPolicyError, match="pre-forward load forbidden"):
        policy.assert_load_allowed(pre_forward)
    assert policy.loads_pre_forward(forward) is False
    assert policy.assert_load_allowed(forward) is None


def test_r1_an_unreadable_timestamp_is_not_answered_as_safe() -> None:
    policy = WarmupPolicy(w_bars=50, longest_feature_lookback_bars=50)
    naive = datetime(2026, 5, 1, 0, 0, 0)  # deliberately naive: must not be assumed UTC
    with pytest.raises(WarmupPolicyError, match="load timestamp rejected"):
        policy.loads_pre_forward(naive)
    with pytest.raises(WarmupPolicyError, match="load timestamp rejected"):
        policy.loads_pre_forward("2026-05-01T00:00:00")


def test_r1_an_undersized_policy_cannot_answer_the_predicate_either() -> None:
    with pytest.raises(WarmupPolicyError, match="warm-up too short"):
        WarmupPolicy(w_bars=10, longest_feature_lookback_bars=50).loads_pre_forward(
            datetime(2026, 5, 1, tzinfo=UTC)
        )


# ------------------------------------------------- B-7(b): package status constants

FORBIDDEN_LABELS = (
    "PASS",
    "Tier 1",
    "FORMALLY_VERIFIED",
    "PRODUCTION_READY",
    "READY_FOR_LIVE",
    "M15_AUTHORISED",
    "H1_AUTHORISED",
    "H2_STARTED",
    "PHASE_C2_STARTED",
    "NEW_EPOCH_ADOPTED",
    "BYTE_ADMISSIBLE",
    "MEETS",
    "ROBUST",
    "DEPLOYABLE",
)
STATUS_CONSTANTS = {
    "IMPLEMENTATION_STATUS": IMPLEMENTATION_STATUS,
    "PRODUCTION_STATUS": PRODUCTION_STATUS,
    "EXECUTION_STATUS": EXECUTION_STATUS,
    "FORWARD_EPOCH_STATUS": FORWARD_EPOCH_STATUS,
}


def _fold(text: str) -> str:
    """Casing- and separator-insensitive form, per playbook §10's near-synonym rule."""
    return "".join(ch for ch in text if ch.isalnum()).upper()


def test_b7b_status_constants_are_value_pinned() -> None:
    """No test in the repository referenced these; all three named mutants stayed green."""
    assert IMPLEMENTATION_STATUS == (
        "M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN"
    )
    assert PRODUCTION_STATUS == "PRODUCTION_READINESS_NOT_CLAIMED"
    assert EXECUTION_STATUS == "NO_EXECUTION_PERFORMED"
    assert FORWARD_EPOCH_STATUS == (
        "FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS"
    )


@pytest.mark.parametrize("name", sorted(STATUS_CONSTANTS))
def test_b7b_no_status_constant_carries_a_forbidden_label(name: str) -> None:
    folded = _fold(STATUS_CONSTANTS[name])
    for label in FORBIDDEN_LABELS:
        assert _fold(label) not in folded, f"{name} carries the forbidden label {label!r}"


@pytest.mark.parametrize(
    "mutation", ["PRODUCTION_READY", "EXECUTION_PERFORMED", "NEW_EPOCH_ADOPTED"]
)
def test_b7b_the_audited_mutations_are_not_the_committed_values(mutation: str) -> None:
    assert mutation not in set(STATUS_CONSTANTS.values())


def test_b7b_the_statuses_agree_with_the_governance_playbook() -> None:
    """The code's statuses and the playbook's carried/always-binding list are one thing."""
    playbook = (REPO_ROOT / "docs" / "governance" / "m15_audit_playbook.md").read_text(
        encoding="utf-8"
    )
    assert "## 1. Current gate state" in playbook  # non-vacuity floor
    for name, value in STATUS_CONSTANTS.items():
        assert value in playbook, f"{name} = {value!r} is not recorded in the playbook"
