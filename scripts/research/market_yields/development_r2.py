"""T-R2 Stage 1: the twenty-day repricing state, its control, and the residual.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.market_yields.development_r2

Runs exactly what `prereg_r2.py` froze — one lookback, one sign, four books, the
universe-closed layer, the same availability lag — and applies the frozen screen.
Seen data decides nothing either way; the result goes back to Human.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

import numpy as np
import pandas as pd

from scripts.research.market_yields import (
    RECORD_DIR,
    development,
    portfolio,
    prereg_r2,
    risk,
)
from scripts.research.model_learning import assert_not_protected

#: The one place the run's own configuration differs from the fast book: the prereg
#: names the layer's own neutralisation pass rather than a pre-step.
BOOK = portfolio.BookConfig(
    name="t_r2",
    mapping="linear",
    neutralize_leading_factor=True,
    weight_cap=0.25,
    band=0.10,
    vol_target=0.10,
    max_leverage=1_000_000.0,
)
COST_STRESSES: tuple[float, ...] = (1.5, 2.0)


def _beta(score: pd.DataFrame, control: pd.DataFrame) -> pd.Series:
    """The daily cross-sectional regression coefficient the residual removes."""
    values = {}
    for day in score.index:
        y = score.loc[day].to_numpy(dtype=float)
        x = control.loc[day].to_numpy(dtype=float)
        ok = np.isfinite(y) & np.isfinite(x)
        if ok.sum() < 3 or float(x[ok] @ x[ok]) <= 0.0:
            continue
        values[day] = float(x[ok] @ y[ok]) / float(x[ok] @ x[ok])
    return pd.Series(values, name="beta")


def _persistence(result: dict[str, Any]) -> dict[str, Any]:
    daily = result["daily"]
    columns = [c for c in daily.columns if c.startswith("x_")]
    weights = daily[columns].div(daily["leverage"].replace(0.0, np.nan), axis=0)
    autocorr = float(np.nanmean([weights[c].autocorr(1) for c in columns]))
    return {
        "share_days_traded": round(float(daily["traded"].mean()), 4),
        "position_autocorrelation_1d": round(autocorr, 4),
        "implied_position_half_life_days": round(float(np.log(0.5) / np.log(autocorr)), 2)
        if 0 < autocorr < 1
        else None,
        "mean_held_max_weight": round(float(daily["held_max_weight"].mean()), 4),
    }


def _book(
    score: pd.DataFrame,
    excess: pd.DataFrame,
    universe: list[str],
    cost_multiple: float | None = None,
) -> dict[str, Any]:
    usable = score.dropna(how="any")
    return portfolio.run_book(BOOK, usable, excess, universe=universe, cost_multiple=cost_multiple)


def run() -> dict[str, Any]:
    from scripts.research.model_learning import corpus as corpus_module

    universe = list(prereg_r2.UNIVERSE)
    panel = corpus_module.currency_panel()
    excess = portfolio.universe_panel(panel, universe)
    days = pd.DatetimeIndex(excess.index)
    assert_not_protected(str(days[0].date()), str(days[-1].date()))

    frames = {
        currency: pd.read_parquet(
            development.ROOT / development.DATA_DIR / f"{currency.lower()}_2y.parquet"
        )
        for currency in universe
    }
    yield_panel = development.lagged_yield_panel(frames, days)

    slow = prereg_r2.PRIMARY_HORIZON_DAYS
    fast = development.LOOKBACK
    state = development._z(yield_panel.diff(slow))
    control = development._z(excess.rolling(slow).sum())
    residual = development._residualise(state, control)
    beta = _beta(state, control)
    momentum_leg = -control.mul(beta, axis=0)

    scores = {
        "A_fast_5d_reference": development._z(yield_panel.diff(fast)),
        "B_slow_rate_state": state,
        "C_fx_price_control": control,
        "D_residualised": residual,
        "E_momentum_leg_of_D": momentum_leg,
    }

    books: dict[str, Any] = {}
    for name, score in scores.items():
        result = _book(score, excess, universe)
        usable = score.dropna(how="any")
        books[name] = {
            "summary": development._summary(result),
            "blocks": development._blocks(result),
            "per_currency_gross_pnl": development._per_currency(result),
            "persistence": _persistence(result),
            "ic": {f"{h}d": development._ic(usable, excess, h) for h in development.HORIZONS},
            "signal_autocorrelation_1d": round(
                float(np.nanmean([usable[c].autocorr(1) for c in universe])), 4
            ),
            "cost_stress": {
                f"x{multiple:g}": development._summary(
                    _book(score, excess, universe, cost_multiple=multiple)
                )["net_sharpe"]
                for multiple in COST_STRESSES
            },
        }

    drops = {}
    for dropped in universe:
        kept = [c for c in universe if c != dropped]
        kept_excess = portfolio.universe_panel(panel, kept)
        kept_days = pd.DatetimeIndex(kept_excess.index)
        kept_yields = development.lagged_yield_panel({c: frames[c] for c in kept}, kept_days)
        kept_state = development._z(kept_yields.diff(slow))
        kept_control = development._z(kept_excess.rolling(slow).sum())
        kept_score = development._residualise(kept_state, kept_control)
        result = portfolio.run_book(BOOK, kept_score.dropna(how="any"), kept_excess, universe=kept)
        drops[f"without_{dropped}"] = development._summary(result)["net_sharpe"]

    primary = books["D_residualised"]["summary"]
    rate_leg = books["B_slow_rate_state"]["summary"]["gross_annual_return"]
    momentum_leg_return = books["E_momentum_leg_of_D"]["summary"]["gross_annual_return"]
    decomposition = {
        "d_gross_annual_return": primary["gross_annual_return"],
        "rate_leg_gross_annual_return": rate_leg,
        "momentum_leg_gross_annual_return": momentum_leg_return,
        "reconciliation_gap": round(
            primary["gross_annual_return"] - rate_leg - momentum_leg_return, 5
        ),
        "rate_leg_share_of_d_gross": round(rate_leg / primary["gross_annual_return"], 4)
        if primary["gross_annual_return"] not in (0.0, -0.0)
        else None,
        "beta_mean": round(float(beta.mean()), 4),
        "beta_sd": round(float(beta.std(ddof=0)), 4),
        "beta_p05_p95": [
            round(float(beta.quantile(0.05)), 4),
            round(float(beta.quantile(0.95)), 4),
        ],
        "note": (
            "the legs are run through the same machinery as D, so capping and the band make the "
            "split approximate; the reconciliation gap is the size of that approximation"
        ),
    }

    vol_per_unit_gross = primary["realized_annual_vol"] / primary["mean_currency_gross"]
    stress = risk.gap_stress(
        development.ROOT, universe, vol_per_unit_gross=vol_per_unit_gross, target_vol=0.10
    )
    capacity_rows = {
        f"{target:g}": risk.leverage_for_return(
            development.ROOT,
            universe,
            vol_per_unit_gross=vol_per_unit_gross,
            net_sharpe=primary["net_sharpe"],
            annual_target=target,
        )
        for target in (0.05, 0.10)
    }

    screen = _screen(books, drops, decomposition, stress)
    return {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "track": "T-R2",
        "prereg": prereg_r2.PREREG,
        "prereg_digest": hashlib.sha256(
            json.dumps(prereg_r2.PREREG, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "feasibility_before_the_run": prereg_r2.feasibility(),
        "executed_book_config": {
            field: getattr(BOOK, field)
            for field in (
                "name",
                "mapping",
                "neutralize_leading_factor",
                "weight_cap",
                "band",
                "vol_target",
                "max_leverage",
                "cost_multiple",
                "sigma_window",
                "factor_window",
                "vol_window",
            )
        },
        "universe": universe,
        "decision_days": int(len(days)),
        "span": {"first": str(days[0].date()), "last": str(days[-1].date())},
        "identity_check": portfolio.identity_check(
            panel, universe, np.array([0.25, -0.25, 0.10, -0.05, -0.05])
        ),
        "books": books,
        "decomposition_of_the_primary_test": decomposition,
        "leave_one_currency_out_net_sharpe": drops,
        "gap_stress_at_10pct_vol": stress,
        "annual_return_capacity": capacity_rows,
        "screen": screen,
        "verdict": screen["verdict"],
        "protected_spans_read": False,
    }


def _screen(
    books: dict[str, Any],
    drops: dict[str, float],
    decomposition: dict[str, Any],
    stress: dict[str, Any],
) -> dict[str, Any]:
    """The frozen screen, applied exactly as written."""
    slow = books["B_slow_rate_state"]["summary"]
    control = books["C_fx_price_control"]["summary"]
    primary = books["D_residualised"]["summary"]
    blocks = books["D_residualised"]["blocks"]
    positive_blocks = sum(1 for row in blocks if (row["net_sharpe"] or 0) > 0)
    share = decomposition["rate_leg_share_of_d_gross"]
    conditions = {
        "B gross Sharpe > 0": slow["gross_sharpe"] > 0,
        "D carries a positive net increment over C": primary["net_sharpe"] - control["net_sharpe"]
        > 0,
        "D's rate-residual leg carries at least half of D's gross": bool(
            share is not None and share >= 0.5
        ),
        "a majority of the six blocks are positive": positive_blocks > len(blocks) / 2,
        "the sign survives dropping any single currency": all(v > 0 for v in drops.values()),
        f"turnover at or below {prereg_r2.TURNOVER_BOUND:g}": primary[
            "turnover_round_trips_per_year_per_unit_gross"
        ]
        <= prereg_r2.TURNOVER_BOUND,
        "the annual cost does not exceed the annual gross": primary["annual_cost"]
        <= primary["gross_annual_return"],
        "net Sharpe stays positive at 1.5x and 2x cost": all(
            value > 0 for value in books["D_residualised"]["cost_stress"].values()
        ),
        "5% annual net is reachable inside the gap stress": bool(
            primary["net_sharpe"] > 0 and not stress["loss_cut_on_gap"]
        ),
    }
    shared = all(conditions.values())
    net = primary["net_sharpe"]
    if shared and net >= prereg_r2.CANDIDATE_NET_SHARPE:
        decision, verdict = "candidate", "MARKET_YIELD_SLOW_REPRICING_DEVELOPMENT_CANDIDATE"
    elif shared and net >= prereg_r2.MARGINAL_NET_SHARPE:
        decision, verdict = (
            "marginal",
            "MARKET_YIELD_SLOW_REPRICING_MARGINAL_DEVELOPMENT_CANDIDATE",
        )
    else:
        decision, verdict = "stop", "MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
    return {
        "shared_conditions": conditions,
        "all_shared_conditions_hold": shared,
        "primary_net_sharpe": net,
        "positive_blocks": positive_blocks,
        "decision": decision,
        "verdict": verdict,
        "decision_grade": False,
        "note": (
            "a development screen. The span separates only a net Sharpe near 1.13 at 80% power, "
            "so neither a pass nor a stop here settles whether the slow state leads FX"
        ),
    }


def main() -> int:
    record = run()
    path = development.ROOT / RECORD_DIR / "development_r2.json"
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    for name, book in record["books"].items():
        summary = book["summary"]
        print(
            f"{name}: gross {summary['gross_sharpe']:+.3f} net {summary['net_sharpe']:+.3f} "
            f"turnover {summary['turnover_round_trips_per_year_per_unit_gross']:.1f} "
            f"IC20 {book['ic'].get('20d')}"
        )
    print("decomposition:", record["decomposition_of_the_primary_test"])
    print("leave-one-out:", record["leave_one_currency_out_net_sharpe"])
    print("verdict:", record["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
