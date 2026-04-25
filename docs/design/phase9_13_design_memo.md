# Phase 9.13 — Risk management (Phase D) Design Memo

**Status**: Design phase (2026-04-25)
**Predecessor**: Phase 9.12 closed SOFT GO at master `79ed1e8`
**Owner**: くりす
**Related**: `docs/phase9_roadmap.md` §6.15, `docs/design/phase9_12_closure_memo.md`

---

## 1. Why this phase

Phase 9.12 closed at SOFT GO — SELECTOR net Sharpe **0.160**. That is real edge (v3/v4 were negative), but it is not enough to clear the Phase 9.10 GO gate (≥ 0.20) or to survive realistic month-to-month variance with live capital.

Phase 9.13's job is **leverage on the existing edge**, not new alpha:

> Same signal stream from v5 (B-2 bid/ask labels), but apply position-sizing, exposure, and kill-switch logic on top so the realised PnL distribution has higher Sharpe and tighter drawdowns.

If Phase 9.13 lifts SELECTOR Sharpe to ≥ 0.20, the Phase 9.10 GO gate is cleared and Phase 9.11 (3+ year robustness) unblocks. Estimated lift across the three levers: **0.16 → 0.18–0.22** (per the Phase 9.12 closure memo §7).

If Phase 9.13 does not clear GO, fall back to **Phase 9.12 v2** (orthogonal features for meta-labeling) before re-running the gate.

---

## 2. Three levers, in priority order

### 2.1 Lever C-1 (highest priority): Kelly / Fractional Kelly position sizing

**Current state (v5/v6):** every trade is 1 unit. A high-confidence signal contributes the same per-trade pip as a marginal one.

**Change:** size each trade as `f × Kelly(win_prob, win_loss_ratio)` where:

- `win_prob` = Layer 1's `max(p_tp, p_sl)` — the model's stated confidence
- `win_loss_ratio` = `tp_mult / sl_mult` (= 1.5 at default)
- `Kelly = win_prob × b − loss_prob, divided by b` where `b` = win/loss ratio
- `f` = Kelly fraction (Quarter Kelly = 0.25 is the conventional safe default)

Concretely, per trade:
```
b = TP_mult / SL_mult                       # 1.5 at defaults
p = max(p_tp, p_sl)                          # Layer 1 confidence
q = 1 - p
kelly = (p * b - q) / b
size  = max(0.0, f * kelly)                 # clamp negatives to 0
```

**Why this should help:**
- Sharpe is a per-trade metric. Sizing that proportionally favours high-`p` bars amplifies the average without adding variance.
- Conventional finance result: Fractional Kelly with `f ∈ [0.25, 0.50]` typically produces **+0.02–0.08 Sharpe** vs uniform sizing on edge-positive strategies.

**Risk:** at full Kelly (`f=1.0`) drawdowns multiply along with returns. We will sweep `f ∈ {0.10, 0.25, 0.50, 1.00}` and report Sharpe + max DD per cell.

### 2.2 Lever C-2: Portfolio correlation cap

**Current state (v5/v6):** the SELECTOR strategy picks one pair per bar and treats each bar's trade as independent. In practice this means up to ~20 concurrent open positions (TP/SL resolves within horizon=20 bars), often heavily JPY-cross-correlated when the picker leans toward USD/JPY + EUR/JPY + GBP/JPY.

**Change:** at trade-open time, count currently-open positions by *correlation cluster*:

```
clusters = {
  "USD_DOMINANCE": {"USD_JPY", "USD_CHF", "USD_CAD"}        # USD long → all
  "JPY_RISK_OFF":  {"USD_JPY", "EUR_JPY", "GBP_JPY"}         # JPY weakness → all
  "AUD_NZD":       {"AUD_USD", "NZD_USD"}
  "EUR_GBP":       {"EUR_USD", "GBP_USD", "EUR_GBP"}
}
```

Skip a new trade if the SELECTOR's chosen pair shares a cluster with `>= max_concurrent_per_cluster` already-open positions. Cluster definition uses static FX correlation (rolling correlation would be more sophisticated, defer to Phase 9.13 v2 if static is insufficient).

**Why this should help:**
- During a JPY trend, SELECTOR fires on all three JPY crosses. Without a cap, drawdowns from a JPY reversal hit triple-magnitude. Capping concurrent JPY exposure at 1 reduces tail risk without much average-PnL cost.
- Estimated lift: +0.01–0.03 Sharpe via reduced variance.

**Risk:** the cap may suppress legitimate diversified opportunities (3 separate good signals on AUD/USD, NZD/USD, USD/CAD all happen at once). We will sweep `max_concurrent_per_cluster ∈ {1, 2, 3, 5}` and report.

### 2.3 Lever C-3: Kill switches

**Current state (v5/v6):** the strategy trades through every fold's drawdown. Some folds in v5 had per-fold Sharpe down to -0.49.

