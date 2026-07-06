# Fable 5 post-run audit + research diagnosis — ML Step 4 `365d_BA` corrected second first-run (PR #425)

- **Document class:** doc-only adversarial post-run audit (Part A) + research
  diagnosis (Part B). Executes nothing. Not a rerun, not a fix, not a tuning
  PR, not a new experiment, not H2/H3, not Phase C2.
- **Branch:** `docs/fable5-corrected-second-run-post-audit-and-diagnosis`
- **Base:** master `ee4e6c02f52db4123de899be26e9fb49832984b8` (post PR #425 merge).
- **Method:** committed evidence payloads + committed reports/audits + source on
  the execution SHA + arithmetic consistency checks on committed values only.
  **No raw data read; no model trained; no holdout evaluated; no new real
  metrics generated.**

## Statuses

- **Part A (evidence validity):**
  **`ML_STEP4_365D_BA_CORRECTED_SECOND_RUN_EVIDENCE_VALID_DOES_NOT_MEET`**
- **Part B (research diagnosis):**
  **`M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`**
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `BYTE_ADMISSIBILITY_APPROVED`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; those tokens
appear only in this prohibition list.

---

# Part A — Evidence-validity audit

## 1. Executive verdict

- **Is the PR #425 corrected second-run evidence valid?** Yes.
- **Did the run execute exactly once?** Yes (preflight, then one execution).
- **Was there any rerun?** No.
- **Was there any tuning after seeing results?** No — the PR #425 diff contains
  zero code/test/contract changes; only evidence + report + roadmap pointer.
- **Was the holdout evaluated exactly once?** Yes (`holdout_evaluated_count = 1`
  in the provenance report and the return summary).
- **Is the `DOES_NOT_MEET` conclusion valid?** Yes — the acceptance machinery
  applied the unchanged pre-registered criteria to internally consistent,
  correctly-scaled metrics (arithmetic identities verified in §9–§10).
- **Is the result production-ready?** **No.** `PRODUCTION_READINESS_NOT_CLAIMED`.
- **Does this close the M1 flagship first-run question?** Yes — under the
  pre-registered contract, with valid evidence, the M1 flagship family fails the
  criteria. Part B records the closure.
- **Invalidators found:** none. **Inconclusive items requiring human decision:**
  none for validity. One precision observation (O-A, §9) and one diagnostic
  limitation (evidence lacks exit-type counts, §10.4) are recorded; neither
  affects validity.

## 2. One-shot discipline — CLEAN

- Exact commands: `python -m scripts.ml_step4.execute_365d_ba
  --first-run-preflight` then `python -m scripts.ml_step4.execute_365d_ba
  --execute-first-run-365d-ba` — the registered explicit pattern; no
  corrected-run flag exists in the tooling, and the corrected code on master is
  the executed identity, so this is the correct invocation.
- Execution occurred exactly once; no rerun; no post-result tuning; no
  threshold/feature/model/acceptance change after seeing results (the diff is
  evidence+docs only); no H2/H3; no Phase C2; no new experiment.
- The governance frame was honoured: exactly one corrected attempt, approved in
  advance, with the PR #423 fix as the sole substantive delta from PR #421.

## 3. Provenance and evidence integrity — CLEAN

- Execution code SHA `6fbb178280b46fd8f158ff029f328721c465274d` (recorded in the
  manifest; equals master post-#424 — no code commit precedes the run on the
  branch). PR #425 head `4395be07f11122085e331b6a7fd694934de92b60`;
  squash-merged as `ee4e6c02…`.
- Evidence directory
  `artifacts/ml_step4/365d_ba_v1/corrected_second_run_6fbb178280b4/` — exactly
  **8 payloads**, all metadata-only and **scrub-clean** (re-verified via
  `evidence.assert_clean` in this audit): no raw rows, raw data files, model
  binaries, personal paths, environment dumps, credentials, Drive links, or R2
  endpoints/keys.
- **Directory relocation is bookkeeping-only and does not weaken provenance:**
  the tooling's `_run_dir` emits `first_run_<code_sha[:12]>` =
  `first_run_6fbb178280b4` (already distinct from PR #421's
  `first_run_181dc52f3a08`, so no overwrite was possible); the 8 files were
  moved verbatim to the `corrected_second_run_…` name. The directory name is
  not embedded in any payload (verified by grep before the move, per the PR #425
  report §19), so no payload byte depends on the location; the code SHA inside
  the manifest — not the folder name — is the provenance anchor.
- PR #421 invalid evidence (`first_run_181dc52f3a08/`, 8 files, last-touch
  commit `7a3e1e2`) and PR #409 stop evidence: **untouched**.

