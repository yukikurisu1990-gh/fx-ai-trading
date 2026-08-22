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
  call.

A fourth, closed by :func:`_reject_win32_normalisable_component` (audit **FB-4**):

* **Win32 name normalisation** — the OS trims trailing dots and spaces from a
  path component before it opens it, so ``<root>/models.`` and ``<root>/models``
  are the same directory. ``Path.resolve(strict=False)`` can only canonicalise a
  component that *exists*; for an absent one it returns the spelling verbatim.
  With ``models/`` absent — which is every fresh clone and every CI run, because
  ``.gitignore`` lists it — ``models.`` therefore survived resolution, compared
  unequal to ``models`` in the name test, had nothing to be identical *to* in the
  identity test, and was ALLOWED; the ``mkdir``/``write_text`` that followed
  created the **real** protected tree. Same shape as the stream case: the guard
  first refused only after the write it existed to prevent.

Containment is decided over the *complete* ancestor chain (``Path.parents`` is
finite by construction — no arbitrary cap to exhaust) and the prefix fold is
case-insensitive.

**What is and is not a function of the input alone.** The *name* limb is: it
reads only the spelling, and after FB-4 it covers every Win32 spelling that
aliases another name (case, via ``PureWindowsPath``'s case-insensitive
comparison; extended-length prefixes, via :func:`normalise_spelling`; streams and
trailing dots/spaces, by refusal). The *identity* limb necessarily consults the
filesystem — a junction cannot be recognised from its spelling. The invariant
that makes that safe is the **name** limb, which consults no filesystem state
at all, and `_reject_non_drive_namespace`, which refuses every spelling that is
not an ordinary local drive path. Those two decide before any filesystem state
is consulted.

A second overclaim has since been withdrawn here. The identity limb alone can
only turn an ALLOW into a REFUSE, but `resolve_candidate` calls `Path.resolve()`
before either limb runs, and `resolve()` follows reparse points — so adding a
junction *inside* a protected tree turns a REFUSE into an ALLOW. Filesystem
state therefore does **not** make this authority uniformly stricter, and the
sentence that said so has been removed rather than qualified. What the module
guarantees is what the two state-free limbs above decide.

