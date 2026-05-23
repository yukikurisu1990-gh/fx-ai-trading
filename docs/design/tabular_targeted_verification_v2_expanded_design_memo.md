# Tabular Targeted Verification V2-expanded — Design Memo (V1 Shared Foundation + 6 Major-Axis Sentinels at #325 / #332 / #338 / #342 / #345 / #351; #318 / #321 / #328 Deferred; Allowed Success Label `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES`)

**Type**: doc-only design memo. **No verification code. No rerun. No A0-broad β resumption.**
**Branch**: `research/tabular-targeted-verification-v2-expanded-design`
**Base**: master @ `9c36adf` (post-PR #356 Phase 27–29 Tabular Evaluation Validity Audit merged)
**Date**: 2026-05-24

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Tabular Targeted Verification V2-expanded design memo**. It pre-states the verification contract, the exact six sentinel reproduction contracts, per-sentinel tolerance and expected artifacts, the test-isolation protocol, the row-set policy per sentinel, the scorer identity per sentinel, the allowed outcome labels, the explicit deferred status of #318 / #321 / #328, and the A0-broad eligibility rule that applies under each outcome.*
>
> *This PR does **NOT**:*
>
> - *write verification code (no `scripts/tabular_targeted_verification_v2_expanded_*.py`; no `tests/unit/test_tabular_targeted_verification_v2_expanded_*.py`; no `artifacts/tabular_targeted_verification_v2_expanded/`);*
> - *re-run, re-fit, or recompute any historical metric;*
> - *resume Phase 29.0b-β A0-broad (which remains halted per PR #355 + audit PR #356 + user instruction);*
> - *open the Phase 29.0b-α rev2 amendment PR (deferred per user instruction);*
> - *modify any prior verdict (Phase 27 / Phase 28 / Phase 29.0a verdicts are NOT retroactively edited; verification PASS by itself does NOT reissue any verdict);*
> - *modify the Phase 28 §10 immutable baseline numeric;*
> - *modify the Phase 29.0a per-target baseline JSON;*
> - *touch any β code, production code, eval script, or production artifact;*
> - *modify the WIP branch `research/phase29-0b-beta-a0-broad-sequence-eval` (tip `9ac8fda`); it remains INVALID_FOR_FORMAL_VERDICT on the remote;*
> - *cite EXPLORATORY_ONLY artifacts under `artifacts/stage29_0b/` from the WIP branch as evidence for any verification claim;*
> - *use the labels `PASS_TABULAR_EVIDENCE_RECONFIRMED` / `FULL_TABULAR_EVIDENCE_REBUILT` / `empirically clean` / `historical execution verified` / `tabular evidence reconfirmed` / `prior verdicts revalidated` anywhere;*
> - *issue any auto-route from any verification outcome.*

The verification implementation is a **separate later PR** explicitly authorised by the user against the contract this memo pre-states; no implementation begins until that authorisation is given.

---

## 1. Mission

Re-establish, with cleanly committed machine-readable run-provenance, both:

1. **The shared A0-broad comparator foundation** — the tabular ceiling + harness + run-provenance predicates that the eventual A0-broad β v2 H-D2 ladder (per PR #355 §A.4) actually depends on.
2. **The six major-axis negative-conclusion sentinels** — clean reproduction of the six β-evals whose verdicts carry the most weight in the Phase 27–29 evidence picture relevant to A0-broad: #325 (S-E origin / C-se control chain), #332 (R7-C + Fix A), #338 (A1 loss redesign), #342 (A4 selection-rule redesign), #345 (A0-narrow tabular topology), #351 (A2 target redesign).

V2-expanded does **NOT** re-execute the three earlier score / trim sub-axis investigations #318 (S-C TIME penalty) / #321 (S-D calibrated EV) / #328 (S-E quantile family trim); they remain Class U after V2-expanded PASS and the verification report enumerates them explicitly.

---

## 2. Scope binding

### 2.1 Why V2-expanded (not V1 / V2 / V3)

| Scope | Adopted? | Reason |
|---|---|---|
| V1 (foundation only) | NO | Does not address the loss-axis (A1) / selection-rule-axis (A4) / target-axis (A2) negative conclusions that A0-broad's invariants depend on |
| V2 (4 sentinels) | NO | Excluded A1 + A4; user instruction requires inclusion |
| **V2-expanded (foundation + 6 sentinels)** | **YES** | Covers the six major-axis negative conclusions relevant to A0-broad without paying V3's full 9-eval cost |
| V3 (full 9 sentinels) | NO | Includes 3 score sub-axis sentinels (#318/#321/#328) that are not load-bearing for A0-broad's immediate decision |

### 2.2 Included scope (binding)

**A. V1 shared foundation** — all items:

- D-1 bid/ask executable PnL harness identity
- Phase 28 §10 C-sb-baseline reproduction (full row-set)
- A0-broad aligned C-sb-baseline comparator generation (windowed-valid aligned row-set; the formal H-D2 H2 comparator per PR #355 §A.4)
- A0-broad aligned C-d2-arch-control generation (windowed-valid aligned row-set; the formal PARTIAL_DRIFT_TABULAR_REPLICA comparator per PR #355 §A.4)
- Validation-only selection / test-touched-once executable logging
- Row-set manifests
- `contract_hash` / `code_hash` / `data_manifest_hash` / `environment_manifest`
- Machine-readable result artifacts committed
- No reuse of WIP @ `9ac8fda` or EXPLORATORY_ONLY artifacts

**B. Six major-axis sentinel reproductions** at:

| Sentinel | PR | Axis | Verdict to reproduce |
|---|---|---|---|
| **S-1** | #325 / 27.0d-β | S-E regression-on-realised-PnL | C-se H1m PASS Spearman +0.4381 / H2 FAIL realised Sharpe wrong-direction; SPLIT_VERDICT_ROUTE_TO_REVIEW; **1st anchor C-se** of the bit-tight reproduction chain |
| **S-2** | #332 / 27.0f-β | R7-C regime/context feature widening + Fix A row-set isolation | FALSIFIED_R7C_INSUFFICIENT (H-B6 row 3); REJECT_NON_DISCRIMINATIVE; C-se-r7a-replica drift "within tolerance"; **Fix A row-set isolation behaviour** |
| **S-3** | #338 / 28.0a-β | A1 loss redesign (closed L1/L2/L3 allowlist) | all 3 variants FALSIFIED_OBJECTIVE_INSUFFICIENT; aggregate REJECT_NON_DISCRIMINATIVE; H-C1 4-outcome ladder; C-a1-se-r7a-replica drift "within tolerance" |
| **S-4** | #342 / 28.0b-β | A4 monetisation-aware selection-rule (closed R1/R2/R3/R4 allowlist) | all 4 rules FALSIFIED_RULE_INSUFFICIENT; aggregate REJECT_NON_DISCRIMINATIVE; R-T1 = FALSIFIED_under_A4; H-C2 4-outcome ladder; C-a4-top-q-control drift "within tolerance" |
| **S-5** | #345 / 28.0c-β | A0-narrow tabular topology (closed AR1/AR2/AR3/AR4 allowlist) | all 4 AR variants FALSIFIED_ARCH_INSUFFICIENT; aggregate FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0); H-C3 4-outcome ladder; C-a0-arch-control drift "within tolerance" |
| **S-6** | #351 / 29.0a-β | A2 target redesign (closed T1/T2/T3/T4 allowlist) | all 4 targets FALSIFIED_TARGET_INSUFFICIENT; aggregate FALSIFIED_A2_NARROW (NEVER FALSIFIED_ALL_A2); R-T3 = FALSIFIED_under_T3; H-D1 4-outcome ladder; C-d1-target-control drift "within tolerance"; Option 9c per-target baseline JSON cross-check |

### 2.3 Excluded from V2-expanded (deferred; Class U preserved)

The following β-evals are **NOT** verified by V2-expanded and remain Class U on run-provenance after V2-expanded PASS:

| Deferred | PR | Axis | Reason for deferral |
|---|---|---|---|
| 27.0b-β | #318 | S-C TIME penalty (α grid) | earlier score sub-axis; H-B3 wrong-direction finding; less load-bearing for A0-broad than the 6 major-axis sentinels |
| 27.0c-β | #321 | S-D calibrated EV (β grid) | earlier score sub-axis; same wrong-direction pattern as 27.0b; less load-bearing |
| 27.0e-β | #328 | S-E quantile family trim ({5, 7.5, 10}) | selection sub-axis; H-B5 PARTIAL_SUPPORT row 2; R-T2 trim-alone does NOT recover monetisation; less load-bearing |

These three deferred PRs remain Class U; V2-expanded does NOT cover them. The eventual verification report MUST enumerate them by phase label + PR number and explicitly state that 3/9 historical β-evals remain unverified after V2-expanded PASS.

---

## 3. Verification contract (binding for the eventual implementation PR)

The implementation PR that this memo authorises MUST obey every clause in this section. Each clause is testable; the implementation harness MUST embed assertions that HALT on violation.

### 3.1 Branching and artifact provenance

- Implementation runs on a **new clean branch** off master `9c36adf` (the audit-merged tip) or off the tip at the time of implementation-PR authorisation, whichever is later; under no circumstance off the WIP branch.
- **No reuse** of any artifact under `artifacts/stage29_0b/` from the WIP branch (`9ac8fda`); no reuse of WIP code paths, WIP windowed dataset shards, WIP checkpoints, WIP sanity-probe outputs, or any other WIP-era evidence.
- Every verification cell emits:
  - `contract_hash` — SHA-256 over the normalised cell + comparator + row-set policy + thresholds + quantile family + loss + optimiser + seed contract dict; the exact contract dict schema is fixed in §3.6.
  - `code_hash` — SHA-256 over the verification harness source files at runtime (sorted concatenation; the file list is fixed in §3.7).
  - `data_manifest_hash` — SHA-256 over the per-pair M1 BA + signal source files with sizes + mtimes + content SHAs; pair universe (20 pairs; ordered); split boundaries (datetime ranges); R7-A-clean row-count manifest.
  - `environment_manifest` — Python version, LightGBM version, numpy / pandas / scipy / sklearn versions, deterministic flags, CPU/GPU model, seed; recorded as artifact field.
- Environment-mismatch policy across (V1 foundation step, S-1 ... S-6 sentinel step, report-assembly step): **HALT**.
- Every cell persists machine-readable result summaries (parquet + JSON); the verification report MUST distinguish "generated artifact" from "narrative summary" and MUST cite the artifact path + content SHA for every numeric claim.

### 3.2 Test isolation (test-touched-once)

- All (cell, q) selection occurs on `aligned_val` (for foundation cells) or the sentinel's contemporaneous val split (for sentinel cells) only. **Test split is materialised exactly once per sentinel, after val-selection of (cell\*, q\*) is frozen.**
- No test information enters tuning, gate revision, comparator choice, tolerance revision, or rerun choice.
- A single `verification_log.jsonl` is appended to in **strict event order**; each line is `{ts, event, scope ∈ {foundation, S-1, ..., S-6, report}, payload}`. The implementation MUST emit, in this order per scope:
  - `val_split_loaded`
  - `cell_fit_complete` (one per cell)
  - `val_quantile_scored` (one per (cell, q))
  - `val_selection_frozen` (records the frozen (cell\*, q\*) tuple)
  - `test_split_loaded`
  - `test_metrics_computed` (one per (cell\*, q\*) the sentinel emits)
- The implementation MUST include a unit test that asserts `val_selection_frozen` strictly precedes `test_split_loaded` per scope; HALT on violation.
- A second unit test MUST assert that no `test_*` field appears in any code path executed before `test_split_loaded` for that scope; HALT on violation.

### 3.3 Row-set policy

- Every formal candidate / comparator comparison uses **explicitly identical** fit/eval row-sets unless the row-set is the declared axis (S-2 explicitly declares row-set isolation as its axis; S-6 declares per-target NaN-PnL propagation as its row-set policy).
- Row indices manifest (parquet) persisted per cell; provenance-bound by `data_manifest_hash`.
- For the V1 foundation aligned cells: `aligned_X = R7-A-clean X ∩ windowed_input_valid` (X ∈ {train, val, test}); the windowed_input_valid mask is derived from the windowed dataset construction per PR #355 §A.3. The aligned split row-index manifest is committed.
- For S-2: the Fix A row-set isolation is verified by re-running the #332 cell structure (C-sb-baseline + C-se-r7a-replica + C-se-rcw) and checking that R7-C feature drops affect C-se-rcw row count only (not C-sb-baseline / r7a-replica). A small synthetic unit test may exist as an additional guard but does NOT substitute for the #332 sentinel cell verification.

### 3.4 D-1 PnL integrity

- Bid/ask executable harness identity fixed (verified by harness checksum recorded in `code_hash` + a dedicated `pnl_harness_identity.json` artifact containing the source SHAs of `_compute_realised_barrier_pnl` + `precompute_realised_pnl_per_row`).
- Static-code assertions:
  - `_compute_realised_barrier_pnl` source contains all of `bid_h`, `ask_l`, `ask_h`, `bid_l`
  - `precompute_realised_pnl_per_row` signature does NOT contain `spread_factor` or `mid_to_mid`
- HALT on violation.
- Baseline cell and candidate cell at every comparison use the **same formal PnL path** unless target is the declared axis (S-6 declares target redesign as its axis).
- Mid-to-mid PnL distribution may be computed as DIAGNOSTIC-ONLY (logged) but MUST NOT appear in any formal verdict computation.

### 3.5 Baseline / control identity preservation

- Phase 28 §10 immutable reference `n=34,626 / Sharpe -0.1732 / ann_pnl -204,664.4 / val Sharpe -0.1863` **remains unchanged**.
- Any reproduction attempt writes a **new** verification result file (under `artifacts/tabular_targeted_verification_v2_expanded/`); it does NOT retroactively overwrite or replace any historic `artifacts/stageXX_Xy/eval_report.md` or any Phase 28 §10 numeric.
- Scorer identity is recorded explicitly and never conflated:
  - **S-B raw P(TP)−P(SL) multiclass head** → C-sb-baseline (full + aligned)
  - **S-E tabular LightGBM regressor** (symmetric Huber α=0.9; sample_weight=1) → C-se / C-se-r7a-replica / C-a1-se-r7a-replica / C-a4-top-q-control / C-a0-arch-control / C-d1-target-control / C-d2-arch-control (full + aligned)
- The verification report MUST state, per cell, its scorer identity literally.

### 3.6 Contract-hash dict schema (fixed)

The `contract_hash` SHA-256 input is a JSON-normalised dict with exactly the following keys (deterministic key order):

```
{
  "scope": "foundation" | "S-1" | "S-2" | "S-3" | "S-4" | "S-5" | "S-6",
  "cells": [{"id": ..., "scorer": ..., "row_set_policy": ..., "fit_row_set": ..., "eval_row_set": ..., "quantile_family": [...], "loss": ..., "optimiser": ..., "seed": ...}],
  "comparators": [{"id": ..., "role": "H2" | "PARTIAL_DRIFT" | "drift-chain" | "diagnostic"}],
  "thresholds": {"sharpe_tol": ..., "ann_pnl_tol_pct": ..., "n_trades_tol": ..., "spearman_tol": ...},
  "row_set_policy": "windowed_aligned" | "full" | "fix_a_isolated" | "per_target_nan_propagated",
  "pnl_harness_path_sha": "<sha of _compute_realised_barrier_pnl source>"
}
```

### 3.7 Code-hash file list (fixed)

The `code_hash` SHA-256 input is the sorted concatenation of file content for exactly the following files:

- `scripts/tabular_targeted_verification_v2_expanded.py`
- `scripts/_verification_harness/__init__.py`
- `scripts/_verification_harness/row_set.py`
- `scripts/_verification_harness/sentinel_runner.py`
- `scripts/_verification_harness/reporting.py`

(File paths fixed at memo merge; implementation PR may not add or remove files without a memo amendment.)

---

## 4. V1 shared foundation (verification predicates)

Each predicate emits its own per-cell artifact bundle (parquet + JSON + manifests).

| ID | Predicate | Cell | Tolerance | Artifacts |
|---|---|---|---|---|
| **F-1** | Phase 28 §10 immutable baseline reproduction | C-sb-baseline (S-B raw P(TP)−P(SL) multiclass head; full R7-A-clean train fit; full val + test eval; q=5 fixed) reproduces `(n_trades, Sharpe, ann_pnl, val_Sharpe) = (34,626, -0.1732, -204,664.4, -0.1863)` | n_trades **±100**; Sharpe **±5e-3**; ann_pnl **±0.5%**; val Sharpe **±5e-3** | `f1_c_sb_baseline_full.parquet` + `f1_c_sb_baseline_full.json` + `manifests/f1_*.json` |
| **F-2** | Aligned C-sb-baseline (formal H-D2 H2 comparator per PR #355 §A.4) | C-sb-baseline-aligned (S-B multiclass head; aligned_train fit; aligned_val + aligned_test eval; q=5 fixed) | n_trades **±100** vs the aligned-only re-derivation (no historic reference; this generates new authoritative numbers); Sharpe finite | `f2_c_sb_baseline_aligned.parquet` + JSON + manifests |
| **F-3** | Aligned C-d2-arch-control (formal PARTIAL_DRIFT_TABULAR_REPLICA comparator per PR #355 §A.4) | C-d2-arch-control-aligned (S-E LightGBM regressor; symmetric Huber α=0.9; sample_weight=1; aligned_train fit; aligned_val + aligned_test eval; quantile family {5, 10, 20, 30, 40}) | drift vs C-se anchor (S-1): n_trades **±100**; Sharpe **±5e-3**; ann_pnl **±0.5%** | `f3_c_d2_arch_control_aligned.parquet` + JSON + manifests |
| **F-4** | D-1 bid/ask executable PnL harness identity | static assertion: `_compute_realised_barrier_pnl` source contains `bid_h / ask_l / ask_h / bid_l`; `precompute_realised_pnl_per_row` signature has no `spread_factor` / `mid_to_mid` | exact match; HALT on violation | `pnl_harness_identity.json` with content SHAs |
| **F-5** | Validation-only selection / test-touched-once executable logging | `verification_log.jsonl` ordering: `val_selection_frozen` strictly precedes `test_split_loaded` per scope | exact event order; HALT on violation | `verification_log.jsonl` (committed; ordered append-only) |
| **F-6** | Row-set manifests | `aligned_train_idx.parquet`, `aligned_val_idx.parquet`, `aligned_test_idx.parquet`, `full_train_idx.parquet`, `full_val_idx.parquet`, `full_test_idx.parquet` committed; `data_manifest_hash` cross-references each | manifest hash matches across foundation cells + sentinel cells that depend on it | `row_sets/*.parquet` + `manifests/data_manifest_hash.json` |
| **F-7** | Provenance binding | `contract_hash` / `code_hash` / `data_manifest_hash` / `environment_manifest` per scope step; HALT on mismatch across steps within a single verification run | exact match within run | `manifests/{contract_hash,code_hash,data_manifest_hash,environment_manifest}.json` |

All F-1..F-7 must PASS for the V1 foundation to be considered verified. The verification report names this state explicitly.

---

## 5. Six major-axis sentinel verification contracts

Each sentinel is a separate self-contained verification cell that reproduces the named #PR's verdict claim within the stated tolerance. Each sentinel's input row-set, scorer identity, loss, selection rule, and target are pre-stated below and frozen by the design memo.

### 5.1 S-1 — #325 / 27.0d-β / C-se origin

- **Sentinel role**: clean reproduction of the 1st anchor (C-se) in the bit-tight control chain.
- **Scorer identity**: vanilla S-E LightGBM regressor; symmetric Huber α=0.9; sample_weight=1; pipeline same as `build_pipeline_lightgbm_regression_widened` at PR #325 @ `999859f`.
- **Row-set policy**: full R7-A-clean train fit; full val + test eval; **no Fix A** (Fix A is introduced at #332 = S-2; not yet at S-1).
- **Cells**: C-sb-baseline (S-B multiclass head; comparator) + C-se (S-E regressor; substantive).
- **Verdict claim to reproduce**: C-se val-selected (cell\*, q\*) reproduces `Spearman = +0.4381` (H1m PASS); realised Sharpe wrong-direction; H2 FAIL; aggregate `SPLIT_VERDICT_ROUTE_TO_REVIEW`.
- **Tolerance**: Spearman **±5e-3**; per-cell val Sharpe / test Sharpe / n_trades / ann_pnl within audit-anchor drift tolerance (n_trades **±100** / Sharpe **±5e-3** / ann_pnl **±0.5%**); aggregate verdict label exact match.
- **Comparator identity**: C-sb-baseline reproduction at #325 era (contemporaneous Phase 26 R6-new-A C02 baseline link; Phase 28 §10 was introduced later at PR #335 and is NOT the contemporaneous baseline for #325).
- **Artifacts**: `s1_c_se.parquet` + `s1_c_sb_baseline_at_325.parquet` + per-cell JSON + `s1_verdict_reproduction.json` + manifests.
- **Cross-link to V1 foundation**: F-1 is computed on the post-PR #335 Phase 28 §10 contract; S-1 is computed on the contemporaneous Phase 26 era contract. The two are recorded as separate cells; their numerics may differ and that is expected (different contemporaneous baselines).

### 5.2 S-2 — #332 / 27.0f-β / R7-C + Fix A

- **Sentinel role**: clean reproduction of the 2nd anchor (C-se-r7a-replica) + verification that Fix A row-set isolation behaves as #332 documents.
- **Scorer identity**: same as S-1 (S-E LightGBM regressor).
- **Row-set policy**: **declared axis** — Fix A row-set isolation. C-sb-baseline + C-se-r7a-replica retain full R7-A-clean row-set; C-se-rcw (R7-C-extended cell) loses rows where R7-C features are NaN. Per-cell row-counts MUST be reproduced.
- **Cells**: C-sb-baseline + C-se-r7a-replica + C-se-rcw.
- **Verdict claim to reproduce**: H-B6 row 3 `FALSIFIED_R7C_INSUFFICIENT`; aggregate `REJECT_NON_DISCRIMINATIVE`; C-se-r7a-replica drift vs C-se (S-1) "within tolerance".
- **Tolerance**: drift vs S-1: n_trades **±100** / Sharpe **±5e-3** / ann_pnl **±0.5%**; per-cell row counts match `eval_report.md §3` at #332 within **±10 rows**; aggregate verdict label exact match.
- **Comparator identity**: C-sb-baseline at #332 era + C-se-r7a-replica (which IS the 2nd anchor).
- **Fix A verification (explicit; per user correction)**: the #332 sentinel cell verification is the primary evidence for Fix A behaviour. A small synthetic unit test on the row-set isolation logic exists as an additional guard but is NOT a substitute. The verification report explicitly states "Fix A verified via clean reproduction of #332 row-set + control outputs".
- **Artifacts**: `s2_c_sb_baseline_at_332.parquet` + `s2_c_se_r7a_replica.parquet` + `s2_c_se_rcw.parquet` + `s2_fix_a_row_counts.json` + per-cell JSON + `s2_verdict_reproduction.json` + manifests.

### 5.3 S-3 — #338 / 28.0a-β / A1 loss redesign

- **Sentinel role**: clean reproduction of the A1 loss-axis closed allowlist (L1 / L2 / L3) + the 3rd anchor (C-a1-se-r7a-replica).
- **Scorer identity**: 4 distinct scorer cells:
  - L1: asymmetric Huber α=0.5 LightGBM regressor on R7-A
  - L2: Huber α=0.7 LightGBM regressor on R7-A
  - L3: Huber α=0.9 + regime-axis sample weights LightGBM regressor on R7-A
  - C-a1-se-r7a-replica: vanilla S-E LightGBM regressor with **L3=α=0.9** matched to 27.0d C-se loss (S-1)
- **Row-set policy**: full R7-A-clean train fit (Fix A inherited from S-2; R7-C feature drop applied only to cells that reference R7-C — but A1 cells use R7-A only, so Fix A inheritance is a no-op for the L1/L2/L3 cells themselves; relevant only for the C-a1-se-r7a-replica anchor relative to the C-se chain).
- **Cells**: C-sb-baseline + L1 + L2 + L3 + C-a1-se-r7a-replica.
- **Verdict claim to reproduce**: per-L (L1, L2, L3) verdict `FALSIFIED_OBJECTIVE_INSUFFICIENT`; aggregate `REJECT_NON_DISCRIMINATIVE`; H-C1 4-outcome ladder; C-a1-se-r7a-replica drift vs C-se (S-1) "within tolerance".
- **Tolerance**: per-L val Sharpe / test Sharpe / n_trades / ann_pnl within drift tolerance (n_trades **±100** / Sharpe **±5e-3** / ann_pnl **±0.5%**); aggregate verdict label exact match; per-L verdict label exact match.
- **Comparator identity**: C-sb-baseline at #338 era (Phase 28 §10 immutable; this is the first sentinel that references Phase 28 §10) + C-a1-se-r7a-replica (3rd anchor).
- **Phase 28 §10 cross-check**: S-3 also exercises F-1 (Phase 28 §10 reproduction); the C-sb-baseline cell at #338 era and the F-1 cell MUST agree on `n_trades / Sharpe / ann_pnl / val Sharpe` within F-1's tolerance.
- **Artifacts**: `s3_c_sb_baseline_at_338.parquet` + `s3_l1.parquet` + `s3_l2.parquet` + `s3_l3.parquet` + `s3_c_a1_se_r7a_replica.parquet` + per-cell JSON + `s3_verdict_reproduction.json` + manifests.

### 5.4 S-4 — #342 / 28.0b-β / A4 selection-rule redesign

- **Sentinel role**: clean reproduction of the A4 selection-rule-axis closed allowlist (R1 / R2 / R3 / R4 per PR #340 Clause 2 amendment) + the 4th anchor (C-a4-top-q-control).
- **Scorer identity**: vanilla S-E LightGBM regressor (same as S-1); the axis is at the **selection rule level**, not the scorer level. The 5 cells differ by selection rule:
  - C-sb-baseline (S-B multiclass head; top-q comparator)
  - R1: absolute threshold; per-pair val-median; 50%
  - R2: middle-bulk; global [40, 60] percentile
  - R3: per-pair quantile; top 5%
  - R4: top-K per bar; K=1
  - C-a4-top-q-control: vanilla quantile R3=5% top-q baseline-equivalent control (4th anchor)
- **Row-set policy**: full R7-A-clean train fit; Fix A inherited. The selection rule determines effective per-cell traded-row mask.
- **Verdict claim to reproduce**: per-rule (R1, R2, R3, R4) verdict `FALSIFIED_RULE_INSUFFICIENT`; aggregate `REJECT_NON_DISCRIMINATIVE`; R-T1 = `FALSIFIED_under_A4`; H-C2 4-outcome ladder; C-a4-top-q-control drift vs C-se (S-1) "within tolerance".
- **Tolerance**: per-rule val Sharpe / test Sharpe / n_trades / ann_pnl within drift tolerance; aggregate verdict label exact match; per-rule verdict label exact match; **R-T1 resolution label** = `FALSIFIED_under_A4` exact match.
- **PR #340 scope amendment cross-check**: S-4 must verify that R1 + R4 (non-quantile cell shapes) are actually admitted at #342 — the code path admits R1/R4 per PR #341 / NG#A4-1 closed allowlist; HALT if code path rejects R1/R4 admission.
- **Artifacts**: `s4_c_sb_baseline_at_342.parquet` + `s4_r1.parquet` + `s4_r2.parquet` + `s4_r3.parquet` + `s4_r4.parquet` + `s4_c_a4_top_q_control.parquet` + per-cell JSON + `s4_verdict_reproduction.json` + manifests.

### 5.5 S-5 — #345 / 28.0c-β / A0-narrow tabular topology

- **Sentinel role**: clean reproduction of the A0-narrow tabular topology closed allowlist (AR1 / AR2 / AR3 / AR4) + the 5th anchor (C-a0-arch-control) + the `FALSIFIED_A0_NARROW` (NEVER `FALSIFIED_ALL_A0`) distinction.
- **Scorer identity**: 5 distinct topology cells:
  - AR1: hierarchical two-stage; stage-1 top 50% per-pair val-median admission
  - AR2: pair-conditioned specialists; 20 per-pair regressors
  - AR3: stacked S-B/S-E blend; 0.5/0.5 fixed weights
  - AR4: deterministic regime split; per-pair val-median atr_at_signal_pip
  - C-a0-arch-control: vanilla S-E LightGBM regressor (5th anchor)
  - C-sb-baseline (S-B multiclass head; comparator)
- **Row-set policy**: full R7-A-clean train fit; Fix A inherited.
- **Verdict claim to reproduce**: per-AR (AR1, AR2, AR3, AR4) verdict `FALSIFIED_ARCH_INSUFFICIENT`; aggregate `FALSIFIED_A0_NARROW`; H-C3 4-outcome ladder; C-a0-arch-control drift vs C-se (S-1) "within tolerance".
- **NEVER `FALSIFIED_ALL_A0`** distinction: S-5 verification report MUST explicitly emit the per-AR verdicts AND the aggregate `FALSIFIED_A0_NARROW` label AND state explicitly that A0-broad sequence/NN remains deferred-not-foreclosed per PR #344 §12.2 / §7.2.
- **Tolerance**: per-AR val Sharpe / test Sharpe / n_trades / ann_pnl within drift tolerance; aggregate verdict label exact match; per-AR verdict label exact match.
- **Artifacts**: `s5_c_sb_baseline_at_345.parquet` + `s5_ar1.parquet` + `s5_ar2.parquet` + `s5_ar3.parquet` + `s5_ar4.parquet` + `s5_c_a0_arch_control.parquet` + per-cell JSON + `s5_verdict_reproduction.json` + manifests.

### 5.6 S-6 — #351 / 29.0a-β / A2 target redesign

- **Sentinel role**: clean reproduction of the A2 target-axis closed allowlist (T1 / T2 / T3 / T4) + the 6th anchor (C-d1-target-control) + Option 9c per-target baseline JSON cross-check + R-T3 = `FALSIFIED_under_T3` resolution.
- **Scorer identity**: same S-E LightGBM regressor backbone (vanilla); the **target** is the declared axis:
  - T1: fixed-horizon executable close PnL (the inherited triple-barrier target)
  - T2: time-weighted linear decay
  - T3: multi-horizon {30, 60, 120} (absorbs R-T3)
  - T4: asymmetric K_FAV=2.0 / K_ADV=0.5
  - C-d1-target-control: vanilla S-E LightGBM regressor with target = inherited triple-barrier (6th anchor)
  - C-sb-baseline (S-B multiclass head; comparator)
- **Row-set policy**: **declared axis** — per-target NaN-PnL propagation. When a target produces NaN PnL on a row, that row is excluded from the cell's effective row-set; per-target row counts MUST be reproduced.
- **Verdict claim to reproduce**: per-target (T1, T2, T3, T4) verdict `FALSIFIED_TARGET_INSUFFICIENT`; aggregate `FALSIFIED_A2_NARROW`; R-T3 = `FALSIFIED_under_T3`; H-D1 4-outcome ladder; C-d1-target-control drift vs C-se (S-1) "within tolerance"; per-target baseline numbers match `artifacts/stage29_0a/phase29_section10_per_target_baseline.json` (which IS committed at #351 — the only committed per-target baseline JSON in the spine) within stated tolerance.
- **NEVER `FALSIFIED_ALL_A2`** distinction: per PR #350 framing.
- **Option 9c cross-check**: per-target baseline JSON committed at #351 has 141 lines (verified at audit PR #356). S-6 MUST cross-check the regenerated per-target baselines against this committed JSON within tolerance; HALT on mismatch.
- **Tolerance**: per-target val Sharpe / test Sharpe / n_trades / ann_pnl within drift tolerance; aggregate verdict label exact match; per-target verdict label exact match; per-target baseline JSON cross-check tolerance: n_trades **±100** / Sharpe **±5e-3** / ann_pnl **±0.5%** per (target, val/test) cell.
- **Artifacts**: `s6_c_sb_baseline_at_351.parquet` + `s6_t1.parquet` + `s6_t2.parquet` + `s6_t3.parquet` + `s6_t4.parquet` + `s6_c_d1_target_control.parquet` + `s6_per_target_baseline_cross_check.json` (cross-reference vs committed `phase29_section10_per_target_baseline.json` at PR #351) + per-cell JSON + `s6_verdict_reproduction.json` + manifests.

### 5.7 Per-sentinel scorer identity matrix (binding)

| Sentinel | Substantive cells | Scorer family | Comparator cell | Anchor role |
|---|---|---|---|---|
| S-1 #325 | C-se | S-E LightGBM regressor (symmetric Huber α=0.9; sample_weight=1) | C-sb-baseline (S-B multiclass head; contemporaneous Phase 26 era) | 1st anchor C-se |
| S-2 #332 | C-se-r7a-replica + C-se-rcw | same S-E + R7-C-extended features for rcw | C-sb-baseline (S-B multiclass head; Phase 27 era) | 2nd anchor C-se-r7a-replica |
| S-3 #338 | L1 + L2 + L3 | 3 distinct loss-axis LightGBM regressors on R7-A | C-sb-baseline (S-B multiclass head; Phase 28 §10 era) | 3rd anchor C-a1-se-r7a-replica (L3=α=0.9 matched to S-1) |
| S-4 #342 | R1 + R2 + R3 + R4 | same S-E LightGBM regressor backbone; axis is selection rule | C-sb-baseline (S-B multiclass head; Phase 28 §10 era) | 4th anchor C-a4-top-q-control |
| S-5 #345 | AR1 + AR2 + AR3 + AR4 | 4 distinct tabular-topology configurations on R7-A | C-sb-baseline (S-B multiclass head; Phase 28 §10 era) | 5th anchor C-a0-arch-control |
| S-6 #351 | T1 + T2 + T3 + T4 | same S-E LightGBM regressor backbone; axis is target | C-sb-baseline (S-B multiclass head; Phase 28 §10 era via Option 9c) | 6th anchor C-d1-target-control |

S-B (multiclass head) and S-E (regressor) are **NEVER conflated**; the verification harness instantiates them via distinct factory functions and records the factory name in per-cell JSON.

---

## 6. Deferred PRs (Class U preserved after V2-expanded PASS)

The following three β-evals are NOT verified by V2-expanded and remain Class U on run-provenance after V2-expanded PASS:

| Deferred | PR | Axis | Class U status after V2-expanded PASS |
|---|---|---|---|
| 27.0b-β | **#318** | S-C TIME penalty (α grid; α ∈ {0.0, 0.3, 0.5, 1.0}) | Class U on run-provenance for: α=0.0 baseline-match PASS; per-α monotonicity (val/test Sharpe ↓, Spearman ↑); H-B3 `REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL` emission |
| 27.0c-β | **#321** | S-D calibrated EV (β grid; β ∈ {0.0, 0.3, 0.5, 1.0}) | Class U on run-provenance for: same-wrong-direction-as-27.0b finding; H-B3-supported claim; verdict `REJECT_NON_DISCRIMINATIVE` emission |
| 27.0e-β | **#328** | S-E quantile family trim (q ∈ {5, 7.5, 10}) | Class U on run-provenance for: q\*=10 test Sharpe -0.767 (WORSE than 27.0d -0.483); Spearman +0.4381 preservation; H-B5 `PARTIAL_SUPPORT` row 2; R-T2 trim-alone claim |

The verification report MUST contain a section titled "Class U preserved after V2-expanded PASS" listing these three β-evals by phase label + PR number + axis + Class U status, and explicitly state: "3 of 9 historical β-evals remain unverified after V2-expanded PASS; full reconstruction of the 9-eval picture requires a separate later V3-scope verification PR if and when the user authorises it."

---

## 7. Outcome ladder (binding)

| Outcome | Trigger | Admissible label |
|---|---|---|
| **PASS** | F-1..F-7 all PASS within stated tolerances AND S-1..S-6 all PASS within stated tolerances AND all required provenance artifacts committed | `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES` |
| **FAIL / HALT** | Any of: D-1 violation, test-isolation violation, baseline reproduction mismatch (F-1 fails tolerance), row-set comparator mismatch, scorer identity conflation, environment mismatch, artifact/provenance generation failure, sentinel reproduction outside its pre-stated tolerance | `VERIFICATION_FAILED` / `HALT` |

**Prohibited labels under V2-expanded (verbatim)**:
- `FULL_TABULAR_EVIDENCE_REBUILT` — reserved for V3 only; NOT emittable under V2-expanded.
- `PASS_TABULAR_EVIDENCE_RECONFIRMED` — forbidden everywhere.
- `empirically clean` / `historical execution verified` / `tabular evidence reconfirmed` / `prior verdicts revalidated` — forbidden everywhere.

### 7.1 Report binding under PASS

The verification report under `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES` MUST explicitly state, in this exact structure:

1. "**Shared A0-broad foundation verified**" — names F-1..F-7 as the verified predicates; cites artifact paths.
2. "**Six major-axis sentinel families verified**" — names S-1..S-6 by sentinel ID + PR + axis + verdict label that was reproduced; cites artifact paths.
3. "**Class U preserved**" — names #318 / #321 / #328 with axis and Class U status per §6.
4. "**FULL_TABULAR_EVIDENCE_REBUILT is NOT claimed**".
5. "**Prior verdicts are not retroactively modified or reissued by this verification alone**" — verdicts at PRs #318 / #321 / #325 / #328 / #332 / #338 / #342 / #345 / #351 remain as their respective squash-merged eval_report.md.

### 7.2 Per-cell pre-stated tolerance summary (binding)

| Tolerance | Default value | Where applied |
|---|---|---|
| n_trades_tol | **±100** | drift comparisons; baseline reproduction; per-cell row count cross-checks |
| sharpe_tol | **±5e-3** | drift; baseline; per-target / per-rule / per-AR / per-L cells |
| ann_pnl_tol_pct | **±0.5%** of magnitude | drift; baseline; per-target / per-rule / per-AR / per-L cells |
| spearman_tol | **±5e-3** | S-1 Spearman +0.4381 reproduction |
| row_count_tol | **±10 rows** | S-2 Fix A per-cell row counts vs eval_report.md §3 |
| val_sharpe_tol | **±5e-3** | F-1 Phase 28 §10 val Sharpe reproduction; sentinel val Sharpe reproductions |

Tolerances are α-fixed by the design memo; the implementation PR may not relax them.

---

## 8. A0-broad eligibility under each verification outcome (binding)

| Verification outcome | A0-broad β v2 eligibility |
|---|---|
| `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES` (V2-expanded PASS) | A0-broad β v2 may be **explicitly authorised by separate user decision** against PR #355 amendment spec. The H-D2 H2 + PARTIAL_DRIFT comparators (F-2 / F-3) are run-prov supported. The same-axis prior (S-5 = A0-narrow), target-axis (S-6 = A2), loss-axis (S-3 = A1), selection-rule-axis (S-4 = A4), regime-axis + Fix A (S-2 = R7-C), and C-se origin (S-1) are run-prov supported. 3 deferred PRs (#318 / #321 / #328) remain Class U; user routing decision MUST acknowledge this when authorising A0-broad β v2. |
| `VERIFICATION_FAILED` / `HALT` on any F-* | A0-broad β v2 **NOT eligible** until the affected foundation predicate is resolved by a separate user-authorised PR. |
| `VERIFICATION_FAILED` / `HALT` on any S-* | The foundation (F-*) may still PASS independently and qualify the H-D2 comparator chain; however, the sentinel HALT preserves that sentinel's pre-existing Class U on run-provenance; A0-broad β v2 eligibility depends on whether the failed sentinel is on A0-broad's load-bearing path. The verification report MUST state this per failed sentinel. |

In every case: A0-broad β v2 re-resumption requires **explicit user authorisation**; no auto-route from any verification outcome.

---

## 9. Sequencing (binding)

### 9.1 This PR (doc-only)

- Author this memo at `docs/design/tabular_targeted_verification_v2_expanded_design_memo.md`.
- Lint gates: `python tools/lint/run_custom_checks.py`, `ruff check docs/`, `ruff format --check .`.
- Commit, push, open PR.
- Wait for CI green.
- **Stop**. No code. No rerun. No A0-broad β resumption.

### 9.2 Eventual implementation PR (separate; explicitly user-authorised against this memo)

- New clean branch off master tip at authorisation time.
- File paths fixed by §3.7 (no additions / removals without memo amendment).
- Tolerances fixed by §7.2 (no relaxation without memo amendment).
- All F-* + S-* must execute; PASS / FAIL / HALT per the §7 ladder.
- Verification report emits per §7.1 binding structure.
- Lint, commit, push, open PR, wait for CI green.
- **Stop**. No A0-broad β resumption from implementation PR alone.

### 9.3 Eventual A0-broad β v2 PR (separate; explicitly user-authorised against PR #355 amendment + V2-expanded PASS)

- Per PR #355 §A.7 / §A.9 sequencing (Stage A / Stage B / Full).
- No auto-route from V2-expanded PASS to β v2.

---

## 10. What this PR is NOT

- ❌ Verification code authored.
- ❌ Verification branch for implementation created.
- ❌ Historic re-execution / re-fit / recomputation.
- ❌ A0-broad β resumption.
- ❌ rev2-α amendment PR.
- ❌ Prior verdict modification.
- ❌ Phase 28 §10 immutable baseline modification.
- ❌ Phase 29.0a per-target baseline JSON modification.
- ❌ Reuse of WIP @ `9ac8fda` or EXPLORATORY_ONLY artifacts as evidence.
- ❌ Reissue of any β-eval verdict.
- ❌ Production change.
- ❌ `MEMORY.md` edit inside this PR.
- ❌ Auto-route from any later verification outcome.
- ❌ Use of forbidden labels (`PASS_TABULAR_EVIDENCE_RECONFIRMED` / `FULL_TABULAR_EVIDENCE_REBUILT` / `empirically clean` / `historical execution verified` / `tabular evidence reconfirmed` / `prior verdicts revalidated`).
- ❌ Current-master file:line citation as historical evidence for any β-eval verdict (audit doc PR #356 §2 binding applies).
- ❌ `pr_body_at_merge` assertion as evidence (audit doc PR #356 §2.1 binding applies; `current_pr_body_context_only` is the maximum claim).

---

## 11. Preserved (verbatim from prior PRs; not relaxed by this memo)

- Scope III / Policy C / Option 9c (PR #348)
- D-1 bid/ask executable harness (preserved across spine; verified at F-4)
- R7-A static context surface
- Inherited triple-barrier realised-PnL target
- Top-q on score selection rule
- Validation-only selection
- Test touched once (enforced by F-5 ordering)
- ADOPT_CANDIDATE wall (PR #355 §A.8 + prior)
- H2 PASS = PROMISING_BUT_NEEDS_OOS only (PR #355 §A.8 + prior)
- NG#10 / NG#11 not relaxed
- γ closure PR #279
- X-v2 OOS gating
- Phase 22 frozen-OOS
- Production v9 untouched (Phase 9.12 tip `79ed1e8`)
- **Phase 28 §10 immutable baseline** `n=34,626 / Sharpe -0.1732 / ann_pnl -204,664.4 / val Sharpe -0.1863` (verified via F-1; not modified)
- **Phase 29.0a per-target baselines** (committed at `artifacts/stage29_0a/phase29_section10_per_target_baseline.json` at PR #351; verified via S-6 cross-check; not modified)
- No prior verdict modification (Phase 27 / Phase 28 / Phase 29.0a verdicts preserved verbatim)
- No production change
- No auto-route
- PR #355 Phase 29.0b-α A0-broad design memo AMENDMENT binding (verification PASS does NOT relax any binding in PR #355 §A.1–§A.10)
- PR #356 Phase 27–29 Tabular Evaluation Validity Audit binding (this memo's scope = the audit's Route U-1 / U-2 partial path)
- `FALSIFIED_A0_BROAD_NARROW` distinction (NEVER `FALSIFIED_ALL_A0_BROAD`) — preserved if A0-broad β v2 later runs
- `FALSIFIED_A0_NARROW` / `FALSIFIED_A2_NARROW` distinctions verified via S-5 / S-6

---

## 12. References

### 12.1 Audited spine (in merge order; from PR #356)

- PR #318 — Phase 27.0b-β S-C TIME penalty eval — merge `17be66a` — **DEFERRED in V2-expanded; Class U preserved**
- PR #321 — Phase 27.0c-β S-D calibrated EV eval — merge `0c34ebe` — **DEFERRED in V2-expanded; Class U preserved**
- PR #325 — Phase 27.0d-β S-E regression eval — merge `999859f` — **S-1**
- PR #328 — Phase 27.0e-β S-E quantile-family trim eval — merge `0d9eca0` — **DEFERRED in V2-expanded; Class U preserved**
- PR #332 — Phase 27.0f-β S-E + R7-C regime eval — merge `ad673b4` — **S-2**
- PR #338 — Phase 28.0a-β A1 objective redesign eval — merge `2b6dee1` — **S-3**
- PR #342 — Phase 28.0b-β A4 monetisation-aware selection eval — merge `c4abdee` — **S-4**
- PR #345 — Phase 28.0c-β A0-narrow tabular topology eval — merge `49c08f5` — **S-5**
- PR #351 — Phase 29.0a-β A2 target redesign eval — merge `abe1ed5` — **S-6**

### 12.2 Binding contracts

- PR #279 — γ closure (production behavior contract; preserved)
- Phase 22 frozen-OOS contract (preserved)
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8`
- PR #335 — Phase 28 kickoff (Phase 28 §10 immutable baseline numeric introduction)
- PR #340 — Phase 28.0b A4 scope amendment (R1 + R4 admission; cross-checked at S-4)
- PR #348 — Phase 29 kickoff (Scope III / Policy C / Option 9c framing)
- PR #355 — Phase 29.0b-α A0-broad design memo AMENDMENT (binding for A0-broad β v2 eventual re-implementation)
- PR #356 — Phase 27–29 Tabular Evaluation Validity Audit (this memo's scope = audit's Route U-1 / U-2 partial path)

---

*End of `docs/design/tabular_targeted_verification_v2_expanded_design_memo.md`.*
