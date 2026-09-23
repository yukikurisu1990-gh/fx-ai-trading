"""USD-factor book の修正 — 合成入力だけで exposure を確かめる（第 3 裁定 §16–§17）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.research.continuous_portfolio import construction
from scripts.research.usd_factor_financing import book

CURRENCIES = list(construction.CURRENCIES)
FOREIGN = [c for c in CURRENCIES if c != "USD"]


def _returns(days: int = 500, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    raw = rng.normal(0, 0.005, size=(days, len(CURRENCIES)))
    frame = pd.DataFrame(raw, index=pd.bdate_range("2010-01-04", periods=days), columns=CURRENCIES)
    return frame.sub(frame.mean(axis=1), axis=0)


def _dollar_mu(index: pd.DatetimeIndex, flip_every: int = 60) -> pd.DataFrame:
    sign = np.where((np.arange(len(index)) // flip_every) % 2 == 0, 1.0, -1.0)
    frame = pd.DataFrame(0.0, index=index, columns=CURRENCIES)
    frame["USD"] = sign
    for c in FOREIGN:
        frame[c] = -sign / 7.0
    return frame


def _dollar_config(band: float = 0.10) -> construction.BookConfig:
    return construction.BookConfig(
        name="usd",
        mapping="linear",
        neutralize_leading_factor=False,
        weight_cap=0.5,
        band=band,
        vol_target=0.10,
        max_leverage=20.0,
    )


def test_default_rebalance_reproduces_construction_run_book_exactly() -> None:
    returns = _returns()
    rng = np.random.default_rng(1)
    mu = pd.DataFrame(rng.normal(size=returns.shape), index=returns.index, columns=CURRENCIES)
    mu = mu.iloc[80:]
    config = construction.BookConfig(name="xs", max_leverage=20.0)
    expected = construction.run_book(config, mu, returns, 252.0)["daily"]
    actual = book.run_book(config, mu, returns, 252.0)["daily"]
    pd.testing.assert_frame_equal(actual, expected)


def test_old_rebalance_collapses_the_dollar_basket() -> None:
    """再現: 旧実装では外国 7 通貨のうち 4 通貨が恒久的に 0 になる。"""
    returns = _returns()
    mu = _dollar_mu(returns.index).iloc[80:]
    daily = book.run_book(_dollar_config(), mu, returns, 252.0)["daily"]
    zeros = [c for c in FOREIGN if (daily[f"x_{c}"].abs() < 1e-12).all()]
    assert len(zeros) >= 4


@pytest.fixture()
def factor_daily() -> pd.DataFrame:
    returns = _returns()
    mu = _dollar_mu(returns.index).iloc[80:]
    return book.run_book(_dollar_config(), mu, returns, 252.0, rebalance=book.factor_rebalance)[
        "daily"
    ]


def test_all_seven_foreign_currencies_receive_exposure(factor_daily) -> None:
    x = factor_daily[[f"x_{c}" for c in FOREIGN]]
    assert (x.abs() > 0).all().all()


def test_foreign_legs_are_equal_weight(factor_daily) -> None:
    x = factor_daily[[f"x_{c}" for c in FOREIGN]].to_numpy()
    assert np.allclose(x, x[:, [0]], atol=1e-12)


def test_usd_balances_the_basket(factor_daily) -> None:
    x = factor_daily[[f"x_{c}" for c in CURRENCIES]]
    assert np.allclose(x.sum(axis=1), 0.0, atol=1e-12)
    assert np.allclose(x["x_USD"], -x[[f"x_{c}" for c in FOREIGN]].sum(axis=1), atol=1e-12)


def test_usd_is_half_the_currency_gross(factor_daily) -> None:
    x = factor_daily[[f"x_{c}" for c in CURRENCIES]]
    share = x["x_USD"].abs() / x.abs().sum(axis=1)
    assert np.allclose(share, 0.5, atol=1e-12)


def test_band_never_deletes_a_currency_under_other_bands() -> None:
    returns = _returns()
    mu = _dollar_mu(returns.index, flip_every=17).iloc[80:]
    for band in (0.05, 0.10, 0.20):
        daily = book.run_book(
            _dollar_config(band), mu, returns, 252.0, rebalance=book.factor_rebalance
        )["daily"]
        assert (daily[[f"x_{c}" for c in FOREIGN]].abs() > 0).all().all()


def test_usd_direction_follows_the_signal(factor_daily) -> None:
    returns = _returns()
    mu = _dollar_mu(returns.index).iloc[80:]
    decided = mu["USD"].reindex(pd.DatetimeIndex(factor_daily["decision_day"])).to_numpy()
    assert (np.sign(factor_daily["x_USD"].to_numpy()) == np.sign(decided)).all()


def test_routing_preserves_the_factor_pnl(factor_daily) -> None:
    """pair book の P&L（split_map で pair へ振った notional × pair return）が x·e と一致する。"""
    currencies = CURRENCIES
    pairs = [f"{a}_{b}" for i, a in enumerate(currencies) for b in currencies[i + 1 :]]
    rng = np.random.default_rng(3)
    levels = np.exp(np.cumsum(rng.normal(0, 0.004, size=(3, len(currencies))), axis=0))
    prices = {
        p: levels[:, currencies.index(p.split("_")[1])]
        / levels[:, currencies.index(p.split("_")[0])]
        for p in pairs
    }
    pair_returns = np.log(pd.DataFrame(prices)).diff().iloc[1:]
    from scripts.research.top_five import panel

    excess = panel._currency_excess(pair_returns)["currency_excess_return"][currencies].to_numpy()[
        0
    ]
    x = factor_daily[[f"x_{c}" for c in currencies]].to_numpy()[0]
    notional = construction.split_map(tuple(pairs), tuple(currencies)) @ x
    assert float(x @ excess) == pytest.approx(
        float(notional @ pair_returns.to_numpy()[0]), abs=1e-14
    )


def test_factor_rebalance_trades_only_on_band_breach() -> None:
    target = np.array([0.5] + [-0.5 / 7] * 7)
    held = target.copy()
    assert np.array_equal(book.factor_rebalance(target, held, 0.10), held)
    flipped = -target
    assert np.array_equal(book.factor_rebalance(flipped, held, 0.10), flipped)


# ----------------------------------------------------------------------
# 経済会計（spot / spread / carry / markup）と凍結
# ----------------------------------------------------------------------
def test_total_economic_identity() -> None:
    from scripts.research.usd_factor_financing import execute

    returns = _returns()
    returns["USD"] = 0.0  # USD numeraire
    mu = _dollar_mu(returns.index).iloc[80:]
    rates = pd.DataFrame(0.0, index=returns.index, columns=CURRENCIES)
    rates["USD"] = 3.0
    panels = {"policy_contemporaneous": rates, "three_month_lagged": rates * 0.5}
    daily = execute.economic_book(execute._config(), mu, returns, panels)
    for basis in panels:
        for markup in (0.0, 0.005, 0.02):
            frame = execute.total(daily, basis, markup)
            expected = (
                daily["spot_gross"]
                + daily[f"carry_{basis}"]
                - daily["spread_cost"]
                - markup * daily["pair_notional_years"]
            )
            assert np.allclose(frame["net"], expected)
            pnl_sum = frame[[f"pnl_{c}" for c in CURRENCIES]].sum(axis=1)
            assert np.allclose(pnl_sum, frame["net"] + daily["spread_cost"])
    #: USD を持つ日は USD の金利 3% を受け取り、売る日は払う
    long_usd = daily["x_USD"] > 0
    assert (daily.loc[long_usd, "carry_policy_contemporaneous"] > 0).all()
    assert (daily.loc[~long_usd & (daily["x_USD"] < 0), "carry_policy_contemporaneous"] < 0).all()
    #: pair notional は外国脚の |x| の和 = |x_USD|
    days = (daily.index - pd.DatetimeIndex(daily["decision_day"])).days.to_numpy()
    assert np.allclose(daily["pair_notional_years"], daily["x_USD"].abs() * days / 365.0)


def test_usd_numeraire_returns_use_the_usd_pairs() -> None:
    from scripts.research.usd_factor_financing import execute

    index = pd.bdate_range("2020-01-06", periods=2)
    pairs = pd.DataFrame(
        {
            "EUR_USD": 0.01,
            "USD_JPY": 0.02,
            "GBP_USD": 0.0,
            "AUD_USD": 0.0,
            "NZD_USD": 0.0,
            "USD_CAD": 0.0,
            "USD_CHF": 0.0,
            "EUR_JPY": 9.9,
        },
        index=index,
    )
    out = execute.usd_numeraire_returns(pairs)
    assert out["EUR"].iloc[0] == pytest.approx(0.01)
    assert out["JPY"].iloc[0] == pytest.approx(-0.02)
    assert (out["USD"] == 0.0).all()


def test_policy_rate_is_used_only_after_its_month_ends(tmp_path, monkeypatch) -> None:
    from scripts.research.mechanism_redesign import signals
    from scripts.research.usd_factor_financing import execute

    stamps = pd.date_range("2005-01-01", "2005-06-01", freq="MS")
    for currency in CURRENCIES:
        values = np.where(stamps >= "2005-03-01", 5.0, 1.0)
        pd.DataFrame({"v": values}, index=stamps).to_parquet(
            tmp_path / f"policy_rate_bis_{currency.lower()}.parquet"
        )
    monkeypatch.setattr(signals, "DATA_DIR", tmp_path)
    monkeypatch.setattr(signals, "VERIFY_INPUT_HASHES", False)
    rates = execute.policy_rates_contemporaneous(pd.bdate_range("2005-02-01", "2005-04-29"))
    #: 3 月の月末値 5% は 3 月末から。3 月中は 2 月末の 1%
    assert (rates.loc["2005-03-01":"2005-03-30", "USD"] == 1.0).all()
    assert (rates.loc["2005-03-31":, "USD"] == 5.0).all()


def test_freeze_digest_matches_the_driver() -> None:
    from scripts.research.usd_factor_financing import driver, prereg

    assert prereg.freeze_digest() == driver.FROZEN_DIGEST
    closure = set(prereg.code_closure())
    for required in (
        "scripts/research/usd_factor_financing/book.py",
        "scripts/research/usd_factor_financing/execute.py",
        "scripts/research/mechanism_redesign/signals.py",
        "scripts/research/continuous_portfolio/construction.py",
    ):
        assert required in closure


def test_driver_refuses_when_a_record_exists(tmp_path, monkeypatch) -> None:
    from scripts.research.usd_factor_financing import driver

    record = tmp_path / "x.json"
    record.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(driver, "RECORD", record)
    with pytest.raises(SystemExit):
        driver.preflight()


def test_both_tracks_are_executed_together() -> None:
    from scripts.research.usd_factor_financing import prereg

    assert prereg.EXECUTION_ORDER == ("M15", "M16")
    assert prereg.BOOK_CONFIG["band"] == 0.10
    assert prereg.BOOK_CONFIG["mapping"] == "linear"
    assert prereg.BOOK_CONFIG["weight_cap"] == 0.5
    assert prereg.BOOK_CONFIG["neutralize_leading_factor"] is False


def test_driver_refuses_when_the_started_marker_exists(tmp_path, monkeypatch) -> None:
    from scripts.research.usd_factor_financing import driver

    started = tmp_path / "started.json"
    started.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(driver, "RECORD", tmp_path / "absent.json")
    monkeypatch.setattr(driver, "STARTED", started)
    with pytest.raises(SystemExit):
        driver.preflight()


def test_driver_refuses_on_a_digest_mismatch(tmp_path, monkeypatch) -> None:
    from scripts.research.usd_factor_financing import driver

    monkeypatch.setattr(driver, "RECORD", tmp_path / "a.json")
    monkeypatch.setattr(driver, "STARTED", tmp_path / "b.json")
    monkeypatch.setattr(driver, "FROZEN_DIGEST", "0" * 64)
    with pytest.raises(SystemExit):
        driver.preflight()
