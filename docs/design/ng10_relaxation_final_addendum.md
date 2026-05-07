# NG#10 Relaxation Final Addendum (Phase 24 path β closure)

Doc-only addendum that closes the NG#10 relaxation chain (PRs #275 →
#276 → #277) by recording the empirical finding from Phase 24.1a and
updating the post-Phase-24 routing decision tree. **No code, no eval,
no implementation.** Single new file.

This addendum **extends, but does not modify, PR #274** (Phase 24
final synthesis). PR #274's path-B closure stands as recorded; this
addendum adds the β-chain conclusion that PR #274 anticipated as a
follow-up.

This addendum is **NOT γ hard close itself**. γ hard close, if chosen,
is a separate downstream decision that may produce its own closure
doc. This addendum simply consolidates what we now know after running
the C2 envelope through the 8-gate harness, so that any future
decision (γ or new audit) is made against an accurate picture.

## §1. Purpose and framing

Per Phase 24 final synthesis (PR #274), path β was opened to test
whether NG#10 strict close-only execution was the binding constraint
on Phase 24's exit-side REJECT verdicts. The chain proceeded:

1. PR #275 (β review) — enumerated 6 NG#10 relaxation candidates;
   verdict 0 ADOPT / 3 DEFER (C1, C2, C6) / 3 REJECT (C3, C4, C5).
   C2 (both-side touch + SL-first same-bar) identified as
   most-promising DEFER.
2. PR #276 (envelope confirmation) — escalated C2 to
   `ADOPT_FOR_IMPLEMENTATION` (a label deliberately distinct from the
   strategy-evaluation `ADOPT_CANDIDATE` / `ADOPT` gates) under a
   binding 11-section envelope contract: trigger semantics, fill
   semantics, same-bar SL-first invariant, negative list, required
   data, leakage demotion proof, OANDA fill realism mapping, unit-test
   contract, implementation-PR contract.
3. PR #277 (24.1a implementation) — executed Phase 24.0b's trailing-
   stop search under the C2 envelope: 33 cells (3 frozen entry
   streams × 11 trailing variants). Verdict REJECT; routing
   diagnostic H3.

This addendum closes the chain.

## §2. Scope

**In scope**:
- Empirical findings from PR #277 (33/33 REJECT; H3; lift -0.022).
- Falsification scope: which hypotheses about NG#10 are now testable.
- Status update for the 6 β candidates given C2's empirical result.
- Routing options post-#277.

**Explicitly out of scope**:
- γ hard close declaration (user decision; this addendum does not
  declare it).
- NG#11 review (separate axis).
- Phase 25 (path α — entry-side return on different feature class)
  detailed planning.
- Any modification of PRs #275 / #276 / #277 verdicts — those stand
  as recorded.
- Any modification of PR #274 (Phase 24 final synthesis).

## §3. Empirical finding from Phase 24.1a (PR #277)

### §3.1 Numerical comparison

| Metric | 24.0b (NG#10 close-only baseline) | 24.1a (C2 envelope) | Lift |
|---|---|---|---|
| Best variant | T1_ATR_K=2.5 | **T1_ATR_K=2.5 (same)** | — |
| Best frozen cell | rank1 (N=50, h=4, exit=tb) | **rank1 (same)** | — |
| Best Sharpe | **-0.177** | **-0.1993** | **-0.022** (worse) |
| Best annual_pnl (pip) | -62 937 | -69 208 | -6 271 |
| Best capture ratio | -0.350 | -0.385 | -0.035 |
| Cells passing A1 (Sharpe ≥ +0.082) | 0 / 33 | **0 / 33** | unchanged |
| REJECT-reason classification | 33 / 33 still_overtrading | **33 / 33 still_overtrading** | unchanged |
| Routing diagnostic | n/a (baseline) | **H3 — no rescue** | — |

The same frozen cell × same trailing variant was best in both
configurations, ruling out the alternative explanation that 24.1a's
REJECT could be explained by selecting a different sub-optimal cell.

### §3.2 Mechanism interpretation

The C2 envelope INCREASED exit firing rate vs NG#10 close-only —
touched-but-reverted bars triggered exits that NG#10 left running.
However, the touch-triggered fills landed at `min(SL, bid_close)`
(long; mirror for short) — i.e., **at the trigger level or worse** —
which is materially less favorable than NG#10's "let it run to next
bar's close" outcome on average. **Net effect: more exits + worse
fills = small negative Sharpe lift.**

### §3.3 Falsification scope

The hypothesis "*NG#10 strict close-only was the binding constraint*"
is **empirically falsified for the C2 envelope**. Relaxing close-only
to both-side touch with realistic OANDA-mapped slippage did not
unlock the path-EV reservoir 24.0a identified in 23.0d's M15
first-touch Donchian REJECT cells.

Falsification is bounded to the C2 envelope under the current
data/execution assumptions (730d OANDA-class M1 BA dataset, M1 OHLC
only, slippage proxied by close-of-bar). It does not falsify NG#10
relaxation in general — only the specific symmetric-touch + SL-first
+ stop-market-slippage-proxy mapping that PR #276 codified.

## §4. Status of the 6 β candidates after 24.1a

PR #275 verdicted 0 ADOPT / 3 DEFER (C1, C2, C6) / 3 REJECT
(C3, C4, C5). With C2 now empirically tested:

| # | Candidate | β verdict | Post-24.1a status | Rationale |
|---|---|---|---|---|
| C1 | TP-side touch, SL conservative close (asymmetric) | DEFER | **DEFER with downgraded prior** | Formal verdict remains DEFER. Post-24.1a prior is downgraded because C2, the most realistic shared envelope, failed empirically — and C1's asymmetric mapping is structurally more optimistic on TP and more conservative on SL than C2, which in 24.1a corresponds to less rather than more expected lift. |
| C2 | Both-side touch + SL-first same-bar | DEFER → ADOPT_FOR_IMPLEMENTATION | **REJECT (empirical, 24.1a)** | 33 / 33 cells still_overtrading; lift -0.022. Final. |
| C3 | Same trigger, next-bar-open execution | REJECT | unchanged | β PR §6.C3 reasoning still holds (pure latency cannot generate +0.30 lift). |
| C4 | Same trigger, next-bar-close execution | REJECT | unchanged | β PR §6.C4 reasoning still holds (strictly worse than C3). |
| C5 | Worst-of-bar fills (anti-cherry-pick) | REJECT | **REJECT, reinforced** | 24.1a's "more exits at worse prices" mechanism is exactly what C5 systematizes. The empirical observation in §3.2 corroborates the β REJECT. |
| C6 | C2 + stale-quote / wide-spread gate | DEFER | **DEFER with downgraded prior** | Formal verdict remains DEFER. Post-24.1a prior is downgraded because C6 inherits C2's now-empirically-failed touch trigger; the gate could only IMPROVE C2's result by removing bad-spread fills, but the lift required (≥ +0.30 vs C2's -0.1993, i.e., reaching ~+0.10 Sharpe) is implausible from a filter alone. |

**Result**: 0 ADOPT / 2 DEFER with downgraded priors (C1, C6) / 4
REJECT (C2 added; C3-C5 unchanged).

The β review's enumeration of NG#10 relaxation candidates is, after
24.1a, **effectively exhausted under the current data/execution
assumptions**.

## §5. Routing options post-#277

### Option A — γ hard close (recommended default)

Per envelope §9, the routing language for the C2 chain is:

> Recommended default: **γ hard close under current data/execution
> assumptions, awaiting user direction**.

This recommendation is supported by:

- C2 demotion held under PR #276 §5 (MEDIUM → LOW leakage).
- C2 implementation in PR #277 confirmed H3 (33 / 33 REJECT; lift
  -0.022).
- C1 and C6 priors are downgraded (§4).
- C3, C4, C5 already REJECT in β (PR #275); no path forward exists.

If the user accepts γ: a follow-up "Phase 24 hard close" doc (a
SEPARATE NEW PR — this addendum is not that doc) would seal Phase 24
with a finalized verdict including both the path-B (exit-side, PR
#274) and the path-β (NG#10 relaxation) conclusions.

### Option B — New data/execution audit

The β review's six NG#10 candidates are exhausted under current
data/execution assumptions. To reopen the question, the audit axis
must shift away from NG#10 alone.

**These are not recommendations to proceed; they are examples of what
would be required to reopen the question:**

- **Longer span**: increase data span beyond 730d (e.g., 1825d) to
  test whether path-EV reservoir conditions vary with data length.
- **Tick-level data**: replace M1 bar-close granularity with sub-minute
  tick data; escapes the same-bar ambiguity that motivates the SL-first
  invariant.
- **Real broker fill logs**: replace the worst-of-bar slippage proxy
  with measured per-trade slippage from a live OANDA paper account or
  recorded fill history.
- **Different broker / data source**: cross-check on a different
  broker's M1 BA feed; ascertains whether OANDA-specific spread /
  fill structure dominates the verdict.
- **Separate NG#11 review**: NG#11 (causal regime tags) was preserved
  unchanged through the entire β chain. A distinct axis-shift PR
  could open a NG#11 review analogous to NG#10's β PR; this is
  ORTHOGONAL to NG#10 and would be its own enumeration / verdicting
  process.

If the user chooses Option B, none of the above is pre-decided; this
addendum simply enumerates them.

### Option C — Path α: Phase 25 entry-side return

Phase 24's entry × exit study now closes negative on both halves
under current envelopes. Path α (different entry feature class —
realised volatility breakout, volume / order-book shape, cross-asset
DXY/index, fundamental-calendar gate) was deferred at PR #274 and
remains a parallel option independent of NG#10 conclusions. If
Option B is declined, Option C is the natural next non-γ direction.

## §6. Recommendation

Recommended default: **γ hard close under current data/execution
assumptions, awaiting user direction**.

This default is the routing language already codified in envelope §9
(PR #276) and is now empirically supported by the 24.1a result. The
recommendation is **not a unilateral decision** — it is a routing
input that awaits explicit user choice between Options A, B, C
(§5).

## §7. Last-of-its-kind framing

This is the **final NG#10-axis document under the current
data/execution assumptions**. Further NG#10 work requires new data or
a new execution model — see Option B above. Within the current
envelope (730d OANDA M1 BA close-only data, OHLC-bar granularity,
worst-of-bar slippage proxy), the NG#10 axis is exhausted.

This is not a permanent closure of the NG#10 question. It is a
closure of the NG#10 axis under the assumptions that have governed
Phases 22, 23, and 24 to date.

## §8. What this addendum does NOT do

- **Does not declare γ hard close.** That is a user decision; this
  doc presents the routing inputs only.
- **Does not modify PR #275, PR #276, or PR #277 verdicts.** PR #275
  ADOPT / DEFER / REJECT counts stand. PR #276
  `ADOPT_FOR_IMPLEMENTATION` stands as the binding envelope contract.
  PR #277 REJECT stands.
- **Does not invalidate the envelope confirmation contract.** PR
  #276's §3 envelope is the authoritative spec for what was tested
  rigorously; this addendum just records what the test outcome was.
- **Does not modify Phase 24 final synthesis (PR #274).** This
  addendum extends, but does not modify, PR #274. PR #274's
  path-B closure stands as recorded.

## §9. PR chain reference

| PR | Stage | Purpose | Verdict / output |
|---|---|---|---|
| #269 | Phase 24 kickoff | Design contract; H1 / H2 hypotheses | merged |
| #270 | Phase 24.0a | Path-EV characterisation | H1 PASS; top-3 frozen |
| #271 | Phase 24.0b | Trailing-stop variants | REJECT (33/33 still_overtrading) |
| #272 | Phase 24.0c | Partial-exit variants | REJECT (27/27 still_overtrading) |
| #273 | Phase 24.0d | Regime-conditional variants | REJECT (27/27 still_overtrading) |
| #274 | Phase 24 final synthesis | Path-B (exit-side) closure | merged; α/β/γ routing |
| #275 | β review | NG#10 relaxation candidate audit | 0 ADOPT / 3 DEFER / 3 REJECT |
| #276 | β envelope confirmation | C2 binding contract | C2 `ADOPT_FOR_IMPLEMENTATION` |
| #277 | Phase 24.1a | C2 implementation eval | REJECT (33/33); routing H3 |

(Master tips and full commit references are recorded in each
individual PR's commit message; not duplicated here.)

## §10. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/ng10_relaxation_final_addendum.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
`MEMORY.md` update. Existing 22.x/23.x/24.x docs/artifacts:
unchanged. NG#11: not relaxed.**

## §11. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)
