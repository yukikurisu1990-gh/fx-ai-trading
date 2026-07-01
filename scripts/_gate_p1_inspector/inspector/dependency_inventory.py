"""Static dependency inventory (PR-B.2 — plan §4).

Builds an AST-derived import graph of representative consumer sources and of the
inspector package itself. It NEVER imports the discovered modules, never runs
pip / a package manager / a subprocess, and never executes any production code.
Every classification is derived from parsed source text only.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

from ..b2_constants import (
    CONSUMER_REGISTRY,
    DEP_FORBIDDEN_TO_EXECUTE,
    DEP_OBSERVED,
    DEP_UNRESOLVED,
    FORBIDDEN_EXECUTION_SURFACES,
    SCOPE_NOT_FULL_REPO_CERT,
    SCOPE_REPRESENTATIVE_DEP_ONLY,
    is_internal_module,
)

_INSPECTOR_PACKAGE_RELDIR = "scripts/_gate_p1_inspector"
# Production import prefixes the PR-B.2 inspector itself must never import.
_PRODUCTION_IMPORT_PREFIXES = ("scripts.stage", "scripts.fetch_oanda", "src", "fx_ai_trading")


def _top_level(module: str | None) -> str | None:
    if not module:
        return None
    return module.split(".", 1)[0]


def _collect_imports(source_text: str) -> list[str]:
    """Return sorted unique fully-qualified import module names from source."""
    tree = ast.parse(source_text)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # relative import; record the referenced module if any
                if node.module:
                    names.add("." * node.level + node.module)
            elif node.module:
                names.add(node.module)
    return sorted(names)


def _classify_kind(top: str) -> str:
    if top in sys.stdlib_module_names:
        return "stdlib"
    if is_internal_module(top):
        return "internal"
    return "third_party"


def _is_forbidden_execution_surface(module_name: str) -> bool:
    lowered = module_name.lower()
    return any(surface in lowered for surface in FORBIDDEN_EXECUTION_SURFACES)


def _label_for(module_name: str, top: str | None) -> str:
    if top is None:
        return DEP_UNRESOLVED
    if _is_forbidden_execution_surface(module_name):
        return DEP_FORBIDDEN_TO_EXECUTE
    return DEP_OBSERVED


def inventory_consumer(repo_root: Path, relpath: str) -> dict[str, Any]:
    """Static import inventory for one consumer source file."""
    path = repo_root / relpath
    if not path.exists():
        return {"source_path": relpath, "present": False, "dependencies": []}
    try:
        imports = _collect_imports(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return {"source_path": relpath, "present": True, "parse_error": True, "dependencies": []}

    deps: list[dict[str, Any]] = []
    for module_name in imports:
        top = _top_level(module_name) if not module_name.startswith(".") else None
        kind = _classify_kind(top) if top else "relative_or_unresolved"
        deps.append(
            {
                "module": module_name,
                "top_level": top,
                "kind": kind,
                "label": _label_for(module_name, top),
            }
        )
    return {"source_path": relpath, "present": True, "dependencies": deps}


def _inspector_self_check(repo_root: Path) -> dict[str, Any]:
    """Confirm the PR-B.2 inspector package imports NO production trading module."""
    pkg_dir = repo_root / _INSPECTOR_PACKAGE_RELDIR
    offenders: list[dict[str, str]] = []
    for py in sorted(pkg_dir.rglob("*.py")):
        try:
            imports = _collect_imports(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for module_name in imports:
            if module_name.startswith(".") or module_name.startswith("scripts._gate_p1_inspector"):
                continue
            if any(module_name.startswith(p) for p in _PRODUCTION_IMPORT_PREFIXES):
                offenders.append(
                    {"file": py.relative_to(repo_root).as_posix(), "import": module_name}
                )
    return {
        "inspector_free_of_production_imports": not offenders,
        "offending_imports": offenders,
    }


def build_dependency_inventory(repo_root: str | Path) -> dict[str, Any]:
    """Build the full static dependency inventory (metadata only)."""
    repo_root = Path(repo_root)
    consumers = [inventory_consumer(repo_root, rel) for rel in CONSUMER_REGISTRY]
    self_check = _inspector_self_check(repo_root)

    all_labels = {d["label"] for c in consumers for d in c["dependencies"]}
    forbidden_execution_count = sum(
        1 for c in consumers for d in c["dependencies"] if d["label"] == DEP_FORBIDDEN_TO_EXECUTE
    )
    return {
        "method": "ast_source_text_only",
        "scope": SCOPE_REPRESENTATIVE_DEP_ONLY,
        "scope_note": SCOPE_NOT_FULL_REPO_CERT,
        "inspected_consumer_registry_only": True,
        "inspected_consumer_sources": list(CONSUMER_REGISTRY),
        "import_execution_performed": False,
        "package_manager_invoked": False,
        "consumers": consumers,
        "inspector_self_check": self_check,
        "summary": {
            "consumer_count": len(consumers),
            "distinct_labels": sorted(all_labels),
            "forbidden_to_execute_count": forbidden_execution_count,
            "scope": SCOPE_REPRESENTATIVE_DEP_ONLY,
            "not_full_repository_certification": True,
        },
    }
