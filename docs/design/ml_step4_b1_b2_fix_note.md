# ML Step 4 B-1 / B-2 first-run source-blocker fixes — note (code-only, no run)

- **Document class:** short implementation note for a code-only, no-run fix PR.
- **Branch:** `fix/ml-step4-b1-b2-first-run-source-blockers`
- **Base:** master after PR #418 merge.
- **Fixes:** the two blockers proven in the PR #418 full source audit
  (`docs/design/ml_step4_first_run_full_source_audit_fable5.md`) + the PR #418
  mandatory additional tests.

## Status

**`ML_STEP4_FULL_SOURCE_BLOCKERS_B1_B2_FIXED_NO_RUN`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## B-1 — cost cell applied exactly once (`body.py`)

> The metrics layer (`metrics.compute_all`) already applied the cell exactly
> once and is unchanged; the double charge lived entirely in `body.py`'s signal
> layer + the inconsistent validation series, which is where the fix is.

**Before:** `_predictions_to_signals` subtracted the flat cost cell from each
signal, and `metrics.compute_all` subtracted it again — a raw +2.0-pip trade
became expectancy 1.0 at the "0.5 cell"; sensitivity cells were shifted +0.5;
validation (single charge via signals, 0.0 in the daily series) and holdout
(double charge) were inconsistent.

**Fix (single-responsibility):**
- `_predictions_to_signals` now emits **raw** traded-direction PnL (spread still
  embedded once by the B-2 ask-entry/bid-exit geometry; no flat cell). Its
  `cell_pips` parameter is removed. `MetricTrade.gross_pnl_pips` is now
  genuinely gross.
- The **metrics layer is the single place** the flat cell is applied, exactly
  once (`compute_all` at the primary cell + cost sensitivity at 0.0/0.5/1.0).
- Validation now charges the **same primary cell** as the holdout
  (`daily_portfolio_pnl(trades, cell_pips)` instead of `0.0`) — consistent
  charging across both segments.
- Evidence gains an explicit `cost_convention` block in the metrics and
  cost-sensitivity reports (`flat_cost_cell: applied_exactly_once_by_metrics_layer`,
  `signal_pnl: raw_gross_of_flat_cell`, `double_charge: false`).

Verified by value-pinned tests: raw +2.0 → expectancy 1.5 @0.5, 1.0 @1.0;
sensitivity cells 2.0/1.5/1.0 (not shifted); validation daily PnL == holdout
expectancy; old double-charge value unreachable. No change to PR #407/#408
acceptance criteria, threshold candidates, label/model contracts, or the
evidence schema (only additive `cost_convention` metadata).

## B-2 — label eligibility aligned to the committed convention (`labels.py`)

**Before:** `bulk_labels` skipped when `i + horizon >= n` (last labeled index
`n − horizon − 1`), one bar past the committed trainer/v9 convention
`range(n − horizon − 1)` (last index `n − horizon − 2`).

**Fix:** skip when `i + horizon + 1 >= n` — last eligible decision bar is now
exactly `n − horizon − 2`, matching the committed convention. Horizon stays 20;
bid/ask geometry, SL-first tie, timeout MTM, and F-2 traded-direction replay
are unchanged. Training labels and holdout trade scoring therefore share
identical eligible decision bars. **No new range convention was pre-registered**
— this is pure alignment to the existing committed one.

Verified: last eligible index `n − horizon − 2` (=178 at n=200; =278 at n=300);
no trailing bar lacking a full future horizon is labeled; boundary cases
`n ∈ {horizon, +1, +2}` correct (ATR warmup keeps very small n unlabeled).

## PR #418 mandatory additional tests (all added)

1. **Numeric ATR cross-check** — `labels.atr14` matches a hand-computed
   mid-true-range SMA-14 (`min_periods=14`) element-by-element.
2. **Import-graph legacy-non-use** — every `scripts/ml_step4/*.py` imports only
   sanctioned externals (F-2 helper, foundation_t2 scrub constants, the trainer
   feature-builder module via the lazy seam) + stdlib/third-party/relative; no
   `compare_multipair`/`stage*`/`model_store`/`lgbm_strategy`/`retrain`/paper/
   live/`fetch_oanda` import; no `src.`/`fx_ai_trading` serving import. The
   test's AST helper was verified to actually catch a planted legacy import.
3. **NaN/inf finiteness** — a NaN or ±inf decision metric now fails closed
   (`ML_STEP4_RUN_INVALID_PROVENANCE_MISSING`), never MEETS
   (`acceptance.non_finite_required_metrics`).
4. **Old optimistic PnL route** cannot be imported/used by the path.
5. **Deployed-model reuse** remains impossible (no `model_path` parameter; no
   joblib/pickle load in the package).

## Scope / non-authorisation

Touches only `scripts/ml_step4/{body,labels,acceptance}.py` +
`tests/ml_step4/` + this note + a roadmap pointer. No real mode; no execution;
no real `365d_BA` read; no real training/backtest/holdout/metrics/evidence; no
model binaries; no external disk / Google Drive / R2; no Phase C2; no
`730d_BA`/`3650d_BA`; no production-readiness claim.

## Remaining first-run gaps (unchanged; execution PR)

Checksum-verified `365d_BA` provider; production v4 bulk feature wiring
(builders only); minimal real-mode enablement + real evidence write.

## Next gate

Short Fable 5 re-check of these B-1/B-2 fixes → then the separately-authorised
first-run execution PR (no contract changes; execute exactly once; metadata-only
evidence; mandatory post-run review) under the PR #413 falsification/baseline
frame.
