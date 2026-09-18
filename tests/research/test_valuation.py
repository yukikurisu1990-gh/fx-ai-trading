"""The T-V freeze: the pre-registration's content, and the exclusion at the request.

These tests run before any FX byte exists, and they are what makes "frozen" a
measurable claim rather than a sentence in a docstring.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

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
