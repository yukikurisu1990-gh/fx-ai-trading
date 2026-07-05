# ML Step 4 `365d_BA` corrected second first-run execution report

- **Document class:** corrected-run execution record (exactly one re-measurement
  of the PR #421 invalid measurement; falsification / baseline per PR #413).
  Reports results; changes no contract.
- **Branch:** `run/ml-step4-365d-ba-v1-corrected-second-run`
- **Base:** master `6fbb178280b46fd8f158ff029f328721c465274d` (after PR #424 merge).
- **Run code SHA:** `6fbb178280b46fd8f158ff029f328721c465274d` (the merged corrected
  code; recorded in the manifest and encoded in the evidence directory name).

## 1. Executive summary

The single governance-approved **corrected second first-run** executed exactly
once on the checksum-verified `365d_BA` epoch, under the unchanged PR #407
contract, with the already-merged PR #423 per-pair pip-size fix as the sole
substantive delta from PR #421. All 12 tooling hard gates passed (20 files /
1,481,715,517 bytes verified) and the per-pair pip map resolved fail-closed
(20 pairs; 6 `_JPY`→`0.01`; 14 non-JPY→`0.0001`) before any training. 20
per-pair LightGBM 3-class classifiers were trained from scratch on ~5.10M
labeled rows; the threshold was selected on the validation window only; the
frozen holdout was evaluated **exactly once**.

**Result: `ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_DOES_NOT_MEET_PREREGISTERED_CRITERIA`
(DOES_NOT_MEET) — now with valid, correctly-scaled metrics.** The post-cost
expectancy is **−3.49 pips/trade** (was an invalid −127.75 under the 100× JPY
pip-scale bug); max equity drawdown is **2.82× notional** (was 103.25×). Four
of the seven gating criteria fail decisively; three now pass (both concentration
criteria + coverage). No production readiness is claimed; no rerun or tuning was
performed.

Run-level status: **`ML_STEP4_365D_BA_CORRECTED_SECOND_RUN_COMPLETED`** ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

## 2. Governance approval basis

Explicitly approved by the human + ChatGPT governance decision as **exactly one
corrected second first-run attempt on the same frozen `365d_BA` holdout**, on
the recorded basis that: PR #421 was procedurally clean but invalid due to a
proven pip-unit implementation bug (PR #422); no tuning and no feedback loop
occurred; the invalid metrics informed no threshold/feature/model/split/label/
acceptance change; PR #423 fixed only the pip-size unit conversion; PR #424
confirmed the fix acceptable. This is a re-measurement of an invalid
measurement, not a second optimisation attempt.

## 3. Scope and non-authorisation

This run: read the 20 checksum-verified `365d_BA` files locally; computed
`FEATURE_VERSION v4` **base** features (39 cols; MTF/vol/moments excluded);
generated B-2 bid/ask triple-barrier labels solely through
`scripts/ml_step4/labels.py`; converted PnL per pair via
`data_adapter.pip_size_for`; trained LightGBM per pair from scratch; selected
one threshold from `{0.35, 0.40, 0.45}` on validation only; evaluated the frozen
holdout once; wrote eight metadata-only evidence files. It did **not**: change
any contract; tune anything; rerun; expand the dataset; use `730d_BA`/`3650d_BA`;
start Phase C2; access Google Drive or R2; write model binaries; commit raw
data; or claim production/paper/live readiness. **No `scripts/ml_step4/` code,
test, or contract file was modified in this PR.**

## 4. Exact command run

```
python -m scripts.ml_step4.execute_365d_ba --first-run-preflight        # gate report, no training
python -m scripts.ml_step4.execute_365d_ba --execute-first-run-365d-ba  # THE one corrected run
```
The repository exposes no separate "corrected-run" flag; the corrected code on
master is the executed identity, so the existing explicit first-run command is
the correct invocation. Run **exactly once**. No execution command was run more
than once; the holdout was evaluated once.

## 5. Code SHA / PR head SHA

Run code SHA (manifest): `6fbb178280b46fd8f158ff029f328721c465274d` — identical
to the base master tip after PR #424 (no code commit precedes the run on this
branch). The evidence directory encodes it as `corrected_second_run_6fbb178280b4`
(see §19). The PR head SHA is the later evidence/report commit.

## 6. Gate results

All 12 ordered pre-execution tooling hard gates **PASS**: (1) explicit first-run
mode; (2) code SHA recorded; (3) config/feature/model hashes recorded;
(4) inventory resolved; (5) **all 20 checksums verified**; (6) feature contract
v4-base-only (39 cols); (7) split policy (purge 21); (8) label contract;
(9) model contract; (10) threshold contract `{0.35,0.40,0.45}`; (11) evidence
path guarded; (12) scrubber ready. In addition, the governance per-pair pip-size
gates are enforced by the run body's fail-closed `pip_size_map` resolution
**before training**: 20 pair mappings resolved; exactly six `_JPY` pairs →
`0.01`; all 14 non-JPY pairs → `0.0001`; `global_pip_size_authoritative_for_all_pairs
= false`.

## 7. Inventory verification

Expected/observed **20 files**, **1,481,715,517 bytes**; per-file SHA-256 + size
re-verified against the committed PR-B.1 inventory immediately before
consumption; `all_match = true`. Provider:
`scripts.ml_step4.data_adapter.Real365dBaProvider.v1`.

## 8. Per-pair pip-size verification

Recorded in the manifest and the leakage/provenance report:
`pip_size_convention = "0.01 if pair endswith _JPY else 0.0001"`;
`global_pip_size_authoritative_for_all_pairs = false`; `pip_size_by_pair` has
**20 entries** — the six JPY crosses (`AUD_JPY, CHF_JPY, EUR_JPY, GBP_JPY,
NZD_JPY, USD_JPY`) → `0.01`; the fourteen non-JPY pairs → `0.0001`. Per-pair
diagnostics carry `pip_size` + `pip_size_kind`.

## 9. Feature wiring identity

`scripts.train_lgbm_models._add_features + _add_upper_tf_features` →
**39 v4-base columns** (15 M1 + 24 M5/M15/H1 upper-TF); `_add_mtf_features`
**not called**; no MTF column present. `feature_config_hash = bff146e4ba54…`
(unchanged from PR #421).

## 10. Label contract identity

`scripts.ml_step4.labels.v1` — B-2 bid/ask triple-barrier, traded-direction PnL
via the committed F-2 helper, SL-first tie, timeout mark-to-market; horizon 20
M1 bars; eligibility `range(n − horizon − 1)` (PR #419 B-2). Sole label/scoring
source. **The only change vs PR #421 is that the per-pair pip size is now
supplied to `bulk_labels` (PR #423); barrier geometry is unchanged.**

## 11. Model contract identity

LightGBM 3-class classifier, `_LGBM_PARAMS = {learning_rate 0.05, num_leaves 31,
verbose −1}`, `n_estimators 200`, from scratch, no deployed reuse, no model
binary persisted. `model_config_hash = bc27cfa39ea3…` (unchanged). All 20 models
trained with `classes_ = [0,1,2]`.

## 12. Threshold contract identity

Candidates `{0.35, 0.40, 0.45}`; validation-only selection; tie rule prefer 0.40
else smallest; `threshold_config_hash = fd6877039bce…` (unchanged).

## 13. Split metadata

Common cross-pair window (from inventory metadata, deterministic):
**2025-04-25T17:09:00Z → 2026-04-24T20:58:00Z** — exactly the contract §5 bounds.
Chronological 70/15/15; purge/embargo = horizon+1 = 21 M1 bars. Holdout:
**2026-03-01T05:59:39Z → 2026-04-24T20:58:00Z** (final 15%). Holdout evaluated
exactly once. (Identical to PR #421 — labels/splits are pip-agnostic.)

## 14. Training metadata

20 pairs trained per-pair from scratch; **5,100,657** labeled training rows
(1,123,683 validation-labeled; 1,143,551 holdout-labeled). Deterministic data
ordering; **no `random_state`** (the frozen trainer convention defines none —
recorded honestly); reproducibility `bounded_not_bitwise_guaranteed`.
Python 3.12.10; lightgbm 4.6.0, numpy 2.4.4, pandas 3.0.2, scikit-learn 1.8.0.

## 15. Validation threshold result

Selected: **0.45**. Rejected variants (validation daily portfolio Sharpe):
0.35 → −16.21 (n=9,475); 0.40 → −16.21 (n=7,209). All three validation Sharpes
are strongly negative; 0.45 is the least-negative and was selected — the same
selection as PR #421, now on correctly-scaled PnL (the selection outcome is
robust to the pip correction).

## 16. Holdout evaluation result

Frozen holdout evaluated **once** with threshold 0.45. Portfolio: **8,082
trades** across **48 UTC trading days** (~1,143,551 holdout-labeled rows across
20 pairs). Trade count, day count, and threshold are identical to PR #421 —
because the correction changed only per-trade PnL magnitude, not which bars are
labeled or which trades fire.

## 17. Metrics summary (holdout)

| Metric | Value | Criterion | Pass |
| --- | --- | --- | --- |
| post-cost expectancy (0.5 pip) | **−3.49 pips/trade** | > 0 | ❌ |
| daily portfolio Sharpe (ann.) | **−18.91** | ≥ 0.8 | ❌ |
| max equity drawdown | **2.82× notional** | ≤ 0.15 | ❌ |
| turnover | **168.4 trades/day** | ≤ 40 | ❌ |
| pair trade concentration | 0.289 | ≤ 0.40 | ✅ |
| pair positive-PnL concentration | **0.230** | ≤ 0.50 | ✅ |
| cost sensitivity @ 1.0 pip | **−3.99 pips** | ≥ 0 | ❌ |
| daily coverage | 1.00 | ≥ 0.60 | ✅ (not gating alone) |
| win rate (diagnostic) | 7.83% | — | — |

Cost sensitivity (expectancy pips): 0.0 → **−2.99**; 0.5 → **−3.49**; 1.0 →
**−3.99** (cost cell applied exactly once — PR #418 B-1; exact 0.5 steps,
unshifted). avg win **+6.38** / avg loss **−4.33** pips. **Four of seven gating
criteria fail; two concentration criteria now pass** (both improved because JPY
no longer dominates PnL). Per-pair PnL (corrected): JPY per-trade **−4.45**
pips vs non-JPY **−3.04** pips — same order of magnitude (the 100× JPY inflation
is eliminated); JPY loss share **40.5%** (was 98.4% invalid), ≈ its 31.8% trade
share.

## 18. Acceptance status

`ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_DOES_NOT_MEET_PREREGISTERED_CRITERIA`
(closed vocabulary; honest below-threshold). Diagnostics
(`NON_DECISION_EXPLORATORY`) did not influence acceptance. Provenance complete.

## 19. Evidence files written

`artifacts/ml_step4/365d_ba_v1/corrected_second_run_6fbb178280b4/` (metadata-only;
a **new versioned directory**). The tooling emitted the 8 payloads under
`first_run_6fbb178280b4` (its `_run_dir` names by code SHA, which already differs
from PR #421's `181dc52f3a08` and so never overwrites it); the eight files were
relocated **verbatim** to the `corrected_second_run_…` name for unambiguous
labeling — bookkeeping only, no payload byte changed, no code change (the dir
name is not embedded in any payload). Eight files: run manifest, pre-consumption
checksum report, split report, model config report, metrics report, cost
sensitivity report, leakage/provenance report, acceptance/failure decision
report. **All scrub-clean** (verified via `evidence.assert_clean`); no raw rows,
paths, env dumps, credentials, Drive/R2 links, or binaries. The PR #409
stop-evidence 8 files and PR #421 invalid-evidence 8 files
(`first_run_181dc52f3a08/`) are **untouched**.

## 20. Deviations / failures

- **No deviation from the contract; no code change.** All gates passed; one run;
  no rerun; no tuning; provenance complete; holdout evaluated once.
- **Observation (not a rerun trigger):** the corrected primary metric (daily
  portfolio Sharpe −18.91) is more negative than PR #421's invalid −13.69. That
  is expected: PR #421's Sharpe was computed over 100×-inflated JPY daily
  variance — a meaningless quantity — whereas this is the valid measure. The
  magnitudes are not comparable; both are strongly negative.

## 21. Comparison to invalid PR #421 evidence (pip-size correction only)

Limited strictly to explaining the pip-size correction (no other contract
element changed):

| Quantity | PR #421 (invalid) | Corrected (valid) | Cause |
| --- | --- | --- | --- |
| expectancy pips/trade (0.5) | −127.75 | −3.49 | JPY 100× inflation removed |
| max equity drawdown | 103.25× notional | 2.82× notional | same |
| JPY per-trade PnL | −358.78 | −4.45 | JPY pip 0.01 (was 0.0001) |
| non-JPY per-trade PnL | −3.18 | −3.04 | essentially unchanged (never affected) |
| JPY share of loss | 98.4% | 40.5% | JPY de-inflated to its trade share |
| trade count / holdout days | 8,082 / 48 | 8,082 / 48 | identical — labels/trades pip-agnostic |
| selected threshold | 0.45 | 0.45 | selection robust to the correction |

The identical trade set + threshold with a ~100× change only in per-trade
magnitude confirms PR #422's diagnosis: labels/training/trade-firing were
pip-agnostic; only PnL scale was corrupted, and only PnL scale changed.

## 22. Non-authorisation statements

No production readiness; no paper/live trading; no rerun; no tuning; no contract
change; no threshold/feature/model/acceptance/label/split/epoch change; no
dataset expansion; no `730d_BA`/`3650d_BA`; no Phase C2; no Google Drive/R2; no
model binaries; no raw data committed. `PRODUCTION_READINESS_NOT_CLAIMED`
remains binding.

## 23. Recommendation for post-run review

Proceed to the mandated **human + ChatGPT post-run review** and a **Fable 5
adversarial post-run audit** confirming provenance/validity of this corrected
measurement. Per the pre-stated interpretation for a DOES_NOT_MEET with clean
provenance: accept this as the **valid corrected measurement**; do not rerun; do
not tune; if the post-run audit validates the evidence, the **M1 flagship
first-run question can be closed** with honest evidence — the M1 family does not
clear the pre-registered criteria on the `365d_BA` holdout, exactly as the
PR #413 frame anticipated. Any subsequent direction (e.g. the PR #413 pivot to
longer horizons / cost-hurdle-aware targets) is a separate, separately-authorised
decision — not started here.
