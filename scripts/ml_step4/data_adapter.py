"""Data adapters for the ML Step 4 run body (fixture vs refused-real).

Separates the synthetic fixture provider (usable now, in tests only) from the
future real ``365d_BA`` provider (REFUSED in this build). No environment
variable, flag, or default can enable real data: ``RealDataProviderRefused``
raises on every access, and no candle-file reader exists in this module.

Bar schema (one dict per completed M1 bar, chronological):
``{"ts": tz-aware UTC datetime (:00 seconds), "bid_o","bid_h","bid_l","bid_c",
"ask_o","ask_h","ask_l","ask_c"}``.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Final

PIP_SIZE: Final[float] = 0.0001


class RealDataRefusedError(RuntimeError):
    """Raised when real 365d_BA data access is requested (unavailable here)."""


class FixtureDataProvider:
    """Deterministic synthetic M1 bars for the fixture rehearsal (no files).

    A seeded LCG random walk — pure Python, no filesystem, no network. Same
    (pairs, n_bars, seed) → byte-identical bars.
    """

    mode = "fixture"
    synthetic_only = True

    def __init__(
        self,
        pairs: tuple[str, ...] = ("FIX_PAIR_A", "FIX_PAIR_B"),
        # 6000 M1 bars ≈ 4.2 days: the 15% holdout tail crosses a UTC date
        # boundary, so the R-5 day-grouping/denominator logic is genuinely
        # exercised by the default rehearsal.
        n_bars: int = 6000,
        seed: int = 20260705,
        start: datetime = datetime(2025, 6, 2, 0, 0, tzinfo=UTC),
    ) -> None:
        if start.tzinfo is None:
            raise RealDataRefusedError("fixture start must be tz-aware UTC")
        self.pairs = tuple(pairs)
        self.n_bars = int(n_bars)
        self.seed = int(seed)
        self.start = start.astimezone(UTC)

    def _lcg(self, state: int) -> int:
        return (state * 6364136223846793005 + 1442695040888963407) % (2**64)

    def bars_for(self, pair: str) -> list[dict]:
        """Deterministic synthetic bars for one pair (cross-process stable).

        Pair mixing uses a SHA-256 digest, NOT ``hash()`` — Python string
        hashing is randomized per process (PYTHONHASHSEED) and would make the
        fixture nondeterministic across runs.
        """
        if pair not in self.pairs:
            raise RealDataRefusedError(f"unknown fixture pair {pair!r}")
        pair_mix = int.from_bytes(hashlib.sha256(pair.encode("utf-8")).digest()[:4], "big")
        state = self.seed ^ pair_mix
        mid = 1.1000
        spread = 1.2 * PIP_SIZE
        bars: list[dict] = []
        ts = self.start
        for _ in range(self.n_bars):
            state = self._lcg(state)
            step = ((state >> 16) % 2001 - 1000) / 1000.0  # [-1, 1]
            state = self._lcg(state)
            wick = ((state >> 16) % 1000) / 1000.0  # [0, 1)
            o = mid
            c = mid + step * 1.2 * PIP_SIZE
            hi = max(o, c) + wick * 0.8 * PIP_SIZE
            lo = min(o, c) - wick * 0.8 * PIP_SIZE
            half = spread / 2.0
            bars.append(
                {
                    "ts": ts,
                    "bid_o": o - half,
                    "bid_h": hi - half,
                    "bid_l": lo - half,
                    "bid_c": c - half,
                    "ask_o": o + half,
                    "ask_h": hi + half,
                    "ask_l": lo + half,
                    "ask_c": c + half,
                }
            )
            mid = c
            ts = ts + timedelta(minutes=1)
        return bars


class RealDataProviderRefused:
    """The future real ``365d_BA`` provider — REFUSES every access in this build.

    A separately-authorised first-run execution PR must replace this with a
    provider that re-verifies the PR-B.1 checksums immediately before reading.
    No environment variable or constructor argument can unlock it here.
    """

    mode = "real_refused"
    synthetic_only = False

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Constructing the refused provider is allowed (so wiring can reference
        # it); every DATA access refuses.
        del args, kwargs

    @property
    def pairs(self) -> tuple[str, ...]:
        raise RealDataRefusedError("real 365d_BA data access is not available in this build")

    def bars_for(self, pair: str) -> list[dict]:
        raise RealDataRefusedError(
            "real 365d_BA data access is not available in this build; a separately "
            "authorised first-run execution PR must implement the real provider "
            "with pre-consumption checksum re-verification"
        )
