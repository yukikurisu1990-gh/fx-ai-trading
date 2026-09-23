"""data_access 層を固定する。**network には出ない**（偽の opener を渡す）。

第 2 裁定 §9 / §12 / §13 / §15 の要件を押さえる:

- 失敗は 10 分類のどれかに落ち、**TIMEOUT を PROVIDER_UNAVAILABLE と書かない**
- HTTP 200 でも HTML / login / 空 / 壊れた本文は成功にしない
- retry は環境側の一過性の失敗だけ、上限付き、provider の status は再試行しない
- 意味検証は前 cycle の取り違えを弾く
  （BoC V36612 = Treasury Bills、ECB A050100 = 主要リファイナンス・オペ）
"""

from __future__ import annotations

import io
import urllib.error

import pandas as pd
import pytest

from scripts.research.data_access import fetch as F  # noqa: N812
from scripts.research.data_access import mapping as M  # noqa: N812
from scripts.research.next_five import series_map, signals

ENV = "DATA_ACCESS_TEST_OPT_IN"


class _Response(io.BytesIO):
    def __enter__(self):  # noqa: ANN204
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _opener(payloads: list[object]):
    calls: list[str] = []

    def opener(request, timeout, context):  # noqa: ANN001, ANN202, ARG001
        calls.append(request.full_url)
        item = payloads[min(len(calls) - 1, len(payloads) - 1)]
        if isinstance(item, BaseException):
            raise item
        return _Response(item)

    opener.calls = calls  # type: ignore[attr-defined]
    return opener


@pytest.fixture(autouse=True)
def _opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, "1")


def _fetch(payloads: list[object], expect: str = "csv", attempts: int = 3):
    opener = _opener(payloads)
    result = F.fetch(
        "https://example.invalid/x",
        opt_in_env=ENV,
        expect=expect,
        limits=F.Limits(timeout_seconds=1, attempts=attempts, backoff_seconds=0.0),
        sleep=lambda _s: None,
        opener=opener,
    )
    return result, opener.calls


class TestTheTaxonomyIsTheOneTheRulingNamed:
    def test_exactly_the_ten_classes(self) -> None:
        assert set(F.CLASSES) == {
            "HTTP_STATUS",
            "TIMEOUT",
            "DNS",
            "TLS",
            "CONTENT_INVALID",
            "PARSER_FAILURE",
            "SERIES_NOT_FOUND",
            "SEMANTIC_MISMATCH",
            "PROVIDER_UNAVAILABLE",
            "ENVIRONMENT_RETRIEVAL_FAILURE",
        }

    def test_an_unregistered_class_cannot_be_raised(self) -> None:
        with pytest.raises(ValueError):
            F.FetchError("LOOKS_BROKEN", "x")

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (urllib.error.HTTPError("u", 404, "nf", {}, None), "SERIES_NOT_FOUND"),
            (urllib.error.HTTPError("u", 403, "f", {}, None), "HTTP_STATUS"),
            (urllib.error.HTTPError("u", 400, "b", {}, None), "HTTP_STATUS"),
            (urllib.error.HTTPError("u", 503, "u", {}, None), "PROVIDER_UNAVAILABLE"),
            (TimeoutError("The read operation timed out"), "TIMEOUT"),
            (urllib.error.URLError("[Errno 11001] getaddrinfo failed"), "DNS"),
            (urllib.error.URLError("_ssl.c:993: The handshake operation timed out"), "TIMEOUT"),
            (urllib.error.URLError("CERTIFICATE_VERIFY_FAILED"), "TLS"),
            (urllib.error.URLError("connection refused"), "ENVIRONMENT_RETRIEVAL_FAILURE"),
        ],
    )
    def test_each_error_lands_in_its_class(self, error: BaseException, expected: str) -> None:
        assert F.classify(error)[0] == expected

    def test_a_timeout_is_never_called_provider_unavailable(self) -> None:
        assert F.classify(TimeoutError("timed out"))[0] != F.PROVIDER_UNAVAILABLE
        assert F.TIMEOUT in F.ENVIRONMENT_SIDE
        assert F.PROVIDER_UNAVAILABLE not in F.ENVIRONMENT_SIDE


