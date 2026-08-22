# M15 gate-3a targeted fix — FB-1…FB-10, FR-1…FR-18, FR-20, FR-21

**Type.** Work PR (policy §14). **Risk tier.** Amber — protected paths under
`scripts/m15_gate3a/**`, `artifacts/**` and research machinery. Merging needs
human + ChatGPT approval.

**Authority.** PR #447 (`653a404`, the merged fourth independent source-audit,
verdict `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`),
PR #444 (`ea40d2f`, the contract) and PR #448 (`c7e477a`, the D-5.8 and §12.25
ruling). No contract is reinterpreted here; where this PR needed a contract
answer it took the one already ruled.

**Statuses, unchanged.** `PRODUCTION_READINESS_NOT_CLAIMED` ·
`NO_EXECUTION_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` ·
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`. Gate-3a continuation is
**not** authorised, and this PR grants **no** source-audit acceptance — closing
the findings is not the same as an independent re-check confirming they are
closed. The fifth independent source-audit has not been started.

---

## 1. What this PR is, in one paragraph

The fourth independent audit recorded ten blockers and twenty-one required
fixes. This PR closes them, and then closes what six internal audit roles found
wrong with those closures — which was substantial. **Four of the six roles
defeated a defence an earlier head of this same PR reported closed**, three of
them reproducing the exact defect class the merged audit had reported closed.
That is the fifth consecutive round of the same failure mode in this programme,
and it is the single most important fact in this document.

---

## 2. Disposition of every audit item

### 2.1 Closed by a structural fix

| ID | What was wrong | What the fix targets |
| --- | --- | --- |
| FB-1 / FR-3 | A subclass, then `object.__new__`, then — found by an internal role — **the exported `register_minted`** minted an authority-bearing record. The public API *was* the forgery route. | Sealing refuses subclassing at class creation; `register_minted` verifies that its calling frame is the record's own `__post_init__`. |
| FB-2 | The writer validated one read of the caller's object and published another. | `snapshot_payload` reads the caller's object exactly once through unbound slots; everything downstream decides against plain built-ins. |
| FB-3(a) | A dataset re-typed into text. Closed three times and re-opened three times: the printed 328 KB payload, then 412 KB of hex once the per-leaf limbs landed, then 244 KB of letters-only base32 once the hex excision was narrowed. | The **token**. Prose has words — the longest in any committed artifact is 14 characters — and an encoded dataset has one enormous run, because separators are what it cannot afford. Bound at the sha256 width the committed schema itself declares, plus an aggregate text budget derived from `PAIRS_20` and the longest committed string. |
| FB-3(b) / (c) | Metric roots in run-together keys; declared numeric keys carrying values from another domain. | Dense-form root matching; value-domain binding taken from the committed artifacts. |
| FB-4 | Containment failed **open** on an absent protected root, and the creating write landed inside the real tree. Closed for the trailing-dot family, then found open for four namespace spellings — extended-UNC, admin share, volume-GUID, GLOBALROOT — which `resolve()` does **not** canonicalise. | An allowlist: only an ordinary local drive path is addressable. The verdict no longer depends on filesystem state for any spelling it owns. |
| FB-5 | Seven comparisons answerable by the caller's own object. | One `_pin_text` primitive over unbound slots, at 24 call sites; `_pin_instant` added for `datetime`. |
| FB-6 | `asdict`/`astuple` republished the gated identity map. Closed — and then `ProofResult().__getstate__()` returned it as element 9, because a `slots` dataclass **generates** that member and the fix had enumerated the other three. | The protocol is refused, not the printed route: `__getstate__` and `__setstate__` join `__copy__`/`__deepcopy__`/`__reduce__`. |
| FB-7 | The confusable fold was a two-script denylist. Replaced by "any non-ASCII **letter** is a finding" — which is a `unicodedata.category` denylist, and 19 of 24 labels fell to one non-letter codepoint. | The rule now targets the **deletion**, not the codepoint: a separator run between two retained characters, every character of which is non-ASCII, is invisible to the reader and a separator to the scanner. Applied to keys as well as values. |
| FB-8 | §12.14's mandated reader-freedom and reverse-caller pins did not exist. Written — and then defeated fifteen ways, including three mutations the pins' own docstrings named as what they killed. | Every root cause replaced: imports walked at any depth; primitives matched as **references** not callee names; `getattr` arguments statically enumerable; recursive module sweep; `PACKAGE + "."` boundaries; all first-party roots; whole-repo reverse-caller sweep resolving relative, `importlib` and `__import__` spellings. |
| FB-9 / §12.25 | Declaring a schema bought *less* shape scrutiny than declaring none. | S1 as ruled, uniform across both scans, with the flattening limb independent of the count. The declared-block exemption is bounded by the schema's own declared block-key count rather than returning early. |
| FB-10 | `WarmupPolicy.validate()` swallowed the numeric refusal. | Pin first, let the refusal out, delete the `isinstance` pre-checks. |
| FR-1 | A prohibition-list exemption inherited by a whole subtree. | Per-item exact membership. |
| FR-4 | The CV limb bound coverage to the byte scan by cardinality alone. | `PairCoverage` carries the certified span; both endpoints are compared, each raising separately, both sides read through `_pin_instant`. **Stated as a narrowing, not a closure** — endpoints are bound, the set is not, and that needs a producer-side set digest at gate 4. |
| FR-7 | `content_digest` was shape-checked and never bound to content. Closed — and then found **not injective**: `name=value` joined by newlines, with newlines permitted inside the values, let two different calendars collide from plain JSON. | The canonical rendering is length-prefixed, which is injective whatever the content holds. A denylist of separator characters would have been the same defect one round later. |
| FR-10 | `TimestampError` leaked where `NoOverlapError` was documented. | One publication chokepoint. |
| FR-13 / FR-14 | Frozen boundary constants and the dead-window inclusive bound unpinned. | Parametrised against the committed evidence block; mutation-verified. |
| FR-15 | Honest denials were refused as claims. Fixed with `dense[:start].endswith(negator)` — a **character**-suffix test over a form with no separators, so `casino PRODUCTION_READY` and `UNBLOCKED_PRODUCTION_READY` wrote to disk clean. | The negator is read as a **word** in the folded text. Honest denials stay writable; the rule is fail-closed in both directions rather than anti-correlated with its own semantics. |
| FR-16 | The package could not list its own byte-level tokens in a prohibition list. | Exact membership, so the entry-length window did not have to widen. |
| FR-17 | A quadratic scrubber pattern; a 306 KB value did not return in 110 s. | Fixed at the **root**, in `scripts/ml_step4/evidence.py`: the pattern had no left boundary. A lookbehind makes it linear — 5.56 s → 0.0008 s at 32 000 characters, verdict parity checked across six cases. This is why the scoped suite went from 757 s to 22 s. |
| FR-18 | A second writer re-exported into the gate-3a namespace. | Private aliases. |
| FR-20 | Seven `# pragma: no cover` on reachable guards. | Removed — and two more, whose stated premise contradicted this package's own declared threat model, removed after an internal role reached both branches. |
| FR-21 | Nineteen mutation survivors. | Closed, including the two in `effective_n.py` that no workstream owned. |

