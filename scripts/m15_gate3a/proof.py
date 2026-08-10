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
(A5, A6)`` — and :func:`current_byte_level_proof_status` returns that pending
status because no producer or verifier package exists yet.

Why promotion cannot happen here
--------------------------------
It is structural, not a comment:

* :class:`DeclarationRecord` and :class:`MeasurementRecord` are distinct frozen
  types. There is no constructor, classmethod, coercion or ``**kwargs`` path
  that turns the first into the second, and the limb evaluator type-checks its
  inputs and raises :class:`ProofPromotionError` on a declaration record.
* :class:`MeasurementRecord` cannot be built at all without per-quantity
  co-measurement provenance that must be identical across digest, size, span and
  scan — something declared metadata does not have and cannot fabricate without
  asserting a single byte-stream pass it never made.
* The declaration-only token is owned by :mod:`scripts.m15_gate3a.no_overlap`,
  which has **no import edge to this module**, so no byte-level token string is
  reachable from the declaration-only code path.
* The byte-level claim tokens are returned from exactly one place —
  :func:`evaluate_four_limbs` — and only after all four limbs are satisfied.

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
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from scripts.m15_gate3a.coverage import CoverageResult
from scripts.m15_gate3a.no_overlap import (
    DECLARATION_ONLY_EVIDENCE_BASIS,
    DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL,
    NoOverlapError,
    assert_design_bounds,
)
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
if set(TOKEN_EVIDENTIARY_BASIS) != set(TOKEN_VOCABULARY):  # pragma: no cover - import guard
    raise RuntimeError("every token in the vocabulary must name its evidentiary basis")

#: The four limbs of D-11. All are required; there is no partial proof.
FOUR_LIMBS: Final[tuple[str, ...]] = ("BI", "TC", "CV", "DB")

#: Aggregate assertions committed in ``design_m15_inventory.json``. Each is a
#: measured conjunction over the 20 pairs (D-8 / NR-C, §12.15).
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


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Provenance:
    """Which byte stream, and which pass over it, produced a measured quantity.

    §12.12 requires the digest and the measured span to be co-measured from one
    pass over one byte stream. Recording provenance *per quantity* and requiring
    the four to be identical is what makes that checkable: a record assembled
    from two reads carries two provenances and is refused.
    """

    stream_id: str
    pass_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.stream_id, str) or not self.stream_id.strip():
            raise ProofCoMeasurementError("provenance stream_id must be a non-empty string")
        if isinstance(self.pass_index, bool) or not isinstance(self.pass_index, int):
            raise ProofCoMeasurementError("provenance pass_index must be an int")
        if self.pass_index < 0:
            raise ProofCoMeasurementError("provenance pass_index must not be negative")


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


