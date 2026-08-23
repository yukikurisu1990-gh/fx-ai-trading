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

**Base.** master `70bf38b` — the merged targeted-fix Work PR (PR #449).
**Not self-mergeable** (policy §14.7: a Gate-decision PR is never Green).

**Statuses carried, unchanged.**
`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES` —
the official gate status; PR #449 recorded fixes and granted no acceptance ·
`M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED` (PR #444) ·
`M15_GATE3A_D5_8_AND_SECTION12_25_CONTRACT_RULED` (PR #448) ·
`M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN` ·
`M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED` ·
`PRODUCTION_READINESS_NOT_CLAIMED` · `NO_EXECUTION_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` ·
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.

**Forbidden-label note.** This document asserts none of `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, `DEPLOYABLE`. Every occurrence of a label
above is inside this prohibition list or inside a prohibition sentence — §2.12's
"an implicit PASS is forbidden" is the only one outside this note.

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
path can write an artifact is never a reason to promote it to authority**, and
**no roster addition is made by any Work PR.**

Where a new artifact type or name is genuinely required:
**`NEW_ARTIFACT_IDENTITY_REQUIRES_SEPARATE_CONTRACT_GATE_DECISION`.**

**`scrub_report` is not a continuation output.** Playbook §5's "metadata-only /
scrub-clean outputs" states a property required *of* the three outputs, not a
fourth output, and that property is already enforced at every write by the
artifact scan. Refreshing the committed `scrub_report.json` after a promotion
belongs to the promotion diff (§2.3), never to the continuation writer.

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

**The two names share a string prefix, and containment is component-wise.**
Measured: `str(target).startswith(str(root))` and `root in target.parents`
disagree across these two roots. A prefix-based *positive* check would admit
`artifacts/m15_gate3a_continuation_evil/…`; a prefix-based *negative* check
would refuse the whole candidate root once D-7's trap step lands, deadlocking the
contract. `path_authority.is_within` is already component-wise and is correct;
any new check must be too.

**Scope.** This root and this authority govern the continuation's **metadata
evidence** artifacts — the identities of §2.1. The derived M15 data surface (the
20 `.jsonl` files the derivation manifest records as `TO_BE_CREATED_AT_GATE5`) is
**not ruled here** (§4.12), and that it is unruled is **not permission**:
`DERIVED_DATA_OUTPUT_SURFACE_REQUIRES_SEPARATE_CONTRACT_GATE_DECISION`.

Normative:

- A continuation candidate output is written at **exactly one path per artifact
  identity** — `artifacts/m15_gate3a_continuation/<canonical filename>`, with no
  intervening directory component. Nested, dated, run-scoped or versioned
  subdirectories are forbidden whether the component is chosen by the caller or
  by the code: either makes §2.3's collision refusal unreachable, and a refusal
  that cannot fire is not a refusal.
- **The routing authority takes no output-directory parameter at all.** The root
  is a module constant. There is no caller-supplied directory — arbitrary or
  validated — and therefore no directory for a caller to traverse out of.
- **"Beneath" is not established by comparing resolved paths.** Measured at
  `70bf38b`: with the root itself an NTFS junction, both the lexical
  (`root in target.parents`) and the resolved comparison report "contained" while
  the bytes land outside the repository, and `os.path.islink()` and
  `Path.is_symlink()` both report `False`. The authority therefore also refuses
  when the root, or any component between the root and the target, is a reparse
  point — detected with **`os.lstat`**, whose `st_file_attributes &
  FILE_ATTRIBUTE_REPARSE_POINT` fires where `os.stat` does not, because `os.stat`
  follows the junction (measured both ways).
- The root is created with **`exist_ok=False`**; an existing root that is not a
  plain directory is refused rather than adopted. `mkdir(exist_ok=True)` over a
  pre-planted junction is measured to succeed silently.
- A root spelling that Win32 name-normalisation would rewrite is refused **on the
  spelling**, before any `mkdir` — with the root absent, `…_continuation.`
  resolves verbatim and the following `mkdir` creates the real root (FB-4,
  replayed against this root).
- Path traversal is forbidden.
- The continuation writer's permitted write surface is **exactly** the candidate
  root; everything else is refused **by default, not by enumeration**. The
  refusal set is not limited to today's `_PROTECTED_PREFIXES`: policy §3 protects
  `artifacts/**` and any existing evidence in full, and PR #447 FO-1 measured
  successful writes into `artifacts/m15_gate3a/sub/`, `artifacts/foundation_t2`
  and `artifacts/oanda_archive_2026-05-31`, none of which is in that tuple. An
  implementation that refuses only an enumerated list does not satisfy this
  clause.

**A containment authority for this does not yet exist.** Every containment
primitive in the repository is negative (`assert_outside`,
`guards.refuse_real_path`), and `refuse_real_path` allows every tree not in its
seven prefixes — measured, `write_metadata_artifact` accepts an arbitrary
absolute `out_dir` outside the repository. The Work PR adds a **distinct positive
primitive**. It may not be written as `not assert_outside(...)` or
`not is_within(...)`: `is_within`'s recorded monotonicity ("adding the identity
test can only add refusals") is an argument about the *negative* direction, and
in the positive direction the identical extra `True` becomes an extra
**admission**.

### 2.3 Ruling 3 — Candidate lifecycle

A continuation output is **not authoritative evidence at the moment it is
generated**. The lifecycle is:

```
generate candidate  →  verify candidate  →  human-reviewed promotion
```

**`candidate_lifecycle_state` — pinned (PR #444 §10 R-2).** R-2 names
"verified"/"certified" among the terms requiring pinning; this document uses them
in a new sense and pins them here. The state is a **closed enumeration** whose
members are the boundaries of the lifecycle above; §2.6's "lifecycle class" and
§2.13's "candidate lifecycle state" are this same field. Adding a state is a §6
change.

| State | Meaning | Set by |
| --- | --- | --- |
| `CANDIDATE_UNVERIFIED` | written under the candidate root by the routing authority; producer-side validation only | the continuation writer, at write |
| `CANDIDATE_VERIFIED__NOT_COMMITTED_EVIDENCE` | an independent verifier re-measured the bytes and every limb agreed | the verifier |
| `CANDIDATE_REFUTED` | the verifier disagreed, or a limb failed — **terminal** | the verifier |
| `PROMOTED` | the promotion diff of item 4 has merged | the human-reviewed diff — **never a code path** |

An unrecognised spelling fails closed rather than defaulting.

**What "verify" means, and what this decision does not settle.** Schema
validation, the scrub scan and a successful write are **producer-side acts and
are not verification**. The nearest committed definition of a verifier is PR #444
§11's independent **V**, which re-measures bytes — and §12.14 keeps
`scripts/m15_gate3a/**` reader-free with P and V outside it, so **the Work PR at
§7 step 2 cannot implement verification**; the P/V reader is §7 step 6. The Work
PR therefore ships verification as an **unsatisfiable precondition**: a candidate
stays `CANDIDATE_UNVERIFIED`, no component in the reader-free package can advance
it, and promotion of an unverified candidate is refused. Whether "verify
candidate" means V's four-limb re-measurement or something lighter is **not
settled by this decision**:
`CANDIDATE_VERIFICATION_DEFINITION_REQUIRES_CONTRACT_DECISION`.

Normative:

1. A continuation execution creates new candidates **only** under the candidate
   root.
2. Candidate generation never overwrites a committed or protected artifact.
3. A candidate is **never** automatically promoted to committed evidence.
4. Promotion happens as a **human-reviewed repository diff**. Its destination is
   `artifacts/m15_gate3a/` at the canonical filename §2.1 fixes. It is **never
   Green** and merging it requires human + ChatGPT approval. Whether it is an
   Execution-evidence PR alone or an Execution-evidence PR followed by an
   independent post-run Gate-decision (policy §14.8 shows both) is **not settled
   here**: `PROMOTION_PR_CLASS_REQUIRES_CONTRACT_DECISION`.
5. At promotion, schema, identity, status, provenance **and the content scan**
   are re-verified.
6. **A candidate is not gate evidence, in any combination.** Until `PROMOTED` it
   may not be cited to discharge any gate requirement, acceptance criterion or
   checklist item — not alone, and not accompanied by its provenance block, a
   verifier record or a narrative. *One thing this does not forbid:* PR #444 §1
   records that the first continuation may halt by design and that the halt
   returns the question "with measurements in hand". A measurement read out of an
   unpromoted candidate **may** be quoted as input to the new Gate-decision §1
   requires, labelled `MEASURED_FROM_UNPROMOTED_CANDIDATE`, and may not satisfy
   any gate criterion. Quoting a measurement is not promoting an artifact.
7. **No code path may overwrite a committed artifact, in place or otherwise.**
   This binds executing code, not a reviewed diff. D-7 rules that population
   happens through a human-reviewed PR diff; `design_m15_inventory.json` carries
   `SCHEMA_FIXED__POPULATED_AT_IMPLEMENTATION`; and PR #449 (`70bf38b`) already
   replaced that file's content by exactly such a diff. Promotion therefore
   **does** change the bytes of a committed artifact, and is the only way they
   may change.

**Overwrite and collision:**

- A second generation of the same identity **collides by construction** and
  fails closed. Because the candidate path is fixed per identity, this refusal is
  reachable from the production path, not only from a synthetic fixture.
- The collision refusal is **atomic**: the candidate is created with
  `O_CREAT | O_EXCL`, never by `Path.exists()` followed by a write. Measured, the
  check-then-write shape truncates a file that appears between the two calls,
  while `O_EXCL` refuses and preserves it. Collision is decided against the
  registry's declared name-set, never against `Path.exists()`, which folds case
  on NTFS and does not on `ubuntu-latest`.
- A pre-existing file at a canonical candidate name is a **hard stop**. No flag,
  argument, environment variable or configuration may clear it.
- Silent overwrite is forbidden.
- Automatic replacement is forbidden.
- A mechanism that lets the **caller** decide how to avoid a version collision is
  forbidden.
- The lifecycle mechanism itself is implemented by the later Work PR, to this
  contract.

**Re-run after a designed halt — not resolved here.** PR #444 §1 records that the
first continuation may well halt and that resolving it "requires a new contract
Gate-decision informed by an approved read-only measurement" — a second
authorised run is the expected sequel. Under §2.2 and §2.5 the candidate path is a
pure function of `artifact_id`, so each eligible identity is writable **exactly
once for the lifetime of the candidate root**, and nothing here names an actor or
procedure that may clear, rotate or version that root — which sits inside
`artifacts/**`, a protected path. Recorded as open, not closed by implication:
**`CANDIDATE_REGENERATION_AFTER_HALT_REQUIRES_CONTRACT_DECISION`.** Two bounded
observations for that decision: a per-run segment *derived by the authority* from
committed provenance is not the caller-chosen mechanism this ruling forbids, but
it is a new output-root shape and §6 reserves it; and **deletion is the wrong
resolution** — a halted run's candidates *are* the measurements the halt exists to
produce. Until then a second run into an occupied root fails closed, which is
correct: it stops, and it stops loudly.

**The candidate root is never committed by accident.**
`artifacts/m15_gate3a_continuation/` is added to `.gitignore` by the
implementation Work PR (verified: no current `.gitignore` entry matches it). PR
#449 §7.1 records `git add -A scripts tests artifacts` staging **183 previously
untracked files** under `artifacts/` — a policy §14 violation found only by a
later read-only pass — and an un-ignored candidate root reproduces that hazard on
every run. A candidate reaching committed history outside the promotion diff is a
candidate a later session reads as evidence.

**Interaction with playbook §9.** Its checklist item "prior evidence directories
untouched (…`artifacts/m15_gate3a/*`)" **is** tripped by a promotion diff, and was
tripped by PR #449. D-7 governs — §9 is "a per-PR merge-scope check, not a
declaration of immutability" — and the checkbox is satisfied when every touched
file under that tree is named in the approval and is the promotion of a verified
candidate. The playbook line is amended accordingly in the same Work PR (§5.4).

### 2.4 Ruling 4 — Single continuation routing authority

**`ALL_GATE3A_CONTINUATION_OUTPUT_WRITES_MUST_ROUTE_THROUGH_THE_APPROVED_CONTINUATION_OUTPUT_AUTHORITY`**

**Scope.** "Continuation output" here means the **metadata evidence** surface —
the identities of §2.1. The derived M15 data files are a different surface and are
not ruled by this decision (§2.2, §4.12).

**Route enumeration cannot carry this rule, and is not attempted.** Measured at
`70bf38b`, thirteen distinct routes place bytes into a candidate root — including
`os.replace` and `os.link`, which emit no `open` at all — and the repository
contains **sixteen** functions named `write_report`, of which §2.4 could name one.
The requirement is therefore stated as an **acceptance** property:

- The routing authority is the **only** producer of a continuation artifact, and
  every artifact it produces carries a provenance record (§2.13) that it alone
  emits.
- **The candidate root is a closed set.** Verification enumerates every entry
  beneath the root — files, directories, links, any extension — and refuses **the
  whole root** if any entry is not an artifact the authority produced with a
  matching provenance record. A file that arrived by any other route therefore
  cannot be verified, cannot be promoted, and poisons the run rather than passing
  through it.
- Nothing about "not calling the generic writers" is claimed or tested as
  containment. **This is not an instruction to remove them**; they remain, and
  they simply cannot produce an artifact that survives verification.

**Pinning.** The Work PR pins this with a **runtime `sys.addaudithook` trace**, in
the manner PR #446 established (`tests/conftest.py`) and `test_wp5_reader_freedom`
already uses for the read direction: during a continuation execution, no
filesystem-mutating audit event may name a path beneath the candidate root except
from the routing authority's own frame. Static import and reverse-caller tests are
retained as a **second** pin and are explicitly not sufficient alone — measured,
FR-18's import-by-name fix leaves `write_report` reachable as
`sys.modules["scripts.ml_step4.evidence"].write_report` and as
`scan_payload.__globals__["write_report"]`, neither of which an AST sweep sees.

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

A payload carrying a non-canonical spelling of the declaration key is
**refused**, not treated as undeclared: falling through to a filename-derived
schema is the same fail-open by another route. The present divergence — an
exact-case schema lookup beside a case-folded scrubber lookup — is closed by
making **both** sides exact; closing it by folding both sides is **forbidden**,
because that admits every spelling instead of refusing every non-canonical one. A
payload carrying two declaration keys, one canonical and one not, is refused
rather than resolved to either. An unknown or malformed declaration **fails
closed**.

### 2.8 Ruling 8 — Reserved filename canonicalisation

Filename identity is **byte equality against the canonical filename the typed
registry emits for that `artifact_id`, after no transformation of any kind** — no
case fold, no NFC/NFKC normalisation, no whitespace strip, no confusable fold, no
extension re-derivation. Stated positively and deliberately: a
canonicalise-then-compare implementation satisfies the words "exact match" while
admitting spellings this rule exists to refuse — measured, NFKC-then-compare
admits a leading space and a fullwidth character, and casefold-then-compare admits
`NO_OVERLAP_PROOF.json`. Byte equality alone separates. No enumeration of
forbidden transformations is given, because §4.5's own nine measured spellings
include two — `_v2` and a double `.json.json` extension — that no such enumeration
reached.

The rule governs **three surfaces**, not one: emission (the caller never supplies
a filename, §2.5); the candidate root as a closed set (§2.4); and promotion and
the committed manifest (§4.10), where it is not relaxed to a fold or a subset.

Comparison is over the registry's declared name-set, **never** over
`Path.exists()`: on NTFS `exists()` folds case, on `ubuntu-latest` it does not, and
deciding identity on it would give one name-set two verdicts across hosts, which
§12.18 forbids.

FB-7 canonicalisation applies to **content**; filename identity is this separate
boundary, and **both must be implemented** — the content limb is (PR #449), the
filename limb is **not**: §4.5 measured nine spellings of one reserved name
coexisting in a single directory. **That two names render identically is never a
reason to admit one, and that two names render differently is never a reason to
admit either.**

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

`cost_table_plan` is **conditionally** eligible: playbook §5 permits it *if and
only if explicitly authorised in the approval*. The registry carries that
condition as its eligibility value, never a flat true, and the continuation
refuses to produce it when the approval does not name it. Referrals NR-F (the
all-in-cost formula is dimensionally incoherent) and NR-I (the rollover exclusion
window) bind at the moment it is authorised.

The committed roster is eight and the eligible set is three. The five
non-eligible committed artifacts are named **exhaustively**:
`design_m15_derivation_manifest`, `effective_n_estimator_spec`,
`forward_epoch_adoption_manifest`, `forward_epoch_inventory` and `scrub_report`.
None is generable by the continuation writer; being readable or committed does
**not** make it generable, and being reserved does **not** make it overwritable.
`effective_n_estimator_spec` and both forward artifacts additionally remain
**never written**, per D-7. §5.3's alignment of
`design_m15_derivation_manifest.json` is a human-reviewed diff (§2.3 item 4), not
a write by the continuation writer.

### 2.11 `cost_table_plan.json`

Not adopted as a ninth committed or continuation artifact. That the current code
can write it is not authority.

The mapping to an existing identity **is** available from committed authority and
therefore needs no invention: `artifacts/m15_gate3a/cost_table_plan_or_metadata.json`
declares `"artifact": "cost_table_plan"`, so the committed evidence states both
halves — canonical identity `cost_table_plan`, canonical filename
`cost_table_plan_or_metadata.json`. **The filename `cost_table_plan.json` is
refused**; the identity `cost_table_plan` resolves to the committed filename.

Had the mapping not been derivable, the disposition would have been
`REQUIRES_SEPARATE_ARTIFACT_CONTRACT_DECISION`.

The schema declares **two** artifact names for this file — `cost_table_plan` and
`cost_table_plan_or_metadata` — and both resolve today. For the continuation
registry the canonical `artifact_id` is **`cost_table_plan`**, the identity the
committed artifact itself declares; **`cost_table_plan_or_metadata` is not a
continuation `artifact_id` and is refused as one.** §2.6's uniqueness rule binds
the forward direction: one `artifact_id` resolves to one identity, and no second
spelling reaches the same output through a different permission path.

### 2.12 D-7 status authority

**`CONTINUATION_OUTPUT_REQUIRES_EXPLICIT_COMMITTED_STATUS_AUTHORITY`**

Every continuation-output-eligible artifact requires a status authority. Where an
artifact currently has no status operand: an implicit PASS is forbidden; treating
it as continuation-authoritative while its status is absent is forbidden; and
substituting a generic global status is forbidden.

Measured, and directly engaged by this rule: `no_overlap_proof` and
`cost_table_plan_or_metadata` — **two of the three eligible outputs** — carry no
`status`, and their schemas presently *forbid* the key (a `status` on either is
refused today as `gate3a_undeclared_key`). `scrub_report` is in the same position
and is **not** a continuation output (§2.1) — recorded only so the absence is on
file if it ever becomes one.

**The third is not settled either.** `design_m15_inventory` carries
`SCHEMA_FIXED__POPULATED_AT_IMPLEMENTATION`, which is its **pre-population**
status, and no committed source names the value it takes once the continuation
populates it (verified: the token appears only in the artifact itself, in PR #444
§7's citation of it, and in test fixtures).

**Admitting the key.** Extending the `no_overlap_proof` and
`cost_table_plan_or_metadata` schema vocabularies by the single key `status` is a
schema change; whether this ruling grants it is **not recorded**, and the document
does not decide it: `STATUS_KEY_ADMISSION_REQUIRES_CONTRACT_DECISION`. §6's
reservation governs any change to what a status **means**.

**Foreseeable consequence, recorded so it is not a surprise.** On this rule **all
three** eligible outputs may fail closed at the first continuation for want of a
status authority — reducing the writable surface from three to none until the
question is settled. That halt is **by design**: the response is a Contract
Gate-decision fixing the status semantics from committed authority, never a
relaxation, and never an implementer supplying a value to turn a suite green.

The later Work PR implements the status operand **from existing contract**. Where
an artifact's status semantics are **not** uniquely derivable from committed
authority, that artifact is
**`STATUS_AUTHORITY_REQUIRES_CONTRACT_DECISION`** and fails closed. No Work PR
invents new research semantics.

### 2.13 Provenance

A continuation output requires a committed provenance binding, at minimum to:
design epoch identity · artifact identity (the canonical `artifact_id`) ·
generating contract/version, by document and merge SHA · the relevant upstream
approved authority — for a coverage-bearing artifact, the approved calendar
artifact's identity **and content digest** · `candidate_lifecycle_state` from
§2.3's enumeration · **run identity** (run ID, code SHA, PR head/base) ·
**derivation binding** (the named aggregation script at a named git SHA, the
config hash, the named source identity — PR #444 §11 limb DB) · **the candidate's
own measured identity** (SHA-256 and byte size, co-measured from one pass) ·
generation timestamp through the single formatter of §12.23. The recorded path is
the **resolved** path, not the spelling handed to the writer.

**The test this list must pass:** two distinct runs must not be able to produce
the same provenance block. The first five items alone do not meet it — a halted
first run and its post-ruling re-run agree on every one of them — which is why run
identity and the derivation binding are named. Each field is **individually**
required; a single "provenance absent" check does not satisfy this section.

"Committed" means each value resolves to committed authority. It does not mean
the candidate's provenance is itself committed; a candidate is not, until
promotion.

A correct path, filename and schema do **not** by themselves establish authority.
Missing, malformed or unapproved provenance **fails closed**.

---

## 3. Dispositions fixed by this decision

| Item | Disposition |
| --- | --- |
| **§12.17 limb 1** | **RULED** — by the dedicated continuation root (§2.2), typed artifact routing (§2.4, §2.6), canonical artifact identity (§2.5, §2.7, §2.8) and the candidate lifecycle (§2.3) |
| **§12.17 limb 2** ("never overwrite protected evidence") | **FIXED at `70bf38b`** — overwrite refusal implemented and lead-reproduced. Protected-tree refusal, sometimes cited here, discharges **§12.18**, not this limb |
| **§12.17 limb 3** ("population by human-reviewed PR diff") | **RULED, NOT IMPLEMENTED** — §2.3's candidate → promotion lifecycle is the mechanism, and no part of it exists in source today |
| **§12.18** (protected trees; cwd-independence) | **FIXED at `70bf38b`** — implemented and lead-reproduced |
| **§12.17 overall** | **`SECTION_12_17_RULED_AND_IMPLEMENTATION_REQUIRED`** |
| **Unknown artifact names** | was `REQUIRES_CONTRACT_OR_SCHEMA_DECISION`; **resolved** → `UNKNOWN_CONTINUATION_ARTIFACTS_FAIL_CLOSED_TYPED_REGISTRY_REQUIRED`. Source implementation is the later Work PR |
| **Routing bypass** | a **first-class contract requirement** (§2.4), not a fix-note footnote |
| **Derivation manifest divergence** | **`TARGETED_IMPLEMENTATION_FIX_REQUIRED`** — see §5.3 |
| **FR-19** | unchanged: `SEPARATE_TEST_SAFETY_WORK_PR`, out of scope |

"FIXED" in this table means **a behaviour measured at `70bf38b`**, never audit
acceptance. The official gate status remains
`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`;
no independent audit has accepted any of this machinery, and this decision grants
none. Limb numbering follows PR #449 §7; §12.17's literal clauses are read
verbatim above.

**Left open by this decision, each recorded rather than closed by implication:**
`CANDIDATE_VERIFICATION_DEFINITION_REQUIRES_CONTRACT_DECISION` ·
`PROMOTION_PR_CLASS_REQUIRES_CONTRACT_DECISION` ·
`CANDIDATE_REGENERATION_AFTER_HALT_REQUIRES_CONTRACT_DECISION` ·
`STATUS_KEY_ADMISSION_REQUIRES_CONTRACT_DECISION` ·
`DERIVED_DATA_OUTPUT_SURFACE_REQUIRES_SEPARATE_CONTRACT_GATE_DECISION`.

---

## 4. The measured evidence this ruling rests on

All probes were executed against a **synthetic copy of the tree, outside the
repository working directory**, at source revision `70bf38b`. The repository
itself was read-only: no file inside it was created, modified or deleted; no
artifact was generated; no real data, `.env`, database, network or credential was
touched. Where a probe below is described as overwriting an artifact or writing
into `docs/`, `data/` or `models/`, the write landed in the **sandbox copy** of
that path and never in the repository. Retained because the ruling's shape follows
from these facts.

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
argument; a path outside the repository was accepted. `write_metadata_artifact` has **no non-test caller**, so confining it breaks no
production route. It is not free in the suite: **45 call sites across 7 test
files** pass a caller-supplied `tmp_path`, most under non-canonical names
(`ok.json`, `x.json`, `y.json`, `sneaky.json`) that §2.8 now refuses — including
the *accepted* half of several refusal tests, whose negative controls must be
re-founded on canonical identities. **`write_metadata_artifact` is the
continuation writer and is confined under the typed registry; it is not left
beside the new authority as a second route**, which would make the repository's
own schema-validating writer the surviving alternate writer §2.4 exists to
close.

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
§12.17 limb 1 implementation · unknown-artifact fail-closed ·
committed-directory-manifest separation · a positive containment primitive ·
reparse-point refusal · atomic `O_EXCL` creation · the `.gitignore` entry for the
candidate root · derivation manifest six-field fix · regression and adversarial
tests · a runtime `sys.addaudithook` routing pin · static reverse-caller and
import tests · internal audit and mutation testing.

**FR-19 is not included.**

### 5.2 Implementation freedom, and its limit

The mechanism is free — class, enum, dataclass, immutable mapping, registry
module, router object. The **observable contract** is not: single routing
authority · typed identity · fixed candidate root · fail-closed unknown identity ·
no caller-supplied path or filename · no alternate-writer bypass · explicit status
· explicit provenance · candidate/promotion lifecycle · preservation of the
committed-directory manifest pin.

One placement is not free: `test_wp5_reader_freedom.py` pins the reverse-caller
set to `scripts/m15_gate3a/` and `tests/m15_gate3a/`, so the routing authority and
its callers live **inside** the package, and that pin is **narrowed to the one
named caller**, never widened. A new writing module is added to that file's
per-module filesystem allowlist with its exact surface.

### 5.3 Derivation manifest divergence

`design_m15_derivation_manifest.json` still declares
`"missing_minute_policy": "… per-file gap report (count + max gap) …"` while
`design_m15_inventory.json` declares the six-field `minute_accounting` that PR
#444 §5 approved and PR #449 implemented. **This is not a contract choice** — it
is an implementation divergence from the current committed schema.
`TARGETED_IMPLEMENTATION_FIX_REQUIRED`: the Work PR aligns the derivation
manifest, the schema declaration and the tests to the approved six-field schema.
**No new schema semantics are invented.**

This edits a committed artifact under `artifacts/m15_gate3a/`, whose own status is
`DERIVATION_CONTRACT_FIXED__BYTE_PRODUCTION_DEFERRED_TO_IMPLEMENTATION`. Its
authority is PR #444 §5 — "This schema change is approved by this Gate-decision" —
and its route is D-7's human-reviewed diff, the same route PR #449 used for
`design_m15_inventory.json` under FR-12. §2.2 and §2.3 item 7 bind the **writer**,
not the diff. The merge record states playbook §9's checklist exception
explicitly, names the single file, and confirms no other file under that tree
changed. `tests/m15_gate3a/test_wp5_authorities.py` also reads this artifact and
is re-checked. Whether the alignment **removes** `gap_report` or leaves it beside
`minute_accounting` is not settled here; a removal is a schema narrowing and needs
its own decision.

### 5.4 Observable requirements the tests must pin

Each item is one **failing-before / passing-after** regression test carrying its
own finding token, beside a **discriminating negative control** — a case identical
in every respect except the single attribute under test, which is accepted. Every
sweep carries a **non-vacuity floor**. This is PR #444 §10 R-1 (the
negative-control rule) and PR #444 §13 (anti-patterns forbidden).

An earlier draft of this list was measured against a deliberately degenerate
implementation and **15 of 17 mutations survived it**, with all six reviewed
failure modes intact. The list below is the replacement.

**Identity and registry**

1. **The eligible identity set is pinned by equality** — exactly
   `{design_m15_inventory, no_overlap_proof, cost_table_plan}`, asserted against
   those three literals. Adding a fourth turns CI red. Without this, §2.1 is
   enforced by nothing.
2. **A known eligible `artifact_id` resolves to exactly one path**, equal to
   `artifacts/m15_gate3a_continuation/<canonical filename>` with **no intervening
   component**. The resolver accepts no directory, filename, subdirectory, run-id,
   version or suffix parameter, and any extra argument raises.
3. **An unknown `artifact_id` raises** the package's own error type — it does not
   return `None`, an empty result or a default path. Corpus: an unregistered name,
   `""`, `"   "`, `None`, `123`, `["x"]`, `{}`, and `"cost_table_plan.json"`.
   *Control:* `"cost_table_plan"` resolves to `cost_table_plan_or_metadata.json`.
4. **A newly registered identity is ineligible by default** — a row constructed
   without an explicit eligibility declaration is refused. *Control:* the same row
   with the declaration is accepted.
5. **The registry and `_SCHEMAS` vary independently**, both directions, each
   injection carrying a **took-effect discriminator**: `_SCHEMAS` is a module-level
   `Final` whose derived maps (`_SCHEMAS_BY_STEM`, `_SCHEMAS_BY_ARTIFACT`,
   `EXPECTED_ARTIFACT_FILES`) are built at import, so a `monkeypatch.setattr` that
   reaches none of them passes whether or not the property holds.
6. **Registry integrity over every row, with a floor** — unique `artifact_id`,
   unique canonical filename, resolving schema, status authority present or the
   row marked `STATUS_AUTHORITY_REQUIRES_CONTRACT_DECISION`, provenance
   requirement present, lifecycle class present.
7. **`cost_table_plan` resolves to `cost_table_plan_or_metadata.json` and only to
   it**; the filename `cost_table_plan.json` is refused by every route; and
   `cost_table_plan_or_metadata` is **not** a second `artifact_id`.
8. **`Artifact`, `ARTIFACT`, `ArTiFaCt`, a confusable spelling and a zero-width
   spelling of the declaration key are each refused**, one case per spelling.
   *Control:* the exact key `artifact` is accepted. Two declaration keys, one
   canonical and one not, are refused rather than resolved to either.
9. **Reserved-filename impersonation is refused across the whole measured
   corpus**, one case per spelling: the nine of §4.5 — leading space, Greek
   omicron, Cyrillic es, fullwidth, zero-width, NBSP, `" x .json"`, double
   extension, `_v2` — plus case variants, trailing dots and spaces, and alternate
   separators. **Each decided by the package's own byte comparison, never by
   `Path.exists()`**, so it discriminates identically on NTFS and on
   `ubuntu-latest`.

**Routing and containment**

10. **The candidate root is pinned by literal and by identity** — equal to
    `artifacts/m15_gate3a_continuation` relative to the repo root; refused if it,
    or any component beneath it, is a reparse point, **detected with `os.lstat`**
    (measured: `os.stat` follows a junction and reports `False`).
11. **Containment is component-wise in both directions.** After
    `artifacts/m15_gate3a` joins `_PROTECTED_PREFIXES`, the candidate root and
    every path beneath it are still **ALLOWED**, while the committed tree, a file
    in it and a deep descendant are all **REFUSED** — asserted together, with
    `…_continuation_evil` and `…_gate3a_evil` as controls, so the string-prefix
    relation cannot be closed by a string-prefix check.
12. **The D-7 trap is discharged**: `artifacts/m15_gate3a` is a member of
    `_PROTECTED_PREFIXES`, and a write at each of the eight committed filenames
    raises.
13. **The authority's public signature accepts no path, path fragment, directory
    or filename from the caller** — pinned against the signature, not by passing a
    bad value. A traversal, protected or absolute value handed to `artifact_id` is
    refused as an unknown identity, not path-validated.
14. **A root spelling Win32 trailing-trim would rewrite is refused with the root
    absent, before any `mkdir`.**
15. **No alternate writer produces an accepted continuation artifact.** Two limbs,
    both required. *Write side, static:* an AST sweep over
    `scripts/m15_gate3a/**` (recursive) plus a live-import-graph probe find no
    reference — called, bound, aliased, `getattr`-computed, relative-imported or
    `importlib`-named — to `scripts.ml_step4.evidence.write_report`, to any other
    generic writer, or to `open(..., "w")` / `Path.write_text` / `Path.write_bytes`
    outside the routing-authority module, whose filesystem surface is itself
    pinned by exact allowlist, each sweep carrying a non-vacuity floor. *Read side,
    behavioural — the limb that makes the requirement true:* a file placed beneath
    the candidate root by any other means, including `os.replace`, `os.link`,
    `shutil.copyfile`, `open(..., "a")`, a `NamedTemporaryFile(dir=root)`, a bare
    `mkdir` or a `.jsonl`, causes verification of the **whole root** to refuse.
    *Control:* a file written through the authority verifies.
16. **A runtime `sys.addaudithook` trace over a continuation execution** shows no
    filesystem-mutating audit event naming a path beneath the candidate root
    except from the authority's own frame. Events are enumerated over CPython's
    audit table — `open`, `os.rename`, `os.link`, `os.symlink`, `os.mkdir`,
    `os.remove`, `os.truncate`, `shutil.copyfile`, `subprocess.Popen` — because
    `os.replace` and `os.link` emit no `open` event at all.

**Payload, status, provenance**

17. **A payload whose self-declared `artifact` disagrees with the resolved identity
    is refused**, and a candidate whose on-disk filename changed after the write is
    refused at verification. *Control:* agreement is accepted.
18. **A payload failing its identity's schema is refused**, with the schema token,
    before any directory is created and before any bytes are written.
19. **A direct overwrite of a committed artifact is refused**, distinctly from
    item 20.
20. **A collision at the canonical candidate path fails closed, atomically** —
    created with `O_CREAT | O_EXCL`, never `exists()`-then-write (measured: the
    check-then-write shape truncates a file appearing between the two calls). The
    refusal is reachable from the production path and names the occupying
    candidate's run identity.
21. **The current status dispositions are pinned as measured, not invented.**
    Each eligible identity whose status authority is not derivable from committed
    authority is refused by name with its own token. Inventing a status semantics
    to turn this green is forbidden by §2.12 and is itself a contract breach.
22. **Each provenance field of §2.13 is individually required** — one case per
    field removed, each with a distinct token, plus one with provenance absent.
    *Control:* the complete binding is accepted. And **two distinct runs cannot
    produce the same provenance block.**

**Lifecycle**

23. **A candidate is marked, and marked candidates are refused as evidence.**
    Every file beneath the root carries `candidate_lifecycle_state`; every
    consumer of gate evidence in the package refuses a payload carrying a
    non-promoted state. *Control:* the promoted state is accepted.
24. **No code path can promote.** No callable in `scripts/m15_gate3a/**` copies,
    moves, renames, links or writes from the candidate root into
    `artifacts/m15_gate3a/`; the package exposes no `promote`/`install`/`publish`
    callable; and no `shutil.copy*`, `shutil.move`, `os.replace`, `os.rename`,
    `Path.rename` or `Path.replace` appears in it. *Control:* the same payload to
    a permitted candidate path succeeds.
25. **`candidate_lifecycle_state` can never reach `PROMOTED` in-process** —
    refused through every route `sealing` already covers, and an unrecognised
    spelling fails closed. **`CANDIDATE_REFUTED` is terminal**: no later call
    moves it.
26. **`cost_table_plan` is refused when the approval does not explicitly authorise
    cost-table production.**

**Manifest and schema**

27. **The committed-directory manifest is a third authority.**
    `tests/m15_gate3a/test_recheck_fixes.py:898` still asserts **set equality**
    against `artifacts/m15_gate3a`, and its expected set is no longer derived from
    `_SCHEMAS`. Adding a `_SCHEMAS` entry alone changes neither the manifest nor
    any continuation permission. Note the subset sibling at
    `test_wp_artifacts_allowlist.py:657` (`set(...) <= set(present)`) would pass
    with a ninth file already; the **equality** form is the one that must survive.
28. **The six minute-accounting field names are pinned by set equality** in **each**
    declaring location — the inventory's `minute_accounting`, the derivation
    manifest's `aggregation_contract.missing_minute_policy`, and the schema
    declaration in source. "Used consistently" is not an assertion; equality
    against literals is.

**Mutation acceptance bar.** The Work PR runs and reports a mutation study in PR
#444 §13's table shape, mutating **call sites, not only primitives** — the recorded
first pass killed 12 of 20 because only primitives were mutated. At minimum, one
mutation per ruling: a fourth registry row; re-siting the root inside
`artifacts/m15_gate3a/`; adding an optional subdirectory or run-id parameter;
adding a promotion helper; calling a generic writer from a **new module outside
`scripts/m15_gate3a/`**; a filename parameter that must merely agree; deriving the
registry from `_SCHEMAS` filtered by filename; folding the declaration key on both
sides; refusing only one confusable; returning `None` in place of raising;
defaulting eligibility to true; accepting `cost_table_plan.json`; minting a status;
requiring one provenance field of several; and aligning the inventory while leaving
the derivation manifest. **Every one must be killed by an identifiable named test,
and no newly-introduced survivor is admitted.**

**The D-7 trap is discharged in the same PR** — once the candidate root is
enforced, `artifacts/m15_gate3a` joins `_PROTECTED_PREFIXES`. The governance text
amended with it is fixed here and not chosen by the Work PR. **Playbook §5 names
no directory** (verified); the three edits are: (1) playbook §5's produce-clauses
gain "written as a **candidate** under `artifacts/m15_gate3a_continuation/`;
promotion into `artifacts/m15_gate3a/` is a separate human-reviewed diff", and may
not add, remove or re-word any enumerated output — that list is the eligibility
authority for §2.1 and §2.10, and changing it is
`NEW_ARTIFACT_IDENTITY_REQUIRES_SEPARATE_CONTRACT_GATE_DECISION`; (2) playbook §9's
NR-A referral row records that D-7 and this decision resolve it in favour of the
dedicated candidate root; (3) playbook §9's "prior evidence directories untouched"
line gains "— except a promotion or schema-alignment diff explicitly named in the
approval".

---

## 6. Changes that will still require human-reviewed contract/schema authority

Every item below is **Amber at minimum** under policy §3 and may not be taken
inside an ordinary Work PR without a Gate-decision recording it:

- a new continuation artifact identity, or a new canonical filename
- granting continuation eligibility to any further artifact
- a new output root, or widening the candidate root
- adding or changing status semantics, and admitting `status` into any schema
  that presently forbids it
- changing lifecycle semantics, the promotion rule, or the promotion PR class
- changing the protected or reserved surface, including `_PROTECTED_PREFIXES` and
  the `path_authority` roots
- performing a promotion, and clearing, rotating, versioning or deleting the
  candidate root or any candidate in it
- any change to the artifact or evidence schema, the scrubber's vocabulary or
  thresholds, or the guards (policy §3)
- any change to a frozen research contract — PR #444's D-series and §12, PR #448's
  rulings, and §2 of this document
- any change to a governance document, other than the three edits §5.4 fixes
- any change to the §7 sequence, or the discharge of any pre-continuation item
- any edit to a committed artifact under `artifacts/m15_gate3a/` other than the
  one §5.3 fixes
- the derived M15 data output surface — the 20 `.jsonl` files — which this
  decision does not rule
- a persisted producer / verifier / consumer-recheck evidence identity, should the
  P/V reader gate require one; it is not among §2.1's three

An ordinary implementation refactor that changes none of these is a Work PR — and
it is still **Amber**, prepared autonomously and merged only on human + ChatGPT
approval. It is never Green and never self-merged (policy §14.7).

---

## 7. Non-authorisation

This decision settles one contract question. It authorises no operation.

It permits no real data read, no real M15 derivation, no checksum execution, no
spread computation, no validation, holdout, training, inference, execution or
broker activity. It adopts no epoch and does not lift the forward-epoch WAIT. **It
generates and approves no calendar artifact and decides no market hours.** **It
creates no directory, including `artifacts/m15_gate3a_continuation/`.** It changes
no source, no test and no committed artifact; it implements nothing in §2; it
implements no FR-19; it grants **no** source-audit acceptance; and it does not
authorise the gate-3a continuation.

Nothing in the preparation of this document used a forbidden operation: no
source, test or artifact change inside the repository · no artifact generated · no
real-data read · no `.env` read · no DB · no network, DNS, UDP or TCP · no
credential use · no derivation, validation, holdout, training or execution · no PR
merged.

---

## 8. Sequence from here

1. This Contract Gate-decision merges on human + ChatGPT approval.
2. The continuation output-surface implementation Work PR.
3. That PR merges on human + ChatGPT approval — Amber, not self-mergeable
   (policy §5, §14.7).
4. The FR-19 test-safety Work PR.
5. The **fifth independent source-audit**, in a fresh top-level session — **not
   before the contract implementation**.
6. The P/V reader design PR — synthetic-only, with its own audit; it introduces
   the repository's first new read capability since the gate-P1 inspector.
7. Concrete calendar artifact approval.
8. Only then a **separately-authorised** gate-3a continuation (playbook §5) —
   **Red**, design-span only, metadata-only outputs.
9. The promotion diff for any verified candidate, and the independent post-run
   judgement of it.

**This ruling does not discharge
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.** A completed output
writer does not authorise a continuation; the calendar artifact approval remains
a separate, open gate.

---

## 9. History — recorded, and not the current status

*The current status is the header and §2; nothing in this section is current.*

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

The same premise also stands in **merged, committed text** —
`docs/design/m15_targeted_fix_fb1_fb10_fr1_fr21.md` §7.2 (PR #449, `70bf38b`). It
is **superseded** by §2.1 and §4.1. Per `CLAUDE.md` the merged record is not
rewritten; it is superseded here.

**Internal review.** Five independent doc-only roles reviewed this document after
the ruling was recorded — contract/governance, artifact identity/schema,
path/routing security, lifecycle/promotion, and testability/adversarial — none
given another's conclusions. Their findings were adopted after the lead
re-executed every decisive measurement, including one correction to a proposed
remedy: the reparse-point detector must be `os.lstat`, since `os.stat` follows the
junction and reports `False`. The most consequential findings were that the
earlier observable-requirement list left 15 of 17 mutations alive, that §12.17's
limb 3 had been mislabelled, that §5.4 pointed at a playbook clause that does not
exist, and that §2.8 claimed an implementation that does not exist.
