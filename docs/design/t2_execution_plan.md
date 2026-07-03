# Phase B — T2 execution plan

- **Document class:** doc-only planning memo (Phase B of the post-remediation gate
  roadmap; executes nothing)
- **Roadmap source-of-truth:** `docs/design/post_remediation_t2_ml_step4_roadmap.md`
  (§4 Phase B, §5), merged as PR #392.
- **Predecessor gate:** Phase A — `docs/design/post_remediation_readiness_audit.md`
  (PR #393, `POST_REMEDIATION_READINESS_AUDIT_COMPLETE`).
- **Base:** master `cc92576` (post PR #393 merge)
- **Branch:** `docs/phase-b-t2-execution-plan`
- **Governing contracts:** `docs/design/foundation_t2_execution_readiness_contract.md`,
  `docs/design/gate_p1_feasibility_inspection_protocol.md` (+ Amendment 1),
  `docs/design/gate_p2_retention_destination_evaluation_memo.md`.

---

## 1. Executive conclusion

**`T2_EXECUTION_PLAN_APPROVED`**

This approves the **plan document only** — the procedure, span strategy, credential
policy, destination policy, evidence schema, and stop conditions below are sound and
ready for a human-authorised, credential-enabled Phase C1 execution. It is **not**
approval to execute T2, deposit any bytes, or access any destination. Execution of
Phase C1 requires a separate human + ChatGPT authorisation (roadmap §9).

Forbidden-label note: no part of this memo asserts `T2_ROUND_TRIP_EVIDENCE_CREATED`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY`, `PASS`, `Tier 1`, or `FORMALLY_VERIFIED`; where those tokens
appear they are listed solely as prohibited outputs.

## 2. Scope

This is **Phase B** from `docs/design/post_remediation_t2_ml_step4_roadmap.md`.

Confirmed properties of this PR:

- **doc-only** — the only file added is this plan (plus, if useful, a one-line Phase B
  status pointer in the roadmap; the roadmap is not rewritten);
- no credential access; no cloud access;
- no T2 execution; no deposit / restore / upload / download / checksum of any real
  remote object;
- no byte-admissibility review or approval;
- no new epoch adoption;
- no ML Step 4 authorisation;
- no real-data run; no model training;
- no production-readiness claim.

## 3. Preconditions (verified at authoring time, base `cc92576`)

| Precondition | State |
| --- | --- |
| PR #392 merged | Yes (`b23c718`) |
| PR #393 merged | Yes (`cc92576`, = master tip) |
| `POST_REMEDIATION_READINESS_AUDIT_COMPLETE` on master | Yes (token present in the Phase A memo) |
| `docs/design/post_remediation_t2_ml_step4_roadmap.md` on master | Yes |
| `docs/design/post_remediation_readiness_audit.md` on master | Yes |
| Working tree clean before starting | Yes |
| Protected stage24/stage25 artifacts clean before starting | Yes |

All preconditions hold; the plan is authored below. (Had any failed, this document
would not have been authored and the branch would have stopped-and-reported.)

## 4. T2 strategy decision

Three options were compared in the roadmap (§5); restated and decided here:

1. **One-span pilot only.** Lowest risk, validates the whole mechanism, but leaves
   the other two spans' retention unresolved — incomplete as a final strategy.
2. **All-span execution.** Fastest if flawless, but highest blast radius: a
   credential / bucket-policy / object-lock mistake affects all three spans at once
   (including the ~10y `3650d_BA` set), and a mid-stream failure produces a mixed
   evidence state that itself needs adjudication.
3. **Pilot-then-expand.** Validates the full process on the smallest span, then
   completes the remaining spans with a proven procedure and identical evidence
   shape, with a clean go/no-go between stages.

**Decision: `pilot-then-expand`.**
- **Pilot span:** `365d_BA`.
- **Expansion spans:** `730d_BA`, then `3650d_BA`.

Rationale (no documented contradiction with the roadmap found):
- **Lower blast radius** — the first credentialed execution in this project's history
  should not risk all spans simultaneously.
- **Validates the credential → destination → object-lock → deposit → restore →
  checksum → evidence flow on the smallest span** (`365d_BA`, 20 files), which
  exercises every mechanism the larger spans need at the lowest cost of failure.
- **Allows human review of pilot evidence before expanding** — Phase C2 is gated on a
  clean Phase C1 review, not auto-triggered.
- **Avoids all-span failure ambiguity** — a pilot failure burns one span's effort and
  is unambiguous to debug.

## 5. Candidate spans

Source: committed Gate P1 PR-B.1 first-run evidence
(`artifacts/gate_p1_pr_b/firstrun_365d_ba/`, `firstrun_730d_ba/`,
`firstrun_3650d_ba/`) and the Foundation T2 pre-deposit-stop evidence
(`artifacts/foundation_t2/t2-all-spans-20260702/`).

| Span | Gate P1 status | Local-data candidate feasibility | Retention | Execution authorised by THIS plan? |
| --- | --- | --- | --- | --- |
| `365d_BA` | `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` | Partial | `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE` — unresolved | **No** (pilot procedure defined; execution is Phase C1) |
| `730d_BA` | `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` | Partial | Unresolved | **No** (expansion procedure defined; execution is Phase C2) |
| `3650d_BA` | `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` | Partial | Unresolved | **No** (expansion procedure defined; execution is Phase C2) |

**This plan defines the procedure for all three spans but executes none of them.**
The Foundation T2 evidence on master records all spans as
`T2_EXECUTION_STOPPED_BEFORE_DEPOSIT` / `T2_CREDENTIALS_UNAVAILABLE` /
`RETENTION_PROBE_REMAINS_UNRESOLVED`, and this plan does not change that state.

## 6. Credential handling

Policy (binding on Phase C execution; consistent with
`foundation_t2_execution_readiness_contract.md`):

- Credentials are **operator-provisioned** at execution time and never originate
  from this repo or from an agent.
- Credentials are **never committed**, **never printed**, and **never captured in
  any artifact or log** (evidence is metadata-only and scrubbed before write).
- **Environment dumps are forbidden** — no `env`, no printing of process
  environment, no echoing of destination secrets.
- Logs and evidence must pass the fail-closed cleanliness scanner
  (`scripts/foundation_t2/scrub.py` lineage) before any commit.
- If credential availability is uncertain at execution time, **Phase C must stop
  before deposit** and record the stop honestly (never fake success).
- The executing agent/operator **must not invent credentials or fabricate
  destination access**; absence of a real credential is a stop condition, not a
  thing to work around.

Credential stop conditions:
- credential missing;
- credential scope ambiguous (cannot confirm write+read to the intended
  destination without exposing secrets);
- a credential or secret accidentally appears in any output or evidence draft;
- the destination cannot be verified without exposing secrets.

## 7. Destination and alias policy

- **Destination alias:** `T2_PRIMARY_R2` (logical alias only; the same alias used in
  the committed T2 manifest).
- **Expected destination type:** Cloudflare R2, per prior planning
  (`gate_p2_retention_destination_evaluation_memo.md`, Tier 1 default = D3 R2 + D7
  backup + D6 IPFS CID sidecar). The Gate P2 §7 recommendation is explicitly
  **not pre-approved**; this Phase B document does not approve or verify the
  destination.
- **This plan alone does not consider the destination verified.** Resolution of the
  alias to a real bucket, and confirmation of write/read/list permissions, happen in
  Phase C under operator credentials — not here.
- **Object-lock / retention requirement:** the destination must enforce
  object-lock / immutability appropriate to a retention probe. **This cannot be
  proven by docs/tooling alone; Phase C must verify object-lock/retention
  semantics against the live destination or fail closed** (a destination without
  observable object-lock is a stop condition).
- **Bucket / object-prefix convention (proposed, deterministic):**
  `t2/<epoch-or-run-id>/<span_id>/<logical_file_id>` — e.g.
  `t2/t2-pilot-365d-<run>/365d_BA/candles_EUR_USD_M1_365d_BA.jsonl`. Keys are
  deterministic functions of (run id, span id, basename) so a restore can be located
  without a side channel. No destination approval is implied by naming a convention.

## 8. T2 round-trip procedure (Phase C; defined, not executed)

For **each span in scope for the given Phase C stage**, the intended procedure is:

1. resolve the local candidate bytes for the span (by inventoried basename);
2. verify the local inventory reference via the F-5 provenance guard
   (`scripts/provenance_guard.py`) — the file must be the inventoried span, and the
   procedure must not overwrite it;
3. read the expected SHA-256 / size from committed PR-B.1 inventory metadata (no
   re-fetch; no raw-row read beyond what checksum streaming requires);
4. deposit to the destination under the deterministic key/prefix (§7);
5. observe deposit metadata (object present, size, object-lock/retention attributes);
6. restore/download to an **isolated temp location** (never over the local candidate
   bytes; never under `data/` or `artifacts/`);
7. recompute SHA-256 of the restored bytes;
8. compare restored SHA-256 + size to the expected inventory values;
9. produce **metadata-only** evidence (schema §9);
10. scrub the evidence for secrets / credentials / personal local paths (fail-closed
    scanner) before any commit;
11. confirm **no raw data** (candle rows, previews) is committed anywhere.

- **Pilot (Phase C1):** run **only** `365d_BA`.
- **Expansion (Phase C2):** run `730d_BA`, then `3650d_BA`, **only after** Phase C1
  evidence has been reviewed clean by a human.

## 9. Evidence schema (metadata-only, per span)

Phase C must emit, per span, at minimum:

- execution timestamp (UTC);
- operator / machine identifier **policy** — recorded only in scrubbed/aliased form,
  never a personal absolute path or username;
- code SHA (executing revision);
- plan document path / SHA (this file);
- span ID;
- local logical path **alias** (basename / logical_file_id, not a personal absolute
  path);
- expected size;
- expected SHA-256;
- deposit status;
- destination alias (`T2_PRIMARY_R2`);
- object key / prefix;
- object-lock / retention observation;
- restore status;
- restored size;
- restored SHA-256;
- checksum comparison result (match / mismatch);
- cleanliness / scrub report;
- non-authorisation statements (no byte-admissibility, no epoch, no Step 4, no
  production readiness).

Evidence must **not** include: raw data rows; credentials; secret values; personal
local paths; unredacted environment dumps.

## 10. Stop conditions (Phase C)

Phase C must stop (fail closed, report honestly, do not proceed) if any of:

- credentials unavailable;
- credential scope ambiguous;
- destination alias cannot be resolved;
- object-lock / retention cannot be observed;
- deposit fails;
- restore fails;
- checksum mismatch (restored vs expected inventory);
- expected inventory missing;
- local candidate bytes ambiguous (basename collision, mixed price mode, overlapping
  span definition);
- evidence would contain secrets or raw data;
- protected stage24/stage25 artifacts become dirty;
- `data/` or raw `artifacts/` would be committed;
- any step attempts to claim byte-admissibility, new epoch adoption, ML Step 4, or
  production readiness.

## 11. Phase C PR split

- **Phase C1 — T2 one-span pilot `365d_BA`:** credential-enabled evidence PR; runs the
  §8 procedure for `365d_BA` only; emits §9 evidence; must stop-and-report on any §10
  condition.
- **Phase C2 — T2 expansion `730d_BA` + `3650d_BA`:** credential-enabled evidence PR;
  runs the §8 procedure for the two larger spans.

**Phase C2 must not begin until Phase C1 evidence has been reviewed clean by a human.**
The two stages are separate PRs; C1 evidence review is a gate input to C2, not an
auto-trigger.

## 12. Non-authorisation statements

- This plan does **not** execute T2.
- This plan does **not** approve byte-admissibility.
- This plan does **not** adopt a new epoch.
- This plan does **not** authorise ML Step 4.
- This plan does **not** authorise a real-data run.
- This plan does **not** train a model.
- This plan does **not** generate real-data labels/features.
- This plan does **not** compute or claim new Sharpe/PnL/DD/win-rate/expectancy.
- This plan does **not** approve production readiness.
- This plan does **not** rehabilitate historical Phase 9.X numerics.
- This plan does **not** promote or demote Phase 9.16 (it remains Tier 2
  `VALID_OPERATIONAL_BASELINE`, fenced comparator with audit caveats).
- This plan does **not** start Phase C.

## 13. Recommended next decision point

- **Next PR:** Phase C1 — T2 one-span pilot `365d_BA`.
- **Type:** credential-enabled evidence PR (first non-doc, non-synthetic execution in
  this remediation sequence).
- **Requires human + ChatGPT approval before execution;** must **not** begin
  automatically after this Phase B PR merges.
- **Preconditions to state at C1 kickoff:** operator credentials provisioned securely;
  destination alias resolvable; object-lock/retention observable; local `365d_BA`
  candidate bytes present and inventory-verified.

Nothing must be fixed before Phase C1 beyond operator credential provisioning (an
external, human-side action). The plan itself is complete and approved as a document.
