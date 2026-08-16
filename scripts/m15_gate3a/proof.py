"""The byte-level T-7 proof **contract** — tokens, limbs, and their enforcement.

D-11 rules that the T-7 proof is the conjunction of four limbs — **BI ∧ TC ∧ CV ∧
DB** — and that declaration-only evidence can never be promoted to a byte-level
claim. This module is where that ruling is enforced.

Scope boundary — read this before extending it
----------------------------------------------
Contract §15.4 places the **byte-reading producer and verifier packages at a
later gate**, after the next independent re-check. What lives here is therefore
the *reader-free contract enforcement and the interfaces*, never the byte-reading
implementations:

* the closed token vocabulary and the rule that promotion is forbidden;
* the four-limb conjunction, evaluated over **measurement records a caller
  supplies**;
* the requirement that producer and verifier records both exist, are
  independent, and agree field-by-field;
* coverage set equality (delegated to :mod:`scripts.m15_gate3a.coverage`);
* the derivation binding and the three TOCTOU windows.

**This module opens no file and measures no byte.** It decides over records that
were measured elsewhere. An interface is not a proof: the presence of these
checks is not evidence that any artifact was ever read, and no later session may
read it as such. The committed ``no_overlap_proof.json`` states the live position
exactly — ``SOURCE_LEVEL_PROOF_PROVEN (A1-A4)`` with ``BYTE_LEVEL_PROOF PENDING
(A5, A6)``.

No byte-level claim is reachable from this package
--------------------------------------------------
§11 fixes component **C** = ``scripts/m15_gate3a/**`` as the component that
*never reads*, whose "maximal claim is the declaration-only token", and rules
that a byte-level token is emitted "**only** by a component that opened the
artifact, scanned it, and recorded its measurements". :func:`evaluate_four_limbs`
lives in C and opens nothing, so it used to mint
:data:`BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN` in direct contradiction of the
component split it was implementing.

It no longer does. The four limbs are still evaluated in full and still fail
closed, but the best outcome reachable from this package is
:data:`BYTE_LEVEL_PROOF_PENDING`, and every returned record says why: no
byte-reading component is registered anywhere in the repository, and the
producer/verifier packages that could be are gate 4 (§15.4).
:data:`BYTE_LEVEL_PROOF_REFUTED` stays reachable — it is carried by
:class:`ProofDisagreementError`, which is how a refutation actually leaves this
layer.

**N-3 — correction of a false claim previously carried here.** This paragraph
used to say the claim tokens "remain in the vocabulary because
:func:`assert_byte_level_claim` and the promotion guard are defined in terms of
them, but **no code path here returns one**". That last clause is false and is
retracted: :func:`assert_byte_level_claim` *returns* its argument, and its
argument is a byte-level claim token by the time it returns (see its ``return
token`` line). What is true, and is the whole of the claim, is narrower:

* **no record-producing path** — :func:`evaluate_four_limbs` and
  :func:`open_for_consumption` — mints a claim token. Both emit
  :data:`BYTE_LEVEL_PROOF_PENDING`, and :func:`open_for_consumption` now
  *re-checks* that rather than copying the field it was handed (N-2);
* :func:`assert_byte_level_claim` is a **predicate-shaped guard**: it accepts a
  token a caller already holds, refuses everything weaker by name, and hands
  the same object back. It creates no token and reads no artifact.

The two spellings are additionally **unwritable by this package**: they are
registered in :data:`~scripts.m15_gate3a.guards.UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS`,
so the artifact scrubber refuses any payload carrying one — together with the
``MEASURED_FROM_DERIVED_ARTIFACT_BYTES`` evidence-basis root, which is the
sentence a self-refuting artifact would have to write beside the token. Before
that registration, a ``no_overlap_proof.json`` payload carrying ``"result":
"BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN"`` scanned clean and wrote, while the
strictly *weaker* ``BYTE_ADMISSIBLE`` was refused.

Why promotion cannot happen here
--------------------------------
It is structural, not a comment:

* :class:`DeclarationRecord` and :class:`MeasurementRecord` are distinct frozen
  types. There is no constructor, classmethod, coercion or ``**kwargs`` path
  that turns the first into the second, and the limb evaluator type-checks its
  inputs and raises :class:`ProofPromotionError` on a declaration record.
* :class:`MeasurementRecord` cannot be built without per-quantity
  co-measurement provenance that is identical across digest, size, span and
  scan and is bound to the artifact the record describes. That is a
  **consistency constraint on caller-supplied fields, not evidence that any
  pass occurred**: this layer cannot tell a real byte-stream pass from a
  fabricated label, and an earlier revision of this docstring wrongly said
  declared metadata "cannot fabricate" it. What the constraint forbids is the
  *shape* of a record assembled from different reads, or of twenty records
  citing one pass.
* The declaration-only token is owned by :mod:`scripts.m15_gate3a.no_overlap`,
  which has **no import edge to this module**, so no byte-level token string is
  reachable from the declaration-only code path.

Records state their own limitation
----------------------------------
Every record this module returns carries :data:`LIMB_EVALUATION_EVIDENCE_BASIS`,
``files_opened = 0``, ``bytes_measured = 0`` and the list of quantities it
consumed as declarations, mirroring the declaration-only path in
:mod:`~scripts.m15_gate3a.no_overlap`. Those values are constant by
construction, and deliberately so: R-1 deletes a constant that *asserts a
property* and would read as a measured fact, and each of these asserts the
opposite — that nothing was measured here. A record that omitted them would be
silent about the only thing that matters about it.

Hashing is a byte read (D-4)
----------------------------
The subject of this proof is the **derived M15 artifact bytes**. A record naming
raw source bytes as its subject is refused by :class:`RawSourceRehashForbiddenError`:
"checksum only" is not an exception to T-1 or to the real-data read restriction,
and there is no field anywhere in this module that accepts a raw-source re-hash.
The committed PR-B.1 source digests are consequently *trusted, not re-checked* —
D-4 records that weaker source-substitution detection as the accepted cost, and
it is repeated here so it is not mistaken for an oversight.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from scripts.m15_gate3a.calendar_authority import SLOT_MINUTES
from scripts.m15_gate3a.coverage import CoverageResult
from scripts.m15_gate3a.guards import UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS
from scripts.m15_gate3a.no_overlap import (
    DECLARATION_ONLY_EVIDENCE_BASIS,
    DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL,
    NoOverlapError,
    assert_design_bounds,
)
from scripts.m15_gate3a.numeric_authority import NumericAuthorityError, pin_int
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.timeutil import TimestampError, to_utc

_SHA256_HEX_LENGTH: Final[int] = 64
_HEX_DIGITS: Final[str] = "0123456789abcdefABCDEF"

ROLE_PRODUCER: Final[str] = "producer"
ROLE_VERIFIER: Final[str] = "verifier"

#: The only admissible proof subject (D-4.3).
SUBJECT_DERIVED_M15_ARTIFACT: Final[str] = "DERIVED_M15_ARTIFACT_BYTES"

# ---------------------------------------------------------------------------
# Token vocabulary — closed, each token naming its own evidentiary basis.
# ---------------------------------------------------------------------------

#: Byte-level claim: measured, not declared. Emitted only by
#: :func:`evaluate_four_limbs` once BI ∧ TC ∧ CV ∧ DB all hold.
BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN: Final[str] = "BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN"

#: Byte-level claim: the bytes are bound to a named script, git SHA and config
#: hash, and re-derive byte-identically (the DB limb).
DERIVATION_IDENTITY_BOUND: Final[str] = "DERIVATION_IDENTITY_BOUND"

#: Default status. No byte-level measurement has been made, so no byte-level
#: claim exists. This is the live position of the committed proof artifact.
BYTE_LEVEL_PROOF_PENDING: Final[str] = "BYTE_LEVEL_PROOF_PENDING"

#: Terminal status. A measurement contradicted another, so the proof is refuted
#: and no later evidence rehabilitates it — a refuted proof is not retried.
BYTE_LEVEL_PROOF_REFUTED: Final[str] = "BYTE_LEVEL_PROOF_REFUTED"

DECLARATION_ONLY_TOKENS: Final[frozenset[str]] = frozenset(
    {DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL}
)
BYTE_LEVEL_CLAIM_TOKENS: Final[frozenset[str]] = frozenset(
    {BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN, DERIVATION_IDENTITY_BOUND}
)
BYTE_LEVEL_STATUS_TOKENS: Final[frozenset[str]] = frozenset(
    {BYTE_LEVEL_PROOF_PENDING, BYTE_LEVEL_PROOF_REFUTED}
)
TOKEN_VOCABULARY: Final[frozenset[str]] = (
    DECLARATION_ONLY_TOKENS | BYTE_LEVEL_CLAIM_TOKENS | BYTE_LEVEL_STATUS_TOKENS
)

#: What each token rests on, so an emitted artifact carries its own basis.
TOKEN_EVIDENTIARY_BASIS: Final[Mapping[str, str]] = {
    DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL: DECLARATION_ONLY_EVIDENCE_BASIS,
    BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN: (
        "MEASURED_FROM_DERIVED_ARTIFACT_BYTES__PRODUCER_AND_INDEPENDENT_VERIFIER_AGREE"
    ),
    DERIVATION_IDENTITY_BOUND: (
        "MEASURED_FROM_DERIVED_ARTIFACT_BYTES__BYTE_REPRODUCIBLE_FROM_NAMED_SCRIPT_AND_CONFIG"
    ),
    BYTE_LEVEL_PROOF_PENDING: "NO_BYTE_LEVEL_MEASUREMENT_EXISTS__NO_CLAIM_MADE",
    BYTE_LEVEL_PROOF_REFUTED: "MEASUREMENTS_DISAGREED__TERMINAL",
}

#: Suffix every declaration-only token must carry. A token is read by humans on
#: the face of an emitted artifact, so the spelling itself has to disclaim the
#: byte level: an internal audit mutation that renamed the declaration-only
#: token back to ``PROVEN_NO_DEAD_WINDOW_OVERLAP`` left the whole suite green,
#: because every check was expressed in terms of the constant rather than of
#: what the constant says. This suffix is checked at import, so that rename now
#: fails before any test runs.
DECLARATION_ONLY_TOKEN_SUFFIX: Final[str] = "__NOT_BYTE_LEVEL"

# Explicit raises, not bare `assert`: `python -O` strips asserts, and the whole
# point of the disjointness is that it cannot be optimised away.
if BYTE_LEVEL_CLAIM_TOKENS & DECLARATION_ONLY_TOKENS:  # pragma: no cover - import guard
    raise RuntimeError("a token cannot be both declaration-only and a byte-level claim")
for _token in DECLARATION_ONLY_TOKENS:
    if not _token.endswith(DECLARATION_ONLY_TOKEN_SUFFIX):
        raise RuntimeError(
            f"declaration-only token {_token!r} must end with "
            f"{DECLARATION_ONLY_TOKEN_SUFFIX!r} so its spelling disclaims the byte level"
        )
    if "PROVEN" in _token.removesuffix(DECLARATION_ONLY_TOKEN_SUFFIX):
        raise RuntimeError(
            f"declaration-only token {_token!r} claims to prove something; declaration-only "
            "evidence proves nothing about any file's contents"
        )
del _token
if BYTE_LEVEL_STATUS_TOKENS & (BYTE_LEVEL_CLAIM_TOKENS | DECLARATION_ONLY_TOKENS):
    raise RuntimeError("byte-level status tokens must be disjoint from claim tokens")
# N-3: the writer's prohibition and this vocabulary must not drift apart. If a
# claim token is renamed here and the scrubber's list is not updated, the new
# spelling becomes writable in the same edit — so the two are pinned to each
# other at import, where `python -O` cannot strip the check.
if not BYTE_LEVEL_CLAIM_TOKENS <= UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS:
    raise RuntimeError(
        "every byte-level claim token must be registered unwritable in "
        "scripts.m15_gate3a.guards.UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS; "
        f"{sorted(BYTE_LEVEL_CLAIM_TOKENS - UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS)} is not"
    )
# The reverse direction is deliberately NOT required: the unwritable set also
# carries the evidence-basis root, which is not a token in this vocabulary.
for _basis_token in BYTE_LEVEL_CLAIM_TOKENS:
    if not any(
        root in TOKEN_EVIDENTIARY_BASIS[_basis_token] for root in UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS
    ):
        raise RuntimeError(
            f"the evidentiary basis of {_basis_token!r} names no registered unwritable root; "
            "a payload could assert the measurement in prose beside a permitted token"
        )
del _basis_token
if set(TOKEN_EVIDENTIARY_BASIS) != set(TOKEN_VOCABULARY):  # pragma: no cover - import guard
    raise RuntimeError("every token in the vocabulary must name its evidentiary basis")

#: What this reader-free layer actually rests on, stated in every record it
#: returns rather than left to a docstring (audit B-2, relocated).
LIMB_EVALUATION_EVIDENCE_BASIS: Final[str] = (
    "LIMBS_EVALUATED_OVER_CALLER_SUPPLIED_RECORDS__NO_FILE_OPENED__NO_BYTE_MEASURED"
)

#: Why no byte-level claim accompanies a satisfied four-limb evaluation.
BYTE_LEVEL_CLAIM_WITHHELD_REASON: Final[str] = (
    "NO_REGISTERED_BYTE_READING_COMPONENT_EXISTS__PRODUCER_AND_VERIFIER_PACKAGES_ARE_A_LATER_GATE"
)

#: Exactly how far "independent verifier" is checkable from records alone. §11
#: requires the verifier not to share the producer's *scalar-derivation code*;
#: nothing in a record can evidence that, so the limit is stated instead of an
#: unconditional ``INDEPENDENT_VERIFIER`` being asserted.
VERIFIER_INDEPENDENCE_BASIS: Final[str] = (
    "DISTINCT_DECLARED_BYTE_STREAM_PASSES_OVER_THE_SAME_STAGED_ARTIFACT__"
    "SHARED_SCALAR_DERIVATION_CODE_NOT_EXCLUDED_BY_THIS_LAYER"
)

#: Every quantity this layer consumed as a caller declaration. Naming them is
#: what stops the four-limb evaluation reading as a measurement of them.
DECLARED_NOT_MEASURED_BY_THIS_LAYER: Final[tuple[str, ...]] = (
    "sha256",
    "re_read_sha256",
    "size_bytes",
    "row_count",
    "bars_scanned",
    "measured_ts_min",
    "measured_ts_max",
    "dead_window_bars_by_bucket_start",
    "dead_window_bars_by_contributing_minute",
    "out_of_design_range_bar_count",
    "re_derivation_sha256",
    "certified_slots",
    "verifier_scalar_derivation_independence",
)

#: The four limbs of D-11. All are required; there is no partial proof.
FOUR_LIMBS: Final[tuple[str, ...]] = ("BI", "TC", "CV", "DB")

#: Aggregate assertions committed in ``design_m15_inventory.json``. Each is a
#: measured conjunction over the 20 pairs (D-8 / NR-C, §12.15).
#:
#: N-7: this tuple is consumed **only** by :func:`assert_measured_conjunction`,
#: which itself has no non-test caller — see that function's docstring for why
#: it is disclosed rather than re-routed. The names are the committed spellings
#: and the limb that actually enforces them is :func:`_limb_tc`, inline.
AGGREGATE_ASSERTIONS: Final[tuple[str, ...]] = (
    "dead_window_bars_present_is_zero",
    "all_ts_max_within_design_end",
    "all_ts_min_within_design_start",
    "file_count_is_20",
)


# ---------------------------------------------------------------------------
# Exceptions — one raise site per failure mode, so a test can name which fired.
# ---------------------------------------------------------------------------


class ProofContractError(RuntimeError):
    """Base class: the byte-level proof contract is not satisfied."""


class ProofPromotionError(ProofContractError):
    """Declaration-only evidence was offered where a measurement is required (D-11)."""


class RawSourceRehashForbiddenError(ProofContractError):
    """A record named raw source bytes as its subject; hashing is a byte read (D-4)."""


class ProofCoMeasurementError(ProofContractError):
    """Digest, size, span and scan were not co-measured from one byte stream (§12.12)."""


class ProofLimbAbsentError(ProofContractError):
    """One of the four limbs was not supplied at all; there is no partial proof."""


class ProofLimbUnsatisfiedError(ProofContractError):
    """A supplied limb was evaluated and did not hold."""


class ProofDisagreementError(ProofContractError):
    """Producer and verifier disagree. Fail-closed and terminal (D-11).

    ``token`` is :data:`BYTE_LEVEL_PROOF_REFUTED`: the status is terminal, so a
    later re-measurement does not rehabilitate the proof.
    """

    token = BYTE_LEVEL_PROOF_REFUTED


class ProofNotUsableError(ProofContractError):
    """A consumer tried to use a proof without re-verifying it first (W3)."""


class AggregateAssertionUnsatisfiedError(ProofContractError):
    """An aggregate assertion lacks a measurement, so it is unsatisfied (D-8)."""


class ProofConstructionError(ProofContractError):
    """A proof record was built outside the function that evaluates it."""


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------


def _require_hex_digest(value: Any, *, what: str) -> str:
    if not isinstance(value, str):
        raise ProofContractError(f"{what} must be a 64-hex string, got {type(value).__name__}")
    text = str.__str__(value)
    if len(text) != _SHA256_HEX_LENGTH or any(c not in _HEX_DIGITS for c in text):
        raise ProofContractError(f"{what} is not a well-formed 64-hex SHA-256 digest")
    return text.lower()


def _require_identifier(value: Any, *, what: str) -> str:
    """An artifact identifier, never a path (D-11 "Identity")."""
    if not isinstance(value, str) or not str.__str__(value).strip():
        raise ProofContractError(f"{what} must be a non-empty string")
    text = str.__str__(value)
    if any(ch in text for ch in ("/", "\\", ":")):
        raise ProofContractError(
            f"{what} {text!r} looks like a path; identity is the artifact identifier, "
            "never a path — the data root is a runtime argument and is never committed"
        )
    return text


def _require_content_digest(value: Any, *, what: str) -> str:
    """A digest-or-version identifier, shape-checked like ``inventory_digest``.

    ``inventory_digest`` is required to be 64-hex; the calendar's content digest
    could not be, because D-6 fixes no algorithm for it and admits a version
    string. What can be required is that it is a single token: the audit's
    fabricated ``calendar_digest="NO CALENDAR EVER EXISTED"`` was copied into the
    proof record unchecked, and a sentence is not a version of anything.
    """
    if not isinstance(value, str):
        raise ProofContractError(f"{what} must be a string, got {type(value).__name__}")
    text = str.__str__(value)
    if not text.strip():
        raise ProofContractError(f"{what} is empty, so the record names no calendar version")
    if any(ch.isspace() for ch in text):
        raise ProofContractError(
            f"{what} {text!r} contains whitespace; a content digest or version is a single "
            "token, never prose"
        )
    return text


def _require_count(value: Any, *, what: str, minimum: int) -> int:
    """A bounded count, pinned to plain ``int`` character data first (N-1).

    ``value < minimum`` was asked of the caller's own object; an ``int``
    subclass owns ``__lt__`` and could answer "large enough" while holding any
    value at all. The pinned ``int`` is what is returned, so the record stores
    the number the object really held.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProofContractError(f"{what} must be an int, got {type(value).__name__}")
    try:
        pinned = pin_int(value, what=what)
    except NumericAuthorityError as exc:  # pragma: no cover - guarded above
        raise ProofContractError(str(exc)) from exc
    if pinned < minimum:
        raise ProofContractError(f"{what} must be >= {minimum}, got {pinned}")
    return pinned


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Provenance:
    """Which byte stream, which pass over it, and which artifact it was opened as.

    §12.12 requires the digest and the measured span to be co-measured from one
    pass over one byte stream. Recording provenance *per quantity* and requiring
    the four to be identical is what makes that checkable: a record assembled
    from two reads carries two provenances and is refused.

    ``artifact_id`` binds the pass to the thing it claims to have read. Without
    it a provenance was two caller-chosen scalars floating free of the record,
    so one fabricated ``Provenance("read", 1)`` served all twenty pairs, both
    roles and every quantity, and the only check was that four copies of it were
    equal. Each consumer states which name the pass must cite — the *staged*
    name for a producer or verifier measurement (W1 hashes before the rename),
    the published name for a consumer re-read.

    None of this evidences that a pass happened. It constrains the shape of what
    a caller may assert, and this layer cannot do more than that.
    """

    stream_id: str
    pass_index: int
    artifact_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.stream_id, str) or not self.stream_id.strip():
            raise ProofCoMeasurementError("provenance stream_id must be a non-empty string")
        if isinstance(self.pass_index, bool) or not isinstance(self.pass_index, int):
            raise ProofCoMeasurementError("provenance pass_index must be an int")
        # N-1: pinned before the bound test, and stored pinned so the pass
        # identity a roster de-duplicates on is a plain int.
        try:
            object.__setattr__(self, "pass_index", pin_int(self.pass_index, what="pass_index"))
        except NumericAuthorityError as exc:  # pragma: no cover - guarded above
            raise ProofCoMeasurementError(f"provenance pass_index: {exc}") from exc
        if self.pass_index < 0:
            raise ProofCoMeasurementError("provenance pass_index must not be negative")
        try:
            object.__setattr__(
                self,
                "artifact_id",
                _require_identifier(self.artifact_id, what="provenance artifact_id"),
            )
        except ProofContractError as exc:
            raise ProofCoMeasurementError(
                f"a byte-stream pass must name the artifact it read: {exc}"
            ) from exc


