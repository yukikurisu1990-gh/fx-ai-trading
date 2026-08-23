# M15 gate-3a — continuation output-surface Contract Gate-decision

**Type.** Contract Gate-decision PR (policy §14.2). **Risk tier.** Amber —
doc-only, and it fixes a research contract governing protected paths.

**Completion state.**
`M15_GATE3A_CONTINUATION_OUTPUT_SURFACE_CONTRACT_RULED`

**Current status.**

- **Human + ChatGPT ruling completed.** The rulings in §2 are normative.
- **Continuation output surface contract RULED.**
- **Source implementation PENDING** — nothing in §2 is implemented. This document
  changes no source, no test and no artifact.
- **Gate-3a continuation NOT authorised.**
- **Source-audit acceptance NOT granted.** The fifth independent source-audit has
  not been started.

**Statuses carried, unchanged.** `PRODUCTION_READINESS_NOT_CLAIMED` ·
`NO_EXECUTION_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` ·
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.

`M15_GATE3A_CONTINUATION_OUTPUT_SURFACE_PENDING_HUMAN_CHATGPT_RULING` and
`CONTRACT_CHANGE_REQUIRES_HUMAN_CHATGPT_RULING` are **superseded**. They are
recorded in §8 as history and are **not** the current status.

---

## 1. The question this decision answers

**By what authority is the set of output artifacts that the gate-3a continuation
may produce defined?** §12.17 limb 1 (a "separate output directory" with no
mechanism) and the unknown-artifact-name gap were one question — two limbs of a
single absent object, a declared output surface. Both are ruled here.

---

## 2. The ruling

### 2.1 Ruling 1 — No new continuation artifact identities

The artifact identities the continuation may produce are **limited to the
existing committed identities playbook §5 already enumerates**:

| Playbook §5 output | Canonical artifact identity | Canonical filename |
| --- | --- | --- |
| design M15 inventory + checksums | `design_m15_inventory` | `design_m15_inventory.json` |
| byte-level no-overlap proof | `no_overlap_proof` | `no_overlap_proof.json` |
| cost tables, **only** if explicitly authorised in the approval | `cost_table_plan` | `cost_table_plan_or_metadata.json` |

No new artifact identity is added for the continuation. **That a current code
path can write an artifact is never a reason to promote it to authority.**

Where a new artifact type or name is genuinely required:
**`NEW_ARTIFACT_IDENTITY_REQUIRES_SEPARATE_CONTRACT_GATE_DECISION`.**

### 2.2 Ruling 2 — Dedicated continuation output root

The normative root for continuation candidate outputs is:

```
artifacts/m15_gate3a_continuation/
```

It is a **sibling** of `artifacts/m15_gate3a/`, deliberately **not** a subtree of
it. The reason is measured and structural: `path_authority.is_within` protects a
root **together with its whole subtree**, so a staging root placed inside the
committed evidence tree could never coexist with D-7's trap step of adding
`artifacts/m15_gate3a` to `_PROTECTED_PREFIXES`, and would collide with the
promotion lifecycle in §2.3.

Normative:

- A continuation candidate output may be written **only** beneath this root.
- Arbitrary output directories are forbidden.
- A caller-supplied arbitrary output directory is forbidden.
- Path traversal is forbidden.
- Direct writes by the continuation writer into any protected root are
  forbidden — `docs/`, `data/`, `models/`, the committed evidence and proof
  trees, and every other current protected tree.

### 2.3 Ruling 3 — Candidate lifecycle

A continuation output is **not authoritative evidence at the moment it is
generated**. The lifecycle is:

```
generate candidate  →  verify candidate  →  human-reviewed promotion
```

Normative:

1. A continuation execution creates new candidates **only** under the candidate
   root.
2. Candidate generation never overwrites a committed or protected artifact.
3. A candidate is **never** automatically promoted to committed evidence.
4. Promotion happens as a **human-reviewed diff / approved repository change**.
5. At promotion, schema, identity, status and provenance are **re-verified**.
6. The existence of a generated candidate is **not** gate evidence by itself.
7. In-place overwrite of a previously committed artifact is forbidden.

**Overwrite and collision:**

