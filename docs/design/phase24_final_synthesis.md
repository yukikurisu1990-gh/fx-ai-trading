# Phase 24 — Final Synthesis (Exit / Capture Study)

Closure document for Phase 24 (Exit / Capture Study). Doc-only; no
code, no eval, no schema change.

## §1. Phase 24 in one paragraph

Phase 24 inverted Phase 23. Where Phase 23 searched for an entry-signal
class that produced realised positive EV under realistic OANDA-class
spreads (and rejected every tested M5/M15 rule-based class), Phase 24
**fixed** the three best path-EV reservoirs (the top-3 frozen entry
streams from 24.0a, all 23.0d M15 first-touch Donchian h=4) and asked
whether causal exit logic could *rescue* those reservoirs into realised
PnL clearing the 8-gate harness. The answer is **no** — under NG#10
strict close-only execution, NG#11 causal regime tags, frozen Phase
23.0d entry streams, and the 730-day OANDA-class M1 BA dataset, none
of the three exit-side mechanisms tested (trailing-stop / partial-exit
/ regime-conditional) cleared the 8-gate harness.

## §2. Phase 23 ↔ Phase 24 connection

Phase 23 showed that the tested M5/M15 rule-based entry families did
not produce realised positive EV. Phase 24 then tested whether the
best path-EV reservoirs from those rejected entry streams could be
rescued by causal exit logic. The answer was also negative under
NG#10 strict close-only execution.

This is the closure of two complementary searches: Phase 23 over the
entry-signal axis with fixed time-bound exits, and Phase 24 over the
exit-rule axis with frozen path-EV-positive entry streams. Neither
half cleared the 8-gate harness.

## §3. Per-stage verdicts

| Stage | PR | Master tip | Cells | Result |
|---|---|---|---|---|
| 24.0 kickoff | #269 | `48d02e7` | — | Design contract (mandatory clauses; H1/H2 hypotheses) |
| 24.0a path-EV characterisation | #270 | `5ec804e` | 216 | **H1 PASS** — 116 eligible; top-3 frozen (all 23.0d, M15, h=4) |
| 24.0b trailing-stop | #271 | `54bacaf` | 33 | **REJECT** (33/33 still_overtrading) |
| 24.0c partial-exit | #272 | `59bc604` | 27 | **REJECT** (27/27 still_overtrading) |
| 24.0d regime-conditional | #273 | `ec77915` | 27 | **REJECT** (27/27 still_overtrading) |

Total cells evaluated across Phase 24: **303** (216 path-EV characterisation
+ 33 trailing + 27 partial + 27 regime-conditional).

## §4. H1 / H2 narrative

**H1 (path-EV exists in 23-stage REJECT cells)**: PASS at 24.0a.
116 of 216 surveyed cells were path-EV-eligible (best-possible exit
score above the kickoff threshold). The top-3 frozen all originate
from 23.0d (M15 first-touch Donchian, horizon=4) — re-confirming the
finding from Phase 23.0d that M15 Donchian carries the strongest raw
path-EV among tested entry classes, despite being a 23-stage REJECT
on realised PnL.

**H2 (causal exit logic converts path-EV to realised PnL)**:
**REJECT unanimously** at 24.0b/0c/0d.

- H2a (trailing-stop): 33/33 cells `still_overtrading`; best Sharpe -0.177
- H2b (partial-exit): 27/27 cells `still_overtrading`; best Sharpe -0.229; partial firing actively *hurts*
- H2c (regime-conditional): 27/27 cells `still_overtrading`; best Sharpe -0.180

H2c (regime-conditional) is the closest to H2 success — R1 ATR-regime
conditional (-0.180) edges its uniform-control sibling (-0.207) — but
still falls far short of A1 Sharpe ≥ +0.082.

## §5. Cross-stage diagnostic compare

### Best cell per stage (1 row each)

| Stage | Best frozen cell | Best variant | Sharpe | ann_pnl (pip) | Capture |
|---|---|---|---|---|---|
| 24.0b | rank1 (N=50, h=4, exit=tb) | `T1_ATR_K=2.5` | **-0.177** | -62 937 | -0.350 |
| 24.0c | rank1 (N=50, h=4, exit=tb) | `P3_mfe_K=1.5_frac=0.5` | -0.229 | -60 252 | -0.335 |
| 24.0d | rank1 (N=50, h=4, exit=tb) | `R1_v2 (K_low=1.5/K_high=2.5)` | -0.180 | -62 995 | -0.350 |

