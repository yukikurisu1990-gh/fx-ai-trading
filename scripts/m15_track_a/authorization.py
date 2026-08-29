"""The single authorisation gate for every Track A route that could reach real data.

**`EXPLICIT_TRACK_A_DATA_READ_AUTHORIZATION_REQUIRED`.**

The principle this module exists to enforce is the one the 2026-08
process-boundary incident produced and ``tests/optin.py`` states for tests:

    the presence of a resource is not authorization to use it

Here it is applied one level up.  A file on disk, a configured path, a merged
contract, an approved PR — none of them authorises a read.  Only a **grant**
does, and a grant is an in-process object a caller must construct and pass
explicitly to the route it authorises.

Why an in-process object and not an environment variable
--------------------------------------------------------

An environment variable is ambient: it authorises every route in the process,
for the whole process lifetime, and it survives into subprocesses.  §8.12's
`CONTRACT_PERMISSION_IS_NOT_EXECUTION_AUTHORISATION` and playbook §2.9's
"approval scope is exact" both require the opposite — an approval covers *the
operation and head it names*.  So a grant here names:

* the **operation** (one of a closed set),
* the **span** it covers, as explicit UTC dates,
* the **pairs** and **timeframe** it covers,
* the **head SHA** the approval was given against,
* and the **approver record** — where the human + ChatGPT approval is written
  down.

A route checks that the grant it was handed covers the operation it is about to
perform.  A grant for one span does not authorise another; a grant for a read
does not authorise a derivation.

What this module deliberately does not do
-----------------------------------------

It does not read anything, does not verify that the approver record exists on
disk, and does not consult the network or a database to check an approval.  It
is a structural gate: it makes the absence of an authorisation a **hard,
early, typed failure**, so an unauthorised route cannot proceed by accident.
Whether the approval it names is genuine is a governance question answered by
the merge ceremony, not by this file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

TOKEN: Final[str] = "EXPLICIT_TRACK_A_DATA_READ_AUTHORIZATION_REQUIRED"

#: The closed set of operations a grant may authorise.  A route names exactly
#: one of these; an unknown operation fails closed rather than being treated as
#: a new capability.
OPERATION_HISTORICAL_READ: Final[str] = "track_a_historical_read"
OPERATION_M15_DERIVATION: Final[str] = "track_a_m15_research_derivation"
OPERATION_OOS_SLICE_READ: Final[str] = "track_a_exploratory_oos_slice_read"

KNOWN_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        OPERATION_HISTORICAL_READ,
        OPERATION_M15_DERIVATION,
        OPERATION_OOS_SLICE_READ,
    }
)

_SHA_RE: Final[re.Pattern[str]] = re.compile(r"\A[0-9a-f]{40}\Z")
_DATE_RE: Final[re.Pattern[str]] = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")


class AuthorizationError(RuntimeError):
    """Raised when a Track A route is attempted without a covering grant."""


class AuthorizationMalformedError(AuthorizationError):
    """Raised when a grant is structurally invalid.

    A subclass so a test can name the construction failure specifically, while
    every existing ``AuthorizationError`` handler keeps failing closed.
    """


def _require_text(value: Any, what: str) -> str:
    if type(value) is not str:  # noqa: E721 - a str subclass may lie about its content
        raise AuthorizationMalformedError(f"{what} must be a plain str, got {type(value).__name__}")
    stripped = value.strip()
    if not stripped:
        raise AuthorizationMalformedError(f"{what} must not be empty")
    if stripped != value:
        raise AuthorizationMalformedError(f"{what} must not carry surrounding whitespace")
    return value


def _require_date(value: Any, what: str) -> str:
    text = _require_text(value, what)
    if not _DATE_RE.match(text):
        raise AuthorizationMalformedError(
            f"{what} must be an ISO UTC date YYYY-MM-DD, got {text!r}"
        )
    try:
        datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise AuthorizationMalformedError(f"{what} is not a real date: {text!r}") from exc
    return text


@dataclass(frozen=True)
class ReadGrant:
    """One explicit human + ChatGPT authorisation, scoped to what it names.

    Construct it only from a recorded approval.  Every field is required, and
    every field is checked at construction — a grant that cannot be validated
    does not exist, rather than existing in a half-usable state.
    """

    operation: str
    span_start_utc: str
    span_end_utc: str
    pairs: tuple[str, ...]
    timeframe: str
    approved_head_sha: str
    approver_record: str

    def __post_init__(self) -> None:
        operation = _require_text(self.operation, "operation")
        if operation not in KNOWN_OPERATIONS:
            raise AuthorizationMalformedError(
                f"unknown operation {operation!r}; a grant may only authorise one of "
                f"{sorted(KNOWN_OPERATIONS)} (fail closed)"
            )
        start = _require_date(self.span_start_utc, "span_start_utc")
        end = _require_date(self.span_end_utc, "span_end_utc")
        if start > end:
            raise AuthorizationMalformedError(f"span_start_utc {start} is after span_end_utc {end}")

        if type(self.pairs) is not tuple:
            raise AuthorizationMalformedError("pairs must be a tuple")
        if not self.pairs:
            raise AuthorizationMalformedError("pairs must name at least one pair")
        seen: set[str] = set()
        for pair in self.pairs:
            text = _require_text(pair, "pair")
            if text in seen:
                raise AuthorizationMalformedError(f"duplicate pair in grant: {text!r}")
            seen.add(text)

        _require_text(self.timeframe, "timeframe")

        sha = _require_text(self.approved_head_sha, "approved_head_sha")
        if not _SHA_RE.match(sha):
            raise AuthorizationMalformedError(
                "approved_head_sha must be a full 40-character lowercase hex SHA — an "
                "abbreviated or absent SHA cannot identify the head an approval was given "
                f"against (got {sha!r})"
            )

        record = _require_text(self.approver_record, "approver_record")
        if len(record) < 8:
            raise AuthorizationMalformedError(
                "approver_record must locate the recorded human + ChatGPT approval "
                "(a PR reference, a document section, or an equivalent)"
            )

    # -- coverage ----------------------------------------------------------

    def covers(
        self,
        *,
        operation: str,
        span_start_utc: str,
        span_end_utc: str,
        pairs: tuple[str, ...],
        timeframe: str,
    ) -> bool:
        """Convenience wrapper over :func:`grant_covers`.

        The gate itself never calls this method: an overridable method is a
        thing a subclass can make answer ``True``. :func:`require_authorization`
        calls the module-level function against the grant's fields instead.
        """
        return grant_covers(
            self,
            operation=operation,
            span_start_utc=span_start_utc,
            span_end_utc=span_end_utc,
            pairs=pairs,
            timeframe=timeframe,
        )

    def as_record(self) -> dict[str, Any]:
        """The grant as a plain dict, for the ledger and the run record."""
        return {
            "operation": self.operation,
            "span_start_utc": self.span_start_utc,
            "span_end_utc": self.span_end_utc,
            "pairs": list(self.pairs),
            "timeframe": self.timeframe,
            "approved_head_sha": self.approved_head_sha,
            "approver_record": self.approver_record,
        }


def _revalidate(grant: ReadGrant) -> None:
    """Re-run every construction check on an existing grant.

    ``__post_init__`` runs from ``__init__``. It does not run for
    ``object.__new__``, for an unpickled instance, or after an
    ``object.__setattr__`` on a frozen field. Re-running the checks here means
    the gate validates the object it was handed rather than the object it
    assumes was constructed.
    """
    try:
        ReadGrant.__post_init__(grant)
    except AuthorizationMalformedError:
        raise
    except Exception as exc:  # pragma: no cover - a malformed object of any shape
        raise AuthorizationMalformedError(f"grant failed re-validation: {exc}") from exc


def grant_covers(
    grant: ReadGrant,
    *,
    operation: str,
    span_start_utc: str,
    span_end_utc: str,
    pairs: tuple[str, ...],
    timeframe: str,
) -> bool:
    """True only when the grant covers **all** of the requested scope.

    Coverage is containment, not overlap: a request reaching one day beyond the
    granted span is not covered, and a request naming one pair the grant omits
    is not covered.

    Both sides of every comparison are validated first. A string comparison of
    span bounds is chronological only once both operands are known to be
    zero-padded ISO dates: an unpadded ``2025-1-15`` sorts *after* ``2025-06-01``
    at index five, so an unvalidated request date reads as inside the grant when
    it is outside it.
    """
    _require_date(span_start_utc, "requested span_start_utc")
    _require_date(span_end_utc, "requested span_end_utc")
    _require_date(grant.span_start_utc, "granted span_start_utc")
    _require_date(grant.span_end_utc, "granted span_end_utc")
    if _require_text(operation, "operation") != _require_text(grant.operation, "grant.operation"):
        return False
    if _require_text(timeframe, "timeframe") != _require_text(grant.timeframe, "grant.timeframe"):
        return False
    if span_start_utc < grant.span_start_utc or span_end_utc > grant.span_end_utc:
        return False
    if type(pairs) is not tuple:
        raise AuthorizationMalformedError("requested pairs must be a tuple")
    if not pairs:
        # ``all(...)`` over an empty tuple is True, so an empty request was
        # "covered" by every grant. A request for no pairs is malformed, not
        # universally authorised.
        raise AuthorizationMalformedError("a request must name at least one pair")
    granted = {_require_text(pair, "grant pair") for pair in grant.pairs}
    return all(_require_text(pair, "requested pair") in granted for pair in pairs)


def require_authorization(
    grant: Any,
    *,
    operation: str,
    span_start_utc: str,
    span_end_utc: str,
    pairs: tuple[str, ...],
    timeframe: str,
    identity: Any = None,
) -> ReadGrant:
    """Return the grant if it covers the requested scope; otherwise raise.

    ``grant=None`` is the ordinary case today and raises with the token, so a
    caller reading the traceback learns what is missing rather than what broke.

    Three deliberate strictnesses, each closing a defeat found by review:

    * **Exact type, not ``isinstance``.** A ``ReadGrant`` subclass can neutralise
      ``__post_init__`` and answer coverage however it likes.
    * **Re-validation at check time, not only at construction.**
      ``object.__new__(ReadGrant)`` never runs ``__post_init__``, and
      ``object.__setattr__`` rewrites a frozen field after it. Every field is
      re-checked here, against the same rules.
    * **The approved head is compared, not merely shaped.** A 40-hex string that
      is never equal to anything is decoration. When an identity is supplied its
      ``code_sha`` must equal the grant's ``approved_head_sha`` — CLAUDE.md's
      "any head change voids the approval", in executable form.

    What it still cannot do: stop code in the same process from constructing a
    wider grant than the human approved. Nothing in-process can, because such
    code could bypass this function entirely. The controls for that are the
    audit hook in :mod:`~scripts.m15_track_a.isolation`, which makes the read
    itself fail, and the grant being recorded so the scope it claimed is
    auditable against the approval document.
    """
    if grant is None:
        raise AuthorizationError(
            f"{TOKEN}: {operation} refused. No grant was supplied. Track A's first "
            "real-data read requires an explicit human + ChatGPT authorisation naming the "
            "operation, the span, the pairs, the timeframe and the approved head SHA "
            "(scripts.m15_track_a.authorization.ReadGrant)."
        )
    if type(grant) is not ReadGrant:
        raise AuthorizationError(
            f"{TOKEN}: {operation} refused. A grant must be exactly a ReadGrant constructed "
            f"from a recorded approval, not a {type(grant).__name__} — a subclass can "
            "neutralise the construction checks and answer coverage however it likes."
        )
    _revalidate(grant)
    if operation not in KNOWN_OPERATIONS:
        raise AuthorizationError(f"{TOKEN}: unknown operation {operation!r} (fail closed)")
    if identity is not None:
        from scripts.m15_track_a.identity import RunIdentity

        if type(identity) is not RunIdentity:
            # Duck-typing the head check in a module that pins ``type(x) is str``
            # everywhere else would let any object with a matching attribute
            # satisfy it.
            raise AuthorizationError(
                f"{TOKEN}: identity must be exactly a RunIdentity, not a {type(identity).__name__}."
            )
        code_sha = identity.code_sha
        if code_sha != grant.approved_head_sha:
            raise AuthorizationError(
                f"{TOKEN}: the grant was approved against head {grant.approved_head_sha!r} "
                f"and the run is on {code_sha!r}. An approval covers the head it names; a "
                "head change voids it (CLAUDE.md)."
            )
    if not grant_covers(
        grant,
        operation=operation,
        span_start_utc=span_start_utc,
        span_end_utc=span_end_utc,
        pairs=pairs,
        timeframe=timeframe,
    ):
        raise AuthorizationError(
            f"{TOKEN}: the supplied grant does not cover this request. "
            f"Granted: {grant.operation} {grant.span_start_utc}..{grant.span_end_utc} "
            f"{grant.timeframe} over {len(grant.pairs)} pair(s). "
            f"Requested: {operation} {span_start_utc}..{span_end_utc} {timeframe} over "
            f"{len(pairs)} pair(s). An approval covers the operation and scope it names "
            "(playbook §2.9)."
        )
    return grant


__all__ = [
    "KNOWN_OPERATIONS",
    "grant_covers",
    "OPERATION_HISTORICAL_READ",
    "OPERATION_M15_DERIVATION",
    "OPERATION_OOS_SLICE_READ",
    "TOKEN",
    "AuthorizationError",
    "AuthorizationMalformedError",
    "ReadGrant",
    "require_authorization",
]
