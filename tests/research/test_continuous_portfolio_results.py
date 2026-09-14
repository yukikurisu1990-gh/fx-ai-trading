"""The Track 1 results document says what the committed run record says.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Reads the committed artefacts only; nothing is recomputed from market data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.research.continuous_portfolio import CASE_C, prereg

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts/research/continuous_portfolio"
DOCUMENT = ROOT / "docs/research/m15_track1_continuous_portfolio_results.md"


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    return json.loads((ARTIFACTS / "development.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def document() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


def test_the_run_executed_the_frozen_preregistration(record: dict[str, Any]) -> None:
    started = json.loads((ARTIFACTS / "development.started.json").read_text(encoding="utf-8"))
    assert record["preregistration_frozen_hash"] == prereg.FROZEN_HASH
    assert started["preregistration_frozen_hash"] == prereg.FROZEN_HASH
    assert record["checkout"] == started["checkout"]
    assert record["checkout"]["sources_differing_from_head"] == []
    assert record["protected_spans_read"] is False
    assert record["broker_access"] is False


def test_the_corpus_stayed_inside_the_seen_spans(record: dict[str, Any]) -> None:
    corpus = record["corpus"]
    assert corpus["observed_first_day"] >= "2021-04-26"
    assert corpus["observed_last_day"] <= "2025-12-28"
    assert record["oos"]["first_decision_day"] == "2023-01-17"


def test_the_document_states_the_recorded_verdict(record: dict[str, Any], document: str) -> None:
    verdict = record["adjudication"]
    assert verdict["case"] == CASE_C
    assert f"**`{CASE_C}`（Case C）。**" in document
    assert f"`{verdict['economic_band']}`" in document
    assert len(verdict["kills_fired"]) == 7
    assert "kill 条項 9 個のうち 7 個が発火した" in document
    assert len(verdict["kill_clauses"]) == 9


@pytest.mark.parametrize(
    ("path", "formatted"),
    [
        (("primary", "summary", "net_sharpe"), "`-0.8425`"),
        (("primary", "summary", "net_annual_return"), "`-0.084198`"),
        (("primary", "summary", "gross_sharpe"), "`-0.4688`"),
        (("primary", "summary", "gross_annual_return"), "`-0.046824`"),
        (("primary", "summary", "cost_annual_drag"), "`0.037374`"),
        (("primary", "summary", "realized_annual_vol"), "`0.099943`"),
        (("primary", "summary", "net_sharpe_at_implementation_cost"), "`-0.7262`"),
        (("primary", "summary", "turnover_round_trips_per_year_per_unit_gross"), "`25.567`"),
        (("adjudication", "unfitted_rules", "reversal_20d", "pnl_correlation"), "`0.6357`"),
        (("adjudication", "unfitted_rules", "reversal_20d", "net_sharpe"), "`0.3141`"),
        (("adjudication", "unfitted_rules", "reversal_60d", "pnl_correlation"), "`0.4889`"),
        (("adjudication", "unfitted_rules", "reversal_60d", "net_sharpe"), "`0.5188`"),
        (("adjudication", "max_pnl_correlation_with_an_unfitted_rule"), "`0.6357`"),
    ],
)
def test_every_pinned_number_is_the_recorded_one(
    record: dict[str, Any], document: str, path: tuple[str, ...], formatted: str
) -> None:
    value: Any = record
    for key in path:
        value = value[key]
    assert f"`{value}`" == formatted
    assert formatted in document


def test_the_identity_section_is_the_recorded_run(record: dict[str, Any], document: str) -> None:
    started = json.loads((ARTIFACTS / "development.started.json").read_text(encoding="utf-8"))
    head = record["checkout"]["head"]
    assert head.startswith("f1939fd")
    assert f"checkout head `{head}`" in document
    assert f"| 凍結 hash | `{record['preregistration_frozen_hash']}` |" in document
    differing = len(record["checkout"]["sources_differing_from_head"])
    assert f"HEAD と異なる source {differing} 件" in document
    marker = started["started_utc"][:19] + "Z"
    assert f"start marker `{marker}`" in document


def test_the_data_section_is_the_recorded_corpus(record: dict[str, Any], document: str) -> None:
    corpus, oos = record["corpus"], record["oos"]
    observed = f"観測 `{corpus['observed_first_day']} … {corpus['observed_last_day']}`"
    assert f"{observed}、{corpus['trading_days']:,} 取引日" in document
    span = f"out-of-fold 判断日 `{oos['first_decision_day']} … {oos['last_decision_day']}`"
    days = f"（{oos['decision_days']} 日、P&L {record['primary']['summary']['days']} 日）"
    assert span + days in document
    assert f"実測 `{oos['days_per_year_measured']}` 取引日/年" in document
    #: the first test day sits `train_rows / 8 + purge + embargo` usable days in,
    #: and every later usable day is a test day
    first_test_index = record["folds"][0]["train_rows"] // 8 + 6
    usable_days = first_test_index + sum(fold["test_days"] for fold in record["folds"])
    assert f"usable days `2021-07-19 … 2025-12-26`（{usable_days:,} 日。" in document


def test_the_protected_section_matches_the_boundaries(
    record: dict[str, Any], document: str
) -> None:
    assert record["corpus"]["observed_first_day"] > "2021-04-25"
    assert record["corpus"]["observed_last_day"] < "2025-12-29"
    assert "| fresh pool `2016-06-02 … 2021-04-25` | **未読**" in document
    assert "| historical OOS（`2025-12-29` 以降） | **研究利用なし**" in document
    assert "| dead window / forward epoch | **未読** |" in document
    ic_days = record["information_diagnostics"]["raw_mu_rank_ic_1d"]["days"]
    assert ic_days == record["oos"]["decision_days"] - 1
    assert f"1 日先 IC の集計日数 {ic_days}" in document


def test_the_walk_forward_section_is_the_recorded_geometry(
    record: dict[str, Any], document: str
) -> None:
    folds = record["folds"]
    tests = "/".join(str(fold["test_days"]) for fold in folds)
    assert f"{len(folds)} fold、test {tests} 日" in document
    per_fold = record["primary"]["summary"]["per_fold_days"]
    assert per_fold[str(folds[-1]["fold"])] == folds[-1]["test_days"] - 1
    assert f"P&L は {per_fold[str(folds[-1]['fold'])]} 日" in document
    assert "purge 5 日 + embargo 1 日" in document
    assert prereg.WALK_FORWARD["purge_days"] == 5 and prereg.WALK_FORWARD["embargo_days"] == 1


def test_the_kill_table_matches_the_record(record: dict[str, Any], document: str) -> None:
    fired = record["adjudication"]["kill_clauses"]
    assert not fired["turnover_unexpectedly_high"]
    assert not fired["leverage_cap_binds_most_days"]
    assert "| turnover > 50 RT/年/単位 gross | no（25.6） |" in document
    assert "| cap 5× 要求日 > 50% | no（46.4%） |" in document
    assert record["primary"]["summary"]["share_days_at_leverage_cap"] == 0.464


def test_the_inverted_benchmark_is_recorded_as_post_hoc_not_as_a_candidate(document: str) -> None:
    assert "B1 reversal の正の数字は候補ではない。通貨レベルの reversal family 全体" in document
    assert "`POST_HOC_EXPLORATORY`" in document
    assert "MULTI_DAY_REVERSAL_FAMILY_DROPPED_FROM_ACTIVE_EXPLORATORY_RESEARCH" in document
    assert "dropped の multi-day reversal\nfamily を再開しない" in document
    assert "FX_HAS_NO_EDGE` ではない" in document


def test_the_cost_and_tail_readings_follow_from_the_record(
    record: dict[str, Any], document: str
) -> None:
    primary = record["primary"]["summary"]
    share = primary["cost_annual_drag"] / -primary["net_annual_return"]
    assert f"= {share:.0%}" in document
    bound = primary["net_annual_return"] - primary["net_inside_3_robust_sigma_annual"]
    assert f"**{bound * 100:.2f}%/年以下**".replace("-", "−") in document
    assert f"**{bound / primary['net_annual_return']:.0%} 以上**" in document
