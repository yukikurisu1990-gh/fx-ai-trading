"""ModelRegistry and Predictor domain interfaces and DTOs (D3 §2.3.1–2.3.2).

ModelRegistry manages AI model lifecycle (stub/shadow/active/review/demoted).
Predictor wraps a loaded model for inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from fx_ai_trading.domain.feature import FeatureSet

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Model:
    """A loaded ML model artifact."""

    model_id: str
    strategy_type: str
    model_path: str
    state: str  # stub | shadow | active | review | demoted
    loaded_at: datetime


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata record for a model version in the registry."""

    model_id: str
    strategy_type: str
    state: str
    created_at: datetime
    promoted_at: datetime | None = None
    demoted_at: datetime | None = None
    demote_reason: str | None = None


@dataclass(frozen=True)
class PredictionContext:
    """Contextual inputs for Predictor.predict()."""

    cycle_id: str
    instrument: str
    strategy_id: str


@dataclass(frozen=True)
class Prediction:
    """Output of Predictor.predict() (D3 §2.3.2).

    Invariant: deterministic model produces same value for same inputs.
    """

    model_id: str
    value: float
    confidence: float


# ---------------------------------------------------------------------------
# Interfaces (Protocol)
# ---------------------------------------------------------------------------


class ModelRegistry(Protocol):
    """AI model lifecycle manager (D3 §2.3.1).

    Invariant: at most one model in 'active' state per strategy_type × instrument.
    Side effects: writes to model_registry table.
    Idempotency: promote/demote are no-ops when already in target state.
    """

    def load(self, model_id: str) -> Model:
        """Load and return model artifact for *model_id*."""
        ...

    def save(self, model: Model, metadata: ModelMetadata) -> str:
        """Persist *model* with *metadata*, return model_id."""
        ...

    def promote(self, model_id: str, to_state: str) -> None:
        """Transition *model_id* to *to_state* (idempotent)."""
        ...

    def demote(self, model_id: str, reason: str) -> None:
        """Demote *model_id* with *reason* (idempotent)."""
        ...

    def get_active(self, strategy_type: str) -> Model | None:
        """Return the active model for *strategy_type*, or None."""
        ...

    def get_shadow(self, strategy_type: str) -> Model | None:
        """Return the shadow model for *strategy_type*, or None."""
        ...

    def list_by_state(self, state: str) -> list[ModelMetadata]:
        """Return all model metadata records with the given *state*."""
        ...


class Predictor(Protocol):
    """AI model inference wrapper (D3 §2.3.2).

    Side effects: writes to predictions table (via evaluation framework).
    Idempotency: deterministic model produces identical output for identical input.
    Failure modes: model load failure → AIStrategy falls back to Stub.
    """

    def predict(self, features: FeatureSet, context: PredictionContext) -> Prediction:
        """Run inference on *features* given *context*."""
        ...

    def get_model_id(self) -> str:
        """Return the model_id this predictor wraps."""
        ...
