"""Guarded ML Step 4 execution orchestration (code-only, no run).

Single fail-closed orchestration layer that assembles the reviewed
``scripts/ml_step4/`` primitives into ONE intended route for a future,
separately-authorised first run. It binds the PR #411/#413 wiring residuals
(R-1 bar-granularity boundaries, R-4 single-source label routing, R-5
trading-day definition, R-6 tie-rule provenance, the seed/determinism policy,
the maxDD fixed-notional constant, and NON_DECISION_EXPLORATORY diagnostic
labeling).

**Real execution is not available in this build.** ``guarded_execute`` refuses
any non-dry-run call; the real training/evaluation body is intentionally absent
and must be added by a separate, explicitly-authorised execution PR. This module
reads no real raw data, trains nothing, evaluates no holdout, and writes no
execution evidence.
"""

from __future__ import annotations

from typing import Any, Final

from . import contract, evidence, labels, metrics, split
from .acceptance import REQUIRED_METRIC_PATHS, AcceptanceEvaluator
from .contract import ContractHashes
from .inventory import InventoryError, resolve_inventory

IMPLEMENTATION_STATUS: Final[str] = "ML_STEP4_GUARDED_EXECUTE_WIRING_IMPLEMENTED_NO_RUN"
EXECUTION_NOT_PERFORMED: Final[str] = contract.EXECUTION_NOT_PERFORMED
PRODUCTION_NOT_CLAIMED: Final[str] = contract.PRODUCTION_NOT_CLAIMED

# PR #411/#413 NON_DECISION_EXPLORATORY labeling.
NON_DECISION_EXPLORATORY: Final[str] = "NON_DECISION_EXPLORATORY"
# Diagnostics that must NEVER influence the accept/fail decision.
EXPLORATORY_DIAGNOSTIC_KEYS: Final[tuple[str, ...]] = (
    "feature_importance",
    "calibration",
    "per_threshold_validation_curves",
    "session_contribution",
    "win_rate",
    "avg_win_pips",
    "avg_loss_pips",
    "concurrency",
    "pair_contribution",
)
# The decision-metric keys the acceptance evaluator actually reads (leaf names).
_DECISION_METRIC_LEAVES: Final[frozenset[str]] = frozenset(
    p.split(".")[-1] for p in REQUIRED_METRIC_PATHS
) | {"trade_count", "expectancy_pips", "daily_portfolio_sharpe_annualised"}


class ExecutionRefusedError(RuntimeError):
    """Raised when real execution is requested (not available in this build)."""


class PreflightError(RuntimeError):
    """Raised when a required wiring component is missing at preflight."""


class DiagnosticLabelingError(ValueError):
    """Raised when a non-decision diagnostic is unlabeled or misused."""


# --- Seed / determinism policy (PR #411 B-1 deferral; does NOT touch model) ---


def reproducibility_policy() -> dict[str, Any]:
    """Execution-time reproducibility policy, separate from the model contract.

    Critically, this does NOT add ``random_state`` to the frozen trainer
    contract (that would change ``model_config_hash`` and break the PR #407
    binding). Determinism is handled at the execution layer and reported in the
    future run manifest; where LightGBM randomness cannot be pinned without
    altering ``_LGBM_PARAMS`` it is declared bounded, not bitwise-guaranteed.
    """
    return {
        "alters_model_config_hash": False,
        "deterministic_data_ordering": True,
        "validation_threshold_selection": "fixed_deterministic",
        "split_determinism": "m1_bar_index_boundaries",
        "seeds_recorded_at_runtime": ["python", "numpy", "lightgbm_if_supported"],
        "package_versions_recorded_at_runtime": True,
        "reproducibility_level": "bounded_not_bitwise_guaranteed",
        "note": (
            "LightGBM training may retain platform/thread-level nondeterminism "
            "that cannot be removed without changing the frozen _LGBM_PARAMS; "
            "the future run records all seeds and versions actually used and "
            "discloses this as a reproducibility limitation."
        ),
    }


def assert_reproducibility_recorded(meta: dict[str, Any]) -> None:
    """Fail closed if the reproducibility policy is absent/incomplete."""
    rp = meta.get("reproducibility_policy")
    required = {"reproducibility_level", "deterministic_data_ordering", "seeds_recorded_at_runtime"}
    if not isinstance(rp, dict) or not required.issubset(rp):
        raise PreflightError("reproducibility policy missing or incomplete")
    if rp.get("alters_model_config_hash") is not False:
        raise PreflightError("reproducibility policy must not alter model_config_hash")


