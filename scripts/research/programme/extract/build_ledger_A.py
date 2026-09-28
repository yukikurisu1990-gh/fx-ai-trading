# ruff: noqa: E501 -- transcription
"""Ledger part A: M15 archive exploratory rounds (PR #464–#470). Transcribed by the lead session.

Each value was copied by hand from the results document or artifact named in `source`. Nothing
is recomputed. This era records per-pair pips over a panel and a bar-level `sharpe_like`, not an
annual return or a daily-book Sharpe, so the annual fields and `calendar_years` are null. The
engine's `sharpe_like` is kept in notes only: it is bar-level and not comparable to a daily-book Sharpe.
The extraction subagent for this part was refused permission to write or run its own builder;
this file is an independent transcription by the lead, not that script.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "artifacts/research/programme/parts/ledger_A.json"

KEYS = (
    "track_id", "cycle", "pr", "family", "hypothesis", "mechanism", "information_source",
    "price_only", "book_type", "span_label", "span_dates", "calendar_years", "effective_n",
    "event_count", "gross_annual_return", "gross_sharpe", "tc_adjusted_annual_return",
    "tc_adjusted_sharpe", "financing_included", "financing_type", "turnover", "annual_cost",
    "ic", "incremental_ic", "null_percentile", "p_value", "stability", "loo_worst",
    "concentration_top10", "max_dd", "result_status", "is_primary", "preregistered",
    "post_result_correction", "invalid", "variant_type", "variant_of",
    "protected_data_caveat", "closure_scope", "source", "notes",
)  # fmt: skip

DEV = "development 2025-04-25..2025-12-28"
OOS_CAVEAT = "HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN (R1 decoded one row past each window; 20 rows in the OOS slice). No OOS value used here"
PIPS = "units: pips per pair summed over the panel, cost x1.0 (spread/2 + 0.25 pip per side). sharpe_like is the engine's bar-level annualised figure, NOT comparable to a daily-book Sharpe"

ROWS = [
    {
        "track_id": "R1_textbook_rules",
        "cycle": "Exploratory Round 1",
        "pr": "#464",
        "family": "trend / breakout / oscillator",
        "hypothesis": "Textbook rules (EMA cross, Donchian, RSI) have an edge at M15",
        "mechanism": "price-pattern trading rules",
        "span_label": "development",
        "span_dates": "2025-04-25..2025-12-28",
        "result_status": "drop",
        "is_primary": True,
        "preregistered": False,
        "variant_type": "DISTINCT_MECHANISM",
        "source": "docs/research/m15_track_a_exploratory_round_1.md §4 research log #2",
        "notes": "net −708 to −1,532 pips/pair; cost 600–1,486 vs |gross| ≤ 148. Not pre-registered (open exploratory search). "
        + PIPS,
    },
    {
        "track_id": "R1_15_strategy_families",
        "cycle": "Exploratory Round 1",
        "pr": "#464",
        "family": "trend / breakout / reversion / MTF",
        "hypothesis": "Some family survives cost",
        "mechanism": "15 strategies across trend / breakout / reversion / multi-timeframe",
        "span_label": "development",
        "span_dates": "2025-04-25..2025-12-28",
        "result_status": "drop",
        "is_primary": True,
        "preregistered": False,
        "variant_type": "MODEL_VARIANT",
        "source": "docs/research/m15_track_a_exploratory_round_1.md §4 research log #3 and #6",
        "notes": "SUMMARY: all 15 negative, best −262 pips/pair; low-turnover selective reversal best −53 net (gross 61, cost 114), 9/20 pairs. Per-strategy corrected nets exist for only 3 of 15 (see extraction report). "
        + PIPS,
    },
    {
        "track_id": "R1_reversal_sweep_walkforward",
        "cycle": "Exploratory Round 1",
        "pr": "#464",
        "family": "reversal",
        "hypothesis": "A parameter cell of the reversal clears cost and would have been choosable in advance",
        "mechanism": "51-config (lookback, hold, z) reversal sweep; walk-forward tune on H1, test on H2",
        "span_label": "development",
        "span_dates": "2025-04-25..2025-12-28",
        "stability": "45/52 positive in H1, 2/52 in H2, rank corr −0.40",
        "result_status": "drop",
        "is_primary": True,
        "preregistered": False,
        "variant_type": "HORIZON_VARIANT",
        "source": "docs/research/m15_track_a_exploratory_round_1.md §3 and §4 research log #7–#8",
        "notes": "7 of 51 configs gross > cost full-sample (best +783 pooled); best-of-H1 → −3,712 on H2. Full-sample IC of the lead was a first-half artefact (−14.6% → −1.9% by quarter). "
        + PIPS,
    },
    {
        "track_id": "R2_reversal_family_primary",
        "cycle": "Exploratory Round 2",
        "pr": "#465",
        "family": "reversal",
        "hypothesis": "Multi-day reversal: 39-configuration pre-registered family; decision by family-max",
        "mechanism": "4-to-6 day cross-pair reversal, best cell lb480_h480_z1.0",
        "span_label": "development",
        "span_dates": "2025-04-25..2025-12-28",
        "selected_best_of_n": 39,
        "ic": -0.2507,
        "p_value": 0.053,
        "turnover": 51.7,
        "stability": "17/20 pairs net positive; 8 phases",
        "max_dd": -96.0,
        "result_status": "MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER",
        "is_primary": True,
        "preregistered": True,
        "variant_type": "DISTINCT_MECHANISM",
        "source": "docs/research/m15_track_a_exploratory_round_2_results.md §1; artifacts/track_a_scratch/exploratory_round_1/supplemental_primary_replication.json original.*",
        "notes": "sharpe_like 2.18 (selected cell, not comparable); gross +324.1, net +262.1 pips/pair, cost 62.0; turnover per year; max_dd in pips. p_value = family-wise p; 0.157 after dropping the best 3 of 212 days. Power under the pre-registered rule 0.29; +661 days for 80%. The reported cell is the best of 39 on the same data. "
        + PIPS,
    },
    {
        "track_id": "R2_reversal_JPY6_subfamily",
        "cycle": "Exploratory Round 2",
        "pr": "#465",
        "family": "reversal",
        "hypothesis": "JPY 6 pairs as their own family",
        "mechanism": "currency-subset of the Round 2 family",
        "span_label": "development",
        "span_dates": "2025-04-25..2025-12-28",
        "p_value": 0.025,
        "result_status": "MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER",
        "is_primary": False,
        "preregistered": False,
        "variant_type": "UNIVERSE_VARIANT",
        "variant_of": "R2_reversal_family_primary",
        "source": "docs/research/m15_track_a_exploratory_round_2_results.md §1 table",
        "notes": "currency-subset diagnostic; non-JPY 14 family-wise p 0.284",
    },
    {
        "track_id": "SUPP_reversal_replication",
        "cycle": "Supplemental historical replication",
        "pr": "#466",
        "family": "reversal",
        "hypothesis": "The frozen Round 2 candidate replicates on 2023-04-26..2025-04-24",
        "mechanism": "4-to-6 day reversal, lb480_h480_z1.0 frozen",
        "span_label": "supplemental",
        "span_dates": "2023-04-26..2025-04-24",
        "ic": 0.0235,
        "p_value": 0.9757,
        "turnover": 49.4,
        "stability": "1/20 pairs net positive; 16/20 gross negative; all 9 neighbourhood cells negative",
        "max_dd": -667.0,
        "result_status": "MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION",
        "is_primary": True,
        "preregistered": True,
        "variant_type": "REPLICATION",
        "variant_of": "R2_reversal_family_primary",
        "closure_scope": "reversal family dropped from active exploratory research (with the momentum round)",
        "source": "artifacts/track_a_scratch/exploratory_round_1/supplemental_primary_replication.json supplemental.*; docs/research/m15_track_a_supplemental_replication_results.md §4, §6",
        "notes": "sharpe_like −1.32 (not comparable); gross −426.5, net −577.3 pips/pair, cost 150.8. p_value = Round 2 family-max rule on the 9-cell family (best cell). Power vs pre-specified alternative +771.5: 0.759 (0.699 under family-max). Difference vs original −2.16 pips/pair/day, bootstrap p 0.0042. "
        + PIPS,
    },
    {
        "track_id": "MOM_B_momentum_mirror",
        "cycle": "Momentum hypothesis (fresh exploratory span)",
        "pr": "#467",
        "family": "momentum",
        "hypothesis": "The mirror (momentum) of the frozen reversal candidate pays on 2021-04-26..2023-04-25",
        "mechanism": "4-to-6 day momentum, lb480_h480_z1.0_momentum",
        "span_label": "momentum_2021_2023",
        "span_dates": "2021-04-26..2023-04-25",
        "ic": -0.0585,
        "p_value": 0.187,
        "turnover": 50.1,
        "stability": "5/20 pairs net positive; 2/20 positive IC (null 8.61, p 0.053)",
        "max_dd": -704.0,
        "result_status": "MULTI_DAY_MOMENTUM_UNRESOLVED_IN_FRESH_EXPLORATORY_HISTORY",
        "is_primary": True,
        "preregistered": True,
        "variant_type": "SIGN_VARIANT",
        "variant_of": "R2_reversal_family_primary",
        "closure_scope": "MULTI_DAY_REVERSAL_FAMILY_DROPPED_FROM_ACTIVE_EXPLORATORY_RESEARCH",
        "source": "artifacts/track_a_scratch/exploratory_round_1/momentum_b_primary.json all_20.*; momentum_b_inference.json ic_null; docs/research/m15_track_a_momentum_hypothesis_results.md §1",
        "notes": "sharpe_like −0.97 (not comparable); gross −299.0, net −451.4 pips/pair (95% CI [−1,128.3, +217.4]), cost 152.4. IC p 0.233. Power vs the motivating alternative 0.124. Inversion was motivated by the supplemental result (post-hoc hypothesis, pre-registered before this span was read). "
        + PIPS,
    },
    {
        "track_id": "MOM_B_reversal_same_span",
        "cycle": "Momentum hypothesis (fresh exploratory span)",
        "pr": "#467",
        "family": "reversal",
        "hypothesis": "Reversal direction on the same span (diagnostic)",
        "mechanism": "mirror of MOM_B_momentum_mirror",
        "span_label": "momentum_2021_2023",
        "span_dates": "2021-04-26..2023-04-25",
        "p_value": 0.667,
        "result_status": "diagnostic",
        "is_primary": False,
        "preregistered": True,
        "variant_type": "SIGN_VARIANT",
        "variant_of": "MOM_B_momentum_mirror",
        "source": "docs/research/m15_track_a_momentum_hypothesis_results.md §1 table; momentum_b_primary.json mirror_check",
        "notes": "net +146.7, gross +299.0 pips/pair. net_momentum + net_reversal ≡ −2 × cost: one measurement, not two",
    },
    {
        "track_id": "ROUNDA_T2_conditional_screen",
        "cycle": "Round A",
        "pr": "#468",
        "family": "conditional reversal / regime conditioning",
        "hypothesis": "Conditioning stabilises the sign of the multi-day signal (39 pre-registered cells, six-condition structural screen)",
        "mechanism": "regime-conditioned drift cells",
        "span_label": "three panels",
        "span_dates": "2021-04-26..2023-04-25; 2023-04-26..2025-04-24; 2025-04-25..2025-12-28",
        "result_status": "TRACK_A_RESEARCH_PROGRAM_ROUND_A_COMPLETED (Case B)",
        "is_primary": True,
        "preregistered": True,
        "variant_type": "MODEL_VARIANT",
        "source": "docs/research/m15_round_a_results.md §1",
        "notes": "0 of 39 cells pass under the registered reading; screen false-positive rate on noise 0.2268 (null mean 0.31 cells). Cells are gross drift, not net P&L. First draft said Case A; withdrawn",
    },
    {
        "track_id": "ROUNDBP_B1_variance_ratio",
        "cycle": "Round B′",
        "pr": "#469",
        "family": "price-path structure (non-economic)",
        "hypothesis": "Serial structure in the M15 price path that no matched null reproduces (VR(q) < 1)",
        "mechanism": "variance ratio, 7 horizons, Westfall–Young family-max",
        "span_label": "three panels",
        "span_dates": "2021-04-26..2023-04-25; 2023-04-26..2025-04-24; 2025-04-25..2025-12-28",
        "p_value": 0.005,
        "result_status": "PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL (Case A)",
        "is_primary": True,
        "preregistered": True,
        "variant_type": "DISTINCT_MECHANISM",
        "source": "docs/research/m15_round_b_prime_results.md §1",
        "notes": "STATISTICAL STRUCTURE, NOT A TRADING RESULT. p 0.005 = floor for 200 draws, all three panels; studentized −14.7. Best linear rule from it reaches 6–16% of a round-trip cost (in-sample)",
    },
    {
        "track_id": "MONETIZ_B3_selector",
        "cycle": "Monetizability package",
        "pr": "#470",
        "family": "price-path structure harvesting",
        "hypothesis": "The Round B′ structure is monetizable by a linear selector on fixed features",
        "mechanism": "one linear selector on eight fixed features, seven event populations",
        "span_label": "three panels",
        "span_dates": "2021-04-26..2023-04-25; 2023-04-26..2025-04-24; 2025-04-25..2025-12-28",
        "result_status": "PRICE_PATH_STRUCTURE_REAL_BUT_NOT_ECONOMICALLY_HARVESTABLE (Case B)",
        "is_primary": True,
        "preregistered": True,
        "variant_type": "DISTINCT_MECHANISM",
        "variant_of": "ROUNDBP_B1_variance_ratio",
        "closure_scope": "selection and direction questions closed on seven populations, for one linear selector on eight fixed features",
        "source": "docs/research/m15_monetizability_results.md §1",
        "notes": "B-3 excess over matched null −0.68 to +2.39 round trips per opportunity vs floor 0.50; the one population clearing it has z ≈ 0.9 on 6–9 events/pair/yr. Economic gate amended before the first real statistic because noise passed it. Stage 2 not begun",
    },
]

DEFAULTS = {
    "price_only": True,
    "book_type": "PAIR_LEVEL",
    "information_source": "FX prices only (OANDA M15 derived from M1 archive)",
    "financing_included": "NONE",
    "financing_type": "none (carry/swap not accounted)",
    "post_result_correction": False,
    "invalid": False,
    "protected_data_caveat": OOS_CAVEAT,
}


def build() -> list[dict]:
    out = []
    for spec in ROWS:
        row = {k: None for k in KEYS}
        row.update(DEFAULTS)
        row.update(spec)
        assert set(KEYS) <= set(row), set(KEYS) - set(row)
        out.append(row)
    ids = [r["track_id"] for r in out]
    assert len(ids) == len(set(ids))
    return out


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(OUT, len(ROWS))
