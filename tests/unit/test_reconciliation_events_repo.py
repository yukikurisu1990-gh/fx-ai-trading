"""Unit tests: ReconciliationEventsRepository (Cycle 6.8 / I-06).

Pure unit tests using MagicMock engine — no DATABASE_URL required.
Verifies that insert() issues the correct INSERT SQL with the expected
parameter shape and that the JSON ``detail`` payload is serialised.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from fx_ai_trading.repositories.reconciliation_events import (
    ReconciliationEventsRepository,
)

_FIXED_AT = datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)


def _make_repo() -> tuple[ReconciliationEventsRepository, MagicMock]:
    engine = MagicMock()
    conn_cm = MagicMock()
    conn_cm.__enter__ = MagicMock(return_value=MagicMock())
    conn_cm.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value = conn_cm
    repo = ReconciliationEventsRepository(engine=engine)
    return repo, engine


class TestReconciliationEventsRepositoryInsert:
    def test_insert_executes_insert_sql_with_required_columns(self) -> None:
        repo, engine = _make_repo()
        conn = engine.begin.return_value.__enter__.return_value
        repo.insert(
            trigger_reason="startup",
            action_taken="MARK_FAILED",
            event_time_utc=_FIXED_AT,
            order_id="ord-1",
            detail={"db_status": "PENDING", "broker_status": None},
        )
        conn.execute.assert_called_once()
        sql_str = str(conn.execute.call_args[0][0])
        assert "INSERT INTO reconciliation_events" in sql_str
        params = conn.execute.call_args[0][1]
        assert params["trigger_reason"] == "startup"
        assert params["action_taken"] == "MARK_FAILED"
        assert params["order_id"] == "ord-1"
        assert params["event_time_utc"] == _FIXED_AT
        assert params["position_snapshot_id"] is None

    def test_insert_serializes_detail_as_json_string(self) -> None:
        repo, engine = _make_repo()
        conn = engine.begin.return_value.__enter__.return_value
        detail = {"count": 3, "table_names": ["a", "b"]}
        repo.insert(
            trigger_reason="outbox_stale",
            action_taken="outbox_stale_detected",
            event_time_utc=_FIXED_AT,
            detail=detail,
        )
        params = conn.execute.call_args[0][1]
        assert isinstance(params["detail"], str)
        assert json.loads(params["detail"]) == detail
        # order_id omitted ⇒ None
        assert params["order_id"] is None

    def test_insert_generates_uuid_when_id_not_provided_and_returns_it(self) -> None:
        repo, engine = _make_repo()
        conn = engine.begin.return_value.__enter__.return_value
        returned = repo.insert(
            trigger_reason="midrun_heartbeat_gap",
            action_taken="MARK_FILLED",
            event_time_utc=_FIXED_AT,
            order_id="ord-9",
        )
        params = conn.execute.call_args[0][1]
        assert params["reconciliation_event_id"] == returned
        # Generated value should be a UUID string (36 chars with 4 hyphens).
        assert isinstance(returned, str)
        assert len(returned) == 36
        assert returned.count("-") == 4
        # Detail omitted ⇒ None (NOT the JSON string "null").
        assert params["detail"] is None