def assert_maxdd_notional(meta: dict[str, Any]) -> None:
    """Fail closed if the maxDD fixed-notional constant is absent/non-positive."""
    val = meta.get("evaluation", {}).get("fixed_notional_equity_pips")
    if not isinstance(val, (int, float)) or val <= 0:
        raise PreflightError("maxDD fixed-notional constant missing or non-positive")


# --- Diagnostic labeling (NON_DECISION_EXPLORATORY) ---------------------------


def label_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Wrap each diagnostic with the NON_DECISION_EXPLORATORY classification."""
    return {
        key: {"classification": NON_DECISION_EXPLORATORY, "value": value}
        for key, value in diagnostics.items()
    }


def assert_diagnostics_labeled(diagnostics: dict[str, Any]) -> None:
    """Fail closed if any diagnostic is missing the NON_DECISION_EXPLORATORY tag.

    Also fails closed if a diagnostic key collides with a decision-metric leaf
    (a decision metric must never be smuggled in as exploratory), and if any
    decision-metric leaf is presented as a diagnostic.
    """
    for key, entry in diagnostics.items():
        if not isinstance(entry, dict) or entry.get("classification") != NON_DECISION_EXPLORATORY:
            raise DiagnosticLabelingError(
                f"diagnostic {key!r} not labeled NON_DECISION_EXPLORATORY"
            )
        if key in _DECISION_METRIC_LEAVES:
            raise DiagnosticLabelingError(f"decision metric {key!r} mislabeled as exploratory")


def assert_diagnostics_excluded_from_decision(acceptance_result: dict[str, Any]) -> None:
    """Confirm no NON_DECISION_EXPLORATORY key appears among evaluated criteria."""
    criteria = acceptance_result.get("criteria", {})
    leaked = set(criteria) & set(EXPLORATORY_DIAGNOSTIC_KEYS)
    if leaked:
        raise DiagnosticLabelingError(
            f"exploratory diagnostics influenced acceptance: {sorted(leaked)}"
        )


# --- Preflight hard-gate orchestration ---------------------------------------

PREFLIGHT_GATES: Final[tuple[str, ...]] = (
    "code_sha_recordable",
    "config_hash_available",
    "feature_config_hash_available",
    "model_config_hash_available",
    "threshold_tie_rule_provenance_available",
    "maxdd_fixed_notional_available",
    "reproducibility_policy_available",
    "label_contract_identity_available",
    "evidence_dir_policy_available",
    "inventory_resolver_available",
    "expected_file_count_and_bytes_available",
    "split_policy_available",
    "metrics_evaluator_available",
    "acceptance_evaluator_available",
    "evidence_writer_available",
    "diagnostic_labeling_policy_available",
)


def run_preflight(inventory_path: str | None = None) -> dict[str, Any]:
    """Verify wiring components WITHOUT reading real raw data or checksumming.

    Resolves committed inventory METADATA only (file count + total bytes); does
    not open, hash, or read any raw candle file. Returns a scrub-clean report;
    any missing component yields a refused status.
    """
    gates: dict[str, str] = {}
    hashes = ContractHashes()

    gates["code_sha_recordable"] = "RECORDABLE_AT_RUNTIME"
    gates["config_hash_available"] = "PRESENT" if hashes.config_hash else "MISSING"
    gates["feature_config_hash_available"] = "PRESENT" if hashes.feature_config_hash else "MISSING"
    gates["model_config_hash_available"] = "PRESENT" if hashes.model_config_hash else "MISSING"
    gates["threshold_tie_rule_provenance_available"] = (
        "PRESENT" if contract.threshold_config().get("tie_rule") else "MISSING"
    )
    gates["maxdd_fixed_notional_available"] = (
        "PRESENT" if contract.FIXED_NOTIONAL_EQUITY_PIPS > 0 else "MISSING"
    )
    gates["reproducibility_policy_available"] = (
        "PRESENT" if reproducibility_policy().get("reproducibility_level") else "MISSING"
    )
    gates["label_contract_identity_available"] = (
        "PRESENT" if labels.label_contract_identity().get("label_contract_id") else "MISSING"
    )
    gates["evidence_dir_policy_available"] = (
        "PRESENT"
        if evidence.EXECUTION_EVIDENCE_DIR and evidence.EXPECTED_EVIDENCE_FILES
        else "MISSING"
    )
    gates["split_policy_available"] = "PRESENT" if callable(split.bar_index_split) else "MISSING"
    gates["metrics_evaluator_available"] = "PRESENT" if callable(metrics.compute_all) else "MISSING"
    gates["acceptance_evaluator_available"] = "PRESENT" if AcceptanceEvaluator else "MISSING"
    gates["evidence_writer_available"] = "PRESENT" if callable(evidence.write_report) else "MISSING"
    gates["diagnostic_labeling_policy_available"] = (
        "PRESENT" if NON_DECISION_EXPLORATORY else "MISSING"
    )

    # Inventory METADATA only (count + bytes; NO file checksums, NO raw read).
    try:
        records = resolve_inventory(inventory_path)
        gates["inventory_resolver_available"] = "PRESENT"
        gates["expected_file_count_and_bytes_available"] = (
            "PRESENT"
            if len(records) == contract.EXPECTED_FILE_COUNT
            and sum(r.size_bytes for r in records) == contract.EXPECTED_TOTAL_BYTES
            else "MISMATCH"
        )
        inventory_meta = {
            "resolved": True,
            "file_count": len(records),
            "total_bytes": sum(r.size_bytes for r in records),
            "checksums_computed": False,
            "raw_files_read": False,
        }
    except InventoryError as exc:
        gates["inventory_resolver_available"] = "MISSING"
        gates["expected_file_count_and_bytes_available"] = "MISSING"
        inventory_meta = {"resolved": False, "detail": str(exc)}

    missing = [
        g for g in PREFLIGHT_GATES if gates.get(g) not in ("PRESENT", "RECORDABLE_AT_RUNTIME")
    ]
    status = "PREFLIGHT_WIRING_COMPLETE_NO_RUN" if not missing else "PREFLIGHT_REFUSED_INCOMPLETE"
    report = {
        "status": status,
        "gates": gates,
        "missing_or_incomplete": missing,
        "inventory_metadata": inventory_meta,
        "reproducibility_policy": reproducibility_policy(),
        "evaluation": contract.contract_dict()["evaluation"],
        "raw_data_read": False,
        "checksums_computed": False,
        "model_trained": False,
        "holdout_evaluated": False,
        "evidence_written": False,
    }
    # metadata-only guarantee.
    assert_reproducibility_recorded(report)
    assert_maxdd_notional(report)
    evidence.assert_clean(report)
    return report


def build_execution_plan(inventory_path: str | None = None) -> dict[str, Any]:
    """Full, scrub-clean execution-plan metadata for a FUTURE authorised run."""
    hashes = ContractHashes()
    plan = {
        "implementation_status": IMPLEMENTATION_STATUS,
        "execution_status": EXECUTION_NOT_PERFORMED,
        "production_status": PRODUCTION_NOT_CLAIMED,
        "epoch_id": contract.EPOCH_ID,
        "span": contract.SPAN,
        "bound_contracts": {"pre_registration": "PR #407", "execution_authorisation": "PR #408"},
        "hashes": {
            **hashes.as_dict(),
            "threshold_config_hash": contract.threshold_config_hash(),
        },
        "contract": contract.contract_dict(),
        "residual_bindings": {
            "R1_boundary_rule": (
                "m1_bar_index [start, end); purge=21 bars; sub-second/non-aligned rejected"
            ),
            "R4_label_routing": labels.label_contract_identity(),
            "R5_trading_day": contract.TRADING_DAY_DEFINITION,
            "R6_threshold_tie_rule": contract.THRESHOLD_TIE_RULE,
            "seed_determinism": reproducibility_policy()["reproducibility_level"],
            "maxdd_fixed_notional_equity_pips": contract.FIXED_NOTIONAL_EQUITY_PIPS,
            "diagnostic_labeling": NON_DECISION_EXPLORATORY,
        },
        "evidence_schema": {
            "directory": evidence.EXECUTION_EVIDENCE_DIR,
            "files": list(evidence.EXPECTED_EVIDENCE_FILES),
            "metadata_only": True,
        },
        "preflight": run_preflight(inventory_path),
        "execution_performed": False,
        "raw_data_read": False,
        "model_trained": False,
        "holdout_evaluated": False,
        "evidence_written": False,
    }
    evidence.assert_clean(plan)
    return plan


def guarded_execute(
    *,
    dry_run: bool = True,
    allow_real_execution: bool = False,
    inventory_path: str | None = None,
) -> dict[str, Any]:
    """The single intended route to a future real run — REFUSED in this build.

    ``dry_run=True`` returns the execution plan + preflight (no side effects).
    Any non-dry-run call fails closed: the real training/evaluation body is
    intentionally absent and must be added by a separate authorised execution
    PR. ``allow_real_execution`` is accepted for a future signature but is still
    refused here.
    """
    if not dry_run or allow_real_execution:
        raise ExecutionRefusedError(
            "real ML Step 4 execution is not available in this build; a separately "
            "authorised execution PR must implement the guarded run body. Use "
            "dry_run=True for planning/preflight."
        )
    return build_execution_plan(inventory_path)
