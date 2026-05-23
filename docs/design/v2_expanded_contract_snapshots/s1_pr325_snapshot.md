# S-1 Contract Snapshot — PR #325 / Phase 27.0d-β / C-se Origin

**Sentinel ID**: S-1
**Phase label**: Phase 27.0d-β
**Supplying PR**: GitHub PR #325
**Squash-merge commit SHA**: `999859fa6443c4a3b2d8e7f6a5c4b3d2e1f0a9b8` (short `999859f`)
**Source script at merge SHA**: `scripts/stage27_0d_s_e_regression_eval.py`
**Anchor role**: 1st anchor — C-se origin

This snapshot is created per the V2-expanded amendment §A.0 / §A.4 contract; its content is pinned at the merge-SHA and the harness loads it as immutable evidence.

---

## 1. Cell IDs and scorer identity

Source: `PR #325 @ 999859f :: scripts/stage27_0d_s_e_regression_eval.py:491-501` (`build_s_e_cells`)

| Cell ID | Picker | Score type | Scorer-family identity |
|---|---|---|---|
| **C-se** | `S-E(regressor_pred)` | `s_e` | **S-E LightGBM regressor**; symmetric Huber α=0.9; sample_weight=1; pipeline = `build_pipeline_lightgbm_regression_widened` (defined at `:308-350`) |
| **C-sb-baseline** | `S-B(raw_p_tp_minus_p_sl)` | `s_b_raw` | **S-B raw P(TP)−P(SL) multiclass head**; inherited from `stage26_0d.build_pipeline_lightgbm_multiclass_widened` |

S-B (multiclass head) and S-E (regressor) are NEVER conflated in the historical script and MUST remain distinct in any Stage 2/3 implementation.

## 2. Quantile family + selection rule

Source: `PR #325 @ 999859f :: scripts/stage27_0d_s_e_regression_eval.py:213` (`THRESHOLDS_QUANTILE_PERCENTS = stage26_0c.THRESHOLDS_QUANTILE_PERCENTS`); upstream `stage26_0c_l1_eval.py:168`

- **Quantile family**: `(5, 10, 20, 30, 40)` (percent values)
- **Selection rule**: top-q on per-row score
- **Val-selection sort key** (`PR #325 @ 999859f :: scripts/stage27_0d_s_e_regression_eval.py:980-984`):

```python
def _q_sort_key(r: dict) -> tuple:
    v = r["val"]
    s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
    return (s, v["annual_pnl"], v["n_trades"], -r["q_percent"])
```

Only `r["val"]` fields participate. No test field is accessed by the selection key.

## 3. Row-set / split rule

