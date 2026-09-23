# ruff: noqa: E501 -- pre-registration prose
"""**M15 / M16 の修正版の事前登録**（2026-09-24 第 3 裁定 §14–§39）。alpha を見る前に凍結する。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`PRODUCTION_READINESS_NOT_CLAIMED` · **`POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY`**.

**clean preregistered evidence でも confirmation evidence でもない。** M16 の結果（欠陥のある book の値と、
設計どおりの book に当たる band 0.05 の感度行）を見た後の実行である（§3）。

変えたのは **book の rebalance の単位だけ**（`book.factor_rebalance`、basket を 1 単位にする）。
signal・符号・horizon・universe・basket の構成と重み・band 幅・rebalance の頻度・leverage・cost・null・
nuisance は mechanism redesign の凍結（`a4413d63…`）と同じである。
新しく決めたのは **financing の扱い**で、実際の OANDA financing の履歴が公開されていないので
`APPROXIMATE_RESEARCH_FINANCING` の markup band で符号の頑健性を見る。

**pre-alpha amendment（独立 review 2 役の後、alpha 前）**:

- **routing（Role 2 RF-2）**: equal-split の pair book は recent の 20 pair で外国脚の実際の exposure が最大
  2.08 倍ずれる。book を **USD numeraire**（7 本の USD pair だけに振る）で測り、実際の通貨 exposure を
  USD 対 7 通貨等ウェイトにする。P&L・vol targeting・carry をすべてこの座標で測る。
- **carry の金利基準（Role 1 B-1）**: signal と同じ lag 付き 3 か月金利で carry を測ると会計が feature の関数に
  なる。primary は**当時の政策金利**（BIS 月末値を翌月に使う）、lag 付き 3 か月金利は感度。
- **判定の頑健性（R-4）**: 符号は 金利基準 2 × markup 4 の 8 セル全点、STRONG / MARGINAL の core 条件は
  不利な端点（政策金利・markup 最大）でも満たすこと。
- **既に見ている値（Role 1 R-5 / Role 2 RF-1）**: 修正版の book の position は、旧実装の band 0.05 感度行と
  完全に同じ（M15 と M16 の**両方**、band 0.05 / 0.10 / 0.20 でも同じ）。旧記録の M16 net 0.279・M15 net 0.102 は
  equal-split の座標・lag 付き 3 か月金利の carry での値なので、routing と carry 基準を直した今回の値とは
  完全には一致しないが、**long の central の大きさと符号はほぼ既知**である。新しい情報は routing 修正後の値・
  spot / carry / markup の分解・8 セル・null・recent である。
- **band の感度は構造的に情報を持たない（O-1）**: factor book の target は符号でしか変わらないので、band が
  0.5 未満ならどの値でも同じ book になる。`implementation_tolerance_band` の感度行は報告するが、
  「band に頑健」とは書かない。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final

from scripts.research.mechanism_redesign import prereg as _mr
from scripts.research.usd_factor_financing import financing_audit

CYCLE: Final[str] = "USD_FACTOR_CORRECTED_AND_FINANCING_2026_09"
QUALIFIER: Final[str] = "POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY"
EXECUTION_ORDER: Final[tuple[str, ...]] = ("M15", "M16")
SPANS: Final[tuple[str, ...]] = ("long", "recent")
PRIMARY_SPAN: Final[str] = "long"

#: mechanism redesign の凍結からそのまま持ってくるもの（値を payload に書き込む）。
BOOK_CONFIG: Final[dict[str, Any]] = {
    **{k: v for k, v in _mr.BOOK_CONFIG.items() if not k.startswith("why_")},
    **_mr.BOOK_CONFIG_DEVIATIONS["M15"],
}
BOOK_REPAIR: Final[dict[str, str]] = {
    "rebalance": "factor_rebalance（basket 全体を 1 単位。どれかの脚の gap が band を超えたら全脚を target へ、超えなければ全脚を据え置く）",
    "routing": "USD numeraire: 外国 7 通貨それぞれを USD pair 1 本で持つ。P&L = x · R（R_c は c の対 USD log return、R_USD = 0）。実際の通貨 exposure が x と一致する",
    "band": "0.10（変えない）",
    "basket": "USD 対 EUR / JPY / GBP / AUD / CAD / CHF / NZD の等ウェイト（linear mapping、weight_cap 0.5。元の凍結どおり）",
    "why_this_is_the_natural_repair": (
        "元の凍結の意味は『USD 対 7 通貨 basket の 1 つの factor』。通貨ごとの band は factor の book では通貨を落とすので、"
        "band を factor（book 全体）に当てるのが凍結の意味に最も近い。band 幅・頻度は変えない"
    ),
    "verified_before_alpha": "tests/research/test_usd_factor_book.py — 7 通貨すべてに等しい exposure、USD が basket と釣り合う、USD は通貨 gross の半分、band 0.05 / 0.10 / 0.20 のどれでも通貨が消えない、pair への routing が x·e を保つ、既定の rebalance では construction.run_book と完全一致",
}

SIGNALS: Final[dict[str, str]] = {
    "M15": "mechanism_redesign.signals.dollar_carry（d = 外国 7 通貨の 3 か月金利平均 − 米 3 か月金利、d > 0 でドル売り）。変更なし",
    "M16": "mechanism_redesign.signals.us_macro_momentum（M11 の score の USD 成分の符号、> 0 でドル買い）。変更なし",
}

FINANCING: Final[dict[str, Any]] = {
    "name": "APPROXIMATE_RESEARCH_FINANCING（actual OANDA financing ではない）",
    "carry": financing_audit.APPROXIMATION["interest_differential"],
    "rate_bases": {
        "policy_contemporaneous": "PRIMARY。BIS 政策金利の月末値を、その月末から（翌月の各日に）使う。signal の series ではない",
        "three_month_lagged": "SENSITIVITY。signal と同じ lag 付き 3 か月銀行間金利（mechanism redesign の carry 近似）",
    },
    "carry_formula": "Σ_c x_c × (r_c − r_USD) × 暦日 / 365（和がゼロの exposure なので numeraire に依らない）。金利が無い通貨は 0",
    "jpy_policy_zero_periods": (
        ("1999-02-12", "2000-09-29"),
        ("2001-03-19", "2006-07-31"),
        ("2013-04-04", "2016-06-01"),
    ),
    "jpy_policy_zero_periods_why": (
        "**判断**。BIS は BoJ のゼロ金利政策・量的緩和・量的質的緩和の期間に数値の政策金利を持たない。"
        "この間の無担保コール翌日物は 0〜0.1% 程度で、その期間に BIS の値が欠けている日だけ 0% と置く"
    ),
    "markup_unit": "pair notional 1 単位あたりの年率（USD pair 7 本の |notional| の和）。OANDA の financing は position の notional に課される",
    "markup_band": (0.0, 0.005, 0.01, 0.02),
    "central_markup": 0.005,
    "markup_band_equivalence": "通貨 gross 1 単位あたりでは {0, 0.25, 0.5, 1.0}%/年（mechanism redesign の band と同じ経済量）。端点 2%/年の根拠となる公開の値は無い（仮定）",
    "adverse_endpoint": "policy_contemporaneous × markup 0.02",
    "lines_reported": (
        "spot（signal の方向の寄与）",
        "spread cost",
        "carry（金利差の受け払い）",
        "markup（仮定）",
        "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING = spot − spread",
        "TOTAL_ECONOMIC(basis, m) = spot + carry(basis) − spread − m × pair notional、basis 2 × m 4 の 8 セル",
    ),
    "pnl_source_label": "SPOT_AND_FINANCING_BOTH_POSITIVE / SPOT_DRIVEN_FINANCING_NEGATIVE / FINANCING_DRIVEN_SPOT_NOT_POSITIVE / NEITHER_POSITIVE（central で機械的に付ける）",
    "signal_vs_financing": "financing で総合が良くなっても『signal alpha が強い』とは書かない。spot と carry を必ず分ける（§32–§34）",
}

NULL: Final[dict[str, Any]] = {
    "method": "circular shift of the signal（持続性を保つ）。各 draw で同じ book・同じ carry・同じ markup を当てる",
    "draws": 1000,
    "seed": 20260925,
    "statistics": (
        "TOTAL_ECONOMIC(central markup) の Sharpe（経済判定用）",
        "NET_EX_FINANCING の Sharpe（signal の効き目の診断。M16 は特にこちらで signal を読む）",
    ),
    "is_the_only_gate": False,
    "multiplicity": "2 本を同じ null に当てるので、帰無でもどちらかが 5% を切る確率は約 10%",
}

DEVELOPMENT_ECONOMICS: Final[dict[str, Any]] = {
    **_mr.DEVELOPMENT_ECONOMICS,
    "judged_on": "TOTAL_ECONOMIC(central markup) の primary span（long）",
    "dollar_breadth_rule": _mr.DOLLAR_TRACK_BREADTH_RULE,
}
POWER_RULE: Final[dict[str, Any]] = _mr.POWER_RULE

VERDICT_LOGIC: Final[tuple[dict[str, str], ...]] = (
    {
        "if": "rename gate（M15 と M16 の USD 列の相関、T5 との相関）が 0.8 以上",
        "then": "RENAME_OF_A_PRIOR_TRACK",
    },
    {
        "if": "金利基準 2 × markup 4 の 8 セルで TOTAL_ECONOMIC の符号が揃わない",
        "then": "FINANCING_NOT_DECISION_GRADE",
    },
    {"if": "TOTAL_ECONOMIC が 8 セル全点で ≤ 0", "then": "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"},
    {
        "if": "8 セル全点で正、central で E1〜E8 すべて真、不利な端点でも core 真、null p ≤ 0.05、有効標本数 ≥ 10",
        "then": "STRONG_EXPLORATORY_CANDIDATE",
    },
    {
        "if": "8 セル全点で正、central と不利な端点の両方で core（E1 / E3 / E4 / E7）真、null percentile ≥ 0.80、有効標本数 ≥ 10",
        "then": "MARGINAL_EXPLORATORY_CANDIDATE",
    },
    {"if": "全点で正だがそれ以外", "then": "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"},
)
FAILURE_CLASS: Final[dict[str, str]] = {
    "spot ≤ 0 かつ total ≤ 0": "SIGNAL_FAILURE",
    "spot > 0 だが spread で ≤ 0": "COST_FAILURE",
    "spot − spread > 0 だが financing（carry − markup）で ≤ 0": "FINANCING_FAILURE",
}
NEVER: Final[str] = "CONFIRMED とは呼ばない。forward / fresh へ進まない（§30）"

NUISANCE_APPLIES: Final[dict[str, tuple[str, ...]]] = {
    "M15": _mr.NUISANCE_APPLIES["M15"],
    "M16": _mr.NUISANCE_APPLIES["M16"],
}
RENAME_GATES: Final[dict[str, dict[str, Any]]] = {
    "M15": {"gates": ("T5_TIC_FLOW", "M16_WITHIN_CYCLE")},
    "M16": {"gates": ("T5_TIC_FLOW", "M15_WITHIN_CYCLE")},
    "rule": _mr.RENAME_NOT_EVALUABLE_RULE,
    "threshold": 0.8,
}

CAPACITY: Final[dict[str, Any]] = {
    **_mr.CAPACITY_REPORTING,
    "only_if": "TOTAL_ECONOMIC が 8 セル全点で正",
    "also_report": (
        *_mr.CAPACITY_REPORTING["also_report"],
        "financing_burden_or_benefit_at_scenario",
    ),
}

_REPO: Final[Path] = Path(__file__).resolve().parents[3]
CLOSURE_ROOT: Final[str] = "scripts/research/usd_factor_financing/driver.py"
INPUT_MANIFEST: Final[str] = "artifacts/research/mechanism_redesign/inputs_manifest_v2.json"


def code_closure() -> tuple[str, ...]:
    import ast

    def module_file(module: str) -> Path | None:
        base = _REPO / Path(*module.split("."))
        if base.with_suffix(".py").exists():
            return base.with_suffix(".py")
        if (base / "__init__.py").exists():
            return base / "__init__.py"
        return None

    seen: set[Path] = set()
    stack = [_REPO / CLOSURE_ROOT]
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        parent = path.parent
        while parent != _REPO and (parent / "__init__.py").exists():
            if parent / "__init__.py" not in seen:
                stack.append(parent / "__init__.py")
            parent = parent.parent
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
            for name in names:
                if name.startswith("scripts"):
                    target = module_file(name)
                    if target is not None and target not in seen:
                        stack.append(target)
    return tuple(sorted(str(p.relative_to(_REPO)).replace("\\", "/") for p in seen))


def _sha(relative: str) -> str:
    raw = (_REPO / relative).read_bytes().replace(b"\r\n", b"\n")
    if relative == CLOSURE_ROOT:
        raw = b"\n".join(line for line in raw.split(b"\n") if not line.startswith(b"FROZEN_DIGEST"))
    return hashlib.sha256(raw).hexdigest()


def _payload() -> dict[str, Any]:
    return {
        "cycle": CYCLE,
        "qualifier": QUALIFIER,
        "execution_order": list(EXECUTION_ORDER),
        "spans": list(SPANS),
        "primary_span": PRIMARY_SPAN,
        "book_config": BOOK_CONFIG,
        "book_repair": BOOK_REPAIR,
        "signals": SIGNALS,
        "financing": FINANCING,
        "null": NULL,
        "development_economics": DEVELOPMENT_ECONOMICS,
        "power_rule": POWER_RULE,
        "verdict_logic": [dict(row) for row in VERDICT_LOGIC],
        "failure_class": FAILURE_CLASS,
        "never": NEVER,
        "nuisance_applies": {k: list(v) for k, v in NUISANCE_APPLIES.items()},
        "rename_gates": RENAME_GATES,
        "capacity": CAPACITY,
        "mechanism_redesign_freeze_used_for_signals": _mr.freeze_digest(),
        "code_closure_sha256": {path: _sha(path) for path in code_closure()},
        "input_manifest_sha256": hashlib.sha256(
            (_REPO / INPUT_MANIFEST).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
    }


def freeze_digest() -> str:
    return hashlib.sha256(
        json.dumps(_payload(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


__all__ = ["BOOK_CONFIG", "EXECUTION_ORDER", "FINANCING", "NULL", "QUALIFIER", "freeze_digest"]
