"""Unit tests: ``scripts/run_paper_loop`` (M9 paper-loop runner scaffold).

Pins the contract that the runner:
  - Resolves ``--interval`` / ``--instrument`` from CLI > env > defaults.
  - Fails fast (RuntimeError) when required OANDA env vars are missing.
  - Builds an ``OandaQuoteFeed`` against the supplied
    ``OandaAPIClient`` and attaches it through
    ``Supervisor.attach_exit_gate`` with the null-safe stubs so the
    tick is a wiring verification (no positions → empty results).
  - The cadence loop respects ``max_iterations`` and ``should_stop``,
    sleeps between ticks via the injected ``sleep_fn``, and emits one
    ``tick.completed`` log line per tick (plus one ``tick.exit_result``
    line per result, which in wiring-verification mode is zero).
  - SIGINT does not crash the process — it sets the loop's stop flag.

These tests do **not** touch real OANDA. The runner is driven through
its public seam (``parse_args`` / ``read_oanda_config_from_env`` /
``build_supervisor_with_oanda_feed`` / ``run_loop``) which accepts
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
# parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_defaults_when_no_argv_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PAPER_LOOP_INTERVAL_SECONDS", raising=False)
        monkeypatch.delenv("PAPER_LOOP_INSTRUMENT", raising=False)
        args = runner.parse_args([])
        assert args.interval_seconds == 5.0
        assert args.instrument == "EUR_USD"
        assert args.max_iterations == 0
        assert args.log_level == "INFO"
        assert args.log_filename == "paper_loop.jsonl"

    def test_env_overrides_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPER_LOOP_INTERVAL_SECONDS", "2.5")
        monkeypatch.setenv("PAPER_LOOP_INSTRUMENT", "USD_JPY")
        args = runner.parse_args([])
        assert args.interval_seconds == 2.5
        assert args.instrument == "USD_JPY"

    def test_cli_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAPER_LOOP_INTERVAL_SECONDS", "2.5")
        monkeypatch.setenv("PAPER_LOOP_INSTRUMENT", "USD_JPY")
        args = runner.parse_args(["--interval", "1", "--instrument", "GBP_USD"])
        assert args.interval_seconds == 1.0
        assert args.instrument == "GBP_USD"

    def test_max_iterations_threaded_through(self) -> None:
        args = runner.parse_args(["--max-iterations", "3"])
        assert args.max_iterations == 3

    def test_non_positive_interval_errors(self) -> None:
        with pytest.raises(SystemExit):
            runner.parse_args(["--interval", "0"])

    def test_negative_max_iterations_errors(self) -> None:
        with pytest.raises(SystemExit):
            runner.parse_args(["--max-iterations", "-1"])


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
# build_supervisor_with_oanda_feed
# ---------------------------------------------------------------------------


class TestBuildSupervisorWithOandaFeed:
    def test_returns_supervisor_and_oanda_feed_with_attach_wired(self) -> None:
        fake_api = MagicMock()
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        oanda = runner.OandaConfig(
            access_token="tok",
            account_id="101-001-1234567-001",
            environment="practice",
        )
        supervisor, feed = runner.build_supervisor_with_oanda_feed(
            oanda=oanda, instrument="EUR_USD", api_client=api_client
        )
        assert isinstance(feed, OandaQuoteFeed)
        # Tick should be safe to call immediately and return [] because
        # the null state manager reports no positions.
        assert supervisor.run_exit_gate_tick() == []
        # The fake api must NOT have been touched — wiring verification
        # mode never reaches get_quote.
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
        # Two ticks ran; the post-tick should_stop() check breaks before sleep.
        assert iterations == 2
        assert supervisor.run_exit_gate_tick.call_count == 2
        # sleep_fn was called once after the first tick, then the second
        # tick's post-check triggered before the second sleep.
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

    def test_happy_path_with_env_runs_one_tick_and_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
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
