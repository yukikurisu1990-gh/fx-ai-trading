"""Every number in the inventory document must come from the inventory artifact.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The fifth time this check has earned its place. It also carries claims the
document makes that a table cannot: that no candidate is GREEN, that the document
never proposes a next track it has not qualified, that it ranks nothing — and,
added after a review found the opposite written in the first draft — that it does
**not** claim a longer history would open a pass region, because per candidate it
would not.
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

#: The candidate table has six columns. A two-column review row whose first cell
#: happens to start with a candidate id is not one of its rows, and an earlier
#: version of this parser crashed on exactly that.
CANDIDATE_COLUMNS = 6


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
    seen: set[str] = set()
    failures: list[str] = []
    for line in text.splitlines():
        if not line.startswith("| C"):
            continue
        cells = [part.strip() for part in line.strip("|").split("|")]
        if len(cells) != CANDIDATE_COLUMNS:
            continue
        prefix = cells[0].split()[0]
        if prefix not in prefixes:
            continue
        seen.add(prefix)
        #: A closed, blocked or out-of-scope row carries em-dashes where the
        #: figures would be, and prose in its reason column. There is nothing to
        #: trace, and parsing "Track 1 suspended" as the number one would be a
        #: false failure.
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
    assert seen == set(prefixes), f"the table is missing {sorted(set(prefixes) - seen)}"


def test_the_horizon_table_is_traceable(artifact: dict[str, Any], text: str) -> None:
    available = _values(artifact["horizon_counterfactuals"])
    for needle in ("1.996", "2.337", "4.786", "6.977", "2.303", "4.674", "9.572", "3.992"):
        assert needle in text
        assert _matches(needle, available), needle


def test_the_per_candidate_year_figures_are_traceable(artifact: dict[str, Any], text: str) -> None:
    """⭐ The figures a reader would act on, rather than the headline.

    A review found the document quoting the `share = 1.0` shortfall as *the* gap
    while no catalogued candidate uses that assumption. The per-candidate table
    now has to trace as well.
    """
    available = _values(artifact["years_to_decision"])
    for needle in ("4.360", "8.721", "11.628", "23.256", "14.082", "28.163", "15.510", "31.020"):
        assert needle in text, needle
        assert _matches(needle, available), needle


def test_the_document_reports_the_status_the_artifact_carries(
    artifact: dict[str, Any], text: str
) -> None:
    assert artifact["status"] in text
    assert artifact["status"] == "CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED"


def test_the_document_does_not_claim_a_longer_history_opens_a_pass_region(
    artifact: dict[str, Any], text: str
) -> None:
    """The claim the first draft made, and the measurement that refuted it."""
    assert artifact["additional_history_would_open_a_pass_region"] is False
    assert artifact["additional_history_would_reach_only_marginal"] is True
    counterfactual = artifact["counterfactual_verdicts_per_candidate"]
    assert counterfactual["with_the_fresh_pool_split_in_two"]["n_pass_region_exists"] == 0
    assert counterfactual["with_the_fresh_pool_split_in_two"]["n_marginal"] == 1
    #: The document must say so where a reader meets the counterfactual, not only
    #: in the review section.
    horizon = text.split("## 8.")[1].split("## 9.")[0]
    assert "MARGINAL" in horizon
    assert "**0**" in horizon


def test_no_green_candidate_is_claimed(artifact: dict[str, Any], text: str) -> None:
    assert "PASS_REGION_EXISTS" not in artifact["by_verdict"]
    assert "MARGINAL_PASS_REGION" not in artifact["by_verdict"]
    assert "### GREEN candidates\n\n**なし。**" in text
    assert "### AMBER candidates\n\n**なし。**" in text


def test_the_document_proposes_no_next_track(text: str) -> None:
    """GREEN is zero, so a suggested track would be a track nobody qualified."""
    section = text.split("## 12. Suggested next tracks")[1]
    assert section.strip().startswith("**なし。**")


def test_the_document_ranks_nothing(text: str) -> None:
    """⭐ The first draft ranked three candidates on qualitative expected alpha.

    The decision forbids using any realised or anticipated signal quantity to
    select candidates, and none of the ranking criteria existed in the artifact.
    """
    section = text.split("## 11. Research ranking")[1].split("## 12.")[0]
    assert "**行わない。**" in section
    assert "削除した" in section


def test_the_counts_match(artifact: dict[str, Any], text: str) -> None:
    counts = {name: len(ids) for name, ids in artifact["by_verdict"].items()}
    assert counts["NO_DECISION_GRADE_PASS_REGION"] == 15
    assert counts["DATA_INTEGRITY_BLOCKED"] == 2
    assert counts["OUT_OF_GATE_SCOPE"] == 2
    assert counts["PRIOR_FAMILY_CLOSED"] == 3
    assert sum(counts.values()) == artifact["n_candidates"] == 22
    normalised = " ".join(text.split())
    assert "RED 15 / BLOCKED 2 / OUT_OF_GATE_SCOPE 2 / CLOSED 3" in normalised


def test_the_document_is_signal_free(artifact: dict[str, Any], text: str) -> None:
    """No realised quantity may be **reported**, in the artifact or in the tables.

    The scan is deliberately limited to the sections that carry results. The
    document is allowed — and required — to name the forbidden quantities where it
    states that it did not compute them, and a whole-document keyword scan would
    fail on that sentence, which is the one a reader most needs to find.
    """
    assert artifact["signal_free"] is True
    results = text.split("## 7.")[1].split("## 10.")[0].lower()
    for forbidden in ("sharpe", "information coefficient", "pnl", "p = 0.", "alpha"):
        assert forbidden not in results, forbidden
