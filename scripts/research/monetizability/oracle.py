"""Stage 1B — how much of the structure could be taken, at most.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `UPPER_BOUND_DIAGNOSTIC_ONLY`.

Nothing here is a strategy result. Three of the four bounds use future
information and could not be run by anything that trades; they exist because a
family whose **upper** bound is small cannot be rescued by a better label or a
better model, which makes this the cheapest available kill.

The four bounds
---------------

* **B-0 take-all** — the structural side on every event, no selection. Not a
  bound; the thing the bounds are measured against.
* **B-1 perfect take / skip** — the side is fixed by the structure and an oracle
  chooses only *whether* to trade, with perfect foresight.
* **B-2 perfect side** — an oracle chooses long or short with perfect foresight,
  and is still obliged to trade. It therefore does **not** dominate B-1: every
  event whose move is smaller than the spread costs it money, while B-1 may skip.
  Measured on a random walk at a 2.5 pip cost, B-2 comes out *below* B-1, and
  neither is the overall ceiling.
* **B-3 achievable selection** — the best **linear** selector on past-only
  features, fitted and scored on the same data. Optimistic, and unlike B-1 and
  B-2 it is limited to information a rule could actually have.

Why B-1 and B-2 cannot decide anything
--------------------------------------

`max(net, 0)` over a symmetric noise distribution is about `0.4 · σ_q` however
that distribution arose, so a perfect take/skip oracle earns a large amount on a
**pure random walk**. Measured on generated data before any panel was read
(`noise_reference`), and recorded as amendment A-1 to the package plan: B-1 and
B-2 are `DESCRIPTIVE_ONLY`, and the economic gate reads B-3 against its own
matched-null value instead. The amendment makes the gate harder, and it was made
before the first real statistic.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import engine
from scripts.research.round_b_prime import nulls, retrace

CLASSIFICATION = "UPPER_BOUND_DIAGNOSTIC_ONLY"

#: B-3's features. Past-only, small, and fixed here rather than searched. Each is
#: measurable at the decision bar; none uses the bar the position opens on.
FEATURE_NAMES: tuple[str, ...] = (
    "move_sigma",
    "log_sigma",
    "log_spread",
    "log_atr",
    "htf_aligned",
    "htf_outer",
    "hour_sin",
    "hour_cos",
)


def basis(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Everything B-3's design matrix needs, computed **once per frame**.

    The rolling windows here cost more than every event evaluation put together,
    and a panel is scored at four horizons, four phases and three thresholds
    against the same frame — so recomputing them per population made one null
    draw take 26 seconds and the whole run infeasible.
    """
    pip = float(frame["pip_size"].iloc[0])
    context = retrace.htf_context(frame)
    hour = frame["ts"].dt.hour.to_numpy(dtype=float)
    return {
        "close": frame["mid_c"].to_numpy(dtype=float),
        "pip": pip,
        "sigma": np.asarray(retrace.trailing_sigma(frame), dtype=float),
        "roundtrip_cost": frame["roundtrip_cost"].to_numpy(dtype=float),
        "log_sigma": np.log(
            np.maximum(np.asarray(retrace.trailing_sigma(frame), dtype=float) / pip, 1e-6)
        ),
        "log_spread": np.log(np.maximum(frame["spread_close_pips"].to_numpy(dtype=float), 1e-6)),
        "log_atr": np.log(np.maximum(np.asarray(engine.atr_pips(frame), dtype=float), 1e-6)),
        "htf_aligned": (np.asarray(context["htf_trend"], dtype=object) == "aligned").astype(float),
        "htf_outer": (np.asarray(context["htf_location"], dtype=object) == "outer").astype(float),
        "hour_sin": np.sin(2 * np.pi * hour / 24.0),
        "hour_cos": np.cos(2 * np.pi * hour / 24.0),
        "ts": frame["ts"].to_numpy(),
        "n": len(frame),
    }


