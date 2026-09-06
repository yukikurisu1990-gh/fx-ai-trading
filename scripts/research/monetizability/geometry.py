"""Stage 1A — the clean retrace geometry re-test.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The detector is Round B′'s, unchanged, and so is the matched null. One thing
changes and it is the thing the plan froze: **the primary statistic is
`median_retrace_sigma`, not the retrace fraction.**

The fraction divides by the realised excursion, and the detector does not select
the same excursions on the real series and on the null — real anchors form faster
and are smaller in σ. Round B′ measured both: the fraction reached `z = +5.70`
while the same quantity without the denominator reached `z ≤ +1.96`. Whatever the
right reading of that is, a statistic whose numerator and denominator both move
cannot be the one a verdict is read off.

Draws are 200, not Round B′'s 40, so a family-wise `p` is not pinned at a floor.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from scripts.research.monetizability import (
    EXCURSION_SIGMAS,
    FAMILYWISE_ALPHA,
    NULL_DRAWS,
    PRIMARY_STATISTIC,
    SECONDARY_STATISTIC,
    SEED,
    STUDENTIZED_FLOOR,
)
from scripts.research.round_a import panels
from scripts.research.round_b_prime import retrace

#: the σ-level companion of the pre-registered day trim, so clause 4 is read off
#: the primary rather than off the fraction
TRIMMED_PRIMARY = "median_retrace_sigma_excluding_top_10_days"


def against_null(
    panel: dict[str, pd.DataFrame],
    k: float,
    *,
    draws: int = NULL_DRAWS,
    seed: int = SEED,
    null_name: str = "N2_sign_flip",
) -> dict[str, Any]:
    """Round B′'s comparison at 200 draws.

    The σ-level day trim clause 4 reads is produced inside `retrace.summarise`,
    so it comes out of the **same** null loop as everything else. An earlier
    version of this module ran a second identical loop for it, which doubled the
    cost of the most expensive stage for no additional information.
    """
    return retrace.against_null(panel, k, draws=draws, seed=seed, null_name=null_name)


def bloc_split(
    panel: dict[str, pd.DataFrame], k: float, *, draws: int = NULL_DRAWS, seed: int = SEED
) -> dict[str, Any]:
    """Clause 5 — JPY and non-JPY, each against the same matched null."""
    out: dict[str, Any] = {}
    for name, chosen in (
        ("JPY", {p: f for p, f in panel.items() if p in panels.JPY_PAIRS}),
        ("non_JPY", {p: f for p, f in panel.items() if p not in panels.JPY_PAIRS}),
    ):
        result = retrace.against_null(chosen, k, draws=draws, seed=seed)
        out[name] = (result.get("null") or {}).get(PRIMARY_STATISTIC)
    return out


def verdict(
    per_panel: dict[str, Any],
    blocs: dict[str, Any],
    deciding: tuple[str, ...],
) -> dict[str, Any]:
    """Plan §7 — five clauses, on the σ-level primary, on both deciding panels."""
    out: dict[str, Any] = {}
    surviving: list[float] = []
    for k in EXCURSION_SIGMAS:
        rows = {name: (per_panel.get(name) or {}).get(str(k)) for name in deciding}
        stats = {
            name: ((rows[name] or {}).get("null") or {}).get(PRIMARY_STATISTIC) for name in deciding
        }
        if not all(stats.values()):
            out[k] = {"decidable": False, "reason": "the primary is unavailable on a panel"}
            continue

        diffs = [stats[name]["real_minus_null"] for name in deciding]
        zs = [stats[name]["studentized"] or 0.0 for name in deciding]
        clause_1 = (diffs[0] > 0) == (diffs[1] > 0)
        clause_2 = all(abs(z) >= STUDENTIZED_FLOOR for z in zs)

        family = {
            name: (((rows[name] or {}).get("null") or {}).get("family_max") or {}).get(
                "family_wise_p"
            )
            for name in deciding
        }
        clause_3 = all(p is not None and p <= FAMILYWISE_ALPHA for p in family.values())

        trimmed = {
            name: ((rows[name] or {}).get("null") or {}).get(TRIMMED_PRIMARY) for name in deciding
        }
        if all(trimmed.values()):
            trimmed_diffs = [trimmed[name]["real_minus_null"] for name in deciding]
            clause_4 = all((d > 0) == (diffs[0] > 0) for d in trimmed_diffs)
        else:
            trimmed_diffs, clause_4 = None, None

        bloc = blocs.get(str(k)) or {}
        bloc_diffs = {
            name: {
                b: (bloc.get(name, {}).get(b) or {}).get("real_minus_null")
                for b in ("JPY", "non_JPY")
            }
            for name in deciding
        }
        values = [v for row in bloc_diffs.values() for v in row.values() if v is not None]
        clause_5 = (
            all((v > 0) == (diffs[0] > 0) for v in values)
            if len(values) == 2 * len(deciding)
            else None
        )

        survives = bool(
            clause_1 and clause_2 and clause_3 and clause_4 is not False and clause_5 is not False
        )
        if survives:
            surviving.append(k)
        out[k] = {
            "decidable": True,
            "primary": PRIMARY_STATISTIC,
            "real_minus_null": [round(d, 5) for d in diffs],
            "studentized": [round(z, 3) for z in zs],
            "family_wise_p": family,
            "clause_1_same_sign": clause_1,
            "clause_2_studentized": clause_2,
            "clause_3_family_wise": clause_3,
            "clause_4_day_trim": clause_4,
            "clause_4_trimmed_real_minus_null": trimmed_diffs,
            "clause_5_both_blocs": clause_5,
            "clause_5_bloc_real_minus_null": bloc_diffs,
            "secondary_fraction": {
                name: (((rows[name] or {}).get("null") or {}).get(SECONDARY_STATISTIC) or {}).get(
                    "real_minus_null"
                )
                for name in deciding
            },
            "survives": survives,
        }
    return {
        "per_threshold": out,
        "surviving_thresholds": surviving,
        "kill_condition_met": not surviving,
        "status": (
            "RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST"
            if not surviving
            else "RETRACE_GEOMETRY_SURVIVES_CLEAN_SIGMA_LEVEL_RETEST"
        ),
    }


__all__ = ["TRIMMED_PRIMARY", "against_null", "bloc_split", "verdict"]
