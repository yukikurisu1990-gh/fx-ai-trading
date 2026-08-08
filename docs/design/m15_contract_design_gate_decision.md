# M15 gate-3a contract & design Gate-decision — referrals 2/3/4, NR-A/C/D/J, and the byte-level T-7 proof

- **Document class:** doc-only **Gate-decision** record (policy §14.2 — it formally
  judges and clarifies research contracts). Executes nothing. Reads no real data.
- **Risk tier:** **Amber.** Not self-mergeable. Merging requires human + ChatGPT
  approval, and that approval is what makes the DECIDED items binding.
- **Base:** master `f2f185e` (the merged third independent source-audit re-check).
- **Purpose:** close the contract and design questions the merged audit left open,
  so the follow-up targeted-fix Work PR **invents nothing**.

## Statuses

- Required: `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_PROPOSED`
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
  · `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Gate-3a continuation: **NOT authorised.** Targeted-fix Work PR: **not started.**

**Forbidden-label note.** This document asserts none of `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, `DEPLOYABLE`. Where such tokens appear they
are quoted probe payloads evidencing a containment behaviour — a prohibition
context under playbook §10, never a claim.

---

## 0. Decision classes used in this document

Every item is exactly one of:

- **DECIDED (clarification)** — committed authority already settles it; this
  document states it so it cannot be re-litigated by an implementer. Binding when
  this PR is approved and merged.
- **DECIDED (contract change)** — authority settles the *principle* but the
  artifact schema or a merged token must change. Binding only on human + ChatGPT
  approval; flagged individually.
