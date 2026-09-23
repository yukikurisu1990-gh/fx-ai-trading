"""mechanism redesign cycle — universe・overlap audit・凍結・signal の契約。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.research.data_access import providers, request_policy
from scripts.research.mechanism_redesign import (
    driver,
    execute,
    prereg,
    prior_cycle,
    ranking,
    signals,
    universe,
)


def test_universe_has_at_least_twenty_complete_mechanisms() -> None:
    assert len(universe.MECHANISMS) >= 20
    for row in universe.MECHANISMS:
        for field in universe.TEMPLATE_FIELDS:
            assert field in row, (row["mechanism_id"], field)


def test_every_family_letter_a_to_j_is_reconsidered() -> None:
    assert ranking.coverage()["letters_covered"] == list("ABCDEFGHIJ")


def test_overlap_audit_covers_every_mechanism() -> None:
    assert ranking.coverage()["complete"]


def test_paid_mechanisms_are_never_selected() -> None:
    paid = {mid for mid, row in ranking.OVERLAP_AUDIT.items() if row["verdict"] == "EXCLUDED_PAID"}
    assert paid.isdisjoint(prereg.EXECUTION_ORDER)
    assert set(universe.PAID_DATA) <= paid


def test_execution_set_is_at_most_five_and_passed_the_audit() -> None:
    assert 1 <= len(prereg.EXECUTION_ORDER) <= 5
    for track in prereg.EXECUTION_ORDER:
        assert ranking.OVERLAP_AUDIT[track]["verdict"] in ranking.ADVANCING_VERDICTS


def test_driver_refuses_to_run_on_an_unfrozen_digest() -> None:
    assert prereg.freeze_digest() == driver.FROZEN_DIGEST


def test_freeze_covers_the_signal_source() -> None:
    payload = prereg._payload()
    assert payload["signals_source_sha256"] == prereg.signals_source_digest()


def test_prior_cycle_qualifier_is_recorded() -> None:
    assert prior_cycle.QUALIFIER == "POST_EXECUTION_SHARED_DEFECT_CORRECTED_EXPLORATORY_RESULT"
    assert "INVALID" in prior_cycle.RUNS["artifacts/research/next_five/development_run2.json"]


def test_dollar_mu_sign_and_basket() -> None:
    index = pd.bdate_range("2020-01-01", periods=5)
    sign = pd.Series([1.0, -1.0, np.nan, 0.0, 1.0], index=index)
    mu = signals._dollar_mu(sign, index)
    assert mu.loc[index[0], "USD"] == 1.0
    assert mu.loc[index[0], signals.FOREIGN].sum() == pytest.approx(-1.0)
    assert mu.loc[index[1], "USD"] == -1.0
    assert mu.loc[index[2]].isna().all()


def test_dollar_carry_sells_usd_when_foreign_rates_are_higher(tmp_path, monkeypatch) -> None:
    stamps = pd.date_range("2002-01-01", "2006-12-01", freq="MS")
    for currency in signals.CURRENCIES:
        level = 1.0 if currency == "USD" else 3.0
        pd.DataFrame({"v": level}, index=stamps).to_parquet(
            tmp_path / f"short_rate_3m_{currency.lower()}.parquet"
        )
    monkeypatch.setattr(signals, "DATA_DIR", tmp_path)
    monkeypatch.setattr(signals, "VERIFY_INPUT_HASHES", False)
    mu = signals.dollar_carry(pd.bdate_range("2003-01-01", "2006-06-30"))
    assert (mu["USD"].dropna() == -1.0).all()


def test_monthly_value_is_not_used_before_its_publication_lag(tmp_path, monkeypatch) -> None:
    stamps = pd.date_range("2002-01-01", "2006-12-01", freq="MS")
    for currency in signals.CURRENCIES:
        values = (
            np.where(stamps >= "2005-03-01", 5.0, 1.0)
            if currency == "USD"
            else np.full(len(stamps), 3.0)
        )
        pd.DataFrame({"v": values}, index=stamps).to_parquet(
            tmp_path / f"short_rate_3m_{currency.lower()}.parquet"
        )
    monkeypatch.setattr(signals, "DATA_DIR", tmp_path)
    monkeypatch.setattr(signals, "VERIFY_INPUT_HASHES", False)
    mu = signals.dollar_carry(pd.bdate_range("2005-01-01", "2005-06-30"))
    #: 2005-03 分は m+1 月末（2005-04-29 以降の営業日）まで使えない
    assert (mu.loc[:"2005-04-28", "USD"] == -1.0).all()
    assert (mu.loc["2005-05-02":, "USD"] == 1.0).all()


def test_load_refuses_a_protected_reference_period(tmp_path, monkeypatch) -> None:
    stamps = pd.to_datetime(["2016-04-01", "2016-05-01", "2016-06-01"])
    pd.DataFrame({"v": [1.0, 2.0, 3.0]}, index=stamps).to_parquet(tmp_path / "x.parquet")
    monkeypatch.setattr(signals, "DATA_DIR", tmp_path)
    monkeypatch.setattr(signals, "VERIFY_INPUT_HASHES", False)
    with pytest.raises(AssertionError):
        signals._load("x")


def test_m10_has_no_long_span() -> None:
    built = {
        "long": {
            "currency_excess_return": pd.DataFrame(index=pd.bdate_range("2000-01-03", periods=10))
        }
    }
    with pytest.raises(signals.SignalUnavailableError):
        signals.scores_for("M10", built, "long")


# ----------------------------------------------------------------------
# pre-alpha amendment
# ----------------------------------------------------------------------
def test_execution_set_has_five_tracks_including_m01() -> None:
    assert prereg.EXECUTION_ORDER == ("M15", "M11", "M16", "M01", "M10")
    assert prereg.FREEZE_AMENDMENT_PRE_ALPHA["digest_before"].startswith("2815e1dd")


def test_freeze_covers_the_code_closure_and_inputs() -> None:
    payload = prereg._payload()
    closure = set(payload["code_closure_sha256"])
    for required in (
        "scripts/research/mechanism_redesign/driver.py",
        "scripts/research/mechanism_redesign/signals.py",
        "scripts/research/mechanism_redesign/prereg.py",
        "scripts/research/continuous_portfolio/construction.py",
        "scripts/research/top_five/prereg.py",
        "scripts/research/top_five/signals.py",
        "scripts/research/next_five/signals.py",
    ):
        assert required in closure, required
    assert len(payload["input_manifest_sha256"]) == 64


def test_book_adds_carry_and_financing(monkeypatch) -> None:
    days = pd.bdate_range("2020-01-06", periods=3)
    frame = pd.DataFrame(
        {
            "decision_day": days[:-1],
            "gross": [0.001, 0.001],
            "cost": [0.0001, 0.0],
            **{f"x_{c}": [0.0, 0.0] for c in signals.CURRENCIES},
            **{f"pnl_{c}": [0.0, 0.0] for c in signals.CURRENCIES},
        },
        index=days[1:],
    )
    frame["x_USD"] = [-1.0, -1.0]
    frame["x_JPY"] = [1.0, 1.0]
    monkeypatch.setattr(execute.construction, "run_book", lambda *a, **k: {"daily": frame.copy()})
    rates = pd.DataFrame(0.0, index=days, columns=list(signals.CURRENCIES))
    rates["USD"] = 5.0
    daily = execute.book(execute._config("M15"), None, None, rates)
    #: USD を 1 単位売って JPY を 1 単位買う → 5% の金利差を払う（1 暦日）
    assert daily["carry"].iloc[0] == pytest.approx(-0.05 / 365)
    assert daily["financing"].iloc[0] == pytest.approx(2 * 0.0025 / 365)
    assert daily["net"].iloc[0] == pytest.approx(0.001 - 0.05 / 365 - 0.0001 - 2 * 0.0025 / 365)
    assert daily["spot_gross"].iloc[0] == pytest.approx(0.001)


def _fake_primary(net: float, n_eff: float) -> dict:
    return {
        "metrics": {
            "gross_sharpe": net + 0.1,
            "net_sharpe": net,
            "effective_independent_observations": n_eff,
        },
        "development_economics": {
            "label": "DEVELOPMENT_ECONOMICS_SUPPORTED",
            "core_satisfied": True,
            "checks": {"E5_breadth": True, "E6_concentration": True},
        },
        "null_diagnostic": {"label": "NULL_REJECTION_SUPPORTED", "observed_percentile": 0.99},
    }


def test_power_cap_limits_positive_verdicts() -> None:
    capped = execute.verdict("M15", _fake_primary(0.5, 5.0), None, {})
    assert capped["status"].endswith("POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE")
    assert capped["status_before_power_cap"].endswith("STRONG_DEVELOPMENT_CANDIDATE")
    free = execute.verdict("M16", _fake_primary(0.5, 27.0), None, {})
    assert free["status"].endswith("STRONG_DEVELOPMENT_CANDIDATE")


def test_not_evaluable_rename_gate_does_not_change_the_verdict() -> None:
    gates = {"M16_WITHIN_CYCLE": {"verdict": "NOT_EVALUABLE"}}
    out = execute.verdict("M15", _fake_primary(-0.1, 5.0), None, gates)
    assert out["status"].endswith("NOT_SUPPORTED_IN_SEEN_DEVELOPMENT")
    assert out["rename_gates_not_evaluable"] == ["M16_WITHIN_CYCLE"]
    renamed = execute.verdict("M15", _fake_primary(0.5, 5.0), None, {"x": {"verdict": "RENAME"}})
    assert renamed["status"].endswith("RENAME_OF_A_CLOSED_TRACK")


def test_yoy_whose_base_month_is_protected_is_dropped() -> None:
    clean = signals._yoy_base_is_clean
    assert not clean(pd.Timestamp("2022-04-01"), request_policy.MONTH)
    assert clean(pd.Timestamp("2022-05-01"), request_policy.MONTH)
    assert clean(pd.Timestamp("2016-05-01"), request_policy.MONTH)
    assert not clean(pd.Timestamp("2022-04-01"), request_policy.QUARTER)
    assert clean(pd.Timestamp("2022-07-01"), request_policy.QUARTER)


def test_gbp_unemployment_uses_a_longer_lag() -> None:
    assert signals.LAG_OVERRIDES[("unemployment", "GBP")] == signals.LAG_MONTHS["unemployment"] + 1


def test_load_refuses_a_parquet_whose_hash_is_not_recorded(tmp_path, monkeypatch) -> None:
    stamps = pd.to_datetime(["2016-04-01", "2016-05-01"])
    pd.DataFrame({"v": [1.0, 2.0]}, index=stamps).to_parquet(tmp_path / "x.parquet")
    monkeypatch.setattr(signals, "DATA_DIR", tmp_path)
    with pytest.raises(AssertionError):
        signals._load("x")


def test_alfred_refuses_an_unbounded_request() -> None:
    with pytest.raises(request_policy.ProtectedRequestError):
        providers.alfred("X", opt_in_env="NOPE")


def test_driver_refuses_when_the_record_exists(tmp_path, monkeypatch) -> None:
    record = tmp_path / "development.json"
    record.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(driver, "RECORD", record)
    with pytest.raises(SystemExit):
        driver.preflight()


def test_draw_count_cannot_be_overridden() -> None:
    import inspect

    assert "draws" not in inspect.signature(execute.null_diagnostic).parameters
    assert "permutation_draws" not in inspect.signature(execute.run_track).parameters


def test_gbp_three_month_average_touching_the_pool_is_dropped(tmp_path, monkeypatch) -> None:
    stamps = pd.date_range("2016-01-01", "2016-05-01", freq="MS").append(
        pd.date_range("2021-05-01", "2021-09-01", freq="MS")
    )
    pd.DataFrame({"v": 1.0}, index=stamps).to_parquet(tmp_path / "unemployment_gbp.parquet")
    pd.DataFrame({"v": 1.0}, index=stamps).to_parquet(tmp_path / "unemployment_cad.parquet")
    monkeypatch.setattr(signals, "DATA_DIR", tmp_path)
    monkeypatch.setattr(signals, "VERIFY_INPUT_HASHES", False)
    gbp, _ = signals._load_slot("unemployment", "GBP")
    #: 2016-04 / 05 は後ろ 2 か月で 2016-06 に、2021-05 / 06 は前 2 か月で 2021-04 に掛かる
    assert list(gbp.index.strftime("%Y-%m")) == [
        "2016-01",
        "2016-02",
        "2016-03",
        "2021-07",
        "2021-08",
        "2021-09",
    ]
    cad, _ = signals._load_slot("unemployment", "CAD")
    assert len(cad) == 10


@pytest.mark.parametrize("pair_set", ["all_28", "pairs_20"])
def test_carry_equals_the_pair_book_carry(pair_set) -> None:
    """x · operator(r) == (split_map @ x) · (r_base − r_quote)（spot と同じ pair book）。"""
    from scripts.research.continuous_portfolio import construction

    currencies = list(signals.CURRENCIES)
    if pair_set == "all_28":
        pairs = [f"{a}_{b}" for i, a in enumerate(currencies) for b in currencies[i + 1 :]]
    else:
        pairs = list(construction.PAIRS_20)
    rng = np.random.default_rng(0)
    index = pd.bdate_range("2020-01-06", periods=1)
    rates = pd.DataFrame([rng.uniform(0, 6, len(currencies))], index=index, columns=currencies)
    x = rng.normal(size=len(currencies))
    x -= x.mean()
    operated = execute.carry_operator(rates, pairs).iloc[0][currencies].to_numpy()
    d = np.array([rates.iloc[0][p.split("_")[0]] - rates.iloc[0][p.split("_")[1]] for p in pairs])
    notional = construction.split_map(tuple(pairs), tuple(currencies)) @ x
    assert float(x @ operated) == pytest.approx(float(notional @ d), abs=1e-12)


def test_nan_effective_observations_is_underpowered() -> None:
    out = execute.verdict("M15", _fake_primary(0.5, float("nan")), None, {})
    assert out["underpowered"]
    assert out["status"].endswith("POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE")


def test_driver_refuses_when_a_started_marker_exists(tmp_path, monkeypatch) -> None:
    started = tmp_path / "started.json"
    started.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(driver, "RECORD", tmp_path / "absent.json")
    monkeypatch.setattr(driver, "STARTED", started)
    with pytest.raises(SystemExit):
        driver.preflight()
