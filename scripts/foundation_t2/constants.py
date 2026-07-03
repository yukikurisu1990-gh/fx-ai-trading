"""Controlled vocabulary + patterns for the Foundation T2 harness."""

from __future__ import annotations

import re
from typing import Final

T2_CONTRACT_VERSION: Final[str] = "foundation-t2.v1"

# Only ONE primary logical destination is in scope for this PR. The real
# endpoint / bucket / account identifiers are never committed; a stable
# non-secret alias is used in all evidence.
PRIMARY_DESTINATION_ALIAS: Final[str] = "T2_PRIMARY_R2"

# Candidate spans + their PR-B.1 committed evidence (read-only metadata only).
T2_SPANS: Final[tuple[str, ...]] = ("365d_BA", "730d_BA", "3650d_BA")
PR_B1_RAW_INVENTORY: Final[dict[str, str]] = {
    "365d_BA": "artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json",
    "730d_BA": "artifacts/gate_p1_pr_b/firstrun_730d_ba/raw_inventory_730d_BA.json",
    "3650d_BA": "artifacts/gate_p1_pr_b/firstrun_3650d_ba/raw_inventory_3650d_BA.json",
}

# --- Allowed positive / neutral statuses ---
T2_EXECUTION_ATTEMPTED_WITH_AUTHORISATION: Final[str] = "T2_EXECUTION_ATTEMPTED_WITH_AUTHORISATION"
T2_MULTI_SPAN_MANIFEST_PREPARED: Final[str] = "T2_MULTI_SPAN_MANIFEST_PREPARED"
T2_DEPOSIT_ATTEMPTED: Final[str] = "T2_DEPOSIT_ATTEMPTED"
T2_RESTORE_ATTEMPTED: Final[str] = "T2_RESTORE_ATTEMPTED"
T2_ROUNDTRIP_METADATA_CAPTURED: Final[str] = "T2_ROUNDTRIP_METADATA_CAPTURED"
T2_ROUNDTRIP_MATCH_OBSERVED: Final[str] = "T2_ROUNDTRIP_MATCH_OBSERVED"
T2_EVIDENCE_METADATA_ONLY: Final[str] = "T2_EVIDENCE_METADATA_ONLY"
T2_EVIDENCE_SCRUBBED: Final[str] = "T2_EVIDENCE_SCRUBBED"

# --- Allowed non-authorisation statuses ---
NON_AUTHORISATION_STATUSES: Final[tuple[str, ...]] = (
    "BYTE_ADMISSIBILITY_NOT_APPROVED",
    "NEW_EPOCH_NOT_AUTHORISED",
    "ML_STEP4_NOT_AUTHORISED",
    "PRODUCTION_CHANGE_NOT_AUTHORISED",
    "MODEL_TRAINING_NOT_AUTHORISED",
    "BACKTEST_NOT_AUTHORISED",
    "TRADING_METRICS_NOT_COMPUTED",
    "LLM_INTEGRATION_NOT_AUTHORISED",
)

# --- Allowed failure / partial / not-performed statuses ---
T2_EXECUTION_STOPPED_BEFORE_DEPOSIT: Final[str] = "T2_EXECUTION_STOPPED_BEFORE_DEPOSIT"
T2_DESTINATION_AMBIGUOUS: Final[str] = "T2_DESTINATION_AMBIGUOUS"
T2_CREDENTIALS_UNAVAILABLE: Final[str] = "T2_CREDENTIALS_UNAVAILABLE"
T2_FILESET_AMBIGUOUS: Final[str] = "T2_FILESET_AMBIGUOUS"
T2_DEPOSIT_PARTIAL: Final[str] = "T2_DEPOSIT_PARTIAL"
T2_RESTORE_PARTIAL: Final[str] = "T2_RESTORE_PARTIAL"
T2_ROUNDTRIP_MISMATCH: Final[str] = "T2_ROUNDTRIP_MISMATCH"
T2_EVIDENCE_SCRUB_FAILED: Final[str] = "T2_EVIDENCE_SCRUB_FAILED"
T2_REMOTE_STATE_UNCERTAIN: Final[str] = "T2_REMOTE_STATE_UNCERTAIN"
# Explicit "did-not-happen" statuses for the pre-deposit-stop path.
T2_DEPOSIT_NOT_PERFORMED: Final[str] = "T2_DEPOSIT_NOT_PERFORMED"
T2_RESTORE_NOT_PERFORMED: Final[str] = "T2_RESTORE_NOT_PERFORMED"
T2_ROUNDTRIP_NOT_PERFORMED: Final[str] = "T2_ROUNDTRIP_NOT_PERFORMED"
RETENTION_PROBE_REMAINS_UNRESOLVED: Final[str] = "RETENTION_PROBE_REMAINS_UNRESOLVED"

# Per-span real-round-trip-observed statuses (emitted ONLY on a real, verified
# cloud round-trip — never for a synthetic/local-mock harness run).
SPAN_ROUNDTRIP_OBSERVED: Final[dict[str, str]] = {
    "365d_BA": "T2_SPAN_365D_BA_ROUNDTRIP_OBSERVED",
    "730d_BA": "T2_SPAN_730D_BA_ROUNDTRIP_OBSERVED",
    "3650d_BA": "T2_SPAN_3650D_BA_ROUNDTRIP_OBSERVED",
}

# Backup HDD / IPFS sidecar are NOT executed in this PR.
BACKUP_HDD_STATUS: Final[str] = "BACKUP_HDD_DEPOSIT_NOT_EXECUTED_DEFERRED"
IPFS_SIDECAR_STATUS: Final[str] = "IPFS_SIDECAR_PUBLICATION_NOT_EXECUTED_DEFERRED"

