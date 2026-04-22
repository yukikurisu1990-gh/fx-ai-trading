"""Unit tests: ``scripts/paper_open_position`` bootstrap CLI.

Pins the contract that the bootstrap:
  - Resolves CLI defaults + validates --units / --nominal-price / --direction.
  - Fails fast (rc=2) when DATABASE_URL is missing.
  - Pre-flight refuses (rc=3 / ``DuplicateOpenInstrumentError``) when the
    instrument is already open for the account.
  - Drives the FSM-compliant 5-step sequence in exact order:
      create_order → update_status('SUBMITTED') → place_order →
      update_status('FILLED') → state_manager.on_fill
  - Returns rc=4 (``BrokerDidNotFillError``) if PaperBroker returns
    non-'filled' — and aborts BEFORE the FILLED transition so the orders
    row is not lied to.
  - ``build_db_engine`` honours an explicit ``env`` dict for
    DATABASE_URL lookup (the test seam used in integration tests).

These tests exercise the script through its public seams
(``parse_args`` / ``build_db_engine`` / ``bootstrap_open_position`` /
``main``); all DB collaborators are substituted with mocks so no
SQLite/Postgres is touched here.  The integration test at
``tests/integration/test_paper_open_position_bootstrap.py`` covers the
real DB write path.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.domain.broker import OrderResult


def _load_bootstrap_module():
    """Import ``scripts/paper_open_position.py`` by file path.

    ``scripts/`` is not on the package path, so a normal ``import`` fails.
    Same loader pattern as ``tests/unit/test_run_paper_loop.py``.
    """
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "paper_open_position.py"
    spec = importlib.util.spec_from_file_location("scripts_paper_open_position", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass / typing introspection finds us.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bootstrap_mod = _load_bootstrap_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_REQUIRED_ARGV = [
    "--account-id",
    "ACC-1",
    "--instrument",
    "EUR_USD",
    "--direction",
    "buy",
    "--units",
    "1000",
]


def _filled_result(*, fill_price: float = 1.0, units: int = 1000) -> OrderResult:
    return OrderResult(
        client_order_id="cid",
        broker_order_id="paper-cid",
        status="filled",
        filled_units=units,
        fill_price=fill_price,
    )


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_defaults_for_unset_optional_flags(self) -> None:
        args = bootstrap_mod.parse_args(_REQUIRED_ARGV)
        assert args.account_id == "ACC-1"
        assert args.instrument == "EUR_USD"
        assert args.direction == "buy"
        assert args.units == 1000
        assert args.account_type == "demo"
        assert args.nominal_price == 1.0
        assert args.log_filename == "paper_open_position.jsonl"
        assert args.log_level == "INFO"

    def test_all_flags_threaded_through(self) -> None:
        args = bootstrap_mod.parse_args(
            _REQUIRED_ARGV
            + [
                "--account-type",
                "live",
                "--nominal-price",
                "1.25",
                "--log-level",
                "DEBUG",
                "--log-filename",
                "custom.jsonl",
            ]
        )
        assert args.account_type == "live"
        assert args.nominal_price == 1.25
        assert args.log_level == "DEBUG"
        assert args.log_filename == "custom.jsonl"

    def test_missing_account_id_errors(self) -> None:
        with pytest.raises(SystemExit):
            bootstrap_mod.parse_args(
                [
                    "--instrument",
                    "EUR_USD",
                    "--direction",
                    "buy",
                    "--units",
                    "1000",
                ]
            )

    def test_missing_instrument_errors(self) -> None:
        with pytest.raises(SystemExit):
            bootstrap_mod.parse_args(
                [
                    "--account-id",
                    "ACC-1",
                    "--direction",
                    "buy",
                    "--units",
                    "1000",
                ]
            )

    def test_invalid_direction_errors(self) -> None:
        with pytest.raises(SystemExit):
            bootstrap_mod.parse_args(
                [
                    "--account-id",
                    "ACC-1",
                    "--instrument",
                    "EUR_USD",
                    "--direction",
                    "sideways",
                    "--units",
                    "1000",
                ]
            )

    def test_non_positive_units_errors(self) -> None:
        with pytest.raises(SystemExit):
            bootstrap_mod.parse_args(
                [
                    "--account-id",
                    "ACC-1",
                    "--instrument",
                    "EUR_USD",
                    "--direction",
                    "buy",
                    "--units",
                    "0",
                ]
            )

    def test_non_positive_nominal_price_errors(self) -> None:
        with pytest.raises(SystemExit):
            bootstrap_mod.parse_args(_REQUIRED_ARGV + ["--nominal-price", "0"])


# ---------------------------------------------------------------------------
# build_db_engine
# ---------------------------------------------------------------------------


class TestBuildDbEngine:
    def test_missing_database_url_raises(self) -> None:
        with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
            bootstrap_mod.build_db_engine(env={})

    def test_blank_database_url_raises(self) -> None:
        with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
            bootstrap_mod.build_db_engine(env={"DATABASE_URL": "   "})

    def test_returns_engine_for_valid_url(self) -> None:
        engine = bootstrap_mod.build_db_engine(env={"DATABASE_URL": "sqlite:///:memory:"})
        # Just check it's a SQLAlchemy Engine-shaped object.
        assert hasattr(engine, "connect")
        assert hasattr(engine, "dispose")


# ---------------------------------------------------------------------------
# bootstrap_open_position — orchestration
# ---------------------------------------------------------------------------


class TestBootstrapOpenPosition:
    def _fakes(
        self,
        *,
        already_open: tuple[str, ...] = (),
        broker_result: OrderResult | None = None,
        on_fill_psid: str = "psid-123",
    ):
        """Build a (state_manager, orders, broker, call_recorder) tuple.

        ``call_recorder`` is a list that records the exact call sequence so
        tests can assert the FSM order (create → SUBMITTED → place →
        FILLED → on_fill).
        """
        calls: list[tuple[str, dict]] = []

        sm = MagicMock(name="StateManager")
        sm.open_instruments.return_value = frozenset(already_open)
        sm.on_fill.side_effect = lambda **kw: calls.append(("on_fill", kw)) or on_fill_psid

        orders = MagicMock(name="OrdersRepository")
        orders.create_order.side_effect = lambda **kw: calls.append(("create_order", kw)) or None
        orders.update_status.side_effect = lambda order_id, new_status, ctx: (
            calls.append(("update_status", {"order_id": order_id, "new_status": new_status}))
            or None
        )

        def _place_order(req):
            calls.append(("place_order", {"side": req.side, "units": req.size_units}))
            return broker_result or _filled_result()

        broker = MagicMock(name="PaperBroker")
        broker.place_order.side_effect = _place_order
        return sm, orders, broker, calls

    def test_happy_path_emits_full_sequence_in_order(self) -> None:
        sm, orders, broker, calls = self._fakes()
        result = bootstrap_mod.bootstrap_open_position(
            engine=MagicMock(),
            instrument="EUR_USD",
            direction="buy",
            units=1000,
            account_id="ACC-1",
            state_manager=sm,
            orders=orders,
            broker=broker,
        )

        # Exactly 5 calls, in the specified FSM order.
        assert [c[0] for c in calls] == [
            "create_order",
            "update_status",
            "place_order",
            "update_status",
            "on_fill",
        ]
        assert calls[1][1]["new_status"] == "SUBMITTED"
        assert calls[3][1]["new_status"] == "FILLED"
        # place_order happened BETWEEN the two update_status calls.
        assert calls[1][1]["order_id"] == calls[3][1]["order_id"]

        # buy → long (production mapping).
        assert calls[2][1]["side"] == "long"
        assert calls[2][1]["units"] == 1000

        # on_fill received the broker's fill_price.
        assert calls[4][1]["avg_price"] == 1.0
        assert calls[4][1]["units"] == 1000

        # BootstrapResult fields wired from the fakes.
        assert result.position_snapshot_id == "psid-123"
        assert result.fill_price == 1.0
        assert result.side == "long"

    def test_sell_maps_to_short_side(self) -> None:
        sm, orders, broker, calls = self._fakes()
        bootstrap_mod.bootstrap_open_position(
            engine=MagicMock(),
            instrument="EUR_USD",
            direction="sell",
            units=500,
            account_id="ACC-1",
            state_manager=sm,
            orders=orders,
            broker=broker,
        )
        assert calls[2][1]["side"] == "short"

    def test_duplicate_open_instrument_raises_before_any_write(self) -> None:
        sm, orders, broker, calls = self._fakes(already_open=("EUR_USD",))
        with pytest.raises(bootstrap_mod.DuplicateOpenInstrumentError):
            bootstrap_mod.bootstrap_open_position(
                engine=MagicMock(),
                instrument="EUR_USD",
                direction="buy",
                units=1000,
                account_id="ACC-1",
                state_manager=sm,
                orders=orders,
                broker=broker,
            )
        # No writes should have happened.
        assert calls == []
        orders.create_order.assert_not_called()
        orders.update_status.assert_not_called()
        broker.place_order.assert_not_called()
        sm.on_fill.assert_not_called()

    def test_broker_not_filled_aborts_before_filled_transition(self) -> None:
        rejected = OrderResult(
            client_order_id="cid",
            broker_order_id="paper-cid",
            status="rejected",
            filled_units=0,
            fill_price=None,
            message="synthetic reject",
        )
        sm, orders, broker, calls = self._fakes(broker_result=rejected)
        with pytest.raises(bootstrap_mod.BrokerDidNotFillError):
            bootstrap_mod.bootstrap_open_position(
                engine=MagicMock(),
                instrument="EUR_USD",
                direction="buy",
                units=1000,
                account_id="ACC-1",
                state_manager=sm,
                orders=orders,
                broker=broker,
            )
        # create_order + SUBMITTED happened; FILLED + on_fill did NOT.
        events = [c[0] for c in calls]
        assert events == ["create_order", "update_status", "place_order"]
        assert calls[1][1]["new_status"] == "SUBMITTED"
        sm.on_fill.assert_not_called()

    def test_invalid_direction_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="direction"):
            bootstrap_mod.bootstrap_open_position(
                engine=MagicMock(),
                instrument="EUR_USD",
                direction="sideways",
                units=1000,
                account_id="ACC-1",
                state_manager=MagicMock(),
                orders=MagicMock(),
                broker=MagicMock(),
            )

    def test_non_positive_units_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="units"):
            bootstrap_mod.bootstrap_open_position(
                engine=MagicMock(),
                instrument="EUR_USD",
                direction="buy",
                units=0,
                account_id="ACC-1",
                state_manager=MagicMock(),
                orders=MagicMock(),
                broker=MagicMock(),
            )


# ---------------------------------------------------------------------------
# main — return codes
# ---------------------------------------------------------------------------


class TestMainRcCodes:
    def _patch_logging(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # apply_logging_config writes a real JSONL file; redirect it to
        # tmp_path so the unit tests never touch the repo's ``logs/``.
        monkeypatch.setattr(
            bootstrap_mod,
            "_DEFAULT_LOG_DIR",
            tmp_path,
            raising=True,
        )

    def test_rc2_when_database_url_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        self._patch_logging(monkeypatch, tmp_path)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        rc = bootstrap_mod.main(_REQUIRED_ARGV + ["--log-dir", str(tmp_path)])
        assert rc == 2

    def test_rc0_on_happy_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self._patch_logging(monkeypatch, tmp_path)
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        engine = MagicMock(name="engine")
        monkeypatch.setattr(bootstrap_mod, "build_db_engine", lambda: engine)

        captured: dict = {}

        def _fake_bootstrap(**kw):
            captured.update(kw)
            return bootstrap_mod.BootstrapResult(
                order_id="oid",
                client_order_id="cid",
                position_snapshot_id="psid",
                fill_price=1.0,
                side="long",
            )

        monkeypatch.setattr(bootstrap_mod, "bootstrap_open_position", _fake_bootstrap)

        rc = bootstrap_mod.main(_REQUIRED_ARGV + ["--log-dir", str(tmp_path)])
        assert rc == 0
        # engine is disposed in finally regardless of rc.
        engine.dispose.assert_called_once()
        # Args were threaded through to bootstrap_open_position.
        assert captured["instrument"] == "EUR_USD"
        assert captured["direction"] == "buy"
        assert captured["units"] == 1000
        assert captured["account_id"] == "ACC-1"

    def test_rc3_on_duplicate_open(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self._patch_logging(monkeypatch, tmp_path)
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        engine = MagicMock(name="engine")
        monkeypatch.setattr(bootstrap_mod, "build_db_engine", lambda: engine)

        def _raise_dup(**kw):
            raise bootstrap_mod.DuplicateOpenInstrumentError("already open")

        monkeypatch.setattr(bootstrap_mod, "bootstrap_open_position", _raise_dup)

        rc = bootstrap_mod.main(_REQUIRED_ARGV + ["--log-dir", str(tmp_path)])
        assert rc == 3
        engine.dispose.assert_called_once()

    def test_rc4_on_broker_not_filled(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        self._patch_logging(monkeypatch, tmp_path)
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        engine = MagicMock(name="engine")
        monkeypatch.setattr(bootstrap_mod, "build_db_engine", lambda: engine)

        def _raise_reject(**kw):
            raise bootstrap_mod.BrokerDidNotFillError("rejected")

        monkeypatch.setattr(bootstrap_mod, "bootstrap_open_position", _raise_reject)

        rc = bootstrap_mod.main(_REQUIRED_ARGV + ["--log-dir", str(tmp_path)])
        assert rc == 4
        engine.dispose.assert_called_once()


# ---------------------------------------------------------------------------
# Direction mapping — pinned to production (execution_gate_runner)
# ---------------------------------------------------------------------------


class TestDirectionMapping:
    def test_buy_maps_to_long(self) -> None:
        assert bootstrap_mod._DIRECTION_TO_BROKER_SIDE["buy"] == "long"

    def test_sell_maps_to_short(self) -> None:
        assert bootstrap_mod._DIRECTION_TO_BROKER_SIDE["sell"] == "short"

    def test_mapping_has_no_other_entries(self) -> None:
        # Keep this in lock-step with execution_gate_runner._DIRECTION_TO_BROKER_SIDE.
        assert set(bootstrap_mod._DIRECTION_TO_BROKER_SIDE.keys()) == {"buy", "sell"}


# Silence noisy per-call error logs from bootstrap_mod during unit tests.
@pytest.fixture(autouse=True)
def _quiet_logger():
    logging.getLogger("scripts.paper_open_position").setLevel(logging.CRITICAL)
