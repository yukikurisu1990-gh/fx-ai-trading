"""Unit tests: _add_labels_bidask triple-barrier label quality (Phase 9.12 fix).

Covers the first-occurrence SL logic introduced to replace the heuristic
`bid_l[long_tp_idx - 1]` check. Key regression cases:

  R1 — SL hit early, price recovers, TP hits later → label 0 (not 1).
       Old code used bid_l[tp_idx - 1] which misses early SL if price recovers.
  R2 — SL hit early, same direction TP also hit, but SL was first → label 0.
  R3 — Both TPs theoretically reachable; one direction has SL before its TP
       → only the other direction is profitable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import train_lgbm_models as tm  # noqa: E402

# ---------------------------------------------------------------------------
# Test fixture helpers
# ---------------------------------------------------------------------------

# With ATR=0.001, tp_mult=1.5, sl_mult=1.0 (defaults):
#   entry_ask = 1.1010, entry_bid = 1.1000
#   long  TP level : bid_h >= entry_ask + tp = 1.1025
#   long  SL level : bid_l <= entry_ask - sl = 1.1000
#   short TP level : ask_l <= entry_bid - tp = 1.0985
#   short SL level : ask_h >= entry_bid + sl = 1.1010
_ATR = 0.001
_ENTRY_ASK = 1.1010
_ENTRY_BID = 1.1000
_NEUTRAL = 1.1005  # a price that triggers no barrier

_LONG_TP_TRIGGER = 1.1030  # bid_h value that hits long TP (>= 1.1025)
_LONG_SL_TRIGGER = 1.0990  # bid_l value that hits long SL (<= 1.1000)
_SHORT_TP_TRIGGER = 1.0980  # ask_l value that hits short TP (<= 1.0985)
_SHORT_SL_TRIGGER = 1.1015  # ask_h value that hits short SL (>= 1.1010)


def _make_df(
    *bars: dict,
    horizon: int = 3,
) -> pd.DataFrame:
    """Build a minimal DataFrame for _add_labels_bidask.

    Each dict in *bars overrides the neutral baseline for one row.
    Row 0 is always the signal bar (atr_14=_ATR, entry prices set).
    Rows 1..n-1 are look-forward bars.

    The labeling iterates i in range(n - horizon - 1); with horizon=3 and n=5
    only i=0 is evaluated. Callers can control hit timing via bar indices 1-3.
    """
    base_rows = [dict(b) for b in bars]

    def _v(row: dict, key: str, default: float) -> float:
        return row.get(key, default)

    data = {
        "atr_14": [_v(r, "atr_14", _ATR) for r in base_rows],
        "ask_o": [_v(r, "ask_o", _ENTRY_ASK) for r in base_rows],
        "bid_o": [_v(r, "bid_o", _ENTRY_BID) for r in base_rows],
        "bid_h": [_v(r, "bid_h", _NEUTRAL) for r in base_rows],
        "bid_l": [_v(r, "bid_l", _NEUTRAL) for r in base_rows],
        "ask_h": [_v(r, "ask_h", _NEUTRAL) for r in base_rows],
        "ask_l": [_v(r, "ask_l", _NEUTRAL) for r in base_rows],
    }
    return pd.DataFrame(data)


def _label0(df: pd.DataFrame, horizon: int = 3) -> int | None:
    """Return the label at index 0."""
    out = tm._add_labels_bidask(df, "TEST", horizon=horizon)
    return out["label_tb"].iloc[0]


# ---------------------------------------------------------------------------
# Basic cases: single direction hits TP (no SL)
# ---------------------------------------------------------------------------


class TestBasicTPHit:
    def test_long_tp_hit_no_sl_returns_1(self) -> None:
        # bar1=entry, bar2=long TP hit, bars 3-4 neutral
        df = _make_df(
            {},  # bar 0: signal bar
            {},  # bar 1: entry (ask_o=1.1010)
            {"bid_h": _LONG_TP_TRIGGER},  # bar 2: long TP hit
            {},  # bar 3
            {},  # bar 4 (padding)
        )
        assert _label0(df) == 1

    def test_short_tp_hit_no_sl_returns_neg1(self) -> None:
        df = _make_df(
            {},
            {},
            {"ask_l": _SHORT_TP_TRIGGER},
            {},
            {},
        )
        assert _label0(df) == -1

    def test_no_tp_within_horizon_returns_0(self) -> None:
        df = _make_df({}, {}, {}, {}, {})
        assert _label0(df) == 0


# ---------------------------------------------------------------------------
# SL before TP → label 0 (R1 / R2 regression fix)
# ---------------------------------------------------------------------------


class TestSLBeforeTP:
    def test_long_sl_before_tp_returns_0(self) -> None:
        # bar2: SL hit; bar3: TP hit → SL was first → label 0
        df = _make_df(
            {},
            {},
            {"bid_l": _LONG_SL_TRIGGER},  # bar 2: long SL
            {"bid_h": _LONG_TP_TRIGGER},  # bar 3: long TP (too late)
            {},
        )
        assert _label0(df) == 0

    def test_short_sl_before_tp_returns_0(self) -> None:
        df = _make_df(
            {},
            {},
            {"ask_h": _SHORT_SL_TRIGGER},  # bar 2: short SL
            {"ask_l": _SHORT_TP_TRIGGER},  # bar 3: short TP (too late)
            {},
        )
        assert _label0(df) == 0

    def test_long_sl_early_recovery_then_tp_returns_0(self) -> None:
        """R1: SL fires at bar2, price recovers (bar3 neutral), TP fires at bar4.

        Old heuristic checked bid_l[long_tp_idx - 1] = bid_l[bar3] which is
        neutral (above SL level) — incorrectly returned 1.  New code tracks
        long_sl_idx=2 < long_tp_idx=4 and correctly returns 0.
        """
        df = _make_df(
            {},
            {},
            {"bid_l": _LONG_SL_TRIGGER},  # bar 2: long SL fires
            {},  # bar 3: price recovers (neutral)
            {"bid_h": _LONG_TP_TRIGGER},  # bar 4: TP fires after recovery
            {},  # padding
        )
        assert _label0(df, horizon=4) == 0

    def test_short_sl_early_recovery_then_tp_returns_0(self) -> None:
        df = _make_df(
            {},
            {},
            {"ask_h": _SHORT_SL_TRIGGER},
            {},
            {"ask_l": _SHORT_TP_TRIGGER},
            {},
        )
        assert _label0(df, horizon=4) == 0

    def test_long_tp_same_bar_as_sl_long_wins(self) -> None:
        # Same bar triggers both TP and SL: long_tp_idx == long_sl_idx → profitable.
        df = _make_df(
            {},
            {},
            {"bid_h": _LONG_TP_TRIGGER, "bid_l": _LONG_SL_TRIGGER},
            {},
            {},
        )
        assert _label0(df) == 1


# ---------------------------------------------------------------------------
# Both-direction TP reachable; SL check per direction (R3 regression fix)
# ---------------------------------------------------------------------------


class TestBothTPReachable:
    def test_both_profitable_long_first_returns_1(self) -> None:
        # bar2: long TP; bar3: short TP (no SL for either)
        df = _make_df(
            {},
            {},
            {"bid_h": _LONG_TP_TRIGGER},
            {"ask_l": _SHORT_TP_TRIGGER},
            {},
        )
        assert _label0(df) == 1

    def test_both_profitable_short_first_returns_neg1(self) -> None:
        df = _make_df(
            {},
            {},
            {"ask_l": _SHORT_TP_TRIGGER},
            {"bid_h": _LONG_TP_TRIGGER},
            {},
        )
        assert _label0(df) == -1

    def test_long_sl_before_long_tp_only_short_profitable_returns_neg1(self) -> None:
        """R3: long SL fires at bar2; long TP fires later at bar3; short TP at bar3 (no short SL).

        Old code (no SL check in the 'both TP' branch) looked at
        long_tp_idx vs short_tp_idx only and returned 1 (wrong).
        New code: long_profit=False, short_profit=True → -1.
        """
        df = _make_df(
            {},
            {},
            {"bid_l": _LONG_SL_TRIGGER},  # bar 2: long SL
            {
                "bid_h": _LONG_TP_TRIGGER,  # bar 3: long TP (after SL — too late)
                "ask_l": _SHORT_TP_TRIGGER,
            },  # bar 3: short TP (profitable)
            {},
        )
        assert _label0(df) == -1

    def test_short_sl_before_short_tp_only_long_profitable_returns_1(self) -> None:
        df = _make_df(
            {},
            {},
            {"ask_h": _SHORT_SL_TRIGGER},  # bar 2: short SL
            {
                "ask_l": _SHORT_TP_TRIGGER,  # bar 3: short TP (after SL)
                "bid_h": _LONG_TP_TRIGGER,
            },  # bar 3: long TP (profitable)
            {},
        )
        assert _label0(df) == 1

    def test_both_sl_before_tp_returns_0(self) -> None:
        # Both directions have SL before TP → neither profitable
        df = _make_df(
            {},
            {},
            {"bid_l": _LONG_SL_TRIGGER, "ask_h": _SHORT_SL_TRIGGER},
            {"bid_h": _LONG_TP_TRIGGER, "ask_l": _SHORT_TP_TRIGGER},
            {},
        )
        assert _label0(df) == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_nan_atr_leaves_label_none(self) -> None:
        df = _make_df(
            {"atr_14": float("nan")},
            {},
            {"bid_h": _LONG_TP_TRIGGER},
            {},
            {},
        )
        assert _label0(df) is None

    def test_zero_atr_leaves_label_none(self) -> None:
        df = _make_df({"atr_14": 0.0}, {}, {"bid_h": _LONG_TP_TRIGGER}, {}, {})
        assert _label0(df) is None

    def test_missing_ask_o_column_raises(self) -> None:
        df = _make_df({}, {}, {}, {}, {})
        df = df.drop(columns=["ask_o"])
        with pytest.raises(ValueError, match="BA candles required"):
            tm._add_labels_bidask(df, "TEST", horizon=3)

    def test_output_length_equals_input_length(self) -> None:
        df = _make_df({}, {}, {"bid_h": _LONG_TP_TRIGGER}, {}, {})
        out = tm._add_labels_bidask(df, "TEST", horizon=3)
        assert len(out) == len(df)

    def test_last_horizon_rows_are_none(self) -> None:
        # Only i in range(n - horizon - 1) are labelled; last horizon+1 rows are None.
        n = 10
        horizon = 3
        rows = [{} for _ in range(n)]
        rows[2]["bid_h"] = _LONG_TP_TRIGGER  # bar 2 triggers TP for i=0
        df = _make_df(*rows)
        out = tm._add_labels_bidask(df, "TEST", horizon=horizon)
        # Last horizon + 1 = 4 rows should be None (indices 6–9 for n=10)
        assert all(v is None or np.isnan(float(v)) for v in out["label_tb"].iloc[-(horizon + 1) :])
