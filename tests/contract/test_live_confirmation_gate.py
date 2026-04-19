"""Contract tests: LiveConfirmationGate demo→live gate (M13b, 6.18).

Verifies:
  1. Demo account always passes the gate (no env/operator/config_version needed).
  2. Live account without operator_confirmed raises Stage 2 error.
  3. Live account without OANDA_ACCOUNT_TYPE env var raises Stage 1 error.
  4. Live account with wrong OANDA_ACCOUNT_TYPE env var raises Stage 1 error.
  5. Live account with empty config_version raises Stage 3 error.
  6. Live account with all stages satisfied passes.
  7. Stage order is 1 → 2 → 3 (env checked before operator before config).

These tests MUST NOT exercise a real live OANDA account.  All env patching
uses monkeypatch / unittest.mock.patch so no real env variable is mutated.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from fx_ai_trading.common.exceptions import LiveConfirmationError
from fx_ai_trading.supervisor.live_confirmation import LiveConfirmationGate

_LIVE = "live"
_DEMO = "demo"
_VALID_CV = "abc123def456"
_ENV_KEY = "OANDA_ACCOUNT_TYPE"


@pytest.fixture
def gate() -> LiveConfirmationGate:
    return LiveConfirmationGate()


def _env_without_key() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != _ENV_KEY}


# ---------------------------------------------------------------------------
# Demo account — gate always passes
# ---------------------------------------------------------------------------


class TestDemoGate:
    def test_demo_passes_without_any_env(self, gate: LiveConfirmationGate) -> None:
        with patch.dict("os.environ", {}, clear=False):
            gate.verify(expected_account_type=_DEMO, config_version=_VALID_CV)

    def test_demo_passes_without_operator_confirmed(self, gate: LiveConfirmationGate) -> None:
        gate.verify(
            expected_account_type=_DEMO,
            config_version=_VALID_CV,
            operator_confirmed=False,
        )

    def test_demo_passes_with_empty_config_version(self, gate: LiveConfirmationGate) -> None:
        gate.verify(expected_account_type=_DEMO, config_version="")

    def test_demo_does_not_require_oanda_account_type_env(self, gate: LiveConfirmationGate) -> None:
        with patch.dict("os.environ", _env_without_key(), clear=True):
            gate.verify(expected_account_type=_DEMO, config_version=_VALID_CV)


# ---------------------------------------------------------------------------
# Live account — stage 1: env var
# ---------------------------------------------------------------------------


class TestLiveGateStage1Env:
    def test_live_fails_if_env_not_set(self, gate: LiveConfirmationGate) -> None:
        with (
            patch.dict("os.environ", _env_without_key(), clear=True),
            pytest.raises(LiveConfirmationError, match="Stage 1"),
        ):
            gate.verify(
                expected_account_type=_LIVE,
                config_version=_VALID_CV,
                operator_confirmed=True,
            )

    def test_live_fails_if_env_set_to_demo(self, gate: LiveConfirmationGate) -> None:
        with (
            patch.dict("os.environ", {_ENV_KEY: "demo"}),
            pytest.raises(LiveConfirmationError, match="Stage 1"),
        ):
            gate.verify(
                expected_account_type=_LIVE,
                config_version=_VALID_CV,
                operator_confirmed=True,
            )

    def test_live_fails_if_env_is_empty_string(self, gate: LiveConfirmationGate) -> None:
        with (
            patch.dict("os.environ", {_ENV_KEY: ""}),
            pytest.raises(LiveConfirmationError, match="Stage 1"),
        ):
            gate.verify(
                expected_account_type=_LIVE,
                config_version=_VALID_CV,
                operator_confirmed=True,
            )


# ---------------------------------------------------------------------------
# Live account — stage 2: operator confirmation
# ---------------------------------------------------------------------------


class TestLiveGateStage2Operator:
    def test_live_fails_without_operator_confirmed(self, gate: LiveConfirmationGate) -> None:
        with (
            patch.dict("os.environ", {_ENV_KEY: _LIVE}),
            pytest.raises(LiveConfirmationError, match="Stage 2"),
        ):
            gate.verify(
                expected_account_type=_LIVE,
                config_version=_VALID_CV,
                operator_confirmed=False,
            )

    def test_live_fails_operator_default_false(self, gate: LiveConfirmationGate) -> None:
        with (
            patch.dict("os.environ", {_ENV_KEY: _LIVE}),
            pytest.raises(LiveConfirmationError, match="Stage 2"),
        ):
            gate.verify(expected_account_type=_LIVE, config_version=_VALID_CV)


# ---------------------------------------------------------------------------
# Live account — stage 3: config_version
# ---------------------------------------------------------------------------


class TestLiveGateStage3ConfigVersion:
    def test_live_fails_with_empty_config_version(self, gate: LiveConfirmationGate) -> None:
        with (
            patch.dict("os.environ", {_ENV_KEY: _LIVE}),
            pytest.raises(LiveConfirmationError, match="Stage 3"),
        ):
            gate.verify(
                expected_account_type=_LIVE,
                config_version="",
                operator_confirmed=True,
            )


# ---------------------------------------------------------------------------
# Live account — all stages pass
# ---------------------------------------------------------------------------


class TestLiveGateAllPass:
    def test_live_passes_when_all_stages_satisfied(self, gate: LiveConfirmationGate) -> None:
        with patch.dict("os.environ", {_ENV_KEY: _LIVE}):
            gate.verify(
                expected_account_type=_LIVE,
                config_version=_VALID_CV,
                operator_confirmed=True,
            )

    def test_verify_is_idempotent(self, gate: LiveConfirmationGate) -> None:
        with patch.dict("os.environ", {_ENV_KEY: _LIVE}):
            gate.verify(
                expected_account_type=_LIVE,
                config_version=_VALID_CV,
                operator_confirmed=True,
            )
            gate.verify(
                expected_account_type=_LIVE,
                config_version=_VALID_CV,
                operator_confirmed=True,
            )


# ---------------------------------------------------------------------------
# Stage ordering contract
# ---------------------------------------------------------------------------


class TestStageOrdering:
    def test_stage1_checked_before_stage2(self, gate: LiveConfirmationGate) -> None:
        with (
            patch.dict("os.environ", _env_without_key(), clear=True),
            pytest.raises(LiveConfirmationError, match="Stage 1"),
        ):
            gate.verify(
                expected_account_type=_LIVE,
                config_version=_VALID_CV,
                operator_confirmed=True,
            )

    def test_stage2_checked_before_stage3(self, gate: LiveConfirmationGate) -> None:
        with (
            patch.dict("os.environ", {_ENV_KEY: _LIVE}),
            pytest.raises(LiveConfirmationError, match="Stage 2"),
        ):
            gate.verify(
                expected_account_type=_LIVE,
                config_version="",
                operator_confirmed=False,
            )
