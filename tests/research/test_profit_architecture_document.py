"""Every number in the redesign document must trace to the artifact.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The sixth time this check has earned its place. It also carries the claims a
table cannot: that the gate audit reopens no verdict, that the one development
observation is never cited without its non-evidence label, and that the final
recommendation states the confirmation bottleneck rather than hiding it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/research/m15_profit_architecture_redesign.md"
ARTIFACT = ROOT / "artifacts/research/profit_architecture/redesign.json"


@pytest.fixture(scope="module")
def artifact() -> dict[str, Any]:
    if not ARTIFACT.exists():
        pytest.skip("run `python -m scripts.research.profit_architecture.driver redesign`")
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
        elif isinstance(value, str):
            for token in re.findall(r"-?\d+(?:\.\d+)?", value):
                out.append(float(token))

    walk(node)
    return out


def _matches(token: str, available: list[float]) -> bool:
    decimals = len(token.split(".")[1]) if "." in token else 0
    tolerance = 0.5 * 10**-decimals + 1e-9
    return any(abs(float(token) - value) <= tolerance for value in available)


def test_the_turnover_law_table_traces(artifact: dict[str, Any], text: str) -> None:
    available = _values(artifact["turnover_law"])
    for needle in ("175.2", "125.4", "65.9", "48.0", "34.5", "20.2"):
        assert needle in text, needle
        assert _matches(needle, available), needle


def test_the_band_table_traces(artifact: dict[str, Any], text: str) -> None:
    available = _values(artifact["no_trade_band"])
    for needle in ("23.1", "14.4", "10.0", "117.5", "78.5", "49.0", "34.1"):
        assert needle in text, needle
        assert _matches(needle, available), needle


def test_the_capacity_table_traces(artifact: dict[str, Any], text: str) -> None:
    available = _values(artifact["capacity"])
    for needle in ("0.33", "0.11", "0.83", "0.61", "2.65", "2.12"):
        assert _matches(needle, available), needle


def test_the_cost_audit_traces(artifact: dict[str, Any], text: str) -> None:
    block = artifact["prediction_vs_turnover"]
    assert "6.87" in text
    assert block["overstatement_factor_for_the_smooth_book"] == pytest.approx(6.87)
    assert "858.3" in text or "858 " in text.replace("858.3", "858 ")
    assert "125.0" in text or "125 " in text


def test_the_power_numbers_trace(artifact: dict[str, Any], text: str) -> None:
    power = artifact["confirmation_power"]
    assert power["rows"]["fresh_pool_one_shot"]["power_at_true_net_ir"]["0.5"] == (
        pytest.approx(0.295, abs=0.001)
    )
    assert "29.5%" in text
    assert "24.7" in text
    assert power["years_for_80_percent_power"]["0.5"] == pytest.approx(24.7, abs=0.3)


def test_the_gate_audit_reopens_nothing_and_the_document_says_so(
    artifact: dict[str, Any], text: str
) -> None:
    assert artifact["gate_audit"]["verdicts_reopened_by_this_audit"] == []
    assert "どの verdict も再開しない" in text


def test_the_development_observation_is_always_labeled_non_evidence(text: str) -> None:
    """⭐ The one direct observation must never appear as support."""
    for position in [match.start() for match in re.finditer(r"\+0\.55", text)]:
        window = text[max(0, position - 300) : position + 300]
        assert "非証拠" in window or "non-evidence" in window.lower(), (
            "the +0.55 observation appears without its non-evidence label"
        )


def test_the_recommendation_is_conditional_and_names_the_condition(text: str) -> None:
    section = text.split("## Y.")[1]
    assert "条件付き YES" in section
    assert "24.7" in section and "27.8" in section
    assert "29.5%" in section
    assert "人間の判断" in section


def test_the_candidate_table_matches_the_artifact(artifact: dict[str, Any], text: str) -> None:
    by_id = {row["candidate_id"]: row for row in artifact["ranking"]}
    assert len(by_id) == 20
    for line in text.splitlines():
        if not line.startswith("| A") or line.count("|") < 5:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        prefix = cells[1].split()[0] if cells[0].strip().isdigit() else cells[0].split()[0]
        full = next((cid for cid in by_id if cid.startswith(prefix)), None)
        if full is None:
            continue
        assert cells[-1] == str(by_id[full]["score"]), f"{prefix}: score mismatch"


def test_the_selected_tracks_match(artifact: dict[str, Any], text: str) -> None:
    tracks = artifact["selected_tracks"]
    assert tracks["track_1_core"]["candidate_id"] == "A01_continuous_currency_portfolio"
    assert tracks["track_3_overlay"]["candidate_id"] == "A04_core_plus_event_overlay"
    assert "Track 1" in text and "Track 2" in text and "Track 3" in text
    for member in tracks["track_2_efficiency_bundle"]["members"]:
        assert member.split("_")[0] in text


def test_the_artifact_is_signal_free(artifact: dict[str, Any]) -> None:
    assert artifact["signal_free"] is True
    assert artifact["market_data_read"] is False
    assert artifact["protected_spans_read"] is False
