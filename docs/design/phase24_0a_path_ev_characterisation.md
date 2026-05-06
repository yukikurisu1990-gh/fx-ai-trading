# Stage 24.0a — Path-EV Characterisation + Frozen Entry Stream Selection

**Date**: 2026-05-06
**Predecessor (kickoff)**: `docs/design/phase24_design_kickoff.md`
**Phase 23 closing reference (read-only)**: `docs/design/phase23_final_synthesis.md`
**Phase 23 stage references (read-only)**:
- `docs/design/phase23_0a_outcome_dataset.md`
- `docs/design/phase23_0b_m5_donchian_baseline.md`
- `docs/design/phase23_0c_m5_zscore_mr_baseline.md`
- `docs/design/phase23_0d_m15_donchian_baseline.md`
- `docs/design/phase23_0c_rev1_signal_quality.md`

This stage is FOUNDATIONAL for Phase 24 — it produces no strategy verdict
on its own. 24.0a evaluates the 216 Phase 23 cells (23.0b 18 + 23.0c 36 +
23.0d 18 + 23.0c-rev1 144) on path-EV statistics, applies the multi-axis
ranking + halt criteria pre-declared here, and emits a small JSON of
the top-K=3 frozen entry streams that 24.0b/c/d/e import verbatim.

---

## §1 Scope and constraints

### In scope
- Re-enumerate all 216 Phase 23 cells using the existing Phase 23 signal
  generators (no parameter re-search; pure replay)
- Compute path-EV statistics and 5-axis multi-metric ranking per cell on
  the 23.0a M5 + M15 outcome datasets (read-only)
- Apply pre-declared eligibility constraints (§4) and halt criteria (§5)
- Emit `frozen_entry_streams.json` with top-K=3 cells for 24.0b/c/d/e
- Emit `path_ev_characterisation_report.md` with full per-cell ranking

### Explicitly out of scope
- Any strategy adoption / production migration: 24.0a is foundational
- Exit-side simulation: that is 24.0b/c/d
- New cell generation outside the 216 Phase 23 cells
- Re-fitting 23.0a outcome columns (read-only context)
- Search over the score formula / weights / K — fixed in this PR before
  implementation

### Hard constraints (mirroring Phase 24 kickoff §13)
- `src/` not touched
- `scripts/run_*.py` not touched
- DB schema not touched
- Existing 22.x / 23.x / 24 kickoff docs / artifacts not modified
- 20-pair canonical universe; no pair / time-of-day filter
- `signal_timeframe ∈ {M5, M15}` runtime assertion carried forward
- **Score formula and K are FIXED in this PR**; 24.0b/c/d/e import the
  emitted JSON with no override

---

## §2 Inputs

- **23.0a outcome parquets** (read-only): `artifacts/stage23_0a/labels_M5/labels_M5_<pair>.parquet` and `labels_M15/labels_M15_<pair>.parquet` for the 20 canonical pairs
- **Phase 23 signal generators** (imported from existing modules):
  - `stage23_0b.extract_signals(m5_df, n)` — continuous Donchian on M5
  - `stage23_0c.extract_signals_first_touch(m5_df, n, threshold)` — first-touch z-MR on M5
  - `stage23_0d.extract_signals_first_touch_donchian(m15_df, n)` — first-touch Donchian on M15
  - `stage23_0c_rev1._signals_f1_neutral_reset(z, threshold, neutral_band)` — F1
  - `stage23_0c_rev1._signals_f2_cooldown(...)` — F2 (post-filter on first-touch)
  - `stage23_0c_rev1._signals_f3_reversal(z, mid_c, threshold, neutral_band)` — F3
  - `stage23_0c_rev1._signals_first_touch(z, threshold)` — F4 base (cost_gate post-join)
- **Phase 23 cell catalogues** (enumerated programmatically; total 216 cells):
  - 23.0b: 18 cells = N {10, 20, 50} × horizon {1, 2, 3} × exit {tb, time}
  - 23.0c: 36 cells = N {12, 24, 48} × threshold {2.0, 2.5} × horizon {1, 2, 3} × exit {tb, time}
  - 23.0d: 18 cells = N {10, 20, 50} × horizon {1, 2, 4} × exit {tb, time}
  - 23.0c-rev1: 144 cells = filter {F1, F2, F3, F4} × N {12, 24, 48} × threshold {2.0, 2.5} × horizon {1, 2, 3} × exit {tb, time}

