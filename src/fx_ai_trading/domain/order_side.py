"""Canonical mapping between ``orders.direction`` and position ``side``.

D3 §2.6.1 records trade intent on the orders table (and on
``trading_signals``) using the ``direction`` vocabulary
(``'buy'`` / ``'sell'``).  The exit / state surface speaks in terms of
``side`` (``'long'`` / ``'short'``).  This module is the single source
of truth for the conversion so both gates (entry and exit) agree on the
mapping by construction.

Cycle 6.7c E2 used a paper-mode long-only default at ``run_exit_gate``;
M-1a (Design A) starts deriving ``side`` per-position from
``orders.direction`` so that short positions can be closed correctly
once paper-mode lifts the long-only constraint and Phase 7 / live sees
real ``'sell'`` orders.

Note: ``services/execution_gate_runner.py`` still defines a sibling
local copy under the name ``_DIRECTION_TO_BROKER_SIDE`` for the entry
side.  Unifying the two callsites onto this module is intentionally
out of scope for M-1a (it would expand the diff into the entry path);
the cleanup is tracked separately.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

# orders.direction → position side.  Single source of truth (D3 §2.6.1).
_DIRECTION_TO_SIDE: Final[Mapping[str, str]] = {
    "buy": "long",
    "sell": "short",
}


__all__ = ["_DIRECTION_TO_SIDE"]
