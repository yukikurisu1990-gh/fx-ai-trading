"""Pair-universe (PAIRS_20) authority resolution (plan §6, §3.2).

Resolves the canonical ``PAIRS_20`` list from the production source by AST
inspection (never import), cross-confirms against the secondary source, and
computes a deterministic ``pair_universe_hash``. Returns a structured result
for the resolver; it decides no outcome itself.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..b1_constants import (
    PAIR_UNIVERSE_CANONICAL_SOURCE,
    PAIR_UNIVERSE_SECONDARY_SOURCE,
)

OUTCOME_OK = "OK"
OUTCOME_AMBIGUOUS = "AMBIGUOUS"
OUTCOME_OK_SECONDARY_UNAVAILABLE = "OK_SECONDARY_UNAVAILABLE"
OUTCOME_INTEGRITY_HALT_CANONICAL_UNPARSEABLE = "INTEGRITY_HALT_CANONICAL_UNPARSEABLE"


@dataclass(frozen=True)
class PairUniverseResult:
    outcome: str
    pairs: list[str] | None
    pair_universe_hash: str | None
    source_a: dict[str, str | None]
    source_b: dict[str, str | None] | None = None
    notes: list[str] = field(default_factory=list)


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_pairs_20(source_text: str) -> list[str] | None:
    """Return the ``PAIRS_20`` string list from module source, or None."""
    tree = ast.parse(source_text)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [t for t in node.targets if isinstance(t, ast.Name)]
        if not any(t.id == "PAIRS_20" for t in targets):
            continue
        if not isinstance(node.value, ast.List):
            return None
        pairs: list[str] = []
        for elt in node.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                pairs.append(elt.value)
            else:
                return None
        return pairs
    return None


def _hash_pairs(pairs: list[str]) -> str:
    payload = json.dumps(sorted(pairs), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_pair_universe(repo_root: str | Path) -> PairUniverseResult:
    """Resolve PAIRS_20 from canonical + secondary sources (AST only)."""
    repo_root = Path(repo_root)
    canonical_path = repo_root / PAIR_UNIVERSE_CANONICAL_SOURCE
    secondary_path = repo_root / PAIR_UNIVERSE_SECONDARY_SOURCE

    source_a: dict[str, str | None] = {
        "path": PAIR_UNIVERSE_CANONICAL_SOURCE,
        "sha256": None,
    }
    if not canonical_path.exists():
        return PairUniverseResult(
            outcome=OUTCOME_INTEGRITY_HALT_CANONICAL_UNPARSEABLE,
            pairs=None,
            pair_universe_hash=None,
            source_a=source_a,
            notes=["canonical source not found"],
        )
    source_a["sha256"] = _sha256_of(canonical_path)

    try:
        canonical_pairs = _extract_pairs_20(canonical_path.read_text(encoding="utf-8"))
    except SyntaxError:
        canonical_pairs = None
    if not canonical_pairs:
        return PairUniverseResult(
            outcome=OUTCOME_INTEGRITY_HALT_CANONICAL_UNPARSEABLE,
            pairs=None,
            pair_universe_hash=None,
            source_a=source_a,
            notes=["canonical PAIRS_20 unparseable or empty"],
        )

    pair_hash = _hash_pairs(canonical_pairs)

    source_b: dict[str, str | None] = {
        "path": PAIR_UNIVERSE_SECONDARY_SOURCE,
        "sha256": None,
    }
    if not secondary_path.exists():
        return PairUniverseResult(
            outcome=OUTCOME_OK_SECONDARY_UNAVAILABLE,
            pairs=canonical_pairs,
            pair_universe_hash=pair_hash,
            source_a=source_a,
            source_b=source_b,
            notes=["secondary source unavailable; canonical accepted"],
        )
    source_b["sha256"] = _sha256_of(secondary_path)

    try:
        secondary_pairs = _extract_pairs_20(secondary_path.read_text(encoding="utf-8"))
    except SyntaxError:
        secondary_pairs = None
    if not secondary_pairs:
        return PairUniverseResult(
            outcome=OUTCOME_OK_SECONDARY_UNAVAILABLE,
            pairs=canonical_pairs,
            pair_universe_hash=pair_hash,
            source_a=source_a,
            source_b=source_b,
            notes=["secondary PAIRS_20 unparseable; canonical accepted"],
        )

    if canonical_pairs != secondary_pairs:
        return PairUniverseResult(
            outcome=OUTCOME_AMBIGUOUS,
            pairs=canonical_pairs,
            pair_universe_hash=pair_hash,
            source_a=source_a,
            source_b=source_b,
            notes=["canonical and secondary PAIRS_20 differ"],
        )

    return PairUniverseResult(
        outcome=OUTCOME_OK,
        pairs=canonical_pairs,
        pair_universe_hash=pair_hash,
        source_a=source_a,
        source_b=source_b,
    )
