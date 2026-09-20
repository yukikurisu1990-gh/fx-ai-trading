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

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/top_five"
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/top_five/acquisition.json"


def _fetch(url: str) -> bytes:
    """network へ出る唯一の場所。**fetch のたびに許可を確認する。**

    fallback は無い。`curl` へ落ちる経路を持たないので、conftest の socket guard が
    拒否すればそこで終わる（子プロセスで網を抜ける経路が存在しない）。
    """
    require_opt_in(OPT_IN_ENV, what="acquire Top-Five public data")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(
        request, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
    ) as response:
        return response.read()


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
    frame = pd.DataFrame(
        {"vix": pd.to_numeric(raw[close], errors="coerce")},
        index=pd.to_datetime(raw[column], errors="coerce"),
    ).dropna()
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


def _parse_generic_daily(blob: bytes, *, column: str, label: str) -> pd.DataFrame:
    """1 列の日次系列を持つ CSV を、緩く読んで厳しく切る。"""
    for skip in range(0, 12):
        try:
            raw = _read_csv(blob, skiprows=skip)
        except Exception:  # noqa: BLE001 - header 位置の探索
            continue
        if raw.shape[1] < 2:
            continue
        index = pd.to_datetime(raw.iloc[:, 0], errors="coerce", dayfirst=False)
        if index.notna().sum() < 100:
            continue
        value = pd.to_numeric(raw.iloc[:, -1], errors="coerce")
        frame = pd.DataFrame({column: value.to_numpy()}, index=index).dropna()
        if len(frame) > 100:
            frame.index.name = "date"
            return _truncate(frame.sort_index(), label=label)
    raise ValueError(f"{label}: 日次系列として読めなかった")


PARSERS: Final[dict[str, Any]] = {
    "vix": _parse_vix,
    "wti": _parse_wti,
    "bund_10y": lambda blob: _parse_generic_daily(blob, column="bund_10y", label="bund_10y"),
    "snb_10y": lambda blob: _parse_generic_daily(blob, column="snb_10y", label="snb_10y"),
    "boc_10y": lambda blob: _parse_generic_daily(blob, column="boc_10y", label="boc_10y"),
    "boe_10y": lambda blob: _parse_generic_daily(blob, column="boe_10y", label="boe_10y"),
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
        urls = [
            sources.url_for(key, start=dt.date(y, 1, 1), end=dt.date(y, 12, 31))
            for y in sources.bounded_years()
        ]
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
