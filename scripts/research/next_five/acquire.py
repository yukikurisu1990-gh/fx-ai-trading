# ruff: noqa: E501 -- acquisition prose
"""次の 5 本の public / free data を取得し、seen span へ切り落として保存する。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: 2026-09-22 第 2 裁定 §2–§4（取得・mapping・Stage 0 再実行の承認）。

**network に出る条件は 2 つ揃ったときだけ。**

1. `NEXT_FIVE_ACQUIRE_APPROVED=1`（`data_access.fetch` が試行のたびに確認）
2. この module を **script として実行**していること

**保護期間は request から外す。** 期間 parameter を受け付ける endpoint（ALFRED / BoC /
BoJ）には seen window の 2 区間だけを request する。受け付けない endpoint（Fed H.4.1 の
一括 zip / SNB の cube）は、parse 直後・保存前に `_truncate` で落とし、保護期間の行が
残っていたら **例外で止まる**。切り落とす前の series は外へ返らない。

mapping は `series_map.SERIES_MAP` に凍結してあり、取得のたびに provider の metadata で
**意味を検証し直す**（`data_access.mapping.check_semantics`）。合わなければ保存しない。
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.acquisition_safety import digest, write_provenance
from scripts.research.data_access import mapping, providers
from scripts.research.data_access.fetch import FetchError
from scripts.research.next_five import prereg, series_map, statements

OPT_IN_ENV: Final[str] = "NEXT_FIVE_ACQUIRE_APPROVED"
OVERWRITE_ENV: Final[str] = "NEXT_FIVE_PROVENANCE_OVERWRITE_APPROVED"

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/next_five"
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/next_five/acquisition.json"

#: seen span の境界。**parsed typed date で判定する。文字列の辞書順比較はしない。**
LONG_LAST: Final[dt.date] = dt.date.fromisoformat(prereg.SPANS["long"]["last"])
RECENT_FIRST: Final[dt.date] = dt.date.fromisoformat(prereg.SPANS["recent"]["first"])
SEEN_LAST: Final[dt.date] = dt.date.fromisoformat(prereg.SPANS["recent"]["last"])
PROTECTED_FIRST: Final[dt.date] = dt.date.fromisoformat(
    prereg.PROTECTED_BOUNDS["fresh_pool"]["first"]
)
PROTECTED_LAST: Final[dt.date] = dt.date.fromisoformat(
    prereg.PROTECTED_BOUNDS["fresh_pool"]["last"]
)

#: request に入れる 2 区間（前半の始点は signal の warm-up のために十分前）
WINDOWS: Final[tuple[tuple[str, str], ...]] = (
    ("1990-01-01", LONG_LAST.isoformat()),
    (RECENT_FIRST.isoformat(), SEEN_LAST.isoformat()),
)

#: series ごとの経済変数（mapping の意味検証に使う）
VARIABLE_OF: Final[dict[str, str]] = {
    "U1": "GOODS_TRADE_BALANCE",
    "U2": "CB_TOTAL_ASSETS",
    "U4": "FX_RESERVES",
    "U5": "HY_CREDIT_SPREAD",
}
FILE_PREFIX: Final[dict[str, str]] = {"U1": "trade", "U2": "balance_sheet", "U4": "reserves"}


def is_seen(day: dt.date) -> bool:
    """**parsed typed date で判定する。** 文字列比較・部分文字列比較はしない。"""
    if not isinstance(day, dt.date) or isinstance(day, dt.datetime):
        day = dt.date(day.year, day.month, day.day)
    if day <= LONG_LAST:
        return True
    if day < RECENT_FIRST:
        #: 保護 pool と、その前後の span 外の日（2016-06-02 … 2021-04-26）
        return False
    return day <= SEEN_LAST


def _truncate(series: pd.Series, *, label: str) -> pd.Series:
    """seen window の外を落とす唯一の場所。**保護 pool の行が残れば例外で止める。**"""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError(f"{label}: DatetimeIndex でない series は切り落とせない")
    kept = series[[is_seen(stamp.date()) for stamp in series.index]]
    for stamp in kept.index:
        if PROTECTED_FIRST <= stamp.date() <= PROTECTED_LAST:
            raise AssertionError(f"{label}: 保護 pool の行が残った（{stamp.date()}）")
        if stamp.date() > SEEN_LAST:
            raise AssertionError(f"{label}: forward epoch 側の行が残った（{stamp.date()}）")
    if kept.empty:
        raise FetchError("SERIES_NOT_FOUND", f"{label}: seen window に観測が 1 つも無い")
    return kept


def _fetch_windowed(fetcher: str, args: dict[str, Any]) -> tuple[pd.Series, dict[str, Any]]:
    """期間 parameter を受け付ける provider には **2 区間だけ** を request する。"""
    if fetcher in {"alfred", "boc_valet"}:
        parts: list[pd.Series] = []
        meta: dict[str, Any] = {}
        urls: list[str] = []
        for first, last in WINDOWS:
            try:
                piece, meta = getattr(providers, fetcher)(
                    opt_in_env=OPT_IN_ENV, first=first, last=last, **args
                )
            except FetchError as error:
                if error.outcome == "PARSER_FAILURE" and "1 つも無い" in str(error):
                    continue  # その区間に観測が無い（例: HY OAS の長 span）
                raise
            parts.append(piece)
            urls.append(meta["source_url"])
        if not parts:
            raise FetchError("SERIES_NOT_FOUND", f"{args}: どちらの区間にも観測が無い")
        series = pd.concat(parts).sort_index()
        series = series[~series.index.duplicated(keep="last")]
        meta = {
            **meta,
            "source_url": " | ".join(urls),
            "request_windows": [list(w) for w in WINDOWS],
        }
        return series, meta
    series, meta = getattr(providers, fetcher)(opt_in_env=OPT_IN_ENV, **args)
    meta = {**meta, "request_windows": "FULL_SERIES_REQUESTED_TRUNCATED_BEFORE_SAVE"}
    return series, meta


def _save(name: str, series: pd.Series) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame = series.to_frame(name=name)
    frame.index.name = "date"
    path = DATA_DIR / f"{name}.parquet"
    frame.to_parquet(path)
    return digest(frame.to_csv())


def acquire_series(track: str, currency: str, spec: dict[str, Any]) -> dict[str, Any]:
    name = "credit_hy_oas" if track == "U5" else f"{FILE_PREFIX[track]}_{currency.lower()}"
    started = pd.Timestamp.now(tz="UTC").isoformat()
    try:
        raw, meta = _fetch_windowed(spec["fetcher"], spec["args"])
        semantic = mapping.check_semantics(
            VARIABLE_OF[track], f"{meta['title']} {meta.get('notes', '')}"
        )
        kept = _truncate(raw, label=name)
        saved_hash = _save(name, kept)
    except FetchError as error:
        return {
            "track": track,
            "currency": currency,
            "file": name,
            "outcome": error.outcome,
            "http_status": error.http_status,
            "error": str(error)[:300],
            "retrieval_timestamp_utc": started,
            "reading": (
                "**環境側の失敗であり、データが存在しないことを意味しない**"
                if error.outcome in {"TIMEOUT", "DNS", "TLS", "ENVIRONMENT_RETRIEVAL_FAILURE"}
                else "provider の応答 / 中身 / 意味の不一致による失敗"
            ),
        }
    record = mapping.SeriesMapping(
        track=track,
        currency=currency,
        variable=VARIABLE_OF[track],
        provider=spec["provider"],
        tier=int(spec["tier"]),
        series_id=meta["series_id"],
        official_title=meta["title"],
        units=meta["units"],
        frequency=meta["frequency"],
        seasonal_adjustment=meta["seasonal_adjustment"],
        coverage_first=str(kept.index.min().date()),
        coverage_last=str(kept.index.max().date()),
        publication_lag=str(spec["lag"]),
        revision_behavior=spec["revision"],
        source_url=meta["source_url"],
        metadata_url=meta["metadata_url"],
        retrieval_timestamp_utc=started,
        content_hash=saved_hash,
        semantic_check=semantic,
    ).as_record()
    return {
        **record,
        "file": name,
        "outcome": "OK",
        "rows_saved": int(len(kept)),
        "rows_long_span": int((kept.index.date <= LONG_LAST).sum()),
        "rows_recent_span": int((kept.index.date >= RECENT_FIRST).sum()),
        "request_windows": meta.get("request_windows"),
        "why_this_route": spec["why_this_route"],
    }


def acquire_statements() -> dict[str, Any]:
    """U3 の声明。**保護期間の日付の声明は request しない。**"""
    out: dict[str, Any] = {}
    years = range(2021, SEEN_LAST.year + 1)
    for currency in statements.LISTERS:
        name = f"tone_{currency.lower()}"
        started = pd.Timestamp.now(tz="UTC").isoformat()
        try:
            series, records = statements.tone_series(
                currency, years, opt_in_env=OPT_IN_ENV, is_seen=is_seen
            )
            kept = _truncate(series, label=name)
            saved_hash = _save(name, kept)
        except FetchError as error:
            out[currency] = {
                "file": name,
                "outcome": error.outcome,
                "error": str(error)[:300],
                "retrieval_timestamp_utc": started,
            }
            continue
        except (ValueError, KeyError, TypeError) as error:
            #: 一覧や本文の形が想定と違った — provider の不在ではなく parser の問題
            out[currency] = {
                "file": name,
                "outcome": "PARSER_FAILURE",
                "error": f"{type(error).__name__}: {error}"[:300],
                "retrieval_timestamp_utc": started,
            }
            continue
        out[currency] = {
            "file": name,
            "outcome": "OK",
            "documents": len(records),
            "coverage_first": str(kept.index.min().date()),
            "coverage_last": str(kept.index.max().date()),
            "regions": sorted({r["region"] for r in records}),
            "content_hash": saved_hash,
            "retrieval_timestamp_utc": started,
            "documents_detail": [
                {k: r[k] for k in ("date", "url", "words", "hawkish", "dovish")} for r in records
            ],
        }
    return out


def run() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for track, currencies in series_map.SERIES_MAP.items():
        for currency, spec in currencies.items():
            rows[f"{track}/{currency}"] = acquire_series(track, currency, spec)
            print(
                f"{track}/{currency:6} {rows[f'{track}/{currency}']['outcome']}",
                file=sys.stderr,
                flush=True,
            )
    tone = acquire_statements()
    for currency, row in tone.items():
        print(
            f"U3/{currency:6} {row['outcome']} docs={row.get('documents')}",
            file=sys.stderr,
            flush=True,
        )
    return {
        "cycle": prereg.CYCLE,
        "freeze_digest": prereg.freeze_digest(),
        "authority": "2026-09-22 第 2 裁定 §2–§4",
        "finished_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "scope": "public / free source のみ。paid / authenticated には触れていない",
        "series": rows,
        "statements": tone,
        "not_mapped": series_map.NOT_MAPPED,
        "protected_span_handling": (
            "期間 parameter を受け付ける endpoint には seen window の 2 区間だけを request した。"
            "受け付けない endpoint は parse 直後・保存前に切り落とし、保護 pool / forward 側の行が"
            "残れば例外で止まる"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="次の 5 本の public data を取得する")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    payload = run()
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(
        RECORD,
        payload,
        overwrite=args.overwrite,
        env_name=OVERWRITE_ENV if args.overwrite else None,
    )
    print(f"written: {RECORD} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if not os.environ.get(OPT_IN_ENV):
        print(f"{OPT_IN_ENV}=1 が無いので何もしない", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
