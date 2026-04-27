"""Retrain production LGBM models for all 20 pairs using fresh OANDA candle data.

Phase 9.5-A / pre-live: must be run after train_lgbm_models.py B-2 label
fix (PR #241) to replace models built on the buggy heuristic SL logic.

Pipeline (per pair):
  1. fetch_oanda_candles.py --price BA --days 365 → data/candles_{PAIR}_M1_365d_BA.jsonl
  2. train_lgbm_models.py                         → models/lgbm/{PAIR}.joblib
                                                     models/lgbm/manifest.json

Requirements:
  OANDA_ACCESS_TOKEN env var must be set.
  lightgbm, joblib, pandas, numpy installed (already in .venv).

Usage:
  .venv/Scripts/python.exe scripts/retrain_production_models.py
  .venv/Scripts/python.exe scripts/retrain_production_models.py --pairs EUR_USD USD_JPY
  .venv/Scripts/python.exe scripts/retrain_production_models.py --skip-fetch

Flags:
  --pairs          Subset of pairs to retrain (default: all 20).
  --skip-fetch     Skip the candle-fetch step (use existing JSONL files).
  --days           Candle look-back in days (default: 365).
  --data-dir       Directory for candle JSONL files (default: data/).
  --model-dir      Output directory for models (default: models/lgbm/).
  --train-frac     Fraction of data for training, rest discarded after purge
                   (default: 0.80, passed to train_lgbm_models.py).
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

_log = logging.getLogger(__name__)

_ALL_PAIRS = [
    "AUD_CAD",
    "AUD_JPY",
    "AUD_NZD",
    "AUD_USD",
    "CHF_JPY",
    "EUR_AUD",
    "EUR_CAD",
    "EUR_CHF",
    "EUR_GBP",
    "EUR_JPY",
    "EUR_USD",
    "GBP_AUD",
    "GBP_CHF",
    "GBP_JPY",
    "GBP_USD",
    "NZD_JPY",
    "NZD_USD",
    "USD_CAD",
    "USD_CHF",
    "USD_JPY",
]

_SCRIPTS_DIR = Path(__file__).resolve().parent
_PYTHON = sys.executable


def _run(cmd: list[str], *, step: str) -> bool:
    """Run a subprocess command.  Returns True on success, False on failure."""
    _log.info("%s: %s", step, " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        _log.error("%s: FAILED (exit code %d)", step, result.returncode)
        return False
    return True


def _fetch_pair(pair: str, data_dir: Path, days: int) -> bool:
    """Fetch BA candles for one pair via fetch_oanda_candles.py."""
    output = data_dir / f"candles_{pair}_M1_{days}d_BA.jsonl"
    return _run(
        [
            _PYTHON,
            str(_SCRIPTS_DIR / "fetch_oanda_candles.py"),
            "--instrument",
            pair,
            "--granularity",
            "M1",
            "--days",
            str(days),
            "--price",
            "BA",
            "--output",
            str(output),
        ],
        step=f"fetch {pair}",
    )


def _train_all(pairs: list[str], data_dir: Path, model_dir: Path, train_frac: float) -> bool:
    """Run train_lgbm_models.py for the given pairs."""
    return _run(
        [
            _PYTHON,
            str(_SCRIPTS_DIR / "train_lgbm_models.py"),
            "--pairs",
            *pairs,
            "--data-dir",
            str(data_dir),
            "--model-dir",
            str(model_dir),
            "--train-frac",
            str(train_frac),
        ],
        step="train all pairs",
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--pairs",
        nargs="*",
        default=None,
        help="Subset of pairs to retrain (default: all 20).",
    )
    p.add_argument(
        "--skip-fetch",
        action="store_true",
        default=False,
        help="Skip candle fetch and use existing JSONL files.",
    )
    p.add_argument("--days", type=int, default=365, help="Candle look-back in days (default 365).")
    p.add_argument("--data-dir", default="data", help="Candle JSONL directory (default: data/).")
    p.add_argument(
        "--model-dir", default="models/lgbm", help="Model output directory (default: models/lgbm/)."
    )
    p.add_argument(
        "--train-frac",
        type=float,
        default=0.80,
        help="Training fraction passed to train_lgbm_models.py (default 0.80).",
    )
    args = p.parse_args()

    pairs = args.pairs or _ALL_PAIRS
    data_dir = Path(args.data_dir)
    model_dir = Path(args.model_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    # Verify OANDA token is available (only needed for fetch step).
    if not args.skip_fetch:
        token = os.environ.get("OANDA_ACCESS_TOKEN", "").strip()
        if not token:
            _log.error("OANDA_ACCESS_TOKEN is not set — required for candle fetch.")
            _log.error("Set the env var or re-run with --skip-fetch to use existing JSONL files.")
            return 1

    fetch_failed: list[str] = []

    if not args.skip_fetch:
        _log.info("=== Step 1: fetching BA candles for %d pairs ===", len(pairs))
        for pair in pairs:
            if not _fetch_pair(pair, data_dir, args.days):
                fetch_failed.append(pair)
        if fetch_failed:
            _log.warning("Fetch failed for: %s — skipping those pairs in training", fetch_failed)
    else:
        _log.info("=== Step 1: fetch skipped (--skip-fetch) ===")

    # Exclude fetch-failed pairs from training.
    train_pairs = [p for p in pairs if p not in fetch_failed]
    if not train_pairs:
        _log.error("No pairs to train after fetch failures.")
        return 1

    _log.info("=== Step 2: training LGBM models for %d pairs ===", len(train_pairs))
    if not _train_all(train_pairs, data_dir, model_dir, args.train_frac):
        _log.error("Training step failed.")
        return 1

    _log.info("=== Retrain complete ===")
    _log.info("Models written to: %s", model_dir)
    if fetch_failed:
        _log.warning("Fetch failed (models NOT updated): %s", fetch_failed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