@dataclass(frozen=True, slots=True)
class DeclarationRecord:
    """Caller-declared inventory metadata. Structurally **not** a measurement.

    It exists so the refusal is testable: offering one of these to
    :func:`evaluate_four_limbs` raises :class:`ProofPromotionError`. It carries
    the declaration-only token and no provenance, because nothing here was
    measured from any byte stream.
    """

    pair: str
    artifact_id: str
    declared_sha256: str
    declared_ts_min_utc: str
    declared_ts_max_utc: str
    token: str = DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL

    def __post_init__(self) -> None:
        if self.token not in DECLARATION_ONLY_TOKENS:
            raise ProofPromotionError(
                f"a declaration record may only carry a declaration-only token, got "
                f"{self.token!r}; declared metadata never becomes a byte-level claim"
            )


@dataclass(frozen=True, slots=True)
class MeasurementRecord:
    """One artifact, measured from its own bytes in a single pass.

    Every field is a *measured* quantity. There is no path by which a
    :class:`DeclarationRecord` becomes one of these, and construction fails
    unless the four per-quantity provenances are identical — a record whose
    digest and span came from different reads is refused (§12.12).
    """

    role: str
    pair: str
    artifact_id: str
    subject: str
    sha256: str
    re_read_sha256: str
    staged_artifact_id: str
    size_bytes: int
    row_count: int
    bars_scanned: int
    measured_ts_min: datetime
    measured_ts_max: datetime
    dead_window_bars_by_bucket_start: int
    dead_window_bars_by_contributing_minute: int
    out_of_design_range_bar_count: int
    digest_provenance: Provenance
    size_provenance: Provenance
    span_provenance: Provenance
    scan_provenance: Provenance

    def __post_init__(self) -> None:
        if self.role not in (ROLE_PRODUCER, ROLE_VERIFIER):
            raise ProofContractError(
                f"measurement role must be {ROLE_PRODUCER!r} or {ROLE_VERIFIER!r}, "
                f"got {self.role!r}"
            )
        # D-4: hashing is a byte read; the proof subject is the DERIVED artifact.
        if self.subject != SUBJECT_DERIVED_M15_ARTIFACT:
            raise RawSourceRehashForbiddenError(
                f"measurement subject {self.subject!r} is not the derived M15 artifact; "
                "raw source bytes are never hashed without their own explicit read "
                "authorisation, and 'checksum only' is not an exception"
            )
        try:
            object.__setattr__(self, "pair", canonical_pair(self.pair))
        except PairAuthorityError as exc:
            raise ProofContractError(f"measurement names an unusable pair: {exc}") from exc

        object.__setattr__(
            self, "artifact_id", _require_identifier(self.artifact_id, what="artifact_id")
        )
        object.__setattr__(
            self,
            "staged_artifact_id",
            _require_identifier(self.staged_artifact_id, what="staged_artifact_id"),
        )
        object.__setattr__(self, "sha256", _require_hex_digest(self.sha256, what="sha256"))
        object.__setattr__(
            self, "re_read_sha256", _require_hex_digest(self.re_read_sha256, what="re_read_sha256")
        )
        object.__setattr__(
            self, "size_bytes", _require_count(self.size_bytes, what="size_bytes", minimum=1)
        )
        object.__setattr__(
            self, "row_count", _require_count(self.row_count, what="row_count", minimum=1)
        )
        object.__setattr__(
            self, "bars_scanned", _require_count(self.bars_scanned, what="bars_scanned", minimum=1)
        )
        for name in (
            "dead_window_bars_by_bucket_start",
            "dead_window_bars_by_contributing_minute",
            "out_of_design_range_bar_count",
        ):
            object.__setattr__(
                self, name, _require_count(getattr(self, name), what=name, minimum=0)
            )
        for name in ("measured_ts_min", "measured_ts_max"):
            try:
                object.__setattr__(self, name, to_utc(getattr(self, name)))
            except TimestampError as exc:
                raise ProofContractError(f"{name} is not an exact UTC instant: {exc}") from exc

        # W1 (derivation -> digest): hash, re-open, re-hash, require equality,
        # then atomically rename from the staging name to the final identifier.
        if self.sha256 != self.re_read_sha256:
            raise ProofContractError(
                f"{self.pair}: the independent re-read digest {self.re_read_sha256} does not "
                f"reproduce the first-pass digest {self.sha256}; the artifact changed between "
                "the two hashes"
            )
        if self.staged_artifact_id == self.artifact_id:
            raise ProofContractError(
                f"{self.pair}: staged_artifact_id equals artifact_id, so the bytes were hashed "
                "under the name they are published as; W1 requires hashing a staged name and "
                "then renaming atomically"
            )
        # The row count is a claim about the same stream the scan walked.
        if self.bars_scanned != self.row_count:
            raise ProofContractError(
                f"{self.pair}: bars_scanned {self.bars_scanned} disagrees with row_count "
                f"{self.row_count}; the declared row count must be what the full scan counted"
            )
        self._assert_internally_consistent()
        # W2 / §12.12: one pass over one byte stream, record built atomically.
        provenances = {
            "digest": self.digest_provenance,
            "size": self.size_provenance,
            "span": self.span_provenance,
            "scan": self.scan_provenance,
        }
        for name, prov in provenances.items():
            if not isinstance(prov, Provenance):
                raise ProofCoMeasurementError(
                    f"{self.pair}: {name}_provenance must be a Provenance, "
                    f"got {type(prov).__name__}"
                )
        distinct = {(p.stream_id, p.pass_index) for p in provenances.values()}
        if len(distinct) != 1:
            raise ProofCoMeasurementError(
                f"{self.pair}: digest, size, span and scan cite {len(distinct)} different "
                "byte-stream passes; they must be co-measured from a single pass over one "
                "byte stream and the record built atomically at the end of it"
            )
        for name, prov in provenances.items():
            if prov.artifact_id != self.staged_artifact_id:
                raise ProofCoMeasurementError(
                    f"{self.pair}: the {name} pass says it read {prov.artifact_id!r} while the "
                    f"record describes {self.staged_artifact_id!r}; a provenance that names no "
                    "particular artifact can be reused across every quantity and every pair"
                )

    def _assert_internally_consistent(self) -> None:
        """Arithmetic floors on the scan (DI-9). No threshold is introduced here.

        A record declaring ``bars_scanned=1`` beside a 303-day measured span was
        accepted, because nothing related the bar count to the span it claims to
        cover. Every relation below is necessary rather than chosen: the M15
        grid is frozen at :data:`~scripts.m15_gate3a.calendar_authority.SLOT_MINUTES`
        by the committed derivation manifest, bars are distinct bucket starts on
        it, and one bar has one timestamp.

        ``size_bytes`` deliberately gets **no** floor: no relation between a byte
        count and a row count holds for every serialisation, so any bytes-per-row
        rule would be an invented threshold. It is constrained instead by
        producer/verifier agreement and by the W3 consumer re-check, and it is
        listed in :data:`DECLARED_NOT_MEASURED_BY_THIS_LAYER`.
        """
        lo, hi = self.measured_ts_min, self.measured_ts_max
        if hi < lo:
            raise ProofContractError(
                f"{self.pair}: measured_ts_max {hi.isoformat()} precedes measured_ts_min "
                f"{lo.isoformat()}; a reversed span is not a measurement of anything"
            )
        for name in ("measured_ts_min", "measured_ts_max"):
            value: datetime = getattr(self, name)
            if value.minute % SLOT_MINUTES or value.second or value.microsecond:
                raise ProofContractError(
                    f"{self.pair}: {name} {value.isoformat()} is not an M15 bucket start on the "
                    f"frozen {SLOT_MINUTES}-minute UTC grid, so it is not a bar timestamp"
                )
        if self.bars_scanned == 1 and hi != lo:
            raise ProofContractError(
                f"{self.pair}: the full scan counted one bar, but the measured span runs from "
                f"{lo.isoformat()} to {hi.isoformat()}; a single bar cannot have two distinct "
                "endpoints"
            )
        capacity = int((hi - lo).total_seconds()) // (SLOT_MINUTES * 60) + 1
        if self.bars_scanned > capacity:
            raise ProofContractError(
                f"{self.pair}: the full scan counted {self.bars_scanned} bars, but the measured "
                f"span {lo.isoformat()}..{hi.isoformat()} holds at most {capacity} distinct "
                f"{SLOT_MINUTES}-minute bucket start(s)"
            )


@dataclass(frozen=True, slots=True)
class DerivationBinding:
    """The DB limb's evidence for one artifact.

    There is deliberately no field for a raw-source re-hash: the source identity
    is the *declared* committed PR-B.1 identity, trusted and not re-checked
    (D-4). ``re_derivation_sha256`` is the digest of re-running the named script
    at the named git SHA and config hash — a measurement of the **derived**
    bytes, which is the only subject this proof admits.
    """

    pair: str
    script_name: str
    git_sha: str
    config_hash: str
    source_identity: str
    re_derivation_sha256: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "pair", canonical_pair(self.pair))
        except PairAuthorityError as exc:
            raise ProofContractError(f"derivation binding names an unusable pair: {exc}") from exc
        for name in ("script_name", "git_sha", "config_hash", "source_identity"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ProofContractError(
                    f"derivation binding field {name!r} must be a non-empty string; the bytes "
                    "must be bound to a named script, git SHA, config hash and source identity"
                )
        object.__setattr__(
            self,
            "re_derivation_sha256",
            _require_hex_digest(self.re_derivation_sha256, what="re_derivation_sha256"),
        )


@dataclass(frozen=True, slots=True)
class ConsumerRecheck:
    """A consumer's own re-measurement, taken immediately before use (W3)."""

    pair: str
    artifact_id: str
    sha256: str
    size_bytes: int
    provenance: Provenance

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "pair", canonical_pair(self.pair))
        except PairAuthorityError as exc:
            raise ProofContractError(f"consumer recheck names an unusable pair: {exc}") from exc
        object.__setattr__(
            self, "artifact_id", _require_identifier(self.artifact_id, what="artifact_id")
        )
        object.__setattr__(self, "sha256", _require_hex_digest(self.sha256, what="sha256"))
        object.__setattr__(
            self, "size_bytes", _require_count(self.size_bytes, what="size_bytes", minimum=1)
        )
        if not isinstance(self.provenance, Provenance):
            raise ProofContractError("consumer recheck must cite the read it performed")
        if self.provenance.artifact_id != self.artifact_id:
            raise ProofContractError(
                f"{self.pair}: the consumer's read says it opened "
                f"{self.provenance.artifact_id!r} while the recheck describes "
                f"{self.artifact_id!r}; a re-verification is of the artifact about to be read"
            )


