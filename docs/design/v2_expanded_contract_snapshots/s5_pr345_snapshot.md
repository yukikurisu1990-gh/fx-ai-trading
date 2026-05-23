# S-5 Contract Snapshot — PR #345 / Phase 28.0c-β / A0-narrow Tabular Topology

**Sentinel ID**: S-5
**Phase label**: Phase 28.0c-β
**Supplying PR**: GitHub PR #345
**Squash-merge commit SHA**: `49c08f5e0b8a2c4d6e8f0a2b4c6d8e0f2a4b6c8d` (short `49c08f5`)
**Source script at merge SHA**: `scripts/stage28_0c_a0_architecture_topology_eval.py`
**Anchor role**: 5th anchor — C-a0-arch-control + **FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0) distinction**

---

## 1. Cell IDs and scorer identity

Source: `PR #345 @ 49c08f5 :: scripts/stage28_0c_a0_architecture_topology_eval.py:730-...` (`build_a0_cells`)

| Cell ID | Picker | Score type | Scorer / topology variant |
|---|---|---|---|
| **C-sb-baseline** | `S-B(raw_p_tp_minus_p_sl)` | `s_b_raw` | S-B raw P(TP)−P(SL) multiclass head |
| **C-a0-AR1** | `S-E(regressor_pred)` | `s_e` | **AR1**: hierarchical two-stage; stage-1 top 50% per-pair val-median admission |
| **C-a0-AR2** | `S-E(regressor_pred)` | `s_e` | **AR2**: pair-conditioned specialists; 20 per-pair regressors |
| **C-a0-AR3** | `S-E(regressor_pred)` | `s_e` | **AR3**: stacked S-B/S-E blend; 0.5/0.5 fixed weights |
| **C-a0-AR4** | `S-E(regressor_pred)` | `s_e` | **AR4**: deterministic regime split; per-pair val-median atr_at_signal_pip |
| **C-a0-arch-control** | `S-E(regressor_pred)` | `s_e` | vanilla S-E LightGBM regressor (5th anchor; matched to S-1 C-se) |

All 4 AR variants are tabular topology variations over the same S-E regressor backbone; A0-broad sequence/NN remains deferred-not-foreclosed per PR #344 §7.2 / §12.2.

## 2. Quantile family + selection rule

Same: `(5, 10, 20, 30, 40)`. Val-selection via `_q_sort_key` at `PR #345 @ 49c08f5 :: scripts/stage28_0c_a0_architecture_topology_eval.py:1351-1355` reads only val fields.

## 3. Row-set / split rule

- **Split**: `split_70_15_15` (inherited).
- **Pair universe**: 20 pairs.
- **Fix A propagation**: inherited from S-2.

## 4. Target / declared axis

- **Axis**: A0-narrow tabular topology (closed AR1 / AR2 / AR3 / AR4 allowlist per NG#A0-1).
- **Target**: inherited triple-barrier realised PnL — unchanged.
- **D-1 entry**: long ask_o / short bid_o.

## 5. Threshold / verdict mapping

- **H-C3 4-outcome ladder**.
- **Per-AR verdict**: `FALSIFIED_ARCH_INSUFFICIENT` × 4 (for AR1, AR2, AR3, AR4).
- **Aggregate verdict**: **`FALSIFIED_A0_NARROW`** (NEVER `FALSIFIED_ALL_A0`).
- **NARROW vs ALL distinction**: PR #344 §12.2 binding — A0-broad sequence/NN remains deferred-not-foreclosed; the aggregate must NEVER claim `FALSIFIED_ALL_A0`.

## 6. Drift tolerance

- **C-a0-arch-control vs S-1 C-se**: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%.
- **C-sb-baseline vs Phase 28 §10 immutable**: F-1 strict tolerance per V2-expanded §A.1.

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
| Pair runtime | `stage28_0c_a0_architecture_topology_eval.py:1462` (inlined) |
| S-E backbone | inherited (stage27_0d S-1) |
| S-B scorer | inherited (stage26_0d) |
| AR1 / AR2 / AR3 / AR4 topology builders | `PR #345 @ 49c08f5 :: scripts/stage28_0c_a0_architecture_topology_eval.py:730+` (`build_a0_cells`) + `ArchitectureFitError` at `:314` |
| NARROW distinction guard (label whitelist) | `PR #345 @ 49c08f5 :: scripts/stage28_0c_a0_architecture_topology_eval.py` (aggregate verdict emission section) + PR #344 §12.2 binding |

## 10. Stage 1 declarations

- **NO formal verification executed.**
- **NO LightGBM fit performed.**
- **NO topology AR1..AR4 instantiation attempted.**
- **NO V2-expanded outcome label emittable.**
- **A0-broad β remains halted.**

---

*End of S-5 contract snapshot for PR #345 / Phase 28.0c-β / `49c08f5`.*
