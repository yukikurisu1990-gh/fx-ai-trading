"""Shared fixtures for Gate P1 PR-B.0 tests.

The ``guard_cleanup`` fixture guarantees that every guard is uninstalled after
each test even if the test installs guards directly, so monkey-patched global
state (os.environ wrappers, socket sentinels, write-allowlist) can never leak
into the pytest session and break unrelated tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._gate_p1_inspector.guards import bytecode as bytecode_guard
from scripts._gate_p1_inspector.guards import credentials as credentials_guard
from scripts._gate_p1_inspector.guards import filesystem as filesystem_guard
from scripts._gate_p1_inspector.guards import imports as imports_guard
from scripts._gate_p1_inspector.guards import network as network_guard
from scripts._gate_p1_inspector.guards import subprocess as subprocess_guard


@pytest.fixture(autouse=True)
def guard_cleanup():
    """Ensure all guards are uninstalled after each test."""
    yield
    for guard in (
        filesystem_guard,
        subprocess_guard,
        network_guard,
        credentials_guard,
        imports_guard,
        bytecode_guard,
    ):
        guard.uninstall()


_BASE_CANDLE = {
    "bid_o": 1.10000,
    "bid_h": 1.10010,
    "bid_l": 1.09990,
    "bid_c": 1.10005,
    "ask_o": 1.10002,
    "ask_h": 1.10012,
    "ask_l": 1.09992,
    "ask_c": 1.10007,
}


def _write_candle_file(
    data_dir: Path,
    pair: str,
    span_label: str,
    *,
    n_rows: int = 5,
    start_minute: int = 0,
    include_extra_key: bool = False,
    malformed: bool = False,
    missing_field: bool = False,
) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"candles_{pair}_M1_{span_label}_BA.jsonl"
    lines: list[str] = []
    for i in range(n_rows):
        minute = start_minute + i
        row = dict(_BASE_CANDLE)
        row["time"] = f"2024-01-01T{(minute // 60) % 24:02d}:{minute % 60:02d}:00.000000000Z"
        if include_extra_key:
            row["volume"] = 100 + i
        if missing_field:
            row.pop("bid_o", None)
        lines.append(json.dumps(row))
    if malformed:
        lines.append("{not valid json")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def write_candle_file():
    """Return a helper that writes one synthetic candle fixture file."""
    return _write_candle_file


@pytest.fixture
def write_full_universe():
    """Return a helper that writes a fixture file for every given pair."""

    def _writer(data_dir: Path, pairs: list[str], span_label: str, **kwargs) -> None:
        for idx, pair in enumerate(pairs):
            _write_candle_file(data_dir, pair, span_label, start_minute=idx, **kwargs)

    return _writer
