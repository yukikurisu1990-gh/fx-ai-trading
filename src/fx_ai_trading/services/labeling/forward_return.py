"""forward_return — leak-free forward-return label generator (Phase 9.5).

Label at bar i = (closes[i+horizon] - closes[i]) / closes[i].
Bars within `horizon` of the end return None (no future data available).

Leak-free guarantee:
  - Label y_t uses only closes[t+1 .. t+horizon].
  - Features at bar t must be computed from closes[0..t] separately.
"""

from __future__ import annotations


def forward_return(closes: list[float], horizon: int = 12) -> list[float | None]:
    """Compute forward log-return for each bar.

    Args:
        closes: Ordered close prices (ascending time).
        horizon: Number of bars ahead to measure return.

    Returns:
        List of length ``len(closes)``.  The last ``horizon`` entries are None.
    """
    if horizon <= 0:
        raise ValueError(f"horizon must be positive, got {horizon}")
    n = len(closes)
    result: list[float | None] = []
    for i in range(n):
        if i + horizon < n and closes[i] != 0.0:
            result.append((closes[i + horizon] - closes[i]) / closes[i])
        else:
            result.append(None)
    return result


__all__ = ["forward_return"]
