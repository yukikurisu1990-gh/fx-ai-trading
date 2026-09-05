# M15 Track A R1 — the authorised historical execution of 2026-09-05

**Track: `TRACK_A`.**

**The development corpus is `EXPLORATORY_SEEN_DATA`.** It was `UNSEEN` until
2026-09-05T03:26:09Z and it cannot be again. Every governance sentence in this
repository that still said "nothing has been read" is corrected in the same
change that records this.

**`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NON_DECISION_BEARING_EXPLORATORY_ONLY`**
· **`RESEARCH_SCRATCH_NON_AUTHORITATIVE`**

`NO_REAL_DATA_READ_PERFORMED` and `NO_EXECUTION_PERFORMED` **no longer hold for
Track A stage R1's authorised scope.** They were discharged by the human +
ChatGPT execution command of 2026-09-05, not by a session's reading of them, and
they continue to bind everywhere else: no other read, no other stage, no other
span.

**Adjudicated by a human + ChatGPT ruling of 2026-09-05, after the run:**

* `TRACK_A_R1_CORE_EXECUTION_ACCEPTED_WITH_POST_EXECUTION_EXCLUSIONS`
* `HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN`
* `R1_UNAUTHORISED_COST_TABLE_OUTPUT_EXCLUDED_FROM_DECISION_BEARING_RESULT`
* `TRACK_A_READY_TO_BEGIN_EXPLORATORY_STRATEGY_RESEARCH`

§6 records what was referred; **§8 records how each was ruled.**

**Risk tier: Red, already exercised.** This document is the evidence of an
irreversible operation that has happened. Recording it authorises nothing
further.

---

## 1. The authorisation this ran under

A human + ChatGPT instruction of **2026-09-05**, given in the working session and
reproduced here in the terms it named:

> **記録済み dual grants を使用した real historical data execution を明示的に許可します。**
> … この指示を `TRACK_A_R1_REAL_HISTORICAL_EXECUTION_EXPLICITLY_AUTHORIZED` として
> 扱ってください。

| | |
| --- | --- |
| Current master named by the instruction | `ca2bf2992382c021c259709aed38b90a481f5bc4` |
| Approved implementation fingerprint named | `e147542aec04f2cf781c5ecd062d8a08b1d058007634c54357f00756736b5e50` |
| Grant A | `track_a_historical_read`, `2025-04-25 … 2025-12-28`, `PAIRS_20`, `M1` |
| Grant B | `track_a_m15_research_derivation`, the M1 input Grant A covers, arm (i), R1 only |

`TRACK_A_R1_REAL_HISTORICAL_EXECUTION_EXPLICITLY_AUTHORIZED` is that
instruction's token. It appears in no committed source before this document, and
this section is where it is written down — because a run declaring its own
authorisation in its own output is the seam this programme keeps closing.

## 2. What was run

One call to `scripts/m15_track_a/r1_orchestrator.run_r1`, the formal entry point,
**unpatched**. No stage was called by hand.

```
preflight (0 market-data bytes)
  -> VerifiedRunContext          one full fingerprint measurement
  -> write-ahead seen declaration
  -> derive_streaming            160 windows: gated read + authorised derivation
  -> assert_implementation_unchanged   one closing full measurement
  -> breadth K -> r1_survey.survey -> STOP
```

| | |
| --- | --- |
| Execution head (working tree) | `ca2bf2992382c021c259709aed38b90a481f5bc4` |
| Approved head (both grants, and `RunIdentity.code_sha`) | `0bb987e775658db3532affdc3992cad94382faa3` |
| Implementation fingerprint, measured before and after | `e147542aec04f2cf781c5ecd062d8a08b1d058007634c54357f00756736b5e50` (surface 32) |
| `run_id` | `track-a-r1-authorized-historical-execution-2026-09-05` |
| Started | `2026-09-05T03:26:07Z` |
| Wall clock | 309 s |
| Terminal status | `TRACK_A_R1_SURVEY_COMPLETE_STOP_NO_NEXT_STAGE_IS_REACHED_FROM_HERE`, `next_stage = null` |

PR #462 was authorization-only, so the execution head differs from the approved
head while the fingerprint — the value that is actually measured — is identical.
`git diff --name-only 0bb987e ca2bf29` touches no file on the surface.

