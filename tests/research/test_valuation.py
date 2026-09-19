"""T-V: the freeze, the exclusion at the request, and the run that followed them.

The first block runs against the pre-registration alone and would have passed
before a single FX byte existed. The rest exercise `development` itself — the
construction, the causality and the screen — rather than reading back the record
it wrote, so a change to the design fails a test.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.research.valuation import DATA_DIR, OUTCOMES, RECORD_DIR, TRACK, prereg, sources

ROOT = Path(__file__).resolve().parents[2]

#: The frozen T-V pre-registration, by content. Any edit to what it declares moves
#: this digest, so a post-result amendment cannot pass itself off as the frozen design.
PREREG_V_DIGEST = "bac5babf29cbbc515b95fd68e609ab536c3e499b03c485792104ade7c1fe5178"


class TestTheFrozenValuationPrereg:
    def test_the_declared_design_is_unchanged(self) -> None:
        digest = hashlib.sha256(
            json.dumps(prereg.PREREG, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        assert digest == PREREG_V_DIGEST, "the frozen pre-registration changed"

    def test_every_item_the_ruling_required_to_be_frozen_is_present(self) -> None:
        #: the ruling's section 23 list, item by item
        assert prereg.PREREG["data"]["fx"]
        assert prereg.PREREG["data"]["cpi"]
        assert prereg.SPAN == {"first": "1999-01-04", "last": "2016-06-01"}
        assert prereg.UNIVERSE == ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")
        assert prereg.CPI_PUBLICATION_LAG_MONTHS == 2
        assert prereg.PREREG["publication_lag"]["vintages"]
        assert "expanding-window mean" in prereg.PREREG["valuation_formula"]["anchor"]
        assert prereg.SPAN["last"] > prereg.WARM_UP_END
        assert prereg.PREREG["cadence"]["decision"]
        assert prereg.PREREG["cadence"]["rebalance"]
        assert prereg.PREREG["cost"]["convention"]
        assert prereg.PRIMARY_HORIZON_MONTHS == 3
        assert prereg.PREREG["benchmarks"]
        assert prereg.PREREG["screen"]["candidate"]
        assert prereg.PREREG["screen"]["stop"]

    def test_the_span_ends_before_the_protected_pool(self) -> None:
        assert prereg.SPAN["last"] < sources.PROTECTED_FROM
        assert prereg.SPAN["last"] == sources.REQUEST_END

    def test_the_screen_bands_are_disjoint_and_exhaustive(self) -> None:
        assert prereg.MARGINAL_NET_SHARPE < prereg.CANDIDATE_NET_SHARPE
        screen = prereg.PREREG["screen"]
        assert "every other outcome" in screen["stop"]
        assert f"at least {prereg.CANDIDATE_NET_SHARPE}" in screen["candidate"]
        assert (
            f"[{prereg.MARGINAL_NET_SHARPE}, {prereg.CANDIDATE_NET_SHARPE})"
            in (screen["marginal_candidate"])
        )
        #: a marginal result returns to Human; it never advances on its own
        assert "never for" in screen["marginal_candidate"]
        assert screen["no_automatic_progress_to_fresh"] is True

    def test_every_declared_status_is_an_allowed_outcome(self) -> None:
        screen = prereg.PREREG["screen"]
        declared = {v for k, v in screen.items() if k.startswith("status_")}
        assert declared == set(OUTCOMES)

    def test_the_sign_and_the_anchor_cannot_be_chosen_after_the_result(self) -> None:
        formula = prereg.PREREG["valuation_formula"]
        assert formula["sign_frozen"] is True
        assert "prohibited" in formula["no_full_sample_anchor"]
        assert "robustness check, never as a selection" in prereg.PREREG["robustness_anchor"]
        prohibited = " ".join(prereg.PREREG["prohibited_after_the_result"])
        for rescue in ("anchor", "horizon", "universe", "ML", "protected span"):
            assert rescue in prohibited

    def test_the_declaration_carries_no_result(self) -> None:
        source = (ROOT / "scripts/research/valuation/prereg.py").read_text(encoding="utf-8")
        for word in ("observed gross", "we found", "the result was", "net sharpe was"):
            assert word not in source.lower()

    def test_one_horizon_only(self) -> None:
        flat = json.dumps(prereg.PREREG)
        assert "horizon_months" not in flat or str(prereg.PRIMARY_HORIZON_MONTHS) in flat
        for other in (1, 6, 9, 12):
            assert f"{other}-month horizon" not in flat


class TestTheProtectedSpanIsExcludedAtTheRequest:
    @pytest.mark.parametrize("series", sources.FX, ids=lambda s: s.currency)
    def test_every_fx_request_ends_before_the_protected_pool(self, series: sources.Series) -> None:
        url = sources.fx_url(series)
        assert f"endPeriod={sources.REQUEST_END}" in url
        assert sources.REQUEST_END < sources.PROTECTED_FROM
        #: the bound is in the request, not in a filter applied to a wider download
        assert "startPeriod=" in url

    @pytest.mark.parametrize("end", ["2016-06-02", "2016-06-03", "2021-04-25", "2026-01-01"])
    def test_a_request_reaching_the_protected_pool_is_refused(self, end: str) -> None:
        with pytest.raises(ValueError):
            sources.fx_url(sources.FX[0], end=end)

    @pytest.mark.parametrize("end", ["2016-06", "2016-07", "2021-04"])
    def test_a_cpi_request_reaching_the_protected_pool_is_refused(self, end: str) -> None:
        with pytest.raises(ValueError):
            sources.cpi_url(sources.CPI[0], end=end)

    def test_the_cpi_request_stops_the_month_before(self) -> None:
        assert sources.CPI_REQUEST_END == "2016-05"
        assert sources.PROTECTED_FROM[:7] > sources.CPI_REQUEST_END

    def test_the_exclusion_rule_is_recorded_as_a_request_property(self) -> None:
        rule = sources.EXCLUSION["rule"]
        assert "never by a local filter" in rule
        assert sources.EXCLUSION["if_a_source_cannot_be_bounded"] == "it is not used"
        assert "maximum observation date" in sources.EXCLUSION["guard"]

    def test_the_universe_and_the_series_agree(self) -> None:
        #: EUR is the numeraire, so it has no FX series of its own but must have a CPI
        assert {s.currency for s in sources.FX} == set(prereg.UNIVERSE) - {"EUR"}
        assert {s.currency for s in sources.CPI} == set(prereg.UNIVERSE)

    def test_the_accidental_early_fetch_is_disclosed_rather_than_omitted(self) -> None:
        doc = sources.__doc__ or ""
        assert "Disclosure" in doc
        assert "preceded this pre-registration" in doc


class TestTheTrackConstants:
    def test_the_track_is_named_and_its_outputs_are_non_decision_bearing(self) -> None:
        assert TRACK == "T-V"
        module_doc = __import__("scripts.research.valuation", fromlist=["x"]).__doc__ or ""
        assert "NON_DECISION_BEARING_EXPLORATORY_ONLY" in module_doc
        assert "RESEARCH_SCRATCH_NON_AUTHORITATIVE" in module_doc

    def test_acquired_data_lands_outside_the_committed_tree(self) -> None:
        assert DATA_DIR.startswith("artifacts/track_a_scratch/")
        assert RECORD_DIR.startswith("artifacts/research/")

    def test_the_span_once_read_can_never_be_confirmation(self) -> None:
        status = prereg.PREREG["data"]["status_of_the_span_once_read"]
        assert "EXPLORATORY_SEEN_DEVELOPMENT_DATA" in status
        assert "never available for confirmation" in status


RECORDS = ROOT / "artifacts/research/valuation"
V_DOC = ROOT / "docs/research/m15_track_v_real_exchange_rate_valuation.md"


@pytest.fixture(scope="module")
def v_record() -> dict[str, Any]:
    return json.loads((RECORDS / "development.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def v_document() -> str:
    return V_DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def acquisition() -> dict[str, Any]:
    return json.loads((RECORDS / "acquisition.json").read_text(encoding="utf-8"))


def _synthetic(months: int = 200, seed: int = 7):
    """A daily FX panel per euro and a monthly CPI panel on the frozen universe."""
    currencies = list(prereg.UNIVERSE)
    days = pd.bdate_range("1999-01-04", periods=months * 21)
    rng = np.random.default_rng(seed)
    drift = np.cumsum(rng.standard_normal((len(days), len(currencies))) / 300.0, axis=0)
    fx = pd.DataFrame(np.exp(drift), index=days, columns=currencies)
    fx["EUR"] = 1.0
    fx = fx[currencies]
    periods = pd.period_range("1994-01", periods=months + 80, freq="M").astype(str)
    inflation = np.cumsum(np.abs(rng.standard_normal((len(periods), len(currencies)))) / 400.0, 0)
    #: a different base year per currency, which the anchor is supposed to absorb
    bases = np.array([50.0, 80.0, 100.0, 120.0, 60.0, 90.0, 110.0, 70.0])
    cpi = pd.DataFrame(np.exp(inflation) * bases, index=periods, columns=currencies)
    return fx, cpi


class TestTheValuationConstruction:
    def test_the_anchor_minimum_comes_from_the_prereg(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        base = development.build_signals(fx, cpi, days)["A_valuation"].dropna(how="any")
        monkeypatch.setattr(prereg, "MIN_ANCHOR_MONTHS", 24)
        shorter = development.build_signals(fx, cpi, days)["A_valuation"].dropna(how="any")
        #: a shorter warm-up must start earlier; nothing else may change
        assert shorter.index[0] < base.index[0]
        assert len(shorter) > len(base)

    def test_the_cpi_lag_comes_from_the_prereg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        frozen_lag = prereg.CPI_PUBLICATION_LAG_MONTHS
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        base = development._lagged_log_cpi(cpi, days)
        #: with the frozen lag, the value on a decision day is month M-2's, never M's
        day = days[100]
        wanted = (pd.Period(day, freq="M") - frozen_lag).strftime("%Y-%m")
        assert base.loc[day, "USD"] == pytest.approx(float(np.log(cpi.loc[wanted, "USD"])))
        monkeypatch.setattr(prereg, "CPI_PUBLICATION_LAG_MONTHS", 0)
        unlagged = development._lagged_log_cpi(cpi, days)
        assert not base.equals(unlagged)

    def test_no_cpi_value_reaches_its_own_month(self) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        lagged = development._lagged_log_cpi(cpi, days)
        logged = np.log(cpi.astype(float))
        for day in days[60:70]:
            month = pd.Period(day, freq="M").strftime("%Y-%m")
            #: the current month's index must not appear anywhere on that row
            assert not np.isclose(lagged.loc[day].to_numpy(), logged.loc[month].to_numpy()).any()

    def test_an_arbitrary_cpi_base_year_cannot_change_the_signal(self) -> None:
        """Rebasing a country's index is a constant in logs, and the anchor removes it."""
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        base = development.build_signals(fx, cpi, days)
        rebased = cpi.copy()
        rebased["JPY"] = rebased["JPY"] * 3.7
        rebased["GBP"] = rebased["GBP"] / 11.0
        moved = development.build_signals(fx, rebased, days)
        for name, frame in base.items():
            pd.testing.assert_frame_equal(frame, moved[name], obj=name, atol=1e-12)

    def test_the_sign_is_frozen_undervalued_is_positive(self) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        nominal = development._demean(-np.log(fx.loc[days].astype(float)))
        prices = development._demean(development._lagged_log_cpi(cpi, days))
        real = nominal + prices
        deviation = (real - development._expanding_anchor(real)).dropna(how="any")
        signal = development.build_signals(fx, cpi, days)["A_valuation"].dropna(how="any")
        day = deviation.index[50]
        #: the most overvalued currency carries the most negative score, and vice versa
        assert signal.loc[day].idxmin() == deviation.loc[day].idxmax()
        assert signal.loc[day].idxmax() == deviation.loc[day].idxmin()
        assert prereg.PREREG["valuation_formula"]["sign_frozen"] is True

    def test_the_control_carries_the_same_sign_convention(self) -> None:
        """B is the nominal deviation under the same sign, or it is not a control."""
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        nominal = development._demean(-np.log(fx.loc[days].astype(float)))
        deviation = (nominal - development._expanding_anchor(nominal)).dropna(how="any")
        control = development.build_signals(fx, cpi, days)["B_nominal_control"].dropna(how="any")
        day = deviation.index[50]
        assert control.loc[day].idxmin() == deviation.loc[day].idxmax()
        assert control.loc[day].idxmax() == deviation.loc[day].idxmin()

    def test_the_price_level_term_actually_enters_the_valuation_signal(self) -> None:
        """Without it, A is B and the primary test is identically zero."""
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        signals = development.build_signals(fx, cpi, days)
        valuation = signals["A_valuation"].dropna(how="any")
        control = signals["B_nominal_control"].dropna(how="any")
        assert not np.allclose(valuation.to_numpy(), control.to_numpy())
        #: and what survives the control is not identically zero either
        residual = signals["C_residualised"].dropna(how="any")
        assert float(np.abs(residual.to_numpy()).max()) > 1e-6
        #: changing relative inflation must move the valuation signal but not the control
        faster = cpi.copy()
        faster["JPY"] = faster["JPY"] * np.linspace(1.0, 1.4, len(faster))
        moved = development.build_signals(fx, faster, days)
        assert not moved["A_valuation"].dropna(how="any").equals(valuation)
        pd.testing.assert_frame_equal(
            moved["B_nominal_control"].dropna(how="any"), control, atol=1e-12
        )

    def test_no_signal_row_uses_a_month_after_its_own(self) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        cut = 150
        full = development.build_signals(fx, cpi, days)
        early = development.build_signals(fx, cpi, days[:cut])
        for name, frame in early.items():
            pd.testing.assert_frame_equal(frame, full[name].iloc[:cut], obj=name)

    def test_perturbing_the_future_cannot_change_the_past(self) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        cut = 150
        moved_fx = fx.copy()
        moved_fx.loc[days[cut] :] *= 1.35
        moved_cpi = cpi.copy()
        moved_cpi.iloc[-40:] *= 1.2
        base = development.build_signals(fx, cpi, days)
        moved = development.build_signals(moved_fx, moved_cpi, days)
        for name, frame in base.items():
            pd.testing.assert_frame_equal(
                frame.iloc[:cut], moved[name].iloc[:cut], obj=name, atol=1e-12
            )

    def test_the_residual_is_orthogonal_to_the_control_each_month(self) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        signals = development.build_signals(fx, cpi, days)
        rows = signals["C_residualised"].dropna(how="any")
        control = signals["B_nominal_control"].loc[rows.index]
        for day in rows.index[:30]:
            assert float(rows.loc[day] @ control.loc[day]) == pytest.approx(0.0, abs=1e-9)

    def test_the_monthly_decision_is_held_and_never_anticipated(self) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        calendar = pd.DatetimeIndex(fx.index)
        days = development._decision_days(calendar)
        signal = development.build_signals(fx, cpi, days)["A_valuation"]
        held = development.daily_mu(signal, calendar)
        usable = signal.dropna(how="any")
        #: on a decision day the held target is that day's decision
        for day in usable.index[:20]:
            pd.testing.assert_series_equal(
                held.loc[day], usable.loc[day], check_names=False, atol=1e-12
            )
        #: between decisions it does not move, so the band produces no trade
        first, second = usable.index[5], usable.index[6]
        between = held.loc[first:second].iloc[:-1]
        assert (between.nunique() == 1).all()

    def test_the_price_of_a_pair_is_the_cross_rate(self) -> None:
        from scripts.research.valuation import development

        fx, _ = _synthetic()
        returns = development.pair_return_panel(fx)
        expected = (fx["JPY"] / fx["USD"]).pct_change().dropna()
        pd.testing.assert_series_equal(
            returns["USD_JPY"].dropna(), expected, check_names=False, atol=1e-12
        )
        #: EUR is the numeraire, so EUR_USD is just the quoted rate
        pd.testing.assert_series_equal(
            returns["EUR_USD"].dropna(),
            fx["USD"].pct_change().dropna(),
            check_names=False,
            atol=1e-12,
        )

    def test_the_tercile_ordering_is_measured_cheap_to_dear(self) -> None:
        from scripts.research.valuation import development

        index = pd.bdate_range("2004-01-01", periods=400)
        currencies = list(prereg.UNIVERSE)
        rng = np.random.default_rng(3)
        signal = pd.DataFrame(
            rng.standard_normal((20, len(currencies))), index=index[::20][:20], columns=currencies
        )
        #: a panel in which the cheap tercile really does earn more
        excess = pd.DataFrame(0.0, index=index, columns=currencies)
        for day in signal.index:
            ranked = signal.loc[day].rank(pct=True)
            after = index[(index > day)][:63]
            for currency in currencies:
                step = (
                    0.001
                    if ranked[currency] > 2 / 3
                    else (-0.001 if ranked[currency] <= 1 / 3 else 0.0)
                )
                excess.loc[after, currency] = step
        out = development._terciles(signal, excess, 3)
        assert out["monotone_cheap_to_dear"] is True
        cheap, mid, dear = out["mean_forward_excess_return_cheap_mid_dear"]
        assert cheap > mid > dear


