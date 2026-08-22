"""Warm-up burn-in policy (PR #430 T-1) — metadata-level, fail-closed.

Dead-window data must NEVER be loaded. Forward-epoch warm-up uses forward-epoch
bars only; the first ``w_bars`` forward bars are event-ineligible; ``w_bars``
must be >= the longest feature lookback (including H1/H4 context). Loading any
timestamp before the forward floor fails closed.

**R-1, the negative-control rule.** ``as_metadata()`` used to emit
``dead_window_loaded: False`` and ``first_w_bars_event_eligible: False`` as
hard-coded constants. The first is the T-1 leakage claim itself asserted as a
fact this class never measures — it observes no load and could not have emitted
``True`` under any input. Both are therefore **deleted, not reported**, and each
property is instead exposed as a genuinely two-valued predicate that the same
code path answers both ways on a deliberately constructed counter-case:

* :meth:`WarmupPolicy.loads_pre_forward` — ``True`` for a pre-forward timestamp,
  ``False`` for a forward one; it is the predicate
  :meth:`WarmupPolicy.assert_load_allowed` refuses on, so the enforcement and the
  measurement cannot drift apart.
* :meth:`WarmupPolicy.is_event_eligible` — ``False`` for every bar index below
  ``w_bars``, ``True`` from ``w_bars`` onwards; the boundary itself is reported
  as the measured ``first_eligible_bar_index``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .no_overlap import FORWARD_FLOOR
from .numeric_authority import NumericAuthorityError, pin_int
from .timeutil import TimestampError, format_utc_z, to_utc


class WarmupPolicyError(RuntimeError):
    """Raised when the warm-up policy is missing/too small or loads pre-forward data."""


@dataclass(frozen=True)
class WarmupPolicy:
    """Forward-epoch warm-up burn-in contract (exact w_bars frozen at feature impl)."""

    w_bars: int
    longest_feature_lookback_bars: int

    def validate(self) -> None:
        """Fail closed unless the warm-up is a positive, long-enough burn-in.

        N-1: both counts are pinned to their plain ``int`` character data before
        anything is compared, and the pinned value is stored back, so every later
        read — the sufficiency test below, :meth:`is_event_eligible`'s boundary,
        and the ``w_bars`` / ``first_eligible_bar_index`` that reach
        :meth:`as_metadata` — sees the number the object really holds. Without
        that, an ``int`` subclass owning ``__lt__`` could report a warm-up long
        enough to cover the longest feature lookback while holding a shorter one,
        which is the T-1 leakage boundary itself.

        **FB-10 / FR-20 — the pin is now the gate, not an optimisation.** The
        loop used to skip pinning whenever ``isinstance(value, int)`` was false,
        and to ``continue`` when the numeric authority *refused*, under a
        a ``no cover - guarded above`` pragma asserting the refusal was
        unreachable. Both were wrong for the same reason: ``isinstance`` consults
        the object's ``__class__``, which any object may claim, while
        ``int.__index__`` then refuses — so the refusal was reachable, the
        ``continue`` swallowed it, and the ``isinstance``-based checks below
        could not recover because they consult ``__class__`` too and ``<=`` is
        answered by the object. Lead-reproduced: ``validate()`` **PASSED** for a
        ``__class__``-spoofing ``w_bars``, ``as_metadata()`` published the spoof
        as both ``w_bars`` and ``first_eligible_bar_index``, and eligibility
        started at bar 1 instead of 24 — the T-1 burn-in disarmed while reporting
        itself valid.

        The structure is now: *pin first, and let the refusal out*. There is no
        ``isinstance`` pre-check to disagree with the pin, so a value reaches the
        numeric comparisons below only after it has been reduced to plain ``int``
        character data. ``pin_int`` already refuses ``bool``, non-``int`` and
        ``__class__``-spoofing objects, so the per-field type checks that used to
        follow are subsumed by it rather than duplicated — a second check that
        could disagree with the first is how this defect existed.
        """
        for name in ("w_bars", "longest_feature_lookback_bars"):
            try:
                pinned = pin_int(getattr(self, name), what=name)
            except NumericAuthorityError as exc:
                raise WarmupPolicyError(
                    f"{name} must be a positive integer: it is not plain int character data ({exc})"
                ) from exc
            object.__setattr__(self, name, pinned)
        if self.w_bars <= 0:
            raise WarmupPolicyError("w_bars must be a positive integer")
        if self.longest_feature_lookback_bars <= 0:
            raise WarmupPolicyError("longest_feature_lookback_bars must be a positive integer")
        if self.w_bars < self.longest_feature_lookback_bars:
            raise WarmupPolicyError(
                f"w_bars {self.w_bars} < longest_feature_lookback_bars "
                f"{self.longest_feature_lookback_bars} (warm-up too short)"
            )

    def is_event_eligible(self, bar_index: int) -> bool:
        """R-1: measured event eligibility of the ``bar_index``-th forward bar.

        Zero-based over forward-epoch bars. ``False`` for every index inside the
        burn-in, ``True`` from ``w_bars`` onwards — a genuinely two-valued
        answer replacing the constant ``first_w_bars_event_eligible: False``.

        FR-20: the ``except NumericAuthorityError`` below carried
        a ``no cover - guarded above`` pragma on the strength of an
        ``isinstance`` pre-check. ``isinstance`` consults ``__class__``, so the
        branch was reachable and the suppression hid it. Both the pre-check and
        the pragma are gone: ``pin_int`` is the single gate on the index, exactly
        as it is on ``w_bars`` in :meth:`validate` (FB-10), and its refusal is
        reported rather than re-derived by a second test that could disagree.
        """
        self.validate()
        # N-1: pinned before the bound test and before the eligibility decision,
        # so an `int` subclass cannot answer "not negative" and "past the
        # burn-in" while holding an index inside it.
        try:
            index = pin_int(bar_index, what="bar_index")
        except NumericAuthorityError as exc:
            raise WarmupPolicyError(
                f"bar_index must be a non-negative integer: it is not plain int character "
                f"data ({exc})"
            ) from exc
        if index < 0:
            raise WarmupPolicyError("bar_index must be a non-negative integer")
        return index >= self.w_bars

    def _resolve_load_ts(self, ts: Any) -> datetime:
        """Validate the policy, then resolve ``ts`` **once** through the timestamp authority."""
        self.validate()
        try:
            return to_utc(ts)
        except TimestampError as exc:
            raise WarmupPolicyError(f"load timestamp rejected: {exc}") from exc

    @staticmethod
    def _is_pre_forward(t: datetime) -> bool:
        """The single pre-forward predicate; both the measurement and the refusal use it."""
        return t < FORWARD_FLOOR

    def loads_pre_forward(self, ts: Any) -> bool:
        """R-1: measured answer to "would loading ``ts`` reach pre-forward data?".

        ``True`` for any timestamp before the forward floor — which is exactly
        what :meth:`assert_load_allowed` refuses — and ``False`` otherwise. It
        replaces the constant ``dead_window_loaded: False``, which asserted the
        T-1 leakage claim while measuring nothing. A malformed or naive
        timestamp raises rather than answering ``False``: an unreadable
        timestamp is not evidence of safety. ``ts`` is resolved exactly once, so
        an object that answers differently on a second read cannot be measured
        as forward and then loaded as pre-forward.
        """
        return self._is_pre_forward(self._resolve_load_ts(ts))

    def assert_load_allowed(self, ts: Any) -> None:
        """Fail closed if any load timestamp precedes the forward floor.

        F-5 fix: naive datetimes and offset-less ISO strings FAIL CLOSED —
        never silently assumed UTC. N-3: the policy validates itself first, so
        an under-sized or malformed warm-up can no longer authorise a load.
        BL-2: awareness is decided by ``utcoffset()`` in the single timestamp
        authority, so a ``utcoffset()``-``None`` zone can no longer be read in
        the host's local time and slip under the forward floor.
        R-1: the refusal and :meth:`loads_pre_forward` share one predicate and
        one resolution of ``ts``, so the measured answer and the enforced one
        cannot diverge.
        """
        t = self._resolve_load_ts(ts)
        if self._is_pre_forward(t):
            raise WarmupPolicyError(
                f"warm-up would load pre-forward data at {t.isoformat()} "
                f"(< forward floor {FORWARD_FLOOR.isoformat()}); pre-forward load forbidden"
            )

    def as_metadata(self) -> dict:
        """Warm-up metadata.

        R-1: ``first_w_bars_event_eligible`` and ``dead_window_loaded`` are gone.
        Neither could ever hold its opposite value, so neither was evidence,
        while both read as measured facts — and ``dead_window_loaded: False`` was
        the T-1 leakage claim itself emitted as a constant. ``w_bars``,
        ``longest_feature_lookback_bars`` and the derived
        ``first_eligible_bar_index`` are declared inputs and a derived boundary,
        not self-attestations; the two properties are answered by
        :meth:`is_event_eligible` and :meth:`loads_pre_forward`.
        """
        self.validate()
        return {
            "policy": "forward_epoch_warmup_burn_in_T1",
            "w_bars": self.w_bars,
            "longest_feature_lookback_bars": self.longest_feature_lookback_bars,
            "first_eligible_bar_index": self.w_bars,
            # §12.23: canonical `...Z`, never `isoformat()`'s `+00:00`.
            "forward_floor_utc": format_utc_z(FORWARD_FLOOR),
            "exact_w_frozen_at": "feature_implementation",
        }
