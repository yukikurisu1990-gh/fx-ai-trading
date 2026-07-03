"""F-8 trainer label contract tests (audit §4 F-8).

F8_LABEL_TIE_BREAK_CONTRACT_ALIGNED — the trainer's same-bar TP+SL
both-touch must resolve SL-first via the strict ``tp_idx < sl_idx``
"clears" test, exactly like the active backtest contract
(compare_multipair_v9_orthogonal._add_labels_bidask).

F8_ATR_WARMUP_GUARDED — trainer ATR(14) uses min_periods=14 with no
prev-close fillna; rows without a full ATR window (or with degenerate
near-zero widths) must produce NO label.

All frames are tiny synthetic in-memory constructs — no real data, no
model training.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = str(REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import train_lgbm_models as tm  # noqa: E402

_v9 = importlib.import_module("compare_multipair_v9_orthogonal")

# ---------------------------------------------------------------------------
# Fixture helpers (same barrier geometry as test_train_lgbm_labels.py)
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
_NEUTRAL = 1.1005

_LONG_TP = 1.1030  # bid_h hits long TP
_LONG_SL = 1.0990  # bid_l hits long SL
_SHORT_TP = 1.0980  # ask_l hits short TP
_SHORT_SL = 1.1015  # ask_h hits short SL


def _make_ba_df(*bars: dict) -> pd.DataFrame:
    """Minimal BA frame accepted by BOTH label implementations.

    Includes bid_c/ask_c (required by the v9 backtest function for its
    F-2 PnL columns; ignored by the trainer's label logic).
    """
    rows = [dict(b) for b in bars]

    def _col(key: str, default: float) -> list[float]:
        return [r.get(key, default) for r in rows]

    return pd.DataFrame(
        {
            "atr_14": _col("atr_14", _ATR),
            "ask_o": _col("ask_o", _ENTRY_ASK),
            "bid_o": _col("bid_o", _ENTRY_BID),
            "bid_h": _col("bid_h", _NEUTRAL),
            "bid_l": _col("bid_l", _NEUTRAL),
            "ask_h": _col("ask_h", _NEUTRAL),
            "ask_l": _col("ask_l", _NEUTRAL),
            "bid_c": _col("bid_c", _NEUTRAL),
            "ask_c": _col("ask_c", _NEUTRAL),
        }
    )


def _norm_label(v: object) -> int | None:
    """Normalise a stored label cell to int or None.

    pandas may coerce a mixed int/None label list to float64 (None → NaN),
    so NaN and None are the same "no label" outcome.
    """
    if v is None:
        return None
    f = float(v)  # type: ignore[arg-type]
    if np.isnan(f):
        return None
    return int(f)


def _trainer_labels(df: pd.DataFrame, horizon: int = 3) -> list[int | None]:
    out = tm._add_labels_bidask(df, "TEST", horizon=horizon)
    return [_norm_label(v) for v in out[tm._LABEL_COLUMN]]


def _backtest_labels(df: pd.DataFrame, horizon: int = 3) -> list[int | None]:
    out = _v9._add_labels_bidask(df, horizon, tm._TP_MULT, tm._SL_MULT)
    return [_norm_label(v) for v in out[_v9.LABEL_COLUMN]]


# ---------------------------------------------------------------------------
# F8-A: same-bar tie resolves SL-first (strict <)
# ---------------------------------------------------------------------------


class TestSameBarTieSLFirst:
    def test_long_same_bar_tp_sl_tie_sl_wins(self) -> None:
        # bar2 touches BOTH long TP and long SL → SL-first → not profitable.
        df = _make_ba_df(
            {},
            {},
            {"bid_h": _LONG_TP, "bid_l": _LONG_SL},
            {},
            {},
        )
        assert _trainer_labels(df)[0] == 0

    def test_short_same_bar_tp_sl_tie_sl_wins(self) -> None:
        df = _make_ba_df(
            {},
            {},
            {"ask_l": _SHORT_TP, "ask_h": _SHORT_SL},
            {},
            {},
        )
        assert _trainer_labels(df)[0] == 0

    def test_long_tie_with_clean_short_tp_yields_short(self) -> None:
        # Long ties (SL-first → not profitable); short TP clears cleanly →
        # the tie-break flip changes the winner to -1 (old `<=` gave +1).
        df = _make_ba_df(
            {},
            {},
            {"bid_h": _LONG_TP, "bid_l": _LONG_SL},
            {"ask_l": _SHORT_TP},
            {},
        )
        assert _trainer_labels(df)[0] == -1

    def test_tp_strictly_before_sl_still_profitable(self) -> None:
        # Strict < must NOT reject TP genuinely landing before SL.
        df = _make_ba_df(
            {},
            {},
            {"bid_h": _LONG_TP},
            {"bid_l": _LONG_SL},
            {},
        )
        assert _trainer_labels(df)[0] == 1


# ---------------------------------------------------------------------------
# F8-A: trainer vs backtest contract agreement
# ---------------------------------------------------------------------------

_SCENARIOS: dict[str, list[dict]] = {
    "long_tp_clean": [{}, {}, {"bid_h": _LONG_TP}, {}, {}],
    "short_tp_clean": [{}, {}, {"ask_l": _SHORT_TP}, {}, {}],
    "timeout_all_neutral": [{}, {}, {}, {}, {}],
    "long_same_bar_tie": [{}, {}, {"bid_h": _LONG_TP, "bid_l": _LONG_SL}, {}, {}],
    "short_same_bar_tie": [{}, {}, {"ask_l": _SHORT_TP, "ask_h": _SHORT_SL}, {}, {}],
    "long_sl_then_tp": [{}, {}, {"bid_l": _LONG_SL}, {"bid_h": _LONG_TP}, {}],
    "short_sl_then_tp": [{}, {}, {"ask_h": _SHORT_SL}, {"ask_l": _SHORT_TP}, {}],
    "both_tp_long_first": [{}, {}, {"bid_h": _LONG_TP}, {"ask_l": _SHORT_TP}, {}],
    "both_tp_short_first": [{}, {}, {"ask_l": _SHORT_TP}, {"bid_h": _LONG_TP}, {}],
    "both_tp_same_bar": [{}, {}, {"bid_h": _LONG_TP, "ask_l": _SHORT_TP}, {}, {}],
    "long_tie_short_tp": [
        {},
        {},
        {"bid_h": _LONG_TP, "bid_l": _LONG_SL},
        {"ask_l": _SHORT_TP},
        {},
    ],
    "nan_atr_no_label": [{"atr_14": float("nan")}, {}, {"bid_h": _LONG_TP}, {}, {}],
    "zero_atr_no_label": [{"atr_14": 0.0}, {}, {"bid_h": _LONG_TP}, {}, {}],
}


class TestTrainerBacktestAgreement:
    def test_scenario_labels_identical(self) -> None:
        for name, bars in _SCENARIOS.items():
            df = _make_ba_df(*bars)
            got_tm = _trainer_labels(df)
            got_v9 = _backtest_labels(df)
            assert got_tm == got_v9, f"scenario {name}: trainer {got_tm} != backtest {got_v9}"

    def test_random_walk_labels_identical(self) -> None:
        # Seeded random-walk BA frame; ATR computed via the trainer's own
        # feature pipeline (min_periods=14 warmup NaNs included) so both
        # functions see the identical atr_14 / entry inputs.
        rng = np.random.default_rng(7)
        n = 300
        mid_c = 1.10 + np.cumsum(rng.normal(0.0, 0.0004, size=n))
        mid_o = np.concatenate([[1.10], mid_c[:-1]])
        wick_hi = np.abs(rng.normal(0.0, 0.0003, size=n))
        wick_lo = np.abs(rng.normal(0.0, 0.0003, size=n))
        mid_h = np.maximum(mid_o, mid_c) + wick_hi
        mid_l = np.minimum(mid_o, mid_c) - wick_lo
        half_spread = 0.0001
        df = pd.DataFrame(
            {
                "open": mid_o,
                "high": mid_h,
                "low": mid_l,
                "close": mid_c,
                "bid_o": mid_o - half_spread,
                "bid_h": mid_h - half_spread,
                "bid_l": mid_l - half_spread,
                "bid_c": mid_c - half_spread,
                "ask_o": mid_o + half_spread,
                "ask_h": mid_h + half_spread,
                "ask_l": mid_l + half_spread,
                "ask_c": mid_c + half_spread,
            }
        )
        df = tm._add_features(df)
        horizon = 10
        got_tm = _trainer_labels(df, horizon=horizon)
        got_v9 = _backtest_labels(df, horizon=horizon)
        assert got_tm == got_v9
        # Sanity: the frame actually exercises labelled rows.
        assert any(v is not None for v in got_tm)


# ---------------------------------------------------------------------------
# F8-B: ATR warmup guard
# ---------------------------------------------------------------------------


def _raw_ba_frame(n: int, flat_first: int = 0, flat_range: float = 0.0) -> pd.DataFrame:
    """Raw BA frame for the trainer feature pipeline.

    First ``flat_first`` bars are (near-)flat with total range
    ``flat_range`` — under the old min_periods=1 ATR these produced
    degenerate near-zero barrier widths.
    """
    rows = []
    for i in range(n):
        if i < flat_first:
            o = c = 1.1000
            hi = 1.1000 + flat_range
            lo = 1.1000 - flat_range
        else:
            o = 1.1000 + (i % 3) * 0.0005
            c = o + 0.0004
            hi = c + 0.0006
            lo = o - 0.0006
        rows.append((o, hi, lo, c))
    o_, h_, l_, c_ = (np.array(x, dtype=np.float64) for x in zip(*rows, strict=True))
    half_spread = 0.0001
    return pd.DataFrame(
        {
            "open": o_,
            "high": h_,
            "low": l_,
            "close": c_,
            "bid_o": o_ - half_spread,
            "bid_h": h_ - half_spread,
            "bid_l": l_ - half_spread,
            "bid_c": c_ - half_spread,
            "ask_o": o_ + half_spread,
            "ask_h": h_ + half_spread,
            "ask_l": l_ + half_spread,
            "ask_c": c_ + half_spread,
        }
    )


class TestATRWarmupGuard:
    def test_first_13_rows_have_nan_atr(self) -> None:
        df = tm._add_features(_raw_ba_frame(40))
        assert df["atr_14"].iloc[:13].isna().all()
        assert np.isfinite(df["atr_14"].iloc[13:]).all()

    def test_warmup_rows_get_no_label(self) -> None:
        # Force a long-TP touch on EVERY bar; only rows with a full ATR
        # window may be labelled.
        df = tm._add_features(_raw_ba_frame(40))
        df["bid_h"] = df["bid_h"] + 1.0  # every window hits long TP instantly
        labels = _trainer_labels(df, horizon=3)
        assert all(v is None for v in labels[:13])
        assert labels[13] is not None

    def test_degenerate_near_zero_width_produces_no_label(self) -> None:
        # 13 near-flat bars (range 1e-9) then volatile bars: the old
        # min_periods=1 ATR yielded a tiny positive width for rows 0-12 and
        # labelled them; the guarded ATR must leave them unlabelled.
        df = tm._add_features(_raw_ba_frame(40, flat_first=13, flat_range=1e-9))
        labels = _trainer_labels(df, horizon=3)
        assert all(v is None for v in labels[:13])

    def test_nonpositive_atr_row_gets_no_label(self) -> None:
        df = _make_ba_df({"atr_14": 0.0}, {}, {"bid_h": _LONG_TP}, {}, {})
        assert _trainer_labels(df)[0] is None

    def test_nonfinite_entry_gets_no_label(self) -> None:
        df = _make_ba_df({}, {"ask_o": float("nan")}, {"bid_h": _LONG_TP}, {}, {})
        assert _trainer_labels(df)[0] is None
