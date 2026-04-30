"""Panel: Account Summary — KPI tiles for the selected account."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=10)
def _fetch(_engine: object, account_id: str) -> dict:
    return dashboard_query_service.get_account_summary(_engine, account_id)  # type: ignore[arg-type]


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("口座サマリー")
    if not account_id:
        st.caption("サイドバーで口座を選択するとKPIを表示します。")
        return
    s = _fetch(engine, account_id)
    if s["n_trades"] == 0:
        st.info("この口座の取引はまだありません。")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("決済済み取引数", s["n_trades"])
    c2.metric("累計損益（JPY）", f"{s['total_pnl']:,.0f}")
    c3.metric("勝率", f"{s['win_rate'] * 100:.1f}%")
    c4, c5, c6 = st.columns(3)
    c4.metric("最良トレード（JPY）", f"{s['best_trade']:,.0f}")
    c5.metric("最悪トレード（JPY）", f"{s['worst_trade']:,.0f}")
    c6.metric("最大ドローダウン（JPY）", f"{s['max_drawdown']:,.0f}")