def _require_count(value: Any, *, what: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProofContractError(f"{what} must be an int, got {type(value).__name__}")
    if value < minimum:
        raise ProofContractError(f"{what} must be >= {minimum}, got {value}")
    return value


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


@dataclass(frozen=True, slots=True)
class ProofResult:
    """The four-limb conjunction. Constructed only by :func:`evaluate_four_limbs`."""

    token: str
    derivation_token: str
    limbs_evaluated: frozenset[str]
    pairs_measured: tuple[str, ...]
    inventory_digest: str
    calendar_digest: str
    aggregate_assertions: Mapping[str, bool]
    identity: Mapping[str, tuple[str, str, int]]

    @property
    def evidentiary_basis(self) -> str:
        return TOKEN_EVIDENTIARY_BASIS[self.token]


@dataclass(frozen=True, slots=True)
class ConsumptionApproval:
    """Returned only when a consumer re-verified every artifact it is about to read."""

    token: str
    pairs_reverified: tuple[str, ...]
    inventory_digest: str


# ---------------------------------------------------------------------------
# Token discipline
# ---------------------------------------------------------------------------


def is_declaration_only(token: Any) -> bool:
    """True iff ``token`` rests on caller-declared metadata."""
    return token in DECLARATION_ONLY_TOKENS


def assert_byte_level_claim(token: Any) -> str:
    """Return ``token`` if it is a byte-level claim; refuse anything weaker.

    This is the promotion guard in its most direct form: a declaration-only
    token offered where a byte-level claim is required is refused by name, and
    a pending or refuted status is not a claim either.
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


def current_byte_level_proof_status() -> str:
    """The live status: pending, because no byte-level measurement exists yet.

    The producer and verifier packages that could measure one are placed at a
    later gate (contract §15.4). This mirrors the committed
    ``no_overlap_proof.json`` position — A1-A4 proven at the source level, A5 and
    A6 pending — and is the default any consumer sees today.
    """
    return BYTE_LEVEL_PROOF_PENDING


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
    return by_pair


_AGREEING_FIELDS: Final[tuple[str, ...]] = (
    "artifact_id",
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
    if producer.digest_provenance == verifier.digest_provenance:
        raise ProofContractError(
            f"{producer.pair}: the verifier cites the producer's own byte-stream pass; a "
            "verifier re-measures independently rather than replaying the producer's read"
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


def _limb_tc(records: Mapping[str, MeasurementRecord]) -> dict[str, dict[str, bool]]:
    """TC — time containment, measured by full scan, never inferred from endpoints."""
    measured: dict[str, dict[str, bool]] = {
        "dead_window_bars_present_is_zero": {},
        "all_ts_max_within_design_end": {},
        "all_ts_min_within_design_start": {},
    }
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
        measured["dead_window_bars_present_is_zero"][pair] = True
        measured["all_ts_max_within_design_end"][pair] = True
        measured["all_ts_min_within_design_start"][pair] = True
    return measured


def _limb_cv(coverage_result: Any) -> CoverageResult:
    """CV — coverage: set equality per pair, already raised on by :mod:`coverage`."""
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
    # Reachable: CoverageResult is a public frozen dataclass, so a caller can hand
    # in a hand-built unsatisfied result without ever going through
    # `assert_full_coverage`. Pinned by
    # test_the_cv_limb_refuses_a_hand_built_unsatisfied_coverage_result.
    if not coverage_result.satisfied:
        raise ProofLimbUnsatisfiedError("CV limb: the 20-pair coverage conjunction is not held")
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
    """Evaluate **BI ∧ TC ∧ CV ∧ DB** and mint the byte-level claim, or refuse.

    Every argument is keyword-only with **no default**, so a limb cannot be
    omitted by accident: leaving one out is a ``TypeError`` and passing ``None``
    raises :class:`ProofLimbAbsentError` naming the limb. There is no partial
    proof and no evaluation mode that skips a limb.

    ``inventory_digest`` closes W2: the record set is built atomically at the end
    of each single pass, and the inventory's own digest is recorded in the proof
    so a consumer can tell which inventory the claim was made about.
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
    measured = _limb_tc(producers)
    coverage = _limb_cv(coverage_result)
    _limb_db(derivation_bindings, producers)

    measured["file_count_is_20"] = {p: True for p in PAIRS_20}
    aggregate = {
        name: assert_measured_conjunction(name, measured[name]) for name in AGGREGATE_ASSERTIONS
    }

    return ProofResult(
        token=BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
        derivation_token=DERIVATION_IDENTITY_BOUND,
        limbs_evaluated=frozenset(FOUR_LIMBS),
        pairs_measured=tuple(PAIRS_20),
        inventory_digest=_require_hex_digest(inventory_digest, what="inventory_digest"),
        calendar_digest=coverage.calendar_digest,
        aggregate_assertions=dict(aggregate),
        identity={
            p: (producers[p].artifact_id, producers[p].sha256, producers[p].size_bytes)
            for p in PAIRS_20
        },
    )


# ---------------------------------------------------------------------------
# W3 — consumer re-verification immediately before use
# ---------------------------------------------------------------------------


def open_for_consumption(result: Any, *, consumer_rechecks: Any) -> ConsumptionApproval:
    """The check a consumer must run **immediately before use**; no proof escapes it.

    W3 makes re-verification a precondition of use, not a one-time proof. A
    proof without a fresh consumer re-measurement is **not usable**, so
    ``consumer_rechecks`` is keyword-only with no default and an empty or absent
    set raises rather than being read as "nothing to check".
    """
    if not isinstance(result, ProofResult):
        raise ProofNotUsableError(
            f"consumption requires an evaluated ProofResult, got {type(result).__name__}"
        )
    assert_byte_level_claim(result.token)
    if result.limbs_evaluated != frozenset(FOUR_LIMBS):
        raise ProofNotUsableError(
            f"proof evaluated only {sorted(result.limbs_evaluated)}; all of {list(FOUR_LIMBS)} "
            "are required before any artifact may be consumed"
        )
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
        artifact_id, sha256, size_bytes = result.identity[pair]
        if recheck.artifact_id != artifact_id:
            raise ProofDisagreementError(
                f"{pair}: consumer re-verified artifact {recheck.artifact_id!r} but the proof "
                f"was made about {artifact_id!r}"
            )
        if recheck.sha256 != sha256:
            raise ProofDisagreementError(
                f"{pair}: the artifact digest changed between the proof ({sha256}) and "
                f"consumption ({recheck.sha256}) — terminal"
            )
        if recheck.size_bytes != size_bytes:
            raise ProofDisagreementError(
                f"{pair}: the artifact byte size changed between the proof ({size_bytes}) and "
                f"consumption ({recheck.size_bytes}) — terminal"
            )
    return ConsumptionApproval(
        token=result.token,
        pairs_reverified=tuple(PAIRS_20),
        inventory_digest=result.inventory_digest,
    )


__all__ = [
    "AGGREGATE_ASSERTIONS",
    "BYTE_LEVEL_CLAIM_TOKENS",
    "BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN",
    "BYTE_LEVEL_PROOF_PENDING",
    "BYTE_LEVEL_PROOF_REFUTED",
    "BYTE_LEVEL_STATUS_TOKENS",
    "DECLARATION_ONLY_TOKENS",
    "DERIVATION_IDENTITY_BOUND",
    "FOUR_LIMBS",
    "ROLE_PRODUCER",
    "ROLE_VERIFIER",
    "SUBJECT_DERIVED_M15_ARTIFACT",
    "TOKEN_EVIDENTIARY_BASIS",
    "TOKEN_VOCABULARY",
    "AggregateAssertionUnsatisfiedError",
    "ConsumerRecheck",
    "ConsumptionApproval",
    "DeclarationRecord",
    "DerivationBinding",
    "MeasurementRecord",
    "ProofCoMeasurementError",
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
    "current_byte_level_proof_status",
    "evaluate_four_limbs",
    "is_declaration_only",
    "open_for_consumption",
    "refuse_raw_source_rehash",
]
