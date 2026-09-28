# ruff: noqa: E501 -- execution prose
"""1 回だけの実行で出す数字（metric・null・LOO・分解・判定・capacity）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

primary は **composite の judged net（central cell）と TC-net** だけ。carry 単独・momentum 単独は診断で、
判定には入らない（`prereg.RESEARCH_VERDICT`）。
"""

from __future__ import annotations

import math
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.classical_premia import book, prereg

TRADING_DAYS: Final[float] = book.TRADING_DAYS
BASES: Final[tuple[str, ...]] = tuple(prereg.FINANCING["rate_bases"])
PRIMARY_BASIS: Final[str] = "policy_contemporaneous"
MARKUPS: Final[tuple[float, ...]] = tuple(prereg.FINANCING["markup_band"])
CENTRAL: Final[float] = float(prereg.FINANCING["central_markup"])
ADVERSE: Final[float] = float(prereg.FINANCING["adverse_markup"])


def sharpe(series: pd.Series) -> float:
    sd = float(series.std(ddof=0))
    return float(series.mean() / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")


def annual(series: pd.Series) -> float:
    return float(series.sum() / (len(series) / TRADING_DAYS))


def _r(value: float, digits: int = 5) -> float | None:
    return round(float(value), digits) if value is not None and np.isfinite(value) else None


# ----------------------------------------------------------------------
# metric
# ----------------------------------------------------------------------
def line_metrics(net: pd.Series) -> dict[str, Any]:
    years = len(net) / TRADING_DAYS
    equity = net.cumsum()
    drawdown = equity - equity.cummax()
    yearly = net.groupby(net.index.year).sum()
    total = float(net.sum())
    ordered = net.sort_values(ascending=False)

    def share(n: int) -> float | None:
        return _r(float(ordered.head(n).sum()) / total, 4) if total != 0 else None

    return {
        "annual_return": _r(total / years),
        "sharpe": _r(sharpe(net), 4),
        "realized_vol": _r(float(net.std(ddof=0)) * math.sqrt(TRADING_DAYS)),
        "max_drawdown": _r(float(drawdown.min())),
        "positive_calendar_years": f"{int((yearly > 0).sum())}/{len(yearly)}",
        "positive_calendar_year_share": _r(float((yearly > 0).mean()), 4),
        "calendar_year_returns": {str(k): _r(v) for k, v in yearly.items()},
        "top_1_day_contribution": share(1),
        "top_5_day_contribution": share(5),
        "top_10_day_contribution": share(10),
    }


def monthly_persistence(frame: pd.DataFrame) -> float:
    values = frame.to_numpy(dtype=float)
    a, b = values[:-1].ravel(), values[1:].ravel()
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def effective_n(composite_targets: pd.DataFrame) -> dict[str, Any]:
    """月次 composite の target weight（x / Σ|x|）の lag-1 自己相関から N(1−ρ)/(1+ρ)。"""
    gross = composite_targets.abs().sum(axis=1).replace(0.0, np.nan)
    normalized = composite_targets.div(gross, axis=0).fillna(0.0)
    rho = monthly_persistence(normalized)
    months = len(normalized)
    value = months * (1 - rho) / (1 + rho) if np.isfinite(rho) and rho < 1 else 1.0
    return {"months": months, "lag1_rho": _r(rho, 4), "effective_n": _r(value, 2)}


def full_metrics(frame: pd.DataFrame, targets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    years = len(frame) / TRADING_DAYS
    tc = book.tc_net(frame)
    central = book.judged_net(frame, PRIMARY_BASIS, CENTRAL)
    gross_economic = frame["spot"] + frame[f"carry_{PRIMARY_BASIS}"]
    cells = {}
    for basis in BASES:
        for markup in MARKUPS:
            series = book.judged_net(frame, basis, markup)
            cells[f"{basis}|{markup:.4f}"] = {
                "annual": _r(annual(series)),
                "sharpe": _r(sharpe(series), 4),
            }
    by_currency = book.judged_by_currency(frame, PRIMARY_BASIS, CENTRAL).sum() / years
    gross_mean = float(frame["currency_gross"].mean())
    return {
        "days": len(frame),
        "years": _r(years, 3),
        "gross_spot": {"annual": _r(annual(frame["spot"])), "sharpe": _r(sharpe(frame["spot"]), 4)},
        "gross_economic_spot_plus_carry": {
            "annual": _r(annual(gross_economic)),
            "sharpe": _r(sharpe(gross_economic), 4),
        },
        "tc_net": {"name": "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING", **line_metrics(tc)},
        "judged_net_central": {"cell": prereg.FINANCING["central_cell"], **line_metrics(central)},
        "judged_net_cells": cells,
        "judged_sign_consistent_across_cells": len({_num(v["annual"]) > 0 for v in cells.values()})
        == 1,
        "annual_transaction_cost": _r(annual(frame["transaction_cost"])),
        "annual_carry": {basis: _r(annual(frame[f"carry_{basis}"])) for basis in BASES},
        "annual_markup_central": _r(annual(book.markup_charge(frame, CENTRAL))),
        "annual_pair_notional_years": _r(annual(frame["pair_notional_years"]), 4),
        "turnover_round_trips_per_year": _r(float(frame["one_way_traded"].sum()) / 2.0 / years, 3),
        "turnover_per_unit_gross": _r(
            float(frame["one_way_traded"].sum()) / 2.0 / years / max(gross_mean, 1e-12), 3
        ),
        "mean_currency_gross": _r(gross_mean, 4),
        "months_at_gross_cap": int(targets["capped"]["capped"].sum()),
        "currency_contribution_judged_central_annual": {
            c: _r(float(v)) for c, v in by_currency.items()
        },
        "currencies_positive_judged_central": int((by_currency > 0).sum()),
        "full_retail_net": prereg.FINANCING["full_retail_net"],
    }


def family_contribution(frame: pd.DataFrame, composite_annual: float) -> dict[str, Any]:
    judged = book.judged_by_family(frame, PRIMARY_BASIS, CENTRAL)
    tc = book.tc_net_by_family(frame)
    years = len(frame) / TRADING_DAYS
    out: dict[str, Any] = {
        "attribution": "spot と carry は線形に厳密、transaction cost は |Δx_f|、markup は外国脚の |x_f| の比で按分"
    }
    for family in book.FAMILIES:
        annual_judged = float(judged[family].sum()) / years
        out[family] = {
            "judged_central_annual": _r(annual_judged),
            "tc_net_annual": _r(float(tc[family].sum()) / years),
            "spot_annual": _r(float(frame[f"spot__{family}"].sum()) / years),
            "carry_annual": _r(float(frame[f"carry_{PRIMARY_BASIS}__{family}"].sum()) / years),
            "share_of_composite_judged": _r(annual_judged / composite_annual, 4)
            if composite_annual != 0
            else None,
            #: ex-ante の risk contribution は構成上ちょうど 50 / 50。ここは実現した売買と保有の比（Role 1 N5）
            "mean_traded_share": _r(
                float(frame.loc[frame["is_decision_day"], f"cost_share__{family}"].mean()),
                4,
            ),
            "mean_foreign_held_share": _r(float(frame[f"markup_share__{family}"].mean()), 4),
            "calendar_year_judged": {
                str(k): _r(v) for k, v in judged[family].groupby(judged.index.year).sum().items()
            },
        }
    corr = float(judged["carry"].corr(judged["momentum"]))
    out["daily_correlation_carry_vs_momentum_judged"] = _r(corr, 4)
    return out


# ----------------------------------------------------------------------
# null
# ----------------------------------------------------------------------
def _span_scores(inputs: book.Inputs, scores: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: frame.reindex(inputs.span) for name, frame in scores.items()}


def shifted_scores(span_scores: dict[str, pd.DataFrame], k: int) -> dict[str, pd.DataFrame]:
    """**同じ k 行**だけ両 family を巡回させる（行の並びは保つ）。"""
    return {
        name: pd.DataFrame(
            np.roll(frame.to_numpy(), k, axis=0), index=frame.index, columns=frame.columns
        )
        for name, frame in span_scores.items()
    }


def permuted_scores(
    span_scores: dict[str, pd.DataFrame], permutation: tuple[int, ...]
) -> dict[str, pd.DataFrame]:
    """**同じ置換 π を両 family に全期間で**当てる: 通貨 i に通貨 π(i) の score を渡す。"""
    order = list(permutation)
    return {
        name: pd.DataFrame(frame.to_numpy()[:, order], index=frame.index, columns=frame.columns)
        for name, frame in span_scores.items()
    }


def null_shifts(n_rows: int) -> list[int]:
    spec = prereg.NULL["joint_circular_shift"]
    rng = np.random.default_rng(int(spec["seed"]))
    low, high = 252, n_rows - 252
    if high <= low:
        raise ValueError("span が短すぎて null の shift を取れない")
    return [int(v) for v in rng.integers(low, high + 1, size=int(spec["draws"]))]


def null_permutations(n_currencies: int = len(prereg.UNIVERSE)) -> list[tuple[int, ...]]:
    spec = prereg.NULL["currency_label_permutation"]
    rng = np.random.default_rng(int(spec["seed"]))
    identity = tuple(range(n_currencies))
    out: list[tuple[int, ...]] = []
    while len(out) < int(spec["draws"]):
        drawn = tuple(int(v) for v in rng.permutation(n_currencies))
        if drawn != identity:
            out.append(drawn)
    return out


def _transform(span_scores, kind: str, draw) -> dict[str, pd.DataFrame]:
    if kind == "currency_label_permutation":
        return permuted_scores(span_scores, draw)
    if kind == "joint_circular_shift":
        return shifted_scores(span_scores, draw)
    raise ValueError(kind)


def _draw_chunk(job) -> list[tuple[float, float]]:
    inputs, span_scores, cov, kind, draws = job
    out = []
    for draw in draws:
        frame = book.run(inputs, _transform(span_scores, kind, draw), cov=cov)
        out.append(
            (sharpe(book.judged_net(frame, PRIMARY_BASIS, CENTRAL)), sharpe(book.tc_net(frame)))
        )
    return out


def null_diagnostic(
    inputs, scores, observed: dict[str, float], kind: str, *, workers: int = 1
) -> dict[str, Any]:
    span_scores = _span_scores(inputs, scores)
    cov = book.covariances(inputs.returns, inputs.decision_days, list(prereg.UNIVERSE))
    if kind == "currency_label_permutation":
        draws: list = null_permutations()
        described: dict[str, Any] = {"distinct_permutations": len(set(draws))}
    else:
        draws = null_shifts(len(inputs.span))
        described = {
            "shift_range": [252, len(inputs.span) - 252],
            "distinct_shifts": len(set(draws)),
        }
    if workers <= 1:
        drawn = _draw_chunk((inputs, span_scores, cov, kind, draws))
    else:
        from concurrent.futures import ProcessPoolExecutor

        size = max(1, -(-len(draws) // workers))
        jobs = [
            (inputs, span_scores, cov, kind, draws[i : i + size])
            for i in range(0, len(draws), size)
        ]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            drawn = [v for chunk in pool.map(_draw_chunk, jobs) for v in chunk]
    out: dict[str, Any] = {
        "kind": kind,
        "role": "PRIMARY" if kind == prereg.NULL["primary"] else "SECONDARY_REPORTED_ONLY",
        "draws": len(draws),
        "seed": int(prereg.NULL[kind]["seed"]),
        **described,
        "finite_draws": int(sum(1 for d in drawn if np.isfinite(d[0]))),
    }
    for i, name in enumerate(("judged_net_central", "tc_net")):
        array = np.array([d[i] for d in drawn if np.isfinite(d[i])])
        value = observed[name]
        out[name] = {
            "observed_sharpe": _r(value, 4),
            "p_value": _r(float(int((array >= value).sum()) + 1) / float(len(array) + 1), 4),
            "observed_percentile": _r(float((array < value).mean()), 4),
            "null_p05": _r(float(np.percentile(array, 5)), 4),
            "null_p50": _r(float(np.percentile(array, 50)), 4),
            "null_p95": _r(float(np.percentile(array, 95)), 4),
            "null_mean": _r(float(array.mean()), 4),
            "null_positive_share": _r(float((array > 0).mean()), 4),
        }
    out["primary"] = "judged_net_central"
    return out


# ----------------------------------------------------------------------
# LOO・cost stress・診断 book
# ----------------------------------------------------------------------
def leave_one_out(inputs, scores) -> dict[str, Any]:
    out = {}
    for drop in prereg.UNIVERSE:
        universe = tuple(c for c in prereg.UNIVERSE if c != drop)
        frame = book.run(inputs, scores, universe=universe)
        central = book.judged_net(frame, PRIMARY_BASIS, CENTRAL)
        out[drop] = {
            "judged_central_annual": _r(annual(central)),
            "judged_central_sharpe": _r(sharpe(central), 4),
            "tc_net_annual": _r(annual(book.tc_net(frame))),
            "tc_net_sharpe": _r(sharpe(book.tc_net(frame)), 4),
        }
    return out


def cost_stress(inputs, scores, cov) -> dict[str, Any]:
    out = {}
    for multiple in prereg.COST["stress_multiples"]:
        frame = book.run(inputs, scores, cost_multiple=float(multiple), cov=cov)
        out[f"cost_x{multiple}"] = {
            "tc_net_annual": _r(annual(book.tc_net(frame))),
            "tc_net_sharpe": _r(sharpe(book.tc_net(frame)), 4),
            "judged_central_annual": _r(annual(book.judged_net(frame, PRIMARY_BASIS, CENTRAL))),
            "judged_central_sharpe": _r(sharpe(book.judged_net(frame, PRIMARY_BASIS, CENTRAL)), 4),
            "judged_adverse_by_basis_sharpe": {
                basis: _r(sharpe(book.judged_net(frame, basis, ADVERSE)), 4) for basis in BASES
            },
        }
    return out


def single_family(inputs, scores, family: str, cov) -> dict[str, Any]:
    """**診断だけ**。同じ vol target・cost・financing で family 1 本の book。"""
    frame = book.run(inputs, scores, families=(family,), cov=cov)
    target = book.targets(inputs, scores, families=(family,), cov=cov)
    tc = book.tc_net(frame)
    central = book.judged_net(frame, PRIMARY_BASIS, CENTRAL)
    weights = target[family]
    gross = weights.abs().sum(axis=1).replace(0.0, np.nan)
    return {
        "diagnostic_only": True,
        "gross_spot_sharpe": _r(sharpe(frame["spot"]), 4),
        "tc_net": {"annual": _r(annual(tc)), "sharpe": _r(sharpe(tc), 4)},
        "judged_central": {"annual": _r(annual(central)), "sharpe": _r(sharpe(central), 4)},
        "annual_carry_policy": _r(annual(frame[f"carry_{PRIMARY_BASIS}"])),
        "annual_transaction_cost": _r(annual(frame["transaction_cost"])),
        "max_drawdown_judged": line_metrics(central)["max_drawdown"],
        "monthly_weight_persistence": _r(
            monthly_persistence(weights.div(gross, axis=0).fillna(0.0)), 4
        ),
    }


# ----------------------------------------------------------------------
# 判定（None / NaN は「満たさない」として扱う。例外で 1 回きりの実行を失わない、Role 2 N-6）
# ----------------------------------------------------------------------
def _num(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out


def research_verdict(result: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    tc = _num(m["tc_net"]["annual_return"])
    judged = _num(m["judged_net_central"]["annual_return"])
    spot = _num(m["gross_spot"]["annual"])
    pct = _num(result["null"]["judged_net_central"]["observed_percentile"])
    fam = result["family_contribution"]
    loo = result["leave_one_out"]
    loo_positive = sum(1 for v in loo.values() if _num(v["judged_central_annual"]) > 0)
    reasons = []
    not_positive = not (tc > 0 and judged > 0)
    if not_positive:
        reasons.append("TC-net ≤ 0 または judged ≤ 0（または非有限）")
    if not pct >= 0.80:
        reasons.append(f"primary null percentile {pct} < 0.80")
    extreme = [
        f
        for f in book.FAMILIES
        if judged > 0 and not _num(fam[f]["judged_central_annual"]) >= -0.5 * judged
    ]
    if extreme:
        reasons.append(f"family が極端に逆向き: {extreme}")
    if loo_positive < 6:
        reasons.append(f"LOO で正の universe が {loo_positive}/8")
    if not_positive:
        failure = (
            "CARRY_ONLY_POSITIVE_SPOT_NET_NOT_POSITIVE"
            if judged > 0
            else "SIGNAL_FAILURE"
            if not spot > 0
            else "COST_FAILURE"
            if not tc > 0
            else "FINANCING_FAILURE"
        )
    else:
        failure = None
    status = (
        "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        if reasons
        else "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"
    )
    caveats = []
    if judged > 0:
        shares = [_num(fam[f]["share_of_composite_judged"]) for f in book.FAMILIES]
        if any(s >= 0.80 for s in shares):
            caveats.append("FAMILY_CONCENTRATION_CAVEAT")
    if any(not _num(v["judged_central_annual"]) > 0 for v in loo.values()):
        caveats.append("CURRENCY_CONCENTRATION_CAVEAT")
    years = _num(m["years"])
    s = _num(m["judged_net_central"]["sharpe"])
    gap_large = not (
        s + 1.0 / math.sqrt(years)
        >= float(prereg.BUSINESS_GAP["required_sharpe_5pct_at_10pct_vol"])
    )
    return {
        "status": status,
        "reasons": reasons,
        "failure_class": failure,
        "caveats": caveats,
        "loo_positive_universes": f"{loo_positive}/8",
        "required_sharpe_gap_large": gap_large,
        "required_risk": business_risk(result),
        "never": "CONFIRMED とは呼ばない。fresh / forward へ進まない",
    }


def business_risk(result: dict[str, Any]) -> dict[str, Any]:
    """REQUIRED_RISK_INCONSISTENT（Role 1 R4）。"""
    m = result["metrics"]["judged_net_central"]
    s = _num(m["sharpe"])
    vol = _num(m["realized_vol"])
    dd = _num(m["max_drawdown"])
    required_vol = 0.05 / s if s > 0 else float("nan")
    dd_at_required = dd * required_vol / vol if s > 0 and vol > 0 else float("nan")
    spec = prereg.BUSINESS_RISK
    inconsistent = not (
        s > 0
        and required_vol <= float(spec["max_required_vol_for_5pct"])
        and dd_at_required >= float(spec["max_drawdown_at_required_vol"])
    )
    return {
        "required_vol_for_5pct": _r(required_vol, 4),
        "max_drawdown_scaled_to_required_vol": _r(dd_at_required, 4),
        "REQUIRED_RISK_INCONSISTENT": inconsistent,
    }


def forward_eligibility(result: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    """F2〜F5・F7 は数値で機械的に判定する。F1・F6・F8 は post-run review と report で確定する（ここでは PENDING）。"""
    m = result["metrics"]
    null = result["null"]["judged_net_central"]
    cells = m["judged_net_cells"]
    f3 = all(_num(cells[f"{b}|{ADVERSE:.4f}"]["annual"]) > 0 for b in BASES)
    f2 = _num(null["observed_percentile"]) >= 0.95 or _num(null["p_value"]) <= 0.05
    n_eff = _num(result["effective_n"]["effective_n"])
    f5 = (
        "CURRENCY_CONCENTRATION_CAVEAT" not in verdict["caveats"]
        and _num(m["judged_net_central"]["top_10_day_contribution"]) < 1
        and _num(m["judged_net_central"]["positive_calendar_year_share"]) >= 0.5
    )
    s = _num(m["judged_net_central"]["sharpe"])
    fresh_years = 4.9
    se = 1.0 / math.sqrt(fresh_years)
    z = s / se if np.isfinite(s) else float("nan")
    power = 0.5 * math.erfc(-(z - 1.645) / math.sqrt(2)) if np.isfinite(z) else float("nan")
    p_nonpositive = 0.5 * math.erfc(z / math.sqrt(2)) if np.isfinite(z) else float("nan")
    f7 = bool(np.isfinite(power) and power >= 0.20 and p_nonpositive >= 0.10)
    return {
        "F1": "PENDING_POST_RUN_REVIEW",
        "F2": "PASS" if f2 else "FAIL",
        "F3": "PASS" if f3 else "FAIL",
        "F4": "PASS" if n_eff >= 10 else "FAIL",
        "F4_note": prereg.EFFECTIVE_N["f4_known_before_run"],
        "F5": "PASS" if f5 else "FAIL",
        "F6": "PENDING_REPORT",
        "F7": "PASS" if f7 else "FAIL",
        "F7_detail": {
            "fresh_years": fresh_years,
            "one_sided_power_at_observed": _r(power, 4),
            "p_fresh_net_nonpositive": _r(p_nonpositive, 4),
        },
        "F8": "PENDING_REPORT",
    }


def disposition(verdict: dict[str, Any], eligibility: dict[str, Any]) -> dict[str, Any]:
    """`prereg.DISPOSITION` を機械的に当てる。F1・F6・F8 が PENDING の間は A を『条件付き』とする。"""
    positive = verdict["status"] == "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"
    risk_bad = bool(verdict["required_risk"]["REQUIRED_RISK_INCONSISTENT"])
    numeric = all(eligibility[k] == "PASS" for k in ("F2", "F3", "F4", "F5", "F7"))
    pending = [k for k in ("F1", "F6", "F8") if eligibility[k] != "PASS"]
    if positive and not verdict["required_sharpe_gap_large"] and not risk_bad:
        fallback = "B. POSITIVE_EXPLORATORY_BUT_NOT_CONFIRMATION_READY"
    else:
        fallback = "C. LONG_TERM_HOLD / NO_FURTHER_SEEN_DATA_ALPHA_SEARCH"
    if positive and numeric and not risk_bad:
        #: A は F1〜F8 すべての PASS が要る。F1・F6・F8 は report で確定するので条件付き（re-audit NEW-5）
        label = "A_CONDITIONAL_PENDING_F1_F6_F8" if pending else "A. FRESH_CONFIRMATION_PROPOSAL"
    else:
        label = fallback
    note = "FX_HAS_NO_EDGE ではない" if label.startswith("C.") else ""
    return {
        "preliminary": label,
        "fallback_if_a_conditions_fail": fallback,
        "pending": pending,
        "note": note,
        "invalid_overrides": "post-run review の BLOCKER は INVALID に上書きする",
    }


def capacity(result: dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    m = result["metrics"]["judged_net_central"]
    ann = _num(m["annual_return"])
    if not ann > 0:
        return {
            "reachable": False,
            "why": "judged net（central）年率 ≤ 0 なので capacity を出さない（leverage で救わない）",
        }
    vol = _num(m["realized_vol"])
    s = _num(m["sharpe"])
    dd = _num(m["max_drawdown"])
    gross = float(frame["currency_gross"].mean())
    foreign = [c for c in prereg.UNIVERSE if c != prereg.NUMERAIRE]
    pair_notional = float(frame[[f"x_{c}" for c in foreign]].abs().sum(axis=1).mean())
    largest = float(frame[[f"x_{c}" for c in prereg.UNIVERSE]].abs().max(axis=1).max())
    margin = float(prereg.CAPACITY["margin_rate"])
    out: dict[str, Any] = {"reachable": True, "judged_central_sharpe": _r(s, 4), "scenarios": {}}
    for target in prereg.CAPACITY["target_vols"]:
        scale = target / vol
        out["scenarios"][f"vol_{int(round(target * 100))}%"] = {
            "annual_net": _r(ann * scale),
            "risk_leverage_vs_run": _r(scale, 3),
            "mean_currency_gross": _r(gross * scale, 3),
            "mean_pair_notional": _r(pair_notional * scale, 3),
            "margin_usage_share_of_equity": _r(pair_notional * scale * margin, 4),
            "historical_max_drawdown": _r(dd * scale),
            "gap_stress_one_day_loss": _r(largest * scale * 0.20),
        }
    for goal in (0.05, 0.10):
        out[f"required_vol_for_{int(goal * 100)}pct"] = _r(goal / s, 4) if s > 0 else None
    out["never"] = prereg.CAPACITY["never"]
    return out


# ----------------------------------------------------------------------
# 全体: compute（重い計算、生の結果）と judge（判定）を分ける
# ----------------------------------------------------------------------
def compute(
    inputs: book.Inputs, scores: dict[str, pd.DataFrame], *, workers: int = 1
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, pd.DataFrame]]:
    cov = book.covariances(inputs.returns, inputs.decision_days, list(prereg.UNIVERSE))
    targets = book.targets(inputs, scores, cov=cov)
    frame = book.run(inputs, scores, cov=cov)
    metrics = full_metrics(frame, targets)
    observed = {
        "judged_net_central": sharpe(book.judged_net(frame, PRIMARY_BASIS, CENTRAL)),
        "tc_net": sharpe(book.tc_net(frame)),
    }
    per_family_n = {}
    for f in book.FAMILIES:
        per_family_n[f] = effective_n(targets[f])
    raw: dict[str, Any] = {
        "metrics": metrics,
        "effective_n": effective_n(targets["composite"]),
        "effective_n_per_family": per_family_n,
        "signal_persistence_monthly": {f: per_family_n[f]["lag1_rho"] for f in book.FAMILIES},
        "family_contribution": family_contribution(
            frame, _num(metrics["judged_net_central"]["annual_return"])
        ),
        "leave_one_out": leave_one_out(inputs, scores),
        "cost_stress": cost_stress(inputs, scores, cov),
        "diagnostic_single_family": {
            f: single_family(inputs, scores, f, cov) for f in book.FAMILIES
        },
    }
    nulls = {
        kind: null_diagnostic(inputs, scores, observed, kind, workers=workers)
        for kind in ("currency_label_permutation", "joint_circular_shift")
    }
    raw["null_all"] = nulls
    raw["null"] = nulls[prereg.NULL["primary"]]
    return raw, frame, targets


def judge(raw: dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    verdict = research_verdict(raw)
    eligibility = forward_eligibility(raw, verdict)
    return {
        "research_verdict": verdict,
        "forward_eligibility": eligibility,
        "disposition": disposition(verdict, eligibility),
        "capacity": capacity(raw, frame),
    }


__all__ = [
    "business_risk",
    "compute",
    "disposition",
    "forward_eligibility",
    "judge",
    "research_verdict",
    "sharpe",
    "annual",
]