@dataclass(frozen=True, slots=True)
class _ArtifactIdentity:
    """What the proof was made about for one pair, and which passes made it.

    Private on purpose. W3 rules re-verification a *precondition of use*, and
    while the proof published its identity map any consumer could read the
    digest, size and identifier straight off the result and never call
    :func:`open_for_consumption` at all. The identity is now reachable only
    through that call, which is what makes the precondition genuine.
    """

    artifact_id: str
    sha256: str
    size_bytes: int
    measured_stream_ids: frozenset[str]


class _ProofConstructionToken:
    """One-shot capability to construct one proof record.

    ``ProofResult`` claimed "Constructed only by :func:`evaluate_four_limbs`" and
    enforced nothing: the adversarial workstream hand-built one carrying the
    byte-level claim token, an empty aggregate map and
    ``calendar_digest='NO-CALENDAR-WAS-EVER-VALIDATED'``, and drove it through
    consumption with **no limb ever evaluated**. Same remedy as
    :mod:`~scripts.m15_gate3a.coverage`.

    **N-5 — the copy protocols are refused.** This used to claim the token
    "removes the public-API route". ``copy.copy``, ``copy.deepcopy`` and
    ``pickle`` are public API and rebuild a frozen ``slots`` dataclass without
    running ``__post_init__``, so each one minted a record having spent no
    token. All three now raise. The acknowledged limit is unchanged and is
    stated rather than claimed away: a caller reaching into this module's
    private names can still mint a token, and ``object.__setattr__`` still
    rewrites a real record — which is exactly why
    :func:`open_for_consumption` re-checks the fields it repeats (N-2) instead
    of inheriting them on trust.
    """

    __slots__ = ("purpose", "spent")

    def __init__(self, purpose: str) -> None:
        self.purpose = purpose
        self.spent = False


def _refuse_reconstruction(self: Any, *_args: Any) -> None:
    """Refuse ``copy.copy`` / ``copy.deepcopy`` / ``pickle`` (N-5).

    Each protocol reconstructs the instance without ``__post_init__``, where the
    one-shot construction token is spent, so each was a free re-mint of a record
    whose whole meaning is that a particular evaluation ran once.
    """
    raise ProofConstructionError(
        f"a {type(self).__name__} may not be copied, deep-copied or pickled; those protocols "
        "rebuild the record without spending a construction token, so the copy would assert an "
        "evaluation that never ran"
    )


_PROOF_RESULT_PURPOSE: Final[str] = "ProofResult"
_APPROVAL_PURPOSE: Final[str] = "ConsumptionApproval"


def _spend(token: Any, *, purpose: str, what: str, minted_by: str) -> None:
    if not isinstance(token, _ProofConstructionToken) or token.purpose != purpose or token.spent:
        raise ProofConstructionError(
            f"a {what} is minted only by {minted_by}(); a hand-built instance asserts an "
            "evaluation that never ran"
        )
    token.spent = True


