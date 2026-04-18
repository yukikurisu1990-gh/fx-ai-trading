"""M4 contract tests: all domain Protocols/ABCs and DTOs exist and are well-formed.

Checks:
1. All Protocols/ABCs are importable and have required methods.
2. All DTOs are @dataclass(frozen=True).
3. domain/ does not import from adapters/, repositories/, or services/.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
from pathlib import Path
from types import ModuleType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import(module_path: str) -> ModuleType:
    return importlib.import_module(module_path)


def _is_frozen_dataclass(cls: type) -> bool:
    return dataclasses.is_dataclass(cls) and cls.__dataclass_params__.frozen  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 1. Protocol / ABC import and method existence
# ---------------------------------------------------------------------------


class TestBrokerDomain:
    def test_broker_importable(self) -> None:
        from fx_ai_trading.domain.broker import Broker

        assert inspect.isclass(Broker)

    def test_broker_has_required_methods(self) -> None:
        from fx_ai_trading.domain.broker import Broker

        for method in (
            "place_order",
            "cancel_order",
            "get_positions",
            "get_pending_orders",
            "get_recent_transactions",
        ):
            assert hasattr(Broker, method), f"Broker missing {method}"

    def test_broker_has_verify_method(self) -> None:
        from fx_ai_trading.domain.broker import Broker

        assert hasattr(Broker, "_verify_account_type_or_raise")

    def test_broker_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.broker import (
            BrokerOrder,
            BrokerPosition,
            BrokerTransactionEvent,
            CancelResult,
            OrderRequest,
            OrderResult,
        )

        for cls in (
            OrderRequest,
            OrderResult,
            CancelResult,
            BrokerPosition,
            BrokerOrder,
            BrokerTransactionEvent,
        ):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestExecutionDomain:
    def test_execution_gate_importable(self) -> None:
        from fx_ai_trading.domain.execution import ExecutionGate

        assert inspect.isclass(ExecutionGate)

    def test_execution_gate_has_check(self) -> None:
        from fx_ai_trading.domain.execution import ExecutionGate

        assert hasattr(ExecutionGate, "check")

    def test_execution_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.execution import GateResult, RealtimeContext, TradingIntent

        for cls in (TradingIntent, RealtimeContext, GateResult):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestRiskDomain:
    def test_risk_manager_importable(self) -> None:
        from fx_ai_trading.domain.risk import RiskManager

        assert inspect.isclass(RiskManager)

    def test_risk_manager_has_accept(self) -> None:
        from fx_ai_trading.domain.risk import RiskManager

        assert hasattr(RiskManager, "accept")

    def test_position_sizer_has_size(self) -> None:
        from fx_ai_trading.domain.risk import PositionSizer

        assert hasattr(PositionSizer, "size")

    def test_risk_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.risk import Exposure, Instrument, RiskAcceptResult, SizeResult

        for cls in (Exposure, RiskAcceptResult, SizeResult, Instrument):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestFeatureDomain:
    def test_feature_builder_importable(self) -> None:
        from fx_ai_trading.domain.feature import FeatureBuilder

        assert inspect.isclass(FeatureBuilder)

    def test_feature_builder_has_required_methods(self) -> None:
        from fx_ai_trading.domain.feature import FeatureBuilder

        for method in ("build", "get_feature_version"):
            assert hasattr(FeatureBuilder, method), f"FeatureBuilder missing {method}"

    def test_feature_set_frozen(self) -> None:
        from fx_ai_trading.domain.feature import FeatureSet

        assert _is_frozen_dataclass(FeatureSet)


class TestStrategyDomain:
    def test_strategy_evaluator_importable(self) -> None:
        from fx_ai_trading.domain.strategy import StrategyEvaluator

        assert inspect.isclass(StrategyEvaluator)

    def test_strategy_evaluator_has_evaluate(self) -> None:
        from fx_ai_trading.domain.strategy import StrategyEvaluator

        assert hasattr(StrategyEvaluator, "evaluate")

    def test_strategy_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

        for cls in (StrategySignal, StrategyContext):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestEVDomain:
    def test_ev_estimator_importable(self) -> None:
        from fx_ai_trading.domain.ev import EVEstimator

        assert inspect.isclass(EVEstimator)

    def test_cost_model_has_compute(self) -> None:
        from fx_ai_trading.domain.ev import CostModel

        assert hasattr(CostModel, "compute")

    def test_ev_estimator_has_estimate(self) -> None:
        from fx_ai_trading.domain.ev import EVEstimator

        assert hasattr(EVEstimator, "estimate")

    def test_ev_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.ev import Cost, EVEstimate

        for cls in (Cost, EVEstimate):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestMetaDomain:
    def test_meta_decider_importable(self) -> None:
        from fx_ai_trading.domain.meta import MetaDecider

        assert inspect.isclass(MetaDecider)

    def test_meta_decider_has_decide(self) -> None:
        from fx_ai_trading.domain.meta import MetaDecider

        assert hasattr(MetaDecider, "decide")

    def test_meta_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.meta import MetaContext, MetaDecision, NoTradeReason

        for cls in (MetaContext, MetaDecision, NoTradeReason):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestPriceFeedDomain:
    def test_price_feed_importable(self) -> None:
        from fx_ai_trading.domain.price_feed import PriceFeed

        assert inspect.isclass(PriceFeed)

    def test_price_feed_has_required_methods(self) -> None:
        from fx_ai_trading.domain.price_feed import PriceFeed

        for method in (
            "list_active_instruments",
            "get_candles",
            "get_latest_price",
            "subscribe_price_stream",
            "subscribe_transaction_stream",
        ):
            assert hasattr(PriceFeed, method), f"PriceFeed missing {method}"

    def test_price_feed_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.price_feed import Candle, PriceEvent, PriceTick

        for cls in (Candle, PriceTick, PriceEvent):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestModelRegistryDomain:
    def test_model_registry_importable(self) -> None:
        from fx_ai_trading.domain.model_registry import ModelRegistry

        assert inspect.isclass(ModelRegistry)

    def test_model_registry_has_required_methods(self) -> None:
        from fx_ai_trading.domain.model_registry import ModelRegistry

        for method in (
            "load",
            "save",
            "promote",
            "demote",
            "get_active",
            "get_shadow",
            "list_by_state",
        ):
            assert hasattr(ModelRegistry, method), f"ModelRegistry missing {method}"

    def test_predictor_has_predict(self) -> None:
        from fx_ai_trading.domain.model_registry import Predictor

        assert hasattr(Predictor, "predict")
        assert hasattr(Predictor, "get_model_id")

    def test_model_registry_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.model_registry import (
            Model,
            ModelMetadata,
            Prediction,
            PredictionContext,
        )

        for cls in (Model, ModelMetadata, PredictionContext, Prediction):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestNotifierDomain:
    def test_notifier_importable(self) -> None:
        from fx_ai_trading.domain.notifier import Notifier, NotifierDispatcher

        assert inspect.isclass(Notifier)
        assert inspect.isclass(NotifierDispatcher)

    def test_notifier_has_send(self) -> None:
        from fx_ai_trading.domain.notifier import Notifier

        assert hasattr(Notifier, "send")

    def test_notifier_dispatcher_has_both_paths(self) -> None:
        from fx_ai_trading.domain.notifier import NotifierDispatcher

        assert hasattr(NotifierDispatcher, "dispatch_direct_sync")
        assert hasattr(NotifierDispatcher, "dispatch_via_outbox")

    def test_notifier_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.notifier import NotifyEvent, NotifyResult

        for cls in (NotifyEvent, NotifyResult):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestEventBusDomain:
    def test_event_bus_importable(self) -> None:
        from fx_ai_trading.domain.event_bus import EventBus

        assert inspect.isclass(EventBus)

    def test_event_bus_has_required_methods(self) -> None:
        from fx_ai_trading.domain.event_bus import EventBus

        for method in ("publish", "subscribe", "unsubscribe"):
            assert hasattr(EventBus, method), f"EventBus missing {method}"

    def test_event_bus_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.event_bus import Event, SubscriptionId

        for cls in (Event, SubscriptionId):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestCorrelationDomain:
    def test_correlation_matrix_importable(self) -> None:
        from fx_ai_trading.domain.correlation import CorrelationMatrix

        assert inspect.isclass(CorrelationMatrix)

    def test_correlation_matrix_has_required_methods(self) -> None:
        from fx_ai_trading.domain.correlation import CorrelationMatrix

        for method in ("get", "update", "exceeds_threshold"):
            assert hasattr(CorrelationMatrix, method), f"CorrelationMatrix missing {method}"

    def test_correlation_dtos_frozen(self) -> None:
        from fx_ai_trading.domain.correlation import CorrelationConfig, CorrelationSnapshot

        for cls in (CorrelationConfig, CorrelationSnapshot):
            assert _is_frozen_dataclass(cls), f"{cls.__name__} is not a frozen dataclass"


class TestEventCalendarDomain:
    def test_event_calendar_importable(self) -> None:
        from fx_ai_trading.domain.event_calendar import EventCalendar

        assert inspect.isclass(EventCalendar)

    def test_event_calendar_has_required_methods(self) -> None:
        from fx_ai_trading.domain.event_calendar import EventCalendar

        for method in ("is_stale", "get_upcoming", "refresh"):
            assert hasattr(EventCalendar, method), f"EventCalendar missing {method}"

    def test_event_calendar_has_properties(self) -> None:
        from fx_ai_trading.domain.event_calendar import EventCalendar

        assert hasattr(EventCalendar, "last_updated_at")
        assert hasattr(EventCalendar, "max_staleness_hours")

    def test_economic_event_frozen(self) -> None:
        from fx_ai_trading.domain.event_calendar import EconomicEvent

        assert _is_frozen_dataclass(EconomicEvent)


class TestExitDomain:
    def test_exit_policy_importable(self) -> None:
        from fx_ai_trading.domain.exit import ExitPolicy

        assert inspect.isclass(ExitPolicy)

    def test_exit_policy_has_evaluate(self) -> None:
        from fx_ai_trading.domain.exit import ExitPolicy

        assert hasattr(ExitPolicy, "evaluate")

    def test_exit_decision_frozen(self) -> None:
        from fx_ai_trading.domain.exit import ExitDecision

        assert _is_frozen_dataclass(ExitDecision)


# ---------------------------------------------------------------------------
# 2. domain/ import isolation: no imports from adapters/repositories/services
# ---------------------------------------------------------------------------


class TestDomainImportIsolation:
    """Verify domain layer does not import from other layers."""

    FORBIDDEN_PREFIXES = (
        "fx_ai_trading.adapters",
        "fx_ai_trading.repositories",
        "fx_ai_trading.services",
    )

    def _get_domain_modules(self) -> list[str]:
        domain_path = Path(__file__).parent.parent.parent / "src" / "fx_ai_trading" / "domain"
        modules = []
        for f in domain_path.glob("*.py"):
            if f.name.startswith("_"):
                continue
            module_name = f"fx_ai_trading.domain.{f.stem}"
            modules.append(module_name)
        return modules

    def test_domain_modules_do_not_import_adapters(self) -> None:
        """No domain module may import from adapters/, repositories/, or services/."""
        for module_name in self._get_domain_modules():
            mod = importlib.import_module(module_name)
            for dep_name in vars(mod).values():
                if not isinstance(dep_name, ModuleType):
                    continue
                for forbidden in self.FORBIDDEN_PREFIXES:
                    assert not dep_name.__name__.startswith(forbidden), (
                        f"{module_name} imports from {dep_name.__name__} "
                        f"(forbidden prefix: {forbidden})"
                    )

    def test_domain_source_has_no_forbidden_imports(self) -> None:
        """Static check: domain .py files don't contain import lines for forbidden layers."""
        domain_path = Path(__file__).parent.parent.parent / "src" / "fx_ai_trading" / "domain"
        violations = []
        for py_file in domain_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            text = py_file.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    continue
                for forbidden in self.FORBIDDEN_PREFIXES:
                    if forbidden in stripped:
                        violations.append(f"{py_file.name}: {stripped}")
        assert not violations, "Domain layer imports from forbidden layers:\n" + "\n".join(
            violations
        )
