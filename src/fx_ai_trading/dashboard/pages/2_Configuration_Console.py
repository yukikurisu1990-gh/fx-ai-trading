"""Configuration Console — Runtime + Bootstrap tabs (M26 Phase 3).

- Runtime tab: app_settings layer view + enqueue changes via
  ``app_settings_changes`` queue. Applied on next restart / hot-reload.
- Bootstrap tab: `.env` sink. PID-gated, atomic write, hash-only audit.
"""

from __future__ import annotations

import os

import streamlit as st
from sqlalchemy import create_engine

from fx_ai_trading.dashboard.config_console import bootstrap_view, runtime_view

st.set_page_config(
    page_title="Configuration Console",
    page_icon="⚙",
    layout="wide",
)
st.title("Configuration Console")
st.caption("app_settings & .env management · M26 Phase 3 · Demo Mode")


@st.cache_resource
def _get_engine():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    try:
        return create_engine(url)
    except Exception:
        return None


engine = _get_engine()
if engine is None:
    st.warning("DATABASE_URL is not set or could not be opened — Runtime tab will show no rows.")

tab_runtime, tab_bootstrap = st.tabs(["Runtime", "Bootstrap"])

with tab_runtime:
    runtime_view.render(engine)

with tab_bootstrap:
    bootstrap_view.render(engine)