def _features(built: dict[str, np.ndarray], index: np.ndarray, move_sigma: np.ndarray):
    """The B-3 design matrix at the decision bars, from information at those bars."""
    columns = [move_sigma] + [built[name][index] for name in FEATURE_NAMES[1:]]
    return np.column_stack([np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0) for c in columns])


def horizon_events(
    built: dict[str, np.ndarray], *, horizon: int, phase: int
) -> dict[str, np.ndarray] | None:
    """The detector-free population: fade the last `horizon`-bar move, hold it.

    Non-overlapping, so an event is one independent observation. The decision is
    taken at bar `t` from information ending at `t`; the position runs from
    `t + 1` to `t + 1 + horizon`, which is `engine.evaluate`'s own convention and
    one full bar of latency.
    """
    close, pip = built["close"], built["pip"]
    sigma, cost, n = built["sigma"], built["roundtrip_cost"], built["n"]

    start = max(horizon, retrace.RV_WINDOW) + phase
    stop = n - horizon - 2
    if stop <= start:
        return None
    index = np.arange(start, stop, horizon)
    if index.size < 8:
        return None

    past = (close[index] - close[index - horizon]) / pip
    forward = (close[index + 1 + horizon] - close[index + 1]) / pip
    #: the structural side is the reversion one -- VR(q) < 1 is what B′-1 found
    side = -np.sign(past)
    scale = np.maximum(sigma[index] / pip, 1e-9)
    keep = (side != 0) & np.isfinite(forward) & np.isfinite(past) & np.isfinite(scale)
    index, past, forward, side, scale = (
        index[keep],
        past[keep],
        forward[keep],
        side[keep],
        scale[keep],
    )
    if index.size < 8:
        return None

    return {
        "index": index,
        "gross": side * forward,
        "unit_cost": cost[index + 1],
        "abs_gross": np.abs(forward),
        "move_sigma": past / (scale * np.sqrt(horizon)),
        "ts": built["ts"][index],
    }


def anchor_events(
    built: dict[str, np.ndarray], found: pd.DataFrame
) -> dict[str, np.ndarray] | None:
    """The detector population: fade each `k · σ` excursion, hold the window.

    Takes the anchor frame the geometry stage already computed, so the detector
    runs once per draw rather than once per consumer.
    """
    if found.empty:
        return None
    close, pip = built["close"], built["pip"]
    cost, n = built["roundtrip_cost"], built["n"]

    anchor = found["anchor"].to_numpy(dtype=int)
    span = found["observation_bars"].to_numpy(dtype=int)
    exit_bar = np.minimum(anchor + 1 + span, n - 1)
    keep = (anchor + 1) < exit_bar
    anchor, span, exit_bar = anchor[keep], span[keep], exit_bar[keep]
    if anchor.size < 8:
        return None

    forward = (close[exit_bar] - close[anchor + 1]) / pip
    side = -found["direction"].to_numpy(dtype=float)[keep]
    return {
        "index": anchor,
        "gross": side * forward,
        "unit_cost": cost[anchor + 1],
        "abs_gross": np.abs(forward),
        "move_sigma": found["excursion_sigma"].to_numpy(dtype=float)[keep]
        * found["direction"].to_numpy(dtype=float)[keep],
        "ts": found["ts"].to_numpy()[keep],
    }


