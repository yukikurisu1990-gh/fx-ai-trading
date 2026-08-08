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

Last reconciled against master at `c3a0468` (2026-08-08); master CI green.

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
| **Third independent source-audit re-check** (this record) | **executed — verdict `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`** (`docs/design/m15_third_independent_source_audit_recheck.md`). Run in a session separate from every fix author, six independent roles. **Seven blockers B-1…B-7 + twenty-nine required fixes RF-1…RF-29.** Containment against real data / derivation / training / execution / broker / credentials re-derived **CLEAN** and proved, not inherited. Mutation resistance measured: 182 mutations, 154 killed, **19 genuine coverage holes** |
| Fourth targeted-fix Work PR (B-1…B-7, RF-1…RF-29) | **NOT started** |
| Fourth **independent** re-check | **NOT started** — must run in a session separate from every fix author |
| Contract Gate-decision on referrals 2 / 3 / 4 (+ NR-A, NR-C, NR-D, NR-J, NR-K) and the byte-level T-7 proof | **RULED by human + ChatGPT; recorded, awaiting merge** — `docs/design/m15_contract_design_gate_decision.md`, status `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED`. Crossed quotes **hard fail-closed** (merged R-2 is authority; no drop-and-count); rejection tolerance **zero and structural**, not an empirical threshold; the missing-minute schema replaced by **six separately measured quantities**; **hashing is a byte read** (no raw-source re-hash without explicit read authorisation; proof subject = derived M15 bytes); T-7 coverage is **set equality** per pair against an approved calendar, not min/max containment; NR-A / NR-C / NR-D / NR-J decided; byte-level proof = **BI ∧ TC ∧ CV ∧ DB**, declaration-only tokens may never be promoted. Adds the negative-control rule and a twenty-term pinned-definition requirement. **Only open item:** `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` |
| Gate-3a continuation (real design-span derivation) | **NOT authorised** until an independent re-check accepts the fixes **and** the contract Gate-decision resolves referrals 2/3/4 |

**Official gate status:** `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
— reaffirmed by the third independent re-check at `c3a0468`. PR #440 and PR #442
each recorded fixes without granting acceptance, and PR #441 was closed as a
non-independent diagnostic review.

**Next required steps before any real data read**, in order:

1. **One** targeted-fix Work PR closing B-1…B-7 / RF-1…RF-29.
2. A **fourth genuinely independent** re-check (separate session, no
   implementation context) accepting it.
3. A **human + ChatGPT contract Gate-decision** on referrals 2, 3 and 4 —
   together with the two new referrals NR-A and NR-D, which are inseparable from
   them. This should be taken **before** the fix PR settles the crossed-quote and
   gap-report semantics, or the fix session will decide the same contract
   questions the audit found it may not decide.
4. A design decision for B-2: how a **byte-level** no-overlap proof is produced
   at all, given the package must not read data.

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

## 2. Research stop rules (mandatory for every session)

These are substantive research boundaries. Procedural stop rules — and the
list of things that are explicitly **not** reasons to stop — live in
`docs/governance/autonomous_development_policy.md` §11. Risk classification
rules — protected paths, upward escalation, the Green allowlist — are policy
§2–§8 and are not overridable by a task prompt.

1. **No real read before audit acceptance:** if a task asks for a real data
   read before the machinery source audit (currently: the F-1…F-5 re-check)
   is accepted, REFUSE and redirect to the audit gate.
2. **No real M15 derivation before audit acceptance:** same refusal + redirect.
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

## 6. Pre-run authorisation template (before ANY single run)

All of the following must be verified true, with citations, before a run is
authorised:

- [ ] Source audit (incl. F-1…F-5 re-check) accepted.
- [ ] Design-span derivation (gate-3a continuation) accepted.
- [ ] **Forward epoch adopted** in a later gate-3a continuation with enough
      accrued data (val ≥ 3 mo, holdout ≥ 2 mo) + byte-level no-overlap proof.
- [ ] Cost tables fixed (design-span data only; committed metadata).
- [ ] Effective-N estimator fixed and human-approved.
- [ ] T-1…T-7 satisfied (warm-up W frozen; EV payoff semantics pinned; ratio
      rule computed — median eligible barrier/cost < 3.0 BLOCKS the run
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