@dataclass(frozen=True, slots=True)
class ProofResult:
    """The four-limb evaluation over caller-supplied records — not a byte-level claim.

    Minted only by :func:`evaluate_four_limbs`, enforced by
    :class:`_ProofConstructionToken`. It carries **no claim token**: §11 reserves
    those for a component that opened the artifact, and this package opens
    nothing. What it carries instead is what actually happened — which limbs were
    evaluated, over what, and what was never measured.

    ``limbs_evaluated``, ``pairs_measured``, ``derivation_token`` and
    ``aggregate_assertions`` are gone. Each could only ever hold one value once
    the evaluator raises on everything else, which is the R-1 defect the audit
    found in ``aggregate_assertions`` (a map of literal ``True`` assigned after
    the raises that made it unfalsifiable). The disclaimer fields that remain
    constant are the deliberate exception recorded in the module docstring.
    """

    byte_level_status: str
    claim_withheld_because: str
    evidence_basis: str
    verifier_independence_basis: str
    declared_not_measured: tuple[str, ...]
    files_opened: int
    bytes_measured: int
    inventory_digest: str
    calendar_digest: str
    _identity: Mapping[str, _ArtifactIdentity] = field(repr=False, compare=False)
    _construction_token: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _spend(
            self._construction_token,
            purpose=_PROOF_RESULT_PURPOSE,
            what="ProofResult",
            minted_by="evaluate_four_limbs",
        )
        object.__setattr__(self, "_construction_token", None)

    __copy__ = _refuse_reconstruction
    __deepcopy__ = _refuse_reconstruction
    __reduce__ = _refuse_reconstruction


@dataclass(frozen=True, slots=True)
class ConsumptionApproval:
    """The W3 re-verification result, and the only route to the proof's identity.

    Returned when every artifact the consumer is about to read was re-measured
    and matched. It is **not** an authorisation to read anything: it repeats the
    ``byte_level_status`` of the proof it came from, which is
    :data:`BYTE_LEVEL_PROOF_PENDING` for as long as no component in this
    repository has ever opened one of these artifacts.
    """

    byte_level_status: str
    claim_withheld_because: str
    evidence_basis: str
    declared_not_measured: tuple[str, ...]
    files_opened: int
    bytes_measured: int
    inventory_digest: str
    identity: Mapping[str, tuple[str, str, int]]
    _construction_token: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _spend(
            self._construction_token,
            purpose=_APPROVAL_PURPOSE,
            what="ConsumptionApproval",
            minted_by="open_for_consumption",
        )
        object.__setattr__(self, "_construction_token", None)

    __copy__ = _refuse_reconstruction
    __deepcopy__ = _refuse_reconstruction
    __reduce__ = _refuse_reconstruction


# ---------------------------------------------------------------------------
# Token discipline
# ---------------------------------------------------------------------------


def is_declaration_only(token: Any) -> bool:
    """True iff ``token`` rests on caller-declared metadata."""
    return token in DECLARATION_ONLY_TOKENS


def _pin_token(value: Any, *, what: str) -> str:
    """The plain character data of a token field, or refuse it (N-2).

    ``str.__str__`` is the same pin :mod:`scripts.m15_gate3a.artifacts` and
    :mod:`scripts.m15_gate3a.path_authority` use: a ``str`` subclass can show one
    spelling to a comparison and another to whatever writes the artifact.
    """
    if not isinstance(value, str):
        raise ProofNotUsableError(
            f"{what} is a {type(value).__name__}, not a token string; the proof record was "
            "rewritten after construction"
        )
    return str.__str__(value)


def _assert_disclosure_untampered(result: ProofResult) -> None:
    """Re-check the token fields :func:`open_for_consumption` is about to repeat.

    **N-2.** ``open_for_consumption`` copied ``byte_level_status``,
    ``claim_withheld_because`` and ``evidence_basis`` verbatim into a *freshly
    minted* :class:`ConsumptionApproval`. A frozen dataclass is not sealed —
    ``object.__setattr__`` is this package's own declared threat model, stated in
    ``coverage.assert_full_coverage`` and on :class:`_ProofConstructionToken` —
    so a tampered ``ProofResult`` yielded a brand-new approval asserting
    ``BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN`` and
    ``MEASURED_FROM_DERIVED_ARTIFACT_BYTES…`` beside its own ``files_opened=0``.
    That is the self-refuting artifact B-2/B-3/§12.13 exist to prevent, minted by
    this layer rather than smuggled through it.

    The remedy is the one :func:`_limb_cv` already applies to ``per_pair``:
    re-check the invariant rather than inherit it. These are **not** vacuous
    R-1 checks — every one of them is reachable, and each is exercised by a test
    that tampers exactly one field. Each divergence has its own raise site so a
    test can name which fired without a regex alternation.
    """
    status = _pin_token(result.byte_level_status, what="byte_level_status")
    if status in BYTE_LEVEL_CLAIM_TOKENS:
        raise ProofPromotionError(
            f"the proof record carries byte-level claim token {status!r}; evaluate_four_limbs "
            "mints no claim token, so this record was rewritten after construction and a "
            "consumption approval minted from it would assert a measurement no component made"
        )
    if status != BYTE_LEVEL_PROOF_PENDING:
        raise ProofNotUsableError(
            f"the proof record declares byte_level_status {status!r}; the only status this "
            f"reader-free layer can reach is {BYTE_LEVEL_PROOF_PENDING!r}"
        )
    if _pin_token(result.evidence_basis, what="evidence_basis") != LIMB_EVALUATION_EVIDENCE_BASIS:
        raise ProofNotUsableError(
            f"the proof record declares evidence_basis {result.evidence_basis!r}; this layer "
            f"evaluates limbs over caller-supplied records and its basis is always "
            f"{LIMB_EVALUATION_EVIDENCE_BASIS!r}"
        )
    withheld = _pin_token(result.claim_withheld_because, what="claim_withheld_because")
    if withheld != BYTE_LEVEL_CLAIM_WITHHELD_REASON:
        raise ProofNotUsableError(
            f"the proof record declares claim_withheld_because {withheld!r}; the reason a "
            "byte-level claim is withheld is not a caller-settable field"
        )
    if tuple(result.declared_not_measured) != DECLARED_NOT_MEASURED_BY_THIS_LAYER:
        raise ProofNotUsableError(
            "the proof record's declared_not_measured list is not the one this layer emits; "
            "shortening it would hide which quantities were consumed as declarations"
        )
    if (result.files_opened, result.bytes_measured) != (0, 0):
        raise ProofNotUsableError(
            f"the proof record declares files_opened={result.files_opened!r} and "
            f"bytes_measured={result.bytes_measured!r}; this layer opens no file and measures "
            "no byte, so a non-zero count means the record was rewritten"
        )


def assert_byte_level_claim(token: Any) -> str:
    """Return ``token`` if it is a byte-level claim; refuse anything weaker.

    This is the promotion guard in its most direct form: a declaration-only
    token offered where a byte-level claim is required is refused by name, and
    a pending or refuted status is not a claim either.

    **N-3 — what "returns a claim token" does and does not mean here.** This
    function hands back the object it was given, unchanged, once it has proved
    that object is already a byte-level claim token. It mints nothing, reads no
    artifact, and cannot turn weaker evidence into a claim — that is the whole
    of its purpose. The module docstring's earlier assertion that "no code path
    here returns one" was nonetheless wrong on its face and is corrected there.
    Both claim spellings are registered unwritable
    (:data:`~scripts.m15_gate3a.guards.UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS`), so a
    token that reaches a caller through this function still cannot reach an
    artifact.
    """
    if token in DECLARATION_ONLY_TOKENS:
        raise ProofPromotionError(
            f"{token!r} rests on caller-declared metadata "
            f"({TOKEN_EVIDENTIARY_BASIS[token]}) and can never be promoted to a "
            "byte-level claim"
        )
    if token not in BYTE_LEVEL_CLAIM_TOKENS:
        raise ProofContractError(
            f"{token!r} is not a byte-level claim token in the closed vocabulary"
        )
    return token


# `current_byte_level_proof_status()` used to live here and returned
# `BYTE_LEVEL_PROOF_PENDING` unconditionally. R-1 deletes a field that can only
# ever hold one value, and a nullary function returning a constant is the same
# thing behind parentheses — created by the very change that deleted eleven such
# attestations. It is gone rather than re-expressed: the pending status now
# reaches a caller only on a record that also states what was and was not
# measured to arrive at it, where it cannot be read as a standalone verdict.


def refuse_raw_source_rehash(subject: Any) -> None:
    """Refuse any request to hash raw source bytes (D-4.1, D-4.7, §12.11)."""
    if subject != SUBJECT_DERIVED_M15_ARTIFACT:
        raise RawSourceRehashForbiddenError(
            f"refusing to hash {subject!r}: hashing is a byte read, unapproved raw source "
            "bytes are not read for checksum purposes, and the dead-window content of a raw "
            "source file may not be circumvented under the guise of hashing"
        )


