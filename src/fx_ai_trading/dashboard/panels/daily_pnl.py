"""Panel: Daily PnL — bar chart of daily PnL totals."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=15)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_daily_pnl(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("Daily PnL (last 30d)")
    rows = _fetch(engine, account_id)
    if not rows:
        st.info("No daily activity in the last 30 days.")
        return
    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["day"])
    df["total_pnl"] = df["total_pnl"].astype(float)
    df["sign"] = df["total_pnl"].apply(lambda x: "win" if x >= 0 else "loss")
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("day:T", title="Date"),
            y=alt.Y("total_pnl:Q", title="PnL (JPY)"),
            color=alt.Color(
                "sign:N",
                scale=alt.Scale(domain=["win", "loss"], range=["#4e79a7", "#e15759"]),
                legend=None,
            ),
            tooltip=["day:T", "total_pnl:Q", "n_trades:Q", "n_wins:Q", "n_losses:Q"],
        )
        .properties(height=240)
    )
    st.altair_chart(chart, use_container_width=True)
