"""Contract test — Bootstrap form is disabled when Supervisor is running.

Per ``operations.md`` §15.2 / ``m26_implementation_plan.md`` §4.3:
when ``ProcessManager.is_running() == True``, the Bootstrap UI MUST NOT
render an editable form. Only a read-only warning is allowed.
"""

from __future__ import annotations

from unittest.mock import patch

from fx_ai_trading.dashboard.config_console import bootstrap_view


class _Ctx:
    """Stand-in for Streamlit return values: context manager + empty-string-like."""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def strip(self) -> str:
        return ""

    def __bool__(self) -> bool:
        return False

    def __len__(self) -> int:
        return 0


class _StubPM:
    def __init__(self, *, running: bool) -> None:
        self._running = running

    def is_running(self) -> bool:
        return self._running


class _StreamlitRecorder:
    """Captures every Streamlit call so we can assert what got rendered."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def recorder(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return _Ctx()

        return recorder

    def columns(self, *args, **kwargs):
        self.calls.append(("columns", args, kwargs))
        n = args[0] if args else 1
        count = n if isinstance(n, int) else len(n)
        return tuple(_Ctx() for _ in range(count))

    def names(self) -> list[str]:
        return [name for name, _, _ in self.calls]


def test_form_not_rendered_when_pm_running() -> None:
    recorder = _StreamlitRecorder()
    with patch("fx_ai_trading.dashboard.config_console.bootstrap_view.st", recorder):
        bootstrap_view.render(engine=None, process_manager=_StubPM(running=True))

    forbidden = {
        "text_input",
        "text_area",
        "button",
        "form",
        "form_submit_button",
    }
    rendered = set(recorder.names())
    leaked = rendered & forbidden
    assert not leaked, f"Bootstrap form must not render when running; got: {leaked}"


def test_form_rendered_when_pm_idle(tmp_path) -> None:
    env = tmp_path / ".env"
    env.write_text("EXISTING=v\n", encoding="utf-8")
    recorder = _StreamlitRecorder()
    with patch("fx_ai_trading.dashboard.config_console.bootstrap_view.st", recorder):
        bootstrap_view.render(engine=None, process_manager=_StubPM(running=False), env_path=env)

    rendered = set(recorder.names())
    assert "form" in rendered
    assert "text_area" in rendered
    assert "text_input" in rendered
    assert "form_submit_button" in rendered


def test_form_uses_clear_on_submit() -> None:
    """clear_on_submit=True is required so plaintext secrets do not persist
    in session_state across reruns (development_rules.md §10.3.1)."""
    recorder = _StreamlitRecorder()
    with patch("fx_ai_trading.dashboard.config_console.bootstrap_view.st", recorder):
        bootstrap_view.render(engine=None, process_manager=_StubPM(running=False))

    form_calls = [c for c in recorder.calls if c[0] == "form"]
    assert form_calls, "st.form must be used to wrap secret inputs"
    _, _, kwargs = form_calls[0]
    assert kwargs.get("clear_on_submit") is True, "st.form must be called with clear_on_submit=True"


def test_warning_message_when_running() -> None:
    recorder = _StreamlitRecorder()
    with patch("fx_ai_trading.dashboard.config_console.bootstrap_view.st", recorder):
        bootstrap_view.render(engine=None, process_manager=_StubPM(running=True))

    warning_calls = [c for c in recorder.calls if c[0] == "warning"]
    assert warning_calls, "Expected at least one st.warning call when PM is running"
    msg = warning_calls[0][1][0]
    assert "running" in msg.lower() or "stop" in msg.lower()
