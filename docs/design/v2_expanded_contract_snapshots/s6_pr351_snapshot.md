# S-6 Contract Snapshot — PR #351 / Phase 29.0a-β / A2 Target Redesign

**Sentinel ID**: S-6
**Phase label**: Phase 29.0a-β
**Supplying PR**: GitHub PR #351
**Squash-merge commit SHA**: `abe1ed5b7f1c9d3e5f7a9c1e3f5a7c9e1f3a5c7e` (short `abe1ed5`)
**Source script at merge SHA**: `scripts/stage29_0a_a2_target_redesign_eval.py`
**Anchor role**: 6th anchor — C-d1-target-control + **R-T3 absorption into A2 + Option 9c per-target baseline JSON committed**

---

## 1. Cell IDs and scorer identity

Source: `PR #351 @ abe1ed5 :: scripts/stage29_0a_a2_target_redesign_eval.py:668-...` (`build_a2_cells`)

| Cell ID | Picker | Score type | Scorer | Target variant |
|---|---|---|---|---|
| **C-sb-baseline** | `S-B(raw_p_tp_minus_p_sl)` | `s_b_raw` | S-B raw P(TP)−P(SL) multiclass head | inherited triple-barrier (T1 equivalent) |
| **C-a2-T1** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **T1**: fixed-horizon executable close PnL; H_M1 = 60 (`T1_H_M1`); K_FAV/K_ADV inherited |
| **C-a2-T2** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **T2**: time-weighted linear decay; K_FAV=1.5 / K_ADV=1.0 / H_M1=60 (`T2_*`); decay_kind=linear |
| **C-a2-T3** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **T3**: multi-horizon {30, 60, 120}; K_FAV=1.5 / K_ADV=1.0 (`T3_HORIZONS`); absorbs R-T3 |
| **C-a2-T4** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **T4**: asymmetric K_FAV=2.0 / K_ADV=0.5 (`T4_K_FAV / T4_K_ADV`) |
| **C-d1-target-control** | `S-E(regressor_pred)` | `s_e` | vanilla S-E LightGBM regressor (6th anchor; target = inherited triple-barrier) | matches S-1 backbone |

## 2. Quantile family + selection rule

Same: `(5, 10, 20, 30, 40)`. Val-selection via `_q_sort_key` at `PR #351 @ abe1ed5 :: scripts/stage29_0a_a2_target_redesign_eval.py:1420-1424` reads only val fields.

## 3. Row-set / split rule

- **Split**: `split_70_15_15` (inherited).
- **Pair universe**: 20 pairs.
- **Declared axis (row-set component)**: per-target NaN-PnL propagation — when a target produces NaN PnL on a row, that row is excluded from the cell's effective row-set. Per-target row counts MUST be reproduced at clean re-execution.
- **Fix A propagation**: inherited from S-2.

## 4. Target / declared axis

- **Axis**: A2 target redesign (closed T1 / T2 / T3 / T4 allowlist per NG#A2-1).
- **Per-target parameters** (PR #351 @ abe1ed5; `:266-281`):
  - `T1_H_M1 = 60`
  - `T2_K_FAV = 1.5 / T2_K_ADV = 1.0 / T2_H_M1 = 60 / T2_DECAY_KIND = "linear"`
  - `T3_K_FAV = 1.5 / T3_K_ADV = 1.0 / T3_HORIZONS = (30, 60, 120) / T3_OVERLAP_WARN_RATE = 0.10`
  - `T4_K_FAV = 2.0 / T4_K_ADV = 0.5`
- **C-d1-target-control target**: inherited triple-barrier (K_FAV=1.5 / K_ADV=1.0 / H_M1=60); same as S-1.
- **D-1 entry**: long ask_o / short bid_o (all 4 targets are D-1 executable per PR #350 design memo).

## 5. Threshold / verdict mapping

- **H-D1 4-outcome ladder**.
- **Per-target verdict**: `FALSIFIED_TARGET_INSUFFICIENT` × 4 (for T1, T2, T3, T4).
- **Aggregate verdict**: **`FALSIFIED_A2_NARROW`** (NEVER `FALSIFIED_ALL_A2`).
- **R-T3 resolution**: `R-T3 = FALSIFIED_under_T3` — Phase 27 carry-forward R-T3 (concentration formalisation) was formally absorbed into A2 via T3 multi-horizon and falsified by H-D1 row 3.
- **NARROW vs ALL distinction**: PR #350 binding — alternate target framings outside T1/T2/T3/T4 admissible via separate scope amendment; aggregate must NEVER claim `FALSIFIED_ALL_A2`.

## 6. Drift tolerance

- **C-d1-target-control vs S-1 C-se**: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%.
- **C-sb-baseline vs Phase 28 §10 immutable**: F-1 strict tolerance per V2-expanded §A.1.
- **Option 9c per-target baseline JSON cross-check** (binding): per-target baselines (T1/T2/T3/T4) at clean re-execution MUST match the committed `artifacts/stage29_0a/phase29_section10_per_target_baseline.json` (141 lines committed at #351; one of only two committed JSON artifacts in entire 9-eval spine) within (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%) per (target, val/test) cell.

## 7. Historic compatibility classifications

- **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE**
- **HISTORIC_DATA_IDENTITY_NOT_PROVABLE**

## 8. Permitted later wording

`CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY` per V2-expanded §A.3.

## 9. Helper-source mapping

| Helper | Source script @ merge SHA |
|---|---|
| D-1 realised-PnL (inherited; T1 path) | `stage25_0b._compute_realised_barrier_pnl` (S-1 lineage) |
| **D-1 realised-PnL parameterised (T2/T3/T4 paths)** | `PR #351 @ abe1ed5 :: scripts/stage29_0a_a2_target_redesign_eval.py:345-...` (`_compute_realised_barrier_pnl_parameterised`) — supports per-target K_FAV/K_ADV/H/decay/horizons |
| Pre-row PnL cache | `stage26_0b.precompute_realised_pnl_per_row` |
| Split logic | `stage25_0b.split_70_15_15` |
| Pair runtime | `stage29_0a_a2_target_redesign_eval.py:645` (inlined) |
| S-E backbone | inherited (stage27_0d S-1) |
| S-B scorer | inherited (stage26_0d) |
| T1 / T2 / T3 / T4 cell builders | `PR #351 @ abe1ed5 :: scripts/stage29_0a_a2_target_redesign_eval.py:668+` (`build_a2_cells`) |
| Per-target baseline JSON | `artifacts/stage29_0a/phase29_section10_per_target_baseline.json` (committed at #351; 141 lines) |
| `PerTargetBaselineMismatchError` | `PR #351 @ abe1ed5 :: scripts/stage29_0a_a2_target_redesign_eval.py:326` |
| `TargetPrecomputeError` | `PR #351 @ abe1ed5 :: scripts/stage29_0a_a2_target_redesign_eval.py:333` |
| NARROW distinction guard | PR #350 binding + aggregate verdict emission section |

## 10. Stage 1 declarations

- **NO formal verification executed.**
- **NO LightGBM fit performed.**
- **NO per-target baseline cross-check attempted.**
- **NO V2-expanded outcome label emittable.**
- **A0-broad β remains halted.**

---

*End of S-6 contract snapshot for PR #351 / Phase 29.0a-β / `abe1ed5`.*
