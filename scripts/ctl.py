#!/usr/bin/env python
"""ctl -- minimal control CLI for FX-AI Trading system (M12 stub).

Commands:
  start               Start Supervisor + Dashboard  (M12: stub, logs only)
  stop                Stop Supervisor               (M12: stub, logs only)
  emergency-flat-all  Flatten all positions         (M12: stub, logs + echo, no real orders)

Usage:
    python scripts/ctl.py start
    python scripts/ctl.py stop
    python scripts/ctl.py emergency-flat-all
"""

from __future__ import annotations

import logging

import click

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [ctl] %(message)s",
)
_log = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """FX-AI Trading control CLI (M12 stub)."""


@cli.command()
def start() -> None:
    """Start Supervisor + Dashboard (stub -- no process spawned in M12)."""
    _log.info("ctl start: initiating Supervisor startup sequence (M12 stub)")
    click.echo("Supervisor startup initiated. (M12 stub -- no process spawned)")
    click.echo("To run for real: implement process management in Iteration 2.")


@cli.command()
def stop() -> None:
    """Stop Supervisor gracefully (stub -- no process stopped in M12)."""
    _log.info("ctl stop: initiating Supervisor shutdown (M12 stub)")
    click.echo("Supervisor stop requested. (M12 stub -- no process stopped)")


@cli.command("emergency-flat-all")
def emergency_flat_all() -> None:
    """Flatten all open positions -- LOGS ONLY, no real orders in M12 stub."""
    _log.warning(
        "EMERGENCY FLAT ALL requested via ctl. "
        "M12 stub: no real orders placed. Implement broker call in Iteration 2."
    )
    click.echo("=" * 60)
    click.echo("EMERGENCY FLAT ALL")
    click.echo("  Intent logged. No real orders placed (M12 stub).")
    click.echo("  Review logs and manually flatten positions if needed.")
    click.echo("=" * 60)


if __name__ == "__main__":
    cli()
