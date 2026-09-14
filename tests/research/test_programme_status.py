"""The pause record, its machine-readable copy, the ledger, the sources and CLAUDE.md agree.

Reads committed documents and artefacts only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from scripts.research import programme_status as ps
from scripts.research.model_learning import PROTECTED_SPANS
from scripts.research.round_a.ledger import LEDGER, summary

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/research/m15_fx_spot_active_alpha_research_pause.md"
TRACK_1_RECORD = ROOT / "artifacts/research/continuous_portfolio/development.json"

#: Where each phase's status tokens are recorded on master.
PHASE_SOURCES: dict[str, str] = {
    "#465": "docs/research/m15_track_a_exploratory_round_2_results.md",
    "#466": "docs/research/m15_track_a_supplemental_replication_results.md",
    "#467": "docs/research/m15_track_a_momentum_hypothesis_results.md",
    "#468": "docs/research/m15_round_a_results.md",
    "#469": "docs/research/m15_round_b_prime_results.md",
    "#470": "docs/research/m15_monetizability_results.md",
    "#471": "docs/research/m15_economic_edge_source_expansion_results.md",
    "#472": "docs/research/m15_exogenous_directional_information_results.md",
    "#474": "docs/research/m15_fx_spot_frontier_unit_audit.md",
    "#475": "docs/research/m15_track_3_execution_frontier.md",
    "#476": "docs/design/m15_feasibility_gate_v2.md",
    "#477": "docs/research/m15_track_2_non_usd_surprise_results.md",
    "#478": "docs/research/m15_decision_grade_research_inventory.md",
    "#479": "docs/research/m15_model_learning_candidate_universe.md",
    "#480": "docs/research/m15_profit_architecture_redesign.md",
    "#481/#482": "docs/research/m15_track1_continuous_portfolio_results.md",
}


@pytest.fixture(scope="module")
def document() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    return json.loads(TRACK_1_RECORD.read_text(encoding="utf-8"))


def _section(document: str, start: str, end: str) -> str:
    return document.split(start, 1)[1].split(end, 1)[0]


def _rows(section: str) -> list[str]:
    return [
        line.rstrip()
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    ]


class TestEveryTableRowIsTheModule:
    def test_the_statuses(self, document: str) -> None:
        rows = _rows(_section(document, "## 1. 裁定と status", "**原則**"))[1:]
        assert rows == [f"| {key} | `{token}` | {prov} |" for key, token, prov in ps.STATUSES]

    def test_the_principles(self, document: str) -> None:
        rows = _rows(_section(document, "**原則**", "## 2."))[1:]
        assert rows == [f"| `{token}` | {prov} |" for token, prov in ps.PRINCIPLES]

    def test_the_prohibited_rescues(self, document: str) -> None:
        rows = _rows(_section(document, "**禁止する救済**", "## 6."))[1:]
        assert rows == [f"| {text} | {prov} |" for text, prov in ps.PROHIBITED_RESCUES]

    def test_the_complex_ml_list(self, document: str) -> None:
        rows = _rows(_section(document, "**未承認**", "## 7."))[1:]
        assert rows == [f"| {text} | {prov} |" for text, prov in ps.COMPLEX_ML_NOT_AUTHORISED]

    def test_the_tail_diagnostics(self, document: str) -> None:
        rows = _rows(_section(document, "## 9. Tail diagnostics", "## 10."))[1:]
        assert rows == [f"| {text} | {prov} |" for text, prov in ps.TAIL_DIAGNOSTICS]

    def test_the_paused_and_continuing_activities(self, document: str) -> None:
        paused = _rows(_section(document, "**停止するもの**", "**停止しないもの**"))[1:]
        continuing = _rows(_section(document, "**停止しないもの**", "## 12."))[1:]
        assert paused == [f"| {text} | {prov} |" for text, prov in ps.PAUSED_ACTIVITIES]
        assert continuing == [f"| {text} | {prov} |" for text, prov in ps.CONTINUING_ACTIVITIES]

    def test_the_resumption_conditions(self, document: str) -> None:
        rows = _rows(_section(document, "## 12. 再開条件", "RC-1 の根拠"))[1:]
        expected = [f"| {cid} | {text} | {prov} |" for cid, text, prov in ps.RESUMPTION_CONDITIONS]
        assert rows == expected

    def test_every_provenance_label_is_a_declared_one(self) -> None:
        tables = (
            [p for _, _, p in ps.STATUSES],
            [p for _, p in ps.PRINCIPLES],
            [p for _, p in ps.PROHIBITED_RESCUES],
            [p for _, p in ps.COMPLEX_ML_NOT_AUTHORISED],
            [p for _, p in ps.TAIL_DIAGNOSTICS],
            [p for _, p in ps.PAUSED_ACTIVITIES],
            [p for _, p in ps.CONTINUING_ACTIVITIES],
            [p for _, _, p in ps.RESUMPTION_CONDITIONS],
        )
        for labels in tables:
            assert set(labels) <= set(ps.PROVENANCE)


class TestWhatTheRecordMayNotSay:
    def test_nothing_is_claimed_about_fx_or_alpha(self, document: str) -> None:
        assert ps.NOT_CLAIMED == ("FX_HAS_NO_EDGE", "ALPHA_SUPPORTED")
        assert "**`FX_HAS_NO_EDGE` ではない。**" in document
        assert "**`ALPHA_SUPPORTED` とはしない。**" in document
        for claim in ("FX spot に edge は無い", "alpha として扱える", "ALPHA_SUPPORTED である"):
            assert claim not in document

    def test_the_next_work_is_not_a_research_step(self, document: str) -> None:
        section = _section(document, "## 1. 裁定と status", "## 2.")
        assert "次の作業は新しい alpha 探索ではない。" in section
        for next_step in ("次は", "次に進む", "Track 3 に進む", "paper-forward を開始"):
            assert next_step not in section

    def test_the_record_is_a_constraint_not_scratch_or_evidence(self, document: str) -> None:
        header = document.split("## 0.", 1)[0]
        assert "RESEARCH_SCRATCH_NON_AUTHORITATIVE" not in header
        assert "**Track A の研究出力ではない。**" in document
        assert "GO・候補・edge の証拠として引用するのではない" in document

    def test_the_truncated_word_is_not_guessed_as_ruled(self) -> None:
        temporal = next(p for text, p in ps.TAIL_DIAGNOSTICS if "temporal co" in text)
        assert temporal == "起草"
        assert not any("temporal concentration" in text for text, _ in ps.TAIL_DIAGNOSTICS)

    def test_the_tail_demotion_is_recorded_as_a_recommendation(self, document: str) -> None:
        tail = next(p for key, _, p in ps.STATUSES if key == "tail_policy_prospective")
        assert tail == "裁定（推奨）"
        assert "降格することを推奨**した" in document
        assert "tail 条項で閉じた family（H-021 COT、H-022 Track A など）を再び開かない" in document

    def test_the_lottery_gap_stays_an_open_decision(self, document: str) -> None:
        decisions = document.split("## 13.", 1)[1]
        assert "tail kill の見逃し（高 Sharpe の lottery 型 book）を受け入れるか" in decisions
        assert "§8 の降格はこれを解消しない" in decisions
        assert "判断は不要" not in document

    def test_resumption_is_an_act_under_an_existing_rule(self, document: str) -> None:
        rc1 = next(row for row in ps.RESUMPTION_CONDITIONS if row[0] == "RC-1")
        assert rc1[2] == "既存規則"
        assert "条件がすべて揃ったことはそれに代わらない" in rc1[1]
        assert "RC-2〜RC-4 は**再開後の作業の順序**を定める" in document
        for cid in ("RC-2", "RC-3", "RC-4"):
            text = next(row[1] for row in ps.RESUMPTION_CONDITIONS if row[0] == cid)
            assert text.startswith("再開後の順序: ")

    def test_the_post_hoc_scope_is_the_whole_family(self, document: str) -> None:
        assert "**対象は通貨レベルの reversal family 全体**" in document
        entry = next(e for e in LEDGER if e["id"] == "H-024")
        assert "whole currency-level reversal family" in entry["status"]
        assert "any horizon" in entry["status"]

    def test_engineering_is_not_a_way_around_the_pause(self) -> None:
        paused = " ".join(text for text, _ in ps.PAUSED_ACTIVITIES)
        for loophole in ("volatility 予測器", "閉じた判定の net を再計算", "artefact を再分析"):
            assert loophole in paused
        assert "どちらでも" in paused


class TestTheLedger:
    def test_track_1_is_closed_with_its_accepted_status(self) -> None:
        entry = next(e for e in LEDGER if e["id"] == "H-023")
        assert entry["prespecified"] is True
        assert entry["status"].startswith("CLOSED")
        compact = entry["status"].replace(" ", "")
        assert ps.status("track_1_continuous_currency_portfolio") in compact
        assert "TURNOVER_REDUCTION_MECHANISM_SUPPORTED, not ALPHA_SUPPORTED" in entry["status"]
        assert "not FX_HAS_NO_EDGE" in entry["status"]

    def test_the_post_hoc_reversal_is_counted_and_not_a_candidate(self) -> None:
        entry = next(e for e in LEDGER if e["id"] == "H-024")
        assert entry["prespecified"] is False
        assert ps.status("post_hoc_currency_reversal_observation") in entry["status"]
        assert "re-pre-registering it is prohibited" in entry["status"]

    def test_the_document_counts_are_the_ledger_counts(self, document: str) -> None:
        counts = summary()
        line = (
            f"{counts['entries']} 件: CLOSED {counts['closed']}、OPEN {counts['open']}、"
            f"事前登録 {counts['prespecified']}、post-hoc {counts['post_hoc']}。"
        )
        assert line in document

    def test_every_ledger_row_carries_the_ledger_state(self, document: str) -> None:
        section = _section(document, "### 10.1", "**一時停止時点で OPEN")
        states = {}
        for row in _rows(section)[1:]:
            ident, _, state = (cell.strip() for cell in row.strip("|").split("|"))
            if "〜" in ident:
                first, last = (int(part.split("-")[1]) for part in ident.split("〜"))
                for number in range(first, last + 1):
                    states[f"H-{number:03d}"] = state
            else:
                states[ident] = state
        for entry in LEDGER:
            expected = "OPEN" if entry["status"].startswith("OPEN") else "CLOSED"
            assert states[entry["id"]] == expected, entry["id"]

    def test_the_open_entries_are_the_ledger_open_entries(self, document: str) -> None:
        open_ids = tuple(e["id"] for e in LEDGER if e["status"].startswith("OPEN"))
        assert open_ids == ps.OPEN_LEDGER_ENTRIES_AT_PAUSE
        listed = "、".join(open_ids)
        assert f"**一時停止時点で OPEN の 4 件（{listed}）**" in document
        assert "本記録は ledger の status 文を変更しない" in document


class TestTheSources:
    def test_every_phase_status_token_is_in_its_source_record(self, document: str) -> None:
        section = _section(document, "### 10.2", "**残った durable")
        for row in _rows(section)[1:]:
            pr = row.strip("|").split("|")[0].strip()
            tokens = re.findall(r"`([A-Z][A-Z0-9_]{10,})`", row)
            if pr == "#464":
                assert not tokens
                continue
            source = (ROOT / PHASE_SOURCES[pr]).read_text(encoding="utf-8")
            assert tokens, pr
            for token in tokens:
                assert token in source, (pr, token)

    def test_the_headline_verdicts_are_not_dropped(self, document: str) -> None:
        section = _section(document, "### 10.2", "**残った durable")
        for token in (
            "PRICE_PATH_STRUCTURE_REAL_BUT_NOT_ECONOMICALLY_HARVESTABLE",
            "ECONOMIC_EDGE_SOURCE_NOT_FOUND_EXOGENOUS_MOVEMENT_STRUCTURE_ESTABLISHED",
            "FEASIBILITY_GATE_V1_LEGACY_FROZEN",
            "TRACK_A_RESEARCH_PROGRAM_ROUND_B_PRIME_COMPLETED",
        ):
            assert f"`{token}`" in section

    def test_every_protected_span_row_is_the_authority(self, document: str) -> None:
        rows = _rows(_section(document, "### 10.3", "- 状態の文言は"))[1:]
        by_name = {row.strip("|").split("|")[0].strip().split(" ")[0]: row for row in rows}
        for name, block in PROTECTED_SPANS.items():
            key = name.replace("_", "_")
            row = next(r for label, r in by_name.items() if label.startswith(key))
            assert row.rstrip().endswith(f"| {block['status']} |"), name
        assert {n: b["status"] for n, b in PROTECTED_SPANS.items()} == ps.PROTECTED_DATA_AT_PAUSE

    def test_the_contamination_gap_is_disclosed(self, document: str) -> None:
        from scripts.research.model_learning import SEEN_SPANS

        runs = {h for block in SEEN_SPANS.values() for h in block["hypotheses_run_here"]}
        if "H-023" not in runs:
            assert "**汚染記録の抜け（開示）**" in document

    @pytest.mark.parametrize(("number", "sha"), sorted(ps.MERGES.items()))
    def test_every_merge_is_in_the_table(self, document: str, number: int, sha: str) -> None:
        row = next(line for line in document.splitlines() if line.startswith(f"| #{number} |"))
        assert row.rstrip().endswith(f"| `{sha}` |")

    def test_the_unmerged_research_pr_is_cited_for_nothing(self, document: str) -> None:
        assert ps.UNMERGED_RESEARCH_PRS == (473,)
        assert "**未 merge の研究 PR**: #473" in document
        assert "閉鎖としても開放としても扱わない" in document

    def test_the_track_1_numbers_are_the_recorded_ones(
        self, document: str, record: dict[str, Any]
    ) -> None:
        primary = record["primary"]["summary"]
        assert record["adjudication"]["case"] == ps.status("track_1_continuous_currency_portfolio")

        def minus(text: str) -> str:
            return text.replace("-", "−")

        for label, key in (("gross Sharpe", "gross_sharpe"), ("net Sharpe", "net_sharpe")):
            assert minus(f"| {label} | **{primary[key]:.2f}**（{primary[key]}） |") in document
        assert minus(f"約 {primary['net_annual_return'] * 100:.2f}%") in document
        assert f"約 {primary['realized_annual_vol'] * 100:.2f}%" in document
        assert f"約 {primary['cost_annual_drag'] * 100:.2f}%/年" in document
        turnover = primary["turnover_round_trips_per_year_per_unit_gross"]
        assert f"約 {turnover:.1f} round trip" in document
        assert minus(f"約 {primary['max_drawdown'] * 100:.0f}%") in document
        assert round(primary["share_of_folds_positive"] * 6) == 1
        assert "| 正の fold | 1 / 6 |" in document
        stressed = [
            record["diagnostics"][f"diag_cost_{m}"]["summary"]["net_sharpe"] for m in ("1_5x", "2x")
        ]
        assert minus(f"×1.5 で {stressed[0]}、×2 で {stressed[1]}") in document
        breadth = minus(
            f"GBP を除くと gross {primary['gross_pnl_without_best_currency'] * 100:.2f}%"
        ) + minus(f"、USD を除いても {primary['gross_pnl_without_usd'] * 100:.2f}%")
        assert primary["best_currency"] == "GBP"
        assert breadth in document
        share = primary["cost_annual_drag"] / -primary["net_annual_return"]
        assert f"コストは損失の約 {share:.0%}" in document
        correlation = record["adjudication"]["unfitted_rules"]["reversal_20d"]["pnl_correlation"]
        assert f"約 {correlation:.2f}" in document
        bundle = record["baseline_2_linear_no_bundle"]["summary"]
        band_only = record["diagnostics"]["diag_band_none"]["summary"]
        assert (
            f"約 {bundle['turnover_round_trips_per_year_per_unit_gross']:.1f}（bundle なし）→ "
            f"約 {turnover:.1f}"
        ) in document
        per_gross = band_only["turnover_round_trips_per_year_per_unit_gross"]
        assert f"band だけを外した診断では {per_gross:.1f}" in document


class TestTheGovernanceDocuments:
    def test_claude_md_carries_the_pause(self) -> None:
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        section = text.split("## FX spot active-alpha research is PAUSED", 1)[1].split("\n## ", 1)[
            0
        ]
        assert f"**`{ps.status('programme')}`**" in section
        assert "docs/research/m15_fx_spot_active_alpha_research_pause.md" in section
        assert "no new\nalpha hypothesis or pre-registration on **any** data" in section
        assert "no paper-forward, demo or live orders" in section
        assert '"Engineering" is not a way around this' in section
        assert (
            "Resuming is an **explicit Human + ChatGPT decision**, never a recorded state"
            in section
        )

    def test_the_older_next_stage_statements_are_superseded(self) -> None:
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.count("TRACK_A_READY_TO_BEGIN_EXPLORATORY_STRATEGY_RESEARCH") >= 2
        assert "**Superseded on 2026-09-14:** active-alpha" in text
        assert "Since 2026-09-14 that exploration is itself paused" in text
        playbook = (ROOT / "docs/governance/m15_audit_playbook.md").read_text(encoding="utf-8")
        assert "**superseded on 2026-09-14** by the pause row below" in playbook
        assert "| **FX spot active-alpha research paused** (2026-09-14) |" in playbook
        assert "**This overrides the Next stage row above**" in playbook
