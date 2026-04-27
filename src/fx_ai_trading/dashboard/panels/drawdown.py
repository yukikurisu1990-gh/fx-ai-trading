"""Panel: Drawdown — running peak-to-trough drawdown."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=10)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_equity_curve(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("Drawdown (JPY)")
    rows = _fetch(engine, account_id)
    if not rows:
        st.info("No closed trades yet.")
        return
    df = pd.DataFrame(rows)
    df["closed_at"] = pd.to_datetime(df["closed_at"])
    df["running_peak"] = df["cumulative_pnl"].cummax()
    df["drawdown"] = df["cumulative_pnl"] - df["running_peak"]
    df = df.set_index("closed_at")
    max_dd = df["drawdown"].min()
    st.metric("Max Drawdown (JPY)", f"{max_dd:,.0f}")
    st.area_chart(df[["drawdown"]], height=220, color="#e15759")
