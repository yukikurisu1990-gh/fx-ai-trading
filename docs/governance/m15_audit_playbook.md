# M15 audit playbook — durable governance record and gate discipline

- **Document class:** doc-only governance playbook. Binding operating
  instructions for every future AI session — of any model — that proposes,
  implements, audits, or merges any M15 / post-M1 research work. Executes
  nothing; authorises nothing.
- **Status:** `M15_AUDIT_PLAYBOOK_AND_CLAUDE_RULES_RECORDED`
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
  · `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_ACCEPTABLE_FOR_GATE3A_DATASET_EPOCH_ADOPTION`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Companion files: `docs/governance/autonomous_development_policy.md`
  (**process authority**: risk tiers, autonomy, stop rules, head-SHA rule),
  `docs/prompts/m15_future_audit_templates.md` (optional prompt templates),
  `docs/prompts/m15_claude_operating_prefix.md` (five-field task contract),
  root `CLAUDE.md` (mandatory pointer).

**Division of authority.** This playbook governs research *substance* — what
may be read, derived, trained, evaluated and claimed at each gate. The
autonomous development policy governs *process* — how much a session decides
alone, when it stops, and how head changes are handled. Where they overlap,
the research restrictions here win. Every gate below is **Amber or Red** in
the policy's tiers: the AI may investigate, implement, test and prepare a PR
autonomously, but merging a gate PR and advancing to the next gate require a
human + ChatGPT decision, and Red operations require approval before they run.

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, or `DEPLOYABLE`; those tokens appear only
in prohibition lists (§10) and in template status vocabularies.

---

## 1. Current gate state

Last reconciled against master at `d694377` (2026-08-31); master CI green.
**P-5 is discharged at this reconciliation**: the table below now carries the
Two-Track gates, the execution gate, the R1 read body, the recorded ReadGrant
and the R1 enablement PR. It previously stopped at PR #444, which is why the
execution gate document recorded P-5 as "§1 reconciled, **gate table not
rebuilt**".

