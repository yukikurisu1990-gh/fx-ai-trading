"""CLI entrypoint for the ML Step 4 ``365d_BA`` executor — DRY-RUN ONLY.

Usage:
    python -m scripts.ml_step4.run_365d_ba --dry-run

Dry-run validates contract wiring and reports what a future, separately-
authorised execution would require. It DOES NOT read real ``365d_BA`` raw data,
DOES NOT train a model, DOES NOT evaluate the holdout, and DOES NOT write real
execution evidence. There is no non-dry-run path wired in this build: invoking
without ``--dry-run`` fails closed (real execution is not available here).
"""

from __future__ import annotations

import argparse
from typing import Any

from . import contract, evidence
from .contract import ContractHashes

# The 16 pre-execution hard gates (PR #408 §3), reported as "required at
# execution, not performed" during dry-run.
_HARD_GATES: tuple[str, ...] = (
    "working_tree_clean",
    "code_sha_recorded",
    "pr407_pr408_present_on_master",
    "epoch_resolved",
    "prb1_inventory_resolved",
    "reverify_20_file_sha256_and_sizes",
    "total_bytes_1481715517",
    "common_window_reproducible",
    "chronological_70_15_15_reproducible",
    "purge_embargo_horizon_plus_1",
    "f2_label_pnl_enforceable",
    "f5_provenance_satisfiable",
    "f8_train_serve_satisfiable",
    "dependency_metadata_safe_no_env_dump",
    "evidence_dir_clean_or_creatable",
    "no_raw_path_cred_env_committed",
)


def _inventory_status() -> dict[str, Any]:
    """Resolve the committed inventory METADATA (no raw candle rows read)."""
    from .inventory import InventoryError, resolve_inventory

    try:
        records = resolve_inventory()
    except InventoryError as exc:
        return {"resolved": False, "detail": str(exc)}
    return {
        "resolved": True,
        "file_count": len(records),
        "expected_file_count": contract.EXPECTED_FILE_COUNT,
        "total_bytes": sum(r.size_bytes for r in records),
        "expected_total_bytes": contract.EXPECTED_TOTAL_BYTES,
        "total_bytes_match": sum(r.size_bytes for r in records) == contract.EXPECTED_TOTAL_BYTES,
    }


def build_dry_run_summary() -> dict[str, Any]:
    """Metadata-only dry-run summary (scrub-clean, no execution)."""
    hashes = ContractHashes()
    return {
        "mode": "dry_run",
        "implementation_status": contract.IMPLEMENTATION_STATUS,
        "execution_status": contract.EXECUTION_NOT_PERFORMED,
        "production_status": contract.PRODUCTION_NOT_CLAIMED,
        "epoch_id": contract.EPOCH_ID,
        "span": contract.SPAN,
        "hashes": hashes.as_dict(),
        "inventory": _inventory_status(),
        "threshold_candidates": list(contract.THRESHOLD_CANDIDATES),
        "primary_cost_cell_pips": contract.PRIMARY_COST_CELL_PIPS,
        "pre_execution_hard_gates": {
            gate: "REQUIRED_AT_EXECUTION_NOT_PERFORMED" for gate in _HARD_GATES
        },
        "execution_performed": False,
        "raw_data_read": False,
        "model_trained": False,
        "holdout_evaluated": False,
        "evidence_written": False,
        "note": (
            "Dry-run validated contract wiring only. No raw data was read, no "
            "model was trained, no holdout was evaluated, and no execution "
            "evidence was written. A separately-authorised execution PR is "
            "required to run the contract."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.ml_step4.run_365d_ba",
        description="ML Step 4 365d_BA executor (dry-run only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate contract wiring without reading data or training.",
    )
    args = parser.parse_args(argv)

    if not args.dry_run:
        print(
            "REFUSED: real execution is not available in this build. "
            "Re-run with --dry-run. Execution requires a separately-authorised "
            "execution PR."
        )
        return 2

    summary = build_dry_run_summary()
    # Metadata-only guarantee: the summary must be scrub-clean.
    evidence.assert_clean(summary)
    print(evidence.serialise(summary))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
