# ruff: noqa: E501 -- safety prose
"""取得 route が network に出る前と、provenance を書く前に必ず通る関門。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**なぜこのモジュールがあるか。** mutation 下で `acquire()` が live network に到達し、
committed な provenance を上書きする事故が起きた。経路は 1 本ではなく、4 つの独立な
穴が直列に並んでいた:

1. `acquire()` の opt-in check は **入口に 1 回だけ**だった。それを消す mutation が
   1 つあれば、以降の fetch は無防備になる。
2. `_fetch` は `except Exception` で **conftest の socket guard が投げた RuntimeError まで
   飲み込み**、fallback に落ちた。guard が「拒否した」ことが「失敗したので次を試す」に
   化けていた。
3. その fallback は `curl` を **subprocess** で起動する。conftest の socket guard は
   Python の socket を patch しているだけなので、**子プロセスは素通り**する。
4. provenance の書き込みは無条件の `write_text` で、既存の committed ファイルを
   黙って上書きできた。

ここで潰すのは 1・2・4（3 は `tests/conftest.py` 側の subprocess guard）。**4 つは互いに
独立で、どれ 1 つでもあの連鎖を断てる**ように作ってある。mutation は 1 度に 1 箇所しか
壊さないので、これが意味を持つ。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Final


#: 拒否は失敗ではない。この型は `except Exception` に紛れて fallback へ落ちてはならず、
#: 取得 route はこれを **絶対に握りつぶさない**。名前で意図が読めるようにしてある。
class AcquisitionRefusedError(RuntimeError):
    """許可が無い、あるいは保護された対象なので取得しない。再試行してはならない。"""


class ProvenanceOverwriteRefusedError(RuntimeError):
    """既存の committed provenance を黙って上書きしようとした。"""


#: fallback が飲み込んでよい例外。ここに無いものは**すべて**呼び出し元へ抜ける。
#: `OSError` は `URLError` と `socket.timeout` の親であり、本当の通信失敗を覆う。
NETWORK_FAILURES: Final[tuple[type[BaseException], ...]] = (OSError, TimeoutError)


def require_opt_in(env_name: str, *, what: str) -> None:
    """取得 route が network に触れる **直前ごと**に呼ぶ。入口で 1 回ではない。

    入口の check だけだと、それを消す mutation 1 つで全 fetch が通ってしまう。
    fetch のたびに確認すれば、1 箇所の mutation では穴が開かない。
    """
    if os.environ.get(env_name) != "1":
        raise AcquisitionRefusedError(
            f"refused: {what} needs {env_name}=1. "
            "これは承認を記録する env であって、承認そのものではない — "
            "Human + ChatGPT の許可が先に要る。"
        )


def digest(payload: bytes | str) -> str:
    blob = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hashlib.sha256(blob).hexdigest()


def write_provenance(
    path: Path,
    payload: Any,
    *,
    overwrite: bool = False,
    env_name: str | None = None,
) -> str:
    """provenance を書く。**既存ファイルの上書きは明示モードでのみ許す。**

    既に同一内容なら何もしない（再実行が冪等であってよい）。内容が違うのに
    `overwrite=False` なら拒否する。`overwrite=True` でも、`env_name` を渡した場合は
    その env が `1` であることまで要求する — 「上書きしたい」と書けてしまうコードと、
    「上書きしてよい」と人が言った事実を分けるため。

    返り値は書かれた（あるいは既に存在した）内容の sha256。
    """
    text = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True, default=str)
    )
    new_digest = digest(text)

    if path.exists():
        current = path.read_text(encoding="utf-8")
        if digest(current) == new_digest:
            return new_digest
        if not overwrite:
            raise ProvenanceOverwriteRefusedError(
                f"refused: {path} は既に存在し、内容が異なる。"
                "committed provenance は歴史的記録であり、新しい観測は新しいファイルに書く。"
                "本当に置き換えるなら overwrite=True を明示すること。"
            )
        if env_name is not None:
            require_opt_in(env_name, what=f"overwrite {path.name}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return new_digest


#: 取得の失敗を「相手が無い」と混同しないための分類（§2 の要求）。
#: TLS 検証の失敗も 403 も、**こちら側の環境**の話であって provider の可用性ではない。
LOCAL_ENVIRONMENT: Final[str] = "LOCAL_ENVIRONMENT_FAILURE_NOT_PROVIDER_UNAVAILABLE"
NAME_RESOLUTION: Final[str] = "NAME_RESOLUTION_FAILURE"
HTTP_STATUS: Final[str] = "HTTP_STATUS_FROM_PROVIDER"
TIMEOUT: Final[str] = "TIMEOUT_NOT_PROVIDER_UNAVAILABLE"
REFUSED_BY_GUARD: Final[str] = "REFUSED_BY_GUARD_NO_REQUEST_MADE"
OK: Final[str] = "OK"


def classify_failure(error: BaseException) -> str:
    """例外を上の語彙に落とす。**判定に迷うものは local 側へ倒す** — 相手の不在を主張しない。"""
    name = type(error).__name__
    text = str(error)
    if isinstance(error, AcquisitionRefusedError):
        return REFUSED_BY_GUARD
    if "CERTIFICATE_VERIFY_FAILED" in text or "SSL" in name or "SSL" in text:
        return LOCAL_ENVIRONMENT
    if "getaddrinfo" in text or "Name or service not known" in text or "NameError" in name:
        return NAME_RESOLUTION
    if isinstance(error, TimeoutError) or "timed out" in text.lower():
        return TIMEOUT
    return LOCAL_ENVIRONMENT


__all__ = [
    "HTTP_STATUS",
    "LOCAL_ENVIRONMENT",
    "NAME_RESOLUTION",
    "NETWORK_FAILURES",
    "OK",
    "REFUSED_BY_GUARD",
    "TIMEOUT",
    "AcquisitionRefusedError",
    "ProvenanceOverwriteRefusedError",
    "classify_failure",
    "digest",
    "require_opt_in",
    "write_provenance",
]