### 2.2 Closed, with the authority corrected

**FR-12** — the committed inventory still declared the superseded two-key
`gap_report`. An earlier head of this PR recorded it as "D-7 territory, human
diff only". **That disposition was wrong**, and an internal role showed why: PR
#444 §5 says the six-field schema change "is approved by this Gate-decision;
implementation lands in the targeted-fix Work PR", and D-7's human-reviewed diff
is exactly what a Work PR is. `artifacts/m15_gate3a/design_m15_inventory.json`
now declares the six-field `minute_accounting` and §12.20's rename to
`complete_bucket_count`. All eight committed artifacts still scan clean.

This is the one committed-artifact change in this PR and it is called out here
so a reviewer does not have to find it in the diff.

### 2.3 Not closed, each with its authority

| ID | Why not |
| --- | --- |
| FR-9 upper bound on `observed` | No committed authority bounds it. Inventing one would decide market hours, which D-6 forbids. |
| FR-11 across a *fresh* evidence set | Needs persisted status, which a reader-free layer cannot hold. Terminality **per evidence object** is enforced — including for `ConsumerRecheck`, which was being marked and never read. |
| FR-19 | Out of scope by instruction: it belongs to a separate test-safety Work PR. |
| §12.17 separate output directory | Never-overwrite is enforced; the output-directory concept is not implemented. Classified FO-1 by the merged audit. |
| FB-3(a) residual | Within the aggregate budget an author can still encode a few kilobytes, and no scrubber can distinguish opaque text from prose. Two orders of magnitude removed, not eliminated. |
| FR-8 second limb / D-5.8 §4.7.2 | A caller who materialises the rule one line earlier and passes the set is not refused. **This cannot be closed inside a reader-free package** — refuting it means comparing against the committed artifact's real bytes, and §12.14 keeps this package reader-free with "P and V live outside it". The source docstring that claimed "no adjacent rule form escapes it" has been corrected to say the opposite. **Citation corrected:** an earlier draft said PR #448 §4.7.3 "places the mechanism at the byte-reading V package". It says the opposite — the *provenance mechanism* is "implementation work for the targeted-fix Work PR, bounded by requirements 1–4", and that work was done here (provenance block, digest binding, epoch binding, requirement-3 fail-closed). What §4.7.3 does not do is close the residual, and the control that actually stands against a forged calendar is `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`, which remains an open pre-continuation gate. |

