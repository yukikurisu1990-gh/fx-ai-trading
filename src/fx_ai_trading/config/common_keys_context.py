"""CommonKeysContext — immutable container for the four mandatory Common Keys.

Common Keys are the cross-cutting identifiers that appear on every log row in
the primary DB (docs/schema_catalog.md §8.1).  They are propagated by the
Repository layer (M5) so application code never writes them directly.

Mandatory fields (schema_catalog.md §8.1):
    run_id          — process-launch unit (set once by Supervisor at startup)
    environment     — e.g. "demo" | "live" | "backtest"
    code_version    — git describe / semver of the deployed code
    config_version  — SHA256[:16] of the canonical config JSON (M3 Cycle 3+)

Optional keys (model_version, cycle_id, correlation_id, strategy_id, …) are
NOT included here — they are scoped to the individual Repository write calls
and added in M5 when the Repository base class is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommonKeysContext:
    """Immutable snapshot of the four mandatory Common Keys for a process run.

    Instances are created once at Supervisor startup and passed through the
    call stack via dependency injection.  Frozen to prevent accidental mutation
    across concurrent coroutines.
    """

    run_id: str
    environment: str
    code_version: str
    config_version: str

    def __post_init__(self) -> None:
        for field_name in ("run_id", "environment", "code_version", "config_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"CommonKeysContext.{field_name} must be a non-empty string")
