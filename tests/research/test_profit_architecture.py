"""The redesign's arithmetic, its signal-freeness, and its declared structure.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The package's whole claim is that it computes economics without touching a
market: the tests pin the arithmetic identities, the turnover scaling law, the
distinctions the instruction demands (prediction != turnover, leverage != edge),
and the fact that no module can open a data file at all.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from scripts.research.profit_architecture import (
    BASKET_ROUNDTRIP_BP,
    MEASURED_ANNUAL_VOL_PER_GROSS_BP,
    MEASURED_TURNOVER_RANKING_MODEL,
    candidates,
    cost_audit,
    mechanics,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scripts/research/profit_architecture"
ARTIFACT = ROOT / "artifacts/research/profit_architecture/redesign.json"


@pytest.fixture(scope="module")
def artifact() -> dict[str, Any]:
    if not ARTIFACT.exists():
        pytest.skip("run `python -m scripts.research.profit_architecture.driver redesign`")
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


class TestTheCostAudit:
    def test_the_decomposition_multiplies_back(self) -> None:
        block = cost_audit.decomposition()
        product = (
            block["factors"]["pair_roundtrip_bp"]["value"]
            * block["factors"]["basket_exposure"]["value"]
        )
        assert product == pytest.approx(BASKET_ROUNDTRIP_BP, abs=2e-3)

    def test_one_way_is_half_a_round_trip(self) -> None:
        assert pytest.approx(BASKET_ROUNDTRIP_BP / 2) == cost_audit.ONE_WAY_BASKET_BP

    def test_the_measured_turnovers_match_the_development_artifact(self) -> None:
        """The constants that refute the old convention must trace to the record."""
        path = ROOT / "artifacts/research/model_learning/development.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        tracks = record["tracks"]
        ranking = tracks["M01_currency_cross_sectional_ranking"]
        assert ranking["model"]["annualised_turnover"] == pytest.approx(
            MEASURED_TURNOVER_RANKING_MODEL, abs=0.05
        )
        assert ranking["baseline_metrics"]["annualised_turnover"] == pytest.approx(
            cost_audit.MEASURED_TURNOVER_TOP2_BOTTOM2, abs=0.05
        )

    def test_the_overstatement_factor_is_what_it_claims(self) -> None:
        assert (
            pytest.approx(252.0 / MEASURED_TURNOVER_RANKING_MODEL, abs=0.01)
            == cost_audit.OVERSTATEMENT_FACTOR_SMOOTH_BOOK
        )

    def test_the_gate_audit_reopens_no_verdict(self) -> None:
        """The instruction's constraint, pinned: audit the instrument, not the ruling."""
        assert cost_audit.gate_audit()["verdicts_reopened_by_this_audit"] == []


