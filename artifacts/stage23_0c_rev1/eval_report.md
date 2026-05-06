# Stage 23.0c-rev1 — Signal-Quality Control Study

Generated: 2026-05-06T13:19:11.416606+00:00

Design contract: `docs/design/phase23_0c_rev1_signal_quality.md`

Universe: 20 pairs, signal TF = `M5`, span = 730d
Sweep: 4 filter(s) × N (12, 24, 48) × threshold (2.0, 2.5) × horizon (1, 2, 3) × exit ('tb', 'time') = 144 cells
Filter constants (FIXED): NEUTRAL_BAND=0.5, COOLDOWN_BARS=3, COST_GATE_THRESHOLD=0.6

## Multiple-testing caveat (mandatory)

**This is a 144-cell diagnostic sweep across 4 filters; PROMISING / ADOPT_CANDIDATE results are HYPOTHESIS-GENERATING ONLY.** A separate `23.0c-rev2` PR with frozen-cell strict OOS validation (no parameter re-search, no filter re-search) is mandatory before any production discussion. The per-filter `assign_verdict` function does NOT correct for the 144-cell multiple-testing inflation.

## Headline overall verdict

**REJECT**

Per-cell verdict counts: 144 REJECT / 0 PROMISING_BUT_NEEDS_OOS / 0 ADOPT_CANDIDATE — out of 144 cells.

REJECT reason breakdown (across all 144 cells):
- under_firing: 0 cell(s)
- still_overtrading: 144 cell(s)
- pnl_edge_insufficient: 0 cell(s)
- robustness_failure: 0 cell(s)

## Filter roles (interpretation labels)

- **F1_neutral_reset**: re-entry control
- **F2_cooldown**: time-interval control
- **F3_reversal_confirmation**: reversal start confirmation
- **F4_cost_gate**: per-entry execution-cost sanity gate (NOT a pair filter)

## Per-filter verdict

| filter | role | best cell | Sharpe | annual_pnl | annual_trades | verdict |
|---|---|---|---|---|---|---|
| F1_neutral_reset | re-entry control | N=48, thr=2.5, h=3, exit=time | -0.2879 | -66058.6 | 24906.0 | REJECT |
| F2_cooldown | time-interval control | N=48, thr=2.5, h=3, exit=time | -0.2821 | -102383.9 | 40311.6 | REJECT |
| F3_reversal_confirmation | reversal start confirmation | N=24, thr=2.5, h=3, exit=time | -0.2899 | -24284.5 | 8456.8 | REJECT |
| F4_cost_gate | per-entry execution-cost sanity gate (NOT a pair filter) | N=24, thr=2.5, h=3, exit=time | -0.1948 | -66181.4 | 33696.1 | REJECT |

## Comparison vs 23.0c base

| stage / filter | best Sharpe | best annual_pnl pip | best annual_trades | best cell |
|---|---|---|---|---|
| 23.0c base (no filter) | -0.2830 | -109888.1 | 43378.2 | N=48, thr=2.5, h=3, exit=time |
| F1_neutral_reset | -0.2879 | -66058.6 | 24906.0 | N=48, thr=2.5, h=3, exit=time |
| F2_cooldown | -0.2821 | -102383.9 | 40311.6 | N=48, thr=2.5, h=3, exit=time |
| F3_reversal_confirmation | -0.2899 | -24284.5 | 8456.8 | N=24, thr=2.5, h=3, exit=time |
| F4_cost_gate | -0.1948 | -66181.4 | 33696.1 | N=24, thr=2.5, h=3, exit=time |

## Filter effectiveness summary (across 36 sub-cells per filter)

