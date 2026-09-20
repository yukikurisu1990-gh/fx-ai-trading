# ruff: noqa: E501 -- source URLs
"""Fetch and normalise the official two-year yield series. Network only on opt-in.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    MARKET_YIELDS_ACQUIRE_APPROVED=1 python -m scripts.research.market_yields.acquire

Importing this module fetches nothing. Running it without the opt-in fetches
nothing. Every fetch is a public, key-free, non-FX page; no FX series is ever
requested, because those pages carry values inside protected spans.

Each series is normalised to `date, yield_percent` in the publishing body's own
observation dates — no resampling, no interpolation, no forward fill. What the
body did not publish stays missing, and `integrity.py` measures the holes.
"""

from __future__ import annotations

import contextlib
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
import zipfile
from pathlib import Path
from typing import Any, Final
from xml.etree import ElementTree as ET

import pandas as pd

from scripts.research.acquisition_safety import (
    NETWORK_FAILURES,
    require_opt_in,
    write_provenance,
)
from scripts.research.market_yields import DATA_DIR, RECORD_DIR, sources

OPT_IN_ENV: Final[str] = "MARKET_YIELDS_ACQUIRE_APPROVED"
#: committed provenance の置き換えは、取得の許可とは別の act として扱う。
OVERWRITE_ENV: Final[str] = "MARKET_YIELDS_PROVENANCE_OVERWRITE_APPROVED"
#: Some public statistics sites refuse non-browser agents outright (HTTP 403), so the
#: request looks like a browser. Nothing here is authenticated and nothing is scraped
#: around a paywall: every URL is a published statistics file.
USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36"
)
TREASURY_YEARS: Final[tuple[int, ...]] = tuple(range(2020, 2027))
NS: Final[str] = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/csv,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    # network に触れる直前ごとに確認する。`acquire()` の入口にも check はあるが、
    # それを消す mutation 1 つで全 fetch が無防備になったのが事故の起点だった。
    require_opt_in(OPT_IN_ENV, what="fetch over the network")
    try:
        with urllib.request.urlopen(
            request, timeout=180, context=ssl.create_default_context()
        ) as r:
            return r.read()
    except NETWORK_FAILURES as error:
        # 本物の通信失敗だけが fallback に落ちる。guard が投げた AcquisitionRefusedError は
        # ここに入らず呼び出し元へ抜ける — 「拒否」が「失敗したので次を試す」に
        # 化けていたのが事故の 2 つめの穴だった。
        #: Some sites (RBNZ) refuse urllib's TLS handshake while serving the same public
        #: file to curl. The fallback changes the client, never the URL or the headers.
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
            #: -f so an HTTP error is a failure and not a saved error page
            [binary, "-fsS", "-L", "--max-time", "180", "-A", USER_AGENT, "-o", str(out), url],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0 or not out.exists() or out.stat().st_size == 0:
            return None
        return out.read_bytes()


def _column(ref: str) -> int:
    number = 0
    for char in ref:
        if not char.isalpha():
            break
        number = number * 26 + (ord(char.upper()) - 64)
    return number - 1


def _sheet_rows(book: zipfile.ZipFile, path: str):
    """Rows of one worksheet, without openpyxl: shared strings then streamed cells."""
    shared: list[str] = []
    if "xl/sharedStrings.xml" in book.namelist():
        with book.open("xl/sharedStrings.xml") as handle:
            for _, element in ET.iterparse(handle, events=("end",)):
                if element.tag == f"{NS}si":
                    shared.append("".join(t.text or "" for t in element.iter(f"{NS}t")))
                    element.clear()
    with book.open(path) as handle:
        row: dict[int, Any] = {}
        for _, element in ET.iterparse(handle, events=("end",)):
            if element.tag == f"{NS}c":
                value = element.find(f"{NS}v")
                text: Any = None if value is None else value.text
                if text is not None:
                    if element.get("t") == "s":
                        text = shared[int(text)]
                    else:
                        with contextlib.suppress(ValueError):
                            text = float(text)
                row[_column(element.get("r", "A1"))] = text
                element.clear()
            elif element.tag == f"{NS}row":
                yield row
                row = {}
                element.clear()


def _excel_date(serial: float) -> dt.date:
    return dt.date(1899, 12, 30) + dt.timedelta(days=int(serial))


def _text(blob: bytes) -> io.StringIO:
    """Bytes to text without guessing an encoding: undecodable bytes are replaced."""
    return io.StringIO(blob.decode("utf-8-sig", errors="replace"))


