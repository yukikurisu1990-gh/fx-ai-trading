"""Stage 1 unit tests — row-set manifest persistence + equality."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts._verification_harness import row_set as RS  # noqa: N812


def test_compute_indices_sha256_deterministic():
    a = np.arange(100, dtype=np.int64)
    b = np.arange(100, dtype=np.int64)
    assert RS.compute_indices_sha256(a) == RS.compute_indices_sha256(b)


def test_compute_indices_sha256_differs_for_different_indices():
    a = np.arange(100, dtype=np.int64)
    b = np.arange(100, dtype=np.int64) + 1
    assert RS.compute_indices_sha256(a) != RS.compute_indices_sha256(b)


def test_persist_and_load_round_trip(tmp_path: Path):
    idx = np.array([0, 2, 4, 6, 8], dtype=np.int64)
    parquet_out = tmp_path / "row_sets" / "aligned_train_idx.parquet"
    json_out = tmp_path / "row_sets" / "aligned_train_idx.json"
    m = RS.persist_row_index_manifest(
        cell_id="C-d2-arch-control-aligned",
        split="train",
        indices=idx,
        parquet_out=parquet_out,
        json_out=json_out,
    )
    assert parquet_out.is_file()
    assert json_out.is_file()
    loaded = RS.load_row_index_manifest(json_out)
    assert loaded.cell_id == m.cell_id
    assert loaded.split == m.split
    assert loaded.n_rows == m.n_rows
    assert loaded.parquet_sha256 == m.parquet_sha256


def test_assert_row_sets_equal_passes_when_identical(tmp_path: Path):
    idx = np.arange(50, dtype=np.int64)
    m_a = RS.persist_row_index_manifest(
        cell_id="A",
        split="train",
        indices=idx,
        parquet_out=tmp_path / "a.parquet",
        json_out=tmp_path / "a.json",
    )
    m_b = RS.persist_row_index_manifest(
        cell_id="B",
        split="train",
        indices=idx,
        parquet_out=tmp_path / "b.parquet",
        json_out=tmp_path / "b.json",
    )
    RS.assert_row_sets_equal(m_a, m_b, label="A-vs-B")  # no raise


def test_assert_row_sets_equal_halts_on_mismatch(tmp_path: Path):
    m_a = RS.persist_row_index_manifest(
        cell_id="A",
        split="train",
        indices=np.arange(50, dtype=np.int64),
        parquet_out=tmp_path / "a.parquet",
        json_out=tmp_path / "a.json",
    )
    m_b = RS.persist_row_index_manifest(
        cell_id="B",
        split="train",
        indices=np.arange(40, dtype=np.int64),  # different
        parquet_out=tmp_path / "b.parquet",
        json_out=tmp_path / "b.json",
    )
    with pytest.raises(RS.RowSetManifestError):
        RS.assert_row_sets_equal(m_a, m_b, label="A-vs-B")


def test_assert_row_sets_equal_halts_on_split_mismatch(tmp_path: Path):
    idx = np.arange(50, dtype=np.int64)
    m_a = RS.persist_row_index_manifest(
        cell_id="A",
        split="train",
        indices=idx,
        parquet_out=tmp_path / "a.parquet",
        json_out=tmp_path / "a.json",
    )
    m_b = RS.persist_row_index_manifest(
        cell_id="B",
        split="val",
        indices=idx,
        parquet_out=tmp_path / "b.parquet",
        json_out=tmp_path / "b.json",
    )
    with pytest.raises(RS.RowSetManifestError):
        RS.assert_row_sets_equal(m_a, m_b)


def test_row_set_manifest_hash_deterministic(tmp_path: Path):
    ms = [
        RS.persist_row_index_manifest(
            cell_id=f"cell_{i}",
            split="train",
            indices=np.arange(10 + i, dtype=np.int64),
            parquet_out=tmp_path / f"{i}.parquet",
            json_out=tmp_path / f"{i}.json",
        )
        for i in range(3)
    ]
    h1 = RS.compute_row_set_manifest_hash(ms)
    h2 = RS.compute_row_set_manifest_hash(list(reversed(ms)))  # order-independent
    assert h1 == h2