class TestTurnoverMechanics:
    def test_turnover_scales_with_the_square_root_of_one_minus_rho(self) -> None:
        """⭐ The central law: persistence, not update frequency, sets the cost."""
        fresh = mechanics.simulate_book_turnover(0.0)["annual_turnover"]
        for rho in (0.5, 0.9, 0.966):
            measured = mechanics.simulate_book_turnover(rho)["annual_turnover"]
            predicted = fresh * math.sqrt(1.0 - rho)
            assert measured == pytest.approx(predicted, rel=0.12), rho

    def test_daily_updates_do_not_mean_252_round_trips(self) -> None:
        """⭐ prediction frequency != turnover, measured on the synthetic book."""
        law = mechanics.turnover_law_table()
        assert law["close_reopen_convention_would_charge"] == 252.0
        for row in law["rows"].values():
            assert row["annual_turnover"] < 252.0
        assert law["rows"]["half_life_20d"]["annual_turnover"] == pytest.approx(
            MEASURED_TURNOVER_RANKING_MODEL, rel=0.10
        ), "the synthetic law should land near the measured book, and it does"

    def test_a_band_cuts_turnover_monotonically(self) -> None:
        table = mechanics.no_trade_band_table()["rows"]
        turnovers = [row["annual_turnover"] for row in table.values()]
        gaps = [row["mean_tracking_gap_gross"] for row in table.values()]
        assert turnovers == sorted(turnovers, reverse=True)
        assert gaps == sorted(gaps)

    def test_the_band_is_not_free_and_the_capture_is_computed(self) -> None:
        """⭐ A review found 'the gap costs nothing' asserted as measured.

        Nothing had computed it. The alpha capture is now part of the simulation:
        it is 1.0 with no band, ~0.958 at the recommended 0.10 band — about 4.2%
        of gross IR forfeited, not nothing — and it falls monotonically as the
        band widens. The required-IC figures must charge it.
        """
        table = mechanics.no_trade_band_table()["rows"]
        captures = [row["alpha_capture"] for row in table.values()]
        assert captures[0] == 1.0
        assert captures == sorted(captures, reverse=True)
        assert table["band_0.1"]["alpha_capture"] == pytest.approx(0.958, abs=0.003)
        charged = table["band_0.1"]["required_target_gross_ir_for_net_0_5"]
        uncharged = (0.5 + mechanics.ir_drag(table["band_0.1"]["annual_turnover"])) / 1.0
        assert charged > uncharged
        assert table["band_0.1"]["required_daily_ic_for_net_0_5"] == pytest.approx(0.0207, abs=3e-4)

    def test_wider_bands_hit_diminishing_returns(self) -> None:
        """Past 0.10 the capture loss eats what the turnover saving buys."""
        table = mechanics.no_trade_band_table()["rows"]
        at_010 = table["band_0.1"]["required_daily_ic_for_net_0_5"]
        at_015 = table["band_0.15"]["required_daily_ic_for_net_0_5"]
        assert abs(at_015 - at_010) < 0.0005

    def test_a_fast_overlay_adds_less_than_a_fast_book(self) -> None:
        """⭐ The §14 point: modulating a core is cheaper than running fast alone.

        And the bound is claimed only for modulating shares up to ~0.3: a review
        measured share 0.5, where the added turnover (41.8) already exceeds
        `share x fast-alone` (40.6). Both sides are pinned.
        """
        slow_only = mechanics.multi_horizon_turnover(fast_share=0.0)["annual_turnover"]
        blended = mechanics.multi_horizon_turnover(fast_share=0.3)["annual_turnover"]
        fast_only = mechanics.multi_horizon_turnover(fast_share=1.0)["annual_turnover"]
        assert slow_only < blended < fast_only
        assert blended - slow_only < 0.3 * fast_only
        half = mechanics.multi_horizon_turnover(fast_share=0.5)["annual_turnover"]
        assert half - slow_only > 0.5 * fast_only, (
            "the sub-additivity bound holds at 0.5 after all; narrow the docstring"
        )

    def test_the_simulation_is_deterministic(self) -> None:
        first = mechanics.simulate_book_turnover(0.9)
        second = mechanics.simulate_book_turnover(0.9)
        assert first == second

    def test_a_rho_outside_the_unit_interval_is_refused(self) -> None:
        for bad in (-0.1, 1.0, 1.5):
            with pytest.raises(ValueError):
                mechanics.simulate_book_turnover(bad)


class TestLeverageTranslation:
    def test_the_drag_is_leverage_invariant(self) -> None:
        """⭐ leverage != edge: the drag is a ratio of per-gross quantities."""
        assert mechanics.ir_drag(36.7) == pytest.approx(
            36.7 * BASKET_ROUNDTRIP_BP / MEASURED_ANNUAL_VOL_PER_GROSS_BP
        )
        assert mechanics.ir_drag(36.7) == pytest.approx(0.331, abs=1e-3)

    def test_leverage_for_the_vol_targets(self) -> None:
        assert mechanics.leverage_for_vol_target(0.10) == pytest.approx(2.65, abs=0.01)
        assert mechanics.leverage_for_vol_target(0.08) == pytest.approx(2.12, abs=0.01)

    def test_required_gross_ir_is_net_plus_drag(self) -> None:
        assert mechanics.required_gross_ir(0.5, 36.7) == pytest.approx(0.831, abs=1e-3)
        assert mechanics.required_gross_ir(0.5, 12.0) == pytest.approx(0.608, abs=1e-3)

    def test_the_capacity_table_carries_the_required_ic(self) -> None:
        table = mechanics.capacity_table()
        row = table["by_turnover"]["turnover_36.7"]
        assert row["required_daily_ic_for_net_sharpe"]["0.5"] == pytest.approx(0.0262, abs=5e-4)

    def test_drawdown_deepens_as_sharpe_falls(self) -> None:
        low = mechanics.expected_max_drawdown(0.3, 0.10)
        high = mechanics.expected_max_drawdown(1.0, 0.10)
        assert low > high > 0


