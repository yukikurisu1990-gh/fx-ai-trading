# Phase 24 Design Kickoff — Exit / Capture Study

**Date**: 2026-05-06
**Status**: ACTIVE — Phase 24 starting reference
**Predecessor (Phase 23 closing reference)**: `docs/design/phase23_final_synthesis.md`
**Phase 22 analogue (read-only)**: `docs/design/phase22_final_synthesis.md`
**Phase 23 stage references (read-only)**:
- `docs/design/phase23_design_kickoff.md`
- `docs/design/phase23_0a_outcome_dataset.md`
- `docs/design/phase23_0b_m5_donchian_baseline.md`
- `docs/design/phase23_0c_m5_zscore_mr_baseline.md`
- `docs/design/phase23_0d_m15_donchian_baseline.md`
- `docs/design/phase23_0c_rev1_signal_quality.md`

---

## §1 Phase 24 charter

> **Phase 24 is an exit-side study. Entry signals are FROZEN from
> Phase 23 outputs; the search space pivots from entry-signal logic
> (Phase 23) to exit logic (trailing, partial, regime-conditional).
> Phase 24 success = at least one exit configuration converts a known
> path-EV into realised-EV that clears the Phase 22 inherited 8-gate
> harness.**

> **Phase 24 does not try to rescue all Phase 23 rejected entries. It
> only tests whether selected entry streams with measurable path-EV can
> be converted into realised PnL by causal exit logic.** Phase 23
> rejected ~216 strategy cells; only a small subset will be carried
> forward as frozen entry streams (selection by 24.0a multi-metric
> ranking, see §6). The vast majority of Phase 23 cells will NOT be
> revisited in Phase 24, and that is by design.

Phase 23 final synthesis §8 articulated the inversion: *"rather than
searching for an entry signal that captures EV under realistic exits,
Phase 24 fixes the entry stream and searches over exit logic to convert
path-EV into realised PnL."* The charter above operationalises that
inversion. The path-EV vs realised-EV gap (kickoff §10 Phase 23 final
synthesis open question 4) is Phase 24's starting question; whether
exit-side improvements can close it is Phase 24's binding question.

---

## §2 Inheritance from Phase 23

### Inherited unchanged
- **8-gate harness** (A0..A5) with Phase 22 inherited thresholds:
  A0 ann_tr ≥ 70 (overtrading WARN > 1000, NOT blocking),
  A1 Sharpe (ddof=0, no √N) ≥ +0.082,
  A2 ann_pnl ≥ +180 pip,
  A3 MaxDD ≤ 200 pip,
  A4 5-fold split, k=0 dropped, eval k=1..4, count(>0) ≥ 3,
  A5 +0.5 pip stress ann_pnl > 0
- **20-pair canonical universe**; no pair / time-of-day filter
- **Per-trade Sharpe convention** (mean / std with ddof=0; no
  √N annualisation); annualisation uses fixed dataset span
  (`span_years = 730 / 365.25 ≈ 1.9986`)
- **Multiple-testing caveat** + **independent OOS validation** as
  production-migration precondition
- **3-class verdict** (ADOPT_CANDIDATE / PROMISING_BUT_NEEDS_OOS / REJECT)
- **REJECT-reason classification** (under_firing / still_overtrading /
  pnl_edge_insufficient / robustness_failure); a new reason
  `path_ev_unrealisable` may be added for Phase 24 (entry has positive
  path-EV but exit logic cannot capture enough)
- **23.0a M5/M15 outcome dataset** (`labels_M5_<pair>.parquet`,
  `labels_M15_<pair>.parquet`) — read-only input to 24.0a
- **NG list** (8 items from kickoff §4) — see §4 below for inheritance
  + Phase 24 extensions

### New for Phase 24
- **Entry stream is FROZEN** from one or more Phase 23 cells; selection
  by 24.0a multi-metric ranking (see §6)
- **Search space pivots**: from entry-signal cells (Phase 23) to
  **exit-logic cells** (Phase 24). Cell dimensions become exit-rule
  parameters (trailing distance, partial fraction, regime tag, etc.)
