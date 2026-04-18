"""Panel: Supervisor Status — recent lifecycle events (M12)."""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service


@st.cache_data(ttl=5)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_recent_supervisor_events(_engine, limit=8)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("Supervisor Status")
    events = _fetch(engine)
    if not events:
        st.info("No supervisor events recorded.")
        return
    for ev in events:
        event_type = ev.get("event_type", "?")
        ts = str(ev.get("event_time_utc", ""))[:19]
        run_id = ev.get("run_id") or "—"
        st.text(f"[{ts}] {event_type}  run={run_id}")