| filter | n_cells | median ann_tr | median Sharpe | best Sharpe | best ann_tr | A0 pass | A1 pass | A2 pass |
|---|---|---|---|---|---|---|---|---|
| F1_neutral_reset | 36 | 52986.3 | -0.4674 | -0.2879 | 24906.0 | 36 | 0 | 0 |
| F2_cooldown | 36 | 81160.8 | -0.4524 | -0.2821 | 40311.6 | 36 | 0 | 0 |
| F3_reversal_confirmation | 36 | 14006.6 | -0.4555 | -0.2899 | 2150.5 | 36 | 0 | 0 |
| F4_cost_gate | 36 | 46930.6 | -0.3292 | -0.1948 | 25987.3 | 36 | 0 | 0 |

23.0b reference (continuous-trigger Donchian, M5): annual_trades 105k–250k, all 18 cells overtrading.  23.0c reference (first-touch z-MR, M5): 43k–157k, all 36 cells overtrading.  23.0d reference (first-touch Donchian, M15): 22k–53k, all 18 cells overtrading.

## Phase 23 routing post-23.0c-rev1

```
23.0c-rev1 returns:
├── any filter ADOPT_CANDIDATE / PROMISING
│     → that single frozen cell promotes to 23.0c-rev2
│       (frozen-cell strict OOS, no parameter re-search)
│     → 23.0e meta-labeling MAY trigger on this cell
│     → Phase 23 conclusion (path B): 'naive firing was the issue;
│       signal-quality controls fix it'
│
└── all 4 filters REJECT
      → 23.0e DOES NOT trigger
      → Phase 23 closes (path A): 'M5/M15 has no recoverable edge
        even with stronger signal-quality controls'
      → Phase 24 (Exit/Capture Study, kickoff §7) becomes the next pivot
```

**This run lands on path A**: all 4 filters REJECT. Phase 23 closes with the negative-but-bounded conclusion. Per design §6.4, F4-only success would have been flagged as a cost-based selection effect (separate diagnosis); here all four filters fail the gate, supporting the broader 'no recoverable edge under stronger controls' conclusion.

## Production-readiness

Even an `ADOPT_CANDIDATE` verdict is **not** production-ready. 144-cell diagnostic sweep with multiple-testing inflation. A separate `23.0c-rev2` PR with frozen-cell strict OOS validation on chronologically out-of-sample data and no parameter re-search is required before any production migration.

## Best cell deep-dive (per filter)

### F1_neutral_reset — re-entry control

- N=48, threshold=2.5, horizon=3, exit=time
- n_trades = 49778 (long 24875 / short 24903)
- annual_trades = 24906.0 — **OVERTRADING WARNING** (> 1000)
- Sharpe = -0.2879
- annual_pnl = -66058.6 pip
- max_dd = 132025.5 pip
- A4 fold Sharpes (k=1..4): -0.3048, -0.2299, -0.3549, -0.3447
- A5 stressed annual_pnl = -78511.6 pip
- hit_rate = 0.3188
- payoff_asymmetry = 0.7949
- S0 random-entry Sharpe = -0.3684
- S1 strict 80/20 OOS: IS -0.2767 (n=39822), OOS -0.3447 (n=9956), oos/is ratio +nan
- verdict: **REJECT**

### F2_cooldown — time-interval control

- N=48, threshold=2.5, horizon=3, exit=time
- n_trades = 80568 (long 40401 / short 40167)
- annual_trades = 40311.6 — **OVERTRADING WARNING** (> 1000)
- Sharpe = -0.2821
- annual_pnl = -102383.9 pip
- max_dd = 204630.5 pip
- A4 fold Sharpes (k=1..4): -0.2971, -0.2268, -0.3479, -0.3409
- A5 stressed annual_pnl = -122539.7 pip
- hit_rate = 0.3240
- payoff_asymmetry = 0.8095
- S0 random-entry Sharpe = -0.3690
- S1 strict 80/20 OOS: IS -0.2697 (n=64454), OOS -0.3409 (n=16114), oos/is ratio +nan
- verdict: **REJECT**

### F3_reversal_confirmation — reversal start confirmation

