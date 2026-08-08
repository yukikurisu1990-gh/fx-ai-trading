# M15 gate-3a contract & design Gate-decision — RULED

- **Document class:** doc-only **Gate-decision** record (policy §14.2 — it
  formally judges and fixes research contracts). Executes nothing. Reads no real
  data.
- **Risk tier:** **Amber.** Not self-mergeable. This document **records a human +
  ChatGPT contract ruling**; the decisions bind when this PR is merged.
- **Base:** master `f2f185e` (the merged third independent source-audit re-check).
- **Purpose:** fix the contract and design questions the merged audit left open,
  so the follow-up targeted-fix Work PR **invents nothing** and re-interprets
  nothing.

## Statuses

- Required: `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED`
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
  · `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
- Open pre-continuation item: **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`**
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Gate-3a continuation: **NOT authorised.** Targeted-fix Work PR: **not started.**

**Forbidden-label note.** This document asserts none of `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, `DEPLOYABLE`. Where such tokens appear they
are quoted probe payloads evidencing a containment behaviour — a prohibition
context under playbook §10, never a claim.

---

## 0. Status of each decision

Every contract question raised by the merged audit is now **RULED**. Nothing in
this document is left "referred" or "pending a human decision", with exactly one
exception, stated once and carried explicitly:

> **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`** — the *contract* for
> the closure/market calendar is fixed here (§9). The **concrete calendar
> artifact** for the target epoch must be produced and approved by human +
> ChatGPT before the gate-3a continuation runs. This is **not** permission for an
> implementer to invent market hours.

The rulings bind the targeted-fix Work PR and the gate-3a continuation. An
implementing session may not re-interpret them, relax them, or introduce a
threshold they do not contain.

---

## 1. Executive summary — what was ruled

| # | Item | Ruling |
| --- | --- | --- |
| **D-1** | Crossed quotes (referral 3) | **Hard fail-closed.** The merged R-2 disposition is authority. No drop-and-count at the first continuation |
| **D-2** | Rejection tolerance (referral 4) | **Zero**, and *structural* — not an empirical "0%" threshold. Certified coverage must contain every expected usable observation |
| **D-3** | Missing-minute schema (referral 2) | **Six distinct measured quantities** replace the ambiguous single count. Schema change **approved here** |
| **D-4** | NR-K / hashing | **Hashing is a byte read.** "Checksum only" is not an exception to T-1 or the real-data restriction |
| **D-5** | Coverage (T-7 CV limb) | **Set equality**, per pair, against the approved calendar — not min/max containment. **NR-C and NR-J integrated here** |
| **D-6** | Closure calendar | A **versioned committed calendar artifact** is the coverage authority. Expected slots are never inferred from observed data |
| **D-7** | NR-A | §9 is a per-PR merge-scope check; each artifact's committed `status` is authority; population by human-reviewed PR diff into a separate output directory |
| **D-8** | NR-C | Measured conjunction over 20 pairs; missing measurement = unsatisfied |
| **D-9** | NR-D | Duplicates fail closed / abort; alias duplicates count after canonicalisation; silent dedup forbidden |
| **D-10** | NR-J | Insufficient required coverage **raises**; a coverage flag alone never permits continuation |
| **D-11** | Byte-level T-7 proof | **BI ∧ TC ∧ CV ∧ DB**, all four limbs, each normatively defined; declaration-only evidence can never be promoted |

**Referrals 1 and 5** (spread magnitude bound; forward evidence shape) remain
`MAY_DEFER_BEYOND_GATE3A_CONTINUATION` — the merged audit's classification stands
and is **not** escalated here.

### One foreseeable consequence, recorded so it is not a surprise

D-1, D-2 and D-5 together are strict by design: any crossed quote, any rejected
minute, or any expected M15 slot that cannot be certified means the affected
pair is not certifiable, and the 20-pair conjunction then fails. **On real data
the first continuation may well halt.** That halt is the *designed* outcome, not
a defect: it returns the empirical question to the decision-makers with
measurements in hand. Resolving it requires a **new contract Gate-decision
informed by an approved read-only measurement**, never an implementer's
relaxation, and never a threshold invented at the point of failure.

