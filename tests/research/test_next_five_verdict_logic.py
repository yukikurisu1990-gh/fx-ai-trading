"""凍結した VERDICT_LOGIC を、実データを使わずに押さえる。

**第 2 裁定 §1 の 2 つの禁止をここで固定する。**

- `p > 0.05 -> automatically NOT_SUPPORTED` は禁止
- `p ≤ 0.05 だから candidate 成立` とも扱わない
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.research.next_five import execute


def _metrics(**overrides: Any) -> dict[str, Any]:
    base = {
        "gross_sharpe": 0.8,
        "net_sharpe": 0.6,
        "incremental_ic": 0.02,
        "positive_temporal_blocks": "12/17",
        "leave_one_currency_out_net_sharpe": {"USD": 0.4, "JPY": 0.5, "EUR": 0.55},
        "top_10_day_contribution": 0.3,
    }
    base.update(overrides)
    return base


def _stressed(x2: float = 0.4) -> dict[str, Any]:
    return {"cost_x1.5": {"net_sharpe": x2 + 0.1}, "cost_x2.0": {"net_sharpe": x2}}


def _primary(p: float, percentile: float, **metric_overrides: Any) -> dict[str, Any]:
    metrics = _metrics(**metric_overrides)
    economics = execute.development_economics(metrics, _stressed())
    net = float(metrics["net_sharpe"])
    return {
        "metrics": metrics,
        "development_economics": economics,
        "null_diagnostic": {
            "p_value": p,
            "observed_percentile": percentile,
            "label": (
                "NULL_REJECTION_SUPPORTED"
                if (p <= 0.05 and net > 0)
                else "NULL_REJECTION_NOT_SUPPORTED"
            ),
        },
    }


class TestAHighPValueIsNotANegativeVerdict:
    def test_positive_economics_with_p_above_five_percent_is_not_not_supported(self) -> None:
        out = execute.verdict("U1", _primary(p=0.12, percentile=0.88), None, None)
        assert "NOT_SUPPORTED" not in out["status"]
        assert out["status"].endswith("MARGINAL_DEVELOPMENT_CANDIDATE")

    def test_positive_net_with_a_weak_null_is_exploratory_not_negative(self) -> None:
        out = execute.verdict("U1", _primary(p=0.40, percentile=0.60), None, None)
        assert out["status"].endswith("POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE")


class TestALowPValueAloneIsNotACandidate:
    def test_p_below_five_percent_without_economics_is_not_strong(self) -> None:
        """E8（net ≥ 0.30）を満たさない → economics は SUPPORTED にならない。"""
        primary = _primary(p=0.01, percentile=0.99, net_sharpe=0.2, gross_sharpe=0.3)
        out = execute.verdict("U1", primary, None, None)
        assert not out["status"].endswith("STRONG_DEVELOPMENT_CANDIDATE")

    def test_strong_needs_both_axes(self) -> None:
        out = execute.verdict("U1", _primary(p=0.01, percentile=0.99), None, None)
        assert out["status"].endswith("STRONG_DEVELOPMENT_CANDIDATE")
        assert out["economics_label"] == "DEVELOPMENT_ECONOMICS_SUPPORTED"
        assert out["null_label"] == "NULL_REJECTION_SUPPORTED"


class TestNegativeNetIsTheOnlyRouteToNotSupported:
    @pytest.mark.parametrize("p", [0.001, 0.04, 0.5, 0.99])
    def test_non_positive_net_is_not_supported_whatever_the_p_value(self, p: float) -> None:
        primary = _primary(p=p, percentile=1 - p, net_sharpe=-0.1, gross_sharpe=0.2)
        out = execute.verdict("U1", primary, None, None)
        assert out["status"].endswith("NOT_SUPPORTED_IN_SEEN_DEVELOPMENT")

    def test_gross_negative_is_a_signal_failure(self) -> None:
        primary = _primary(p=0.5, percentile=0.5, net_sharpe=-0.3, gross_sharpe=-0.1)
        assert execute.verdict("U1", primary, None, None)["failure_class"] == "SIGNAL_FAILURE"

    def test_gross_positive_net_negative_is_a_cost_failure(self) -> None:
        primary = _primary(p=0.5, percentile=0.5, net_sharpe=-0.3, gross_sharpe=0.4)
        assert execute.verdict("U1", primary, None, None)["failure_class"] == "COST_FAILURE"


class TestTheOtherCriteriaAreLoadBearing:
    def test_one_currency_carrying_the_book_blocks_strong(self) -> None:
        primary = _primary(
            p=0.01,
            percentile=0.99,
            leave_one_currency_out_net_sharpe={"USD": -0.1, "JPY": 0.5},
        )
        out = execute.verdict("U1", primary, None, None)
        assert not out["status"].endswith("STRONG_DEVELOPMENT_CANDIDATE")

    def test_top_day_concentration_blocks_strong(self) -> None:
        primary = _primary(p=0.01, percentile=0.99, top_10_day_contribution=0.8)
        assert not execute.verdict("U1", primary, None, None)["status"].endswith(
            "STRONG_DEVELOPMENT_CANDIDATE"
        )

    def test_unstable_blocks_marginal(self) -> None:
        primary = _primary(p=0.12, percentile=0.88, positive_temporal_blocks="4/17")
        out = execute.verdict("U1", primary, None, None)
        assert out["status"].endswith("POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE")

    def test_no_incremental_information_blocks_marginal(self) -> None:
        primary = _primary(p=0.12, percentile=0.88, incremental_ic=-0.001)
        out = execute.verdict("U1", primary, None, None)
        assert out["status"].endswith("POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE")

    def test_a_rename_overrides_everything(self) -> None:
        out = execute.verdict("U5", _primary(p=0.01, percentile=0.99), None, {"verdict": "RENAME"})
        assert out["status"].endswith("RENAME_OF_A_CLOSED_TRACK")


class TestStageTwoEligibility:
    def test_eligible_without_p_below_five_percent(self) -> None:
        primary = _primary(p=0.15, percentile=0.85)
        assert execute.stage2_eligible(primary["development_economics"], primary["null_diagnostic"])

    def test_not_eligible_below_the_eightieth_percentile(self) -> None:
        primary = _primary(p=0.3, percentile=0.7)
        assert not execute.stage2_eligible(
            primary["development_economics"], primary["null_diagnostic"]
        )

    def test_not_eligible_without_the_economic_core(self) -> None:
        primary = _primary(p=0.01, percentile=0.99, net_sharpe=-0.2)
        assert not execute.stage2_eligible(
            primary["development_economics"], primary["null_diagnostic"]
        )
