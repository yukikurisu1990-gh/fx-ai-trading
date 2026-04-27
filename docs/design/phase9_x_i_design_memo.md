# Phase 9.X-I Design Memo — Risk-based Position Sizing in Backtest + Production

**Status:** kickoff. Implementation in progress.
**Date:** 2026-04-27.
**Anchor:** Phase 9.X-E v19 causal +mtf K=3 SELECTOR — Sharpe 0.158 / PnL 11,414 pip / DD%PnL 2.1%.
**Goal:** make risk-based sizing visible in backtest (¥-based Sharpe), then wire `PositionSizerService` into production `run_paper_decision_loop`.

---

## Why this matters

`PositionSizerService` (M10) implements
`size_units = floor(balance × risk_pct / sl_pips / min_lot) × min_lot`
but **no production runner uses it**. All current paths use fixed CLI `--units` or default 1,000 (1 mini lot):

- `run_paper_decision_loop` — broker call deferred (logs only)
- `run_paper_entry_loop`, `paper_open_position` — fixed `--units`
- `run_volume_mode` — fixed `--units-per-trade` (intentional, alpha-agnostic)
- `execution_gate_runner` — falls back to fixed 1,000 when `risk_manager=None`

Backtests report **pip**-based Sharpe. Sizing is invariant in pip terms — multiplying every trade by N doesn't change Sharpe, only scales PnL. So risk-based sizing's effect is **invisible** in current backtest output.

The lift from risk-based sizing comes from **¥-variance equalisation across trades**:
- High-vol pair (wide ATR-based SL) → smaller `size_units` → smaller ¥ exposure per trade
- Low-vol pair (tight SL) → larger `size_units` → matched ¥ exposure
- Net effect: ¥ PnL series has lower variance for same mean → **¥-Sharpe ↑**

Estimated lift: **+10-20% Sharpe in ¥ terms**, mostly from variance reduction. PnL absolute may be slightly down or flat.

---

## I-1: Backtest extension — `compare_multipair_v22_risk_sizing.py`

Cloned from v19 (causal-fixed). Two new computation paths:

### Per-trade sizing
For each candidate trade in the backtest:
```python
sl_distance_pip = sl_mult * atr  # already computed for triple-barrier label
size_units = floor(balance × risk_pct / sl_distance_pip / min_lot) × min_lot
size_units = max(size_units, min_lot)  # clip to min if positive
```

`balance` starts at `--initial-balance` (default ¥300,000). For initial implementation, `balance` is **constant** (no compounding) — compounding adds another lever orthogonal to sizing itself, defer to Phase 9.X-J.

### ¥-based PnL reporting
For each trade:
```python
pnl_jpy = pnl_pip × pip_value(pair) × size_units / pip_unit_count(pair)
```

Where:
- `pip_value(USD/JPY) = 0.01 yen / unit`
- `pip_value(EUR/USD) = ~1.10 yen / unit` (mid × 0.0001 of USD = ~$0.00011 per unit, ¥0.0165 per unit at ¥150/USD)
- For simplicity: convert all final PnL to USD via current rate, then to ¥ at fixed ¥150/USD assumption (avoid path-dependent conversion).

Existing pip-based Sharpe / PnL / DD all **preserved**. New columns: `Sharpe(JPY)`, `PnL(JPY)`, `MaxDD(JPY)`, `DD%PnL(JPY)`.

### CLI additions
```
--enable-risk-sizing              # off by default (reproduces v19 numbers)
--risk-pct FLOAT                  # default 1.0 (% of balance per trade)
--initial-balance-jpy FLOAT       # default 300000.0
--min-lot INT                     # default 1000 (1 mini lot)
```

---

## I-2: Production wiring (after I-1 GO)

Inject `PositionSizerService` + `RiskManagerService` into `run_paper_decision_loop`:

```python
sizer = PositionSizerService(risk_pct=args.risk_pct)
risk_mgr = RiskManagerService(sizer=sizer, ...)
# Pass to the (still-deferred) execution_gate_runner call when broker
# integration lands.
```

Once this path is wired, the same `--feature-groups` / `--top-k` machinery feeds into per-trade sized orders.

Out of scope for I-2:
- Account balance updates (compounding) — Phase 9.X-J
- Multi-trade per bar (J-3 deferred work) — Phase 9.X-K
- Live margin / collateral checks — needs broker account info wire-up

---

## Verdict gates

For I-1 backtest result:

| Verdict | Condition |
| ---     | ---       |
| GO         | Sharpe(JPY) ≥ 1.10 × Sharpe(pip) AND PnL(JPY) ≥ 1.00× PnL(pip)-equivalent |
| PARTIAL GO | Sharpe(JPY) ≥ Sharpe(pip) (variance reduction) |
| **STRETCH GO** | Sharpe(JPY) ≥ 0.20 (cracks Phase 9.11) |
| NO ADOPT | Sharpe(JPY) < Sharpe(pip) (sizing makes it worse) |

---

## Calibration prior

Risk-based sizing is well-known to lift Sharpe. The question is **how much**.

- 50% — PARTIAL GO (modest +5-10% Sharpe lift)
- 30% — GO (+10-20% Sharpe lift)
- 15% — STRETCH GO (Sharpe ≥ 0.20 — would crack 9.11 alone)
- 5% — NO ADOPT (formula tuning needed; likely caused by unstable sl_pips at fold edges)

If Phase 9.X-G (portfolio-opt) ALSO GOes, the combined effect could push Sharpe > 0.22 (Phase 9.X-J = combinator phase).

---

## Sequencing

1. **Now**: I-1 v22 script implementation. Eval with `--enable-risk-sizing` vs default.
2. Eval should match v19 numbers when `--enable-risk-sizing=False` (sanity).
3. With risk-sizing enabled, expect Sharpe(JPY) > Sharpe(pip).
4. Closure verdict.
5. If GO/STRETCH GO: I-2 production wiring (separate PR, ~1-2 days).
6. Live deploy plan update — replace fixed `--units` with `--risk-pct` flag.

---

## Files

- This memo: `docs/design/phase9_x_i_design_memo.md`
- Implementation: `scripts/compare_multipair_v22_risk_sizing.py` (new)
- Eval log: `artifacts/phase9_x_i_risk_sizing.log` (new)
- Closure: `docs/design/phase9_x_i_closure_memo.md` (after eval)

Master tip when authored: fd1d2f1.
