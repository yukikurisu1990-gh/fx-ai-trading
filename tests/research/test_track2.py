"""Tests for Track 2 — the Stage 0 audit and the Stage 1 measurement.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Two things carry this Track and both are pinned here.

**The audit has to be able to fail.** An acceptance rule that passes whatever it
is given is not an acceptance rule, so the verdict is exercised against records
that should fail it — a bad date rate, an unrecognised currency code, a forecast
that matches its actual too often.

**The signs and the selection are mechanical.** Families are chosen by pattern
over the archive's own vocabulary and its own impact label, and the direction
comes from the mechanism. Neither may depend on a return, and neither may be
edited after one is seen — so the rules are tested as rules, on names rather than
on data.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from scripts.research.clock_flow import CURRENCIES
from scripts.research.clock_flow.frontier import MIN_BARS_FOR_A_TRADING_DAY, SIGNAL_TO_PAIR
from scripts.research.exploratory_m15 import PAIRS
from scripts.research.fxunits import HALF_SPREAD_ADDITION_PIPS, pips_to_bp
from scripts.research.track2 import (
    G10,
    MAX_FORECAST_EXACT_MATCH_SHARE,
    MIN_DATE_AGREEMENT,
    NON_USD,
    STATUS_SKIP,
    stage0,
    stage1,
)


def archive_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["utc"] = pd.to_datetime(frame["utc"], utc=True)
    return frame


class TestTheAuditCanFail:
    @staticmethod
    def record(*, agreement: float, codes_ok: bool, exact: float, beats: bool) -> dict[str, object]:
        return {
            "date_fidelity": {"pooled_agreement": agreement},
            "currency_mapping": {"all_codes_recognised": codes_ok},
            "forecast_audit": {
                "exact_match_below_ceiling": exact < MAX_FORECAST_EXACT_MATCH_SHARE,
                "beats_the_naive_benchmark": beats,
            },
        }

    def test_a_clean_record_passes(self) -> None:
        verdict = stage0.verdict(self.record(agreement=1.0, codes_ok=True, exact=0.1, beats=True))
        assert verdict["pass"] is True
        assert verdict["status"] is None

    def test_a_date_rate_below_the_threshold_fails(self) -> None:
        verdict = stage0.verdict(
            self.record(agreement=MIN_DATE_AGREEMENT - 0.01, codes_ok=True, exact=0.1, beats=True)
        )
        assert verdict["checks"]["date_agreement_at_least_95_percent"] is False
        assert verdict["status"] == STATUS_SKIP

    def test_the_threshold_is_inclusive(self) -> None:
        verdict = stage0.verdict(
            self.record(agreement=MIN_DATE_AGREEMENT, codes_ok=True, exact=0.1, beats=True)
        )
        assert verdict["checks"]["date_agreement_at_least_95_percent"] is True

    def test_an_unrecognised_currency_fails(self) -> None:
        verdict = stage0.verdict(self.record(agreement=1.0, codes_ok=False, exact=0.1, beats=True))
        assert verdict["pass"] is False

    def test_a_forecast_that_matches_too_often_fails(self) -> None:
        verdict = stage0.verdict(self.record(agreement=1.0, codes_ok=True, exact=0.9, beats=True))
        assert verdict["pass"] is False

    def test_a_forecast_that_adds_nothing_fails(self) -> None:
        verdict = stage0.verdict(self.record(agreement=1.0, codes_ok=True, exact=0.1, beats=False))
        assert verdict["pass"] is False

    def test_a_missing_date_measurement_is_not_a_pass(self) -> None:
        verdict = stage0.verdict(self.record(agreement=None, codes_ok=True, exact=0.1, beats=True))
        assert verdict["pass"] is False


class TestAgreementIsBothDirections:
    def test_perfect_recall_with_spurious_dates_is_not_agreement(self) -> None:
        """The case a recall-only metric calls perfect and a study trades on."""
        official = ["2023-01-10", "2023-02-10"]
        archive = ["2023-01-10", "2023-02-10", "2023-01-20", "2023-02-20"]
        score = stage0._agreement(archive, official, archive)
        assert score["recall"] == 1.0
        assert score["precision"] == 0.5
        #: The lower governs, so this is not a 95% agreement.
        assert score["agreement"] == 0.5

    def test_perfect_precision_with_missing_dates_is_not_agreement(self) -> None:
        official = ["2023-01-10", "2023-02-10", "2023-03-10"]
        archive = ["2023-01-10", "2023-03-10"]
        score = stage0._agreement(archive, official, archive)
        assert score["precision"] == 1.0
        assert score["recall"] == pytest.approx(2 / 3, abs=1e-4)
        assert score["agreement"] == pytest.approx(0.6667, abs=1e-4)

    def test_official_dates_outside_the_archive_range_are_not_misses(self) -> None:
        official = ["2019-01-01", "2023-01-10", "2030-01-01"]
        archive = ["2023-01-10"]
        assert stage0._agreement(archive, official, archive)["recall"] == 1.0

    def test_a_duplicated_row_costs_precision(self) -> None:
        """Dates are deduplicated; rows are not, because a duplicate is a defect."""
        official = ["2023-01-10"]
        score = stage0._agreement(
            ["2023-01-10", "2023-01-11"], official, ["2023-01-10"] * 3 + ["2023-01-11"]
        )
        assert score["n_archive_rows"] == 4
        assert score["precision"] == 0.75


class TestTheSelectionRuleIsMechanical:
    def test_each_family_matches_its_own_vocabulary(self) -> None:
        assert stage1.family_of("CPI y/y") == "inflation"
        assert stage1.family_of("Employment Change") == "employment"
        assert stage1.family_of("Main Refinancing Rate") == "policy_rate"
        assert stage1.family_of("Retail Sales m/m") is None

    def test_an_expectation_is_not_a_realisation(self) -> None:
        """`CPI Expectations` matches the inflation pattern and is not a print."""
        assert stage1.family_of("CPI Expectations") is None
        assert stage1.family_of("Inflation Rate Forecast") is None

    def test_only_the_bad_news_series_carry_a_minus(self) -> None:
        assert stage1.sign_of("CPI y/y") == 1
        assert stage1.sign_of("Employment Change") == 1
        assert stage1.sign_of("Unemployment Rate") == -1
        assert stage1.sign_of("Claimant Count Change") == -1

    def test_a_zero_surprise_is_not_traded(self) -> None:
        rows = archive_rows(
            [
                {
                    "utc": "2023-05-10T12:00:00Z",
                    "Currency": "EUR",
                    "Impact": stage1.HIGH_IMPACT,
                    "Event": "CPI y/y",
                    "Actual": "2.0",
                    "Forecast": "2.0",
                    "Previous": "1.9",
                }
            ]
        )
        assert stage1.events(rows).empty

    def test_a_usd_row_is_not_this_track(self) -> None:
        rows = archive_rows(
            [
                {
                    "utc": "2023-05-10T12:00:00Z",
                    "Currency": "USD",
                    "Impact": stage1.HIGH_IMPACT,
                    "Event": "CPI y/y",
                    "Actual": "2.2",
                    "Forecast": "2.0",
                    "Previous": "1.9",
                }
            ]
        )
        assert stage1.events(rows).empty

    def test_the_date_is_shifted_by_the_correction_stage_0_identified(self) -> None:
        """A 19:30 row is the one hour where every candidate offset agrees, so
        `TestTheOffsetIsOneObject` carries the cases that can tell them apart."""
        rows = archive_rows(
            [
                {
                    "utc": "2023-05-10T19:30:00Z",
                    "Currency": "EUR",
                    "Impact": stage1.HIGH_IMPACT,
                    "Event": "CPI y/y",
                    "Actual": "2.2",
                    "Forecast": "2.0",
                    "Previous": "1.9",
                }
            ]
        )
        table = stage1.events(rows, 5)
        assert table.iloc[0]["release_date"] == dt.date(2023, 5, 11)
        assert table.iloc[0]["direction"] == 1

    def test_the_direction_follows_the_mechanism_and_not_the_number(self) -> None:
        rows = archive_rows(
            [
                {
                    "utc": "2023-05-10T12:00:00Z",
                    "Currency": "GBP",
                    "Impact": stage1.HIGH_IMPACT,
                    "Event": "Unemployment Rate",
                    "Actual": "4.5",
                    "Forecast": "4.0",
                    "Previous": "4.1",
                }
            ]
        )
        #: A *higher* unemployment rate is a weaker economy, so the currency is
        #: sold even though the surprise is positive.
        assert stage1.events(rows).iloc[0]["direction"] == -1


class TestTheCurrencyPosition:
    def test_it_is_one_currency_against_the_other_seven(self) -> None:
        weights = stage1.currency_weights("EUR")
        assert len(weights) == len(PAIRS)
        #: Every pair with a EUR leg carries weight; a pair with none does not.
        for index, pair in enumerate(PAIRS):
            if "EUR" not in pair.split("_"):
                continue
            assert weights[index] != 0.0

    def test_being_long_a_currency_is_long_its_base_pairs(self) -> None:
        weights = stage1.currency_weights("EUR")
        for index, pair in enumerate(PAIRS):
            base, quote = pair.split("_")
            if base == "EUR":
                assert weights[index] > 0, pair
            elif quote == "EUR":
                assert weights[index] < 0, pair

    def test_the_dollar_is_inside_the_basket(self) -> None:
        """So the dollar factor cannot be the effect, which cost `H-003` 96%."""
        assert "USD" in G10
        weights = stage1.currency_weights("EUR")
        usd_pairs = [i for i, p in enumerate(PAIRS) if "USD" in p.split("_")]
        assert any(weights[i] != 0.0 for i in usd_pairs)

    def test_every_currency_has_a_position_and_they_are_the_same_size(self) -> None:
        sizes = {c: float(np.abs(stage1.currency_weights(c)).sum()) for c in G10}
        assert min(sizes.values()) > 0
        assert max(sizes.values()) - min(sizes.values()) < 0.5

    def test_the_matrix_ordering_is_the_clock_families_ordering(self) -> None:
        """A silent re-ordering here would rotate every currency's position."""
        assert sorted(CURRENCIES) == list(CURRENCIES)
        assert set(CURRENCIES) == set(G10)


