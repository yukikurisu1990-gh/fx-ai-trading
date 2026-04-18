"""Panel: Meta Decision — last meta-strategy selection result (M12).

MetaDecision is not persisted to a DB table in Iteration 1.
This panel shows a static note and will display live data in Iteration 2
once the meta_decisions table is populated.
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy import Engine


def render(engine: Engine | None) -> None:  # noqa: ARG001
    st.subheader("Meta Decision")
    st.info(
        "Meta-decision data is populated during live operation.\n\n"
        "Iteration 2 will persist MetaDecision rows to the meta_decisions table "
        "and display them here."
    )
    st.caption("M12: static placeholder — no persistent MetaDecision table yet")
