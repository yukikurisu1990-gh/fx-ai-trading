"""M1 BA schema authority resolution (plan §6, §3.1).

Derives the M1 BA required-field set from production source by AST inspection
of ``load_m1_ba`` (the ``raw[<key>]`` subscripts it reads) — never by import —
and HALTs on drift versus the protocol §3.1 list. ``volume`` (or any other
extra key) is recorded as an informational extension and is never a HALT.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from ..b1_constants import PROTOCOL_REQUIRED_FIELDS, SCHEMA_AUTHORITY_SOURCE

OUTCOME_OK = "OK"
OUTCOME_INTEGRITY_HALT_SCHEMA_AUTHORITY_DRIFT = "INTEGRITY_HALT_SCHEMA_AUTHORITY_DRIFT"
OUTCOME_INTEGRITY_HALT_SOURCE_UNPARSEABLE = "INTEGRITY_HALT_SOURCE_UNPARSEABLE"

_LOADER_FUNCTION = "load_m1_ba"
_SUBSCRIPT_VAR = "raw"


@dataclass(frozen=True)
class SchemaAuthorityResult:
    outcome: str
    required_fields: list[str] | None
    informational_extensions: list[str]
    source: dict[str, str | None]
    notes: list[str] = field(default_factory=list)


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _collect_subscript_keys(func: ast.FunctionDef, var_name: str) -> set[str]:
    """Collect string keys from ``var_name[<const str>]`` subscripts."""
    keys: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Subscript):
            continue
        value = node.value
        if isinstance(value, ast.Name) and value.id == var_name:
            sl = node.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                keys.add(sl.value)
    return keys


def resolve_schema_authority(repo_root: str | Path) -> SchemaAuthorityResult:
    """Resolve the M1 BA required-field set from production source (AST only)."""
    repo_root = Path(repo_root)
    source_path = repo_root / SCHEMA_AUTHORITY_SOURCE
    source: dict[str, str | None] = {"path": SCHEMA_AUTHORITY_SOURCE, "sha256": None}

    if not source_path.exists():
        return SchemaAuthorityResult(
            outcome=OUTCOME_INTEGRITY_HALT_SOURCE_UNPARSEABLE,
            required_fields=None,
            informational_extensions=[],
            source=source,
            notes=["schema authority source not found"],
        )
    source["sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()

    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return SchemaAuthorityResult(
            outcome=OUTCOME_INTEGRITY_HALT_SOURCE_UNPARSEABLE,
            required_fields=None,
            informational_extensions=[],
            source=source,
            notes=["schema authority source failed to parse"],
        )

    func = _find_function(tree, _LOADER_FUNCTION)
    if func is None:
        return SchemaAuthorityResult(
            outcome=OUTCOME_INTEGRITY_HALT_SOURCE_UNPARSEABLE,
            required_fields=None,
            informational_extensions=[],
            source=source,
            notes=[f"{_LOADER_FUNCTION} not found in source"],
        )

    derived = _collect_subscript_keys(func, _SUBSCRIPT_VAR)
    required = derived & PROTOCOL_REQUIRED_FIELDS
    missing = PROTOCOL_REQUIRED_FIELDS - derived
    extensions = sorted(derived - PROTOCOL_REQUIRED_FIELDS)

    if missing:
        return SchemaAuthorityResult(
            outcome=OUTCOME_INTEGRITY_HALT_SCHEMA_AUTHORITY_DRIFT,
            required_fields=sorted(required),
            informational_extensions=extensions,
            source=source,
            notes=[f"derived schema missing protocol field(s): {sorted(missing)}"],
        )

    return SchemaAuthorityResult(
        outcome=OUTCOME_OK,
        required_fields=sorted(PROTOCOL_REQUIRED_FIELDS),
        informational_extensions=extensions,
        source=source,
    )
