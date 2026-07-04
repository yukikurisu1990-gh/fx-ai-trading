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

This module reads no real data itself. It provides the reviewed per-decision
primitives plus ``bulk_labels`` (the single sanctioned bulk route the run body
must use for BOTH training labels and trade scoring); running it over real
candles happens only at a separately-authorised execution.
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


# ---------------------------------------------------------------------------
# PR #411 R-4 — single-source label routing identity
# ---------------------------------------------------------------------------

# Fully-qualified identity of the ONLY sanctioned label/PnL primitives. The
# wiring layer records this in preflight metadata and routes all label
# generation AND all trade scoring exclusively through this module; any
# alternative/fallback label path is a contract violation.
LABEL_CONTRACT_ID: Final[str] = "scripts.ml_step4.labels.v1"


def label_contract_identity() -> dict[str, str]:
    """Identity of the sanctioned single-source label/PnL adapter (R-4)."""
    return {
        "label_contract_id": LABEL_CONTRACT_ID,
        "pnl_scorer": "scripts.ml_step4.labels.traded_direction_pnl_pips",
        "delegates_to": "scripts.traded_direction_pnl.traded_direction_pnl_price",
        "label_rule": "scripts.ml_step4.labels.barrier_label",
        "tie_handling": "sl_first_strict",
        "spread_convention": "b2_ask_entry_bid_exit_spread_once",
    }


# ---------------------------------------------------------------------------
# Bulk B-2 label generation (single-source route for the run body)
# ---------------------------------------------------------------------------
#
# The run body must generate ALL training labels and ALL trade scores through
# this module (PR #416 required-in-body item 2). ``bulk_labels`` is a pure-
# Python causal scan that reuses the reviewed per-decision primitives above
# (``first_hit_index``, ``barrier_label``, ``traded_direction_pnl_price`` via
# the committed F-2 helper) — no fork of barrier/PnL math exists elsewhere.


def atr14(bars: Sequence[dict], *, period: int = 14, min_periods: int = 14) -> list[float | None]:
    """Causal ATR from mid true ranges; None until ``min_periods`` TRs exist.

    ``bars[i]`` needs bid_h/bid_l/ask_h/ask_l/bid_c/ask_c. TR_i uses bar i's
    mid high/low and bar i-1's mid close (classic true range); ATR_i is the
    simple mean of the last ``period`` TRs ending at i (only past/current bars —
    causal).
    """
    mids_h = [(b["bid_h"] + b["ask_h"]) / 2.0 for b in bars]
    mids_l = [(b["bid_l"] + b["ask_l"]) / 2.0 for b in bars]
    mids_c = [(b["bid_c"] + b["ask_c"]) / 2.0 for b in bars]
    trs: list[float] = []
    out: list[float | None] = []
    for i in range(len(bars)):
        if i == 0:
            tr = mids_h[i] - mids_l[i]
        else:
            tr = max(
                mids_h[i] - mids_l[i],
                abs(mids_h[i] - mids_c[i - 1]),
                abs(mids_l[i] - mids_c[i - 1]),
            )
        trs.append(tr)
        if len(trs) < min_periods:
            out.append(None)
        else:
            window = trs[-period:]
            out.append(sum(window) / len(window))
    return out


def bulk_labels(
    bars: Sequence[dict],
    *,
    horizon: int,
    tp_mult: float,
    sl_mult: float,
    pip_size: float,
) -> list[dict]:
    """Per-bar B-2 3-class labels + per-direction traded PnL (pips, spread once).

    Returns one record per decision bar i: ``{"label": -1|0|1|None,
    "pnl_long_pips": float|None, "pnl_short_pips": float|None}``. Semantics
    mirror the committed B-2 contract: entry next-bar ask (long) / bid (short);
    window = bars i+1 .. i+horizon; SL-first same-bar tie; timeout scored at the
    horizon-end exit-side close (mark-to-market, never zeroed). Bars without a
    valid ATR or a full window get label None.
    """
    if horizon <= 0 or tp_mult <= 0 or sl_mult <= 0 or pip_size <= 0:
        raise LabelContractError("bulk_labels requires positive horizon/mults/pip_size")
    atrs = atr14(bars)
    n = len(bars)
    out: list[dict] = []
    for i in range(n):
        atr_i = atrs[i]
        # Window covers bars i+1 .. i+horizon, so the last labelable decision
        # bar is n-1-horizon (matching the committed labeller's range).
        if atr_i is None or atr_i <= 0 or i + horizon >= n:
            out.append(
                {
                    "label": None,
                    "pnl_long_pips": None,
                    "pnl_short_pips": None,
                    "exit_long_offset": None,
                    "exit_short_offset": None,
                }
            )
            continue
        entry_long = bars[i + 1]["ask_o"]
        entry_short = bars[i + 1]["bid_o"]
        tp = tp_mult * atr_i
        sl = sl_mult * atr_i
        window = bars[i + 1 : i + 1 + horizon]
        long_tp_idx = first_hit_index([b["bid_h"] >= entry_long + tp for b in window])
        long_sl_idx = first_hit_index([b["bid_l"] <= entry_long - sl for b in window])
        short_tp_idx = first_hit_index([b["ask_l"] <= entry_short - tp for b in window])
        short_sl_idx = first_hit_index([b["ask_h"] >= entry_short + sl for b in window])
        pnl_long = traded_direction_pnl_pips(
            direction=LONG,
            tp_idx=long_tp_idx,
            sl_idx=long_sl_idx,
            tp_dist_price=tp,
            sl_dist_price=sl,
            mtm_exit_pnl_price=bars[i + horizon]["bid_c"] - entry_long,
            pip_size=pip_size,
        )
        pnl_short = traded_direction_pnl_pips(
            direction=SHORT,
            tp_idx=short_tp_idx,
            sl_idx=short_sl_idx,
            tp_dist_price=tp,
            sl_dist_price=sl,
            mtm_exit_pnl_price=entry_short - bars[i + horizon]["ask_c"],
            pip_size=pip_size,
        )
        label = barrier_label(
            long_tp_idx=long_tp_idx,
            long_sl_idx=long_sl_idx,
            short_tp_idx=short_tp_idx,
            short_sl_idx=short_sl_idx,
        )
        out.append(
            {
                "label": label,
                "pnl_long_pips": pnl_long,
                "pnl_short_pips": pnl_short,
                # Exit timing stays single-sourced here (R-4): window offsets
                # (0-based within bars i+1..i+horizon) per traded direction.
                "exit_long_offset": exit_window_offset(long_tp_idx, long_sl_idx, horizon),
                "exit_short_offset": exit_window_offset(short_tp_idx, short_sl_idx, horizon),
            }
        )
    return out


def exit_window_offset(tp_idx: int, sl_idx: int, horizon: int) -> int:
    """Window offset (0-based, within bars i+1..i+horizon) where the trade exits.

    SL-first same-bar tie (consistent with :func:`traded_direction_pnl_pips`);
    timeout exits at the last window bar (``horizon - 1``). Keeping this here
    keeps ALL exit semantics single-sourced in the label adapter (R-4).
    """
    if horizon <= 0:
        raise LabelContractError("horizon must be positive")
    sl_first = sl_idx >= 0 and (tp_idx < 0 or sl_idx <= tp_idx)
    if sl_first:
        return sl_idx
    if tp_idx >= 0:
        return tp_idx
    return horizon - 1
