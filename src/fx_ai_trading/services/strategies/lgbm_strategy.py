"""LGBMStrategy — multi-instrument LightGBM classifier strategy.

Loads pre-trained per-pair LGBMClassifiers from models/lgbm/ and dispatches
to the correct model for each instrument in evaluate().

B-2 label convention (matching train_lgbm_models.py):
  proba[2] = P(long TP hit)   -> signal "long"
  proba[0] = P(short TP hit)  -> signal "short"
  proba[1] = P(timeout / neutral)

ev_after_cost = P(win) * tp_pips - P(lose) * sl_pips.
B-2 labels already embed the bid/ask spread, so this EV is post-spread.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_log = logging.getLogger(__name__)

_DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[4] / "models" / "lgbm"
_DEFAULT_THRESHOLD = 0.40

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


class LGBMStrategy:
    """Multi-instrument LGBM strategy (Phase 9.5-A).

    Loads all available per-pair models at init and dispatches by instrument.
    Instruments without a trained model receive a no_trade signal.

    Args:
        model_dir:  Directory containing {instrument}.joblib and manifest.json.
        threshold:  Minimum P(win) to emit a long/short signal (default 0.40).
        strategy_id: Identifier used in strategy_signals table.
    """

    _STRATEGY_TYPE = "lgbm_classifier"
    _STRATEGY_VERSION = "v1"

    def __init__(
        self,
        model_dir: Path = _DEFAULT_MODEL_DIR,
        threshold: float = _DEFAULT_THRESHOLD,
        strategy_id: str = "lgbm",
    ) -> None:
        self._threshold = threshold
        self._strategy_id = strategy_id

        manifest_path = model_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"LGBMStrategy: manifest not found at {manifest_path}. "
                "Run scripts/train_lgbm_models.py first."
            )
        manifest = json.loads(manifest_path.read_text())
        self._feature_cols: list[str] = manifest["feature_cols"]
        self._tp_mult: float = manifest.get("tp_mult", 1.5)
        self._sl_mult: float = manifest.get("sl_mult", 1.0)

        self._models: dict[str, lgb.LGBMClassifier] = {}
        for model_path in model_dir.glob("*.joblib"):
            instrument = model_path.stem
            self._models[instrument] = joblib.load(model_path)

        _log.info(
            "LGBMStrategy loaded: %d instruments, threshold=%.2f, features=%d",
            len(self._models),
            threshold,
            len(self._feature_cols),
        )

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        model = self._models.get(instrument)
        if model is None:
            return self._no_trade(instrument, features)

        stats = features.feature_stats
        x = np.array([[float(stats.get(col) or 0.0) for col in self._feature_cols]])

        proba = model.predict_proba(x)[0]
        p_long = float(proba[2])  # class 2 = label +1 (long TP)
        p_short = float(proba[0])  # class 0 = label -1 (short TP)

        atr = stats.get("atr_14", 0.0) or 0.0
        pip = _PIP_SIZE.get(instrument, 0.0001)
        tp_pips = (self._tp_mult * atr) / pip if atr > 0.0 else 0.0
        sl_pips = (self._sl_mult * atr) / pip if atr > 0.0 else 0.0

        if p_long >= self._threshold and p_long >= p_short:
            signal = "long"
            confidence = p_long
            ev = p_long * tp_pips - p_short * sl_pips
        elif p_short >= self._threshold:
            signal = "short"
            confidence = p_short
            ev = p_short * tp_pips - p_long * sl_pips
        else:
            signal = "no_trade"
            confidence = max(p_long, p_short)
            ev = 0.0

        return StrategySignal(
            strategy_id=self._strategy_id,
            strategy_type=self._STRATEGY_TYPE,
            strategy_version=self._STRATEGY_VERSION,
            signal=signal,
            confidence=round(confidence, 8),
            ev_before_cost=round(ev, 8),
            ev_after_cost=round(ev, 8),
            tp=round(tp_pips, 4),
            sl=round(sl_pips, 4),
            holding_time_seconds=1800,
            enabled=True,
        )

    def _no_trade(self, instrument: str, features: FeatureSet) -> StrategySignal:
        atr = features.feature_stats.get("atr_14", 0.0) or 0.0
        pip = _PIP_SIZE.get(instrument, 0.0001)
        tp_pips = (self._tp_mult * atr) / pip if atr > 0.0 else 0.0
        sl_pips = (self._sl_mult * atr) / pip if atr > 0.0 else 0.0
        return StrategySignal(
            strategy_id=self._strategy_id,
            strategy_type=self._STRATEGY_TYPE,
            strategy_version=self._STRATEGY_VERSION,
            signal="no_trade",
            confidence=0.0,
            ev_before_cost=0.0,
            ev_after_cost=0.0,
            tp=round(tp_pips, 4),
            sl=round(sl_pips, 4),
            holding_time_seconds=1800,
            enabled=True,
        )
