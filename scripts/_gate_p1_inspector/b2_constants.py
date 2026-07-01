"""Shared constants for the PR-B.2 read-only inspection layer.

PR-B.2 completes the read-only Gate P1 inspection surface with two static,
AST/source-only, metadata-only inspections:

* dependency inventory  — static import graph of representative consumers,
* pipeline feasibility  — static references + committed PR-B.1 evidence check.

PR-B.2 imports NO production module, executes NO production code, runs NO
pipeline / model / backtest, reads NO raw data, and computes NO trading metric.
It changes NO PR-B.1 outcome.
"""

from __future__ import annotations

from typing import Final

B2_SCHEMA_VERSION: Final[str] = "gate-p1-pr-b-2.0"
PR_B_STAGE_B2: Final[str] = "PR-B.2"

# --- Representative consumer sources inspected by the dependency inventory ---
# These are AST-parsed as source text only (never imported). They are the same
# authority sources PR-B.1 already reads, and are representative of what a later
# ML experiment harness would build on.
CONSUMER_REGISTRY: Final[tuple[str, ...]] = (
    "scripts/stage23_0a_build_outcome_dataset.py",
    "scripts/stage22_0a_scalp_label_design.py",
)

# --- Static pipeline reference targets (functions / constants located by AST) ---
PIPELINE_REFERENCE_TARGETS: Final[tuple[tuple[str, str], ...]] = (
    ("scripts/stage23_0a_build_outcome_dataset.py", "load_m1_ba"),
    ("scripts/stage23_0a_build_outcome_dataset.py", "aggregate_m1_to_tf"),
    ("scripts/stage23_0a_build_outcome_dataset.py", "PAIRS_20"),
    ("scripts/stage22_0a_scalp_label_design.py", "PAIRS_20"),
)

# --- PR-B.1 committed evidence consumed (read-only) by pipeline feasibility ---
PR_B1_EVIDENCE_SPANS: Final[tuple[str, ...]] = ("365d_BA", "730d_BA", "3650d_BA")
PR_B1_EVIDENCE_DIRS: Final[dict[str, str]] = {
    "365d_BA": "artifacts/gate_p1_pr_b/firstrun_365d_ba",
    "730d_BA": "artifacts/gate_p1_pr_b/firstrun_730d_ba",
    "3650d_BA": "artifacts/gate_p1_pr_b/firstrun_3650d_ba",
}
PR_B1_EXPECTED_OUTCOME: Final[str] = "LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY"
PR_B1_EXPECTED_RETENTION: Final[str] = "RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE"

# --- Dependency inventory controlled vocabulary ---
DEP_OBSERVED: Final[str] = "STATIC_DEPENDENCY_OBSERVED"
DEP_UNRESOLVED: Final[str] = "STATIC_DEPENDENCY_UNRESOLVED"
DEP_FORBIDDEN_TO_EXECUTE: Final[str] = "STATIC_DEPENDENCY_FORBIDDEN_TO_EXECUTE_IN_GATE_P1"
DEP_OUT_OF_SCOPE: Final[str] = "STATIC_DEPENDENCY_OUT_OF_SCOPE_FOR_PR_B2"
DEPENDENCY_LABELS: Final[frozenset[str]] = frozenset(
    {DEP_OBSERVED, DEP_UNRESOLVED, DEP_FORBIDDEN_TO_EXECUTE, DEP_OUT_OF_SCOPE}
)

# Top-level module-name substrings marking a production EXECUTION surface that
# Gate P1 must never run (broker / quote feed / OANDA / network / subprocess /
# model training / production entrypoints). Presence is static-only information;
# it is never a reason to import or execute.
FORBIDDEN_EXECUTION_SURFACES: Final[tuple[str, ...]] = (
    "broker",
    "oanda",
    "quote",
    "supervisor",
    "run_exit_gate",
    "run_paper",
    "run_live",
    "fetch_oanda",
    "requests",
    "socket",
    "urllib",
    "http",
    "subprocess",
    "torch",
    "lightgbm",
    "sklearn",
)

_INTERNAL_PREFIXES: Final[tuple[str, ...]] = ("scripts", "src", "fx_ai_trading")

# --- Pipeline feasibility controlled vocabulary ---
PIPE_PATH_OBSERVED: Final[str] = "STATIC_PIPELINE_PATH_OBSERVED"
PIPE_PATH_PARTIAL: Final[str] = "STATIC_PIPELINE_PATH_PARTIAL"
PIPE_PATH_UNRESOLVED: Final[str] = "STATIC_PIPELINE_PATH_UNRESOLVED"
PIPE_EXECUTION_NOT_AUTHORISED: Final[str] = "PIPELINE_EXECUTION_NOT_AUTHORISED"
PIPE_NEW_EPOCH_NOT_AUTHORISED: Final[str] = "NEW_EPOCH_CONSTRUCTION_NOT_AUTHORISED"
PIPE_RETENTION_PROBE_REQUIRED: Final[str] = "RETENTION_PROBE_REQUIRED_BEFORE_BYTE_ADMISSIBILITY"
PIPELINE_LABELS: Final[frozenset[str]] = frozenset(
    {
        PIPE_PATH_OBSERVED,
        PIPE_PATH_PARTIAL,
        PIPE_PATH_UNRESOLVED,
        PIPE_EXECUTION_NOT_AUTHORISED,
        PIPE_NEW_EPOCH_NOT_AUTHORISED,
        PIPE_RETENTION_PROBE_REQUIRED,
    }
)

# --- Top-level PR-B.2 outcome controlled vocabulary (PASS unreachable) ---
OUTCOME_OBSERVED_RETENTION_PROBE_REQUIRED: Final[str] = (
    "GATE_P1_READONLY_SURFACE_STATICALLY_OBSERVED_RETENTION_PROBE_REQUIRED"
)
OUTCOME_PARTIAL_STATIC_FEASIBILITY: Final[str] = (
    "GATE_P1_READONLY_SURFACE_PARTIAL_STATIC_FEASIBILITY"
)
OUTCOME_INSUFFICIENT_STATIC_EVIDENCE: Final[str] = (
    "GATE_P1_READONLY_SURFACE_INSUFFICIENT_STATIC_EVIDENCE"
)
OUTCOME_HALTED: Final[str] = "GATE_P1_READONLY_SURFACE_HALTED"
ALLOWED_B2_OUTCOMES: Final[frozenset[str]] = frozenset(
    {
        OUTCOME_OBSERVED_RETENTION_PROBE_REQUIRED,
        OUTCOME_PARTIAL_STATIC_FEASIBILITY,
        OUTCOME_INSUFFICIENT_STATIC_EVIDENCE,
        OUTCOME_HALTED,
    }
)

# --- Labels/content that must never appear in a PR-B.2 report ---
FORBIDDEN_REPORT_TOKENS: Final[tuple[str, ...]] = (
    "FORMALLY_VERIFIED",
    "SENTINEL_VERIFICATION_COMPLETE",
    "LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW",
    "TIER1",
    "TIER_1",
    "BYTE_ADMISSIBILITY_APPROVED",
    "T2_EXECUTION_AUTHORISED_TRUE",
)


def is_internal_module(top_level: str) -> bool:
    return top_level in _INTERNAL_PREFIXES
