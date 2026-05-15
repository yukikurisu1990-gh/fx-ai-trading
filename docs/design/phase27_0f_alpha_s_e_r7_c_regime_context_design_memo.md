# Phase 27.0f-α — S-E + R7-C Regime/Context Feature Design Memo

**Type**: doc-only design memo
**Status**: tier-promotes S-E + R7-C cell *admissible at 27.0f-α* (PR #330) → *formal at 27.0f-β*; does NOT trigger 27.0f-β implementation
**Branch**: `research/phase27-0f-alpha-s-e-r7-c-design-memo`
**Base**: master @ 9ac2c5f (post-PR #330 / Phase 27 R7-C scope amendment merge)
**Pattern**: analogous to PR #312 / #317 / #320 / #324 / #327 design memos under Phase 27
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the **canonical 27.0f-α design memo**. On merge, the S-E + R7-C 3-cell structure specified here becomes *formal at sub-phase 27.0f-β*, meaning a future 27.0f-β eval PR may evaluate it under the policies bound here without further scope amendment. It does NOT by itself authorise the 27.0f-β eval implementation — that requires a separate later user instruction.*

Same approval-then-defer pattern as PR #320 (27.0c-α) / PR #324 (27.0d-α) / PR #327 (27.0e-α).

This PR is doc-only. No `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md` is touched.

---

## 1. Why 27.0f-α exists

The R7-C scope amendment (PR #330, master 9ac2c5f) admitted R7-C (Phase 25 F5 regime/context closed allowlist; 3 features additive to R7-A) to Phase 27 formal evaluation. This design memo specifies the 27.0f-β contract: cell structure, feature construction details, volume pre-flight, quantile-of-val family policy, BaselineMismatchError inheritance, H-B6 falsification criteria, sanity probe extensions.

### 1.1 Targeted hypotheses

- **H-B6 (primary; from PR #329 §3.2)**: top-tail adversarial selection / regime confound in regressor confidence. R7-C adds spread / volume regime features that should let the regressor distinguish "high-vol high-EV" from "high-vol high-cost" rows.
- **H-B2 (implicit)**: R7-A too narrow. Adding 3 features tests whether broader feature space recovers monetisation under R7-A's score structure.

### 1.2 Targeted predictions

- If C-se-rcw produces H2 PASS at some q ∈ {5, 10, 20, 30, 40} → **STRONG_SUPPORT** for H-B6; PROMISING_BUT_NEEDS_OOS branch triggered
- If C-se-rcw H1m PASS AND Sharpe meaningfully better than C-se-r7a-replica → **PARTIAL_SUPPORT**; route to R-T1 or R-B
- If C-se-rcw matches C-se-r7a-replica → **FALSIFIED — R7-C insufficient**; bottleneck is elsewhere; route to R-B / R-T1 / R-T3 / R-E
- If C-se-rcw H1-weak FAIL → **PARTIALLY_FALSIFIED + new question**

**27.0f-α scope is narrow**: define the 27.0f-β contract within the R7-C admissibility already granted at PR #330. No new scope amendments, no clause 2 modification, no Phase 25 reopening.

---

## 2. Inheritance bindings (FIXED for 27.0f-β)

The following are FIXED for 27.0f-β and CANNOT be relaxed by this design memo:

| Binding | Source | Status |
|---|---|---|
| R7-A 4-feature allowlist (`pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`) | PR #311 / #313 / #323 | FIXED — preserved as subset |
| R7-C 3-feature additive allowlist (`f5a_spread_z_50`, `f5b_volume_z_50`, `f5c_high_spread_low_vol_50`) | PR #330 §3.1 | FIXED — closed; no other F5 features admissible |
| 25.0a-β path-quality dataset (spread column source) | inherited | FIXED |
| M1 BA `volume` column | Phase 25.0f-α §2.5 / PR #295 / PR #330 §3.4 | FIXED — pre-flight HALT contract inherited (§4 below) |
| F5 causal construction rules (Phase 25.0f-α §2.4 / §2.5 / §2.6 / §2.7) | PR #295; PR #330 inheritance | FIXED — verbatim |
| 70/15/15 chronological split | inherited | FIXED |
| Triple-barrier inputs (K_FAV=1.5·ATR, K_ADV=1.0·ATR, H_M1=60) | inherited | FIXED |
| `_compute_realised_barrier_pnl` (D-1 binding; bid/ask executable) | inherited | FIXED — both formal verdict PnL and S-E regression target |
| L-1 ternary class encoding (TP/SL/TIME) | inherited | PRESERVED for sanity probe + C-sb-baseline only |
| LightGBMRegressor + Huber (α=0.9) config | 27.0d-α §4 | FIXED — applies to both C-se-rcw (7 features) and C-se-r7a-replica (4 features) |
| LightGBM multiclass head config | 26.0d / 27.0d | FIXED — used ONLY for C-sb-baseline replica |
| Verdict ladder H1/H2/H3/H4 thresholds | inherited | FIXED |
| Quantile-of-val family policy (per-cell per 27.0e-α D-X4) | inherited / 27.0e | FIXED — per-cell choice |
| Validation-only cutoff selection; test touched once | inherited | FIXED |
| Cross-cell aggregation (26.0c-α §7.2) | inherited | FIXED — SPLIT_VERDICT_ROUTE_TO_REVIEW branch admissible |
| ADOPT_CANDIDATE 8-gate A0-A5 SEPARATE-PR wall | inherited | FIXED |
| BaselineMismatchError tolerances (n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip) | inherited | FIXED |
| D10 amendment (per §6.1 — now 3-artifact form) | 27.0d-α §7.5 / 27.0e-α §7.5 | AMENDED — see §6.1 |
| 2-layer selection-overfit guard | 27.0d-α §13 | FIXED |
| 5-fold OOF DIAGNOSTIC-ONLY (seed=42) | 27.0c-α / 27.0d-α | FIXED |
| Clause 2 diagnostic-only binding | kickoff §8 / PR #323 / PR #330 | **load-bearing; unchanged** |
| Phase 22 frozen-OOS contract | inherited | FIXED |
| Production v9 20-pair tip 79ed1e8 | inherited | UNTOUCHED |

The substantive scope of 27.0f-β is the **R7-C feature widening** (3 features additive to R7-A). All other bindings carry forward unchanged from 27.0e-α.

---

## 3. R7-C feature construction details (D-Z1; verbatim from Phase 25.0f-α inheritance)

### 3.1 `f5a_spread_z_50`

```
Source: spread_at_signal_pip column from path_quality_dataset.parquet (already loaded)
Step 1: deduplicate to (pair, signal_ts) → spread series per pair (drop direction axis;
        spread is direction-independent at the (pair, signal_ts) level)
Step 2: per-pair, shift(1) the spread series → causal_spread
Step 3: per-pair, rolling_mean(causal_spread, window=50, min_periods=50)
Step 4: per-pair, rolling_std(causal_spread, window=50, min_periods=50)
Step 5: f5a_spread_z_50 = (spread - rolling_mean) / rolling_std
Step 6: rolling_std == 0 OR rolling_std NaN → f5a_spread_z_50 = NaN
Step 7: re-attach to (pair, signal_ts) → direction key (broadcast to direction axis)
```

### 3.2 `f5b_volume_z_50`

```
Source: M1 BA jsonl 'volume' column (per pair; loaded by stage23_0a load_m1_ba)
Pre-flight (per Phase 25.0f-α §2.5.1; HALT on failure; see §4):
  - 'volume' column present in every loaded row
  - non-null fraction ≥ 0.99 per pair across eval span
  - M1 → M5 aggregation strictly non-decreasing index, aligned to 25.0a-β
  - volume values non-negative
Step 1: M1 → M5 aggregation = sum over 5 M1 bars per M5 bar (right-closed / right-labeled,
        matching stage23_0a aggregate_m1_to_tf semantics)
Step 2: per-pair, shift(1) the M5 volume series → causal_volume
Step 3: per-pair, rolling_mean(causal_volume, window=50, min_periods=50)
Step 4: per-pair, rolling_std(causal_volume, window=50, min_periods=50)
Step 5: f5b_volume_z_50 = (volume - rolling_mean) / rolling_std
Step 6: rolling_std == 0 OR rolling_std NaN → f5b_volume_z_50 = NaN
Step 7: re-attach to (pair, signal_ts) → direction key
```

### 3.3 `f5c_high_spread_low_vol_50`

```
f5c_high_spread_low_vol_50 = bool((f5a_spread_z_50 > 1.0) AND (f5b_volume_z_50 < -1.0))
NaN propagation: if EITHER f5a or f5b is NaN, f5c is NaN.
```

Captures the **illiquid-stress regime** — H-B6's predicted adversarial top-tail concentration.

### 3.4 D-Z2 — Causal binding (non-negotiable)

`shift(1) BEFORE rolling` is **non-negotiable**. Any reversal of this order (rolling on un-shifted series, then shift after) is an **NG#11 violation** (future-info leak; the row at time t would see information from time t when computing the rolling mean / std that includes time t).

The 27.0f-β implementation MUST include unit tests that verify:
- `test_f5a_causal_shift_before_rolling`
- `test_f5b_causal_shift_before_rolling`
- `test_f5c_inherits_causality_from_inputs`

Any unit test failure on causality is a 27.0f-β implementation halt (NOT a 27.0f-α design issue).

---

## 4. Volume pre-flight + R7-C feature NaN policy (D-Z3)

### 4.1 D-Z3.a — Volume pre-flight HALT contract

The 27.0f-β implementation MUST execute the §3.2 pre-flight **BEFORE** any feature computation. Failure modes:

| Failure | HALT exception |
|---|---|
| `volume` column missing in ≥ 1 row | `R7CPreflightError` (NEW exception, analogous to `L3PreflightError`) |
| non-null fraction < 0.99 for any pair | `R7CPreflightError` |
| M1 → M5 aggregation index not strictly non-decreasing | `R7CPreflightError` |
| volume < 0 for any row | `R7CPreflightError` |

`R7CPreflightError` is a `RuntimeError` subclass defined in `stage27_0f_*` module. The exception MUST be raised with a clear failure message indicating which check failed and the affected pair(s) / row counts.

### 4.2 D-Z3.b — R7-C feature NaN row-drop policy

Rows with NaN in ANY R7-C feature (`f5a_spread_z_50`, `f5b_volume_z_50`, or `f5c_high_spread_low_vol_50`) are **DROPPED** from train / val / test, analogous to R7-A row-drop policy from PR #313.

Expected drop sources:
- First 50 M5 bars per pair (lookback warmup) before `min_periods=50` is satisfied
- Sparse / zero rolling-std rows (rare; pathological)
- Volume gaps (should be caught by pre-flight in §4.1; defensive secondary catch)

Expected drop rate: ~50 rows per pair × 20 pairs ≈ 1,000 rows per split (negligible vs ~600k val / ~600k test ≈ 0.2%).

### 4.3 D-Z3.c — Split-level drop count HALT

If total R7-C row-drop > **1%** of split rows on val or test, HALT with `SanityProbeError`. At expected ~0.2% drop rate, this is a 5× safety margin. The HALT message MUST indicate which split exceeded the threshold and the absolute row count.

The 1% threshold is binding: if the actual drop rate exceeds this, something has gone wrong with the volume data or aggregation, and the 27.0f-β eval cannot proceed with confidence.

---

## 5. Quantile-of-val family policy for 27.0f cells (D-Z4)

### 5.1 Decision

| Cell | Quantile family |
|---|---|
| **C-se-rcw** | **{5, 10, 20, 30, 40}** (inherited 27.0d full family; NOT 27.0e trimmed) |
| **C-se-r7a-replica** | **{5, 10, 20, 30, 40}** (inherited 27.0d full family; matches C-se-rcw for direct comparability) |
| **C-sb-baseline** | **{5, 10, 20, 30, 40}** (inherited unchanged; preserves baseline match) |

### 5.2 Rationale

The 27.0e-β finding (PR #328) was that the trim {5, 7.5, 10} made Sharpe WORSE under R7-A. H-B6 predicts the regressor's top-q is structurally adversarial. For 27.0f cells with the **wider R7-A + R7-C 7-feature** set, two questions are entangled:

1. (Channel A — R7-C feature widening) Does adding regime features help?
2. (Channel C — quantile trim) Does narrower q help?

Using the inherited {5, 10, 20, 30, 40} family for **all 3 cells** isolates the Channel A effect from the Channel C effect:

- If C-se-rcw at any q passes H2 → R7-C helped (Channel A confirmed)
- If C-se-rcw at q=40 specifically improves vs C-se-r7a-replica at q=40 → R7-C unlocks the wide-selection region too
- If C-se-rcw at q=5/q=7.5/q=10 specifically improves → would require a separate 27.0g sub-phase to disentangle (deferred; not addressed here)

The 27.0e trim {5, 7.5, 10} is **rejected** for 27.0f because it would conflate the two channels and prevent clean H-B6 evaluation.

---

## 6. Cell structure (D-Z5; D-Z6)

### 6.1 3-cell structure

| Cell ID | Score | Feature set | Quantile family | Purpose |
|---|---|---|---|---|
| **C-se-rcw** | S-E = `regressor.predict(row)` (LightGBMRegressor + Huber) | R7-A + R7-C (7 features) | {5, 10, 20, 30, 40} | substantive — tests H-B6 + H-B2 directly |
| **C-se-r7a-replica** | S-E = `regressor.predict(row)` (LightGBMRegressor + Huber) | R7-A only (4 features) | {5, 10, 20, 30, 40} | within-eval ablation control — should reproduce 27.0d C-se outcome (n=184,703, Sharpe -0.483, Spearman +0.4381 at q=40) |
| **C-sb-baseline** | raw `P(TP) - P(SL)` (LightGBM multiclass head) | R7-A only (4 features) | {5, 10, 20, 30, 40} | inheritance-chain match — must reproduce 27.0b C-alpha0 / R6-new-A C02 baseline |

**3 cells × 5 quantiles = 15 (cell, q) pairs.** Multiple-testing exposure noted in §11 §21.

### 6.1.1 D-Z6 — Why include C-se-r7a-replica (within-eval ablation control)

A 2-cell structure (C-se-rcw + C-sb-baseline) would force comparison of R7-C effects via re-citing PR #325 artifacts for the 27.0d C-se outcome. Adding C-se-r7a-replica:

- **Pro**: provides clean within-eval comparison, controlled for split / random seed / refit-on-full-train state. Isolates Channel A (R7-C feature widening) from cross-run noise.
- **Pro**: reproduces 27.0d C-se outcome within tight tolerance (Sharpe ±5e-3 expected; not as tight as C-sb-baseline because regression fit is sensitive to feature column order, but `random_state=42` should give deterministic results)
- **Pro**: drift detection (if C-se-r7a-replica drifts > 5e-3 from 27.0d C-se → DIAGNOSTIC-ONLY WARN, investigate)
- **Con**: 1 additional regressor fit per run (~30s based on 27.0d precedent) — acceptable cost

D-Z6 default: **YES, include C-se-r7a-replica**. Drift policy: **DIAGNOSTIC-ONLY WARN, NOT HALT** (cross-run determinism is best-effort; the C-sb-baseline match check is the hard inheritance-chain guarantee).

### 6.2 D10 amendment for 27.0f (3-artifact form)

"Single model fit" in 27.0f-β means:

- **one** LightGBMRegressor fit on R7-A + R7-C (7 features) — production C-se-rcw head
- **one** LightGBMRegressor fit on R7-A only (4 features) — production C-se-r7a-replica head
- **one** LightGBM multiclass head fit on R7-A only (4 features) — for C-sb-baseline only

Each artifact fit ONCE; no per-cell re-fit; no per-quantile re-fit. The R7-A + R7-C and R7-A-only regressors are deterministic under `random_state=42` and same train data.

Cost (estimated): 3 model fits × ~30s = ~90s + 5-fold OOF on R7-A + R7-C regressor (~30s; DIAGNOSTIC-ONLY) + train PnL precompute (~150s) + scoring (~30s) ≈ **~8-10 min total runtime**.

---

## 7. H-B6 falsification criteria (D-Z7; design-memo binding; pre-stated)

| Row | Outcome | H-B6 status | Routing implication |
|---|---|---|---|
| **1** | C-se-rcw at some q ∈ {5, 10, 20, 30, 40} passes H2 (Sharpe ≥ 0.082 AND ann_pnl ≥ 180) | **STRONG_SUPPORT** | PROMISING_BUT_NEEDS_OOS branch triggered → separate A0-A5 8-gate PR. H-B6 elevated to load-bearing. **Phase 27's first PROMISING outcome** |
| **2** | C-se-rcw H1m PASS (Spearman ≥ 0.10) AND Sharpe improvement over C-se-r7a-replica > 0.05 at SAME q (or at C-se-rcw's val-selected q vs C-se-r7a-replica's val-selected q) but no H2 PASS | **PARTIAL_SUPPORT** | regime features help directionally but not enough; route to R-T1 (further selection-rule revision) OR R-B (microstructure feature widening) |
| **3** | C-se-rcw H1m PASS AND Sharpe within ±0.05 of C-se-r7a-replica (no meaningful improvement) | **FALSIFIED — R7-C INSUFFICIENT** | regime features don't help; bottleneck is elsewhere; route to R-B (different feature axis) OR R-T1 / R-T3 / R-E |
| **4** | C-se-rcw H1-weak FAIL (Spearman ≤ 0.05) | **PARTIALLY_FALSIFIED + new question** | adding R7-C destroyed ranking signal — sub-question whether R7-A's clean ranking was load-bearing for feature interaction. Route to R-T1 OR R-E |

Row precedence: **1 > 2 > 3 > 4**; strict thresholds; no ε tolerance (analogous to D-K8 from 27.0e-α).

Secondary discriminator (binding): the **delta-Sharpe vs C-se-r7a-replica** at the val-selected q (or matched q) is the key signal for Row 2 vs Row 3 disambiguation. The within-eval ablation control (C-se-r7a-replica) is what makes Rows 2 vs 3 well-defined — without it, the test reduces to a noisy comparison with PR #325 artifacts.

D-Z7 implementation: `compute_h_b6_falsification_outcome(cell_results)` returns one of `STRONG_SUPPORT | PARTIAL_SUPPORT | FALSIFIED_R7C_INSUFFICIENT | PARTIALLY_FALSIFIED_NEW_QUESTION | NEEDS_REVIEW` (defensive). 27.0f-β `eval_report.md §22` MUST cite exactly one row and the routing implication verbatim.

---

## 8. Verdict tree (inherited unchanged)

Inherited verbatim from 27.0e-α §8 / 27.0d-α §8 / 27.0c-α §8 / 27.0b-α / 26.0c-α / 26.0d-α:

- H1-weak: Spearman > 0.05
- H1-meaningful: Spearman ≥ 0.10
- H2: Sharpe ≥ 0.082 AND ann_pnl ≥ 180
- H3: Sharpe > −0.192
- H4: Sharpe ≥ 0
- Cross-cell aggregation per 26.0c-α §7.2 — SPLIT_VERDICT_ROUTE_TO_REVIEW branch admissible
- H2 PASS → **PROMISING_BUT_NEEDS_OOS only**
- ADOPT_CANDIDATE requires SEPARATE A0-A5 8-gate PR
- NG#10 / NG#11 not relaxed

---

## 9. Mandatory clauses (clauses 1–5 verbatim; clause 6 = PR #330 §6 verbatim)

Clauses 1–5 inherited verbatim. Clause 2 **load-bearing for R-T1 / R-T3 framings**; unchanged here.

**Clause 6 verbatim from PR #330 §6** (canonical R7-C-updated wording from PR #330 forward):

> *6. Phase 27 scope. Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff. **R7-C (Phase 25 F5 regime/context closed allowlist) was promoted from "requires SEPARATE Phase 27 scope-amendment PR" to "admissible at 27.0f-α design memo" via Phase 27 R7-C scope-amendment PR #330. The R7-C closed allowlist is `[f5a_spread_z_50, f5b_volume_z_50, f5c_high_spread_low_vol_50]` (3 features; additive to R7-A; constructed per Phase 25.0f-α §2.4 / §2.5 / §2.6 causal rules; pre-flight HALT if M1 volume missing/corrupt). R7-B remains admissible only after its own separate scope amendment.** R7-D and R7-Other remain NOT admissible. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D was promoted from admissible-but-deferred to formal at 27.0c-β via PR #320. S-E was promoted from "requires scope amendment" to "admissible at 27.0d-α design memo" via PR #323; on PR #324 merge S-E became formal at 27.0d-β. 27.0e R-T2 trimmed-quantile policy admissible under existing clause 6 + clause 2 (per PR #327 §0.1); on PR #327 merge became formal at 27.0e-β. S-Other NOT admissible. Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.*

This design memo IS the kickoff §5 / clause 6 / PR #330 "27.0f-α design memo" required for R7-C's cell-structure tier promotion. On merge, the S-E + R7-C 3-cell structure becomes *formal at sub-phase 27.0f-β*.

---

## 10. Sanity probe (inherited items 1-13 + NEW R7-C items 14-19)

Inherited verbatim from 27.0e-α §10 (items 1–13). NEW for 27.0f:

| # | Item | Status |
|---|---|---|
| 14 | **R7-C volume pre-flight check** (per §4 / D-Z3.a) | **HALT-on-failure** (`R7CPreflightError`) |
| 15 | **R7-C feature NaN rate per split** (per §4 / D-Z3.b) | HALT if > 5% per feature per split |
| 16 | **R7-C row-drop count per split** (per §4 / D-Z3.c) | **HALT if > 1% of split rows** (`SanityProbeError`) |
| 17 | **R7-C feature distribution on train** (DIAGNOSTIC-ONLY): mean / p5 / p50 / p95 / std / min / max for each R7-C feature | WARN-only on outliers |
| 18 | **Per-pair R7-C feature stats** (DIAGNOSTIC-ONLY): per-pair p50 of `f5a_spread_z_50` + `f5b_volume_z_50` + activation rate of `f5c_high_spread_low_vol_50` | WARN-only |
| 19 | **Top-tail regime audit (NEW; DIAGNOSTIC-ONLY; H-B6 mechanism diagnosis)**: in C-se-rcw top-q val rows (q=10 and q=20), report mean `f5a_spread_z_50`, mean `f5b_volume_z_50`, fraction with `f5c_high_spread_low_vol_50=True`. If concentrated in `f5c_high_spread_low_vol_50=True` regime → H-B6 mechanism diagnosed | WARN-only |

Probe writes `artifacts/stage27_0f/sanity_probe.json` + `sanity_probe_run.log`.

Items 14–19 are deferred at `--sanity-probe-only` stage (computed post-fit; same pattern as 27.0d / 27.0e items 7–13).

---

## 11. Eval report (27.0f-β) mandatory sections (D-Z8)

25 sections total (up from 22 in 27.0e-β):

| § | Content | Source |
|---|---|---|
| 1 | Mandatory clauses 1–6 verbatim (clause 6 = PR #330 §6) | INHERITED |
| 2 | D-1 binding restated | INHERITED |
| 3 | R7-A + R7-C feature set restated (7 features; closed allowlist) | NEW (27.0f-specific) |
| 4 | 3-cell definitions (C-se-rcw + C-se-r7a-replica + C-sb-baseline) | NEW (27.0f-specific) |
| 5 | Sanity probe (incl. NEW items 14–19; HALT-conditions audit) | NEW + INHERITED |
| 6 | Pre-flight diagnostics + row-drop + split dates (incl. R7-C row-drop) | INHERITED + UPDATED |
| 7 | All formal cells primary table (3 cells × 5 quantiles = 15 (cell, q) pairs) | INHERITED form |
| 8 | Val-selected cell\* + q\* — formal verdict source | INHERITED |
| 9 | Aggregate H1/H2/H3/H4 outcome + verdict | INHERITED |
| 10 | Cross-cell aggregation (26.0c-α §7.2) | INHERITED |
| 11 | **MANDATORY** 6-column baseline comparison: 26.0d / 27.0b / 27.0c / 27.0d / 27.0e / 27.0f val-selected | NEW (adds 27.0e column) |
| 12 | **MANDATORY** C-sb-baseline reproduction check (FAIL-FAST HALT) | INHERITED |
| 13 | **MANDATORY** C-se-r7a-replica reproduction check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN; NOT HALT) | NEW |
| 14 | **MANDATORY** per-pair Sharpe contribution table (val-selected; D4 sort) | INHERITED |
| 15 | **MANDATORY** pair concentration per cell | INHERITED |
| 16 | Classification-quality diagnostics (multiclass head; C-sb-baseline only) | INHERITED (DIAGNOSTIC-ONLY) |
| 17 | Regressor feature importance: R7-A (4-bucket for C-se-r7a-replica) and R7-A+R7-C (7-bucket for C-se-rcw) | INHERITED + UPDATED |
| 18 | Predicted-PnL distribution train/val/test (both regressors) | INHERITED |
| 19 | Predicted-vs-realised correlation diagnostic (OOF + per-split for C-se-rcw) | INHERITED |
| 20 | Regressor MAE + R² on train/val/test (both regressors) | INHERITED |
| 21 | Multiple-testing caveat (3 cells × 5 quantiles = 15 (cell, q) pairs; up from 10 in 27.0e) | UPDATED |
| 22 | **H-B6 falsification outcome** (per §7 4-row table binding) | NEW (analogous to H-B5 in 27.0e-β) |
| 23 | **NEW: Top-tail regime audit** (from probe §10 item 19) — DIAGNOSTIC-ONLY; directly diagnoses H-B6 mechanism | NEW |
| 24 | **NEW: C-se-r7a-replica vs 27.0d C-se delta** — DIAGNOSTIC-ONLY; isolates R7-C effect from cross-run noise (re-cite 27.0d C-se metrics from `artifacts/stage27_0d/sweep_results.json` with fallback to PR #325 constants) | NEW |
| 25 | Verdict statement (incl. H-B6 outcome row) | INHERITED + NEW |

---

## 12. 27.0f-β implementation contract (high-level only; no code here)

The 27.0f-β implementation PR (separate later instruction) will:

- Author `scripts/stage27_0f_s_e_r7_c_regime_eval.py` inheriting from `scripts/stage27_0e_s_e_quantile_trim_eval.py`
- Author `tests/unit/test_stage27_0f_s_e_r7_c_regime_eval.py`
- Implement `R7CPreflightError(RuntimeError)` (new exception)
- Implement `build_r7_c_features(df, pair_runtime_map)` — adds `f5a_spread_z_50` + `f5b_volume_z_50` + `f5c_high_spread_low_vol_50` per §3 spec; causality unit tests per §3.4
- Implement `verify_volume_preflight(pair_runtime_map, pairs)` per §4.1 — HALT-on-failure
- Implement `drop_rows_with_missing_r7_c_features(df)` — analogous to `drop_rows_with_missing_new_features`
- Extend `build_s_e_cells_trimmed()` → `build_s_e_r7_c_cells()` returning 3 cells with `feature_set` field
- Extend `evaluate_cell_27_0e` → `evaluate_cell_27_0f` reading `cell["feature_set"]` to choose feature columns
- Extend `run_sanity_probe_27_0e` → `run_sanity_probe_27_0f` adding items 14–19
- Implement `compute_h_b6_falsification_outcome(cell_results)` per §7 binding
- Implement `compute_top_tail_regime_audit(val_score, val_features, q_list)` per §10 item 19 / §11 §23
- Emit `artifacts/stage27_0f/eval_report.md` with all 25 sections
- Add `.gitignore` entries for `artifacts/stage27_0f/*` intermediates
- Run sanity probe FIRST, then full sweep
- BaselineMismatchError HALT on C-sb-baseline non-match (FAIL-FAST)
- DIAGNOSTIC-ONLY WARN on C-se-r7a-replica drift > 5e-3 Sharpe vs 27.0d C-se (NOT HALT; cross-run determinism best-effort)
- Lint via `run_custom_checks.py` + `ruff check` + `ruff format --check` before push
- CI green before merge

None of the above is authorised by THIS PR.

---

## 13. Selection-overfit handling — explicit binding (inherited 2-layer guard)

> *S-E's three trainable artifacts (LightGBMRegressor on R7-A + R7-C; LightGBMRegressor on R7-A only; LightGBM multiclass head on R7-A only) are ALL fit on train-only data. Val data is used ONLY for cutoff selection (quantile-of-val q\* per cell). Test data is touched exactly once at the val-selected (cell\*, q\*). 5-fold OOF DIAGNOSTIC-ONLY (computed on R7-A + R7-C regressor only). Any deviation is a NG#10 violation.*

The 3-cell structure increases multiple-testing exposure to **15 (cell, q) pairs** (up from 10 in 27.0e). The §22 H-B6 falsification table mitigates this by **pre-stating** the routing implication of each outcome, preventing post-hoc q\* selection bias.

The R7-C feature widening (7 features vs 4 in R7-A) increases model capacity. Selection-overfit risk on val-cutoff selection is monitored via:
- `val_n_trades / val_baseline_n_trades` (inherited trade-count budget audit)
- Per-pair concentration diagnostic (inherited)
- §22 H-B6 outcome row (binding; pre-stated)

---

## 14. What this PR will NOT do

- ❌ Authorise 27.0f-β eval implementation (separate later user instruction)
- ❌ Authorise post-27.0f routing review
- ❌ Authorise any other Phase 27 sub-phase (27.0g / 27.0h / ...)
- ❌ Authorise R7-B (still requires its own SEPARATE scope-amendment PR)
- ❌ Authorise R7-D / R7-Other (NOT admissible)
- ❌ Authorise broader F5-c interactions beyond `f5c_high_spread_low_vol_50` (per PR #330 §3.3; broader F5-c via future scope amendment if R-C is REJECT)
- ❌ Authorise F5-d (tick-level micro-imbalance) / F5-e (pair-level liquidity rank) — deferred per Phase 25.0f-α §2.3
- ❌ Authorise R-T1 (S-E selection redesign — separate route from #329)
- ❌ Authorise R-T3 (pair-concentration formalisation — requires scope amendment; clause 2 modification)
- ❌ Authorise alternative S-E regression-variant cells (MSE / L1 / Tweedie — deferred per 27.0d-α §7.6)
- ❌ Modify Phase 27 scope per kickoff §8 / PR #323 / PR #324 / PR #327 / PR #330 clause 6
- ❌ Modify clause 2 diagnostic-only binding
- ❌ Reopen Phase 25
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b / 27.0c / 27.0d / 27.0e / routing reviews / scope amendments)
- ❌ Relax the ADOPT_CANDIDATE 8-gate A0-A5 wall
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279) / X-v2 OOS gating / Phase 22 frozen-OOS contract / production v9 20-pair tip 79ed1e8
- ❌ Pre-approve any production deployment under any 27.0f-β outcome
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md`
- ❌ Auto-route to 27.0f-β implementation after merge

---

## 15. Sign-off

Phase 27 produces its sixth design memo (after kickoff #316 + 27.0b-α #317 + 27.0c-α #320 + 27.0d-α #324 + 27.0e-α #327). The S-E + R7-C 3-cell structure moves from *admissible at 27.0f-α* (PR #330) → *formal at sub-phase 27.0f-β* on merge of this design memo. The 27.0f-β implementation PR is triggered by a separate later user instruction. No auto-route.

**This PR stops here.**
