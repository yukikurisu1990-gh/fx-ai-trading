# Post-M1 research program roadmap (Fable 5)

- **Document class:** doc-only research-program design memo. Not an
  implementation PR, not an execution PR, not a pre-registration for any
  specific strategy family. Designs the research sequence and governance after
  the valid M1 flagship failure; executes and authorises nothing.
- **Branch:** `docs/post-m1-research-program-roadmap`
- **Base:** master `5f10088e668e9e1f39f894c3e56f01b71271fa61` (post PR #426 merge).
- **Related records:** PR #413 trading-logic/profitability audit; PR #407
  pre-registration; PRs #421–#426 (the closed M1 arc); Gate P1/P2 protocols;
  `research_development_roadmap_post_audit.md` (binding tier classifications —
  unamended by this document).

## Statuses

- **`POST_M1_RESEARCH_PROGRAM_ROADMAP_PROPOSED`**
- Carried prior: **`M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`**
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `M15_AUTHORISED`, `H2_STARTED`,
`PHASE_C2_STARTED`, or `NEW_EPOCH_ADOPTED`; those tokens appear only in this
prohibition list.

---

## 1. Executive summary

The M1 flagship question is closed on valid evidence: the pre-registered
LightGBM/B-2/M1 family loses money **before** cost, at every threshold, on all
20 pairs, in validation and holdout alike. The failure is informative, not
merely negative — it localises the problem to **short-horizon economics**
(spread-inclusive barriers, 20-minute timeouts, 168 trades/day) and
**information content** (lagged OHLC technicals cannot resolve M1 direction),
not to governance, data integrity, or evaluation machinery, all of which
survived two adversarial audits intact.

This roadmap proposes the next research program: a ranked family sequence
(**A: M15-first cost-hurdle-aware family** first, **B: H1/H4 swing family**
second, C/D as supporting layers, E/F deferred, G prerequisite-gated,
H forbidden as standalone), a ten-gate governance pipeline reusing the ML Step 4
discipline, a dataset/epoch strategy that quarantines the consumed `365d_BA`
holdout, and a draft acceptance philosophy centred on cost-aware expectancy
with turnover budgets and disjoint replication. **Nothing is implemented,
trained, evaluated, or authorised here.**

## 2. Closed prior: M1 flagship result

**Arc (all merged):** PR #421 first-run executed once (`DOES_NOT_MEET`) →
PR #422 Fable 5 post-audit **invalidated** it (fixed `PIP_SIZE = 0.0001`
applied to all 20 pairs; the six JPY crosses require `0.01`; JPY PnL ~100×
inflated) → PR #423 code-only per-pair pip-size fix → PR #424 Fable 5 re-check
(acceptable) → PR #425 governance-approved corrected re-measurement, executed
exactly once (`ML_STEP4_365D_BA_CORRECTED_SECOND_RUN_COMPLETED`) → PR #426
post-run audit + diagnosis: **evidence VALID**, outcome **`DOES_NOT_MEET`**,
**M1 flagship lineage CLOSED**, **`365d_BA` holdout CONSUMED**. No rerun, no
tuning, no same-lineage iteration on `365d_BA` — ever.

