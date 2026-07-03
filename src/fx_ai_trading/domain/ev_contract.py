"""Canonical EV unit/cost contract — F8-F.

Status: F8_POST_COST_EV_CONTRACT_HARDENED
(see docs/design/project_wide_logic_audit_fable5_findings.md §4 F-8).

Contract
--------
The canonical expected-value unit for cross-strategy comparison is
**pips, post-cost** (``EV_UNIT_PIPS_POST_COST``).  Every strategy that
emits ``ev_before_cost`` / ``ev_after_cost`` MUST declare its
``ev_unit`` on the ``StrategySignal`` DTO; the value rides in the
``strategy_signals.meta`` JSON (no schema change) and is read back by
the Meta selector.

Meta (``run_meta_cycle``) only ranks candidates whose ``ev_unit``
equals ``EV_UNIT_PIPS_POST_COST``.  Candidates carrying any other unit
— including legacy rows with no ``ev_unit`` key at all (loaded as
``EV_UNIT_UNKNOWN``) — are rejected **fail-closed** with
``MetaFilterReason.EV_UNIT_INCOMPARABLE`` before the F-16 sort, so the
selector never compares pips against raw price units.

Why LGBMStrategy is post-cost with ``cost_pips=0.0``
----------------------------------------------------
The B-2 training labels embed the bid/ask spread in the triple-barrier
geometry itself (barriers are placed on bid/ask, not mid), so the
model's EV is post-embedded-cost *by construction* — no additional
subtraction may happen here or the cost would be double-counted.
Additional *live* spread gating happens at entry time via the F-1
entry gate, not in the EV figure.

Strategies that cannot produce this unit
----------------------------------------
A strategy without instrument/pip context (or whose EV formula has
never been expressed in pips) must NOT fake the canonical unit.  It
declares a non-comparable marker (``EV_UNIT_PRICE_RAW``) instead and
is rejected by Meta as above.
"""

from __future__ import annotations

EV_UNIT_PIPS_POST_COST = "pips_post_cost"
"""Canonical comparable EV unit: pips, with cost already subtracted."""

EV_UNIT_PRICE_RAW = "price_raw"
"""Non-comparable marker: EV in raw quote-price units, cost not modelled."""

EV_UNIT_UNKNOWN = "unknown"
"""Non-comparable marker: unit not declared (legacy rows / default)."""


def ev_after_cost_pips(ev_before_cost_pips: float, cost_pips: float) -> float:
    """Derive post-cost EV in pips, subtracting *cost_pips* exactly once.

    This helper is the single subtraction point of the F8-F contract:
    strategies MUST route their ``ev_after_cost`` derivation through it
    so cost can never be subtracted twice (or silently not at all).

    Args:
        ev_before_cost_pips: Pre-cost expected value, in pips.
        cost_pips: Round-trip cost in pips.  Pass ``0.0`` (with a
            comment) when cost is already embedded upstream — e.g.
            LGBM B-2 labels — or when no cost feed is available to the
            strategy and cost gating is delegated to the entry gate.

    Raises:
        ValueError: if *cost_pips* is negative (a negative cost would
            silently inflate EV).
    """
    if cost_pips < 0.0:
        raise ValueError(f"cost_pips must be >= 0.0 (got {cost_pips})")
    return ev_before_cost_pips - cost_pips


def is_comparable(ev_unit: str) -> bool:
    """True iff *ev_unit* is the canonical unit Meta may rank on."""
    return ev_unit == EV_UNIT_PIPS_POST_COST


def pip_size(instrument: str) -> float:
    """Price value of one pip for *instrument* (``BASE_QUOTE`` form).

    JPY-quoted pairs price at 0.01 per pip; other FX pairs at 0.0001.
    Matches the convention in ``adapters/broker/paper._default_pip_size``
    and the ``lgbm_strategy._PIP_SIZE`` table.
    """
    return 0.01 if instrument.endswith("_JPY") else 0.0001


__all__ = [
    "EV_UNIT_PIPS_POST_COST",
    "EV_UNIT_PRICE_RAW",
    "EV_UNIT_UNKNOWN",
    "ev_after_cost_pips",
    "is_comparable",
    "pip_size",
]
