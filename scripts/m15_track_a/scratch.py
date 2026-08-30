"""Q8 — the one research-scratch write root for Track A.

Every byte Track A writes goes beneath **one** root, named here as a module
constant with no caller-supplied directory component.  That constraint is not
tidiness: §9 of the gate document records that its own OUT ruling on
reserved-filename impersonation is honest *only* under "a **module constant
with no caller-supplied directory component**", because with a constant root
the researcher is not the adversary, and without one the Win32 trailing-dot
family becomes a correctness surface rather than merely an attack surface.

Containment is decided by :mod:`scripts.m15_gate3a.path_authority`, the
repository's single authority for path aliasing — the extended-UNC prefix, the
Win32 trailing-dot/space class, NTFS stream suffixes, ``..`` traversal and the
volume-GUID namespace are all closed there and are not re-implemented.

Two things this module adds that the gate-3a guards do not cover
----------------------------------------------------------------

1. ``artifacts/m15_gate3a/`` is **not** in ``guards._PROTECTED_PREFIXES`` — the
   open referral **NR-A** — so ``guards.refuse_real_path`` permits exactly the
   write §8.11.9 item 6 forbids.  This module protects it explicitly rather
   than relying on a guard that does not reach it.
2. Containment here is **positive**: a path is admissible only if it is *inside*
   the scratch root.  The gate-3a guard is negative — it refuses named
   protected roots and permits everything else — which is the right shape for a
   writer with many legitimate destinations and the wrong shape for one with
   exactly one.
"""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import Any, Final

from scripts.m15_gate3a.path_authority import PathAuthorityError, is_within, resolve_candidate

#: The single Track A scratch root, relative to the repository root.  A module
#: constant: no caller supplies it, no environment variable overrides it, and no
#: function takes it as an argument.
SCRATCH_ROOT_RELATIVE: Final[str] = "artifacts/track_a_scratch"

#: The Track A **governance ledger** root, and it is deliberately a different
#: directory from the scratch root above.
#:
#: §8.13.5 item 5 requires the `EXPLORATORY_SEEN_DATA` ledger to be "write-ahead,
#: append-only, **committed** — it is what makes the one-way transition
#: auditable". It was living under the scratch root, which `.gitignore` excludes
#: by name ("Never evidence, and never swept into a commit"). A review role put
#: the two side by side: the irreversible record of what had been seen would
#: have survived only in an untracked, deletable file, and the design purpose it
#: exists for would not have held.
#:
#: Both requirements are real and they pull apart, so the roots do too. Research
#: output stays ignored; the ledgers that record an irreversible transition are
#: committed. Separating them is also what §6 of the R1 enablement brief asks
#: for in as many words: "research outputとは分離".
LEDGER_SUBDIRECTORY: Final[str] = "ledger"
LEDGER_ROOT_RELATIVE: Final[str] = f"{SCRATCH_ROOT_RELATIVE}/{LEDGER_SUBDIRECTORY}"

#: Roots Track A may never write into.  The first four are
#: ``guards._PROTECTED_PREFIXES``; ``artifacts/m15_gate3a`` is added here because
#: NR-A leaves it out of that tuple while §8.11.9 item 6 forbids the write.
FORBIDDEN_WRITE_PREFIXES: Final[tuple[str, ...]] = (
    "artifacts/ml_step4/365d_ba_v1",
    "artifacts/gate_p1_pr_b/firstrun_365d_ba",
    "artifacts/gate_p1_pr_b/firstrun_730d_ba",
    "artifacts/gate_p1_pr_b/firstrun_3650d_ba",
    "artifacts/m15_gate3a",
    "artifacts/oanda_archive_2026-05-31",
    "data",
    "models",
    "docs",
    "src",
    "scripts",
    "tests",
)

#: Canonical filenames of committed artifacts.  §8.12.13 G-9: no Track A file
#: may bear one, anywhere — the root constraint alone does not stop a Track A
#: file being mistaken for evidence by its name.
RESERVED_ARTIFACT_FILENAMES: Final[frozenset[str]] = frozenset(
    {
        "scrub_report.json",
        "no_overlap_proof.json",
        "design_m15_inventory.json",
        "design_m15_derivation_manifest.json",
        "forward_epoch_inventory.json",
        "forward_epoch_adoption_manifest.json",
        "effective_n_estimator_spec.json",
        "cost_table_plan_or_metadata.json",
        "candles_manifest.json",
        "raw_inventory_365d_BA.json",
    }
)


class ScratchRootError(RuntimeError):
    """Raised when a Track A write is outside the scratch root or is otherwise refused."""


#: Resolved once.  ``Path.resolve()`` hits the filesystem, and the isolation
#: hook asks for this root on **every** file operation in the process — it was
#: a measurable share of the guard's cost. The repository root cannot move
#: while the interpreter is running.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """The repository root, derived from this file's location."""
    return _REPO_ROOT


