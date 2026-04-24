"""Integration test: build_feature_store JSONL → parquet roundtrip (Phase 9.5).

Writes a minimal synthetic JSONL candle file, runs build_feature_store,
reads the parquet back, and asserts schema + row count + leak-free invariant.
"""

from __future__ import annotations

import json

# Import the CLI entry point.
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from build_feature_store import main  # noqa: E402


def _make_jsonl(path: Path, n: int = 120) -> None:
    """Write *n* synthetic M5 candles starting 2024-01-01 00:00 UTC."""
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    with path.open("w") as fh:
        for i in range(n):
            ts = base + timedelta(minutes=5 * i)
            close = 1.1000 + i * 0.00001
            row = {
                "time": ts.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                "o": round(close - 0.0001, 5),
                "h": round(close + 0.0002, 5),
                "l": round(close - 0.0002, 5),
                "c": round(close, 5),
                "volume": 100 + i,
            }
            fh.write(json.dumps(row) + "\n")


class TestFeatureStoreRoundtrip:
    def test_parquet_written_and_readable(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "candles.jsonl"
        out = tmp_path / "features.parquet"
        _make_jsonl(jsonl, n=120)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--input",
                str(jsonl),
                "--instrument",
                "EUR_USD",
                "--output",
                str(out),
                "--horizon",
                "12",
                "--warmup",
                "50",
            ],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

        table = pq.read_table(out)
        # 120 candles - 50 warmup = 70 rows, but last 12 have null labels → still 70 rows
        assert len(table) == 70

    def test_schema_columns_present(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "candles.jsonl"
        out = tmp_path / "features.parquet"
        _make_jsonl(jsonl, n=100)

        runner = CliRunner()
        runner.invoke(
            main,
            [
                "--input",
                str(jsonl),
                "--instrument",
                "EUR_USD",
                "--output",
                str(out),
                "--horizon",
                "12",
                "--warmup",
                "50",
            ],
        )

        table = pq.read_table(out)
        expected_cols = {
            "instrument",
            "ts",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "atr_14",
            "sma_20",
            "sma_50",
            "ema_12",
            "ema_26",
            "macd_line",
            "macd_signal",
            "macd_histogram",
            "rsi_14",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_pct_b",
            "bb_width",
            "last_close",
            "label_fwd_return",
            "label_triple_barrier",
        }
        assert expected_cols.issubset(set(table.schema.names))

    def test_last_horizon_labels_are_null(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "candles.jsonl"
        out = tmp_path / "features.parquet"
        _make_jsonl(jsonl, n=100)

        runner = CliRunner()
        runner.invoke(
            main,
            [
                "--input",
                str(jsonl),
                "--instrument",
                "EUR_USD",
                "--output",
                str(out),
                "--horizon",
                "12",
                "--warmup",
                "50",
            ],
        )

        table = pq.read_table(out)
        fwd = table.column("label_fwd_return").to_pylist()
        tb = table.column("label_triple_barrier").to_pylist()
        # Last 12 rows should have null labels.
        assert all(v is None for v in fwd[-12:])
        assert all(v is None for v in tb[-12:])
        # Rows before that should have non-null labels.
        assert all(v is not None for v in fwd[:-12])

    def test_leak_free_ts_ordering(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "candles.jsonl"
        out = tmp_path / "features.parquet"
        _make_jsonl(jsonl, n=100)

        runner = CliRunner()
        runner.invoke(
            main,
            [
                "--input",
                str(jsonl),
                "--instrument",
                "EUR_USD",
                "--output",
                str(out),
                "--horizon",
                "12",
                "--warmup",
                "50",
            ],
        )

        table = pq.read_table(out)
        ts_list = table.column("ts").to_pylist()
        assert ts_list == sorted(ts_list), "timestamps must be in ascending order"

    def test_too_few_candles_fails(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "candles.jsonl"
        out = tmp_path / "features.parquet"
        _make_jsonl(jsonl, n=10)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--input",
                str(jsonl),
                "--instrument",
                "EUR_USD",
                "--output",
                str(out),
                "--horizon",
                "12",
                "--warmup",
                "50",
            ],
        )
        assert result.exit_code != 0
