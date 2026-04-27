"""Operator Console — ctl commands, model retrain, system health (M26 + Phase 9.5)."""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st
from sqlalchemy import create_engine

from fx_ai_trading.dashboard.operator import ctl_invoker, preflight, retrain_invoker
from fx_ai_trading.services import dashboard_query_service

st.set_page_config(page_title="オペレーターコンソール", page_icon="🛠", layout="wide")
st.title("オペレーターコンソール")
st.caption("CTLコマンド · モデル再学習 · システム状態")

_DEBOUNCE_SECONDS = 1.5
_MANIFEST_PATH = Path(__file__).resolve().parents[4] / "models" / "lgbm" / "manifest.json"


@st.cache_resource
def _get_engine():
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        return None
    return create_engine(db_url)


engine = _get_engine()

# ── Section 1: System Health ────────────────────────────────────────────────
st.subheader("システム状態")
h_col1, h_col2, h_col3, h_col4 = st.columns(4)

pid = preflight.read_pid()
with h_col1:
    if pid is None:
        st.metric("スーパーバイザー", "停止中")
    else:
        st.metric("スーパーバイザー", f"稼働中（PID {pid}）")

with h_col2:
    if engine is not None:
        st.metric("データベース", "接続済み")
    else:
        st.metric("データベース", "未設定")

with h_col3:
    try:
        open_positions = dashboard_query_service.get_open_positions(engine)
        st.metric("オープンポジション", len(open_positions))
    except Exception:
        st.metric("オープンポジション", "N/A")

with h_col4:
    if _MANIFEST_PATH.exists():
        mtime = datetime.fromtimestamp(_MANIFEST_PATH.stat().st_mtime, tz=UTC)
        age_hours = (datetime.now(UTC) - mtime).total_seconds() / 3600  # noqa: CLOCK
        st.metric("モデル経過時間", f"{age_hours:.0f}h")
    else:
        st.metric("モデル経過時間", "マニフェストなし")

st.divider()

# ── Section 2: Recent Open Positions ────────────────────────────────────────
with st.expander("オープンポジション", expanded=False):
    positions_data = dashboard_query_service.get_open_positions(engine)
    if not positions_data:
        st.info("オープンポジションなし。")
    else:
        import pandas as pd

        df = pd.DataFrame(positions_data)[
            ["instrument", "event_type", "units", "avg_price", "unrealized_pl", "event_time_utc"]
        ]
        df.columns = ["通貨ペア", "種別", "数量", "平均価格", "含み損益", "時刻（UTC）"]
        st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ── Section 3: ctl Commands ──────────────────────────────────────────────────
st.subheader("スーパーバイザー制御")
reason_value = st.session_state.get("operator.resume_reason", "")
buttons = preflight.compute_button_state(pid, reason=reason_value)

col_start, col_stop, col_recon = st.columns(3)

with col_start:
    st.subheader("start")
    st.code("python scripts/ctl.py start", language="bash")
    if st.button("start 実行", disabled=not buttons.can_start, key="btn_start"):
        _now = time.monotonic()
        _last = st.session_state.get("operator.invoked_at.start", 0.0)
        if _now - _last < _DEBOUNCE_SECONDS:
            st.warning("連続クリックを無視しました。")
        else:
            st.session_state["operator.invoked_at.start"] = _now
            with st.spinner("ctl start 実行中..."):
                result = ctl_invoker.invoke("start")
            st.session_state["operator.last_result"] = {
                "label": "start",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            }

with col_stop:
    st.subheader("stop")
    st.code("python scripts/ctl.py stop", language="bash")
    if st.button("stop 実行", disabled=not buttons.can_stop, key="btn_stop"):
        _now = time.monotonic()
        _last = st.session_state.get("operator.invoked_at.stop", 0.0)
        if _now - _last < _DEBOUNCE_SECONDS:
            st.warning("連続クリックを無視しました。")
        else:
            st.session_state["operator.invoked_at.stop"] = _now
            with st.spinner("ctl stop 実行中..."):
                result = ctl_invoker.invoke("stop")
            st.session_state["operator.last_result"] = {
                "label": "stop",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            }

with col_recon:
    st.subheader("run-reconciler")
    st.code("python scripts/ctl.py run-reconciler", language="bash")
    if st.button("照合 実行", disabled=not buttons.can_run_reconciler, key="btn_recon"):
        _now = time.monotonic()
        _last = st.session_state.get("operator.invoked_at.recon", 0.0)
        if _now - _last < _DEBOUNCE_SECONDS:
            st.warning("連続クリックを無視しました。")
        else:
            st.session_state["operator.invoked_at.recon"] = _now
            with st.spinner("照合 実行中..."):
                result = ctl_invoker.invoke("run-reconciler")
            st.session_state["operator.last_result"] = {
                "label": "run-reconciler",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            }

