# ruff: noqa: E501 -- book prose
"""carry + momentum の等リスク合成 book（凍結は `prereg`）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

鎖（どの環も合成入力で test する）:

    日次 score（carry: 月末の翌日から使う政策金利、momentum: 12-1 の spot return）
      -> decision day（月初）で rank weight（Σ|w| = 1、和ゼロ）
      -> family ごとに ex-ante vol 1 へ（t−1 までの 252 営業日の共分散。t の fix は使わない）
      -> 0.5 / 0.5 で合成（2 資産の厳密な ERC）-> 10% vol へ leverage、通貨 gross 5 で cap
      -> 次の decision day まで exposure 一定
      -> P&L(t+1) = x_t · R_{t+1}、cost は decision day の Δx にだけ、carry は x_t と t の金利で暦日按分

**USD numeraire**: R_c は c の対 USD log return、R_USD = 0。x は和ゼロなので、x · R は numeraire に依らない。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from scripts.research.classical_premia import prereg
from scripts.research.continuous_portfolio import construction

TRADING_DAYS: Final[float] = 252.0
UNIVERSE: Final[tuple[str, ...]] = prereg.UNIVERSE
FAMILIES: Final[tuple[str, ...]] = ("carry", "momentum")


# ----------------------------------------------------------------------
# 入力
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Inputs:
    """book が読むもの全部。`returns` は全 panel（warm-up を含む）、`span` は P&L の対象日。"""

    returns: pd.DataFrame  #: 日次 R（対 USD log return）、列 = UNIVERSE、R_USD = 0
    signal_rates: pd.DataFrame  #: carry の signal 用金利（%）。月末の翌暦日から使う置き方済み
    account_rates: dict[str, pd.DataFrame]  #: financing 会計の金利基準（%）
    decision_days: pd.DatetimeIndex  #: 月初の decision day（span 内）
    span: pd.DatetimeIndex  #: 最初の decision day … 最後から 2 番目の営業日（P&L は翌日）


def usd_numeraire_returns(pair_returns: pd.DataFrame) -> pd.DataFrame:
    """ECB panel の pair log return から R_c（c の対 USD）を作る。R_USD = 0。"""
    out = pd.DataFrame(0.0, index=pair_returns.index, columns=list(UNIVERSE))
    for currency in UNIVERSE:
        if currency == "USD":
            continue
        if f"{currency}_USD" in pair_returns.columns:
            out[currency] = pair_returns[f"{currency}_USD"]
        elif f"USD_{currency}" in pair_returns.columns:
            out[currency] = -pair_returns[f"USD_{currency}"]
        else:
            raise KeyError(f"{currency} の USD pair が無い")
    if out.isna().any().any():
        raise ValueError("R に欠損がある（ECB panel は全通貨が同じ営業日に揃うはず）")
    return out


def monthly_decision_days(
    index: pd.DatetimeIndex, first_on_or_after: str, last_return_day: str
) -> pd.DatetimeIndex:
    """各月の最初の営業日。最後の return 日は decision day にしない（翌日の P&L が無い）。"""
    frame = pd.Series(index, index=index)
    frame = frame[
        (frame.index >= pd.Timestamp(first_on_or_after))
        & (frame.index < pd.Timestamp(last_return_day))
    ]
    firsts = frame.groupby(frame.index.to_period("M")).min()
    return pd.DatetimeIndex(firsts.to_numpy())


# ----------------------------------------------------------------------
# score
# ----------------------------------------------------------------------
def carry_scores(signal_rates: pd.DataFrame) -> pd.DataFrame:
    """s_c = 金利の水準（%）。**lag は signal_rates 側で掛け済み**であること。"""
    return signal_rates[list(UNIVERSE)].copy()


def momentum_scores(returns: pd.DataFrame) -> pd.DataFrame:
    """12-1: Σ R over 営業日 [t−251, t−21] = logP(t−21) − logP(t−252)。"""
    lookback = int(prereg.MOMENTUM["formation_trading_days"])
    skip = int(prereg.MOMENTUM["skip_trading_days"])
    log_price = returns[list(UNIVERSE)].cumsum()
    return log_price.shift(skip) - log_price.shift(lookback)


def rank_weights(scores: np.ndarray) -> np.ndarray:
    """rank − mean(rank)（同順位は平均順位）を Σ|w| = 1 に。全部同順位なら 0。NaN は許さない。"""
    if not np.all(np.isfinite(scores)):
        raise ValueError("rank weight に NaN の score が来た（fail-closed）")
    ranks = pd.Series(scores).rank(method="average").to_numpy()
    centred = ranks - ranks.mean()
    total = float(np.abs(centred).sum())
    if total == 0.0:
        return np.zeros_like(centred)
    return centred / total


# ----------------------------------------------------------------------
# risk
# ----------------------------------------------------------------------
def covariances(
    returns: pd.DataFrame, days: pd.DatetimeIndex, columns: list[str]
) -> dict[pd.Timestamp, np.ndarray]:
    """decision day t の**前日まで**（t−252 … t−1）の 252 営業日の年率共分散。

    R_t は t の fix（14:15 CET）で初めて確定するので、t の fix で執行する weight には使わない（Role 2 N-2）。
    """
    window = int(prereg.RISK["covariance_window"])
    values = returns[columns].to_numpy()
    out: dict[pd.Timestamp, np.ndarray] = {}
    for day in days:
        loc = returns.index.get_loc(day)
        if loc < window:
            raise ValueError(f"{day.date()}: 共分散の窓が足りない")
        block = values[loc - window : loc]
        out[day] = np.cov(block, rowvar=False, ddof=1) * TRADING_DAYS
    return out


def _vol(w: np.ndarray, cov: np.ndarray) -> float:
    return float(np.sqrt(max(float(w @ cov @ w), 0.0)))


def compose(
    weights: dict[str, np.ndarray], cov: np.ndarray, families: tuple[str, ...] = FAMILIES
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    """family を unit vol に揃えて等ウェイトで足し、10% vol へ。戻り値は (x, family 別の x, 診断)。"""
    units: dict[str, np.ndarray] = {}
    for family in families:
        w = weights[family]
        sigma = _vol(w, cov)
        units[family] = w / sigma if sigma > 0 else np.zeros_like(w)
    share = 1.0 / len(families)
    raw = sum(share * units[f] for f in families)
    sigma_raw = _vol(raw, cov)
    if sigma_raw <= 0:
        zero = np.zeros_like(raw)
        return zero, {f: zero.copy() for f in families}, {"leverage": 0.0, "capped": False}
    leverage = float(prereg.RISK["target_vol"]) / sigma_raw
    cap = float(prereg.RISK["gross_cap"])
    gross = float(np.abs(raw).sum()) * leverage
    capped = gross > cap
    if capped:
        leverage *= cap / gross
    parts = {f: leverage * share * units[f] for f in families}
    return leverage * raw, parts, {"leverage": leverage, "capped": capped}


# ----------------------------------------------------------------------
# book
# ----------------------------------------------------------------------
def targets(
    inputs: Inputs,
    scores: dict[str, pd.DataFrame],
    *,
    universe: tuple[str, ...] = UNIVERSE,
    families: tuple[str, ...] = FAMILIES,
    cov: dict[pd.Timestamp, np.ndarray] | None = None,
) -> dict[str, pd.DataFrame]:
    """decision day ごとの target x（composite と family 別）。universe 外の通貨は 0。"""
    columns = list(universe)
    idx = [UNIVERSE.index(c) for c in columns]
    if cov is None:
        cov = covariances(inputs.returns, inputs.decision_days, columns)
    if cov[inputs.decision_days[0]].shape != (len(columns), len(columns)):
        raise ValueError("共分散の次元が universe と合わない")
    rows: dict[str, list[np.ndarray]] = {"composite": [], **{f: [] for f in families}}
    capped: list[bool] = []
    for day in inputs.decision_days:
        weights = {
            f: rank_weights(scores[f].loc[day, columns].to_numpy(dtype=float)) for f in families
        }
        x, parts, info = compose(weights, cov[day], families)
        for key, value in (("composite", x), *parts.items()):
            full = np.zeros(len(UNIVERSE))
            full[idx] = value
            rows[key].append(full)
        capped.append(bool(info["capped"]))
    out = {
        key: pd.DataFrame(np.vstack(value), index=inputs.decision_days, columns=list(UNIVERSE))
        for key, value in rows.items()
    }
    out["capped"] = pd.DataFrame({"capped": capped}, index=inputs.decision_days)
    return out


def run(
    inputs: Inputs,
    scores: dict[str, pd.DataFrame],
    *,
    universe: tuple[str, ...] = UNIVERSE,
    families: tuple[str, ...] = FAMILIES,
    cost_multiple: float = 1.0,
    cov: dict[pd.Timestamp, np.ndarray] | None = None,
) -> pd.DataFrame:
    """日次の book。行 = P&L 日（t+1）。spot・cost・各金利基準の carry・pair notional・family 別の分解を持つ。"""
    target = targets(inputs, scores, universe=universe, families=families, cov=cov)
    span = inputs.span
    index = inputs.returns.index
    held = target["composite"].reindex(span, method="ffill")
    if held.isna().any().any():
        raise ValueError("span の最初の日が decision day ではない")
    parts = {f: target[f].reindex(span, method="ffill") for f in families}
    locations = index.get_indexer(span)
    if (locations < 0).any() or locations[-1] + 1 >= len(index):
        raise ValueError("span の日が panel に無いか、最後の日の翌日が無い")
    next_days = index[locations + 1]
    realised = inputs.returns.iloc[locations + 1][list(UNIVERSE)].to_numpy()
    x = held.to_numpy()
    days = np.asarray((next_days - span).days, dtype=float)

    previous = np.vstack([np.zeros(len(UNIVERSE)), x[:-1]])
    delta = x - previous
    cost = np.abs(delta).sum(axis=1) * construction.CHARGED_ONE_WAY_BP * cost_multiple / 10_000.0

    frame = pd.DataFrame(index=next_days)
    frame.index.name = "pnl_day"
    #: exposure を持っている日 t（P&L は t+1）。decision day とは限らない（Role 2 N-8）
    frame["exposure_day"] = span
    frame["spot"] = (x * realised).sum(axis=1)
    frame["transaction_cost"] = cost
    frame["one_way_traded"] = np.abs(delta).sum(axis=1)
    frame["currency_gross"] = np.abs(x).sum(axis=1)
    foreign = [i for i, c in enumerate(UNIVERSE) if c != prereg.NUMERAIRE]
    frame["pair_notional_years"] = np.abs(x[:, foreign]).sum(axis=1) * days / 365.0
    frame["cost_multiple"] = cost_multiple
    usd = UNIVERSE.index("USD")
    used = sorted({UNIVERSE.index(c) for c in universe} | {usd})
    #: 通貨別の寄与は cross-section 平均を引いた return / 金利で測る（Role 1 R3）。Σx = 0 なので
    #: 合計は変わらず、「USD は numeraire だから寄与 0」という偏りが消える
    realised_dm = realised - realised.mean(axis=1, keepdims=True)
    for basis, panel in inputs.account_rates.items():
        level = panel.reindex(span)[list(UNIVERSE)].to_numpy() / 100.0
        if np.isnan(level[:, used]).any():
            raise ValueError(f"{basis}: span 内に金利の欠損がある（USD を含む、fail-closed）")
        level = np.where(np.isnan(level), 0.0, level)
        relative = level - level[:, [usd]]
        carry = x * relative * days[:, None] / 365.0
        frame[f"carry_{basis}"] = carry.sum(axis=1)
        demeaned = level - level.mean(axis=1, keepdims=True)
        carry_dm = x * demeaned * days[:, None] / 365.0
        for i, currency in enumerate(UNIVERSE):
            frame[f"carry_{basis}_{currency}"] = carry_dm[:, i]
        for family in families:
            frame[f"carry_{basis}__{family}"] = (
                parts[family].to_numpy() * relative * days[:, None] / 365.0
            ).sum(axis=1)
    for i, currency in enumerate(UNIVERSE):
        frame[f"x_{currency}"] = x[:, i]
        frame[f"spot_{currency}"] = x[:, i] * realised_dm[:, i]
    #: family 別の cost は**実際の売買**（|Δx_f|）の比、markup は外国脚の |x_f| の比で按分する（Role 1 R2）
    traded: dict[str, np.ndarray] = {}
    foreign_held: dict[str, np.ndarray] = {}
    for family in families:
        xf = parts[family].to_numpy()
        frame[f"spot__{family}"] = (xf * realised).sum(axis=1)
        prev_f = np.vstack([np.zeros(len(UNIVERSE)), xf[:-1]])
        traded[family] = np.abs(xf - prev_f).sum(axis=1)
        foreign_held[family] = np.abs(xf[:, foreign]).sum(axis=1)
    for name, source in (("cost_share", traded), ("markup_share", foreign_held)):
        total = sum(source.values())
        for family in families:
            frame[f"{name}__{family}"] = np.divide(
                source[family],
                total,
                out=np.full_like(total, 1.0 / len(families)),
                where=total > 0,
            )
    frame["is_decision_day"] = np.isin(span, inputs.decision_days)
    return frame


# ----------------------------------------------------------------------
# 会計の行
# ----------------------------------------------------------------------
def tc_net(frame: pd.DataFrame) -> pd.Series:
    """NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING。"""
    return frame["spot"] - frame["transaction_cost"]


def markup_charge(frame: pd.DataFrame, markup: float) -> pd.Series:
    return markup * frame["cost_multiple"] * frame["pair_notional_years"]


def judged_net(frame: pd.DataFrame, basis: str, markup: float) -> pd.Series:
    """TOTAL_ECONOMIC(basis, markup)。"""
    return (
        frame["spot"]
        + frame[f"carry_{basis}"]
        - frame["transaction_cost"]
        - markup_charge(frame, markup)
    )


def judged_by_currency(frame: pd.DataFrame, basis: str, markup: float) -> pd.DataFrame:
    """通貨別の judged。spot と carry は cross-section 平均を引いた値（numeraire に依らない）、
    cost と markup は各日の |x_c| の比で按分する（USD numeraire の routing に依存させない）。"""
    x = frame[[f"x_{c}" for c in UNIVERSE]].abs()
    share = x.div(x.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0)
    charge = frame["transaction_cost"] + markup_charge(frame, markup)
    out = pd.DataFrame(index=frame.index)
    for currency in UNIVERSE:
        out[currency] = (
            frame[f"spot_{currency}"]
            + frame[f"carry_{basis}_{currency}"]
            - charge * share[f"x_{currency}"]
        )
    return out


def judged_by_family(
    frame: pd.DataFrame, basis: str, markup: float, families: tuple[str, ...] = FAMILIES
) -> pd.DataFrame:
    """family 別の judged。spot と carry は線形なので厳密、cost は |Δx_f|、markup は外国脚の |x_f| で按分。"""
    charge = markup_charge(frame, markup)
    return pd.DataFrame(
        {
            f: frame[f"spot__{f}"]
            + frame[f"carry_{basis}__{f}"]
            - frame["transaction_cost"] * frame[f"cost_share__{f}"]
            - charge * frame[f"markup_share__{f}"]
            for f in families
        },
        index=frame.index,
    )


def tc_net_by_family(frame: pd.DataFrame, families: tuple[str, ...] = FAMILIES) -> pd.DataFrame:
    return pd.DataFrame(
        {
            f: frame[f"spot__{f}"] - frame["transaction_cost"] * frame[f"cost_share__{f}"]
            for f in families
        },
        index=frame.index,
    )


__all__ = [
    "FAMILIES",
    "Inputs",
    "carry_scores",
    "compose",
    "covariances",
    "judged_by_currency",
    "judged_by_family",
    "judged_net",
    "momentum_scores",
    "monthly_decision_days",
    "rank_weights",
    "run",
    "targets",
    "tc_net",
    "usd_numeraire_returns",
]
