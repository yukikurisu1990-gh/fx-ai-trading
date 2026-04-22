"""Unit tests: ``scripts/run_paper_loop`` (M9 paper-stack bootstrap).

Pins the contract that the runner:
  - Resolves CLI / env / defaults precedence (interval, instrument,
    max_iterations, max_holding_seconds).
  - Fails fast (rc=2) when required OANDA env vars are missing.
  - Fails fast (rc=2) when ``DATABASE_URL`` is missing.
  - Builds an ``OandaQuoteFeed`` against the supplied
    ``OandaAPIClient`` and attaches it through
    ``Supervisor.attach_exit_gate`` with the production paper stack
    (``PaperBroker`` + ``StateManager`` + ``ExitPolicyService``).  With
    no positions seeded in the DB, ``run_exit_gate_tick`` returns ``[]``
    and the OANDA client is never called.
  - The cadence loop respects ``max_iterations`` and ``should_stop``,
    sleeps between ticks via the injected ``sleep_fn``, and emits one
    ``tick.completed`` log line per tick (plus one ``tick.exit_result``
    line per result).
  - SIGINT does not crash the process — it sets the loop's stop flag.

These tests do **not** touch real OANDA or a real Postgres.  The runner
is driven through its public seams (``parse_args`` /
``read_oanda_config_from_env`` / ``build_db_engine`` /
``build_supervisor_with_paper_stack`` / ``run_loop``) which all accept
test doubles.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed


def _load_runner_module():
    """Import ``scripts/run_paper_loop.py`` by file path.

    The ``scripts/`` directory is not on the package path, so a normal
    ``import`` would fail.  Loading by spec keeps the runner reachable
    from tests without making it a top-level package."""
    repo_root = Path(__file__).resolve().parents[2]
    runner_path = repo_root / "scripts" / "run_paper_loop.py"
    spec = importlib.util.spec_from_file_location("scripts_run_paper_loop", runner_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass()/typing introspection that walks
    # ``sys.modules[cls.__module__]`` (Python 3.12 stdlib) finds us.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner_module()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


# Minimal DDL for StateManager.open_position_details() to execute.  We
# don't seed any rows here — these unit tests verify the wiring up to
# the empty-positions branch; the integration test exercises the full
# close path (see tests/integration/test_paper_loop_close_path.py).
_DDL_POSITIONS = """
CREATE TABLE positions (
    position_snapshot_id TEXT PRIMARY KEY,
    order_id             TEXT,
    account_id           TEXT NOT NULL,
    instrument           TEXT NOT NULL,
    event_type           TEXT NOT NULL,
    units                NUMERIC(18,4) NOT NULL,
    avg_price            NUMERIC(18,8),
    unrealized_pl        NUMERIC(18,8),
    realized_pl          NUMERIC(18,8),
    event_time_utc       TEXT NOT NULL,
    correlation_id       TEXT
)
"""

_DDL_ORDERS = """
CREATE TABLE orders (
    order_id          TEXT PRIMARY KEY,
    client_order_id   TEXT,
    trading_signal_id TEXT,
    account_id        TEXT NOT NULL,
    instrument        TEXT NOT NULL,
    account_type      TEXT NOT NULL,
    order_type        TEXT NOT NULL,
    direction         TEXT NOT NULL,
    units             NUMERIC(18,4) NOT NULL,
    status            TEXT NOT NULL DEFAULT 'PENDING',
    submitted_at      TEXT,
    filled_at         TEXT,
    canceled_at       TEXT,
    correlation_id    TEXT,
    created_at        TEXT NOT NULL
)
"""


@pytest.fixture
def empty_engine() -> Iterator[Engine]:
    """In-memory SQLite engine with positions+orders schema, no rows."""
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_ORDERS))
        conn.execute(text(_DDL_POSITIONS))
    try:
        yield eng
    finally:
        eng.dispose()


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_defaults_when_no_argv_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PAPER_LOOP_INTERVAL_SECONDS", raising=False)
        monkeypatch.delenv("PAPER_LOOP_INSTRUMENT", raising=False)
        monkeypatch.delenv("PAPER_LOOP_MAX_HOLDING_SECONDS", raising=False)
        args = runner.parse_args([])
        assert args.interval_seconds == 5.0
        assert args.instrument == "EUR_USD"
        assert args.max_iterations == 0
        assert args.max_holding_seconds == 86400
        assert args.log_level == "INFO"
        assert args.log_filename == "paper_loop.jsonl"

    def test_env_overrides_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPER_LOOP_INTERVAL_SECONDS", "2.5")
        monkeypatch.setenv("PAPER_LOOP_INSTRUMENT", "USD_JPY")
        monkeypatch.setenv("PAPER_LOOP_MAX_HOLDING_SECONDS", "3600")
        args = runner.parse_args([])
        assert args.interval_seconds == 2.5
        assert args.instrument == "USD_JPY"
        assert args.max_holding_seconds == 3600

    def test_cli_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPER_LOOP_INTERVAL_SECONDS", "2.5")
        monkeypatch.setenv("PAPER_LOOP_INSTRUMENT", "USD_JPY")
        monkeypatch.setenv("PAPER_LOOP_MAX_HOLDING_SECONDS", "3600")
        args = runner.parse_args(
            [
                "--interval",
                "1",
                "--instrument",
                "GBP_USD",
                "--max-holding-seconds",
                "7200",
            ]
        )
        assert args.interval_seconds == 1.0
        assert args.instrument == "GBP_USD"
        assert args.max_holding_seconds == 7200

    def test_max_iterations_threaded_through(self) -> None:
        args = runner.parse_args(["--max-iterations", "3"])
        assert args.max_iterations == 3

    def test_non_positive_interval_errors(self) -> None:
        with pytest.raises(SystemExit):
            runner.parse_args(["--interval", "0"])

    def test_negative_max_iterations_errors(self) -> None:
        with pytest.raises(SystemExit):
            runner.parse_args(["--max-iterations", "-1"])

    def test_non_positive_max_holding_seconds_errors(self) -> None:
        with pytest.raises(SystemExit):
            runner.parse_args(["--max-holding-seconds", "0"])


# ---------------------------------------------------------------------------
# read_oanda_config_from_env
# ---------------------------------------------------------------------------


class TestReadOandaConfigFromEnv:
    def test_happy_path_with_explicit_env(self) -> None:
        cfg = runner.read_oanda_config_from_env(
            env={
                "OANDA_ACCESS_TOKEN": "tok",
                "OANDA_ACCOUNT_ID": "101-001-1234567-001",
                "OANDA_ENVIRONMENT": "practice",
            }
        )
        assert cfg.access_token == "tok"
        assert cfg.account_id == "101-001-1234567-001"
        assert cfg.environment == "practice"

    def test_environment_defaults_to_practice(self) -> None:
        cfg = runner.read_oanda_config_from_env(
            env={"OANDA_ACCESS_TOKEN": "tok", "OANDA_ACCOUNT_ID": "acct"}
        )
        assert cfg.environment == "practice"

    def test_missing_token_raises(self) -> None:
        with pytest.raises(RuntimeError, match="OANDA_ACCESS_TOKEN"):
            runner.read_oanda_config_from_env(env={"OANDA_ACCOUNT_ID": "acct"})

    def test_missing_account_id_raises(self) -> None:
        with pytest.raises(RuntimeError, match="OANDA_ACCOUNT_ID"):
            runner.read_oanda_config_from_env(env={"OANDA_ACCESS_TOKEN": "tok"})

    def test_blank_values_treated_as_missing(self) -> None:
        with pytest.raises(RuntimeError):
            runner.read_oanda_config_from_env(
                env={"OANDA_ACCESS_TOKEN": "  ", "OANDA_ACCOUNT_ID": "acct"}
            )


# ---------------------------------------------------------------------------
# build_supervisor_with_paper_stack
# ---------------------------------------------------------------------------


class TestBuildSupervisorWithPaperStack:
    def test_returns_supervisor_and_oanda_feed(self, empty_engine: Engine) -> None:
        from fx_ai_trading.adapters.broker.paper import PaperBroker
        from fx_ai_trading.services.exit_policy import ExitPolicyService
        from fx_ai_trading.services.state_manager import StateManager

        fake_api = MagicMock()
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        oanda = runner.OandaConfig(
            access_token="tok",
            account_id="acct-bootstrap-1",
            environment="practice",
        )
        supervisor, feed = runner.build_supervisor_with_paper_stack(
            oanda=oanda,
            instrument="EUR_USD",
            engine=empty_engine,
            api_client=api_client,
        )
        assert isinstance(feed, OandaQuoteFeed)

        # Sanity-check the wired components match the production stack.
        cfg = supervisor._exit_gate  # type: ignore[attr-defined]
        assert isinstance(cfg.broker, PaperBroker)
        assert isinstance(cfg.state_manager, StateManager)
        assert isinstance(cfg.exit_policy, ExitPolicyService)
        assert cfg.account_id == "acct-bootstrap-1"

    def test_tick_returns_empty_when_no_positions(self, empty_engine: Engine) -> None:
        fake_api = MagicMock()
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        oanda = runner.OandaConfig(
            access_token="tok",
            account_id="acct-bootstrap-2",
            environment="practice",
        )
        supervisor, _feed = runner.build_supervisor_with_paper_stack(
            oanda=oanda,
            instrument="EUR_USD",
            engine=empty_engine,
            api_client=api_client,
        )
        # No positions seeded → state_manager.open_position_details()
        # returns [] → quote_feed is never queried → fake_api is never
        # touched.  This is the wiring smoke test for the bootstrap.
        assert supervisor.run_exit_gate_tick() == []
        fake_api.request.assert_not_called()


# ---------------------------------------------------------------------------
# run_loop
# ---------------------------------------------------------------------------


def _make_supervisor_with_results(results_per_tick: list[list]) -> MagicMock:
    supervisor = MagicMock()
    iterator = iter(results_per_tick)

    def _tick() -> list:
        try:
            return next(iterator)
        except StopIteration:
            return []

    supervisor.run_exit_gate_tick.side_effect = _tick
    return supervisor


class _CountingSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


class _FakeMonotonic:
    def __init__(self, increments: list[float]) -> None:
        self._values: Iterator[float] = iter(increments)

    def __call__(self) -> float:
        return next(self._values)


class TestRunLoop:
    def test_stops_after_max_iterations(self, caplog: pytest.LogCaptureFixture) -> None:
        supervisor = _make_supervisor_with_results([[], [], []])
        sleep = _CountingSleep()
        log = logging.getLogger("test.runner.max_iterations")
        with caplog.at_level(logging.INFO, logger=log.name):
            iterations = runner.run_loop(
                supervisor=supervisor,
                interval_seconds=0.01,
                max_iterations=3,
                log=log,
                should_stop=lambda: False,
                sleep_fn=sleep,
                monotonic_fn=_FakeMonotonic([0.0, 0.001] * 3),
            )
        assert iterations == 3
        assert supervisor.run_exit_gate_tick.call_count == 3
        # No sleep after the final tick — the loop breaks before sleep().
        assert sleep.calls == [0.01, 0.01]

    def test_should_stop_breaks_loop_before_first_tick(self) -> None:
        supervisor = MagicMock()
        sleep = _CountingSleep()
        log = logging.getLogger("test.runner.preempt")
        iterations = runner.run_loop(
            supervisor=supervisor,
            interval_seconds=1.0,
            max_iterations=0,
            log=log,
            should_stop=lambda: True,
            sleep_fn=sleep,
            monotonic_fn=_FakeMonotonic([]),
        )
        assert iterations == 0
        supervisor.run_exit_gate_tick.assert_not_called()
        assert sleep.calls == []

    def test_should_stop_after_n_ticks_short_circuits_sleep(self) -> None:
        supervisor = _make_supervisor_with_results([[], [], []])
        sleep = _CountingSleep()
        log = logging.getLogger("test.runner.midflight")
        # Sequence: top-check (enter tick 1) → post-check (continue) →
        # top-check (enter tick 2) → post-check (break).  Four reads.
        flips = iter([False, False, False, True])
        iterations = runner.run_loop(
            supervisor=supervisor,
            interval_seconds=1.0,
            max_iterations=0,
            log=log,
            should_stop=lambda: next(flips),
            sleep_fn=sleep,
            monotonic_fn=_FakeMonotonic([0.0, 0.001, 0.0, 0.001]),
        )
        assert iterations == 2
        assert supervisor.run_exit_gate_tick.call_count == 2
        assert sleep.calls == [1.0]

    def test_emits_tick_completed_with_iteration_and_results_count(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        supervisor = _make_supervisor_with_results([[]])
        log = logging.getLogger("test.runner.tickcompleted")
        log.propagate = True
        with caplog.at_level(logging.INFO, logger=log.name):
            runner.run_loop(
                supervisor=supervisor,
                interval_seconds=0.01,
                max_iterations=1,
                log=log,
                should_stop=lambda: False,
                sleep_fn=lambda _s: None,
                monotonic_fn=_FakeMonotonic([0.0, 0.002]),
            )
        records = [r for r in caplog.records if r.message == "tick.completed"]
        assert len(records) == 1
        rec = records[0]
        assert rec.iteration == 1
        assert rec.results_count == 0
        assert rec.tick_duration_ms == pytest.approx(2.0, abs=0.5)

    def test_emits_one_exit_result_line_per_result(self, caplog: pytest.LogCaptureFixture) -> None:
        from fx_ai_trading.services.exit_gate_runner import ExitGateRunResult

        results = [
            ExitGateRunResult(
                instrument="EUR_USD",
                order_id="ord-1",
                outcome="closed",
                primary_reason="tp",
            ),
            ExitGateRunResult(
                instrument="USD_JPY",
                order_id="ord-2",
                outcome="noop_stale_quote",
                primary_reason=None,
            ),
        ]
        supervisor = _make_supervisor_with_results([results])
        log = logging.getLogger("test.runner.exitresults")
        log.propagate = True
        with caplog.at_level(logging.INFO, logger=log.name):
            runner.run_loop(
                supervisor=supervisor,
                interval_seconds=0.01,
                max_iterations=1,
                log=log,
                should_stop=lambda: False,
                sleep_fn=lambda _s: None,
                monotonic_fn=_FakeMonotonic([0.0, 0.001]),
            )
        exit_records = [r for r in caplog.records if r.message == "tick.exit_result"]
        assert len(exit_records) == 2
        assert {r.outcome for r in exit_records} == {"closed", "noop_stale_quote"}
        assert {r.instrument for r in exit_records} == {"EUR_USD", "USD_JPY"}

    def test_tick_exception_logged_as_error_and_loop_continues(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        supervisor = MagicMock()
        supervisor.run_exit_gate_tick.side_effect = [RuntimeError("transient"), []]
        log = logging.getLogger("test.runner.exception")
        log.propagate = True
        with caplog.at_level(logging.INFO, logger=log.name):
            iterations = runner.run_loop(
                supervisor=supervisor,
                interval_seconds=0.01,
                max_iterations=2,
                log=log,
                should_stop=lambda: False,
                sleep_fn=lambda _s: None,
                monotonic_fn=_FakeMonotonic([0.0, 0.001, 0.0, 0.001]),
            )
        assert iterations == 2
        error_records = [r for r in caplog.records if r.message == "tick.error"]
        assert len(error_records) == 1
        assert error_records[0].levelno == logging.ERROR


# ---------------------------------------------------------------------------
# main() smoke
# ---------------------------------------------------------------------------


class TestMainSmoke:
    def test_returns_2_when_oanda_env_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("OANDA_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("OANDA_ACCOUNT_ID", raising=False)
        rc = runner.main(
            [
                "--max-iterations",
                "1",
                "--interval",
                "0.01",
                "--log-dir",
                str(tmp_path),
            ]
        )
        assert rc == 2

    def test_returns_2_when_database_url_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # OANDA env present so we get past that check and hit the DB
        # check.  build_db_engine raises RuntimeError because
        # get_database_url() does, and main maps it to rc=2.
        monkeypatch.setenv("OANDA_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "101-001-1234567-001")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        rc = runner.main(
            [
                "--max-iterations",
                "1",
                "--interval",
                "0.01",
                "--log-dir",
                str(tmp_path),
            ]
        )
        assert rc == 2

    def test_happy_path_with_env_runs_one_tick_and_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        empty_engine: Engine,
    ) -> None:
        monkeypatch.setenv("OANDA_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("OANDA_ACCOUNT_ID", "101-001-1234567-001")
        # Substitute the OANDA constructor so we don't hit oandapyV20.
        monkeypatch.setattr(
            runner,
            "OandaAPIClient",
            lambda **kwargs: OandaAPIClient(
                access_token="tok", environment="practice", api=MagicMock()
            ),
        )
        # Substitute build_db_engine so we don't need a real DATABASE_URL
        # or a real Postgres.  The fixture engine has the schema needed
        # for StateManager.open_position_details() to execute.
        monkeypatch.setattr(runner, "build_db_engine", lambda: empty_engine)
        rc = runner.main(
            [
                "--max-iterations",
                "1",
                "--interval",
                "0.01",
                "--log-dir",
                str(tmp_path),
            ]
        )
        assert rc == 0
        assert (tmp_path / "paper_loop.jsonl").exists()


# ---------------------------------------------------------------------------
# SIGINT handler
# ---------------------------------------------------------------------------


class TestSigintHandler:
    def test_handler_sets_stop_flag_and_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        flag = [False]
        log = logging.getLogger("test.runner.sigint")
        log.propagate = True
        with caplog.at_level(logging.INFO, logger=log.name):
            runner._install_sigint_handler(flag, log)
            # We don't actually raise SIGINT (would terminate the test
            # process); call the handler directly via the registered
            # signal handler getter.  signal.getsignal returns the
            # callable we registered.
            import signal as _signal

            handler = _signal.getsignal(_signal.SIGINT)
            assert callable(handler)
            handler(_signal.SIGINT, None)
        assert flag[0] is True
        assert any(
            r.message == "shutdown.signal_received"
            and getattr(r, "signum", None) == int(_signal.SIGINT)
            for r in caplog.records
        )


@pytest.fixture(autouse=True)
def _restore_sigint_default() -> Iterator[None]:
    """Reset SIGINT after every test so a leaked handler doesn't leak."""
    import signal as _signal

    previous = _signal.getsignal(_signal.SIGINT)
    yield
    _signal.signal(_signal.SIGINT, previous)
