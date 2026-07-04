# ML Step 4 contract executor — implementation note (code-only, no run)

- **Document class:** short implementation note for a code-only, no-execution PR
- **Branch:** `feat/ml-step4-contract-executor-no-run`
- **Base:** master after PR #409 merge
- **Bound contract:** PR #407 pre-registration
  (`docs/design/phase_f_ml_step4_pre_registration.md`) as constrained by PR #408
  (`docs/design/ml_step4_365d_ba_execution_authorisation_plan.md`).
- **Bound epoch:** `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1` (`365d_BA`).

## Status

**`ML_STEP4_CONTRACT_EXECUTOR_IMPLEMENTED_NO_RUN`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## What this PR adds

A reviewed, deterministic, fail-closed executor/harness under `scripts/ml_step4/`
that can **later** run exactly the PR #407 / PR #408 contract, plus synthetic-only
tests under `tests/ml_step4/`. It **does not execute the real run**: it does not
read real `365d_BA` raw candle data, does not train a model, does not evaluate
the holdout, does not generate real ML metrics, does not write model binaries,
and does not create real execution evidence under `artifacts/ml_step4/365d_ba_v1/`.

### Modules (`scripts/ml_step4/`)

| Module | Responsibility |
| --- | --- |
| `contract.py` | Frozen champion config bound to committed conventions; deterministic `config_hash` / `feature_config_hash` / `model_config_hash`; fail-closed guards (non-LightGBM family, deployed `models/lgbm/` reuse, opt-in feature groups). |
| `inventory.py` | Resolve the committed PR-B.1 inventory (metadata only); verify 20 files + total bytes = 1,481,715,517; stream SHA-256/size for runtime files at execution; fail closed on missing/extra/mismatch/ambiguous. |
| `split.py` | Common cross-pair window from per-pair timestamp metadata; chronological 70/15/15; purge/embargo = horizon + 1 = 21 bars; fail closed on missing/inconsistent/non-deterministic timestamps. |
| `labels.py` | F-2 label/PnL adapter wrapping the committed `scripts/traded_direction_pnl.py`: traded-direction PnL, spread embedded once, SL-first tie, timeout mark-to-market, B-2 3-class label rule. |
| `thresholds.py` | Validation-only threshold selection from `{0.35, 0.40, 0.45}`; records rejected variants; never inspects holdout; deterministic ties. |
| `simulator.py` | Event-driven **max 1 open position per pair**; ignores overlapping signals; deterministic order; per-trade metadata for daily aggregation. |
| `metrics.py` | Daily portfolio PnL; **daily portfolio Sharpe from the daily series** (never per-trade); max equity drawdown on the daily equity curve; pair concentration (trade + positive-PnL share); turnover; coverage; concurrency; cost sensitivity at 0.0/0.5/1.0 pip. |
| `acceptance.py` | Evaluates the §10 criteria; emits exactly one allowed status; insufficient sample / missing provenance are hard `ML_STEP4_RUN_INVALID_*` triggers; honest below-threshold → `..._DOES_NOT_MEET_...`. |
| `evidence.py` | Metadata-only writer + dedicated ml_step4 scrubber (allows metric keys; rejects raw rows / personal paths / credentials / env dumps / Google Drive links / R2 keys); deterministic JSON ordering; **guard refuses to write real execution evidence** in a no-run context. |
| `run_365d_ba.py` | CLI `--dry-run` entrypoint: validates wiring, reports the 16 pre-execution hard gates as "required at execution / not performed", confirms no execution. No non-dry-run path is wired. |

### Dry-run

```
python -m scripts.ml_step4.run_365d_ba --dry-run
```

Emits a scrub-clean metadata summary (statuses, epoch, the three deterministic
hashes, inventory metadata resolution, hard-gate checklist) and the flags
`execution_performed=false`, `raw_data_read=false`, `model_trained=false`,
`holdout_evaluated=false`, `evidence_written=false`. Invoking without `--dry-run`
fails closed (real execution is not available in this build).

## What remains for the future execution PR

The heavy execution steps are intentionally **not** implemented as an invokable
real run here: reading real `365d_BA` candles, causal feature generation
(`FEATURE_VERSION v4` base), bulk B-2 label generation, from-scratch LightGBM
training, prediction, and wiring the above modules into a single guarded
`execute()` path that writes the eight metadata-only evidence files. That path,
its provenance capture, and its first real numbers require a **separate,
explicitly-authorised execution PR** (and the mandated post-run human + ChatGPT
review, with a recommended Fable 5 adversarial post-run audit before any
positive result is interpreted).

## Non-authorisation

No ML Step 4 execution; no real raw data read; no model trained; no backtest;
no real ML metrics; no model binaries; no real execution evidence; no external
disk / Google Drive / R2 access; no Phase C2; no `730d_BA`; no `3650d_BA`; no
production-readiness claim; no Phase 9.X rehabilitation; Phase 9.16 not
promoted/demoted.
