# Tabular Evidence Epoch Rebase — Routing Memo (Stage 2 Hard HALT Record + New Provenance-bound Dataset Epoch Routing Decision)

**Type**: doc-only routing memo. **No code. No data fetch. No re-execution. No A0-broad resumption.**
**Branch**: `research/tabular-evidence-epoch-rebase-routing-memo`
**Base**: master @ `a0ec7bb` (post-PR #359 Stage 1 merged)
**Date**: 2026-05-24

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Tabular Evidence Epoch Rebase Routing Memo**. It records the Stage 2 hard-HALT finding (Phase 28 §10 anchor input dataset unavailable locally), formally classifies V2-expanded Stage 2 as `HALTED_INPUT_UNAVAILABLE` and F-1 as `UNEXECUTABLE_INPUT_UNAVAILABLE`, and ranks three routing options for next-step direction — with **Option 2 (new provenance-bound dataset epoch rebase)** as the PRIMARY recommendation absent a verified original backup.*
>
> *This PR does **NOT**:*
>
> - *fetch data;*
> - *regenerate the labels parquet;*
> - *write new implementation code;*
> - *push the existing local Stage 2 implementation branch `research/tabular-targeted-verification-v2-expanded-stage2-preflight` (which contains code commit `0234ed3` retained ONLY as a non-accepted, traceability-only artifact under the obsolete F-1 contract);*
> - *resume Phase 29.0b-β A0-broad (which remains halted);*
> - *modify any prior verdict (Phase 27 / Phase 28 / Phase 29.0a verdicts preserved verbatim; F-1 hard-HALT does NOT invalidate them);*
> - *modify the Phase 28 §10 immutable baseline numeric (`n_trades=34,626 / Sharpe=-0.1732 / ann_pnl=-204,664.4 / val Sharpe=-0.1863`; preserved as archived historic context);*
> - *touch any β code, production code, eval script, or production artifact;*
> - *use forbidden wordings ("historical execution verified" / "historic verdict reproduced" / "prior verdict revalidated" / "historical execution invalidated" / "Phase 28 §10 baseline failed" / "prior tabular verdicts disproven" / "LightGBM has/has not reached its limit" / "PASS_TABULAR_EVIDENCE_RECONFIRMED" / "FULL_TABULAR_EVIDENCE_REBUILT" / "tabular evidence reconfirmed");*
> - *issue any auto-route to a downstream PR.*

A `HALTED_INPUT_UNAVAILABLE` classification means the necessary input dataset for the F-1 strict-tolerance reproduction is not present on the current machine and cannot be silently substituted. It is **NOT** a `BaselineMismatchError`; it is **NOT** evidence that the Phase 28 §10 numerics are wrong; it is a concrete instance of the Class U "run/data provenance unverifiable" status already established by audit PR #356.

---

## 1. Confirmed hard-HALT finding

The Stage 2 preflight HALT'd twice in succession against the same root cause: the historical Phase 28 §10 anchor input dataset is not locally available.

### 1.1 Required inputs for F-1 strict reproduction

Per PR #358 amendment §A.1 (binding):
- n_trades = **34,626 exact (±0)**
- Sharpe = **-0.1732 within ±1e-4**
- ann_pnl = **-204,664.4 within ±0.5 pip**
- val Sharpe = -0.1863 (DIAGNOSTIC-ONLY)

These numerics were computed against the Phase 28 §10 era input chain, which requires:

| Input | Phase 28 §10 era state | Current local state |
|---|---|---|
| `artifacts/stage25_0a/path_quality_dataset.parquet` (labels parquet) | full historical signal universe; 20 pairs; ~3M rows; ~1095-day span | **3 pairs only** (EUR_USD / GBP_JPY / USD_JPY); **1,306 rows**; **1-day span** (2026-04-29 to 2026-04-30); mtime 2026-05-24 03:48 (recent development slice) |
| `data/candles_<PAIR>_M1_1095d_BA.jsonl` for all 20 pairs | required for `_build_pair_runtime(pair, days=1095)` | **0/20 pairs available** |

### 1.2 Available BA inventory (local)

| Depth | Pair count |
|---|---|
| 365d_BA | 20 / 20 ✅ |
| 730d_BA | 20 / 20 ✅ |
| **1095d_BA** | **0 / 20** ❌ |
| **1825d_BA** | **0 / 20** ❌ |

### 1.3 Git history confirms unversioned

`git log --all -- artifacts/stage25_0a/path_quality_dataset.parquet` returns **no commits**. The labels parquet was never committed to git history (gitignored under `artifacts/`). No byte-identity-verifiable in-repo restoration source exists for the Phase 28 §10 era dataset.

### 1.4 Hard-HALT scope

Even acquiring all 20 pairs × 1095 days of M1 BA data via OANDA fetch would NOT restore the Phase 28 §10 era dataset, because:

1. New fetched data ends at today (2026-05-24), not at the Phase 28 §10 era closing date. The historical 1095-day window cannot be reconstructed without point-in-time historical BA data.
2. The labels parquet would still need regeneration through `stage25_0a_*` label-generation pipeline (signal generation + triple-barrier labelling + frozen-OOS contract), producing a dataset under a DIFFERENT time window than the Phase 28 §10 era.
3. The regenerated dataset's n_trades / Sharpe / ann_pnl would NOT match `34,626 / -0.1732 / -204,664.4` because those numerics are bound to a specific (now lost) signal universe.

---

## 2. Formal status of the blocked verification (binding)

| Item | Status |
|---|---|
| **V2-expanded Stage 2** | **`HALTED_INPUT_UNAVAILABLE`** |
| **F-1 historic anchor preflight** | **`UNEXECUTABLE_INPUT_UNAVAILABLE`** |
| F-2 aligned C-sb-baseline preflight | not executed |
| F-3 aligned C-d2-arch-control preflight | not executed |
| F-4 D-1 harness identity (Stage 2 partial output) | non-authoritative; not retained as verification evidence |
| F-5 / F-6 / F-7 (Stage 2 partial outputs) | non-authoritative; not retained as verification evidence |
| **Stage 3 formal evidence run** | **not eligible to begin** |
| **A0-broad β** | **remains halted** |

### 2.1 Prohibited interpretations (binding)

The Stage 2 HALT does **NOT** imply any of the following. These wordings MUST NOT appear in this memo, future memos, or any subsequent communication arising from this HALT:

- ❌ "Phase 28 §10 baseline failed"
- ❌ "prior tabular verdicts were disproven"
- ❌ "historical execution was invalidated"
- ❌ "LightGBM has reached its limit"
- ❌ "LightGBM has not reached its limit"
- ❌ "historical execution verified"
- ❌ "historic verdict reproduced"
- ❌ "prior verdict revalidated"
- ❌ "historical execution invalidated"
- ❌ "PASS_TABULAR_EVIDENCE_RECONFIRMED"
- ❌ "FULL_TABULAR_EVIDENCE_REBUILT"
- ❌ "tabular evidence reconfirmed"

### 2.2 Permitted interpretation (binding)

The Stage 2 HALT means **exactly** that the input dataset required for F-1 strict reproduction is not locally available. F-1 is unexecutable on the current machine without supplying the original inputs or rebasing onto a new dataset epoch. No claim about model-class limits, axis exhaustion, or historic verdict validity is made.

---

## 3. Historic evidence status (binding)

PR #356 audit outcome **`TARGETED_VERIFICATION_REQUIRED`** (master `9c36adf`) remains valid and unchanged by this routing memo.

| Audit-doc finding | Status after this HALT |
|---|---|
| 9-eval picture across PRs #318 / #321 / #325 / #328 / #332 / #338 / #342 / #345 / #351 | preserved verbatim |
| Static-code inspection: 0 Class A blockers proven | unchanged |
| Run-provenance: 64 Class U findings (sweep_results / aggregate / val_selected / sanity_probe gitignored at every merge SHA) | **strengthened** by the newly confirmed missing-input condition (the labels parquet itself, not just per-cell sweep_results, is also absent in its historic form) |
| Aggregate outcome `TARGETED_VERIFICATION_REQUIRED` | unchanged |
| Per-PR outcomes `PR_TARGETED_VERIFICATION_REQUIRED` for all 9 spine PRs | unchanged |
| Citation-drift finding (Class B at routing-memo level for #311 / #319 / #327) | unchanged |

This memo does NOT modify any prior β-eval verdict. Phase 27 / Phase 28 / Phase 29.0a verdicts remain as their respective squash-merged `eval_report.md` files.

---

## 4. Routing options

### 4.1 Option 1 — Restore original historic input dataset

**Admissible only if an off-machine backup of the Phase 28 §10 era input chain is supplied.**

Restoration requirements:
- Off-machine backup of `artifacts/stage25_0a/path_quality_dataset.parquet` (the labels parquet) from Phase 28 §10 era
- Corresponding `data/candles_<PAIR>_M1_1095d_BA.jsonl` files for all 20 pairs at the historical span
- Schema validation: filename contract, OANDA bid/ask BA schema (`time` + `bid_o/h/l/c` + `ask_o/h/l/c`), per-pair row counts within historical expectations
- **Byte-identity-verifiable** restoration: SHA-256 of every restored file recorded; if these SHAs cannot be cross-referenced against an immutable historical record, the dataset is classified `CURRENT_MANIFEST_ACQUIRED_INPUT_ONLY` rather than `ORIGINAL_BYTES_IDENTITY_PROVEN`

If a verified backup exists:
- This route could preserve the existing F-1 strict historic-anchor reproduction contract.
- Stage 2 preflight could be retried from the existing local code commit `0234ed3` (subject to user authorisation; not auto-routed).
- The PR #358 amendment binding tolerance (`n_trades ±0 / Sharpe ±1e-4 / ann_pnl ±0.5 pip`) would apply unchanged.

**Status**: available **only if** the user supplies an actual backup source. Until then, this option is not actionable. No fetch attempt is authorised here.

### 4.2 Option 2 — New provenance-bound dataset epoch rebase

**PRIMARY recommendation absent a verified original backup.**

A new dataset epoch is created for all future tabular and A0-broad evaluation work:

- All future tabular baseline / control / candidate cells are trained/evaluated on a single newly-generated and durably-versioned dataset contract.
- The old Phase 28 §10 numerics (`34,626 / -0.1732 / -204,664.4`) become **archived historic context only**; they are NOT an executable FAIL-FAST gate for new-epoch runs.
- The new-epoch dataset is the **single source of truth** for downstream tabular and A0-broad verification; old artifacts are not concatenated with new-epoch artifacts.
- No statement that the new epoch reproduces or invalidates the old results. The old and new epochs are explicitly distinct evaluation universes.

**Why this is the primary recommendation**:

- It restores forward-execution capability (Stage 2 / Stage 3 / A0-broad β v2 can all proceed once a new-epoch design lands).
- It is honest about the data-provenance gap (no pretense that the new epoch reconstructs the old one).
- It durably commits to the discipline that future baselines must have retained inputs + manifests sufficient for independent recomputation (the gap that PR #356 audit exposed will not recur for the new epoch).
- It does not modify any prior verdict.

**Cost**: significant. A new dataset epoch requires the design PR enumerated in §5 below, plus authorised data acquisition, plus regenerated baselines / controls under the new epoch.

### 4.3 Option 3 — Indefinite halt

Preserve current Class U status. Do not resume A0-broad or rebuild evidence until original input data becomes available.

- All current verdicts remain in place.
- No new dataset is generated.
- No verification baseline change.
- A0-broad β v2 indefinitely deferred.

**Status**: conservative; admissible but does not advance research. Recommended only if Option 1 is anticipated to become available soon.

### 4.4 Explicitly NOT recommended

The following routes are rejected per user binding:

- ❌ **Substituting `days=730`** into the existing Phase 28 §10 reproduction contract — would silently change the historic depth setting and produce numerics under a different signal universe; the resulting reproduction attempt would not test the Phase 28 §10 anchor.
- ❌ **Fetching new data and pretending it is the historic dataset** — current OANDA fetch produces a rolling window ending today, not the historical Phase 28 §10 era window. Any "reproduction" would silently rebase the evaluation universe.
- ❌ **Resuming A0-broad β v2 against the existing Class-U ceiling while retaining the impossible Phase 28 §10 historic FAIL-FAST gate** — the FAIL-FAST gate is impossible to satisfy under current data availability; retaining it as a binding β v2 gate would render A0-broad β v2 unexecutable from the start.

---

## 5. New dataset epoch design requirements (Option 2 — pre-stated; binding for a later design PR)

This routing memo does **not** specify the new-epoch design. A separate later design PR (not this PR) will define the new-epoch contract. That later PR MUST address every item below; this list is binding minimum scope:

| # | Item |
|---|---|
| 1 | Data source identification + credentials/access feasibility audit (OANDA API access; alternate sources if any; required credential bootstrap) |
| 2 | Pair universe — explicit closed allowlist for the new epoch |
| 3 | Precise date coverage with a frozen cutoff (the new epoch is point-in-time anchored; no rolling-window ambiguity) |
| 4 | Raw BA candle schema — exact `time` parsing + `bid_o/h/l/c` + `ask_o/h/l/c` columns + dtype contract |
| 5 | Signal-generation contract — how signal_ts is determined; what triggers an entry |
| 6 | Target/label-generation contract — triple-barrier K_FAV / K_ADV / H_M1 / direction logic; whether to inherit from Phase 25 lineage verbatim or restate |
| 7 | Train / val / test / frozen-OOS boundary contract — explicit datetime boundaries; same logic as `split_70_15_15` or alternative |
| 8 | D-1 executable PnL contract — bid/ask only; no mid-price; per-pair pip table |
| 9 | Row-set manifest policy — every cell must persist row-index parquets + SHA-256 of indices |
| 10 | Artifact retention policy — every artifact required for independent later recomputation MUST be durably retained (NOT gitignored). Specifically: sweep_results / aggregate / val_selected / sanity_probe equivalents must be either committed or have content SHAs committed to a manifest |
| 11 | Raw input + immutable-source manifest hashing — SHA-256 of every M1 BA jsonl + labels parquet recorded in a committed manifest at epoch creation |
| 12 | Labels parquet commitment/versioning strategy — either commit the parquet directly to git (size permitting) OR commit a content-SHA manifest + retain off-machine immutable copy with verifiable identity |
| 13 | Baseline / control regeneration policy — under the new epoch, what is the S-B baseline cell's value? what is the S-E control? are they new numerics, archived for the new epoch? |
| 14 | A0-broad eligibility rule under the new epoch — does A0-broad β v2 run against the new-epoch S-B baseline + S-E control? what are the new-epoch H-D2 ladder comparator values? |

### 5.1 Mandatory binding principle (the principle that caused this HALT)

**No future baseline numeric may become a binding immutable gate unless the exact input dataset, split manifest, result artifacts, and provenance necessary to reproduce that numeric are durably retained at the moment of gate-establishment.**

This principle, if enforced for Phase 28 §10 at the time of its establishment (PR #335), would have prevented the current `UNEXECUTABLE_INPUT_UNAVAILABLE` state. It is the binding rule for the new epoch.

---

## 6. Current branch and implementation disposition

### 6.1 Stage 2 local implementation branch

Branch: `research/tabular-targeted-verification-v2-expanded-stage2-preflight`
Code commit: `0234ed3` (local; not pushed; not on remote)

**Disposition**:

- ✅ May be retained locally for traceability.
- ❌ **NOT** accepted formal implementation.
- ❌ **NOT** to be pushed to `origin`.
- ❌ **NOT** to be merged into master.
- ❌ Any preflight artifacts generated from this branch MUST NOT be cited as Stage 2 evidence under the obsolete F-1 contract.
- ⚠️ Reusable infrastructure concepts (test-access guard primitive, event-log ordering, factory provenance binding, dataset_status classification, F-1 anchor event sequence design) MAY be selectively carried forward into the new-epoch implementation **only after** the new-epoch design PR (§5) is approved.

### 6.2 V2-expanded Stage 1 (PR #359)

Stage 1 infrastructure (PR #359 → master `a0ec7bb`) was infrastructure-only by binding and is not affected by this HALT.

- Stage 1 contract snapshots S-1..S-6 remain committed at master.
- Stage 1 harness modules (`tolerances.py` / `event_log.py` / `pnl_identity.py` / `row_set.py` / `contract_snapshots.py` / `forbidden_inputs.py` / `manifests.py` / `__init__.py`) remain committed at master.
- Stage 1 81 unit tests remain passing.
- Stage 1 STAGE_2_PREFLIGHT / STAGE_3_FORMAL stage-label discipline remains correct as a design principle; only the executable Stage 2 path is now HALTED.

### 6.3 V2-expanded contract memos (PR #357 + PR #358)

Both remain in force as design documents. The amended F-1 strict tolerance contract (PR #358 §A.1) remains the binding contract that any future restoration attempt (Option 1) would need to satisfy. Option 2 supersedes this contract for future new-epoch evaluations; the new-epoch design PR (§5) will define the new-epoch comparator contract.

### 6.4 A0-broad β WIP

WIP @ `9ac8fda` remains INVALID_FOR_FORMAL_VERDICT and EXPLORATORY_ONLY. This memo does not change that status.

---

## 7. Constraints (binding for this PR)

- ❌ Doc-only PR.
- ❌ No data fetch.
- ❌ No labels parquet regeneration.
- ❌ No implementation code authored.
- ❌ No push of the Stage 2 implementation branch.
- ❌ No A0-broad β resumption.
- ❌ No prior verdict modification (Phase 27 / Phase 28 / Phase 29.0a verdicts preserved verbatim).
- ❌ No production change.
- ❌ No `MEMORY.md` edit inside this PR.
- ❌ No auto-route to the new-epoch design PR (the routing recommendation is read-only; user decides).
- ❌ No forbidden wordings.

---

## 8. References

### 8.1 Related PRs

- PR #355 — Phase 29.0b-α A0-broad design memo AMENDMENT (binding for future A0-broad β v2 against the new epoch)
- PR #356 — Phase 27–29 Tabular Evaluation Validity Audit (aggregate outcome `TARGETED_VERIFICATION_REQUIRED`; preserved by this memo)
- PR #357 — Tabular Targeted Verification V2-expanded design memo (binding contract for Option 1; superseded for new epoch by §5 design PR if Option 2 selected)
- PR #358 — V2-expanded amendment (F-1 strict tolerance binding; preserved as the Option 1 contract)
- PR #359 — V2-expanded Stage 1 infrastructure (master `a0ec7bb`; not affected by this HALT)

### 8.2 HALT origin records

- Local Stage 2 branch: `research/tabular-targeted-verification-v2-expanded-stage2-preflight` (not pushed)
- Local code commit: `0234ed3` (not pushed; retained for traceability only)
- Two consecutive Stage 2 preflight HALT runs (logged in conversation context):
  - HALT 1: `AttributeError: module 'stage27_0d_s_e_regression_eval' has no attribute 'load_raw_labels_for_27_0d'` (implementation defect; corrected at `0234ed3`)
  - HALT 2: `FileNotFoundError: data/candles_EUR_USD_M1_1095d_BA.jsonl` (data-availability gap; root cause)

### 8.3 Audit context preserved

PR #356 audit findings preserved verbatim. The newly-confirmed missing-input condition strengthens the Class U explanation by demonstrating that the missing run-provenance was structural (gitignored at every merge SHA, in some cases unversioned entirely) rather than incidental. The new-epoch design (§5) will enforce a binding retention principle (§5.1) that prevents this from recurring.

---

*End of `docs/design/tabular_evidence_epoch_rebase_routing_memo.md`.*