## 4. Inventory verification — CLEAN

Provider `scripts.ml_step4.data_adapter.Real365dBaProvider.v1`. Expected /
observed **20 / 20 files**; expected / observed **1,481,715,517 /
1,481,715,517 bytes**; `all_match = true`. Verification is structurally
pre-consumption: `_run_hard_gates` calls `provider.verify()` (gate 5) and any
failure raises before `run_first_run_365d_ba` is entered, and
`Real365dBaProvider.pair_frame` independently refuses unless `verify()` has
passed — no partial training/evaluation before checksum verification is
possible. No unknown or extra dataset was used (the provider can only resolve
the 20 inventory filenames; fail-closed on any other pair).

## 5. Per-pair pip-size verification — CLEAN (INV-1 verified closed in-run)

- `pip_size_by_pair`: **20 mappings**; exactly **six `_JPY` pairs → `0.01`**
  (`AUD_JPY, CHF_JPY, EUR_JPY, GBP_JPY, NZD_JPY, USD_JPY`); exactly **fourteen
  non-JPY pairs → `0.0001`**; `global_pip_size_authoritative_for_all_pairs =
  false`; convention string `0.01 if pair endswith _JPY else 0.0001`.
- Recorded in **both** the run manifest and the leakage/provenance report, and
  the two mappings are byte-identical (verified). Per-pair diagnostics carry
  `pip_size` + `pip_size_kind`, and every `pip_size==0.01` entry corresponds
  exactly to a `_JPY` pair (verified).
- **Scale pathology gone:** JPY per-trade **−4.45** vs non-JPY **−3.04** (net at
  the 0.5 primary cell; ratio **1.47×**, vs **112.8×** in the invalid run). JPY
  loss share **40.5%** (vs 98.4%), roughly proportional to JPY's 31.8% trade
  share. Every remaining JPY value is the same order of magnitude as non-JPY.
  **No sign of the PR #421 pip-scale bug remains.**

## 6. Contract compliance — CLEAN (no drift)

Epoch `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1` unchanged; feature version v4
**base only**, 39 columns, `_add_mtf_features` not called (feature hash
`bff146e4…` unchanged); label contract `labels.v1` unchanged — horizon 20 M1
bars, B-2 eligibility `range(n−h−1)`, SL-first tie, timeout MTM; model family
unchanged — LightGBM 3-class from scratch, `learning_rate 0.05 / num_leaves 31 /
verbose −1 / n_estimators 200`, `hyperparameter_search: none`, `calibration:
none`, no binary persisted (model hash `bc27cfa3…` unchanged); threshold
candidates `{0.35, 0.40, 0.45}` with validation-only selection and the
registered tie rule (threshold hash `fd687703…` unchanged); split 70/15/15,
purge 21, common window `2025-04-25T17:09:00Z → 2026-04-24T20:58:00Z` == the
contract §5 bounds; acceptance criteria unchanged. No threshold search, no
feature search, no model-family change. All four contract hashes equal the
PR #421 values — the pip fix touched none of them, exactly as required.

## 7. Feature / label / prediction alignment — CLEAN

Production v4-base wiring used (binding recorded in the manifest; gate 6
asserts 39 cols + `mtf_excluded`); labels routed solely through
`scripts.ml_step4.labels.v1`; predictions aligned to eligible rows (probs are
computed only for labeled validation/holdout indices); threshold selected on
validation **before** the single holdout simulation (code order:
`select_threshold(val_metrics)` precedes `simulate(hold_signals[selected])`);
holdout could not influence selection; holdout evaluated once. **No
class-direction inversion:** labels `{-1,0,1}` map to training indices
`{0,1,2}` via `_CLASS_INDEX`; the model-config `class_order [-1,0,1]` is the
label vocabulary while the fitted `classes_ [0,1,2]` (all 20 models, verified in
evidence) are the index classes; `_prob_short_long` reads
`p[_CLASS_INDEX[-1]]`/`p[_CLASS_INDEX[1]]` robustly. Consistent, no inversion.

## 8. PnL / pip / cost sanity audit — CLEAN

