"""Unit tests for the ``--fast`` mode of the paper evaluation runner.

The ``--fast`` flag short-circuits the inter-tick ``time.sleep`` while
leaving every other part of the tick (quote fetch, signal evaluation,
policy decision, open / close path, PnL) untouched.  These tests pin
that contract via two narrow surfaces:

1. **CLI plumbing** — ``parse_args`` exposes ``--fast`` as a
   ``store_true`` flag (default ``False``).
2. **Loop behaviour** — when ``fast=True`` is passed to
   ``run_eval_ticks`` the injected ``sleep_fn`` is *never* called;
   when ``fast=False`` it is called ``max_iterations - 1`` times and
   each call forwards ``interval_seconds``.  Policy evaluation and
   supervisor exit-gate ticks are driven on every iteration either way,
   so the two modes are functionally equivalent aside from pacing.

We avoid a live OANDA / DB / policy stack by injecting a fake ``entry``
lib (via monkeypatching ``module._entry_lib``) whose
``MinimumEntryPolicy`` is a stub that returns a ``no_signal`` decision.
This keeps the test pure and lets us count sleep / supervisor calls
without schema or network setup.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_paper_evaluation.py"

_FIXED_TS = datetime(2026, 4, 23, 14, 0, 0, tzinfo=UTC)


def _load_module() -> Any:
    alias = "_paper_evaluation_under_fast_mode_test"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class _StubDecision:
    should_fire: bool
    reason: str


class _StubPolicy:
    """Returns a stable ``no_signal`` decision every evaluate()."""

    def __init__(self, **_kwargs: Any) -> None:
        self.calls = 0

    def evaluate(self) -> _StubDecision:
        self.calls += 1
        return _StubDecision(should_fire=False, reason="no_signal")


class _StubClock:
    def now(self) -> datetime:
        return _FIXED_TS


class _StubSupervisor:
    def __init__(self) -> None:
        self.exit_tick_calls = 0

    def run_exit_gate_tick(self) -> None:
        self.exit_tick_calls += 1


class _RecordingSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _make_fake_entry_lib() -> Any:
    """Minimal stand-in for ``run_paper_entry_loop`` used by the runner.

    Exposes only the attributes ``run_eval_ticks`` reads:
    ``MinimumEntryPolicy`` (our stub), and the two exception classes
    caught around ``_open_one_position`` — never raised here because
    ``should_fire`` is always False.  ``_open_one_position`` itself is
    provided but never invoked.
    """

    class DuplicateOpenInstrumentError(Exception):
        pass

    class BrokerDidNotFillError(Exception):
        pass

    def _open_one_position(**_kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("should_fire is False; open path must not be taken")

    return SimpleNamespace(
        MinimumEntryPolicy=_StubPolicy,
        DuplicateOpenInstrumentError=DuplicateOpenInstrumentError,
        BrokerDidNotFillError=BrokerDidNotFillError,
        _open_one_position=_open_one_position,
    )


def _make_components() -> Any:
    return SimpleNamespace(
        state_manager=object(),
        quote_feed=object(),
        clock=_StubClock(),
    )


def _run(
    *,
    module: Any,
    fast: bool,
    max_iterations: int,
    interval_seconds: float,
    sleep_fn: _RecordingSleep,
    supervisor: _StubSupervisor,
) -> tuple[int, int]:
    _start, _end, ticks, no_signal = module.run_eval_ticks(
        components=_make_components(),
        supervisor=supervisor,
        instrument="EUR_USD",
        direction="buy",
        units=1000,
        account_id="acct-fast-test",
        account_type="demo",
        interval_seconds=interval_seconds,
        max_iterations=max_iterations,
        stale_after_seconds=60.0,
        signals=[],
        log=logging.getLogger("test.fast_mode"),
        fast=fast,
        sleep_fn=sleep_fn,
    )
    return ticks, no_signal


class TestParseArgsFastFlag:
    """``--fast`` defaults to False and is exposed on ``EvaluationArgs``."""

    def _base_argv(self) -> list[str]:
        return [
            "--account-id",
            "acct-x",
            "--direction",
            "buy",
            "--strategy",
            "minimum",
            "--max-iterations",
            "10",
        ]

    def test_default_is_false(self) -> None:
        mod = _load_module()
        args = mod.parse_args(self._base_argv())
        assert args.fast is False

    def test_flag_sets_true(self) -> None:
        mod = _load_module()
        args = mod.parse_args([*self._base_argv(), "--fast"])
        assert args.fast is True


class TestRunEvalTicksFastMode:
    """Fast-mode skips sleep; non-fast sleeps (N-1) times at the chosen interval."""

    def test_fast_skips_sleep(self, monkeypatch) -> None:
        mod = _load_module()
        monkeypatch.setattr(mod, "_entry_lib", _make_fake_entry_lib)

        sleep_fn = _RecordingSleep()
        supervisor = _StubSupervisor()

        ticks, no_signal = _run(
            module=mod,
            fast=True,
            max_iterations=5,
            interval_seconds=1.0,
            sleep_fn=sleep_fn,
            supervisor=supervisor,
        )

        assert sleep_fn.calls == []
        assert ticks == 5
        assert no_signal == 5
        assert supervisor.exit_tick_calls == 5

    def test_non_fast_sleeps_between_ticks(self, monkeypatch) -> None:
        mod = _load_module()
        monkeypatch.setattr(mod, "_entry_lib", _make_fake_entry_lib)

        sleep_fn = _RecordingSleep()
        supervisor = _StubSupervisor()

        ticks, no_signal = _run(
            module=mod,
            fast=False,
            max_iterations=5,
            interval_seconds=0.25,
            sleep_fn=sleep_fn,
            supervisor=supervisor,
        )

        # N-1 sleeps between N iterations, each at the requested interval.
        assert sleep_fn.calls == [0.25, 0.25, 0.25, 0.25]
        assert ticks == 5
        assert no_signal == 5
        assert supervisor.exit_tick_calls == 5

    def test_fast_and_non_fast_drive_identical_policy_and_exit_calls(self, monkeypatch) -> None:
        """Same iteration count and same side-effect call counts across modes.

        Only the number of ``sleep_fn`` calls differs — policy evaluations
        and exit-gate ticks must match.  This is the "same result, only
        time differs" contract the PR description pins.
        """
        mod = _load_module()
        monkeypatch.setattr(mod, "_entry_lib", _make_fake_entry_lib)

        sleep_fast = _RecordingSleep()
        sv_fast = _StubSupervisor()
        ticks_fast, no_signal_fast = _run(
            module=mod,
            fast=True,
            max_iterations=7,
            interval_seconds=1.0,
            sleep_fn=sleep_fast,
            supervisor=sv_fast,
        )

        sleep_slow = _RecordingSleep()
        sv_slow = _StubSupervisor()
        ticks_slow, no_signal_slow = _run(
            module=mod,
            fast=False,
            max_iterations=7,
            interval_seconds=1.0,
            sleep_fn=sleep_slow,
            supervisor=sv_slow,
        )

        assert ticks_fast == ticks_slow == 7
        assert no_signal_fast == no_signal_slow == 7
        assert sv_fast.exit_tick_calls == sv_slow.exit_tick_calls == 7
        # Only difference: the sleep count.
        assert len(sleep_fast.calls) == 0
        assert len(sleep_slow.calls) == 6
