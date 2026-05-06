# Stage 23.0c — M5 z-score MR + M1 Execution Eval

Generated: 2026-05-06T11:35:26.759596+00:00

Design contract: `docs/design/phase23_0c_m5_zscore_mr_baseline.md`

Universe: 20 pairs, signal TF = `M5`, span = 730d, trigger mode = `first_touch`
Sweep: N (12, 24, 48) × threshold (2.0, 2.5) × horizon (1, 2, 3) × exit ('tb', 'time') = 36 cells

## Headline verdict

**REJECT**

Per-cell verdict counts: 36 REJECT / 0 PROMISING_BUT_NEEDS_OOS / 0 ADOPT_CANDIDATE — out of 36 cells.

REJECT reason breakdown:
- under_firing: 0 cell(s)
- still_overtrading: 36 cell(s)
- pnl_edge_insufficient: 0 cell(s)
- robustness_failure: 0 cell(s)

Best cell: `N=48, threshold=2.5, horizon=3, exit=time` (Sharpe -0.2830, annual_pnl -109888.1 pip, n_trades 86697)

## Did first-touch fix overtrading?

- 23.0c annual_trades distribution across 36 cells: min 43378.2 / median 87104.1 / max 157058.0
- Cells triggering overtrading warning (`> 1000`): 36 / 36
- 23.0b reference (continuous-trigger Donchian): annual_trades 105,275 – 249,507 across 18 cells; ALL 18 triggered the overtrading warning.
- First-touch did **not** eliminate overtrading; all cells still warn.

## Production-readiness

Even an `ADOPT_CANDIDATE` verdict is **not** production-ready. The S1 strict OOS is computed *after* the in-sample sweep selected the best cell from 36 cells × 20 pairs (multiple-testing surface). A separate `23.0c-v2` PR with frozen-cell strict OOS validation on chronologically out-of-sample data and no parameter re-search is required before any production migration.

## Trigger semantics

- Trigger mode: `first_touch` (rising-edge into the extreme zone). Long: `z[t] < -threshold AND z[t-1] >= -threshold`. Short: mirrored.
- Same-direction re-entry is locked while `z` stays outside the band. Long-side and short-side locks are independent.
- **Continuous trigger is not the Phase 23 default because 23.0b showed continuous-trigger overtrading. A continuous variant may be reintroduced only as a diagnostic follow-up, not as the main baseline.**

## Gate thresholds (Phase 22 inherited, identical to 23.0b)

- A0: annual_trades >= 70.0 (overtrading warning if > 1000.0, NOT blocking)
- A1: per-trade Sharpe (ddof=0, no √N) >= +0.082
- A2: annual_pnl_pip >= +180.0
- A3: max_dd_pip <= 200.0
- A4: 5-fold chronological, drop k=0, eval k=1..4, count(Sharpe > 0) >= 3/4
- A5: annual_pnl after subtracting 0.5 pip per round trip > 0

## Sweep summary (all cells, sorted by Sharpe)

| N | thr | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 48 | 2.5 | 3 | time | 86697 | 43378.2 | -0.2830 | -109888.1 | 219628.6 | 0/4 | -131577.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 3 | time | 126526 | 63306.3 | -0.2923 | -157546.2 | 314883.7 | 0/4 | -189199.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | time | 144064 | 72081.3 | -0.3021 | -179676.7 | 359106.1 | 0/4 | -215717.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | time | 204112 | 102125.9 | -0.3107 | -255364.9 | 510386.2 | 0/4 | -306427.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | time | 210474 | 105309.1 | -0.3139 | -262183.9 | 524006.9 | 0/4 | -314838.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | time | 313894 | 157054.5 | -0.3222 | -386772.3 | 772998.6 | 0/4 | -465299.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | time | 86697 | 43378.2 | -0.3409 | -111278.4 | 222406.6 | 0/4 | -132967.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | time | 126526 | 63306.3 | -0.3567 | -161054.9 | 321897.3 | 0/4 | -192708.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | time | 144064 | 72081.3 | -0.3606 | -181600.5 | 362951.3 | 0/4 | -217641.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | time | 204113 | 102126.4 | -0.3699 | -257118.5 | 513888.7 | 0/4 | -308181.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | time | 210475 | 105309.6 | -0.3803 | -266253.0 | 532137.9 | 0/4 | -318907.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | time | 313896 | 157055.5 | -0.3837 | -389956.7 | 779371.8 | 0/4 | -468484.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 3 | tb | 86697 | 43378.2 | -0.4037 | -99160.9 | 198184.8 | 0/4 | -120850.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | tb | 144064 | 72081.3 | -0.4289 | -162233.1 | 324242.7 | 0/4 | -198273.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 3 | tb | 126526 | 63306.3 | -0.4306 | -139732.4 | 279280.1 | 0/4 | -171385.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | time | 86698 | 43378.7 | -0.4383 | -114626.0 | 229094.7 | 0/4 | -136315.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | tb | 86697 | 43378.2 | -0.4462 | -99097.4 | 198057.9 | 0/4 | -120786.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | tb | 210474 | 105309.1 | -0.4515 | -234282.4 | 468236.4 | 0/4 | -286936.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | tb | 204112 | 102125.9 | -0.4529 | -225596.0 | 450876.3 | 0/4 | -276659.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | tb | 313894 | 157054.5 | -0.4545 | -343527.1 | 686576.8 | 0/4 | -422054.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | time | 126528 | 63307.3 | -0.4594 | -166219.4 | 332216.6 | 0/4 | -197873.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | time | 144066 | 72082.3 | -0.4667 | -186200.2 | 372145.2 | 0/4 | -222241.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | tb | 144064 | 72081.3 | -0.4719 | -161470.7 | 322719.2 | 0/4 | -197511.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | time | 204118 | 102128.9 | -0.4720 | -263752.0 | 527132.5 | 0/4 | -314816.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | tb | 126526 | 63306.3 | -0.4724 | -139493.2 | 278803.3 | 0/4 | -171146.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | time | 210478 | 105311.1 | -0.4942 | -272731.1 | 545078.4 | 0/4 | -325386.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | tb | 204113 | 102126.4 | -0.4952 | -223821.9 | 447330.8 | 0/4 | -274885.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | time | 313901 | 157058.0 | -0.4957 | -398105.5 | 795664.0 | 0/4 | -476634.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | tb | 210475 | 105309.6 | -0.4987 | -233575.1 | 466823.0 | 0/4 | -286229.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | tb | 313896 | 157055.5 | -0.5041 | -342370.3 | 684264.8 | 0/4 | -420898.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | tb | 86698 | 43378.7 | -0.5372 | -99167.3 | 198198.4 | 0/4 | -120856.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | tb | 126528 | 63307.3 | -0.5660 | -139724.2 | 279262.5 | 0/4 | -171377.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | tb | 144066 | 72082.3 | -0.5723 | -161547.3 | 322873.0 | 0/4 | -197588.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | tb | 204118 | 102128.9 | -0.5956 | -223760.5 | 447207.0 | 0/4 | -274824.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | tb | 210478 | 105311.1 | -0.6048 | -233185.0 | 466043.3 | 0/4 | -285840.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | tb | 313901 | 157058.0 | -0.6157 | -342654.9 | 684838.7 | 0/4 | -421183.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |

