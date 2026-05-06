# NG#10 Relaxation Envelope Confirmation (Phase 24 path β follow-up)

Doc-only contract that escalates **C2 (both-side touch with SL-first
same-bar policy)** from DEFER to **ADOPT_FOR_IMPLEMENTATION**, per the
β review (PR #275). **No code, no eval, no implementation in this
PR.** This document is the binding envelope that any subsequent
implementation PR must obey.

> **Naming convention**: this PR uses the verdict label
> **`ADOPT_FOR_IMPLEMENTATION`** (or equivalently "C2 is approved for a
> bounded implementation PR") **deliberately distinct from the
> strategy-evaluation `ADOPT_CANDIDATE` / `ADOPT` gates** used by the
> 8-gate harness. ADOPT_FOR_IMPLEMENTATION authorises the implementation
> PR to execute against the envelope below; it does NOT pre-approve
> any strategy verdict the implementation will yield.

## §1. Purpose and routing

The β PR (#275) found 0 ADOPT / 3 DEFER / 3 REJECT among the six NG#10
relaxation candidates. C2 was identified as the most-promising DEFER,
gated on four prerequisites (data extension, same-bar policy, OANDA
fill realism, leakage demotion). This envelope-confirmation PR
addresses all four prerequisites in a single binding doc.

Two outcomes:

- **C2 demotes MEDIUM → LOW under §5 invariants** AND **§4.3
  reproducibility pre-audit passes** → C2 envelope verdict is
  **ADOPT_FOR_IMPLEMENTATION**; the next PR is a Phase 24.0b-analog
  implementation against the §3 envelope.
- **§5 demotion fails** OR **§4.3 reproducibility cannot be guaranteed**
  → recommend **γ hard close under the current data/execution
  assumptions, unless the user explicitly requests a new
  data/execution audit**.

## §2. Scope

**In scope**:

- C2 envelope only (both-side touch with SL-first same-bar policy).
- The four C2 prerequisites listed in β PR §6/§8.

**Explicitly out of scope**:

- C1 (asymmetry justification not pursued; see §10 for status).
- C6 (deferred until C2 settles; see §10 for short follow-up note).
- C3, C4, C5 (REJECTed in β PR §7; not revisited).
- NG#11 (causal regime tags) — not relaxed.
- Phase 23 entry-axis revision (path α) — independent.
- Frozen entry stream selection — still 24.0a top-3.

## §3. C2 envelope (binding contract)

Every clause below is a binding invariant for the implementation PR.

### §3.1 Trigger semantics (both-side touch)

| Position | Trigger condition |
|---|---|
| Long TP | `bid_high[t] >= TP` |
| Long SL | `bid_low[t] <= SL` |
| Short TP | `ask_low[t] <= TP` |
| Short SL | `ask_high[t] >= SL` |

Trigger is evaluated *only* against bar `t`'s OHLC. No use of `t-1`
or `t+1` data. Trigger never uses information published after bar
`t`'s close.

### §3.2 Fill semantics (research execution model, NOT real-fill guarantee)

The fill model below is **the research execution model used to
falsify or confirm C2's plausible Sharpe lift**. It is asymmetric in
slippage — TP fills exactly at the limit price; SL fills with a
worst-of-bar slippage proxy at close — because that asymmetry maps
to OANDA's structural fill mechanics (TP=limit / SL=stop-market).

> **Important caveat**: this is a *research execution model*, not a
> real-fill guarantee. Live OANDA fills may differ from this model
> due to per-tick liquidity, requotes, partial fills, and
> microstructure latency. The model is constructed to be (a)
> directionally consistent with OANDA reality and (b) conservative
> on the SL side. Production-readiness still requires an
> X-v2-equivalent frozen-OOS PR (Phase 22 gating) before any live
> deployment, regardless of what the C2 implementation PR's verdict
> is.

| Position | Fill price | OANDA mapping (informational) |
|---|---|---|
| Long TP | **exact TP** | Take-Profit limit; limits do not slip |
| Long SL | `min(SL, bid_close[t])` | Stop-Loss stop-market; close-of-bar is a conservative slippage proxy |
| Short TP | **exact TP** | Limit (buy-to-cover); limits do not slip |
| Short SL | `max(SL, ask_close[t])` | Stop-market; close-of-bar is the conservative slippage proxy |

### §3.3 Same-bar ambiguity policy (SL-first; non-negotiable)

If a single bar `t` has both `bid_high[t] >= TP` AND `bid_low[t] <= SL`
for an open long position (mirror for short):

| Position | Same-bar fill |
|---|---|
| Long both-hit | fill at `min(SL, bid_close[t])` (SL formula from §3.2) |
| Short both-hit | fill at `max(SL, ask_close[t])` |

The TP fill never happens for that trade. This is a hard
non-negotiable invariant. Per user direction, fixing the same-bar
fill at `bid_low` (long) / `ask_high` (short) regardless of close is
explicitly NOT used here — SL-first with the §3.2 SL formula is
sufficient conservatism without being overly pessimistic.

### §3.4 Negative-list (prohibitions)

The implementation PR MUST NOT:

- Use `bid_high`, `bid_low`, `ask_high`, or `ask_low` at bar `t-1` or
  `t+1` for triggering a fill at bar `t`. Trigger is bar-`t`-local
  only.
- Fill TP at any price *more favorable* to the trader than TP exact
  (e.g., long TP must never fill above TP).
- Fill SL more favorably than the §3.2 SL formula (e.g., long SL must
  never fill above SL when `bid_close < SL`).
- Apply touch-trigger TP and close-only-trigger SL together — that is
  C1, REJECTed in β.
- Skip a bar based on intra-bar path observation (no path
  cherry-pick).
- Use M1 OHLC for any purpose other than (a) the four §3.1 trigger
  conditions and (b) the §3.2 SL slippage proxy.
- Modify NG#11 — regime tags must remain causal.
- Modify the frozen entry streams from 24.0a top-3.
- Modify Phase 22 8-gate harness thresholds.

## §4. Required data

### §4.1 OANDA M1 bid/ask OHLC specification

| Field | Type | Used by |
|---|---|---|
| `bid_o` | float | (not used by envelope; included for completeness) |
| `bid_h` | float | Long TP trigger |
| `bid_l` | float | Long SL trigger |
| `bid_c` | float | Long SL fill (existing close field) |
| `ask_o` | float | (not used) |
| `ask_h` | float | Short SL trigger |
| `ask_l` | float | Short TP trigger |
| `ask_c` | float | Short SL fill (existing close field) |

Universe: canonical 20 pairs. Span: 730d. Cadence: M1.

### §4.2 Pipeline integration plan (carried into implementation PR, NOT this PR)

The implementation PR (NOT this envelope PR) must:

1. Extend `stage23_0a.load_m1_ba` (or add a sibling
   `load_m1_ba_ohlc`) with an opt-in flag returning OHLC. **The
   default API stays close-only — backward compatibility is mandatory**
   (see §4.3).
2. Source OHLC from OANDA M1 candles (already used in
   `scripts/fetch_oanda_candles.py`); store under
   `data/M1_OHLC/<pair>/...` parallel to the existing close-only
   store.
3. Document storage cost (~2x close-only) and fetch wall time.
4. The envelope-confirmation doc itself does not specify storage
   format details (parquet schema, partitioning) — the implementation
   PR's design memo must.

### §4.3 Reproducibility preservation (non-negotiable)

The implementation PR must guarantee:

- **Phase 22.x and 23.x scripts continue using the close-only API by
  default and remain source-compatible.** Byte-identical artifact
  reproduction is NOT required for 22.x / 23.x — but source
  compatibility is.
- **Phase 24.x stages (24.0b / 24.0c / 24.0d) must reproduce
  byte-identical eval_report.md** (excluding the
  `Generated:` timestamp line) when re-run on the close-only API
  with the existing scripts and the existing artifacts. This is the
  hard reproducibility requirement.
- A regression test re-runs 24.0b/0c/0d and checks
  byte-identicality of eval_report.md modulo timestamp.

If §4.3 cannot be guaranteed (e.g., the data extension subtly
changes a numpy hash or a sort order anywhere in the close-only
path), the envelope FAILS and routing reverts to γ recommendation
per §1/§9.

## §5. Leakage demotion proof (MEDIUM → LOW)

The β PR §6 audit flagged C2 vanilla as MEDIUM-leakage on these
axes. The §3 envelope addresses each:

| Leakage type | β-MEDIUM source | §3 envelope mitigation | Residual |
|---|---|---|---|
| Lookahead | (already absent in C2) | §3.4 prohibits `t-1` / `t+1` use | none |
| Path cherry-pick (TP side) | β assumed implicit slippage waiver on touch | §3.2 TP=limit reflects OANDA reality (limits do not slip); not cherry-pick | none |
| Path cherry-pick (SL side) | favorable touches counted at exact SL | §3.2 worst-of-{SL, close} models stop-market slippage; sub-optimal fills no longer cherry-picked | none |
| Implicit slippage waiver | both sides assumed exact fill | TP=limit (genuinely no slippage); SL=stop-market with close-slippage proxy | none |
| Optimistic latency | (already absent in C2) | no latency assumed; fills occur at bar `t` close — same as NG#10 | none |
| Asymmetric optimism | β concern: EV tilted upward by asymmetric fills | Asymmetry MATCHES OANDA structural reality (TP=limit, SL=stop-market). Not optimism — structural fact. | none |

**Result**: every row's residual = none → **A1 demotes from MEDIUM
to LOW**.

If any reviewer disagrees with the demotion of any specific row
(e.g., they argue that "TP=limit fills exactly" still constitutes
path cherry-pick because the touch detection itself is
path-dependent), this envelope-confirmation PR cannot be merged.
Resolution requires either (a) a strengthened §3.2 (e.g., apply
worst-of-bar to TP as well, accepting beyond-OANDA conservatism), or
(b) C2 stays DEFER and routing reverts to γ recommendation per §9.

## §6. OANDA fill realism mapping

| §3 fill | OANDA order type | Realism note |
|---|---|---|
| Long TP at exact TP | Take-Profit ON FILLED ORDER (limit) | Limits do not slip on standard OANDA; TP fills at the limit price upon touch |
| Long SL at `min(SL, bid_close)` | Stop-Loss ON FILLED ORDER (stop-market) | Stop-market fills at next-tick price; close-of-bar is a per-bar conservative proxy |
| Short TP at exact TP | TP limit (buy-to-cover) | Same |
| Short SL at `max(SL, ask_close)` | SL stop-market (buy-to-cover stop) | Same |
| Same-bar both-hit → SL fill | (no specific OANDA semantic; modeling choice) | Conservative; protects against unobservable intra-bar order |

The "same-bar both-hit → SL" line is **not** an OANDA semantic — it
is a modeling conservatism. The implementation PR's eval_report.md
must call this out explicitly to readers so they understand it is a
research-model choice, not a OANDA behavior.

## §7. Unit-test contract

The implementation PR MUST include at minimum these tests
(this envelope-confirmation PR documents them; the implementation PR
writes the actual test code):

### §7.1 Trigger boundary tests (4 tests)

1. `test_long_tp_touch_no_close_above_fills_at_tp` — `bid_h>=TP`,
   `bid_c<TP` → fill at TP (exact).
2. `test_long_tp_no_touch_no_fill` — `bid_h<TP` → no TP fill.
3. `test_short_tp_touch_no_close_below_fills_at_tp` — mirror long #1.
4. `test_short_tp_no_touch_no_fill` — mirror long #2.

### §7.2 SL slippage proxy tests (4 tests)

5. `test_long_sl_touch_close_above_fills_at_sl` — `bid_l<=SL`,
   `bid_c>SL` → fill at SL (exact, since `min(SL, bid_close) = SL`).
6. `test_long_sl_touch_close_below_fills_at_close` — `bid_l<=SL`,
   `bid_c<SL` → fill at `bid_c` (slippage; `min(SL, bid_close)`).
7. `test_short_sl_touch_close_below_fills_at_sl` — mirror long #5.
8. `test_short_sl_touch_close_above_fills_at_close` — mirror long #6.

### §7.3 Same-bar SL-first invariant (2 tests; HARD invariants)

9. **`test_same_bar_both_hit_long_fills_at_sl_formula`** —
   `bid_h>=TP` AND `bid_l<=SL` → fill at `min(SL, bid_close)`. **MUST
   never fill at TP.**
10. `test_same_bar_both_hit_short_fills_at_sl_formula` — mirror.

### §7.4 No-lookahead invariants (2 tests)

11. `test_no_lookahead_t_minus_1_unused` — synthetic data where
    `bid_h[t-1] >= TP` but `bid_h[t] < TP`; expect no fill at `t`.
12. `test_no_lookahead_t_plus_1_unused` — synthetic data where
    `bid_h[t+1] >= TP` but `bid_h[t] < TP`; expect no fill at `t`.

### §7.5 Data API backward compatibility (2 tests)

13. `test_load_m1_ba_default_is_close_only` — existing API returns no
    OHLC columns by default.
14. `test_load_m1_ba_ohlc_opt_in` — opt-in API returns the eight OHLC
    columns specified in §4.1.

### §7.6 Phase 24 reproducibility regression (3 tests)

15. `test_24_0b_close_only_reproduction` — re-run 24.0b on close-only
    API; eval_report.md byte-identical (excluding `Generated:`
    timestamp).
16. `test_24_0c_close_only_reproduction` — same.
17. `test_24_0d_close_only_reproduction` — same.

**Total minimum tests: 17.**

## §8. Implementation-PR contract

The implementation PR (next-next PR after this envelope confirmation
merges) must:

### §8.1 Identity

- Named e.g. `Phase 24.1a — both-side-touch envelope eval` (analogous
  to 24.0b but on the relaxed envelope).
- Add the M1 OHLC data extension per §4.
- Add a NEW eval script `scripts/stage24_1a_both_side_touch_eval.py`
  that imports stage24_0b's structure but uses the §3.2 fill
  semantics on the §3.1 trigger semantics.

### §8.2 Sweep size — strict 24.0b parity

| Dimension | Count | Source |
|---|---|---|
| Frozen entry streams | 3 | 24.0a top-3 (frozen, immutable) |
| Trailing variants | 11 | Same 11 ATR-K variants as 24.0b |
| **Total** | **33 cells** | Strict 24.0b parity |

The implementation PR **MUST NOT** include partial-exit (24.0c) or
regime-conditional (24.0d) variants under the relaxed envelope. The
purpose of Phase 24.1a is to isolate the C2 envelope effect on the
24.0b trailing equivalent alone. If 24.1a verdicts ADOPT_CANDIDATE /
PROMISING_BUT_NEEDS_OOS, follow-up PRs may consider partial / regime
under the same envelope — but those are NOT in the 24.1a scope.

### §8.3 Gates and frozen contracts

- 8-gate harness inherited verbatim from Phase 22 (Sharpe ≥ +0.082,
  ann_pnl ≥ +180 pip, MaxDD ≤ 200, A4 ≥ 3/4, A5 +0.5 stress > 0).
- Frozen entry streams unchanged.
- `signal_timeframe == "M15"` runtime assertion preserved.
- 8 mandatory unit tests from §7.1–§7.4 + 2 from §7.5 + 3 from §7.6
  + any 24.0b-analog tests = ≥ 17 unit tests minimum.
- Generates `artifacts/stage24_1a/eval_report.md` with mandatory
  clauses verbatim, including a NEW clause:
  *"fills follow the NG#10-relaxed envelope confirmed in PR
  #&lt;envelope-confirmation-PR-#&gt;; this is a research execution model and
  not a real-fill guarantee."*

### §8.4 Implementation-PR prohibitions

The implementation PR MUST NOT:

- Modify the frozen 24.0a entry streams.
- Modify Phase 22 thresholds.
- Add candidates beyond the §3 envelope (no C1 fills, no C6 gate, no
  C5 worst-of-bar TP fill).
- Use stage24_0b's `_simulate_atr_*` functions directly without an
  adapter that injects OHLC fields.
- Modify NG#11.
- Touch existing 22.x/23.x/24.x docs/artifacts (additive only).

## §9. Routing logic

| Outcome of envelope confirmation | Next move |
|---|---|
| §5 demotion holds (all rows residual = none) AND §4.3 pre-audit passes | Merge envelope; **C2 envelope verdict: `ADOPT_FOR_IMPLEMENTATION`**; open Phase 24.1a |
| §5 demotion contested by reviewer | Either strengthen §3.2 (e.g., worst-of-bar TP) or stay DEFER → recommend γ hard close per below |
| §4.3 reproducibility cannot be guaranteed | Envelope cannot proceed → recommend γ hard close per below |
| Any of the §8 prohibitions cannot be honored | Envelope cannot proceed → recommend γ hard close per below |

**γ hard-close trigger language (softened per direction)**:

> If C2 demotion fails or §4.3 reproducibility cannot be guaranteed,
> we **recommend γ hard close under the current data/execution
> assumptions**, **unless the user explicitly requests a new
> data/execution audit** that re-evaluates the assumptions
> themselves (e.g., a different data source, a different OANDA fill
> model, or a relaxation of §4.3's byte-identical reproducibility
> requirement).

The recommendation is not a unilateral decision; it is a routing
input awaiting user direction.

## §10. C6 follow-up note (informational)

C6 (C2 + stale-quote / wide-spread gate) was DEFERred in β PR §6.
This envelope-confirmation PR does **not** address C6.

> If the Phase 24.1a (C2) implementation shows
> PROMISING_BUT_NEEDS_OOS or ADOPT_CANDIDATE but is sensitive to
> spread spikes (e.g., A5 stress fails or per-bar spread variance
> drives the residual REJECTs), C6 may be considered as a follow-up
> PR (Phase 24.1b). C6 is not part of the C2 envelope confirmation.

C1 (asymmetric TP-touch / SL-close) is not pursued because the §3.2
asymmetry already captures OANDA's structural fill mechanics in a
way that maps cleanly onto OANDA reality; C1's distinct asymmetry
(TP-touch + SL-close, where SL-close is *conservative beyond* OANDA
reality) does not offer a path to LOW leakage.

## §11. Files to create

| Path | Status | Lines |
|---|---|---|
| `docs/design/ng10_envelope_confirmation.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No `scripts/`
entry. No `src/` change. No DB schema change. No MEMORY.md update.
Existing 22.x/23.x/24.x docs/artifacts: unchanged. NG#11: not
relaxed.**

## §12. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing 71+ Phase 24 tests untouched)
- Markdown not lint-checked by ruff in this repo.

## §13. Verdict and signature line for the next PR

If this envelope confirmation merges with §5/§4.3 holding:

> **C2 envelope verdict: `ADOPT_FOR_IMPLEMENTATION`** — Phase 24.1a
> may begin under the §3 envelope, the §4 data extension, the §7
> unit-test contract, and the §8 implementation-PR contract. The
> implementation's strategy verdict (8-gate harness output) is
> independent of this approval and follows the same Phase 22/23/24
> rigor as prior stages.
