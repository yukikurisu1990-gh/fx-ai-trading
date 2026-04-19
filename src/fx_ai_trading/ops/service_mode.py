"""ServiceMode declaration and connection points (D3 §2.14.2).

Three execution modes share a single logical contract; switching modes
does NOT change application code, only the concrete `ServiceMode`
implementation that resolves the EventBus / Transport / Supervisor
layout.

Iteration 2 scope: Interface declaration + connection points only.
Only `single_process_mode` is operationally implemented at MVP; the
other two modes are reserved for Phase 7+ (multi_service_mode) and
Phase 8+ (container_ready_mode) — see `iteration2_implementation_plan.md`
§6.12 and §10.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ServiceModeName(StrEnum):
    """Canonical execution-mode identifiers.

    Stable string values are used directly in configuration files,
    `app_settings`, and dashboard panels. Do not rename without a
    schema migration + Common Keys propagation review.
    """

    SINGLE_PROCESS = "single_process_mode"
    MULTI_SERVICE = "multi_service_mode"
    CONTAINER_READY = "container_ready_mode"


class ServiceMode(Protocol):
    """Execution-mode abstraction (D3 §2.14.2).

    Each mode declares which concrete EventBus / Transport implementation
    is appropriate and what process / orchestration topology it expects.
    The contract is intentionally minimal at Iteration 2 — additional
    connection points (lifecycle hooks, supervisor handoff) will be added
    in Phase 7+ when multi_service_mode is operationalized.
    """

    @property
    def name(self) -> ServiceModeName:
        """Canonical mode identifier."""
        ...

    @property
    def event_bus_implementation(self) -> str:
        """Class name of the EventBus implementation appropriate for this mode.

        Resolved by composition root at startup; matches one of
        `InProcessEventBus` / `LocalQueueEventBus` / `NetworkBusEventBus`
        as defined in D3 §2.14.1.
        """
        ...

    @property
    def supports_multi_process(self) -> bool:
        """True if this mode runs the application as multiple OS processes."""
        ...

    @property
    def supports_container_orchestration(self) -> bool:
        """True if this mode expects an external orchestrator (k8s / nomad / etc.)."""
        ...


@dataclass(frozen=True)
class SingleProcessMode:
    """The MVP-default mode (D3 §2.14.2, single_process_mode).

    Single OS process, in-process EventBus, OS-level supervisor
    (systemd / nssm / launchd) handles process restart. This is the
    only mode that is operationally implemented at Iteration 2.
    """

    @property
    def name(self) -> ServiceModeName:
        return ServiceModeName.SINGLE_PROCESS

    @property
    def event_bus_implementation(self) -> str:
        return "InProcessEventBus"

    @property
    def supports_multi_process(self) -> bool:
        return False

    @property
    def supports_container_orchestration(self) -> bool:
        return False


def get_service_mode(name: ServiceModeName) -> ServiceMode:
    """Resolve a `ServiceMode` instance for *name*.

    Iteration 2 only implements `SINGLE_PROCESS`. The other two modes
    are recognised at the type level (their `ServiceModeName` enum
    values exist and may be referenced by configuration) but raise
    `NotImplementedError` here until Phase 7+ (multi_service_mode)
    and Phase 8+ (container_ready_mode) bring them online.
    """
    if name is ServiceModeName.SINGLE_PROCESS:
        return SingleProcessMode()
    if name is ServiceModeName.MULTI_SERVICE:
        raise NotImplementedError(
            "multi_service_mode is reserved for Phase 7+ "
            "(see iteration2_implementation_plan.md §10.1)"
        )
    if name is ServiceModeName.CONTAINER_READY:
        raise NotImplementedError(
            "container_ready_mode is reserved for Phase 8+ "
            "(see iteration2_implementation_plan.md §10.1)"
        )
    raise ValueError(f"Unknown ServiceModeName: {name!r}")