## 3. What was read, and what was produced

| | |
| --- | --- |
| Span | `2025-04-25 … 2025-12-28`, 248 inclusive UTC dates |
| Pairs | the registered `PAIRS_20`, all twenty |
| Source timeframe | `M1` |
| Source files | 20, `data/candles_{pair}_M1_365d_BA.jsonl` |
| M1 rows ingested | **4,979,585** |
| M15 bars emitted | **335,200** (complete 319,358 · incomplete 15,842) |
| Earliest bar | `2025-04-25T00:00:00+00:00` |
| Latest bar | `2025-12-28T23:45:00+00:00` |
| Rejected source minutes | 0 |
| Peak retained raw M1 rows | **32,988** — one (pair, 31-day window), against 4,979,585 ingested |
| Live retained after the run | 0 |
| Seen declarations | 1, write-ahead |
| Grant-ledger rows | 320 (160 read + 160 derivation) |
| Breadth `K` | 0, `result_observed = false` |

**`source_bytes_on_disk` in the run summary is 1,481,715,517 and that is not the
number of bytes read.** It is the total size of twenty `365d_BA` archives, an
epoch that physically extends past the authorised window. The route stops
scanning at the window's end, so the bytes actually touched are far fewer. The
figure is kept because it identifies the files; it is labelled here because a
reader would otherwise take it for a read volume.

**`peak_rss_bytes` in the run summary is `0`, which is a failed measurement
reported as a number.** The driver's Windows RSS probe returned nothing. The
bounded-memory property is established by the retention instrument and by an
independent re-derivation (§5), not by that field. It should have been `null`.

## 4. R1's required outputs

All eight, in `R1Survey.as_record()`: schema, span, pair coverage, missingness,
descriptive statistics, the barrier/cost ratio distribution (descriptive only),
the eligible-bar rate per pair and session, and the per-pair × session spread
distribution.

Selected results, descriptive only and decision-bearing on nothing:

* **Median spread** ranges from 1.3 pip (`AUD_USD`, all sessions) to 5.5 pip
  (`GBP_AUD`). Europe is the tightest session for nearly every pair.
* **Eligible-bar rate** medians: asia 0.950, europe 0.997, us 0.978. The floor is
  `AUD_NZD` (0.359–0.603 across sessions) and `EUR_GBP` in asia (0.311).
* **Barrier/cost ratio**, post-floor TP: median 3.323 across pairs, from 3.000
  (`AUD_NZD`) to 6.556 (`USD_JPY`). Pooled n = 283,073.
* **T-3 is not evaluated.** `numerator_ruling = UNRULED_ALL_THREE_READINGS_REPORTED`,
  `status = REPORTED_AS_A_DESCRIPTIVE_STATISTIC_NO_T3_VERDICT_IS_REACHED_HERE`,
  and the stop trigger is preserved:
  `A_TRACK_A_MEASUREMENT_FIRES_T_3_S_BLOCK_UNCHANGED`.

Carried statuses, unchanged from the committed constants:
`COVERAGE_AUTHORITY_ABSENT_R1_REPORTS_A_DECLARED_LABEL_DIAGNOSTIC` ·
`RULING_4_HOLIDAY_THIN_LIQUIDITY_LIST_IS_FIXED_AT_DESIGN_AUDIT_AND_NONE_EXISTS` ·
`ATR_PRICE_SERIES_IS_AN_UNREGISTERED_RESEARCH_CHOICE_S_20A`.

## 5. Review — two independent roles

Neither was given the other's conclusions.

**Result and contract conformance.** The role **re-implemented the M1→M15
derivation from the committed rules alone** and ran it over five pairs
(`AUD_CAD`, `AUD_NZD`, `EUR_USD`, `GBP_CHF`, `USD_JPY`): bars, first/last
timestamp, complete/incomplete counts, rows ingested, missing minutes, max gap,
spread median/p90/p95 per session, cost table, eligibility and barrier ratios —
**0 mismatches, to the float**. Every internal identity reconciles across all
twenty pairs. R1 stayed inside R1: no threshold, no candidate, no `ev_min`, no
`c` / `ω` / `N_eff`, no model, no feature; every existing referral untouched.

