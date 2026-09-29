"""PATSD Stage 0 の部品を**合成入力だけで**確かめる（実 data は読まない）。"""

from __future__ import annotations

import builtins
import math

import numpy as np
import pandas as pd
import pytest

from scripts.research.patsd_stage0 import cost, data, ledgers, null_pipeline, prereg


def _m15(days: int = 30, start: str = "2023-05-01", seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ts = pd.date_range(start, periods=days * 96, freq="15min", tz="UTC")
    mid = 1.1 * np.exp(np.cumsum(rng.normal(0, 3e-4, len(ts))))
    spread = np.full(len(ts), 0.00012)
    minute = ts.hour * 60 + ts.minute
    rollover = (minute < 22 * 60 + 15) & (minute + 15 > 21 * 60 + 55)
    return pd.DataFrame(
        {
            "ts": ts,
            "mid_o": mid,
            "mid_h": mid * 1.0002,
            "mid_l": mid * 0.9998,
            "mid_c": mid,
            "spread_close_pips": np.where(rollover, 5.0, spread / 1e-4),
            "pip_size": 1e-4,
            "rollover": rollover,
            "session": "europe",
        }
    )


def test_span_guard_rejects_fresh_and_beyond_last_day():
    ok = pd.Series(pd.to_datetime(["2021-04-26", "2025-12-28"], utc=True))
    data.assert_in_span(ok)
    with pytest.raises(data.BoundaryError):
        data.assert_in_span(pd.Series(pd.to_datetime(["2021-04-25"], utc=True)))
    with pytest.raises(data.BoundaryError):
        data.assert_in_span(pd.Series(pd.to_datetime(["2025-12-29"], utc=True)))


def test_aggregate_h4_ohlc_and_close_spread():
    m15 = _m15(days=2)
    h4 = data.aggregate(m15, "H4")
    first = m15.iloc[:16]
    assert h4["mid_o"].iloc[0] == first["mid_o"].iloc[0]
    assert h4["mid_c"].iloc[0] == first["mid_c"].iloc[-1]
    assert h4["mid_h"].iloc[0] == first["mid_h"].max()
    assert h4["n_m15"].iloc[0] == 16


def test_relative_spread_excludes_rollover_closes():
    m15 = _m15(days=3)
    spread = cost.relative_spread(data.aggregate(m15, "M15"))
    assert np.allclose(spread.to_numpy(), 0.00012 / m15.loc[~m15["rollover"], "mid_c"].to_numpy())


def test_sharpe_drag_formula():
    m15 = _m15(days=60)
    out = cost.pair_economics(m15)
    h4 = out["H4"]
    expected = (
        h4["turnover_round_trips_per_year"]
        * (h4["spread_bp"]["median"] / 1e4)
        / out["sigma_annual"]
    )
    assert math.isclose(h4["sharpe_drag"], expected, abs_tol=1e-4)


def _panel(days: int = 400, pairs: int = 3):
    h4 = {}
    for p in range(pairs):
        m15 = _m15(days=days, start="2021-04-26", seed=p)
        h4[f"P{p}"] = data.aggregate(m15, "H4")
    costs = {k: 1e-4 for k in h4}
    return null_pipeline.build_panel(h4, costs)


def test_synthetic_path_keeps_magnitudes_and_randomises_common_signs():
    panel = _panel(days=900)
    cum = null_pipeline.synthetic_cumret(panel, np.random.default_rng(1))
    increments = np.diff(cum, axis=0)
    assert np.allclose(np.abs(increments), np.abs(panel.returns))
    nonzero = np.abs(panel.returns[:, 0]) > 0
    ratio = increments[nonzero] / panel.returns[nonzero]
    assert np.allclose(ratio, ratio[:, [0]])
    share_flipped = (ratio[:, 0] < 0).mean()
    assert 0.4 < share_flipped < 0.6


def test_trades_respect_last_entry_bar_and_panel_end():
    panel = _panel(days=900)
    trades = null_pipeline.make_trades(panel, (0, 0, 2, 2, 1))
    assert trades.t0.max() <= panel.last_entry_bar
    assert trades.t1.max() <= panel.returns.shape[0] - 1


def test_deflated_p_behaves():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1, 2000)
    assert 0.05 < null_pipeline.deflated_p(noise, 0.0) < 0.95
    strong = rng.normal(0.2, 1, 2000)
    assert null_pipeline.deflated_p(strong, 0.0) < 1e-6
    assert null_pipeline.deflated_p(strong, 0.3) > 0.9


