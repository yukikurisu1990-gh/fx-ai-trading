"""Metadata artifact validation + writing with a gate-3a-STRICT scrubber.

The ML Step 4 evidence scrubber legitimately allows metric keys (sharpe / pnl /
expectancy). Gate-3a/gate-5 metadata artifacts must be even stricter: they carry
NO strategy metrics, predictions, model outputs, or trade-level rows. This module
layers those extra prohibitions on top of the base scrubber and refuses to write
under any protected real path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from scripts.ml_step4 import evidence

from .guards import refuse_real_path

# Extra forbidden keys beyond the base scrubber (metrics/predictions/model/trades).
_GATE3A_FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "predictions",
        "prediction",
        "logits",
        "proba",
        "probability",
        "probabilities",
        "model",
        "model_binary",
        "weights",
        "trades",
        "trade_rows",
        "trade_level",
        "validation_metrics",
        "holdout_metrics",
        "sharpe",
        "expectancy",
        "pnl",
        "pnl_realized",
        "drawdown",
        "win_rate",
        "returns",
    }
)

# Recommended gate-3a artifact filenames (mirrors artifacts/m15_gate3a/).
EXPECTED_ARTIFACT_FILES: Final[tuple[str, ...]] = (
    "design_m15_derivation_manifest.json",
    "design_m15_inventory.json",
    "forward_epoch_adoption_manifest.json",
    "forward_epoch_inventory.json",
    "no_overlap_proof.json",
    "effective_n_estimator_spec.json",
    "cost_table_plan_or_metadata.json",
    "scrub_report.json",
)


class ArtifactScrubError(RuntimeError):
    """Raised when a gate-3a metadata artifact would leak forbidden content."""


def _scan_gate3a_keys(obj: Any, findings: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.lower() in _GATE3A_FORBIDDEN_KEYS:
                findings.append(f"gate3a_forbidden_key:{key}")
            _scan_gate3a_keys(value, findings)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _scan_gate3a_keys(item, findings)


def scan_gate3a(payload: Any) -> list[str]:
    """Base scrubber findings PLUS gate-3a metric/prediction/trade prohibitions."""
    findings = list(evidence.scan_payload(payload))
    _scan_gate3a_keys(payload, findings)
    return sorted(set(findings))


def assert_gate3a_clean(payload: Any) -> None:
    findings = scan_gate3a(payload)
    if findings:
        raise ArtifactScrubError(f"gate-3a artifact not clean: {findings}")


def validate_metadata_artifact(payload: Any) -> None:
    """Fail closed unless the payload is a scrub-clean metadata object."""
    if not isinstance(payload, (dict, list)):
        raise ArtifactScrubError("metadata artifact must be an object or array")
    assert_gate3a_clean(payload)


def write_metadata_artifact(out_dir: str | Path, name: str, payload: Any) -> Path:
    """Validate + write a scrub-clean gate-3a metadata artifact (never under real paths)."""
    if not name.endswith(".json"):
        raise ArtifactScrubError("artifact name must end with .json")
    out = Path(out_dir)
    refuse_real_path(out)
    validate_metadata_artifact(payload)
    out.mkdir(parents=True, exist_ok=True)
    target = out / name
    refuse_real_path(target)
    target.write_text(evidence.serialise(payload), encoding="utf-8")
    return target
