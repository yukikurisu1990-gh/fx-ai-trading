"""DictConfig-based JSON-Lines logging for paper-mode runners (M9 ops scaffold).

Provides ``apply_logging_config()`` which:

  - Renders every record as a one-line JSON object (UTC timestamp, level,
    logger, message, plus any ``extra=`` keys).
  - Writes to a rotating file (``logs/<basename>.jsonl``, 10 MiB × 5).
  - Mirrors to the console with the existing ``basicConfig``-style
    text format so interactive operators still see human output.

Existing callers using ``logging.getLogger(__name__)`` need no change —
the formatter is applied at handler level. Structured fields can be
added per-call via ``logger.info("event", extra={"key": value})`` and
will appear as top-level JSON keys.

Scope (M9 paper-loop runner scaffold):
  - This module is **only invoked by ``scripts/run_paper_loop.py``**
    today. ``supervisor/__main__.py`` and ``scripts/ctl.py`` keep their
    ``basicConfig`` for backwards compatibility — switching them is a
    separate concern.
  - No env var coupling here. ``apply_logging_config`` accepts explicit
    log dir / level / filename so callers (CLI flags, future bootstrap)
    own the policy decision.
"""

from __future__ import annotations

import json
import logging
import logging.config
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

# LogRecord attributes the standard library always sets — we exclude
# these from the "extras" pass so the JSON payload only contains
# operator-supplied fields plus our explicit standard envelope.
_STANDARD_LOGRECORD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class JsonLineFormatter(logging.Formatter):
    """Render a ``LogRecord`` as a single JSON object on one line.

    Standard envelope (always present):
        ``ts``      RFC3339 UTC timestamp with millisecond precision and ``Z`` suffix.
        ``level``   Log level name (``INFO`` / ``WARNING`` / ...).
        ``logger``  Logger name (e.g. ``scripts.run_paper_loop``).
        ``message`` Pre-rendered ``record.getMessage()``.

    Anything passed via ``extra={...}`` becomes a top-level key.
    Exception info, when present, lands under ``exc_info`` as a
    pre-formatted multi-line string.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds")
        # isoformat emits "+00:00"; we prefer "Z" to match OANDA's
        # convention (and what humans tend to grep for in JSONL).
        if ts.endswith("+00:00"):
            ts = ts[:-6] + "Z"

        payload: dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _STANDARD_LOGRECORD_KEYS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


def build_dict_config(
    *,
    log_dir: Path,
    filename: str = "paper_loop.jsonl",
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> dict[str, Any]:
    """Build the ``logging.config.dictConfig`` payload used by the runner.

    Split out so tests can introspect the resolved dict without touching
    real handlers / files.
    """
    log_path = log_dir / filename
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "fx_ai_trading.ops.logging_config.JsonLineFormatter",
            },
            "console": {
                "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": level,
            },
            "json_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "level": level,
                "filename": str(log_path),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console", "json_file"],
        },
    }


def apply_logging_config(
    *,
    log_dir: Path,
    filename: str = "paper_loop.jsonl",
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> Path:
    """Apply the JSON-Lines + rotating-file logging config.

    Creates ``log_dir`` if it does not exist (mirrors
    ``supervisor/__main__.py`` which uses the same pattern for
    ``logs/notifications.jsonl`` / ``logs/safe_stop.jsonl``).

    Returns the resolved JSONL path — useful for the runner to print
    "tail -f <path>" hints to the operator.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    config = build_dict_config(
        log_dir=log_dir,
        filename=filename,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )
    logging.config.dictConfig(config)
    return log_dir / filename
