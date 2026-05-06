# Stage 24.0a — Path-EV Characterisation + Frozen Entry Stream Selection

Generated: 2026-05-06T14:37:34.038980+00:00

Design contract: `docs/design/phase24_0a_path_ev_characterisation.md`

Universe: 20 pairs (canonical 20). Span = 730d. Cells evaluated: 216 / total Phase 23 cells: 216.

## Mandatory caveats

**best_possible_pnl is an ex-post path diagnostic, not an executable PnL. Frozen entry streams are selected for exit-study eligibility only, not for production. Path-EV magnitude indicates path-side upside availability that exit-side improvements may attempt to capture; it does NOT guarantee that any exit logic will succeed in converting that path-EV into realised PnL.**

**positive_rate(best_possible_pnl > 0) is path-side upside availability rate, NOT trade win rate.** A trade with `best_possible_pnl > 0` means the price moved in the favourable direction at some point during the holding window after entry-side spread; whether the trade closed positive depends on the exit logic (which is the entire question Phase 24 is investigating).

## Headline verdict

**OK — 116 eligible cell(s) out of 216; top-K=3 frozen for 24.0b/c/d/e.**

## Score formula and weights (FIXED in this PR)

- Axis 1 (primary, weight +1.0): `mean(best_possible_pnl)`
- Axis 2 (auxiliary, weight +0.3): `realised_gap = mean(best_possible_pnl) - mean(max(tb_pnl, time_exit_pnl))`
- Axis 3 (risk-path penalty, weight -0.5): `mean(|mae_after_cost|)`
- K = 3. Tie-breaker: lower `mean(|mae_after_cost|)`.
- `p75(best_possible_pnl)` is reported as diagnostic only — NOT in the score.

## Eligibility constraints (FIXED in this PR; H1 path-EV criteria included)

- `annual_trades >= 70.0`
- `max_pair_share <= 0.5`
- `min_fold_share >= 0.1`
- `mean(best_possible_pnl) > 0.0`
- `p75(best_possible_pnl) > 0.0`
- `positive_rate(best_possible_pnl > 0) >= 0.55`

### Eligibility violation breakdown (cells failing each constraint)

- `annual_trades_lt_70`: 0 / 216 cells
- `max_pair_share_gt_0_5`: 0 / 216 cells
- `min_fold_share_lt_0_10`: 0 / 216 cells
- `mean_best_le_0`: 16 / 216 cells
- `p75_best_le_0`: 0 / 216 cells
- `positive_rate_lt_0_55`: 100 / 216 cells

## Top-K frozen entry streams