---

## 2. Authority and method

Read directly at `f2f185e`: the merged audit
(`docs/design/m15_third_independent_source_audit_recheck.md`, §7/§8 being the
authoritative referral/NR definitions), `docs/governance/m15_audit_playbook.md`,
`docs/governance/autonomous_development_policy.md`, the frozen pre-registration,
the T-1…T-7 design audit, the merged PR #439 audit record, all eight
`artifacts/m15_gate3a/*.json`, the committed M1 inventory metadata, and the
current source.

**Five independent roles** were used to prepare the analysis (contract/governance
consistency · data-integrity/proof-design · adversarial/bypass ·
testability/observability · artifact/schema), none given another's conclusions,
and **every decisive factual claim was independently reproduced by the lead**
before adoption. The rulings in §3–§11 were then supplied by human + ChatGPT and
are recorded here as normative.

**No real data was read; no M15 derived; no checksum computed; no spread, no
validation, holdout, training, inference or execution; no broker, external
storage or credential touched; `uv.lock` untouched; no source or test file
changed; no calendar artifact generated.** Committed metadata JSON under
`artifacts/**` was read, which the audit method explicitly permits.

---

## 3. D-1 — Crossed quotes: hard fail-closed

**Ruling.** The first gate-3a continuation does **not** adopt drop-and-count. The
merged PR #439 R-2 disposition — *"assert … `ask_* >= bid_*` per row"* — is the
authority.

### Normative

1. A **crossed quote** is any required bid/ask field pair where `ask < bid`.
2. A crossed quote is **never corrected** to a plausible value.
3. A crossed-quote row is **never dropped-and-continued**.
4. If a crossed quote exists anywhere in a bucket or file under certification,
   **that bucket and that file are not certifiable.**
5. Eligibility and event counts are **never preserved by dropping** the offending
   observation.
6. Occurrence counts **may** be recorded where observable, but **recording is
   never grounds for acceptance**. A count is a diagnostic, not a licence.
7. **`ask == bid` is not a crossed quote.** A zero spread is refused only if it
   violates a separate cost/spread contract, and then by that contract — not by
   this rule. (This also settles **NR-E**: the zero-spread limb no longer rests on
   the `stage25_0a` analogy, which §11 of the pre-registration does not admit as
   authority for a family-A design decision.)

**Forbidden:** drop-and-count; any lenient mode, flag, kwarg or environment
variable that downgrades the refusal; citing `scripts/stage25_0a_build_path_quality_dataset.py`
or any non-family script as authority for a family-A design semantic.

**Fail-closed:** any crossed row; any row where the comparison cannot be
evaluated.

**Observable outcomes tests must pin.** A 15-row bucket with exactly one crossed
row yields **no certifiable bar** — not a bar with `eligible: False`; each of the
four side pairs crossed in isolation refuses, as four separate tests with
distinct match strings (no regex alternation); `ask == bid` does **not** refuse by
this rule; the refusal survives `python -O`.

**Changing this later** requires an **approved read-only measurement** followed by
a **separate contract Gate-decision**. It is not an implementation choice.

**Class:** restores and confirms the merged audit remedy. The re-disposition made
in a Work PR is recorded as procedurally void (policy §14.2, §14.5, §12).

---

## 4. D-2 — Rejection tolerance: zero, structurally

**Ruling.** The semantic row/minute rejection tolerance for the **first gate-3a
certification** is **zero**.

**This is not an empirical "0% threshold".** No percentage was chosen, and none
may be inferred. The requirement is structural:

> **Certified coverage must contain every expected usable observation the
> contract requires.**

### Normative

1. No empirical tolerance (5%, 10%, or any other figure) may be invented,
   defaulted, configured or inferred.
2. A row-drop ratio **alone** never decides whether the continuation may proceed.
3. If the rejection of a single row makes an M15 bucket unable to satisfy its
   contract, that bucket is **coverage loss** — not a degraded but acceptable bar.
4. Dropped or rejected observations are **never imputed**.
5. An M15 slot missing because of a rejection is **never counted as covered**.
6. Introducing a non-zero tolerance later requires a **separate contract
   Gate-decision**.

