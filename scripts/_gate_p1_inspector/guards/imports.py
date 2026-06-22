"""Production-module import guard (plan §5 "Namespace allowlist").

Installs a ``sys.meta_path`` finder that fails closed on any attempt to import
a production pipeline / data-fetch / source module. This is redundant
enforcement of the AST/source-only mandate: PR-B inspects production code via
``ast.parse`` over ``Path.read_text`` text, never by importing it.

Blocked import prefixes:
    * ``scripts.stage*``                 (production pipeline modules)
    * ``scripts.fetch_oanda_archive``    (data fetch)
    * ``scripts.fetch_oanda_candles``    (data fetch)
    * ``src`` / ``fx_ai_trading``        (production source packages)

Permitted: the Python standard library and ``scripts._gate_p1_inspector.*``
(the inner package itself).
"""

from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from importlib.abc import MetaPathFinder
from typing import Final

from . import GuardViolationError

_BLOCKED_PREFIXES: Final[tuple[str, ...]] = (
    "scripts.stage",
    "scripts.fetch_oanda_archive",
    "scripts.fetch_oanda_candles",
    "src",
    "fx_ai_trading",
)


def _is_blocked(fullname: str) -> bool:
    for prefix in _BLOCKED_PREFIXES:
        if prefix.endswith("stage"):
            # Prefix-of-name match: e.g. ``scripts.stage23_0a_build_outcome``
            # has no dotted boundary after ``scripts.stage``.
            if fullname.startswith(prefix):
                return True
        elif fullname == prefix or fullname.startswith(prefix + "."):
            return True
    return False


class _ProductionImportBlocker(MetaPathFinder):
    """Meta-path finder that HALTs on blocked production imports."""

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: object = None,
    ) -> None:
        if _is_blocked(fullname):
            raise GuardViolationError(
                f"import guard: import of production module '{fullname}' is "
                "prohibited; PR-B inspects production code via ast.parse over "
                "source text only (plan §5 Namespace allowlist)."
            )
        return None  # defer to the normal import machinery


_finder: _ProductionImportBlocker | None = None


def install() -> None:
    """Install the production-import meta-path finder at highest priority."""
    global _finder
    if _finder is not None:
        return
    _finder = _ProductionImportBlocker()
    sys.meta_path.insert(0, _finder)


def uninstall() -> None:
    """Remove the production-import meta-path finder if installed."""
    global _finder
    if _finder is not None and _finder in sys.meta_path:
        sys.meta_path.remove(_finder)
    _finder = None


@contextmanager
def activate() -> Iterator[None]:
    """Context manager that installs the import guard for its duration."""
    install()
    try:
        yield
    finally:
        uninstall()
