"""Panel: Meta Decision — last meta-strategy selection result (M12).

MetaDecision is not persisted to a DB table in Iteration 1.
This panel shows a static note and will display live data in Iteration 2
once the meta_decisions table is populated.
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine


def render(engine: Engine | None) -> None:  # noqa: ARG001
    st.subheader("メタ判定")
    st.info(
        "ライブ運用中にメタ判定データが蓄積されます。\n\n"
        "meta_decisions テーブルへの永続化後、ここに表示されます。"
    )
    st.caption("M12: 静的プレースホルダー")
