"""Panel: Execution Quality — fill latency, slippage, signal age (M19-A)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_execution_quality_summary(_engine)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("Execution Quality")
    rows = _fetch(engine)
    if not rows:
        st.info("No execution metrics recorded yet.")
        return
    display = [
        {
            "Order ID": r.get("order_id", ""),
            "Instrument": r.get("instrument", ""),
            "Signal Age (s)": r.get("signal_age_seconds", ""),
            "Slippage (pips)": r.get("slippage_pips", ""),
            "Fill Latency (ms)": r.get("fill_latency_ms", ""),
            "Created (UTC)": str(r.get("created_at", "")),
        }
        for r in rows
    ]
    st.dataframe(display, use_container_width=True)