def scratch_root() -> Path:
    """The absolute Track A scratch root.  Not created here."""
    return repo_root() / SCRATCH_ROOT_RELATIVE


def ledger_root() -> Path:
    """The committed governance-ledger root, created on demand.

    A **subdirectory of the scratch root**, and that placement is the whole
    design. It gives the two properties that pull against each other:

    * ``.gitignore`` ignores the scratch root's *contents* and then un-ignores
      this one directory by name, so the ledgers are committed while research
      output stays out of every commit;
    * every write still lands inside the scratch root, so the isolation layer's
      classification, its append-only ledger identities and ``assert_writable``
      need no exception carved into them. A sibling root would have required
      one in each, and those are the most-audited surfaces in this package.
    """
    root = scratch_root() / LEDGER_SUBDIRECTORY
    root.mkdir(parents=True, exist_ok=True)
    return root


def _forbidden_roots() -> tuple[tuple[Path, str], ...]:
    root = repo_root()
    return tuple((root / prefix, prefix) for prefix in FORBIDDEN_WRITE_PREFIXES)


#: The reserved names, case-folded once.  NTFS and macOS both treat
#: ``Scrub_Report.JSON`` and ``scrub_report.json`` as the same file, so a
#: case-sensitive membership test refuses one spelling of a name and admits
#: another spelling of the same file. §8.12.13 G-9 says "no Track A file may
#: bear one, **anywhere**" — which is a statement about the file, not about how
#: the caller happened to type it.
_RESERVED_FOLDED: Final[frozenset[str]] = frozenset(
    name.casefold() for name in RESERVED_ARTIFACT_FILENAMES
)

#: Files beneath the scratch root that may only ever be **appended** to.
#: :mod:`~scripts.m15_track_a.isolation` reads this set to refuse a truncating
#: open of any of them: an append-only API binds only its own callers, and one
#: ``Path.write_text("")`` erases a `BINDING_GOVERNANCE_RECORD` that no ruling
#: can restore.
APPEND_ONLY_FILENAMES: Final[frozenset[str]] = frozenset(
    {
        "exploratory_seen_ledger.jsonl",
        "exploratory_oos_budget.jsonl",
        "exploration_breadth.jsonl",
        "track_a_authorization_ledger.jsonl",
    }
)


#: How long :func:`append_line` waits for the ledger lock before refusing.
APPEND_LOCK_TIMEOUT_SECONDS: Final[float] = 30.0

#: After this long, a lock is treated as abandoned and broken.  A lock leaks on
#: ``SIGKILL`` or ``os._exit``, and nothing else clears it: without this, one
#: killed writer halts every governance ledger permanently, which is a denial of
#: service on the write-ahead declaration that must precede any read.  The
#: window is two orders of magnitude longer than a real append (milliseconds),
#: so breaking a lock this old does not race a live writer.
APPEND_LOCK_STALE_SECONDS: Final[float] = 120.0

_APPEND_LOCK_POLL_SECONDS: Final[float] = 0.002


def _break_lock_if_abandoned(lock: Path) -> None:
    """Remove a lock whose holder is gone.

    Judged by age alone. A PID would be more precise and is not reliable: the
    number is reused, and the holder may be on another machine sharing the
    directory. Age is coarse and cannot wrongly break a live lock, because an
    append takes milliseconds and the threshold is two minutes.
    """
    try:
        age = time.time() - lock.stat().st_mtime
    except OSError:
        return
    if age < APPEND_LOCK_STALE_SECONDS:
        return
    with contextlib.suppress(OSError):
        os.unlink(lock)


