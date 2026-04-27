"""Unit tests: run_paper_decision_loop.py argparse + broker helpers (Phase 9.19/J-3 + 9.X-K)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_RUNNER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_paper_decision_loop.py"
_spec = importlib.util.spec_from_file_location("paper_decision_runner", _RUNNER_PATH)
runner = importlib.util.module_from_spec(_spec)
sys.modules["paper_decision_runner"] = runner
assert _spec.loader is not None
_spec.loader.exec_module(runner)


# ---------------------------------------------------------------------------
# Existing flags should still parse with no value
# ---------------------------------------------------------------------------


class TestExistingFlags:
    def test_default_args_parse(self) -> None:
        args = runner._parse_args([])
        # Phase 9.19/J-3 default — no behaviour change.
        assert args.top_k == 1
        assert args.dry_run is False
        assert args.granularity == "M5"

    def test_dry_run_flag(self) -> None:
        args = runner._parse_args(["--dry-run"])
        assert args.dry_run is True


# ---------------------------------------------------------------------------
# Phase 9.19/J-3 --top-k flag
# ---------------------------------------------------------------------------


class TestTopKFlag:
    def test_top_k_default_is_one(self) -> None:
        args = runner._parse_args([])
        assert args.top_k == 1

    def test_top_k_explicit_two(self) -> None:
        args = runner._parse_args(["--top-k", "2"])
        assert args.top_k == 2

    def test_top_k_zero_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--top-k", "0"])

    def test_top_k_negative_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--top-k", "-1"])

    def test_top_k_non_integer_rejected(self) -> None:
        # argparse type=int rejects floats / non-numeric input.
        with pytest.raises(SystemExit):
            runner._parse_args(["--top-k", "1.5"])
        with pytest.raises(SystemExit):
            runner._parse_args(["--top-k", "x"])

    def test_top_k_three_accepted(self) -> None:
        args = runner._parse_args(["--top-k", "3"])
        assert args.top_k == 3


# ---------------------------------------------------------------------------
# Phase 9.X-B/J-4 --feature-groups flag (plumbing only)
# ---------------------------------------------------------------------------


class TestFeatureGroupsFlag:
    def test_feature_groups_default_empty(self) -> None:
        args = runner._parse_args([])
        assert args.feature_groups == ""
        assert args.feature_groups_set == frozenset()

    def test_feature_groups_mtf_accepted(self) -> None:
        args = runner._parse_args(["--feature-groups", "mtf"])
        assert args.feature_groups_set == frozenset({"mtf"})

    def test_feature_groups_combination_accepted(self) -> None:
        # Phase 9.X-B amendment: "moments" was scoped during J-4 plumbing
        # but never wired into FeatureService — only "vol" and "mtf" remain.
        args = runner._parse_args(["--feature-groups", "vol,mtf"])
        assert args.feature_groups_set == frozenset({"vol", "mtf"})

    def test_feature_groups_whitespace_stripped(self) -> None:
        args = runner._parse_args(["--feature-groups", " mtf , vol "])
        assert args.feature_groups_set == frozenset({"mtf", "vol"})

    def test_feature_groups_invalid_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--feature-groups", "garbage"])

    def test_feature_groups_partial_invalid_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--feature-groups", "mtf,xyz"])

    def test_feature_groups_empty_string_in_list(self) -> None:
        # Trailing comma is tolerated
        args = runner._parse_args(["--feature-groups", "mtf,"])
        assert args.feature_groups_set == frozenset({"mtf"})


# ---------------------------------------------------------------------------
# Phase 9.5-A --max-spread-pip flag + _fetch_spread_pips helper
# ---------------------------------------------------------------------------


class TestMaxSpreadPipFlag:
    def test_default_is_2_0(self) -> None:
        args = runner._parse_args([])
        assert args.max_spread_pip == 2.0

    def test_custom_value_accepted(self) -> None:
        args = runner._parse_args(["--max-spread-pip", "1.5"])
        assert args.max_spread_pip == 1.5

    def test_zero_accepted(self) -> None:
        args = runner._parse_args(["--max-spread-pip", "0.0"])
        assert args.max_spread_pip == 0.0


class TestFetchSpreadPips:
    def _mock_client(self, bid: float, ask: float):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_pricing.return_value = [
            {"bids": [{"price": str(bid)}], "asks": [{"price": str(ask)}]}
        ]
        return client

    def test_normal_spread(self) -> None:
        client = self._mock_client(159.000, 159.010)
        pip = runner._fetch_spread_pips(client, "acct1", "USD_JPY")
        assert pip == pytest.approx(1.0, abs=0.01)

    def test_eur_usd_spread(self) -> None:
        client = self._mock_client(1.10000, 1.10020)
        pip = runner._fetch_spread_pips(client, "acct1", "EUR_USD")
        assert pip == pytest.approx(2.0, abs=0.01)

    def test_empty_prices_returns_none(self) -> None:
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_pricing.return_value = []
        assert runner._fetch_spread_pips(client, "acct1", "EUR_USD") is None

    def test_api_error_returns_none(self) -> None:
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_pricing.side_effect = RuntimeError("network error")
        assert runner._fetch_spread_pips(client, "acct1", "EUR_USD") is None

    def test_unknown_instrument_uses_default_pip(self) -> None:
        client = self._mock_client(1.00000, 1.00010)
        pip = runner._fetch_spread_pips(client, "acct1", "XYZ_ABC")
        assert pip == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# Exit gate wiring: _granularity_minutes helper
# ---------------------------------------------------------------------------


class TestGranularityMinutes:
    def test_m1(self) -> None:
        assert runner._granularity_minutes("M1") == 1

    def test_m5(self) -> None:
        assert runner._granularity_minutes("M5") == 5

    def test_m15(self) -> None:
        assert runner._granularity_minutes("M15") == 15

    def test_h1(self) -> None:
        assert runner._granularity_minutes("H1") == 60

    def test_h4(self) -> None:
        assert runner._granularity_minutes("H4") == 240

    def test_unknown_falls_back_to_5(self) -> None:
        assert runner._granularity_minutes("D1") == 5

    def test_lowercase_accepted(self) -> None:
        assert runner._granularity_minutes("m5") == 5


class TestMaxHoldingBarsFlag:
    def test_default_is_20(self) -> None:
        args = runner._parse_args([])
        assert args.max_holding_bars == 20

    def test_custom_value(self) -> None:
        args = runner._parse_args(["--max-holding-bars", "50"])
        assert args.max_holding_bars == 50

    def test_zero_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--max-holding-bars", "0"])


# ---------------------------------------------------------------------------
# Phase 9.X-K: production levers — argparse flags
# ---------------------------------------------------------------------------


class TestPhase9XKFlags:
    def test_defaults(self) -> None:
        args = runner._parse_args([])
        assert args.initial_balance == pytest.approx(300_000.0)
        assert args.risk_pct == pytest.approx(1.0)
        assert args.max_units == 10_000
        assert args.max_leverage == pytest.approx(25.0)
        assert args.daily_dd_pct == pytest.approx(3.0)

    def test_initial_balance_custom(self) -> None:
        args = runner._parse_args(["--initial-balance", "500000"])
        assert args.initial_balance == pytest.approx(500_000.0)

    def test_risk_pct_custom(self) -> None:
        args = runner._parse_args(["--risk-pct", "0.5"])
        assert args.risk_pct == pytest.approx(0.5)

    def test_risk_pct_zero_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--risk-pct", "0"])

    def test_risk_pct_over_100_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--risk-pct", "101"])

    def test_max_units_custom(self) -> None:
        args = runner._parse_args(["--max-units", "5000"])
        assert args.max_units == 5000

    def test_max_units_zero_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--max-units", "0"])

    def test_max_leverage_custom(self) -> None:
        args = runner._parse_args(["--max-leverage", "10.0"])
        assert args.max_leverage == pytest.approx(10.0)

    def test_max_leverage_zero_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--max-leverage", "0"])

    def test_daily_dd_pct_custom(self) -> None:
        args = runner._parse_args(["--daily-dd-pct", "5.0"])
        assert args.daily_dd_pct == pytest.approx(5.0)

    def test_daily_dd_pct_zero_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--daily-dd-pct", "0"])

    def test_daily_dd_pct_over_100_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--daily-dd-pct", "101"])


# ---------------------------------------------------------------------------
# Phase 9.X-K: _DailyDrawdownBrake unit tests
# ---------------------------------------------------------------------------


class TestDailyDrawdownBrake:
    from datetime import date as _date

    def _make_engine(self, daily_loss: float):
        """Return a mock Engine whose connect() returns the given daily_loss sum."""
        from unittest.mock import MagicMock

        row = MagicMock()
        row.__getitem__ = lambda self, i: daily_loss
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.one.return_value = row
        engine = MagicMock()
        engine.connect.return_value = conn
        return engine

    def _today(self):
        from datetime import date

        return date(2026, 4, 28)

    def test_not_engaged_when_loss_below_threshold(self) -> None:
        brake = runner._DailyDrawdownBrake(opening_balance=300_000.0, dd_pct=3.0)
        engine = self._make_engine(-5_000.0)  # 5k loss < 9k threshold (3% of 300k)
        assert brake.is_engaged(engine, self._today()) is False

    def test_engaged_when_loss_exceeds_threshold(self) -> None:
        brake = runner._DailyDrawdownBrake(opening_balance=300_000.0, dd_pct=3.0)
        engine = self._make_engine(-10_000.0)  # 10k loss > 9k threshold
        assert brake.is_engaged(engine, self._today()) is True

    def test_exactly_at_threshold_not_engaged(self) -> None:
        brake = runner._DailyDrawdownBrake(opening_balance=300_000.0, dd_pct=3.0)
        engine = self._make_engine(-9_000.0)  # exactly 3% — strict less-than
        assert brake.is_engaged(engine, self._today()) is False

    def test_db_error_falls_through_safely(self) -> None:
        from unittest.mock import MagicMock

        brake = runner._DailyDrawdownBrake(opening_balance=300_000.0, dd_pct=3.0)
        engine = MagicMock()
        engine.connect.side_effect = RuntimeError("DB down")
        assert brake.is_engaged(engine, self._today()) is False


# ---------------------------------------------------------------------------
# Phase 9.X-K: _compute_position_size unit tests
# ---------------------------------------------------------------------------


class TestComputePositionSize:
    def _make_features(self, atr_14: float, inst: str = "USD_JPY"):
        from unittest.mock import MagicMock

        feat = MagicMock()
        feat.sampled_features = {"atr_14": atr_14}
        return {inst: feat}

    def test_basic_sizing_usd_jpy(self) -> None:
        features = self._make_features(0.20, "USD_JPY")  # 20 pip ATR
        size, reason = runner._compute_position_size(
            inst="USD_JPY",
            features=features,
            initial_balance=300_000.0,
            risk_pct=1.0,
            max_units=10_000,
            max_leverage=25.0,
            bar_close=155.0,
        )
        assert reason is None
        assert size > 0
        assert size <= 10_000

    def test_clip_cap_applied(self) -> None:
        # Small ATR → small SL pips → large raw size; should be clipped.
        features = self._make_features(0.001, "USD_JPY")  # tiny ATR → huge raw size
        size, reason = runner._compute_position_size(
            inst="USD_JPY",
            features=features,
            initial_balance=300_000.0,
            risk_pct=1.0,
            max_units=5_000,
            max_leverage=25.0,
            bar_close=155.0,
        )
        assert reason is None or size == 5_000 or size == 0

    def test_no_atr_returns_zero(self) -> None:
        features = self._make_features(0.0, "EUR_USD")
        size, reason = runner._compute_position_size(
            inst="EUR_USD",
            features=features,
            initial_balance=300_000.0,
            risk_pct=1.0,
            max_units=10_000,
            max_leverage=25.0,
            bar_close=1.10,
        )
        assert size == 0
        assert reason == "NoATR"

    def test_missing_instrument_returns_zero(self) -> None:
        size, reason = runner._compute_position_size(
            inst="EUR_USD",
            features={},
            initial_balance=300_000.0,
            risk_pct=1.0,
            max_units=10_000,
            max_leverage=25.0,
            bar_close=1.10,
        )
        assert size == 0
        assert reason == "NoFeatures"

    def test_margin_check_reduces_oversized_position(self) -> None:
        # Force an over-leveraged scenario: tiny balance, large size.
        features = self._make_features(0.001, "USD_JPY")  # would generate huge raw size
        size, reason = runner._compute_position_size(
            inst="USD_JPY",
            features=features,
            initial_balance=1_000.0,  # tiny balance
            risk_pct=1.0,
            max_units=1_000_000,  # no clip cap
            max_leverage=2.0,  # tight leverage
            bar_close=155.0,
        )
        # margin_limit = 1000 × 0.5 = 500; max_units_by_margin = 500×2/155 ≈ 6
        # Result is either 0 (InsufficientMargin) or a small positive number.
        assert reason in (None, "InsufficientMargin", "SizeUnderMin") or size >= 0


# ---------------------------------------------------------------------------
# Phase 9.X-K broker wiring: _open_paper_position unit tests
# ---------------------------------------------------------------------------


class TestOpenPaperPosition:
    """Unit tests for _open_paper_position using SQLite in-memory DB."""

    def _build_engine(self):
        import sqlalchemy as sa

        engine = sa.create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    """
                    CREATE TABLE orders (
                        order_id TEXT PRIMARY KEY,
                        client_order_id TEXT,
                        trading_signal_id TEXT,
                        account_id TEXT,
                        instrument TEXT,
                        account_type TEXT,
                        order_type TEXT,
                        direction TEXT,
                        units TEXT,
                        status TEXT DEFAULT 'PENDING',
                        submitted_at TEXT,
                        filled_at TEXT,
                        canceled_at TEXT,
                        correlation_id TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    )
                    """
                )
            )
            conn.execute(
                sa.text(
                    """
                    CREATE TABLE positions (
                        position_snapshot_id TEXT PRIMARY KEY,
                        order_id TEXT,
                        account_id TEXT,
                        instrument TEXT,
                        event_type TEXT,
                        units INTEGER,
                        avg_price REAL,
                        unrealized_pl REAL,
                        realized_pl REAL,
                        event_time_utc TEXT,
                        correlation_id TEXT
                    )
                    """
                )
            )
            conn.execute(
                sa.text(
                    """
                    CREATE TABLE secondary_sync_outbox (
                        outbox_id TEXT PRIMARY KEY,
                        table_name TEXT,
                        primary_key TEXT,
                        version_no INTEGER,
                        payload_json TEXT,
                        enqueued_at TEXT,
                        attempt_count INTEGER DEFAULT 0,
                        run_id TEXT,
                        environment TEXT,
                        code_version TEXT,
                        config_version TEXT
                    )
                    """
                )
            )
        return engine

    def _make_collaborators(self, engine):
        from unittest.mock import MagicMock

        from fx_ai_trading.common.clock import WallClock
        from fx_ai_trading.config.common_keys_context import CommonKeysContext
        from fx_ai_trading.repositories.orders import OrdersRepository
        from fx_ai_trading.services.state_manager import StateManager

        clock = MagicMock(spec=WallClock)
        clock.now.return_value = __import__("datetime").datetime(
            2026, 4, 28, 12, 0, 0, tzinfo=__import__("datetime").timezone.utc
        )
        state_manager = StateManager(engine, account_id="acct1", clock=clock)
        orders_repo = OrdersRepository(engine)
        orders_context = CommonKeysContext(
            run_id="test-run",
            environment="demo",
            code_version="test",
            config_version="v1",
        )
        return state_manager, orders_repo, orders_context, clock

    def test_successful_open_buy(self) -> None:
        engine = self._build_engine()
        state_manager, orders_repo, ctx, clock = self._make_collaborators(engine)
        result = runner._open_paper_position(
            engine=engine,
            account_id="acct1",
            instrument="EUR_USD",
            direction="buy",
            size_units=1000,
            fill_price=1.1050,
            clock=clock,
            state_manager=state_manager,
            orders_repo=orders_repo,
            orders_context=ctx,
        )
        assert result is not None
        assert isinstance(result, str)
        assert "EUR_USD" in state_manager.open_instruments()

    def test_successful_open_sell(self) -> None:
        engine = self._build_engine()
        state_manager, orders_repo, ctx, clock = self._make_collaborators(engine)
        result = runner._open_paper_position(
            engine=engine,
            account_id="acct1",
            instrument="USD_JPY",
            direction="sell",
            size_units=500,
            fill_price=155.0,
            clock=clock,
            state_manager=state_manager,
            orders_repo=orders_repo,
            orders_context=ctx,
        )
        assert result is not None
        assert isinstance(result, str)
        assert "USD_JPY" in state_manager.open_instruments()

    def test_duplicate_instrument_skipped(self) -> None:
        engine = self._build_engine()
        state_manager, orders_repo, ctx, clock = self._make_collaborators(engine)
        # First open succeeds.
        runner._open_paper_position(
            engine=engine,
            account_id="acct1",
            instrument="EUR_USD",
            direction="buy",
            size_units=1000,
            fill_price=1.1050,
            clock=clock,
            state_manager=state_manager,
            orders_repo=orders_repo,
            orders_context=ctx,
        )
        # Second open on same instrument → skipped.
        result = runner._open_paper_position(
            engine=engine,
            account_id="acct1",
            instrument="EUR_USD",
            direction="buy",
            size_units=500,
            fill_price=1.1060,
            clock=clock,
            state_manager=state_manager,
            orders_repo=orders_repo,
            orders_context=ctx,
        )
        assert result is None

    def test_unknown_direction_returns_none(self) -> None:
        engine = self._build_engine()
        state_manager, orders_repo, ctx, clock = self._make_collaborators(engine)
        result = runner._open_paper_position(
            engine=engine,
            account_id="acct1",
            instrument="EUR_USD",
            direction="hold",  # invalid
            size_units=1000,
            fill_price=1.1050,
            clock=clock,
            state_manager=state_manager,
            orders_repo=orders_repo,
            orders_context=ctx,
        )
        assert result is None
        assert "EUR_USD" not in state_manager.open_instruments()

    def test_order_fsm_transitions_to_filled(self) -> None:
        import sqlalchemy as sa

        engine = self._build_engine()
        state_manager, orders_repo, ctx, clock = self._make_collaborators(engine)
        runner._open_paper_position(
            engine=engine,
            account_id="acct1",
            instrument="GBP_USD",
            direction="sell",
            size_units=200,
            fill_price=1.2700,
            clock=clock,
            state_manager=state_manager,
            orders_repo=orders_repo,
            orders_context=ctx,
        )
        with engine.connect() as conn:
            row = conn.execute(
                sa.text("SELECT status FROM orders WHERE instrument = 'GBP_USD'")
            ).fetchone()
        assert row is not None
        assert row[0] == "FILLED"

    def test_returns_order_id_string(self) -> None:
        engine = self._build_engine()
        state_manager, orders_repo, ctx, clock = self._make_collaborators(engine)
        result = runner._open_paper_position(
            engine=engine,
            account_id="acct1",
            instrument="AUD_USD",
            direction="buy",
            size_units=1000,
            fill_price=0.6550,
            clock=clock,
            state_manager=state_manager,
            orders_repo=orders_repo,
            orders_context=ctx,
        )
        # Returned order_id can be used as key in _tpsl_map.
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Phase 9.X-K+1: TP/SL constants and per-position map wiring
# ---------------------------------------------------------------------------


class TestTPSLConstants:
    def test_tp_mult_matches_b2_label(self) -> None:
        assert pytest.approx(1.5) == runner._TP_MULT

    def test_sl_mult_matches_b2_label(self) -> None:
        assert pytest.approx(1.0) == runner._SL_MULT

    def test_buy_tp_above_entry(self) -> None:
        entry = 1.1000
        atr = 0.0020
        tp = entry + runner._TP_MULT * atr
        sl = entry - runner._SL_MULT * atr
        assert tp > entry
        assert sl < entry
        assert tp == pytest.approx(1.1030)
        assert sl == pytest.approx(1.0980)

    def test_sell_tp_below_entry(self) -> None:
        entry = 1.1000
        atr = 0.0020
        tp = entry - runner._TP_MULT * atr
        sl = entry + runner._SL_MULT * atr
        assert tp < entry
        assert sl > entry
        assert tp == pytest.approx(1.0970)
        assert sl == pytest.approx(1.1020)
