"""Panel: Trade Outcomes — count + PnL per close reason (TP / SL / TIME / etc)."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=15)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_trade_outcome_breakdown(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("取引結果")
    rows = _fetch(engine, account_id)
    if not rows:
        st.info("決済済み取引なし。")
        return
    df = pd.DataFrame(rows)
    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta("n_trades:Q", title="取引数"),
            color=alt.Color("reason:N", title="決済理由"),
            tooltip=["reason:N", "n_trades:Q", "total_pnl:Q"],
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)
    df_disp = df.copy()
    df_disp["total_pnl"] = df_disp["total_pnl"].round(0).astype(int)
    st.dataframe(df_disp, use_container_width=True, hide_index=True)