## Best cell deep-dive

- N=48, threshold=2.5, horizon=3, exit=time
- n_trades = 86697 (long 43445 / short 43252)
- annual_trades = 43378.2 — **OVERTRADING WARNING** (> 1000)
- Sharpe = -0.2830
- annual_pnl = -109888.1 pip
- max_dd = 219628.6 pip
- A4 fold Sharpes (k=1..4): -0.2924, -0.2309, -0.3507, -0.3371
- A5 stressed annual_pnl = -131577.2 pip

### z_at_entry distribution (|z| at signal bars)

- p10 = 2.543, p25 = 2.617, p50 = 2.788, p75 = 3.115, p90 = 3.640

### time_to_revert_to_mean (forward-path, diagnostic only)

- Reverted within horizon: 3546 / 86697 trades (4.09%)
- M1 bars to revert (among reverted): p25 6.0 / p50 10.0 / p75 13.0
- (Forward-path diagnostic only — NOT used for ADOPT decisions or features.)

### Diagnostics (NOT gates)

- hit_rate = 0.3238
- payoff_asymmetry = 0.8097
- S0 random-entry Sharpe = -0.3666
- S1 strict 80/20 OOS: IS Sharpe -0.2715 (n=69358), OOS Sharpe -0.3371 (n=17339), oos/is ratio +nan

### Per-pair contribution

| pair | n_trades | Sharpe | annual_pnl | hit_rate |
|---|---|---|---|---|
| USD_JPY | 4294 | -0.1237 | -3286.2 | 0.4162 |
| EUR_USD | 4373 | -0.2045 | -3194.2 | 0.3691 |
| EUR_JPY | 4362 | -0.2050 | -5575.7 | 0.3810 |
| GBP_USD | 4377 | -0.2436 | -4094.7 | 0.3669 |
| AUD_USD | 4328 | -0.2515 | -2868.1 | 0.3609 |
| AUD_JPY | 4284 | -0.2702 | -5647.7 | 0.3506 |
| USD_CHF | 4385 | -0.2717 | -3360.8 | 0.3460 |
| GBP_JPY | 4377 | -0.2832 | -9312.5 | 0.3594 |
| USD_CAD | 4338 | -0.2897 | -4049.4 | 0.3280 |
| EUR_AUD | 4431 | -0.3108 | -7809.2 | 0.3304 |
| NZD_USD | 4282 | -0.3281 | -3338.5 | 0.3192 |
| EUR_CAD | 4387 | -0.3369 | -6094.4 | 0.3041 |
| EUR_CHF | 4346 | -0.3465 | -3644.8 | 0.2964 |
| CHF_JPY | 4293 | -0.3599 | -9119.6 | 0.3189 |
| NZD_JPY | 4315 | -0.3716 | -6799.4 | 0.2962 |
| GBP_AUD | 4372 | -0.3731 | -10487.8 | 0.3040 |
| EUR_GBP | 4300 | -0.4067 | -3038.6 | 0.2756 |
| GBP_CHF | 4356 | -0.4351 | -6481.7 | 0.2656 |
| AUD_CAD | 4301 | -0.4390 | -5413.8 | 0.2795 |
| AUD_NZD | 4196 | -0.5764 | -6271.0 | 0.2040 |

### Per-session contribution

| session | n_trades | Sharpe | annual_pnl | hit_rate |
|---|---|---|---|---|
| American (12-18 UTC) | 22664 | -0.1912 | -22547.2 | 0.3799 |
| Asian (00-06 UTC) | 23645 | -0.3101 | -27877.4 | 0.3050 |
| European (06-12 UTC) | 26026 | -0.2677 | -27871.3 | 0.3415 |
| Late (18-24 UTC) | 14362 | -0.4446 | -31592.2 | 0.2344 |