def _linear_selection(
    built: dict[str, np.ndarray], events: dict[str, np.ndarray], net: np.ndarray
) -> dict[str, float]:
    """B-3: the best in-sample linear predictor of the per-event net, then take it.

    Ridge-regularised least squares on standardised features, with the ridge
    fixed rather than tuned. In-sample by construction, so it is an upper bound
    on any linear selector rather than an achievable result — and the same
    computation on the matched null says how much of it is fitting noise.
    """
    design = _features(built, events["index"], events["move_sigma"])
    if len(net) <= design.shape[1] + 2:
        return {"selected": 0, "net": 0.0, "net_per_event": 0.0, "taken": None}
    centre = design.mean(axis=0)
    scale = design.std(axis=0)
    scale[scale == 0] = 1.0
    standard = np.column_stack([np.ones(len(design)), (design - centre) / scale])
    ridge = np.eye(standard.shape[1]) * 1e-3
    ridge[0, 0] = 0.0
    try:
        beta = np.linalg.solve(standard.T @ standard + ridge, standard.T @ net)
    except np.linalg.LinAlgError:  # pragma: no cover - singular design
        return {"selected": 0, "net": 0.0, "net_per_event": 0.0, "taken": None}
    taken = (standard @ beta) > 0
    return {
        "selected": int(taken.sum()),
        "net": float(net[taken].sum()),
        "net_per_event": float(net[taken].sum() / len(net)),
        "taken": taken,
    }


def _tail_share(ts: np.ndarray, value: np.ndarray, *, days: int = 10) -> float:
    """The share of a positive total contributed by its ten largest days."""
    total = float(value.sum())
    if total <= 0:
        return float("nan")
    frame = pd.DataFrame({"day": pd.to_datetime(ts, utc=True).floor("D"), "v": value})
    by_day = frame.groupby("day")["v"].sum().sort_values(ascending=False)
    return float(by_day.head(days).sum() / total)


def bounds(
    built: dict[str, np.ndarray],
    events: dict[str, np.ndarray] | None,
    *,
    trading_days: int,
    cost_multiplier: float,
) -> dict[str, Any] | None:
    """B-0, B-1, B-2 and B-3 for one pair's event population at one cost level."""
    if events is None or events["gross"].size < 8:
        return None
    gross = events["gross"]
    cost = events["unit_cost"] * cost_multiplier
    net = gross - cost
    count = len(net)
    take_skip = np.maximum(net, 0.0)
    perfect_side = events["abs_gross"] - cost
    equity = np.cumsum(net)
    selection = _linear_selection(built, events, net)
    taken = selection["taken"]

    return {
        "events": count,
        "events_per_year": round(count / max(trading_days, 1) * 252.0, 2),
        "median_cost": round(float(np.median(cost)), 4),
        "b0_take_all_gross": round(float(gross.sum()), 1),
        "b0_take_all_net": round(float(net.sum()), 1),
        "b0_net_per_event": round(float(net.mean()), 4),
        "b1_take_skip_net": round(float(take_skip.sum()), 1),
        "b1_net_per_event": round(float(take_skip.mean()), 4),
        "b1_taken": int((net > 0).sum()),
        "b2_perfect_side_net": round(float(perfect_side.sum()), 1),
        "b2_net_per_event": round(float(perfect_side.mean()), 4),
        "b3_selection_net": round(selection["net"], 1),
        "b3_net_per_event": round(selection["net_per_event"], 4),
        "b3_selected": selection["selected"],
        "max_drawdown": round(float((equity - np.maximum.accumulate(equity)).min()), 1),
        "b1_tail_share_top10_days": round(_tail_share(events["ts"], take_skip), 4),
        "b3_top10_day_share": round(
            _tail_share(
                events["ts"],
                np.where(taken, np.maximum(net, 0.0), 0.0) if taken is not None else take_skip * 0,
            ),
            4,
        ),
    }


