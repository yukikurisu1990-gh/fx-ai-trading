"""Runtime mode tab — read app_settings, enqueue changes (M26 Phase 2).

Pure helpers (`is_editable`, `is_secret_like`) are framework-free and
unit-testable. ``render`` is the Streamlit entry point.

Per operations.md §11 L145: ``expected_account_type`` is read-only via UI.
Per operations.md §15.2: changes go to ``app_settings_changes`` queue ONLY;
``app_settings`` is never UPDATEd from this view (applied on next restart /
hot-reload).
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine, text

from fx_ai_trading.services.dashboard_query_service import (
    enqueue_app_settings_change,
)

READONLY_KEYS: frozenset[str] = frozenset({"expected_account_type"})

SECRET_KEY_PATTERNS: tuple[str, ...] = (
    "API_KEY",
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "PRIVATE",
    "CREDENTIAL",
)

QUEUE_SUCCESS_MESSAGE = "キューに登録しました。次の再起動 / hot-reload で反映されます。"
SUBMIT_BUTTON_LABEL = "キューに登録 (再起動で反映)"


def is_secret_like(name: str) -> bool:
    """Defensive: True if name matches a known secret pattern.

    app_settings should never contain secrets (those go to .env), but a
    positive filter prevents accidental exposure if seed drift happens.
    """
    upper = name.upper()
    return any(pat in upper for pat in SECRET_KEY_PATTERNS)


def is_editable(name: str) -> bool:
    """True iff name is editable via Runtime tab (not read-only, not secret-like)."""
    if name in READONLY_KEYS:
        return False
    return not is_secret_like(name)


def _load_settings(engine: Engine | None) -> list[dict]:
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT name, value, type, description, updated_at"
                        " FROM app_settings"
                        " ORDER BY name ASC"
                    )
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


def render(engine: Engine | None) -> None:
    st.subheader("Runtime mode")
    st.caption(
        "app_settings layer — 閲覧可。変更はキュー経由 "
        "(`app_settings_changes`) で受け付け、次の再起動 / hot-reload で反映。"
    )

    rows = _load_settings(engine)
    if not rows:
        st.warning("No app_settings rows available (DB unreachable or table empty).")
        return

    st.markdown("**Current values**")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Change request (queue)**")

    editable = [r for r in rows if is_editable(r["name"])]
    if not editable:
        st.info("No editable keys.")
        return

    name_options = [r["name"] for r in editable]
    selected_name = st.selectbox(
        "Key",
        name_options,
        key="config.runtime.selected_name",
    )
    selected_row = next(r for r in editable if r["name"] == selected_name)

    st.write(f"Current value: `{selected_row['value']}` (type: `{selected_row['type']}`)")
    if selected_row.get("description"):
        st.caption(selected_row["description"])

    new_value = st.text_input(
        "New value",
        value="",
        key="config.runtime.new_value",
    )
    reason = st.text_input(
        "Reason (required, non-empty)",
        value="",
        key="config.runtime.reason",
    )

    can_submit = bool(new_value.strip()) and bool(reason.strip())

    if st.button(
        SUBMIT_BUTTON_LABEL,
        disabled=not can_submit,
        key="config.runtime.submit",
    ):
        try:
            count = enqueue_app_settings_change(
                engine,
                name=selected_name,
                old_value=selected_row["value"],
                new_value=new_value.strip(),
                changed_by="operator (UI)",
                reason=reason.strip(),
            )
        except Exception as e:
            st.error(f"Failed to enqueue change: {type(e).__name__}: {e}")
            return
        st.success(f"{QUEUE_SUCCESS_MESSAGE} (rows={count})")

    if selected_name in READONLY_KEYS:
        # Defensive: this branch is unreachable (filtered in `editable`),
        # but keep an explanatory note next to the form for operators
        # browsing the dropdown.
        st.info(f"`{selected_name}` is read-only via UI (operations.md §11 L145 / §15.1).")