- N=24, threshold=2.5, horizon=3, exit=time
- n_trades = 16902 (long 8738 / short 8164)
- annual_trades = 8456.8 — **OVERTRADING WARNING** (> 1000)
- Sharpe = -0.2899
- annual_pnl = -24284.5 pip
- max_dd = 48549.8 pip
- A4 fold Sharpes (k=1..4): -0.3037, -0.2614, -0.3864, -0.3565
- A5 stressed annual_pnl = -28512.9 pip
- hit_rate = 0.3150
- payoff_asymmetry = 0.7646
- S0 random-entry Sharpe = -0.3651
- S1 strict 80/20 OOS: IS -0.2779 (n=13522), OOS -0.3565 (n=3380), oos/is ratio +nan
- verdict: **REJECT**

### F4_cost_gate — per-entry execution-cost sanity gate (NOT a pair filter)

- N=24, threshold=2.5, horizon=3, exit=time
- n_trades = 67346 (long 33932 / short 33414)
- annual_trades = 33696.1 — **OVERTRADING WARNING** (> 1000)
- Sharpe = -0.1948
- annual_pnl = -66181.4 pip
- max_dd = 132309.5 pip
- A4 fold Sharpes (k=1..4): -0.2307, -0.1197, -0.2530, -0.2413
- A5 stressed annual_pnl = -83029.4 pip
- hit_rate = 0.3874
- payoff_asymmetry = 0.8373
- S0 random-entry Sharpe = -0.3688
- S1 strict 80/20 OOS: IS -0.1859 (n=53877), OOS -0.2413 (n=13469), oos/is ratio +nan
- verdict: **REJECT**

## Sweep summary (all cells, sorted by Sharpe within filter)

### F1_neutral_reset

| N | thr | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 48 | 2.5 | 3 | time | 49778 | 24906.0 | -0.2879 | -66058.6 | 132025.5 | 0/4 | -78511.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | time | 70741 | 35394.7 | -0.2990 | -91831.0 | 183536.1 | 0/4 | -109528.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 3 | time | 87624 | 43842.0 | -0.2996 | -111104.4 | 222063.8 | 0/4 | -133025.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | time | 124175 | 62130.0 | -0.3169 | -158210.8 | 316203.0 | 0/4 | -189275.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | time | 157926 | 79017.1 | -0.3209 | -200650.3 | 401032.7 | 0/4 | -240158.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | time | 214579 | 107363.0 | -0.3313 | -270070.5 | 539754.7 | 0/4 | -323752.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | time | 49778 | 24906.0 | -0.3454 | -66236.9 | 132382.1 | 0/4 | -78690.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | time | 70741 | 35394.7 | -0.3593 | -92821.6 | 185515.0 | 0/4 | -110518.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | time | 87624 | 43842.0 | -0.3669 | -114288.1 | 228427.7 | 0/4 | -136209.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | time | 157927 | 79017.6 | -0.3786 | -201253.7 | 402235.3 | 0/4 | -240762.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | time | 124176 | 62130.5 | -0.3846 | -160785.9 | 321348.0 | 0/4 | -191851.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | time | 214581 | 107364.0 | -0.3906 | -271929.3 | 543478.6 | 0/4 | -325611.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 3 | tb | 49778 | 24906.0 | -0.4293 | -57365.7 | 114651.6 | 0/4 | -69818.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | time | 49778 | 24906.0 | -0.4306 | -68777.9 | 137461.2 | 0/4 | -81230.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | tb | 70741 | 35394.7 | -0.4439 | -80146.5 | 160181.8 | 0/4 | -97843.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 3 | tb | 87624 | 43842.0 | -0.4449 | -96679.6 | 193233.4 | 0/4 | -118600.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | time | 70741 | 35394.7 | -0.4551 | -95530.4 | 190929.6 | 0/4 | -113227.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | time | 87625 | 43842.5 | -0.4665 | -117424.6 | 234693.9 | 0/4 | -139345.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | tb | 124175 | 62130.0 | -0.4682 | -138769.1 | 277340.6 | 0/4 | -169834.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | tb | 157926 | 79017.1 | -0.4690 | -175741.7 | 351235.8 | 0/4 | -215250.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | tb | 49778 | 24906.0 | -0.4692 | -57318.1 | 114556.7 | 0/4 | -69771.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | tb | 214579 | 107363.0 | -0.4703 | -237406.4 | 474480.9 | 0/4 | -291087.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | time | 157929 | 79018.6 | -0.4822 | -206667.0 | 413040.7 | 0/4 | -246176.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | tb | 70741 | 35394.7 | -0.4838 | -79809.2 | 159508.0 | 0/4 | -97506.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | tb | 87624 | 43842.0 | -0.4877 | -96768.2 | 193411.8 | 0/4 | -118689.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | time | 124177 | 62131.0 | -0.4938 | -164502.4 | 328769.3 | 0/4 | -195568.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | time | 214583 | 107365.0 | -0.4994 | -277152.6 | 553923.8 | 0/4 | -330835.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | tb | 157927 | 79017.6 | -0.5109 | -173972.1 | 347699.5 | 0/4 | -213480.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | tb | 124176 | 62130.5 | -0.5135 | -138146.9 | 276097.2 | 0/4 | -169212.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | tb | 214581 | 107364.0 | -0.5196 | -236177.6 | 472024.8 | 0/4 | -289859.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | tb | 49778 | 24906.0 | -0.5456 | -57195.9 | 114313.0 | 0/4 | -69648.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | tb | 70741 | 35394.7 | -0.5725 | -79687.6 | 159265.8 | 0/4 | -97385.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | tb | 87625 | 43842.5 | -0.5779 | -96650.3 | 193173.7 | 0/4 | -118571.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | tb | 124177 | 62131.0 | -0.6120 | -137632.0 | 275068.1 | 0/4 | -168697.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | tb | 157929 | 79018.6 | -0.6139 | -174091.5 | 347937.1 | 0/4 | -213600.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | tb | 214583 | 107365.0 | -0.6312 | -236194.9 | 472064.6 | 0/4 | -289877.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |

### F2_cooldown

| N | thr | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 48 | 2.5 | 3 | time | 80568 | 40311.6 | -0.2821 | -102383.9 | 204630.5 | 0/4 | -122539.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 3 | time | 117886 | 58983.4 | -0.2904 | -146207.6 | 292222.0 | 0/4 | -175699.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | time | 133064 | 66577.6 | -0.3024 | -166776.5 | 333323.2 | 0/4 | -200065.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | time | 191355 | 95743.0 | -0.3113 | -239310.2 | 478298.8 | 0/4 | -287181.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | time | 194181 | 97157.0 | -0.3133 | -241934.7 | 483536.2 | 0/4 | -290513.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | time | 289169 | 144683.5 | -0.3212 | -356395.7 | 712286.9 | 0/4 | -428737.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | time | 80568 | 40311.6 | -0.3391 | -103388.8 | 206638.2 | 0/4 | -123544.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | time | 117886 | 58983.4 | -0.3550 | -149842.1 | 299486.9 | 0/4 | -179333.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | time | 133064 | 66577.6 | -0.3599 | -168176.0 | 336120.7 | 0/4 | -201464.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | time | 191356 | 95743.5 | -0.3697 | -240832.1 | 481338.3 | 0/4 | -288703.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | time | 194182 | 97157.5 | -0.3785 | -245280.4 | 490221.4 | 0/4 | -293859.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | time | 289171 | 144684.5 | -0.3816 | -358849.6 | 717200.2 | 0/4 | -431191.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 3 | tb | 80568 | 40311.6 | -0.4052 | -92288.7 | 184449.8 | 0/4 | -112444.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 3 | tb | 117886 | 58983.4 | -0.4285 | -129783.2 | 259395.3 | 0/4 | -159274.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | tb | 133064 | 66577.6 | -0.4306 | -150305.0 | 300402.8 | 0/4 | -183593.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | time | 80569 | 40312.1 | -0.4355 | -106932.9 | 213719.1 | 0/4 | -127089.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | tb | 80568 | 40311.6 | -0.4467 | -92196.0 | 184264.6 | 0/4 | -112351.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | tb | 194181 | 97157.0 | -0.4513 | -216139.0 | 431974.5 | 0/4 | -264717.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | tb | 191355 | 95743.0 | -0.4535 | -211449.5 | 422602.5 | 0/4 | -259321.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | tb | 289169 | 144683.5 | -0.4547 | -316462.7 | 632485.2 | 0/4 | -388804.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | time | 117888 | 58984.4 | -0.4570 | -154744.4 | 309282.4 | 0/4 | -184236.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | time | 133066 | 66578.6 | -0.4647 | -172066.6 | 343897.3 | 0/4 | -205355.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | tb | 117886 | 58983.4 | -0.4705 | -129687.1 | 259204.6 | 0/4 | -159178.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | time | 191360 | 95745.5 | -0.4710 | -247471.2 | 494593.2 | 0/4 | -295344.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | tb | 133064 | 66577.6 | -0.4720 | -149285.3 | 298365.1 | 0/4 | -182574.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | time | 194185 | 97159.0 | -0.4922 | -251446.8 | 502538.9 | 0/4 | -300026.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | time | 289176 | 144687.0 | -0.4931 | -366501.3 | 732499.1 | 0/4 | -438844.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | tb | 191356 | 95743.5 | -0.4951 | -209572.9 | 418852.3 | 0/4 | -257444.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | tb | 194182 | 97157.5 | -0.4978 | -215429.8 | 430557.0 | 0/4 | -264008.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | tb | 289171 | 144684.5 | -0.5038 | -315240.1 | 630041.7 | 0/4 | -387582.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | tb | 80569 | 40312.1 | -0.5354 | -92278.2 | 184429.6 | 0/4 | -112434.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | tb | 117888 | 58984.4 | -0.5632 | -129942.5 | 259712.6 | 0/4 | -159434.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | tb | 133066 | 66578.6 | -0.5704 | -149254.4 | 298304.2 | 0/4 | -182543.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | tb | 191360 | 95745.5 | -0.5960 | -209777.1 | 419259.4 | 0/4 | -257649.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | tb | 194185 | 97159.0 | -0.6015 | -215032.5 | 429763.1 | 0/4 | -263612.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | tb | 289176 | 144687.0 | -0.6147 | -315632.2 | 630830.7 | 0/4 | -387975.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |

