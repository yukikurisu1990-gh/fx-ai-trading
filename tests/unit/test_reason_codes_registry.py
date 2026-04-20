"""Lint tests for the reason_code central registry (Cycle 6.8 / I-04).

Three guarantees enforced by this module:

1. Registry shape — ``LEGACY_BARE`` is bare/UPPERCASE only and ``DOTTED``
   is dotted only.  Sets are disjoint.
2. Producer hygiene — at every reason_code-related kwarg sink in the
   producer modules, the value must be a *non-literal* (i.e. attribute
   access into the registry) so that adding a new code requires
   registering it first.
3. Registered values cover every literal currently used at those sinks
   so the lint rule cannot silently regress when a new producer is
   wired up.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from fx_ai_trading.domain.reason_codes import (
    ALL_REGISTERED,
    DOTTED,
    LEGACY_BARE,
)

# Producer modules that emit reason_code values.  Adding a new
# producer that writes ``reason_code`` / ``primary_reason_code`` /
# ``reject_reason`` / ``constraint_violated`` MUST extend this list so
# the lint scan covers it.
_PRODUCER_FILES = [
    "src/fx_ai_trading/services/exit_policy.py",
    "src/fx_ai_trading/services/risk_manager.py",
    "src/fx_ai_trading/services/execution_gate.py",
    "src/fx_ai_trading/services/execution_gate_runner.py",
    "src/fx_ai_trading/services/meta_decider.py",
    "src/fx_ai_trading/services/meta_cycle_runner.py",
]

# Kwargs whose values are reason_code-typed in either DTOs or
# persistence calls.  Literals here must come from the registry.
_REASON_CODE_KWARGS = frozenset(
    {
        "reason_code",
        "primary_reason_code",
        "reject_reason",
        "constraint_violated",
    }
)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _string_literals_at_reason_kwargs(path: Path) -> list[tuple[int, str, str]]:
    """Return ``(lineno, kwarg_name, value)`` for every reason_code
    kwarg whose argument is a string literal in *path*."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    findings: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg not in _REASON_CODE_KWARGS:
                continue
            value = kw.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                findings.append((kw.value.lineno, kw.arg, value.value))
    return findings


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------


def test_dotted_values_all_contain_dot():
    offenders = [c for c in DOTTED if "." not in c]
    assert offenders == [], (
        f"DOTTED contains values without a dot: {offenders}.  "
        "New non-dotted codes must go into LEGACY_BARE (which is frozen) "
        "— refactor the value to dotted form instead."
    )


def test_legacy_bare_values_have_no_dot():
    offenders = [c for c in LEGACY_BARE if "." in c]
    assert offenders == [], (
        f"LEGACY_BARE contains dotted values: {offenders}.  "
        "Move them to DOTTED — LEGACY_BARE is reserved for grandfathered "
        "bare/UPPERCASE literals already persisted in DB."
    )


def test_legacy_and_dotted_are_disjoint():
    overlap = LEGACY_BARE & DOTTED
    assert overlap == set(), f"LEGACY_BARE and DOTTED must be disjoint: overlap={overlap}"


def test_all_registered_is_union():
    assert ALL_REGISTERED == LEGACY_BARE | DOTTED


# ---------------------------------------------------------------------------
# Producer hygiene
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", _PRODUCER_FILES)
def test_producer_does_not_inline_reason_code_literals(relpath: str):
    """Producers must use registry constants at reason_code kwarg sinks.

    A literal at any of ``reason_code=`` / ``primary_reason_code=`` /
    ``reject_reason=`` / ``constraint_violated=`` is rejected even if
    the value happens to be in the registry — the test is the
    enforcement mechanism that *new* literals get registered first.
    """
    path = _REPO_ROOT / relpath
    findings = _string_literals_at_reason_kwargs(path)
    if findings:
        rendered = "\n".join(
            f"  {relpath}:{lineno} — {kwarg}={value!r}" for lineno, kwarg, value in findings
        )
        pytest.fail(
            "Inlined reason_code literals must come from "
            "fx_ai_trading.domain.reason_codes:\n"
            f"{rendered}"
        )


# ---------------------------------------------------------------------------
# Registry coverage cross-check
# ---------------------------------------------------------------------------


def test_known_legacy_codes_present():
    """Sanity: the bare/UPPERCASE values that exit_policy /
    meta_decider / meta_cycle_runner produce are all registered.

    Acts as a regression net — if someone removes an entry from
    ``LEGACY_BARE`` thinking it is unused, this test fails.
    """
    expected = {
        "sl",
        "tp",
        "emergency_stop",
        "max_holding_time",
        "EV_BELOW_THRESHOLD",
        "CONFIDENCE_BELOW_THRESHOLD",
        "NO_CANDIDATES",
        "NO_SCORED_CANDIDATES",
        "CALENDAR_STALE",
        "SIGNAL_NO_TRADE",
        "NEAR_EVENT",
        "PRICE_ANOMALY",
        "ttl_expired",
        "SignalExpired",
        "DeferExhausted",
        "SpreadTooWide",
        "BrokerUnreachable",
    }
    missing = expected - LEGACY_BARE
    assert missing == set(), f"LEGACY_BARE is missing grandfathered codes: {missing}"


def test_known_dotted_codes_present():
    """Sanity: every ``risk.*`` value emitted by the Risk gate is registered."""
    expected = {
        "risk.concurrent_limit",
        "risk.single_currency_exposure",
        "risk.net_directional_exposure",
        "risk.total_risk",
        "risk.duplicate_instrument",
        "risk.max_open_positions",
        "risk.recent_execution_failure_cooloff",
        "risk.invalid_sl",
        "risk.invalid_risk_pct",
        "risk.size_under_min",
        "risk.unknown",
    }
    missing = expected - DOTTED
    assert missing == set(), f"DOTTED is missing registered risk codes: {missing}"