class TestA200IsNotAutomaticallyData:
    @pytest.mark.parametrize(
        ("payload", "expect"),
        [
            (b"<!DOCTYPE html><html><body>Not found</body></html>", "csv"),
            (b"<html><body>error</body></html>", "json"),
            (b"", "csv"),
            (b"   \n  ", "json"),
            (b"no delimiters here", "csv"),
            (b"not json", "json"),
            (b"not a zip", "zip"),
            (b'{"a": 1}', "html"),
            (b"<html><form>Sign in<input type=password></form></html>", "html"),
        ],
    )
    def test_invalid_content_is_rejected(self, payload: bytes, expect: str) -> None:
        with pytest.raises(F.FetchError) as caught:
            F.validate_content(payload, expect=expect)
        assert caught.value.outcome == F.CONTENT_INVALID

    def test_a_bom_prefixed_json_is_valid(self) -> None:
        """Fed の press JSON は BOM 付き。**初版はこれを弾いていた。**"""
        F.validate_content('﻿[{"d": 1}]'.encode(), expect="json")

    def test_an_html_fragment_without_html_tag_is_valid_html(self) -> None:
        """ECB の年別一覧は <html> を持たない断片。"""
        F.validate_content(
            b"<dt>2023</dt><dd><a href='/x'>Monetary policy decisions</a></dd>", expect="html"
        )


class TestRetriesAreBoundedAndOnlyForTheEnvironment:
    def test_a_provider_status_is_not_retried(self) -> None:
        result, calls = _fetch([urllib.error.HTTPError("u", 404, "nf", {}, None)])
        assert result.outcome == F.SERIES_NOT_FOUND
        assert len(calls) == 1

    def test_content_invalid_is_not_retried(self) -> None:
        result, calls = _fetch([b"<html>err</html>"])
        assert result.outcome == F.CONTENT_INVALID
        assert len(calls) == 1

    def test_timeouts_are_retried_up_to_the_limit_and_no_further(self) -> None:
        result, calls = _fetch([TimeoutError("timed out")], attempts=3)
        assert result.outcome == F.TIMEOUT
        assert len(calls) == 3

    def test_a_transient_failure_then_success(self) -> None:
        result, calls = _fetch([TimeoutError("timed out"), b"a,b\n1,2\n"])
        assert result.ok
        assert len(calls) == 2
        assert result.content_hash

    def test_the_opt_in_is_checked_on_every_attempt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ENV)
        with pytest.raises(Exception):  # noqa: B017 - acquisition_safety の拒否例外
            _fetch([b"a,b\n1,2\n"])


class TestSemanticValidationCatchesThePreviousMistakes:
    def test_boc_treasury_bills_is_not_total_assets(self) -> None:
        with pytest.raises(F.FetchError) as caught:
            M.check_semantics(
                "CB_TOTAL_ASSETS",
                "Treasury Bills — Assets - Government of Canada direct and guaranteed securities",
            )
        assert caught.value.outcome == F.SEMANTIC_MISMATCH

    def test_ecb_main_refinancing_is_not_total_assets(self) -> None:
        with pytest.raises(F.FetchError):
            M.check_semantics("CB_TOTAL_ASSETS", "Main refinancing operation - Eurosystem")

    def test_a_district_total_is_not_the_system_total(self) -> None:
        with pytest.raises(F.FetchError):
            M.check_semantics(
                "CB_TOTAL_ASSETS",
                "Assets: Total Assets: Total assets: District 2: New York: Wednesday level",
            )

    def test_bank_reserve_balances_are_not_fx_reserves(self) -> None:
        with pytest.raises(F.FetchError):
            M.check_semantics("FX_RESERVES", "Reserve balances with Federal Reserve Banks")

    def test_an_ig_spread_is_not_a_high_yield_spread(self) -> None:
        with pytest.raises(F.FetchError):
            M.check_semantics(
                "HY_CREDIT_SPREAD",
                "ICE BofA US Corporate Index Option-Adjusted Spread investment grade",
            )

    @pytest.mark.parametrize(
        ("variable", "title"),
        [
            ("CB_TOTAL_ASSETS", "Assets: Total Assets: Total assets: Wednesday level"),
            (
                "CB_TOTAL_ASSETS",
                "Bank of Japan Accounts/Assets/Total (Assets, or Liabilities and Net Assets) (s)",
            ),
            ("CB_TOTAL_ASSETS", "Assets / Total"),
            ("CB_TOTAL_ASSETS", "Total assets — Assets"),
            ("CB_TOTAL_ASSETS", "Central Bank Assets for Euro Area (11-19 Countries)"),
            ("FX_RESERVES", "Reserves Excluding Gold for Japan"),
            (
                "GOODS_TRADE_BALANCE",
                "International Merchandise Trade Statistics: Trade Balance: Commodities for Japan",
            ),
            ("HY_CREDIT_SPREAD", "ICE BofA US High Yield Index Option-Adjusted Spread"),
        ],
    )
    def test_the_mapped_titles_pass(self, variable: str, title: str) -> None:
        M.check_semantics(variable, title)


