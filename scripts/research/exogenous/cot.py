"""The COT branch — speculative positioning as an expected-return source.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Reached under plan §15 Route D: the macro surprise family was obtainable and
produced no edge, so the next candidate expected-return source is tested. Unlike
the macro family this one is genuinely multi-currency — the CFTC publishes
positioning for all seven non-USD currencies `PAIRS_20` spans — so it is the
first directional family in this package that the breadth rule does not kill in
advance.

The timing is the whole risk
----------------------------

A COT report is **as of Tuesday** and **published the following Friday at 15:30
America/New York**. Using it from Tuesday is a three-day look-ahead and would
manufacture an edge out of nothing. Every position here opens at the first M15
bar starting after **Friday 20:30 UTC**, which is the later of the two daylight
conversions taken unconditionally, so the conversion can never be optimistic.

Two economic claims, each committed to one sign
------------------------------------------------

Plan §17 fixes the signs before any return was computed:

* `net_level`, `net_percentile`, `net_extreme` — **contrarian**. Speculative
  positioning at an extreme is a position that has to be unwound.
* `net_change` — **momentum**. A change in positioning is flow that has not
  finished.

A signal whose measured sign is the opposite is **dropped, not flipped**.

What is deliberately not done
------------------------------

No cross-sectional `k` grid, no threshold sweep, no alternative trader category,
no alternative normalisation. Four signals and two horizons is the entire search,
fixed in the plan. Overlapping four-week holds are evaluated as independent
events, each paying its own round trip — which overstates cost and overstates
sample size, and both are reported rather than corrected away.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Final

import certifi
import numpy as np
import pandas as pd

from scripts.research.exogenous import (
    BREADTH_SHARE,
    COT_EXTREME_LOWER,
    COT_EXTREME_UPPER,
    COT_HORIZON_DAYS,
    COT_PERCENTILE_WEEKS,
    COT_PUBLICATION_SAFETY_DAYS,
    COT_PUBLICATION_UTC_HOUR,
    COT_PUBLICATION_UTC_MINUTE,
    COT_SIGNS,
    NULL_DRAWS,
    SEED,
    TAIL_SHARE_CEILING,
)

_CONTEXT: Final[ssl.SSLContext] = ssl.create_default_context(cafile=certifi.where())
_HEADERS: Final[dict[str, str]] = {"User-Agent": "fx-ai-trading-research/1.0"}

SOCRATA: Final[str] = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"

#: Contract name -> currency. Six sit in the CURRENCY subgroup; NZ DOLLAR sits in
#: CURRENCY(NON-MAJOR), which plan amendment A-2 records. USD has no contract of
#: its own here and is constructed in `currency_scores`.
CONTRACTS: Final[dict[str, str]] = {
    "AUSTRALIAN DOLLAR": "AUD",
    "BRITISH POUND": "GBP",
    "CANADIAN DOLLAR": "CAD",
    "EURO FX": "EUR",
    "JAPANESE YEN": "JPY",
    "SWISS FRANC": "CHF",
    "NZ DOLLAR": "NZD",
}
NON_USD: Final[tuple[str, ...]] = tuple(sorted(set(CONTRACTS.values())))


def _get(url: str, *, attempts: int = 4) -> tuple[bytes, dict[str, Any]]:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers=_HEADERS)  # noqa: S310 - fixed https
            with urllib.request.urlopen(request, timeout=300, context=_CONTEXT) as response:  # noqa: S310
                payload = response.read()
                return payload, {
                    "url": url,
                    "status": int(response.status),
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "attempts": attempt,
                    "acquired_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if attempt < attempts:
                time.sleep(3.0 * attempt)
    raise RuntimeError(f"could not acquire {url}: {last}")


def acquire(*, start: str, end: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Weekly leveraged-money positioning for the seven currencies.

    One request per contract, filtered server-side by report date. The response
    is the *Traders in Financial Futures* report; `lev_money` is the speculative
    category and `open_interest_all` normalises it so a contract whose size grew
    over the sample does not read as a positioning trend.
    """
    rows: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    for contract, currency in sorted(CONTRACTS.items()):
        query = urllib.parse.urlencode(
            {
                "$select": (
                    "report_date_as_yyyy_mm_dd,open_interest_all,"
                    "lev_money_positions_long,lev_money_positions_short"
                ),
                "$where": (
                    f"contract_market_name='{contract}' "
                    f"and report_date_as_yyyy_mm_dd>='{start}T00:00:00.000' "
                    f"and report_date_as_yyyy_mm_dd<='{end}T00:00:00.000'"
                ),
                "$order": "report_date_as_yyyy_mm_dd",
                "$limit": "5000",
            }
        )
        payload, record = _get(f"{SOCRATA}?{query}")
        parsed = json.loads(payload)
        record.update({"contract": contract, "currency": currency, "rows": len(parsed)})
        provenance.append(record)
        for row in parsed:
            interest = float(row.get("open_interest_all") or 0.0)
            if not interest:
                continue
            long_ = float(row.get("lev_money_positions_long") or 0.0)
            short = float(row.get("lev_money_positions_short") or 0.0)
            rows.append(
                {
                    "report_date": row["report_date_as_yyyy_mm_dd"][:10],
                    "currency": currency,
                    "net_level": (long_ - short) / interest,
                    "open_interest": interest,
                }
            )

    frame = pd.DataFrame(rows)
    wide = frame.pivot(index="report_date", columns="currency", values="net_level").sort_index()
    weekdays = {dt.date.fromisoformat(value).weekday() for value in wide.index}
    return wide, {
        "contracts": provenance,
        "weeks": int(len(wide)),
        "currencies": sorted(wide.columns),
        "report_weekdays": sorted(weekdays),
        "report_is_always_tuesday": weekdays == {1},
        "field": "lev_money_positions_long - lev_money_positions_short, over open_interest_all",
        "as_of": "Tuesday",
        "published": "the following Friday, 15:30 America/New_York",
        "revision": (
            "the CFTC republishes a report only on a stated correction; the "
            "as-of date is not restated, so a row is keyed by its Tuesday"
        ),
    }


