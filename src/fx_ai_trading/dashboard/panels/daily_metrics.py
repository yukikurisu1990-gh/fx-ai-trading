"""Panel: Daily Metrics — today's order counts and PnL status (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object, account_id: str | None) -> dict:
    return dashboard_query_service.get_daily_order_summary(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("Daily Metrics")
    summary = _fetch(engine, account_id)
    col1, col2, col3 = st.columns(3)
    col1.metric("Orders today", summary["total"])
    col2.metric("Filled", summary["filled"])
    col3.metric("Canceled", summary["canceled"])
    if summary.get("failed", 0):
        st.warning(f"Failed orders today: {summary['failed']}")
