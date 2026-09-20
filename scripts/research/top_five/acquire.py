# ruff: noqa: E501 -- acquisition prose
"""Top-Five の public / free data を取得し、seen span へ切り落として保存する。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: 2026-09-21 Human + ChatGPT 裁定 §5（取得承認）・§6（記録義務）・
§7（network safety）・§8（境界）。

**network に出る条件は 2 つ揃ったときだけ。**

1. `TOP_FIVE_ACQUIRE_APPROVED=1`（`acquisition_safety.require_opt_in` が fetch のたびに確認）
2. この module を **script として実行**していること

opt-in を消す mutation が入っても、`_fetch` が `require_opt_in` を毎回呼ぶので
fetch 単位で止まる。import しただけでは何も起きない。

**保存するのは切り落とし済みの frame だけ。** raw frame は `_truncate` の内側にしか
存在せず、外へ返らない。呼び出し側が protected 領域を見る経路が無い。
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.acquisition_safety import (
    HTTP_STATUS,
    NETWORK_FAILURES,
    OK,
    classify_failure,
    digest,
    require_opt_in,
    write_provenance,
)
from scripts.research.top_five import sources

OPT_IN_ENV: Final[str] = "TOP_FIVE_ACQUIRE_APPROVED"
USER_AGENT: Final[str] = "Mozilla/5.0 fx-ai-trading research acquisition"
TIMEOUT_SECONDS: Final[int] = 120
#: 一過性の切断だけを再試行する回数と間隔。provider の status は再試行しない。
ATTEMPTS: Final[int] = 3
RETRY_SECONDS: Final[float] = 2.0

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/top_five"
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/top_five/acquisition.json"


def _fetch(url: str) -> bytes:
    """network へ出る唯一の場所。**fetch のたびに許可を確認する。**

    fallback は無い。`curl` へ落ちる経路を持たないので、conftest の socket guard が
    拒否すればそこで終わる（子プロセスで網を抜ける経路が存在しない）。
    """
    #: 許可は **試行のたび**に確認する。再試行が guard を 1 回で済ませる抜け道に
    #: ならないようにするため、ループの内側に置く。
    last: BaseException | None = None
    for _ in range(ATTEMPTS):
        require_opt_in(OPT_IN_ENV, what="acquire Top-Five public data")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(
                request, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
            ) as response:
                return response.read()
        except urllib.error.HTTPError:
            #: provider が答えた status は再試行しない。それは相手の返事である。
            raise
        except NETWORK_FAILURES as error:
            #: IncompleteRead のような一過性の切断だけを再試行する。
            last = error
            time.sleep(RETRY_SECONDS)
    raise last if last is not None else RuntimeError(f"{url}: 取得できなかった")


def _truncate(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    """seen span の外の行を落とす。**raw frame はここから外へ出ない。**

    全量配信 endpoint のための関門である。index は `datetime.date` でなければならない
    — 文字列のまま比較させない。
    """
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError(f"{label}: index は DatetimeIndex でなければならない")
    days = [ts.date() for ts in frame.index]
    keep = [sources.is_seen(day) for day in days]
    kept = frame.loc[keep]
    sources.assert_no_protected_day([ts.date() for ts in kept.index], label=label)
    return kept


def _read_csv(blob: bytes, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(blob.decode("utf-8-sig", errors="replace")), **kwargs)


# ---------------------------------------------------------------------------
# source ごとの parser。**どれも切り落とし済みの frame しか返さない。**
# ---------------------------------------------------------------------------


def _parse_vix(blob: bytes) -> pd.DataFrame:
    raw = _read_csv(blob)
    column = next(c for c in raw.columns if c.strip().upper() in {"DATE"})
    close = next(c for c in raw.columns if "CLOSE" in c.strip().upper())
    #: CBOE は MM/DD/YYYY。format を指定しないと pandas が全行 NaT にして、
    #: 切り落としが「全部 protected」に見える形で空になる。実際に一度そうなった。
    #: `.to_numpy()` で値を渡す。Series をそのまま渡すと、pandas が RangeIndex を
    #: 新しい DatetimeIndex に **再 index** して全行 NaN にする。実際にそうなり、
    #: 「日付が parse できない」ように見えていた。
    frame = pd.DataFrame(
        {"vix": pd.to_numeric(raw[close], errors="coerce").to_numpy()},
        index=pd.to_datetime(raw[column], format="%m/%d/%Y", errors="coerce"),
    ).dropna()
    if frame.empty:
        raise ValueError("vix: 日付が 1 行も parse できなかった")
    frame.index.name = "date"
    return _truncate(frame.sort_index(), label="vix")


def _parse_wti(blob: bytes) -> pd.DataFrame:
    """EIA の OLE2 `.xls`。**parsing のみ**で、埋め込み macro は実行しない。

    `pd.read_excel(engine="xlrd")` は worksheet の cell を読むだけで、VBA project を
    評価しない。裁定 §2 の条件はここで満たされる。
    """
    book = pd.read_excel(io.BytesIO(blob), sheet_name=None, engine="xlrd", header=None)
    for sheet in book.values():
        for header in range(0, min(12, len(sheet))):
            row = sheet.iloc[header].astype(str).str.lower()
            if row.str.contains("date").any():
                table = sheet.iloc[header + 1 :]
                index = pd.to_datetime(table.iloc[:, 0], errors="coerce")
                value = pd.to_numeric(table.iloc[:, 1], errors="coerce")
                frame = pd.DataFrame({"wti": value.to_numpy()}, index=index).dropna()
                if len(frame) > 1000:
                    frame.index.name = "date"
                    return _truncate(frame.sort_index(), label="wti")
    raise ValueError("wti: 日付列を持つ sheet が見つからない")


def _parse_bund(blob: bytes) -> pd.DataFrame:
    """Bundesbank Zinsstruktur 10 年。

    **最終列は flags 列**（"No value available"）で、値は 2 列目にある。generic に
    `iloc[:, -1]` を取らせると全行が NaN になり、`rows=0` が「取れなかった」ではなく
    「全部 protected だった」に見える — 実際に一度そうなった。
    """
    text = blob.decode("utf-8-sig", errors="replace")
    raw = pd.read_csv(io.StringIO(text), skiprows=8, header=None, usecols=[0, 1], names=["d", "v"])
    index = pd.to_datetime(raw["d"], format="%Y-%m-%d", errors="coerce")
    value = pd.to_numeric(raw["v"], errors="coerce")
    frame = pd.DataFrame({"bund_10y": value.to_numpy()}, index=index).dropna()
    if frame.empty:
        raise ValueError("bund_10y: 値が 1 行も parse できなかった")
    frame.index.name = "date"
    return _truncate(frame.sort_index(), label="bund_10y")


def _parse_snb(blob: bytes) -> pd.DataFrame:
    """SNB rendoblid cube。`;` 区切りで、満期は `D0` 列に入っている。

    10 年物のラベルは `10J0` である（`1J` `2J` ... と並ぶ中で、`10J` ではない）。
    """
    text = blob.decode("utf-8-sig", errors="replace")
    raw = pd.read_csv(io.StringIO(text), sep=";", skiprows=3)
    ten = raw[raw["D0"].astype(str).str.strip() == "10J0"]
    index = pd.to_datetime(ten["Date"], format="%Y-%m-%d", errors="coerce")
    value = pd.to_numeric(ten["Value"], errors="coerce")
    frame = pd.DataFrame({"snb_10y": value.to_numpy()}, index=index).dropna()
    if frame.empty:
        raise ValueError("snb_10y: 10J0 の行が 1 つも読めなかった")
    frame.index.name = "date"
    return _truncate(frame.sort_index(), label="snb_10y")


def _parse_treasury(blob: bytes) -> pd.DataFrame:
    """US Treasury の日次 par yield curve。10 年列だけを採る。"""
    raw = _read_csv(blob)
    date_column = next(c for c in raw.columns if c.strip().lower() == "date")
    ten = next(c for c in raw.columns if c.strip().lower() in {"10 yr", "10yr", "10 year"})
    index = pd.to_datetime(raw[date_column], format="%m/%d/%Y", errors="coerce")
    value = pd.to_numeric(raw[ten], errors="coerce")
    frame = pd.DataFrame({"ust_10y": value.to_numpy()}, index=index).dropna()
    if frame.empty:
        raise ValueError("ust_10y: 10 年列が 1 行も読めなかった")
    frame.index.name = "date"
    return _truncate(frame.sort_index(), label="ust_10y")


def _parse_boc(blob: bytes) -> pd.DataFrame:
    """Bank of Canada Valet。header の後に `date,value` が並ぶ。"""
    text = blob.decode("utf-8-sig", errors="replace")
    body = text[text.index("OBSERVATIONS") :] if "OBSERVATIONS" in text else text
    raw = pd.read_csv(io.StringIO(body), skiprows=1)
    index = pd.to_datetime(raw.iloc[:, 0], format="%Y-%m-%d", errors="coerce")
    value = pd.to_numeric(raw.iloc[:, 1], errors="coerce")
    frame = pd.DataFrame({"boc_10y": value.to_numpy()}, index=index).dropna()
    if frame.empty:
        raise ValueError("boc_10y: 値が 1 行も読めなかった")
    frame.index.name = "date"
    return _truncate(frame.sort_index(), label="boc_10y")


def _parse_boe(blob: bytes) -> pd.DataFrame:
    """Bank of England。`DATE,IUDMNZC` の 2 列で、日付は `DD Mon YYYY`。"""
    raw = _read_csv(blob)
    index = pd.to_datetime(raw.iloc[:, 0], format="%d %b %Y", errors="coerce")
    if index.notna().sum() == 0:
        index = pd.to_datetime(raw.iloc[:, 0], errors="coerce")
    value = pd.to_numeric(raw.iloc[:, 1], errors="coerce")
    frame = pd.DataFrame({"boe_10y": value.to_numpy()}, index=index).dropna()
    if frame.empty:
        raise ValueError("boe_10y: 値が 1 行も読めなかった")
    frame.index.name = "date"
    return _truncate(frame.sort_index(), label="boe_10y")


def _parse_tic(blob: bytes) -> pd.DataFrame:
    """TIC S-1。**全世界計（All Countries）・長期 domestic 証券の net foreign purchases。**

    file は `国名, 国コード, 月, gross 購入 6 列, gross 売却 6 列` の横長レポートである。
    net = gross 購入 - gross 売却 で、domestic 証券は 4 列（US Treasury / agency /
    corporate bond / stock）。凍結文が「gross でも domestic/foreign 別でも国別でもない」
    と固定しているので、ここで採る行と列は一意に決まる。
    """
    text = blob.decode("utf-8-sig", errors="replace")
    raw = pd.read_csv(io.StringIO(text), skiprows=18, header=None, thousands=",", low_memory=False)
    raw.columns = ["country", "code", "month"] + [f"c{i}" for i in range(1, 13)]
    world = raw[raw["country"].astype(str).str.strip() == "All Countries"].copy()
    if world.empty:
        raise ValueError("tic_s1: All Countries の行が見つからない")

    month = pd.to_datetime(world["month"], format="%Y-%m", errors="coerce")
    #: domestic 長期証券 4 列。購入 c1..c4、売却 c7..c10。
    buys = world[["c1", "c2", "c3", "c4"]].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    sells = world[["c7", "c8", "c9", "c10"]].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    frame = pd.DataFrame(
        {"tic_s1": (buys - sells).to_numpy()}, index=pd.DatetimeIndex(month)
    ).dropna()
    if frame.empty:
        raise ValueError("tic_s1: net purchases が 1 つも計算できなかった")
    frame.index.name = "date"
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    #: 月次系列の切り落としは **vintage 適用後の使用可能日**で判定する。観測月 m の値は
    #: m+2 月末から使えるので、その日が seen window に入る月だけを残す。観測月そのもので
    #: 切ると、保護 pool の月を抱えたまま保存してしまう（実際に一度そうなった）。
    usable = (frame.index + pd.offsets.MonthEnd(0) + pd.DateOffset(months=2)).normalize()
    keep = [sources.is_seen(day.date()) for day in usable]
    kept = frame.loc[keep]
    if kept.empty:
        raise ValueError("tic_s1: 使用可能日が seen window に入る月が 1 つも無い")
    return kept


PARSERS: Final[dict[str, Any]] = {
    "vix": _parse_vix,
    "wti": _parse_wti,
    "ust_10y": _parse_treasury,
    "bund_10y": _parse_bund,
    "boc_10y": _parse_boc,
    "snb_10y": _parse_snb,
    "boe_10y": _parse_boe,
    "tic_s1": _parse_tic,
}


def acquire_one(key: str) -> dict[str, Any]:
    """1 source を取得し、切り落として保存し、provenance を返す。"""
    source = sources.BY_KEY[key]
    started = dt.datetime.now(dt.UTC).isoformat()
    record: dict[str, Any] = {
        "key": key,
        "track": source.track,
        "provider": source.provider,
        "frequency": source.frequency,
        "publication_timing": source.publication_timing,
        "bounded_request": source.bounded_request,
        "retrieval_timestamp": started,
        "request_parameters": {
            "timeout_seconds": TIMEOUT_SECONDS,
            "user_agent": USER_AGENT,
            "method": "GET",
        },
    }

    urls: list[str]
    if source.bounded_request and "{year}" in source.url:
        #: 年の両端が seen window の外に出る年がある（1999 年は 1/4 から、
        #: 2016 年は 6/1 まで）。**window と交差させてから request する。**
        urls = []
        for year in sources.bounded_years():
            for first, last in sources.SEEN_WINDOWS:
                start = max(first, dt.date(year, 1, 1))
                end = min(last, dt.date(year, 12, 31))
                if start <= end:
                    urls.append(sources.url_for(key, start=start, end=end))
    elif source.bounded_request:
        urls = [sources.url_for(key, start=first, end=last) for first, last in sources.SEEN_WINDOWS]
    else:
        urls = [source.url]
    record["url"] = urls if len(urls) > 1 else urls[0]

    blobs: list[bytes] = []
    try:
        for url in urls:
            blobs.append(_fetch(url))
        record["http_status"] = 200
        record["result"] = OK
    except urllib.error.HTTPError as error:
        record["http_status"] = error.code
        record["result"] = HTTP_STATUS
        record["detail"] = str(error)[:300]
        return record
    except NETWORK_FAILURES as error:
        record["http_status"] = None
        record["result"] = classify_failure(error)
        record["detail"] = f"{type(error).__name__}: {error}"[:300]
        return record

    record["content_hash"] = [digest(b) for b in blobs] if len(blobs) > 1 else digest(blobs[0])
    record["raw_bytes"] = sum(len(b) for b in blobs)

    frames = [PARSERS[key](b) for b in blobs] if key in PARSERS else []
    if not frames:
        raise NotImplementedError(f"{key}: parser が未実装")
    frame = pd.concat(frames).sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"{key}.parquet"
    frame.to_parquet(out)
    record["coverage"] = {
        "rows": int(len(frame)),
        "first": frame.index.min().date().isoformat(),
        "last": frame.index.max().date().isoformat(),
        "columns": list(frame.columns),
    }
    record["stored"] = str(out.relative_to(REPO_ROOT))
    record["truncated_to_seen_spans"] = True
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Top-Five public data acquisition")
    parser.add_argument("keys", nargs="*", default=None)
    args = parser.parse_args()
    keys = args.keys or [s.key for s in sources.SOURCES if s.key in PARSERS]

    records = {}
    for key in keys:
        try:
            records[key] = acquire_one(key)
        except Exception as error:  # noqa: BLE001 - 失敗も記録する
            records[key] = {
                "key": key,
                "result": classify_failure(error),
                "detail": f"{type(error).__name__}: {error}"[:400],
            }
        status = records[key].get("result")
        coverage = records[key].get("coverage", {})
        print(f"{key:10s} {status:44s} rows={coverage.get('rows', 0)}", file=sys.stderr)

    payload = {
        "authority": "2026-09-21 Human + ChatGPT 裁定 §5",
        "scope": "public / free source のみ。protected span は request / truncation の両方で除外",
        "finished_utc": dt.datetime.now(dt.UTC).isoformat(),
        "sources": records,
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(RECORD, payload)
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
