"""mechanism redesign cycle — universe・overlap audit・凍結・signal の契約。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.research.mechanism_redesign import (
    driver,
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
    mu = signals.dollar_carry(pd.bdate_range("2005-01-01", "2005-06-30"))
    #: 2005-03 分は m+1 月末（2005-04-29 以降の営業日）まで使えない
    assert (mu.loc[:"2005-04-28", "USD"] == -1.0).all()
    assert (mu.loc["2005-05-02":, "USD"] == 1.0).all()


def test_load_refuses_a_protected_reference_period(tmp_path, monkeypatch) -> None:
    stamps = pd.to_datetime(["2016-04-01", "2016-05-01", "2016-06-01"])
    pd.DataFrame({"v": [1.0, 2.0, 3.0]}, index=stamps).to_parquet(tmp_path / "x.parquet")
    monkeypatch.setattr(signals, "DATA_DIR", tmp_path)
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
