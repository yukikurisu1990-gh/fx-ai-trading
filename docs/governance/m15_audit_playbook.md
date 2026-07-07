# M15 audit playbook — durable governance record and gate discipline

- **Document class:** doc-only governance playbook. Binding operating
  instructions for every future Claude / Opus / Fable session that proposes,
  implements, audits, or merges any M15 / post-M1 research work. Executes
  nothing; authorises nothing.
- **Status:** `M15_AUDIT_PLAYBOOK_AND_CLAUDE_RULES_RECORDED`
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
  · `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_ACCEPTABLE_FOR_GATE3A_DATASET_EPOCH_ADOPTION`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Companion files: `docs/prompts/m15_future_audit_templates.md` (copy-paste
  prompts), `docs/prompts/m15_claude_operating_prefix.md` (session prefix),
  root `CLAUDE.md` (mandatory pointer).

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, or `DEPLOYABLE`; those tokens appear only
in prohibition lists (§10) and in template status vocabularies.

---

## 1. Current gate state (as recorded at authorship)

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
| Targeted fix PR for F-1…F-5 (PR #434) | **OPEN, not merged** — must be rebased onto post-#433 master, reviewed at its new head, and merged only with explicit approval |
| Source-audit **re-check** of the F-1…F-5 fixes | **NOT started** — required after the fix PR merges, before any real read |
| Gate-3a continuation (real design-span derivation) | **NOT authorised** until the re-check accepts the fixes |

**Next required step before any real data read:** merge the targeted fixes
(after review), then a **short Fable 5 source-audit re-check of F-1…F-5**.
Only after that re-check is accepted may a separately-authorised gate-3a
continuation read/derive design-span data. (This supersedes-by-progress the
earlier phrasing "the source audit is next": the *first* audit ran and
BLOCKED; the re-check is now the gatekeeper.)

## 2. Immutable stop rules (mandatory for every session)

1. **Head-change stop:** if a PR head SHA changes after review/reporting —
   even doc-only or hygiene-only — STOP, do not merge or proceed, and report
   the new SHA for human + ChatGPT review.
2. **No real read before audit acceptance:** if a task asks for a real data
   read before the machinery source audit (currently: the F-1…F-5 re-check)
   is accepted, REFUSE and redirect to the audit gate.
3. **No real M15 derivation before audit acceptance:** same refusal + redirect.
4. **No forward-epoch adoption** before sufficient forward data accrues AND an
   explicitly authorised gate-3a continuation PR exists — refuse and redirect.
5. **No validation, holdout, training, execution, or strategy metrics**
   without an explicit approved gate — refuse and redirect.
6. **Forbidden-label block:** any task or diff introducing
   `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, `PRODUCTION_READY`, `MEETS`, or an
   equivalent final-success label outside a prohibition list → block or
   require human + ChatGPT review.
7. **Doc-only purity:** if evidence, data, model binaries, raw rows, candles,
   predictions, trade logs, local paths, secrets, Drive/R2 credentials, or
   environment dumps appear in a doc-only PR → block.
8. **Ambiguity rule:** if the current step is ambiguous, choose the NARROWER
   (no-run, no-read) interpretation and require human + ChatGPT review.

## 3. Remaining gate order

1. **Source-contamination / implementation source audit of the PR #432
   machinery** — *executed (PR #433): BLOCKED pending targeted fixes.*
   Sub-steps now pending: (1a) merge the reviewed targeted-fix PR;
   (1b) **short Fable 5 re-check of F-1…F-5** (accept / block again).
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

Use for the F-1…F-5 re-check and for any future machinery audit. Verify each:

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

## 9. Merge approval checklist (standard, every M15 PR)

- [ ] PR open · [ ] PR mergeable
- [ ] reviewed head SHA unchanged (else STOP per §2.1)
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