---

## 3. False guarantees withdrawn

A docstring that claims more than the code does is a finding in its own right,
and this programme has now shipped several. Each of these was stated as fact at
an earlier head of this PR and is false:

- `sealing.py` — "you must reach into module privates" to mint. `register_minted`
  was **exported**; the route was one public call.
- `proof.py` `_limb_cv` — said FR-4 was open and unimplementable on this side of
  the boundary, while the code eighty lines below closed it.
- `proof.py` `_IdentityVault` — "reachable only through `open_for_consumption()`".
  `__getstate__` reached it, and `gc.get_referents` still does; both are now named.
- `calendar_authority.py` — "no adjacent rule form escapes it". The adjacent form
  escapes it completely.
- `path_authority.py` — "filesystem state makes this authority stricter and never
  more permissive". A junction inside a protected tree turns a REFUSE into an
  ALLOW; the claim is withdrawn rather than qualified.
- `artifacts.py` — "every string reaching the base scanner is at most
  `_MAX_TEXT_CHARS` long". It is handed the whole document as one string.
- `calendar_authority.py` — "two records describing different calendars cannot
  carry the same digest". They could, from plain JSON.

---

## 4. Verification

**Suites.** Scoped `tests/m15_gate3a/` — **1589 passed, 1 skipped** (the skip is
symlink creation, unavailable on this host). Full repository — **6070 passed,
40 skipped**, confirmed stable across three consecutive runs. Every skip is a
test-safety opt-in gate behaving as designed: 27 database tests behind
`RUN_DB_INTEGRATION_TESTS`, 10 research-data tests behind
`RUN_RESEARCH_DATA_TESTS`, one optional heavy-model test, the symlink test and
one that needs a shared console. Enumerated rather than counted, because "the
presence of a `.env` is not authorization" is the control this repository
learned the hard way.

**CI (`ubuntu-latest`, the authority).** `test` — **6065 passed, 45 skipped**;
`contract-tests` — **553 passed, 1 skipped**. Both green at head `395e217`. The
Linux/Windows skip difference is platform-gated tests, not a gate that stopped
firing; the five FB-4 namespace tests assert the refusal *reason each platform
actually gives*, because on POSIX a backslash is an ordinary filename character
and those spellings are relative paths rather than aliases. CI being Linux-only
means the Windows half of that family is asserted on the developer host and not
in CI — stated here rather than left for the next audit to find.
`ruff check`, `ruff format --check` and `tools/lint/run_custom_checks.py` clean.

**Mutation.** A consolidated battery over the twenty guards this PR adds or
changes: **18 killed, 2 equivalent, 0 genuine survivors.** The two equivalents
are proven, not assumed — narrowing the hex excision is unobservable because any
run wider than a digest is already refused by the token bound, and the UNC branch
of the namespace rule is subsumed by the drive-letter branch. Both are kept as
defence in depth. Nineteen further mutations against the reader-freedom pins were
run separately and all killed, with the unmutated baseline confirmed green each
time and `__pycache__` purged before and after every run.

**The first pass of that battery killed only twelve of twenty.** Six survivors
were call sites whose primitive was tested and whose *use* was not — and one was
worse: the recheck-refutation guard tested for a `Mapping` when rechecks arrive
as a sequence, so it never executed. The test written to pin it is what found
that. A green suite predicted conformance at neither pass.

---

## 5. Internal audit

Six independent roles, each given the source, the diff and the contract, none
given another role's conclusions: contract/specification conformance;
adversarial/bypass; proof-layer and import graph; tests and mutation;
filesystem containment and scrubber; FB/FR disposition verification. Two further
perspectives — implementation review and final integration — were run by the lead
against the reconciled findings.

