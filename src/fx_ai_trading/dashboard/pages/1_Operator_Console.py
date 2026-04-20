"""Operator Console — Streamlit page for ctl 4-command wrapper (M26 Phase 1).

Wraps ``start`` / ``stop`` / ``resume-from-safe-stop`` / ``run-reconciler``.
``emergency-flat-all`` is intentionally absent — CLI-only per operations.md
§15.1 / phase6_hardening.md §6.18 (4-defense gate).
"""

from __future__ import annotations

import time

import streamlit as st

from fx_ai_trading.dashboard.operator import ctl_invoker, preflight

st.set_page_config(page_title="Operator Console", page_icon="🛠", layout="wide")
st.title("Operator Console")
st.caption("ctl 4-command wrapper · M26 Phase 1 · Demo Mode")

_DEBOUNCE_SECONDS = 1.5


def _store_result(result: ctl_invoker.CtlResult, label: str) -> None:
    st.session_state["operator.last_result"] = {
        "label": label,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timed_out": result.timed_out,
    }


def _safe_invoke(label: str, command: ctl_invoker.CtlCommand, **kwargs) -> None:
    now = time.monotonic()
    last_at = st.session_state.get(f"operator.invoked_at.{label}", 0.0)
    if now - last_at < _DEBOUNCE_SECONDS:
        st.warning(f"Ignored rapid re-click on `{label}` ({_DEBOUNCE_SECONDS}s debounce).")
        return
    st.session_state[f"operator.invoked_at.{label}"] = now
    with st.spinner(f"Invoking ctl {label}..."):
        result = ctl_invoker.invoke(command, **kwargs)
    _store_result(result, label)


pid = preflight.read_pid()
reason_value = st.session_state.get("operator.resume_reason", "")
buttons = preflight.compute_button_state(pid, reason=reason_value)

if pid is None:
    st.info("Supervisor: **STOPPED** (no PID file)")
else:
    st.success(f"Supervisor: **RUNNING** (PID={pid})")

st.divider()

col_start, col_stop, col_recon = st.columns(3)

with col_start:
    st.subheader("start")
    st.code("python scripts/ctl.py start", language="bash")
    if st.button("Run start", disabled=not buttons.can_start, key="btn_start"):
        _safe_invoke("start", "start")

with col_stop:
    st.subheader("stop")
    st.code("python scripts/ctl.py stop", language="bash")
    if st.button("Run stop", disabled=not buttons.can_stop, key="btn_stop"):
        _safe_invoke("stop", "stop")

with col_recon:
    st.subheader("run-reconciler")
    st.code("python scripts/ctl.py run-reconciler", language="bash")
    if st.button(
        "Run reconciler",
        disabled=not buttons.can_run_reconciler,
        key="btn_recon",
    ):
        _safe_invoke("run-reconciler", "run-reconciler")

st.divider()

st.subheader("resume-from-safe-stop")
st.code('python scripts/ctl.py resume-from-safe-stop --reason="..."', language="bash")
reason_input = st.text_input(
    "Reason (required, non-empty)",
    key="operator.resume_reason",
)
buttons = preflight.compute_button_state(pid, reason=reason_input)
if st.button(
    "Run resume-from-safe-stop",
    disabled=not buttons.can_resume,
    key="btn_resume",
):
    _safe_invoke("resume-from-safe-stop", "resume-from-safe-stop", reason=reason_input)

st.divider()

last = st.session_state.get("operator.last_result")
if last is not None:
    st.subheader("Last invocation")
    if last["timed_out"]:
        st.error(
            f"`{last['label']}` timed out (default {ctl_invoker.DEFAULT_TIMEOUT_SECONDS}s)."
        )
    elif last["returncode"] == 0:
        st.success(f"`{last['label']}` exited 0.")
    else:
        st.error(f"`{last['label']}` exited {last['returncode']}.")
    if last["stdout"]:
        st.text_area("stdout (tail)", value=last["stdout"][-2000:], height=140)
    if last["stderr"]:
        st.text_area("stderr (tail)", value=last["stderr"][-2000:], height=140)

st.divider()

st.warning(
    "**emergency-flat-all is CLI-only.** "
    "Run from a terminal: `python scripts/ctl.py emergency-flat-all` "
    "(2-factor confirmation required). UI exposure is forbidden by the "
    "4-defense gate (operations.md §15.1, phase6_hardening.md §6.18)."
)
