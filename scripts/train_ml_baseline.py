"""train_ml_baseline — feature parquet → LightGBM model (Phase 9.6).

Runs walk-forward cross-validation and saves the final fold's model
(trained on all available data up to the last val_cutoff).

Usage:
    python scripts/train_ml_baseline.py \\
        --parquet data/features/eur_usd_m5.parquet \\
        --output-dir models/

    # Custom window sizes:
    python scripts/train_ml_baseline.py \\
        --parquet data/features/eur_usd_m5.parquet \\
        --train-months 6 --val-months 1 \\
        --output-dir models/
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fx_ai_trading.services.ml.model_store import (
    ModelMetadata,
    model_dir_name,
    save_model,
)
from fx_ai_trading.services.ml.training import (
    DEFAULT_PARAMS,
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    train_walk_forward,
)


@click.command()
@click.option("--parquet", required=True, help="Feature store parquet path.")
@click.option("--output-dir", default="models", show_default=True, help="Models root directory.")
@click.option("--train-months", default=6, show_default=True, help="Training window (months).")
@click.option("--val-months", default=1, show_default=True, help="Validation window (months).")
def main(parquet: str, output_dir: str, train_months: int, val_months: int) -> None:
    """Train LightGBM walk-forward baseline and save the best model."""
    click.echo(f"Loading features from {parquet} …")
    folds = train_walk_forward(parquet, train_months=train_months, val_months=val_months)

    if not folds:
        raise click.ClickException("No folds produced — check data size and window settings.")

    click.echo(f"Walk-forward complete: {len(folds)} fold(s)")
    for f in folds:
        click.echo(
            f"  fold {f.fold_idx}: train={f.n_train} val={f.n_val} "
            f"hit_rate={f.metrics.get('hit_rate', 0):.4f} "
            f"prec={f.metrics.get('macro_precision', 0):.4f}"
        )

    # Save the last fold's model (trained on the most data).
    best = folds[-1]
    out_dir = Path(output_dir) / model_dir_name()

    metadata = ModelMetadata(
        model_id=out_dir.name,
        created_at=datetime.now(UTC).isoformat(),
        feature_version="v2",
        feature_columns=FEATURE_COLUMNS,
        label_column=LABEL_COLUMN,
        train_cutoff=best.train_cutoff.isoformat(),
        val_cutoff=best.val_cutoff.isoformat(),
        n_train_rows=best.n_train,
        n_val_rows=best.n_val,
        metrics=best.metrics,
        hyperparams=DEFAULT_PARAMS,
    )

    save_model(best.model, metadata, out_dir)
    click.echo(f"Model saved → {out_dir}")


if __name__ == "__main__":
    main()
