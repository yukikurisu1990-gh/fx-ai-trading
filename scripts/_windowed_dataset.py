"""Windowed dataset builder for Phase 29.0b-β A0-broad sequence/NN eval.

Per PR #354 §6 / §7 (Phase 29.0b-α A0-broad design memo) and PR #353 §6
(A0-broad preflight audit).

Windowed input shape (α-fixed; NG#A0B-1):
  N = 32 M5 bars × 8 channels (bid_OHLC + ask_OHLC)
  NO mid price; NO volume; NO z-score; NO batch-norm

Per-pair pip normalisation + entry-price centering (relative to long-side
entry ask_o at signal_ts + 1 min). Float32. Deterministic.

CAUSALITY GUARD (per user instruction):
  - entry_m1_idx = signal_ts + 1 min entry point (D-1)
  - sequence window must end strictly before entry_m1_idx
  - no M1 bar with timestamp >= entry timestamp may enter sequence input
  - violation → CausalityGuardError HALT
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Constants (α-fixed per PR #354 §6 / §7)
# ---------------------------------------------------------------------------

N_M5_BARS = 32  # window length in M5 bars
M5_BAR_MINUTES = 5  # M5 bar duration
N_CHANNELS = 8  # bid_OHLC (4) + ask_OHLC (4)
N_M1_PER_M5 = 5  # 5 M1 bars per M5 bar
TOTAL_M1_BARS_IN_WINDOW = N_M5_BARS * N_M1_PER_M5  # 32 × 5 = 160 M1 bars

# Channel order (fixed; NG#A0B-1)
CHANNEL_NAMES: tuple[str, ...] = (
    "bid_O", "bid_H", "bid_L", "bid_C",
    "ask_O", "ask_H", "ask_L", "ask_C",
)

# Coverage HALT threshold per PR #354 §16.2 item 7 / PR #353 §6.4
WINDOWED_COVERAGE_HALT_THRESHOLD = 0.95


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CausalityGuardError(RuntimeError):
    """Raised when sequence input contains M1 data at or beyond entry timestamp.

    Per user instruction: sequence window must end strictly before
    entry_m1_idx (signal_ts + 1 min). HALT on violation.
    """


class WindowedCoverageError(RuntimeError):
    """Raised when windowed dataset coverage falls below threshold.

    Per PR #354 §16.2 item 7. HALT if < 95% per split.
    """


# ---------------------------------------------------------------------------
# M1 → M5 aggregation (per-bar bid/ask OHLC)
# ---------------------------------------------------------------------------


def _aggregate_m1_to_m5_bar(
    bid_o: np.ndarray, bid_h: np.ndarray, bid_l: np.ndarray, bid_c: np.ndarray,
    ask_o: np.ndarray, ask_h: np.ndarray, ask_l: np.ndarray, ask_c: np.ndarray,
) -> np.ndarray:
    """Aggregate 5 M1 bars into 1 M5 bar; returns (8,) channels.

    Channels: bid_O / bid_H / bid_L / bid_C / ask_O / ask_H / ask_L / ask_C.

    Aggregation rules:
      - O = first M1 in slice
      - H = max M1 high in slice
      - L = min M1 low in slice
      - C = last M1 close in slice
    """
    return np.array([
        bid_o[0],            # bid_O (first)
        np.max(bid_h),       # bid_H (max)
        np.min(bid_l),       # bid_L (min)
        bid_c[-1],           # bid_C (last)
        ask_o[0],            # ask_O (first)
        np.max(ask_h),       # ask_H (max)
        np.min(ask_l),       # ask_L (min)
        ask_c[-1],           # ask_C (last)
    ], dtype=np.float32)


# ---------------------------------------------------------------------------
# Per-row windowed input builder
# ---------------------------------------------------------------------------


def _build_window_for_row(
    signal_ts: pd.Timestamp,
    pair_data: dict,
    n_m5_bars: int = N_M5_BARS,
    causality_check: bool = True,
) -> tuple[np.ndarray | None, bool]:
    """Build (32, 8) windowed input for a single row.

    Returns (window, valid):
      window: np.ndarray shape (32, 8) float32, or None if invalid
      valid: True if window is fully populated; False if boundary/NaN

    CAUSALITY GUARD: verifies the last M1 bar in the window has timestamp
    strictly less than the entry M1 timestamp (signal_ts + 1 min).
    """
    pip = pair_data["pip"]
    m1_pos = pair_data["m1_pos"]
    target_entry_ts = signal_ts + pd.Timedelta(minutes=1)
    if target_entry_ts not in m1_pos.index:
        return None, False
    entry_idx = int(m1_pos.loc[target_entry_ts])

    # Window covers the 32 × 5 = 160 M1 bars ending strictly BEFORE entry_idx
    window_end_m1_idx = entry_idx  # exclusive
    window_start_m1_idx = window_end_m1_idx - TOTAL_M1_BARS_IN_WINDOW

    if window_start_m1_idx < 0:
        return None, False  # not enough history at dataset boundary

    # Causality guard: every M1 bar in [window_start_m1_idx, window_end_m1_idx)
    # has timestamp strictly less than target_entry_ts.
    if causality_check:
        last_m1_in_window_ts = m1_pos.index[window_end_m1_idx - 1]
        if last_m1_in_window_ts >= target_entry_ts:
            raise CausalityGuardError(
                f"Causality violation: last M1 bar in window has timestamp "
                f"{last_m1_in_window_ts} >= entry timestamp {target_entry_ts}; "
                f"window_end_m1_idx={window_end_m1_idx} entry_idx={entry_idx}"
            )

    # Build per-M5-bar aggregation
    bid_o_arr = pair_data["bid_o"]
    bid_h_arr = pair_data["bid_h"]
    bid_l_arr = pair_data["bid_l"]
    bid_c_arr = pair_data["bid_c"]
    ask_o_arr = pair_data["ask_o"]
    ask_h_arr = pair_data["ask_h"]
    ask_l_arr = pair_data["ask_l"]
    ask_c_arr = pair_data["ask_c"]

    window = np.empty((n_m5_bars, N_CHANNELS), dtype=np.float32)
    for i in range(n_m5_bars):
        m5_start = window_start_m1_idx + i * N_M1_PER_M5
        m5_end = m5_start + N_M1_PER_M5
        window[i] = _aggregate_m1_to_m5_bar(
            bid_o_arr[m5_start:m5_end], bid_h_arr[m5_start:m5_end],
            bid_l_arr[m5_start:m5_end], bid_c_arr[m5_start:m5_end],
            ask_o_arr[m5_start:m5_end], ask_h_arr[m5_start:m5_end],
            ask_l_arr[m5_start:m5_end], ask_c_arr[m5_start:m5_end],
        )

    # Per-pair pip normalisation + entry-price centering
    entry_ask_o = float(ask_o_arr[entry_idx])  # signal_ts + 1min ask_o
    window = (window - entry_ask_o) / pip

    return window, True


# ---------------------------------------------------------------------------
# Batch windowed input builder
# ---------------------------------------------------------------------------


def build_windowed_input_per_row(
    df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    n_m5_bars: int = N_M5_BARS,
    causality_check: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Build per-row windowed inputs for an entire DataFrame.

    Returns (windowed, valid_mask):
      windowed: np.ndarray shape (n_rows, 32, 8) float32; rows where
        valid_mask=False contain garbage (do not use)
      valid_mask: np.ndarray shape (n_rows,) bool; True if row has full
        32-bar window

    CAUSALITY GUARD applied per-row; CausalityGuardError raised on
    violation (HALT semantics).
    """
    n = len(df)
    windowed = np.zeros((n, n_m5_bars, N_CHANNELS), dtype=np.float32)
    valid_mask = np.zeros(n, dtype=bool)
    pairs = df["pair"].to_numpy()
    signal_ts_arr = df["signal_ts"].to_numpy()
    for i in range(n):
        pr = pair_runtime_map.get(str(pairs[i]))
        if pr is None:
            continue
        window, valid = _build_window_for_row(
            pd.Timestamp(signal_ts_arr[i]),
            pr,
            n_m5_bars=n_m5_bars,
            causality_check=causality_check,
        )
        if valid and window is not None:
            windowed[i] = window
            valid_mask[i] = True
    return windowed, valid_mask