---

## §3 Score formula (FIXED in this PR)

```
SCORE(cell) = 1.0 * mean(best_possible_pnl)         # axis 1 — primary path-EV magnitude
            + 0.3 * realised_gap                     # axis 2 — improvement potential (auxiliary)
            - 0.5 * mean(|mae_after_cost|)           # axis 3 — adverse-path penalty (strong)
```

Where:
- `mean(best_possible_pnl)` is computed across `valid_label = True` rows in the joined trades, in pips
- `realised_gap = mean(best_possible_pnl) - mean(max(tb_pnl, time_exit_pnl))` — the upside left on the table by the better of the two realistic exits, in pips
- `mean(|mae_after_cost|)` is the absolute value of the mean adverse-path excursion in pips (always ≥ 0; subtracting from the score penalises large excursions)

### Weight rationale (audit trail)

- **Axis 1 (1.0)** is primary: a positive `mean(best_possible_pnl)` is the
  necessary condition for any exit-side improvement to have headroom.
- **Axis 2 (0.3)** is auxiliary, deliberately weaker than axis 1: a large
  `realised_gap` could come from `mean(best_possible_pnl)` being modestly
  positive while realised is catastrophically negative — that is *not* a
  good candidate (the realised distribution drags the entry stream down).
  The axis-1 dominance discourages cells whose only merit is "huge gap".
- **Axis 3 (-0.5)** is strong: adverse path excursions are risk that
  exit logic alone cannot fully save — even an aggressive trailing stop
  has to absorb the path's downside before any trail point. Penalising
  high `mean(|mae|)` discourages cells that would force exit logic to
  sit on large drawdowns.

### Tie-breaker

If two cells have equal SCORE within `1e-9`, the lower
`mean(|mae_after_cost|)` wins (less risky path).

### NOT in score (diagnostic only)

- `p75(best_possible_pnl)` — reported in `metrics` but not used in SCORE.
  It IS used in eligibility (§4).
- `worst_possible_pnl` quantiles — reported but not in SCORE.
- `median(best_possible_pnl)` — reported but not in SCORE.
- `positive_rate(best_possible_pnl > 0)` — reported, used in eligibility (§4).

### K (top-K)

**K = 3.** Fixed. Smaller K keeps 24.0b/c/d evaluation tractable (3
frozen streams × per-stage variants is already a substantial sweep).
24.0a does NOT promote K beyond 3 even if more than 3 cells are
eligible.

---

## §4 Eligibility constraints (FIXED in this PR)

A cell is ELIGIBLE for ranking if and only if ALL six conditions hold:

```
ELIGIBLE(cell) =
    annual_trades >= 70              # axis 4 sample sufficiency (Phase 22 A0)
  AND max_pair_share <= 0.5            # axis 5 per-pair concentration
  AND min_fold_share >= 0.10           # axis 5 per-fold concentration
  AND mean(best_possible_pnl) > 0      # H1.2 path-EV mean
  AND p75(best_possible_pnl) > 0       # H1.3 path-EV upper-quartile
  AND positive_rate(best_possible_pnl > 0) >= 0.55   # H1.4 upside availability
```

The last three conditions encode the kickoff §7 H1 halt criteria
**directly into eligibility** (per user spec): cells failing H1 are
excluded from top-K, not just from halt-avoidance.

### Constraint definitions

- `annual_trades = n_valid_trades / span_years` where
  `span_years = 730 / 365.25 ≈ 1.9986`
- `max_pair_share = max(pair_count) / total_count` over all 20 pairs;
  cells where any single pair contributes > 50% of trades are excluded
- `min_fold_share`: split valid trades chronologically by `entry_ts` into
  5 quintiles, drop k=0 (warmup, Phase 22/23 convention), evaluate
  k=1..4. Compute the per-fold count divided by the total k=1..4 count.
  Require all 4 fold shares ≥ 10% (so no single fold has < 10% of the
  evaluation trades).
