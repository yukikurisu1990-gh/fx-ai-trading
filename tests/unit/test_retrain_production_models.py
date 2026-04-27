"""Unit tests: retrain_production_models.py (Task 2 — model retrain helper)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "retrain_production_models.py"
_spec = importlib.util.spec_from_file_location("retrain_production_models", _SCRIPT_PATH)
retrain = importlib.util.module_from_spec(_spec)
sys.modules["retrain_production_models"] = retrain
assert _spec.loader is not None
_spec.loader.exec_module(retrain)


class TestAllPairs:
    def test_all_pairs_has_20_entries(self) -> None:
        assert len(retrain._ALL_PAIRS) == 20

    def test_all_pairs_no_duplicates(self) -> None:
        assert len(retrain._ALL_PAIRS) == len(set(retrain._ALL_PAIRS))

    def test_all_pairs_underscore_format(self) -> None:
        for pair in retrain._ALL_PAIRS:
            assert "_" in pair, f"{pair} missing underscore"
            parts = pair.split("_")
            assert len(parts) == 2, f"{pair} has unexpected format"

    def test_key_pairs_present(self) -> None:
        assert "EUR_USD" in retrain._ALL_PAIRS
        assert "USD_JPY" in retrain._ALL_PAIRS
        assert "GBP_USD" in retrain._ALL_PAIRS


class TestArgParsing:
    def _parse(self, argv: list[str]) -> object:
        import argparse

        p = argparse.ArgumentParser()
        p.add_argument("--pairs", nargs="*", default=None)
        p.add_argument("--skip-fetch", action="store_true", default=False)
        p.add_argument("--days", type=int, default=365)
        p.add_argument("--data-dir", default="data")
        p.add_argument("--model-dir", default="models/lgbm")
        p.add_argument("--train-frac", type=float, default=0.80)
        return p.parse_args(argv)

    def test_defaults(self) -> None:
        args = self._parse([])
        assert args.pairs is None
        assert args.skip_fetch is False
        assert args.days == 365
        assert args.data_dir == "data"
        assert args.model_dir == "models/lgbm"
        assert args.train_frac == pytest.approx(0.80)

    def test_skip_fetch_flag(self) -> None:
        args = self._parse(["--skip-fetch"])
        assert args.skip_fetch is True

    def test_pairs_subset(self) -> None:
        args = self._parse(["--pairs", "EUR_USD", "USD_JPY"])
        assert args.pairs == ["EUR_USD", "USD_JPY"]


class TestRunHelper:
    def test_success_returns_true(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert retrain._run(["echo", "hi"], step="test") is True

    def test_failure_returns_false(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert retrain._run(["false"], step="test") is False

    def test_check_false_passed_to_subprocess(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            retrain._run(["cmd"], step="x")
            mock_run.assert_called_once_with(["cmd"], check=False)


class TestFetchPair:
    def test_calls_fetch_script(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = retrain._fetch_pair("EUR_USD", Path("data"), 365)
            assert result is True
            cmd = mock_run.call_args[0][0]
            assert "fetch_oanda_candles.py" in cmd[1]
            assert "EUR_USD" in cmd
            assert "BA" in cmd
            assert "365" in cmd

    def test_failure_propagated(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert retrain._fetch_pair("EUR_USD", Path("data"), 365) is False


class TestTrainAll:
    def test_calls_train_script_with_pairs(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = retrain._train_all(
                ["EUR_USD", "USD_JPY"], Path("data"), Path("models/lgbm"), 0.80
            )
            assert result is True
            cmd = mock_run.call_args[0][0]
            assert "train_lgbm_models.py" in cmd[1]
            assert "EUR_USD" in cmd
            assert "USD_JPY" in cmd

    def test_failure_propagated(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert retrain._train_all(["EUR_USD"], Path("data"), Path("models/lgbm"), 0.80) is False


class TestMainSkipFetch:
    def test_skip_fetch_goes_straight_to_train(self, tmp_path) -> None:
        with (
            patch.object(retrain, "_fetch_pair") as mock_fetch,
            patch.object(retrain, "_train_all", return_value=True) as mock_train,
        ):
            # Call main with --skip-fetch via subprocess-like path: patch argv
            import sys

            old_argv = sys.argv
            sys.argv = [
                "retrain",
                "--skip-fetch",
                "--pairs",
                "EUR_USD",
                "--data-dir",
                str(tmp_path),
                "--model-dir",
                str(tmp_path / "models"),
            ]  # noqa: E501
            try:
                exit_code = retrain.main()
            finally:
                sys.argv = old_argv

            mock_fetch.assert_not_called()
            mock_train.assert_called_once()
            assert exit_code == 0

    def test_missing_token_exits_1(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("OANDA_ACCESS_TOKEN", raising=False)
        import sys

        old_argv = sys.argv
        sys.argv = [
            "retrain",
            "--pairs",
            "EUR_USD",
            "--data-dir",
            str(tmp_path),
            "--model-dir",
            str(tmp_path / "models"),
        ]  # noqa: E501
        try:
            exit_code = retrain.main()
        finally:
            sys.argv = old_argv

        assert exit_code == 1

    def test_fetch_failure_excludes_pair_from_training(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("OANDA_ACCESS_TOKEN", "test-token")
        with (
            patch.object(retrain, "_fetch_pair", return_value=False),
            patch.object(retrain, "_train_all") as mock_train,
        ):
            import sys

            old_argv = sys.argv
            sys.argv = [
                "retrain",
                "--pairs",
                "EUR_USD",
                "--data-dir",
                str(tmp_path),
                "--model-dir",
                str(tmp_path / "models"),
            ]  # noqa: E501
            try:
                exit_code = retrain.main()
            finally:
                sys.argv = old_argv

            # All pairs failed fetch → no train pairs → exits 1
            mock_train.assert_not_called()
            assert exit_code == 1
