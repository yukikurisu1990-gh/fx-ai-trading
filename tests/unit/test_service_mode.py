"""ServiceMode Interface contract tests (D3 §2.14.2 / M24)."""

from __future__ import annotations

import pytest

from fx_ai_trading.ops.service_mode import (
    ServiceMode,
    ServiceModeName,
    SingleProcessMode,
    get_service_mode,
)


def test_service_mode_name_has_three_canonical_values() -> None:
    """The enum must expose exactly the 3 modes documented in design.md §57."""
    assert {m.value for m in ServiceModeName} == {
        "single_process_mode",
        "multi_service_mode",
        "container_ready_mode",
    }


def test_single_process_mode_satisfies_protocol() -> None:
    """SingleProcessMode is the MVP-default and must satisfy ServiceMode."""
    instance: ServiceMode = SingleProcessMode()
    assert instance.name is ServiceModeName.SINGLE_PROCESS
    assert instance.event_bus_implementation == "InProcessEventBus"
    assert instance.supports_multi_process is False
    assert instance.supports_container_orchestration is False


def test_get_service_mode_returns_single_process_implementation() -> None:
    mode = get_service_mode(ServiceModeName.SINGLE_PROCESS)
    assert isinstance(mode, SingleProcessMode)


def test_get_service_mode_multi_service_is_not_implemented() -> None:
    """multi_service_mode is reserved for Phase 7+ at Iteration 2."""
    with pytest.raises(NotImplementedError, match="Phase 7"):
        get_service_mode(ServiceModeName.MULTI_SERVICE)


def test_get_service_mode_container_ready_is_not_implemented() -> None:
    """container_ready_mode is reserved for Phase 8+ at Iteration 2."""
    with pytest.raises(NotImplementedError, match="Phase 8"):
        get_service_mode(ServiceModeName.CONTAINER_READY)
