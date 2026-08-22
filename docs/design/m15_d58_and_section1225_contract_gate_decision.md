# M15 gate-3a contract Gate-decision — D-5.8 and §12.25

- **Document class:** doc-only **Gate-decision** record (policy §14.2 — it
  formally fixes research contracts). **This document records a human + ChatGPT
  contract ruling** on two questions; the decisions bind when it is merged.
  Executes nothing. Reads no real data. Changes no source, no test, no committed
  artifact.
- **Risk tier:** **Amber** (policy §3 — it concerns a frozen research contract,
  the M15 coverage limb, the artifact schema and the scrubber). **Not
  self-mergeable.**
- **Base:** master `653a404` — the merged fourth independent source-audit
  re-check (PR #447).
- **Purpose:** freeze the two contract questions the merged audit left open, so
  that the single next targeted-fix Work PR **invents nothing and re-interprets
  nothing**. Exactly two questions are in scope: **D-5.8** and **§12.25**. Both
  are now **RULED** (§1).

## Statuses

- Required: **`M15_GATE3A_D5_8_AND_SECTION12_25_CONTRACT_RULED`**
- D-5.8: **`D5_8_RULED_NO_NUMERIC_FLOOR_TRUSTED_CALENDAR_PROVENANCE_AND_SET_EQUALITY_REQUIRED`**
- §12.25: **S1 `RULED`** · S2 **`REJECTED`** · S3 **`NOT_ADOPTED_IN_THIS_GATE`**
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
  · `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED`
  · `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
- Open pre-continuation item: **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`**
  — **still open**, and not discharged by these rulings. The *contract* for the
  calendar is now fixed; the **concrete artifact** for the target epoch is not
  approved.
- Resolved by this document: D-5.8's `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`
  classification (merged audit §11) is **discharged at the contract level** by
  §4.7's ruling. Two tokens this document carried while the packet was being
  prepared — `M15_GATE3A_D5_8_AND_SECTION12_25_PENDING_HUMAN_CHATGPT_RULING` and
  `CONTRACT_CHANGE_REQUIRES_HUMAN_CHATGPT_RULING` — are **superseded**; see §9 for
  that history, which is recorded but is **not** the current status.
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Gate-3a continuation: **NOT authorised.** Targeted-fix Work PR: **not started.**

**Forbidden-label note.** This document asserts none of `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, `DEPLOYABLE`.

---

## 1. The rulings

Both questions are **RULED** by human + ChatGPT. This section states the current
position; §9 records how it was reached.

### D-5.8 — `D5_8_RULED_NO_NUMERIC_FLOOR_TRUSTED_CALENDAR_PROVENANCE_AND_SET_EQUALITY_REQUIRED`

**No numeric minimum `expected_m15_slot_count` floor is adopted.** D-5.8 is
discharged instead by **trusted calendar provenance plus set equality**. The
eight normative requirements are in §4.7.

The ruling rests on evidence, not on caution. No committed authority pins a
numeric floor (§4.3); `1000` / `400` were already foreclosed by §10 R-2 (§4.3);
and the independent audit demonstrated that a deterministic self-generated
calendar rule produces **20,832 slots per pair** while passing floor, extent and
continuity guards simultaneously (§4.2). **Slot count is therefore not the trust
axis, and an arbitrary count floor would not solve the calendar-provenance
problem it would appear to address.**

D-5.8's `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION` classification from the merged
audit is **discharged at the contract level** by this ruling.
**`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` remains open as a
separate gate** — the contract is settled; the concrete artifact is not approved.

### §12.25 — S1 RULED

**S1 (strict) is `RULED`. S2 (permissive) is `REJECTED`. S3 is
`NOT_ADOPTED_IN_THIS_GATE`.** Sentence 1 of committed §12.25 stands as a binding
normative requirement, and the next targeted-fix Work PR conforms to it. §5.7
carries the ruling and its consequences.

Moving to S3 in future requires **its own explicit Contract Gate-decision**.

§5.7 also records, and the next fix PR must not treat as a reason to relax:
**strict §12.25 is not a complete security or data-containment defence** — a
strict-conformant nested structure still carries a large numeric dataset clean
(§5.3c). That is an argument for the FB-1 / FB-3 allowlist and scrubber controls,
never against §12.25.

### The evidence base both rulings rest on

Each item is a read-off from committed text or a lead-reproduced probe, and each
survives the rulings as the record of *why* they are what they are:

1. **The count is the wrong axis.** §9 permits the calendar to supply *"a rule
   that generates [the slot set] deterministically"*, and a rule closing over the
   derivation is deterministic. Lead-reproduced: such a rule yields 20,832 slots
   per pair, reaches both epoch ends, has a 60-minute maximum gap, and reports
   `absent = rejected = max_unavailable_gap = 0` — defeating a count floor, an
   extent criterion and a continuity criterion at once, **and disarming D-1, D-2
   and D-3 with them** (§4.2). This is the finding the D-5.8 ruling turns on.
2. No committed document pins a slot, bar, span, density or coverage floor for
   the **design** epoch. Reported as a negative result with the search that
   produced it (§4.3).
3. The frozen `raw_holdout_trade_floor: 1000` and `N_eff_holdout_floor: 400`
   **may not be reused** as a D-5.8 floor. Four independent grounds (§4.3).
4. Any bare numeric slot floor would **implicitly decide the Ruling-4
   holiday/thin-liquidity exclusion calendar**, marked `[FIXED-AT design audit]`
   and never fixed; and an extent criterion is **unsatisfiable as literally
   stated**, because `DESIGN_END` falls on a **Saturday** (§4.3).
5. The arithmetic **ceiling** is derivable and is not an invented number:
   **29,760 expected M15 slots per pair**, equivalently 446,400 source minutes
   (§4.4).
6. For §12.25, PR #445's selection between the two readings was **procedurally
   unauthorised** — a contract determination taken inside a Work PR (§5.4).
7. For §12.25, the practical justification for the permissive reading is
   **false**: the **§12.20-conformant** record shape has four immediate numeric
   fields with `gap_report` nested and scans clean under both rules, so the two
   clauses were never in conflict — the fixture manufactured one by putting two
   effective-N quantities in the per-file record (§5.3).
8. Committed governance already pointed the same way as the S1 ruling — playbook
   §2.8 and `CLAUDE.md` make the narrower reading govern *and* require human +
   ChatGPT review. The review has now happened, and it selected the narrower
   reading (§5.6).
9. **Placement and ordering** of any coverage-side check are derivable and
   testable without a contract decision, and getting them wrong silently breaks
   six existing guards (§4.9).

---

## 2. How the packet was prepared, and its limits

Four independent roles were used — contract/governance · research-statistics and
count semantics · adversarial/fail-open · testability/observable behaviour — none
given another's conclusions, none told what the others were examining. The lead
integrated on committed authority and evidence, never by majority, and
**re-executed every decisive factual claim** before adopting it. Two claims were
reproduced twice by different methods and are flagged where they appear.

**Nothing in this document was produced by an operation this task forbids.** No
source or test change · no artifact generated · no real-data read · no `.env`
read · no DB · no network, DNS, UDP or TCP · no raw-source hashing · no M15
derivation · no validation, holdout, training, inference or execution · no
broker or storage · no credential use · no calendar artifact generated · no
market hours decided · no targeted-fix implementation · no gate-3a continuation.

Probes were synthetic, ran against a private `git archive` extract, and used
self-evidently fake slot sets (a handful of consecutive 15-minute buckets).

---

## 3. Scope

Two questions, one PR. They share an objective (freeze the contract before the
next fix PR), a risk tier (Amber), and a revert unit — policy §14 keeps them
together.

**Out of scope and deliberately untouched:** FB-1…FB-10 and FR-1…FR-18, FR-20,
FR-21 go to the single next targeted-fix Work PR. **FR-19** is a separate
test-safety Work PR requirement and is not implemented, re-scoped or folded in
here. No source defect found while preparing this document was fixed; where one
bears on a decision it is cited as a dependency, not repaired.

---

## 4. D-5.8 — the coverage adequacy question

### 4.1 Issue — the exact question, reconstructed from committed text

Contract §8 clause 8, verbatim:

> 8. A single instant, or a sparse handful of points, **never** produces a proof
>    token.

Clauses §8.1–§8.7 make coverage **set equality** per pair —
`actual_certified_m15_slots == expected_m15_slots` — against the approved
calendar artifact. That closes the *truncated-derivation* case §8 was written
for. §8.8 is a separate absolute, and it binds in the one case set equality
cannot reach: **a degenerate expected set**. If the calendar declares one slot
per pair and one bar per pair is certified, the equality holds and the
conjunction over 20 pairs is satisfied.

**The quantity, named precisely** — getting this wrong is how §10 R-2's
confusions happen:

> **D-5.8 concerns `expected_m15_slot_count(pair)`** — the cardinality of the
> expected M15 slot set that the approved calendar artifact declares for one
> canonical pair over the frozen design epoch.

Containment chain against every confusable neighbour, by construction:

```
expected_m15_slots(p)              ceiling 29,760 (§4.3)
  == actual_certified_m15_slots(p)          D-5 set equality
  == complete_bucket_count(p)               when absent = rejected = 0 (§12.20 name)
  ×15 == usable_source_minute_count(p)      frozen grid (coverage.py:666 bind)
  ⊇ cost_hurdle_eligible_bar_count(p)       needs the cost table — not computable at this gate
  ⊇ raw_traded_event_count(p, role)         needs a trained model + EV gate, on a forward epoch
```

**Level:** **per pair, design epoch only.** Per pair because D-5 is per pair and
the token is a conjunction — a portfolio floor is satisfiable by one healthy pair
and nineteen degenerate ones (lead-confirmed). Design epoch only because
validation and holdout adequacy are governed by Ruling 2's span minima and the
effective-N floors — different instruments, different question.

### 4.2 The finding that reframes the question

**A count floor cannot discharge §8.8, because the count need not be a lie.**

Contract §9 permits the artifact to supply *"the expected M15 slot set, **or a
rule that generates it deterministically**"*, and `_slots_from_rule` validates a
rule by calling it twice and comparing. **A rule that closes over the derivation
output is perfectly deterministic.** Lead-reproduced, plain data, no hostile
object:

```
validate_calendar ACCEPTED a rule that closes over the derivation: ValidatedCalendar
  grid slots in epoch = 29760 | expectation = 20832 (70.0% of grid)
  first/last = 2025-04-25T00:00:00+00:00 / 2026-02-28T23:45:00+00:00
  largest gap between consecutive expected slots = 60 minutes
  assert_full_coverage -> CoverageResult over 20 pairs
  per_pair[0]: PairCoverage(pair='EUR_USD', expected_slot_count=20832, certified_slot_count=20832)
  reported absent/rejected/max_unavailable_gap: 0 / 0 / 0  <-- the losses are invisible
```

One construction defeats **a count floor, an extent criterion and a continuity
criterion simultaneously**: 20,832 slots per pair clears any plausible floor,
both epoch ends are reached, and the largest gap is an hour. Nothing is
falsified — the count, the extent and the continuity are all *real*. They are
the derivation's.

**And it is worse than a D-5.8 bypass.** Because the expectation tracks the
derivation, a bucket lost to a **D-1 crossed quote** or a **D-2 rejected minute**
leaves the *expected* set at the same instant it leaves the certified set. The
run therefore reports `absent = 0`, `rejected = 0`,
`max_unavailable_gap_minutes = 0`, and the six-quantity D-3 accounting is
arithmetically self-consistent. **The same closure disarms D-1's hard
fail-closed, D-2's zero tolerance and D-3's accounting in one move, and the
halt §1 pre-commits to as the designed outcome never fires.**

> **Consequence for the ruling: the count is the wrong axis.** The defect is that
> `expected` may be a function of `observed`, and §9 currently authorises it. Any
> ruling that sets a floor and leaves the rule form open will be reported as
> conformant and defeated on day one.

A second, independent instance of the same class: the criterion is read off an
object the caller supplies. A `frozenset` subclass that lies only about `__len__`
yields a **successfully returned** `CoverageResult` whose own record
self-contradicts, and nothing compares the two fields:

```
CoverageResult minted. per_pair[0]: PairCoverage(pair='EUR_USD',
                                    expected_slot_count=21000, certified_slot_count=1)
```

### 4.3 Existing authority — including what it forecloses

**The negative result, reported as carefully as a positive.** Sweeps across
`docs/**`, `artifacts/**`, `scripts/**`, `tests/**` for slot/bar/span/density
/coverage floors, plus targeted reads of the pre-registration, the T-1…T-7 design
audit, the adoption record and all eight committed artifacts: **no design-epoch
floor of any kind exists.** The only frozen counts touching this epoch are
`file_count: 20` (a *pair* count), `H_m15_bars: 24`, `purge_embargo_m15_bars: 25`
and `SLOT_MINUTES = 15`. Playbook **NR-G** states the negative in committed form:
*"only holdout floors (`1000` raw / `400` N_eff) are frozen"* — even the
**validation** role has none.

**Foreclosure 1 — the frozen effective-N floors may not be reused.** Four
independent grounds, any one sufficient:

- *Quantity.* The APPROVED spec defines `raw_event_count` as *"eligible
  **traded** events … that pass the cost-hurdle and fire an EV-gated trade"*. An
  M15 slot is a `complete_bucket_count` unit. Contract §10 R-2 names this exact
  substitution and states its price: it *"clears the frozen floors … by orders of
  magnitude and **disarms `INSUFFICIENT_SAMPLE`**."* `effective_n()` already
  enforces the distinction by name. Borrowing `1000` back into the coverage layer
  is that refused call with the direction reversed.
- *Epoch.* Both are **holdout** floors, on a forward epoch that does not exist.
- *Level.* Both are applied at **portfolio** level; D-5 is per pair.
- *Kind.* `400` bounds a derived real whose inputs — realised inter-event gaps
  and daily-PnL correlations — are undefined for a slot set.

**Foreclosure 2 — a bare number decides an unfixed market-hours question.**
Ruling 4 freezes the session partition and the rollover exclusion (21:55–22:15
UTC minimum, widen-only) and marks the **holiday / thin-liquidity exclusion
calendar `[FIXED-AT design audit]`, before implementation** — never fixed
(playbook NR-I confirms zero representation in the package). The gap between the
arithmetic ceiling and the true expected count *is* the closed-market fraction.
Therefore any admissible answer must be **market-hours-independent, or carried by
the approved calendar artifact.**

**Foreclosure 3 — an extent criterion, as literally stated, is unsatisfiable.**
Lead-verified:

```
DESIGN_START 2025-04-25T00:00:00+00:00 Friday
DESIGN_END   2026-02-28T23:59:59+00:00 Saturday
last 15-min grid slot in the epoch: 2026-02-28T23:45:00+00:00 Saturday
```

**`DESIGN_END` falls on a Saturday.** "The expected set must reach both ends of
the epoch" would require an honest FX session calendar to declare a Saturday
23:45 bucket, or would need a tolerance — and the tolerance is a market-hours
quantity §9 forbids. Published as-is, it forces the implementer to invent the
constant.

**Foreclosure 4 — deferral past the continuation is closed.** The merged audit
§11 at `653a404` classifies D-5.8 `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`;
reversing that needs a Gate-decision, not a default.

**Shape precedent, not content.** Ruling 2's minima (validation ≥ 3 months,
holdout ≥ 2 months) show that when this programme wanted an adequacy floor it
stated it as a **span, per role, for the forward epoch** — and deliberately not
for the design epoch, whose span is fixed exactly instead.

**Relevant but not authority.** Pre-registration §9's `daily coverage ≥ 0.60` is
a *holdout strategy* metric; "coverage" is item 16 of R-2's own pinned-term list.

### 4.4 The derivable ceiling

Pure arithmetic on frozen constants, cross-checked two ways:

```
310 UTC dates x 96 buckets/day                 = 29,760 expected M15 slots per pair
closed-span arithmetic int((end-start)/900)+1  = 29,760
at the frozen 15-minute grid                   = 446,400 source minutes per pair
```

A **ceiling**, already enforced. **Nothing committed bounds it below.**

### 4.5 Current implementation

`coverage.py:40-53` discloses the gap in its own docstring and refers it to a
separate contract Gate-decision. That was the correct call: minting a floor would
have breached §12's preamble. Lead-reproduced behaviour (synthetic, obviously
fake slot sets):

```
1-slot calendar (single instant)   CoverageResult RETURNED   3-slot     RETURNED
96-slot (one day)                  RETURNED                  3 slots 100 days apart  RETURNED
empty per-pair slot list           REFUSED CalendarMalformedError
asymmetric 5/1 slots per pair      RETURNED
evaluate_four_limbs at 1 slot/pair BI /\ TC /\ CV /\ DB all satisfied
```

**Directionality.** Over-declaring fails; under-deriving fails; one absent or
rejected minute fails. **The only free parameter that makes the conjunction
satisfiable is shrinking the expected set**, and nothing bounds it below. The
contract's own strictness creates a gradient toward a smaller calendar, and
D-5.8 is the only thing opposing it.

**Not publishable today:** `PairCoverage` carries `(pair, expected_slot_count,
certified_slot_count)` and nothing about span or gaps, so no extent or continuity
criterion is checkable from what `CoverageResult` exposes — the evidence-shape
gap FR-4 records.

### 4.6 What the ruling protects — the research-integrity argument

The property that fails is **discrimination**: with a degenerate or
observation-derived expectation the coverage token stops distinguishing a
complete derivation of the frozen epoch from an arbitrarily truncated one — the
non-discrimination §8 was written to close, returning one level up. Four
downstream harms, each traced to committed text:

1. **Epoch adoption.** A reader of a satisfied conjunction concludes the
   ten-month epoch is derived and certified; FR-7 records that `calendar_digest`
   is shape-checked only and never bound to content, so the record cannot
   contradict them.
2. **The frozen cross-pair discount ρ_x — the sharpest harm, and committed.**
   `effective_n_estimator_spec.json` (`APPROVED_SPEC`) fixes
   `correlation_estimation_data: "DESIGN span only (2025-04-25..2026-02-28);
   never validation/holdout; frozen once and recorded."` and
   `rho_x = 1 + (P − 1) · mean_abs_pairwise_corr`. A degenerate design set makes
   the per-pair daily-PnL series length-1, the correlation undefined, and every
   degenerate resolution drives ρ_x → 1. At P = 20 that removes the entire
   cross-pair discount from `N_eff = Σ N_eff_pair / ρ_x`, inflating it by up to
   20× **exactly where the 400 floor is applied at holdout**. So a missing
   coverage criterion can **disarm `INSUFFICIENT_SAMPLE`** — the harm §12.20
   names, by a different route. `effective_n()` cannot defend itself: it takes
   `cross_pair_corr` as a caller-supplied number.
3. **The cost table.** §5 freezes `cost(pair, session)` from design-span spreads,
   and every §9 acceptance number is denominated in it. `validate_cost_table`
   checks all 60 cells are **present**; it cannot check that a cell rests on more
   than one observation. Under-estimated cost moves every acceptance criterion
   permissively at once.
4. **The C-3 pre-condition.** §6's median eligible `barrier_distance / cost`
   ratio becomes unmeasurable while still reporting a number.

### 4.7 THE RULING — D-5.8

**`D5_8_RULED_NO_NUMERIC_FLOOR_TRUSTED_CALENDAR_PROVENANCE_AND_SET_EQUALITY_REQUIRED`**

Recorded as an **explicit human + ChatGPT contract ruling**, not as an
interpretation of existing text. It replaces D-5.8's open question; §8.8's
"never" is discharged by the requirements below rather than by a count.

#### 4.7.1 The eight normative requirements

1. The expected M15 slot set is obtainable **only** from the approved calendar
   artifact and its **committed provenance**.
2. The source and the runtime **may not invent** the expected slot set from
   observed data or from a self-generated rule.
3. Where calendar **authority**, **provenance** or **epoch binding** is not
   established, the behaviour is **fail-closed**.
4. `assert_full_coverage` may recognise coverage as satisfied **only after both**
   the PR #444 set-equality limbs **and** calendar-provenance validation hold.
5. An expected slot count on its own — and likewise a minimum count, a temporal
   extent criterion or a continuity criterion — **is not a substitute proof of
   calendar authenticity**.
6. **No independent numeric minimum slot-count threshold is established.**
7. **No unauthorised numeric value** — `100`, `400`, `1000` or any other — is
   introduced into source or tests for this purpose.
8. Counts **may** be retained as a **diagnostic or recorded measurement**; they
   **may not** serve as an acceptance authority substituting for trusted-calendar
   provenance.

#### 4.7.2 Why the count was rejected as the trust axis

Four evidentiary grounds, each recorded above with its reproduction: no committed
numeric floor exists (§4.3); `1000`/`400` are foreclosed by §10 R-2 and would
disarm `INSUFFICIENT_SAMPLE` (§4.3); the self-generated-rule construction clears
floor, extent and continuity guards together at 20,832 slots per pair (§4.2); and
therefore a count floor would add a threshold without touching the defect it
appears to address.

#### 4.7.3 What this ruling forecloses, and what it adopts

- **O1, O2, O3 and O5 are not adopted** — none is the trust axis; O1 and O3 mint
  numbers, and O2 is unsatisfiable as stated (§4.3).
- **O7 (provenance and ordering) is adopted**, as requirements 1–4.
- **O4's count field is not adopted as an acceptance gate.** A declared count may
  exist as a diagnostic under requirement 8; it may not decide admission.
- **O6 is not needed** — the contract question is settled, so there is nothing to
  return to a second Gate-decision.

**Consequence for FR-8 (the `expected_m15_slot_rule` callable route).**
Requirement 1 admits a generating rule only where it arrives with the approved
artifact's committed provenance; requirement 2 forbids a self-generated one; and
requirement 3 makes an unestablished provenance fail closed. An in-memory
callable assembled at runtime has no committed provenance and so does not satisfy
requirement 1. **The concrete provenance mechanism is implementation work for the
targeted-fix Work PR, bounded by requirements 1–4** — this ruling fixes the
contract, not the mechanism, and the fix PR may not widen it.

#### 4.7.4 Allowed · Forbidden · Fail-closed

- **Allowed:** measuring, recording and publishing per-pair expected and
  certified counts as diagnostics (requirement 8); refusing an empty expected set
  (already implemented); defence-in-depth checks that mint no number.
- **Forbidden:** any numeric minimum slot-count threshold (requirements 6, 7);
  inferring the expected set from observed data (D-6.1, requirement 2);
  synthesising weekend or closure bars (D-6.3); any tolerance parameter (D-2);
  reusing `1000` or `400` (§4.3); treating a count, an extent or a continuity
  property as evidence of calendar authenticity (requirement 5).
- **Fail-closed:** absent, malformed, unapproved, wrong-epoch or ambiguous
  calendar → refuse (already implemented); **authority, provenance or epoch
  binding not established → refuse** (requirement 3); a provenance check that
  cannot be evaluated → refuse, never pass. Refusal **raises**; there is no
  report-only path and no parameter (D-10).

#### 4.7.5 Observable tests the targeted-fix Work PR must supply

Each with a failing-before / passing-after pair, a unique
`pytest.raises(match=...)` string and **no regex alternation** (§13):

- A calendar whose expected slot set has no committed provenance is **refused**,
  and the refusal names provenance uniquely.
- The self-generated-rule construction of §4.2 — a deterministic rule closing
  over the derivation — is **refused**. This is the ruling's headline case and
  must be pinned directly.
- `assert_full_coverage` refuses when provenance validation fails **even though**
  set equality holds (requirement 4), and the message identifies which limb
  failed.
- A **negative control**: a well-formed calendar with established provenance is
  accepted, so the check discriminates rather than refusing everything.
- The **forged-subclass** regression that pins *placement* (§4.9), since a check
  sited only in `validate_calendar` is bypassed today.
- No test asserts a numeric slot-count minimum, and no such constant is
  introduced (requirements 6, 7).

#### 4.7.6 Implementation freedom remaining

The exception type and message wording, provided the message names the failing
condition uniquely; whether provenance validation is duplicated in
`validate_calendar` as defence in depth; and the concrete representation of
committed provenance — subject to §4.9's placement and ordering constraints, and
to D-7, which makes any committed-artifact change a human-reviewed diff.

#### 4.7.7 Disposition

- **Must resolve before the targeted-fix Work PR?** Resolved — this is the
  ruling.
- **Must resolve before the gate-3a continuation?** The contract-level
  requirement is **discharged**: the merged audit's
  `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION` classification for D-5.8 is satisfied
  by this ruling. **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` remains
  a separate open gate**, and the continuation stays unauthorised until it and the
  rest of §8's gate order are discharged.
- **Further human + ChatGPT ruling required?** Not for D-5.8. The calendar
  artifact approval is its own decision and is unaffected.

**Term pinning.** `expected_m15_slot_count` joins §10 R-2's pinned terms as a
**recorded diagnostic measurement, unit = M15 slots, per pair, declared by the
approved calendar artifact and measured from it** — explicitly *not* an
acceptance authority. It sits one confusion away from `complete_bucket_count`,
from `usable_source_minute_count` (differs by the frozen factor 15), from §9's
`daily coverage ≥ 0.60`, and from the 1000/400 holdout floors.

### 4.8 Options considered, and their disposition

Retained as the record of what was weighed. Disposition per §4.7.3.

| # | Criterion | Defeated by / disposition | Mints a number? |
| --- | --- | --- | --- |
| **O1** | Numeric floor on expected slots per pair | §4.2's rule closure (20,832 slots); the lying `__len__`; says *how many*, never *which*. **NOT ADOPTED** | **Yes**, and it implicitly decides the unfixed Ruling-4 exclusion calendar |
| **O2** | Temporal extent — expected set reaches both epoch ends | A two-point calendar (lead-verified); §4.2's closure reaches both ends free; **unsatisfiable at Saturday `DESIGN_END`**. **NOT ADOPTED** | **No** in strict form, **yes** once a tolerance is needed |
| **O3** | Continuity / maximum gap | **Vacuous on a singleton** — the loop never runs, so the single instant it targets passes; a G-spaced comb of ~0.5% of the grid clears it. **NOT ADOPTED** | **Yes, unavoidably** — G must exceed the longest legitimate closure |
| **O4** | Approval-carried declared count, checked declared == measured | Does not exclude degeneracy (1 == 1 passes); the open calendar vocabulary silently ignores a misspelt field; bypassed by the FB-1 forged subclass when sited in `validate_calendar`. **Count retained as a diagnostic only** (requirement 8), **not** as an acceptance gate | **No** |
| **O5** | Horizon/purge structural minimum (`H = 24`, purge 25) | Closes only the literal *"single instant"*; 25 slots is 6¼ hours. **NOT ADOPTED** — requirement 5 makes count-shaped criteria non-substitutive | **No** |
| **O6** | Halt-and-report, no coverage token | Sequences rather than closes; still spends the irreversible read. **NOT NEEDED** — the contract question is settled | **No** |
| **O7** | **Provenance and ordering** — the expected slot set materialised, provenance-bound and approved before the derivation exists; the run consumes that, not a callable | Attacks the actual defect: severs `expected` from `observed`. **ADOPTED**, as requirements 1–4 | **No** |

### 4.9 Implementation guidance that needs no contract decision

Derivable, testable, and independent of which option is ruled — recorded so the
fix PR does not have to guess:

- **Placement.** A criterion sited only in `validate_calendar` is bypassed today
  by the FB-1 forged subclass; sited in `assert_full_coverage` — which already
  re-reads `calendar.expected_slots(pair)` rather than trusting the type — it
  holds. **Site it in `assert_full_coverage`, or in both.**
- **Ordering.** Placed *before* the set-equality limbs, any criterion silently
  takes over the guard identity of six existing refusals
  (`…a_missing_expected_slot_raises`, `…an_unexpected_extra_slot_raises`,
  `…a_duplicate_certified_slot_raises`, `…set_equality_is_not_count_equality`,
  `…the_calendar_never_shrinks_to_what_was_observed`,
  `…a_single_instant_per_pair_never_earns_coverage`) — the §13 anti-pattern of a
  test that can no longer identify which guard fired. **Site it after.**
- **Non-vacuity.** Any continuity-shaped criterion needs an explicit test that it
  fires on ≥2 slots, or the singleton case passes silently.
- **A numberless check that exists today and is missing:** `PairCoverage`
  publishes `expected_slot_count` and `certified_slot_count` and nothing compares
  them; §4.2's second probe returns a record asserting 21,000 expected against 1
  certified. Adding that comparison mints nothing.
- **Blast radius, measured**, so the ruling knows what it is buying: a criterion
  in `assert_full_coverage` fails ~75 tests directly, and because
  `test_third_recheck_fixes.py` calls `evaluated_proof()` at **module import**
  inside a `parametrize` list, that module's 114 tests become **uncollectable**
  — ≈189 tests for O1/O2, ≈197 for O4, 0 for O3. Mostly a fixture migration, but
  not a small edit.
- **Committed tests that must be rewritten or deleted** under any criterion
  enforced in `validate_calendar`: `test_second_recheck_fixes.py::_calendar_probes`
  and `_coverage_probes` **affirmatively assert that a one-slot-per-pair calendar
  validates and a one-bar measurement certifies.** D-10's stated rationale —
  *"leaving it is how a re-disposition becomes permanent"* — applies.

## 5. §12.25 — the schema shape constraint

### 5.1 Issue — the original normative wording, in full

Contract §12 item 25, verbatim:

> 25. **Schema shape constraint (lead-verified, non-negotiable).** The
>     continuation's inventory is writable only if per-file records stay
>     **nested** with **≤5 immediate numeric fields**; six refuses, and
>     flattening `gap_report` refuses. A populated 20-record instance must be
>     asserted to pass `scan_gate3a` **before** any derivation. Note the scrubber
>     currently **refuses the committed M1 predecessor inventory's own record
>     shape**, falsifying `artifacts.py:68-69`'s calibration claim — that is audit
>     blocker B-1's allowlist redesign, not a threshold to raise.

The question: **does sentence 1 state a behavioural requirement the redesigned
scrubber must keep, or describe the then-current miscalibration that B-1's
redesign was handed to replace?** The heading carries both signals —
*"lead-verified"* reads as a verified fact, *"non-negotiable"* as a prescription.

### 5.2 How PR #445 re-interpreted it

`_scan_declared` (`artifacts.py:901-998`) contains **no shape heuristic**. The
predicates survive at `:1013-1037` and are called only from `_scan_undeclared`.
**A payload that resolves to a declared schema receives strictly less shape
scrutiny than one that declares none.** The re-interpretation is pinned twice and
argued in a docstring:

- fixture docstring (`:53-60`) — *"Eleven fields, six of them immediate
  numerics… The previous shape denylist refused this at six immediate numerics
  and refused it again when the block was flattened (§12.25)."*
- `:306-317` — asserts `immediate_numerics >= 6, "the shape §12.25 records as
  refused must be exercised"` then `scan_gate3a(inventory) == []`.
- `:320-325` — *"Nesting is no longer what decides admissibility."*

The fix note restates §12.25 as only *"Inventory must be writable; assert before
any derivation"* — sentence 1 dropped — and reports conformance as *"nested **or
flattened**"*, the negation of *"flattening `gap_report` refuses"*. **Superseded
by restatement, not by argument.**

### 5.3 What the measurements show

**(a) The strict reading does not conflict with sentence 2 — but only for the
§12.20-conformant record shape.** Lead-verified:

```
§12.20-conformant record (complete_bucket_count), 4 immediate numerics, gap_report nested
   scan_gate3a(20-record instance, artifact="design_m15_inventory.json") -> CLEAN
literal committed name 'eligible_event_count', populated
   -> ['gate3a_undeclared_numeric_field:eligible_event_count']     (deliberate, per C-8/§12.20)
PR #445 fixture shape, 6 immediate numerics
   -> CLEAN
```

So sentence 2 must be ruled as: **a populated 20-record instance in the
§12.20-conformant shape** — not "the committed schema shape populated", which is
deliberately refused, and not "the implementer's fixture".

**(b) The implementer's fixture reaches six only by putting two effective-N
quantities in the per-file record** — `cost_hurdle_eligible_bar_count` and
`raw_traded_event_count`. §12.20 pins those as **terms**; it does not require
them as per-file fields, and under D-7 adding them is a committed-schema change
by human-reviewed diff. **The conflict was manufactured by the fixture's choice
of a not-yet-committed record shape.**

**(c) But the strict reading buys very little.** A strict-conformant shape still
carries a price dataset — lead-verified:

```
STRICT-conformant shape (immediate numerics = 3 <= 5, nested), 8 price columns x 20 pairs
   -> CLEAN
```

Against FB-3's three encodings, the shape rule is orthogonal to re-typing into a
string leaf and to run-together key spellings, and is defeated for declared
numeric keys by nesting — which is the rule's own instruction.

**(d) A minimal strict implementation breaks exactly the three tests that
implement §12.25** (`3 failed, 1097 passed`), two of them implementing its own
operative last clause.

**(e) "Six refuses" is ill-defined for a single record.** The existing heuristic
requires **≥2** row-like records: `6 immediate numerics × 1 record -> []`. A
strict ruling must say whether one six-numeric record refuses.

**(f) Neither reading discharges §12.25's own diagnostic.** The M1 predecessor
inventory (7 immediate numerics) is still refused, and FR-6 records that the
`gap_report` the producer actually emits is unwritable into the committed schema.

### 5.4 What was derivable before the ruling, and grounds it

**(i) A Work PR was not entitled to select between the readings.** §12.25 is a
clause of a merged contract; §12's preamble forbids the Work PR carrying it to
*"re-interpret a contract"*; §0 repeats it; policy §14.2 reserves formally
judging a contract to a Gate-decision PR; policy §3 makes the frozen contract,
the artifact schema and the scrubber protected; policy §11.3 makes changing a
frozen contract a stop trigger. **Ultra vires regardless of which reading is
right**, and neither the merge nor the internal audit loop conferred contract
authority (policy §14.5, §12).

**(ii) The direction selected is the fail-open one**, and cannot become the
settled meaning by default.

**(iii) The practical justification is false** — §5.3(a), (b).

**(iv) The operative last clause is not discharged at HEAD under either
reading** — §5.3(f).

**The precedents apply by analogy only.** D-1's *"procedurally void"* disposition
and D-10's *"must be rewritten or deleted"* both use the definite article and
refer to specific acts at `ea40d2f`. Their *reasoning* transfers — and the
general authorities D-1 cites (policy §14.2, §14.5, §12) apply here by their own
terms — but extending the *remedy* to a new subject is legislating. That is why
the ruling below stops where it does.

### 5.5 THE RULING — §12.25

**S1 `RULED` · S2 `REJECTED` · S3 `NOT_ADOPTED_IN_THIS_GATE`.**

Recorded as an **explicit human + ChatGPT contract ruling**.

#### 5.5.1 What is ruled

**Sentence 1 of committed §12.25 stands as a binding normative requirement.**
Per-file records stay **nested** with **≤5 immediate numeric fields**; six
refuses; flattening `gap_report` refuses. The next targeted-fix Work PR conforms
to strict §12.25.

**Grounds, as ruled:**

- Under current governance a Work PR is **not permitted to re-interpret** a
  merged contract clause on its own authority.
- The selection PR #445 made was therefore **procedurally unauthorised** (§5.4).
- **Implicit migration to S2** from the existing implementation **is forbidden**;
  S2 may not be reached by inheritance, by CI-green, or by the fact that it is
  already merged.
- **S3 may become a contract-amendment candidate in future**, but it is **not
  adopted in this Gate-decision**.
- At this point **S1 is the most conservative and the only unique reading that
  entails no change of meaning.**

#### 5.5.2 Disposition of the three options

| Option | Disposition |
| --- | --- |
| **S1 — strict** | **`RULED`.** Binding. The targeted-fix Work PR conforms |
| **S2 — permissive** | **`REJECTED`.** Not adopted, and specifically not reachable by inheritance from the current implementation |
| **S3 — replace sentence 1 with a committed-schema/domain-bound property** | **`NOT_ADOPTED_IN_THIS_GATE`.** A legitimate future candidate; **changing to S3 requires its own explicit Contract Gate-decision** |

#### 5.5.3 The limitation this ruling does not cure — recorded, and not to be deleted

**Strict §12.25 is not a complete security or data-containment defence.** The
audit observation stands and must survive into the fix PR's context:

```
STRICT-conformant shape (immediate numerics = 3 <= 5, nested), 8 price columns x 20 pairs
   -> CLEAN
```

A strict-conformant **nested** structure still carries a large numeric dataset.
The shape rule is also orthogonal to FB-3's other two encodings — re-typing a
dataset into a string leaf, and run-together key spellings (§5.3c).

**This is not a reason to relax §12.25.** It is the evidence that the
**FB-1 / FB-3 allowlist and scrubber controls are separately required**, and that
they carry the containment burden the shape rule was never able to carry. The fix
PR must treat §12.25 and those controls as complementary, and must not cite this
limitation as grounds for weakening either.

#### 5.5.4 Two sub-questions a strict implementation must resolve

Both were surfaced by measurement (§5.3) and neither changes the ruling; both are
implementation questions the fix PR must settle **without** widening the clause:

- **Where the two effective-N quantities live.** `cost_hurdle_eligible_bar_count`
  and `raw_traded_event_count` are pinned by §12.20 as **terms**, not as per-file
  inventory fields. Adding them to the record is a committed-schema change by
  human-reviewed diff (D-7). Absent such a diff, they do not belong in the
  per-file record, and the §12.20-conformant shape — four immediate numerics,
  `gap_report` nested — is what must scan clean.
- **Whether one six-numeric record refuses.** The existing heuristic requires
  **≥2** row-like records, so `6 immediate numerics × 1 record → []` today
  (§5.3e). §12.25 speaks of a *record*. The fix PR implements the stricter
  reading — a single six-numeric record refuses — consistent with the ambiguity
  rule that produced S1; if it concludes it cannot, it records the blockage and
  does not choose the looser behaviour.

#### 5.5.5 Allowed · Forbidden · Fail-closed · Observable tests

- **Allowed:** the §12.20-conformant per-file record (four immediate numerics,
  `gap_report` nested), which scans clean and satisfies §12.25's second sentence
  (§5.3a).
- **Forbidden:** carrying S2 forward by inheritance; raising the numeric-field
  bound to accommodate a record shape (§12.25's own last sentence forbids exactly
  that); adopting S3 without a separate Contract Gate-decision.
- **Fail-closed:** six or more immediate numeric fields refuses; a flattened
  `gap_report` refuses; where the fix PR cannot determine the correct behaviour
  it refuses and records, rather than admitting.
- **Observable tests required:** a populated 20-record instance in the
  §12.20-conformant shape **scans clean and writes** (§12.25 sentence 2, pinned
  directly); a six-immediate-numeric record **refuses**; a flattened `gap_report`
  **refuses**; each with a unique `match=` and no alternation. The two tests that
  currently pin the permissive reading —
  `test_b1_a_populated_twenty_record_inventory_is_accepted` and
  `test_b1_a_flattened_gap_report_is_also_accepted` — must be **rewritten or
  deleted**, and their docstrings' §12.25 exegesis removed. D-10's stated
  rationale applies: *"leaving it is how a re-disposition becomes permanent."*

#### 5.5.6 A trap the fix PR must not fall into

"Declaring a schema must not buy less scrutiny than declaring none" sounds
unimpeachable and is **jointly unsatisfiable with §12.25's last clause** under the
current calibration: the very payload sentence 2 requires to be writable produces
findings when scanned schemaless. An implementer handed the bare property resolves
it the cheap way — by **weakening the undeclared backstop**. If the property is
pursued at all, it comes with its tie-breaker: *conflicts are resolved by
narrowing the schema or by replacing the shape predicate with a content
predicate, never by weakening the backstop.*

#### 5.5.7 Disposition

- **Must resolve before the targeted-fix Work PR?** Resolved — this is the
  ruling. The fix PR implements strict §12.25.
- **Must resolve before the gate-3a continuation?** Resolved at the contract
  level. The operative clause remains a **pre-derivation** requirement by its own
  terms, and FB-9 remains a blocker to be closed by the fix PR.
- **Further human + ChatGPT ruling required?** Only to move to S3, which needs
  its own explicit Contract Gate-decision.

### 5.6 How committed governance had already pointed this way

Playbook §2.8: *"if what a gate permits is ambiguous, choose the NARROWER
(no-run, no-read) interpretation **and require human + ChatGPT review**."*
`CLAUDE.md`: *"the stricter reading of a research restriction wins."* Both halves
applied: the narrower reading governed in the interim, and the required review has
now taken place and selected it. The ruling in §5.5 is that review's outcome, not
a continuation of the interim posture.

## 6. Authority and requirements for the next targeted-fix Work PR

### 6.1 The Work PR's authority set

The single next targeted-fix Work PR takes **all** of the following as authority,
and nothing beyond it:

- **PR #447 FB-1 … FB-10** — the merged audit's blockers.
- **PR #447 FR-1 … FR-18** and **FR-20 … FR-21** — its required fixes.
- **PR #444** — the normative contract, in full.
- **This document's D-5.8 ruling** (§4.7) —
  `D5_8_RULED_NO_NUMERIC_FLOOR_TRUSTED_CALENDAR_PROVENANCE_AND_SET_EQUALITY_REQUIRED`.
- **This document's §12.25 ruling** (§5.5) — **S1**.

**FR-19 is not in that set.** It remains a **separate test-safety Work PR**
requirement and must not be folded in.

### 6.2 Requirements

1. **D-5.8 — implement provenance, not a count.** Requirements 1–8 of §4.7.1.
   **Introduce no numeric minimum slot-count threshold and no unauthorised
   numeric constant** into source or tests. Counts may be recorded as
   diagnostics; they may not gate acceptance. Where authority, provenance or
   epoch binding is not established, **fail closed**.
2. **Coverage ordering.** `assert_full_coverage` recognises coverage only after
   **both** the PR #444 set-equality limbs **and** calendar-provenance validation
   hold (§4.7.1 requirement 4). Site any coverage-side check in
   `assert_full_coverage` and **after** the set-equality limbs — in
   `validate_calendar` alone it is bypassed by the FB-1 forged subclass, and
   before the limbs it hijacks the guard identity of six existing tests (§4.9).
3. **§12.25 — implement S1 (strict).** Six or more immediate numeric fields
   refuses; a flattened `gap_report` refuses. Do **not** carry the permissive
   reading forward by inheritance. Settle the two sub-questions in §5.5.4 without
   widening the clause; if either cannot be settled, record the blockage rather
   than choosing the looser behaviour.
4. **Rewrite or delete** `test_b1_a_populated_twenty_record_inventory_is_accepted`
   and `test_b1_a_flattened_gap_report_is_also_accepted`, and remove their
   docstrings' §12.25 exegesis. Leaving them is how a re-disposition becomes
   permanent (D-10's stated rationale).
5. **Do not add** `cost_hurdle_eligible_bar_count` or `raw_traded_event_count` to
   the per-file inventory record without a committed-schema change by
   human-reviewed diff (D-7). The §12.20-conformant shape — four immediate
   numerics, `gap_report` nested — is what must scan clean.
6. **Do not treat §12.25 as containment.** §5.5.3 records that a
   strict-conformant nested structure still carries a large numeric dataset; that
   is an argument for the FB-1 / FB-3 allowlist and scrubber controls, never for
   relaxing §12.25 or for deferring those controls.
7. **One numberless check may be added regardless:** `PairCoverage` publishes
   `expected_slot_count` and `certified_slot_count` and nothing compares them, so
   a record asserting 21,000 expected against 1 certified is returned
   successfully today (§4.2). Comparing them mints nothing.
8. **Supply the observable tests** listed at §4.7.5 and §5.5.5, each with a
   failing-before / passing-after pair, a unique `pytest.raises(match=...)` and no
   regex alternation.

---

## 7. Non-authorisation

These rulings settle two contract questions. They authorise no operation.

This document permits no real data read, no real M15 derivation, no checksum
execution, no spread computation, no validation, holdout, training, inference,
execution, or broker/paper/live activity. It adopts no epoch and does not lift
the forward-epoch WAIT. **It generates and approves no calendar artifact and
decides no market hours** — `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`
is untouched and remains open. It changes no source, no test and no committed
artifact; it starts no Work PR; it implements no targeted fix and no FR-19; and
it does not authorise the gate-3a continuation.

Nothing in the preparation of this document used a forbidden operation: no source
or test change · no artifact generated · no real-data read · no `.env` read · no
DB · no network, DNS, UDP or TCP · no credential use · no derivation, validation,
holdout, training or execution · no PR merged.

`PRODUCTION_READINESS_NOT_CLAIMED` · `NO_EXECUTION_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`.

---

## 8. Gate order from here

1. **This Gate-decision** — D-5.8 and §12.25 **RULED**; merged on human + ChatGPT
   approval.
2. **One targeted-fix Work PR** — the authority set at §6.1, the requirements at
   §6.2.
3. **A separate test-safety Work PR** — FR-19.
4. **A fifth independent source-audit re-check**, in a session separate from
   every fix author.
5. **The P/V reader design PR** — §12.14's reader-freedom and reverse-caller pins
   should exist before it lands.
6. **Calendar artifact approval** —
   **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`, still open.** The
   D-5.8 ruling fixes the *contract* the artifact must satisfy — approved
   provenance, epoch binding, no observation-derived expectation — but the
   **concrete artifact for the target epoch is not approved**, and no ruling here
   approves it.
7. Only then a **separately-authorised gate-3a continuation** — Red, design-span
   only, metadata-only outputs.

---

## 9. How this decision was reached — history, not current status

Recorded so the reasoning is auditable. **None of this is the current status**;
the current status is §1 and the Statuses block.

This document was first prepared as a **decision packet** rather than a ruling.
At that point it carried
`M15_GATE3A_D5_8_AND_SECTION12_25_PENDING_HUMAN_CHATGPT_RULING` and
`CONTRACT_CHANGE_REQUIRES_HUMAN_CHATGPT_RULING`, on the ground that D-5.8's
criterion and §12.25's permanent reading were decisions about research acceptance
and the meaning of a merged contract, which contract §0 and §12's preamble
reserve. Four independent roles — contract/governance, research-statistics and
count semantics, adversarial/fail-open, and testability/observable behaviour —
prepared the analysis, none given another's conclusions; the lead re-executed
every decisive claim and corrected one of its own in the process.

**Human + ChatGPT then ruled both questions**, and the rulings are recorded at
§4.7 and §5.5. Two things about the outcome are worth preserving:

- The D-5.8 ruling **did not select from the option table as offered**. It
  adopted the packet's structural finding — that the count is not the trust axis
  — and replaced the question with a provenance requirement, declining the
  numeric floor outright. Options O1–O6 are recorded at §4.8 as not adopted.
- The §12.25 ruling selected **S1**, the conservative reading that committed
  governance had already made the interim position, and **rejected** S2 while
  leaving S3 available only through a future explicit Contract Gate-decision.

Both pending tokens are **superseded** by
`M15_GATE3A_D5_8_AND_SECTION12_25_CONTRACT_RULED`.
