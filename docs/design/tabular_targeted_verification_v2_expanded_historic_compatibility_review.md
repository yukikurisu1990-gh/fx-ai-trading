# Tabular Targeted Verification V2-expanded — Historic Compatibility Review (S-1..S-6)

**Type**: read-only static compatibility review at each sentinel's squash-merge snapshot. **Doc-only**.
**Branch**: `research/tabular-targeted-verification-v2-expanded-amendment`
**Base**: master @ `608e21d` (post-PR #357 V2-expanded design memo merged)
**Date**: 2026-05-24

This document records the read-only static review of each sentinel's merge-SHA eval script to determine:

1. **Historic test-touched-once compatibility** — does the historic val-selection code path read any test field before val-selection of (cell\*, q\*) is frozen?
2. **Historic data identity availability** — is there a merge-time immutable data manifest / content SHA recoverable from committed evidence at the merge SHA?

The review is **read-only**; no rerun, no recomputation, no historic verdict modification. All evidence pointers are merge-SHA pinned per audit doc PR #356 §2.

---

## 1. Methodology

For each sentinel S-1..S-6, the review reads at the sentinel's squash-merge SHA (via `git show <sha>:<path>`):

- The val-selection sort key function (typically named `_q_sort_key`).
- Any data manifest / content-SHA recording code paths (greps for `data_manifest`, `content_sha`, `source_sha`, `sha256.*data`, `hashlib.*data`, `m1_ba.*sha`, `file_sha`, `md5.*data`, `sha256.*\.parquet`).

The review does NOT execute, refit, or recompute anything.

---

## 2. Historic test-touched-once compatibility per sentinel

### 2.1 Sort-key inspection (uniform pattern across all 6 sentinels)

At every sentinel's merge SHA, the val-selection sort key function `_q_sort_key` has the following structure (verbatim citation; line-number references):

```python
def _q_sort_key(r: dict) -> tuple:
    v = r["val"]
    s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
    return (s, v["annual_pnl"], v["n_trades"], -r["q_percent"])

best_q_record = max(quantile_results, key=_q_sort_key)
```

The sort-key tuple reads from `r["val"]` only (`sharpe`, `annual_pnl`, `n_trades`) plus `r["q_percent"]`. **No `r["test"]` field is accessed.** The test field is read only after `best_q_record` is selected (i.e., after val-selection freezes).

### 2.2 Per-sentinel evidence pointers

| Sentinel | PR | Merge SHA | Script | `_q_sort_key` location | test-touched-once verdict |
|---|---|---|---|---|---|
| S-1 | #325 | `999859f` | `scripts/stage27_0d_s_e_regression_eval.py` | L980–984 | **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE** |
| S-2 | #332 | `ad673b4` | `scripts/stage27_0f_s_e_r7_c_regime_eval.py` | L1461–1465 | **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE** |
| S-3 | #338 | `2b6dee1` | `scripts/stage28_0a_a1_objective_redesign_eval.py` | L1113–1117 | **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE** |
| S-4 | #342 | `c4abdee` | `scripts/stage28_0b_a4_monetisation_aware_selection_eval.py` | L1227–1231 | **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE** |
| S-5 | #345 | `49c08f5` | `scripts/stage28_0c_a0_architecture_topology_eval.py` | L1351–1355 | **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE** |
| S-6 | #351 | `abe1ed5` | `scripts/stage29_0a_a2_target_redesign_eval.py` | L1420–1424 | **HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE** |

### 2.3 Aggregate test-touched-once verdict

**All 6 sentinels are HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE.** No sentinel's historic val-selection sort key reads any test field. V2-expanded implementation may proceed past the test-touched-once gate for all six.

No `INCOMPATIBILITY_FOUND` finding. No sentinel triggers HALT under the user-bound rule "incompatibility found in any sentinel → stop and require scope amendment".

No `UNVERIFIED / INSUFFICIENT_EVIDENCE` finding. Every sentinel's sort key was inspected at its merge SHA and produced a deterministic verdict.

---

## 3. Historic data identity availability per sentinel

### 3.1 Inspection method

At each merge SHA, the eval script source was grepped for any of the following patterns that would indicate a recorded data manifest / content SHA:

- `data_manifest`
- `content_sha`
- `source_sha`
- `sha256.*data`
- `hashlib.*data`
- `m1_ba.*sha`
- `file_sha`
- `md5.*data`
- `sha256.*\.parquet`

### 3.2 Per-sentinel result

| Sentinel | PR | Merge SHA | Pattern hits | Result |
|---|---|---|---|---|
| S-1 | #325 | `999859f` | 0 | **HISTORIC_DATA_IDENTITY_NOT_PROVABLE** |
| S-2 | #332 | `ad673b4` | 0 | **HISTORIC_DATA_IDENTITY_NOT_PROVABLE** |
| S-3 | #338 | `2b6dee1` | 0 | **HISTORIC_DATA_IDENTITY_NOT_PROVABLE** |
| S-4 | #342 | `c4abdee` | 0 | **HISTORIC_DATA_IDENTITY_NOT_PROVABLE** |
| S-5 | #345 | `49c08f5` | 0 | **HISTORIC_DATA_IDENTITY_NOT_PROVABLE** |
| S-6 | #351 | `abe1ed5` | 0 | **HISTORIC_DATA_IDENTITY_NOT_PROVABLE** |

None of the six historic eval scripts at their respective merge SHAs records any content-SHA of the underlying M1 BA / signal data files. The data is loaded at runtime from `data/m1_ba/` and `data/signals/` (current paths) without any per-file content-SHA emitted into a committed artifact.

### 3.3 Aggregate data identity verdict

**All 6 sentinels fall under Case B** per the user-bound classification:

- contract semantics: pinnable from merge-SHA (each historic eval script is a deterministic procedure when given the same data + same code)
- data bytes identity: **NOT** provable from merge-time committed evidence

### 3.4 Reporting wording binding (per user instruction §3)

For all six sentinels under V2-expanded, the verification report MUST express each per-sentinel result as:

> **`CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY`** — clean re-execution under the current provenance-bound dataset.

The verification report MUST NOT express any per-sentinel result as:

- `HISTORIC_DATA_IDENTITY_PROVEN`
- `historical execution verified`
- `historic verdict reproduced`
- `prior verdict revalidated`

Since **all six sentinels** are Case B, the overall V2-expanded outcome cannot be called "historical negative verdict reproduction". The PASS label `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES` remains the only admissible label, but its narrative is bound to the wording "clean re-execution under current provenance-bound dataset" for every sentinel.

---

## 4. Implication for V2-expanded implementation

### 4.1 Test-touched-once gate

All six sentinels PASS the test-touched-once compatibility gate. The implementation PR may execute foundation + 6 sentinels under the modern test-touched-once contract without conflicting with any historic semantics.

### 4.2 Data identity gate

No sentinel has a recoverable merge-time immutable data manifest. The implementation PR runs all six sentinels under `CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY` semantics. The per-run `data_manifest_hash` (PR #357 §3.6 / amendment §3.6) captures the **current** data bytes content at the verification run time; this hash is committed and provenance-binds the run going forward, but it does NOT establish identity with the historic merge-time runs.

### 4.3 No HALT triggered by this review

The user-bound rules:

| Trigger | Found? |
|---|---|
| incompatibility found in any sentinel's historic test-touched-once compliance | **No** (all 6 COMPATIBLE) |
| unverified test-touched-once compliance in any sentinel | **No** (all 6 inspected deterministically) |
| historic data identity proven in any sentinel | **No** (all 6 NOT_PROVABLE) |

The first two are not triggered → implementation may proceed (subject to the data identity wording binding above). The third being uniformly `No` is a finding to be reflected in the verification report wording but does not block implementation per the user instruction (Case B sentinels remain in V2-expanded scope; only the wording changes).

### 4.4 No prior verdict modification

This review modifies **no** historic verdict. Phase 27 / Phase 28 / Phase 29.0a verdicts at PRs #325 / #332 / #338 / #342 / #345 / #351 remain as their respective squash-merged eval_report.md.

---

## 5. Evidence pointers (audit-style; merge-SHA pinned)

- PR #325 @ `999859f` :: `scripts/stage27_0d_s_e_regression_eval.py:980-984` (S-1 `_q_sort_key`)
- PR #332 @ `ad673b4` :: `scripts/stage27_0f_s_e_r7_c_regime_eval.py:1461-1465` (S-2 `_q_sort_key`)
- PR #338 @ `2b6dee1` :: `scripts/stage28_0a_a1_objective_redesign_eval.py:1113-1117` (S-3 `_q_sort_key`)
- PR #342 @ `c4abdee` :: `scripts/stage28_0b_a4_monetisation_aware_selection_eval.py:1227-1231` (S-4 `_q_sort_key`)
- PR #345 @ `49c08f5` :: `scripts/stage28_0c_a0_architecture_topology_eval.py:1351-1355` (S-5 `_q_sort_key`)
- PR #351 @ `abe1ed5` :: `scripts/stage29_0a_a2_target_redesign_eval.py:1420-1424` (S-6 `_q_sort_key`)
- All 6 scripts: grep at merge SHA for `data_manifest|content_sha|source_sha|sha256.*data|hashlib.*data|m1_ba.*sha|file_sha|md5.*data|sha256.*\.parquet` returns 0 hits.

---

*End of `docs/design/tabular_targeted_verification_v2_expanded_historic_compatibility_review.md`.*