- `positive_rate(best_possible_pnl > 0)`: fraction of valid trades with
  `best_possible_pnl > 0`. The 0.55 threshold is "materially above
  50%" per kickoff §7 — 5 percentage points above the coin-toss baseline,
  comfortably outside the typical noise band on ~70k-trade samples.

### Halt logic

```
halt_triggered = (count(ELIGIBLE cells) == 0)
```

Phase 24 closes early if halt_triggered. Otherwise, the top-K=3 ELIGIBLE
cells (sorted by SCORE descending) are emitted as the frozen entry
streams.

---

## §5 Algorithm (per-cell evaluation)

```
1. Per-pair preload (one-time):
   - Load M1 BA candles (730d)
   - Aggregate to M5 and M15 (right-closed/right-labeled)
   - Compute mid_c on M5 (for F3 reversal) and mid_h/mid_l/mid_c
   - Compute z arrays per N ∈ {12, 24, 48} on M5 (for 23.0c, F1, F2, F3, F4)
   - Load 23.0a M5 and M15 outcome parquets (filtered to valid_label = True)

2. For each of the 216 cells:
   a. Re-generate signals via parent module's signal function
      (dispatch on source_stage + filter)
   b. Pool across 20 pairs
   c. Inner-join to 23.0a outcome (on entry_ts, pair, direction; filter
      by horizon_bars matching the cell)
   d. Verify NG#6: assert all rows have signal_timeframe matching the
      cell's signal_timeframe
   e. (For 23.0c-rev1 F4 cells: apply cost_gate post-filter
      cost_ratio <= 0.6)
   f. Compute path-EV metrics and concentration metrics on the joined
      trade table
   g. Apply ELIGIBLE(cell) check
   h. Compute SCORE(cell) if eligible; else SCORE = -inf

3. Halt check:
   if no cell is ELIGIBLE:
     halt_triggered = True
     frozen_cells = []
   else:
     halt_triggered = False
     frozen_cells = sorted(eligible cells, by SCORE descending)[0:K]

4. Emit:
   - frozen_entry_streams.json (per §6 schema)
   - path_ev_characterisation_report.md (per §7 structure)
   - path_ev_distribution.parquet (per-cell raw metrics; gitignored)
   - run.log (build log via tee; committed)
```

### Caching

Per pair, signal generation is cached per `(signal_TF, N, threshold,
filter_variant)`:
- 23.0b continuous Donchian on M5 per N: 3 generations × 20 pairs = 60
- 23.0c first-touch z-MR on M5 per (N, threshold): 6 × 20 = 120 (also
  used as F4 base, no extra generation)
- 23.0d first-touch Donchian on M15 per N: 3 × 20 = 60
- 23.0c-rev1 F1 neutral_reset per (N, threshold): 6 × 20 = 120
- 23.0c-rev1 F2 cooldown: derived from first-touch base via post-filter
  (no extra generation)
- 23.0c-rev1 F3 reversal per (N, threshold): 6 × 20 = 120
- 23.0c-rev1 F4 cost_gate: same as first-touch base (no extra
  generation; cost_gate applies post-join)

Total: 60 + 120 + 60 + 120 + 120 = 480 signal generations across 20
pairs. Estimated runtime ~10-15 min total (signal generation + joins +
metrics).

---

## §6 frozen_entry_streams.json schema

```json
{
  "version": "24.0a-1",
  "generated_at": "<ISO-8601 UTC>",
  "halt_triggered": false,
  "halt_criteria": {
    "annual_trades_min": 70,
    "mean_best_pnl_min": 0,
    "p75_best_pnl_min": 0,
    "positive_rate_min": 0.55
  },
  "eligibility_criteria": {
    "annual_trades_min": 70,
    "max_pair_share_max": 0.5,
    "min_fold_share_min": 0.10,
    "mean_best_possible_pnl_min": 0,
    "p75_best_possible_pnl_min": 0,
    "positive_rate_best_pnl_min": 0.55
  },
  "score_formula": {
    "axis_1_weight_mean_best_possible_pnl": 1.0,
    "axis_2_weight_realised_gap": 0.3,
    "axis_3_weight_mean_abs_mae_after_cost": -0.5,
    "tiebreaker": "lower mean |mae_after_cost|",
    "p75_in_score": false,
    "p75_in_diagnostic_only": true
  },
  "K": 3,
  "n_eligible_cells": <int>,
  "n_total_cells": 216,
  "frozen_cells": [
    {
      "rank": 1,
      "source_stage": "23.0b",
      "source_pr": 264,
      "source_merge_commit": "8d58c42",
      "source_verdict": "REJECT",
      "reject_reason": "overtrading",
      "signal_timeframe": "M5",
      "filter": null,
      "cell_params": {"N": 50, "horizon_bars": 3, "exit_rule": "time"},
      "score": 6.84,
      "metrics": {
        "annual_trades": 105275.1,
        "mean_best_possible_pnl": 4.23,
        "median_best_possible_pnl": 2.15,
        "p75_best_possible_pnl": 5.82,
        "positive_rate_best_pnl": 0.58,
        "realised_gap": 6.91,
        "mean_abs_mae_after_cost": 2.85,
        "worst_possible_pnl_p10": -8.4,
        "max_pair_share": 0.063,
        "min_fold_share": 0.21
      }
    },
    ... up to K=3 cells
  ]
}
```

