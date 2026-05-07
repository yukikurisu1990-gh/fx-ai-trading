# Stage 25.0a-β — Causality Audit

This document maps each binding causality invariant from 25.0a-α §9
to the unit test that enforces it. Unit tests are the authoritative
enforcement; this document is a brief audit map.

## Invariant 1 — Labels at `t` use only future bars `[t+1, t+H_M1_BARS]`

Labels are computed by slicing M1 OHLC arrays at `[entry_m1_idx,
entry_m1_idx + H_M1_BARS)` where `entry_m1_idx = position(signal_ts +
1 minute)`. No bar at index `<= signal_ts` is used in label
computation; no bar at index `> entry_m1_idx + H_M1_BARS - 1` is used.

Tests:
- `test_no_lookahead_uses_only_t_plus_1_through_t_plus_h`
- `test_no_use_of_bars_at_or_before_signal_time_for_label`

## Invariant 2 — `atr_at_signal_pip` at `t` uses only past bars (shift(1))

`stage23_0a.atr_causal` computes ATR over bars `[t-N+1, t]` (inclusive
of bar t). 25.0a-α §8 mandates strict `shift(1)` so signal bar t's own
data is NOT used in its own ATR. We apply an additional `shift(1)` on
top of `atr_causal` output via `_causal_m5_atr_pip_strict`, producing
ATR that strictly uses bars `[t-N..t-1]`.

Tests:
- `test_design_constants_match_25_0a_alpha`
- (manual: `_causal_m5_atr_pip_strict` shifts atr_causal output by 1 bar)

## Invariant 3 — `spread_at_signal_pip` uses bar `t`'s OHLC only

The spread is computed at the entry M1 bar (`t + 1 minute`) using its
ask_o − bid_o. This is the price at which the entry would actually
fill, so it is causally observable.

Tests:
- `test_spread_cost_integrated_long_uses_entry_ask`
- `test_spread_cost_integrated_short_uses_entry_bid`

## Invariant 4 — `entry_ask`, `entry_bid` at `t` are bar `t` open values

We use `ask_o[entry_m1_idx]` and `bid_o[entry_m1_idx]` (the open of
the entry M1 bar) as the cost-inclusive entry prices. This matches
the convention in stage23_0a.

Tests:
- `test_spread_cost_integrated_long_uses_entry_ask`
- `test_spread_cost_integrated_short_uses_entry_bid`

## Invariant 5 — Same-bar SL-first

Within the H-bar window, if a single M1 bar contains both fav-touch
and adv-touch conditions, the label is NEGATIVE (per PR #276 §3.3).
Implemented in `_resolve_label_from_first_hits`.

Tests:
- `test_same_bar_both_hit_long_labels_negative_hard`
- `test_same_bar_both_hit_short_labels_negative_hard`

## Invariant 6 — Ineligible rows are dropped, not labeled

Rows where `K_FAV * ATR < M_MARGIN * spread` are skipped via `continue`
and counted in `dropped_by_margin`. Rows with negative or non-finite
spread are skipped via `continue` and counted in
`dropped_invalid_spread`. Neither category produces a label row.

Tests:
- `test_low_volatility_signal_dropped_when_fav_threshold_below_margin`

## Diagnostic columns leakage prohibition

The columns `max_fav_excursion_pip`, `max_adv_excursion_pip`,
`time_to_fav_bar`, `time_to_adv_bar`, `same_bar_both_hit` are
label-side diagnostic outputs. They are computed from the same future
bars as the label and **MUST NOT be used as model input features by
any downstream Phase 25 PR (25.0b+)**. Per kickoff §10 / 25.0a-α §10,
each per-class PR must include a unit test asserting non-use.