- A collision with an existing candidate filename **fails closed**.
- Silent overwrite is forbidden.
- Automatic replacement is forbidden.
- A mechanism that lets the **caller** decide how to avoid a version collision is
  forbidden.
- The lifecycle mechanism itself is implemented by the later Work PR, to this
  contract.

### 2.4 Ruling 4 — Single continuation routing authority

**`ALL_GATE3A_CONTINUATION_OUTPUT_WRITES_MUST_ROUTE_THROUGH_THE_APPROVED_CONTINUATION_OUTPUT_AUTHORITY`**

For continuation artifacts, the following may **not** be used to bypass that
authority: a direct call to a generic writer; an alternate writer;
`scripts/ml_step4/evidence.write_report`; generic JSON writers; generic report
writers; `open(..., "w")`; `Path.write_text` / `Path.write_bytes`; or any
equivalent filesystem sink.

**This is not an instruction to remove the repository's generic writers.** What
is forbidden is *their use as a route for writing a gate-3a continuation
artifact*. The later Work PR pins this boundary with static import and
reverse-caller tests.

### 2.5 Ruling 5 — The filename is not the permission authority

A caller does **not** acquire permission to write a continuation artifact by
choosing a filename. The normative model is:

```
caller supplies:            artifact_id
routing authority resolves: artifact_id -> canonical filename
                                        -> schema
                                        -> output class
                                        -> status authority
                                        -> provenance requirements
                                        -> continuation root
```

A design in which a caller names an arbitrary file and thereby determines the
artifact identity is forbidden. **`filename != authority`.**

### 2.6 Ruling 6 — Typed artifact registry, separated from the schema registry

The schema registry and the artifact permission/identity registry are
**separated**. `_SCHEMAS` may no longer serve simultaneously as schema registry,
committed-directory manifest and artifact permission roster.

The later Work PR implements a typed artifact authority whose logical fields are
at minimum: canonical `artifact_id` · canonical filename · schema reference ·
output class · status authority · provenance requirement · lifecycle class ·
continuation-output eligibility.

Uniqueness is required: **one `artifact_id` → one canonical continuation
identity.** Permission escalation via an alias is forbidden.

### 2.7 Ruling 7 — Canonical artifact declaration key

Only the **exact canonical key** declares artifact identity. Case folding is
**not** a permission-discovery mechanism.

`artifact` is canonical. `Artifact`, `ARTIFACT`, `ArTiFaCt`, a Unicode lookalike,
a zero-width insertion and any confusable spelling are **not** canonical
declaration keys.

The present divergence — an exact-case schema lookup beside a case-folded
scrubber lookup — is forbidden. An unknown or malformed declaration **fails
closed**.

### 2.8 Ruling 8 — Reserved filename canonicalisation

A reserved or canonical artifact filename requires an **exact match on the
canonical basename**. Forbidden: case variants · Unicode confusables ·
zero-width characters · trailing dots · trailing spaces · alternate separator
spellings · any equivalent rendered filename · namespace aliases ·
reserved-name impersonation.

FB-7 canonicalisation applies to **content**; filename identity enforcement is a
**separate boundary** and both are implemented. **That two names render
identically is never a reason to admit one.**

### 2.9 Unknown artifact behaviour

An unknown artifact identity handed to the continuation routing authority
**fails closed**. A new identity may **not** be inferred from a filename, from
the presence of a schema, from a writable directory, or from a free-text
declaration.

**`UNKNOWN_CONTINUATION_ARTIFACTS_FAIL_CLOSED_TYPED_REGISTRY_REQUIRED`**

A genuinely new artifact requires its own Contract Gate-decision.

### 2.10 Committed roster ≠ continuation eligibility

Membership of the committed artifact roster and eligibility to be *generated by
the continuation* are **different properties**. The typed registry carries an
explicit `continuation_output_eligible` authority, and **only** playbook §5's
outputs are eligible.

For every other committed artifact: being readable or committed does **not** make
it generable by the continuation writer, and being reserved does **not** make it
overwritable by the continuation writer. `effective_n_estimator_spec` and both
forward artifacts remain **never written**, per D-7.

### 2.11 `cost_table_plan.json`

Not adopted as a ninth committed or continuation artifact. That the current code
can write it is not authority.