- Direction/sign conventions unchanged from the audited PR #418/#420 state
  (long: next-bar ask entry, bid barriers/exit; short: mirrored) — the pip fix
  altered no geometry.
- **Pip conversion:** verified per §5; JPY and non-JPY magnitudes now
  commensurate. No pips/raw-price mixing (single conversion site, PR #424).
- **Cost cell:** cells 0.0/0.5/1.0 → **−2.987541 / −3.487541 / −3.987541** —
  exact 0.5-pip steps (verified to 1e-9), confirming the flat cost is applied
  exactly once and unshifted (B-1 intact). The primary expectancy equals the
  0.5 cell exactly.
- **Arithmetic identities (all verified from committed values):**
  Σ(per-pair net PnL @0.5) = **−28,186.31** = 8,082 × −3.487541 exactly;
  gross reconciliation −2.987541 × 8,082 − 0.5 × 8,082 = −28,186.31 exactly;
  `max_drawdown_pips` 28,186.31 = |total net loss| exactly (equity minimum at
  the end — a near-monotone decline, consistent with a uniformly negative
  strategy); `max_drawdown_frac` 2.818631 = 28,186.31 / 10,000 exactly;
  turnover 8,082/48 = 168.375 exactly; win/loss identity
  0.078322 × 6.377858 + 0.921678 × (−4.325881) = **−3.4875** = expectancy @0.5
  exactly. The metrics are numerically airtight.
- **Failed classifier, not an implementation invalidator:** the corrected
  magnitudes sit in a physically plausible band (−3…−4.5 pips/trade), match the
  archived honest M1 rejection band (−1…−3 net) cited by the PR #422 audit, are
  broad-based across all 20 pairs, and reconcile arithmetically end-to-end. No
  sign, pip, class-mapping, or alignment bug is in evidence.
- **Observation O-A (precision, no validity impact):** the per-pair
  `pair_contribution.pnl_pips` values are **net at the 0.5 primary cell**
  (`metrics.pair_contribution(hold_trades, cell_pips)`), so "JPY per-trade
  −4.45 / non-JPY −3.04" are net@0.5 figures; the PR #421 comparison values
  (−358.78 / −3.18) came from the same definition, so the comparison is
  apples-to-apples. The PR #425 report's §21 table did not state the cell
  convention explicitly; recorded here for precision.

## 9. Metrics / acceptance audit — CLEAN

Selected threshold **0.45**; rejected **0.35** (val Sharpe −16.21, n=9,475) and
**0.40** (−16.21, n=7,209) — recorded with the selection. Holdout evaluated
once: **8,082 trades / 48 UTC days**. Metrics at the 0.5 cell: expectancy
**−3.49**; daily portfolio Sharpe (ann.) **−18.91**; maxDD **2.82× notional**;
turnover **168.4/day**; pair-trade concentration **0.289** (≤0.40 ✅); pair
positive-PnL concentration **0.230** (≤0.50 ✅); 1.0-pip expectancy **−3.99**
(≥0 ❌); coverage **1.00**; win rate **7.83%** (diagnostic). Cells
−2.99/−3.49/−3.99. **Four of seven gating criteria fail** (expectancy, Sharpe,
maxDD, turnover, plus the 1.0-pip robustness cell also fails — five failing
checks across the seven-line table; the two concentration criteria pass).
`DOES_NOT_MEET` is the correct closed-vocabulary outcome; diagnostics are
labeled `NON_DECISION_EXPLORATORY` and did not affect acceptance; no
unregistered metric softened or overrode the result.

---

# Part B — Research diagnosis and cause analysis

*(Performed because Part A finds the evidence VALID. All numbers below are
committed evidence values or arithmetic on them; no raw-data recomputation.)*

## 10. Failure decomposition

### 10.1 Gross edge before cost — the classifier's selection edge is negative

Gross expectancy at the 0.0 cell is **−2.99 pips/trade**. The strategy loses
*before* the flat cost cell is applied. This is **not** "cost killed a small
edge": setting the flat cell to zero still leaves −2.99. One nuance: the B-2
label geometry embeds the bid/ask **spread** once (ask entry / bid exit), so the
0.0 cell is post-spread, pre-slippage. The true mid-to-mid edge is not in
evidence, but even granting back a generous ~1–1.5 pips of embedded spread per
trade, the implied mid-mid edge remains negative (≈ −1.5 to −2). **Conclusion:
the classifier has negative gross selection edge; the flat cost only deepens
it.** Lower slippage alone cannot rescue the strategy, and spread cannot be
"removed" — it is a physical cost of trading.

### 10.2 Cost impact — real but secondary

Each 0.5-pip cell step costs exactly 0.50 pips/trade (−2.99 → −3.49 → −3.99).
The flat cell accounts for **0.50 of the 3.49** (~14%) at the primary cell; the
embedded spread accounts for an additional unknown-but-bounded share inside the
−2.99. Cost matters enormously *relative to the attainable edge at M1* (a
realistic all-in cost of ~1–2 pips/trade vs single-pip candidate edges), but in
this measurement the dominant term is **negative selection**, not cost. A
zero-cost world still loses.

### 10.3 Turnover — structurally too high

**168.4 trades/day** against a 40/day gate (4.2× over). At −3.49 pips/trade the
portfolio bleeds ≈ **−587 pips/day**. Even under a hypothetical +0.5 pip/trade
edge, this event rate would demand extreme capacity and would be hypersensitive
to any cost mis-estimate (each 0.5 pip of unmodelled cost swings daily PnL by
~84 pips). The M1 3-class argmax + probability-threshold rule generates far too
many low-quality events; the registered thresholds barely modulate volume
(9,475 → 7,209 → 8,082 across 0.35/0.40/0.45 windows). **The M1 event rate is
structurally too high for the per-trade edge this family can produce.**

### 10.4 Win rate / payoff structure — catastrophically below breakeven

Win rate **7.83%** with avg win **+6.38** / avg loss **−4.33** (payoff ratio
1.47). Breakeven at this payoff requires wr ≈ 4.33/(6.38+4.33) ≈ **40.4%**;
actual is 7.83% — a −32-point shortfall. With TP=1.5×ATR / SL=1.0×ATR and
SL-first ties, a coin-flip directional signal would produce a *far* higher
positive-outcome rate than 7.8%; a rate this low implies the vast majority of
threshold-crossing trades end at SL or in negative timeout MTM — i.e.
high-confidence probability regions are, if anything, *adversely* associated
with realized traded-direction PnL. The committed evidence does **not** contain
exit-type counts (TP/SL/timeout decomposition), so the split between "many SL
hits" and "many negative timeouts" cannot be determined here — recorded as a
diagnostic limitation, not an invalidator. What is determinable: this is not a
marginal calibration problem; the class-probability signal does not select
positive-EV trades at any registered threshold.

### 10.5 Validation behavior — no edge ever existed before holdout

Validation daily Sharpe at all three registered thresholds: −16.21 (0.35),
−16.21 (0.40), with 0.45 selected as least-negative. **The model showed no
validation edge whatsoever** — the holdout (−18.91) merely confirmed what
validation already showed. Thresholding on raw class probability failed to find
an economic signal at every registered operating point; there was never a
positive region to select. This matters for interpretation: the failure is not
an unlucky holdout draw — the entire evaluation chain (train → validation →
holdout) was consistently and strongly negative.

### 10.6 Pair-level behavior — broad-based failure, not one-pair pathology

Both concentration gates pass (trade share 0.289; positive-PnL share 0.230).
**All 20 of 20 pairs have negative net PnL** (verified from the committed
per-pair contributions). JPY loss share normalized to 40.5% (≈ its trade
share). Per-trade losses span roughly −1 to −4.6 pips across pairs. The failure
is uniform across the pair universe — there is no single-pair artifact to
excise, and no subset whose removal would plausibly flip the sign.

### 10.7 PnL scale and plausibility — consistent with the archived prior

The corrected −3.49 net pips/trade sits exactly in the archived honest M1
rejection band (≈ −1…−3 net pips/trade) documented across the committed audit
record and cited by the PR #422 audit, marginally deeper — consistent with this
run's stricter B-2 spread-embedded geometry and 0.5-pip cell. It also matches
the PR #413 prior that a valid M1 flagship measurement would likely be negative.
The corrected measurement is *quantitatively unsurprising*; the PR #421 anomaly
is fully explained by the pip bug and is gone.

### 10.8 Model/label mismatch

The LightGBM 3-class B-2 triple-barrier setup produces probability estimates
that demonstrably do not translate into positive traded PnL: raw
`predict_proba` (no calibration, per the committed model config) over a 3-class
argmax-style rule with a flat probability threshold ignores the *asymmetric
economics* of the two tradable classes (expected win/loss magnitudes, spread,
timeout MTM). Likely contributing mismatches, ranked by evidence support:
(a) **spread-inclusive barrier economics at M1** — with ATR14 on M1 bars, TP/SL
distances are frequently only a few pips, so the embedded spread consumes a
large fraction of every barrier distance; (b) **horizon 20 M1 bars (~20 min) is
short** — timeout MTM outcomes dominate whenever barriers are not quickly hit,
and wrong-side timeouts accrue systematic negative drift; (c) **labels noisy at
M1** — B-2 class labels at this resolution are dominated by microstructure
noise the v4-base features cannot resolve; (d) **probability threshold ≠ EV
threshold** — even a weakly informative classifier cannot be monetised through
a class-probability cutoff when per-class payoffs are asymmetric and
cost-laden. None of these can be tested further on this holdout without
violating the frozen-holdout discipline.

### 10.9 Feature limitations

The v4-base 39 features are lagged OHLC-derived technicals (M1) plus completed
upper-TF aggregates (M5/M15/H1). At M1 horizon-20, predictive power for
direction-of-next-20-minutes must come substantially from microstructure
(order flow, book imbalance, tick dynamics, realized spread), none of which is
present. There is no spread/liquidity-regime input, no session/calendar/event
control beyond raw time-derived indicators, and no cross-sectional currency
strength (excluded by contract). The archived Phase 9.X record (committed)
already showed such feature families producing only marginal lifts at higher
timeframes; expecting them to overcome a ~1–2 pip all-in cost at M1 with 168
trades/day was always the falsification-frame long shot that PR #413
anticipated.

### 10.10 Acceptance criteria failure map

| Gate | Result | Implication |
| --- | --- | --- |
| expectancy > 0 | ❌ −3.49 | profitability failure (core) |
| daily Sharpe ≥ 0.8 | ❌ −18.91 | profitability failure (consistent daily bleed) |
| maxDD ≤ 0.15× | ❌ 2.82× | risk failure — but *derivative* of relentless negative drift, not of volatility spikes |
| turnover ≤ 40/day | ❌ 168.4 | structural design failure (event rate) |
| 1.0-pip robustness ≥ 0 | ❌ −3.99 | cost-robustness failure (already negative pre-cell) |
| pair-trade concentration ≤ 0.40 | ✅ 0.289 | diversification adequate |
| pair positive-PnL concentration ≤ 0.50 | ✅ 0.230 | no reliance on one lucky pair |
| coverage ≥ 0.60 | ✅ 1.00 | sampling adequate |

The passes are all *distributional/safety* properties; every *economic*
property fails. This is a **profitability failure with a clean measurement**,
not a risk-management accident.

## 11. M1 viability assessment

- **Does PR #425 prove all possible M1 strategies cannot work?** **No.** It is
  one contract (one feature set, one label family, one model, one rule) on one
  year of one broker's M1 BA data. Negative existence proofs of that generality
  are not obtainable from one experiment.
- **Does it prove this pre-registered M1 flagship family fails?** **Yes.** The
  evidence is valid, the measurement is clean, the failure is decisive (every
  economic gate, all 20 pairs, validation and holdout agreeing) and consistent
  with the archived prior.
- **Is there enough evidence to continue improving this exact lineage on the
  same holdout?** **No.** The `365d_BA` holdout is now consumed as a decision
  surface for this lineage; any further M1 iteration that evaluates against it
  converts the frozen holdout into a design set. A new pre-registered protocol
  (new validation design, ideally a disjoint epoch) would be required.
- **Is M1 structurally disadvantaged for this architecture and data?** **Yes,
  on the committed evidence:** cost-to-signal is the worst of any timeframe
  (per-trade attainable edge ≲ spread), turnover is intrinsically high, label
  noise is maximal, horizon-20 timeouts dominate, and validation showed zero
  edge at every operating point — all consistent with the PR #413 audit's
  cost-hurdle analysis.
- **Should M1 be closed for the current flagship first-run question?** **Yes.**
- **Should all M1 research be permanently banned?** **No** — but any return to
  M1 requires a materially different hypothesis (microstructure/order-flow
  data, explicit spread-regime modelling) and full pre-registration; minor
  tweaks to this lineage are not a credible path.

**Classification:** `M1_FLAGSHIP_CLOSED_THIS_LINEAGE_FAILED` (this contract
family, decided) + `M1_GENERAL_RESEARCH_DISCOURAGED_BUT_NOT_IMPOSSIBLE`
(near-term) + `M1_GENERAL_RESEARCH_REQUIRES_NEW_HYPOTHESIS` (condition for any
return).

## 12. Improvement-lever analysis

Legend per lever: **[F]** forbidden as same-holdout tuning · **[H]** allowed
future research hypothesis (requires pre-registration) · **[P]** likely
high-value pivot.

### A. Timeframe pivot — [P][H]
M15/H1/H4 improve the cost-to-signal ratio mechanically: ATR-proportional
barriers grow with timeframe while spread is ~constant, so the embedded-cost
fraction of each trade shrinks; event rate drops 15–240×, curing the turnover
gate by construction; label noise falls. The archived Phase 9.16/9.X record
(committed) already demonstrates small-but-positive gross edges at multi-TF
aggregation. **M15 and H1 are the natural next measurement targets; M5 shares
too much of M1's cost profile to be the default.**

### B. Cost-hurdle-aware targets — [P][H]
Labels/targets that require the expected move to clear spread + slippage + a
safety margin (e.g. barrier distances floored at k×spread, or "tradeable move"
classes) directly encode the PR #413 cost-hurdle finding. Avoid trades where
ATR (or predicted move) is small relative to spread. This converts the
economics from an afterthought into the label definition — the single most
direct answer to §10.1.

### C. Empirical spread / liquidity regime — [P][H]
Replace the flat cell with observed per-pair, per-session spread distributions
(the BA archive contains the raw material); exclude high-spread windows
(rollover, illiquid sessions, event spikes); pair-specific cost models. Any
future acceptance gate should be evaluated under empirical cost, not a single
flat cell — the 0.5-pip cell flattered nothing here, but it will matter for
marginal candidates.

### D. Abstention and trade-frequency control — [H]
A stronger no-trade stance: EV-threshold (probability × payoff − cost) instead
of raw class-probability threshold; minimum-predicted-edge gates; explicit
max-turnover constraint; probability calibration before any EV mapping. Note
honestly: on *this* lineage, validation showed no positive region for any
threshold, so abstention alone would have produced ~zero trades rather than
profit — abstention is a multiplier on an edge, not a source of one.

### E. Regime filters — [H]
Trend/range and volatility regimes, session filters, macro-event avoidance.
Same caveat as D: filters can only concentrate an existing edge. The archived
Phase 9.7/9.17 record shows regime weighting produced modest, mixed effects.
Useful as a secondary lever in a pre-registered design; not a rescue mechanism.

### F. Feature improvements — [H]
Plausibly helpful *only* with genuinely new information content: order-book /
tick microstructure, realized-spread and liquidity features, cross-sectional
currency-basket strength, carry/calendar. Marginal recombinations of lagged
OHLC technicals are not a credible M1 rescue (§10.9). **Any feature search must
run on training/validation data of a new protocol — never against the PR #425
holdout.**

### G. Label / objective redesign — [H]
Direct expected-value regression; meta-labeling (edge-on-top-of-trigger);
cost-aware triple barrier (B above); longer-horizon labels; pair-normalized
(ATR- or spread-normalized) targets; ranking objectives. The archived record
(9.X-A regression, 9.12 B-2/B-3) shows label-class changes alone did not flip
economics at higher TFs either — combine with A+B+C rather than as a lone lever.

### H. Portfolio/risk improvements — [H, explicitly not curative]
Correlation-aware exposure caps, pair selection (from training data only),
throttling, daily stops. **Risk controls reduce damage; they cannot create
edge.** With −3.49 pips/trade expectancy, every risk overlay merely shrinks the
bleed. These belong in a future design only after a positive-expectancy core
exists.

## 13. Recommended next research path (not started, not authorised here)

1. **Immediate conclusion:** accept the valid `DOES_NOT_MEET`; **close the M1
   flagship first-run question**; no rerun; no tuning; the `365d_BA` M1 frozen
   holdout is consumed for this lineage.
2. **Next research family (recommended):** an **M15-first (H1 secondary)**
   cost-hurdle-aware family: B-2-style bid/ask barrier labels with
   **spread-floored barriers** (target must clear empirical spread + slippage +
   margin), **empirical per-pair/session cost model** from the BA archive,
   explicit **turnover budget** (≤ ~10–40 trades/day portfolio-wide), EV-based
   (not raw-probability) trade gate with calibration, v4-base features as the
   baseline plus pre-registered feature extensions. Training/validation on
   pre-holdout spans; **a new pre-registered frozen holdout** (either the
   365d_BA holdout span for a *different timeframe contract* — a governance
   decision — or preferably a disjoint epoch under Gate P2 retention rules).
3. **Evidence gate before any future holdout:** the candidate must first show a
   positive **validation** expectancy under the empirical cost model (a
   pre-registered magnitude, e.g. ≥ +0.5 pips/trade net) — no holdout touch
   until that gate passes; the PR #407-style pre-registration (criteria,
   thresholds, one-shot discipline, evidence schema) must be re-issued for the
   new family.
