# A0-broad Preflight Audit — 9-Dimension Feasibility Review Before Phase 29.0b-α; PASS / WARN / HALT Ladder; 7th Anchor (Tabular LightGBM Control inside Sequence-Cell Harness); Single-Axis A0-broad on R7-A Only

**Type**: Path 1 PRIMARY first concrete PR. **Doc-only audit**.
**Branch**: `research/phase29-a0-broad-preflight-audit`
**Base**: master @ `2718b2b` (post-PR #352)
**Pattern**: analogous to PR #340 (scope amendment audit doc-only pattern); inherits checklist source from PR #348 §14.1
**Date**: 2026-05-20

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval **formally accepts the preflight audit findings** for the 9 dimensions (per-dimension PASS / WARN / HALT verdicts + aggregate gate). It is the **first concrete PR** of the Path 1 PRIMARY preflight-gated sequencing accepted at PR #352 §15.1.*
>
> ***Critical wording**: a preflight aggregate verdict of `PASS_29_0B_ALPHA_AUTHORISED` is a **necessary-but-not-sufficient** condition for 29.0b-α authorisation. It indicates that no HALT-gated blocker is detected. It does **NOT auto-initiate** the Phase 29.0b-α A0-broad design memo PR; the 29.0b-α PR authorisation requires a **separate explicit user instruction** subsequent to this preflight audit's merge.*
>
> *This PR does **NOT**:*
>
> - *create a Phase 29.0b-α A0-broad design memo (separate later PR; user-instructed);*
> - *create a 29.0b-β eval (further later PR);*
> - *implement any model training, sequence architecture allowlist, windowed dataset generation script, or sequence-cell evaluation harness;*
> - *commit any windowed dataset artifact, sequence model checkpoint, or R-B feature class data;*
> - *implement R-B or A3 (deferred-not-foreclosed per PR #348 §6 / PR #352 §5);*
> - *create any scope amendment (Scope III + Policy C + Option 9c cover A0-broad single-axis on R7-A; preflight audits feasibility, not admissibility);*
> - *modify the Phase 28 §10 baseline numeric (immutable; archived);*
> - *modify the Phase 29 §10 per-target baseline values (T1/T2/T3/T4 frozen at PR #351);*
> - *touch any prior verdict (Phase 27 + Phase 28 + Phase 29.0a verdicts preserved verbatim);*
> - *modify the production v9 wiring (Phase 9.12 tip `79ed1e8`; untouched);*
> - *relax ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, or the Phase 22 frozen-OOS contract;*
> - *amend the D-1 bid/ask executable harness (preflight audits sequence-cell extension feasibility under the existing D-1 binding);*
> - *foreclose any path — Path 4 joint / Path 2 R-B / Path 5 A3 / Path 6 Phase 29 closure all remain admissible per PR #352;*
> - *auto-route to any subsequent PR.*

---

## 1. Preflight audit mission

**Derisk A0-broad implementation by auditing 9 prerequisite dimensions before the Phase 29.0b-α design memo is authored, and produce a per-dimension PASS / WARN / HALT verdict plus an aggregate gate that determines whether 29.0b-α PR authoring may proceed.**

The preflight audit is the **first concrete PR** of the Path 1 PRIMARY preflight-gated sequencing (PR #352 §15.1):

1. **This PR**: A0-broad preflight audit (doc-only)
2. (separate later PR) `docs/design/phase29_0b_alpha_a0_broad_design_memo.md`
3. (further later PR) Phase 29.0b-β eval implementation

A0-broad introduces a new pipeline class (GPU / sequence training / windowed dataset / sequence-aware D-1 / sequence-cell OOS / sequence-cell FAIL-FAST). Preflight-gating controls implementation risk by verifying these prerequisites before committing to the α design memo.

The aggregate gate has two outcomes:

- **`PASS_29_0B_ALPHA_AUTHORISED`** — necessary-but-not-sufficient condition for 29.0b-α authoring; no auto-initiation
- **`HALT_29_0B_ALPHA_BLOCKED`** — 29.0b-α authoring blocked until a separate resolution PR merges

---

## 2. Inheritance from PR #352 §10.4 / §15.1 / §14

This PR is the first concrete step of Path 1 PRIMARY (accepted at PR #352 merge):

| Item | Source | Status at this preflight |
|---|---|---|
| Path 1 PRIMARY status | PR #352 §9 | preserved; this PR is its first concrete PR |
| Preflight-gated sequencing | PR #352 §10.4 / §15.1 | this PR exercises it |
| 3-step Path 1 sequence | PR #352 §15.1 | step 1 = this PR; step 2 = 29.0b-α; step 3 = 29.0b-β |
| 9-eval picture motivation | PR #352 §1 | preserved as inherited motivation |
| Scope III admissibility | PR #348 §6 | A0-broad admissible; single-axis on R7-A is within Scope III |
| Policy C joint-axis policy | PR #348 §7 | joint admission deferred; first sequence sub-phase is single-axis |
| Option 9c dual baseline | PR #348 §9 | Phase 28 §10 archived + Phase 29 §10 per-target frozen; this PR does not modify either |
| No auto-route | PR #352 §0 | preserved; preflight merge does not auto-initiate 29.0b-α |

---

## 3. 9-dimension audit overview

| # | Dimension | Gating | What is audited |
|---|---|---|---|
| 1 | GPU availability | **HALT-gated** | CUDA device detection, VRAM budget, driver version |
| 2 | Sequence / NN training stack choice | WARN-only | PyTorch vs JAX vs TensorFlow trade-off; ecosystem compatibility |
| 3 | Windowed dataset feasibility | **HALT-gated** | Sequence input shape regenerable from existing M1 + M5 outcome data |
| 4 | M1 / M5 alignment | **HALT-gated** | Signal_ts ↔ M1 bar index lookup; D-1 binding alignment |
| 5 | Sequence-cell D-1 bid/ask harness | **HALT-gated** | D-1 binding extension to sequence inputs without amendment |
| 6 | Phase 22 frozen-OOS compatibility | WARN-only | OOS dataset format extension for sequence-cell evaluation |
| 7 | Sequence baseline / control reproduction | **HALT-gated** | 7th anchor in bit-tight reproduction chain (tabular control in sequence-cell harness) |
| 8 | Artifact / storage footprint | WARN-only | Sequence model checkpoint + windowed dataset disk footprint estimate |
| 9 | Runtime / compute budget | WARN-only | Per-fit + 5-fold OOF + full β-eval time estimate |

**5 HALT-gated dimensions** (must be PASS or WARN for aggregate PASS) × **4 WARN-only dimensions**.

---

## 4. Audit dimension 1 — GPU availability (HALT-gated)

### 4.1 Scope

- CUDA device detection (`torch.cuda.is_available()` or framework equivalent)
- VRAM budget per detected device
- Driver version + framework compatibility
- Multi-GPU vs single-GPU declaration

### 4.2 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | CUDA device available; ≥ 8 GB VRAM; driver version meets minimum required by chosen framework (PyTorch 2.x typically ≥ CUDA 11.8) |
| **WARN** | CUDA device available but VRAM is 4 GB–8 GB; mitigation via gradient checkpointing / smaller batch / mixed precision is feasible at sub-phase α |
| **HALT** | No CUDA device detected; CPU-only environment; sequence/NN training at production data scale (≥ 2.9M train rows × N M5 bars window) infeasible without GPU |

### 4.3 HALT resolution path

If HALT: blocked until a separate **infrastructure setup PR** (or alternative compute provisioning) merges. Alternatives:

- Provision a CUDA-capable machine
- Use cloud GPU instance (Colab / cloud-VM); reproducibility contract must extend to remote compute
- Reduce data scope to fit CPU training (NOT recommended; violates production data scale assumption)

---

## 5. Audit dimension 2 — Sequence / NN training stack choice (WARN-only)

### 5.1 Scope

Trade-off audit across the three viable stacks:

| Stack | Strengths | Weaknesses |
|---|---|---|
| **PyTorch** | Largest ecosystem; eager mode familiarity; `torch.compile` for speed; deterministic mode straightforward (`torch.use_deterministic_algorithms(True)`); broad sequence-model library coverage | Manual gradient management more verbose than JAX |
| **JAX** | Best deterministic guarantees (functional API; deterministic by default); JIT compilation; superior on TPUs | Smaller ecosystem; less LightGBM / sklearn interop |
| **TensorFlow** | Production-grade serving (tf.serving); tf.data pipeline strength | Smaller research-time community in 2026; deterministic mode less mature than PyTorch / JAX |

### 5.2 Recommended choice (preflight-level)

**PyTorch preferred** at the preflight level, based on:

- Largest sequence-model library ecosystem (HuggingFace transformers / torch.nn / native LSTM / GRU / TransformerEncoder)
- `torch.compile` for speed
- `torch.use_deterministic_algorithms(True)` for reproducibility (see §13)
- Compatibility with existing LightGBM-based eval harness (no framework conflict)
- Familiarity with research-team's prior code base

### 5.3 Lock semantics

**The final training-stack lock is deferred to 29.0b-α design memo**, not this preflight PR. Preflight only **recommends** PyTorch; if 29.0b-α design memo's closed sequence-architecture allowlist requires JAX-specific features (e.g., functional transformation of sub-modules), the lock can shift to JAX at α with explicit motivation.

If preflight finds **no blocker** for any of {PyTorch, JAX, TensorFlow}, this dimension is **WARN** (recommendation not yet locked at α) and does **not** block aggregate PASS.

### 5.4 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | All three stacks viable; PyTorch recommended; lock deferred to 29.0b-α |
| **WARN** | Stack choice has a blocker for one specific stack (e.g., deterministic mode missing); recommendation can route around to alternative |
| **HALT** | All three stacks have blockers (extremely unlikely under current ecosystem; not expected) |

WARN-only by gating policy: even if HALT-criterion met, would route via WARN with mitigation note.

---

## 6. Audit dimension 3 — Windowed dataset feasibility (HALT-gated)

### 6.1 Scope

- Sequence input shape per sample (e.g., N M5 bars × {OHLCV bid + ask} channels per bar)
- Regenerable from existing M1 BA + M5 outcome dataset; no new data acquisition
- Disk footprint estimate
- Storage / streaming pattern

### 6.2 Proposed shape (preflight-level; not locked at α)

- Window length: **N = 32 M5 bars** (covers last 160 minutes pre-signal)
- Per-bar channels: 8 (bid_OHLC + ask_OHLC), or 10 (bid_OHLCV + ask_OHLCV if volume available)
- Per-sample tensor: (32, 8) or (32, 10) → 256-320 floats per sample
- Train ≈ 2.94M rows × 320 floats × 4 bytes ≈ 3.8 GB raw
- Val ≈ 0.52M rows × 320 floats × 4 bytes ≈ 0.7 GB raw
- Test ≈ 0.60M rows × 320 floats × 4 bytes ≈ 0.8 GB raw
- **Total disk footprint estimate: ~5-6 GB** raw (uncompressed); ~2-3 GB compressed (parquet / float16)

### 6.3 Regeneration script

- Extends `_build_pair_runtime` to materialise per-row windowed arrays
- Inputs: existing M1 BA bid/ask OHLC + signal_ts
- Output: parquet shard per pair (gitignored)
- Deterministic; reproducible from M1 BA tip + M5 outcome dataset

### 6.4 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | Shape definable; regeneration script trivially extends existing pipeline; footprint < 10 GB |
| **WARN** | Shape feasible but footprint 10-30 GB; mitigation: lazy streaming / float16 / sample subsetting |
| **HALT** | Shape requires data not in M1 BA (e.g., tick data); footprint > 30 GB without mitigation path |

### 6.5 HALT resolution path

If HALT: blocked until **scope amendment PR** redefines window shape or admits alternative data source.

---

## 7. Audit dimension 4 — M1 / M5 alignment feasibility (HALT-gated)

### 7.1 Scope

- M5 signal_ts → M1 bar index lookup (existing `pair_runtime_map['m1_pos']` mechanism)
- Sequence input: M1 bars in `[signal_ts − N × 5 minutes, signal_ts]` aligned to M1 timeline
- Edge cases: data boundaries (start of dataset); weekend gaps (Fri close → Mon open); illiquid pair coverage
- Phase 22 frozen-OOS row-set alignment

### 7.2 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | Alignment trivially extends `_build_pair_runtime` for windowed view; edge cases handled by clamp / NaN-row mask |
| **WARN** | Edge cases (weekend gaps; data boundaries) need explicit handling at 29.0b-α (e.g., drop rows with incomplete window) |
| **HALT** | M1 BA structure cannot support windowed view (impossible under current structure — index by ts is preserved) |

### 7.3 HALT resolution path

Unlikely to trigger. If HALT: scope amendment PR to alter M1 BA structure (out of scope at preflight).

---

## 8. Audit dimension 5 — Sequence-cell D-1 bid/ask executable harness feasibility (HALT-gated)

### 8.1 Scope

The D-1 binding (PR #279 / inherited bid/ask executable harness) must extend to sequence-cell evaluation **without amendment**. Specifically:

- **Entry/exit prices at signal_ts**: unchanged from tabular (long entry=ask_o; short entry=bid_o; long exit=bid_c; short exit=ask_c)
- **Sequence model input**: uses bid/ask OHLC of preceding N M5 bars (NOT mid-prices) — preserves D-1 binding for inputs
- **Sequence model output**: per-row score (NOT per-step); top-q selection identical to tabular
- **H_M1 horizon semantics**: unchanged from tabular (60 M1 bars; per-row barrier resolution)

### 8.2 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | D-1 binding extends to sequence inputs verbatim (sequence input columns are bid/ask, not mid; per-row scoring + top-q selection identical to tabular; H_M1 unchanged) |
| **WARN** | Implementation detail needs explicit choice at 29.0b-α (e.g., normalisation scheme — per-pair vs per-window vs per-channel; document in 29.0b-α §X.X) |
| **HALT** | Sequence input requires mid-price (breaks D-1); sequence output requires per-step entry/exit (breaks per-row D-1 contract); H_M1 must change |

### 8.3 HALT resolution path

If HALT: D-1 amendment is a **scope amendment PR** (analogous to PR #340 for A4 non-quantile cells); high-stakes; would need explicit user authorisation given D-1 binding is one of the most senior contracts in the codebase.

---

## 9. Audit dimension 6 — Phase 22 frozen-OOS compatibility (WARN-only)

### 9.1 Scope

- Phase 22 frozen-OOS dataset format uses M5 signals + tabular R7-A features
- Sequence-cell evaluation extends OOS to include windowed inputs (same windowing logic as train/val/test)
- Regeneration: extend OOS labels parquet to include a per-row sequence-window-validity flag (excludes rows where the full window is unavailable, e.g., near OOS start)
- Fallback: if OOS regeneration cost is prohibitive, document at 29.0b-α and route via a **subset-OOS** approach (use only OOS rows with full windows)

### 9.2 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | OOS compatibility trivially extends; regeneration script straightforward |
| **WARN** | Regeneration step required; documented at 29.0b-α; subset-OOS fallback available |
| **HALT** | OOS labels incompatible (e.g., requires target redesign — not the case for A0-broad single-axis on R7-A with inherited target) |

WARN-only by gating: even if regeneration step is required, sub-phase α can handle it; not blocking.

---

## 10. Audit dimension 7 — Sequence baseline / control reproduction requirements (HALT-gated)

### 10.1 Scope: 7th anchor in bit-tight reproduction chain

| Anchor | PR | Cell | Cell type |
|---|---|---|---|
| 1 | 27.0d-β (PR #325) | C-se | tabular LightGBM, R7-A, S-E regression, baseline target |
| 2 | 27.0f-β (PR #332) | C-se-r7a-replica | tabular LightGBM, R7-A, S-E regression, baseline target |
| 3 | 28.0a-β (PR #338) | C-a1-se-r7a-replica | tabular LightGBM, R7-A, S-E regression, baseline target |
| 4 | 28.0b-β (PR #342) | C-a4-top-q-control | tabular LightGBM, R7-A, S-E regression, baseline target |
| 5 | 28.0c-β (PR #345) | C-a0-arch-control | tabular LightGBM, R7-A, S-E regression, baseline target |
| 6 | 29.0a-β (PR #351) | C-d1-target-control | tabular LightGBM, R7-A, S-E regression, baseline target |
| **7** | **29.0b-β (post-preflight)** | **C-d2-arch-control** | **tabular LightGBM, R7-A, S-E regression, baseline target — evaluated INSIDE the sequence-cell evaluation harness** |

### 10.2 7th anchor framing — load-bearing distinction

**Critical**: the 7th anchor is **NOT a sequence model**. It is a **tabular LightGBM control evaluated inside the sequence-cell evaluation harness**.

**Purpose**:
- Verify the sequence-cell evaluation harness can correctly reproduce the tabular LightGBM result (within tolerance n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%)
- **Separate harness drift from sequence-model effect**: if 7th anchor deviates from 6th anchor, the deviation is harness drift (architectural change in the evaluation pipeline). If 7th anchor matches but sequence-model cells deviate, the deviation is genuinely the sequence-model effect.
- Preserve the bit-tight reproduction chain across 7 anchors → high confidence that any Phase 29.0b sequence-model verdict (PASS / FAIL) is attributable to the model class change, not eval pipeline drift

**The 7th anchor uses identical model, features, target, and selection as the 6th anchor**. The only architectural change is the **evaluation harness** (sequence-cell harness instead of tabular harness). If the harness is correctly architected, anchors 6 and 7 must match within tolerance.

### 10.3 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | 7th anchor (C-d2-arch-control) can be definably evaluated inside the sequence-cell evaluation harness; pre-stated tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%) reproducible at 29.0b-β |
| **WARN** | 7th anchor evaluatable but tolerances may need recalibration (e.g., sequence-cell harness handles a different per-pair iteration order); document at 29.0b-α |
| **HALT** | 7th anchor cannot be defined (e.g., sequence-cell evaluation harness cannot consume a tabular LightGBM model — incompatible) |

### 10.4 HALT resolution path

If HALT: separate **preflight rev1 PR** re-architects the sequence-cell evaluation harness to support tabular controls. High-stakes; bit-tight chain extension is a binding contract.

---

## 11. Audit dimension 8 — Artifact / storage footprint estimate (WARN-only)

### 11.1 Estimates

| Component | Size estimate |
|---|---|
| Sequence model checkpoint (per architecture variant) | 50-500 MB (depending on architecture — small LSTM ~50 MB; medium Transformer ~500 MB) |
| Closed allowlist of 3-5 sequence architectures | 5 × 500 MB = ~2.5 GB at upper bound |
| Windowed dataset (parquet shards, all 20 pairs) | ~5-6 GB raw; ~2-3 GB compressed |
| Intermediate eval artifacts (parquet sweep results) | ~50-100 MB (similar to 29.0a) |
| **Total upper bound** | **~12-15 GB** |

### 11.2 gitignore pattern

Extends existing `.gitignore` block for `artifacts/stage29_0b/`:
- model checkpoints: gitignored
- windowed dataset shards: gitignored
- intermediate parquet: gitignored
- only `eval_report.md` + `aggregate_summary.json` + `phase29_section10_sequence_control_baseline.json` committed

### 11.3 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | Total < 20 GB; gitignore pattern applicable; no external storage required |
| **WARN** | Total 20-50 GB; external storage / streaming required |
| **HALT** | Total > 50 GB unmitigated (not the case under proposed allowlist) |

---

## 12. Audit dimension 9 — Runtime / compute budget estimate (WARN-only)

### 12.1 Estimates

| Component | 29.0a-β (CPU) | 29.0b-β estimate (GPU; A0-broad) |
|---|---|---|
| Data load + R7-A drop + per-target precompute | ~25 min | ~25 min (target unchanged from inherited) |
| Per-fit (5 S-E LightGBM regressors @ ~45s each on CPU) | ~4 min | n/a (replaced by sequence models) |
| Per-fit (sequence model; per architecture; estimate) | n/a | ~30-90 min per architecture on single GPU |
| 5-fold OOF | ~10 min | ~150-450 min per architecture (5x amplification); **DIAGNOSTIC-ONLY**; may be skipped if budget-constrained |
| Per-cell evaluation | ~3 min | ~10-30 min (sequence-cell predictions) |
| Total full sweep | ~50 min | ~3-8 hours per architecture (single GPU; production OOF skipped or sampled) |

### 12.2 Closed allowlist size implication

- 3 architectures × 6 hours/architecture = ~18 hours full sweep
- 5 architectures × 6 hours/architecture = ~30 hours full sweep
- Recommendation: 29.0b-α allowlist with **3-5 sequence architectures** (final count locked at α)

### 12.3 Verdict criteria

| Verdict | Criterion |
|---|---|
| **PASS** | Total ≤ 24 hours; acceptable for research iteration |
| **WARN** | Total 24-72 hours; affects time-to-verdict; consider OOF sampling / parallel multi-GPU |
| **HALT** | Total > 72 hours under proposed scope (not the case for 3-5 architectures on single GPU) |

---

## 13. Deterministic reproducibility requirements

### 13.1 Seed contract

- **Seed = 42** (inherited from 27.0c OOF / 28.0c OOF / 29.0a OOF)
- Per-fold: `seed = OOF_SEED + fold_idx`
- Per-architecture: `seed = OOF_SEED + arch_idx` (if multi-architecture sub-phase)

### 13.2 PyTorch determinism

```python
import torch
torch.manual_seed(42)
torch.cuda.manual_seed_all(42)
torch.use_deterministic_algorithms(True, warn_only=False)  # strict
# Environment: CUBLAS_WORKSPACE_CONFIG=":4096:8" or ":16:8"
```

### 13.3 CUDA non-determinism mitigation

- CUDA convolutions: `torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False`
- Some operations may not have deterministic implementations (e.g., scatter); falls back to `warn_only=True` if blocking — but flagged in 29.0b-α
- Data loader: `num_workers=0` or per-worker seeding

### 13.4 Bit-tight reproduction contract

For the **7th anchor (C-d2-arch-control)** to bit-tight reproduce the 6th anchor (C-d1-target-control), the **tabular LightGBM model** is identical (same seed; same hyperparameters; same train data). The sequence-cell evaluation harness is the only architectural change. Deterministic LightGBM is already guaranteed by inherited 27.0d pattern.

For the **sequence-model cells**, deterministic reproduction is required across multiple β-eval runs of the same 29.0b-β PR. This is the §13.2 / §13.3 contract.

---

## 14. Scope declaration: Single-axis A0-broad on R7-A only

### 14.1 Locked at preflight

**Phase 29.0b first sequence sub-phase = single-axis A0-broad on R7-A only**. Specifically:

- **Axis**: sequence / NN model class (changing model class from tabular LightGBM to sequence/NN)
- **Feature surface**: **R7-A only** (4 features: pair, direction, atr_at_signal_pip, spread_at_signal_pip); R-B feature expansion **NOT** included at 29.0b
- **Target**: triple-barrier realised PnL (K_FAV=1.5 / K_ADV=1.0 / H_M1=60); inherited from 28.0c / 29.0a target-control
- **Selection rule**: top-q on score with quantile family {5, 10, 20, 30, 40}; inherited
- **Loss**: TBD at 29.0b-α (likely symmetric Huber α=0.9 on regression target, or cross-entropy on classification — locked at α)
- **Baseline reference**: Phase 28 §10 inherited (target unchanged)

### 14.2 R-B remains deferred-not-foreclosed

- R-B feature class (path-shape / microstructure / multi-TF / calendar / cross-asset) **NOT** included at 29.0b
- R-B status: **deferred-not-foreclosed** per PR #348 §6 Scope III + PR #352 §13.1
- Admissible later via:
  - Separate Path 2 (R-B alone, single-axis tabular) — Tier 3 per PR #352
  - Joint Path 4 (A0-broad + R-B joint, Policy C) — DISSENT 1 per PR #352; requires explicit α motivation block + attribution ambiguity handling

### 14.3 Joint Path 4 remains admissible later

- Joint A0-broad + R-B remains **DISSENT 1** per PR #352 §11
- Admissible at a **later sub-phase** under Policy C with explicit α motivation
- **NOT** elevated at preflight; preflight scope locks single-axis A0-broad first to establish sequence-cell scaffolding (NG#A0-broad-* / sequence-cell FAIL-FAST / 7th anchor) cleanly before joint admission

### 14.4 Rationale

Phase 29.0a-β (A2 target redesign) established the per-target FAIL-FAST + target-control pattern under single-axis A2. The same single-axis pattern at 29.0b (A0-broad single-axis on R7-A) lets the 7th anchor + sequence-cell evaluation harness be established cleanly before joint complexity is introduced.

---

## 15. PASS / WARN / HALT outcome ladder + aggregate gate

### 15.1 Per-dimension verdict (assessed at preflight authoring)

The verdicts below are the **preflight authoring's findings**. Each is locked at preflight merge.

| # | Dimension | Gating | Expected verdict at preflight |
|---|---|---|---|
| 1 | GPU availability | HALT-gated | TBD at audit-write time (likely PASS if CUDA device available; HALT if CPU-only) |
| 2 | Sequence/NN training stack | WARN-only | PASS (PyTorch recommended; lock deferred to 29.0b-α) |
| 3 | Windowed dataset feasibility | HALT-gated | PASS (shape definable; regeneration script trivial; footprint ~5-6 GB) |
| 4 | M1 / M5 alignment | HALT-gated | PASS (trivial extension of existing `_build_pair_runtime`) |
| 5 | Sequence-cell D-1 harness | HALT-gated | PASS (D-1 extends to sequence inputs verbatim; per-row scoring identical to tabular) |
| 6 | Phase 22 frozen-OOS compatibility | WARN-only | WARN (regeneration step required; documented at 29.0b-α) |
| 7 | Sequence baseline-control reproduction | HALT-gated | PASS (7th anchor definable; tabular LightGBM control in sequence-cell harness) |
| 8 | Artifact / storage footprint | WARN-only | PASS (~12-15 GB total; gitignored) |
| 9 | Runtime / compute budget | WARN-only | WARN (~18-30 hours for 3-5 architectures; affects time-to-verdict) |

**Note**: dimension 1 (GPU availability) is the only verdict that depends on **execution environment**, not on memo-level audit content. The preflight author MUST verify GPU availability at memo merge time and adjust dimension 1's verdict accordingly. If GPU is unavailable at the user's research environment, dimension 1 is HALT and aggregate is `HALT_29_0B_ALPHA_BLOCKED`.

### 15.2 Aggregate gate

**Aggregate criterion**: **all 5 HALT-gated dimensions must be PASS or WARN**. WARN-only dimensions never block aggregate PASS.

If **all HALT-gated dimensions PASS or WARN** → aggregate verdict = **`PASS_29_0B_ALPHA_AUTHORISED`**.

If **any HALT-gated dimension HALT** → aggregate verdict = **`HALT_29_0B_ALPHA_BLOCKED`**; the specific dimension's HALT resolution path becomes the next-PR target.

### 15.3 Aggregate verdict semantics

| Aggregate verdict | Meaning |
|---|---|
| **`PASS_29_0B_ALPHA_AUTHORISED`** | **Necessary-but-not-sufficient** condition for 29.0b-α authoring. No HALT-gated blocker detected. **Does NOT auto-initiate** 29.0b-α PR. User must explicitly invoke 29.0b-α authoring with a separate instruction subsequent to this preflight merge. |
| **`HALT_29_0B_ALPHA_BLOCKED`** | 29.0b-α PR authoring is **blocked**. The specific HALT-gated dimension's resolution path (§ that dimension's HALT resolution) determines the next PR (e.g., infrastructure setup PR for GPU HALT; scope amendment PR for windowed dataset HALT; preflight rev1 PR for sequence baseline-control HALT). |

### 15.4 No auto-route

**Critical**: even if aggregate verdict is `PASS_29_0B_ALPHA_AUTHORISED`, **no automatic next PR is created**. The user must explicitly instruct the 29.0b-α A0-broad design memo PR authoring as a separate step. This is the Path 1 PRIMARY preflight-gated sequencing semantics from PR #352 §0 / §15.1.

---

## 16. Open questions / unknowns deferred to 29.0b-α

The preflight audit records these as deferred; each is addressed at the 29.0b-α design memo (if aggregate PASS).

1. **Closed sequence-architecture allowlist** (3-5 variants from {LSTM / GRU / Temporal CNN / Transformer encoder / multi-head NN}; final allowlist + α-fixed numerics) — deferred to 29.0b-α
2. **Windowed dataset shape final lock** (N = 32 recommended; bid+ask OHLC vs OHLCV; normalisation scheme) — deferred to 29.0b-α
3. **Training stack final lock** (PyTorch recommended at preflight; final lock deferred to 29.0b-α)
4. **Loss function for sequence models** (symmetric Huber α=0.9 regression vs cross-entropy classification; locked at α)
5. **Per-architecture H-Cx ladder definition** (analogous to 29.0a H-D1 4-outcome ladder; H-E1 or H-D2 naming TBD)
6. **NG#A0-broad-* anti-collapse guards** (closed allowlist enforcement; no β-time grid sweep; no joint admission at first sub-phase)
7. **Phase 29 §10 baseline reference policy under A0-broad** (target unchanged; Phase 28 §10 inherited per Option 9c)
8. **Hyperparameter defaults** (learning rate; batch size; epochs; early stopping) — locked at α; no β-time grid sweep
9. **Phase 22 frozen-OOS regeneration script details** (window-validity flag; sequence-cell OOS rerun cost) — deferred to 29.0b-α
10. **CUDA non-determinism warning fallback** (if `warn_only=False` blocks some operations, document at 29.0b-α)

---

## 17. Decision rule pre-statement

Approving this PR squash-merge **formally accepts the preflight audit findings**. The decision-rule mapping:

| Aggregate verdict | Next step |
|---|---|
| **`PASS_29_0B_ALPHA_AUTHORISED`** | User may instruct authoring of `docs/design/phase29_0b_alpha_a0_broad_design_memo.md` (separate later PR; user-instructed). No auto-route. |
| **`HALT_29_0B_ALPHA_BLOCKED`** | Next PR is the HALT-gated dimension's resolution path (infrastructure / scope amendment / preflight rev1); 29.0b-α authoring blocked until resolution merges. |

**Critical**: merge formally accepts findings only. **Does NOT auto-initiate 29.0b-α even if aggregate is PASS.**

---

## 18. Binding constraints preserved (verbatim from PR #348 §17 + PR #352 §17)

The preflight audit preserves every constraint binding at PR #352 merge:

- D-1 bid/ask executable harness preserved (preflight audits sequence-cell extension; does not amend the binding)
- R7-A subset preserved as the default feature surface (scope-locked at preflight)
- Triple-barrier realised-PnL target preserved as default (target unchanged for A0-broad single-axis)
- Tabular LightGBM model class preserved as default (preflight audits sequence-cell extension; does not change default until 29.0b-α admits A0-broad)
- Top-q on score selection rule preserved
- Symmetric Huber α=0.9 loss preserved as default (final loss locked at 29.0b-α)
- Validation-only selection preserved
- Test touched once preserved
- ADOPT_CANDIDATE wall preserved (preflight does NOT relax)
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating required
- Phase 22 frozen-OOS preserved (preflight audits sequence-cell extension feasibility)
- Production v9 20-pair (Phase 9.12 tip `79ed1e8`) untouched
- **Phase 28 §10 baseline numeric immutable** (n=34626 / Sharpe -0.1732 / ann_pnl -204664.4 / val Sharpe -0.1863); never retroactively modified
- **Phase 29 §10 per-target baseline** (T1/T2/T3/T4 numeric values frozen at PR #351) preserved as archived reference
- No prior verdict modification (Phase 27 + Phase 28 + Phase 29.0a verdicts preserved verbatim)
- MEMORY.md unchanged inside PR
- A1 / A4 / A0-narrow / A2-narrow exhausted statuses preserved
- R-T1 = FALSIFIED_under_A4 / R-T3 = FALSIFIED_under_T3 preserved
- A0-broad / R-B / A3 admissible at Phase 29 (Scope III; PR #348 §6)
- Policy C joint-axis admissibility preserved (PR #348 §7)
- Option 9c dual baseline reference policy preserved (PR #348 §9)
- Phase 27/28 inertia routes NOT admissible without amendment
- No scope amendment in this PR
- No 29.0b-α in this PR
- No 29.0b-β in this PR
- No model training in this PR
- No sequence architecture closed allowlist in this PR (deferred to 29.0b-α)
- No windowed dataset artifact committed in this PR (preflight audits feasibility; generation deferred to 29.0b-β)
- No R-B implementation
- No A3 implementation
- No production change in this PR
- No auto-route after merge (merge formally accepts findings only; subsequent authoring requires separate explicit user instruction)
- This PR is doc-only

---

## 19. What this PR is NOT (consolidated; non-duplicated)

- ❌ Phase 29.0b-α A0-broad design memo (separate later PR if aggregate PASS; user-instructed)
- ❌ Phase 29.0b-β eval implementation (further later PR)
- ❌ Sequence model training (no implementation)
- ❌ Closed sequence-architecture allowlist (deferred to 29.0b-α)
- ❌ Windowed dataset generation artifact committed (preflight audits feasibility; generation deferred to 29.0b-β; no parquet shards committed in this PR)
- ❌ R-B implementation (deferred-not-foreclosed; admissible later via Path 2 alone or Path 4 joint under Policy C)
- ❌ A3 implementation
- ❌ Scope amendment (Scope III + Policy C + Option 9c cover A0-broad single-axis on R7-A; preflight audits feasibility, not admissibility)
- ❌ Phase 29 closure (Path 6 premature per PR #352 §13.3)
- ❌ Production change
- ❌ Prior verdict modification
- ❌ Phase 28 §10 / Phase 29 §10 per-target baseline modification
- ❌ D-1 bid/ask executable harness amendment (preflight audits sequence-cell extension; does not amend the binding)
- ❌ ADOPT_CANDIDATE wall / NG / γ / X-v2 / Phase 22 frozen-OOS relaxation
- ❌ Foreclosure of any path (Path 2 R-B / Path 4 joint / Path 5 A3 / Path 6 closure all remain admissible per PR #352)
- ❌ Auto-initiation of 29.0b-α after merge (even if aggregate PASS)
- ❌ MEMORY.md edit inside PR

---

## 20. References

### Phase 29 PRs

- **PR #348** — Phase 29 kickoff (Scope III / Policy C / Option 9c)
- **PR #349** — Phase 29 first-mover routing review
- **PR #350** — Phase 29.0a-α A2 target redesign design memo
- **PR #351** — Phase 29.0a-β A2 target redesign eval (A2-narrow FALSIFIED; R-T3 = FALSIFIED_under_T3)
- **PR #352** — Phase 29 post-29.0a routing review (Path 1 PRIMARY preflight-gated)
- **This PR** — A0-broad preflight audit (first concrete PR under Path 1 PRIMARY)

### Phase 28 (predecessor; pattern source)

- **PR #340** — Phase 28 scope amendment (doc-only audit template)
- **PR #344** — Phase 28.0c-α A0-narrow design memo (25-section pattern source)
- **PR #345** — Phase 28.0c-β A0-narrow eval (5th anchor in bit-tight chain)
- **PR #347** — Phase 28 closure memo

### Phase 27 inheritance

- **PR #325** — Phase 27.0d-β S-E regression (1st anchor in bit-tight chain; tabular control source)
- **PR #332** — Phase 27.0f-β (2nd anchor)
- **PR #334** — Phase 27 closure memo

### Binding contracts

- **PR #279** — γ closure (production behavior contract; preserved)
- **Phase 22 frozen-OOS contract** (preserved)
- **X-v2 OOS gating** (required for any future production deployment)
- **Phase 9.12 production v9 closure tip `79ed1e8`** (production v9 20-pair; untouched throughout Phase 27 / Phase 28 / Phase 29)

---

*End of `docs/design/phase29_a0_broad_preflight_audit.md`.*