- **M1 path simulation**: exit decisions at M1 bar boundaries require
  intra-path simulation that 23.0a outcome columns do NOT directly
  encode. Phase 24 stages MAY need to re-load M1 BA data per pair to
  evaluate trailing / partial / regime-conditional exits at M1 bar
  granularity (TBD per stage PR).
- **New diagnostic columns** may extend 23.0a outputs (e.g., trailing-
  stop trigger position along the path). Specification deferred to per-
  stage PRs; the canonical 23.0a parquets remain read-only.

---

## §3 Hypotheses

- **H1 — Path-EV exists**. Across Phase 23 cells, `best_possible_pnl`
  (path peak after entry-side spread) is meaningfully positive on a
  non-trivial fraction of trades, even when `tb_pnl` / `time_exit_pnl`
  (realised-EV) are negative. **Adjudicated by 24.0a multi-metric
  ranking and pre-declared halt criteria (§7).**
- **H2 — Exit improvements close the gap**. At least one exit logic
  family (trailing, partial, regime-conditional) converts a sufficient
  fraction of `best_possible_pnl` into realised PnL to clear A1
  (`Sharpe ≥ +0.082`) and A2 (`ann_pnl ≥ +180`). **Adjudicated by
  24.0b/c/d.**
- **H3 — Regime conditioning matters**. Exit logic that conditions on
  market regime (ATR / time-of-day / trend) outperforms regime-blind
  variants on the same Phase 23 frozen entry stream. **Adjudicated by
  24.0d vs 24.0b/c.** Regime is used **only** as an exit-parameter
  selector — see §5 24.0d clarification.

