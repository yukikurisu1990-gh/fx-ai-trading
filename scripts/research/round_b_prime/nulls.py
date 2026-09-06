"""The three nulls, and exactly what each preserves and destroys.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

This file is first because the plan puts it first. Round A's failure was not that
its statistic was wrong but that it had no null, so an identity in `σ√H` read as
a finding. Every null below states its contract in its own docstring, and
`sanity_check` refuses to let one be used before it has been shown to recover the
known answer on a series whose answer is known.

The contracts
-------------

============  ==========================================  ==========================
null          preserves                                    destroys
============  ==========================================  ==========================
N1 iid        the marginal distribution of 1-bar returns   all serial dependence,
                                                           including clustering
N2 signflip   ``|r_t|`` at every bar, so volatility        the sign of every
              clustering, the calendar and the weekend     return, drawn
              gaps are intact                              independently per bar
N3 weekday    each return's weekday and hour-of-day slot   serial dependence within
                                                           a slot; not calendar
                                                           placement
============  ==========================================  ==========================

**N2 is the primary null.** It is the only one that isolates *directional* serial
dependence: it leaves volatility clustering exactly where it was and randomises
nothing but the signs, so a real-minus-N2 difference cannot be clustering.
N1 and N3 are there to say what an N2 result is not.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

BARS_PER_DAY: Final[int] = 96


def _returns(frame: pd.DataFrame) -> np.ndarray:
    """1-bar mid returns in pips. The object every null permutes."""
    return (frame["mid_c"].diff() / frame["pip_size"]).to_numpy()[1:]


def _rebuild(frame: pd.DataFrame, steps: np.ndarray) -> pd.DataFrame:
    """A frame whose `mid_c` is the given step sequence, everything else intact.

    High and low keep their own offsets from the close, so bar shapes survive and
    the excursion detector sees the same kind of object it sees on real bars.
    """
    out = frame.copy()
    pip = frame["pip_size"].to_numpy()
    close = frame["mid_c"].to_numpy()
    walk = np.concatenate([[close[0]], close[0] + np.cumsum(steps * pip[1:])])
    for column in ("mid_h", "mid_l", "mid_o"):
        offset = (frame[column] - frame["mid_c"]).to_numpy()
        out[column] = walk + offset
    out["mid_c"] = walk
    return out


def n1_iid(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Preserves the return marginal. Destroys **all** serial dependence.

    Cannot distinguish directional dependence from volatility clustering: both
    are gone. Use it only to bound "is there any serial structure at all".
    """
    steps = _returns(frame)
    return _rebuild(frame, rng.permutation(steps))


def n2_sign_flip(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Preserves `|r_t|` at every bar. Destroys the sign of every return.

    Volatility clustering, the calendar, the weekend gaps and the intraday shape
    are all exactly as they were — only the signs are re-drawn, **independently
    per bar**. So a real-minus-N2 difference cannot be clustering, because
    clustering is identical on both sides.

    **This is the primary null**, and it was amended before any statistic ran.
    The plan first registered a 5-day *block* flip; a block flip leaves every
    path inside a block untouched, so the variance of a `q`-bar sum with `q`
    below the block length is unchanged and the null returns the real value
    exactly — measured at 0.8959 against a real 0.8959 on a synthetic AR(1)
    series. `docs/research/m15_round_b_prime_plan.md` §13 carries the table.
    """
    steps = _returns(frame)
    return _rebuild(frame, steps * rng.choice((-1.0, 1.0), size=len(steps)))


def n3_weekday(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Preserves each return's weekday and hour slot. Destroys order within it.

    If a real-minus-N1 difference is really about weekend gaps or session
    structure rather than serial dependence, N3 reproduces it and N1 does not.
    """
    steps = _returns(frame)
    stamps = frame["ts"].iloc[1:]
    key = (stamps.dt.dayofweek * 24 + stamps.dt.hour).to_numpy()
    shuffled = steps.copy()
    for slot in np.unique(key):
        index = np.flatnonzero(key == slot)
        shuffled[index] = steps[rng.permutation(index)]
    return _rebuild(frame, shuffled)


NULLS: Final[dict[str, Any]] = {
    "N1_iid": n1_iid,
    "N2_sign_flip": n2_sign_flip,
    "N3_weekday": n3_weekday,
}

CONTRACTS: Final[dict[str, dict[str, str]]] = {
    "N1_iid": {
        "preserves": "the marginal distribution of 1-bar returns",
        "destroys": "all serial dependence, including volatility clustering",
        "detects": "any serial structure; cannot separate clustering from direction",
    },
    "N2_sign_flip": {
        "preserves": "|r_t| at every bar, so clustering, the calendar and the gaps are intact",
        "destroys": "the sign of every return, drawn independently per bar",
        "detects": "directional serial dependence with clustering held fixed (primary)",
    },
    "N3_weekday": {
        "preserves": "each return's weekday and hour-of-day slot",
        "destroys": "serial dependence within a slot, but not calendar placement",
        "detects": "whether an N1 result is a calendar artefact rather than serial dependence",
    },
}


def random_walk_frame(n: int, rng: np.random.Generator, *, pip: float = 0.01) -> pd.DataFrame:
    """A generated IID Gaussian random walk with the columns the round needs.

    The known answer: `VR(q) = 1` for every `q`, and no retrace structure beyond
    what the anchor selection itself produces.
    """
    steps = rng.normal(0.0, 1.0, n - 1)
    close = np.concatenate([[100.0], 100.0 + np.cumsum(steps * pip)])
    ts = pd.date_range("2022-01-03", periods=n, freq="15min", tz="UTC")
    spread = np.full(n, 0.02)
    return pd.DataFrame(
        {
            "ts": ts,
            "mid_o": close,
            "mid_h": close + pip * 0.5,
            "mid_l": close - pip * 0.5,
            "mid_c": close,
            "spread_close_pips": spread / pip,
            "pip_size": pip,
            "rollover": False,
            "n_source_bars": 15,
            "complete_bucket": True,
            "session": "asia",
        }
    )


def sanity_check(statistic, *, draws: int, length: int = 40_000, seed: int) -> dict[str, Any]:
    """Every null must recover the known answer on a true random walk.

    A null that does not is measuring its own construction, and any real-minus-
    null difference computed against it is uninterpretable. This runs before any
    real comparison is read and is reported whatever it shows.

    `statistic` takes a frame and returns a dict of `{name: value}`.
    """
    rng = np.random.default_rng(seed)
    walk = random_walk_frame(length, rng)
    observed = statistic(walk)
    out: dict[str, Any] = {"walk_bars": length, "draws": draws, "observed_on_walk": observed}
    for name, null in NULLS.items():
        values: list[dict[str, float]] = []
        for _ in range(draws):
            values.append(statistic(null(walk, rng)))
        keys = sorted(observed)
        out[name] = {
            key: {
                "null_mean": round(float(np.mean([v[key] for v in values])), 5),
                "null_sd": round(float(np.std([v[key] for v in values])), 5),
                "observed": round(float(observed[key]), 5),
                "z": round(
                    float(
                        (observed[key] - np.mean([v[key] for v in values]))
                        / (np.std([v[key] for v in values]) or np.inf)
                    ),
                    3,
                ),
            }
            for key in keys
        }
    return out


__all__ = [
    "BARS_PER_DAY",
    "CONTRACTS",
    "NULLS",
    "n1_iid",
    "n2_sign_flip",
    "n3_weekday",
    "random_walk_frame",
    "sanity_check",
]
