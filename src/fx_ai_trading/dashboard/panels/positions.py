"""Panel: Positions — current open positions (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_open_positions(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("オープンポジション")
    rows = _fetch(engine, account_id)
    if not rows:
        st.info("オープンポジションなし。")
        return
    display = [
        {
            "通貨ペア": r.get("instrument", ""),
            "種別": r.get("event_type", ""),
            "数量": r.get("units", ""),
            "平均価格": r.get("avg_price", ""),
            "含み損益": r.get("unrealized_pl", ""),
            "時刻（UTC）": str(r.get("event_time_utc", "")),
        }
        for r in rows
    ]
    st.dataframe(display, use_container_width=True)
