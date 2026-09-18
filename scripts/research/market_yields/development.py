"""Stage 1: the unfitted yield rule, the FX-momentum control, and the residual.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.market_yields.development

Runs exactly what `prereg.py` froze and committed before this module existed:
three books over the five decision-grade currencies, on the seen corpus, with the
yields lagged one trading day. No fitted coefficient, no ML, no search. The
result is development evidence; the screen it feeds is symmetric and exhaustive.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.continuous_portfolio import construction
from scripts.research.edge_sources import capacity, leverage
from scripts.research.market_yields import DATA_DIR, RECORD_DIR, WORKFLOW_STATUS, integrity, prereg
from scripts.research.model_learning import assert_not_protected

ROOT: Final[Path] = Path(__file__).resolve().parents[3]
BLOCKS: Final[int] = 6
#: Read from the frozen pre-registration, never written as a literal here.
LOOKBACK: Final[int] = int(prereg.PREREG["signal"]["lookback_days"])
HORIZONS: Final[tuple[int, ...]] = tuple(prereg.PREREG["targets"]["horizons_days"])

#: The book actually run, recorded in the artefact so the executed configuration can be
#: compared with the frozen one rather than taken on trust.
BOOK: Final[construction.BookConfig] = construction.BookConfig(
    name="t_r",
    mapping="linear",
    #: Neutralisation happens inside the five-currency universe (`_neutralise_within_universe`),
    #: so the layer must not neutralise again over all eight: its factor would place deliberate
    #: weight on currencies this track cannot observe. This is a deviation from "the layer,
    #: reused unchanged", and it is disclosed in the results document and in ledger H-025.
    neutralize_leading_factor=False,
    weight_cap=0.25,
    band=0.10,
    vol_target=0.10,
    max_leverage=1_000_000.0,
)


def _z(frame: pd.DataFrame) -> pd.DataFrame:
    centred = frame.sub(frame.mean(axis=1), axis=0)
    spread = frame.std(axis=1, ddof=0).replace(0.0, np.nan)
    return centred.div(spread, axis=0)


def _residualise(score: pd.DataFrame, control: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional residual of the score on the control, one day at a time."""
    out = pd.DataFrame(index=score.index, columns=score.columns, dtype=float)
    for day in score.index:
        y = score.loc[day].to_numpy(dtype=float)
        x = control.loc[day].to_numpy(dtype=float)
        ok = np.isfinite(y) & np.isfinite(x)
        if ok.sum() < 3 or float(x[ok] @ x[ok]) <= 0.0:
            continue
        beta = float(x[ok] @ y[ok]) / float(x[ok] @ x[ok])
        residual = np.full_like(y, np.nan)
        residual[ok] = y[ok] - beta * x[ok]
        out.loc[day] = residual
    return out


def _neutralise_within_universe(
    score: pd.DataFrame, excess: pd.DataFrame, window: int = 120
) -> pd.DataFrame:
    """Remove the universe's own leading factor from each day's cross-section.

    The frozen pre-registration keeps factor neutralisation, and the universe is the
    five decision-grade currencies, so the factor is theirs: neutralising against the
    eight-currency factor would put weight on the three currencies this track cannot
    trade. Only returns up to and including the decision day are used.
    """
    out = pd.DataFrame(index=score.index, columns=score.columns, dtype=float)
    returns = excess.reindex(columns=score.columns)
    for day in score.index:
        row = score.loc[day].to_numpy(dtype=float)
        if not np.all(np.isfinite(row)):
            continue
        history = returns.loc[:day].to_numpy(dtype=float)[-window:]
        factor = construction.leading_factor(history)
        out.loc[day] = construction.neutralize(row, factor)
    return out


def _expand(score: pd.DataFrame) -> pd.DataFrame:
    """The universe's scores in the execution layer's columns; others exactly zero.

    The scores are demeaned within the universe, so their sum is zero and the layer's
    own demeaning leaves the excluded currencies at zero weight.
    """
    return score.reindex(columns=list(construction.CURRENCIES)).fillna(0.0)