# ---------------------------------------------------------------------------
# Aggregate assertions (D-8 / NR-C, §12.15)
# ---------------------------------------------------------------------------


def assert_measured_conjunction(name: str, per_pair: Any) -> bool:
    """A committed aggregate assertion is a measured conjunction over 20 pairs.

    A missing measurement makes the assertion **unsatisfied — never vacuously
    true** (D-8). A declared count alone never establishes it.

    **N-7 — this guard has no non-test caller, and that is stated rather than
    implied.** :func:`_limb_tc` used to build a ``{assertion: {pair: True}}`` map
    and hand it here; every value was a literal ``True`` written after the raises
    above it, so the conjunction could not fail (R-1). The substance moved
    *inline* into that limb, which now raises directly on each of the four
    committed assertions — a genuine improvement, and it left this function and
    :data:`AGGREGATE_ASSERTIONS` unrouted.

    That is the same condition RF-15 forced :mod:`scripts.m15_gate3a.guards` to
    disclose about three of its four public guards, so it is disclosed the same
    way instead of being re-routed: **re-introducing a call from ``_limb_tc``
    would mean re-deriving the per-pair map from measurements the limb has
    already refused on, which is how the R-1 defect was built in the first
    place.** What this function constrains is exactly what is handed to it, and
    nothing more. It is retained because it is the executable statement of D-8's
    disposition — *a missing measurement is unsatisfied, never vacuously true* —
    and because the byte-reading producer/verifier packages at gate 4 (§15.4) are
    where a real per-pair measurement map will exist to route through it. It is
    **not** evidence that any aggregate assertion in
    ``design_m15_inventory.json`` has been checked by this package, and must not
    be cited as such.
    """
    if name not in AGGREGATE_ASSERTIONS:
        raise AggregateAssertionUnsatisfiedError(
            f"{name!r} is not one of the committed aggregate assertions {AGGREGATE_ASSERTIONS}"
        )
    if not isinstance(per_pair, Mapping):
        raise AggregateAssertionUnsatisfiedError(
            f"aggregate assertion {name!r} needs a per-pair measurement mapping, got "
            f"{type(per_pair).__name__}; a declared count is not a measurement"
        )
    snapshot = dict(per_pair)
    for pair in PAIRS_20:
        if pair not in snapshot or snapshot[pair] is None:
            raise AggregateAssertionUnsatisfiedError(
                f"aggregate assertion {name!r} has no measurement for {pair}; a missing "
                "measurement is unsatisfied, never vacuously true"
            )
        value = snapshot[pair]
        if not isinstance(value, bool):
            raise AggregateAssertionUnsatisfiedError(
                f"aggregate assertion {name!r} for {pair} is {type(value).__name__}, not a "
                "measured boolean"
            )
        if not value:
            raise AggregateAssertionUnsatisfiedError(
                f"aggregate assertion {name!r} is false for {pair}; the conjunction over "
                "PAIRS_20 does not hold"
            )
    return True


# ---------------------------------------------------------------------------
# Roster / agreement
# ---------------------------------------------------------------------------


def _measurement_roster(records: Any, *, role: str) -> dict[str, MeasurementRecord]:
    if records is None:
        raise ProofLimbAbsentError(
            f"no {role} measurement records supplied; the BI limb cannot be evaluated"
        )
    if isinstance(records, (str, bytes, bytearray)) or not isinstance(records, Sequence):
        raise ProofContractError(
            f"{role} records must be a concrete sequence, got {type(records).__name__}"
        )
    items = tuple(records)
    if not items:
        raise ProofLimbAbsentError(
            f"the {role} measurement record set is empty; the BI limb cannot be evaluated"
        )
    by_pair: dict[str, MeasurementRecord] = {}
    for index, item in enumerate(items):
        if isinstance(item, DeclarationRecord):
            raise ProofPromotionError(
                f"{role} record {index} is a DeclarationRecord carrying {item.token!r}; "
                "declaration-only evidence is never promoted to a byte-level measurement"
            )
        if not isinstance(item, MeasurementRecord):
            raise ProofPromotionError(
                f"{role} record {index} is a {type(item).__name__}, not a MeasurementRecord; "
                "only evidence measured from the artifact's own bytes is admissible"
            )
        if item.role != role:
            raise ProofContractError(
                f"record {index} declares role {item.role!r} in the {role} record set"
            )
        if item.pair in by_pair:
            raise ProofContractError(
                f"{role}: {item.pair} is measured twice; after canonicalisation each pair is "
                "measured exactly once"
            )
        by_pair[item.pair] = item

    # One pass over one byte stream measured one artifact, so two records citing
    # the same pass are describing the same file twice. Without this a single
    # fabricated `Provenance` served all twenty pairs (DI-5).
    passes: dict[tuple[str, int], str] = {}
    staged: dict[str, str] = {}
    for pair, item in by_pair.items():
        key = (item.digest_provenance.stream_id, item.digest_provenance.pass_index)
        if key in passes:
            raise ProofCoMeasurementError(
                f"{role}: {pair} and {passes[key]} both cite byte-stream pass {key[0]!r} "
                f"#{key[1]}; one pass over one byte stream measures one artifact"
            )
        passes[key] = pair
        if item.staged_artifact_id in staged:
            raise ProofContractError(
                f"{role}: {pair} and {staged[item.staged_artifact_id]} were both hashed under "
                f"the staging name {item.staged_artifact_id!r}; twenty files means twenty "
                "staging identities"
            )
        staged[item.staged_artifact_id] = pair
    return by_pair


_AGREEING_FIELDS: Final[tuple[str, ...]] = (
    "artifact_id",
    "staged_artifact_id",
    "size_bytes",
    "row_count",
    "bars_scanned",
    "measured_ts_min",
    "measured_ts_max",
    "dead_window_bars_by_bucket_start",
    "dead_window_bars_by_contributing_minute",
    "out_of_design_range_bar_count",
)


def assert_records_agree(producer: Any, verifier: Any) -> None:
    """Producer and an independent verifier must agree field-by-field (D-11).

    Any disagreement is fail-closed and terminal. A **digest match with a scalar
    mismatch is the more alarming case**: identical bytes yielding different
    measured quantities means a derivation is wrong, not that a file moved, so it
    is reported separately rather than folded into a generic mismatch.

    **How far "independent" is checkable here** (:data:`VERIFIER_INDEPENDENCE_BASIS`).
    The old test was ``producer.digest_provenance != verifier.digest_provenance``,
    a tuple comparison that a verifier citing a *different file at the same pass
    index* satisfied. It now takes two distinct byte-stream passes over the
    **same** named artifact. What no record can evidence is §11's real
    requirement — that the verifier does not share the producer's
    scalar-derivation code. That is a property of the P and V packages, which
    are a later gate; this layer states the limit rather than asserting
    ``INDEPENDENT_VERIFIER``.
    """
    if producer is None:
        raise ProofLimbAbsentError("the producer measurement record is absent")
    if verifier is None:
        raise ProofLimbAbsentError(
            "the independent verifier measurement record is absent; a producer measurement "
            "alone is never attestation"
        )
    if not isinstance(producer, MeasurementRecord) or not isinstance(verifier, MeasurementRecord):
        raise ProofPromotionError(
            "agreement is only defined between two MeasurementRecords measured from bytes"
        )
    if producer.role != ROLE_PRODUCER or verifier.role != ROLE_VERIFIER:
        raise ProofContractError(
            f"agreement needs one {ROLE_PRODUCER} and one {ROLE_VERIFIER} record, got "
            f"{producer.role!r} and {verifier.role!r}"
        )
    if producer.pair != verifier.pair:
        raise ProofDisagreementError(
            f"producer measured {producer.pair} while the verifier measured {verifier.pair}"
        )
    if producer.digest_provenance.stream_id == verifier.digest_provenance.stream_id:
        raise ProofContractError(
            f"{producer.pair}: the verifier cites the producer's own byte-stream pass; a "
            "verifier re-measures independently rather than replaying the producer's read"
        )
    if producer.digest_provenance.artifact_id != verifier.digest_provenance.artifact_id:
        raise ProofDisagreementError(
            f"{producer.pair}: the verifier's pass names artifact "
            f"{verifier.digest_provenance.artifact_id!r} while the producer's names "
            f"{producer.digest_provenance.artifact_id!r}; an independent verifier re-reads the "
            "same artifact, not a different one"
        )

    scalar_mismatches = [
        name for name in _AGREEING_FIELDS if getattr(producer, name) != getattr(verifier, name)
    ]
    if producer.sha256 == verifier.sha256:
        if scalar_mismatches:
            raise ProofDisagreementError(
                f"{producer.pair}: producer and verifier agree on the digest but disagree on "
                f"{scalar_mismatches}; identical bytes yielding different measurements means a "
                "derivation is wrong — terminal"
            )
        return
    raise ProofDisagreementError(
        f"{producer.pair}: producer digest {producer.sha256} != verifier digest "
        f"{verifier.sha256}; the two reads did not see the same artifact — terminal"
    )


