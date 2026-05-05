"""compare_prod_ablation.py — v26差分アブレーションバックテスト

本番ロジック (anti-pyramiding / Top-K=3 / currency diversification) を忠実に
再現した逐次シミュレーションで、各差分の単独・複合効果を測定する。

比較セル:
  A  baseline      : 本番現状 (45特徴量, 正則化なし, 365d固定80/20分割)
  B  +spread       : スプレッド3特徴量追加
  C  +reg          : 正則化追加 (reg_alpha=0.1, reg_lambda=0.1, min_child_samples=50)
  D  +spread+reg   : B+C
  E  +730d         : 730d固定80/20 (D+データ量増)
  F  wf90/90       : 90dウィンドウ90dステップ WF (D+WF)
  G  wf365/90      : 365dウィンドウ90dステップ WF (D+WF)

本番準拠ルール:
  - ナンピン対策: 同一ペアはホライズン分バー消化まで再エントリー不可
  - Top-K=3 + 通貨多様化 (同通貨ファミリー重複排除)
  - 信頼度閾値 0.40
  - スプレッドコスト 1.0pip
  - B-2 bid/ask ラベル (長短それぞれの TP/SL バリア)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
_HORIZON = 20
_TP_MULT = 1.5
_SL_MULT = 1.0
_FILTER_K = 1.0
_CONF_THR = 0.40
_SPREAD_PIP = 1.0
_N_ESTIMATORS = 200
_TOP_K = 3
_LABEL_COLUMN = "label_tb"
_LABEL_LONG = "label_long"        # +1 long_TP first / -1 long_SL first / 0 timeout
_LABEL_SHORT = "label_short"      # +1 short_TP first / -1 short_SL first / 0 timeout
_TO_PNL_LONG = "timeout_pnl_long"   # NEW BUG #H: timeout 時の実 PnL (long, pip)
_TO_PNL_SHORT = "timeout_pnl_short" # 同 short
_LABEL_ENCODE = {-1: 0, 0: 1, 1: 2}

# Variant flags (set in main() from CLI)
_TRAINING_MODE = "direction"      # "multi" or "direction"
_USE_CLASS_WEIGHT = True
_EV_SL_FACTOR = 1.0               # Multi mode: scale p_short in EV formula
_BAR_MINUTES = 1                  # 1 for M1, 5 for M5, 15 for M15. Anti-pyramiding 用
_TRAIN_DAYS_OVERRIDE = 0          # 0 = use cell default, >0 = override
_STEP_DAYS_OVERRIDE  = 0
_CUSTOM_CLASS_WEIGHT: dict | None = None  # When set, overrides both balanced/None

_ALL_PAIRS = [
    "AUD_CAD",
    "AUD_JPY",
    "AUD_NZD",
    "AUD_USD",
    "CHF_JPY",
    "EUR_AUD",
    "EUR_CAD",
    "EUR_CHF",
    "EUR_GBP",
    "EUR_JPY",
    "EUR_USD",
    "GBP_AUD",
    "GBP_CHF",
    "GBP_JPY",
    "GBP_USD",
    "NZD_JPY",
    "NZD_USD",
    "USD_CAD",
    "USD_CHF",
    "USD_JPY",
]

_PIP_SIZE: dict[str, float] = {
    "AUD_CAD": 0.0001,
    "AUD_JPY": 0.01,
    "AUD_NZD": 0.0001,
    "AUD_USD": 0.0001,
    "CHF_JPY": 0.01,
    "EUR_AUD": 0.0001,
    "EUR_CAD": 0.0001,
    "EUR_CHF": 0.0001,
    "EUR_GBP": 0.0001,
    "EUR_JPY": 0.01,
    "EUR_USD": 0.0001,
    "GBP_AUD": 0.0001,
    "GBP_CHF": 0.0001,
    "GBP_JPY": 0.01,
    "GBP_USD": 0.0001,
    "NZD_JPY": 0.01,
    "NZD_USD": 0.0001,
    "USD_CAD": 0.0001,
    "USD_CHF": 0.0001,
    "USD_JPY": 0.01,
}

_BASE_INDICATORS = [
    "atr_14", "bb_lower", "bb_middle", "bb_pct_b", "bb_upper", "bb_width",
    "ema_12", "ema_26", "macd_histogram", "macd_line", "macd_signal",
    "rsi_14", "sma_20", "sma_50",
]

# Upper-TF feature suffix list (8 feats per prefix)
_UPPER_TF_SUFFIXES = [
    "_return_1", "_return_3", "_volatility", "_rsi_14",
    "_ma_slope", "_bb_pct_b", "_trend_slope", "_trend_dir",
]

# MTF features (h4_atr_14, d1_*, w1_*)
_MTF_FEATURES = [
    "h4_atr_14", "d1_return_3", "d1_range_pct", "d1_atr_14",
    "w1_return_1", "w1_range_pct",
]

# Multi-TF feature schedules: base TF (in minutes) → 上位 TF resample rule + prefix
_UPPER_TF_RULES: dict[int, list[tuple[str, str]]] = {
    1:  [("5min", "m5"),  ("15min", "m15"), ("1h", "h1")],     # M1 base (旧来)
    5:  [("15min", "m15"), ("1h", "h1"),    ("4h", "h4_full")], # M5 base
    15: [("1h", "h1"),    ("4h", "h4_full"), ("8h", "h8")],     # M15 base
}


def _get_base_feat_for_tf(bar_minutes: int) -> list[str]:
    """Base TF に応じた特徴量列名のリスト."""
    rules = _UPPER_TF_RULES.get(bar_minutes, _UPPER_TF_RULES[1])
    upper_feats = []
    for _rule, pfx in rules:
        upper_feats.extend(f"{pfx}{suf}" for suf in _UPPER_TF_SUFFIXES)
    return _BASE_INDICATORS + upper_feats + _MTF_FEATURES


# Backward compat: M1 base default (used at module load before _BAR_MINUTES set)
_BASE_FEAT = _get_base_feat_for_tf(1)
_SPREAD_FEAT = ["spread_now_pip", "spread_ma_ratio_20", "spread_zscore_50"]

_LGBM_BASE_PARAMS = {"learning_rate": 0.05, "num_leaves": 31, "verbose": -1, "class_weight": "balanced",
                     "random_state": 42}  # NEW BUG #G fix: 再現性確保
_LGBM_REG_PARAMS = {
    **_LGBM_BASE_PARAMS,
    "min_child_samples": 50,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "random_state": 42,
}

# マルチペアモデル用: ペア名 → 整数インデックス (pair_id 特徴量)
_PAIR_IDX: dict[str, int] = {p: i for i, p in enumerate(_ALL_PAIRS)}
_MULTIPAIR_KEY = "__multipair__"


@dataclass
class AblationCell:
    name: str
    spread_features: bool
    regularize: bool
    train_days: int  # 0 = fixed 80/20 split; >0 = WF rolling window
    step_days: int  # 0 = fixed split; >0 = WF step size
    data_suffix: str  # "365d" or "730d"
    multipair: bool = False  # True = 全ペア統合1モデル + pair_id特徴量
    description: str = field(default="")


_CELLS: list[AblationCell] = [
    # Step 0: ベースライン (固定80/20, 365d) — 比較基準
    AblationCell(
        "A_baseline",
        False,
        False,
        0,
        0,
        "365d",
        description="ベースライン: 45特徴量, 正則化なし, 固定80/20, 365d",
    ),
    # Step 1: WFベースライン (窓幅比較)
    AblationCell(
        "B_wf90_base",
        False,
        False,
        90,
        90,
        "730d",
        description="WFベースライン: 45特徴量, 正則化なし, WF90d/90d",
    ),
    AblationCell(
        "C_wf365_base",
        False,
        False,
        365,
        90,
        "730d",
        description="WFベースライン: 45特徴量, 正則化なし, WF365d/90d",
    ),
    # Step 2: +spread+reg (窓幅ごと)
    AblationCell(
        "D_wf90_full",
        True,
        True,
        90,
        90,
        "730d",
        description="+spread+reg: スプレッド3特徴量+正則化, WF90d/90d",
    ),
    AblationCell(
        "E_wf365_full",
        True,
        True,
        365,
        90,
        "730d",
        description="+spread+reg: スプレッド3特徴量+正則化, WF365d/90d",
    ),
    # Step 3: +multipair (窓幅ごと)
    AblationCell(
        "F_mp_wf90",
        True,
        True,
        90,
        90,
        "730d",
        multipair=True,
        description="+multipair: 全ペア統合1モデル+pair_id特徴量, WF90d/90d",
    ),
    AblationCell(
        "G_mp_wf365",
        True,
        True,
        365,
        90,
        "730d",
        multipair=True,
        description="+multipair: 全ペア統合1モデル+pair_id特徴量, WF365d/90d",
    ),
]


# ---------------------------------------------------------------------------
# データ読み込み
# ---------------------------------------------------------------------------
def _load_ba_candles(path: Path) -> pd.DataFrame:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    for col in ["bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Mid price (matches train_lgbm_models.py)
    df["open"] = (df["bid_o"] + df["ask_o"]) / 2.0
    df["high"] = (df["bid_h"] + df["ask_h"]) / 2.0
    df["low"] = (df["bid_l"] + df["ask_l"]) / 2.0
    df["close"] = (df["bid_c"] + df["ask_c"]) / 2.0
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    return df


# ---------------------------------------------------------------------------
# 特徴量構築
# ---------------------------------------------------------------------------
def _rsi(c: pd.Series, period: int = 14) -> pd.Series:
    delta = c.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()
    rs = gain / loss.replace(0.0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)


def _add_base_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]
    df["ema_12"] = c.ewm(span=12, adjust=False, min_periods=1).mean()
    df["ema_26"] = c.ewm(span=26, adjust=False, min_periods=1).mean()
    df["macd_line"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd_line"].ewm(span=9, adjust=False, min_periods=1).mean()
    df["macd_histogram"] = df["macd_line"] - df["macd_signal"]
    df["rsi_14"] = _rsi(c, 14)
    sma20 = c.rolling(20, min_periods=1).mean()
    std20 = c.rolling(20, min_periods=1).std(ddof=0).fillna(0.0)
    df["bb_middle"] = sma20
    df["bb_upper"] = sma20 + 2.0 * std20
    df["bb_lower"] = sma20 - 2.0 * std20
    bb_range = df["bb_upper"] - df["bb_lower"]
    df["bb_width"] = (bb_range / sma20.replace(0.0, np.nan)).fillna(0.0)
    df["bb_pct_b"] = ((c - df["bb_lower"]) / bb_range.replace(0.0, np.nan)).fillna(0.5)
    df["sma_20"] = sma20
    df["sma_50"] = c.rolling(50, min_periods=1).mean()
    # NEW BUG-B fix: shift(1).fillna(c) は先頭バー TR が「未来の自分」を見る形になるため fillna(c) を削除。
    # NEW BUG M1 fix: weekend gap 越えの shift(1) が前週末の close を pc に取る → TR 7.3× 膨張。
    #   bar の timestamp diff が > 2 分なら gap 跨ぎ → pc を NaN にして TR も NaN にする。
    pc = c.shift(1)
    ts_diff = df["timestamp"].diff()
    gap_mask = ts_diff > pd.Timedelta(minutes=2)
    pc = pc.where(~gap_mask)
    h, lo = df["high"], df["low"]
    tr = pd.concat([h - lo, (h - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14, min_periods=14).mean()
    return df


def _add_upper_tf_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    idx = pd.DatetimeIndex(df["timestamp"])
    rules = _UPPER_TF_RULES.get(_BAR_MINUTES, _UPPER_TF_RULES[1])
    for rule, pfx in rules:
        ohlc = (
            df.set_index(idx)[["open", "high", "low", "close"]]
            .resample(rule)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna(how="all")
        )
        c = ohlc["close"]
        ret1 = c.pct_change(1)
        ret3 = c.pct_change(3)
        vol = ret1.rolling(5, min_periods=2).std(ddof=0)
        rsi14 = _rsi(c, 14)
        sma5 = c.rolling(5, min_periods=1).mean()
        ma_slope = sma5.diff(1) / sma5.shift(1)
        bb_std = c.rolling(20, min_periods=1).std(ddof=0).fillna(0.0)
        bb_mid = c.rolling(20, min_periods=1).mean()
        bb_lo = bb_mid - 2 * bb_std
        bb_wi = (4 * bb_std).replace(0.0, float("nan"))
        bb_pct = (c - bb_lo) / bb_wi
        trend_slope = c.pct_change(5)
        trend_dir = np.sign(c.diff(3))
        raw = pd.DataFrame(
            {
                f"{pfx}_return_1": ret1,
                f"{pfx}_return_3": ret3,
                f"{pfx}_volatility": vol,
                f"{pfx}_rsi_14": rsi14,
                f"{pfx}_ma_slope": ma_slope,
                f"{pfx}_bb_pct_b": bb_pct,
                f"{pfx}_trend_slope": trend_slope,
                f"{pfx}_trend_dir": trend_dir,
            },
            index=ohlc.index,
        )
        # NEW BUG C1 fix: weekend/gap 跨ぎの bin で pct_change/diff/rolling が
        # 異常な値を出すので、bin 間の timestamp diff が rule の 1.5x を超える
        # 直後の bin は features を NaN にする (= 後続 5 bin まで影響伝播)
        rule_minutes = pd.Timedelta(rule).total_seconds() / 60.0
        bin_gap_minutes = ohlc.index.to_series().diff().dt.total_seconds() / 60.0
        is_post_gap = (bin_gap_minutes > rule_minutes * 1.5).fillna(False).values
        # 後続 5 bin (vol/trend_slope/diff(3)/diff(5) の影響範囲) も NaN
        post_gap_taint = pd.Series(is_post_gap, index=ohlc.index).rolling(5, min_periods=1).max().fillna(0).astype(bool)
        raw.loc[post_gap_taint.values, :] = np.nan

        aligned = raw.shift(1).reindex(idx, method="ffill")
        for col in aligned.columns:
            df[col] = aligned[col].values  # BUG-C fix: NaN 透過 → LightGBM の native handling
    return df


def _add_mtf_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    idx = pd.DatetimeIndex(df["timestamp"])
    df_ts = df.set_index(idx)

    def _tr(ohlc: pd.DataFrame) -> pd.Series:
        h, lo, pc = ohlc["high"], ohlc["low"], ohlc["close"].shift(1)
        return pd.concat([(h - lo), (h - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)

    # NEW BUG C2/C3 fix: H4/D1 で partial bin を除外、 ATR は min_periods=14 統一
    # Filter helper: bin に M1 が rule の 50% 以上ないと partial 扱いで drop
    def _filter_partial(ohlc, rule, min_ratio=0.5):
        rule_minutes = pd.Timedelta(rule).total_seconds() / 60.0
        full_count = int(rule_minutes / max(_BAR_MINUTES, 1))
        threshold = max(1, int(full_count * min_ratio))
        counts = df_ts["close"].resample(rule).count()
        valid_idx = counts[counts >= threshold].index
        return ohlc.loc[ohlc.index.intersection(valid_idx)]

    h4 = (
        df_ts[["open", "high", "low", "close"]]
        .resample("4h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna(how="all")
    )
    h4 = _filter_partial(h4, "4h", min_ratio=0.5)  # 4h で 50%(120 M1) 未満は drop
    h4_raw = pd.DataFrame(
        {"h4_atr_14": _tr(h4).rolling(14, min_periods=14).mean()},  # min_periods=14
        index=h4.index,
    )
    df["h4_atr_14"] = h4_raw.shift(1).reindex(idx, method="ffill")["h4_atr_14"].values

    d1 = (
        df_ts[["open", "high", "low", "close"]]
        .resample("1D")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna(how="all")
    )
    d1 = _filter_partial(d1, "1D", min_ratio=0.25)  # 1D で 25% (= 6h = 360 M1) 未満は Sunday partial で drop
    d1_c = d1["close"]
    d1_raw = pd.DataFrame(
        {
            "d1_return_3": d1_c.pct_change(3),
            "d1_range_pct": (d1["high"] - d1["low"]) / d1_c.replace(0.0, float("nan")),
            "d1_atr_14": _tr(d1).rolling(14, min_periods=14).mean(),  # min_periods=14
        },
        index=d1.index,
    )
    d1_aligned = d1_raw.shift(1).reindex(idx, method="ffill")
    for col in d1_raw.columns:
        df[col] = d1_aligned[col].values

    w1 = (
        df_ts[["open", "high", "low", "close"]]
        .resample("1W")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna(how="all")
    )
    w1 = _filter_partial(w1, "1W", min_ratio=0.5)  # 1W で 50% (= 3600 M1 ≈ 2.5 trading days) 未満は drop
    w1_c = w1["close"]
    w1_raw = pd.DataFrame(
        {
            "w1_return_1": w1_c.pct_change(1),
            "w1_range_pct": (w1["high"] - w1["low"]) / w1_c.replace(0.0, float("nan")),
        },
        index=w1.index,
    )
    w1_aligned = w1_raw.shift(1).reindex(idx, method="ffill")
    for col in w1_raw.columns:
        df[col] = w1_aligned[col].values  # BUG-C fix

    return df


def _add_spread_features(df: pd.DataFrame, pip: float) -> pd.DataFrame:
    """スプレッド3特徴量 (Phase 9.15/v26 spread bundle)."""
    df = df.copy()
    if "ask_o" in df.columns and "bid_o" in df.columns:
        spread = (df["ask_o"] - df["bid_o"]) / pip
    else:
        spread = pd.Series(np.nan, index=df.index)
    df["spread_now_pip"] = spread
    spread_ma20 = spread.rolling(20, min_periods=5).mean()
    df["spread_ma_ratio_20"] = (
        (spread / spread_ma20.replace(0.0, np.nan))
        .replace([np.inf, -np.inf], np.nan)
    )
    spread_mean50 = spread.rolling(50, min_periods=10).mean()
    spread_std50 = spread.rolling(50, min_periods=10).std(ddof=0)
    df["spread_zscore_50"] = (
        ((spread - spread_mean50) / spread_std50.replace(0.0, np.nan))
        .replace([np.inf, -np.inf], np.nan)
    )
    return df


def _add_labels(df: pd.DataFrame, instrument: str) -> pd.DataFrame:
    """B-2 bid/ask ATR triple-barrier ラベル (ベクトル化) + SL>spread*_FILTER_K."""
    if "ask_o" not in df.columns or "bid_o" not in df.columns:
        raise ValueError(f"{instrument}: BA candles required")
    n = len(df)
    bid_h = df["bid_h"].to_numpy(dtype=np.float64)
    bid_l = df["bid_l"].to_numpy(dtype=np.float64)
    ask_h = df["ask_h"].to_numpy(dtype=np.float64)
    ask_l = df["ask_l"].to_numpy(dtype=np.float64)
    ask_o = df["ask_o"].to_numpy(dtype=np.float64)
    bid_o = df["bid_o"].to_numpy(dtype=np.float64)
    bid_c = df["bid_c"].to_numpy(dtype=np.float64) if "bid_c" in df.columns else df["close"].to_numpy(dtype=np.float64)
    ask_c = df["ask_c"].to_numpy(dtype=np.float64) if "ask_c" in df.columns else df["close"].to_numpy(dtype=np.float64)
    atrs  = df["atr_14"].to_numpy(dtype=np.float64)

    # NEW BUG #1 fix: n_eff = n - _HORIZON にすることで末尾バーまでラベル付与可能
    n_eff = n - _HORIZON
    if n_eff <= 0:
        df = df.copy()
        df[_LABEL_COLUMN] = [None] * n
        return df

    atr_view        = atrs[:n_eff]
    entry_long_arr  = ask_o[1: n_eff + 1]
    entry_short_arr = bid_o[1: n_eff + 1]
    spread_entry    = entry_long_arr - entry_short_arr

    sl_arr = _SL_MULT * atr_view
    tp_arr = _TP_MULT * atr_view

    valid = (
        np.isfinite(atr_view)
        & (atr_view > 0)
        & np.isfinite(entry_long_arr)
        & np.isfinite(entry_short_arr)
        & (sl_arr > spread_entry * _FILTER_K)
    )

    bid_h_win = np.lib.stride_tricks.sliding_window_view(bid_h[1:], _HORIZON)[:n_eff]
    bid_l_win = np.lib.stride_tricks.sliding_window_view(bid_l[1:], _HORIZON)[:n_eff]
    ask_h_win = np.lib.stride_tricks.sliding_window_view(ask_h[1:], _HORIZON)[:n_eff]
    ask_l_win = np.lib.stride_tricks.sliding_window_view(ask_l[1:], _HORIZON)[:n_eff]

    # NEW BUG #2 fix: window 内に NaN があると比較が False を返しヒット見逃しが発生 → finite 判定で valid から除外
    win_finite = (
        np.isfinite(bid_h_win).all(axis=1)
        & np.isfinite(bid_l_win).all(axis=1)
        & np.isfinite(ask_h_win).all(axis=1)
        & np.isfinite(ask_l_win).all(axis=1)
    )
    valid = valid & win_finite

    ltp_mask = bid_h_win >= (entry_long_arr  + tp_arr).reshape(-1, 1)
    lsl_mask = bid_l_win <= (entry_long_arr  - sl_arr).reshape(-1, 1)
    stp_mask = ask_l_win <= (entry_short_arr - tp_arr).reshape(-1, 1)
    ssl_mask = ask_h_win >= (entry_short_arr + sl_arr).reshape(-1, 1)

    def _fv(mask: np.ndarray) -> np.ndarray:
        has = mask.any(axis=1)
        idx = mask.argmax(axis=1)
        return np.where(has, idx, -1)

    li = _fv(ltp_mask); ls = _fv(lsl_mask)
    si = _fv(stp_mask); ss = _fv(ssl_mask)

    lc = (li >= 0) & ((ls < 0) | (li < ls))
    sc = (si >= 0) & ((ss < 0) | (si < ss))

    # Multinomial label (training target) — 4 バリア中の最先着で勝ち方向を決める
    inner = np.zeros(n_eff, dtype=np.int64)
    inner[lc & ~sc] = 1
    inner[sc & ~lc] = -1
    both = lc & sc
    inner[both & (li <= si)] = 1
    inner[both & (li >  si)] = -1

    # Direction-specific labels (simulation PnL 用) — long/short それぞれの barrier 単独で評価
    long_inner = np.zeros(n_eff, dtype=np.int64)
    long_tp_first = (li >= 0) & ((ls < 0) | (li <  ls))
    long_sl_first = (ls >= 0) & ((li < 0) | (ls <  li)) & ~long_tp_first
    long_inner[long_tp_first] = 1
    long_inner[long_sl_first] = -1
    # else 0 (timeout — neither long-side barrier completed in horizon)

    short_inner = np.zeros(n_eff, dtype=np.int64)
    short_tp_first = (si >= 0) & ((ss < 0) | (si <  ss))
    short_sl_first = (ss >= 0) & ((si < 0) | (ss <  si)) & ~short_tp_first
    short_inner[short_tp_first] = 1
    short_inner[short_sl_first] = -1

    # NEW BUG #H fix: timeout 時の真 PnL を計算して保存
    # Long timeout: bid_c[i+_HORIZON] - ask_o[i+1] (in pip)
    # Short timeout: bid_o[i+1] - ask_c[i+_HORIZON] (in pip)
    pip = _PIP_SIZE.get(instrument, 0.0001)
    exit_bid_c = bid_c[_HORIZON: n_eff + _HORIZON]   # 長さ n_eff
    exit_ask_c = ask_c[_HORIZON: n_eff + _HORIZON]
    timeout_pnl_long_pip  = (exit_bid_c - entry_long_arr)  / pip
    timeout_pnl_short_pip = (entry_short_arr - exit_ask_c) / pip

    labels:  list[int | None]   = [None] * n
    long_l:  list[int | None]   = [None] * n
    short_l: list[int | None]   = [None] * n
    to_long: list[float | None] = [None] * n
    to_shrt: list[float | None] = [None] * n
    for i in np.flatnonzero(valid):
        labels[i]  = int(inner[i])
        long_l[i]  = int(long_inner[i])
        short_l[i] = int(short_inner[i])
        to_long[i] = float(timeout_pnl_long_pip[i])
        to_shrt[i] = float(timeout_pnl_short_pip[i])
    df = df.copy()
    df[_LABEL_COLUMN] = labels
    df[_LABEL_LONG]   = long_l
    df[_LABEL_SHORT]  = short_l
    df[_TO_PNL_LONG]  = to_long
    df[_TO_PNL_SHORT] = to_shrt
    return df


def _build_pair_df(df: pd.DataFrame, instrument: str, spread_features: bool) -> pd.DataFrame:
    pip = _PIP_SIZE.get(instrument, 0.0001)
    df = _add_base_features(df)
    df = _add_upper_tf_features(df)
    df = _add_mtf_features(df)
    if spread_features:
        df = _add_spread_features(df, pip)
    df = _add_labels(df, instrument)
    return df


# ---------------------------------------------------------------------------
# フォールド生成
# ---------------------------------------------------------------------------
def _generate_folds(
    t_min: pd.Timestamp,
    t_max: pd.Timestamp,
    train_days: int,
    step_days: int,
) -> list[dict]:
    """ウォークフォワードフォールドのリストを返す."""
    folds = []
    train_td = pd.Timedelta(days=train_days)
    step_td = pd.Timedelta(days=step_days)
    test_start = t_min + train_td
    while test_start < t_max:
        test_end = min(test_start + step_td, t_max)
        train_start = test_start - train_td
        folds.append(
            {
                "train_start": train_start,
                "train_end": test_start,
                "test_start": test_start,
                "test_end": test_end,
            }
        )
        test_start += step_td
    return folds


# ---------------------------------------------------------------------------
# モデル訓練
# ---------------------------------------------------------------------------
def _train_models(
    pair_dfs: dict[str, pd.DataFrame],
    feature_cols: list[str],
    train_mask: dict[str, pd.Series],
    regularize: bool,
    multipair: bool = False,
    fold_seed: int = 42,
) -> dict:
    """学習モード:
      _TRAINING_MODE='multi'    → 1 モデル/ペア (label_tb)
      _TRAINING_MODE='direction'→ 2 モデル/ペア (label_long, label_short)
    """
    base = _LGBM_REG_PARAMS if regularize else _LGBM_BASE_PARAMS
    params = {**base, "n_estimators": _N_ESTIMATORS}
    if _CUSTOM_CLASS_WEIGHT is not None:
        params["class_weight"] = _CUSTOM_CLASS_WEIGHT  # custom dict
    elif not _USE_CLASS_WEIGHT:
        params["class_weight"] = None  # 無効化
    # else: keep "balanced" from base

    def _fit(x, y):
        m = lgb.LGBMClassifier(**params); m.fit(x, y); return m

    if multipair:
        _mp_cap = 25_000
        frames: list[pd.DataFrame] = []
        for pair, df in pair_dfs.items():
            tr = df[train_mask[pair]].dropna(subset=[_LABEL_COLUMN]).copy()
            if len(tr) < 50:
                continue
            if len(tr) > _mp_cap:
                tr = tr.sample(n=_mp_cap, random_state=fold_seed)
            tr["pair_id"] = _PAIR_IDX.get(pair, 0)
            frames.append(tr)
        if not frames:
            return {}
        all_tr = pd.concat(frames, ignore_index=True)
        mp_feat = feature_cols + ["pair_id"]
        x = all_tr[mp_feat].values  # BUG-C: LightGBM が NaN を native に扱う
        if _TRAINING_MODE == "multi":
            y = all_tr[_LABEL_COLUMN].astype(int).map(_LABEL_ENCODE).to_numpy()
            return {_MULTIPAIR_KEY: {"multi": _fit(x, y)}}
        else:
            y_long  = all_tr[_LABEL_LONG ].astype(int).map(_LABEL_ENCODE).to_numpy()
            y_short = all_tr[_LABEL_SHORT].astype(int).map(_LABEL_ENCODE).to_numpy()
            return {_MULTIPAIR_KEY: {"long": _fit(x, y_long), "short": _fit(x, y_short)}}

    models: dict[str, dict] = {}
    for pair, df in pair_dfs.items():
        mask = train_mask[pair]
        tr = df[mask].dropna(subset=[_LABEL_COLUMN])
        if len(tr) < 200:
            continue
        x = tr[feature_cols].values  # BUG-C
        if _TRAINING_MODE == "multi":
            y = tr[_LABEL_COLUMN].astype(int).map(_LABEL_ENCODE).to_numpy()
            models[pair] = {"multi": _fit(x, y)}
        else:
            y_long  = tr[_LABEL_LONG ].astype(int).map(_LABEL_ENCODE).to_numpy()
            y_short = tr[_LABEL_SHORT].astype(int).map(_LABEL_ENCODE).to_numpy()
            models[pair] = {"long": _fit(x, y_long), "short": _fit(x, y_short)}
    return models


# ---------------------------------------------------------------------------
# 逐次シミュレーション (ナンピン対策 + Top-K + 通貨多様化)
# ---------------------------------------------------------------------------
def _direction_proba(model: lgb.LGBMClassifier, feat: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (p_TP, p_SL, p_TO) using model.classes_ to resolve column order.
    Encoded labels: 0=SL(-1), 1=TO(0), 2=TP(+1)."""
    proba = model.predict_proba(feat)
    cls = list(int(c) for c in model.classes_)
    col_TP = cls.index(2) if 2 in cls else None
    col_SL = cls.index(0) if 0 in cls else None
    col_TO = cls.index(1) if 1 in cls else None
    p_TP = proba[:, col_TP] if col_TP is not None else np.zeros(len(proba))
    p_SL = proba[:, col_SL] if col_SL is not None else np.zeros(len(proba))
    p_TO = proba[:, col_TO] if col_TO is not None else np.zeros(len(proba))
    return p_TP, p_SL, p_TO


