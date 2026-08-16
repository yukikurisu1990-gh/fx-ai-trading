r"""Single path-containment authority for gate-3a (BL-3).

The diagnostic review of PR #440 defeated the protected-path guard twice:

* **casing** — the extended-UNC prefix was matched as the literal ``"\\?\UNC\"``,
  but Windows treats it case-insensitively, so ``\\?\unc\localhost\C$\...``
  reached ``resolve()`` unstripped and compared unequal to the protected tree
  even though ``os.path.samefile`` said they were the same directory;
* **depth** — the ancestor walk was capped at a fixed 64 iterations and returned
  ``False`` (allowed) on exhaustion. A path 64 levels below the protected tree
  was ALLOWED while one at 63 was REFUSED.

This module replaces both. A third defeat, found by the mutation/adversarial
workstream against *this* module, is closed by :func:`_reject_stream_suffix`:

* **NTFS alternate data streams** — ``<protected>/docs:probe_stream`` writes
  into the protected directory while ``docs`` remains a directory, so neither
  the name walk nor ``samestat`` sees a match until the stream already exists.
  The guard therefore allowed the *creating* write and refused only the second
  call. Containment is decided over the *complete* ancestor
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
# The one position at which a colon is a drive-letter separator (`C:\...`) and
# not an NTFS stream separator. See `_reject_stream_suffix`.
_DRIVE_COLON_INDEX: Final[int] = 1


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
        # Fold only when what follows is ITSELF a rooted path — a `<letter>:`
        # drive, or anything the platform already calls absolute. That is what
        # makes the extended spelling a pure alias of an ordinary path.
        # `Volume{GUID}\...` and `GLOBALROOT\Device\...` are neither, so they
        # keep their prefix and reach `resolve()` intact; stripping them left a
        # relative path that resolved against the working directory and walked
        # straight out of the protected tree.
        is_drive = len(rest) >= 2 and rest[0].isascii() and rest[0].isalpha() and rest[1] == ":"
        if is_drive or Path(rest).is_absolute():
            return rest
    return text


def _reject_stream_suffix(normalised: str) -> None:
    r"""Refuse a path whose spelling names an NTFS alternate data stream.

    A stream-qualified name (``<path>:<stream>``) **aliases the object it is
    attached to without being that object**: ``docs:probe_stream`` writes into
    the protected ``docs`` directory while ``docs`` stays a directory, so
    ``Path.parents`` never names ``docs`` and ``stat()`` on the stream fails
    with ``FileNotFoundError`` until the stream exists. Lead-reproduced on a
    synthetic protected root: the *creating* write was **ALLOWED** and
    succeeded, and only the second call — once the stream existed and
    ``samestat`` could see it — refused. A containment guard that first refuses
    after the write it was meant to prevent is fail-open where it matters.

    This is the same family as the device-namespace and NUL-byte refusals in
    :func:`resolve_candidate`: a spelling whose aliasing rules the name and
    identity tests below cannot model is refused outright, before anything is
    interrogated or created.

    **Platform rule — the same on every platform, deliberately.** A colon is
    permitted only as the drive-letter separator (index
    ``_DRIVE_COLON_INDEX`` = 1, preceded by an ASCII letter: ``C:\...``); every
    other colon is refused, on POSIX as well as on Windows, where ``:`` is a
    legal filename character. Two reasons, in order:

    * §12.18 requires the verdict to be a function of the path alone. Deciding
      this on ``os.name`` would make the ubuntu CI host and the Windows
      development host answer differently about the same string — exactly the
      host-dependence the audit recorded against two other tests in this suite;
    * this gate writes ``*.json`` metadata under caller-supplied output
      directories and nothing else (``_validate_name`` already refuses ``:`` in
      the filename), so a colon-bearing POSIX directory name is not a capability
      being taken away. Refusing is the fail-closed choice and the stricter
      reading wins.
    """
    for index, character in enumerate(normalised):
        if character != ":":
            continue
        if index == _DRIVE_COLON_INDEX and normalised[0].isascii() and normalised[0].isalpha():
            continue
        raise PathAuthorityError(
            f"stream-qualified path {normalised!r} refused: a ':' outside the "
            "drive-letter position names an NTFS alternate data stream, which "
            "aliases the object it is attached to without being that object"
        )


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


def _pin_path_characters(path: Path) -> str:
    r"""Return a ``Path``'s own character data, or refuse a two-faced subclass.

    RF-5: the ``str`` branch of :func:`resolve_candidate` was hardened against a
    subclass showing one string to the checks and another to the consumer, but
    the ``Path`` branch called plain ``str(path)`` and was not. Lead-verified:
    a ``Path`` subclass whose ``__str__`` returned ``"artifacts/harmless"``
    while carrying the consumed-holdout tree was **ALLOWED**, and the very same
    object wrapped as ``Path(obj)`` was refused.

    Two things are needed, because a ``Path`` reaches a consumer by two
    different routes:

    * the guard must judge the object's **own** path data, so it is read through
      the unbound ``PurePath.__str__`` rather than through any override;
    * an ``open()``/``mkdir()`` on the same object goes through
      ``__fspath__``, which is defined as ``str(self)`` and therefore *does*
      re-enter the override. So ``str(path)`` and ``os.fspath(path)`` must both
      agree with that pinned rendering; a disagreement means the guard and the
      consumer would be looking at different paths, and is refused outright
      rather than resolved in either direction.
    """
    try:
        pinned = Path.__str__(path)
    except Exception as exc:  # noqa: BLE001 - a hostile subclass fails closed
        raise PathAuthorityError(f"path object cannot be rendered: {exc}") from exc
    for label, render in (("__str__", str), ("__fspath__", os.fspath)):
        try:
            shown = render(path)
        except Exception as exc:  # noqa: BLE001 - a hostile subclass fails closed
            raise PathAuthorityError(f"path object {label} raised: {exc}") from exc
        if shown != pinned:
            raise PathAuthorityError(
                f"{type(path).__name__}.{label} disagrees with its own path data; "
                "a path shown to the guard must be the path handed to the consumer"
            )
    return pinned


def resolve_candidate(path: Any) -> Path:
    """Resolve *path* to an absolute ``Path``, or refuse.

    Rejects non-path types, empty strings, embedded NUL bytes, the device
    namespace, **stream-qualified spellings** (see
    :func:`_reject_stream_suffix`) and **relative spellings** outright; any
    resolution failure refuses rather than proceeding with an unresolved
    spelling.

    §12.18 / D-7 — **relative paths are refused, not anchored.** ``Path(rel)
    .resolve()`` consults the process working directory, so the same logical
    path was ALLOWED from one directory and REFUSED from another
    (lead-verified). D-7 permits either anchoring at the repository root or
    requiring absolute paths; **requiring absolute paths is the fail-closed
    choice** and is what this implements. Anchoring would decide containment
    against ``repo_root / rel`` while the caller that later writes the path
    still resolves it against the working directory — the guard and the
    consumer would then be judging two different locations, which is the same
    class of divergence RF-5 closes above. Refusal admits no path at all, so no
    such gap can open, and the verdict for every accepted input is now a
    function of the input alone.
    """
    if isinstance(path, Path):
        text = _pin_path_characters(path)
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
    normalised = normalise_spelling(text)
    _reject_stream_suffix(normalised)
    candidate = Path(normalised)
    if not candidate.is_absolute():
        raise PathAuthorityError(
            f"relative path {text!r} refused: containment would depend on the working "
            "directory; supply an absolute path"
        )
    try:
        return candidate.resolve()
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
