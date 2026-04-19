"""Unit tests: CloseEventsRepository (M14 / M-EXIT-1).

Pure unit tests using MagicMock engine — no DATABASE_URL required.
Verifies that insert() and get_by_id() issue the correct SQL with correct params.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from fx_ai_trading.repositories.close_events import CloseEventsRepository

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _make_repo() -> tuple[CloseEventsRepository, MagicMock]:
    engine = MagicMock()
    conn_cm = MagicMock()
    conn_cm.__enter__ = MagicMock(return_value=MagicMock())
    conn_cm.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value = conn_cm
    engine.connect.return_value = conn_cm
    repo = CloseEventsRepository(engine=engine)
    return repo, engine


class TestCloseEventsRepositoryInsert:
    def test_insert_calls_engine_begin(self) -> None:
        repo, engine = _make_repo()
        repo.insert(
            close_event_id="evt-1",
            order_id="ord-1",
            primary_reason_code="tp",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            closed_at=_FIXED_AT,
        )
        engine.begin.assert_called_once()

    def test_insert_executes_insert_sql(self) -> None:
        repo, engine = _make_repo()
        conn = engine.begin.return_value.__enter__.return_value
        repo.insert(
            close_event_id="evt-1",
            order_id="ord-1",
            primary_reason_code="tp",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            closed_at=_FIXED_AT,
        )
        conn.execute.assert_called_once()
        call_args = conn.execute.call_args
        sql_str = str(call_args[0][0])
        assert "INSERT INTO close_events" in sql_str

    def test_insert_passes_close_event_id(self) -> None:
        repo, engine = _make_repo()
        conn = engine.begin.return_value.__enter__.return_value
        repo.insert(
            close_event_id="evt-unique-123",
            order_id="ord-1",
            primary_reason_code="sl",
            reasons=[{"priority": 1, "reason_code": "sl", "detail": ""}],
            closed_at=_FIXED_AT,
        )
        params = conn.execute.call_args[0][1]
        assert params["close_event_id"] == "evt-unique-123"
        assert params["order_id"] == "ord-1"
        assert params["primary_reason_code"] == "sl"

    def test_insert_serializes_reasons_as_json(self) -> None:
        repo, engine = _make_repo()
        conn = engine.begin.return_value.__enter__.return_value
        reasons = [{"priority": 1, "reason_code": "tp", "detail": ""}]
        repo.insert(
            close_event_id="evt-1",
            order_id="ord-1",
            primary_reason_code="tp",
            reasons=reasons,
            closed_at=_FIXED_AT,
        )
        params = conn.execute.call_args[0][1]
        reasons_param = params["reasons"]
        assert isinstance(reasons_param, str)
        parsed = json.loads(reasons_param)
        assert parsed[0]["reason_code"] == "tp"

    def test_insert_optional_fields_default_to_none(self) -> None:
        repo, engine = _make_repo()
        conn = engine.begin.return_value.__enter__.return_value
        repo.insert(
            close_event_id="evt-1",
            order_id="ord-1",
            primary_reason_code="tp",
            reasons=[],
            closed_at=_FIXED_AT,
        )
        params = conn.execute.call_args[0][1]
        assert params["position_snapshot_id"] is None
        assert params["pnl_realized"] is None
        assert params["correlation_id"] is None


class TestCloseEventsRepositoryGetById:
    def test_get_by_id_returns_none_when_not_found(self) -> None:
        repo, engine = _make_repo()
        conn = engine.connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = None
        result = repo.get_by_id("no-such-event")
        assert result is None

    def test_get_by_id_returns_dict_when_found(self) -> None:
        repo, engine = _make_repo()
        conn = engine.connect.return_value.__enter__.return_value
        reasons_json = json.dumps([{"priority": 1, "reason_code": "tp", "detail": ""}])
        conn.execute.return_value.fetchone.return_value = (
            "evt-1",
            "ord-1",
            None,
            reasons_json,
            "tp",
            _FIXED_AT,
            None,
            None,
        )
        result = repo.get_by_id("evt-1")
        assert result is not None
        assert result["close_event_id"] == "evt-1"
        assert result["primary_reason_code"] == "tp"
        assert isinstance(result["reasons"], list)
        assert result["reasons"][0]["reason_code"] == "tp"
