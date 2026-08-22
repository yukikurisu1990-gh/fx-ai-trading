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

import weakref
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Final

from scripts.m15_gate3a.calendar_authority import SLOT_MINUTES
from scripts.m15_gate3a.coverage import CoverageResult, PairCoverage
from scripts.m15_gate3a.guards import UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS
from scripts.m15_gate3a.no_overlap import (
    DECLARATION_ONLY_EVIDENCE_BASIS,
    DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL,
    NoOverlapError,
    assert_design_bounds,
)
from scripts.m15_gate3a.numeric_authority import NumericAuthorityError, pin_int
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.sealing import assert_minted, register_minted, seal
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
#:
#: **P-7 — ruled explicitly, and restructured.** This constant used to open with
#: ``DISTINCT_DECLARED_BYTE_STREAM_PASSES_OVER_THE_SAME_STAGED_ARTIFACT__``, and
#: was named ``VERIFIER_INDEPENDENCE_BASIS`` on a field called
#: ``verifier_independence_basis``. That opening clause is a **favourable
#: assertion that can only ever hold one value**: :func:`assert_records_agree`
#: *raises* when the verifier cites the producer's stream id and when the two
#: passes name different artifacts, so no record carrying the sentence can ever
#: have failed it. R-1 deletes exactly that shape, and the deliberate exception
#: the module docstring records is for a constant that **denies** something.
#:
#: The decision taken here is to restructure rather than delete: the limitation
#: half is real, is the only thing §11 leaves unevidenced, and a record that
#: omitted it would be silent about it. So the sentence now leads with what is
#: **not** excluded, names the pass-distinctness requirement as a precondition a
#: raise enforces rather than as evidence, and the field is renamed
#: ``verifier_independence_limit`` so its key cannot be read as an attestation.
VERIFIER_INDEPENDENCE_LIMIT: Final[str] = (
    "SHARED_SCALAR_DERIVATION_CODE_NOT_EXCLUDED_BY_THIS_LAYER__"
    "TWO_DISTINCT_BYTE_STREAM_READS_ARE_A_PRECONDITION_A_RAISE_ENFORCES__"
    "NOT_EVIDENCE_OF_INDEPENDENCE"
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
    """Producer and verifier disagree. Fail-closed, and terminal for this evidence.

    ``token`` is :data:`BYTE_LEVEL_PROOF_REFUTED`.

    **FR-11 — what "terminal" means here, exactly.** This docstring used to say
    "the status is terminal, so a later re-measurement does not rehabilitate the
    proof", and nothing implemented it: the layer is stateless, so a caller that
    caught this error and re-ran got :data:`BYTE_LEVEL_PROOF_PENDING` back with
    no trace that a refutation had ever occurred. What is enforced now is that
    the *evidence this error was pronounced over* is dead — every record and
    every result named in the refusal is refused by identity from then on, with
    the original refutation quoted back. What is **not** enforced, and is no
    longer claimed, is terminality across a fresh evidence set or across
    processes: that requires persisting the refuted status, which belongs to the
    committed proof artifact and to the byte-reading packages at gate 4 (§15.4),
    not to a layer that opens nothing. See the ledger above
    :func:`_assert_not_refuted`.
    """

    token = BYTE_LEVEL_PROOF_REFUTED


class ProofNotUsableError(ProofContractError):
    """A consumer tried to use a proof without re-verifying it first (W3)."""


class AggregateAssertionUnsatisfiedError(ProofContractError):
    """An aggregate assertion lacks a measurement, so it is unsatisfied (D-8)."""


class ProofConstructionError(ProofContractError):
    """A proof record was built outside the function that evaluates it."""


# ---------------------------------------------------------------------------
# FR-11 — a refutation is terminal for the evidence it was pronounced over
# ---------------------------------------------------------------------------
#
# Section 11 requires a disagreement to be fail-closed **and terminal**.
# Fail-closed was real; terminality was a docstring property of a stateless
# layer, so a caller that caught `ProofDisagreementError` and re-ran got
# `BYTE_LEVEL_PROOF_PENDING` back with nothing recording that anything had ever
# been refuted, and `BYTE_LEVEL_PROOF_REFUTED` reached no record.
#
# What is enforced here, and what is not — the distinction is the whole of the
# honesty of the claim, so it is stated rather than left to be inferred:
#
# * **Enforced.** The evidence a refutation was pronounced over is dead. Any
#   later use of a refuted measurement record, or of a refuted proof result, is
#   refused by name and the refusal carries `BYTE_LEVEL_PROOF_REFUTED`, so
#   catching the error and retrying with the same evidence cannot yield a clean
#   result. The reason the refutation was pronounced is kept and re-reported,
#   which is the record that one occurred.
# * **Not enforced, and not claimed.** Terminality *across* evidence sets, and
#   across processes. A caller that re-measures and builds fresh records is
#   offering new evidence, and this reader-free layer holds no persistent state
#   in which a refuted *artifact* could be remembered — it opens nothing, so it
#   cannot tell that two record sets describe one file except by trusting the
#   labels on them. Durable terminality belongs to the component that persists
#   the proof status: the committed proof artifact, whose `result` field is
#   exactly where `BYTE_LEVEL_PROOF_REFUTED` would be written, and the
#   byte-reading producer/verifier packages at gate 4 (§15.4). The docstrings
#   now say this instead of asserting a property this layer does not have.
#
# The ledger is keyed by object **identity**. A `WeakSet` cannot express it:
# `weakref.ref` hashes and compares by *referent equality*, so condemning one
# record would condemn every record equal to it, and rewriting a field
# afterwards would silently un-condemn it. Entries are dropped by a weakref
# callback when the object dies, which is what makes `id()` reuse harmless.
_REFUTED: Final[dict[int, str]] = {}
_REFUTED_WATCH: Final[dict[int, Any]] = {}


def _mark_refuted(subject: Any, reason: str) -> None:
    key = id(subject)

    def _forget(_ref: Any, key: int = key) -> None:
        _REFUTED.pop(key, None)
        _REFUTED_WATCH.pop(key, None)

    # No `try` and no pragma: every refutation subject is one of this module's
    # sealed records, and `seal` refuses at **import** any slots dataclass
    # declared without `weakref_slot=True`, so the reference is always
    # constructible. A guard here would be an unreachable branch asserting the
    # opposite, which is the FR-20 anti-pattern one line down from its own fix.
    _REFUTED_WATCH[key] = weakref.ref(subject, _forget)
    _REFUTED[key] = reason


def _assert_not_refuted(subject: Any, *, what: str) -> None:
    """Refuse evidence a refutation was already pronounced over (FR-11)."""
    reason = _REFUTED.get(id(subject))
    if reason is None:
        return
    raise ProofDisagreementError(
        f"{what} was already refuted, and {BYTE_LEVEL_PROOF_REFUTED} is terminal: re-offering "
        f"the same evidence does not rehabilitate it. The refutation was: {reason}"
    )


def _refute(message: str, *subjects: Any) -> ProofDisagreementError:
    """Record the refutation against the evidence it condemns, then build the error.

    Every :class:`ProofDisagreementError` this module raises over caller-supplied
    evidence goes through here, so there is one place where "fail-closed" and
    "terminal" are the same act rather than two properties of which only the
    first was ever executed.
    """
    for subject in subjects:
        _mark_refuted(subject, message)
    return ProofDisagreementError(message)


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------


def _pin_text(value: Any, *, what: str, error: type[ProofContractError]) -> str:
    """Read a ``str``'s real character data once, through the unbound slot (FB-5).

    ``str.__str__`` is the pin :mod:`scripts.m15_gate3a.artifacts`,
    :mod:`scripts.m15_gate3a.timeutil` and
    :mod:`scripts.m15_gate3a.path_authority` already use, and
    :func:`~scripts.m15_gate3a.numeric_authority.pin_int` is its numeric twin.

    **Why one primitive and not five local fixes.** A ``str`` subclass owns
    ``__eq__``, ``__hash__``, ``__str__``, ``__repr__`` and ``__format__``, so
    *every* comparison written against the caller's own object — ``==``,
    ``!=``, ``in`` against a ``frozenset``, use as a ``dict`` key — asks that
    object whether it should be refused. FB-5 found five such comparisons in
    this module alone, deciding D-4 (the proof subject), D-11 (the promotion
    prohibition), the co-measurement roster de-dup, verifier independence, W3
    consumer freshness and the producer/verifier split — each with a plain-value
    control that was correctly refused. Patching those five would leave the
    sixth. The family is "a contract rule decided against an object instead of
    against its character data", and the structural remedy is to read the
    character data once, at the boundary, decide everything downstream against
    the plain value, and **store and publish that same value** (B-3 / P-3) so a
    later reader cannot be shown a different spelling.

    ``isinstance`` consults ``__class__``, which an arbitrary object may claim,
    so the unbound slot is called inside a ``try``: a spoofed ``__class__``
    lands on this module's documented error type instead of escaping as a bare
    ``TypeError`` (the RF-29 class), exactly as ``numeric_authority._index``
    does for ``int.__index__``.
    """
    if not isinstance(value, str):
        raise error(f"{what} must be a string, got {type(value).__name__}")
    try:
        return str.__str__(value)
    except TypeError as exc:
        raise error(
            f"{what} claims to be a str but is a {type(value).__name__} that the str slot "
            f"refuses: {exc}"
        ) from exc


def _assert_minted(record: Any, *, what: str) -> None:
    """:func:`~scripts.m15_gate3a.sealing.assert_minted` with this module's error type (FR-3).

    ``object.__new__`` bypasses ``__post_init__`` outright — no ``__new__``
    override can intercept it — so twenty forged :class:`MeasurementRecord`\\ s
    carrying ``subject='RAW_M1_SOURCE_BYTES'``, ``size_bytes=-1``, a reversed
    span and ``dead_window_bars_by_bucket_start=7`` were accepted by the roster:
    every field check in ``__post_init__`` had run on nothing, and ``isinstance``
    cannot tell the two apart. The registry can, because a record built that way
    is absent from it.

    The shared registry is keyed by object **identity**, which is what makes the
    check answerable at all: it touches none of the record's own methods, so a
    forgery cannot answer it with ``__eq__`` or ``__hash__``, a forgery whose
    fields merely *equal* a live genuine record's is not authenticated, and a
    genuine record whose field was rewritten afterwards is not de-authenticated
    (that is the declared threat model, and it is caught by the field re-checks
    at each boundary, which name the field).
    """
    assert_minted(record, what=what, error=ProofConstructionError)


def _require_hex_digest(value: Any, *, what: str) -> str:
    if not isinstance(value, str):
        raise ProofContractError(f"{what} must be a 64-hex string, got {type(value).__name__}")
    text = _pin_text(value, what=what, error=ProofContractError)
    if len(text) != _SHA256_HEX_LENGTH or any(c not in _HEX_DIGITS for c in text):
        raise ProofContractError(f"{what} is not a well-formed 64-hex SHA-256 digest")
    return text.lower()


def _require_identifier(value: Any, *, what: str) -> str:
    """An artifact identifier, never a path (D-11 "Identity")."""
    if not isinstance(value, str):
        raise ProofContractError(f"{what} must be a non-empty string")
    text = _pin_text(value, what=what, error=ProofContractError)
    if not text.strip():
        raise ProofContractError(f"{what} must be a non-empty string")
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
    text = _pin_text(value, what=what, error=ProofContractError)
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
    except NumericAuthorityError as exc:
        # FR-20: NOT unreachable, and the `# pragma: no cover - guarded above`
        # that sat here asserted the opposite. `isinstance` consults
        # `__class__`, which an arbitrary object may claim, and the unbound
        # `int.__index__` slot then refuses it — so an object whose `__class__`
        # says `int` enters this branch. It is pinned by a test.
        raise ProofContractError(str(exc)) from exc
    if pinned < minimum:
        raise ProofContractError(f"{what} must be >= {minimum}, got {pinned}")
    return pinned


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
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
        # FB-5: `stream_id` was the one field of three that was neither pinned
        # nor stored pinned, while `pass_index` went through `pin_int` and
        # `artifact_id` through `_require_identifier`. It decides the
        # co-measurement roster de-dup, the verifier-independence check and the
        # W3 consumer-freshness check — three contract rules, all expressed as
        # `==` or `in` against the caller's own object, so two `Provenance` over
        # one real byte-stream pass could compare unequal and hash distinctly.
        if not isinstance(self.stream_id, str):
            raise ProofCoMeasurementError("provenance stream_id must be a non-empty string")
        stream_id = _pin_text(
            self.stream_id, what="provenance stream_id", error=ProofCoMeasurementError
        )
        if not stream_id.strip():
            raise ProofCoMeasurementError("provenance stream_id must be a non-empty string")
        object.__setattr__(self, "stream_id", stream_id)
        if isinstance(self.pass_index, bool) or not isinstance(self.pass_index, int):
            raise ProofCoMeasurementError("provenance pass_index must be an int")
        # N-1: pinned before the bound test, and stored pinned so the pass
        # identity a roster de-duplicates on is a plain int.
        try:
            object.__setattr__(self, "pass_index", pin_int(self.pass_index, what="pass_index"))
        except NumericAuthorityError as exc:
            # FR-20: reachable, for the reason recorded on `_require_count`.
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
        register_minted(self)


#: The `datetime` accessors, unbound. A `datetime` subclass can override
#: `__eq__`, `year`, `isoformat` and every comparison operator, so reading them
#: off the object asks the object to answer a question about itself.
_INSTANT_PARTS: Final[tuple[str, ...]] = (
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "second",
    "microsecond",
)


def _pin_instant(value: Any, *, what: str) -> datetime:
    """Rebuild a **plain** ``datetime`` from *value*'s components.

    The FB-5 family, applied to instants. A comparison like
    ``entry.certified_slot_min != record.measured_ts_min`` is answered by
    whichever operand's ``__eq__`` Python reaches, so a subclass that reports one
    span to the guard and another to the reader defeats it — an audit did exactly
    that against the FR-4 binding. Reconstructing through the unbound descriptors
    means the value that gets compared is character-for-character the value the
    object holds, and a subclass has nothing left to override.
    """
    if not isinstance(value, datetime):
        raise ProofContractError(f"{what} must be a datetime, got {type(value).__name__}")
    try:
        rebuilt = datetime(
            *(getattr(datetime, name).__get__(value) for name in _INSTANT_PARTS),
            tzinfo=datetime.tzinfo.__get__(value),
        )
    except (TypeError, ValueError, AttributeError) as exc:
        raise ProofContractError(f"{what} is not plain datetime data: {exc}") from exc
    if rebuilt.utcoffset() != timedelta(0):
        raise ProofContractError(
            f"{what} must be UTC-aware; a naive or offset instant is not comparable "
            "with a measured span"
        )
    return rebuilt


def _pin_artifact_id(provenance: Any, *, what: str) -> str:
    """Re-read `Provenance.artifact_id`, for the reason `_pin_pass` exists.

    ``artifact_id`` was pinned at construction and then compared raw at three
    boundaries, while ``stream_id`` and ``pass_index`` beside it were re-read —
    and the reason given for re-reading them, ``object.__setattr__`` on a real
    record being this package's declared threat model, applies identically here.
    An internal audit used the gap twice: one fabricated pass answered ``==`` for
    all twenty pairs (defeating DI-5's remedy, that a provenance naming no
    particular artifact cannot be reused across pairs), and a verifier whose pass
    really named a different file passed the "reads the same artifact" check.
    """
    return _pin_text(provenance.artifact_id, what=f"{what} artifact_id", error=ProofContractError)


def _pin_pass(provenance: Any, *, what: str) -> tuple[str, int]:
    """The pass identity a roster de-duplicates on, as plain character data.

    ``Provenance.__post_init__`` already pins both halves, so on a genuine,
    untampered record this returns what is stored. It is re-read here because
    ``object.__setattr__`` on a real record is this package's **declared** threat
    model — stated on :class:`_ProofConstructionToken` and in
    ``coverage.assert_full_coverage`` — and no minting registry can see it. The
    de-dup that stops one fabricated pass serving twenty pairs (DI-5) is decided
    on this value, so it is the value that must be plain.
    """
    _assert_minted(provenance, what=f"{what} provenance")
    stream_id = _pin_text(
        provenance.stream_id, what=f"{what} stream_id", error=ProofCoMeasurementError
    )
    try:
        pass_index = pin_int(provenance.pass_index, what=f"{what} pass_index")
    except NumericAuthorityError as exc:
        raise ProofCoMeasurementError(f"{what} pass_index: {exc}") from exc
    return stream_id, pass_index


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
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
        # FB-5 family: ``in`` against a ``frozenset`` is decided by the caller's
        # own ``__hash__``/``__eq__``, so the token is read as character data
        # first and a non-``str`` is not a token in this vocabulary at all.
        token = self.token if isinstance(self.token, str) else None
        if token is not None:
            token = _pin_text(token, what="declaration record token", error=ProofPromotionError)
        if token is None or token not in DECLARATION_ONLY_TOKENS:
            raise ProofPromotionError(
                f"a declaration record may only carry a declaration-only token, got "
                f"{token if token is not None else self.token!r}; declared metadata never "
                "becomes a byte-level claim"
            )
        object.__setattr__(self, "token", token)
        register_minted(self)


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
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
        # FB-5: the producer/verifier split was decided by `in` against the
        # caller's own object, so one record was accepted into **both** rosters.
        role = self.role if isinstance(self.role, str) else None
        if role is not None:
            role = _pin_text(role, what="measurement role", error=ProofContractError)
        if role is None or role not in (ROLE_PRODUCER, ROLE_VERIFIER):
            raise ProofContractError(
                f"measurement role must be {ROLE_PRODUCER!r} or {ROLE_VERIFIER!r}, "
                f"got {role if role is not None else self.role!r}"
            )
        object.__setattr__(self, "role", role)
        # D-4: hashing is a byte read; the proof subject is the DERIVED artifact.
        # FB-5: a `str` subclass whose real character data was
        # `RAW_M1_SOURCE_BYTES` answered this `!=` favourably and was accepted,
        # which is D-4 defeated by the caller's own object. Decide on the
        # character data, and store the character data.
        subject = self.subject if isinstance(self.subject, str) else None
        if subject is not None:
            subject = _pin_text(
                subject, what="measurement subject", error=RawSourceRehashForbiddenError
            )
        if subject is None or subject != SUBJECT_DERIVED_M15_ARTIFACT:
            raise RawSourceRehashForbiddenError(
                f"measurement subject "
                f"{subject if subject is not None else self.subject!r} is not the derived M15 "
                "artifact; raw source bytes are never hashed without their own explicit read "
                "authorisation, and 'checksum only' is not an exception"
            )
        object.__setattr__(self, "subject", subject)
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
        distinct = {
            _pin_pass(prov, what=f"{self.pair} {name}") for name, prov in provenances.items()
        }
        if len(distinct) != 1:
            raise ProofCoMeasurementError(
                f"{self.pair}: digest, size, span and scan cite {len(distinct)} different "
                "byte-stream passes; they must be co-measured from a single pass over one "
                "byte stream and the record built atomically at the end of it"
            )
        for name, prov in provenances.items():
            if _pin_artifact_id(prov, what=f"{name} pass") != self.staged_artifact_id:
                raise ProofCoMeasurementError(
                    f"{self.pair}: the {name} pass says it read {prov.artifact_id!r} while the "
                    f"record describes {self.staged_artifact_id!r}; a provenance that names no "
                    "particular artifact can be reused across every quantity and every pair"
                )
        register_minted(self)

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


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
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
            text = (
                _pin_text(
                    value, what=f"derivation binding field {name!r}", error=ProofContractError
                )
                if isinstance(value, str)
                else None
            )
            if text is None or not text.strip():
                raise ProofContractError(
                    f"derivation binding field {name!r} must be a non-empty string; the bytes "
                    "must be bound to a named script, git SHA, config hash and source identity"
                )
            object.__setattr__(self, name, text)
        object.__setattr__(
            self,
            "re_derivation_sha256",
            _require_hex_digest(self.re_derivation_sha256, what="re_derivation_sha256"),
        )
        register_minted(self)


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
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
        # The consumer's own pass identity is what W3 freshness is decided on
        # (`stream_id in identity.measured_stream_ids`), so it is authenticated
        # and pinned here rather than trusted.
        _pin_pass(self.provenance, what=f"{self.pair} consumer recheck")
        if _pin_artifact_id(self.provenance, what="recheck provenance") != self.artifact_id:
            raise ProofContractError(
                f"{self.pair}: the consumer's read says it opened "
                f"{self.provenance.artifact_id!r} while the recheck describes "
                f"{self.artifact_id!r}; a re-verification is of the artifact about to be read"
            )
        register_minted(self)


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
class _ArtifactIdentity:
    """What the proof was made about for one pair, and which passes made it.

    Private on purpose. W3 rules re-verification a *precondition of use*, and
    while the proof published its identity map any consumer could read the
    digest, size and identifier straight off the result and never call
    :func:`open_for_consumption` at all.

    **FB-6 — the previous sentence here said the identity is "reachable only
    through that call", and it was false.** Underscore-prefixing a dataclass
    field hides it from nothing: :func:`dataclasses.asdict` and
    :func:`dataclasses.astuple` recurse over dataclass fields themselves and
    never consult ``__copy__``, ``__deepcopy__`` or ``__reduce__``, all three of
    which this package had correctly refused. One plain stdlib call — no hostile
    object, no private name — rebuilt the whole twenty-pair map, digests and
    sizes included, with ``open_for_consumption`` never called. The claim is
    made true by :class:`_IdentityVault`, which is what the field now holds; the
    limit that remains is the one this package discloses everywhere else — a
    caller reaching for a private attribute is not stopped by any of this.
    """

    artifact_id: str
    sha256: str
    size_bytes: int
    measured_stream_ids: frozenset[str]

    def __post_init__(self) -> None:
        register_minted(self)


class _IdentityVault(Mapping[str, _ArtifactIdentity]):
    """The per-artifact identity map, closed to the recursive stdlib copies (FB-6).

    Gating the identity is this layer's **entire** enforcement of W3, so the
    route that bypassed the gate is the route that mattered. It was not a
    protocol this package had forgotten to refuse: ``asdict``/``astuple``
    recurse into dataclasses, lists, tuples and ``dict`` objects and reach
    :func:`copy.deepcopy` for **everything else**. This is a ``Mapping`` that is
    none of those four, so both functions arrive at ``deepcopy`` — which is
    refused here, by the same reasoning N-5 applied one function further in.

    Structural rather than a fifth denylisted entry point: any future stdlib
    walker that recurses over dataclass fields hits the same wall, because the
    map is no longer a shape such a walker knows how to descend into.

    ``dict(vault)`` still works for a caller that already holds the private
    attribute. That is deliberate — the disclosed limit of this package is
    "reaching into private names is not stopped", and pretending otherwise is
    the kind of claim these audits keep falsifying.
    """

    __slots__ = ("_by_pair", "__weakref__")

    def __init__(self, by_pair: Mapping[str, _ArtifactIdentity]) -> None:
        self._by_pair: dict[str, _ArtifactIdentity] = dict(by_pair)

    def __getitem__(self, pair: str) -> _ArtifactIdentity:
        return self._by_pair[pair]

    def __iter__(self) -> Iterator[str]:
        return iter(self._by_pair)

    def __len__(self) -> int:
        return len(self._by_pair)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: {len(self._by_pair)} artifact identities, withheld>"

    def _refuse_copy(self, *_args: Any) -> Any:
        raise ProofNotUsableError(
            "the proof's per-artifact identity is reachable only through "
            "open_for_consumption(); copying the record republishes every artifact's digest "
            "and byte size with no W3 re-verification, which is the precondition of use it "
            "exists to enforce"
        )

    __copy__ = _refuse_copy
    __deepcopy__ = _refuse_copy
    __reduce__ = _refuse_copy


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


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
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
    verifier_independence_limit: str
    declared_not_measured: tuple[str, ...]
    files_opened: int
    bytes_measured: int
    inventory_digest: str
    calendar_digest: str
    #: FB-6: an `_IdentityVault`, not a plain mapping — see that class. The
    #: annotation is the type `evaluate_four_limbs` mints; `open_for_consumption`
    #: still validates what it finds here, because `object.__setattr__` can
    #: replace it with anything.
    _identity: _IdentityVault = field(repr=False, compare=False)
    _construction_token: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _spend(
            self._construction_token,
            purpose=_PROOF_RESULT_PURPOSE,
            what="ProofResult",
            minted_by="evaluate_four_limbs",
        )
        object.__setattr__(self, "_construction_token", None)
        register_minted(self)

    __copy__ = _refuse_reconstruction
    __deepcopy__ = _refuse_reconstruction
    __reduce__ = _refuse_reconstruction


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
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
        register_minted(self)

    __copy__ = _refuse_reconstruction
    __deepcopy__ = _refuse_reconstruction
    __reduce__ = _refuse_reconstruction


# ---------------------------------------------------------------------------
# Token discipline
# ---------------------------------------------------------------------------


def is_declaration_only(token: Any) -> bool:
    """True iff ``token`` rests on caller-declared metadata.

    FB-5 family: ``in`` against a ``frozenset`` is answered by the caller's own
    ``__hash__`` and ``__eq__``, so the character data is read first. A
    non-``str`` is not a token in this closed vocabulary, so it is not
    declaration-only either — and this is a predicate, not a guard, so it says
    ``False`` rather than raising.
    """
    if not isinstance(token, str):
        return False
    try:
        text = str.__str__(token)
    except TypeError:
        return False
    return text in DECLARATION_ONLY_TOKENS


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
    return _pin_text(value, what=what, error=ProofNotUsableError)


def _pin_disclosure_count(value: Any, *, what: str) -> int:
    """The plain ``int`` character data of a disclosure count, or refuse it (P-2).

    ``(result.files_opened, result.bytes_measured) != (0, 0)`` compares the tuple
    element-wise with ``==``, which asks the caller's own object whether it is
    zero. An ``int`` subclass answering every equality favourably held 20 and 999
    through that guard — an N-1 miss inside the N-2 fix.
    """
    try:
        return pin_int(value, what=what)
    except NumericAuthorityError as exc:
        raise ProofNotUsableError(
            f"{what} is not a plain integer count ({exc}); the proof record was rewritten "
            "after construction"
        ) from exc


def _pin_declared_not_measured(value: Any) -> tuple[str, ...]:
    """Pin every entry of the disclosure list before comparing any of them (P-1).

    ``tuple(value) != DECLARED_NOT_MEASURED_BY_THIS_LAYER`` compares element-wise
    with ``==``, so thirteen same-length ``str`` subclasses answering every
    equality favourably passed it and were then copied verbatim onto the
    approval. Measured with ``''`` (the disclosure of which quantities were
    consumed as declarations simply erased), ``'-'``, ``'measured'`` and
    ``'MEASURED_FROM_DERIVED_ARTIFACT_BYTES'`` — and every one of those payloads
    scans clean, because a scrubber cannot know which thirteen names belong
    there. The length check the N-2 test exercises catches only a *shortened*
    list.
    """
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ProofNotUsableError(
            f"declared_not_measured is not a list of quantity names but a "
            f"{type(value).__name__}; the proof record was rewritten after construction"
        )
    entries = tuple(value)
    if len(entries) != len(DECLARED_NOT_MEASURED_BY_THIS_LAYER):
        raise ProofNotUsableError(
            "the proof record's declared_not_measured list is not the one this layer emits; "
            "shortening it would hide which quantities were consumed as declarations"
        )
    pinned = tuple(
        _pin_token(entry, what=f"declared_not_measured[{index}]")
        for index, entry in enumerate(entries)
    )
    for index, (got, expected) in enumerate(
        zip(pinned, DECLARED_NOT_MEASURED_BY_THIS_LAYER, strict=True)
    ):
        if got != expected:
            raise ProofNotUsableError(
                f"the proof record's declared_not_measured entry {index} is {got!r}, not "
                f"{expected!r}; this layer discloses a fixed list of the quantities it "
                "consumed as declarations, and rewriting an entry hides one of them"
            )
    return pinned


@seal(error=ProofConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
class _PinnedDisclosure:
    """The disclosure fields, read once as plain built-in character data (P-3).

    :func:`_assert_disclosure_untampered` pinned each token *for its comparison*
    and :func:`open_for_consumption` then published the caller's original object.
    A ``str`` subclass whose character data spells
    :data:`BYTE_LEVEL_PROOF_PENDING` while its ``__str__``, ``__repr__`` and
    ``__format__`` spell :data:`BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN`
    therefore minted an approval that was safe only to ``json.dumps`` and
    asserted the byte-level claim to every other reader. B-3's rule — parse
    once, then check and publish the **same** objects — was broken inside the
    fix that exists to enforce it. This carries what was checked, and it is
    what gets published.
    """

    byte_level_status: str
    claim_withheld_because: str
    evidence_basis: str
    declared_not_measured: tuple[str, ...]
    files_opened: int
    bytes_measured: int
    inventory_digest: str

    def __post_init__(self) -> None:
        register_minted(self)


def _assert_disclosure_untampered(result: ProofResult) -> _PinnedDisclosure:
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

    **What it returns, and the one thing it cannot check (P-3).** It returns the
    pinned values, so the caller publishes what was checked rather than the
    caller's objects. ``inventory_digest`` is re-checked here too — it was
    repeated onto the approval untouched, so a record tampered to
    ``'NO_INVENTORY_EVER_EXISTED'`` put that on the approval as the inventory the
    proof was evaluated over. What the re-check establishes is its **shape** and
    its plain character data; substituting one well-formed 64-hex digest for
    another is not detectable from the record alone, exactly as for
    ``calendar_digest``. That limit is stated rather than papered over.
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
    basis = _pin_token(result.evidence_basis, what="evidence_basis")
    if basis != LIMB_EVALUATION_EVIDENCE_BASIS:
        raise ProofNotUsableError(
            f"the proof record declares evidence_basis {basis!r}; this layer "
            f"evaluates limbs over caller-supplied records and its basis is always "
            f"{LIMB_EVALUATION_EVIDENCE_BASIS!r}"
        )
    withheld = _pin_token(result.claim_withheld_because, what="claim_withheld_because")
    if withheld != BYTE_LEVEL_CLAIM_WITHHELD_REASON:
        raise ProofNotUsableError(
            f"the proof record declares claim_withheld_because {withheld!r}; the reason a "
            "byte-level claim is withheld is not a caller-settable field"
        )
    declared_not_measured = _pin_declared_not_measured(result.declared_not_measured)
    files_opened = _pin_disclosure_count(result.files_opened, what="files_opened")
    bytes_measured = _pin_disclosure_count(result.bytes_measured, what="bytes_measured")
    if (files_opened, bytes_measured) != (0, 0):
        raise ProofNotUsableError(
            f"the proof record declares files_opened={files_opened!r} and "
            f"bytes_measured={bytes_measured!r}; this layer opens no file and measures "
            "no byte, so a non-zero count means the record was rewritten"
        )
    try:
        inventory_digest = _require_hex_digest(result.inventory_digest, what="inventory_digest")
    except ProofContractError as exc:
        raise ProofNotUsableError(
            f"the proof record's inventory_digest is no longer a well-formed digest ({exc}); "
            "an approval repeats it as the inventory the proof was evaluated over"
        ) from exc
    return _PinnedDisclosure(
        byte_level_status=status,
        claim_withheld_because=withheld,
        evidence_basis=basis,
        declared_not_measured=declared_not_measured,
        files_opened=files_opened,
        bytes_measured=bytes_measured,
        inventory_digest=inventory_digest,
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
    # FB-5, and the single most emphasised rule of this contract: both tests
    # below are `in` against a `frozenset`, answered by the caller's own
    # `__hash__`/`__eq__`. A `str` subclass whose real character data is the
    # declaration-only token was handed straight back as an accepted byte-level
    # claim, which is D-11's promotion prohibition defeated by the argument.
    # Decide on the character data — and return the pinned value, not the
    # caller's object, so what the caller goes on to write is what was checked
    # (B-3 / P-3). For a plain `str` this is the same object.
    if not isinstance(token, str):
        raise ProofContractError(
            f"{token!r} is not a byte-level claim token in the closed vocabulary"
        )
    text = _pin_text(token, what="byte-level claim token", error=ProofContractError)
    if text in DECLARATION_ONLY_TOKENS:
        raise ProofPromotionError(
            f"{text!r} rests on caller-declared metadata "
            f"({TOKEN_EVIDENTIARY_BASIS[text]}) and can never be promoted to a "
            "byte-level claim"
        )
    if text not in BYTE_LEVEL_CLAIM_TOKENS:
        raise ProofContractError(
            f"{text!r} is not a byte-level claim token in the closed vocabulary"
        )
    return text


# `current_byte_level_proof_status()` used to live here and returned
# `BYTE_LEVEL_PROOF_PENDING` unconditionally. R-1 deletes a field that can only
# ever hold one value, and a nullary function returning a constant is the same
# thing behind parentheses — created by the very change that deleted eleven such
# attestations. It is gone rather than re-expressed: the pending status now
# reaches a caller only on a record that also states what was and was not
# measured to arrive at it, where it cannot be read as a standalone verdict.


def refuse_raw_source_rehash(subject: Any) -> None:
    """Refuse any request to hash raw source bytes (D-4.1, D-4.7, §12.11).

    FB-5: the dedicated D-4 guard **allowed** an object whose real character
    data was ``RAW_M1_SOURCE_BYTES``, because ``!=`` asked that object whether
    it should be refused, while the identical plain string was correctly
    refused. A non-``str`` is refused outright: the only admissible subject is
    one fixed string constant, so anything that merely *compares* equal to it is
    not it.
    """
    if isinstance(subject, str):
        subject = _pin_text(subject, what="hash subject", error=RawSourceRehashForbiddenError)
        admissible = subject == SUBJECT_DERIVED_M15_ARTIFACT
    else:
        admissible = False
    if not admissible:
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
    # FB-5 family: `in` against a tuple of committed spellings is decided by the
    # caller's own `__eq__`, so the name is read as character data first.
    name = (
        _pin_text(name, what="aggregate assertion name", error=AggregateAssertionUnsatisfiedError)
        if isinstance(name, str)
        else name
    )
    if name not in AGGREGATE_ASSERTIONS:
        raise AggregateAssertionUnsatisfiedError(
            f"{name!r} is not one of the committed aggregate assertions {AGGREGATE_ASSERTIONS}"
        )
    if not isinstance(per_pair, Mapping):
        raise AggregateAssertionUnsatisfiedError(
            f"aggregate assertion {name!r} needs a per-pair measurement mapping, got "
            f"{type(per_pair).__name__}; a declared count is not a measurement"
        )
    # The FB-5 family again, one level out: `pair not in snapshot` and
    # `snapshot[pair]` are answered by the KEY's `__hash__`/`__eq__`, so a
    # mapping keyed by objects whose real character data is
    # `PAIR_NEVER_MEASURED_0..19` satisfied D-8's "a measurement for every pair
    # in PAIRS_20". The name argument was pinned above and the keys were not.
    # Rebuild the mapping on pinned string keys before any lookup.
    snapshot: dict[str, Any] = {}
    for raw_key, raw_value in dict(per_pair).items():
        if not isinstance(raw_key, str):
            raise AggregateAssertionUnsatisfiedError(
                f"aggregate assertion {name!r} is keyed by a {type(raw_key).__name__}; "
                "a per-pair measurement mapping is keyed by pair names"
            )
        pinned_key = _pin_text(
            raw_key, what="per-pair key", error=AggregateAssertionUnsatisfiedError
        )
        if pinned_key in snapshot:
            raise AggregateAssertionUnsatisfiedError(
                f"aggregate assertion {name!r} names {pinned_key} twice; two keys that render "
                "differently but hold one pair's character data are one measurement, not two"
            )
        snapshot[pinned_key] = raw_value
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
    """Every admissible producer/verifier record for one role, keyed by pair.

    **FR-3 — this is where twenty forgeries were accepted.** ``object.__new__``
    bypasses ``__post_init__`` outright, so a ``MeasurementRecord`` carrying
    ``subject='RAW_M1_SOURCE_BYTES'``, ``size_bytes=-1``, a reversed span and
    ``dead_window_bars_by_bucket_start=7`` satisfied every ``isinstance`` here
    while no field check had ever run on it. :func:`_assert_minted` closes that
    route, and it is the only thing that can: no ``__new__`` override can
    intercept ``object.__new__``, so the difference between a record and a
    forgery is not visible on the object — only in the registry.

    **And the registry is not sufficient either.** ``object.__setattr__`` on a
    *genuine* record is this package's declared, unclosed threat model, and a
    record rewritten that way is still registered. So the two fields that decide
    a contract rule at this boundary — the D-4 subject and the producer/verifier
    role — are re-read here as plain character data, the same "re-check rather
    than inherit" the CV limb and the disclosure re-check already apply. Type,
    registration and re-check are three independent limbs; none of them is
    claimed to be the whole guard.
    """
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
        _assert_minted(item, what=f"{role} record {index}")
        _assert_not_refuted(item, what=f"{role} record {index}")
        # D-4 at the consumer boundary, on the character data: the dedicated
        # guard is called rather than the check being re-typed here, so the two
        # cannot drift apart.
        refuse_raw_source_rehash(item.subject)
        item_role = _pin_text(
            item.role, what=f"{role} record {index} role", error=ProofContractError
        )
        if item_role != role:
            raise ProofContractError(
                f"record {index} declares role {item_role!r} in the {role} record set"
            )
        item_pair = _pin_text(
            item.pair, what=f"{role} record {index} pair", error=ProofContractError
        )
        if item_pair in by_pair:
            raise ProofContractError(
                f"{role}: {item_pair} is measured twice; after canonicalisation each pair is "
                "measured exactly once"
            )
        by_pair[item_pair] = item

    # One pass over one byte stream measured one artifact, so two records citing
    # the same pass are describing the same file twice. Without this a single
    # fabricated `Provenance` served all twenty pairs (DI-5).
    passes: dict[tuple[str, int], str] = {}
    staged: dict[str, str] = {}
    for pair, item in by_pair.items():
        key = _pin_pass(item.digest_provenance, what=f"{role} {pair} digest")
        if key in passes:
            raise ProofCoMeasurementError(
                f"{role}: {pair} and {passes[key]} both cite byte-stream pass {key[0]!r} "
                f"#{key[1]}; one pass over one byte stream measures one artifact"
            )
        passes[key] = pair
        staged_id = _pin_text(
            item.staged_artifact_id,
            what=f"{role} {pair} staged_artifact_id",
            error=ProofContractError,
        )
        if staged_id in staged:
            raise ProofContractError(
                f"{role}: {pair} and {staged[staged_id]} were both hashed under "
                f"the staging name {staged_id!r}; twenty files means twenty "
                "staging identities"
            )
        staged[staged_id] = pair
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

    Any disagreement is fail-closed, and terminal for the two records it was
    pronounced over — see :class:`ProofDisagreementError` for exactly how far
    "terminal" reaches in a layer that holds no persistent state (FR-11). A
    **digest match with a scalar mismatch is the more alarming case**: identical
    bytes yielding different measured quantities means a derivation is wrong, not
    that a file moved, so it is reported separately rather than folded into a
    generic mismatch.

    **How far "independent" is checkable here** (:data:`VERIFIER_INDEPENDENCE_LIMIT`).
    The old test was ``producer.digest_provenance != verifier.digest_provenance``,
    a tuple comparison that a verifier citing a *different file at the same pass
    index* satisfied. It now takes two distinct byte-stream passes over the
    **same** named artifact — enforced by the two raises below, which is why the
    record states the *limit* rather than attesting that the passes were
    distinct (P-7). What no record can evidence is §11's real requirement — that
    the verifier does not share the producer's scalar-derivation code. That is a
    property of the P and V packages, which are a later gate; this layer states
    the limit rather than asserting ``INDEPENDENT_VERIFIER``.
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
    _assert_minted(producer, what="the producer measurement record")
    _assert_minted(verifier, what="the verifier measurement record")
    _assert_not_refuted(producer, what="the producer measurement record")
    _assert_not_refuted(verifier, what="the verifier measurement record")
    producer_role = _pin_text(producer.role, what="producer record role", error=ProofContractError)
    verifier_role = _pin_text(verifier.role, what="verifier record role", error=ProofContractError)
    if producer_role != ROLE_PRODUCER or verifier_role != ROLE_VERIFIER:
        raise ProofContractError(
            f"agreement needs one {ROLE_PRODUCER} and one {ROLE_VERIFIER} record, got "
            f"{producer_role!r} and {verifier_role!r}"
        )
    if producer.pair != verifier.pair:
        raise _refute(
            f"producer measured {producer.pair} while the verifier measured {verifier.pair}",
            producer,
            verifier,
        )
    producer_stream, _ = _pin_pass(producer.digest_provenance, what="producer digest")
    verifier_stream, _ = _pin_pass(verifier.digest_provenance, what="verifier digest")
    if producer_stream == verifier_stream:
        raise ProofContractError(
            f"{producer.pair}: the verifier cites the producer's own byte-stream pass; a "
            "verifier re-measures independently rather than replaying the producer's read"
        )
    producer_artifact = _pin_artifact_id(producer.digest_provenance, what="producer digest pass")
    verifier_artifact = _pin_artifact_id(verifier.digest_provenance, what="verifier digest pass")
    if producer_artifact != verifier_artifact:
        raise _refute(
            f"{producer.pair}: the verifier's pass names artifact "
            f"{verifier.digest_provenance.artifact_id!r} while the producer's names "
            f"{producer.digest_provenance.artifact_id!r}; an independent verifier re-reads the "
            "same artifact, not a different one",
            producer,
            verifier,
        )

    scalar_mismatches = [
        name for name in _AGREEING_FIELDS if getattr(producer, name) != getattr(verifier, name)
    ]
    if producer.sha256 == verifier.sha256:
        if scalar_mismatches:
            raise _refute(
                f"{producer.pair}: producer and verifier agree on the digest but disagree on "
                f"{scalar_mismatches}; identical bytes yielding different measurements means a "
                "derivation is wrong — terminal",
                producer,
                verifier,
            )
        return
    raise _refute(
        f"{producer.pair}: producer digest {producer.sha256} != verifier digest "
        f"{verifier.sha256}; the two reads did not see the same artifact — terminal",
        producer,
        verifier,
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
            raise _refute(
                f"TC limb: {pair} counts {record.dead_window_bars_by_bucket_start} dead-window "
                f"bar(s) by bucket start and {record.dead_window_bars_by_contributing_minute} by "
                "contributing source minute; the two definitions diverging means the bucketing "
                "is wrong — terminal",
                record,
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
    ``bars_scanned=50_000`` measurement. The certified slot count is bound to
    the scanned bar count here, and the binding is arithmetic rather than a
    threshold: each certified slot is one bar of the scanned artifact, with no
    duplicate (:class:`~scripts.m15_gate3a.coverage.CoverageSetMismatchError`)
    and no uncertifiable bar
    (:class:`~scripts.m15_gate3a.coverage.BarNotCertifiableError`).

    **FR-4 — the binding is by cardinality only, and the claim that it "makes
    the four limbs one proof rather than four unrelated checks" was too strong.
    It is retracted here rather than left standing.** Two evidence sets that
    agree on *how many* slots there are still satisfy this limb while describing
    different stretches of time: coverage certified for three slots on
    ``2025-05-01`` and a byte scan measured over
    ``2025-12-01T00:00…00:30`` are both three, and the conjunction holds. What
    the count binding actually excludes is a *cardinality* mismatch — the
    one-slot-beside-fifty-thousand-bars shape — and nothing more.

    Closing it needs the coverage evidence to publish the **measured span** of
    the slot set it certified.
    :class:`~scripts.m15_gate3a.coverage.PairCoverage` publishes only
    ``(pair, expected_slot_count, certified_slot_count)``, so span containment
    is **not checkable from what a CoverageResult exposes**, and no amount of
    work on this side of the boundary can derive it: this layer never sees the
    slot set. The required change is in
    :mod:`scripts.m15_gate3a.coverage` — ``PairCoverage`` carrying the minimum
    and maximum certified slot as measured UTC instants — after which the
    binding below extends to ``certified_slot_min == measured_ts_min`` and
    ``certified_slot_max == measured_ts_max``. Until then the limitation is
    stated, not papered over, and no count-based substitute is invented for it:
    D-5.8 is ruled with **no numeric floor**, and a span cannot be inferred from
    a count in any case.
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
    _assert_minted(coverage_result, what="the CV limb's CoverageResult")
    # A CoverageResult is minted only by `assert_full_coverage`, but a frozen
    # dataclass is not sealed — `object.__setattr__` rewrites `per_pair` on a
    # real one. The roster is re-checked here rather than inherited on trust.
    #
    # Set equality, and a duplicate is a defect rather than a longer roster: a
    # dict comprehension over `entry.pair` silently let a second entry for an
    # already-certified pair *replace* the first, so a 21st `PairCoverage` was
    # absorbed whenever it re-used a canonical name. Each pair is keyed on its
    # plain character data (FB-5 family: a two-faced `pair` would answer two
    # different keys) and may appear exactly once.
    covered: dict[str, PairCoverage] = {}
    for index, entry in enumerate(coverage_result.per_pair):
        if not isinstance(entry, PairCoverage):
            raise ProofLimbUnsatisfiedError(
                f"CV limb: coverage entry {index} is a {type(entry).__name__}, not a "
                "PairCoverage; the per-pair verdicts are what set equality was decided over"
            )
        entry_pair = _pin_text(
            entry.pair,
            what=f"CV limb: coverage entry {index} pair",
            error=ProofLimbUnsatisfiedError,
        )
        if entry_pair in covered:
            raise ProofLimbUnsatisfiedError(
                f"CV limb: coverage certifies {entry_pair} twice; each pair is certified exactly "
                "once, and a second entry would silently replace the first"
            )
        covered[entry_pair] = entry
    if sorted(covered) != sorted(PAIRS_20):
        raise ProofLimbUnsatisfiedError(
            f"CV limb: coverage was certified for {sorted(covered)}, which is not the canonical "
            "PAIRS_20 roster; the coverage token is the conjunction over all twenty"
        )
    for pair in PAIRS_20:
        entry = covered[pair]
        scanned = records[pair].bars_scanned
        try:
            certified_slot_count = pin_int(
                entry.certified_slot_count, what=f"CV limb: {pair} certified_slot_count"
            )
        except NumericAuthorityError as exc:
            raise ProofLimbUnsatisfiedError(
                f"CV limb: {pair} certified slot count is not a plain integer ({exc}); a count "
                "that answers a comparison for itself is not a measurement"
            ) from exc
        if certified_slot_count != scanned:
            raise ProofLimbUnsatisfiedError(
                f"CV limb: {pair} certifies {certified_slot_count} M15 slot(s) while the "
                f"full byte scan counted {scanned} bar(s); the coverage evidence and the scanned "
                "artifact are not describing the same file"
            )
        # FR-4: the count binding above says *how many*, never *which*. The audit
        # satisfied the whole four-limb conjunction with coverage certified for
        # 2025-05-01 beside a byte scan measured over 2025-12-01 — same
        # cardinality, different months. `PairCoverage` now publishes the span of
        # the set the equality limbs certified, so the two can be required to
        # describe the same stretch of time as well as the same number of bars.
        #
        # This is a comparison of two *measured* quantities, not a threshold: no
        # number is minted, and D-5.8's prohibition on count-shaped acceptance
        # criteria is untouched — indeed this is the binding a count could never
        # provide.
        record = records[pair]
        # Pinned, not compared raw. `PairCoverage` is publicly constructible and
        # performs no validation, and `object.__setattr__` on a genuine
        # `CoverageResult.per_pair` is this module's declared threat model — the
        # same reason `certified_slot_count` sixteen lines above goes through
        # `pin_int`. An audit answered both comparisons with a lying `datetime`
        # subclass and had a proof accept a certified span three years from the
        # one the byte scan measured.
        certified_min = _pin_instant(entry.certified_slot_min, what=f"{pair} certified_slot_min")
        certified_max = _pin_instant(entry.certified_slot_max, what=f"{pair} certified_slot_max")
        measured_min = _pin_instant(record.measured_ts_min, what=f"{pair} measured_ts_min")
        measured_max = _pin_instant(record.measured_ts_max, what=f"{pair} measured_ts_max")
        if certified_min != measured_min:
            raise ProofLimbUnsatisfiedError(
                f"CV limb: {pair} certifies slots from "
                f"{certified_min.isoformat()} while the full byte scan measured "
                f"from {measured_min.isoformat()}; equal bar counts over different "
                "spans are two unrelated measurements, not one proof"
            )
        if certified_max != measured_max:
            raise ProofLimbUnsatisfiedError(
                f"CV limb: {pair} certifies slots to "
                f"{certified_max.isoformat()} while the full byte scan measured "
                f"to {measured_max.isoformat()}; equal bar counts over different "
                "spans are two unrelated measurements, not one proof"
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
        _assert_minted(item, what=f"derivation binding {index}")
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
        verifier_independence_limit=VERIFIER_INDEPENDENCE_LIMIT,
        declared_not_measured=DECLARED_NOT_MEASURED_BY_THIS_LAYER,
        files_opened=0,
        bytes_measured=0,
        inventory_digest=_require_hex_digest(inventory_digest, what="inventory_digest"),
        calendar_digest=_require_content_digest(coverage.calendar_digest, what="calendar_digest"),
        # FB-6: an `_IdentityVault`, not a plain dict — `dataclasses.asdict` and
        # `astuple` recurse over dataclass fields and republished the whole map
        # with `open_for_consumption` never called.
        _identity=_IdentityVault(
            {
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
            }
        ),
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

    **FB-6 — that last sentence was false while the map was an ordinary
    ``dict`` under an underscore-prefixed field name.**
    :func:`dataclasses.asdict` and :func:`dataclasses.astuple` recurse over
    dataclass fields themselves and never consult ``__copy__``,
    ``__deepcopy__`` or ``__reduce__``, so one plain stdlib call — no hostile
    object, no private name — rebuilt all twenty identities with this function
    never called, and W3's "precondition of use" was enforced by nothing. The
    field now holds an :class:`_IdentityVault`, which both walkers reach only
    through :func:`copy.deepcopy` and which refuses it. What remains open, and
    is disclosed rather than claimed away, is direct access to the private
    attribute.

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

    **P-3 — and it publishes what it pinned.** The N-2 fix pinned each token for
    its *comparison* and then still built the approval out of ``result.<field>``,
    so a two-faced ``str`` subclass passed the check on its character data and
    reached the approval intact. Every disclosure field below now comes from
    :class:`_PinnedDisclosure`.

    The returned :class:`ConsumptionApproval` **authorises no read**. It repeats
    the pending status and states, in the value itself, that this layer opened no
    file and measured no byte.
    """
    if not isinstance(result, ProofResult):
        raise ProofNotUsableError(
            f"consumption requires an evaluated ProofResult, got {type(result).__name__}"
        )
    _assert_not_refuted(result, what="this proof result")
    try:
        disclosure = _assert_disclosure_untampered(result)
    except ProofContractError:
        raise
    except Exception as exc:
        # A result built by `object.__new__` has unset slots, so reading a
        # disclosure field off it raises `AttributeError` rather than this
        # module's documented type (the RF-29 class).
        raise ProofNotUsableError(
            f"the proof record's disclosure fields could not be read "
            f"({type(exc).__name__}: {exc}); a record whose fields were never assigned asserts "
            "an evaluation that never ran"
        ) from exc
    # FR-3, deliberately **after** the disclosure re-check: that check owns the
    # diagnosis of a field rewritten after construction and must speak first,
    # by name, about which field. What is left for the registry is the record
    # that was never constructed at all.
    _assert_minted(result, what="the ProofResult offered for consumption")
    if consumer_rechecks is None:
        raise ProofNotUsableError(
            "no consumer re-verification supplied; a proof that has not been re-verified "
            "immediately before use is not usable"
        )
    # `_refute` condemns the recheck it was pronounced over, and nothing read
    # that mark: an audit refuted a proof, then re-offered the very same recheck
    # objects to a freshly minted result and consumption succeeded. Either the
    # ledger entry means something or `_refute` should not be writing it — §11's
    # "the evidence a refutation was pronounced over is dead" says it means
    # something.
    if isinstance(consumer_rechecks, Mapping):
        for pair, recheck in dict(consumer_rechecks).items():
            _assert_not_refuted(recheck, what=f"the consumer re-verification for {pair}")
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
        _assert_minted(item, what=f"consumer re-verification {index}")
        if item.pair in by_pair:
            raise ProofNotUsableError(f"{item.pair} is re-verified twice")
        by_pair[item.pair] = item
    missing = [p for p in PAIRS_20 if p not in by_pair]
    if missing:
        raise ProofNotUsableError(
            f"no consumer re-verification for {missing}; every artifact is re-verified before "
            "any row of it is read"
        )
    # P-3, second half: the identity map was VERIFIED from one read of
    # `result._identity` and then PUBLISHED from three more reads of it per pair.
    # `_identity` is a plain dict as `evaluate_four_limbs` builds it, but so was
    # every other field before `object.__setattr__` — this package's declared
    # threat model — and a Mapping that answers differently on each read would
    # have published an identity nothing compared. Each identity is read once,
    # here, and that object is what the approval carries.
    verified: dict[str, _ArtifactIdentity] = {}
    for pair in PAIRS_20:
        recheck = by_pair[pair]
        identity = result._identity[pair]  # noqa: SLF001 - W3 is the accessor
        if not isinstance(identity, _ArtifactIdentity):
            raise ProofNotUsableError(
                f"{pair}: the proof's identity entry is a {type(identity).__name__}, not the "
                "record evaluate_four_limbs built; the proof was rewritten after construction"
            )
        _assert_minted(identity, what=f"{pair}: the proof's identity entry")
        verified[pair] = identity
        if recheck.artifact_id != identity.artifact_id:
            raise _refute(
                f"{pair}: consumer re-verified artifact {recheck.artifact_id!r} but the proof "
                f"was made about {identity.artifact_id!r}",
                result,
                recheck,
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
            raise _refute(
                f"{pair}: the artifact digest changed between the proof ({identity.sha256}) and "
                f"consumption ({recheck.sha256}) — terminal",
                result,
                recheck,
            )
        if recheck.size_bytes != identity.size_bytes:
            raise _refute(
                f"{pair}: the artifact byte size changed between the proof "
                f"({identity.size_bytes}) and consumption ({recheck.size_bytes}) — terminal",
                result,
                recheck,
            )
    # P-3: every disclosure field published here is the value
    # `_assert_disclosure_untampered` pinned and checked, never the object it was
    # handed. A `str` subclass cannot show one spelling to the check and another
    # to `str()`, `repr()` or an f-string on the approval.
    return ConsumptionApproval(
        byte_level_status=disclosure.byte_level_status,
        claim_withheld_because=disclosure.claim_withheld_because,
        evidence_basis=disclosure.evidence_basis,
        declared_not_measured=disclosure.declared_not_measured,
        files_opened=disclosure.files_opened,
        bytes_measured=disclosure.bytes_measured,
        inventory_digest=disclosure.inventory_digest,
        identity={
            pair: (
                verified[pair].artifact_id,
                verified[pair].sha256,
                verified[pair].size_bytes,
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
    "VERIFIER_INDEPENDENCE_LIMIT",
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
