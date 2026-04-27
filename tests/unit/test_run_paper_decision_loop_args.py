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


# ---------------------------------------------------------------------------
# Phase 9.X-B/J-4 --feature-groups flag (plumbing only)
# ---------------------------------------------------------------------------


class TestFeatureGroupsFlag:
    def test_feature_groups_default_empty(self) -> None:
        args = runner._parse_args([])
        assert args.feature_groups == ""
        assert args.feature_groups_set == frozenset()

    def test_feature_groups_mtf_accepted(self) -> None:
        args = runner._parse_args(["--feature-groups", "mtf"])
        assert args.feature_groups_set == frozenset({"mtf"})

    def test_feature_groups_combination_accepted(self) -> None:
        # Phase 9.X-B amendment: "moments" was scoped during J-4 plumbing
        # but never wired into FeatureService — only "vol" and "mtf" remain.
        args = runner._parse_args(["--feature-groups", "vol,mtf"])
        assert args.feature_groups_set == frozenset({"vol", "mtf"})

    def test_feature_groups_whitespace_stripped(self) -> None:
        args = runner._parse_args(["--feature-groups", " mtf , vol "])
        assert args.feature_groups_set == frozenset({"mtf", "vol"})

    def test_feature_groups_invalid_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--feature-groups", "garbage"])

    def test_feature_groups_partial_invalid_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner._parse_args(["--feature-groups", "mtf,xyz"])

    def test_feature_groups_empty_string_in_list(self) -> None:
        # Trailing comma is tolerated
        args = runner._parse_args(["--feature-groups", "mtf,"])
        assert args.feature_groups_set == frozenset({"mtf"})


# ---------------------------------------------------------------------------
# Phase 9.5-A --max-spread-pip flag + _fetch_spread_pips helper
# ---------------------------------------------------------------------------


class TestMaxSpreadPipFlag:
    def test_default_is_2_0(self) -> None:
        args = runner._parse_args([])
        assert args.max_spread_pip == 2.0

    def test_custom_value_accepted(self) -> None:
        args = runner._parse_args(["--max-spread-pip", "1.5"])
        assert args.max_spread_pip == 1.5

    def test_zero_accepted(self) -> None:
        args = runner._parse_args(["--max-spread-pip", "0.0"])
        assert args.max_spread_pip == 0.0


class TestFetchSpreadPips:
    def _mock_client(self, bid: float, ask: float):
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_pricing.return_value = [
            {"bids": [{"price": str(bid)}], "asks": [{"price": str(ask)}]}
        ]
        return client

    def test_normal_spread(self) -> None:
        client = self._mock_client(159.000, 159.010)
        pip = runner._fetch_spread_pips(client, "acct1", "USD_JPY")
        assert pip == pytest.approx(1.0, abs=0.01)

    def test_eur_usd_spread(self) -> None:
        client = self._mock_client(1.10000, 1.10020)
        pip = runner._fetch_spread_pips(client, "acct1", "EUR_USD")
        assert pip == pytest.approx(2.0, abs=0.01)

    def test_empty_prices_returns_none(self) -> None:
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_pricing.return_value = []
        assert runner._fetch_spread_pips(client, "acct1", "EUR_USD") is None

    def test_api_error_returns_none(self) -> None:
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_pricing.side_effect = RuntimeError("network error")
        assert runner._fetch_spread_pips(client, "acct1", "EUR_USD") is None

    def test_unknown_instrument_uses_default_pip(self) -> None:
        client = self._mock_client(1.00000, 1.00010)
        pip = runner._fetch_spread_pips(client, "acct1", "XYZ_ABC")
        assert pip == pytest.approx(1.0, abs=0.01)