def _ic(score: pd.DataFrame, excess: pd.DataFrame, horizon: int) -> float:
    from scipy import stats as scipy_stats

    forward = excess.rolling(horizon).sum().shift(-horizon)
    values = []
    for day in score.index:
        if day not in forward.index:
            continue
        a = score.loc[day].to_numpy(dtype=float)
        b = forward.loc[day].to_numpy(dtype=float)
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < 3:
            continue
        values.append(float(scipy_stats.spearmanr(a[ok], b[ok]).statistic))
    return round(float(np.nanmean(values)), 4) if values else float("nan")


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    daily = result["daily"]
    net = daily["net"].to_numpy(dtype=float)
    gross = daily["gross"].to_numpy(dtype=float)
    equity = np.cumsum(net)
    drawdown = np.maximum.accumulate(np.maximum(equity, 0.0)) - equity
    top = np.sort(net)[::-1]
    total = float(net.sum())
    return {
        "gross_sharpe": round(float(np.mean(gross) / np.std(gross, ddof=0) * np.sqrt(252)), 4),
        "net_sharpe": round(float(np.mean(net) / np.std(net, ddof=0) * np.sqrt(252)), 4),
        "gross_annual_return": round(float(np.mean(gross) * 252), 5),
        "net_annual_return": round(float(np.mean(net) * 252), 5),
        "realized_annual_vol": round(float(np.std(net, ddof=0) * np.sqrt(252)), 5),
        "annual_cost": round(float(daily["cost"].mean() * 252), 5),
        "turnover_round_trips_per_year_per_unit_gross": round(
            float(daily["one_way_traded"].sum() / 2.0 / len(daily) * 252.0)
            / float(daily["currency_gross"].mean()),
            3,
        ),
        "mean_currency_gross": round(float(daily["currency_gross"].mean()), 4),
        "mean_leverage": round(float(daily["leverage"].mean()), 4),
        "mean_uncapped_leverage": round(float(daily["uncapped_leverage"].mean()), 4),
        "p95_uncapped_leverage": round(float(daily["uncapped_leverage"].quantile(0.95)), 4),
        "mean_held_max_weight": round(float(daily["held_max_weight"].mean()), 4),
        "share_days_traded": round(float(daily["traded"].mean()), 4),
        "max_drawdown": round(-float(drawdown.max()), 5),
        "top_1_day_share_of_net": round(float(top[0] / total), 4) if total else None,
        "top_5_day_share_of_net": round(float(top[:5].sum() / total), 4) if total else None,
        "top_10_day_share_of_net": round(float(top[:10].sum() / total), 4) if total else None,
        "net_without_top_5_days": round(total - float(top[:5].sum()), 5),
        "worst_day": round(float(np.sort(net)[0]), 5),
        "days": int(len(daily)),
    }


def _blocks(result: dict[str, Any]) -> list[dict[str, Any]]:
    daily = result["daily"]
    edges = np.linspace(0, len(daily), BLOCKS + 1).astype(int)
    rows = []
    for i in range(BLOCKS):
        chunk = daily.iloc[edges[i] : edges[i + 1]]
        net = chunk["net"].to_numpy(dtype=float)
        rows.append(
            {
                "block": i + 1,
                "start": str(chunk.index[0].date()),
                "end": str(chunk.index[-1].date()),
                "days": int(len(chunk)),
                "net_sharpe": round(float(np.mean(net) / np.std(net, ddof=0) * np.sqrt(252)), 4)
                if np.std(net, ddof=0) > 0
                else None,
                "net_return": round(float(net.sum()), 5),
            }
        )
    return rows


def _outside_universe(result: dict[str, Any], universe: list[str]) -> dict[str, Any]:
    """Exposure the reused layer put on currencies this track cannot see.

    `band_rebalance` trades "the currency with the largest opposite gap" as the
    counter-leg when every breaching gap shares a sign. With a universe smaller than
    the layer's cross-section, a currency outside it has gap zero and can win that
    comparison, so the book takes a small position in a currency whose yield is not
    observed. It is a property of the reused layer, not of the signal, and it is
    measured here rather than assumed away.
    """
    daily = result["daily"]
    outside = [c for c in construction.CURRENCIES if c not in universe]
    exposure = daily[[f"x_{c}" for c in outside]].abs()
    pnl = {c: round(float(daily[f"pnl_{c}"].sum()), 5) for c in outside}
    inside_gross = daily[[f"x_{c}" for c in universe]].abs().sum(axis=1)
    return {
        "currencies": outside,
        "share_of_days_with_any_exposure": round(float((exposure.sum(axis=1) > 1e-12).mean()), 4),
        "mean_share_of_currency_gross": round(
            float((exposure.sum(axis=1) / (exposure.sum(axis=1) + inside_gross)).mean()), 4
        ),
        "cumulative_pnl": pnl,
        "cumulative_pnl_total": round(float(sum(pnl.values())), 5),
    }


def _per_currency(result: dict[str, Any]) -> dict[str, float]:
    daily = result["daily"]
    columns = [c for c in daily.columns if c.startswith("pnl_")]
    return {
        column.removeprefix("pnl_"): round(float(daily[column].sum()), 5)
        for column in columns
        if abs(float(daily[column].sum())) > 0
    }