24.0b/c/d/e import this JSON and consume `frozen_cells` directly. They
must NOT override the score formula, K, or eligibility criteria — those
are sealed by 24.0a's commit hash.

If `halt_triggered = True`, `frozen_cells = []` and Phase 24 closes
early with a closure synthesis (24.0f short form).

---

## §7 path_ev_characterisation_report.md structure

The committed report (analogous to Phase 23 stage eval reports) must
include:

1. **Verdict header**: `halt_triggered` boolean, n_eligible / n_total,
   K, top-3 cell summary (source / cell_params / score / key metrics)
2. **Mandatory caveat block** (verbatim text, per user spec):

   > **best_possible_pnl is an ex-post path diagnostic, not an executable
   > PnL. Frozen entry streams are selected for exit-study eligibility
   > only, not for production. Path-EV magnitude indicates path-side
   > upside availability that exit-side improvements may attempt to
   > capture; it does NOT guarantee that any exit logic will succeed in
   > converting that path-EV into realised PnL.**

3. **positive_rate clarification** (verbatim text, per user spec):

   > **positive_rate(best_possible_pnl > 0) is path-side upside
   > availability rate, NOT trade win rate. A trade with
   > best_possible_pnl > 0 means the price moved in the favourable
   > direction at some point during the holding window after entry-side
   > spread; whether the trade closed positive depends on the exit logic
   > (which is the entire question Phase 24 is investigating).**

