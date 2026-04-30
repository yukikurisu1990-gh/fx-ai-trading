"""Panel: Strategy Summary — order counts by direction (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_recent_orders(_engine, limit=100)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("戦略サマリー")
    orders = _fetch(engine)
    if not orders:
        st.info("注文なし。")
        return
    buy_count = sum(1 for o in orders if o.get("direction") in ("buy", "long"))
    sell_count = sum(1 for o in orders if o.get("direction") in ("sell", "short"))
    col1, col2 = st.columns(2)
    col1.metric("買いシグナル", buy_count)
    col2.metric("売りシグナル", sell_count)
