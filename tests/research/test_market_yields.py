"""T-R: the sources are official, the lag cannot leak, and the universe is what the audit fixed.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Reads committed records only. No network, no market data.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from scripts.research.market_yields import CURRENCIES, OUTCOMES, integrity, prereg, sources

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scripts/research/market_yields"
RECORDS = ROOT / "artifacts/research/market_yields"


@pytest.fixture(scope="module")
def integrity_record() -> dict[str, Any]:
    return json.loads((RECORDS / "integrity.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def acquisition_record() -> dict[str, Any]:
    return json.loads((RECORDS / "acquisition.json").read_text(encoding="utf-8"))


class TestTheSources:
    def test_every_primary_source_is_an_official_body(self) -> None:
        for source in sources.primary():
            assert source.currency in CURRENCIES
            body = source.body.lower()
            assert any(
                word in body for word in ("bank", "treasury", "ministry", "reserve", "bundesbank")
            ), source.body
            assert source.url.startswith("https://")

    def test_no_paid_or_authenticated_or_fx_source(self) -> None:
        for source in sources.SOURCES:
            url = source.url.lower()
            assert "api_key" not in url and "apikey" not in url and "token" not in url
            assert "fx" not in url and "exchange-rate" not in url and "eurofxref" not in url
            assert "bloomberg" not in url and "refinitiv" not in url

    def test_publication_times_are_recorded_as_unconfirmed(self) -> None:
        for source in sources.primary():
            assert "unconfirmed" in source.publication_time

    def test_the_unreachable_sources_are_declared_not_hidden(self) -> None:
        unreachable = {s.currency for s in sources.primary() if not s.reachable}
        assert "AUD" in unreachable


class TestTheAvailabilityRule:
    def _series(self) -> pd.DataFrame:
        days = pd.bdate_range("2021-01-01", "2021-03-31")
        return pd.DataFrame({"date": days, "yield_percent": range(len(days))})

    def test_a_value_never_reaches_its_own_day(self) -> None:
        frame = self._series()
        days = pd.DatetimeIndex(frame["date"])
        check = integrity.leak_check(frame, days)
        assert check["same_or_future_dated_values"] == 0
        assert check["min_age_days"] >= 1

    def test_the_carried_value_is_the_previous_publication(self) -> None:
        frame = self._series()
        days = pd.DatetimeIndex(frame["date"])
        carried = integrity.available_from(frame, days)
        expected = frame.set_index("date")["yield_percent"].shift(1)
        pd.testing.assert_series_equal(
            carried.astype(float), expected.astype(float), check_names=False
        )

    def test_a_holiday_carries_forward_but_ages(self) -> None:
        frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2021-01-04", "2021-01-05", "2021-01-12"]),
                "yield_percent": [1.0, 2.0, 3.0],
            }
        )
        days = pd.DatetimeIndex(pd.bdate_range("2021-01-05", "2021-01-13"))
        carried = integrity.available_from(frame, days)
        assert carried.loc[pd.Timestamp("2021-01-06")] == 2.0
        assert carried.loc[pd.Timestamp("2021-01-12")] == 2.0
        assert integrity.leak_check(frame, days)["max_age_days"] >= 5

    def test_the_lag_is_one_trading_day(self) -> None:
        assert integrity.AVAILABILITY_LAG_TRADING_DAYS == 1


class TestTheGate:
    def _audit(self, **overrides: Any) -> dict[str, Any]:
        base = {
            "covers_first_day": True,
            "covers_last_day": True,
            "gaps_over_five_business_days": 0,
            "longest_unchanged_run": 3,
            "duplicate_dates": 0,
            "min_value": 0.5,
            "max_value": 5.0,
        }
        return {**base, **overrides}

    def _leak(self, **overrides: Any) -> dict[str, Any]:
        return {
            "observations_used": 1000,
            "max_age_days": 4,
            "same_or_future_dated_values": 0,
            **overrides,
        }

    def test_a_clean_series_passes(self) -> None:
        assert integrity.verdict(self._audit(), 1000, self._leak())["decision_grade"]

    @pytest.mark.parametrize(
        ("audit_change", "leak_change"),
        [
            ({"covers_last_day": False}, {}),
            ({"gaps_over_five_business_days": 1}, {}),
            ({"longest_unchanged_run": 40}, {}),
            ({"duplicate_dates": 2}, {}),
            ({"max_value": 99.0}, {}),
            ({}, {"observations_used": 900}),
            ({}, {"max_age_days": 200}),
            ({}, {"same_or_future_dated_values": 1}),
        ],
    )
    def test_each_defect_fails_with_a_reason(
        self, audit_change: dict[str, Any], leak_change: dict[str, Any]
    ) -> None:
        result = integrity.verdict(self._audit(**audit_change), 1000, self._leak(**leak_change))
        assert not result["decision_grade"]
        assert result["reasons"]


class TestTheRecordedAudit:
    def test_the_universe_is_what_the_audit_fixed(self, integrity_record: dict[str, Any]) -> None:
        assert tuple(integrity_record["decision_grade_universe"]) == prereg.UNIVERSE
        assert set(prereg.EXCLUDED) == set(integrity_record["excluded"])
        for currency in prereg.EXCLUDED:
            assert integrity_record["currencies"][currency]["decision_grade"] is False

    def test_every_included_currency_passed_every_condition(
        self, integrity_record: dict[str, Any]
    ) -> None:
        for currency in prereg.UNIVERSE:
            row = integrity_record["currencies"][currency]
            assert row["decision_grade"] and not row["reasons"]
            assert row["leak_check"]["same_or_future_dated_values"] == 0
            assert row["leak_check"]["min_age_days"] >= 1
            assert (
                row["availability_on_decision_days"]
                >= integrity.GATE["min_availability_on_decision_days"]
            )

    def test_the_two_euro_sources_agree(self, integrity_record: dict[str, Any]) -> None:
        check = integrity_record["eur_cross_check_bundesbank_vs_ecb"]
        assert check["overlapping_days"] > 1000
        assert check["level_correlation"] > 0.99
        assert check["mean_absolute_difference_pp"] < 0.05
        #: the one-day change is genuinely source-dependent — different end-of-day snapshots
        #: and 0.01pp rounding — while the five-day change the signal uses agrees far better
        assert check["daily_change_correlation"] > 0.6
        assert check["five_day_change_correlation"] > check["daily_change_correlation"]

    def test_the_audit_span_matches_the_prereg(self, integrity_record: dict[str, Any]) -> None:
        span = integrity_record["decision_span"]
        assert span["first"] == prereg.DECISION_SPAN["first"]
        assert span["last"] == prereg.DECISION_SPAN["last"]
        assert span["fx_trading_days"] == prereg.DECISION_DAYS

    def test_the_audit_used_only_the_calendar(self, integrity_record: dict[str, Any]) -> None:
        assert "trading calendar only" in integrity_record["market_data_read"]

    def test_no_fx_series_was_acquired(self, acquisition_record: dict[str, Any]) -> None:
        assert acquisition_record["no_fx_series_requested"] is True
        for name in acquisition_record["series"]:
            assert name in {*CURRENCIES, "EUR_ECB_CROSS_CHECK"}


class TestThePrereg:
    def test_it_declares_one_unfitted_rule_and_two_horizons(self) -> None:
        assert "unfitted" in prereg.PREREG["stage"]
        assert prereg.PREREG["signal"]["lookback_days"] == 5
        assert prereg.PREREG["signal"]["sign_frozen"] is True
        assert prereg.PREREG["targets"]["horizons_days"] == [5, 20]
        assert set(prereg.PREREG["books"]) >= {"A", "B", "C"}

    def test_the_screen_is_exhaustive_and_returns_to_human(self) -> None:
        screen = prereg.PREREG["screen"]
        assert "any result that fails even one advance condition" in screen["stop"]
        assert screen["no_automatic_progress_to_fresh"] is True
        assert screen["status_if_advance"] in OUTCOMES
        assert screen["status_if_stop"] in OUTCOMES
        assert screen["status_if_data_fails"] in OUTCOMES

    def test_the_book_reuses_the_layer_but_not_the_alpha(self) -> None:
        assert prereg.PREREG["book_configuration"]["track_1_alpha_model_reused"] is False
        assert prereg.PREREG["book_configuration"]["leverage_cap"].startswith("none")

    def test_the_feasibility_is_signal_blind_and_states_the_power(self) -> None:
        feasibility = prereg.feasibility()
        assert feasibility["effective_breadth_assumed"] == prereg.EFFECTIVE_BREADTH
        assert feasibility["detectable_net_sharpe_at_80pct_power"] > 1.0
        assert "not be decision-grade" in feasibility["note"]

    def test_the_module_holds_no_result(self) -> None:
        source = (PACKAGE / "prereg.py").read_text(encoding="utf-8").lower()
        for word in ("sharpe = ", "ic = ", "observed", "we found", "the result was"):
            assert word not in source


class TestTheBoundaries:
    ALLOWED_TOP_LEVEL = {
        "__future__",
        "contextlib",
        "dataclasses",
        "typing",
        "json",
        "math",
        "sys",
        "os",
        "io",
        "ssl",
        "zipfile",
        "hashlib",
        "datetime",
        "pathlib",
        "shutil",
        "subprocess",
        "tempfile",
        "urllib.request",
        "xml.etree",
        "xml.etree.ElementTree",
        "pandas",
        "numpy",
        "scipy",
        "scripts.research.market_yields",
        "scripts.research.model_learning",
        "scripts.research.continuous_portfolio",
        "scripts.research.edge_sources",
    }

    def test_the_package_imports_nothing_unexpected(self) -> None:
        for path in PACKAGE.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for name in names:
                    assert name in self.ALLOWED_TOP_LEVEL, (path.name, name)

    def test_only_acquire_touches_the_network_and_only_on_opt_in(self) -> None:
        for path in PACKAGE.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            if path.name == "acquire.py":
                assert 'os.environ.get(OPT_IN_ENV) != "1"' in source
                assert 'if __name__ == "__main__"' in source
                continue
            for word in ("urlopen", "urllib", "requests", "curl"):
                assert word not in source, (path.name, word)

    def test_no_module_reads_a_protected_span(self) -> None:
        for path in PACKAGE.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "2016-06-02" not in source
            assert "2021-04-25" not in source
            for word in ("historical_oos", "dead_window", "forward_epoch"):
                assert word not in source


DOC = ROOT / "docs/research/m15_track_r_market_yield_repricing.md"


@pytest.fixture(scope="module")
def development() -> dict[str, Any]:
    return json.loads((RECORDS / "development.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def document() -> str:
    return DOC.read_text(encoding="utf-8")


class TestTheDevelopmentRun:
    def test_it_ran_what_the_prereg_froze(self, development: dict[str, Any]) -> None:
        assert development["universe"] == list(prereg.UNIVERSE)
        assert development["prereg"]["signal"]["lookback_days"] == 5
        assert set(development["books"]) == {"A_yield_repricing", "B_fx_momentum", "C_residualised"}
        assert development["span"]["first"] == prereg.DECISION_SPAN["first"]
        assert development["protected_spans_read"] is False

    def test_the_screen_is_applied_exactly_and_stops(self, development: dict[str, Any]) -> None:
        screen = development["screen"]
        books = development["books"]
        a = books["A_yield_repricing"]["summary"]
        assert screen["conditions"]["A gross Sharpe > 0"] is (a["gross_sharpe"] > 0)
        assert screen["conditions"]["A net Sharpe >= 0.3"] is (a["net_sharpe"] >= 0.3)
        assert screen["decision"] == ("advance" if all(screen["conditions"].values()) else "stop")
        assert screen["decision"] == "stop"
        assert screen["verdict"] == "MARKET_YIELD_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        assert screen["decision_grade"] is False

    def test_cost_is_what_separates_gross_from_net(self, development: dict[str, Any]) -> None:
        for name, book in development["books"].items():
            summary = book["summary"]
            drag = summary["gross_sharpe"] - summary["net_sharpe"]
            assert drag > 0.9, name
            assert summary["turnover_round_trips_per_year_per_unit_gross"] > 60.0, name
            assert summary["annual_cost"] > 0.09, name

    def test_the_observed_ic_is_below_what_the_design_needed(
        self, development: dict[str, Any]
    ) -> None:
        needed = development["feasibility_before_the_run"]["rows"]["half_life_5d"][
            "required_daily_ic_for_net_0_3"
        ]
        for name in ("A_yield_repricing", "C_residualised"):
            assert development["books"][name]["ic"]["5d"] < needed, name

    def test_the_outside_universe_exposure_is_measured_not_hidden(
        self, development: dict[str, Any]
    ) -> None:
        outside = development["books"]["A_yield_repricing"]["outside_universe_exposure"]
        assert set(outside["currencies"]) == set(prereg.EXCLUDED)
        assert outside["share_of_days_with_any_exposure"] > 0
        assert abs(outside["cumulative_pnl_total"]) < 0.05

    def test_leverage_cannot_rescue_a_negative_net(self, development: dict[str, Any]) -> None:
        assert development["leverage_and_margin_at_10pct_vol"]["annual_net_return"] < 0

    def test_every_book_is_underpowered_by_the_prereg_s_own_number(
        self, development: dict[str, Any]
    ) -> None:
        power = development["feasibility_before_the_run"]["detectable_net_sharpe_at_80pct_power"]
        assert power > 1.0
        for book in development["books"].values():
            assert abs(book["summary"]["gross_sharpe"]) < power


class TestTheResultsDocument:
    NUMBERS = (
        ("A_yield_repricing", "gross_sharpe", "+0.144"),
        ("A_yield_repricing", "net_sharpe", "−0.921"),
        ("B_fx_momentum", "net_sharpe", "−0.947"),
        ("C_residualised", "gross_sharpe", "+0.772"),
        ("C_residualised", "net_sharpe", "−0.512"),
    )

    @pytest.mark.parametrize(("book", "field", "text"), NUMBERS)
    def test_each_headline_number_is_in_the_record(
        self, development: dict[str, Any], document: str, book: str, field: str, text: str
    ) -> None:
        value = development["books"][book]["summary"][field]
        assert f"{value:+.3f}".replace("-", "−") == text
        assert text in document

    def test_the_document_states_the_verdict_and_its_limits(self, document: str) -> None:
        assert "MARKET_YIELD_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT" in document
        assert "決まっていないこと" in document
        assert "decision-grade ではなく" in document
        assert "保護 span" in document and "読んでいない" in document

    def test_the_document_forbids_the_post_hoc_rescues(self, document: str) -> None:
        for phrase in ("符号反転", "lookback の変更", "horizon の追加", "vol target の変更"):
            assert phrase in document

    def test_the_ledger_entry_matches_the_record(self, development: dict[str, Any]) -> None:
        from scripts.research.round_a.ledger import LEDGER

        entry = next(e for e in LEDGER if e["id"] == "H-025")
        assert entry["prespecified"] is True
        assert entry["status"].startswith("CLOSED - MARKET_YIELD_REPRICING_NOT_SUPPORTED")
        assert "a25d078" in entry["configurations"]
        assert "settles nothing" in entry["result"]
        for book, field in (
            ("A_yield_repricing", "gross_sharpe"),
            ("A_yield_repricing", "net_sharpe"),
            ("C_residualised", "gross_sharpe"),
        ):
            value = development["books"][book]["summary"][field]
            assert f"{value:+.3f}" in entry["result"] or f"{value:.3f}" in entry["result"]
