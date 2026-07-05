# ML Step 4 `365d_BA` first-run execution report

- **Document class:** first-run execution record (one real run; falsification /
  baseline measurement per PR #413). Reports results; changes no contract.
- **Branch:** `run/ml-step4-365d-ba-v1-first-run`
- **Base:** master after PR #420 merge.
- **Run code SHA:** `181dc52f3a08fa350420450cb51a3571ef150ac3` (the committed
  implementation; recorded in the manifest and the evidence directory name).

## 1. Executive summary

The single authorised ML Step 4 first run executed exactly once on the
checksum-verified `365d_BA` epoch under the PR #407 contract. All 12
pre-execution hard gates passed (20 files / 1,481,715,517 bytes verified). The
run trained 20 per-pair LightGBM 3-class classifiers from scratch on ~5.10M
labeled training rows, selected the confidence threshold on the validation
window only, and evaluated the frozen holdout **exactly once**.

**Result: `ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_DOES_NOT_MEET_PREREGISTERED_CRITERIA`.**
This is the expected, valid falsification/baseline outcome. Six of the seven
gating criteria fail decisively (only pair-trade-concentration passes); the M1
flagship family is closed with honest evidence. **No production readiness is
claimed. No rerun or tuning was performed.**

Run-level status: **`ML_STEP4_365D_BA_FIRST_RUN_COMPLETED`** ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

## 2. Scope and non-authorisation

This run: read the 20 checksum-verified `365d_BA` files locally; computed
`FEATURE_VERSION v4` **base** features (39 cols; MTF/vol/moments excluded);
generated B-2 bid/ask triple-barrier labels solely through
`scripts/ml_step4/labels.py`; trained LightGBM per pair from scratch; selected
one threshold from `{0.35, 0.40, 0.45}` on validation only; evaluated the frozen
holdout once; wrote eight metadata-only evidence files. It did **not**: change
any contract; tune anything; rerun; expand the dataset; use `730d_BA`/`3650d_BA`;
start Phase C2; access Google Drive or R2; write model binaries; commit raw
data; or claim production/paper/live readiness.

## 3. Exact command run

```
python -m scripts.ml_step4.execute_365d_ba --execute-first-run-365d-ba
```
(preceded by `--first-run-preflight` for the Phase 2 gate report). Run once.

## 4. Code SHA / PR head SHA

Run code SHA (manifest): `181dc52f3a08fa350420450cb51a3571ef150ac3`. The PR head
SHA is the later evidence commit; the *run* was produced by the implementation
commit above (the evidence directory is `first_run_181dc52f3a08`).

## 5. Gate results

All 12 ordered pre-execution hard gates **PASS**: (1) explicit first-run mode;
(2) code SHA recorded; (3) config/feature/model hashes recorded; (4) inventory
resolved; (5) **all 20 checksums verified**; (6) feature contract v4-base-only
(39 cols); (7) split policy (purge 21); (8) label contract; (9) model contract;
(10) threshold contract `{0.35,0.40,0.45}`; (11) evidence path guarded;
(12) scrubber ready.

## 6. Inventory verification

Expected/observed **20 files**, **1,481,715,517 bytes**; per-file SHA-256 + size
re-verified against the committed PR-B.1 inventory immediately before
consumption; `all_match = true`. Provider:
`scripts.ml_step4.data_adapter.Real365dBaProvider.v1`.

## 7. Feature wiring identity

`scripts.train_lgbm_models._add_features + _add_upper_tf_features` →
**39 v4-base columns** (15 M1 + 24 M5/M15/H1 upper-TF); `_add_mtf_features`
**not called**; no MTF column present (asserted). `feature_config_hash =
bff146e4ba54…`. Contract note: the trainer's deployed `_FEATURE_COLS` (45)
bundles the opt-in MTF group; PR #407 §4 requires v4 **base** only, so the
first run uses the base-39 and excludes MTF.

## 8. Label contract identity

`scripts.ml_step4.labels.v1` — B-2 bid/ask triple-barrier, traded-direction PnL
via the committed F-2 helper, SL-first tie, timeout mark-to-market; horizon 20
M1 bars; eligibility `range(n − horizon − 1)` (PR #419 B-2). Sole label/scoring
source.

## 9. Model contract identity

LightGBM 3-class classifier, `_LGBM_PARAMS = {learning_rate 0.05, num_leaves 31,
verbose −1}`, `n_estimators 200`, from scratch, no deployed reuse, no model
binary persisted. `model_config_hash = bc27cfa39ea3…` (unchanged from PR #412).
All 20 models trained with `classes_ = [0,1,2]`.

## 10. Threshold contract identity

Candidates `{0.35, 0.40, 0.45}`; validation-only selection; tie rule prefer
0.40 else smallest; `threshold_config_hash = fd6877039bce…`.

## 11. Split metadata

Common cross-pair window (from inventory metadata, deterministic):
**2025-04-25T17:09:00Z → 2026-04-24T20:58:00Z** — exactly the contract §5 bounds.
Chronological 70/15/15; purge/embargo = horizon+1 = 21 M1 bars. Holdout:
2026-03-01T05:59:39Z → 2026-04-24T20:58:00Z (final 15%). Holdout evaluated
exactly once.

## 12. Training metadata

20 pairs trained per-pair from scratch; ~5,100,657 labeled training rows total.
Deterministic data ordering; **no `random_state`** (the frozen trainer
convention defines none — recorded honestly); reproducibility
`bounded_not_bitwise_guaranteed`. Python 3.12.10; lightgbm 4.6.0, numpy 2.4.4,
pandas 3.0.2, scikit-learn 1.8.0.

## 13. Validation threshold result

Selected: **0.45**. Rejected variants (validation daily portfolio Sharpe):
0.35 → −14.26 (n=9,475); 0.40 → −13.41 (n=7,209). All three validation Sharpes
are strongly negative; 0.45 is the least-negative and was selected.

## 14. Holdout evaluation result

Frozen holdout evaluated **once** with threshold 0.45. Portfolio: **8,082
trades** across **48 UTC trading days** (~1,143,551 holdout-labeled rows across
20 pairs).

## 15. Metrics summary (holdout, 0.5 pip cell)

| Metric | Value | Criterion | Pass |
| --- | --- | --- | --- |
| post-cost expectancy | **−127.75 pips/trade** | > 0 | ❌ |
| daily portfolio Sharpe (ann.) | **−13.69** | ≥ 0.8 | ❌ |
| max equity drawdown | **103.25× notional** | ≤ 0.15 | ❌ |
| turnover | **168.4 trades/day** | ≤ 40 | ❌ |
| pair trade concentration | 0.289 | ≤ 0.40 | ✅ |
| pair positive-PnL concentration | 0.550 | ≤ 0.50 | ❌ |
| cost sensitivity @ 1.0 pip | −128.25 pips | ≥ 0 | ❌ |
| daily coverage | 1.00 | ≥ 0.60 | ✅ (not gating alone) |
| win rate (diagnostic) | 7.8% | — | — |

Cost sensitivity (expectancy pips): 0.0 → −127.25; 0.5 → −127.75; 1.0 → −128.25
(cost cell applied exactly once — PR #418 B-1; cells unshifted). **Six of seven
gating criteria fail.**

## 16. Acceptance status

`ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_DOES_NOT_MEET_PREREGISTERED_CRITERIA`
(closed vocabulary; honest below-threshold). Diagnostics
(`NON_DECISION_EXPLORATORY`) did not influence acceptance.

## 17. Evidence files written

`artifacts/ml_step4/365d_ba_v1/first_run_181dc52f3a08/` (metadata-only; a **new
versioned directory** — the PR #409 stop-evidence 8 files in the parent dir are
untouched): run manifest, pre-consumption checksum report, split report, model
config report, metrics report, cost sensitivity report, leakage/provenance
report, acceptance/failure decision report. All scrub-clean; no raw rows, paths,
env dumps, credentials, Drive/R2 links, or binaries.

## 18. Deviations / observations

- **No deviation from the contract.** All gates passed; one run; no rerun; no
  tuning; provenance complete.
- **Observation for the post-run audit (not a rerun trigger):** the magnitude
  is far more negative than the archived honest baselines (~−0.2…−0.5 Sharpe).
  Expectancy −127.75 pips/trade with a **7.8% win rate** implies the classifier
  is systematically adverse-directional on this holdout and/or that
  traded-direction timeout mark-to-market on the wrong side accumulates large
  losses (plausibly dominated by JPY crosses where pip size magnifies pip-space
  PnL). Per the one-shot discipline this is recorded, **not** patched or rerun —
  it is exactly what the mandated adversarial post-run audit must investigate
  (e.g., class-imbalance/argmax behavior, per-pair pip normalisation of the
  MTM, whether the 3-class argmax is an appropriate trade rule).

## 19. Non-authorisation statements

No production readiness; no paper/live trading; no rerun; no tuning; no contract
change; no threshold/feature/model/acceptance change; no dataset expansion; no
`730d_BA`/`3650d_BA`; no Phase C2; no Google Drive/R2; no model binaries; no raw
data committed.

## 20. Recommendation for post-run review

Proceed to the mandated **human + ChatGPT post-run review** and the recommended
**Fable 5 adversarial post-run audit** before interpreting the result further.
The valid conclusion at this gate: **the M1 flagship family does not clear the
pre-registered criteria on the `365d_BA` holdout** — closing the M1 question
with honest evidence, exactly as the PR #413 frame anticipated. The post-run
audit should (a) confirm the run's validity and the extreme-magnitude
observation in §18, then (b) authorise the PR #413 pivot to longer horizons
(M15/H1/H4), cost-hurdle-aware targets, and empirical-spread work. **No rerun of
this configuration; no tuning; no next experiment is started here.**
