# ruff: noqa: E501 -- acquisition prose
"""次の 5 本の public / free data を取得し、seen span へ切り落として保存する。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: 2026-09-22 Human + ChatGPT 裁定 §K（Stage 0 / 取得）。

**network に出る条件は 2 つ揃ったときだけ。**

1. `NEXT_FIVE_ACQUIRE_APPROVED=1`（`require_opt_in` が fetch のたびに確認）
2. この module を **script として実行**していること

`import` では何も起きない。curl 等へ落ちる経路は持たない。

**保存するのは切り落とし済みの frame だけ。** 切り落とし前の frame は `_truncate` の
内側にしか存在せず、外へ返らない。呼び出し側が protected 領域を見る経路が無い。

**source は 2 系統ある。** FRED 経由と、各国公式サイト直の経路である。
前 cycle で FRED だけが到達せず、公式サイト直は 8 本すべて HTTP 200 で取れた。
`--route` でどちらを使うかを選ぶ — **どちらを使ったかは provenance に残る。**
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.acquisition_safety import (
    NETWORK_FAILURES,
    OK,
    classify_failure,
    digest,
    require_opt_in,
    write_provenance,
)
from scripts.research.next_five import prereg

OPT_IN_ENV: Final[str] = "NEXT_FIVE_ACQUIRE_APPROVED"
OVERWRITE_ENV: Final[str] = "NEXT_FIVE_PROVENANCE_OVERWRITE_APPROVED"
USER_AGENT: Final[str] = "Mozilla/5.0 fx-ai-trading research acquisition"
TIMEOUT_SECONDS: Final[int] = 90
ATTEMPTS: Final[int] = 2
RETRY_SECONDS: Final[float] = 2.0

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/next_five"
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/next_five/acquisition.json"

#: seen span の外側は **保存しない**。境界は parsed date で判定する。
SEEN_LAST: Final[dt.date] = dt.date.fromisoformat(prereg.SPANS["recent"]["last"])
PROTECTED_FIRST: Final[dt.date] = dt.date.fromisoformat(
    prereg.PROTECTED_BOUNDS["fresh_pool"]["first"]
)
PROTECTED_LAST: Final[dt.date] = dt.date.fromisoformat(
    prereg.PROTECTED_BOUNDS["fresh_pool"]["last"]
)
LONG_LAST: Final[dt.date] = dt.date.fromisoformat(prereg.SPANS["long"]["last"])


def is_seen(day: dt.date) -> bool:
    """**parsed typed date で判定する。文字列の辞書順比較はしない。**"""
    if not isinstance(day, dt.date) or isinstance(day, dt.datetime):
        day = dt.date(day.year, day.month, day.day)
    if day <= LONG_LAST:
        return True
    if PROTECTED_FIRST <= day <= PROTECTED_LAST:
        return False
    return day <= SEEN_LAST


#: FRED 経由の series id。
FRED: Final[dict[str, str]] = {
    "trade_usd": "BOPGSTB",
    "trade_jpy": "XTNTVA01JPM664S",
    "trade_gbp": "XTNTVA01GBM664S",
    "trade_cad": "XTNTVA01CAM664S",
    "trade_aud": "XTNTVA01AUM664S",
    "trade_nzd": "XTNTVA01NZM664S",
    "trade_chf": "XTNTVA01CHM664S",
    "trade_eur": "XTNTVA01EZM664S",
    "balance_sheet_usd": "WALCL",
    "balance_sheet_eur": "ECBASSETSW",
    "balance_sheet_jpy": "JPNASSETS",
    "reserves_jpy": "TRESEGJPM052N",
    "reserves_chf": "TRESEGCHM052N",
    "reserves_gbp": "TRESEGGBM052N",
    "reserves_cad": "TRESEGCAM052N",
    "reserves_aud": "TRESEGAUM052N",
    "credit_hy_oas": "BAMLH0A0HYM2",
}

#: 各国公式サイト直の経路（FRED が到達しないときの代替）。
#: **前 cycle で HTTP 200 が確認できた host を優先している。**
DIRECT: Final[dict[str, dict[str, str]]] = {
    "balance_sheet_chf": {
        "provider": "Swiss National Bank",
        "url": "https://data.snb.ch/api/cube/snbbipo/data/csv/en",
        "kind": "snb_csv",
    },
    "reserves_chf": {
        "provider": "Swiss National Bank",
        "url": "https://data.snb.ch/api/cube/snbdevbil/data/csv/en",
        "kind": "snb_csv",
    },
}


def _fetch(url: str) -> bytes:
    """network へ出る唯一の場所。**fetch のたびに許可を確認する。** fallback は無い。"""
    last: BaseException | None = None
    for _ in range(ATTEMPTS):
        require_opt_in(OPT_IN_ENV, what="acquire next-five public data")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(
                request, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
            ) as response:
                return response.read()
        except urllib.error.HTTPError:
            raise
        except NETWORK_FAILURES as error:
            last = error
            time.sleep(RETRY_SECONDS)
    raise last if last is not None else RuntimeError(f"{url}: 取得できなかった")


def _truncate(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    """**seen window の外を落とす唯一の場所。** 切り落とし前の frame は外へ返らない。"""
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError(f"{label}: DatetimeIndex でない frame は切り落とせない")
    keep = [is_seen(stamp.date()) for stamp in frame.index]
    kept = frame[keep]
    leaked = [str(s.date()) for s, k in zip(frame.index, keep, strict=True) if not k][:3]
    if kept.empty:
        raise ValueError(f"{label}: seen window に 1 行も残らなかった（外側の例: {leaked}）")
    for stamp in kept.index:
        if PROTECTED_FIRST <= stamp.date() <= PROTECTED_LAST:
            raise AssertionError(f"{label}: 保護 pool の行が残った（{stamp.date()}）")
    return kept


def _parse_fred(payload: bytes, name: str) -> pd.DataFrame:
    frame = pd.read_csv(io.StringIO(payload.decode("utf-8", errors="replace")))
    if frame.shape[1] < 2:
        raise ValueError(f"{name}: 列が足りない")
    stamps = pd.to_datetime(frame.iloc[:, 0], errors="coerce")
    values = pd.to_numeric(
        frame.iloc[:, 1].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    out = pd.DataFrame({name: values.to_numpy()}, index=pd.DatetimeIndex(stamps))
    out = out[out.index.notna()].dropna()
    if out.empty or float(out[name].std()) == 0.0:
        #: 前 cycle の TIC は全 0.0 で通りかけた。**分散ゼロは parse 失敗として扱う。**
        raise ValueError(f"{name}: 値が空か定数である（parse を疑う）")
    return out.sort_index()


def _parse_snb(payload: bytes, name: str) -> pd.DataFrame:
    text = payload.decode("utf-8", errors="replace")
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("Date")), 0)
    frame = pd.read_csv(io.StringIO("\n".join(lines[start:])), sep=";")
    stamps = pd.to_datetime(frame.iloc[:, 0], errors="coerce")
    values = pd.to_numeric(frame.iloc[:, -1], errors="coerce")
    out = pd.DataFrame({name: values.to_numpy()}, index=pd.DatetimeIndex(stamps))
    out = out[out.index.notna()].dropna()
    if out.empty or float(out[name].std()) == 0.0:
        raise ValueError(f"{name}: 値が空か定数である（parse を疑う）")
    return out.sort_index()


PARSERS: Final[dict[str, Any]] = {"fred": _parse_fred, "snb_csv": _parse_snb}


def _acquire_one(name: str, url: str, kind: str, provider: str) -> dict[str, Any]:
    started = pd.Timestamp.utcnow().isoformat()
    try:
        payload = _fetch(url)
    except Exception as error:  # noqa: BLE001 - 分類して記録するのが仕事である
        return {
            "name": name,
            "provider": provider,
            "url": url,
            "retrieval_timestamp_utc": started,
            "http_status": getattr(error, "code", None),
            "outcome": classify_failure(error),
            "error": f"{type(error).__name__}: {error}"[:200],
            "reading": "**『provider にデータが無い』ではない。** 到達の話である",
        }
    try:
        frame = PARSERS[kind](payload, name)
        kept = _truncate(frame, label=name)
    except Exception as error:  # noqa: BLE001
        return {
            "name": name,
            "provider": provider,
            "url": url,
            "retrieval_timestamp_utc": started,
            "http_status": 200,
            "outcome": f"PARSE_OR_TRUNCATION_FAILED: {type(error).__name__}",
            "error": str(error)[:200],
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    kept.to_parquet(DATA_DIR / f"{name}.parquet")
    spacing = pd.Series(kept.index).diff().dt.days.median()
    return {
        "name": name,
        "provider": provider,
        "url": url,
        "request_parameters": url.split("?", 1)[1] if "?" in url else "",
        "retrieval_timestamp_utc": started,
        "http_status": 200,
        "outcome": OK,
        "content_hash": digest(payload.decode("utf-8", errors="replace")),
        "coverage": {
            "first": str(kept.index.min().date()),
            "last": str(kept.index.max().date()),
            "rows": int(len(kept)),
        },
        "frequency": (
            "daily"
            if spacing and spacing <= 5
            else "weekly"
            if spacing and spacing <= 10
            else "monthly"
        ),
        "publication_timing": "prereg.TRACKS の publication_lag に従って適用される",
        "truncated_to_seen_window": True,
    }


def run(route: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if route in {"fred", "both"}:
        for name, series_id in FRED.items():
            rows.append(
                _acquire_one(
                    name,
                    f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
                    "fred",
                    "Federal Reserve Bank of St. Louis (FRED)",
                )
            )
    if route in {"direct", "both"}:
        for name, spec in DIRECT.items():
            if route == "both" and any(r["name"] == name and r["outcome"] == OK for r in rows):
                continue
            rows.append(_acquire_one(name, spec["url"], spec["kind"], spec["provider"]))

    ok = [row["name"] for row in rows if row["outcome"] == OK]
    return {
        "cycle": prereg.CYCLE,
        "freeze_digest": prereg.freeze_digest(),
        "authority": "2026-09-22 Human + ChatGPT 裁定 §K",
        "route": route,
        "finished_utc": pd.Timestamp.utcnow().isoformat(),
        "scope": "public / free source のみ。paid / authenticated には触れていない",
        "sources": {row["name"]: row for row in rows},
        "acquired": sorted(ok),
        "failed": sorted(row["name"] for row in rows if row["outcome"] != OK),
        "protected_span_handling": (
            "seen window の外は **保存前に落とす**。境界は parsed typed date で判定し、"
            "保護 pool の行が残っていたら AssertionError で落ちる"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="次の 5 本の public data を取得する")
    parser.add_argument("--route", choices=("fred", "direct", "both"), default="both")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    payload = run(args.route)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(
        RECORD,
        payload,
        overwrite=args.overwrite,
        env_name=OVERWRITE_ENV if args.overwrite else None,
    )
    print(f"取得成功 {len(payload['acquired'])} / 失敗 {len(payload['failed'])}", file=sys.stderr)
    for name in payload["failed"]:
        print(f"  失敗: {name} -> {payload['sources'][name]['outcome']}", file=sys.stderr)
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if not os.environ.get(OPT_IN_ENV):
        print(f"{OPT_IN_ENV}=1 が無いので何もしない", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
