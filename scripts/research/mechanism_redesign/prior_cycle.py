# ruff: noqa: E501 -- ruling prose
"""前 cycle（next-five、U1..U5）の確定記録（2026-09-24 Human + ChatGPT 裁定 §1–§8）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

next-five の module（`scripts/research/next_five/`）は merge 済みの evidence なので書き換えない。
裁定が付けた qualifier と status は、ここに別に置く。
"""

from __future__ import annotations

from typing import Any, Final

MERGES: Final[dict[str, dict[str, str]]] = {
    "#492": {
        "final_head": "84d78321f992094533ffd79f11b3d5571e49e3c2",
        "merge_sha": "b06436abd39a5125eccc4a733a29d873e516314f",
        "ci": "contract-tests SUCCESS / test SUCCESS",
        "method": "merge commit（#493 が #492 の commit の上に積まれているので、head を変えずに merge できる方式）",
    },
    "#493": {
        "final_head": "5465f914b6183a63437787ec0b2b83cf47970eaa",
        "merge_sha": "c95c11f6ae5f435214be9c732e74a62ee91b5929",
        "ci": "contract-tests SUCCESS / test SUCCESS",
        "method": "merge commit",
    },
    "master_after_both": {"sha": "c95c11f6ae5f435214be9c732e74a62ee91b5929"},
}

#: 裁定 §2。**clean one-shot preregistered evidence とは扱わない。**
QUALIFIER: Final[str] = "POST_EXECUTION_SHARED_DEFECT_CORRECTED_EXPLORATORY_RESULT"

RUNS: Final[dict[str, str]] = {
    "artifacts/research/next_five/development_run4.json": f"ACCEPTED_AS_AUTHORITATIVE_DEVELOPMENT_EVIDENCE · {QUALIFIER}",
    "artifacts/research/next_five/development_run2.json": "INVALID（共通基盤の date / leakage / staleness / publication timing defect。保持し、削除・弱化しない）",
    "run3（修正初版 1e9d34e）": "ABORTED_BEFORE_ANY_TRACK_COMPLETED_OUTPUT_NOT_INSPECTED",
}

#: 裁定 §3。
FINAL_STATUS: Final[dict[str, dict[str, str]]] = {
    "U1": {
        "candidate": "S29",
        "status": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        "failure": "SIGNAL_FAILURE",
    },
    "U2": {
        "candidate": "S25",
        "status": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        "failure": "primary long では実質 signal なし（gross +0.030 は null 中心と区別不能）",
        "note": "recent の正は secondary かつ不安定で、rescue に使わない",
    },
    "U3": {
        "candidate": "S27",
        "status": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        "failure": "SIGNAL_FAILURE",
    },
    "U4": {
        "candidate": "S31",
        "status": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        "failure": "SIGNAL_FAILURE",
    },
    "U5": {
        "candidate": "S07",
        "status": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        "failure": "SIGNAL_FAILURE（cost も悪化要因）",
    },
}

#: 裁定 §4。同じ candidate の別名・軽微な変形として再実行しない。
FORBIDDEN_U1_U5_RESCUES: Final[tuple[str, ...]] = (
    "horizon 変更",
    "sign flip",
    "currency subset 変更",
    "smoothing 変更",
    "staleness 最適化",
    "threshold 変更",
    "lag 変更",
    "feature 追加",
    "low-turnover redesign",
    "leverage 変更",
    "nonlinear model 追加",
)

#: 裁定 §5 / §0。**FX_HAS_NO_EDGE ではない。**
INTERPRETATION: Final[str] = (
    "今回 preregister した 5 つの mechanism / formulation が seen development で支持されなかった。"
    "primary net positive 0、null rejection 0、incremental value 実質 0、5 本中 4 本は gross から負。"
    "最大の bottleneck は signal quality。次 cycle の目的は execution rescue ではなく "
    "new expected-return mechanism discovery"
)

#: 裁定 §8。D-5 で起きたことと FX fresh pool read を区別する。
D5_DISTINCTION: Final[dict[str, str]] = {
    "what_happened": "外部 macro series（H.4.1 zip・SNB cube・BoJ 全系列・Fed ne-press.json）の full response をメモリで parse し、保存前に切り落とした",
    "what_did_not_happen": "FX fresh pool（2016-06-02 … 2021-04-25）、historical OOS、dead window、forward epoch の FX データは読んでいない",
    "prospective_rule": "外部データでも保護暦日を無制限に memory parse しない。date-bounded request が可能なら request-level exclusion 必須、bulk-only は Human + ChatGPT の例外承認まで取得しない（`data_access.request_policy`）",
}


def record() -> dict[str, Any]:
    return {
        "merges": MERGES,
        "qualifier": QUALIFIER,
        "runs": RUNS,
        "final_status": FINAL_STATUS,
        "forbidden_rescues": FORBIDDEN_U1_U5_RESCUES,
        "interpretation": INTERPRETATION,
        "d5_distinction": D5_DISTINCTION,
    }


__all__ = [
    "D5_DISTINCTION",
    "FINAL_STATUS",
    "FORBIDDEN_U1_U5_RESCUES",
    "INTERPRETATION",
    "MERGES",
    "QUALIFIER",
    "RUNS",
    "record",
]
