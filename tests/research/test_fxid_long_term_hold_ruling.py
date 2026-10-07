"""FXID の長期保留の裁定（governance）の内容を固定する contract test。"""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
RULING = REPO / "docs/governance/fxid_long_term_hold_ruling_2026_10.md"


def _text() -> str:
    return RULING.read_text(encoding="utf-8")


def test_final_state_and_reason_tokens_are_recorded():
    text = _text()
    assert "**最終 state: `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`**" in text
    assert "`NO_JUSTIFIED_ALPHA_CYCLE_AT_CURRENT_COST_DATA_AND_EVIDENCE`" in text


def test_required_sections_are_present_in_order():
    headings = re.findall(r"^## (\d+)\. (.+)$", _text(), flags=re.M)
    assert [title for _, title in headings] == [
        "Final ruling",
        "Scope",
        "What the ruling means",
        "What it does NOT mean",
        "Evidence summary",
        "Near-miss mechanisms",
        "Why no alpha cycle is justified",
        "Preserved statistical / governance settings",
        "Restart triggers",
        "Actions prohibited during HOLD",
        "Reopen procedure",
        "Relationship to previous programme rulings",
        "Provenance",
        "Human + ChatGPT approval date",
    ]


def test_overstated_conclusions_are_not_written():
    text = _text().replace(" ", "")
    for phrase in (
        "FXにedgeは無い",
        "FXにedgeはない",
        "FXデイトレードは不可能",
        "すべての戦略を検証し尽くした",
        "M15では利益を出せない",
    ):
        assert phrase not in text, phrase
    assert "`NO_EDGE` とは記録しない" in _text()
    assert _text().count("`NO_EDGE`") == 1


def test_section_4_denials_are_pinned():
    section = _text().split("## 4. What it does NOT mean", 1)[1].split("## 5.", 1)[0]
    assert section.count("という判定ではない") >= 4
    for line in (
        "- FX の日中に edge が存在しない、という判定ではない",
        "- FX のデイトレードで利益を上げることが原理的にできない、という判定ではない。",
        "- あらゆる戦略を検証した、という判定ではない。",
        "- M15 の解像度では利益が出せない、という判定ではない。",
    ):
        assert line in section, line


def test_economic_magnitude_layer_numbers():
    text = _text()
    assert "| EUR の欧州の朝の short | 0.131 | 0.078〜0.115 |" in text
    assert "| JPY の東京の仲値の後 | 0.126 | 0.115〜0.119 |" in text
    assert "2013 年以降" in text


def test_near_misses_are_kept():
    text = _text()
    assert "EUR の欧州の朝の short" in text
    assert "02:00 ET → 08:15 ET" in text
    assert "**0.2〜0.75**" in text
    assert "JPY の東京の仲値の後" in text


def test_preserved_settings():
    text = _text()
    assert "`shrunk / posterior expected net Sharpe ≥ 1.0`" in text
    assert "0.8 には下げない" in text
    assert "**未凍結**" in text
    assert "**限定的な候補**" in text
    assert "2021–2025 の seen data を、新しい独立な data に戻してはならない" in text
    assert "**個々の strategy に必ず Sharpe 1.0 を要求するという意味にはしない**" in text
    assert "`μ = 0, τ = 0.4`" in text


def test_cost_trigger_is_all_in_and_not_automatic():
    text = _text()
    assert "`ALL_IN_ROUND_TRIP_COST ≤ 1.0 BP`" in text
    assert "spread + slippage + execution friction" in text
    assert "**spread ≤ 1 bp ではない**" in text
    assert "**研究を自動で再開してはならない。**" in text
    assert "**1 bp 以下になったら自動的に alpha 研究を始める、という意味ではない。**" in text
    assert "`FXID_REOPEN_REVIEW_PROPOSAL`" in text
    assert "**再開の trigger が観測された場合でも、agent はこれらを自動で行わない。**" in text
    for non_trigger in (
        "「AI の model が進化した」",
        "「新しい indicator を思いついた」",
        "LightGBM",
    ):
        assert non_trigger in text, non_trigger


def test_previous_rulings_are_unchanged():
    text = _text()
    for token in (
        "`LONG_TERM_HOLD`",
        "`NO_FURTHER_SEEN_DATA_ALPHA_SEARCH`",
        "`STAGE0_RED_RETURN_TO_HUMAN`",
        "`FXID_CYCLE1_EXIT_CONDITION_II_FIRED_RETURN_TO_HUMAN`",
        "`R_A2B_ECON_PARTIAL`",
    ):
        assert token in text, token


def test_pr503_provenance():
    text = _text()
    assert "**`332719e`**" in text
    for sha in ("`957fa3d`", "`1b05255`", "`03ce274`"):
        assert sha in text, sha
    assert "`58967b7`" in text
