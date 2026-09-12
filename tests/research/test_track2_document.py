"""Every number in the Track 2 document must come from the Track 2 artifacts.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The same transcription route this programme has been burned on four times. The
tables are parsed and every figure resolved to its place in `stage0.json` or
`stage1.json`; a row citing something the artifact does not hold fails here,
whichever of the two is wrong.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/research/m15_track_2_non_usd_surprise_results.md"
STAGE0 = ROOT / "artifacts/research/track2/stage0.json"
STAGE1 = ROOT / "artifacts/research/track2/stage1.json"

PANEL_OF = {"momentum": "momentum_2021_2023", "supplemental": "supplemental_2023_2025"}
FAMILIES = ("employment", "inflation", "policy_rate")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _skip_unless(path: Path, stage: str) -> None:
    if not path.exists():
        pytest.skip(
            f"{path.relative_to(ROOT)} not present; run "
            f"`python -m scripts.research.track2.driver {stage}`"
        )


@pytest.fixture(scope="module")
def stage0() -> dict[str, Any]:
    _skip_unless(STAGE0, "stage0")
    return json.loads(STAGE0.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def stage1() -> dict[str, Any]:
    _skip_unless(STAGE1, "stage1")
    return json.loads(STAGE1.read_text(encoding="utf-8"))


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
    claimed = float(token)
    return any(abs(claimed - value) <= tolerance for value in available)


def _rows(document: str) -> list[list[str]]:
    out: list[list[str]] = []
    for line in document.splitlines():
        if not line.startswith("|"):
            continue
        cells = [part.strip() for part in line.strip("|").split("|")]
        if cells and cells[0] and not set(cells[0]) <= set("-: "):
            out.append(cells)
    return out


def _split(label: str) -> tuple[str, str | None]:
    parts = [part.strip() for part in label.replace("**", "").split("·")]
    if len(parts) == 2 and parts[1] in PANEL_OF:
        return parts[0], PANEL_OF[parts[1]]
    return label.replace("**", "").strip(), None


def test_every_table_row_is_traceable_to_the_artifacts(
    stage0: dict[str, Any], stage1: dict[str, Any], text: str
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

    fidelity = stage0["date_fidelity"]["per_currency"]
    for cells in _rows(text):
        label, panel = _split(cells[0])

        if label in fidelity and panel is None:
            check(f"date fidelity {label}", cells[1:], _values(fidelity[label]))

        elif label in FAMILIES and panel is not None:
            cell = stage1["panels"][panel]["families"][label]
            gate = stage1["gate_v2"][label]
            available = (
                _values(cell)
                + _values(gate["statistical"][panel])
                + _values(gate["economic"][panel])
            )
            check(f"{label} · {panel}", cells[1:], available)

        elif label in FAMILIES and panel is None:
            block = stage1["verdict"]["families"][label]
            check(f"verdict {label}", cells[1:], _values(block))

        elif label == "**pooled**" or label == "pooled":
            check("pooled", cells[1:], _values(stage0["date_fidelity"]))

    assert not failures, "\n".join(failures)
    assert checked > 90, f"only {checked} figures were checked; the parser is not matching"


def test_the_document_reports_the_status_the_artifact_carries(
    stage1: dict[str, Any], text: str
) -> None:
    assert stage1["verdict"]["status"] in text
    assert "NON_USD_SURPRISE_RELATIVE_CLOSED" in text  # named, and explicitly not claimed


def test_the_closed_status_is_only_ever_declined(text: str) -> None:
    """A future edit that drops the negation would leave the token in place."""
    for line in text.splitlines():
        if "NON_USD_SURPRISE_RELATIVE_CLOSED" in line:
            assert "主張しない" in line


def test_stage_0_passed_and_stage_1_did_not_claim_support(
    stage0: dict[str, Any], stage1: dict[str, Any]
) -> None:
    assert stage0["verdict"]["pass"] is True
    assert all(not block["supported"] for block in stage1["verdict"]["families"].values())


def test_the_offset_is_reported_as_unidentified(stage0: dict[str, Any], text: str) -> None:
    """The flat profile is the finding, and the document has to carry it.

    Within the unidentified band the score moves from 1.0 to 0.369, so a reader
    who takes the argmax for a measurement has been misled.
    """
    assert stage0["offset_estimation"]["separated_from_runner_up"] is False
    assert "separated_from_runner_up" in text or "平坦" in text


def test_stage_1_uses_the_offset_stage_0_validated(
    stage0: dict[str, Any], stage1: dict[str, Any]
) -> None:
    """The two constants that drifted apart in the first version.

    Stage 0 estimated hours and Stage 1 applied a calendar day; scoring the day
    through Stage 0's own scorer gives 0.369 against its 0.95 floor.
    """
    assert stage1["offset_hours_from_stage_0"] == stage0["date_fidelity"]["offset_hours_applied"]
    assert stage1["offset_hours_from_stage_0"] == stage0["offset_estimation"]["best_offset_hours"]


def test_the_partial_sessions_are_excluded_and_counted(stage1: dict[str, Any]) -> None:
    """Two thirds of a family used to enter into a three-hour Sunday session."""
    excluded = stage1["partial_days_excluded_per_panel"]
    for panel in PANEL_OF.values():
        assert excluded[panel] > 90


def test_the_impact_label_is_not_the_admission_rule(stage1: dict[str, Any]) -> None:
    """The pre-registration names it once, as a diagnostic."""
    for panel in PANEL_OF.values():
        for family in FAMILIES:
            cell = stage1["panels"][panel]["families"][family]
            if cell.get("n_events"):
                assert cell["n_high_impact"] <= cell["n_events"]
                assert "high_impact_diagnostic" in cell


def test_no_family_claims_the_hypothesised_sign(stage1: dict[str, Any]) -> None:
    """A family that moved the wrong way is dropped, never inverted."""
    for block in stage1["verdict"]["families"].values():
        assert block["checks"]["sign_is_the_hypothesised_one"] is False
        assert block["supported"] is False


def test_the_economic_gate_failed_on_every_cell(stage1: dict[str, Any]) -> None:
    """The claim §2.3 makes, checked rather than transcribed."""
    for family in FAMILIES:
        for block in stage1["gate_v2"][family]["economic"].values():
            assert block["pass"] is False
