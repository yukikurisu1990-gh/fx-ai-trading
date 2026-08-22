"""Metadata artifact validation + writing under a per-artifact **allowlist**.

Gate-3a/gate-5 metadata artifacts carry NO strategy metrics, predictions, model
outputs, trade-level rows or readiness claims. The previous design tried to
enforce that with a *denylist* of container shapes and literal label spellings,
and the third independent source-audit re-check (B-1) showed the denylist could
not hold: the same 300 records re-keyed as a dict-of-dicts scanned clean, a
claim embedded in a sentence scanned clean, and a Cyrillic or zero-width
homoglyph scanned clean — while the one construct governance expressly permits,
a prohibition list, was refused.

**What replaced it.** Each artifact this gate may write declares a schema: the
key vocabulary permitted anywhere in the payload, which of those keys may carry
a numeric leaf, which may carry a prohibition list, and the list/leaf/numeric
budgets implied by those declarations. A payload that resolves to a schema is
checked against it and everything outside it is refused, in **any** container
shape — re-keying cannot help, because the keys themselves must be declared.
A payload that resolves to no schema falls to a shape-agnostic backstop: the
inherited shape heuristics *plus* total numeric-leaf and total-leaf budgets that
a re-encoding cannot evade.

Claim detection is layered here rather than in :mod:`scripts.m15_gate3a.guards`:
that module's :func:`is_forbidden_status` is an exact whole-string predicate over
*labels*, which is the right contract for a label predicate and the wrong one for
a scrubber. This module folds NFKC, confusable (Cyrillic/Greek) homoglyphs,
combining marks and zero-width/format characters, then scans **substrings**, in
the manner :mod:`scripts.foundation_t2.scrub` already does in-repo.

**What the fourth re-check changed (FB-2, FB-3, FB-7, FB-9, FR-1/2/6/15/16/17/18).**
Four rounds were defeated by instance-specific patches, so each of these is a
family-level rule rather than another list entry:

* **One read, one snapshot (FB-2).** ``write_metadata_artifact`` used to validate
  the caller's object and then serialise it again; a ``dict`` subclass showing a
  clean face for the validating reads and the real payload on the ninth put
  ``PRODUCTION_READY``, ``sharpe_ratio`` and ``net_pnl`` on disk. Every entry
  point now takes :func:`snapshot_payload` first, and that snapshot is the single
  authority for validation, scanning, serialisation and the write. There is no
  check-then-reread anywhere on the write path, and the serialised text is
  produced exactly once (which also reconciles RF-11's internal ``serialise``).
* **A string leaf is a description, not a container (FB-3a).** 2 000 bid/ask rows
  ``json.dumps``'d into one leaf under a declared key scanned clean and wrote a
  328 KB artifact. Text is now bounded three independent ways — length, "does it
  parse as a non-empty JSON container", and how many numeric literals it carries
  — each bound derived from committed content.
* **A metric root is matched on the key's letters, not on its separators
  (FB-3b).** ``sharperatio`` / ``netpnl`` / ``maxdrawdown`` produced no token to
  match and ``PnL`` split into ``('pn','l')``.
* **A declared numeric key carries a value from its own domain (FB-3c).** Twenty
  pairs x eight price columns parked under eight *declared* numeric names scanned
  clean, because "declared numeric" said nothing about what a *count* may hold.
  A count-like key now refuses ``1.10001``, and ``pip_size`` must come from the
  pip authority's own value set.
* **§12.25 is implemented strictly (FB-9), as ruled by PR #448 §5.5.** Per-file
  records stay nested with at most five immediate numeric fields; **one** record
  with six refuses (the stricter of the two readings §5.5.4 leaves open), and a
  flattened ``gap_report`` refuses on its own limb. The rule is uniform across the
  declared and undeclared scans, so declaring a schema can no longer buy *less*
  shape scrutiny than declaring none — resolved by narrowing the schema, never by
  weakening the backstop (§5.5.6).
* **The fold is script-restricted, not a two-script denylist (FB-7).** A single
  Cherokee codepoint defeated **all 21** forbidden labels, and two table entries
  folded to the *wrong* Latin letter. A hand-maintained table cannot be completed
  by enumeration, so the structural rule is now: after folding, a letter that is
  still outside ASCII is itself a finding.
* **A prohibition list is a list of registered labels (FR-1, FR-16).** The
  exemption used to be inherited by an entire subtree, so
  ``{"forbidden_labels": {"result": "PASS"}}`` wrote. It now attaches to one list
  item at a time, and only when that item is *exactly* a registered label — which
  is also what makes the 40-character byte-level claim tokens listable without
  raising :data:`_MAX_PROHIBITION_ENTRY_LEN` by a single character.
* **A denial is not a claim, in the value direction too (FR-15).** The machinery
  could not write ``{"note": "NOT_PRODUCTION_READY"}``.
* **The gatekeeper returns (FR-17).** The base scrubber's
  ``[a-z0-9]+\\.r2\\.cloudflarestorage\\.com`` pattern is quadratic on a long
  alphanumeric run (16 000 chars -> 1.4 s; 306 KB did not finish in 110 s). The
  structural scan runs **first** and text it has already refused as unbounded is
  never handed to it.
* **Only the two functions actually used are imported (FR-18).** The module-level
  ``import evidence`` re-exported ``evidence.write_report`` into this namespace —
  a second writer that applies ``assert_clean`` only, calls no
  :func:`~scripts.m15_gate3a.guards.refuse_real_path` and overwrites
  unconditionally.

Two rules were added by the second-round audit:

* **N-3 — the byte-level claim vocabulary is unwritable.** The scan vocabulary
  is derived from ``FORBIDDEN_STATUSES`` *and*
  :data:`~scripts.m15_gate3a.guards.UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS`. Before
  that, a ``no_overlap_proof.json`` payload carrying ``"result":
  "BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN"`` and a
  ``MEASURED_FROM_DERIVED_ARTIFACT_BYTES__...`` source scanned clean and wrote,
  while the strictly weaker ``BYTE_ADMISSIBLE`` was refused.
* **§12.23 at the writer** — a timestamp rendered as ``...+00:00`` rather than
  the canonical ``...Z`` is a finding. Every producer in this package already
  goes through ``timeutil.format_utc_z``; the writer is where a payload that
  never called it is still catchable. See :func:`_scan_timestamp_spelling` for
  exactly how narrow the rule is.

**What this module actually guarantees (RF-15).** The previous docstring claimed
it "refuses to write under any protected real path". That was false and is not
restated. What is true:

* every write is preceded by :func:`scripts.m15_gate3a.guards.refuse_real_path`
  on both the output directory and the joined target, so a path naming or
  sitting under a tree in that module's protected set is refused — a set which
  deliberately does **not** contain ``artifacts/m15_gate3a`` (D-7);
* the writer **never overwrites**: an existing target is refused outright, which
  is what keeps the human-reviewed committed artifacts out of reach of a code
  path rather than a prefix list (D-7, §12.17);
* a refused write leaves nothing behind — no file, and no directory this call
  created (RF-9);
* nothing here reads a file. The module's only filesystem primitives are
  ``mkdir``, ``write_text`` and the existence/removal calls the refusal and
  clean-up paths need.

Containment of an *unrouted* caller is not a property this module has, and must
not be cited as one.

**Negative-control rule (R-1, §12.19).** This module mints no self-attestation.
It deliberately exposes no ``cleanliness_report``-style emitter: a ``clean``
flag beside a fixed ``checks`` list is exactly the one-valued field R-1 deletes
rather than reports. :func:`scan_gate3a` returns the findings themselves, and
both of its outcomes are reachable on every rule it implements.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

# FR-18: the two functions this module actually uses, imported by name. The
# previous `from scripts.ml_step4 import evidence` re-exported the whole module,
# and with it `evidence.write_report` — a SECOND writer reachable as
# `artifacts.evidence.write_report`, which applies `assert_clean` only, calls no
# `refuse_real_path`, and overwrites unconditionally. Importing the names means
# this module's namespace offers exactly one way to write.
from scripts.ml_step4.evidence import scan_payload as _base_scan_payload
from scripts.ml_step4.evidence import serialise as _serialise

from .guards import (
    FORBIDDEN_STATUSES,
    UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS,
    is_forbidden_status,
    refuse_real_path,
)
from .pair_authority import PAIRS_20, pip_size_for_pair


class ArtifactScrubError(RuntimeError):
    """Raised when a gate-3a metadata artifact would leak forbidden content."""


# ---------------------------------------------------------------------------
# Character folding — the input to every claim decision
# ---------------------------------------------------------------------------

# Confusables that render as a Latin letter but carry a different code point.
# NFKC folds the fullwidth and mathematical forms; it does **not** fold these,
# which is why `"PАSS"` (U+0410) scanned clean before. Only visually identical
# pairs are listed: a fold that is not visually justified would refuse honest
# text without closing anything.
#
# **FB-7 — this table is no longer load-bearing, and must not be treated as if it
# were.** A single-codepoint sweep over the Cherokee syllabary defeated **all 21**
# forbidden labels, and two entries folded to the WRONG letter (`"Ꭰ": "A"` is
# U+13A0 CHEROKEE LETTER A, which renders **D**; `"ᑭ": "C"` is U+146D, which
# renders **P**) — a mis-map is worse than an omission, because it guarantees the
# miss. Both are deleted. The reason the sweep worked at all is structural rather
# than a missing row: `_dense`/`_spaced` strip every character outside
# `[0-9A-Za-z]`, so an unlisted letter-like codepoint is **silently deleted** and
# the label closes up around the hole.
#
# A hand-maintained table cannot be completed by enumeration, and deriving a fold
# from Unicode *names* is exactly the mistake the two deleted rows made ("CHEROKEE
# LETTER A" is not an A). So the guarantee now rests on
# :func:`_scan_non_ascii_letters`: after NFKC/NFKD folding, any character that is
# still a **letter** and still outside ASCII is itself a finding. This table
# survives only so that a Cyrillic or Greek spelling of a label reports *which*
# label it spells, instead of the generic script finding.
_CONFUSABLES: Final[dict[str, str]] = {
    # Cyrillic capitals
    "А": "A",
    "В": "B",
    "Е": "E",
    "З": "3",
    "К": "K",
    "М": "M",
    "Н": "H",
    "О": "O",
    "Р": "P",
    "С": "C",
    "Т": "T",
    "У": "Y",
    "Х": "X",
    "Ѕ": "S",
    "І": "I",
    "Ј": "J",
    "Ү": "Y",
    "Ӏ": "I",
    "Ԛ": "Q",
    "Ԝ": "W",
    # Cyrillic smalls
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "у": "y",
    "х": "x",
    "ѕ": "s",
    "і": "i",
    "ј": "j",
    "ԛ": "q",
    "ԝ": "w",
    "м": "m",
    "н": "h",
    "т": "t",
    # Greek capitals
    "Α": "A",
    "Β": "B",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "H",
    "Ι": "I",
    "Κ": "K",
    "Μ": "M",
    "Ν": "N",
    "Ο": "O",
    "Ρ": "P",
    "Τ": "T",
    "Υ": "Y",
    "Χ": "X",
    # Greek smalls
    "α": "a",
    "ε": "e",
    "ι": "i",
    "κ": "k",
    "ν": "v",
    "ο": "o",
    "ρ": "p",
    "τ": "t",
    "χ": "x",
    "υ": "u",
    # Latin/other lookalikes not covered by NFKC
    "ı": "i",
    "ɡ": "g",
    "ǀ": "I",
    "Ⲓ": "I",
    "Ꮮ": "L",
    "ᴏ": "O",
}

# Categories carrying no glyph: format (zero-width space/joiner, soft hyphen,
# BOM, word joiner), control, and combining marks left over after NFKD. Each is
# invisible in a rendered artifact, so none may separate a claim from itself.
_INVISIBLE_CATEGORIES: Final[frozenset[str]] = frozenset({"Cf", "Cc", "Mn", "Me"})


def _pin(text: str) -> str:
    """Pin a ``str``'s character data, defeating a two-faced subclass.

    ``str(text)`` re-enters an overridden ``__str__``, so a subclass can show
    one string to a check and another to the consumer. The same technique is
    used by :func:`scripts.m15_gate3a.path_authority.resolve_candidate`.
    """
    return str.__str__(text)


def _fold(text: str) -> str:
    """NFKC + confusables + NFKD + invisible-character removal."""
    folded = unicodedata.normalize("NFKC", _pin(text))
    folded = "".join(_CONFUSABLES.get(ch, ch) for ch in folded)
    folded = unicodedata.normalize("NFKD", folded)
    return "".join(ch for ch in folded if unicodedata.category(ch) not in _INVISIBLE_CATEGORIES)


def _spaced(text: str) -> str:
    """Folded text with every non-alphanumeric run collapsed to one space.

    Case is **preserved**: a label written in its registered casing is a label,
    while the same letters in lower-case prose ("buckets that pass the
    cost-hurdle") are English. That distinction is what lets the scrubber refuse
    ``"PASS"`` without refusing the committed effective-N spec.
    """
    return " " + re.sub(r"[^0-9A-Za-z]+", " ", _fold(text)).strip() + " "


def _dense(text: str) -> str:
    """Folded text with every non-alphanumeric character removed, upper-cased."""
    return re.sub(r"[^0-9A-Za-z]+", "", _fold(text)).upper()


def _is_dense_kept(char: str) -> bool:
    """True for exactly the characters ``_dense`` and ``_spaced`` retain."""
    return char.isascii() and char.isalnum()


def _fold_hazards(text: str) -> list[tuple[str, str]]:
    """Non-ASCII codepoints that can launder a claim through the fold (FB-7).

    Two hazards, both derived from the fold's own mechanism rather than from a
    table of scripts:

    * **letter** — a character that is still a letter after NFKC + confusable
      folding + NFKD + invisible-character removal, and is still outside ASCII.
      The scrubber cannot prove such a character is not a homoglyph of a claim.

    * **join** — the mechanism the letter rule alone does *not* cover, and the
      one that defeated it. ``_dense`` and ``_spaced`` delete every character
      outside ``[0-9A-Za-z]``, so a non-ASCII codepoint that is **not** a letter
      does not merely fail to fold: it *vanishes*, and the label closes up around
      the hole exactly as an unlisted letter would. ``PR<U+07C0>DUCTION_READY``
      renders as the claim, denses to ``PRDUCTIONREADY``, and matched nothing.
      Restricting the letter rule to ``category().startswith("L")`` left every
      non-ASCII digit, symbol and mark — tens of thousands of codepoints — able
      to do this, and 19 of the 24 forbidden labels fell to one substitution.

      So the join rule targets the *deletion*, not the codepoint: take each
      maximal run of characters the dense fold deletes; if that run sits between
      two retained characters, and every character in it is non-ASCII, then the
      run is invisible as a separator to a human reader while being a separator
      to the scanner. Every character in it is reported.

    The "every character in the run is non-ASCII" condition is what keeps
    ordinary typography writable: in ``"1.5 -> higher"`` — or the same with a
    real arrow — the run between ``5`` and ``h`` contains ASCII spaces, so the
    reader sees the break the scanner sees and nothing is reported. It is only
    when the *whole* separator is invisible that the two disagree. Verified
    against all eight committed artifacts, which remain clean.
    """
    folded = _fold(text)
    hazards: dict[tuple[str, str], None] = {}
    index = 0
    length = len(folded)
    while index < length:
        if _is_dense_kept(folded[index]):
            index += 1
            continue
        run_start = index
        while index < length and not _is_dense_kept(folded[index]):
            index += 1
        run = folded[run_start:index]
        if run_start > 0 and index < length and all(not c.isascii() for c in run):
            for char in run:
                hazards[("join", char)] = None
    for char in folded:
        if not char.isascii() and unicodedata.category(char).startswith("L"):
            hazards[("letter", char)] = None
    return sorted(hazards)


# ---------------------------------------------------------------------------
# Forbidden claims
# ---------------------------------------------------------------------------

# Labels whose letters also spell ordinary English. A dense substring scan for
# these would refuse honest prose (the committed effective-N spec contains "pass
# the cost-hurdle"), so they are matched as **delimited tokens** — either in the
# label's registered upper-case spelling, or after a claim connector in any
# casing. Every other forbidden label is unique enough that a substring hit is a
# claim; new labels added to `FORBIDDEN_STATUSES` therefore default to the
# stricter treatment.
_AMBIGUOUS_CLAIM_KEYS: Final[frozenset[str]] = frozenset({"PASS", "MEETS", "ROBUST", "VALIDATED"})
# N-3: the byte-level claim vocabulary joins the substring scan. Each entry is a
# long, unique, registered spelling, so it belongs to the *unambiguous* class by
# the same rule as every other label here — a dense substring hit on
# `BYTELEVELNODEADWINDOWOVERLAPPROVEN` or `MEASUREDFROMDERIVEDARTIFACTBYTES` is a
# claim, never English. Listing the evidence-basis ROOT is what catches the two
# full basis sentences and any future `..._BYTES__<whatever>` variant of them.
_UNAMBIGUOUS_CLAIM_KEYS: Final[frozenset[str]] = (
    frozenset(_dense(s) for s in (FORBIDDEN_STATUSES | UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS))
    - _AMBIGUOUS_CLAIM_KEYS
)
# Words that turn an ambiguous token into an assertion about the subject.
_CLAIM_CONNECTORS: Final[str] = (
    "STATUS|RESULT|VERDICT|OUTCOME|CONCLUSION|READINESS|GRADE|ASSESSMENT|RATING|DECISION"
)
_AMBIGUOUS_PATTERNS: Final[tuple[tuple[str, re.Pattern[str], re.Pattern[str]], ...]] = tuple(
    (
        key,
        re.compile(rf"(?<![0-9A-Za-z]){key}(?![0-9A-Za-z])"),
        re.compile(
            rf"(?<![0-9A-Za-z])(?:{_CLAIM_CONNECTORS})\s+{key}(?![0-9A-Za-z])",
            re.IGNORECASE,
        ),
    )
    for key in sorted(_AMBIGUOUS_CLAIM_KEYS)
)

# A forbidden label used as a dict key is a *disclaimer* when its value denies
# it. RF-8: truthiness was the previous proxy, which refused
# `{"PRODUCTION_READY": "no"}` (a denial) and passed `{"PRODUCTION_READY": False}`
# only by accident of the same rule. Denial is now an explicit, closed
# vocabulary; anything else — including a number, a container, or `True` — is an
# assertion and is refused.
_NEGATION_VALUES: Final[frozenset[str]] = frozenset(
    {
        "FALSE",
        "NO",
        "NOT",
        "NONE",
        "NEVER",
        "NA",
        "NOTCLAIMED",
        "NOTASSERTED",
        "NOTAPPLICABLE",
        "NOTPERFORMED",
        "DENIED",
        "REFUSED",
        "FORBIDDEN",
        "PROHIBITED",
        "BLOCKED",
        "ABSENT",
    }
)
# Deliberately absent: "PENDING", "TBD" and their kin. Those defer a claim rather
# than denying it, and the stricter reading of a research restriction wins — a
# key naming a forbidden status is refused unless its value actually denies it.


def _is_denial(value: Any) -> bool:
    """True iff *value* explicitly denies the claim its key would otherwise make."""
    if value is False:
        return True
    return isinstance(value, str) and _dense(value) in _NEGATION_VALUES


# FR-15 — the mirror defect, one axis over from B-1's.
#
# `_is_denial` was consulted for dict KEYS only, so a *value* got no denial logic
# at all and the machinery could not write the denials its own governance
# vocabulary is made of: `{"note": "NOT_PRODUCTION_READY"}` reported
# `gate3a_forbidden_status_value:PRODUCTIONREADY`, and so did `"NOT_VALIDATED"`,
# `"no PASS is claimed"` and `"this gate is not production ready"`. The three
# always-binding statuses survived only by accident of spelling —
# `PRODUCTION_READINESS_NOT_CLAIMED` breaks the dense substring, and nothing was
# deciding that it was a denial.
#
# The rule is deliberately tight, because a denial exemption is a bypass if it is
# loose: an occurrence is denied only when a negator sits **immediately** before
# it — adjacent characters in the dense form, or the one preceding word in the
# spaced form. "is not really production ready" is therefore still refused, which
# is the fail-closed direction, and `"PRODUCTION_READY_NOT_PRODUCTION_READY"` is
# refused on its first, un-negated occurrence.
_NEGATORS: Final[tuple[str, ...]] = (
    "NOT",
    "NO",
    "NEVER",
    "NONE",
    "NEITHER",
    "WITHOUT",
    "DENIED",
    "DENIES",
    "REFUSED",
    "REFUSES",
    "PROHIBITED",
    "FORBIDDEN",
    "UNCLAIMED",
    "BLOCKED",
)


def _folded_projection(text: str, *, keep: str) -> tuple[str, list[int]]:
    """A fold projection plus, for each output character, its index in ``_fold``.

    ``keep="dense"`` reproduces :func:`_dense`; ``keep="spaced"`` reproduces
    :func:`_spaced`. The index list is what lets a match found in a projection be
    interrogated **in the folded text**, where token boundaries still exist. That
    is the whole point: a projection that has deleted every separator cannot be
    asked whether two things are one word, and FR-15's rule is a rule about words.
    """
    folded = _fold(text)
    chars: list[str] = []
    positions: list[int] = []
    pending: int | None = None
    for index, char in enumerate(folded):
        if _is_dense_kept(char):
            if pending is not None:
                chars.append(" ")
                positions.append(pending)
                pending = None
            chars.append(char.upper() if keep == "dense" else char)
            positions.append(index)
        elif keep == "spaced" and chars and pending is None:
            # A separator run is emitted as one space, and only once a further
            # retained character proves it separates rather than trails.
            pending = index
    if keep == "spaced":
        return " " + "".join(chars) + " ", [-1, *positions, len(folded)]
    return "".join(chars), positions


def _negated(folded: str, positions: list[int], start: int) -> bool:
    """True iff the **word** immediately before the claim is a negator (FR-15).

    The rule this replaces was ``dense[:start].endswith(negator)`` — a
    *character*-suffix test over a projection with no separators left in it. Any
    word merely ending in a negator's letters therefore disarmed the claim, and
    an internal audit wrote ``casino PRODUCTION_READY``, ``kimono
    BYTE_LEVEL_...``, ``whenever PRODUCTION_READY`` and
    ``UNBLOCKED_PRODUCTION_READY`` onto disk through the real writer with a clean
    scan. ``casino`` ends in ``NO``; ``UNBLOCKED`` ends in ``BLOCKED``.

    So the negator is read as a **token**, in the folded text where separators
    still exist: walk left from the claim over the separator run, then take the
    maximal alphanumeric run before it, and require *that whole word* to be a
    negator. A word that merely ends in one is not one. This is applied to both
    the dense and the spaced scan, so the two cannot disagree — previously only
    the spaced scan (the four ambiguous labels) had word semantics, which is why
    every *unambiguous* label was exposed and the four ambiguous ones were not.

    The gap between negator and claim is deliberately not constrained beyond
    "nothing else in between", because FR-15's own requirement is that honest
    denials stay writable: ``NOT_PRODUCTION_READY``, ``no PASS is claimed`` and
    ``this gate is not production ready`` are all denials and all write. The
    accepted residual is an author who puts a genuine negator word immediately
    before a claim without meaning a denial; that is a far narrower opening than
    "any word ending in these letters", and it cannot be reached by an ordinary
    English word the way the suffix rule could.
    """
    index = positions[start] - 1
    while index >= 0 and not _is_dense_kept(folded[index]):
        index -= 1
    end = index + 1
    while index >= 0 and _is_dense_kept(folded[index]):
        index -= 1
    return folded[index + 1 : end].upper() in _NEGATORS


def _claim_keys(text: str) -> list[str]:
    """Forbidden-claim labels asserted in *text*, by substring and by folding.

    "Asserted" rather than "present": an occurrence spelled as an atomic negated
    token is a **denial** and is not a finding (FR-15, see :func:`_negated`).
    """
    hits: list[str] = []
    folded = _fold(text)
    dense, dense_at = _folded_projection(text, keep="dense")
    for key in sorted(_UNAMBIGUOUS_CLAIM_KEYS):
        if not key:
            continue
        start = dense.find(key)
        while start != -1:
            if not _negated(folded, dense_at, start):
                hits.append(key)
                break
            start = dense.find(key, start + 1)
    spaced, spaced_at = _folded_projection(text, keep="spaced")
    for key, exact, connected in _AMBIGUOUS_PATTERNS:
        for pattern in (exact, connected):
            if any(
                not _negated(folded, spaced_at, m.end() - len(key))
                for m in pattern.finditer(spaced)
            ):
                hits.append(key)
                break
    # The whole-string fallback. It is the ONLY thing that catches a label spelled
    # out with separators between every letter — `"P A S S"`, `"M E E T S"`,
    # `"R O B U S T"`, `"V A L I D A T E D"` — because those produce no dense
    # substring and no delimited token; §14 recorded its removal as a surviving
    # mutant. `is_forbidden_status` is exact over the whole string, so a denial
    # spelling such as `NOT_PASS` folds to a key no forbidden label folds to and
    # never reaches here.
    if is_forbidden_status(_fold(text)) and not hits:
        hits.append(dense)
    return sorted(set(hits))


# ---------------------------------------------------------------------------
# Forbidden key vocabulary (RF-7)
# ---------------------------------------------------------------------------

# RF-7: the previous set was exact-match, so `sharpe_ratio`, `sharpeRatio`,
# `net_pnl`, `max_drawdown_pct`, `hit_rate`, `profit_factor`,
# `expectancy_per_trade` and `total_return` all passed. Matching is now over the
# key's **word tokens** (snake, kebab, camel and spaced spellings all split the
# same way), so a metric root cannot hide behind a qualifier.
_FORBIDDEN_KEY_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "sharpe",
        "sortino",
        "calmar",
        "expectancy",
        "pnl",
        "drawdown",
        "profit",
        "payoff",
        "equity",
        "backtest",
        "predictions",
        "prediction",
        "logits",
        "proba",
        "probability",
        "probabilities",
        "weights",
        "model",
        "trades",
        "return",
        "returns",
        # FB-3(b) named two further metric spellings the vocabulary had no entry
        # for at all — `MaxDD`, `ROI`, `informationratio`, `alpha`. That is a
        # vocabulary gap rather than a spelling gap, and this list is a
        # **backstop** for payloads that declare no schema: under a declared
        # schema any of them is already `gate3a_undeclared_key`. Added because a
        # named leak left open is worse than a list entry, not because the list
        # is what closes the family.
        "roi",
        "alpha",
    }
)
_FORBIDDEN_KEY_PHRASES: Final[tuple[tuple[str, ...], ...]] = (
    ("hit", "rate"),
    ("win", "rate"),
    ("validation", "metrics"),
    ("holdout", "metrics"),
    ("trade", "level"),
    ("trade", "rows"),
    ("model", "binary"),
    ("max", "dd"),
    ("information", "ratio"),
)


def _key_tokens(key: str) -> tuple[str, ...]:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", _fold(key))
    return tuple(t for t in re.split(r"[^0-9A-Za-z]+", text.lower()) if t)


# FB-3(b) — a metric root is a property of the key's LETTERS, not of the
# separators someone chose to type. RF-7 replaced exact matching with word-token
# matching, and the fourth re-check walked round it by simply removing the word
# boundaries: `{"sharperatio":1.93,"netpnl":128345.6,"maxdrawdown":3.21}` scanned
# clean and `metrics.json` was written. The same tokenizer also split the standard
# finance spelling `PnL` into `('pn','l')`, so `PnL` and `netPnL` were clean while
# `pnl` and `net_pnl` were caught.
#
# Matching is therefore ALSO done on the key's dense form, where separators do not
# exist. Every root and every phrase below is long and specific enough that a
# dense hit is a metric name: each was checked against the complete key
# vocabulary of all eight schemas and against every key in the eight committed
# artifacts, and the only hits are the committed scrub report's own
# `holdout_metrics_committed` / `model_binaries_committed` family — which carry
# `false` and are exempt as disclaimers under RF-8, exactly as they were before.
#
# Two tokens are matched as words only. `roi` is three letters and `alpha` is a
# common English prefix, so a *substring* hit on either would not be evidence
# that a key names a metric — and a check that fires on ordinary words is the
# mirror-image defect B-1 recorded. Both are still caught in every separator
# spelling by the word-token rule above, which is where they belong.
_TOKEN_ONLY_METRIC_ROOTS: Final[frozenset[str]] = frozenset({"roi", "alpha"})
_DENSE_FORBIDDEN_KEY_ROOTS: Final[tuple[str, ...]] = tuple(
    sorted(
        {
            token.upper()
            for token in _FORBIDDEN_KEY_TOKENS
            if len(token) >= 3 and token not in _TOKEN_ONLY_METRIC_ROOTS
        }
        | {"".join(phrase).upper() for phrase in _FORBIDDEN_KEY_PHRASES}
    )
)


def _forbidden_key_hit(key: str) -> str | None:
    tokens = _key_tokens(key)
    for token in tokens:
        if token in _FORBIDDEN_KEY_TOKENS:
            return token
    for phrase in _FORBIDDEN_KEY_PHRASES:
        span = len(phrase)
        for start in range(len(tokens) - span + 1):
            if tokens[start : start + span] == phrase:
                return "_".join(phrase)
    dense = _dense(key)
    for root in _DENSE_FORBIDDEN_KEY_ROOTS:
        if root in dense:
            return root.lower()
    return None


# ---------------------------------------------------------------------------
# Per-artifact schemas — the allowlist
# ---------------------------------------------------------------------------

# Container budgets are DERIVED from committed authority, never chosen:
#   * a list may not be longer than the frozen 20-pair universe — every list in
#     every committed artifact is shorter, and the roster is the largest
#     collection this gate legitimately describes;
#   * a prohibition list may name every forbidden label, so its bound is the
#     size of the guards' `FORBIDDEN_STATUSES` set and tracks it;
#   * per schema, numeric leaves are bounded by (roster size + 1) x the number of
#     keys that schema declares numeric, and total leaves by roster size x the
#     size of the schema's key vocabulary.
_MAX_LIST_ITEMS: Final[int] = len(PAIRS_20)
# The registered claim vocabulary — the complete set of labels a prohibition list
# may name, and therefore both the list's length bound and its membership test
# (FR-1, FR-16). `UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS` is included because
# `guards.py:61` says those tokens "may appear only in prohibition lists"; before
# this they could appear nowhere, since all three exceed
# `_MAX_PROHIBITION_ENTRY_LEN`.
_REGISTERED_CLAIM_LABELS: Final[frozenset[str]] = (
    FORBIDDEN_STATUSES | UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS
)
_MAX_PROHIBITION_ITEMS: Final[int] = len(_REGISTERED_CLAIM_LABELS)
# The per-key half of the schema numeric budget, made explicit rather than left
# implicit in the product below. A declared numeric key describes ONE quantity,
# so the most it can legitimately carry is one value per roster entry plus one
# aggregate — which is exactly the factor the schema budget was already derived
# from. The mutation workstream reproduced 340 float price values parked under
# the declared numeric key `pip_size` (chunked into 17 lists of 20, so neither
# the list bound nor the schema-wide budget of 357 fired) scanning with
# `findings=[]`. A declared key is a licence to hold *a* number, not a series.
_MAX_VALUES_PER_NUMERIC_KEY: Final[int] = _MAX_LIST_ITEMS + 1

# The committed `design_m15_inventory.json` `required_schema_per_file` block —
# the only per-file record shape this gate has committed authority for. Its key
# count and numeric-field count are what bound an *undeclared* payload, so the
# backstop invents no threshold of its own. Transcribed verbatim, including the
# confusable `eligible_event_count` (C-8): only the two *lengths* are consumed
# below, and re-spelling the transcription would silently move a derived bound
# while claiming to quote a committed artifact.
_COMMITTED_PER_FILE_KEYS: Final[tuple[str, ...]] = (
    "filename",
    "pair",
    "sha256",
    "size_bytes",
    "row_count",
    "eligible_event_count",
    "ts_min_utc",
    "ts_max_utc",
    "gap_report",
    "pip_size",
)
_COMMITTED_PER_FILE_NUMERIC_KEYS: Final[tuple[str, ...]] = (
    "size_bytes",
    "row_count",
    "eligible_event_count",
    "pip_size",
    "missing_minute_count",
    "max_gap_minutes",
)
_UNDECLARED_MAX_NUMERIC_LEAVES: Final[int] = _MAX_LIST_ITEMS * len(_COMMITTED_PER_FILE_NUMERIC_KEYS)
_UNDECLARED_MAX_LEAVES: Final[int] = _MAX_LIST_ITEMS * len(_COMMITTED_PER_FILE_KEYS)

# ---------------------------------------------------------------------------
# FB-3(a) — a string leaf is a DESCRIPTION, not a container
# ---------------------------------------------------------------------------
#
# The docstring used to claim "total numeric-leaf and total-leaf budgets that a
# re-encoding cannot evade". That was false: a serialised payload is ONE leaf,
# costs zero numeric budget, and is only claim- and timestamp-scanned. 2 000 full
# bid/ask OHLC rows `json.dumps`'d into a single string under a declared key
# scanned clean and wrote a 328 KB artifact; base64 and data-in-keys reached the
# same result.
#
# Three independent limbs bound text, because any one of them alone has an
# adjacent encoding that walks round it:
#
#   1. LENGTH — bounded by the longest string value any committed gate-3a
#      artifact actually carries. Transcribed verbatim below, for the same reason
#      `_COMMITTED_PER_FILE_KEYS` is: re-spelling the transcription would silently
#      move a derived bound while claiming to quote committed evidence. The bound
#      is `len()` of it, so it tracks the transcription and no number is invented.
#   2. STRUCTURE — text that parses as a non-empty JSON object or array is a
#      serialised container, not a description, whatever its length. This catches
#      the small dataset the length bound would admit.
#   3. NUMERIC DENSITY — a description may quote a few figures; a CSV or
#      space-separated dump quotes a series. The bound is
#      `_MAX_VALUES_PER_NUMERIC_KEY`, the same "one value per roster entry plus an
#      aggregate" factor a declared numeric key gets, so this invents nothing
#      either. The busiest committed string carries fifteen numeric runs, under
#      the bound of twenty-one.
#
# All three apply to KEYS as well as to string leaves, because data in keys is
# the third encoding FB-3(a) names. None of them is exempted inside a prohibition
# list: a prohibition-list entry is a label, and a registered label satisfies all
# three trivially.
_LONGEST_COMMITTED_STRING_VALUE: Final[str] = (
    "Producing the cost tables requires reading design-span raw candles and "
    "computing per-pair x session spread statistics via the M15 aggregation "
    "code, which does not exist yet (gate-5 code-only implementation "
    "deliverable). This gate is metadata-only and does not read raw data or run "
    "derivations, so Option A (produce tables now) is not admissible here. No "
    "ambiguity: the tables are produced by the implementation PR from "
    "DESIGN-span data only, human-approved before any gate-7 execution "
    "authorisation."
)
_MAX_TEXT_CHARS: Final[int] = len(_LONGEST_COMMITTED_STRING_VALUE)
# Digit runs, counted after the one construct that legitimately packs digits
# among letters — a hex digest — is removed. A bare `\d+` count scores 32 on a
# `0a0a0a...` sha256 and would refuse a legitimate committed digest, which is the
# mirror-image defect this redesign exists to avoid; but counting only
# *delimited* numbers would let a dataset back in glued to letters
# (`a1.10001a,a1.10002a`). Excising digests first lets the count stay greedy.
#
# The width is the committed one — `design_m15_inventory.json` declares `sha256`
# as "64-hex of the derived M15 file bytes" — so this excises a digest and not an
# arbitrary hex run.
_SHA256_HEX_WIDTH: Final[int] = 64
# EXACTLY the committed width, not `{64,}`. Open-ended was the defect: it excised
# every hex run of 64 characters or more, so the digit-density limb — one of the
# three the redesign calls independent — went blind to any hex payload up to the
# per-leaf character bound. An internal audit wrote 383 KB carrying 22 400
# exactly-recoverable float64 prices through a plain-JSON artifact with a clean
# scan, larger than the 328 KB artifact FB-3(a) reported as the original defect.
# A sha256 digest is 64 hex characters; a run of 65 is not a digest, and the
# committed artifacts confirm it (verified: every `sha256` value is width 64).
_HEX_DIGEST_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?<![0-9A-Za-z])[0-9a-fA-F]{{{_SHA256_HEX_WIDTH}}}(?![0-9A-Za-z])"
)
_DIGIT_RUN_RE: Final[re.Pattern[str]] = re.compile(r"\d+")

# ---------------------------------------------------------------------------
# FB-3(c) — a declared numeric key carries a value from its own domain
# ---------------------------------------------------------------------------
#
# "Declared numeric" said only *that* a number may sit there, never *which*
# numbers, so twenty pairs x eight float price columns re-keyed onto eight
# declared numeric names scanned clean and wrote: `absent_source_minute_count:
# 1.10001`, `complete_bucket_count: 1.10011`, and so on. The per-key bound of 21
# values bounds ONE key; `design_m15_inventory` declares sixteen.
#
# The binding is the key's own semantics, taken from the committed artifacts
# rather than chosen here: every numeric quantity in the eight committed
# artifacts is a non-negative integer except three, and those three are named in
# `fractional_keys` on the schema that declares them. A price cannot be a count.
# `pip_size` is bound harder still — to the value set the pip authority itself
# produces over the frozen roster, which is the only place a gate-3a pip size may
# come from (B-4).
_COMMITTED_PIP_SIZES: Final[frozenset[float]] = frozenset(
    pip_size_for_pair(pair) for pair in PAIRS_20
)

# ---------------------------------------------------------------------------
# §12.25 (S1, RULED by PR #448 §5.5) — the schema shape constraint
# ---------------------------------------------------------------------------
#
# Committed §12.25, verbatim: per-file records stay **nested** with **<=5
# immediate numeric fields**; six refuses, and flattening `gap_report` refuses.
# PR #445 implemented none of it for a payload that resolves to a schema, so
# declaring a schema bought strictly LESS shape scrutiny than declaring none
# (FB-9). PR #448 ruled S1 binding and S2 rejected, and settled the two
# sub-questions §5.5.4 left to the implementation:
#
#   * the §12.20-conformant record — four immediate numerics, `gap_report`
#     nested — is what must scan clean; `cost_hurdle_eligible_bar_count` and
#     `raw_traded_event_count` are pinned as *terms*, not per-file fields, so they
#     do not belong in the record absent a committed-schema diff (D-7);
#   * **one** six-numeric record refuses. The inherited heuristic needed two
#     row-like records, so `6 immediate numerics x 1 record` was clean; the
#     stricter reading is implemented here, as the ruling directs.
#
# The bound is §12.25's own number, and the rule runs in BOTH scans, so the
# inversion FB-9 named cannot recur. §5.5.6's tie-breaker is respected: the
# conflict is resolved by narrowing the schema — declared nested blocks are named
# explicitly below — never by weakening the undeclared backstop, which only got
# stricter.
_RECORD_MAX_IMMEDIATE_NUMERIC_FIELDS: Final[int] = 5


@dataclass(frozen=True)
class ArtifactSchema:
    """The permitted schema for one gate-3a artifact.

    ``allowed_keys`` is the complete key vocabulary: any key appearing at any
    depth must be in it. ``numeric_keys`` is the subset whose values may carry a
    numeric leaf, so a price series cannot be parked under a descriptive key.
    ``prohibition_list_keys`` are the keys under which a forbidden label is
    *named as prohibited* rather than asserted — the one usage playbook §10
    permits, and the construct the previous denylist refused.

    Being in ``numeric_keys`` licenses at most
    :data:`_MAX_VALUES_PER_NUMERIC_KEY` values for that key across the whole
    payload, not an array of arbitrary length: see
    :func:`_scan_declared`.

    ``fractional_keys`` are the declared numeric keys whose committed values are
    not integers; every other declared numeric key carries a non-negative integer
    (FB-3c). ``value_domains`` binds a declared numeric key to the closed value
    set a committed authority produces for it. ``nested_block_keys`` names the
    keys under which a *declared block* sits: a block may carry more immediate
    numeric fields than a record may (the D-3 minute accounting has exactly six),
    and the keys it owns may appear nowhere else — which is how "flattening
    ``gap_report`` refuses" is enforced as its own limb rather than as a
    side-effect of the count.
    """

    stem: str
    artifact_names: frozenset[str]
    allowed_keys: frozenset[str]
    numeric_keys: frozenset[str]
    prohibition_list_keys: frozenset[str] = frozenset()
    fractional_keys: frozenset[str] = frozenset()
    value_domains: tuple[tuple[str, frozenset[float]], ...] = ()
    nested_block_keys: frozenset[str] = frozenset()
    block_only_keys: frozenset[str] = frozenset()

    @property
    def filename(self) -> str:
        return f"{self.stem}.json"

    def value_domain(self, key: str) -> frozenset[float] | None:
        for declared, domain in self.value_domains:
            if declared == key:
                return domain
        return None

    @property
    def max_numeric_leaves(self) -> int:
        return _MAX_VALUES_PER_NUMERIC_KEY * len(self.numeric_keys)

    @property
    def max_leaves(self) -> int:
        return _MAX_LIST_ITEMS * len(self.allowed_keys)

    def list_bound(self, key: str | None) -> int:
        """The item bound for a list under *key*.

        FR-1: a prohibition list no longer reaches here — :func:`_scan_prohibition_list`
        owns it end to end, and applies :data:`_MAX_PROHIBITION_ITEMS` itself. A
        list *nested inside* one is an ordinary list and gets the ordinary bound,
        which is why the prohibition branch is gone rather than retained as an
        inheritance the nested container could pick up.
        """
        del key
        return _MAX_LIST_ITEMS


def _schema(
    stem: str,
    keys: tuple[str, ...],
    numeric: tuple[str, ...],
    *,
    artifact_names: tuple[str, ...] = (),
    prohibition_lists: tuple[str, ...] = (),
    fractional: tuple[str, ...] = (),
    value_domains: tuple[tuple[str, frozenset[float]], ...] = (),
    nested_blocks: tuple[str, ...] = (),
    block_only: tuple[str, ...] = (),
) -> ArtifactSchema:
    """Build a schema with every vocabulary folded to its comparison casing."""
    return ArtifactSchema(
        stem=stem,
        artifact_names=frozenset(n.lower() for n in (artifact_names or (stem,))),
        allowed_keys=frozenset(
            k.lower() for k in (*keys, *numeric, *prohibition_lists, *nested_blocks, *block_only)
        ),
        numeric_keys=frozenset(k.lower() for k in numeric),
        prohibition_list_keys=frozenset(k.lower() for k in prohibition_lists),
        fractional_keys=frozenset(k.lower() for k in fractional),
        value_domains=tuple((k.lower(), v) for k, v in value_domains),
        nested_block_keys=frozenset(k.lower() for k in nested_blocks),
        block_only_keys=frozenset(k.lower() for k in block_only),
    )


# Key vocabularies are the committed artifacts' own, extended only where a
# committed ruling names the extension: `design_m15_inventory` gains the
# populated-inventory record list, the six missing-minute quantities approved by
# the contract Gate-decision §5 (D-3), and the pinned-term renames required by
# §12.20 (R-2); `scrub_report` gains the prohibition-list vocabulary playbook
# §10 permits. Nothing else is invented here.
_SCHEMAS: Final[tuple[ArtifactSchema, ...]] = (
    _schema(
        "design_m15_derivation_manifest",
        (
            "aggregation_config_hash",
            "aggregation_contract",
            "aggregation_script_git_sha",
            "aggregation_script_path",
            "artifact",
            "bucket_convention",
            "byte_reproducible_from_source",
            "derivation_identity_required_at_implementation",
            "design_end_utc",
            "design_span_cut",
            "design_start_utc",
            "event_label_eligibility",
            "excludes_dead_window",
            "gate",
            "imputation",
            "incomplete_buckets",
            "input_identity",
            "metadata_only",
            "mid_price_construction_at_aggregation",
            "missing_minute_policy",
            "ohlc_rule",
            "personal_paths",
            "pip_size_authority",
            "purpose",
            "raw_candles_committed",
            "raw_rows_committed",
            "role",
            "scrub",
            "secrets",
            "source_checksum_authority",
            "source_epoch_id",
            "source_inventory_path",
            "source_pairs",
            "source_timeframe",
            "spread_field",
            "status",
            "synthetic_weekend_bars",
            "timezone",
            "value_pinned_tests_required_before_any_real_read",
        ),
        ("source_file_count",),
    ),
    _schema(
        "design_m15_inventory",
        (
            "all_ts_max_within_design_end",
            "all_ts_min_within_design_start",
            "artifact",
            # C-8 / §12.20 — `eligible_event_count` is admissible as a *key* and
            # NOT as a numeric one. The committed `design_m15_inventory.json`
            # uses it inside `required_schema_per_file` to *describe* a field
            # ("count of n_source_bars==15 buckets"), so removing it from the
            # vocabulary outright would make committed evidence — which D-7 says
            # is populated by human-reviewed PR diff and which this PR may not
            # edit — stop scanning clean. Leaving it in `numeric_keys` was the
            # worse failure the contract/specification audit named: the
            # scrubber would silently accept a continuation that *populated*
            # the confusable name, and confusing it with the effective-N spec's
            # traded-event quantity clears the frozen floors by orders of
            # magnitude and disarms `INSUFFICIENT_SAMPLE`. Declared here, the
            # committed descriptive usage stays clean while a populated
            # `eligible_event_count: 21500` is reported as
            # `gate3a_undeclared_numeric_field`. §12.20's pinned name
            # `complete_bucket_count` is the only spelling that may carry the
            # quantity; retiring the old key from the vocabulary lands with the
            # inventory schema extension at the continuation, in the same
            # human-reviewed diff that repopulates the artifact.
            "eligible_event_count",
            "filename",
            "files",
            "gate",
            "metadata_only",
            "pair",
            "raw_rows_committed",
            "reason_not_populated_now",
            "required_aggregate_assertions",
            "required_schema_per_file",
            "scrub",
            "sha256",
            "status",
            "ts_max_utc",
            "ts_min_utc",
        ),
        (
            "absent_source_minute_count",
            "complete_bucket_count",
            "cost_hurdle_eligible_bar_count",
            "dead_window_bars_present",
            "expected_source_minute_count",
            "file_count",
            "incomplete_bucket_count",
            "max_gap_minutes",
            "max_unavailable_gap_minutes",
            "missing_minute_count",
            "missing_whole_buckets",
            "n_buckets_emitted",
            "observed_source_minute_count",
            "pip_size",
            "raw_traded_event_count",
            "rejected_source_minute_count",
            "row_count",
            "rows_ingested",
            "size_bytes",
            "total_missing_source_minutes_within_emitted_buckets",
            "usable_source_minute_count",
        ),
        # FR-6 — the producer and the writer disagreed about this schema, and the
        # producer was the one telling the truth. The `gap_report` `aggregate_m15`
        # actually emits was unwritable here: six `gate3a_undeclared_key`
        # findings, including `minute_accounting`, the entire D-3 six-field block
        # coverage consumes. `_SCHEMAS` is code, not a committed artifact, so the
        # vocabulary is extended to the producer's real output; the committed
        # artifact's own two-key `gap_report` (FR-12) is a separate,
        # human-reviewed diff that this change does not pre-empt.
        #
        # Both blocks are declared NESTED (§12.25): a block may carry more
        # immediate numeric fields than a per-file record may, which is exactly
        # what nesting buys. `block_only` is the other half of the same clause —
        # these keys may appear under `gap_report` / `minute_accounting` and
        # nowhere else, so hoisting the accounting into the record refuses on its
        # own limb rather than only through the field count.
        nested_blocks=("gap_report", "minute_accounting"),
        block_only=(
            "absent_source_minute_count",
            "expected_source_minute_count",
            "incomplete_bucket_count",
            "max_gap_minutes",
            "max_unavailable_gap_minutes",
            "missing_minute_count",
            "missing_whole_buckets",
            "n_buckets_emitted",
            "observed_source_minute_count",
            "rejected_source_minute_count",
            "rows_ingested",
            "total_missing_source_minutes_within_emitted_buckets",
            "usable_source_minute_count",
        ),
        # FB-3(c): `pip_size` is the one non-integral quantity this schema
        # declares, and it may hold only what the pip authority itself produces
        # over the frozen roster. `1.10001` is neither.
        fractional=("pip_size",),
        value_domains=(("pip_size", _COMMITTED_PIP_SIZES),),
    ),
    _schema(
        "forward_epoch_adoption_manifest",
        (
            "adoption_for_research_only",
            "artifact",
            "as_of_utc",
            "committed_source_epoch_ts_max_utc",
            "earliest_data_complete_estimate_utc",
            "earliest_feasible_adoption_estimate_utc",
            "feasibility_finding",
            "forward_epoch_source",
            "forward_epoch_start_floor_utc",
            "forward_inventory_sha256",
            "frozen_requirement",
            "gate",
            "holdout_span_utc",
            "metadata_only",
            "no_overlap_proof",
            "note_committed_epoch",
            "personal_paths",
            "production_ready",
            "raw_rows_committed",
            "retention_binding",
            "scrub",
            "secrets",
            "status",
            "to_be_fixed_when_adopted_at_a_future_gate_3a_continuation",
            "validation_span_utc",
            "verdict",
        ),
        (
            "committed_forward_epoch_bars_in_repo",
            "elapsed_months_approx",
            "elapsed_since_forward_floor_as_of_2026_07_07_days_approx",
            "holdout_min_span_months",
            "purge_embargo_m15_bars",
            "total_min_forward_span_months_approx",
            "validation_min_span_months",
        ),
        # The committed manifest carries `elapsed_months_approx: 2.4`; every other
        # numeric quantity it declares is an integral count of bars, days or
        # months (FB-3c).
        fractional=("elapsed_months_approx",),
    ),
    _schema(
        "forward_epoch_inventory",
        (
            "artifact",
            "filename",
            "files",
            "gate",
            "metadata_only",
            "raw_rows_committed",
            "reason",
            "required_schema_when_populated",
            "role",
            "scrub",
            "sha256",
            "status",
            "ts_max_utc",
            "ts_min_utc",
        ),
        ("file_count", "size_bytes"),
    ),
    _schema(
        "no_overlap_proof",
        (
            "artifact",
            "assert",
            "boundary_constants_utc",
            # FR-6, the other direction: the honest-disclosure keys
            # `assert_per_file_bounds` emits — `evidence_basis`, `files_opened`,
            # `bytes_measured`, `declared_not_measured`, `certified_spans`, and
            # the roster report's own fields — were every one of them
            # `gate3a_undeclared_key` here, so the record B-2 made honest was the
            # record this writer refused. Dropping keys to fit would revert to the
            # pre-B-2 shape, which is the wrong half to change.
            "certified_spans",
            "committed_365d_ba_epoch_ts_max_utc",
            "committed_365d_ba_epoch_ts_min_utc",
            "consequence",
            "dead_window_end",
            "dead_window_start",
            "declared_not_measured",
            "design_end",
            "design_start",
            "evidence_basis",
            "expected_pairs",
            "filename",
            "forward_epoch_floor",
            "gate",
            "id",
            "lhs",
            "machine_checkable_assertions",
            "metadata_only",
            "overall",
            "pair",
            "policy",
            "raw_rows_committed",
            "requirement",
            "result",
            "rhs",
            "role",
            "schema_keys_not_verified",
            "scrub",
            "sha256",
            "source",
            "source_metadata_evidence",
            "t1_feature_warmup_leakage_addressed",
            "ts_max_utc",
            "ts_min_utc",
        ),
        ("bytes_measured", "expected_pair_count", "files_checked", "files_opened"),
    ),
    _schema(
        "effective_n_estimator_spec",
        (
            "artifact",
            "correlation_estimation_data",
            "cross_pair_discount",
            "daily_aggregation_dependence_note",
            "definitions",
            "failure_handling",
            "frozen_parameters",
            "gate",
            "granularity",
            "holdout",
            "horizon_overlap_factor",
            "metadata_only",
            "must_report_raw_and_effective",
            "no_strategy_metrics_computed_at_gate3a",
            "per_pair_effective",
            "per_role",
            "portfolio_effective",
            "purpose",
            "raw_event_count",
            "raw_rows_committed",
            "reporting",
            "scrub",
            "status",
            "trade_count_floor",
            "validation",
        ),
        ("H_m15_bars", "N_eff_holdout_floor", "raw_holdout_trade_floor"),
    ),
    _schema(
        "cost_table_plan_or_metadata",
        (
            "all_in_cost_formula",
            "artifact",
            "asia",
            "claim_scope",
            "data_source_restriction",
            "europe",
            "gate",
            "granularity",
            "median_quoted_spread",
            "metadata_only",
            "must_produce_before_gate7_authorisation",
            "no_raw_data_read_at_gate3a",
            "option_selected",
            "p90_session_spread",
            "p95_session_spread",
            "pip_conversion_policy",
            "rationale",
            "raw_rows_committed",
            "scrub",
            "sessions_utc",
            "statistics",
            "stress_forms",
            "us",
        ),
        ("execution_padding_pip", "flat_slippage_cell_pip"),
        artifact_names=("cost_table_plan", "cost_table_plan_or_metadata"),
        # The committed plan's two pip-unit constants (0.3, 0.5) are the only
        # non-integral quantities it declares (FB-3c).
        fractional=("execution_padding_pip", "flat_slippage_cell_pip"),
    ),
    _schema(
        "scrub_report",
        (
            "artifact",
            "assertions",
            "checked_artifacts",
            "content_kind",
            "credentials_or_secrets",
            "findings",
            "gate",
            "google_drive_or_r2_secrets",
            "holdout_metrics_committed",
            "metadata_only",
            "model_binaries_committed",
            "model_outputs_committed",
            "personal_or_local_paths",
            "predictions_committed",
            "raw_candles_committed",
            "raw_price_rows_committed",
            "result",
            "strategy_performance_metrics_committed",
            "trade_level_outputs_committed",
            "validation_metrics_committed",
        ),
        ("checked_artifact_count",),
        prohibition_lists=(
            "forbidden_labels",
            "prohibited_labels",
            "forbidden_statuses",
            "prohibited_statuses",
        ),
    ),
)

_SCHEMAS_BY_STEM: Final[dict[str, ArtifactSchema]] = {s.stem.lower(): s for s in _SCHEMAS}
_SCHEMAS_BY_ARTIFACT: Final[dict[str, ArtifactSchema]] = {
    name: s for s in _SCHEMAS for name in s.artifact_names
}
# The longest registered forbidden STATUS label. FR-16 recorded the trap this
# constant used to set: derived from `FORBIDDEN_STATUSES` alone it is 22, so the
# package could not list its own byte-level claim tokens
# (`BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN` is 40) in the one construct
# `guards.py:61` says they may appear in — and raising the number would have
# widened the window of text a prohibition entry may carry unscanned, which is
# not a fix.
#
# It is deliberately left at 22, and the permission is restored the other way:
# the exemption is now decided by **exact membership** of
# `_REGISTERED_CLAIM_LABELS`, so a 40-character registered token is admissible
# because it is a label, not because a bound was loosened. There is no longer any
# unscanned window at all — an entry that is not a registered label is claim-,
# timestamp- and text-scanned exactly like any other string, and this bound is
# what additionally stops a prohibition list becoming a prose dump.
_MAX_PROHIBITION_ENTRY_LEN: Final[int] = max(len(s) for s in FORBIDDEN_STATUSES)

# The gate-3a artifact filenames, derived from the schema table so the two
# cannot drift (the previous literal tuple had neither consumer nor test).
EXPECTED_ARTIFACT_FILES: Final[tuple[str, ...]] = tuple(s.filename for s in _SCHEMAS)


def artifact_schema(name: str) -> ArtifactSchema | None:
    """The declared schema for an artifact stem, filename or ``artifact`` value."""
    if not isinstance(name, str):
        return None
    key = _pin(name).strip().lower()
    if key.endswith(".json"):
        key = key[: -len(".json")]
    return _SCHEMAS_BY_STEM.get(key) or _SCHEMAS_BY_ARTIFACT.get(key)


# ---------------------------------------------------------------------------
# Shared leaf checks
# ---------------------------------------------------------------------------


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# §12.23 — an ISO date-time carrying an explicit NUMERIC UTC offset instead of
# the canonical `Z`. `datetime.isoformat()` renders exactly this. Both ISO
# decimal separators are admitted in the fraction and both offset spellings
# (`+00:00`, `+0000`) are matched, since either would be an isoformat-family
# rendering; `Z` is the canonical form and is not matched.
_ISO_OFFSET_TIMESTAMP_RE: Final[re.Pattern[str]] = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:[.,]\d+)?[+-]\d{2}:?\d{2}"
)


def _non_finite(value: Any) -> bool:
    """D6 / RF-10: ``json.dumps`` emits the non-standard ``NaN`` / ``Infinity``.

    RF-10: this inspected values only, so a non-finite **key** was unscanned and
    silently stringified to ``"NaN"`` by ``json.dumps``. Keys are now checked on
    the same predicate.
    """
    return isinstance(value, float) and not math.isfinite(value)


def _scan_key_claims(key: Any, value: Any, findings: list[str]) -> None:
    """Claim / metric checks for a dict key, with the RF-8 disclaimer exemption."""
    if not isinstance(key, str):
        return
    for kind, char in _fold_hazards(key):
        findings.append(f"gate3a_non_ascii_{kind}_in_key:{key}:{ord(char):04X}")
    denial = _is_denial(value)
    hits = _claim_keys(key)
    if hits and not denial:
        findings.append(f"gate3a_forbidden_status_key:{key}")
    metric = _forbidden_key_hit(key)
    if metric is not None and not denial:
        findings.append(f"gate3a_forbidden_key:{key}")


def _scan_value_claims(value: Any, findings: list[str], *, exempt: bool) -> None:
    if not isinstance(value, str) or exempt:
        return
    for hit in _claim_keys(value):
        findings.append(f"gate3a_forbidden_status_value:{hit}")


def _scan_timestamp_spelling(text: Any, findings: list[str], key_label: str | None) -> None:
    """§12.23 at the writer: refuse a timestamp rendered with a numeric offset.

    :func:`scripts.m15_gate3a.timeutil.format_utc_z` is the single emission
    authority and renders ``YYYY-MM-DDTHH:MM:SSZ``. §12.23 says the
    ``datetime.isoformat()`` spelling — which yields ``+00:00`` — "must not reach
    **any artifact**", and every *producer* in this package obeys that. Nothing
    enforced it at the **writer**, which is the chokepoint where a payload
    assembled by a caller that never called the formatter is still catchable: a
    ``{"ts_min_utc": "2025-06-02T00:00:00+00:00"}`` payload scanned with
    ``findings == []`` and wrote.

    Deliberately narrow. This is a **spelling** check on values that already look
    like timestamps, not a schema requirement that any key must carry one: only a
    complete ``YYYY-MM-DDTHH:MM`` followed by an explicit numeric offset is a
    finding. A bare date (``"2026-07-07"``), a date inside prose, and the
    committed nine-zero-digit form ``"2025-04-24T22:03:00.000000000Z"`` — which
    §12.23 expressly accepts, since all-zero excess carries no information — are
    untouched. It is applied to keys as well as values, and is **not** exempted
    inside a prohibition list, because a prohibition list has no occasion to
    carry a timestamp at all.
    """
    if not isinstance(text, str):
        return
    for match in _ISO_OFFSET_TIMESTAMP_RE.finditer(_pin(text)):
        findings.append(f"gate3a_non_canonical_timestamp:{key_label}:{match.group(0)}")


# FR-2 — a live-format credential in a string VALUE, under a permitted key.
#
# The base scrubber detects credentials by dict-KEY name plus two value patterns
# (a presigned URL and `Bearer <token>`), so `{"note": "OANDA_API_KEY=1a2b..."}`
# and `{"rationale": "api_key=sk-live-..."}` both scanned clean and the write
# succeeded. `scripts/foundation_t2/constants.py` is not this workstream's file,
# so the value side is implemented here.
#
# The rule is an ASSIGNMENT rule, not a keyword rule: a credential-named
# identifier, an `=`, and a long opaque run. That is what distinguishes a secret
# from the many honest sentences in the committed artifacts that contain the word
# "secret" or "token" — `"secrets": "NONE_COMMITTED"` names a credential and
# assigns nothing, and stays clean. `:` is deliberately NOT accepted as the
# separator; prose uses it constantly.
_CREDENTIAL_ROOTS: Final[tuple[str, ...]] = (
    "APIKEY",
    "ACCESSKEY",
    "SECRETKEY",
    "PRIVATEKEY",
    "SESSIONTOKEN",
    "AUTHTOKEN",
    "ACCESSTOKEN",
    "TOKEN",
    "PASSWORD",
    "PASSPHRASE",
    "CREDENTIAL",
    "APISECRET",
    "CLIENTSECRET",
)
# `16` here is a **detection heuristic** on the opaque part of an assignment, not
# a research threshold of any kind: it is what separates `api_key=none` (a
# disclaimer, and the shape the committed artifacts actually use) from a key.
# Nothing downstream reads it, and no gate decision turns on it. The identifier
# quantifier is a bound on the regex's work, not a semantic limit.
_MIN_OPAQUE_SECRET_CHARS: Final[int] = 16
_ASSIGNMENT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![0-9A-Za-z_])([A-Za-z][A-Za-z0-9_.\-]{0,63})\s*=\s*"
    rf"([A-Za-z0-9_\-.~+/]{{{_MIN_OPAQUE_SECRET_CHARS},}})"
)
# Vendor key formats that identify themselves, independent of any assignment.
_SECRET_LITERAL_RES: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    (
        "openai_style_live_key",
        re.compile(rf"\bsk-(?:live|test|proj)?-?[A-Za-z0-9]{{{_MIN_OPAQUE_SECRET_CHARS},}}"),
    ),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
)


def _scan_credential_values(text: Any, findings: list[str], key_label: str | None) -> None:
    """FR-2: refuse a credential VALUE, wherever it sits and whatever names it."""
    if not isinstance(text, str):
        return
    pinned = _pin(text)
    for match in _ASSIGNMENT_RE.finditer(pinned):
        identifier = _dense(match.group(1))
        if any(root in identifier for root in _CREDENTIAL_ROOTS):
            findings.append(f"gate3a_credential_value:{key_label}:{match.group(1)}")
    for label, pattern in _SECRET_LITERAL_RES:
        if pattern.search(pinned):
            findings.append(f"gate3a_credential_value:{key_label}:{label}")


def _scan_text_bounds(text: Any, findings: list[str], key_label: str | None) -> None:
    """FB-3(a): text is a description — bounded in length, structure and density.

    Applied to keys and to string leaves alike, in both the declared and the
    undeclared scan, and never exempted: the three limbs are what stop a dataset
    from being re-typed into one leaf that costs one leaf and zero numeric budget.
    """
    if not isinstance(text, str):
        return
    pinned = _pin(text)
    if len(pinned) > _MAX_TEXT_CHARS:
        findings.append(f"gate3a_oversize_text:{key_label}:{len(pinned)}")
    stripped = pinned.strip()
    if stripped[:1] in ("{", "["):
        try:
            parsed = json.loads(stripped)
        except (ValueError, RecursionError):
            parsed = None
        if isinstance(parsed, (dict, list)) and len(parsed) > 0:
            findings.append(f"gate3a_serialised_container_in_text:{key_label}")
    runs = len(_DIGIT_RUN_RE.findall(_HEX_DIGEST_RE.sub(" ", pinned)))
    if runs > _MAX_VALUES_PER_NUMERIC_KEY:
        findings.append(f"gate3a_numeric_series_in_text:{key_label}:{runs}")
    for kind, char in _fold_hazards(pinned):
        findings.append(f"gate3a_non_ascii_{kind}:{key_label}:{ord(char):04X}")


# ---------------------------------------------------------------------------
# Declared scan — the allowlist proper
# ---------------------------------------------------------------------------


@dataclass
class _Counters:
    numeric: int = 0
    leaves: int = 0
    #: numeric leaves seen per *declared numeric* key, for the per-key bound.
    per_numeric_key: dict[str, int] = field(default_factory=dict)


def _immediate_numeric_fields(obj: dict) -> int:
    """Numeric fields of *obj* itself, not of anything nested inside it."""
    return sum(1 for value in obj.values() if _is_numeric(value))


def _scan_record_shape(
    obj: dict, findings: list[str], key_label: str | None, *, is_declared_block: bool
) -> None:
    """§12.25 (S1): a record stays nested with at most five immediate numerics.

    Applied to **every** dict, in both scans, and to a single record as well as
    to a collection of them — PR #448 §5.5.4 directs the stricter of the two
    readings, and §5.5.6 forbids resolving the resulting tension by weakening the
    undeclared backstop. The one exemption is a dict sitting under a key the
    schema declares a *nested block*: nesting is what §12.25 prescribes, and the
    D-3 minute accounting the contract mandates has exactly six fields. That
    exemption is a narrowing of the schema, not a widening of the clause — a
    block's keys must still be declared, and they may appear nowhere else.
    """
    if is_declared_block:
        return
    count = _immediate_numeric_fields(obj)
    if count > _RECORD_MAX_IMMEDIATE_NUMERIC_FIELDS:
        findings.append(f"gate3a_record_immediate_numeric_fields:{key_label}:{count}")


def _scan_declared(
    obj: Any,
    schema: ArtifactSchema,
    findings: list[str],
    counters: _Counters,
    *,
    numeric_allowed: bool,
    exempt: bool,
    key_label: str | None,
) -> None:
    if isinstance(obj, dict):
        _scan_record_shape(
            obj,
            findings,
            key_label,
            is_declared_block=key_label is not None and key_label in schema.nested_block_keys,
        )
        for key, value in obj.items():
            if not isinstance(key, str):
                findings.append(f"gate3a_non_string_key:{key!r}")
                if _non_finite(key):
                    findings.append("gate3a_non_finite_key")
                # F2-3: report the key AND scan what sits under it. The previous
                # `continue` did neither: 30 x 8 numeric price rows under a
                # single `int` key reported `gate3a_non_string_key:0` and the
                # entire subtree beneath it was never examined, so one
                # unrenderable key exempted a whole dataset. A non-string key
                # declares nothing, so nothing below it may carry a numeric
                # leaf, and the label it passes down must not be the *parent's*
                # — `{"pip_size": {0: [...]}}` would then report a violation
                # against `pip_size`, a key that really is declared numeric.
                _scan_declared(
                    value,
                    schema,
                    findings,
                    counters,
                    numeric_allowed=False,
                    exempt=exempt,
                    key_label=f"non_string_key({key!r})",
                )
                continue
            pinned = _pin(key)
            folded = pinned.strip().lower()
            if folded not in schema.allowed_keys:
                findings.append(f"gate3a_undeclared_key:{pinned}")
            # §12.25's flattening limb, as its own finding. A key the schema
            # declares to live inside `gap_report` / `minute_accounting` may
            # appear only there, so hoisting the D-3 accounting into the per-file
            # record refuses on this limb whatever the field count happens to be.
            if folded in schema.block_only_keys and (
                key_label is None or key_label not in schema.nested_block_keys
            ):
                findings.append(f"gate3a_nested_block_key_flattened:{pinned}")
            _scan_key_claims(pinned, value, findings)
            _scan_timestamp_spelling(pinned, findings, key_label)
            _scan_text_bounds(pinned, findings, f"key({pinned[:40]})")
            _scan_credential_values(pinned, findings, f"key({pinned[:40]})")
            if folded in schema.prohibition_list_keys:
                _scan_prohibition_list(value, schema, findings, counters, key_label=folded)
                continue
            _scan_declared(
                value,
                schema,
                findings,
                counters,
                numeric_allowed=folded in schema.numeric_keys,
                exempt=exempt,
                key_label=folded,
            )
        return
    if isinstance(obj, (list, tuple)):
        bound = schema.list_bound(key_label)
        if len(obj) > bound:
            findings.append(f"gate3a_list_longer_than_declared:{key_label}")
        for item in obj:
            _scan_declared(
                item,
                schema,
                findings,
                counters,
                numeric_allowed=numeric_allowed,
                exempt=exempt,
                key_label=key_label,
            )
        return
    counters.leaves += 1
    if counters.leaves > schema.max_leaves:
        findings.append("gate3a_leaf_cardinality_exceeded")
    if _non_finite(obj):
        findings.append(f"gate3a_non_finite_value:{key_label}")
    if _is_numeric(obj):
        counters.numeric += 1
        if counters.numeric > schema.max_numeric_leaves:
            findings.append("gate3a_numeric_cardinality_exceeded")
        if not numeric_allowed:
            findings.append(f"gate3a_undeclared_numeric_field:{key_label}")
        elif key_label is not None:
            # F2-2: a declared numeric key may hold a value per roster entry
            # plus an aggregate — the very factor `max_numeric_leaves` is
            # derived from — and not a series. Without this, 340 prices chunked
            # into 17 lists of 20 sat under `pip_size` with `findings=[]`:
            # every chunk was within the list bound and the total was under the
            # schema-wide budget, which is a budget for ALL numeric keys
            # together.
            seen = counters.per_numeric_key.get(key_label, 0) + 1
            counters.per_numeric_key[key_label] = seen
            if seen > _MAX_VALUES_PER_NUMERIC_KEY:
                findings.append(f"gate3a_numeric_series_under_declared_key:{key_label}")
            _scan_numeric_domain(obj, schema, findings, key_label)
    elif isinstance(obj, str):
        _scan_value_claims(obj, findings, exempt=exempt)
        _scan_timestamp_spelling(obj, findings, key_label)
        _scan_text_bounds(obj, findings, key_label)
        _scan_credential_values(obj, findings, key_label)
    elif obj is not None and not isinstance(obj, bool):
        findings.append(f"gate3a_undeclared_value_type:{type(obj).__name__}")


def _scan_numeric_domain(value: Any, schema: ArtifactSchema, findings: list[str], key: str) -> None:
    """FB-3(c): a declared numeric key carries a value from its own domain.

    "Declared numeric" said only *that* a number may sit there. Twenty pairs x
    eight float price columns re-keyed onto eight declared numeric names of
    `design_m15_inventory` therefore scanned clean and wrote an 8.7 KB artifact
    whose first record read `absent_source_minute_count: 1.10001`. Neither the
    per-key bound (which bounds ONE key) nor the schema-wide budget (which bounds
    sixteen keys together) can see that a *count* is holding a *price*.

    Two bindings, both taken from committed authority rather than chosen:

    * every numeric quantity in the eight committed artifacts is a non-negative
      integer except the three named in ``fractional_keys``, so any other declared
      numeric key refuses a fractional or negative value — and, as a side effect
      that §14 asked for, refuses ``NaN`` and ``Infinity`` a second time, since
      neither is integral;
    * ``pip_size`` may hold only what the pip authority produces over the frozen
      roster (B-4 makes that the single pip authority for this gate).
    """
    domain = schema.value_domain(key)
    if domain is not None and value not in domain:
        findings.append(f"gate3a_value_outside_committed_domain:{key}")
    if key in schema.fractional_keys:
        return
    # `int(value)`, not `float(value)`: the value already came through
    # `snapshot_payload`, so it is a plain `int`/`float`, and this module does not
    # re-enter a caller's `__float__` after the N-1 / R-1 history of exactly that
    # mistake. `math.isfinite` is checked first because `int(inf)` raises.
    if not math.isfinite(value) or int(value) != value or value < 0:
        findings.append(f"gate3a_non_integral_value_under_count_key:{key}")


def _scan_prohibition_list(
    value: Any,
    schema: ArtifactSchema,
    findings: list[str],
    counters: _Counters,
    *,
    key_label: str,
) -> None:
    """FR-1 / FR-16: the §10 exemption reaches a registered label, nothing else.

    The exemption used to be a flag inherited by the **whole subtree** under a
    prohibition key, unbounded by shape, so ``{"forbidden_labels": {"result":
    "PASS", "content_kind": "PRODUCTION_READY"}}`` scanned clean and was written
    to disk — a dict is not a prohibition list — and a 22-character claim
    sentence inside the list (``"GATE 3A RESULT IS PASS"``) scanned clean because
    the only thing standing between the exemption and arbitrary text was a length
    bound.

    It is now decided one item at a time, by **exact membership** of the
    registered claim vocabulary:

    * the value must be a list or tuple; anything else is reported and then
      scanned with no exemption at all;
    * an item that is exactly a registered label is exempt from claim scanning —
      which is what makes the 40-character byte-level tokens listable (FR-16)
      without touching :data:`_MAX_PROHIBITION_ENTRY_LEN`;
    * any other item — including a nested container — is scanned exactly as it
      would be anywhere else, so there is no unscanned window left to exploit;
    * a label may be named once. Naming it twice is not a longer prohibition, and
      distinctness is what keeps :data:`_MAX_PROHIBITION_ITEMS` a tight bound
      rather than a number a mutation can raise unnoticed (§14).
    """
    if not isinstance(value, (list, tuple)):
        findings.append(f"gate3a_prohibition_list_not_a_list:{key_label}")
        _scan_declared(
            value,
            schema,
            findings,
            counters,
            numeric_allowed=False,
            exempt=False,
            key_label=key_label,
        )
        return
    if len(value) > _MAX_PROHIBITION_ITEMS:
        findings.append(f"gate3a_list_longer_than_declared:{key_label}")
    seen: set[str] = set()
    for item in value:
        registered = isinstance(item, str) and _pin(item) in _REGISTERED_CLAIM_LABELS
        if registered:
            pinned = _pin(item)
            if pinned in seen:
                findings.append(f"gate3a_prohibition_entry_duplicated:{key_label}")
            seen.add(pinned)
        elif isinstance(item, str) and len(_pin(item)) > _MAX_PROHIBITION_ENTRY_LEN:
            findings.append(f"gate3a_prohibition_entry_too_long:{key_label}")
        _scan_declared(
            item,
            schema,
            findings,
            counters,
            numeric_allowed=False,
            exempt=registered,
            key_label=key_label,
        )


# ---------------------------------------------------------------------------
# Undeclared backstop — shape-agnostic, plus the inherited shape heuristics
# ---------------------------------------------------------------------------

# Inherited O-2 / R-5 heuristics. They are a denylist and are kept only as a
# backstop for payloads that declare no schema: >= 2 dicts each carrying >= 6
# numeric (non-bool) immediate values (a full BA row has 8 numeric sides), and
# >= 2 numeric arrays of length >= 4 (the columnar encoding of the same rows).
# Both counts are taken over a container's members whether that container is a
# `list`/`tuple` or a `dict` — counting them in lists alone was itself the
# re-keying route (F2-2). B-1 showed shape heuristics can be re-keyed around at
# all, which is why the cardinality budgets below run alongside them and count
# leaves rather than shapes.
_ROW_LIKE_MIN_RECORDS: Final[int] = 2
_ROW_LIKE_MIN_NUMERIC_FIELDS: Final[int] = 6
_COLUMNAR_MIN_SERIES: Final[int] = 2
_COLUMNAR_MIN_LENGTH: Final[int] = 4


def _numeric_field_count(d: dict) -> int:
    return sum(1 for v in d.values() if _is_numeric(v))


def _row_like_count(values: Any) -> int:
    """How many of *values* are row-like records (a dict of >= 6 numeric fields)."""
    return sum(
        1
        for value in values
        if isinstance(value, dict) and _numeric_field_count(value) >= _ROW_LIKE_MIN_NUMERIC_FIELDS
    )


def _is_numeric_series(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= _COLUMNAR_MIN_LENGTH
        and all(_is_numeric(v) for v in value)
    )


def _scan_undeclared(
    obj: Any, findings: list[str], counters: _Counters, *, key_label: str | None = None
) -> None:
    if isinstance(obj, dict):
        # §12.25 (S1) runs here too. There are no declared blocks in a payload
        # that declares no schema, so nothing is exempt — the backstop is the
        # stricter of the two, which is the direction PR #448 §5.5.6 requires.
        _scan_record_shape(obj, findings, key_label, is_declared_block=False)
        series_count = sum(1 for v in obj.values() if _is_numeric_series(v))
        if series_count >= _COLUMNAR_MIN_SERIES:
            findings.append("gate3a_columnar_numeric_series")
        # F2-2: the row-like count applied to `list`/`tuple` items only, so the
        # identical records re-keyed as a dict-of-dicts were counted nowhere.
        # 15 x 8 price rows that way land on exactly 120 numeric leaves — the
        # undeclared budget, which bounds but does not exceed — and scanned with
        # `findings=[]`. The record count is a property of the records, not of
        # the container they were poured into.
        if _row_like_count(obj.values()) >= _ROW_LIKE_MIN_RECORDS:
            findings.append("gate3a_row_like_numeric_records")
        for key, value in obj.items():
            if not isinstance(key, str):
                findings.append(f"gate3a_non_string_key:{key!r}")
                if _non_finite(key):
                    findings.append("gate3a_non_finite_key")
                # Same labelling rule as the declared scan: a finding raised
                # under a non-string key names that key, never the parent's.
                _scan_undeclared(value, findings, counters, key_label=f"non_string_key({key!r})")
                continue
            pinned = _pin(key)
            _scan_key_claims(pinned, value, findings)
            _scan_timestamp_spelling(pinned, findings, key_label)
            _scan_text_bounds(pinned, findings, f"key({pinned[:40]})")
            _scan_credential_values(pinned, findings, f"key({pinned[:40]})")
            _scan_undeclared(value, findings, counters, key_label=pinned)
        return
    if isinstance(obj, (list, tuple)):
        if _row_like_count(obj) >= _ROW_LIKE_MIN_RECORDS:
            findings.append("gate3a_row_like_numeric_records")
        numeric_rows = sum(1 for x in obj if _is_numeric_series(x))
        if numeric_rows >= _ROW_LIKE_MIN_RECORDS:
            findings.append("gate3a_row_like_numeric_arrays")
        for item in obj:
            _scan_undeclared(item, findings, counters, key_label=key_label)
        return
    counters.leaves += 1
    if counters.leaves > _UNDECLARED_MAX_LEAVES:
        findings.append("gate3a_leaf_cardinality_exceeded")
    if _non_finite(obj):
        findings.append(f"gate3a_non_finite_value:{key_label}")
    if _is_numeric(obj):
        counters.numeric += 1
        if counters.numeric > _UNDECLARED_MAX_NUMERIC_LEAVES:
            findings.append("gate3a_numeric_cardinality_exceeded")
    elif isinstance(obj, str):
        _scan_value_claims(obj, findings, exempt=False)
        _scan_timestamp_spelling(obj, findings, key_label)
        _scan_text_bounds(obj, findings, key_label)
        _scan_credential_values(obj, findings, key_label)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

_UNSCANNABLE: Final[tuple[type[BaseException], ...]] = (
    TypeError,
    ValueError,
    OverflowError,
    RecursionError,
)


def resolve_schema(payload: Any, artifact: str | None) -> tuple[ArtifactSchema | None, list[str]]:
    """Resolve the declared schema for *payload*, reporting any mismatch.

    A payload may declare itself through its own ``artifact`` field; a writer
    additionally supplies the filename stem. When both are present they must
    agree — otherwise a payload could carry a permissive artifact's schema while
    being written under another artifact's name.
    """
    findings: list[str] = []
    self_declared: ArtifactSchema | None = None
    if isinstance(payload, dict):
        raw = payload.get("artifact")
        if isinstance(raw, str):
            self_declared = artifact_schema(raw)
            if self_declared is None and _pin(raw).strip():
                findings.append(f"gate3a_undeclared_artifact_name:{_pin(raw)}")
    by_filename = artifact_schema(artifact) if artifact is not None else None
    if artifact is not None and self_declared is not None and by_filename is not self_declared:
        findings.append(f"gate3a_artifact_name_mismatch:{artifact}")
        return None, findings
    return (by_filename or self_declared), findings


def snapshot_payload(payload: Any) -> Any:
    """Read *payload* **once**, into plain built-in containers (FB-2).

    ``write_metadata_artifact`` used to validate the caller's object and then
    hand the *same object* back to ``serialise``, so the bytes on disk were a
    different read from the bytes that were checked. A ``dict`` subclass showing
    a clean face for the validating reads and the real payload on the ninth
    published ``{"result": "PRODUCTION_READY", "sharpe_ratio": 2.31, "net_pnl":
    91234.5}`` through the real writer. Nothing in this module snapshotted, while
    ``_pin``, ``no_overlap._materialise``, ``coverage._materialise_bars`` and
    ``calendar_authority._slots_from_mapping`` all do — and this is the one
    module that writes.

    Every container is read exactly once here and never consulted again: each
    ``items()`` / iteration result is materialised immediately, ``str`` character
    data is pinned through ``str.__str__``, and ``int`` / ``float`` are pinned
    through the **unbound** ``int.__index__`` / ``float.__float__``, because
    ``int(v)`` and ``float(v)`` re-enter the object's own dunder. Whatever face
    the object shows at this moment is the face that is validated, scrubbed,
    serialised and written.

    Objects of any other type are carried through unchanged — they are not
    containers, so there is nothing to re-read, and ``serialise`` refuses them as
    ``gate3a_unserialisable_payload``.
    """
    if isinstance(payload, dict):
        return {snapshot_payload(k): snapshot_payload(v) for k, v in list(payload.items())}
    if isinstance(payload, (list, tuple)):
        return [snapshot_payload(item) for item in list(payload)]
    if isinstance(payload, bool):
        return payload is True
    if isinstance(payload, str):
        return str.__str__(payload)
    if isinstance(payload, int):
        return int.__index__(payload)
    if isinstance(payload, float):
        return float.__float__(payload)
    return payload


def _refuse_json_constant(constant: str) -> None:
    """``json.loads`` hook: the non-standard literals are not JSON."""
    raise ValueError(f"non-standard JSON constant {constant}")


def _scan_snapshot(snapshot: Any, artifact: str | None) -> tuple[list[str], str | None]:
    """Scan an already-snapshotted payload; return its findings and its bytes.

    Order is part of the fix. The structural scan runs **first** and the base
    scrubber is reached only if this payload's text is within the bounds
    :func:`_scan_text_bounds` enforces (FR-17): the base scrubber's
    ``[a-z0-9]+\\.r2\\.cloudflarestorage\\.com`` pattern backtracks
    catastrophically on a long alphanumeric run — 2 000 chars 0.024 s, 8 000
    0.355 s, 16 000 1.416 s, and a 306 KB base64 value did not finish in 110 s —
    and there is no size bound or timeout on it. A payload carrying text this
    module has already refused as unbounded is refused; it is not additionally
    handed to a scanner that may not return.

    What that buys, stated exactly rather than overclaimed: every string reaching
    the base scanner is at most :data:`_MAX_TEXT_CHARS` long and there are at most
    ``schema.max_leaves`` of them, so the cost is **bounded** — the theoretical
    worst legitimate payload measures ~1.4 s, and the 306 KB case that previously
    did not terminate measures ~0.4 s. It is not made fast; it is made finite,
    which is the property a gatekeeper needs.

    The serialisation is performed **once**, here, and returned. That is what
    reconciles RF-11's internal ``serialise`` with the writer's: there is one
    call and its result is the bytes that get written.
    """
    findings: list[str] = []
    schema, resolution_findings = resolve_schema(snapshot, artifact)
    findings.extend(resolution_findings)
    counters = _Counters()
    try:
        if schema is None:
            _scan_undeclared(snapshot, findings, counters)
        else:
            _scan_declared(
                snapshot,
                schema,
                findings,
                counters,
                numeric_allowed=False,
                exempt=False,
                key_label=None,
            )
    except RecursionError:
        findings.append("gate3a_payload_too_deeply_nested")

    # RF-11: a payload declared clean that `serialise` cannot write used to die
    # with a bare `TypeError` at the write. It fails here, as a scrub error.
    serialised: str | None = None
    try:
        serialised = _serialise(snapshot)
    except _UNSCANNABLE as exc:
        findings.append(f"gate3a_unserialisable_payload:{type(exc).__name__}")

    if serialised is not None:
        # §14's worst survivor: a non-finite leaf under a *declared* numeric key
        # was caught by one guard and nothing else, and neither `scan_payload`
        # nor `serialise` rejects NaN — so with that guard removed the writer
        # emitted the non-standard `NaN` literal. The bytes about to be written
        # are re-parsed in strict mode, which is a check on the *artifact* rather
        # than on the payload and cannot be defeated by any re-encoding of it.
        try:
            json.loads(serialised, parse_constant=_refuse_json_constant)
        except (ValueError, RecursionError) as exc:
            findings.append(f"gate3a_non_standard_json_output:{type(exc).__name__}")

    if not any(f.startswith("gate3a_oversize_text:") for f in findings):
        try:
            findings.extend(_base_scan_payload(snapshot))
        # Reachable: a deeply nested payload raises RecursionError inside the
        # base scanner. Pinned by
        # test_a_payload_the_scanner_cannot_traverse_is_a_finding_not_a_crash.
        except _UNSCANNABLE as exc:
            findings.append(f"gate3a_unscannable_payload:{type(exc).__name__}")
    return sorted(set(findings)), serialised


def scan_gate3a(payload: Any, *, artifact: str | None = None) -> list[str]:
    """Base scrubber findings PLUS the gate-3a allowlist / claim prohibitions."""
    try:
        snapshot = snapshot_payload(payload)
    except _UNSCANNABLE as exc:
        return [f"gate3a_unscannable_payload:{type(exc).__name__}"]
    return _scan_snapshot(snapshot, artifact)[0]


def assert_gate3a_clean(payload: Any, *, artifact: str | None = None) -> None:
    findings = scan_gate3a(payload, artifact=artifact)
    if findings:
        raise ArtifactScrubError(f"gate-3a artifact not clean: {findings}")


def _assert_snapshot_shape(snapshot: Any) -> None:
    """RF-22 / RF-27: the vacuity floor, decided on the snapshot.

    A bare label, a number or ``None`` is not a metadata artifact, and neither is
    an empty container — each used to be accepted under a mutation of the type
    test alone. FB-2: these are answered by the snapshot, so ``__len__`` and
    ``__class__`` are read from a plain ``dict`` / ``list``, not from the
    caller's object.
    """
    if isinstance(snapshot, (dict, list)) is False or isinstance(snapshot, bool):
        raise ArtifactScrubError(
            f"metadata artifact must be an object or array, got {type(snapshot).__name__}"
        )
    if len(snapshot) == 0:
        raise ArtifactScrubError("metadata artifact must not be empty")


def _validate_and_serialise(payload: Any, *, artifact: str | None) -> str:
    """Snapshot once, validate that snapshot, and return **its** bytes (FB-2).

    This is the whole write path's single read of the caller's object. There is
    no check-then-reread after it: the text returned here is the text written.
    """
    try:
        snapshot = snapshot_payload(payload)
    except _UNSCANNABLE as exc:
        raise ArtifactScrubError(
            f"metadata artifact could not be read into a snapshot: {type(exc).__name__}"
        ) from exc
    _assert_snapshot_shape(snapshot)
    findings, serialised = _scan_snapshot(snapshot, artifact)
    if findings:
        raise ArtifactScrubError(f"gate-3a artifact not clean: {findings}")
    if serialised is None:  # pragma: no cover - a failed serialise is always a finding
        raise ArtifactScrubError("metadata artifact could not be serialised")
    return serialised


def validate_metadata_artifact(payload: Any, *, artifact: str | None = None) -> None:
    """Fail closed unless the payload is a scrub-clean metadata object."""
    _validate_and_serialise(payload, artifact=artifact)


def _validate_name(name: Any) -> str:
    """Pin and validate a bare ``*.json`` artifact filename (RF-6).

    The checks used to run against the object handed in, so a ``str`` subclass
    overriding ``endswith``, ``__eq__`` or ``__contains__`` answered them one way
    and gave ``out / name`` a different string. The character data is pinned once
    and every later use — including the join — reads the pinned value.
    """
    if not isinstance(name, str):
        raise ArtifactScrubError(f"artifact name must be a str, got {type(name).__name__}")
    text = _pin(name)
    if "\x00" in text:
        raise ArtifactScrubError("artifact name containing a NUL byte refused")
    if not text.endswith(".json"):
        raise ArtifactScrubError(f"artifact name must end with .json, got {text!r}")
    if (
        text != Path(text).name
        or Path(text).is_absolute()
        or any(sep in text for sep in ("/", "\\", ":"))
    ):
        raise ArtifactScrubError(f"artifact name must be a bare filename, got {text!r}")
    if not text[: -len(".json")].strip().strip("."):
        raise ArtifactScrubError(f"artifact name needs a non-empty stem, got {text!r}")
    return text


def _missing_ancestors(out: Path) -> list[Path]:
    """Directories that do not exist yet, deepest first."""
    missing: list[Path] = []
    probe = out
    while True:
        try:
            if probe.exists():
                return missing
        except (OSError, ValueError):  # pragma: no cover - defensive
            return missing
        missing.append(probe)
        if probe.parent == probe:
            return missing
        probe = probe.parent


def write_metadata_artifact(out_dir: str | Path, name: str, payload: Any) -> Path:
    """Validate + write a scrub-clean gate-3a metadata artifact.

    Order matters and is part of the contract: both path refusals run before any
    directory is created, the payload is validated against the schema its
    filename declares, an existing target is refused rather than overwritten
    (D-7 — the committed artifacts are populated by human-reviewed PR diff, not
    by a code path), and any failure at the write itself removes the partial file
    and every directory this call created (RF-9).
    """
    text = _validate_name(name)
    out = Path(out_dir)
    refuse_real_path(out)
    target = out / text
    refuse_real_path(target)
    # FB-2: ONE read of the caller's object, and the bytes that read produced are
    # the bytes written. The previous two lines were
    # `validate_metadata_artifact(payload, ...)` followed by
    # `evidence.serialise(payload)` — a second, unchecked read of the same
    # object.
    serialised = _validate_and_serialise(payload, artifact=text)
    if target.exists():
        raise ArtifactScrubError(
            f"refusing to overwrite an existing artifact: {text} (D-7: existing evidence is "
            "never rewritten by a code path)"
        )
    created = _missing_ancestors(out)
    try:
        out.mkdir(parents=True, exist_ok=True)
        target.write_text(serialised, encoding="utf-8")
    except (OSError, ValueError) as exc:
        with suppress(OSError):
            target.unlink()
        for directory in created:
            with suppress(OSError):
                directory.rmdir()
        raise ArtifactScrubError(f"artifact write failed for {text!r}: {exc}") from exc
    return target
