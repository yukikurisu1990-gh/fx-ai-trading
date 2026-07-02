"""Traded-direction barrier/horizon PnL scoring — F-2 correction.

Shared by the patched compare_multipair_v* evaluation scripts. See
docs/design/project_wide_logic_audit_fable5_findings.md §3 F-2: the
legacy eval layer mapped the tri-directional label identity to PnL
(label==+1 → +tp, label==-1 → -sl, label==0 → 0.0), which booked real
traded-direction SL hits hidden inside label==0 as 0.0 pips and booked
timeout exits at 0.0 with no mark-to-market.

This helper scores the traded direction's OWN barrier path instead:

- SL hit first  → -sl_dist (same-bar TP+SL tie resolves SL-first,
  conservative — matching both the existing label contract's strict
  ``tp_idx < sl_idx`` "clears" test and the Stage22+ convention).
- TP hit first  → +tp_dist.
- Neither hit within the horizon → horizon-end mark-to-market PnL
  supplied by the caller.

Spread/cost convention (unchanged from the B-2 label contract): entry
at next-bar ask (long) / bid (short); barriers and horizon-end exits
valued on the opposite side (bid for long, ask for short). The spread
is therefore embedded exactly once in tp/sl distances and in the
mark-to-market exit — this helper adds NO additional spread, and the
eval layer's flat ``--slippage-pip`` deduction is unchanged, so barrier
rows are never double-charged.

Units: price units in, price units out. Callers convert to pips.

Scope statuses: F2_PNL_LAYER_CORRECTED_BY_INVARIANT_TESTS;
F2_REAL_DATA_RERUN_NOT_PERFORMED;
HISTORICAL_PHASE9_NUMERICS_NOT_REHABILITATED (committed historical
reports are records of the old scorer; they are not recomputed here).
"""

from __future__ import annotations


def traded_direction_pnl_price(
    *,
    tp_idx: int,
    sl_idx: int,
    tp_dist: float,
    sl_dist: float,
    mtm_exit_pnl: float,
) -> float:
    """Score one traded direction's outcome in price units.

    Args:
        tp_idx: first window index where this direction's TP triggered,
            -1 if never (window = bars entry..entry+horizon-1).
        sl_idx: first window index where this direction's SL triggered,
            -1 if never.
        tp_dist: TP barrier distance in price units (> 0).
        sl_dist: SL barrier distance in price units (> 0).
        mtm_exit_pnl: signed horizon-end mark-to-market PnL in price
            units for this direction (long: exit_bid_close - entry_ask;
            short: entry_bid - exit_ask_close). Used only on timeout.

    Same-bar tie (tp_idx == sl_idx) resolves SL-first (conservative).
    """
    sl_first = sl_idx >= 0 and (tp_idx < 0 or sl_idx <= tp_idx)
    if sl_first:
        return -sl_dist
    if tp_idx >= 0:
        return tp_dist
    return mtm_exit_pnl
