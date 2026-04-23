"""Unit tests: ``--replay`` flag wiring in ``run_paper_evaluation`` (replay PR3).

Pins the contract that the evaluation runner:
  - Accepts ``--replay <path>`` and stores the path on ``EvaluationArgs``.
  - Errors at parse-time (NOT at run-time) when ``--replay`` points at
    a missing file — operator gets the failure before any DB / OANDA
    work begins.
  - Defaults ``replay_path`` to ``None`` (live OANDA mode).
  - Honours ``--replay`` together with ``--fast`` (the two flags are
    independent: ``--replay`` swaps the quote source, ``--fast`` removes
    inter-tick sleep).
  - In replay mode, ``main()`` does NOT consult OANDA env vars — the
    load-bearing user-facing property of PR3.  Verified by clearing
    OANDA_* from the environment and asserting that the env-reader is
    never called.

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
    alias = "_eval_under_replay_flag_test"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, _SCRIPTS_DIR / "run_paper_evaluation.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _write_jsonl_fixture(path: Path) -> None:
    """Write a 3-quote JSONL the recorder would produce — enough for
    ``ReplayQuoteFeed.__init__`` to succeed and for the smoke test to
    proceed past wiring."""
    lines = [
        {
            "ts": datetime(2026, 4, 24, 12, 0, i, tzinfo=UTC).isoformat(),
            "price": 1.10 + 0.001 * i,
            "source": "oanda_rest_snapshot",
        }
        for i in range(3)
    ]
    path.write_text("\n".join(json.dumps(ln) for ln in lines) + "\n", encoding="utf-8")


# --- parse_args ---------------------------------------------------------------


class TestReplayFlagParsing:
    def _base_argv(self, *extra: str) -> list[str]:
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

    def test_default_replay_path_is_none(self) -> None:
        ev = _load_eval()
        args = ev.parse_args(self._base_argv())
        assert args.replay_path is None

    def test_replay_flag_parses_to_path(self, tmp_path: Path) -> None:
        ev = _load_eval()
        fixture = tmp_path / "quotes.jsonl"
        _write_jsonl_fixture(fixture)

        args = ev.parse_args(self._base_argv("--replay", str(fixture)))

        assert args.replay_path == fixture
        assert isinstance(args.replay_path, Path)

    def test_replay_missing_file_errors_at_parse_time(self, tmp_path: Path) -> None:
        # Operator must see the failure before any DB / OANDA work
        # begins — argparse.error() raises SystemExit(2) by convention.
        ev = _load_eval()
        missing = tmp_path / "does_not_exist.jsonl"

        with pytest.raises(SystemExit):
            ev.parse_args(self._base_argv("--replay", str(missing)))

    def test_replay_combines_with_fast(self, tmp_path: Path) -> None:
        # --replay swaps the quote source; --fast removes inter-tick
        # sleep.  They are independent and must compose.
        ev = _load_eval()
        fixture = tmp_path / "quotes.jsonl"
        _write_jsonl_fixture(fixture)

        args = ev.parse_args(self._base_argv("--replay", str(fixture), "--fast"))

        assert args.replay_path == fixture
        assert args.fast is True


# --- main() does not consult OANDA env in replay mode ------------------------


class TestReplayModeSkipsOandaEnv:
    def test_main_with_replay_does_not_call_read_oanda_config_from_env(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # The load-bearing PR3 contract: an operator with NO OANDA
        # credentials must be able to run --replay.  We clear all OANDA
        # env vars, install a tripwire on read_oanda_config_from_env,
        # and assert main() reaches return 0 without tripping it.
        for var in ("OANDA_ACCESS_TOKEN", "OANDA_ACCOUNT_ID", "OANDA_ENVIRONMENT"):
            monkeypatch.delenv(var, raising=False)

        ev = _load_eval()
        exit_lib = ev._exit_lib()
        entry = ev._entry_lib()

        env_reader_calls = {"n": 0}

        def _trip_env_reader(*_a: object, **_kw: object) -> object:
            env_reader_calls["n"] += 1
            raise AssertionError("main() must NOT call read_oanda_config_from_env in replay mode")

        monkeypatch.setattr(exit_lib, "read_oanda_config_from_env", _trip_env_reader)

        # Stub the DB / wiring / loop / aggregation so we exercise only
        # the env-decision branch.
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

        fixture = tmp_path / "quotes.jsonl"
        _write_jsonl_fixture(fixture)

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
                "--replay",
                str(fixture),
                "--log-dir",
                str(tmp_path / "logs"),
            ]
        )

        assert rc == 0
        assert env_reader_calls["n"] == 0

        # And: build_components received a ReplayQuoteFeed, not None.
        from fx_ai_trading.adapters.price_feed.replay_quote_feed import ReplayQuoteFeed

        feed = captured["components_kwargs"]["quote_feed"]
        assert isinstance(feed, ReplayQuoteFeed)


# --- live mode still requires OANDA env --------------------------------------


class TestLiveModeStillRequiresOandaEnv:
    def test_main_without_replay_returns_rc2_when_oanda_env_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Negative check: PR3 must NOT change live-mode behaviour.
        # When --replay is absent and OANDA env is missing, main() still
        # surfaces rc=2 (existing contract from §10.9 runbook).
        for var in ("OANDA_ACCESS_TOKEN", "OANDA_ACCOUNT_ID", "OANDA_ENVIRONMENT"):
            monkeypatch.delenv(var, raising=False)

        ev = _load_eval()

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
                "--log-dir",
                str(tmp_path / "logs"),
            ]
        )

        assert rc == 2