4. **What not to do:** no further M1 threshold/feature tweaks on `365d_BA`; no
   rerun-until-pass; no pair selection or any design choice based on the
   PR #425 holdout; the PR #425 holdout is never a design set.
5. **If M1 is ever revisited:** require a materially new hypothesis —
   order-book/tick microstructure data, explicit liquidity/spread-regime
   modelling, materially different data — with fresh pre-registered
   train/validation/holdout. This M1 flagship lineage is **not salvageable by
   minor tweaks**.

## 14. Decision table

| # | Decision | Recommendation | Rationale | Allowed next step | Forbidden next step |
| --- | --- | --- | --- | --- | --- |
| 1 | Accept corrected evidence validity | **ACCEPT** | one-shot clean; provenance complete; arithmetic airtight; pip fix verified in-run | record validity (this audit) | re-litigating via raw-data recomputation |
| 2 | Close M1 flagship first-run question | **CLOSE (failed criteria)** | valid decisive failure; validation+holdout agree; broad-based | record closure; human+ChatGPT countersign | citing closure as "all M1 impossible" |
| 3 | Continue same M1 lineage | **NO** | holdout consumed; no validation edge existed; tweaks = tuning | archive lineage | any further eval of this lineage on 365d_BA |
| 4 | Start H2/H3 immediately | **NO** | governance sequencing: post-run review first; H2/H3 not authorised | await human+ChatGPT decision | starting H2/H3 from this PR |
| 5 | Start M15/H1/H4 research design | **RECOMMEND (design only, later)** | best cost-to-signal ratio; archived record supports | propose a pre-registration PR **after** this audit is accepted | executing anything before pre-registration |
| 6 | Tune thresholds/features on 365d_BA | **NEVER** | converts frozen holdout into design set | — | any such tuning |
| 7 | Use PR #425 holdout for pair selection | **NEVER** | same contamination | — | any holdout-derived design choice |
| 8 | Build new pre-registered cost-aware protocol | **YES (next concrete step)** | encodes §10 lessons: cost-hurdle labels, empirical spread, turnover budget, EV gate | draft protocol doc for approval | treating a draft as execution authorisation |

