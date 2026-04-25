# Phase 9.18 — Asymmetric TP/SL + partial exits (Phase H) Closure Memo

**Status**: Closed — **NO ADOPT** (symmetric v9 20-pair bundle remains production default)
**Master tip at authorship**: `af6bb86` (Phase 9.18 H-2 merged) + this PR
**Predecessor**: Phase 9.16 closed at master `a973018`
**Related**: `docs/phase9_roadmap.md` §6.20, `docs/design/phase9_18_design_memo.md`, `docs/design/phase9_16_closure_memo.md`

---

## 1. What this phase set out to do

Phase 9.16 closed with a 20-pair v9 spread bundle as production default (PnL +20.1% vs v5, DD%PnL 2.5%, Sharpe 0.160). But Sharpe stayed rangebound at **0.143–0.177** across Phase 9.13–9.16 — Layer 1 / pair / risk levers couldn't break out.

Phase 9.18 attacked the **per-trade EV** axis — the only remaining lever that touches the EV/variance ratio directly without an alpha-source change.

**H-1**: confidence-bucketed TP/SL.
- Low `[0.50, 0.55)`: TP=1.2, SL=1.2 — cap loss tail on borderline calls
- Mid `[0.55, 0.65)`: TP=1.5, SL=1.0 — current default (A/B baseline)
- High `[0.65, 1.00]`: TP=2.0, SL=0.8 — let winners run on confident calls

**H-2**: partial exit on the High bucket only.
- 50% size split at entry; partial leg TP=1×ATR, SL=0.8×ATR
- runner leg TP=2×ATR, SL=0.8×ATR initially → trail to entry once partial fires

The kickoff design memo predicted **per-trade EV +20–30%, Sharpe +0.02–0.04, PnL +10–20%** on top of the 20-pair v9 spread baseline — but with an explicit honesty disclosure (§9.1, §9.3) that the math could go either way and the eval is the arbiter.

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| #202 | Phase 9.18 design memo | docs only |
| #203 | H-1 bucketed TP/SL eval (`compare_multipair_v12_asymmetric.py`) | implementation; smoke-tested |
| #204 | H-2 partial exit on High bucket (extends v12) | implementation; smoke-tested |
| **(this PR)** | H-3 20-pair eval + closure memo | NO ADOPT |

---

## 3. Results

### 3.1 20-pair 3-cell sweep (full Phase 9.16 universe, v9 spread bundle)

```
                          Sharpe   PnL(pip)   MaxDD    DD%PnL   WinFold%   Trades
20p v9 symmetric (base)   0.160    8,157.2    203.4     2.5%      90%      12,461
20p v9 bucketed (H-1)     0.127    6,600.6    251.5     3.8%      77%      12,461   (0.81x PnL)
20p v9 bucketed+partial  -0.025   -1,342.0   1887.7   999.0%      41%      12,461  (-0.16x PnL)
```

### 3.2 Per-bucket distribution (SELECTOR, bucketed cell)

```
Bucket    TP/SL    Trades            Hit Rate   GrossPnL   EV/trade
low       1.2/1.2  4,369 (35.1%)    53.6%       484.7      0.111
mid       1.5/1.0  5,001 (40.1%)    56.2%      3781.5      0.756
high      2.0/0.8  3,091 (24.8%)    54.1%      2334.5      0.755
```

Symmetric baseline (all mid): 12,461 trades, 54.5% hit rate, 8,157.2 pip, EV/trade **0.655**.

### 3.3 High-bucket partial-exit outcome distribution (SELECTOR, bucketed+partial cell)

```
Outcome                  Count   Share
sl_before_partial        2,486   80.4%
partial_then_trail         284    9.2%
partial_then_tp            281    9.1%
partial_then_timeout        28    0.9%
timeout_no_partial          12    0.4%
Partial fire rate:         593 / 3,091   (19.2%)
```

High bucket with partial: hit rate drops to 19.3% (593/3,091), GrossPnL −5,608.2, EV/trade **−1.814**.

---

## 4. Verdict — NO ADOPT

Per the design memo's PnL-priority gates:

| Gate | Rule | Result |
|------|------|--------|
| LEGACY GO | SELECTOR Sharpe >= 0.20 AND PnL > 0 | ✗ NOT MET — best cell 0.160 (symmetric, baseline) |
| STRETCH GO | any cell reaches Sharpe >= 0.18 | ✗ NOT MET — 0.160 / 0.127 / −0.025 |
| GO | PnL >= 1.10 × baseline AND DD%PnL <= 5% AND Sharpe >= baseline | ✗ NOT MET — bucketed PnL = 0.81× baseline |
| NO ADOPT | PnL < baseline OR DD%PnL > 5% | ✓ TRIGGERED — bucketed: PnL −19%, bucketed+partial: PnL negative |

**H-1 (bucketed)**: SOFT GO by DD%PnL gate (2.5%→3.8%, still ≤5%) but **PnL regression −19%** → NO ADOPT.
**H-2 (bucketed+partial)**: NO ADOPT. PnL −116%, MaxDD +829%, WinFold% 41%.

**Production default unchanged**: v9 20-pair symmetric spread bundle (Sharpe 0.160, PnL 8,157 pip, DD%PnL 2.5%).

---

## 5. Per-bucket EV — actual vs theoretical

The design memo §9.1 made these theoretical EV predictions (in ATR units):