**Observable outcomes.** No entry point exposes a tolerance parameter with a
numeric default; a single rejected minute in an otherwise complete bucket makes
that bucket non-certifiable and is visible as a coverage deficit, not as a
silently smaller count.

**Why the reported ratio could not have carried this decision** (lead-reproduced;
retained because it explains why a ratio-based rule was rejected):

```
1 crossed minute in each of 10 buckets:
  rows_ingested / rows_retained : 150 / 140
  row-drop ratio                : 0.0667
  eligible buckets              : 0 of 10
  ELIGIBILITY loss ratio        : 1.0000   <- 15x the row-drop ratio
  committed gap_report          : missing_minute_count=0 max_gap_minutes=0
```

A 6.67% row-drop ratio is a **100% eligibility loss**, and the committed
`gap_report` shows nothing. A tolerance expressed against the row-drop ratio would
have licensed total destruction of a pair's event supply.

---

## 5. D-3 — Missing-minute schema

**Ruling.** The current two-key `gap_report` is insufficient as proof evidence.
The following six quantities are **separately measured and separately recorded**.
**This schema change is approved by this Gate-decision**; implementation lands in
the targeted-fix Work PR.

| Field | Normative definition |
| --- | --- |
| `expected_source_minute_count` | Minutes that the **approved calendar artifact** (§9) says should exist for this pair in the certified span |
| `observed_source_minute_count` | Minutes for which a source record existed |
| `absent_source_minute_count` | Expected by the calendar, **not present** in the source |
| `rejected_source_minute_count` | **Present** in the source but not usable, because it violated a contract |
| `usable_source_minute_count` | Canonical, distinct minutes admissible to aggregation |
| `max_unavailable_gap_minutes` | Longest run of **consecutive expected-but-not-usable** minutes, measured against the expected calendar |

### Normative

1. **Coverage deficit includes both `absent` and `rejected`.** Neither alone
   describes it.
2. A present-but-rejected minute is **never described only as "missing"**.
3. **`missing_minute_count` alone is never proof authority.** If it is retained
   for compatibility, it may not be used in any certification decision, and its
   meaning must be stated explicitly wherever it appears.
4. `max_unavailable_gap_minutes` is defined **against the expected calendar**, not
   against observed data.
5. **An emitted or certified M15 bar requires every source minute its contract
   demands to be `usable`.** A bar assembled from fewer is not certifiable.

**Why the two-key schema had to change** (lead-reproduced): a file losing 50% of
its source minutes to rejection reports, under the committed schema,
`{'max_gap_minutes': 0, 'missing_minute_count': 0}` — indistinguishable from a
perfect file. And `total_missing_source_minutes_within_emitted_buckets` counted
present-but-rejected minutes as *missing source minutes*, contradicting the
module's own docstring. Both are resolved by the six-field split.

**Observable outcomes.** The accounting identity
`expected = usable + absent + rejected` holds per pair; a fixture containing a
calendar-absent minute and a contract-rejected minute reports them in **different**
fields; a bar with 14 usable minutes is not certifiable.

---

## 6. D-4 — NR-K: hashing is a byte read

**Ruling.** Hashing is a **byte read**. "Checksum only" is **not** an exception to
T-1 or to the real-data read restriction.

### Normative

1. **Unapproved raw source bytes are not read for checksum purposes.**
2. If raw-source re-hashing is ever required, it needs its own **explicit read
   authorisation**, on its own merits.
3. The **subject of the T-7 byte-level proof is the derived M15 artifact bytes** —
   not the raw source bytes.
4. At derived-artifact production, the **digest, byte size, declared identity and
   measured span are co-measured from the same byte stream**.
5. The **proof verifier independently re-reads** the derived M15 artifact and
   re-measures.
6. **A byte-level proof token is never generated from declaration-only metadata.**
7. The fact that a raw source file contains dead-window or forward-region data
   **may not be circumvented under the guise of hashing**.
8. A **consumer re-verifies the derived artifact's identity and digest immediately
   before use.**

The **C/P/V role split** and the **TOCTOU re-verification** policy proposed in
this PR are retained (§11).