| rank | source | filter | cell_params | score | mean_best | p75_best | positive_rate | annual_tr | mae | gap |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 23.0d (PR #266, d929867) | - | N=50, horizon_bars=4, exit_rule=tb | +3.6992 | +7.944 | +10.700 | 0.7876 | 22630.0 | 12.851 | +7.271 |
| 2 | 23.0d (PR #266, d929867) | - | N=50, horizon_bars=4, exit_rule=time | +3.6992 | +7.944 | +10.700 | 0.7876 | 22630.0 | 12.851 | +7.271 |
| 3 | 23.0d (PR #266, d929867) | - | N=20, horizon_bars=4, exit_rule=tb | +3.0684 | +7.310 | +10.000 | 0.7724 | 36780.2 | 12.571 | +6.813 |

## Per-stage summary

| stage | cells | eligible | best score | median ann_tr | median mean_best |
|---|---|---|---|---|---|
| 23.0b | 18 | 6 | -0.2820 | 173209.1 | +1.310 |
| 23.0c | 36 | 14 | -0.5089 | 87104.1 | +1.248 |
| 23.0d | 18 | 18 | +3.6992 | 36782.2 | +4.517 |
| 23.0c-rev1 | 144 | 78 | +1.2063 | 42516.4 | +1.464 |

## Full ranking (all cells, sorted by score descending)

| rank | source | filter | cell_params | eligible | score | mean_best | p75_best | positive_rate | annual_tr | mae | gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 23.0d | - | N=50, horizon_bars=4, exit_rule=tb | ✓ | +3.6992 | +7.944 | +10.700 | 0.7876 | 22630.0 | 12.851 | +7.271 |
| 2 | 23.0d | - | N=50, horizon_bars=4, exit_rule=time | ✓ | +3.6992 | +7.944 | +10.700 | 0.7876 | 22630.0 | 12.851 | +7.271 |
| 3 | 23.0d | - | N=20, horizon_bars=4, exit_rule=tb | ✓ | +3.0684 | +7.310 | +10.000 | 0.7724 | 36780.2 | 12.571 | +6.813 |
| 4 | 23.0d | - | N=20, horizon_bars=4, exit_rule=time | ✓ | +3.0684 | +7.310 | +10.000 | 0.7724 | 36780.2 | 12.571 | +6.813 |
| 5 | 23.0d | - | N=10, horizon_bars=4, exit_rule=tb | ✓ | +2.5917 | +6.790 | +9.300 | 0.7589 | 53198.4 | 12.305 | +6.515 |
| 6 | 23.0d | - | N=10, horizon_bars=4, exit_rule=time | ✓ | +2.5917 | +6.790 | +9.300 | 0.7589 | 53198.4 | 12.305 | +6.515 |
| 7 | 23.0d | - | N=50, horizon_bars=2, exit_rule=tb | ✓ | +1.8839 | +5.080 | +7.100 | 0.7106 | 22632.5 | 9.908 | +5.859 |
| 8 | 23.0d | - | N=50, horizon_bars=2, exit_rule=time | ✓ | +1.8839 | +5.080 | +7.100 | 0.7106 | 22632.5 | 9.908 | +5.859 |
| 9 | 23.0d | - | N=20, horizon_bars=2, exit_rule=tb | ✓ | +1.3111 | +4.517 | +6.400 | 0.6898 | 36782.2 | 9.689 | +5.461 |
| 10 | 23.0d | - | N=20, horizon_bars=2, exit_rule=time | ✓ | +1.3111 | +4.517 | +6.400 | 0.6898 | 36782.2 | 9.689 | +5.461 |
| 11 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | +1.2063 | +4.271 | +6.100 | 0.7485 | 25987.3 | 8.874 | +4.576 |
| 12 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | +1.2063 | +4.271 | +6.100 | 0.7485 | 25987.3 | 8.874 | +4.576 |
| 13 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | +1.1965 | +4.195 | +6.000 | 0.7483 | 33696.1 | 8.634 | +4.396 |
| 14 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | +1.1965 | +4.195 | +6.000 | 0.7483 | 33696.1 | 8.634 | +4.396 |
| 15 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | +1.0703 | +3.949 | +5.700 | 0.7364 | 41190.2 | 8.390 | +4.386 |
| 16 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | +1.0703 | +3.949 | +5.700 | 0.7364 | 41190.2 | 8.390 | +4.386 |
| 17 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | +1.0018 | +3.882 | +5.600 | 0.7355 | 52670.6 | 8.328 | +4.281 |
| 18 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | +1.0018 | +3.882 | +5.600 | 0.7355 | 52670.6 | 8.328 | +4.281 |
| 19 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | +0.9803 | +3.825 | +5.500 | 0.7321 | 55712.1 | 8.253 | +4.272 |
| 20 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | +0.9803 | +3.825 | +5.500 | 0.7321 | 55712.1 | 8.253 | +4.272 |
| 21 | 23.0d | - | N=10, horizon_bars=2, exit_rule=tb | ✓ | +0.9290 | +4.099 | +5.900 | 0.6727 | 53200.4 | 9.451 | +5.186 |
| 22 | 23.0d | - | N=10, horizon_bars=2, exit_rule=time | ✓ | +0.9290 | +4.099 | +5.900 | 0.6727 | 53200.4 | 9.451 | +5.186 |
| 23 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | +0.9161 | +3.673 | +5.300 | 0.7261 | 81949.1 | 8.027 | +4.190 |
| 24 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | +0.9161 | +3.673 | +5.300 | 0.7261 | 81949.1 | 8.027 | +4.190 |
| 25 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.5, horizon_bars=2, exit_rule=tb | ✓ | +0.5033 | +3.157 | +4.600 | 0.6944 | 25987.3 | 7.714 | +4.012 |
| 26 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.5, horizon_bars=2, exit_rule=time | ✓ | +0.5033 | +3.157 | +4.600 | 0.6944 | 25987.3 | 7.714 | +4.012 |
| 27 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.5, horizon_bars=2, exit_rule=tb | ✓ | +0.4878 | +3.077 | +4.500 | 0.6950 | 33696.1 | 7.490 | +3.854 |
| 28 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.5, horizon_bars=2, exit_rule=time | ✓ | +0.4878 | +3.077 | +4.500 | 0.6950 | 33696.1 | 7.490 | +3.854 |
| 29 | 23.0d | - | N=50, horizon_bars=1, exit_rule=tb | ✓ | +0.4575 | +2.975 | +4.400 | 0.6178 | 22633.5 | 7.821 | +4.643 |
| 30 | 23.0d | - | N=50, horizon_bars=1, exit_rule=time | ✓ | +0.4575 | +2.975 | +4.400 | 0.6178 | 22633.5 | 7.821 | +4.643 |
| 31 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.0, horizon_bars=2, exit_rule=tb | ✓ | +0.3717 | +2.868 | +4.300 | 0.6795 | 41190.2 | 7.286 | +3.820 |
| 32 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.0, horizon_bars=2, exit_rule=time | ✓ | +0.3717 | +2.868 | +4.300 | 0.6795 | 41190.2 | 7.286 | +3.820 |
| 33 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.5, horizon_bars=2, exit_rule=tb | ✓ | +0.3305 | +2.822 | +4.200 | 0.6800 | 52671.1 | 7.219 | +3.728 |
| 34 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.5, horizon_bars=2, exit_rule=time | ✓ | +0.3305 | +2.822 | +4.200 | 0.6800 | 52671.1 | 7.219 | +3.728 |
| 35 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.0, horizon_bars=2, exit_rule=tb | ✓ | +0.2973 | +2.757 | +4.200 | 0.6755 | 55712.6 | 7.153 | +3.721 |
| 36 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.0, horizon_bars=2, exit_rule=time | ✓ | +0.2973 | +2.757 | +4.200 | 0.6755 | 55712.6 | 7.153 | +3.721 |
| 37 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.0, horizon_bars=2, exit_rule=tb | ✓ | +0.2450 | +2.632 | +4.000 | 0.6687 | 81950.1 | 6.959 | +3.641 |
| 38 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.0, horizon_bars=2, exit_rule=time | ✓ | +0.2450 | +2.632 | +4.000 | 0.6687 | 81950.1 | 6.959 | +3.641 |
| 39 | 23.0d | - | N=20, horizon_bars=1, exit_rule=tb | ✓ | -0.0125 | +2.535 | +4.000 | 0.5935 | 36783.2 | 7.658 | +4.273 |
| 40 | 23.0d | - | N=20, horizon_bars=1, exit_rule=time | ✓ | -0.0125 | +2.535 | +4.000 | 0.5935 | 36783.2 | 7.658 | +4.273 |
| 41 | 23.0b | - | N=50, horizon_bars=3, exit_rule=tb | ✓ | -0.2820 | +2.555 | +3.900 | 0.5941 | 105275.1 | 7.730 | +3.428 |
| 42 | 23.0b | - | N=50, horizon_bars=3, exit_rule=time | ✓ | -0.2820 | +2.555 | +3.900 | 0.5941 | 105275.1 | 7.730 | +3.428 |
| 43 | 23.0d | - | N=10, horizon_bars=1, exit_rule=tb | ✓ | -0.3285 | +2.203 | +3.500 | 0.5734 | 53201.4 | 7.476 | +4.022 |
| 44 | 23.0d | - | N=10, horizon_bars=1, exit_rule=time | ✓ | -0.3285 | +2.203 | +3.500 | 0.5734 | 53201.4 | 7.476 | +4.022 |
| 45 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.5, horizon_bars=1, exit_rule=tb | ✓ | -0.5046 | +1.649 | +2.700 | 0.5795 | 25987.3 | 6.179 | +3.120 |
| 46 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.5, horizon_bars=1, exit_rule=time | ✓ | -0.5046 | +1.649 | +2.700 | 0.5795 | 25987.3 | 6.179 | +3.120 |
| 47 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.5054 | +2.615 | +4.200 | 0.6351 | 40311.6 | 8.204 | +3.272 |
| 48 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.5054 | +2.615 | +4.200 | 0.6351 | 40311.6 | 8.204 | +3.272 |
| 49 | 23.0c | - | N=48, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.5089 | +2.599 | +4.200 | 0.6355 | 43378.2 | 8.176 | +3.267 |
| 50 | 23.0c | - | N=48, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.5089 | +2.599 | +4.200 | 0.6355 | 43378.2 | 8.176 | +3.267 |
| 51 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.5, horizon_bars=1, exit_rule=tb | ✓ | -0.5211 | +1.591 | +2.700 | 0.5787 | 33697.1 | 6.019 | +2.993 |
| 52 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.5, horizon_bars=1, exit_rule=time | ✓ | -0.5211 | +1.591 | +2.700 | 0.5787 | 33697.1 | 6.019 | +2.993 |
| 53 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.0, horizon_bars=1, exit_rule=tb | ✓ | -0.6211 | +1.415 | +2.400 | 0.5595 | 41190.7 | 5.834 | +2.938 |
| 54 | 23.0c-rev1 | F4_cost_gate | N=48, threshold=2.0, horizon_bars=1, exit_rule=time | ✓ | -0.6211 | +1.415 | +2.400 | 0.5595 | 41190.7 | 5.834 | +2.938 |
| 55 | 23.0b | - | N=20, horizon_bars=3, exit_rule=tb | ✓ | -0.6268 | +2.162 | +3.500 | 0.5704 | 173208.1 | 7.445 | +3.113 |
| 56 | 23.0b | - | N=20, horizon_bars=3, exit_rule=time | ✓ | -0.6268 | +2.162 | +3.500 | 0.5704 | 173208.1 | 7.445 | +3.113 |
| 57 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.6276 | +2.546 | +4.200 | 0.6278 | 11531.9 | 8.426 | +3.464 |
| 58 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.6276 | +2.546 | +4.200 | 0.6278 | 11531.9 | 8.426 | +3.464 |
| 59 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.5, horizon_bars=1, exit_rule=tb | ✓ | -0.6319 | +1.407 | +2.400 | 0.5616 | 52673.1 | 5.808 | +2.886 |
| 60 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.5, horizon_bars=1, exit_rule=time | ✓ | -0.6319 | +1.407 | +2.400 | 0.5616 | 52673.1 | 5.808 | +2.886 |
| 61 | 23.0c | - | N=48, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.6490 | +2.260 | +3.700 | 0.6105 | 72081.3 | 7.645 | +3.046 |
| 62 | 23.0c | - | N=48, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.6490 | +2.260 | +3.700 | 0.6105 | 72081.3 | 7.645 | +3.046 |
| 63 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.6547 | +2.266 | +3.700 | 0.6104 | 66577.6 | 7.670 | +3.048 |
| 64 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.6547 | +2.266 | +3.700 | 0.6104 | 66577.6 | 7.670 | +3.048 |
| 65 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.0, horizon_bars=1, exit_rule=tb | ✓ | -0.6691 | +1.339 | +2.300 | 0.5555 | 55713.6 | 5.739 | +2.870 |
| 66 | 23.0c-rev1 | F4_cost_gate | N=24, threshold=2.0, horizon_bars=1, exit_rule=time | ✓ | -0.6691 | +1.339 | +2.300 | 0.5555 | 55713.6 | 5.739 | +2.870 |
| 67 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.7484 | +2.473 | +4.000 | 0.6220 | 24906.0 | 8.296 | +3.088 |
| 68 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.7484 | +2.473 | +4.000 | 0.6220 | 24906.0 | 8.296 | +3.088 |
| 69 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.7535 | +2.260 | +3.700 | 0.6069 | 58983.4 | 7.767 | +2.899 |
| 70 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.7535 | +2.260 | +3.700 | 0.6069 | 58983.4 | 7.767 | +2.899 |
| 71 | 23.0b | - | N=10, horizon_bars=3, exit_rule=tb | ✓ | -0.7597 | +1.978 | +3.300 | 0.5587 | 249502.3 | 7.271 | +2.993 |
| 72 | 23.0b | - | N=10, horizon_bars=3, exit_rule=time | ✓ | -0.7597 | +1.978 | +3.300 | 0.5587 | 249502.3 | 7.271 | +2.993 |
| 73 | 23.0c | - | N=24, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.7626 | +2.246 | +3.700 | 0.6073 | 63306.3 | 7.757 | +2.901 |
| 74 | 23.0c | - | N=24, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.7626 | +2.246 | +3.700 | 0.6073 | 63306.3 | 7.757 | +2.901 |
| 75 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.7798 | +2.145 | +3.700 | 0.6012 | 22068.6 | 7.748 | +3.164 |
| 76 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.7798 | +2.145 | +3.700 | 0.6012 | 22068.6 | 7.748 | +3.164 |
| 77 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.8406 | +2.444 | +4.200 | 0.6176 | 8456.8 | 8.503 | +3.222 |
| 78 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.8406 | +2.444 | +4.200 | 0.6176 | 8456.8 | 8.503 | +3.222 |
| 79 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.8499 | +2.004 | +3.400 | 0.5892 | 97157.0 | 7.397 | +2.814 |
| 80 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.8499 | +2.004 | +3.400 | 0.5892 | 97157.0 | 7.397 | +2.814 |
| 81 | 23.0c | - | N=24, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.8505 | +1.997 | +3.400 | 0.5886 | 105309.1 | 7.384 | +2.815 |
| 82 | 23.0c | - | N=24, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.8505 | +1.997 | +3.400 | 0.5886 | 105309.1 | 7.384 | +2.815 |
| 83 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.8519 | +2.206 | +3.700 | 0.6032 | 35394.7 | 7.863 | +2.911 |
| 84 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.8519 | +2.206 | +3.700 | 0.6032 | 35394.7 | 7.863 | +2.911 |
| 85 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.8656 | +1.879 | +3.200 | 0.5789 | 144683.5 | 7.137 | +2.745 |
| 86 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.8656 | +1.879 | +3.200 | 0.5789 | 144683.5 | 7.137 | +2.745 |
| 87 | 23.0c | - | N=12, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.8683 | +1.875 | +3.200 | 0.5791 | 157054.5 | 7.134 | +2.744 |
| 88 | 23.0c | - | N=12, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.8683 | +1.875 | +3.200 | 0.5791 | 157054.5 | 7.134 | +2.744 |
| 89 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.8699 | +1.986 | +3.400 | 0.5877 | 95743.0 | 7.375 | +2.771 |
| 90 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.8699 | +1.986 | +3.400 | 0.5877 | 95743.0 | 7.375 | +2.771 |
| 91 | 23.0c | - | N=12, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.8706 | +1.988 | +3.400 | 0.5885 | 102125.9 | 7.379 | +2.771 |
| 92 | 23.0c | - | N=12, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.8706 | +1.988 | +3.400 | 0.5885 | 102125.9 | 7.379 | +2.771 |
| 93 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.9180 | +2.115 | +3.600 | 0.5960 | 43842.0 | 7.730 | +2.774 |
| 94 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.9180 | +2.115 | +3.600 | 0.5960 | 43842.0 | 7.730 | +2.774 |
| 95 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.9189 | +1.976 | +3.400 | 0.5904 | 26208.4 | 7.564 | +2.957 |
| 96 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.9189 | +1.976 | +3.400 | 0.5904 | 26208.4 | 7.564 | +2.957 |
| 97 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -0.9693 | +1.876 | +3.200 | 0.5803 | 79017.1 | 7.314 | +2.707 |
| 98 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -0.9693 | +1.876 | +3.200 | 0.5803 | 79017.1 | 7.314 | +2.707 |
| 99 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -0.9828 | +1.775 | +3.100 | 0.5717 | 107363.0 | 7.123 | +2.681 |
| 100 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -0.9828 | +1.775 | +3.100 | 0.5717 | 107363.0 | 7.123 | +2.681 |
| 101 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -1.0013 | +1.902 | +3.300 | 0.5802 | 62130.0 | 7.428 | +2.703 |
| 102 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -1.0013 | +1.902 | +3.300 | 0.5802 | 62130.0 | 7.428 | +2.703 |
| 103 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.0, horizon_bars=3, exit_rule=tb | ✓ | -1.0225 | +1.926 | +3.400 | 0.5819 | 16481.3 | 7.609 | +2.852 |
| 104 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.0, horizon_bars=3, exit_rule=time | ✓ | -1.0225 | +1.926 | +3.400 | 0.5819 | 16481.3 | 7.609 | +2.852 |
| 105 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.5, horizon_bars=2, exit_rule=tb | ✓ | -1.1328 | +1.673 | +3.100 | 0.5692 | 40311.6 | 7.272 | +2.767 |
| 106 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.5, horizon_bars=2, exit_rule=time | ✓ | -1.1328 | +1.673 | +3.100 | 0.5692 | 40311.6 | 7.272 | +2.767 |
| 107 | 23.0c | - | N=48, threshold=2.5, horizon_bars=2, exit_rule=tb | ✓ | -1.1329 | +1.658 | +3.100 | 0.5690 | 43378.2 | 7.242 | +2.766 |
| 108 | 23.0c | - | N=48, threshold=2.5, horizon_bars=2, exit_rule=time | ✓ | -1.1329 | +1.658 | +3.100 | 0.5690 | 43378.2 | 7.242 | +2.766 |
| 109 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.5, horizon_bars=2, exit_rule=tb | ✓ | -1.2206 | +1.592 | +3.000 | 0.5604 | 11531.9 | 7.423 | +2.998 |
| 110 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.5, horizon_bars=2, exit_rule=time | ✓ | -1.2206 | +1.592 | +3.000 | 0.5604 | 11531.9 | 7.423 | +2.998 |
| 111 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.5, horizon_bars=2, exit_rule=tb | ✓ | -1.3676 | +1.547 | +3.000 | 0.5572 | 24906.0 | 7.379 | +2.583 |
| 112 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.5, horizon_bars=2, exit_rule=time | ✓ | -1.3676 | +1.547 | +3.000 | 0.5572 | 24906.0 | 7.379 | +2.583 |
| 113 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.5, horizon_bars=2, exit_rule=tb | ✓ | -1.4302 | +1.513 | +3.000 | 0.5506 | 8456.8 | 7.512 | +2.709 |
| 114 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.5, horizon_bars=2, exit_rule=time | ✓ | -1.4302 | +1.513 | +3.000 | 0.5506 | 8456.8 | 7.512 | +2.709 |
| 115 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.5, horizon_bars=3, exit_rule=tb | ✓ | -1.5439 | +2.144 | +4.000 | 0.5917 | 2150.5 | 9.158 | +2.969 |
| 116 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.5, horizon_bars=3, exit_rule=time | ✓ | -1.5439 | +2.144 | +4.000 | 0.5917 | 2150.5 | 9.158 | +2.969 |
| 117 | 23.0b | - | N=50, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.651 | +2.800 | 0.5307 | 105275.6 | 6.789 | +2.954 |
| 118 | 23.0b | - | N=50, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.651 | +2.800 | 0.5307 | 105275.6 | 6.789 | +2.954 |
| 119 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.379 | +2.700 | 0.5414 | 66577.6 | 6.789 | +2.567 |
| 120 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.379 | +2.700 | 0.5414 | 66577.6 | 6.789 | +2.567 |
| 121 | 23.0c | - | N=48, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.370 | +2.700 | 0.5412 | 72081.3 | 6.768 | +2.564 |
| 122 | 23.0c | - | N=48, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.370 | +2.700 | 0.5412 | 72081.3 | 6.768 | +2.564 |
| 123 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.5, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.359 | +2.700 | 0.5396 | 58983.4 | 6.889 | +2.437 |
| 124 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.5, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.359 | +2.700 | 0.5396 | 58983.4 | 6.889 | +2.437 |
| 125 | 23.0c | - | N=24, threshold=2.5, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.345 | +2.700 | 0.5397 | 63306.3 | 6.877 | +2.437 |
| 126 | 23.0c | - | N=24, threshold=2.5, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.345 | +2.700 | 0.5397 | 63306.3 | 6.877 | +2.437 |
| 127 | 23.0b | - | N=20, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.310 | +2.400 | 0.5040 | 173209.1 | 6.546 | +2.664 |
| 128 | 23.0b | - | N=20, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.310 | +2.400 | 0.5040 | 173209.1 | 6.546 | +2.664 |
| 129 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.306 | +2.700 | 0.5358 | 35394.7 | 6.985 | +2.425 |
| 130 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.306 | +2.700 | 0.5358 | 35394.7 | 6.985 | +2.425 |
| 131 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.269 | +2.600 | 0.5303 | 22068.6 | 6.829 | +2.678 |
| 132 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.269 | +2.600 | 0.5303 | 22068.6 | 6.829 | +2.678 |
| 133 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | +1.248 | +2.300 | 0.5461 | 81952.1 | 5.590 | +2.796 |
| 134 | 23.0c-rev1 | F4_cost_gate | N=12, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | +1.248 | +2.300 | 0.5461 | 81952.1 | 5.590 | +2.796 |
| 135 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.5, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.234 | +2.600 | 0.5283 | 43842.0 | 6.869 | +2.331 |
| 136 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.5, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.234 | +2.600 | 0.5283 | 43842.0 | 6.869 | +2.331 |
| 137 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.5, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.213 | +3.000 | 0.5265 | 2150.5 | 8.196 | +2.395 |
| 138 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.5, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.213 | +3.000 | 0.5265 | 2150.5 | 8.196 | +2.395 |
| 139 | 23.0c | - | N=12, threshold=2.5, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.152 | +2.400 | 0.5191 | 102126.4 | 6.537 | +2.318 |
| 140 | 23.0c | - | N=12, threshold=2.5, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.152 | +2.400 | 0.5191 | 102126.4 | 6.537 | +2.318 |
| 141 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.5, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.151 | +2.400 | 0.5185 | 95743.5 | 6.534 | +2.315 |
| 142 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.5, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.151 | +2.400 | 0.5185 | 95743.5 | 6.534 | +2.315 |
| 143 | 23.0b | - | N=10, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.151 | +2.200 | 0.4912 | 249503.8 | 6.404 | +2.557 |
| 144 | 23.0b | - | N=10, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.151 | +2.200 | 0.4912 | 249503.8 | 6.404 | +2.557 |
| 145 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.150 | +2.400 | 0.5192 | 97157.5 | 6.547 | +2.359 |
| 146 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.150 | +2.400 | 0.5192 | 97157.5 | 6.547 | +2.359 |
| 147 | 23.0c | - | N=24, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.141 | +2.400 | 0.5184 | 105309.6 | 6.535 | +2.359 |
| 148 | 23.0c | - | N=24, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.141 | +2.400 | 0.5184 | 105309.6 | 6.535 | +2.359 |
| 149 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.128 | +2.400 | 0.5188 | 26208.4 | 6.671 | +2.479 |
| 150 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.128 | +2.400 | 0.5188 | 26208.4 | 6.671 | +2.479 |
| 151 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.089 | +2.400 | 0.5120 | 16481.3 | 6.727 | +2.382 |
| 152 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.089 | +2.400 | 0.5120 | 16481.3 | 6.727 | +2.382 |
| 153 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.063 | +2.300 | 0.5087 | 144684.5 | 6.315 | +2.301 |
| 154 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.063 | +2.300 | 0.5087 | 144684.5 | 6.315 | +2.301 |
| 155 | 23.0c | - | N=12, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.057 | +2.300 | 0.5085 | 157055.5 | 6.312 | +2.299 |
| 156 | 23.0c | - | N=12, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.057 | +2.300 | 0.5085 | 157055.5 | 6.312 | +2.299 |
| 157 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.5, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.056 | +2.300 | 0.5106 | 79017.6 | 6.484 | +2.253 |
| 158 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.5, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.056 | +2.300 | 0.5106 | 79017.6 | 6.484 | +2.253 |
| 159 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +1.056 | +2.300 | 0.5107 | 62130.5 | 6.588 | +2.254 |
| 160 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +1.056 | +2.300 | 0.5107 | 62130.5 | 6.588 | +2.254 |
| 161 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.0, horizon_bars=2, exit_rule=tb | ✗ | -inf | +0.971 | +2.200 | 0.5009 | 107364.0 | 6.314 | +2.241 |
| 162 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.0, horizon_bars=2, exit_rule=time | ✗ | -inf | +0.971 | +2.200 | 0.5009 | 107364.0 | 6.314 | +2.241 |
| 163 | 23.0b | - | N=50, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.451 | +1.300 | 0.4107 | 105277.1 | 5.537 | +2.234 |
| 164 | 23.0b | - | N=50, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.451 | +1.300 | 0.4107 | 105277.1 | 5.537 | +2.234 |
| 165 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.396 | +1.600 | 0.4431 | 40312.1 | 6.039 | +2.024 |
| 166 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.396 | +1.600 | 0.4431 | 40312.1 | 6.039 | +2.024 |
| 167 | 23.0c | - | N=48, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.385 | +1.500 | 0.4424 | 43378.7 | 6.007 | +2.020 |
| 168 | 23.0c | - | N=48, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.385 | +1.500 | 0.4424 | 43378.7 | 6.007 | +2.020 |
| 169 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.298 | +1.500 | 0.4353 | 11531.9 | 6.063 | +2.209 |
| 170 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.298 | +1.500 | 0.4353 | 11531.9 | 6.063 | +2.209 |
| 171 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.281 | +1.500 | 0.4307 | 24906.0 | 6.182 | +1.850 |
| 172 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.281 | +1.500 | 0.4307 | 24906.0 | 6.182 | +1.850 |
| 173 | 23.0b | - | N=20, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.191 | +1.100 | 0.3824 | 173212.1 | 5.362 | +1.994 |
| 174 | 23.0b | - | N=20, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.191 | +1.100 | 0.3824 | 173212.1 | 5.362 | +1.994 |
| 175 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.184 | +1.500 | 0.4232 | 8456.8 | 6.219 | +1.947 |
| 176 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.184 | +1.500 | 0.4232 | 8456.8 | 6.219 | +1.947 |
| 177 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.182 | +1.300 | 0.4123 | 66578.6 | 5.632 | +1.851 |
| 178 | 23.0c-rev1 | F2_cooldown | N=48, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.182 | +1.300 | 0.4123 | 66578.6 | 5.632 | +1.851 |
| 179 | 23.0c | - | N=48, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.175 | +1.300 | 0.4118 | 72082.3 | 5.616 | +1.850 |
| 180 | 23.0c | - | N=48, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.175 | +1.300 | 0.4118 | 72082.3 | 5.616 | +1.850 |
| 181 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.168 | +1.300 | 0.4135 | 58984.4 | 5.751 | +1.747 |
| 182 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.168 | +1.300 | 0.4135 | 58984.4 | 5.751 | +1.747 |
| 183 | 23.0c | - | N=24, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.157 | +1.300 | 0.4129 | 63307.3 | 5.739 | +1.747 |
| 184 | 23.0c | - | N=24, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.157 | +1.300 | 0.4129 | 63307.3 | 5.739 | +1.747 |
| 185 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.108 | +1.300 | 0.4069 | 35394.7 | 5.835 | +1.721 |
| 186 | 23.0c-rev1 | F1_neutral_reset | N=48, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.108 | +1.300 | 0.4069 | 35394.7 | 5.835 | +1.721 |
| 187 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.079 | +1.200 | 0.4000 | 22068.6 | 5.600 | +1.960 |
| 188 | 23.0c-rev1 | F3_reversal_confirmation | N=48, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.079 | +1.200 | 0.4000 | 22068.6 | 5.600 | +1.960 |
| 189 | 23.0b | - | N=10, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.071 | +1.000 | 0.3691 | 249507.3 | 5.257 | +1.908 |
| 190 | 23.0b | - | N=10, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.071 | +1.000 | 0.3691 | 249507.3 | 5.257 | +1.908 |
| 191 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.070 | +1.200 | 0.4033 | 43842.5 | 5.762 | +1.645 |
| 192 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.070 | +1.200 | 0.4033 | 43842.5 | 5.762 | +1.645 |
| 193 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.035 | +1.100 | 0.3903 | 95745.5 | 5.463 | +1.662 |
| 194 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.035 | +1.100 | 0.3903 | 95745.5 | 5.463 | +1.662 |
| 195 | 23.0c | - | N=12, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.035 | +1.100 | 0.3908 | 102128.9 | 5.461 | +1.662 |
| 196 | 23.0c | - | N=12, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.035 | +1.100 | 0.3908 | 102128.9 | 5.461 | +1.662 |
| 197 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.023 | +1.100 | 0.3908 | 97159.0 | 5.459 | +1.691 |
| 198 | 23.0c-rev1 | F2_cooldown | N=24, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.023 | +1.100 | 0.3908 | 97159.0 | 5.459 | +1.691 |
| 199 | 23.0c | - | N=24, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | +0.015 | +1.100 | 0.3901 | 105311.1 | 5.447 | +1.689 |
| 200 | 23.0c | - | N=24, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | +0.015 | +1.100 | 0.3901 | 105311.1 | 5.447 | +1.689 |
| 201 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | -0.026 | +1.000 | 0.3790 | 144687.0 | 5.267 | +1.649 |
| 202 | 23.0c-rev1 | F2_cooldown | N=12, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | -0.026 | +1.000 | 0.3790 | 144687.0 | 5.267 | +1.649 |
| 203 | 23.0c | - | N=12, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | -0.031 | +1.000 | 0.3788 | 157058.0 | 5.264 | +1.647 |
| 204 | 23.0c | - | N=12, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | -0.031 | +1.000 | 0.3788 | 157058.0 | 5.264 | +1.647 |
| 205 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | -0.034 | +1.100 | 0.3863 | 26208.4 | 5.495 | +1.788 |
| 206 | 23.0c-rev1 | F3_reversal_confirmation | N=24, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | -0.034 | +1.100 | 0.3863 | 26208.4 | 5.495 | +1.788 |
| 207 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | -0.041 | +1.000 | 0.3823 | 79018.6 | 5.438 | +1.607 |
| 208 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | -0.041 | +1.000 | 0.3823 | 79018.6 | 5.438 | +1.607 |
| 209 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | -0.054 | +1.000 | 0.3841 | 62131.0 | 5.518 | +1.593 |
| 210 | 23.0c-rev1 | F1_neutral_reset | N=24, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | -0.054 | +1.000 | 0.3841 | 62131.0 | 5.518 | +1.593 |
| 211 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | -0.081 | +1.100 | 0.3818 | 16481.3 | 5.539 | +1.683 |
| 212 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | -0.081 | +1.100 | 0.3818 | 16481.3 | 5.539 | +1.683 |
| 213 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.0, horizon_bars=1, exit_rule=tb | ✗ | -inf | -0.096 | +0.900 | 0.3718 | 107365.0 | 5.284 | +1.598 |
| 214 | 23.0c-rev1 | F1_neutral_reset | N=12, threshold=2.0, horizon_bars=1, exit_rule=time | ✗ | -inf | -0.096 | +0.900 | 0.3718 | 107365.0 | 5.284 | +1.598 |
| 215 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.5, horizon_bars=1, exit_rule=tb | ✗ | -inf | -0.190 | +1.400 | 0.4125 | 2150.5 | 6.867 | +1.553 |
| 216 | 23.0c-rev1 | F3_reversal_confirmation | N=12, threshold=2.5, horizon_bars=1, exit_rule=time | ✗ | -inf | -0.190 | +1.400 | 0.4125 | 2150.5 | 6.867 | +1.553 |

## Phase 24 forward routing

24.0b (trailing-stop variants), 24.0c (partial-exit variants), and 24.0d (regime-conditional exits — exit-parameter selection only, NOT entry filter) will import `frozen_entry_streams.json` and use the top-3 cells as their frozen entry streams. The score formula and K are sealed by this 24.0a PR's commit hash; downstream stages must NOT override or re-search them.