| Bucket | Predicted HR | Predicted EV | Observed HR | Observed EV (pip) | Delta |
|--------|-------------|--------------|-------------|-------------------|-------|
| Low (1.2/1.2) | 52% | +0.05 ATR | 53.6% | +0.111 | HR ≈ predicted; EV positive but drags vs symmetric |
| Mid (1.5/1.0) | 57% | +0.43 ATR | 56.2% | +0.756 | HR roughly matched; EV lifted vs symmetric 0.655 |
| High (2.0/0.8) | 62% | +0.94 ATR | 54.1% | +0.755 (no partial) | HR 8 pp below prediction — model confidence ≠ hit rate |

**Root cause of H-1 failure**: Low bucket (35.1% of trades) dragged the overall average.
Symmetric EV/trade = 0.655; bucketed average = (0.111×0.351 + 0.756×0.401 + 0.755×0.248) = **0.530** — a −19% drop.

The Low-bucket trades (conf 0.50–0.55) do slightly better than 52% hit rate, but switching them from TP=1.5/SL=1.0 to TP=1.2/SL=1.2 caps per-winner PnL while barely improving hit rate. The net result is markedly lower EV/trade for 35% of the trade book.

**Root cause of H-2 failure**: 80.4% of High-bucket trades hit SL before the partial TP (1×ATR) fires. The model's correct exit is 2×ATR — splitting at 1×ATR meant 80% of the time the partial leg _added_ cost without benefit. The trail-to-entry runner mechanism increased variance without rescuing sufficient losses.

---

## 6. Cumulative path through Phase 9.10–9.18

```
v3 (mid label, 1pip):            Sharpe -0.076  NO-GO
v5 (bid/ask label):              Sharpe +0.160  SOFT GO  ★ DECISIVE
v8 (C-3 kill switches):          Sharpe +0.177  SOFT GO+
v9 (10p, +spread):               Sharpe +0.152  PnL +13%, DD -17%        ★ Phase 9.15
v10 (10p, +spread+RH):           Sharpe +0.143  PnL +15.5%               ★ Phase 9.15 opt-in
v9-20p (20 pairs):               Sharpe +0.160  PnL +20.1% vs v5         ★ Phase 9.16 (production default)
v11 (+CSI):                      Sharpe +0.143  PnL -15% vs 20p          ✗ rejected
v12 symmetric (sanity):          Sharpe +0.160  matches v9-20p exactly   ★ this phase baseline confirmed
v12 bucketed (H-1):              Sharpe +0.127  PnL -19% vs symmetric    ✗ NO ADOPT
v12 bucketed+partial (H-2):      Sharpe -0.025  PnL -116% vs symmetric   ✗ NO ADOPT
```

---

## 7. What's next

Phase 9.18 closes the **per-trade EV engineering** thread. Both H-1 and H-2 produced regressions on the 20-pair full eval.

The Sharpe ceiling (0.143–0.177) is now confirmed to resist all engineering levers that don't touch the alpha source:
- Layer 1 features: tried (9.4–9.9), SELECTOR plateau
- Risk multipliers / kill-switches: tried (9.13 C-3), small lift
- Pair expansion: tried (9.16), +20% PnL, Sharpe flat
- Per-trade exit engineering: tried (9.18 H-1/H-2), regression

**The next required step is structural alpha change:**
- **Phase 9.17**: multi-strategy ensemble (orthogonal signal sources)
- **Alternative**: LSTM / transformer, alternative barrier labels, alternative feature engineering

Phase 9.11 (3+ year robustness) remains **BLOCKED** on Sharpe ≥ 0.20 gate.

H-4 (production runtime toggle for exit_policy) is **not triggered**.

---

## 8. Notes for future-me

1. **Model confidence ≠ hit rate lift.** High-confidence calls (0.65+) hit at 54.1% — nearly identical to the overall 54.5%. LightGBM's predict_proba in this regime is well-calibrated in the mid range but confidence above 0.65 doesn't predict materially higher success rates. Don't build exit strategies that assume monotonic confidence→hit-rate mapping.

2. **Low-bucket drag is large.** At 35.1% of trades, the Low bucket is not a small tail. Switching those trades from TP=1.5/SL=1.0 to TP=1.2/SL=1.2 converts them from EV=0.655 to EV=0.111. If you revisit bucketing, test the 2-bucket fallback from the design memo (drop Low entirely; skip trades below 0.55 confidence) before giving up on the concept.

3. **Partial exit requires fast price movement.** The partial-TP at 1×ATR fires only 19.2% of the time because the HL range within the trade horizon rarely reaches TP before SL. A viable partial-exit strategy needs to use an _earlier_ partial level (e.g. 0.5×ATR) OR accept that partial exits suit momentum regimes only. Test partial exits in regime-filtered sub-samples before applying universally.

4. **Smoke-run results were directionally correct.** The 2-pair smoke run predicted: Low bucket EV negative, High+partial Sharpe < 0. The full 20-pair run confirmed: Low bucket EV marginal (+0.111), High+partial Sharpe −0.025. Smoke runs on 2 pairs are a reliable pre-filter for structural failures.

5. **Per-trade EV is not the binding constraint.** The binding constraint is alpha quality — the model's signal is correct direction ~54-56% of the time, and no exit engineering can compensate for a weak directional edge. Phase 9.17 (multi-strategy ensemble) or structural model change is the only remaining path to Sharpe ≥ 0.20.

---

## 9. Commit trail

```
019f79f  PR #202  Phase 9.18 kickoff design memo
b391c8d  PR #203  H-1 confidence-bucketed TP/SL eval
af6bb86  PR #204  H-2 partial exit on High bucket
97adb2c  PR #205  H-3 + this closure memo
```
