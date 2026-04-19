"""Panel: Market State — current phase and market indicator (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> dict:
    return {
        "phase_mode": dashboard_query_service.get_app_setting(_engine, "phase_mode"),  # type: ignore[arg-type]
        "runtime_environment": dashboard_query_service.get_app_setting(  # type: ignore[arg-type]
            _engine, "runtime_environment"
        ),
    }


def render(engine: Engine | None) -> None:
    st.subheader("Market State")
    data = _fetch(engine)
    phase = data["phase_mode"] or "—"
    env = data["runtime_environment"] or "—"
    st.metric("Phase Mode", phase)
    st.metric("Environment", env)
    if engine is None:
        st.caption("No DATABASE_URL — showing defaults")
