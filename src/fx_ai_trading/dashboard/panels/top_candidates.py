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
    st.subheader("Top Candidates")
    rows = _fetch(engine)
    if not rows:
        st.info("No candidates available. (TSS mart populated after M20.)")
        return
    display = [
        {
            "Instrument": r.get("instrument", ""),
            "Strategy": r.get("strategy_id", ""),
            "TSS Score": r.get("tss_score", ""),
            "Direction": r.get("direction", ""),
            "Rank": r.get("rank", ""),
            "Generated (UTC)": str(r.get("generated_at", "")),
        }
        for r in rows
    ]
    st.dataframe(display, use_container_width=True)
