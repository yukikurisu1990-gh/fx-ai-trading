"""Panel: Execution Quality — fill latency, slippage, signal age (M19-A)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object, account_id: str | None) -> list[dict]:
    return dashboard_query_service.get_execution_quality_summary(  # type: ignore[arg-type]
        _engine, account_id=account_id
    )


def render(engine: Engine | None, account_id: str | None = None) -> None:
    st.subheader("執行品質")
    rows = _fetch(engine, account_id)
    if not rows:
        st.info("執行メトリクスなし。")
        return
    display = [
        {
            "注文ID": str(r.get("order_id", ""))[:12],
            "シグナル経過（秒）": r.get("signal_age_seconds", ""),
            "スリッページ（pips）": r.get("slippage_pips", ""),
            "レイテンシ（ms）": r.get("latency_ms", ""),
            "記録時刻（UTC）": str(r.get("recorded_at", ""))[:19],
        }
        for r in rows
    ]
    st.dataframe(display, use_container_width=True)