class TestTheMappingIsComplete:
    def test_every_series_carries_the_audit_fields(self) -> None:
        for track, rows in series_map.SERIES_MAP.items():
            for currency, spec in rows.items():
                for field in (
                    "provider",
                    "tier",
                    "fetcher",
                    "args",
                    "lag",
                    "revision",
                    "why_this_route",
                ):
                    assert spec.get(field) not in (None, ""), f"{track}/{currency}.{field}"
                assert spec["tier"] in M.TIERS

    def test_every_track_meets_the_breadth_floor_on_paper(self) -> None:
        """最低 3 通貨（U5 は 1 本の spread を凍結 beta で 8 通貨へ射影する）。"""
        for track in ("U1", "U2", "U4"):
            assert len(series_map.mapped_currencies(track)) >= 3, track

    def test_unmapped_currencies_say_why_and_are_not_substituted(self) -> None:
        assert "semantic substitution" in series_map.NOT_MAPPED["U4"]["CHF"]

    def test_monthly_series_never_use_a_business_day_lag(self) -> None:
        """月初の日付に営業日の lag を当てると look-ahead になる（P-2）。"""
        monthly = {("U2", "JPY"), ("U2", "CHF"), ("U2", "CAD")}
        for track, currency in monthly:
            assert series_map.SERIES_MAP[track][currency]["lag"]["kind"] == "month_end_offset"
        for currency in series_map.mapped_currencies("U1"):
            assert series_map.SERIES_MAP["U1"][currency]["lag"]["kind"] == "month_end_offset"


class TestTheChangeWindowIsInMonths:
    def test_weekly_change_reaches_back_twelve_months_not_twelve_weeks(self) -> None:
        weekly = pd.Series(
            range(1, 200), index=pd.date_range("2000-01-05", periods=199, freq="W-WED"), dtype=float
        )
        changed = signals._change(weekly, 12)
        day = pd.Timestamp("2002-01-02")
        prior = weekly[weekly.index <= day - pd.DateOffset(months=12)].iloc[-1]
        assert changed.loc[day] == weekly.loc[day] - prior
        assert changed.loc[day] != weekly.loc[day] - weekly.shift(12).loc[day]

    def test_monthly_change_is_unchanged(self) -> None:
        monthly = pd.Series(
            range(1, 60), index=pd.date_range("2000-01-01", periods=59, freq="MS"), dtype=float
        )
        pd.testing.assert_series_equal(
            signals._change(monthly, 12).dropna(),
            (monthly - monthly.shift(12)).dropna(),
            check_names=False,
        )

    def test_it_does_not_extrapolate_before_the_first_observation(self) -> None:
        monthly = pd.Series(
            range(1, 30), index=pd.date_range("2000-01-01", periods=29, freq="MS"), dtype=float
        )
        assert signals._change(monthly, 12).iloc[:12].isna().all()


class TestTheForbiddenWordsWorkOnTheirOwn:
    """**必須語を満たしたうえで、禁止語だけが効く**ケース。

    前 cycle の取り違えた title は必須語も満たしていなかったので、禁止語が無くても弾かれた。
    それでは禁止語そのものが効いているかが分からない。
    """

    def test_treasury_bills_is_rejected_even_when_total_asset_appears(self) -> None:
        with pytest.raises(F.FetchError):
            M.check_semantics("CB_TOTAL_ASSETS", "Total assets held as Treasury Bills")

    def test_refinancing_is_rejected_even_when_total_asset_appears(self) -> None:
        with pytest.raises(F.FetchError):
            M.check_semantics("CB_TOTAL_ASSETS", "Total asset side: main refinancing operations")

    def test_reserve_balances_are_rejected_even_when_reserve_assets_appears(self) -> None:
        with pytest.raises(F.FetchError):
            M.check_semantics(
                "FX_RESERVES", "Reserve assets: reserve balances with Federal Reserve Banks"
            )

    def test_an_ig_label_is_rejected_even_when_high_yield_spread_appears(self) -> None:
        with pytest.raises(F.FetchError):
            M.check_semantics("HY_CREDIT_SPREAD", "High yield vs investment grade spread")


class TestHtmlIsRejectedEvenWhenItLooksLikeTheExpectedShape:
    """形の検査だけなら通ってしまう HTML。**HTML 判定そのものが効いていること。**"""

    def test_an_html_error_page_with_commas_is_not_csv(self) -> None:
        with pytest.raises(F.FetchError) as caught:
            F.validate_content(
                b"<!DOCTYPE html><html><body>Error, not found; try again</body></html>",
                expect="csv",
            )
        assert caught.value.outcome == F.CONTENT_INVALID

    def test_an_html_page_is_not_xml_even_though_it_starts_with_a_bracket(self) -> None:
        with pytest.raises(F.FetchError) as caught:
            F.validate_content(b"<html><body>Service notice</body></html>", expect="xml")
        assert caught.value.outcome == F.CONTENT_INVALID