- **Split function**: `split_70_15_15` — imported from `stage25_0b_f1_volatility_expansion_eval` (per `PR #325 @ 999859f :: scripts/stage27_0d_s_e_regression_eval.py` imports). 70/15/15 train/val/test by chronological order.
- **Pair universe**: 20 pairs, ordered by `_build_pair_runtime(pair, days)` enumeration (`:1508`).
- **R7-A-clean row-set**: full historic; **Fix A** (introduced at #332 = S-2) is NOT yet present at #325; both C-se and C-sb-baseline share full R7-A-clean row-set.

## 4. Target (declared axis = scorer; target is invariant)

- **Target function**: `_compute_realised_barrier_pnl` (from `stage25_0b`) — triple-barrier realised PnL.
- **K_FAV = 1.5** (from `stage25_0b:88`)
- **K_ADV = 1.0** (from `stage25_0b:89`)
- **H_M1_BARS = 60** (from `stage25_0b:90`)
- **Entry**: long → ask_o; short → bid_o at signal_ts + 1 minute (D-1 bid/ask executable).

## 5. Threshold / verdict mapping

- **H1m**: `H1_MEANINGFUL_THRESHOLD = stage26_0c.H1_MEANINGFUL_THRESHOLD` (Spearman ≥ +0.30 for cell to count as meaningfully classifying)
- **H1m PASS at C-se**: reported `Spearman = +0.4381` per eval_report.md §13 at merge SHA
- **H2 FAIL at C-se**: realised Sharpe wrong-direction (val-selected q* test_sharpe -0.483 wrong direction)
- **Aggregate H-B4 ladder verdict**: `SPLIT_VERDICT_ROUTE_TO_REVIEW`

## 6. Drift tolerance

S-1 IS the 1st anchor; it defines the contemporaneous baseline link. No upstream anchor exists to compare against. For Stage 3, S-1's drift tolerance is the **standard control-drift tolerance** used to compare its reproduction at clean re-execution against the historic eval_report.md numerics:

- n_trades **±100**
- Sharpe **±5e-3**
- ann_pnl **±0.5%** of magnitude
- Spearman **±5e-3** (for the +0.4381 reproduction)

## 7. Historic compatibility classifications (from PR #358 companion review)

- **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE** — `_q_sort_key` reads only val fields; test fields appear only after `best_q_record = max(quantile_results, key=_q_sort_key)` selects (verified at PR #358 §A.0 review).
- **HISTORIC_DATA_IDENTITY_NOT_PROVABLE** — no merge-SHA recording of `data/m1_ba/` or `data/signals/` content SHA (verified at PR #358 §A.0 review; zero hits for `data_manifest / content_sha / source_sha / sha256.*data / hashlib.*data / m1_ba.*sha / file_sha / md5.*data` patterns).

## 8. Permitted later wording (under V2-expanded)

- Per V2-expanded amendment §A.3 (PR #358): per-sentinel display **MUST** be `CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY`.
- `HISTORIC_DATA_IDENTITY_PROVEN` is forbidden under current evidence.
- Forbidden aggregate wording (any of): "historical execution verified" / "historic verdict reproduced" / "prior verdict revalidated" / "historical negative verdict reproduction" / "tabular evidence reconfirmed".

## 9. Helper-source mapping (for Stage 2 import/port decision)

Per the V2-expanded amendment §A.4 + Stage 1 binding "snapshots must identify the exact historical script/function source", the following helpers are inlined/imported at S-1's merge SHA:

| Helper | Source script @ merge SHA | Line range | Stage 2 import/port decision (TBD) |
|---|---|---|---|
| D-1 realised-PnL implementation | `stage25_0b_f1_volatility_expansion_eval.py` (defines `_compute_realised_barrier_pnl`) | `:482-...` | TBD at Stage 2 |
| Pre-row PnL cache | `stage26_0b_l2_eval.py` (defines `precompute_realised_pnl_per_row`) | `:489-...` | TBD at Stage 2 |
| Split logic | `stage25_0b_f1_volatility_expansion_eval.py` (defines `split_70_15_15`) | `:365-...` | TBD at Stage 2 |
| Pair runtime construction | `stage27_0d_s_e_regression_eval.py` (inlined `_build_pair_runtime`) | `:1508-...` | TBD at Stage 2 |
| S-E scorer construction | `stage27_0d_s_e_regression_eval.py` (`build_pipeline_lightgbm_regression_widened`) | `:308-350` | TBD at Stage 2 |
| S-B scorer construction | `stage26_0d_r6_new_a_eval.py` (`build_pipeline_lightgbm_multiclass_widened`) | (via `stage26_0d` import) | TBD at Stage 2 |
| Quantile constant | `stage26_0c_l1_eval.py` (`THRESHOLDS_QUANTILE_PERCENTS`) | `:168` | TBD at Stage 2 |
| K_FAV / K_ADV / H_M1_BARS | `stage25_0b_f1_volatility_expansion_eval.py` | `:88-90` | TBD at Stage 2 |
| H1 thresholds | `stage26_0c_l1_eval.py` (`H1_WEAK_THRESHOLD` / `H1_MEANINGFUL_THRESHOLD`) | (constants) | TBD at Stage 2 |

Stage 1 does NOT port any of these helpers; Stage 2 (when authorised) will decide per snapshot whether to import from the merge-SHA script or port verbatim into the sentinel adapter.

## 10. Stage 1 declarations

- **NO formal verification executed.**
- **NO model fit performed.**
- **NO baseline reproduction asserted.**
- **NO V2-expanded outcome label emittable from this snapshot alone.**
- **A0-broad β remains halted.**

---

*End of S-1 contract snapshot for PR #325 / Phase 27.0d-β / `999859f`.*
