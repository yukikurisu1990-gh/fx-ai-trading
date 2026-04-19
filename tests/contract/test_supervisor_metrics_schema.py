"""Contract tests: MetricsLoop 9-item schema (M16 / M-METRIC-1).

Verifies:
  1. MetricsCollector.collect() returns dict with all 9 required keys.
  2. MetricsLoop.record() calls insert_event with event_type='metric_sample'.
  3. detail passed to insert_event contains all 9 metric keys.
  4. Caller-supplied metrics (cycle_duration_seconds, stream_heartbeat_age_seconds)
     are propagated into detail.
  5. MetricsLoop.record() returns True on success, False on DB failure.
  6. DB failure does not raise (fail-open).
  7. Supervisor.record_metrics() delegates to attached MetricsLoop.
  8. Supervisor.record_metrics() returns False when no loop attached.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.supervisor.metrics_loop import (
    _ALL_METRIC_KEYS,
    MetricsCollector,
    MetricsLoop,
)
from fx_ai_trading.supervisor.supervisor import Supervisor

_FIXED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_REQUIRED_KEYS = set(_ALL_METRIC_KEYS)


def _make_loop(*, raise_on_insert: bool = False) -> tuple[MetricsLoop, MagicMock]:
    collector = MetricsCollector(engine=None)
    repo = MagicMock()
    if raise_on_insert:
        repo.insert_event.side_effect = RuntimeError("db down")
    ctx = MagicMock()
    loop = MetricsLoop(collector=collector, repo=repo, context=ctx)
    return loop, repo


class TestMetricsCollectorSchema:
    def test_collect_returns_dict(self) -> None:
        collector = MetricsCollector(engine=None)
        result = collector.collect()
        assert isinstance(result, dict)

    def test_collect_has_all_9_keys(self) -> None:
        collector = MetricsCollector(engine=None)
        result = collector.collect()
        assert set(result.keys()) == _REQUIRED_KEYS

    def test_cycle_duration_propagated(self) -> None:
        collector = MetricsCollector(engine=None)
        result = collector.collect(cycle_duration_seconds=1.23)
        assert result["cycle_duration_seconds"] == pytest.approx(1.23)

    def test_stream_heartbeat_age_propagated(self) -> None:
        collector = MetricsCollector(engine=None)
        result = collector.collect(stream_heartbeat_age_seconds=45.0)
        assert result["stream_heartbeat_age_seconds"] == pytest.approx(45.0)

    def test_db_counts_none_when_no_engine(self) -> None:
        collector = MetricsCollector(engine=None)
        result = collector.collect()
        assert result["outbox_pending_count"] is None
        assert result["notification_outbox_pending_count"] is None
        assert result["active_positions_count"] is None
        assert result["concurrent_orders_pending_count"] is None
        assert result["db_connections_count"] is None


class TestMetricsLoopRecord:
    def test_record_calls_insert_event_with_metric_sample(self) -> None:
        loop, repo = _make_loop()
        loop.record(_FIXED_AT)
        repo.insert_event.assert_called_once()
        kwargs = repo.insert_event.call_args.kwargs
        assert kwargs["event_type"] == "metric_sample"

    def test_record_passes_event_time_utc(self) -> None:
        loop, repo = _make_loop()
        loop.record(_FIXED_AT)
        kwargs = repo.insert_event.call_args.kwargs
        assert kwargs["event_time_utc"] == _FIXED_AT

    def test_record_detail_has_all_9_keys(self) -> None:
        loop, repo = _make_loop()
        loop.record(_FIXED_AT)
        kwargs = repo.insert_event.call_args.kwargs
        assert set(kwargs["detail"].keys()) == _REQUIRED_KEYS

    def test_record_returns_true_on_success(self) -> None:
        loop, _ = _make_loop()
        result = loop.record(_FIXED_AT)
        assert result is True

    def test_record_returns_false_on_db_failure(self) -> None:
        loop, _ = _make_loop(raise_on_insert=True)
        result = loop.record(_FIXED_AT)
        assert result is False

    def test_record_does_not_raise_on_db_failure(self) -> None:
        loop, _ = _make_loop(raise_on_insert=True)
        loop.record(_FIXED_AT)  # must not raise

    def test_caller_supplied_cycle_duration_in_detail(self) -> None:
        loop, repo = _make_loop()
        loop.record(_FIXED_AT, cycle_duration_seconds=2.5)
        kwargs = repo.insert_event.call_args.kwargs
        assert kwargs["detail"]["cycle_duration_seconds"] == pytest.approx(2.5)

    def test_caller_supplied_heartbeat_age_in_detail(self) -> None:
        loop, repo = _make_loop()
        loop.record(_FIXED_AT, stream_heartbeat_age_seconds=30.0)
        kwargs = repo.insert_event.call_args.kwargs
        assert kwargs["detail"]["stream_heartbeat_age_seconds"] == pytest.approx(30.0)


class TestSupervisorMetricsIntegration:
    def test_record_metrics_returns_false_when_no_loop_attached(self) -> None:
        supervisor = Supervisor(clock=FixedClock(_FIXED_AT))
        result = supervisor.record_metrics()
        assert result is False

    def test_record_metrics_delegates_to_metrics_loop(self) -> None:
        supervisor = Supervisor(clock=FixedClock(_FIXED_AT))
        mock_loop = MagicMock()
        mock_loop.record.return_value = True
        supervisor.attach_metrics_loop(mock_loop)
        result = supervisor.record_metrics(cycle_duration_seconds=1.5)
        assert result is True
        mock_loop.record.assert_called_once_with(
            _FIXED_AT,
            cycle_duration_seconds=1.5,
            stream_heartbeat_age_seconds=None,
        )

    def test_record_metrics_returns_false_after_safe_stop(self) -> None:
        supervisor = Supervisor(clock=FixedClock(_FIXED_AT))
        supervisor._is_stopped = True
        mock_loop = MagicMock()
        supervisor.attach_metrics_loop(mock_loop)
        result = supervisor.record_metrics()
        assert result is False
        mock_loop.record.assert_not_called()
