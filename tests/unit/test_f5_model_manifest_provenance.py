"""F5-E model manifest provenance tests (audit §4 F-5).

The trainer's models/lgbm/manifest.json must carry, per trained pair and
globally: logical file id (basename only), streaming data sha256, UTC time
bounds, row count, price mode, label contract, cost contract, code_sha and
config_hash — with NO absolute/personal path anywhere in the manifest text.

Everything runs against a tiny synthetic JSONL in tmp_path; the real LGBM
fit is monkeypatched to a millisecond stub. NEVER reads data/ or artifacts/.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = str(REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import train_lgbm_models as tm  # noqa: E402

_PAIR = "EUR_USD"
_N_BARS = 1200
_T0 = datetime(2026, 1, 5, tzinfo=UTC)
_HORIZON = 3


class _StubModel:
    """Millisecond stand-in for a fitted LGBMClassifier."""


def _write_synthetic_ba(path: Path, n: int = _N_BARS) -> None:
    """Random-walk M1 BA candles in fetch_oanda_candles JSONL shape."""
    rng = np.random.default_rng(42)
    mid = 1.10
    half_spread = 0.0001
    with open(path, "w") as f:
        for i in range(n):
            o = mid
            c = mid + float(rng.normal(0.0, 0.0004))
            hi = max(o, c) + abs(float(rng.normal(0.0, 0.0003)))
            lo = min(o, c) - abs(float(rng.normal(0.0, 0.0003)))
            row = {
                "time": (_T0 + timedelta(minutes=i)).isoformat(),
                "bid_o": o - half_spread,
                "bid_h": hi - half_spread,
                "bid_l": lo - half_spread,
                "bid_c": c - half_spread,
                "ask_o": o + half_spread,
                "ask_h": hi + half_spread,
                "ask_l": lo + half_spread,
                "ask_c": c + half_spread,
            }
            f.write(json.dumps(row) + "\n")
            mid = c


@pytest.fixture(scope="module")
def train_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Run tm.main() once on the synthetic file with the fit stubbed out."""
    data_dir = tmp_path_factory.mktemp("data")
    model_dir = tmp_path_factory.mktemp("models")
    jsonl_path = data_dir / f"candles_{_PAIR}_M1_365d_BA.jsonl"
    _write_synthetic_ba(jsonl_path)

    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(tm, "_train", lambda df: _StubModel())
        rc = tm.main(
            [
                "--pairs",
                _PAIR,
                "--data-dir",
                str(data_dir),
                "--model-dir",
                str(model_dir),
                "--horizon",
                str(_HORIZON),
            ]
        )
    finally:
        mp.undo()
    assert rc == 0

    manifest_text = (model_dir / "manifest.json").read_text()
    return {
        "manifest": json.loads(manifest_text),
        "text": manifest_text,
        "jsonl_path": jsonl_path,
        "model_dir": model_dir,
        "data_dir": data_dir,
    }


class TestGlobalManifestFields:
    def test_pair_trained_and_model_written(self, train_run: dict) -> None:
        assert train_run["manifest"]["trained_pairs"] == [_PAIR]
        assert (train_run["model_dir"] / f"{_PAIR}.joblib").exists()

    def test_label_contract(self, train_run: dict) -> None:
        assert train_run["manifest"]["label_contract"] == {
            "type": "b2_bidask_triple_barrier",
            "tie_break": "sl_first_strict_lt",
            "horizon": _HORIZON,
            "tp_mult": tm._TP_MULT,
            "sl_mult": tm._SL_MULT,
            "atr": "atr14_min_periods_14",
        }

    def test_cost_contract(self, train_run: dict) -> None:
        assert train_run["manifest"]["cost_contract"] == "spread_embedded_in_bidask_labels"

    def test_code_sha_present_never_crashes(self, train_run: dict) -> None:
        code_sha = train_run["manifest"]["code_sha"]
        assert isinstance(code_sha, str)
        assert re.fullmatch(r"[0-9a-f]{40}", code_sha) or code_sha == "unknown"

    def test_config_hash_matches_helper(self, train_run: dict) -> None:
        m = train_run["manifest"]
        assert re.fullmatch(r"[0-9a-f]{64}", m["config_hash"])
        expected = tm._config_hash(m["lgbm_params"], m["label_contract"])
        assert m["config_hash"] == expected

    def test_global_data_aggregates(self, train_run: dict) -> None:
        m = train_run["manifest"]
        assert m["price_mode"] == "BA"
        assert m["data_files"] == [train_run["jsonl_path"].name]
        assert m["total_row_count"] == _N_BARS
        assert m["data_ts_min_utc"] == m["pairs"][_PAIR]["data_ts_min_utc"]
        assert m["data_ts_max_utc"] == m["pairs"][_PAIR]["data_ts_max_utc"]
        assert m["feature_version"] == "v4"
        assert m["feature_cols"] == tm._FEATURE_COLS