### F3_reversal_confirmation

| N | thr | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 24 | 2.5 | 3 | time | 16902 | 8456.8 | -0.2899 | -24284.5 | 48549.8 | 0/4 | -28512.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 3 | time | 23048 | 11531.9 | -0.2982 | -32477.5 | 64910.3 | 0/4 | -38243.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | time | 4298 | 2150.5 | -0.3205 | -7430.6 | 14858.5 | 0/4 | -8505.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | time | 32940 | 16481.3 | -0.3229 | -45068.7 | 90084.4 | 0/4 | -53309.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | time | 52381 | 26208.4 | -0.3254 | -70702.6 | 141312.6 | 0/4 | -83806.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | time | 44107 | 22068.6 | -0.3261 | -59995.7 | 119912.5 | 0/4 | -71030.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | time | 16902 | 8456.8 | -0.3376 | -23730.1 | 47440.4 | 0/4 | -27958.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | time | 23048 | 11531.9 | -0.3631 | -32749.5 | 65453.9 | 0/4 | -38515.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | time | 4298 | 2150.5 | -0.3717 | -6957.4 | 13913.2 | 0/4 | -8032.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | time | 32940 | 16481.3 | -0.3718 | -44257.3 | 88452.0 | 0/4 | -52497.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | time | 52381 | 26208.4 | -0.3807 | -69940.2 | 139784.1 | 0/4 | -83044.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | time | 44107 | 22068.6 | -0.3844 | -59356.8 | 118630.2 | 0/4 | -70391.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 3 | tb | 16902 | 8456.8 | -0.4215 | -20553.1 | 41077.6 | 0/4 | -24781.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 3 | tb | 23048 | 11531.9 | -0.4251 | -28927.7 | 57815.6 | 0/4 | -34693.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | time | 16902 | 8456.8 | -0.4294 | -24613.8 | 49200.5 | 0/4 | -28842.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | tb | 4298 | 2150.5 | -0.4393 | -5473.1 | 10945.8 | 0/4 | -6548.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | tb | 44107 | 22068.6 | -0.4421 | -53074.0 | 106077.7 | 0/4 | -64108.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | time | 23048 | 11531.9 | -0.4537 | -32838.1 | 65630.5 | 0/4 | -38604.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | tb | 16902 | 8456.8 | -0.4574 | -20344.3 | 40660.4 | 0/4 | -24572.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | tb | 32940 | 16481.3 | -0.4575 | -38263.5 | 76473.1 | 0/4 | -46504.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | tb | 52381 | 26208.4 | -0.4579 | -61702.1 | 123323.4 | 0/4 | -74806.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | time | 4298 | 2150.5 | -0.4588 | -7193.6 | 14384.4 | 0/4 | -8268.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | tb | 4298 | 2150.5 | -0.4639 | -5435.1 | 10869.4 | 0/4 | -6510.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | tb | 23048 | 11531.9 | -0.4721 | -29122.9 | 58205.7 | 0/4 | -34888.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | time | 32940 | 16481.3 | -0.4855 | -45127.9 | 90192.5 | 0/4 | -53368.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | tb | 44107 | 22068.6 | -0.4867 | -52642.1 | 105209.8 | 0/4 | -63676.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | time | 44107 | 22068.6 | -0.4914 | -60179.0 | 120273.8 | 0/4 | -71213.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | tb | 32940 | 16481.3 | -0.4990 | -37974.6 | 75895.5 | 0/4 | -46215.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | tb | 52381 | 26208.4 | -0.5005 | -61010.4 | 121936.6 | 0/4 | -74114.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | time | 52381 | 26208.4 | -0.5019 | -71051.5 | 142005.0 | 0/4 | -84155.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | tb | 4298 | 2150.5 | -0.5171 | -5307.6 | 10615.1 | 0/4 | -6382.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | tb | 16902 | 8456.8 | -0.5415 | -20273.1 | 40517.6 | 0/4 | -24501.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | tb | 23048 | 11531.9 | -0.5589 | -28605.1 | 57170.2 | 0/4 | -34371.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | tb | 32940 | 16481.3 | -0.5944 | -37362.2 | 74671.5 | 0/4 | -45602.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | tb | 44107 | 22068.6 | -0.5972 | -52410.8 | 104748.0 | 0/4 | -63445.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | tb | 52381 | 26208.4 | -0.6117 | -60663.0 | 121242.2 | 0/4 | -73767.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |

### F4_cost_gate

| N | thr | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 24 | 2.5 | 3 | time | 67346 | 33696.1 | -0.1948 | -66181.4 | 132309.5 | 0/4 | -83029.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 3 | time | 51939 | 25987.3 | -0.2045 | -54563.7 | 109077.4 | 0/4 | -67557.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | time | 105269 | 52670.6 | -0.2117 | -107862.2 | 215587.5 | 0/4 | -134197.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | time | 82324 | 41190.2 | -0.2148 | -85019.7 | 169922.2 | 0/4 | -105614.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | time | 111348 | 55712.1 | -0.2166 | -113364.7 | 226573.6 | 0/4 | -141220.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | time | 163786 | 81949.1 | -0.2211 | -165836.3 | 331435.1 | 0/4 | -206810.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | time | 67346 | 33696.1 | -0.2435 | -67266.6 | 134448.2 | 0/4 | -84114.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | time | 51939 | 25987.3 | -0.2510 | -54421.5 | 108777.9 | 0/4 | -67415.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | time | 105270 | 52671.1 | -0.2558 | -107342.7 | 214556.6 | 0/4 | -133678.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | time | 82324 | 41190.2 | -0.2606 | -84671.4 | 169226.0 | 0/4 | -105266.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | time | 111349 | 55712.6 | -0.2663 | -114074.3 | 227988.9 | 0/4 | -141930.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | time | 163788 | 81950.1 | -0.2680 | -166484.7 | 332736.4 | 0/4 | -207459.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 3 | tb | 51939 | 25987.3 | -0.3045 | -55348.4 | 110616.5 | 0/4 | -68342.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 3 | tb | 67346 | 33696.1 | -0.3083 | -69234.0 | 138379.8 | 0/4 | -86082.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 3 | tb | 82324 | 41190.2 | -0.3186 | -86802.6 | 173485.5 | 0/4 | -107397.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 3 | tb | 163786 | 81949.1 | -0.3260 | -168841.5 | 337445.5 | 0/4 | -209816.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 3 | tb | 105269 | 52670.6 | -0.3264 | -110672.7 | 221192.4 | 0/4 | -137007.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 3 | tb | 111348 | 55712.1 | -0.3267 | -116899.5 | 233632.7 | 0/4 | -144755.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | time | 67348 | 33697.1 | -0.3316 | -68920.9 | 137753.9 | 0/4 | -85769.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | time | 51939 | 25987.3 | -0.3362 | -54824.0 | 109572.5 | 0/4 | -67817.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 2 | tb | 51939 | 25987.3 | -0.3392 | -55453.4 | 110827.3 | 0/4 | -68447.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 2 | tb | 67346 | 33696.1 | -0.3393 | -68997.8 | 137908.1 | 0/4 | -85845.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | time | 105274 | 52673.1 | -0.3413 | -108866.5 | 217578.1 | 0/4 | -135203.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 2 | tb | 82324 | 41190.2 | -0.3515 | -86155.3 | 172191.7 | 0/4 | -106750.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | time | 82325 | 41190.7 | -0.3531 | -85675.5 | 171231.6 | 0/4 | -106270.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 2 | tb | 105270 | 52671.1 | -0.3562 | -109039.8 | 217934.6 | 0/4 | -135375.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 2 | tb | 111349 | 55712.6 | -0.3622 | -116299.1 | 232431.4 | 0/4 | -144155.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 2 | tb | 163788 | 81950.1 | -0.3626 | -167781.4 | 335326.1 | 0/4 | -208756.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | time | 163792 | 81952.1 | -0.3631 | -168081.9 | 335931.8 | 0/4 | -209058.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | time | 111351 | 55713.6 | -0.3666 | -115655.6 | 231142.4 | 0/4 | -143512.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.5 | 1 | tb | 67348 | 33697.1 | -0.4112 | -69111.0 | 138132.7 | 0/4 | -85959.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.5 | 1 | tb | 51939 | 25987.3 | -0.4112 | -55292.6 | 110509.1 | 0/4 | -68286.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 48 | 2.0 | 1 | tb | 82325 | 41190.7 | -0.4302 | -85970.6 | 171821.2 | 0/4 | -106565.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.5 | 1 | tb | 105274 | 52673.1 | -0.4329 | -108870.2 | 217587.8 | 0/4 | -135206.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 24 | 2.0 | 1 | tb | 111351 | 55713.6 | -0.4442 | -115883.8 | 231601.4 | 0/4 | -143740.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 12 | 2.0 | 1 | tb | 163792 | 81952.1 | -0.4488 | -167949.1 | 335666.2 | 0/4 | -208925.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