**Data-boundary, ledger, K, RunIdentity and fingerprint conformance.** The role
**recounted the corpus independently** and reproduced 4,979,585 rows, 335,200
bars and the 32,988 peak exactly, per pair and per window. All 320 grant-ledger
rows verified individually. One `RunIdentity` across all 322 ledger rows. The run
wrote four files, all under the Track A scratch root; no protected path, no
tracked file, no network, no database, no broker. The `.pyc` escape hatch that
`containment.AUDIT_BOUNDS` discloses was checked and not used: all 51 cached
files are timestamp-invalidated and valid against the current sources.

### Data quality — no defect found

Every coverage finding is a property of the market or of the archive, checked
against the source rather than assumed:

* **`AUD_CAD` 15.6% incomplete buckets** against 1.5–7% elsewhere: it is the
  thinnest pair in the universe (median M1 volume 16, next-thinnest 31), the
  missing minutes are singletons spread across all 24 hours, and the
  `n_source_bars` histogram decays smoothly. Not a truncated read.
* **`AUD_NZD`'s low eligible rate in all three sessions**: the hurdle is
  `1.5×ATR ≥ 2.0×cost`, i.e. `ATR ≥ (4/3)×cost`. Its median ATR is 4.480 pip
  against 4.489 required — the median sits fractionally *below* the threshold, so
  a 35–60% rate is arithmetic, not a defect.
* **`max_gap_minutes = 2944`, identical for all twenty pairs**: 2025-11-02, the
  end of US daylight saving. The Friday close is 21:00Z under EDT and the Sunday
  open 22:00Z under EST, so that weekend is 49 hours once a year. Every other
  weekend is 2884–2885.
* **`missing_whole_buckets` clustered at 7012–7030**: weekend closures — 192
  buckets a week over ~35.4 weeks ≈ 6,800 — plus per-pair isolated gaps.

## 6. Findings that needed a human + ChatGPT ruling

**None of these is a defect in the run.** Each is a property of committed code or
of the record, found by reading the source after the fact.

**All five were ruled on 2026-09-05 — see §8.** This section is left as it was
written, before the ruling, so that what was put to the human is legible
alongside what the human decided. Nothing here is edited to match the outcome.

### 6.1 The read decodes one row past the window, and for the final window that row is inside the `EXPLORATORY_OOS_SLICE`

`REFERRED`: `READ_ROUTE_DECODES_ONE_ROW_PAST_THE_WINDOW_DISCLOSURE_IS_WRONG_REFERRED`

`read_route.read_historical` calls `json.loads(line)` **before** testing
`timestamp > hi`, so the first row after the window is fully parsed — prices
included — and then discarded by the `break`. For the last of the eight windows,
`hi` is `2025-12-28T23:59:59` and the next row in each archive is on or after
`2025-12-29`, i.e. inside the quarantined slice. Twenty rows, one per pair.

Three committed statements say this cannot happen:

* `SCAN_DISCLOSURE = "SCAN_DECODES_TIMESTAMPS_OF_EARLIER_ROWS_IN_THE_SAME_FILE"`
  — **earlier** only;
* module docstring, "the consumed dead window and the forward epoch … are never
  reached";
* line 133, "prices are not materialised, and **nothing after the window is
  reached at all**".

**What is established:** no slice value reached any output. The derived extremes,
the row counts and the per-window counts were reproduced independently and are
identical to what a source ending at `2025-12-28` would have produced. The OOS
`N = 1` budget was not touched and the slice remains unread as a *dataset*.

**What is not for a session to decide:** whether twenty parsed-and-discarded rows
constitute an OOS read under the contract, and whether the fix is to correct the
disclosure or to reorder the loop so the timestamp is extracted before the row
is decoded. Reordering edits `read_route.py`, which is on the fingerprint
surface, so it would void both grants — which is acceptable now that they have
been exercised, but it is a ruling, not a cleanup.

### 6.2 The 320-row grant ledger contains two distinct lines

`REFERRED`: `GRANT_LEDGER_PER_WINDOW_PROVENANCE_JUSTIFICATION_IS_NOT_TRUE_REFERRED`

