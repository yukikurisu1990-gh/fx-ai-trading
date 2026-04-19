"""Token-bucket RateLimiter with 2 named buckets (M15 / Ob-MIDRUN-1).

Buckets:
  trading   — high-priority path (capacity=10, rps=10)
  reconcile — low-priority path  (capacity=2,  rps=2  per §6.2)

MidRunReconciler selects the bucket based on its priority argument:
  normal → reconcile bucket
  high   → trading bucket (gap-recovery mode)

Clock injection enables deterministic tests without real time.
"""

from __future__ import annotations

import threading

from fx_ai_trading.common.clock import Clock, WallClock

_BUCKET_CONFIGS: dict[str, tuple[float, float]] = {
    "trading": (10.0, 10.0),
    "reconcile": (2.0, 2.0),
}

VALID_BUCKETS = frozenset(_BUCKET_CONFIGS)


class _TokenBucket:
    def __init__(self, capacity: float, rps: float, clock: Clock) -> None:
        self._capacity = capacity
        self._rps = rps
        self._clock = clock
        self._tokens = capacity
        self._last_refill = clock.now()
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        with self._lock:
            now = self._clock.now()
            elapsed = (now - self._last_refill).total_seconds()
            if elapsed > 0:
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rps)
                self._last_refill = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    @property
    def tokens(self) -> float:
        with self._lock:
            return self._tokens


class RateLimiter:
    """Token-bucket rate limiter with independent 'trading' and 'reconcile' buckets."""

    def __init__(self, clock: Clock | None = None) -> None:
        _clock = clock or WallClock()
        self._buckets: dict[str, _TokenBucket] = {
            name: _TokenBucket(capacity=cap, rps=rps, clock=_clock)
            for name, (cap, rps) in _BUCKET_CONFIGS.items()
        }

    def acquire(self, bucket: str) -> bool:
        """Consume one token from *bucket*.  Returns True if acquired, False if rate-limited."""
        if bucket not in self._buckets:
            raise ValueError(f"Unknown RateLimiter bucket: {bucket!r}")
        return self._buckets[bucket].acquire()

    def available_tokens(self, bucket: str) -> float:
        """Return current token count for *bucket* (for tests / observability)."""
        if bucket not in self._buckets:
            raise ValueError(f"Unknown RateLimiter bucket: {bucket!r}")
        return self._buckets[bucket].tokens