**Note**: The same frozen cell (rank1, 23.0d N=50 h=4 exit=tb) was the
best-of-stage in all three exit-side stages. This is consistent — it
is the single highest path-EV reservoir 24.0a identified — and rules
out the alternative explanation that 24.0b/0c/0d's REJECT was driven
by selecting different sub-optimal entries per stage.

### REJECT-reason distribution (87 evaluated exit-side cells)

| Reason | Count | Share |
|---|---|---|
| `still_overtrading` | 87 / 87 | 100% |
| `under_firing` | 0 / 87 | 0% |
| `pnl_edge_insufficient` | 0 / 87 | 0% |
| `path_ev_unrealisable` | 0 / 87 | 0% |
| `robustness_failure` | 0 / 87 | 0% |

The unanimous `still_overtrading` classification means every cell
emitted enough trades to clear A0 (annual_trades ≥ 70) but failed at
A1 / A2 / A3 / A4 / A5 simultaneously — i.e. the per-trade EV after
spread cost was insufficient at the firing rates the entry streams
imply. None of the three exit-side mechanisms changed firing rates
enough to break this classification.

### Conditional-vs-uniform finding (24.0d only)

R1 ATR-regime carries some exit-parameter signal (-0.180 vs uniform
-0.207); R2 session and R3 trend do not. This narrows the residual
exit-side signal to volatility-conditioning of the trail distance —
which still falls 0.26 Sharpe-points short of A1.

## §6. NG#10 / NG#11 audit

**NG#10 (close-only execution)**: held throughout 24.0b/0c/0d. All
exit triggers (TP, SL, partial trigger, MFE running max/min, trailing,
regime tag application) are evaluated at M1 bar close only. 24.0d
inherited NG#10 by direct reuse of `stage24_0b._simulate_atr_long/short`
and `stage24_0c._simulate_p1_long/short` — no re-implementation.
**Not relaxed in any stage.**

**NG#11 (causal regime tags)**: held throughout 24.0d. R1 used
23.0a's already-causal `atr_at_entry_signal_tf` (`mid_c.shift(1).rolling(N)`),
R2 used trivially-causal `entry_ts.hour_utc`, R3 used
`slope_5 = mid_c[t-1] - mid_c[t-5]` — the signal bar's own close was
never used. **Not relaxed in any stage.**

The fact that both NGs held throughout, combined with the unanimous
REJECT, is what gives the next-stage routing decision (§8) its weight.

## §7. Mandatory clauses (verbatim)

The following three clauses scope the conclusions of Phase 24. They
are deliberately phrased to avoid over-generalisation beyond the
exact tested envelope.

### Clause 1 — Path-EV vs realised-EV

Path-EV is a property of the signal stream measured against
best-possible exits at M1 close granularity. Phase 24 has confirmed
empirically that path-EV does NOT translate into realised PnL clearing
the 8-gate harness **under NG#10 strict close-only execution, NG#11
causal regime tags, frozen Phase 23.0d entry streams, and the 730-day
OANDA-class M1 BA dataset**.

### Clause 2 — Exit-side route closure

Phase 24.0b/0c/0d exhausted the exit-side improvement route under the
kickoff §5 contracts: trailing-stop, partial-exit, and
regime-conditional exits. All three returned REJECT **under the same
envelope as Clause 1**. The 24.0e exit meta-labeling stage is NOT
triggered per kickoff §5 (no 24.0b/c/d cell ADOPT/PROMISING).

### Clause 3 — Production-readiness preservation

No 24-stage cell graduated past `PROMISING_BUT_NEEDS_OOS` or
`ADOPT_CANDIDATE`. The Phase 22 frozen-OOS gating discipline (any
ADOPT_CANDIDATE still requires X-v2 frozen-OOS PR) is preserved
unbroken. Phase 24 introduced no new production-graduation routes.

## §8. Routing options for the next phase

The closure of Phase 24 leaves three downstream paths. They are
listed in the order of recommended evaluation, not of decisiveness.

