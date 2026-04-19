"""Unit tests for ConfigProvider — pure Python, no DB required."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.config.config_provider import ConfigProvider


def _make_provider(
    get_return: str | None = None,
    env_file_path: Path | None = None,
    default_catalog: dict[str, str] | None = None,
) -> ConfigProvider:
    repo = MagicMock()
    repo.get.return_value = get_return
    return ConfigProvider(repo=repo, env_file_path=env_file_path, default_catalog=default_catalog)


class TestGet:
    def test_delegates_to_repo(self) -> None:
        provider = _make_provider(get_return="demo")
        assert provider.get("expected_account_type") == "demo"
        provider._repo.get.assert_called_once_with("expected_account_type")

    def test_returns_none_when_repo_returns_none(self) -> None:
        provider = _make_provider(get_return=None)
        assert provider.get("missing_key") is None


class TestParseEnvFile:
    def test_returns_empty_when_path_is_none(self) -> None:
        provider = _make_provider()
        assert provider._parse_env_file() == {}

    def test_returns_empty_when_file_does_not_exist(self, tmp_path: Path) -> None:
        provider = _make_provider(env_file_path=tmp_path / "nonexistent.env")
        assert provider._parse_env_file() == {}

    def test_parses_key_value_pairs(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n", encoding="utf-8")
        provider = _make_provider(env_file_path=env_file)
        result = provider._parse_env_file()
        assert result == {"BAZ": "qux", "FOO": "bar"}

    def test_skips_comments_and_blank_lines(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY=value\n", encoding="utf-8")
        provider = _make_provider(env_file_path=env_file)
        result = provider._parse_env_file()
        assert result == {"KEY": "value"}

    def test_result_is_sorted_by_key(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("Z_KEY=z\nA_KEY=a\n", encoding="utf-8")
        provider = _make_provider(env_file_path=env_file)
        result = provider._parse_env_file()
        assert list(result.keys()) == ["A_KEY", "Z_KEY"]


class TestCollectEnvVars:
    def test_filters_to_app_and_fx_prefixes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            os,
            "environ",
            {"APP_MODE": "paper", "FX_PAIR": "EURUSD", "UNRELATED": "ignored"},
        )
        provider = _make_provider()
        result = provider._collect_env_vars()
        assert result == {"APP_MODE": "paper", "FX_PAIR": "EURUSD"}
        assert "UNRELATED" not in result

    def test_returns_empty_when_no_matching_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "environ", {"HOME": "/home/user"})
        provider = _make_provider()
        assert provider._collect_env_vars() == {}


class TestGetEnvSecret:
    def test_returns_value_when_key_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OANDA_ACCOUNT_TYPE", "live")
        provider = _make_provider()
        assert provider.get_env_secret("OANDA_ACCOUNT_TYPE") == "live"

    def test_returns_none_when_key_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OANDA_ACCOUNT_TYPE", raising=False)
        provider = _make_provider()
        assert provider.get_env_secret("OANDA_ACCOUNT_TYPE") is None

    def test_does_not_call_repo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOME_SECRET", "s3cr3t")
        provider = _make_provider()
        provider.get_env_secret("SOME_SECRET")
        provider._repo.get.assert_not_called()


class TestComputeVersion:
    def test_returns_16_hex_chars_with_mocked_engine(self) -> None:
        repo = MagicMock()
        repo.get.return_value = None
        engine = MagicMock()
        repo._engine = engine

        conn_cm = MagicMock()
        conn_cm.__enter__ = MagicMock(return_value=MagicMock())
        conn_cm.__exit__ = MagicMock(return_value=False)

        result_mock = MagicMock()
        result_mock.__iter__ = MagicMock(return_value=iter([]))
        conn_cm.__enter__.return_value.execute.return_value = result_mock

        engine.connect.return_value = conn_cm

        provider = ConfigProvider(repo=repo)
        version = provider.compute_version()
        assert len(version) == 16
        assert all(c in "0123456789abcdef" for c in version)
