"""Programme evidence synthesis (2026-09-28): ledger integrity, tiers, rules, signal-blind math."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from scripts.research.programme import assemble, rules
from scripts.research.programme import feasibility_math as fm
from scripts.research.programme import synthesis as syn

REPO = Path(__file__).resolve().parents[2]
PROGRAMME = REPO / "scripts/research/programme"


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    return syn.load_ledger()


# ----------------------------------------------------------------------
# signal-blind math
# ----------------------------------------------------------------------
def test_years_needed_matches_closed_form() -> None:
    assert fm.years_needed(0.2) == pytest.approx(196.2, abs=0.1)
    assert fm.years_needed(0.3) == pytest.approx(87.2, abs=0.1)
    assert fm.years_needed(0.5) == pytest.approx(31.4, abs=0.1)
    assert fm.mde_sharpe(fm.years_needed(0.4)) == pytest.approx(0.4)


def test_aggregation_formula_and_ceiling() -> None:
    assert fm.aggregate_sharpe(0.1, 1, 0.3) == pytest.approx(0.1)
    assert fm.aggregate_sharpe(0.1, 10, 0.0) == pytest.approx(0.1 * math.sqrt(10))
    #: as N grows the composite approaches s / sqrt(rho), never beyond
    assert fm.aggregate_sharpe(0.1, 10_000, 0.1) < 0.1 / math.sqrt(0.1)
    assert fm.aggregate_sharpe(0.1, 10_000, 0.1) == pytest.approx(0.1 / math.sqrt(0.1), rel=1e-3)
    reach = fm.aggregation_scenarios()["min_n_to_reach_target"]
    assert reach["target=0.5|s=0.2|rho=0.1"] == 15
    assert reach["target=0.5|s=0.1|rho=0.1"] is None


def test_drag_is_additive_in_sharpe_units_and_vol_invariant() -> None:
    table = fm.objective_table(
        financing_drag_sharpe={"optimistic": 0.0, "central": 0.07, "conservative": 0.27},
        tc_drag_sharpe={"median": 0.4},
        prior_mean=0.0,
        prior_sd=0.1,
    )["rows"]
    for key, row in table.items():
        gap = row["tc_net_ex_financing_required"]["conservative"] - row["net_all_in"]
        assert gap == pytest.approx(0.27, abs=1e-3), key
        assert row["gross_required_at_central_financing"]["median"] - row[
            "net_all_in"
        ] == pytest.approx(0.47, abs=1e-3)
    assert table["5%@vol10%"]["net_all_in"] == pytest.approx(0.5)
    assert table["5%@vol20%"]["stress_only"] is True
    assert table["5%@vol10%"]["stress_only"] is False


def test_drawdown_variants_are_not_more_optimistic_than_iid() -> None:
    iid = fm.drawdown_distribution(0.5, 0.10, paths=1000)
    for variant in ("stochastic_vol", "gap"):
        other = fm.drawdown_distribution(0.5, 0.10, paths=1000, variant=variant)
        assert other["p10_max_dd"] <= iid["p10_max_dd"] + 0.01, variant


# ----------------------------------------------------------------------
# known-answer tests for the estimators
# ----------------------------------------------------------------------
def test_binomial_tail_known_values() -> None:
    assert syn._binomial_tail(0, 7, 0.3) == pytest.approx(1.0)
    assert syn._binomial_tail(7, 7, 0.3) == pytest.approx(0.3**7)
    assert syn._binomial_tail(1, 10, 0.05) == pytest.approx(1 - 0.95**10)


def test_normal_normal_fit_homogeneous_gives_tau_zero() -> None:
    fit = syn.fit_normal_normal(np.array([0.1, 0.1, 0.1, 0.1]), np.full(4, 0.05))
    assert fit["mu_hat"] == pytest.approx(0.1, abs=0.006)
    assert fit["tau_hat"] == pytest.approx(0.0)
    assert fit["boundary_hit"] is False


def test_normal_normal_fit_close_to_dersimonian_laird() -> None:
    s = np.array([-0.9, -0.4, 0.0, 0.3, 0.8, 1.1])
    se2 = np.full(6, 0.04)
    w = 1 / se2
    mu_fe = float(np.sum(w * s) / np.sum(w))
    q = float(np.sum(w * (s - mu_fe) ** 2))
    tau2_dl = max(0.0, (q - (len(s) - 1)) / (np.sum(w) - np.sum(w**2) / np.sum(w)))
    fit = syn.fit_normal_normal(s, se2)
    #: with equal se, ML tau² = (1/n)·Σ(s−μ)² − se², DL = (1/(n−1))·Σ(s−μ)² − se²
    ml_expected = float(np.mean((s - mu_fe) ** 2)) - 0.04
    assert fit["tau_hat"] ** 2 == pytest.approx(ml_expected, rel=0.05)
    assert tau2_dl > ml_expected
    assert fit["mu_hat"] == pytest.approx(mu_fe, abs=0.006)
    assert fit["tau_upper_95"] > fit["tau_hat"]


def test_normal_normal_fit_flags_grid_boundary() -> None:
    assert (
        syn.fit_normal_normal(np.array([-4.0, 4.0, -4.0, 4.0]), np.full(4, 0.01))["boundary_hit"]
        is True
    )


def test_forward_information_matches_conjugate_formula() -> None:
    out = fm.forward_information(prior_mean=0.1, prior_sd=0.2)["rows"]["12m"]
    assert out["se_of_sharpe"] == pytest.approx(1.0)
    assert out["posterior_sd"] == pytest.approx(math.sqrt(1 / (1 / 0.04 + 1)), abs=1e-3)


# ----------------------------------------------------------------------
# tiers
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("row", "tier"),
    [
        ({"invalid": True, "post_result_correction": True, "is_primary": True}, "E"),
        ({"post_result_correction": True, "is_primary": True, "preregistered": True}, "C"),
        (
            {
                "ledger_part": "E",
                "is_primary": True,
                "preregistered": True,
                "variant_type": "DISTINCT_MECHANISM",
            },
            "D",
        ),
        ({"is_primary": False, "preregistered": True, "variant_type": "DISTINCT_MECHANISM"}, "D"),
        ({"is_primary": True, "preregistered": True, "variant_type": "SENSITIVITY"}, "D"),
        ({"is_primary": True, "preregistered": True, "variant_type": "HORIZON_VARIANT"}, "B"),
        ({"is_primary": True, "preregistered": False, "variant_type": "DISTINCT_MECHANISM"}, "B"),
        (
            {
                "is_primary": True,
                "preregistered": True,
                "variant_type": "DISTINCT_MECHANISM",
                "selected_best_of_n": 39,
            },
            "B",
        ),
        ({"is_primary": True, "preregistered": True, "variant_type": "DISTINCT_MECHANISM"}, "A"),
    ],
)
def test_tier_of(row: dict, tier: str) -> None:
    assert syn.tier_of(row) == tier


# ----------------------------------------------------------------------
# ledger integrity
# ----------------------------------------------------------------------
def test_committed_ledger_matches_parts() -> None:
    committed = json.loads(assemble.LEDGER.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(assemble.build(), ensure_ascii=False, default=str))


def test_every_row_has_schema_source_and_unique_id(rows: list[dict]) -> None:
    ids = [r["track_id"] for r in rows]
    assert len(ids) == len(set(ids))
    for r in rows:
        assert set(assemble.SCHEMA_KEYS) <= set(r)
        assert r["source"], r["track_id"]


def test_every_row_is_full_retail_net_unknown(rows: list[dict]) -> None:
    assert {r["full_retail_net"] for r in rows} == {"FULL_RETAIL_NET_UNKNOWN"}
    allowed = {None, "NONE", "APPROXIMATE_CARRY_AND_MARKUP", "RESEARCH_CARRY_POLICY_RATES"}
    assert {r["financing_included"] for r in rows} <= allowed
    for r in rows:
        if r["financing_included"] in {None, "NONE"}:
            assert r["net_definition"] == "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING"


def test_ruled_statuses_are_recorded_unchanged(rows: list[dict]) -> None:
    by_id = {r["track_id"]: r for r in rows}
    assert by_id["USDF_M15_long_total"]["result_status"].startswith(
        "M15_CORRECTED_FINANCING_NOT_DECISION_GRADE"
    )
    assert by_id["USDF_M16_long_total"]["result_status"].startswith(
        "M16_CORRECTED_POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"
    )
    assert by_id["MR_M11_long"]["result_status"] == "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"
    assert by_id["MR_M01_long"]["result_status"] == "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"
    assert by_id["MR_M10_recent"]["result_status"] == "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
    #: post-result corrected runs are never promoted to tier A or B
    for track in ("USDF_M15_long_total", "USDF_M16_long_total"):
        assert by_id[track]["evidence_tier"] == "C"
    assert by_id["MR_M15_long"]["evidence_tier"] == "E"
    assert by_id["MR_M16_long"]["evidence_tier"] == "E"
    #: the best of 39 cells is not tier A, and bar-level sharpe_like is not a comparable Sharpe
    assert by_id["R2_reversal_family_primary"]["evidence_tier"] == "B"
    assert by_id["R2_reversal_family_primary"]["sharpe_comparable"] is False


def test_legacy_era_never_enters_the_sharpe_pool(rows: list[dict]) -> None:
    for r in rows:
        if r["ledger_part"] == "E":
            assert r["sharpe_comparable"] is False
            assert r["evidence_tier"] in {"D", "E"}


def test_mixed_net_definitions_are_not_pooled(rows: list[dict]) -> None:
    by_id = {r["track_id"]: r for r in rows}
    #: M01 pools its spot-only TC-net; its judged net (carry + markup) is kept apart
    assert by_id["MR_M01_long"]["sharpe_ex_financing"] == pytest.approx(0.2961)
    assert by_id["MR_M01_long"]["judged_net_sharpe_incl_approx_financing"] == pytest.approx(
        0.0804, abs=1e-3
    )
    #: #495 total rows pool their ex-financing twin, never the financing-inclusive value
    assert (
        by_id["USDF_M16_long_total"]["sharpe_ex_financing"]
        == by_id["USDF_M16_long_exfin"]["tc_adjusted_sharpe"]
    )
    #: model-learning costs are in bp/yr and flagged as such
    assert by_id["ML_A_M01_model"]["annual_cost_unit"] == "BP_PER_YEAR"


# ----------------------------------------------------------------------
# synthesis
# ----------------------------------------------------------------------
def test_shrinkage_counts_each_mechanism_and_span_once(rows: list[dict]) -> None:
    by_id = {r["track_id"]: r for r in rows}
    for tiers in ({"A"}, {"A", "B"}, {"A", "B", "C"}):
        result = syn.shrinkage(rows, tiers)
        ids = [m["mechanism_id"] for m in result["mechanisms"]]
        assert len(ids) == len(set(ids))
        for mechanism in result["mechanisms"]:
            spans = [by_id[t]["span_dates"] or by_id[t]["span_label"] for t in mechanism["members"]]
            assert len(spans) == len(set(spans)), mechanism
            for t in mechanism["members"]:
                assert by_id[t]["variant_type"] != "SIGN_VARIANT"
                assert by_id[t]["is_primary"]


def test_horizon_variant_on_the_same_span_is_not_a_second_mechanism(rows: list[dict]) -> None:
    result = syn.shrinkage(rows, {"A", "B"})
    members = [t for m in result["mechanisms"] for t in m["members"]]
    assert "TR_C" in members
    assert "TR2_D" not in members


def test_gross_sign_is_counted_per_mechanism(rows: list[dict]) -> None:
    out = syn.null_comparison(rows, {"A", "B", "C"})
    groups = syn.mechanism_groups(
        [r for r in rows if r.get("financing_included") in (None, "NONE")],
        {"A", "B", "C"},
        measure="gross_sharpe",
    )
    sign = out["gross_sign_by_mechanism"]
    assert sign["positive"] + sign["negative"] == len(groups)


def test_committed_synthesis_is_current() -> None:
    from scripts.research.programme import run

    committed = json.loads(run.OUT.read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(run.build(), ensure_ascii=False, sort_keys=True, default=str))
    assert committed == fresh


# ----------------------------------------------------------------------
# rules
# ----------------------------------------------------------------------
def test_missing_values_are_unknown_not_pass() -> None:
    result = rules.forward_eligibility({"track_id": "x", "evidence_tier": "A"})
    assert result["eligible_to_raise_to_human"] is False
    assert "F2_beats_null_on_every_deciding_span" in result["unknown_not_recorded"]
    assert "F2_beats_null_on_every_deciding_span" not in result["failed"]


def test_no_ledger_row_is_eligible_for_forward(rows: list[dict]) -> None:
    assert not [
        r["track_id"] for r in rows if rules.forward_eligibility(r)["eligible_to_raise_to_human"]
    ]


def test_f2_uses_family_p_and_every_deciding_span(rows: list[dict]) -> None:
    by_id = {r["track_id"]: r for r in rows}
    cell = by_id["EX_MACRO_cpi_1h_p2325"]
    assert cell["p_value"] <= 0.05
    #: the cell p passes alone, but the recorded family-max p (0.124) does not
    assert (
        rules.forward_eligibility(cell)["checks"]["F2_beats_null_on_every_deciding_span"] is False
    )
    good = {"track_id": "a", "p_value": 0.01}
    bad = {"track_id": "b", "p_value": 0.4}
    assert (
        rules.forward_eligibility(good, [bad])["checks"]["F2_beats_null_on_every_deciding_span"]
        is False
    )
    assert (
        rules.forward_eligibility(good, [good])["checks"]["F2_beats_null_on_every_deciding_span"]
        is True
    )


def test_f3_requires_conservative_financing_and_f4_rejects_signal_states(rows: list[dict]) -> None:
    by_id = {r["track_id"]: r for r in rows}
    #: M11 TC-net 0.19 is positive but not after the conservative financing drag (0.274)
    assert (
        rules.forward_eligibility(by_id["MR_M11_long"])["checks"][
            "F3_positive_after_conservative_financing"
        ]
        is False
    )
    #: Top-Five records distinct signal states, which are not an effective N
    assert rules.forward_eligibility(by_id["TOP5_T5_recent"])["checks"]["F4_effective_n"] is None


def test_broker_trigger_not_met_for_m15(rows: list[dict]) -> None:
    by_id = {r["track_id"]: r for r in rows}
    result = rules.broker_auth_trigger(
        by_id["USDF_M15_long_exfin"], sign_changes_across_financing_cells=True
    )
    assert result["met"] is False
    assert result["checks"]["B1_ex_financing_edge_beats_null"] is False


def test_financing_sign_changes_are_read_from_the_cells() -> None:
    from scripts.research.programme import run

    cells = run._financing_cells()
    assert cells["M15"]["sign_changes_across_cells"] is True
    assert cells["M16"]["sign_changes_across_cells"] is False
    assert cells["drag_sharpe"]["conservative_markup_2pct"] == pytest.approx(0.274, abs=1e-3)


def test_d_m3_is_recorded_with_jpy_scope_only() -> None:
    entry = next(e for e in rules.PROTECTED_INFORMATION_LEDGER if e["state"] == rules.D_M3_TOKEN)
    assert "JPY" in entry["scope"]
    assert (
        rules.D_M3_TOKEN
        == "JPY_RATE_RELATED_FORWARD_CONFIRMATION_CONTAMINATED_BY_EXTERNAL_INFORMATION_EXPOSURE"
    )


def test_rate_exposure_follows_signal_and_judged_pnl(rows: list[dict]) -> None:
    by_id = {r["track_id"]: r for r in rows}
    #: M01 signal uses policy rates; M11 judged P&L accrues carry; M15/M16 totals too
    for track in ("MR_M01_long", "MR_M11_long", "USDF_M15_long_total", "USDF_M16_long_total"):
        assert rules.forward_eligibility(by_id[track])["checks"]["F6_not_contaminated"] is False, (
            track
        )
    #: FX reference rates and CPI (spot-only book) are not interest rates: D-M3 does not reach them
    assert rules.forward_eligibility(by_id["TV_C"])["checks"]["F6_not_contaminated"] is True


def test_pause_is_not_automatic() -> None:
    assert "自動では立てない" in rules.PAUSE_POLICY


def test_closure_never_claims_fx_has_no_edge() -> None:
    assert "FX に edge は無い』とは言わない" in rules.CLOSURE_PRINCIPLE
    for item in rules.CLOSED:
        assert item["span_and_mde"]
    assert any("carry" in entry for entry in rules.OPEN["UNDERPOWERED"])


def test_programme_package_reads_no_market_data_and_no_network() -> None:
    forbidden = (
        "read_parquet",
        "urllib",
        "requests",
        "http.client",
        "socket",
        "subprocess",
        "ARCHIVE",
    )
    for path in PROGRAMME.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} contains {token}"


# ----------------------------------------------------------------------
# known-answer tests for pooling, counting and predictive shares
# ----------------------------------------------------------------------
def _row(track: str, sharpe: float, years: float, span: str, **extra: object) -> dict:
    base = {
        "track_id": track,
        "mechanism_id": extra.pop("mechanism_id", track),
        "evidence_tier": "A",
        "sharpe_comparable": True,
        "is_primary": True,
        "variant_type": "DISTINCT_MECHANISM",
        "sharpe_ex_financing": sharpe,
        "gross_sharpe": sharpe + 0.1,
        "financing_included": "NONE",
        "calendar_years": years,
        "span_dates": span,
    }
    base.update(extra)
    return base


def test_mechanism_groups_year_weighted_pooling() -> None:
    rows = [
        _row("M_long", 0.2, 15.0, "1999..2016", mechanism_id="M"),
        _row("M_recent", -0.4, 5.0, "2021..2025", mechanism_id="M"),
        _row("M_dup", 9.9, 5.0, "2021..2025", mechanism_id="M", variant_of="M_long"),
        _row("N_mirror", 0.5, 10.0, "1999..2016", variant_type="SIGN_VARIANT"),
    ]
    groups = syn.mechanism_groups(rows, {"A"})
    assert [g["mechanism_id"] for g in groups] == ["M"]
    assert groups[0]["years"] == pytest.approx(20.0)
    assert groups[0]["sharpe"] == pytest.approx((0.2 * 15 - 0.4 * 5) / 20)


def test_null_comparison_counts_known_input() -> None:
    rows = [
        _row(f"t{i}", 0.1, 10.0, f"s{i}", p_value=p)
        for i, p in enumerate((0.01, 0.04, 0.2, 0.5, 0.9))
    ]
    rows[0]["null_percentile"] = 0.97
    out = syn.null_comparison(rows, {"A"})
    assert out["p_le_005"]["actual"] == 2
    assert out["p_le_005"]["expected_false_positives_under_null"] == pytest.approx(0.25)
    assert out["percentile_counts"][">=0.95"]["actual"] == 1
    assert out["gross_sign_by_mechanism"] == {
        "positive": 5,
        "negative": 0,
        "prob_at_least_positive_if_null_half": pytest.approx(1 / 32, abs=1e-3),
    }


def test_predictive_share_is_never_degenerate_at_tau_zero(rows: list[dict]) -> None:
    fit = syn.shrinkage(rows, {"A"})
    share = fit["share_true_above_predictive"]["0.0"]["at_tau_hat"]
    assert 0.0 < share < 1.0
    expected = 1 - __import__("statistics").NormalDist(fit["mu_hat"], fit["mu_se_lower_bound"]).cdf(
        0.0
    )
    assert share == pytest.approx(expected, abs=0.01)


def test_forward_probability_matches_predictive_formula() -> None:
    from statistics import NormalDist

    out = fm.forward_information(prior_mean=0.2, prior_sd=0.3)["rows"]["24m"]
    se = math.sqrt(1 / 2)
    predictive = math.sqrt(0.3**2 + se**2)
    expected = 1 - NormalDist(0.2, predictive).cdf(1.959964 * se)
    assert out["prob_forward_alone_z_above_1_96_one_sided_2_5pct"] == pytest.approx(
        expected, abs=1e-3
    )


def test_family_max_p_takes_precedence_over_cell_percentile() -> None:
    row = {"track_id": "x", "null_percentile": 0.99, "notes": "family_max_p=0.40"}
    assert rules.forward_eligibility(row)["checks"]["F2_beats_null_on_every_deciding_span"] is False


def test_policy_rate_surprise_and_statement_tone_are_rate_exposed(rows: list[dict]) -> None:
    by_id = {r["track_id"]: r for r in rows}
    for track in ("T2_policy_rate_p2123", "NF_U3_recent"):
        assert by_id[track]["rate_exposure"] is True, track
