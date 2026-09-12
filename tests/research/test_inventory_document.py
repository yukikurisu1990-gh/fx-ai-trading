"""Every number in the inventory document must come from the inventory artifact.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The fifth time this check has earned its place. It also carries two claims the
document makes that a table cannot: that no candidate is GREEN, and that the
document never proposes a next track it has not qualified.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/research/m15_decision_grade_research_inventory.md"
ARTIFACT = ROOT / "artifacts/research/feasibility/inventory.json"
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


@pytest.fixture(scope="module")
def artifact() -> dict[str, Any]:
    if not ARTIFACT.exists():
        pytest.skip("run `python -m scripts.research.feasibility.driver inventory`")
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def text() -> str:
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
    decimals = len(token.split(".")[1]) if "." in token else 0
    tolerance = 0.5 * 10**-decimals + 1e-9
    return any(abs(float(token) - value) <= tolerance for value in available)


def test_every_candidate_row_is_traceable(artifact: dict[str, Any], text: str) -> None:
    by_id = {block["candidate_id"]: block for block in artifact["candidates"]}
    prefixes = {cid.split("_")[0]: cid for cid in by_id}
    checked = 0
    failures: list[str] = []
    for line in text.splitlines():
        if not line.startswith("| C"):
            continue
        cells = [part.strip() for part in line.strip("|").split("|")]
        prefix = cells[0].split()[0]
        if prefix not in prefixes:
            continue
        #: A closed or blocked row carries em-dashes where the figures would be,
        #: and prose in its reason column. There is nothing to trace, and parsing
        #: "Track 1 suspended" as the number one would be a false failure.
        if cells[2].strip() in {"—", "-", ""}:
            continue
        available = _values(by_id[prefixes[prefix]])
        for column in cells[1:]:
            for token in NUMBER.findall(column):
                if not _matches(token, available):
                    failures.append(f"{prefix}: {token} is not in the artifact")
                checked += 1
    assert not failures, "\n".join(failures)
    assert checked > 40, f"only {checked} figures checked; the parser is not matching"


def test_the_horizon_table_is_traceable(artifact: dict[str, Any], text: str) -> None:
    available = _values(artifact["horizon_counterfactuals"])
    for needle in ("1.996", "2.337", "4.786", "6.977", "2.303", "4.674", "9.572", "3.992"):
        assert needle in text
        assert _matches(needle, available), needle


def test_the_document_reports_the_status_the_artifact_carries(
    artifact: dict[str, Any], text: str
) -> None:
    assert artifact["status"] in text
    assert "ADDITIONAL_INDEPENDENT_HISTORY_WOULD_OPEN_PASS_REGION" in text
    assert artifact["additional_history_would_open_a_pass_region"] is True


def test_no_green_candidate_is_claimed(artifact: dict[str, Any], text: str) -> None:
    assert "PASS_REGION_EXISTS" not in artifact["by_verdict"]
    assert "### GREEN candidates\n\n**なし。**" in text
    assert "### AMBER candidates\n\n**なし。**" in text


def test_the_document_proposes_no_next_track(text: str) -> None:
    """GREEN is zero, so a suggested track would be a track nobody qualified."""
    section = text.split("## 12. Suggested next tracks")[1]
    assert section.strip().startswith("**なし。**")


def test_the_counts_match(artifact: dict[str, Any], text: str) -> None:
    counts = {name: len(ids) for name, ids in artifact["by_verdict"].items()}
    assert counts["NO_DECISION_GRADE_PASS_REGION"] == 14
    assert counts["DATA_INTEGRITY_BLOCKED"] == 2
    assert counts["PRIOR_FAMILY_CLOSED"] == 6
    normalised = " ".join(text.split())
    assert "RED 14 / BLOCKED 2 / CLOSED 6 / AMBER 0 / GREEN 0" in normalised