def _ic_comparison(book: dict[str, Any], lookback: int) -> dict[str, Any]:
    """Compare like with like: the realised drag, and the IC on one day.

    The pre-run feasibility assumed a five-day half-life, so it used the band law's
    turnover for that. The book's own signal decayed faster, so the honest comparison
    uses the realised cost drag. The measured IC is on the five-day horizon, so it is
    converted to its daily equivalent under the signal's own AR(1) decay.
    """
    summary = book["summary"]
    rho = book["signal_autocorrelation_1d"]
    half_life = math.log(0.5) / math.log(rho) if 0 < rho < 1 else float("nan")
    drag = summary["gross_sharpe"] - summary["net_sharpe"]
    capture = capacity.band_law(round(max(half_life, 1.0)))["capture"]
    scale = sum(rho**k for k in range(lookback)) / math.sqrt(lookback)
    required = (0.3 + drag) / (
        capacity.TRANSFER_COEFFICIENT * capture * math.sqrt(prereg.EFFECTIVE_BREADTH * 252.0)
    )
    observed_daily = book["ic"][f"{lookback}d"] / scale
    return {
        "implied_half_life_days": round(half_life, 2),
        "realised_cost_ir_drag": round(drag, 3),
        "required_daily_ic_for_net_0_3_at_realised_turnover": round(required, 4),
        "observed_daily_equivalent_ic": round(observed_daily, 4),
        "shortfall_multiple": round(required / observed_daily, 2) if observed_daily else None,
        "caveat": (
            "the measured IC is a Spearman rank correlation while the fundamental law uses a "
            "Pearson-style IC; the comparison is indicative, and the shortfall is large enough "
            "that the distinction does not carry it"
        ),
    }


def _screen(
    books: dict[str, Any], drops: dict[str, float], gap_stress: dict[str, Any]
) -> dict[str, Any]:
    """The frozen screen, applied exactly: anything not advance is stop."""
    a = books["A_yield_repricing"]["summary"]
    b = books["B_fx_momentum"]["summary"]
    c = books["C_residualised"]["summary"]
    blocks = books["A_yield_repricing"]["blocks"]
    positive_blocks = sum(1 for row in blocks if (row["net_sharpe"] or 0) > 0)
    conditions = {
        "A gross Sharpe > 0": a["gross_sharpe"] > 0,
        "A net Sharpe >= 0.3": a["net_sharpe"] >= 0.3,
        #: the frozen text is "keeps a positive net increment over B" and nothing more;
        #: an extra "and C > 0" clause would be tightening a screen after the result
        "C keeps a positive net increment over B": c["net_sharpe"] - b["net_sharpe"] > 0,
        "the sign survives dropping any single currency": all(v > 0 for v in drops.values()),
        "a majority of the six blocks are positive": positive_blocks > len(blocks) / 2,
        #: computed from the same gap stress the record carries, never asserted. It reads the
        #: equity-proportional case, which is what #484's policy requires of an implementation;
        #: the executed layer sizes on fixed capital, where the same record says the loss-cut is
        #: reached. Both flags are reported below, and the stricter reading would only add a
        #: sixth failure to a screen that already stops.
        "10% vol is reachable inside the gap stress": not gap_stress["loss_cut_on_gap"],
    }
    advance = all(conditions.values())
    return {
        "conditions": conditions,
        "c_minus_b_net_sharpe": round(c["net_sharpe"] - b["net_sharpe"], 4),
        "gap_stress_reading": {
            "equity_proportional_loss_cut": gap_stress["loss_cut_on_gap"],
            "fixed_notional_loss_cut": gap_stress["fixed_notional_loss_cut"],
            "note": (
                "the condition is evaluated on the equity-proportional case; the executed layer "
                "sizes on fixed capital, where the loss-cut is reached"
            ),
        },
        "c_net_sharpe_still_negative": c["net_sharpe"] < 0,
        "positive_blocks": positive_blocks,
        "decision": "advance" if advance else "stop",
        "verdict": (
            "MARKET_YIELD_REPRICING_FAST_5D_MEASURE_DEVELOPMENT_CANDIDATE"
            if advance
            else "MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        ),
        "decision_grade": False,
        "note": (
            "a development screen, not decision-grade in either direction: the span separates a "
            "net Sharpe of about 1.13 at 80% power, so neither a pass nor a fail here settles "
            "whether yield repricing leads FX"
        ),
    }


def lagged_yield_panel(frames: dict[str, pd.DataFrame], days: pd.DatetimeIndex) -> pd.DataFrame:
    """Each currency's yield as it could be used, under the frozen availability rule."""
    return pd.DataFrame(
        {currency: integrity.available_from(frame, days) for currency, frame in frames.items()},
        index=days,
    )


def build_scores(
    yield_panel: pd.DataFrame, excess: pd.DataFrame, lookback: int = LOOKBACK
) -> dict[str, pd.DataFrame]:
    """The three pre-registered scores, from an already-lagged yield panel.

    `yield_panel` must come from `lagged_yield_panel`: a yield dated on the decision
    day cannot be in it, and nothing here reaches forward.
    """
    repricing = _z(yield_panel.diff(lookback))
    momentum = _z(excess.rolling(lookback).sum())
    return {
        "A_yield_repricing": repricing,
        "B_fx_momentum": momentum,
        "C_residualised": _residualise(repricing, momentum),
    }


def provenance() -> dict[str, Any]:
    """The book that ran and the one declared deviation, as the record carries them."""
    return {
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
                "leverage_hysteresis",
                "cost_multiple",
                "sigma_window",
                "factor_window",
                "vol_window",
            )
        },
        "deviations_from_the_frozen_text": {
            "factor_neutralisation_moved_into_the_universe": (
                "the frozen text reuses the layer unchanged with factor neutralisation on. The "
                "layer neutralises against the eight-currency factor, which would place "
                "deliberate weight on the three currencies this track cannot observe, so "
                "neutralisation is applied inside the five-currency universe and the layer's own "
                "flag is off. A post-freeze implementation decision that changes the result"
            ),
            "lookback_and_horizons_read_from_the_prereg": True,
        },
    }


