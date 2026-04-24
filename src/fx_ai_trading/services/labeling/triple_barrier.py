"""triple_barrier — fixed-pip triple-barrier label generator (Phase 9.5).

For each bar i, scans closes[i+1 .. i+horizon]:
  +1  if price reaches entry + tp_pips * pip_size first
  -1  if price reaches entry - sl_pips * pip_size first
   0  if neither barrier is touched within horizon (timeout)
  None if the full horizon window is not available (last `horizon` bars)

Leak-free guarantee:
  - Label y_t uses only closes[t+1 .. t+horizon].
  - Features at bar t must be computed from closes[0..t] separately.

Design choice (Phase 9.5):
  Fixed pips rather than ATR-based barriers for simplicity.
  ATR-based barriers are deferred to Phase 9.6+ if needed.
"""

from __future__ import annotations


def triple_barrier(
    closes: list[float],
    horizon: int,
    tp_pips: float,
    sl_pips: float,
    pip_size: float = 0.0001,
) -> list[int | None]:
    """Apply triple-barrier labeling to a close-price series.

    Args:
        closes: Ordered close prices (ascending time).
        horizon: Maximum bars to wait for a barrier touch.
        tp_pips: Take-profit distance in pips (positive float).
        sl_pips: Stop-loss distance in pips (positive float).
        pip_size: Price value of 1 pip (default 0.0001 for most FX pairs).

    Returns:
        List of length ``len(closes)``.  The last ``horizon`` entries are None.
    """
    if horizon <= 0:
        raise ValueError(f"horizon must be positive, got {horizon}")
    if tp_pips <= 0 or sl_pips <= 0:
        raise ValueError("tp_pips and sl_pips must be positive")

    n = len(closes)
    result: list[int | None] = []

    for i in range(n):
        if i + horizon >= n:
            result.append(None)
            continue

        entry = closes[i]
        tp_level = entry + tp_pips * pip_size
        sl_level = entry - sl_pips * pip_size
        label = 0

        for j in range(i + 1, i + horizon + 1):
            if closes[j] >= tp_level:
                label = 1
                break
            if closes[j] <= sl_level:
                label = -1
                break

        result.append(label)

    return result


__all__ = ["triple_barrier"]
