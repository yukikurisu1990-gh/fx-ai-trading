"""grid_search_tp_sl_conf.py — Phase 9.10/A-6 spread x conf sweep.

For the Phase 9.10 Go/No-Go judgment we need to know: *is there any
(spread, confidence) regime in which SELECTOR keeps net Sharpe >= 0.20?*

The expensive inputs — feature engineering + model training — are fixed
by TP=3 / SL=2 / horizon=20 (v2's labelling).  We reuse the trained
models once and sweep only:

    spread_pip ∈ {0.0, 0.5, 1.0, 1.5, 2.0}   (5 points)
    conf_threshold ∈ {0.50, 0.55, 0.60, 0.65}  (4 points)

→ 20 (spread, conf) combinations, all evaluated by replaying the same
signal stream; the per-cell cost is just a vectorised re-score over the
already-computed model outputs.

Why not sweep TP/SL here
------------------------
Different TP/SL changes the labels → must retrain all models per
combination (≈30 trains × 5 TP × 4 SL = 600 trains ≈ 100 minutes plus
feature rebuild each time).  Sweeping TP/SL lives in Phase 9.12 where
ATR-based dynamic barriers replace the fixed-pip scheme.

Output
------
One markdown-style table: rows = spread_pip, columns = conf, cells =
SELECTOR net Sharpe.  A second table shows net PnL (pip).  The GO /
SOFT GO / NO-GO cells are tagged so the closure memo can cite them.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import lightgbm as lgb
import pandas as pd

# Reuse v3's building blocks directly — they are all pure functions.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.compare_multipair_v3_costs import (  # noqa: E402
    DEFAULT_PAIRS,
    LABEL_COLUMN,
    _build_cross_pair_features,
    _build_pair_features,
    _compute_retrain_schedule,
    _generate_folds,
    _gross_pnl_pips,
    _load_ba,
    _load_mid,
    _net_pnl_pips,
    _pick_file,
    _pip_size,
    _train,
)

SPREAD_GRID = (0.0, 0.5, 1.0, 1.5, 2.0)
CONF_GRID = (0.50, 0.55, 0.60, 0.65)


def _sharpe(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return (mu / math.sqrt(var)) if var > 0 else 0.0


def _eval_fold_all_cells(
    pair_models: dict[str, lgb.LGBMClassifier],
    pair_test_dfs: dict[str, pd.DataFrame],
    base_pair: str,
    feature_cols: list[str],
    tp_pip: int,
    sl_pip: int,
    rng: random.Random,
) -> dict[tuple[float, float], dict]:
    """Evaluate every (spread, conf) cell for this fold in one pass.

    The per-bar ML inference is the expensive step — do it once per (pair,
    bar) and score each (spread, conf) cell from the cached (p_tp, p_sl)
    pairs.  This collapses the 20-cell cost to essentially 1x the inference
    cost.
    """
    base_df = pair_test_dfs[base_pair].dropna(subset=[LABEL_COLUMN])

    # Cache: for each pair at each timestamp, the model's (p_tp, p_sl, label).
    # Keyed by ts; skips pairs with no row / no label at that ts.
    base_preds: dict[pd.Timestamp, tuple[float, float, int]] = {}
    other_preds: dict[pd.Timestamp, dict[str, tuple[float, float, int]]] = {}

    # Pre-compute per-bar probabilities for the base pair (one model call per bar).
    for _, brow in base_df.iterrows():
        ts = brow["timestamp"]
        x = [[float(brow.get(c) or 0.0) for c in feature_cols]]
        proba = pair_models[base_pair].predict_proba(x)[0]
        base_preds[ts] = (float(proba[2]), float(proba[0]), int(brow[LABEL_COLUMN]))
        other_preds[ts] = {}

    # Now each non-base pair: scan its test frame and stash (p_tp, p_sl, label)
    # for timestamps that exist in the base frame.
    for pair, model in pair_models.items():
        if pair == base_pair:
            continue
        pdf = pair_test_dfs[pair].dropna(subset=[LABEL_COLUMN])
        for _, row in pdf.iterrows():
            ts = row["timestamp"]
            if ts not in other_preds:
                continue
            x = [[float(row.get(c) or 0.0) for c in feature_cols]]
            proba = model.predict_proba(x)[0]
            other_preds[ts][pair] = (float(proba[2]), float(proba[0]), int(row[LABEL_COLUMN]))

    cells: dict[tuple[float, float], dict] = {}
    for spread in SPREAD_GRID:
        for conf in CONF_GRID:
            cells[(spread, conf)] = {
                "EURUSD_ML": {"gross": [], "net": []},
                "SELECTOR": {"gross": [], "net": []},
                "EQUAL_AVG": {"gross": [], "net": []},
                "RANDOM": {"gross": [], "net": []},
                "base_n": 0,
            }

    # Scoring loop (vectorised per cell by caching pair preds above).
    for ts, (p_tp_b, p_sl_b, base_label) in base_preds.items():
        per_pair = other_preds[ts]
        per_pair_full = {base_pair: (p_tp_b, p_sl_b, base_label), **per_pair}

        for spread in SPREAD_GRID:
            for conf in CONF_GRID:
                c = cells[(spread, conf)]
                c["base_n"] += 1

                # EURUSD_ML
                sig = _classify(p_tp_b, p_sl_b, conf)
                g = _gross_pnl_pips(sig, base_label, tp_pip, sl_pip)
                _accumulate(c["EURUSD_ML"], g, spread)

                # Signals for all pairs
                signals = {}
                for pair, (p_tp, p_sl, lab) in per_pair_full.items():
                    s = _classify(p_tp, p_sl, conf)
                    s_conf = max(p_tp, p_sl)
                    signals[pair] = (s, s_conf, lab)

                # SELECTOR
                active = [(p, d) for p, d in signals.items() if d[0] != "no_trade"]
                if active:
                    best_pair = max(active, key=lambda x: x[1][1])[0]
                    s, _, lab = signals[best_pair]
                    _accumulate(c["SELECTOR"], _gross_pnl_pips(s, lab, tp_pip, sl_pip), spread)
                else:
                    _accumulate(c["SELECTOR"], None, spread)

                # EQUAL_AVG
                traded = []
                for _, (s, _, lab) in signals.items():
                    g2 = _gross_pnl_pips(s, lab, tp_pip, sl_pip)
                    if g2 is not None:
                        traded.append(g2)
                if traded:
                    mean_g = sum(traded) / len(traded)
                    c["EQUAL_AVG"]["gross"].append(mean_g)
                    c["EQUAL_AVG"]["net"].append(mean_g - spread)
                else:
                    pass  # skipped bar

                # RANDOM
                rp = rng.choice(list(signals.keys()))
                s, _, lab = signals[rp]
                _accumulate(c["RANDOM"], _gross_pnl_pips(s, lab, tp_pip, sl_pip), spread)

    return cells


def _classify(p_tp: float, p_sl: float, conf: float) -> str:
    if p_tp >= conf and p_tp >= p_sl:
        return "long"
    if p_sl >= conf:
        return "short"
    return "no_trade"


def _accumulate(strat_acc: dict, gross: float | None, spread: float) -> None:
    if gross is None:
        return
    net = _net_pnl_pips(gross, spread)
    strat_acc["gross"].append(gross)
    strat_acc["net"].append(net if net is not None else 0.0)


def _print_heatmap(
    title: str,
    metric_name: str,
    values: dict[tuple[float, float], float],
    highlight: str | None = None,
) -> None:
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)
    # Header row
    header = "  spread \\ conf | " + " | ".join(f"{c:.2f}" for c in CONF_GRID)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for sp in SPREAD_GRID:
        row = f"  {sp:>12.2f}  |"
        for cf in CONF_GRID:
            v = values.get((sp, cf), 0.0)
            tag = ""
            if highlight == "go" and v >= 0.20:
                tag = "*"
            elif highlight == "soft" and 0.15 <= v < 0.20:
                tag = "+"
            row += f" {v:>6.3f}{tag}|" if metric_name == "sharpe" else f" {v:>6.0f} |"
        print(row)
    if highlight == "go":
        print("  * = GO cell (SELECTOR net Sharpe >= 0.20)")
    if highlight == "soft":
        print("  + = SOFT-GO cell (0.15 <= net Sharpe < 0.20)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grid_search_tp_sl_conf")
    parser.add_argument("--pairs", default=",".join(DEFAULT_PAIRS))
    parser.add_argument("--base-pair", default="EUR_USD")
    parser.add_argument("--tp-pip", type=int, default=3)
    parser.add_argument("--sl-pip", type=int, default=2)
    parser.add_argument("--horizon", type=int, default=20)
    parser.add_argument("--retrain-interval-days", type=int, default=90)
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    base_pair = args.base_pair

    print(
        f"Grid: spread={SPREAD_GRID} × conf={CONF_GRID}  "
        f"(TP={args.tp_pip}/SL={args.sl_pip} fixed)\n"
    )

    # Load + features (identical to v3 prelude)
    print("Loading candles ...")
    mid_dfs: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        path, mode = _pick_file(pair)
        df = _load_ba(path) if mode == "BA" else _load_mid(path)
        mid_dfs[pair] = df
    print("Building features ...")
    feat_dfs: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        pip = _pip_size(pair)
        feat = _build_pair_features(
            mid_dfs[pair], args.horizon, args.tp_pip * pip, args.sl_pip * pip
        )
        feat_dfs[pair] = feat
    feat_dfs = _build_cross_pair_features(feat_dfs, ref_pair=base_pair)

    sample = feat_dfs[base_pair]
    feature_cols = [
        c
        for c in sample.columns
        if c
        not in (
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "bid_c",
            "ask_c",
            LABEL_COLUMN,
        )
    ]
    folds = _generate_folds(feat_dfs[base_pair]["timestamp"])
    retrain_schedule = _compute_retrain_schedule(folds, args.retrain_interval_days)
    print(f"Folds: {len(folds)}  retrains: {retrain_schedule}\n")

    rng = random.Random(args.seed)
    pair_models: dict[str, lgb.LGBMClassifier] = {}

    # Accumulate per-strategy net PnL series across all folds, per (spread, conf) cell.
    grand: dict[tuple[float, float], dict[str, list[float]]] = {
        (sp, cf): {s: [] for s in ("EURUSD_ML", "SELECTOR", "EQUAL_AVG", "RANDOM")}
        for sp in SPREAD_GRID
        for cf in CONF_GRID
    }

    for fid, fold in enumerate(folds):
        if fid in retrain_schedule:
            for pair in pairs:
                ts = feat_dfs[pair]["timestamp"]
                tr_mask = (ts >= fold["train_start"]) & (ts < fold["train_end"])
                pair_models[pair] = _train(feat_dfs[pair][tr_mask], feature_cols, args.n_estimators)
        pair_test_dfs: dict[str, pd.DataFrame] = {}
        for pair in pairs:
            ts = feat_dfs[pair]["timestamp"]
            te_mask = (ts >= fold["test_start"]) & (ts < fold["test_end"])
            pair_test_dfs[pair] = feat_dfs[pair][te_mask].reset_index(drop=True)

        cells = _eval_fold_all_cells(
            pair_models,
            pair_test_dfs,
            base_pair,
            feature_cols,
            args.tp_pip,
            args.sl_pip,
            rng,
        )
        for (sp, cf), strats in cells.items():
            for s in ("EURUSD_ML", "SELECTOR", "EQUAL_AVG", "RANDOM"):
                grand[(sp, cf)][s].extend(strats[s]["net"])

        print(f"  Fold{fid:>3} done")

    # Reports
    sharpe_sel: dict[tuple[float, float], float] = {}
    pnl_sel: dict[tuple[float, float], float] = {}
    sharpe_eu: dict[tuple[float, float], float] = {}
    for (sp, cf), strats in grand.items():
        sharpe_sel[(sp, cf)] = _sharpe(strats["SELECTOR"])
        pnl_sel[(sp, cf)] = sum(strats["SELECTOR"])
        sharpe_eu[(sp, cf)] = _sharpe(strats["EURUSD_ML"])

    _print_heatmap(
        "SELECTOR net Sharpe -- spread x conf",
        "sharpe",
        sharpe_sel,
        highlight="go",
    )
    _print_heatmap(
        "SELECTOR net PnL (pip) -- spread x conf",
        "pnl",
        pnl_sel,
        highlight=None,
    )
    _print_heatmap(
        "EURUSD_ML net Sharpe -- spread x conf",
        "sharpe",
        sharpe_eu,
        highlight="go",
    )

    # Summary line: best cell by Sharpe
    best_cell = max(sharpe_sel, key=sharpe_sel.get)
    print(
        "\n  Best SELECTOR cell: "
        f"spread={best_cell[0]:.2f}  conf={best_cell[1]:.2f}  "
        f"netSharpe={sharpe_sel[best_cell]:.3f}  netPnL={pnl_sel[best_cell]:.0f} pip"
    )

    # Go/No-Go summary — restrict to *realistic* spread cells (spread >= 0.5pip).
    # Spread=0 cells are reproducer/sanity checks (they should match v2's gross Sharpe)
    # and must NOT count toward the gate verdict.
    realistic = [k for k in sharpe_sel if k[0] >= 0.5]
    go_cells = [k for k in realistic if sharpe_sel[k] >= 0.20 and pnl_sel[k] > 0]
    soft_cells = [k for k in realistic if 0.15 <= sharpe_sel[k] < 0.20 and pnl_sel[k] > 0]
    zero_cost_go = [k for k in sharpe_sel if k[0] == 0.0 and sharpe_sel[k] >= 0.20]
    print("\n  Go/No-Go (SELECTOR, realistic spread >= 0.5pip):")
    print(f"    GO      cells (Sh>=0.20 & PnL>0): {len(go_cells):>3}")
    print(f"    SOFT GO cells (0.15<=Sh<0.20):    {len(soft_cells):>3}")
    print(
        "    NO-GO   cells (else):             "
        f"{len(realistic) - len(go_cells) - len(soft_cells):>3}"
    )
    print(
        f"    (info) zero-cost GO cells:        {len(zero_cost_go):>3}  "
        "(sanity check, not counted toward verdict)"
    )
    if go_cells:
        print("    -> Phase 9.10 GO (>=1 realistic spread regime has edge)")
    elif soft_cells:
        print("    -> Phase 9.10 SOFT GO (Phase 9.12 quality lift recommended)")
    else:
        print("    -> Phase 9.10 NO-GO (strategy redesign required)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
