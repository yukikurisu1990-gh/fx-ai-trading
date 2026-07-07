# M15 future prompt templates — copy-paste library for Claude/Opus/Fable sessions

- **Document class:** doc-only prompt library. Companion to
  `docs/governance/m15_audit_playbook.md` (the playbook is authoritative; if a
  template and the playbook disagree, the playbook + the stricter reading win).
- **Status:** `M15_AUDIT_PLAYBOOK_AND_CLAUDE_RULES_RECORDED`
- No template below authorises real data, validation, holdout, training, or
  execution. Templates 4–6 are usable ONLY after their gate-specific human +
  ChatGPT approval exists; pasting a template is never itself an approval.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`,
`PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`, `H1_AUTHORISED`,
`H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`,
`MEETS`, `ROBUST`, `DEPLOYABLE` appear here only inside prohibition lists and
registered status vocabularies.

---

## COMMON BLOCKS (paste into EVERY template instantiation)

**[STATE HEADER — fill in]**
```
Current master tip: <MASTER_SHA>
Gate chain state: <one line per completed gate, from the playbook §1>
Statuses in force: <required + carried + always-binding>
Forward epoch: FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS (unless a later ruling changed it — cite it)
```

**[COMMON FORBIDDEN — paste verbatim]**
```
Do not read real raw data. Do not derive real M15 data. Do not compute real
checksums/spreads/labels on real data. Do not compute validation metrics. Do
not compute holdout metrics. Do not train models. Do not generate predictions.
Do not execute. Do not generate execution evidence. Do not write model
binaries. Do not adopt a forward epoch. Do not claim byte-admissibility. Do
not claim production readiness. Do not use 730d_BA or 3650d_BA. Do not start
Phase C2 or H2/H3. Forbidden final statuses (prohibition-list-only): PASS,
Tier 1, FORMALLY_VERIFIED, PRODUCTION_READY, READY_FOR_LIVE, M15_AUTHORISED,
H1_AUTHORISED, H2_STARTED, PHASE_C2_STARTED, NEW_EPOCH_ADOPTED,
BYTE_ADMISSIBLE, MEETS, ROBUST, DEPLOYABLE.
```
*(Gate-specific templates below relax individual lines ONLY where the gate's
explicit approval says so — e.g. template 2 permits design-span reads.)*

**[COMMON CHECKS — run all]**
```
git diff --name-only master...HEAD
git status --porcelain
python tools/lint/run_custom_checks.py
ruff check .
ruff format --check .
pytest tests/ml_step4
pytest tests/gate_p1_pr_b
pytest tests/ml_uplift_harness
pytest tests/foundation_t2
pytest tests/m15_gate3a
```

**[COMMON REPORT TAIL — every final report ends with]**
```
- exact local test status (honest, incl. skips)
- confirmation of every COMMON FORBIDDEN line (one per line)
- confirmation prior evidence dirs + artifacts/m15_gate3a untouched
- confirmation stage24/stage25 clean
- confirmation no next experiment started
Do not merge. Stop after opening the PR and reporting.
Important process rule: if the PR head changes after reporting — even
doc-only or hygiene-only — do not merge or proceed. Stop and report the
changed head SHA for human + ChatGPT review.
```

---

## Template 1 — Source-contamination audit (incl. the F-1…F-5 re-check)

```
[STATE HEADER]
Create a doc-only source-contamination / implementation source audit PR for
<TARGET: e.g. the merged targeted-fix PR #<N> M15 machinery>.
Branch: docs/fable5-m15-<target>-source-audit(-recheck)
Base: latest master (<BASE_SHA>)
Primary document: docs/design/m15_<target>_source_audit_fable5.md
Allowed files: the primary document + a short pointer in
docs/design/post_remediation_t2_ml_step4_roadmap.md only.
[COMMON FORBIDDEN]
Audit per docs/governance/m15_audit_playbook.md §4 (full checklist: import
graph, legacy paths, real-data/derivation/validation/holdout/training/
execution/model-binary/broker routes, aggregation correctness incl.
distinct-minute eligibility + finite prices, no-overlap/dead-window boundaries,
T-1 warm-up, T-7 proofs, effective-N role handling, cost schema finiteness,
artifact/scrubber probes, refusal guards, test adequacy, non-authorisation).
Probe adversarially with synthetic literals only; confirm every finding.
Required final status (exactly one):
  M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_ACCEPTABLE_FOR_GATE3A_CONTINUATION
  M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES
  M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_REQUIRES_REWRITE
