"""Contract tests: Configuration Console Runtime tab must not expose secrets
or allow editing of read-only keys (M26 Phase 2 + Phase 3 transition).

Verifies the 3-layer defense for Runtime mode:
  1. Pure-helper level — `is_editable` rejects secret patterns and
     read-only keys (`expected_account_type`).
  2. Source level — page file wires both Runtime and Bootstrap tabs (P3).
  3. Source level — runtime view file does not invoke `UPDATE app_settings`
     and does not contain any `.env` write path (those live in Bootstrap).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fx_ai_trading.dashboard.config_console import runtime_view

_PAGE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "fx_ai_trading"
    / "dashboard"
    / "pages"
    / "2_Configuration_Console.py"
)

_RUNTIME_VIEW_PATH = Path(runtime_view.__file__)


class TestIsEditableHelper:
    def test_expected_account_type_is_not_editable(self) -> None:
        assert runtime_view.is_editable("expected_account_type") is False

    @pytest.mark.parametrize(
        "name",
        [
            "OANDA_API_KEY",
            "oanda_api_key",
            "SMTP_PASSWORD",
            "SUPABASE_API_KEY",
            "SLACK_WEBHOOK_TOKEN",
            "ANY_PRIVATE_KEY",
            "STORED_CREDENTIAL",
            "session_secret",
        ],
    )
    def test_secret_like_keys_are_not_editable(self, name: str) -> None:
        assert runtime_view.is_secret_like(name) is True
        assert runtime_view.is_editable(name) is False

    @pytest.mark.parametrize(
        "name",
        [
            "risk_per_trade_pct",
            "max_concurrent_positions",
            "phase_mode",
            "runtime_environment",
            "strategy.AI.enabled",
            "ui_polling_interval_seconds_min",
        ],
    )
    def test_normal_runtime_keys_are_editable(self, name: str) -> None:
        assert runtime_view.is_secret_like(name) is False
        assert runtime_view.is_editable(name) is True


class TestPageFile:
    def test_page_file_exists(self) -> None:
        assert _PAGE_PATH.exists(), f"Configuration Console page missing at {_PAGE_PATH}"

    def test_page_imports_runtime_view(self) -> None:
        src = _PAGE_PATH.read_text(encoding="utf-8")
        assert "runtime_view" in src

    def test_page_has_tabs_runtime_first(self) -> None:
        src = _PAGE_PATH.read_text(encoding="utf-8")
        assert "st.tabs(" in src
        assert '"Runtime"' in src
        assert src.index('"Runtime"') < src.index('"Bootstrap')

    def test_page_calls_bootstrap_view(self) -> None:
        """P3: Bootstrap tab is wired via bootstrap_view.render(engine)."""
        src = _PAGE_PATH.read_text(encoding="utf-8")
        assert "bootstrap_view" in src
        assert "bootstrap_view.render" in src


class TestRuntimeViewSource:
    def test_does_not_invoke_update_app_settings(self) -> None:
        src = _RUNTIME_VIEW_PATH.read_text(encoding="utf-8").lower()
        assert "update app_settings" not in src

    def test_does_not_write_env_file(self) -> None:
        """Runtime view must not contain any code path that writes to .env —
        that belongs to Bootstrap (P3). Docstring references for context are
        allowed; actual write-API calls are not."""
        src = _RUNTIME_VIEW_PATH.read_text(encoding="utf-8")
        forbidden_write_patterns = (
            'open(".env"',
            "open('.env'",
            'Path(".env"',
            "Path('.env'",
            "os.replace",
            "env_writer",
            "bootstrap_view",
        )
        for needle in forbidden_write_patterns:
            assert needle not in src, f"Runtime view must not contain .env write path: {needle!r}"

    def test_uses_required_ux_wording(self) -> None:
        """Submit + success must explicitly say "queue / 再起動 / hot-reload"
        — not "Save" or "Apply" alone."""
        src = _RUNTIME_VIEW_PATH.read_text(encoding="utf-8")
        assert "キューに登録" in src
        assert "再起動" in src or "hot-reload" in src

    def test_does_not_use_save_or_apply_alone_as_button_label(self) -> None:
        src = _RUNTIME_VIEW_PATH.read_text(encoding="utf-8")
        button_lines = [
            line
            for line in src.splitlines()
            if "st.button(" in line or "SUBMIT_BUTTON_LABEL" in line
        ]
        for line in button_lines:
            stripped = line.strip()
            assert not stripped.startswith('st.button("Save"')
            assert not stripped.startswith('st.button("Apply"')
            assert not stripped.startswith("st.button('Save'")
            assert not stripped.startswith("st.button('Apply'")