class TestPanelDays:
    @staticmethod
    def frames(days: list[str]) -> dict[str, pd.DataFrame]:
        out = {}
        for pair in PAIRS:
            stamps, mids = [], []
            for day in days:
                base = pd.Timestamp(day, tz="UTC")
                for step in range(96):
                    stamps.append(base + pd.Timedelta(minutes=15 * step))
                    mids.append(1.1 + 0.0001 * step)
            out[pair] = pd.DataFrame(
                {
                    "ts": pd.DatetimeIndex(stamps),
                    "mid_o": mids,
                    "mid_c": mids,
                    "spread_close_pips": np.full(len(mids), 1.2),
                    "pip_size": np.full(len(mids), 0.0001),
                }
            )
        return out

    def test_the_next_trading_day_skips_a_weekend(self) -> None:
        days = self.frames(["2023-05-04", "2023-05-05", "2023-05-08"])
        panel = stage1.PanelDays(days)
        #: Friday's release trades on Monday, because Saturday has no bars.
        assert panel.first_day_after(dt.date(2023, 5, 5)) == dt.date(2023, 5, 8)
        assert panel.first_day_after(dt.date(2023, 5, 4)) == dt.date(2023, 5, 5)

    def test_a_release_after_the_last_bar_has_no_trading_day(self) -> None:
        panel = stage1.PanelDays(self.frames(["2023-05-04"]))
        assert panel.first_day_after(dt.date(2023, 5, 4)) is None

    def test_the_entry_is_strictly_after_the_release_date(self) -> None:
        """The announcement day itself is never traded — the whole point of
        entering forward when the source's time of day is unusable."""
        panel = stage1.PanelDays(self.frames(["2023-05-04", "2023-05-05"]))
        assert panel.first_day_after(dt.date(2023, 5, 4)) != dt.date(2023, 5, 4)


