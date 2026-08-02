"""Effective-N estimator (PR #430 T-6) — pure, synthetic inputs only.

The **committed** ``artifacts/m15_gate3a/effective_n_estimator_spec.json``
(status ``APPROVED_SPEC``) is the sole authority for the arithmetic:

* ``rho_h_pair = 1 + (H - 1) * overlap_fraction_pair``  (H = 24 M15 bars)
* ``N_eff_pair = N_raw_pair / rho_h_pair``
* ``rho_x      = 1 + (P - 1) * mean_abs_pairwise_corr``
* ``N_eff      = (sum of N_eff_pair) / rho_x``

Re-check fixes (PR #439):

* **B-3** — the previous implementation collapsed the per-pair step into one
  portfolio scalar ``raw / (rho_h * rho_x)``. That is not equivalent when
  overlap varies across pairs and it is **not conservative**: the audited
  counter-example (50 events at overlap 0.0 plus 8000 at overlap 1.0) is
  ``383.33`` → ``INSUFFICIENT_SAMPLE`` under the approved spec but came out as
  ``644.00`` → ``SAMPLE_SUFFICIENT``. Per-pair counts and overlaps are now
  required, and both portfolio and per-pair granularity are reported as the
  spec's ``reporting`` block mandates.
* **B-5** — validation floors are validated before they can decide anything:
  both must be supplied together, finite, correctly typed and positive. A NaN
  floor previously produced ``SAMPLE_SUFFICIENT`` on zero events because
  ``0 < nan`` is ``False`` — the same comparison-with-NaN class F-4 fixed.
* **R-1** — ``horizon_bars`` is pinned to the frozen contract value for the
  holdout role and is echoed in the record, so an override can no longer flip
  the verdict invisibly.

Computes NO strategy metrics and reads NO validation / holdout data — the raw
counts, overlap fractions and correlation are supplied by the caller.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Final

from .pair_authority import PAIRS_20, PairAuthorityError, canonical_pair

HORIZON_M15_BARS: Final[int] = 24
N_EFF_HOLDOUT_FLOOR: Final[int] = 400
RAW_HOLDOUT_TRADE_FLOOR: Final[int] = 1000
INSUFFICIENT_SAMPLE: Final[str] = "INSUFFICIENT_SAMPLE"
SUFFICIENT: Final[str] = "SAMPLE_SUFFICIENT"
NOT_EVALUATED: Final[str] = "NOT_EVALUATED_AT_THIS_ROLE"
_KNOWN_ROLES: Final[frozenset[str]] = frozenset({"holdout", "validation"})


class EffectiveNError(ValueError):
    """Raised when effective-N inputs violate the estimator contract."""


def _require_count(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EffectiveNError(f"{what} must be a non-negative integer")
    return value


def _require_unit_fraction(value: Any, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EffectiveNError(f"{what} must be a number")
    v = float(value)
    if not math.isfinite(v) or not (0.0 <= v <= 1.0):
        raise EffectiveNError(f"{what} must be a finite number in [0, 1]")
    return v


def _require_positive_floor(value: Any, what: str, *, integral: bool) -> float:
    if value is None:
        raise EffectiveNError(f"{what} must be supplied")
    if isinstance(value, bool):
        raise EffectiveNError(f"{what} must be a number, not a bool")
    if integral:
        if not isinstance(value, int):
            raise EffectiveNError(f"{what} must be an integer")
    elif not isinstance(value, (int, float)):
        raise EffectiveNError(f"{what} must be a number")
    v = float(value)
    if not math.isfinite(v) or v <= 0:
        raise EffectiveNError(f"{what} must be a finite positive number")
    return v


def _normalise_pairs(per_pair: Sequence[Any]) -> list[dict[str, Any]]:
    if not isinstance(per_pair, Sequence) or isinstance(per_pair, (str, bytes)):
        raise EffectiveNError("per_pair must be a sequence of per-pair records")
    if not per_pair:
        raise EffectiveNError("per_pair must not be empty")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for entry in per_pair:
        if not isinstance(entry, dict):
            raise EffectiveNError("each per-pair record must be a dict")
        for key in ("pair", "raw_event_count", "overlap_fraction"):
            if key not in entry:
                raise EffectiveNError(f"per-pair record missing key {key!r}")
        # D4: identity is bound to the canonical PAIRS_20 universe. Without it
        # "usd_jpy" and "USD_JPY" counted as two pairs, defeating the duplicate
        # guard and inflating P in the cross-pair haircut, and an off-universe
        # label was accepted outright.
        try:
            pair = canonical_pair(entry["pair"])
        except PairAuthorityError as exc:
            raise EffectiveNError(f"per-pair 'pair' invalid: {exc}") from exc
        if pair in seen:
            raise EffectiveNError(f"duplicate pair in per_pair: {pair!r}")
        seen.add(pair)
        out.append(
            {
                "pair": pair,
                "raw_event_count": _require_count(
                    entry["raw_event_count"], f"raw_event_count for {pair!r}"
                ),
                "overlap_fraction": _require_unit_fraction(
                    entry["overlap_fraction"], f"overlap_fraction for {pair!r}"
                ),
            }
        )
    return out


def effective_n(
    per_pair: Sequence[Any],
    *,
    cross_pair_corr: float,
    horizon_bars: int = HORIZON_M15_BARS,
    role: str = "holdout",
    validation_raw_floor: int | None = None,
    validation_neff_floor: float | None = None,
) -> dict:
    """Return raw + effective counts, per-pair detail, and the verdict (fail-closed).

    ``per_pair`` is a sequence of ``{"pair", "raw_event_count",
    "overlap_fraction"}`` records — the per-pair granularity the approved spec
    requires. Non-overlapping, independent inputs recover ``N_eff -> raw``.

    Role handling is fail-closed: an unknown ``role`` raises;
    ``role="holdout"`` applies the frozen floors (raw >= 1000 AND N_eff >= 400)
    and pins the horizon to the contract value; ``role="validation"`` NEVER
    returns ``SAMPLE_SUFFICIENT`` by default — without validation floors it
    returns ``NOT_EVALUATED_AT_THIS_ROLE``, and floors that are supplied must be
    complete, finite and positive.
    """
    if role not in _KNOWN_ROLES:
        raise EffectiveNError(f"unknown role {role!r} (fail closed)")

    records = _normalise_pairs(per_pair)
    corr = _require_unit_fraction(cross_pair_corr, "cross_pair_corr")

    if isinstance(horizon_bars, bool) or not isinstance(horizon_bars, int) or horizon_bars < 1:
        raise EffectiveNError("horizon_bars must be a positive integer")
    if horizon_bars != HORIZON_M15_BARS:
        # R-1: the horizon is frozen at 24 by Ruling 6. Pinning it only for the
        # holdout role still let a validation verdict be flipped by an override,
        # so it is now frozen for every role.
        raise EffectiveNError(
            f"horizon_bars is frozen at {HORIZON_M15_BARS} by the contract (got {horizon_bars})"
        )

    n_pairs = len(records)
    if n_pairs > len(PAIRS_20):  # pragma: no cover - canonical identity already bounds this
        raise EffectiveNError(f"n_pairs {n_pairs} exceeds the frozen universe {len(PAIRS_20)}")
    rho_x = 1.0 + (n_pairs - 1) * corr
    raw_total = 0
    n_eff_sum = 0.0
    per_pair_out: list[dict[str, Any]] = []
    for rec in records:
        rho_h_pair = 1.0 + (horizon_bars - 1) * rec["overlap_fraction"]
        n_eff_pair = rec["raw_event_count"] / rho_h_pair
        raw_total += rec["raw_event_count"]
        n_eff_sum += n_eff_pair
        per_pair_out.append(
            {
                "pair": rec["pair"],
                "raw_event_count": rec["raw_event_count"],
                "overlap_fraction": rec["overlap_fraction"],
                "rho_h": rho_h_pair,
                "effective_n": n_eff_pair,
            }
        )

    n_eff = n_eff_sum / rho_x

    floors_applied: dict[str, float] | None = None
    if role == "holdout":
        verdict = (
            INSUFFICIENT_SAMPLE
            if raw_total < RAW_HOLDOUT_TRADE_FLOOR or n_eff < N_EFF_HOLDOUT_FLOOR
            else SUFFICIENT
        )
        floors_applied = {
            "raw_floor": float(RAW_HOLDOUT_TRADE_FLOOR),
            "neff_floor": float(N_EFF_HOLDOUT_FLOOR),
        }
    elif validation_raw_floor is None and validation_neff_floor is None:
        verdict = NOT_EVALUATED  # validation is never default-sufficient (F-3)
    else:
        # B-5: partial, non-finite, non-positive or wrongly typed floors fail
        # closed instead of silently defaulting the other limb to zero.
        raw_floor = _require_positive_floor(
            validation_raw_floor, "validation_raw_floor", integral=True
        )
        neff_floor = _require_positive_floor(
            validation_neff_floor, "validation_neff_floor", integral=False
        )
        verdict = INSUFFICIENT_SAMPLE if raw_total < raw_floor or n_eff < neff_floor else SUFFICIENT
        floors_applied = {"raw_floor": raw_floor, "neff_floor": neff_floor}

    # D6: NaN / Infinity must never reach a written artifact (json.dumps would
    # emit the non-standard constants and the file would not re-parse strictly).
    for label, value in (("effective_n", n_eff), ("rho_x", rho_x)):
        if not math.isfinite(value):
            raise EffectiveNError(f"derived {label} is non-finite ({value!r})")
    for rec in per_pair_out:
        if not math.isfinite(rec["effective_n"]) or not math.isfinite(rec["rho_h"]):
            raise EffectiveNError(f"derived per-pair value for {rec['pair']!r} is non-finite")

    return {
        "role": role,
        "horizon_bars": horizon_bars,
        "n_pairs": n_pairs,
        "raw_event_count": raw_total,
        "rho_x": rho_x,
        "effective_n": n_eff,
        "per_pair": per_pair_out,
        "floors_applied": floors_applied,
        "n_eff_holdout_floor": N_EFF_HOLDOUT_FLOOR,
        "raw_holdout_trade_floor": RAW_HOLDOUT_TRADE_FLOOR,
        "verdict": verdict,
        "strategy_metrics_computed": False,
    }
