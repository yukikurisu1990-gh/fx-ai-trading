"""Track A run identity, and the calendar semantics a run declares.

§8.12's `TRACK_A_CALENDAR_IDENTITY_REQUIREMENT_IS_AN_EXECUTION_GATE_QUESTION`
left open how much provenance a Track A run needs.  This is the answer at the
weight the execution gate actually requires: **enough to tell which run touched
which span, and under which calendar reading** — and no more.

What Track A does *not* need
----------------------------

The formal-evidence calendar contract (`calendar_authority.ValidatedCalendar`)
requires an approved artifact carrying ``authority_version``,
``content_digest``, ``target_epoch`` and the human + ChatGPT approval marker,
and `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` gates it.  **That is
unchanged for Track B.**  Requiring it of Track A would block exploration on an
artifact that does not exist, for no leakage reason: a Track A run computes no
coverage verdict and produces no evidence.

What it does need, and why each field is here
---------------------------------------------

* ``run_id`` — so the seen-data ledger's entries attribute to something. Without
  it the ledger records that *a* run touched a span, which is not a record.
* ``code_sha`` — the run's own commit. R-7's ancestry test needs a code SHA to
  compare a registration against; a run that cannot name its own commit cannot
  participate in an ordering claim later.
* ``calendar_semantics`` — a **label**, not an artifact: which reading of
  session and closure boundaries the run used. Track A may not *author* market
  hours (§8.4's ω-12 ownership ruling stands), so the label names a reading, and
  two runs with different labels are not comparable.
* ``started_at_utc`` — supplied by the caller, never read from the clock here,
  so a record is reproducible and a test does not depend on the time of day.

Determinism note
----------------

This module derives nothing from the wall clock and generates no randomness.
``run_id`` is a caller-supplied label; the digest is a pure function of the
declared fields.  A run that wants a stable id computes it once and records it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Final

_SHA_RE: Final[re.Pattern[str]] = re.compile(r"\A[0-9a-f]{40}\Z")
_RUN_ID_RE: Final[re.Pattern[str]] = re.compile(r"\A[a-z0-9][a-z0-9_-]{2,63}\Z")
_TS_RE: Final[re.Pattern[str]] = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")

#: Calendar readings a Track A run may declare.  A closed set: an unrecognised
#: label fails closed rather than becoming a new, undocumented convention.
#: ``utc_calendar_dates_no_market_hours`` is the only reading available today,
#: because no approved calendar artifact exists and Track A may not invent one
#: (omega-12). PR #455 produced a **proposed** Calendar A and a review role showed
#: why this sentence still stands: the boundary it invented was both uncommitted
#: and factually wrong. See docs/governance/m15_track_a_r1_enablement_referrals.md.
CALENDAR_UTC_DATES_NO_MARKET_HOURS: Final[str] = "utc_calendar_dates_no_market_hours"

KNOWN_CALENDAR_SEMANTICS: Final[frozenset[str]] = frozenset({CALENDAR_UTC_DATES_NO_MARKET_HOURS})

#: Recorded on every run so a reader knows the identity is research-grade.
IDENTITY_GRADE: Final[str] = "TRACK_A_RESEARCH_RUN_IDENTITY_NOT_EVIDENCE_GRADE_PROVENANCE"


class RunIdentityError(ValueError):
    """Raised when a run identity is incomplete or malformed."""


def _require(value: Any, pattern: re.Pattern[str], what: str, hint: str) -> str:
    if type(value) is not str:  # noqa: E721 - a subclass may lie about its content
        raise RunIdentityError(f"{what} must be a plain str, got {type(value).__name__}")
    if not pattern.match(value):
        raise RunIdentityError(f"{what} is malformed ({hint}): {value!r}")
    return value


@dataclass(frozen=True)
class RunIdentity:
    """Who a Track A run is, and under what calendar reading it ran."""

    run_id: str
    code_sha: str
    calendar_semantics: str
    started_at_utc: str

    def __post_init__(self) -> None:
        _require(
            self.run_id,
            _RUN_ID_RE,
            "run_id",
            "lowercase alphanumerics, hyphen and underscore, 3-64 chars",
        )
        _require(self.code_sha, _SHA_RE, "code_sha", "full 40-character lowercase hex SHA")
        if type(self.calendar_semantics) is not str:  # noqa: E721
            raise RunIdentityError("calendar_semantics must be a plain str")
        if self.calendar_semantics not in KNOWN_CALENDAR_SEMANTICS:
            raise RunIdentityError(
                f"unknown calendar_semantics {self.calendar_semantics!r}; a Track A run "
                f"declares one of {sorted(KNOWN_CALENDAR_SEMANTICS)} and may not author "
                "market hours (fail closed)"
            )
        _require(
            self.started_at_utc,
            _TS_RE,
            "started_at_utc",
            "YYYY-MM-DDTHH:MM:SSZ, supplied by the caller",
        )

    @property
    def digest(self) -> str:
        """A stable digest of the declared identity — for cross-referencing, not proof."""
        payload = json.dumps(self.as_record(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "code_sha": self.code_sha,
            "calendar_semantics": self.calendar_semantics,
            "started_at_utc": self.started_at_utc,
            "identity_grade": IDENTITY_GRADE,
        }


__all__ = [
    "CALENDAR_UTC_DATES_NO_MARKET_HOURS",
    "IDENTITY_GRADE",
    "KNOWN_CALENDAR_SEMANTICS",
    "RunIdentity",
    "RunIdentityError",
]
