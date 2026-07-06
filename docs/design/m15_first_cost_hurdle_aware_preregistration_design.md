# Family A pre-registration design — M15-first cost-hurdle-aware trend/continuation

- **Document class:** doc-only selected-family pre-registration design (gate 3
  of the accepted Post-M1 research program). Not an implementation PR, not an
  execution PR. **Nothing is trained, read, derived, evaluated, or executed
  here.**
- **Branch:** `docs/m15-first-cost-aware-preregistration`
- **Base:** master `434e504632fa03d0e8b57d0a9646236b9507f1b2` (post PR #428 merge).
- **Governing records:** PR #427 roadmap (gate 1) + PR #428 adversarial audit
  (gate 2, `POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION`),
  whose rulings **R-2a / R-2b** and binding conditions **C-1…C-8** are
  incorporated below.

## Statuses

- **`M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_PROPOSED`**
- Carried: `POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION`
  · `M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `M15_AUTHORISED`, `H1_AUTHORISED`,
`H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, or
`MEETS`; those tokens appear only in this prohibition list.

Numeric-value convention: every number marked **[CANDIDATE]** is a
pre-registration candidate requiring explicit human + ChatGPT approval before
this PR merges; numbers marked **[FIXED-AT]** name the later gate where they
are frozen. Nothing in this document is a final threshold unless the merge
approval explicitly freezes it.

---

## 1. Executive thesis

**Hypothesis under test (not an expectation):** at the M15 timeframe, a
cost-hurdle-aware trend/continuation classifier over the fixed PAIRS_20
universe can select trades whose **net expectancy under an empirical
per-pair/session cost model is positive**, at a portfolio turnover within a
pre-registered budget.

- **Why M15 first:** the valid M1 failure (PR #425/#426) localised to
  short-horizon economics — barriers a few pips wide with embedded spread
  consuming them, ~20-minute timeouts, 168 trades/day — and to feature
  information content. M15 attacks the economics directly: ATR-proportional
  barriers several times wider at unchanged spread, event rate ~15× lower,
  label noise reduced, while data and tooling exist today (fastest valid
  falsification — the PR #428-sustained ranking).
- **Why this is NOT a continuation of the failed M1 lineage:** different
  native timeframe, different label geometry (spread-floored barriers +
  eligibility hurdle), different decision rule (calibrated EV gate, not a raw
  class-probability threshold), different acceptance frame (cost-relative
  floors, validation-first), and — decisively — **no design input from the
  consumed holdout** (R-2b). The only shared elements are audited
  infrastructure and conventions (per-pair pip authority, evidence
  discipline).
- **Why falsifiable, and cheaply:** the family carries a **validation-first
  kill gate**: if validation net expectancy under the empirical cost model
  fails the §9 floor at every registered operating point, the family is
  **closed without consuming any holdout**. A clean negative is a valid,
  useful outcome; the design optimises for decision speed, not for rescue.
- **What closes the family before any holdout touch:** failing the validation
  floor (§9.V) at all registered EV-gate operating points; or
  `INSUFFICIENT_SAMPLE` on effective-N grounds that cannot be remedied by the
  registered data plan; or a design-audit/source-audit finding of a
  contract-level defect.

## 2. Closed prior constraints (binding)

M1 flagship **closed** (`M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`);
corrected PR #425 evidence **valid `DOES_NOT_MEET`** (expectancy −3.49
pips/trade at 0.5 cell; gross −2.99; 20/20 pairs negative; no validation edge);
PR #426 accepted the closure and diagnosis; PR #427 proposed the successor
program; PR #428 accepted it with rulings R-2a/R-2b and conditions C-1…C-8.
The `365d_BA` M1 frozen holdout is **consumed**; the calendar window
**2026-03-01 → 2026-04-24 is dead for all roles at all timeframes** (§3);
same-data M1 flagship retry is **forbidden**; general M1 is admissible only
under a materially new microstructure-grade hypothesis and separate protocol.

## 3. Dataset and epoch plan (C-1 — merge-blocking until approved)

### 3.1 Roles and spans (proposal — gate 3a subject matter)

| Role | Span (UTC) | Source | Status |
| --- | --- | --- | --- |
| **Design (exploratory)** | 2025-04-25 → **2026-02-28** | M15 aggregate of the adopted `365d_BA` epoch's pre-holdout span (R-2a) | usable only after the §4 derivation artifact exists; results never citable as evidence |
| **DEAD window** | **2026-03-01 → 2026-04-24** | — | excluded from every role at every timeframe (R-2b) |
| **Validation** | 2026-04-25 → T_v | **new forward epoch** (separately adopted; gate 3a) | not yet adopted |
| **Frozen holdout** | T_v (+embargo) → T_h | same new forward epoch | not yet adopted; one-shot |
| **Disjoint replication** | a further, later or separately adopted span | future decision | required before any production-grade claim |

T_v / T_h (the validation/holdout boundary and end) are **[FIXED-AT gate 3a]**
when the forward epoch is adopted, with minimum spans: validation ≥ 3 months
and holdout ≥ 2 months **[CANDIDATE]**; if insufficient forward data has
accrued at adoption time, adoption waits — the verdict `INSUFFICIENT_SAMPLE`
exists precisely so that impatience cannot shrink the holdout.

### 3.2 Rules

- **Chronological ordering:** design < (dead window) < validation < holdout <
  replication. The dead window sits between design and validation, providing a
  natural ≥ 1-month buffer in addition to formal purge.
- **Purge/embargo:** ≥ horizon + 1 M15 bars at every role boundary
  **[FIXED-AT gate 3 merge, with the horizon]**.
- **Holdout consumption:** the frozen holdout is consumed at its single
  authorised evaluation, or upon any decision-bearing observation of it
  (including via an invalid run).
- **Invalid-run rule:** the #422→#425 ceremony verbatim — prove the
  invalidator from committed evidence; code-only fix; adversarial re-check;
  a corrected re-measurement only by explicit separate approval and only if
  no feedback loop occurred; otherwise holdout forfeiture.
- **R-2a compliance:** pair universe fixed at **PAIRS_20** (the 20 inventory
  pairs — no inclusion/exclusion decisions anywhere in this family); design
  results never citable as evidence; validation/holdout strictly later than
  and disjoint from the design span. **R-2b compliance:** the dead window
  appears in no role above and is banned from design/validation/holdout/
  replication/pair/session/threshold/feature/acceptance use.
- **Gate 3a placement:** this section **is the severable gate-3a proposal**.
  Two artifacts are distinguished: (i) the **design-data derivation artifact**
  (M15 aggregate of the already-adopted pre-holdout span — §4) and (ii) the
  **forward-epoch adoption artifact** (new raw data; full Gate-P2-style
  adoption). **This PR must remain unmerged until the human + ChatGPT
  decision either approves this §3 plan (with §3.1 spans resolved or
  explicitly deferred to a named separate gate-3a PR) or supersedes it.**
- **Explicit non-authorisations:** no `730d_BA`; no `3650d_BA`; no epoch
  adopted by this document; no raw data read in this PR.

## 4. M15 aggregation and derived-dataset policy (C-2)

The design-data M15 aggregate is a **new derived dataset** and requires a
Gate-P2-style adoption artifact **before any real read**. Required contract
(specified now; produced later, at gate 3a / implementation):

- **Input identity:** the 20 committed `365d_BA` M1 BA files, named by the
  PR-B.1 inventory (filename + SHA-256 + size), restricted to the design span.
- **Output identity:** 20 M15 BA files with their own inventory (filename,
  SHA-256, size, `ts_min_utc`/`ts_max_utc`, row count) committed as the
  adoption artifact.
- **Boundary convention:** bars bucketed by floor(timestamp / 15 min) on the
  **UTC** clock; bar timestamp = bucket start. No DST logic (UTC only).
- **Bid/ask OHLC aggregation:** per side (bid, ask): open = first M1 open in
  bucket; close = last M1 close; high = max of M1 highs; low = min of M1 lows.
  No mid-price construction at aggregation time.
- **Partial-bar policy:** buckets containing fewer than 15 M1 bars are kept
  with a recorded `n_source_bars` field; buckets with `n_source_bars <` a
  floor **[CANDIDATE: 5]** are marked incomplete and excluded from event
  eligibility (not from context/features' history).
- **Missing-minute policy:** absent M1 minutes are simply absent (no
  imputation); a per-file gap report (count + max gap) is part of the
  artifact.
- **Weekend/rollover/holiday:** no synthetic bars across market close; buckets
  spanning the weekend boundary are terminated at close; the session/rollover
  exclusion windows for *event eligibility* are defined in §5/§6, not by
  deleting data.
- **Spread computation:** per-bar quoted spread = `ask_c − bid_c` (plus
  open-side variant recorded); this is the raw material of the §5 cost model.
- **Per-pair pip-size mapping:** `pip_size_for` (0.01 iff `*_JPY` else 0.0001)
  carried forward verbatim as the sole conversion authority; the derived
  inventory records the mapping.
- **Derivation identity:** the aggregation script's path + git SHA + its own
  config hash recorded in the artifact; re-running it must be byte-reproducible
  from the same inputs.
- **Required tests before any real read (INV-1 lesson):** value-pinned
  aggregation tests on synthetic JPY-scale AND non-JPY-scale inputs (exact
  expected OHLC/spread/pip outputs); boundary tests (bucket edges, weekend,
  gaps); checksum round-trip test.
- **Not done in this PR:** no aggregation is implemented or executed here.

## 5. Cost model and spread policy (C-4 prerequisite)

- **Per-pair, session-aware empirical spread model:** from design-span M15
  quoted spreads, per pair × session (3 sessions **[CANDIDATE]**: Asia
  00:00–07:59, Europe 08:00–15:59, US 16:00–23:59 UTC), estimate the median
  and p90 quoted spread. These estimates are **frozen from design data** and
  recorded (values + method) in the contract at implementation time
  **[FIXED-AT design audit]**.
- **All-in modelled cost per trade:** `cost(pair, session) =
  median_spread(pair, session) + pad_exec + cell_slippage`, where `pad_exec`
  is a quote-vs-fill execution padding **[CANDIDATE: 0.3 pip]** and
  `cell_slippage` the flat slippage cell **[CANDIDATE: 0.5 pip primary]**.
  Claims are explicitly **quote-cost-validity** claims; the padding
  acknowledges (not eliminates) the executable-fill gap.
- **Stress tests (both mandatory):** (i) **2× stress** — all metrics
  recomputed at `2 × cost(pair, session)`; (ii) **p90 stress** — recomputed
  with p90 session spread substituted for the median. Acceptance requires
  survival per §9.
- **Weekend/rollover/holiday:** rollover windows (21:55–22:15 UTC
  **[CANDIDATE]**) and low-liquidity holiday sessions are event-ineligible
  (cost there is unmodelled, so no trade may be scored there); the exclusion
  windows are frozen at design audit from design data.
- **Admissibility requirements:** the cost model is admissible only if the
  spread estimates derive from the checksummed derived dataset (§4), the
  estimation script identity is recorded, and per-pair/session tables are
  committed as metadata (no raw rows).
- **Evidence requirements:** every future run's evidence records the full cost
  table used, the padding, the stress results, and
  `global_pip_size_authoritative_for_all_pairs = false` with the per-pair map.
- **Not done in this PR:** no spreads are computed here.

## 6. Label design (C-3/C-4)

- **Geometry (bid/ask-aware, B-2 heritage):** long enters next-bar ask, exits
  on bid; short mirrored; SL-first same-bar tie; timeout scored at
  horizon-end mark-to-market on the exit side. (These conventions survived
  three audits; they are carried, not re-derived.)
- **Spread-floored barriers:** `TP_dist = max(tp_mult × ATR14_M15,
  f_tp × cost(pair, session))`, `SL_dist = max(sl_mult × ATR14_M15,
  f_sl × cost(pair, session))`, with `tp_mult = 1.5`, `sl_mult = 1.0`
  **[CANDIDATE — carried from the audited convention]** and floors
  `f_tp = 3.0`, `f_sl = 2.0` **[CANDIDATE]**.
- **Cost-hurdle eligibility:** a bar is an eligible event only if
  `tp_mult × ATR14_M15 ≥ h_min × cost(pair, session)` with `h_min = 2.0`
  **[CANDIDATE]** — bars whose attainable move cannot plausibly clear cost
  are never labeled, trained on, or traded. This is the family's defining
  condition.
- **Barrier/spread ratio requirement (C-3):** before implementation, the
  actual distribution of `barrier_distance / cost` on design data must be
  derived and recorded; if the median eligible ratio is < 3 **[CANDIDATE]**,
  the parameters (or the family) must be reconsidered at the design audit —
  M15 must demonstrably escape the M1 cost regime, not just claim to.
- **Horizon candidates:** {16, 24, 32} M15 bars (4–8 hours) **[CANDIDATE
  set]**; exactly ONE value is frozen at gate-3-merge approval — horizon is
  **not** a searchable parameter.
- **Class vocabulary:** {−1, 0, +1} (short/timeout/long), unchanged.
- **No drift:** identical label code path for training, validation, and
  holdout; no label parameter may change after validation is first computed;
  no threshold or label search after validation.
- **Material differences from the failed M1 setup:** native M15 bars; spread
  floors; eligibility hurdle; 4–8 h horizon (vs 20 min); EV-gated decisions
  (§8) instead of raw probability cutoffs; per-pair session cost inside the
  label economics.
- **Not done in this PR:** no labels implemented.

## 7. Feature policy

| Feature group | Classification |
| --- | --- |
| Native M15 OHLC technical base (v4-style, recomputed at M15) | **allowed only after audit** (native-M15 review, C-3; warmups/windows revalidated) |
| H1/H4 completed-bar context features | **allowed only after audit** (alignment audit: only completed upper bars, no peek) |
| Session/time-of-day encodings | **allowed now** (deterministic calendar arithmetic; frozen set) |
| Realised-volatility features (from M15 history) | **allowed only after audit** |
| Spread/cost-regime features (from design-frozen cost tables) | **supporting-only** (may gate eligibility; must not become a fitted alpha input without design-audit approval) |
| Calendar/economic-event features | **deferred** (blocked pending point-in-time provenance — PR #428 ruling) |
| Carry/macro features | **deferred** (no data source) |
| Microstructure/tick features | **deferred** (family F prerequisite) |
| M1-derived features (any) | **forbidden** — no M1 microstructure proxying from OHLC M1; M1 exists in this family only as aggregation input |

Cross-cutting prohibitions: no consumed-window-derived features (R-2b); no
feature selection on any holdout; no legacy-route feature evidence (C-8); the
final feature list is frozen at the design audit and hashed into the contract.

## 8. Model and decision policy

- **Baseline model family:** LightGBM 3-class classifier — retained
  deliberately: the model family was not the proven M1 failure mode, and
  changing it would confound the timeframe/cost-economics test. Params carry
  the audited convention (`learning_rate 0.05, num_leaves 31, verbose −1,
  n_estimators 200`) **[CANDIDATE — re-frozen at gate-3 merge]**; from-scratch
  training; no deployed-model reuse; no model-family search; no post-result
  model changes.
- **Class imbalance:** class frequencies are a mandatory evidence item (§9);
  handling (none vs class-weight) is fixed at the design audit **[FIXED-AT
  design audit]** — not searched.
- **Probability calibration (C-4):** probabilities are calibrated before EV
  computation, using a calibration split **carved from the training span
  only** (never validation/holdout). Method candidate: isotonic regression
  **[CANDIDATE; FIXED-AT gate-3 merge]**.
- **EV-gate mechanism (C-4 — the decision rule):** for each eligible bar and
  direction d ∈ {long, short}:
  `EV_d = p̂_d × W̄(pair, session) − (1 − p̂_d) × L̄(pair, session) −
  cost(pair, session)`, where p̂ is the calibrated probability of the
  direction's barrier class and W̄/L̄ are expected win/loss magnitudes in pips
  **estimated on design data and frozen** (never re-fit on validation/
  holdout). Trade direction d iff `EV_d ≥ ev_min` and `EV_d > EV_{−d}`.
  **A raw probability threshold alone is explicitly not a permitted decision
  rule.**
- **Operating-point selection:** `ev_min` is chosen on **validation only**
  from a pre-registered candidate set {0.0, 0.25, 0.5} pips **[CANDIDATE
  set]**, tie rule: smallest passing candidate; selection metric: validation
  net expectancy subject to the turnover budget. Holdout is evaluated once,
  after selection, at the selected operating point only.
- **Seed policy:** any RNG actually used is recorded in the manifest; if the
  trainer convention defines none, that is recorded honestly (M1 precedent);
  reproducibility level declared (`bounded_not_bitwise_guaranteed`).
- **Not done in this PR:** no training.

## 9. Metrics and acceptance criteria (all thresholds [CANDIDATE] pending merge approval)

**V. Validation kill gate (evaluated before any holdout touch):** validation
net expectancy under the empirical cost model > 0 **AND** validation gross
expectancy ≥ k × modelled all-in cost with **k = 1.5 [CANDIDATE]**, at at
least one registered `ev_min` operating point, within the turnover budget.
Fail at all points → **family closed, no holdout consumed**.

**H. Holdout acceptance (single evaluation, selected operating point):**

| Criterion | Candidate threshold |
| --- | --- |
| net expectancy (empirical cost) | > 0 |
| gross expectancy vs cost | ≥ 1.5 × all-in cost |
| stressed-cost survival | net expectancy ≥ 0 at 2× cost AND at p90 session spread |
| daily portfolio Sharpe (ann., UTC-day) | ≥ 0.8 (metric definition frozen; number [CANDIDATE]) |
| max equity drawdown (vs fixed notional) | ≤ 0.15 |
| trade count lower bound | ≥ 1,000 holdout trades AND effective-N ≥ 400 (§ below), else `INSUFFICIENT_SAMPLE` |
| daily coverage | ≥ 0.60 |
| turnover upper bound | ≤ 40 trades/day portfolio-wide |
| pair trade concentration | ≤ 0.40 |
| pair positive-PnL concentration | ≤ 0.50 |
| class-frequency sanity | recorded; no gate, defect trigger only |
| concurrency/exposure | max concurrent positions and per-currency net exposure recorded; caps [FIXED-AT design audit] |

**Mandatory evidence schema (C-5):** exit-type counts (TP/SL/timeout),
timeout share, gross/net layer decomposition, class frequencies, concurrency
metrics, per-currency exposure, full cost-model metadata, EV-gate metadata
(candidates, selected, rejected-with-metrics), calibration metadata
(method + fit-span), effective-N estimate, per-pair pip map + convention +
`global…= false`.

**Effective-N (C-6):** raw event counts overstate independence under
overlapping horizons and cross-pair dependence. Draft estimator: block-adjust
by horizon (events per pair thinned by mean overlap factor ≈ horizon/mean
inter-event gap) and discount cross-pair by an average-correlation factor
estimated on design data; method **[FIXED-AT design audit]**; the estimate
appears in evidence and gates the trade-count criterion. Daily-aggregation
dependence: Sharpe is computed on UTC-day portfolio sums (as in M1),
acknowledged as correlated across pairs — the per-currency exposure metric is
the monitoring instrument. `INSUFFICIENT_SAMPLE` triggers whenever the
effective-N or trade-count floor fails at any stage — validation or holdout,
M15 included.

**Disjoint replication:** required before any production-grade claim; not
part of this family's acceptance.

## 10. Execution protocol (gates for this family — none skippable)

1. **This pre-registration design PR** (gate 3) — merge blocked until §3
   (C-1) is approved and all [CANDIDATE] values are approved or amended.
2. **Fable 5 design audit PR** (gate 4).
3. **Gate 3a dataset/epoch artifacts** — design-data derivation artifact (§4)
   and forward-epoch adoption artifact (§3.1), if not already approved as the
   severable §3 of this PR; each requires human + ChatGPT approval.
4. **Code-only implementation PR(s)** (gate 5) — fixture-tested; value-pinned
   JPY/non-JPY tests on every conversion/aggregation path; no real run.
5. **Source-contamination audit PR** (gate 6).
6. **Single-run execution PR** (gate 7) — validation kill gate first; holdout
   once only if it passes; metadata-only scrub-clean evidence.
7. **Post-run audit PR** (gate 8).
8. **Disjoint replication decision** (gate 9).
9. **Paper/live gates** (gate 10) — separate approval track; never implied.

## 11. Source reuse / non-reuse declaration

- **Reusable as governance/evidence patterns:** ml_step4 manifest / evidence /
  acceptance / diagnostics discipline; checksum + inventory tooling; scrubber;
  protected-evidence guard; ordered hard-gate executor; **per-pair pip-size
  authority (`data_adapter.pip_size_for`) carried forward verbatim**.
- **Reusable after audit/wrapping:** feature builders (native-M15 review
  required), label helpers (`labels.py` B-2 machinery — parameterised floors/
  horizon), PnL helper (`traded_direction_pnl_price`, F-2-corrected), metric
  helpers (extended per C-5).
- **Historical-only:** all M1 flagship evidence (both directories); archived
  stage/compare logs; Phase 9.x numerics per the standing tier
  classifications.
- **Forbidden:** optimistic legacy PnL routes; deployed-model machinery in
  evidence paths; invalid backtest routes; anything reading the consumed
  window for design/tuning.
- **Live/paper runners:** engineering assets for the separate production
  gates; never research evidence.

**C-8 no-legacy-evidence declaration:** no number from the fenced legacy
routes (archived Phase 9.x numerics, pre-F-2 PnL outputs, halted tabular
evidence, stage/compare logs) enters this family's design justification,
priors, thresholds, acceptance criteria, pair selection, session selection,
feature selection, or evidence claims. Where archived context is referenced
(e.g. "small gross, fragile net at multi-TF"), it is cited as non-evidence
background only and decides nothing.

## 12. Risk register

| # | Risk | Handling in this design |
| --- | --- | --- |
| 1 | Overlapping-label effective-N | §9 effective-N gate; horizon frozen; events thinned in the estimator |
| 2 | Cross-pair dependence | fixed PAIRS_20 (no selection); per-currency exposure metric; correlation discount in effective-N |
| 3 | Non-stationarity | claim scoped to the evaluated spans; disjoint replication required for stronger claims |
| 4 | Quote-vs-fill gap | execution padding in the cost model; dual stress tests; quote-cost-validity claim scope |
| 5 | Weekend/rollover/holiday | event-ineligibility windows frozen at design audit; aggregation policy §4 |
| 6 | Class imbalance | mandatory class-frequency evidence; handling fixed at design audit, not searched |
| 7 | Probability calibration | training-span-only calibration split; method frozen pre-run |
| 8 | Concurrency/exposure aggregation | simulator must define overlapping-position accounting; concurrency metrics mandatory |
| 9 | M1→M15 aggregation alignment (INV-1-class) | checksummed derivation artifact; value-pinned JPY/non-JPY tests; gate-6 audit |
| 10 | Multiple-comparison budget | C-7: families A then B only; small pre-registered candidate sets (one horizon, three ev_min) |
| 11 | Operator search temptation | validation kill gate closes the family without a holdout touch; every negative closes its question; consumed data dead |
| 12 | Stopping-rule discipline | if A fails validation → B (own contracts, H1/H4 split); if B fails → mandatory program-level review; no family C without a new roadmap arc |

## 13. Blockers and open questions

**Must resolve before this PR merges (C-1):**
- The §3 dataset/epoch plan (spans, minimums, forward-epoch commitment) —
  approve, amend, or defer to a named separate gate-3a PR.
- Every **[CANDIDATE]** value (horizon; tp/sl mults; floors f_tp/f_sl; hurdle
  h_min; k; ev_min set; session partition; padding; minimum spans; acceptance
  numbers) — approve or amend as the frozen contract, or explicitly mark
  which remain [FIXED-AT design audit].

**Must resolve before implementation (gates 4–5):**
- Forward-epoch adoption artifact (gate 3a) and design-data derivation
  artifact (§4) produced and approved.
- Barrier/spread ratio derivation from design data (§6, C-3).
- Empirical spread tables + padding validation (§5).
- Native-M15 feature-builder review (§7).
- Effective-N estimator method; class-imbalance handling; concurrency caps;
  rollover/holiday exclusion windows.

**Must resolve before execution (gates 6–7):**
- Source-contamination audit; evidence-schema implementation (C-5); scrubber
  coverage of the new payload fields.

**Before any production claim:** disjoint replication (gate 9) + separate
paper/live gates (gate 10).

## 14. Non-authorisation statements

This document authorises **nothing**: no implementation; no training; no
execution; no holdout evaluation; no raw data access; no metric computation;
no epoch adoption (the §3 plan is a proposal pending C-1 approval; the
forward epoch is not adopted by this text); no `730d_BA`; no `3650d_BA`; no
Phase C2; no H2/H3; no paper/live trading; no production readiness; no
selected-family run. The consumed `365d_BA` holdout and the dead window
2026-03-01 → 2026-04-24 remain quarantined. Statuses:
`M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_PROPOSED`,
`NO_EXECUTION_PERFORMED`, `PRODUCTION_READINESS_NOT_CLAIMED`.

## 15. Recommendation for next gate

1. Human + ChatGPT review this pre-registration: rule on §3 (C-1) and on every
   [CANDIDATE]; merge only with those rulings recorded (in the approval
   message or an amended revision).
2. Then the **Fable 5 design audit PR** (gate 4) attacks the frozen contract.
3. Then gate 3a artifacts (if deferred), implementation (gate 5), source audit
   (gate 6) — in order, each separately approved.
4. Nothing runs until gate 7 is separately authorised with its own one-shot
   discipline.