def _average(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean over the phases, skipping the cells a phase could not produce."""
    out: dict[str, Any] = {}
    for key in rows[0]:
        if not isinstance(rows[0][key], int | float):
            continue
        values = [r[key] for r in rows if np.isfinite(r[key])]
        out[key] = float(np.mean(values)) if values else float("nan")
    return out


def _pool(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-pair rows pooled to the per-pair mean the programme reports in."""
    if not rows:
        return {"pairs": 0}
    keys = [k for k in rows[0] if isinstance(rows[0][k], int | float)]
    pooled: dict[str, Any] = {}
    for key in keys:
        values = [r[key] for r in rows if np.isfinite(r[key])]
        pooled[key] = round(float(np.mean(values)), 4) if values else None
    pooled["pairs"] = len(rows)
    pooled["pairs_b0_positive"] = int(sum(1 for r in rows if r["b0_take_all_net"] > 0))
    pooled["pairs_b3_positive"] = int(sum(1 for r in rows if r["b3_selection_net"] > 0))
    return pooled


def panel_bounds(
    panel: dict[str, pd.DataFrame],
    *,
    trading_days: int,
    horizons: tuple[int, ...],
    thresholds: tuple[float, ...],
    cost_multipliers: tuple[float, ...] = (1.0,),
    phases: int = 4,
) -> dict[str, dict[str, Any]]:
    """Every event population on one panel, at every cost level, in one pass.

    The feature basis is built once per pair and the events once per population;
    a cost multiplier only shifts `net` by a constant, so both levels come out of
    the same arrays.
    """
    per_pair: dict[str, dict[str, list[dict[str, Any]]]] = {f"x{m}": {} for m in cost_multipliers}

    def record(population: str, multiplier: float, row: dict[str, Any] | None) -> None:
        if row is not None:
            per_pair[f"x{multiplier}"].setdefault(population, []).append(row)

    for frame in panel.values():
        built = basis(frame)
        for horizon in horizons:
            collected: dict[float, list[dict[str, Any]]] = {m: [] for m in cost_multipliers}
            for phase in range(phases):
                events = horizon_events(
                    built, horizon=horizon, phase=phase * max(1, horizon // phases)
                )
                for multiplier in cost_multipliers:
                    row = bounds(
                        built, events, trading_days=trading_days, cost_multiplier=multiplier
                    )
                    if row:
                        collected[multiplier].append(row)
            #: phase-averaged, so the non-overlapping grid is not one UTC hour
            for multiplier, rows in collected.items():
                if rows:
                    record(
                        f"horizon_{horizon}",
                        multiplier,
                        _average(rows),
                    )
        for k in thresholds:
            events = anchor_events(built, retrace.find_anchors(frame, k))
            for multiplier in cost_multipliers:
                record(
                    f"anchor_{k}",
                    multiplier,
                    bounds(built, events, trading_days=trading_days, cost_multiplier=multiplier),
                )

    return {
        level: {population: _pool(rows) for population, rows in populations.items()}
        for level, populations in per_pair.items()
    }


def noise_reference(
    *, pairs: int = 8, length: int = 40_000, horizons: tuple[int, ...] = (4, 48), seed: int
) -> dict[str, Any]:
    """The amendment's evidence: what the bounds return on a pure random walk.

    A generated walk has no structure at all. Whatever B-1 and B-2 report here is
    what perfect foresight extracts from noise, and any gate they can pass on
    noise is a gate that cannot reject.
    """
    rng = np.random.default_rng(seed)
    panel = {f"W{i:02d}": nulls.random_walk_frame(length, rng) for i in range(pairs)}
    return {
        "fixture": "IID Gaussian random walk, generated",
        "pairs": pairs,
        "bars_per_pair": length,
        "bounds": panel_bounds(
            panel, trading_days=length // 96, horizons=horizons, thresholds=(), phases=2
        )["x1.0"],
        "note": (
            "B-1 and B-2 are large here because max(net, 0) over a symmetric "
            "distribution is about 0.4 sigma_q whatever produced it. A gate read "
            "off them is passed by noise"
        ),
    }


def signal_reference(
    *,
    pairs: int = 6,
    length: int = 30_000,
    horizons: tuple[int, ...] = (4, 48),
    decay: float = 0.99,
    seed: int,
) -> dict[str, Any]:
    """The positive control: B-3 must find a structure that really is there.

    `noise_reference` shows B-3 returning exactly zero on a random walk, which is
    the right answer but is also what a broken selector returns.

    The control is an **Ornstein–Uhlenbeck level** — the price itself reverts,
    with a half-life of about 69 bars — rather than an AR(1) on returns. An AR(1)
    with `φ = −0.3` was tried first and is the wrong control: a single lag-1 term
    largely cancels inside a `q`-bar block, so fading blocks does not pay under it
    and take-all stays negative. That is the same arithmetic Round B′ ran into,
    and it would have made an inert selector look correct.
    """
    rng = np.random.default_rng(seed)
    panel: dict[str, pd.DataFrame] = {}
    for index in range(pairs):
        base = nulls.random_walk_frame(length, rng)
        innovations = rng.normal(0.0, 1.0, length)
        level = np.empty(length)
        level[0] = 0.0
        for position in range(1, length):
            level[position] = decay * level[position - 1] + innovations[position]
        frame = nulls._rebuild(base, np.diff(level))
        #: a small cost, so a real effect is not hidden by the spread
        frame["roundtrip_cost"] = 0.2
        panel[f"S{index:02d}"] = frame
    return {
        "fixture": f"Ornstein-Uhlenbeck level, decay={decay}, 0.2 pip round trip, generated",
        "pairs": pairs,
        "bars_per_pair": length,
        "bounds": panel_bounds(
            panel, trading_days=length // 96, horizons=horizons, thresholds=(), phases=2
        )["x1.0"],
        "note": (
            "a fade rule pays here by construction, so B-3 returning zero would "
            "mean the selector is inert rather than that the panels are empty"
        ),
    }


BOUND_KEYS: tuple[str, ...] = (
    "b0_net_per_event",
    "b1_net_per_event",
    "b2_net_per_event",
    "b3_net_per_event",
)


def null_referenced(
    panel: dict[str, pd.DataFrame],
    *,
    trading_days: int,
    horizons: tuple[int, ...],
    thresholds: tuple[float, ...],
    draws: int,
    seed: int,
    cost_multipliers: tuple[float, ...] = (1.0,),
) -> dict[str, Any]:
    """Every bound beside the same bound on the matched null, at every cost level.

    The decisive quantity is `b3_net_per_event` minus its null value: the part of
    an in-sample linear selector's take that is attributable to structure rather
    than to fitting a design matrix to noise. B-1 and B-2 are `DESCRIPTIVE_ONLY`
    and are reported beside it.
    """
    real = panel_bounds(
        panel,
        trading_days=trading_days,
        horizons=horizons,
        thresholds=thresholds,
        cost_multipliers=cost_multipliers,
    )
    rng = np.random.default_rng(seed)
    samples: list[dict[str, dict[str, Any]]] = []
    for _ in range(draws):
        shuffled = {p: nulls.n2_sign_flip(f, rng) for p, f in panel.items()}
        samples.append(
            panel_bounds(
                shuffled,
                trading_days=trading_days,
                horizons=horizons,
                thresholds=thresholds,
                cost_multipliers=cost_multipliers,
            )
        )

    out: dict[str, Any] = {}
    for level, populations in real.items():
        out[level] = {}
        for population, row in populations.items():
            drawn = [
                s[level][population]
                for s in samples
                if population in s.get(level, {}) and s[level][population].get("pairs")
            ]
            if not drawn or not row.get("pairs"):
                out[level][population] = {"real": row, "null": None}
                continue
            stats: dict[str, Any] = {}
            for key in BOUND_KEYS:
                values = [d[key] for d in drawn if key in d]
                if not values:
                    continue
                mean, sd = float(np.mean(values)), float(np.std(values))
                stats[key] = {
                    "real": row[key],
                    "null_mean": round(mean, 5),
                    "null_sd": round(sd, 5),
                    "real_minus_null": round(row[key] - mean, 5),
                    "studentized": round((row[key] - mean) / sd, 3) if sd > 0 else None,
                }
            out[level][population] = {"real": row, "null": stats, "draws": len(drawn)}
    return out


__all__ = [
    "CLASSIFICATION",
    "FEATURE_NAMES",
    "anchor_events",
    "bounds",
    "horizon_events",
    "noise_reference",
    "null_referenced",
    "panel_bounds",
]
