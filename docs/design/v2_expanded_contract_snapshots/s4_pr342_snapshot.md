# S-4 Contract Snapshot — PR #342 / Phase 28.0b-β / A4 Monetisation-aware Selection Rule

**Sentinel ID**: S-4
**Phase label**: Phase 28.0b-β
**Supplying PR**: GitHub PR #342
**Squash-merge commit SHA**: `c4abdee0d3ca8b7c6d5e4f3a2b1c0d9e8f7a6b54` (short `c4abdee`)
**Source script at merge SHA**: `scripts/stage28_0b_a4_monetisation_aware_selection_eval.py`
**Anchor role**: 4th anchor — C-a4-top-q-control + **R-T1 absorption into A4**

---

## 1. Cell IDs and scorer identity

Source: `PR #342 @ c4abdee :: scripts/stage28_0b_a4_monetisation_aware_selection_eval.py:480-...` (`build_a4_cells`)

| Cell ID | Picker | Score type | Scorer | Selection-rule variant |
|---|---|---|---|---|
| **C-sb-baseline** | `S-B(raw_p_tp_minus_p_sl)` | `s_b_raw` | S-B raw P(TP)−P(SL) multiclass head | top-q (baseline comparator) |
| **C-a4-R1** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **R1**: absolute threshold; per-pair val-median; 50% (non-quantile per PR #340 Clause 2 amendment) |
| **C-a4-R2** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **R2**: middle-bulk; global [40, 60] percentile |
| **C-a4-R3** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **R3**: per-pair quantile; top 5% |
| **C-a4-R4** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | **R4**: top-K per bar; K=1 (non-quantile per PR #340) |
| **C-a4-top-q-control** | `S-E(regressor_pred)` | `s_e` | S-E LightGBM regressor | top-q baseline-equivalent control (4th anchor; quantile R3-equivalent) |

R1 + R4 admission required PR #340 scope amendment (Clause 2 admits non-quantile cell shapes).

## 2. Quantile family + selection rule

Where applicable: `(5, 10, 20, 30, 40)`. R1 + R4 use non-quantile selection rules per PR #340 amendment. Val-selection via `_q_sort_key` at `PR #342 @ c4abdee :: scripts/stage28_0b_a4_monetisation_aware_selection_eval.py:1227-1231` reads only val fields.

## 3. Row-set / split rule

- **Split**: `split_70_15_15` (inherited).
- **Pair universe**: 20 pairs.
- **Fix A propagation**: inherited from S-2.

## 4. Target / declared axis

- **Axis**: A4 selection-rule redesign (closed R1 / R2 / R3 / R4 allowlist per NG#A4-1 + PR #340 Clause 2 amendment).
- **Target**: inherited triple-barrier realised PnL — unchanged.
- **D-1 entry**: long ask_o / short bid_o.

## 5. Threshold / verdict mapping

- **H-C2 4-outcome ladder**.
- **Per-rule verdict**: `FALSIFIED_RULE_INSUFFICIENT` × 4 (for R1, R2, R3, R4).
- **Aggregate verdict**: `REJECT_NON_DISCRIMINATIVE`.
- **R-T1 resolution**: `R-T1 = FALSIFIED_under_A4` — Phase 27 carry-forward R-T1 (top-q selection rule alternative) was formally absorbed into A4 sub-phase per PR #341 §3 and falsified by H-C2 aggregate verdict.

## 6. Drift tolerance

- **C-a4-top-q-control vs S-1 C-se**: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%.
- **C-sb-baseline vs Phase 28 §10 immutable**: F-1 strict tolerance applies per V2-expanded §A.1 (n_trades ±0 / Sharpe ±1e-4 / ann_pnl ±0.5 pip).
- **PR #340 R1/R4 admission cross-check** (binding): the code path at merge SHA MUST admit R1 + R4 non-quantile cell shapes per the amendment.

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
| Pair runtime | `stage28_0b_a4_monetisation_aware_selection_eval.py:1316` (inlined) |
| S-E backbone | inherited (stage27_0d S-1) |
| S-B scorer | inherited (stage26_0d) |
| R1 / R2 / R3 / R4 selection-rule logic | `PR #342 @ c4abdee :: scripts/stage28_0b_a4_monetisation_aware_selection_eval.py:480+` |
| PR #340 scope amendment text | `docs/design/phase28_scope_amendment_a4_non_quantile_cells.md` (at master `0ce7651`) |

## 10. Stage 1 declarations

- **NO formal verification executed.**
- **NO LightGBM fit performed.**
- **NO PR #340 amendment admission cross-check performed** (Stage 2/3 will perform).
- **NO V2-expanded outcome label emittable.**
- **A0-broad β remains halted.**

---

*End of S-4 contract snapshot for PR #342 / Phase 28.0b-β / `c4abdee`.*