class TestPerPairProvenance:
    def test_logical_file_id_is_basename_only(self, train_run: dict) -> None:
        pp = train_run["manifest"]["pairs"][_PAIR]
        assert pp["logical_file_id"] == f"candles_{_PAIR}_M1_365d_BA.jsonl"
        assert "/" not in pp["logical_file_id"]
        assert "\\" not in pp["logical_file_id"]

    def test_sha256_matches_independent_hash(self, train_run: dict) -> None:
        pp = train_run["manifest"]["pairs"][_PAIR]
        independent = hashlib.sha256(train_run["jsonl_path"].read_bytes()).hexdigest()
        assert pp["data_sha256"] == independent

    def test_ts_bounds_and_row_count(self, train_run: dict) -> None:
        pp = train_run["manifest"]["pairs"][_PAIR]
        assert datetime.fromisoformat(pp["data_ts_min_utc"]) == _T0
        assert datetime.fromisoformat(pp["data_ts_max_utc"]) == _T0 + timedelta(minutes=_N_BARS - 1)
        assert pp["row_count"] == _N_BARS
        assert pp["price_mode"] == "BA"


class TestNoAbsolutePaths:
    def test_manifest_text_has_no_personal_paths(self, train_run: dict) -> None:
        text = train_run["text"]
        for needle in (":\\", ":/", "/Users/", "/home/", "Users\\"):
            assert needle not in text, f"manifest leaks path fragment {needle!r}"
        # The tmp dirs used for the run must not appear either.
        for p in (train_run["data_dir"], train_run["model_dir"]):
            assert str(p) not in text
            assert p.as_posix() not in text


class TestConfigHash:
    _LC = {
        "type": "b2_bidask_triple_barrier",
        "tie_break": "sl_first_strict_lt",
        "horizon": 20,
        "tp_mult": 1.5,
        "sl_mult": 1.0,
        "atr": "atr14_min_periods_14",
    }
    _PARAMS = {"learning_rate": 0.05, "num_leaves": 31, "verbose": -1, "n_estimators": 200}

    def test_stable_across_identical_configs(self) -> None:
        h1 = tm._config_hash(self._PARAMS, self._LC)
        h2 = tm._config_hash(dict(self._PARAMS), dict(self._LC))
        assert h1 == h2

    def test_key_order_independent(self) -> None:
        reordered = dict(reversed(list(self._PARAMS.items())))
        assert tm._config_hash(reordered, self._LC) == tm._config_hash(self._PARAMS, self._LC)

    def test_changes_with_lgbm_params(self) -> None:
        h1 = tm._config_hash(self._PARAMS, self._LC)
        h2 = tm._config_hash({**self._PARAMS, "num_leaves": 63}, self._LC)
        assert h1 != h2

    def test_changes_with_label_contract(self) -> None:
        h1 = tm._config_hash(self._PARAMS, self._LC)
        h2 = tm._config_hash(self._PARAMS, {**self._LC, "horizon": 40})
        assert h1 != h2
