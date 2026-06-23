"""PR-B.1 raw inventory + coverage tests (plan §6)."""

from __future__ import annotations

import hashlib

from scripts._gate_p1_inspector.inspector import coverage as coverage_mod
from scripts._gate_p1_inspector.inspector import raw_inventory as raw_mod

_PAIRS = ["EUR_USD", "GBP_USD"]


def test_inventory_reads_readonly_and_computes_metadata(tmp_path, write_candle_file):
    path = write_candle_file(tmp_path, "EUR_USD", "365d", n_rows=5)
    before_bytes = path.read_bytes()
    inv = raw_mod.inspect_file("EUR_USD", path)

    assert inv.present is True
    assert inv.row_count == 5
    assert inv.size_bytes == len(before_bytes)
    assert inv.file_sha256 == hashlib.sha256(before_bytes).hexdigest()
    assert inv.ts_min_utc is not None and inv.ts_max_utc is not None
    assert inv.schema_valid is True
    # File is not mutated by inspection.
    assert path.read_bytes() == before_bytes


def test_inventory_handles_missing_file(tmp_path):
    inv = raw_mod.inspect_file("EUR_USD", tmp_path / "nope_M1_365d_BA.jsonl")
    assert inv.present is False
    assert inv.row_count == 0
    assert inv.file_sha256 is None


def test_inventory_handles_malformed_rows_safely(tmp_path, write_candle_file):
    path = write_candle_file(tmp_path, "EUR_USD", "365d", n_rows=3, malformed=True)
    inv = raw_mod.inspect_file("EUR_USD", path)
    assert inv.row_count == 3
    assert inv.malformed_rows == 1
    # malformed row does not crash; file still hashed fully.
    assert inv.file_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_inventory_detects_missing_schema_field(tmp_path, write_candle_file):
    path = write_candle_file(tmp_path, "EUR_USD", "365d", n_rows=4, missing_field=True)
    inv = raw_mod.inspect_file("EUR_USD", path)
    assert inv.missing_fields_count == 4
    assert inv.schema_valid is False


def test_inventory_records_extension_keys(tmp_path, write_candle_file):
    path = write_candle_file(tmp_path, "EUR_USD", "365d", n_rows=3, include_extra_key=True)
    inv = raw_mod.inspect_file("EUR_USD", path)
    names = {e["field_name"] for e in inv.schema_extension_findings}
    assert "volume" in names
    assert inv.schema_valid is True  # extra key is informational, not a failure


def test_inventory_bounded_memory_small_block(tmp_path, write_candle_file, monkeypatch):
    # Force a 64-byte streaming block to prove multi-block streaming works
    # without loading the whole file; result must equal a whole-file hash.
    path = write_candle_file(tmp_path, "EUR_USD", "365d", n_rows=30)
    monkeypatch.setattr(raw_mod, "_BLOCK_SIZE", 64)
    inv = raw_mod.inspect_file("EUR_USD", path)
    assert inv.row_count == 30
    assert inv.file_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_coverage_full_universe_has_interval(tmp_path, write_full_universe):
    write_full_universe(tmp_path, _PAIRS, "365d", n_rows=5)
    candidate = raw_mod.inspect_candidate(tmp_path, _PAIRS, "365d")
    cov = coverage_mod.derive_coverage("365d", candidate["files"])
    assert cov["observation_start_timestamp_utc"] is not None
    assert cov["observation_end_timestamp_utc"] is not None
    assert cov["span_days_effective"] is not None


def test_coverage_null_interval_when_pair_missing(tmp_path, write_candle_file):
    # Only one of two pairs present => interval is null.
    write_candle_file(tmp_path, "EUR_USD", "365d", n_rows=5)
    candidate = raw_mod.inspect_candidate(tmp_path, _PAIRS, "365d")
    cov = coverage_mod.derive_coverage("365d", candidate["files"])
    assert cov["observation_start_timestamp_utc"] is None
    assert cov["span_days_effective"] is None
    finding_types = {f["finding_type"] for f in cov["common_coverage_findings"]}
    assert "pairs_missing_or_empty" in finding_types
