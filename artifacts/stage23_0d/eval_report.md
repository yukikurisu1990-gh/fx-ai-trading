# Stage 23.0d — M15 Donchian First-Touch Breakout + M1 Execution Eval

Generated: 2026-05-06T12:25:20.506446+00:00

Design contract: `docs/design/phase23_0d_m15_donchian_baseline.md`

Universe: 20 pairs, signal TF = `M15`, span = 730d, trigger mode = `first_touch`
Sweep: N (10, 20, 50) × horizon (1, 2, 4) × exit ('tb', 'time') = 18 cells

## Headline verdict

**REJECT**

Per-cell verdict counts: 18 REJECT / 0 PROMISING_BUT_NEEDS_OOS / 0 ADOPT_CANDIDATE — out of 18 cells.

REJECT reason breakdown:
- under_firing: 0 cell(s)
- still_overtrading: 18 cell(s)
- pnl_edge_insufficient: 0 cell(s)
- robustness_failure: 0 cell(s)

Best cell: `N=50, horizon=4, exit=time` (Sharpe -0.1616, annual_pnl -60361.3 pip, n_trades 45229)

## Interpretation note carried from 23.0c

**The 23.0c REJECT was not a complete dismissal of M5 z-score MR.** All 36 cells were classified `still_overtrading`, meaning trade volume was reduced 2-5× by first-touch but remained above the 1000-trade warning threshold; per-trade EV was dominated by spread cost. This is consistent with **insufficient signal firing precision**, not with 'M5 z-score MR has no edge'.

23.0d's design therefore considers first-touch a *partial* fix and documents follow-up signal-quality controls (see Phase 23 routing below).

## Phase 23 routing on 23.0d outcome

```
23.0d returns:
├── ADOPT_CANDIDATE / PROMISING_BUT_NEEDS_OOS
│     → 23.0e (meta-labeling on best 23.0b/c/d cell) triggers
│     → 23.0d-v2 (frozen-cell strict OOS) mandatory before production
│
└── REJECT (any reason)
      ├── If any 23.0b/c/d cell has positive realistic-exit Sharpe
      │     → 23.0e meta-labeling on that cell triggers
      │
      └── If NO 23.0b/c/d cell has positive realistic-exit Sharpe
            → 23.0e DOES NOT trigger
            → 23.0c-rev1 (signal-quality control study) is the next candidate
              with fixed (non-search) controls layered on 23.0c first-touch:
              • neutral reset: re-entry only after z returns to [-0.5, +0.5]
              • cooldown: 3 M5 bars block after any fire
              • reversal confirmation: z direction + mid_c direction agree
              • fixed cost gate: cost_ratio_at_entry <= 0.6
            → If 23.0c-rev1 also fails, Phase 23 closes with the
              negative-but-bounded conclusion
```

**Phase 23 closure must distinguish two failure modes** (per design §7.2):
1. *Cost regime alone (M5/M15 vs M1) was insufficient for naive / weakly-controlled signal firing* — supported by 23.0b/0c (and 23.0d, if it REJECTs).
2. *M5/M15 has no recoverable edge even with stronger signal-quality controls* — would require 23.0c-rev1 also failing across all four candidate filters.
These are different conclusions; closure must NOT short-circuit (1) into (2).

## Production-readiness

Even an `ADOPT_CANDIDATE` verdict is **not** production-ready. The S1 strict OOS is computed *after* the in-sample sweep selected the best cell from 18 cells × 20 pairs (multiple-testing surface). A separate `23.0d-v2` PR with frozen-cell strict OOS validation on chronologically out-of-sample data and no parameter re-search is required before any production migration.

## Trigger semantics

- Trigger mode: `first_touch` (rising-edge crossing of the band, with shift(1) on both `mid_c` and the band itself for causality).
- Same-direction re-entry locked while price stays beyond the band; long-side and short-side locks independent.
- **Continuous trigger is not the Phase 23 default because 23.0b showed continuous-trigger overtrading.**

## Gate thresholds (Phase 22 inherited, identical to 23.0b/0c)

- A0: annual_trades >= 70.0 (overtrading warning if > 1000.0, NOT blocking)
- A1: per-trade Sharpe (ddof=0, no √N) >= +0.082
- A2: annual_pnl_pip >= +180.0
- A3: max_dd_pip <= 200.0
- A4: 5-fold chronological, drop k=0, eval k=1..4, count(Sharpe > 0) >= 3/4
- A5: annual_pnl after subtracting 0.5 pip per round trip > 0

## Sweep summary (all cells, sorted by Sharpe)

