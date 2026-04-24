"""evaluate_ml_baseline — out-of-sample metrics for a trained model (Phase 9.6).

Loads a saved model directory and a feature parquet, runs inference on rows
strictly AFTER the model's train_cutoff, and prints evaluation metrics.

Usage:
    python scripts/evaluate_ml_baseline.py \\
        --model-dir models/ml_baseline_20260424T120000 \\
        --parquet data/features/eur_usd_m5.parquet
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import click
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fx_ai_trading.services.ml.inference import load_inference_service
from fx_ai_trading.services.ml.training import LABEL_COLUMN  # noqa: PLC2701


@click.command()
@click.option("--model-dir", required=True, help="Model directory (from train_ml_baseline).")
@click.option("--parquet", required=True, help="Feature store parquet path.")
@click.option(
    "--split",
    default="after_train_cutoff",
    type=click.Choice(["after_train_cutoff", "after_val_cutoff", "all"]),
    show_default=True,
    help="Which rows to evaluate.",
)
def main(model_dir: str, parquet: str, split: str) -> None:
    """Print out-of-sample evaluation metrics."""
    svc = load_inference_service(model_dir)
    meta = svc.metadata
    click.echo(f"Model: {meta.model_id}  feature_version={meta.feature_version}")
    click.echo(f"Train cutoff: {meta.train_cutoff}  Val cutoff: {meta.val_cutoff}")

    table = pq.read_table(parquet, columns=["ts"] + meta.feature_columns + [LABEL_COLUMN])
    mask_valid = table.column(LABEL_COLUMN).is_valid()
    table = table.filter(mask_valid)

    # Apply split filter.
    if split != "all":
        cutoff_str = meta.train_cutoff if split == "after_train_cutoff" else meta.val_cutoff
        cutoff = datetime.fromisoformat(cutoff_str)
        ts_col = table.column("ts").to_pylist()
        keep = [ts > cutoff for ts in ts_col]
        table = table.filter(keep)

    n = len(table)
    if n == 0:
        click.echo("No rows to evaluate after applying split filter.")
        return

    click.echo(f"Evaluating on {n} rows …")

    y_true, y_pred = [], []
    for i in range(n):
        feats = {col: table.column(col)[i].as_py() for col in meta.feature_columns}
        label, _ = svc.predict(feats)
        true_val = table.column(LABEL_COLUMN)[i].as_py()
        y_true.append(true_val)
        y_pred.append(label)

    hit_rate = sum(a == b for a, b in zip(y_true, y_pred, strict=True)) / n
    label_counts = {v: y_pred.count(v) for v in (-1, 0, 1)}

    click.echo(f"\nHit rate:         {hit_rate:.4f}")
    click.echo("Prediction distribution:")
    click.echo(f"  long  (+1): {label_counts.get(1, 0):5d} ({label_counts.get(1, 0) / n:.2%})")
    click.echo(f"  short (-1): {label_counts.get(-1, 0):5d} ({label_counts.get(-1, 0) / n:.2%})")
    click.echo(f"  timeout (0): {label_counts.get(0, 0):5d} ({label_counts.get(0, 0) / n:.2%})")

    # Per-class metrics.
    click.echo("\nPer-class metrics (true label → predicted):")
    for cls, name in [(-1, "short"), (0, "timeout"), (1, "long")]:
        tp = sum(1 for a, b in zip(y_true, y_pred, strict=True) if a == cls and b == cls)
        fp = sum(1 for a, b in zip(y_true, y_pred, strict=True) if a != cls and b == cls)
        fn = sum(1 for a, b in zip(y_true, y_pred, strict=True) if a == cls and b != cls)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        click.echo(f"  {name:8s}: precision={prec:.4f}  recall={rec:.4f}  tp={tp}")


if __name__ == "__main__":
    main()
