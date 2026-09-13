"""From an expected-return vector to traded deltas, costs and portfolio P&L.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The chain, one function per link, each testable on synthetic inputs:

    mu (8,)  ->  scores  ->  PC1-neutral scores  ->  capped sum-zero weights (gross 1)
             ->  band rebalance of the held book     ->  volatility-targeted exposure
             ->  traded currency delta               ->  cost on the delta only
             ->  next-day P&L of the held exposure

Units, stated once so they cannot drift
---------------------------------------

* A **currency weight** `x_c` is a fraction of capital held in currency `c`
  against the equally weighted basket of the other currencies, implemented in
  pairs by the corpus's own equal split (`split_map`). Weights sum to zero.
* **Currency gross** is `sum|x|`. The measured volatility of a gross-1 book is
  377.7 bp a year; leverage is currency gross per unit of capital.
* **Pair gross notional** is `sum|split_map @ x|` — the notional actually held in
  pairs. Reported beside currency gross, never substituted for it.
* **P&L**: `x_t . r_{t+1}` with `r` the currency excess return. Because
  `sum x = 0`, this is identically the P&L of the equal-split pair book
  `(split_map @ x_t) . r_pair_{t+1}` — a test measures the identity.
* **Cost**: every day, `sum|x_t - x_{t-1}| x 1.703 bp` of capital. That is the
  3.406 bp basket round trip charged once per unit of *turnover*
  (`sum|delta| / 2`), under Track 2's conservative isolated-position routing
  ratio of 1.32. The faithful cost of the equal-split book is measured beside it
  (`implementation_cost`) and is never the primary charge.

What is charged
---------------

Only the delta. A daily forecast that moves the target a little moves the held
book a little, and nothing is closed and reopened. No per-signal, per-prediction
or per-pair round trip exists anywhere in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.continuous_portfolio import CHARGED_ONE_WAY_BP, PAIR_ROUNDTRIP_BP
from scripts.research.model_learning import CURRENCIES_G10, PAIRS_20

CURRENCIES: Final[tuple[str, ...]] = tuple(sorted(CURRENCIES_G10))


# -------------------------------------------------------------- pair topology
def split_map(
    pairs: tuple[str, ...] = PAIRS_20, currencies: tuple[str, ...] = CURRENCIES
) -> np.ndarray:
    """`(pairs x currencies)` map from currency weights to the equal-split pair book.

    Currency `c` is observed as the mean of its signed pair returns, so one unit
    of `x_c` is `1/n_c` of pair notional on each of `c`'s pairs, long where `c`
    is the base and short where it is the quote.
    """
    counts = {c: sum(c in pair.split("_") for pair in pairs) for c in currencies}
    matrix = np.zeros((len(pairs), len(currencies)))
    for row, pair in enumerate(pairs):
        base, quote = pair.split("_")
        matrix[row, currencies.index(base)] = 1.0 / counts[base]
        matrix[row, currencies.index(quote)] = -1.0 / counts[quote]
    return matrix


# ------------------------------------------------------------------- mappings
def linear_scores(mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    del sigma
    return mu - mu.mean()


def vol_normalized_scores(mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """`mu / sigma`, demeaned. The pre-registered primary mapping."""
    safe = np.where(sigma > 0, sigma, np.nan)
    scores = mu / safe
    scores = np.where(np.isfinite(scores), scores, 0.0)
    return scores - scores.mean()


def rank_scores(mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    del sigma
    ranks = pd.Series(mu).rank(method="average").to_numpy()
    return ranks - ranks.mean()


MAPPINGS: Final[dict[str, Any]] = {
    "vol_normalized": vol_normalized_scores,
    "linear": linear_scores,
    "rank": rank_scores,
}


# --------------------------------------------------------- factor neutrality
def leading_factor(returns_window: np.ndarray) -> np.ndarray:
    """First principal direction of a trailing window of currency excess returns.

    The window must end at the decision day. Demeaned and unit-length, so
    removing it preserves the sum-zero constraint.
    """
    if returns_window.shape[0] < 2:
        return np.zeros(returns_window.shape[1])
    cov = np.cov(returns_window, rowvar=False)
    values, vectors = np.linalg.eigh(cov)
    vector = vectors[:, int(np.argmax(values))]
    vector = vector - vector.mean()
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


def neutralize(scores: np.ndarray, factor: np.ndarray) -> np.ndarray:
    """Remove the scores' projection on the factor, then re-centre."""
    if not np.any(factor):
        return scores - scores.mean()
    out = scores - (scores @ factor) * factor
    return out - out.mean()


# ------------------------------------------------------------ capped weights
def _fill_side(magnitudes: np.ndarray, total: float, cap: float) -> np.ndarray:
    """Proportional allocation of `total` across `magnitudes`, no entry above `cap`."""
    out = np.zeros_like(magnitudes)
    active = magnitudes > 0
    remaining = total
    for _ in range(len(magnitudes) + 1):
        if remaining <= 1e-15 or not active.any():
            break
        share = magnitudes[active] / magnitudes[active].sum() * remaining
        over = share > cap - out[active] + 1e-15
        if not over.any():
            out[active] += share
            break
        indices = np.flatnonzero(active)[over]
        remaining -= float((cap - out[indices]).sum())
        out[indices] = cap
        active[indices] = False
    return out


