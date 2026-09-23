# ruff: noqa: E501 -- fetch prose
"""上限付きの取得と、失敗の分類（第 2 裁定 §12 / §13）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**network へ出る条件は、呼び出し側が渡した opt-in env が 1 であること。** 許可は
**試行のたびに**確かめる（再試行が guard を 1 度で済ませる抜け道にならないように）。
test 中は conftest が socket 層を塞いでいるので、ここの opt-in を消す mutation が
入っても live network へは届かない。curl 等への fallback は持たない。

分類の原則:

- **TIMEOUT を `PROVIDER_UNAVAILABLE` と書かない。** 相手が「使えない」と答えたのは
  503 のときだけである
- **HTTP 200 でも成功とは限らない。** HTML のエラーページ・login ページ・空・壊れた本文は
  `CONTENT_INVALID` にする（前 cycle で BoE の 200 エラーページを「取れた」と記録した）
- 取得できない理由が **こちら側の環境**なら `ENVIRONMENT_RETRIEVAL_FAILURE` 系に入れる。
  それは「データが存在しない」ではない
"""

from __future__ import annotations

import dataclasses
import re
import ssl
import time
import urllib.error
import urllib.request
from typing import Final

from scripts.research.acquisition_safety import digest, require_opt_in

USER_AGENT: Final[str] = "Mozilla/5.0 fx-ai-trading research data access"

#: 第 2 裁定 §13 の分類。**この 10 個以外の結果を返さない。**
HTTP_STATUS: Final[str] = "HTTP_STATUS"
TIMEOUT: Final[str] = "TIMEOUT"
DNS: Final[str] = "DNS"
TLS: Final[str] = "TLS"
CONTENT_INVALID: Final[str] = "CONTENT_INVALID"
PARSER_FAILURE: Final[str] = "PARSER_FAILURE"
SERIES_NOT_FOUND: Final[str] = "SERIES_NOT_FOUND"
SEMANTIC_MISMATCH: Final[str] = "SEMANTIC_MISMATCH"
PROVIDER_UNAVAILABLE: Final[str] = "PROVIDER_UNAVAILABLE"
ENVIRONMENT_RETRIEVAL_FAILURE: Final[str] = "ENVIRONMENT_RETRIEVAL_FAILURE"
OK: Final[str] = "OK"

CLASSES: Final[tuple[str, ...]] = (
    HTTP_STATUS,
    TIMEOUT,
    DNS,
    TLS,
    CONTENT_INVALID,
    PARSER_FAILURE,
    SERIES_NOT_FOUND,
    SEMANTIC_MISMATCH,
    PROVIDER_UNAVAILABLE,
    ENVIRONMENT_RETRIEVAL_FAILURE,
)

#: **環境側の失敗**（データは存在しうるが、ここから取れない）。
ENVIRONMENT_SIDE: Final[frozenset[str]] = frozenset(
    {TIMEOUT, DNS, TLS, ENVIRONMENT_RETRIEVAL_FAILURE}
)


@dataclasses.dataclass(frozen=True)
class Limits:
    """1 回の取得の上限。**無制限の retry はしない。**"""

    timeout_seconds: float = 45.0
    attempts: int = 3
    backoff_seconds: float = 1.5
    #: 1 回の fetch 全体にかける最長時間（retry を含む）
    deadline_seconds: float = 180.0


DEFAULT_LIMITS: Final[Limits] = Limits()


@dataclasses.dataclass(frozen=True)
class FetchResult:
    url: str
    outcome: str
    http_status: int | None
    payload: bytes | None
    content_hash: str | None
    attempts: int
    elapsed_seconds: float
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.outcome == OK


class FetchError(RuntimeError):
    """分類済みの失敗。`outcome` は必ず `CLASSES` のどれかである。"""

    def __init__(self, outcome: str, message: str, http_status: int | None = None) -> None:
        if outcome not in CLASSES:
            raise ValueError(f"未登録の失敗分類: {outcome}")
        super().__init__(message)
        self.outcome = outcome
        self.http_status = http_status


def classify(error: BaseException) -> tuple[str, int | None]:
    """例外を §13 の語彙へ落とす。**迷うものは環境側へ倒す** — 相手の不在を主張しない。

    `HTTPError` は `URLError` の subclass なので **先に** 見る（前 cycle ではこの分岐が
    無く、404 も 403 も環境のせいにしていた）。
    """
    if isinstance(error, FetchError):
        return error.outcome, error.http_status
    if isinstance(error, urllib.error.HTTPError):
        code = int(error.code)
        if code == 404:
            return SERIES_NOT_FOUND, code
        if code == 503:
            #: 相手が「今は使えない」と明言したときだけ PROVIDER_UNAVAILABLE
            return PROVIDER_UNAVAILABLE, code
        return HTTP_STATUS, code
    text = f"{type(error).__name__}: {error}"
    lowered = text.lower()
    if isinstance(error, TimeoutError) or "timed out" in lowered:
        return TIMEOUT, None
    if "getaddrinfo" in lowered or "name or service not known" in lowered or "nodename" in lowered:
        return DNS, None
    if "ssl" in lowered or "certificate" in lowered or "handshake" in lowered:
        return TLS, None
    return ENVIRONMENT_RETRIEVAL_FAILURE, None


