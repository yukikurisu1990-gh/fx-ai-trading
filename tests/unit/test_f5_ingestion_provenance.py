"""Unit tests: F-5 ingestion-provenance hardening.

Status pins: F5_INGESTION_PROVENANCE_HARDENED_BY_TESTS /
F5_INVENTORIED_SPAN_OVERWRITE_GUARDED
(audit context: docs/design/project_wide_logic_audit_fable5_findings.md §4 F-5).

Covers:

- F5-A fetch truncation fail-closed: a mid-stream request failure raises
  ``FetchIncompleteError`` and ``main()`` exits non-zero.
- F5-B atomic write: candles stream into ``<output>.incomplete`` and are
  promoted to the final path only on fully-successful completion; a failed
  re-fetch never clobbers an existing final file.
- F5-C inventoried-span overwrite protection: ``provenance_guard`` fails
  closed when an output basename is referenced by committed inventory
  metadata, with an explicit override flag wired into
  ``fetch_oanda_candles`` and ``retrain_production_models``.
- F5-D archive resume safety: skip only on a valid, size-matching
  completion marker; existing-but-unmarked inventoried bytes are blocked.

All fetch clients are fakes (no network); inventory fixtures are synthetic
files under ``tmp_path`` except one explicitly read-only assertion against
the committed default roots.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

import scripts.fetch_oanda_archive as foa
import scripts.fetch_oanda_candles as foc
import scripts.provenance_guard as pg
import scripts.retrain_production_models as retrain
from scripts.fetch_oanda_candles import FetchIncompleteError, fetch_candles
from scripts.provenance_guard import (
    DEFAULT_INVENTORY_ROOTS,
    ProvenanceGuardError,
    assert_not_inventoried_span,
    find_inventory_references,
)

# ---------------------------------------------------------------------------
# fakes / fixtures
# ---------------------------------------------------------------------------


def _candle(time_str: str, *, price: float = 1.1) -> dict[str, Any]:
    return {
        "time": time_str,
        "complete": True,
        "mid": {
            "o": f"{price:.5f}",
            "h": f"{price + 0.0001:.5f}",
            "l": f"{price - 0.0001:.5f}",
            "c": f"{price + 0.00005:.5f}",
        },
        "volume": 17,
    }


class _PagesClient:
    """Returns queued pages in order; a queued Exception is raised instead.

    Once the queue is drained every further call returns an empty page (the
    fetcher then walks its cursor past ``end_time`` and terminates).
    """

    def __init__(self, pages: list[Any]) -> None:
        self._pages = list(pages)
        self.calls = 0

    def get_candles(self, instrument: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls += 1
        if not self._pages:
            return {"candles": []}
        item = self._pages.pop(0)
        if isinstance(item, Exception):
            raise item
        return {"candles": item}


@pytest.fixture
def synthetic_inventory_root(tmp_path: Path) -> Path:
    """A synthetic inventory root referencing one span basename, mirroring
    the committed metadata shape (filename / logical_file_id keys)."""
    root = tmp_path / "synthetic_inventory"
    root.mkdir()
    (root / "raw_inventory_9d_BA.json").write_text(
        json.dumps(
            {
                "candidate_id": "9d_BA",
                "files": [
                    {
                        "filename": "candles_EUR_USD_M1_9d_BA.jsonl",
                        "file_sha256": "0" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "t2_manifest.json").write_text(
        json.dumps(
            {
                "spans": [
                    {
                        "files": [
                            {
                                "logical_file_id": "candles_EUR_USD_M1_9d_BA.jsonl",
                                "sha256": "0" * 64,
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return root


@pytest.fixture
def empty_inventory_root(tmp_path: Path) -> Path:
    root = tmp_path / "empty_inventory"
    root.mkdir()
    return root


# ---------------------------------------------------------------------------
# F5-A / F5-B — fetch truncation fail-closed + atomic promotion
# ---------------------------------------------------------------------------


def test_fetch_failure_raises_and_leaves_only_incomplete(tmp_path: Path) -> None:
    output = tmp_path / "candles.jsonl"
    api = _PagesClient(
        pages=[
            [_candle("2026-04-23T20:00:00.000000000Z")],
            RuntimeError("boom mid-stream"),
        ]
    )

    with pytest.raises(FetchIncompleteError, match="boom mid-stream"):
        fetch_candles(
            instrument="EUR_USD",
            granularity="S5",
            days=1,
            output_path=output,
            api_client=api,
        )

    incomplete = tmp_path / "candles.jsonl.incomplete"
    assert not output.exists(), "truncated output must NOT be promoted to the final path"
    assert incomplete.exists()
    # Partial rows were retained under the .incomplete name only.
    assert len(incomplete.read_text(encoding="utf-8").splitlines()) == 1


def test_fetch_failure_main_exits_nonzero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "candles_not_inventoried.jsonl"
    monkeypatch.setattr(
        foc,
        "fetch_candles",
        MagicMock(side_effect=FetchIncompleteError("request failed")),
    )
    monkeypatch.setattr(foc, "assert_not_inventoried_span", MagicMock(return_value=[]))

    rc = foc.main(["--output", str(output)])

    assert rc != 0
    assert not output.exists()


def test_successful_fetch_promotes_final_file_without_incomplete_residue(tmp_path: Path) -> None:
    output = tmp_path / "candles.jsonl"
    api = _PagesClient(pages=[[_candle("2026-04-23T20:00:00.000000000Z")]])

    written = fetch_candles(
        instrument="EUR_USD",
        granularity="S5",
        days=1,
        output_path=output,
        api_client=api,
    )

    assert written == 1
    assert output.exists()
    assert not (tmp_path / "candles.jsonl.incomplete").exists()
    rec = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
    assert rec["time"] == "2026-04-23T20:00:00.000000000Z"


def test_failed_refetch_does_not_clobber_existing_final_file(tmp_path: Path) -> None:
    output = tmp_path / "candles.jsonl"
    output.write_text('{"time": "OLD"}\n', encoding="utf-8")
    api = _PagesClient(pages=[RuntimeError("boom")])

    with pytest.raises(FetchIncompleteError):
        fetch_candles(
            instrument="EUR_USD",
            granularity="S5",
            days=1,
            output_path=output,
            api_client=api,
        )

    # Atomicity: the pre-existing final bytes are untouched; the failed
    # attempt lives only under .incomplete.
    assert output.read_text(encoding="utf-8") == '{"time": "OLD"}\n'
    assert (tmp_path / "candles.jsonl.incomplete").exists()


# ---------------------------------------------------------------------------
# F5-D — archive resume safety (completion marker)
# ---------------------------------------------------------------------------


def _make_span_file(tmp_path: Path, name: str = "candles_ZZZ_TEST_M1_9d_BA.jsonl") -> Path:
    out = tmp_path / name
    out.write_text('{"time": "t1"}\n{"time": "t2"}\n', encoding="utf-8")
    return out


def test_archive_nonempty_file_without_marker_is_not_skipped(
    tmp_path: Path, empty_inventory_root: Path
) -> None:
    out = _make_span_file(tmp_path)

    action, _ = foa._resume_decision(out, inventory_roots=[empty_inventory_root])

    assert action == "fetch"


def test_archive_valid_marker_and_matching_size_is_skipped(
    tmp_path: Path, empty_inventory_root: Path
) -> None:
    out = _make_span_file(tmp_path)
    marker = foa._write_completion_marker(out, rows_written=2)

    assert marker.exists()
    meta = json.loads(marker.read_text(encoding="utf-8"))
    assert meta == {
        "rows_written": 2,
        "size_bytes": out.stat().st_size,
        "completed": True,
    }
    action, _ = foa._resume_decision(out, inventory_roots=[empty_inventory_root])
    assert action == "skip"


def test_archive_corrupted_marker_is_not_skipped(
    tmp_path: Path, empty_inventory_root: Path
) -> None:
    out = _make_span_file(tmp_path)
    foa._completion_marker_path(out).write_text("{not valid json", encoding="utf-8")

    action, _ = foa._resume_decision(out, inventory_roots=[empty_inventory_root])

    assert action == "fetch"


def test_archive_marker_size_mismatch_is_not_skipped(
    tmp_path: Path, empty_inventory_root: Path
) -> None:
    out = _make_span_file(tmp_path)
    foa._write_completion_marker(out, rows_written=2)
    with out.open("a", encoding="utf-8") as fh:
        fh.write('{"time": "t3"}\n')  # file grew after the marker was written

    action, _ = foa._resume_decision(out, inventory_roots=[empty_inventory_root])

    assert action == "fetch"


def test_archive_marker_completed_false_is_not_skipped(
    tmp_path: Path, empty_inventory_root: Path
) -> None:
    out = _make_span_file(tmp_path)
    foa._completion_marker_path(out).write_text(
        json.dumps({"rows_written": 2, "size_bytes": out.stat().st_size, "completed": False}),
        encoding="utf-8",
    )

    action, _ = foa._resume_decision(out, inventory_roots=[empty_inventory_root])

    assert action == "fetch"


def test_archive_unmarked_inventoried_bytes_are_blocked(
    tmp_path: Path, synthetic_inventory_root: Path
) -> None:
    out = _make_span_file(tmp_path, name="candles_EUR_USD_M1_9d_BA.jsonl")

    action, info = foa._resume_decision(out, inventory_roots=[synthetic_inventory_root])

    assert action == "blocked"
    assert info["inventory_references"]


def test_archive_missing_file_is_fetched(tmp_path: Path, empty_inventory_root: Path) -> None:
    out = tmp_path / "candles_ZZZ_TEST_M1_9d_BA.jsonl"

    action, _ = foa._resume_decision(out, inventory_roots=[empty_inventory_root])

    assert action == "fetch"


def test_archive_missing_inventoried_file_is_blocked(
    tmp_path: Path, synthetic_inventory_root: Path
) -> None:
    """A locally-deleted inventoried span must NOT be silently recreated:
    new bytes under a committed-SHA basename are the same identity
    re-point as an overwrite (review finding on F5-D)."""
    out = tmp_path / "candles_EUR_USD_M1_9d_BA.jsonl"
    assert not out.exists()

    action, info = foa._resume_decision(out, inventory_roots=[synthetic_inventory_root])

    assert action == "blocked"
    assert info["inventory_references"]


# ---------------------------------------------------------------------------
# F5-C — provenance guard core
# ---------------------------------------------------------------------------


def test_find_inventory_references_matches_synthetic_fixture(
    synthetic_inventory_root: Path,
) -> None:
    refs = find_inventory_references(
        "candles_EUR_USD_M1_9d_BA.jsonl", inventory_roots=[synthetic_inventory_root]
    )

    # Both synthetic metadata files (filename key + logical_file_id key) hit.
    assert len(refs) == 2
    assert all(str(synthetic_inventory_root) in r for r in refs)


def test_find_inventory_references_reduces_full_path_to_basename(
    synthetic_inventory_root: Path, tmp_path: Path
) -> None:
    refs = find_inventory_references(
        tmp_path / "anywhere" / "candles_EUR_USD_M1_9d_BA.jsonl",
        inventory_roots=[synthetic_inventory_root],
    )

    assert len(refs) == 2


def test_find_inventory_references_non_inventoried_name_is_empty(
    synthetic_inventory_root: Path,
) -> None:
    refs = find_inventory_references(
        "candles_ZZZ_TEST_M1_9d_BA.jsonl", inventory_roots=[synthetic_inventory_root]
    )

    assert refs == []


def test_guard_rejects_inventoried_span_by_default(synthetic_inventory_root: Path) -> None:
    with pytest.raises(ProvenanceGuardError, match="new output path / dataset epoch"):
        assert_not_inventoried_span(
            Path("data/candles_EUR_USD_M1_9d_BA.jsonl"),
            inventory_roots=[synthetic_inventory_root],
        )


def test_guard_allows_inventoried_span_with_explicit_override(
    synthetic_inventory_root: Path,
) -> None:
    refs = assert_not_inventoried_span(
        Path("data/candles_EUR_USD_M1_9d_BA.jsonl"),
        allow_overwrite=True,
        inventory_roots=[synthetic_inventory_root],
    )

    assert len(refs) == 2


def test_guard_override_is_never_silent(
    synthetic_inventory_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Using the override against a referenced basename MUST emit an
    explicit PROVENANCE_OVERRIDE warning — an overridden overwrite may
    never look like a normal provenance-clean run, and it confers no
    byte-admissibility / new-epoch / ML Step 4 authorisation."""
    assert_not_inventoried_span(
        Path("data/candles_EUR_USD_M1_9d_BA.jsonl"),
        allow_overwrite=True,
        inventory_roots=[synthetic_inventory_root],
    )

    err = capsys.readouterr().err
    assert "PROVENANCE_OVERRIDE" in err
    assert "byte-admissibility" in err


