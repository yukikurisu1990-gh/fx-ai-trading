"""config_version computation (docs/phase6_hardening.md §6.19).

config_version = SHA256(canonical_json)[:16]

The five elements that compose the canonical JSON are passed in as arguments
so this module is a pure function — all I/O (DB query, env read, file read)
is the caller's responsibility (see ConfigProvider, M3 Cycle 4).

Canonical JSON rules (§6.19):
  - Keys in lexicographic ascending order.
  - No structural whitespace (compact serialisation).
  - UTF-8, LF line endings (irrelevant for compact JSON).
  - Floating-point values serialised as strings to avoid rounding divergence.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical_dumps(obj: Any) -> str:
    """Serialise *obj* to compact, key-sorted JSON."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_config_version(
    app_settings_rows: list[dict[str, str]],
    env_vars: dict[str, str],
    env_file_entries: dict[str, str],
    default_catalog: dict[str, str],
    secret_refs: dict[str, str],
) -> str:
    """Return the first 16 hex chars of SHA256 over the effective config.

    Args:
        app_settings_rows:
            All rows from ``app_settings`` table, each with keys
            ``name``, ``value``, ``type``, ``introduced_in_version``.
            Must be pre-sorted by ``name`` ascending (caller's responsibility).
        env_vars:
            Environment variables whose keys start with ``APP_`` or ``FX_``,
            sorted by key ascending.
        env_file_entries:
            Key-value pairs parsed from ``.env`` (comments and blank lines
            excluded), sorted by key ascending.  Empty dict when no ``.env``.
        default_catalog:
            Code-defined fallback values for settings absent from the DB.
        secret_refs:
            ``{secret_key: SHA256(secret_value)[:16]}`` — hashes only,
            never the secret values themselves.  Sorted by key ascending.

    Returns:
        16-character lowercase hex string.
    """
    effective = {
        "app_settings": app_settings_rows,
        "defaults": default_catalog,
        "env_file": env_file_entries,
        "env_vars": env_vars,
        "secret_refs": secret_refs,
    }
    canonical = _canonical_dumps(effective)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:16]
