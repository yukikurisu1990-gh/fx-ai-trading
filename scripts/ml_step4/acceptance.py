"""Acceptance / failure evaluator for the PR #407 §10 criteria (fail-closed).

Outputs exactly one allowed final status. An honest below-threshold result is a
valid, reportable ``..._DOES_NOT_MEET_PREREGISTERED_CRITERIA`` outcome — never
hidden and never retried into a search. Hard invalidation triggers map to the
enumerated ``ML_STEP4_RUN_INVALID_<REASON>`` vocabulary.

Note the §10 nuance: **insufficient OOS sample** (below the minimum trade count
or daily coverage) is a *hard invalidation trigger*
(``ML_STEP4_RUN_INVALID_INSUFFICIENT_OOS_SAMPLE``), not a soft below-threshold
result. Provenance incompleteness is ``..._PROVENANCE_MISSING``.
"""

from __future__ import annotations

from typing import Any

from . import contract

MEETS = "ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_MEETS_PREREGISTERED_CRITERIA"
DOES_NOT_MEET = "ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_DOES_NOT_MEET_PREREGISTERED_CRITERIA"

# Enumerated invalid reasons, in deterministic precedence order.
INVALID_REASONS: tuple[str, ...] = (
    "CHECKSUM_MISMATCH",
    "PROVENANCE_MISSING",
    "LABEL_CONTRACT_VIOLATION",
    "TRAIN_SERVE_MISMATCH",
    "LOOKAHEAD_LEAKAGE",
    "INSUFFICIENT_OOS_SAMPLE",
    "POST_HOC_TUNING",
    "RAW_DATA_COMMITTED",
    "PERSONAL_PATH_LEAKAGE",
    "SCOPE_EXPANSION",
)


def invalid_status(reason: str) -> str:
    """Return the ``ML_STEP4_RUN_INVALID_<REASON>`` status; fail closed on typos."""
    if reason not in INVALID_REASONS:
        raise ValueError(f"unknown invalid reason {reason!r}")
    return f"ML_STEP4_RUN_INVALID_{reason}"


# PR #411 B-3 fix: required metric inputs. "a.b" means metrics["a"]["b"].
# A missing or None value for ANY of these makes the metrics record
# provenance-incomplete → ML_STEP4_RUN_INVALID_PROVENANCE_MISSING. Missing
# metrics must NEVER become passing defaults.
REQUIRED_METRIC_PATHS: tuple[str, ...] = (
    "trade_count",
    "daily_coverage_frac",
    "expectancy_pips",
    "daily_portfolio_sharpe_annualised",
    "max_equity_drawdown.max_drawdown_frac",
    "turnover_trades_per_day",
    "pair_concentration.max_trade_share",
    "pair_concentration.max_positive_pnl_share",
    "cost_sensitivity.1.0pip.expectancy_pips",
)


def _lookup(metrics: dict[str, Any], path: str) -> Any:
    """Resolve a dotted path; the '1.0pip' cost-cell key is one segment."""
    if path.startswith("cost_sensitivity."):
        rest = path[len("cost_sensitivity.") :]
        cell, _, leaf = rest.rpartition(".")
        node = metrics.get("cost_sensitivity")
        if not isinstance(node, dict):
            return None
        cell_node = node.get(cell)
        if not isinstance(cell_node, dict):
            return None
        return cell_node.get(leaf)
    node: Any = metrics
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def missing_required_metrics(metrics: dict[str, Any]) -> list[str]:
    """Return the required metric paths that are absent or None."""
    return [p for p in REQUIRED_METRIC_PATHS if _lookup(metrics, p) is None]