`streaming.py` justifies the 320 rows as per-window provenance — "one row cannot
say which windows were entered" — and `CLAUDE.md` presents that to a human as an
operational consequence to weigh before authorising a run. Measured: the file has
**320 lines and 2 distinct lines**. No row carries a window, a pair, an index or
a timestamp, so 320 rows say exactly what 2 would. The design choice may still be
right; the reason given for it is false, and it was given to a human before an
irreversible decision.

### 6.3 `cost_table` is produced unconditionally, and the approval did not name it

`REFERRED`: `R1_SURVEY_PRODUCES_COST_TABLES_WITHOUT_THE_APPROVAL_NAMING_THEM_REFERRED`

The MRG's Track A transfer table says a run may produce design-span cost tables
"**if and only if explicitly authorised in the approval**". Neither grant names
them. `r1_survey.survey()` produces `cost_table` unconditionally — there is no
switch — so **this run had no choice**, and the question is about the committed
survey rather than about the execution.

Two deferred referrals become engaged by a produced cost table and are not yet
recorded as engaged: **NR-F** (the frozen all-in-cost formula is dimensionally
incoherent — `SPREAD_UNIT = "price"` while the pads `0.3` / `0.5` are pips; R1's
implementation resolves it by converting to pips first) and **NR-I** (the
rollover exclusion window has no representation in the cost schema).

The produced table is not a frozen cost table: it carries
`NON_DECISION_BEARING_EXPLORATORY_ONLY` and derives from Track A research scratch
rather than the checksummed §4 dataset that prereg §5 requires for an admissible
cost model. It shares a name with the frozen object and carries no token saying
it is not one.

### 6.4 `required_outputs` is a static self-attestation

`REFERRED`: `R1_SURVEY_REQUIRED_OUTPUTS_IS_A_HARD_CODED_SELF_ATTESTATION_REFERRED`

The eight-item tuple is a dataclass default. It reports the same eight strings
whatever the run produced, and no test ties any item to a produced field —
exactly the shape `aggregation.py`'s own R-1 deleted, on the ground that "none
could ever take the other value, so none was evidence". Whether
`descriptive_statistics` has any substance beyond the three items listed beside
it is the open half: the record carries no price-series statistics (OHLC,
returns, range, ATR distribution).

### 6.5 `RunIdentity.code_sha` names the approved head, not the executing head

`identity.py` defines `code_sha` as "the run's own commit". All 322 ledger rows
carry `0bb987e7…` while the run executed at `ca2bf299…`, because
`r1_orchestrator` refuses unless `identity.code_sha == grant.approved_head_sha`.
The fingerprint makes this harmless, and the executing head is recorded here and
in the run summary — but a `BINDING_GOVERNANCE_RECORD` field carries a value that
does not mean what its own definition says. **Non-blocking**, recorded so it is
not rediscovered.

## 7. Evidence, and where it lives

| File | sha256 | bytes |
| --- | --- | --- |
| `artifacts/track_a_scratch/ledger/exploratory_seen_ledger.jsonl` | `e3b350de6b02dcbe7b418d65910a468d8d1a0ed79a070a2bff5456cd69425bba` | 795 |
| `artifacts/track_a_scratch/ledger/track_a_authorization_ledger.jsonl` | `cddc466849570a0a1ea30501f65d9fb7ae91531763793a53f0d8cf72932e9bc2` | 329,920 |
| `artifacts/track_a_scratch/ledger/exploration_breadth.jsonl` | `8f0e4f3b37cbb3787ecb33d8610a5fed2061f81bca0059b74a575acfb87e89d4` | 856 |
| `docs/governance/evidence/m15_track_a_r1_driver_2026_09_05.py.txt` | `3a799236bdb38e3558e2131152de9881dd376acae9277c1a22f375fd9357a11d` | 9,276 |
| `artifacts/track_a_scratch/r1_execution_2026_09_05/r1_execution_summary.json` *(not committed)* | `bb52c045b01ad6b214ea736afea27f722d8bb2e86e5bd79288dd769d92e0bb5c` | 127,284 |

**The summary's `cost_table` and `barrier_cost_ratio` values are excluded from
R1's decision-bearing result by §8.2.** They remain in the file unaltered,
because the file is the record of what ran and editing it would make it a record
of something else. They are not results and they are not retroactively approved.

