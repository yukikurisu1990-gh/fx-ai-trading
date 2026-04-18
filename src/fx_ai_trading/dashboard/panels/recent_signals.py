"""Panel: Recent Signals — latest orders as proxy for signals (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_recent_orders(_engine, limit=20)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("Recent Signals")
    orders = _fetch(engine)
    if not orders:
        st.info("No signals recorded yet.")
        return
    display = [
        {
            "Order ID": str(o.get("order_id", ""))[:12],
            "Instrument": o.get("instrument", ""),
            "Direction": o.get("direction", ""),
            "Units": o.get("units", ""),
            "Status": o.get("status", ""),
            "Created (UTC)": str(o.get("created_at", ""))[:19],
        }
        for o in orders
    ]
    st.dataframe(display, use_container_width=True)
