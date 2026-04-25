"""Unit tests: scripts/run_paper_decision_loop.py argparse seam (Phase 9.19/J-3)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_RUNNER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_paper_decision_loop.py"
_spec = importlib.util.spec_from_file_location("paper_decision_runner", _RUNNER_PATH)
runner = importlib.util.module_from_spec(_spec)
sys.modules["paper_decision_runner"] = runner
assert _spec.loader is not None
_spec.loader.exec_module(runner)


# ---------------------------------------------------------------------------
# Existing flags should still parse with no value
# ---------------------------------------------------------------------------


class TestExistingFlags:
    def test_default_args_parse(self) -> None:
        args = runner._parse_args([])
        # Phase 9.19/J-3 default — no behaviour change.
        assert args.top_k == 1
        assert args.dry_run is False
        assert args.granularity == "M5"

    def test_dry_run_flag(self) -> None:
        args = runner._parse_args(["--dry-run"])
        assert args.dry_run is True


# ---------------------------------------------------------------------------
# Phase 9.19/J-3 --top-k flag
# ---------------------------------------------------------------------------


class TestTopKFlag:
    def test_top_k_default_is_one(self) -> None:
        args = runner._parse_args([])
        assert args.top_k == 1

    def test_top_k_explicit_two(self) -> None:
        args = runner._parse_args(["--top-k", "2"])
        assert args.top_k == 2

    def test_top_k_zero_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--top-k", "0"])

    def test_top_k_negative_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--top-k", "-1"])

    def test_top_k_non_integer_rejected(self) -> None:
        # argparse type=int rejects floats / non-numeric input.
        with pytest.raises(SystemExit):
            runner._parse_args(["--top-k", "1.5"])
        with pytest.raises(SystemExit):
            runner._parse_args(["--top-k", "x"])

    def test_top_k_three_accepted(self) -> None:
        args = runner._parse_args(["--top-k", "3"])
        assert args.top_k == 3