class TestTheVerdictMapping:
    @staticmethod
    def panels(**cells: dict[str, object]) -> dict[str, object]:
        return {name: {"families": cells} for name in ("a", "b")}

    def test_an_undecidable_family_gives_skip_not_closed(self) -> None:
        gate = {
            family: {"gates_passed": {"statistical": False, "economic": False, "robustness": True}}
            for family in stage1.FAMILY_PATTERNS
        }
        cells = {family: {"n_events": 10, "sign": -1, "p_value_on_gross": 0.9} for family in gate}
        verdict = stage1._verdict(self.panels(**cells), gate)
        assert verdict["every_family_is_decidable"] is False
        assert verdict["status"] == STATUS_SKIP

    def test_a_decidable_null_closes_the_family(self) -> None:
        gate = {
            family: {"gates_passed": {"statistical": True, "economic": True, "robustness": True}}
            for family in stage1.FAMILY_PATTERNS
        }
        cells = {
            family: {
                "n_events": 200,
                "sign": -1,
                "p_value_on_gross": 0.9,
                "tail_share": 0.2,
                "currency_breadth": 5,
            }
            for family in gate
        }
        verdict = stage1._verdict(self.panels(**cells), gate)
        assert verdict["status"] == "NON_USD_SURPRISE_RELATIVE_CLOSED"

    def test_support_needs_every_check(self) -> None:
        gate = {
            family: {"gates_passed": {"statistical": True, "economic": True, "robustness": True}}
            for family in stage1.FAMILY_PATTERNS
        }
        cells = {
            family: {
                "n_events": 200,
                "sign": 1,
                "p_value_on_gross": 0.01,
                "tail_share": 0.2,
                "currency_breadth": 5,
            }
            for family in gate
        }
        verdict = stage1._verdict(self.panels(**cells), gate)
        assert verdict["status"] == "NON_USD_SURPRISE_RELATIVE_EDGE_SUPPORTED_EXPLORATORY"
        #: ...and one failing check is enough to remove it.
        cells["inflation"] = {**cells["inflation"], "currency_breadth": 1}
        assert (
            stage1._verdict(self.panels(**cells), gate)["families"]["inflation"]["supported"]
            is False
        )

    def test_a_family_negative_on_both_panels_is_not_support(self) -> None:
        """The inversion the pre-registration forbids, arriving through the rule.

        Agreement alone is not enough: the sign the panels agree on has to be the
        one the mechanism predicted, or a family that moved the wrong way would be
        recorded as supported.
        """
        gate = {
            family: {"gates_passed": {"statistical": True, "economic": True, "robustness": True}}
            for family in stage1.FAMILY_PATTERNS
        }
        wrong = {
            "n_events": 200,
            "sign": -1,
            "p_value_on_gross": 0.01,
            "tail_share": 0.2,
            "currency_breadth": 5,
        }
        verdict = stage1._verdict(self.panels(**{f: wrong for f in gate}), gate)
        for block in verdict["families"].values():
            assert block["checks"]["panels_agree_on_sign"] is True
            assert block["checks"]["sign_is_the_hypothesised_one"] is False
            assert block["supported"] is False

    def test_panels_disagreeing_on_sign_is_not_support(self) -> None:
        gate = {
            family: {"gates_passed": {"statistical": True, "economic": True, "robustness": True}}
            for family in stage1.FAMILY_PATTERNS
        }
        good = {
            "n_events": 200,
            "sign": 1,
            "p_value": 0.01,
            "tail_share": 0.2,
            "currency_breadth": 5,
        }
        panels = {
            "a": {"families": {f: good for f in gate}},
            "b": {"families": {f: {**good, "sign": -1} for f in gate}},
        }
        verdict = stage1._verdict(panels, gate)
        assert all(not block["supported"] for block in verdict["families"].values())


