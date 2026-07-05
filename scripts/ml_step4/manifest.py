"""Runtime manifest capture for the ML Step 4 run body (PR #416 item 4).

Captures the ACTUAL git code SHA (fail-closed if unrecordable), the Python
version, package versions for the declared dependency set (via
``importlib.metadata`` — names and versions only, never an environment dump),
and the runtime seeds actually used. Never touches ``model_config_hash`` and
never adds a seed to the frozen PR #407 model contract.
"""

from __future__ import annotations

import platform
import subprocess
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Final

from . import contract
from .evidence import repo_root

REPRODUCIBILITY_LEVEL: Final[str] = "bounded_not_bitwise_guaranteed"

# Names-only dependency capture set (versions recorded when installed).
_PACKAGE_CAPTURE: Final[tuple[str, ...]] = ("numpy", "pandas", "lightgbm", "scikit-learn")

REQUIRED_MANIFEST_FIELDS: Final[tuple[str, ...]] = (
    "code_sha",
    "python_version",
    "package_versions",
    "seeds",
    "reproducibility_level",
    "epoch_id",
    "config_hash",
    "feature_config_hash",
    "model_config_hash",
    "threshold_config_hash",
    "label_contract_id",
    "fixed_notional_equity_pips",
    "mode",
)


class ManifestError(RuntimeError):
    """Raised when required runtime provenance cannot be captured."""


def git_code_sha(cwd: Path | None = None) -> str:
    """The ACTUAL current git code SHA; fail closed if unrecordable."""
    try:
        out = subprocess.run(  # read-only provenance query
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd or repo_root()),
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManifestError(f"git code SHA unrecordable: {type(exc).__name__}") from exc
    sha = out.stdout.strip()
    if len(sha) != 40:
        raise ManifestError(f"git code SHA malformed (len {len(sha)})")
    return sha


def package_versions() -> dict[str, str]:
    """Versions for the declared capture set (absent packages marked, no env dump)."""
    versions: dict[str, str] = {}
    for name in _PACKAGE_CAPTURE:
        try:
            versions[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            versions[name] = "not_installed"
    return versions


def build_run_manifest(
    *,
    mode: str,
    seeds: dict[str, int],
    pip_size_by_pair: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Assemble the runtime manifest; fail closed on any missing field.

    ``pip_size_by_pair`` (optional) records the INV-1 per-pair pip-size mapping
    used by the run. When supplied it must be a non-empty mapping of positive
    pip sizes; it is recorded alongside an explicit flag that no single global
    pip size is authoritative for all pairs. The fixture rehearsal may omit it.
    """
    if not isinstance(seeds, dict) or not seeds:
        raise ManifestError("runtime seeds missing (record every seed actually used)")
    from .labels import label_contract_identity  # local import avoids cycles

    manifest: dict[str, Any] = {
        "mode": mode,
        "code_sha": git_code_sha(),
        "python_version": platform.python_version(),
        "package_versions": package_versions(),
        "seeds": dict(seeds),
        "reproducibility_level": REPRODUCIBILITY_LEVEL,
        "epoch_id": contract.EPOCH_ID,
        "config_hash": contract.config_hash(),
        "feature_config_hash": contract.feature_config_hash(),
        "model_config_hash": contract.model_config_hash(),
        "threshold_config_hash": contract.threshold_config_hash(),
        "label_contract_id": label_contract_identity()["label_contract_id"],
        "threshold_tie_rule": contract.THRESHOLD_TIE_RULE,
        "trading_day_definition": contract.TRADING_DAY_DEFINITION,
        "daily_coverage_denominator": contract.DAILY_COVERAGE_DENOMINATOR,
        "fixed_notional_equity_pips": contract.FIXED_NOTIONAL_EQUITY_PIPS,
    }
    if pip_size_by_pair is not None:
        if not pip_size_by_pair or any(not (v > 0) for v in pip_size_by_pair.values()):
            raise ManifestError("pip_size_by_pair must be a non-empty map of positive pip sizes")
        manifest["pip_size_by_pair"] = dict(pip_size_by_pair)
        manifest["global_pip_size_authoritative_for_all_pairs"] = False
        manifest["pip_size_convention"] = "0.01 if pair endswith _JPY else 0.0001"
    assert_manifest_complete(manifest)
    return manifest


def assert_manifest_complete(manifest: dict[str, Any]) -> None:
    """Fail closed if any required provenance field is missing or empty."""
    missing = [f for f in REQUIRED_MANIFEST_FIELDS if not manifest.get(f)]
    if missing:
        raise ManifestError(f"manifest missing required provenance fields: {missing}")
    if manifest["reproducibility_level"] != REPRODUCIBILITY_LEVEL:
        raise ManifestError("reproducibility level must be bounded_not_bitwise_guaranteed")
