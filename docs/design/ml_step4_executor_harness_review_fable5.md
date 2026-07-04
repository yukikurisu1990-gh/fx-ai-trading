# Fable 5 adversarial harness review — ML Step 4 contract executor (PR #410)

- **Document class:** review-only adversarial audit record (no code changes,
  no execution)
- **Branch:** `docs/fable5-ml-step4-executor-harness-review`
- **Base:** master `4c2bdbc` (post PR #410 merge)
- **Audited against:** PR #407 pre-registration
  (`docs/design/phase_f_ml_step4_pre_registration.md`) and PR #408
  execution-authorisation plan
  (`docs/design/ml_step4_365d_ba_execution_authorisation_plan.md`)
- **Audited surface:** `scripts/ml_step4/` (10 modules), `tests/ml_step4/`
  (88 tests), `docs/design/ml_step4_executor_implementation_note.md`

## Review status

**`ML_STEP4_EXECUTOR_PRIMITIVES_BLOCKED_FOR_GUARDED_WIRING_REVIEW`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear in this review only as prohibitions.

## 1. Executive verdict

The PR #410 primitives are **architecturally sound** — no execution path exists,
dry-run reads no raw data, holdout leakage into threshold selection is
structurally absent, the primary metric is genuinely daily-portfolio Sharpe, and
the evidence scrubber rejects every probed leak class. However, the adversarial
pass found **one material contract-drift blocker and two fail-open blockers**,
all three *proven by execution*, and all three missed by the 88-test suite:

- **B-1 (material drift):** `contract.py` freezes the **wrong LightGBM
  hyperparameters** — v14 research-script params plus `n_estimators = 300`,
  a value that matches **no committed convention** — instead of the trainer
  defaults PR #407 §4 binds to.
- **B-2 (fail-open):** the threshold selector silently accepts an **incomplete
  candidate sweep** (1 of 3), violating PR #407 §11 multiplicity control.
- **B-3 (fail-open):** the acceptance evaluator emits
  `..._MEETS_PREREGISTERED_CRITERIA` when a required metric key is **missing**,
  silently defaulting turnover to a passing value.

Because the fixes are small, isolated, and nothing has yet consumed the
affected hashes (no run was performed; PR #409 stopped before training), the
correct route is a **small code-only fix PR** addressing B-1/B-2/B-3 (+ selected
residuals), re-reviewed, then the guarded `execute()` wiring PR. **Verdict:
BLOCKED for guarded wiring until the required fixes land.**

## 2. Reviewed files

`scripts/ml_step4/`: `__init__.py`, `contract.py`, `inventory.py`, `split.py`,
`labels.py`, `thresholds.py`, `simulator.py`, `metrics.py`, `acceptance.py`,
`evidence.py`, `run_365d_ba.py`. `tests/ml_step4/`: all 10 test modules
(88 tests). Plus `docs/design/ml_step4_executor_implementation_note.md`, and the
bound convention sources: `scripts/train_lgbm_models.py`,
`scripts/traded_direction_pnl.py`, `scripts/compare_multipair_v9_orthogonal.py`
(B-2 label rule), `src/fx_ai_trading/services/feature_service.py`,
`src/fx_ai_trading/services/strategies/lgbm_strategy.py`,
`scripts/compare_multipair_v14_topk.py`.

## 3. Contract fidelity findings

Verified against PR #407 §2/§4/§5 and the committed sources:

| Element | contract.py | Bound convention | Verdict |
| --- | --- | --- | --- |
| epoch ID / span | `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1` / `365d_BA` | PR #406/#407 | match |
| file count / bytes | 20 / 1,481,715,517 | PR-B.1 inventory | match |
| model family | LightGBM 3-class | trainer | match |
| TP/SL/ATR | 1.5 / 1.0 / ATR14 `min_periods=14` | trainer `_TP_MULT=1.5`, `_SL_MULT=1.0`; PR #407 §4 | match |
| horizon | 20 M1 bars | trainer `_HORIZON=20` | match |
| feature set | v4 base only, opt-in excluded | `FEATURE_VERSION="v4"`, `ENABLE_GROUPS_DEFAULT=∅` | match |
| thresholds | {0.35, 0.40, 0.45}; default 0.40 | `_DEFAULT_THRESHOLD=0.40` | match |
| cost cells | 0.5 primary; 0.0/1.0 diagnostics | PR #407 §4 | match |
| split | common window 2025-04-25T17:09Z→2026-04-24T20:58Z; 70/15/15; purge 21 | PR #407 §5 | match |
| primary metric | daily portfolio Sharpe ×√252 | PR #407 §9 | match |
| acceptance thresholds | §10 table verbatim | PR #407 §10 / PR #408 §5 | match |
| forbidden scope | 730d/3650d/C2/families/reuse/search/holdout-tuning/filters/Drive/R2 | PR #408 §4 | match |
| **hyperparameters** | **v14 `DEFAULT_PARAMS` + `n_estimators=300`** | **trainer `_LGBM_PARAMS={lr 0.05, num_leaves 31, verbose −1}`, `_N_ESTIMATORS=200`** | **DRIFT — B-1** |

**B-1 detail (material).** PR #407 §4 row "hyperparameters" binds to "the
committed `_LGBM_PARAMS` + `_N_ESTIMATORS` defaults, frozen" with source
convention *trainer* (`scripts/train_lgbm_models.py`). The trainer's committed
values are `_LGBM_PARAMS = {"learning_rate": 0.05, "num_leaves": 31,
"verbose": -1}` (line 58) and `_N_ESTIMATORS = 200` (line 54). `contract.py`
instead froze `compare_multipair_v14_topk.py`'s research `DEFAULT_PARAMS`
(adding `min_child_samples=50`, `reg_alpha=0.1`, `reg_lambda=0.1`,
`random_state=42`, `n_jobs=1`) and set `LGBM_N_ESTIMATORS = 300` — which
matches **neither** the trainer (200) **nor even v14's own argparse default
(200)**. The silent addition of regularisation parameters and an invented
estimator count is exactly the "no invented parameters" violation PR #407 §4
prohibits, and it is baked into `model_config_hash`/`config_hash`. Mitigating
factor: no run has consumed these hashes, so the fix is clean.
The `random_state`/determinism question (the trainer's frozen set has no seed)
must be resolved as an **explicit human + ChatGPT decision** in the fix PR, not
a silent default in either direction.

Minor notes (non-drift): `EXCLUDED_FEATURE_GROUPS` includes `"moments"`, which
is not a `FeatureService` group (`_VALID_GROUPS={"mtf","vol"}`) — a harmless
superset (R-7). `LGBM_OBJECTIVE`/`LGBM_NUM_CLASS` are descriptor-level fields
the sklearn wrapper infers rather than trainer literals — acceptable (R-8).

## 4. Fail-closed findings

Probed and confirmed fail-closed: non-dry-run invocation (rc 2, no wired path);
non-LightGBM family (`assert_model_family` raises); deployed `models/lgbm/`
reuse (case-insensitive path check raises); non-empty feature groups (raises,
including unknown groups); inventory wrong count / wrong total bytes / duplicate
filenames / invalid sha / non-positive size (all raise); runtime file missing or
checksum/size mismatch (raises); unparseable / naive / non-overlapping
timestamps (raise); unregistered thresholds and non-finite metrics (raise);
unsafe evidence content (raises before write; probe file confirmed never
created).

Confirmed fail-OPEN (blockers):

- **B-2:** `select_threshold({0.45: …})` — a 1-of-3 sweep — returns 0.45 with
  zero rejected variants recorded (proven by execution). PR #407 §11 requires
  all 3 validation variants evaluated and the 2 rejected ones reported; the
  primitive lets an incomplete sweep pass silently, so a wiring bug could
  evaluate one threshold and still look contract-compliant.
- **B-3:** `AcceptanceEvaluator.evaluate()` with `turnover_trades_per_day`
  **absent** returned `ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_MEETS_PREREGISTERED_CRITERIA`
  with `turnover {value 0.0, passed True}` (proven by execution). Missing-key
  defaults are fail-safe for most criteria (0.0 expectancy/Sharpe fail; 1.0
  dd/concentration fail) but fail-open for turnover — an unmeasured criterion
  can be reported as met. An acceptance gate must raise on missing input, not
  default it.

## 5. F-2 label / PnL findings

Sound. `labels.py` delegates to the committed
`scripts/traded_direction_pnl.traded_direction_pnl_price` (identity verified by
test — no reimplementation drift possible); same-bar TP+SL tie resolves SL-first
(proven: tie → −1.0 R); timeout returns caller-supplied mark-to-market (proven:
0.37 R, not zeroed); barrier distances carry the B-2 ask-entry/bid-exit geometry
with **no** extra spread in the adapter, and `apply_cost_cell` subtracts the
flat slippage exactly once (proven: 1.5 → 1.0 at 0.5 pip); long/short signs
correct; `barrier_label` reproduces the committed v9 clears-rule including the
both-clear earlier-TP tie. Label/evaluation consistency is achieved by
construction (one adapter feeds both) **provided the wiring PR routes all label
generation and all trade scoring through this module** — recorded as wiring
requirement R-4.

## 6. Split / leakage findings

Correct on the probed cases: common window = max(ts_min)..min(ts_max) with
fail-closed empty-overlap; chronological 70/15/15 by time-fraction of the
common window (matching §5 "fixed fractions of the common window");
purge/embargo = 21 bars applied to each earlier segment's label-eligible end
(21 = next-bar entry + 20-bar window, so no training/validation label window
can cross a boundary — off-by-one checked and sound); strictly ordered
boundaries enforced (`start < train_label_end < train_end < val_label_end <
val_end < end`); deterministic (pure function, no wall clock; equality of
repeated builds tested). Residual **R-1:** boundary datetimes are derived from
float-seconds arithmetic and serialised at whole-second precision
(`%H:%M:%S`), so a sub-second float remainder is truncated in the emitted
metadata; the wiring PR must apply boundaries at M1-bar granularity with one
documented comparison rule (recommend: bar belongs to segment iff
`bar_ts < boundary`) so the truncation can never reclassify a bar.

## 7. Threshold findings

Validation-only by construction — `select_threshold` has **no holdout
parameter**; there is no code route for holdout data to reach the selection
(structural absence, the strongest form). Unregistered thresholds, missing
selection metric, non-finite values, and empty input all raise. Ties are
deterministic (prefer 0.40, else smallest) — note **R-6**: this tie rule is a
*new* deterministic decision not specified in PR #407; acceptable, but it must
be carried explicitly into the wiring PR's pre-registered config record.
Rejected variants are recorded with their validation metrics **when supplied**
— but see **B-2**: completeness of the 3-candidate sweep is not enforced.

## 8. Simulator findings

Correct on all probed cases: overlapping same-pair signal ignored with reason
`pair_position_open`; re-entry accepted at `entry == exit` (documented,
deterministic convention, consistent with `concurrency_profile`'s
exit-before-entry tie handling); per-pair isolation (two pairs concurrently
open is allowed — the rule is per-pair, matching §4); input-order independence
proven (same result for permuted input); malformed intervals and missing pair
fail closed. Deterministic sort key `(entry, pair, direction)` means a same-bar
long+short pair conflict resolves alphabetically (long first) — deterministic,
and moot if the wiring emits at most one signal per pair-bar as the SELECTOR
contract implies (note R-9). The simulator **trusts** caller-resolved
exits/PnL; barrier/timeout correctness is delegated to `labels.py` — wiring
requirement R-4 again.

## 9. Metrics findings

The historical failure mode this project audited (per-trade optimistic
evaluation) is guarded against: `annualised_daily_sharpe` consumes the
**daily-aggregated portfolio series** (test proves the daily series `[1,3]` is
used, not the per-trade `[0.5,0.5,3]`); max drawdown is peak-to-trough on the
daily equity curve against an explicit fixed-notional base (fail-closed on
non-positive notional); pair concentration reports both trade share and
positive-PnL share (matching the §10 dual guard); cost sensitivity genuinely
recomputes per cell (proven 1.0/0.5/0.0 expectancy at 0/0.5/1 pip); session
contribution is not an evaluated dimension anywhere in the acceptance path
(diagnostic-only preserved). Degenerate Sharpe (<2 days, zero variance) returns
0.0 — conservative (fails the ≥0.8 gate). Residual **R-5:** turnover divides by
days-with-trades (conservative for the ≤40 guard: fewer days ⇒ higher turnover)
and `daily_coverage` takes `holdout_trading_days` as an external input — the
wiring PR must pin one auditable trading-day definition for the holdout and
document it in the split/metrics reports.

## 10. Acceptance evaluator findings

Status vocabulary is exactly the allowed set: the two `..._CREATED_*` outcomes
plus `ML_STEP4_RUN_INVALID_<REASON>` over a closed, typo-checked reason enum
with deterministic precedence; no pass-like or production-like status exists in
the module. Insufficient sample (trades < 300 or coverage < 60%) and missing
provenance are hard invalidation triggers, matching PR #407 §10's hard-failure
list. An honest below-threshold result yields `..._DOES_NOT_MEET_...` **with
the full criteria table attached** (not hidden; no retry path exists in code).
Strict-vs-inclusive comparisons match §10 (`> 0` expectancy; `≥ 0.8` Sharpe;
`≤` guards; `≥ 0` at 1 pip). One blocker: **B-3** (missing-key fail-open,
§4 above) — the evaluator must raise on absent required metrics.

## 11. Evidence writer findings

Metadata-only and deterministic: sorted-key, UTF-8, BOM-free JSON with trailing
newline (byte-determinism tested); non-string non-JSON reports fail closed. The
dedicated scrubber correctly **allows metric keys** (unlike the Foundation T2
scrubber, whose metric-key prohibition would falsely reject legitimate ML
evidence) while rejecting, each verified by test: raw candle/quote row keys;
Windows/Unix personal paths; credential-bearing keys; env dumps (both
VAR-assignment text and non-empty `env`/`environ` mappings); Google Drive
links; R2 endpoints/keys. Scrub-then-write ordering verified (rejected file
never created). The real-execution-directory guard refused a probe write into
`artifacts/ml_step4/365d_ba_v1/` without creating the probe — **PR #409 stop
evidence untouched** (also verified via git). No binary/model write path
exists. Residual **R-2:** the guard anchors on `Path.cwd()`, so invoking from a
different working directory could bypass it — defence-in-depth only; the wiring
PR should anchor the guard to the repo root and gate the real dir behind the
explicit execution flag.

## 12. CLI dry-run findings

`--dry-run` returns 0; reads **only** the committed PR-B.1 inventory JSON
(metadata; no `data/` file is opened — verified by code path and by the absence
of any raw-read primitive in the package); trains nothing (no ML import
anywhere in `scripts/ml_step4/` — LightGBM is never imported); evaluates no
holdout; writes no files (prints to stdout only); output is scrub-clean by
construction (`assert_clean` before print, plus test). Invoking without
`--dry-run` returns 2 with an explicit refusal — there is **no non-dry-run code
path to accidentally trigger**; the "real execution" branch simply does not
exist in this build. No accidental execution path found.

## 13. Test adequacy review

88 tests, synthetic-only, well-targeted on the probed invariants (F-2 ties,
timeout MTM, spread-once, daily-vs-per-trade Sharpe, scrub classes, guard
ordering, determinism). However, the suite **failed to catch all three
blockers**: no test pins `LGBM_PARAMS`/`LGBM_N_ESTIMATORS` against the
trainer's committed literals (B-1 — a hash-stability test cannot catch a wrong
frozen value); no test requires the full 3-candidate sweep (B-2); no test
probes a missing metric key in the acceptance evaluator (B-3). Under the
decision rule "tests are too weak to catch the above", this independently
supports the blocked verdict. The fix PR must add: a literal cross-check of the
frozen params against `scripts/train_lgbm_models.py` values; a
completeness-required selector test; missing-key acceptance tests.

## 14. Blockers

| ID | Module | Defect | Proof |
| --- | --- | --- | --- |
| **B-1** | `contract.py` | Frozen hyperparameters drift from the PR #407 §4 bound convention: v14 research params (+`min_child_samples`/`reg_alpha`/`reg_lambda`/`random_state`/`n_jobs`) and `n_estimators=300` vs trainer `_LGBM_PARAMS={lr 0.05, num_leaves 31, verbose −1}` / `_N_ESTIMATORS=200`; 300 matches no committed source | source diff (trainer lines 54–62 vs contract.py) |
| **B-2** | `thresholds.py` | Incomplete candidate sweep accepted silently (1 of 3 selects; zero rejected recorded) — §11 multiplicity-control bypass route | executed: `select_threshold({0.45:…})` → 0.45, rejected=0 |
| **B-3** | `acceptance.py` | Fail-open on missing required metric key: absent turnover defaults to 0.0/passed and the run reports `..._MEETS_PREREGISTERED_CRITERIA` | executed: MEETS with `turnover {value 0.0, passed True}` |

## 15. Non-blocking residual risks

- **R-1** split boundary float→whole-second serialisation truncation; wiring
  must apply boundaries at bar granularity with one documented rule.
- **R-2** evidence execution-dir guard is cwd-anchored (bypassable from another
  cwd); harden to repo-root anchor in wiring.
- **R-3** `verify_files` does not detect *extra* runtime files (consumption is
  inventory-driven, so extras cannot enter the dataset; document in wiring).
- **R-4** simulator/metrics trust caller-resolved exits and PnL; wiring must
  route all label generation AND all trade scoring exclusively through
  `labels.py` (single-source label/eval consistency).
- **R-5** turnover denominator = days-with-trades (conservative direction);
  `holdout_trading_days` definition externally supplied — pin one auditable
  trading-day definition in wiring.
- **R-6** threshold tie-break (prefer 0.40, else smallest) is a new
  deterministic decision not in PR #407 — record it explicitly in the wiring
  PR's pre-registered config.
- **R-7** `"moments"` in excluded groups is not a `FeatureService` group —
  harmless superset; keep.
- **R-8** `LGBM_OBJECTIVE`/`LGBM_NUM_CLASS` are descriptor-level (wrapper
  infers) — acceptable.
- **R-9** same-bar long+short same-pair tie resolves alphabetically in the
  simulator — deterministic; moot if wiring emits ≤1 signal per pair-bar.

## 16. Required fixes

A **small code-only fix PR** (no execution) before the guarded wiring PR:

1. **B-1:** set `LGBM_PARAMS = {"learning_rate": 0.05, "num_leaves": 31,
   "verbose": -1}` and `LGBM_N_ESTIMATORS = 200` (the trainer's committed
   literals). The seed/determinism question (trainer has no `random_state`)
   must be an **explicit human + ChatGPT decision** recorded in that PR —
   either match the trainer literally or add a declared determinism amendment.
   `config_hash`/`model_config_hash` will change; this is safe because no run
   has consumed the old hashes (PR #409 stopped pre-training with null hashes).
   Add a test pinning the frozen literals against `train_lgbm_models.py`.
2. **B-2:** require `select_threshold` input to cover **exactly**
   `{0.35, 0.40, 0.45}`; fail closed on missing or extra candidates; test.
3. **B-3:** make `AcceptanceEvaluator` raise on any missing/None required
   metric key instead of defaulting; tests for each required key.
4. Recommended in the same fix PR (cheap): repo-root-anchor the evidence
   execution-dir guard (R-2).
5. Defer to the wiring PR (documented there): R-1 bar-granularity boundary
   rule; R-4 single-source label routing; R-5 trading-day definition; R-6
   tie-rule record.

## 17. Recommendation for next gate

1. **Human + ChatGPT review of this audit.**
2. A **code-only fix PR** implementing §16 items 1–4 (+ tests), reviewed.
3. Then the **guarded `execute()` wiring PR** (code-only, still no run),
   binding the §16 item-5 wiring requirements.
4. Only after that: the separately-authorised first-run execution PR, followed
   by the mandated post-run human + ChatGPT review (with a recommended Fable 5
   adversarial post-run audit before interpreting any positive result).

## Non-authorisation

This review did **not**: execute ML Step 4; read real `365d_BA` raw data; train
a model; run a backtest; generate real ML metrics; create real execution
evidence; write model binaries; access external disks; access Google Drive;
access R2; start Phase C2; touch `730d_BA` or `3650d_BA`; claim production
readiness; rehabilitate historical Phase 9.X metrics; or promote/demote
Phase 9.16. The two proof-of-defect probes ran the merged synthetic primitives
on inline literals only (no data, no files written).
