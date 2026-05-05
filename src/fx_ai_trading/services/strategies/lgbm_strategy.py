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
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import lightgbm as lgb
import numpy as np

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

if TYPE_CHECKING:
    from sqlalchemy import Engine

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
        self._model_dir = model_dir

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
            p_long=round(p_long, 8),
            p_short=round(p_short, 8),
        )

    def register_models(self, engine: Engine) -> None:
        """Upsert each loaded model into model_registry and cache model_ids."""
        from sqlalchemy import text

        now = datetime.now(UTC)
        with engine.begin() as conn:
            for instrument in self._models:
                model_id = f"{self._strategy_id}_{instrument}"
                artifact = str(self._model_dir / f"{instrument}.joblib")
                conn.execute(
                    text(
                        """
                        INSERT INTO model_registry
                            (model_id, model_type, model_version, status, artifact_path, created_at, updated_at)
                        VALUES
                            (:mid, :mtype, :mver, 'active', :artifact, :now, :now)
                        ON CONFLICT (model_id) DO UPDATE
                            SET updated_at = EXCLUDED.updated_at,
                                status = 'active'
                        """
                    ),
                    {
                        "mid": model_id,
                        "mtype": self._STRATEGY_TYPE,
                        "mver": self._STRATEGY_VERSION,
                        "artifact": artifact,
                        "now": now,
                    },
                )
        _log.info(
            "register_models: upserted %d models into model_registry",
            len(self._models),
        )

    def write_predictions(
        self,
        engine: Engine,
        cycle_id: str,
        predictions: list[dict],
        feature_version: str = "v4",
    ) -> None:
        """Bulk-insert per-instrument predictions for one cycle."""
        if not predictions:
            return
        from sqlalchemy import text

        now = datetime.now(UTC)
        with engine.begin() as conn:
            for row in predictions:
                instrument = row["instrument"]
                model_id = f"{self._strategy_id}_{instrument}"
                conn.execute(
                    text(
                        """
                        INSERT INTO predictions
                            (model_id, cycle_id, instrument, strategy_id,
                             predicted_at, prediction, confidence, feature_version)
                        VALUES
                            (:mid, :cid, :inst, :sid, :ts, :pred, :conf, :fver)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "mid": model_id,
                        "cid": cycle_id,
                        "inst": instrument,
                        "sid": self._strategy_id,
                        "ts": now,
                        "pred": row.get("prediction", 1),
                        "conf": row.get("confidence", 0.0),
                        "fver": feature_version,
                    },
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