**`required_outputs` is checked rather than trusted.** The field is a static
dataclass default; a test added with this record
(`test_required_outputs_names_things_the_survey_actually_produced`) ties seven of
the eight names to a produced, non-empty field and records the eighth,
`descriptive_statistics`, as having no distinct field — which is the open half of
the referral, left open rather than mapped onto a neighbour. Tests are outside
the fingerprint surface, so checking the claim costs nothing; fixing the field
itself is the Work PR.

**The three ledgers are committed here, and that closes a defect both review
roles found independently.** MRG §8.13.5 items 5 and 6 require the
`EXPLORATORY_SEEN_DATA` ledger and the breadth record to be "write-ahead,
append-only, **committed** — it is what makes the one-way transition auditable".
`.gitignore` un-ignores them, which is not the same as committing them, and until
this change the only record of an irreversible transition was three untracked,
deletable files.

**The driver is committed verbatim, with a `.py.txt` suffix.** `r1_orchestrator`
has no CLI by design, so a driver had to be written, and it was written outside
the repository — which meant the run was not reproducible and "unpatched" was a
claim rather than a check. The suffix keeps the archived bytes out of the
formatter: a reformatted driver is not the driver that ran. Its sha256 above is
the bytes that executed.

**The run summary is not committed** and that is deliberate:
`.gitignore` line 195 ignores `artifacts/track_a_scratch/*` because Track A
scratch output is `NON_DECISION_BEARING_EXPLORATORY_ONLY` and is not evidence.
Its hash is recorded here so the local file can be checked against this record.

## 8. The post-execution adjudication of 2026-09-05

A human + ChatGPT ruling, given after the run and after both review roles
reported. It is recorded here in the terms it was given; nothing below is a
session's inference.

### 9.1 The OOS boundary decode **is a read**

`HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN`

> 実行時、各20ペアについて最終development windowの直後の1行が file から取得され、
> `json.loads` で decode され、timestamp > hi と判定後に破棄された。…
> **これは read に該当する。**

So, from here, **these three claims are prohibited** anywhere in this repository
and in any report:

* "OOS 完全未読" — the historical OOS slice was not completely unread;
* "pristine historical OOS";
* "untouched historical OOS".

The historical `EXPLORATORY_OOS_SLICE` (`2025-12-29 … 2026-02-28`) is **touched**.
Twenty rows, one per pair, were read from disk and decoded.

What the ruling equally establishes, and what may therefore still be said:

* no OOS row reached any R1 output;
* no OOS value was used in a metric, a selection or any R1 result;
* the development R1 core result is **not** invalidated by it;
* this is **not** to be treated as having performed the formal OOS `N = 1`
  execution. That budget is unspent.

**The Two-Track policy is unchanged**: Formal Confirmation uses a **future
untouched epoch**. This historical OOS slice may not be used as formal evidence.

The decode is not redefined as "not a read" to make the record consistent. The
claim is withdrawn instead. That direction is the ruling's, and it is the only
one that leaves the record true.

### 9.2 The unauthorised `cost_table` output is excluded

`R1_UNAUTHORISED_COST_TABLE_OUTPUT_EXCLUDED_FROM_DECISION_BEARING_RESULT`

The R1 approval did not explicitly authorise cost-table output, and the MRG
permits design-span cost tables "if and only if explicitly authorised in the
approval". The values this run produced — `cost_table` and the
`barrier_cost_ratio` figures derived from it — are **excluded from R1's formal
decision-bearing output**. They remain in the artefact, unaltered, as a record of
what ran; they are not results.

They are **not retroactively approved**. A later approval naming cost tables
would authorise a later run, not this output.

This does not invalidate: R1 as a whole, the spread diagnostic, the M15
derivation, or the data-quality survey.

### 9.3 R1 core execution is accepted, with those exclusions

`TRACK_A_R1_CORE_EXECUTION_ACCEPTED_WITH_POST_EXECUTION_EXCLUSIONS`

**Accepted:** the authorised development-corpus read; the M1→M15 derivation; the
declared-label diagnostic; coverage and missingness; the spread and session
diagnostics; the data-quality findings; `K`, `RunIdentity` and the grant ledger;
the fingerprint and containment results.

**Excluded:** the unauthorised `cost_table` decision-bearing output (§8.2), and
any claim that the historical OOS is pristine (§8.1).