# ---------------------------------------------------------------------------
# The four limbs
# ---------------------------------------------------------------------------


def _limb_bi(records: Mapping[str, MeasurementRecord]) -> None:
    """BI — byte identity: 20 distinct whole files, digest reproduced on re-read."""
    missing = [p for p in PAIRS_20 if p not in records]
    if missing:
        raise ProofLimbUnsatisfiedError(
            f"BI limb: no byte measurement for {missing}; each of the 20 derived artifacts "
            "must be measured from its own bytes"
        )
    by_digest: dict[str, str] = {}
    by_identifier: dict[str, str] = {}
    for pair in PAIRS_20:
        record = records[pair]
        if record.sha256 in by_digest:
            raise ProofLimbUnsatisfiedError(
                f"BI limb: {pair} and {by_digest[record.sha256]} share digest {record.sha256}; "
                "no two roster entries may resolve to the same object"
            )
        by_digest[record.sha256] = pair
        if record.artifact_id in by_identifier:
            raise ProofLimbUnsatisfiedError(
                f"BI limb: {pair} and {by_identifier[record.artifact_id]} share artifact "
                f"identifier {record.artifact_id!r}; twenty files means twenty identities"
            )
        by_identifier[record.artifact_id] = pair


def _limb_tc(records: Mapping[str, MeasurementRecord]) -> None:
    """TC — time containment, measured by full scan, never inferred from endpoints.

    This used to build a ``{assertion: {pair: True}}`` map and hand it to
    :func:`assert_measured_conjunction`. Every value was a literal ``True``
    written *after* the raises above it, so the conjunction could not fail and
    the ``aggregate_assertions`` field it fed could only ever hold one value —
    R-1's negative-control violation, committed by the change that deleted eleven
    others. The limb now raises or returns nothing; there is no derived
    attestation to report.
    """
    for pair in PAIRS_20:
        record = records[pair]
        try:
            assert_design_bounds(record.measured_ts_min, record.measured_ts_max)
        except NoOverlapError as exc:
            raise ProofLimbUnsatisfiedError(
                f"TC limb: {pair} measured span is not inside the frozen design epoch: {exc}"
            ) from exc
        if record.out_of_design_range_bar_count:
            raise ProofLimbUnsatisfiedError(
                f"TC limb: {pair} full scan counted {record.out_of_design_range_bar_count} bar(s) "
                "outside the design epoch; endpoints cannot exclude an interior bar and the "
                "interior is where a bucketing fault hides"
            )
        # D-8: measured under BOTH definitions. They coincide under a correct
        # implementation and diverge exactly when it is wrong.
        if (
            record.dead_window_bars_by_bucket_start
            != record.dead_window_bars_by_contributing_minute
        ):
            raise ProofDisagreementError(
                f"TC limb: {pair} counts {record.dead_window_bars_by_bucket_start} dead-window "
                f"bar(s) by bucket start and {record.dead_window_bars_by_contributing_minute} by "
                "contributing source minute; the two definitions diverging means the bucketing "
                "is wrong — terminal"
            )
        if record.dead_window_bars_by_bucket_start:
            raise ProofLimbUnsatisfiedError(
                f"TC limb: {pair} full scan counted "
                f"{record.dead_window_bars_by_bucket_start} dead-window bar(s); the count must "
                "be zero by full scan"
            )


def _limb_cv(coverage_result: Any, records: Mapping[str, MeasurementRecord]) -> CoverageResult:
    """CV — coverage: set equality per pair, bound to the artifact BI and TC measured.

    The type check is the D-5.9 guard: a ``{"n_pairs": 20}``-shaped object is
    exactly the non-evidence that ruling names, and it is refused by type rather
    than by reading a flag off it.

    CV and BI/TC used to constrain **disjoint** evidence: coverage decided over a
    slot set while BI and TC decided over a byte scan, and nothing said the two
    described the same artifact — a pair could certify one M15 slot beside a
    ``bars_scanned=50_000`` measurement. Binding the certified slot count to the
    scanned bar count is what makes the four limbs one proof rather than four
    unrelated checks, and it is arithmetic rather than a threshold: each
    certified slot is one bar of the scanned artifact, with no duplicate
    (:class:`~scripts.m15_gate3a.coverage.CoverageSetMismatchError`) and no
    uncertifiable bar
    (:class:`~scripts.m15_gate3a.coverage.BarNotCertifiableError`).
    """
    if coverage_result is None:
        raise ProofLimbAbsentError(
            "the CV limb is absent; coverage set equality has not been evaluated and a proof "
            "without it is not a proof"
        )
    if not isinstance(coverage_result, CoverageResult):
        raise ProofLimbUnsatisfiedError(
            f"CV limb: expected a measured CoverageResult, got {type(coverage_result).__name__}; "
            "a pair count is not coverage evidence"
        )
    # A CoverageResult is minted only by `assert_full_coverage`, but a frozen
    # dataclass is not sealed — `object.__setattr__` rewrites `per_pair` on a
    # real one. The roster is re-checked here rather than inherited on trust.
    covered = {entry.pair: entry for entry in coverage_result.per_pair}
    if sorted(covered) != sorted(PAIRS_20):
        raise ProofLimbUnsatisfiedError(
            f"CV limb: coverage was certified for {sorted(covered)}, which is not the canonical "
            "PAIRS_20 roster; the coverage token is the conjunction over all twenty"
        )
    for pair in PAIRS_20:
        entry = covered[pair]
        scanned = records[pair].bars_scanned
        if entry.certified_slot_count != scanned:
            raise ProofLimbUnsatisfiedError(
                f"CV limb: {pair} certifies {entry.certified_slot_count} M15 slot(s) while the "
                f"full byte scan counted {scanned} bar(s); the coverage evidence and the scanned "
                "artifact are not describing the same file"
            )
    return coverage_result


def _limb_db(bindings: Any, records: Mapping[str, MeasurementRecord]) -> None:
    """DB — derivation binding: named script, git SHA, config hash, byte-reproducible."""
    if bindings is None:
        raise ProofLimbAbsentError(
            "the DB limb is absent; the bytes are not bound to any named derivation"
        )
    if isinstance(bindings, (str, bytes, bytearray)) or not isinstance(bindings, Sequence):
        raise ProofContractError(
            f"derivation bindings must be a concrete sequence, got {type(bindings).__name__}"
        )
    items = tuple(bindings)
    if not items:
        raise ProofLimbAbsentError(
            "the derivation binding set is empty; the DB limb cannot be evaluated"
        )
    by_pair: dict[str, DerivationBinding] = {}
    for index, item in enumerate(items):
        if not isinstance(item, DerivationBinding):
            raise ProofLimbUnsatisfiedError(
                f"DB limb: binding {index} is a {type(item).__name__}, not a DerivationBinding"
            )
        if item.pair in by_pair:
            raise ProofLimbUnsatisfiedError(f"DB limb: {item.pair} is bound twice")
        by_pair[item.pair] = item
    missing = [p for p in PAIRS_20 if p not in by_pair]
    if missing:
        raise ProofLimbUnsatisfiedError(
            f"DB limb: no derivation binding for {missing}; every artifact must name the script, "
            "git SHA and config hash that produced it"
        )
    for pair in PAIRS_20:
        binding = by_pair[pair]
        if binding.re_derivation_sha256 != records[pair].sha256:
            raise ProofLimbUnsatisfiedError(
                f"DB limb: {pair} re-derives to {binding.re_derivation_sha256} but the measured "
                f"artifact is {records[pair].sha256}; the bytes are not byte-reproducible from "
                "the named script and config"
            )


