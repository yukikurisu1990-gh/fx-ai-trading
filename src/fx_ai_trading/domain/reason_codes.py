"""Central registry for reason_code values (Cycle 6.8 / I-04).

Background
----------
Phase 6 producers historically emit reason_code literals in three
namespaces that grew incrementally:

* **bare snake_case** (close_events): ``sl``, ``tp``,
  ``emergency_stop``, ``max_holding_time``.
* **dotted** (risk-origin no_trade_events / risk_events / risk-blocked
  outcomes): ``risk.concurrent_limit``, ``risk.duplicate_instrument``,
  ``risk.size_under_min``, etc.
* **UPPERCASE** (meta-origin no_trade_events): ``EV_BELOW_THRESHOLD``,
  ``CALENDAR_STALE``, ``NO_CANDIDATES``, etc.

I-04 unifies the *source of truth* for these values without rewriting
DB rows or renaming any literal.  The historical strings are
grandfathered as ``LEGACY_BARE``; new reason codes must use the
``DOTTED`` namespace.

Policy
------
1. **``LEGACY_BARE`` is frozen.**  No new entries may be added.  The
   set captures the bare/UPPERCASE literals that already exist in
   ``no_trade_events``, ``close_events``, and the broker-level
   ``ExecutionGateRunResult.reject_reason`` DTO.  Renaming any of
   these would invalidate historical rows.
2. **New reason codes MUST be dotted.**  Add them to the appropriate
   ``RiskReason`` (or future ``<namespace>Reason``) class and ensure
   the value contains ``.``.  ``test_reason_codes_registry.py``
   enforces this at lint time.
3. **Producers MUST import constants from this module.**  Inlining a
   string literal that matches a registered code is a lint failure
   (``test_no_literal_reason_code_in_producers``).  Inlining a *new*
   string literal at a registered sink (``reason_code=``,
   ``primary_reason_code=``, ``reject_reason=``,
   ``constraint_violated=``) without registering it here is also a
   lint failure (``test_producer_kwarg_literals_are_registered``).

This module performs no DB I/O and has no runtime side effects.  It
is safe to import from any layer.
"""

from __future__ import annotations


class CloseReason:
    """Bare snake_case reason codes for ``close_events.primary_reason_code``.

    Frozen — these strings are already persisted in production rows.
    """

    SL = "sl"
    TP = "tp"
    EMERGENCY_STOP = "emergency_stop"
    MAX_HOLDING_TIME = "max_holding_time"


class RiskReason:
    """Dotted reason codes produced by the Risk gate (M10 / Cycle 6.6).

    These flow into ``RiskAcceptResult.reject_reason`` /
    ``AllowTradeResult.reject_reason`` DTOs and are persisted to
    ``no_trade_events`` (split into category + bare via
    ``execution_gate_runner._handle_risk_blocked``) and
    ``risk_events``.

    New risk reason codes MUST be added here with a dotted form
    (``risk.<snake_case>``).
    """

    CONCURRENT_LIMIT = "risk.concurrent_limit"
    SINGLE_CURRENCY_EXPOSURE = "risk.single_currency_exposure"
    NET_DIRECTIONAL_EXPOSURE = "risk.net_directional_exposure"
    TOTAL_RISK = "risk.total_risk"
    DUPLICATE_INSTRUMENT = "risk.duplicate_instrument"
    MAX_OPEN_POSITIONS = "risk.max_open_positions"
    RECENT_EXECUTION_FAILURE_COOLOFF = "risk.recent_execution_failure_cooloff"
    INVALID_SL = "risk.invalid_sl"
    INVALID_RISK_PCT = "risk.invalid_risk_pct"
    SIZE_UNDER_MIN = "risk.size_under_min"
    UNKNOWN = "risk.unknown"


class MetaReason:
    """UPPERCASE reason codes produced by the Meta layer (M9).

    Frozen — already persisted in ``no_trade_events`` rows.
    Sources: ``MetaDeciderService`` (filter / select stages) and
    ``run_meta_cycle`` (filter pipeline + whole-cycle verdict).
    """

    EV_BELOW_THRESHOLD = "EV_BELOW_THRESHOLD"
    CONFIDENCE_BELOW_THRESHOLD = "CONFIDENCE_BELOW_THRESHOLD"
    NO_CANDIDATES = "NO_CANDIDATES"
    NO_SCORED_CANDIDATES = "NO_SCORED_CANDIDATES"
    CALENDAR_STALE = "CALENDAR_STALE"
    SIGNAL_NO_TRADE = "SIGNAL_NO_TRADE"
    NEAR_EVENT = "NEAR_EVENT"
    PRICE_ANOMALY = "PRICE_ANOMALY"