class AcceptanceEvaluator:
    """Evaluate holdout metrics against the frozen §10 acceptance criteria."""

    def __init__(self, criteria: dict[str, Any] | None = None) -> None:
        self.criteria = criteria or contract.ACCEPTANCE_CRITERIA

    def evaluate(
        self,
        metrics: dict[str, Any],
        *,
        provenance_complete: bool,
        hard_triggers: set[str] | None = None,
    ) -> dict[str, Any]:
        """Return {status, criteria table, hard_triggers, meets, missing_metrics}."""
        triggers: set[str] = set(hard_triggers or set())
        for t in triggers:
            if t not in INVALID_REASONS:
                raise ValueError(f"unknown hard trigger {t!r}")

        # PR #411 B-3 fix: fail closed on missing/None required metric inputs
        # BEFORE any criterion is evaluated. Missing metrics are a provenance
        # gap, never passing defaults.
        missing = missing_required_metrics(metrics)
        if missing:
            triggers.add("PROVENANCE_MISSING")

        if not missing:
            trade_count = int(metrics["trade_count"])
            coverage = float(metrics["daily_coverage_frac"])
            # Sample sufficiency is a HARD trigger, not a soft miss.
            if (
                trade_count < self.criteria["min_holdout_trades"]
                or coverage < self.criteria["min_daily_coverage_frac"]
            ):
                triggers.add("INSUFFICIENT_OOS_SAMPLE")
        if not provenance_complete:
            triggers.add("PROVENANCE_MISSING")

        if triggers:
            reason = next(r for r in INVALID_REASONS if r in triggers)
            return {
                "status": invalid_status(reason),
                "hard_triggers": sorted(triggers),
                "meets": False,
                "criteria": {},
                "missing_metrics": missing,
            }

        table = self._quality_criteria(metrics)
        meets = all(c["passed"] for c in table.values())
        return {
            "status": MEETS if meets else DOES_NOT_MEET,
            "hard_triggers": [],
            "meets": meets,
            "criteria": table,
            "missing_metrics": [],
        }

    def _quality_criteria(self, m: dict[str, Any]) -> dict[str, dict[str, Any]]:
        # PR #411 B-3 fix: direct indexing, no fallback defaults — presence of
        # every required key is guaranteed by missing_required_metrics() before
        # this method is reached; an unexpected gap raises rather than passes.
        c = self.criteria
        dd = m["max_equity_drawdown"]
        conc = m["pair_concentration"]
        exp_1pip = float(m["cost_sensitivity"]["1.0pip"]["expectancy_pips"])

        def crit(name: str, value: float, threshold: float, passed: bool) -> dict[str, Any]:
            return {"value": value, "threshold": threshold, "passed": bool(passed)}

        exp = float(m["expectancy_pips"])
        sharpe = float(m["daily_portfolio_sharpe_annualised"])
        dd_frac = float(dd["max_drawdown_frac"])
        turnover = float(m["turnover_trades_per_day"])
        max_trade_share = float(conc["max_trade_share"])
        max_pos_share = float(conc["max_positive_pnl_share"])

        return {
            "post_cost_expectancy": crit(
                "post_cost_expectancy",
                exp,
                c["min_post_cost_expectancy_pips"],
                exp > c["min_post_cost_expectancy_pips"],
            ),
            "daily_portfolio_sharpe": crit(
                "daily_portfolio_sharpe",
                sharpe,
                c["min_daily_portfolio_sharpe_annualised"],
                sharpe >= c["min_daily_portfolio_sharpe_annualised"],
            ),
            "max_equity_drawdown": crit(
                "max_equity_drawdown",
                dd_frac,
                c["max_equity_drawdown_frac"],
                dd_frac <= c["max_equity_drawdown_frac"],
            ),
            "turnover": crit(
                "turnover",
                turnover,
                c["max_turnover_trades_per_day"],
                turnover <= c["max_turnover_trades_per_day"],
            ),
            "pair_trade_concentration": crit(
                "pair_trade_concentration",
                max_trade_share,
                c["max_pair_trade_share"],
                max_trade_share <= c["max_pair_trade_share"],
            ),
            "pair_pnl_concentration": crit(
                "pair_pnl_concentration",
                max_pos_share,
                c["max_pair_positive_pnl_share"],
                max_pos_share <= c["max_pair_positive_pnl_share"],
            ),
            "cost_sensitivity_1pip": crit(
                "cost_sensitivity_1pip",
                exp_1pip,
                c["cost_sensitivity_min_expectancy_at_1pip"],
                exp_1pip >= c["cost_sensitivity_min_expectancy_at_1pip"],
            ),
        }
