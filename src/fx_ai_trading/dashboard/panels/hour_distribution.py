"""Panel: Hour-of-Day Distribution — trade frequency + avg PnL by UTC hour."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=30)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_hourly_distribution(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("時間帯別分布（UTC）")
    rows = _fetch(engine, account_id)
    if not rows:
        st.info("決済済み取引なし。")
        return
    df = pd.DataFrame(rows)
    df = df.set_index("hour").reindex(range(24), fill_value=0).reset_index()
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("hour:O", title="時（UTC）"),
            y=alt.Y("n_trades:Q", title="取引数"),
            color=alt.Color(
                "avg_pnl:Q",
                title="平均損益",
                scale=alt.Scale(scheme="redblue", domainMid=0),
            ),
            tooltip=["hour:O", "n_trades:Q", "avg_pnl:Q", "total_pnl:Q"],
        )
        .properties(height=200)
    )
    st.altair_chart(chart, use_container_width=True)