class TimeoutReason:
    """Reason markers for the TTL-expiry path in ``run_execution_gate``.

    ``TTL_EXPIRED`` is persisted to ``no_trade_events.reason_code``.
    ``SIGNAL_EXPIRED`` is the broker-level marker carried on
    ``ExecutionGateRunResult.reject_reason`` (DTO field returned to
    the caller; not directly persisted).  Both are grandfathered.
    """

    TTL_EXPIRED = "ttl_expired"
    SIGNAL_EXPIRED = "SignalExpired"


class GateReason:
    """CamelCase reason markers emitted by ``ExecutionGateService.check``.

    These are the ``GateResult.reason_code`` values returned to the
    caller when a TradingIntent is rejected or deferred.  They are not
    written directly to a ``reason_code`` column today, but the
    ``SignalExpired`` value also surfaces on
    ``ExecutionGateRunResult.reject_reason``.  Frozen — already part
    of the public protocol surface.
    """

    SIGNAL_EXPIRED = "SignalExpired"
    DEFER_EXHAUSTED = "DeferExhausted"
    SPREAD_TOO_WIDE = "SpreadTooWide"
    BROKER_UNREACHABLE = "BrokerUnreachable"


# ---------------------------------------------------------------------------
# Aggregate sets — used by the lint test in ``test_reason_codes_registry``.
# ---------------------------------------------------------------------------

LEGACY_BARE: frozenset[str] = frozenset(
    {
        # close_events
        CloseReason.SL,
        CloseReason.TP,
        CloseReason.EMERGENCY_STOP,
        CloseReason.MAX_HOLDING_TIME,
        # meta no_trade_events
        MetaReason.EV_BELOW_THRESHOLD,
        MetaReason.CONFIDENCE_BELOW_THRESHOLD,
        MetaReason.NO_CANDIDATES,
        MetaReason.NO_SCORED_CANDIDATES,
        MetaReason.CALENDAR_STALE,
        MetaReason.SIGNAL_NO_TRADE,
        MetaReason.NEAR_EVENT,
        MetaReason.PRICE_ANOMALY,
        # timeout / broker outcome
        TimeoutReason.TTL_EXPIRED,
        TimeoutReason.SIGNAL_EXPIRED,
        # ExecutionGate decision markers
        GateReason.SIGNAL_EXPIRED,
        GateReason.DEFER_EXHAUSTED,
        GateReason.SPREAD_TOO_WIDE,
        GateReason.BROKER_UNREACHABLE,
    }
)
"""Frozen — historical bare/UPPERCASE codes already in DB.  Never add."""

DOTTED: frozenset[str] = frozenset(
    {
        RiskReason.CONCURRENT_LIMIT,
        RiskReason.SINGLE_CURRENCY_EXPOSURE,
        RiskReason.NET_DIRECTIONAL_EXPOSURE,
        RiskReason.TOTAL_RISK,
        RiskReason.DUPLICATE_INSTRUMENT,
        RiskReason.MAX_OPEN_POSITIONS,
        RiskReason.RECENT_EXECUTION_FAILURE_COOLOFF,
        RiskReason.INVALID_SL,
        RiskReason.INVALID_RISK_PCT,
        RiskReason.SIZE_UNDER_MIN,
        RiskReason.UNKNOWN,
    }
)
"""Dotted reason codes.  New entries MUST be added here, not LEGACY_BARE."""

ALL_REGISTERED: frozenset[str] = LEGACY_BARE | DOTTED
"""Union of every registered reason_code.  Producers must use these constants."""


__all__ = [
    "ALL_REGISTERED",
    "DOTTED",
    "LEGACY_BARE",
    "CloseReason",
    "GateReason",
    "MetaReason",
    "RiskReason",
    "TimeoutReason",
]