Its only question is "does this path name, or sit under, a protected tree?".
It reads no file contents.
"""

from __future__ import annotations

import os
import re
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
    Left unfolded they keep their prefix and are refused outright by
    :func:`_reject_non_drive_namespace`. An earlier version of this docstring
    said ``Path.resolve()`` canonicalises them and the identity test catches
    them, "verified for every spelling". **That was false** - measured,
    ``resolve()`` returns the volume-GUID and UNC spellings unchanged, and with
    the protected root absent the identity limb is silent - so the guarantee is
    withdrawn and replaced by refusal.
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


# Win32 trims these from the end of a path component before it opens the path,
# so `models.`, `models `, `models. ` and `models ...` all name `models`.
_WIN32_TRIMMED_TRAILERS: Final[str] = ". "
# Both separators, on every platform: this module refuses to let the verdict
# depend on `os.sep` (see `_reject_stream_suffix`'s platform rule).
_ANY_SEPARATOR: Final[re.Pattern[str]] = re.compile("[\\\\/]")
# The two components that are *relative navigation*, not names. `resolve()`
# collapses them; they are the only components allowed to end in a dot.
_NAVIGATION_COMPONENTS: Final[frozenset[str]] = frozenset({".", ".."})


def _reject_non_drive_namespace(normalised: str) -> None:
    r"""Refuse every Win32 namespace that is not an ordinary local drive path.

    ``_reject_win32_normalisable_component`` closes the trailing-dot/space family
    FB-4 printed. It does not close the *namespace* family, and an internal audit
    walked four members of that family straight through the guard and wrote a
    real file into a real protected tree with the root absent:

    * ``\?\UNC\localhost\C$\...\models`` and its lower-case spelling,
    * ``\localhost\C$\...\models`` (the administrative share),
    * ``\?\Volume{GUID}\...\models``,
    * ``\?\GLOBALROOT\Device\HarddiskVolumeN\...\models``.

    Each names the same directory as the drive spelling; none is folded by
    :func:`normalise_spelling`; and — this is the part that made the earlier
    reasoning wrong — ``Path.resolve()`` does **not** canonicalise them to the
    drive spelling, so with the protected root absent the identity limb has
    nothing to compare and the name limb never sees the protected name. The
    docstring claim that ``resolve()`` catches them "verified for every
    spelling" was false, and the write landed in ``<repo>/models``.

    The remedy is an **allowlist**, because enumerating namespaces is the shape
    of defect this programme keeps re-opening: the Win32 namespace admits
    device paths, volume GUIDs, GLOBALROOT device chains, UNC shares and
    administrative shares, and a denylist of those five is a denylist of the
    five that were found. Gate-3a writes metadata into an ordinary local
    directory and has no reason to address anything else, so the rule is that a
    candidate must be a plain ``<letter>:\`` path after the extended-length fold
    — and every other spelling is refused whether or not it aliases a protected
    root, which also means the verdict no longer depends on filesystem state.

    Non-Windows paths are unaffected: a POSIX absolute path has no drive letter
    and no UNC form, so the rule applies only where ``\`` or a drive letter is
    the platform's own addressing scheme.
    """
    if os.name != "nt":
        return
    if normalised.startswith("\\\\") or normalised.startswith("//"):
        raise PathAuthorityError(
            "refused UNC or device-namespace path: gate-3a addresses only ordinary "
            "local drive paths, and a share, volume-GUID or GLOBALROOT spelling names "
            "the same directory as a drive path while defeating both containment limbs"
        )
    drive = os.path.splitdrive(normalised)[0]
    if not (len(drive) == 2 and drive[0].isascii() and drive[0].isalpha() and drive[1] == ":"):
        raise PathAuthorityError(
            f"refused path with no ordinary drive letter ({normalised[:40]!r}...); gate-3a "
            "addresses only ordinary local drive paths"
        )


def _reject_win32_normalisable_component(normalised: str) -> None:
    r"""Refuse a path with a component Win32 name normalisation would rewrite.

    **The family, not the two spellings the audit printed.** Win32 trims *every*
    trailing dot and space from a path component before opening it, so an
    unbounded set of spellings — ``models.``, ``models ``, ``models...``,
    ``models. . .`` — all name the one directory ``models``. The invariant here
    is therefore stated over the normalisation itself: *a component is admissible
    only if it is a fixed point of Win32's trailing-trim*. Any component that the
    trim would change names something other than what it spells, and is refused.

    Why refuse rather than normalise and re-test. Normalising would make this
    authority judge ``models`` while the caller that later writes still passes
    ``models.`` to ``open``/``mkdir`` — guard and consumer looking at two
    different strings, which is the divergence class RF-5 and
    :func:`_pin_path_characters` exist to close. Refusal admits no path at all,
    so no such gap can open. It is the same disposition as the device-namespace,
    NUL-byte and alternate-data-stream refusals: a spelling whose aliasing rules
    the name and identity tests cannot model is refused before anything is
    interrogated or created.

    **Why the name limb has to carry this** (audit FB-4). The identity limb
    cannot: ``Path.resolve(strict=False)`` canonicalises a trailing-dot component
    only when it **exists**, and ``_protected_stat`` returns ``None`` for an
    absent root because there is nothing to be identical *to*. With ``models/``
    absent — every fresh clone, every CI run, since ``.gitignore`` lists it —
    ``<root>/models.`` was ALLOWED and the ``mkdir`` that followed **created the
    real protected tree**. Refusing on the spelling is what makes the name limb
    complete, and completeness of the name limb is what makes the identity limb's
    filesystem dependence monotone (it can then only add refusals).

    **Platform rule — the same on every platform, deliberately.** POSIX permits a
    filename ending in a dot or a space, so this refuses paths a POSIX host would
    have accepted. That is the stricter reading, and §12.18's requirement that
    one string get one verdict outranks the lost spelling: this gate writes
    ``*.json`` metadata under caller-supplied output directories and nothing
    else. ``.`` and ``..`` are exempt — they are navigation, not names, and
    ``resolve()`` collapses them before any comparison.

    **Extended-length spellings.** Under ``\\?\`` Win32 performs no normalisation
    at all, so ``\\?\C:\repo\models.`` really is a directory distinct from
    ``models``. :func:`normalise_spelling` has already folded that prefix away by
    the time this runs, so such a path is refused too. Over-strict, and
    deliberately so: admitting it would require this module to model two
    different normalisation regimes selected by a prefix, and a guard that
    branches on which aliasing rules apply is how the previous three defeats
    happened.
    """
    for component in _ANY_SEPARATOR.split(normalised):
        if not component or component in _NAVIGATION_COMPONENTS:
            continue
        trimmed = component.rstrip(_WIN32_TRIMMED_TRAILERS)
        if trimmed != component:
            raise PathAuthorityError(
                f"win32-normalisable path component {component!r} refused: the platform "
                f"trims trailing dots and spaces, so it names {trimmed!r}; a component that "
                "is not a fixed point of that trim aliases a different directory"
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

    **Monotonicity, and why the name test has to be complete** (audit FB-4). The
    identity test is skipped when the protected root is absent — there is nothing
    to be identical *to* — so on an absent root the name test is the *only* thing
    deciding containment. That is fail-closed only while the name test is
    complete over the spellings that alias a name: casing (``PureWindowsPath``
    compares case-insensitively), extended-length prefixes
    (:func:`normalise_spelling`), and the spellings :func:`resolve_candidate`
    refuses outright — device namespace, alternate data streams and
    Win32-normalisable components. FB-4 was exactly this hole: ``models.`` passed
    the name test and the absent root silenced the identity test, so the
    *creating* write landed in the real protected tree. With the name test
    complete, adding the identity test can only add refusals.

    **The wider monotonicity claim that stood here is withdrawn.** It said
    filesystem state "makes this authority stricter and never more permissive",
    and that is false: :func:`resolve_candidate` calls ``Path.resolve()``, which
    follows reparse points, so creating a junction *inside* a protected tree
    turns a REFUSE into an ALLOW - measured with ``mklink /J``, no elevation
    required. What is true, and all that is claimed now, is that the **name**
    limb and :func:`_reject_non_drive_namespace` decide without consulting the
    filesystem at all, so the spellings they own cannot be changed by on-disk
    state.
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
    such gap can open.

    **What this does and does not make input-determined** (audit FB-4). Refusing
    relative spellings removes the working directory from the verdict, and the
    stream, device-namespace, NUL-byte and Win32-normalisation refusals remove
    the spellings whose aliasing this function cannot model. What it does *not*
    do — and what the previous sentence here wrongly claimed — is make the whole
    containment verdict a function of the input alone: :func:`is_within`'s
    identity limb reads the filesystem, and must, because a junction is invisible
    in a spelling. The honest guarantee is :func:`is_within`'s monotonicity, and
    it is stated there.
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
    _reject_win32_normalisable_component(normalised)
    candidate = Path(normalised)
    # AFTER the relative-spelling refusal below, so that a relative path keeps
    # reporting the working-directory reason rather than "no drive letter",
    # which is true of every relative path and would say nothing.
    if candidate.is_absolute():
        _reject_non_drive_namespace(normalised)
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
