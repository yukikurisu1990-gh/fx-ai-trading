"""Event-driven single-position-per-pair simulator (deterministic).

Enforces the contract's concurrency rule: **max 1 open position per pair**. A
new signal on a pair is ignored while that pair already has an open position;
the pair becomes eligible again only once its position exits (barrier/timeout).
This closes the audit F-7 overlapping-trades defect for this experiment.

The simulator is pure and deterministic: it consumes resolved candidate signals
(each already carrying its entry marker, exit marker, direction, and post-cost
PnL as computed by the F-2 label adapter) and emits per-trade metadata suitable
for daily portfolio aggregation. It does not compute barriers or read data.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


class SimulatorError(ValueError):
    """Raised on malformed simulator input."""


@dataclass(frozen=True)
class TradeSignal:
    """A resolved candidate signal for one pair.

    ``entry`` / ``exit_`` are comparable, sortable markers (M1 bar index or ISO
    timestamp) with ``exit_ > entry``. ``pnl_pips`` is the post-cost PnL of the
    traded direction.
    """

    pair: str
    entry: Any
    exit_: Any
    direction: str
    pnl_pips: float


def _validate(sig: TradeSignal) -> None:
    if not sig.pair:
        raise SimulatorError("signal missing pair")
    try:
        if not (sig.exit_ > sig.entry):
            raise SimulatorError(f"signal exit must be after entry ({sig.pair})")
    except TypeError as exc:
        raise SimulatorError(f"entry/exit not comparable for {sig.pair}") from exc


def simulate(signals: Iterable[TradeSignal]) -> dict[str, Any]:
    """Apply the 1-open-position-per-pair rule; return accepted + ignored trades.

    Signals are processed in deterministic order: ``(entry, pair, direction)``.
    """
    sigs = list(signals)
    for s in sigs:
        _validate(s)
    ordered = sorted(sigs, key=lambda s: (s.entry, s.pair, s.direction))

    open_until: dict[str, Any] = {}
    accepted: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for s in ordered:
        busy = s.pair in open_until and s.entry < open_until[s.pair]
        if busy:
            ignored.append(
                {
                    "pair": s.pair,
                    "entry": s.entry,
                    "direction": s.direction,
                    "reason": "pair_position_open",
                }
            )
            continue
        accepted.append(
            {
                "pair": s.pair,
                "entry": s.entry,
                "exit": s.exit_,
                "direction": s.direction,
                "pnl_pips": float(s.pnl_pips),
            }
        )
        open_until[s.pair] = s.exit_

    return {
        "accepted_trades": accepted,
        "ignored_signals": ignored,
        "n_accepted": len(accepted),
        "n_ignored": len(ignored),
        "max_open_positions_per_pair": 1,
        "deterministic_order_key": "(entry, pair, direction)",
    }
