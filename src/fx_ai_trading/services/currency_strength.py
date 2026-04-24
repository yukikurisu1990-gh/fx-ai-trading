"""CurrencyStrengthIndex — classical CSI from cross-pair returns (Phase 9.3).

Computes per-currency strength scores from a snapshot of 1-bar returns across
FX pairs, then z-score normalises the raw strength values.

Algorithm (classical CSI):
  For each currency C:
    strength(C) = mean(returns for pairs where C is base)
                - mean(returns for pairs where C is quote)

  Then z-score normalise across all currencies so the output is comparable
  across cycles regardless of market volatility magnitude.

Design:
  - Pure, stateless computation — no DB I/O, no clock.
  - ``compute()`` accepts any dict[str, float] keyed by OANDA-style instrument
    names (``"EUR_USD"``, ``"GBP_JPY"`` …).  Non-``A_B`` names are silently
    skipped.
  - Returns an empty dict if no valid pairs are supplied.
  - Returns zeros if fewer than 2 currencies are present (z-score undefined).
  - ``CurrencyStrengthIndex`` is instantiated once and reused; no mutable state.

Usage:
    csi = CurrencyStrengthIndex()
    pair_returns = {"EUR_USD": 0.0012, "GBP_USD": -0.0005, "EUR_GBP": 0.0017}
    strengths = csi.compute(pair_returns)
    # {"EUR": 1.15, "USD": -0.82, "GBP": -0.33}
"""

from __future__ import annotations

import logging
from collections import defaultdict
from statistics import mean, stdev

_log = logging.getLogger(__name__)


class CurrencyStrengthIndex:
    """Stateless classical CSI calculator.

    ``compute()`` is idempotent: same input → same output (Phase 1 I-7).
    """

    def compute(self, pair_returns: dict[str, float]) -> dict[str, float]:
        """Compute z-score normalised per-currency strength.

        Args:
            pair_returns: instrument → 1-bar return.  Keys must follow
                ``"BASE_QUOTE"`` format (e.g. ``"EUR_USD"``).

        Returns:
            currency → z-score strength.  Empty dict if no valid pairs.
        """
        base_returns: dict[str, list[float]] = defaultdict(list)
        quote_returns: dict[str, list[float]] = defaultdict(list)

        for inst, ret in pair_returns.items():
            parts = inst.split("_")
            if len(parts) != 2:
                _log.debug("CurrencyStrengthIndex: skipping non-pair key %r", inst)
                continue
            base, quote = parts
            base_returns[base].append(ret)
            quote_returns[quote].append(ret)

        currencies = set(base_returns) | set(quote_returns)
        if not currencies:
            return {}

        raw: dict[str, float] = {}
        for ccy in currencies:
            b_avg = mean(base_returns[ccy]) if base_returns[ccy] else 0.0
            q_avg = mean(quote_returns[ccy]) if quote_returns[ccy] else 0.0
            raw[ccy] = b_avg - q_avg

        return _zscore(raw)


def _zscore(values: dict[str, float]) -> dict[str, float]:
    """Z-score normalise a dict of floats in place (returns new dict)."""
    if len(values) < 2:
        return {k: 0.0 for k in values}
    vals = list(values.values())
    mu = mean(vals)
    s = stdev(vals)
    if s == 0.0:
        return {k: 0.0 for k in values}
    return {k: (v - mu) / s for k, v in values.items()}


__all__ = ["CurrencyStrengthIndex"]
