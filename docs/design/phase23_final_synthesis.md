# Phase 23 Final Synthesis — Closing Reference

**Date**: 2026-05-06
**Status**: ACTIVE — Phase 23 closing reference
**Predecessor (Phase 23 starting reference)**: `docs/design/phase23_design_kickoff.md`
**Phase 22 analogue (read-only)**: `docs/design/phase22_final_synthesis.md`
**Stage references (read-only, in chronological order)**:
- `docs/design/phase23_0a_outcome_dataset.md` (PR #263)
- `docs/design/phase23_0b_m5_donchian_baseline.md` (PR #264)
- `docs/design/phase23_0c_m5_zscore_mr_baseline.md` (PR #265)
- `docs/design/phase23_0d_m15_donchian_baseline.md` (PR #266)
- `docs/design/phase23_0c_rev1_signal_quality.md` (PR #267)

---

## §1 Executive summary

Phase 23 closes with **headline verdict REJECT (closure path A)**: across five
stages and ~360 evaluated cells covering naive continuous-trigger Donchian,
first-touch z-score mean-reversion, first-touch Donchian on a longer
timeframe, and a four-filter signal-quality control battery, **no cell
clears the Phase 22 inherited 8-gate harness on the 730-day OANDA M1 BA
dataset**. No production migration is recommended or possible from Phase
23 outputs alone; the conditional 23.0e meta-labeling stage is NOT
triggered (kickoff §5 precondition unmet — no realistic-exit positive-Sharpe
cell to label). The next pivot per kickoff §7 is Phase 24 (Exit / Capture
Study).

> **Phase 23 does not prove that M5/M15-based FX scalping is impossible.
> It rejects the tested rule-based signal families under the current
> 730-day dataset and OANDA-class cost assumptions.** The conclusion
> applies to: (a) the four signal families actually tested
> (M5 continuous Donchian, M5 first-touch z-MR, M15 first-touch Donchian,
> M5 first-touch z-MR with four fixed signal-quality controls);
> (b) the 730-day 20-pair canonical OANDA M1 BA dataset; (c) the Phase 22
> inherited 8-gate harness with `Sharpe ≥ +0.082` and `annual_pnl ≥ +180`
> as the binding clearance bar. It does NOT generalise to model-based
> entries (LightGBM / LSTM), exit-side improvements (Phase 24 scope),
> longer timeframes (M30 / H1, untested in Phase 23), or different cost
> regimes / brokers / datasets.

---

## §2 Phase 23 charter recap (verbatim, kickoff §1)

> **Phase 23 is not a continuation of Phase 22's failed M1/M5 naive route.
> It is a timeframe-pivot study: judgement timeframe is raised to M5/M15,
> while M1 is demoted to execution support.**

The Phase 23 success criterion (kickoff §1) was binary at the harness
level (any single ADOPT cell) and graded at the Phase level (clear
evidence of qualitatively different statistics versus Phase 22).
Adjudication:

- (a) **ADOPT cell**: NOT achieved. Zero cells across five stages.
- (b) **Qualitatively different statistics**: PARTIALLY achieved. The
  M5/M15 cost regime is structurally lighter than M1's (kickoff §3 H1
  validated empirically by 23.0a); trade volume monotonically lower as
  TF rises and as filters tighten; Sharpe directionally less negative.
  All quantities improved versus Phase 22's 22.0c M5 Donchian breakout
  REJECT, but never crossed `Sharpe ≥ +0.082`.

---

## §3 Stage-by-stage outcomes

| stage | PR | merge commit | cells | role / verdict | best Sharpe | best ann_tr |
|---|---|---|---|---|---|---|
| 23.0a outcome dataset | #263 | `ddaaf72` | n/a | **foundation — validation passed (0 WARN, 0 HALT)** | n/a | n/a |
| 23.0b M5 cont. Donchian | #264 | `8d58c42` | 18 | **REJECT** (overtrading) | -0.318 | 105k–250k |
| 23.0c M5 first-touch z-MR | #265 | `cc416e6` | 36 | **REJECT** (still_overtrading) | -0.283 | 43k–157k |
| 23.0d M15 first-touch Donchian | #266 | `d929867` | 18 | **REJECT** (still_overtrading) | -0.162 | 22k–53k |
| 23.0c-rev1 4-filter sweep | #267 | `b90e03d` | 144 | **REJECT — closure path A** | -0.195 (F4) | 8k–80k |

### 23.0a (foundation, NOT a strategy verdict)

23.0a built path-aware outcome datasets at signal timeframes M5 and
M15, on the 730-day OANDA M1 BA data across the 20 canonical pairs.
Validation gates passed: M5 cross-pair median `cost_ratio` 0.573 (in
WARN band 0.40–0.65), M15 cross-pair median 0.319 (in WARN band
0.20–0.45), M15 < M5 < Phase 22 M1 (1.28) ordering preserved, coverage
≥ 97.4% per (pair, TF), sign-convention deviation ≤ 0.15 pip. Schema
22.0a-compatible with the four new column groups (key / price / outcome
/ validity / context / barrier / auxiliary). This stage produced no
strategy verdict — it is foundational data infrastructure for 23.0b/c/d
and any future Phase 23+ stage.

### 23.0b M5 continuous-trigger Donchian breakout (REJECT)

Naive continuous-trigger Donchian on M5 mid-OHLC: `long_break = mid_c >
upper_N` fires every bar the price stays above the band, not only on
the first cross. Sweep N {10, 20, 50} × horizon {1, 2, 3} × exit {tb,
time} = 18 cells. All 18 cells REJECT with 105k–250k annual_trades
(every cell triggers the overtrading warning); per-trade EV dominated
by spread cost (cost_ratio improvement insufficient to offset).
Sharpe range -0.32 to -0.62. **Failure mode recorded: continuous-
trigger Donchian, not "M5 fails"**. This was the lesson that motivated
the Phase 23 commitment to first-touch trigger semantics for all
subsequent rule-based stages.

### 23.0c M5 first-touch z-score mean-reversion (REJECT, still_overtrading)

First-touch trigger semantics applied to z-score MR: `z[t] < -threshold
AND z[t-1] >= -threshold` (rising-edge into negative-extreme zone) with
same-direction re-entry lock (release at `z` back inside threshold
band). Sweep N {12, 24, 48} × threshold {2.0, 2.5} × horizon {1, 2, 3}
× exit {tb, time} = 36 cells. All 36 cells REJECT, all classified
`still_overtrading`. First-touch reduced trade volume 2-5× versus
23.0b but not below the 1000-trade overtrading threshold; Sharpe
range -0.28 to -0.62. **Interpretation note carried forward**: this
REJECT is consistent with insufficient signal firing precision, not
with "M5 z-score MR has no edge". This interpretation became normative
for downstream stages.

### 23.0d M15 first-touch Donchian breakout (REJECT, still_overtrading)

Timeframe-pivot stage: first-touch Donchian on M15 mid-OHLC, with
shift(1) on both `mid_c` and the band itself for causality. Sweep N
{10, 20, 50} M15 bars × horizon {1, 2, 4} × exit {tb, time} = 18 cells
(horizon=4 = 60 min H1-equivalent per kickoff §6.2). All 18 cells
REJECT, all `still_overtrading`. Annual_trades 22k–53k (lowest of the
three base stages); best Sharpe -0.162 (least negative across all
23.0b/c/d). The M15 timeframe + first-touch combination was directionally
the cleanest result, but still well below the +0.082 A1 threshold.

### 23.0c-rev1 four-filter signal-quality control study (REJECT — path A)

Per the routing established in 23.0d §7.2 — since no 23.0b/c/d cell
showed positive realistic-exit Sharpe, the conditional 23.0e meta-
labeling stage was NOT triggered, and 23.0c-rev1 was the next stage
to test fixed (non-search) signal-quality controls. Four filters
evaluated independently:

- **F1 neutral_reset** (re-entry control): release lock at `|z| <= 0.5`
- **F2 cooldown** (time-interval control): 3 M5 bars block per direction
- **F3 reversal_confirmation** (reversal start confirmation): replaces
  first-touch with `z` + `mid_c` co-rising (long) / co-falling (short)
  with neutral-band lock release
- **F4 cost_gate** (per-entry execution-cost sanity gate, NOT a pair
  filter): drop trades where `cost_ratio_at_entry > 0.6`

Sweep 4 × 36 = 144 cells. **All 144 cells REJECT.** Per-filter best
Sharpe: F1 -0.288, F2 -0.282, F3 -0.290, F4 **-0.195** (best across all
of Phase 23). F4-only could have been flagged as a cost-based selection
effect (per design §6.4), but here **all four filters fail**, so the
F4 improvement does NOT change the path-A conclusion. F3 produced the
lowest trade volume (8,457 ann_tr, ~5× vs 23.0c base) — most aggressive
volume reducer — but Sharpe stayed at -0.29.

**Phase 23 closure path A is now empirically supported**: M5/M15 has no
recoverable edge under the four naive rule-based signal-quality controls
tested, even when paired with the lighter cost regime.

---

## §4 Hypotheses adjudication (kickoff §3)

| hypothesis | status | evidence |
|---|---|---|
| **H1** — Cost-regime advantage: per-pair `cost_ratio` (spread / ATR at signal time) is strictly lower at M5 than M1, and lower again at M15 | **VALIDATED** | 23.0a empirical: M5 cross-pair median 0.573, M15 0.319, vs Phase 22 M1 reference 1.28. M15 < M5 < M1 ordering observed across 20/20 pairs at TF level. |
| **H2** — Positive-EV signals exist at the lighter cost regime that did not exist at M1 | **REJECTED** | Across 5 stages and ~216 strategy cells (excluding 23.0a foundation), zero cells clear A1 (`Sharpe ≥ +0.082`) or A2 (`annual_pnl ≥ +180`). The lighter cost regime alone, even paired with first-touch precision and four signal-quality controls, was insufficient. |
| **H3** — Lower false-breakout / firing-burden rate at M5/M15 vs M1 | **PARTIALLY VALIDATED** | Trade volume monotonically lower as TF rises (M5 cont. → M5 first-touch → M15 first-touch → 4-filter sweep): 105k–250k → 43k–157k → 22k–53k → 8k–80k. Sharpe directionally less negative: -0.32 → -0.28 → -0.16 → -0.20 (best). The reduction was real but never sufficient to bridge the gate gap. |

### Sharpe and trade-volume progression (best cell per stage)

```
Sharpe progression (best cell):
  23.0b -0.318   M5 continuous Donchian
  23.0c -0.283   M5 first-touch z-MR
  23.0d -0.162   M15 first-touch Donchian          ← best of base stages
  23.0c-rev1 F4 -0.195   M5 first-touch z-MR + F4 cost gate

Trade-volume progression (best cell, annual_trades):
  23.0b   105k–250k       (cont. trigger overtrades)
  23.0c    43k–157k       (first-touch reduces volume 2-5×)
  23.0d    22k–53k        (M15 TF reduces volume further)
  23.0c-rev1 F3   ~8k     (most aggressive volume reducer)
```

Both metrics improved in the expected direction across the multi-stage
sequence, but the remaining edge gap (~+0.28 Sharpe to clear A1) is too
large to bridge with any combination tested.

---

## §5 Failure-mode taxonomy (unified across stages)

| stage | failure mode | reject_reason classification |
|---|---|---|
| 23.0b | continuous-trigger overtrading; signal duty-cycle ~30%; spread cost dominates per-trade EV | overtrading |
| 23.0c | first-touch reduced volume 2–5× but per-trade EV still negative; insufficient signal firing precision | still_overtrading × 36 |
| 23.0d | M15 cost regime lighter; first-touch on the longer TF; volume halved further; Sharpe least negative; still insufficient | still_overtrading × 18 |
| 23.0c-rev1 | four fixed signal-quality controls (re-entry, time-interval, reversal-confirmation, per-entry cost) fail to produce a positive-EV cell | still_overtrading × 144 |

**Common thread**: per-trade mean PnL stays at -1 to -3 pip across all
configurations. Spread cost (~0.3-1 pip per round trip) is the binding
structural constraint; entry-side precision improvements alone are
insufficient when the entry signal does not capture a directional move
that exceeds 1.5–2× the round-trip spread on average.

---

## §6 NG list compliance final audit (kickoff §4)

The Phase 22 NG list was inherited unchanged. Per-item Phase 23 audit:

| # | NG | Phase 23 audit |
|---|---|---|
| 1 | Pair filter (universe-restriction) | ✓ All five stages used the 20-pair canonical universe with no pair filter |
| 2 | Train-side time filter | ✓ No time-of-day filter applied at any stage |
| 3 | Test-side filter improvement claim | ✓ No claim made; S1 strict 80/20 OOS was diagnostic-only across all stages |
| 4 | WeekOpen-aware sample weighting | ✓ No weighting; `is_week_open_window` excluded from 23.0a outcome dataset per audit allowlist |
| 5 | Universe-restricted cross-pair feature | ✓ No restriction; rule-based stages used per-pair signal generation only |
| 6 | Phase 22 M1 Donchian-immediate cell reuse / re-search | ✓ Runtime assertion `signal_timeframe ∈ {M5, M15}` in every stage's data loader; no `conf` parameter; horizon units M5/M15 (not M1); outcome dataset is 23.0a M5/M15 (not 22.0a M1) |
| 7 | (Phase 22 specific) | n/a |
| 8 | 22.0a M1 outcome dataset re-fitting | ✓ 23.0a built NEW M5/M15 outcome datasets; 22.0a labels read-only context only |

All eight NG items pass the Phase 23 audit.

---

## §7 Production-readiness final clause

**Phase 23 closes with zero ADOPT cells.** No production migration is
recommended or possible from Phase 23 outputs alone. The 23.0c-v2 /
23.0d-v2 / 23.0c-rev2 frozen-cell strict OOS PRs (kickoff §5 / per-stage
production-readiness clauses) are NOT triggered — no ADOPT_CANDIDATE or
PROMISING_BUT_NEEDS_OOS precondition exists in any of 23.0b/c/d/c-rev1.

The 23.0e meta-labeling stage is also NOT triggered per kickoff §5
conditional. The trigger condition was "23.0b/c/d shows at least one cell
with positive realistic-exit Sharpe (does not require ADOPT to trigger;
does require non-trivial signal)". Across 23.0b/c/d/c-rev1 (cumulatively
~216 strategy cells), no realistic-exit Sharpe is positive — the
maximum positive value observed was a cell-internal fold sub-Sharpe
(diagnostic only), never a cell-level Sharpe.

**Repeating the §1 scope clause**: this REJECT applies to (a) the four
rule-based signal families actually tested; (b) the 730-day 20-pair
canonical OANDA M1 BA dataset; (c) the Phase 22 inherited gate
thresholds. It does NOT generalise to model-based entries, exit-side
improvements, longer timeframes (M30 / H1), or different cost regimes.
**The closure does not retire M5/M15 as a research target permanently;
it retires the four specific signal families under the current dataset
and gate thresholds.**

---

## §8 Forward routing — Phase 24 (Exit / Capture Study)

Per kickoff §7: "If both M5 and M15 cells universally land in REJECT or
FAILED_OOS, Phase 23 closes with the same kind of negative-but-bounded
conclusion as Phase 22, and the next pivot becomes Phase 24 (Exit /
Capture Study)."

Phase 23 inverts the question: rather than searching for an entry signal
that captures EV under realistic exits, Phase 24 fixes the entry stream
(e.g., from 23.0a path-EV best cell or any 23.0b/c/d/c-rev1 cell with
positive `best_possible_pnl`) and searches over exit logic to convert
path-EV into realised PnL.

### Rough Phase 24 stage roadmap (subject to Phase 24 kickoff PR confirmation)

| stage | rough scope |
|---|---|
| **24.0a** | path-EV characterisation: histogram of `best_possible_pnl`, `mfe_after_cost`, `worst_possible_pnl`, `mae_after_cost` across 23.0a outputs; identify cells/pairs with non-trivial path-EV; quantify the path-EV-vs-realised-PnL gap that all of Phase 23 left on the table |
| **24.0b** | trailing-stop variants: ATR trailing, fixed-pip trailing, breakeven move; sweep parameters; 8-gate eval |
| **24.0c** | partial-exit variants: 50%-exit at +TP/2, 50%-exit at horizon midpoint; 8-gate eval |
| **24.0d** | regime-conditional exits: ATR regime, time-of-day regime, session regime; 8-gate eval |
| **24.0e** | exit-side meta-labeling (triggered conditionally): apply meta-labeling to exit decisions if any 24.0a–c–d cell ADOPT/PROMISING |

**Detail TBD in Phase 24 kickoff PR.** This roadmap is rough and may be
revised before Phase 24 begins; the precise stage indexing, cell counts,
and trigger conditions are deferred to that PR.

### What Phase 24 inherits from Phase 23

- 8-gate harness (A0..A5) with Phase 22 inherited thresholds
- 20-pair canonical universe; no pair / time filter
- 23.0a M5/M15 outcome datasets (path columns are the input to 24.0a)
- NG list (8 items), with NG#6 likely needing extension for "exit-side
  Phase 22 cell reuse" (Phase 24 kickoff to specify)
- Per-trade Sharpe convention (ddof=0, no √N annualisation)

### What is new for Phase 24

- Search space pivots from entry signal to exit logic
- Entry stream is fixed (one or more 23.0b/c/d/c-rev1 cells frozen)
- New diagnostic columns may need to extend 23.0a (e.g., trailing-stop
  triggers along the path) — TBD in Phase 24 kickoff

---

## §9 Methodological learnings (carried forward)

- **Negative results are findings, not failures.** The five-PR Phase 23
  sequence produced unambiguous evidence for the (1) "cost regime alone
  insufficient" vs (2) "no recoverable edge under stronger controls"
  failure-mode distinction. Closure path A is a substantive output.
- **First-touch as Phase 23 default.** Continuous-trigger signaling
  overtrades; first-touch is the rule-based-stage default that all
  subsequent Phase 23+ stages should adopt.
- **Multi-stage PR sequence with merge gates.** Each stage merged before
  the next started; closure logic (kickoff §5 / per-stage routing
  notes) determined whether 23.0e or 23.0c-rev1 was the next pivot.
  This protocol kept the per-PR scope small (1 PR = 1 responsibility)
  and made the cumulative reasoning auditable.
- **Multiple-testing discipline.** 23.0c-rev1's 144-cell sweep was
  diagnostic-only; even hypothetical PROMISING would have required
  23.0c-rev2 frozen-OOS before any production discussion. The same
  discipline applies forward to Phase 24.
- **Cost regime improvement is necessary but not sufficient.** M5/M15
  `cost_ratio` ~50% / ~30% vs M1's 128% — a structural improvement —
  was insufficient on its own to extract positive EV under naive rule-
  based signaling. This negative result narrows the Phase 24+ search
  space.
- **Failure-mode interpretation is normative.** The 23.0c REJECT was
  *not* "M5 z-score MR has no edge"; it was "first-touch alone
  insufficient signal firing precision". 23.0d adopted that
  interpretation; 23.0c-rev1 tested it directly with four fixed
  controls. The closing conclusion (no recoverable edge under the
  four tested controls) is itself bounded — see §1 scope clause.

---

## §10 Open questions for Phase 24+

1. **Entry meta-labeling on path-EV-positive cells.** Phase 23.0e was
   conditional on 23.0b/c/d producing positive realistic-exit Sharpe and
   was NOT triggered. A Phase 25+ stage could trigger meta-labeling on
   `best_possible_pnl > 0` cells (i.e., path-EV positive even if
   realised-EV negative) to test whether ML-based entry filtering can
   bridge the path-vs-realised gap.
2. **Exit-side improvements (Phase 24 scope).** Can trailing stops,
   partial exits, or regime-conditional exits convert the path-EV that
   23.0a recorded into realised PnL that clears the 8-gate harness?
3. **Longer timeframes (M30 / H1, untested in Phase 23).** Phase 23 stopped
   at M15 per kickoff §6.2. A Phase 26+ stage could extend to M30 / H1
   if the path-EV-vs-realised gap motivates it.
4. **Path-EV vs realised-EV gap quantification.** How large is the gap
   between `best_possible_pnl` (path peak after spread) and `tb_pnl` /
   `time_exit_pnl` (realistic exits) across 23.0a outputs? This is the
   24.0a starting question and adjudicates whether Phase 24 has any
   chance of closing the gap.

---

## §11 Memory and handoff

- **No `MEMORY.md` entry is added by this PR**, matching the Phase 22
  final synthesis convention. Phase 23 closure context is captured here
  in this synthesis doc; future sessions reading the codebase will find
  it via the `docs/design/` directory.
- The Phase 22 final synthesis (`docs/design/phase22_final_synthesis.md`)
  served as the reference template for this synthesis and is **read-only**
  — Phase 22 docs are NOT modified by this PR.
- Future Phase 24+ kickoff docs may cite this synthesis as their
  "Phase 23 closing reference" instead of citing individual stage docs.

---

## §12 Document role boundary

- This file is the **canonical Phase 23 closing reference**. All future
  Phase 24+ docs that refer to Phase 23 conclusions must cite this
  synthesis instead of individual stage docs.
- Per-stage docs (23.0a / 23.0b / 23.0c / 23.0d / 23.0c-rev1) are
  read-only references; this synthesis does NOT modify them.
- The Phase 22 final synthesis is read-only and unchanged by this PR.
- Contradictions between this doc and the kickoff: the kickoff wins for
  charter / scope / NG list (those are the stable contract); this
  synthesis is authoritative for OUTCOMES and FORWARD ROUTING.
- 1 PR = 1 responsibility: this PR adds exactly one new doc file and
  modifies nothing else (no `src/`, no `scripts/`, no `tests/`, no DB
  schema, no existing docs / artifacts).

Phase 23 closes here. Next: Phase 24 (Exit / Capture Study) kickoff
PR.
