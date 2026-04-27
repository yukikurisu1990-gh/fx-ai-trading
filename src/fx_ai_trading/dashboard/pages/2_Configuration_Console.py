"""Configuration Console — Runtime + Bootstrap + Model Info + Risk Settings (M26 + Phase 9.5)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st
from sqlalchemy import create_engine

from fx_ai_trading.dashboard.config_console import bootstrap_view, runtime_view
from fx_ai_trading.services import dashboard_query_service

st.set_page_config(page_title="設定コンソール", page_icon="⚙", layout="wide")
st.title("設定コンソール")
st.caption("app_settings · .env · モデル情報 · リスク設定")

_MANIFEST_PATH = Path(__file__).resolve().parents[4] / "models" / "lgbm" / "manifest.json"
_MODELS_DIR = _MANIFEST_PATH.parent


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
    st.warning("DATABASE_URL 未設定または接続失敗 — ランタイムタブにデータが表示されません。")

tab_runtime, tab_bootstrap, tab_model, tab_risk = st.tabs(
    ["ランタイム", "ブートストラップ (.env)", "モデル情報", "リスク設定"]
)

with tab_runtime:
    runtime_view.render(engine)

with tab_bootstrap:
    bootstrap_view.render(engine)

with tab_model:
    st.subheader("LGBMモデルマニフェスト")
    if not _MANIFEST_PATH.exists():
        st.warning(
            "manifest.json が見つかりません。"
            "`python scripts/retrain_production_models.py` を先に実行してください。"
        )
    else:
        mtime = datetime.fromtimestamp(_MANIFEST_PATH.stat().st_mtime, tz=UTC)
        age_h = (datetime.now(UTC) - mtime).total_seconds() / 3600  # noqa: CLOCK

        c1, c2, c3 = st.columns(3)
        c1.metric("最終学習日時", mtime.strftime("%Y-%m-%d %H:%M UTC"))
        c2.metric("モデル経過時間", f"{age_h:.0f} h")

        try:
            manifest = json.loads(_MANIFEST_PATH.read_text())
        except Exception as exc:
            st.error(f"manifest.json の解析に失敗しました: {exc}")
            manifest = {}

        trained_pairs = manifest.get("trained_pairs", [])
        c3.metric("学習済みペア数", len(trained_pairs))

        if manifest:
            col_meta, col_pairs = st.columns([1, 2])
            with col_meta:
                st.subheader("ハイパーパラメータ")
                meta_keys = ["horizon", "n_estimators", "tp_mult", "sl_mult"]
                for k in meta_keys:
                    if k in manifest:
                        st.text(f"{k}: {manifest[k]}")
                if "feature_cols" in manifest:
                    st.text(f"特徴量数: {len(manifest['feature_cols'])}")

            with col_pairs:
                st.subheader("学習済みペア")
                cols = st.columns(4)
                for i, pair in enumerate(sorted(trained_pairs)):
                    model_file = _MODELS_DIR / f"{pair}.joblib"
                    exists = model_file.exists()
                    cols[i % 4].markdown(f"{'✅' if exists else '❌'} {pair}")

        st.subheader("モデルファイル")
        if _MODELS_DIR.exists():
            import pandas as pd

            files = sorted(_MODELS_DIR.glob("*.joblib"))
            if files:
                file_data = [
                    {
                        "ペア": f.stem,
                        "サイズ（KB）": f"{f.stat().st_size / 1024:.1f}",
                        "更新日時": datetime.fromtimestamp(f.stat().st_mtime, tz=UTC).strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                    }
                    for f in files
                ]
                st.dataframe(pd.DataFrame(file_data), use_container_width=True, hide_index=True)
            else:
                st.info(".joblib ファイルなし。")

    st.divider()
    st.subheader("学習ジョブ（DB）")
    jobs = dashboard_query_service.get_learning_jobs(engine, limit=10)
    if not jobs:
        st.info("system_jobs テーブルに学習ジョブなし。")
    else:
        import pandas as pd

        df = pd.DataFrame(jobs)
        df = df[["job_type", "status", "created_at", "started_at", "ended_at"]]
        df.columns = ["種別", "ステータス", "作成", "開始", "終了"]
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_risk:
    st.subheader("リスク設定")
    st.caption("app_settings のライブ値。変更はランタイムタブからキュー登録→再起動で反映。")

    _RISK_KEYS = [
        ("risk.max_concurrent_positions", "Max Concurrent Positions", "int"),
        ("risk.max_single_currency_pct", "Max Single Currency % Exposure", "float"),
        ("risk.max_net_direction_pct", "Max Net Direction % Exposure", "float"),
        ("risk.risk_pct_per_position", "Risk % per Position", "float"),
        ("risk.max_spread_pip", "Max Spread (pip) for entry", "float"),
        ("meta.min_ev_threshold", "Min EV Threshold", "float"),
        ("meta.min_confidence", "Min Model Confidence", "float"),
    ]

    risk_data = []
    for key, label, dtype in _RISK_KEYS:
        val = dashboard_query_service.get_app_setting(engine, key)
        risk_data.append({"設定項目": label, "キー": key, "値": val or "（未設定）", "型": dtype})

    if risk_data:
        import pandas as pd

        st.dataframe(pd.DataFrame(risk_data), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("全 app_settings")
    if engine is not None:
        try:
            from sqlalchemy import text

            with engine.connect() as conn:
                rows = (
                    conn.execute(
                        text(
                            "SELECT name, value, type, description FROM app_settings ORDER BY name"
                        )
                    )
                    .mappings()
                    .all()
                )
            if rows:
                import pandas as pd

                df = pd.DataFrame([dict(r) for r in rows])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("app_settings テーブルは空です。")
        except Exception as e:
            st.warning(f"app_settings の取得に失敗しました: {e}")
    else:
        st.info("データベース未接続。")
