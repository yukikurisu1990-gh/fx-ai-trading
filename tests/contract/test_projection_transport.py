"""Contract tests: ProjectionTransport Protocol (M23 / D3 §2.19).

Verifies that SupabaseProjectionTransport implements the Protocol contract:
- upsert() returns row count
- upsert() never raises (fail-open)
- upsert() with empty rows returns 0
- MockSupabaseClient correctly tracks stored rows
"""

from __future__ import annotations

import pytest

from fx_ai_trading.adapters.projector.supabase import (
    MockSupabaseClient,
    SupabaseProjectionTransport,
)


@pytest.fixture()
def mock_client() -> MockSupabaseClient:
    return MockSupabaseClient()


@pytest.fixture()
def transport(mock_client: MockSupabaseClient) -> SupabaseProjectionTransport:
    return SupabaseProjectionTransport(client=mock_client)


class TestProjectionTransportContract:
    def test_upsert_returns_row_count(self, transport, mock_client) -> None:
        rows = [{"supervisor_event_id": "a", "event_type": "startup"}]
        count = transport.upsert("supervisor_events", rows)
        assert count == 1

    def test_upsert_empty_rows_returns_zero(self, transport) -> None:
        count = transport.upsert("supervisor_events", [])
        assert count == 0

    def test_upsert_multiple_rows(self, transport, mock_client) -> None:
        rows = [
            {"supervisor_event_id": "a", "event_type": "startup"},
            {"supervisor_event_id": "b", "event_type": "safe_stop"},
        ]
        count = transport.upsert("supervisor_events", rows)
        assert count == 2

    def test_upsert_stores_rows_in_mock(self, transport, mock_client) -> None:
        rows = [{"supervisor_event_id": "x1", "event_type": "startup"}]
        transport.upsert("supervisor_events", rows)
        stored = mock_client.rows("supervisor_events")
        assert len(stored) == 1
        assert stored[0]["supervisor_event_id"] == "x1"

    def test_upsert_overwrites_by_pk(self, transport, mock_client) -> None:
        transport.upsert("supervisor_events", [{"supervisor_event_id": "z1", "val": "v1"}])
        transport.upsert("supervisor_events", [{"supervisor_event_id": "z1", "val": "v2"}])
        stored = mock_client.rows("supervisor_events")
        assert len(stored) == 1
        assert stored[0]["val"] == "v2"

    def test_upsert_fail_open_on_transport_error(self) -> None:
        class BrokenClient:
            def upsert(self, table, rows):
                raise RuntimeError("network error")

        transport = SupabaseProjectionTransport(client=BrokenClient())
        result = transport.upsert("supervisor_events", [{"id": "1"}])
        assert result == 0

    def test_mock_client_call_count(self, transport, mock_client) -> None:
        transport.upsert("supervisor_events", [{"supervisor_event_id": "a"}])
        transport.upsert("supervisor_events", [{"supervisor_event_id": "b"}])
        assert mock_client.call_count("supervisor_events") == 2

    def test_mock_client_rows_empty_when_no_upsert(self, mock_client) -> None:
        assert mock_client.rows("supervisor_events") == []
