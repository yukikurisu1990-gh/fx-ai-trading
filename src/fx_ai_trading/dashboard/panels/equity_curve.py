"""Panel: Equity Curve — cumulative PnL over time."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=10)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_equity_curve(_engine, account_id=account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("資産推移")
    rows = _fetch(engine, account_id)
    if not rows:
        st.info("決済済み取引なし。")
        return
    df = pd.DataFrame(rows)
    df["closed_at"] = pd.to_datetime(df["closed_at"])
    df = df.set_index("closed_at")
    final_pnl = df["cumulative_pnl"].iloc[-1]
    delta_color = "normal" if final_pnl >= 0 else "inverse"
    st.metric("累積損益（JPY）", f"{final_pnl:,.0f}", delta_color=delta_color)
    st.line_chart(df[["cumulative_pnl"]], height=260)
