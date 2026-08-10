"""Contract §12.23 — canonical `YYYY-MM-DDTHH:MM:SSZ` emission (audit finding C-2).

The formatter existed from the first commit of this Work PR and had **zero
production callers**, so `datetime.isoformat()` — which yields `+00:00` — still
reached the emitted proof payload and the warm-up metadata. §12.23 says it
"must not reach any artifact", and no committed gate-3a artifact uses that
spelling: an automated cross-check comparing an emitted record against a
committed one would fail on honest evidence.

These tests pin the emission itself, not the existence of a formatter.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.m15_gate3a.no_overlap import assert_per_file_bounds
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_gate3a.timeutil import TimestampError, format_utc_z
from scripts.m15_gate3a.warmup import WarmupPolicy

CANONICAL = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
REPO_ROOT = Path(__file__).resolve().parents[2]


def _roster() -> list[dict[str, object]]:
    return [
        {
            "pair": pair,
            "filename": f"candles_{pair}_M15_365d_BA_DESIGN.jsonl",
            "sha256": f"{index:064x}",
            "ts_min_utc": "2025-04-25T00:00:00Z",
            "ts_max_utc": "2026-02-28T23:59:59Z",
        }
        for index, pair in enumerate(PAIRS_20)
    ]


def test_certified_spans_are_emitted_in_the_canonical_z_form() -> None:
    """`+00:00` must not reach the proof payload."""
    result = assert_per_file_bounds(_roster(), role="design", expected_count=20)
    spans = result["certified_spans"]
    assert len(spans) == len(PAIRS_20)  # non-vacuity: the loop below must run
    for span in spans:
        assert CANONICAL.match(span["ts_min_utc"]), span["ts_min_utc"]
        assert CANONICAL.match(span["ts_max_utc"]), span["ts_max_utc"]


def test_warmup_metadata_is_emitted_in_the_canonical_z_form() -> None:
    metadata = WarmupPolicy(w_bars=100, longest_feature_lookback_bars=50).as_metadata()
    assert CANONICAL.match(metadata["forward_floor_utc"]), metadata["forward_floor_utc"]


def test_the_emitted_form_matches_what_the_committed_artifacts_use() -> None:
    """The point of a canonical form: an emitted record and a committed one agree.

    The boundary constants in the committed proof artifact are the reference
    spelling. If emission drifted back to `+00:00`, a cross-artifact comparison
    would fail on honest evidence — which is how a reviewer learns to ignore it.
    """
    committed = json.loads(
        (REPO_ROOT / "artifacts" / "m15_gate3a" / "no_overlap_proof.json").read_text(
            encoding="utf-8"
        )
    )
    boundaries = committed["boundary_constants_utc"]
    assert boundaries, "non-vacuity: the committed artifact must declare boundaries"
    for value in boundaries.values():
        assert CANONICAL.match(value), value
    assert format_utc_z(datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC)) == boundaries["design_end"]


def test_a_sub_second_instant_is_refused_rather_than_truncated() -> None:
    """§12.23: refuse, never truncate — the RF-1 lesson applied to emission."""
    with pytest.raises(TimestampError, match="microsecond"):
        format_utc_z(datetime(2026, 2, 28, 23, 59, 59, 500_000, tzinfo=UTC))
