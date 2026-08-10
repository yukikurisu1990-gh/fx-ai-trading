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

## 8. Process deviation — disclosed

During test reconciliation a subagent ran an unscoped `pytest tests/`, which
incidentally executed **host-gated tests that read local M1 data and a live
`DATABASE_URL`**. Those tests skip in a clean environment and none imports
`m15_gate3a`. The run was read-only; **no artifact was created or modified** (the
untracked `artifacts/*.log` files all predate this session), no M15 was derived,
no checksum or spread computed, and no evidence was produced or relied upon.

It was nonetheless outside this PR's forbidden-action boundary and is recorded
here rather than omitted. Every subsequent run — including the whole mutation
study — was explicitly scoped to `tests/m15_gate3a/`, and later subagents were
instructed not to repeat it.

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
