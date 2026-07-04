"""PR #418 B-1/B-2 fixes + PR #418 mandatory additional tests (synthetic-only)."""

from __future__ import annotations

import ast
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.ml_step4 import contract, labels
from scripts.ml_step4.acceptance import MEETS, AcceptanceEvaluator
from scripts.ml_step4.body import (
    _predictions_to_signals,
    _trades_from_accepted,
    evaluate_portfolio,
    guarded_run_body,
)
from scripts.ml_step4.data_adapter import FixtureDataProvider

_ML_STEP4_DIR = Path(__file__).resolve().parents[2] / "scripts" / "ml_step4"


# ---------------------------------------------------------------------------
# B-1: cost cell applied exactly once
# ---------------------------------------------------------------------------


def _one_trade_bundle(raw_pnl: float):
    bars = [{"ts": datetime(2025, 6, 2, 0, i, tzinfo=UTC)} for i in range(30)]
    recs = [
        {
            "label": 1,
            "pnl_long_pips": raw_pnl,
            "pnl_short_pips": -raw_pnl,
            "exit_long_offset": 3,
            "exit_short_offset": 3,
        }
    ] + [{"label": None}] * 29
    probs = [[0.1, 0.2, 0.7]] * 30
    sigs = _predictions_to_signals("P", bars, probs, recs, range(0, 1), threshold=0.4, horizon=20)
    trades = _trades_from_accepted(
        [{"pair": "P", "entry": 0, "exit": 4, "direction": "long", "pnl_pips": sigs[0].pnl_pips}],
        {"P": bars},
    )
    return sigs, evaluate_portfolio(trades, holdout_trading_days=1)


def test_b1_signal_pnl_is_raw_gross() -> None:
    sigs, _ = _one_trade_bundle(2.0)
    assert sigs[0].pnl_pips == 2.0  # NOT 1.5 — no cost cell at the signal layer


def test_b1_half_pip_cell_subtracts_exactly_once() -> None:
    _, bundle = _one_trade_bundle(2.0)
    assert bundle["expectancy_pips"] == pytest.approx(1.5)  # 2.0 - 0.5, once (not 1.0)


def test_b1_one_pip_cell_subtracts_exactly_once() -> None:
    _, bundle = _one_trade_bundle(2.0)
    cs = bundle["cost_sensitivity"]
    assert cs["1.0pip"]["expectancy_pips"] == pytest.approx(1.0)  # 2.0 - 1.0 (not 1.5 or 2.0)


def test_b1_sensitivity_cells_not_shifted() -> None:
    _, bundle = _one_trade_bundle(2.0)
    cs = bundle["cost_sensitivity"]
    assert cs["0.0pip"]["expectancy_pips"] == pytest.approx(2.0)  # gross
    assert cs["0.5pip"]["expectancy_pips"] == pytest.approx(1.5)
    assert cs["1.0pip"]["expectancy_pips"] == pytest.approx(1.0)


def test_b1_validation_and_holdout_charge_identically(tmp_path: Path) -> None:
    # Both segments run through the metrics layer with the same primary cell;
    # neither pre-charges at the signal layer. Structural: signal PnL is raw.
    from scripts.ml_step4 import metrics

    sigs, _ = _one_trade_bundle(2.0)
    trades = _trades_from_accepted(
        [{"pair": "P", "entry": 0, "exit": 4, "direction": "long", "pnl_pips": sigs[0].pnl_pips}],
        {"P": [{"ts": datetime(2025, 6, 2, tzinfo=UTC)}]},
    )
    val_series = [
        v for _, v in metrics.daily_portfolio_pnl(trades, contract.PRIMARY_COST_CELL_PIPS)
    ]
    hold_bundle = evaluate_portfolio(trades, holdout_trading_days=1)
    # validation daily PnL at the primary cell == holdout expectancy (one trade)
    assert val_series[0] == pytest.approx(hold_bundle["expectancy_pips"])


def test_b1_cost_convention_explicit_in_evidence(tmp_path: Path) -> None:
    guarded_run_body(
        mode="fixture", provider=FixtureDataProvider(n_bars=300), out_dir=str(tmp_path)
    )
    report = json.loads((tmp_path / "ml_step4_metrics_report.json").read_text(encoding="utf-8"))
    cc = report["cost_convention"]
    assert cc["flat_cost_cell"] == "applied_exactly_once_by_metrics_layer"
    assert cc["signal_pnl"] == "raw_gross_of_flat_cell"
    assert cc["double_charge"] is False
    assert cc["validation_and_holdout_charge_identically"] is True


def test_b1_double_charge_is_impossible() -> None:
    # A raw +1.0 trade at the 0.5 cell can only be 0.5 (single charge). The old
    # double-charge value (0.0) must be unreachable through the body helpers.
    _, bundle = _one_trade_bundle(1.0)
    assert bundle["expectancy_pips"] == pytest.approx(0.5)
    assert bundle["expectancy_pips"] != pytest.approx(0.0)


