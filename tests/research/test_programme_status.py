"""The pause record, its machine-readable copy, the ledger and the Track 1 record agree.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Reads committed documents and artefacts only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.research import programme_status as status
from scripts.research.round_a.ledger import LEDGER, summary

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/research/m15_fx_spot_active_alpha_research_pause.md"
TRACK_1_RECORD = ROOT / "artifacts/research/continuous_portfolio/development.json"


@pytest.fixture(scope="module")
def document() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    return json.loads(TRACK_1_RECORD.read_text(encoding="utf-8"))


def _ledger(entry_id: str) -> dict[str, Any]:
    return next(entry for entry in LEDGER if entry["id"] == entry_id)


class TestTheProgrammeState:
    def test_the_programme_is_paused_and_says_so(self, document: str) -> None:
        assert status.active_alpha_research_paused()
        assert f"Status: **`{status.PROGRAMME_STATUS}`**" in document

    def test_what_is_not_claimed_is_written_as_not_claimed(self, document: str) -> None:
        assert status.NOT_CLAIMED == ("FX_HAS_NO_EDGE", "ALPHA_SUPPORTED")
        assert "**`FX_HAS_NO_EDGE` ではない。**" in document
        assert "**`ALPHA_SUPPORTED` とはしない。**" in document

    @pytest.mark.parametrize("name", sorted(status.STATUSES))
    def test_every_ruled_status_is_in_the_document(self, document: str, name: str) -> None:
        assert f"**`{status.STATUSES[name]}`**" in document

    @pytest.mark.parametrize("principle", status.PRINCIPLES)
    def test_every_principle_is_in_the_document(self, document: str, principle: str) -> None:
        assert f"**`{principle}`**" in document

    def test_the_tail_policy_is_prospective(self, document: str) -> None:
        assert f"**`{status.TAIL_POLICY}`**（prospective のみ）" in document
        assert "過去の事前登録・判定も**書き換えない**" in document
        assert "prospective only" in status.TAIL_POLICY_SCOPE

    def test_the_rescues_the_decision_names_are_prohibited(self, document: str) -> None:
        for rescue in status.PROHIBITED_RESCUES[:4]:
            assert rescue in status.PROHIBITED_RESCUES
        named = "event filter、volatility filter、regime filter、horizon 変更"
        assert f"**禁止**（救済としての使用）: {named}" in document
        assert "**再事前登録は禁止。**" in document


class TestDraftedVersusRuled:
    def test_the_truncation_is_disclosed(self, document: str) -> None:
        assert '"temporal co"' in document
        assert "Human + ChatGPT の確認で確定する" in document

    def test_the_tail_diagnostics_carry_their_provenance(self, document: str) -> None:
        drafted = [name for name, kind in status.TAIL_DIAGNOSTICS if kind == "drafted"]
        ruled = [name for name, kind in status.TAIL_DIAGNOSTICS if kind.startswith("ruled")]
        section = document.split("## 9. Tail diagnostics")[1].split("## 10.")[0]
        assert section.count("| 起草 |") == len(drafted) == 4
        assert section.count("| 裁定") == len(ruled) == 6

    @pytest.mark.parametrize(("condition_id", "text", "kind"), status.RESUMPTION_CONDITIONS)
    def test_every_resumption_condition_is_in_the_table_with_its_provenance(
        self, document: str, condition_id: str, text: str, kind: str
    ) -> None:
        section = document.split("## 12. 再開条件")[1].split("## 13.")[0]
        row = next(line for line in section.splitlines() if line.startswith(f"| {condition_id} |"))
        expected = "裁定" if kind == "ruled" else "起草"
        assert row.rstrip().endswith(f"| {expected} |")

    def test_the_drafted_conditions_are_the_ones_sent_back_for_confirmation(
        self, document: str
    ) -> None:
        drafted = [cid for cid, _, kind in status.RESUMPTION_CONDITIONS if kind == "drafted"]
        assert drafted == ["RC-1", "RC-5", "RC-6", "RC-7"]
        assert "（RC-1、RC-5、RC-6、RC-7）" in document


class TestTheLedger:
    def test_track_1_is_closed_with_its_accepted_status(self) -> None:
        entry = _ledger("H-023")
        assert entry["prespecified"] is True
        assert entry["status"].startswith("CLOSED")
        compact = entry["status"].replace(" ", "")
        assert status.STATUSES["track_1_continuous_currency_portfolio"] in compact
        assert "TURNOVER_REDUCTION_MECHANISM_SUPPORTED, not ALPHA_SUPPORTED" in entry["status"]
        assert "not FX_HAS_NO_EDGE" in entry["status"]

    def test_the_post_hoc_reversal_is_counted_and_not_a_candidate(self) -> None:
        entry = _ledger("H-024")
        assert entry["prespecified"] is False
        assert status.STATUSES["post_hoc_currency_reversal_observation"] in entry["status"]
        assert "re-pre-registering it is prohibited" in entry["status"]

    def test_the_open_entries_are_the_ones_frozen_at_the_pause(self, document: str) -> None:
        open_ids = tuple(e["id"] for e in LEDGER if e["status"].startswith("OPEN"))
        assert open_ids == status.OPEN_LEDGER_ENTRIES_FROZEN_AT_PAUSE
        frozen = "、".join(status.OPEN_LEDGER_ENTRIES_FROZEN_AT_PAUSE)
        assert f"**OPEN の 4 件（{frozen}）は一時停止時点の状態で凍結する**" in document

    def test_the_document_counts_are_the_ledger_counts(self, document: str) -> None:
        counts = summary()
        line = (
            f"{counts['entries']} 件: CLOSED {counts['closed']}、OPEN {counts['open']}、"
            f"事前登録 {counts['prespecified']}、post-hoc {counts['post_hoc']}。"
        )
        assert line in document

    def test_every_ledger_id_appears_in_the_document(self, document: str) -> None:
        section = document.split("### 10.1")[1].split("### 10.2")[0]
        for entry in LEDGER:
            number = int(entry["id"].split("-")[1])
            covered = entry["id"] in section or (number <= 4 and "H-001〜H-004" in section)
            assert covered, entry["id"]


class TestTheRecords:
    @pytest.mark.parametrize(("number", "sha"), sorted(status.MERGES.items()))
    def test_every_merge_is_in_the_table(self, document: str, number: int, sha: str) -> None:
        row = next(line for line in document.splitlines() if line.startswith(f"| #{number} |"))
        assert row.rstrip().endswith(f"| `{sha}` |")

    def test_the_unmerged_research_pr_is_not_cited_as_authority(self, document: str) -> None:
        assert set(status.UNMERGED_RESEARCH_PRS) == {473}
        assert "**未 merge の研究 PR**: #473" in document
        assert "**正本として引用しない**" in document

    def test_the_track_1_numbers_are_the_recorded_ones(
        self, document: str, record: dict[str, Any]
    ) -> None:
        primary = record["primary"]["summary"]
        assert (
            record["adjudication"]["case"]
            == status.STATUSES["track_1_continuous_currency_portfolio"]
        )
        for label, key in (("gross Sharpe", "gross_sharpe"), ("net Sharpe", "net_sharpe")):
            row = f"| {label} | **{primary[key]:.2f}**（{primary[key]}） |"
            assert row.replace("-", "−") in document
        assert f"約 {primary['net_annual_return'] * 100:.2f}%".replace("-", "−") in document
        assert f"約 {primary['realized_annual_vol'] * 100:.2f}%" in document
        assert f"約 {primary['cost_annual_drag'] * 100:.2f}%/年" in document
        turnover = primary["turnover_round_trips_per_year_per_unit_gross"]
        assert f"約 {turnover:.1f} round trip" in document
        assert f"約 {primary['max_drawdown'] * 100:.0f}%".replace("-", "−") in document
        folds = primary["share_of_folds_positive"]
        assert round(folds * 6) == 1 and "| 正の fold | 1 / 6 |" in document
        correlation = record["adjudication"]["unfitted_rules"]["reversal_20d"]["pnl_correlation"]
        assert f"約 {correlation:.2f}" in document
        bundle = record["baseline_2_linear_no_bundle"]["summary"][
            "turnover_round_trips_per_year_per_unit_gross"
        ]
        assert f"約 {bundle:.1f}（bundle なし）→ 約 {turnover:.1f}" in document

    def test_the_protected_data_statuses_are_copied_not_restated(self, document: str) -> None:
        section = document.split("### 10.3")[1].split("## 11.")[0]
        assert status.PROTECTED_DATA_AT_PAUSE["historical_oos"] in section
        assert "never read" not in section.split("historical OOS")[1].split("\n")[0].replace(
            '"never read"', ""
        )
        for name in ("fresh_pool", "dead_window", "forward_epoch"):
            assert status.PROTECTED_DATA_AT_PAUSE[name] == "never read"
