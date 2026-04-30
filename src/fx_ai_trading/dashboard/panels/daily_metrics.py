"""Panel: Daily Metrics — today's order counts and PnL status (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object, account_id: str | None) -> dict:
    return dashboard_query_service.get_daily_order_summary(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("本日のメトリクス")
    summary = _fetch(engine, account_id)
    col1, col2, col3 = st.columns(3)
    col1.metric("本日の注文数", summary["total"])
    col2.metric("約定", summary["filled"])
    col3.metric("キャンセル", summary["canceled"])
    if summary.get("failed", 0):
        st.warning(f"本日の失敗注文数: {summary['failed']}")
