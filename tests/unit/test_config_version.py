"""Unit tests for config_version computation — pure Python, no DB required."""

from __future__ import annotations

import hashlib
import json

import pytest

from fx_ai_trading.config.config_version import compute_config_version

_ROWS = [
    {
        "name": "expected_account_type",
        "value": "demo",
        "type": "str",
        "introduced_in_version": "0.1.0",
    },
    {
        "name": "max_concurrent_positions",
        "value": "5",
        "type": "int",
        "introduced_in_version": "0.1.0",
    },
]
_ENV_VARS: dict[str, str] = {"APP_MODE": "paper"}
_ENV_FILE: dict[str, str] = {}
_DEFAULTS: dict[str, str] = {"risk_per_trade_pct": "1.0"}
_SECRETS: dict[str, str] = {}


def test_returns_16_hex_chars() -> None:
    result = compute_config_version(_ROWS, _ENV_VARS, _ENV_FILE, _DEFAULTS, _SECRETS)
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)


def test_deterministic_same_inputs() -> None:
    a = compute_config_version(_ROWS, _ENV_VARS, _ENV_FILE, _DEFAULTS, _SECRETS)
    b = compute_config_version(_ROWS, _ENV_VARS, _ENV_FILE, _DEFAULTS, _SECRETS)
    assert a == b


def test_different_app_settings_yields_different_version() -> None:
    extra = {"name": "z_extra", "value": "1", "type": "int", "introduced_in_version": "0.2.0"}
    rows_alt = [*_ROWS, extra]
    a = compute_config_version(_ROWS, _ENV_VARS, _ENV_FILE, _DEFAULTS, _SECRETS)
    b = compute_config_version(rows_alt, _ENV_VARS, _ENV_FILE, _DEFAULTS, _SECRETS)
    assert a != b


def test_different_env_vars_yields_different_version() -> None:
    a = compute_config_version(_ROWS, _ENV_VARS, _ENV_FILE, _DEFAULTS, _SECRETS)
    b = compute_config_version(_ROWS, {"APP_MODE": "live"}, _ENV_FILE, _DEFAULTS, _SECRETS)
    assert a != b


def test_different_secret_refs_yields_different_version() -> None:
    a = compute_config_version(_ROWS, _ENV_VARS, _ENV_FILE, _DEFAULTS, _SECRETS)
    b = compute_config_version(
        _ROWS, _ENV_VARS, _ENV_FILE, _DEFAULTS, {"API_KEY": "deadbeef01234567"}
    )
    assert a != b


def test_matches_manual_sha256() -> None:
    """Verify output equals SHA256[:16] of the expected canonical JSON."""
    effective = {
        "app_settings": _ROWS,
        "defaults": _DEFAULTS,
        "env_file": _ENV_FILE,
        "env_vars": _ENV_VARS,
        "secret_refs": _SECRETS,
    }
    canonical = json.dumps(effective, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    assert compute_config_version(_ROWS, _ENV_VARS, _ENV_FILE, _DEFAULTS, _SECRETS) == expected


def test_empty_inputs_returns_16_hex_chars() -> None:
    result = compute_config_version([], {}, {}, {}, {})
    assert len(result) == 16


@pytest.mark.parametrize(
    "rows_a,rows_b",
    [
        (
            [{"name": "a", "value": "1", "type": "int", "introduced_in_version": "0.1"}],
            [{"name": "a", "value": "2", "type": "int", "introduced_in_version": "0.1"}],
        ),
    ],
)
def test_value_change_changes_version(rows_a, rows_b) -> None:
    v_a = compute_config_version(rows_a, {}, {}, {}, {})
    v_b = compute_config_version(rows_b, {}, {}, {}, {})
    assert v_a != v_b
