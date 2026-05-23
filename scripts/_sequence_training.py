"""Sequence model training harness for Phase 29.0b-β A0-broad eval.

Per PR #354 §12 (training schedule; α-fixed). Critical design choice:
train-time early stopping uses validation **Huber loss** (NOT val Sharpe).
This preserves the train-time vs verdict-time objective wall.

Per-architecture overrides:
  S1 LSTM: lr=1e-3, batch=256
  S2 Temporal CNN: lr=1e-3, batch=512
  S3 Transformer: lr=5e-4, batch=256

Common settings:
  seed=42; AdamW with weight_decay=1e-4
  loss: HuberLoss(delta=0.9) (Huber α=0.9)
  max epochs=5; patience=2; best checkpoint = lowest val Huber loss
  deterministic mode: torch.use_deterministic_algorithms(True, warn_only=True)
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

# α-fixed per PR #354 §12
HUBER_DELTA = 0.9
MAX_EPOCHS = 5
PATIENCE = 2
WEIGHT_DECAY = 1e-4
SEED_DEFAULT = 42

# Per-architecture overrides (PR #354 §12.2)
ARCH_TRAINING_CONFIG: dict[str, dict] = {
    "S1": {"lr": 1e-3, "batch_size": 256},
    "S2": {"lr": 1e-3, "batch_size": 512},
    "S3": {"lr": 5e-4, "batch_size": 256},
}


@dataclass
class TrainingResult:
    arch_id: str
    best_epoch: int  # 0-indexed
    best_val_huber_loss: float
    val_huber_loss_per_epoch: list[float]
    train_huber_loss_per_epoch: list[float] = field(default_factory=list)
    early_stopping_triggered: bool = False
    epochs_run: int = 0
    checkpoint_path: str = ""
    seed: int = SEED_DEFAULT


def setup_deterministic_environment(seed: int = SEED_DEFAULT) -> None:
    """Configure deterministic PyTorch + CUDA per PR #354 §13.

    warn_only=True allows non-deterministic fallback for ops without
    deterministic implementations (per user instruction; CUDA numeric
    noise allowed within metric-level tolerance).
    """
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)


class CudaUnavailableError(RuntimeError):
    """Raised when CUDA device is required but not available.

    Per PR #353 §4 HALT criterion (preflight audit).
    """


def select_device() -> torch.device:
    """Select GPU device per PR #353 §4 preflight.

    HALT if no CUDA device available. Sequence training at production
    scale (~2.94M train rows × N M5 bars) infeasible on CPU.
    """
    if not torch.cuda.is_available():
        raise CudaUnavailableError(
            "CUDA device required for Phase 29.0b-β sequence training per "
            "PR #353 §4 HALT criterion. Sequence training at production data "
            "scale infeasible on CPU. Provision a CUDA-capable machine "
            "(≥ 8 GB VRAM recommended)."
        )
    device = torch.device("cuda:0")
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    if vram_gb < 8:
        warnings.warn(
            f"VRAM {vram_gb:.1f} GB < 8 GB; per PR #353 §4 mitigation may need "
            "gradient checkpointing / smaller batch (NOT implemented at α; α "
            "amendment required if blocked).",
            UserWarning,
            stacklevel=2,
        )
    return device


def _make_dataloader(
    x: np.ndarray, y: np.ndarray, batch_size: int, shuffle: bool, seed: int
) -> torch.utils.data.DataLoader:
    """Create a deterministic DataLoader.

    For shuffled (train) loaders: uses a torch.Generator with explicit seed
    to make iteration order reproducible.
    """
    x_tensor = torch.from_numpy(x).float()
    y_tensor = torch.from_numpy(y).float()
    dataset = torch.utils.data.TensorDataset(x_tensor, y_tensor)
    generator = torch.Generator()
    generator.manual_seed(seed)
    return torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator if shuffle else None,
        num_workers=0,  # determinism: avoid worker non-determinism
    )


def _compute_val_huber_loss(
    model: nn.Module,
    val_x: np.ndarray,
    val_y: np.ndarray,
    batch_size: int,
    device: torch.device,
    huber_delta: float = HUBER_DELTA,
) -> float:
    """Compute mean validation Huber loss."""
    model.eval()
    huber = nn.HuberLoss(delta=huber_delta, reduction="sum")
    loader = _make_dataloader(val_x, val_y, batch_size=batch_size, shuffle=False, seed=0)
    total_loss = 0.0
    n = 0
    with torch.no_grad():
        for x_batch, y_batch in loader:
            x_batch = x_batch.to(device, non_blocking=True)
            y_batch = y_batch.to(device, non_blocking=True)
            pred = model(x_batch)
            total_loss += float(huber(pred, y_batch).item())
            n += int(y_batch.size(0))
    if n == 0:
        return float("inf")
    return total_loss / n


def train_sequence_model(
    model: nn.Module,
    arch_id: str,
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    checkpoint_path: Path,
    device: torch.device,
    max_epochs: int = MAX_EPOCHS,
    patience: int = PATIENCE,
    huber_delta: float = HUBER_DELTA,
    seed: int = SEED_DEFAULT,
) -> TrainingResult:
    """Train sequence model with val Huber loss early stopping.

    Per PR #354 §12 (critical design choice): early stopping monitor
    metric is **validation Huber loss**, NOT val Sharpe. This preserves
    the train-time vs verdict-time objective wall.

    Best checkpoint = lowest val Huber loss; saved to checkpoint_path.
    """
    setup_deterministic_environment(seed)
    model = model.to(device)
    arch_cfg = ARCH_TRAINING_CONFIG.get(arch_id)
    if arch_cfg is None:
        raise ValueError(f"unknown arch_id={arch_id!r}")
    lr = arch_cfg["lr"]
    batch_size = arch_cfg["batch_size"]

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)
    huber = nn.HuberLoss(delta=huber_delta, reduction="mean")

    best_val_loss = float("inf")
    best_epoch = -1
    epochs_no_improve = 0
    val_loss_history: list[float] = []
    train_loss_history: list[float] = []
    early_stopped = False
    epochs_run = 0

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(max_epochs):
        epochs_run = epoch + 1

        # Train pass
        model.train()
        train_loader = _make_dataloader(
            train_x, train_y, batch_size=batch_size, shuffle=True, seed=seed + epoch
        )
        train_loss_sum = 0.0
        train_n = 0
        for x_batch, y_batch in train_loader:
            x_batch = x_batch.to(device, non_blocking=True)
            y_batch = y_batch.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            pred = model(x_batch)
            loss = huber(pred, y_batch)
            loss.backward()
            optimizer.step()
            train_loss_sum += float(loss.item()) * int(y_batch.size(0))
            train_n += int(y_batch.size(0))
        train_loss_history.append(train_loss_sum / max(train_n, 1))

        # Val pass
        val_loss = _compute_val_huber_loss(
            model, val_x, val_y, batch_size=batch_size, device=device, huber_delta=huber_delta
        )
        val_loss_history.append(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            epochs_no_improve = 0
            torch.save(model.state_dict(), checkpoint_path)
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                early_stopped = True
                break

    return TrainingResult(
        arch_id=arch_id,
        best_epoch=best_epoch,
        best_val_huber_loss=best_val_loss,
        val_huber_loss_per_epoch=val_loss_history,
        train_huber_loss_per_epoch=train_loss_history,
        early_stopping_triggered=early_stopped,
        epochs_run=epochs_run,
        checkpoint_path=str(checkpoint_path),
        seed=seed,
    )


def predict_sequence_score(
    model: nn.Module,
    x: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    """Inference: per-row scalar scores as float64 np.ndarray.

    Deterministic given the same model state_dict + same input.
    """
    model.eval()
    model = model.to(device)
    scores: list[np.ndarray] = []
    loader = _make_dataloader(
        x, np.zeros(len(x), dtype=np.float32), batch_size=batch_size, shuffle=False, seed=0
    )
    with torch.no_grad():
        for x_batch, _ in loader:
            x_batch = x_batch.to(device, non_blocking=True)
            pred = model(x_batch)
            scores.append(pred.cpu().numpy().astype(np.float64))
    return np.concatenate(scores) if scores else np.zeros(0, dtype=np.float64)


def load_checkpoint(model: nn.Module, checkpoint_path: Path, device: torch.device) -> nn.Module:
    """Load model state_dict from checkpoint; returns model on device."""
    state_dict = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    return model.to(device)


def estimate_gpu_memory_after_fit(device: torch.device) -> dict:
    """DIAGNOSTIC: report peak VRAM utilisation since reset.

    Used by sanity probe item 10 per PR #354 §16.2.
    """
    if device.type != "cuda":
        return {"available": False}
    peak_mb = torch.cuda.max_memory_allocated(device) / 1e6
    total_mb = torch.cuda.get_device_properties(device).total_memory / 1e6
    util_frac = peak_mb / max(total_mb, 1)
    return {
        "available": True,
        "peak_mb": float(peak_mb),
        "total_mb": float(total_mb),
        "utilisation_fraction": float(util_frac),
    }


def reset_gpu_memory_tracker(device: torch.device) -> None:
    """Reset peak memory tracker; called before each architecture fit."""
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