**What failed (from the committed PR #426 diagnosis):**

| Failure | Evidence |
| --- | --- |
| Negative **gross** edge | −2.99 pips/trade at the 0.0 cell — losing before the flat cost; not "cost killed a small edge" |
| High turnover | 168.4 trades/day (4.2× the 40/day gate); thresholds barely modulate volume |
| Win rate far below breakeven | 7.83% actual vs ~40.4% required at payoff 1.47 |
| Spread-inclusive M1 barrier economics | ATR14-on-M1 barriers are a few pips; embedded spread consumes a large fraction of every trade |
| 20-bar timeout behaviour | ~20-minute horizon → timeout MTM dominates when barriers are not hit; wrong-side timeouts accrue |
| Feature information deficit | lagged OHLC technicals + completed upper-TF aggregates carry no microstructure information at M1 |
| Probability threshold ≠ EV threshold | raw class-probability cutoffs ignore asymmetric per-class payoffs and cost; no positive-EV region existed at any registered threshold |
| Broad-based failure | 20/20 pairs negative; both concentration gates passed — no single-pair pathology to excise |

**What did NOT fail:** the governance chain (pre-registration → gates →
one-shot → post-audit) caught a real 100× unit bug, forced an honest
invalidation, and produced a clean corrected measurement. The evidence,
checksum, scrubber, and acceptance machinery are proven assets.

## 3. Research governance going forward (mandatory)

Every new research family MUST proceed through, in order:

1. **Doc-only research thesis** — hypothesis, edge source, falsification
   criteria, data plan; no code.
2. **Fable 5 adversarial design audit** — before any implementation.
3. **Code-only implementation PR(s)** — synthetic/fixture-tested; no real run;
   no real data reads beyond committed metadata.
4. **Source-contamination audit** — before any real run (the PR #418-style
   full-source pass; catches optimistic PnL routes, leakage, unit bugs — the
   class of defect that invalidated PR #421).
5. **Single-run execution PR** — pre-stated gates, one shot, metadata-only
   scrub-clean evidence, explicit stop-before-training on any gate failure.
6. **Post-run audit** — adversarial, before the result is cited for anything.
7. **No rerun-into-search** — a failed run closes the registered question; it
   never becomes an iteration loop on the same holdout.
8. **No tuning on any consumed holdout** — consumed holdouts are permanently
   quarantined from design, tuning, pair/session/threshold/feature selection.
9. **No production claim without disjoint replication** — a second,
   independently frozen epoch must reproduce the result before any
   stronger-than-research claim.
10. **Paper/live trading only behind separate gates** — research acceptance
    never implies paper/live authorisation (Production P1–P3 remain separate).

Invalid runs follow the PR #422→#425 precedent: prove the invalidator from
committed evidence; fix code-only; adversarially re-check; then a separately
authorised corrected re-measurement MAY be admissible if (and only if) no
feedback loop occurred — a governance decision each time, never a default.

## 4. Candidate research families

### A. M15-first cost-hurdle-aware trend/continuation family

- **Rationale:** directly repairs the two proven killers — cost fraction and
  turnover — while staying inside data and tooling we already have. At M15,
  ATR-proportional barriers are ~4–8× wider than M1 while spread is unchanged,
  so the embedded-cost fraction per trade drops several-fold; the event rate
  drops ~15× by construction.
- **Expected edge source:** short-horizon continuation/trend persistence at
  15-minute resolution, monetisable only where the expected move clears an
  explicit cost hurdle — the PR #413 cost-hurdle finding made into the label.
- **Data requirements:** M15 BA candles (available: the preserved OANDA archive
  spans M1…D for 20 pairs; the `365d_BA` M1 files can also be aggregated to
  M15 deterministically). Empirical spread distributions derivable from BA
  bid/ask columns. No new external data.
- **Cost sensitivity:** materially lower than M1; still the first-order design
  constraint — hence spread-floored barriers (TP/SL distances ≥ k×empirical
  spread) and per-pair/session cost cells.
- **Turnover profile:** target a pre-registered budget (portfolio-wide
  ~10–40 trades/day ceiling), enforced by construction (event definition +
  abstention), not post-hoc filtering.
- **Label requirements:** cost-aware B-2-style bid/ask triple-barrier with
  spread-floored distances; longer horizon (e.g. 16–32 M15 bars — draft, to be
  fixed at pre-registration); per-pair pip/spread normalisation from day one
  (the INV-1 lesson institutionalised).
- **Feature requirements:** v4-base as baseline; candidate extensions
  (realized-spread/vol features, session encodings) pre-registered, evaluated
  on design data only.
- **Risks:** M15 momentum may be as edge-free as M1 post-cost (the honest
  prior from the archived Phase 9.X record is "small positive gross, fragile
  net"); aggregation bugs (mitigated by the source-contamination gate);
  fewer events → wider confidence intervals (mitigated by 20-pair pooling).
- **Falsification criteria (draft):** if validation net expectancy under the
  empirical cost model is ≤ 0 (or below a pre-registered floor, e.g.
  +0.5 pips/trade) at every registered operating point, the family fails
  **without touching any holdout** — validation-first gating is the core
  protocol improvement.

### B. H1/H4 swing family

- **Rationale:** the cost-to-signal ratio improves a further ~4–16× over M15;
  spread becomes almost negligible relative to barrier distances; turnover is
  intrinsically tiny.
- **Expected edge source:** multi-hour/multi-day trend persistence and
  vol-adjusted continuation — the regime where the archived record (stage
  8/10/13 H1 experiments) showed the least-negative to mildly-positive
  behaviour.
- **Cost sensitivity:** lowest of any candidate; a strategy that fails here
  post-cost has essentially no edge at all.
- **Lower turnover advantage:** a handful of trades/day portfolio-wide;
  turnover and capacity gates pass by construction.
- **Reduced sample-size risk — inverted:** the *opposite* risk dominates: a
  365-day span yields few independent H4 events per pair; statistical power is
  the binding constraint. Requires longer design spans (multi-year) and pooled
  cross-pair evaluation; acceptance needs a trade-count lower bound.
- **Label requirements:** triple-barrier or return-horizon labels at H1/H4 with
  cost floors (cheap here); possibly direct EV regression.
- **Feature requirements:** upper-TF technicals become genuinely informative at
  their native scale; carry/session/cross-sectional strength candidates.
- **Risks:** low event count → slow falsification and wide CIs; overlapping
  multi-bar exposures complicate portfolio accounting; regime dependence over
  long spans.
- **Falsification criteria (draft):** same validation-first gate as A, plus a
  minimum-events requirement (else `INSUFFICIENT_SAMPLE`, not a pass).

### C. Session / volatility regime family — **supporting layer, not standalone**

- **Rationale:** liquidity/vol regimes demonstrably modulate cost and signal
  quality (session spread differences are large and observable in BA data).
- **Standalone or filter:** **filter/conditioning layer only.** A regime gate
  multiplies an existing edge; it does not create one (archived Phase 9.7/9.17
  record: modest, mixed effects). It enters family A/B designs as a
  pre-registered conditioning variable.
- **Overfitting risk:** high — regime definitions are a classic
  many-degrees-of-freedom trap. Mitigation: regimes must be defined from
  design data only, with a small pre-registered set (e.g. 3 sessions ×
  2–3 vol buckets), never searched.
- **Validation requirements:** regime-conditioned metrics reported on
  validation; no regime may be dropped/added after seeing holdout.
- **Falsification:** if regime conditioning does not improve validation net
  expectancy at pre-registered granularity, it is dropped without iteration.

### D. Calendar / event-risk aware family — **supporting layer, not standalone**

- **Rationale:** scheduled macro events produce known spread/vol spikes;
  avoiding them is cost control, not alpha.
- **Data-source requirements:** an external economic-calendar source with
  point-in-time integrity — **not currently in the repo**; acquisition,
  licensing, and as-of reconstruction are open questions (§10).
- **Leakage risks:** severe if calendars are revised post-hoc; only
  point-in-time snapshots are admissible, and ingestion would need its own
  provenance gate (Gate-P1-style).
- **Execution limitations:** event windows are exactly when fills degrade;
  avoidance is more robust than exploitation.
- **Role:** supporting avoidance filter inside A/B once a calendar source
  passes provenance review; standalone event-trading is out of scope.

### E. Carry / macro-light family — **deferred**

- **Rationale:** interest-rate differential (carry) is a documented long-horizon
  FX return source, orthogonal to technical families.
- **Data support:** requires swap/forward-points or policy-rate data —
  **not in the current archive**; OANDA candles alone cannot support it.
- **Horizon implications:** weeks-to-months holding periods; incompatible with
  the M1/M15 scalping infrastructure and with 365-day evaluation spans
  (sample-size collapse).
- **Verdict:** deferred until a positive-edge technical family exists and a
  provenanced rates/swap data source is adopted; revisit at the portfolio
  layer (G) horizon.

### F. Microstructure-grade M1 family — **deferred (the only admissible M1 return path)**

- **Material difference from the failed flagship:** the closed M1 family failed
  for lack of microstructure information and cost headroom. A genuine M1 retry
  requires *different information*: tick/order-flow/book-imbalance features,
  explicit spread-regime modelling, and sub-bar execution assumptions — none of
  which OHLC M1 candles can provide. Same-data M1 retries are forbidden by the
  PR #426 closure.
- **Data requirements:** tick-level or L2 data with provenance (new
  acquisition; large volumes; new Gate-P1/P2-style admissibility work).
- **Cost/slippage requirements:** empirical fill modelling, not flat cells.
- **Verdict:** **deferred indefinitely** — highest data cost, highest
  implementation risk, lowest auditability today. It exists on this roadmap
  only to record what a legitimate M1 return would require.

### G. Portfolio / pair-selection layer — **prerequisite-gated**

- **Edge creation vs allocation:** allocation only. It can concentrate or
  diversify an existing positive edge; it cannot rescue a negative one
  (PR #426 §12.H).
- **Why holdout-derived pair selection is forbidden:** selecting pairs on the
  consumed holdout is textbook selection bias — the PR #425 per-pair table is
  permanently off-limits for design.
- **When appropriate:** after at least one family shows positive validated
  edge; pair weights/selection then become pre-registered design-data choices
  inside that family's protocol.

### H. Risk-overlay-only family — **forbidden as a standalone research path**

- Risk controls (stops, throttles, caps, kill switches) bound losses; they
  cannot create expectancy. With a negative-edge core, every overlay merely
  shapes the bleed (archived Phase 9.13 C-3 finding; PR #426 §12.H).
- **Role:** mandatory containment inside any executing family (and later
  paper/live gates), never a research hypothesis of its own.

## 5. Ranking and recommended sequence

| Rank | Family | Verdict |
| --- | --- | --- |
| **1st** | **A — M15-first cost-hurdle-aware** | recommended first: largest expected improvement in cost-to-signal per unit of new work; data + tooling in hand; fast time-to-valid-test; validation-first falsification is cheap |
| **2nd** | **B — H1/H4 swing** | recommended second (or parallel *thesis-writing* only): best cost profile; slower falsification (sample size); benefits from A's cost-model and label tooling |
| Support | C — session/vol regime; D — calendar avoidance | conditioning layers inside A/B; C immediately (data in hand), D pending calendar-source provenance |
| Deferred | E — carry/macro; F — microstructure M1 | blocked on new data sources + admissibility work |
| Gated | G — portfolio layer | unlocked only by a positive-edge family |
| Forbidden | H — risk-overlay-only; any same-data M1 flagship retry; any use of the consumed `365d_BA` holdout for design | not research paths |

**Ordering rationale:** A dominates B on time-to-valid-test and sample size;
B dominates A on cost headroom; both clearly dominate everything else on data
availability, auditability, and implementation risk. Starting at M15 (not H1)
preserves statistical power within a one-year-class epoch while still cutting
the M1 cost pathology by roughly an order of magnitude; if A fails its
validation gate honestly, B is the natural escalation with tooling reuse.
**No family is authorised to implement or execute by this ranking.**

## 6. Dataset and epoch strategy

- **Consumed:** the `365d_BA` **M1 frozen holdout span
  (2026-03-01 → 2026-04-24)** is consumed for design/tuning/selection —
  permanently, for every future family (any strategy that "avoids" only the
  exact M1 contract but designs against the same price window is contaminated).
- **Open governance question (§10):** whether the `365d_BA`
  **pre-holdout** span (2025-04-25 → 2026-03-01) may serve as *design data*
  for a new-timeframe family. Default-conservative position pending decision:
  usable for exploratory design only, with any new frozen holdout taken from a
  **disjoint, later or separately-adopted** span — never re-freezing the
  consumed window.
- **New epochs:** any new frozen epoch (including any M15/H1 aggregate epoch
  derived from archived raw data) requires its own byte-admissibility /
  epoch-adoption process (Gate P2 pattern: inventory, checksums, ts-bounds,
  retention binding). `730d_BA` and `3650d_BA` are **not authorised here**;
  the preserved 10-year archive is the raw-material candidate for future
  adoption decisions, nothing more.
- **Roles:** (i) **exploratory/design data** — oldest spans; unrestricted
  iteration; results never citable as evidence; (ii) **validation data** —
  pre-registered span; bounded, pre-declared model/threshold comparisons;
  gates the right to touch any holdout; (iii) **frozen holdout** — one-shot,
  purge/embargo-separated, consumed on first decision use; (iv) **disjoint
  replication epoch** — separately adopted, non-overlapping; required before
  any production-grade claim.
- **Leakage rules:** chronological ordering (design < validation < holdout);
  purge/embargo at every boundary (≥ horizon+1 bars); no feature/label may use
  information from a later role's span; per-pair pip/spread parameters fixed by
  convention (not fitted); any statistic computed on a holdout before its
  single authorised evaluation invalidates that holdout.
- **Consumption rule:** a holdout is consumed the moment any decision-bearing
  metric from it is observed — including via an invalid run (the PR #421
  precedent: the corrected PR #425 re-measurement was admissible only because
  the invalid observation provably fed back into nothing; that defence is
  one-time-per-incident and requires explicit governance approval).
- **Invalid runs:** prove the invalidator from committed evidence → code-only
  fix → adversarial re-check → separately-authorised corrected re-measurement
  (if no feedback loop) or holdout forfeiture (if contaminated).

## 7. Source reuse / non-reuse strategy

- **Reusable as governance/evidence patterns (as-is or lightly generalised):**
  the `scripts/ml_step4/` manifest / evidence / acceptance / diagnostics
  discipline; checksum + inventory tooling (`inventory.py`, provider verify);
  the scrubber (`evidence.assert_clean`) and protected-evidence guard; the
  ordered hard-gate executor pattern; the per-pair pip-size authority
  (`data_adapter.pip_size_for` — carry forward verbatim as convention).
- **Reusable after audit/wrapping (per-family source audit required):**
  feature builders (`train_lgbm_models._add_features`/upper-TF, with an
  M15/H1-native review), label helpers (`labels.py` bulk B-2 machinery —
  parameterise horizon/floors), PnL helpers (`traded_direction_pnl_price` —
  F-2-corrected, keep), metric helpers (`metrics.py` — add exit-type counts
  and gross/net decomposition per PR #426's schema gap).
- **Historical-only (citable as record, never as evidence):** all M1 flagship
  evidence (`first_run_181dc52f3a08` invalid; `corrected_second_run_6fbb178280b4`
  valid-but-consumed); the pre-audit stage/compare experiment logs; archived
  Phase 9.x numerics (per the standing tier classifications).
- **Forbidden for future evidence unless rewritten and audited:** the
  optimistic legacy PnL routes (pre-F-2 label→PnL identity mapping); deployed
  model reuse in any evidence path; backtest routes flagged invalid in the
  project-wide logic audit; anything that reads the consumed holdout span for
  design/tuning.
- **Live/paper runners** (`run_live_loop`, paper stack, supervisor cadence):
  **not research evidence** — engineering assets for the separate production
  P1–P3 / paper gates only; they play no role in research acceptance.

## 8. Acceptance philosophy (draft principles — final thresholds set at pre-registration)

- **Cost-aware expectancy is the primary economic object:** net expectancy
  under an **empirical per-pair/session cost model**, with the flat-cell
  sensitivity sweep retained as a robustness axis.
- **Gross vs net decomposition mandatory:** every report must show the edge
  before and after each cost layer (embedded spread, slippage cell), so
  "cost-killed" vs "no gross edge" is decidable at a glance (the PR #426
  decomposition, institutionalised).
- **Turnover budget as a hard gate,** enforced by design (event definition +
  abstention), with capacity reasoning recorded.
- **Daily portfolio Sharpe** retained as the primary risk-adjusted metric;
  **max equity drawdown** retained (vs fixed notional); **trade-count lower
  bound** added (an H1/H4 result with too few events returns
  `INSUFFICIENT_SAMPLE`, not a verdict); **daily coverage**, **pair trade
  concentration**, and **positive-PnL concentration** retained as
  distributional gates.
- **Cost-assumption sensitivity:** acceptance requires survival at a stressed
  cost cell (draft: net expectancy ≥ 0 at 2× the modelled cost), not just the
  base case.
- **Validation-first gating:** no holdout touch until validation clears a
  pre-registered net-expectancy floor (draft candidate: ≥ +0.5 pips/trade at
  M15 — explicitly a draft, to be fixed at pre-registration).
- **Disjoint replication before any production-grade claim.**
- **Invalidation rules:** closed vocabulary (`…EVIDENCE_INVALID`,
  `…STOPPED_BEFORE_TRAINING`, `INSUFFICIENT_SAMPLE`, …); any proven
  implementation defect in a unit/sign/alignment path invalidates the run;
  invalid ≠ negative (the #421/#425 distinction, kept).

## 9. Decision gates (the pipeline for whatever family is selected)

1. **This roadmap PR** (`POST_M1_RESEARCH_PROGRAM_ROADMAP_PROPOSED`).
2. **Fable 5 adversarial roadmap audit PR** — attack the ranking, the dataset
   strategy, and the acceptance philosophy before anything is designed.
3. **Selected-family pre-registration design PR** — full contract: epoch,
   labels, features, model, thresholds/EV gate, splits, acceptance numbers,
   falsification criteria, evidence schema (incl. exit-type counts).
4. **Fable 5 design audit PR.**
5. **Code-only implementation PR(s)** — fixture-tested, no real run.
6. **Source-contamination audit PR** — before any real data touch.
7. **Single-run execution PR** — one shot, gates first, metadata-only evidence.
8. **Post-run audit PR** — validity before interpretation.
9. **Disjoint replication decision** — human + ChatGPT gate for any
   stronger-than-research claim.
10. **Paper/live gate** — entirely separate approval track (Production P1–P3);
    never implied by research acceptance.

Each gate requires explicit human + ChatGPT approval to proceed; no gate may be
skipped or merged into another.

## 10. Blockers and open questions

1. **Epoch choice:** which span/timeframe becomes the new design+validation
   set, and where the new frozen holdout comes from (disjoint later span vs
   separately-adopted archive slice). Requires a Gate-P2-style adoption
   decision. `730d_BA`/`3650d_BA` remain unauthorised.
2. **Pre-holdout reuse:** may the `365d_BA` pre-holdout span serve as design
   data for a new-timeframe family? (Default-conservative: design-only, new
   holdout disjoint. Needs explicit ruling.)
3. **M15-first vs H1-first:** this roadmap ranks M15 first on
   time-to-valid-test; the roadmap audit (gate 2) should stress-test whether
   H1's cost headroom outweighs its sample-size cost.
4. **Empirical spread reliability:** BA candles give top-of-book quote spread
   at bar boundaries; whether that suffices as a fill-cost model (vs padding
   margins) must be settled in the design PR.
5. **Calendar/event data:** no point-in-time source in the repo; acquisition +
   leakage-safe ingestion is unresolved (family D stays supporting-only until
   solved).
6. **Feature builders at M15/H1:** are the v4 builders correct/meaningful at
   native M15/H1 bars (warmups, upper-TF definitions), or is a rewrite needed?
   Belongs to the implementation-audit gates.
7. **EV-gate calibration:** does the EV threshold require probability
   calibration (and if so, on which split), or can it be rank-based? Must be
   fixed at pre-registration to avoid post-hoc choice.
8. **Evidence-schema additions:** exit-type counts (TP/SL/timeout), gross/net
   layers, per-regime metrics — to be specified in the design PR.

## 11. Non-authorisation statements

This document does **not**: implement anything; train models; evaluate any
holdout; execute any run; generate metrics or evidence; select or adopt an
epoch; authorise family A or any other family to proceed past gate 2; start
H2/H3, Phase C2, or M15/H1 implementation; use `730d_BA` or `3650d_BA`; access
Google Drive or R2; modify any prior evidence; or claim production readiness.
The consumed `365d_BA` holdout remains quarantined. All statuses:
`POST_M1_RESEARCH_PROGRAM_ROADMAP_PROPOSED`, `NO_EXECUTION_PERFORMED`,
`PRODUCTION_READINESS_NOT_CLAIMED`.

## 12. Recommendation for next gate

1. **Merge this roadmap** (records the proposed program; authorises nothing).
2. **Run the Fable 5 adversarial roadmap audit** (gate 2) — attack the A-first
   ranking, the dataset/epoch strategy (esp. open questions 1–3), and the
   acceptance philosophy.
3. Only after that audit is accepted: **draft the selected family's
   pre-registration design PR** (gate 3) — expected to be family A (M15-first
   cost-hurdle-aware), doc-only, separately approved.
4. **Do not implement or execute anything** until gates 2–4 have passed and a
   human + ChatGPT decision explicitly authorises implementation.
