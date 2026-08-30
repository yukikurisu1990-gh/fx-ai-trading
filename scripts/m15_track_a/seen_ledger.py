"""The write-ahead ``EXPLORATORY_SEEN_DATA`` ledger.

§8.11.4 as corrected by §8.12.13 C-1 and §8.13.13: an interval is declared
**before** it is touched, the declaration is what binds, and the record is
append-only.  Seven rules govern it, and each is enforced here or is recorded as
enforced elsewhere:

1. **Unrecorded is seen.**  Any span inside a window a run touched, and not
   recorded at finer granularity, is presumed seen in full.  Enforced by
   :func:`assert_declared` — a read whose scope is not covered by a *prior*
   declaration is refused, so an undeclared read cannot happen rather than
   being retroactively presumed.
2. **Warm-up and lookback count as observation.**  A caller declares the
   interval it will *touch*, not the interval it will *label*; the read route
   passes the widened interval.
3. **An entry is never removed, narrowed or downgraded.**  The file is opened
   append-only and :func:`declare` refuses to rewrite history.
4. **Marking follows the source minutes and reaches every timeframe.**  Coverage
   ignores the timeframe field when deciding whether an interval is already
   seen; the field records *how* it was seen.
5. **Marking reaches every pair over the interval.**  Same: the pair field
   records *which* pairs were read, never narrows *what* was seen.
6. **A discarded run still spends its data.**  Nothing here can un-declare.
7. **Write-ahead.**  :func:`declare` must be called and must have returned
   before the read begins.

Both tracks
-----------

§8.12.13 C-1 extends the trigger to **either track** and §8.13.13 D-9 makes it
contact rather than completion, so a Track B confirmation observation is
declared here too.  This module does not know about tracks; it knows about
intervals.

Not a formal-evidence artifact
------------------------------

The ledger is a ``BINDING_GOVERNANCE_RECORD`` (§8.12.13 G-6), not research
output — the non-decision-bearing label does not reach it, because it is what
constrains a formal claim.  It is written beneath the Track A scratch root for
now; committing it is a governance-propagation item, not something this module
decides.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from scripts.m15_track_a import scratch
from scripts.m15_track_a.identity import RunIdentity
from scripts.m15_track_a.scratch import ScratchRootError, assert_writable

LEDGER_FILENAME: Final[str] = "exploratory_seen_ledger.jsonl"

#: Where an exercised authorisation is recorded, beside the interval it covered.
GRANT_LEDGER_FILENAME: Final[str] = "track_a_authorization_ledger.jsonl"

#: The ledger's own classification.  It constrains a formal claim, so the
#: non-decision-bearing label does not reach it (§8.12.13 G-6).
LEDGER_CLASSIFICATION: Final[str] = "BINDING_GOVERNANCE_RECORD"

_DATE_RE: Final[re.Pattern[str]] = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")


class SeenLedgerError(RuntimeError):
    """Raised when a declaration is malformed, or a read is attempted undeclared."""


def _require_pair(value: Any) -> str:
    """Pin a pair name to an exact ``str``.

    Membership here is ``__hash__``/``__eq__``, so a ``str`` subclass can hash
    and compare as ``EUR_USD`` while holding ``XAU_USD``. That would void the
    pair scope of the seen-data record — the record would say one pair was seen
    while another was read.
    """
    if type(value) is not str or not value.strip():  # noqa: E721
        raise SeenLedgerError(f"malformed pair: {value!r}")
    return value


def _require_date(value: Any, what: str) -> str:
    if type(value) is not str:  # noqa: E721
        raise SeenLedgerError(f"{what} must be a plain str, got {type(value).__name__}")
    if not _DATE_RE.match(value):
        raise SeenLedgerError(f"{what} must be an ISO UTC date YYYY-MM-DD, got {value!r}")
    return value


@dataclass(frozen=True)
class SeenDeclaration:
    """One write-ahead declaration of an interval a run intends to touch."""

    run_id: str
    span_start_utc: str
    span_end_utc: str
    pairs: tuple[str, ...]
    timeframe: str
    purpose: str

    def __post_init__(self) -> None:
        start = _require_date(self.span_start_utc, "span_start_utc")
        end = _require_date(self.span_end_utc, "span_end_utc")
        if start > end:
            raise SeenLedgerError(f"span_start_utc {start} is after span_end_utc {end}")
        if type(self.pairs) is not tuple or not self.pairs:
            raise SeenLedgerError("pairs must be a non-empty tuple")
        for pair in self.pairs:
            if type(pair) is not str or not pair.strip():  # noqa: E721
                raise SeenLedgerError(f"malformed pair in declaration: {pair!r}")
        for field, value in (
            ("run_id", self.run_id),
            ("timeframe", self.timeframe),
            ("purpose", self.purpose),
        ):
            if type(value) is not str or not value.strip():  # noqa: E721
                raise SeenLedgerError(f"{field} must be a non-empty plain str")

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "span_start_utc": self.span_start_utc,
            "span_end_utc": self.span_end_utc,
            "pairs": list(self.pairs),
            "timeframe": self.timeframe,
            "purpose": self.purpose,
            "classification": LEDGER_CLASSIFICATION,
        }

    def covers(self, *, span_start_utc: str, span_end_utc: str, pairs: tuple[str, ...]) -> bool:  # noqa: E501
        """True when this declaration covers the requested interval and pairs.

        **Timeframe is deliberately ignored** (rule 4): declaring M15 over an
        interval declares that interval, because every timeframe over it is the
        same underlying minutes seen at a different resolution.
        """
        if span_start_utc < self.span_start_utc or span_end_utc > self.span_end_utc:
            return False
        declared = {_require_pair(pair) for pair in self.pairs}
        return all(_require_pair(pair) in declared for pair in pairs)


def ledger_path() -> Path:
    """The ledger's location beneath the Track A scratch root."""
    return scratch.scratch_root() / LEDGER_FILENAME