def evaluate_four_limbs(
    *,
    producer_records: Any,
    verifier_records: Any,
    coverage_result: Any,
    derivation_bindings: Any,
    inventory_digest: Any,
) -> ProofResult:
    """Evaluate **BI ∧ TC ∧ CV ∧ DB** over caller-supplied records, or refuse.

    Every argument is keyword-only with **no default**, so a limb cannot be
    omitted by accident: leaving one out is a ``TypeError`` and passing ``None``
    raises :class:`ProofLimbAbsentError` naming the limb. There is no partial
    proof and no evaluation mode that skips a limb.

    ``inventory_digest`` closes W2: the record set is built atomically at the end
    of each single pass, and the inventory's own digest is recorded so a consumer
    can tell which inventory was evaluated.

    **It mints no byte-level claim.** All four limbs holding is necessary for the
    T-7 proof and is not sufficient for it: §11 emits a byte-level token only
    from a component that opened the artifact, and this one opened nothing. The
    returned :class:`ProofResult` therefore carries
    :data:`BYTE_LEVEL_PROOF_PENDING` and the reason, however good the records
    are.
    """
    producers = _measurement_roster(producer_records, role=ROLE_PRODUCER)
    verifiers = _measurement_roster(verifier_records, role=ROLE_VERIFIER)

    missing_verified = [p for p in producers if p not in verifiers]
    if missing_verified:
        raise ProofLimbAbsentError(
            f"no independent verifier measurement for {sorted(missing_verified)}; attestation "
            "is by the verifier, never the producer"
        )
    for pair in PAIRS_20:
        if pair in producers and pair in verifiers:
            assert_records_agree(producers[pair], verifiers[pair])

    _limb_bi(producers)
    _limb_bi(verifiers)
    _limb_tc(producers)
    coverage = _limb_cv(coverage_result, producers)
    _limb_db(derivation_bindings, producers)

    return ProofResult(
        byte_level_status=BYTE_LEVEL_PROOF_PENDING,
        claim_withheld_because=BYTE_LEVEL_CLAIM_WITHHELD_REASON,
        evidence_basis=LIMB_EVALUATION_EVIDENCE_BASIS,
        verifier_independence_basis=VERIFIER_INDEPENDENCE_BASIS,
        declared_not_measured=DECLARED_NOT_MEASURED_BY_THIS_LAYER,
        files_opened=0,
        bytes_measured=0,
        inventory_digest=_require_hex_digest(inventory_digest, what="inventory_digest"),
        calendar_digest=_require_content_digest(coverage.calendar_digest, what="calendar_digest"),
        _identity={
            p: _ArtifactIdentity(
                artifact_id=producers[p].artifact_id,
                sha256=producers[p].sha256,
                size_bytes=producers[p].size_bytes,
                measured_stream_ids=frozenset(
                    {
                        producers[p].digest_provenance.stream_id,
                        verifiers[p].digest_provenance.stream_id,
                    }
                ),
            )
            for p in PAIRS_20
        },
        _construction_token=_ProofConstructionToken(_PROOF_RESULT_PURPOSE),
    )


# ---------------------------------------------------------------------------
# W3 — consumer re-verification immediately before use
# ---------------------------------------------------------------------------


def open_for_consumption(result: Any, *, consumer_rechecks: Any) -> ConsumptionApproval:
    """The check a consumer must run **immediately before use**; no proof escapes it.

    W3 makes re-verification a precondition of use, not a one-time proof. A
    proof without a fresh consumer re-measurement is **not usable**, so
    ``consumer_rechecks`` is keyword-only with no default and an empty or absent
    set raises rather than being read as "nothing to check". It is also the only
    route to the proof's per-artifact identity: while that map was public a
    consumer could read the digests off the result and skip this call entirely.

    **N-2 — the disclosure fields are re-checked, not copied.** An earlier
    revision argued here that "re-reading fields the constructor already
    guarantees would be the vacuous check R-1 forbids". That reasoning was
    wrong, and it is retracted: the constructor guarantees what a field held *at
    construction*, and a frozen dataclass is not sealed afterwards. This function
    then **minted a new record** carrying those fields verbatim, so a
    ``ProofResult`` tampered with ``object.__setattr__`` produced a fresh
    ``ConsumptionApproval`` asserting a byte-level measurement beside
    ``files_opened=0``. R-1 forbids reporting a field that can hold only one
    value; it does not forbid verifying that a field a *consumer* handed back
    still holds it. :func:`_assert_disclosure_untampered` does that, exactly as
    :func:`_limb_cv` re-checks ``per_pair`` for the same reason.

    The returned :class:`ConsumptionApproval` **authorises no read**. It repeats
    the pending status and states, in the value itself, that this layer opened no
    file and measured no byte.
    """
    if not isinstance(result, ProofResult):
        raise ProofNotUsableError(
            f"consumption requires an evaluated ProofResult, got {type(result).__name__}"
        )
    _assert_disclosure_untampered(result)
    if consumer_rechecks is None:
        raise ProofNotUsableError(
            "no consumer re-verification supplied; a proof that has not been re-verified "
            "immediately before use is not usable"
        )
    if isinstance(consumer_rechecks, (str, bytes, bytearray)) or not isinstance(
        consumer_rechecks, Sequence
    ):
        raise ProofNotUsableError(
            f"consumer re-verification must be a concrete sequence of ConsumerRecheck, got "
            f"{type(consumer_rechecks).__name__}"
        )
    items = tuple(consumer_rechecks)
    if not items:
        raise ProofNotUsableError(
            "the consumer re-verification set is empty; skipping the re-check is not the same "
            "as passing it"
        )
    by_pair: dict[str, ConsumerRecheck] = {}
    for index, item in enumerate(items):
        if not isinstance(item, ConsumerRecheck):
            raise ProofNotUsableError(
                f"consumer re-verification {index} is a {type(item).__name__}, not a "
                "ConsumerRecheck"
            )
        if item.pair in by_pair:
            raise ProofNotUsableError(f"{item.pair} is re-verified twice")
        by_pair[item.pair] = item
    missing = [p for p in PAIRS_20 if p not in by_pair]
    if missing:
        raise ProofNotUsableError(
            f"no consumer re-verification for {missing}; every artifact is re-verified before "
            "any row of it is read"
        )
    for pair in PAIRS_20:
        recheck = by_pair[pair]
        identity = result._identity[pair]  # noqa: SLF001 - W3 is the accessor
        if recheck.artifact_id != identity.artifact_id:
            raise ProofDisagreementError(
                f"{pair}: consumer re-verified artifact {recheck.artifact_id!r} but the proof "
                f"was made about {identity.artifact_id!r}"
            )
        # The recheck carried a provenance that nothing ever compared, so the
        # producer's own read satisfied W3 by being handed back verbatim. A
        # re-verification "immediately before use" is the consumer's own read.
        if recheck.provenance.stream_id in identity.measured_stream_ids:
            raise ProofNotUsableError(
                f"{pair}: the consumer cites byte-stream pass "
                f"{recheck.provenance.stream_id!r}, which is one of the passes the proof was "
                "made from; W3 requires the consumer's own fresh read, not a replay of the "
                "producer's or the verifier's"
            )
        if recheck.sha256 != identity.sha256:
            raise ProofDisagreementError(
                f"{pair}: the artifact digest changed between the proof ({identity.sha256}) and "
                f"consumption ({recheck.sha256}) — terminal"
            )
        if recheck.size_bytes != identity.size_bytes:
            raise ProofDisagreementError(
                f"{pair}: the artifact byte size changed between the proof "
                f"({identity.size_bytes}) and consumption ({recheck.size_bytes}) — terminal"
            )
    return ConsumptionApproval(
        byte_level_status=result.byte_level_status,
        claim_withheld_because=result.claim_withheld_because,
        evidence_basis=result.evidence_basis,
        declared_not_measured=result.declared_not_measured,
        files_opened=0,
        bytes_measured=0,
        inventory_digest=result.inventory_digest,
        identity={
            pair: (
                result._identity[pair].artifact_id,  # noqa: SLF001 - W3 is the accessor
                result._identity[pair].sha256,  # noqa: SLF001 - W3 is the accessor
                result._identity[pair].size_bytes,  # noqa: SLF001 - W3 is the accessor
            )
            for pair in PAIRS_20
        },
        _construction_token=_ProofConstructionToken(_APPROVAL_PURPOSE),
    )


__all__ = [
    "AGGREGATE_ASSERTIONS",
    "BYTE_LEVEL_CLAIM_TOKENS",
    "BYTE_LEVEL_CLAIM_WITHHELD_REASON",
    "BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN",
    "BYTE_LEVEL_PROOF_PENDING",
    "BYTE_LEVEL_PROOF_REFUTED",
    "BYTE_LEVEL_STATUS_TOKENS",
    "DECLARATION_ONLY_TOKENS",
    "DECLARED_NOT_MEASURED_BY_THIS_LAYER",
    "DERIVATION_IDENTITY_BOUND",
    "FOUR_LIMBS",
    "LIMB_EVALUATION_EVIDENCE_BASIS",
    "ROLE_PRODUCER",
    "ROLE_VERIFIER",
    "SUBJECT_DERIVED_M15_ARTIFACT",
    "TOKEN_EVIDENTIARY_BASIS",
    "TOKEN_VOCABULARY",
    "VERIFIER_INDEPENDENCE_BASIS",
    "AggregateAssertionUnsatisfiedError",
    "ConsumerRecheck",
    "ConsumptionApproval",
    "DeclarationRecord",
    "DerivationBinding",
    "MeasurementRecord",
    "ProofCoMeasurementError",
    "ProofConstructionError",
    "ProofContractError",
    "ProofDisagreementError",
    "ProofLimbAbsentError",
    "ProofLimbUnsatisfiedError",
    "ProofNotUsableError",
    "ProofPromotionError",
    "ProofResult",
    "Provenance",
    "RawSourceRehashForbiddenError",
    "assert_byte_level_claim",
    "assert_measured_conjunction",
    "assert_records_agree",
    "evaluate_four_limbs",
    "is_declaration_only",
    "open_for_consumption",
    "refuse_raw_source_rehash",
]