# --- T2_PRIMARY_R2 adapter readiness statuses (support for a FUTURE, separately
# authorised Phase C1 re-run). None of these is a round-trip success status;
# a real round-trip is emitted only by an authorised real run, never here. ---
T2_PRIMARY_R2_ADAPTER_WIRED_FOR_FUTURE_USE: Final[str] = (
    "T2_PRIMARY_R2_ADAPTER_WIRED_FOR_FUTURE_USE"
)
T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS: Final[str] = "T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS"
T2_PRIMARY_R2_MOCK_ROUNDTRIP_TESTED: Final[str] = "T2_PRIMARY_R2_MOCK_ROUNDTRIP_TESTED"
T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT: Final[str] = "T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT"
T2_PRIMARY_R2_CONFIG_INCOMPLETE: Final[str] = "T2_PRIMARY_R2_CONFIG_INCOMPLETE"
T2_PRIMARY_R2_OBJECT_LOCK_NOT_OBSERVED: Final[str] = "T2_PRIMARY_R2_OBJECT_LOCK_NOT_OBSERVED"
T2_PRIMARY_R2_OBJECT_LOCK_OBSERVED: Final[str] = "T2_PRIMARY_R2_OBJECT_LOCK_OBSERVED"
# Runtime client-construction readiness (a real client is built OUTSIDE this
# package, in scripts/t2_r2_runtime.py, from operator-provisioned config). None
# of these is a round-trip success status.
T2_PRIMARY_R2_RUNTIME_CLIENT_READY: Final[str] = "T2_PRIMARY_R2_RUNTIME_CLIENT_READY"
T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED: Final[str] = "T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED"
T2_PRIMARY_R2_DRY_RUN_READY_NO_OBJECTS_TOUCHED: Final[str] = (
    "T2_PRIMARY_R2_DRY_RUN_READY_NO_OBJECTS_TOUCHED"
)
REAL_T2_EXECUTION_NOT_PERFORMED: Final[str] = "REAL_T2_EXECUTION_NOT_PERFORMED"
PHASE_C1_RERUN_NOT_AUTHORISED: Final[str] = "PHASE_C1_RERUN_NOT_AUTHORISED"

# Required credential env-var NAMES for the real R2 destination. The adapter
# checks NAME PRESENCE ONLY — it never reads, prints, logs, or serialises the
# VALUES. Values, if present, are handed straight to a runtime client and never
# touched by this module.
R2_CREDENTIAL_ENV_VARS: Final[tuple[str, ...]] = (
    "T2_PRIMARY_R2_ACCESS_KEY_ID",
    "T2_PRIMARY_R2_SECRET_ACCESS_KEY",
)
# Required non-secret destination config env-var NAMES (bucket / endpoint may be
# provided via env at execution time; still checked by presence only here).
R2_CONFIG_ENV_VARS: Final[tuple[str, ...]] = (
    "T2_PRIMARY_R2_BUCKET",
    "T2_PRIMARY_R2_ENDPOINT",
)

# Phase C1 pilot is 365d_BA ONLY. Object-key construction for phase_c1 refuses
# the expansion spans unless a later command explicitly overrides.
PHASE_C1_ALLOWED_SPANS: Final[tuple[str, ...]] = ("365d_BA",)

# Object-key namespace root. Non-secret, deterministic; contains no bucket or
# account identifier.
T2_OBJECT_KEY_NAMESPACE: Final[str] = "t2"

# --- Forbidden success/promotion labels (must never appear in evidence) ---
FORBIDDEN_LABELS: Final[tuple[str, ...]] = (
    "PASS",
    "TIER1",
    "TIER_1",
    "FORMALLY_VERIFIED",
    "SENTINEL_VERIFICATION_COMPLETE",
    "FEASIBLE_FOR_CONSTRUCTION",
    "BYTE_ADMISSIBLE",
    "PRODUCTION_READY",
    "MODEL_IMPROVED",
    "EXPECTANCY_IMPROVED",
)

# --- Scrubber patterns ---
# Local / personal absolute path indicators.
LOCAL_PATH_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"[A-Za-z]:[\\/]"),  # Windows drive-letter path
    re.compile(r"/Users/"),
    re.compile(r"/home/"),
    re.compile(r"AppData"),
    re.compile(r"\\Users\\", re.IGNORECASE),
)
# Signed-URL / bearer-token VALUE indicators (match actual secret values in
# text, NOT the mere words "credential"/"token"/"key" which legitimately appear
# in status names and negative disclaimers).
SECRET_VALUE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"https?://[^\s\"]*[?&](X-Amz-Signature|X-Amz-Credential|token|sig|signature)=",
        re.IGNORECASE,
    ),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{5,}"),
)
# Dict KEY names that carry a credential/secret value (flagged only when the key
# holds a non-empty string value).
CREDENTIAL_KEY_NAMES: Final[frozenset[str]] = frozenset(
    {
        "aws_access_key_id",
        "aws_secret_access_key",
        "access_key",
        "secret_key",
        "session_token",
        "password",
        "credential",
        "credentials",
        "secret",
        "api_key",
        "token",
    }
)
# Raw candle/quote row keys (must not be embedded as data).
RAW_ROW_KEYS: Final[frozenset[str]] = frozenset(
    {"bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c", "rows", "candles"}
)
# Trading-metric keys forbidden anywhere in T2 evidence.
FORBIDDEN_METRIC_KEYS: Final[frozenset[str]] = frozenset(
    {"sharpe", "pnl", "ic", "mi", "expectancy", "expected_value", "win_rate", "drawdown"}
)
# Overclaim phrases forbidden in T2 evidence.
FORBIDDEN_CLAIM_SUBSTRINGS: Final[tuple[str, ...]] = (
    "byte_admissibility_approved",
    "new_epoch_adopted",
    "production_ready",
    "ml_step4_authorised",
)
