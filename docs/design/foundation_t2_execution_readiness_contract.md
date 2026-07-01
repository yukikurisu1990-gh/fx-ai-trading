# Foundation T2 — Execution Readiness / Constraint Contract (Doc-Only)

**Status:** `T2_READINESS_CONTRACT_ONLY` — doc-only. **This PR does not execute
T2.** It creates no bucket, uploads/downloads/restores nothing, performs no
object-lock or round-trip verification, uses no credentials/env-vars, and
accesses no cloud/network. It defines the authorisation boundary, readiness
checklist, credential/cloud constraints, evidence requirements, round-trip
criteria, and stop conditions for a **future, separately authorised** T2
execution PR.
**Scope key:** Foundation Track stage **T2** (roadmap §5.3), building on the
planning-layer routing memo `docs/design/t2_retention_destination_selection_planning_memo.md`
(PR #378), the Gate P2 retention evaluation `gate_p2_retention_destination_evaluation_memo.md`
(PR #366), and PR #361 §7 byte-admissibility criteria.
**Base:** master `4f1f14d` (post PR #385).
**Branch:** `docs/foundation-t2-execution-readiness-contract`.

---

## 0. Binding constraints (this PR)

This memo is a **contract for future work**. It authorises nothing executable.
It does not: create/configure any cloud bucket or account; access
credentials / env-var values / secrets; access network or cloud storage;
upload / deposit / download / restore any bytes; perform object-lock or
round-trip verification; approve byte-admissibility; construct or adopt a new
epoch; read raw data / archives / candle / quote / JSONL / parquet / CSV; run
any model / backtest / sweep / replay / feature / label / metric; change
production code or routing; integrate any LLM. It commits no `artifacts/`,
`data/`, `.gitignore`, `MEMORY.md`, or prior-verdict-memo change.

Controlled status of this PR: `T2_EXECUTION_NOT_AUTHORISED`,
`CREDENTIALS_NOT_ACCESSED_IN_THIS_PR`, `CLOUD_NOT_ACCESSED_IN_THIS_PR`,
`NETWORK_NOT_ACCESSED_IN_THIS_PR`, `NO_ARTIFACTS_COMMITTED`, `NO_DATA_COMMITTED`.

---

## 1. Current state

- **Master baseline:** `4f1f14d` (after PR #385).
- **Gate P1 read-only surface is complete:** PR-B.0 (guarded launcher /
  infrastructure), PR-B.1 (raw inventory / coverage / retention feasibility),
  PR-B.2 (static dependency inventory / static pipeline feasibility).
- **PR-B.1 candidate-span evidence complete** for `365d_BA`, `730d_BA`,
  `3650d_BA`; **all three** at `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`.
- **All three spans still require** `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`.
- **PR-B.2 outcome:** `GATE_P1_READONLY_SURFACE_STATICALLY_OBSERVED_RETENTION_PROBE_REQUIRED`.
- **ML uplift side complete through synthetic dry-run:** Step 1 contract
  (`ml_accuracy_uplift_experiment_contract.md`), Step 2 harness scaffolding
  (`scripts/ml_uplift_harness/`), Step 3 synthetic dry-run
  (`tests/fixtures/ml_uplift_harness/synthetic_reports/`).
- **No real ML experiment is authorised.** `ML_STEP4_NOT_AUTHORISED`.
- **T2 execution is not authorised. Byte-admissibility is not approved.
  New-epoch adoption is not authorised.** Phase 9.16 v9 20p remains Tier 2
  `VALID_OPERATIONAL_BASELINE`.

---

## 2. T2 purpose

T2 is the Foundation **Gate P2 retention destination selection / deposit +
round-trip verification** stage. It is:

- the **first non-read-only** Foundation step (it touches credentials / cloud /
  real bytes, unlike PR-B.0/B.1/B.2 which are read-only / static),
- a **prerequisite for byte-admissibility** (PR #361 §7: an epoch cannot become
  binding until the exact accepted raw bytes + generated labels bytes are
  stored in a retrievable immutable location, verified end-to-end),
- a **prerequisite before any real ML experiment on a durable epoch** (ML
  uplift Step 4).

T2 explicitly does **NOT**, by itself:

- approve byte-admissibility (`BYTE_ADMISSIBILITY_NOT_APPROVED`),
- construct or adopt a new epoch (`NEW_EPOCH_NOT_AUTHORISED`),
- authorise ML uplift Step 4 (`ML_STEP4_NOT_AUTHORISED`),
- authorise production routing (`PRODUCTION_CHANGE_NOT_AUTHORISED`),
- prove profitability or produce any trading metric.

A successful T2 execution establishes only that **the deposited bytes are
durably retrievable and round-trip-verifiable**. Every downstream step remains
separately gated.

---

## 3. Proposed destination status (planning-layer only)

Referenced from PR #378 / PR #366 as **planning-layer only** —
`T2_DESTINATION_PLAN_REMAINS_PLANNING_LAYER`. No destination has been created,
configured, tested, selected as final, or verified.

- **Primary proposed destination:** Cloudflare R2 with object-lock-style
  retention — **if later authorised and technically confirmed**.
- **Backup proposed destination:** offline HDD copy — **if later authorised**.
- **Manifest sidecar / external checksum registry concept:** IPFS manifest-CID
  (or equivalent content-addressed reference) — **if later authorised**.

Controlled statuses (all hold now): `T2_DESTINATION_PLAN_REMAINS_PLANNING_LAYER`,
`DESTINATION_NOT_VERIFIED`, `OBJECT_LOCK_NOT_VERIFIED`, `ROUND_TRIP_NOT_VERIFIED`.
Selection among / configuration of destinations is deferred to the future T2
execution PR under explicit user authorisation; PR #361 §7 "not pre-approved"
binding remains intact.

---

## 4. Future T2 execution boundary

A future T2 execution PR **may do the following ONLY after explicit user
authorisation** (each still subject to the safety rules in §5-§8):

- inspect the intended candidate-span metadata from committed PR-B.1 evidence
  (read-only, e.g. `artifacts/gate_p1_pr_b/firstrun_<span>_ba/`);
- prepare a deposit manifest (file logical IDs, sizes, checksums to be
  computed);
- compute cryptographic checksums over the approved files, if authorised;
- upload / deposit the approved bytes to the approved destination, if
  authorised;
- verify remote object metadata (size / checksum / retention mode), if
  authorised;
- download / restore to a safe temporary location (never the repo), if
  authorised;
- compare checksum / size / manifest against the original, if authorised;
- write **metadata-only** evidence to `artifacts/foundation_t2/` (or another
  explicitly approved path), if authorised.

Even in a future authorised T2, the following remain **forbidden unless
separately authorised**: model training, model inference, backtest, sweep,
replay, feature generation, label generation, trading metrics, production
changes, ML uplift Step 4, live / paper trading, LLM integration, new-epoch
adoption, and byte-admissibility approval.

---

## 5. Credential and secret handling (future T2)

Strict, non-negotiable rules for the future T2 execution PR:

- **Credentials must never be committed.**
- **Env-var values must never be printed** or written to any report.
- **Secrets must never appear in reports** (tokens, signed URLs, keys).
- **Local absolute paths must never appear in committed reports**
  (machine-independent references only, per the PR-B.1 / ML-harness precedent).
- **Bucket / account IDs** should be **redacted or represented by stable
  non-secret aliases** (e.g. `t2_primary_destination`) unless a specific ID is
  explicitly approved as non-secret.
- **Logs must be scrubbed** before any commit.
- **Any secret exposure is a blocker** requiring immediate stop / report (§8).

Future status labels: `CREDENTIALS_NOT_ACCESSED_IN_THIS_PR`,
`SECRETS_MUST_NOT_BE_COMMITTED`, `ENV_VALUES_MUST_NOT_BE_REPORTED`,
`LOCAL_PATHS_MUST_NOT_BE_COMMITTED`.

---

## 6. Evidence rules for future T2 (metadata-only)

Future committed T2 evidence **may include**:

- manifest ID;
- file logical IDs;
- byte sizes;
- cryptographic checksums (e.g. SHA-256);
- deposit timestamp; restore timestamp;
- remote object logical reference (alias, not a secret URL);
- storage class / retention mode status, **if non-secret**;
- round-trip checksum match result (boolean / per-file);
- tool version;
- git SHA (execution code SHA);
- operator-provided authorisation reference.

Future committed T2 evidence **must not include**:

- raw market rows; candle / quote rows; archive contents;
- credentials; env-var values;
- personal-machine absolute paths; local usernames;
- cloud secrets; signed URLs; access tokens; full bucket secrets;
- raw logs containing sensitive data.

---

## 7. Round-trip verification criteria (future, conceptual)

The future T2 round-trip is conceptually **successful** when all of:

- a deposit manifest was created;
- the approved bytes were deposited;
- remote metadata was observed;
- object retention / object-lock state was observed where applicable;
- restore / download was performed to a safe temporary location;
- restored checksum / size match the original manifest;
- committed evidence is **metadata-only** and scrubbed;
- no raw data or secrets were committed;
- no local absolute path was committed.

Cautious statuses that hold **now** (nothing executed here):
`ROUND_TRIP_CRITERIA_DEFINED_NOT_EXECUTED`,
`RETENTION_PROBE_NOT_PERFORMED_IN_THIS_PR`, `BYTE_ADMISSIBILITY_NOT_APPROVED`.

Even a successful future round-trip does **not** emit and this contract does
**not** use: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`,
`SENTINEL_VERIFICATION_COMPLETE`, `BYTE_ADMISSIBLE`, `PRODUCTION_READY`,
`MODEL_IMPROVED`, `EXPECTANCY_IMPROVED` (see §11 forbidden-label list).

---

## 8. Stop conditions (future T2 must abort)

The future T2 execution PR must **stop and report** (not patch around) on any:

- missing explicit authorisation;
- credential ambiguity;
- bucket / account ambiguity;
- object-lock not available or not confirmable;
- inability to avoid local-path leaks in evidence;
- raw data would need to be committed;
- evidence would include secrets;
- checksum mismatch;
- restore mismatch;
- remote metadata mismatch;
- unexpected file set (deposit set ≠ approved set);
- network / cloud error with uncertain remote state;
- local dirty tracked worktree that could contaminate evidence;
- any production / model / backtest / metric code path being invoked.

---

## 9. Relationship to PR-B.1 / PR-B.2 / ML uplift Step 4

- **PR-B.1 / PR-B.2:** T2 consumes their committed metadata (read-only) to
  choose the candidate-span byte set to deposit; it does **not** change their
  outcomes. PR-B.1 spans remain `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`;
  PR-B.2 remains `GATE_P1_READONLY_SURFACE_STATICALLY_OBSERVED_RETENTION_PROBE_REQUIRED`.
- **ML uplift Step 4 remains not startable now** (`ML_STEP4_NOT_AUTHORISED`).
  Step 4 requires a separately approved durable epoch / T2 path. The synthetic
  harness (Steps 1-3) does **not** authorise any real experiment.
- **A future real run (Step 4) requires:** an approved span; an approved data
  epoch; an approved feature / label / cost / split / model contract; committed
  provenance; committed metadata-only evidence; and **no archived / untrusted
  numerics** (`INVALID_LOOKAHEAD_NUMERIC` / `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`)
  used as routing evidence.

---

## 10. Future T2 execution final-report template

A future T2 execution PR must report:

- PR URL; head SHA; base SHA;
- exact authorisation reference (operator-provided);
- destination logical alias (not a secret);
- files logically included;
- checksums; byte sizes;
- deposit status; restore status; round-trip comparison status;
- retention / object-lock observation status;
- committed evidence paths;
- scrubbed / no-secret confirmation;
- no raw data committed;
- no local absolute paths committed;
- no byte-admissibility approval unless separately authorised;
- no new-epoch adoption unless separately authorised;
- no ML run; no production change;
- stop conditions encountered, if any.

---

## 11. Controlled labels

**Introduced / used by this contract** (readiness + future-execution reporting):
`T2_READINESS_CONTRACT_ONLY`, `T2_EXECUTION_NOT_AUTHORISED`,
`T2_DESTINATION_PLAN_REMAINS_PLANNING_LAYER`, `DESTINATION_NOT_VERIFIED`,
`OBJECT_LOCK_NOT_VERIFIED`, `ROUND_TRIP_NOT_VERIFIED`,
`RETENTION_PROBE_NOT_PERFORMED_IN_THIS_PR`,
`ROUND_TRIP_CRITERIA_DEFINED_NOT_EXECUTED`, `BYTE_ADMISSIBILITY_NOT_APPROVED`,
`NEW_EPOCH_NOT_AUTHORISED`, `ML_STEP4_NOT_AUTHORISED`,
`PRODUCTION_CHANGE_NOT_AUTHORISED`, `CREDENTIALS_NOT_ACCESSED_IN_THIS_PR`,
`CLOUD_NOT_ACCESSED_IN_THIS_PR`, `NETWORK_NOT_ACCESSED_IN_THIS_PR`,
`NO_ARTIFACTS_COMMITTED`, `NO_DATA_COMMITTED`, `SECRETS_MUST_NOT_BE_COMMITTED`,
`ENV_VALUES_MUST_NOT_BE_REPORTED`, `LOCAL_PATHS_MUST_NOT_BE_COMMITTED`.

**Forbidden labels** — must never be emitted by this contract or a future T2
execution report (listed here only to prohibit them): `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `SENTINEL_VERIFICATION_COMPLETE`,
`FEASIBLE_FOR_CONSTRUCTION`, `BYTE_ADMISSIBLE`, `PRODUCTION_READY`,
`MODEL_IMPROVED`, `EXPECTANCY_IMPROVED`.

---

## 12. Status carry-forward

- **T2:** execution not authorised; destination plan planning-layer only;
  `T2_PROPOSED_DESTINATION_PLAN` (PR #378) unchanged.
- **PR-B.1 span outcomes:** unchanged (`LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`,
  retention `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`).
- **PR-B.2 outcome:** unchanged
  (`GATE_P1_READONLY_SURFACE_STATICALLY_OBSERVED_RETENTION_PROBE_REQUIRED`).
- **ML uplift Steps 1/2/3:** synthetic-only; unchanged.
- **Byte-admissibility / new-epoch adoption / ML Step 4:** not authorised.
- **Phase 9.16 v9 20p:** Tier 2 `VALID_OPERATIONAL_BASELINE`, neither promoted
  nor demoted.
- **A0-broad β halt / A0-narrow / A2-narrow FALSIFIED bindings / Phase 27-29 /
  9.10..9.X-O verdicts:** unchanged.
- **Routing authority granted by this PR:** none.

End of contract.
