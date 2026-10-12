"""RATES_ANCHORED_FX_CONVERGENCE の契約（合成の data だけ。実 data を読まない）。"""

from __future__ import annotations

import datetime as dt
import hashlib
import pathlib

import pytest

from scripts.research.rates_anchored_fx import data_rates as dr

REPO = pathlib.Path(__file__).resolve().parents[2]
HOLD = REPO / "docs/governance/fxid_long_term_hold_ruling_2026_10.md"


def test_hold_ruling_is_unchanged():
    raw = HOLD.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == (
        "e7abc2f56c559d0965c551485dbc9d4e883af8acd66ebfb2e393954d9718e221"
    )


def test_request_windows_stay_inside_the_seen_span():
    ws = dr.windows()
    assert ws[0][0] == dt.datetime(2021, 4, 26, tzinfo=dt.UTC)
    assert ws[-1][1] == dt.datetime(2025, 12, 29, tzinfo=dt.UTC)
    for lo, hi in ws:
        dr.check_bounds(lo, hi)
        assert (hi - lo).days <= 45


@pytest.mark.parametrize(
    ("lo", "hi"),
    [
        (dt.datetime(2021, 4, 25, tzinfo=dt.UTC), dt.datetime(2021, 5, 1, tzinfo=dt.UTC)),
        (dt.datetime(2025, 12, 1, tzinfo=dt.UTC), dt.datetime(2025, 12, 30, tzinfo=dt.UTC)),
        (dt.datetime(2022, 1, 1), dt.datetime(2022, 2, 1)),
    ],
)
def test_out_of_span_or_naive_bounds_are_refused(lo, hi):
    with pytest.raises(dr.BoundaryError):
        dr.check_bounds(lo, hi)


def test_candle_times_outside_span_are_refused():
    with pytest.raises(dr.BoundaryError):
        dr.check_candle_times([dt.datetime(2021, 4, 25, 23, 45, tzinfo=dt.UTC)])
    with pytest.raises(dr.BoundaryError):
        dr.check_candle_times([dt.datetime(2025, 12, 29, 0, 0, tzinfo=dt.UTC)])
    dr.check_candle_times([dt.datetime(2025, 12, 28, 23, 45, tzinfo=dt.UTC)])


def test_time_parser_refuses_str_subclass_and_non_utc():
    class Evil(str):
        pass

    with pytest.raises(dr.BoundaryError):
        dr.parse_oanda_time(Evil("2021-05-01T00:00:00.000000000Z"))
    with pytest.raises(dr.BoundaryError):
        dr.parse_oanda_time("2021-05-01T00:00:00.000000000+01:00")
    assert dr.parse_oanda_time("2021-05-01T00:15:00.000000000Z") == dt.datetime(
        2021, 5, 1, 0, 15, tzinfo=dt.UTC
    )


# ------------------------------------------------------------------ engine（合成）

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scripts.research.rates_anchored_fx import engine as en  # noqa: E402


def _synthetic(n_days=130, beta=0.5, seed=0, shock_every=7):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2023-01-02", periods=n_days, tz="UTC")
    idx = pd.DatetimeIndex(
        [
            d + pd.Timedelta(hours=7) + pd.Timedelta(minutes=15 * k)
            for d in days
            for k in range(1, 57)
        ]
    )
    rd = np.cumsum(rng.normal(0, 2e-4, len(idx)))
    noise = rng.normal(0, 1e-4, len(idx))
    shock = np.zeros(len(idx))
    times = pd.Series(range(len(idx)), index=idx)
    for d_i, d in enumerate(days):
        if d_i % shock_every == 0:
            t = d + pd.Timedelta(hours=14)
            if t in times.index:
                shock[times[t]] = 30e-4  # その bar だけの overshoot、次の bar で戻る
    logp = np.log(1.1) + beta * rd + noise + shock
    mid = np.exp(logp)
    fx = pd.DataFrame(
        {
            "mid_c": mid,
            "bid_c": mid * (1 - 0.3e-4),
            "ask_c": mid * (1 + 0.3e-4),
            "mid_h": mid * (1 + 1e-4),
            "mid_l": mid * (1 - 1e-4),
            "spread_bp": 0.6,
            "ok": True,
        },
        index=idx,
    )
    levels = {"RD": pd.Series(rd, index=idx)}
    return en.PairData("EUR_USD", fx, levels, pd.Series(True, index=idx)), shock


def test_daily_fit_uses_only_prior_days():
    pdat, _ = _synthetic()
    obs = en.observations(pdat)
    spec = en.Spec(lookback_days=60)
    fits = en.daily_fits(obs, ["RD"], spec)
    day = fits.index[5]
    obs2 = obs.copy()
    obs2.loc[obs2["day"] == day, "dfx"] += 0.05  # その日の data を壊す
    fits2 = en.daily_fits(obs2, ["RD"], spec)
    assert fits.loc[day, "b_RD"] == fits2.loc[day, "b_RD"]
    assert fits.loc[day, "sigma"] == fits2.loc[day, "sigma"]
    assert abs(fits["b_RD"].median() - 0.5) < 0.1


def test_overshoot_is_shorted_and_converges_on_synthetic_data():
    pdat, _ = _synthetic()
    obs = en.observations(pdat)
    spec = en.Spec(lookback_days=60)
    fits = en.daily_fits(obs, ["RD"], spec)
    days = sorted(obs["day"].unique())
    costs = en.cost_profile(pdat.fx, days, spec.lookback_days)
    atr = en.atr_series(pdat.fx, spec.atr_n)
    sig = en.candidate_signals(pdat, obs, fits, costs, atr, spec, ["RD"])
    assert len(sig) > 0
    at_shock = sig[(sig.index.hour == 14) & (sig.index.minute == 0)]
    assert len(at_shock) > 0 and (at_shock["direction"] == -1).all()
    trades = en.run_portfolio({"EUR_USD": at_shock}, {"EUR_USD": pdat}, ["RD"], spec, set(), set())
    df = en.trades_frame(trades)
    assert len(df) == len(at_shock)
    assert (df["gross_bp"] > 0).all()
    assert (df["exit_reason"] == "converged").all()


def test_decision_times_respect_london_and_new_york_windows():
    idx = pd.DatetimeIndex(
        ["2023-07-10 06:30", "2023-07-10 07:00", "2023-07-10 19:00", "2023-07-10 19:30"], tz="UTC"
    )
    # 夏時間: London 08:00 = 07:00 UTC、NY 15:00 = 19:00 UTC
    assert en.is_decision_time(idx).tolist() == [False, True, True, False]
