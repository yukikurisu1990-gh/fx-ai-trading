"""F-2 PnL-layer invariant tests (audit memo §3 F-2).

The legacy compare_multipair_v* eval layer mapped the tri-directional
label identity to PnL (label==0 -> 0.0 pips), which booked real
traded-direction SL hits as 0 and timeout exits at 0 with no
mark-to-market. The correction computes per-direction outcome columns
(PNL_LONG_COLUMN / PNL_SHORT_COLUMN, price units) alongside the label
from the same barrier indices, and the eval layer scores the traded
direction's own column.

These tests use tiny synthetic in-memory rows only. They read no real
market data and compute no aggregate strategy metrics. Historical
Phase 9.X numbers are NOT recomputed or rehabilitated by these tests
(F2_REAL_DATA_RERUN_NOT_PERFORMED /
HISTORICAL_PHASE9_NUMERICS_NOT_REHABILITATED).

Every test would have FAILED under the old scoring logic (which had no
per-direction columns at all, and booked the constructed SL/timeout
scenarios as 0.0).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from traded_direction_pnl import traded_direction_pnl_price  # noqa: E402

# Evidence-relevant legacy evaluators patched with the F-2 correction.
PATCHED_SCRIPTS = [
    "compare_multipair_v5_bidask",
    "compare_multipair_v9_orthogonal",
    "compare_multipair_v19_causal",
    "compare_multipair_v23_realism",
    "compare_multipair_v26_dynamic_sltp",
]

# Archived/superseded legacy scripts that retain the OLD scoring pattern
# on purpose (historical record of what produced committed reports; not
# evidence-relevant going forward). Any compare script NOT listed here
# and NOT patched must not contain the old pattern.
ARCHIVED_UNPATCHED_SCRIPTS = {
    "compare_multipair_v3_costs",
    "compare_multipair_v4_atr",
    "compare_multipair_v6_meta",
    "compare_multipair_v7_kelly",
    "compare_multipair_v8_risk",
    "compare_multipair_v10_recent_hr",
    "compare_multipair_v11_csi",
    "compare_multipair_v12_asymmetric",
    "compare_multipair_v13_ensemble",
    "compare_multipair_v14_topk",
    "compare_multipair_v15_regression",
    "compare_multipair_v16_features",
    "compare_multipair_v22_risk_sizing",
    "compare_multipair_v24_calendar",
    "compare_multipair_v25_filter",
}

_OLD_PATTERN = "long_mask & (label == 1)"

_MODULE_CACHE: dict[str, object] = {}


def _load_script(name: str):
    if name not in _MODULE_CACHE:
        spec = importlib.util.spec_from_file_location(f"f2_{name}", SCRIPTS_DIR / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"f2_{name}"] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        _MODULE_CACHE[name] = mod
    return _MODULE_CACHE[name]


# ---------------------------------------------------------------------------
# Pure helper truth table
# ---------------------------------------------------------------------------


class TestTradedDirectionPnlHelper:
    def test_sl_first_is_negative_sl(self) -> None:
        assert traded_direction_pnl_price(
            tp_idx=3, sl_idx=1, tp_dist=0.0015, sl_dist=0.0010, mtm_exit_pnl=0.0002
        ) == pytest.approx(-0.0010)

    def test_sl_only_is_negative_sl(self) -> None:
        assert traded_direction_pnl_price(
            tp_idx=-1, sl_idx=2, tp_dist=0.0015, sl_dist=0.0010, mtm_exit_pnl=0.0002
        ) == pytest.approx(-0.0010)

    def test_tp_first_is_positive_tp_no_extra_spread(self) -> None:
        # Exactly +tp_dist: spread is embedded in the barrier geometry,
        # never charged again here.
        assert traded_direction_pnl_price(
            tp_idx=1, sl_idx=4, tp_dist=0.0015, sl_dist=0.0010, mtm_exit_pnl=0.0002
        ) == pytest.approx(0.0015)

    def test_same_bar_tie_is_sl_first_conservative(self) -> None:
        assert traded_direction_pnl_price(
            tp_idx=2, sl_idx=2, tp_dist=0.0015, sl_dist=0.0010, mtm_exit_pnl=0.0002
        ) == pytest.approx(-0.0010)

    def test_timeout_is_mark_to_market_not_zero(self) -> None:
        assert traded_direction_pnl_price(
            tp_idx=-1, sl_idx=-1, tp_dist=0.0015, sl_dist=0.0010, mtm_exit_pnl=-0.0007
        ) == pytest.approx(-0.0007)


# ---------------------------------------------------------------------------
# Synthetic label-function invariants, parametrized over patched scripts
# ---------------------------------------------------------------------------

_HORIZON = 5
_TP_MULT = 1.5
_SL_MULT = 1.0
_ATR0 = 0.0010  # tp = 0.0015, sl = 0.0010 (price units)
_SPREAD = 0.0002


def _ba_df(bid_rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """Build a minimal BA-mode frame; only row 0 has ATR => only i=0 labeled."""
    bids = np.array(bid_rows, dtype=np.float64)
    asks = bids + _SPREAD
    n = len(bids)
    atr = np.full(n, np.nan)
    atr[0] = _ATR0
    return pd.DataFrame(
        {
            "bid_o": bids[:, 0],
            "bid_h": bids[:, 1],
            "bid_l": bids[:, 2],
            "bid_c": bids[:, 3],
            "ask_o": asks[:, 0],
            "ask_h": asks[:, 1],
            "ask_l": asks[:, 2],
            "ask_c": asks[:, 3],
            "atr_14": atr,
        }
    )


# entry_long = ask_o[1] = 1.10020; entry_short = bid_o[1] = 1.10000
# long TP >= 1.10170 (bid_h); long SL <= 1.09920 (bid_l)
# short TP <= 1.09850 (ask_l => bid_l <= 1.09830); short SL >= 1.10100 (ask_h => bid_h >= 1.10080)
_FLAT = (1.10000, 1.10005, 1.09995, 1.10000)


def _rows(*window: tuple[float, float, float, float]) -> list[tuple[float, float, float, float]]:
    """Row 0 (decision bar) + 5 window bars + 1 tail bar."""
    assert len(window) == _HORIZON
    return [_FLAT, *window, _FLAT]


def _label_pnl(mod, rows):
    df = mod._add_labels_bidask(_ba_df(rows), _HORIZON, _TP_MULT, _SL_MULT)
    return (
        df[mod.LABEL_COLUMN].iloc[0],
        df[mod.PNL_LONG_COLUMN].iloc[0],
        df[mod.PNL_SHORT_COLUMN].iloc[0],
    )


@pytest.mark.parametrize("script", PATCHED_SCRIPTS)
class TestPatchedScriptInvariants:
    def test_long_label0_sl_hit_scores_negative(self, script: str) -> None:
        # Dip below long SL but NOT deep enough for short TP: label stays 0
        # under the tri-directional contract, but the traded LONG lost -sl.
        mod = _load_script(script)
        rows = _rows(
            _FLAT,
            (1.10000, 1.10005, 1.09915, 1.09950),  # bid_l 1.09915 <= 1.09920 -> long SL
            (1.09950, 1.09955, 1.09945, 1.09950),
            (1.09950, 1.09955, 1.09945, 1.09950),
            (1.09950, 1.09955, 1.09945, 1.09950),
        )
        label, pnl_long, pnl_short = _label_pnl(mod, rows)
        assert label == 0
        assert pnl_long == pytest.approx(-_SL_MULT * _ATR0)  # NOT 0.0
        # Short never hit a barrier -> mark-to-market at horizon end.
        assert pnl_short == pytest.approx(1.10000 - (1.09950 + _SPREAD))

    def test_short_label0_sl_hit_scores_negative(self, script: str) -> None:
        # Rise above short SL but NOT high enough for long TP: label 0,
        # but the traded SHORT lost -sl.
        mod = _load_script(script)
        rows = _rows(
            _FLAT,
            (1.10000, 1.10085, 1.09995, 1.10050),  # ask_h 1.10105 >= 1.10100 -> short SL
            (1.10050, 1.10055, 1.10045, 1.10050),
            (1.10050, 1.10055, 1.10045, 1.10050),
            (1.10050, 1.10055, 1.10045, 1.10050),
        )
        label, pnl_long, pnl_short = _label_pnl(mod, rows)
        assert label == 0
        assert pnl_short == pytest.approx(-_SL_MULT * _ATR0)  # NOT 0.0
        # Long never hit a barrier -> mark-to-market at horizon end.
        assert pnl_long == pytest.approx(1.10050 - 1.10020)

    def test_timeout_is_mark_to_market_both_directions(self, script: str) -> None:
        # No barrier ever hit: both directions exit at horizon-end
        # mark-to-market crossing the spread once — NOT 0.0 by default.
        mod = _load_script(script)
        rows = _rows(
            _FLAT,
            (1.10000, 1.10010, 1.09990, 1.10005),
            (1.10005, 1.10015, 1.09995, 1.10010),
            (1.10010, 1.10020, 1.10000, 1.10020),
            (1.10020, 1.10055, 1.10015, 1.10050),
        )
        label, pnl_long, pnl_short = _label_pnl(mod, rows)
        assert label == 0
        # Long: exit bid_c=1.10050 vs entry ask 1.10020 -> +0.0003
        assert pnl_long == pytest.approx(1.10050 - 1.10020)
        assert pnl_long != 0.0
        # Short: entry bid 1.10000 vs exit ask_c=1.10052 -> -0.00052
        assert pnl_short == pytest.approx(1.10000 - (1.10050 + _SPREAD))
        assert pnl_short != 0.0

    def test_tp_and_sl_rows_carry_exact_barrier_pnl_no_double_spread(self, script: str) -> None:
        # Strong rise: long TP fires (label +1), short SL fires. Barrier
        # PnL must be EXACTLY +tp / -sl — spread is embedded in the
        # barrier geometry and must not be charged again.
        mod = _load_script(script)
        rows = _rows(
            _FLAT,
            # bid_h 1.10180 >= 1.10170 -> long TP; ask_h 1.10200 >= 1.10100 -> short SL
            (1.10000, 1.10180, 1.09995, 1.10150),
            (1.10150, 1.10160, 1.10140, 1.10150),
            (1.10150, 1.10160, 1.10140, 1.10150),
            (1.10150, 1.10160, 1.10140, 1.10150),
        )
        label, pnl_long, pnl_short = _label_pnl(mod, rows)
        assert label == 1
        assert pnl_long == pytest.approx(_TP_MULT * _ATR0)  # not tp - spread
        assert pnl_short == pytest.approx(-_SL_MULT * _ATR0)  # not -sl - spread

    def test_same_bar_tp_sl_tie_is_sl_first_conservative(self, script: str) -> None:
        # One bar touches BOTH long barriers: unknowable path -> SL-first.
        # Label semantics unchanged: long does not "clear", label stays 0.
        mod = _load_script(script)
        rows = _rows(
            _FLAT,
            (1.10000, 1.10180, 1.09910, 1.10000),  # long TP touch AND long SL touch
            _FLAT,
            _FLAT,
            _FLAT,
        )
        label, pnl_long, _pnl_short = _label_pnl(mod, rows)
        assert label == 0
        assert pnl_long == pytest.approx(-_SL_MULT * _ATR0)

    def test_labels_unchanged_by_correction(self, script: str) -> None:
        # The correction adds columns only — the label itself must keep
        # the historical tri-directional semantics (training target
        # compatibility). Clean long TP -> +1; clean short TP -> -1.
        mod = _load_script(script)
        up = _rows(
            (1.10000, 1.10180, 1.09995, 1.10150),
            _FLAT,
            _FLAT,
            _FLAT,
            _FLAT,
        )
        down = _rows(
            (1.10000, 1.10005, 1.09820, 1.09850),  # ask_l 1.09840 <= 1.09850 -> short TP
            _FLAT,
            _FLAT,
            _FLAT,
            _FLAT,
        )
        label_up, _, _ = _label_pnl(mod, up)
        label_down, _, _ = _label_pnl(mod, down)
        assert label_up == 1
        assert label_down == -1


# ---------------------------------------------------------------------------
# Static guard: the old pattern must not reappear in active evaluators
# ---------------------------------------------------------------------------


class TestOldPatternGuard:
    def test_patched_scripts_use_helper_and_drop_old_pattern(self) -> None:
        for name in PATCHED_SCRIPTS:
            src = (SCRIPTS_DIR / f"{name}.py").read_text(encoding="utf-8")
            assert "traded_direction_pnl" in src, f"{name}: F-2 helper not wired"
            assert _OLD_PATTERN not in src, f"{name}: old label-identity PnL mapping present"

    def test_no_new_script_reintroduces_old_pattern(self) -> None:
        known = set(PATCHED_SCRIPTS) | ARCHIVED_UNPATCHED_SCRIPTS
        for path in sorted(SCRIPTS_DIR.glob("compare_multipair_*.py")):
            name = path.stem
            if name in known:
                continue
            src = path.read_text(encoding="utf-8")
            assert _OLD_PATTERN not in src, (
                f"{name}: contains the F-2 label-identity PnL pattern; wire "
                "traded_direction_pnl_price instead (audit memo §3 F-2) or, if "
                "this is a frozen historical record, add it to "
                "ARCHIVED_UNPATCHED_SCRIPTS with justification."
            )