class TestTheValuationScreen:
    def _books(self, *, net=0.35, turnover=2.0, monotone=True, stress=0.2, best_year=True):
        summary = {
            "gross_sharpe": net,
            "net_sharpe": net,
            "turnover_round_trips_per_year_per_unit_gross": turnover,
            "mean_currency_gross": 3.0,
            "realized_annual_vol": 0.10,
        }
        book = {
            "summary": dict(summary),
            "blocks": [{"net_sharpe": 1.0}] * 6,
            "per_currency_gross_pnl": dict.fromkeys(prereg.UNIVERSE, 0.1),
            "terciles": {"monotone_cheap_to_dear": monotone},
            "worst_year": {"sign_survives_removing_the_best_year": best_year},
            "cost_stress": {"x2": stress, "x3": stress},
        }
        return {
            "A_valuation": {"summary": {"gross_sharpe": 1.0}},
            "B_nominal_control": {"summary": {"net_sharpe": 0.0}},
            "C_residualised": book,
        }

    def _screen(self, books, *, drops=None, reachable=True, vol=0.10, robust=1.0):
        from scripts.research.valuation import development

        return development._screen(
            books,
            {"C_residualised": {"net_sharpe": robust}},
            drops if drops is not None else dict.fromkeys(prereg.UNIVERSE, 1.0),
            {"0.05": {"reachable": reachable, "target_vol": vol}},
        )

    def test_the_bands_are_the_frozen_ones(self) -> None:
        assert self._screen(self._books(net=0.30))["decision"] == "candidate"
        assert self._screen(self._books(net=0.29))["decision"] == "marginal"
        assert self._screen(self._books(net=0.25))["decision"] == "marginal"
        assert self._screen(self._books(net=0.24))["decision"] == "stop"

    def test_a_marginal_tier_needs_half_the_turnover_bound(self) -> None:
        bound = prereg.TURNOVER_BOUND
        assert self._screen(self._books(net=0.27, turnover=bound / 2))["decision"] == "marginal"
        assert self._screen(self._books(net=0.27, turnover=bound / 2 + 0.1))["decision"] == "stop"

    def test_the_turnover_bound_comes_from_the_prereg(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        books = self._books(turnover=20.0)
        assert self._screen(books)["decision"] == "stop"
        monkeypatch.setattr(prereg, "TURNOVER_BOUND", 40.0)
        loosened = self._screen(books)
        assert loosened["decision"] == "candidate"
        assert "turnover at or below 40" in loosened["shared_conditions"]

    def test_the_cost_stresses_are_the_frozen_multiples(self) -> None:
        assert prereg.COST_STRESSES == (2.0, 3.0)
        clause = "net Sharpe stays positive at 2x and 3x cost"
        assert self._screen(self._books())["shared_conditions"][clause] is True
        assert self._screen(self._books(stress=-0.01))["shared_conditions"][clause] is False

    def test_each_frozen_condition_can_fail_on_its_own(self) -> None:
        cases = {
            "forward return falls monotonically from the cheap tercile to the dear one": (
                self._books(monotone=False),
                {},
            ),
            "removing the best twelve-month window leaves the sign": (
                self._books(best_year=False),
                {},
            ),
            "the sign survives dropping any one of the eight": (
                self._books(),
                {"drops": {**dict.fromkeys(prereg.UNIVERSE, 1.0), "without_JPY": -0.1}},
            ),
            "5% annual net is reachable at a volatility at most 15% whose gap stress survives": (
                self._books(),
                {"reachable": False},
            ),
            "the sign is unchanged under the declared robustness anchor": (
                self._books(),
                {"robust": -1.0},
            ),
        }
        for clause, (books, kwargs) in cases.items():
            screen = self._screen(books, **kwargs)
            assert screen["shared_conditions"][clause] is False, clause
            assert screen["decision"] == "stop", clause
            assert clause in screen["failing_conditions"], clause

    def test_a_15pct_volatility_is_the_bound_not_merely_reachability(self) -> None:
        clause = "5% annual net is reachable at a volatility at most 15% whose gap stress survives"
        assert self._screen(self._books(), vol=0.15)["shared_conditions"][clause] is True
        assert self._screen(self._books(), vol=0.151)["shared_conditions"][clause] is False

    def test_every_verdict_is_an_allowed_outcome(self) -> None:
        for books in (self._books(net=0.35), self._books(net=0.27), self._books(net=0.1)):
            assert self._screen(books)["verdict"] in OUTCOMES


class TestTheValuationRun:
    def test_it_ran_the_frozen_design(self, v_record: dict[str, Any]) -> None:
        assert v_record["prereg_digest"] == PREREG_V_DIGEST
        assert v_record["universe"] == list(prereg.UNIVERSE)
        assert v_record["protected_spans_read"] is False
        assert v_record["identity_check"]["identity_holds"] is True
        assert v_record["identity_check"]["incomplete_pair_days"] == 0
        assert set(v_record["books"]) == {"A_valuation", "B_nominal_control", "C_residualised"}

    def test_the_span_stops_before_the_protected_pool(self, v_record: dict[str, Any]) -> None:
        assert v_record["span"]["last"] < sources.PROTECTED_FROM
        assert v_record["span"]["last"] == prereg.SPAN["last"]
        assert v_record["span"]["first"] >= prereg.SPAN["first"]

    def test_the_book_config_records_every_live_field(self, v_record: dict[str, Any]) -> None:
        from dataclasses import fields

        from scripts.research.valuation import development

        live = {f.name for f in fields(development.BOOK)}
        assert not live - set(v_record["executed_book_config"])

    def test_the_screen_stops_and_names_what_failed(self, v_record: dict[str, Any]) -> None:
        screen = v_record["screen"]
        assert screen["decision"] == "stop"
        assert screen["verdict"] == "REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT"
        assert screen["decision_grade"] is False
        assert len(screen["shared_conditions"]) == 12
        assert set(screen["failing_conditions"]) == {
            "forward return falls monotonically from the cheap tercile to the dear one",
            "a majority of the temporal blocks are positive",
            "no single currency carries more than half of the gross",
            "the sign survives dropping any one of the eight",
            "removing the best twelve-month window leaves the sign",
            "5% annual net is reachable at a volatility at most 15% whose gap stress survives",
        }
        #: and it would have stopped on the band alone
        assert screen["primary_net_sharpe"] < prereg.MARGINAL_NET_SHARPE

    def test_cost_is_not_what_decided_this_one(self, v_record: dict[str, Any]) -> None:
        """The finding that is new for the programme, asserted rather than narrated."""
        primary = v_record["books"]["C_residualised"]
        assert primary["summary"]["turnover_round_trips_per_year_per_unit_gross"] < 2.0
        assert primary["summary"]["annual_cost"] < 0.002
        assert primary["extra"]["break_even_cost_multiple"] > 10.0
        assert all(value > 0 for value in primary["cost_stress"].values())
        #: the pre-registered turnover bound was met with an order of magnitude to spare
        assert (
            primary["summary"]["turnover_round_trips_per_year_per_unit_gross"]
            < prereg.TURNOVER_BOUND / 5
        )

    def test_the_predicted_ordering_is_not_separable_from_the_nominal_control(
        self, v_record: dict[str, Any]
    ) -> None:
        books = v_record["books"]
        assert books["A_valuation"]["terciles"]["monotone_cheap_to_dear"] is True
        assert books["B_nominal_control"]["terciles"]["monotone_cheap_to_dear"] is True
        assert books["C_residualised"]["terciles"]["monotone_cheap_to_dear"] is False
        #: the control's cheap-to-dear spread is the wider one
        spread = {
            name: book["terciles"]["mean_forward_excess_return_cheap_mid_dear"][0]
            - book["terciles"]["mean_forward_excess_return_cheap_mid_dear"][2]
            for name, book in books.items()
        }
        assert spread["B_nominal_control"] > spread["A_valuation"] > 0
        assert v_record["books"]["C_residualised"]["ic_at_the_primary_horizon"] < 0

    def test_nothing_here_is_separable_from_zero(self, v_record: dict[str, Any]) -> None:
        bar = v_record["power"]["detectable_net_sharpe_at_80pct_power"]
        for name, book in v_record["books"].items():
            assert abs(book["summary"]["net_sharpe"]) < bar, name
            assert abs(book["extra"]["net_t_stat"]) < 2.0, name

    def test_the_shortfalls_are_disclosed_with_their_direction(
        self, v_record: dict[str, Any]
    ) -> None:
        shortfalls = v_record["disclosed_shortfalls"]
        assert any("spot return" in row["what"] for row in shortfalls)
        assert any("vintage" in row["what"] for row in shortfalls)
        for row in shortfalls:
            assert row["why"] and row["direction"]

    def test_the_cost_identity_holds_for_every_book(self, v_record: dict[str, Any]) -> None:
        for name, book in v_record["books"].items():
            summary = book["summary"]
            assert summary["net_annual_return"] == pytest.approx(
                summary["gross_annual_return"] - summary["annual_cost"], abs=2e-4
            ), name


class TestTheValuationDocument:
    def test_the_headline_numbers_come_from_the_record(
        self, v_record: dict[str, Any], v_document: str
    ) -> None:
        for name in ("A_valuation", "C_residualised"):
            summary = v_record["books"][name]["summary"]
            for field in ("gross_sharpe", "net_sharpe"):
                text = f"{summary[field]:+.3f}".replace("-", "−")
                assert text in v_document, (name, field, text)

    def test_the_document_states_the_verdict_and_its_scope(self, v_document: str) -> None:
        assert "REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT" in v_document
        assert "読んでいない" in v_document
        assert "request 側で除外" in v_document
        #: the finding, and the thing it must not be read as
        assert "cost が結論を壊さない book が出た" in v_document
        assert "「実質為替 valuation に内容が無い」" in v_document
        assert "spot-only" in v_document

    def test_the_document_reports_the_inverted_ordering(self, v_document: str) -> None:
        assert "逆転" in v_document
        assert "名目の平均回帰" in v_document

    def test_the_document_forbids_the_rescues(self, v_document: str) -> None:
        for phrase in ("carry leg の追加もこれに含まれる", "保護 span の読み取り"):
            assert phrase in v_document

    def test_the_ledger_entry_matches_the_record(self, v_record: dict[str, Any]) -> None:
        from scripts.research.round_a.ledger import LEDGER

        entry = next(e for e in LEDGER if e["id"] == "H-027")
        assert entry["prespecified"] is True
        assert entry["status"].startswith(
            "CLOSED - REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT"
        )
        assert entry["document"] == "docs/research/m15_track_v_real_exchange_rate_valuation.md"
        assert (ROOT / entry["document"]).exists()
        for value in ("1.25", "0.789", "10.7", "-5.57", "-3.34"):
            assert value in entry["result"], value


class TestTheRequestBoundIsParsedNotCompared:
    """A lexicographic test on the caller's object is not a bound. Both defeats below
    were verified against the first version of these builders."""

    @pytest.mark.parametrize("end", ["2016-06", "2016", "2016-06-0", "", "2016-6-2", "20160601"])
    def test_a_bound_that_is_not_an_exact_day_is_refused(self, end: str) -> None:
        #: "2016-06" sorts below "2016-06-02" but the server reads it as the end of June
        with pytest.raises(ValueError):
            sources.fx_url(sources.FX[0], end=end)

    @pytest.mark.parametrize("end", ["2016", "", "2016-6", "2016-13", "2016-06-01"])
    def test_a_monthly_bound_that_is_not_an_exact_month_is_refused(self, end: str) -> None:
        with pytest.raises(ValueError):
            sources.cpi_url(sources.CPI[0], end=end)

    def test_a_str_subclass_that_lies_about_ordering_is_refused(self) -> None:
        class Sneaky(str):
            def __ge__(self, other: object) -> bool:
                return False

            def __gt__(self, other: object) -> bool:
                return False

        with pytest.raises(ValueError):
            sources.fx_url(sources.FX[0], end=Sneaky("2026-01-01"))
        with pytest.raises(ValueError):
            sources.cpi_url(sources.CPI[0], end=Sneaky("2026-01"))
        #: and the same trick on the start bound
        with pytest.raises(ValueError):
            sources.fx_url(sources.FX[0], start=Sneaky("1999-01-04"))

    @pytest.mark.parametrize("end", [None, 20160601, 2016.06])
    def test_a_non_string_bound_is_refused(self, end: object) -> None:
        with pytest.raises(ValueError):
            sources.fx_url(sources.FX[0], end=end)  # type: ignore[arg-type]

    def test_a_request_that_starts_after_it_ends_is_refused(self) -> None:
        with pytest.raises(ValueError):
            sources.fx_url(sources.FX[0], start="2015-01-01", end="2014-01-01")

    def test_the_frozen_defaults_still_build(self) -> None:
        assert sources.fx_url(sources.FX[0]).endswith(f"endPeriod={sources.REQUEST_END}")
        assert sources.cpi_url(sources.CPI[0]).endswith(f"endPeriod={sources.CPI_REQUEST_END}")


class TestTheAcquisitionRefusesProtectedData:
    """`acquire` is the code that turns a request into bytes on disk, so its refusal
    path is the one that matters most and it had no test at all."""

    def _frame(self, periods: list[str]) -> pd.DataFrame:
        return pd.DataFrame({"period": periods, "value": range(len(periods))})

    def test_a_clean_daily_frame_passes(self) -> None:
        from scripts.research.valuation import acquire

        acquire.guard(self._frame(["1999-01-04", "2016-06-01"]), label="fx:USD")

    @pytest.mark.parametrize(
        "periods",
        [
            ["1999-01-04", "2016-06-02"],
            ["1999-01-04", "2021-04-25"],
            ["2016-06-02"],
            #: the protected row is not last: a guard reading iloc[-1] would miss it
            ["1999-01-04", "2016-06-02", "2000-01-04"],
        ],
    )
    def test_a_frame_reaching_the_protected_span_is_refused(self, periods: list[str]) -> None:
        from scripts.research.valuation import acquire

        with pytest.raises(acquire.ProtectedDataError):
            acquire.guard(self._frame(periods), label="fx:USD")

    def test_the_boundary_day_itself_is_refused(self) -> None:
        from scripts.research.valuation import acquire

        #: 2016-06-02 is the first protected day, so `>=` and not `>`
        with pytest.raises(acquire.ProtectedDataError):
            acquire.guard(self._frame(["2016-06-02"]), label="fx:USD")
        acquire.guard(self._frame(["2016-06-01"]), label="fx:USD")

    @pytest.mark.parametrize("periods", [["2016-05"], ["1994-01", "2016-05"]])
    def test_a_clean_monthly_frame_passes(self, periods: list[str]) -> None:
        from scripts.research.valuation import acquire

        acquire.guard(self._frame(periods), label="cpi:USD")

    @pytest.mark.parametrize("periods", [["2016-06"], ["1994-01", "2021-04"]])
    def test_a_monthly_frame_reaching_the_protected_span_is_refused(
        self, periods: list[str]
    ) -> None:
        from scripts.research.valuation import acquire

        with pytest.raises(acquire.ProtectedDataError):
            acquire.guard(self._frame(periods), label="cpi:USD")

    def test_a_response_mixing_period_formats_is_refused(self) -> None:
        from scripts.research.valuation import acquire

        #: a bound that cannot be compared is not a bound
        with pytest.raises(acquire.ProtectedDataError):
            acquire.guard(self._frame(["2016-05", "2016-05-31"]), label="cpi:USD")

    def test_an_empty_response_is_refused(self) -> None:
        from scripts.research.valuation import acquire

        with pytest.raises(RuntimeError):
            acquire.guard(self._frame([]), label="fx:USD")

    def test_acquiring_without_the_opt_in_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.research.valuation import acquire

        #: `_fetch` is stubbed as well as the opt-in being absent. The opt-in is the
        #: behaviour under test, so this test must not rely on it to stay offline — a
        #: mutation that removed the check once let this very test reach the network
        #: and overwrite a committed provenance artefact.
        def refuse(url: str) -> bytes:
            raise AssertionError(f"the network was reached: {url}")

        monkeypatch.setattr(acquire, "_fetch", refuse)
        monkeypatch.setattr(acquire, "_fetch_via_curl", refuse)
        monkeypatch.setattr(
            pathlib.Path, "write_text", lambda *a, **k: pytest.fail("the record was written")
        )
        monkeypatch.delenv(acquire.OPT_IN_ENV, raising=False)
        with pytest.raises(RuntimeError, match=acquire.OPT_IN_ENV):
            acquire.acquire()
        assert acquire.main() == 2

    def test_a_run_that_acquired_nothing_leaves_the_record_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty record is not provenance; it would erase the acquisition that was."""
        from scripts.research.valuation import acquire

        monkeypatch.setenv(acquire.OPT_IN_ENV, "1")
        monkeypatch.setattr(
            acquire, "_fetch", lambda url: (_ for _ in ()).throw(RuntimeError("offline"))
        )
        monkeypatch.setattr(
            pathlib.Path, "write_text", lambda *a, **k: pytest.fail("the record was written")
        )
        with pytest.raises(RuntimeError, match="no series was acquired"):
            acquire.acquire()

    def test_a_refused_series_never_reaches_the_disk(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The write must be unreachable from the refusal path, not merely skipped."""
        from scripts.research.valuation import acquire

        written: list[str] = []
        monkeypatch.setenv(acquire.OPT_IN_ENV, "1")
        monkeypatch.setattr(
            acquire, "_fetch", lambda url: b"TIME_PERIOD,OBS_VALUE\n2016-06-02,1.0\n"
        )
        monkeypatch.setattr(
            acquire, "_fetch_via_curl", lambda url: pytest.fail(f"network reached: {url}")
        )
        #: and the record itself must not be overwritten by a refused run
        monkeypatch.setattr(
            pathlib.Path, "write_text", lambda *a, **k: pytest.fail("record written")
        )
        monkeypatch.setattr(
            pd.DataFrame, "to_parquet", lambda self, *a, **k: written.append(str(a))
        )
        with pytest.raises(acquire.ProtectedDataError):
            acquire.acquire()
        assert written == [], "a frame reaching the protected span was written to disk"


class TestTheAcquiredFilesAreInsideTheBound:
    def test_no_acquired_observation_reaches_the_protected_span(
        self, acquisition: dict[str, Any]
    ) -> None:
        data = ROOT / DATA_DIR
        checked = 0
        for kind in ("fx", "cpi"):
            for currency in acquisition[kind]:
                path = data / f"{kind}_{currency.lower()}.parquet"
                if not path.is_file():
                    pytest.skip("the acquired series are untracked local artefacts")
                periods = pd.read_parquet(path)["period"].astype(str)
                bound = sources.PROTECTED_FROM[: len(periods.iloc[0])]
                assert periods.max() < bound, (kind, currency, periods.max())
                checked += 1
        assert checked == 15

    def test_every_recorded_request_carries_the_bound(self, acquisition: dict[str, Any]) -> None:
        assert acquisition["unreachable"] == {}
        for kind, bound in (("fx", sources.REQUEST_END), ("cpi", sources.CPI_REQUEST_END)):
            for currency, block in acquisition[kind].items():
                assert f"endPeriod={bound}" in block["url"], (kind, currency)
                assert block["last"] < sources.PROTECTED_FROM[: len(block["last"])]


class TestEveryFrozenConditionIsLoadBearing:
    """Each of the twelve must be able to fail on its own, or it is decoration."""

    def _books(self, **over: Any):
        summary = {
            "gross_sharpe": over.get("net", 0.35),
            "net_sharpe": over.get("net", 0.35),
            "turnover_round_trips_per_year_per_unit_gross": over.get("turnover", 2.0),
        }
        return {
            "A_valuation": {"summary": {"gross_sharpe": over.get("a_gross", 1.0)}},
            "B_nominal_control": {"summary": {"net_sharpe": over.get("b_net", 0.0)}},
            "C_residualised": {
                "summary": summary,
                "blocks": [{"net_sharpe": v} for v in over.get("blocks", [1.0] * 6)],
                "per_currency_gross_pnl": over.get(
                    "per_currency", dict.fromkeys(prereg.UNIVERSE, 0.1)
                ),
                "terciles": {"monotone_cheap_to_dear": over.get("monotone", True)},
                "worst_year": {"sign_survives_removing_the_best_year": over.get("best_year", True)},
                "cost_stress": {"x2": over.get("stress", 0.2), "x3": over.get("stress3", 0.2)},
            },
        }

    def _screen(self, books, *, drops=None, reachable=True, vol=0.10, robust=1.0):
        from scripts.research.valuation import development

        return development._screen(
            books,
            {"C_residualised": {"net_sharpe": robust}},
            drops if drops is not None else dict.fromkeys(prereg.UNIVERSE, 1.0),
            {"0.05": {"reachable": reachable, "target_vol": vol}},
        )

    def test_all_twelve_hold_on_a_clean_book(self) -> None:
        screen = self._screen(self._books())
        assert screen["all_shared_conditions_hold"] is True
        assert len(screen["shared_conditions"]) == 12
        assert screen["decision"] == "candidate"

    @pytest.mark.parametrize(
        ("clause", "over", "kwargs"),
        [
            ("book A gross Sharpe > 0", {"a_gross": -0.1}, {}),
            ("C has positive gross and net", {"net": -0.1}, {}),
            #: the condition that encodes the whole hypothesis: C beyond B, not C alone
            ("C carries a positive net increment over B", {"b_net": 0.9}, {}),
            (
                "forward return falls monotonically from the cheap tercile to the dear one",
                {"monotone": False},
                {},
            ),
            (
                "a majority of the temporal blocks are positive",
                {"blocks": [1.0, 1.0, 1.0, -1.0, -1.0, -1.0]},
                {},
            ),
            (
                "no single currency carries more than half of the gross",
                {"per_currency": {**dict.fromkeys(prereg.UNIVERSE, 0.01), "CHF": 0.9}},
                {},
            ),
            (
                "the sign survives dropping any one of the eight",
                {},
                {"drops": {**dict.fromkeys(prereg.UNIVERSE, 1.0), "without_JPY": -0.1}},
            ),
            ("removing the best twelve-month window leaves the sign", {"best_year": False}, {}),
            ("turnover at or below 12", {"turnover": 12.1}, {}),
            ("net Sharpe stays positive at 2x and 3x cost", {"stress3": -0.01}, {}),
            (
                "the sign is unchanged under the declared robustness anchor",
                {},
                {"robust": -1.0},
            ),
            (
                "5% annual net is reachable at a volatility at most 15% whose gap stress survives",
                {},
                {"reachable": False},
            ),
        ],
    )
    def test_each_condition_fails_on_its_own_and_forces_a_stop(
        self, clause: str, over: dict[str, Any], kwargs: dict[str, Any]
    ) -> None:
        screen = self._screen(self._books(**over), **kwargs)
        assert screen["shared_conditions"][clause] is False, clause
        assert clause in screen["failing_conditions"], clause
        assert screen["decision"] == "stop", clause

    def test_the_increment_condition_is_not_merely_c_being_positive(self) -> None:
        """`net > 0` would be a strictly weaker predicate and must not pass for it."""
        clause = "C carries a positive net increment over B"
        books = self._books(net=0.35, b_net=0.35)
        assert books["C_residualised"]["summary"]["net_sharpe"] > 0
        assert self._screen(books)["shared_conditions"][clause] is False

    def test_the_concentration_denominator_is_the_books_gross(self) -> None:
        """Not the sum of absolute contributions, which is easier and means nothing."""
        clause = "no single currency carries more than half of the gross"
        #: largest 0.4 of an absolute sum of 1.0 (40%, which that reading lets through)
        #: but 0.4 of a signed gross of 0.6, which is 67% and fails the frozen one
        offsetting = {
            **dict.fromkeys(prereg.UNIVERSE, 0.0),
            "CHF": 0.4,
            "JPY": -0.2,
            "AUD": 0.2,
            "CAD": 0.2,
        }
        assert sum(abs(v) for v in offsetting.values()) == pytest.approx(1.0)
        assert sum(offsetting.values()) == pytest.approx(0.6)
        assert (
            self._screen(self._books(per_currency=offsetting))["shared_conditions"][clause] is False
        )

    def test_the_concentration_threshold_is_a_half(self) -> None:
        clause = "no single currency carries more than half of the gross"
        #: exactly half the gross passes; a hair over fails, so a loosened bound shows
        half = {**dict.fromkeys(prereg.UNIVERSE, 0.0), "CHF": 0.5, "JPY": 0.5}
        assert self._screen(self._books(per_currency=half))["shared_conditions"][clause] is True
        over = {**dict.fromkeys(prereg.UNIVERSE, 0.0), "CHF": 0.7, "JPY": 0.3}
        assert self._screen(self._books(per_currency=over))["shared_conditions"][clause] is False

    def test_the_cost_stress_needs_every_multiple(self) -> None:
        clause = "net Sharpe stays positive at 2x and 3x cost"
        assert self._screen(self._books(stress=-0.01))["shared_conditions"][clause] is False
        assert self._screen(self._books(stress3=-0.01))["shared_conditions"][clause] is False

    def test_the_block_majority_is_a_majority(self) -> None:
        clause = "a majority of the temporal blocks are positive"
        half = {"blocks": [1.0, 1.0, 1.0, -1.0, -1.0, -1.0]}
        assert self._screen(self._books(**half))["shared_conditions"][clause] is False
        four = {"blocks": [1.0, 1.0, 1.0, 1.0, -1.0, -1.0]}
        assert self._screen(self._books(**four))["shared_conditions"][clause] is True


class TestTheQuarterlyPublishersDoNotLeak:
    def test_the_quarterly_publishers_are_detected_from_the_data(self) -> None:
        from scripts.research.valuation import development

        _, cpi = _synthetic()
        quarterly = cpi.copy()
        #: stamp one reading on all three months of each quarter, as the BIS does
        periods = pd.PeriodIndex(quarterly.index, freq="M")
        quarterly["AUD"] = quarterly.groupby(periods.asfreq("Q"))["AUD"].transform("first")
        assert development.quarterly_publishers(quarterly) == ("AUD",)
        assert development.quarterly_publishers(cpi) == ()

    def test_a_quarterly_reading_never_reaches_a_decision_before_its_quarter_ends(self) -> None:
        from scripts.research.valuation import development

        _, cpi = _synthetic()
        periods = pd.PeriodIndex(cpi.index, freq="M")
        cpi = cpi.copy()
        cpi["AUD"] = cpi.groupby(periods.asfreq("Q"))["AUD"].transform("first")
        days = pd.bdate_range("2005-01-31", periods=60, freq="BME")
        lagged = development._lagged_log_cpi(cpi, days)
        logged = np.log(cpi.astype(float))
        lag = prereg.CPI_PUBLICATION_LAG_MONTHS
        for day in days:
            value = lagged.loc[day, "AUD"]
            #: find which months carry this reading, and require the quarter to have
            #: ended at least `lag` months before the decision
            carriers = [m for m in cpi.index if np.isclose(logged.loc[m, "AUD"], value)]
            latest_quarter_end = max(pd.Period(m, freq="M").asfreq("Q") for m in carriers)
            end_month = latest_quarter_end.asfreq("M", how="end")
            assert end_month + lag <= pd.Period(day, freq="M"), (day, end_month)

    def test_the_as_frozen_variant_reproduces_the_look_ahead(self) -> None:
        from scripts.research.valuation import development

        _, cpi = _synthetic()
        periods = pd.PeriodIndex(cpi.index, freq="M")
        cpi = cpi.copy()
        cpi["AUD"] = cpi.groupby(periods.asfreq("Q"))["AUD"].transform("first")
        days = pd.bdate_range("2005-01-31", periods=60, freq="BME")
        frozen = development._lagged_log_cpi(cpi, days, as_frozen=True)
        fixed = development._lagged_log_cpi(cpi, days)
        assert not frozen["AUD"].equals(fixed["AUD"])
        #: the monthly publishers are untouched either way
        pd.testing.assert_series_equal(frozen["USD"], fixed["USD"])

    def test_the_record_reports_both_and_prefers_the_leak_free_one(
        self, v_record: dict[str, Any]
    ) -> None:
        assert v_record["quarterly_publishers"] == ["AUD", "NZD"]
        comparison = v_record["as_the_frozen_text_described_the_source"]
        frozen = comparison["summaries"]["C_residualised"]["net_sharpe"]
        reported = v_record["books"]["C_residualised"]["summary"]["net_sharpe"]
        #: the look-ahead flattered the book, so the reported figure is the lower one
        assert reported < frozen
        assert "cannot be a rescue" in comparison["why_it_is_not_the_result"]


class TestTheRunReportsWhatThePreregAsked:
    def test_the_incremental_ic_is_computed_and_negative(self, v_record: dict[str, Any]) -> None:
        power = v_record["forecasting_power"]
        incremental = power["incremental_ic_of_valuation_beyond_the_nominal_control"]
        assert incremental["mean"] < 0
        #: the strongest statistic in the exercise, and it is a negative one
        assert incremental["newey_west_t"] < -2.0
        assert power["decisions_scored"] > 100
        assert set(power["signal_persistence_month_to_month"]) == set(v_record["books"])

    def test_the_tercile_claim_carries_its_own_dispersion(self, v_record: dict[str, Any]) -> None:
        power = v_record["forecasting_power"]
        gap = power["control_minus_valuation_tercile_spread"]
        #: the comparison the first draft called "the only reading" is a coin flip
        assert abs(gap["newey_west_t"]) < 2.0
        for row in power["tercile_spread_cheap_minus_dear"].values():
            assert "newey_west_t" in row

    def test_the_carry_direction_is_measured_not_assumed(self, v_record: dict[str, Any]) -> None:
        exposure = v_record["carry_exposure"]["C_residualised"]
        #: the primary test is long the low-inflation currencies, so the omitted carry
        #: is negative and its absence overstates rather than understates the book
        assert exposure["mean_rank_correlation_with_relative_trailing_inflation"] < -0.3
        assert exposure["newey_west_t"] < -2.0
        shortfall = next(
            row for row in v_record["disclosed_shortfalls"] if "spot return" in row["what"]
        )
        assert "OVERSTATES" in shortfall["direction"]
        assert "measured, not assumed" in shortfall["direction"]

    def test_the_turnover_is_attributed_to_what_actually_trades(
        self, v_record: dict[str, Any]
    ) -> None:
        extra = v_record["books"]["C_residualised"]["extra"]
        #: most of the turnover is the vol targeter, not the monthly signal
        assert extra["share_of_turnover_from_the_signal"] < 0.5
        assert extra["turnover_from_the_volatility_targeter"] > extra["turnover_from_the_signal"]
        assert extra["decisions_that_did_not_trade"] > extra["decisions_in_the_book"] / 2
        total = extra["turnover_from_the_signal"] + extra["turnover_from_the_volatility_targeter"]
        assert total == pytest.approx(
            v_record["books"]["C_residualised"]["summary"][
                "turnover_round_trips_per_year_per_unit_gross"
            ],
            abs=0.01,
        )

    def test_the_time_concentration_is_reported(self, v_record: dict[str, Any]) -> None:
        concentration = v_record["books"]["C_residualised"]["concentration"]
        #: the top five days carry more than the whole result
        assert concentration["top_5_day_share_of_net"] > 1.0
        assert concentration["net_without_the_top_5_days"] < 0
        assert concentration["largest_day"] == "2015-01-15"
        assert concentration["positive_calendar_years"] < concentration["calendar_years"]

    def test_the_leave_one_out_count_matches_the_values(self, v_record: dict[str, Any]) -> None:
        drops = v_record["leave_one_currency_out_net_sharpe"]
        assert len(drops) == len(prereg.UNIVERSE)
        assert v_record["leave_one_out_negative_count"] == sum(1 for v in drops.values() if v <= 0)
        assert v_record["leave_one_out_negative_count"] == 4


class TestTheRunGuardsItself:
    def test_the_run_refuses_a_panel_reaching_the_protected_span(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic(months=80)
        fx.index = pd.bdate_range("2016-01-04", periods=len(fx))
        monkeypatch.setattr(development, "load_panels", lambda: (fx, cpi))
        with pytest.raises(RuntimeError, match="protected"):
            development.run()

    def test_the_decision_day_is_the_last_trading_day_of_the_month(self) -> None:
        from scripts.research.valuation import development

        calendar = pd.bdate_range("2004-01-01", "2004-06-30")
        days = development._decision_days(calendar)
        assert len(days) == 6
        for day in days:
            later = calendar[(calendar > day) & (calendar.month == day.month)]
            assert len(later) == 0, day
        assert str(days[0].date()) == "2004-01-30"

    def test_the_leave_one_out_book_is_built_on_the_kept_currencies_only(self) -> None:
        """Rebuilding from the full cross-section would let the dropped name back in."""
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        kept = tuple(c for c in prereg.UNIVERSE if c != "JPY")
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        subset = development.build_signals(fx[list(kept)], cpi[list(kept)], days)
        for name, frame in subset.items():
            assert tuple(frame.columns) == kept, name
        #: and the subset is genuinely a different book, not the full one restricted
        full = development.build_signals(fx, cpi, days)
        assert not np.allclose(
            subset["C_residualised"].dropna(how="any").to_numpy(),
            full["C_residualised"].dropna(how="any")[list(kept)].to_numpy(),
        )

    def test_the_book_that_ran_is_the_book_the_prereg_declared(self) -> None:
        from scripts.research.valuation import development

        declared = prereg.PREREG["book_configuration"]
        assert development.BOOK.vol_target == declared["vol_target"]
        assert development.BOOK.max_leverage == declared["max_leverage"]
        #: the layer settings the frozen prose names, pinned against the prose
        architecture = declared["architecture"]
        assert f"weights at {development.BOOK.weight_cap}" in architecture
        assert f"band {development.BOOK.band}" in architecture
        assert development.BOOK.neutralize_leading_factor is True
        assert "the layer's own single pass" in declared["factor_neutralisation"]

    def test_the_robustness_anchor_is_a_different_anchor(self) -> None:
        from scripts.research.valuation import development

        _, cpi = _synthetic()
        frame = pd.DataFrame(
            np.vstack([np.arange(80.0), np.arange(80.0) ** 2]).T,
            index=pd.bdate_range("2004-01-01", periods=80),
            columns=["a", "b"],
        )
        mean = development._expanding_anchor(frame).dropna()
        median = development._median_anchor(frame).dropna()
        assert not np.allclose(mean.to_numpy(), median.to_numpy())

    def test_the_price_level_enters_with_the_frozen_sign(self) -> None:
        """`q = n + pi`, not `n - pi`: a currency whose prices rose is dear, not cheap."""
        from scripts.research.valuation import development

        fx, cpi = _synthetic()
        days = development._decision_days(pd.DatetimeIndex(fx.index))
        nominal = development._demean(-np.log(fx.loc[days].astype(float)))
        prices = development._demean(development._lagged_log_cpi(cpi, days))
        plus = fast_z_deviation(nominal + prices)
        minus = fast_z_deviation(nominal - prices)
        built = development.build_signals(fx, cpi, days)["A_valuation"].dropna(how="any")
        pd.testing.assert_frame_equal(built, plus.loc[built.index], atol=1e-12)
        assert not np.allclose(built.to_numpy(), minus.loc[built.index].to_numpy())


def fast_z_deviation(real: pd.DataFrame) -> pd.DataFrame:
    from scripts.research.market_yields import development as fast
    from scripts.research.valuation import development

    return fast._z(-(real - development._expanding_anchor(real)))


class TestTheReportedStatisticsAreComputedNotTranscribed:
    """These call the functions on inputs whose answers are known in advance.

    The record-reading tests above cannot see a change to the code that produced the
    record; each test here corresponds to a mutation that survived without it.
    """

    def _panels(self, months: int = 40):
        index = pd.bdate_range("2004-01-30", periods=months, freq="BME")
        currencies = list(prereg.UNIVERSE)
        return index, currencies

    def test_the_incremental_ic_is_a_minus_b_in_that_order(self) -> None:
        from scripts.research.valuation import development

        index, currencies = self._panels()
        rng = np.random.default_rng(4)
        daily = pd.bdate_range("2004-01-01", periods=len(index) * 21 + 200)
        excess = pd.DataFrame(
            rng.standard_normal((len(daily), len(currencies))) / 100.0,
            index=daily,
            columns=currencies,
        )
        excess = excess.sub(excess.mean(axis=1), axis=0)
        horizon = int(round(prereg.PRIMARY_HORIZON_MONTHS * 21))
        forward = excess.rolling(horizon).sum().shift(-horizon)
        #: A is built to forecast the forward window, B to forecast its negation
        good = forward.reindex(index).dropna(how="any")
        signals = {
            "A_valuation": good,
            "B_nominal_control": -good,
            "C_residualised": good,
        }
        power = development.forecasting_power(signals, excess, prereg.PRIMARY_HORIZON_MONTHS)
        assert power["ic"]["A_valuation"]["mean"] > 0
        assert power["ic"]["B_nominal_control"]["mean"] < 0
        incremental = power["incremental_ic_of_valuation_beyond_the_nominal_control"]
        #: A - B, not B - A: a signal that forecasts better than its control scores positive
        assert incremental["mean"] > 0
        assert incremental["newey_west_t"] > 0
        assert incremental["mean"] == pytest.approx(
            power["ic"]["A_valuation"]["mean"] - power["ic"]["B_nominal_control"]["mean"], abs=1e-3
        )

    def test_the_tercile_spread_is_cheap_minus_dear(self) -> None:
        from scripts.research.valuation import development

        index, currencies = self._panels()
        daily = pd.bdate_range("2004-01-01", periods=len(index) * 21 + 200)
        rng = np.random.default_rng(9)
        excess = pd.DataFrame(
            rng.standard_normal((len(daily), len(currencies))) / 100.0,
            index=daily,
            columns=currencies,
        )
        horizon = int(round(prereg.PRIMARY_HORIZON_MONTHS * 21))
        forward = excess.rolling(horizon).sum().shift(-horizon)
        good = forward.reindex(index).dropna(how="any")
        power = development.forecasting_power(
            {"A_valuation": good, "B_nominal_control": -good, "C_residualised": good},
            excess,
            prereg.PRIMARY_HORIZON_MONTHS,
        )
        #: a signal that ranks the winners highest has a positive cheap-minus-dear spread
        assert power["tercile_spread_cheap_minus_dear"]["A_valuation"]["mean_pp"] > 0
        assert power["tercile_spread_cheap_minus_dear"]["B_nominal_control"]["mean_pp"] < 0

    def test_the_carry_exposure_is_positive_when_the_book_buys_inflation(self) -> None:
        from scripts.research.valuation import development

        months = pd.period_range("1994-01", periods=300, freq="M").astype(str)
        currencies = list(prereg.UNIVERSE)
        rates = np.linspace(0.001, 0.02, len(currencies))
        cpi = pd.DataFrame(
            np.exp(np.outer(np.arange(len(months)), rates)) * 100.0,
            index=months,
            columns=currencies,
        )
        days = pd.bdate_range("2005-01-31", periods=60, freq="BME")
        #: a book long exactly the fastest-inflating currencies
        rank = pd.Series(rates, index=currencies)
        long_inflation = pd.DataFrame(
            np.tile((rank - rank.mean()).to_numpy(), (len(days), 1)), index=days, columns=currencies
        )
        out = development.carry_exposure(
            {"A_valuation": long_inflation, "B_nominal_control": -long_inflation}, cpi
        )
        assert out["A_valuation"]["mean_rank_correlation_with_relative_trailing_inflation"] > 0.9
        assert out["B_nominal_control"][
            "mean_rank_correlation_with_relative_trailing_inflation"
        ] < (-0.9)

    def test_the_turnover_split_counts_the_decision_days_as_the_signal(self) -> None:
        from scripts.research.valuation import development

        days = pd.bdate_range("2004-01-05", periods=40)
        decisions = days[::10]
        frame = pd.DataFrame(
            {
                "decision_day": days,
                "net": 0.001,
                "gross": 0.002,
                "cost": 0.0001,
                "implementation_cost": 0.0001,
                "traded": [d in set(decisions) for d in days],
                "one_way_traded": [1.0 if d in set(decisions) else 0.0 for d in days],
                **{f"x_{c}": 0.1 for c in prereg.UNIVERSE},
            },
            index=days,
        )
        out = development._turnover_cost({"daily": frame}, decisions, 4.0)
        #: everything traded on a decision day, so none of it is the targeter
        assert out["share_of_turnover_from_the_signal"] == pytest.approx(1.0)
        assert out["turnover_from_the_signal"] == pytest.approx(4.0)
        assert out["turnover_from_the_volatility_targeter"] == pytest.approx(0.0)
        assert out["decisions_in_the_book"] == len(decisions)
        assert out["decisions_that_did_not_trade"] == 0
        #: and the mirror case: nothing traded on a decision day
        frame["one_way_traded"] = [0.0 if d in set(decisions) else 1.0 for d in days]
        frame["traded"] = [d not in set(decisions) for d in days]
        mirrored = development._turnover_cost({"daily": frame}, decisions, 4.0)
        assert mirrored["share_of_turnover_from_the_signal"] == pytest.approx(0.0)
        assert mirrored["decisions_that_did_not_trade"] == len(decisions)

    def test_the_negative_drop_count_is_counted(self) -> None:
        from scripts.research.valuation import development

        assert development.negative_drops({"a": 1.0, "b": -0.1, "c": 0.0, "d": 2.0}) == 2
        assert development.negative_drops(dict.fromkeys("abcd", 1.0)) == 0
        assert development.negative_drops(dict.fromkeys("abcd", -1.0)) == 4

    def test_a_broken_middle_tercile_is_not_monotone(self) -> None:
        """`cheap > mid > dear`, not merely `cheap > dear`."""
        from scripts.research.valuation import development

        index = pd.bdate_range("2004-01-30", periods=30, freq="BME")
        currencies = list(prereg.UNIVERSE)
        daily = pd.bdate_range("2004-01-01", periods=len(index) * 21 + 200)
        signal = pd.DataFrame(
            np.tile(np.linspace(-1.0, 1.0, len(currencies)), (len(index), 1)),
            index=index,
            columns=currencies,
        )
        horizon = int(round(prereg.PRIMARY_HORIZON_MONTHS * 21))
        ranked = signal.iloc[0].rank(pct=True)
        #: cheap beats dear, but the middle bucket beats them both
        step = {
            c: (0.002 if ranked[c] > 2 / 3 else (0.004 if ranked[c] > 1 / 3 else 0.001))
            for c in currencies
        }
        excess = pd.DataFrame(0.0, index=daily, columns=currencies)
        for day in index:
            after = daily[daily > day][:horizon]
            for c in currencies:
                excess.loc[after, c] = step[c] / horizon
        out = development._terciles(signal, excess, prereg.PRIMARY_HORIZON_MONTHS)
        cheap, mid, dear = out["mean_forward_excess_return_cheap_mid_dear"]
        assert cheap > dear
        assert mid > cheap
        assert out["monotone_cheap_to_dear"] is False

    def test_the_leave_one_out_books_never_see_the_dropped_currency(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scripts.research.valuation import development

        fx, cpi = _synthetic(months=90)
        panel = development.pair_return_panel(fx)
        seen: list[tuple[int, int]] = []
        real = development.build_signals

        def spy(fx_in, cpi_in, days_in, **kwargs):
            seen.append((len(fx_in.columns), len(cpi_in.columns)))
            return real(fx_in, cpi_in, days_in, **kwargs)

        monkeypatch.setattr(development, "build_signals", spy)
        development._drop_one(fx, cpi, panel)
        assert seen, "the leave-one-out path did not build any signal"
        #: every rebuild sees seven currencies, never the full eight
        assert set(seen) == {(len(prereg.UNIVERSE) - 1, len(prereg.UNIVERSE) - 1)}
