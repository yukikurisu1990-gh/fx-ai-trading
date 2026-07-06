# Fable 5 design audit — Family-A M15-first cost-hurdle-aware pre-registration (gate 4)

- **Document class:** doc-only adversarial design audit of the frozen PR #429
  contract. Not an implementation PR, not a dataset/epoch adoption PR, not an
  execution PR. **Nothing is trained, read, derived, computed, or executed.**
- **Branch:** `docs/fable5-m15-preregistration-design-audit`
- **Base:** master `282a491ed861a5059c3fd768e5536faf7f6a70e0` (post PR #429 merge).
- **Audit target:** `docs/design/m15_first_cost_hurdle_aware_preregistration_design.md`
  (the frozen contract, §16 rulings 1–13), against the PR #427/#428 program
  records; M1 closure records (PR #425/#426) as context only.
- **Core audit rule (PR #429 Ruling 10):** this audit may only **tighten**
  thresholds, require **targeted fixes**, or **refer back** for a new human +
  ChatGPT ruling. It loosens nothing and authorises nothing.

## Statuses

- **Verdict:**
  **`M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_ACCEPTABLE_FOR_GATE3A_DATASET_EPOCH_ADOPTION`**
  — with **seven binding tightenings/requirements (T-1…T-7, §15/§16)** imposed
  on gates 3a/5/7. No PR #429 amendment is required: every finding is a
  tightening or a scheduling precision, consistent with Ruling 10.
- Carried: `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_PROPOSED` ·
  `POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION` ·
  `M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `M15_AUTHORISED`, `H1_AUTHORISED`,
`H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, or
`MEETS`; those tokens appear only in this prohibition list.

---

## 1. Executive verdict

- **Is the frozen contract acceptable for proceeding to gate 3a?** Yes —
  subject to T-1…T-7.
- **Too permissive / too strict / inconsistent / appropriately conservative?**
  Appropriately conservative overall. One genuine **leakage loophole** was
  found and is closed by tightening (T-1: dead-window feature warm-up); three
  precision gaps are pinned (T-2 EV payoff semantics, T-5 maxDD notional,
  T-7 no-overlap proof); one soft rule is hardened (T-3 ratio rule); several
  `[FIXED-AT design audit]` items are data-dependent and cannot be fixed by a
  no-read audit — they are re-pointed with mandatory human approval (T-6),
  which schedules rather than loosens.
- **Blockers before gate 3a?** None. **Blockers before implementation recorded
  now?** Yes — the T-list items bind gates 3a/5/7 (§15).
- **Does the design authorise nothing beyond the contract record?** Confirmed
  (§14).
- **Does it avoid turning M15 into an opportunistic search path?** Yes: one
  frozen horizon, three frozen `ev_min` values, frozen thresholds with a
  loosening prohibition, a validation-first kill gate, and the A-then-B
  program budget. The multiplicity surface is as small as a real experiment
  can be.

## 2. Audit scope

Read adversarially: the frozen contract (all 16 sections); the PR #428 audit
(rulings/conditions provenance); the PR #427 roadmap; PR #425/#426 as context
for the M1 failure modes the contract claims to escape. Verified by grep that
the contract contains the §16 ruling table and all 13 rulings inline. No raw
data, no derived data, no spreads, no labels, no metrics were touched.

## 3. Rulings 1–13 audit — ALL CORRECTLY INCORPORATED

Checked one by one against the contract text: (1) gate 3a deferred to the
named separate PR, artifact list complete ✓; (2) spans approved as
design-policy only, adoption withheld ✓; (3) `n_source_bars == 15`
eligibility, diagnostics-only incomplete buckets, no imputation ✓;
(4) session partition + 21:55–22:15 UTC rollover minimum, widen-only ✓;
(5) cost model frozen (median + 0.3 + 0.5; 2× + p90 stress; quote-cost-validity
scope) ✓; (6) label contract frozen (TP/SL mults + floors, hurdle, ratio
warning, horizon 24, SL-first, timeout MTM, class vocab, no searches) ✓;
(7) conservative feature table incl. M1-as-aggregation-input-only ✓;
(8) model + no-weighting + isotonic training-span-only calibration frozen ✓;
(9) EV set {0.0, 0.25, 0.5}, validation-only, smallest-passing tie, raw
probability threshold forbidden ✓; (10) kill gate + holdout table frozen with
the tighten-only clause ✓; (11) effective-N mandatory with frozen minimum
requirements ✓; (12) A-then-B budget + stopping rule ✓; (13) strengthened
no-legacy-evidence declaration ✓. **No ruling is missing, ambiguous, or
weakened.**

## 4. R-2a / R-2b audit — ONE LOOPHOLE FOUND AND CLOSED (T-1)

The explicit prohibitions are all present: design-only pre-holdout span, never
evidence, fixed PAIRS_20 (no inclusion/exclusion), dead window
2026-03-01→2026-04-24 excluded from design/validation/holdout/replication/
pair/session/threshold/feature/acceptance use.

**Adversarial loophole hunt — found:** the contract nowhere regulates
**feature warm-up at the start of the forward epoch**. Validation begins
2026-04-25; every lagged indicator (ATR14, EMAs, realised-vol windows, and
especially H1/H4 completed-bar context with long lookbacks) needs history. An
implementation that innocently "warms up" indicators from the bars immediately
preceding validation would read the **dead window** — dead-window prices would
enter validation features, violating R-2b through the back door. The same
channel could let dead-window bars leak via M15 aggregation context or spread
tables if spans were sloppily cut.

**T-1 (binding tightening):** dead-window data is **never loaded** for any
purpose. All indicators/context features initialise **only from forward-epoch
bars**; the first W bars of the forward epoch are a **warm-up burn-in** —
event-ineligible, used only to warm indicators — with `W ≥ the longest feature
lookback across all groups including H1/H4 context`, the exact W frozen at
implementation and verified at the source-contamination audit. Cost/spread
tables derive from the design span only (already required) with T-7's
ts-bound proof. With T-1 imposed, no consumed-window leakage path remains via
aggregation, H1/H4 context, warmups, spread tables, or the cost model.

## 5. Dataset / epoch plan audit — SOUND, with T-7 and a feasibility note

- **Deferring gate 3a to a separate PR: safe.** The contract adopts nothing,
  and the only real-read authorisation lives in gate 3a; the design-audit →
  adoption ordering matches the program pipeline.
- **Raw-data access before gate 3a:** structurally prevented — no artifact, no
  read; implementation is barred from reading/deriving until gate 3a
  completes (Ruling 1). Adequate.
- **Design span as design-only:** acceptable (R-2a compliant; never evidence).
- **Dead-window boundary:** conservative — it additionally buffers design from
  validation by ~8 weeks; with T-1 the boundary is airtight.
- **Forward epoch ≥ 2026-04-25:** acceptable; strictly later than the dead
  window.
- **Minimum spans (val ≥ 3 mo, holdout ≥ 2 mo):** adequate as minimums; NOT
  tightened (raising minimums would delay falsification without a leakage
  benefit) — but see the **feasibility note**: with turnover ≤ 40/day and
  ≥ 1,000 holdout trades, a 2-month holdout (~43 trading days) gives a
  feasible corridor of [1,000 … ~1,720] trades — intentionally demanding but
  narrow. **Gate 3a should prefer a holdout longer than the 2-month minimum
  when accrued data allows**; `INSUFFICIENT_SAMPLE` is the honest fallback,
  and adoption waits (already frozen).
- **Purge/embargo 25 M15 bars for horizon 24:** adequate at the
  validation/holdout boundary (labels cannot straddle). The design→validation
  boundary is additionally protected by the ~8-week dead window. With T-1,
  warm-up cannot bridge it either.
- **No-overlap proof:** **T-7 (binding):** the gate-3a artifacts must include
  an explicit machine-checkable no-overlap proof — per-file ts-bound
  assertions that design artifacts end ≤ 2026-02-28T23:59:59Z and forward-epoch
  artifacts begin ≥ 2026-04-25T00:00:00Z — committed as metadata.
- **`730d_BA` / `3650d_BA`:** clearly unauthorised in the contract ✓.

## 6. M15 aggregation audit — ADEQUATE against INV-1-class bugs, with T-7

All required elements are present and correct: UTC bucket-start; per-side
bid/ask OHLC (no mid construction); `n_source_bars == 15` eligibility;
diagnostics-only incomplete buckets; no imputation; no synthetic weekend bars;
gap report; pip authority; **value-pinned JPY + non-JPY tests** (the direct
INV-1 countermeasure); derivation identity + byte-reproducibility; committed
inventory/checksums.

Attacked risks: boundary off-by-one and weekend/rollover partial buckets are
neutralised by the `== 15` completeness rule (a boundary bug produces
incomplete buckets, which cannot become events — fail-safe by construction);
missing minutes likewise. Source-bucket leakage across the dead window and
warm-up crossings are closed by T-1/T-7. Dead-window-derived M15 bars cannot
enter any role: the derivation artifacts themselves must satisfy the T-7
ts-bounds, so such bars never exist in any adopted artifact. **No aggregation
policy change required.**

## 7. Cost model audit — ACCEPTABLE WITH TIGHTENING (T-6, T-7)

- **0.3 pip padding:** at the low end of honest for majors under normal
  conditions, and the claim is explicitly quote-cost-validity, with 2× stress
  (which doubles the padding too) covering model error. Acceptable as the
  primary; cannot be loosened; not raised (raising the *primary* would change
  a frozen value — the stress tests are the guard).
- **p90 vs p95/p99:** p90 + 2× is a reasonable dual stress; extreme quantiles
  are dominated by event/rollover spikes that are event-ineligible anyway.
  **Tightening (part of T-7): p95 session spread must additionally be
  *reported* as a diagnostic** (not a gate) so the tail is visible.
- **Double/undercount check:** the p90 stress substitutes the median term
  only (padding and cell unchanged) — coherent, no double count; the 2×
  stress scales the whole modelled cost — coherent.
- **Median as primary:** appropriate for a per-trade expectation model.
- **Where fixed:** the contract said `[FIXED-AT gate 3a or design audit]`.
  A no-read design audit cannot compute spread tables. **T-6 ruling: cost
  tables are fixed at gate 3a (or the implementation PR at latest), derived
  from design-span data only, committed as metadata, human-approved before
  any gate-7 authorisation.** Computing them is a real read and is therefore
  only permitted after the gate-3a design-data artifact exists.
- **Accidental validation/holdout use in cost tables:** blocked by T-7
  ts-bounds + the design-span-only derivation rule.
- **JPY/non-JPY scaling:** spreads are measured in price units and convert
  via `pip_size_for` — the audited single authority; the value-pinned tests
  extend to the spread path (§6). Correct.
- **Quote-cost validity vs paper/live:** explicit in the contract ✓.

**Ruling: acceptable with tightening** (p95 diagnostic; T-6 scheduling; T-7
proof). Not blocked.

## 8. Label contract audit — ACCEPTABLE with T-3 and T-4

- **Coherence of asymmetry + floors:** TP 1.5×ATR/floor 3×cost vs SL
  1.0×ATR/floor 2×cost preserves the 1.5:1 shape in both regimes (ATR-driven
  and floor-driven); coherent.
- **Horizon 24 vs barriers:** ~6 h for barriers ~1.5×ATR14(M15) is a
  reasonable pairing (M1's pathology was 20 *minutes*); whether timeouts still
  dominate is an empirical question the evidence schema must answer —
  **T-4 (binding): timeout share is mandatory evidence, and a holdout timeout
  share > 60% triggers a mandatory post-run-audit investigation before the
  result is cited for anything** (a defect-trigger, not a new acceptance
  gate — no untested criterion is added).
- **Ratio warning < 3.0 “reconsideration” too weak — YES.** **T-3 (binding
  hardening): if the median eligible barrier/cost ratio on design data is
  < 3.0, execution authorisation (gate 7) is BLOCKED pending a new human +
  ChatGPT ruling** — escalated from "design-audit reconsideration". M15 must
  demonstrably escape the M1 cost regime before anything runs.
- **Cost-hurdle strictness:** `1.5×ATR ≥ 2.0×cost` implies eligible TP
  distances ≥ 2×cost pre-floor and ≥ 3×cost post-floor — strict enough as a
  first contract; tightening further would be arbitrary without design data
  (which T-3 forces to be examined).
- **M1 failure-mode avoidance:** native M15, floors, hurdle, 18× longer
  horizon, EV gate — the four proven killers are each addressed. Confirmed
  materially different.
- Tie rule, timeout MTM, bid/ask geometry, class vocabulary, no-search
  clauses: carried from the triple-audited conventions ✓.

## 9. Feature policy audit — SUSTAINED, with one permitted narrowing noted

- Classifications are conservative and correctly gated. The
  **H1/H4-context-premature** attack: legitimate concern (longer lookbacks =
  bigger warm-up surface and alignment risk), but the group is already gated
  behind a dedicated alignment audit, and T-1 closes its dead-window channel.
  **Noted narrowing (permitted, tighten-direction): the first implementation
  MAY proceed native-M15-only if the H1/H4 alignment audit is not complete —
  dropping a feature group is always allowed; adding one is not.**
- Spread/cost-regime features as supporting-only: correctly fenced from
  becoming fitted alpha inputs without approval; target-leakage risk
  acknowledged and contained.
- v4-reuse vs replace: reuse-after-native-review is the right call — a
  rewrite would introduce a fresh un-audited surface for no informational
  gain.
- Completed-bar rules: stated for H1/H4 ("only completed upper bars, no
  peek"); the alignment audit verifies. Adequate.
- M1-derived features forbidden; consumed-window features forbidden; no
  holdout feature selection — all explicit ✓.

## 10. Model / calibration / EV-gate audit — ACCEPTABLE with T-2

- **Isotonic too data-hungry?** No — design/training spans contain millions of
  M15 rows across 20 pairs; isotonic's flexibility is affordable and the
  method is frozen (no search). Platt would be the fallback only via a new
  ruling; not needed.
- **Training-span-only calibration split:** correct and cheap (the split
  reduces training data marginally at these row counts).
- **No class weighting:** acceptable — frequencies are mandatory evidence,
  `INSUFFICIENT_SAMPLE`/invalid handling replaces post-hoc changes, and any
  weighting change requires a design amendment. The failure mode is honest,
  not hidden.
- **EV formula vs the timeout class — genuine imprecision found.** `EV_d =
  p̂_d×W̄ − (1−p̂_d)×L̄ − cost` treats the complement of the TP class as a
  single loss bucket, but realized complements include SL hits AND timeout
  MTM (which can be positive). Left unpinned, an implementation could choose
  W̄/L̄ definitions opportunistically. **T-2 (binding): the payoff estimates
  are pinned as — W̄(pair, session) = design-data mean traded-direction PnL
  conditional on the direction's TP class; L̄(pair, session) = design-data
  mean |traded-direction PnL| conditional on the complement (SL hits and
  timeouts, timeout MTM included, signed losses and gains netted within the
  complement). Estimated once on design data, frozen, recorded in evidence.**
  This keeps the frozen formula and removes its only degree of freedom.
- **W̄/L̄ stability across the design→forward regime gap:** a real risk
  (added as risk 13, §13) — mis-estimated payoffs shift EV operating points;
  the validation-only `ev_min` selection absorbs level error, and the kill
  gate catches the failure honestly. No change required.
- **`ev_min` set breadth:** three points spanning 0–0.5 pips is appropriately
  narrow; multiplicity is negligible and already budgeted.
- **Tie rule (smallest passing):** conservative — it prefers MORE trades at
  lower claimed edge, which strengthens the sample and weakens cherry-picking.
  Correct direction.
- **Does the EV gate actually prevent the M1 probability-threshold failure?**
  Structurally yes: it prices in per-pair/session cost and asymmetric
  payoffs, which the M1 rule ignored — and the kill gate ensures that if the
  EV signal is as empty as M1's probabilities were, the family dies at
  validation without holdout consumption.

## 11. Metrics / acceptance audit — FROZEN SET SUSTAINED; T-5; feasibility noted

- **Too loose?** No — jointly, net>0 + gross ≥1.5×cost + dual stress + Sharpe
  0.8 + DD 0.15 + turnover 40 + concentrations is a demanding conjunction; M1
  would have failed it at every line that matters.
- **Too strict / false-rejection risk?** The corridor between ≥1,000 trades
  and ≤40/day over a minimum 2-month holdout is the tightest spot (§5
  feasibility note; gate 3a should size the holdout generously). A false
  rejection into `INSUFFICIENT_SAMPLE` is recoverable by adopting more
  forward data — acceptable by design.
- **Turnover ≤40/day too high for M15?** As an upper bound it is fine (it is
  a budget, not a target); tightening it would shrink the trade-count
  corridor — rejected.
- **Timeout-share cap:** handled as the T-4 defect-trigger (not a new gate).
- **Concurrency/exposure caps frozen now?** Cannot be set honestly without
  design data; **T-6: caps fixed at implementation (from design data),
  human-approved before gate-7 authorisation** — recorded-in-evidence stays
  mandatory meanwhile.
- **maxDD notional — genuine gap: the contract never names the notional.**
  **T-5 (binding): the fixed notional is the M1 convention (10,000 pips)
  unless a new explicit human + ChatGPT ruling changes it; the value must be
  stated in the implementation contract and recorded in evidence.**
- **Effective-N method before gate 3a?** A no-read audit cannot fix a
  data-dependent estimator honestly. **T-6: the estimator is fixed IN the
  gate-3a PR** (which has the design-data context), satisfying the frozen
  minimum requirements, human-approved there.
- **Kill gate strong enough?** Yes — it requires positive net AND 1.5×-cost
  gross before any holdout touch; M1's entire history would have died there.
- **Stronger than 1.5× gross?** Not imposed — 1.5× plus dual stress is
  already conjunctive; raising it now would be numerology without data. The
  audit records that gate 8 (post-run) must scrutinise marginal passes.

## 12. Source reuse / no-legacy-evidence audit — SAFE

Reuse classifications match the program roadmap and PR #428; the pip
authority, scrubber, evidence discipline, and hard-gate executor are the
proven assets; helpers gated behind per-family audits. **Legacy influence
probe:** the only archived references in the contract ("small gross, fragile
net at multi-TF") appear as explicitly-marked non-evidence background and
justify *caution*, not thresholds — no number from fenced routes reaches
priors, thresholds, acceptance criteria, or selections. Removing the
references entirely was considered and rejected: they document why the
hypothesis is framed as a long shot, which is honest context. Boundaries are
precise enough for implementation (named modules, named gates). Not blocked.

## 13. Risk register audit — COMPLETE + ONE ADDITION

The 12 registered risks are each genuinely handled (not merely listed) — the
strongest entries are 9 (aggregation INV-1-class: checksummed derivation +
value-pinned dual-scale tests) and 11/12 (temptation + stopping rule).
**Addition — risk 13: W̄/L̄ payoff-estimate staleness across the
design→forward regime gap** (mitigation: T-2 pinned definitions; validation
kill gate absorbs level error; evidence records the frozen estimates for the
post-run audit to compare against realized payoffs).

## 14. Non-authorisation audit — CLEAN

The contract authorises nothing beyond its own record: no implementation,
training, execution, holdout evaluation, raw data access, metric computation,
or epoch adoption; no `730d_BA`/`3650d_BA`; no Phase C2; no H2/H3; no
paper/live; no production readiness; no selected-family run. The §3 span
policy is explicitly design-policy-only with adoption exclusively in gate 3a.
Nothing in the text reads as an authorisation beyond doc-only design.

## 15. Blockers

**Before gate 3a: NONE.** The T-list binds later gates:

| # | Binding tightening / requirement | Binds |
| --- | --- | --- |
| T-1 | Dead-window data never loaded; forward-epoch warm-up burn-in (first W bars event-ineligible; W ≥ longest feature lookback incl. H1/H4 context; W frozen at implementation; verified at source audit) | gates 3a/5/6 |
| T-2 | EV payoff semantics pinned: W̄ = design-data mean traded PnL given TP class; L̄ = design-data mean |traded PnL| given complement (SL + timeout MTM, netted); frozen once, recorded in evidence | gates 5/7 |
| T-3 | Median eligible barrier/cost ratio < 3.0 on design data → gate-7 execution authorisation BLOCKED pending a new human + ChatGPT ruling (hardened from "reconsideration") | gates 5→7 |
| T-4 | Timeout share mandatory evidence; holdout timeout share > 60% → mandatory post-run-audit investigation before any citation (defect-trigger, not a new acceptance gate) | gates 7/8 |
| T-5 | maxDD fixed notional = the M1 convention (10,000 pips) unless a new explicit ruling; stated in the implementation contract and evidence | gates 5/7 |
| T-6 | Data-dependent deferrals re-pointed with mandatory human approval: effective-N estimator → **gate 3a**; cost tables → **gate 3a or implementation PR** (design-span data only, before gate-7 authorisation); concurrency/exposure caps + holiday exclusion calendar → **implementation, approved before gate 7** | gates 3a/5/7 |
| T-7 | Gate-3a artifacts must include a machine-checkable **no-overlap proof** vs the dead window (design ≤ 2026-02-28T23:59:59Z; forward ≥ 2026-04-25T00:00:00Z, per-file ts-bounds) + **p95 session spread reported as diagnostic** alongside p90 | gate 3a |

Feasibility note (non-binding): gate 3a should prefer a holdout longer than
the 2-month minimum when accrued forward data allows, easing the
[≥1,000, ≤40/day] trade-count corridor; `INSUFFICIENT_SAMPLE` remains the
honest fallback.

## 16. Recommendation for next gate

**Proceed to the gate-3a dataset/epoch adoption PR**, incorporating T-1, T-6,
and T-7. **Exact allowed next PR shape:** doc-only (plus committed metadata
artifacts) gate-3a dataset/epoch adoption PR on branch
`docs/m15-gate3a-dataset-epoch-adoption`; **no implementation, no model
training, no validation/holdout computation, no metrics, no execution, no
`730d_BA`, no `3650d_BA`**; must produce/adopt: the design-data M15 derivation
artifact; the forward-epoch adoption artifact; inventory / checksums /
ts-bounds / derivation identity (incl. M1→M15 aggregation identity); the
**T-7 no-overlap proof against the dead window**; the cost-table derivation
plan or metadata (T-6); the **effective-N estimator** (T-6); and the retention
binding — all **metadata-only and scrub-clean**, each element human + ChatGPT
approved. Only after gate 3a: implementation (gate 5) under T-1…T-6, source
audit (gate 6), and a separately-authorised single run (gate 7, subject to
T-3).

**Non-authorisation:** this audit starts none of that. No implementation, no
training, no execution, no holdout evaluation, no raw data access, no epoch
adoption, no gate 3a, no H2/H3, no Phase C2, no paper/live, no production
readiness. Statuses as declared above.
