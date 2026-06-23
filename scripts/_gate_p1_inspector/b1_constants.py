"""Shared constants for the PR-B.1 read-only inspection layer.

PR-B.1 performs the FIRST real read-only Gate P1 inspection on top of the
PR-B.0 guarded launcher / bootstrap / guards. It is strictly read-only over
candidate raw files (existence / size / streaming SHA-256 / row count /
timestamp boundary / schema-key presence) and AST/source-only over authority
sources. It implements authority + raw inventory + coverage + retention +
resolver only — NOT dependency inventory and NOT pipeline feasibility (those
are PR-B.2, not implemented here).
"""

from __future__ import annotations

from typing import Final

# Protocol §3.1 M1 BA required raw JSON keys. The schema authority module
# derives the same set from production source (AST over load_m1_ba) and HALTs
# on drift versus this list.
PROTOCOL_REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "time",
        "bid_o",
        "bid_h",
        "bid_l",
        "bid_c",
        "ask_o",
        "ask_h",
        "ask_l",
        "ask_c",
    }
)

# Numeric subset of the required fields (everything except the timestamp).
NUMERIC_REQUIRED_FIELDS: Final[frozenset[str]] = PROTOCOL_REQUIRED_FIELDS - {"time"}

# Authority source files (AST/source-text only; never imported).
PAIR_UNIVERSE_CANONICAL_SOURCE: Final[str] = "scripts/stage23_0a_build_outcome_dataset.py"
PAIR_UNIVERSE_SECONDARY_SOURCE: Final[str] = "scripts/stage22_0a_scalp_label_design.py"
SCHEMA_AUTHORITY_SOURCE: Final[str] = "scripts/stage23_0a_build_outcome_dataset.py"

# Candidate spans inspected by PR-B.1 (plan §9). 90d is excluded from the
# candidate set (recorded as non-candidate only).
CANDIDATE_SPANS: Final[tuple[str, ...]] = ("365d", "730d", "3650d")
NON_CANDIDATE_SPANS: Final[tuple[str, ...]] = ("90d",)

# Allowed first-run top-level outcomes. PASS / feasible-for-construction is
# structurally unreachable on the first run (plan §6.2 / §8).
OUTCOME_PARTIAL: Final[str] = "LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY"
OUTCOME_INSUFFICIENT: Final[str] = "LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH"
OUTCOME_RETENTION_UNRESOLVED: Final[str] = "RETENTION_DESTINATION_UNRESOLVED"
ALLOWED_FIRST_RUN_OUTCOMES: Final[frozenset[str]] = frozenset(
    {OUTCOME_PARTIAL, OUTCOME_INSUFFICIENT, OUTCOME_RETENTION_UNRESOLVED}
)

# The construction-review outcome is UNREACHABLE on the first run; if a code
# path ever tries to emit it under first_run_mode the resolver HALTs.
OUTCOME_FEASIBLE_FOR_CONSTRUCTION_REVIEW: Final[str] = (
    "LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW"
)

# Retention classifications permitted on the first run (plan §6.2). The two
# PASS-enabling classifications are forbidden under first_run_mode.
RETENTION_REQUIRES_PROBE: Final[str] = "RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE"
RETENTION_UNRESOLVED: Final[str] = "RETENTION_DESTINATION_UNRESOLVED"
RETENTION_FORBIDDEN_FIRST_RUN: Final[frozenset[str]] = frozenset(
    {
        "IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2",
        "EXISTING_LOCAL_IMMUTABLE_ARCHIVE_VISIBLE_READ_ONLY",
    }
)

# Success / verification labels that must NEVER appear in a PR-B.1 report body.
FORBIDDEN_SUCCESS_LABELS: Final[tuple[str, ...]] = (
    "FORMALLY_VERIFIED",
    "SENTINEL_VERIFICATION_COMPLETE",
    OUTCOME_FEASIBLE_FOR_CONSTRUCTION_REVIEW,
    "TIER1",
    "TIER_1",
)

# Report schema version + stage marker for PR-B.1 artifacts.
B1_SCHEMA_VERSION: Final[str] = "gate-p1-pr-b-1.0"
PR_B_STAGE_B1: Final[str] = "PR-B.1"

# Per-file retention guard mirror (bytes); semantics: per-file ceiling, NOT an
# aggregate budget (plan §6.1). Mirror of
# scripts/_verification_harness/tolerances.py::ARTIFACT_SIZE_GUARD_BYTES.
ARTIFACT_SIZE_GUARD_BYTES: Final[int] = 95 * 1024 * 1024

# OANDA archive manifest (provenance only; existence check, never opened for
# raw bytes by PR-B.1).
OANDA_ARCHIVE_MANIFEST_RELPATH: Final[str] = (
    "artifacts/oanda_archive_2026-05-31/candles_manifest.json"
)