def _multi_proba(model: lgb.LGBMClassifier, feat: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (p_long, p_short, p_timeout) for multinomial model.
    Encoded: -1→0 (short), 0→1 (timeout), +1→2 (long)."""
    proba = model.predict_proba(feat)
    cls = list(int(c) for c in model.classes_)
    col_long = cls.index(2) if 2 in cls else None
    col_short = cls.index(0) if 0 in cls else None
    col_to = cls.index(1) if 1 in cls else None
    p_long  = proba[:, col_long]  if col_long  is not None else np.zeros(len(proba))
    p_short = proba[:, col_short] if col_short is not None else np.zeros(len(proba))
    p_to    = proba[:, col_to]    if col_to    is not None else np.zeros(len(proba))
    return p_long, p_short, p_to


def _simulate(
    pair_dfs: dict[str, pd.DataFrame],
    models: dict,
    feature_cols: list[str],
    test_mask: dict[str, pd.Series],
    multipair: bool = False,
    open_until_ts: dict[str, pd.Timestamp] | None = None,  # NEW BUG #F: 持ち越しサポート
) -> tuple[list[float], dict[str, pd.Timestamp]]:
    """逐次シミュレーション。training_mode に従い multi / direction を切替。
    NEW BUG #E fix: anti-pyramiding を timestamp ベースに変更
    NEW BUG #F fix: open_until_ts を fold 間で持ち越し可能に
    NEW BUG #H fix: timeout PnL に真 close-at-horizon を使用
    """

    is_mp = multipair and _MULTIPAIR_KEY in models
    single_models = models[_MULTIPAIR_KEY] if is_mp else None
    mp_feat = feature_cols + ["pair_id"] if is_mp else feature_cols
    if open_until_ts is None:
        open_until_ts = {}
    # Multi-TF 対応: HORIZON × bar 分（M1=1分, M5=5分, M15=15分）
    horizon_td = pd.Timedelta(minutes=_HORIZON * _BAR_MINUTES)

    pair_signals: dict[str, dict] = {}
    for pair, df in pair_dfs.items():
        if is_mp:
            pair_models = single_models
        elif pair not in models:
            continue
        else:
            pair_models = models[pair]
        # NEW BUG #A fix: dropna+reset_index 後の sp[i+1] は元 df で連続でない可能性あり。
        # 元 df の row+1 を引きにいくため、dropna 前の original index を保持する
        labeled = df[test_mask[pair]].dropna(subset=[_LABEL_COLUMN]).copy()
        if len(labeled) == 0:
            continue
        orig_idx = labeled.index.to_numpy()
        te = labeled.reset_index(drop=True)
        if is_mp:
            te["pair_id"] = _PAIR_IDX.get(pair, 0)
        feat = te[mp_feat].values  # BUG-C
        pip = _PIP_SIZE.get(pair, 0.0001)
        if "ask_o" in df.columns and "bid_o" in df.columns:
            ask_full = df["ask_o"].to_numpy()
            bid_full = df["bid_o"].to_numpy()
            n_full   = len(df)
            spread_arr = np.array([
                (ask_full[oi] - bid_full[oi]) / pip if 0 <= oi < n_full else np.nan
                for oi in orig_idx
            ], dtype=float)
            # entry スプレッド = bar i+1 の値。元 df の orig_idx[i] + 1 行を引く
            spread_entry_arr = np.array([
                (ask_full[oi+1] - bid_full[oi+1]) / pip if oi + 1 < n_full else np.nan
                for oi in orig_idx
            ], dtype=float)
        else:
            spread_arr       = np.full(len(te), np.nan)
            spread_entry_arr = np.full(len(te), np.nan)

        sig = {
            "timestamps":     te["timestamp"].values,
            "labels_long":    te[_LABEL_LONG].values.astype(float),
            "labels_short":   te[_LABEL_SHORT].values.astype(float),
            "atrs":           te["atr_14"].values.astype(float),
            "spread_entries": spread_entry_arr,
            "to_long":        te[_TO_PNL_LONG ].values.astype(float),  # NEW BUG #H
            "to_short":       te[_TO_PNL_SHORT].values.astype(float),
            "pip":            pip,
        }
        if _TRAINING_MODE == "multi":
            p_long, p_short, p_to = _multi_proba(pair_models["multi"], feat)
            sig.update({"p_long_multi": p_long, "p_short_multi": p_short, "p_to_multi": p_to})
        else:
            p_l_TP, p_l_SL, p_l_TO = _direction_proba(pair_models["long"],  feat)
            p_s_TP, p_s_SL, p_s_TO = _direction_proba(pair_models["short"], feat)
            sig.update({
                "p_long_TP":  p_l_TP, "p_long_SL":  p_l_SL, "p_long_TO":  p_l_TO,
                "p_short_TP": p_s_TP, "p_short_SL": p_s_SL, "p_short_TO": p_s_TO,
            })
        pair_signals[pair] = sig

    bar_data: dict = {}
    for pair, sig in pair_signals.items():
        for i, ts in enumerate(sig["timestamps"]):
            bar_data.setdefault(ts, []).append((pair, i))

    pnl_list: list[float] = []

    for ts in sorted(bar_data.keys()):
        ts_now = pd.Timestamp(ts)
        candidates = []
        for pair, bar_idx in bar_data[ts]:
            # NEW BUG #E/#F fix: timestamp ベース anti-pyramiding
            if open_until_ts.get(pair, pd.Timestamp.min) > ts_now:
                continue
            sig = pair_signals[pair]
            atr = float(sig["atrs"][bar_idx])
            spread_entry = float(sig["spread_entries"][bar_idx])
            l_long  = sig["labels_long"][bar_idx]
            l_short = sig["labels_short"][bar_idx]
            if np.isnan(spread_entry) or np.isnan(atr) or atr <= 0.0:
                continue
            if np.isnan(l_long) or np.isnan(l_short):
                continue
            pip = sig["pip"]
            tp_pip = _TP_MULT * atr / pip
            sl_pip = _SL_MULT * atr / pip

            if _TRAINING_MODE == "multi":
                p_long  = float(sig["p_long_multi"][bar_idx])
                p_short = float(sig["p_short_multi"][bar_idx])
                p_to    = float(sig["p_to_multi"][bar_idx])
                # EV: p_long*tp - SL_FACTOR*p_short*sl - p_to*spread
                # SL_FACTOR=1.0 が旧 v2 の素朴な式 (tp/sl のみ、spread は別 gate で扱う)
                # SL_FACTOR>1 で p_short を実 SL レート ≒ 4×p_short_multi に補正
                ev_long  = p_long  * tp_pip - _EV_SL_FACTOR * p_short * sl_pip - p_to * spread_entry
                ev_short = p_short * tp_pip - _EV_SL_FACTOR * p_long  * sl_pip - p_to * spread_entry
                if p_long >= p_short and p_long >= _CONF_THR and ev_long > 0:
                    direction = "long";  conf = p_long;  pnl_label = int(l_long)
                elif p_short > p_long and p_short >= _CONF_THR and ev_short > 0:
                    direction = "short"; conf = p_short; pnl_label = int(l_short)
                else:
                    continue
            else:
                p_l_TP = float(sig["p_long_TP"][bar_idx])
                p_l_SL = float(sig["p_long_SL"][bar_idx])
                p_l_TO = float(sig["p_long_TO"][bar_idx])
                p_s_TP = float(sig["p_short_TP"][bar_idx])
                p_s_SL = float(sig["p_short_SL"][bar_idx])
                p_s_TO = float(sig["p_short_TO"][bar_idx])
                ev_long  = p_l_TP * tp_pip - p_l_SL * sl_pip - p_l_TO * spread_entry
                ev_short = p_s_TP * tp_pip - p_s_SL * sl_pip - p_s_TO * spread_entry
                if ev_long >= ev_short and ev_long > 0 and p_l_TP >= _CONF_THR:
                    direction = "long";  conf = p_l_TP;  pnl_label = int(l_long)
                elif ev_short > ev_long and ev_short > 0 and p_s_TP >= _CONF_THR:
                    direction = "short"; conf = p_s_TP; pnl_label = int(l_short)
                else:
                    continue

            # NEW BUG #H: 真 timeout PnL を candidate に含める
            to_pnl = float(sig["to_long"][bar_idx]) if direction == "long" else float(sig["to_short"][bar_idx])
            candidates.append(
                {
                    "pair":         pair,
                    "bar_idx":      bar_idx,
                    "direction":    direction,
                    "conf":         conf,
                    "atr":          atr,
                    "pip":          pip,
                    "pnl_label":    pnl_label,
                    "spread_entry": spread_entry,
                    "to_pnl":       to_pnl,
                }
            )

        if not candidates:
            continue

        candidates.sort(key=lambda x: -x["conf"])

        # --- Top-K: 通貨多様化 + ナンピン対策 ---
        used_ccy: set[str] = set()
        picks: list[dict] = []
        for cand in candidates:
            pair = cand["pair"]
            base, quote = pair.split("_")
            if base in used_ccy or quote in used_ccy:
                continue
            picks.append(cand)
            used_ccy.add(base); used_ccy.add(quote)
            # NEW BUG #E/#F fix: timestamp ベースで再エントリー禁止 (fold をまたいで持続)
            open_until_ts[pair] = ts_now + horizon_td
            if len(picks) >= _TOP_K:
                break

        # --- PnL 計算: direction-specific label で +tp / -sl / 真 timeout_pnl ---
        for pick in picks:
            tp_pip = _TP_MULT * pick["atr"] / pick["pip"]
            sl_pip = _SL_MULT * pick["atr"] / pick["pip"]
            pl     = pick["pnl_label"]
            if pl == 1:
                pnl_list.append(tp_pip)
            elif pl == -1:
                pnl_list.append(-sl_pip)
            else:
                # NEW BUG #H fix: timeout 時は真 close-at-horizon の PnL を使用
                to = pick["to_pnl"]
                pnl_list.append(to if np.isfinite(to) else -pick["spread_entry"])

    return pnl_list, open_until_ts


# ---------------------------------------------------------------------------
# 統計
# ---------------------------------------------------------------------------
def _stats(pnls: list[float], n_test_bars: int = 0) -> dict:
    if not pnls:
        return {
            "n": 0,
            "hit_pct": 0.0,
            "pnl": 0.0,
            "sharpe": 0.0,
            "maxdd": 0.0,
        }
    arr = np.array(pnls, dtype=np.float64)
    n = len(arr)
    hit = float(np.sum(arr > 0)) / n * 100.0
    total = float(np.sum(arr))

    # Per-trade 情報比 (v26 と同スケール: mean/std, ddof=0, 年率換算なし)
    mu = float(np.mean(arr))
    sd = float(np.std(arr, ddof=0)) if n > 1 else 1e-9
    sharpe = mu / sd if sd > 0 else 0.0

    cum = np.cumsum(arr)
    peak = np.maximum.accumulate(cum)
    maxdd = float(np.min(cum - peak))
    return {
        "n": n,
        "hit_pct": hit,
        "pnl": total,
        "sharpe": sharpe,
        "maxdd": maxdd,
    }


# ---------------------------------------------------------------------------
# セル実行
# ---------------------------------------------------------------------------
def _run_cell(
    cell: AblationCell,
    pair_dfs: dict[str, pd.DataFrame],
    pairs: list[str],
) -> dict:
    # Dynamic feat_cols based on current base TF
    feat_cols = _get_base_feat_for_tf(_BAR_MINUTES)
    if cell.spread_features:
        feat_cols = feat_cols + list(_SPREAD_FEAT)

    all_pnls: list[float] = []

    # NEW BUG #F fix: open_until_ts を fold をまたいで持続させる
    open_until_ts: dict[str, pd.Timestamp] = {}

    def _purge_tail_bars(mask: pd.Series, n_purge: int) -> pd.Series:
        """NEW BUG #D fix: bar 数ベースで mask 末尾を除外"""
        idx_true = mask[mask].index
        if len(idx_true) <= n_purge:
            return pd.Series(False, index=mask.index)
        new_mask = pd.Series(False, index=mask.index)
        new_mask.loc[idx_true[:-n_purge]] = True
        return new_mask

    if cell.train_days == 0:
        # 固定 80/20 分割 — purge: 末尾 _HORIZON+1 行を train から除外
        train_mask: dict[str, pd.Series] = {}
        test_mask: dict[str, pd.Series] = {}
        for pair in pairs:
            df = pair_dfs[pair]
            n = len(df)
            n_train = int(n * 0.80)
            n_purge = max(0, n_train - _HORIZON - 1)  # purge horizon+1 from train tail
            m_tr = pd.Series(False, index=df.index)
            m_tr.iloc[:n_purge] = True
            m_te = pd.Series(False, index=df.index)
            m_te.iloc[n_train:] = True
            train_mask[pair] = m_tr
            test_mask[pair] = m_te

        models = _train_models(pair_dfs, feat_cols, train_mask, cell.regularize, cell.multipair)
        all_pnls, open_until_ts = _simulate(
            pair_dfs, models, feat_cols, test_mask, cell.multipair, open_until_ts=open_until_ts
        )
    else:
        # ウォークフォワード
        t_min = min(pair_dfs[p]["timestamp"].min() for p in pairs if p in pair_dfs)
        t_max = max(pair_dfs[p]["timestamp"].max() for p in pairs if p in pair_dfs)
        # CLI override (train_days/step_days) — Multi-TF 用
        train_days_used = _TRAIN_DAYS_OVERRIDE if _TRAIN_DAYS_OVERRIDE > 0 else cell.train_days
        step_days_used  = _STEP_DAYS_OVERRIDE  if _STEP_DAYS_OVERRIDE  > 0 else cell.step_days
        folds = _generate_folds(t_min, t_max, train_days_used, step_days_used)
        print(f"    {len(folds)} folds  (purge={_HORIZON}bars)", flush=True)

        prev_train_end: pd.Timestamp | None = None
        models: dict[str, lgb.LGBMClassifier] = {}

        for fi, fold in enumerate(folds, 1):
            tr_s, tr_e = fold["train_start"], fold["train_end"]
            te_s, te_e = fold["test_start"], fold["test_end"]

            # 訓練データが変わった場合のみ再訓練
            if tr_e != prev_train_end:
                train_mask = {}
                # 正しい purge: bar 数ベース (週末跨ぎでも leak 無し)
                for pair in pairs:
                    ts = pair_dfs[pair]["timestamp"]
                    m = (ts >= tr_s) & (ts < tr_e)
                    train_mask[pair] = _purge_tail_bars(m, _HORIZON + 1)
                models = _train_models(
                    pair_dfs, feat_cols, train_mask, cell.regularize, cell.multipair,
                    fold_seed=fi,
                )
                prev_train_end = tr_e
                print(
                    f"    fold {fi:3d}/{len(folds)}"
                    f" train [{tr_s.date()}→{tr_e.date()}]"
                    f" test [{te_s.date()}→{te_e.date()}]",
                    flush=True,
                )

            test_mask = {}
            for pair in pairs:
                ts = pair_dfs[pair]["timestamp"]
                m = (ts >= te_s) & (ts < te_e)
                test_mask[pair] = m

            fold_pnls, open_until_ts = _simulate(
                pair_dfs, models, feat_cols, test_mask, cell.multipair,
                open_until_ts=open_until_ts,
            )
            all_pnls.extend(fold_pnls)

    return _stats(all_pnls)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--pairs", nargs="*", default=_ALL_PAIRS)
    parser.add_argument(
        "--cells",
        nargs="*",
        default=None,
        help="実行するセル名 (例: A_baseline F_wf90d). 省略時は全セル.",
    )
    parser.add_argument("--tp-mult",   type=float, default=None, help="TP multiplier (default: _TP_MULT)")
    parser.add_argument("--sl-mult",   type=float, default=None, help="SL multiplier (default: _SL_MULT)")
    parser.add_argument("--horizon",   type=int,   default=None, help="Triple-barrier horizon bars (default: _HORIZON)")
    parser.add_argument("--filter-k",  type=float, default=None, help="SL > spread * k filter (default: _FILTER_K)")
    parser.add_argument("--conf-thr",  type=float, default=None, help="Confidence threshold (default: _CONF_THR)")
    parser.add_argument("--training-mode", choices=["multi", "direction"], default="direction",
                        help="multi: label_tb 1モデル / direction: label_long+label_short の2モデル")
    parser.add_argument("--no-class-weight", action="store_true", help="LGBM class_weight='balanced' を外す")
    parser.add_argument("--ev-sl-factor", type=float, default=1.0,
                        help="multi モード EV 式の p_short スケーリング係数 (default 1.0; 4.0 で実損失レート補正)")
    parser.add_argument("--timeframe", default="M1", choices=["M1", "M5", "M15"],
                        help="ベース時間枠. ファイル名 candles_{pair}_{TF}_{suffix}_BA.jsonl を読む")
    parser.add_argument("--data-suffix-override", default=None,
                        help="セル定義の data_suffix を上書き (例: '1095d')")
    parser.add_argument("--train-days-override", type=int, default=None,
                        help="セル定義の train_days を上書き (例: 1095)")
    parser.add_argument("--step-days-override", type=int, default=None,
                        help="セル定義の step_days を上書き")
    args = parser.parse_args()

    # CLI 引数でグローバル定数を上書き
    global _TP_MULT, _SL_MULT, _HORIZON, _FILTER_K, _CONF_THR
    global _TRAINING_MODE, _USE_CLASS_WEIGHT, _EV_SL_FACTOR, _TRAIN_DAYS_OVERRIDE, _STEP_DAYS_OVERRIDE
    if args.tp_mult  is not None: _TP_MULT  = args.tp_mult
    if args.sl_mult  is not None: _SL_MULT  = args.sl_mult
    if args.conf_thr is not None: _CONF_THR = args.conf_thr
    if args.horizon  is not None: _HORIZON  = args.horizon
    if args.filter_k is not None: _FILTER_K = args.filter_k
    _TRAINING_MODE    = args.training_mode
    _USE_CLASS_WEIGHT = not args.no_class_weight
    _EV_SL_FACTOR     = args.ev_sl_factor
    global _BAR_MINUTES
    _BAR_MINUTES = {"M1": 1, "M5": 5, "M15": 15}[args.timeframe]
    _TRAIN_DAYS_OVERRIDE = args.train_days_override or 0
    _STEP_DAYS_OVERRIDE  = args.step_days_override  or 0
    print(f"[VARIANT] training_mode={_TRAINING_MODE}  class_weight={'balanced' if _USE_CLASS_WEIGHT else 'None'}  ev_sl_factor={_EV_SL_FACTOR}  timeframe={args.timeframe}({_BAR_MINUTES}min)", flush=True)

    # ファイルリダイレクト時もバッファなしで即時書き込み
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    import gc

    data_dir = Path(args.data_dir)
    target_cells = [c for c in _CELLS if c.name in args.cells] if args.cells else _CELLS

    # セルを (suffix, spread) キーでグループ化し、同キーのセルは同一特徴量を共有
    # グループ間では明示的に解放してメモリを節約
    from itertools import groupby as _groupby

    suffix_override = args.data_suffix_override
    def _feat_key(c: AblationCell) -> tuple[str, bool]:
        suffix = suffix_override if suffix_override is not None else c.data_suffix
        return (suffix, c.spread_features)

    cell_groups: list[tuple[tuple[str, bool], list[AblationCell]]] = []
    for key, grp in _groupby(target_cells, key=_feat_key):
        cell_groups.append((key, list(grp)))

    results: list[tuple[AblationCell, dict]] = []

    for group_idx, (feat_key, cells_in_group) in enumerate(cell_groups):
        suffix, with_spread = feat_key
        print(
            f"\n=== Feature group {group_idx + 1}/{len(cell_groups)}"
            f" [{suffix} spread={with_spread}] ===",
            flush=True,
        )

        # --- データ読み込み ---
        print("Loading candle data ...", flush=True)
        raw_dfs: dict[str, pd.DataFrame] = {}
        for pair in args.pairs:
            fname = f"candles_{pair}_{args.timeframe}_{suffix}_BA.jsonl"
            path = data_dir / fname
            if not path.exists():
                print(f"  SKIP {pair} ({suffix}): not found", file=sys.stderr)
                continue
            raw_dfs[pair] = _load_ba_candles(path)
        print(f"  loaded {len(raw_dfs)} pairs", flush=True)

        # --- 特徴量構築 ---
        print("Building features ...", flush=True)
        pair_dfs: dict[str, pd.DataFrame] = {}
        for pair, df in raw_dfs.items():
            print(f"  {pair} [{suffix}] spread={with_spread}", flush=True)
            try:
                pair_dfs[pair] = _build_pair_df(df, pair, with_spread)
            except Exception as exc:
                print(f"  ERROR {pair}: {exc}", file=sys.stderr)

        # 生データはもう不要 — 解放
        del raw_dfs
        gc.collect()

        pairs = [p for p in args.pairs if p in pair_dfs]

        # --- このグループ内の各セルを実行 ---
        for cell in cells_in_group:
            print(f"\n[{cell.name}] {cell.description}", flush=True)
            try:
                res = _run_cell(cell, pair_dfs, pairs)
            except Exception as exc:
                print(f"  ERROR: {exc}", file=sys.stderr)
                res = {"n": 0, "hit_pct": 0.0, "pnl": 0.0, "sharpe": 0.0, "maxdd": 0.0}
            results.append((cell, res))
            print(
                f"  n={res['n']:,}  hit={res['hit_pct']:.1f}%"
                f"  PnL={res['pnl']:,.0f}pip"
                f"  Sharpe={res['sharpe']:.4f}"
                f"  MaxDD={res['maxdd']:.1f}pip",
                flush=True,
            )

        # グループ終了 — 特徴量を解放してから次グループへ
        del pair_dfs
        gc.collect()
        print(f"  [group {group_idx + 1} done - memory released]", flush=True)

    # 結果テーブル — A_baseline の実測値を基準とする
    baseline_res = next((r for c, r in results if c.name == "A_baseline"), None)
    baseline_sharpe = baseline_res["sharpe"] if baseline_res else float("nan")
    baseline_pnl = baseline_res["pnl"] if baseline_res else float("nan")

    sep = "-" * 105
    header = (
        f"{'Cell':<16} {'Data':>5} {'N':>7} {'Hit%':>6} {'PnL(pip)':>10}"
        f" {'Sharpe':>8} {'MaxDD':>8} {'dSharpe':>9} {'PnL比':>7}  Description"
    )
    print(f"\n{'=' * 105}")
    print("ABLATION RESULTS (EV-gate=ON, anti-pyramiding=ON, Top-K=3, conf>=0.40)")
    print(
        f"  Baseline: A_baseline (fixed 80/20, 365d)"
        f" => Sharpe={baseline_sharpe:.4f}  PnL={baseline_pnl:.0f}pip"
    )
    print(f"{'=' * 105}")
    print(header)
    print(sep)

    for cell, res in results:
        import math

        d_sharpe = (
            res["sharpe"] - baseline_sharpe if baseline_sharpe == baseline_sharpe else float("nan")
        )
        pnl_ratio = (
            res["pnl"] / baseline_pnl
            if (baseline_pnl == baseline_pnl and baseline_pnl != 0)
            else float("nan")
        )
        d_sharpe_str = f"{d_sharpe:+.4f}" if not math.isnan(d_sharpe) else "   N/A"
        pnl_ratio_str = f"{pnl_ratio:7.2f}x" if not math.isnan(pnl_ratio) else "    N/A"
        print(
            f"{cell.name:<16} {cell.data_suffix:>5} {res['n']:>7,}"
            f" {res['hit_pct']:>6.1f}% {res['pnl']:>10,.0f}"
            f" {res['sharpe']:>8.4f} {res['maxdd']:>8.1f}"
            f" {d_sharpe_str:>9} {pnl_ratio_str}  {cell.description}"
        )

    print(sep)
    print(
        "dSharpe/PnL比: vs A_baseline. anti-pyramiding: 同一ペアはhorizon=20バー再エントリー禁止."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
