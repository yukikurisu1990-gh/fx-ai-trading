# M15 gate-3a targeted fixes — B-1…B-7, RF-1…RF-29, and the RULED contract

- **PR kind:** Work PR (policy §14) — source, tests, docs, internal audit and CI
  repair in **one** PR, one objective.
- **Risk tier:** **Amber** (`scripts/m15_gate3a/**` is a protected path).
  **Not self-mergeable.** Merging requires human + ChatGPT approval.
- **Base:** master `ea40d2f` (the merged contract Gate-decision, PR #444).
- **Status:** `M15_AGGREGATION_DATASET_MACHINERY_TARGETED_FIXES_PROPOSED`
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
  · `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
  · **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`**
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Gate-3a continuation: **NOT authorised.** **This PR does not grant itself
  source-audit acceptance** — that is a separate independent re-check.

---

## 1. What this PR does

Closes the seven blockers and twenty-nine required fixes recorded by the merged
third independent source-audit re-check (PR #443), and conforms the source and
tests to the twenty-five normative requirements ruled by the contract
Gate-decision (PR #444 §12).

Three modules are new and **reader-free**: `calendar_authority.py` (D-6
validation interface), `coverage.py` (D-5 set equality), `proof.py` (D-11 token
vocabulary and the four-limb conjunction).

**Scope boundary, stated up front.** PR #444 §15.4 places the byte-reading
**producer/verifier packages at gate 4** — a separate synthetic-only PR *after*
the next independent re-check. This PR therefore implements the **reader-free**
half of the byte-level proof: the token vocabulary with promotion structurally
forbidden, the four-limb conjunction evaluated over caller-supplied measurement
records, producer/verifier agreement, consumer re-verification, coverage set
equality, and the calendar validation interface. `scripts/m15_gate3a/**` remains
**reader-free** (§12.14), re-verified by AST sweep: **zero** read primitives.

---

## 2. Contract conformance — PR #444 §12

| § | Requirement | Conformance |
| --- | --- | --- |
| 1 | Crossed quote → refuse; bucket and file not certifiable; no correction, no drop-and-continue | `aggregation._assert_not_crossed` raises per field pair; the drop-and-count loop is **deleted** |
| 2 | `ask == bid` is not a crossed quote | comparison is `<`, never `<=`; pinned both ways |
| 3 | Duplicate minute → fail-closed abort; canonicalise first; no silent dedup; claim before disposition | retained and pinned, incl. nanosecond-differing and alias duplicates |
| 4 | Zero rejection tolerance, structural | no tolerance parameter, default or ratio comparison exists anywhere in the package |
| 5 | Six-field minute accounting + identity | `minute_accounting` emits all six; `expected == usable + absent + rejected` **asserted in code** |
| 6 | `missing_minute_count` never a certification authority | retained with its meaning stated at the emission site; `coverage.py` refuses it as evidence |
| 7 | A certified bar requires all contract-required minutes usable | `complete_bucket` = 15 distinct usable minutes |
| 8 | Coverage = set equality; token = 20-pair conjunction | `coverage.assert_full_coverage`; no report-only mode, no tolerance parameter |
| 9 | Calendar-authority interface; fail closed; **do not author a calendar** | `calendar_authority.py` validates an **injected** artifact; **no calendar authored** |
| 10 | Never infer closure from absent data; no synthetic bars | `expected_minutes` is injection-only; `None` yields `None`, never `0` |
| 11 | Hashing is a byte read; proof subject is the derived artifact | no raw-source hashing anywhere; subject pinned to derived artifacts |
| 12 | Co-measure from one stream; verifier re-measures; consumer re-verifies; disagreement fail-closed | `proof.MeasurementRecord` requires identical per-quantity provenance; producer/verifier must agree; `consumer_rechecks` required |
| 13 | Separate declaration-only and byte-level tokens; **promotion forbidden** | five structural barriers (§4 below) |
| 14 | Keep the package reader-free; pin import direction | AST sweep: **zero** read primitives; `no_overlap` has **no import edge** to `proof` |
| 15 | Aggregate assertions are measured conjunctions; missing measurement unsatisfied | `CoverageMeasurementMissingError`; `measure_pair_coverage(rejected_slots=…)` is **required, not defaulted** |
| 16 | Cost-table 20×3 **raises** | `validate_cost_table` raises and names each missing cell |
| 17 | Continuation outputs to a separate directory; never overwrite protected evidence | writer refuses an existing target; `artifacts/m15_gate3a` deliberately **not** blanket-protected (D-7) |
| 18 | Protect `data/`, `models/`, `docs/`, both PR-B.1 trees; cwd-independent | all five added; relative paths now **refused** (fail-closed branch of D-7) |
| 19 | Negative-control rule on every attested boolean | eleven vacuous attestations **deleted** (§5 below) |
| 20 | Pin the terms; `eligible_event_count` → `complete_bucket_count`; declare the quantity | done at the measurement layer; `effective_n(count_quantity=…)` mandatory, admits only `raw_traded_event_count` |
| 21 | Record-identity guard in aggregation | `id()` guard mirroring `no_overlap._materialise` |
| 22 | Emit `spread_open` | emitted, finiteness- and sign-checked, value-pinned on JPY and non-JPY |
| 23 | Canonical `…Z` emission; refuse non-zero sub-microsecond on ingest | `timeutil.format_utc_z`; zero-only excess digits accepted, non-zero refused |
| 24 | Correct the false "package's own invention" docstring | corrected; `stage25_0a` removed as cited authority |
| 25 | Inventory must be writable; assert before any derivation | the allowlist accepts a populated 20-record inventory **nested or flattened**, and the eight committed artifacts |

---

## 3. Blocker disposition — B-1…B-7

| ID | Disposition | Evidence |
| --- | --- | --- |
| **B-1** | **Fixed** — shape denylist replaced by a per-artifact **allowlist** with derived (never chosen) cardinality budgets, plus confusable/zero-width folding and substring claim scanning | 300 rows as dict-of-dicts: `ACCEPTED` → **REFUSED**; prose claim, `status=PRODUCTION_READY`, Cyrillic-А, zero-width `PASS`: all `ACCEPTED` → **REFUSED**; the mirror defect closed — a prohibition list and a columnar roster are now writable once declared; all 8 committed artifacts still clean |
| **B-2** | **Fixed at the contract layer; discharge is gate 4 by §15.4.** Token discipline, the four-limb conjunction, co-measurement, verifier agreement and consumer re-verification are implemented reader-free. The byte-reading producer/verifier that can actually *discharge* the proof is the next gate — by ruling, not omission | declaration-only token + `evidence_basis`, `files_opened: 0`; promotion structurally impossible |
| **B-3** | **Fixed** — parse once, check and publish the same objects | before: token emitted beside a published `ts_max` of `2026-03-01T11:00:00+00:00` (inside the dead window); after: `2026-02-28T12:00:00+00:00`, `utcoffset()` calls 4 → 2 |
| **B-4** | **Fixed** — crossed quotes are hard fail-closed per D-1; drop-and-count deleted | before: `{'n_source_bars': 14, 'eligible': False, 'dropped_crossed_quote_rows': 1}` and all four crossed tests `DID NOT RAISE` |
| **B-5** | **Fixed, with one residual** — `data/`, `models/`, `docs/`, both PR-B.1 trees protected; `Path`-subclass pin; cwd-independence. **Residual:** when a protected root is *absent*, only the name limb runs, so an alias spelling of that root is not caught (§7) | before/after refusal matrix reproduced by the lead |
| **B-6** | **Resolved by committed authority** — referrals 2/3/4 were RULED in PR #444; this PR implements the rulings | PR #444 §3–§5 |
| **B-7** | **Fixed** — both epoch limbs isolated with unique messages; all four status constants pinned by equality and by non-forbiddenness | before: nulling either limb left the suite green (zero mutants killed) |

---

## 4. How promotion is structurally prevented (D-11)

Not by comment — five independent barriers:

1. **No import edge.** `no_overlap.py` imports nothing from `proof.py`, so no
   byte-level string is reachable from the declaration path.
2. **Distinct types.** `DeclarationRecord` and `MeasurementRecord` are separate
   frozen dataclasses with no coercion path; a declaration record is refused by
   type.
3. **Co-measurement gate.** A `MeasurementRecord` cannot be constructed without
   four per-quantity provenance values that must be *identical* — declared
   metadata cannot supply a byte-stream pass it never made.
4. **Import-time spelling guard.** A declaration-only token must end
   `__NOT_BYTE_LEVEL` and must not contain `PROVEN`. **This was added because the
   implementer's own first mutation run found the token rename survived** — every
   check had been written against the constant rather than against what the
   string says.
5. **Single mint site.** Claim tokens are returned only by
   `evaluate_four_limbs`, after BI ∧ TC ∧ CV ∧ DB.

---

## 5. Negative-control rule (§12.19 / R-1)

Eleven attestations that could only ever hold one value were **deleted, not
reported**: `imputation`, `synthetic_weekend_bars`, `mid_price_constructed`,
`dropped_crossed_quote_rows`, `rows_retained`, `buckets_fully_dropped`,
`all_rows_dropped`, `strategy_metrics_computed`, `p95_diagnostic_present`,
`real_spreads_computed`, `first_w_bars_event_eligible`, and **`dead_window_loaded`**
— the T-1 leakage claim emitted as a constant. `full_20x3_coverage` was deleted
too: the RF-19 fix made it incapable of ever being `False`, i.e. **the fix
created a vacuous field in the same edit that closed one** — precisely the class
PR #442 produced four of. `warmup` gained genuinely measured replacements
(`is_event_eligible()`, `loads_pre_forward()`).

---

## 6. Required-fix disposition — RF-1…RF-29

All twenty-nine are **Fixed**. Grouped by what closed them:

- **Source defects fixed** — RF-1 (ISO comma **and** the offset fraction, which
  `.search` never reached), RF-3, RF-4, RF-5, RF-6, RF-7, RF-8 (truthiness →
  closed denial vocabulary), RF-9, RF-10, RF-11, RF-12, RF-13, RF-14, RF-16,
  RF-17, RF-18, RF-19.
- **Documentation defects fixed** — RF-2 (the `timestamp()` cross-check
  guarantee restated truthfully), RF-15 (`guards.py` and `artifacts.py`
  docstrings now claim only what is true).
- **Coverage gaps closed where the source was already correct** — RF-20, RF-21
  (source-text test rewritten behaviourally; **verified** it now kills both a
  guard-deletion and a bare-`assert`-under-`-O` mutant, which the old form killed
  neither of), RF-22 (non-vacuity floor), RF-23, RF-24, RF-25, RF-26, RF-27,
  RF-28, RF-29.

---

## 7. Residual blockers and unresolved questions

Recorded rather than quietly closed.

1. **B-5 residual — absent protected root.** When a protected root does not exist
   there is nothing to be identical *to*, so only the name limb runs and an alias
   spelling is not caught. Every protected root is present in a checkout, so the
   degraded path is unreachable in practice — **but that is a property of the
   tree, not of the guard.** The test that previously *certified* this fail-open
   has been replaced by one asserting only the refusal (audit §9 AP-5).
2. **`no_overlap`'s dead-window limbs are unreachable dead code.** `DEAD_START`
   is one second after `DESIGN_END` and `_DEAD_END_EXCLUSIVE == FORWARD_FLOOR`,
   so both limbs are unreachable while the frozen constants hold — proven by
   mutation (nulling **both** leaves the suite green, so no test can name
   either). Retained as defence-in-depth against a constant edit, now explicitly
   documented and `pragma`'d with that reasoning. **This is why the removed
   `"dead window|DESIGN_END"` alternation looked like coverage: it was passing on
   the ceiling limb.**
3. **`eligible_event_count` term split.** §12.20 pins the measured quantity as
   `complete_bucket_count`, which `aggregation.py` now emits. The committed
   `design_m15_inventory.json` still declares `eligible_event_count`, and
   `no_overlap.schema_keys_not_verified` quotes that artifact **verbatim**.
   Renaming the key in code would desynchronise the list from the artifact it
   names. The rename lands with the inventory schema extension at the
   continuation — recorded, not silently reconciled.
4. **Two structural residuals reported for relocation, not fixed here.** A
   host-zone source scan has no runtime observable and does not belong in
   `tests/`; a compiled-code-object rule covering all 14 modules (versus the old
   text scan's 4) is proposed for `tools/lint/custom_checks.py`, which this PR
   does not own.
5. **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` remains open.** The
   interface is implemented and fails closed on a missing / malformed /
   unapproved / wrong-epoch calendar; a validated calendar reports
   `approval_basis = APPROVAL_DECLARED_BY_ARTIFACT__NOT_EVIDENCE_THAT_APPROVAL_OCCURRED`.
   **No calendar artifact was authored and no market-hours time was decided.**
6. **Referrals 1 and 5 remain `MAY_DEFER`** — not escalated. `max_spread_pips`
   stays required-with-no-default and may be `None`; no magnitude ceiling was
   invented.
7. **Nothing was referred as `Requires separate contract Gate-decision`.** Every
   item was implementable from the RULED text as written.

### Foreseeable consequence, restated

D-1 + D-2 + D-5 are strict by design. On real data the first continuation may
halt on a single crossed quote, a single rejected minute, or a coverage set that
is not exactly equal. **That halt is the designed outcome**, and resolving it
requires a new contract Gate-decision informed by approved measurement — never an
implementer's relaxation. Nothing in this PR softens that.

---

## 7a. Internal multi-agent audit (policy §13)

Roles, none given another's conclusions: **implementation** (five parallel
workstreams with disjoint file ownership) · **contract/specification** ·
**adversarial/bypass** · **tests/mutation** · **data-integrity/proof-design** ·
**containment/security**. The lead reproduced every blocker itself before
accepting it, and rejected none of the audit's substantive findings.

**The audit found the fix defective, and the fixes below were made in response.**

| Finding | Disposition |
| --- | --- |
| **The byte-level `PROVEN` token was minted inside package C** — found *independently* by the contract role and the data-integrity role. §11 fixes C's maximal claim at the declaration-only token; the note's original "§15.4 deferral" framing was the convenient reading, not the correct one (§15.4 defers the *reader*) | **Closed.** No code path returns a claim token. Best outcome is `BYTE_LEVEL_PROOF_PENDING` with `claim_withheld_because = NO_REGISTERED_BYTE_READING_COMPONENT_EXISTS…`; all four limbs still evaluate and still fail closed |
| **A `ValidatedCalendar` could be hand-built** with `authority="THE OBSERVED DATA ITSELF"`, `slot_source_field="reverse-inferred from observation"` — defeating D-6.1's single "Never" (lead-reproduced) | **Closed.** One-shot construction tokens, *spent* on first use so `dataclasses.replace` cannot re-mint from a real record |
| **`assert_full_coverage` was satisfied over a slot set lying entirely inside the consumed dead window** (lead-reproduced) | **Closed.** Dead-window and design-epoch slot refusal; `assert_full_coverage` and `_limb_cv` re-check invariants rather than trusting the type |
| **The emitted record asserted `MEASURED_FROM_DERIVED_ARTIFACT_BYTES…`** while measuring nothing — B-2 relocated into the new module | **Closed.** `evidence_basis`, `files_opened=0`, `bytes_measured=0`, `declared_not_measured` now reach the return value |
| **Coverage never read bar certifiability** — 20 pairs of `complete_bucket=False` bars gave `COVERAGE SATISFIED` (§12.7) | **Closed.** Reads each bar's own fields, not the caller's totals |
| **§12.23 unconformed** — `format_utc_z` was built in this PR and never called, so `+00:00` still reached the proof payload | **Closed.** Both emission sites routed through the single formatter |
| **B-3 was pinned for timestamps only** — re-deriving the identity keys at publication survived the whole suite | **Closed.** Source was already correct; the test that constrains it is new and mutation-verified |
| **NTFS alternate-data-stream bypass** — `<protected>/docs:probe_stream` was ALLOWED *and the write succeeded*, refusing only on the second call once the stream existed | **Closed.** Stream-qualified spellings refused before anything is created |
| **Declared numeric keys accepted unbounded series**; a non-string key skipped a whole subtree | **Closed.** |
| **`current_byte_level_proof_status()`** returned one constant — a new single-valued attestation created in the same edit that deleted eleven | **Closed by deletion.** So was `aggregate_assertions`, a literal-`True` map |
| DI-5…DI-9, C-5, C-8 (both confusable spellings admitted) | **Closed.** C-8 resolved better than either option offered: `eligible_event_count` stays admissible as a *key* so the committed artifact scans clean, but **not** as a numeric one, so a continuation populating it with a real count is flagged |
| **D-5.8 count floor** | **Deliberately NOT closed** — `Requires separate contract Gate-decision`. Enforcing "a sparse handful of points never produces a proof token" against a calendar that itself declares one slot per pair needs a number nobody pinned, and D-6 forbids this module to decide how many buckets an epoch contains |

**Mutation study**: 203 mutants, 181 killed (**89.2%**), 22 survivors — 17 genuine
gaps at audit time, since closed or pinned; 2 verified redundant, 2 verified
equivalent, 1 disclosed harness artifact. Every fix above was re-verified by a
36-case temporary-revert harness reporting `unverified: none`.

**The R-1 trap fired twice on this PR** — once when the RF-19 fix made
`full_20x3_coverage` incapable of being `False`, and once when
`current_byte_level_proof_status()` was created. Both were caught by audit, not
by the implementer. The constants that remain (`evidence_basis`,
`files_opened=0`) are **disclaimers** asserting that nothing was measured, which
DI-2 requires; every constant asserting a *favourable* property was deleted.

**Methodological note worth carrying forward:** a stale `__pycache__` entry
falsified one mutation result (same-size edit inside one second). Every mutation
run here used `PYTHONDONTWRITEBYTECODE=1`. Any future mutation study on this
suite should do the same or it may silently under-report survivors.

## 7b. Second audit round — a fresh-context re-audit found the first round defective

Policy §13.3 step 7 requires the fixes be re-verified in a context that does not
inherit the first conclusions. That re-audit found **three more blockers**, two
of which the lead reproduced independently. This section records them because
the pattern matters more than any individual defect.

| Finding | Evidence | Disposition |
| --- | --- | --- |
| **N-1 — a lying `float` subclass defeated D-1** | Crossed-quote rows yielded `n_source_bars=15, eligible=True, complete_bucket=True` while identical plain-`float` crossings refused 12/12. Also reached `cost_schema` (`min_observed_spread_pips = -50000.0`) and `effective_n` (`raw = -100` accepted) | **Closed.** New `numeric_authority.py` pins numeric character data through the **unbound** `float.__float__` / `int.__index__` slots |
| **N-2 — `open_for_consumption` minted a record carrying a claim token** | An `object.__setattr__`-tampered `ProofResult` produced a fresh `ConsumptionApproval` asserting `MEASURED_FROM_DERIVED_ARTIFACT_BYTES…` beside `files_opened=0` | **Closed.** All six token fields re-checked, mirroring `_limb_cv`'s existing `per_pair` re-check |
| **N-3 — the byte-level claim token was writable into a scrub-clean artifact** | **No tampering needed**: `is_forbidden_status` was `False` for the claim token while `BYTE_ADMISSIBLE` — a strictly weaker claim — was `True`. A `no_overlap_proof.json` asserting the claim scanned clean and wrote | **Closed.** `UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS`, cross-checked **at import** so a rename cannot make a token writable |
| **N-4 — the R-1 trap fired a THIRD time** | `CoverageResult.pairs_measured = tuple(PAIRS_20)` asserted a favourable constant — the same field deleted from `ProofResult` for that exact reason | **Closed by deletion**; the roster is recovered from `per_pair` |
| **N-5 — `copy.deepcopy` / `pickle` bypassed the one-shot construction tokens** | Two forged `ValidatedCalendar`s driven to a satisfied `CoverageResult` | **Closed** on all five token-bearing records; the docstrings claiming the token "removes the public-API route" corrected — `deepcopy` *is* the public API |
| **N-6 — two guards closed but unpinned** | Re-established by the new-guard mutation study with reachability controls | **Pinned by tests; source deliberately unchanged** — the study scoped these as a defence-in-depth loss and a verdict flip, explicitly **not** "bypass proven" |
| **§12.23 unenforced at the writer** | An `isoformat` timestamp scanned clean and wrote, though every producer was correct | **Closed** with a narrow spelling rule (full date-time bearing a *numeric* offset only) |

**Three corrections to this document's own earlier claims**, recorded rather than
quietly amended:

1. §7's *"Nothing was referred as `Requires separate contract Gate-decision`"* was
   contradicted by §7a in the same document, which refers exactly that for D-5.8.
   §7a is correct.
2. §7a's *"every constant asserting a favourable property was deleted"* was false
   when written — `pairs_measured` survived (N-4). It is true now.
3. The lead's own fix instruction to *"reuse `float(value)`"* would **not** have
   closed N-1: `float()` calls `__float__`, so a subclass still controls it.
   Measured: `float(F(-5.0)) == 0.0` versus `float.__float__(F(-5.0)) == -5.0`.
   The implementer caught this and used the unbound slot.

**Beyond the brief**, the fix round found `warmup.py` unswept — the T-1 leakage
boundary `w_bars < longest_feature_lookback_bars` was decided against the
caller's object — and swept it.

**Verification:** a 73-test revert harness, **100 % killed, zero pass-throughs**,
tree restored byte-identically. It caught six of the round's *own* new tests that
were controls rather than pins (an ordering-liar cannot defeat `==`), which were
then completed. Separately, a mutation study of the round-1 guards ran 42 mutants:
**38 killed, 2 import-refused, 2 survived** — the two survivors being N-6, pinned
here.

**The honest summary of this PR's fix cycle:** three rounds, and each round found
real defects the previous one created or missed. The R-1 trap fired three times
and was caught by audit every time, never by the implementer. That is the loop
working — but the next independent re-check should assume the same pattern rather
than treat a green suite as evidence of conformance.

## 7c. Fourth round — and where the audit loop actually landed

A second fresh-context re-audit found round 3 held on its three headline
blockers and broke nothing, but was **incomplete**: its N-2 fix left three live
routes, its N-1 sweep-scope claim was wrong for two modules, and the R-1 trap
had a **fourth** instance in `no_overlap` — a module none of the rounds had
touched. Seven fixes, all closed:

| # | Finding | Fix |
| --- | --- | --- |
| P-1 | `declared_not_measured` compared element-wise with unpinned `==`; thirteen `str` subclasses with `__eq__ → True` passed and the **forged tuple was published verbatim** (including one that erased the disclosure entirely) | each element pinned before comparison; the **pinned** tuple published |
| P-2 | `(files_opened, bytes_measured) != (0, 0)` unpinned — an N-1 miss *inside* the N-2 fix, in a file that already imported `pin_int` | pinned |
| P-3 | `_pin_token` pinned for the comparison and published the **unpinned original** — B-3's own rule violated inside the fix meant to enforce it. A `str` subclass rendering the claim token under `str()`/`repr()`/f-string minted an approval | publish what was pinned; `inventory_digest` re-checked; **the identity half closed too** (published from three further reads of a map verified from one) |
| P-4 | `expected_count` unpinned (`LyingInt(999)` accepted where plain `999` refused) | pinned |
| P-5 | the BL-2/F-1 divergence guard subtracted before pinning, so a `float`-subclass instant liar was accepted where the plain-float liar was refused | both `timestamp()` results pinned before subtracting |
| P-6 | R-1 fourth instance: six unfalsifiable favourable fields in the roster report | **all six deleted**; the roster is recoverable from `certified_spans`; `expected_pairs`/`expected_pair_count` kept as *requirement* disclosures |
| P-7 | `verifier_independence_basis` opened with an unfalsifiable favourable clause | **restructured**, not kept and not deleted — renamed to `…_limit` and rewritten to lead with the denial and end `…NOT_EVIDENCE_OF_INDEPENDENCE` |

The round also fixed `numeric_authority`'s `TypeError` escape (its docstring
promised every function raises `NumericAuthorityError`, and a bare `TypeError`
escaped the caller's documented wrapping) and a prose arithmetic error in
`guards.py`.

### The fifth R-1 instance — ruled, not silently kept

The round found a **fifth** instance itself and, correctly, did **not** delete it
out of scope: `no_overlap.py` `files_checked` is always `20` on the only path
that returns, for exactly the reason P-6 names. It reported that this weakens
P-6's coherence — the field deleted as `actual_record_count` is the same number
`files_checked` still publishes under another name — and asked for a ruling.

**Ruling: retained, and the reason recorded at the emission site.** Unlike
`actual_record_count`, `files_checked` is named in the committed
`no_overlap_proof` allowlist, and this Work PR does not change committed
schemas — the same reasoning that kept `eligible_event_count` in
`schema_keys_not_verified`. It is recorded as a **residual for the next gate**:
if the artifact schema is revised, this field goes with `actual_record_count`.
It must not be read as evidence that twenty files were examined.

### What four rounds actually demonstrated

Each round found real defects the previous round created or missed, and the R-1
trap fired **five times** — caught by audit every time, never by the
implementer. Two of those were created by fixes for other findings. The lead's
own fix instruction was wrong once (`float(value)` is not a pin, because
`float()` calls `__float__`). An auditor had to withdraw claims it could not
stand behind, and a mutation study had to correct its own headline figure.

The loop converged — round 4's findings are all bounded defence-in-depth rather
than exploitable dispositions — but **the honest reading is that this machinery
needs the independent re-check gate, not this session's assurance.** A green
suite has been a poor predictor of conformance at every round of this PR.

## 7d. Reclassification of the five "residual blockers"

Earlier drafts of this note called all five **residual blockers**. That label was
too strong for every one of them. Reclassified against committed authority:

| # | Item | Classification | Authority |
| --- | --- | --- | --- |
| 1 | Absent-protected-root name-limb-only case | **Defence-in-depth only** | The identity limb needs the root on disk; all protected roots are **git-tracked**, so a checkout always materialises them and the degraded path is unreachable in practice. The name limb — which is host-independent — still refuses anything *named* under a protected tree. The audit's own scoping was "a verdict flip on the refusal function, **not** a demonstrated write into a protected tree" |
| 2 | `no_overlap` dead-window limbs unreachable while constants hold | **Defence-in-depth only** | `DEAD_START` is exactly one second after `DESIGN_END` and `_DEAD_END_EXCLUSIVE == FORWARD_FLOOR`, both asserted at import with explicit `raise` (not `assert`, so `python -O` cannot strip them). The ceiling and floor limbs decide every reachable case; these are retained against a future constant edit and are documented as such |
| 3 | `eligible_event_count` term split | **Non-blocking observation with committed authority** | D-7: committed artifacts are populated by human-reviewed PR diff, and this Work PR does not change committed schemas. The confusable name cannot carry a real count — the allowlist admits it as a *key* (so `design_m15_inventory.json` still scans clean) and flags it as a *numeric* one. §12.20's pinned `complete_bucket_count` is what the code emits. The rename lands with the inventory schema extension at the continuation |
| 4 | `files_checked` retained by ruling | **Non-blocking observation with committed authority** | Same authority as #3: it is named in the committed `no_overlap_proof` allowlist, so deleting it would desynchronise the emitted record from a committed schema this PR may not change. It is a tautology on the returning path, that is recorded at the emission site, and it is explicitly not to be read as evidence that twenty files were examined |
| 5 | `measure_pair_coverage` has no bid/ask crossing check | **Defence-in-depth only** | D-1's refusal lives in `aggregation`, which is the only component that sees M1 rows; coverage consumes already-aggregated bars. The forged case is caught anyway by the 20-pair accounting cross-check and by `_assert_bar_certifiable` |

**True residual blockers: zero.** None of the five prevents the contract from
being satisfied as ruled in PR #443/#444, and each non-blocking item rests on a
committed authority named above rather than on this session's judgement.

## 7e. D-5.8 — referral status

**Status: `Requires separate contract Gate-decision`.** Verified in the clean
room at the final head:

- **No implicit default and no invented threshold exists.** A search for a slot
  count floor across `coverage.py` and `calendar_authority.py` returns only
  prose; the sole numeric relation is `expected_minutes == 15 × |expected slots|`,
  which is **arithmetic, not a threshold** (`coverage.py:661`).
- **It fails closed while undecided.** An empty expected-slot set is refused —
  *"absence of slots is never a statement that the market was closed"*
  (`calendar_authority.py:295-296`) — and the referral is recorded in the
  module's own docstring (`coverage.py:42-48`) rather than left to a reader.
- **Whether it must resolve before the gate-3a continuation, or may defer, is
  itself for the next contract Gate-decision.** The literal clause names *"a
  single instant"*, which needs no invented number, while *"a sparse handful"*
  does. This session deliberately does **not** decide which, and mints nothing.
  Meanwhile the operative control is
  `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`: the expected slot set
  comes only from an approved calendar artifact, which does not yet exist.

## 8. Process-boundary breach — disclosed, isolated, and revalidated

During test reconciliation a subagent ran an unscoped `pytest tests/`, which
incidentally executed **host-gated tests that read local research data and
connected to a live database**. This section replaces an earlier version of it.

> **CORRECTION.** The earlier disclosure said *"The run was read-only."* **That
> was wrong.** A later boundary investigation established from source that the
> DB-gated tests perform `INSERT` / `UPDATE` / `DELETE`. The claim is withdrawn
> and corrected below rather than amended silently. Nothing here rewrites the
> history — the run happened, and it wrote.

### What the run actually touched

- **A live database, with writes.** The integration tests call
  `load_dotenv(<repo>/.env, override=False)` at import, so `DATABASE_URL` was
  available even though the shell environment was clean. In a clean room
  **41 tests skip on `DATABASE_URL not set`**; those are exactly the ones that
  executed here. They `INSERT` / `DELETE` / `UPDATE` fixture rows (brokers,
  accounts, instruments, orders, positions) under fixed test IDs, with explicit
  teardown `DELETE`s.
- **Local research data, read only.** Four tests are gated on real M1 / curated
  data being present (`tests/unit/test_stage24_1a_*`, `test_stage25_0*`,
  `test_stage27_0f_*`, `tests/ml_step4/test_inventory.py`,
  `tests/unit/test_calendar_service.py`). The host carries 358 untracked
  `data/*.jsonl` M1 files; the repo tracks one CSV.

### What it did **not** do

- **No schema migration ran.** The only destructive schema test —
  `tests/migration/test_roundtrip.py`, whose own docstring warns it *"drops all
  44 D1 tables. Any data in the DB is lost."* — is excluded by
  `pyproject.toml` `addopts = "… --ignore=tests/migration/test_roundtrip.py"`.
  The two other migration tests that mention `downgrade` only assert that
  `upgrade`/`downgrade` are **callable**; they never execute them and make no DB
  contact.
- **No tracked evidence was modified.** `tests/conftest.py` carries a
  session-wide autouse fixture that hashes the eight protected tracked artifacts
  at session start and **fails the session at teardown** if any changed. It did
  not fire, and `git diff HEAD -- artifacts/` is empty.
- **No artifact was produced.** Every untracked `artifacts/*.log` predates this
  session.
- **No credential was exposed.** `.env` is gitignored, **never tracked and never
  committed** (`git log --all -- .env` is empty); the PR diff contains no
  credential-shaped content; the PR body names `DATABASE_URL` only as an
  identifier. No secret value was read, printed, copied or recorded during the
  investigation.

### Evidence discarded

**The entire unscoped run is excluded from this PR's verification evidence.** No
B-1…B-7 disposition, no RF-1…RF-29 disposition, no §12 conformance verdict and
no mutation result rests on it — every such result came from runs scoped to
`tests/m15_gate3a/` (plus `tests/contract/`), and all of them have now been
re-derived in a clean room (§8a).

### Residual exposure this session cannot close

Whether the database that received those writes is a development or a
production instance is **not determinable without reading the credential**,
which is forbidden. The writes were test-scoped and self-cleaning, and no schema
change occurred — but **confirming the target instance is a human decision**, and
it is recorded here as an open process item rather than assumed benign.

## 8a. Clean-room revalidation

The final head was re-verified in an isolated environment built from
`git archive c2ef65a`, containing **no `.env`, no `data/*.jsonl`, no model
binaries**, with `DATABASE_URL` and every broker/storage credential unset, a
temporary `HOME`/`TMPDIR`, and a **clean `pip install -e ".[dev]"`** (never
`uv` — the lockfile is known-stale). Isolation was asserted in-process before
any test ran.

| Gate | Clean-room result |
| --- | --- |
| custom checks | exit 0 |
| `ruff check` / `ruff format --check` | clean · 664 files formatted |
| **M15 gate-3a suite** (B-1…B-7, RF-1…RF-29, §12 conformance) | **1100 passed, 1 skipped** |
| contract tests | **500 passed** |
| mutation battery over the contract's load-bearing limbs | **11 applied, 11 killed, 0 survived** |

The clean-room figures are **identical** to those obtained on the host, so the
acceptance evidence demonstrably does not depend on the breached resources.

**Regression check against base.** `tests/unit` + `tests/ml_step4` were run in
the clean room at both `ea40d2f` and `c2ef65a`: **27 failed / 3277 passed / 13
skipped at each, with byte-identical failing-test sets.** PR #445 introduces
**zero** new failures. Those 27 are pre-existing environment failures — tests
that *fail* rather than *skip* when research data is absent, which is itself the
follow-up issue in §8b.

**Mutation honesty note.** The first clean-room batch reported two survivors and
two spec-errors. On inspection all four were **harness defects, not test gaps**:
one pattern matched a docstring instead of the code, one changed only an
exception message that still substring-matched, and two patterns did not exist.
Re-run against the real code sites, all four were **KILLED**. The corrected
total is 11 valid mutants, 11 killed.

## 8b. Follow-up issue — test-safety (separate Work PR, not this one)

Not fixed here: changing the host-gated tests is unrelated to this PR's
targeted-fix objective, and folding it in would violate one-objective-per-PR.
Recorded for a separate **test-safety / infra Work PR**:

1. A repository-wide `pytest` run must not enable local-data or live-database
   tests on **mere resource presence**. Today `load_dotenv(...)` at import plus
   `skipif(not DATABASE_URL)` means *having a `.env` on the machine* silently
   opts you in.
2. Live and real-data tests must require **explicit opt-in** (a marker plus a
   deliberate flag or environment variable), not implicit availability.
3. **Default test execution must touch no external or local research data**, and
   no database.
4. Tests that currently **fail** rather than **skip** when research data is
   absent should be re-gated — the 27 pre-existing failures above are that
   defect, and they make a clean-room run indistinguishable from a real
   regression at a glance.

---

## 9. Non-authorisation

No real data was read for any research purpose; no M15 derived; no checksum
computed; no spread computed; no validation, holdout, training, inference or
execution; no broker, paper, live, external-storage or credential path touched;
no calendar artifact generated; no market-hours decision made; no frozen contract
changed; `uv.lock` untouched and **no dependency added**; `uv sync` never run.

**This PR does not grant itself source-audit acceptance.** The official gate
status remains `…_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES` until a **fourth
independent re-check**, in a session separate from every author here, accepts it.
Gate-3a continuation remains **NOT authorised**; the forward epoch remains
**BLOCKED/WAIT**.
