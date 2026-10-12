# ruff: noqa: E501 -- research prose
"""金利の proxy の data の feasibility（指示 §8）。OANDA の account の instrument の一覧（metadata）だけを読む。価格は読まない。

command: python -X utf8 -m scripts.research.rates_anchored_fx.feasibility
"""

from __future__ import annotations

import json
import os
import sys

from dotenv import dotenv_values

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient

KEYWORDS = (
    "B02Y",
    "B05Y",
    "B10Y",
    "B30Y",
    "10YB",
    "SCHATZ",
    "BOBL",
    "BUND",
    "GILT",
    "JGB",
    "T-NOTE",
    "BOND",
    "TNOTE",
)


def main() -> int:
    env = dotenv_values(".env")
    client = OandaAPIClient(
        access_token=str(env["OANDA_ACCESS_TOKEN"]),
        environment=str(env.get("OANDA_ENVIRONMENT") or "practice"),
    )
    items = client.list_account_instruments(str(env["OANDA_ACCOUNT_ID"]))
    keep = [
        {
            k: i.get(k)
            for k in (
                "name",
                "type",
                "displayName",
                "pipLocation",
                "displayPrecision",
                "minimumTradeSize",
                "marginRate",
            )
        }
        for i in items
        if i.get("type") != "CURRENCY"
        and any(w in (i.get("name", "") + i.get("displayName", "")).upper() for w in KEYWORDS)
    ]
    print(
        json.dumps(
            {
                "n_instruments_total": len(items),
                "rate_like": keep,
                "types": sorted({i.get("type") for i in items}),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    os.environ.pop("OANDA_ACCESS_TOKEN", None)
    sys.exit(main())