| N | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 50 | 4 | time | 45229 | 22630.0 | -0.1616 | -60361.3 | 120681.8 | 0/4 | -71676.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 20 | 4 | time | 73510 | 36780.2 | -0.1767 | -102264.3 | 204436.2 | 0/4 | -120654.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 10 | 4 | time | 106324 | 53198.4 | -0.1894 | -152429.1 | 304727.5 | 0/4 | -179028.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 50 | 2 | time | 45234 | 22632.5 | -0.2098 | -58174.0 | 116270.6 | 0/4 | -69490.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 20 | 2 | time | 73514 | 36782.2 | -0.2380 | -100954.2 | 201776.0 | 0/4 | -119345.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 50 | 4 | tb | 45229 | 22630.0 | -0.2459 | -57227.4 | 114386.4 | 0/4 | -68542.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 10 | 2 | time | 106328 | 53200.4 | -0.2540 | -150090.7 | 299981.6 | 0/4 | -176690.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 20 | 4 | tb | 73510 | 36780.2 | -0.2657 | -95402.5 | 190692.4 | 0/4 | -113792.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 10 | 4 | tb | 106324 | 53198.4 | -0.2794 | -140594.6 | 281012.2 | 0/4 | -167193.8 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 50 | 2 | tb | 45234 | 22632.5 | -0.2802 | -56361.8 | 112642.8 | 0/4 | -67678.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 50 | 1 | time | 45236 | 22633.5 | -0.2861 | -58569.5 | 117074.8 | 0/4 | -69886.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 20 | 2 | tb | 73514 | 36782.2 | -0.3064 | -94532.8 | 188939.7 | 0/4 | -112923.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 20 | 1 | time | 73516 | 36783.2 | -0.3141 | -99419.7 | 198719.4 | 0/4 | -117811.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 10 | 2 | tb | 106328 | 53200.4 | -0.3245 | -138703.5 | 277217.9 | 0/4 | -165303.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 10 | 1 | time | 106330 | 53201.4 | -0.3319 | -147031.4 | 293873.1 | 0/4 | -173632.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 50 | 1 | tb | 45236 | 22633.5 | -0.3377 | -55954.8 | 111844.0 | 0/4 | -67271.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 20 | 1 | tb | 73516 | 36783.2 | -0.3628 | -92370.5 | 184625.7 | 0/4 | -110762.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| 10 | 1 | tb | 106330 | 53201.4 | -0.3843 | -134909.2 | 269639.7 | 0/4 | -161509.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |

## Did first-touch + M15 fix overtrading?

- 23.0d annual_trades distribution across 18 cells: min 22630.0 / median 36782.2 / max 53201.4
- Cells triggering overtrading warning (`> 1000`): 18 / 18
- 23.0b reference (continuous-trigger Donchian, M5): annual_trades 105,275 – 249,507 across 18 cells; ALL 18 triggered the warning.
- 23.0c reference (first-touch z-score MR, M5): annual_trades 43,378 – 157,058 across 36 cells; ALL 36 triggered the warning.

## Best cell deep-dive

- N=50, horizon=4, exit=time
- n_trades = 45229 (long 24123 / short 21106)
- annual_trades = 22630.0 — **OVERTRADING WARNING** (> 1000)
- Sharpe = -0.1616
- annual_pnl = -60361.3 pip
- max_dd = 120681.8 pip
- A4 fold Sharpes (k=1..4): -0.1437, -0.1566, -0.1930, -0.2117
- A5 stressed annual_pnl = -71676.3 pip

### band_distance_at_entry distribution (|pip| beyond band)

- p10 = 0.350, p25 = 0.900, p50 = 2.300, p75 = 5.050, p90 = 9.850

### breakout_holding_diagnostic (forward-path, diagnostic only)

- n_trades evaluated: 45229
- M1 bars beyond band (p25/p50/p75): 21.0 / 47.0 / 60.0
- Fraction held the full horizon: 0.2794
- (Forward-path diagnostic only — NOT used for ADOPT decisions or features.)

### Diagnostics (NOT gates)

- hit_rate = 0.3770
- payoff_asymmetry = 0.9754
- S0 random-entry Sharpe = -0.1986
- S1 strict 80/20 OOS: IS Sharpe -0.1509 (n=36183), OOS Sharpe -0.2117 (n=9046), oos/is ratio +nan

### Per-pair contribution

| pair | n_trades | Sharpe | annual_pnl | hit_rate |
|---|---|---|---|---|
| USD_JPY | 2423 | -0.0665 | -1779.3 | 0.4482 |
| EUR_JPY | 2213 | -0.1124 | -2938.9 | 0.4216 |
| AUD_JPY | 2253 | -0.1203 | -2459.4 | 0.3964 |
| GBP_JPY | 2298 | -0.1218 | -4054.2 | 0.4321 |
| USD_CHF | 2338 | -0.1444 | -1743.5 | 0.3837 |
| EUR_USD | 2350 | -0.1515 | -2369.1 | 0.3868 |
| GBP_USD | 2451 | -0.1681 | -3016.4 | 0.4002 |
| EUR_AUD | 2141 | -0.1781 | -4284.9 | 0.3643 |
| CHF_JPY | 2309 | -0.1850 | -4577.2 | 0.3872 |
| AUD_USD | 2249 | -0.1851 | -2002.0 | 0.3815 |
| GBP_AUD | 2153 | -0.1988 | -4997.7 | 0.3730 |
| NZD_USD | 2382 | -0.1998 | -1968.2 | 0.3766 |
| NZD_JPY | 2266 | -0.2125 | -3587.3 | 0.3614 |
| USD_CAD | 2390 | -0.2142 | -3070.9 | 0.3753 |
| EUR_GBP | 2088 | -0.2175 | -1561.6 | 0.3578 |
| GBP_CHF | 2196 | -0.2228 | -3084.0 | 0.3689 |
| EUR_CAD | 2278 | -0.2291 | -3864.7 | 0.3657 |
| EUR_CHF | 2136 | -0.2749 | -2475.3 | 0.3399 |
| AUD_CAD | 2152 | -0.2789 | -3097.4 | 0.3243 |
| AUD_NZD | 2163 | -0.3752 | -3429.2 | 0.2769 |

### Per-session contribution

| session | n_trades | Sharpe | annual_pnl | hit_rate |
|---|---|---|---|---|
| American (12-18 UTC) | 14145 | -0.1277 | -17092.4 | 0.4060 |
| Asian (00-06 UTC) | 10338 | -0.1603 | -11671.3 | 0.3580 |
| European (06-12 UTC) | 14907 | -0.1474 | -17078.5 | 0.3940 |
| Late (18-24 UTC) | 5839 | -0.3023 | -14519.0 | 0.2973 |