class TestConstants:
    def test_the_non_usd_universe_excludes_the_dollar(self) -> None:
        assert "USD" not in NON_USD
        assert set(NON_USD) | {"USD"} == set(G10)

    def test_the_default_offset_is_no_correction_at_all(self) -> None:
        """The real one comes from Stage 0's artifact; a default that silently
        corrected would be a second constant able to drift from the first."""
        assert stage1.DEFAULT_OFFSET_HOURS == 0


# ---------------------------------------------------------------------------
# The quantitative core. A review found that `measure`, `statistics`,
# `_effective_n`, `_permutation_p` and `PanelDays`'s returns and costs had no
# test at all: ten mutations survived, including a **zero** round-trip cost, a
# return computed in pips, and trading the release day itself. Every number in
# `stage1.json` came out of code nothing exercised.
# ---------------------------------------------------------------------------


def panel_frames(
    days: list[str],
    *,
    bars_per_day: dict[str, int] | None = None,
    open_price: float = 1.1,
    close_price: float = 1.1,
    spread_pips: float = 1.2,
) -> dict[str, pd.DataFrame]:
    """Bars whose open and close are pinned, so a return can be predicted exactly."""
    out = {}
    for pair in PAIRS:
        stamps, opens, closes = [], [], []
        for day in days:
            base = pd.Timestamp(day, tz="UTC")
            count = (bars_per_day or {}).get(day, 96)
            for step in range(count):
                stamps.append(base + pd.Timedelta(minutes=15 * step))
                opens.append(open_price)
                closes.append(close_price if step == count - 1 else open_price)
        pip = 0.01 if "JPY" in pair else 0.0001
        scale = 100.0 if "JPY" in pair else 1.0
        out[pair] = pd.DataFrame(
            {
                "ts": pd.DatetimeIndex(stamps),
                "mid_o": np.array(opens) * scale,
                "mid_c": np.array(closes) * scale,
                "spread_close_pips": np.full(len(stamps), spread_pips),
                "pip_size": np.full(len(stamps), pip),
            }
        )
    return out


