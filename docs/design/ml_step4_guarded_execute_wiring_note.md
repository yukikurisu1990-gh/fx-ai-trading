# ML Step 4 guarded `execute()` wiring — implementation note (code-only, no run)

- **Document class:** short implementation note for a code-only, no-execution PR.
- **Branch:** `feat/ml-step4-guarded-execute-wiring-no-run`
- **Base:** master after PR #414 merge.
- **Bound contracts:** PR #407 pre-registration
  (`docs/design/phase_f_ml_step4_pre_registration.md`) + PR #408
  execution-authorisation, under the PR #413 falsification/baseline frame and
  the PR #414 re-check (`…_ACCEPTABLE_FOR_GUARDED_WIRING_REVIEW_AFTER_RECHECK`).

## Status

**`ML_STEP4_GUARDED_EXECUTE_WIRING_IMPLEMENTED_NO_RUN`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## What this PR adds

A single fail-closed orchestration layer (`scripts/ml_step4/executor.py` +
CLI `scripts/ml_step4/execute_365d_ba.py`) that assembles the reviewed
primitives into ONE intended route for a future, separately-authorised first
run, and binds the seven PR #411/#413/#414 wiring residuals. **Real execution
is refused in this build** — the training/evaluation body is intentionally
absent; `guarded_execute` fails closed on any non-dry-run call. Nothing here
reads real raw data, trains, evaluates the holdout, or writes execution evidence.

### Entry points
- `executor.guarded_execute(dry_run=True)` → execution plan + preflight (no side
  effects); `dry_run=False` or `allow_real_execution=True` → `ExecutionRefusedError`.
- `executor.run_preflight()` → hard-gate wiring report (16 gates) using inventory
  **metadata only** (file count + total bytes; **no checksums, no raw read**).
- `executor.build_execution_plan()` → full scrub-clean plan metadata.
- CLI: `python -m scripts.ml_step4.execute_365d_ba --preflight` (returns 0);
  `--execute` / no flag → refusal, exit 2. (`run_365d_ba.py --dry-run` unchanged.)

### Residual bindings
| Residual | Binding |
| --- | --- |
| **R-1** bar-granularity boundaries | `split.bar_index_split` — segments are M1 **bar indices** `[start, end)` (end-exclusive), purge/embargo = horizon+1 = 21 bars; `split.assert_m1_aligned` rejects non-`:00`/sub-second timestamps. Off-by-one and small-n cases fail closed. |
| **R-4** single-source label routing | `labels.label_contract_identity()` (`LABEL_CONTRACT_ID = scripts.ml_step4.labels.v1`) recorded in preflight/plan; the sanctioned scorer delegates to the committed `scripts.traded_direction_pnl.traded_direction_pnl_price` (no fork); no fallback route exists. |
| **R-5** trading-day definition | `contract.TRADING_DAY_DEFINITION = "utc_calendar_date"`; `metrics.trading_day_utc()` (UTC calendar date; naive datetime fails closed); coverage denominator = distinct UTC dates in holdout — recorded in the frozen contract. |
| **R-6** tie-rule provenance | `contract.THRESHOLD_TIE_RULE` recorded in `threshold_config()` (dedicated `threshold_config_hash`) **and** in `contract_dict()` (so `config_hash` covers it). |
| **seed/determinism** | `executor.reproducibility_policy()` — separate from the model contract (`alters_model_config_hash: False`); deterministic data ordering + fixed validation selection; runtime seeds/versions recorded; LightGBM residual nondeterminism declared `bounded_not_bitwise_guaranteed`. Does **not** add `random_state` to `_LGBM_PARAMS`. |
| **maxDD fixed-notional** | `contract.FIXED_NOTIONAL_EQUITY_PIPS = 10_000.0`; `maxDD% = peak_to_trough_pips / notional`; recorded in `contract_dict()["evaluation"]` (config-hash covered); missing/non-positive fails closed. |
| **NON_DECISION_EXPLORATORY** | `executor.label_diagnostics()` tags every diagnostic; `assert_diagnostics_labeled()` fails closed on unlabeled diagnostics or a decision metric mislabeled as exploratory; `assert_diagnostics_excluded_from_decision()` rejects any exploratory key that leaks into the acceptance criteria table. |

Because these bindings enter the frozen contract, `config_hash` and
`model_config_hash`/`threshold_config_hash` are recomputed — **safe: no run has
ever consumed any prior hash** (PR #409 stopped pre-training with null hashes).

## Preflight hard gates (no raw data read)

16 gates verified present without touching raw files: code SHA recordable;
config/feature/model/threshold hashes; tie-rule provenance; maxDD notional;
reproducibility policy; label-contract identity; evidence-dir policy; inventory
resolver + expected count/bytes (metadata only); split policy; metrics +
acceptance evaluators; evidence writer; diagnostic-labeling policy. Any missing
component → `PREFLIGHT_REFUSED_INCOMPLETE`.

## What remains for the future execution PR

The real guarded run body (raw read → causal v4-base features → bulk B-2 labels
via `labels.py` → from-scratch LightGBM train → validation-only threshold
selection → single event-driven holdout evaluation at bar-index boundaries →
daily-portfolio-Sharpe + the eight metadata-only evidence files with full F-5
provenance including the seeds/versions actually used) is intentionally NOT
implemented and NOT invokable here. It requires a separate, explicitly-
authorised execution PR, followed by the mandated post-run human + ChatGPT
review (recommended Fable 5 adversarial post-run audit) — under the PR #413
falsification/baseline-measurement frame (likely `DOES_NOT_MEET`; no
rerun-into-search).

## Non-authorisation

No ML Step 4 execution; no real raw data read; no model trained; no backtest;
no holdout evaluation; no real ML metrics; no real execution evidence; no model
binaries; no external disk / Google Drive / R2 access; no Phase C2; no
`730d_BA`; no `3650d_BA`; no production-readiness claim.
