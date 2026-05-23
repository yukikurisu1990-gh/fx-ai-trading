"""Forbidden-input rejection for Tabular Targeted Verification V2-expanded.

Per PR #358 amendment §A.0 + V2-expanded design memo §3.1: the verification
harness MUST NOT read any EXPLORATORY_ONLY artifact under
``artifacts/stage29_0b/`` (the β WIP @ 9ac8fda exploratory output) and MUST
NOT read any non-implementation-branch file as input.

Stage 1 provides the rejection primitives; orchestration is Stage 2/3.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

FORBIDDEN_PATH_PREFIXES: tuple[str, ...] = (
    "artifacts/stage29_0b/",  # β WIP @ 9ac8fda exploratory output (EXPLORATORY_ONLY)
)


class ForbiddenInputError(RuntimeError):
    """Raised when a forbidden EXPLORATORY_ONLY or off-branch path is opened.

    Per amendment §A.0 / §3.1: NO reuse of WIP @ 9ac8fda or
    EXPLORATORY_ONLY artifacts as evidence.
    """


def assert_path_not_forbidden(path: str | Path) -> None:
    """Raise ForbiddenInputError if ``path`` matches any forbidden prefix.

    ``path`` is interpreted as a project-relative path. Absolute paths under
    the project root are normalised to project-relative for the check.
    """
    p = str(path).replace("\\", "/")
    # Normalise: strip leading "./"
    if p.startswith("./"):
        p = p[2:]
    for forbidden in FORBIDDEN_PATH_PREFIXES:
        if p.startswith(forbidden) or ("/" + forbidden) in p:
            raise ForbiddenInputError(
                f"forbidden EXPLORATORY_ONLY input path: {path!r} "
                f"(matches prefix {forbidden!r}); per V2-expanded amendment §A.0, "
                f"WIP @ 9ac8fda artifacts MUST NOT be reused as evidence"
            )


def write_forbidden_inputs_manifest(out_path: Path) -> None:
    """Persist the forbidden-inputs registry to a manifest file.

    The committed manifest is required at every formal run per amendment §A.5.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "v2-expanded-1.0",
        "forbidden_path_prefixes": list(FORBIDDEN_PATH_PREFIXES),
        "rationale": (
            "Per PR #358 amendment §A.0 + V2-expanded design memo §3.1: "
            "EXPLORATORY_ONLY artifacts under artifacts/stage29_0b/ from β "
            "WIP @ 9ac8fda MUST NOT be reused as formal evidence. The harness "
            "rejects any open() on a matching path with ForbiddenInputError."
        ),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def check_paths_iterable(paths: Iterable[str | Path]) -> None:
    """Apply ``assert_path_not_forbidden`` to every path in ``paths``."""
    for p in paths:
        assert_path_not_forbidden(p)