Carry all statuses in force. [COMMON CHECKS]
Final report: PR URL / head / base / CI / touched files / audit doc path /
status / per-section findings / blockers / recommendation for next gate /
[COMMON REPORT TAIL]
```

## Template 2 — Gate-3a continuation (design-span derivation; REQUIRES prior audit acceptance + explicit approval)

```
[STATE HEADER — must cite the accepted source-audit status and this gate's
explicit human + ChatGPT approval; without both, REFUSE this task]
Create the gate-3a continuation PR: design-span M15 derivation
metadata/checksums.
Branch: code/m15-gate3a-continuation-design-derivation
Base: latest master (<BASE_SHA>)
Allowed files: artifacts/m15_gate3a/* (populating the PR #431 schemas), a
derivation-run record doc, roadmap pointer. Code changes only if the approval
names them.
[COMMON FORBIDDEN] — with EXACTLY these relaxations and no others:
  MAY read committed design-span M1 data (2025-04-25..2026-02-28) via the
  audited machinery; MAY derive design-span M15 files and compute their
  checksums; MAY compute design-span cost tables ONLY if the approval says so.
Still absolutely forbidden: forward-epoch data/adoption; dead-window
(2026-03-01..2026-04-24) reads incl. warm-up; validation/holdout/metrics/
training/execution; NEW_EPOCH_ADOPTED; BYTE_ADMISSIBLE unless separately ruled.
Must produce: design M15 inventory + SHA-256 checksums (20 files, per-file
ts-bounds); byte-level no-overlap proof (all ts_max <= 2026-02-28T23:59:59Z,
zero dead-window bars); gap reports; scrub report (metadata-only, scrub-clean;
no raw rows/candles committed).
Required status: M15_GATE3A_CONTINUATION_DESIGN_DERIVATION_PROPOSED (or as the
approval names it). Forward epoch remains WAIT. [COMMON CHECKS]
Final report: PR URL / head / base / CI / artifact list + checksums summary /
no-overlap proof result / cost-table status / [COMMON REPORT TAIL]
```

## Template 3 — Gate-3a continuation audit (audit of template-2 outputs)

```
[STATE HEADER]
Create a doc-only audit PR of the gate-3a continuation outputs (PR #<N>).
Branch: docs/fable5-m15-gate3a-continuation-audit
Base: latest master (<BASE_SHA>)
Allowed files: the audit doc + roadmap pointer.
[COMMON FORBIDDEN] (reading the COMMITTED metadata artifacts is allowed; raw
data is not).
Verify: inventory completeness (20 files); checksum well-formedness; per-file
ts-bounds vs the byte-level no-overlap proof; zero dead-window bars; gap
reports plausible vs the committed M1 inventory gap profiles; derivation
identity (script SHA + config hash) recorded; byte-reproducibility claim;
scrub cleanliness; cost tables (if produced) design-span-only + p90/p95
present + pip authority; no validation/holdout/metric leakage into artifacts;
non-authorisation.
Required final status (exactly one):
  M15_GATE3A_CONTINUATION_OUTPUTS_ACCEPTABLE / _BLOCKED_PENDING_TARGETED_FIXES
  / _REQUIRES_REWRITE
[COMMON CHECKS] Final report: per-section findings + [COMMON REPORT TAIL]
```

## Template 4 — Pre-run authorisation (BEFORE any single run; decision document only)

```
[STATE HEADER]
Create a doc-only pre-run authorisation review for the family-A M15 single
run. This PR decides NOTHING itself — it assembles the checklist for the
human + ChatGPT go/no-go.
Branch: docs/m15-pre-run-authorisation-review
Base: latest master (<BASE_SHA>)
Allowed files: the review doc + roadmap pointer.
[COMMON FORBIDDEN]
Verify with citations (playbook §6): source audit + re-check accepted;
design-span derivation accepted; FORWARD EPOCH ADOPTED via a later
continuation (val >= 3mo + holdout >= 2mo + byte-level proof) — if not
adopted, the verdict MUST be blocked; cost tables fixed; effective-N
estimator fixed; T-1..T-7 satisfied (incl. ratio rule: median eligible
barrier/cost >= 3.0 on design data else BLOCKED pending ruling; warm-up W
frozen; EV payoff semantics pinned; maxDD notional 10,000 pips); no
consumed-window leakage; no legacy-evidence dependency (C-8); no
validation/holdout contamination; acceptance criteria frozen; run is exactly
once; holdout only after the validation kill gate passes.
Required final status (exactly one):
  M15_PRE_RUN_AUTHORISATION_REVIEW_READY_FOR_HUMAN_DECISION
  M15_PRE_RUN_AUTHORISATION_REVIEW_BLOCKED (with blocker list)
[COMMON CHECKS] Final report: checklist verdicts + [COMMON REPORT TAIL]
```

## Template 5 — Single-run execution (REQUIRES the explicit human + ChatGPT run approval; exactly once)

```
[STATE HEADER — must quote the explicit run approval; without it, REFUSE]
Execute the family-A M15 single run EXACTLY ONCE under the frozen PR #429
contract as tightened by gate 4.
Branch: run/m15-family-a-single-run
Base: latest master (<BASE_SHA>)
Allowed outputs: metadata-only scrub-clean evidence in a NEW versioned
directory; execution report doc; roadmap pointer. Implementation code must
already be merged; commit any run-recording SHA BEFORE executing.
Absolute constraints: one execution attempt; validation kill gate FIRST
(fail at all registered ev_min -> family A closes, holdout untouched, report
honestly); holdout evaluated at most once, only at the selected operating
point; no rerun; no tuning after seeing any metric; if a hard gate fails,
stop before training and write metadata-only stop evidence; if a defect is
found after execution, do NOT rerun — report and mark invalid/stopped.
[COMMON FORBIDDEN] — with EXACTLY these relaxations: MAY read the adopted
design/validation/holdout artifacts; MAY train the registered model from
scratch; MAY compute the registered validation metrics and (kill-gate
permitting) the single holdout evaluation.
Report per playbook §7 (all fields). Statuses: use only the registered run
vocabulary; always PRODUCTION_READINESS_NOT_CLAIMED. [COMMON CHECKS]
[COMMON REPORT TAIL]
```

## Template 6 — Post-run audit

```
[STATE HEADER]
Create a doc-only Fable 5 post-run audit of the single-run evidence (PR #<N>).
Branch: docs/fable5-m15-single-run-post-audit
Base: latest master (<BASE_SHA>)
Allowed files: audit doc + roadmap pointer. Read ONLY committed evidence
metadata + committed source; arithmetic consistency checks on committed values
allowed; NO raw-data recomputation.
[COMMON FORBIDDEN]
Audit per playbook §8 (full checklist: lineage, code SHA, reproducibility,
pip authority, aggregation, dead-window, warm-up, split, cost model, 2x/p90
stress + p95 diagnostic, labels, EV payoff semantics, effective-N, timeout
share incl. the >60% trigger, ratio rule, concentration, turnover, gross/net,
stress survival, Sharpe, maxDD, no rerun, no cherry-picking, no production
claim).
Required final status (exactly one):
  M15_SINGLE_RUN_EVIDENCE_VALID_DOES_NOT_MEET
  M15_SINGLE_RUN_EVIDENCE_VALID_MEETS_PREREGISTERED_CRITERIA
  M15_SINGLE_RUN_EVIDENCE_INVALID
  M15_SINGLE_RUN_EVIDENCE_INSUFFICIENT_SAMPLE
Binding: even the MEETS status is NOT production readiness and requires a
separate human + ChatGPT ruling (disjoint replication before stronger claims).
[COMMON CHECKS] Final report: per-section findings + [COMMON REPORT TAIL]
```

## Template 7 — Merge approval (for the human to issue; Claude executes read-only checks then merges)

```
Human approval granted: merge PR #<N>.
Reviewed head SHA: <HEAD_SHA> ; Base: <BASE_SHA>.
This merge accepts: <the PR's registered status + key conclusions, itemised>.
This merge does not approve: <the standard non-approval list for the gate>.
Before merging, perform final read-only pre-merge checks per playbook §9
(open, mergeable, head unchanged — else STOP and report the new SHA, do not
merge —, base expected, CI green, touched files exactly <LIST>, no unexpected
code/test/config, no raw data/secrets/evidence/binaries, prior evidence +
artifacts/m15_gate3a untouched, stage24/25 clean, working tree clean,
statuses correct, non-authorisation present).
If all checks pass, merge using the repository's normal (squash) method.
After merge, report: PR URL / merge commit SHA / final master tip / final CI /
touched files / status confirmations / the gate's confirmation list / next
gate. Stop after the merge report.
```

## Template 8 — Amendment for a changed head SHA

```
[STATE HEADER]
Amend existing PR #<N>. Do not open a new PR. Do not merge.
Reason: <the reviewer's stated reason>.
Old reviewed head: <OLD_HEAD_SHA>.
Allowed files: <exact list — typically doc-only>.
Apply exactly: <the itemised required changes>. Do not loosen any guard,
threshold, or status. Do not add capabilities.
[COMMON FORBIDDEN] [COMMON CHECKS]
Final amendment report: PR URL / OLD head / NEW head / base / CI on the new
head / touched-by-amendment files / confirmation only the requested change
was made / [COMMON REPORT TAIL]
Because the head SHA changes by design, report the NEW head SHA for human +
ChatGPT review and do not merge until it is reviewed.
```
