# ruff: noqa: E501 -- a catalogue of Japanese prose and rendered table rows
"""Markdown tables for the reframing document, rendered from the package itself.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The document embeds these tables verbatim and a test re-renders them, so a table
cannot say something the catalogue, the evidence map or the arithmetic does not.
"""

from __future__ import annotations

from scripts.research.edge_sources import candidates, capacity

ELIGIBILITY_JA = {
    candidates.ACTIVE: "対象",
    candidates.EXCLUDED: "除外（閉鎖 family の改名・救済）",
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
        "| 予測の半減期 | turnover / 年 / 単位 gross | alpha capture | cost による IR 低下 | net 0.3 / 0.5 / 0.8 に必要な gross IR | net 0.3 / 0.5 / 0.8 に必要な horizon IC | net 0.5 の日次換算 IC |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in table["rows"].items():
        gross = " / ".join(str(v) for v in row["required_gross_ir"].values())
        ic = " / ".join(f"{v:.1%}" for v in row["required_horizon_ic"].values())
        rows.append(
            f"| {key.removeprefix('half_life_')} | {row['turnover_per_unit_gross']} | {row['alpha_capture']} | "
            f"{row['cost_ir_drag']} | {gross} | {ic} | {row['daily_equivalent_ic_at_net_0_5']:.1%} |"
        )
    return rows


def event_capacity() -> list[str]:
    table = capacity.event_book_table()
    rows = [
        "| 事象 / 年 | 保有日数 | net Sharpe | 事象あたり sd（bp） | 必要 edge（課金 cost、bp） | 必要 edge（pair cost、bp） | 必要 edge（事象 sd 比、課金） | 平均同時保有 | 10% vol の片側 notional レバレッジ |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in table["rows"].items():
        sharpe = key.split("_s")[-1]
        rows.append(
            f"| {int(row['events_per_year'])} | {int(row['hold_days'])} | {sharpe} | {row['sd_per_event_bp']} | "
            f"{row['required_edge_bp_charged_cost']} | {row['required_edge_bp_pair_cost']} | "
            f"{row['required_edge_in_event_sd_charged']:.1%} | {row['mean_concurrent_positions']} | "
            f"{row['gross_leverage_at_10pct_vol']} |"
        )
    return rows


def return_capacity() -> list[str]:
    table = capacity.return_and_leverage_table()
    rows = [
        "| vol target | gross leverage | net 0.3 の年率 | net 0.5 の年率 | net 0.8 の年率 | 年 5% に必要な net Sharpe | 年 10% に必要な net Sharpe |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in table["rows"].items():
        vol = key.removeprefix("vol_")
        returns = row["annual_net_return"]
        rows.append(
            f"| {float(vol):.0%} | {row['gross_leverage']} | {returns['0.3']:.1%} | {returns['0.5']:.1%} | "
            f"{returns['0.8']:.1%} | {table['net_sharpe_needed_for_5pct'][key]} | "
            f"{table['net_sharpe_needed_for_10pct'][key]} |"
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
}


__all__ = ["TABLES"]
