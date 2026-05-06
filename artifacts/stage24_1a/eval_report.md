# Stage 24.1a — Both-Side Touch Envelope Eval (Phase 24 path β)

Generated: 2026-05-06T23:14:16.681720+00:00

Envelope contract: `docs/design/ng10_envelope_confirmation.md` (PR #276)

## Mandatory clauses

**Fills follow the NG#10-relaxed envelope confirmed in PR #276; this is a research execution model and not a real-fill guarantee.** Live OANDA fills may differ due to per-tick liquidity, requotes, partial fills, and microstructure latency. Production-readiness still requires an X-v2-equivalent frozen-OOS PR (Phase 22 gating).

**TP fills at the limit price exactly (limits do not slip); SL fills via min(SL, bid_close) for long / max(SL, ask_close) for short (stop-market slippage proxy).** This asymmetry maps to OANDA structural reality (TP=limit / SL=stop-market).

**Same-bar both-hit fills SL using the §3.2 SL formula; the TP fill never occurs in a same-bar both-hit (SL-first invariant from envelope §3.3).** This is a research-model conservatism, not a OANDA semantic.

**All frozen entry streams originate from Phase 23.0d REJECT cells.** Phase 24.1a tests exit-side capture under the relaxed envelope only; it does not reclassify the entry signal itself as ADOPT.

## Scope and inheritance

Strict 24.0b parity: 33 cells = 3 frozen entry streams x 11 trailing variants (4 T1_ATR + 4 T2_fixed_pip + 3 T3_breakeven). Variants imported VERBATIM from `stage24_0b.VARIANTS`. No partial-exit (24.0c) or regime-conditional (24.0d) variants. NG#11 not relaxed. Phase 22 thresholds unchanged. Frozen entries unchanged. 8-gate harness inherited verbatim.

Universe: 20 pairs (canonical 20). Span = 730d.

## Frozen entry streams (imported from 24.0a)

| rank | source | cell_params | Phase 23 verdict | Phase 23 reject_reason |
|---|---|---|---|---|
| 1 | 23.0d (PR #266, d929867) | N=50, horizon_bars=4, exit_rule=tb | REJECT | still_overtrading |
| 2 | 23.0d (PR #266, d929867) | N=50, horizon_bars=4, exit_rule=time | REJECT | still_overtrading |
| 3 | 23.0d (PR #266, d929867) | N=20, horizon_bars=4, exit_rule=tb | REJECT | still_overtrading |

## Headline verdict

**REJECT**

Per-cell verdict counts: 33 REJECT / 0 PROMISING_BUT_NEEDS_OOS / 0 ADOPT_CANDIDATE — out of 33 cells.

REJECT reason breakdown:
- still_overtrading: 33 cell(s)

**Best cell (max A1 Sharpe among A0-passers):** rank 1 (N=50, h=4, exit_rule=tb) x T1_ATR_K=2.5 -> Sharpe -0.1993, annual_pnl -69207.6 pip, capture -0.385

## Routing diagnostic (H1/H2/H3)

Routing hypotheses are FIXED constants set BEFORE this sweep ran. They are routing diagnostics, NOT formal verdicts (the 8-gate harness remains the formal verdict mechanism).

- **H1 (envelope works)**: best Sharpe >= +0.082 (A1 threshold) -> ADOPT_CANDIDATE / PROMISING.
- **H2 (partial rescue)**: best Sharpe lift >= +0.20 vs 24.0b best -0.177 (i.e., new best >= +0.023). REJECT but interesting.
- **H3 (no rescue)**: best Sharpe lift < +0.20. Recommends gamma hard close under current data/execution assumptions.

**Routing diagnostic this sweep: H3**

best Sharpe -0.1993; lift -0.0223 < +0.20. No rescue — envelope does not lift Sharpe meaningfully. Recommends gamma hard close under current data/execution assumptions per envelope §9, unless user requests new data/execution audit.

## Sweep summary (all 33 cells, sorted by Sharpe desc)

| rank_cell | variant | n | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | capture | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r1_N=50_h=4_exit=tb | T1_ATR_K=2.5 | 45229 | 22630.0 | -0.1993 | -69207.6 | 138362.2 | 0/4 | -80522.6 | -0.385 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T1_ATR_K=2.5 | 45229 | 22630.0 | -0.1993 | -69207.6 | 138362.2 | 0/4 | -80522.6 | -0.385 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T2_fixed_pip_30 | 45229 | 22630.0 | -0.2096 | -67328.2 | 134606.0 | 0/4 | -78643.2 | -0.375 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T2_fixed_pip_30 | 45229 | 22630.0 | -0.2096 | -67328.2 | 134606.0 | 0/4 | -78643.2 | -0.375 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T1_ATR_K=2.0 | 45229 | 22630.0 | -0.2172 | -71627.9 | 143190.6 | 0/4 | -82942.9 | -0.398 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T1_ATR_K=2.0 | 45229 | 22630.0 | -0.2172 | -71627.9 | 143190.6 | 0/4 | -82942.9 | -0.398 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T1_ATR_K=2.5 | 73510 | 36780.2 | -0.2181 | -117948.6 | 235783.3 | 0/4 | -136338.7 | -0.439 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T2_fixed_pip_30 | 73510 | 36780.2 | -0.2215 | -112744.6 | 225382.3 | 0/4 | -131134.7 | -0.419 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T1_ATR_K=2.0 | 73510 | 36780.2 | -0.2373 | -122014.2 | 243899.9 | 0/4 | -140404.3 | -0.454 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T2_fixed_pip_20 | 45229 | 22630.0 | -0.2486 | -71990.2 | 143923.6 | 0/4 | -83305.2 | -0.400 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T2_fixed_pip_20 | 45229 | 22630.0 | -0.2486 | -71990.2 | 143923.6 | 0/4 | -83305.2 | -0.400 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T1_ATR_K=1.5 | 45229 | 22630.0 | -0.2540 | -74975.3 | 149880.8 | 0/4 | -86290.3 | -0.417 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T1_ATR_K=1.5 | 45229 | 22630.0 | -0.2540 | -74975.3 | 149880.8 | 0/4 | -86290.3 | -0.417 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T2_fixed_pip_20 | 73510 | 36780.2 | -0.2611 | -120330.6 | 240543.9 | 0/4 | -138720.6 | -0.448 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T1_ATR_K=1.5 | 73510 | 36780.2 | -0.2727 | -126598.1 | 253057.6 | 0/4 | -144988.2 | -0.471 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T3_breakeven_BE=2.0 | 45229 | 22630.0 | -0.2782 | -68076.5 | 136068.7 | 0/4 | -79391.5 | -0.379 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T3_breakeven_BE=2.0 | 45229 | 22630.0 | -0.2782 | -68076.5 | 136068.7 | 0/4 | -79391.5 | -0.379 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T3_breakeven_BE=1.5 | 45229 | 22630.0 | -0.2798 | -68354.6 | 136624.4 | 0/4 | -79669.6 | -0.380 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T3_breakeven_BE=1.5 | 45229 | 22630.0 | -0.2798 | -68354.6 | 136624.4 | 0/4 | -79669.6 | -0.380 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T3_breakeven_BE=1.0 | 45229 | 22630.0 | -0.2936 | -69843.5 | 139588.4 | 0/4 | -81158.5 | -0.389 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T3_breakeven_BE=1.0 | 45229 | 22630.0 | -0.2936 | -69843.5 | 139588.4 | 0/4 | -81158.5 | -0.389 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T3_breakeven_BE=2.0 | 73510 | 36780.2 | -0.3023 | -115492.4 | 230843.7 | 0/4 | -133882.5 | -0.430 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T3_breakeven_BE=1.5 | 73510 | 36780.2 | -0.3037 | -115885.8 | 231629.8 | 0/4 | -134275.8 | -0.431 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T3_breakeven_BE=1.0 | 73510 | 36780.2 | -0.3163 | -117788.5 | 235421.1 | 0/4 | -136178.6 | -0.438 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T1_ATR_K=1.0 | 45229 | 22630.0 | -0.3296 | -78604.8 | 157102.6 | 0/4 | -89919.8 | -0.437 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T1_ATR_K=1.0 | 45229 | 22630.0 | -0.3296 | -78604.8 | 157102.6 | 0/4 | -89919.8 | -0.437 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T1_ATR_K=1.0 | 73510 | 36780.2 | -0.3493 | -132016.6 | 263860.3 | 0/4 | -150406.7 | -0.491 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T2_fixed_pip_10 | 45229 | 22630.0 | -0.3733 | -79131.3 | 158187.1 | 0/4 | -90446.3 | -0.440 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T2_fixed_pip_10 | 45229 | 22630.0 | -0.3733 | -79131.3 | 158187.1 | 0/4 | -90446.3 | -0.440 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T2_fixed_pip_10 | 73510 | 36780.2 | -0.3887 | -133190.5 | 266237.2 | 0/4 | -151580.6 | -0.495 | OK | x | x | x | x | x | still_overtrading |
| r1_N=50_h=4_exit=tb | T2_fixed_pip_5 | 45229 | 22630.0 | -0.6119 | -83326.4 | 166552.7 | 0/4 | -94641.4 | -0.464 | OK | x | x | x | x | x | still_overtrading |
| r2_N=50_h=4_exit=time | T2_fixed_pip_5 | 45229 | 22630.0 | -0.6119 | -83326.4 | 166552.7 | 0/4 | -94641.4 | -0.464 | OK | x | x | x | x | x | still_overtrading |
| r3_N=20_h=4_exit=tb | T2_fixed_pip_5 | 73510 | 36780.2 | -0.6223 | -138717.3 | 277260.1 | 0/4 | -157107.4 | -0.516 | OK | x | x | x | x | x | still_overtrading |

## Reproducibility note

CI uses smoke-mode regression (3-pair subset) for reproducibility checks of 24.0b/0c/0d eval_report.md byte-identicality. Full close-only reproduction is checked locally if feasible. The existing close-only API (`stage23_0a.load_m1_ba`) remains default and backward-compatible — no API change. M1 OHLC fields (bid_h/bid_l/ask_h/ask_l) were already returned by `load_m1_ba` and were previously unused by 24.0b/0c/0d; no fetch step required for 24.1a.

## Phase 24 routing post-24.1a

Per envelope §9, the 24.1a result does NOT auto-route to the next stage. The user must explicitly decide:

- If routing diagnostic is **H1 / verdict ADOPT_CANDIDATE / PROMISING**: candidate next PR is Phase 24.1b (C6 stale-quote gate as follow-up if spread sensitivity is observed).
- If routing diagnostic is **H2**: REJECT but interesting; user decides whether to escalate to a focused investigation or close.
- If routing diagnostic is **H3**: recommends gamma hard close under the current data/execution assumptions, unless user requests new data/execution audit.
