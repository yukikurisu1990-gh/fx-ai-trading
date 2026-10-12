# ruff: noqa: E501 -- research prose
"""金利の proxy（OANDA の bond CFD）の M15 bid / ask の取得と読み込み（事前登録 §1・§3）。

- request の from / to を **2021-04-26T00:00Z / 2025-12-29T00:00Z（排他）** に固定する。境界は parse した `datetime` で比べる（文字列の比較・subclass の bypass を避ける）。
- 返った candle の時刻を parse し、全てが境界の内側であることを確かめる。1 本でも外にあれば何も書かない。
- `complete = true` だけ。取得は historical / read-only の candle の endpoint だけで、注文・account の endpoint を呼ばない。

command: python -X utf8 -m scripts.research.rates_anchored_fx.data_rates
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Final

import pandas as pd

REPO: Final[Path] = Path(__file__).resolve().parents[3]
CACHE: Final[Path] = REPO / "data/rates_anchored_fx"
MANIFEST: Final[Path] = REPO / "artifacts/research/rates_anchored_fx/rates_acquisition.json"
INSTRUMENTS: Final[dict[str, str]] = {"USD": "USB10Y_USD", "EUR": "DE10YB_EUR", "GBP": "UK10YB_GBP"}
LOWER: Final[dt.datetime] = dt.datetime(2021, 4, 26, tzinfo=dt.UTC)
UPPER: Final[dt.datetime] = dt.datetime(2025, 12, 29, tzinfo=dt.UTC)  # 排他
FRESH_END: Final[dt.date] = dt.date(2021, 4, 25)
WINDOW_DAYS: Final[int] = 45  # M15 で 45 日 = 最大 4,320 本 < 5,000


class BoundaryError(AssertionError):
    """境界の外の request か candle。"""


def parse_oanda_time(s: str) -> dt.datetime:
    if not isinstance(s, str) or type(s) is not str:
        raise BoundaryError("時刻は str でなければならない")
    head = s[:19]
    out = dt.datetime.strptime(head, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.UTC)
    if not s.endswith("Z"):
        raise BoundaryError(f"UTC の Z で終わらない時刻: {s}")
    return out


def check_bounds(lo: dt.datetime, hi: dt.datetime) -> None:
    if type(lo) is not dt.datetime or type(hi) is not dt.datetime:
        raise BoundaryError("境界は datetime でなければならない")
    if lo.utcoffset() != dt.timedelta(0) or hi.utcoffset() != dt.timedelta(0):
        raise BoundaryError("境界は UTC でなければならない")
    if lo < LOWER or hi > UPPER or lo >= hi:
        raise BoundaryError(f"request の境界が範囲の外: {lo} … {hi}")


def check_candle_times(times: list[dt.datetime]) -> None:
    for t in times:
        if t < LOWER or t >= UPPER or t.date() <= FRESH_END:
            raise BoundaryError(f"範囲の外の candle: {t}")


def windows() -> list[tuple[dt.datetime, dt.datetime]]:
    out = []
    lo = LOWER
    while lo < UPPER:
        hi = min(lo + dt.timedelta(days=WINDOW_DAYS), UPPER)
        out.append((lo, hi))
        lo = hi
    return out


def _fmt(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def fetch(instrument: str, client: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lo, hi in windows():
        check_bounds(lo, hi)
        params = {"granularity": "M15", "price": "BA", "from": _fmt(lo), "to": _fmt(hi)}
        for attempt in range(4):
            try:
                resp = client.get_candles(instrument, params=params)
                break
            except Exception:  # noqa: BLE001 -- 一時的な失敗は再試行し、最後は上げる
                if attempt == 3:
                    raise
                time.sleep(2.0 * (attempt + 1))
        candles = [c for c in resp.get("candles", []) if c.get("complete")]
        times = [parse_oanda_time(c["time"]) for c in candles]
        check_candle_times(times)
        for c, t in zip(candles, times, strict=True):
            rows.append(
                {
                    "ts": t.isoformat(),
                    "volume": int(c.get("volume", 0)),
                    **{f"bid_{k}": float(c["bid"][k]) for k in "ohlc"},
                    **{f"ask_{k}": float(c["ask"][k]) for k in "ohlc"},
                }
            )
    seen: set[str] = set()
    out = []
    for r in rows:
        if r["ts"] not in seen:
            seen.add(r["ts"])
            out.append(r)
    return out


def load(currency: str) -> pd.DataFrame:
    """取得済みの cache を読み、範囲を再び確かめる。"""
    path = CACHE / f"{INSTRUMENTS[currency]}_M15_BA.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    frame = pd.DataFrame(rows)
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True)
    check_candle_times([t.to_pydatetime() for t in frame["ts"]])
    return frame.sort_values("ts").reset_index(drop=True)


def main() -> int:
    from dotenv import dotenv_values

    from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient

    if MANIFEST.exists():
        raise SystemExit(f"{MANIFEST} は既にある。上書きしない")
    env = dotenv_values(REPO / ".env")
    client = OandaAPIClient(
        access_token=str(env["OANDA_ACCESS_TOKEN"]),
        environment=str(env.get("OANDA_ENVIRONMENT") or "practice"),
    )
    import subprocess

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "scripts", "docs", "tests"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if dirty:
        raise SystemExit(f"dirty tree では取得しない: {dirty[:200]}")
    started = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "head": head,
        "started_utc": started,
        "endpoint": "v20 InstrumentsCandles（historical / read-only）",
        "environment": str(env.get("OANDA_ENVIRONMENT") or "practice"),
        "granularity": "M15",
        "price": "BA",
        "request_lower_utc": LOWER.isoformat(),
        "request_upper_utc_exclusive": UPPER.isoformat(),
        "instruments": {},
        "code_sha256": hashlib.sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
    }
    for cur, inst in INSTRUMENTS.items():
        rows = fetch(inst, client)
        raw = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows).encode("utf-8")
        path = CACHE / f"{inst}_M15_BA.jsonl"
        path.write_bytes(raw)
        manifest["instruments"][cur] = {
            "instrument": inst,
            "rows": len(rows),
            "first_ts": rows[0]["ts"] if rows else None,
            "last_ts": rows[-1]["ts"] if rows else None,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "file": str(path.relative_to(REPO)).replace("\\", "/"),
        }
    manifest["completed_utc"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest["instruments"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