# ---------------------------------------------------------------------------
# Per-pair coverage report
# ---------------------------------------------------------------------------


def compute_windowed_coverage_per_pair(
    df: pd.DataFrame, valid_mask: np.ndarray, pairs: list[str]
) -> dict[str, dict]:
    """Per-pair count of valid windowed rows + coverage rate.

    Used by sanity probe item 7. HALT if overall coverage < 95%.
    """
    pair_arr = df["pair"].to_numpy()
    out: dict[str, dict] = {}
    for pair in pairs:
        mask = pair_arr == pair
        n_total = int(mask.sum())
        n_valid = int((mask & valid_mask).sum())
        rate = n_valid / max(n_total, 1)
        out[pair] = {"n_total": n_total, "n_valid": n_valid, "rate": float(rate)}
    return out


def assert_windowed_coverage_meets_threshold(
    coverage_per_pair: dict[str, dict],
    split_name: str,
    threshold: float = WINDOWED_COVERAGE_HALT_THRESHOLD,
) -> None:
    """HALT if overall coverage < threshold (default 95%).

    Per PR #354 §16.2 item 7 / PR #353 §6.4.
    """
    total = sum(v["n_total"] for v in coverage_per_pair.values())
    valid = sum(v["n_valid"] for v in coverage_per_pair.values())
    overall_rate = valid / max(total, 1)
    if overall_rate < threshold:
        raise WindowedCoverageError(
            f"Windowed dataset coverage on {split_name} = "
            f"{overall_rate:.3%} < {threshold:.0%} (HALT per PR #354 §16.2 item 7); "
            f"n_total={total} n_valid={valid}"
        )