def capped_weights(scores: np.ndarray, cap: float) -> np.ndarray:
    """Sum-zero weights of gross at most 1 with `|w_c| <= cap`.

    Each side (long, short) is filled to 0.5 proportionally to its scores, with
    the cap enforced by water-filling. When a side cannot reach 0.5 under the cap
    both sides are held to the smaller achievable total, so the book stays
    sum-zero and its gross falls below 1 rather than breaking the constraint.
    """
    centred = scores - scores.mean()
    positive = np.clip(centred, 0.0, None)
    negative = np.clip(-centred, 0.0, None)
    capacity = min(0.5, cap * int((positive > 0).sum()), cap * int((negative > 0).sum()))
    if capacity <= 0:
        return np.zeros_like(scores)
    return _fill_side(positive, capacity, cap) - _fill_side(negative, capacity, cap)


# ------------------------------------------------------------- band rebalance
def band_rebalance(target: np.ndarray, held: np.ndarray, band: float) -> np.ndarray:
    """Trade only currencies whose gap exceeds `band`, keeping the book sum-zero.

    The traded set's net is spread back over the traded set. When exactly one
    currency breaches the band, the currency with the largest opposite gap is
    traded as its counter-leg — otherwise the restoration would cancel the only
    trade and the book could never move.
    """
    gap = target - held
    if band <= 0:
        return target.copy()
    mask = np.abs(gap) > band
    if not mask.any():
        return held.copy()
    if mask.sum() == 1:
        main = int(np.flatnonzero(mask)[0])
        opposite = -np.sign(gap[main]) * gap
        opposite[main] = -np.inf
        mask[int(np.argmax(opposite))] = True
    trade = np.where(mask, gap, 0.0)
    trade[mask] -= trade.sum() / mask.sum()
    return held + trade


# ----------------------------------------------------------- volatility target
@dataclass(slots=True)
class VolTargeter:
    """Past-only leverage to a volatility target, with hysteresis and a cap."""

    target_vol: float
    max_leverage: float
    hysteresis: float
    held: float | None = None

    def update(self, ex_ante_vol: float) -> float:
        if not np.isfinite(ex_ante_vol) or ex_ante_vol <= 0:
            wanted = self.held if self.held is not None else 0.0
        else:
            wanted = min(self.target_vol / ex_ante_vol, self.max_leverage)
        if self.held is None or self.held == 0.0 or abs(wanted / self.held - 1.0) > self.hysteresis:
            self.held = wanted
        return float(self.held)


# ---------------------------------------------------------------------- cost
def charged_cost(delta: np.ndarray, cost_multiple: float = 1.0) -> float:
    """Fraction of capital: `sum|delta| x 1.703 bp`, the conservative convention."""
    return float(np.abs(delta).sum()) * CHARGED_ONE_WAY_BP * cost_multiple / 10_000.0


def implementation_cost(delta: np.ndarray, pair_map: np.ndarray) -> float:
    """Faithful cost of the equal-split pair book: pair one-way x half a round trip."""
    return float(np.abs(pair_map @ delta).sum()) * (PAIR_ROUNDTRIP_BP / 2.0) / 10_000.0


# ---------------------------------------------------------------- the book
@dataclass(frozen=True, slots=True)
class BookConfig:
    """Every free choice of one book, declared in full."""

    name: str
    mapping: str = "vol_normalized"
    neutralize_leading_factor: bool = True
    weight_cap: float = 0.25
    band: float = 0.10
    vol_target: float | None = 0.10
    max_leverage: float = 5.0
    leverage_hysteresis: float = 0.10
    cost_multiple: float = 1.0
    sigma_window: int = 60
    factor_window: int = 120
    vol_window: int = 60
    drawdown_governor: bool = False
    governor_trigger: float = 0.10
    governor_release: float = 0.05
    governor_scale: float = 0.5
    notes: tuple[str, ...] = field(default_factory=tuple)