class TestPairRouting:
    def test_the_three_ratios_are_ordered_and_the_charged_one_reproduces(self) -> None:
        """⭐ One formula, three ratios: charged 1.32 / implementation 0.77 / floor 0.55.

        The implementation row reproduces an independent review's measurement
        (0.77, conservatism ~1.7x) of the corpus's own equal-split netting; the
        floor is the minimum-notional linear programme. A first version of this
        audit multiplied one-way notional by the full round-trip rate and fed the
        LP a mixed-space delta.
        """
        audit = mechanics.pair_routing_audit(days=252 * 4)
        charged = audit["charged_isolated_position"]
        implementation = audit["implementation_equal_split_netting"]
        floor = audit["minimal_notional_floor"]
        assert charged["pair_one_way_per_currency_one_way"] == pytest.approx(1.32, abs=1e-2)
        assert charged["cost_per_turnover_unit_bp"] == pytest.approx(3.406)
        assert implementation["pair_one_way_per_currency_one_way"] == pytest.approx(0.77, abs=0.02)
        assert implementation["conservatism_factor_vs_convention"] == pytest.approx(1.71, abs=0.06)
        assert (
            floor["pair_one_way_per_currency_one_way"]
            < (implementation["pair_one_way_per_currency_one_way"])
        )
        assert (
            floor["conservatism_factor_vs_convention"]
            > (implementation["conservatism_factor_vs_convention"])
        )

    def test_the_cost_identity_holds_for_every_row(self) -> None:
        audit = mechanics.pair_routing_audit(days=252 * 2)
        for key in (
            "charged_isolated_position",
            "implementation_equal_split_netting",
            "minimal_notional_floor",
        ):
            row = audit[key]
            assert row["cost_per_turnover_unit_bp"] == pytest.approx(
                row["pair_one_way_per_currency_one_way"] * 2.58, abs=2e-3
            )


class TestConfirmationPower:
    def test_the_fresh_pool_cannot_confirm_a_realistic_edge(self) -> None:
        """⭐ The honest bottleneck, pinned so no later stage forgets it."""
        assert mechanics.one_shot_power(0.5, 4.9) == pytest.approx(0.295, abs=0.01)
        assert mechanics.one_shot_power(0.5, 4.9) < 0.5

    def test_power_rises_with_years_and_edge(self) -> None:
        assert mechanics.one_shot_power(0.5, 25.0) > mechanics.one_shot_power(0.5, 4.9)
        assert mechanics.one_shot_power(1.2, 4.9) > mechanics.one_shot_power(0.5, 4.9)

    def test_eighty_percent_power_at_half_sharpe_needs_decades(self) -> None:
        table = mechanics.confirmation_power_table()
        assert table["years_for_80_percent_power"]["0.5"] == pytest.approx(24.7, abs=0.3)


