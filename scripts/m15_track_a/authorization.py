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
import weakref
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
_FINGERPRINT_RE: Final[re.Pattern[str]] = re.compile(r"\A[0-9a-f]{64}\Z")
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


def _assert_operation_span(operation: str, start: str, end: str) -> None:
    """A grant may not name a span its own operation is not allowed to read.

    Coverage is *containment*, so a grant is allowed to be wider than the
    request it covers — and a review role turned that into the whole exploit:
    with a grant reaching `2026-02-28`, a `ReadRequest` subclass that answered
    honestly at the gates and widened afterwards returned all 62 quarantined
    slice dates. Narrowing the grant to the ruled corpus reduced the same attack
    to zero slice rows, which makes the grant's own ceiling the load-bearing
    backstop rather than a formality.

    So the ruling is enforced on the **grant object**, where no caller-supplied
    request can reach it:

    * `track_a_historical_read` may not name a date at or after the
      `EXPLORATORY_OOS_SLICE` start;
    * `track_a_exploratory_oos_slice_read` may name **only** slice dates —
      the same rule in the other direction, so an OOS approval cannot be spent
      on development data either.

    `track_a_m15_research_derivation` is deliberately not constrained here: it
    derives over whatever its own read was authorised for, and its route applies
    the development gate itself.
    """
    from scripts.m15_track_a.oos_slice import DEVELOPMENT_END_UTC, SLICE_END_UTC, SLICE_START_UTC

    if operation == OPERATION_HISTORICAL_READ and end > DEVELOPMENT_END_UTC:
        raise AuthorizationMalformedError(
            f"a {OPERATION_HISTORICAL_READ} grant may not reach {end}: the committed "
            f"development corpus ends at {DEVELOPMENT_END_UTC}, and "
            f"{SLICE_START_UTC}..{SLICE_END_UTC} is the EXPLORATORY_OOS_SLICE, which R-2 "
            "quarantines from every stage before R4. Reading it is a separate operation "
            f"({OPERATION_OOS_SLICE_READ}) with its own approval and an N = 1 budget."
        )
    if operation == OPERATION_OOS_SLICE_READ and not (
        start >= SLICE_START_UTC and end <= SLICE_END_UTC
    ):
        raise AuthorizationMalformedError(
            f"a {OPERATION_OOS_SLICE_READ} grant may only name dates inside "
            f"{SLICE_START_UTC}..{SLICE_END_UTC}, and this one names {start}..{end}. An OOS "
            "approval is not a licence to read development data under a different name."
        )


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
    approved_implementation_fingerprint: str
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
        _assert_operation_span(operation, start, end)

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

        fingerprint = _require_text(
            self.approved_implementation_fingerprint, "approved_implementation_fingerprint"
        )
        if not _FINGERPRINT_RE.match(fingerprint):
            raise AuthorizationMalformedError(
                "approved_implementation_fingerprint must be a full 64-character lowercase "
                "hex sha256 of the declared implementation surface, as returned by "
                "scripts.m15_track_a.containment.implementation_fingerprint() at the head "
                f"the approval was given against (got {fingerprint!r})"
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
            "approved_implementation_fingerprint": self.approved_implementation_fingerprint,
            "approver_record": self.approver_record,
        }


#: Contexts that actually ran their own verification, keyed by object identity.
#:
#: A frozen dataclass hashes and compares **by value**, so a `set` keyed on the
#: object would accept an equal forgery as a member; and `id()` alone is reusable
#: once an object dies. Each entry therefore holds a weak reference checked with
#: `is`, and a callback removes the row when the object is collected.
_SEALED_BINDINGS: dict[int, tuple[weakref.ref, dict[str, Any]]] = {}


def _seal(context: VerifiedRunContext, record: dict[str, Any]) -> None:
    """Record that this exact object completed the verification, and what it saw."""
    key = id(context)

    def _forget(_ref: weakref.ref, key: int = key) -> None:
        _SEALED_BINDINGS.pop(key, None)

    _SEALED_BINDINGS[key] = (weakref.ref(context, _forget), record)