**Findings adopted as blockers, all reproduced by the lead before acting:** the
FB-7 non-letter fold class; the FR-15 suffix test; the exported `register_minted`;
the `__getstate__` vault leak; the FB-3(a) chunked payload; the FB-4 namespace
family; the reader-freedom pin gaps. **Required fixes adopted:** the digest
injectivity defect, the double read of the expected slot set, the unpinned
`artifact_id` / conjunction keys / FR-4 span endpoints, the unread recheck
ledger, the unbounded block exemption, two reachable pragmas, a one-valued
`provenance_basis`, five dead copy handlers and one dead export.

**Where the lead did not simply adopt a role's conclusion.** One role graded the
declared-block exemption against a bound of six; the producer's real `gap_report`
legitimately carries nine, so the bound is the schema's declared block-key count
instead. Two roles asked for `no_overlap`'s `result` token to be deleted under
R-1; §11's token discipline **requires** a declaration-only token to exist, and
unlike the cost-schema field it replaces, its value is a denial — it stays, and
the reasoning is now in the source rather than implied.

**Disagreement resolved on evidence.** Role 7 said the FR-12 disposition cited
the wrong authority. The lead read PR #444 §5 directly, found the role correct
and the earlier head wrong, and implemented the schema change.

**Head drift during the audit.** Three roles disclosed that the working tree
moved while they ran. Their findings are against `ef6539e`; every one of them
was re-verified by the lead against the current head before being acted on, and
the fixes made after their reports are covered by the mutation battery in §4
rather than by their passes.

---

## 6. What a reviewer should be most sceptical of

The honest answer is the pattern, not any single item. Five rounds running, this
programme has produced fixes that close the payload an audit printed and leave
the family open, and the suite was green at every one of them. Three of the four
blockers found in this round were re-openings of defects a *previous* round had
recorded as closed. Two of the defects fixed here were created by this PR's own
earlier fixes.

So the specific claims worth attacking are the ones shaped like the previous
failures: that the fold rule is now structural rather than a denylist one
category over; that the token bound is not simply the next chunk size waiting to
be found; that the namespace allowlist covers a namespace nobody has named yet;
and that the reader-freedom pins, having been defeated fifteen times, are not
defeatable a sixteenth. Each is argued in source and mutation-tested, and none of
that is the same thing as an independent session re-deriving it.

**Next gate: the fifth independent source-audit re-check, in a separate
top-level session.** Not started here.

---

## 7. Final disposition audit (read-only, at head `0a744e6`)

A separate pass over the residual items, to establish whether each is genuinely
deferrable with authority rather than a blocker wearing a defer label. Every
behaviour below was executed against a `git archive` extract of this head; none
of it is taken from §2.

### 7.1 A scope defect found and fixed in this pass

`git add -A scripts tests artifacts` in `f184fe5` staged **183 previously
untracked files** under `artifacts/` — pre-existing research logs and
`artifacts/stage29_0b/**`, 406 000 lines, inside a protected path, with no
relation to this objective. That is a policy §14 violation and it was mine.
They are removed from the index and left on disk untouched (`0a744e6`); the net
diff is again 30 files. All 183 were verified restored to untracked.

### 7.2 Dispositions

**FR-12 — `FIXED_BY_APPROVED_SCHEMA_IMPLEMENTATION`.** PR #444 §5 approves the
six-field schema and assigns implementation to the targeted-fix Work PR; D-7's
human-reviewed diff is what this PR is. The diff adds exactly §5's six normative
fields and §12.20's rename — no invented field, no invented semantics — and two
tests pin the committed shape, one of them against
`coverage.MINUTE_ACCOUNTING_FIELDS` so the two authorities cannot drift.

**FR-9 — `DEFERRED_NO_COMMITTED_UPPER_BOUND_AUTHORITY`.** No committed clause
bounds `observed_source_minute_count` above. Bounding it decides whether a source
record may exist outside market hours: D-6.1 forbids inferring closure from data
and D-6.3 forbids synthesising it. Executed — every *derivable* relation still
bites (`expected = usable + absent + rejected`, `observed >= usable`,
`max_gap <= absent + rejected`, each refusing with `MinuteAccountingError`); only
the upper bound is open, and the count remains a diagnostic.

**FR-11 — `DEFERRED_TO_PV_READER_GATE`.** Cross-evidence terminality needs
persisted status; §12.14 keeps this package reader-free with "P and V live
outside it". Executed — the layer mints no byte-level token (all three are
refused as values), `evaluate_four_limbs` returns `BYTE_LEVEL_PROOF_PENDING` with
`files_opened=0` and `bytes_measured=0`, and terminality *per evidence object* is
enforced, including for `ConsumerRecheck`, which this PR found was being marked
and never read.

