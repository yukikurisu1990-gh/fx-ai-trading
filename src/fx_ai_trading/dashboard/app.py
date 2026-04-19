"""FX-AI Trading Dashboard — Streamlit entry point (M12).

Launch:
    streamlit run src/fx_ai_trading/dashboard/app.py

Requires DATABASE_URL env var for live data.
Panels degrade gracefully when DATABASE_URL is unset.
"""

from __future__ import annotations

import os

import streamlit as st
from sqlalchemy import create_engine

from fx_ai_trading.dashboard.panels import (
    daily_metrics,
    execution_quality,
    market_state,
    meta_decision,
    positions,
    recent_signals,
    risk_state_detail,
    strategy_summary,
    supervisor_status,
    top_candidates,
)

st.set_page_config(
    page_title="FX-AI Trading Dashboard",
    page_icon="📈",
    layout="wide",
)


@st.cache_resource
def _get_engine():
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        return None
    return create_engine(db_url)


engine = _get_engine()

st.title("FX-AI Trading Dashboard")
st.caption("paper mode · Iteration 2 · M19")

if engine is None:
    st.warning("DATABASE_URL not set — panels show fallback data only.")

# --- Row 1: three columns ---
col_a, col_b, col_c = st.columns(3)
with col_a:
    market_state.render(engine)
with col_b:
    strategy_summary.render(engine)
with col_c:
    meta_decision.render(engine)

st.divider()

# --- Row 2: two columns ---
col_d, col_e = st.columns(2)
with col_d:
    positions.render(engine)
with col_e:
    daily_metrics.render(engine)

st.divider()

# --- Row 3: two columns ---
col_f, col_g = st.columns(2)
with col_f:
    supervisor_status.render(engine)
with col_g:
    recent_signals.render(engine)

st.divider()

# --- Row 4: three columns (M19) ---
col_h, col_i, col_j = st.columns(3)
with col_h:
    top_candidates.render(engine)
with col_i:
    execution_quality.render(engine)
with col_j:
    risk_state_detail.render(engine)
