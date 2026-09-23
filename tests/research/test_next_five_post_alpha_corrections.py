"""alpha 後の共通基盤修正 C-1..C-5（`next_five.corrections`）を合成データで固定する。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.research.next_five import corrections, prereg, series_map, signals


def test_freeze_digest_is_not_touched_by_the_corrections() -> None:
    assert prereg.freeze_digest() == (
        "0bc7b198d1564fd1d2da8d4433762d3c0fb7c60bac7ae0526e26dbdae3e9715c"
    )


def test_c2_change_base_across_a_gap_is_missing() -> None:
    before = pd.date_range("2015-01-01", "2016-06-01", freq="MS")
    after = pd.date_range("2021-05-01", "2022-12-01", freq="MS")
    series = pd.Series(1.0, index=before.append(after))
    series[after] = 5.0
    changed = signals._change(series, 12, staleness_days=75)
    #: 空白の直後 12 か月は基準値が 2016 年にしか無いので欠損
    assert changed["2021-05-01":"2022-04-01"].isna().all()
    #: 基準値が空白の後にある月は計算される
    assert changed["2022-05-01"] == pytest.approx(0.0)
    #: 空白の前は普通に計算される
    assert changed["2016-01-01"] == pytest.approx(0.0)


def test_c2_weekly_base_within_staleness_is_used() -> None:
    index = pd.date_range("2020-01-01", "2022-01-01", freq="W-WED")
    series = pd.Series(np.arange(len(index), dtype=float), index=index)
    changed = signals._change(series, 12, staleness_days=75)
    assert changed.iloc[-1] == pytest.approx(52.0, abs=1.0)


def test_c3_month_end_offset_lands_on_month_end() -> None:
    series = pd.Series(
        [1.0, 2.0, 3.0], index=pd.to_datetime(["2023-02-01", "2023-06-01", "2023-11-01"])
    )
    days = pd.bdate_range("2023-01-01", "2024-03-01")
    aligned = signals._align(series, days, vintage_offset_months=2, staleness_days=400)
    first = aligned.dropna().index
    #: 2 月分は 4 月 30 日（日曜）以降の最初の営業日から。4 月 28 日（金）には使えない
    assert pd.Timestamp("2023-04-28") not in first
    assert first[0] == pd.Timestamp("2023-05-01")
    assert aligned["2023-08-31"] == 2.0
    assert aligned["2023-08-30"] == 1.0
    assert aligned["2024-01-30"] == 2.0
    assert aligned["2024-01-31"] == 3.0


def test_c4_protected_reference_periods() -> None:
    protected = signals._reference_period_is_protected
    assert protected(pd.Timestamp("2016-06-01"), pd.Timestamp("2016-06-30"))
    assert protected(pd.Timestamp("2021-04-01"), pd.Timestamp("2021-04-30"))
    assert protected(pd.Timestamp("2025-12-01"), pd.Timestamp("2025-12-31"))
    assert not protected(pd.Timestamp("2016-05-01"), pd.Timestamp("2016-05-31"))
    assert not protected(pd.Timestamp("2021-05-01"), pd.Timestamp("2021-05-31"))
    assert not protected(pd.Timestamp("2025-11-01"), pd.Timestamp("2025-11-30"))


def test_c4_load_drops_monthly_stamps_whose_period_is_protected(tmp_path, monkeypatch) -> None:
    stamps = pd.to_datetime(["2016-05-01", "2016-06-01", "2021-05-01", "2025-11-01", "2025-12-01"])
    frame = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 5.0]}, index=stamps)
    frame.to_parquet(tmp_path / "x.parquet")
    monkeypatch.setattr(signals, "DATA_DIR", tmp_path)
    kept = signals._load("x", monthly=True)
    assert list(kept.index.strftime("%Y-%m")) == ["2016-05", "2021-05", "2025-11"]
    #: 日次・週次は stamp が観測時点なので落とさない
    assert len(signals._load("x")) == 5


def _toy_scorer(index, overrides=None):
    frame = pd.DataFrame(np.nan, index=index, columns=list(signals.CURRENCIES))
    frame.iloc[:, :3] = 1.0
    frame.iloc[:, 3] = -1.0
    #: 4 列目は途中で終わる。3 列目は途中から欠ける
    frame.iloc[10:, 3] = np.nan
    frame.iloc[20:, 2] = np.nan
    return frame


def test_c1_scores_for_does_not_carry_stale_scores(monkeypatch) -> None:
    index = pd.bdate_range("2022-01-03", periods=40)
    built = {"recent": {"currency_excess_return": pd.DataFrame(index=index)}}
    monkeypatch.setitem(signals.SCORERS, "U1", _toy_scorer)
    scores = signals.scores_for("U1", built, "recent")
    #: 4 列目は欠けた後 0（持ち越さない）
    assert (scores.iloc[10:, 3] == 0.0).all()
    #: 3 通貨未満になった日（20 日目以降）は残さない
    assert len(scores) == 20


def test_o3_no_columns_returns_no_rows(monkeypatch) -> None:
    index = pd.bdate_range("2022-01-03", periods=40)
    built = {"long": {"currency_excess_return": pd.DataFrame(index=index)}}
    monkeypatch.setitem(
        signals.SCORERS,
        "U1",
        lambda idx, overrides=None: pd.DataFrame(np.nan, index=idx, columns=["USD"]),
    )
    assert len(signals.scores_for("U1", built, "long")) == 0


def test_c5_weekly_lags_follow_publication_date() -> None:
    assert signals._lag_kwargs("U2", "USD") == {"lag_business_days": 3}
    assert signals._lag_kwargs("U2", "EUR") == {"lag_business_days": 4}
    #: 凍結した series_map は書き換えていない
    assert series_map.SERIES_MAP["U2"]["EUR"]["lag"] == {"kind": "business_days", "n": 2}
    #: 月次は凍結どおり
    assert signals._lag_kwargs("U2", "JPY") == {"vintage_offset_months": 2}


def test_run2_is_recorded_invalid_and_every_track_is_covered() -> None:
    assert any("development_run2.json" in k for k in corrections.INVALIDATED_RECORDS)
    touched = {t for c in corrections.POST_ALPHA_CORRECTIONS.values() for t in c["tracks"]}
    assert touched == set(prereg.EXECUTION_ORDER)
    assert len(corrections.corrections_digest()) == 64