**FR-8 second limb — `SECOND_LIMB_DEFERRED_TO_GATE4_BYTE_READER`.** Authority is
§12.14 plus the open gate `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`
— **not** §4.7.3, which assigns the provenance *mechanism* to this PR (see §2.3
for that correction). The layer does not pretend the limb is satisfied: pending
status is maintained and no byte-level claim is writable.

**§12.17 — limb 2 `FIXED`, limb 3 `FIXED`, limb 1 `REQUIRES_CONTRACT_DECISION`.**
Executed: a second write to the same path is refused, and `docs/`, `data/`,
`models/` and both PR-B.1 trees are all refused as write targets. Limb 1 says
"**Continuation** outputs go to a separate output directory" — the continuation
is unauthorised and not performed, and D-7's trap sequences directory adoption
*before* adding `artifacts/m15_gate3a` to `_PROTECTED_PREFIXES` (verified absent,
so the trap is unsprung). No committed clause names the directory, so adopting
one here would invent an unapproved value. The merged audit classifies this FO-1,
non-blocking — **and it also says the limb "was handed to this Work PR and is not
started", which is accurate and is not softened here.** It is a pre-continuation
gate item, alongside the calendar-artifact approval.

**FB-3(a) residual — `NON_BLOCKING_BY_COMMITTED_CONTRACT`.** Measured, not
asserted. Three bounds, each derived from committed authority: per-leaf 499
(byte-identical to the longest committed string value), per-token 64 (the sha256
width `design_m15_inventory.json` declares), aggregate 9 980 (the frozen 20-pair
universe times the longest committed string). The audit's own 2 000-row payload
is refused on three limbs and the write raises. The strongest surviving encoding
— pure A–Z, tokens under 64, respecting every bound — carries **8 960 characters,
about 5.3 KB, about 658 float64 values, about 82 OHLC rows**, against the 2 000
rows and 328 096 bytes FB-3(a) reported. This is not offered as "smaller, so
acceptable": it is what follows necessarily from the contract permitting
free-text descriptive fields at all, which it does — a 499-character prose
`rationale` is committed evidence. Reaching zero requires a contract change
forbidding free text, which is not this PR's to make.

**Unknown artifact names — `REQUIRES_CONTRACT_OR_SCHEMA_DECISION`.** Two of three
routes are fail-closed: an unknown name in the payload's `artifact` field raises
`gate3a_undeclared_artifact_name`, and a known field written to a different
filename raises `gate3a_artifact_name_mismatch`. The third is open — a payload
that **omits** the field is writable to any `*.json` name and falls to the
undeclared backstop. Executed at base `c7e477a` and at this head: **identical**,
so this PR neither introduced nor widened it. Case A (roster-strict) cannot
simply be applied, because §12.17 contemplates *continuation outputs* that are by
definition not among the committed eight, and no clause names or types them. This
is the **same missing decision as §12.17 limb 1** — what the continuation's output
surface is — and the two should be settled in one Gate-decision before the
continuation. Content bounding is not offered as a substitute for the name
boundary.

**FR-19 — `SEPARATE_TEST_SAFETY_WORK_PR`.** Out of scope by instruction; not
implemented, not claimed, not present in the diff.

**Windows FB-4 coverage —
`NON_BLOCKING_PLATFORM_VALIDATION_GAP_FOR_NEXT_INDEPENDENT_AUDIT`.** The
namespace tests exist in source and run on both platforms, asserting the reason
each actually gives; CI is `ubuntu-latest` only, so Windows runtime behaviour is
exercised on the developer host and not in CI. No static Windows bypass is
visible in `_reject_non_drive_namespace`: measured via `os.path.splitdrive`, the
drive-letter branch alone refuses all four namespace spellings, so the UNC branch
is redundant rather than load-bearing.

### 7.3 Structural fixes re-verified at this head

FB-1 subclassing refused at class creation · the registry refuses a public mint
and reports `is_minted=False` · FB-2 a two-faced dict yields the validated face ·
FB-4 volume-GUID refused · FB-7 the non-letter homoglyph reported as
`gate3a_non_ascii_join` · FB-10 `validate()`, `is_event_eligible` and
`as_metadata` all refuse a `__class__`-spoofed int that answers `__index__`, with
the honest control eligible at bar 24 and not at 23.

**True residual source blockers: 0.** Two items require a Gate-decision before
the continuation — §12.17 limb 1 and the artifact-name surface — and they are one
question, not two. Neither is a defect in this PR's code, and neither is
discharged by merging it.
