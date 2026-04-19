"""Integration tests: ProjectionService + MockSupabaseClient (M23).

Uses a real in-memory SQLite with supervisor_events table.
All transport calls use MockSupabaseClient (no real Supabase).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.adapters.projector.supabase import (
    MockSupabaseClient,
    SupabaseProjectionTransport,
)
from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.services.projection_service import ProjectionService

_DDL = """CREATE TABLE supervisor_events (
    supervisor_event_id TEXT PRIMARY KEY,
    event_type          TEXT NOT NULL,
    run_id              TEXT,
    config_version      TEXT,
    source_breakdown    TEXT,
    detail              TEXT,
    event_time_utc      TEXT NOT NULL
)"""

_T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL))
    yield eng
    eng.dispose()


@pytest.fixture()
def mock_client() -> MockSupabaseClient:
    return MockSupabaseClient()


@pytest.fixture()
def service(engine, mock_client) -> ProjectionService:
    transport = SupabaseProjectionTransport(client=mock_client)
    clock = FixedClock(_T0)
    return ProjectionService(engine=engine, transport=transport, clock=clock)


def _insert_event(engine, eid: str, event_type: str = "startup") -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO supervisor_events"
                " (supervisor_event_id, event_type, event_time_utc)"
                " VALUES (:eid, :etype, '2026-01-01T00:00:00+00:00')"
            ),
            {"eid": eid, "etype": event_type},
        )


class TestProjectionServiceDue:
    def test_initially_due(self, service) -> None:
        assert service.due() is True

    def test_not_due_immediately_after_snapshot(self, service) -> None:
        service.snapshot()
        assert service.due() is False

    def test_due_after_interval_elapsed(self, engine, mock_client) -> None:
        clock = FixedClock(_T0)
        transport = SupabaseProjectionTransport(client=mock_client)
        svc = ProjectionService(engine=engine, transport=transport, clock=clock)
        svc.snapshot()
        clock._dt = _T0 + timedelta(seconds=300)
        assert svc.due() is True

    def test_not_due_before_interval(self, engine, mock_client) -> None:
        clock = FixedClock(_T0)
        transport = SupabaseProjectionTransport(client=mock_client)
        svc = ProjectionService(engine=engine, transport=transport, clock=clock)
        svc.snapshot()
        clock._dt = _T0 + timedelta(seconds=299)
        assert svc.due() is False


class TestProjectionServiceSnapshot:
    def test_snapshot_returns_zero_with_no_events(self, service) -> None:
        count = service.snapshot()
        assert count == 0

    def test_snapshot_returns_event_count(self, service, engine) -> None:
        _insert_event(engine, "e1")
        _insert_event(engine, "e2")
        count = service.snapshot()
        assert count == 2

    def test_snapshot_upserts_to_mock_client(self, service, engine, mock_client) -> None:
        _insert_event(engine, "s1", event_type="startup")
        service.snapshot()
        stored = mock_client.rows("supervisor_events")
        assert len(stored) == 1
        assert stored[0]["supervisor_event_id"] == "s1"

    def test_snapshot_idempotent_on_same_data(self, service, engine, mock_client) -> None:
        _insert_event(engine, "s1")
        service.snapshot()
        service.snapshot()
        stored = mock_client.rows("supervisor_events")
        assert len(stored) == 1

    def test_snapshot_fail_open_on_missing_table(self, mock_client) -> None:
        bad_engine = create_engine("sqlite:///:memory:")
        transport = SupabaseProjectionTransport(client=mock_client)
        svc = ProjectionService(engine=bad_engine, transport=transport, clock=FixedClock(_T0))
        count = svc.snapshot()
        assert count == 0

    def test_snapshot_updates_last_snapshot_timestamp(self, service) -> None:
        assert service._last_snapshot is None
        service.snapshot()
        assert service._last_snapshot is not None

    def test_second_snapshot_upserts_all_rows(self, engine, mock_client) -> None:
        clock = FixedClock(_T0)
        transport = SupabaseProjectionTransport(client=mock_client)
        svc = ProjectionService(engine=engine, transport=transport, clock=clock)
        _insert_event(engine, "e1")
        svc.snapshot()
        _insert_event(engine, "e2")
        clock._dt = _T0 + timedelta(seconds=300)
        count = svc.snapshot()
        assert count == 2
        assert len(mock_client.rows("supervisor_events")) == 2