class TestPanelDayArithmetic:
    def test_the_daily_return_is_open_to_close_in_basis_points(self) -> None:
        """A return computed in pips would be a hundred times this on JPY."""
        frames = panel_frames(["2023-05-08"], open_price=1.1, close_price=1.1011)
        panel = stage1.PanelDays(frames)
        day = dt.date(2023, 5, 8)
        expected = (1.1011 - 1.1) / 1.1 * 1e4
        for pair in PAIRS:
            assert panel.returns[pair][day] == pytest.approx(expected, rel=1e-9), pair

    def test_the_round_trip_is_the_programmes_spread_plus_half_a_pip(self) -> None:
        """Zero cost, or a quarter of it, would pass without this."""
        frames = panel_frames(["2023-05-08"], spread_pips=1.4)
        panel = stage1.PanelDays(frames)
        day = dt.date(2023, 5, 8)
        for pair in PAIRS:
            pip = 0.01 if "JPY" in pair else 0.0001
            mid = 110.0 if "JPY" in pair else 1.1
            expected = float(pips_to_bp(1.4 + HALF_SPREAD_ADDITION_PIPS, pip, mid))
            assert panel.costs[pair][day] == pytest.approx(expected, rel=1e-9), pair
            assert panel.costs[pair][day] > 0

    def test_a_partial_session_is_not_a_trading_day(self) -> None:
        """The Sunday reopen carries about twelve bars and used to be a day.

        Two thirds of the best-populated family entered into it, while the
        docstring claimed the following Monday.
        """
        frames = panel_frames(
            ["2023-05-05", "2023-05-07", "2023-05-08"],
            bars_per_day={"2023-05-07": 12},
        )
        panel = stage1.PanelDays(frames)
        assert dt.date(2023, 5, 7) not in panel.days
        assert panel.partial_days >= 1
        #: A Friday release therefore trades on Monday, as claimed.
        assert panel.first_day_after(dt.date(2023, 5, 5)) == dt.date(2023, 5, 8)

    def test_the_threshold_is_the_clock_families_constant(self) -> None:
        frames = panel_frames(
            ["2023-05-08", "2023-05-09"],
            bars_per_day={"2023-05-09": MIN_BARS_FOR_A_TRADING_DAY},
        )
        assert dt.date(2023, 5, 9) in stage1.PanelDays(frames).days
        frames = panel_frames(
            ["2023-05-08", "2023-05-09"],
            bars_per_day={"2023-05-09": MIN_BARS_FOR_A_TRADING_DAY - 1},
        )
        assert dt.date(2023, 5, 9) not in stage1.PanelDays(frames).days


