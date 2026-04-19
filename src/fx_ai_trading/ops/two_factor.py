"""Two-factor confirmation for high-risk ctl operations (M22 / Mi-CTL-1).

Implements the TwoFactorAuthenticator Protocol defined in D3 (§2.18).
Production: ConsoleTwoFactor generates a one-time token and prompts the
operator to type it back.  The token is produced via secrets.token_hex
(cryptographically random, not the forbidden random module).

Phase 8 replacement: SSO-backed TwoFactorAuthenticator injected here;
the Protocol contract does not change.
"""

from __future__ import annotations

import secrets
from typing import Protocol


class TwoFactorAuthenticator(Protocol):
    """Single-method confirmation gate (D3 §2.18 / M22).

    MUST:
    - Return True only when the operator actively confirms.
    - Return False (not raise) on any failure or cancellation.
    - Never bypass itself or store a persistent "already confirmed" flag.
    """

    def run_challenge(self) -> bool:
        """Run the interactive confirmation challenge.

        Returns:
            True if the operator confirmed successfully.
            False if confirmation failed, was cancelled, or timed out.
        """
        ...


class ConsoleTwoFactor:
    """Interactive console 2-factor: display token, prompt operator to retype it."""

    def run_challenge(self) -> bool:
        """Display a random token and require the operator to type it back.

        Returns True if the entered token matches; False otherwise.
        Catches KeyboardInterrupt (Ctrl-C) and returns False.
        """
        token = secrets.token_hex(3)
        try:
            import click

            click.echo(f"\n  Confirmation token: {token}")
            click.echo("  Type the token above to confirm, or press Ctrl-C to abort.\n")
            entered = click.prompt("  Token")
        except (KeyboardInterrupt, EOFError):
            return False

        matched = entered.strip() == token
        if not matched:
            import click

            click.echo("  Token mismatch — operation aborted.")
        return matched


class FixedTwoFactor:
    """Deterministic stub for tests — always returns the configured result."""

    def __init__(self, result: bool) -> None:
        self._result = result

    def run_challenge(self) -> bool:
        return self._result