def test_guard_override_silent_for_non_inventoried(
    synthetic_inventory_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No spurious override warning when nothing is referenced."""
    assert_not_inventoried_span(
        Path("data/candles_ZZZ_TEST_M1_9d_BA.jsonl"),
        allow_overwrite=True,
        inventory_roots=[synthetic_inventory_root],
    )

    assert "PROVENANCE_OVERRIDE" not in capsys.readouterr().err


def test_guard_passes_non_inventoried_filename(synthetic_inventory_root: Path) -> None:
    refs = assert_not_inventoried_span(
        Path("data/candles_ZZZ_TEST_M1_9d_BA.jsonl"),
        inventory_roots=[synthetic_inventory_root],
    )

    assert refs == []


def test_real_default_inventory_roots_resolve_read_only() -> None:
    """READ-ONLY sanity: the committed default roots exist and reference the
    Gate P1 PR-B.1 / T2 span basename. No file is written or modified."""
    assert all(root.is_dir() for root in DEFAULT_INVENTORY_ROOTS)

    refs = find_inventory_references("candles_EUR_USD_M1_365d_BA.jsonl")

    assert refs, "committed metadata should reference the 365d_BA EUR_USD span"


def test_real_default_roots_cover_oanda_archive_manifest_read_only() -> None:
    """READ-ONLY: the 2026-05-31 archive manifest root must be a default
    inventory root — its 120 committed-SHA files include 100 non-M1 spans
    that no other metadata references (review finding on F5-C)."""
    assert any("oanda_archive_2026-05-31" in str(root) for root in DEFAULT_INVENTORY_ROOTS)

    refs = find_inventory_references("candles_EUR_USD_H4_3650d_BA.jsonl")

    assert any("oanda_archive_2026-05-31" in r for r in refs), (
        "archive manifest should reference the non-M1 H4 3650d span"
    )


# ---------------------------------------------------------------------------
# F5-C — CLI wiring (fetch_oanda_candles main / retrain_production_models)
# ---------------------------------------------------------------------------


def _bind_guard_to_root(monkeypatch: pytest.MonkeyPatch, module: Any, root: Path) -> None:
    """Rebind the module's guard to a synthetic inventory root."""

    def patched(output_path: Any, *, allow_overwrite: bool = False) -> list[str]:
        return pg.assert_not_inventoried_span(
            output_path, allow_overwrite=allow_overwrite, inventory_roots=[root]
        )

    monkeypatch.setattr(module, "assert_not_inventoried_span", patched)


def test_fetch_main_rejects_inventoried_output_by_default(
    tmp_path: Path, synthetic_inventory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_guard_to_root(monkeypatch, foc, synthetic_inventory_root)
    fetch_mock = MagicMock()
    monkeypatch.setattr(foc, "fetch_candles", fetch_mock)
    output = tmp_path / "candles_EUR_USD_M1_9d_BA.jsonl"

    rc = foc.main(["--output", str(output)])

    assert rc != 0
    fetch_mock.assert_not_called()
    assert not output.exists()


def test_fetch_main_allows_inventoried_output_with_flag(
    tmp_path: Path, synthetic_inventory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_guard_to_root(monkeypatch, foc, synthetic_inventory_root)
    fetch_mock = MagicMock(return_value=0)
    monkeypatch.setattr(foc, "fetch_candles", fetch_mock)
    output = tmp_path / "candles_EUR_USD_M1_9d_BA.jsonl"

    rc = foc.main(["--output", str(output), "--allow-overwrite-inventoried"])

    assert rc == 0
    fetch_mock.assert_called_once()


def test_fetch_main_passes_non_inventoried_output(
    tmp_path: Path, synthetic_inventory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bind_guard_to_root(monkeypatch, foc, synthetic_inventory_root)
    fetch_mock = MagicMock(return_value=0)
    monkeypatch.setattr(foc, "fetch_candles", fetch_mock)
    output = tmp_path / "candles_ZZZ_TEST_M1_9d_BA.jsonl"

    rc = foc.main(["--output", str(output)])

    assert rc == 0
    fetch_mock.assert_called_once()


def _run_retrain_main(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["retrain", *argv])
    return retrain.main()


def test_retrain_rejects_inventoried_span_by_default(
    tmp_path: Path, synthetic_inventory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OANDA_ACCESS_TOKEN", "test-token")
    _bind_guard_to_root(monkeypatch, retrain, synthetic_inventory_root)
    fetch_mock = MagicMock(return_value=True)
    train_mock = MagicMock(return_value=True)
    monkeypatch.setattr(retrain, "_fetch_pair", fetch_mock)
    monkeypatch.setattr(retrain, "_train_all", train_mock)

    rc = _run_retrain_main(
        monkeypatch,
        [
            "--pairs",
            "EUR_USD",
            "--days",
            "9",
            "--data-dir",
            str(tmp_path / "data"),
            "--model-dir",
            str(tmp_path / "models"),
        ],
    )

    assert rc == 1
    fetch_mock.assert_not_called()
    train_mock.assert_not_called()


def test_retrain_allows_inventoried_span_with_flag_and_forwards_it(
    tmp_path: Path, synthetic_inventory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OANDA_ACCESS_TOKEN", "test-token")
    _bind_guard_to_root(monkeypatch, retrain, synthetic_inventory_root)
    fetch_mock = MagicMock(return_value=True)
    train_mock = MagicMock(return_value=True)
    monkeypatch.setattr(retrain, "_fetch_pair", fetch_mock)
    monkeypatch.setattr(retrain, "_train_all", train_mock)

    rc = _run_retrain_main(
        monkeypatch,
        [
            "--pairs",
            "EUR_USD",
            "--days",
            "9",
            "--data-dir",
            str(tmp_path / "data"),
            "--model-dir",
            str(tmp_path / "models"),
            "--allow-overwrite-inventoried",
        ],
    )

    assert rc == 0
    fetch_mock.assert_called_once()
    assert fetch_mock.call_args.kwargs["allow_overwrite"] is True
    train_mock.assert_called_once()


def test_retrain_non_inventoried_span_passes_without_flag(
    tmp_path: Path, synthetic_inventory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OANDA_ACCESS_TOKEN", "test-token")
    _bind_guard_to_root(monkeypatch, retrain, synthetic_inventory_root)
    fetch_mock = MagicMock(return_value=True)
    train_mock = MagicMock(return_value=True)
    monkeypatch.setattr(retrain, "_fetch_pair", fetch_mock)
    monkeypatch.setattr(retrain, "_train_all", train_mock)

    # days=42 → candles_EUR_USD_M1_42d_BA.jsonl is NOT in the synthetic inventory.
    rc = _run_retrain_main(
        monkeypatch,
        [
            "--pairs",
            "EUR_USD",
            "--days",
            "42",
            "--data-dir",
            str(tmp_path / "data"),
            "--model-dir",
            str(tmp_path / "models"),
        ],
    )

    assert rc == 0
    fetch_mock.assert_called_once()
    assert fetch_mock.call_args.kwargs["allow_overwrite"] is False


def test_retrain_fetch_pair_forwards_override_flag_to_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(retrain.subprocess, "run", run_mock)

    retrain._fetch_pair("EUR_USD", Path("data"), 9, allow_overwrite=True)
    cmd_with = run_mock.call_args[0][0]
    assert "--allow-overwrite-inventoried" in cmd_with

    retrain._fetch_pair("EUR_USD", Path("data"), 9)
    cmd_without = run_mock.call_args[0][0]
    assert "--allow-overwrite-inventoried" not in cmd_without
