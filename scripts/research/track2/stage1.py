"""Stage 1 — does a non-USD macro surprise carry a forward relative return?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The hypothesis, fixed in the pre-registration before any return was computed:

> A surprise in a non-USD economy's release carries a **forward** one-day return
> for that currency against a basket of the other G10 currencies.

**Forward**, because the archive's time of day is unusable and only its date
survived Stage 0. Entry is the open of the first bar of the first trading day
**strictly after** the release date, and the exit is that day's close. The
announcement day itself is never traded, so no intraday timestamp defect can
reach a return — and the price of that safety is that the immediate reaction,
where an announcement effect is most likely to live, is deliberately given up.
The hypothesis is correspondingly weaker, and it is the one that was registered.

The target is a currency, not a pair
-------------------------------------

`H-003` lost 96% of its gross to the dollar factor by treating pairs as assets.
The position here is one currency long against the other seven equally, built
through `frontier.SIGNAL_TO_PAIR` — the same construction the clock family used —
so the dollar is inside the basket and cannot be the effect.

Signs come from mechanics and are never read off a result
----------------------------------------------------------

A stronger or more inflationary print is hawkish for that central bank and
appreciates its currency; the two "bad news is a bigger number" series, the
unemployment rate and the claimant count, carry a minus. A measured effect in the
opposite direction **drops** the family. It is never inverted — this programme
came close to re-running a refuted reversal rule as a momentum rule once already.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.clock_flow.frontier import SIGNAL_TO_PAIR
from scripts.research.exploratory_m15 import PAIRS
from scripts.research.feasibility.gate_v2 import Costs, Design, adjudicate
from scripts.research.fxunits import (
    HALF_SPREAD_ADDITION_PIPS,
    POWER_MULTIPLIER,
    pips_to_bp,
)
from scripts.research.round_a import panels as round_a_panels
from scripts.research.track2 import (
    G10,
    NON_USD,
    PANEL_SPANS,
    STATUS_CLOSED,
    STATUS_SKIP,
    STATUS_SUPPORTED,
)

#: The correction Stage 0 identified: the archive's date is one calendar day
#: early. The hour is not identified and is never used.
ARCHIVE_DATE_SHIFT_DAYS: Final[int] = 1

#: Pre-registration §7: three primary cells, selected by a mechanical rule over
#: the archive's own event vocabulary and its own impact label. Not a list of
#: events chosen one by one, which is how an event zoo starts.
FAMILY_PATTERNS: Final[dict[str, tuple[str, ...]]] = {
    "inflation": ("CPI", "Inflation Rate", "HICP"),
    "employment": (
        "Employment Change",
        "Unemployment Rate",
        "Claimant Count Change",
        "Jobs",
        "Employment Cost",
    ),
    "policy_rate": (
        "Cash Rate",
        "Main Refinancing Rate",
        "BOJ Policy Rate",
        "Official Bank Rate",
        "Overnight Rate",
        "SNB Policy Rate",
        "Libor Rate",
    ),
}
#: Names that match a family pattern but are expectations or forecasts rather
#: than a realisation. Excluded by rule, before any return existed.
EXCLUDED_NAME_FRAGMENTS: Final[tuple[str, ...]] = ("Expectations", "Forecast", "Outlook")

#: Pre-registration §6. `+1` is the default for every family; only the two
#: series whose bigger number is bad news carry a minus.
NEGATIVE_SIGN_FRAGMENTS: Final[tuple[str, ...]] = ("Unemployment Rate", "Claimant Count")

#: The archive's own impact label. Used as a mechanical admission rule, never as
#: a weight and never as a filter applied after a result.
HIGH_IMPACT: Final[str] = "High Impact Expected"

NULL_DRAWS: Final[int] = 2000
SEED: Final[int] = 20260911
TAIL_SHARE_CEILING: Final[float] = 0.50
MIN_CURRENCY_BREADTH: Final[int] = 4
FAMILYWISE_ALPHA: Final[float] = 0.05


def _numeric(series: pd.Series) -> np.ndarray:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("K", "e3", regex=False)
        .str.replace("M", "e6", regex=False)
        .str.replace("B", "e9", regex=False)
        .str.replace("T", "e12", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce").to_numpy(dtype=float)


def family_of(event: str) -> str | None:
    if any(fragment in event for fragment in EXCLUDED_NAME_FRAGMENTS):
        return None
    for family, patterns in FAMILY_PATTERNS.items():
        if any(pattern in event for pattern in patterns):
            return family
    return None


def sign_of(event: str) -> int:
    return -1 if any(fragment in event for fragment in NEGATIVE_SIGN_FRAGMENTS) else 1


def events(archive: pd.DataFrame) -> pd.DataFrame:
    """Every admissible non-USD release, with its corrected date and its direction.

    One row per release. The surprise is `actual - forecast`; a row missing
    either, or where they are equal, carries no direction and is dropped — a zero
    surprise is not a signal and must not be traded as one.
    """
    rows = archive[
        archive["Currency"].isin(NON_USD) & (archive["Impact"].astype(str) == HIGH_IMPACT)
    ].copy()
    rows["family"] = rows["Event"].astype(str).map(family_of)
    rows = rows[rows["family"].notna()]
    actual, forecast = _numeric(rows["Actual"]), _numeric(rows["Forecast"])
    usable = np.isfinite(actual) & np.isfinite(forecast) & (actual != forecast)
    rows = rows[usable].copy()
    columns = [
        "Currency",
        "Event",
        "family",
        "surprise",
        "mechanism_sign",
        "direction",
        "release_date",
    ]
    if rows.empty:
        #: An empty admissible set is a legitimate outcome — a family with no
        #: high-impact rows, or a panel span with none — and it used to raise
        #: from a string dtype being multiplied by another string dtype.
        return pd.DataFrame({name: pd.Series(dtype="object") for name in columns})
    rows["surprise"] = actual[usable] - forecast[usable]
    rows["mechanism_sign"] = rows["Event"].astype(str).map(sign_of).astype(int)
    rows["direction"] = np.sign(
        rows["surprise"].to_numpy(dtype=float) * rows["mechanism_sign"].to_numpy(dtype=int)
    ).astype(int)
    corrected = rows["utc"] + pd.Timedelta(days=ARCHIVE_DATE_SHIFT_DAYS)
    rows["release_date"] = [stamp.date() for stamp in corrected]
    return rows[columns]


class PanelDays:
    """Per-pair daily open-to-close returns and round-trip costs, in bp.

    A "day" is a UTC calendar day that the panel actually carries bars for, so a
    weekend or a holiday is absent rather than zero, and the first trading day
    after a Friday release is the following Monday by construction.
    """

    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.returns: dict[str, dict[dt.date, float]] = {}
        self.costs: dict[str, dict[dt.date, float]] = {}
        days: set[dt.date] = set()
        for pair, frame in frames.items():
            stamps = frame["ts"].dt.tz_convert("UTC")
            key = stamps.dt.date
            grouped = frame.assign(_day=key).groupby("_day", sort=True)
            first = grouped.first()
            last = grouped.last()
            entry_open = first["mid_o"].to_numpy(dtype=float)
            exit_close = last["mid_c"].to_numpy(dtype=float)
            with np.errstate(invalid="ignore", divide="ignore"):
                ret = (exit_close - entry_open) / entry_open * 1e4
            half_in = (
                pips_to_bp(
                    first["spread_close_pips"].to_numpy(dtype=float) + HALF_SPREAD_ADDITION_PIPS,
                    first["pip_size"].to_numpy(dtype=float),
                    entry_open,
                )
                / 2.0
            )
            half_out = (
                pips_to_bp(
                    last["spread_close_pips"].to_numpy(dtype=float) + HALF_SPREAD_ADDITION_PIPS,
                    last["pip_size"].to_numpy(dtype=float),
                    exit_close,
                )
                / 2.0
            )
            index = list(first.index)
            self.returns[pair] = dict(zip(index, ret, strict=True))
            self.costs[pair] = dict(zip(index, half_in + half_out, strict=True))
            days.update(index)
        self.days: list[dt.date] = sorted(days)
        self._position = {day: rank for rank, day in enumerate(self.days)}

    def first_day_after(self, date: dt.date) -> dt.date | None:
        position = int(np.searchsorted(np.array(self.days, dtype=object), date, side="right"))
        return self.days[position] if position < len(self.days) else None


def currency_weights(currency: str) -> np.ndarray:
    """Long one currency against the other seven, in pair space.

    Built through the matrix the clock family already uses, so the construction
    is one object with one test rather than a second implementation of the same
    idea. Gross exposure is normalised to two units, as there.
    """
    signal = np.full(len(G10), -1.0 / (len(G10) - 1))
    signal[G10.index(currency)] = 1.0
    signal = signal - signal.mean()
    gross = np.abs(signal).sum()
    signal = 2.0 * signal / gross if gross > 0 else signal
    #: `SIGNAL_TO_PAIR` is indexed by `clock_flow.CURRENCIES`, which is sorted.
    from scripts.research.clock_flow import CURRENCIES

    ordered = np.array([signal[G10.index(c)] for c in CURRENCIES])
    return SIGNAL_TO_PAIR @ ordered


WEIGHTS: Final[dict[str, np.ndarray]] = {c: currency_weights(c) for c in G10}


def measure(days: PanelDays, table: pd.DataFrame, family: str) -> dict[str, Any]:
    """Every event in one family, one observation per currency and release date."""
    rows = table[table["family"] == family]
    grouped = rows.groupby(["Currency", "release_date"], sort=True)["direction"].sum()
    gross: list[float] = []
    cost: list[float] = []
    exposure: list[float] = []
    currencies: list[str] = []
    dates: list[dt.date] = []
    for (currency, release_date), net_direction in grouped.items():
        direction = int(np.sign(net_direction))
        if direction == 0:
            continue
        day = days.first_day_after(release_date)
        if day is None:
            continue
        weights = WEIGHTS[currency]
        returns = np.array([days.returns[pair].get(day, np.nan) for pair in PAIRS])
        costs = np.array([days.costs[pair].get(day, np.nan) for pair in PAIRS])
        present = np.isfinite(returns) & np.isfinite(costs)
        if int(present.sum()) < len(PAIRS) - 2:
            continue
        gross.append(float(direction * np.nansum(weights[present] * returns[present])))
        cost.append(float(np.nansum(np.abs(weights[present]) * costs[present])))
        exposure.append(float(np.nansum(np.abs(weights[present]))))
        currencies.append(currency)
        dates.append(day)
    return {
        "gross": np.array(gross),
        "cost": np.array(cost),
        "exposure": np.array(exposure),
        "currencies": np.array(currencies),
        "dates": np.array(dates, dtype=object),
    }


def _effective_n(cell: dict[str, Any]) -> float:
    """Dependence across currencies, through the estimator the rounds already use.

    Events on the same day share one market, so treating them as independent
    would credit the design with power it does not have.
    """
    gross, currencies, dates = cell["gross"], cell["currencies"], cell["dates"]
    if len(gross) < 3:
        return float(max(len(gross), 1))
    frame = pd.DataFrame({"gross": gross, "currency": currencies, "day": dates})
    wide = frame.pivot_table(index="day", columns="currency", values="gross", aggfunc="sum")
    per_currency = {str(c): wide[c].fillna(0.0) for c in wide.columns}
    if len(per_currency) < 2:
        return float(len(gross))
    effective_currencies = round_a_panels.effective_independent_pairs(per_currency)
    share = min(1.0, effective_currencies / max(len(per_currency), 1))
    return float(max(1.0, len(gross) * share))


def _permutation_p(gross: np.ndarray, dates: np.ndarray, rng: np.random.Generator) -> float:
    """Signs drawn **per day**, so the cross-currency structure inside a day survives."""
    if gross.size == 0:
        return 1.0
    unique = {day: index for index, day in enumerate(sorted(set(dates)))}
    day_index = np.array([unique[day] for day in dates])
    observed = float(np.mean(gross))
    draws = np.empty(NULL_DRAWS)
    for draw in range(NULL_DRAWS):
        flips = rng.choice((-1.0, 1.0), size=len(unique))
        draws[draw] = float(np.mean(gross * flips[day_index]))
    return float((np.sum(np.abs(draws) >= abs(observed)) + 1) / (NULL_DRAWS + 1))


def statistics(cell: dict[str, Any], years: float, rng: np.random.Generator) -> dict[str, Any]:
    gross, cost = cell["gross"], cell["cost"]
    n = int(gross.size)
    if n == 0:
        return {"n_events": 0}
    net = gross - cost
    effective = _effective_n(cell)
    dispersion = float(np.std(gross, ddof=1)) if n > 1 else float("inf")
    #: Concentration by **magnitude**, so it is defined whatever the sign of the
    #: total. A first version divided the ten largest net contributions by the
    #: signed total, which is undefined for a negative family and then read in
    #: the record as a *failed* tail check rather than as an unanswerable one.
    #: `round_a.panels.tail_contributions` makes the same point: reporting only
    #: the best days answers the wrong question for a negative series.
    magnitude = np.abs(net)
    order = np.argsort(magnitude)[::-1]
    concentration = (
        float(np.sum(magnitude[order[:10]]) / np.sum(magnitude)) if np.sum(magnitude) > 0 else None
    )
    total = float(np.sum(net))
    by_currency = {}
    for currency in sorted(set(cell["currencies"].tolist())):
        pick = cell["currencies"] == currency
        by_currency[currency] = {
            "n": int(pick.sum()),
            "net_bp": round(float(np.mean(net[pick])), 4),
        }
    positive = sum(1 for block in by_currency.values() if block["net_bp"] > 0)
    return {
        "n_events": n,
        "effective_n": round(effective, 2),
        "events_per_year": round(n / years, 2),
        "gross_bp": round(float(np.mean(gross)), 4),
        "cost_bp": round(float(np.mean(cost)), 4),
        "net_bp": round(float(np.mean(net)), 4),
        "net_total_bp": round(total, 4),
        "dispersion_bp": round(dispersion, 4),
        "mde_bp": round(float(POWER_MULTIPLIER * dispersion / np.sqrt(effective)), 4),
        "confidence_interval_bp": [
            round(float(np.mean(net) - 1.96 * dispersion / np.sqrt(effective)), 4),
            round(float(np.mean(net) + 1.96 * dispersion / np.sqrt(effective)), 4),
        ],
        "p_value": round(_permutation_p(gross, cell["dates"], rng), 4),
        "currency_breadth": positive,
        "n_currencies": len(by_currency),
        "by_currency": by_currency,
        "tail_share": round(concentration, 4) if concentration is not None else None,
        "sign": int(np.sign(np.mean(net))),
        #: Where the cost comes from. A currency held against a basket is traded
        #: as twenty pairs, so the book turns over more than one unit of notional
        #: and pays for all of it — the composition term the unit audit measured.
        "gross_exposure": round(float(np.mean(cell["exposure"])), 4),
        "per_pair_roundtrip_bp": round(float(np.mean(cost) / np.mean(cell["exposure"])), 4)
        if float(np.mean(cell["exposure"])) > 0
        else None,
    }


def build(archive: pd.DataFrame, loaded: dict[str, dict[str, pd.DataFrame]]) -> dict[str, Any]:
    """Every family, on both deciding panels, adjudicated by Gate v2."""
    table = events(archive)
    rng = np.random.default_rng(SEED)
    per_panel: dict[str, Any] = {}
    for panel, frames in loaded.items():
        days = PanelDays(frames)
        start, end = PANEL_SPANS[panel]
        years = (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days / 365.25
        inside = table[
            (table["release_date"] >= dt.date.fromisoformat(start))
            & (table["release_date"] <= dt.date.fromisoformat(end))
        ]
        per_panel[panel] = {
            "years": round(years, 3),
            "n_admissible_events": int(len(inside)),
            "families": {
                family: statistics(measure(days, inside, family), years, rng)
                for family in FAMILY_PATTERNS
            },
        }
    record: dict[str, Any] = {
        "classification": [
            "NON_DECISION_BEARING_EXPLORATORY_ONLY",
            "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        ],
        "archive_date_shift_days": ARCHIVE_DATE_SHIFT_DAYS,
        "n_admissible_events_total": int(len(table)),
        "panels": per_panel,
    }
    record["gate_v2"] = _gate(per_panel)
    record["verdict"] = _verdict(per_panel, record["gate_v2"])
    return record


def _gate(per_panel: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for family in FAMILY_PATTERNS:
        designs: dict[str, Design] = {}
        costs: list[float] = []
        for panel, block in per_panel.items():
            cell = block["families"][family]
            if not cell.get("n_events"):
                continue
            designs[panel] = Design(
                label=f"{family}:{panel}",
                n_events=cell["n_events"],
                effective_n=min(cell["effective_n"], cell["n_events"]),
                dispersion_bp=cell["dispersion_bp"],
                events_per_year=cell["events_per_year"],
            )
            costs.append(cell["cost_bp"])
        if len(designs) < 2:
            out[family] = {"adjudicated": False, "reason": "fewer than two deciding panels"}
            continue
        out[family] = adjudicate(
            "non_usd_surprise_relative", designs, Costs(roundtrip_bp=float(np.mean(costs)))
        )
    return out


def _verdict(per_panel: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    """The pre-registered success rule, applied family by family."""
    families: dict[str, Any] = {}
    for family in FAMILY_PATTERNS:
        cells = [block["families"][family] for block in per_panel.values()]
        gate_block = gate.get(family, {})
        signs = {cell.get("sign") for cell in cells if cell.get("n_events")}
        p_values = [cell.get("p_value", 1.0) for cell in cells if cell.get("n_events")]
        tails = [cell.get("tail_share") for cell in cells if cell.get("tail_share") is not None]
        breadth = [cell.get("currency_breadth", 0) for cell in cells if cell.get("n_events")]
        checks = {
            "gate_v2_statistical": bool(gate_block.get("gates_passed", {}).get("statistical")),
            "gate_v2_economic": bool(gate_block.get("gates_passed", {}).get("economic")),
            "gate_v2_robustness": bool(gate_block.get("gates_passed", {}).get("robustness")),
            "panels_agree_on_sign": bool(len(signs) == 1 and 0 not in signs),
            "currency_breadth": bool(breadth and min(breadth) >= MIN_CURRENCY_BREADTH),
            "family_wise_evidence": bool(p_values and max(p_values) < FAMILYWISE_ALPHA),
            "tail_not_dominant": bool(tails and max(tails) < TAIL_SHARE_CEILING),
        }
        families[family] = {
            "checks": checks,
            "supported": all(checks.values()),
            #: Reported per family, because the Track-level status is one word and
            #: the families did not all fail for the same reason.
            "decision_grade": bool(checks["gate_v2_statistical"] and checks["gate_v2_robustness"]),
            "net_bp_per_panel": [cell.get("net_bp") for cell in cells],
            "p_value_per_panel": [cell.get("p_value") for cell in cells],
        }
    any_supported = any(block["supported"] for block in families.values())
    decidable = all(
        gate.get(family, {}).get("gates_passed", {}).get("statistical")
        and gate.get(family, {}).get("gates_passed", {}).get("robustness")
        for family in FAMILY_PATTERNS
    )
    if any_supported:
        status = STATUS_SUPPORTED
    elif decidable:
        status = STATUS_CLOSED
    else:
        status = STATUS_SKIP
    return {
        "families": families,
        "every_family_is_decidable": decidable,
        "status": status,
    }


__all__ = [
    "ARCHIVE_DATE_SHIFT_DAYS",
    "FAMILY_PATTERNS",
    "PanelDays",
    "build",
    "currency_weights",
    "events",
    "family_of",
    "measure",
    "sign_of",
    "statistics",
]
