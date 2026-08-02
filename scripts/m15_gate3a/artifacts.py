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

from .guards import is_forbidden_status, refuse_real_path

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


# O-2 / R-5 hardening: conservative row-like heuristic. Two record-shaped
# smuggling forms are rejected — >= 2 dicts each carrying >= 6 numeric (non-bool)
# immediate values (a full BA row has 8 numeric sides), and >= 2 numeric arrays
# of equal length >= 4 (the columnar encoding of the same rows). Thresholds are
# chosen so legitimate metadata survives: cost-table entries have 4 numeric
# fields, inventory records <= 4; neither trips the heuristic.
#
# R-5: the record test COUNTS qualifying dicts instead of requiring `all(...)`.
# The previous `all(...)` was defeated by appending one benign dict to the list.
_ROW_LIKE_MIN_RECORDS: Final[int] = 2
_ROW_LIKE_MIN_NUMERIC_FIELDS: Final[int] = 6
_COLUMNAR_MIN_SERIES: Final[int] = 2
_COLUMNAR_MIN_LENGTH: Final[int] = 4


def _numeric_field_count(d: dict) -> int:
    return sum(1 for v in d.values() if isinstance(v, (int, float)) and not isinstance(v, bool))


def _is_numeric_series(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= _COLUMNAR_MIN_LENGTH
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
    )


def _scan_gate3a_keys(obj: Any, findings: list[str]) -> None:
    if isinstance(obj, dict):
        series_lengths = [len(v) for v in obj.values() if _is_numeric_series(v)]
        if len(series_lengths) >= _COLUMNAR_MIN_SERIES and len(set(series_lengths)) == 1:
            findings.append("gate3a_columnar_numeric_series")
        for key, value in obj.items():
            if isinstance(key, str) and key.strip().lower() in _GATE3A_FORBIDDEN_KEYS:
                findings.append(f"gate3a_forbidden_key:{key}")
            if is_forbidden_status(value):
                findings.append(f"gate3a_forbidden_status_value:{value}")
            _scan_gate3a_keys(value, findings)
    elif isinstance(obj, (list, tuple)):
        row_like = sum(
            1
            for x in obj
            if isinstance(x, dict) and _numeric_field_count(x) >= _ROW_LIKE_MIN_NUMERIC_FIELDS
        )
        if row_like >= _ROW_LIKE_MIN_RECORDS:
            findings.append("gate3a_row_like_numeric_records")
        numeric_rows = sum(1 for x in obj if _is_numeric_series(x))
        if numeric_rows >= _ROW_LIKE_MIN_RECORDS:
            findings.append("gate3a_row_like_numeric_arrays")
        for item in obj:
            if is_forbidden_status(item):
                findings.append(f"gate3a_forbidden_status_value:{item}")
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
    """Validate + write a scrub-clean gate-3a metadata artifact (never under real paths).

    R-9: ``name`` must be a bare filename. It previously reached ``out / name``
    unchecked, so ``"../escaped.json"`` and absolute names wrote outside
    ``out_dir``; the directory was also created before the target refusal, so a
    refused write could still leave a stray directory behind.
    """
    if not isinstance(name, str) or not name.endswith(".json"):
        raise ArtifactScrubError("artifact name must end with .json")
    if (
        name != Path(name).name
        or Path(name).is_absolute()
        or any(sep in name for sep in ("/", "\\"))
    ):
        raise ArtifactScrubError(f"artifact name must be a bare filename, got {name!r}")
    out = Path(out_dir)
    refuse_real_path(out)
    target = out / name
    refuse_real_path(target)
    validate_metadata_artifact(payload)
    out.mkdir(parents=True, exist_ok=True)
    target.write_text(evidence.serialise(payload), encoding="utf-8")
    return target
