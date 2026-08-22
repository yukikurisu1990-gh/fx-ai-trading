# M15 gate-3a — continuation output-surface Contract Gate-decision

**Type.** Contract Gate-decision PR (policy §14.2). **Risk tier.** Amber —
doc-only, but it fixes a research contract governing protected paths. Merging
needs human + ChatGPT approval.

**Completion state.**
`M15_GATE3A_CONTINUATION_OUTPUT_SURFACE_PENDING_HUMAN_CHATGPT_RULING`
· `CONTRACT_CHANGE_REQUIRES_HUMAN_CHATGPT_RULING`

**Statuses, unchanged and carried.** `PRODUCTION_READINESS_NOT_CLAIMED` ·
`NO_EXECUTION_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` ·
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`. Gate-3a continuation is
**not** authorised. The fifth independent source-audit has **not** been started.
No source, test or artifact is changed by this PR.

---

## 1. The question

**By what authority is the set of output artifacts that the gate-3a continuation
may produce defined?** Specifically, which of *filename · artifact identifier ·
artifact type · output directory · schema · status · provenance* is the identity
authority, which is the permission authority, and how do they bind.

Two items previously tracked separately — **§12.17 limb 1** (the "separate output
directory" that has no mechanism) and **unknown artifact names** (a payload that
declares no identity is writable under any `*.json` name) — are one question.
Both are limbs of a single absent object: a declared output surface.

---

## 2. What the committed authority already settles

**D-7 / NR-A is RULED and closed** (PR #444 §7). The playbook's referral table
still shows NR-A as `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`, but the playbook's
own preamble governs it: the rulings "are **closed** … the Classification column
below is retained as the historical audit finding that produced them, not as an
open question." **This packet does not reopen NR-A.** It completes a successor
item that D-7 itself created.

D-7 settles, verbatim:

- Playbook §9 is a per-PR merge-scope check, **not** immutability.
- **Population happens through a human-reviewed PR diff. No code path writes into
  the protected tree.**
- The continuation's **outputs go to a separate output directory** and **never
  overwrite existing protected evidence**.
- `effective_n_estimator_spec.json` and both forward artifacts are **never
  written** by this continuation.
- **Trap:** do not add `artifacts/m15_gate3a` to `_PROTECTED_PREFIXES` until the
  separate output directory is adopted. *(Verified unsprung at `70bf38b`.)*

**The premise that made this question look hard is false.** PR #449 §7.2 recorded
that "§12.17 contemplates continuation outputs that are by definition not among
the committed eight". Playbook §5 enumerates the continuation's outputs:

> - Produce the **design M15 inventory + checksums** (populating the PR #431
>   schema; 20 files; per-file ts-bounds).
> - Produce the **byte-level no-overlap proof** …
> - Optionally produce **cost tables from the design span only**, if and only if
>   explicitly authorised in the approval …

Those are `design_m15_inventory`, `no_overlap_proof` and
`cost_table_plan_or_metadata` — **three of the committed eight, by name**. The
gate-3a continuation needs **no new artifact name**. What it needs is a second
*location* and a *lifecycle* distinction for identities that already exist. The
earlier framing is withdrawn here.

---

## 3. Measured present behaviour

All executed read-only against `70bf38b` in a `git archive` sandbox. Nothing was
written inside the repository.

### 3.1 There is no identity authority — only an opportunistic schema lookup

`_validate_name` validates **shape only** and consults no roster.
`resolve_schema` is the single site where a filename and a schema meet, and it
binds them **only if the payload volunteers a non-empty `str` `artifact` field**.
A miss returns `(None, [])` — no finding — and the payload falls to the
undeclared backstop.

**Seven spellings of "declare nothing" each buy an arbitrary filename:**

| `artifact` value | result under filename `gate3a_continuation.json` |
| --- | --- |
| absent · `""` · `"   "` · `123` · `None` · `["x"]` · `{}` | **CLEAN — accepted** |

Measured **identical at base `c7e477a`**: this PR's predecessor neither
introduced nor widened it.

### 3.2 The reserved surface is nine names, not eight

`cost_table_plan_or_metadata.json` declares `"artifact": "cost_table_plan"`, and
the alias is registered. Consequence, executed: **`cost_table_plan.json` — a
filename that has never been committed or reviewed — resolves to a full declared
schema and writes.**

### 3.3 Reserved-name impersonation is live, and the family is wide

Filenames receive `str.__str__` pinning and **no** NFKC, confusable fold or
invisible-character strip — the FB-7 machinery protects payload content and not
the namespace. Executed, into one directory already holding the genuine
`scrub_report.json`:

| spelling | result |
| --- | --- |
| `" scrub_report.json"` (leading space) | **WROTE** |
| `"scrub_repοrt.json"` (Greek omicron) | **WROTE** |
| `"ѕcrub_report.json"` (Cyrillic es) | **WROTE** |
| `"ｓcrub_report.json"` (fullwidth) | **WROTE** |
| `"scrub​report.json"` (zero-width) | **WROTE** |
| `"scrub report.json"` (NBSP) | **WROTE** |
| `" scrub_report .json"` | **WROTE** |
| `"scrub_report.json.json"` · `"scrub_report_v2.json"` | **WROTE** |
| `"Scrub_Report.json"` (case) | refused **only** because NTFS `exists()` folds — CI is `ubuntu-latest`, where it writes |

**Nine files rendering as one reserved name coexisted in a single directory.**
This is not recorded in any prior audit and is the strongest single argument that
a name authority is needed and that it must fold.

### 3.4 §12.17 limb 1 has no representation at all

`write_metadata_artifact(out_dir, name, payload)` takes `out_dir` as a free
caller argument. Accepted: `<repo>/artifacts`, `<repo>/artifacts/m15_gate3a`,
`<repo>/src/anywhere`, a path outside the repository entirely. Refused: the seven
`_PROTECTED_PREFIXES` roots, relative spellings, traversal. **Limbs 2 and 3 are
implemented and proven; limb 1 is absent.** `write_metadata_artifact` has **no
non-test caller**, so tightening it costs nothing today.

### 3.5 D-7's status authority has no operand for three of the eight

`cost_table_plan_or_metadata`, `no_overlap_proof` and `scrub_report` carry no
`status` — and their schemas **forbid** the key (`gate3a_undeclared_key:status`).
Two of those three are exactly what playbook §5 directs the continuation to
produce. Making D-7's status rule operative would require both a source change
and a committed-evidence change that **no clause pre-approves**.

### 3.6 Declaring a schema can weaken content control

| surface | max numeric leaves | max leaves |
| --- | --- | --- |
| declared `design_m15_inventory` | **441** | 820 |
| declared `no_overlap_proof` | 84 | 820 |
| declared `scrub_report` | 21 | 500 |
| undeclared backstop | 120 | 200 |

Routing an output at a reserved name is not automatically the stricter choice.
One of the three is looser than the backstop.

### 3.7 `_SCHEMAS` is also the directory manifest

`tests/m15_gate3a/test_recheck_fixes.py:898` asserts
`[p.name for p in paths] == sorted(EXPECTED_ARTIFACT_FILES)` — **set equality
between the schema table and the on-disk contents of `artifacts/m15_gate3a`**.
The code therefore already implements "the committed eight are the whole
namespace, and the namespace is that one directory". Any model registering a
continuation artifact in `_SCHEMAS` breaks this pin, and the cheap repair —
relaxing equality to a subset — silently destroys it.

### 3.8 Two output surfaces, not one

`write_metadata_artifact` refuses any name not ending `.json`, so the 20 derived
M15 `.jsonl` files cannot pass through it. They belong to the aggregation script
the derivation manifest records as `TO_BE_CREATED_AT_GATE5`, and PR #444 §11 says
the data root "is a runtime argument and is never committed". **This packet
governs the metadata-evidence surface only**; the derived-data surface is a
separate, currently ungoverned question and is named here so it is not assumed
covered.

### 3.9 The routing hole — the finding that governs all the others

**A surface contract that binds only `write_metadata_artifact` binds nothing**,
because a second writer reaches the same paths with none of its guards.

`scripts/ml_step4/evidence.write_report` — a function in the *same module*
`artifacts.py` already imports two names from (`scan_payload`, `serialise`, lines
144–145) — is one import away and carries no `refuse_real_path`, no name
validation, and a scrubber that legitimately permits metrics because `ml_step4`
evidence legitimately carries them. Executed in a synthetic sandbox root whose
`repo_root()` resolves inside the sandbox, so the protected prefixes were live:

| call | result |
| --- | --- |
| `write_report(artifacts/m15_gate3a, "design_m15_inventory.json", …)` | **overwrote a committed artifact, 2 138 → 16 bytes** |
| `write_report(docs/governance | data | models, "planted.json", …)` | **WROTE** into all three §12.18 protected trees |
| `write_report(artifacts/m15_gate3a, "../../escaped.json", …)` | **WROTE** — traversal *in the filename*, landed at the repo root |
| `write_report(artifacts, "planted_metrics.json", {"sharpe_ratio": 2.31, …})` | **WROTE** strategy metrics |

**This is not a defect in `ml_step4`**, which is a different package with its own
purpose, and it is **already disclosed** by `guards.py:22-25`:

> "Each guard is individually fail-closed on the input it is given. Nothing here
> asserts that a caller exists, that every write is routed, or that the package
> is therefore contained: **containment of an *unrouted* caller is not a property
> this module has, and must not be cited as one.**"

The disclosure is honest. The **contract** gap is that §12.17 is written as
though one writer exists. FR-18 closed the *re-export*
`artifacts.evidence.write_report`; the function itself is unchanged and
importable in one line — the programme's standing shape, where the printed
spelling was closed and the family left open.

**Consequence for the ruling:** any output-surface contract must carry a
**routing obligation** — that the continuation writes through exactly one
function and reaches no other write primitive — or it is an authority over one
function rather than over the artifact surface. That obligation is derivable from
`guards.py`'s own disclosure; what it must *name* as the sanctioned writer is
part of the same referral as the directory.

### 3.10 One capital letter defeats both existing identity defences

`resolve_schema` reads the declaration with `payload.get("artifact")` — an
exact-case dict lookup — while `_scan_declared` folds every key to lower case
before the allowlist test. The two disagree, and the gap is a complete bypass.
Executed:

| payload key | filename | result |
| --- | --- | --- |
| `artifact: "continuation_summary"` | `scrub_report.json` | `gate3a_undeclared_artifact_name` ✓ |
| **`Artifact: "continuation_summary"`** | `scrub_report.json` | **CLEAN** |
| **`ARTIFACT: "continuation_summary"`** | `scrub_report.json` | **CLEAN** |
| `artifact: "design_m15_inventory"` | `continuation.json` | `gate3a_artifact_name_mismatch` ✓ |
| **`Artifact: "design_m15_inventory"`** | `continuation.json` | **CLEAN** |
| `artifact: "scrub_report"` **+** `Artifact: "continuation_summary"` | `scrub_report.json` | **CLEAN** — two identities in one file, one invisible to the resolver |

**Both refusals that constitute the current identity defence are one keystroke
from off**, and the bypass is invisible to a green suite because `scan_gate3a`
returns `[]`. A human reading the JSON sees an artifact identity; a reader doing
`d["artifact"]` sees nothing. Any model keyed on the payload's `artifact` field
inherits this unchanged.

### 3.11 Directory identity is not a string

Measured on NTFS with 8.3 names enabled and junction creation available without
elevation: an `out_dir` that is an **NTFS junction** was accepted and the file
landed at the junction's target — and `os.path.islink()` reported `False` for it,
so a naive "is it a link?" clause does not see it. An **8.3 short-name alias** of
a long directory was likewise accepted. `resolve_candidate` does follow both, so
a rule comparing *resolved* paths holds where a rule comparing *strings* does
not; and the approved root must additionally be required to be a real directory
rather than a reparse point.

---

## 4. Options considered

| | A — fixed name allowlist | B — typed extensible surface | C — hybrid |
| --- | --- | --- | --- |
| Enforceable today | Nearly free; the tables exist | Nothing: no type, output-class, directory, required-key or provenance concept exists in `ArtifactSchema` | Name half free; type half not |
| Satisfies §12.17 limb 1 | **No** — a name roster is not a directory | Only if the tuple's directory element is enforced, which needs the missing concept | **Yes** |
| Fails closed on unknown names | Yes | Only if the type authority is itself closed and required | Yes |
| Invents a vocabulary | No | **Yes** — "artifact type" / "output class" appear nowhere in committed authority | Partly |
| Effect on future review class | Every new name is a Gate-decision | **Lowers** it: new names become ordinary Work PRs | Mixed |
| Existing-suite cost | Highest — breaks the never-overwrite pin's own fixtures | Breaks three roster pins incl. §3.7 | Moderate, mechanical |

**A is not foreclosed the way PR #449 assumed** (§2), but it does not answer
§12.17, which is about a *place*. **B lowers the amount of human review a
protected surface receives**, and under `CLAUDE.md` the stricter reading of a
research restriction wins. **C is the only shape that addresses both limbs.**

---

## 5. Recommended ruling — offered, not adopted

Structured as four slots so the ruling supplies the values.

**5.0 Routing — first, because without it the rest is advisory.** The
continuation writes every artifact through exactly one sanctioned function and
reaches no other write primitive, `scripts.ml_step4.evidence.write_report`
included. Pinned by an AST sweep over the continuation's own modules and by an
`open`-audit-hook test over a synthetic run. Derivable from `guards.py:22-25`'s
own disclosure; *which* function is sanctioned belongs to the referral.

**5.1 Identity.** An output's identity is its `ArtifactSchema`. The relation
name→schema is **n:1** and must stay so — `cost_table_plan_or_metadata.json`
declares `cost_table_plan`, so any 1:1 model breaks committed evidence on day
one.

**5.2 Declaration is mandatory at the write boundary, and is read case-folded.**
Every write must carry a non-empty `str` `artifact` that resolves to a registered
schema; any key folding to `artifact` counts, and two disagreeing declaration
keys are a hard finding (§3.10); the filename
must resolve to the same schema. All eight committed artifacts already satisfy
this, so the committed evidence is the negative control. **Sited at
`write_metadata_artifact`, not `scan_gate3a`** — 46 existing negative controls
call `scan_gate3a` with neither an `artifact=` nor a declaring payload, and
moving the rule there converts every one of them into a failure whose cheapest
repair is weakening the new rule.

**5.3 Names fold before they are judged.** A filename is reserved if its folded
form matches a reserved stem. Without this, §3.3's nine spellings all remain
writable and any "impersonation is forbidden" clause is unfalsifiable.

**5.3a Directory identity is compared resolved, never as a string**, and the
approved root must be a real directory rather than a reparse point (§3.11).

**5.4 Location carries lifecycle.** `artifacts/m15_gate3a/*.json` is adopted
evidence, reachable only by human-reviewed PR diff. One approved output root
holds proposed outputs. Same identity, same schema, different directory. This
invents no field and no name — but **the root's value is not derivable** (§6).

**5.5 The roster splits from the manifest.** §3.7's equality must be preserved
deliberately by separating the schema registry from the committed-directory
manifest, not by relaxing it.

**Explicitly not offered:** content bounding as any part of the answer. PR #449
§7.2 measured the residual at ~8,960 characters ≈ 82 OHLC rows. Content bounds
do not resolve a name or surface authority.

---

## 6. What only human + ChatGPT may decide

1. **The output root's literal path.** No committed clause names one. The repo
   convention is `artifacts/<gate-or-stage>/<run-identity>/`, and it carries at
   least three incompatible run-identity conventions. `artifacts/m15_gate3a_continuation`
   appears in PR #447 only as *an example of a path that currently ALLOWs* and in
   two test fixtures as a `script_name` string — **an illustration and a fixture
   string are not authority.**
2. **A hard constraint whoever names it must know:** `is_within` treats a
   directory as protected together with its whole subtree, so a root spelled
   *inside* `artifacts/m15_gate3a/` is permanently incompatible with D-7's trap.
   The root must be **disjoint** from every protected prefix, and its leaf must
   differ from every protected leaf.
3. **Whether the root is fixed, per-run or per-epoch.** PR #444 §1 says the first
   continuation "may well halt", and never-overwrite makes a directory one-shot —
   a single fixed literal strands the retry.
4. **Whether provenance is mandatory on metadata outputs, and its field list.**
   No committed definition exists for metadata artifacts; §11's four-field
   `DerivationBinding` is scoped to derived bytes.
5. **Whether `status` becomes mandatory**, given §3.5.
6. **Whether the `cost_table_plan` alias is retained (roster of nine) or retired
   (eight).**
7. **Whether a new output type needs a Work PR, a Contract Gate-decision, or a
   human-reviewed schema diff.** *The ruling sets the future review class:* A
   makes every new name a Gate-decision, B makes it a Work PR. Answering this
   silently would decide how much human review this surface gets.
8. **What happens if the continuation has no writable name** under a strict
   eight-name roster — ruled deliberately, not discovered at run time.

---

## 7. D-7 relation and review classes

D-7's clause is a **mechanism requirement (human-reviewed diff), not a
prohibition** — the error PR #449 corrected in its FR-12 disposition. Derived
classes:

| Change | Vehicle |
| --- | --- |
| Schema change whose semantics a merged Gate-decision already approved | **Work PR** (executed precedent: PR #449's FR-12) |
| Schema change whose semantics are not yet approved | **Contract Gate-decision**, then Work PR |
| Populating an artifact with measured values | **Execution-evidence PR**, post-approval |
| Adding a new artifact identity to the roster | **Contract Gate-decision** *under present authority* — but item 7 of §6 may change this |

---

## 8. Implementation requirements for the later Work PR

Carried, not closed, by this packet:

1. `_APPROVED_OUTPUT_ROOT` as a module-level constant, enforced inside
   `write_metadata_artifact` via `is_within` containment — never a string prefix,
   never conditional on repo-relativity (a conditional rule never fires in any
   test).
2. Mandatory declaration (§5.2) with its own finding token, distinct from both
   `gate3a_undeclared_artifact_name` and `gate3a_artifact_name_mismatch`.
3. Folded reserved-name matching (§5.3), with the nine spellings of §3.3 as the
   regression set.
4. The name check must run **after** every structural name guard, or it shadows
   five existing single-guard tests.
5. `artifacts/m15_gate3a` joins `_PROTECTED_PREFIXES` **in the same PR** that
   adopts the root, discharging D-7's trap; and a set-equality pin on the prefix
   roster in both directions — an addition to it is currently caught by nothing.
6. Playbook §5 must be amended in the same PR: it still names
   `artifacts/m15_gate3a` as the continuation's write target, which is the
   remaining half of the trap's precondition.
7. Re-engineer the RF-9 partial-write cleanup test, whose only vehicle is an
   over-long filename that a name roster would refuse earlier.
8. Enforcement of "never written": `effective_n_estimator_spec` and both forward
   artifacts are writable today — D-7's "never written" is a statement, not a
   mechanism.
9. The routing obligation (§3.9 / §5.0), without which items 1–8 bind one
   function rather than the surface.
10. The case-folded declaration read (§3.10) — the current identity defence is
    one capital letter from off.

**Two carried obligations that this ruling does not close:** the derived-data
surface (§3.8), and the gate-4 producer, which by §12.14 lives outside this
package and is therefore not bound by anything in `artifacts.py` unless a clause
says so.

**A collision to pre-empt:** `proof.MeasurementRecord` carries exactly **six**
immediate integer fields against §12.25 S1's cap of **five** — measured, a flat
serialisation refuses. The gate-4 record must nest. Raising the bound is
forbidden by PR #448 §5.5.5.

---

## 9. A divergence found while reading, outside this packet's scope

`design_m15_derivation_manifest.json` still declares
`"missing_minute_policy": "… per-file gap report (count + max gap) …"` while
`design_m15_inventory.json` now declares the six-field `minute_accounting`.
**Two committed authorities disagree about one quantity** — the R-2 failure mode
PR #449's own FR-12 fix was closing. Its semantics are already approved by PR
#444 §5, so it is a **Work PR** item; it is currently in no PR's scope and is
recorded here so the fifth audit does not have to find it.

---

## 10. Why this is `PENDING` and not `RULED`

Policy §14.2 reserves changing a research contract to a Gate-decision; §5
requires human + ChatGPT to merge an Amber PR and advance a gate; §12 forbids an
AI that performed an audit from giving final approval. PR #444 §0 forbids an
implementing session from introducing a value the contract does not contain — and
a directory name is exactly that. PR #448 §5.4(i) recorded that a Work PR
selecting between §12.25's two readings was *"ultra vires regardless of which
reading is right"*; this is stronger, because §12.17 limb 1 has no readings at
all, only a missing value.

The decisive precedent is PR #448 §9: the last question of this class was
prepared as a packet, and the human + ChatGPT ruling **did not select from the
option table** — it replaced the question with a provenance requirement. Four
roles and a re-executing lead did not predict that. An AI pre-setting `RULED`
here would be both improper and, on the record, unreliable.

If human + ChatGPT rule, **this same file** is amended to `RULED` with the
pending history preserved as history — the PR #448 pattern — and no second PR is
opened.
