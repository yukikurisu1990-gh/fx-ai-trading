# ML Step 4 — `365d_BA` first-run: acceptance / failure decision

- **Final execution status:** `ML_STEP4_RUN_INVALID_PROVENANCE_MISSING`
- **Also binding:** `ML_STEP4_EXECUTION_NOT_PERFORMED` · `PRODUCTION_READINESS_NOT_CLAIMED`
- **Epoch:** `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1` (`365d_BA`, 20 files, 1,481,715,517 bytes)
- **Code SHA:** `e0abde1a188f1668ae59382d37205310ed07b675`
- **Bound contract:** PR #407 pre-registration; **bound plan:** PR #408 execution-authorisation.
- **Evidence type:** metadata-only.

## Decision

**Stopped before training.** No model was trained; no holdout was evaluated;
no raw data rows were read into any feature or label computation.

This is **not** an honest below-threshold result — it is a **pre-execution
hard-gate stop**. The binding acceptance criteria are **UNMEASURED**, not failed.

## What passed

| Gate | Result |
| --- | --- |
| 1. Working tree clean | PASS |
| 2. Code SHA recorded | PASS (`e0abde1`) |
| 3. PR #407 + PR #408 present on master | PASS (both MERGED) |
| 4. Epoch resolved | PASS |
| 5. PR-B.1 inventory resolved | PASS |
| 6. Re-verify all 20 SHA-256 + sizes vs PR-B.1 inventory | **PASS — 20/20 match, 0 mismatch, 0 missing** |
| 7. Total bytes = 1,481,715,517 | PASS |
| 14. Dependency metadata recordable safely | PASS |
| 15. Evidence dir clean / creatable | PASS |
| 16. No raw/path/cred/env would be committed | PASS |

**Data integrity is not the problem.** All 20 files matched the committed
inventory immediately before the decision.

## Why the run stopped (gates 11–13)

The exact PR #407 contract requires an execution pipeline that:

1. trims all 20 pairs to the deterministic common cross-pair window,
2. applies a **chronological 70/15/15 train/validation/frozen-holdout split**
   with **purge/embargo = horizon + 1 = 21 M1 bars**,
3. generates **B-2 bid/ask triple-barrier labels** with the F-2-corrected
   traded-direction PnL / spread-once / SL-first-tie / timeout-mark-to-market
   semantics,
4. computes **`FEATURE_VERSION v4` base** features causally,
5. trains a **LightGBM 3-class classifier from scratch**,
6. selects one threshold from `{0.35, 0.40, 0.45}` **on validation only**,
7. evaluates the **frozen holdout exactly once** under an **event-driven
   max-1-open-position-per-pair** simulation,
8. computes **daily portfolio Sharpe** (primary), drawdown, turnover,
   concentration, and cost sensitivity at the 0.0 / 0.5 / 1.0 pip cells,
9. emits a **complete F-5 provenance chain** (code SHA + config hash +
   feature config hash + model config hash + seeds + deterministic
   reproducibility) per PR #407 §7.

**No committed, reviewed execution harness on master implements this contract.**
The existing `train_lgbm_models.py` has no 70/15/15 chronological frozen-holdout
split, no validation-only threshold selection, no event-driven per-pair holdout
simulation, and no daily-portfolio-Sharpe metric. The `compare_multipair_*`
scripts use **walk-forward folds** — a different evaluation topology than the
single frozen-holdout the contract mandates. The `foundation_t2` matches for
`ml_step4` are forbidden-path constants and scrubber patterns, not a runner.

Therefore:

- **Gate 12 (F-5 provenance) FAILS:** the provenance-complete pipeline that must
  emit the config / feature / model hashes and guarantee deterministic
  reproducibility does not exist as reviewed code. `config_hash`,
  `feature_config_hash`, and `model_config_hash` cannot be produced from a
  reviewed source, so provenance cannot be completed.
- **Gates 11 (F-2) and 13 (F-8) CANNOT BE CONFIRMED:** their enforcement lives
  inside the (absent) executor.

Per the PR #408 mandate — *"must run exactly the PR #407 contract … or stop"* —
and the standing rule that an unreviewed pipeline must not have its output
treated as the project's first real ML result, execution halted here rather than
authoring and **self-certifying** a novel ~several-hundred-line ML pipeline in a
single autonomous run. The project's own audit (F-2 / F-5 / F-8) exists because
hastily-assembled ML pipelines produce plausible-but-wrong numbers; a fresh,
unreviewed harness carries exactly that risk, and its correctness is the whole
point of this gate.

## This is a human + ChatGPT decision

The first real ML run is genuinely blocked on **one missing artifact: a
reviewed, contract-faithful execution harness.** Two clean ways forward — the
choice belongs to the human + ChatGPT reviewers, not to this autonomous run:

- **Option A (recommended): author the executor in its own reviewable PR
  first.** A dedicated `scripts/ml_step4/` runner implementing the contract
  end-to-end (split, F-2 labels, v4 features, LightGBM, validation-only
  threshold, single event-driven holdout, daily-portfolio-Sharpe, F-5
  provenance), **code-only, no execution**, reviewed by human + ChatGPT (and
  optionally a Fable 5 adversarial review of the harness). Once merged and
  reviewed, a **subsequent** first-run execution PR uses that reviewed executor
  — so the first real number comes from reviewed code, and its provenance chain
  is real.

- **Option B: explicitly authorise author-and-run in one PR, accepting the
  self-certification risk.** If the reviewers prefer, they may instruct this run
  to both author the executor and run it in a single PR, on the understanding
  that the resulting metrics come from a **newly-authored, not-yet-independently-
  reviewed** harness and must be treated as provisional until the mandated
  post-run human + ChatGPT review and recommended Fable 5 adversarial audit.

## Non-authorisation (this stop)

No ML Step 4 execution · no model trained · no holdout evaluated · no metrics
generated · no raw data / rows / files committed · no model binaries · no
personal paths · no environment dumps · no external disk / Google Drive / R2
access · no Phase C2 · no `730d_BA` · no `3650d_BA` · no production-readiness
claim · no Phase 9.X rehabilitation · Phase 9.16 not promoted/demoted.
