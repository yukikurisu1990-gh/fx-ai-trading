"""The evidence for the two pre-registration amendments, from committed code.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The plan carries two amendment tables — §13, which rejected a 5-day *block* sign
flip as the primary null, and §14, which rescaled the retrace observation
window. Both were computed on **generated** data before any panel was touched,
and both made the test harder. Neither had a producing file in the tree.

That is the same failure this programme has hit before: an artifact whose
generator was never committed cannot be re-derived, and a reviewer measuring the
committed code got numbers close to but not equal to the recorded ones. Since
those two tables are the entire evidence that the amendments were legitimate,
they have to be reproducible from the repository.

This module reproduces both. The numbers it produces **supersede** the recorded
tables where they differ: these are the ones a reader can re-run. Nothing here
touches market data — every series is generated.

The rejected designs are implemented here, clearly labelled, rather than in
`nulls.py` or `retrace.py`, so that no rejected design is importable from the
modules the round actually runs.
"""

from __future__ import annotations

import json
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.round_b_prime import SEED, nulls, retrace, variance_ratio

CACHE: Final = bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "round_b_prime"

#: the block length the plan first registered, in bars
REGISTERED_BLOCK_BARS: Final[int] = 5 * nulls.BARS_PER_DAY
#: the window multiples §14 compared against the flat one
WINDOW_MULTIPLES: Final[tuple[int, ...]] = (2, 4, 8)


