"""Panel: Risk State Detail — recent RiskManager accept/reject decisions (M19-A)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_risk_state_detail(_engine)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("Risk State Detail")
    rows = _fetch(engine)
    if not rows:
        st.info("No risk events recorded yet.")
        return
    display = [
        {
            "Instrument": r.get("instrument", ""),
            "Decision": r.get("decision", ""),
            "Reason Codes": str(r.get("reason_codes", "") or ""),
            "Cycle ID": r.get("cycle_id", ""),
            "Time (UTC)": str(r.get("event_time_utc", "")),
        }
        for r in rows
    ]
    # Highlight rejects
    has_rejects = any(r.get("decision") == "reject" for r in rows)
    if has_rejects:
        st.warning("Recent risk rejections detected.")
    st.dataframe(display, use_container_width=True)