def append_line(path: Path, line: str) -> None:
    """Append one line to a ledger, under a cross-process lock.

    Two failed attempts are recorded here because the third is only
    understandable against them.

    ``open(path, "a")`` goes through a buffered text wrapper: under concurrent
    writers, lines interleave and whole records are lost — measured at 109 of
    120 with four processes. Replacing it with a single ``os.write`` to a
    descriptor opened ``O_APPEND`` was **not** the fix, though the docstring
    then claimed atomicity "on both POSIX and Windows": the Windows CRT
    emulates ``O_APPEND`` as seek-then-write, which is not atomic across
    processes, and the same probe then measured 105–113 of 120.

    So the lock is explicit — an ``O_CREAT | O_EXCL`` lock file, the same
    primitive :mod:`~scripts.m15_track_a.oos_budget` uses successfully for the
    ``N = 1`` claim, because it is the only cross-process mutual exclusion
    available here without a lock service. A writer that cannot take the lock
    within :data:`APPEND_LOCK_TIMEOUT_SECONDS` **refuses**; it does not write
    unlocked. A lock older than :data:`APPEND_LOCK_STALE_SECONDS` is treated as
    abandoned and broken — without that, one writer killed mid-append halts
    every ledger permanently, and the write-ahead declaration that must precede
    any read is the first thing it halts.
    """
    # The lock is derived from the **resolved** ledger path, and is not
    # re-checked: it lives in the directory that was just cleared, and a path
    # check on a file that another process is unlinking right now resolves
    # through Windows' `\$Extend\$Deleted` and fails with access denied. The
    # check belongs on the path a caller supplied, not on one this function
    # derives from it.
    resolved = assert_writable(path)
    lock = resolved.with_name(resolved.name + ".lock")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    payload = (line + "\n").encode("utf-8")

    nonce = f"{os.getpid()}:{id(payload)}".encode()
    deadline = time.monotonic() + APPEND_LOCK_TIMEOUT_SECONDS
    while True:
        try:
            handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                os.write(handle, nonce)
            finally:
                os.close(handle)
            break
        # ``FileExistsError`` is another writer holding the lock. ``PermissionError``
        # is the same thing one moment later: Windows reports ERROR_ACCESS_DENIED,
        # not ERROR_FILE_EXISTS, for a name whose delete is still pending — and
        # catching only the first lost 27 of 120 lines in one measured round,
        # because the writer crashed instead of retrying.
        except (FileExistsError, PermissionError):
            _break_lock_if_abandoned(lock)
            if time.monotonic() >= deadline:
                raise ScratchRootError(
                    f"could not take the append lock for {path.name} within "
                    f"{APPEND_LOCK_TIMEOUT_SECONDS}s. Refusing rather than appending "
                    "unlocked — an unlocked append loses whole records."
                ) from None
            time.sleep(_APPEND_LOCK_POLL_SECONDS)

    try:
        # ``O_BINARY`` matters: on Windows ``os.open`` defaults to text mode, so
        # the line terminator this function writes reached the file as CRLF and
        # the ledger's bytes differed by platform. A BINDING_GOVERNANCE_RECORD
        # that may later be hashed has to be byte-identical wherever it was
        # written.
        fd = os.open(
            resolved,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0),
            0o644,
        )
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
    finally:
        # Unlink only **our** lock. A holder that stalled past the staleness
        # threshold would otherwise delete the lock a second writer had since
        # taken, and a third could then enter alongside it.
        with contextlib.suppress(OSError):
            if lock.read_bytes() == nonce:
                os.unlink(lock)


def assert_writable(path: Any) -> Path:
    """Return the resolved path if Track A may write it; otherwise raise.

    Three independent checks, all fail-closed, in the order that makes the
    error most informative:

    1. the path resolves under the path authority (which refuses relative
       spellings, stream suffixes, the Win32 normalisable-component class and
       the non-drive namespace outright);
    2. it is **inside** the scratch root — a positive containment test;
    3. its filename is not a committed artifact's canonical name.

    Check 2 makes check 3 redundant for a well-behaved caller.  It is kept
    because §9's honesty condition for the reserved-filename OUT ruling depends
    on the root being constant, and a defence that rests on one condition is
    weaker than one that rests on two.
    """
    try:
        candidate = resolve_candidate(path)
    except PathAuthorityError as exc:
        raise ScratchRootError(f"Track A write refused: {exc}") from exc

    root = scratch_root()
    if not is_within(candidate, root):
        for forbidden, label in _forbidden_roots():
            if is_within(candidate, forbidden):
                raise ScratchRootError(
                    f"Track A write refused: {candidate} is inside the protected root "
                    f"{label!r}. Track A writes only beneath {SCRATCH_ROOT_RELATIVE}."
                )
        raise ScratchRootError(
            f"Track A write refused: {candidate} is outside the scratch root "
            f"{SCRATCH_ROOT_RELATIVE}. Every Track A output goes beneath it, and nothing "
            "goes anywhere else."
        )

    name = candidate.name
    if name.casefold() in _RESERVED_FOLDED:
        raise ScratchRootError(
            f"Track A write refused: {name!r} is the canonical filename of a committed "
            "artifact. A Track A output may not bear one, anywhere — a file that looks "
            "like evidence can be cited as evidence (§8.12.13 G-9)."
        )
    return candidate


def is_writable(path: Any) -> bool:
    """Predicate form of :func:`assert_writable`, for reporting rather than enforcement."""
    try:
        assert_writable(path)
    except ScratchRootError:
        return False
    return True


__all__ = [
    "FORBIDDEN_WRITE_PREFIXES",
    "APPEND_LOCK_STALE_SECONDS",
    "APPEND_LOCK_TIMEOUT_SECONDS",
    "APPEND_ONLY_FILENAMES",
    "RESERVED_ARTIFACT_FILENAMES",
    "SCRATCH_ROOT_RELATIVE",
    "ScratchRootError",
    "append_line",
    "assert_writable",
    "is_writable",
    "repo_root",
    "scratch_root",
]
