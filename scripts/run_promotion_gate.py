"""run_promotion_gate — daily batch CLI for challenger → champion promotion (Phase 9.8).

Usage:
    python scripts/run_promotion_gate.py \\
        --challenger-run-id <training_run_id> \\
        --db-url sqlite:///paper.db

The script loads paper stats stored in training_runs.input_params (JSON with keys
paper_days, trade_count, sharpe, max_drawdown).  If a champion exists its stats are
loaded the same way; if no champion exists NO_CHAMPION_STATS is used as baseline.

Exit codes:
  0 — decision logged (promoted or deferred)
  1 — challenger run not found or missing required stats fields
"""

from __future__ import annotations

import json
import logging
import sys

import click
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import WallClock
from fx_ai_trading.services.learning_ops import LearningOps
from fx_ai_trading.services.promotion_gate import (
    NO_CHAMPION_STATS,
    ChallengerStats,
    ChampionStats,
    PromotionCriteria,
    PromotionGate,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger(__name__)

_REQUIRED_STATS = ("paper_days", "trade_count", "sharpe", "max_drawdown")


def _load_run(engine, run_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT training_run_id, model_id, status, input_params"
                " FROM training_runs WHERE training_run_id = :rid"
            ),
            {"rid": run_id},
        ).fetchone()
    return dict(row._mapping) if row else None


@click.command()
@click.option("--challenger-run-id", required=True, help="training_run_id of the challenger")
@click.option(
    "--db-url",
    default="sqlite:///paper.db",
    show_default=True,
    help="SQLAlchemy database URL",
)
@click.option("--min-days", default=14, show_default=True)
@click.option("--min-trades", default=100, show_default=True)
@click.option("--sharpe-margin", default=0.2, show_default=True)
@click.option("--max-dd-ratio", default=1.2, show_default=True)
def main(
    challenger_run_id: str,
    db_url: str,
    min_days: int,
    min_trades: int,
    sharpe_margin: float,
    max_dd_ratio: float,
) -> None:
    engine = create_engine(db_url)
    ops = LearningOps(clock=WallClock())
    ops.ensure_promotion_schema(engine)

    # --- load challenger row ---
    challenger_row = _load_run(engine, challenger_run_id)
    if challenger_row is None:
        _log.error("Challenger run not found: %s", challenger_run_id)
        sys.exit(1)

    try:
        stats_raw = json.loads(challenger_row["input_params"] or "{}")
        for key in _REQUIRED_STATS:
            if key not in stats_raw:
                raise KeyError(key)
        challenger = ChallengerStats(
            model_id=challenger_row["model_id"] or "",
            training_run_id=challenger_run_id,
            paper_days=int(stats_raw["paper_days"]),
            trade_count=int(stats_raw["trade_count"]),
            sharpe=float(stats_raw["sharpe"]),
            max_drawdown=float(stats_raw["max_drawdown"]),
        )
    except (KeyError, ValueError) as exc:
        _log.error("Challenger run missing required stats field: %s", exc)
        sys.exit(1)

    # --- load champion row (may be None) ---
    champion_row = ops.get_champion(engine)
    if champion_row is not None:
        try:
            champ_raw = json.loads(champion_row["input_params"] or "{}")
            champion: ChampionStats = ChampionStats(
                model_id=champion_row["model_id"] or "",
                training_run_id=champion_row["training_run_id"],
                sharpe=float(champ_raw.get("sharpe", 0.0)),
                max_drawdown=float(champ_raw.get("max_drawdown", float("inf"))),
            )
        except (ValueError, TypeError):
            _log.warning("Could not parse champion stats; using NO_CHAMPION_STATS baseline")
            champion = NO_CHAMPION_STATS
    else:
        champion = NO_CHAMPION_STATS

    # --- evaluate ---
    criteria = PromotionCriteria(
        min_days=min_days,
        min_trades=min_trades,
        sharpe_margin=sharpe_margin,
        max_dd_ratio=max_dd_ratio,
    )
    gate = PromotionGate(criteria)
    decision = gate.evaluate(challenger, champion)

    _log.info(
        "PromotionGate result: promoted=%s reason=%s",
        decision.promoted,
        decision.reason,
    )

    # --- promote if criteria met ---
    if decision.promoted:
        ops.promote(engine, challenger_run_id)
        _log.info("Promoted %s to champion", challenger_run_id)

    # --- audit log ---
    ops.log_promotion_decision(
        engine,
        challenger_run_id=challenger_run_id,
        champion_run_id=champion.training_run_id,
        promoted=decision.promoted,
        reason=decision.reason,
        criteria_met=decision.criteria,
    )

    click.echo(
        f"{'PROMOTED' if decision.promoted else 'DEFERRED'}: "
        f"challenger={challenger_run_id} reason={decision.reason}"
    )


if __name__ == "__main__":
    main()
