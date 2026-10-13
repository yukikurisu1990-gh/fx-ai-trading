# ruff: noqa: E501 -- research prose
"""RATES_ANCHORED_FX_CONVERGENCE の engine（事前登録 `docs/research/rates_anchored_fx_prereg_2026_10.md` §3〜§10）。

全ての推定（β・σ・ATR・cost の profile）は、その判定の時刻より前の情報だけを使う:
- β・σ・cost の profile: その日より前の lookback 営業日（日の単位で past-only）。
- ATR: 判定の時刻までに完成した H1 の bar。
- exit の判定: その bar の終わりの時刻までの気配（金利は as-of で直前の値）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Final
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

NY: Final = ZoneInfo("America/New_York")
LDN: Final = ZoneInfo("Europe/London")
FRA: Final = ZoneInfo("Europe/Berlin")
BAR: Final = pd.Timedelta(minutes=15)
HUBER_C: Final[float] = 1.345
SEED: Final[int] = 20261013


@dataclass(frozen=True)
class Spec:
    """事前登録 §4〜§7 の primary の値。sensitivity は replace で 1 つだけ変える。"""

    z_entry: float = 2.5
    lookback_days: int = 90
    under_frac: float = 0.50
    near_zero_frac: float = 0.10
    capture: float = 0.60
    cost_multiple: float = 4.0
    atr_hurdle: float = 0.35
    resid_exit: float = 0.40
    invalidation: float = 0.50
    invalidation_min_fair_sigma: float = 1.0
    stop_expansion: float = 1.5
    max_hold_min: int = 120
    slippage_bp: float = 0.5
    cost_stress: float = 1.0
    sigma_kind: str = "mad"  # "mad" / "sd"
    use_usd_common: bool = False
    abnormal_spread_mult: float = 3.0
    atr_n: int = 14
    min_fair_z: float = 2.5


@dataclass
class PairData:
    """1 つの pair の 15 分の grid（index = bar の終わりの UTC 時刻）。"""

    pair: str
    fx: pd.DataFrame  # mid_c, bid_c, ask_c, mid_h, mid_l, spread_bp, ok
    levels: dict[str, pd.Series]  # fair の regressor の水準（log）: "RD", 必要なら "UC"
    rate_ok: pd.Series  # t の bar が両方の金利で存在し volume > 0
    extra: dict[str, pd.Series] = field(default_factory=dict)


# ------------------------------------------------------------------ data の整形


def fx_grid(frame: pd.DataFrame) -> pd.DataFrame:
    f = frame.copy()
    f["end"] = pd.to_datetime(f["ts"], utc=True) + BAR
    f = f.set_index("end").sort_index()
    out = pd.DataFrame(index=f.index)
    out["mid_c"] = (f["bid_c"] + f["ask_c"]) / 2
    out["bid_c"] = f["bid_c"]
    out["ask_c"] = f["ask_c"]
    out["mid_h"] = (f["bid_h"] + f["ask_h"]) / 2
    out["mid_l"] = (f["bid_l"] + f["ask_l"]) / 2
    out["spread_bp"] = (f["ask_c"] - f["bid_c"]) / out["mid_c"] * 1e4
    out["ok"] = f["complete_bucket"].astype(bool) & (f["ask_c"] >= f["bid_c"]) & (f["bid_c"] > 0)
    return out


def rate_mid(frame: pd.DataFrame) -> pd.DataFrame:
    f = frame.copy()
    f["end"] = pd.to_datetime(f["ts"], utc=True) + BAR
    f = f.set_index("end").sort_index()
    return pd.DataFrame(
        {
            "mid": (f["bid_c"] + f["ask_c"]) / 2,
            "volume": f["volume"],
            "ok": f["ask_c"] >= f["bid_c"],
        }
    )


def rd_level(foreign: pd.DataFrame, usd: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """RD の水準 = −log B_foreign + log B_USD（Δ がそのまま ΔRD）。両方の bar がある時刻だけ。"""
    idx = foreign.index.intersection(usd.index)
    lvl = -np.log(foreign.loc[idx, "mid"]) + np.log(usd.loc[idx, "mid"])
    ok = (
        (foreign.loc[idx, "volume"] > 0)
        & (usd.loc[idx, "volume"] > 0)
        & foreign.loc[idx, "ok"]
        & usd.loc[idx, "ok"]
    )
    return lvl, ok


def shift_one_trading_day(series: pd.Series) -> pd.Series:
    """金利の series を、次の営業日の同じ時刻に移す（time-shift の control）。金曜は月曜へ。"""
    t = series.index
    wd = t.tz_convert(NY).dayofweek
    add = np.where(wd == 4, 3, 1)
    new_index = t + pd.to_timedelta(add, unit="D")
    return pd.Series(series.to_numpy(), index=new_index).sort_index()


# ------------------------------------------------------------------ 観測


def is_decision_time(idx: pd.DatetimeIndex) -> np.ndarray:
    ny = idx.tz_convert(NY)
    ldn = idx.tz_convert(LDN)
    on_half_hour = (idx.minute % 30) == 0
    after_ldn = (ldn.hour * 60 + ldn.minute) >= 8 * 60
    before_ny = (ny.hour * 60 + ny.minute) <= 15 * 60
    weekday = ny.dayofweek < 5
    return np.asarray(on_half_hour & after_ldn & before_ny & weekday)


def observations(pd_: PairData, rate_mask: pd.Series | None = None) -> pd.DataFrame:
    """判定の時刻の (ΔFX, ΔX_j) の表。t と t − 30m の全ての価格がある観測だけ。"""
    fx = pd_.fx
    idx = fx.index[is_decision_time(fx.index)]
    prev = idx - 2 * BAR
    have = fx.index
    m = np.isin(prev, have) & fx.loc[idx, "ok"].to_numpy()
    idx, prev = idx[m], prev[m]
    m2 = fx.loc[prev, "ok"].to_numpy()
    idx, prev = idx[m2], prev[m2]
    out = pd.DataFrame(index=idx)
    out["dfx"] = np.log(fx.loc[idx, "mid_c"].to_numpy()) - np.log(fx.loc[prev, "mid_c"].to_numpy())
    rate_ok = pd_.rate_ok if rate_mask is None else rate_mask
    keep = np.ones(len(idx), bool)
    for name, lvl in pd_.levels.items():
        have_l = np.isin(idx, lvl.index) & np.isin(prev, lvl.index)
        keep &= have_l
        vals = np.full(len(idx), np.nan)
        vals[have_l] = lvl.reindex(idx[have_l]).to_numpy() - lvl.reindex(prev[have_l]).to_numpy()
        out["d" + name] = vals
    keep &= rate_ok.reindex(idx).fillna(False).to_numpy().astype(bool)
    out = out[keep]
    out["day"] = out.index.tz_convert(NY).date
    out["hour_ny"] = out.index.tz_convert(NY).hour
    return out.dropna()


# ------------------------------------------------------------------ 推定


def huber(
    x: np.ndarray, y: np.ndarray, c: float = HUBER_C, iters: int = 50
) -> tuple[np.ndarray, np.ndarray]:
    """Huber の IRLS（切片あり）。返り値: 係数（切片が先頭）と残差。"""
    xx = np.column_stack([np.ones(len(y)), x])
    beta = np.linalg.lstsq(xx, y, rcond=None)[0]
    for _ in range(iters):
        r = y - xx @ beta
        s = np.median(np.abs(r - np.median(r))) / 0.6745
        if s <= 0:
            break
        u = np.abs(r / s)
        w = np.where(u <= c, 1.0, c / np.maximum(u, 1e-12))
        sw = np.sqrt(w)
        new = np.linalg.lstsq(xx * sw[:, None], y * sw, rcond=None)[0]
        if np.max(np.abs(new - beta)) < 1e-12:
            beta = new
            break
        beta = new
    return beta, y - xx @ beta


def daily_fits(obs: pd.DataFrame, regressors: list[str], spec: Spec) -> pd.DataFrame:
    """各営業日に、その日より前の lookback 営業日で推定（past-only）。"""
    days = sorted(obs["day"].unique())
    rows = []
    by_day = {d: g for d, g in obs.groupby("day")}
    for i, d in enumerate(days):
        if i < spec.lookback_days:
            continue
        window = pd.concat([by_day[x] for x in days[i - spec.lookback_days : i]])
        x = window[["d" + r for r in regressors]].to_numpy()
        y = window["dfx"].to_numpy()
        coef, resid = huber(x, y)
        if spec.sigma_kind == "mad":
            sig = 1.4826 * float(np.median(np.abs(resid - np.median(resid))))
        else:
            sig = float(np.std(resid, ddof=1))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1 - float(np.sum(resid**2)) / ss_tot if ss_tot > 0 else float("nan")
        fx_sig = 1.4826 * float(np.median(np.abs(y - np.median(y))))
        row = {"day": d, "alpha": coef[0], "sigma": sig, "r2": r2, "fx_sigma": fx_sig, "n": len(y)}
        for j, r in enumerate(regressors):
            row["b_" + r] = coef[j + 1]
        rows.append(row)
    return pd.DataFrame(rows).set_index("day")


def cost_profile(fx: pd.DataFrame, days: list, lookback: int) -> dict:
    """(day, NY の時) → 過去 lookback 営業日の spread の中央値（bp）。"""
    f = fx[fx["ok"]].copy()
    f["day"] = f.index.tz_convert(NY).date
    f["hour"] = f.index.tz_convert(NY).hour
    per_day = {d: g for d, g in f.groupby("day")}
    out = {}
    for i, d in enumerate(days):
        prior = [x for x in days[max(0, i - lookback) : i] if x in per_day]
        if not prior:
            continue
        w = pd.concat([per_day[x] for x in prior])
        out[d] = w.groupby("hour")["spread_bp"].median().to_dict()
    return out


def atr_series(fx: pd.DataFrame, n: int) -> pd.Series:
    """H1（UTC の正時の境界）の true range の直前 n 本の平均（log）。index = H1 の bar の終わり。"""
    f = fx[fx["ok"]]
    start = f.index - BAR
    hour = start.floor("h")
    g = f.groupby(hour)
    h1 = pd.DataFrame({"h": g["mid_h"].max(), "l": g["mid_l"].min(), "c": g["mid_c"].last()})
    prev_c = h1["c"].shift(1)
    hi = np.maximum(h1["h"], prev_c.fillna(h1["h"]))
    lo = np.minimum(h1["l"], prev_c.fillna(h1["l"]))
    tr = np.log(hi) - np.log(lo)
    atr = tr.rolling(n, min_periods=n).mean()
    atr.index = atr.index + pd.Timedelta(hours=1)  # bar の終わり
    return atr


# ------------------------------------------------------------------ signal と執行


@dataclass
class Trade:
    pair: str
    kind: str  # "A" / "B"
    overlap: bool
    entry: pd.Timestamp
    exit: pd.Timestamp
    direction: int
    z: float
    fair_sigma: float
    expected_capture_bp: float
    expected_cost_bp: float
    gross_bp: float
    net_bp: float
    exit_reason: str
    event: bool


def event_flag(t: pd.Timestamp, fomc: set, ecb: set) -> bool:
    ny = t.tz_convert(NY)
    mins = ny.hour * 60 + ny.minute
    if ny.dayofweek < 5 and 8 * 60 + 30 <= mins <= 10 * 60 + 30:
        return True
    if ny.date() in fomc and 14 * 60 <= mins <= 16 * 60:
        return True
    fr = t.tz_convert(FRA)
    fm = fr.hour * 60 + fr.minute
    return bool(fr.date() in ecb and 13 * 60 + 45 <= fm <= 16 * 60)


def _asof(series: pd.Series, t: pd.Timestamp) -> float:
    i = series.index.searchsorted(t, side="right") - 1
    return float(series.iloc[i]) if i >= 0 else float("nan")


def candidate_signals(
    pd_: PairData,
    obs: pd.DataFrame,
    fits: pd.DataFrame,
    costs: dict,
    atr: pd.Series,
    spec: Spec,
    regressors: list[str],
    price_only: bool = False,
) -> pd.DataFrame:
    """判定の時刻ごとの signal の候補（gate を通ったものだけ）。"""
    o = obs[obs["day"].isin(fits.index)].copy()
    f = fits.reindex(o["day"]).set_index(o.index)
    if price_only:
        fair = np.zeros(len(o))
        sigma = f["fx_sigma"].to_numpy()
    else:
        fair = np.zeros(len(o))
        for r in regressors:
            fair = fair + f["b_" + r].to_numpy() * o["d" + r].to_numpy()
        sigma = f["sigma"].to_numpy()
    act = o["dfx"].to_numpy()
    res = act - fair
    z = res / sigma
    fz = np.abs(fair) / sigma
    a = np.abs(z) >= spec.z_entry
    same = (np.sign(act) == np.sign(fair)) | (np.abs(act) <= spec.near_zero_frac * np.abs(fair))
    b = (
        (not price_only)
        & (fz >= spec.min_fair_z)
        & same
        & (np.abs(act) <= spec.under_frac * np.abs(fair))
    )
    direction = np.where(a, -np.sign(z), np.sign(fair)).astype(int)
    d_size = np.abs(res)
    hour = o["hour_ny"].to_numpy()
    days = o["day"].to_numpy()
    spread_med = np.array(
        [costs.get(dd, {}).get(int(hh), np.nan) for dd, hh in zip(days, hour, strict=True)]
    )
    c_exp = (spread_med + spec.slippage_bp) * spec.cost_stress
    atr_v = np.array([_asof(atr, t) for t in o.index])
    cap_bp = spec.capture * d_size * 1e4
    gate = (cap_bp >= spec.cost_multiple * c_exp) & (d_size >= spec.atr_hurdle * atr_v)
    entry_spread = pd_.fx.loc[o.index, "spread_bp"].to_numpy()
    sane = entry_spread <= spec.abnormal_spread_mult * spread_med
    sig = (a | b) & gate & sane & np.isfinite(c_exp) & np.isfinite(atr_v) & (direction != 0)
    out = pd.DataFrame(
        {
            "kind": np.where(a, "A", "B"),
            "overlap": a & b,
            "direction": direction,
            "z": z,
            "fair_sigma": fz,
            "res": res,
            "fair": fair,
            "cap_bp": cap_bp,
            "c_exp": c_exp,
            "drd": o["dRD"].to_numpy() if "dRD" in o else np.zeros(len(o)),
            "rd_sign": o["rd_sign"].to_numpy() if "rd_sign" in o else np.ones(len(o)),
        },
        index=o.index,
    )
    out["day"] = days
    for r in regressors:
        out["b_" + r] = 0.0 if price_only else f["b_" + r].to_numpy()
    return out[sig]


def simulate(
    pd_: PairData,
    row: pd.Series,
    regressors: list[str],
    spec: Spec,
    fomc: set,
    ecb: set,
    price_only: bool = False,
    direction_override: int | None = None,
) -> Trade | None:
    t = row.name
    fx = pd_.fx
    anchor = t - 2 * BAR
    direction = int(direction_override if direction_override is not None else row["direction"])
    ny_t = t.tz_convert(NY)
    cutoff = pd.Timestamp(ny_t.date().isoformat() + " 16:45", tz=NY).tz_convert("UTC")
    last = min(t + pd.Timedelta(minutes=spec.max_hold_min), cutoff)
    path = fx.loc[(fx.index > t) & (fx.index <= last)]
    path = path[path["ok"]]
    if len(path) == 0:
        return None
    p_anchor = math.log(fx.at[anchor, "mid_c"])
    lv0 = {r: _asof(pd_.levels[r], anchor) for r in regressors}
    res0 = float(row["res"])
    m0 = float(row["drd"])
    use_thesis = (
        (not price_only) and row["fair_sigma"] >= spec.invalidation_min_fair_sigma and m0 != 0
    )
    reason = "time"
    exit_t = path.index[-1]
    for s in path.index:
        if price_only:
            res_s = math.log(fx.at[s, "mid_c"]) - p_anchor
        else:
            fair_s = sum(
                row["b_" + r]
                * (_asof(pd_.levels[r], s) - lv0[r])
                * (row["rd_sign"] if r == "RD" else 1.0)
                for r in regressors
            )
            res_s = (math.log(fx.at[s, "mid_c"]) - p_anchor) - fair_s
        if np.sign(res_s) == np.sign(res0) and abs(res_s) >= spec.stop_expansion * abs(res0):
            reason, exit_t = "stop", s
            break
        if use_thesis:
            m = (_asof(pd_.levels["RD"], s) - lv0["RD"]) * row["rd_sign"]
            if m * np.sign(m0) <= spec.invalidation * abs(m0):
                reason, exit_t = "thesis", s
                break
        if abs(res_s) <= spec.resid_exit * abs(res0):
            reason, exit_t = "converged", s
            break
    if reason == "time" and exit_t >= cutoff:
        reason = "cutoff"
    entry_px = fx.at[t, "ask_c"] if direction > 0 else fx.at[t, "bid_c"]
    exit_px = fx.at[exit_t, "bid_c"] if direction > 0 else fx.at[exit_t, "ask_c"]
    gross = direction * (math.log(fx.at[exit_t, "mid_c"]) - math.log(fx.at[t, "mid_c"])) * 1e4
    quoted = direction * (math.log(exit_px) - math.log(entry_px)) * 1e4
    spread_cost = gross - quoted
    net = gross - (spread_cost + spec.slippage_bp) * spec.cost_stress
    return Trade(
        pair=pd_.pair,
        kind=str(row["kind"]),
        overlap=bool(row["overlap"]),
        entry=t,
        exit=exit_t,
        direction=direction,
        z=float(row["z"]),
        fair_sigma=float(row["fair_sigma"]),
        expected_capture_bp=float(row["cap_bp"]),
        expected_cost_bp=float(row["c_exp"]),
        gross_bp=gross,
        net_bp=net,
        exit_reason=reason,
        event=event_flag(t, fomc, ecb),
    )


def run_portfolio(
    signals: dict[str, pd.DataFrame],
    pairs: dict[str, PairData],
    regressors: list[str],
    spec: Spec,
    fomc: set,
    ecb: set,
    price_only: bool = False,
) -> list[Trade]:
    """時刻の順に、pair ごとに 1 position、同じ USD の方向の衝突は expected capture / C の大きい方（§6）。"""
    allsig = []
    for p, s in signals.items():
        for t, row in s.iterrows():
            allsig.append((t, p, row))
    allsig.sort(key=lambda x: (x[0], x[1]))
    open_until: dict[str, tuple[pd.Timestamp, int]] = {}
    trades: list[Trade] = []
    i = 0
    while i < len(allsig):
        t = allsig[i][0]
        batch = []
        while i < len(allsig) and allsig[i][0] == t:
            batch.append(allsig[i])
            i += 1
        for p in list(open_until):
            if open_until[p][0] <= t:
                del open_until[p]
        cands = [(p, row) for _, p, row in batch if p not in open_until]
        cands = [
            (p, row)
            for p, row in cands
            if not any(d == int(row["direction"]) for _, d in open_until.values())
        ]
        chosen = {}
        for p, row in sorted(
            cands, key=lambda pr: (-(pr[1]["cap_bp"] / pr[1]["c_exp"]), -abs(pr[1]["z"]))
        ):
            d = int(row["direction"])
            if d in chosen:
                continue
            chosen[d] = (p, row)
        for p, row in chosen.values():
            tr = simulate(pairs[p], row, regressors, spec, fomc, ecb, price_only=price_only)
            if tr is None:
                continue
            trades.append(tr)
            open_until[p] = (tr.exit, tr.direction)
    return trades


# ------------------------------------------------------------------ 指標


def trades_frame(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=[f.name for f in Trade.__dataclass_fields__.values()])
    df = pd.DataFrame([t.__dict__ for t in trades])
    df["exit_day"] = pd.to_datetime(df["exit"]).dt.tz_convert(NY).dt.date
    df["year"] = pd.to_datetime(df["entry"]).dt.tz_convert(NY).dt.year
    df["hold_min"] = (
        pd.to_datetime(df["exit"]) - pd.to_datetime(df["entry"])
    ).dt.total_seconds() / 60
    return df


def metrics(df: pd.DataFrame, eval_days: list) -> dict:
    n_days = len(eval_days)
    years = n_days / 252 if n_days else float("nan")
    if len(df) == 0:
        return {
            "trades": 0,
            "trades_per_year": 0.0,
            "net_mean_bp": float("nan"),
            "sharpe": float("nan"),
        }
    daily = df.groupby("exit_day")["net_bp"].sum().reindex(eval_days, fill_value=0.0)
    mu, sd = daily.mean(), daily.std(ddof=1)
    down = daily[daily < 0]
    dd_sd = math.sqrt(float((np.minimum(daily, 0) ** 2).mean())) if len(down) else float("nan")
    cum = daily.cumsum()
    maxdd_bp = float((cum.cummax() - cum).max())
    wins = df.loc[df["net_bp"] > 0, "net_bp"].sum()
    losses = -df.loc[df["net_bp"] < 0, "net_bp"].sum()
    return {
        "trades": int(len(df)),
        "trades_per_year": round(len(df) / years, 2),
        "win_rate": round(float((df["net_bp"] > 0).mean()), 4),
        "gross_mean_bp": round(float(df["gross_bp"].mean()), 4),
        "cost_mean_bp": round(float((df["gross_bp"] - df["net_bp"]).mean()), 4),
        "net_mean_bp": round(float(df["net_bp"].mean()), 4),
        "net_median_bp": round(float(df["net_bp"].median()), 4),
        "net_total_bp": round(float(df["net_bp"].sum()), 2),
        "sharpe": round(float(mu / sd * math.sqrt(252)), 4) if sd > 0 else float("nan"),
        "gross_sharpe": round(
            float(
                df.groupby("exit_day")["gross_bp"]
                .sum()
                .reindex(eval_days, fill_value=0.0)
                .pipe(lambda s: s.mean() / s.std(ddof=1) * math.sqrt(252))
            ),
            4,
        ),
        "sortino": round(float(mu / dd_sd * math.sqrt(252)), 4)
        if dd_sd and dd_sd > 0
        else float("nan"),
        "maxdd_pct_1x": round(maxdd_bp / 100, 4),
        "profit_factor": round(float(wins / losses), 4) if losses > 0 else float("inf"),
        "position_hours_per_year": round(float(df["hold_min"].sum() / 60 / years), 2),
        "turnover_round_trips_per_year": round(len(df) / years, 2),
    }


def bootstrap(
    df: pd.DataFrame, eval_days: list, block: int = 10, reps: int = 2000, seed: int = SEED
) -> dict:
    daily = (
        df.groupby("exit_day")["net_bp"].sum().reindex(eval_days, fill_value=0.0).to_numpy()
        if len(df)
        else np.zeros(len(eval_days))
    )
    n = len(daily)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / block))
    means, sharpes = [], []
    for _ in range(reps):
        starts = rng.integers(0, n - block + 1, size=nb)
        sample = np.concatenate([daily[s : s + block] for s in starts])[:n]
        m, s = sample.mean(), sample.std(ddof=1)
        means.append(m)
        sharpes.append(m / s * math.sqrt(252) if s > 0 else 0.0)
    means, sharpes = np.array(means), np.array(sharpes)
    return {
        "mean_daily_bp_ci90": [
            round(float(np.quantile(means, 0.05)), 4),
            round(float(np.quantile(means, 0.95)), 4),
        ],
        "sharpe_ci90": [
            round(float(np.quantile(sharpes, 0.05)), 4),
            round(float(np.quantile(sharpes, 0.95)), 4),
        ],
        "p_mean_le_0": round(float(np.mean(means <= 0)), 4),
    }


def with_spec(spec: Spec, **kw: object) -> Spec:
    return replace(spec, **kw)


# ------------------------------------------------------------------ 診断（事前登録 §10）

Z_BINS: Final[list[tuple[float, float]]] = [
    (1.0, 1.5),
    (1.5, 2.0),
    (2.0, 2.5),
    (2.5, 3.0),
    (3.0, math.inf),
]


def _asof_vec(series: pd.Series, times: pd.DatetimeIndex) -> np.ndarray:
    i = series.index.searchsorted(times, side="right") - 1
    vals = series.to_numpy()
    out = np.full(len(times), np.nan)
    m = i >= 0
    out[m] = vals[i[m]]
    return out


def diagnostics(
    pd_: PairData, obs: pd.DataFrame, fits: pd.DataFrame, regressors: list[str]
) -> dict:
    o = obs[obs["day"].isin(fits.index)].copy()
    f = fits.reindex(o["day"]).set_index(o.index)
    fair = sum(f["b_" + r].to_numpy() * o["d" + r].to_numpy() for r in regressors)
    res = o["dfx"].to_numpy() - fair
    sigma = f["sigma"].to_numpy()
    z = res / sigma
    fz = np.abs(fair) / sigma
    anchor = o.index - 2 * BAR
    mid = np.log(pd_.fx["mid_c"])
    p_anchor = _asof_vec(mid, anchor)
    lv_anchor = {r: _asof_vec(pd_.levels[r], anchor) for r in regressors}
    out: dict = {"n_obs": int(len(o))}
    decay = {}
    conv = {}
    for h in (30, 60, 90, 120):
        th = o.index + pd.Timedelta(minutes=h)
        ph = _asof_vec(mid, th)
        fair_h = sum(
            f["b_" + r].to_numpy() * (_asof_vec(pd_.levels[r], th) - lv_anchor[r])
            for r in regressors
        )
        res_h = (ph - p_anchor) - fair_h
        ratio = res_h / res
        for lo, hi in Z_BINS:
            m = (np.abs(z) >= lo) & (np.abs(z) < hi) & np.isfinite(ratio)
            decay.setdefault(f"{lo}-{hi}", {})[str(h)] = {
                "n": int(m.sum()),
                "mean_ratio": round(float(np.mean(ratio[m])), 4) if m.any() else None,
                "median_ratio": round(float(np.median(ratio[m])), 4) if m.any() else None,
            }
        if h == 120:
            conv_ret = -np.sign(res) * (res_h - res) * 1e4
            fx_fwd = (ph - _asof_vec(mid, o.index)) * 1e4
            for lo, hi in Z_BINS:
                m = (np.abs(z) >= lo) & (np.abs(z) < hi) & np.isfinite(conv_ret)
                conv[f"{lo}-{hi}"] = {
                    "n": int(m.sum()),
                    "mean_conv_bp": round(float(np.mean(conv_ret[m])), 4) if m.any() else None,
                }
            under = {}
            for lo, hi in Z_BINS:
                m = (fz >= lo) & (fz < hi) & np.isfinite(fx_fwd)
                under[f"{lo}-{hi}"] = {
                    "n": int(m.sum()),
                    "mean_follow_bp": round(float(np.mean(np.sign(fair[m]) * fx_fwd[m])), 4)
                    if m.any()
                    else None,
                }
            out["underreaction_follow_120m_by_fair_sigma"] = under
    out["residual_decay_ratio"] = decay
    out["convergence_120m_by_abs_z"] = conv
    b = fits["b_RD"]
    rr = pd.Series(res, index=o.index)
    same_day = pd.Series(o["day"].to_numpy(), index=o.index)
    lag = rr.shift(1)
    m = same_day.eq(same_day.shift(1)) & np.isfinite(lag)
    rho = float(np.corrcoef(rr[m], lag[m])[0, 1]) if m.sum() > 10 else float("nan")
    out["regression"] = {
        "beta_rd_mean": round(float(b.mean()), 6),
        "beta_rd_sd": round(float(b.std()), 6),
        "beta_rd_q05_q50_q95": [round(float(b.quantile(q)), 6) for q in (0.05, 0.5, 0.95)],
        "beta_rd_share_positive": round(float((b > 0).mean()), 4),
        "r2_mean": round(float(fits["r2"].mean()), 4),
        "residual_lag1_autocorr_30m": round(rho, 4),
        "residual_half_life_min": round(float(-math.log(2) / math.log(rho) * 30), 1)
        if 0 < rho < 1
        else None,
        "hetero_corr_res2_abs_drd": round(
            float(np.corrcoef(res**2, np.abs(o["dRD"].to_numpy()))[0, 1]), 4
        ),
    }
    return out