def _frame(pairs: list[tuple[dt.date, float]]) -> pd.DataFrame:
    frame = pd.DataFrame(pairs, columns=["date", "yield_percent"])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)


def parse_treasury(blobs: list[bytes]) -> pd.DataFrame:
    rows: list[tuple[dt.date, float]] = []
    for blob in blobs:
        table = pd.read_csv(_text(blob))
        for _, row in table.iterrows():
            rows.append((pd.to_datetime(row["Date"]).date(), float(row["2 Yr"])))
    return _frame(rows)


def parse_bundesbank(blob: bytes) -> pd.DataFrame:
    table = pd.read_csv(_text(blob), skiprows=8, header=None, names=["date", "value", "flag"])
    table = table[table["value"] != "."]
    return _frame(
        [
            (pd.to_datetime(d).date(), float(v))
            for d, v in zip(table["date"], table["value"], strict=True)
        ]
    )


def parse_ecb(blob: bytes) -> pd.DataFrame:
    table = pd.read_csv(_text(blob), usecols=["TIME_PERIOD", "OBS_VALUE"])
    return _frame(
        [
            (pd.to_datetime(d).date(), float(v))
            for d, v in zip(table["TIME_PERIOD"], table["OBS_VALUE"], strict=True)
        ]
    )


def parse_mof(blobs: list[bytes]) -> pd.DataFrame:
    rows: list[tuple[dt.date, float]] = []
    for blob in blobs:
        table = pd.read_csv(_text(blob), skiprows=1)
        for _, row in table.iterrows():
            value = row["2Y"]
            if value in ("-", "", None) or pd.isna(value):
                continue
            year, month, day = str(row["Date"]).split("/")
            rows.append((dt.date(int(year), int(month), int(day)), float(value)))
    return _frame(rows)


def parse_boc(blob: bytes) -> pd.DataFrame:
    text = blob.decode("utf-8-sig", errors="replace")
    start = text.index("OBSERVATIONS")
    table = pd.read_csv(io.StringIO(text[start:]), skiprows=1)
    column = [c for c in table.columns if c != "date"][0]
    return _frame(
        [
            (pd.to_datetime(d).date(), float(v))
            for d, v in zip(table["date"], table[column], strict=True)
            if str(v) not in ("nan", "")
        ]
    )


def parse_snb(blob: bytes) -> pd.DataFrame:
    text = blob.decode("utf-8-sig", errors="replace")
    table = pd.read_csv(io.StringIO(text), sep=";", skiprows=3)
    table = table[table["D0"] == "2J"].dropna(subset=["Value"])
    return _frame(
        [
            (pd.to_datetime(d).date(), float(v))
            for d, v in zip(table["Date"], table["Value"], strict=True)
        ]
    )


def parse_boe(archive: bytes, current: bytes) -> pd.DataFrame:
    """The 24-month point of the nominal spot curve, short end (sheet '3. spot, short end')."""
    rows: list[tuple[dt.date, float]] = []
    for blob, members in (
        (archive, None),
        (current, ["GLC Nominal daily data current month.xlsx"]),
    ):
        with zipfile.ZipFile(io.BytesIO(blob)) as outer:
            names = members or [
                n
                for n in outer.namelist()
                if n.endswith(".xlsx") and ("2016 to 2024" in n or "2025 to present" in n)
            ]
            for name in names:
                with zipfile.ZipFile(io.BytesIO(outer.read(name))) as book:
                    workbook = book.read("xl/workbook.xml").decode("utf-8", "replace")
                    order = [
                        part.split('name="')[1].split('"')[0]
                        for part in workbook.split("<sheet ")[1:]
                    ]
                    index = order.index("3. spot, short end") + 1
                    path = f"xl/worksheets/sheet{index}.xml"
                    if path not in book.namelist():  # pragma: no cover - layout guard
                        raise RuntimeError(f"{name}: no worksheet at {path}")
                    months: dict[int, float] | None = None
                    for row in _sheet_rows(book, path):
                        first = row.get(0)
                        if first == "months:":
                            months = {
                                col: float(value)
                                for col, value in row.items()
                                if col > 0 and isinstance(value, float)
                            }
                            continue
                        if months is None or not isinstance(first, float) or first < 20000:
                            continue
                        column = next((c for c, m in months.items() if abs(m - 24.0) < 1e-9), None)
                        value = row.get(column) if column is not None else None
                        if isinstance(value, float):
                            rows.append((_excel_date(first), value))
    return _frame(rows)


