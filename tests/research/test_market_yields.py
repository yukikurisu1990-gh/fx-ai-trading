"""T-R: the sources are official, the lag cannot leak, and the universe is what the audit fixed.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Reads committed records only. No network, no market data.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.research import model_learning
from scripts.research.edge_sources import leverage
from scripts.research.market_yields import (
    CURRENCIES,
    DATA_DIR,
    FAMILY_BOUNDARY,
    OUTCOMES,
    WORKFLOW_STATUS,
    development,
    integrity,
    portfolio,
    prereg,
    prereg_r2,
    risk,
    sources,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scripts/research/market_yields"
RECORDS = ROOT / "artifacts/research/market_yields"

#: The M15 bar cache and the acquired yield series live under `artifacts/track_a_scratch/`,
#: which `.gitignore` excludes, so CI has the code and not the bytes. The handful of tests
#: that must touch them skip there rather than failing — and say which route repopulates
#: them, because a test that fails for want of data teaches a reader to ignore red CI.
_LOCAL_INPUTS = [
    *[
        ROOT / block["cache"] / "m15_AUD_CAD.parquet"
        for block in model_learning.SEEN_SPANS.values()
    ],
    *[ROOT / DATA_DIR / f"{currency.lower()}_2y.parquet" for currency in prereg.UNIVERSE],
]
needs_local_caches = pytest.mark.skipif(
    not all(path.is_file() for path in _LOCAL_INPUTS),
    reason=(
        "the M15 bar cache and the acquired yield series are untracked local artefacts; "
        "run the model_learning build_cache and "
        "`MARKET_YIELDS_ACQUIRE_APPROVED=1 python -m scripts.research.market_yields.acquire`"
    ),
)


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
        assert screen["verdict"] == (
            "MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        )
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
        assert (
            "MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT" in document
        )
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
        assert entry["status"].startswith(
            "CLOSED - MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED"
        )
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


@pytest.fixture(scope="module")
def repaired_record() -> dict[str, Any]:
    return json.loads((RECORDS / "fast_repaired.json").read_text(encoding="utf-8"))


class TestTheUniverseClosedBook:
    UNIVERSE = prereg.UNIVERSE

    def test_only_pairs_whose_both_legs_are_observed(self) -> None:
        pairs = portfolio.tradable_pairs(self.UNIVERSE)
        assert pairs == (
            "EUR_CAD",
            "EUR_GBP",
            "EUR_JPY",
            "EUR_USD",
            "GBP_JPY",
            "GBP_USD",
            "USD_CAD",
            "USD_JPY",
        )
        for pair in pairs:
            assert set(pair.split("_")) <= set(self.UNIVERSE)

    def test_the_routing_graph_connects_the_universe(self) -> None:
        routing = portfolio.routing_profile(self.UNIVERSE)
        assert routing.connected
        assert 0.5 < routing.pair_gross_per_unit_currency_gross < 1.0

    def test_the_split_map_is_the_equal_split_of_the_restricted_pairs(self) -> None:
        matrix = portfolio.split_map(self.UNIVERSE)
        pairs = portfolio.tradable_pairs(self.UNIVERSE)
        assert matrix.shape == (len(pairs), len(self.UNIVERSE))
        #: one unit of a currency is split evenly over the pairs that carry it, signed
        for column, currency in enumerate(self.UNIVERSE):
            carried = [p for p in pairs if currency in p.split("_")]
            assert np.isclose(np.abs(matrix[:, column]).sum(), 1.0)
            assert int((matrix[:, column] != 0).sum()) == len(carried)

    def test_a_currency_with_no_tradable_pair_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no tradable pair"):
            portfolio.split_map(("CAD", "NZD"))

    def _book(self) -> dict[str, Any]:
        index = pd.bdate_range("2021-01-04", periods=60)
        rng = np.random.default_rng(5)
        columns = list(self.UNIVERSE)
        excess = pd.DataFrame(
            rng.standard_normal((len(index), len(columns))) / 100.0, index=index, columns=columns
        )
        mu = pd.DataFrame(
            rng.standard_normal((len(index), len(columns))), index=index, columns=columns
        )
        return portfolio.run_book(development.BOOK, mu, excess, universe=columns)

    def test_no_weight_can_reach_a_currency_outside_the_universe(self) -> None:
        daily = self._book()["daily"]
        exposures = {c.removeprefix("x_") for c in daily.columns if c.startswith("x_")}
        assert exposures == set(self.UNIVERSE)
        assert not exposures & set(prereg.EXCLUDED)

    def test_the_book_is_sum_zero_and_capped(self) -> None:
        daily = self._book()["daily"]
        weights = daily[[f"x_{c}" for c in self.UNIVERSE]]
        levered = weights.div(daily["leverage"], axis=0).dropna()
        assert float(levered.sum(axis=1).abs().max()) < 1e-9
        assert float(levered.abs().to_numpy().max()) <= 0.25 + 0.10 + 1e-9

    def test_net_is_gross_minus_the_charged_cost(self) -> None:
        daily = self._book()["daily"]
        assert np.allclose(daily["net"], daily["gross"] - daily["cost"])
        expected = daily["one_way_traded"] * 1.703 / 10_000.0
        assert np.allclose(daily["cost"], expected)

    def test_the_repaired_rerun_keeps_the_recorded_verdict(
        self, repaired_record: dict[str, Any], development_record: dict[str, Any]
    ) -> None:
        assert repaired_record["verdict_unchanged"] == development_record["verdict"]
        for name, row in repaired_record["against_the_recorded_run"].items():
            assert row["repaired_net_sharpe"] < 0.3, name
        assert repaired_record["books"]["A_yield_repricing"]["summary"]["gross_sharpe"] > 0
        for book in repaired_record["books"].values():
            assert {c.removeprefix("x_") for c in book["exposure_columns"]} == set(prereg.UNIVERSE)


class TestTheSlowPrereg:
    def test_one_horizon_only(self) -> None:
        assert prereg_r2.PRIMARY_HORIZON_DAYS == 20
        signal = prereg_r2.PREREG["signal"]
        assert isinstance(signal["horizon_days"], int)
        assert "not_chosen_for_fit" in signal
        #: a grid would show up as a collection of horizons; the ruling forbids one
        import ast as _ast

        tree = _ast.parse((PACKAGE / "prereg_r2.py").read_text(encoding="utf-8"))
        horizon_constants = [
            node
            for node in tree.body
            if isinstance(node, _ast.AnnAssign)
            and isinstance(node.target, _ast.Name)
            and "HORIZON" in node.target.id
        ]
        assert len(horizon_constants) == 1
        assert isinstance(horizon_constants[0].value, _ast.Constant)
        assert "horizons_days" not in prereg_r2.PREREG["signal"]

    def test_the_hypothesis_is_not_the_fast_one_smoothed(self) -> None:
        assert "why_this_is_not_the_fast_hypothesis_smoothed" in prereg_r2.PREREG
        assert prereg_r2.PREREG["primary_test"] == "D"
        assert set(prereg_r2.PREREG["books"]) == {
            "A_fast_5d_reference",
            "B_slow_rate_state",
            "C_fx_price_control",
            "D_residualised",
        }

    def test_the_sign_and_universe_are_frozen(self) -> None:
        assert prereg_r2.PREREG["signal"]["sign_frozen"] is True
        assert prereg_r2.PREREG["signal"]["inversion_after_the_result_prohibited"] is True
        assert prereg_r2.UNIVERSE == prereg.UNIVERSE
        assert set(prereg_r2.EXCLUDED) == set(prereg.EXCLUDED)

    def test_the_layer_is_the_repaired_one_and_not_track_1s_alpha(self) -> None:
        config = prereg_r2.PREREG["book_configuration"]
        assert config["track_1_alpha_model_reused"] is False
        assert "portfolio.py" in config["architecture"]
        assert config["leverage_cap"].startswith("none")

    def test_every_declared_status_is_an_allowed_outcome(self) -> None:
        screen = prereg_r2.PREREG["screen"]
        for key in ("status_candidate", "status_marginal", "status_stop", "status_data"):
            assert screen[key] in OUTCOMES
        assert screen["no_automatic_progress_to_fresh"] is True
        assert "OIS" in prereg_r2.PREREG["family_boundary_if_stop"]
        assert FAMILY_BOUNDARY.endswith("NOT_SUPPORTED_IN_SEEN_DEVELOPMENT")

    def test_the_feasibility_is_signal_blind(self) -> None:
        feasibility = prereg_r2.feasibility()
        assert (
            feasibility["rows"]["half_life_20d"]["cost_ir_drag"]
            < feasibility["rows"]["half_life_5d"]["cost_ir_drag"]
        )
        assert feasibility["detectable_net_sharpe_at_80pct_power"] > 1.0

    def test_the_module_holds_no_result(self) -> None:
        source = (PACKAGE / "prereg_r2.py").read_text(encoding="utf-8").lower()
        for word in ("observed gross", "we found", "the result was", "net sharpe was"):
            assert word not in source


#: The frozen T-R2 pre-registration, by content. Any edit to what it declares changes
#: this digest, so a silent post-result amendment cannot pass as the frozen design.
PREREG_R2_DIGEST = "2f3f8bb37af00b31fcd2242278998847c7262f557d885df36d71a9a4e32bc67a"


def _synthetic(days: int = 90, currencies: tuple[str, ...] = prereg.UNIVERSE, seed: int = 3):
    index = pd.bdate_range("2021-01-04", periods=days)
    rng = np.random.default_rng(seed)
    excess = pd.DataFrame(
        rng.standard_normal((days, len(currencies))) / 100.0, index=index, columns=list(currencies)
    )
    excess = excess.sub(excess.mean(axis=1), axis=0)
    mu = pd.DataFrame(
        rng.standard_normal((days, len(currencies))), index=index, columns=list(currencies)
    )
    return mu, excess


class TestTheLayerIsFaithful:
    def test_the_pnl_belongs_to_the_day_after_the_decision(self) -> None:
        mu, excess = _synthetic()
        day = excess.index[40]
        moved = excess.copy()
        moved.loc[moved.index > day] += 0.02
        base = portfolio.run_book(development.BOOK, mu, excess, universe=prereg.UNIVERSE)["daily"]
        after = portfolio.run_book(development.BOOK, mu, moved, universe=prereg.UNIVERSE)["daily"]
        #: the exposure chosen on `day` cannot know the days after it
        columns = [f"x_{c}" for c in prereg.UNIVERSE]
        before = base["decision_day"] <= day
        pd.testing.assert_frame_equal(base.loc[before, columns], after.loc[before, columns])
        #: and the P&L of that exposure is the next day's return, which did change
        row = base.index[base["decision_day"] == day][0]
        assert base.loc[row, "gross"] != after.loc[row, "gross"]

    def test_the_history_window_never_reaches_past_the_decision_day(self) -> None:
        mu, excess = _synthetic()
        day = excess.index[50]
        moved = excess.copy()
        moved.loc[moved.index > day] *= 8.0
        base = portfolio.run_book(development.BOOK, mu, excess, universe=prereg.UNIVERSE)["daily"]
        after = portfolio.run_book(development.BOOK, mu, moved, universe=prereg.UNIVERSE)["daily"]
        #: every decision up to and including `day` sees only history
        before = base["decision_day"] <= day
        assert base.loc[before, "ex_ante_vol"].equals(after.loc[before, "ex_ante_vol"])
        assert base.loc[before, "leverage"].equals(after.loc[before, "leverage"])
        columns = [f"x_{c}" for c in prereg.UNIVERSE]
        pd.testing.assert_frame_equal(base.loc[before, columns], after.loc[before, columns])

    def test_the_volatility_target_is_applied(self) -> None:
        mu, excess = _synthetic()
        daily = portfolio.run_book(development.BOOK, mu, excess, universe=prereg.UNIVERSE)["daily"]
        assert daily["leverage"].nunique() > 5
        assert float(daily["leverage"].mean()) > 1.0
        flat = portfolio.run_book(
            portfolio.BookConfig(name="flat", mapping="linear", vol_target=None),
            mu,
            excess,
            universe=prereg.UNIVERSE,
        )["daily"]
        assert set(flat["leverage"].unique()) == {1.0}

    def test_the_no_trade_band_stops_some_days(self) -> None:
        mu, excess = _synthetic()
        banded = portfolio.run_book(development.BOOK, mu, excess, universe=prereg.UNIVERSE)["daily"]
        no_band = portfolio.run_book(
            portfolio.BookConfig(name="nb", mapping="linear", band=0.0),
            mu,
            excess,
            universe=prereg.UNIVERSE,
        )["daily"]
        assert float(banded["traded"].mean()) < 1.0
        assert float(no_band["one_way_traded"].sum()) > float(banded["one_way_traded"].sum())

    def test_the_declared_mapping_and_windows_are_used(self) -> None:
        mu, excess = _synthetic()
        columns = [f"x_{c}" for c in prereg.UNIVERSE]
        #: only the field under test differs from the book that runs
        linear = portfolio.run_book(development.BOOK, mu, excess, universe=prereg.UNIVERSE)["daily"]
        for mapping in ("rank", "vol_normalized"):
            other = portfolio.run_book(
                replace(development.BOOK, mapping=mapping), mu, excess, universe=prereg.UNIVERSE
            )["daily"]
            assert not linear[columns].equals(other[columns]), mapping
        narrow = portfolio.run_book(
            replace(development.BOOK, mapping="vol_normalized", sigma_window=10),
            mu,
            excess,
            universe=prereg.UNIVERSE,
        )["daily"]
        wide = portfolio.run_book(
            replace(development.BOOK, mapping="vol_normalized", sigma_window=60),
            mu,
            excess,
            universe=prereg.UNIVERSE,
        )["daily"]
        assert not narrow[columns].equals(wide[columns])

    def test_a_gap_in_the_decision_calendar_is_refused(self) -> None:
        mu, excess = _synthetic()
        with pytest.raises(ValueError, match="contiguous"):
            portfolio.run_book(
                development.BOOK, mu.drop(mu.index[20]), excess, universe=prereg.UNIVERSE
            )

    def test_the_cost_multiple_is_honoured(self) -> None:
        mu, excess = _synthetic()
        base = portfolio.run_book(development.BOOK, mu, excess, universe=prereg.UNIVERSE)["daily"]
        doubled = portfolio.run_book(
            development.BOOK, mu, excess, universe=prereg.UNIVERSE, cost_multiple=2.0
        )["daily"]
        assert np.allclose(doubled["cost"], 2.0 * base["cost"])
        assert np.allclose(doubled["net"], doubled["gross"] - doubled["cost"])

    def test_the_drawdown_governor_is_refused_rather_than_ignored(self) -> None:
        mu, excess = _synthetic()
        with pytest.raises(NotImplementedError):
            portfolio.run_book(
                portfolio.BookConfig(name="g", mapping="linear", drawdown_governor=True),
                mu,
                excess,
                universe=prereg.UNIVERSE,
            )

    def test_the_leverage_cap_is_reported_when_it_binds(self) -> None:
        mu, excess = _synthetic()
        capped = portfolio.run_book(
            portfolio.BookConfig(name="c", mapping="linear", max_leverage=1.5),
            mu,
            excess,
            universe=prereg.UNIVERSE,
        )["daily"]
        assert bool(capped["at_leverage_cap"].any())
        assert float(capped["leverage"].max()) <= 1.5 + 1e-9
        loose = portfolio.run_book(development.BOOK, mu, excess, universe=prereg.UNIVERSE)["daily"]
        assert not bool(loose["at_leverage_cap"].any())

    def test_a_split_routing_graph_is_reported_as_such(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PAIRS_20 happens to connect every subset, so the helper is tested directly."""
        monkeypatch.setattr(portfolio, "tradable_pairs", lambda universe: ("AUD_NZD", "GBP_USD"))
        assert portfolio._connected(("AUD", "NZD", "GBP", "USD")) is False
        monkeypatch.setattr(
            portfolio, "tradable_pairs", lambda universe: ("AUD_NZD", "NZD_USD", "GBP_USD")
        )
        assert portfolio._connected(("AUD", "NZD", "GBP", "USD")) is True

    def test_the_real_universe_is_connected(self) -> None:
        assert portfolio.routing_profile(prereg.UNIVERSE).connected is True

    def test_the_routing_profile_reports_what_the_helper_says(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(portfolio, "_connected", lambda universe: False)
        assert portfolio.routing_profile(prereg.UNIVERSE).connected is False

    def test_the_reported_pnl_is_the_routed_books_pnl(self) -> None:
        panel = {"pair_returns": None}
        index = pd.bdate_range("2021-01-04", periods=40)
        rng = np.random.default_rng(7)
        pairs = portfolio.tradable_pairs(prereg.UNIVERSE)
        panel["pair_returns"] = pd.DataFrame(
            rng.standard_normal((len(index), len(pairs))) / 100.0, index=index, columns=list(pairs)
        )
        weights = np.array([0.25, -0.25, 0.10, -0.05, -0.05])
        assert abs(weights.sum()) < 1e-12
        assert portfolio.identity_residual(panel, prereg.UNIVERSE, weights) < 1e-15

    def test_the_repair_statement_says_what_was_repaired(self) -> None:
        assert "returns" in portfolio.REPAIR["fix"]
        assert "#485" in portfolio.REPAIR["verdicts_unchanged"]
        assert "robustness" in portfolio.REPAIR["verdicts_unchanged"]


class TestTheFrozenSlowPrereg:
    def test_the_declared_design_is_unchanged(self) -> None:
        digest = hashlib.sha256(
            json.dumps(prereg_r2.PREREG, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        assert digest == PREREG_R2_DIGEST, "the frozen pre-registration changed"

    def test_the_horizon_constant_and_the_declaration_agree(self) -> None:
        assert prereg_r2.PREREG["signal"]["horizon_days"] == prereg_r2.PRIMARY_HORIZON_DAYS
        #: no second horizon may hide anywhere in the declaration
        flat = json.dumps(prereg_r2.PREREG)
        for other in (10, 15, 30, 40, 60):
            assert '"horizon_days": ' + str(other) not in flat

    def test_the_bands_are_disjoint_and_the_bars_are_where_they_were(self) -> None:
        assert prereg_r2.CANDIDATE_NET_SHARPE == 0.3
        assert prereg_r2.MARGINAL_NET_SHARPE == 0.2
        assert prereg_r2.MARGINAL_NET_SHARPE < prereg_r2.CANDIDATE_NET_SHARPE
        screen = prereg_r2.PREREG["screen"]
        assert "at least 0.3" in screen["candidate"]
        assert "[0.2, 0.3)" in screen["marginal_candidate"]
        assert "every other outcome" in screen["stop"]
        assert "no held state" in screen["stop"]

    def test_the_turnover_bound_is_a_screen_condition_with_a_number(self) -> None:
        shared = " ".join(prereg_r2.PREREG["screen"]["shared_conditions"])
        assert str(int(prereg_r2.TURNOVER_BOUND)) in shared
        expectation = prereg_r2.feasibility()["turnover_expectation"]
        assert expectation["screen_bound"] == prereg_r2.TURNOVER_BOUND
        #: the expectation is built from what the fast run paid, not from the law alone
        assert (
            expectation["expected_turnover_by_that_multiplier"]
            > expectation["band_law_at_twenty_day_half_life"]
        )

    def test_the_primary_statistic_is_decomposed_in_advance(self) -> None:
        text = prereg_r2.PREREG["primary_test_decomposition"]
        assert "beta" in text and "leg" in text
        assert any(
            "rate-residual leg" in c for c in prereg_r2.PREREG["screen"]["shared_conditions"]
        )

    def test_the_layer_and_the_returns_are_named(self) -> None:
        config = prereg_r2.PREREG["book_configuration"]
        assert "universe_panel" in config["returns"]
        assert "exactly one pass" in config["factor_neutralisation"]
        assert config["max_leverage"] == 1_000_000.0

    def test_the_prereg_forbids_what_the_ruling_forbids(self) -> None:
        assert "no fitted coefficient" in prereg_r2.PREREG["stage"].lower()
        prohibited = " ".join(prereg_r2.PREREG["prohibited_after_the_result"]).lower()
        for phrase in ("horizon", "sign", "universe", "ml", "protected"):
            assert phrase in prohibited
        assert "further conditioning variable" in prereg_r2.PREREG["no_control_zoo"].lower()
        assert "may not be rescued" in prereg_r2.PREREG["universe"]["breadth_expansion"]
        assert "No same-day use" in prereg_r2.PREREG["availability_rule"]

    def test_the_tokens_stay_what_they_are(self) -> None:
        assert not any("PRODUCTION" in token for token in OUTCOMES)
        assert FAMILY_BOUNDARY == (
            "MARKET_YIELD_REPRICING_SIMPLE_DIRECTIONAL_FAMILY_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        )
        #: both formulations have run; the status says so and still does not declare
        #: the family boundary, which is a Human decision
        assert WORKFLOW_STATUS == (
            "MARKET_YIELD_REPRICING_FAST_AND_SLOW_FORMULATIONS_BOTH_NOT_SUPPORTED"
            "_AWAITING_HUMAN_DECISION"
        )
        assert FAMILY_BOUNDARY not in WORKFLOW_STATUS


class TestTheRepairedRerunIsTheFrozenSignal:
    def test_it_uses_the_frozen_lookback_and_book(self) -> None:
        source = (PACKAGE / "fast_repair_check.py").read_text(encoding="utf-8")
        assert "development.LOOKBACK" in source
        assert "development.BOOK" in source
        assert "portfolio.universe_panel" in source
        assert "assert_not_protected" in source

    def test_the_record_shows_the_closed_identity(self, repaired_record: dict[str, Any]) -> None:
        check = repaired_record["identity_check"]
        assert check["identity_holds"] is True
        assert check["incomplete_pair_days"] == 0
        assert check["max_residual_on_complete_days"] < 1e-12
        assert "binding one" in repaired_record["condition_re_verified"]

    @needs_local_caches
    def test_the_panel_drops_the_days_it_cannot_route(self) -> None:
        from scripts.research.model_learning import corpus

        panel = corpus.currency_panel()
        rebuilt = portfolio.universe_panel(panel, prereg.UNIVERSE)
        pairs = list(portfolio.tradable_pairs(prereg.UNIVERSE))
        complete = panel["pair_returns"][pairs].dropna(how="any")
        assert len(rebuilt) == len(complete)
        assert len(rebuilt) < len(panel["pair_returns"]), "at least one day is incomplete"
        assert float(rebuilt.sum(axis=1).abs().max()) < 1e-12


class TestTheLayerMatchesItsReference:
    def test_on_the_full_cross_section_it_is_the_reference(self) -> None:
        """With every currency in the universe, this must be construction.run_book."""
        from scripts.research.continuous_portfolio import construction
        from scripts.research.model_learning import CURRENCIES_G10

        currencies = tuple(sorted(CURRENCIES_G10))
        mu, excess = _synthetic(days=120, currencies=currencies, seed=11)
        config = replace(development.BOOK, neutralize_leading_factor=True)
        mine = portfolio.run_book(config, mu, excess, universe=currencies)["daily"]
        reference = construction.run_book(config, mu, excess, days_per_year=252.0)["daily"]
        shared = [c for c in mine.columns if c in reference.columns and c != "decision_day"]
        assert {"gross", "cost", "net", "leverage", "x_USD", "pnl_USD"} <= set(shared)
        pd.testing.assert_frame_equal(
            mine[shared].astype(float), reference[shared].astype(float), check_names=False
        )

    def test_the_first_decision_day_takes_no_position_as_the_reference_does(self) -> None:
        mu, excess = _synthetic(days=30)
        daily = portfolio.run_book(development.BOOK, mu, excess, universe=prereg.UNIVERSE)["daily"]
        #: one row cannot give a covariance, so the vol target refuses to size the book
        assert float(daily["leverage"].iloc[0]) == 0.0
        assert float(daily["gross"].iloc[0]) == 0.0

    def test_the_factor_window_is_used(self) -> None:
        mu, excess = _synthetic()
        columns = [f"x_{c}" for c in prereg.UNIVERSE]
        narrow = portfolio.run_book(
            replace(development.BOOK, neutralize_leading_factor=True, factor_window=20),
            mu,
            excess,
            universe=prereg.UNIVERSE,
        )["daily"]
        wide = portfolio.run_book(
            replace(development.BOOK, neutralize_leading_factor=True, factor_window=120),
            mu,
            excess,
            universe=prereg.UNIVERSE,
        )["daily"]
        assert not narrow[columns].equals(wide[columns])


class TestTheIdentityIsCheckedAgainstTheWholePanel:
    def _panel(self) -> dict[str, Any]:
        from scripts.research.model_learning import PAIRS_20

        index = pd.bdate_range("2021-01-04", periods=60)
        rng = np.random.default_rng(19)
        return {
            "pair_returns": pd.DataFrame(
                rng.standard_normal((len(index), len(PAIRS_20))) / 100.0,
                index=index,
                columns=list(PAIRS_20),
            )
        }

    def test_the_identity_is_verified_independently_on_a_full_panel(self) -> None:
        panel = self._panel()
        weights = np.array([0.25, -0.25, 0.10, -0.05, -0.05])
        excess = portfolio.universe_panel(panel, prereg.UNIVERSE)
        pairs = list(portfolio.tradable_pairs(prereg.UNIVERSE))
        #: recomputed here, not taken from the module under test
        routed = portfolio.split_map(prereg.UNIVERSE) @ weights
        through_pairs = panel["pair_returns"][pairs].to_numpy() @ routed
        direct = excess.to_numpy() @ weights
        residual = float(np.max(np.abs(direct - through_pairs)))
        assert residual < 1e-15
        assert portfolio.identity_check(panel, prereg.UNIVERSE, weights)["identity_holds"] is True
        #: the module's own number must be the one just computed here
        assert portfolio.identity_residual(panel, prereg.UNIVERSE, weights) == pytest.approx(
            residual, abs=1e-18
        )

    def test_a_pair_outside_the_universe_cannot_enter_the_panel(self) -> None:
        """The leakage this closure exists to prevent, at its source."""
        panel = self._panel()
        untouched = portfolio.universe_panel(panel, prereg.UNIVERSE)
        for pair in ("AUD_JPY", "CHF_JPY", "AUD_CAD", "NZD_USD"):
            panel["pair_returns"][pair] *= 50.0
        moved = portfolio.universe_panel(panel, prereg.UNIVERSE)
        pd.testing.assert_frame_equal(untouched, moved)

    def test_a_gap_in_a_pair_the_book_never_trades_costs_no_day(self) -> None:
        panel = self._panel()
        panel["pair_returns"].loc[panel["pair_returns"].index[5], "AUD_JPY"] = np.nan
        rebuilt = portfolio.universe_panel(panel, prereg.UNIVERSE)
        assert len(rebuilt) == len(panel["pair_returns"]), "only the routed pairs decide a day"

    def test_a_panel_built_from_every_pair_would_break_it(self) -> None:
        """The defect the closure exists to prevent, reproduced from the outside."""
        from scripts.research.model_learning import PAIRS_20

        panel = self._panel()
        currencies = list(prereg.UNIVERSE)
        weights = np.array([0.25, -0.25, 0.10, -0.05, -0.05])
        wrong = pd.DataFrame(index=panel["pair_returns"].index, columns=currencies, dtype=float)
        for currency in currencies:
            signed = [
                panel["pair_returns"][pair]
                if currency == pair.split("_")[0]
                else -panel["pair_returns"][pair]
                for pair in PAIRS_20
                if currency in pair.split("_")
            ]
            wrong[currency] = pd.concat(signed, axis=1).mean(axis=1)
        wrong = wrong.sub(wrong.mean(axis=1), axis=0)
        routed = portfolio.split_map(currencies) @ weights
        pairs = list(portfolio.tradable_pairs(currencies))
        gap = np.abs(wrong.to_numpy() @ weights - panel["pair_returns"][pairs].to_numpy() @ routed)
        assert float(np.max(gap)) > 1e-6, "the eight-currency definition must not satisfy it"

    def test_an_incomplete_day_is_reported_not_skipped(self) -> None:
        panel = self._panel()
        pairs = list(portfolio.tradable_pairs(prereg.UNIVERSE))
        panel["pair_returns"].loc[panel["pair_returns"].index[10], pairs[0]] = np.nan
        check = portfolio.identity_check(
            panel, prereg.UNIVERSE, np.array([0.25, -0.25, 0.10, -0.05, -0.05])
        )
        assert check["incomplete_pair_days_dropped_from_the_panel"] == 1
        assert check["incomplete_pair_days"] == 0
        assert check["identity_holds"] is True


class TestTheUniverseAwareRisk:
    ROOT_ARG = ROOT

    def test_the_margin_is_routed_over_this_universes_pairs_only(self) -> None:
        profile = risk.margin_per_unit_currency_gross(self.ROOT_ARG, prereg.UNIVERSE)
        assert profile["pairs"] == len(portfolio.tradable_pairs(prereg.UNIVERSE)) == 8
        assert profile["margin_p95"] > profile["margin_mean"], "p95, not a central value"
        assert 0.0 < profile["margin_mean"] < 0.06
        #: the eight-currency book is a different portfolio and must not be reported here
        eight = leverage.routing_profile(ROOT)["margin_per_unit_currency_gross"]
        assert profile["margin_p95"] != eight["p95"]

    def test_the_loss_cut_flag_follows_equity_against_margin(self) -> None:
        for target in (0.05, 0.10, 0.20, 0.40):
            row = risk.gap_stress(
                self.ROOT_ARG, prereg.UNIVERSE, vol_per_unit_gross=0.028, target_vol=target
            )
            assert row["loss_cut_on_gap"] == (row["maintenance_ratio_after_gap"] <= 1.0)
            assert row["equity_after_gap"] == pytest.approx(
                1.0 - row["gap_loss_at_leverage_tail"], abs=1e-6
            )

    def test_the_declared_shock_drives_the_gap_loss(self) -> None:
        assert risk.STRESS_CURRENCY_GAP == 0.20
        row = risk.gap_stress(
            self.ROOT_ARG, prereg.UNIVERSE, vol_per_unit_gross=0.028, target_vol=0.10
        )
        profile = risk.margin_per_unit_currency_gross(self.ROOT_ARG, prereg.UNIVERSE)
        expected = (
            row["risk_leverage_C_tail"]
            * profile["largest_currency_exposure_p95"]
            * risk.STRESS_CURRENCY_GAP
        )
        assert row["gap_loss_at_leverage_tail"] == pytest.approx(expected, abs=2e-3)

    def test_the_bound_is_where_the_flag_turns(self) -> None:
        bound = risk.feasible_target_vol(self.ROOT_ARG, prereg.UNIVERSE, 0.028)
        assert not risk.gap_stress(
            self.ROOT_ARG, prereg.UNIVERSE, vol_per_unit_gross=0.028, target_vol=bound * 0.98
        )["loss_cut_on_gap"]
        assert risk.gap_stress(
            self.ROOT_ARG, prereg.UNIVERSE, vol_per_unit_gross=0.028, target_vol=bound * 1.02
        )["loss_cut_on_gap"]

    def test_a_non_positive_sharpe_cannot_be_levered_into_a_return(self) -> None:
        for sharpe in (0.0, -0.5):
            row = risk.leverage_for_return(
                self.ROOT_ARG,
                prereg.UNIVERSE,
                vol_per_unit_gross=0.028,
                net_sharpe=sharpe,
                annual_target=0.05,
            )
            assert row["reachable"] is False
            assert "non-positive" in row["why"]

    def test_the_universes_own_volatility_is_required(self) -> None:
        #: no default: a caller cannot silently inherit Track 1's constant
        import inspect

        parameter = inspect.signature(risk.gap_stress).parameters["vol_per_unit_gross"]
        assert parameter.default is inspect.Parameter.empty
        low = risk.gap_stress(ROOT, prereg.UNIVERSE, vol_per_unit_gross=0.023, target_vol=0.10)[
            "risk_leverage_C_mean"
        ]
        high = risk.gap_stress(ROOT, prereg.UNIVERSE, vol_per_unit_gross=0.028, target_vol=0.10)[
            "risk_leverage_C_mean"
        ]
        assert low > high


class TestTheRepairedRerunBehaviour:
    def _stub_panel(self, first: str = "2021-05-03", days: int = 40) -> dict[str, Any]:
        from scripts.research.model_learning import PAIRS_20

        index = pd.bdate_range(first, periods=days)
        rng = np.random.default_rng(23)
        frame = pd.DataFrame(
            rng.standard_normal((len(index), len(PAIRS_20))) / 100.0,
            index=index,
            columns=list(PAIRS_20),
        )
        return {
            "pair_returns": frame,
            "currency_excess_return": pd.DataFrame(0.0, index=index, columns=list(CURRENCIES)),
        }

    @needs_local_caches
    def test_it_asks_for_the_frozen_lookback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.research.market_yields import fast_repair_check
        from scripts.research.model_learning import corpus

        seen: dict[str, Any] = {}

        def spy(yield_panel, excess, lookback=development.LOOKBACK):
            seen["lookback"] = lookback
            raise RuntimeError("stop here")

        monkeypatch.setattr(corpus, "currency_panel", lambda *a, **k: self._stub_panel())
        monkeypatch.setattr(development, "build_scores", spy)
        with pytest.raises(RuntimeError, match="stop here"):
            fast_repair_check.run()
        assert seen["lookback"] == development.LOOKBACK == 5

    def test_it_refuses_a_protected_span(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.research.market_yields import fast_repair_check
        from scripts.research.model_learning import corpus

        monkeypatch.setattr(
            corpus, "currency_panel", lambda *a, **k: self._stub_panel(first="2016-06-06")
        )
        from scripts.research.model_learning import ProtectedDataError

        with pytest.raises(ProtectedDataError):
            fast_repair_check.run()

    def test_the_recorded_numbers_are_internally_consistent(
        self, repaired_record: dict[str, Any]
    ) -> None:
        for name, book in repaired_record["books"].items():
            summary = book["summary"]
            assert summary["net_annual_return"] == pytest.approx(
                summary["gross_annual_return"] - summary["annual_cost"], abs=2e-4
            ), name
            assert summary["net_sharpe"] == pytest.approx(
                summary["net_annual_return"] / summary["realized_annual_vol"], abs=2e-3
            ), name
        #: and they are not the originals copied across
        for name, row in repaired_record["against_the_recorded_run"].items():
            assert row["repaired_gross_sharpe"] != row["original_gross_sharpe"], name


R2_DOC = ROOT / "docs/research/m15_track_r2_slow_repricing.md"


@pytest.fixture(scope="module")
def r2_record() -> dict[str, Any]:
    return json.loads((RECORDS / "development_r2.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def r2_document() -> str:
    return R2_DOC.read_text(encoding="utf-8")


class TestTheSlowRunFollowedItsPrereg:
    def test_it_ran_the_frozen_design(self, r2_record: dict[str, Any]) -> None:
        assert r2_record["prereg_digest"] == PREREG_R2_DIGEST
        assert r2_record["universe"] == list(prereg_r2.UNIVERSE)
        assert r2_record["prereg"]["signal"]["horizon_days"] == prereg_r2.PRIMARY_HORIZON_DAYS
        assert set(r2_record["books"]) == {
            "A_fast_5d_reference",
            "B_slow_rate_state",
            "C_fx_price_control",
            "D_residualised",
            "E_momentum_leg_of_D",
        }
        assert r2_record["protected_spans_read"] is False
        assert r2_record["identity_check"]["identity_holds"] is True

    def test_the_executed_book_is_the_declared_one(self, r2_record: dict[str, Any]) -> None:
        from scripts.research.market_yields import development_r2

        config = r2_record["executed_book_config"]
        #: JSON has no tuple, so a sequence field comes back as a list
        live = {
            field: list(value)
            if isinstance(value := getattr(development_r2.BOOK, field), tuple)
            else value
            for field in config
        }
        assert config == live
        assert config["neutralize_leading_factor"] is True, (
            "the prereg names the layer's own single pass"
        )
        assert config["vol_target"] == prereg_r2.PREREG["book_configuration"]["vol_target"]
        assert config["max_leverage"] == prereg_r2.PREREG["book_configuration"]["max_leverage"]

    def test_the_screen_is_the_frozen_one_and_stops(self, r2_record: dict[str, Any]) -> None:
        screen = r2_record["screen"]
        conditions = screen["shared_conditions"]
        assert len(conditions) == len(prereg_r2.PREREG["screen"]["shared_conditions"])
        assert screen["all_shared_conditions_hold"] is all(conditions.values())
        assert screen["decision"] == "stop"
        assert screen["verdict"] == "MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        assert screen["verdict"] in OUTCOMES
        assert screen["decision_grade"] is False
        #: the four that fail are the ones the document reports
        failing = {name for name, value in conditions.items() if not value}
        assert failing == set(screen["failing_conditions"])
        assert failing == {
            "net Sharpe stays positive at 1.5x and 2x cost",
            "the sign survives dropping any single currency",
            f"turnover at or below {prereg_r2.TURNOVER_BOUND:g}",
            "5% annual net is reachable inside the gap stress",
        }

    def test_the_capacity_condition_is_the_frozen_predicate_not_the_10pct_stress(
        self, r2_record: dict[str, Any]
    ) -> None:
        #: the frozen clause asks whether 5% net is reachable at a vol whose gap stress
        #: survives — not whether the stress survives at the book's declared 10% target
        conditions = r2_record["screen"]["shared_conditions"]
        capacity = r2_record["annual_return_capacity"]["0.05"]
        assert (
            conditions["5% annual net is reachable inside the gap stress"] is capacity["reachable"]
        )
        assert capacity["reachable"] is False
        #: and the weaker reading it replaced would have passed, which is why it matters
        assert r2_record["gap_stress_at_10pct_vol"]["loss_cut_on_gap"] is False

    def test_the_run_discloses_what_the_frozen_text_could_not_deliver(
        self, r2_record: dict[str, Any]
    ) -> None:
        clauses = {row["clause"] for row in r2_record["deviations_from_the_frozen_text"]}
        assert "D's rate-residual leg carries at least half of D's gross P&L" in clauses
        for row in r2_record["deviations_from_the_frozen_text"]:
            assert row["what_was_measured"] and row["why_it_was_not_changed"]

    def test_the_tiers_are_applied_as_frozen(self, r2_record: dict[str, Any]) -> None:
        from scripts.research.market_yields import development_r2

        net = r2_record["screen"]["primary_net_sharpe"]
        assert net < prereg_r2.MARGINAL_NET_SHARPE
        #: and had every condition held, the tier would follow the bands, not a choice
        books = {
            "B_slow_rate_state": {"summary": {"gross_sharpe": 1.0}},
            "C_fx_price_control": {"summary": {"net_sharpe": 0.0}},
            "D_residualised": {
                "summary": {
                    "net_sharpe": 0.25,
                    "turnover_round_trips_per_year_per_unit_gross": 20.0,
                    "annual_cost": 0.01,
                    "gross_annual_return": 0.05,
                },
                "blocks": [{"net_sharpe": 1.0}] * 6,
                "cost_stress": {"x1.5": 0.2, "x2": 0.1},
            },
        }
        screen = development_r2._screen(
            books,
            {"x": 1.0},
            {"rate_leg_share_of_d_gross": 0.9},
            {"0.05": {"reachable": True}},
        )
        assert screen["decision"] == "marginal"
        books["D_residualised"]["summary"]["net_sharpe"] = 0.35
        assert (
            development_r2._screen(
                books,
                {"x": 1.0},
                {"rate_leg_share_of_d_gross": 0.9},
                {"0.05": {"reachable": True}},
            )["decision"]
            == "candidate"
        )


class TestTheSlowRunEconomics:
    def test_the_central_diagnostic_is_answered_from_the_record(
        self, r2_record: dict[str, Any]
    ) -> None:
        fast = r2_record["books"]["A_fast_5d_reference"]["summary"]
        slow = r2_record["books"]["B_slow_rate_state"]["summary"]
        #: turnover fell and the gross survived — the informative side of the diagnostic
        assert (
            slow["turnover_round_trips_per_year_per_unit_gross"]
            < fast["turnover_round_trips_per_year_per_unit_gross"]
        )
        assert slow["gross_sharpe"] > fast["gross_sharpe"] > 0
        assert slow["net_sharpe"] > 0 > fast["net_sharpe"]

    def test_the_cost_identity_holds_for_every_book(self, r2_record: dict[str, Any]) -> None:
        for name, book in r2_record["books"].items():
            summary = book["summary"]
            assert summary["net_annual_return"] == pytest.approx(
                summary["gross_annual_return"] - summary["annual_cost"], abs=2e-4
            ), name

    def test_the_decomposition_is_reported_with_its_approximation(
        self, r2_record: dict[str, Any]
    ) -> None:
        decomposition = r2_record["decomposition_of_the_primary_test"]
        assert decomposition["rate_leg_share_of_d_gross"] >= 0.5
        assert decomposition["reconciliation_gap"] == pytest.approx(
            decomposition["d_gross_annual_return"]
            - decomposition["rate_leg_gross_annual_return"]
            - decomposition["momentum_leg_gross_annual_return"],
            abs=1e-5,
        )
        assert decomposition["beta_sd"] > 0
        assert len(decomposition["beta_p05_p95"]) == 2

    def test_leverage_cannot_rescue_a_break_even_book(self, r2_record: dict[str, Any]) -> None:
        assert r2_record["annual_return_capacity"]["0.05"]["reachable"] is False
        assert r2_record["gap_stress_at_10pct_vol"]["universe"] == list(prereg_r2.UNIVERSE)
        #: measured on this universe, not on the eight-currency book
        assert r2_record["gap_stress_at_10pct_vol"]["vol_per_unit_gross"] != pytest.approx(
            0.023288, abs=1e-6
        )

    def test_every_book_is_underpowered_against_the_prereg_s_own_bar(
        self, r2_record: dict[str, Any]
    ) -> None:
        bar = r2_record["feasibility_before_the_run"]["detectable_net_sharpe_at_80pct_power"]
        for book in r2_record["books"].values():
            assert abs(book["summary"]["gross_sharpe"]) < bar


class TestTheSlowDocument:
    def test_the_headline_numbers_come_from_the_record(
        self, r2_record: dict[str, Any], r2_document: str
    ) -> None:
        for name in ("B_slow_rate_state", "D_residualised"):
            summary = r2_record["books"][name]["summary"]
            for field in ("gross_sharpe", "net_sharpe"):
                text = f"{summary[field]:+.3f}".replace("-", "−")
                assert text in r2_document, (name, field, text)

    def test_the_document_states_the_verdict_and_its_scope(self, r2_document: str) -> None:
        assert "MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT" in r2_document
        assert "同じ gross を、4 割少ない売買で取れている" in r2_document
        #: the comparator the first draft got wrong must be named as corrected
        assert "主検定では gross は上がっていない" in r2_document
        assert "訂正する" in r2_document
        assert "decision-grade ではない" in r2_document
        assert FAMILY_BOUNDARY in r2_document
        assert "OIS" in r2_document
        assert "読んでいない" in r2_document

    def test_the_document_reports_the_four_failing_conditions(
        self, r2_record: dict[str, Any], r2_document: str
    ) -> None:
        assert "9 条件のうち **4 つ**が落ちる" in r2_document
        assert len(r2_record["screen"]["failing_conditions"]) == 4
        #: the capacity condition, and where the defect actually was
        assert "実装が凍結文から外れていた" in r2_document
        assert "97.8%" in r2_document

    def test_the_document_reports_the_cost_margin_and_the_ic(self, r2_document: str) -> None:
        for phrase in ("break-even cost 倍率", "1.066", "1.085", "無情報"):
            assert phrase in r2_document, phrase

    def test_the_document_does_not_read_the_leave_one_out_as_concentration(
        self, r2_document: str
    ) -> None:
        assert "「USD と JPY への集中」ではない" in r2_document
        assert "リターン定義そのものが変わる" in r2_document

    def test_the_document_forbids_the_rescues(self, r2_document: str) -> None:
        for phrase in (
            "horizon・符号・lookback・universe・control の変更",
            "turnover 上限 45 を結果後に緩める",
        ):
            assert phrase in r2_document

    def test_the_ledger_entry_matches_the_record(self, r2_record: dict[str, Any]) -> None:
        from scripts.research.round_a.ledger import LEDGER

        entry = next(e for e in LEDGER if e["id"] == "H-026")
        assert entry["prespecified"] is True
        assert entry["status"].startswith("CLOSED - MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED")
        assert "OIS" in entry["status"]
        for value in ("39.3", "+0.541", "+0.834", "59.8"):
            assert value in entry["result"], value


def _r2_panels(days: int = 160, seed: int = 11):
    """A synthetic yield panel and return panel on the T-R2 universe."""
    currencies = list(prereg_r2.UNIVERSE)
    index = pd.bdate_range("2022-01-03", periods=days)
    rng = np.random.default_rng(seed)
    excess = pd.DataFrame(
        rng.standard_normal((days, len(currencies))) / 100.0, index=index, columns=currencies
    )
    excess = excess.sub(excess.mean(axis=1), axis=0)
    yields = pd.DataFrame(
        np.cumsum(rng.standard_normal((days, len(currencies))) / 20.0, axis=0),
        index=index,
        columns=currencies,
    )
    return yields, excess


class TestTheSlowRunsCodeAndNotOnlyItsRecord:
    """These exercise `development_r2` itself, so a changed design fails a test.

    The record-reading tests above cannot see a change to the code that produced
    the record; these can, and each one corresponds to a mutation that survived an
    earlier review's mutation run.
    """

    def test_the_lookback_is_read_from_the_prereg_at_call_time(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scripts.research.market_yields import development_r2

        yields, excess = _r2_panels()
        base, _ = development_r2.build_scores(yields, excess)
        monkeypatch.setattr(prereg_r2, "PRIMARY_HORIZON_DAYS", 30)
        moved, _ = development_r2.build_scores(yields, excess)
        #: every book that depends on the slow window must move with the constant
        for name in ("B_slow_rate_state", "C_fx_price_control", "D_residualised"):
            assert not base[name].equals(moved[name]), name
        #: and the fast reference is the fast track's own lookback, untouched by it
        assert base["A_fast_5d_reference"].equals(moved["A_fast_5d_reference"])

    def test_the_sign_is_the_frozen_one(self) -> None:
        from scripts.research.market_yields import development, development_r2

        yields, excess = _r2_panels()
        scores, beta = development_r2.build_scores(yields, excess)
        slow = prereg_r2.PRIMARY_HORIZON_DAYS
        #: a rising yield is a positive score: the prereg's sign, not its negation
        expected = development._z(yields.diff(slow))
        pd.testing.assert_frame_equal(scores["B_slow_rate_state"], expected)
        assert prereg_r2.PREREG["signal"]["sign_frozen"] is True
        #: and the momentum leg is the negated control, scaled by the same beta
        pd.testing.assert_frame_equal(
            scores["E_momentum_leg_of_D"],
            -scores["C_fx_price_control"].mul(beta, axis=0),
        )

    def test_no_score_row_uses_a_value_dated_after_its_own_day(self) -> None:
        """The leakage that would matter most: a control reaching forward.

        Truncating the panels after day `t` must leave every score row up to `t`
        bit-identical. A `shift(-h)` anywhere in the construction breaks this.
        """
        from scripts.research.market_yields import development_r2

        yields, excess = _r2_panels()
        cut = 120
        full, _ = development_r2.build_scores(yields, excess)
        early, _ = development_r2.build_scores(yields.iloc[:cut], excess.iloc[:cut])
        for name, frame in early.items():
            pd.testing.assert_frame_equal(frame, full[name].iloc[:cut], obj=name)

    def test_perturbing_the_future_cannot_change_the_past(self) -> None:
        from scripts.research.market_yields import development_r2

        yields, excess = _r2_panels()
        cut = 120
        rng = np.random.default_rng(5)
        moved_excess = excess.copy()
        moved_yields = yields.copy()
        moved_excess.iloc[cut:] += rng.standard_normal(moved_excess.iloc[cut:].shape) / 50.0
        moved_yields.iloc[cut:] += rng.standard_normal(moved_yields.iloc[cut:].shape)
        base, _ = development_r2.build_scores(yields, excess)
        moved, _ = development_r2.build_scores(moved_yields, moved_excess)
        for name, frame in base.items():
            pd.testing.assert_frame_equal(frame.iloc[:cut], moved[name].iloc[:cut], obj=name)

    def test_every_pre_registered_book_is_built(self) -> None:
        from scripts.research.market_yields import development_r2

        yields, excess = _r2_panels()
        scores, _ = development_r2.build_scores(yields, excess)
        assert set(scores) == {
            "A_fast_5d_reference",
            "B_slow_rate_state",
            "C_fx_price_control",
            "D_residualised",
            "E_momentum_leg_of_D",
        }

    def test_the_residual_is_orthogonal_to_the_control_each_day(self) -> None:
        from scripts.research.market_yields import development_r2

        yields, excess = _r2_panels()
        scores, _ = development_r2.build_scores(yields, excess)
        rows = scores["D_residualised"].dropna(how="any")
        control = scores["C_fx_price_control"].loc[rows.index]
        for day in rows.index[:40]:
            assert float(rows.loc[day] @ control.loc[day]) == pytest.approx(0.0, abs=1e-9)


class TestTheSlowScreenIsTiedToItsConstants:
    def _books(self, *, net: float = 0.35, turnover: float = 20.0, stress: float = 0.2):
        return {
            "B_slow_rate_state": {"summary": {"gross_sharpe": 1.0}},
            "C_fx_price_control": {"summary": {"net_sharpe": 0.0}},
            "D_residualised": {
                "summary": {
                    "net_sharpe": net,
                    "turnover_round_trips_per_year_per_unit_gross": turnover,
                    "annual_cost": 0.01,
                    "gross_annual_return": 0.05,
                },
                "blocks": [{"net_sharpe": 1.0}] * 6,
                "cost_stress": {"x1.5": stress, "x2": stress},
            },
        }

    def _screen(self, books, *, share: float = 0.9, reachable: bool = True):
        from scripts.research.market_yields import development_r2

        return development_r2._screen(
            books,
            {"x": 1.0},
            {"rate_leg_share_of_d_gross": share},
            {"0.05": {"reachable": reachable}},
        )

    def test_the_turnover_bound_comes_from_the_prereg(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        books = self._books(turnover=50.0)
        assert self._screen(books)["decision"] == "stop"
        monkeypatch.setattr(prereg_r2, "TURNOVER_BOUND", 60.0)
        loosened = self._screen(books)
        assert loosened["decision"] == "candidate"
        #: and the condition is named by the constant, so a record cannot hide the change
        assert "turnover at or below 60" in loosened["shared_conditions"]

    def test_the_cost_stresses_are_the_frozen_multiples(self) -> None:
        from scripts.research.market_yields import development_r2

        assert development_r2.COST_STRESSES == (1.5, 2.0)
        name = "net Sharpe stays positive at 1.5x and 2x cost"
        assert name in self._screen(self._books())["shared_conditions"]

    def test_the_decomposition_threshold_is_a_half(self) -> None:
        clause = "D's rate-residual leg carries at least half of D's gross"
        assert self._screen(self._books(), share=0.5)["shared_conditions"][clause] is True
        assert self._screen(self._books(), share=0.49)["shared_conditions"][clause] is False
        assert self._screen(self._books(), share=0.49)["decision"] == "stop"

    def test_the_capacity_condition_follows_the_capacity_row(self) -> None:
        clause = "5% annual net is reachable inside the gap stress"
        assert self._screen(self._books(), reachable=False)["shared_conditions"][clause] is False
        assert self._screen(self._books(), reachable=False)["decision"] == "stop"
        assert self._screen(self._books(), reachable=True)["shared_conditions"][clause] is True

    def test_the_cost_stress_condition_is_not_hardcoded(self) -> None:
        clause = "net Sharpe stays positive at 1.5x and 2x cost"
        assert self._screen(self._books(stress=-0.1))["shared_conditions"][clause] is False
        assert self._screen(self._books(stress=-0.1))["decision"] == "stop"


class TestTheSlowRecordAttributesTheLegsToTheRightBooks:
    def test_the_rate_leg_is_book_b_and_the_momentum_leg_is_book_e(
        self, r2_record: dict[str, Any]
    ) -> None:
        decomposition = r2_record["decomposition_of_the_primary_test"]
        books = r2_record["books"]
        assert (
            decomposition["rate_leg_gross_annual_return"]
            == (books["B_slow_rate_state"]["summary"]["gross_annual_return"])
        )
        assert (
            decomposition["momentum_leg_gross_annual_return"]
            == (books["E_momentum_leg_of_D"]["summary"]["gross_annual_return"])
        )

    def test_the_ratio_is_reported_with_what_it_is_not(self, r2_record: dict[str, Any]) -> None:
        decomposition = r2_record["decomposition_of_the_primary_test"]
        text = decomposition["what_the_ratio_is_not"]
        assert "rather than a share of one book's P&L" in text
        assert "invariant to a positive per-day scalar" in text
        assert decomposition["unattributed_share_of_d_gross"] > 0.3
        #: the question the ratio was meant to answer, answered by something that can
        assert decomposition["d_daily_gross_correlation_with_rate_leg"] > 0.5
        assert abs(decomposition["d_daily_gross_correlation_with_momentum_leg"]) < 0.1

    def test_the_comparator_is_the_repaired_fast_residual(self, r2_record: dict[str, Any]) -> None:
        row = r2_record["against_the_repaired_fast_run"]["primary_residual"]
        #: the primary test's gross did not rise; the net improvement is the cost saved
        assert row["gross_sharpe"]["change"] < 0
        assert row["net_sharpe"]["change"] > 0
        assert row["annual_cost"]["change"] < 0
        assert row["gross_sharpe"]["fast_5d"] == pytest.approx(0.8625, abs=1e-4)

    def test_every_book_reports_its_break_even_cost_and_its_net_t(
        self, r2_record: dict[str, Any]
    ) -> None:
        for name, book in r2_record["books"].items():
            extra = book["extra"]
            assert extra["net_t_stat"] is not None, name
            assert extra["faithful_annual_implementation_cost"] > 0, name
        #: the two books with a positive gross are within 10% of their break-even cost
        for name in ("B_slow_rate_state", "D_residualised"):
            multiple = r2_record["books"][name]["extra"]["break_even_cost_multiple"]
            assert 1.0 < multiple < 1.1, (name, multiple)

    def test_the_measured_ic_is_reported_against_the_ic_the_costs_demand(
        self, r2_record: dict[str, Any]
    ) -> None:
        for name in ("B_slow_rate_state", "D_residualised"):
            comparison = r2_record["books"][name]["ic_comparison"]
            assert comparison["required_daily_ic_for_net_0_3_at_realised_turnover"] > 0
            #: every rate book's measured IC is negative, which the document must say
            assert comparison["observed_daily_equivalent_ic"] < 0, name

    def test_the_book_config_records_every_live_field(self, r2_record: dict[str, Any]) -> None:
        from dataclasses import fields

        from scripts.research.market_yields import development_r2

        live = {f.name for f in fields(development_r2.BOOK)}
        for recorded in (
            set(r2_record["executed_book_config"]),
            set(development_r2.executed_book_config()),
        ):
            missing = live - recorded
            assert not missing, f"these change the book and are not recorded: {sorted(missing)}"
        #: the one that had been omitted is live inside the vol targeter
        assert "leverage_hysteresis" in development_r2.executed_book_config()

    def test_the_legs_are_taken_from_the_pre_registered_books(self) -> None:
        """A leg sourced from the wrong book must change this function's output."""
        from scripts.research.market_yields import development_r2

        index = pd.bdate_range("2022-01-03", periods=8)
        books = {
            name: {"summary": {"gross_annual_return": value}}
            for name, value in (
                ("D_residualised", 0.10),
                ("B_slow_rate_state", 0.06),
                ("E_momentum_leg_of_D", -0.01),
            )
        }
        results = {
            name: {
                "daily": pd.DataFrame(
                    {"decision_day": index, "gross": np.linspace(-1.0, 1.0, len(index)) * scale}
                )
            }
            for name, scale in (
                ("D_residualised", 1.0),
                ("B_slow_rate_state", 1.0),
                ("E_momentum_leg_of_D", -1.0),
            )
        }
        beta = pd.Series(np.linspace(-0.2, 0.9, len(index)), index=index)
        out = development_r2.decompose_primary(books, results, beta)
        assert out["rate_leg_gross_annual_return"] == 0.06
        assert out["momentum_leg_gross_annual_return"] == -0.01
        assert out["rate_leg_share_of_d_gross"] == pytest.approx(0.6)
        assert out["unattributed_share_of_d_gross"] == pytest.approx(0.5)
        assert out["d_daily_gross_correlation_with_rate_leg"] == pytest.approx(1.0)
        assert out["d_daily_gross_correlation_with_momentum_leg"] == pytest.approx(-1.0)
        assert out["share_of_days_beta_negative"] > 0
