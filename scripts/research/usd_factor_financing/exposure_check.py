# ruff: noqa: E501 -- check prose
"""実際の M15 / M16 の score を、**合成の return** の上で修正版の book に通し、exposure を確かめる。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**実際の FX return は使わない**（signal-blind）。panel からは日付 index だけを取る。
mechanism redesign の欠陥は、この種の確認を alpha の前に 1 度も走らせなかったから通り抜けた。
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.acquisition_safety import write_provenance
from scripts.research.mechanism_redesign import signals
from scripts.research.top_five import panel
from scripts.research.usd_factor_financing import book, execute

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/usd_factor_financing/exposure_check.json"


def _synthetic(index: pd.DatetimeIndex, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        rng.normal(0, 0.005, (len(index), 8)), index=index, columns=list(signals.CURRENCIES)
    )
    return frame.sub(frame.mean(axis=1), axis=0)


def run() -> dict[str, Any]:
    warnings.filterwarnings("ignore")
    rows: dict[str, Any] = {}
    for span, maker in (("long", panel.long_span_panel), ("recent", panel.recent_span_panel)):
        index = maker()["currency_excess_return"].index
        synthetic = _synthetic(index, seed=7)
        built = {span: {"currency_excess_return": pd.DataFrame(index=index)}}
        for track in ("M15", "M16"):
            scores = signals.scores_for(track, built, span)
            for label, rebalance in (
                ("old_band_rebalance", None),
                ("factor_rebalance", book.factor_rebalance),
            ):
                kwargs = {} if rebalance is None else {"rebalance": rebalance}
                daily = book.run_book(execute._config(), scores, synthetic, 252.0, **kwargs)[
                    "daily"
                ]
                x = daily[[f"x_{c}" for c in signals.CURRENCIES]]
                foreign = x[[f"x_{c}" for c in signals.FOREIGN]]
                gross = x.abs().sum(axis=1).replace(0.0, np.nan)
                rows[f"{track}_{span}_{label}"] = {
                    "days": len(daily),
                    "currencies_ever_zero_after_first_trade": [
                        c for c in signals.FOREIGN if (x[f"x_{c}"].iloc[5:].abs() < 1e-12).any()
                    ],
                    "currencies_always_zero": [
                        c for c in signals.FOREIGN if (x[f"x_{c}"].abs() < 1e-12).all()
                    ],
                    "foreign_legs_equal": bool(
                        np.allclose(foreign.to_numpy(), foreign.to_numpy()[:, [0]], atol=1e-10)
                    ),
                    "usd_share_of_gross_mean": round(float((x["x_USD"].abs() / gross).mean()), 4),
                    "sum_zero_max_abs": float(x.sum(axis=1).abs().max()),
                    "usd_sign_matches_signal": bool(
                        (
                            np.sign(x["x_USD"])
                            == np.sign(
                                scores["USD"]
                                .reindex(pd.DatetimeIndex(daily["decision_day"]))
                                .to_numpy()
                            )
                        ).mean()
                        > 0.99
                    ),
                }
    return {
        "returns_used": "SYNTHETIC_ONLY（seed 7）。実際の FX return は使っていない",
        "rows": rows,
    }


def main() -> int:
    payload = run()
    written = write_provenance(RECORD, payload)
    for key, row in payload["rows"].items():
        print(key, row, file=sys.stderr)
    print(f"written {RECORD} {written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
