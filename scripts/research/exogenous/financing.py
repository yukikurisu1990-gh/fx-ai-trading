"""Stage D — is broker-realizable financing obtainable without an account?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The Economic Edge package priced carry off central-bank **policy rates**, which
is the coarsest rung of its own source hierarchy. The question here is not
whether carry can be made to work — it is one number: how far is that proxy from
what a broker would actually pay?

This module **probes**; it does not log in. Every candidate is requested exactly
as an anonymous client, the response is recorded, and a source that answers with
a login wall, a token requirement or a paid tier is written down as such and
left alone. Entering a credential is a hard boundary in the plan and no result
would justify crossing it.

What "materially more favourable" means was fixed before the probe
------------------------------------------------------------------

Plan §9: financing must improve the non-JPY bloc's net by more than
`CARRY_REOPEN_PIPS` per pair per panel — about five times the `+4.2 / +4.0` that
bloc actually earned — before carry may be reopened at all. Equal or worse closes
the family. The threshold exists so that a marginally better financing number
cannot be used to reopen a question the decomposition already answered.
"""

from __future__ import annotations

import datetime as dt
import ssl
import urllib.error
import urllib.request
from typing import Any, Final

import certifi

_CONTEXT: Final[ssl.SSLContext] = ssl.create_default_context(cafile=certifi.where())
_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "close",
}

#: Candidate, what it would give, and why it is on the list. Ordered by the
#: plan's source hierarchy: broker actuals first, then swap points, then a
#: public proxy for either.
CANDIDATES: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "oanda_financing_rates_us",
        "https://www.oanda.com/us-en/trading/financing-rates/",
        "current per-pair long/short financing rates as advertised",
    ),
    (
        "oanda_financing_rates_global",
        "https://www.oanda.com/bvi-en/cfds/financing-rates/",
        "same, on the non-US entity",
    ),
    (
        "oanda_v20_developer",
        "https://developer.oanda.com/rest-live-v20/account-ep/",
        "the REST endpoint that carries realised financing per trade",
    ),
    (
        "oanda_historical_rates_page",
        "https://www.oanda.com/currency-converter/en/historical-rates/",
        "any historical rate archive published without an account",
    ),
    (
        "cme_fx_settlements",
        "https://www.cmegroup.com/markets/fx/g10/euro-fx.settlements.html",
        "futures settlements, from which a forward basis could be implied",
    ),
    (
        "bis_effective_exchange_rates",
        "https://data.bis.org/static/bulk/WS_EER_csv_flat.zip",
        "a BIS bulk file, checked for any forward or swap-point series",
    ),
)


def probe() -> dict[str, Any]:
    """One anonymous GET per candidate. No credential, no account, no token."""
    results: list[dict[str, Any]] = []
    for name, url, purpose in CANDIDATES:
        record: dict[str, Any] = {"name": name, "url": url, "purpose": purpose}
        try:
            request = urllib.request.Request(url, headers=_HEADERS)  # noqa: S310 - fixed https
            with urllib.request.urlopen(request, timeout=90, context=_CONTEXT) as response:  # noqa: S310
                body = response.read(400_000)
                text = body.decode("utf-8", "replace").lower()
                record["status"] = int(response.status)
                record["bytes"] = len(body)
                record["content_type"] = response.headers.get("Content-Type")
                record.update(
                    {
                        "mentions_login": any(
                            token in text for token in ("sign in", "log in", "login")
                        ),
                        "mentions_api_token": "token" in text or "api key" in text,
                        "mentions_history": "historical" in text or "history" in text,
                        #: A *word* is not a data archive. The positive branch
                        #: requires a machine-readable payload as well, so a
                        #: marketing page that happens to say "historical"
                        #: cannot flip the verdict to "publicly available".
                        "is_data_payload": any(
                            token in (record.get("content_type") or "").lower()
                            for token in ("csv", "json", "zip", "excel", "spreadsheet")
                        ),
                    }
                )
        except urllib.error.HTTPError as exc:
            record.update({"status": int(exc.code), "error": exc.reason})
        except Exception as exc:  # noqa: BLE001 - a probe records its failure
            record.update({"status": None, "error": f"{type(exc).__name__}: {exc}"})
        results.append(record)

    reachable_history = [
        row
        for row in results
        if row.get("status") == 200
        and row.get("mentions_history")
        and row.get("is_data_payload")
        and not row.get("mentions_login")
        and not row.get("mentions_api_token")
    ]
    return {
        "probed_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "candidates": results,
        "public_financing_history_found": bool(reachable_history),
        "status": (
            "BROKER_FINANCING_HISTORY_PUBLICLY_AVAILABLE"
            if reachable_history
            else "BROKER_REALIZABLE_CARRY_NOT_SUPPORTED_FINANCING_HISTORY_NOT_PUBLIC"
        ),
        "carry_family": (
            "CARRY_FAMILY_REMAINS_CLOSED_PENDING_FINANCING_HISTORY"
            if not reachable_history
            else "CARRY_FAMILY_REOPENING_TEST_REQUIRED"
        ),
        "route_if_needed": (
            "OANDA publishes realised financing per trade through the v20 REST "
            "account endpoints, which require an account and an API token. That "
            "is a hard boundary in this plan: the route is reported, not taken."
        ),
        "proxy_gap_already_measured": (
            "The Economic Edge package measured the policy-rate proxy against "
            "public overnight money for USD, EUR and GBP: mean gap -0.0406, "
            "-0.0797 and -0.0513 percentage points a year, correlations above "
            "0.9997. That bounds the money-market half of the gap and says "
            "nothing about a broker's markup."
        ),
    }


__all__ = ["CANDIDATES", "probe"]