**R1 is not re-run.** The development corpus is already `EXPLORATORY_SEEN_DATA`,
so a second run would read data that is already seen and could not restore
anything. Re-running to "do the one-row decode properly" would spend more of the
same seen corpus for no statistical gain.

### 9.4 `TRACK_A_R1_EXECUTED_ON_AUTHORIZED_HISTORICAL_DEVELOPMENT_CORPUS` stays unrecorded

Its wording collides with §8.1: twenty rows outside the authorised corpus were
read. Rather than weaken the token's meaning after the fact, the ruling uses the
accurate one — `TRACK_A_R1_CORE_EXECUTION_ACCEPTED_WITH_POST_EXECUTION_EXCLUSIONS`
— and leaves the original token meaning exactly what it always meant, unclaimed.

### 9.5 The next stage

`TRACK_A_READY_TO_BEGIN_EXPLORATORY_STRATEGY_RESEARCH`

Feature, model, label, calibration and threshold exploration may begin over the
historical development data, which is free to use for exploration now that it is
seen.

Every output of that work is `NON_DECISION_BEARING_EXPLORATORY_ONLY` and
`RESEARCH_SCRATCH_NON_AUTHORITATIVE`. None of it is formal evidence. It is **not**
authority to run R2, to read the OOS slice, or to begin Formal Confirmation —
each of those remains its own Red gate needing its own explicit act.

And it is not an instruction to build another production-grade gate first.

## 9. Referrals carried forward as ordinary Work PRs

**None of these blocks the start of exploratory strategy research**, by the same
ruling.

| Referral | What it is |
| --- | --- |
| `READ_ROUTE_DECODES_ONE_ROW_PAST_THE_WINDOW_DISCLOSURE_IS_WRONG_REFERRED` | Reorder the loop so the timestamp is read before the row is decoded, **and** correct the three false statements in `read_route.py` (§6.1) |
| `R1_SURVEY_PRODUCES_COST_TABLES_WITHOUT_THE_APPROVAL_NAMING_THEM_REFERRED` | Gate `cost_table` production on an approval that names it; record NR-F and NR-I as engaged |
| `GRANT_LEDGER_PER_WINDOW_PROVENANCE_JUSTIFICATION_IS_NOT_TRUE_REFERRED` | Correct the same wording in `streaming.py` that `CLAUDE.md` is corrected for here |
| `R1_SURVEY_REQUIRED_OUTPUTS_IS_A_HARD_CODED_SELF_ATTESTATION_REFERRED` | Tie `required_outputs` to the artefacts actually produced |

**Why none of the four is fixed in this PR, stated plainly.** Every one of them
lives in `read_route.py`, `r1_survey.py` or `streaming.py` — all on the
fingerprint surface. Editing any of them, **including a docstring**, moves
`e147542a…` and invalidates both grants, which would require this evidence PR to
also un-tick §5a and record the grants as refused — in the same change that
records R1 having run under them. That is a confusing state to create for a
comment fix, and the execution command asked for a governance/evidence PR without
a large reader source change mixed in.

So the false statements in `read_route.py` are **still there and still false** as
this merges. They are quoted verbatim in §6.1 so no reader has to find them, and
the first of the four Work PRs corrects them. Recording that they remain is the
point: this document does not claim they are fixed.

## 10. What this is not

`TRACK_A_R1_EXECUTED_ON_AUTHORIZED_HISTORICAL_DEVELOPMENT_CORPUS` **is not
recorded**, and §8.4 says why: its wording is no longer true.
`TRACK_A_R1_CORE_EXECUTION_ACCEPTED_WITH_POST_EXECUTION_EXCLUSIONS` is what
holds.

This run does **not** mean: an M15 edge is confirmed; a strategy candidate has
been selected; OOS has been passed, or read as a dataset; Gate-3a has been
passed; Formal Confirmation has been passed; anything is production ready.

It also does **not** mean the historical OOS slice is untouched — §8.1 — nor
that the cost figures it produced are results — §8.2.

R1 (first read), R3 (training) and R4 (evaluation) remain **separate Red gates**.
Nothing here authorises R2, an OOS read, a strategy search, a candidate
selection, or formal `c` / `ω` / `N_eff` evidence. The next step is a human +
ChatGPT decision, not a session's.
