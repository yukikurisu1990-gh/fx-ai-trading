# ruff: noqa: E501 -- source URLs
"""Fetch the pre-2016 FX and CPI series T-V declared. Network only on opt-in.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    VALUATION_ACQUIRE_APPROVED=1 python -m scripts.research.valuation.acquire

Importing this module fetches nothing; running it without the opt-in fetches
nothing. Every request carries a server-side period bound that ends before the
protected fresh pool begins, and **every parsed frame is checked against that
bound before it is written**: a server that ignored `endPeriod` produces a
refusal and no file, not a local filter that quietly trims the extra rows. The
distinction is the whole of the ruling's section 25 — a download that contained
protected observations would be a read of them even if nothing downstream used
them.

Each series is normalised to the publishing body's own observation dates. No
resampling, no interpolation, no forward fill: what was not published stays
missing, and the development run measures the holes rather than filling them.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.acquisition_safety import (
    NETWORK_FAILURES,
    require_opt_in,
    write_provenance,
)
from scripts.research.valuation import DATA_DIR, RECORD_DIR, prereg, sources

OPT_IN_ENV: Final[str] = "VALUATION_ACQUIRE_APPROVED"
#: committed provenance の置き換えは、取得の許可とは別の act として扱う。
OVERWRITE_ENV: Final[str] = "VALUATION_PROVENANCE_OVERWRITE_APPROVED"
USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36"
)


class ProtectedDataError(RuntimeError):
    """A download reached the protected span. Nothing is kept and nothing is used."""


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,application/vnd.sdmx.data+csv,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    # network に触れる直前ごとに確認する。`acquire()` の入口にも check はあるが、
    # それを消す mutation 1 つで全 fetch が無防備になったのが事故の起点だった。
    require_opt_in(OPT_IN_ENV, what="fetch over the network")
    try:
        with urllib.request.urlopen(
            request, timeout=180, context=ssl.create_default_context()
        ) as response:
            return response.read()
    except NETWORK_FAILURES as error:
        # 本物の通信失敗だけが fallback に落ちる。guard が投げた AcquisitionRefusedError は
        # ここに入らず呼び出し元へ抜ける — 「拒否」が「失敗したので次を試す」に
        # 化けていたのが事故の 2 つめの穴だった。
        blob = _fetch_via_curl(url)
        if blob is None:
            raise RuntimeError(f"{url}: {type(error).__name__}: {error}") from error
        return blob


def _fetch_via_curl(url: str) -> bytes | None:
    # conftest の socket guard は Python の socket を patch しているだけなので、
    # **子プロセスの curl は見えない**。事故で網を抜けたのがこの route なので、
    # ここは自分で許可を確認する。
    require_opt_in(OPT_IN_ENV, what="fetch over the network via curl")
    binary = shutil.which("curl")
    if binary is None:  # pragma: no cover - environment dependent
        return None
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "payload"
        result = subprocess.run(  # noqa: S603 - fixed binary, no shell
            [binary, "-fsS", "-L", "--max-time", "180", "-A", USER_AGENT, "-o", str(out), url],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0 or not out.exists() or out.stat().st_size == 0:
            return None
        return out.read_bytes()


def _text(blob: bytes) -> io.StringIO:
    return io.StringIO(blob.decode("utf-8-sig", errors="replace"))


def _observations(blob: bytes) -> pd.DataFrame:
    """SDMX CSV from either body: the period column and the observation column."""
    table = pd.read_csv(_text(blob), dtype=str)
    period = next(c for c in table.columns if c.upper() in {"TIME_PERIOD", "TIME_PERIOD:PERIOD"})
    value = next(c for c in table.columns if c.upper() in {"OBS_VALUE", "OBS_VALUE:OBSERVATION"})
    frame = pd.DataFrame(
        {
            "period": table[period].astype(str).str.strip(),
            "value": pd.to_numeric(table[value], errors="coerce"),
        }
    )
    return frame.dropna().drop_duplicates("period").sort_values("period").reset_index(drop=True)


def guard(frame: pd.DataFrame, *, label: str) -> None:
    """Refuse anything that reaches the protected span, whatever the server did.

    The maximum observation, not the last row: a response that arrived unsorted, or
    that a future parser stops sorting, must not be able to hide a protected date
    behind an earlier final row.
    """
    if frame.empty:
        raise RuntimeError(f"{label}: the response carried no observations")
    periods = frame["period"].astype(str)
    widths = set(periods.str.len())
    if len(widths) != 1 or widths.pop() not in (7, 10):
        raise ProtectedDataError(
            f"{label}: the response mixes period formats or uses an unexpected one; "
            "a bound that cannot be compared is not a bound, so nothing is kept"
        )
    furthest = str(periods.max())
    bound = sources.PROTECTED_FROM[: len(furthest)]
    if furthest >= bound:
        raise ProtectedDataError(
            f"{label}: the response reaches {furthest}, at or past the protected span at {bound}; "
            "nothing is kept"
        )


def acquire() -> dict[str, Any]:
    #: the opt-in is checked here and not only in `main`, so importing this module and
    #: calling the function is not a way around it
    if os.environ.get(OPT_IN_ENV) != "1":
        raise RuntimeError(f"refused: set {OPT_IN_ENV}=1 to acquire")
    root = Path(__file__).resolve().parents[3]
    data = root / DATA_DIR
    data.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "track": "T-V",
        "acquired_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "exclusion": dict(sources.EXCLUSION),
        "requested_span": dict(prereg.SPAN),
        "protected_span_first_day": sources.PROTECTED_FROM,
        "fx": {},
        "cpi": {},
        "unreachable": {},
    }

    for kind, series_list, url_of in (
        ("fx", sources.FX, sources.fx_url),
        ("cpi", sources.CPI, sources.cpi_url),
    ):
        for series in series_list:
            label = f"{kind}:{series.currency}"
            url = url_of(series)
            #: the write lives in the `else` clause, so it is reachable only when the
            #: guard raised nothing. A `try/except/continue` shape would let a later
            #: edit to the handler fall through into `to_parquet` with a refused frame
            try:
                blob = _fetch(url)
                frame = _observations(blob)
                guard(frame, label=label)
            except ProtectedDataError:
                raise
            except Exception as error:  # noqa: BLE001 - a refused source is a recorded fact
                record["unreachable"][label] = {
                    "body": series.body,
                    "url": url,
                    "reason": f"{type(error).__name__}: {error}"[:400],
                }
                continue
            else:
                path = data / f"{kind}_{series.currency.lower()}.parquet"
                frame.to_parquet(path, index=False)
            record[kind][series.currency] = {
                "body": series.body,
                "key": series.key,
                "url": url,
                "rows": int(len(frame)),
                "first": str(frame["period"].iloc[0]),
                "last": str(frame["period"].iloc[-1]),
                "file": str(path.relative_to(root)).replace("\\", "/"),
                "sha256_of_normalised_csv": hashlib.sha256(
                    frame.to_csv(index=False).encode("utf-8")
                ).hexdigest(),
                "bytes_fetched": len(blob),
                "sha256_of_payload": hashlib.sha256(blob).hexdigest(),
                "note": series.note,
            }

    #: a run that acquired nothing is a failed run, not a provenance record. Writing
    #: one would overwrite the record of the acquisition that did happen, which is the
    #: evidence that the freeze preceded the read
    if not record["fx"] and not record["cpi"]:
        raise RuntimeError(
            "no series was acquired; the existing record is left untouched. "
            f"unreachable: {sorted(record['unreachable'])}"
        )
    out = root / RECORD_DIR
    out.mkdir(parents=True, exist_ok=True)
    #: 既存の committed provenance を黙って置き換えない。同一内容なら no-op、
    #: 内容が違えば拒否する — 新しい観測は新しいファイルに書くのが本 repo の規約で、
    #: 事故ではここが無条件の write_text だったために記録が失われた。
    write_provenance(
        out / "acquisition.json",
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        overwrite=os.environ.get(OVERWRITE_ENV) == "1",
        env_name=OVERWRITE_ENV,
    )
    return record


def main() -> int:
    if os.environ.get(OPT_IN_ENV) != "1":
        print(f"refused: set {OPT_IN_ENV}=1 to acquire (public pre-2016 sources only)")
        return 2
    record = acquire()
    for kind in ("fx", "cpi"):
        for currency, block in record[kind].items():
            print(f"{kind} {currency}: {block['rows']} rows, {block['first']} .. {block['last']}")
    for label, block in record["unreachable"].items():
        print(f"unreachable {label}: {block['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
