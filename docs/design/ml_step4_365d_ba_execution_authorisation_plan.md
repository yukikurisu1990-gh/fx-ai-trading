# ML Step 4 — `365d_BA` execution-authorisation / execution plan

- **Document class:** doc-only execution-authorisation / execution-plan record
  (prepares the final gate; authorises no execution by itself)
- **Base:** master `b7d8cdc` (post PR #407 merge)
- **Branch:** `docs/ml-step4-execution-authorisation-plan`
- **Bound contract:** PR #407 pre-registration
  (`docs/design/phase_f_ml_step4_pre_registration.md`,
  `PHASE_F_ML_STEP4_PRE_REGISTRATION_CREATED`).
- **Bound epoch:** `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1` (Phase E, PR #406).

## Status

**`ML_STEP4_365D_BA_EXECUTION_AUTHORISATION_PLAN_CREATED`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: this record does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `BYTE_ADMISSIBILITY_APPROVED`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; those tokens
appear only as prohibitions.

## 1. Executive decision

- This is a **doc-only execution-authorisation / execution-plan record**.
- **It authorises no execution by itself.**
- It prepares the **final gate** for running exactly the PR #407 pre-registered
  ML Step 4 contract against `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`
  (`365d_BA`, 20 files, 1,481,715,517 bytes, evidence basis through PR #407).
- Any future execution must **either run the contract exactly or stop.**
- This PR does **not** train a model or run a backtest.

## 2. Bound pre-registration contract (PR #407 summary)

- epoch ID: `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`;
- model family: **LightGBM 3-class classifier** (single family);
- **B-2 bid/ask triple-barrier labels** (TP 1.5×/SL 1.0× ATR14 `min_periods=14`,
  SL-first strict `<`);
- horizon: **20 M1 bars**;
- **`FEATURE_VERSION v4` base only** (opt-in groups excluded);
- **retrain from scratch**; **no deployed `models/lgbm/` reuse**;
- **no broad hyperparameter search** (frozen `_LGBM_PARAMS` / `_N_ESTIMATORS`);
- threshold set: **`{0.35, 0.40, 0.45}`**, **validation-only** selection;
- **frozen holdout evaluated exactly once**;
- **primary metric: daily portfolio Sharpe** (annualised) on the holdout at the
  0.5 pip cell;
- **metadata-only reporting** under `artifacts/ml_step4/365d_ba_v1/`.

## 3. Pre-execution hard gates

A future execution must **stop before reading raw data or training** if any of
these fail:

- working tree not clean;
- current code SHA not recorded;
- config hash cannot be generated;
- epoch inventory cannot be resolved;
- all 20 file SHA-256 + sizes are not re-verified against the PR-B.1 inventory
  immediately before execution;
- train/validation/test split cannot be reproduced deterministically;
- F-2 / F-5 / F-8 contracts cannot be enforced;
- dependency/package metadata cannot be recorded safely;
- the evidence output directory is not clean or cannot be created safely;
- any personal paths, environment dumps, credentials, or raw data would be
  committed;
- any attempt is made to touch `730d_BA`, `3650d_BA`, Phase C2, Google Drive, or
  R2.

## 4. Execution scope for the future run

**Allowed:**
- read `365d_BA` raw data locally **for the sole purpose of executing PR #407**;
- re-verify checksums immediately before use;
- compute features under the pre-registered `FEATURE_VERSION v4` base set;
- train the LightGBM model family **from scratch** on the training window;
- choose threshold **on validation only** from `{0.35, 0.40, 0.45}`;
- evaluate the frozen holdout **exactly once**;
- generate **metadata-only** evidence under `artifacts/ml_step4/365d_ba_v1/`.

**Forbidden:**
- train on holdout; tune threshold on holdout;
- run extra model families; run broad hyperparameter search;
- add pair/session filters;
- reuse deployed `models/lgbm/`;
- write model binaries unless separately approved;
- commit raw data; commit personal paths or environment dumps;
- run `730d_BA` or `3650d_BA`;
- claim production readiness.

## 5. Binding acceptance / failure criteria (§10 of PR #407, confirmed)

The PR #407 §10 thresholds are **confirmed as binding lower-bound execution
criteria for the first run**. They may be **tightened only by explicit human +
ChatGPT review**; they **must not be loosened**.

| Criterion | Binding lower bound (holdout, 0.5 pip cell) |
| --- | --- |
| minimum holdout trades | ≥ 300 (portfolio-wide) |
| minimum daily coverage | trades on ≥ 60% of holdout trading days |
| post-cost expectancy | > 0 pips per trade |
| daily portfolio Sharpe (annualised) | ≥ 0.8 |
| max equity drawdown | ≤ 15% of fixed notional equity |
| turnover guard | ≤ 40 trades/day portfolio average |
| pair concentration guard | no single pair > 40% of trades or > 50% of positive PnL |
| session concentration guard | diagnostic-only in this Step 4 |
| cost sensitivity guard | post-cost expectancy remains ≥ 0 at the 1.0 pip cell |
| provenance / reproducibility | complete per PR #407 §7 |

The future run **must report both** whether criteria are met/not met **and** any
hard invalidation trigger. **An honest below-threshold result is valid
reportable evidence, not a process failure** — it must not be hidden or rerun
into a search.

## 6. Evidence schema for the future execution (metadata-only)

Future evidence directory: `artifacts/ml_step4/365d_ba_v1/`

Expected files:
- `ml_step4_run_manifest.json`
- `ml_step4_pre_consumption_checksum_report.json`
- `ml_step4_split_report.json`
- `ml_step4_model_config_report.json`
- `ml_step4_metrics_report.json`
- `ml_step4_cost_sensitivity_report.json`
- `ml_step4_leakage_provenance_report.json`
- `ml_step4_acceptance_failure_decision_report.md`

Evidence **may include:** epoch ID; code SHA; config hash; feature config hash;
package versions; random seeds; file hashes; split boundaries; selected
validation threshold; model config; metrics; acceptance/failure outcome;
hard-stop status if applicable.

Evidence **must not include:** raw data rows; raw data files; model binaries
(unless separately approved); credentials; personal paths; environment dumps;
Google Drive links; R2 object keys.

## 7. Outcome vocabulary for the future execution

Allowed future execution statuses:
- `ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_MEETS_PREREGISTERED_CRITERIA`
- `ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_DOES_NOT_MEET_PREREGISTERED_CRITERIA`
- `ML_STEP4_RUN_INVALID_CHECKSUM_MISMATCH`
- `ML_STEP4_RUN_INVALID_PROVENANCE_MISSING`
- `ML_STEP4_RUN_INVALID_LABEL_CONTRACT_VIOLATION`
- `ML_STEP4_RUN_INVALID_TRAIN_SERVE_MISMATCH`
- `ML_STEP4_RUN_INVALID_LOOKAHEAD_LEAKAGE`
- `ML_STEP4_RUN_INVALID_INSUFFICIENT_OOS_SAMPLE`
- `ML_STEP4_RUN_INVALID_POST_HOC_TUNING`
- `ML_STEP4_RUN_INVALID_RAW_DATA_COMMITTED`
- `ML_STEP4_RUN_INVALID_PERSONAL_PATH_LEAKAGE`
- `ML_STEP4_RUN_INVALID_SCOPE_EXPANSION`

Not permitted as final result labels: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`,
`PRODUCTION_READY`, `ML_STEP4_AUTHORISED`.

## 8. Post-run review requirement

- Any future execution evidence **must be reviewed by human + ChatGPT**.
- A **Fable 5 adversarial post-run audit is recommended before interpreting any
  positive result.**
- A positive result **does not imply production readiness**.
- A negative result is **valid evidence** and must not be hidden or rerun into a
  search.
- **No live/paper trading decision follows directly from the first run.**

## 9. Non-authorisation statements

This PR does **not**: execute ML Step 4; read raw data; train a model; run a
backtest; write model binaries; generate metrics; access external disks; access
Google Drive; access R2; start Phase C2; include `730d_BA`; include `3650d_BA`;
claim production readiness; validate profitability; rehabilitate historical
Phase 9.X metrics; or promote/demote Phase 9.16. It is an execution-plan record
only.

## 10. Recommended next gate

- **Next gate: ML Step 4 first-run execution evidence PR.**
- That next PR **must be explicitly authorised** (separate human + ChatGPT
  go-ahead).
- It will be the **first PR allowed to read `365d_BA` raw data and train the
  pre-registered model**.
- It **must run exactly the PR #407 contract** as constrained by this
  execution-authorisation plan.
- It **must stop if any pre-execution hard gate (§3) fails**, recording the
  appropriate `ML_STEP4_RUN_INVALID_*` status.

**TBDs / blockers: none** — the contract (PR #407) and this authorisation plan
fully constrain the run; the only remaining action before the run is the
explicit human + ChatGPT execution go-ahead.
