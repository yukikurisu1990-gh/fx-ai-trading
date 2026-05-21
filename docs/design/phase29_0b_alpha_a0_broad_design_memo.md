# Phase 29.0b-α A0-broad Design Memo — Closed 3-Architecture Sequence-NN Allowlist (S1 LSTM / S2 Temporal CNN / S3 Transformer); Windowed (N=32×8) Input on R7-A; C-d2-arch-control 7th Anchor; Early Stopping on Val Huber Loss (Train-time vs Verdict-time Objective Wall); H-D2 4-Outcome Ladder; FALSIFIED_A0_BROAD_NARROW Distinction

**Type**: Phase 29 second sub-phase α design memo. **Doc-only**.
**Branch**: `research/phase29-0b-alpha-a0-broad-design`
**Base**: master @ `1985e92` (post-PR #353 A0-broad preflight audit)
**Pattern**: analogous to PR #344 (28.0c-α A0-narrow design memo; closed-architecture-allowlist) + PR #350 (29.0a-α A2; per-target baseline + FALSIFIED_*_NARROW distinction) + PR #353 (A0-broad preflight audit; 7th anchor framing source)
**Date**: 2026-05-22

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 29.0b-α A0-broad design memo**. It pre-states the **closed 3-architecture sequence-NN allowlist** (S1 Bidirectional LSTM / S2 Temporal CNN / S3 Transformer encoder), the **windowed dataset shape** (N=32 M5 bars × 8 bid/ask OHLC channels), the **C-d2-arch-control 7th anchor** (tabular LightGBM control inside sequence-cell harness; NOT a sequence model), the **fixed non-architecture axes** (R7-A only / inherited triple-barrier target / top-q selection / symmetric Huber α=0.9 regression loss), the **NG#A0B-1 / NG#A0B-2 / NG#A0B-3 anti-collapse guards**, the **H-D2 4-outcome ladder** with `FALSIFIED_A0_BROAD_NARROW` distinction, the **training schedule with early stopping on validation Huber loss** (NOT Sharpe — train-time vs verdict-time objective wall), and the **sanity probe items 1-6 inherited + 7-12 NEW sequence-cell-specific**.*
>
> *This PR does **NOT**:*
>
> - *initiate the Phase 29.0b-β eval (no `scripts/stage29_0b_*.py`; no `tests/unit/test_stage29_0b_*.py`; no `artifacts/stage29_0b/`);*
> - *implement sequence training code, generate windowed dataset artifacts, or commit any model checkpoints;*
> - *implement R-B or A3 (deferred-not-foreclosed per PR #348 §6 / PR #353 §14.2);*
> - *admit joint Path 4 (Policy C single-axis default per PR #353 §14.3);*
> - *create any scope amendment (Scope III + Policy C + Option 9c cover A0-broad single-axis on R7-A);*
> - *modify the Phase 28 §10 baseline numeric (immutable; inherited DIRECTLY as Phase 29 §10 reference for A0-broad since target unchanged; Option 9c simple case);*
> - *modify the Phase 29 §10 per-target baseline values (T1/T2/T3/T4 frozen at PR #351; DIAGNOSTIC-ONLY 2nd references; NOT used for A0-broad H-D2 evaluation);*
> - *touch any prior verdict (Phase 27 + Phase 28 + Phase 29.0a verdicts preserved verbatim);*
> - *amend the D-1 bid/ask executable harness (sequence-cell extension uses bid/ask OHLC; harness contract unchanged);*
> - *modify the production v9 wiring (Phase 9.12 tip `79ed1e8`; untouched);*
> - *relax ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, or Phase 22 frozen-OOS contract;*
> - *auto-route to Phase 29.0b-β after merge.*
>
> *The β-eval implementation is a **separate later PR** (recommended path: `scripts/stage29_0b_a0_broad_sequence_eval.py` + `tests/unit/test_stage29_0b_a0_broad_sequence_eval.py` + `artifacts/stage29_0b/eval_report.md`). The pre-stated parameters / closed 3-architecture allowlist / windowed shape / training schedule / NG#A0B-* are fixed at α and cannot be changed at β; any change requires a memo amendment PR back to α.*

Same approval-then-defer pattern as PR #344 / PR #350 / PR #353.

---

## 1. A0-broad mission statement

**Phase 29.0b tests A0-broad (sequence / NN model class beyond tabular LightGBM) as the Phase 29 second sub-phase per PR #352 primary recommendation, gated by PR #353 preflight clearance.** The hypothesis is that the **tabular LightGBM model class** is the binding constraint on Sharpe lift across the 9-eval picture (PR #352 §1). Phase 29.0b replaces the model class with a **closed allowlist of 3 sequence-NN architectures** (S1 Bidirectional LSTM / S2 Temporal CNN / S3 Transformer encoder), keeping the R7-A feature surface, triple-barrier realised-PnL target, top-q selection rule, and symmetric Huber α=0.9 regression loss **all fixed**. Only the **model class** and the **input shape** (tabular → windowed M5 bars) change.

This sub-phase is the **7th anchor** in the bit-tight reproduction chain (27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a → **29.0b**), with **C-d2-arch-control = tabular LightGBM inside the sequence-cell evaluation harness** (NOT a sequence model) per PR #353 §10. The 7th anchor's purpose is to **separate sequence-cell harness drift from sequence-model effect**.

A0-broad is **single-axis** per Policy C default (PR #348 §7) and scope-locked per PR #353 §14.1: R-B / A3 / joint Path 4 are deferred-not-foreclosed and NOT included at 29.0b.

**Critical design choice — train-time vs verdict-time objective wall**: training early stopping uses **validation Huber loss** (the same objective minimised by training). The H-D2 verdict uses **validation Sharpe lift** + H1m + H3 + baseline reproduction. These two objectives are **explicitly separated** to preserve the selection-overfit guard: epoch selection by val Huber loss never directly optimises Sharpe, so Sharpe-based verdict retains its falsifiability discipline.

---

## 2. Why A0-broad is not Phase 27/28/29 inertia (8-distinction analysis)

A0-broad is structurally distinct from every Phase 27 / Phase 28 / Phase 29 sub-phase tested to date.

### 2.1 A0-broad ≠ S-axis score micro-redesign (27.0b/c/d/e/f)

- S-axis varied **score formulation** (S-C TIME penalty / S-D calibrated EV / S-E regression / quantile family trim / R7-C regime feature) within tabular LightGBM.
- A0-broad varies the **model class** (tabular → sequence/NN); the score is the sequence model's output (scalar per row).
- NG#A0B-1 enforces fixed loss + fixed selection; score-formulation variation requires separate scope amendment.

### 2.2 A0-broad ≠ A1 loss redesign (28.0a)

- A1 varied **loss function** (L1 asymmetric Huber α=0.5 / L2 Huber α=0.7 / L3 Huber α=0.9 + regime sample weights) within tabular LightGBM.
- A0-broad varies the **model class**; loss remains symmetric Huber α=0.9 regression (per-row scalar output → Huber vs realised PnL).

### 2.3 A0-broad ≠ A4 selection rule redesign (28.0b)

- A4 varied the **selection rule** (R1 / R2 / R3 / R4) within tabular LightGBM.
- A0-broad varies the **model class**; selection remains top-q on score (quantile family {5, 10, 20, 30, 40}).

### 2.4 A0-broad ≠ A0-narrow tabular topology audit (28.0c)

- A0-narrow varied **tabular topology** (AR1 hierarchical / AR2 specialist heads / AR3 stacked / AR4 deterministic regime split) **within** tabular LightGBM.
- A0-broad varies the **model class beyond tabular**; sequence/NN is the most structurally distinct axis change in the 9-eval picture.

### 2.5 A0-broad ≠ A2 target redesign (29.0a)

- A2 varied **target framing** (T1 fixed-horizon close / T2 time-weighted / T3 multi-horizon / T4 asymmetric K_FAV/K_ADV) within tabular LightGBM.
- A0-broad varies the **model class**; target remains inherited triple-barrier realised PnL (same as 29.0a C-d1-target-control).

### 2.6 A0-broad ≠ R-T1 / R-T3 standalone (resolved)

- R-T1 absorbed under A4 frame at 28.0b (FALSIFIED_under_A4).
- R-T3 absorbed under A2 frame at 29.0a (FALSIFIED_under_T3).
- A0-broad does not revive either standalone.

### 2.7 A0-broad ≠ R7-C-style regime feature widening (27.0f)

- R7-C varied **regime feature class** within tabular.
- A0-broad varies the **model class**; R7-A feature surface unchanged (NO R-B at 29.0b per scope lock; PR #353 §14.1).

### 2.8 A0-broad ≠ R-B feature class redesign

- R-B varies **feature class** beyond R7-A (path-shape / microstructure / multi-TF / calendar / cross-asset).
- A0-broad varies **model class only**; R-B deferred-not-foreclosed (admissible later via Path 2 alone or Path 4 joint per PR #352).

---

## 3. Formal H-D2 hypothesis statement

> **H-D2 (A0-broad scope)**: At least one of the closed 3 sequence-NN architecture variants {S1, S2, S3} will produce a val-selected configuration on the C-d2-Sx cell satisfying **all** of:
>
> 1. **H2 PASS**: val Sharpe ≥ Phase 28 §10 baseline + **+0.05 absolute** (val Sharpe ≥ -0.1363)
> 2. **H1m preserved**: val-selected cell Spearman ≥ **+0.30**
> 3. **H3 PASS**: trade count ≥ **20,000**
> 4. **C-sb-baseline reproduction FAIL-FAST PASS** (gate inherited from PR #344 §10)
>
> **OR** H-D2 is FALSIFIED at the variant.

### 3.1 H-D2 falsification interpretation — FALSIFIED_A0_BROAD_NARROW vs FALSIFIED_ALL_A0_BROAD

Load-bearing distinction analogous to:
- PR #344 §12.2: FALSIFIED_A0_NARROW vs FALSIFIED_ALL_A0
- PR #350 §3.1: FALSIFIED_A2_NARROW vs FALSIFIED_ALL_A2

- **If all 3 architecture variants FALSIFIED** (any combination of row 2 PARTIAL_SUPPORT / row 3 FALSIFIED_ARCH_INSUFFICIENT / row 4 PARTIAL_DRIFT_TABULAR_REPLICA without any PASS) → the result is **`FALSIFIED_A0_BROAD_NARROW`**, **NOT** `FALSIFIED_ALL_A0_BROAD`.
- **Alternate sequence architectures outside the closed 3-variant allowlist remain admissible** via separate scope amendment PR. Examples that remain admissible: GRU / unidirectional LSTM / encoder-only Transformer with different pooling / hybrid CNN-Transformer / state-space models (S4 / Mamba) / dilated convolution stacks with different patterns / multi-head NN with non-sequence inputs.
- **This PR explicitly does not claim `FALSIFIED_ALL_A0_BROAD` under any β outcome.**

---

## 4. Closed 3-architecture sequence-NN allowlist (formal pre-statement)

NG#A0B-1 enforces. Each variant has α-fixed numerics; no β-time grid sweep.

### 4.1 S1 — Bidirectional LSTM

- **Architecture**: bidirectional LSTM
- **Layers**: 2
- **hidden_dim**: 128
- **dropout**: 0.2
- **Pooling**: final-step pooling (last hidden state) + linear head → scalar score
- **Input shape**: (batch, 32, 8) — 32 M5 bars × 8 channels (bid_OHLC + ask_OHLC)
- **Loss**: symmetric Huber α=0.9 (per-row scalar output vs realised PnL)
- **Sample weight**: 1 (uniform)
- **Optimizer**: AdamW; lr=1e-3; weight_decay=1e-4
- **Batch size**: 256
- **Max epochs**: 5
- **Early stopping**: validation Huber loss; patience=2; best checkpoint = lowest val Huber loss
- **Seed**: 42
- **Deterministic mode**: `torch.use_deterministic_algorithms(True, warn_only=True)`
- **Rationale**: classical sequence baseline; mature; ~50 MB checkpoint

### 4.2 S2 — Temporal CNN

- **Architecture**: 1D Temporal CNN (channels-first; conv1d)
- **Conv blocks**: 4
- **Kernel size**: 3
- **Dilations**: [1, 2, 4, 8] (one per block)
- **Channels**: 64
- **Dropout**: 0.2 (between blocks)
- **Pooling**: global average pooling over temporal dim + linear head → scalar score
- **Input shape**: (batch, 8, 32) — channels-first; same data as S1 transposed
- **Loss**: symmetric Huber α=0.9
- **Sample weight**: 1
- **Optimizer**: AdamW; lr=1e-3; weight_decay=1e-4
- **Batch size**: 512
- **Max epochs**: 5
- **Early stopping**: validation Huber loss; patience=2; best checkpoint = lowest val Huber loss
- **Seed**: 42
- **Deterministic mode**: `torch.use_deterministic_algorithms(True, warn_only=True)`
- **Rationale**: parallel conv (faster than LSTM); receptive field 1+2+4+8 = 15 bars covered by dilation cascade; ~30 MB checkpoint

### 4.3 S3 — Transformer encoder

- **Architecture**: Transformer encoder
- **Layers**: 2
- **d_model**: 128
- **n_heads**: 4
- **ff_dim**: 256
- **Dropout**: 0.2
- **Positional encoding**: sinusoidal (fixed; not learned)
- **Pooling**: [CLS]-token-equivalent (first position) + linear head → scalar score (the first position embedding is treated as the aggregate; alternative: global mean pool over all positions if [CLS] proves unstable — α-fixed: first-position pooling)
- **Input shape**: (batch, 32, 8)
- **Loss**: symmetric Huber α=0.9
- **Sample weight**: 1
- **Optimizer**: AdamW; lr=5e-4; weight_decay=1e-4
- **Batch size**: 256
- **Max epochs**: 5
- **Early stopping**: validation Huber loss; patience=2; best checkpoint = lowest val Huber loss
- **Seed**: 42
- **Deterministic mode**: `torch.use_deterministic_algorithms(True, warn_only=True)`
- **Rationale**: attention-based global temporal interaction; ~200 MB checkpoint

### 4.4 Why 3 architectures exactly

| Variant | Architectural lever tested |
|---|---|
| S1 LSTM | "recurrent inductive bias helps" |
| S2 Temporal CNN | "local convolutional receptive field with dilation helps" |
| S3 Transformer | "attention-based global interaction helps" |

The 3 architectures span structurally distinct sequence inductive biases. NG#A0B-1 enforces:
- 4th architecture variant at β NOT admissible (requires α memo amendment PR)
- Numeric grid sweep within a variant NOT admissible (e.g., S1-with-{1,2,3,4}-layers grid)
- Joint admission (R-B / A2 / A3) NOT admissible (Policy C single-axis default)
- Feature surface (R7-A only) / target / selection / loss / windowed shape (32×8) all fixed

### 4.5 No grid sweep within a variant

- S1 layers=2 fixed; hidden_dim=128 fixed; dropout=0.2 fixed
- S2 blocks=4 fixed; dilations=[1,2,4,8] fixed; channels=64 fixed; dropout=0.2 fixed
- S3 layers=2 fixed; d_model=128 fixed; n_heads=4 fixed; ff_dim=256 fixed; dropout=0.2 fixed
- All: lr / batch_size / max_epochs / patience / seed α-fixed
- Sub-phase α merge locks these; β change requires α amendment PR

---

## 5. Fixed non-architecture axes

A0-broad commits to 5 invariants across all 3 sequence variants. NG#A0B-1 enforces.

| Axis | Fixed value | Source |
|---|---|---|
| Feature surface | **R7-A only** (4 features: pair / direction / atr_at_signal_pip / spread_at_signal_pip) | PR #353 §14.1; R-B deferred |
| Windowed input shape | **(32, 8)** — 32 M5 bars × 8 channels (bid_OHLC + ask_OHLC); NO mid-price; NO volume | PR #353 §6.2 + this memo §6 |
| Target | **triple-barrier realised PnL** (K_FAV=1.5 × ATR / K_ADV=1.0 × ATR / H_M1=60) | inherited from 27.0d / 28.0c / 29.0a C-d1-target-control |
| Selection rule | **top-q on score** with quantile family {5, 10, 20, 30, 40} | inherited |
| Loss | **symmetric Huber α=0.9** regression (per-row scalar output → Huber vs realised PnL); sample_weight=1 | inherited from 27.0d S-E |

---

## 6. Windowed dataset shape (final lock)

### 6.1 Shape

- **N = 32 M5 bars** (last 160 minutes pre-signal)
- **Per-bar channels = 8**: bid_O, bid_H, bid_L, bid_C, ask_O, ask_H, ask_L, ask_C
- **NO mid-price**; **NO volume**; **NO derived/computed channels**
- **Per-sample tensor**: (32, 8) for S1 + S3; (8, 32) channels-first for S2
- **Sample dtype**: float32

### 6.2 Normalisation policy (α-fixed)

- **Per-pair pip normalisation**: each raw price divided by pair's pip size (per-pair adaptive; same as inherited `pip_size_for`)
- **Entry-price centering**: subtract `signal_ts ask_o` (long-side reference price at entry) from all 32 × 8 channel values; preserves relative bid/ask structure
- **NO z-score normalisation** (preserves D-1 bid/ask executable semantics directly; preserves cross-pair comparability via pip)
- **NO batch normalisation** (per-pair pip handles cross-pair scale)
- **No β-time normalisation-scheme grid sweep**

### 6.3 Storage estimate

| Split | Rows | Sample bytes | Total raw |
|---|---|---|---|
| Train | 2.94M | 32 × 8 × 4 = 1024 | ~3.0 GB |
| Val | 0.52M | 1024 | ~0.5 GB |
| Test | 0.60M | 1024 | ~0.6 GB |
| **Total** | — | — | **~4.1 GB raw** |

Within PR #353 §6.2 estimate. Gitignored under `artifacts/stage29_0b/windowed_dataset/` (β-eval gitignore pattern).

### 6.4 Regeneration script (β-eval responsibility; NOT this PR)

- Will extend `_build_pair_runtime` to add `build_windowed_input_per_row(df, pair_runtime_map, N=32)` returning `np.ndarray (n_rows, 32, 8)`
- Deterministic; reproducible from M1 BA + signal_ts
- Per-pair parquet shards (gitignored)
- **NOT implemented in this α memo PR**

---

## 7. M1 / M5 alignment policy

### 7.1 Window alignment rule

- Sequence input window: M5 bars `[signal_ts − 32 × 5 min, signal_ts]` (exclusive of signal_ts itself; entry happens at signal_ts + 1 min per inherited D-1)
- M5 bars derived by aggregating M1 OHLC:
  - bid_O = first M1 bid_o in 5-min window
  - bid_H = max M1 bid_h in 5-min window
  - bid_L = min M1 bid_l in 5-min window
  - bid_C = last M1 bid_c in 5-min window
  - ask_OHLC symmetric

### 7.2 Boundary handling

- **Sample dropped** if any of the 32 M5 bars has no underlying M1 data (weekend gap; data start; data corruption)
- Per-pair NaN-mask reported in sanity probe item 7 (windowed dataset coverage)
- **Dropped rows excluded** from training / validation / test (NaN-mask propagates to PnL; same as 29.0a per-target NaN-PnL pattern from PR #350 §17.1)

### 7.3 Phase 22 frozen-OOS extension

- Phase 22 OOS rows extended with `windowed_input_valid: bool` flag at β-eval pre-flight
- Per-pair OOS rows with full windows: ~99% expected (rare boundary drops)
- Subset-OOS fallback documented if regeneration cost exceeds 1 hour (PR #353 §9 WARN-only)

---

## 8. Sequence-cell D-1 bid/ask executable harness

### 8.1 Entry/exit pricing (unchanged from tabular)

- Entry at signal_ts + 1 min: long → ask_o; short → bid_o
- Triple-barrier resolution at K_FAV × ATR / K_ADV × ATR / H_M1=60
- Long PnL: `(resolution_price - entry_ask) / pip`
- Short PnL: `(entry_bid - resolution_price) / pip`
- **Identical** to 27.0d / 28.0c / 29.0a C-d1-target-control

### 8.2 Sequence input D-1 preservation

- Sequence input uses **bid/ask OHLC** of M5 bars in window — **NOT mid-prices**
- Preserves D-1 binding for inputs; sequence model "sees" the same bid/ask data the executable harness uses for entry/exit pricing
- No mid-price computation anywhere in the input pipeline

### 8.3 Per-row scoring (unchanged)

- Sequence model output: scalar score per row (S1 final-step pooling / S2 global average pooling / S3 first-position pooling)
- Top-q selection on scalar score (identical to tabular)
- No per-step entry/exit; no path-dependent action by the model

### 8.4 H_M1 horizon inherited

- H_M1 = 60 M1 bars
- Triple-barrier resolution semantics identical to 27.0d C-se

---

## 9. Cell structure (5 cells; 21 records)

| # | Cell ID | Score | Target | Selection | Purpose |
|---|---|---|---|---|---|
| 1 | **C-d2-S1** | S1 LSTM sequence regressor (final-step pooling → scalar) | inherited triple-barrier | top-q quantile family {5,10,20,30,40} | A0-broad S1 — recurrent inductive bias |
| 2 | **C-d2-S2** | S2 Temporal CNN sequence regressor (global avg pooling → scalar) | inherited triple-barrier | top-q quantile family | A0-broad S2 — dilated convolution |
| 3 | **C-d2-S3** | S3 Transformer encoder sequence regressor (first-position pooling → scalar) | inherited triple-barrier | top-q quantile family | A0-broad S3 — attention-based global interaction |
| 4 | **C-d2-arch-control** | tabular LightGBM (vanilla S-E; symmetric Huber α=0.9; sample_weight=1) on R7-A | inherited triple-barrier | top-q quantile family | **7th anchor**; tabular control inside sequence-cell evaluation harness; NOT a sequence model |
| 5 | **C-sb-baseline** | S-B raw P(TP)−P(SL) multiclass head on R7-A | inherited triple-barrier | top-q (q=5 only) | Phase 28 §10 baseline FAIL-FAST gate (inherited Option 9c) |

- 4 cells × 5 quantiles = 20 records
- + 1 baseline cell at q=5 only = 1 record
- **Total: 21 (cell, q) records**

### 9.1 Artifact count

| Cell | Artifact | Estimated size |
|---|---|---|
| C-d2-S1 | 1 sequence model checkpoint (S1 LSTM) | ~50 MB |
| C-d2-S2 | 1 sequence model checkpoint (S2 Temporal CNN) | ~30 MB |
| C-d2-S3 | 1 sequence model checkpoint (S3 Transformer) | ~200 MB |
| C-d2-arch-control | 1 tabular LightGBM regressor (27.0d S-E backbone) | ~5 MB |
| C-sb-baseline | 1 multiclass LightGBM head (R7-A) | ~5 MB |

**Total: 3 sequence model artifacts + 2 LightGBM artifacts = 5 artifacts; ~290 MB total checkpoints**.

---

## 10. C-d2-arch-control 7th anchor — load-bearing distinction

**Critical**: C-d2-arch-control is a **tabular LightGBM model evaluated inside the sequence-cell evaluation harness**. It is **NOT a sequence model**.

### 10.1 Definition

- Model: vanilla S-E LightGBM regressor on R7-A (4 features); symmetric Huber α=0.9; sample_weight=1
- Identical to 27.0d C-se backbone
- Reproduces 27.0d C-se / 27.0f r7a-replica / 28.0a r7a-replica / 28.0b top-q-control / 28.0c arch-control / 29.0a C-d1-target-control (the 6th anchor) **as the 7th anchor**, evaluated INSIDE the sequence-cell harness
- Quantile family {5, 10, 20, 30, 40}; target = inherited triple-barrier; same as 29.0a C-d1-target-control

### 10.2 Why 7th anchor

The sequence-cell evaluation harness must correctly evaluate a tabular LightGBM model. If C-d2-arch-control reproduces 6th anchor (29.0a C-d1-target-control) within tolerance, the harness is correctly architected. If C-d2-arch-control deviates significantly, the deviation is **harness drift** (architectural change in the evaluation pipeline) — NOT model effect.

**This separates sequence-model effect from sequence-cell-harness drift**:
- C-d2-S1/S2/S3 differ from C-d2-arch-control → genuinely the sequence model effect
- C-d2-arch-control deviates from 29.0a C-d1-target-control → harness drift (not model effect)

### 10.3 Reproduction tolerance

Inherited from PR #344 §11 / PR #350 §10.3 / PR #353 §10.3:

| Metric | Tolerance |
|---|---|
| n_trades | ±100 |
| Sharpe | ±5e-3 |
| ann_pnl | ±0.5 % magnitude |

**DIAGNOSTIC-ONLY WARN** if outside tolerance; **NOT HALT**. WARN flagged in eval_report §11b (analogous to PR #344 §15 / PR #350 §14).

---

## 11. Baseline / control reproduction policy

### 11.1 C-sb-baseline FAIL-FAST (Phase 28 §10 inherited directly)

A0-broad does NOT redesign the target. Phase 29 §10 baseline reference inherited from Phase 28 §10 **directly** under Option 9c simple case (PR #348 §9; target unchanged).

| Metric | Phase 28 §10 baseline (immutable) | Tolerance |
|---|---|---|
| n_trades (test, val-selected q\*=5 on C-sb-baseline) | **34,626** | exact (±0) |
| Sharpe (test) | **-0.1732** | ±1e-4 |
| ann_pnl (test, pip) | **-204,664.4** | ±0.5 pip |

**HALT on mismatch**: `BaselineMismatchError` (inherited from PR #344 §10 / PR #350 §8.4 pattern).

**val Sharpe reference**: -0.1863 (Phase 28 §10 val Sharpe; used for H-D2 H2 lift threshold: PASS if val Sharpe ≥ -0.1363, i.e., lift ≥ +0.05).

### 11.2 Phase 29 29.0a per-target baselines (DIAGNOSTIC-ONLY 2nd reference)

- Phase 29 §10 per-target baselines (T1/T2/T3/T4) frozen at PR #351 in `artifacts/stage29_0a/phase29_section10_per_target_baseline.json`
- **NOT used for A0-broad H-D2 evaluation** (target unchanged at A0-broad; per-target baselines apply only to A2 sub-phase)
- Inherited as DIAGNOSTIC-ONLY 2nd reference; informational only

### 11.3 C-d2-arch-control 7th-anchor (DIAGNOSTIC-ONLY WARN)

Per §10.3.

---

## 12. Training schedule (α-fixed)

### 12.1 Common settings

- **Seed**: 42 (inherited per OOF seed contract)
- **Optimizer**: AdamW; weight_decay=1e-4
- **Loss**: symmetric Huber α=0.9 (`torch.nn.HuberLoss(delta=0.9)`)
- **Sample weight**: 1 (uniform)
- **Max epochs**: 5
- **Deterministic mode**: `torch.use_deterministic_algorithms(True, warn_only=True)`; `torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False`
- **CUBLAS_WORKSPACE_CONFIG**: `":4096:8"` (environment variable)

### 12.2 Per-architecture overrides

| Variant | lr | batch_size |
|---|---|---|
| S1 LSTM | 1e-3 | 256 |
| S2 Temporal CNN | 1e-3 | 512 |
| S3 Transformer | 5e-4 | 256 |

### 12.3 Early stopping — validation **Huber loss** (NOT Sharpe; critical wall)

**Critical design choice**: training early stopping uses **validation Huber loss**, NOT validation Sharpe.

- **Monitor metric**: validation Huber loss (the same objective minimised by training)
- **Mode**: minimise
- **Patience**: 2 epochs
- **Best checkpoint selection**: the epoch with the **lowest val Huber loss** (within max_epochs=5)
- **Verdict metric (separate)**: H-D2 verdict uses val Sharpe lift + H1m + H3 + baseline reproduction — NOT training loss; NOT directly correlated to training selection

#### Why train-time vs verdict-time objective wall

A0-broad introduces sequence/NN models with **higher capacity** than tabular LightGBM. If epoch selection used val Sharpe (the verdict metric), an additional implicit Sharpe optimisation would slip inside the train-time loop, weakening the **selection-overfit guard** (PR #344 §14 / PR #350 §15 / inherited PR #335 Clause 1).

By using val Huber loss for epoch selection and val Sharpe for verdict, the two objectives remain explicitly separated:

- **Train-time objective**: minimise validation Huber loss (regression fidelity to realised PnL)
- **Verdict-time objective**: maximise validation Sharpe lift vs Phase 28 §10 baseline (monetisation gain)

The H-D2 verdict ladder retains its falsifiability discipline because val Sharpe is **not** the metric the model selection (epoch) optimises against. This preserves the **ADOPT_CANDIDATE wall** and H2 PASS = PROMISING_BUT_NEEDS_OOS semantics.

### 12.4 Quantile family selection (verdict-time)

- After best-checkpoint selection by val Huber loss, the resulting sequence model produces val_score + test_score per row
- Quantile family {5, 10, 20, 30, 40} applied at val_score → top-q cutoffs → val realised metrics
- Per-cell `(cell, q)` Sharpe / n_trades / ann_pnl → val-selection picks best (cell, q) by val Sharpe (validation-only selection; same as PR #344 / PR #350)
- This is the **only** Sharpe-based selection layer in A0-broad

---

## 13. NG#A0B-* anti-collapse guards

### 13.1 NG#A0B-1 — closed 3-architecture allowlist + fixed non-architecture axes + no joint admission

- Architectures MUST be {S1 LSTM, S2 Temporal CNN, S3 Transformer} with α-fixed numerics (§4)
- 4th architecture variant at β NOT admissible (requires α memo amendment)
- Numeric grid sweep within a variant NOT admissible
- Feature surface (R7-A only) / windowed shape (32×8 bid/ask OHLC) / target (inherited triple-barrier) / selection (top-q {5,10,20,30,40}) / loss (symmetric Huber α=0.9) / sample_weight=1 all fixed
- Joint admission (R-B / A2 / A3) NOT admissible (Policy C single-axis default)
- Training schedule lr/batch/max_epochs/patience α-fixed per architecture
- Early stopping monitor metric: validation Huber loss (NOT val Sharpe)

### 13.2 NG#A0B-2 — per-architecture verdict required

- Each architecture variant {S1, S2, S3} produces its own H-D2 outcome (PASS / PARTIAL_SUPPORT / FALSIFIED_ARCH_INSUFFICIENT / PARTIAL_DRIFT_TABULAR_REPLICA)
- Aggregate-only verdict NOT admissible

### 13.3 NG#A0B-3 — C-d2-arch-control mandatory (7th anchor)

- C-d2-arch-control = tabular LightGBM control inside sequence-cell harness (§10)
- 7th-anchor reproduction WARN-only; DIAGNOSTIC
- Per-architecture PARTIAL_DRIFT_TABULAR_REPLICA detection: if C-d2-Sx ≈ C-d2-arch-control within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%) at val-selected q*, flag PARTIAL_DRIFT_TABULAR_REPLICA (sequence model produces no architectural lift vs tabular)

---

## 14. H-D2 4-outcome ladder per architecture (precedence row 4 > 1 > 2 > 3)

Inherited from PR #344 §12.3 / PR #350 §10 pattern.

| Row | Outcome | Per-architecture condition |
|---|---|---|
| **4** | **PARTIAL_DRIFT_TABULAR_REPLICA** (checked first per NG#A0B-3) | C-d2-Sx ≈ C-d2-arch-control (val-selected q\*) within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%) — sequence model produces no architectural lift vs tabular |
| **1** | **PASS** | All four H-D2 conditions: val Sharpe lift ≥ +0.05 vs Phase 28 §10 baseline AND H1m ≥ +0.30 AND trade count ≥ 20,000 AND C-sb-baseline FAIL-FAST PASS |
| **2** | **PARTIAL_SUPPORT** | val Sharpe lift ∈ [+0.02, +0.05); others intact |
| **3** | **FALSIFIED_ARCH_INSUFFICIENT** (default) | val Sharpe lift < +0.02 OR other H-D2 conditions fail |

---

## 15. Aggregate verdict mapping

- **any AR PASS** → **SPLIT_VERDICT_ROUTE_TO_REVIEW** (route to post-29.0b routing review; PROMISING_BUT_NEEDS_OOS candidate; ADOPT_CANDIDATE wall preserved per Clause 1; H2 PASS = PROMISING_BUT_NEEDS_OOS only)
- **0 PASS + 1+ PARTIAL_SUPPORT** → **REJECT_NON_DISCRIMINATIVE** (sub-threshold; route to post-29.0b routing review for next-axis comparison — R-B / A3 / joint Path 4 / Phase 29 closure)
- **All 3 architectures FALSIFIED_ARCH_INSUFFICIENT or PARTIAL_DRIFT_TABULAR_REPLICA** → **REJECT_NON_DISCRIMINATIVE + diagnostic `FALSIFIED_A0_BROAD_NARROW`**
  - **NEVER labelled `FALSIFIED_ALL_A0_BROAD`**
  - Alternate sequence architectures outside closed 3-variant allowlist remain admissible via separate scope amendment
  - Post-29.0b routing review compares R-B / A3 / joint Path 4 / Phase 29 closure next-axis options

---

## 16. Sanity probe items (12 total: 6 inherited + 6 NEW sequence-cell-specific)

### 16.1 Inherited items 1-6 (from PR #344 §15 / PR #350 §13)

1. **Class priors** per split (train / val / test) for L1 3-class labels
2. **Per-pair TIME share** on train
3. **D-1 binding check**: bid/ask executable treatment verified for parameterised barrier + sequence input pipeline (bid_h/ask_l/ask_h/bid_l + bid_o/ask_o/bid_c/ask_c)
4. **Realised-PnL distribution per class** on TRAIN (DIAGNOSTIC)
5. **R7-A new-feature NaN-rate check**
6. **R7-A positivity check** on TRAIN

### 16.2 NEW items 7-12 (sequence-cell-specific)

7. **Windowed dataset coverage**:
   - Per-pair count of rows with full 32-bar windows
   - Per-pair NaN-mask rate
   - Total dropped rows per split
   - **HALT** if any split coverage < 95%

8. **Sequence-cell harness verification**:
   - C-d2-arch-control evaluation succeeds (tabular LightGBM evaluated correctly inside sequence-cell harness)
   - 7th-anchor reproduction (DIAGNOSTIC-ONLY WARN if outside tolerance vs 29.0a C-d1-target-control)
   - **HALT** if harness fails to evaluate tabular control

9. **Per-architecture training convergence**:
   - Val Huber loss trajectory per architecture (decreasing; non-NaN; not exploding)
   - Best-checkpoint epoch number per architecture (within max_epochs=5)
   - Early-stopping triggered count
   - **WARN** if slow convergence (best epoch = max_epochs)

10. **GPU memory utilisation**:
    - Peak VRAM per architecture during fit
    - Per-architecture checkpoint disk size
    - **HALT** if peak VRAM > 90% of available

11. **Determinism check**:
    - 2 consecutive runs of same architecture × same seed must produce identical metrics within tolerance
    - Tolerance:
      - val Sharpe **±1e-4**
      - n_trades **exact**
      - selected q **identical** (i.e., quantile-family argmax matches)
    - **NOT a bit-identical tensor comparison** — metric-level tolerance only, accounting for minor numeric noise even under deterministic ops (CUDA non-determinism partial mitigation per `warn_only=True`)
    - **HALT** if metric tolerance not met

12. **Phase 22 OOS extension verification**:
    - OOS rows with `windowed_input_valid=True` count
    - Per-pair OOS coverage rate
    - Subset-OOS fallback path verified
    - **WARN** if OOS coverage < 99% (subset-OOS fallback documented)

### 16.3 HALT vs WARN summary

| Item | Gating |
|---|---|
| 1-6 inherited | HALT semantics inherited (per PR #344 §15 / PR #350 §13) |
| 7 windowed dataset coverage | HALT if < 95% |
| 8 harness verification | HALT if tabular control fails to evaluate |
| 9 training convergence | WARN (informational; slow convergence at α may need β-time review) |
| 10 GPU memory | HALT if VRAM > 90% |
| 11 determinism | HALT if metric tolerance not met |
| 12 OOS extension | WARN if coverage < 99% (subset-OOS fallback) |

---

## 17. eval_report.md (25-section pattern inherited from PR #344 §15 / PR #350 §14)

Per-section adaptation for A0-broad:

| § | Adaptation |
|---|---|
| 1 Executive summary | Per-architecture H-D2 outcomes; **FALSIFIED_A0_BROAD_NARROW vs FALSIFIED_ALL_A0_BROAD distinction** if all 3 falsify |
| 2 Cells overview | 5 cells (S1 / S2 / S3 / arch-control / baseline) |
| 3 Row-set policy | R7-A-clean parent + windowed-input-valid rows |
| 4 Sanity probe results | Items 1-6 inherited + items 7-12 NEW per-sequence-cell |
| 5 OOF correlation diagnostic | DIAGNOSTIC-ONLY; per-architecture S-E regression OOF on tabular comparison (architectures themselves not OOF-fit due to cost; reported as caveat) |
| 6 Regression diagnostic | Per-architecture S-E regression (val Huber loss / R² / MAE on val + test) |
| 7 Per-cell quantile family results | 4 sequence cells × 5 quantiles + 1 baseline = 21 records |
| 8 Val-selection per cell | Per-cell val-selected (cell\*, q\*) — selection by val Sharpe (validation-only) |
| 9 Cross-cell aggregate verdict | Phase 28 cross-cell template |
| 10 **§10 baseline reproduction FAIL-FAST** | Phase 28 §10 numeric (n=34626 / Sharpe -0.1732 / ann_pnl -204664.4); inherited Option 9c simple case (target unchanged) |
| 11 Within-eval ablation drift | Per-architecture (C-d2-Sx vs C-d2-arch-control) |
| 11b **7th anchor drift** | C-d2-arch-control vs 29.0a C-d1-target-control (6th anchor); DIAGNOSTIC-ONLY WARN; chain extension |
| 12 Feature importance per architecture | DIAGNOSTIC-ONLY; per-architecture (sequence-specific): attention weights for S3; gradient saliency for S1/S2; tabular feature_importances_ for C-d2-arch-control |
| 13 **H-D2 outcome row binding per architecture** | Per-architecture 4-outcome (PASS / PARTIAL_SUPPORT / FALSIFIED_ARCH_INSUFFICIENT / PARTIAL_DRIFT_TABULAR_REPLICA); **FALSIFIED_A0_BROAD_NARROW distinction explicit** |
| 14 Trade-count budget audit | Per-architecture; sequence cells expected ~similar trade counts to tabular at matched q |
| 15 Pair concentration | Per-architecture (val-selected) |
| 16 Direction balance | Per-architecture |
| 17 Per-pair Sharpe contribution | Per-architecture (DIAGNOSTIC-ONLY) |
| 18 Top-tail regime audit | Per-architecture on `spread_at_signal_pip` only (R7-C features NOT computed) |
| 19 R7-A NaN check | Inherited |
| 20 Realised-PnL distribution by class on TRAIN | Inherited (target unchanged) |
| 21 Predicted PnL distribution per architecture | Per-architecture S-E predicted distribution (train / val / test) |
| 22 References | PR #344 / #348 / #350 / #351 / #352 / #353 + Phase 28 templates |
| 23 **Caveats** | A0-broad scope (single-axis on R7-A; no R-B / A2 / A3 / joint Path 4); ADOPT_CANDIDATE wall; H2 PASS = PROMISING_BUT_NEEDS_OOS only; FALSIFIED_A0_BROAD_NARROW vs FALSIFIED_ALL_A0_BROAD distinction; Phase 28 §10 inherited directly (target unchanged); 29.0a per-target baselines are DIAGNOSTIC-ONLY (not used for A0-broad H-D2); 7th anchor bit-tight chain extension; train-time vs verdict-time objective wall (val Huber loss for epoch selection, val Sharpe for verdict) |
| 24 Cross-validation re-fits | Per-architecture training convergence summary; DIAGNOSTIC-ONLY |
| 25 Sub-phase verdict snapshot | Per-architecture outcomes + aggregate + Phase 28 §10 baseline reproduction status + 7th-anchor drift WARN |

---

## 18. Selection-overfit guard preservation

Inherited from PR #344 §14 / PR #350 §15 + A0-broad-specific reinforcement.

### 18.1 Layer 1 — validation-only configuration selection per cell

Val-selected `(cell, q)` only contributes to formal H-D2 verdict. Other `(cell, q)` records labelled **DIAGNOSTIC-ONLY** in eval_report; excluded from H-D2 outcome row binding.

### 18.2 Layer 2 — cross-cell aggregation

Per Phase 28 / Phase 29.0a pattern; sequence cells + arch-control + baseline aggregated.

### 18.3 NEW: train-time vs verdict-time objective wall (A0-broad-specific reinforcement)

A0-broad-specific selection-overfit guard reinforcement (PR #344 / PR #350 did not require this because tabular LightGBM does not have a per-epoch selection layer):

- **Train-time objective** (per-epoch selection): validation **Huber loss**
- **Verdict-time objective** (cell, q selection + H-D2 ladder): validation **Sharpe**
- These two objectives are **explicitly separated**; epoch selection by val Huber loss never directly optimises Sharpe, so the val-Sharpe-based verdict preserves its falsifiability discipline

### 18.4 H1 / H2 / H3 / H4 ladder preservation

- **H1m** ≥ +0.30 (cell Spearman on val): preserved
- **H2** lift ≥ +0.05 vs Phase 28 §10 baseline: preserved
- **H3** ≥ 20,000 trades: preserved
- **H4 DIAGNOSTIC-ONLY**: preserved
- **ADOPT_CANDIDATE wall preserved**: H2 PASS = PROMISING_BUT_NEEDS_OOS only
- **NG#10 / NG#11 not relaxed**

---

## 19. Binding constraints + what this PR is NOT (consolidated; non-duplicated)

### 19.1 Binding constraints preserved (verbatim from PR #348 §17 / PR #352 §17 / PR #353 §18)

- D-1 bid/ask executable harness preserved (sequence-cell extension uses bid/ask OHLC; harness contract unchanged)
- R7-A subset preserved (4 features; **no R-B** at 29.0b per scope lock)
- Triple-barrier realised-PnL target preserved (target unchanged from 29.0a C-d1-target-control)
- Top-q on score selection rule preserved (quantile family {5, 10, 20, 30, 40})
- Symmetric Huber α=0.9 loss preserved (per-row scalar output → Huber vs realised PnL)
- sample_weight = 1 (uniform) preserved
- Validation-only selection preserved
- Test touched once preserved
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating required
- Phase 22 frozen-OOS preserved (sequence-cell extension feasibility audited at PR #353 §9)
- Production v9 20-pair (Phase 9.12 tip `79ed1e8`) untouched
- **Phase 28 §10 baseline numeric immutable** (n=34626 / Sharpe -0.1732 / ann_pnl -204664.4 / val Sharpe -0.1863); never retroactively modified; inherited DIRECTLY as Phase 29 §10 reference for A0-broad (target unchanged; Option 9c simple case)
- **Phase 29 §10 per-target baselines** (T1/T2/T3/T4) from 29.0a frozen at PR #351; DIAGNOSTIC-ONLY 2nd references; NOT used for A0-broad H-D2 evaluation
- No prior verdict modification (Phase 27 + Phase 28 + Phase 29.0a verdicts preserved verbatim)
- MEMORY.md unchanged inside PR
- A1 / A4 / A0-narrow / A2-narrow exhausted statuses preserved
- R-T1 = FALSIFIED_under_A4 / R-T3 = FALSIFIED_under_T3 preserved
- R-B / A3 deferred-not-foreclosed (admissible at Phase 29 per Scope III; PR #348 §6)
- Joint Path 4 (A0-broad + R-B) deferred-not-foreclosed (Policy C admissible later with explicit α motivation; NOT exercised at 29.0b)
- Scope III + Policy C + Option 9c preserved
- Phase 27/28 inertia routes NOT admissible without amendment
- 7th anchor bit-tight reproduction chain extension preserved (27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a → 29.0b)
- No scope amendment in this PR
- No 29.0b-β eval in this PR
- No sequence training code in this PR
- No windowed dataset artifact committed (preflight §6.3 audited feasibility; generation deferred to 29.0b-β; gitignored under `artifacts/stage29_0b/windowed_dataset/`)
- No sequence model checkpoint committed
- No R-B / A2 / A3 implementation
- No production change in this PR
- No auto-route after merge
- This PR is doc-only

### 19.2 What this PR is NOT

- ❌ Phase 29.0b-β eval implementation (separate later PR)
- ❌ Sequence model training (no implementation)
- ❌ Windowed dataset generation artifact (preflight audited feasibility; generation deferred to 29.0b-β)
- ❌ Sequence model checkpoint
- ❌ 4th sequence architecture variant at β (NG#A0B-1)
- ❌ Numeric grid sweep within a variant at β (NG#A0B-1)
- ❌ R-B implementation (deferred per scope lock)
- ❌ A2 target redesign revisit (A2-narrow exhausted at 29.0a)
- ❌ A3 implementation
- ❌ Joint Path 4 admission (Policy C single-axis default; admissible later with explicit α motivation)
- ❌ Scope amendment (Scope III + Policy C + Option 9c cover A0-broad single-axis on R7-A)
- ❌ Phase 29 closure (Path 6 premature per PR #352 §13.3)
- ❌ Production change
- ❌ Prior verdict modification
- ❌ Phase 28 §10 / Phase 29 §10 per-target baseline modification
- ❌ D-1 bid/ask executable harness amendment
- ❌ ADOPT_CANDIDATE wall / NG / γ / X-v2 / Phase 22 frozen-OOS relaxation
- ❌ Foreclosure of any path
- ❌ Auto-route to 29.0b-β after merge
- ❌ MEMORY.md edit inside PR

---

## 20. References

### Phase 29 PRs

- PR #348 — Phase 29 kickoff (Scope III / Policy C / Option 9c)
- PR #349 — Phase 29 first-mover routing review
- PR #350 — Phase 29.0a-α A2 target redesign design memo
- PR #351 — Phase 29.0a-β A2 target redesign eval (FALSIFIED_A2_NARROW; R-T3 = FALSIFIED_under_T3)
- PR #352 — Phase 29 post-29.0a routing review (Path 1 PRIMARY preflight-gated)
- PR #353 — A0-broad preflight audit (PASS gate; 7th anchor framing source)
- **This PR** — Phase 29.0b-α A0-broad design memo

### Phase 28 templates

- PR #335 — Phase 28 kickoff
- PR #340 — Phase 28 scope amendment (doc-only audit template)
- PR #344 — Phase 28.0c-α A0-narrow design memo (closed-architecture-allowlist pattern; FALSIFIED_*_NARROW distinction template)
- PR #345 — Phase 28.0c-β A0-narrow eval (5th anchor in bit-tight chain)
- PR #347 — Phase 28 closure memo

### Phase 27 inheritance

- PR #325 — Phase 27.0d-β S-E regression (1st anchor in bit-tight chain; tabular control source; C-se backbone)
- PR #332 — Phase 27.0f-β (2nd anchor)
- PR #334 — Phase 27 closure memo

### Binding contracts

- PR #279 — γ closure (production behavior contract; preserved)
- Phase 22 frozen-OOS contract (preserved)
- X-v2 OOS gating (required for any future production deployment)
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair; untouched throughout Phase 27 / Phase 28 / Phase 29)

---

*End of `docs/design/phase29_0b_alpha_a0_broad_design_memo.md`.*
