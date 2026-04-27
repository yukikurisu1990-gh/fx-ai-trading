"""Panel: Recent Signals — latest orders as proxy for signals (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_recent_orders(  # type: ignore[arg-type]
        _engine, limit=20, account_id=account_id
    )


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("直近シグナル")
    orders = _fetch(engine, account_id)
    if not orders:
        st.info("シグナルなし。")
        return
    display = [
        {
            "注文ID": str(o.get("order_id", ""))[:12],
            "通貨ペア": o.get("instrument", ""),
            "方向": o.get("direction", ""),
            "数量": o.get("units", ""),
            "ステータス": o.get("status", ""),
            "作成時刻（UTC）": str(o.get("created_at", ""))[:19],
        }
        for o in orders
    ]
    st.dataframe(display, use_container_width=True)
