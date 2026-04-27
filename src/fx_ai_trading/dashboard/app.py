"""FX-AI Trading Dashboard — Streamlit entry point.

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
    account_summary,
    daily_metrics,
    daily_pnl,
    drawdown,
    equity_curve,
    execution_quality,
    hour_distribution,
    market_state,
    meta_decision,
    per_pair_performance,
    positions,
    recent_signals,
    risk_state_detail,
    strategy_breakdown,
    strategy_summary,
    supervisor_status,
    top_candidates,
    trade_outcomes,
)
from fx_ai_trading.services import dashboard_query_service

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


@st.cache_data(ttl=30)
def _list_accounts(_engine: object) -> list[dict]:
    return dashboard_query_service.list_accounts(_engine)  # type: ignore[arg-type]


def _format_account(acct: dict) -> str:
    aid = acct.get("account_id", "?")
    atype = acct.get("account_type", "?")
    cur = acct.get("base_currency", "?")
    broker = acct.get("broker_name") or acct.get("broker_id") or "?"
    return f"[{atype}] {aid} ({broker}, {cur})"


engine = _get_engine()

st.title("FX-AI Trading Dashboard")
st.caption("Phase 9.X · demo-ready · multi-account")

if engine is None:
    st.warning("DATABASE_URL not set — panels show fallback data only.")

# --- Sidebar: account switcher ---
accounts = _list_accounts(engine) if engine is not None else []
account_options: list[tuple[str | None, str]] = [(None, "All accounts")]
account_options.extend((a["account_id"], _format_account(a)) for a in accounts)
labels = [label for _, label in account_options]
selected_label = st.sidebar.selectbox(
    "Account",
    labels,
    index=0,
    help="Scope panels to a single OANDA account, or show all.",
)
selected_account_id: str | None = next(
    (aid for aid, label in account_options if label == selected_label), None
)
st.sidebar.caption(
    f"{len(accounts)} account(s) registered" if accounts else "No accounts registered yet."
)

# --- Section 1: KPI tiles ---
account_summary.render(engine, account_id=selected_account_id)
st.divider()

# --- Section 2: Equity + Drawdown ---
col_eq, col_dd = st.columns([3, 2])
with col_eq:
    equity_curve.render(engine, account_id=selected_account_id)
with col_dd:
    drawdown.render(engine, account_id=selected_account_id)
st.divider()

# --- Section 3: Daily + Hour distribution ---
col_d, col_h = st.columns(2)
with col_d:
    daily_pnl.render(engine, account_id=selected_account_id)
with col_h:
    hour_distribution.render(engine, account_id=selected_account_id)
st.divider()

# --- Section 4: Per-pair + Strategy + Outcomes ---
col_pair, col_strat, col_out = st.columns([2, 2, 1])
with col_pair:
    per_pair_performance.render(engine, account_id=selected_account_id)
with col_strat:
    strategy_breakdown.render(engine, account_id=selected_account_id)
with col_out:
    trade_outcomes.render(engine, account_id=selected_account_id)
st.divider()

# --- Section 5: Operational state (system-wide) ---
col_a, col_b, col_c = st.columns(3)
with col_a:
    market_state.render(engine)
with col_b:
    strategy_summary.render(engine)
with col_c:
    meta_decision.render(engine)
st.divider()

col_pos, col_dm = st.columns(2)
with col_pos:
    positions.render(engine, account_id=selected_account_id)
with col_dm:
    daily_metrics.render(engine, account_id=selected_account_id)
st.divider()

col_sup, col_sig = st.columns(2)
with col_sup:
    supervisor_status.render(engine)
with col_sig:
    recent_signals.render(engine, account_id=selected_account_id)
st.divider()

col_top, col_eq2, col_risk = st.columns(3)
with col_top:
    top_candidates.render(engine)
with col_eq2:
    execution_quality.render(engine, account_id=selected_account_id)
with col_risk:
    risk_state_detail.render(engine)