The mapping to an existing identity **is** available from committed authority and
therefore needs no invention: `artifacts/m15_gate3a/cost_table_plan_or_metadata.json`
declares `"artifact": "cost_table_plan"`, so the committed evidence states both
halves — canonical identity `cost_table_plan`, canonical filename
`cost_table_plan_or_metadata.json`. **The filename `cost_table_plan.json` is
refused**; the identity `cost_table_plan` resolves to the committed filename.

No roster addition is made by any Work PR. Had the mapping not been derivable, the
disposition would have been `REQUIRES_SEPARATE_ARTIFACT_CONTRACT_DECISION`.

### 2.12 D-7 status authority

**`CONTINUATION_OUTPUT_REQUIRES_EXPLICIT_COMMITTED_STATUS_AUTHORITY`**

Every continuation-output-eligible artifact requires a status authority. Where an
artifact currently has no status operand: an implicit PASS is forbidden; treating
it as continuation-authoritative while its status is absent is forbidden; and
substituting a generic global status is forbidden.

Measured, and directly engaged by this rule: `no_overlap_proof` and
`cost_table_plan_or_metadata` — **two of the three eligible outputs** — carry no
`status`, and their schemas presently *forbid* the key. `scrub_report` is in the
same position.

The later Work PR implements the status operand **from existing contract**. Where
an artifact's status semantics are **not** uniquely derivable from committed
authority, that artifact is
**`STATUS_AUTHORITY_REQUIRES_CONTRACT_DECISION`** and fails closed. No Work PR
invents new research semantics.

### 2.13 Provenance

A continuation output requires a committed provenance binding, at minimum to:
design epoch identity · artifact identity · generating contract/version ·
the relevant upstream approved authority · candidate lifecycle state.

A correct path, filename and schema do **not** by themselves establish authority.
Missing, malformed or unapproved provenance **fails closed**.

---

## 3. Dispositions fixed by this decision

| Item | Disposition |
| --- | --- |
| **§12.17 limb 1** | **RULED** — by the dedicated continuation root (§2.2), typed artifact routing (§2.4, §2.6), canonical artifact identity (§2.5, §2.7, §2.8) and the candidate lifecycle (§2.3) |
| **§12.17 limb 2** | already **FIXED** — overwrite refusal, implemented and proven |
| **§12.17 limb 3** | already **FIXED** — protected-tree refusal, implemented and proven |
| **§12.17 overall** | **`SECTION_12_17_RULED_AND_IMPLEMENTATION_REQUIRED`** |
| **Unknown artifact names** | was `REQUIRES_CONTRACT_OR_SCHEMA_DECISION`; **resolved** → `UNKNOWN_CONTINUATION_ARTIFACTS_FAIL_CLOSED_TYPED_REGISTRY_REQUIRED`. Source implementation is the later Work PR |
| **Routing bypass** | a **first-class contract requirement** (§2.4), not a fix-note footnote |
| **Derivation manifest divergence** | **`TARGETED_IMPLEMENTATION_FIX_REQUIRED`** — see §5.3 |
| **FR-19** | unchanged: `SEPARATE_TEST_SAFETY_WORK_PR`, out of scope |

---

## 4. The measured evidence this ruling rests on

All executed read-only at `70bf38b`, in a sandbox; nothing was written inside the
repository. Retained because the ruling's shape follows from these facts.

**4.1 The continuation needs no new artifact name.** Playbook §5 enumerates its
outputs, and all three map to committed identities (§2.1). An earlier draft of
this packet asserted the opposite; that assertion is withdrawn.

**4.2 D-7 / NR-A is closed.** The playbook's referral table still shows NR-A as
`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`, but its own preamble governs: the
column is "the historical audit finding that produced them, not an open
question". This decision completes a *successor* item D-7 created.

**4.3 The routing hole — the finding that governs the rest.**
`scripts/ml_step4/evidence.write_report`, a function in the same module
`artifacts.py` already imports two names from, is one import away and carries no
path guard and no name validation. Executed in a synthetic sandbox root: it
**overwrote a committed artifact, 2 138 → 16 bytes**, wrote into
`docs/governance`, `data` and `models`, accepted `../../escaped.json` as a
*filename*, and accepted strategy metrics. `guards.py:22-25` already disclosed
that "containment of an *unrouted* caller is not a property this module has". The
contract gap was that §12.17 was written as though one writer exists. §2.4 closes
it.