def run_book(
    config: BookConfig,
    mu: pd.DataFrame,
    excess: pd.DataFrame,
    days_per_year: float,
) -> dict[str, Any]:
    """Run one book over the days `mu` covers.

    `mu` is `day x currency`, one row per decision day. `excess` is the full
    daily currency excess-return panel; every quantity used on day `t` is taken
    from rows `<= t`, and the P&L of the exposure chosen on day `t` is the
    return of day `t+1`.
    """
    currencies = list(CURRENCIES)
    mu = mu[currencies]
    returns = excess[currencies]
    index = returns.index
    positions = {day: index.get_loc(day) for day in mu.index}
    pair_map = split_map()
    mapping = MAPPINGS[config.mapping]

    targeter = (
        VolTargeter(config.vol_target, config.max_leverage, config.leverage_hysteresis)
        if config.vol_target is not None
        else None
    )
    held = np.zeros(len(currencies))
    exposure_prev = np.zeros(len(currencies))
    equity = 0.0
    peak = 0.0
    governor_on = False

    rows: list[dict[str, Any]] = []
    for day in mu.index:
        loc = positions[day]
        if loc + 1 >= len(index):
            break
        history = returns.iloc[: loc + 1].to_numpy()
        sigma = np.nanstd(history[-config.sigma_window :], axis=0, ddof=0)
        raw = mapping(mu.loc[day].to_numpy(dtype=float), sigma)
        scores = raw
        if config.neutralize_leading_factor:
            factor = leading_factor(history[-config.factor_window :])
            scores = neutralize(raw, factor)
        target = capped_weights(scores, config.weight_cap)
        held = band_rebalance(target, held, config.band)

        leverage = 1.0
        ex_ante = float("nan")
        if targeter is not None:
            window = history[-config.vol_window :]
            cov = np.cov(window, rowvar=False)
            ex_ante = float(np.sqrt(max(held @ cov @ held, 0.0) * days_per_year))
            leverage = targeter.update(ex_ante)
        scale = config.governor_scale if (config.drawdown_governor and governor_on) else 1.0
        exposure = held * leverage * scale

        delta = exposure - exposure_prev
        cost = charged_cost(delta, config.cost_multiple)
        faithful = implementation_cost(delta, pair_map)
        next_day = index[loc + 1]
        realised = returns.iloc[loc + 1].to_numpy()
        contributions = exposure * realised
        gross = float(contributions.sum())
        net = gross - cost

        equity += net
        peak = max(peak, equity)
        drawdown = equity - peak
        if config.drawdown_governor:
            if not governor_on and drawdown < -config.governor_trigger:
                governor_on = True
            elif governor_on and drawdown > -config.governor_release:
                governor_on = False

        rows.append(
            {
                "decision_day": day,
                "pnl_day": next_day,
                "gross": gross,
                "cost": cost,
                "implementation_cost": faithful,
                "net": net,
                "currency_gross": float(np.abs(exposure).sum()),
                "pair_gross": float(np.abs(pair_map @ exposure).sum()),
                "one_way_traded": float(np.abs(delta).sum()),
                "leverage": leverage * scale,
                "ex_ante_vol": ex_ante,
                "traded": bool(np.abs(delta).sum() > 0),
                "raw_target_corr": _corr(raw, scores),
                **{f"x_{c}": float(v) for c, v in zip(currencies, exposure, strict=True)},
                **{f"pnl_{c}": float(v) for c, v in zip(currencies, contributions, strict=True)},
            }
        )
        exposure_prev = exposure

    frame = pd.DataFrame(rows).set_index("pnl_day")
    return {"config": config, "daily": frame}


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


# ----------------------------------------------------- signal-free calibration
def band_calibration(
    bands: tuple[float, ...] = (0.0, 0.05, 0.08, 0.10, 0.15),
    *,
    half_life_days: float = 20.0,
    days: int = 252 * 60,
    seed: int = 20260914,
) -> dict[str, Any]:
    """Turnover and alpha capture of `band_rebalance` on synthetic AR(1) targets.

    The pre-registration chose its band here, before any model existed: the
    #480 mechanics measured capture 0.958 for an unconstrained per-currency band
    of 0.10; the implementable sum-zero version, with a counter-leg when only one
    currency breaches, reaches 0.958 at the same band. No price, return or signal
    enters.
    """
    rho = 0.5 ** (1.0 / half_life_days)
    innovation = np.sqrt(1.0 - rho * rho)
    rows: dict[str, Any] = {}
    for band in bands:
        rng = np.random.default_rng(seed)
        state = rng.standard_normal(len(CURRENCIES))
        held: np.ndarray | None = None
        one_way = 0.0
        dot_ht = 0.0
        dot_tt = 0.0
        for _ in range(days):
            state = rho * state + innovation * rng.standard_normal(len(CURRENCIES))
            target = state - state.mean()
            target = target / np.abs(target).sum()
            if held is None:
                held = target.copy()
                continue
            new = band_rebalance(target, held, band)
            one_way += float(np.abs(new - held).sum())
            held = new
            dot_ht += float(held @ target)
            dot_tt += float(target @ target)
        rows[f"band_{band:g}"] = {
            "annual_turnover": round(one_way / 2.0 / days * 252.0, 2),
            "alpha_capture": round(dot_ht / dot_tt, 4),
        }
    return {"half_life_days": half_life_days, "rows": rows}


__all__ = [
    "CURRENCIES",
    "MAPPINGS",
    "BookConfig",
    "VolTargeter",
    "band_calibration",
    "band_rebalance",
    "capped_weights",
    "charged_cost",
    "implementation_cost",
    "leading_factor",
    "linear_scores",
    "neutralize",
    "rank_scores",
    "run_book",
    "split_map",
    "vol_normalized_scores",
]