class TestTheBasketIdentity:
    def test_the_position_pays_exactly_the_pre_registered_target(self) -> None:
        """`w · r` is `r_c - mean(r_k for k != c)`, to the last bit.

        This is the whole of pre-registration §5, and mutation testing showed an
        outright long with no basket at all passing every other test. The
        currency index is built here from the pair returns directly, so the
        assertion does not go through the matrix it is checking.
        """
        rng = np.random.default_rng(11)
        returns = rng.normal(0.0, 20.0, len(PAIRS))
        for currency in G10:
            index = {}
            for other in G10:
                legs = [
                    returns[i] if p.split("_")[0] == other else -returns[i]
                    for i, p in enumerate(PAIRS)
                    if other in p.split("_")
                ]
                index[other] = float(np.mean(legs))
            target = index[currency] - float(np.mean([index[k] for k in G10 if k != currency]))
            realised = float(stage1.currency_weights(currency) @ returns)
            assert realised == pytest.approx(target, rel=1e-9), currency

    def test_the_basket_leg_is_actually_there(self) -> None:
        """An outright currency long would pay the index; this pays the spread.

        Mutation testing removed the neutralisation and left every other test
        green. The difference it makes is exactly the basket, so that is what is
        measured here.
        """
        rng = np.random.default_rng(23)
        returns = rng.normal(0.0, 20.0, len(PAIRS))
        legs = [
            returns[i] if p.split("_")[0] == "EUR" else -returns[i]
            for i, p in enumerate(PAIRS)
            if "EUR" in p.split("_")
        ]
        index = float(np.mean(legs))
        realised = float(stage1.currency_weights("EUR") @ returns)
        assert realised != pytest.approx(index, abs=1e-6)
        #: ...and the gap is the basket's own return, not noise.
        assert abs(realised - index) > 0.5