**Consequence recorded honestly:** source-side substitution detection is
correspondingly weaker — the committed PR-B.1 digests are *trusted*, not
re-checked. That is the accepted cost of not reading unapproved raw bytes, and it
is stated so no later session mistakes it for an oversight.

---

## 7. D-7 · D-8 · D-9 · D-10 — NR-A, NR-C, NR-D, NR-J

### D-7 — NR-A: `artifacts/m15_gate3a/` (**RULED**)

- Playbook §9 is a **per-PR merge-scope check**, not a declaration of
  immutability.
- **Each artifact's own committed `status` is the authority** on what may happen
  to it (`SCHEMA_FIXED__POPULATED_AT_IMPLEMENTATION`,
  `DERIVATION_CONTRACT_FIXED__…`, `APPROVED_SPEC`, `EMPTY__NO_FORWARD_DATA_EXISTS`,
  `ADOPTION_BLOCKED__…`).
- **Population happens through a human-reviewed PR diff** — the mechanism by which
  all eight artifacts arrived (`7e795d4`, PR #431). No code path writes into the
  protected tree.
- The continuation's **outputs go to a separate output directory** and **never
  overwrite existing protected evidence**.
- `effective_n_estimator_spec.json` (`APPROVED_SPEC`) and both forward artifacts
  are **never written** by this continuation.
- **Trap for the fix PR:** do not close audit B-5 by adding `artifacts/m15_gate3a`
  to `_PROTECTED_PREFIXES` while §5 still names it as a write target — adopt the
  separate output directory first, then the prefix is safe to add. B-5's other
  content stands: **`data/`, `models/`, the 730d/3650d PR-B.1 trees, and `docs/`**
  (which currently permits `write_metadata_artifact` to target the governance tree
  itself) must be protected.
- **Also required:** `refuse_real_path` is **cwd-dependent on relative paths**
  (lead-verified — the same logical path is ALLOWED from a different working
  directory). Anchor relative paths at the repo root, or require absolute paths.

### D-8 — NR-C: attestation (**RULED**, integrated into D-5)

- `dead_window_bars_present` and every other aggregate assertion is a **measured
  conjunction over all 20 pairs/files**.
- **A missing measurement makes the assertion unsatisfied — never vacuously
  true.**
- **A declared count alone never establishes it.** Attestation is by the
  **verifier**, never the producer, never human transcription.
- Bar membership is measured under **both** definitions — bucket-start in the dead
  window, and *any contributing source minute* in the dead window — and **both must
  be zero**. They coincide under a correct implementation and diverge exactly when
  it is wrong, which is the case the assertion exists to catch.

### D-9 — NR-D: duplicate minutes (**RULED**)

- A duplicate source minute is **fail-closed: abort**.
- **Alias duplicates count as duplicates after canonicalisation** — normalise
  first, then detect.
- **Silent deduplication is forbidden**, in every form (first-wins, last-wins,
  tolerating a sub-minute-remainder difference).
- The minute is claimed **before** any quality disposition, so a rejected row still
  consumes its minute and cannot be substituted by a second record.

Recorded evidence: the committed source inventory shows `duplicate_timestamps = 0`
across all 20 files, so this strict disposition has **zero measured cost** on the
design-span input.

### D-10 — NR-J: required coverage (**RULED**)

- Insufficient required coverage **raises**; it is **not** report-only.
- **Recording a coverage flag never permits continuation.**
- For cost tables specifically, all `20 × 3 = 60` `(canonical_pair, session)`
  cells must be present or `validate_cost_table` refuses. Both operands are
  already frozen, so no number is minted.
- The existing test that currently pins the re-disposition as correct behaviour
  must be rewritten or deleted — leaving it is how a re-disposition becomes
  permanent.

---

## 8. D-5 — Coverage: set equality

**Ruling.** The T-7 coverage limb is **set equality**, not min/max containment.

For **each pair**:

```
actual_certified_m15_slots  ==  expected_m15_slots
```

### Normative

1. The roster **exactly equals** the canonical `PAIRS_20`.
2. **All 20 pairs are measured.**
3. **A missing measurement is false/unsatisfied**, never treated as satisfied.
4. **No expected slot is absent.**
5. **No duplicate slot.**
6. **No unexpected extra slot.**
7. A bucket that cannot be constituted because a source minute was rejected is
   **not counted as covered**.
8. A single instant, or a sparse handful of points, **never** produces a proof
   token.
9. **`n_pairs == 20` alone is not coverage proof.**
10. Epoch/span boundary inclusive/exclusive semantics **do not change** — the
    committed constants (`DESIGN_START` inclusive, `DESIGN_END` inclusive at
    `2026-02-28T23:59:59Z`, dead window, forward floor) stand exactly as committed.

The coverage token is emitted as the **conjunction over the 20 measured pairs**.

**Why containment was insufficient** (lead-reproduced):

```
full design span -> PROVEN_NO_DEAD_WINDOW_OVERLAP  files_checked=20
ONE DAY only     -> PROVEN_NO_DEAD_WINDOW_OVERLAP  files_checked=20
a single instant -> PROVEN_NO_DEAD_WINDOW_OVERLAP  files_checked=20
last month only  -> PROVEN_NO_DEAD_WINDOW_OVERLAP  files_checked=20
```

`DESIGN_START` is a floor on `ts_min`, not a coverage requirement. A derivation
truncated to one day earned the identical token as the full ten-month span. Set
equality closes this; containment cannot.

**NR-C and NR-J are integrated into this decision**: the coverage conjunction is
the measured attestation (NR-C), and insufficient coverage raises (NR-J).

---

## 9. D-6 — Closure calendar contract

**Ruling.** The expected slot set is **never inferred from the raw source**. The
coverage authority is a **versioned, committed closure/market calendar artifact**
for the target epoch.

### The calendar artifact must carry

- source / broker / session authority
- authority **version or retrieval date**
- timezone
- market open/close rule
- DST rule
- how **known exceptional closures** are handled
- target epoch
- the **expected M15 slot set**, or a rule that generates it deterministically
- content **digest / version**

### Normative

1. **Never** reverse-infer "the market must have been closed because there is no
   data". Absence of data is a coverage question, not a calendar answer.
2. If the calendar is **absent, ambiguous or unapproved**, the coverage proof
   **fails closed**.
3. **No synthetic weekend or closure bars** are generated, ever.
4. A change to the calendar is a **contract / data-boundary change** and is
   reviewed as such.
5. The targeted-fix Work PR **may** implement the mechanism that injects and
   consumes a calendar authority — the interface, the validation, the fail-closed
   behaviour, and synthetic-fixture tests.
6. Before the gate-3a continuation runs, the **calendar artifact for the target
   epoch must be approved by human + ChatGPT**.

**This document deliberately invents no broker market-hours times.** No open/close
instants, no DST transition dates, no holiday list appear here or may be added by
an implementer.

> **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`** — the only item left
> open by this Gate-decision. It is a real-data-independent approval item: the
> artifact is a statement of market hours, not a measurement of the dataset.

---

## 10. Cross-cutting rules

### R-1 — The negative-control rule

`scripts/m15_gate3a/**` and the committed artifacts emit **eleven hard-coded
self-attestations**: `imputation: False`, `synthetic_weekend_bars: False`,
`mid_price_constructed: False`, `p95_diagnostic_present: True`,
`real_spreads_computed: False`, `strategy_metrics_computed: False`,
`first_w_bars_event_eligible: False`, **`dead_window_loaded: False`**,
`no_raw_data_read_at_gate3a: true`, `"result": "ALL_SCRUB_CLEAN"`, and
`MAGNITUDE_AUTHORITY_STATUS`. None can take the other value, so none is evidence —
yet each reads as a measured fact. `dead_window_loaded: False` is the **T-1
leakage claim itself, emitted as a constant.**

> **No artifact field may assert a property unless the same code path, exercised
> in the same run, is demonstrated to emit the opposite value on a deliberately
> constructed counter-case, and that demonstration is recorded alongside the
> attestation. A field that can only ever hold one value is deleted, not
> reported.**

### R-2 — Pinned terms

Twenty terms are currently used in incompatible senses across committed documents
and code. **The fix PR pins each by naming the quantity measured, its unit, and
whether it is declared or measured.** The three most dangerous:

- **`n_source_bars`** — source minutes observed · rows retained after rejection ·
  number of *reads*. It currently means the second, and can be inflated to the
  third by one repeated row object (audit RF-4).
- **`eligible_event_count` vs `raw_event_count`** — the committed inventory defines
  the first as *"count of `n_source_bars==15` buckets"*; the approved effective-N
  spec defines the second as *"eligible **traded** events (buckets that pass the
  cost-hurdle and fire an EV-gated trade)"*. Different quantities, confusable
  names. Feeding the first where the second is meant clears the frozen floors
  (raw ≥ 1000, N_eff ≥ 400) by orders of magnitude and **disarms
  `INSUFFICIENT_SAMPLE`**. Pin `complete_bucket_count`,
  `cost_hurdle_eligible_bar_count`, `raw_traded_event_count`, and require
  `effective_n()` to take a mandatory literal naming which it receives.
- **"proof" / `PROVEN`** — declaration-consistency vs byte-level.

The remaining seventeen: `missing_minute_count`, `max_gap_minutes`, "gap",
`row_count`, "source bar"/"source minute", `sha256` vs lineage `file_sha256`,
`ts_min_utc`/`ts_max_utc` (declared vs measured), "untouched",
"verified"/"certified", "byte-reproducible", `dead_window_bars_present`, "spread"
(close-only vs open-side; price vs pips), "drop" (rows vs minutes vs
**eligibility**), "duplicate", `ts` vs the source's `time` key, "coverage", and
"synthetic-only".

---

## 11. D-11 — The byte-level T-7 proof contract

**Ruling.** The design proposed in this PR is approved. The proof is the
**conjunction of all four limbs**, each defined normatively below.

### Subject and identity

- **Subject:** the **derived M15 artifact bytes**.
- **Identity:** canonical pair · filename / artifact identifier · **SHA-256
  whole-file digest** · **byte size**. Never a path — the data root is a runtime
  argument and is never committed.

### The four limbs

**BI — byte identity.** Each of the 20 derived artifacts is a distinct, whole
file identified by a SHA-256 digest and byte size **measured from the artifact
itself**; the digest is reproduced on an independent re-read; `size_bytes` and
`row_count` agree with the measured stream. No two roster entries resolve to the
same filesystem object.

**TC — time containment.** Measured from those same bytes: every bar lies within
`[DESIGN_START, DESIGN_END]` as committed, and the dead-window bar count is
**zero, established by a full scan**, never inferred from endpoints. The count is
strictly stronger than the endpoints, because endpoints cannot exclude an interior
bar and the interior is where a bucketing fault hides.

**CV — coverage.** For each pair, `actual_certified_m15_slots ==
expected_m15_slots` against the approved calendar artifact (§8, §9): no missing,
no duplicate, no unexpected slot; every certified slot's bucket has **all**
contract-required source minutes usable. Emitted as the conjunction over the 20
measured pairs.

**DB — derivation binding.** The bytes are the output of the named aggregation
script at a named git SHA and config hash, applied to the named source identity,
and are **byte-reproducible on re-run**.

### Token discipline

- Declaration-only evidence gets a **declaration-only token** that names its basis
  and makes no claim about any file's contents.
- **Promotion from a declaration-only token to a byte-level token is forbidden.**
  No code path may derive one from the other.
- A byte-level token is emitted **only** by a component that opened the artifact,
  scanned it, and recorded its measurements.
- **The digest and the measured span are never assembled from different reads** —
  they are co-measured from one pass over one byte stream, and the record is
  constructed atomically at the end of that pass.
- After producer measurement, an **independent verifier re-measures**; it shares
  the frozen constants and the timestamp/pair/path authorities but **not** the
  producer's scalar-derivation code.
- A **consumer re-verifies identity and digest immediately before use**.
- **Any disagreement is fail-closed** and terminal — a digest match with a scalar
  mismatch is the more alarming case, because it means a derivation is wrong.

### Component split (retained from this PR)

**C** = `scripts/m15_gate3a/**` — **never reads**; its maximal claim is the
declaration-only token. **P** (producer) and **V** (verifier) are separate
packages **outside** it, following the in-repo `scripts/_gate_p1_inspector/**`
precedent. Import direction is one-way and pinned by a test; this adds reverse
callers to a package the audit recorded as having none, and that change must be
declared and re-derived by the next independent re-check.

### TOCTOU windows (retained)

**W1 derivation → digest:** write to a temp name, flush and fsync, hash, re-open
and re-hash requiring equality, then atomically rename. **W2 digest → inventory
write:** the record is built atomically at the end of the single pass; the
inventory's own digest is recorded in the proof. **W3 inventory → consumption:**
every consumer re-verifies before reading any row — a precondition of use, not a
one-time proof.

---

## 12. Normative requirements handed to the targeted-fix Work PR

The single next Work PR carries audit **B-1…B-7** and **RF-1…RF-29**, plus the
following. An implementing session **may not re-interpret a contract or invent a
threshold**.

1. Crossed quote (`ask < bid` on any required field pair) → refuse; the bucket and
   file are not certifiable; no correction, no drop-and-continue (D-1).
2. `ask == bid` is not a crossed quote; refuse it only under a separate
   cost/spread contract (D-1.7).
3. Duplicate minute → fail-closed abort; canonicalise before detecting; no silent
   dedup; claim the minute before any quality disposition (D-9).
4. Zero semantic rejection tolerance, structurally; no tolerance parameter, no
   default, no inference (D-2).
5. Implement the six-field missing-minute schema and the identity
   `expected = usable + absent + rejected` (D-3).
6. `missing_minute_count`, if retained, may not be used in any certification
   decision and must state its meaning where it appears (D-3.3).
7. A certified M15 bar requires **all** contract-required source minutes usable
   (D-3.5).
8. Coverage is **set equality** per pair against the approved calendar; the token
   is the conjunction over 20 measured pairs (D-5).
9. Implement the calendar-authority interface: inject, validate, fail closed when
   absent/ambiguous/unapproved. **Do not author a calendar artifact** (D-6).
10. Never infer closure from absent data; never synthesise weekend or closure bars
    (D-6.1, D-6.3).
11. Hashing is a byte read: no raw-source re-hash without explicit read
    authorisation; the proof subject is the derived artifact (D-4).
12. Co-measure digest, size, identity and span from one byte stream; independent
    verifier re-measures; consumer re-verifies before use; disagreement is
    fail-closed (D-4, D-11).
13. Separate declaration-only and byte-level tokens; **promotion forbidden**
    (D-11).
14. Keep `scripts/m15_gate3a/**` reader-free; P and V live outside it; pin the
    import direction and the reverse-caller set with tests (D-11).
15. Aggregate assertions are measured conjunctions over 20 pairs; a missing
    measurement is unsatisfied (D-8).
16. Cost-table coverage `20 × 3` **raises**; rewrite the test that pins the
    re-disposition (D-10).
17. Continuation outputs go to a **separate output directory**; never overwrite
    protected evidence; population by human-reviewed PR diff (D-7).
18. Protect `data/`, `models/`, `artifacts/gate_p1_pr_b/firstrun_730d_ba`,
    `artifacts/gate_p1_pr_b/firstrun_3650d_ba`, and `docs/`; make
    `refuse_real_path` cwd-independent (D-7).
19. Apply the **negative-control rule** to every attested boolean and result token
    (R-1).
20. Pin the twenty terms; rename `eligible_event_count` to `complete_bucket_count`;
    require `effective_n()` to declare which quantity it receives (R-2).
21. Add the record-identity guard to aggregation that `no_overlap._materialise`
    already has — one row object presented 15 times currently yields
    `n_source_bars: 15, eligible: True` (audit RF-4).
22. Emit `spread_open = ask_o − bid_o` per bar, finiteness- and sign-checked like
    `spread_close` (audit RF-18 — required by pre-registration §4 and the
    derivation manifest).
23. Emit timestamps as `YYYY-MM-DDTHH:MM:SSZ` through a single formatter;
    `datetime.isoformat()` (which yields `+00:00`) must not reach any artifact.
    On ingest of committed metadata, accept **zero-only** excess fractional digits
    and **refuse any non-zero sub-microsecond digit** — refuse, never truncate.
    (Engineering rule bounded by the existing invariant; not a new contract
    constant.)
24. Correct `aggregation.py:36-38`, which states *"Aborting the whole pair was this
    package's own invention"* — the merged PR #439 audit prescribed it, and the
    implementing session's own retraction never reached the source.
25. **Schema shape constraint (lead-verified, non-negotiable).** The continuation's
    inventory is writable only if per-file records stay **nested** with **≤5
    immediate numeric fields**; six refuses, and flattening `gap_report` refuses.
    A populated 20-record instance must be asserted to pass `scan_gate3a` **before**
    any derivation. Note the scrubber currently **refuses the committed M1
    predecessor inventory's own record shape**, falsifying `artifacts.py:68-69`'s
    calibration claim — that is audit blocker B-1's allowlist redesign, not a
    threshold to raise.

---

## 13. Observable outcomes and the acceptance bar

**Accounting identities**, asserted parametrically over synthetic scenarios:
`expected = usable + absent + rejected` · `rows_ingested = rows_retained +
rejected` · `sum(n_source_bars) = usable minutes` · `certified slots = expected
slots` (set equality, per pair) · `n_eligible + n_incomplete = n_buckets_emitted`.

**Anti-patterns forbidden**, each grounded in a defect already found in this
suite: regex alternation in `pytest.raises(match=...)` that cannot identify which
guard fired (this concealed audit B-7a for three rounds); tests asserting on
**source text** instead of behaviour; vacuous globs with no non-vacuity floor;
tests passing because of host state; tests that freeze a fail-open as expected
behaviour; broad exception types where the module defines its own;
`# pragma: no cover` on a reachable guard.

**Acceptance bar:** all 19 genuine mutation survivors from the merged audit
killed; both epoch-range limbs pinned **in isolation**; all four package status
constants pinned; every blocker B-1…B-7 and required fix RF-1…RF-29 with a
failing-before/passing-after regression test; the mutation study re-run and
reported in the audit's table shape; **no newly-introduced survivor** — PR #442
introduced four defects while fixing five, and this is the check that catches that
class.

**Synthetic now vs authorised run.** Every mechanism above is testable today on
scratchpad fixtures — digests over known bytes, spans over known timestamps,
injected dead-window bars, hardlinked files, truncated files, disagreeing
producers, a synthetic calendar artifact. **Only the values require the run:** the
20 real digests, the real measured spans, the real dead-window counts, real
coverage against the approved calendar, producer/verifier agreement on real data,
and re-derivation reproducibility.

---

## 14. Non-authorisation

This document authorises nothing to run. It permits no real data read, no real M15
derivation, no checksum execution, no spread computation, no validation, holdout,
training, inference, execution, or broker/paper/live activity. It adopts no epoch
and does not lift the forward-epoch WAIT. It does not start the targeted-fix Work
PR. It generates no calendar artifact. It does not claim reproducibility under a
frozen `uv` environment — the lockfile remains known-stale and `uv sync --frozen`
reproducibility is **not** claimed.

---

## 15. Gate order from here

1. **This Gate-decision** — merged on human + ChatGPT approval; the rulings bind
   at that point.
2. **One targeted-fix Work PR** — audit B-1…B-7 / RF-1…RF-29 plus §12. Single PR,
   one objective (policy §14).
3. **A fourth independent source-audit re-check**, in a session separate from every
   fix author, accepting it.
4. **The P/V reader design PR** — synthetic-only, with its own audit; it introduces
   the repository's first new read capability since the gate-P1 inspector.
5. **Calendar artifact approval** — `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`,
   human + ChatGPT, real-data-independent.
6. Only then a **separately-authorised gate-3a continuation** (playbook §5) — Red,
   design-span only, metadata-only outputs.

**Referrals 1 and 5 remain deferred** as classified by the merged audit, and are
not escalated by this decision.
