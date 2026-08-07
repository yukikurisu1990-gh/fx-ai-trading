r"""Single path-containment authority for gate-3a (BL-3).

The diagnostic review of PR #440 defeated the protected-path guard twice:

* **casing** — the extended-UNC prefix was matched as the literal ``"\\?\UNC\"``,
  but Windows treats it case-insensitively, so ``\\?\unc\localhost\C$\...``
  reached ``resolve()`` unstripped and compared unequal to the protected tree
  even though ``os.path.samefile`` said they were the same directory;
* **depth** — the ancestor walk was capped at a fixed 64 iterations and returned
  ``False`` (allowed) on exhaustion. A path 64 levels below the protected tree
  was ALLOWED while one at 63 was REFUSED.

This module replaces both. Containment is decided over the *complete* ancestor
chain (``Path.parents`` is finite by construction — no arbitrary cap to
exhaust), the prefix fold is case-insensitive, and every failure mode refuses.

Its only question is "does this path name, or sit under, a protected tree?".
It reads no file contents.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final

# Windows spellings that alias an ordinary path. Matched case-insensitively:
# the OS treats `\\?\unc\` and `\\?\UNC\` identically.
_EXTENDED_UNC: Final[str] = "\\\\?\\UNC\\"
_EXTENDED: Final[str] = "\\\\?\\"
# Device namespace: never a data path, and its aliasing rules differ. Refused.
_DEVICE: Final[str] = "\\\\.\\"


class PathAuthorityError(ValueError):
    """Raised when a path cannot be proved to sit outside the protected trees."""


def normalise_spelling(path: str | Path) -> str:
    r"""Fold Windows extended-length prefixes, case-insensitively.

    ``\\?\C:\x`` -> ``C:\x``; ``\\?\UNC\host\share`` -> ``\\host\share``
    (and the same for any casing of ``?\unc\``). Other spellings are returned
    unchanged — this is a prefix fold, not a resolution.

    The fold applies **only** when a drive letter or ``UNC\`` follows. The
    internal audit found the unconditional strip was itself a bypass: the
    Win32 namespace also admits ``\\?\Volume{GUID}\...`` and
    ``\\?\GLOBALROOT\Device\HarddiskVolumeN\...``, and stripping ``\\?\`` from
    those leaves a **relative** path that then resolves against the working
    directory — so a spelling naming the consumed-holdout tree was ALLOWED.
    Left unfolded, ``Path.resolve()`` canonicalises them and the identity test
    catches them; verified for every spelling, including the plain ``\\?\C:\``
    case this fold was written for.
    """
    text = str(path)
    upper = text.upper()
    if upper.startswith(_EXTENDED_UNC):
        return "\\\\" + text[len(_EXTENDED_UNC) :]
    if upper.startswith(_EXTENDED):
        rest = text[len(_EXTENDED) :]
        # Only a `<letter>:` device is a drive whose extended spelling is a
        # pure alias of an ordinary path. Anything else keeps its prefix.
        if len(rest) >= 2 and rest[0].isascii() and rest[0].isalpha() and rest[1] == ":":
            return rest
    return text


def _protected_stat(protected: Path) -> os.stat_result | None:
    """``stat`` of a protected root; ``None`` iff it is genuinely absent.

    A ``FileNotFoundError`` means there is nothing to be identical *to*, so the
    name test alone is sufficient. Any other ``OSError`` (permission, I/O, a
    path that cannot be interrogated) leaves containment undecidable and must
    fail closed — RF-3 flagged the previous ``protected.exists()`` shortcut,
    which reported "absent" for both cases and skipped the identity test.
    """
    try:
        return protected.stat()
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise PathAuthorityError(f"cannot interrogate protected root {protected}: {exc}") from exc


def _same_file(probe: Path, protected_stat: os.stat_result) -> bool:
    """True iff *probe* is the same filesystem object as the protected root."""
    try:
        probe_stat = probe.stat()
    except FileNotFoundError:
        return False
    except (OSError, ValueError) as exc:
        # Existing-but-uninterrogable: containment undecidable -> fail closed.
        raise PathAuthorityError(f"cannot interrogate {probe}: {exc}") from exc
    return os.path.samestat(probe_stat, protected_stat)


def is_within(candidate: Path, protected: Path) -> bool:
    r"""True iff *candidate* is, or sits under, *protected* — by name or identity.

    The name test covers targets that do not exist yet (the usual case for a
    write). The identity test covers spellings that resolve to a different
    string while naming the same directory: UNC aliases (``\\localhost\C$\...``),
    NTFS junctions and 8.3 short names. The walk visits the whole ancestor
    chain; there is no depth at which it stops looking and allows.
    """
    if candidate == protected or protected in candidate.parents:
        return True
    protected_stat = _protected_stat(protected)
    if protected_stat is None:
        return False
    return any(_same_file(probe, protected_stat) for probe in (candidate, *candidate.parents))


def resolve_candidate(path: Any) -> Path:
    """Resolve *path* to an absolute ``Path``, or refuse.

    Rejects non-path types, empty strings, embedded NUL bytes and the device
    namespace outright; any resolution failure refuses rather than proceeding
    with an unresolved spelling.
    """
    if isinstance(path, Path):
        text = str(path)
    elif isinstance(path, str):
        # `str(path)` again would re-enter a subclass's __str__, letting it show
        # one string to the checks and another to `Path()`. Pin the character
        # data once, as a plain `str`.
        text = str.__str__(path)
    else:
        raise PathAuthorityError(f"path must be a str or Path, got {type(path).__name__}")
    if not text.strip():
        raise PathAuthorityError("empty path refused")
    if "\x00" in text:
        raise PathAuthorityError("path containing a NUL byte refused")
    if text.startswith(_DEVICE):
        raise PathAuthorityError(r"device-namespace path (\\.\) refused")
    try:
        return Path(normalise_spelling(text)).resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        raise PathAuthorityError(f"unresolvable path {text!r}: {exc}") from exc


def assert_outside(path: Any, protected_roots: tuple[Path, ...], labels: tuple[str, ...]) -> None:
    """Refuse if *path* names or sits under any protected root.

    ``labels`` supplies the human-readable name reported for each root, so the
    refusal message never has to echo an absolute host path.
    """
    candidate = resolve_candidate(path)
    for protected, label in zip(protected_roots, labels, strict=True):
        try:
            resolved_protected = protected.resolve()
        except (OSError, ValueError, RuntimeError) as exc:
            raise PathAuthorityError(f"unresolvable protected root {label}: {exc}") from exc
        if is_within(candidate, resolved_protected):
            raise PathAuthorityError(f"refused real/protected path: {label}")