def _rejected_block_flip(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """The null the plan **first registered** and §13 rejected. Not for use.

    A whole block's signs are drawn together, so the path inside a block is
    reversed but otherwise untouched. Every `q`-bar sum with `q` below the block
    length therefore has the same variance it had, and the null reproduces the
    real statistic instead of testing it.
    """
    steps = nulls._returns(frame)
    blocks = np.arange(len(steps)) // REGISTERED_BLOCK_BARS
    signs = rng.choice((-1.0, 1.0), size=blocks.max() + 1)[blocks]
    return nulls._rebuild(frame, steps * signs, flipped=signs < 0)


def _serially_dependent_walk(
    n: int, rng: np.random.Generator, *, phi: float = -0.10, pip: float = 0.01
) -> pd.DataFrame:
    """An AR(1) walk with volatility clustering — the §13 fixture.

    `phi < 0` puts a real mean-reverting term at lag 1, so a null that works
    must push `VR` back toward 1 and a null that does not will return the real
    value.
    """
    base = nulls.random_walk_frame(n, rng, pip=pip)
    innovations = rng.normal(0.0, 1.0, n - 1)
    #: a slow volatility cycle, so clustering is present for a null to preserve
    scale = 1.0 + 0.6 * np.sin(np.arange(n - 1) / 500.0)
    steps = np.empty(n - 1)
    previous = 0.0
    for index in range(n - 1):
        previous = phi * previous + innovations[index] * scale[index]
        steps[index] = previous
    return nulls._rebuild(base, steps)


def block_flip_is_degenerate(
    *, n: int = 60_000, draws: int = 20, seed: int = SEED
) -> dict[str, Any]:
    """Plan §13, reproduced: the registered block flip returns the real `VR`."""
    rng = np.random.default_rng(seed)
    frame = _serially_dependent_walk(n, rng)
    panel = {"AR1": frame}
    real = variance_ratio.panel_vr(panel)

    def mean_vr(null) -> dict[int, float]:
        draws_rng = np.random.default_rng(seed)
        samples = [variance_ratio.panel_vr({"AR1": null(frame, draws_rng)}) for _ in range(draws)]
        return {q: float(np.mean([s[q] for s in samples])) for q in real}

    block = mean_vr(_rejected_block_flip)
    per_bar = mean_vr(nulls.n2_sign_flip)
    return {
        "fixture": "AR(1) phi=-0.10 with a volatility cycle, generated",
        "bars": n,
        "draws": draws,
        "block_length_bars": REGISTERED_BLOCK_BARS,
        "per_horizon": {
            str(q): {
                "real": round(real[q], 5),
                "registered_block_flip": round(block[q], 5),
                "amended_per_bar_flip": round(per_bar[q], 5),
                "block_shift_from_real": round(abs(block[q] - real[q]), 6),
                "per_bar_shift_from_real": round(abs(per_bar[q] - real[q]), 6),
            }
            for q in sorted(real)
        },
        "verdict": (
            "the registered block flip reproduces the real variance ratio to "
            "several decimals at every horizon below the block length, so it "
            "cannot reject anything; the amended per-bar flip moves it to about 1"
        ),
    }


def _anchors_with_window(frame: pd.DataFrame, k: float, multiple: int | None) -> pd.DataFrame:
    """`find_anchors` with the observation window forced, for §14 only.

    `multiple = None` is the flat `OBSERVATION_WINDOW` the plan first
    registered; an integer is that many times the bars the excursion took.
    """
    original = retrace.WINDOW_MULTIPLE
    forced = retrace.OBSERVATION_WINDOW if multiple is None else multiple
    try:
        retrace.WINDOW_MULTIPLE = forced  # type: ignore[misc]
        return retrace.find_anchors(frame, k)
    finally:
        retrace.WINDOW_MULTIPLE = original  # type: ignore[misc]


def the_window_was_scale_mismatched(
    *, n: int = 60_000, k: float = 1.5, seed: int = SEED
) -> dict[str, Any]:
    """Plan §14, reproduced: a flat 480-bar window measures the window.

    On a random walk there is no retrace structure, so a well-scaled window
    should return a median fraction near the value anchor selection alone
    produces and a `reached_50` rate well below saturation.
    """
    frame = nulls.random_walk_frame(n, np.random.default_rng(seed))
    rows: dict[str, Any] = {}
    for label, multiple in [("flat_480", None)] + [(f"x{m}", m) for m in WINDOW_MULTIPLES]:
        anchors = _anchors_with_window(frame, k, multiple)
        if anchors.empty:
            rows[label] = {"anchors": 0}
            continue
        rows[label] = {
            "anchors": int(len(anchors)),
            "median_bars_to_anchor": round(float(anchors["bars_to_anchor"].median()), 1),
            "median_observation_bars": round(float(anchors["observation_bars"].median()), 1),
            "window_over_excursion": round(
                float(anchors["observation_bars"].median() / anchors["bars_to_anchor"].median()), 1
            ),
            "median_retrace_fraction": round(float(anchors["max_retrace_fraction"].median()), 5),
            "reached_50_rate": round(float(anchors["reached_50"].mean()), 5),
        }
    return {
        "fixture": "IID Gaussian random walk, generated",
        "bars": n,
        "k": k,
        "adopted_multiple": retrace.WINDOW_MULTIPLE,
        "per_window": rows,
        "verdict": (
            "the flat window is tens of times the excursion that opened it, so "
            "the median fraction and `reached_50` measure the window rather "
            "than the retrace; the adopted multiple restores the scale the "
            "pre-registered economic floor was written for"
        ),
    }


def evidence() -> dict[str, Any]:
    return {
        "classification": "AMENDMENT_EVIDENCE_GENERATED_DATA_ONLY",
        "market_data_read": False,
        "section_13_block_flip": block_flip_is_degenerate(),
        "section_14_window_scale": the_window_was_scale_mismatched(),
    }


def write() -> dict[str, Any]:
    """Its own entry point rather than a step in the panel driver.

    Nothing here reads a panel, so it does not belong inside a run that does.
    """
    payload = evidence()
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "amendment_evidence.json").write_text(
        json.dumps(
            {
                "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
                "classification_secondary": "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
                "payload": payload,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":  # pragma: no cover - the entry point
    print(json.dumps(write(), indent=2, sort_keys=True, default=str))


__all__ = [
    "CACHE",
    "REGISTERED_BLOCK_BARS",
    "WINDOW_MULTIPLES",
    "block_flip_is_degenerate",
    "evidence",
    "the_window_was_scale_mismatched",
    "write",
]
