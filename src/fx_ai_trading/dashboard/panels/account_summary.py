"""Panel: Account Summary — KPI tiles for the selected account."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=10)
def _fetch(_engine: object, account_id: str) -> dict:
    return dashboard_query_service.get_account_summary(_engine, account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("Account Summary")
    if not account_id:
        st.caption("Select a single account in the sidebar to see its KPI tiles.")
        return
    s = _fetch(engine, account_id)
    if s["n_trades"] == 0:
        st.info("No trades for this account yet.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Closed trades", s["n_trades"])
    c2.metric("Total PnL (JPY)", f"{s['total_pnl']:,.0f}")
    c3.metric("Win rate", f"{s['win_rate'] * 100:.1f}%")
    c4, c5, c6 = st.columns(3)
    c4.metric("Best trade", f"{s['best_trade']:,.0f}")
    c5.metric("Worst trade", f"{s['worst_trade']:,.0f}")
    c6.metric("Max drawdown", f"{s['max_drawdown']:,.0f}")
