"""build_feature_store — JSONL candle → parquet feature store (Phase 9.5).

Reads one or more JSONL candle files (produced by fetch_oanda_candles.py),
computes TA features and forward-return / triple-barrier labels for each bar,
and writes a parquet file suitable for ML training.

Leak-free design:
  - Features at row i use candles[0..i] (no lookahead).
  - Labels at row i use closes[i+1..i+horizon] (future window).
  - Rows where the full label window is unavailable get null labels.
  - Training code must further filter: max(train_ts) < min(val_ts).

Usage:
    python scripts/build_feature_store.py \\
        --input data/smoke_eurusd_m5_1d.jsonl \\
        --instrument EUR_USD \\
        --output data/features/eur_usd_m5.parquet

    # Multiple files merged into one output:
    python scripts/build_feature_store.py \\
        --input data/g8_m5_202501.jsonl \\
        --input data/g8_m5_202502.jsonl \\
        --instrument EUR_USD \\
        --output data/features/eur_usd_m5.parquet
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import click
import pyarrow as pa
import pyarrow.parquet as pq

# Ensure src/ is on path when run directly.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fx_ai_trading.services.feature_service import compute_features_from_candles
from fx_ai_trading.services.labeling.forward_return import forward_return
from fx_ai_trading.services.labeling.triple_barrier import triple_barrier

_WARMUP = 50  # minimum candles before first feature row


def _parse_oanda_time(raw: str) -> datetime:
    raw = raw.rstrip("Z")
    if "." in raw:
        base, frac = raw.split(".", 1)
        raw = f"{base}.{frac[:6]}"
    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


def _load_jsonl(path: Path) -> list[dict]:
    candles = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            candles.append(
                {
                    "timestamp": _parse_oanda_time(raw["time"]),
                    "open": float(raw["o"]),
                    "high": float(raw["h"]),
                    "low": float(raw["l"]),
                    "close": float(raw["c"]),
                    "volume": int(raw.get("volume", 0)),
                }
            )
    candles.sort(key=lambda c: c["timestamp"])
    return candles


def _build_rows(
    candles: list[dict],
    instrument: str,
    horizon: int,
    tp_pips: float,
    sl_pips: float,
    pip_size: float,
    warmup: int,
) -> list[dict]:
    closes = [c["close"] for c in candles]
    fwd_labels = forward_return(closes, horizon)
    tb_labels = triple_barrier(closes, horizon, tp_pips, sl_pips, pip_size)

    rows = []
    for i in range(warmup, len(candles)):
        c = candles[i]
        # Features use candles[0..i] inclusive — no lookahead.
        feats = compute_features_from_candles(candles[: i + 1])
        rows.append(
            {
                "instrument": instrument,
                "ts": c["timestamp"],
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c["volume"],
                **feats,
                "label_fwd_return": fwd_labels[i],
                "label_triple_barrier": tb_labels[i],
            }
        )
    return rows


def _rows_to_table(rows: list[dict]) -> pa.Table:
    if not rows:
        raise ValueError("No rows to write — check warmup / input data size")

    schema = pa.schema(
        [
            ("instrument", pa.string()),
            ("ts", pa.timestamp("us", tz="UTC")),
            ("open", pa.float64()),
            ("high", pa.float64()),
            ("low", pa.float64()),
            ("close", pa.float64()),
            ("volume", pa.int64()),
            # M1 base features (15)
            ("atr_14", pa.float64()),
            ("bb_lower", pa.float64()),
            ("bb_middle", pa.float64()),
            ("bb_pct_b", pa.float64()),
            ("bb_upper", pa.float64()),
            ("bb_width", pa.float64()),
            ("ema_12", pa.float64()),
            ("ema_26", pa.float64()),
            ("last_close", pa.float64()),
            ("macd_histogram", pa.float64()),
            ("macd_line", pa.float64()),
            ("macd_signal", pa.float64()),
            ("rsi_14", pa.float64()),
            ("sma_20", pa.float64()),
            ("sma_50", pa.float64()),
            # v4 upper-TF features — M5 (8)
            ("m5_return_1", pa.float64()),
            ("m5_return_3", pa.float64()),
            ("m5_volatility", pa.float64()),
            ("m5_rsi_14", pa.float64()),
            ("m5_ma_slope", pa.float64()),
            ("m5_bb_pct_b", pa.float64()),
            ("m5_trend_slope", pa.float64()),
            ("m5_trend_dir", pa.float64()),
            # v4 upper-TF features — M15 (8)
            ("m15_return_1", pa.float64()),
            ("m15_return_3", pa.float64()),
            ("m15_volatility", pa.float64()),
            ("m15_rsi_14", pa.float64()),
            ("m15_ma_slope", pa.float64()),
            ("m15_bb_pct_b", pa.float64()),
            ("m15_trend_slope", pa.float64()),
            ("m15_trend_dir", pa.float64()),
            # v4 upper-TF features — H1 (8)
            ("h1_return_1", pa.float64()),
            ("h1_return_3", pa.float64()),
            ("h1_volatility", pa.float64()),
            ("h1_rsi_14", pa.float64()),
            ("h1_ma_slope", pa.float64()),
            ("h1_bb_pct_b", pa.float64()),
            ("h1_trend_slope", pa.float64()),
            ("h1_trend_dir", pa.float64()),
            # Labels
            ("label_fwd_return", pa.float64()),
            ("label_triple_barrier", pa.int8()),
        ]
    )

    cols: dict[str, list] = {field.name: [] for field in schema}
    for row in rows:
        for field in schema:
            cols[field.name].append(row[field.name])

    arrays = []
    for field in schema:
        if pa.types.is_timestamp(field.type):
            arrays.append(pa.array(cols[field.name], type=field.type))
        elif field.type == pa.int8():
            arrays.append(
                pa.array(
                    [int(v) if v is not None else None for v in cols[field.name]],
                    type=pa.int8(),
                )
            )
        else:
            arrays.append(pa.array(cols[field.name], type=field.type))

    return pa.table(dict(zip([f.name for f in schema], arrays, strict=True)), schema=schema)


@click.command()
@click.option("--input", "inputs", multiple=True, required=True, help="JSONL candle file(s).")
@click.option("--instrument", required=True, help="Instrument name, e.g. EUR_USD.")
@click.option("--output", required=True, help="Output parquet path.")
@click.option("--horizon", default=12, show_default=True, help="Label horizon in bars.")
@click.option("--tp-pips", default=10.0, show_default=True, help="Triple-barrier TP in pips.")
@click.option("--sl-pips", default=10.0, show_default=True, help="Triple-barrier SL in pips.")
@click.option(
    "--pip-size", default=0.0001, show_default=True, help="Pip size (0.0001 for most FX)."
)
@click.option("--warmup", default=_WARMUP, show_default=True, help="Min candles before first row.")
def main(
    inputs: tuple[str, ...],
    instrument: str,
    output: str,
    horizon: int,
    tp_pips: float,
    sl_pips: float,
    pip_size: float,
    warmup: int,
) -> None:
    """Build a parquet feature store from JSONL candle files."""
    t0 = time.perf_counter()

    all_candles: list[dict] = []
    for path_str in inputs:
        path = Path(path_str)
        click.echo(f"Loading {path} …")
        batch = _load_jsonl(path)
        click.echo(f"  {len(batch)} candles")
        all_candles.extend(batch)

    all_candles.sort(key=lambda c: c["timestamp"])
    click.echo(f"Total candles: {len(all_candles)}")

    if len(all_candles) < warmup + horizon:
        raise click.ClickException(
            f"Need at least {warmup + horizon} candles, got {len(all_candles)}"
        )

    click.echo("Computing features and labels …")
    rows = _build_rows(all_candles, instrument, horizon, tp_pips, sl_pips, pip_size, warmup)
    click.echo(f"  {len(rows)} rows generated")

    table = _rows_to_table(rows)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out_path, compression="snappy")

    elapsed = time.perf_counter() - t0
    click.echo(f"Written {out_path}  ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
