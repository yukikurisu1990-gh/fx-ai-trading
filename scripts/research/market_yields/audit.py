"""Run the integrity, availability and coverage audit, and fix the universe.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.market_yields.audit

The only FX information this stage uses is the **trading calendar** — which UTC
days the seen corpus has bars for — because coverage has to be measured against
the days a decision could be taken. No price, return or spread enters, and no
signal exists yet.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.market_yields import CURRENCIES, DATA_DIR, RECORD_DIR, integrity, sources
from scripts.research.model_learning import SEEN_SPANS

ROOT: Final[Path] = Path(__file__).resolve().parents[3]


def trading_calendar() -> pd.DatetimeIndex:
    """UTC days the seen corpus can decide on, from the committed corpus provenance."""
    from scripts.research.model_learning import corpus as corpus_module

    panel = corpus_module.currency_panel()
    return pd.DatetimeIndex(panel["currency_excess_return"].index)


def load(currency: str) -> pd.DataFrame | None:
    path = ROOT / DATA_DIR / f"{currency.lower()}_2y.parquet"
    return pd.read_parquet(path) if path.exists() else None


def build(days: pd.DatetimeIndex) -> dict[str, Any]:
    first, last = str(days[0].date()), str(days[-1].date())
    acquisition = json.loads((ROOT / RECORD_DIR / "acquisition.json").read_text(encoding="utf-8"))
    rows: dict[str, Any] = {}
    for currency in CURRENCIES:
        frame = load(currency)
        source = sources.by_currency(currency)
        if frame is None:
            rows[currency] = {
                "source": source.body,
                "acquired": False,
                "decision_grade": False,
                "reasons": [
                    acquisition["unreachable"].get(currency, {}).get("reason", "not acquired")
                ],
            }
            continue
        audit = integrity.audit_series(frame, first, last)
        leak = integrity.leak_check(frame, days)
        audit["publication_days_per_fx_trading_day"] = round(audit["rows_in_span"] / len(days), 4)
        result = integrity.verdict(audit, len(days), leak)
        rows[currency] = {
            "source": source.body,
            "series": source.series,
            "maturity": source.maturity,
            "publication_time": source.publication_time,
            "timezone": source.timezone,
            "acquired": True,
            **audit,
            **result,
            "leak_check": leak,
        }
    universe = tuple(c for c in CURRENCIES if rows[c].get("decision_grade"))
    cross_check = load("EUR_ECB_CROSS_CHECK")
    eur = load("EUR")
    comparison: dict[str, Any] = {}
    if cross_check is not None and eur is not None:
        merged = (
            eur.rename(columns={"yield_percent": "bundesbank"})
            .merge(cross_check.rename(columns={"yield_percent": "ecb"}), on="date")
            .query("@pd.Timestamp(@first) <= date <= @pd.Timestamp(@last)")
        )
        difference = (merged["bundesbank"] - merged["ecb"]).abs()
        comparison = {
            "overlapping_days": int(len(merged)),
            "level_correlation": round(float(merged["bundesbank"].corr(merged["ecb"])), 4),
            "mean_absolute_difference_pp": round(float(difference.mean()), 4),
            "max_absolute_difference_pp": round(float(difference.max()), 4),
            "daily_change_correlation": round(
                float(merged["bundesbank"].diff().corr(merged["ecb"].diff())), 4
            ),
            "five_day_change_correlation": round(
                float(merged["bundesbank"].diff(5).corr(merged["ecb"].diff(5))), 4
            ),
            "bundesbank_rounding_pp": 0.01,
            "reading": (
                "the two euro-area sources agree almost exactly on the level but much less on the "
                "one-day change: different end-of-day snapshots, and the Bundesbank series is "
                "published to 0.01pp. A one-day repricing measure is therefore source-dependent, "
                "which is one reason the pre-registered lookback is five days rather than one"
            ),
        }
    return {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "decision_span": {"first": first, "last": last, "fx_trading_days": int(len(days))},
        "seen_spans": SEEN_SPANS,
        "gate": integrity.GATE,
        "availability_rule": (
            "publication times are unconfirmed on every source page, so a yield dated d may only "
            f"inform a position taken {integrity.AVAILABILITY_LAG_TRADING_DAYS} trading day later"
        ),
        "currencies": rows,
        "decision_grade_universe": list(universe),
        "excluded": {c: rows[c].get("reasons", []) for c in CURRENCIES if c not in universe},
        "eur_cross_check_bundesbank_vs_ecb": comparison,
        "market_data_read": "the seen corpus trading calendar only; no price, return or spread",
    }


def main() -> int:
    days = trading_calendar()
    record = build(days)
    out = ROOT / RECORD_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "integrity.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"decision span {record['decision_span']}")
    for currency, row in record["currencies"].items():
        mark = "OK " if row.get("decision_grade") else "NO "
        print(f"{mark}{currency}: {row.get('reasons') or row.get('availability_on_decision_days')}")
    print("universe:", record["decision_grade_universe"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
