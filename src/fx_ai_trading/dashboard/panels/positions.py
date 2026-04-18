"""Panel: Positions — current open positions (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_open_positions(_engine)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("Open Positions")
    rows = _fetch(engine)
    if not rows:
        st.info("No open positions.")
        return
    display = [
        {
            "Instrument": r.get("instrument", ""),
            "Type": r.get("event_type", ""),
            "Units": r.get("units", ""),
            "Avg Price": r.get("avg_price", ""),
            "Unrealized PL": r.get("unrealized_pl", ""),
            "Time (UTC)": str(r.get("event_time_utc", "")),
        }
        for r in rows
    ]
    st.dataframe(display, use_container_width=True)
