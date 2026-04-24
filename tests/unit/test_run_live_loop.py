"""Unit tests: ``scripts/run_live_loop`` (M9 live-demo runner).

Pins the contract that the live runner:
  - Resolves CLI / env / defaults precedence using the ``LIVE_LOOP_*``
    env namespace and the ``live_loop.jsonl`` default log filename
    (distinct from the paper runner so dashboards / runbooks /
    log-parsing scripts can disambiguate).
  - Fails fast (rc=2) when required OANDA env vars are missing.
  - Fails fast (rc=2) when ``DATABASE_URL`` is missing.
  - Builds an ``OandaBroker`` (NOT ``PaperBroker``) with
    ``account_type="demo"`` hard-pinned, plus an ``OandaQuoteFeed`` over
    the same injected ``OandaAPIClient``.  Both are wired through
    ``Supervisor.attach_exit_gate``; with no positions seeded in the DB,
    ``run_exit_gate_tick`` returns ``[]`` and the OANDA client is never
    called.
  - Error messages from ``read_oanda_config_from_env`` /
    ``build_db_engine`` carry the ``run_live_loop:`` prefix so an
    operator triaging a missing-env log line can tell which runner
    crashed (vs the paper runner's ``run_paper_loop:`` prefix).

These tests do **not** touch real OANDA or a real Postgres.  The runner
is driven through its public seams, all of which accept test doubles.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from fx_ai_trading.adapters.broker.oanda import OandaBroker
from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed


def _load_runner_module():
    """Import ``scripts/run_live_loop.py`` by file path.

    The ``scripts/`` directory is not on the package path, so a normal
    ``import`` would fail.  Loading by spec keeps the runner reachable
    from tests without making it a top-level package."""
    repo_root = Path(__file__).resolve().parents[2]
    runner_path = repo_root / "scripts" / "run_live_loop.py"
    spec = importlib.util.spec_from_file_location("scripts_run_live_loop", runner_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner_module()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


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
        monkeypatch.delenv("LIVE_LOOP_INTERVAL_SECONDS", raising=False)
        monkeypatch.delenv("LIVE_LOOP_INSTRUMENT", raising=False)
        monkeypatch.delenv("LIVE_LOOP_MAX_HOLDING_SECONDS", raising=False)
        args = runner.parse_args([])
        assert args.interval_seconds == 5.0
        assert args.instrument == "EUR_USD"
        assert args.max_iterations == 0
        assert args.max_holding_seconds == 86400
        assert args.log_level == "INFO"
        # The live runner MUST default to live_loop.jsonl, not
        # paper_loop.jsonl — this is the only way an operator (or a jq
        # script) can tell which runner produced a given log file.
        assert args.log_filename == "live_loop.jsonl"

    def test_env_overrides_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LIVE_LOOP_INTERVAL_SECONDS", "2.5")
        monkeypatch.setenv("LIVE_LOOP_INSTRUMENT", "USD_JPY")
        monkeypatch.setenv("LIVE_LOOP_MAX_HOLDING_SECONDS", "3600")
        args = runner.parse_args([])
        assert args.interval_seconds == 2.5
        assert args.instrument == "USD_JPY"
        assert args.max_holding_seconds == 3600

    def test_paper_env_does_not_leak_into_live(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If both PAPER_LOOP_* and LIVE_LOOP_* are set, the live runner
        must read its own namespace.  Guards against a copy-paste bug
        where the live runner accidentally references PAPER_LOOP_*."""
        monkeypatch.setenv("PAPER_LOOP_INTERVAL_SECONDS", "99.0")
        monkeypatch.setenv("PAPER_LOOP_INSTRUMENT", "GBP_USD")
        monkeypatch.delenv("LIVE_LOOP_INTERVAL_SECONDS", raising=False)
        monkeypatch.delenv("LIVE_LOOP_INSTRUMENT", raising=False)
        args = runner.parse_args([])
        assert args.interval_seconds == 5.0
        assert args.instrument == "EUR_USD"

    def test_cli_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LIVE_LOOP_INTERVAL_SECONDS", "2.5")
        monkeypatch.setenv("LIVE_LOOP_INSTRUMENT", "USD_JPY")
        monkeypatch.setenv("LIVE_LOOP_MAX_HOLDING_SECONDS", "3600")
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

    def test_missing_token_raises_with_runner_prefix(self) -> None:
        with pytest.raises(RuntimeError, match=r"run_live_loop:.*OANDA_ACCESS_TOKEN"):
            runner.read_oanda_config_from_env(env={"OANDA_ACCOUNT_ID": "acct"})

    def test_missing_account_id_raises_with_runner_prefix(self) -> None:
        with pytest.raises(RuntimeError, match=r"run_live_loop:.*OANDA_ACCOUNT_ID"):
            runner.read_oanda_config_from_env(env={"OANDA_ACCESS_TOKEN": "tok"})

    def test_blank_values_treated_as_missing(self) -> None:
        with pytest.raises(RuntimeError, match=r"run_live_loop:"):
            runner.read_oanda_config_from_env(
                env={"OANDA_ACCESS_TOKEN": "  ", "OANDA_ACCOUNT_ID": "acct"}
            )


# ---------------------------------------------------------------------------
# build_db_engine
# ---------------------------------------------------------------------------


