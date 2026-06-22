# Foundation T2 — retention destination selection / deposit planning (Doc-Only)

**Status:** DESIGN/PLANNING-ONLY routing-decision memo. **No retention is
implemented, no data is uploaded, no raw data is read, no cloud storage is
configured, no bucket is created, no artifact is generated, no round-trip
verification is performed, no production state is changed.**
**Scope key:** Roadmap §5.3 Foundation Track stage **T2** — Gate P2 retention
deposit + round-trip verification — *planning layer only*. Routing decision
over the candidate set D1–D10 defined in
`docs/design/gate_p2_retention_destination_evaluation_memo.md` (PR #366).
**Date authored:** 2026-06-23.
**Branch:** `docs/t2-retention-destination-planning`.
**Base:** master `7b130f7` (post PR #377 merge).

---

## 0. Binding constraints

This memo:

- makes a **routing decision** over the existing D1–D10 candidate set (i.e.
  proposes which candidate(s) to carry into T2 *execution*), grounded in
  `gate_p2_retention_destination_evaluation_memo.md` (PR #366) and the current
  roadmap §5.3,
- does **not** implement retention,
- does **not** upload or transfer any data,
- does **not** read raw data (no `data/` access, no JSONL/parquet read),
- does **not** configure cloud storage,
- does **not** create buckets / releases / accounts / object-lock settings,
- does **not** generate artifacts (no file under `artifacts/`),
- does **not** perform round-trip verification (no download → SHA-256 →
  compare),
- does **not** access broker / quote feed / credentials / env-vars,
- does **not** execute any model, experiment, backtest, or recompute any
  metric,
- does **not** modify source code, scripts, tests, config, `.gitignore`,
  `MEMORY.md`, or any prior verdict memo,
- does **not** modify the PR #361 §7 admissibility criteria,
- does **not** modify the PR #366 evaluation framework or its tier ordering,
- does **not** pre-approve any destination at the byte-admissibility level
  (PR #361 §7 "not pre-approved" binding remains intact — see §5 below),
- does **not** authorise T2 *execution* (deposit / round-trip), T3, T4,
  new-epoch adoption, any Research Track A–G, any P1/P2/P3 implementation,
  or any production change.

A routing decision at the **planning layer** selects *which candidate to
verify under T2 execution*. It is **not** the §7 byte-admissibility approval,
which can only be granted after T2 execution performs a real deposit and a
passing round-trip under explicit user authorisation.

---

## 1. Purpose / scope / non-scope

### 1.1 Purpose

To convert the PR #366 evaluation framework (which scored D1–D10 against the
PR #361 §7 admissibility criteria but **selected nothing**) into a concrete
**planning-layer routing decision of record** for Foundation stage T2:

- which destination plan is proposed to carry into T2 execution,
- in what sequence the T2 execution steps would run (deposit → immutability →
  round-trip → runbook → record),
- which open questions from PR #366 §11 must be resolved by the user **before**
  T2 execution can be authorised.

The memo gives the eventual T2-execution PR a single, reviewer-ready proposed
destination plan rather than re-opening the D1–D10 comparison.

### 1.2 Scope

- Foundation stage-numbering clarification (§2).
- Restatement of the PR #361 §7 "not pre-approved" binding and how a
  planning-layer routing decision coexists with it (§5).
- A routing decision over D1–D10 with an explicit recommended plan (§6).
- The T2-execution step sequence as a **plan** (§7), drawn from roadmap §5.3
  Scope and PR #366 §8 protocol — **not executed here**.
- Pre-execution user decisions required (§8), mapped to PR #366 §11 open
  questions.
- Non-authorisation bindings (§9).
- Status carry-forward (§10).

### 1.3 Non-scope

- No deposit, upload, transfer, account/bucket creation, object-lock
  configuration, round-trip verification, or artifact generation.
- No raw-data read.
- No selection that becomes §7-binding without T2 execution + user
  authorisation.
- No change to PR #361 §7 criteria or PR #366 framework / tier ordering.
- No authorisation of any downstream stage or track.

---

## 2. Foundation stage-numbering clarification (binding)

The correct roadmap Foundation Track mapping (roadmap §5) is:

| Stage | Definition (roadmap §5) |
| --- | --- |
| **T0** | Production keep-alive (continuous; no stage gate). |
| **T1** | Gate P1 PR-B implementation (read-only feasibility inspection). |
| **T2** | **Gate P2 retention deposit + round-trip verification** (durable byte retention of the OANDA 2026-05-31 archive). |
| **T3** | New-epoch baseline + control construction. |
| **T4** | V2-expanded sentinel verification implementation. |

Explicit clarifications mandated for this memo:

- **T2 = Gate P2 retention destination selection / deposit + round-trip
  verification.** Retention destination selection and deposit belong to **T2**,
  not T3.
- **T3 = new-epoch baseline + control construction.** T3 is **not** retention.
- **T4 = V2-expanded sentinel verification.**
- **T2 is prerequisite infrastructure, not formal verification.** A passing T2
  round-trip proves that the archive bytes are *durably retrievable per
  PR #361 §7*; it does **not** constitute formal verification of any baseline
  or model.
- **T2 alone does not authorise T3 or T4.** Per roadmap §5.3 stage gate, a
  passing T2 only means "T3 *may begin*" — it is an eligibility gate, not an
  authorisation. T3 and T4 each require independent explicit user
  authorisation.
- **T2 alone does not authorise new-epoch adoption.** Deposit ≠ epoch adoption
  (roadmap Amendment 1: "T2 deposit ≠ epoch adoption").
- **T2 alone does not authorise experiments, model execution, or production
  changes.**

This memo is a **planning artefact for T2** only. It does not itself execute
T2, and it does not advance the Foundation Track past its current state.

---

## 3. Inputs this routing decision is grounded in

- `docs/design/gate_p2_retention_destination_evaluation_memo.md` (PR #366):
  the D1–D10 candidate set, the C1/C2/C3 admissibility scoring, the OF1–OF7
  operational factors, the §6 comparison matrix, the §7 recommended tier
  ordering, the §8 round-trip protocol design, the §10 risk register, and the
  §11 open questions.
- `docs/design/new_provenance_bound_dataset_epoch_design.md` (PR #361): §7
  byte-admissibility criteria and the "not pre-approved" binding.
- `docs/design/research_development_roadmap_post_audit.md` §5.3: the T2 Scope,
  Exit criteria, and Stage gate.
- The OANDA 2026-05-31 archive provenance (PR #364): 120 raw JSONL files,
  17.54 GB, with `artifacts/oanda_archive_2026-05-31/candles_manifest.json`
  holding per-file SHA-256 + size + row count + `time` boundaries.
  **This memo references the manifest's existence and role; it does not read
  the raw bytes.**

No new evidence is generated. No file is read beyond the committed design
memos cited above.

---

## 4. What PR #366 already settled vs what this memo adds

| Concern | PR #366 (evaluation) | This memo (T2 planning) |
| --- | --- | --- |
| D1–D10 admissibility scoring | scored against C1/C2/C3 + OF1–OF7 | unchanged; cited |
| Recommended tier ordering | §7 Tier 1 = {D3, D5, D1, D4}; recommended combination D3 + D7 + D6 manifest-CID | adopted as the routing-decision-of-record proposal (§6) |
| Destination selection | **explicitly none** ("not pre-approved") | a **planning-layer proposed selection**, still subordinate to the **T1 Gate P1 PR-B review** (the read-only feasibility-inspection prerequisite, *not* Gate P2 retention) + explicit T2-execution authorisation |
| Round-trip protocol | §8 design | restated as a T2-execution **plan** (§7), not executed |
| Open questions | §11 Q1–Q11 | mapped to pre-execution user decisions (§8) |

This memo does **not** re-score, re-rank, or expand the candidate set. It
selects a proposed routing **at the planning layer** and pins the
pre-execution decisions.

---

## 5. Coexistence with the PR #361 §7 "not pre-approved" binding

PR #361 §7 binds: *no specific external service is admissible until its
availability, access, and immutability semantics are verified inside the Gate
P1 / Gate P2 PR; a committed SHA-256 manifest without an accessible byte
archive is insufficient.* PR #366 re-declared this binding at its §0/§1/§7.

A planning-layer routing decision is **compatible** with that binding because
it operates at a different layer:

- **Planning-layer routing decision (this memo):** "Of the D1–D10 candidates,
  carry **D3 (R2 + object-lock) primary + D7 (offline HDD) backup + D6 (IPFS
  manifest-CID sidecar)** into T2 execution as the proposed destination plan."
  This is a *decision about what to verify*, not a *declaration that bytes are
  durably retained*.
- **§7 byte-admissibility approval (NOT granted here):** "These bytes are now
  stored in a retrievable immutable location, verified end-to-end." This
  requires a **real deposit** and a **passing round-trip** under T2 execution,
  with explicit user authorisation. **This memo performs neither.**

Therefore the routing decision in §6 is labelled
`PENDING_T1_GATE_P1_PR_B_REVIEW_AND_EXPLICIT_T2_EXECUTION_AUTHORISATION`.
Here **"T1 Gate P1 PR-B review"** means the Foundation **T1** read-only
feasibility-inspection prerequisite (Gate P1 PR-B, plan locked at PR #365) — it
is **not** Gate P2 retention, which **is** T2 itself. The label encodes the two
gating conditions: (a) the upstream T1 Gate P1 PR-B inspection records the
candidate's retention feasibility, and (b) explicit user authorisation of T2
execution. It is the decision-of-record for *planning*; it does **not**
pre-approve the destination at the §7 level, and it does **not** make the epoch
binding.

---

## 6. Routing decision (planning layer)

### 6.1 Proposed destination plan of record

Adopting the PR #366 §7 recommended combination as the T2 planning proposal:

| Role | Candidate | Why (from PR #366 §5/§7) |
| --- | --- | --- |
| **Primary** | **D3 — Cloudflare R2 + bucket object-lock** | C1/C2/C3 all SATISFIES structurally; zero egress eliminates round-trip cost concern; S3-API stability; lowest operational complexity among Tier-1 options. |
| **Backup** | **D7 — Physical HDD offline duplicate (one drive)** | Disaster-recovery leg; ~$0/month; strengthens OF4 SPOF via geographic/vendor diversity. Not primary (C3 auditor-runnable is awkward alone). |
| **Manifest sidecar** | **D6 — IPFS manifest-CID only** | CID is content-addressed (most rigorous C2 match) for the manifest itself; small content, easily re-pinned; tamper-evidence for `candles_manifest.json`. |

This mirrors PR #366 §7 "Recommended combination for current epoch" exactly;
this memo does not invent a new plan.

### 6.2 Rationale for adopting rather than re-deciding

- PR #366 already performed the criterion-by-criterion comparison; re-deriving
  it would duplicate committed work.
- The recommended combination satisfies all three §7 criteria at SATISFIES
  level, provides OF4 SPOF diversity, and minimises ongoing cost (PR #366 §7).
- D3's zero-egress property (PR #366 §5 D3 OF3) directly de-risks the T2
  round-trip step, which downloads all 120 files to recompute SHA-256.

### 6.3 Documented user-override surface

The user may, at T2-execution authorisation time, select any other Tier-1
option or combination from PR #366 §7 instead:

- **D5 (Backblaze B2 + object-lock)** — lowest storage cost; "free egress up
  to 3× stored bytes" (PR #366 §5 D5 OF3); strongest cost-sensitive Tier-1
  alternative.
- **D1 (GitHub release, free)** — only when per-release size headroom is
  clearly above the epoch total (17.54 GB raw needs multi-release sharding;
  PR #366 §5 D1 OF2); immutability-by-procedure is weaker than object-lock.
- **D4 (AWS S3 + object-lock compliance mode)** — strongest service-level
  immutability; egress cost is the trade-off vs D3 (PR #366 §5 D4 OF3).

This memo's recommendation is **D3 + D7 + D6**; the override surface is
recorded so the eventual T2-execution PR can document the user's actual choice
against a documented option set.

### 6.4 Routing decision label

`T2_PROPOSED_DESTINATION_PLAN = {primary: D3, backup: D7, manifest_sidecar: D6}`
with status
`PENDING_T1_GATE_P1_PR_B_REVIEW_AND_EXPLICIT_T2_EXECUTION_AUTHORISATION`.

The `T1_GATE_P1_PR_B_REVIEW` term in this status refers to the Foundation **T1**
Gate P1 PR-B read-only feasibility inspection (PR #365 plan); it does **not**
refer to Gate P2 retention (which is T2). The status does **not** mix Gate P1
and Gate P2: T1 Gate P1 PR-B is the upstream inspection prerequisite, and T2
(this stage) is the Gate P2 retention deposit + round-trip.

No byte is deposited. No account is created. No §7 approval is granted.

---

## 7. T2 execution step sequence (PLAN ONLY — not executed here)

Drawn from roadmap §5.3 Scope and PR #366 §8 round-trip protocol. Each step
below belongs to the **T2-execution PR** (separately authorised); **none is
performed by this memo**:

1. **Destination setup** *(execution)* — create the R2 account/bucket, enable
   object-lock (compliance/governance mode TBD per PR #366 §5 D3 C2), set
   retention horizon (≥ 5 years recommended per PR #366 §11.Q4). *Not done
   here.*
2. **Deposit** *(execution)* — transfer the 120 OANDA 2026-05-31 raw JSONL
   files (17.54 GB) to the R2 bucket under a documented key prefix
   (e.g. `epochs/<manifest_id>/raw/...` per PR #366 §11.Q7). *Not done here.*
3. **Immutability activation** *(execution)* — confirm object-lock is active
   on every deposited object. *Not done here.*
4. **Round-trip verification** *(execution)* — download all files →
   recompute streaming SHA-256 (8 MB block recipe per PR #365 §6 / PR #366
   §8) → assert per-file equality against `candles_manifest.json`; size +
   row-count + `time`-boundary spot check on a deterministically-sampled
   subset. *Not done here.*
5. **Backup leg** *(execution)* — repeat deposit + round-trip for D7 (offline
   HDD). *Not done here.*
6. **Manifest-CID sidecar** *(execution)* — pin `candles_manifest.json` to
   IPFS, obtain the CID, and commit a small `candles_manifest_cid.txt`
   (PR #366 §11.Q6) in a follow-up doc PR. *Not done here.*
7. **Report** *(execution)* — emit
   `artifacts/gate_p2_verification/<verification_id>/gate_p2_retention_verification_report.json`
   with per-file pass/fail. *Not done here.*
8. **Runbook** *(execution / docs)* — commit the restoration procedure under
   `docs/runbook/` per epoch (PR #366 §11.Q8). *Not done here.*

**T2 exit criteria (roadmap §5.3), restated for reference only:**

- round-trip report shows 100% per-file SHA-256 match,
- restoration procedure committed under `docs/runbook/`,
- immutability mode verified active (object-lock horizon ≥ 5 years
  recommended).

Meeting these is the function of the **T2-execution PR**, not this planning
memo.

---

## 8. Pre-execution user decisions required (mapped to PR #366 §11)

Before a T2-execution PR can be authorised, the user must resolve:

| Decision | PR #366 ref | This memo's proposal |
| --- | --- | --- |
| Tier-1 destination for the epoch | §11.Q2 | **D3 (R2 + object-lock)** |
| D10 combination vs single primary | §11.Q3 | **Full D3 + D7 + D6** (override to single primary permitted) |
| Object-lock retention horizon | §11.Q4 | **≥ 5 years** from deposit |
| Egress budget (verifications + auditor restorations/yr) | §11.Q5 | **1 verification + 0–1 auditor restorations/yr** (D3 zero-egress makes this near-free) |
| Manifest-CID sidecar path | §11.Q6 | `artifacts/oanda_archive_2026-05-31/candles_manifest_cid.txt` |
| Labels/split-manifest destination | §11.Q7 | same destination, separate key prefix |
| Restoration procedure location | §11.Q8 | standalone file under `docs/runbook/` per epoch |
| Deposit vs auditor-read role separation | §11.Q10 | **two roles**, object-lock-strict permissions |
| Candidate-set completeness | §11.Q1 | accept PR #366 set as starting point; user may nominate more |

These are **decisions**, not actions. This memo records the proposals; the
user grants or overrides them when authorising T2 execution.

---

## 9. Non-authorisation bindings (explicit)

This memo authorises **nothing executable**. Specifically:

- **T2 execution** (deposit / round-trip / account / bucket / object-lock):
  NOT AUTHORISED. Requires a separate explicit instruction.
- **T3** (new-epoch baseline + control construction): NOT AUTHORISED. A
  passing T2 would make T3 *eligible to begin*, not authorised.
- **T4** (V2-expanded sentinel verification): NOT AUTHORISED.
- **New-epoch adoption:** NOT AUTHORISED. Deposit ≠ epoch adoption.
- **Experiments / model execution / backtests / metric recomputation:** NOT
  AUTHORISED.
- **Research Tracks A / B / C / D / E / F / G:** NOT AUTHORISED.
- **P1 / P2 / P3 implementation:** NOT AUTHORISED. (P2 live spread
  snapshotting remains `DESIGNED_NOT_IMPLEMENTED`; P1 remains
  `BLOCKED_ON_P2_OBSERVATION`.)
- **Production change:** NOT AUTHORISED.
- **PR #361 §7 byte-admissibility approval:** NOT GRANTED. "Not pre-approved"
  binding intact.
- **Phase 9.16 v9 20p baseline:** unchanged — Tier 2
  `VALID_OPERATIONAL_BASELINE`, neither promoted nor demoted.
- **A0-broad β halt / A0-narrow / A2-narrow FALSIFIED bindings:** unchanged.
- **Phase 27 / 28 / 29.0a / 9.10..9.X-O verdicts:** unchanged.

---

## 10. Status carry-forward

- **Foundation T0:** continuous; unchanged.
- **Foundation T1 (Gate P1 PR-B):** plan locked at PR #365; PR-B.0/B.1/B.2
  await independent authorisation; unchanged by this memo.
- **Foundation T2:** evaluation framework locked at PR #366; **destination
  plan now proposed at the planning layer by this memo**
  (`T2_PROPOSED_DESTINATION_PLAN = {D3, D7, D6}`,
  `PENDING_T1_GATE_P1_PR_B_REVIEW_AND_EXPLICIT_T2_EXECUTION_AUTHORISATION`);
  **deposit not begun; round-trip not performed; §7 not pre-approved.**
- **Foundation T3 / T4:** designed (PR #361) / specified (roadmap §5.4/§5.5);
  construction not begun; unchanged.
- **§11B framework status:** `DESIGNED_NOT_OPERATIONALISED_ON_CANDIDATES`
  broadly; first concrete application landed at PR #377; unchanged by this
  memo.
- **P1 / P2 / P3:** unchanged.
- **Research Tracks A / B / C / D / E / F / G:** unchanged.
- **Routing authority granted by this PR:** none executable; planning-layer
  destination proposal only.

End of planning memo.
