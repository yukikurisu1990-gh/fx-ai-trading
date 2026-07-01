"""CLI for the ML uplift harness — synthetic-only, no real run.

Loads a JSON experiment contract, validates it fail-closed, and writes a
clearly-marked SYNTHETIC-ONLY smoke report under a safe output root. It trains
no model, reads no real market data, and computes no trading metric.

Usage::

    python scripts/run_ml_uplift_harness.py --config <contract.json> \\
        --output-root /tmp/ml_uplift_out
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ml_uplift_harness.contracts import HarnessContractError  # noqa: E402
from scripts.ml_uplift_harness.synthetic_runner import run_synthetic_smoke  # noqa: E402

DEFAULT_OUTPUT_ROOT = Path(tempfile.gettempdir()) / "ml_uplift_harness_synthetic"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_ml_uplift_harness",
        description="ML uplift harness synthetic-only smoke runner (no real run).",
    )
    parser.add_argument("--config", required=True, help="Path to a JSON experiment contract.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--code-sha", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = json.loads(Path(args.config).read_text(encoding="utf-8"))
    payload.setdefault("generated_at", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    try:
        report = run_synthetic_smoke(payload, args.output_root, code_sha=args.code_sha)
    except HarnessContractError as exc:
        sys.stderr.write(f"[harness fail-closed] {exc}\n")
        return 1
    sys.stdout.write(
        f"SYNTHETIC_ONLY smoke report written for experiment "
        f"'{report['experiment_id']}' under {args.output_root}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