# ---------------------------------------------------------------------------
# B-2: label eligibility aligned to range(n - horizon - 1)
# ---------------------------------------------------------------------------


def _labelable_bars(n: int) -> list[dict]:
    # Bars with enough movement that ATR(14) is positive from index 13 onward.
    out = []
    for i in range(n):
        base = 1.1000 + 0.0001 * ((i * 7) % 11 - 5)
        out.append(
            {
                "bid_o": base,
                "bid_h": base + 0.0006,
                "bid_l": base - 0.0006,
                "bid_c": base + 0.0001,
                "ask_o": base + 0.00012,
                "ask_h": base + 0.0007,
                "ask_l": base - 0.0005,
                "ask_c": base + 0.00022,
            }
        )
    return out


def _bulk(n: int) -> list[dict]:
    return labels.bulk_labels(
        _labelable_bars(n), horizon=20, tp_mult=1.5, sl_mult=1.0, pip_size=0.0001
    )


def test_b2_last_eligible_index_is_n_minus_horizon_minus_2() -> None:
    n, h = 200, 20
    recs = _bulk(n)
    eligible = [i for i, r in enumerate(recs) if r["label"] is not None]
    assert max(eligible) == n - h - 2  # == 178, matching range(n - horizon - 1)


def test_b2_no_trailing_bar_without_full_horizon_is_labeled() -> None:
    n, h = 200, 20
    recs = _bulk(n)
    for i in range(n - h - 1, n):  # indices n-h-1 .. n-1
        assert recs[i]["label"] is None
        assert recs[i]["pnl_long_pips"] is None
        assert recs[i]["exit_long_offset"] is None


def test_b2_boundary_cases() -> None:
    h = 20
    for n in (h, h + 1, h + 2):
        recs = _bulk(n)
        eligible = [i for i, r in enumerate(recs) if r["label"] is not None]
        # n <= h+1 -> no eligible bar; n=h+2 -> last eligible would be index 0 but
        # ATR warmup (min_periods=14) means it is still None at such small n.
        assert eligible == [] or max(eligible) <= n - h - 2


def test_b2_matches_committed_range_convention() -> None:
    # The committed labeller iterates range(n - horizon - 1); the highest index
    # it could label is n - horizon - 2. bulk_labels must never exceed it.
    n, h = 300, 20
    recs = _bulk(n)
    eligible = [i for i, r in enumerate(recs) if r["label"] is not None]
    assert all(i <= n - h - 2 for i in eligible)
    assert max(eligible) == n - h - 2


def test_b2_horizon_still_20() -> None:
    assert contract.HORIZON_M1_BARS == 20


def test_b2_adapter_failure_still_stops_body(tmp_path: Path, monkeypatch) -> None:
    def boom(*a, **k):
        raise labels.LabelContractError("down")

    monkeypatch.setattr("scripts.ml_step4.body.bulk_labels", boom)
    with pytest.raises(labels.LabelContractError):
        guarded_run_body(
            mode="fixture", provider=FixtureDataProvider(n_bars=300), out_dir=str(tmp_path)
        )


# ---------------------------------------------------------------------------
# PR #418 additional test 1: numeric ATR cross-check vs hand-computed TR
# ---------------------------------------------------------------------------


def test_atr14_matches_hand_computed_true_range() -> None:
    bars = _labelable_bars(40)
    atrs = labels.atr14(bars, period=14, min_periods=14)
    mids_h = [(b["bid_h"] + b["ask_h"]) / 2.0 for b in bars]
    mids_l = [(b["bid_l"] + b["ask_l"]) / 2.0 for b in bars]
    mids_c = [(b["bid_c"] + b["ask_c"]) / 2.0 for b in bars]
    trs = []
    for i in range(len(bars)):
        if i == 0:
            trs.append(mids_h[i] - mids_l[i])
        else:
            trs.append(
                max(
                    mids_h[i] - mids_l[i],
                    abs(mids_h[i] - mids_c[i - 1]),
                    abs(mids_l[i] - mids_c[i - 1]),
                )
            )
    for i in range(len(bars)):
        if i < 13:
            assert atrs[i] is None  # warmup: fewer than 14 TRs
        else:
            expected = sum(trs[i - 13 : i + 1]) / 14
            assert atrs[i] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# PR #418 additional test 2: import-graph legacy-non-use
# ---------------------------------------------------------------------------

_SANCTIONED_SCRIPTS_IMPORTS = {
    "scripts.traded_direction_pnl",
    "scripts.foundation_t2.constants",
    "scripts.train_lgbm_models",  # feature builders only, via the lazy seam
}
_FORBIDDEN_SUBSTRINGS = (
    "compare_multipair",
    "model_store",
    "lgbm_strategy",
    "retrain_production",
    "run_paper",
    "run_live",
    "stage2",
    "fetch_oanda",
)