def declare(declaration: SeenDeclaration, identity: RunIdentity) -> Path:
    """Append a write-ahead declaration and return the ledger path.

    Append-only by construction: the file is opened in ``"a"`` mode, this module
    exposes no delete or rewrite, and the path is checked by the scratch-root
    authority before opening so the ledger cannot be redirected outside it.
    """
    if declaration.run_id != identity.run_id:
        raise SeenLedgerError(
            f"declaration run_id {declaration.run_id!r} does not match the identity's "
            f"{identity.run_id!r} — a declaration attributes to the run that makes it"
        )
    path = ledger_path()
    try:
        assert_writable(path)
    except ScratchRootError as exc:  # pragma: no cover - the path is a module constant
        raise SeenLedgerError(f"ledger path refused by the scratch authority: {exc}") from exc

    entry = {"declaration": declaration.as_record(), "identity": identity.as_record()}
    line = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    scratch.append_line(path, line)
    return path


def grant_ledger_path() -> Path:
    """Where the scope an approval was exercised at is recorded."""
    return scratch.scratch_root() / GRANT_LEDGER_FILENAME


def record_grant(grant: Any, identity: RunIdentity, *, route: str) -> Path:
    """Record the authorisation a route ran under, before it runs.

    A grant that leaves no trace cannot be audited against the approval
    document it claims to come from. This is the record that makes the claimed
    scope checkable after the fact — it does not make the claim true, and this
    module does not pretend it does.
    """
    path = grant_ledger_path()
    try:
        assert_writable(path)
    except ScratchRootError as exc:  # pragma: no cover - the path is a constant
        raise SeenLedgerError(f"grant ledger path refused: {exc}") from exc
    entry = {
        "grant": grant.as_record(),
        "identity": identity.as_record(),
        "route": route,
        "classification": LEDGER_CLASSIFICATION,
    }
    scratch.append_line(
        path, json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )
    return path


def read_declarations() -> tuple[SeenDeclaration, ...]:
    """Every declaration recorded so far, in the order it was written."""
    path = ledger_path()
    if not path.exists():
        return ()
    out: list[SeenDeclaration] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        payload = json.loads(raw)["declaration"]
        out.append(
            SeenDeclaration(
                run_id=payload["run_id"],
                span_start_utc=payload["span_start_utc"],
                span_end_utc=payload["span_end_utc"],
                pairs=tuple(payload["pairs"]),
                timeframe=payload["timeframe"],
                purpose=payload["purpose"],
            )
        )
    return tuple(out)


def assert_declared(*, span_start_utc: str, span_end_utc: str, pairs: tuple[str, ...]) -> None:
    """Refuse unless a **prior** declaration covers the whole requested interval.

    This is the write-ahead property in enforceable form: at read time the
    declaration must already be on the ledger.  A single declaration must cover
    the request — a request is not satisfied by stitching two partial
    declarations together, because that is how a widened read gets recorded as
    two narrower ones.
    """
    _require_date(span_start_utc, "span_start_utc")
    _require_date(span_end_utc, "span_end_utc")
    for declaration in read_declarations():
        if declaration.covers(
            span_start_utc=span_start_utc, span_end_utc=span_end_utc, pairs=pairs
        ):
            return
    raise SeenLedgerError(
        f"no prior seen-data declaration covers {span_start_utc}..{span_end_utc} over "
        f"{len(pairs)} pair(s). The interval a run will touch is declared **before** it is "
        "touched; unrecorded is seen, and a read that was never declared cannot be "
        "distinguished from one that was concealed."
    )


__all__ = [
    "GRANT_LEDGER_FILENAME",
    "LEDGER_CLASSIFICATION",
    "LEDGER_FILENAME",
    "SeenDeclaration",
    "SeenLedgerError",
    "assert_declared",
    "declare",
    "grant_ledger_path",
    "ledger_path",
    "record_grant",
    "read_declarations",
]