**4.4 One capital letter defeated both identity defences.** `resolve_schema` read
`payload.get("artifact")` exact-case while the key allowlist folded. `Artifact`
and `ARTIFACT` each defeated *both* `gate3a_undeclared_artifact_name` and
`gate3a_artifact_name_mismatch`, and a payload could carry two identities with one
invisible to the resolver — with `scan_gate3a` returning `[]`. §2.7 closes it.

**4.5 Reserved-name impersonation was live and wide.** Filenames received
`str.__str__` and no fold, while payload content received the full FB-7
treatment. Nine spellings rendering as one reserved name coexisted in a single
directory: leading space, Greek omicron, Cyrillic es, fullwidth, zero-width,
NBSP, `" x .json"`, double extension, `_v2`. Case variance was refused **only**
because NTFS folds `exists()`; CI is `ubuntu-latest`, where it writes. §2.8
closes it.

**4.6 Seven spellings of "declare nothing"** — absent, `""`, `"   "`, `123`,
`None`, `["x"]`, `{}` — each bought an arbitrary `*.json` filename. Measured
**identical at base `c7e477a`**: inherited, not introduced. §2.7 and §2.9 close
it.

**4.7 The accepted filename surface was nine, not eight.**
`cost_table_plan.json` has never been committed and resolved to a full declared
schema. §2.11 refuses the filename and fixes the identity mapping.

**4.8 §12.17 limb 1 had no representation at all.** `out_dir` was a free caller
argument; a path outside the repository was accepted. `write_metadata_artifact`
has **no non-test caller**, so §2.2's confinement costs nothing today.

**4.9 Directory identity is not a string.** An `out_dir` that was an NTFS
junction was accepted and the file landed at the junction's target — with
`os.path.islink()` reporting `False` — and an 8.3 short-name alias was likewise
accepted. Directory identity must therefore be compared **resolved**, and the
approved root required to be a real directory rather than a reparse point.

**4.10 `_SCHEMAS` was three authorities at once.**
`tests/m15_gate3a/test_recheck_fixes.py:898` asserts set equality between the
schema table and the on-disk contents of `artifacts/m15_gate3a`. §2.6 separates
them; the later Work PR must preserve that manifest pin deliberately rather than
relax it to a subset.

**4.11 Declaring a schema could weaken content control.**
`design_m15_inventory` permits 441 numeric leaves against the undeclared
backstop's 120 (`no_overlap_proof` 84, `scrub_report` 21). A reserved name is not
automatically the stricter route.

**4.12 Two output surfaces.** The metadata writer refuses `.jsonl`, so the 20
derived M15 data files belong to the aggregation script the derivation manifest
records as `TO_BE_CREATED_AT_GATE5`. This decision governs the **metadata
evidence** surface; the derived-data surface is not ruled here and must not be
assumed covered.

**4.13 A §12.25 collision to pre-empt at gate 4.** `proof.MeasurementRecord`
carries exactly **six** immediate integer fields against S1's cap of **five** —
measured, a flat serialisation refuses. The gate-4 record must nest; raising the
bound is forbidden by PR #448 §5.5.5.

---

## 5. Requirements on the later implementation Work PR

### 5.1 Scope

Continuation typed registry · dedicated candidate root enforcement · single
routing authority · generic-writer bypass prevention · artifact-key exactness ·
filename canonical identity · reserved-name impersonation prevention · D-7 status
authority enforcement · provenance enforcement · `_SCHEMAS` authority separation ·
§12.17 limb 1 implementation · unknown-artifact fail-closed · derivation manifest
six-field fix · regression and adversarial tests · static reverse-caller and
import tests · internal audit and mutation testing.

**FR-19 is not included.**

### 5.2 Implementation freedom, and its limit

The mechanism is free — class, enum, dataclass, immutable mapping, registry
module, router object. The **observable contract** is not: single routing
authority · typed identity · fixed candidate root · fail-closed unknown identity ·
no arbitrary filename · no alternate-writer bypass · explicit status · explicit
provenance · candidate/promotion lifecycle.

### 5.3 Derivation manifest divergence

