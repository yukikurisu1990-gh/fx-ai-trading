"""Smoke tests — verify the package imports and config loads."""

from fx_ai_trading import __version__
from fx_ai_trading.common.config import load_config
from fx_ai_trading.common.logging import get_logger, setup_logging


def test_version_is_non_empty_string() -> None:
    assert isinstance(__version__, str) and __version__


def test_load_config_uses_defaults(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    cfg = load_config()
    assert cfg.app_env == "development"
    assert cfg.log_level == "INFO"


def test_logger_setup_does_not_raise() -> None:
    setup_logging("INFO")
    logger = get_logger("fx_ai_trading.smoke")
    logger.info("smoke test logger ok")