def _module_imports(path: Path) -> set[str]:
    """Fully-qualified imported module names (absolute imports only).

    ``from pkg import name`` records ``pkg`` AND ``pkg.name`` so that
    ``from scripts import compare_multipair_v9`` is caught as
    ``scripts.compare_multipair_v9`` (not just the dotless ``scripts``).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
            # `from scripts import X` imports submodule X of the namespace
            # package — record scripts.X. For deeper modules the names are
            # symbols, not submodules, so only expand at the top namespace.
            if node.module == "scripts":
                names.update(f"scripts.{a.name}" for a in node.names)
    return names


def test_ml_step4_imports_no_legacy_routes() -> None:
    for py in _ML_STEP4_DIR.glob("*.py"):
        imports = _module_imports(py)
        for name in imports:
            if name.startswith("scripts."):
                assert name in _SANCTIONED_SCRIPTS_IMPORTS, f"{py.name} imports {name}"
            if name.startswith("src.") or name.startswith("fx_ai_trading"):
                raise AssertionError(f"{py.name} imports serving code {name}")
            for bad in _FORBIDDEN_SUBSTRINGS:
                assert bad not in name, f"{py.name} imports forbidden {name}"


def test_old_optimistic_pnl_route_not_importable_in_path() -> None:
    # The only sanctioned PnL helper is the F-2 corrected one, imported by labels.py.
    imports = _module_imports(_ML_STEP4_DIR / "labels.py")
    assert "scripts.traded_direction_pnl" in imports
    for py in _ML_STEP4_DIR.glob("*.py"):
        assert not any("compare_multipair" in n for n in _module_imports(py))


# ---------------------------------------------------------------------------
# PR #418 additional test 3: NaN/infinity metric finiteness
# ---------------------------------------------------------------------------


def _passing_metrics() -> dict:
    return {
        "trade_count": 500,
        "daily_coverage_frac": 0.8,
        "expectancy_pips": 0.4,
        "daily_portfolio_sharpe_annualised": 1.2,
        "max_equity_drawdown": {"max_drawdown_frac": 0.05},
        "turnover_trades_per_day": 12.0,
        "pair_concentration": {"max_trade_share": 0.2, "max_positive_pnl_share": 0.3},
        "cost_sensitivity": {"1.0pip": {"expectancy_pips": 0.1}},
    }


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nan_inf_metric_never_meets(bad: float) -> None:
    m = _passing_metrics()
    m["daily_portfolio_sharpe_annualised"] = bad
    r = AcceptanceEvaluator().evaluate(m, provenance_complete=True)
    assert r["status"] != MEETS
    assert r["status"] == "ML_STEP4_RUN_INVALID_PROVENANCE_MISSING"


def test_nan_in_nested_metric_never_meets() -> None:
    m = _passing_metrics()
    m["cost_sensitivity"]["1.0pip"]["expectancy_pips"] = float("nan")
    r = AcceptanceEvaluator().evaluate(m, provenance_complete=True)
    assert r["status"] != MEETS


def test_finite_metrics_still_meet() -> None:
    r = AcceptanceEvaluator().evaluate(_passing_metrics(), provenance_complete=True)
    assert r["status"] == MEETS


# ---------------------------------------------------------------------------
# PR #418 additional test: deployed-model reuse remains impossible
# ---------------------------------------------------------------------------


def test_deployed_model_reuse_remains_impossible() -> None:
    # No model_path parameter on the trainer wrapper.
    import inspect

    from scripts.ml_step4 import trainer

    assert "model_path" not in inspect.signature(trainer.train_lgbm).parameters
    for bad in ("models/lgbm/EUR_USD.txt", "MODELS/LGBM/x"):
        with pytest.raises(contract.ContractViolationError):
            contract.assert_no_deployed_model_reuse(bad)
    # No joblib/pickle load anywhere in the package.
    for py in _ML_STEP4_DIR.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        assert "joblib.load" not in text and "pickle.load" not in text


def test_fixture_e2e_still_deterministic_after_fixes(tmp_path: Path) -> None:
    a = guarded_run_body(
        mode="fixture", provider=FixtureDataProvider(n_bars=300), out_dir=str(tmp_path / "a")
    )
    b = guarded_run_body(
        mode="fixture", provider=FixtureDataProvider(n_bars=300), out_dir=str(tmp_path / "b")
    )
    for k in ("selected_threshold", "n_holdout_trades_fixture", "acceptance_dry_output"):
        assert a[k] == b[k]
    assert not math.isnan(float(a["n_holdout_trades_fixture"]))
