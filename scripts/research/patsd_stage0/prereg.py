# ruff: noqa: E501 -- pre-registration prose
"""Stage 0 の凍結値（`docs/governance/patsd_stage0_ruling_2026_09_30.md`）。実行の前に固定する。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Final

CYCLE: Final[str] = "PATSD_STAGE_0_FEASIBILITY"
AUTHORIZATION: Final[str] = "R-A"

#: R-A の route（#498 §24）。3 window の seen cache だけ。
ROUTES: Final[tuple[tuple[str, str, str], ...]] = (
    ("scripts.research.exploratory_m15.momentum", "2021-04-26", "2023-04-25"),
    ("scripts.research.exploratory_m15.supplemental", "2023-04-26", "2025-04-24"),
    ("scripts.research.exploratory_m15.bars", "2025-04-25", "2025-12-28"),
)
FIRST_DAY: Final[str] = "2021-04-26"
LAST_DAY: Final[str] = "2025-12-28"
FRESH_POOL: Final[tuple[str, str]] = ("2016-06-02", "2021-04-25")

TIMEFRAMES: Final[tuple[str, ...]] = ("M15", "H1", "H4", "D")

# ----------------------------------------------------------------------
# S0-1: cost economics
# ----------------------------------------------------------------------
#: 標準の想定（template ごとの平均保有、営業日）。T = 年間営業日 / 保有 = 往復回数 / 年 / pair
STANDARD_HOLD_DAYS: Final[dict[str, float]] = {"M15": 0.25, "H1": 1.0, "H4": 5.0, "D": 20.0}
COST_DEFINITION: Final[str] = (
    "round trip cost（return 単位）= bar の終値時点の spread / mid（ask で買い bid で売る。片道は半 spread）。"
    "rollover の bar（21:55–22:15 UTC に掛かる M15）は entry / exit に使わないので、統計から除く"
)
DRAG_DEFINITION: Final[str] = (
    "Sharpe drag = T × c / σ_annual（pair の年率 vol、日次 mid の log return から）。vol target に依らない"
)
S0_1_BANDS: Final[dict[str, float]] = {"green_max": 0.5, "amber_max": 1.0}
S0_1_TIMEFRAME: Final[str] = "H4"

# ----------------------------------------------------------------------
# S0-2 / S0-3: selection pipeline の帰無較正と G4
# ----------------------------------------------------------------------
WARMUP_BUSINESS_DAYS: Final[int] = 100
FIRST_TRAINING_YEARS: Final[float] = 1.0
MAX_HOLD_BUSINESS_DAYS: Final[int] = 20

BUDGET: Final[dict[str, Any]] = {
    "families": 4,
    "architectures_per_family": 3,
    "grid": {"entry_prob_per_h4_bar": (1 / 60, 1 / 30, 1 / 15), "hold_h4_bars": (6, 30, 90)},
    "exits": ("fixed_horizon", "time_stop_uniform_half_to_full"),
    "rule_trials": 216,
    "l2_filters_per_family": 2,
    "l2_top_configs": 3,
    "l2_trials": 48,
    "ml_families": 2,
    "ml_models": 2,
    "ml_hp": 6,
    "ml_targets": 2,
    "ml_top_k": (0.2, 0.4, 0.6),
    "ml_trials": 144,
    "reserve": 192,
    "cap": 600,
}
SYNTHETIC: Final[dict[str, str]] = {
    "method": "vector sign randomization: seen の H4 mid log return に、時点ごとに全 pair 共通の ±1 を掛ける",
    "preserves": "|r|・vol の塊・pair 間の相関",
    "destroys": "方向の情報",
    "circular_shift": "使わない（実価格の経路の上で候補 position の損益を計算することになり、R-A の禁止に当たる）",
}
NULL_REPLICATIONS: Final[int] = 200
INJECTION_REPLICATIONS: Final[int] = 200
INJECTED_TRUE_SHARPES: Final[tuple[float, ...]] = (1.0, 1.1, 1.5, 2.0)
NEIGHBOUR_SIGNAL_SHARE: Final[float] = 0.8
SEED: Final[int] = 20260930

SELECTION: Final[dict[str, Any]] = {
    "U": "median_fold(縮小 net Sharpe) − 1.0 × fold 間の SD − 0.5 × cost ×1.5 での低下 − tier penalty（S=0）− 0.3 × 集中度（ここでは 0）",
    "hard_filters": (
        "TC-net OOF > 0 at cost ×1.5",
        "plateau: 近傍（中心 + 隣接格子点）の 70% 以上が中心と同符号、かつ近傍の中央値 > 0",
        "deflated Sharpe の p ≤ p*",
        "fold: 60% 以上の四半期で正、最悪の fold Sharpe ≥ −1 SE",
        "baseline margin: OOF net Sharpe ≥ 最良の baseline + 0.3",
        "tail: 置き換えの規則には escalation が無いので自動で通す（限界として開示）",
    ),
    "dsr_ladder": (0.10, 0.05, 0.025, 0.01, 0.005, 0.001),
    "effective_trials": "fold 外の日次 net P&L の相関を平均 linkage で階層 clustering し、相関 ≥ 0.8（距離 ≤ 0.2）を 1 つにまとめた cluster 数",
    "finalists": 3,
    "portfolio": "finalist の fold 外の日次 P&L を単位 vol に揃えて等ウェイト",
    "false_pass": "1 replication で hard filter を全て通る trial が 1 つでもあれば誤合格（family-wise）",
}
S0_2_BANDS: Final[dict[str, Any]] = {"target_rate": 0.10, "green_min_p": 0.01}

PRIOR: Final[dict[str, float]] = {"mu": 0.07, "tau": 0.565}
G4_THRESHOLD: Final[float] = 1.0
G4_DEFINITION: Final[str] = (
    "primary: hard filter（deflated Sharpe の p ≤ p* を含む）を通った finalist の portfolio の縮小 Sharpe ≥ 1.0、"
    "かつ注入した system（またはその派生）が finalist に入る。感度: 点推定の deflation（観測 − SE × E[max_Neff]）"
)
S0_3_BANDS: Final[dict[str, float]] = {"green_min": 0.30, "amber_min": 0.20}
S0_3_TRUE_SHARPE: Final[float] = 1.5

# ----------------------------------------------------------------------
# S0-4 / S0-5
# ----------------------------------------------------------------------
S0_4_BANDS: Final[str] = (
    "GREEN: fresh の価格の読み取り無し + 外部情報の露出が限定。AMBER: 価格の重なりの可能性が未解決か、露出が広い。RED: 価格の読み取りを確認"
)
S0_5_BANDS: Final[dict[str, int]] = {"green_min": 4, "amber_min": 2}

# ----------------------------------------------------------------------
# freeze digest
# ----------------------------------------------------------------------
_REPO: Final[Path] = Path(__file__).resolve().parents[3]
CLOSURE_ROOT: Final[str] = "scripts/research/patsd_stage0/run.py"


def code_closure() -> tuple[str, ...]:
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
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level != 0:
                    raise ValueError(f"{path}: 相対 import は閉包の外に出る")
                if node.module:
                    names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                if name.startswith("scripts"):
                    target = module_file(name)
                    if target is not None and target not in seen:
                        stack.append(target)
    return tuple(sorted(str(p.relative_to(_REPO)).replace("\\", "/") for p in seen))


def _sha(relative: str) -> str:
    return hashlib.sha256((_REPO / relative).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _payload() -> dict[str, Any]:
    constants = {
        k: v
        for k, v in globals().items()
        if k.isupper() and not k.startswith("_") and isinstance(v, (str, int, float, tuple, dict))
    }
    return {
        "constants": json.loads(json.dumps(constants, ensure_ascii=False, default=str)),
        "ruling_doc_sha256": _sha("docs/governance/patsd_stage0_ruling_2026_09_30.md"),
        "code_closure_sha256": {p: _sha(p) for p in code_closure()},
    }


def freeze_digest() -> str:
    return hashlib.sha256(
        json.dumps(_payload(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
