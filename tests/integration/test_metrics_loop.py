"""Integration tests: MetricsLoop fake-clock 60s recording (M16 / M-METRIC-1).

Verifies:
  1. Each record() call produces exactly one insert_event call.
  2. Successive record() calls produce independent metric_sample rows.
  3. MetricsLoop with real MetricsCollector (no engine) collects without error.
  4. event_type is always 'metric_sample'.
  5. detail schema is stable across multiple calls.
  6. Supervisor.record_metrics() respects is_stopped flag.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.supervisor.metrics_loop import (
    _ALL_METRIC_KEYS,
    MetricsCollector,
    MetricsLoop,
)
from fx_ai_trading.supervisor.supervisor import Supervisor


class _TickClock:
    """Deterministic clock that advances by 60s on each call to now()."""

    def __init__(self) -> None:
        self._dt = datetime(2026, 1, 1, tzinfo=UTC)
        self._calls = 0

    def now(self) -> datetime:
        dt = self._dt + timedelta(seconds=60 * self._calls)
        self._calls += 1
        return dt


def _make_loop() -> tuple[MetricsLoop, MagicMock]:
    collector = MetricsCollector(engine=None)
    repo = MagicMock()
    ctx = MagicMock()
    loop = MetricsLoop(collector=collector, repo=repo, context=ctx)
    return loop, repo


class TestSingleRecord:
    def test_single_record_produces_one_insert(self) -> None:
        loop, repo = _make_loop()
        at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        loop.record(at)
        assert repo.insert_event.call_count == 1

    def test_single_record_event_type_is_metric_sample(self) -> None:
        loop, repo = _make_loop()
        at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        loop.record(at)
        kwargs = repo.insert_event.call_args.kwargs
        assert kwargs["event_type"] == "metric_sample"

    def test_single_record_detail_is_dict(self) -> None:
        loop, repo = _make_loop()
        at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        loop.record(at)
        kwargs = repo.insert_event.call_args.kwargs
        assert isinstance(kwargs["detail"], dict)


class TestMultipleRecords:
    def test_three_ticks_produce_three_inserts(self) -> None:
        loop, repo = _make_loop()
        clock = _TickClock()
        for _ in range(3):
            loop.record(clock.now())
        assert repo.insert_event.call_count == 3

    def test_each_tick_has_correct_timestamp(self) -> None:
        loop, repo = _make_loop()
        base = datetime(2026, 1, 1, tzinfo=UTC)
        timestamps = [base + timedelta(seconds=60 * i) for i in range(3)]
        for ts in timestamps:
            loop.record(ts)
        calls = repo.insert_event.call_args_list
        recorded = [c.kwargs["event_time_utc"] for c in calls]
        assert recorded == timestamps

    def test_schema_stable_across_ticks(self) -> None:
        loop, repo = _make_loop()
        clock = _TickClock()
        for _ in range(3):
            loop.record(clock.now())
        required = set(_ALL_METRIC_KEYS)
        for c in repo.insert_event.call_args_list:
            assert set(c.kwargs["detail"].keys()) == required


class TestFailOpen:
    def test_db_failure_does_not_propagate(self) -> None:
        loop, repo = _make_loop()
        repo.insert_event.side_effect = RuntimeError("db unavailable")
        at = datetime(2026, 1, 1, tzinfo=UTC)
        loop.record(at)  # must not raise

    def test_db_failure_returns_false(self) -> None:
        loop, repo = _make_loop()
        repo.insert_event.side_effect = Exception("connection lost")
        result = loop.record(datetime(2026, 1, 1, tzinfo=UTC))
        assert result is False


class TestSupervisorRecordMetricsLifecycle:
    def test_record_metrics_false_before_attach(self) -> None:
        supervisor = Supervisor(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
        assert supervisor.record_metrics() is False

    def test_record_metrics_true_after_attach(self) -> None:
        loop, repo = _make_loop()
        clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
        supervisor = Supervisor(clock=clock)
        supervisor.attach_metrics_loop(loop)
        result = supervisor.record_metrics()
        assert result is True
        assert repo.insert_event.call_count == 1

    def test_record_metrics_false_after_safe_stop(self) -> None:
        loop, repo = _make_loop()
        clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
        supervisor = Supervisor(clock=clock)
        supervisor.attach_metrics_loop(loop)
        supervisor._is_stopped = True
        result = supervisor.record_metrics()
        assert result is False
        repo.insert_event.assert_not_called()
