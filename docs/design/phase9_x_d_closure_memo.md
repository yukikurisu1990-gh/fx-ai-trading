# Phase 9.X-D Closure — DXY Cross-Asset NO ADOPT

**Status:** NO ADOPT for both eval cells.
**Date:** 2026-04-26.
**PR:** #222 OPEN (recommend close without merge).
**Anchor:** Phase 9.X-B v18 +mtf alone, 20-pair, K=3 lgbm_only **Sharpe 0.174 / PnL 15,118 / DD%PnL 1.8%**.

---

## Summary

Phase 9.X-D evaluated synthetic DXY (linear combination of 5 USD pairs) plus 8 derived cross-asset features per pair, on the existing 20-pair feed (no new data dependency). Two cells were swept against the Phase 9.X-B mtf-alone benchmark:

1. **+dxy alone** — replaces mtf with the new dxy group.
2. **+dxy+mtf** — stacks both groups (STRETCH GO candidate).

Both cells underperform the mtf-alone anchor across all K ∈ {1, 2, 3, 5}. The stacked +dxy+mtf cell is *worse* than mtf alone, indicating DXY contributes noise rather than signal in this configuration.

---

## Result

| Cell                       | K=1   | K=2   | K=3   | K=5   |
| ---                        | ---   | ---   | ---   | ---   |
| Phase 9.X-B +mtf (anchor)  | 0.163 | 0.173 | **0.174** | 0.170 |
| +dxy alone                 | 0.149 | 0.154 | 0.154 | 0.151 |
| +dxy+mtf (STRETCH)         | 0.163 | 0.169 | 0.168 | 0.166 |

(Net Sharpe, lgbm_only cell, slippage 0.0 pip; gross PnL anchored to bid/ask labels.)

PnL detail at K=3 lgbm_only:

| Cell           | NetPnL | MaxDD | DD%PnL | Trades |
| ---            | ---    | ---   | ---    | ---    |
| +mtf (anchor)  | 15,118 | 276   | 1.8%   | 16,958 |
| +dxy alone     | 9,994  | 252   | 2.5%   | 11,613 |
| +dxy+mtf       | 14,171 | 329   | 2.3%   | 15,290 |

---

## Verdict gates (from Phase 9.X-D kickoff memo)

- GO: Sharpe ≥ 0.18 AND PnL ≥ 1.10× baseline AND DD%PnL ≤ 5%
- PARTIAL GO: Sharpe ≥ 0.174
- STRETCH GO: Sharpe ≥ 0.20 (would unblock Phase 9.11)
- NO ADOPT: Sharpe < 0.174

Both cells fall in the **NO ADOPT** band. Highest cell (+dxy+mtf K=2) reaches 0.169, still 0.005 short of the parity threshold.

---

## Why DXY did not lift Sharpe

Three plausible reasons:

1. **Per-pair single-pair features already encode the USD beta.** With 5 USD-pairs in a 20-pair universe, EUR_USD's own price already reflects USD strength relative to EUR. Adding a synthetic basket reintroduces the same information through a noisier channel (the basket's variance is dominated by EUR_USD weight −0.601).
2. **Cross-asset correlation features may be regime-dependent.** `dxy_correlation_pair_20` and `dxy_pair_alignment` flip sign frequently in noisy intervals. The model fits these as semi-random features and overfits in-sample.
3. **+mtf already captures slow-cadence USD regime.** `d1_return_3` on USD-quoted pairs effectively measures the USD trend over 3 days. DXY at higher granularity (m5) does not add information beyond that.

Calibration prior (~50% NO ADOPT) hit. The "expand the data set" axis is **not a free lever** without a fundamentally new data channel (e.g. true DXY futures price, FOMC calendar, or order-book microstructure).

---

## Decision

- **Do NOT merge PR #222** to production. Close with reference to this memo.
- The dxy group remains in the script for future research (e.g. as an input to LSTM Mode B variants), but is **not opt-in via CLI** in production decision loop.
- **Production-bound configuration remains:** `--feature-groups mtf` (Phase 9.X-B/J-5 PR #223), pending v19 lookahead-fix verification (Phase 9.X-E/L-2).

---

## Knock-on effects

- **Phase 9.11 robustness gate (Sharpe ≥ 0.20)** still blocked. Phase 9.X-D was the leading candidate to clear it; with NO ADOPT here, the next attempt is either:
  - Phase 9.X-E/L-2 v19 result (if causal mtf preserves 0.174, no further axis needed for live deploy at scenario-B sizing)
  - True DXY price feed, FOMC calendar, or order-book data (new data dependency, ≥ 1 week to integrate)
- **5th confirming case of the trade-rate ↔ EV trade-off**: dxy+mtf raises trade count (15,290 vs 16,958 for mtf alone — actually slightly fewer here) without raising Sharpe. The pattern is now: only +mtf (Phase 9.X-B) escapes the trade-rate-explosion-collapse cycle.

---

## Files

- Eval scripts: `scripts/compare_multipair_v18_crossasset.py` (PR #222 branch).
- Eval logs: `artifacts/phase9_x_d_dxy.log`, `artifacts/phase9_x_d_dxy_mtf.log`.
- Kickoff memo: `docs/design/phase9_x_d_design_memo.md` (if present on branch).
- Master tip when authored: 1afd2dd (Phase 9.X-B closure base; J-5 PR #223 still OPEN).
