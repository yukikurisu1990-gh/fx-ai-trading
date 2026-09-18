"""The fast five-day books re-run through the universe-closed layer.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.market_yields.fast_repair_check

#485's verdict stands as recorded. This re-runs the same frozen fast signal
through the repaired construction — nothing else changes, no parameter is
touched — so that the repair is shown not to have been the reason the fast
formulation failed, and so that T-R2 starts from a layer whose behaviour on a
restricted universe is known.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import pandas as pd

from scripts.research.market_yields import RECORD_DIR, development, portfolio, prereg


def run() -> dict[str, Any]:
    from scripts.research.model_learning import corpus as corpus_module

    universe = list(prereg.UNIVERSE)
    panel = corpus_module.currency_panel()
    excess_all = panel["currency_excess_return"]
    days = pd.DatetimeIndex(excess_all.index)
    frames = {
        currency: pd.read_parquet(
            development.ROOT / development.DATA_DIR / f"{currency.lower()}_2y.parquet"
        )
        for currency in universe
    }
    yield_panel = development.lagged_yield_panel(frames, days)
    excess = excess_all[universe]
    scores = development.build_scores(yield_panel, excess, development.LOOKBACK)

    books: dict[str, Any] = {}
    for name, score in scores.items():
        usable = development._neutralise_within_universe(score, excess).dropna(how="any")
        result = portfolio.run_book(development.BOOK, usable, excess, universe=universe)
        outside = [c for c in result["daily"].columns if c.startswith("x_")]
        books[name] = {
            "summary": development._summary(result),
            "blocks": development._blocks(result),
            "per_currency_gross_pnl": development._per_currency(result),
            "exposure_columns": sorted(outside),
        }

    original = json.loads(
        (development.ROOT / RECORD_DIR / "development.json").read_text(encoding="utf-8")
    )
    comparison = {
        name: {
            "original_gross_sharpe": original["books"][name]["summary"]["gross_sharpe"],
            "repaired_gross_sharpe": books[name]["summary"]["gross_sharpe"],
            "original_net_sharpe": original["books"][name]["summary"]["net_sharpe"],
            "repaired_net_sharpe": books[name]["summary"]["net_sharpe"],
            "original_turnover": original["books"][name]["summary"][
                "turnover_round_trips_per_year_per_unit_gross"
            ],
            "repaired_turnover": books[name]["summary"][
                "turnover_round_trips_per_year_per_unit_gross"
            ],
        }
        for name in books
    }
    routing = portfolio.routing_profile(prereg.UNIVERSE)
    return {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "purpose": (
            "a robustness re-run of the frozen fast five-day signal through the universe-closed "
            "layer. It does not replace #485's verdict and no parameter was changed"
        ),
        "repair": portfolio.REPAIR,
        "universe": universe,
        "tradable_pairs": list(routing.pairs),
        "pair_gross_per_unit_currency_gross": routing.pair_gross_per_unit_currency_gross,
        "routing_connects_the_universe": routing.connected,
        "books": books,
        "against_the_recorded_run": comparison,
        "verdict_unchanged": original["verdict"],
        "protected_spans_read": False,
    }


def main() -> int:
    record = run()
    path = development.ROOT / RECORD_DIR / "fast_repaired.json"
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    for name, row in record["against_the_recorded_run"].items():
        print(
            f"{name}: gross {row['original_gross_sharpe']:+.3f}"
            f" -> {row['repaired_gross_sharpe']:+.3f}"
            f" | net {row['original_net_sharpe']:+.3f} -> {row['repaired_net_sharpe']:+.3f}"
            f" | turnover {row['original_turnover']} -> {row['repaired_turnover']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
