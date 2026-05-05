"""Stage 23.0a outcome-dataset validation runner.

Loads the parquets emitted by ``stage23_0a_build_outcome_dataset.py`` and
applies the WARN / HALT gates from
``docs/design/phase23_0a_outcome_dataset.md`` §5.

Outputs:
- ``artifacts/stage23_0a/validation_report.md``
- exit code 0 (all gates pass or only WARN), 1 (any HALT)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO_ROOT / "artifacts" / "stage23_0a"

PHASE22_M1_MEDIAN_COST_RATIO = 1.28  # Reference cross-pair median (cost_ratio scale).

WARN_BANDS = {
    "M5": (0.40, 0.65),
    "M15": (0.20, 0.45),
}
COVERAGE_HALT_THRESHOLD = 0.95
AMBIG_WARN_THRESHOLD = 0.05
SIGN_CONVENTION_TOL_PIP = 0.5  # max permitted absolute deviation per pair


def discover_parquets(root: Path) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {}
    for tf in ("M5", "M15"):
        d = root / f"labels_{tf}"
        if not d.exists():
            out[tf] = []
            continue
        out[tf] = sorted(d.glob(f"labels_{tf}_*.parquet"))
    return out


def load_pair_summary(pq_path: Path) -> dict:
    df = pd.read_parquet(pq_path)
    valid = df[df["valid_label"]]
    n_total = int(len(df))
    n_valid = int(len(valid))
    pair = pq_path.stem.split("_", 2)[2]  # labels_M5_EUR_USD -> EUR_USD
    tf = pq_path.stem.split("_", 2)[1]
    long_te = valid[valid["direction"] == "long"]["time_exit_pnl"]
    short_te = valid[valid["direction"] == "short"]["time_exit_pnl"]
    long_te = long_te[np.isfinite(long_te)]
    short_te = short_te[np.isfinite(short_te)]
    spread = valid["spread_entry"]
    spread = spread[np.isfinite(spread)]
    if len(long_te) and len(short_te):
        sign_inv_lhs = float(long_te.mean() + short_te.mean())
    else:
        sign_inv_lhs = float("nan")
    sign_inv_rhs = float(-2.0 * spread.mean()) if len(spread) else float("nan")
    return {
        "pair": pair,
        "signal_timeframe": tf,
        "n_total": n_total,
        "n_valid": n_valid,
        "coverage": (n_valid / n_total) if n_total else float("nan"),
        "cost_ratio_p10": float(valid["cost_ratio"].quantile(0.10)) if n_valid else float("nan"),
        "cost_ratio_p50": float(valid["cost_ratio"].quantile(0.50)) if n_valid else float("nan"),
        "cost_ratio_p90": float(valid["cost_ratio"].quantile(0.90)) if n_valid else float("nan"),
        "ambig_long": _ambig_rate(valid, "long"),
        "ambig_short": _ambig_rate(valid, "short"),
        "sign_inv_lhs": sign_inv_lhs,
        "sign_inv_rhs": sign_inv_rhs,
        "sign_inv_dev": abs(sign_inv_lhs - sign_inv_rhs)
        if np.isfinite(sign_inv_lhs) and np.isfinite(sign_inv_rhs)
        else float("nan"),
        "schema_columns": list(df.columns),
    }


def _ambig_rate(df: pd.DataFrame, direction: str) -> float:
    sub = df[df["direction"] == direction]
    if len(sub) == 0:
        return float("nan")
    return float(sub["same_bar_tp_sl_ambiguous"].mean())


def cross_pair_median(summaries: list[dict], tf: str, key: str) -> float:
    values = [s[key] for s in summaries if s["signal_timeframe"] == tf and np.isfinite(s[key])]
    if not values:
        return float("nan")
    return float(np.median(values))


def evaluate_gates(summaries: list[dict], schema_spec: dict) -> tuple[list[str], list[str], dict]:
    warns: list[str] = []
    halts: list[str] = []
    metrics: dict = {}

    if not summaries:
        halts.append("HALT: no parquets discovered")
        return warns, halts, metrics

    expected_cols = schema_spec.get("columns", [])

    for s in summaries:
        if s["schema_columns"] != expected_cols:
            halts.append(
                f"HALT[schema_compat]: {s['signal_timeframe']}/{s['pair']} columns "
                f"differ from label_schema.json (expected {len(expected_cols)} cols, "
                f"got {len(s['schema_columns'])})"
            )
        if s["coverage"] < COVERAGE_HALT_THRESHOLD:
            halts.append(
                f"HALT[coverage]: {s['signal_timeframe']}/{s['pair']} coverage "
                f"{s['coverage']:.4f} < {COVERAGE_HALT_THRESHOLD:.2f}"
            )
        if np.isfinite(s["sign_inv_dev"]) and s["sign_inv_dev"] > SIGN_CONVENTION_TOL_PIP:
            halts.append(
                f"HALT[sign_convention]: {s['signal_timeframe']}/{s['pair']} "
                f"|long_te + short_te - (-2*spread)| = {s['sign_inv_dev']:.4f} pip > "
                f"{SIGN_CONVENTION_TOL_PIP}"
            )
        for direction_key in ("ambig_long", "ambig_short"):
            v = s[direction_key]
            if np.isfinite(v) and v > AMBIG_WARN_THRESHOLD:
                warns.append(
                    f"WARN[ambig]: {s['signal_timeframe']}/{s['pair']}/{direction_key} "
                    f"{v:.4f} > {AMBIG_WARN_THRESHOLD}"
                )

    m5_med = cross_pair_median(summaries, "M5", "cost_ratio_p50")
    m15_med = cross_pair_median(summaries, "M15", "cost_ratio_p50")
    metrics["m5_cross_pair_median_cost_ratio"] = m5_med
    metrics["m15_cross_pair_median_cost_ratio"] = m15_med

    if np.isfinite(m5_med):
        lo, hi = WARN_BANDS["M5"]
        if not (lo <= m5_med <= hi):
            warns.append(
                f"WARN[cost_ratio_band]: M5 cross-pair median {m5_med:.3f} outside [{lo}, {hi}]"
            )
        if m5_med >= PHASE22_M1_MEDIAN_COST_RATIO:
            halts.append(
                f"HALT[cost_regime]: M5 cross-pair median {m5_med:.3f} >= "
                f"Phase22 M1 median {PHASE22_M1_MEDIAN_COST_RATIO:.2f}"
            )
    if np.isfinite(m15_med):
        lo, hi = WARN_BANDS["M15"]
        if not (lo <= m15_med <= hi):
            warns.append(
                f"WARN[cost_ratio_band]: M15 cross-pair median {m15_med:.3f} outside [{lo}, {hi}]"
            )
        if m15_med >= PHASE22_M1_MEDIAN_COST_RATIO:
            halts.append(
                f"HALT[cost_regime]: M15 cross-pair median {m15_med:.3f} >= "
                f"Phase22 M1 median {PHASE22_M1_MEDIAN_COST_RATIO:.2f}"
            )
    if np.isfinite(m5_med) and np.isfinite(m15_med) and m15_med >= m5_med:
        halts.append(
            f"HALT[ordering]: M15 median {m15_med:.3f} >= M5 median {m5_med:.3f} "
            f"(structural ordering wrong)"
        )

    return warns, halts, metrics


def write_report(
    out_path: Path,
    summaries: list[dict],
    warns: list[str],
    halts: list[str],
    metrics: dict,
    schema_spec: dict,
) -> None:
    lines: list[str] = []
    lines.append("# Stage 23.0a Outcome Dataset Validation Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase23_0a_outcome_dataset.md`")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    if halts:
        lines.append(f"**HALT** — {len(halts)} hard-gate failure(s); {len(warns)} warning(s).")
    elif warns:
        lines.append(f"**OK with WARN** — 0 hard-gate failures; {len(warns)} warning(s).")
    else:
        lines.append("**OK** — all hard gates pass; no warnings.")
    lines.append("")
    if halts:
        lines.append("## HALT items")
        lines.append("")
        for h in halts:
            lines.append(f"- {h}")
        lines.append("")
    if warns:
        lines.append("## WARN items")
        lines.append("")
        for w in warns:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Cross-pair metrics")
    lines.append("")
    lines.append(
        f"- M5 cross-pair median cost_ratio: "
        f"{metrics.get('m5_cross_pair_median_cost_ratio', float('nan')):.3f} "
        f"(WARN band {WARN_BANDS['M5']})"
    )
    lines.append(
        f"- M15 cross-pair median cost_ratio: "
        f"{metrics.get('m15_cross_pair_median_cost_ratio', float('nan')):.3f} "
        f"(WARN band {WARN_BANDS['M15']})"
    )
    lines.append(
        f"- HALT thresholds: any TF >= {PHASE22_M1_MEDIAN_COST_RATIO:.2f} (Phase22 M1 median); "
        f"M15 >= M5 (ordering); coverage < {COVERAGE_HALT_THRESHOLD:.2f}; "
        f"sign convention deviation > {SIGN_CONVENTION_TOL_PIP} pip"
    )
    lines.append("")

    lines.append("## Per-pair × TF summary")
    lines.append("")
    lines.append(
        "| TF | pair | rows | valid | coverage | cost_ratio p10/p50/p90 | "
        "ambig L/S | sign_dev pip |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in sorted(summaries, key=lambda x: (x["signal_timeframe"], x["pair"])):
        lines.append(
            f"| {s['signal_timeframe']} | {s['pair']} | {s['n_total']} | "
            f"{s['n_valid']} | {s['coverage']:.4f} | "
            f"{s['cost_ratio_p10']:.3f} / {s['cost_ratio_p50']:.3f} / "
            f"{s['cost_ratio_p90']:.3f} | "
            f"{s['ambig_long']:.4f} / {s['ambig_short']:.4f} | "
            f"{s['sign_inv_dev']:.4f} |"
        )
    lines.append("")

    lines.append("## Schema reference")
    lines.append("")
    lines.append(f"- Version: `{schema_spec.get('version', '?')}`")
    lines.append(f"- Columns: {len(schema_spec.get('columns', []))}")
    lines.append(
        f"- Barrier profile: `{schema_spec.get('barrier_profile', '?')}` "
        f"(TP={schema_spec.get('tp_atr_mult', '?')} × ATR, "
        f"SL={schema_spec.get('sl_atr_mult', '?')} × ATR)"
    )
    lines.append(f"- Ambiguity resolution: `{schema_spec.get('ambiguity_resolution', '?')}`")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_ROOT / "validation_report.md")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="If any HALT, exit with non-zero code.",
    )
    args = parser.parse_args(argv)

    schema_path = args.root / "label_schema.json"
    if not schema_path.exists():
        print(f"label_schema.json not found at {schema_path}", file=sys.stderr)
        return 2
    schema_spec = json.loads(schema_path.read_text(encoding="utf-8"))

    parquets = discover_parquets(args.root)
    summaries: list[dict] = []
    for _tf, paths in parquets.items():
        for p in paths:
            summaries.append(load_pair_summary(p))

    warns, halts, metrics = evaluate_gates(summaries, schema_spec)
    write_report(args.out, summaries, warns, halts, metrics, schema_spec)

    print(f"Validation report: {args.out}")
    print(f"  WARN: {len(warns)}")
    print(f"  HALT: {len(halts)}")
    if halts:
        for h in halts:
            print(f"  - {h}")
    if args.strict and halts:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
