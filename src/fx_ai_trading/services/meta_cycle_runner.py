"""Meta cycle runner — Phase 6 Cycle 6.4.

Reads every strategy_signals row emitted for a given cycle by
Cycle 6.3's run_strategy_cycle and produces one MetaDecision plus,
when possible, one trading_signals row (the Execution-ready intent).

Design constraints (Cycle 6.4 brief, amended by F8-G):

  1. F8-G: the Cycle 6.4 "≥1 trading_signal per cycle" guarantee is now
     OPT-IN (``force_fallback=True``, for smoke/tests only).  The
     production-like default is fail-closed: if the normal Filter →
     Sort pipeline rejects every candidate, Meta adopts NOTHING and
     records the rejections as no_trade_events.  Only when
     ``force_fallback`` is explicitly enabled does Meta fall back to
     the top-EV candidate and adopt it despite the filters.
     (F8_FORCE_FALLBACK_PRODUCTION_GUARDED — see
     docs/design/project_wide_logic_audit_fable5_findings.md §4 F-4.)

  1b. F8-F: candidates are only rankable when their ``ev_unit`` (from
     strategy_signals.meta) equals the canonical unit
     ``pips_post_cost`` (domain/ev_contract.py).  Any other unit —
     including legacy rows without the key — is rejected fail-closed
     with ``meta.ev_unit_incomparable`` so the F-16 sort never
     compares pips against raw price units.

  2. Sort order is F-16:
       primary   : ev_after_cost   DESC
       secondary : confidence      DESC
       tertiary  : spread          ASC   (not tracked in strategy_signals
                                          today; defaulted to 0.0 so the
                                          primary/secondary keys decide)
       stable    : strategy_id     ASC   (deterministic tie-break)

  3. Append-only.  Three INSERTs per cycle (meta_decisions + maybe
     trading_signals + zero or more no_trade_events) and N outbox
     INSERTs.  No UPDATEs, no DELETEs.

  4. Every persisted row is mirrored into ``secondary_sync_outbox`` via
     ``enqueue_secondary_sync`` under the F-12 sanitize-before-enqueue
     contract.

Runner is a pure function (``run_meta_cycle``).  No loops, no retries,
no sleeps — one call, one cycle.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from fx_ai_trading.common.clock import Clock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.domain.ev_contract import EV_UNIT_UNKNOWN, is_comparable
from fx_ai_trading.domain.reason_codes import MetaFilterReason, MetaReason
from fx_ai_trading.sync.enqueue import enqueue_secondary_sync

SOURCE_COMPONENT = "meta_cycle_runner"

# --- Config / Result --------------------------------------------------------


@dataclass(frozen=True)
class MetaCycleConfig:
    """Thresholds applied to trade candidates before adoption.

    Attributes:
      min_ev_after_cost    : candidates with ``ev_after_cost`` strictly
                             less than this value are filtered out.
                             Default 0.0 — filters only candidates whose
                             expected cost exceeds expected win.
      confidence_threshold : candidates with ``confidence`` strictly less
                             than this value are filtered out.  Default
                             0.0 — no filter.
      force_fallback       : if every trade candidate is filtered, adopt
                             the top-EV candidate anyway.  **False by
                             default** (F8-G fail-closed: all-filtered
                             cycles end in no adoption + no_trade_events,
                             the production-like behaviour).  Set True
                             explicitly ONLY for smoke/tests that need
                             the legacy Cycle 6.4 ≥1-trade guarantee —
                             it adopts a candidate that failed the EV /
                             confidence filters, which is never
                             acceptable in a production-like run.
      top_k                : Phase 9.19/J-3 config plumbing only. The
                             intended SELECTOR rule is "adopt the K
                             highest-EV candidates per cycle"
                             (backtest validated K=2 naive lift +25%
                             PnL — see docs/design/phase9_19_closure_memo.md).
                             At present, ``run_meta_cycle`` honours
                             ``top_k`` in the F-16 sort but ADOPTS ONLY
                             the rank-1 candidate (single-adopt
                             contract preserved). Must be >= 1; default
                             1 reproduces Phase 9.16 production
                             behaviour exactly. Multi-trade adoption
                             (K > 1 actually opening K positions per
                             cycle) is deferred to a follow-up phase
                             that requires changes to
                             MetaCycleRunResult, the execution
                             gateway, and position-management
                             invariants.
    """

    min_ev_after_cost: float = 0.0
    confidence_threshold: float = 0.0
    force_fallback: bool = False
    top_k: int = 1

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise ValueError(f"MetaCycleConfig.top_k must be >= 1 (got {self.top_k})")


@dataclass(frozen=True)
class MetaCycleRunResult:
    """Per-cycle Meta outcome.

    adopted=True implies ``trading_signal_id`` / ``adopted_*`` are set
    and one trading_signals row was written.  adopted=False implies the
    cycle ended in no_trade (no trade candidates existed and fallback
    was not invoked).

    ``adopted_ev_after_cost`` carries the adopted candidate's post-cost
    EV (F-1 fix — see docs/design/project_wide_logic_audit_fable5_findings.md);
    it is None when no candidate was adopted.  Consumers of the live
    entry gate must treat None as "EV unknown" and fail closed, never
    default it to 0.0.
    """

    cycle_id: str
    meta_decision_id: str
    adopted: bool
    trading_signal_id: str | None
    adopted_strategy_id: str | None
    adopted_instrument: str | None
    adopted_direction: str | None
    candidate_count: int
    trade_candidate_count: int
    filtered_count: int
    fallback_used: bool
    no_trade_event_count: int
    adopted_ev_after_cost: float | None = None


# --- Internal candidate representation --------------------------------------


@dataclass(frozen=True)
class _Candidate:
    instrument: str
    strategy_id: str
    strategy_type: str
    strategy_version: str | None
    direction: str  # 'buy' | 'sell' | 'no_trade'
    confidence: float
    ev_after_cost: float
    ev_before_cost: float
    ev_unit: str  # F8-F unit declaration; missing/legacy meta → "unknown"
    spread: float
    decision_chain_id: str | None
    signal_time_utc: Any  # datetime from strategy_signals.signal_time_utc


def _f16_sort_key(c: _Candidate) -> tuple[float, float, float, str]:
    """F-16 sort key.

    Primary: -ev_after_cost  (DESC in ascending sort)
    Secondary: -confidence   (DESC)
    Tertiary: spread         (ASC, lower preferred)
    Stable:   strategy_id    (ASC, deterministic tie-break)
    """
    return (-c.ev_after_cost, -c.confidence, c.spread, c.strategy_id)


# --- F-12 sanitizer for meta-domain payloads --------------------------------


def _meta_sanitizer(payload: dict[str, Any]) -> dict[str, Any]:
    """Meta-domain sanitizer.  Strategy/meta outputs carry no secrets
    today; we still route through a sanitizer to honour the F-12
    contract.  Returns a shallow copy to prevent aliasing."""
    return dict(payload)


# --- Public entry point -----------------------------------------------------


def run_meta_cycle(
    engine: Engine,
    *,
    cycle_id: str,
    clock: Clock,
    config: MetaCycleConfig | None = None,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    run_id: str | None = None,
    environment: str | None = None,
    code_version: str | None = None,
    config_version: str | None = None,
    ttl_seconds: int = 60,
) -> MetaCycleRunResult:
    """Run one Meta cycle over ``strategy_signals`` rows for *cycle_id*.

    Pipeline:
      1. Load every strategy_signals row for the cycle.
      2. Partition into trade candidates (direction ∈ {buy, sell}) and
         no-trade rows.  no-trade rows are not adopt-eligible but do
         not generate no_trade_events by themselves — they are
         strategy-originated, not meta-originated.
      3. Apply the F8-F ev_unit comparability gate (only
         ``pips_post_cost`` candidates are rankable; others rejected
         with ``meta.ev_unit_incomparable``) and the
         min_ev_after_cost / confidence_threshold filters to trade
         candidates.
      4. Sort survivors by F-16.  Adopt top-1 if any survive.
      5. Else, if ``force_fallback`` (opt-in for smoke/tests; default
         False per F8-G) and trade candidates exist, sort ALL trade
         candidates by F-16 and adopt top-1.  Mark
         ``fallback_used=True`` in the meta_decisions.filter_result
         JSON.
      6. Else (fail-closed default, or no trade candidates at all):
         adopt nothing; a cycle with zero trade candidates emits a
         single no_trade_events row with reason_code=NO_CANDIDATES.
      7. For every filtered-out trade candidate, write one
         no_trade_events row with the concrete reason.
      8. Enqueue every persisted row into secondary_sync_outbox.

    Raises:
      ValueError: on empty cycle_id or if no strategy_signals rows exist
                  for the cycle (Meta has nothing to act on).
    """
    if not cycle_id or not cycle_id.strip():
        raise ValueError("cycle_id must be non-empty")

    cfg = config or MetaCycleConfig()
    san = sanitizer or _meta_sanitizer
    now = clock.now()

    candidates = _load_candidates(engine, cycle_id=cycle_id)
    if not candidates:
        raise ValueError(
            f"no strategy_signals rows found for cycle_id={cycle_id!r}; "
            "run_strategy_cycle must run before run_meta_cycle"
        )

    trade_candidates = [c for c in candidates if c.direction in {"buy", "sell"}]

    # Filter pipeline (trade candidates only).
    filtered: list[_Candidate] = []
    rejections: list[dict[str, Any]] = []
    for c in trade_candidates:
        reason_code = _reject_reason(c, cfg)
        if reason_code is None:
            filtered.append(c)
        else:
            rejections.append(
                {
                    "strategy_id": c.strategy_id,
                    "instrument": c.instrument,
                    "reason_code": reason_code,
                    "ev_after_cost": c.ev_after_cost,
                    "ev_unit": c.ev_unit,
                    "confidence": c.confidence,
                }
            )

    survivors = sorted(filtered, key=_f16_sort_key)

    fallback_used = False
    adopted: _Candidate | None = None

    if survivors:
        adopted = survivors[0]
    elif cfg.force_fallback and trade_candidates:
        # Forced fallback — adopt the highest-EV trade candidate even
        # though it failed the normal filter.  This is the legacy Cycle
        # 6.4 ≥1-trade guarantee, now opt-in for smoke/tests only
        # (F8-G): the production-like default (force_fallback=False)
        # falls through and adopts nothing.
        adopted = sorted(trade_candidates, key=_f16_sort_key)[0]
        fallback_used = True

    score_contributions = _build_score_contributions(survivors if survivors else trade_candidates)

    filter_result = {
        "total_rows": len(candidates),
        "trade_candidates": len(trade_candidates),
        "filtered_out": len(rejections),
        "survivors": len(survivors),
        "fallback_used": fallback_used,
        "rejections": rejections,
    }

    active_strategies = [c.strategy_id for c in (survivors or trade_candidates)]

    meta_decision_id = generate_ulid()
    no_trade_reason = _derive_no_trade_reason(
        adopted=adopted,
        trade_candidates=trade_candidates,
        rejections=rejections,
    )

    _insert_meta_decision(
        engine,
        meta_decision_id=meta_decision_id,
        cycle_id=cycle_id,
        filter_result=filter_result,
        score_contributions=score_contributions,
        active_strategies=active_strategies,
        decision_time_utc=now,
        no_trade_reason=no_trade_reason,
    )
    _enqueue_meta_decision(
        engine,
        meta_decision_id=meta_decision_id,
        cycle_id=cycle_id,
        filter_result=filter_result,
        score_contributions=score_contributions,
        active_strategies=active_strategies,
        decision_time_utc=now,
        no_trade_reason=no_trade_reason,
        sanitizer=san,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )

    trading_signal_id: str | None = None
    if adopted is not None:
        trading_signal_id = generate_ulid()
        _insert_trading_signal(
            engine,
            trading_signal_id=trading_signal_id,
            meta_decision_id=meta_decision_id,
            cycle_id=cycle_id,
            instrument=adopted.instrument,
            strategy_id=adopted.strategy_id,
            signal_direction=adopted.direction,
            signal_time_utc=now,
            correlation_id=adopted.decision_chain_id,
            ttl_seconds=ttl_seconds,
        )
        _enqueue_trading_signal(
            engine,
            trading_signal_id=trading_signal_id,
            meta_decision_id=meta_decision_id,
            cycle_id=cycle_id,
            instrument=adopted.instrument,
            strategy_id=adopted.strategy_id,
            signal_direction=adopted.direction,
            signal_time_utc=now,
            correlation_id=adopted.decision_chain_id,
            ttl_seconds=ttl_seconds,
            sanitizer=san,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )

    no_trade_event_count = _write_no_trade_events(
        engine,
        cycle_id=cycle_id,
        meta_decision_id=meta_decision_id,
        rejections=rejections,
        trade_candidates_count=len(trade_candidates),
        adopted=adopted,
        event_time_utc=now,
        sanitizer=san,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )

    return MetaCycleRunResult(
        cycle_id=cycle_id,
        meta_decision_id=meta_decision_id,
        adopted=adopted is not None,
        trading_signal_id=trading_signal_id,
        adopted_strategy_id=adopted.strategy_id if adopted else None,
        adopted_instrument=adopted.instrument if adopted else None,
        adopted_direction=adopted.direction if adopted else None,
        candidate_count=len(candidates),
        trade_candidate_count=len(trade_candidates),
        filtered_count=len(rejections),
        fallback_used=fallback_used,
        no_trade_event_count=no_trade_event_count,
        adopted_ev_after_cost=adopted.ev_after_cost if adopted else None,
    )


# --- Candidate loading ------------------------------------------------------


def _load_candidates(engine: Engine, *, cycle_id: str) -> list[_Candidate]:
    sql = text(
        """
        SELECT instrument, strategy_id, strategy_type, strategy_version,
               signal_direction, confidence, signal_time_utc, meta
        FROM strategy_signals
        WHERE cycle_id = :cycle_id
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"cycle_id": cycle_id}).fetchall()

    out: list[_Candidate] = []
    for r in rows:
        meta_raw = r.meta
        meta = _parse_meta_json(meta_raw)
        out.append(
            _Candidate(
                instrument=r.instrument,
                strategy_id=r.strategy_id,
                strategy_type=r.strategy_type,
                strategy_version=r.strategy_version,
                direction=r.signal_direction,
                confidence=float(r.confidence) if r.confidence is not None else 0.0,
                ev_after_cost=float(meta.get("ev_after_cost", 0.0)),
                ev_before_cost=float(meta.get("ev_before_cost", 0.0)),
                # F8-F: legacy rows without an ev_unit key load as
                # "unknown" and are rejected fail-closed by _reject_reason.
                ev_unit=str(meta.get("ev_unit", EV_UNIT_UNKNOWN)),
                spread=float(meta.get("spread", 0.0)),
                decision_chain_id=meta.get("decision_chain_id"),
                signal_time_utc=r.signal_time_utc,
            )
        )
    return out


