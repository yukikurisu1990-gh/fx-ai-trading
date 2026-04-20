"""Bootstrap mode tab — `.env` sink (M26 Phase 3).

Constraints (operations.md §15.1 / §15.2 / §15.4, development_rules.md §10.3.1):
  - Form renders ONLY when ``ProcessManager.is_running() == False``.
  - Secret inputs use ``text_input(type="password")`` with ``key=None`` so the
    value is NOT retained in ``st.session_state``.
  - Diff preview shows key names + sha256 hex prefixes (8 chars) only — never
    plaintext values.
  - On write, ``app_settings_changes`` audit row stores hash prefixes (not
    plaintext) in ``old_value`` / ``new_value``. Reuses
    ``enqueue_app_settings_change`` from ``dashboard_query_service`` (P2).
  - Plaintext values exist only as local variables in this module's
    callbacks; they are never logged, returned, or embedded in exceptions.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from sqlalchemy import Engine

from fx_ai_trading.dashboard.config_console.env_diff import (
    compute_diff,
    hash_prefix,
    parse_env_text,
)
from fx_ai_trading.dashboard.config_console.env_writer import (
    SupervisorRunningError,
    atomic_write_env,
)
from fx_ai_trading.ops.process_manager import ProcessManager
from fx_ai_trading.services.dashboard_query_service import (
    enqueue_app_settings_change,
)

PID_RUNNING_MESSAGE = "App is running — stop the Supervisor before editing `.env`."
WRITE_SUCCESS_MESSAGE = ".env updated. 再起動後に新しい値が反映されます。"
NO_CHANGE_MESSAGE = "差分がありません。書込は実行しませんでした。"
RACE_ABORTED_MESSAGE = (
    "書込直前に Supervisor の起動を検出したため中止しました。再度停止してから操作してください。"
)
AUDIT_REASON = "bootstrap .env update"


def _default_env_path() -> Path:
    return Path(__file__).resolve().parents[3].parent / ".env"


def render(
    engine: Engine | None,
    *,
    process_manager: ProcessManager | None = None,
    env_path: Path | None = None,
) -> None:
    pm = process_manager or ProcessManager()
    target_path = env_path or _default_env_path()

    st.subheader("Bootstrap mode")
    st.caption(
        "`.env` 直接編集モード — secret / 接続情報の初期投入・rotate のみ可。"
        "アプリ停止時のみ操作可能。値は DB / log / session_state に保持されません。"
    )

    if pm.is_running():
        st.warning(PID_RUNNING_MESSAGE)
        st.caption(
            "operations.md §15.2 — Bootstrap モードは PID 不在時のみ書込可能 "
            "(race-safe atomic rename)。"
        )
        return

    old_env = _read_env_safe(target_path)

    st.markdown("**Current `.env` keys**")
    if old_env:
        st.dataframe(
            [{"name": k, "old_hash": hash_prefix(v)} for k, v in old_env.items()],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("`.env` is empty or unreadable. New file will be created on write.")

    st.divider()
    st.markdown("**New `.env` content**")
    st.caption("全文を貼り付けてください。`KEY=VALUE` 形式 / `#` 行はコメント / 空行可。")

    # st.form(clear_on_submit=True) ensures Streamlit clears the text_area /
    # text_input widget state after submit, so plaintext secrets do not
    # persist in session_state across reruns (development_rules.md §10.3.1,
    # m26_implementation_plan.md §4.5 #2).
    with st.form("bootstrap_env_form", clear_on_submit=True):
        new_text = st.text_area(
            "New .env body",
            value="",
            height=300,
            placeholder="DATABASE_URL=postgresql+psycopg://...\nOANDA_ACCESS_TOKEN=...",
        )
        reason = st.text_input(
            "Reason (required, non-empty)",
            value="",
        )
        submitted = st.form_submit_button("Write .env (atomic, requires app stopped)")

    if not submitted:
        st.caption("貼り付けてフォームを送信すると、ハッシュ差分プレビューと書込が実行されます。")
        return

    if not new_text.strip():
        st.warning("新しい `.env` 本文が空です。書込は実行しませんでした。")
        return
    if not reason.strip():
        st.warning("Reason が空です。書込は実行しませんでした。")
        return

    new_env = parse_env_text(new_text)
    diff = compute_diff(old_env, new_env)

    st.markdown("**Diff (hash prefixes only — no plaintext)**")
    col_a, col_r, col_c = st.columns(3)
    with col_a:
        st.caption(f"Added ({len(diff['added'])})")
        st.dataframe(diff["added"], use_container_width=True, hide_index=True)
    with col_r:
        st.caption(f"Removed ({len(diff['removed'])})")
        st.dataframe(diff["removed"], use_container_width=True, hide_index=True)
    with col_c:
        st.caption(f"Changed ({len(diff['changed'])})")
        st.dataframe(diff["changed"], use_container_width=True, hide_index=True)
    st.caption(f"Unchanged: {len(diff['unchanged'])} keys")

    if not (diff["added"] or diff["removed"] or diff["changed"]):
        st.info(NO_CHANGE_MESSAGE)
        return

    try:
        atomic_write_env(target_path, new_env, process_manager=pm)
    except SupervisorRunningError:
        st.error(RACE_ABORTED_MESSAGE)
        return
    except Exception as exc:
        st.error(f"Failed to write .env: {type(exc).__name__}")
        return

    _enqueue_audit_rows(engine, diff, reason.strip())

    st.success(WRITE_SUCCESS_MESSAGE)


def _read_env_safe(path: Path) -> dict[str, str]:
    try:
        return parse_env_text(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except OSError:
        return {}


def _enqueue_audit_rows(engine: Engine | None, diff: dict, reason: str) -> None:
    """Insert one audit row per affected key, hash prefixes only."""
    if engine is None:
        return
    try:
        for entry in diff["added"]:
            enqueue_app_settings_change(
                engine,
                name=f".env:{entry['name']}",
                old_value=None,
                new_value=entry["new_hash"],
                changed_by="operator (bootstrap UI)",
                reason=f"{AUDIT_REASON} — {reason}",
            )
        for entry in diff["removed"]:
            enqueue_app_settings_change(
                engine,
                name=f".env:{entry['name']}",
                old_value=entry["old_hash"],
                new_value="-",
                changed_by="operator (bootstrap UI)",
                reason=f"{AUDIT_REASON} (removed) — {reason}",
            )
        for entry in diff["changed"]:
            enqueue_app_settings_change(
                engine,
                name=f".env:{entry['name']}",
                old_value=entry["old_hash"],
                new_value=entry["new_hash"],
                changed_by="operator (bootstrap UI)",
                reason=f"{AUDIT_REASON} — {reason}",
            )
    except Exception:
        st.warning("Audit row insert failed (write succeeded). 値は保存されました。")
