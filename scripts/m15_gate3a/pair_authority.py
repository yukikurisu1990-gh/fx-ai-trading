"""Canonical pair normalisation + universe enforcement for gate-3a (B-4).

The re-check (PR #439, B-4) found that gate-3a read its pip size straight from
``data_adapter.pip_size_for``, whose contract is ``pair.endswith("_JPY")`` with
no case handling and no pair universe. ``usd_jpy`` therefore scaled 100x wrong
and an unknown pair was silently given the non-JPY size, while this package's
docstrings claimed it failed closed on unknown pairs. Both `aggregate_m15` and
`validate_cost_table` consulted the same function, so their cross-check could
not see the error.

This module is the gate-3a boundary: every pair name is normalised to its
canonical ``XXX_YYY`` form, checked against the frozen 20-pair universe, and
only then handed to the single pip authority. Unknown or ambiguous names fail
closed. No data is read and no spread is computed here.
"""

from __future__ import annotations

from typing import Final

from scripts.ml_step4.data_adapter import pip_size_for as _authority_pip_size_for

# The frozen PAIRS_20 universe (Ruling 2 — fixed, no selection). Value-pinned
# here so gate-3a does not depend on a stage script's import side effects; the
# tests assert this tuple equals the canonical lists committed elsewhere.
PAIRS_20: Final[tuple[str, ...]] = (
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CHF",
    "USD_CAD",
    "EUR_GBP",
    "USD_JPY",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "CHF_JPY",
    "EUR_CHF",
    "EUR_AUD",
    "EUR_CAD",
    "AUD_NZD",
    "AUD_CAD",
    "GBP_AUD",
    "GBP_CHF",
)

_SEPARATORS: Final[tuple[str, ...]] = ("-", "/", ".", " ")


class PairAuthorityError(ValueError):
    """Raised when a pair name is unusable: malformed, ambiguous, or off-universe."""


def _normalise_key(pair: str) -> str:
    """Reduce a pair spelling to its canonical ``XXX_YYY`` key (no universe check)."""
    key = pair.strip().upper()
    for sep in _SEPARATORS:
        key = key.replace(sep, "_")
    while "__" in key:
        key = key.replace("__", "_")
    key = key.strip("_")
    if "_" not in key and len(key) == 6:
        key = f"{key[:3]}_{key[3:]}"
    return key


def _build_index() -> dict[str, str]:
    """Map every accepted spelling key to its canonical pair; fail closed on collision."""
    index: dict[str, str] = {}
    for canonical in PAIRS_20:
        key = _normalise_key(canonical)
        if key in index and index[key] != canonical:  # pragma: no cover - defensive
            raise PairAuthorityError(
                f"normalisation collision: {canonical!r} and {index[key]!r} both map to {key!r}"
            )
        index[key] = canonical
    if len(index) != len(PAIRS_20):  # pragma: no cover - defensive
        raise PairAuthorityError("pair normalisation is not injective over PAIRS_20")
    return index


_INDEX: Final[dict[str, str]] = _build_index()


def canonical_pair(pair: object) -> str:
    """Return the canonical ``XXX_YYY`` name, or fail closed.

    Accepts case, separator (``-`` ``/`` ``.`` space) and compact (``USDJPY``)
    spellings. Rejects non-strings, empty strings, and anything outside the
    frozen PAIRS_20 universe — including names that merely *look* like pairs.
    """
    if not isinstance(pair, str) or not pair.strip():
        raise PairAuthorityError("pair must be a non-empty string")
    key = _normalise_key(pair)
    canonical = _INDEX.get(key)
    if canonical is None:
        raise PairAuthorityError(
            f"pair {pair!r} (normalised {key!r}) is not in the frozen PAIRS_20 universe"
        )
    return canonical


def pip_size_for_pair(pair: object) -> float:
    """Per-pair pip size for a gate-3a caller — normalised, universe-bound, fail-closed.

    Delegates to the single pip authority (``data_adapter.pip_size_for``) using
    the canonical name, so JPY crosses always resolve to ``0.01`` and non-JPY to
    ``0.0001`` regardless of how the caller spelled the pair.
    """
    canonical = canonical_pair(pair)
    size = _authority_pip_size_for(canonical)
    if not isinstance(size, float) or not size > 0:  # pragma: no cover - defensive
        raise PairAuthorityError(f"non-positive pip size for {canonical!r}")
    return size