def run() -> dict[str, Any]:
    from scripts.research.model_learning import corpus as corpus_module

    universe = list(prereg.UNIVERSE)
    panel = corpus_module.currency_panel()
    excess_all = panel["currency_excess_return"]
    days = pd.DatetimeIndex(excess_all.index)
    assert_not_protected(str(days[0].date()), str(days[-1].date()))

    frames = {
        currency: pd.read_parquet(ROOT / DATA_DIR / f"{currency.lower()}_2y.parquet")
        for currency in universe
    }
    yield_panel = lagged_yield_panel(frames, days)

    excess = excess_all[universe]
    scores = build_scores(yield_panel, excess, LOOKBACK)
    config = BOOK
    books: dict[str, Any] = {}
    for name, score in scores.items():
        usable = _neutralise_within_universe(score, excess).dropna(how="any")
        result = construction.run_book(config, _expand(usable), excess_all, days_per_year=252.0)
        books[name] = {
            "summary": _summary(result),
            "outside_universe_exposure": _outside_universe(result, universe),
            "blocks": _blocks(result),
            "per_currency_gross_pnl": _per_currency(result),
            "ic": {f"{h}d": _ic(usable, excess, h) for h in HORIZONS},
            "signal_autocorrelation_1d": round(
                float(np.nanmean([usable[c].autocorr(1) for c in universe])), 4
            ),
        }

    drops = {}
    for dropped in universe:
        kept = [c for c in universe if c != dropped]
        score = _neutralise_within_universe(
            _z(yield_panel[kept].diff(LOOKBACK)), excess_all[kept]
        ).dropna(how="any")
        result = construction.run_book(config, _expand(score), excess_all, days_per_year=252.0)
        drops[f"without_{dropped}"] = _summary(result)["net_sharpe"]

    for name, book in books.items():
        books[name]["ic_comparison"] = _ic_comparison(book, LOOKBACK)
    scale = leverage.scale(
        ROOT,
        0.10 / capacity.VOL_PER_UNIT_GROSS,
        books["A_yield_repricing"]["summary"]["net_sharpe"],
    )
    screen = _screen(books, drops, scale)
    return {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "workflow_status": WORKFLOW_STATUS,
        **provenance(),
        "prereg": prereg.PREREG,
        "feasibility_before_the_run": prereg.feasibility(),
        "universe": universe,
        "decision_days": int(len(days)),
        "span": {"first": str(days[0].date()), "last": str(days[-1].date())},
        "books": books,
        "screen": screen,
        "verdict": screen["verdict"],
        "leave_one_currency_out_net_sharpe": drops,
        "leverage_and_margin_at_10pct_vol": scale,
        "protected_spans_read": False,
    }


def main() -> int:
    record = run()
    out = ROOT / RECORD_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "development.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    for name, block in record["books"].items():
        summary = block["summary"]
        print(
            f"{name}: gross {summary['gross_sharpe']:+.3f} net {summary['net_sharpe']:+.3f} "
            f"turnover {summary['turnover_round_trips_per_year_per_unit_gross']} "
            f"IC {block['ic']}"
        )
    print("leave-one-out:", record["leave_one_currency_out_net_sharpe"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
