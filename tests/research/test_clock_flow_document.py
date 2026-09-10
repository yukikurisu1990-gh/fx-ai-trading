"""Every number in the unit-audit document must come from the artifact.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Why this exists
---------------

This programme has twice written a figure into a results document from a stale
console line, and the first draft of the document this test guards had **76**
numbers that disagreed with the run that produced them — not one of them a
typo. They were the residue of an estimator that had been fixed in between, and
they were invisible to every other check because a document is prose.

So the tables are parsed rather than trusted. For each row the test finds the
matching cell in `frontier.json` and requires every number in that row to be one
of that cell's own values, to the precision the document printed. A row that
cites a figure the artifact does not hold fails here, whichever of the two is
wrong.

It does not check prose. A sentence can still overstate what a table says, which
is what review roles are for; this only closes the transcription route.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/research/m15_fx_spot_frontier_unit_audit.md"
ARTIFACT = ROOT / "artifacts/research/clock_flow/frontier.json"

PANELS = ("momentum_2021_2023", "supplemental_2023_2025")

#: Document row label -> where that row lives in the artifact. The document
#: writes for a reader and the artifact for a machine, so the two spellings are
#: mapped once, here, rather than either being bent toward the other.
#:
#: Two maps, not one: §4.3's table reuses six of §4.1's labels for a different
#: subset of days, and a single dictionary silently kept only the second meaning
#: of each — which would have checked the all-days rows against the month-end
#: cells and passed, because the parser would never have noticed.
ALL_DAY_ROWS: dict[str, tuple[str, str]] = {
    "calendar 1d": ("calendar", "1d"),
    "calendar 1w": ("calendar", "1w"),
    "calendar 2w": ("calendar", "2w"),
    "calendar 1m": ("calendar", "1m"),
    "london_fix pre": ("clock", "london_fix_pre"),
    "london_fix post": ("clock", "london_fix_post"),
    "london_open pre": ("clock", "london_open_pre"),
    "london_open post": ("clock", "london_open_post"),
    "ny_option_cut pre": ("clock", "ny_option_cut_pre"),
    "ny_option_cut post": ("clock", "ny_option_cut_post"),
    "tokyo_fix pre": ("clock", "tokyo_fix_pre"),
    "tokyo_fix post": ("clock", "tokyo_fix_post"),
    "rollover pre": ("clock", "rollover_pre"),
    "rollover post": ("clock", "rollover_post"),
    "london_fix pre, every day": ("clock", "london_fix_pre"),
    "london_fix post, every day": ("clock", "london_fix_post"),
    "london_open pre, every day": ("clock", "london_open_pre"),
    "ny_option_cut post, every day": ("clock", "ny_option_cut_post"),
    "tokyo_fix pre, every day": ("clock", "tokyo_fix_pre"),
    "rollover pre, every day": ("clock", "rollover_pre"),
    "rollover post, every day": ("clock", "rollover_post"),
}

MONTH_END_ROWS: dict[str, tuple[str, str]] = {
    "london_open pre": ("clock", "london_open_pre__month_end"),
    "london_open post": ("clock", "london_open_post__month_end"),
    "london_fix pre": ("clock", "london_fix_pre__month_end"),
    "london_fix post": ("clock", "london_fix_post__month_end"),
    "ny_option_cut pre": ("clock", "ny_option_cut_pre__month_end"),
    "ny_option_cut post": ("clock", "ny_option_cut_post__month_end"),
    "tokyo_fix pre": ("clock", "tokyo_fix_pre__month_end"),
    "tokyo_fix post": ("clock", "tokyo_fix_post__month_end"),
}

assert set(MONTH_END_ROWS) <= set(ALL_DAY_ROWS), "a month-end row with no all-days twin"

NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


@pytest.fixture(scope="module")
def artifact() -> dict[str, Any]:
    if not ARTIFACT.exists():
        pytest.skip(
            f"{ARTIFACT.relative_to(ROOT)} not present; "
            "run `python -m scripts.research.clock_flow.driver frontier`"
        )
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _values_of(cell: dict[str, Any]) -> list[float]:
    """Every number the cell holds, flattened, including its economics."""
    out: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            out.append(float(node))

    walk(cell)
    return out


def _tables(text: str) -> list[tuple[str, list[str]]]:
    """`(section heading, table rows)` for every markdown table in the document."""
    tables: list[tuple[str, list[str]]] = []
    heading = ""
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current:
                tables.append((heading, current))
                current = []
            heading = line.strip("# ").strip()
        elif line.startswith("|"):
            current.append(line)
        elif current:
            tables.append((heading, current))
            current = []
    if current:
        tables.append((heading, current))
    return tables


def _matches(token: str, available: list[float]) -> bool:
    """Is the printed figure one of the cell's values, at the precision printed?

    The document rounds for a reader — `5.28` for `5.275`, `160` for `160.26` —
    so the tolerance is half a unit in the last place **the document showed**,
    never a fixed epsilon that would let a wrong number through on a big row.

    The precision has to come from the token as written. Taking it from the
    parsed float instead makes `160` into `160.0`, demands three digits of
    agreement from a figure that showed none, and rejects six correct rows.
    """
    decimals = len(token.split(".")[1]) if "." in token else 0
    tolerance = 0.5 * 10**-decimals + 1e-9
    claimed = float(token)
    return any(abs(claimed - value) <= tolerance for value in available)


def test_every_table_row_is_traceable_to_the_artifact(artifact: dict[str, Any]) -> None:
    text = DOCUMENT.read_text(encoding="utf-8")
    panels = artifact["panels"]
    checked = 0
    failures: list[str] = []

    for heading, rows in _tables(text):
        month_end = "selectivity" in heading.lower()
        for line in rows:
            cells = [part.strip() for part in line.strip("|").split("|")]
            if len(cells) < 2 or set(cells[0]) <= set("-: ") or not cells[0]:
                continue
            label = cells[0].replace("**", "").split("·")[0].strip()
            key = (MONTH_END_ROWS if month_end else ALL_DAY_ROWS).get(label)
            if key is None:
                continue
            group, name = key
            if any(name not in panels[panel][group] for panel in PANELS):
                failures.append(f"{heading!r} row {label!r}: no cell {group}/{name}")
                continue
            available = {panel: _values_of(panels[panel][group][name]) for panel in PANELS}
            for column in cells[1:]:
                for token in NUMBER.findall(column):
                    if not any(_matches(token, values) for values in available.values()):
                        failures.append(
                            f"{heading!r} row {label!r}: {token} is in neither panel's "
                            f"{group}/{name}"
                        )
                    checked += 1

    assert not failures, "\n".join(failures)
    #: A parser that silently matched nothing would pass vacuously.
    assert checked > 150, f"only {checked} figures were checked; the parser is not matching"


def test_the_document_reports_the_status_the_artifact_carries(artifact: dict[str, Any]) -> None:
    text = DOCUMENT.read_text(encoding="utf-8")
    assert artifact["unit_audit"]["status"] in text
    assert artifact["unit_audit"]["numeric_fields_not_in_bp"] == []


def test_the_document_does_not_claim_the_research_started(artifact: dict[str, Any]) -> None:
    """§1 of the decision stops the tracks if the frontier's conclusion moved.

    It did, so the document must say the hypothesis stages did not run — and must
    not have quietly acquired a result table while saying so.
    """
    _ = artifact
    text = DOCUMENT.read_text(encoding="utf-8")
    assert "PRIOR_FRONTIER_CONCLUSION_CHANGED_RESEARCH_NOT_STARTED" in text
    assert "not started" in text


def test_the_panels_are_the_two_seen_deciding_spans(artifact: dict[str, Any]) -> None:
    """No read outside the two already-seen panels reached this artifact."""
    measured = artifact["measured_spans"]
    assert measured["momentum_2021_2023"][0].startswith("2021-04-26")
    assert measured["momentum_2021_2023"][1].startswith("2025-") is False
    assert measured["momentum_2021_2023"][1].startswith("2023-04-25")
    assert measured["supplemental_2023_2025"][0].startswith("2023-04-26")
    assert measured["supplemental_2023_2025"][1].startswith("2025-04-24")
    assert set(artifact["panels"]) == set(PANELS)


def _survivors(artifact: dict[str, Any], ir_max: float) -> list[str]:
    """Cells powered on **both** deciding panels and payable at `ir_max`."""
    keep: list[str] = []
    for group in ("calendar", "clock"):
        for name, first in artifact["panels"][PANELS[0]][group].items():
            second = artifact["panels"][PANELS[1]][group].get(name)
            if second is None or min(first.get("n_events", 0), second.get("n_events", 0)) < 2:
                continue
            if not (first["decidable"] and second["decidable"]):
                continue
            worst = max(
                first["economics"]["break_even_gross_ir"],
                second["economics"]["break_even_gross_ir"],
            )
            if worst <= ir_max:
                keep.append(name)
    return sorted(keep)


def test_how_much_survives_both_gates(artifact: dict[str, Any]) -> None:
    """The document's headline, pinned — because it was wrong once.

    A first draft said five cells survive at `IR_max = 2.0`. One does. Raising
    the ceiling admits no second cell, because the next candidates fail the
    *power* gate on one panel rather than the economic one, and a claim that
    loosening `IR_max` opens the space would have pointed a re-decision the wrong
    way.
    """
    assert _survivors(artifact, 1.0) == []
    assert _survivors(artifact, 1.5) == ["london_open_pre__month_end"]
    assert _survivors(artifact, 2.0) == ["london_open_pre__month_end"]


def test_the_survivor_passes_by_the_margin_the_document_states(
    artifact: dict[str, Any],
) -> None:
    margins = [
        artifact["panels"][panel]["clock"]["london_open_pre__month_end"]["headroom_bp"]
        for panel in PANELS
    ]
    assert margins == pytest.approx([0.196, 0.086], abs=0.0006)
    #: Three per cent and one and a half of the hurdle it clears.
    for margin, panel in zip(margins, PANELS, strict=True):
        hurdle = artifact["panels"][panel]["clock"]["london_open_pre__month_end"]["hurdle_bp"]
        assert 0.01 < margin / hurdle < 0.04


def test_the_measured_cell_count_the_document_cites(artifact: dict[str, Any]) -> None:
    measured = sum(
        1
        for group in ("calendar", "clock")
        for value in artifact["panels"][PANELS[0]][group].values()
        if value.get("n_events", 0) >= 2
    )
    assert measured == 34
    assert "thirty-four measured" in DOCUMENT.read_text(encoding="utf-8")
