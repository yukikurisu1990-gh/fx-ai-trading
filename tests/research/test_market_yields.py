"""T-R: the sources are official, the lag cannot leak, and the universe is what the audit fixed.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Reads committed records only. No network, no market data.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.research.market_yields import (
    CURRENCIES,
    OUTCOMES,
    development,
    integrity,
    prereg,
    sources,
)

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
def development_record() -> dict[str, Any]:
    return json.loads((RECORDS / "development.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def document() -> str:
    return DOC.read_text(encoding="utf-8")


class TestTheDevelopmentRun:
    def test_it_ran_what_the_prereg_froze(self, development_record: dict[str, Any]) -> None:
        assert development_record["universe"] == list(prereg.UNIVERSE)
        assert development_record["prereg"]["signal"]["lookback_days"] == 5
        assert set(development_record["books"]) == {
            "A_yield_repricing",
            "B_fx_momentum",
            "C_residualised",
        }
        assert development_record["span"]["first"] == prereg.DECISION_SPAN["first"]
        assert development_record["protected_spans_read"] is False

    def test_the_screen_is_applied_exactly_and_stops(
        self, development_record: dict[str, Any]
    ) -> None:
        screen = development_record["screen"]
        books = development_record["books"]
        a = books["A_yield_repricing"]["summary"]
        assert screen["conditions"]["A gross Sharpe > 0"] is (a["gross_sharpe"] > 0)
        assert screen["conditions"]["A net Sharpe >= 0.3"] is (a["net_sharpe"] >= 0.3)
        assert screen["decision"] == ("advance" if all(screen["conditions"].values()) else "stop")
        assert screen["decision"] == "stop"
        assert screen["verdict"] == "MARKET_YIELD_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        assert screen["decision_grade"] is False

    def test_cost_is_what_separates_gross_from_net(
        self, development_record: dict[str, Any]
    ) -> None:
        for name, book in development_record["books"].items():
            summary = book["summary"]
            drag = summary["gross_sharpe"] - summary["net_sharpe"]
            assert drag > 0.9, name
            assert summary["turnover_round_trips_per_year_per_unit_gross"] > 60.0, name
            assert summary["annual_cost"] > 0.09, name

    def test_the_observed_ic_is_below_what_the_design_needed(
        self, development_record: dict[str, Any]
    ) -> None:
        needed = development_record["feasibility_before_the_run"]["rows"]["half_life_5d"][
            "required_daily_ic_for_net_0_3"
        ]
        for name in ("A_yield_repricing", "C_residualised"):
            assert development_record["books"][name]["ic"]["5d"] < needed, name

    def test_the_outside_universe_exposure_is_measured_not_hidden(
        self, development_record: dict[str, Any]
    ) -> None:
        outside = development_record["books"]["A_yield_repricing"]["outside_universe_exposure"]
        assert set(outside["currencies"]) == set(prereg.EXCLUDED)
        assert outside["share_of_days_with_any_exposure"] > 0
        assert abs(outside["cumulative_pnl_total"]) < 0.05

    def test_leverage_cannot_rescue_a_negative_net(
        self, development_record: dict[str, Any]
    ) -> None:
        assert development_record["leverage_and_margin_at_10pct_vol"]["annual_net_return"] < 0

    def test_every_book_is_underpowered_by_the_prereg_s_own_number(
        self, development_record: dict[str, Any]
    ) -> None:
        power = development_record["feasibility_before_the_run"][
            "detectable_net_sharpe_at_80pct_power"
        ]
        assert power > 1.0
        for book in development_record["books"].values():
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
        self, development_record: dict[str, Any], document: str, book: str, field: str, text: str
    ) -> None:
        value = development_record["books"][book]["summary"][field]
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

    def test_the_ledger_entry_matches_the_record(self, development_record: dict[str, Any]) -> None:
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
            value = development_record["books"][book]["summary"][field]
            assert f"{value:+.3f}" in entry["result"] or f"{value:.3f}" in entry["result"]


class TestTheRunPipeline:
    """The run module's own functions, on synthetic panels. No market data needed."""

    def _panels(self, days: int = 80) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
        index = pd.bdate_range("2021-01-04", periods=days)
        rng = np.random.default_rng(11)
        columns = list(prereg.UNIVERSE)
        excess = pd.DataFrame(
            rng.standard_normal((days, len(columns))) / 100.0, index=index, columns=columns
        )
        frames = {
            c: pd.DataFrame(
                {"date": index, "yield_percent": np.cumsum(rng.standard_normal(days)) / 10.0 + 2.0}
            )
            for c in columns
        }
        panel = development.lagged_yield_panel(frames, index)
        return excess, panel, frames

    def test_a_same_day_yield_cannot_reach_its_own_score(self) -> None:
        excess, panel, frames = self._panels()
        scores = development.build_scores(panel, excess)
        day = panel.index[60]
        moved = {c: f.copy() for c, f in frames.items()}
        target = moved["USD"]
        target.loc[target["date"] == day, "yield_percent"] += 5.0
        after = development.build_scores(development.lagged_yield_panel(moved, panel.index), excess)
        for name in scores:
            pd.testing.assert_series_equal(
                scores[name].loc[day], after[name].loc[day], check_names=False
            )
        #: it must reach the next decision day, or the lag would be hiding the signal
        assert not np.allclose(
            scores["A_yield_repricing"].loc[panel.index[61]].to_numpy(dtype=float),
            after["A_yield_repricing"].loc[panel.index[61]].to_numpy(dtype=float),
        )

    def test_the_lagged_panel_is_the_availability_rule(self) -> None:
        excess, panel, frames = self._panels()
        for currency, frame in frames.items():
            pd.testing.assert_series_equal(
                panel[currency].astype(float),
                integrity.available_from(frame, panel.index).astype(float),
                check_names=False,
            )

    def test_the_lookback_and_horizons_come_from_the_prereg(self) -> None:
        import inspect

        assert prereg.PREREG["signal"]["lookback_days"] == development.LOOKBACK
        #: the default is the constant itself, not a number that could drift from the prereg
        assert (
            inspect.signature(development.build_scores).parameters["lookback"].default
            == development.LOOKBACK
        )
        assert "lookback: int = LOOKBACK" in (PACKAGE / "development.py").read_text(
            encoding="utf-8"
        )
        assert list(development.HORIZONS) == prereg.PREREG["targets"]["horizons_days"]
        excess, panel, _ = self._panels()
        wide = development.build_scores(panel, excess, lookback=20)
        narrow = development.build_scores(panel, excess, lookback=5)
        assert not wide["A_yield_repricing"].equals(narrow["A_yield_repricing"])

    def test_the_ic_looks_forward_by_exactly_the_horizon(self) -> None:
        excess, panel, _ = self._panels()
        forward = excess.rolling(5).sum().shift(-5)
        assert development._ic(forward.dropna(), excess, 5) == pytest.approx(1.0, abs=1e-9)
        assert abs(development._ic(excess, excess, 5)) < 0.2

    def test_expand_puts_exactly_zero_outside_the_universe(self) -> None:
        excess, panel, _ = self._panels()
        score = development.build_scores(panel, excess)["A_yield_repricing"].dropna()
        expanded = development._expand(score)
        outside = [c for c in expanded.columns if c not in prereg.UNIVERSE]
        assert outside
        assert float(expanded[outside].abs().to_numpy().max()) == 0.0

    def test_neutralisation_happens_inside_the_universe(self) -> None:
        excess, panel, _ = self._panels()
        score = development.build_scores(panel, excess)["A_yield_repricing"]
        out = development._neutralise_within_universe(score, excess).dropna(how="any")
        assert list(out.columns) == list(prereg.UNIVERSE)
        assert float(out.sum(axis=1).abs().max()) < 1e-9
        assert development.BOOK.neutralize_leading_factor is False

    def test_the_control_is_the_same_lookback_as_the_signal(self) -> None:
        excess, panel, _ = self._panels()
        scores = development.build_scores(panel, excess)
        day = panel.index[70]
        window = excess.loc[:day].tail(development.LOOKBACK).sum()
        expected = (window - window.mean()) / window.std(ddof=0)
        pd.testing.assert_series_equal(
            scores["B_fx_momentum"].loc[day].astype(float),
            expected.astype(float),
            check_names=False,
        )

    def test_the_residual_is_orthogonal_to_the_control(self) -> None:
        excess, panel, _ = self._panels()
        scores = development.build_scores(panel, excess)
        day = panel.index[70]
        residual = scores["C_residualised"].loc[day].to_numpy(dtype=float)
        control = scores["B_fx_momentum"].loc[day].to_numpy(dtype=float)
        assert abs(float(residual @ control)) < 1e-9

    def test_the_screen_condition_on_the_gap_stress_is_computed(self) -> None:
        books = {
            "A_yield_repricing": {
                "summary": {"gross_sharpe": 1.0, "net_sharpe": 1.0},
                "blocks": [],
            },
            "B_fx_momentum": {"summary": {"net_sharpe": 0.0}},
            "C_residualised": {"summary": {"net_sharpe": 0.5}},
        }
        stress = {"loss_cut_on_gap": False, "fixed_notional_loss_cut": True}
        passing = development._screen(books, {"x": 1.0}, stress)
        failing = development._screen(books, {"x": 1.0}, {**stress, "loss_cut_on_gap": True})
        key = "10% vol is reachable inside the gap stress"
        assert passing["conditions"][key] is True
        assert failing["conditions"][key] is False
        #: both readings travel with the condition, not only the one it uses
        assert passing["gap_stress_reading"]["equity_proportional_loss_cut"] is False
        assert passing["gap_stress_reading"]["fixed_notional_loss_cut"] is True
        assert failing["gap_stress_reading"]["equity_proportional_loss_cut"] is True

    def test_the_screen_condition_on_c_is_the_frozen_text(self) -> None:
        books = {
            "A_yield_repricing": {
                "summary": {"gross_sharpe": 1.0, "net_sharpe": 1.0},
                "blocks": [],
            },
            "B_fx_momentum": {"summary": {"net_sharpe": -0.9}},
            "C_residualised": {"summary": {"net_sharpe": -0.5}},
        }
        screen = development._screen(
            books, {"x": 1.0}, {"loss_cut_on_gap": False, "fixed_notional_loss_cut": True}
        )
        #: the frozen text asks for an increment over B, not for C to be positive
        assert screen["conditions"]["C keeps a positive net increment over B"] is True
        assert screen["c_net_sharpe_still_negative"] is True

    def test_the_momentum_control_cannot_see_the_future(self) -> None:
        """B feeds C, so a leak in the control would reach the primary test."""
        excess, panel, _ = self._panels()
        day = panel.index[60]
        moved = excess.copy()
        moved.loc[moved.index > day] += 0.05
        before = development.build_scores(panel, excess)
        after = development.build_scores(panel, moved)
        for name in ("B_fx_momentum", "A_yield_repricing", "C_residualised"):
            pd.testing.assert_series_equal(
                before[name].loc[day], after[name].loc[day], check_names=False
            )
        #: and the control must react to the past, or it is not a momentum control
        past = excess.copy()
        #: one currency only: a shift common to all of them cancels in the cross-section
        past.loc[past.index <= day, "USD"] += 0.05
        shifted = development.build_scores(panel, past)
        assert not np.allclose(
            before["B_fx_momentum"].loc[day].to_numpy(dtype=float),
            shifted["B_fx_momentum"].loc[day].to_numpy(dtype=float),
        )

    def test_the_executed_configuration_matches_the_frozen_text(
        self, development_record: dict[str, Any]
    ) -> None:
        """Field by field, with the one declared deviation as the only exception."""
        config = development_record["executed_book_config"]
        frozen = prereg.PREREG["book_configuration"]
        assert config["vol_target"] == frozen["vol_target"]
        assert config["weight_cap"] == 0.25, "the frozen text caps currency weights at 0.25"
        assert config["band"] == 0.10, "the frozen text sets the no-trade band at 0.10"
        assert config["mapping"] == "linear"
        assert config["cost_multiple"] == 1.0
        assert config["max_leverage"] >= 1_000_000.0, frozen["leverage_cap"]
        current = development.provenance()
        assert config == current["executed_book_config"], (
            "the record must describe the book that ran"
        )
        assert (
            development_record["deviations_from_the_frozen_text"]
            == current["deviations_from_the_frozen_text"]
        )
        #: the single declared exception, and it must stay declared
        assert config["neutralize_leading_factor"] is False
        assert frozen["factor_neutralisation"] is True
        assert (
            "factor_neutralisation_moved_into_the_universe"
            in development_record["deviations_from_the_frozen_text"]
        )

    def test_both_gap_stress_readings_are_recorded(
        self, development_record: dict[str, Any]
    ) -> None:
        reading = development_record["screen"]["gap_stress_reading"]
        assert reading["equity_proportional_loss_cut"] is False
        assert reading["fixed_notional_loss_cut"] is True
        assert "fixed capital" in reading["note"]

    def test_the_executed_configuration_is_recorded(
        self, development_record: dict[str, Any]
    ) -> None:
        config = development_record["executed_book_config"]
        assert config["neutralize_leading_factor"] is False
        assert config["mapping"] == "linear"
        assert config["vol_target"] == prereg.PREREG["book_configuration"]["vol_target"]
        assert config["weight_cap"] == 0.25 and config["band"] == 0.10
        assert config["max_leverage"] >= 1_000_000.0
        assert (
            "factor_neutralisation_moved_into_the_universe"
            in development_record["deviations_from_the_frozen_text"]
        )

    def test_run_takes_its_horizon_numbers_from_the_constants(self) -> None:
        """A literal in `run` would be a design number that the prereg no longer governs."""
        tree = ast.parse((PACKAGE / "development.py").read_text(encoding="utf-8"))
        run = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run"
        )
        names = {node.id for node in ast.walk(run) if isinstance(node, ast.Name)}
        assert {"LOOKBACK", "HORIZONS"} <= names
        numbers = {
            node.value
            for node in ast.walk(run)
            if isinstance(node, ast.Constant) and isinstance(node.value, int | float)
        }
        assert not ({5, 20} & numbers), numbers

    def test_the_frozen_sign_is_pinned(self) -> None:
        assert prereg.PREREG["signal"]["sign"].startswith("+1")
        assert prereg.PREREG["signal"]["sign_frozen"] is True
        assert prereg.PREREG["signal"]["inversion_after_the_result_prohibited"] is True
