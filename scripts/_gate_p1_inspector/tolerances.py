"""PR-B-local constants for the Gate P1 inspector (PR-B.0).

These constants are intentionally *mirrored* (not imported) from the
verification harness so the inspector depends only on the Python standard
library, honouring the AST/source-only mandate at its strictest (plan §3
"Library binding", §13.Q1). A unit test asserts the mirror still matches its
documented source of truth.
"""

from typing import Final

# Mirror of scripts/_verification_harness/tolerances.py::ARTIFACT_SIZE_GUARD_BYTES
# (per-file ceiling, NOT an aggregate budget). Source of truth lives in the
# verification harness; this duplicate keeps the inspector stdlib-only.
ARTIFACT_SIZE_GUARD_BYTES: Final[int] = 95 * 1024 * 1024

# Per-artifact output ceilings for report writers (plan §7). Defends against
# accidental verbose output. A write exceeding these HALTs the writer.
JSON_ARTIFACT_MAX_BYTES: Final[int] = 1 * 1024 * 1024  # 1 MB per JSON artifact
MARKDOWN_ARTIFACT_MAX_BYTES: Final[int] = 256 * 1024  # 256 KB per markdown

# Report schema version stamped into every JSON artifact (plan §7).
SCHEMA_VERSION: Final[str] = "gate-p1-pr-b-0.1-stub"

# PR-B stage marker. PR-B.0 is infrastructure-only and performs NO inspection.
PR_B_STAGE: Final[str] = "PR-B.0"

# Stub-only marker placed in every PR-B.0 artifact so it can never be confused
# with a real Gate P1 inspection report.
STUB_MARKER: Final[str] = "PR_B0_STUB_ONLY"

# The single top-level outcome literal permitted in PR-B.0. It is added in
# PR-B.0 only and removed by PR-B.1 (plan §11). It is NOT one of the real
# Gate P1 outcomes and carries no feasibility / retention / authorisation
# meaning.
STUB_TOP_LEVEL_OUTCOME: Final[str] = "STUB_NO_INSPECTION_PERFORMED"

# Allowed output file extensions for the write-allowlist (plan §5, §7).
ALLOWED_OUTPUT_EXTENSIONS: Final[frozenset[str]] = frozenset({".json", ".md"})
