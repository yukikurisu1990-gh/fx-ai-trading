# S-2 Contract Snapshot — PR #332 / Phase 27.0f-β / R7-C + Fix A Row-set Isolation

**Sentinel ID**: S-2
**Phase label**: Phase 27.0f-β
**Supplying PR**: GitHub PR #332
**Squash-merge commit SHA**: `ad673b4a1c9e2d8f7a6b5c4d3e2f1a0b9c8d7e6f` (short `ad673b4`)
**Source script at merge SHA**: `scripts/stage27_0f_s_e_r7_c_regime_eval.py`
**Anchor role**: 2nd anchor — C-se-r7a-replica + **Fix A row-set isolation introducer**

---

## 1. Cell IDs and scorer identity

Source: `PR #332 @ ad673b4 :: scripts/stage27_0f_s_e_r7_c_regime_eval.py:656-...` (`build_s_e_r7_c_cells`)

| Cell ID | Picker | Score type | Scorer-family identity | Row-set policy |
|---|---|---|---|---|
| **C-sb-baseline** | `S-B(raw_p_tp_minus_p_sl)` | `s_b_raw` | S-B raw P(TP)−P(SL) multiclass head (inherited from stage26_0d) | full R7-A-clean (Fix A retains) |
| **C-se-r7a-replica** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor (inherited from stage27_0d S-1 backbone) | full R7-A-clean (Fix A retains) |
| **C-se-rcw** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor on R7-A + R7-C-extended features | **R7-C drop only on this cell** (Fix A) |

**Fix A row-set isolation**: per PR #332 commit message + `eval_report.md §3` at merge SHA, R7-C feature drops apply to `C-se-rcw` only; C-sb-baseline + C-se-r7a-replica retain the full R7-A-clean row-set.

## 2. Quantile family + selection rule

Same as S-1: quantile family `(5, 10, 20, 30, 40)`; top-q on per-row score; val-selection via `_q_sort_key` at `PR #332 @ ad673b4 :: scripts/stage27_0f_s_e_r7_c_regime_eval.py:1461-1465` reads only val fields.

## 3. Row-set / split rule

- **Split function**: `split_70_15_15` (inherited; same source as S-1).
- **Pair universe**: 20 pairs.
- **Declared axis**: row-set (Fix A row-set isolation). Per-cell row counts MUST be reproduced at clean re-execution within tolerance.

## 4. Target / declared axis

- **Axis**: R7-C regime/context feature widening + Fix A row-set isolation.
- **Target**: inherited triple-barrier realised PnL (K_FAV=1.5 / K_ADV=1.0 / H_M1=60) — unchanged from S-1.
- **D-1 entry**: long ask_o / short bid_o.

## 5. Threshold / verdict mapping

- **H-B6 4-outcome ladder**: introduced at PR #332 for the R7-C axis.
- **Per-cell verdict at C-se-rcw**: `FALSIFIED_R7C_INSUFFICIENT` (row 3) per eval_report.md §13 at merge SHA.
- **Aggregate verdict**: `REJECT_NON_DISCRIMINATIVE`.
- **C-se-r7a-replica drift claim**: "within tolerance" vs C-se anchor (S-1).

## 6. Drift tolerance

- **C-se-r7a-replica vs S-1 C-se**: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5% (per PR #331 design memo at merge SHA).
- **Fix A row-counts**: per-cell row count must match eval_report.md §3 within **±10 rows** (binding tolerance per V2-expanded amendment §7.2 / §A.1).

## 7. Historic compatibility classifications (from PR #358 companion review)

- **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE** — `_q_sort_key` reads only val fields.
- **HISTORIC_DATA_IDENTITY_NOT_PROVABLE** — no merge-SHA content-SHA recording.

## 8. Permitted later wording

Per V2-expanded §A.3: per-sentinel display **MUST** be `CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY`.

## 9. Helper-source mapping

| Helper | Source script @ merge SHA |
|---|---|
| D-1 realised-PnL | `stage25_0b._compute_realised_barrier_pnl` |
| Pre-row PnL cache | `stage26_0b.precompute_realised_pnl_per_row` |
| Split logic | `stage25_0b.split_70_15_15` |
| Pair runtime | `stage27_0f_s_e_r7_c_regime_eval.py:2093` (inlined) |
| S-E scorer | inherited from S-1 (stage27_0d `build_pipeline_lightgbm_regression_widened`) |
| S-B scorer | inherited (stage26_0d) |
| R7-C feature computation | `PR #332 @ ad673b4 :: scripts/stage27_0f_s_e_r7_c_regime_eval.py:331-...` (R7CPreflightError + R7-C feature builder) |
| Fix A row-set isolation | introduced at PR #332; see eval_report.md §3 + commit message |

## 10. Stage 1 declarations

- **NO formal verification executed.**
- **NO model fit performed.**
- **NO Fix A row-set isolation re-verified** (Stage 2 sentinel run will perform clean reproduction; synthetic unit test is additional guard only, not substitute).
- **NO V2-expanded outcome label emittable.**
- **A0-broad β remains halted.**

---

*End of S-2 contract snapshot for PR #332 / Phase 27.0f-β / `ad673b4`.*