st.divider()
st.subheader("セーフストップから再開")
st.code('python scripts/ctl.py resume-from-safe-stop --reason="..."', language="bash")
reason_input = st.text_input("理由（必須、空不可）", key="operator.resume_reason")
buttons = preflight.compute_button_state(pid, reason=reason_input)
if st.button("セーフストップから再開 実行", disabled=not buttons.can_resume, key="btn_resume"):
    _now = time.monotonic()
    _last = st.session_state.get("operator.invoked_at.resume", 0.0)
    if _now - _last < _DEBOUNCE_SECONDS:
        st.warning("連続クリックを無視しました。")
    else:
        st.session_state["operator.invoked_at.resume"] = _now
        with st.spinner("セーフストップから再開 実行中..."):
            result = ctl_invoker.invoke("resume-from-safe-stop", reason=reason_input)
        st.session_state["operator.last_result"] = {
            "label": "resume-from-safe-stop",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }

last = st.session_state.get("operator.last_result")
if last is not None:
    st.subheader("最後のCTL実行結果")
    if last["timed_out"]:
        st.error(f"`{last['label']}` タイムアウト。")
    elif last["returncode"] == 0:
        st.success(f"`{last['label']}` 正常終了（exit 0）。")
    else:
        st.error(f"`{last['label']}` 異常終了（exit {last['returncode']}）。")
    if last["stdout"]:
        st.text_area("標準出力", value=last["stdout"][-2000:], height=120)
    if last["stderr"]:
        st.text_area("標準エラー", value=last["stderr"][-2000:], height=120)

st.divider()

st.warning(
    "**emergency-flat-all はCLI専用です。** "
    "ターミナルから実行: `python scripts/ctl.py emergency-flat-all` "
    "（2段階確認が必要）。UIからの実行は4防衛ゲートにより禁止されています "
    "（operations.md §15.1, phase6_hardening.md §6.18）。"
)
st.divider()

# ── Section 4: Model Retrain ─────────────────────────────────────────────────
st.subheader("モデル再学習")
st.caption("`retrain_production_models.py` をバックグラウンドプロセスとして起動します。")

_retrain_pid: int | None = st.session_state.get("retrain.pid")
_retrain_started_at: float | None = st.session_state.get("retrain.started_at")
_retrain_running = False

if _retrain_pid is not None:
    _retrain_running = retrain_invoker.is_running(_retrain_pid)
    if _retrain_running:
        elapsed = time.monotonic() - (_retrain_started_at or time.monotonic())
        st.info(
            f"再学習実行中 — PID {_retrain_pid} — "
            f"経過 {elapsed / 60:.1f} 分。"
            "通常20〜40分かかります。ページをリロードして状態を確認してください。"
        )
    else:
        started_str = (
            datetime.fromtimestamp(_retrain_started_at, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
            if _retrain_started_at
            else "不明"
        )
        st.success(
            f"最後の再学習プロセス（PID {_retrain_pid}）は完了したようです（開始: {started_str}）。"
        )

if _MANIFEST_PATH.exists():
    mtime = datetime.fromtimestamp(_MANIFEST_PATH.stat().st_mtime, tz=UTC)
    st.caption(f"Current manifest last modified: {mtime.strftime('%Y-%m-%d %H:%M UTC')}")
    try:
        manifest = json.loads(_MANIFEST_PATH.read_text())
        n_pairs = len(manifest.get("trained_pairs", []))
        horizon = manifest.get("horizon")
        n_est = manifest.get("n_estimators")
        st.caption(f"Trained pairs: {n_pairs} · horizon={horizon} · n_estimators={n_est}")
    except Exception:
        pass

r_col1, r_col2, r_col3 = st.columns([1, 1, 2])
with r_col1:
    retrain_days = st.number_input(
        "学習日数",
        min_value=30,
        max_value=730,
        value=365,
        step=30,
        key="retrain.days",
    )
with r_col2:
    retrain_skip_fetch = st.checkbox("フェッチスキップ（キャッシュ使用）", key="retrain.skip_fetch")

with r_col3:
    if st.button(
        "再学習開始",
        disabled=_retrain_running,
        key="btn_retrain",
        type="primary",
    ):
        _now_mono = time.monotonic()
        _last_retrain = st.session_state.get("retrain.invoked_at", 0.0)
        if _now_mono - _last_retrain < 5.0:
            st.warning("連続クリック防止（5秒）。しばらくお待ちください。")
        else:
            st.session_state["retrain.invoked_at"] = _now_mono
            handle = retrain_invoker.launch(
                skip_fetch=retrain_skip_fetch,
                days=int(retrain_days),
            )
            st.session_state["retrain.pid"] = handle.pid
            st.session_state["retrain.started_at"] = _now_mono
            st.success(
                f"再学習開始しました — PID {handle.pid}。"
                "バックグラウンドで実行中です。ページをリロードして状態を確認してください。"
            )
            st.rerun()