def _parse_meta_json(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (str, bytes, bytearray)):
        try:
            decoded = json.loads(raw)
            return decoded if isinstance(decoded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


# --- Filter / reason helpers ------------------------------------------------


def _reject_reason(c: _Candidate, cfg: MetaCycleConfig) -> str | None:
    # F8-F fail-closed unit gate: EV thresholds and the F-16 sort are only
    # meaningful in the canonical unit (pips, post-cost).  Candidates
    # declaring any other unit — or none at all — must never be ranked.
    if not is_comparable(c.ev_unit):
        return MetaFilterReason.EV_UNIT_INCOMPARABLE
    if c.ev_after_cost < cfg.min_ev_after_cost:
        return MetaReason.EV_BELOW_THRESHOLD
    if c.confidence < cfg.confidence_threshold:
        return MetaReason.CONFIDENCE_BELOW_THRESHOLD
    return None


def _build_score_contributions(ranked: list[_Candidate]) -> list[dict[str, Any]]:
    contributions: list[dict[str, Any]] = []
    sorted_for_rank = sorted(ranked, key=_f16_sort_key)
    for rank, c in enumerate(sorted_for_rank, start=1):
        contributions.append(
            {
                "rank": rank,
                "strategy_id": c.strategy_id,
                "instrument": c.instrument,
                "ev_after_cost": c.ev_after_cost,
                "confidence": c.confidence,
                "spread": c.spread,
            }
        )
    return contributions


def _derive_no_trade_reason(
    *,
    adopted: _Candidate | None,
    trade_candidates: list[_Candidate],
    rejections: list[dict[str, Any]],
) -> str | None:
    if adopted is not None:
        return None
    if not trade_candidates:
        return MetaReason.NO_CANDIDATES
    # All filtered AND force_fallback=False.
    if rejections:
        return rejections[0]["reason_code"]
    return MetaReason.NO_CANDIDATES


# --- meta_decisions INSERT + outbox -----------------------------------------


def _insert_meta_decision(
    engine: Engine,
    *,
    meta_decision_id: str,
    cycle_id: str,
    filter_result: dict[str, Any],
    score_contributions: list[dict[str, Any]],
    active_strategies: list[str],
    decision_time_utc: Any,
    no_trade_reason: str | None,
) -> None:
    sql = text(
        """
        INSERT INTO meta_decisions (
            meta_decision_id, cycle_id, filter_result,
            score_contributions, active_strategies, regime_detected,
            decision_time_utc, no_trade_reason
        ) VALUES (
            :meta_decision_id, :cycle_id, :filter_result,
            :score_contributions, :active_strategies, :regime_detected,
            :decision_time_utc, :no_trade_reason
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "meta_decision_id": meta_decision_id,
                "cycle_id": cycle_id,
                "filter_result": json.dumps(filter_result, ensure_ascii=False, sort_keys=True),
                "score_contributions": json.dumps(
                    score_contributions, ensure_ascii=False, sort_keys=True
                ),
                "active_strategies": json.dumps(
                    active_strategies, ensure_ascii=False, sort_keys=True
                ),
                "regime_detected": "normal",
                "decision_time_utc": decision_time_utc,
                "no_trade_reason": no_trade_reason,
            },
        )


def _enqueue_meta_decision(
    engine: Engine,
    *,
    meta_decision_id: str,
    cycle_id: str,
    filter_result: dict[str, Any],
    score_contributions: list[dict[str, Any]],
    active_strategies: list[str],
    decision_time_utc: Any,
    no_trade_reason: str | None,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> None:
    payload = {
        "meta_decision_id": meta_decision_id,
        "cycle_id": cycle_id,
        "filter_result": filter_result,
        "score_contributions": score_contributions,
        "active_strategies": active_strategies,
        "regime_detected": "normal",
        "decision_time_utc": decision_time_utc.isoformat(),
        "no_trade_reason": no_trade_reason,
    }
    enqueue_secondary_sync(
        engine,
        table_name="meta_decisions",
        primary_key=json.dumps([meta_decision_id]),
        version_no=0,
        payload=payload,
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )


# --- trading_signals INSERT + outbox ----------------------------------------


def _insert_trading_signal(
    engine: Engine,
    *,
    trading_signal_id: str,
    meta_decision_id: str,
    cycle_id: str,
    instrument: str,
    strategy_id: str,
    signal_direction: str,
    signal_time_utc: Any,
    correlation_id: str | None,
    ttl_seconds: int,
) -> None:
    sql = text(
        """
        INSERT INTO trading_signals (
            trading_signal_id, meta_decision_id, cycle_id, instrument,
            strategy_id, signal_direction, signal_time_utc,
            correlation_id, ttl_seconds
        ) VALUES (
            :trading_signal_id, :meta_decision_id, :cycle_id, :instrument,
            :strategy_id, :signal_direction, :signal_time_utc,
            :correlation_id, :ttl_seconds
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "trading_signal_id": trading_signal_id,
                "meta_decision_id": meta_decision_id,
                "cycle_id": cycle_id,
                "instrument": instrument,
                "strategy_id": strategy_id,
                "signal_direction": signal_direction,
                "signal_time_utc": signal_time_utc,
                "correlation_id": correlation_id,
                "ttl_seconds": ttl_seconds,
            },
        )


def _enqueue_trading_signal(
    engine: Engine,
    *,
    trading_signal_id: str,
    meta_decision_id: str,
    cycle_id: str,
    instrument: str,
    strategy_id: str,
    signal_direction: str,
    signal_time_utc: Any,
    correlation_id: str | None,
    ttl_seconds: int,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> None:
    payload = {
        "trading_signal_id": trading_signal_id,
        "meta_decision_id": meta_decision_id,
        "cycle_id": cycle_id,
        "instrument": instrument,
        "strategy_id": strategy_id,
        "signal_direction": signal_direction,
        "signal_time_utc": signal_time_utc.isoformat(),
        "correlation_id": correlation_id,
        "ttl_seconds": ttl_seconds,
    }
    enqueue_secondary_sync(
        engine,
        table_name="trading_signals",
        primary_key=json.dumps([trading_signal_id]),
        version_no=0,
        payload=payload,
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )


# --- no_trade_events INSERT + outbox ----------------------------------------


def _write_no_trade_events(
    engine: Engine,
    *,
    cycle_id: str,
    meta_decision_id: str,
    rejections: list[dict[str, Any]],
    trade_candidates_count: int,
    adopted: _Candidate | None,
    event_time_utc: Any,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> int:
    """Write one no_trade_events row per rejection.

    Additionally, when zero trade candidates existed at all, write a
    single NO_CANDIDATES row so operators can see *why* the cycle
    produced no trading_signal.  This row carries no instrument /
    strategy_id because it represents the whole-cycle verdict.
    """
    count = 0

    for rej in rejections:
        _insert_and_enqueue_no_trade_event(
            engine,
            cycle_id=cycle_id,
            meta_decision_id=meta_decision_id,
            reason_category="filter",
            reason_code=rej["reason_code"],
            reason_detail=(f"ev_after_cost={rej['ev_after_cost']}, confidence={rej['confidence']}"),
            instrument=rej["instrument"],
            strategy_id=rej["strategy_id"],
            event_time_utc=event_time_utc,
            sanitizer=sanitizer,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )
        count += 1

    if trade_candidates_count == 0 and adopted is None:
        _insert_and_enqueue_no_trade_event(
            engine,
            cycle_id=cycle_id,
            meta_decision_id=meta_decision_id,
            reason_category="meta",
            reason_code=MetaReason.NO_CANDIDATES,
            reason_detail="no trade candidates in cycle",
            instrument=None,
            strategy_id=None,
            event_time_utc=event_time_utc,
            sanitizer=sanitizer,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )
        count += 1

    return count


def _insert_and_enqueue_no_trade_event(
    engine: Engine,
    *,
    cycle_id: str,
    meta_decision_id: str,
    reason_category: str,
    reason_code: str,
    reason_detail: str | None,
    instrument: str | None,
    strategy_id: str | None,
    event_time_utc: Any,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> str:
    no_trade_event_id = generate_ulid()
    sql = text(
        """
        INSERT INTO no_trade_events (
            no_trade_event_id, cycle_id, meta_decision_id,
            reason_category, reason_code, reason_detail,
            source_component, instrument, strategy_id, event_time_utc
        ) VALUES (
            :no_trade_event_id, :cycle_id, :meta_decision_id,
            :reason_category, :reason_code, :reason_detail,
            :source_component, :instrument, :strategy_id, :event_time_utc
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "no_trade_event_id": no_trade_event_id,
                "cycle_id": cycle_id,
                "meta_decision_id": meta_decision_id,
                "reason_category": reason_category,
                "reason_code": reason_code,
                "reason_detail": reason_detail,
                "source_component": SOURCE_COMPONENT,
                "instrument": instrument,
                "strategy_id": strategy_id,
                "event_time_utc": event_time_utc,
            },
        )
    payload = {
        "no_trade_event_id": no_trade_event_id,
        "cycle_id": cycle_id,
        "meta_decision_id": meta_decision_id,
        "reason_category": reason_category,
        "reason_code": reason_code,
        "reason_detail": reason_detail,
        "source_component": SOURCE_COMPONENT,
        "instrument": instrument,
        "strategy_id": strategy_id,
        "event_time_utc": event_time_utc.isoformat(),
    }
    enqueue_secondary_sync(
        engine,
        table_name="no_trade_events",
        primary_key=json.dumps([no_trade_event_id]),
        version_no=0,
        payload=payload,
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    return no_trade_event_id


__all__ = [
    "MetaCycleConfig",
    "MetaCycleRunResult",
    "run_meta_cycle",
]