`design_m15_derivation_manifest.json` still declares
`"missing_minute_policy": "… per-file gap report (count + max gap) …"` while
`design_m15_inventory.json` declares the six-field `minute_accounting` that PR
#444 §5 approved and PR #449 implemented. **This is not a contract choice** — it
is an implementation divergence from the current committed schema.
`TARGETED_IMPLEMENTATION_FIX_REQUIRED`: the Work PR aligns the derivation
manifest, the schema declaration and the tests to the approved six-field schema.
**No new schema semantics are invented.**

### 5.4 Observable requirements the tests must pin

1. A known eligible `artifact_id` resolves to its canonical candidate path, and
   only that path.
2. An unknown `artifact_id` is refused.
3. A caller-supplied filename cannot change the canonical identity.
4. `Artifact`, `ARTIFACT` and every non-canonical declaration key are refused.
5. A reserved-name confusable is refused.
6. A protected path is refused.
7. A traversal path is refused.
8. An alternate writer cannot produce a continuation artifact.
9. A direct overwrite is refused.
10. An existing-candidate collision is refused.
11. A missing status authority is refused.
12. Missing provenance is refused.
13. A schema mismatch is refused.
14. An `artifact_id` / filename mismatch is refused.
15. An `artifact_id` / schema mismatch is refused.
16. A non-continuation committed artifact is refused by the continuation writer.
17. A candidate is not automatically authoritative.
18. Promotion requires a reviewed repository diff.
19. `_SCHEMAS` alone cannot grant write permission.
20. The current six-field minute-accounting schema is used consistently.

Each refusal carries its own finding token and a negative control beside it, per
§13's anti-pattern rules; and the D-7 trap is discharged in the same PR — once
the candidate root is enforced, `artifacts/m15_gate3a` joins
`_PROTECTED_PREFIXES`, and playbook §5's clause naming that tree as the write
target is amended with it.

---

## 6. Changes that will still require human-reviewed contract/schema authority

A new continuation artifact identity · adding continuation eligibility · a new
output root · adding or changing status semantics · changing lifecycle semantics ·
changing the promotion rule · changing the protected or reserved surface.

An ordinary implementation refactor that changes none of these is a Work PR.

---

## 7. Sequence from here

1. This Contract Gate-decision merges on human + ChatGPT approval.
2. The continuation output-surface implementation Work PR.
3. That PR merges after review.
4. The FR-19 test-safety Work PR.
5. The **fifth independent source-audit**, in a fresh top-level session — **not
   before the contract implementation**.
6. P/V byte-reader work.
7. Concrete calendar artifact approval.
8. Only then, an authorised gate-3a continuation.

**This ruling does not discharge
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.** A completed output
writer does not authorise a continuation; the calendar artifact approval remains
a separate, open gate.

---

## 8. History — recorded, and not the current status

This document was first prepared as a **decision packet** carrying
`M15_GATE3A_CONTINUATION_OUTPUT_SURFACE_PENDING_HUMAN_CHATGPT_RULING` and
`CONTRACT_CHANGE_REQUIRES_HUMAN_CHATGPT_RULING`, on the ground that no committed
clause named an output directory and that naming one would invent an unapproved
value. Both tokens are **superseded** by §2.

The packet offered three options — **A** a fixed artifact-name allowlist, **B** a
typed extensible surface, **C** a hybrid — and recommended C's shape while
reserving eight items to human + ChatGPT, chief among them the directory's
literal path.

**The ruling is close to C in shape but is not the option as offered.** It adopts
the typed registry and the dedicated root, and it adds two things the packet
raised but did not resolve: the **routing authority** as a first-class
requirement, and the **candidate → promotion lifecycle**, which no option had.
It also settles items the packet had reserved — the canonical declaration key,
reserved-name canonicalisation, the `cost_table_plan.json` disposition, the
status-authority requirement and the provenance requirement — and it names the
root `artifacts/m15_gate3a_continuation/`, as a sibling of the committed tree
rather than a subtree, for the containment reason recorded in §2.2.

An earlier draft also asserted that §12.17 contemplates continuation outputs "by
definition not among the committed eight". That assertion was **wrong** —
playbook §5 enumerates them and all are committed identities — and it is
withdrawn in §4.1. It is recorded here because it was the premise that made the
question appear to require a new namespace, and it did not.
