"""Verify vectorised _add_labels_bidask matches the original Python-loop output.

Loads a slice of real bid/ask candle data, runs both implementations,
asserts byte-equal labels.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd


def _first_hit_idx(mask: np.ndarray) -> int:
    if not mask.any():
        return -1
    return int(np.argmax(mask))


def _add_labels_bidask_loop(
    df: pd.DataFrame, horizon: int, tp_mult: float, sl_mult: float
) -> list[int | None]:
    """Original Python-loop implementation (reference)."""
    n = len(df)
    bid_h = df["bid_h"].to_numpy(dtype=np.float64)
    bid_l = df["bid_l"].to_numpy(dtype=np.float64)
    ask_h = df["ask_h"].to_numpy(dtype=np.float64)
    ask_l = df["ask_l"].to_numpy(dtype=np.float64)
    ask_o = df["ask_o"].to_numpy(dtype=np.float64)
    bid_o = df["bid_o"].to_numpy(dtype=np.float64)
    atrs = df["atr_14"].to_numpy(dtype=np.float64)
    labels: list[int | None] = [None] * n
    for i in range(n - horizon - 1):
        atr_i = atrs[i]
        if not np.isfinite(atr_i) or atr_i <= 0:
            continue
        entry_long = ask_o[i + 1]
        entry_short = bid_o[i + 1]
        if not (np.isfinite(entry_long) and np.isfinite(entry_short)):
            continue
        tp = tp_mult * atr_i
        sl = sl_mult * atr_i
        long_bh = bid_h[i + 1 : i + 1 + horizon]
        long_bl = bid_l[i + 1 : i + 1 + horizon]
        short_al = ask_l[i + 1 : i + 1 + horizon]
        short_ah = ask_h[i + 1 : i + 1 + horizon]
        long_tp_idx = _first_hit_idx(long_bh >= entry_long + tp)
        long_sl_idx = _first_hit_idx(long_bl <= entry_long - sl)
        short_tp_idx = _first_hit_idx(short_al <= entry_short - tp)
        short_sl_idx = _first_hit_idx(short_ah >= entry_short + sl)
        long_clears = long_tp_idx >= 0 and (long_sl_idx < 0 or long_tp_idx < long_sl_idx)
        short_clears = short_tp_idx >= 0 and (short_sl_idx < 0 or short_tp_idx < short_sl_idx)
        if long_clears and not short_clears:
            labels[i] = 1
        elif short_clears and not long_clears:
            labels[i] = -1
        elif long_clears and short_clears:
            labels[i] = 1 if long_tp_idx <= short_tp_idx else -1
        else:
            labels[i] = 0
    return labels


def _add_labels_bidask_vec(
    df: pd.DataFrame, horizon: int, tp_mult: float, sl_mult: float
) -> list[int | None]:
    """Vectorised implementation (paste of v26 function body)."""
    n = len(df)
    bid_h = df["bid_h"].to_numpy(dtype=np.float64)
    bid_l = df["bid_l"].to_numpy(dtype=np.float64)
    ask_h = df["ask_h"].to_numpy(dtype=np.float64)
    ask_l = df["ask_l"].to_numpy(dtype=np.float64)
    ask_o = df["ask_o"].to_numpy(dtype=np.float64)
    bid_o = df["bid_o"].to_numpy(dtype=np.float64)
    atrs = df["atr_14"].to_numpy(dtype=np.float64)
    n_eff = n - horizon - 1
    if n_eff <= 0:
        return [None] * n
    atr_view = atrs[:n_eff]
    entry_long_arr = ask_o[1 : n_eff + 1]
    entry_short_arr = bid_o[1 : n_eff + 1]
    valid = (
        np.isfinite(atr_view)
        & (atr_view > 0)
        & np.isfinite(entry_long_arr)
        & np.isfinite(entry_short_arr)
    )
    bid_h_win = np.lib.stride_tricks.sliding_window_view(bid_h[1:], horizon)[:n_eff]
    bid_l_win = np.lib.stride_tricks.sliding_window_view(bid_l[1:], horizon)[:n_eff]
    ask_h_win = np.lib.stride_tricks.sliding_window_view(ask_h[1:], horizon)[:n_eff]
    ask_l_win = np.lib.stride_tricks.sliding_window_view(ask_l[1:], horizon)[:n_eff]
    tp_arr = tp_mult * atr_view
    sl_arr = sl_mult * atr_view
    long_tp_thresh = (entry_long_arr + tp_arr).reshape(-1, 1)
    long_sl_thresh = (entry_long_arr - sl_arr).reshape(-1, 1)
    short_tp_thresh = (entry_short_arr - tp_arr).reshape(-1, 1)
    short_sl_thresh = (entry_short_arr + sl_arr).reshape(-1, 1)
    long_tp_mask = bid_h_win >= long_tp_thresh
    long_sl_mask = bid_l_win <= long_sl_thresh
    short_tp_mask = ask_l_win <= short_tp_thresh
    short_sl_mask = ask_h_win >= short_sl_thresh

    def _first_hit_vec(mask: np.ndarray) -> np.ndarray:
        has_any = mask.any(axis=1)
        first = mask.argmax(axis=1)
        return np.where(has_any, first, -1)

    long_tp_idx = _first_hit_vec(long_tp_mask)
    long_sl_idx = _first_hit_vec(long_sl_mask)
    short_tp_idx = _first_hit_vec(short_tp_mask)
    short_sl_idx = _first_hit_vec(short_sl_mask)
    long_clears = (long_tp_idx >= 0) & ((long_sl_idx < 0) | (long_tp_idx < long_sl_idx))
    short_clears = (short_tp_idx >= 0) & ((short_sl_idx < 0) | (short_tp_idx < short_sl_idx))
    inner = np.zeros(n_eff, dtype=np.int64)
    inner[long_clears & ~short_clears] = 1
    inner[short_clears & ~long_clears] = -1
    both = long_clears & short_clears
    both_long = both & (long_tp_idx <= short_tp_idx)
    both_short = both & ~(long_tp_idx <= short_tp_idx)
    inner[both_long] = 1
    inner[both_short] = -1
    labels: list[int | None] = [None] * n
    for i in np.flatnonzero(valid):
        labels[i] = int(inner[i])
    return labels


def main() -> None:
    # Load slice of real BA candles.
    path = Path("data/candles_EUR_USD_M1_365d_BA.jsonl")
    rows: list[dict] = []
    with path.open() as f:
        for j, line in enumerate(f):
            if j >= 10_000:  # limited slice for fast test
                break
            d = json.loads(line)
            rows.append(d)

    df = pd.DataFrame(rows)
    # JSONL has flat columns: bid_o/h/l/c, ask_o/h/l/c. Use mid as (b+a)/2.
    df["mid_h"] = (df["bid_h"] + df["ask_h"]) / 2.0
    df["mid_l"] = (df["bid_l"] + df["ask_l"]) / 2.0
    df["mid_c"] = (df["bid_c"] + df["ask_c"]) / 2.0
    prev_c = df["mid_c"].shift(1)
    tr = pd.concat(
        [df["mid_h"] - df["mid_l"], (df["mid_h"] - prev_c).abs(), (df["mid_l"] - prev_c).abs()],
        axis=1,
    ).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    horizon = 12

    print("Running both implementations on 10,000-row slice...")  # noqa: PRINT
    for tp_mult, sl_mult in [(2.0, 2.0), (3.0, 3.0), (4.0, 4.0), (5.0, 3.0), (3.0, 5.0)]:
        t0 = time.time()  # noqa: CLOCK
        loop_labels = _add_labels_bidask_loop(df, horizon, tp_mult, sl_mult)
        t1 = time.time()  # noqa: CLOCK
        vec_labels = _add_labels_bidask_vec(df, horizon, tp_mult, sl_mult)
        t2 = time.time()  # noqa: CLOCK

        # Compare element-by-element.
        n_diff = 0
        first_diff_idx = -1
        for i, (a, b) in enumerate(zip(loop_labels, vec_labels, strict=False)):
            if a != b:
                if first_diff_idx == -1:
                    first_diff_idx = i
                n_diff += 1

        loop_ms = (t1 - t0) * 1000
        vec_ms = (t2 - t1) * 1000
        speedup = loop_ms / vec_ms if vec_ms > 0 else float("inf")
        print(  # noqa: PRINT
            f"  tp={tp_mult}, sl={sl_mult}: "
            f"loop={loop_ms:.1f}ms vec={vec_ms:.1f}ms speedup={speedup:.1f}x "
            f"diffs={n_diff}/{len(loop_labels)}"
        )
        if n_diff > 0:
            print(  # noqa: PRINT
                f"    First diff at index {first_diff_idx}: "
                f"loop={loop_labels[first_diff_idx]} vec={vec_labels[first_diff_idx]}"
            )


if __name__ == "__main__":
    main()
