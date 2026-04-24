"""Unit tests: ``--replay-candles`` flag wiring in ``run_paper_evaluation``.

Pins the contract that the evaluation runner:
  - Accepts ``--replay-candles <path>`` and stores it on
    ``EvaluationArgs.replay_candles_path``.
  - Errors at parse-time when ``--replay-candles`` points at a missing
    file (matches ``--replay`` semantics).
  - Defaults ``replay_candles_path`` to ``None``.
  - Rejects ``--replay`` and ``--replay-candles`` set simultaneously
    (mutually exclusive — they would race on which feed to wire).
  - In replay-candles mode, ``main()`` does NOT consult OANDA env vars,
    builds a ``CandleReplayQuoteFeed`` (NOT a ``ReplayQuoteFeed``), and
    threads it into ``build_components``.

The tests stub out ``build_components`` / ``build_supervisor_with_paper_stack``
/ ``run_eval_ticks`` / ``aggregate_metrics`` / ``build_db_engine`` so no
DB or network is touched.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"


def _load_eval() -> Any:
    alias = "_eval_under_replay_candles_flag_test"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, _SCRIPTS_DIR / "run_paper_evaluation.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _write_candles_fixture(path: Path, n: int = 3) -> None:
    """Write an n-candle JSONL in the ``fetch_oanda_candles`` shape — enough
    for ``CandleReplayQuoteFeed.__init__`` to succeed."""
    lines = [
        {
            "time": (
                datetime(2026, 4, 24, 12, 0, i, tzinfo=UTC).isoformat().replace("+00:00", "Z")
            ),
            "o": 1.10 + 0.001 * i,
            "h": 1.11 + 0.001 * i,
            "l": 1.09 + 0.001 * i,
            "c": 1.105 + 0.001 * i,
            "volume": 17 + i,
        }
        for i in range(n)
    ]
    path.write_text("\n".join(json.dumps(ln) for ln in lines) + "\n", encoding="utf-8")


def _write_quotes_fixture(path: Path) -> None:
    """``ReplayQuoteFeed``-shape fixture for the mutex test."""
    lines = [
        {
            "ts": datetime(2026, 4, 24, 12, 0, i, tzinfo=UTC).isoformat(),
            "price": 1.10 + 0.001 * i,
            "source": "oanda_rest_snapshot",
        }
        for i in range(3)
    ]
    path.write_text("\n".join(json.dumps(ln) for ln in lines) + "\n", encoding="utf-8")


def _base_argv(*extra: str) -> list[str]:
    return [
        "--account-id",
        "acct-test",
        "--instrument",
        "EUR_USD",
        "--direction",
        "buy",
        "--strategy",
        "minimum",
        "--max-iterations",
        "10",
        *extra,
    ]


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


class TestReplayCandlesFlagParsing:
    def test_default_replay_candles_path_is_none(self) -> None:
        ev = _load_eval()
        args = ev.parse_args(_base_argv())
        assert args.replay_candles_path is None

    def test_replay_candles_flag_parses_to_path(self, tmp_path: Path) -> None:
        ev = _load_eval()
        fixture = tmp_path / "candles.jsonl"
        _write_candles_fixture(fixture)

        args = ev.parse_args(_base_argv("--replay-candles", str(fixture)))

        assert args.replay_candles_path == fixture
        assert isinstance(args.replay_candles_path, Path)

    def test_missing_file_errors_at_parse_time(self, tmp_path: Path) -> None:
        ev = _load_eval()
        missing = tmp_path / "does_not_exist.jsonl"

        with pytest.raises(SystemExit):
            ev.parse_args(_base_argv("--replay-candles", str(missing)))

    def test_replay_and_replay_candles_are_mutually_exclusive(self, tmp_path: Path) -> None:
        ev = _load_eval()
        candles = tmp_path / "candles.jsonl"
        quotes = tmp_path / "quotes.jsonl"
        _write_candles_fixture(candles)
        _write_quotes_fixture(quotes)

        with pytest.raises(SystemExit):
            ev.parse_args(
                _base_argv(
                    "--replay",
                    str(quotes),
                    "--replay-candles",
                    str(candles),
                )
            )

    def test_replay_candles_combines_with_fast(self, tmp_path: Path) -> None:
        ev = _load_eval()
        fixture = tmp_path / "candles.jsonl"
        _write_candles_fixture(fixture)

        args = ev.parse_args(_base_argv("--replay-candles", str(fixture), "--fast"))

        assert args.replay_candles_path == fixture
        assert args.fast is True


# ---------------------------------------------------------------------------
# main() in replay-candles mode
# ---------------------------------------------------------------------------


class TestReplayCandlesModeWiresCandleFeed:
    def test_main_uses_candle_replay_feed_not_quote_replay_feed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for var in ("OANDA_ACCESS_TOKEN", "OANDA_ACCOUNT_ID", "OANDA_ENVIRONMENT"):
            monkeypatch.delenv(var, raising=False)

        ev = _load_eval()
        exit_lib = ev._exit_lib()
        entry = ev._entry_lib()

        env_reader_calls = {"n": 0}

        def _trip_env_reader(*_a: object, **_kw: object) -> object:
            env_reader_calls["n"] += 1
            raise AssertionError(
                "main() must NOT call read_oanda_config_from_env in replay-candles mode"
            )

        monkeypatch.setattr(exit_lib, "read_oanda_config_from_env", _trip_env_reader)
        monkeypatch.setattr(exit_lib, "build_db_engine", lambda env=None: object())

        captured: dict[str, Any] = {}

        def _fake_build_components(**kw: object) -> object:
            captured["components_kwargs"] = kw
            return SimpleNamespace(
                state_manager=object(),
                orders=object(),
                broker=object(),
                quote_feed=kw.get("quote_feed"),
                clock=object(),
                signal=object(),
            )

        def _fake_build_supervisor(**kw: object) -> tuple[object, object]:
            captured["supervisor_kwargs"] = kw
            return object(), kw.get("quote_feed")

        def _fake_run_ticks(**_kw: object) -> tuple[datetime, datetime, int, int]:
            t = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)
            return t, t, 0, 0

        def _fake_aggregate(**_kw: object) -> dict[str, object]:
            return {"strategy": "minimum", "ticks_executed": 0}

        monkeypatch.setattr(entry, "build_components", _fake_build_components)
        monkeypatch.setattr(exit_lib, "build_supervisor_with_paper_stack", _fake_build_supervisor)
        monkeypatch.setattr(ev, "run_eval_ticks", _fake_run_ticks)
        monkeypatch.setattr(ev, "aggregate_metrics", _fake_aggregate)

        fixture = tmp_path / "candles.jsonl"
        _write_candles_fixture(fixture)

        rc = ev.main(
            [
                "--account-id",
                "acct-test",
                "--instrument",
                "EUR_USD",
                "--direction",
                "buy",
                "--strategy",
                "minimum",
                "--max-iterations",
                "1",
                "--replay-candles",
                str(fixture),
                "--log-dir",
                str(tmp_path / "logs"),
            ]
        )

        assert rc == 0
        assert env_reader_calls["n"] == 0

        from fx_ai_trading.adapters.price_feed.candle_replay_quote_feed import (
            CandleReplayQuoteFeed,
        )
        from fx_ai_trading.adapters.price_feed.replay_quote_feed import ReplayQuoteFeed

        feed = captured["components_kwargs"]["quote_feed"]
        assert isinstance(feed, CandleReplayQuoteFeed)
        # Defining negative: must NOT be the quote replay feed.
        assert not isinstance(feed, ReplayQuoteFeed)