def sealed_binding(context: Any) -> dict[str, Any]:
    """The record written when **this** object ran ``__post_init__``, or refuse.

    Why the measurement does not live on the object
    -----------------------------------------------

    ``__post_init__`` runs from ``__init__``. It does not run for
    ``object.__new__``, for an unpickled instance, or after an
    ``object.__setattr__`` on a frozen field — which is exactly what
    :func:`_revalidate` was written for on :class:`ReadGrant`, and the same three
    routes apply here. A review role walked all three: an ``object.__new__``
    context carrying a grant approved against ``"0" * 64`` authorised a read that
    the per-call measurement refused.

    :class:`ReadGrant` closes that by re-running its own checks, which is
    affordable because they are pure. A context cannot: re-running its checks
    means re-measuring the tree, and not re-measuring is the entire point. So the
    measurement is kept **off** the object, in a side record this module writes
    and nothing can ``setattr`` into, and every security decision reads it from
    here. A forged or tampered context reaches no record and is refused.

    The limit is the one this module already states: code in the same process can
    reach this dict, just as it could bypass :func:`require_authorization`
    altogether. The controls for that are the isolation audit hook and the
    recorded grant, not this function.
    """
    if type(context) is not VerifiedRunContext:
        raise AuthorizationError(
            f"{TOKEN}: context must be exactly a VerifiedRunContext, not a "
            f"{type(context).__name__}."
        )
    entry = _SEALED_BINDINGS.get(id(context))
    if entry is None:
        raise AuthorizationError(
            f"{TOKEN}: this context never ran its own verification. A context is the record "
            "of a measurement; one assembled without performing it is not one."
        )
    ref, record = entry
    if ref() is not context:
        raise AuthorizationError(
            f"{TOKEN}: this context does not match the verification recorded under its "
            "identity (fail closed)."
        )
    return record


