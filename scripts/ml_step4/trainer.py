"""Trainer wrapper for the ML Step 4 run body (from scratch, contract-pinned).

Production path: ``train_lgbm`` builds a fresh LightGBM 3-class classifier from
exactly the frozen contract convention (``contract.LGBM_PARAMS`` +
``LGBM_N_ESTIMATORS``) via lazy import — never invoked on real data in this
build, never loads a deployed ``models/lgbm/`` artifact, never persists a
binary.

Fixture path: ``FixtureModelStub`` — a deterministic, dependency-free stand-in
used by tests to rehearse the pipeline without LightGBM. It is explicitly NOT
a trained model and is labeled synthetic in every manifest.
"""

from __future__ import annotations

from typing import Any, Final

from . import contract

TRAINING_MODE_FIXTURE: Final[str] = "fixture_stub_synthetic_only"
TRAINING_MODE_PRODUCTION: Final[str] = "lightgbm_from_scratch"

_CLASS_ORDER: Final[tuple[int, int, int]] = (-1, 0, 1)


class TrainerContractError(ValueError):
    """Raised when a training request deviates from the frozen contract."""


def training_config() -> dict[str, Any]:
    """Provenance record for the training convention (contract-pinned)."""
    return {
        "model_config": contract.model_config(),
        "model_config_hash": contract.model_config_hash(),
        "deployed_model_reuse": False,
        "model_binary_persisted": False,
        "class_order": list(_CLASS_ORDER),
    }


def train_lgbm(x_rows: list[list[float]], y: list[int]):  # pragma: no cover - heavy path
    """From-scratch LightGBM training under the frozen convention (lazy import).

    Exercised only on tiny synthetic data in an optional, skippable test; the
    real-data invocation belongs to the future execution PR. No model_path
    argument exists — deployed-model reuse is structurally impossible here.
    """
    contract.assert_model_family(contract.MODEL_FAMILY)
    contract.assert_no_deployed_model_reuse(None)
    import lightgbm as lgb

    params = {**contract.LGBM_PARAMS, "n_estimators": contract.LGBM_N_ESTIMATORS}
    model = lgb.LGBMClassifier(**params)
    model.fit(x_rows, y)
    return model


class FixtureModelStub:
    """Deterministic 3-class probability stub (synthetic rehearsal only).

    ``predict_proba`` maps the first feature through a fixed squashing rule —
    no learning, no randomness, no dependencies. Same rows → same output.
    """

    training_mode = TRAINING_MODE_FIXTURE
    synthetic_only = True
    classes_ = list(_CLASS_ORDER)

    def __init__(self, scale: float = 8000.0) -> None:
        self._scale = scale

    def fit(self, x_rows: list[list[float]], y: list[int]) -> FixtureModelStub:
        del x_rows, y  # deterministic stub: nothing is learned
        return self

    def predict_proba(self, x_rows: list[list[float]]) -> list[list[float]]:
        out: list[list[float]] = []
        for row in x_rows:
            s = max(-1.0, min(1.0, row[0] * self._scale))
            p_long = 0.34 + 0.30 * max(0.0, s)
            p_short = 0.34 + 0.30 * max(0.0, -s)
            p_flat = max(0.0, 1.0 - p_long - p_short)
            total = p_long + p_short + p_flat
            out.append([p_short / total, p_flat / total, p_long / total])
        return out
