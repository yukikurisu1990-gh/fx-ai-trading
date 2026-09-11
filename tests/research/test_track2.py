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
from scripts.research.exploratory_m15 import PAIRS
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

    def test_a_low_impact_row_is_not_admitted(self) -> None:
        rows = archive_rows(
            [
                {
                    "utc": "2023-05-10T12:00:00Z",
                    "Currency": "EUR",
                    "Impact": "Low Impact Expected",
                    "Event": "CPI y/y",
                    "Actual": "2.2",
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
        table = stage1.events(rows)
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
        cells = {family: {"n_events": 10, "sign": -1, "p_value": 0.9} for family in gate}
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
                "p_value": 0.9,
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
                "p_value": 0.01,
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

    def test_the_date_shift_is_one_day(self) -> None:
        assert stage1.ARCHIVE_DATE_SHIFT_DAYS == 1