**Change:** three kill switches, each independently configurable:

- **Daily loss limit:** if intraday cumulative net pnl reaches `-daily_loss_pct × equity`, halt all trading until next trading day. Default `-3%`.
- **Consecutive-loss cooldown:** if last `N_consec_losses` trades all closed at SL, pause new entries for `cooldown_bars` bars. Default `N=5, cooldown=60` (1 hour M1).
- **Drawdown kill:** if equity drops below `peak_equity × (1 − dd_kill_pct)`, halt all trading for the rest of the backtest run. Default `-10%`. (This is the simulator's analogue of the live `EmergencyStopWatchdog`.)

**Why this should help:**
- Sharpe is variance-sensitive. The worst-tail months / folds disproportionately drag the aggregate Sharpe. Stopping early in a bad period preserves equity for a fresh restart.
- Estimated effect: **Sharpe-neutral or +0.01, but max DD -30 to -50%**. The big win is not in the average — it is in the tail that determines whether a live account survives to see the average.

**Risk:** the daily / DD kill is asymmetric — it sometimes stops you out right before a recovery. Threshold tuning matters. We will sweep daily limit ∈ {-2%, -3%, -5%} and DD kill ∈ {-7%, -10%, -15%}.

---

## 3. PR breakdown

| PR | Scope | Size | Depends |
|----|-------|------|---------|
| **C-0** (this memo) | `docs/design/phase9_13_design_memo.md` | docs only | master `79ed1e8` |
| **C-1** | `scripts/compare_multipair_v7_kelly.py` — Kelly sizing on top of v5; `f` sweep | ≤ 700 lines | C-0 |
| **C-2** | extend C-1 with correlation-cluster cap; `max_concurrent` sweep | ≤ 250 lines diff | C-1 |
| **C-3** | extend C-2 with three kill switches; per-switch ablation | ≤ 300 lines diff | C-2 |
| **C-4** | `docs/design/phase9_13_closure_memo.md` (Go / SOFT GO / NO-GO verdict) | docs only | C-3 |

Note: C-1/C-2/C-3 are layered, not independent. Each adds on top of the previous so the closure memo can ablation-decompose Sharpe contributions.

---

## 4. Detailed design — C-1 (Kelly sizing)

### 4.1 Where in the flow

In v5/v6, per-bar PnL is currently:
```
pnl = ±(tp_mult or sl_mult) * ATR(14) / pip_size      # variable in pip due to ATR
```

In v7, the same trade fires but with a sized contribution:
```
size = fractional_kelly(p, b, f)
pnl  = size * ±(tp_mult or sl_mult) * ATR(14) / pip_size
```

Kelly fraction calculation:
```python
def _kelly_size(p_win: float, b: float, f: float) -> float:
    """Fractional Kelly position size in [0, 1].

    p_win = Layer 1 confidence on the chosen direction
    b     = TP_mult / SL_mult (win/loss payoff ratio)
    f     = Kelly fraction (e.g. 0.25 = quarter Kelly)
    """
    q = 1.0 - p_win
    kelly = (p_win * b - q) / b
    return max(0.0, f * kelly)
```

For typical Layer 1 confidence p ≈ 0.55 with b = 1.5:
```
kelly = (0.55 * 1.5 - 0.45) / 1.5 = 0.25
quarter_kelly_size = 0.25 * 0.25 = 0.0625
```

That is 6.25% of equity per trade — small, conservative, matches retail-prudent sizing.

### 4.2 Sharpe in the sized world

Sharpe is computed on the per-trade-pip series. With variable size, the per-trade pnl distribution changes shape — high-`p` bars contribute larger wins AND larger losses, but the wins outweigh losses in expectation when `p > 1/(1+b) = 0.40`. So Sharpe rises if the model's `p` is calibrated.

If the model is poorly calibrated (Layer 1 reports 0.65 confidence on bars that hit 50% in reality), Kelly amplifies *miscalibration* and Sharpe drops. The grid sweep on `f` will surface this.

### 4.3 CLI

```
--kelly-fraction 0.25      # f ∈ {0.10, 0.25, 0.50, 1.00} for sweep
--no-kelly                 # uniform 1-unit sizing (reproduces v5)
```

---

## 5. Detailed design — C-2 (correlation cluster cap)

### 5.1 Cluster definition (static)

Static clusters based on common FX correlation patterns:

```python
CLUSTERS = {
    "USD_LONG":      ["USD_JPY", "USD_CHF", "USD_CAD"],
    "JPY_WEAKNESS":  ["USD_JPY", "EUR_JPY", "GBP_JPY"],
    "EUR_GBP_BLOCK": ["EUR_USD", "GBP_USD", "EUR_GBP"],
    "COMMODITY":     ["AUD_USD", "NZD_USD", "USD_CAD"],
}
```

A pair can belong to multiple clusters (e.g. USD/JPY in both USD_LONG and JPY_WEAKNESS). The cap applies per-cluster.

### 5.2 Concurrent-position tracking

In the backtest:
- Each fired trade has an open ts and an exit ts (TP / SL / horizon timeout).
- Maintain a `open_positions: list[(pair, open_ts, exit_ts)]` log; prune entries whose `exit_ts ≤ current_ts`.
- Before adding a new trade for `pair X`, count `n_in_cluster = sum(1 for p in open_positions if p.pair shares a cluster with X)`; skip the trade if `n_in_cluster ≥ max_concurrent_per_cluster`.

### 5.3 CLI

```
--max-concurrent-per-cluster 2    # sweep {1, 2, 3, 5}
--no-correlation-cap              # disables (reproduces C-1 behaviour)
```

---

## 6. Detailed design — C-3 (kill switches)

### 6.1 Three switches

```python
@dataclass
class KillSwitchConfig:
    daily_loss_pct: float = 0.03          # -3%: halt for the rest of the day
    consec_loss_n: int = 5                 # 5 SL hits in a row
    cooldown_bars: int = 60                # 1 hour M1 cooldown
    drawdown_kill_pct: float = 0.10        # -10% from peak: halt for the rest of run
```

### 6.2 State machine

The simulator maintains:
- `equity_curve: list[(ts, equity)]` — running equity in pip-units
- `peak_equity` — high-water mark
- `today_open_equity` — equity at start of current trading day
- `consec_loss_count` — running count
- `cooldown_until_ts` — kill-switch cooldown timestamp

At each new trade:
1. If `current_ts < cooldown_until_ts`: skip (kill in effect).
2. If `equity < peak_equity * (1 - drawdown_kill_pct)`: hard-stop, halt all trades for rest of run.
3. If `equity < today_open_equity * (1 - daily_loss_pct)`: halt for rest of day.
4. If `consec_loss_count >= consec_loss_n`: enter cooldown for `cooldown_bars`.
5. Otherwise: execute trade.

After each closed trade:
- Update `equity_curve`, `peak_equity`.
- If trade closed at SL: `consec_loss_count += 1`. If TP/timeout-positive: `consec_loss_count = 0`.

### 6.3 CLI

```
--daily-loss-pct 0.03
--consec-loss-n 5
--cooldown-bars 60
--drawdown-kill-pct 0.10
--no-kill-switch                  # disables all (reproduces C-2 behaviour)
```

---

## 7. Composition order and what gets reported

1. **C-1 alone:** answers "does Kelly sizing alone clear GO?" — fastest path.
2. **C-1 + C-2:** adds variance reduction from cluster cap. Should help drawdowns more than Sharpe.
3. **C-1 + C-2 + C-3:** full risk-managed strategy. The closure memo's verdict comes from this.

Each script run reports:
- Aggregate Sharpe / PnL / WinFold% / max DD
- Per-fold Sharpe distribution
- For C-2: per-cluster concurrent-position histogram
- For C-3: number of times each kill fired

---

## 8. Out of scope (deferred)

| Item | Deferred to |
|------|-------------|
| Rolling correlation (vs static clusters) | Phase 9.13 v2 if static is insufficient |
| Risk-parity weighting across signals | Phase 9.13 v2 |
| Per-pair leverage caps (broker margin awareness) | Phase 9.14 (paper) |
| Regime-aware Kelly (smaller `f` in high-vol) | Phase 9.13 v2 |
| Production code wiring (`risk_manager.py`, `position_sizer.py`) | After Phase 9.13 produces full GO |
| OANDA demo paper trading | Phase 9.14 |
| 3+ yr multi-regime data | Phase 9.11 (still BLOCKED on 9.13 GO) |

---

## 9. Success criteria for closure memo

The closure memo (C-4) reports verdict against the same Phase 9.10 thresholds used in 9.10/9.12:

| Cell condition | Verdict |
|---|---|
| Best (C-1+C-2+C-3) cell SELECTOR net Sharpe ≥ 0.20 AND net PnL > 0 | **GO** → unblock Phase 9.11 |
| Best cell 0.15 ≤ Sharpe < 0.20 | **SOFT GO** → consider Phase 9.12 v2 (orthogonal features) before paper |
| Best cell < 0.15 | **NO-GO** → unwind to Phase 9.12 baseline; Phase 9.13 didn't pay |

Secondary criterion (if GO is met):
- **Max drawdown improvement**: best cell DD ≤ v5 DD × 0.7 (i.e. at least 30% drawdown reduction). This is what the kill switches are mostly buying.

---

## 10. Timeline estimate

- C-0 (this memo): <1 hour
- C-1: 1 day implementation + ~10 min wall-time per cell × 4 cells = ~40 min sweep
- C-2: 0.5 day implementation + ~5 min × 4 cells = ~20 min
- C-3: 1 day implementation + ~5 min × 6 cells = ~30 min
- C-4: 0.5 day

Total ≈ 3 days excluding any unexpected pivot.
