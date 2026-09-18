"""T-R2 Stage 1: the twenty-day repricing state, its control, and the residual.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.market_yields.development_r2

Runs exactly what `prereg_r2.py` froze — one lookback, one sign, four books, the
universe-closed layer, the same availability lag — and applies the frozen screen.
Seen data decides nothing either way; the result goes back to Human.

Two things the frozen text asked for cannot be delivered as literally as it reads,
and both are recorded in `deviations_from_the_frozen_text` rather than quietly
absorbed: the pre-registered leg decomposition measures a ratio of two separately
normalised books rather than a share of P&L, and the run reports that fact beside
the number the screen consumes.
"""

from __future__ import annotations

import dataclasses
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


def _daily_corr(left: dict[str, Any], right: dict[str, Any]) -> float:
    """Correlation of two books' daily gross P&L over the days both traded."""
    a = left["daily"].set_index("decision_day")["gross"]
    b = right["daily"].set_index("decision_day")["gross"]
    joined = pd.concat([a, b], axis=1, join="inner").dropna()
    return round(float(joined.iloc[:, 0].corr(joined.iloc[:, 1])), 4)


def _extra(result: dict[str, Any]) -> dict[str, Any]:
    """The numbers `_summary` does not carry and a break-even book needs.

    `_summary` is shared with the fast track and pinned by its record, so the
    additions live here rather than changing a published shape.
    """
    daily = result["daily"]
    net = daily["net"].to_numpy(dtype=float)
    gross = daily["gross"].to_numpy(dtype=float)
    days = len(daily)
    annual_gross = float(np.mean(gross) * 252.0)
    annual_cost = float(daily["cost"].mean() * 252.0)
    #: the band and the weights do not look at cost, so exposures are unchanged by a
    #: cost multiple and the charged cost scales exactly linearly with it
    return {
        "gross_t_stat": round(float(np.mean(gross) / np.std(gross, ddof=0) * np.sqrt(days)), 3),
        "net_t_stat": round(float(np.mean(net) / np.std(net, ddof=0) * np.sqrt(days)), 3),
        "break_even_cost_multiple": round(annual_gross / annual_cost, 3)
        if annual_cost > 0
        else None,
        "faithful_annual_implementation_cost": round(
            float(daily["implementation_cost"].mean() * 252.0), 5
        ),
    }


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


def build_scores(
    yield_panel: pd.DataFrame, excess: pd.DataFrame
) -> tuple[dict[str, pd.DataFrame], pd.Series]:
    """Every book's score, from the frozen lookback and the frozen sign.

    Separated from `run` so the construction can be tested without the corpus: the
    lookback is read from the pre-registration at call time, nothing is shifted
    forward, and a row dated `t` uses no value dated after `t`.
    """
    slow = prereg_r2.PRIMARY_HORIZON_DAYS
    fast = development.LOOKBACK
    state = development._z(yield_panel.diff(slow))
    control = development._z(excess.rolling(slow).sum())
    residual = development._residualise(state, control)
    beta = _beta(state, control)
    momentum_leg = -control.mul(beta, axis=0)
    return {
        "A_fast_5d_reference": development._z(yield_panel.diff(fast)),
        "B_slow_rate_state": state,
        "C_fx_price_control": control,
        "D_residualised": residual,
        "E_momentum_leg_of_D": momentum_leg,
    }, beta


def executed_book_config() -> dict[str, Any]:
    """Every field of the book that ran, from the dataclass rather than a kept list.

    A hand-kept list is how `leverage_hysteresis` — live inside the vol targeter —
    went unrecorded: the record then described a book the run did not execute.
    """
    return {field.name: getattr(BOOK, field.name) for field in dataclasses.fields(BOOK)}