# ---------------------------------------------------------------------------
# Causality sanity probe (item 7 / 8 supplement)
# ---------------------------------------------------------------------------


def verify_causality_guard(
    df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    sample_size: int = 1000,
    seed: int = 42,
) -> dict:
    """Sanity probe: verify causality guard on a random sample.

    For each sampled row:
      - compute entry_m1_idx = signal_ts + 1 min
      - compute window_end_m1_idx (last M1 in window)
      - assert m1_pos.index[window_end_m1_idx - 1] < signal_ts + 1 min

    Returns dict with sample count and per-pair max-input-timestamp / entry-timestamp.
    Raises CausalityGuardError on violation.
    """
    rng = np.random.RandomState(seed)
    n = len(df)
    sample_indices = rng.choice(n, min(sample_size, n), replace=False)
    pairs = df["pair"].to_numpy()
    signal_ts_arr = df["signal_ts"].to_numpy()

    n_checked = 0
    n_valid_windows = 0
    violations: list[dict] = []
    max_input_ts_examples: list[dict] = []

    for i in sample_indices:
        pr = pair_runtime_map.get(str(pairs[i]))
        if pr is None:
            continue
        signal_ts = pd.Timestamp(signal_ts_arr[i])
        target_entry_ts = signal_ts + pd.Timedelta(minutes=1)
        m1_pos = pr["m1_pos"]
        if target_entry_ts not in m1_pos.index:
            continue
        entry_idx = int(m1_pos.loc[target_entry_ts])
        window_end_m1_idx = entry_idx
        window_start_m1_idx = window_end_m1_idx - TOTAL_M1_BARS_IN_WINDOW
        if window_start_m1_idx < 0:
            continue
        n_checked += 1
        last_m1_in_window_ts = m1_pos.index[window_end_m1_idx - 1]
        if last_m1_in_window_ts >= target_entry_ts:
            violations.append({
                "row_idx": int(i),
                "pair": str(pairs[i]),
                "signal_ts": str(signal_ts),
                "target_entry_ts": str(target_entry_ts),
                "last_m1_in_window_ts": str(last_m1_in_window_ts),
            })
        else:
            n_valid_windows += 1
            if len(max_input_ts_examples) < 5:
                max_input_ts_examples.append({
                    "row_idx": int(i),
                    "pair": str(pairs[i]),
                    "signal_ts": str(signal_ts),
                    "target_entry_ts": str(target_entry_ts),
                    "max_input_ts": str(last_m1_in_window_ts),
                    "gap_minutes": float(
                        (target_entry_ts - last_m1_in_window_ts).total_seconds() / 60.0
                    ),
                })

    if violations:
        raise CausalityGuardError(
            f"Causality guard violated on {len(violations)} sampled row(s); "
            f"first violation: {violations[0]}"
        )

    return {
        "n_sampled": len(sample_indices),
        "n_checked": n_checked,
        "n_valid_windows": n_valid_windows,
        "n_violations": 0,
        "max_input_ts_examples": max_input_ts_examples,
    }