class TestTheCatalogue:
    def test_twenty_distinct_architectures(self) -> None:
        rows = candidates.catalogue()
        assert len(rows) == 20
        assert len({row.candidate_id for row in rows}) == 20
        assert len({row.mechanism for row in rows}) == 20

    def test_the_three_frequencies_are_stated_separately(self) -> None:
        """⭐ The instruction's §39, enforced as a schema rather than a promise."""
        for row in candidates.catalogue():
            assert row.prediction_frequency_per_year >= 0
            assert row.position_update_frequency_per_year >= 0
            assert row.expected_annual_turnover >= 0
            assert row.turnover_basis.strip()
            #: And the point of separating them: for no continuous candidate may
            #: the turnover silently equal the prediction frequency.
            if row.prediction_frequency_per_year >= 252 and row.role == "core":
                assert row.expected_annual_turnover < row.prediction_frequency_per_year / 4

    def test_every_candidate_names_its_evidence_against(self) -> None:
        for row in candidates.catalogue():
            assert row.evidence_against.strip(), row.candidate_id
            assert row.prior_overlap.strip(), row.candidate_id

    def test_all_four_roles_are_present(self) -> None:
        roles = {row.role for row in candidates.catalogue()}
        assert roles == {"core", "overlay", "efficiency", "evaluation"}

    def test_no_candidate_reopens_a_closed_family(self) -> None:
        for record in candidates.assess_all():
            assert record.get("verdict") != "PRIOR_FAMILY_CLOSED", record["candidate_id"]

    def test_the_closed_family_guard_actually_fires_when_declared(self) -> None:
        """⭐ Both reviews: the guard was decorative — nothing declares gate_family.

        The adjacency judgments stay prose (nothing mechanical can decide them),
        but the mechanism must not rot: a synthetic candidate declaring a closed
        family has to be refused by `assert_prospective`, not by convention.
        """
        import dataclasses

        template = candidates.catalogue()[0]
        declaring = dataclasses.replace(template, gate_family="carry")
        original = candidates.catalogue

        def with_declaring() -> list[candidates.Architecture]:
            return [declaring]

        candidates.catalogue = with_declaring  # type: ignore[assignment]
        try:
            records = candidates.assess_all()
        finally:
            candidates.catalogue = original  # type: ignore[assignment]
        assert records[0]["verdict"] == "PRIOR_FAMILY_CLOSED"
        assert "adjudicated under the rules in force" in records[0]["reason"]
        assert "economics" not in records[0]

    def test_the_development_run_has_a_ledger_entry(self) -> None:
        """⭐ A review found the model-learning run missing from the ledger.

        The ledger's own discipline is that entries are appended when a round
        completes; H-022 now records the run whose measured turnovers this
        package's cost audit is built on.
        """
        from scripts.research.round_a.ledger import LEDGER

        latest = LEDGER[-1]
        assert latest["id"] == "H-022"
        assert "36.7" in latest["result"]
        assert latest["status"].startswith("CLOSED")

    def test_core_economics_carry_required_ic(self) -> None:
        by_id = {record["candidate_id"]: record for record in candidates.assess_all()}
        core = by_id["A01_continuous_currency_portfolio"]["economics"]
        #: A01 declares the mechanics turnover 34.5, so its drag is 0.311 and the
        #: gross requirement 0.811; at the measured 36.7 it would be 0.831.
        assert core["net_5pct_at_10vol"]["required_gross_ir"] == pytest.approx(0.811, abs=0.01)
        assert core["net_5pct_at_10vol"]["required_daily_ic"] == pytest.approx(0.026, abs=0.002)

    def test_the_ranking_is_the_declared_score_and_nothing_else(self) -> None:
        rows = candidates.ranking()
        scores = [row["score"] for row in rows]
        assert scores == sorted(scores, reverse=True)
        by_id = {row.candidate_id: row for row in candidates.catalogue()}
        for row in rows:
            assert row["score"] == candidates.score(by_id[row["candidate_id"]])

    def test_the_selection_takes_one_core_one_overlay_and_the_bundle(self) -> None:
        tracks = candidates.selected_tracks()
        assert tracks["track_1_core"]["role"] == "core"
        assert tracks["track_3_overlay"]["role"] == "overlay"
        bundle = tracks["track_2_efficiency_bundle"]["members"]
        assert len(bundle) >= 3
        by_id = {row.candidate_id: row for row in candidates.catalogue()}
        for member in bundle:
            assert by_id[member].role == "efficiency"
            assert candidates.score(by_id[member]) >= (candidates.EFFICIENCY_BUNDLE_SCORE_FLOOR)

    def test_evaluation_never_occupies_a_track_slot(self) -> None:
        tracks = candidates.selected_tracks()
        for key in ("track_1_core", "track_3_overlay"):
            assert tracks[key]["role"] != "evaluation"
        assert (
            "A20_paper_forward_evaluation" not in (tracks["track_2_efficiency_bundle"]["members"])
        )
        assert tracks["paper_forward_recommended_for_all"] is True


class TestSignalFreedom:
    def test_no_module_can_open_a_market_data_file(self) -> None:
        """The package computes economics without touching a market."""
        for path in sorted(PACKAGE.glob("*.py")):
            if path.name == "driver.py":
                continue
            source = path.read_text(encoding="utf-8")
            for forbidden in ("read_parquet", "read_csv", "urlopen", "open(", "load("):
                assert forbidden not in source, f"{path.name}: {forbidden}"

    def test_the_driver_only_writes_its_own_artifact(self) -> None:
        source = (PACKAGE / "driver.py").read_text(encoding="utf-8")
        for forbidden in ("read_parquet", "read_csv", "urlopen", "read_text"):
            assert forbidden not in source, forbidden

    def test_the_artifact_declares_and_carries_no_realised_quantity(
        self, artifact: dict[str, Any]
    ) -> None:
        assert artifact["signal_free"] is True
        assert artifact["market_data_read"] is False
        assert artifact["protected_spans_read"] is False
        blob = json.dumps(artifact).lower()
        for forbidden in ("realised_return", "observed_ic", "p_value", "pnl"):
            assert forbidden not in blob, forbidden


class TestTheArtifact:
    def test_the_artifact_matches_a_fresh_build(self, artifact: dict[str, Any]) -> None:
        from scripts.research.profit_architecture import driver

        fresh = json.loads(json.dumps(driver.build(), sort_keys=True, default=str))
        committed = json.loads(json.dumps(artifact, sort_keys=True, default=str))
        assert fresh == committed

    def test_the_headline_numbers_are_in_the_artifact(self, artifact: dict[str, Any]) -> None:
        assert artifact["prediction_vs_turnover"]["overstatement_factor_for_the_smooth_book"] == (
            pytest.approx(6.87)
        )
        assert artifact["capacity"]["by_turnover"]["turnover_36.7"]["ir_drag"] == (
            pytest.approx(0.331)
        )
        assert artifact["confirmation_power"]["years_for_80_percent_power"]["0.5"] == (
            pytest.approx(24.7, abs=0.3)
        )
