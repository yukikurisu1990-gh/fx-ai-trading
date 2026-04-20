"""Pure helpers for `.env` diff computation (M26 Phase 3).

All public helpers are framework-free. Output never contains plaintext
secret values — only key names and sha256 hex prefixes (8 chars), per
``development_rules.md`` §10.3.1.
"""

from __future__ import annotations

import hashlib
from typing import TypedDict

_HASH_PREFIX_LEN = 8


class EnvDiff(TypedDict):
    added: list[dict[str, str]]
    removed: list[dict[str, str]]
    changed: list[dict[str, str]]
    unchanged: list[str]


def hash_prefix(value: str | None) -> str:
    """Return sha256 hex prefix of ``value`` (8 chars). Empty / None → ``"-"``."""
    if value is None or value == "":
        return "-"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:_HASH_PREFIX_LEN]


def parse_env_text(text: str) -> dict[str, str]:
    """Parse ``.env`` text into ``{key: value}``.

    Rules:
      - Blank lines and lines starting with ``#`` are skipped.
      - Each retained line must contain ``=``; otherwise it is skipped.
      - Surrounding single / double quotes around the value are stripped.
      - On duplicate keys, the last occurrence wins.
      - Whitespace around the key and around the value is stripped.
    """
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (len(value) >= 2) and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        if not key:
            continue
        result[key] = value
    return result


def render_env_text(env: dict[str, str]) -> str:
    """Serialize ``env`` back to ``.env`` text (KEY=VALUE per line, no quoting).

    Keys are emitted in insertion order. Values are written verbatim — callers
    must not pass values that contain newlines or unescaped quotes (Bootstrap
    UI rejects such input upstream).
    """
    lines: list[str] = []
    for key, value in env.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines) + ("\n" if lines else "")


def compute_diff(old: dict[str, str], new: dict[str, str]) -> EnvDiff:
    """Return added / removed / changed / unchanged sets between two env dicts.

    The output never contains plaintext values. Each entry carries only the
    key name and ``hash_prefix`` of old / new values — sufficient for an
    operator preview, insufficient to recover the secret.
    """
    old_keys = set(old.keys())
    new_keys = set(new.keys())

    added_keys = sorted(new_keys - old_keys)
    removed_keys = sorted(old_keys - new_keys)
    common_keys = sorted(old_keys & new_keys)

    added = [{"name": k, "new_hash": hash_prefix(new[k])} for k in added_keys]
    removed = [{"name": k, "old_hash": hash_prefix(old[k])} for k in removed_keys]
    changed: list[dict[str, str]] = []
    unchanged: list[str] = []
    for k in common_keys:
        if old[k] == new[k]:
            unchanged.append(k)
        else:
            changed.append(
                {
                    "name": k,
                    "old_hash": hash_prefix(old[k]),
                    "new_hash": hash_prefix(new[k]),
                }
            )

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }
