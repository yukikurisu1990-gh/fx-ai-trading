# ruff: noqa: E501 -- a catalogue of Japanese prose and rendered table rows
"""Markdown tables for the reframing document, rendered from the package itself.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The document embeds these tables verbatim and a test re-renders them, so a table
cannot say something the catalogue, the evidence map or the arithmetic does not.
"""

from __future__ import annotations

from pathlib import Path

from scripts.research.edge_sources import candidates, capacity, leverage

ROOT = Path(__file__).resolve().parents[3]

ELIGIBILITY_JA = {
    candidates.ACTIVE: "対象",
    candidates.EXCLUDED: "除外（閉鎖 family の改名・救済）",
    candidates.INFEASIBLE: "除外（構造的に cost を超えない）",
    candidates.SUSPENDED_FAMILY: "除外（決定により停止中の family）",
    candidates.BLOCKED: "データ不可",
}


def _cell(text: str) -> str:
    return text.replace("|", "／")


def evidence_map() -> list[str]:
    rows = ["| ref | 内容 | 分類 | 記録上の status |", "| --- | --- | --- | --- |"]
    order = {klass: i for i, klass in enumerate(candidates.EVIDENCE_CLASSES)}
    for item in sorted(candidates.EVIDENCE_MAP, key=lambda e: order[e.klass]):
        rows.append(f"| {item.ref} | {_cell(item.what)} | {item.klass} | `{item.status}` |")
    return rows


def candidate_definitions() -> list[str]:
    rows = [
        "| ID | 方向 | 候補 | mechanism | information | target / horizon | architecture |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in candidates.CANDIDATES:
        rows.append(
            f"| {c.cid} | {c.direction} | {_cell(c.name)} | {_cell(c.mechanism)} | "
            f"{_cell(c.information)} | {_cell(c.target)}／{_cell(c.horizon)} | {_cell(c.architecture)} |"
        )
    return rows


def candidate_feasibility() -> list[str]:
    rows = [
        "| ID | turnover | utilisation | breadth | data | access | 既存研究との重なり | なぜ未反証か | capacity | ML の役割 | 扱い |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in candidates.CANDIDATES:
        overlap = "、".join(c.overlap) if c.overlap else "なし"
        rows.append(
            f"| {c.cid} | {_cell(c.turnover)} | {_cell(c.utilisation)} | {_cell(c.breadth)} | "
            f"{_cell(c.data)} | {_cell(c.access)} | {overlap} | {_cell(c.why_not_falsified)} | "
            f"{_cell(c.capacity)} | {_cell(c.ml_role)} | {ELIGIBILITY_JA[c.eligibility]} |"
        )
    return rows


def overlap_map() -> list[str]:
    by_ref: dict[str, list[str]] = {}
    for item in candidates.EVIDENCE_MAP:
        by_ref.setdefault(item.ref, []).append(item.klass)
    rows = ["| ID | 重なる既存研究（分類） | 扱い |", "| --- | --- | --- |"]
    for c in candidates.CANDIDATES:
        parts = []
        for ref in c.overlap:
            classes = "・".join(sorted(set(by_ref.get(ref, ["候補"]))))
            parts.append(f"{ref}（{classes}）")
        rows.append(
            f"| {c.cid} | {'、'.join(parts) if parts else 'なし（UNTESTED）'} | {ELIGIBILITY_JA[c.eligibility]} |"
        )
    return rows


def ranking() -> list[str]:
    rows = [
        "| 順位 | ID | 候補 | score | P(real) | 規模 | 稼働 | breadth | 頑健 | 情報利得 | turnover | 複雑 | 過学習 | data | 実装 | 扱い |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    by_id = {c.cid: c for c in candidates.CANDIDATES}
    for row in candidates.ranking():
        c = by_id[str(row["cid"])]
        rank = "—" if row["rank"] is None else str(row["rank"])
        rows.append(
            f"| {rank} | {c.cid} | {_cell(c.name)} | {row['score']} | {c.p_real} | {c.magnitude} | "
            f"{c.utilisation_score} | {c.breadth_score} | {c.robustness} | {c.information_gain} | "
            f"{c.turnover_cost} | {c.complexity} | {c.overfit_risk} | {c.data_burden} | "
            f"{c.engineering_burden} | {ELIGIBILITY_JA[c.eligibility]} |"
        )
    return rows


def continuous_capacity() -> list[str]:
    table = capacity.continuous_book_table()
    rows = [
        "| 予測の半減期 | turnover / 年 / 単位 gross | alpha capture | cost による IR 低下 | net 0.3 / 0.5 / 0.8 に必要な gross IR | net 0.3 / 0.5 / 0.8 に必要な horizon IC（AR(1)、breadth 4） | net 0.5 に必要な日次 IC（breadth 4 / 2） |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in table["rows"].items():
        gross = " / ".join(str(v) for v in row["required_gross_ir"].values())
        ic = " / ".join(f"{v:.1%}" for v in row["required_horizon_ic"].values())
        daily = " / ".join(f"{v:.1%}" for v in row["required_daily_ic_at_net_0_5"].values())
        rows.append(
            f"| {key.removeprefix('half_life_')} | {row['turnover_per_unit_gross']} | {row['alpha_capture']} | "
            f"{row['cost_ir_drag']} | {gross} | {ic} | {daily} |"
        )
    return rows


def event_capacity() -> list[str]:
    table = capacity.event_book_table()
    rows = [
        "| 事象 / 年 | 保有日数 | net Sharpe | 事象あたり sd（bp） | 必要 edge（課金 cost、bp） | 必要 edge（pair cost、bp） | 必要 edge（集中 position vol 7%、課金、bp） | 平均同時保有 | 保有のある日 | 10% vol の片側 notional レバレッジ（基準 / 集中） |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in table["rows"].items():
        sharpe = key.split("_s")[-1]
        rows.append(
            f"| {row['events_per_year']:g} | {row['hold_days']:g} | {sharpe} | {row['sd_per_event_bp']} | "
            f"{row['required_edge_bp_charged_cost']} | {row['required_edge_bp_pair_cost']} | "
            f"{row['required_edge_bp_charged_cost_concentrated']} | {row['mean_concurrent_positions']} | "
            f"{row['share_of_days_with_a_position']:.0%} | "
            f"{row['gross_leverage_at_10pct_vol']} / {row['gross_leverage_at_10pct_vol_concentrated']} |"
        )
    return rows


def return_capacity() -> list[str]:
    table = capacity.return_and_leverage_table()
    rows = [
        "| vol target | risk leverage C（vol target ÷ unlevered vol） | net 0.3 / 0.5 / 0.8 の年率 | 10 年の最大 DD 中央値（net 0.3 / 0.5 / 0.8） | 10 年の最大 DD 95%点（net 0.3 / 0.5 / 0.8） | 年 5% に必要な net Sharpe | 年 10% に必要な net Sharpe |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in table["rows"].items():
        vol = key.removeprefix("vol_")
        returns = " / ".join(f"{v:.1%}" for v in row["annual_net_return"].values())
        median = " / ".join(f"{v:.0%}" for v in row["median_max_drawdown_10y"].values())
        p95 = " / ".join(f"{v:.0%}" for v in row["p95_max_drawdown_10y"].values())
        rows.append(
            f"| {float(vol):.0%} | {row['risk_leverage_C']} | {returns} | {median} | {p95} | "
            f"{table['net_sharpe_needed_for_5pct'][key]} | {table['net_sharpe_needed_for_10pct'][key]} |"
        )
    return rows


def _flag(row: dict[str, object]) -> str:
    return "**loss-cut**" if row["loss_cut_on_gap"] else "なし"


def _ratio(row: dict[str, object]) -> str:
    return (
        "—（equity 消失）"
        if float(row["equity_after_gap"]) <= 0
        else str(row["maintenance_ratio_after_gap"])
    )


def pair_margin() -> list[str]:
    data = leverage.build(ROOT)["pair_margin_at_10pct_vol"]
    rows = [
        "| pair | 証拠金率（TY3 MT5 個人） | broker hard leverage A | routed notional / equity | 必要証拠金 / equity |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in data["rows"]:
        rows.append(
            f"| {row['pair']} | {row['margin_rate']:.0%} | {row['broker_hard_leverage_A']}x | "
            f"{row['routed_notional_per_equity']} | {row['required_margin_per_equity']:.4f} |"
        )
    rows.append(
        f"| **合計**（equity 1、risk leverage C {data['risk_leverage_C']}） | — | — | "
        f"**{data['total_routed_notional_B']}**（portfolio gross leverage B） | **{data['total_required_margin']:.1%}**（margin utilisation） |"
    )
    return rows


def _scenario_row(label: str, row: dict[str, object]) -> str:
    return (
        f"| {label} | {row['risk_leverage_C_mean']} / {row['risk_leverage_C_tail']} | {float(row['annual_vol']):.1%} | "
        f"{row['portfolio_gross_leverage_B_mean']} | {float(row['annual_net_return']):.1%} | "
        f"{float(row['margin_utilisation_mean']):.1%} / {float(row['margin_utilisation_at_leverage_tail']):.1%} | "
        f"{float(row['gap_loss_at_leverage_tail']):.0%} | {_ratio(row)} | {_flag(row)} | "
        f"{float(row['largest_currency_gap_before_loss_cut']):.0%} | "
        f"{float(row['p95_max_drawdown_10y_at_zero_sharpe']):.0%} / {float(row['p95_max_drawdown_10y_at_assumed_sharpe']):.0%} | "
        f"{float(row['fixed_notional_equity_after_drawdown_and_gap']):.0%} | "
        f"{'**loss-cut**' if row['fixed_notional_loss_cut'] else 'なし'} |"
    )


_SCENARIO_HEADER = [
    "| scenario | risk leverage C（平均 / tail） | 年率 vol | portfolio gross B（平均） | 年率 net（net 0.5） | margin 利用率（平均 / tail） | 20% gap の損失（tail） | gap 後の維持率 | gap で loss-cut | loss-cut までの 1 通貨 gap | 10 年最大 DD 95%点（net 0 / net 0.5） | 固定 notional の DD+gap 後 equity | 固定 notional で loss-cut |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
]


def leverage_scenarios() -> list[str]:
    data = leverage.build(ROOT)["risk_leverage_scenarios"]
    return _SCENARIO_HEADER + [
        _scenario_row(f"C = {lev}", rows["0.5"]) for lev, rows in data.items()
    ]


def vol_target_scenarios() -> list[str]:
    data = leverage.build(ROOT)["vol_target_scenarios"]
    return _SCENARIO_HEADER + [
        _scenario_row(f"vol {float(vol):.0%}", rows["0.5"]) for vol, rows in data.items()
    ]


def return_targets() -> list[str]:
    data = leverage.build(ROOT)["return_targets"]
    rows = [
        "| 年率 net 目標 | net Sharpe | 必要 vol | risk leverage C（平均 / tail） | portfolio gross B | margin 利用率（tail） | gap 後の維持率 | gap で loss-cut | 10 年最大 DD 95%点（net 0 / 仮定 Sharpe） | 固定 notional で loss-cut |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for target, by_sharpe in data.items():
        for sharpe, row in by_sharpe.items():
            rows.append(
                f"| {float(target):.0%} | {sharpe} | {float(row['required_vol']):.1%} | "
                f"{row['risk_leverage_C_mean']} / {row['risk_leverage_C_tail']} | {row['portfolio_gross_leverage_B_mean']} | "
                f"{float(row['margin_utilisation_at_leverage_tail']):.1%} | {_ratio(row)} | {_flag(row)} | "
                f"{float(row['p95_max_drawdown_10y_at_zero_sharpe']):.0%} / {float(row['p95_max_drawdown_10y_at_assumed_sharpe']):.0%} | "
                f"{'**loss-cut**' if row['fixed_notional_loss_cut'] else 'なし'} |"
            )
    return rows


def detection_capacity() -> list[str]:
    rows = [
        "| net Sharpe | 片側 5% 検定の必要年数（検出力 50%） | 同（検出力 80%） | 最初の 5 年が負になる確率（Gaussian） |",
        "| --- | --- | --- | --- |",
    ]
    negative = capacity.return_and_leverage_table()["probability_first_five_years_negative"]
    for s in capacity.NET_SHARPE_SCENARIOS:
        rows.append(
            f"| {s:g} | {capacity.sample_years_needed(s)} | {capacity.sample_years_needed(s, 0.8)} | "
            f"{negative[f'{s:g}']:.0%} |"
        )
    return rows


TABLES = {
    "evidence_map": evidence_map,
    "candidate_definitions": candidate_definitions,
    "candidate_feasibility": candidate_feasibility,
    "overlap_map": overlap_map,
    "ranking": ranking,
    "continuous_capacity": continuous_capacity,
    "event_capacity": event_capacity,
    "return_capacity": return_capacity,
    "detection_capacity": detection_capacity,
    "pair_margin": pair_margin,
    "leverage_scenarios": leverage_scenarios,
    "vol_target_scenarios": vol_target_scenarios,
    "return_targets": return_targets,
}


__all__ = ["TABLES"]