def currency_scores(levels: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The four pre-registered signals, per currency, with USD constructed.

    Every window is backward-looking and includes the current week, which is
    known at publication. `net_percentile` ranks the current value inside the
    trailing `COT_PERCENTILE_WEEKS`; a version that ranked inside the whole
    sample would put the future into every early week.
    """
    level = levels[list(NON_USD)].astype(float)
    change = level.diff()
    percentile = level.rolling(COT_PERCENTILE_WEEKS, min_periods=COT_PERCENTILE_WEEKS // 2).apply(
        lambda window: float((window <= window[-1]).mean()), raw=True
    )
    extreme = pd.DataFrame(0.0, index=level.index, columns=level.columns)
    extreme[percentile > COT_EXTREME_UPPER] = 1.0
    extreme[percentile < COT_EXTREME_LOWER] = -1.0
    extreme[percentile.isna()] = np.nan

    out: dict[str, pd.DataFrame] = {
        "net_level": level,
        "net_change": change,
        "net_percentile": percentile - 0.5,
        "net_extreme": extreme,
    }
    for name, table in out.items():
        #: Plan §17: USD has no leveraged-money contract, so it is the negative
        #: of the equally-weighted mean of the other seven. A pre-registered
        #: construction, not a fitted one.
        table["USD"] = -table[list(NON_USD)].mean(axis=1)
        out[name] = table
    return out


def publication_timestamp(
    report_date: str, *, safety_days: int = COT_PUBLICATION_SAFETY_DAYS
) -> dt.datetime:
    """The moment the report is certainly public, in UTC.

    The nominal release is the Friday of the report week at 15:30
    America/New_York. 20:30 UTC is that time under standard time and an hour
    later under daylight time, so taking it unconditionally can never be
    optimistic about the clock.

    It can still be optimistic about the *day*: a federal holiday later in the
    report week delays the release by one business day while the as-of date
    stays Tuesday, and the report carries no release timestamp to detect that.
    `safety_days` (plan amendment A-3) waits three calendar days past the
    nominal Friday. That is at or after every **one-business-day** holiday
    delay, which is the delay the CFTC applies for a federal holiday in the
    report week — and under standard time the margin is exactly fifteen
    minutes, because entry is the first bar *strictly after* 20:30 UTC. It does
    **not** cover a multi-day suspension, and the report carries no release
    timestamp from which one could be detected. Passing `safety_days=0`
    reproduces the pre-amendment Friday entry and exists only for the
    timing-sensitivity diagnostic.
    """
    day = dt.date.fromisoformat(report_date)
    friday = day + dt.timedelta(days=(4 - day.weekday()) % 7)
    return dt.datetime.combine(
        friday + dt.timedelta(days=safety_days),
        dt.time(COT_PUBLICATION_UTC_HOUR, COT_PUBLICATION_UTC_MINUTE),
        tzinfo=dt.UTC,
    )


def week_moves(
    frames: dict[str, pd.DataFrame],
    report_dates: list[str],
    *,
    horizon: str,
    safety_days: int = COT_PUBLICATION_SAFETY_DAYS,
) -> dict[str, list[dict[str, Any]]]:
    """Per pair and week: the base-direction move and the cost of taking it.

    The move is separated from the signal on purpose. The price side is fixed
    once and the signal side is permuted 200 times against it, which is what
    makes the null a statement about the signal rather than about the calendar.
    """
    days = COT_HORIZON_DAYS[horizon]
    out: dict[str, list[dict[str, Any]]] = {}
    for pair, frame in sorted(frames.items()):
        times = frame["ts"].reset_index(drop=True)
        close = frame["mid_c"].reset_index(drop=True)
        open_ = frame["mid_o"].reset_index(drop=True)
        spread = frame["spread_close_pips"].reset_index(drop=True)
        pip = float(frame["pip_size"].iloc[0])
        rows: list[dict[str, Any]] = []
        for report_date in report_dates:
            stamp = pd.Timestamp(publication_timestamp(report_date, safety_days=safety_days))
            entry = int(times.searchsorted(stamp, side="right"))
            if entry >= len(times) or times.iloc[entry] - stamp > pd.Timedelta(days=3):
                continue
            exit_stamp = times.iloc[entry] + pd.Timedelta(days=days)
            exit_index = int(times.searchsorted(exit_stamp, side="left"))
            if exit_index >= len(close):
                continue
            rows.append(
                {
                    "report_date": report_date,
                    "entry_utc": times.iloc[entry].isoformat(),
                    "move_pips": (float(close.iloc[exit_index]) - float(open_.iloc[entry])) / pip,
                    "cost_pips": float(spread.iloc[entry]) + 0.5,
                    "held_days": float(
                        (times.iloc[exit_index] - times.iloc[entry]) / pd.Timedelta(days=1)
                    ),
                }
            )
        out[pair] = rows
    return out


def _pair_positions(scores: pd.DataFrame, pair: str, signal: str) -> pd.Series:
    base, quote = pair.split("_")
    if base not in scores.columns or quote not in scores.columns:
        return pd.Series(dtype=float)
    spread = scores[base] - scores[quote]
    return COT_SIGNS[signal] * np.sign(spread)


def evaluate(
    moves: dict[str, list[dict[str, Any]]], scores: pd.DataFrame, *, signal: str
) -> list[dict[str, Any]]:
    """Apply one signal's pre-registered sign to the fixed price side."""
    rows: list[dict[str, Any]] = []
    for pair, entries in moves.items():
        positions = _pair_positions(scores, pair, signal)
        if positions.empty:
            continue
        for entry in entries:
            position = positions.get(entry["report_date"])
            if position is None or not np.isfinite(position) or position == 0.0:
                continue
            gross = float(position) * entry["move_pips"]
            rows.append(
                {
                    "pair": pair,
                    "report_date": entry["report_date"],
                    "position": float(position),
                    "gross_pips": gross,
                    "cost_pips": entry["cost_pips"],
                    "net_pips": gross - entry["cost_pips"],
                    "held_days": entry["held_days"],
                }
            )
    return rows


def summarise(
    moves: dict[str, list[dict[str, Any]]],
    scores: pd.DataFrame,
    *,
    signal: str,
    draws: int = NULL_DRAWS,
    seed: int = SEED,
) -> dict[str, Any]:
    """Plan §20's reporting set, with a null that permutes the signal weeks.

    The null shuffles whole **weeks** of the score table against the unchanged
    price side, so the cross-sectional structure inside a week survives and only
    the alignment between positioning and the subsequent move is destroyed.
    """
    rows = evaluate(moves, scores, signal=signal)
    if not rows:
        return {"events": 0}

    frame = pd.DataFrame(rows)
    gross = frame["gross_pips"].to_numpy(dtype=float)
    per_pair = {
        pair: {
            "events": int(len(block)),
            "gross_mean": float(block["gross_pips"].mean()),
            "net_mean": float(block["net_pips"].mean()),
        }
        for pair, block in frame.groupby("pair")
    }
    statistic = float(np.mean(gross) / (np.std(gross, ddof=1) / np.sqrt(len(gross))))

    rng = np.random.default_rng(seed)
    null_statistics: list[float] = []
    null_means: list[float] = []
    #: A **circular shift** of the whole score table, not a free permutation of
    #: week labels. A currency sits above its 90th percentile for runs of
    #: consecutive weeks and the four-week holds overlap, so a free permutation
    #: scatters those runs: in the null the overlapping windows carry
    #: near-independent signs and partly cancel, while in the data they add
    #: coherently. That makes a free permutation anti-conservative. A circular
    #: shift preserves the serial persistence exactly and the within-week cross
    #: section exactly, and moves only the alignment with the price side.
    values_matrix = scores.to_numpy()
    offsets = rng.permutation(np.arange(1, len(scores)))[:draws]
    for offset in offsets:
        shuffled = pd.DataFrame(
            np.roll(values_matrix, int(offset), axis=0),
            index=scores.index,
            columns=scores.columns,
        )
        drawn = evaluate(moves, shuffled, signal=signal)
        if not drawn:
            continue
        values = np.array([row["gross_pips"] for row in drawn], dtype=float)
        null_statistics.append(
            float(np.mean(values) / (np.std(values, ddof=1) / np.sqrt(len(values))))
        )
        null_means.append(float(np.mean(values)))
    extreme = sum(1 for value in null_statistics if abs(value) >= abs(statistic))
    p_value = (extreme + 1) / (len(null_statistics) + 1) if null_statistics else None

    #: Plan §13's clause, as the plan defines it and as the previous package
    #: implemented it: the ten largest events over the **net** total, negatives
    #: included. A first version divided the top ten by the sum of the POSITIVE
    #: gross only, which at this sample size returns roughly the value pure
    #: noise would give and therefore cannot fail. Both are recorded so the size
    #: of that substitution is visible.
    net_total = float(frame["net_pips"].sum())
    top_ten = float(np.sort(gross)[-10:].sum())
    tail = float(top_ten / net_total) if net_total else None
    positive = [float(value) for value in gross if value > 0]
    tail_positive_only = (
        float(sum(sorted(positive, reverse=True)[:10]) / sum(positive))
        if positive and sum(positive)
        else None
    )

    #: Plan §16 criterion 9 — "no worse than a simple baseline". The baseline is
    #: unconditional long over exactly the same event set, which is the
    #: simplest rule that takes the same trades at the same times. A first
    #: version of this package claimed the criterion was met without measuring
    #: it.
    baseline = [entry["move_pips"] for entries in moves.values() for entry in entries]
    #: Plan §16 criterion 7 — "more than one currency". The USD score is a
    #: continuous mean of the other seven and is essentially never zero, so a
    #: USD pair takes a position in almost every week in which anything is
    #: extreme, whether or not its own non-USD leg is. Reporting the two halves
    #: separately is the only way that criterion can be read honestly.
    has_usd = frame["pair"].str.contains("USD")
    interval = (
        [
            float(np.mean(gross) - 1.96 * np.std(null_means, ddof=1)),
            float(np.mean(gross) + 1.96 * np.std(null_means, ddof=1)),
        ]
        if len(null_means) > 1
        else None
    )
    return {
        "signal": signal,
        "sign": COT_SIGNS[signal],
        "baseline_unconditional_long_pips": float(np.mean(baseline)) if baseline else None,
        "usd_leg_events": int(has_usd.sum()),
        "usd_leg_gross_mean_pips": (
            float(frame.loc[has_usd, "gross_pips"].mean()) if bool(has_usd.any()) else None
        ),
        "non_usd_leg_events": int((~has_usd).sum()),
        "non_usd_leg_gross_mean_pips": (
            float(frame.loc[~has_usd, "gross_pips"].mean()) if bool((~has_usd).any()) else None
        ),
        "gross_mean_ci95_pips": interval,
        "events": int(frame["report_date"].nunique()),
        "pair_events": int(len(frame)),
        "pairs": len(per_pair),
        "gross_mean_pips": float(np.mean(gross)),
        "cost_mean_pips": float(frame["cost_pips"].mean()),
        "net_mean_pips": float(frame["net_pips"].mean()),
        "net_mean_pips_double_cost": float(
            np.mean(gross - 2.0 * frame["cost_pips"].to_numpy(dtype=float))
        ),
        "gross_t": statistic,
        "permutation_p": p_value,
        "null_statistics": null_statistics,
        "hit_rate": float((gross > 0).mean()),
        "pairs_gross_positive": sum(1 for value in per_pair.values() if value["gross_mean"] > 0),
        "pairs_net_positive": sum(1 for value in per_pair.values() if value["net_mean"] > 0),
        "mean_held_days": float(frame["held_days"].mean()),
        "tail_share_of_net": tail,
        "tail_share_of_positive_gross_diagnostic": tail_positive_only,
        #: Plan §13: when a family is dropped for absence of effect, say what the
        #: design could have detected. The dispersion comes from the **null
        #: distribution of the mean**, not from an i.i.d. standard error: the
        #: pairs share currency legs and the four-week holds overlap, so an
        #: i.i.d. standard error understates the spread by the same factor that
        #: makes the naive `t` misleading, and a power figure built on it would
        #: flatter the design in exactly the place this package criticises the
        #: `t`. 2.802 is z(0.975) + z(0.80). The i.i.d. figure is kept beside it
        #: so the size of that mistake is visible rather than asserted.
        "detectable_at_80pct_power_pips": (
            float(2.802 * np.std(null_means, ddof=1)) if len(null_means) > 1 else None
        ),
        "detectable_at_80pct_power_pips_iid": float(
            2.802 * np.std(gross, ddof=1) / np.sqrt(len(gross))
        ),
        "null_mean_sd_pips": (float(np.std(null_means, ddof=1)) if len(null_means) > 1 else None),
        "per_pair": per_pair,
    }


def family_max_p(cells: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Westfall–Young family-max over the eight cells, on the shared draws.

    Each draw contributes its largest `|t|` across the cells; a cell's corrected
    `p` is the share of draws whose family maximum reaches that cell's observed
    `|t|`. Correcting each cell on its own null would report eight independent
    tests as if only one had been run.
    """
    usable = {name: cell for name, cell in cells.items() if cell.get("null_statistics")}
    if not usable:
        return {}
    widths = {len(cell["null_statistics"]) for cell in usable.values()}
    #: Westfall-Young needs draw b to be the SAME draw in every cell. A cell
    #: that skipped a draw would shorten and shift its list, and positional
    #: indexing would then silently pair draw b of one cell with draw b+1 of
    #: another. Fail closed rather than truncate.
    if len(widths) != 1:
        return {}
    width = widths.pop()
    maxima = [
        max(abs(cell["null_statistics"][index]) for cell in usable.values())
        for index in range(width)
    ]
    out: dict[str, Any] = {}
    for name, cell in usable.items():
        observed = abs(cell["gross_t"])
        extreme = sum(1 for value in maxima if value >= observed)
        out[name] = (extreme + 1) / (len(maxima) + 1)
    return out


def verdict(
    per_panel: dict[str, dict[str, dict[str, Any]]],
    deciding: tuple[str, ...],
    *,
    min_events: int,
    corrected: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Plan §13, read mechanically off the artifacts. Every clause fails closed."""
    rows = [per_panel[panel] for panel in deciding if panel in per_panel]
    complete = len(rows) == len(deciding) and bool(rows)

    surviving: list[str] = []
    dropped: dict[str, list[str]] = {}
    names = sorted({key for panel in rows for key in panel}) if complete else []
    for name in names:
        cells = [panel.get(name) for panel in rows]
        reasons: list[str] = []
        if any(cell is None or not cell.get("events") for cell in cells):
            reasons.append("CELL_MISSING")
        else:
            if min(cell["events"] for cell in cells) < min_events:
                reasons.append("TOO_FEW_EVENTS")
            gross = [cell["gross_mean_pips"] for cell in cells]
            if len({int(np.sign(value)) for value in gross}) > 1:
                reasons.append("PANEL_SIGN_REVERSAL")
            if all(value <= 0 for value in gross):
                reasons.append("NO_GROSS_EFFECT")
            if any(cell["net_mean_pips"] <= 0 for cell in cells):
                reasons.append("NEGATIVE_AFTER_COST")
            if any(cell["pairs_gross_positive"] < BREADTH_SHARE * cell["pairs"] for cell in cells):
                reasons.append("INSUFFICIENT_BREADTH")
            tails = [cell.get("tail_share_of_net") for cell in cells]
            if any(value is not None and value > TAIL_SHARE_CEILING for value in tails):
                reasons.append("TAIL_ABOVE_CEILING")
            adjusted = [
                corrected.get(panel, {}).get(name) for panel in deciding if panel in per_panel
            ]
            if any(value is None or value >= 0.05 for value in adjusted):
                reasons.append("FAMILYWISE_NULL")
        if reasons:
            dropped[name] = sorted(set(reasons))
        else:
            surviving.append(name)

    return {
        "status": ("COT_EDGE_NOT_SUPPORTED" if not surviving else "COT_EDGE_SUPPORTED_EXPLORATORY"),
        "complete": complete,
        "cells_tested": len(names),
        "surviving": surviving,
        "dropped": dropped,
        "note": (
            "Signs are pre-registered per signal. A signal whose measured sign "
            "is the opposite of its hypothesis is dropped, never flipped."
        ),
    }


__all__ = [
    "CONTRACTS",
    "NON_USD",
    "SOCRATA",
    "acquire",
    "currency_scores",
    "evaluate",
    "family_max_p",
    "publication_timestamp",
    "summarise",
    "verdict",
    "week_moves",
]