class TestMeasure:
    @staticmethod
    def table(rows: list[tuple[str, str, int]]) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Currency": currency,
                    "Event": "CPI y/y",
                    "family": "inflation",
                    "surprise": 1.0,
                    "mechanism_sign": 1,
                    "direction": direction,
                    "release_date": dt.date.fromisoformat(date),
                    "high_impact": True,
                }
                for currency, date, direction in rows
            ]
        )

    def test_the_release_day_itself_is_never_traded(self) -> None:
        """Even when it is a full trading day with bars available."""
        frames = panel_frames(["2023-05-08", "2023-05-09"], close_price=1.2)
        panel = stage1.PanelDays(frames)
        cell = stage1.measure(panel, self.table([("EUR", "2023-05-08", 1)]), "inflation")
        assert list(cell["dates"]) == [dt.date(2023, 5, 9)]

    def test_a_thin_cross_section_is_dropped_and_counted(self) -> None:
        frames = panel_frames(["2023-05-08", "2023-05-09"])
        for pair in PAIRS[1:]:
            frames.pop(pair)
        panel = stage1.PanelDays(frames)
        cell = stage1.measure(panel, self.table([("EUR", "2023-05-08", 1)]), "inflation")
        assert cell["gross"].size == 0
        assert cell["dropped"]["thin_cross_section"] == 1

    def test_a_net_zero_direction_is_dropped_and_counted(self) -> None:
        frames = panel_frames(["2023-05-08", "2023-05-09"])
        panel = stage1.PanelDays(frames)
        table = self.table([("EUR", "2023-05-08", 1), ("EUR", "2023-05-08", -1)])
        cell = stage1.measure(panel, table, "inflation")
        assert cell["gross"].size == 0
        assert cell["dropped"]["zero_net_direction"] == 1

    def test_the_cost_is_the_exposure_times_the_per_pair_round_trip(self) -> None:
        """A cost scaled by any constant passes every other test in this file."""
        frames = panel_frames(["2023-05-08", "2023-05-09"], spread_pips=1.4)
        panel = stage1.PanelDays(frames)
        cell = stage1.measure(panel, self.table([("EUR", "2023-05-08", 1)]), "inflation")
        weights = stage1.currency_weights("EUR")
        day = dt.date(2023, 5, 9)
        expected = float(
            sum(abs(weights[i]) * panel.costs[pair][day] for i, pair in enumerate(PAIRS))
        )
        assert float(cell["cost"][0]) == pytest.approx(expected, rel=1e-9)
        assert float(cell["exposure"][0]) == pytest.approx(float(np.abs(weights).sum()), rel=1e-9)

    def test_the_construction_is_invariant_to_two_equivalent_rewritings(self) -> None:
        """Recorded because mutation testing produced both and neither is a defect.

        Centring makes an outright `e_c` the same vector as the basket, and the
        basket already has a gross exposure of two, so the normalisation is a
        no-op on it. A reader chasing either mutation should know it is
        equivalent rather than untested.
        """
        weights = stage1.currency_weights("EUR")
        raw = np.zeros(len(G10))
        raw[G10.index("EUR")] = 1.0
        raw = raw - raw.mean()
        raw = 2.0 * raw / np.abs(raw).sum()
        ordered = np.array([raw[G10.index(c)] for c in CURRENCIES])
        assert np.allclose(weights, SIGNAL_TO_PAIR @ ordered)

    def test_the_direction_flips_the_sign_of_the_gross(self) -> None:
        frames = panel_frames(["2023-05-08", "2023-05-09"], close_price=1.2)
        panel = stage1.PanelDays(frames)
        long = stage1.measure(panel, self.table([("EUR", "2023-05-08", 1)]), "inflation")
        short = stage1.measure(panel, self.table([("EUR", "2023-05-08", -1)]), "inflation")
        assert float(long["gross"][0]) == pytest.approx(-float(short["gross"][0]), rel=1e-9)
        #: ...and the cost does not, because a cost is paid either way.
        assert float(long["cost"][0]) == pytest.approx(float(short["cost"][0]), rel=1e-9)
        assert float(long["cost"][0]) > 0


