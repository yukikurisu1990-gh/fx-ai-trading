# Fable 5 re-check — PR #412 fixes for executor blockers B-1/B-2/B-3 + R-2

- **Document class:** doc-only focused re-review (no code changes, no execution).
  Not a root-level audit; not a wiring PR.
- **Branch:** `docs/fable5-ml-step4-executor-recheck`
- **Base:** master `6fd2928` (post PR #413 merge)
- **Re-checked against:** PR #411 review
  (`docs/design/ml_step4_executor_harness_review_fable5.md`,
  `ML_STEP4_EXECUTOR_PRIMITIVES_BLOCKED_FOR_GUARDED_WIRING_REVIEW`) and the
  PR #412 diff (`b70de8e`). PR #413 used for sequencing context only.
- **Method:** every blocker was re-verified **by execution** against merged
  master code — the exact PR #411 reproduction probes plus an extended
  adversarial battery — not by re-reading the fix PR's claims. Probes ran the
  synthetic primitives on inline literals only; no data, no writes outside a
  refused-guard check (probe files verified never created).

## Re-check status

**`ML_STEP4_EXECUTOR_PRIMITIVES_ACCEPTABLE_FOR_GUARDED_WIRING_REVIEW_AFTER_RECHECK`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## 1. Executive verdict

**All three PR #411 blockers and the R-2 hardening are verified fixed by
execution.** The exact reproduction cases that proved the blockers in PR #411
now fail closed; an extended adversarial battery (subset/extra/duplicate/
non-numeric sweeps; per-path missing/None acceptance probes; cwd-manipulation,
path-traversal, nested-dir and case-trick guard probes; six scrub leak
classes) found **zero fail-open paths**. No stale hyperparameters remain
anywhere in the package; nothing sets `allow_execution_evidence=True`; PR #409
stop evidence is untouched. The executor primitives are acceptable to proceed
to a **code-only guarded `execute()` wiring PR**, which must bind the
wiring-bound residuals in §8 before any first-run execution.

## 2. Re-check scope

Re-checked: `scripts/ml_step4/{contract,thresholds,acceptance,evidence}.py`,
`tests/ml_step4/test_{contract,thresholds,acceptance,evidence}.py`, the PR
#411 review document, and the PR #412 diff. Supporting sources:
`scripts/train_lgbm_models.py` (AST-extracted literals). Out of scope by
design: split/labels/simulator/metrics/CLI modules (unchanged by PR #412 and
not blocked by PR #411), the PR #413 audit (sequencing context only).

## 3. B-1 re-check — model contract drift: **FIXED**

Verified by execution against master:

- `contract.LGBM_PARAMS == {"learning_rate": 0.05, "num_leaves": 31,
  "verbose": -1}` and **byte-matches the AST-extracted trainer literals** from
  `scripts/train_lgbm_models.py` (`_LGBM_PARAMS`, lines 58–62).
- `contract.LGBM_N_ESTIMATORS == 200 ==` trainer `_N_ESTIMATORS`.
- Research extras absent: none of `min_child_samples` / `reg_alpha` /
  `reg_lambda` / `random_state` / `n_jobs` appears in `LGBM_PARAMS`; a
  repo-grep confirms no stale reference anywhere in `scripts/ml_step4/` (the
  only `random_state` hit is the explanatory comment).
- **No seed invented:** `model_config()` has no `random_seed`; it records
  `seed_policy = "wiring_pr_responsibility_trainer_defines_none"` — the
  determinism decision is explicitly deferred to the guarded wiring PR.
- `model_config_hash` = `bc27cfa39ea3…`, stable across calls, reflecting the
  corrected convention (changed from the drifted `28ec6b…`; safe — no run ever
  consumed the old hash).
- The pinning test (`test_b1_lgbm_params_equal_trainer_literals`) extracts the
  trainer literals via `ast.parse`/`ast.literal_eval` — **no import of the
  trainer module, no lightgbm dependency, no execution**.
- Fail-closed guards intact: `assert_model_family("xgboost")` raises;
  `assert_no_deployed_model_reuse("models/lgbm/…")` raises.

## 4. B-2 re-check — threshold selector full-sweep enforcement: **FIXED**

Verified by execution:

- Signature has **no holdout parameter** (`validation_metrics_by_threshold`,
  `selection_metric`, `candidates`, `production_default`) — holdout leakage
  into selection remains structurally impossible.
- The exact PR #411 reproduction `select_threshold({0.45: …})` now raises
  ("threshold sweep must cover exactly the registered candidate set").
- Missing candidate ({0.35, 0.45}) raises; extra candidate (+0.50) raises;
  non-numeric key raises; missing validation metric for any candidate raises;
  duplicate-after-float-normalisation raises (code inspection: `provided`-set
  duplicate check; dict keys make same-float duplicates unrepresentable, the
  check catches str/float aliases).
- Deterministic selection and tie rule verified: all-equal tie → **0.40**
  (production default preferred); tie excluding the default → **smallest
  (0.35)**. The rule is recorded in code comments and tests (residual R-6:
  it must also be recorded in the wiring PR's pre-registered config).
- Rejected variants: both non-selected thresholds are recorded with their
  validation metrics (`rejected: [0.35, 0.45]` in the tie probe).

## 5. B-3 re-check — acceptance evaluator missing/None metrics: **FIXED**

Verified by execution:

- `REQUIRED_METRIC_PATHS` (9 paths) explicitly covers: trade count, daily
  coverage, post-cost expectancy (0.5-pip cell), annualised daily portfolio
  Sharpe, max-drawdown fraction, **turnover**, pair trade-share concentration,
  pair positive-PnL-share concentration, and the 1.0-pip cost-sensitivity
  expectancy. Provenance completeness is enforced via the required
  `provenance_complete` parameter (verified: `False` →
  `ML_STEP4_RUN_INVALID_PROVENANCE_MISSING`).
- The exact PR #411 reproduction (missing `turnover_trades_per_day`) now
  yields `ML_STEP4_RUN_INVALID_PROVENANCE_MISSING` with the missing path
  listed — no meets-criteria status is reachable with missing data.
- **Per-path None probes: 0 of 9 fail open** (every None → PROVENANCE_MISSING).
  Deletion probes equally covered by the parametrised PR #412 tests.
- All-criteria-met still → `…_MEETS_PREREGISTERED_CRITERIA`; honest
  below-threshold (Sharpe 0.3) still → `…_DOES_NOT_MEET_PREREGISTERED_CRITERIA`
  with the full criteria table (not hidden).
- Hard-trigger dominance intact: `CHECKSUM_MISMATCH` + missing turnover →
  `ML_STEP4_RUN_INVALID_CHECKSUM_MISMATCH` (precedence order preserved).
- No broad pass-like or production-like status is reachable: the vocabulary is
  the closed set {MEETS, DOES_NOT_MEET} ∪ {`ML_STEP4_RUN_INVALID_<enum>`}.

## 6. R-2 re-check — evidence guard hardening: **FIXED**

Verified by execution (with the process cwd moved **outside the repository**
for the write probes):

- Guard is **repo-root anchored** via the module's own path
  (`Path(__file__).resolve().parents[2]`), not cwd; `repo_root()` resolves to
  the repository independent of the working directory.
- Refused, with probe files verified never created: direct write into the real
  `artifacts/ml_step4/365d_ba_v1/`; `..`-traversal that resolves into it;
  nested subdirectory of it; **case-trick path** (`ARTIFACTS/ML_STEP4/…` —
  refused via Windows case-insensitive path equality); all under cwd
  manipulation. `allow_execution_evidence` defaults False and is set nowhere
  in the tree.
- Scrubber rejects all six probed leak classes: Google Drive links, R2
  endpoints/keys, credential-bearing keys, environment dumps, raw candle-row
  keys, personal absolute paths.
- Deterministic JSON serialisation preserved (sorted keys, byte-equal across
  key order); scrub-then-write ordering preserved.
- **PR #409 stop evidence untouched:** directory still exactly 8 files,
  git-clean before and after all probes.

## 7. Test adequacy: **ADEQUATE**

PR #412 raised the suite from 88 → **124 tests**, adding direct reproduction
coverage for every PR #411 blocker: B-1 AST literal-pinning + research-extras
absence + extra-param hash change; B-2 subset/missing/extra/non-numeric/
duplicate raise tests incl. the `{0.45: …}` reproduction; B-3 parametrised
missing + None probes for each of the 9 required paths (18 cases) incl. the
turnover reproduction and trigger-dominance; R-2 cwd-manipulation, traversal,
nested-dir and safe-tmp tests. All synthetic-only: no real raw data read, no
model trained, no real ML metrics. The failure modes PR #411 proved are now
each pinned by at least one test that would fail on regression.

## 8. Remaining wiring-bound residuals (intentionally unresolved — carry to wiring)

Confirmed still open by design; the guarded `execute()` wiring PR **must bind
all of these before any first-run execution**:

1. **R-1** — apply split boundaries at M1-bar granularity with one documented
   comparison rule.
2. **R-4** — route all label generation AND all trade scoring exclusively
   through `labels.py` (single-source label/eval consistency).
3. **R-5** — pin one auditable holdout trading-day definition.
4. **R-6** — record the threshold tie-rule (prefer 0.40, else smallest) in the
   wiring PR's pre-registered config.
5. **Seed/determinism decision** (deferred by B-1's fix; trainer defines none).
6. **maxDD fixed-notional constant** (PR #413 must-fix — without it the ≤15%
   criterion is unfalsifiable).
7. **`NON_DECISION_EXPLORATORY` diagnostic labeling** enforcement in the
   evidence path (PR #413 must-fix).

## 9. Blockers

**None.** All PR #411 blockers (B-1, B-2, B-3) are verified fixed; R-2 is
verified hardened.

## 10. Non-blocking residual risks

- **NaN semantics:** a NaN metric value passes the presence check (it is not
  None) and falls through to criteria comparison, where every comparison is
  False → `…_DOES_NOT_MEET_…`. Conservative (an honest miss, never a pass),
  but arguably a NaN should be `PROVENANCE_MISSING`; the wiring PR may add a
  finiteness check when assembling metrics. Not a fail-open path.
- **String-typed numerics** (e.g. `"500"` for trade_count) are coerced by
  `int()`/`float()` rather than rejected — benign because the wiring PR
  computes these values internally via `metrics.compute_all`; noted for
  completeness.
- The case-trick guard refusal relies on Windows case-insensitive path
  equality; on a case-sensitive filesystem a differently-cased directory would
  be a genuinely different directory (not the protected one), so this is not a
  bypass vector on either platform.
- Wiring-bound residuals of §8 (unchanged).

## 11. Recommendation for next gate

1. Human + ChatGPT review/merge of this re-check.
2. **Code-only guarded `execute()` wiring PR** (separately authorised; still
   no run): assemble the re-checked primitives into a single fail-closed
   `execute()` path binding all seven §8 items, with the PR #413 pre-declared
   interpretation frame (first-run = falsification/baseline measurement).
3. Wiring-PR review (optionally a short Fable 5 wiring re-check).
4. Separately-authorised first-run execution PR; then the mandated post-run
   review (+ recommended Fable 5 adversarial post-run audit).

## 12. Non-authorisation statements

This re-check did **not**: execute ML Step 4; read real `365d_BA` raw data;
train a model; run a backtest; generate real ML metrics; create real execution
evidence (the guard probes were refused before any write; probe files verified
absent; PR #409 evidence dir git-clean); write model binaries; start guarded
execute wiring; access external disks, Google Drive, or R2; start Phase C2;
touch `730d_BA` or `3650d_BA`; claim production readiness.