def validate_content(payload: bytes, *, expect: str) -> None:
    """**200 が返っても data とは限らない。** 期待した形でなければ `CONTENT_INVALID`。

    `expect` は `csv` / `json` / `xml` / `zip` / `html`（テキスト archive は HTML が本体）。
    """
    if not payload or not payload.strip():
        raise FetchError(CONTENT_INVALID, "空の本文")
    #: 先頭の BOM は除いてから形を見る（Fed の press JSON は BOM 付きで、初版はこれを
    #: 「JSON の形をしていない」と誤って弾いた）
    head = payload[:600].decode("utf-8-sig", "replace").lstrip().lower()[:400]
    looks_html = head.startswith(("<!doctype", "<html")) or "<html" in head[:200]
    if expect == "html":
        #: 一覧の include 断片（ECB の年別 press 一覧など）は <html> タグを持たない。
        #: **markup を含むか**で見る
        body = payload[:8000].decode("utf-8-sig", "replace").lower()
        if not (looks_html or re.search(r"<(div|a|p|dt|dd|span|section|ul|li|h[1-6])[\s>]", body)):
            raise FetchError(CONTENT_INVALID, "HTML を期待したが markup が無い")
        if "sign in" in head and "password" in head:
            raise FetchError(CONTENT_INVALID, "login ページが返った")
        return
    if looks_html:
        raise FetchError(
            CONTENT_INVALID, f"{expect} を期待したが HTML（エラーページの可能性）が返った"
        )
    if expect == "json" and head[:1] not in ("{", "["):
        raise FetchError(CONTENT_INVALID, "JSON の形をしていない")
    if expect == "xml" and not head.startswith("<"):
        raise FetchError(CONTENT_INVALID, "XML の形をしていない")
    if expect == "zip" and not payload[:2] == b"PK":
        raise FetchError(CONTENT_INVALID, "zip の形をしていない")
    if expect == "csv" and ("," not in head and ";" not in head and "\t" not in head):
        raise FetchError(CONTENT_INVALID, "区切り文字が無い（CSV の形をしていない）")


def fetch(
    url: str,
    *,
    opt_in_env: str,
    expect: str,
    limits: Limits = DEFAULT_LIMITS,
    sleep=time.sleep,
    opener=urllib.request.urlopen,
) -> FetchResult:
    """上限付きの取得。**retry するのは環境側の一過性の失敗だけ**で、provider の status は再試行しない。"""
    started = time.monotonic()
    attempts = 0
    last_outcome = ENVIRONMENT_RETRIEVAL_FAILURE
    last_status: int | None = None
    last_error: str | None = None
    while attempts < limits.attempts:
        if time.monotonic() - started > limits.deadline_seconds:
            break
        attempts += 1
        require_opt_in(opt_in_env, what=f"fetch {url[:80]}")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with opener(
                request, timeout=limits.timeout_seconds, context=ssl.create_default_context()
            ) as response:
                payload = response.read()
            validate_content(payload, expect=expect)
            return FetchResult(
                url=url,
                outcome=OK,
                http_status=200,
                payload=payload,
                content_hash=digest(payload.decode("utf-8", "replace")),
                attempts=attempts,
                elapsed_seconds=round(time.monotonic() - started, 2),
            )
        except Exception as error:  # noqa: BLE001 - 分類するのが仕事である
            last_outcome, last_status = classify(error)
            last_error = f"{type(error).__name__}: {error}"[:240]
            if last_outcome not in ENVIRONMENT_SIDE:
                #: provider が答えた / 中身が違う — 再試行しても変わらない
                break
            sleep(limits.backoff_seconds * (2 ** (attempts - 1)))
    return FetchResult(
        url=url,
        outcome=last_outcome,
        http_status=last_status,
        payload=None,
        content_hash=None,
        attempts=attempts,
        elapsed_seconds=round(time.monotonic() - started, 2),
        error=last_error,
    )


__all__ = [
    "CLASSES",
    "CONTENT_INVALID",
    "DEFAULT_LIMITS",
    "DNS",
    "ENVIRONMENT_RETRIEVAL_FAILURE",
    "ENVIRONMENT_SIDE",
    "HTTP_STATUS",
    "OK",
    "PARSER_FAILURE",
    "PROVIDER_UNAVAILABLE",
    "SEMANTIC_MISMATCH",
    "SERIES_NOT_FOUND",
    "TIMEOUT",
    "TLS",
    "FetchError",
    "FetchResult",
    "Limits",
    "classify",
    "fetch",
    "validate_content",
]