- **REFERRED** — no committed authority exists. Options and trade-offs are tabled;
  **this document does not choose.** Each carries a **fail-closed default** that
  governs *until* the ruling, derived from playbook §2 rule 8 (*"if what a gate
  permits is ambiguous, choose the NARROWER (no-run, no-read) interpretation"*) —
  so no implementer is ever left without an instruction, and no number is minted.

**A fail-closed default is not a decision.** Where the default is "the
continuation does not proceed", that is the instruction.

---

## 1. Executive summary

| # | Item | Class | Outcome |
| --- | --- | --- | --- |
| D-1 | Referral 3 — crossed-quote disposition | governance **DECIDED**; substance **REFERRED** | A Work PR may not re-dispose a merged audit remedy. Default: restore the R-2 hard assertion |
| D-2 | Referral 4 — drop-ratio acceptance | **REFERRED** | No authority *and* no observational basis exists. Moot under D-1's default |
| D-3 | NR-D — duplicate source minutes | **DECIDED (clarification)** | Abort stands. Playbook §4 names duplicates "fail closed" |
| D-4 | Referral 2 — `missing_minute_count` | **REFERRED** + decided defects | The committed 2-key schema cannot represent drop-induced loss. Continuation blocked until ruled |
| D-5 | NR-A — `artifacts/m15_gate3a/` writability | **DECIDED (clarification)** | §9 is a per-PR scope check. Each artifact's own committed `status` governs |
| D-6 | NR-J — 20 × 3 cost-table coverage | **DECIDED (clarification)** | Coverage must **raise**, grounded independently of R-8 |
| D-7 | NR-C — attestation of `dead_window_bars_present` | **DECIDED** + schema **change** | Measured conjunction over 20 files, attested by the verifier |
| D-8 | Byte-level T-7 proof | **DECIDED** (mostly clarification) + 5 changes | Defined in full: subject, inputs, identity, digest, measurement, tokens, roles, TOCTOU |

**Six items are referred to human + ChatGPT** (§11): the crossed-quote substance,
the drop-ratio rule, the `missing_minute_count` semantics, NR-K (whether
re-hashing a source file violates T-1), the design-span coverage expectation, and
the closure calendar. Each carries a fail-closed default, so the implementing
session is never left without an instruction and never mints a number.

**Two cross-cutting rules** (§10a) close more holes than any individual ruling:
the **negative-control rule** (a field that can only ever hold one value is not
evidence) and **pinned terms** (twenty terms are currently used in incompatible
senses; the decision must *emit* definitions, not prose a later session
re-interprets).

Three results found by adversarial probing changed this document materially, all
lead-reproduced: a **6.67% row-drop ratio is a 100% eligibility loss** (§4); a
**single instant per pair earns the full proof token** because no coverage
requirement exists (§10); and the committed inventory's `eligible_event_count`
is **not** the effective-N spec's `raw_event_count`, so confusing them disarms
`INSUFFICIENT_SAMPLE` (§10a).

**One fact frames everything** (verified from committed metadata, no candle file
opened): **all 20 M1 source files span into the dead window**, and 10 of 20 begin
before design start. The design M15 dataset is a *filter applied to bytes known to
contain the forbidden window*. `dead_window_bars_present: 0` is therefore not a
formality — it is the single assertion stating that the filter worked, and it is
emitted by no code path today.

---

## 2. Authority and method

Read directly at `f2f185e`: the merged audit
(`docs/design/m15_third_independent_source_audit_recheck.md`, **§7/§8 are the
authoritative referral/NR definitions**), `docs/governance/m15_audit_playbook.md`,
`docs/governance/autonomous_development_policy.md`, the frozen pre-registration,
the T-1…T-7 design audit, the merged PR #439 audit record, all eight
`artifacts/m15_gate3a/*.json`, the committed M1 inventory metadata, and the
current source.

**Five independent roles**, none given another's conclusions: contract/governance
consistency · data-integrity/proof-design · adversarial/bypass · testability/
observability · artifact/schema. The lead read the committed artifacts and the
governance texts first, and **independently reproduced every decisive factual
claim** before adopting it. Nothing in this document rests on a role's assertion
alone.

**No real data was read; no M15 derived; no checksum, spread, validation,
holdout, training, inference or execution performed; no broker, external storage
or credential touched; `uv.lock` untouched and `uv sync` never run; no source or
test file changed.** Committed metadata JSON under `artifacts/**` was read, which
the audit method explicitly permits.

---

## 3. D-1 — Referral 3: crossed-quote disposition

**Problem.** Merged PR #439 prescribed a hard per-row `ask_* >= bid_*` assertion
(`m15_aggregation_dataset_machinery_source_audit_recheck.md:411-412`, verbatim:
*"assert `h >= max(o, c)`, `l <= min(o, c)`, `h >= l` per side, and `ask_* >=
bid_*` per row."*). PR #442 re-disposed it to a counted drop, inside a **Work PR**,
citing `scripts/stage25_0a_build_path_quality_dataset.py`.

**Authority.** Policy §14.2 reserves judging *"an independent source-audit
verdict"* to a **Gate-decision PR**; §14.5: *"Having run an internal audit never
excuses skipping a required gate-decision"*; §12: historical audit records *"are
facts and must not be rewritten"*. Pre-registration §11's reuse taxonomy
enumerates what may be reused (`data_adapter.pip_size_for`, `labels.py`, PnL and
metric helpers, the scrubber, the executor) and **`stage25_0a` appears in no
bucket**; §11 classifies archived stage/compare material as *Historical-only*,
and §3.2 bans the `730d_BA` / `3650d_BA` epochs that script consumes. The
implementing session itself conceded the point
(`m15_second_recheck_targeted_fixes_note.md:198-200`: *"It is evidence … **not a
ruling**"*). **No committed authority pins crossed-quote disposition for M15
derivation** — searched pre-registration §4, Ruling 3, the gate-4 design audit §6,
the derivation manifest and the gate-3a adoption record.

**Verified consequence** (lead reproduction — 15 genuine distinct source minutes,
three crossed):

```
eligible                : [False]      <- the bucket loses event eligibility
n_source_bars           : [12]         <- 15 source bars existed
rows_ingested/retained  : 15 / 12
dropped_crossed_quote_rows : 3
```

So the disposition changes `eligible_event_count` — a committed per-file field
(`design_m15_inventory.json:12`) and the denominator of the family's effective-N.
It is **not** diagnostics-only.

### Governance limb — **DECIDED (clarification)**

A Work PR may not re-dispose a remedy recorded in a merged independent
source-audit verdict. PR #442's change is **procedurally void as a contract
disposition**, whatever its technical merits, and the merged R-2 remedy is the
status quo ante. `stage25_0a` is **not admissible authority** for a family-A
design semantic.

### Substance limb — **REFERRED** (`REQUIRES_HUMAN_PLUS_CHATGPT_DECISION`)

Which disposition is *right* is a research judgement, not a governance
determination.

| | Option | `eligible_event_count` | Continuation outcome |
| --- | --- | --- | --- |
| **A** | Hard assert, abort the pair (restores R-2) | unaffected — no artifact unless the pair is clean | Any pair with ≥1 crossed row → no file → the 20-file inventory cannot complete → continuation **halts and escalates**. Fail-closed, reversible |
| **B** | Counted drop (current source) | **decreases** silently | Continuation completes with an unreviewed disposition baked into adopted checksums that no later gate re-derives |
| **C** | Drop with a recorded ratio ceiling | as B, plus refusal above the ceiling | Requires D-2's number, which no authority pins |
| **D** | Abort **and** produce a metadata-only crossed-quote census first | n/a | Gives the decision-maker the counts D-2 needs. New mechanism = contract change; the census is itself a Red read, so a two-phase continuation |

**Fail-closed default until ruled: Option A.** Grounds: it is the only committed
authority; playbook §2 rule 8 requires the narrower reading; and it is the only
option that is simultaneously reversible and self-escalating. **If real data trips
the assertion, that is a STOP-and-refer event** (policy §11), not something the
implementing session resolves.

- **Normative requirement (binding now):** a row with `ask_x < bid_x` for any
  `x ∈ {o,h,l,c}` raises `AggregationError`; no bar for that pair is emitted.
- **Forbidden:** drop-and-count; any lenient mode, flag, kwarg or env var that
  downgrades the error; citing `stage25_0a` or any non-family script as authority.
- **Fail-closed:** any crossed row; any row where the comparison cannot be
  evaluated.
- **Observable outcomes:** a 15-row bucket with exactly one crossed row raises and
  returns **no bar** (not a bar with `eligible: False`); each of the four sides
  crossed in isolation raises, as four separate tests with distinct match strings;
  `ask_x == bid_x` does **not** raise (that is NR-E); the raise survives `python -O`.
- **Freedom:** message wording, check ordering.
- **Required before continuation?** Yes.
- **Class:** governance limb clarification; any outcome other than A is a
  contract change.

---

## 4. D-2 — Referral 4: drop-ratio acceptance

**Problem.** If crossed rows are dropped, nothing decides how much loss makes a
derived file inadmissible.

**Authority.** **None exists.** The source correctly declines to invent one
(`aggregation.py:311-314`; `all_rows_dropped` reported, never raised on).

**A second, independent reason this cannot be decided today** (lead-verified from
committed metadata): the named `source_checksum_authority` records per-file
`duplicate_timestamps`, `monotonicity_violations`, `malformed_rows`,
`missing_fields_count`, `non_finite_fields_count` — **all zero across all 20
files** — and **no crossed-quote counter at all**. Nobody currently knows whether
the design span contains zero crossed rows or a great many. A threshold set now
would have **zero observational basis**.

### **REFERRED** (`REQUIRES_HUMAN_PLUS_CHATGPT_DECISION`)

| | Shape | Trade-off |
| --- | --- | --- |
| **α** | No threshold; human judgement recorded at continuation approval | Mints nothing, but needs a census that does not exist — forces D-1 option D, or a judgement *after* the adoption run |
| **β** | Pin a ratio now | Deterministic, but numerology — there is no observation to calibrate against |
| **γ** | Fail-closed on any drop | Collapses into D-1 option A; this referral becomes moot |

### The reported ratio is the wrong quantity — **DECIDED**

Lead-verified, and decisive for how this referral may be resolved. One crossed
minute in each of ten buckets:

```
rows_ingested / rows_retained            : 150 / 140
row-drop ratio (the only ratio derivable): 0.0667
eligible buckets                         : 0 of 10
ELIGIBILITY loss ratio                   : 1.0000   <- 15x the row-drop ratio
committed gap_report                     : missing_minute_count=0 max_gap_minutes=0
```

**A 6.7% row-drop ratio is a 100% eligibility loss**, because one dropped minute
costs an entire bucket's eligibility. The amplification is up to 15×, and the
quantity that matters is reported nowhere. Portfolio aggregation compounds it:
nineteen clean pairs and one destroyed pair average to ~0.3%.

**Fail-closed default: no threshold may be minted, and under D-1's default
(Option A) this referral is moot.** If the ruling selects B or C, the approval
submission must report — **per pair and per calendar month, never portfolio- or
span-aggregated**:

1. `rows_dropped`, split by named anomaly class;
2. `eligible_event_count` as derived **and**
   `eligible_event_count_counterfactual_no_drops` — the eligibility the file
   would have had with no drop — plus their difference and ratio;
3. the longest run of consecutive lost eligible buckets;
4. the **maximum** of (2)'s ratio over all 20 pairs and all months, as the
   headline figure.

The judgement is made on (4). **A submission reporting only a row-drop ratio, or
only a portfolio figure, is not a valid approval submission** — it invites a
decision on a number up to 15× too small.

- **Forbidden:** any comparison of a drop count or ratio against a literal; any
  "sane default"; deriving a threshold from the M1 lineage's `gap_profile` by
  analogy.
- **Observable outcomes:** no entry point exposes a ratio parameter with a numeric
  default; if a ratio gate is ever added, omitting the bound **raises** rather
  than defaulting (the `cost_schema.max_spread_pips` precedent).
- **Required before continuation?** Yes if D-1 resolves to B or C; moot under A/γ.
  **Decide with D-1, in one ruling.**

---

## 5. D-3 — NR-D: duplicate source minutes — **DECIDED (clarification)**

**Problem.** `aggregation.py:195-198` aborts the whole pair on a duplicate minute
while crossed quotes are dropped — two opposite dispositions, the asymmetry
unstated.

**Authority — this one *is* pinned.** Playbook §4, `m15_audit_playbook.md:210-211`
(lead-verified verbatim): *"15 DISTINCT minute-aligned source minutes for
eligibility; **duplicates + sub-minute timestamps fail closed**"*. Duplicates are
the one anomaly class committed governance names this way. Ruling 3 (FROZEN)
requires 15 **distinct** minutes. The lineage's inspection protocol records
anomalies and **corrects nothing**.

**Decision: the abort stands.** The asymmetry is principled, not arbitrary: a
crossed quote is one identified bad *row*; a duplicate minute means the input's
*identity* is untrustworthy — two records claim one minute and nothing says which
is real, so keeping either would be a blind choice, and it is exactly the
"distinct" property Ruling 3 freezes. Lead-verified from committed metadata:
`duplicate_timestamps` totals **0 across all 20 source files**, so the strict
choice costs nothing on the actual design-span input.

- **Normative requirement:** a second record for a minute already claimed within a
  bucket raises `AggregationError`; no bar for that pair is emitted. The minute is
  claimed **before** any quality disposition is applied, so a dropped anomalous row
  still consumes its minute and cannot be substituted (already correct at
  `aggregation.py:193-199` — **preserve this ordering under every D-1 outcome**).
- **Forbidden:** deduplication; first-wins or last-wins; tolerating a duplicate
  differing only in sub-minute remainder; any lenient mode.
- **Observable outcomes:** two records for one minute → raise, no bars; the
  claim-before-drop ordering pinned under **both** D-1 outcomes; nanosecond-
  differing duplicates raise via the **duplicate** guard, with a match string
  distinct from the timestamp guard's.
- **Consistency constraint:** if D-1 is ruled to B or C, the ruling must **state
  why the two anomaly classes differ**. Moving duplicates to a counted drop would
  contradict playbook `:210-211` and needs its own ruling — it must not be done as
  a tidy-up alongside D-1.
- **Required before continuation?** Yes. **Class:** clarification.

---

## 6. D-4 — Referral 2: `missing_minute_count` semantics

**Problem.** The committed schema (`design_m15_inventory.json:15`) is exactly
`{"missing_minute_count": "int", "max_gap_minutes": "int"}`; `_build_gap_report`
emits **17** keys. The continuation must populate the field and cannot without
deciding its meaning.

### Decided defects (independent of the ruling)

**(a) `total_missing_source_minutes_within_emitted_buckets` is misnamed.**
Lead-verified: 15 **present** source minutes with 3 crossed →
`total_missing_source_minutes_within_emitted_buckets: 3` although no minute is
absent, and `n_source_bars: 12` although 15 source bars existed. This contradicts
the module's own docstring (`aggregation.py:305-309`: *"the gap metrics describe
SOURCE coverage, the drop counters describe quality rejection"*). A counter must
mean what its name says. **DECIDED: rename to separate *absent* from *rejected*,
and stop redefining `n_source_bars` from source to retained.**

**(b) The committed 2-key schema cannot represent drop-induced loss.**
Lead-verified, the decisive scenario — bucket 0 entirely crossed, bucket 1 clean:

```
rows_ingested / rows_retained : 30 / 15        (50% of the file lost)
what the COMMITTED inventory would carry: {'max_gap_minutes': 0, 'missing_minute_count': 0}
reads as a GAPLESS, fully-eligible file? -> True
```

**A file that lost half its source minutes is indistinguishable, in the committed
inventory, from a perfect file.** This couples D-4 to D-1: under D-1's default
(abort) no drops exist and the 2-key schema suffices; under a drop disposition the
schema **must** be extended, which is a contract change.

### **REFERRED** (`REQUIRES_HUMAN_PLUS_CHATGPT_DECISION`)

Undecided: whether `missing_minute_count` counts market-closure minutes; whether
leading/trailing partial buckets contribute; and which keys beyond the committed
two survive into the artifact.

Measured behaviour today, offered as evidence, not as a recommendation: a 48 h
closure yields `missing_minute_count: 2865`; leading and trailing partial buckets
contribute `0`. Supporting evidence for the "count closure" reading: the M1
predecessor inventory named as `source_checksum_authority` carries a `gap_profile`
whose histogram counts closure gaps — **a different key, unit and structure, so it
informs the decision without settling it.**

**Fail-closed default: the continuation does not proceed.** This is a
`MUST_RESOLVE` referral; there is no default semantic, because populating a
committed field with an undecided meaning is precisely the failure to be avoided.

- **Normative requirement once ruled:** the artifact must carry an explicit
  `missing_minute_count_semantics` token recording the ruling, so the artifact is
  self-describing and a later change cannot be silent. The aggregation function's
  return value must be **projected** onto the ruled key set by a named, tested
  mapping — never passed through.
- **Observable outcomes:** `set(record["gap_report"]) == RULED_KEYS` exactly for
  all 20 records; a one-minute hole yields `missing_minute_count == 1` (kills the
  surviving `hole > 0 → hole > 1` mutant); the accounting identities in §13 hold
  on a fixture containing both a closure gap and a rejected minute; **scenario (b)
  above must not read as gapless in whatever schema is ruled.**
- **Required before continuation?** Yes. **Class:** the semantics ruling is a
  clarification; every key beyond the committed two is a **contract change**.

---

## 7. D-5 — NR-A: is `artifacts/m15_gate3a/` immutable or the output directory? — **DECIDED (clarification)**

**Problem.** Playbook §9 lists it under *"prior evidence directories untouched"*;
§5 requires the continuation to populate `design_m15_inventory.json` inside it.

**Authority.** §9 is headed *"Merge approval checklist (standard, every Amber/Red
PR) — Run these read-only checks **immediately before merging an approved PR**"*,
and its neighbouring item is *"touched files exactly match the **approved
scope**"*. Read together, "untouched" means *this PR did not touch prior evidence
outside its approved scope* — not "these bytes are frozen forever". The tree's own
contents settle the rest: **each artifact's committed `status` field declares its
own writability**, and four of the eight carry `…AT_IMPLEMENTATION` /
`PENDING` / `TO_BE_CREATED_AT_GATE5` markers that are unintelligible under an
immutability reading.

**Decision — the per-file rule, derived from each artifact's own committed status:**

| File | Committed status | Rule |
| --- | --- | --- |
| `design_m15_inventory.json` | `SCHEMA_FIXED__POPULATED_AT_IMPLEMENTATION` | **Populate-once.** `required_schema_per_file` and `required_aggregate_assertions` may not be weakened. Once populated with real checksums it is frozen; a re-derivation changing any `sha256` is a **new adoption gate**, not an overwrite |
| `design_m15_derivation_manifest.json` | `DERIVATION_CONTRACT_FIXED__BYTE_PRODUCTION_DEFERRED_TO_IMPLEMENTATION` | **Field-restricted.** Only `derivation_identity_required_at_implementation` (script path, git SHA, config hash) may be completed. `input_identity`, `design_span_cut`, `aggregation_contract` immutable |
| `no_overlap_proof.json` | `SOURCE_LEVEL_PROOF_PROVEN (A1-A4); BYTE_LEVEL_PROOF PENDING` | **Byte-frozen.** A1–A4 and `boundary_constants_utc` immutable. A5 is discharged by a **new** artifact (§10), not by rewriting this file |
| `effective_n_estimator_spec.json` | `APPROVED_SPEC` | **Immutable. Never written by any continuation.** Change needs a new human + ChatGPT ruling |
| `forward_epoch_inventory.json` | `EMPTY__NO_FORWARD_DATA_EXISTS` | **Immutable at this gate.** Writing it is a forward-epoch adoption — forbidden |
| `forward_epoch_adoption_manifest.json` | `ADOPTION_BLOCKED__FORWARD_DATA_NOT_YET_ACCRUED` | **Immutable at this gate** |
| `cost_table_plan_or_metadata.json` | `option_selected: B__DEFER_…` | **Untouched unless cost-table production is explicitly authorised.** Its `must_produce_before_gate7_authorisation` block is immutable and is the acceptance spec |
| `scrub_report.json` | — | **Regenerated**, and must name every artifact the continuation writes |

### How the population happens — the mechanism, decided on evidence

Two roles disagreed here and the disagreement is resolved by a fact, not a vote.
One argued for populate-once **inside** the tree (the artifacts' own `status`
fields say they are to be populated); the other argued the tree must be
protected-immutable, because *"populate-once" and "append-only" are unobservable*
— nothing after the fact distinguishes a first write from a second, and JSON is
not appendable.

Both are right, and the committed history reconciles them: **all eight artifacts
were added by a single human-reviewed PR diff** (`7e795d4`, PR #431). No code path
has ever written into `artifacts/m15_gate3a/`.

**Decision.** The continuation's code writes its outputs to a **separate output
directory**; the population of `artifacts/m15_gate3a/` happens through the
**human-reviewed PR diff** that lands the continuation's evidence — exactly as
every artifact there arrived. This satisfies the authority (the artifacts *are*
populated at implementation) and the observability objection (no runtime write
into the protected tree, so the rule is enforceable rather than promised).

- **A trap the fix PR must not fall into.** Do **not** close audit blocker B-5 by
  adding `artifacts/m15_gate3a` to `guards._PROTECTED_PREFIXES` *and stopping
  there* while §5 still names it as the write target — resolve it by the separate
  output directory above, then the prefix may be added safely. B-5's other content
  stands: **`data/`, `models/`, the 730d/3650d PR-B.1 evidence trees — and
  `docs/`, which currently permits `write_metadata_artifact` to target the
  governance tree itself — are unprotected** and must be added.
- **New containment requirement (lead-verified).** `refuse_real_path` is
  **cwd-dependent on relative paths**: from a different working directory,
  `artifacts/ml_step4/365d_ba_v1` is **ALLOWED** while its absolute spelling is
  REFUSED. Callers must pass absolute paths, or the guard must anchor relative
  paths at the repo root. This matters because the continuation's reader takes a
  data root as a runtime argument.
- **Observable outcomes:** a write to `effective_n_estimator_spec.json` refuses,
  **and the on-disk bytes are unchanged** (assert content, not just the raise);
  writes to either forward artifact refuse; `data/`, `models/` and both PR-B.1
  trees refuse; the negative case is built under `tmp_path` with the authority
  root monkeypatched, so it cannot pass because of host state.
- **Governance-doc consequence:** playbook §9's line should read "untouched
  **outside the PR's approved scope**". Folded into this PR (policy §14.6).
- **Required before continuation?** Yes. **Class:** clarification.

---

## 8. D-6 — NR-J: 20 × 3 cost-table coverage — **DECIDED (clarification)**

**Problem.** Merged R-8 required four fixes *"before the tables are produced"*.
Three landed; the fourth — coverage — became a reported boolean with no raise
(`cost_schema.py:214`), and the change was never referred.

**Authority, independent of R-8.** Pre-registration `:116-117` (lead-verified
verbatim): *"pair universe fixed at **PAIRS_20** … — **no inclusion/exclusion
decisions anywhere in this family**"*; Ruling 4 freezes the three sessions;
`cost_table_plan_or_metadata.json` fixes granularity *"per pair x session"*; and
every barrier, floor and EV test in Ruling 6 is a function of `cost(pair,
session)`. **A missing cell is operationally a pair-or-session exclusion**, which
the frozen contract forbids. So coverage is derivable from the contract itself —
the audit's remedy and the contract agree.

**Decision.** A cost-table metadata object that does not carry all
`20 × 3 = 60` distinct `(canonical_pair, session)` cells must **not** validate:
`validate_cost_table` raises. `full_20x3_coverage` may remain as a diagnostic but
must be `True` in every summary ever returned. The re-disposition was a §14.2
violation of the same class as D-1 and is recorded as corrected.

- **Forbidden:** any flag, mode or default permitting a partial table to validate;
  treating the boolean as sufficient; producing or committing a partial table.
- **Observable outcomes:** a 59-cell table raises; a 60-cell table validates; a
  one-entry table raises (R-8's own reproduction); the error names the missing
  cells; the mutant `len(seen) == 60 → True` is killed. **The existing test that
  currently pins the re-disposition as correct behaviour must be rewritten or
  deleted** — leaving it is how the re-disposition becomes permanent.
- **Required before continuation?** Binds before cost tables are produced; the
  **governance correction is required now** regardless. `20 × 3` mints nothing —
  both operands are already frozen.
- **Class:** clarification.

---

## 9. D-7 — NR-C: who attests `dead_window_bars_present: 0`

**Problem.** Declared at `design_m15_inventory.json:22`, emitted by **no code
path**, with no per-file counterpart to rest on, and the term "dead-window bar"
undefined.

**Decision — DECIDED (principle), with a contract change for the schema.**

- **It is a measured aggregate, never a declaration.**
  `dead_window_bars_present := Σ` of the 20 per-file measured counts. Satisfied
  **iff** the sum is 0 **and** all 20 were measured. A missing measurement makes
  it **unsatisfied**, never vacuously true. The same rule governs
  `all_ts_max_within_design_end`, `all_ts_min_within_design_start` and
  `file_count`.
- **Who attests:** the **Verifier** (§10), never the producer, never a human
  transcription. This extends the committed rule *"Fabricating checksums here is
  forbidden"* to the aggregate that depends on them.
- **Bar membership — both definitions, both zero (fail-closed).** Under a
  *correct* bucketer, "bucket-start in the dead window" and "any contributing
  source minute in the dead window" coincide; they diverge exactly when the
  implementation is wrong, which is the only case the assertion exists to catch.
  Both are therefore measured and both must be 0.
- **Contract change (requires approval):** `required_schema_per_file` gains
  `dead_window_bar_count`, `dead_window_bucket_starts`, `bars_before_design_start`,
  `bars_after_design_end` — non-negative ints, all measured.
- **Observable outcomes:** a synthetic file whose bar has a clean bucket start but
  one contributing minute inside the dead window yields
  `dead_window_bar_count = 1`, `dead_window_bucket_starts = 0` → refused (this is
  the test that distinguishes the two definitions); the aggregate asserted with
  only 19 per-file counts → unsatisfied; a per-file count of `None` → unsatisfied,
  never coerced to 0; no token is reachable from a producer-only attestation.
- **Required before continuation?** Yes.

---

## 10. D-8 — The byte-level T-7 proof contract

**Problem.** `assert_per_file_bounds` emits `PROVEN_NO_DEAD_WINDOW_OVERLAP` from
caller-declared metadata; 20 plain ISO strings earn the token with no file access
(lead-reproduced). Playbook §5 requires a **byte-level** proof.

**The committed record already anticipates this.** `no_overlap_proof.json`
separates `SOURCE_LEVEL_PROOF_PROVEN (A1-A4)` from `BYTE_LEVEL_PROOF PENDING (A5
at implementation; A6 when forward data accrues)`, and A5 reads *"design-M15
derived artifacts must satisfy per-file `ts_max <= design_end`"*. Most of what
follows is therefore **clarification of a contract already written**, not new
invention.

### The thirteen questions, answered

1. **Subject of the proof** — the **bytes of the 20 derived design-M15 files**.
   Authority: `design_m15_inventory.json:9` (`"sha256": "64-hex of the derived M15
   file bytes"`). The M1 source bytes are a *bound input*, not the subject, and are
   constitutionally unable to satisfy T-7 (all 20 span the dead window).
2. **Proof inputs** — the frozen boundary constants; the committed M1 inventory
   (source identity); the derivation manifest; the design inventory; `PAIRS_20`;
   the derived M15 bytes; and the realised derivation identity (script path, git
   SHA, config hash).
3. **File identity** — the triple **(canonical pair, filename, sha256)** plus
   `size_bytes`. **Never by path** — the committed M1 inventory records no path,
   and playbook §2 rule 7 bans local paths from artifacts. The data root is a
   runtime argument, never committed.
4. **Digest — REQUIRED. SHA-256, whole file, lowercase 64-hex.** Adopted from
   committed authority, not minted: `design_m15_inventory.json:9`,
   `design_m15_derivation_manifest.json:12`, and the repo's existing checksum
   helpers. No truncated digest, no alternative algorithm.
5. **Auxiliary metadata — required, each with a job.** `size_bytes` catches
   truncation independently of the digest; `row_count` binds the digest to a
   *parse* of the same bytes; `eligible_event_count` is the effective-N
   denominator (its value depends on D-1); `gap_report` is coverage (D-4);
   `pip_size` is a consistency check, not a measurement.
6. **Binding a declared span to actual content — single-pass co-measurement.**
   The producer opens each file **once**; one block loop feeds the SHA-256, the
   byte counter and the row parser; **every scalar in the record is produced by
   that one pass and the record is constructed atomically at its end.** There is
   no code path by which `ts_min_utc` can originate from anything other than the
   bytes that produced `sha256`. This is the mechanism the repo's own committed M1
   inventory was produced by — adopted, not invented.
7. **What T-7 proves — four limbs, named separately.**
   **BI (byte identity):** 20 distinct, whole, digest-identified files, digest
   reproducible on re-read, `size_bytes` and `row_count` agreeing.
   **TC (time containment):** measured from those same bytes — `ts_min ≥
   DESIGN_START`, `ts_max ≤ DESIGN_END`, and `dead_window_bar_count == 0`. The
   count is strictly stronger than the endpoints: endpoints cannot exclude an
   *interior* bar, and the interior is where a bucketing bug hides.
   **CV (coverage) — newly required; see below.**
   **DB (derivation binding):** the bytes are the output of the named script at
   the named git SHA and config hash, byte-reproducible on re-run.
   **Playbook §5's "byte-level no-overlap proof" = BI ∧ TC ∧ CV**, with DB
   co-required by pre-registration §4.

   **Why CV is not optional — lead-verified.** The current proof enforces a
   *ceiling*, never *coverage*. `DESIGN_START` is a floor on `ts_min`, and no
   committed aggregate assertion constrains row counts or span extent:

   ```
   full design span    -> PROVEN_NO_DEAD_WINDOW_OVERLAP  files_checked=20
   ONE DAY only        -> PROVEN_NO_DEAD_WINDOW_OVERLAP  files_checked=20
   a single instant    -> PROVEN_NO_DEAD_WINDOW_OVERLAP  files_checked=20
   last month only     -> PROVEN_NO_DEAD_WINDOW_OVERLAP  files_checked=20
   ```

   A derivation that silently truncated to the last month — or emitted **one bar
   per pair** — earns the identical token as the full ten-month span. Every
   downstream acceptance metric would then be computed on a fraction of the design
   data with nothing in the evidence chain showing it. **The proof record must
   therefore carry measured `ts_min`/`ts_max` and `row_count` per pair, and the
   approval must name the expected span and a per-pair row-count expectation
   range.** Those expectation numbers are `REQUIRES_HUMAN_PLUS_CHATGPT_DECISION`
   (§11) — this document does not mint them.
8. **Roster** — exactly 20; canonical roster **equals** PAIRS_20. There is no
   partial proof: 19 proven files earn nothing.
9. **Duplicate / alias / substitution — eight layers.** Three exist today (record
   `id()`, duplicate `filename`, duplicate `sha256`). Five are added:
   **filename↔pair coherence** (today the two keys are validated independently and
   never cross-checked); **the digest is measured, not declared**; **source-side
   substitution** (subject to NR-K); **filesystem identity** — no two roster
   entries may resolve to the same object (`os.path.samestat`), which catches
   hardlink/junction substitution that distinct filenames and distinct digests both
   miss; and **cross-artifact binding** — the proof's 20 triples must equal the
   inventory's.
10. **Proof record contents** — per file: `pair`, `filename`, `sha256`,
    `size_bytes`, `row_count`, `ts_min_utc`, `ts_max_utc`, `dead_window_bar_count`,
    `dead_window_bucket_starts`, `bars_before_design_start`,
    `bars_after_design_end`, `eligible_event_count`. Proof-level: `proof_class`,
    `subject`, `digest_algorithm`, `measurement_method`, `evidence_basis`,
    `boundary_constants_utc`, `roster_binding`, `producer_identity`,
    `verifier_identity`, `source_identity`, `inventory_binding` (the inventory's own
    sha256), `result`. **Forbidden in the record:** any path, data root, price, row,
    spread or strategy metric.
11. **Token vocabulary — the single token must be split.** A consumer currently
    cannot tell that the evidentiary basis is caller-supplied metadata.

    | Token | What a consumer may conclude | Reads bytes |
    | --- | --- | --- |
    | `SOURCE_LEVEL_PROOF_PROVEN` *(existing)* | The frozen spans are ordered and disjoint (A1–A4). **Nothing about any file** | no |
    | `DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL` *(replaces the current token)* | 20 distinct, roster-complete, identity-keyed **declarations** are internally consistent. **No claim about any file's contents** | no |
    | `BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN` | For 20 files identified by **measured** sha256: every bar in `[DESIGN_START, DESIGN_END]` and `dead_window_bar_count == 0`, measured from the bytes that produced the digest and independently re-measured | yes |
    | `DERIVATION_IDENTITY_BOUND` | Those bytes are reproducible from the named source by the named script/SHA/config | yes |
    | `BYTE_LEVEL_PROOF_PENDING` *(default)* / `BYTE_LEVEL_PROOF_REFUTED` | No byte-level claim / a re-verification disagreed (terminal) | — |

    Only `BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN` **∧** `DERIVATION_IDENTITY_BOUND`
    satisfies playbook §5, §6 ("No consumed-window leakage") and §8 ("dead-window
    exclusion (byte-level proof holds)"). `BYTE_ADMISSIBLE` is deliberately **not**
    used and remains forbidden.
12. **Generation / verification separation — yes, three components.**
    **C (Checker)** = `scripts/m15_gate3a/**`, **never reads**; maximal claim
    `DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL`. **P (Producer)** and
    **V (Verifier)** are new packages **outside** it, following the in-repo
    `scripts/_gate_p1_inspector/**` precedent (the read-only package that produced
    the committed M1 inventory). V must not reuse P's scalar-derivation code — only
    the frozen constants and the timestamp/pair/path authorities, so `DESIGN_END`
    has exactly one definition.
    **Why the split is mandatory:** the audit proved `scripts/m15_gate3a/**`
    contains *no read primitive at all*; keeping P and V outside is what preserves
    that audited property. The pure aggregation core is reused, not re-implemented.
    **Import direction is one-way and must be pinned by a test.** This *adds
    reverse callers* to a package the audit recorded as having none outside its
    tests — that change must be declared and re-derived by the next independent
    re-check.
13. **TOCTOU — three named windows.**
    **W1 derivation → digest:** write to a temp name, `flush()`+`fsync()`, hash,
    **re-open and re-hash requiring equality**, then atomically rename. Residual
    risk on a shared filesystem is declared, not hidden.
    **W2 digest → inventory write:** the record is built atomically at the end of
    the single pass; the inventory's own sha256 is recorded in the proof, so a
    later edit is detectable.
    **W3 inventory → consumption:** the long window — months may elapse. **Every
    consumer must re-verify a file's digest before reading any row**, and refuse on
    mismatch. This is a *precondition of use*, not a one-time proof, and must be
    wired into the feature/label/training entry point when it is built.

### Class

**Clarifications:** the token split; single-pass co-measurement; the C/P/V role
split and placement; the consumer re-verification duty; that A5 is discharged by
measurement rather than declaration; identity by triple, not path.

**Contract changes (require approval):** (a) the four new measured per-file fields
(D-7); (b) redefining `dead_window_bars_present` as a measured conjunction;
(c) retiring the `PROVEN_NO_DEAD_WINDOW_OVERLAP` token emitted by merged code;
(d) permitting reverse callers of `scripts.m15_gate3a`; (e) a **new** artifact
`design_m15_byte_level_no_overlap_proof.json` rather than rewriting the frozen
`no_overlap_proof.json`.

---

## 10a. Two cross-cutting rules

These close more holes than any individual ruling, and both are **observable** —
a reviewer can check compliance without re-deriving anything.

### R-1 — The negative-control rule (**DECIDED**)

`scripts/m15_gate3a/**` and the committed artifacts currently emit **eleven
hard-coded self-attestations**: `imputation: False`, `synthetic_weekend_bars:
False`, `mid_price_constructed: False`, `p95_diagnostic_present: True`,
`real_spreads_computed: False`, `strategy_metrics_computed: False`,
`first_w_bars_event_eligible: False`, **`dead_window_loaded: False`**,
`no_raw_data_read_at_gate3a: true`, `"result": "ALL_SCRUB_CLEAN"`, and
`MAGNITUDE_AUTHORITY_STATUS`. None can ever take the other value, so none is
evidence — yet each reads to a downstream consumer as a measured fact.
`dead_window_loaded: False` is the **T-1 leakage claim itself**, emitted as a
constant.

> **No artifact field may assert a property unless the same code path, exercised
> in the same run, is demonstrated to emit the opposite value on a deliberately
> constructed counter-case, and that demonstration is recorded alongside the
> attestation. A field that can only ever hold one value is deleted, not
> reported.**

This applies to every boolean and every result token in `artifacts/m15_gate3a/**`
and in the continuation's outputs. It subsumes the `full_20x3_coverage` defect
(D-6) and the proof-token defect (D-8) as instances of one class.

### R-2 — Pinned terms (**DECIDED**; the decision must *emit* definitions, not prose)

The audit's deepest structural risk is that a ruling in prose gets re-interpreted
by the fix session. Twenty terms are currently used in two or more incompatible
senses across committed documents and code. **The fix PR may not proceed until
each is pinned by naming the quantity measured, its unit, and whether it is
declared or measured.** The most dangerous three:

- **`n_source_bars`** — source minutes observed · rows retained after quality
  drops · number of *reads*. Currently it silently means the second (verified),
  and can be inflated to the third by a repeated row object (audit RF-4).
- **`eligible_event_count` vs `raw_event_count`** — the committed inventory
  defines `eligible_event_count` as *"count of `n_source_bars==15` buckets"*,
  while the approved effective-N spec defines `raw_event_count` as *"eligible
  **traded** events (buckets that pass the cost-hurdle and fire an EV-gated
  trade)"* (both verbatim, lead-verified). These are different quantities with
  confusable names. Feeding the first where the second is meant clears the frozen
  floors (raw ≥ 1000, N_eff ≥ 400) by orders of magnitude and **disarms
  `INSUFFICIENT_SAMPLE`, the family's principal honest-failure mechanism.**
  Pin three distinct names — `complete_bucket_count`, `cost_hurdle_eligible_bar_count`,
  `raw_traded_event_count` — and require `effective_n()` to take a mandatory
  literal declaring which it is being passed.
- **"proof" / `PROVEN`** — declaration-consistency vs byte-level (D-8).

The remaining seventeen — `missing_minute_count`, `max_gap_minutes`, "gap",
`row_count`, "source bar"/"source minute", `sha256` vs lineage `file_sha256`,
`ts_min_utc`/`ts_max_utc` (declared vs measured; 6 vs 9 fractional digits),
"untouched", "verified"/"certified", "byte-reproducible" (asserted vs
demonstrated), `dead_window_bars_present`, "spread" (close-only vs open-side;
price vs pips), "drop" (rows vs minutes vs **eligibility**), "duplicate",
`ts` vs the source's `time` key, "coverage", and "synthetic-only" — are listed so
the fix PR pins them in one pass rather than discovering them one defect at a
time.

## 11. Items requiring a human + ChatGPT decision

| Ref | Question | Fail-closed default until ruled |
| --- | --- | --- |
| **D-1 substance** | Crossed quotes: hard abort (A) / counted drop (B) / drop + ratio (C) / abort + census (D) | **A** — restore the merged R-2 assertion |
| **D-2** | Drop-ratio: no threshold + recorded judgement (α) / pinned ratio (β) / fail-closed on any drop (γ) | **No number may be minted.** Moot under D-1 = A |
| **D-4** | `missing_minute_count`: closure counted or not; partial-bucket contribution; which keys survive into the committed schema | **The continuation does not proceed** |
| **NR-K** *(new, raised here)* | Does re-hashing an M1 source file violate T-1's *"dead-window data is NEVER loaded for any purpose"*? All 20 source files span the dead window, so a whole-file digest streams dead-window bytes through the process | **Option A (narrow):** no source re-hash; the reader terminates early at the first timestamp past `DESIGN_END`, licensed by the committed `monotonicity_violations: 0` and re-asserted live; record `source_digest_reverified: false`. Zero dead-window bytes enter the process — but source substitution becomes unverifiable |
| **Coverage expectation** *(new, D-8 limb CV)* | The expected design span and per-pair `row_count` expectation range, without which a one-day derivation earns the same proof token as the full span | **The proof records measured span and row counts; no token may be issued until the approval names the expectation** |
| **Closure calendar** *(new)* | Which rule splits closure-attributable from in-session missing minutes — a fixed weekly Fri-close/Sun-open rule, or an observed-data rule. Both are defensible | Continuation does not proceed (part of D-4) |
| Schema changes | The four measured fields; the `gap_report` extension; the new proof artifact; token retirement; permitting reverse callers; renaming `eligible_event_count` | Not implemented until approved |

**A read-only crossed-quote counting gate.** D-1 and D-2 would be ruled blind: the
committed source inventory carries counters for duplicates, monotonicity,
malformed rows, missing and non-finite fields — **all zero across all 20 files** —
and **no crossed-quote counter at all**. Either D-1 is ruled conservatively
without measurement (Option A, making D-2 moot), **or** a new, narrowly-scoped,
read-only counting gate is approved that opens the 20 committed M1 files, counts
crossed-quote rows and their bucket-level clustering per pair per month, writes
**counts only** — no prices, no rows, no derivation, no M15 — and stops. That gate
does not exist, is a real-data read (**Red**), and requires human + ChatGPT
approval before it runs. This document does not create it.

Also referred, with reasons, and **not** promoted: referral 1 (spread magnitude
bound) and referral 5 (forward evidence shape) remain
`MAY_DEFER_BEYOND_GATE3A_CONTINUATION`; NR-F, NR-G, NR-I bind at later gates.
**NR-E is coupled to D-1**: `cost_schema.py:181-186` accepts a zero spread on the
same `stage25_0a` analogy this decision rules inadmissible, so the ruling should
either restate zero-spread acceptance on independent grounds or refer it.
**NR-B**: the *emission* format is decided (§12); the *ingestion* rule for the
committed 9-digit M1 timestamps requires an explicit choice, and deferral requires
a decision rather than silence.

---

## 12. Normative requirements handed to the targeted-fix Work PR

Numbered so the fix PR can cite them. None requires an implementer contract choice.

1. Crossed quote → `AggregationError`, no bar emitted (D-1 default).
2. Duplicate minute → `AggregationError`, no bar emitted; the minute is claimed
   **before** any quality disposition (D-3).
3. No drop-ratio threshold may be minted, defaulted or inferred (D-2).
4. Rename the misnamed counter; stop redefining `n_source_bars` from *source* to
   *retained* (D-4a).
5. Do **not** add `artifacts/m15_gate3a` to `_PROTECTED_PREFIXES`. **Do** add
   `data/`, `models/`, `artifacts/gate_p1_pr_b/firstrun_730d_ba`,
   `artifacts/gate_p1_pr_b/firstrun_3650d_ba` (D-5, audit B-5).
6. `refuse_real_path` must not be cwd-dependent: anchor relative paths at the repo
   root or require absolute paths (D-5).
7. Full 20 × 3 cost-table coverage must **raise**; rewrite the test that currently
   pins the re-disposition (D-6).
8. Aggregate assertions are conjunctions/sums over 20 **measured** per-file values;
   a missing value makes them unsatisfied, never true (D-7).
9. `scripts/m15_gate3a/**` must remain **reader-free**; its maximal claim is
   `DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL` (D-8).
10. Emit `spread_open = ask_o − bid_o` per bar, finiteness- and sign-checked like
    `spread_close`, computed from the first **retained** minute (audit RF-18 —
    required by pre-registration §4 and the derivation manifest; the field name is
    the only free variable).
11. Emit timestamps as `YYYY-MM-DDTHH:MM:SSZ` — literal `Z`, no fractional part —
    through a single formatter; `datetime.isoformat()` (which produces `+00:00`)
    must not reach any artifact (NR-B emission limb).
12. Correct `aggregation.py:36-38`, which states *"Aborting the whole pair was this
    package's own invention"* — the merged PR #439 audit prescribed it, and the
    implementing session already retracted the claim in its own note without the
    retraction reaching the source. Required under **every** D-1 outcome.
13. Apply the **negative-control rule** (§10a R-1): every attested boolean and
    result token either gains a demonstrated counter-case or is deleted. Start
    with `dead_window_loaded`, `imputation`, `synthetic_weekend_bars`,
    `mid_price_constructed`, `real_spreads_computed`,
    `strategy_metrics_computed`, `p95_diagnostic_present`.
14. Pin the twenty terms (§10a R-2) in one pass; rename `eligible_event_count`
    to `complete_bucket_count` and require `effective_n()` to take a mandatory
    literal naming which quantity it is being passed.
15. Add the record-identity guard to aggregation that `no_overlap._materialise`
    already has: one row object presented 15 times currently yields
    `n_source_bars: 15, eligible: True` (audit RF-4). Every accounting identity in
    §13 balances on fabricated terms without it.
16. **Schema shape constraint (non-negotiable, lead-verified).** The continuation's
    inventory is writable **only** if per-file records stay **nested** with **≤5
    immediate numeric fields**; six refuses, and flattening `gap_report` refuses.
    A populated 20-record instance must be asserted to pass `scan_gate3a` **before**
    any derivation — otherwise the run discovers its output is unwritable after the
    fact. Note the scrubber currently **refuses the committed M1 predecessor
    inventory's own record shape**, falsifying `artifacts.py:68-69`'s calibration
    claim; that is audit blocker B-1's allowlist redesign, not a threshold to raise.

---

## 13. Observable outcomes and the test acceptance bar

**Accounting identities** — decision-independent; they must hold under every
candidate disposition and be asserted parametrically over the scenarios in §6:

| ID | Identity |
| --- | --- |
| I-1 | `rows_ingested == rows_retained + total_dropped` |
| I-2 | `sum(n_source_bars) == rows_retained` |
| I-3 | `absent_in_emitted_buckets == 15 × n_buckets_emitted − rows_retained` |
| I-4 | `n_buckets_emitted + fully_dropped + missing_whole_buckets ==` slots spanned |
| I-5 | `n_eligible + n_incomplete == n_buckets_emitted` |
| I-6 | `missing_minute_count ==` span-in-minutes − distinct observed minutes |

**Anti-patterns forbidden**, each grounded in a defect already found in this
suite: alternation in `pytest.raises(match=...)` that cannot identify which guard
fired (this is what concealed the audit's B-7a for three rounds); tests asserting
on **source text** instead of behaviour; vacuous globs with no non-vacuity floor;
tests that pass because of host state; tests that freeze a fail-open as expected
behaviour; broad exception types where the module defines its own;
`# pragma: no cover` on a reachable guard.

**Acceptance bar for the fix PR:** all 19 genuine mutation survivors from the
merged audit killed; both epoch-range limbs pinned **in isolation**; all four
package status constants pinned; every blocker B-1…B-7 and required fix
RF-1…RF-29 carrying a failing-before/passing-after regression test; the mutation
study re-run and reported in the audit's table shape; **no newly-introduced
survivor** (PR #442 introduced four defects while fixing five — this is the check
that catches that class).

**What is testable now vs only under the authorised run.** Every mechanism above
is synthetically testable today on scratchpad fixtures — digests over known bytes,
spans over known timestamps, injected dead-window bars, hardlinked files,
truncated files, disagreeing producers. **Only the values require the run.** Six
outcomes are structurally unreachable without it: the 20 real digests, the real
measured spans, the real dead-window counts, P/V agreement on real data,
re-derivation reproducibility, and the per-pair drop ratios.

---

## 13a. Disagreements between roles, and how they were resolved

Resolved on evidence, never by majority (policy §13.2).

- **NR-A — populate-once inside the tree, or protected-immutable with a separate
  output directory?** Two roles took opposite positions. Resolved by a fact
  neither had weighed: all eight committed artifacts were added by a **single
  human-reviewed PR diff** (`7e795d4`), so no code path has ever written there.
  The synthesis in §7 satisfies both the authority (the artifacts' own `status`
  fields say they are populated at implementation) and the observability
  objection (populate-once is unenforceable after the fact). Neither role's
  position was adopted whole.
- **NR-B — `MAY_DEFER` or blocking?** The merged audit classified it `MAY_DEFER`;
  one role argued the *emission* limb binds now because it determines the bytes of
  artifacts that get checksummed and frozen. Resolved in favour of splitting the
  item: emission is decided here (§12 item 11), ingestion may defer **only by an
  explicit choice**, not by silence.
- **Referral 4 — is reporting the drop ratio a sufficient resolution?** One role
  treated it as adequate; the adversarial role showed the reported quantity is
  the wrong one by up to 15×. Reproduced by the lead and adopted (§4).
- **No unresolved material disagreement remains.**

## 14. Non-authorisation

This document authorises nothing. It permits no real data read, no real M15
derivation, no real checksum or spread computation, no validation, holdout,
training, inference, execution, or broker/paper/live activity. It adopts no epoch
and does not lift the forward-epoch WAIT. It does not start the targeted-fix Work
PR. It does not claim reproducibility under a frozen `uv` environment — the
lockfile remains known-stale and `uv sync --frozen` reproducibility is **not**
claimed. Per policy §12, the AI preparing this Gate-decision may not give final
approval for it.

---

## 15. Gate order after this decision

1. **This Gate-decision** — human + ChatGPT approval, including rulings on the
   four referred items in §11.
2. **One targeted-fix Work PR** closing audit B-1…B-7 / RF-1…RF-29 under the
   §12 normative requirements. Single PR, one objective (policy §14).
3. **A fourth independent source-audit re-check**, in a session separate from
   every fix author, accepting it.
4. **The P/V reader design PR** (byte-level proof machinery), synthetic-only, with
   its own audit — it introduces the repository's first new read capability since
   the gate-P1 inspector.
5. Only then a **separately-authorised gate-3a continuation** (playbook §5),
   Red, design-span only, metadata-only outputs.

**Recommendation.** Rule D-1 and D-2 together — they are one decision — and rule
D-4 in the same sitting, since the gap-report schema depends on which anomaly
disposition is chosen. NR-K should be ruled at the same time: it determines
whether the continuation's reader may touch a dead-window byte at all, and the
narrow default materially weakens substitution detection.