class TestBuildDbEngine:
    def test_missing_database_url_raises_with_runner_prefix(self) -> None:
        with pytest.raises(RuntimeError, match=r"run_live_loop:.*DATABASE_URL"):
            runner.build_db_engine(env={})

    def test_blank_database_url_treated_as_missing(self) -> None:
        with pytest.raises(RuntimeError, match=r"run_live_loop:"):
            runner.build_db_engine(env={"DATABASE_URL": "   "})


# ---------------------------------------------------------------------------
# build_supervisor_with_live_demo_stack
# ---------------------------------------------------------------------------


class TestBuildSupervisorWithLiveDemoStack:
    def test_returns_supervisor_and_oanda_feed(self, empty_engine: Engine) -> None:
        from fx_ai_trading.services.exit_policy import ExitPolicyService
        from fx_ai_trading.services.state_manager import StateManager

        fake_api = MagicMock()
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        oanda = runner.OandaConfig(
            access_token="tok",
            account_id="acct-live-bootstrap-1",
            environment="practice",
        )
        supervisor, feed = runner.build_supervisor_with_live_demo_stack(
            oanda=oanda,
            instrument="EUR_USD",
            engine=empty_engine,
            api_client=api_client,
        )
        assert isinstance(feed, OandaQuoteFeed)

        cfg = supervisor._exit_gate  # type: ignore[attr-defined]
        # The defining contract of the live runner: broker is OandaBroker,
        # NOT PaperBroker.  If a future refactor accidentally swapped
        # this back to paper, real-money risk would still be gated by
        # the 6.18 invariant — but the runner would silently lose its
        # purpose.
        assert isinstance(cfg.broker, OandaBroker)
        assert not isinstance(cfg.broker, PaperBroker)
        assert isinstance(cfg.state_manager, StateManager)
        assert isinstance(cfg.exit_policy, ExitPolicyService)
        assert cfg.account_id == "acct-live-bootstrap-1"

    def test_broker_account_type_is_pinned_to_demo(self, empty_engine: Engine) -> None:
        """``account_type='demo'`` is the script-level guard against live-money
        trading.  The 6.18 invariant in ``OandaBroker.place_order`` is the
        defense in depth, but this assertion pins that the runner itself
        never constructs a live-account broker."""
        fake_api = MagicMock()
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        oanda = runner.OandaConfig(
            access_token="tok",
            account_id="acct-live-bootstrap-2",
            environment="practice",
        )
        supervisor, _feed = runner.build_supervisor_with_live_demo_stack(
            oanda=oanda,
            instrument="EUR_USD",
            engine=empty_engine,
            api_client=api_client,
        )
        broker = supervisor._exit_gate.broker  # type: ignore[attr-defined]
        # BrokerBase stores it on _account_type; OandaBroker has no
        # public account_type property.
        assert broker._account_type == "demo"

    def test_broker_and_feed_share_the_injected_api_client(self, empty_engine: Engine) -> None:
        """One REST client per runner: passing ``api_client=`` should be
        reused by both the broker and the auto-built feed (no double
        connection pool)."""
        fake_api = MagicMock()
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        oanda = runner.OandaConfig(
            access_token="tok",
            account_id="acct-live-bootstrap-3",
            environment="practice",
        )
        supervisor, feed = runner.build_supervisor_with_live_demo_stack(
            oanda=oanda,
            instrument="EUR_USD",
            engine=empty_engine,
            api_client=api_client,
        )
        broker = supervisor._exit_gate.broker  # type: ignore[attr-defined]
        assert broker.api_client is api_client
        assert feed._api is api_client  # type: ignore[attr-defined]

    def test_tick_returns_empty_when_no_positions(self, empty_engine: Engine) -> None:
        fake_api = MagicMock()
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        oanda = runner.OandaConfig(
            access_token="tok",
            account_id="acct-live-bootstrap-4",
            environment="practice",
        )
        supervisor, _feed = runner.build_supervisor_with_live_demo_stack(
            oanda=oanda,
            instrument="EUR_USD",
            engine=empty_engine,
            api_client=api_client,
        )
        # No positions → no quote query → no HTTP traffic.
        assert supervisor.run_exit_gate_tick() == []
        fake_api.request.assert_not_called()


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
        # Substitute build_db_engine so we don't need a real DATABASE_URL.
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
        # Default log filename for the live runner.
        assert (tmp_path / "live_loop.jsonl").exists()


# ---------------------------------------------------------------------------
# SIGINT handler — reuse paper runner's; sanity-check it is wired
# ---------------------------------------------------------------------------


class TestSigintHandlerImport:
    def test_sigint_handler_is_imported_from_paper_runner(self) -> None:
        """The live runner deliberately reuses the paper runner's
        ``_install_sigint_handler`` (framework-free, identical
        semantics).  If a future edit accidentally shadows it with a
        local stub, we want the test to flag that the shared seam was
        broken."""
        from scripts.run_paper_loop import _install_sigint_handler as paper_handler

        assert runner._install_sigint_handler is paper_handler


@pytest.fixture(autouse=True)
def _restore_sigint_default() -> Iterator[None]:
    """Reset SIGINT after every test so a leaked handler doesn't leak."""
    import signal as _signal

    previous = _signal.getsignal(_signal.SIGINT)
    yield
    _signal.signal(_signal.SIGINT, previous)