4. **Score formula and weights** — full §3 reproduced
5. **Eligibility constraints** — full §4 reproduced with violation
   counts (e.g., "X cells failed annual_trades; Y cells failed pair
   concentration; ...")
6. **Top-K=3 deep dive**: per-cell metrics, source stage attribution,
   path-EV histogram summary
7. **All 216 cells ranked**: full table sorted by SCORE descending,
   with eligibility indicators and source attribution. ELIGIBLE cells
   ranked above non-eligible (which all have SCORE = -inf and are
   sorted by metrics for readability).
8. **Per-stage summary**: how many cells from each Phase 23 stage
   passed eligibility / made top-K
9. **Phase 24 forward routing**: if halt_triggered, declare Phase 24
   closes early; else, declare 24.0b/c/d will use the frozen JSON

---

## §8 NG list compliance (Phase 23 + Phase 24)

| NG | how 24.0a complies |
|---|---|
| 1 | 20-pair canonical, no pair filter |
| 2 | No train-side time filter |
| 3 | No test-side filter improvement claim (24.0a is foundational) |
| 4 | No WeekOpen weighting |
| 5 | No universe-restricted cross-pair feature |
| 6 | M5/M15 signal_TF only; runtime assertion `signal_timeframe ∈ {M5, M15}` carried forward |
| 7 | n/a |
| 8 | 23.0a M5/M15 outcome dataset is sole PnL source; 22.0a M1 read-only context |
| 9 | each frozen cell records source_stage, source_pr, source_merge_commit, source_verdict, reject_reason — honest entry-status reporting |
| 10 | n/a (24.0a is path-EV characterisation only — no exit decisions, no causality issues) |
| 11 | n/a (24.0a is regime-blind — no regime conditioning at this stage) |

---

## §9 Mandatory unit tests (≥ 14 cases)

| # | name | what it verifies |
|---|---|---|
| 1 | `test_score_formula_constants_fixed` | weights (1.0, 0.3, -0.5), K=3, NEUTRAL_BAND/COOLDOWN_BARS/COST_GATE_THRESHOLD, positive_rate threshold 0.55 are module constants; no CLI overrides |
| 2 | `test_eligibility_excludes_low_trade_count` | annual_trades < 70 → ELIGIBLE = False |
| 3 | `test_eligibility_excludes_pair_concentration` | max_pair_share > 0.5 → ELIGIBLE = False |
| 4 | `test_eligibility_excludes_fold_concentration` | min_fold_share < 0.10 → ELIGIBLE = False |
| 5 | `test_eligibility_excludes_negative_mean_path_ev` | mean(best_possible_pnl) ≤ 0 → ELIGIBLE = False |
| 6 | `test_eligibility_excludes_negative_p75_path_ev` | p75(best_possible_pnl) ≤ 0 → ELIGIBLE = False |
| 7 | `test_eligibility_excludes_low_positive_rate` | positive_rate < 0.55 → ELIGIBLE = False |
| 8 | `test_score_axis1_dominates` | with axis 2 and 3 contributions equal, doubling axis 1 input doubles score (modulo other terms) |
| 9 | `test_score_axis3_penalises_adverse_path` | higher mean(|mae|) → lower score |
| 10 | `test_p75_not_in_score` | varying p75 alone (with all other inputs fixed) does not change SCORE |
| 11 | `test_halt_triggers_when_no_cell_eligible` | synthetic catalogue with 0 eligible cells → halt_triggered=True, frozen_cells=[] |
| 12 | `test_top_k_returns_at_most_K` | with > K=3 eligible cells → exactly 3 frozen cells |
| 13 | `test_top_k_returns_fewer_when_eligible_count_lt_K` | 2 eligible cells → 2 frozen cells (not padded) |
| 14 | `test_phase23_cell_enumeration_total_216` | enumerate produces 216 cells = 18 + 36 + 18 + 144 |
| 15 | `test_signal_generators_imported_from_phase23_modules` | module imports `stage23_0b/c/d/c_rev1`; uses public signal functions |
| 16 | `test_frozen_entry_streams_json_includes_required_fields` | per-cell record has source_stage, source_pr, source_merge_commit, source_verdict, reject_reason, signal_timeframe, cell_params, filter, score, metrics |
| 17 | `test_smoke_mode_3pairs_3cells_from_23_0b` | --smoke runs 3 pairs × 3 cells (23.0b only) without error |
| 18 | `test_no_phase23_artifacts_modified` | 23.0a parquets and stage23_0b/c/d/c_rev1 source files unchanged after run |

---

## §10 CLI contract

```bash
python scripts/stage24_0a_path_ev_characterisation.py [--smoke]
```

Smoke: 3 pairs (USD_JPY, EUR_USD, GBP_JPY) × 3 cells from 23.0b only.

---

## §11 Effort estimate

| item | hours |
|---|---|
| Cell enumeration across 4 Phase 23 stages | 1-2 |
| Multi-metric ranking + score formula + eligibility + halt | 2-3 |
| Frozen entry stream JSON output | 0.5 |
| Per-cell metrics computation (concentration / quintile fold splitting) | 1-2 |
| Tests (≥ 14, target 16-18) | 2-3 |
| Report drafting (with caveats, role of axis weights, etc.) | 1-2 |
| Full eval run on 216 cells × 20 pairs (~10-15 min) | included |
| **Total** | **8-13** |

---

## §12 Document role boundary

This file is the stage contract for 24.0a — foundational stage that
produces no strategy verdict on its own. Per-cell results go to
`artifacts/stage24_0a/path_ev_characterisation_report.md`; the top-K=3
frozen entry streams (the actionable output) go to
`artifacts/stage24_0a/frozen_entry_streams.json`.

24.0b/c/d/e import the frozen JSON verbatim. The score formula, K,
eligibility criteria, and halt criteria are sealed by this 24.0a PR's
commit hash — downstream stages must NOT override or re-search them.

If a contradiction arises between this doc and the Phase 24 kickoff,
the kickoff wins.
