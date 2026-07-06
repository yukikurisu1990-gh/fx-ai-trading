"""Warm-up burn-in policy (PR #430 T-1) — metadata-level, fail-closed.

Dead-window data must NEVER be loaded. Forward-epoch warm-up uses forward-epoch
bars only; the first ``w_bars`` forward bars are event-ineligible; ``w_bars``
must be >= the longest feature lookback (including H1/H4 context). Loading any
timestamp before the forward floor fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .no_overlap import FORWARD_FLOOR


class WarmupPolicyError(RuntimeError):
    """Raised when the warm-up policy is missing/too small or loads pre-forward data."""


@dataclass(frozen=True)
class WarmupPolicy:
    """Forward-epoch warm-up burn-in contract (exact w_bars frozen at feature impl)."""

    w_bars: int
    longest_feature_lookback_bars: int

    def validate(self) -> None:
        if not isinstance(self.w_bars, int) or self.w_bars <= 0:
            raise WarmupPolicyError("w_bars must be a positive integer")
        if (
            not isinstance(self.longest_feature_lookback_bars, int)
            or self.longest_feature_lookback_bars <= 0
        ):
            raise WarmupPolicyError("longest_feature_lookback_bars must be a positive integer")
        if self.w_bars < self.longest_feature_lookback_bars:
            raise WarmupPolicyError(
                f"w_bars {self.w_bars} < longest_feature_lookback_bars "
                f"{self.longest_feature_lookback_bars} (warm-up too short)"
            )

    def assert_load_allowed(self, ts: Any) -> None:
        """Fail closed if any load timestamp precedes the forward floor (dead-window guard)."""
        if isinstance(ts, datetime):
            t = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
            t = t.astimezone(UTC)
        elif isinstance(ts, str) and ts.strip():
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)
        else:
            raise WarmupPolicyError(f"unparseable load timestamp: {ts!r}")
        if t < FORWARD_FLOOR:
            raise WarmupPolicyError(
                f"warm-up would load pre-forward data at {t.isoformat()} "
                f"(< forward floor {FORWARD_FLOOR.isoformat()}); pre-forward load forbidden"
            )

    def as_metadata(self) -> dict:
        self.validate()
        return {
            "policy": "forward_epoch_warmup_burn_in_T1",
            "w_bars": self.w_bars,
            "longest_feature_lookback_bars": self.longest_feature_lookback_bars,
            "first_w_bars_event_eligible": False,
            "dead_window_loaded": False,
            "forward_floor_utc": FORWARD_FLOOR.isoformat(),
            "exact_w_frozen_at": "feature_implementation",
        }