def decompose_primary(
    books: dict[str, Any], results: dict[str, Any], beta: pd.Series
) -> dict[str, Any]:
    """The pre-registered leg decomposition, and what it can and cannot measure.

    The rate leg is book B and the momentum leg is book E, named here rather than
    passed in, so a leg sourced from the wrong book is a change to this function.
    """
    primary = books["D_residualised"]["summary"]
    rate_leg = books["B_slow_rate_state"]["summary"]["gross_annual_return"]
    momentum_leg_return = books["E_momentum_leg_of_D"]["summary"]["gross_annual_return"]
    share = (
        round(rate_leg / primary["gross_annual_return"], 4)
        if primary["gross_annual_return"] not in (0.0, -0.0)
        else None
    )
    return {
        "d_gross_annual_return": primary["gross_annual_return"],
        "rate_leg_gross_annual_return": rate_leg,
        "momentum_leg_gross_annual_return": momentum_leg_return,
        "reconciliation_gap": round(
            primary["gross_annual_return"] - rate_leg - momentum_leg_return, 5
        ),
        "rate_leg_share_of_d_gross": share,
        "unattributed_share_of_d_gross": round(
            1.0 - share - momentum_leg_return / primary["gross_annual_return"], 4
        )
        if share is not None
        else None,
        "beta_mean": round(float(beta.mean()), 4),
        "beta_sd": round(float(beta.std(ddof=0)), 4),
        "beta_p05_p95": [
            round(float(beta.quantile(0.05)), 4),
            round(float(beta.quantile(0.95)), 4),
        ],
        "share_of_days_beta_negative": round(float((beta < 0).mean()), 4),
        "what_the_ratio_is_not": (
            "construction.capped_weights renormalises each side to a fixed total, so it is exactly "
            "invariant to a positive per-day scalar. Book E's score is -beta_t * C_t, and that "
            "scalar is discarded: E is the sign of -beta_t applied to the control, not the leg at "
            "the magnitude it carries inside D. B, E and D are each normalised per day, so their "
            "annual returns are not additive and the pre-registered ratio is a comparison of three "
            "separately levered books rather than a share of one book's P&L. The reconciliation "
            "gap is that non-additivity, not the cap-and-band approximation"
        ),
        "what_answers_the_question_instead": (
            "whether D is a momentum artefact is answered by how D's daily P&L moves, which is "
            "measured directly below over every decision day rather than inferred from a ratio"
        ),
        "d_daily_gross_correlation_with_rate_leg": _daily_corr(
            results["D_residualised"], results["B_slow_rate_state"]
        ),
        "d_daily_gross_correlation_with_momentum_leg": _daily_corr(
            results["D_residualised"], results["E_momentum_leg_of_D"]
        ),
    }


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
    scores, beta = build_scores(yield_panel, excess)

    books: dict[str, Any] = {}
    results: dict[str, Any] = {}
    for name, score in scores.items():
        result = _book(score, excess, universe)
        results[name] = result
        usable = score.dropna(how="any")
        books[name] = {
            "summary": development._summary(result),
            "extra": _extra(result),
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
        #: the pre-run feasibility frame, applied to this book rather than dropped: it is
        #: the one instrument that puts the measured IC next to the IC the costs demand
        books[name]["ic_comparison"] = development._ic_comparison(books[name], slow)

    drops = {}
    for dropped in universe:
        kept = [c for c in universe if c != dropped]
        kept_excess = portfolio.universe_panel(panel, kept)
        kept_days = pd.DatetimeIndex(kept_excess.index)
        assert_not_protected(str(kept_days[0].date()), str(kept_days[-1].date()))
        kept_yields = development.lagged_yield_panel({c: frames[c] for c in kept}, kept_days)
        kept_state = development._z(kept_yields.diff(slow))
        kept_control = development._z(kept_excess.rolling(slow).sum())
        kept_score = development._residualise(kept_state, kept_control)
        result = portfolio.run_book(BOOK, kept_score.dropna(how="any"), kept_excess, universe=kept)
        drops[f"without_{dropped}"] = development._summary(result)["net_sharpe"]

    primary = books["D_residualised"]["summary"]
    decomposition = decompose_primary(books, results, beta)

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

    screen = _screen(books, drops, decomposition, capacity_rows)
    return {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "workflow_status": "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        "track": "T-R2",
        "prereg": prereg_r2.PREREG,
        "prereg_digest": hashlib.sha256(
            json.dumps(prereg_r2.PREREG, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "feasibility_before_the_run": prereg_r2.feasibility(),
        "executed_book_config": executed_book_config(),
        "universe": universe,
        "return_panel_days": int(len(days)),
        "decision_days_used_by_the_primary_test": books["D_residualised"]["summary"]["days"],
        "span": {"first": str(days[0].date()), "last": str(days[-1].date())},
        "identity_check": portfolio.identity_check(
            panel, universe, np.array([0.25, -0.25, 0.10, -0.05, -0.05])
        ),
        "books": books,
        "decomposition_of_the_primary_test": decomposition,
        "leave_one_currency_out_net_sharpe": drops,
        "what_leave_one_out_changes": (
            "dropping a currency rebuilds the tradable pair set, so every kept currency's return "
            "definition changes as well as the cross-section. It is the right test for a routed "
            "book — a four-name book is what would actually be traded — but it is not a subset of "
            "the five-name result, and a uniform drop across all five is a level shift rather than "
            "a concentration in the currencies that were removed"
        ),
        "against_the_repaired_fast_run": _fast_comparison(books),
        "gap_stress_at_10pct_vol": stress,
        "annual_return_capacity": capacity_rows,
        "screen": screen,
        "verdict": screen["verdict"],
        "deviations_from_the_frozen_text": [
            {
                "clause": "D's rate-residual leg carries at least half of D's gross P&L",
                "what_was_measured": (
                    "the ratio of book B's annual gross return to book D's. Each book is levered "
                    "to its own volatility target and its weights are renormalised per day, so "
                    "this is not a share of D's P&L and the three legs do not sum to D"
                ),
                "why_it_was_not_changed": (
                    "the condition is digest-pinned; applying something else after seeing the "
                    "result would be the rescue the ruling forbids. It is applied as frozen, and "
                    "the quantity that does answer the question — the correlation of D's daily "
                    "P&L with each leg's — is recorded beside it"
                ),
            },
            {
                "clause": "book E is the momentum leg of D",
                "what_was_measured": (
                    "E is -beta_t * C_t run standalone, and capped_weights discards the positive "
                    "per-day scalar exactly, so E is the sign of -beta_t on the control rather "
                    "than the leg at the magnitude it carries inside D"
                ),
                "why_it_was_not_changed": "same reason; the fact is recorded rather than corrected",
            },
        ],
        "protected_spans_read": False,
    }


def _fast_comparison(books: dict[str, Any]) -> dict[str, Any]:
    """The like-for-like comparator: the fast track re-run through this same layer.

    The diagnostic the prereg posed is about the primary test, and the fast track's
    primary test is its own residual — not its rate-state book. Comparing D against
    the fast rate book overstates the change, and the repaired fast record is already
    committed, so the honest comparison costs nothing.
    """
    path = development.ROOT / RECORD_DIR / "fast_repaired.json"
    if not path.exists():  # pragma: no cover - the repaired run is committed
        return {"available": False}
    fast = json.loads(path.read_text(encoding="utf-8"))["books"]
    rows: dict[str, Any] = {"available": True}
    for label, fast_name, slow_name in (
        ("rate_state", "A_yield_repricing", "B_slow_rate_state"),
        ("fx_control", "B_fx_momentum", "C_fx_price_control"),
        ("primary_residual", "C_residualised", "D_residualised"),
    ):
        old = fast[fast_name]["summary"]
        new = books[slow_name]["summary"]
        rows[label] = {
            field: {
                "fast_5d": old[field],
                "slow_20d": new[field],
                "change": round(new[field] - old[field], 5),
            }
            for field in (
                "gross_sharpe",
                "net_sharpe",
                "gross_annual_return",
                "annual_cost",
                "turnover_round_trips_per_year_per_unit_gross",
            )
        }
    rows["reading"] = (
        "on the primary test the gross did not rise — it fell slightly — and the whole of the net "
        "improvement is the cost saved by turning over less. The rate-state book's gross did rise, "
        "which is the A-to-B leg of the pre-registered diagnostic and a different claim"
    )
    return rows


def _screen(
    books: dict[str, Any],
    drops: dict[str, float],
    decomposition: dict[str, Any],
    capacity: dict[str, Any],
) -> dict[str, Any]:
    """The frozen screen, applied as written.

    The last condition is the frozen predicate itself — whether 5% annual net is
    reachable at a target volatility whose gap stress does not force a loss-cut —
    which is `risk.leverage_for_return` at a 5% target, not the gap stress measured
    at the book's declared 10% target. The two disagree whenever the book's net
    Sharpe is below 0.5, which is exactly the region this screen exists to catch.
    """
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
        #: the label is built from the frozen multiples, so changing them cannot leave a
        #: record whose condition reads as the pre-registered one
        "net Sharpe stays positive at "
        + " and ".join(f"{m:g}x" for m in COST_STRESSES)
        + " cost": all(value > 0 for value in books["D_residualised"]["cost_stress"].values()),
        "5% annual net is reachable inside the gap stress": bool(capacity["0.05"]["reachable"]),
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
        "failing_conditions": sorted(name for name, value in conditions.items() if not value),
        "primary_net_sharpe": net,
        #: declared in the frozen screen and evaluated here rather than left unrecorded
        "strong": bool(net >= 0.5),
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
