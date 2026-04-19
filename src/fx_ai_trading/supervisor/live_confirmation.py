"""LiveConfirmationGate — demo→live trading confirmation gate (6.18 / M13b).

Implements the three-stage verification that must pass before the system
is allowed to trade on a live OANDA account.  Called from:

  - startup.py Step 9 (account_type check extension, wired in M22)
  - ctl --confirm-live-trading command (M22 scope)

Stages (live only — demo always passes):
  1. Environment variable: OANDA_ACCOUNT_TYPE env var must equal the
     expected account type so that the runtime environment is explicitly
     declared live.
  2. Operator flag: caller must pass operator_confirmed=True, set by
     the ctl --confirm-live-trading command (M22).  Without this flag,
     no automated restart can silently switch to live trading.
  3. Config version: config_version must be non-empty, confirming that
     the startup config was fully computed (Step 4) before this gate.

All three stages must pass for a live account.  A single failure raises
LiveConfirmationError naming the failed stage.  Errors are NOT retried
here; the caller (ctl / startup) decides whether to abort or exit.

Secret safety: this module reads the OANDA_ACCOUNT_TYPE env var only for
comparison — it does NOT log its value.  OANDA_ACCESS_TOKEN is never
read here; that is OandaBroker's responsibility.
"""

from __future__ import annotations

import os

from fx_ai_trading.common.exceptions import LiveConfirmationError

_ENV_KEY_ACCOUNT_TYPE = "OANDA_ACCOUNT_TYPE"


class LiveConfirmationGate:
    """Three-stage gate for live trading activation.

    Stateless: every call to verify() re-evaluates all stages from the
    current environment.  No caching so that mis-configurations cannot
    be silently carried across restarts.
    """

    def verify(
        self,
        expected_account_type: str,
        config_version: str,
        *,
        operator_confirmed: bool = False,
    ) -> None:
        """Assert all confirmation stages pass for the given account type.

        For demo accounts: returns immediately (no gate required).
        For live accounts: all three stages must pass or LiveConfirmationError
        is raised with the name of the first failing stage.

        Args:
            expected_account_type: The account type from app_settings
                (``'demo'`` or ``'live'``).
            config_version: The config_version computed by ConfigProvider
                at startup Step 4.  Must be non-empty.
            operator_confirmed: True when the ctl ``--confirm-live-trading``
                flag has been explicitly passed (M22 scope).
        """
        if expected_account_type != "live":
            return

        self._check_stage1_env(expected_account_type)
        self._check_stage2_operator(operator_confirmed)
        self._check_stage3_config_version(config_version)

    # ------------------------------------------------------------------
    # Stage checks
    # ------------------------------------------------------------------

    def _check_stage1_env(self, expected: str) -> None:
        env_value = os.environ.get(_ENV_KEY_ACCOUNT_TYPE)
        if env_value != expected:
            raise LiveConfirmationError(
                f"Stage 1 (env): {_ENV_KEY_ACCOUNT_TYPE} is not set to 'live'. "
                f"Set the environment variable before starting with a live account."
            )

    def _check_stage2_operator(self, operator_confirmed: bool) -> None:
        if not operator_confirmed:
            raise LiveConfirmationError(
                "Stage 2 (operator): live trading requires explicit operator "
                "confirmation via `ctl --confirm-live-trading` (M22). "
                "Pass operator_confirmed=True only when that flag is present."
            )

    def _check_stage3_config_version(self, config_version: str) -> None:
        if not config_version:
            raise LiveConfirmationError(
                "Stage 3 (config_version): config_version is empty. "
                "Ensure startup Step 4 (config_version computation) completed "
                "successfully before calling the live confirmation gate."
            )
