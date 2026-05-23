# Phase 27–29 Tabular Evaluation Validity Audit — Read-only Static + Run-provenance Audit Across the Full 9-eval Tabular Negative-evidence Picture

**Type**: Read-only formal-validity audit. **Doc-only**.
**Branch**: `research/phase27-29-tabular-audit-pre-authoring`
**Base**: master @ `0d06ad2` (post-PR #355 amendment merged)
**Audit-doc version**: rev2 (per user instruction set)
**Date**: 2026-05-23

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 27–29 Tabular Evaluation Validity Audit**, read-only at each audited PR's own squash-merge snapshot. The audit produces **findings**, not historical verdict modifications. It enumerates the formal-β tabular negative-evidence spine (9 β-eval PRs across Phase 27–29), classifies findings per (PR × dimension) cell with separate static-code and run-provenance columns, and emits one aggregate outcome from the revised 3-row ladder: `STATIC_BLOCKER_FOUND` / `TARGETED_VERIFICATION_REQUIRED` / `STATIC_REVIEW_NO_BLOCKER_FOUND`.*
>
> *This PR does **NOT**:*
>
> - *re-run, re-fit, or recompute any historical metric;*
> - *modify any prior verdict (Phase 27 / Phase 28 / Phase 29.0a verdicts are quoted verbatim from each PR's own merge-time snapshot; verdicts are NOT retroactively edited);*
> - *use current master file:line citations as evidence for historical verdicts (current master `0d06ad2` is the docs-add base only);*
> - *issue standalone historical verdict modifications for supporting-dependency documents;*
> - *modify any β code, eval script, eval_report, test, or production artifact;*
> - *resume Phase 29.0b-β A0-broad (which remains halted per PR #355 + user instruction);*
> - *open the Phase 29.0b-α rev2 amendment PR (deferred per user instruction);*
> - *use the phrase `PASS_TABULAR_EVIDENCE_RECONFIRMED` anywhere — read-only audit cannot make that claim;*
> - *issue any auto-route.*

A `STATIC_REVIEW_NO_BLOCKER_FOUND` aggregate outcome means "no static blocker found in the inspected committed evidence at each PR's merge-time snapshot"; it is **NOT** an empirical reconfirmation or evidence reproduction. Any A0-broad re-resumption requires a separate user decision.

---

## 1. Mission

Determine, **read-only** at each PR's squash-merge snapshot, whether the negative verdicts emitted by the Phase 27–29 tabular β-eval spine are formal evidence in the strict sense — i.e., whether each verdict's H-ladder row binding is supported by an evaluation harness that is row-set-comparable, test-isolated, D-1-pure, axis-pure, and verdict-code-consistent at that snapshot.

Establish whether A0-broad re-resumption can rely on a trustworthy tabular ceiling, or whether predicates of that ceiling need re-establishing first.

---

## 2. Methodology

### 2.1 Evidence snapshot policy (binding)

Per audited PR, every evidence pointer in this audit doc and the findings JSON uses the form:

```
PR #<n> @ <merge_commit_sha[:12]> :: <path-at-that-commit>:<L_start>-<L_end>
PR #<n> @ <merge_commit_sha[:12]> :: artifact <relpath> presence=<committed|gitignored|absent>
PR #<n> @ <merge_commit_sha[:12]> :: PR body — current_pr_body_context_only (historical_body_provenance_unverified)
```

- `file:line` pointers against current master `0d06ad2` are **NOT** used as evidence for historical verdicts.
- `pr_body_at_merge` is **NOT** asserted; PR-body fields are recorded as `current_pr_body_context_only` because the merge-time revision of the PR description cannot be recovered with certainty from `gh` alone (PR bodies can be edited post-merge without leaving an audit trail accessible via `gh api`).
- CI green / merge metadata are **not** evidence of formal validity; they confirm only that committed tests passed and the branch was squash-merged.

### 2.2 Read mechanism

The audit reads historic file content via `git show <sha>:<path>`. Forward diffs (merge SHA → current master) are computed only to attribute forward-hardening changes; current master content is never substituted for historical evidence.

### 2.3 Static-code vs run-provenance split (binding for every (PR × dimension) cell)

Each cell records **two parallel evidence fields**:

| Field | Question |
|---|---|
| **A. Static contract inspection** | Does the committed code path at `merge_commit_sha` honour the contract? E.g., does the eval script gate val-selection before reading test metrics? Does it forbid forbidden row-set mixing? Do declared constants match code constants? |
| **B. Historical run provenance** | Is there committed evidence (artifact / log / commit history / report cross-reference) that the actual merge-time run executed the intended path? E.g., logged val-selection-before-test sequence, committed sweep_results.parquet, FAIL-FAST result verifiable from committed JSON, eval_report numerics cross-checkable against committed machine-readable artifact |

Per-cell classification logic (per rev2 instruction set):

| Static A | Run-provenance B | Cell classification |
|---|---|---|
| clean | reproducible from committed evidence | NONE (or C if hardening absent) |
| clean | absent or non-reproducible from committed evidence | **U** (static OK; cannot prove run followed it) |
| clean | self-inconsistent with eval_report numerics | **A** (Tier 1 if verdict-affecting) |
| contract violation (verdict-affecting) | irrelevant | **A** |
| contract violation (non-verdict-affecting) | irrelevant | **B** (with explicit narrative) |
| ambiguous static | absent or weak provenance | **U** |

### 2.4 Classification rubric

Five mutually exclusive classes per cell:

- **A** — proven formal validity blocker (Tier 1 universal, or Tier 2 contemporaneous-contract violation under the PR's own merged design memo)
- **B** — scientific-policy choice taken under the stated contract; defensible; non-blocking
- **C** — engineering hardening opportunity that does NOT affect the verdict's formal validity under the contract that PR was merged under
- **U** — UNVERIFIED / INSUFFICIENT_EVIDENCE — verdict-dependent claim cannot be confirmed or refuted from committed evidence at the merge-time snapshot; targeted later verification required
- **NONE** — no finding in inspected evidence

U is **never** collapsed into NONE or B. A static-clean code path with absent run-provenance is **U**, not NONE.

### 2.5 Three-tier rubric (no retroactive standards)

**Tier 1 — Universal formal validity blockers** (always Class A if proven):
- Unequal uncontrolled comparator row-sets in a formal comparison
- Test information entering selection / verdict tuning / threshold revision
- Different executable-PnL harness across compared formal cells
- Mid-price in a bid/ask-bound formal PnL path
- Memo-to-code threshold mismatch
- Suppressed binding HALT
- Hidden simultaneous axis change altering verdict interpretation
- Retroactive modification of an immutable baseline numeric

**Tier 2 — Contemporaneous contract checks** (Class A only if the PR's own merged design memo required it and it was violated):
- FAIL-FAST executed before verdict generation (if memo binds this)
- Drift tolerance honoured (if memo specifies)
- Control identity correctly named (if memo specifies)
- Verdict naming consistency (`FALSIFIED_NARROW` vs `FALSIFIED_ALL`) per the PR's own memo

**Tier 3 — Forward hardening** (NOT auto-Class-A or auto-Class-C; contextual):
- `contract_hash` / `code_hash` / `data_manifest_hash` absence
- `environment_manifest` absence
- Stage artifact schema v2 absence

Tier-3 absence that blocks a Tier-1 / Tier-2 claim → **Class U**, not A or C automatically.

### 2.6 Outcome ladder (binding rewrite per rev2)

Per-PR outcomes:

| Per-PR outcome | Trigger |
|---|---|
| **PR_STATIC_BLOCKER_FOUND** | ≥1 Class A finding (Tier 1 or contemporaneous Tier 2) |
| **PR_TARGETED_VERIFICATION_REQUIRED** | No Class A; ≥1 Class U OR ≥1 material Class B |
| **PR_STATIC_REVIEW_NO_BLOCKER_FOUND** | No Class A; no Class U; only B (immaterial) / C / NONE |

Aggregate outcome:

| Aggregate | Trigger |
|---|---|
| **STATIC_BLOCKER_FOUND** | ≥1 PR is PR_STATIC_BLOCKER_FOUND |
| **TARGETED_VERIFICATION_REQUIRED** | No proven Class A; ≥1 PR has unresolved U or material B findings |
| **STATIC_REVIEW_NO_BLOCKER_FOUND** | No proven Class A; no unresolved U on any PR |

Precedence: `STATIC_BLOCKER_FOUND > TARGETED_VERIFICATION_REQUIRED > STATIC_REVIEW_NO_BLOCKER_FOUND`.

---

## 3. Evidence-universe inventory + scope-completeness

### 3.1 Inventory inputs (read-only)

The audit read the following routing / closure / kickoff memos at master `0d06ad2` to enumerate every formal β-eval cited as evidence in the routing-memo "5-eval / 8-eval / 9-eval picture" framings:

- `docs/design/phase27_kickoff.md`
- `docs/design/phase27_routing_review_post_27_{0b,0c,0d,0e}.md`
- `docs/design/phase27_post_27_0f_routing_review.md`
- `docs/design/phase27_closure_memo.md`
- `docs/design/phase28_kickoff.md`
- `docs/design/phase28_first_mover_routing_review.md`
- `docs/design/phase28_post_28_{0a,0b,0c}_routing_review.md`
- `docs/design/phase28_closure_memo.md`
- `docs/design/phase29_kickoff.md`
- `docs/design/phase29_first_mover_routing_review.md`
- `docs/design/phase29_post_29_0a_routing_review.md`
- `docs/design/phase29_a0_broad_preflight_audit.md`
- `docs/design/phase29_0b_alpha_a0_broad_design_memo.md`

### 3.2 Primary audited scope (locked)

The Phase 29 post-29.0a routing review §1 explicitly names the **9-eval evidence picture** (`docs/design/phase29_post_29_0a_routing_review.md:32-48` at master `0d06ad2`); the Phase 28 closure memo §4 names the **8-eval evidence picture**; the Phase 27 closure memo §1 names the **5-eval evidence picture**. The union of these three pictures is exactly the candidate 9 β-evals listed in the user's instruction set.

| # | Phase label | Supplying β-eval PR | Squash-merge commit SHA | Anchor in control chain |
|---|---|---|---|---|
| 1 | 27.0b-β | **#318** | `17be66aa17c4` | (S-C TIME penalty cell; not a control anchor) |
| 2 | 27.0c-β | **#321** | `0c34ebe42dd2` | (S-D calibrated EV cell; not a control anchor) |
| 3 | 27.0d-β | **#325** | `999859fa6443` | 1st anchor — C-se |
| 4 | 27.0e-β | **#328** | `0d9eca043902` | (S-E quantile-trim; not a control anchor) |
| 5 | 27.0f-β | **#332** | `ad673b4a1c9e` | 2nd anchor — C-se-r7a-replica |
| 6 | 28.0a-β | **#338** | `2b6dee1ea6c6` | 3rd anchor — C-a1-se-r7a-replica |
| 7 | 28.0b-β | **#342** | `c4abdee0d3ca` | 4th anchor — C-a4-top-q-control |
| 8 | 28.0c-β | **#345** | `49c08f5e0b8a` | 5th anchor — C-a0-arch-control |
| 9 | 29.0a-β | **#351** | `abe1ed5b7f1c` | 6th anchor — C-d1-target-control |

(Squash-merge SHAs above are the first 12 characters; the audit doc uses 7-character prefixes in evidence pointers below for brevity. Full 40-character SHAs are recorded in the findings JSON.)

### 3.3 Inventory-discovered finding (citation drift; recorded for §9 Dimension 9)

The Phase 28 closure memo §4 (`docs/design/phase28_closure_memo.md:94-101` at master `0d06ad2`) and the Phase 29 post-29.0a routing review §1 (`docs/design/phase29_post_29_0a_routing_review.md:36-46` at master `0d06ad2`) cite the following PR numbers for the first three Phase 27 β-evals:

| Sub-phase | Cited (Phase 28 closure + Phase 29 post-29.0a) | Actual β-eval merge | Cited PR's actual content |
|---|---|---|---|
| 27.0b-β | PR #311 | PR #318 | #311 is `docs(phase26)` scope amendment (not a β-eval) |
| 27.0c-β | PR #319 | PR #321 | #319 is `docs(phase27) post-27.0b routing review` (not a β-eval) |
| 27.0e-β | PR #327 | PR #328 | #327 is `docs(phase27-0e-alpha)` design memo (not a β-eval) |

The Phase 27 closure memo §1 (`docs/design/phase27_closure_memo.md:25-29` at master `0d06ad2`) cites correctly: 27.0b-β = #318, 27.0c-β = #321, 27.0e-β = #328.

This is a citation drift: the authoritative Phase 27 closure cites correctly, downstream memos at Phase 28 closure + Phase 29 post-29.0a propagate an incorrect three-PR-citation pattern (every cited number is off by ±2-7 PRs and refers to a non-β-eval PR). The β-eval evidence itself is unaffected (the actual β-eval merges exist and contain the eval_report); the routing-memo citation strings mislabel the supplying PRs.

Classification per (PR × dimension): supporting-dependency contamination affecting Phase 28 closure + Phase 29 post-29.0a memos (not the β-evals themselves). Class B at the routing-memo level (citation accuracy); does not modify any β-eval verdict. See §16.

### 3.4 Scope-completeness verdict

**SPINE_COMPLETE**. No additional β-evals discovered in routing-memo evidence pictures beyond the 9 candidate PRs. No PRs in the candidate set are non-β-evals (all 9 are formal β-eval squash-merges with eval_report.md + script + tests committed). No β-evals require exclusion. Primary audited scope is locked at the above 9 PRs.

### 3.5 Supporting-dependency scope (read-only; §16 traces contamination only)

The following are read-only contamination-tracing targets; no standalone historical verdict modification is issued for them:

| Dependency | Audit purpose |
|---|---|
| D-1 bid/ask executable harness — `_compute_realised_barrier_pnl` + `precompute_realised_pnl_per_row` | Verify identity across all 9 β-eval merge SHAs; confirm no mid-price leakage |
| S-B raw P(TP)−P(SL) multiclass head — origin (pre-Phase 27) + Phase 28 §10 numeric introduction | Verify the immutable baseline numeric `(n=34,626 / Sharpe -0.1732 / ann_pnl -204,664.4 / val Sharpe -0.1863)` is not in-PR modified by any spine PR |
| Fix A row-set isolation — introducing commit (post-#332), scope (R7-C drop → C-se-rcw only), inheritance into post-#332 PRs | Trace Fix A propagation into #338 / #342 / #345 / #351 |
| Option 9c framing — PR #348 / #350 / #351 context | Verify Option 9c simple-case inheritance for #351 (target unchanged → direct inheritance of Phase 28 §10) |
| Phase 28.0b A4 scope amendment (PR #340) | Confirm amendment was applied at #342 merge time |

---

## 4. Universal cross-PR structural findings (apply to all 9 β-evals)

Two structural findings apply uniformly to all 9 audited PRs because they arise from the .gitignore policy that was in effect at every merge.

### 4.1 U-1 — Machine-readable artifact run-provenance is gitignored across all 9 PRs (Class U; Tier 3 absence blocks Tier 1/2 verification)

At every merge commit `<sha>` for the 9 spine PRs:

```
git show <sha>:.gitignore  # shows the following patterns are gitignored:
artifacts/stageXX_Xy/sweep_results.parquet
artifacts/stageXX_Xy/sweep_results.json
artifacts/stageXX_Xy/aggregate_summary.json
artifacts/stageXX_Xy/val_selected_cell.json
artifacts/stageXX_Xy/sanity_probe.json
```

The only committed evidence file per PR is `artifacts/stageXX_Xy/eval_report.md` (a human-readable markdown). The machine-readable sweep results, aggregate summary, val-selected cell record, and sanity probe outputs are absent from the merge commit.

**Consequence**: the eval_report.md numerics cannot be independently cross-checked against any committed machine-readable artifact at the merge-time snapshot. Re-running the eval would regenerate sweep_results / aggregate_summary, but rerun is **out of scope** per audit policy (§2.2).

**Classification**: Class **U** on Dimension 8 (artifact / code reproducibility — run-provenance column) for every PR; Class **U** on Dimension 6 (baseline reproduction — run-provenance column) for every PR for the numeric FAIL-FAST claim (the eval_report states FAIL-FAST PASS, but the underlying baseline-cell sweep_results entry is gitignored). The static-code column for both dimensions is separately classified per §5–§13 (typically NONE or C).

**Tier**: Tier 3 (forward hardening) — these artifacts being gitignored at the time of each merge is a contemporaneous engineering choice that pre-dates the rev2-α stage-artifact-provenance framing. The absence is NOT auto-Class-A or auto-Class-C; per §2.5, it is **Class U** because it blocks Tier-1 (baseline reproduction) and Tier-2 (FAIL-FAST executed) verification.

**Suggested action** (per-PR): `TARGETED_VERIFICATION` — at user's discretion, a future authorised re-execution PR can regenerate sweep_results.parquet for a single targeted PR and cross-check eval_report.md numerics. This audit does not perform that rerun.

### 4.2 U-2 — Sanity-probe HALT outcome cannot be independently verified (Class U; Tier 2 absence blocks contemporaneous-contract claim)

Each PR's eval_report.md asserts "sanity probe PASS" or enumerates per-item HALT-gate results, but the underlying `sanity_probe.json` is gitignored at every merge SHA. The sanity probe is a contemporaneous-contract-required HALT gate per each PR's own design memo (e.g., 27.0d-α §10; 28.0c-α §15; 29.0a-α §13).

**Classification**: Class **U** on Dimension 6 (baseline reproduction — run-provenance for sanity-probe PASS) and Dimension 1 (split integrity — run-provenance for class-prior / NaN-rate / coverage gates). Static-code is separately classified.

**Tier**: Tier 2 (contemporaneous contract) — sanity probe was required by each PR's own merged memo; its result is not independently checkable from committed evidence. Per §2.5, this is Class U.

### 4.3 Implication for the aggregate verdict

U-1 and U-2 are present across **all 9 PRs**. Per the §2.6 outcome ladder, the aggregate audit verdict cannot be `STATIC_REVIEW_NO_BLOCKER_FOUND` because that label requires zero unresolved Class U findings across all PRs. The aggregate verdict will therefore be **at minimum** `TARGETED_VERIFICATION_REQUIRED` regardless of whether any Class A is found in static-code dimensions.

Whether the aggregate becomes `STATIC_BLOCKER_FOUND` depends on whether any per-PR Class A is found in §5–§13.

---

## 5. Per-PR audit: 27.0b-β / PR #318 / `17be66a`

Sub-phase: S-C TIME penalty α grid eval. Closed allowlist α ∈ {0.0, 0.3, 0.5, 1.0}. Verdict: REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL.

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | `split_70_15_15` used; pair universe + datetime boundaries set in `_build_pair_runtime`; per-pair row counts logged to stdout in eval_report §3. (PR #318 @ `17be66a` :: `scripts/stage27_0b_s_c_time_penalty_eval.py:_build_pair_runtime`) | Per-pair / per-split row counts reported in eval_report.md §3 but underlying `sweep_results.parquet` gitignored; cannot cross-check counts against any committed artifact. | 1 (static) / 2 (run-prov) | NONE (static) / **U** (run-prov; per §4.1) |
| 2 | Test isolation | Sanity probe reads test_df for **class-prior counts + NaN-rate only** (non-verdict-affecting; coverage gates only). Per-cell evaluator computes test PnL during sweep; val-selection key reads only val_sharpe (no test field in selection sort key). Standard "test-touched-once-per-(cell,q)" pattern. (PR #318 @ `17be66a` :: `scripts/stage27_0b_s_c_time_penalty_eval.py` sanity probe + cell sweep) | The actually-emitted val-selection record is gitignored (`val_selected_cell.json`). Cannot independently confirm that the actual run's val-selection step never read test_sharpe. | 1 (static) / 2 (run-prov) | NONE (static) / **U** (run-prov) |
| 3 | Row-set comparability | C-sb-baseline + C-sc-α cells fitted on same R7-A-clean training row-set; per-cell row counts logged in eval_report.md §7. | Per-cell row-count equality is asserted in eval_report.md but underlying parquet absent. | 1 / 2 | NONE (static) / **U** (run-prov) |
| 4 | D-1 executable PnL integrity | Sanity probe item 3 explicitly checks: `_compute_realised_barrier_pnl` source contains `bid_h / ask_l / ask_h / bid_l`; `precompute_realised_pnl_per_row` signature does not expose `spread_factor` or `mid_to_mid`. HALT on violation. | Mid-to-mid PnL distribution is computed as DIAGNOSTIC-ONLY (logged but not used in verdict path). | 1 | NONE |
| 5 | Axis purity | S-C TIME penalty axis: α ∈ {0.0, 0.3, 0.5, 1.0} grid. α=0.0 cell is documented as the baseline-match cell (no TIME penalty). Other axes (loss / selection / target / feature / scorer base) declared unchanged. eval_report.md §6 confirms α=0.0 sanity-check tied to Phase 26 R6-new-A C02 baseline. | α=0.0 baseline-match PASS claimed in eval_report.md §6 but the underlying parquet entry is absent. | 1 (static) / 2 (run-prov) | NONE (static) / **U** (run-prov for the α=0.0 baseline-match assertion) |
| 6 | Baseline reproduction | This PR predates the Phase 28 §10 immutable baseline (which is introduced at PR #335 Phase 28 kickoff). The contemporaneous baseline at 27.0b is the Phase 26 R6-new-A C02 baseline; α=0.0 cell reproduces it. | α=0.0 reproduction asserted in eval_report.md but no committed JSON to cross-check. | 2 | **U** (run-prov; contemporaneous Phase 26 baseline) |
| 7 | Control-chain integrity | Not applicable: 27.0b-β predates the 6-anchor C-se chain (which begins at 27.0d). The R6-new-A baseline link is the contemporaneous control. | (see §15 cross-PR control-chain matrix) | n.a. | NONE |
| 8 | Artifact / code reproducibility | eval script + tests + eval_report.md committed at merge. Seeds / deterministic flags referenced in code. No `contract_hash` / `code_hash` / `data_manifest_hash` (rev2-α framing did not exist). | Per §4.1: sweep_results.parquet / json / aggregate_summary.json / val_selected_cell.json / sanity_probe.json all gitignored. Eval_report.md numerics cannot be cross-checked from committed artifacts. | 3 (rev2 absence) | C (no rev2 provenance; pre-rev2 era) + **U** (run-prov for numerics) |
| 9 | Verdict-code consistency | Verdict label `REJECT_NON_DISCRIMINATIVE` / `H1_WEAK_FAIL` emitted; per eval_report.md §1 + §8 the per-cell H-B3-style ladder produces the verdict from val Sharpe lift. Per-α monotonicity (val/test Sharpe decreasing as α increases; Spearman increasing) documented. | Per-cell val_sharpe + test_sharpe + Spearman values quoted in eval_report.md but underlying parquet absent. | 1 (memo↔code constants) / 2 (run-prov for emitted verdict) | NONE (static) / **U** (run-prov for the emitted verdict's numeric inputs) |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED** (no Class A; multiple Class U on run-provenance per §4.1/§4.2; static-code clean).

---

## 6. Per-PR audit: 27.0c-β / PR #321 / `0c34ebe`

Sub-phase: S-D calibrated EV eval. Closed allowlist β ∈ {0.0, 0.3, 0.5, 1.0}. Verdict: REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL.

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | Inherits split + pair universe + `_build_pair_runtime` from 27.0b pattern. (PR #321 @ `0c34ebe` :: `scripts/stage27_0c_s_d_calibrated_ev_eval.py`) | Row counts in eval_report.md §3; parquet absent. | 1 / 2 | NONE / **U** |
| 2 | Test isolation | Same pattern as 27.0b: sanity probe reads test only for class priors + NaN rates; val-selection by val_sharpe only. | val_selected_cell.json gitignored. | 1 / 2 | NONE / **U** |
| 3 | Row-set comparability | C-sb-baseline + C-sd-β cells share R7-A-clean row-set. | parquet absent. | 1 / 2 | NONE / **U** |
| 4 | D-1 executable PnL integrity | Inherited harness; sanity probe verifies bid/ask + no mid-price in formal path. | NONE |
| 5 | Axis purity | S-D calibrated EV axis; β grid; other axes unchanged. eval_report.md §1 confirms "same wrong-direction as 27.0b S-C; Spearman improved +0.047 yet realised Sharpe worse". | parquet absent. | 1 / 2 | NONE / **U** |
| 6 | Baseline reproduction | C-sb-baseline reproduction PASS claimed in eval_report.md. | sweep_results parquet absent. | 2 | **U** |
| 7 | Control-chain integrity | Pre-C-se chain (chain starts at 27.0d). | n.a. | NONE |
| 8 | Artifact / code reproducibility | Same gitignore pattern as 27.0b; eval_report.md only. | per §4.1 | 3 | C + **U** |
| 9 | Verdict-code consistency | H-B3 ladder; verdict `REJECT_NON_DISCRIMINATIVE` consistent with reported numerics. | parquet absent. | 1 / 2 | NONE / **U** |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED**.

---

## 7. Per-PR audit: 27.0d-β / PR #325 / `999859f` — **1st anchor (C-se)**

Sub-phase: S-E regression-on-realised-PnL eval. Loss: symmetric Huber α=0.9. Verdict: SPLIT_VERDICT_ROUTE_TO_REVIEW (C-se H1m_PASS Spearman +0.4381; H2 FAIL).

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | `split_70_15_15` + `_build_pair_runtime`; per-pair row counts in eval_report.md §3. (PR #325 @ `999859f` :: `scripts/stage27_0d_s_e_regression_eval.py:_build_pair_runtime` + `split_70_15_15`) | Row counts in eval_report.md; parquet absent. | 1 / 2 | NONE / **U** |
| 2 | Test isolation | Sanity probe (`run_sanity_probe_27_0d` :: `scripts/stage27_0d_s_e_regression_eval.py:578-...`) reads test_df only for class-prior counts + NaN-rate (non-verdict-affecting HALT gates). `evaluate_cell_27_0d` (line 930) computes test PnL during sweep; val-selection via `_q_sort_key` (line 980) reads val fields only (val Sharpe / val annualised PnL / val n_trades). Test fields appear in the per-(cell,q) record but are not in the selection sort key. Standard "test-touched-once-per-(cell,q)" pattern preserved. | val_selected_cell.json gitignored; cannot independently confirm the actual run's val-selection step never read test_sharpe. | 1 (static) / 2 (run-prov) | NONE (static) / **U** (run-prov) |
| 3 | Row-set comparability | C-sb-baseline + C-se cells share R7-A-clean row-set (Fix A not yet introduced; first appears at 27.0f). | parquet absent. | 1 / 2 | NONE / **U** |
| 4 | D-1 executable PnL integrity | Sanity probe item 3 (PR #325 @ `999859f` :: `scripts/stage27_0d_s_e_regression_eval.py:660-680`): `_compute_realised_barrier_pnl` source must contain `bid_h / ask_l / ask_h / bid_l`; `precompute_realised_pnl_per_row` signature must not expose `spread_factor` or `mid_to_mid`. HALT on violation (`SanityProbeError`). | NONE |
| 5 | Axis purity | S-E regression axis. Loss = symmetric Huber α=0.9. Other axes declared unchanged. eval_report.md §1 / §8: H1m PASS (Spearman +0.4381) but H2 FAIL (realised Sharpe wrong-direction). | parquet absent. | 1 / 2 | NONE / **U** |
| 6 | Baseline reproduction | C-sb-baseline match check at end of main (PR #325 @ `999859f` :: `scripts/stage27_0d_s_e_regression_eval.py:1826-1834`); raises `BaselineMismatchError` on mismatch. FAIL-FAST happens AFTER cell sweep completes but BEFORE `val_selected_cell.json` is written (which is the "verdict assignment" per the contract header at line 49). | C-sb-baseline match PASS asserted in eval_report.md §10 but underlying sweep_results.parquet entry gitignored. | 1 (static) / 2 (run-prov) | NONE (static) / **U** (run-prov) |
| 7 | Control-chain integrity | This PR introduces C-se as the **1st anchor** in the subsequent bit-tight reproduction chain. Scorer = vanilla S-E LightGBM regressor on R7-A; fit = R7-A-clean train; eval = R7-A-clean val + test; preprocessing = R7-A 4 features; target = inherited triple-barrier realised PnL; tolerance n/a (defines the anchor); reported outcome = H1m PASS / H2 FAIL. | All 6-anchor cross-PR drift values are reported in subsequent PRs' eval_reports (`§11b`-style sections) but the underlying per-cell parquet entries are gitignored. | n.a. | NONE (anchor definition; not a drift claim) |
| 8 | Artifact / code reproducibility | Same gitignore pattern; eval_report.md + script + tests committed. | per §4.1 | 3 | C + **U** |
| 9 | Verdict-code consistency | H-B4 4-outcome ladder (per design memo PR #324 / 27.0d-α §3 — at master `0d06ad2` since 27.0d-α already merged). Verdict `SPLIT_VERDICT_ROUTE_TO_REVIEW` consistent with reported per-cell numerics in eval_report.md §13. | per-cell val/test numerics quoted in eval_report.md; parquet absent. | 1 / 2 | NONE / **U** |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED** (no Class A; static-code clean throughout; structural Class U on run-provenance).

---

## 8. Per-PR audit: 27.0e-β / PR #328 / `0d9eca0`

Sub-phase: S-E quantile family trim eval. Closed allowlist q ∈ {5, 7.5, 10}. Verdict: SPLIT_VERDICT_ROUTE_TO_REVIEW / H-B5 PARTIAL_SUPPORT.

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | Inherits 27.0d pattern; same `_build_pair_runtime`. | parquet absent. | 1 / 2 | NONE / **U** |
| 2 | Test isolation | Same pattern as 27.0d. | val_selected_cell.json gitignored. | 1 / 2 | NONE / **U** |
| 3 | Row-set comparability | C-sb-baseline + C-se-trimmed cells share R7-A-clean row-set. | parquet absent. | 1 / 2 | NONE / **U** |
| 4 | D-1 executable PnL integrity | Inherited harness; sanity probe verifies bid/ask + no mid-price. | n.a. | 1 | NONE |
| 5 | Axis purity | S-E quantile trim axis (q ∈ {5, 7.5, 10}); scorer / loss / target unchanged from 27.0d. eval_report.md §1: "C-se-trimmed q*=10 test_sharpe=-0.767 (WORSE than 27.0d -0.483) but Spearman +0.4381 preserved". | parquet absent. | 1 / 2 | NONE / **U** |
| 6 | Baseline reproduction | C-sb-baseline reproduction PASS asserted. | parquet absent. | 2 | **U** |
| 7 | Control-chain integrity | Not a designated anchor (the C-se-r7a-replica anchor begins at 27.0f, not 27.0e). | n.a. | NONE |
| 8 | Artifact / code reproducibility | Same gitignore pattern. | per §4.1 | 3 | C + **U** |
| 9 | Verdict-code consistency | H-B5 ladder; verdict PARTIAL_SUPPORT (row 2) consistent with reported Spearman-preservation + worse Sharpe. R-T2 trim-alone-does-NOT-recover-monetisation. | parquet absent. | 1 / 2 | NONE / **U** |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED**.

---

## 9. Per-PR audit: 27.0f-β / PR #332 / `ad673b4` — **2nd anchor (C-se-r7a-replica) + Fix A introduction**

Sub-phase: S-E + R7-C regime/context feature widening. RCW with row-set isolation (Fix A). Verdict: H-B6 FALSIFIED_R7C_INSUFFICIENT (row 3); REJECT_NON_DISCRIMINATIVE.

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | Inherits 27.0d pattern. Fix A is documented in eval_report.md §3 as "R7-C drop applied to C-se-rcw only". | parquet absent. | 1 / 2 | NONE / **U** |
| 2 | Test isolation | Same pattern. | val_selected_cell.json gitignored. | 1 / 2 | NONE / **U** |
| 3 | Row-set comparability | **Fix A row-set isolation**: R7-C-feature drop applied to C-se-rcw only; C-sb-baseline + C-se r7a-replica retain full R7-A-clean row-set. Per eval_report.md §3 + commit message "Fix A row-set isolation applied". | Per-cell row counts asserted in eval_report.md; parquet absent. | 1 (static design) / 2 (run-prov) | NONE (static) / **U** (run-prov: row-set isolation actually applied) |
| 4 | D-1 executable PnL integrity | Inherited harness. | n.a. | 1 | NONE |
| 5 | Axis purity | R7-C regime/context feature widening axis. eval_report.md §1 + §8 confirm R7-A static-feature surface and 27.0d S-E regressor preserved. | parquet absent. | 1 / 2 | NONE / **U** |
| 6 | Baseline reproduction | C-sb-baseline reproduction PASS; r7a-replica drift "within tolerance". | parquet absent; drift numerics quoted in eval_report.md §11b but not independently cross-checkable. | 2 | **U** |
| 7 | Control-chain integrity | **2nd anchor: C-se-r7a-replica**. r7a-replica is the C-se backbone re-fit on R7-A only (R7-C dropped via Fix A). Drift tolerance: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5% (per design memo PR #331). Reported drift "within tolerance" per eval_report.md §11b. | Drift numerics from r7a-replica cell quoted in eval_report.md but the cell's sweep_results entry is gitignored. | 2 (contemporaneous drift tolerance check) | **U** (run-prov: drift PASS independently unverifiable) |
| 8 | Artifact / code reproducibility | Same gitignore pattern. | per §4.1 | 3 | C + **U** |
| 9 | Verdict-code consistency | H-B6 ladder; verdict `FALSIFIED_R7C_INSUFFICIENT` (row 3). R-T2 absorbed; R-T1 / R-T3 carry-forward. | parquet absent. | 1 / 2 | NONE / **U** |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED**.

---

## 10. Per-PR audit: 28.0a-β / PR #338 / `2b6dee1` — **3rd anchor (C-a1-se-r7a-replica)**

Sub-phase: A1 objective redesign. Closed allowlist L1 (asymmetric Huber α=0.5) / L2 (α=0.7) / L3 (α=0.9 + regime-axis weights). Verdict: all 3 FALSIFIED_OBJECTIVE_INSUFFICIENT; REJECT_NON_DISCRIMINATIVE.

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | Inherits 27.0f Fix A row-set isolation pattern. (PR #338 @ `2b6dee1` :: `scripts/stage28_0a_a1_objective_redesign_eval.py`) | parquet absent. | 1 / 2 | NONE / **U** |
| 2 | Test isolation | Same val-selection-by-val_sharpe pattern. | val_selected_cell.json gitignored. | 1 / 2 | NONE / **U** |
| 3 | Row-set comparability | C-sb-baseline + C-a1-* cells share R7-A-clean row-set; Fix A propagated. | parquet absent. | 1 / 2 | NONE / **U** |
| 4 | D-1 executable PnL integrity | Inherited harness; sanity probe verifies bid/ask + no mid-price. | n.a. | 1 | NONE |
| 5 | Axis purity | A1 loss axis. Loss varied L1/L2/L3; other axes (target / selection / feature / scorer base) unchanged. | parquet absent. | 1 / 2 | NONE / **U** |
| 6 | Baseline reproduction | **Phase 28 §10 immutable baseline** referenced for the first time (introduced contemporaneously at PR #335 Phase 28 kickoff; numeric n=34,626 / Sharpe -0.1732 / ann_pnl -204,664.4 / val Sharpe -0.1863). C-sb-baseline reproduction PASS claimed in eval_report.md §10. | sweep_results parquet absent → numeric reproduction not independently verifiable from committed evidence. | 1 (Phase 28 §10 immutable; Tier-1 baseline integrity) / 2 (run-prov for FAIL-FAST) | NONE (no in-PR modification of immutable numeric) / **U** (run-prov: reproduction PASS not independently verifiable) |
| 7 | Control-chain integrity | **3rd anchor: C-a1-se-r7a-replica**. Reproduces C-se-r7a-replica (2nd anchor at 27.0f) with L3=α=0.9 (matched to 27.0d C-se loss). Reported drift "within tolerance". | Drift numerics quoted in eval_report.md §11b but cell parquet absent. | 2 | **U** |
| 8 | Artifact / code reproducibility | Same gitignore pattern. | per §4.1 | 3 | C + **U** |
| 9 | Verdict-code consistency | H-C1 4-outcome ladder (per design memo PR #337). Per-L verdict FALSIFIED_OBJECTIVE_INSUFFICIENT; aggregate REJECT_NON_DISCRIMINATIVE. Verdict naming consistent with PR #337 memo. | parquet absent. | 1 / 2 | NONE / **U** |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED**.

---

## 11. Per-PR audit: 28.0b-β / PR #342 / `c4abdee` — **4th anchor (C-a4-top-q-control)**

Sub-phase: A4 monetisation-aware selection rule. Closed allowlist R1 / R2 / R3 / R4 (Clause 2 amendment at PR #340). Verdict: all 4 FALSIFIED_RULE_INSUFFICIENT; REJECT_NON_DISCRIMINATIVE; R-T1 = FALSIFIED_under_A4.

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | Inherits pattern. (PR #342 @ `c4abdee` :: `scripts/stage28_0b_a4_monetisation_aware_selection_eval.py`) | parquet absent. | 1 / 2 | NONE / **U** |
| 2 | Test isolation | Same pattern. | val_selected_cell.json gitignored. | 1 / 2 | NONE / **U** |
| 3 | Row-set comparability | C-sb-baseline + C-a4-* + C-a4-top-q-control cells share R7-A-clean row-set; Fix A propagated. | parquet absent. | 1 / 2 | NONE / **U** |
| 4 | D-1 executable PnL integrity | Inherited harness. | n.a. | 1 | NONE |
| 5 | Axis purity | A4 selection-rule axis. Per design memo (PR #341) and scope amendment (PR #340 Clause 2), non-quantile cell shapes R1 + R4 admitted alongside quantile R2/R3. Other axes unchanged. R-T1 absorbed into A4 sub-frame per PR #341 §3. | parquet absent. | 1 / 2 | NONE / **U** |
| 6 | Baseline reproduction | Phase 28 §10 reproduction PASS asserted. | parquet absent. | 1 / 2 | NONE / **U** |
| 7 | Control-chain integrity | **4th anchor: C-a4-top-q-control**. Quantile R3=5% / top-K=1 baseline-equivalent control. Reported drift "within tolerance". | Drift numerics quoted in eval_report.md §11b; cell parquet absent. | 2 | **U** |
| 8 | Artifact / code reproducibility | Same gitignore pattern. | per §4.1 | 3 | C + **U** |
| 9 | Verdict-code consistency | H-C2 4-outcome ladder. Aggregate REJECT_NON_DISCRIMINATIVE; R-T1 = FALSIFIED_under_A4. Verdict naming consistent with PR #341 memo. | parquet absent. | 1 / 2 | NONE / **U** |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED**.

---

## 12. Per-PR audit: 28.0c-β / PR #345 / `49c08f5` — **5th anchor (C-a0-arch-control)**

Sub-phase: A0-narrow tabular topology audit. Closed allowlist AR1 (hierarchical) / AR2 (per-pair specialists) / AR3 (stacked) / AR4 (deterministic regime split). Verdict: all 4 FALSIFIED_ARCH_INSUFFICIENT; aggregate FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0).

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | Inherits pattern. (PR #345 @ `49c08f5` :: `scripts/stage28_0c_a0_architecture_topology_eval.py`) | parquet absent. | 1 / 2 | NONE / **U** |
| 2 | Test isolation | Same pattern. | val_selected_cell.json gitignored. | 1 / 2 | NONE / **U** |
| 3 | Row-set comparability | C-sb-baseline + 4 AR cells + C-a0-arch-control share R7-A-clean row-set; Fix A propagated. | parquet absent. | 1 / 2 | NONE / **U** |
| 4 | D-1 executable PnL integrity | Inherited harness. | n.a. | 1 | NONE |
| 5 | Axis purity | A0-narrow tabular topology axis. Per design memo PR #344, the FALSIFIED_A0_NARROW distinction (NEVER FALSIFIED_ALL_A0) is explicitly enforced; A0-broad sequence/NN remains deferred-not-foreclosed. | parquet absent. | 1 / 2 | NONE / **U** |
| 6 | Baseline reproduction | Phase 28 §10 reproduction PASS asserted. | parquet absent. | 1 / 2 | NONE / **U** |
| 7 | Control-chain integrity | **5th anchor: C-a0-arch-control**. Vanilla S-E LightGBM with L3=α=0.9 on R7-A; matched to prior anchors. Reported drift "within tolerance". | Drift numerics quoted in eval_report.md §11b; cell parquet absent. | 2 | **U** |
| 8 | Artifact / code reproducibility | Same gitignore pattern. | per §4.1 | 3 | C + **U** |
| 9 | Verdict-code consistency | H-C3 4-outcome ladder. Per-AR verdict FALSIFIED_ARCH_INSUFFICIENT; aggregate FALSIFIED_A0_NARROW. NARROW vs ALL distinction explicit in PR #344 design memo §12.2. | parquet absent. | 1 / 2 | NONE / **U** |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED**.

---

## 13. Per-PR audit: 29.0a-β / PR #351 / `abe1ed5` — **6th anchor (C-d1-target-control)**

Sub-phase: A2 target redesign. Closed allowlist T1 (fixed-horizon close) / T2 (time-weighted) / T3 (multi-horizon; R-T3 absorbed) / T4 (asymmetric K_FAV/K_ADV). Verdict: all 4 FALSIFIED_TARGET_INSUFFICIENT; aggregate FALSIFIED_A2_NARROW; R-T3 = FALSIFIED_under_T3.

| # | Dimension | Static-code finding | Run-provenance finding | Tier | Classification |
|---|---|---|---|---|---|
| 1 | Split integrity | Inherits pattern. (PR #351 @ `abe1ed5` :: `scripts/stage29_0a_a2_target_redesign_eval.py`) | parquet absent. | 1 / 2 | NONE / **U** |
| 2 | Test isolation | Same pattern. | val_selected_cell.json gitignored. | 1 / 2 | NONE / **U** |
| 3 | Row-set comparability | Per-target NaN-PnL propagation: when a target produces NaN PnL on a row, that row is excluded from the cell's effective row-set. Per-target row counts logged in eval_report.md. | parquet absent. | 1 / 2 | NONE (static design) / **U** (run-prov) |
| 4 | D-1 executable PnL integrity | Per design memo PR #350, all 4 targets are D-1 executable (long ask_o / short bid_o entry; barrier-driven resolution). | n.a. | 1 | NONE |
| 5 | Axis purity | A2 target axis. Other axes (loss / selection / feature / scorer base) unchanged. R-T3 absorbed into A2 via T3 multi-horizon. eval_report.md §1: all 4 targets FALSIFIED_TARGET_INSUFFICIENT. | parquet absent. | 1 / 2 | NONE / **U** |
| 6 | Baseline reproduction | **Option 9c simple-case**: target unchanged for C-sb-baseline → direct inheritance of Phase 28 §10 immutable (n=34,626 / Sharpe -0.1732 / ann_pnl -204,664.4 / val Sharpe -0.1863). Additionally introduces **Phase 29 §10 per-target baselines** (T1/T2/T3/T4 frozen at PR #351 in `artifacts/stage29_0a/phase29_section10_per_target_baseline.json` — this file IS committed at #351; one of only two committed JSON artifacts in the entire 9-eval spine). | The per-target baseline JSON `artifacts/stage29_0a/phase29_section10_per_target_baseline.json` is committed (141 lines per `git show abe1ed5 --stat`). The C-sb-baseline (Phase 28 §10 reproduction) sweep_results parquet remains gitignored. | 1 (Phase 28 §10 + Option 9c) / 2 (per-target baseline JSON committed → REPRODUCIBLE) | NONE (static) / **partial U** (run-prov: per-target baseline is REPRODUCIBLE from committed JSON; Phase 28 §10 reproduction remains U) |
| 7 | Control-chain integrity | **6th anchor: C-d1-target-control**. Vanilla S-E LightGBM with L3=α=0.9 on R7-A; target = inherited triple-barrier; matched to prior anchors. Reported drift "within tolerance". | Drift numerics quoted in eval_report.md §11b; cell parquet absent. | 2 | **U** |
| 8 | Artifact / code reproducibility | One additional committed JSON (per-target baseline) compared to prior PRs. Other artifacts (sweep_results / aggregate / val_selected / sanity_probe) gitignored. | partially improved vs prior PRs (committed per-target baseline JSON). | 3 | C + partial **U** |
| 9 | Verdict-code consistency | H-D1 4-outcome ladder (per design memo PR #350). Aggregate FALSIFIED_A2_NARROW (NEVER FALSIFIED_ALL_A2). R-T3 = FALSIFIED_under_T3 consistent with PR #350 framing. | parquet absent (verdict numerics not independently checkable). | 1 / 2 | NONE / **U** |

**Per-PR outcome**: **PR_TARGETED_VERIFICATION_REQUIRED** (slightly better run-provenance than prior PRs due to committed per-target baseline JSON, but Phase 28 §10 reproduction and main sweep results remain Class U).

---

## 14. Per-PR outcome summary

| # | PR | Phase | Per-PR outcome | Reason |
|---|---|---|---|---|
| 1 | #318 | 27.0b-β | PR_TARGETED_VERIFICATION_REQUIRED | structural U (§4.1/§4.2); no static A |
| 2 | #321 | 27.0c-β | PR_TARGETED_VERIFICATION_REQUIRED | structural U; no static A |
| 3 | #325 | 27.0d-β | PR_TARGETED_VERIFICATION_REQUIRED | structural U; no static A |
| 4 | #328 | 27.0e-β | PR_TARGETED_VERIFICATION_REQUIRED | structural U; no static A |
| 5 | #332 | 27.0f-β | PR_TARGETED_VERIFICATION_REQUIRED | structural U; no static A; Fix A introduced |
| 6 | #338 | 28.0a-β | PR_TARGETED_VERIFICATION_REQUIRED | structural U; no static A; Phase 28 §10 immutable introduced |
| 7 | #342 | 28.0b-β | PR_TARGETED_VERIFICATION_REQUIRED | structural U; no static A |
| 8 | #345 | 28.0c-β | PR_TARGETED_VERIFICATION_REQUIRED | structural U; no static A; FALSIFIED_A0_NARROW distinction explicit |
| 9 | #351 | 29.0a-β | PR_TARGETED_VERIFICATION_REQUIRED | partial U improvement (committed per-target baseline JSON); no static A |

**Class A count**: 0 (across all 9 PRs × 9 dimensions)
**Class U count**: 81 (structural U-1 + U-2 + per-dimension run-provenance gaps; dominated by gitignored sweep_results / aggregate / val_selected / sanity_probe artifacts across 9 PRs × multiple dimensions)
**Class B count**: 0 at the β-eval level; 1 at the supporting-dependency level (citation drift at Phase 28 closure + Phase 29 post-29.0a routing memos; recorded in §16)
**Class C count**: 9 (one per PR for rev2-α-style provenance absence — pre-rev2 era)
**Class NONE count**: ~40+ on static-code dimensions where the committed code path is contract-clean

(Exact per-cell counts in the findings JSON.)

---

## 15. Cross-PR control-chain matrix (6 anchors)

| Anchor # | PR | Merge SHA | Scorer identity | Fit row-set | Eval row-set | Preprocessing | Target | Drift tolerance | Reported outcome | Run-provenance status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | #325 | `999859f` | vanilla S-E LightGBM regressor; symmetric Huber α=0.9; sample_weight=1 | R7-A-clean train | R7-A-clean val + test | R7-A 4 features (pair / direction / atr_at_signal_pip / spread_at_signal_pip) | inherited triple-barrier (K_FAV=1.5×ATR / K_ADV=1.0×ATR / H_M1=60); long ask_o / short bid_o entry | n.a. (defines anchor) | C-se: H1m PASS (Spearman +0.4381) / H2 FAIL (realised Sharpe wrong-direction) | **U** (sweep_results parquet gitignored) |
| 2 | #332 | `ad673b4` | same as 1 | R7-A-clean train (Fix A: R7-C drop applied to C-se-rcw only) | R7-A-clean val + test | R7-A 4 features (same as 1) | same as 1 | n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5% | C-se-r7a-replica: drift "within tolerance" | **U** (cell parquet gitignored) |
| 3 | #338 | `2b6dee1` | same as 1 (L3=α=0.9 matched to 27.0d) | R7-A-clean train; Fix A propagated | R7-A-clean val + test | R7-A 4 features | same | same | C-a1-se-r7a-replica: drift "within tolerance" | **U** |
| 4 | #342 | `c4abdee` | same as 1 | R7-A-clean train; Fix A propagated | R7-A-clean val + test | R7-A 4 features | same | same | C-a4-top-q-control (R3=5% / top-K=1): drift "within tolerance" | **U** |
| 5 | #345 | `49c08f5` | same as 1 | R7-A-clean train; Fix A propagated | R7-A-clean val + test | R7-A 4 features | same | same | C-a0-arch-control: drift "within tolerance" | **U** |
| 6 | #351 | `abe1ed5` | same as 1 | R7-A-clean train; Fix A propagated | R7-A-clean val + test | R7-A 4 features | same (Option 9c simple-case: target unchanged for C-d1-target-control) | same | C-d1-target-control: drift "within tolerance" | **U** |

**Cross-anchor static-code consistency**: NONE — all 6 anchors share the same scorer / fit / eval / preprocessing / target / drift-tolerance contract per their respective design memos.

**Cross-anchor run-provenance**: Class **U** across all 6 anchors — each drift "within tolerance" claim is asserted in the respective eval_report.md §11b-style section but the underlying per-anchor sweep_results.parquet entries are gitignored at every merge SHA.

**Cumulative drift**: cannot be quantified from committed evidence; rerun required.

---

## 16. Supporting-dependency contamination graph

> **Wording binding for §16 (all subsections)**: every "contamination status" line below describes the result of **static contract inspection** at each merge-time snapshot — i.e., "no visible contract violation found in the inspected committed code / memo". The static-clean finding **does NOT remove the structural Class U on run-provenance** established in §4.1 (U-1) and §4.2 (U-2). Actual historical execution of these dependencies remains **unverified** where committed machine-readable artifacts / sanity-probe outputs are absent. The aggregate audit outcome therefore remains `TARGETED_VERIFICATION_REQUIRED` (see §17). Wording such as "empirically clean across all 9 PRs" / "historical execution verified" / "tabular evidence reconfirmed" / "prior verdicts formally revalidated" is **NOT** used and **NOT** implied anywhere in this section.

### 16.1 D-1 bid/ask executable harness

- **Origin**: `_compute_realised_barrier_pnl` + `precompute_realised_pnl_per_row` in `scripts/_data_helpers/...` (introduced pre-Phase 27).
- **Static identity check across 9 merge SHAs**: every β-eval's sanity probe item 3 explicitly verifies (a) `_compute_realised_barrier_pnl` source contains `bid_h / ask_l / ask_h / bid_l`, and (b) `precompute_realised_pnl_per_row` signature does NOT expose `spread_factor` or `mid_to_mid`. HALT on violation.
- **Static-code contamination status**: **no visible contract violation found in D-1 harness lineage** across all 9 PRs in static inspection. No mid-price leakage into the formal PnL code path. Class NONE for Dimension 4 (D-1 integrity) on every PR at the static-code column.
- **Run-provenance status**: actual historical execution of the D-1 sanity-probe HALT gate remains **unverified** where the committed `sanity_probe.json` is absent (U-2). The static-clean code path does not by itself prove the run actually executed the inspected sanity-probe item 3. **This finding does NOT remove the structural Class U** on Dimension 6 (baseline reproduction — run-provenance) or Dimension 8 (artifact / code reproducibility — run-provenance).

### 16.2 S-B raw P(TP)−P(SL) multiclass head + Phase 28 §10 baseline numeric

- **Origin**: S-B multiclass head pre-dates Phase 27. The immutable baseline numeric `(n=34,626 / Sharpe -0.1732 / ann_pnl -204,664.4 / val Sharpe -0.1863)` is introduced contemporaneously at PR #335 (Phase 28 kickoff).
- **Static modification check across 9 merge SHAs**: no spine PR's committed memo / code / artifact contains a retroactive modification of the immutable numeric. Phase 27 PRs (predating PR #335) reference contemporaneous baselines (Phase 26 R6-new-A C02). Phase 28 + Phase 29 PRs all reference Phase 28 §10 verbatim.
- **Static-code contamination status**: **no visible contract violation found in Phase 28 §10 immutable baseline lineage** in static inspection. Class NONE for the Tier-1 retroactive-modification check (§2.5 universal blocker not triggered).
- **Run-provenance status**: each PR's claim of "C-sb-baseline reproduction PASS" against Phase 28 §10 is asserted in `eval_report.md §10` but the underlying baseline-cell `sweep_results.parquet` entry is gitignored (U-1). The static-clean lineage does not by itself prove the run actually reproduced the numeric. **This finding does NOT remove the structural Class U** on Dimension 6 (baseline reproduction — run-provenance) for PRs #338 / #342 / #345 / #351.

### 16.3 Fix A row-set isolation

- **Origin**: Introduced at PR #332 (27.0f-β); R7-C-feature drop applied to C-se-rcw cell only; C-sb-baseline + r7a-replica retain full R7-A-clean row-set.
- **Static propagation check**: Fix A is referenced by all subsequent spine PRs (#338 / #342 / #345 / #351). Per each PR's `eval_report.md §3`, the row-set construction documents inherit the 27.0f Fix A pattern.
- **Static-code contamination status**: **no visible contract violation found in Fix A inheritance** across #338 / #342 / #345 / #351 in static inspection. Class NONE for Dimension 1 (split integrity) and Dimension 3 (row-set comparability) at the static-code column.
- **Run-provenance status**: per-cell row counts demonstrating that the Fix A row-set isolation was actually applied at run time are asserted in `eval_report.md §3` but the underlying per-cell row-count artifacts (parquet) are gitignored. The static-clean inheritance does not by itself prove the run actually applied the isolation. **This finding does NOT remove the structural Class U** on Dimension 3 (row-set comparability — run-provenance) at the four propagating PRs.

### 16.4 Option 9c framing (Phase 29.0a)

- **Origin**: PR #348 (Phase 29 kickoff) introduces Option 9c (simple-case: target unchanged → direct inheritance of Phase 28 §10; redesign-case: per-target baseline reference required).
- **Static application check at #351**: A2 redesigns target → per-target baselines (T1/T2/T3/T4) frozen at `artifacts/stage29_0a/phase29_section10_per_target_baseline.json`. Phase 28 §10 retained as DIAGNOSTIC-ONLY 2nd reference (not the formal H-D1 comparator for redesigned targets).
- **Static-code contamination status**: **no visible contract violation found in Option 9c application** at #351 in static inspection. Per-target baseline JSON is one of the few machine-readable artifacts committed in the entire 9-eval spine.
- **Run-provenance status**: the per-target baseline JSON is REPRODUCIBLE_VIA_COMMITTED_ARTIFACT (committed; 141 lines). The C-sb-baseline (Phase 28 §10 reproduction) at #351 remains run-provenance Class U because the C-sb-baseline cell's `sweep_results.parquet` entry is gitignored (U-1). The partial improvement at #351 (committed per-target baseline JSON) does **NOT remove** the structural Class U on the C-sb-baseline reproduction component.

### 16.5 Phase 28.0b A4 scope amendment (PR #340)

- **Origin**: PR #340 amended Clause 2 to admit non-quantile cell shapes R1 (absolute threshold) + R4 (top-K per bar) alongside quantile R2/R3.
- **Static application check at #342**: 28.0b-β eval uses R1 / R2 / R3 / R4 closed allowlist per PR #341 / NG#A4-1. Scope amendment applied at merge time of #342.
- **Static-code contamination status**: **no visible contract violation found in PR #340 amendment application at #342** in static inspection. Code-level cell allowlist matches PR #341 design memo's pre-stated allowlist.
- **Run-provenance status**: actual per-cell execution of the R1 / R4 non-quantile cells (e.g., whether each cell's row-set was constructed as documented) remains **unverified** where `sweep_results.parquet` is gitignored. **This finding does NOT remove the structural Class U** at #342.

### 16.6 Citation drift (Phase 28 closure + Phase 29 post-29.0a routing memos)

- **Finding**: Phase 28 closure memo (`docs/design/phase28_closure_memo.md:94-101` at master `0d06ad2`) and Phase 29 post-29.0a routing review (`docs/design/phase29_post_29_0a_routing_review.md:36-46` at master `0d06ad2`) cite PR #311 / #319 / #327 for 27.0b/c/e-β. Correct PR numbers are #318 / #321 / #328 (cited correctly by Phase 27 closure memo at `docs/design/phase27_closure_memo.md:25-29`).
- **Impact**: Does NOT modify any β-eval verdict (the actual β-eval merges are findable by phase label; eval_report.md + script + tests are committed at the correct merge SHAs). The mis-citations affect downstream traceability when readers attempt to navigate from routing-memo evidence-picture rows back to the supplying β-eval PR.
- **Contamination status**: Class B at the routing-memo level. Class NONE at the β-eval level.
- **Suggested action**: TARGETED_VERIFICATION at the routing-memo level — a future doc-only PR may correct the citation strings in Phase 28 closure §4 + Phase 29 post-29.0a routing review §1 (corrections: #311 → #318, #319 → #321, #327 → #328). This audit does not issue the correction.

---

## 17. Aggregate audit outcome

Per the §2.6 outcome ladder:

| Outcome | Trigger | Met? |
|---|---|---|
| STATIC_BLOCKER_FOUND | ≥1 PR has PR_STATIC_BLOCKER_FOUND (Class A) | **No** (0 Class A findings) |
| TARGETED_VERIFICATION_REQUIRED | No Class A; ≥1 PR has PR_TARGETED_VERIFICATION_REQUIRED (Class U or material B) | **Yes** (all 9 PRs are TARGETED_VERIFICATION_REQUIRED due to structural U on artifact run-provenance — §4.1 / §4.2) |
| STATIC_REVIEW_NO_BLOCKER_FOUND | No Class A; no Class U on any PR | **No** (structural U on every PR) |

### **Aggregate outcome: `TARGETED_VERIFICATION_REQUIRED`**

**Narrative** (binding):

The Phase 27–29 tabular β-eval spine (PRs #318 / #321 / #325 / #328 / #332 / #338 / #342 / #345 / #351) is **static-code clean at each PR's own merge-time snapshot**, under each PR's own merged design memo. No formal validity blocker (Class A) was identified in static-code inspection across 9 PRs × 9 dimensions. The committed code paths gate test isolation at `_q_sort_key`-style val-only selection (Dimension 2), preserve D-1 bid/ask executable PnL semantics across all PRs (Dimension 4), implement single-axis purity per each PR's declared axis change (Dimension 5), and emit verdict labels consistent with each PR's own design memo (Dimension 9).

However, the audit **cannot empirically reconfirm** these claims from committed evidence alone because, at every spine PR's merge SHA, the machine-readable sweep_results.parquet / aggregate_summary.json / val_selected_cell.json / sanity_probe.json artifacts are gitignored. The only committed numerical evidence per PR is eval_report.md (markdown), which is structurally Class U for any claim that requires cross-checking eval_report numerics against the underlying per-cell scoring outputs. The C-sb-baseline FAIL-FAST PASS claims (Phase 28 §10 reproduction at PRs #338 / #342 / #345 + Option 9c at #351), the sanity-probe HALT-gate PASS claims, and the cross-anchor drift "within tolerance" claims across the 6-anchor control chain are all Class U on run-provenance.

The 6-anchor cross-PR control chain (C-se → C-se-r7a-replica → C-a1-se-r7a-replica → C-a4-top-q-control → C-a0-arch-control → C-d1-target-control) is static-code consistent across all 6 anchors (matched scorer / fit / eval / preprocessing / target / drift-tolerance contract); cumulative drift cannot be quantified from committed evidence.

One supporting-dependency Class B finding is recorded (§16.6): citation drift in Phase 28 closure + Phase 29 post-29.0a routing memos mis-attributes 27.0b/c/e-β to incorrect PR numbers; the underlying β-evals are unaffected.

**This outcome does not invalidate any historical verdict.** No prior verdict is modified by this audit. Whether the tabular ceiling is trustworthy enough to anchor A0-broad H-D2 comparison is a routing decision deferred to the user.

**Wording binding (re-affirmed)**: the "static-code clean at each PR's own merge-time snapshot" finding above and the "no visible contract violation found in ..." findings in §16 are **static contract inspection** results. They are **NOT** empirical reconfirmation of historical execution, NOT tabular evidence reconfirmation, NOT prior verdict formal revalidation, NOT a claim that the actual historical runs followed the inspected code paths. The structural Class U on artifact run-provenance (U-1) and sanity-probe run-provenance (U-2) is preserved across all 9 PRs; the aggregate outcome `TARGETED_VERIFICATION_REQUIRED` reflects exactly this remaining unverified-run-provenance state.

---

## 18. Routing recommendations (read-only; user decides; no auto-route)

Under the `TARGETED_VERIFICATION_REQUIRED` aggregate, the user has the following routes available. The audit does **not** decide.

### 18.1 Route U-1 — Targeted artifact regeneration for a single binding PR

If the user wishes to elevate the tabular ceiling for A0-broad re-resumption above Class U:

- Pick the highest-priority binding PR (likely #338 Phase 28 §10 FAIL-FAST or #351 6th-anchor C-d1-target-control).
- Authorise a separate doc-only or code-only PR that re-runs the eval at the merge SHA (or a re-pinned reproducible snapshot) and commits the sweep_results.parquet + aggregate_summary.json + val_selected_cell.json + sanity_probe.json for **one** PR.
- Cross-check the regenerated machine-readable artifacts against the committed eval_report.md numerics.
- If cross-check PASS, the affected PR's run-provenance Class U is upgraded to NONE on the verified dimensions.

### 18.2 Route U-2 — Targeted artifact regeneration for the full spine

Same as U-1 but applied across all 9 PRs. High cost (regenerating sweep results at 9 merge SHAs); only justified if multiple downstream commitments require the full ceiling.

### 18.3 Route U-3 — Re-resume A0-broad against the existing Class-U tabular ceiling

A0-broad re-resumption (per the merged PR #355 amendment spec) proceeds without first regenerating tabular artifacts. The formal H-D2 comparator becomes C-sb-baseline-aligned (S-B multiclass head fitted on the aligned row-set), which is computed inside the β v2 run; the historic Phase 28 §10 immutable baseline is used only for FAIL-FAST on C-sb-baseline-full at the β v2 run, NOT as a formal H-D2 comparator (per PR #355 §A.4). Under this routing, the Class U findings on Phase 27–29 tabular run-provenance do not directly block A0-broad re-resumption.

### 18.4 Route U-4 — Doc-only correction of citation drift (§16.6)

Independent of any β resumption, a doc-only PR can correct the Phase 28 closure §4 + Phase 29 post-29.0a routing review §1 citation drift (#311 → #318, #319 → #321, #327 → #328). Cheap; clarifies downstream traceability.

### 18.5 No routing decision made by this audit

The audit doc records that all four routes above are available; the user decides which (if any) to authorise. **No auto-route.**

---

## 19. Phase 29.0b-β / A0-broad status (binding read-out)

- A0-broad formal β remains **halted**.
- Existing WIP branch `research/phase29-0b-beta-a0-broad-sequence-eval` (tip `9ac8fda`) remains **INVALID_FOR_FORMAL_VERDICT** on the remote.
- Existing exploratory artifacts / checkpoints remain **EXPLORATORY_ONLY**; not cited as formal evidence by this audit.
- PR #355 (Phase 29.0b-α amendment) spec is in force; rev2-α amendment PR is deferred per user instruction.
- This audit issues **no auto-route** to any β re-implementation, scope amendment, or production change.

---

## 20. Constraints honoured by this PR

- ❌ No β code modification anywhere.
- ❌ No historic re-execution / re-fit / recomputation.
- ❌ No A0-broad β resumption.
- ❌ No rev2-α amendment PR.
- ❌ No prior verdict modification (Phase 27 / Phase 28 / Phase 29.0a verdicts quoted verbatim at merge-time snapshot).
- ❌ No standalone historical verdict modification for supporting-dependency documents.
- ❌ No production change.
- ❌ No `MEMORY.md` edit inside this PR.
- ❌ No auto-route.
- ❌ No `PASS_TABULAR_EVIDENCE_RECONFIRMED` label.
- ❌ No evidence pointer to current master `0d06ad2` for historical verdicts.
- ❌ No `pr_body_at_merge` assertion (recorded as `current_pr_body_context_only` per §2.1).

---

## 21. References

### 21.1 Audited spine (in merge order)

- PR #318 — Phase 27.0b-β S-C TIME penalty eval — merge `17be66aa17c4`
- PR #321 — Phase 27.0c-β S-D calibrated EV eval — merge `0c34ebe42dd2`
- PR #325 — Phase 27.0d-β S-E regression eval — merge `999859fa6443` (1st anchor)
- PR #328 — Phase 27.0e-β S-E quantile-family trim eval — merge `0d9eca043902`
- PR #332 — Phase 27.0f-β S-E + R7-C regime eval — merge `ad673b4a1c9e` (2nd anchor; Fix A)
- PR #338 — Phase 28.0a-β A1 objective redesign eval — merge `2b6dee1ea6c6` (3rd anchor; Phase 28 §10 immutable referenced)
- PR #342 — Phase 28.0b-β A4 monetisation-aware selection eval — merge `c4abdee0d3ca` (4th anchor)
- PR #345 — Phase 28.0c-β A0-narrow tabular topology eval — merge `49c08f5e0b8a` (5th anchor)
- PR #351 — Phase 29.0a-β A2 target redesign eval — merge `abe1ed5b7f1c` (6th anchor; Option 9c per-target baseline JSON committed)

### 21.2 Inventory inputs (master `0d06ad2`)

- `docs/design/phase27_closure_memo.md`
- `docs/design/phase28_closure_memo.md`
- `docs/design/phase29_post_29_0a_routing_review.md`
- `docs/design/phase29_a0_broad_preflight_audit.md`
- `docs/design/phase29_0b_alpha_a0_broad_design_memo.md`
- Plus all kickoff / routing review / scope amendment memos for Phase 27 / 28 / 29.

### 21.3 Supporting-dependency origins

- D-1 bid/ask executable harness: `_compute_realised_barrier_pnl` + `precompute_realised_pnl_per_row` (pre-Phase 27)
- S-B raw P(TP)−P(SL) multiclass head: pre-Phase 27
- Phase 28 §10 immutable baseline numeric: introduced contemporaneously at PR #335 (Phase 28 kickoff)
- Fix A row-set isolation: introduced at PR #332 (27.0f-β)
- Option 9c framing: PR #348 (Phase 29 kickoff)
- Phase 28.0b A4 scope amendment (R1 + R4 admission): PR #340

### 21.4 Binding contracts

- PR #279 — γ closure (production behavior contract; preserved)
- Phase 22 frozen-OOS contract (preserved)
- X-v2 OOS gating (required for any future production deployment)
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair; untouched throughout Phase 27 / 28 / 29 + this audit)
- PR #355 — Phase 29.0b-α A0-broad design memo AMENDMENT (binding for any future A0-broad β re-implementation)

---

*End of `docs/design/phase27_29_tabular_eval_validity_audit.md` (audit-doc version: rev2).*
