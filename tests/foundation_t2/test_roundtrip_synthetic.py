"""Foundation T2 round-trip tests (synthetic files via local-mock only)."""

from __future__ import annotations

from scripts.foundation_t2.constants import (
    T2_ROUNDTRIP_MATCH_OBSERVED,
    T2_ROUNDTRIP_MISMATCH,
)
from scripts.foundation_t2.destination import LocalMockDestination, UnavailableR2Destination
from scripts.foundation_t2.roundtrip import roundtrip_file, roundtrip_span_synthetic


def test_synthetic_roundtrip_matches(tmp_path, synthetic_span_files):
    src = tmp_path / "src"
    files = synthetic_span_files(src, n=3)
    dest = LocalMockDestination(tmp_path / "store")
    result = roundtrip_span_synthetic(dest, "synthetic-span", files, src, tmp_path / "restore")
    assert result["all_files_matched"] is True
    for f in result["files"]:
        assert f["roundtrip_status"] == T2_ROUNDTRIP_MATCH_OBSERVED
        assert f["size_match"] and f["checksum_match"]


def test_roundtrip_detects_mismatch(tmp_path, synthetic_span_files):
    src = tmp_path / "src"
    files = synthetic_span_files(src, n=1)
    dest = LocalMockDestination(tmp_path / "store")
    meta = files[0]
    # Claim a wrong expected checksum => mismatch detected.
    result = roundtrip_file(
        dest,
        src / meta["logical_file_id"],
        meta["logical_file_id"],
        "0" * 64,
        meta["size_bytes"],
        tmp_path / "restore",
    )
    assert result["roundtrip_status"] == T2_ROUNDTRIP_MISMATCH
    assert result["checksum_match"] is False


def test_roundtrip_unavailable_destination_not_performed(tmp_path, synthetic_span_files):
    src = tmp_path / "src"
    files = synthetic_span_files(src, n=2)
    result = roundtrip_span_synthetic(
        UnavailableR2Destination(), "365d_BA", files, src, tmp_path / "restore"
    )
    assert result["all_files_matched"] is False
    for f in result["files"]:
        assert f["deposit_status"] == "NOT_PERFORMED"
