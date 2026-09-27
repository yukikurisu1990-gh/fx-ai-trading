# ruff: noqa: E501 -- book prose
"""**USD-factor book の修正**（2026-09-24 第 3 裁定 §14–§18）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

mechanism redesign の M15 / M16 は「USD 対 7 通貨 basket」として凍結されたが、
`construction.band_rebalance` は通貨ごとに band を当てるので、target が USD ±0.5・外国 ∓0.071 の book では
外国の脚（0.071 < band 0.10）が売買されず、同符号の breach の counter-leg として同値の中から
アルファベット順の先頭（AUD → CAD → CHF）が選ばれた。実際の book は USD 対 AUD / CAD / CHF だった。

**修正は実装だけ**（§18）。band 幅（0.10）・rebalance の頻度（毎日の判定）・leverage・signal・符号・
basket の構成は変えない。変えるのは **band を当てる単位**である:

- `factor_rebalance`: basket 全体を 1 単位として扱う。どれかの脚の gap が band を超えたら
  **全脚を同時に target へ動かし**、超えなければ全脚を据え置く。USD factor の target は符号でしか
  変わらないので、実際の売買は符号の反転と vol targeting の leverage 変更だけになる。
- `run_book` は `construction.run_book` の本体をそのまま写し、rebalance 関数だけを引数にした。
  既定値（`construction.band_rebalance`）では `construction.run_book` と**完全に同じ出力**になることを
  test で固定する（共有の construction.py は書き換えない — 実行済みの凍結の閉包に入っているため）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from scripts.research.continuous_portfolio import construction


def factor_rebalance(target: np.ndarray, held: np.ndarray, band: float) -> np.ndarray:
    """basket を 1 単位として rebalance する。**通貨を構造的に落とさない。**"""
    if band <= 0 or float(np.max(np.abs(target - held))) > band:
        return target.copy()
    return held.copy()


def run_book(
    config: construction.BookConfig,
    mu: pd.DataFrame,
    excess: pd.DataFrame,
    days_per_year: float,
    *,
    rebalance: Callable[[np.ndarray, np.ndarray, float], np.ndarray] = construction.band_rebalance,
) -> dict[str, Any]:
    """Run one book over the days `mu` covers.

    `mu` is `day x currency`, one row per decision day. `excess` is the full
    daily currency excess-return panel; every quantity used on day `t` is taken
    from rows `<= t`, and the P&L of the exposure chosen on day `t` is the
    return of day `t+1`.
    """
    currencies = list(construction.CURRENCIES)
    mu = mu[currencies]
    returns = excess[currencies]
    index = returns.index
    positions = {day: index.get_loc(day) for day in mu.index}
    locations = np.array(list(positions.values()), dtype=int)
    if len(locations) and not np.array_equal(
        locations, np.arange(locations[0], locations[0] + len(locations))
    ):
        raise ValueError(
            "mu must cover a contiguous run of the return calendar: a missing decision "
            "day would silently drop the held book's P&L"
        )
    pair_map = construction.split_map()
    mapping = construction.MAPPINGS[config.mapping]

    targeter = (
        construction.VolTargeter(config.vol_target, config.max_leverage, config.leverage_hysteresis)
        if config.vol_target is not None
        else None
    )
    held = np.zeros(len(currencies))
    exposure_prev = np.zeros(len(currencies))
    equity = 0.0
    peak = 0.0
    governor_on = False

    rows: list[dict[str, Any]] = []
    for day in mu.index:
        loc = positions[day]
        if loc + 1 >= len(index):
            break
        history = returns.iloc[: loc + 1].to_numpy()
        sigma = np.nanstd(history[-config.sigma_window :], axis=0, ddof=0)
        raw = mapping(mu.loc[day].to_numpy(dtype=float), sigma)
        factor = construction.leading_factor(history[-config.factor_window :])
        scores = construction.neutralize(raw, factor) if config.neutralize_leading_factor else raw
        target = construction.capped_weights(scores, config.weight_cap)
        held = rebalance(target, held, config.band)

        leverage = 1.0
        uncapped = float("nan")
        at_cap = False
        ex_ante = float("nan")
        if targeter is not None:
            window = history[-config.vol_window :]
            cov = np.cov(window, rowvar=False)
            ex_ante = float(np.sqrt(max(held @ cov @ held, 0.0) * days_per_year))
            leverage = targeter.update(ex_ante)
            uncapped = targeter.uncapped
            #: the cap binds when the target *asks* for it: the held leverage
            #: can sit just below the cap for months under hysteresis
            at_cap = bool(np.isfinite(uncapped) and uncapped >= config.max_leverage)
        scale = config.governor_scale if (config.drawdown_governor and governor_on) else 1.0
        exposure = held * leverage * scale

        delta = exposure - exposure_prev
        cost = construction.charged_cost(delta, config.cost_multiple)
        faithful = construction.implementation_cost(delta, pair_map)
        next_day = index[loc + 1]
        realised = returns.iloc[loc + 1].to_numpy()
        contributions = exposure * realised
        gross = float(contributions.sum())
        net = gross - cost
        exposure_norm = float(np.linalg.norm(exposure))
        factor_loading = float(exposure @ factor)

        equity += net
        peak = max(peak, equity)
        drawdown = equity - peak
        if config.drawdown_governor:
            if not governor_on and drawdown < -config.governor_trigger:
                governor_on = True
            elif governor_on and drawdown > -config.governor_release:
                governor_on = False

        rows.append(
            {
                "decision_day": day,
                "pnl_day": next_day,
                "gross": gross,
                "cost": cost,
                "implementation_cost": faithful,
                "net": net,
                "currency_gross": float(np.abs(exposure).sum()),
                "pair_gross": float(np.abs(pair_map @ exposure).sum()),
                "one_way_traded": float(np.abs(delta).sum()),
                "leverage": leverage * scale,
                "uncapped_leverage": uncapped,
                "at_leverage_cap": at_cap,
                "held_max_weight": float(np.abs(held).max()),
                "held_gross": float(np.abs(held).sum()),
                "factor_abs_cosine": abs(factor_loading) / exposure_norm
                if exposure_norm > 0
                else float("nan"),
                "factor_pnl": factor_loading * float(factor @ realised),
                "ex_ante_vol": ex_ante,
                "traded": bool(np.abs(delta).sum() > 0),
                "raw_target_corr": construction._corr(raw, scores),
                **{f"x_{c}": float(v) for c, v in zip(currencies, exposure, strict=True)},
                **{f"pnl_{c}": float(v) for c, v in zip(currencies, contributions, strict=True)},
            }
        )
        exposure_prev = exposure

    frame = pd.DataFrame(rows).set_index("pnl_day")
    return {"config": config, "daily": frame}


__all__ = ["factor_rebalance", "run_book"]