| Gate | State |
| --- | --- |
| Gate 1 — post-M1 research program roadmap (PR #427) | ✅ complete |
| Gate 2 — Fable 5 roadmap audit (PR #428, rulings R-2a/R-2b, conditions C-1…C-8) | ✅ complete |
| Gate 3 — Family-A M15-first pre-registration (PR #429, rulings 1–13 frozen) | ✅ complete, contract FROZEN |
| Gate 4 — Fable 5 design audit (PR #430, tightenings T-1…T-7) | ✅ accepted for gate 3a |
| Gate 3a — dataset/epoch adoption record (PR #431, metadata/status only) | ✅ complete as a record; **forward epoch NOT adopted** |
| Forward epoch (validation + holdout) | **`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`** — needs ≥ 3 mo validation + ≥ 2 mo holdout of data at/after 2026-04-25; earliest feasible adoption ≈ **2026-10** per the PR #431 record |
| Gate 5 — synthetic-only M15 machinery (PR #432) | ✅ merged (`M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`) |
| Source-contamination audit of the PR #432 machinery | **executed and merged (PR #433)** with verdict `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES` — five probe-confirmed blockers **F-1…F-5** (F-1/F-2 INV-1-class) |
| Targeted fix PR for F-1…F-5 (+O-1/O-2) (PR #434) | ✅ **merged** as `5701ce8` (2026-07-27), on a recorded human + ChatGPT approval of the rebased head `2afa01f`. Status `M15_AGGREGATION_DATASET_MACHINERY_TARGETED_FIXES_PROPOSED`. The merge recorded the fixes; it did **not** grant audit acceptance |
| CI reproducibility repair (PR #436) | ✅ **merged** as `0e19135` (2026-08-02) — infra-only Ruff pin `0.15.11`; master CI green. Status `RUFF_VERSION_PINNED_FOR_REPRODUCIBLE_CI_NO_RUN` |
| **Independent source-audit re-check of the F-1…F-5 fixes** | **executed — verdict `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`** (`docs/design/m15_aggregation_dataset_machinery_source_audit_recheck.md`). F-2…F-5 fixed; **F-1 defeated by `pandas.Timestamp` nanoseconds**; five blockers B-1…B-5 + ten required fixes. Containment re-derived CLEAN |
| Second targeted-fix Work PR (B-1…B-5, R-1…R-10) (PR #440) | ✅ **merged** as `9c36cb0` (2026-08-03) — code + tests + docs + internal audit (`docs/design/m15_recheck_targeted_fixes_note.md`, status `M15_AGGREGATION_DATASET_MACHINERY_RECHECK_FIXES_PROPOSED`). Merged with the `uv.lock` inconsistency formally unresolved: **`uv sync --frozen` reproducibility is NOT claimed**, and no Red operation that presumes a frozen uv environment is approved until it is |
| Second re-check attempt (PR #441) | **CLOSED unmerged — non-independent diagnostic review, no gate authority.** Authored in the same session as PR #440, so it does not satisfy policy §12. Its BL-1…BL-5 / RF-1…RF-11 findings are retained as **non-authoritative diagnostic input** only |
| Third targeted-fix Work PR (BL-1…BL-5, RF-1…RF-11) (PR #442) | ✅ **merged** as `c3a0468` (2026-08-07) — code + tests + docs (`docs/design/m15_second_recheck_targeted_fixes_note.md`), status `M15_AGGREGATION_DATASET_MACHINERY_SECOND_RECHECK_FIXES_PROPOSED`. Added `timeutil.py` + `path_authority.py`, and `pandas>=2.0,<4.0` to the `dev` extra (an Amber dependency change; `uv.lock` not regenerated, so `uv sync --frozen` reproducibility remains **unclaimed**). The merge recorded the fixes; it granted **no** audit acceptance |
| **Third independent source-audit re-check** (PR #443) | **executed — verdict `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`** (`docs/design/m15_third_independent_source_audit_recheck.md`). Run in a session separate from every fix author, six independent roles. **Seven blockers B-1…B-7 + twenty-nine required fixes RF-1…RF-29.** Containment against real data / derivation / training / execution / broker / credentials re-derived **CLEAN** and proved, not inherited. Mutation resistance measured: 182 mutations, 154 killed, **19 genuine coverage holes** |
| Fourth targeted-fix Work PR (B-1…B-7, RF-1…RF-29) (PR #445) | ✅ **merged** as `adcfd52` (2026-08-19) — code + tests + docs (`docs/design/m15_targeted_fix_b1_b7_rf1_rf29_note.md`); tests 356 → 1100; new reader-free modules `proof.py`, `coverage.py`, `calendar_authority.py`, `numeric_authority.py`. The merge recorded the fixes; it granted **no** audit acceptance. The PR also discloses a process-boundary incident (an unscoped `pytest` run reached a live local database), resolved and revalidated |
| Test-safety Work PR (PR #446) | ✅ **merged** as `0e3b001` (2026-08-20) — `tests/optin.py` + `tests/conftest.py` guards; the presence of a resource no longer authorises using it. Two residual routes recorded by the fourth re-check (§FR-19 there): the `.env` matcher is route-dependent, and the socket guard misses UDP/DNS |
| **Fourth independent source-audit re-check** | **executed — verdict `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`** (`docs/design/m15_fourth_independent_source_audit_recheck.md`). Run in a session separate from every fix author, ten independent roles. **Nine blockers FB-1…FB-9 + nineteen required fixes FR-1…FR-19.** B-2, B-3, B-4 and B-7 re-derive **CLOSED** by re-running the original exploits; B-1 and B-5 CLOSED_BUT_NARROW; 27 of 29 RF items CLOSED. The blocking shape is *absent* guards, not broken ones: no `__init_subclass__` seals the token-bearing records, the writer validates one read and publishes another, reader-freedom is pinned by no test, and forbidden content reaches disk through three plain-JSON encodings. **D-5.8 classified `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** |
| Contract Gate-decision on referrals 2 / 3 / 4 (+ NR-A, NR-C, NR-D, NR-J, NR-K) and the byte-level T-7 proof (PR #444) | ✅ **RULED by human + ChatGPT and merged** as `ea40d2f` (2026-08-08) — `docs/design/m15_contract_design_gate_decision.md`, status `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED`. Crossed quotes **hard fail-closed** (merged R-2 is authority; no drop-and-count); rejection tolerance **zero and structural**, not an empirical threshold; the missing-minute schema replaced by **six separately measured quantities**; **hashing is a byte read** (no raw-source re-hash without explicit read authorisation; proof subject = derived M15 bytes); T-7 coverage is **set equality** per pair against an approved calendar, not min/max containment; NR-A / NR-C / NR-D / NR-J decided; byte-level proof = **BI ∧ TC ∧ CV ∧ DB**, declaration-only tokens may never be promoted. Adds the negative-control rule and a twenty-term pinned-definition requirement. **Only open item:** `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` |
| Gate-3a continuation (real design-span derivation) | **NOT authorised.** Referrals 2/3/4 are RULED (PR #444), but no independent re-check has accepted the machinery, **D-5.8** is unresolved, and `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` is open. Note this is **Track B's** continuation and is untouched by the Track A rows below |
| Targeted-fix Work PR FB-1…FB-10 / FR-1…FR-21 (PR #449) | ✅ **merged** as `70bf38b` (2026-08-23) |
| Continuation output-surface Contract Gate-decision (PR #450) | ✅ **RULED and merged** — five questions closed; the routing hole in `ml_step4.evidence.write_report` recorded; the artifact roster is **nine**, not eight |
| **Two-Track model** — §8.11 / §8.12 / §8.13 of the minimum research gate (PR #451) | ✅ **RULED and merged** as `4f45515` (2026-08-30). Track A = exploratory, Track B = formal confirmation. `APPROVAL_IDENTIFIER_PENDING_UNTIL_MERGE` is **discharged** by that merge |
| **Minimum Research Execution Gate** — Track A R1 enablement apparatus (PR #452) | ✅ **merged** as `37edbb0` (2026-08-30). Building the gate is not passing it; the merge authorised no read |
| Track A R1 read body + `EXPLORATORY_OOS_SLICE` ruling + grant binding (PR #453) | ✅ **merged** as `6b75aab` (2026-08-30). Slice = final 20% of the committed DESIGN UTC dates = `2025-12-29 … 2026-02-28`; development corpus = `2025-04-25 … 2025-12-28` (248 dates). A grant binds to a **measured implementation fingerprint** |
| Recorded Track A R1 development `ReadGrant` (PR #454) | ✅ **merged** as `d694377` (2026-08-31), authorization-only. `track_a_historical_read` / `2025-04-25 … 2025-12-28` / `PAIRS_20` / `M1`, bound to fingerprint `497e187b…`. ⚠ **Invalidated by PR #455**, by design |
| **Track A R1 execution command of 2026-08-31** | **REFUSED before any read.** R1 could not complete: `derive_m15` had no body, no derivation grant existed, neither calendar artifact existed, T-3's numerator was undefined, no survey runner existed, and the P-1…P-15 predicate was not recorded true on a named master SHA. No byte of market data was read; the corpus remains **UNSEEN** |
| **R1 Enablement Remediation Work PR (PR #455)** | in review — closes all six, plus the `aggregate_m15` bypass and the gitignored ledger. `TRACK_A_R1_END_TO_END_SYNTHETIC_DRY_RUN_PASSED`. **Invalidates the PR #454 grant by design**; a new read grant and a new derivation grant are the only remaining steps |

**Official gate status:** `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
— reaffirmed by the **fourth** independent re-check at `0e3b001`. PR #440, #442
and #445 each recorded fixes without granting acceptance, and PR #441 was closed
as a non-independent diagnostic review.

**Next required steps before any real data read**, in order:

1. A **human + ChatGPT contract Gate-decision** on **D-5.8** (the coverage count
   floor, classified `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION` by the fourth
   re-check) and on the reading of contract §12.25 that PR #445 took. Taking it
   **before** the next fix PR is the same lesson PR #444 recorded: otherwise the
   fix session decides contract questions it may not decide.
2. **One** targeted-fix Work PR closing FB-1…FB-9 / FR-1…FR-18. FR-19 is a
   **separate** test-safety Work PR — it is not gate-3a research machinery.
3. A **fifth genuinely independent** re-check (separate session, no
   implementation context) accepting it.
4. The **P/V reader design PR** (contract §15.4). Contract §12.14's
   reader-freedom and reverse-caller pins should exist **before** it lands.
5. **Calendar artifact approval** — `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`.
   Not discharged by an accepted source audit.

Only then may a separately-authorised gate-3a continuation read/derive
design-span data. (This supersedes-by-progress the earlier phrasing "the source
audit is next": the *first* audit BLOCKED, the F-1…F-5 fixes merged, the
re-check BLOCKED again, the B-1…B-5 and BL-1…BL-5 fixes merged, and the third
independent re-check BLOCKED again on defects those fixes did not cover.)

**Contract referrals.** Referrals **2, 3 and 4** and **NR-A / NR-C / NR-D / NR-J /
NR-K** were **RULED by human + ChatGPT** and are recorded in
`docs/design/m15_contract_design_gate_decision.md` (see the gate table above);
they are **closed** and bind the targeted-fix Work PR — the Classification column
below is retained as the historical audit finding that produced them, not as an
open question. Referrals **1 and 5** remain genuinely open and deferred. The only
item still requiring a human + ChatGPT decision before the continuation is
**`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`** — the concrete
market-calendar artifact for the target epoch; its *contract* is already fixed,
and no session may invent market hours.

| Referral | Classification | Question | Raised by |
| --- | --- | --- | --- |
| Spread magnitude bound | `MAY_DEFER` — binds at latest at the §6 pre-run gate ("cost tables fixed") | No committed authority pins an absolute upper (or lower) bound on a quoted spread. PR #440 invented `MAX_PLAUSIBLE_SPREAD_PIPS = 100.0`; it has been removed rather than re-tuned, and the bound is now a required caller-supplied argument so the omission cannot be silent. **Deferral conditions:** the continuation must pass `None` *explicitly*, and it is recorded that any finite positive value satisfies "a bound was declared" | BL-5 |
| `missing_minute_count` semantics | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** | Does the committed inventory's field count **all** absent minutes (closure included) or only in-session ones? Leading/trailing partial buckets differ between the two emitted figures, and the committed per-file `gap_report` carries only two keys, so the crossed-quote drop counters would not survive into the inventory unless that schema is extended. **Third re-check adds a third cause of divergence:** crossed-quote drops are counted as missing source minutes in `total_missing_source_minutes_within_emitted_buckets`, contradicting the module's own docstring. The committed schema declares 2 keys; the code emits 17 | RF-2 |
| Crossed-quote disposition | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** | The merged PR #439 audit prescribed `ask_* >= bid_*` as a hard assertion (R-2, `:411-412`). This change re-disposes it to a counted drop on the `stage25_0a` precedent. Re-disposing a recorded audit finding is not an implementing session's call. **Third re-check:** the disposition also flips `eligible` and therefore `eligible_event_count` — not diagnostics-only — and `stage25_0a` is not admissible authority under pre-registration §11's closed reuse taxonomy | BL-4 |
| Drop-ratio acceptance | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** (derivative of the above; moot if that reverts to a hard assertion) | Is there a threshold above which a pair's crossed-quote drop ratio is unacceptable? `all_rows_dropped` is reported, never raised on, because a ratio threshold would be an invented number. The continuation **is** the adoption gate for the design dataset and no later gate re-derives it | BL-4 |
| Forward evidence shape | `MAY_DEFER` — binds at the forward-epoch adoption continuation (earliest ≈ 2026-10) | `forward_epoch_inventory.json` declares no `pair` key and a per-file `validation \| holdout` split. Until its shape is recorded, `assert_per_file_bounds(role="forward")` **refuses** rather than projecting the design roster onto it. Deferral is itself committed: `forward_epoch_adoption_manifest.json:23-28` marks these `PENDING … [FIXED-AT gate 3a continuation]` | BL-1 |
| **NR-A** — is `artifacts/m15_gate3a/` protected-immutable or the continuation's output directory? | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** | §9 requires it "untouched"; §5 requires the continuation to populate `design_m15_inventory.json` inside it; `guards._PROTECTED_PREFIXES` permits the write. Neither reading is supported over the other by any committed source | Third re-check (B-5) |
| **NR-B** — in what format must the continuation emit `ts_min_utc` / `ts_max_utc`? | `MAY_DEFER` — but fixes the continuation's own output format | `timeutil` refuses >6 fractional digits; the committed M1 inventory named as `source_checksum_authority` writes 9 (`2025-04-24T22:03:00.000000000Z`). Refusing is fail-closed and safe; nothing decides whether the house format is normalised, re-emitted or accepted | Third re-check (NR-B) |
| **NR-C** — who computes and attests `dead_window_bars_present: 0`? | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** | Declared in `design_m15_inventory.json:22` and emitted by **no** code path. Bound up with B-2: the T-7 helper certifies *declared* metadata and reads no bytes, so nothing in the machinery can produce the byte-level proof §5 requires | Third re-check (B-2) |
| **NR-D** — duplicate source minutes abort the whole pair, crossed quotes are a counted drop | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** (resolve with the crossed-quote referral) | Two opposite dispositions for two anomaly classes, neither pinned by any committed authority | Third re-check (NR-D) |
| **NR-E** — the lower spread-magnitude limb is already decided | `MAY_DEFER` (falls with the crossed-quote referral) | `cost_schema.py:181-186` accepts a zero spread on the same `stage25_0a` analogy whose standing the crossed-quote referral disputes | Third re-check (NR-E) |
| **NR-F** — the frozen all-in-cost formula is dimensionally incoherent | `MAY_DEFER` — binds when cost tables are produced | `SPREAD_UNIT = "price"` while the formula adds pip-unit constants `0.3` / `0.5`. A conversion step is implied and nowhere stated. Flagged in a merged fix note but never previously referred | Third re-check (NR-F) |
| **NR-G** — validation-role sample floors are unpinned | `MAY_DEFER` — binds at the validation kill gate | The committed spec says "below **the family's minimum**"; only holdout floors (`1000` raw / `400` N_eff) are frozen. The code correctly refuses to default, but the omission was never referred | Third re-check (NR-G) |
| **NR-H** — the scrubber's four shape thresholds are invented numbers | `MAY_DEFER`, but interacts with the `missing_minute_count` referral | `artifacts.py:73-76`. The natural shape for 20 per-file gap reports is refused by a threshold no authority pins | Third re-check (NR-H) |
| **NR-I** — the rollover exclusion window has no representation | `MAY_DEFER` — escalates if cost-table production is authorised | Ruling 4 freezes "rollover exclusion 21:55–22:15 UTC minimum — widen-only"; zero occurrences in the package, and `_check_session_partition()` requires the three sessions to tile all 1440 minutes, so no carve-out is expressible | Third re-check (NR-I) |
| **NR-J** — merged-audit R-8 limb 4 was re-disposed without referral | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** (same governance class as the crossed-quote referral) | R-8 required "Fix all four before the tables are produced"; 20 × 3 coverage became a reported boolean with no raise | Third re-check (RF-19) |

**Scope of the step list above (Two-Track).** Those steps are the route to
the **gate-3a continuation** — the committed design-M15 derivation, and every
formal read that depends on it. They are **not** the route to a **Track A**
exploratory read, which §2.1's narrow exception governs and which runs through
the Minimum Research Execution Gate instead (§3's ladder, §5a's template).
Neither route shortens the other: a Track A read discharges none of the steps
above, and passing the execution gate does not advance the continuation by one
item.

## 2. Research stop rules (mandatory for every session)

These are substantive research boundaries. Procedural stop rules — and the
list of things that are explicitly **not** reasons to stop — live in
`docs/governance/autonomous_development_policy.md` §11. Risk classification
rules — protected paths, upward escalation, the Green allowlist — are policy
§2–§8 and are not overridable by a task prompt.

1. **No real read before audit acceptance:** if a task asks for a real data
   read before the machinery source audit (currently: the F-1…F-5 re-check)
   is accepted, REFUSE and redirect to the audit gate. **One narrow exception**
   (`docs/design/m15_minimum_research_gate.md` §8.12.2): a **Track A**
   historical read, on the **design span only**, producing output classified
   **both** `NON_DECISION_BEARING_EXPLORATORY_ONLY` **and**
   `RESEARCH_SCRATCH_NON_AUTHORITATIVE`, **after** the Minimum Research
   Execution Gate has passed on a named head **and** an explicit human +
   ChatGPT read grant covers the operation. That is **five** conditions, not
   three — the exception's own three limbs plus the two execution conditions —
   and absent **any one of the five**, refuse as before. Nothing else in §2
   moves.

   These five are **not** the same enumeration as CLAUDE.md's "three
   execution-safety conditions" (§8.12.10) or the four-step order in
   `docs/design/m15_track_a_execution_gate.md` §1. They overlap and neither
   contains the other, so the governing set is their **union**: PR #451 merged;
   the P-1…P-15 propagation predicate true on a named master SHA; the Minimum
   Research Execution Gate passed on a named head; the derivation route
   committed in a diff; the read confined to the design span; the output
   carrying both classifications; and an explicit read grant. **The stricter
   reading wins where they differ.**
2. **No real M15 derivation before audit acceptance:** same refusal + redirect,
   and the same single Track A exception — a research-scratch derivation whose
   output is **not** the prereg §4 artifact and may never be recorded as one.
3. **No forward-epoch adoption** before sufficient forward data accrues AND an
   explicitly authorised gate-3a continuation PR exists — refuse and redirect.
4. **No validation, holdout, training, execution, or strategy metrics**
   without an explicit approved gate — refuse and redirect.
5. **No automatic chaining of irreversible stages:** real-data read → training,
   and validation → holdout, are separate gates with separate approvals.
6. **Forbidden-label block:** any task or diff introducing
   `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, `PRODUCTION_READY`, `MEETS`, or an
   equivalent final-success label outside a prohibition list → block or
   require human + ChatGPT review.
7. **Doc-only purity:** if evidence, data, model binaries, raw rows, candles,
   predictions, trade logs, local paths, secrets, Drive/R2 credentials, or
   environment dumps appear in a doc-only PR → block.
8. **Ambiguity rule:** if what a gate permits is ambiguous, choose the NARROWER
   (no-run, no-read) interpretation and require human + ChatGPT review. This
   applies to research scope, not to ordinary implementation choices — those
   the session decides on its own (policy §1). Classification itself is not a
   free choice: it escalates upward per policy §2–§3.
9. **Approval scope is exact:** an approval covers the operation and head it
   names. After merge approval, a changed head or an out-of-scope addition
   voids it (policy §10).

## 3. Remaining gate order

**The Two-Track ladder** (`docs/design/m15_minimum_research_gate.md` §8.11–§8.13),
inserted here so a session reading this file alone sees it:

| # | Gate | Template |
| --- | --- | --- |
| — | Two-Track contract approval (PR #451) | — |
| **MREG** | **Minimum Research Execution Gate** — Track A R1 enablement | §5a |
| A-R1 | Track A first real-data read (Red) | §5a + an explicit read grant |
| A-R2/R3 | Track A baselines and training (Red, **separate approvals**) | policy §6 |
| A-R4 | Track A `EXPLORATORY_OOS_SLICE` evaluation (Red; Q7 `N = 1`) | policy §6 |
| B-0 | Track A ends; candidate declared and re-pre-registered | §8.13.7 |
| B-1 | Track B surfaces frozen; `c` measured and committed | §8.13.7 |
| gate 3a cont. | The committed design-M15 derivation | §5 |
| gate 7 | The formal single-shot run | §6, §7, §8 |

Track A does **not** require the forward epoch to exist; Track B does.

Rows `B-0` and `B-1` are a **compression**. §8.12.0(4) records that "promotion
from Track A to Track B runs through **eight mandatory steps** and through no
other route", restated as seven ordered steps at §8.13.7. The ladder above
names where promotion sits in the order; it does not replace the route, and a
session preparing a promotion reads §8.13.7 rather than this table.


**PR shape for this order (policy §14).** Each audit or adoption step below is
a **Gate-decision PR** — it judges or changes the research state. The work it
judges is a single **Work PR** that carries its code, tests, docs, internal
audit and CI repair together; do not fragment a step into code / tests / docs
/ audit-preparation PRs. A post-approval irreversible run and its evidence go
in an **Execution-evidence PR**.

1. **Source-contamination / implementation source audit of the PR #432
   machinery** — *executed (PR #433): BLOCKED pending targeted fixes.*
   (1a) merge the reviewed targeted-fix PR — ✅ done (PR #434 → `5701ce8`);
   (1b) **independent source-audit re-check of F-1…F-5** (accept / block
   again) — **pending; this is the next gate.** If it accepts: one
   Gate-decision PR, then a separate approval for the continuation. If it
   blocks: one Gate-decision PR carrying the verdict → **one** targeted-fix
   Work PR (code + tests + docs + internal audit + CI fixes) → one independent
   re-check Gate-decision PR.
2. If accepted → **separately-authorised gate-3a continuation**: design-span
   M15 derivation metadata/checksums; optionally design-span cost tables if
   explicitly authorised. (Template §5.)
3. **Source/artifact audit of the gate-3a continuation outputs** if required
   by the approval.
4. **Code-only feature/label/model implementation** (native-M15 feature
   review, labels, calibrated EV gate) — still no validation/holdout
   execution unless separately authorised; T-1 warm-up W frozen here.
5. **Pre-run authorisation gate** (template §6).
6. **Single-run execution** — validation kill gate first; holdout once, only
   if it passes (template §7).
7. **Post-run audit** (template §8).
8. If and only if accepted → **next human + ChatGPT ruling** (replication /
   family B / program review — never self-granted).

**Forward-epoch adoption remains BLOCKED/WAIT** until enough forward data
exists (validation ≥ 3 months + holdout ≥ 2 months at/after 2026-04-25;
earliest ≈ **2026-10** per the PR #431 governance record). It resumes only as
a gate-3a continuation with its own approval, byte-level no-overlap proof,
and Gate-P2-style adoption artifacts.

## 4. Source-contamination audit template (reusable checklist)

**Scope note (Track A).** The checklist below asks whether a read route is
*absent*. That is right for the gate-3a machinery and impossible for **Track A**,
whose whole purpose is to have one. **Two** of §4's own items invert:
"real-data read routes — none reachable" becomes "**exactly one, declared and
gated**", and "real M15 derivation routes — none enabled" becomes "**exactly
one, selected in a diff**". Two further items are **added**, because §4 has no
counterpart to them: a single declared **write root**, and a single
**authorisation gate**. Everything else stays at **none**: broker, network,
external DB, credentials, model binaries, forward-epoch access, protected-path
writes.

One §4 item needs care rather than inversion: "**validation / holdout /
training / execution routes — none exist**". That holds for **R1**, and it does
**not** hold for R3/R4, which §8.12.2 records as training and computing
exploratory metrics. An auditor applying §4 to a later Track A stage must not
read the R1 answer forward. The executable form is `scripts/m15_track_a/containment.py`, and its
final statuses are `TRACK_A_EXECUTION_CONTAINMENT_PROBES_PASSED_BOUNDED_ASSURANCE` /
`TRACK_A_EXECUTION_CONTAINMENT_PROBE_FAILED` — deliberately not "verified", and
every report carries a `bounds` list of what it does **not** establish. It is an
**execution-containment** check, not a hostile-input audit, and it does not
replace the gate-6 source-contamination audit Track B still needs.

Use for the F-1…F-5 re-check and for any future machinery audit. The audit
must be **independent**: performed by a session separate from the one that
wrote the code, reading the source itself rather than trusting the fix report.
Any sufficiently capable model may perform it; the auditing AI may not give
final approval for the gate (policy §12).

The checklist may be **split across specialised audit roles** (policy §13) —
for example containment and forbidden routes, aggregation and boundary
correctness, artifact/scrubber probing, and a refutation role arguing the
machinery is still unsafe. Each role reads the source and diff itself and is
not given the other roles' conclusions; the lead reconciles conflicting
findings on the evidence rather than by majority, and reports any material
disagreement it cannot resolve as a blocker. Verify each:

- [ ] **Import graph** — outbound imports enumerated; only audited internal
      modules + stdlib; zero unexpected reverse callers.
- [ ] **Legacy path access** — no stage/compare, deployed-model, or legacy
      evidence path callable from or calling the audited package.
- [ ] **Real-data read routes** — none reachable; protected paths refuse
      (incl. `..` traversal); no CLI/`__main__`/file-readers added.
- [ ] **Real M15 derivation routes** — none enabled.
- [ ] **Validation / holdout / training / execution routes** — none exist.
- [ ] **Model binary routes** — none; **deployed model reuse** — none.
- [ ] **Broker / live / paper routes** — none.
- [ ] **Aggregation correctness** — UTC bucket boundaries; per-side OHLC; no
      mid construction; 15 DISTINCT minute-aligned source minutes for
      eligibility; duplicates + sub-minute timestamps fail closed;
      non-finite prices fail closed; no imputation; no synthetic weekend
      bars; gap report; unsorted-input behaviour; pip authority + JPY /
      non-JPY value-pinned scaling.
- [ ] **No-overlap / dead-window handling** — boundary off-by-ones at
      2026-02-28T23:59:59Z / 2026-03-01T00:00:00Z / 2026-04-24T23:59:59Z /
      2026-04-25T00:00:00Z; naive timestamps fail closed; per-file ts-bound
      assertions.
- [ ] **T-1 warm-up handling** — dead window never loaded; forward-only
      burn-in; W ≥ longest lookback; pre-forward loads fail closed.
- [ ] **T-7 no-overlap proof handling** — machine-checkable per-file bounds;
      p95 diagnostic requirement preserved.
- [ ] **Effective-N helper** — raw preserved; overlap + cross-pair
      adjustments; role handling fail-closed (unknown roles raise; validation
      never default-sufficient); `INSUFFICIENT_SAMPLE` floors.
- [ ] **Cost schema** — sessions frozen; median/p90/p95 finite +
      non-negative; padding 0.3 / cell 0.5 unloosenable; pip vs authority;
      quote-cost-validity scope; no real spread computation.
- [ ] **Artifact / scrubber** — raw rows, candles, predictions, model
      outputs, validation/holdout metrics, trade-level payloads, secrets,
      local paths, env dumps all rejected; smuggling probes (alternate keys,
      nested structures, credentialed URLs) run and results recorded.
- [ ] **Refusal guards** — synthetic-only modes; forbidden operations;
      forbidden statuses (normalised matching); protected paths; unknown
      flags fail closed.
- [ ] **Tests** — every audited behaviour has a test; every found defect gets
      a failing-before/passing-after regression test.
- [ ] **Non-authorisation** — neither code nor docs read as authorising any
      real read/derivation/run/claim.

**Required final statuses (choose exactly one):**
acceptable → `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_ACCEPTABLE_FOR_GATE3A_CONTINUATION`;
targeted fixes → `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`;
rewrite → `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_REQUIRES_REWRITE`.

## 5. Gate-3a continuation template (future design-span derivation PR)

**Scope.** This template governs the **gate-3a continuation** — the PR that
produces the *committed* design-M15 artifact and the byte-level proof. It does
**not** govern **Track A**, which is a different gate in §3's ladder and whose
whole purpose is the training and strategy metrics the clauses below forbid.
Scope follows the gate ladder, not the difficulty of compliance. Track A's
equivalent precondition is the **Minimum Research Execution Gate** (§5a), and
four of the clauses below are imposed on it directly there.

Binding shape — every clause mandatory:

- Only after the source audit (re-check) is **accepted**.
- **Design-span only** (2025-04-25 → 2026-02-28); the dead window
  (2026-03-01 → 2026-04-24) is excluded from every artifact.
- **No forward-epoch adoption** (forward remains WAIT).
- **No validation computation; no holdout evaluation; no strategy metrics;
  no training; no execution.**
- **Metadata-only / scrub-clean** outputs.
- Produce the **design M15 inventory + checksums** (populating the PR #431
  schema; 20 files; per-file ts-bounds).
- Produce the **byte-level no-overlap proof** (per-file `ts_max ≤
  2026-02-28T23:59:59Z`; zero dead-window bars).
- Optionally produce **cost tables from the design span only**, if and only
  if explicitly authorised in the approval (median + p90 + p95 diagnostic;
  padding 0.3; cell 0.5; quote-cost-validity scope).
- **No `NEW_EPOCH_ADOPTED`.** **No `BYTE_ADMISSIBLE`** unless separately
  ruled. Forward epoch remains **WAIT**.

## 5a. Minimum Research Execution Gate template (Track A R1 enablement)

The gate's own record is `docs/design/m15_track_a_execution_gate.md`, and its
executable half is `scripts/m15_track_a/`.

**Scope.** Track A's first real-data read, and nothing else. Passing it
authorises **R1 only** — R3 (training) and R4 (evaluation) remain separate Red
gates with separate approvals (policy §6, §2.5). Every item verified true, with
citations, on a **named head**:

*Decisions the human + ChatGPT round of 2026-08-30 closed, so a session
does not reopen them:* the turnover axes (prereg **§9a**), prereg **§13a**
(`P_7_DISCHARGED_AT_THIS_RULING`),
`TRACK_A_R1_BOUNDED_ASSURANCE_THREAT_MODEL_ACCEPTED` and
`GENERAL_ADVERSARIAL_AUDIT_COMPLETE_FOR_TRACK_A_R1_BOUNDED_SCOPE`
(gate document §15). **None of them authorises a read.**

**How to read the boxes.** A ticked box means the item was verified **on the
head named beside it**, with the citation given. An unticked box is not a
formality: the R1 execution command of 2026-08-31 was refused because six items
that nobody had tried to verify turned out to be false, so the boxes are ticked
only where something was run or read, never where something was believed.

- [x] **PR #451 approved and merged** — `4f45515`, 2026-08-30, so
      `APPROVAL_IDENTIFIER_PENDING_UNTIL_MERGE` and
      `THE_TWO_TRACK_SECTIONS_ARE_RULED_AS_RECORDED_AND_NOT_YET_CITABLE_AS_AUTHORITY`
      are **discharged**. §8.11–§8.13 are citable authority.
- [x] **Governance propagation complete** (see the §8.9 caveat below), as
      §8.12.13 C-10 defines it: the
      **P-1 … P-15** predicate on named files, discharged **in those files** at
      PR #455 — P-5 in the §1 gate table above, **P-10** on **all eight**
      RULED MRG sections rather than on §8.13 alone (verified 8 of 8 at
      PR #456; C-9 wants the identifier on *every* RULED section, and one
      section declaring it for the others at a distance is the self-assessment
      C-10 refuses). **The population is the headings that spell `RULED` in
      capitals**; §8.9 spells it lowercase and carries no identifier, so on a
      case-insensitive reading of C-9 the count is 8 of 9 and this box is not
      yet true — disclosed at PR #456 rather than resolved, because deciding
      which reading governs is a ruling, not a session's call. **P-13** in the
      gate-4 design audit's §1a. C-10 requires
      the predicate true on a named *master* SHA and it now is: PR #455 merged
      as **`fc3e0f8`**. An earlier revision of PR #455 ticked this box on
      discharges written into a *different* file; two review roles refuted it,
      and
      `PROPAGATION_COMPLETENESS_IS_A_PREDICATE_ON_NAMED_FILES_NOT_A_SELF_ASSESSMENT`
      is why. The per-item table is
      `docs/design/m15_track_a_execution_gate.md` §12.
- [x] **Q8** — `scratch.SCRATCH_ROOT_RELATIVE` is a module constant with no
      caller-supplied component, and `assert_writable` refuses outside it.
      Tested: `test_a_write_outside_the_permitted_roots_is_refused`.
- [x] **FR-19** — a default `pytest` reaches no real DB, no `.env`, no external
      network, no broker, no real historical read, no production storage.
      `tests/optin.py` + `tests/conftest.py`; the two residual routes the fourth
      re-check recorded (route-dependent `.env` matcher, UDP/DNS) are unchanged
      and still disclosed.
- [x] **One** historical read route, gated
      (`scripts/m15_track_a/read_route.py`), and **one** derivation route
      (`scripts/m15_track_a/derivation.py`) — now with a body, and with the
      `aggregate_m15` bypass **closed** at the aggregator itself
      (`scripts/m15_gate3a/derivation_containment.py`). Tested:
      `test_a_direct_aggregate_m15_bypass_is_refused`.
- [x] **Isolation** — network, external DB, broker, live, demo and order
      submission all refuse, demonstrated by `containment.audit()` returning
      `TRACK_A_EXECUTION_CONTAINMENT_PROBES_PASSED_BOUNDED_ASSURANCE`, and by
      `test_network_db_and_broker_stay_refused`. Bounded assurance, as the
      status says: `AUDIT_BOUNDS` names what it does not establish.
- [x] **Seen-data ledger** — write-ahead, append-only, declared before the
      interval is touched, warm-up included, **and committed**: it moved to
      `artifacts/track_a_scratch/ledger/`, which `.gitignore` un-ignores while
      the research output around it stays ignored. §8.13.5 item 5 required
      "committed" and the file had been in a gitignored tree. Tested:
      `test_the_ledgers_are_written_under_the_committed_root`,
      `test_the_declaration_precedes_the_read`.
- [x] **Breadth (`K`) record** — in R-7's unit, recorded as it accrues, and
      committed beside the seen ledger. R1 records an entry with
      `result_observed=False`, so `K` is explicitly **0** rather than absent:
      R1 measures and scores nothing.
- [x] **Run and calendar identity** — `RunIdentity` carries
      `CALENDAR_UTC_DATES_NO_MARKET_HOURS` as a declared label, and **Track A
      authors no market hours**. PR #455's first revision did author some; the
      calendar and its artifacts are **deleted**, because D-6 says no market
      open/close instant, DST transition or holiday list "may be added by an
      implementer". What remains is `scripts/m15_gate3a/session_windows.py`,
      carrying only Ruling 4's frozen session partition and its frozen rollover
      window — both fixed UTC clock windows, neither a market-hours claim — each
      pinned against a **hand-written oracle** in
      `tests/m15_gate3a/test_session_windows_independent_oracle.py`. R1 reports
      coverage as `COVERAGE_AUTHORITY_ABSENT_R1_REPORTS_A_DECLARED_LABEL_DIAGNOSTIC`,
      which is the route execution gate §8 provides for.
      `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` stays open and is
      not discharged here.
- [x] **Q7's `N = 1`** on the `EXPLORATORY_OOS_SLICE` is enforced at run time
      (`oos_budget`), and `K` is not a substitute for `N`. The slice is
      `2025-12-29 … 2026-02-28` and a `track_a_historical_read` grant **cannot be
      constructed** over it.
- [x] **No consumed-window leakage** — the dead window and the forward epoch are
      refused at the grant, at the declared interval, at the computed window and
      at the row. Warm-up is included in the touched interval, and is refused
      rather than trimmed. The `DESIGN_END` trailing purge remains a
      **downstream** obligation the declaration guard cannot detect, carried as
      `A_TRAILING_PURGE_APPLIES_AT_THE_SLICE_BOUNDARY_AND_IS_NOT_DISCHARGED_BY_THIS_READ`.
- [x] **No legacy-evidence dependency** (C-8 held). R1 reads the committed
      `365d_BA` M1 source and nothing else — the calendars an earlier revision
      of PR #455 authored are deleted — and nothing under
      `artifacts/ml_step4/**`; the isolation hook refuses that tree by name.
- [x] Track A output is **both** `NON_DECISION_BEARING_EXPLORATORY_ONLY` and
      `RESEARCH_SCRATCH_NON_AUTHORITATIVE`, on `HistoricalRead`, `DerivedM15` and
      `R1Survey` alike, and lands nowhere near the evidence tree.

**The two items no session could tick. Both are OUTSTANDING at this head.**

- [ ] **An explicit human + ChatGPT `track_a_historical_read` grant** against the
      implementation fingerprint of the head being run. Three have been issued
      and all three are **invalid**, each voided by the change that came after
      it: PR #454's at `497e187b…`, PR #456's pair at `e43583e0…`, and PR #458's
      pair at `64fbace9…`, which the R1 orchestrator voided by widening the
      declared surface from 29 files to 30. Every recorded number is left
      exactly as a human approved it; re-issuing is a separate act from
      rewriting. Tested:
      `test_the_recorded_grant_is_invalidated_by_the_orchestrator` and
      `test_the_invalidated_grant_is_actually_refused_at_the_gate` in
      `test_reissued_dual_grants.py`, and
      `test_the_two_superseded_records_are_still_refused` for the older two.
- [ ] **An explicit human + ChatGPT `track_a_m15_research_derivation` grant** —
      §3 of the same record, same head, same fingerprint, arm (i) route only, R1
      only. A read grant does not authorise a derivation (§2.5), which is why
      there are two rather than one widened. Its *scope* is settled and tested:
      `test_neither_grant_covers_the_other_operation` for the coverage half,
      `test_a_direct_aggregate_m15_bypass_is_refused` for the bypass, and
      `tests/m15_track_a/test_authorization_integrity.py` for the derivation's
      **actual input**. Only the binding is stale.

`TRACK_A_R1_PREFLIGHT_13_OF_15_BOTH_GRANTS_AWAIT_REISSUE_ON_THE_CURRENT_FINGERPRINT`.

**13 of 15, and the two grant rows are un-ticked rather than ticked with a
correction attached.** PR #457 and PR #459 each left them ticked and wrote the
correction underneath; a review role found the second one asserting the grants
were "currently in force" and "accepted by `require_authorization` on this tree"
while measuring a refusal, with the correction eighty lines below — the exact
self-contradiction this section elsewhere says it exists to prevent. A box is
ticked where something was verified, and these two are not verifiable at this
head. They become true again when the grants are re-issued against
**`18124a7d6f05b5bcf69e8efe18cc4febdcb025d2251c7904693dcd8e41f36fd0`**, and
`test_the_two_grant_rows_are_ticked_only_when_the_grants_actually_validate`
enforces exactly that correspondence, so the tick can no longer run ahead of the
fact.

One *other* box still carries a caveat and this paragraph does not erase it: item
2 records that P-10's population is the headings spelling `RULED` in capitals,
and that on a case-insensitive reading of C-9 §8.9 is a ninth section without an
identifier, making the count 8 of 9. That caveat is unchanged and unresolved here
— deciding which reading governs is a ruling.
PR #457 closed the two authorization-integrity defects the review of PR #456
disclosed; both fixes edit the declared surface, so the fingerprint moved off
`e43583e0…` and both PR #456 grants were refused. PR #458 re-issued them against
`64fbace9…` at head `c2cdea0`, measured on the merged tree. The superseded
records are kept unedited.

Every mechanical prerequisite is in place, demonstrated on synthetic data end to
end. The grants are **not** currently accepted by `require_authorization` on this
tree — the orchestrator moved the fingerprint — so what is left is re-issuing
them. **Nothing has been read**; the seen-data ledger is empty and the
development corpus is `UNSEEN`.

**Read this before treating 15 of 15 as permission.**

PR #455 added the two grant rows above to a checklist whose closing paragraph
still read "the read grant is deliberately NOT an item of this checklist",
justified on the ground that a fully-ticked §5a would then *be* the
authorisation. That was a contradiction inside one section, and PR #456 had to
resolve it one way or the other. It resolves it by **stating the consequence
plainly instead of denying it**, because the denial does not survive the text.

**What §8.12.1 actually says**, quoted rather than paraphrased — an earlier
revision of this paragraph paraphrased it backwards, and a review role caught
that:

> | | Contract permission | Execution authorisation |
> | Who gives it | a human + ChatGPT contract ruling | a named gate, against a checklist, on a named head |
> | What it produces | a permitted route | a permitted **run** |
>
> Every prior confusion in this packet's history has run through this seam: an
> approval of a *document* being read afterwards as an approval of an
> *operation*.

So §8.12.1 does **not** say a checklist cannot authorise a run; it says a
checklist is exactly the thing that does. And §6 of this playbook says "Track
A's pre-run checklist is §5a". Put together: **with 15 of 15 on a named head and
both grants recorded, the recorded authority for R1 is complete.** Saying
otherwise would be the false comfort this section exists to prevent.

**What is therefore still missing is not a document — it is an act.**

> **Step 3 (separate).** An explicit human + ChatGPT **execution command**
> naming the operation, span, pairs, timeframe and approved head SHA. A
> real-data read is **Red** (policy §5), and Red requires human + ChatGPT
> approval *before you run it*. That is a decision taken at a moment, not a
> state a file can reach. Constructing a `ReadGrant`
> (`scripts/m15_track_a/authorization.py`) is not the act of granting one, and
> reading a ticked checklist is not the act of being commanded.

`TRACK_A_R1_AUTHORITY_INCOMPLETE_BOTH_GRANTS_AWAIT_REISSUE_EXECUTION_STILL_EXPRESSLY_WITHHELD`.
The authority is **not** complete at this head: both grants are invalid, and the
human instruction that produced them directed in the same breath that nothing be
executed. So R1 is withheld twice over — no valid grant, and no command. A
session that later finds this section at 15 of 15 has found a complete authority
and **still no command**, and must stop anyway; that is what the paragraph above
is for.

**The two defects that sat here are discharged.**
`DERIVATION_ROUTE_ROW_LEVEL_GUARDS_AND_REQUEST_TYPE_PIN_ABSENT_REFERRED` and
`FINGERPRINT_SURFACE_IS_NOT_THE_TRANSITIVE_CLOSURE_RELATIVE_IMPORTS_MISRESOLVED_REFERRED`
were closed at **PR #457**, and the grants they would have voided were re-issued
at PR #458 against the resulting fingerprint. This paragraph previously said both
still blocked a first read; a review role found it standing ninety lines below the
paragraph that said they were fixed, which is the sort of self-contradiction §5a
exists to prevent.

**The R1 orchestrator now exists**, and it was the last piece of engineering this
section recorded as outstanding. `scripts/m15_track_a/r1_orchestrator.py` is the
formal entry point: `preflight` → write-ahead seen declaration → gated M1 read →
authorised M15 derivation on the **same** `ReadRequest` object → breadth `K` →
the committed survey → stop. It adds no research logic, re-implements no read,
derivation or survey semantics, contains no `try`/`except` around a stage, and
reaches no next stage by construction — `oos_budget` is not imported and a test
pins its whole call surface. A synthetic end-to-end drives that entry point
rather than a second composition, because a route that is only exercised through
a fixture is a route nobody has reviewed as the thing that will run.

**The bounded-memory route follows it.** `scripts/m15_track_a/streaming.py`
replaces the full-buffer pair — one read of the whole corpus, then one derivation
over everything it returned — with a per-(pair, window) loop that releases each
window's raw M1 rows before reading the next. A review role had measured the old
shape at roughly 4.5–6 GB for the authorised corpus, with an `OutOfMemoryError`
landing *after* the irreversible seen-data declaration; that was the last
substantive blocker in front of a first read.

The accumulation that lets a batched pair still produce **one** gap report lives
in `scripts/m15_gate3a/incremental_m15.py`, beside the aggregator whose
intermediate quantities it combines. Doing it in Track A would have needed four
of that package's private helpers, and the WP5 reader-freedom pin lists what
Track A may import from it **by name**: one public class was added to that list
with the reason recorded, and four privates were not. Loosening a committed
prohibition to make a memory optimisation possible is not a trade this programme
makes.

**Both changes moved the fingerprint, as they had to** — `64fbace9…` →
`1f1f0ed5…` → `2be46927…`, surface 30 → 32 — so the two grants recorded at
PR #458 are invalidated and the two grant rows above need re-issuing before a
read. The record is kept unedited each time; re-issuing is a separate act from
rewriting.

One disclosure is carried forward rather than closed:
`DERIVATION_ROUTE_DOES_NOT_PIN_ITS_TIMEFRAME_TO_THE_COMMITTED_SOURCE_CONSTANT_REFERRED`
(`m15_track_a_r1_dual_grants_reissued.md` §3) — no data scope widens, and the fix
is a separate Work PR because it too would void the grants. The orchestrator
supplies the pin at the route level: `PLAN_TIMEFRAME` **is**
`read_route.SOURCE_TIMEFRAME` and `preflight` refuses a plan naming anything
else, so a non-M1 derivation is unreachable through the formal entry point. The
referral stays open for direct callers, and the orchestrator is why there should
not be any.

**One preflight item is a gate-time obligation rather than an in-process check**,
and the reason is worth recording. The first drafting had `preflight` read this
playbook and count these boxes; `containment.audit()` immediately reported
`TRACK_A_EXECUTION_CONTAINMENT_PROBE_FAILED`, because `_check_single_read_route`
sweeps every module in the package for a file-opening call and `read_text()` is
one. Silencing that would have meant adding the orchestrator to
`_PERMITTED_FILE_OPENERS` — widening the declared read surface in order to check
a document. So §5a's completeness is verified in CI by
`test_the_playbook_checklist_is_complete_at_this_head`, outside the gated
surface, in the same category as the ancestry check the grant record already
handles that way. `PLAYBOOK_5A_COMPLETENESS_IS_A_GATE_TIME_OBLIGATION_VERIFIED_IN_CI_NOT_FROM_INSIDE_THE_GATED_SURFACE`.

**On "the gate authorises R1 only":** that phrase states the **scope** a gate
pass can reach — R1, never R3 or R4 — not that a pass is **sufficient** for R1.
Reaching a gate is not passing through it.

## 6. Pre-run authorisation template (before ANY single run)

**Scope.** The **formal single-shot run** — Track B's confirmation. Its items
require an adopted forward epoch, fixed cost tables and a once-only run, none of
which is satisfiable or meaningful for an exploratory iteration; Track A's
pre-run checklist is §5a. **Track B passes this in full.**

All of the following must be verified true, with citations, before a run is
authorised:

- [ ] Source audit (incl. F-1…F-5 re-check) accepted.
- [ ] Design-span derivation (gate-3a continuation) accepted.
- [ ] **Forward epoch adopted** in a later gate-3a continuation with enough
      accrued data (val ≥ 3 mo, holdout ≥ 2 mo) + byte-level no-overlap proof.
- [ ] Cost tables fixed (design-span data only; committed metadata).
- [ ] Effective-N estimator fixed and human-approved.
- [ ] T-1…T-7 satisfied (warm-up W frozen; EV payoff semantics pinned; ratio
      rule computed **from the §4 derivation artifact under the declared
      candidate's frozen cost table** — a Track A measurement **fires** T-3's
      block but does **not** discharge this checkbox, because §8.11.2(1) stops a
      Track A result advancing the programme while a finding that *stops* it is
      not advancement; median eligible barrier/cost < 3.0 BLOCKS the run
      pending a new ruling; timeout-share trigger armed; maxDD notional =
      10,000 pips; deferred items approved; no-overlap proofs + p95 present).
- [ ] No consumed-window leakage (2026-03-01 → 2026-04-24 dead at all
      timeframes for all roles, including feature warm-up).
- [ ] No legacy-evidence dependency (C-8 declaration held).
- [ ] No validation/holdout contamination (chronology + purge 25 bars).
- [ ] All acceptance criteria frozen (PR #429 §9 as tightened by gate 4 —
      design audits may only have tightened them).
- [ ] The run is **exactly once**; no rerun-into-search.
- [ ] Holdout is touched **only after the validation kill gate passes**
      (validation net > 0 under empirical cost AND gross ≥ 1.5× cost at ≥ 1
      registered `ev_min`, within the turnover budget). Kill-gate failure
      closes family A without holdout consumption.

## 7. Single-run execution report template (required fields)

**Track field (required).** Every run report names its track: `TRACK_A` or
`TRACK_B`. A `TRACK_A` report may not use §8's `M15_SINGLE_RUN_EVIDENCE_*`
vocabulary, which is **Formal Confirmation only**; it reports a conclusion and
its `K` count, never its numbers.

- run ID · code SHA · PR head/base SHAs
- data artifact IDs (design/validation/holdout inventories + checksums)
- validation decision (per registered `ev_min`; metrics per operating point)
- selected EV threshold (`ev_min`) + tie-rule application
- validation kill gate passed: yes/no (no → family closed, holdout untouched)
- holdout touched: yes/no
- holdout metrics **if and only if authorised** (single evaluation)
- no-rerun declaration · no-tuning-after-result declaration
- generated artifacts (metadata-only list) · scrub report
- exact tests run + results · failures/deviations (honest, verbatim)

## 8. Post-run audit template (checklist)

**Track field (required).** A post-run audit names its track. The four
statuses below are **Formal Confirmation (Track B) only** — a Track A run may
not carry one, and in particular may not carry the one containing `MEETS`.

**A fifth status, for a void registration** (§8.12.13 C-8): where a
re-pre-registration is declared void — taken after confirmation data was
observed — the run is recorded
`M15_SINGLE_RUN_EVIDENCE_VOID_REGISTRATION_NOT_LATE`, the work done under it is
`NON_DECISION_BEARING_EXPLORATORY_ONLY`, and the span it touched is
`EXPLORATORY_SEEN_DATA`. **Void is declared by a party other than the executing
session**, on the committed ledger and declaration objects.



- [ ] data lineage (inventory → checksums → run inputs)
- [ ] code SHA (manifest = executed commit)
- [ ] run reproducibility level declared honestly
- [ ] pip-size authority (per-pair; JPY 0.01 / non-JPY 0.0001; no global)
- [ ] M15 aggregation correctness (distinct-minute eligibility; finite prices)
- [ ] dead-window exclusion (byte-level proof holds)
- [ ] warm-up burn-in applied (W bars event-ineligible; no pre-forward loads)
- [ ] validation/holdout split (chronology, purge 25, holdout-once)
- [ ] cost model (frozen tables used; padding + cell as registered)
- [ ] spread stress (2× and p90 both computed) · p95 diagnostic reported
- [ ] labels (spread-floored barriers; hurdle; horizon 24; SL-first; timeout MTM)
- [ ] EV payoff semantics (W̄/L̄ per T-2 pinned definitions, design-frozen)
- [ ] effective-N (raw + effective reported; floors applied)
- [ ] timeout share (mandatory; > 60% triggers investigation before citation)
- [ ] ratio rule (median eligible barrier/cost ≥ 3.0 verified pre-run)
- [ ] concentration gates · turnover budget · gross/net decomposition
- [ ] stress survival (net ≥ 0 at 2× AND p90) · Sharpe · maxDD (10,000-pip notional)
- [ ] no rerun · no metric cherry-picking (all registered metrics reported)
- [ ] no production-readiness claim anywhere

**Required final statuses (choose exactly one):**
`M15_SINGLE_RUN_EVIDENCE_VALID_DOES_NOT_MEET` ·
`M15_SINGLE_RUN_EVIDENCE_VALID_MEETS_PREREGISTERED_CRITERIA` ·
`M15_SINGLE_RUN_EVIDENCE_INVALID` ·
`M15_SINGLE_RUN_EVIDENCE_INSUFFICIENT_SAMPLE`.

**Binding interpretation:** even
`M15_SINGLE_RUN_EVIDENCE_VALID_MEETS_PREREGISTERED_CRITERIA` is **not**
production readiness, not paper/live authorisation, and not replication — it
requires a separate human + ChatGPT ruling (disjoint replication before any
stronger claim; the M1 precedent applies).

## 9. Merge approval checklist (standard, every Amber/Red PR)

Run these read-only checks immediately before merging an approved PR. (Green
PRs meeting every policy §4 self-merge condition do not need this ceremony;
anything touching a protected path (policy §3) does.)

- [ ] PR open · [ ] PR mergeable
- [ ] head SHA still the approved one (else the approval is void — do not
      merge, report the new SHA and request re-review; policy §10)
- [ ] base = expected master tip
- [ ] CI green on the reviewed head
- [ ] touched files exactly match the approved scope
- [ ] no unexpected code/test/config changes
- [ ] no raw data / raw candles / predictions / model outputs /
      validation-holdout metrics / trade-level rows
- [ ] no secrets, local/personal paths, Drive/R2 credentials, env dumps
- [ ] no generated execution evidence (unless the gate explicitly produces it)
- [ ] no model binaries
- [ ] prior evidence directories untouched
      (`artifacts/ml_step4/365d_ba_v1/*`, `artifacts/m15_gate3a/*`)
- [ ] protected stage24/stage25 artifacts clean (when relevant)
- [ ] working tree clean for the PR scope
- [ ] statuses correct (required + carried + always-binding present;
      forbidden labels only in prohibition lists)
- [ ] non-authorisation statements present
- [ ] **track named** — `TRACK_A` or `TRACK_B` — for any PR carrying run output
- [ ] **no Track A numeric output committed**; a Track A PR reports the
      conclusion and the `K` count, not the numbers
- [ ] research-scratch root untouched by anything but Track A
      (`artifacts/track_a_scratch/`)

## 10. Forbidden labels and wording

Block, or require human + ChatGPT review, whenever any of these (or a
near-synonym) appears outside a prohibition list:

`PASS` · `Tier 1` · `FORMALLY_VERIFIED` · `PRODUCTION_READY` ·
`READY_FOR_LIVE` · `M15_AUTHORISED` · `H1_AUTHORISED` · `H2_STARTED` ·
`PHASE_C2_STARTED` · `NEW_EPOCH_ADOPTED` · `BYTE_ADMISSIBLE` · `MEETS` ·
`ROBUST` · `DEPLOYABLE`

Near-synonym guidance: "validated", "proven profitable", "ready to deploy",
"green-light", "cleared for live/paper", and casing/whitespace variants of
the above are treated identically. These tokens may appear only inside
prohibition lists — except where a specific, explicitly-approved gate defines
a narrowly-scoped status containing one (e.g. the §8 post-run vocabulary),
and then only as that exact registered status string.
