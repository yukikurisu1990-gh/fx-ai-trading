"""Every number in the Track 3 document must come from the Track 3 artifacts.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The same route this programme has been burned on twice: a figure transcribed
from a console line, or left behind by an estimator that was fixed afterwards.
The unit-audit document had **76** such disagreements in its first draft, none of
them typos, and none visible to any check that treats a document as prose.

So the tables are parsed. Each row is resolved to its place in `replay.json` or
`frontier.json` and every number in it must be one of that place's own values, to
the precision the document printed. The pair-distribution row is the exception
that proves the rule: its minimum, maximum and median are not stored anywhere, so
the test recomputes them from `by_pair` rather than accepting them.

It does not check prose — a sentence can still overstate a table, which is what
review roles are for. It closes the transcription route only.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/research/m15_track_3_execution_frontier.md"
PREREG = ROOT / "docs/research/m15_track_3_execution_prereg.md"
REPLAY = ROOT / "artifacts/research/execution_frontier/replay.json"
FRONTIER = ROOT / "artifacts/research/execution_frontier/frontier.json"

PANEL_OF = {
    "momentum": "momentum_2021_2023",
    "supplemental": "supplemental_2023_2025",
}

#: Document cell label -> artifact cell key, for the frontier comparison table.
CELL_OF = {
    "london_open pre · month-end": "clock:london_open_pre__month_end",
    "ny_option_cut pre · month-end": "clock:ny_option_cut_pre__month_end",
    "london_fix pre · month-end": "clock:london_fix_pre__month_end",
    "calendar 1d": "calendar:1d",
}

#: Document row label -> the field in `entry_leg` it reports, for the
#: adverse-selection table, whose rows are quantities and columns are panels.
DRIFT_ROWS = {
    "baseline leg cost bp": "baseline_leg_bp",
    "passive leg cost bp (`P2`)": "passive_leg_bp",
    "conditional leg cost bp (`P1`, 約定分のみ)": "conditional_leg_bp",
    "capture bp（`P2` の対クロス節約）": "capture_bp",
    "drift after a market order bp": "drift_baseline_bp",
    "drift after a market order, **約定した判断のみ** bp": "drift_baseline_on_filled_bp",
    "adverse selection bp": "adverse_selection_bp",
}

NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _skip_unless(path: Path, stage: str) -> None:
    if not path.exists():
        pytest.skip(
            f"{path.relative_to(ROOT)} not present; run "
            f"`python -m scripts.research.execution_frontier.driver {stage}`"
        )


@pytest.fixture(scope="module")
def replay() -> dict[str, Any]:
    _skip_unless(REPLAY, "replay")
    return json.loads(REPLAY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def frontier() -> dict[str, Any]:
    _skip_unless(FRONTIER, "frontier")
    return json.loads(FRONTIER.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def text() -> str:
    #: The document writes a typographic minus; the parser reads ASCII. Without
    #: this every negative figure would be silently read as positive and matched
    #: against the wrong sign.
    return DOCUMENT.read_text(encoding="utf-8").replace("−", "-")


def _values(node: Any) -> list[float]:
    out: list[float] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            out.append(float(value))

    walk(node)
    return out


def _matches(token: str, available: list[float]) -> bool:
    """Half a unit in the last place the *document* printed, never a fixed epsilon."""
    decimals = len(token.split(".")[1]) if "." in token else 0
    tolerance = 0.5 * 10**-decimals + 1e-9
    claimed = float(token)
    return any(abs(claimed - value) <= tolerance for value in available)


def _tables(document: str) -> list[tuple[str, list[list[str]]]]:
    tables: list[tuple[str, list[list[str]]]] = []
    heading = ""
    current: list[list[str]] = []
    for line in document.splitlines():
        if line.startswith("#"):
            if current:
                tables.append((heading, current))
                current = []
            heading = line.strip("# ").strip()
        elif line.startswith("|"):
            cells = [part.strip() for part in line.strip("|").split("|")]
            if cells and not (set(cells[0]) <= set("-: ") and cells[0]):
                current.append(cells)
        elif current:
            tables.append((heading, current))
            current = []
    if current:
        tables.append((heading, current))
    return tables


def _split(label: str) -> tuple[str, str | None]:
    """`"all_bars · momentum"` -> `("all_bars", "momentum_2021_2023")`."""
    parts = [part.strip() for part in label.replace("**", "").split("·")]
    if len(parts) >= 2 and parts[-1] in PANEL_OF:
        return " · ".join(parts[:-1]), PANEL_OF[parts[-1]]
    return label.replace("**", "").strip(), None


def _pair_stats(block: dict[str, Any]) -> list[float]:
    ratios = {pair: row["cost_ratio"] for pair, row in block["by_pair"].items()}
    values = list(ratios.values())
    return [
        float(len(values)),
        float(sum(1 for v in values if v > 1.0)),
        min(values),
        max(values),
        statistics.median(values),
    ]


def test_every_table_row_is_traceable_to_the_artifacts(
    replay: dict[str, Any], frontier: dict[str, Any], text: str
) -> None:
    checked = 0
    failures: list[str] = []

    def check(where: str, columns: list[str], available: list[float]) -> None:
        nonlocal checked
        for column in columns:
            for token in NUMBER.findall(column):
                if not _matches(token, available):
                    failures.append(f"{where}: {token} is not in the artifact")
                checked += 1

    for heading, rows in _tables(text):
        for cells in rows:
            label, panel = _split(cells[0])
            rest = cells[1:]

            if "主結果" in heading and panel:
                block = replay["panels"][panel]["populations"].get(label)
                if block is None:
                    failures.append(f"{heading}: no population {label!r}")
                    continue
                check(f"{heading} {cells[0]}", rest, _values(block))

            elif "感度軸" in heading and panel:
                block = replay["panels"][panel]["sensitivity"].get(label)
                if block is None:
                    failures.append(f"{heading}: no sensitivity cell {label!r}")
                    continue
                check(f"{heading} {cells[0]}", rest, _values(block))

            elif "ペア別分布" in heading and label in PANEL_OF:
                block = replay["panels"][PANEL_OF[label]]
                check(f"{heading} {cells[0]}", rest, _pair_stats(block))

            elif "Adverse-selection" in heading and cells[0] in DRIFT_ROWS:
                field = DRIFT_ROWS[cells[0]]
                #: `strict` on purpose: if the table gains or loses a panel column this
                #: must fail loudly rather than check the ones that still line up.
                for column, name in zip(rest, ("momentum", "supplemental"), strict=True):
                    entry = replay["panels"][PANEL_OF[name]]["populations"]["all_bars"]["entry_leg"]
                    check(f"{heading} {cells[0]} [{name}]", [column], [float(entry[field])])

            elif "design-feasible" in heading and label in frontier["feasibility"]:
                check(f"{heading} {label}", rest, _values(frontier["feasibility"][label]))

            elif "主要 cell" in heading and label in CELL_OF:
                variant, cell_panel = _split(rest[0])
                block = (
                    frontier["feasibility"].get(variant, {}).get("cells", {}).get(CELL_OF[label])
                )
                if block is None or cell_panel is None:
                    failures.append(f"{heading}: no {variant}/{CELL_OF[label]}")
                    continue
                check(
                    f"{heading} {cells[0]} {rest[0]}",
                    rest[1:],
                    _values(block["per_panel"][cell_panel]),
                )

    assert not failures, "\n".join(failures)
    #: A parser that matched nothing would pass vacuously.
    assert checked > 150, f"only {checked} figures were checked; the parser is not matching"


def test_the_identity_table_matches_the_measured_panels(
    replay: dict[str, Any], frontier: dict[str, Any], text: str
) -> None:
    for panel in PANEL_OF.values():
        block = replay["panels"][panel]
        assert f"{block['n_bars']:,}" in text
        assert f"{block['n_measurable']:,}" in text
        assert str(frontier["panels"]["quoted"][panel]["n_days"]) in text


def test_the_document_carries_the_statuses_the_stage_may_reach(text: str) -> None:
    for status in (
        "SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED",
        "OFFLINE_EXECUTION_FRONTIER_ESTIMATED",
        "CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER",
        "CLOCK_STRUCTURE_TRACK_V1_WITHDRAWN_AFTER_UNIT_CORRECTION",
    ):
        assert status in text


def test_the_prohibited_claim_appears_only_as_a_prohibition(text: str) -> None:
    """The one status this stage may not reach, in both documents.

    Present, because a reader has to be told it is excluded — but only ever in a
    sentence that excludes it. A future edit that drops the negation would leave
    the token in place and this is the check that notices.
    """
    prohibited = "BROKER_REALIZABLE_COST_REDUCTION_ESTABLISHED"
    for path in (DOCUMENT, PREREG):
        body = path.read_text(encoding="utf-8")
        for line in body.splitlines():
            if prohibited in line:
                assert ("しない" in line) or ("prohibited" in line.lower())


def test_the_unit_audit_passed_on_both_artifacts(
    replay: dict[str, Any], frontier: dict[str, Any]
) -> None:
    for artifact in (replay, frontier):
        assert artifact["unit_audit"]["status"] == "UNIT_CONSISTENCY_VERIFIED"
        assert artifact["unit_audit"]["numeric_fields_not_in_bp"] == []


def test_the_document_does_not_claim_track_2_or_m1_moved(text: str) -> None:
    """Both were held by the sequencing decision, and a results document is
    exactly where a held stage quietly acquires a result table."""
    assert "Track 2 status" in text
    assert "待機" in text
    assert "M1 status" in text
    assert "未使用" in text
