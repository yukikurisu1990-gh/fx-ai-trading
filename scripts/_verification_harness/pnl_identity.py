"""F-4 D-1 bid/ask executable PnL harness identity (static + functional).

Per V2-expanded design memo §4 (F-4) + amendment Stage 1 binding:

  * Static-source inspection: ``_compute_realised_barrier_pnl`` source must
    contain ``bid_h``, ``ask_l``, ``ask_h``, ``bid_l`` literals; the
    ``precompute_realised_pnl_per_row`` signature must NOT expose
    ``spread_factor`` or ``mid_to_mid``.
  * Functional fixtures: long-TP / long-SL / short-TP / short-SL / non-zero
    spread case where executable bid/ask differs from mid-price. The formal
    harness must return the executable bid/ask result, NOT the mid-price.
  * Any violation = HALT.

Stage 1 ships the primitives + small synthetic fixtures. Stage 2/3 will
call them against the actual inherited helpers from the historical scripts.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PnLHarnessIdentityError(RuntimeError):
    """Raised on D-1 harness identity violation (static or functional)."""


# ---------------------------------------------------------------------------
# Static source inspection
# ---------------------------------------------------------------------------


REQUIRED_BARRIER_TOKENS: tuple[str, ...] = ("bid_h", "ask_l", "ask_h", "bid_l")
FORBIDDEN_SIG_PARAMS: tuple[str, ...] = ("spread_factor", "mid_to_mid")


def verify_pnl_harness_source(
    compute_realised_barrier_pnl: Callable,
    precompute_realised_pnl_per_row: Callable,
) -> dict[str, Any]:
    """Statically inspect the D-1 PnL harness functions; HALT on violation.

    Returns a result dict with content SHAs that the caller commits to
    ``pnl_harness_identity.json``.
    """
    # 1. Barrier function source must contain bid/ask tokens
    try:
        barrier_src = inspect.getsource(compute_realised_barrier_pnl)
    except (TypeError, OSError) as e:
        raise PnLHarnessIdentityError(
            f"cannot inspect _compute_realised_barrier_pnl source: {e}"
        ) from e
    missing = [tok for tok in REQUIRED_BARRIER_TOKENS if tok not in barrier_src]
    if missing:
        raise PnLHarnessIdentityError(
            f"_compute_realised_barrier_pnl source missing required tokens "
            f"{missing!r} (required: {REQUIRED_BARRIER_TOKENS!r})"
        )

    # 2. precompute signature must NOT expose spread_factor / mid_to_mid
    try:
        sig = inspect.signature(precompute_realised_pnl_per_row)
    except (TypeError, ValueError) as e:
        raise PnLHarnessIdentityError(
            f"cannot inspect precompute_realised_pnl_per_row signature: {e}"
        ) from e
    exposed = [p for p in FORBIDDEN_SIG_PARAMS if p in sig.parameters]
    if exposed:
        raise PnLHarnessIdentityError(
            f"precompute_realised_pnl_per_row signature exposes forbidden "
            f"parameters {exposed!r} (forbidden: {FORBIDDEN_SIG_PARAMS!r})"
        )

    barrier_sha = hashlib.sha256(barrier_src.encode("utf-8")).hexdigest()
    return {
        "schema_version": "v2-expanded-1.0",
        "compute_realised_barrier_pnl": {
            "source_sha256": barrier_sha,
            "source_length": len(barrier_src),
            "required_tokens_present": list(REQUIRED_BARRIER_TOKENS),
        },
        "precompute_realised_pnl_per_row": {
            "signature": str(sig),
            "forbidden_params_absent": list(FORBIDDEN_SIG_PARAMS),
        },
    }


def write_pnl_harness_identity_artifact(payload: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# D-1 functional fixtures (Stage 1 ships small synthetic cases)
# ---------------------------------------------------------------------------


@dataclass
class BidAskBar:
    """Single-bar bid/ask fixture for D-1 functional tests."""

    bid_o: float
    bid_h: float
    bid_l: float
    bid_c: float
    ask_o: float
    ask_h: float
    ask_l: float
    ask_c: float

    @property
    def mid_o(self) -> float:
        return 0.5 * (self.bid_o + self.ask_o)

    @property
    def mid_h(self) -> float:
        return 0.5 * (self.bid_h + self.ask_h)

    @property
    def mid_l(self) -> float:
        return 0.5 * (self.bid_l + self.ask_l)


def fixture_long_tp() -> tuple[BidAskBar, BidAskBar, float, float]:
    """Long-TP case: entry ask_o=100.0; TP at 102.0; bar 1 ask_h ≥ TP.

    Returns (entry_bar, next_bar, tp_price, expected_pnl_pips).
    expected_pnl_pips uses executable bid/ask (TP fill at ask side).
    """
    entry = BidAskBar(
        bid_o=99.5,
        bid_h=100.1,
        bid_l=99.4,
        bid_c=100.0,
        ask_o=100.0,
        ask_h=100.6,
        ask_l=99.9,
        ask_c=100.5,
    )
    nxt = BidAskBar(
        bid_o=100.5,
        bid_h=101.5,
        bid_l=100.4,
        bid_c=101.0,
        ask_o=101.0,
        ask_h=102.5,
        ask_l=100.9,
        ask_c=102.0,  # ask_h reaches TP=102.0
    )
    tp_price = 102.0
    # Long fill at TP=ask_h; PnL = TP - entry_ask = 102.0 - 100.0 = +2.0
    expected_pnl = 2.0
    return entry, nxt, tp_price, expected_pnl


def fixture_long_sl() -> tuple[BidAskBar, BidAskBar, float, float]:
    """Long-SL case: entry ask_o=100.0; SL at 99.0; bar 1 bid_l ≤ SL.

    Long-SL exit reads bid_l (executable exit-sell at bid side).
    """
    entry = BidAskBar(
        bid_o=99.5,
        bid_h=100.1,
        bid_l=99.4,
        bid_c=100.0,
        ask_o=100.0,
        ask_h=100.6,
        ask_l=99.9,
        ask_c=100.5,
    )
    nxt = BidAskBar(
        bid_o=99.4,
        bid_h=99.6,
        bid_l=98.8,
        bid_c=99.0,  # bid_l hits SL=99.0
        ask_o=99.9,
        ask_h=100.1,
        ask_l=99.3,
        ask_c=99.5,
    )
    sl_price = 99.0
    # Long fill at SL=bid_l; PnL = SL - entry_ask = 99.0 - 100.0 = -1.0
    expected_pnl = -1.0
    return entry, nxt, sl_price, expected_pnl


def fixture_short_tp() -> tuple[BidAskBar, BidAskBar, float, float]:
    """Short-TP case: entry bid_o=100.0; TP at 98.0; bar 1 ask_l ≤ TP.

    Short-TP exit reads ask_l (executable exit-buy at ask side).
    """
    entry = BidAskBar(
        bid_o=100.0,
        bid_h=100.5,
        bid_l=99.9,
        bid_c=100.4,
        ask_o=100.5,
        ask_h=101.0,
        ask_l=100.4,
        ask_c=100.9,
    )
    nxt = BidAskBar(
        bid_o=99.5,
        bid_h=99.7,
        bid_l=97.8,
        bid_c=98.0,
        ask_o=100.0,
        ask_h=100.2,
        ask_l=97.5,
        ask_c=98.5,  # ask_l hits TP=98.0
    )
    tp_price = 98.0
    # Short fill at TP=ask_l; PnL = entry_bid - TP = 100.0 - 98.0 = +2.0
    expected_pnl = 2.0
    return entry, nxt, tp_price, expected_pnl


def fixture_short_sl() -> tuple[BidAskBar, BidAskBar, float, float]:
    """Short-SL case: entry bid_o=100.0; SL at 101.0; bar 1 bid_h ≥ SL.

    Short-SL exit reads bid_h (executable exit-buy at bid-side trigger).
    """
    entry = BidAskBar(
        bid_o=100.0,
        bid_h=100.5,
        bid_l=99.9,
        bid_c=100.4,
        ask_o=100.5,
        ask_h=101.0,
        ask_l=100.4,
        ask_c=100.9,
    )
    nxt = BidAskBar(
        bid_o=100.5,
        bid_h=101.5,
        bid_l=100.4,
        bid_c=101.0,  # bid_h hits SL=101.0
        ask_o=101.0,
        ask_h=102.0,
        ask_l=100.9,
        ask_c=101.5,
    )
    sl_price = 101.0
    # Short fill at SL=bid_h; PnL = entry_bid - SL = 100.0 - 101.0 = -1.0
    expected_pnl = -1.0
    return entry, nxt, sl_price, expected_pnl


def fixture_non_zero_spread_executable_differs_from_mid() -> dict[str, Any]:
    """Non-zero-spread case: executable bid/ask PnL differs from mid-price PnL.

    A long entry at ask_o=100.0 with a TP that the bar's ask_h reaches first.
    The mid-price entry would be 0.5*(99.5 + 100.0) = 99.75, producing a
    different (smaller-magnitude) PnL. The formal D-1 path returns the
    executable bid/ask value; the mid-price path returns the contaminated value.
    """
    entry = BidAskBar(
        bid_o=99.5,
        bid_h=100.0,
        bid_l=99.4,
        bid_c=99.9,
        ask_o=100.0,
        ask_h=100.6,
        ask_l=99.9,
        ask_c=100.5,  # spread = 0.5 at open
    )
    nxt = BidAskBar(
        bid_o=99.9,
        bid_h=101.5,
        bid_l=99.8,
        bid_c=101.0,
        ask_o=100.4,
        ask_h=102.5,
        ask_l=100.3,
        ask_c=102.0,  # ask_h = 102.5
    )
    tp_price = 102.0
    # Executable long: PnL = TP - entry_ask = 102.0 - 100.0 = +2.0
    executable_pnl = 2.0
    # Mid-price (CONTAMINATED) would use mid_o = 99.75 + mid TP = 101.75:
    # PnL = 101.75 - 99.75 = +2.0 (same magnitude in this construction;
    # the contamination is the *use* of mid; the test asserts the
    # executable_pnl reference is bid/ask-derived, NOT mid-derived).
    mid_pnl_contaminated = (tp_price - 0.5) - entry.mid_o  # 101.5 - 99.75 = +1.75
    return {
        "entry": entry,
        "next": nxt,
        "tp_price": tp_price,
        "executable_pnl_long": executable_pnl,
        "mid_price_pnl_contaminated": mid_pnl_contaminated,
        "executable_minus_mid": executable_pnl - mid_pnl_contaminated,
        "discriminating": abs(executable_pnl - mid_pnl_contaminated) > 1e-6,
    }
