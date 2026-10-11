"""FXID Frontier Expansion の契約（Track B は spread だけ、fresh 不読、HOLD は不変）。"""

from __future__ import annotations

import ast
import hashlib
import inspect
import pathlib

import numpy as np
import pandas as pd

from scripts.research.fx_frontier import track_b_cost as tb

REPO = pathlib.Path(__file__).resolve().parents[2]
HOLD = REPO / "docs/governance/fxid_long_term_hold_ruling_2026_10.md"
GOV = REPO / "docs/governance/fxid_frontier_expansion_reopen_2026_10.md"


def test_hold_ruling_bytes_are_pinned():
    raw = HOLD.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == (
        "e7abc2f56c559d0965c551485dbc9d4e883af8acd66ebfb2e393954d9718e221"
    )


def test_governance_forbids_fresh_and_trading():
    gov = GOV.read_text(encoding="utf-8")
    assert "**`2016-06-02 … 2021-04-25`** を一切読まない" in gov
    assert "live / demo / paper の取引" in gov


def test_track_b_reads_only_through_the_guarded_route_and_computes_no_returns():
    tree = ast.parse(inspect.getsource(tb))
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "guarded.load_pair" in calls
    assert not any(c.endswith(("read_parquet", "read_csv")) for c in calls)
    src = inspect.getsource(tb)
    for forbidden in ("pct_change", ".diff(", "shift(", "log("):
        assert forbidden not in src, forbidden


def test_spreads_and_buckets_on_synthetic_frame():
    ts = pd.date_range("2023-07-10 12:00", periods=8, freq="15min", tz="UTC")
    mid = np.full(len(ts), 1.1)
    frame = pd.DataFrame(
        {
            "ts": ts,
            "bid_c": mid - 0.00005,
            "ask_c": mid + 0.00005,
            "bid_o": mid - 0.0001,
            "ask_o": mid + 0.0001,
        }
    )
    s = tb.spreads(frame)
    assert np.allclose(s["spread_close_bp"], 0.0001 / 1.1 * 1e4)
    # 12:00 UTC は夏時間の 08:00 ET。最初の bar の終わりは 08:15 ET で ny08 に入る
    assert tb._bucket_mask(s, "ny08_0800_0900").iloc[0]
    assert tb.classify_1bp(0.6) == "CONTINUOUS"
    assert tb.classify_1bp(0.0) == "NEVER"
