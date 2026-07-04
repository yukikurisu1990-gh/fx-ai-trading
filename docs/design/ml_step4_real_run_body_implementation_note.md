# ML Step 4 real-run body — implementation note (code-only, fixture-only, no run)

- **Document class:** short implementation note for a code-only, no-real-run PR.
- **Branch:** `feat/ml-step4-real-run-body-no-run`
- **Base:** master after PR #416 merge.
- **Bound contracts:** PR #407 pre-registration + PR #408 execution-authorisation,
  under the PR #413 falsification/baseline frame; PR #415 wiring; PR #416 source
  audit (`…_ACCEPTABLE_FOR_REAL_RUN_BODY_IMPLEMENTATION_REVIEW` + the 6-item
  required-in-body checklist, all bound here).

## Status

**`ML_STEP4_REAL_RUN_BODY_IMPLEMENTED_NO_RUN`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## What this PR adds

The guarded run body: the full future production sequence assembled into one
fail-closed path (`scripts/ml_step4/body.py::guarded_run_body`), exercisable
**only** with synthetic fixtures. `mode="real"` — and any non-fixture provider —
refuses with `ExecutionRefusedError`; no environment variable can enable real
data. The fixture rehearsal runs **end-to-end in ~0.2 s** and emits all eight
metadata-only evidence payloads (scrub-gated) into a non-protected temporary
path; the repo-root guard refuses the real evidence directory, and PR #409 stop
evidence is verified untouched by tests.

### New modules
| Module | Responsibility |
| --- | --- |
| `data_adapter.py` | `FixtureDataProvider` (deterministic seeded synthetic M1 bars; SHA-256 pair mixing — cross-process stable, no `hash()` randomisation) + `RealDataProviderRefused` (every data access raises; future execution PR must replace it with a checksum-re-verifying real provider). |
| `features.py` | Fixture feature builder (pure-Python, strictly causal, deterministic — explicitly labeled NOT production v4) + `feature_binding()` provenance (contract v4-base descriptor + hash) + `load_production_feature_builder()` lazy seam bound by identity to the committed trainer bulk builders (`_add_features`/`_add_upper_tf_features`/`_FEATURE_COLS`) — never invoked in this build. |
| `trainer.py` | `train_lgbm` from-scratch wrapper pinned to the frozen convention (`{lr 0.05, num_leaves 31, verbose −1}`, `n_estimators 200`; no model_path argument — deployed reuse structurally impossible; verified once locally on tiny synthetic data, optional/skippable in CI) + deterministic `FixtureModelStub` for rehearsals. |
| `manifest.py` | Runtime provenance capture: **actual git code SHA** (fail-closed if unrecordable), Python version, package versions (numpy/pandas/lightgbm/scikit-learn via importlib.metadata — never an env dump), runtime seeds, `bounded_not_bitwise_guaranteed`; completeness fail-closed; never touches `model_config_hash`. |
| `body.py` | The guarded sequence: provider → causal features → **bulk B-2 labels + exit timing single-sourced from `labels.py`** → authoritative integer split indices → training → **validation-only** threshold selection over exactly {0.35, 0.40, 0.45} → **single** event-driven holdout evaluation (max 1 position/pair, occupancy = resolved barrier/timeout exit) → `metrics.compute_all` (contract notional) → acceptance evaluation → labeled diagnostics → eight scrubbed evidence payloads. |

### Extended modules
- `labels.py`: `atr14` (causal, min_periods 14), `bulk_labels` (per-bar B-2
  3-class labels + per-direction traded PnL + exit offsets — reuses the reviewed
  primitives; the ONLY bulk label/scoring route), `exit_window_offset`
  (SL-first exit timing).
- `split.py`: **integer-arithmetic boundaries** via exact `Fraction` math
  (item 6) — emitted indices equal the exact-rational floor for every n and are
  the authoritative record the body consumes.
- `metrics.py`: `compute_all` notional now **defaults to the contract constant
  and fails closed on any conflicting value** (item 1).
- `execute_365d_ba.py`: new `--fixture-e2e` (exit 0, path-free scrub-clean
  summary); `--preflight` unchanged (exit 0); `--execute`/no-flag still refuse
  (exit 2).

## Required-in-body checklist (PR #416) — all six bound

1. **maxDD notional:** `compute_all` defaults to `FIXED_NOTIONAL_EQUITY_PIPS`
   (10,000); conflicting caller value fails closed in both `metrics` and
   `body.evaluate_portfolio`; recorded in the run manifest.
2. **Single-source labels/scoring:** all labels, PnL, and exit timing come from
   `labels.bulk_labels`; adapter failure propagates (monkeypatch test proves no
   catch-and-continue); a source test proves no barrier math exists in the body;
   `LABEL_CONTRACT_ID` recorded in the leakage/provenance payload.
3. **UTC coverage denominator:** distinct UTC calendar dates in the holdout
   window (the default rehearsal genuinely spans 2 dates); naive datetimes fail
   closed; offset timezones convert to UTC.
4. **Manifest:** real 40-char git SHA (fail-closed on git failure), seeds,
   package versions, Python version, reproducibility level; incomplete manifest
   fails closed; `model_config_hash` untouched.
5. **Diagnostics labeler invoked in the pipeline:** feature importance,
   calibration, per-threshold validation curves, session contribution, etc. are
   wrapped `NON_DECISION_EXPLORATORY` inside the metrics evidence payload,
   separated from decision metrics; the acceptance path is asserted
   exploratory-free.
6. **Split hardening:** exact integer arithmetic (previously-divergent sizes
   2690/5280/5650 now equal `(70·n)//100`); the body consumes the emitted
   indices, never recomputes.

## Fixture rehearsal design

Deterministic seeded LCG random-walk bars (2 pairs × 6,000 M1 bars ≈ 4.2 days;
holdout tail crosses a UTC date boundary), stub model (no learning — fixed
squash of one feature), full pipeline to eight evidence payloads, each carrying
`fixture_rehearsal/synthetic_only/real_run=false` banners. Deterministic across
processes (SHA-256 pair mixing; verified over 3 fresh interpreter runs). The
rehearsal's acceptance output is a **dry output** (closed vocabulary, honest
`DOES_NOT_MEET` on the random-walk fixture) and is explicitly non-decision —
it must never be cited as an ML Step 4 result.

## Remaining limitations (for the future execution PR)

- The **real data provider** (with immediate pre-consumption checksum
  re-verification against the PR-B.1 inventory) is intentionally absent.
- The **production v4-base bulk feature path** is bound by identity to the
  committed trainer builders but not invoked; the execution PR wires and runs
  it on real data (heavy pandas/lightgbm path).
- Real LightGBM training/prediction at 20-pair scale, the real holdout
  evaluation, and real evidence under `artifacts/ml_step4/365d_ba_v1/` all
  remain gated behind the separately-authorised first-run execution PR.
- The fixture feature builder is a plumbing stand-in, NOT the production v4
  set — labeled as such in every manifest.

## Non-authorisation

No real `365d_BA` read; no real checksums computed; no real training; no real
backtest; no real holdout evaluation; no real ML metrics; no real execution
evidence (protected dir verified untouched); no model binaries (fixture models
in-memory/temp only); no external disk / Google Drive / R2; no Phase C2; no
`730d_BA`/`3650d_BA`; no production-readiness claim.

## Next gate

Fable 5 source audit of this run body → then the **separately-authorised
first-run execution PR** (real provider + production feature wiring + real
mode enablement) under the PR #413 falsification/baseline frame → mandated
post-run review.
