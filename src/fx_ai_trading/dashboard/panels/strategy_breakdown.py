"""Panel: Strategy Breakdown — PnL contribution per strategy_id."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=15)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_strategy_breakdown(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("Strategy Breakdown")
    rows = _fetch(engine, account_id)
    if not rows:
        st.info("No closed trades yet.")
        return
    df = pd.DataFrame(rows)
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("strategy_id:N", title="Strategy", sort="-y"),
            y=alt.Y("total_pnl:Q", title="Total PnL (JPY)"),
            color=alt.condition(
                alt.datum.total_pnl >= 0,
                alt.value("#4e79a7"),
                alt.value("#e15759"),
            ),
            tooltip=["strategy_id", "n_trades", "total_pnl", "win_rate"],
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)
    df_disp = df.copy()
    df_disp["total_pnl"] = df_disp["total_pnl"].round(0).astype(int)
    df_disp["avg_pnl"] = df_disp["avg_pnl"].round(1)
    df_disp["win_rate"] = (df_disp["win_rate"] * 100).round(1).astype(str) + "%"
    st.dataframe(df_disp, use_container_width=True, hide_index=True)
