"""T-V: the freeze, the exclusion at the request, and the run that followed them.

The first block runs against the pre-registration alone and would have passed
before a single FX byte existed. The rest exercise `development` itself — the
construction, the causality and the screen — rather than reading back the record
it wrote, so a change to the design fails a test.
"""

from __future__ import annotations

import hashlib
import json
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
            "the sign survives dropping any one of the eight",
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
        assert "−9.12%" in v_document
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
        for value in ("12.9", "1.29", "0.789", "-9.12%"):
            assert value in entry["result"], value
