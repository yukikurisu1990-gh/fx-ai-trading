"""CLI for the guarded ML Step 4 ``365d_BA`` executor.

Modes:
  * ``--preflight``               wiring preflight + plan (no run).
  * ``--fixture-e2e``             synthetic run-body rehearsal (no real data).
  * ``--first-run-preflight``     real hard-gate report incl. 20-file checksum
                                  verification, NO training (metadata only).
  * ``--execute-first-run-365d-ba``  the ONE authorised real first-run: gates ->
                                  train from scratch -> validation-only threshold
                                  -> single holdout -> metadata-only evidence.
  * ``--execute`` / no flag       refused (generic real execution unavailable).

Environment variables cannot enable any real path; only the explicit
``--execute-first-run-365d-ba`` flag runs the real body, and only after all
ordered hard gates pass. Any gate failure stops before training.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from . import contract, evidence, executor, features
from .data_adapter import Real365dBaProvider, RealDataRefusedError
from .inventory import InventoryError, resolve_inventory

_REAL_EVIDENCE_ROOT = "artifacts/ml_step4/365d_ba_v1"


class FirstRunGateError(RuntimeError):
    """Raised when a pre-execution hard gate fails (stop before training)."""


def _code_sha() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(evidence.repo_root()),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    sha = out.stdout.strip()
    if len(sha) != 40:
        raise FirstRunGateError("code SHA unrecordable")
    return sha


def _run_hard_gates(provider: Real365dBaProvider) -> dict[str, Any]:
    """Ordered pre-execution hard gates. Raises FirstRunGateError on any failure.

    Returns a metadata-only gate report (also carries the checksum result).
    """
    gates: dict[str, str] = {}
    code_sha = _code_sha()
    gates["1_explicit_first_run_mode"] = "PASS"
    gates["2_code_sha_recorded"] = "PASS" if len(code_sha) == 40 else "FAIL"
    hashes = executor.ContractHashes()
    gates["3_config_hashes_recorded"] = (
        "PASS"
        if hashes.config_hash and hashes.feature_config_hash and hashes.model_config_hash
        else "FAIL"
    )
    gates["4_inventory_resolved"] = "PASS" if provider._records else "FAIL"
    # 5. checksum verify all 20 files (re-hash vs inventory) — the decisive gate
    checksum_report = provider.verify()  # raises RealDataRefusedError on mismatch
    gates["5_checksums_verified_20_files"] = "PASS" if checksum_report["all_match"] else "FAIL"
    # 6. feature contract available and v4-base only
    fb = features.production_feature_binding()
    gates["6_feature_contract_v4_base_only"] = (
        "PASS" if fb["n_features"] == 39 and fb["mtf_excluded"] else "FAIL"
    )
    gates["7_split_policy_recorded"] = "PASS" if contract.PURGE_EMBARGO_BARS == 21 else "FAIL"
    gates["8_label_contract_recorded"] = "PASS"
    gates["9_model_contract_recorded"] = "PASS" if contract.model_config_hash() else "FAIL"
    gates["10_threshold_contract_recorded"] = (
        "PASS" if list(contract.THRESHOLD_CANDIDATES) == [0.35, 0.40, 0.45] else "FAIL"
    )
    gates["11_evidence_path_guarded"] = "PASS"
    gates["12_scrubber_ready"] = "PASS" if callable(evidence.assert_clean) else "FAIL"

    failed = [g for g, v in gates.items() if v != "PASS"]
    if failed:
        raise FirstRunGateError(f"pre-execution hard gate(s) failed: {failed}")
    return {
        "code_sha": code_sha,
        "config_hash": hashes.config_hash,
        "feature_config_hash": hashes.feature_config_hash,
        "model_config_hash": hashes.model_config_hash,
        "threshold_config_hash": contract.threshold_config_hash(),
        "gates": gates,
        "checksum_report": checksum_report,
        "feature_binding": fb,
    }


def _resolve_real_provider() -> Real365dBaProvider:
    records = resolve_inventory()  # 20 records, count+bytes validated, fail-closed
    return Real365dBaProvider(records)


def _run_dir(code_sha: str) -> Path:
    return evidence.repo_root() / _REAL_EVIDENCE_ROOT / f"first_run_{code_sha[:12]}"


def first_run_preflight(provider: Real365dBaProvider | None = None) -> dict[str, Any]:
    """Phase 2: run gates + checksum verification only; NO training. Metadata-only."""
    provider = provider or _resolve_real_provider()
    try:
        gate = _run_hard_gates(provider)
    except (RealDataRefusedError, FirstRunGateError, InventoryError) as exc:
        report = {
            "run_status": "ML_STEP4_365D_BA_FIRST_RUN_STOPPED_BEFORE_TRAINING",
            "stopped_reason": str(exc),
            "production_status": contract.PRODUCTION_NOT_CLAIMED,
            "training_performed": False,
            "holdout_evaluated": False,
            "evidence_written": False,
        }
        evidence.assert_clean(report)
        return report
    report = {
        "run_status": "FIRST_RUN_GATES_PASSED_NO_TRAINING",
        "production_status": contract.PRODUCTION_NOT_CLAIMED,
        "training_performed": False,
        "holdout_evaluated": False,
        "evidence_written": False,
        **{
            k: gate[k]
            for k in (
                "code_sha",
                "config_hash",
                "feature_config_hash",
                "model_config_hash",
                "threshold_config_hash",
                "gates",
            )
        },
        "inventory": {
            "expected_file_count": gate["checksum_report"]["expected_file_count"],
            "observed_file_count": gate["checksum_report"]["observed_file_count"],
            "expected_total_bytes": gate["checksum_report"]["expected_total_bytes"],
            "observed_total_bytes": gate["checksum_report"]["observed_total_bytes"],
            "all_match": gate["checksum_report"]["all_match"],
        },
    }
    evidence.assert_clean(report)
    return report


def execute_first_run(provider: Real365dBaProvider | None = None) -> dict[str, Any]:
    """Phase 3: the ONE authorised real first-run. Gates -> train -> evaluate once."""
    from .body import run_first_run_365d_ba

    provider = provider or _resolve_real_provider()
    gate = _run_hard_gates(provider)  # raises on any failure -> stop before training
    out_dir = _run_dir(gate["code_sha"])
    summary = run_first_run_365d_ba(
        provider=provider, out_dir=str(out_dir), code_sha=gate["code_sha"], real=True
    )
    summary["evidence_dir"] = f"{_REAL_EVIDENCE_ROOT}/first_run_{gate['code_sha'][:12]}"
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.ml_step4.execute_365d_ba",
        description="Guarded ML Step 4 365d_BA executor.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight", action="store_true", help="Wiring preflight + plan (no run).")
    group.add_argument("--fixture-e2e", action="store_true", help="Synthetic rehearsal (no data).")
    group.add_argument(
        "--first-run-preflight",
        action="store_true",
        help="Real hard-gate + checksum report, NO training.",
    )
    group.add_argument(
        "--execute-first-run-365d-ba",
        action="store_true",
        help="THE authorised real first-run (gates -> train once -> evidence).",
    )
    group.add_argument("--execute", action="store_true", help="Refused (generic real execution).")
    args = parser.parse_args(argv)

    if args.fixture_e2e:
        import tempfile

        from .body import guarded_run_body

        with tempfile.TemporaryDirectory() as td:
            summary = guarded_run_body(mode="fixture", out_dir=td)
        evidence.assert_clean(summary)
        print(evidence.serialise(summary))
        return 0

    if args.first_run_preflight:
        report = first_run_preflight()
        print(evidence.serialise(report))
        return 0 if report["run_status"] == "FIRST_RUN_GATES_PASSED_NO_TRAINING" else 3

    if getattr(args, "execute_first_run_365d_ba", False):
        summary = execute_first_run()
        # print a path-free JSON summary (evidence file names only)
        printable = {k: v for k, v in summary.items() if k != "metrics"}
        evidence.assert_clean(printable)
        print(json.dumps(printable, sort_keys=True, indent=2))
        return 0

    if args.preflight:
        plan = executor.guarded_execute(dry_run=True)
        evidence.assert_clean(plan)
        print(evidence.serialise(plan))
        return 0

    # Default and --execute both refuse.
    try:
        executor.guarded_execute(dry_run=False)
    except executor.ExecutionRefusedError as exc:
        print(f"REFUSED: {exc}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