## 15. Blockers or invalidators

**None.** The evidence is valid. Non-blocking observations: O-A (§8 —
pair-contribution cell convention should be stated in future report tables);
missing exit-type decomposition in the evidence schema (§10.4 — a candidate
schema addition for any future protocol, not retrofittable here).

## 16. Recommendation

1. Merge this audit (records validity + closure diagnosis).
2. Human + ChatGPT post-run review countersigns: (a) evidence VALID; (b) M1
   flagship first-run question CLOSED as failed against pre-registered
   criteria; (c) the `365d_BA` M1 holdout is consumed for this lineage.
3. Next concrete step, if the review agrees: a **pre-registration design PR**
   for the M15-first cost-hurdle-aware family (§13) — doc-only, separately
   approved, nothing executed.
4. No rerun; no tuning; no H2/H3 start until this audit is accepted by the
   review.

## 17. Non-authorisation statements

This document does **not**: rerun ML Step 4; train models; evaluate holdout;
generate new real metrics; read raw data (all analysis is committed-metadata +
arithmetic); start or authorise any experiment, H2/H3, Phase C2, or the
recommended M15 family; use `730d_BA`/`3650d_BA`; change any contract; access
Google Drive or R2; or claim production readiness. PR #421 invalid evidence,
PR #425 corrected evidence, and PR #409 stop evidence are untouched.
`PRODUCTION_READINESS_NOT_CLAIMED` remains binding.
