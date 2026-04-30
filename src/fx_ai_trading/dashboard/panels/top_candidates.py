"""Panel: Top Candidates — ranked trade candidates from TSS mart (M19-A).

Data source: dashboard_top_candidates mart (created in M20).
Returns empty list until M20 migration creates the mart table.
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_top_candidates(_engine)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("上位候補")
    rows = _fetch(engine)
    if not rows:
        st.info("候補なし（M20以降にTSSマートが生成されます）。")
        return
    display = [
        {
            "通貨ペア": r.get("instrument", ""),
            "戦略": r.get("strategy_id", ""),
            "TSSスコア": r.get("tss_score", ""),
            "方向": r.get("direction", ""),
            "ランク": r.get("rank", ""),
            "生成時刻（UTC）": str(r.get("generated_at", "")),
        }
        for r in rows
    ]
    st.dataframe(display, use_container_width=True)