If **H1 fails** (24.0a's multi-criteria halt triggers), Phase 24 closes
early with a "no path-EV to capture" conclusion — analogous to Phase
23 path A but at a different mechanism level. If H1 passes but **H2
fails**, Phase 24 closes with "path-EV exists but uncapturable under
tested exit logic" — bounded conclusion that motivates Phase 25+
(model-based exit decisions or longer timeframes).

---

## §4 NG list — Phase 23 inheritance + Phase 24 extensions

### Phase 23 inheritance (unchanged from Phase 22 → 23 → 24)

| # | NG | Phase 24 stance |
|---|---|---|
| 1 | Pair filter (universe-restriction) | inherited; 20-pair canonical |
| 2 | Train-side time filter | inherited; no time-of-day filter at entry |
| 3 | Test-side filter improvement claim | inherited; S1 strict OOS diagnostic-only |
| 4 | WeekOpen-aware sample weighting | inherited; not used |
| 5 | Universe-restricted cross-pair feature | inherited; not used |
| 6 | Phase 22 M1 Donchian-immediate cell reuse | inherited; runtime assertion `signal_timeframe ∈ {M5, M15}` carried forward (NB: Phase 24 frozen entry stream comes FROM Phase 23 23.0b/c/d/c-rev1 cells, which already enforced this) |
| 7 | (Phase 22 specific) | n/a |
| 8 | 22.0a M1 outcome dataset re-fitting | inherited; 23.0a M5/M15 read-only input only |

### Phase 24 extensions

> **NG#9 — Honest Phase 23 entry status reporting.** Phase 24 exit
> cells may use Phase 23-rejected entry signals as their frozen
> stream (this is the entire point — Phase 23 rejected them on
> realised-EV; Phase 24 tests if exit-side improvements salvage
> path-EV). Phase 24 ADOPT verdicts MUST report the entry stream's
> Phase 23 status verbatim in `eval_report.md` (PR number, merge
> commit, Phase 23 verdict, Phase 23 best Sharpe). No "free
> improvement" framing that hides the entry stream's Phase 23
> rejection.

> **NG#10 — Causal exit decisions at M1 bar close (strong rule).**
> All trailing-stop, partial-exit, and regime-conditional exit
> decisions MUST be computed at M1 bar close. **No intra-bar
> favourable ordering, no forward-looking path decisions, no "if
> the high happened before the low" assumptions.** Trailing-stop
> simulation MUST evaluate `trailing_distance` against the M1 close
> price only; partial-exit simulation MUST decide at M1 bar
> boundaries with no peek at the rest of the path. The 23.0a same-bar
> ambiguity resolution (conservative SL priority) carries forward as
> the MAXIMUM intra-bar resolution allowed; any exit logic that
> requires finer than M1 close resolution must be REJECTED at design
> review.

> **NG#11 — Non-forward-looking regime tags.** Regime conditioning
> (ATR regime, time-of-day session, trend regime) MUST use only
> data available at trade entry time. ATR regime tags must use ATR
> computed on bars strictly before the signal bar (causal). Time-of-
> day session tags are ALWAYS available at entry (no leakage). Trend
> regime tags must use a rolling slope / momentum statistic computed
> with shift(1) before the signal. Any regime tag whose value depends
> on data observed AFTER the signal bar (including same-bar) is a
> NG#11 violation and must be REJECTED at design review.

These three NG items extend Phase 22/23's protections to the exit-side
search space. NG#10's strong causality rule is non-negotiable and must
be unit-tested in every Phase 24 implementation PR.

---

## §5 Stage roadmap

| stage | mandatory? | scope |
|---|---|---|
| **24.0a** | mandatory | Path-EV characterisation + frozen entry stream selection (§6). Pre-declared halt criteria (§7) determine whether Phase 24 closes early. |
| **24.0b** | mandatory unless 24.0a halts | Trailing-stop variants on frozen entry stream(s): ATR trailing, fixed-pip trailing, breakeven move. Single-rule sweeps; combinations deferred to 24.0e. |
| **24.0c** | mandatory unless 24.0a halts | Partial-exit variants: 50%-exit at TP/2, time-based (exit X% at horizon midpoint), MFE-triggered exit. Single-rule sweeps. |
| **24.0d** | mandatory unless 24.0a halts | **Regime-conditional exits (NOT entry filters).** ATR regime / time-of-day session / trend regime as **exit-parameter selectors** only — i.e., the regime tag selects WHICH trailing distance or WHICH partial fraction to use, NOT whether the trade fires. See restriction below. |
| **24.0e** | conditional (only if 24.0b OR 24.0c OR 24.0d returns ADOPT_CANDIDATE OR PROMISING_BUT_NEEDS_OOS) | Exit-side meta-labeling (LightGBM on the frozen entry stream's exit decisions). Per Phase 23.0e convention. |
| **24.0f** | mandatory at phase end | Phase 24 final synthesis (analogue of `phase23_final_synthesis.md`). |

### 24.0d regime-conditioning restriction (mandatory)

**24.0d uses regime tags ONLY for exit-parameter selection or exit-rule
choice.** Regime tags MUST NOT be used as entry filters. Specifically:

- Allowed: "if ATR-regime is high-vol, use trailing distance = K1; if
  low-vol, use K2" (regime selects exit parameter)
- Allowed: "if session is Asian, use partial-exit fraction = 0.3; if
  London/NY, use 0.5" (regime selects exit rule)
- **PROHIBITED**: "if session is X, do not enter the trade" (regime as
  entry filter — this is the Phase 22/23 time-gate route that was
  REJECTED)
- **PROHIBITED**: "if ATR-regime is high-vol, drop the signal" (entry-
  side regime filter — same prohibition)

The Phase 22 NG list and Phase 23 audit explicitly rejected time-of-day
and regime-based entry filtering. Phase 24 must NOT revive that route
via the back door of "regime-conditional exits". The `24.0d` stage
contract PR must include a unit test that asserts the regime tag is
referenced ONLY in the exit-parameter selection code path, never in
the entry signal filtering code path.

---

## §6 24.0a — entry stream selection (multi-metric ranking)

Top-K-by-path-EV-gap alone is **insufficient** — a cell with extremely
negative `tb_pnl` and slightly positive `best_possible_pnl` would have
a large gap but would also be a structurally bad bet (the realised
distribution is dominated by losses). 24.0a uses a **multi-metric
ranking** with the following axes:

### Multi-metric ranking axes (24.0a, exact score formula in 24.0a PR)

1. **Positive path-EV magnitude**: `mean(best_possible_pnl)`,
   `median(best_possible_pnl)`, `p75(best_possible_pnl)` — all in pips,
   on valid_label rows only. Cells with all three positive are preferred.
2. **Realised gap**: `mean(best_possible_pnl) - mean(max(tb_pnl,
   time_exit_pnl))` — the upside left on the table by realistic exits.
3. **Risk path**: `mean(mae_after_cost)`, `worst_possible_pnl` quantiles
   (p10, p25). Cells with extreme adverse path excursions are
   penalised even if path-EV is positive.
4. **Sample sufficiency**: `annual_trades >= 70` (Phase 22 A0 minimum).
   Cells below this are EXCLUDED from ranking — they cannot pass A0
   under any exit logic.
5. **Concentration**: per-pair contribution (no single pair > 50% of
   trades), per-fold concentration (each of 4 evaluation folds has
   ≥ 10% of trades). Cells dominated by one pair or one time period
   are penalised.

### Score and K determination

The exact score formula combining the 5 axes and the value of K (top-K)
are **fixed in the 24.0a PR before implementation**, NOT in this
kickoff. The 24.0a PR must:
- Pre-declare the scoring formula and K
- Apply it to all Phase 23 23.0b/c/d/c-rev1 cells (~216 cells)
- Output `artifacts/stage24_0a/frozen_entry_streams.json` with the
  top-K cells, including: PR number, merge commit, cell parameters
  (N, threshold, horizon, exit_rule, filter), and the 5 ranking axis
  values
- 24.0b/c/d/e import this JSON as the canonical source of frozen entry
  streams; no parameter re-search across stages

### 24.0a expected outputs

- `artifacts/stage24_0a/path_ev_characterisation_report.md` (committed)
- `artifacts/stage24_0a/frozen_entry_streams.json` (committed; small)
- `artifacts/stage24_0a/path_ev_distribution.parquet` (gitignored;
  per-cell aggregated stats; summary embedded in report)

24.0a is FOUNDATIONAL for Phase 24 — analogous to 23.0a for Phase 23
— and produces no strategy verdict on its own.

---

## §7 Pre-declared halt criteria (H1 adjudication)

> **Mean path-EV alone is NOT sufficient for Phase 24 early closure.**

If Phase 24 were to close early on `mean(best_possible_pnl) ≤ 0` alone,
it would discard cells where the median is negative but a small
positive tail exists — the exact distribution shape that exit logic is
designed to exploit (cut the losers earlier, ride the rare winners).
Multi-criteria halt avoids that pitfall.

### Halt rule (Phase 24 closes early ONLY if NO candidate cell satisfies ALL of)

1. `annual_trades ≥ 70` (sample sufficiency, Phase 22 A0 minimum)
2. `mean(best_possible_pnl) > 0` (in pips, on valid_label rows)
3. `p75(best_possible_pnl) > 0` (the upper quartile of path peaks is positive)
4. `positive-rate of best_possible_pnl materially above 50%` (the
   fraction of trades with positive path peak exceeds the
   coin-toss baseline by a margin to be fixed in 24.0a)

The exact threshold for criterion (4) — "materially above 50%", e.g.,
≥ 55% or ≥ 60% — is **fixed in the 24.0a PR before implementation**,
not in this kickoff. The 24.0a PR must pre-declare this threshold.

If at least one Phase 23 cell satisfies all 4 criteria, Phase 24
proceeds to 24.0b/c/d. If none do, Phase 24 closes early with an §1-
analogue scope clause (the closure does NOT prove M5/M15 has no
path-EV; it concludes that the rule-based Phase 23 cells we tested
do not exhibit non-trivial positive path-EV under the four criteria).

---

## §8 8-gate harness — Phase 22 inherited, identical to Phase 23

A0 ≥ 70 (overtrading WARN > 1000, NOT blocking), A1 Sharpe ≥ +0.082,
A2 ann_pnl ≥ +180 pip, A3 MaxDD ≤ 200 pip, A4 ≥ 3/4 folds positive,
A5 +0.5 pip stress > 0. S0/S1 diagnostic-only.

Phase 24 may add a **path-EV-aware diagnostic** alongside A0..A5:
`realised_capture_ratio = mean(realised_pnl) / mean(best_possible_pnl)`
— interpretable as "what fraction of path-EV did this exit logic
capture". Diagnostic only; not a gate. Useful for cross-cell comparison.

REJECT-reason classification gains one new reason for Phase 24 stages:
- **path_ev_unrealisable**: cell's frozen entry stream has positive
  `best_possible_pnl` (per 24.0a) but the exit logic cannot capture
  enough — distinct from `pnl_edge_insufficient` (which assumes no
  edge at all)

---

## §9 Production-readiness clause structure

Same structure as Phase 23: even ADOPT_CANDIDATE requires a separate
**24.0X-v2** PR with frozen-cell strict OOS validation before any
production discussion. Independent OOS is mandatory. Per-stage PRs
must include the production-readiness clause verbatim in their
`eval_report.md`.

If Phase 24 produces an ADOPT_CANDIDATE, the per-stage PR notes a
candidate `24.0X-v2` PR scope; production migration discussion happens
only after `24.0X-v2` confirms.

---

## §10 Out-of-scope

- Phase 23-rejected entry signals are **inputs** to 24.0a's selection,
  not re-evaluated as entries
- Model-based entries (LightGBM / LSTM): Phase 25+ scope
- Model-based exits beyond 24.0e: Phase 25+ scope (24.0e is one
  conditional LightGBM stage; further model classes deferred)
- Longer timeframes (M30 / H1): Phase 25+ scope
- New 23.0a-style outcome dataset construction (M30/H1 path data, new
  barrier profiles): NOT planned in Phase 24 kickoff; if needed,
  specified per stage PR
- Live trading / paper trading wiring: Phase 24 stays research-only
- Combining multiple exit rules in a single cell (e.g., trailing +
  partial): deferred to 24.0e (LightGBM can learn implicit
  combinations) or to a follow-up Phase 24+ stage; the 24.0b/c/d cells
  test single-rule families to keep the search space tractable

---

## §11 Document role boundary

- This file is the **canonical Phase 24 starting reference**. All
  Phase 24 stage PRs must cite this kickoff for charter / inheritance /
  NG list / halt criteria
- Per-stage docs (24.0a/b/c/d/e/f) will be added in their own PRs
  with their own design contracts
- Phase 23 final synthesis is **read-only** and unchanged by this PR
- Phase 22/23 docs and artifacts are **read-only** and unchanged
- Contradictions between this kickoff and Phase 23 final synthesis:
  Phase 23 final synthesis wins for Phase 23 closure assertions; this
  kickoff is authoritative for Phase 24 charter and forward routing
- 1 PR = 1 responsibility: this PR adds exactly one new doc file
  (`docs/design/phase24_design_kickoff.md`) and modifies nothing else

---

## §12 Effort estimate (kickoff PR alone)

| item | hours |
|---|---|
| Kickoff doc drafting | 2-3 |
| Cross-reference checks (Phase 22/23 docs, NG list audit) | 0.5 |
| **Total (kickoff PR only)** | **2.5-3.5** |

Per-stage PRs (24.0a/b/c/d/e/f) are downstream and out of scope for
this kickoff PR. Each stage PR will have its own effort estimate in
its own design doc.

---

## §13 Constraints (mirroring Phase 23 kickoff §10)

- doc-only
- 1 new file only (`docs/design/phase24_design_kickoff.md`)
- `src/` not touched
- `scripts/` not touched
- `tests/` not touched
- DB schema not touched
- Existing 22.x / 23.x docs / artifacts unchanged
- 1 PR = 1 responsibility
- No `MEMORY.md` update (matching Phase 22/23 kickoff convention)

Phase 24 starts here. Per-stage PRs follow with the 24.0a multi-metric
ranking PR as the first implementation step.
