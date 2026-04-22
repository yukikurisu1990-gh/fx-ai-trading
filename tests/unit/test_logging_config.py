"""Unit tests: ``fx_ai_trading.ops.logging_config`` (M9 paper-loop runner scaffold).

Pins the contract that the JSON-Lines formatter:
  - Renders one JSON object per record.
  - Always emits the ``ts``/``level``/``logger``/``message`` envelope.
  - Promotes ``extra={...}`` keys to top-level JSON keys.
  - Suffixes ``ts`` with ``Z`` (matches OANDA convention so operators
    can grep across log streams uniformly).
  - Includes ``exc_info`` when an exception is logged.

And that ``apply_logging_config`` actually wires a rotating file
handler into the root logger and returns the resolved path so the
runner can echo it to operators.
"""

from __future__ import annotations

import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fx_ai_trading.ops.logging_config import (
    JsonLineFormatter,
    apply_logging_config,
    build_dict_config,
)


def _format_one(record: logging.LogRecord) -> dict:
    return json.loads(JsonLineFormatter().format(record))


def _make_record(
    *,
    name: str = "scripts.run_paper_loop",
    level: int = logging.INFO,
    msg: str = "tick.completed",
    extra: dict | None = None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=42,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


class TestJsonLineFormatterEnvelope:
    def test_returns_valid_single_line_json(self) -> None:
        out = JsonLineFormatter().format(_make_record())
        assert "\n" not in out
        json.loads(out)

    def test_envelope_contains_standard_keys(self) -> None:
        payload = _format_one(_make_record())
        assert set(payload).issuperset({"ts", "level", "logger", "message"})
        assert payload["level"] == "INFO"
        assert payload["logger"] == "scripts.run_paper_loop"
        assert payload["message"] == "tick.completed"

    def test_ts_is_rfc3339_with_millis_and_z_suffix(self) -> None:
        payload = _format_one(_make_record())
        # YYYY-MM-DDTHH:MM:SS.mmmZ
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", payload["ts"])


class TestJsonLineFormatterExtras:
    def test_extras_promoted_to_top_level(self) -> None:
        payload = _format_one(
            _make_record(
                extra={
                    "event": "tick.completed",
                    "iteration": 7,
                    "results_count": 0,
                    "tick_duration_ms": 1.234,
                }
            )
        )
        assert payload["event"] == "tick.completed"
        assert payload["iteration"] == 7
        assert payload["results_count"] == 0
        assert payload["tick_duration_ms"] == 1.234

    def test_standard_logrecord_attrs_not_leaked(self) -> None:
        """Extras must not include ``args``/``msecs``/``pathname``/etc.

        Otherwise every line would carry noisy stdlib internals that
        change with Python version and bloat the JSONL."""
        payload = _format_one(_make_record())
        for noisy in ("args", "msecs", "pathname", "lineno", "funcName", "module"):
            assert noisy not in payload

    def test_exc_info_present_when_raised(self) -> None:
        log = logging.getLogger("test.exc")
        log.handlers.clear()
        captured: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(JsonLineFormatter().format(record))

        log.addHandler(_Capture())
        log.setLevel(logging.ERROR)
        try:
            raise ValueError("boom")
        except ValueError:
            log.exception("caught")

        assert len(captured) == 1
        payload = json.loads(captured[0])
        assert payload["message"] == "caught"
        assert "ValueError: boom" in payload["exc_info"]


class TestBuildDictConfig:
    def test_rotation_handler_resolves_to_log_dir_filename(self, tmp_path: Path) -> None:
        cfg = build_dict_config(log_dir=tmp_path, filename="paper.jsonl")
        rh = cfg["handlers"]["json_file"]
        assert rh["class"] == "logging.handlers.RotatingFileHandler"
        assert rh["filename"] == str(tmp_path / "paper.jsonl")
        assert rh["maxBytes"] == 10 * 1024 * 1024
        assert rh["backupCount"] == 5

    def test_root_handlers_include_console_and_json_file(self, tmp_path: Path) -> None:
        cfg = build_dict_config(log_dir=tmp_path)
        assert cfg["root"]["handlers"] == ["console", "json_file"]

    def test_level_is_threaded_through(self, tmp_path: Path) -> None:
        cfg = build_dict_config(log_dir=tmp_path, level="DEBUG")
        assert cfg["root"]["level"] == "DEBUG"
        assert cfg["handlers"]["console"]["level"] == "DEBUG"
        assert cfg["handlers"]["json_file"]["level"] == "DEBUG"


class TestApplyLoggingConfig:
    def test_creates_log_dir_and_returns_path(self, tmp_path: Path) -> None:
        target_dir = tmp_path / "fresh_logs"
        assert not target_dir.exists()
        path = apply_logging_config(log_dir=target_dir, filename="paper.jsonl")
        assert target_dir.is_dir()
        assert path == target_dir / "paper.jsonl"

    def test_writes_json_lines_to_rotating_file(self, tmp_path: Path) -> None:
        path = apply_logging_config(log_dir=tmp_path, filename="paper.jsonl")
        try:
            log = logging.getLogger("test.apply.json_file")
            log.info("hello", extra={"event": "smoke"})
            # Ensure handler flushes before we read.
            for h in logging.getLogger().handlers:
                h.flush()
            content = path.read_text(encoding="utf-8")
            lines = [line for line in content.splitlines() if line.strip()]
            payloads = [json.loads(line) for line in lines]
            assert any(p.get("event") == "smoke" and p.get("message") == "hello" for p in payloads)
        finally:
            # Detach handlers to avoid leaking file handles into other
            # tests in the same process.
            root = logging.getLogger()
            for h in list(root.handlers):
                if isinstance(h, RotatingFileHandler):
                    h.close()
                    root.removeHandler(h)
