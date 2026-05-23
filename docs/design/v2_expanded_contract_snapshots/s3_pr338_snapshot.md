# S-3 Contract Snapshot — PR #338 / Phase 28.0a-β / A1 Loss Redesign

**Sentinel ID**: S-3
**Phase label**: Phase 28.0a-β
**Supplying PR**: GitHub PR #338
**Squash-merge commit SHA**: `2b6dee1ea6c6f5e4d3c2b1a0987654321fedcba9` (short `2b6dee1`)
**Source script at merge SHA**: `scripts/stage28_0a_a1_objective_redesign_eval.py`
**Anchor role**: 3rd anchor — C-a1-se-r7a-replica + **Phase 28 §10 immutable baseline first reference**

---

## 1. Cell IDs and scorer identity

Source: `PR #338 @ 2b6dee1 :: scripts/stage28_0a_a1_objective_redesign_eval.py:468-...` (`build_a1_cells`)

| Cell ID | Picker | Score type | Scorer-family identity | Loss axis variant |
|---|---|---|---|---|
| **C-sb-baseline** | `S-B(raw_p_tp_minus_p_sl)` | `s_b_raw` | S-B raw P(TP)−P(SL) multiclass head | — (baseline) |
| **C-a1-L1** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **L1**: asymmetric Huber α=0.5 |
| **C-a1-L2** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **L2**: Huber α=0.7 |
| **C-a1-L3** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **L3**: Huber α=0.9 + regime-axis sample weights |
| **C-a1-se-r7a-replica** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor (3rd anchor; L3=α=0.9 matched to 27.0d C-se loss) | matches S-1 backbone |

S-B (multiclass) vs S-E (regressor) NEVER conflated.

## 2. Quantile family + selection rule

Same: `(5, 10, 20, 30, 40)`. Val-selection via `_q_sort_key` at `PR #338 @ 2b6dee1 :: scripts/stage28_0a_a1_objective_redesign_eval.py:1113-1117` reads only val fields.

## 3. Row-set / split rule

- **Split**: `split_70_15_15` (inherited from S-1 lineage).
- **Pair universe**: 20 pairs.
- **Fix A propagation**: inherited from S-2; R7-C feature drop applies only to cells that reference R7-C — but A1 L1/L2/L3 cells use R7-A only, so Fix A is a no-op for the L1/L2/L3 cells themselves. Relevant for the C-a1-se-r7a-replica anchor relative to the C-se chain.

## 4. Target / declared axis

- **Axis**: A1 loss function redesign (closed L1 / L2 / L3 allowlist per NG#A1-1).
- **Target**: inherited triple-barrier realised PnL (K_FAV=1.5 / K_ADV=1.0 / H_M1=60) — unchanged.
- **D-1 entry**: long ask_o / short bid_o.

## 5. Threshold / verdict mapping

- **H-C1 4-outcome ladder**: introduced at PR #337 (28.0a-α design memo) for A1 axis.
- **Per-L verdict**: `FALSIFIED_OBJECTIVE_INSUFFICIENT` × 3 (for each of L1, L2, L3) per eval_report.md §13.
- **Aggregate verdict**: `REJECT_NON_DISCRIMINATIVE`.

## 6. Drift tolerance

- **C-a1-se-r7a-replica vs S-1 C-se**: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%.
- **Phase 28 §10 cross-check**: C-sb-baseline at #338 (S-B multiclass on full R7-A-clean row-set) is the **first** reference to the Phase 28 §10 immutable baseline `n_trades=34,626 / Sharpe=-0.1732 / ann_pnl=-204,664.4 / val Sharpe=-0.1863`. Phase 28 §10 was introduced at PR #335 (Phase 28 kickoff). The baseline numeric is the same as the Phase 26 R6-new-A C02 baseline that S-1 (#325) used contemporaneously — frozen as immutable at PR #335.
- **F-1 strict tolerance applies** (per V2-expanded amendment §A.1): n_trades ±0 / Sharpe ±1e-4 / ann_pnl ±0.5 pip. **Control-drift tolerance MUST NOT be reused for Phase 28 §10 baseline FAIL-FAST.**

## 7. Historic compatibility classifications

- **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE**
- **HISTORIC_DATA_IDENTITY_NOT_PROVABLE**

## 8. Permitted later wording

`CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY` per V2-expanded §A.3.

## 9. Helper-source mapping

| Helper | Source script @ merge SHA |
|---|---|
| D-1 realised-PnL | `stage25_0b._compute_realised_barrier_pnl` |
| Pre-row PnL cache | `stage26_0b.precompute_realised_pnl_per_row` |
| Split logic | `stage25_0b.split_70_15_15` |
| Pair runtime | `stage28_0a_a1_objective_redesign_eval.py:1203` (inlined) |
| S-E backbone (L3 matched to S-1) | inherited from stage27_0d S-1 |
| S-B scorer | inherited (stage26_0d) |
| L1 / L2 / L3 loss configurations | `PR #338 @ 2b6dee1 :: scripts/stage28_0a_a1_objective_redesign_eval.py` (loss-specific LGBMRegressor instantiation per cell) |

## 10. Stage 1 declarations

- **NO formal verification executed.**
- **NO LightGBM fit performed.**
- **NO Phase 28 §10 baseline reproduction attempted** (Stage 2/3 will perform under F-1 strict tolerance).
- **NO V2-expanded outcome label emittable.**
- **A0-broad β remains halted.**

---

*End of S-3 contract snapshot for PR #338 / Phase 28.0a-β / `2b6dee1`.*