### Path α — Phase 25 entry-side return (different feature class)

Restart the entry-signal search on a **different feature universe**
(e.g., realised-volatility breakout, volume / order-book shape if
available, cross-asset DXY/index, fundamental-calendar gate). Reverts
to Phase 23 structure but explicitly tests classes Phase 23 did not
cover. ~2-3 weeks.

### Path β — NG-relaxation review (recommended next step, doc-only)

Open a **small doc-only PR** that audits the eleven NGs (NG#1-11) and
explicitly asks: which NGs, if relaxed in a clearly-bounded and
realistic-execution-compatible way, might admit a positive-EV exit
class that Phase 24 could not test? Candidate examples (to be
evaluated in the doc, NOT pre-decided):

- NG#10 close-only → **TP-side touch-with-partial-fill** while keeping
  SL conservative. Requires: realistic per-pair fill probability, OANDA
  order-type semantic, leakage-risk audit.
- NG#10 → **next-bar-close** vs same-bar-close at trigger (single-bar
  latency).
- NG#11 → admit one regime tag computed from a higher TF (e.g., H1
  realised vol in M15 simulation), provided strict shift(1) and full
  causality audit.

The β PR's deliverable is **a written verdict per candidate**, scoped
strictly: leakage risk, realistic executability under OANDA M1 BA
data, and whether the relaxation could plausibly change Phase
24-style results. **No implementation in the β PR itself.**

If β finds at least one defensible relaxation, a follow-up
implementation PR (a new exit-side stage analogous to 24.0b) becomes
in scope. If β finds none, route to γ.

### Path γ — Hard close (only if β finds no defensible relaxation)

Ship a closure document declaring that, **within the tested envelope
of Clause 1 (NG#10 + NG#11 + frozen 23.0d entries + 730d OANDA M1 BA)**,
the exit-side improvement route is exhausted and pivot research
direction (e.g., longer horizons, different asset class).

γ should NOT be the first path taken because Phase 24 only tested the
NG#10 strict-close-only exit family. FX scalping more broadly, and
the broader exit-logic space, are not falsified by Phase 24.

## §9. Recommendation

1. **Phase 24 is formally closed** with the verdicts in §3.
2. **Next step: open a small doc-only β PR** (NG-relaxation review) to
   evaluate which NG relaxations, if any, admit an exit class Phase 24
   could not test. The β PR must rigorously define leakage risk and
   realistic executability before any implementation follows.
3. If β finds no defensible relaxation, **route to γ hard close**.
4. Path α (Phase 25 entry-side return) remains a parallel option but
   is not the immediate next step; it would be triggered if β confirms
   that the exit axis is exhausted under all realistic NG envelopes.

## §10. Reproducibility appendix

### Sweep counts per stage

| Stage | Cells | Notes |
|---|---|---|
| 24.0a | 216 characterised | 116 path-EV-eligible; top-3 frozen |
| 24.0b | 33 | 3 frozen × 11 trailing variants |
| 24.0c | 27 | 3 frozen × 9 partial-exit variants |
| 24.0d | 27 | 3 frozen × 9 regime-conditional variants |
| **total** | **303** | |

### Rerun commands

Each stage is reproducible from the merged scripts (master tip
`ec77915`):

```bash
python scripts/stage24_0a_path_ev_characterisation.py
python scripts/stage24_0b_trailing_stop_eval.py
python scripts/stage24_0c_partial_exit_eval.py
python scripts/stage24_0d_regime_conditional_eval.py
```

All four scripts use the canonical 20-pair universe and the 730d
OANDA-class M1 BA dataset under `data/`. They write per-stage reports
to `artifacts/stage24_0X/eval_report.md`.

### Reference PRs

| PR | Subject | Master tip |
|---|---|---|
| #269 | docs(phase24): kickoff — Exit / Capture Study | `48d02e7` |
| #270 | research(phase24-0a): path-EV characterisation — H1 PASSES | `5ec804e` |
| #271 | research(phase24-0b): trailing-stop variants — REJECT | `54bacaf` |
| #272 | research(phase24-0c): partial-exit variants — REJECT | `59bc604` |
| #273 | research(phase24-0d): regime-conditional exits — REJECT | `ec77915` |
