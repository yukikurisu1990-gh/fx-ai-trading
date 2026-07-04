"""CLI for the guarded ML Step 4 ``365d_BA`` executor — PREFLIGHT ONLY.

Usage:
    python -m scripts.ml_step4.execute_365d_ba --preflight

``--preflight`` runs the wiring preflight + execution plan (metadata only; no
raw data read, no training, no holdout eval, no evidence written) and returns 0.
Requesting real execution (``--execute``, or no flag) fails closed with a
refusal and a non-zero exit: the real run is only available via a separately
authorised execution PR.
"""

from __future__ import annotations

import argparse

from . import evidence, executor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.ml_step4.execute_365d_ba",
        description="Guarded ML Step 4 365d_BA executor (preflight only).",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--preflight",
        action="store_true",
        help="Run wiring preflight + execution plan (no run).",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="Request real execution (refused in this build).",
    )
    args = parser.parse_args(argv)

    if not args.preflight:
        # Default and --execute both refuse: real execution is unavailable here.
        try:
            executor.guarded_execute(dry_run=False)
        except executor.ExecutionRefusedError as exc:
            print(f"REFUSED: {exc}")
        return 2

    plan = executor.guarded_execute(dry_run=True)
    evidence.assert_clean(plan)
    print(evidence.serialise(plan))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
