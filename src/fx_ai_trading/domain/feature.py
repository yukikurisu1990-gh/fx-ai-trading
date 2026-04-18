"""FeatureBuilder domain interface and DTOs (D3 §2.2.1).

Deterministic feature computation. No look-ahead, no random state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureSet:
    """Output of FeatureBuilder.build() (D3 §2.2.1).

    feature_hash: SHA256 short — same inputs + same feature_version → byte-equal hash.
    full_features: None when compact_mode is active.
    """

    feature_version: str
    feature_hash: str
    feature_stats: dict
    sampled_features: dict
    computed_at: datetime
    full_features: dict | None = None


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


class FeatureBuilder(Protocol):
    """Deterministic feature computation (D3 §2.2.1).

    Critical invariants:
      - Never reference now() internally; use as_of_time parameter.
      - No unfixed random state.
      - No order-nondeterministic parallel reduce.

    Side effect: writes to feature_snapshots (via Repository, not directly).

    Raises FeatureUnavailable when input data is missing.
    """

    def build(
        self,
        instrument: str,
        tier: str,
        cycle_id: UUID,
        as_of_time: datetime,
    ) -> FeatureSet:
        """Compute and return features as of *as_of_time*.

        Raises:
            FeatureUnavailable: if required input data is absent.
        """
        ...

    def get_feature_version(self) -> str:
        """Return the deterministic version string (6.10)."""
        ...