def parse_rbnz(blob: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(blob)) as book:
        workbook = book.read("xl/workbook.xml").decode("utf-8", "replace")
        order = [part.split('name="')[1].split('"')[0] for part in workbook.split("<sheet ")[1:]]
        path = f"xl/worksheets/sheet{order.index('Data') + 1}.xml"
        group: dict[int, Any] = {}
        label: dict[int, Any] = {}
        rows: list[tuple[dt.date, float]] = []
        column: int | None = None
        for row in _sheet_rows(book, path):
            if not group:
                group = row
                continue
            if not label:
                label = row
                column = next(
                    (
                        col
                        for col, name in label.items()
                        if name == "2 year" and "government bond" in str(group.get(col, "")).lower()
                    ),
                    None,
                )
                continue
            first = row.get(0)
            value = row.get(column) if column is not None else None
            if isinstance(first, float) and first > 20000 and isinstance(value, float):
                rows.append((_excel_date(first), value))
    if column is None:  # pragma: no cover - layout guard
        raise RuntimeError("RBNZ: no 2 year government bond column")
    return _frame(rows)


def acquire() -> dict[str, Any]:
    """Fetch every reachable primary source plus the ECB cross-check, and record it."""
    root = Path(__file__).resolve().parents[3]
    data = root / DATA_DIR
    data.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "acquired_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "no_fx_series_requested": True,
        "series": {},
        "unreachable": {},
    }
    blobs: dict[str, bytes] = {}

    def get(key: str, url: str) -> bytes:
        blob = _fetch(url)
        blobs[key] = blob
        return blob

    treasury = [
        get(f"usd_{year}", sources.by_currency("USD").url.format(year=year))
        for year in TREASURY_YEARS
    ]
    ecb = next(s for s in sources.SOURCES if s.role == "cross_check")
    plan: dict[str, Any] = {
        "USD": lambda: parse_treasury(treasury),
        "EUR": lambda: parse_bundesbank(get("eur", sources.by_currency("EUR").url)),
        "JPY": lambda: parse_mof(
            [
                get("jpy_all", sources.by_currency("JPY").url),
                get(
                    "jpy_current",
                    "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv",
                ),
            ]
        ),
        "CAD": lambda: parse_boc(get("cad", sources.by_currency("CAD").url)),
        "NZD": lambda: parse_rbnz(get("nzd", sources.by_currency("NZD").url)),
        "CHF": lambda: parse_snb(get("chf", sources.by_currency("CHF").url)),
        "GBP": lambda: parse_boe(
            get("gbp_archive", sources.by_currency("GBP").url),
            get(
                "gbp_current",
                "https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/latest-yield-curve-data.zip",
            ),
        ),
        "EUR_ECB_CROSS_CHECK": lambda: parse_ecb(get("eur_ecb", ecb.url)),
    }
    frames: dict[str, pd.DataFrame] = {}
    for name, build_frame in plan.items():
        try:
            frames[name] = build_frame()
        except Exception as error:  # noqa: BLE001 - a refused source is a recorded fact
            record["unreachable"][name] = {
                "body": sources.by_currency(name).body
                if name in {s.currency for s in sources.primary()}
                else ecb.body,
                "reason": f"{type(error).__name__}: {error}"[:400],
            }

    for name, frame in frames.items():
        path = data / f"{name.lower()}_2y.parquet"
        frame.to_parquet(path, index=False)
        record["series"][name] = {
            "rows": int(len(frame)),
            "first": str(frame["date"].min().date()),
            "last": str(frame["date"].max().date()),
            "file": str(path.relative_to(root)).replace("\\", "/"),
            "sha256_of_normalised_csv": hashlib.sha256(
                frame.to_csv(index=False).encode("utf-8")
            ).hexdigest(),
        }
    for key, blob in blobs.items():
        record.setdefault("fetched_bytes", {})[key] = {
            "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
        }
    for source in sources.SOURCES:
        if not source.reachable and source.currency not in record["unreachable"]:
            record["unreachable"][source.currency] = {
                "body": source.body,
                "url": source.url,
                "reason": source.notes[0] if source.notes else "refused from this environment",
            }
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
        print(f"refused: set {OPT_IN_ENV}=1 to acquire (public non-FX sources only)")
        return 2
    record = acquire()
    for name, block in record["series"].items():
        print(f"{name}: {block['rows']} rows, {block['first']} .. {block['last']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
