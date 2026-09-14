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
        assert (
            "tail 条項も発火して閉じた family（H-021 COT、H-022 Track A など）を再び開かない**"
            "（`裁定から導出`、RC-10）"
        ) in document

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

    def test_the_post_hoc_scope_says_what_was_stated_and_what_is_derived(
        self, document: str
    ) -> None:
        assert "5・20・60 日のどれでも、どの符号の組み合わせでも（Track 1 の結果記録が" in document
        assert "**それ以外の horizon に及ぶかは `裁定から導出` で、§13 の確認事項**" in document
        results = (ROOT / "docs/research/m15_track1_continuous_portfolio_results.md").read_text(
            encoding="utf-8"
        )
        assert "5・20・60 日のどれでも、どの符号の組み合わせでも" in results
        entry = next(e for e in LEDGER if e["id"] == "H-024")
        assert "at 5, 20 or 60 days in any sign combination" in entry["status"]
        assert "awaits Human + ChatGPT confirmation" in entry["status"]
        assert "or another" not in entry["status"]

    def test_the_resumption_rules_split_existing_from_derived(self) -> None:
        by_id = {cid: (text, prov) for cid, text, prov in ps.RESUMPTION_CONDITIONS}
        assert by_id["RC-1"][1] == "既存規則"
        assert "実データの読み取りや実行を伴う再開" in by_id["RC-1"][0]
        assert "仮説" not in by_id["RC-1"][0]
        assert by_id["RC-9"][1] == "裁定から導出"
        assert "読み取りを伴わない再開" in by_id["RC-9"][0]
        assert by_id["RC-8"][1] == "裁定（推奨）"
        assert "再び開かない" not in by_id["RC-8"][0]
        assert by_id["RC-10"][1] == "裁定から導出"
        assert "tail 条項も発火して閉じた family" in by_id["RC-10"][0]

    def test_pending_rows_bind_provisionally_and_never_widen(self, document: str) -> None:
        assert "確認されるまで**暫定的に拘束する**（厳しい方の読み）" in document
        assert "確認待ちの「停止しないもの」の行は、許可を**広げない**" in document
        assert any("市場データを使うかどうかを問わない" in text for text, _ in ps.PAUSED_ACTIVITIES)
        continuing = " ".join(text for text, _ in ps.CONTINUING_ACTIVITIES)
        assert "停止中の track の実装でもない" in continuing

    def test_engineering_is_not_a_way_around_the_pause(self) -> None:
        paused = " ".join(text for text, _ in ps.PAUSED_ACTIVITIES)
        for loophole in ("volatility 予測器", "閉じた判定の net を再計算", "artefact を再分析"):
            assert loophole in paused
        assert "どちらでも" in paused


class TestTheProseKeepsItsPolarity:
    """The rows are pinned by equality; the sentences around them are pinned here."""

    REQUIRED_SENTENCES: tuple[str, ...] = (
        "**コストだけが原因ではない。**",
        "標準誤差 約 0.58",
        "今回の Case C の判定は**変更しない**",
        "過去の事前登録・判定も**書き換えない**",
        "**再事前登録は禁止。**",
        "OPEN であることは再開の根拠にならない",
        "**どの条件も、それが記録上満たされたことだけでは再開にならない**",
        "#482 の base 追随 merge は tree hash が承認時と同一",
        "**正本として引用しない**",
        '"never read" / "pristine" は主張しない',
        "GO・候補・edge の証拠として引用するのではない",
        "この引用との関係は §13 で Human + ChatGPT の確認事項とする",
        "`NOT_STARTED_BASE_EDGE_REQUIRED`**。進まない。",
        "停止中は追求しない。",
        "確認されるまで**暫定的に拘束する**（厳しい方の読み）",
        "確認待ちの行が許可を広げることはない。",
    )
    FORBIDDEN_PHRASES: tuple[str, ...] = (
        "再開してよい",
        "追求してよい",
        "進めてよい",
        "条件付きで可",
        "変更しうる",
        "merge 済みで正本",
        "pristine である",
        "問題ない",
        "証拠には引用できる",
        "FX spot には edge が無い",
        "揃えば再開",
        "次は Track 3",
        "自動的に再開",
        "解除される",
        "救済は認める",
        "継続して検討できる",
        "ただし alpha",
        "untouched",
        "advisory",
    )

    @pytest.mark.parametrize("sentence", REQUIRED_SENTENCES)
    def test_a_required_sentence_is_present(self, document: str, sentence: str) -> None:
        assert sentence in document

    @pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
    def test_a_permissive_phrase_is_absent(self, document: str, phrase: str) -> None:
        assert phrase not in document

    def test_the_decision_list_is_complete(self, document: str) -> None:
        decisions = document.split("## 13.", 1)[1]
        items = re.findall(r"^(\d+)\. ", decisions, flags=re.MULTILINE)
        assert items == [str(n) for n in range(1, 10)]
        for needle in (
            "本 PR の merge 承認",
            "出典が `起草` と `裁定から導出` の項目の確定",
            "「temporal co…」の語の確定",
            "H-024 の範囲が 5・20・60 日以外の horizon に及ぶか",
            "`記録用` token",
            "#473",
            "lottery 型 book",
            "§8.11.2(1)",
            "H-011、H-015、H-018、H-019",
            "RC-7 について",
        ):
            assert needle in decisions


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


def _claude_section() -> str:
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    heading = "## FX spot active-alpha research is PAUSED"
    return " ".join(text.split(heading, 1)[1].split("\n## ", 1)[0].split())


class TestTheClaudeSectionPolarity:
    REQUIRED: tuple[str, ...] = (
        "This is **not** `FX_HAS_NO_EDGE`",
        "not `ALPHA_SUPPORTED`",
        "which bind provisionally, and none of which widens what is permitted",
        "no new alpha search",
        "pre-registration on **any** data, seen or new",
        "no alpha-seeking run",
        "no Track 3 overlay of #480",
        "no complex ML",
        "no fresh-pool or forward-epoch read",
        "no paper-forward, demo or live orders",
        "is never re-pre-registered",
        '"Engineering" is not a way around this',
        "with or without market data",
        "never a recorded state",
    )
    FORBIDDEN: tuple[str, ...] = (
        "reads are allowed",
        "is fine",
        "may continue",
        "may resume",
        "is `FX_HAS_NO_EDGE`",
        "are permitted",
        "advisory",
        "except",
    )

    @pytest.mark.parametrize("phrase", REQUIRED)
    def test_a_prohibition_is_present(self, phrase: str) -> None:
        assert phrase in _claude_section()

    @pytest.mark.parametrize("phrase", FORBIDDEN)
    def test_a_permission_is_absent(self, phrase: str) -> None:
        assert phrase not in _claude_section()


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
        row = next(
            line for line in playbook.splitlines() if "research paused** (2026-09-14)" in line
        )
        assert "exploration does **not** continue" in row
        assert "until an explicit Human + ChatGPT decision resumes it" in row
        assert "may continue" not in row and "continues" not in row
        assert "except" not in row and "proceeds" not in row
        flat = " ".join(text.split())
        assert "so this exploration does not continue until an explicit Human + ChatGPT" in flat
        assert "does continue" not in flat
        superseded = flat.split("**Superseded on 2026-09-14:**", 1)[1].split(".", 2)
        assert "except" not in superseded[0] + superseded[1]
