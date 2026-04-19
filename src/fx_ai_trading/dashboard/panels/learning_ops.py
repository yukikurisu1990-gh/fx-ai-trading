"""Panel: Learning Jobs — training job enqueue, status, and history (M21 / M-LRN-1).

Displays recent training jobs from system_jobs.
Provides an 'Enqueue Training Job' button that inserts a pending job via
LearningOps service.  The stub executor immediately marks it succeeded;
Phase 7 replaces the executor with a real implementation.
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.services import dashboard_query_service
from fx_ai_trading.services.learning_ops import _ops


@st.cache_data(ttl=10)
def _fetch(_engine: object) -> list[dict]:
    return dashboard_query_service.get_learning_jobs(_engine)  # type: ignore[arg-type]


def render(engine: Engine | None) -> None:
    st.subheader("Learning Jobs")

    if engine is not None and st.button("Enqueue Training Job"):
        job_id = _ops.enqueue(engine)
        _ops.execute_stub(engine, job_id)
        st.success(f"Job {job_id[:8]}… enqueued and completed (stub).")

    rows = _fetch(engine)
    if not rows:
        st.info("No training jobs recorded yet.")
        return

    display = [
        {
            "Job ID": r.get("system_job_id", "")[:8],
            "Type": r.get("job_type", ""),
            "Status": r.get("status", ""),
            "Created (UTC)": str(r.get("created_at", "")),
            "Started": str(r.get("started_at") or "—"),
            "Ended": str(r.get("ended_at") or "—"),
        }
        for r in rows
    ]
    st.dataframe(display, use_container_width=True)
