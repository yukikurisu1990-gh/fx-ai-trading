"""Panel: Risk State Detail — recent RiskManager accept/reject decisions (M19-A)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_risk_state_detail(_engine)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("リスク状態詳細")
    rows = _fetch(engine)
    if not rows:
        st.info("リスクイベントなし。")
        return
    display = [
        {
            "通貨ペア": r.get("instrument", ""),
            "判定": r.get("verdict", ""),
            "制約": str(r.get("constraint_violated", "") or ""),
            "サイクルID": r.get("cycle_id", ""),
            "時刻（UTC）": str(r.get("event_time_utc", ""))[:19],
        }
        for r in rows
    ]
    has_rejects = any(r.get("verdict") == "reject" for r in rows)
    if has_rejects:
        st.warning("直近リスク拒否あり。")
    st.dataframe(display, use_container_width=True)