@dataclass(frozen=True)
class VerifiedRunContext:
    """One R1 run's implementation binding, verified once and then reused.

    Why this exists
    ---------------

    `require_authorization` measures `implementation_fingerprint()` on **every**
    call — deliberately, because a grant checked against a tree the run is no
    longer executing is not a check. Once the read and the derivation ran per
    window, that became about **321** measurements a run, each parsing and
    hashing thirty-two source files: roughly two minutes, and most of it
    happening *after* the irreversible seen-data declaration, where a refusal
    costs the corpus rather than nothing.

    So the measurement moves to preflight and the result is frozen here. What is
    reused is the **implementation identity**. What is emphatically not reused is
    the data-scope validation, which still runs per window and per row exactly as
    before. Those are different checks, and this class separates them rather than
    collapsing them.

    Why constructing one is not a way around the gate
    -------------------------------------------------

    `__post_init__` performs the whole verification itself: it measures the
    fingerprint from the tree, pins both grants to the exact `ReadGrant` type,
    re-runs their construction checks, requires each to name its own operation
    and to carry the measured fingerprint, requires the two to name the same
    approved head, and requires the run identity to agree with it. A context
    holding a fabricated fingerprint cannot be built; one holding real grants is
    exactly what a verified preflight produces.

    It is frozen, and `require_authorization` accepts it only alongside a grant
    that is **the same object** this context verified — identity, not equality,
    because two equal grants are what a later divergence starts from.

    What it deliberately does **not** hold
    -------------------------------------

    A span, a pair list and a timeframe. An earlier drafting recorded the plan's
    scope here "for the record" and nothing ever read it, so a mutation that
    wrote `1970-01-01..2099-12-31 / ("XXX_YYY",) / NOT_A_TIMEFRAME` into it
    survived the whole suite and reached the R1 evidence record — the second time
    a fabricated span has travelled into this programme's evidence that way. The
    fields are gone rather than checked: a context is an **implementation
    identity**, the request is the scope, and the run record already carries the
    scope from the request. Conflating the two is what the reuse of this object
    is written to avoid.

    Nor does it hold the measurement itself; see :func:`sealed_binding`.
    """

    read_grant: ReadGrant
    derivation_grant: ReadGrant
    identity: Any

    #: **Measured, never supplied, and not stored on the object.** A first
    #: drafting took the fingerprint as a constructor argument and re-measured it
    #: to check the claim, which cost two full measurements and gave a caller
    #: something to assert. These read the sealed record instead, so there is
    #: nothing to assert and nothing to `object.__setattr__`: building a context
    #: *is* the measurement, and the run pays for exactly one.
    @property
    def fingerprint(self) -> str:
        """The tree hash measured while this context was built."""
        return str(sealed_binding(self)["fingerprint"])

    @property
    def approved_head_sha(self) -> str:
        """The head both grants name, kept so a reader need not open them."""
        return str(sealed_binding(self)["approved_head_sha"])

    @property
    def surface_stamp(self) -> tuple[tuple[str, str, int, int], ...]:
        """`(surface name, absolute path, size, mtime_ns)` per covered file.

        Captured at the same moment as the fingerprint. Cheap to re-check; see
        `containment.assert_surface_unchanged` for what it does and does not
        establish.
        """
        stamp: tuple[tuple[str, str, int, int], ...] = sealed_binding(self)["surface_stamp"]
        return stamp

    def __post_init__(self) -> None:
        from scripts.m15_track_a.containment import measure_surface
        from scripts.m15_track_a.identity import RunIdentity

        if type(self.identity) is not RunIdentity:
            raise AuthorizationMalformedError(
                f"identity must be exactly a RunIdentity, not a {type(self.identity).__name__}"
            )
        for label, grant, operation in (
            ("read", self.read_grant, OPERATION_HISTORICAL_READ),
            ("derivation", self.derivation_grant, OPERATION_M15_DERIVATION),
        ):
            if type(grant) is not ReadGrant:
                raise AuthorizationMalformedError(
                    f"the {label} grant must be exactly a ReadGrant, not a {type(grant).__name__}"
                )
            _revalidate(grant)
            if grant.operation != operation:
                raise AuthorizationMalformedError(
                    f"the {label} grant names {grant.operation!r}, not {operation!r}"
                )
        if self.read_grant is self.derivation_grant:
            raise AuthorizationMalformedError(
                "one grant object cannot be both the read and the derivation authorisation"
            )
        if self.read_grant.approved_head_sha != self.derivation_grant.approved_head_sha:
            raise AuthorizationMalformedError(
                "the two grants name different approved heads; one run, one approved implementation"
            )
        if self.identity.code_sha != self.read_grant.approved_head_sha:
            raise AuthorizationMalformedError(
                "the run identity names a different head from the grants"
            )

        # **The one measurement.** Taken here rather than accepted here, which
        # is the whole difference between a record of a verification and a
        # claim about one. `measure_surface` walks the surface once and returns
        # the hash and the stamp together: hashing and stamping separately meant
        # two walks, and the walk is ~205 ms of the ~207 ms.
        try:
            measured, stamp = measure_surface()
        except Exception as exc:  # noqa: BLE001 - re-raised as this module's type
            raise AuthorizationMalformedError(
                f"the implementation surface could not be measured: {exc}"
            ) from exc
        for label, grant in (("read", self.read_grant), ("derivation", self.derivation_grant)):
            if grant.approved_implementation_fingerprint != measured:
                raise AuthorizationMalformedError(
                    f"the {label} grant was approved against implementation "
                    f"{grant.approved_implementation_fingerprint!r} and the tree hashes to "
                    f"{measured!r}. The read implementation changed after the approval."
                )
        # Sealed off the object, and holding its **own** references to the two
        # grants and the identity: a later `object.__setattr__` on a frozen field
        # changes what the object says and cannot change what was verified.
        _seal(
            self,
            {
                "fingerprint": measured,
                "approved_head_sha": self.read_grant.approved_head_sha,
                "surface_stamp": stamp,
                "identity": self.identity,
                OPERATION_HISTORICAL_READ: self.read_grant,
                OPERATION_M15_DERIVATION: self.derivation_grant,
            },
        )

    def grant_for(self, operation: str) -> ReadGrant:
        """The grant this context **verified** for one operation.

        From the sealed record, not from `self`: the point of the lookup is to
        answer "which object did the verification cover", and reading it off a
        field an `object.__setattr__` can rewrite would answer "which object does
        this one claim now".
        """
        if operation not in (OPERATION_HISTORICAL_READ, OPERATION_M15_DERIVATION):
            raise AuthorizationError(
                f"{TOKEN}: this context verifies {OPERATION_HISTORICAL_READ} and "
                f"{OPERATION_M15_DERIVATION}, not {operation!r}"
            )
        grant: ReadGrant = sealed_binding(self)[operation]
        return grant

    def verified_identity(self) -> Any:
        """The run identity this context was verified against, from the record."""
        return sealed_binding(self)["identity"]

    def as_record(self) -> dict[str, Any]:
        """Implementation identity only — never a scope, never a grant, never a row.

        The scope the run is authorised for belongs to the request and to the two
        grants, and the R1 record carries it from there. It is deliberately not
        restated here; see the class docstring.
        """
        record = sealed_binding(self)
        return {
            "fingerprint": record["fingerprint"],
            "approved_head_sha": record["approved_head_sha"],
            "surface_files": len(record["surface_stamp"]),
            "read_grant": record[OPERATION_HISTORICAL_READ].operation,
            "derivation_grant": record[OPERATION_M15_DERIVATION].operation,
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
    identity: Any,
    context: Any = None,
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
    * **The approved implementation is measured, not asserted.** This replaced
      an equality between ``identity.code_sha`` and ``grant.approved_head_sha``,
      and the replacement is recorded rather than quietly made, because it
      *removed* a check.

      That check compared two **caller-asserted** strings: ``code_sha`` is never
      derived from the running tree, so a caller running anything at all could
      assert the approved head and pass. It therefore refused an honest run at
      the wrong head and refused a dishonest one never — and, worse, it made the
      sequence in which an approval is recorded self-defeating. Committing a
      grant into the repository moves ``HEAD``; an honest run at the new head
      would then be refused by the grant that commit exists to record
      (`READ_GRANT_BINDS_TO_APPROVED_IMPLEMENTATION_ANCESTRY_NOT_SELF_REFERENTIAL_EXECUTION_HEAD`).

      What replaces it is measured from disk:
      :func:`~scripts.m15_track_a.containment.implementation_fingerprint` hashes
      declared implementation surface — every ``.py`` under
      ``scripts/m15_track_a/`` plus the **transitive** first-party import
      closure, resolved through ``importlib`` so that a shadowed module is
      hashed as it will actually be loaded — and it must equal the value the
      grant records. So a commit that adds an authorisation
      record, a document or a governance note keeps the grant valid, and **any**
      change to what a read actually does invalidates it, whatever head the
      caller claims to be on.

      ``identity`` is still **required** and its ``code_sha`` is still recorded
      with the exercised grant: it defaulted to ``None`` once and skipped the
      head check silently.

      The limit, stated: this binds the **implementation**, not the *ancestry*.
      Whether the execution head descends from the approved head is a `git`
      question, and reaching git from inside a gated read would mean spawning a
      process the isolation layer exists to refuse. It is a gate-time obligation
      on the reviewer, written down in the execution gate document, not an
      in-process check — and it is the weaker of the two, since a head with
      identical implementation bytes reads identically wherever it sits.

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
    from scripts.m15_track_a.identity import RunIdentity

    if type(identity) is not RunIdentity:
        # Duck-typing the head check in a module that pins ``type(x) is str``
        # everywhere else would let any object with a matching attribute
        # satisfy it.
        raise AuthorizationError(
            f"{TOKEN}: identity must be exactly a RunIdentity, not a {type(identity).__name__}."
        )
    if context is not None:
        # **The verified binding, reused rather than re-measured.**
        #
        # This is an implementation-*identity* check, and it was being repeated
        # about 321 times a run — most of them after the irreversible seen-data
        # declaration, where a refusal costs the corpus instead of nothing. The
        # measurement now happens once, in `VerifiedRunContext.__post_init__`,
        # which cannot be constructed without it.
        #
        # The data-*scope* validation below is untouched and still runs on every
        # call: `grant_covers`, the span, the pairs, the timeframe. Reusing an
        # identity is not reusing a scope check, and conflating the two is the
        # mistake this branch is written to avoid.
        # Everything below comes from the **sealed record**, which only a context
        # that ran its own verification has. An `object.__new__` instance, an
        # unpickled one, and one whose frozen fields were `object.__setattr__`
        # after the fact all reach no record and are refused here — the same
        # three routes `_revalidate` closes for `ReadGrant`.
        record = sealed_binding(context)
        if grant is not record.get(operation):
            # Identity, not equality: an equal-looking grant is what a later
            # divergence starts from, and the context verified one object.
            raise AuthorizationError(
                f"{TOKEN}: the grant supplied for {operation} is not the object this run's "
                "context verified."
            )
        if identity is not record["identity"]:
            raise AuthorizationError(
                f"{TOKEN}: the run identity is not the one this context was verified against."
            )
        measured = record["fingerprint"]
    else:
        from scripts.m15_track_a.containment import implementation_fingerprint

        try:
            measured = implementation_fingerprint()
        except Exception as exc:
            # Wrapped, so a caller's ``except AuthorizationError`` cannot be
            # walked straight past by a bare RuntimeError from the surface walk.
            # The polarity is unchanged — an unmeasurable surface refuses the
            # read — but it now refuses as the type this module documents.
            raise AuthorizationError(
                f"{TOKEN}: the implementation surface could not be measured, so the grant "
                f"cannot be checked against it: {exc}"
            ) from exc
    if measured != grant.approved_implementation_fingerprint:
        raise AuthorizationError(
            f"{TOKEN}: the grant was approved against implementation "
            f"{grant.approved_implementation_fingerprint!r} (head "
            f"{grant.approved_head_sha!r}) and the tree this run is executing hashes to "
            f"{measured!r}. The read implementation changed after the approval, so the "
            "approval does not cover it. Recording an authorisation, a document or a "
            "governance note does not change this value; changing what a read does always "
            "does."
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


def assert_implementation_unchanged(context: Any) -> None:
    """Re-measure the tree **once**, at the end of a run, against the binding.

    Why one more measurement, when removing them was the point
    ----------------------------------------------------------

    Per-window rehashing bought evidence, not protection: by the time a window
    runs, every module the process will execute is already in ``sys.modules``, so
    disk drift changes what a reader would find on disk and not what the run
    does. Dropping it to a per-window ``stat`` keeps that evidence for every case
    a single-process run on a clean checkout is exposed to — an edit, a
    replacement, a truncation, a removal — and loses exactly one: an edit that
    preserves both size and mtime. A review role reproduced that case with an
    external editor: the previous code refused the run, and the stamp alone
    completes it.

    So the span is closed at the far end instead of sampled 320 times inside it.
    One measurement here covers every byte of every covered file for the whole
    interval between preflight and the survey, and a run whose implementation
    moved under it refuses to certify its own output. Two full measurements a
    run, both cryptographic, one before the first read and one after the last —
    against 321 before, of which 320 sat after the irreversible declaration.

    It is a **completion** check, not a gate on a read: by the time it runs the
    corpus is already seen either way, and what it protects is the record's claim
    to describe the approved implementation.
    """
    from scripts.m15_track_a.containment import implementation_fingerprint

    record = sealed_binding(context)
    try:
        measured = implementation_fingerprint()
    except Exception as exc:  # noqa: BLE001 - re-raised as this module's type
        raise AuthorizationError(
            f"{TOKEN}: the implementation surface could not be re-measured at the end of the "
            f"run, so the run cannot attest to the tree it executed: {exc}"
        ) from exc
    if measured != record["fingerprint"]:
        raise AuthorizationError(
            f"{TOKEN}: the implementation was verified as {record['fingerprint']!r} before the "
            f"read and hashes to {measured!r} after it. The tree changed while the run was in "
            "progress, so this run's output cannot be recorded against the approved "
            "implementation."
        )


__all__ = [
    "VerifiedRunContext",
    "KNOWN_OPERATIONS",
    "assert_implementation_unchanged",
    "grant_covers",
    "sealed_binding",
    "OPERATION_HISTORICAL_READ",
    "OPERATION_M15_DERIVATION",
    "OPERATION_OOS_SLICE_READ",
    "TOKEN",
    "AuthorizationError",
    "AuthorizationMalformedError",
    "ReadGrant",
    "require_authorization",
]
