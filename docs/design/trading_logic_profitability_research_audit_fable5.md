# Fable 5 trading-logic & profitability research audit (root-level)

- **Document class:** doc-only root-level audit of the trading thesis, buy/sell
  decision logic, alpha hypotheses, evaluation design, and research roadmap.
  Executes nothing; changes no code.
- **Branch:** `docs/fable5-trading-logic-profitability-audit`
- **Base:** master `b70de8e` (post PR #412 merge)
- **Evidence basis:** `docs/design/project_wide_logic_audit_fable5_findings.md`
  (F-1…F-13); phase 22/23/24 final syntheses + integrity audit; phase 25/26/27/28
  closure memos; `phase27_29_tabular_eval_validity_audit.md`;
  `research_development_roadmap_post_audit.md` (§2 tiers, §6 Tracks A–G, §11A
  levers, §11B root-logic mandate); PR #407 pre-registration; PR #408
  execution-authorisation; PR #409 stop evidence; PR #410/#411/#412 executor +
  harness review + fixes; strategy/trainer/feature/label source code.
- **Relationship to the roadmap:** this document substantially discharges the
  roadmap Amendment 7/8 **§11B Root Logic Reassessment / Profit Logic Audit**
  obligation for the ML Step 4 path (§11B.1–§11B.9 are answered in §§2–10, 17
  below). Roadmap bindings (tier classifications, archived numerics, track
  gating) remain in force verbatim; nothing here promotes any archived numeric.

## Audit status

**`TRADING_LOGIC_PROFITABILITY_RESEARCH_AUDIT_ACCEPTABLE_FOR_GUARDED_WIRING_WITH_REQUIRED_RESEARCH_DISCIPLINE`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

---

## 1. Executive verdict

**The central epistemic fact of this project is an asymmetry: every historical
POSITIVE result is invalidated, and every honest measurement was negative or
tiny.** The Phase 9.X positives (Sharpe 0.160–0.177, "+20% PnL") rest on the
F-2 optimistically-biased PnL layer (real stop-losses scored as 0.0; timeouts
booked at zero cost), F-6 reused-OOS multiplicity (argmax of a ~150-cell search
on one OOS grid), and F-7 per-trade non-annualised Sharpe over overlapping
trades. The honest-stack measurements (phases 22–28, ~1,000+ cells across
entry families, exits, features, labels, objectives, and architectures) were
**uniformly REJECT**, with the best honest M1 LGBM baseline at per-trade Sharpe
+0.0822 (~+180 pips/yr across 20 pairs — economically negligible) and the
Phase 28 research baseline itself **negative** (−0.1732).

**What has never been measured is the flagship itself:** the Phase 9-lineage
multipair LightGBM 3-class B-2 triple-barrier champion has never been evaluated
under fully honest F-2/F-5/F-8 accounting on a provenance-bound epoch. That
measurement is exactly what PR #407 pre-registers. The correct frame for the
first run is therefore **a falsification/baseline measurement, not a
profitability attempt**: on all honest priors, the likely outcome is
`..._DOES_NOT_MEET_PREREGISTERED_CRITERIA`, and that outcome is the valuable
product — it closes the M1 flagship question with valid evidence, proves the
audited pipeline end-to-end, and establishes the trustworthy comparator
baseline for the pivot that follows.

**Verdict: proceed to guarded wiring under the existing PR #407/#408 contract**
(after the known wiring residuals R-1/R-4/R-5/R-6 + seed decision), with the
binding research discipline in §12/§17: pre-declared interpretation, no
rerun-into-search, and a pre-committed pivot to the genuinely under-explored
region — **longer horizons (M15/H1/H4), cost-hurdle-aware targets, and new
information (calendar/carry/empirical spread)** — the moment the M1 question is
closed. Changing the contract now would restart the Phase E/F gate chain and add
multiplicity for no informational gain.

---

## 2. Current trading thesis

**Implicit thesis (reconstructed — no document states it):** *short-horizon
(20-minute) directional continuation/imbalance on 20 FX pairs is predictable
from recent price-derived technical state (M1 TA + M5/M15/H1 resampled
features), strongly enough that a gradient-boosted classifier's barrier-race
predictions clear retail spread costs.*

- **Inefficiency claimed:** none is ever articulated. The design is
  pattern-recognition-first: features → 3-class barrier label → argmax/threshold.
  There is no stated economic mechanism (who is on the other side; why the
  pattern persists; why it isn't arbitraged at the M1 horizon).
- **Family:** hybrid momentum/trend-continuation at M1 with multi-timeframe
  context. Not mean-reversion (22.0b killed it), not breakout (22.0c/23 killed
  it), not carry, not event-driven.
- **What the model actually predicts:** *barrier reachability* — P(TP hit
  before SL within 20 bars) per direction — which conflates direction,
  volatility, and path shape. It does not predict expected value; cost enters
  only after prediction (threshold/EV stage), never inside the target.
- **Alignment:** the LightGBM 3-class triple-barrier machinery is internally
  coherent with this thesis, but the thesis itself is the weak link: at M1 the
  median spread is **128% of ATR(14)** (phase 22 measurement: per-pair 65–236%),
  so the tradable residual after cost is a small fraction of the predicted
  quantity. The system has a coherent *statistical* reason to buy/sell and no
  articulated *economic* reason.
- **Conclusion:** the thesis is under-specified. The first run should be
  understood as measuring "does ANY net-of-cost signal exist in this family at
  M1", not as testing a well-formed inefficiency hypothesis. The successor
  experiment must state its mechanism explicitly (see §11).

## 3. Buy/sell decision logic audit

Signal path (production lineage, as pre-registered): completed M1 bar → v4-base
features (15 M1 TA + 24 upper-TF resampled) → LightGBM 3-class
`predict_proba` → confidence threshold (validation-selected from
{0.35, 0.40, 0.45}) → direction = argmax class → entry next-bar ask (long) /
bid (short) → exit only at TP (1.5×ATR14), SL (1.0×ATR14), or 20-bar timeout
mark-to-market → event-driven max 1 open position per pair.

- **Economic meaningfulness of direction:** the label's "clears" rule (TP fires
  strictly before own SL) makes +1/−1 genuinely directional and executable —
  post-F-2 this maps cleanly to tradable decisions. Sound.
- **What must be true to make money (the audit's key arithmetic):** with
  barrier geometry already embedding spread once (ask-entry/bid-exit) and the
  0.5-pip flat cell, a "win" nets ≈ `1.5·ATR − 0.5p` and a "loss" nets
  ≈ `−1.0·ATR − 0.5p`. At a representative EUR_USD M1 ATR ≈ 1 pip, that is
  **+1.0 vs −1.5** — the nominal 1.5:1 reward:risk *inverts* to 1:1.5 after
  cost, so the model needs ≥ ~60% precision on resolved 20-minute barrier races
  just to break even (worse on the ~2/3 of pairs with higher spread/ATR; better
  only on USD_JPY-class pairs). No honest measurement in this repository has
  ever shown precision anywhere near that at M1.
- **Thresholding/calibration:** thresholds apply to raw uncalibrated
  `predict_proba` (audit F-8; isotonic calibration exists in stage25–27 research
  but was never ported). Calibration is a known gap — acceptable for the frozen
  first run (declared limitation in PR #407 §4), mandatory before any
  paper-trading decision.
- **Entry timing:** next-bar open entry is honest and consistent with labels
  (F8-A fixed). Phase 22.0c showed entry-timing refinement (retest/momentum)
  does NOT rescue the economics — entry timing is not the binding constraint.
- **Exit coherence:** exits are label-symmetric (same barrier contract), which
  is clean. Phase 24 proved exhaustively (87/87 cells REJECT) that exit-side
  optimisation cannot rescue entries without edge; keeping exits frozen is
  correct.
- **Long/short asymmetry:** none modeled. Phase 22 integrity audit found both
  long and short means negative at M1 — no evidence asymmetric modeling is the
  binding constraint at this horizon; defer.
- **Pair-specific behavior:** one pooled cross-pair model with per-pair
  evaluation. Phase 22.0z showed pair-restricted universes *hurt* (co-training
  matters) and single-pair concentration is the recurring failure driver; the
  §10 concentration guards are therefore well-aimed.
- **Session/regime:** deliberately absent from the first run — justified:
  session filters were destructively falsified as train-side filters (22.0z),
  and regime conditioning was falsified four independent ways (27.0f, 28.0a-L3,
  28.0b-R3, 28.0c-AR4). They should return, if at all, as *cost-side* inputs
  (spread-by-time-of-day), not alpha inputs.

## 4. Alpha hypothesis inventory

| # | Hypothesis | Status | Hold period | Freq | Cost sens. | Key features | Label | Validation | Overfit risk | Priority |
|---|---|---|---|---|---|---|---|---|---|---|
| H1 | M1 scalping (current champion) | **likely dead** (128% spread/ATR; all honest priors negative; PR #407 = the formal test) | 20 min | high | extreme | v4 base | B-2 3-class | PR #407 frozen holdout | low (frozen) | **run once to close, then stop** |
| H2 | M5/M15 intraday continuation, ML judgement | **plausible-weak** (rule families REJECT at −0.16…−0.32, but the *ML* judgement layer was never honestly run at M5/M15; cost 50%/32% of ATR) | 1–8 h | med | high | v4-base recomputed at M5/M15 + spread features | cost-hurdle-embedded barrier or meta-label | new pre-registration, frozen holdout | med | **1st post-pivot** |
| H3 | H1/H4 swing continuation/momentum | **plausible — genuinely untested** (cost share falls to ~10–15% of ATR; never evaluated in this repo at any rigor) | 0.5–5 days | low | med | H1/H4/D1 trend, vol, carry, calendar distance | EV-aware barrier, longer horizon | walk-forward + frozen tail; low trade count needs ≥2y span (730d_BA when authorised) | med-high (small n) | **2nd post-pivot / co-primary** |
| H4 | Donchian/breakout continuation | **likely dead** at M1–M15 (44% false-breakout; overtrading; 23.0b/d, 24 exhaustive) | — | — | — | — | — | — | — | kill (≤M15); untested ≥H4 |
| H5 | Mean reversion after overextension | **likely dead** at M1/M5 (spread≈ATR; 22.0b −0.18, 23.0c −0.28); untested ≥H1 | — | — | — | — | — | — | — | kill (≤M5) |
| H6 | Volatility regime expansion/contraction | **weak** standalone (P25 F1/F2 AUC≈0.56 with negative Sharpe; 24.0d R1 marginal) | — | — | — | — | — | — | — | conditioning input only |
| H7 | Session-specific behavior | **likely dead** as alpha/filter (22.0z destructive; 9.X-L −8.9%) | — | — | — | — | — | — | — | cost-side only (spread by hour) |
| H8 | JPY-cross common factor | **weak** (JPY universes all REJECT; concentration risk dominates) | — | — | — | — | — | — | — | kill as universe filter |
| H9 | USD factor / DXY | **untested honestly** (9.X-D archived-untrusted; Track D.4/D.5 material) | days | low | low | DXY, rate spreads | — | Track D gate | med | after H2/H3 |
| H10 | Cross-pair relative strength (CSI) | **likely dead** as features (P25 F3 AUC 0.548 FAIL; CSI −15% PnL) | — | — | — | — | — | — | — | kill |
| H11 | Range/trend regime switching | **likely dead** deterministic (AR4 worst cell −0.405); learned gating (Track F) deferred | — | — | — | — | — | — | high | defer |
| H12 | News/event avoidance | **plausible, untested** (calendar never wired — audit F-12; pure cost/risk-side lever) | n/a | n/a | improves cost | economic calendar (Track D.2 gate) | n/a | event-window PnL attribution | low | **with H2/H3** |
| H13 | Spread/liquidity timing | **plausible, cost-side** (roadmap L1 = highest near-term; P2 observational snapshotting) | n/a | n/a | is the lever | live spread by pair×hour | n/a | observational then A/B | low | **highest near-term non-ML** |
| H14 | Pair selection / meta-strategy | **weak-unknown** (selector quality was measured under the tainted layer; first run re-measures implicitly) | — | — | — | — | — | — | — | read from first-run diagnostics |
| H15 | Portfolio diversification across pairs | **plausible but bounded** (pairs systemically correlated; √K lift failed in 9.19) | — | — | — | — | — | — | — | keep 20-pair portfolio frame |

## 5. Lessons from previous failures

1. **Why M1 scalping failed:** structural cost, not model weakness. Median M1
   spread/ATR = 128% means the quantity predicted is smaller than the fee to
   trade it. Overtrading amplifies it (23/24: "still_overtrading" on 100% of
   exit cells; per-trade mean PnL stuck at −1…−3 pips). Wrong-label/wrong-metric
   made it *look* alive pre-F-2 — the accounting fix, not the market, killed it.
2. **Moving to M5/M15 is justified but insufficient alone:** cost drops to
   50%/32% of ATR (real, verified not an aggregation artifact), yet all
   *rule-based* families still failed. The untested combination is ML judgement
   + cost-hurdle-aware target at those TFs (H2). "Cost improvement is necessary
   but not sufficient" (Phase 23 §9) is the single most load-bearing sentence in
   the archive.
3. **Donchian/Phase 23/24:** M15 Donchian h=4 had the strongest *raw path-EV*
   of anything measured — and still could not be converted to realised PnL by
   any of 87 exit variants. Lesson: path-EV ≠ tradable EV; conversion is where
   edges die. Any future design must embed conversion (cost, exit) in the
   *target*, not hope to recover it downstream.
4. **Exit optimisation failed because entries had no edge, and costs dominated**
   — both, demonstrably: capture ratios were negative (−0.35) even on the best
   path-EV reservoirs. Exits were not the defect.
5. **Meta-labeling:** the only phase-22 non-REJECT (+0.138 walk-forward)
   evaporated under strict chronological OOS (−0.019) as a one-pair/one-window
   multiplicity artifact. Lesson institutionalised: walk-forward folds within a
   dataset are NOT a substitute for a never-touched chronological tail — the
   PR #407 frozen-holdout design is the direct descendant of this lesson.
6. **Score ≠ money:** Phase 27.0d achieved Spearman +0.438 (real ranking
   signal!) with Sharpe **−0.483**; Phase 25 F5 improved AUC while PnL worsened.
   Ranking/classification metrics are diagnostics only; only post-cost
   portfolio PnL decides.
7. **Kill (confirmed dead):** M1 rule-based MR/breakout; session train-side
   filters; JPY/pair-restricted universes; CSI features; deterministic regime
   splits; per-trade-Sharpe metrics; label-class swaps as a standalone lever
   (Phase 26: L-1≡L-2≡L-3 identity); exit-side rescue of edgeless entries.
8. **Revisit under corrected contracts:** the flagship M1 LGBM itself (=PR
   #407); ML judgement at M15/H1 (H2/H3); meta-labeling *on top of* a
   longer-TF primary signal with proper OOS; calendar/carry information
   (Tracks D.2/D.4); learned regime gating only after a positive primary exists.

## 6. Feature and information audit

- **Present (v4 base):** 15 M1 TA features (EMA/MACD/RSI/BB/ATR/returns) + 24
  upper-TF (M5/M15/H1 × returns, vol, RSI, MA-slope, BB%b, trend) — pure
  price-derived, causal (F8-D/E fixed), deterministic hash. **Sufficient for
  the first run**: the question being measured is whether *this* production
  feature surface carries net-of-cost signal; changing it now would answer a
  different question.
- **Opt-in exclusions (mtf/vol/moments) are right for run 1:** the mtf group's
  headline number was lookahead-falsified (F-10); vol/moments showed
  interference (9.15: all-12 underperforms). Multiplicity minimisation wins.
- **Missing information that likely matters (for successors, gated by Track D):**
  1. **empirical spread/liquidity state** (the one feature class that improved
     AUC in Phase 25 — F5 — and the only lever class with a clean causal story:
     you always pay it) — P2 snapshotting feeds this;
  2. **economic calendar distance/severity** (never wired; F-12);
  3. **carry / rate differentials** (untested; the classic persistent FX factor);
  4. **time-axis features** (D.1 — cheap, timestamp-derived).
- **Known-weak/leak-prone to avoid:** CSI/cross-pair strength (F3 falsified);
  in-progress upper-TF buckets (F8-E — only shift(1) completed buckets);
  hour/dow as train-side inputs (22.0z destructive); anything from the v16/v18
  non-causal MTF code path (F-10 — still in-tree, do not touch).
- **Noise floor:** M1-derived features at 20-minute horizons sit below the cost
  floor regardless of information content — the feature question is second-order
  until the horizon question (H2/H3) is answered.

## 7. Label and target design audit

- **Current target (B-2, TP 1.5×ATR / SL 1.0×ATR / h=20 M1, SL-first strict,
  timeout MTM):** internally consistent, honest, executable, and now uniformly
  enforced train↔eval (F8-A, PR #412 B-1). As a *first measurement* target it
  is right. As a *profit* target it has two structural defects:
  1. **cost is outside the label** — the model optimises barrier reachability,
     not net EV; at M1 the gap between those two is ~128% of ATR;
  2. **horizon 20 M1 bars** pins the strategy inside the worst cost regime
     measured in this repository.
- **Timeout as a class:** legitimate in 3-class form; but timeouts were 84% of
  labels in the 9.X-C era — the class the model sees most is the one that makes
  no money. An EV-regression or trade/no-trade meta-target reduces this
  distortion; note Phase 26 showed label-class swaps *alone* don't monetise
  (identity result), so target redesign must be coupled to horizon/cost changes,
  not substituted for them.
- **Recommended successor target designs (priority order):**
  1. **cost-hurdle-embedded barrier label at M15/H1** — label +1/−1 only if the
     traded direction clears TP *net of a per-pair empirical spread + slippage
     hurdle*; else 0 (H2 experiment);
  2. **two-stage direction → meta-label trade-quality** (direction model at
     H1 + meta-model on "is this signal worth its cost"), validated with the
     strict-OOS lesson from 22.0e-v2;
  3. **expected-value regression with per-pair normalisation** (Track E.3) only
     after 1–2 establish a positive primary;
  4. separate long/short models: defer — no honest evidence of asymmetry being
     binding.
- **Is the 3-class classifier the right first ML Step 4 experiment?** Yes — not
  because it is the best design, but because it is the *committed production
  lineage*, and the first honest number must be measured on the thing the
  project actually built. Redesigns start from that baseline.

## 8. Cost, spread, and execution realism

- **What is honest now:** spread embedded once via B-2 ask/bid geometry; flat
  0.5-pip primary cell + 0.0/1.0 diagnostics; turnover guard ≤40/day (vs the
  execution-infeasible ~80/day of the tainted era); max 1 position/pair.
- **What the flat cell misses:** per-pair spread differences span **3.6×**
  (USD_JPY 0.673 → AUD_NZD 2.375 spread/ATR); time-of-day and event widening
  are unmodeled; a single flat pip understates costs exactly on the pairs/hours
  where naive signals fire most. The 1.0-pip diagnostic cell partially bounds
  this, and the §10 guard ("expectancy ≥ 0 at 1.0 pip") is the right blunt
  instrument for run 1.
- **Before any result is *believed* (as opposed to measured):** the cost model
  must graduate to **empirical per-pair × per-hour spread distributions** from
  live snapshotting (roadmap P2 → P1, lever L1 — highest near-term priority and
  runnable in parallel with everything else since it is observational), plus
  slippage measurement from paper fills. A strategy that only survives at flat
  0.5 pip is not evidence; one that survives per-pair empirical costs at the
  75th percentile is.
- **M1 vs M5/M15 burden:** 128% / ~50% / ~32% of ATR — the single most
  decision-relevant measurement in the repository, and the quantitative core of
  the pivot recommendation.

## 9. Evaluation metric audit

- **Primary (daily portfolio Sharpe, annualised, on frozen holdout at 0.5 pip):**
  correct and hard-won — it directly repairs F-7 (per-trade Sharpe over
  overlapping trades was the old regime's most misleading metric). Executor
  computes it from the daily series (PR #410/#412, test-pinned).
- **Decision vs diagnostic separation (binding):** decision = the §10 table
  (trades ≥300, coverage ≥60%, expectancy >0, Sharpe ≥0.8, maxDD ≤15%,
  turnover ≤40/day, concentration 40%/50%, 1.0-pip expectancy ≥0, provenance).
  Diagnostics only = win rate, payoff ratio, per-pair/session contribution,
  calibration curves, feature importance, validation threshold curves. The
  PR #407 §11 `NON_DECISION_EXPLORATORY` labeling rule must be enforced in the
  evidence writer at wiring time.
- **Sharpe ≥0.8 meaningfulness:** as a *pass* bar it is low for live purposes
  but appropriately high for this data: on 365d, an annualised daily Sharpe of
  0.8 is ≈ a 1.5σ observation — weak evidence even when met. This is fine
  because the run is a falsification measurement; §17's discipline prevents
  over-reading a marginal pass.
- **MaxDD ≤15% definition gap (must pin at wiring):** the criterion is
  "% of fixed notional equity" but the notional (pips base per unit stake) is
  not yet numerically pinned anywhere. The wiring PR must fix the notional
  constant (and the R-5 trading-day definition) in the pre-registered config —
  otherwise the DD criterion is unfalsifiable. **This is the only material
  metric gap found.**
- **Missing before paper/live (not before run 1):** capital-based equity curve
  with position sizing; unrealized-loss-aware drawdown; per-trade slippage
  distribution vs assumed; regime-stratified PnL; rolling drift metrics.

## 10. Validation design and anti-overfitting plan

Already institutionalised (keep): frozen never-touched holdout evaluated once;
purge/embargo = horizon+1; validation-only threshold selection from a
pre-declared 3-set; max 3 configurations / 1 champion; rejected variants
reported; hard `ML_STEP4_RUN_INVALID_*` vocabulary; no-rerun-into-search rule;
fail-closed executor (PR #410–#412).

Required additions for the research program (binding on successor design memos):

1. **Experiment registry:** every future experiment family gets a pre-registered
   design memo with hypothesis, mechanism statement, config count, thresholds,
   and §11B.8 root-cause taxonomy + §11B.9 kill criteria BEFORE data touch —
   the phase-22 8-gate discipline generalised.
2. **Family-wise multiplicity budget:** count every evaluated cell against the
   family; report the count in the evidence; a result that is the argmax of N
   cells must present N (the F-6 lesson made procedural).
3. **Champion/challenger:** the first-run honest number becomes the standing
   champion (even if negative — the champion can be "no-trade/cash"); every
   successor challenges it on the SAME frozen holdout protocol on a NEW epoch
   window, never re-using the 365d_BA holdout for a second decision.
4. **Epoch expansion:** `730d_BA`/`3650d_BA` only after a separately authorised
   Phase C2 + byte-admissibility + adoption chain, and only when a hypothesis
   *needs* the span (H3 swing horizons legitimately will — low trade counts).
5. **Pair/session cherry-picking firewall:** all-20-pair portfolio is the unit
   of decision; per-pair/session views are diagnostics; any universe change is
   itself a pre-registered experiment (22.0z lesson).
6. **Exploration vs decision evidence:** exploratory runs are allowed only on
   the training/validation windows and must be labeled non-decision; holdout
   touches are counted and limited to one per pre-registration.

## 11. Strategy roadmap toward profitability

**Must do before first-run:** guarded `execute()` wiring PR (R-1 bar-granularity
boundary rule; R-4 single-source label routing; R-5 trading-day definition;
R-6 tie-rule provenance; seed/determinism decision; **pin the maxDD notional
constant** — §9); wiring re-check; explicit first-run authorisation. Nothing
else — adding anything restarts the gate chain.

**Should do after first-run (the pivot, in order):**
1. Post-run audit + formal classification of the M1 flagship lineage (expected:
   closed-with-valid-negative; if positive: replicate before believing — §12).
2. **P2 live spread snapshotting** (observational; can start even earlier in
   parallel — it is the cheapest real information the project can buy).
3. **H2 experiment family:** M15 (and/or H1) ML judgement with
   cost-hurdle-embedded labels, per-pair empirical spread hurdles, calendar
   distance as a *risk* input; full pre-registration; frozen holdout on a new
   window.
4. **H3 experiment family:** H1/H4 swing horizon (requires 730d+ span → Phase
   C2 chain when authorised).
5. Data upgrades per Track D gates: D.1 time-axis (cheap) → D.2 calendar →
   D.4 rate differentials.
6. Target upgrades (Track E) and architecture (Track C/A0-broad) only after an
   H2/H3-class primary shows a survivable post-cost signal.

**Before paper trading:** F-3/F-12 containment fixes (account-type tautology,
live-env confirmation, leverage-cap JPY conversion, wired event/session logic,
fail-closed DD brake, `close_position` semantics, real QuoteFeed + bid/ask
fills in the flagship runner — audit P1 list); probability calibration ported
to the trainer; capital-based risk metrics; empirical-cost validation of the
candidate; monitoring/drift detection design.

**Before live trading:** sustained multi-month paper record consistent with the
backtest under measured costs; drawdown governance with hard stops; broker
execution-quality measurement (fill slippage distribution); kill-switch
rehearsal; independent (human + ChatGPT + Fable) go review. None of this is in
scope for years-horizon promises — it is listed to prevent scope creep, not to
imply readiness.

**Long-term backlog:** learned regime gating (F), ensembles (G), sequence NNs
(C), MoE — all conditional on a positive primary; portfolio construction
beyond equal-stake; multi-account/latency engineering explicitly out of scope
for retail.

## 12. Current ML Step 4 plan: proceed, modify, or stop?

**PROCEED — as a falsification/baseline measurement under the existing
contract.** Justification:

- The contract is the right *measurement*: production lineage, honest
  accounting, frozen holdout, one champion, closed status vocabulary.
- Every alternative is worse: *modifying* the contract (e.g., to M15) discards
  the Phase E/F gate chain, adds multiplicity, and destroys the one thing only
  this run can produce — the honest number for the thing the project actually
  built. *Stopping* without the measurement leaves the M1 question forever
  arguable and the pipeline unproven end-to-end.
- **What the first run CAN tell us:** whether the flagship family has any
  net-of-cost signal at M1 (likely answer: no/insufficient); the true honest
  baseline for the selector, concentration, turnover, and cost sensitivity;
  that the full audited pipeline produces provenance-complete evidence.
- **What it CANNOT tell us:** anything about profitability elsewhere (M15/H1,
  other targets); anything about live execution; and a *pass* cannot tell us
  the edge is real — 365d of daily Sharpe 0.8 is ~1.5σ; a MEETS outcome is a
  hypothesis to replicate (on 730d_BA via the Phase C2 chain, then paper), not
  evidence to deploy.
- **Pre-declared interpretation (binding):** DOES_NOT_MEET → M1 flagship closed
  with valid negative evidence; pivot per §11; **no rerun, no threshold change,
  no feature-group retry on this epoch**. MEETS → adversarial post-run audit
  (mandated) + replication requirement before any further claim.

## 13. Must-fix before first-run

1. Guarded wiring residuals: R-1, R-4, R-5, R-6 (PR #411 §16(5)).
2. Seed/determinism decision recorded in the wiring PR (PR #412 deferral).
3. **Pin the maxDD fixed-notional constant** in the pre-registered wiring config
   (§9 — the only material metric-definition gap).
4. Enforce `NON_DECISION_EXPLORATORY` labeling for diagnostics in the evidence
   writer path.
5. Nothing else: no feature changes, no threshold changes, no new metrics.

## 14. Should-fix after first-run

Post-run audit; P2 spread snapshotting; H2 pre-registration (cost-hurdle label,
M15/H1); calibration port; F-6-style multiplicity registry formalised;
legacy-route reconciliation memo for the phase 20–26 archive (roadmap
L-LEGACY); F-10 cleanup (lookahead remnants, stale docstrings) — doc/test-only.

## 15. Pre-paper-trading requirements

Audit P1 containment list complete (F-3/F-12); empirical cost model (P2→P1)
validating the candidate at per-pair 75th-percentile costs; calibrated
probabilities; capital-based equity/risk accounting incl. unrealized losses;
drift monitoring; a candidate that met pre-registered criteria on TWO disjoint
epochs (not just 365d_BA).

## 16. Pre-live-trading requirements

Multi-month paper concordance with backtest under measured slippage; hard
drawdown governance + rehearsed kill switch; broker execution-quality
measurement; leverage/regulatory caps fixed (F-3); independent tri-party go
review; explicit position that a first live allocation is an experiment with
a pre-committed maximum loss, not income.

## 17. Kill criteria / stop conditions (program-level, pre-registered)

1. **M1 family:** one honest first-run; DOES_NOT_MEET closes it permanently. No
   M1 successor experiments.
2. **H2 (M15/H1 cost-hurdle family):** max 2 pre-registered experiment families
   (≤3 configs each). If neither achieves post-cost expectancy > 0 at the
   1.0-pip cell AND daily portfolio Sharpe ≥ 0.3 on its frozen holdout → kill
   intraday ML on this data surface.
3. **H3 (H1/H4 swing):** max 2 families after the 730d chain exists; same
   thresholds; else kill.
4. **Data-expansion tracks (calendar/carry/spread):** each gets ONE family
   coupled to H2/H3; no standalone fishing.
5. **Program stop condition:** if after (1)–(4) — i.e., ≤5 honest pre-registered
   families total — no experiment shows survivable post-cost signal, the
   correct conclusion is **no accessible edge on this data/execution surface**;
   the project should stop pursuing retail FX alpha with this stack and either
   terminate the research program or re-scope fundamentally (different asset
   class, different data, different horizon class) via a new root design review.
   "Try one more feature" is not an admissible response to (5).

## 18. Profitability realism assessment (adversarial) & residual risks

- **Strongest argument this will not make money:** retail FX is negative-sum
  after spread; at the chosen horizon the fee exceeds the predicted quantity
  (128% of ATR); ~1,000+ honest cells across seven phases found nothing
  monetisable; ranking signal demonstrably exists (Spearman +0.438) and still
  loses money — the market charges more than the signal is worth at short
  horizons; the only "profits" ever seen came from accounting bias, lookahead,
  or argmax-of-many. These are exactly the conditions under which continued
  search produces false positives, not profits.
- **Strongest argument it might eventually:** the honest machinery now exists
  (labels, costs, holdouts, fail-closed executors — rare discipline); the
  under-explored region (H1–D1 horizons, carry/calendar information,
  empirical-cost-aware selection) is where documented, persistent,
  retail-accessible FX factors live; Phase 22's honest B-Rule was *positive*
  (+0.0822) — signal is nonzero even at M1, it is merely dwarfed by cost, and
  cost share falls an order of magnitude by H4.
- **What counts as real evidence of edge:** pre-registered MEETS on a frozen
  holdout **and** replication on a disjoint epoch **and** paper-trading
  concordance under measured costs. **Insufficient:** any single-epoch result;
  anything chosen from >3 configs; anything only surviving flat 0.5-pip costs;
  any diagnostic metric (AUC/Spearman/win-rate).
- **Biggest self-deception vectors:** rerun-into-search after a near-miss;
  metric substitution ("PnL up" when Sharpe fails); universe/session trimming
  after seeing results; treating the 1.5σ pass bar as proof; forgetting that
  the archive's positives were artifacts.
- **Retail execution constraints:** spread widening at news/rollover; no
  meaningful rebates; queue position invisible; leverage caps; platform
  kill-switch latency — all argue for fewer, longer, larger-edge trades, i.e.
  H3 over H1 over M1.
- **What must be true to justify continuing after the first run:** a
  pre-registered H2/H3 experiment must clear §17(2)'s modest bar. If nothing
  does within the §17 budget, stopping IS the profitable decision.
- **Non-blocking residual risks:** wiring residuals R-1/R-4/R-5/R-6 (bound to
  wiring PR); F-10/F-13 hygiene items (post-run cleanup); phase 20–26 legacy
  reconciliation outstanding (roadmap L-LEGACY); stage24/25 F-9 worktree state
  (pre-existing; untouched by this PR); this audit's horizon-economics
  arithmetic uses representative ATR values, not a new data computation (by
  design — no data was read).

## 19. Recommended next PR sequence

1. **Merge this audit** (human + ChatGPT review first).
2. **Guarded `execute()` wiring PR** — code-only, no run; binds §13 items;
   separately authorised.
3. (Optional, cheap, parallel) **P2 live spread snapshotting design memo**.
4. **First-run execution PR** — separately authorised; runs exactly PR #407
   under §12's pre-declared interpretation.
5. **Post-run audit PR** (human + ChatGPT + recommended Fable 5 adversarial).
6. **Pivot pre-registration** (H2 family design memo per §10/§11), or — if the
   improbable MEETS occurs — replication design via the Phase C2 chain.

## Non-authorisation

This audit did **not**: execute ML Step 4; read real `365d_BA` raw data; train
a model; run a backtest; compute new performance metrics over real data (every
number above is quoted from committed docs/artifacts); create real execution
evidence; write model binaries; start guarded wiring; access external disks,
Google Drive, or R2; start Phase C2; touch `730d_BA`/`3650d_BA`; claim
production readiness; rehabilitate any archived numeric; or promote/demote
Phase 9.16.
