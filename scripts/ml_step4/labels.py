"""F-2 label / PnL contract adapter for the ML Step 4 executor.

Thin, reviewed wrappers over the committed F-2 helper
(:func:`scripts.traded_direction_pnl.traded_direction_pnl_price`) plus the
committed B-2 barrier-label rule (from ``compare_multipair_v9_orthogonal``).
The point of this module is a single interface the future executor uses so the
same contract generates training labels and scores evaluation trades
(label ↔ evaluation consistency), enforcing:

* traded-direction PnL (score the traded direction's own barrier path, never
  label identity);
* spread embedded exactly once (barrier tp/sl distances and the timeout
  mark-to-market already carry the ask-entry / bid-exit geometry; this adapter
  adds NO extra spread — only the flat per-cost-cell slippage is additive);
* SL-first same-bar tie handling (strict, conservative);
* timeout mark-to-market at the horizon-end exit-side close (never booked 0);
* no reuse of pre-F-2 optimistic historical results.

This module performs NO real-data label generation. It provides the reviewed
per-decision primitives; bulk generation over real candles happens only at a
separately-authorised execution.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from scripts.traded_direction_pnl import traded_direction_pnl_price

LONG: Final[str] = "long"
SHORT: Final[str] = "short"

# 3-class label encoding (matches the committed B-2 label contract).
LABEL_SHORT: Final[int] = -1
LABEL_TIMEOUT: Final[int] = 0
LABEL_LONG: Final[int] = 1


class LabelContractError(ValueError):
    """Raised when a scoring/label request violates the F-2 contract."""


def first_hit_index(hits: Sequence[bool]) -> int:
    """First index where ``hits`` is True, or -1 (matches ``_first_hit_idx``)."""
    for i, hit in enumerate(hits):
        if hit:
            return i
    return -1


def traded_direction_pnl_pips(
    *,
    direction: str,
    tp_idx: int,
    sl_idx: int,
    tp_dist_price: float,
    sl_dist_price: float,
    mtm_exit_pnl_price: float,
    pip_size: float,
) -> float:
    """Score one traded direction's own barrier path, in pips (spread once).

    ``tp_dist_price`` / ``sl_dist_price`` are positive barrier distances in
    price units (already carrying the B-2 ask-entry / bid-exit geometry).
    ``mtm_exit_pnl_price`` is the signed horizon-end mark-to-market for this
    direction, used only on timeout. No additional spread is applied here.
    """
    if direction not in (LONG, SHORT):
        raise LabelContractError(f"unknown direction {direction!r}")
    if pip_size <= 0:
        raise LabelContractError("pip_size must be positive")
    if tp_dist_price <= 0 or sl_dist_price <= 0:
        raise LabelContractError("tp/sl distances must be positive")
    pnl_price = traded_direction_pnl_price(
        tp_idx=tp_idx,
        sl_idx=sl_idx,
        tp_dist=tp_dist_price,
        sl_dist=sl_dist_price,
        mtm_exit_pnl=mtm_exit_pnl_price,
    )
    return pnl_price / pip_size


def barrier_label(
    *,
    long_tp_idx: int,
    long_sl_idx: int,
    short_tp_idx: int,
    short_sl_idx: int,
) -> int:
    """3-class label in {-1, 0, 1} using the committed B-2 clears rule.

    A direction "clears" if its TP fires strictly before its own SL. Ties and
    the both-clear case resolve exactly as the committed labeller.
    """
    long_clears = long_tp_idx >= 0 and (long_sl_idx < 0 or long_tp_idx < long_sl_idx)
    short_clears = short_tp_idx >= 0 and (short_sl_idx < 0 or short_tp_idx < short_sl_idx)
    if long_clears and not short_clears:
        return LABEL_LONG
    if short_clears and not long_clears:
        return LABEL_SHORT
    if long_clears and short_clears:
        return LABEL_LONG if long_tp_idx <= short_tp_idx else LABEL_SHORT
    return LABEL_TIMEOUT


def apply_cost_cell(pnl_pips: float, slippage_pips: float) -> float:
    """Apply the flat per-trade slippage cell exactly once (additive to spread).

    The barrier geometry already embeds spread once; the evaluation cost cell is
    a separate flat deduction applied a single time per trade.
    """
    if slippage_pips < 0:
        raise LabelContractError("slippage_pips must be >= 0")
    return pnl_pips - slippage_pips