class TestStatistics:
    @staticmethod
    def cell(gross: np.ndarray, *, cost: float = 2.0) -> dict[str, object]:
        n = len(gross)
        return {
            "gross": gross,
            "cost": np.full(n, cost),
            "exposure": np.full(n, 1.3),
            "high_impact": np.ones(n, dtype=bool),
            "currencies": np.array(["EUR", "JPY"] * (n // 2) + ["EUR"] * (n % 2)),
            "dates": np.array(
                [dt.date(2023, 1, 1) + dt.timedelta(days=i) for i in range(n)], dtype=object
            ),
            "dropped": {},
        }

    def test_a_null_series_is_not_significant(self) -> None:
        """A hard-coded p-value passes every other test in this file."""
        rng = np.random.default_rng(5)
        record = stage1.statistics(
            self.cell(rng.normal(0.0, 30.0, 200)), 2.0, np.random.default_rng(7)
        )
        assert record["p_value_on_gross"] > 0.2

    def test_a_large_effect_is_significant(self) -> None:
        rng = np.random.default_rng(5)
        gross = rng.normal(0.0, 5.0, 200) + 40.0
        record = stage1.statistics(self.cell(gross), 2.0, np.random.default_rng(7))
        assert record["p_value_on_gross"] < 0.01

    def test_the_sign_is_taken_on_gross_and_not_on_net(self) -> None:
        """Net is negative in every real cell, so a sign on net says nothing."""
        gross = np.full(50, 1.0)
        record = stage1.statistics(self.cell(gross, cost=5.0), 2.0, np.random.default_rng(7))
        assert record["net_bp"] < 0
        assert record["sign"] == 1

    def test_the_breadth_counts_currencies_agreeing_with_the_family(self) -> None:
        #: Deliberately not symmetric: a family whose mean gross is exactly zero
        #: has no sign for a currency to agree with.
        #: A cost large enough that **every** currency's net is negative, so a
        #: breadth counted on positive net would be zero while the answer is one.
        gross = np.array([12.0, -10.0] * 25)
        record = stage1.statistics(self.cell(gross, cost=20.0), 2.0, np.random.default_rng(7))
        assert record["n_currencies"] == 2
        assert record["sign"] == 1
        assert all(block["net_bp"] < 0 for block in record["by_currency"].values())
        assert record["currency_breadth"] == 1

    def test_dependence_cannot_raise_the_effective_sample(self) -> None:
        rng = np.random.default_rng(3)
        record = stage1.statistics(
            self.cell(rng.normal(0.0, 20.0, 120)), 2.0, np.random.default_rng(7)
        )
        assert record["effective_n"] <= record["n_events"]
        assert record["mde_bp"] > 0


class TestTheOffsetIsOneObject:
    def test_a_different_offset_moves_the_dates(self) -> None:
        """So the correction is a real parameter and not decoration."""
        rows = archive_rows(
            [
                {
                    "utc": "2023-05-10T19:30:00Z",
                    "Currency": "EUR",
                    "Impact": stage1.HIGH_IMPACT,
                    "Event": "CPI y/y",
                    "Actual": "2.2",
                    "Forecast": "2.0",
                    "Previous": "1.9",
                }
            ]
        )
        assert stage1.events(rows, 0).iloc[0]["release_date"] == dt.date(2023, 5, 10)
        assert stage1.events(rows, 5).iloc[0]["release_date"] == dt.date(2023, 5, 11)

    def test_a_midday_row_is_not_moved_by_the_validated_offset(self) -> None:
        """The defect is a time-of-day defect, not a uniform day shift.

        A one-day constant moves this row and scores 0.369 through Stage 0's own
        scorer; the validated five-hour offset leaves it where it is.
        """
        rows = archive_rows(
            [
                {
                    "utc": "2023-05-10T12:15:00Z",
                    "Currency": "EUR",
                    "Impact": stage1.HIGH_IMPACT,
                    "Event": "CPI y/y",
                    "Actual": "2.2",
                    "Forecast": "2.0",
                    "Previous": "1.9",
                }
            ]
        )
        assert stage1.events(rows, 5).iloc[0]["release_date"] == dt.date(2023, 5, 10)

    def test_the_impact_label_does_not_admit_or_exclude(self) -> None:
        """It is a diagnostic in the pre-registration, not the admission rule."""
        rows = archive_rows(
            [
                {
                    "utc": "2023-05-10T12:15:00Z",
                    "Currency": "EUR",
                    "Impact": "Low Impact Expected",
                    "Event": "CPI y/y",
                    "Actual": "2.2",
                    "Forecast": "2.0",
                    "Previous": "1.9",
                }
            ]
        )
        table = stage1.events(rows, 5)
        assert len(table) == 1
        assert bool(table.iloc[0]["high_impact"]) is False
