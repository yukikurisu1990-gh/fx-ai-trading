# Phase F — ML Step 4 pre-registration (`RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`)

- **Document class:** doc-only pre-registration contract (designs the first real
  ML Step 4 experiment; executes nothing)
- **Base:** master `f75786b` (post PR #406 merge)
- **Branch:** `docs/phase-f-ml-step4-pre-registration`
- **Predecessor gates:** Phase D acceptance (PR #405), Phase E epoch adoption
  (PR #406, `PHASE_E_365D_BA_RESEARCH_FROZEN_HOLDOUT_EPOCH_ADOPTION_RECORDED`).
- **Binding contracts inherited:** F-2 (`tests/unit/test_f2_pnl_layer_invariants.py`,
  `scripts/traded_direction_pnl.py`), F-5 (`scripts/provenance_guard.py`,
  model-manifest provenance), F-8
  (`docs/design/train_serve_consistency_contract.md`), audit memo
  (`docs/design/project_wide_logic_audit_fable5_findings.md`).

## Phase F status

**`PHASE_F_ML_STEP4_PRE_REGISTRATION_CREATED`**

Also binding: `ML_STEP4_EXECUTION_NOT_AUTHORISED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: this contract does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `BYTE_ADMISSIBILITY_APPROVED`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; those tokens
appear only as prohibitions.

## 1. Executive summary

- This is a **doc-only ML Step 4 pre-registration contract**.
- It binds the first real ML experiment to
  **`RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`**.
- It does **not** execute ML Step 4, does **not** train a model, does **not**
  run a backtest, and does **not** claim production readiness.
- It is written so that a future execution PR can **only run the pre-registered
  experiment or stop** — any deviation is a hard failure, not a judgment call.

## 2. Pre-registered epoch

| Field | Value |
| --- | --- |
| epoch ID | `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1` |
| span | `365d_BA` |
| file count | 20 |
| total bytes | 1,481,715,517 |
| byte-admissibility acceptance | PR #405 |
| Phase E adoption | PR #406 |
| local/offline limitation | no object-lock / WORM (must be disclosed in the run report) |
| required pre-consumption check | **re-verify all 20 file SHA-256 + sizes against the PR-B.1 inventory immediately before execution; any mismatch = hard stop** |

## 3. Experiment purpose

Narrow purpose: **evaluate whether a post-F-2/F-5/F-8-compliant ML pipeline
shows out-of-sample evidence strong enough to justify further research.**

Explicitly not the purpose: claiming profitability; approving live/paper
trading; selecting a production strategy; rehabilitating historical Phase 9.X
results (all pre-F-2 numerics remain archived/untrusted/invalid as classified).

## 4. Candidate model / champion configuration (exactly one)

Bound to existing project conventions (no invented parameters):

| Element | Pre-registered value | Source convention |
| --- | --- | --- |
| model family | LightGBM multiclass classifier (3-class: SL / timeout / TP), single family — no XGBoost/CatBoost comparisons, no alternative families | `scripts/train_lgbm_models.py` |
| target / label contract | B-2 bid/ask triple-barrier: entry next-bar ask (long) / bid (short); TP = 1.5×ATR14, SL = 1.0×ATR14; ATR14 `min_periods=14`; same-bar tie **SL-first strict `<`** (F8-A) | trainer + F-8 contract |
| prediction horizon | 20 M1 bars | `_HORIZON = 20` |
| feature set family | `FEATURE_VERSION v4` **base** set only — opt-in groups (`mtf`, `vol`, `moments`) are **excluded** from this first Step 4 (minimises multiplicity; avoids the F8-E fallback-history caveat) | `feature_service.py` / trainer |
| training procedure | contract-consistent **retrain from scratch** on the training window (the deployed `models/lgbm/` artifacts predate F8-A/F5-E and **must not** be reused as evidence — Phase A residual R6) | readiness audit §5 R6 |
| hyperparameters | the committed `_LGBM_PARAMS` + `_N_ESTIMATORS` defaults, **frozen** — no hyperparameter search | trainer |
| calibration | none in this Step 4 (raw `predict_proba` with fixed thresholds, matching the current production trainer); recorded as a declared limitation | F-8 residual, audit MM-3 |
| eligible instruments | the 20 pairs of `365d_BA` (the epoch's inventoried files), all trained/evaluated per-pair | epoch identity |
| cost model | spread embedded exactly once via B-2 label geometry; flat slippage applied per trade at evaluation; **primary evaluation cell = 0.5 pip slippage**; {0.0, 1.0} pip as sensitivity diagnostics only | Phase 9.10/9.12 convention + F-2 |
| thresholding rule | confidence threshold selected **on the validation window only** from the pre-declared set **{0.35, 0.40, 0.45}** (0.40 = production default); the frozen holdout is evaluated **exactly once** with the selected threshold — no tuning on holdout | `lgbm_strategy.py` `_DEFAULT_THRESHOLD` |
| position sizing (evaluation) | fixed stake, 1 notional unit per trade, non-compounding; PnL in pips (`pips_post_cost`) | F-8 EV contract |
| trade concurrency | **event-driven, max 1 open position per pair**: a new signal on a pair is ignored while that pair's position is open (entry blocks re-entry until barrier/timeout exit) — this closes the audit F-7 overlapping-trades defect for this experiment | audit VB-4/F-7 |
| portfolio aggregation | per-trade pips → **daily portfolio PnL** (sum across pairs per UTC day, equal per-trade stake) → daily-return series on fixed notional equity | audit F-7 metric fix |
| maximum configurations | **3** total (the three threshold variants on validation); **1** champion on the holdout | §11 |

No element above may be changed at execution time. **`PRE_REGISTRATION_BLOCKER_TBD` items: none** — every element resolves to an existing committed convention; the only open values are the acceptance thresholds in §10, which are conservative placeholders explicitly requiring human + ChatGPT review before execution.

## 5. Data split and leakage control

- **Common cross-pair window** (from the committed inventory, deterministic):
  from `max(per-pair ts_min_utc)` = 2025-04-25T17:09Z to
  `min(per-pair ts_max_utc)` = 2026-04-24T20:58Z. All pairs trimmed to this
  common window before splitting (avoids per-pair vintage skew at the edges).
- **Chronological split by fixed fractions of the common window (deterministic
  and reproducible from the inventory alone):**
  - training: first **70%**;
  - validation: next **15%** (threshold selection only);
  - **frozen holdout: final 15%** — the final test region, evaluated exactly
    once with the validation-selected threshold.
- **Purge/embargo:** the last `horizon + 1` (= 21) M1 bars of each earlier
  segment are dropped from label-eligible rows at every boundary, so no
  training/validation label window crosses into a later segment.
- **Completed-bar-only rule:** decisions use completed bars only; features may
  use the decision bar's close (matching training availability, F8-D).
- **MTF as-of rule:** not applicable (mtf group excluded); if any upper-TF
  feature in the v4 base set is used, it must be the shift(1) completed-bucket
  definition (F8-E) — no in-progress buckets.
- **No lookahead**; **no train-on-test**; **no threshold tuning on the final
  holdout**; **no post-hoc pair/session cherry-picking** — the reported result
  is the all-20-pair portfolio, with per-pair contributions shown as
  diagnostics only.

## 6. F-2 label / PnL contract (hard stop on violation)

The experiment is bound to the F-2 corrections:

- **traded-direction PnL** — the traded direction's own barrier path is scored
  (per `scripts/traded_direction_pnl.py` semantics), never label identity;
- **spread embedded exactly once** (ask-entry / bid-exit geometry; the flat
  slippage cell is additive and declared);
- **SL-first same-bar tie handling** (strict `<`), identical in labels and
  evaluation;
- **timeout mark-to-market** at the horizon-end exit side close — never booked
  as 0;
- **label ↔ evaluation consistency** — the same contract generates training
  labels and scores evaluation trades;
- **no use of pre-F-2 optimistic historical results** anywhere in design,
  thresholds, or reporting.

**Any violation of this section is a hard stop** (`ML_STEP4_RUN_INVALID`-class
outcome; the run is non-admissible).

## 7. F-5 provenance contract (missing item ⇒ run non-admissible)

Future execution evidence must include: epoch ID; the 20 file hashes /
inventory references (and the pre-consumption re-verification result); code
SHA; config hash; feature config hash; label contract reference; cost model
reference; train/validation/test boundary timestamps as computed; random
seeds; package/environment metadata where appropriate (versions, no env-var
values); **metadata-only evidence**; **no raw data committed**. Any missing
required provenance makes the run **non-admissible**.

## 8. F-8 train/serve consistency contract

- **EV unit: canonical `pips_post_cost`**, explicit and comparable between
  training evaluation and any serving-side interpretation;
- completed-bar decision assumptions declared (decision at bar close; entry
  next-bar open side-appropriate price);
- MTF as-of assumptions declared (excluded in this Step 4; else shift(1)
  completed buckets);
- warmup/min-period constraints (ATR14 `min_periods=14`; feature warmup rows
  unlabeled/excluded);
- **fail-closed behavior for unvalidated legacy strategies** — only the
  pre-registered LGBM pipeline participates; no fallback to incompatible EV
  units; **no silent strategy substitution**.

## 9. Metrics

**Primary decision metric:** **daily portfolio Sharpe (annualised ×√252) on the
frozen holdout at the 0.5 pip slippage cell** — computed from the daily
portfolio PnL series (never per-trade Sharpe as the decision metric).

**Secondary diagnostics:** per-trade post-cost expectancy (pips); trade count;
turnover (trades/day); win rate; average win / average loss; daily portfolio
PnL series; pair-level contribution; exposure / position concurrency
(open-positions distribution under the 1-per-pair rule); session-level
contribution (diagnostic only; session is not an evaluated dimension in this
Step 4).

**Safety metrics:** max equity drawdown (% of fixed notional equity, peak-to-
trough on the daily equity curve — not DD%PnL); pair concentration (max single-
pair share of trades and of PnL); cost sensitivity (all metrics recomputed at
0.0 and 1.0 pip cells).

**Non-decision exploratory diagnostics** (must be labeled as such in the
report): feature importance; per-threshold validation curves; calibration
diagnostics.

## 10. Acceptance and failure criteria

**Acceptance criteria (ALL must hold on the frozen holdout, 0.5 pip cell).**
Thresholds below are **conservative placeholders requiring human + ChatGPT
review before execution** — they make the gate concrete, not ambiguous, and may
be tightened (not loosened) at review:

| Criterion | Placeholder threshold |
| --- | --- |
| minimum trade count | ≥ 300 holdout trades (portfolio-wide) |
| minimum daily coverage | trades on ≥ 60% of holdout trading days |
| post-cost expectancy | > 0 pips per trade at 0.5 pip cell |
| daily portfolio Sharpe (annualised) | ≥ 0.8 |
| max equity drawdown | ≤ 15% of fixed notional equity |
| turnover / overtrading guard | ≤ 40 trades/day portfolio average |
| pair concentration guard | no single pair > 40% of trades or > 50% of positive PnL |
| session concentration guard | diagnostic-only in this Step 4 (session not evaluated) |
| cost sensitivity guard | post-cost expectancy remains ≥ 0 at the 1.0 pip cell |
| reproducibility / provenance | §7 complete; re-run from manifest reproduces metrics |

**Hard failure triggers (any one ⇒ run invalid / stop):** checksum mismatch
before execution; missing provenance (§7); label-contract violation (§6);
train/serve mismatch (§8); lookahead leakage; insufficient OOS sample (below
minimum trade count / coverage); post-hoc threshold tuning on the holdout; raw
data committed; personal path leakage; any attempt to claim production
readiness.

Outcome vocabulary for the future run: acceptance meets all criteria ⇒
`ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_MEETS_PREREGISTERED_CRITERIA`; criteria
not met ⇒ `..._DOES_NOT_MEET_PREREGISTERED_CRITERIA` (an honest negative is a
valid, reportable outcome); hard trigger ⇒ `ML_STEP4_RUN_INVALID_<REASON>`.

## 11. Multiplicity control

- maximum model configurations: **3** (threshold variants {0.35, 0.40, 0.45},
  validation window only);
- maximum thresholds: **3** (the same set; nothing else swept);
- maximum pair/session filters: **0** (all 20 pairs, no session filter);
- **no unrestricted grid search; no post-hoc best-cell selection** — the
  holdout sees exactly one configuration, chosen on validation before the
  holdout is touched;
- failed / rejected configurations (the 2 non-selected thresholds) **must be
  reported** with their validation metrics;
- exploratory diagnostics are allowed only if labeled
  `NON_DECISION_EXPLORATORY` in the report and are never inputs to the
  accept/fail decision.

## 12. Reporting schema (future execution, metadata-only)

Future evidence directory: `artifacts/ml_step4/365d_ba_v1/`

Expected reports: run manifest (epoch ID, code SHA, config hash, seeds,
boundaries); pre-consumption checksum verification report;
training/validation/test split report; model config report; metrics report
(primary/secondary/safety, per cost cell); cost sensitivity report;
leakage/provenance report; acceptance/failure decision report (against §10
verbatim).

Evidence must **not** include: raw data rows; raw data files; model binaries
(unless explicitly approved later); credentials; personal paths; environment
dumps.

## 13. Non-authorisation statements

This PR does **not**: execute ML Step 4; train a model; run a backtest; access
raw data; access external disks; access Google Drive; access R2; start
Phase C2; include `730d_BA`; include `3650d_BA`; claim production readiness;
validate profitability; rehabilitate historical Phase 9.X metrics; or
promote/demote Phase 9.16. It is a pre-registration contract only.

## 14. Recommended next gate

1. **Human + ChatGPT review of this Phase F pre-registration** — including the
   §10 placeholder thresholds, which must be confirmed or tightened before any
   execution.
2. If accepted, a **separate ML Step 4 execution-authorisation PR** (or
   execution-plan PR) that authorises running exactly this contract.

**ML Step 4 execution remains blocked until separately authorised. No training
or backtest can start from this PR alone.** Phase C2
(`730d_BA` / `3650d_BA`) may proceed independently later.
