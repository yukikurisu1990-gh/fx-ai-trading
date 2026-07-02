"""Evidence cleanliness scrubber for the Foundation T2 harness.

Scans a candidate evidence payload/text and fails closed if it would leak:
local absolute / personal paths, credentials / secrets / signed URLs / tokens,
raw candle/quote rows, forbidden success labels, trading-metric keys, or
byte-admissibility / new-epoch / production / ML-Step-4 overclaims.
"""

from __future__ import annotations

import json
from typing import Any

from .constants import (
    CREDENTIAL_KEY_NAMES,
    FORBIDDEN_CLAIM_SUBSTRINGS,
    FORBIDDEN_LABELS,
    FORBIDDEN_METRIC_KEYS,
    LOCAL_PATH_PATTERNS,
    RAW_ROW_KEYS,
    SECRET_VALUE_PATTERNS,
)

SCRUBBER_VERSION = "foundation-t2-scrubber.v1"


class EvidenceScrubError(RuntimeError):
    """Raised when evidence would leak forbidden content."""


def _scan_text(text: str, findings: list[str]) -> None:
    for pattern in LOCAL_PATH_PATTERNS:
        if pattern.search(text):
            findings.append(f"local_path:{pattern.pattern}")
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.search(text):
            findings.append(f"secret_value:{pattern.pattern}")
    for label in FORBIDDEN_LABELS:
        if label in text:
            findings.append(f"forbidden_label:{label}")
    lowered = text.lower()
    for phrase in FORBIDDEN_CLAIM_SUBSTRINGS:
        if phrase in lowered:
            findings.append(f"overclaim:{phrase}")


def _scan_keys(obj: Any, findings: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str):
                low = key.lower()
                if low in RAW_ROW_KEYS:
                    findings.append(f"raw_row_key:{key}")
                if low in FORBIDDEN_METRIC_KEYS:
                    findings.append(f"metric_key:{key}")
                if low in CREDENTIAL_KEY_NAMES and isinstance(value, str) and value.strip():
                    findings.append(f"credential_key:{key}")
            _scan_keys(value, findings)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _scan_keys(item, findings)


def scan_payload(payload: dict[str, Any]) -> list[str]:
    """Return a list of cleanliness findings (empty == clean)."""
    findings: list[str] = []
    _scan_keys(payload, findings)
    _scan_text(json.dumps(payload, ensure_ascii=False), findings)
    return sorted(set(findings))


def assert_clean(payload: dict[str, Any]) -> None:
    findings = scan_payload(payload)
    if findings:
        raise EvidenceScrubError(f"evidence not clean: {findings}")


def cleanliness_report(payload: dict[str, Any]) -> dict[str, Any]:
    findings = scan_payload(payload)
    return {
        "scrubber_version": SCRUBBER_VERSION,
        "clean": not findings,
        "findings": findings,
        "checks": [
            "no_local_absolute_paths",
            "no_windows_user_paths",
            "no_users_home_drive_paths",
            "no_credentials",
            "no_env_var_values",
            "no_signed_urls",
            "no_access_tokens",
            "no_raw_market_rows",
            "no_candle_quote_row_previews",
            "no_forbidden_success_labels",
            "no_trading_metric_keys",
            "no_byte_admissibility_claim",
            "no_new_epoch_claim",
            "no_production_claim",
            "no_ml_step4_claim",
        ],
    }