def test_effective_trials_clusters():
    rng = np.random.default_rng(0)
    base = rng.normal(size=500)
    same = np.vstack([base + rng.normal(0, 0.01, 500) for _ in range(5)])
    assert null_pipeline.effective_trials(same) == 1
    independent = rng.normal(size=(6, 500))
    assert null_pipeline.effective_trials(independent) == 6


def test_g4_arithmetic_matches_design():
    out = null_pipeline.g4_arithmetic(3.4)
    assert abs(out["observed_needed"] - 1.86) < 0.01
    assert abs(out["pass_prob_by_true_sharpe"]["1.5"] - 0.256) < 0.01
    assert abs(out["marginal_pass_prob_under_prior"] - 0.0113) < 0.001


def test_budget_counts():
    assert len(null_pipeline.base_configs()) == prereg.BUDGET["rule_trials"]
    b = prereg.BUDGET
    assert b["rule_trials"] + b["l2_trials"] + b["ml_trials"] + b["reserve"] == b["cap"]


def test_replication_runs_on_synthetic_panel_and_is_deterministic():
    panel = _panel(days=900, pairs=2)
    book = null_pipeline.build_trade_book(panel)
    a = null_pipeline.run_replication(panel, book, 3)
    b = null_pipeline.run_replication(panel, book, 3)
    assert a == b
    assert (
        a["n_trials"]
        <= prereg.BUDGET["rule_trials"] + prereg.BUDGET["l2_trials"] + prereg.BUDGET["ml_trials"]
    )
    for t in prereg.SELECTION["dsr_ladder"]:
        assert set(a[str(t)]) >= {"any_pass", "g4", "g4_with_injected"}


def test_injected_signal_raises_the_target_sharpe():
    panel = _panel(days=900, pairs=2)
    book = null_pipeline.build_trade_book(panel)
    strong = null_pipeline.run_replication(panel, book, 5, (3.0, (0, 0, 1, 1, 0)))
    assert strong["0.1"]["n_pass"] >= 1


def test_pre_r1_overlap_never_opens_price_files(monkeypatch):
    real_open = builtins.open

    def guarded(path, *args, **kwargs):
        if str(path).endswith(".jsonl"):
            raise AssertionError("price file opened")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)
    out = ledgers.pre_r1_overlap()
    assert "overlap" in out


def test_rename_ledger_counts_partial_conservatively():
    out = ledgers.s0_5()
    assert out["genuine_yes"] + out["partial"] == len(ledgers.RENAME_LEDGER)
    assert out["classification"] in {"GREEN", "AMBER", "RED"}


def test_closure_and_digest():
    closure = prereg.code_closure()
    for name in ("run", "data", "cost", "null_pipeline", "ledgers", "prereg"):
        assert f"scripts/research/patsd_stage0/{name}.py" in closure
    assert len(prereg.freeze_digest()) == 64


def test_real_returns_are_used_only_through_the_sign_randomiser_and_std():
    """実 return は符号ランダム化と vol（std）以外で使わない。"""
    import ast
    import inspect

    source = inspect.getsource(null_pipeline)
    tree = ast.parse(source)
    allowed = {
        "synthetic_cumret",
        "build_panel",
        "make_trades",
        "run_replication",
        "daily",
        "trade_pnl",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            uses = [
                n for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr == "returns"
            ]
            if uses:
                assert node.name in allowed, node.name
                if node.name not in {"synthetic_cumret", "build_panel"}:
                    body = ast.unparse(node)
                    assert "returns.shape" in body and body.count(".returns") == body.count(
                        ".returns.shape"
                    ), node.name


def test_pre_r1_overlap_never_reads_price_files_via_pathlib(monkeypatch):
    from pathlib import Path

    real = Path.read_text

    def guarded(self, *args, **kwargs):
        if self.suffix == ".jsonl":
            raise AssertionError("price file read")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded)
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda self: (
            (_ for _ in ()).throw(AssertionError("read_bytes")) if self.suffix == ".jsonl" else b""
        ),
    )
    assert "overlap" in ledgers.pre_r1_overlap()
