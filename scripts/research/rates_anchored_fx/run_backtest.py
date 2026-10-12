# ruff: noqa: E501 -- research prose
"""primary・controls・sensitivity・診断・判定を 1 回だけ実行し、記録する（事前登録 §4〜§13）。

command: python -X utf8 -m scripts.research.rates_anchored_fx.run_backtest
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.patsd_stage0 import data as guarded
from scripts.research.rates_anchored_fx import data_rates as dr
from scripts.research.rates_anchored_fx import engine as en

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/rates_anchored_fx/backtest.json"
PREREG: Final[Path] = REPO / "docs/research/rates_anchored_fx_prereg_2026_10.md"
CALENDAR: Final[Path] = REPO / "artifacts/track_a_scratch/exogenous/s1_calendar.json"
PAIRS: Final[dict[str, str]] = {"EUR_USD": "EUR", "GBP_USD": "GBP"}
UC_POOL: Final[tuple[str, ...]] = (
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CAD",
    "USD_CHF",
    "USD_JPY",
)
HOLDOUT_START: Final = pd.Timestamp("2025-01-01").date()


def _git(*a: str) -> str:
    return subprocess.run(
        ["git", *a], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _clean(x: Any) -> Any:
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [_clean(v) for v in x]
    if isinstance(x, np.generic):
        return _clean(x.item())
    return x


def foreign_log_value(pair: str, fx: pd.DataFrame) -> pd.Series:
    lm = np.log(fx.loc[fx["ok"], "mid_c"])
    return lm if pair.endswith("_USD") else -lm


def build(
    spec_uc: bool,
    raw_fx: dict[str, pd.DataFrame],
    rates: dict[str, pd.DataFrame],
    shift: bool = False,
) -> dict[str, en.PairData]:
    usd = rates["USD"]
    out = {}
    for pair, cur in PAIRS.items():
        fx = en.fx_grid(raw_fx[pair])
        lvl, ok = en.rd_level(rates[cur], usd)
        if shift:
            lvl = en.shift_one_trading_day(lvl)
            ok = en.shift_one_trading_day(ok.astype(float)).astype(bool)
        levels = {"RD": lvl}
        if spec_uc:
            others = [p for p in UC_POOL if p != pair]
            frame = pd.concat(
                {p: foreign_log_value(p, en.fx_grid(raw_fx[p])) for p in others}, axis=1
            )
            uc = frame.dropna(thresh=4).mean(axis=1)
            levels["UC"] = uc
        out[pair] = en.PairData(pair=pair, fx=fx, levels=levels, rate_ok=ok)
    return out


def run(
    pairs: dict[str, en.PairData],
    spec: en.Spec,
    fomc: set,
    ecb: set,
    *,
    price_only: bool = False,
    random_sign: bool = False,
) -> dict[str, Any]:
    regressors = ["RD"] + (["UC"] if spec.use_usd_common else [])
    sigs, fits_all, diag, eval_days_by_pair = {}, {}, {}, {}
    rng = np.random.default_rng(en.SEED)
    for p, pdat in pairs.items():
        obs = en.observations(pdat)
        if random_sign:
            sign = rng.choice([-1.0, 1.0], size=len(obs))
            obs = obs.copy()
            obs["dRD"] = obs["dRD"] * sign
            obs["rd_sign"] = sign
        fits = en.daily_fits(obs, regressors, spec)
        days = sorted(obs["day"].unique())
        costs = en.cost_profile(pdat.fx, days, spec.lookback_days)
        atr = en.atr_series(pdat.fx, spec.atr_n)
        sigs[p] = en.candidate_signals(
            pdat, obs, fits, costs, atr, spec, regressors, price_only=price_only
        )
        fits_all[p] = fits
        eval_days_by_pair[p] = list(fits.index)
        if not price_only and not random_sign:
            diag[p] = en.diagnostics(pdat, obs, fits, regressors)
    trades = en.run_portfolio(sigs, pairs, regressors, spec, fomc, ecb, price_only=price_only)
    df = en.trades_frame(trades)
    eval_days = sorted(set().union(*[set(v) for v in eval_days_by_pair.values()]))
    return {
        "df": df,
        "eval_days": eval_days,
        "eval_days_by_pair": eval_days_by_pair,
        "fits": fits_all,
        "diag": diag,
        "signals": sigs,
    }


def summarize(res: dict[str, Any]) -> dict[str, Any]:
    df, days = res["df"], res["eval_days"]
    out: dict[str, Any] = {"portfolio": en.metrics(df, days)}
    if len(df) == 0:
        return out
    out["by_pair"] = {
        p: en.metrics(df[df["pair"] == p], res["eval_days_by_pair"][p])
        for p in res["eval_days_by_pair"]
    }
    out["by_kind"] = {k: en.metrics(df[df["kind"] == k], days) for k in ("A", "B")}
    out["by_event"] = {
        "EVENT": en.metrics(df[df["event"]], days),
        "NON_EVENT": en.metrics(df[~df["event"]], days),
    }
    out["by_year"] = {}
    for y in sorted(df["year"].unique()):
        yd = [d for d in days if d.year == y]
        out["by_year"][str(y)] = en.metrics(df[df["year"] == y], yd)
    out["leave_one_year_out_net_mean_bp"] = {
        str(y): round(float(df.loc[df["year"] != y, "net_bp"].mean()), 4)
        for y in sorted(df["year"].unique())
    }
    dev = [d for d in days if d < HOLDOUT_START]
    hold = [d for d in days if d >= HOLDOUT_START]
    out["development"] = en.metrics(df[df["exit_day"] < HOLDOUT_START], dev)
    out["final_seen_holdout_2025"] = en.metrics(df[df["exit_day"] >= HOLDOUT_START], hold)
    out["exit_reasons"] = df["exit_reason"].value_counts().to_dict()
    out["overlap_A_and_B"] = int(df["overlap"].sum())
    out["bootstrap"] = en.bootstrap(df, days)
    return out


def classify(primary: dict, stress: dict, controls: dict, diag: dict) -> dict[str, Any]:
    pf = primary["portfolio"]
    net = pf.get("net_mean_bp", float("nan"))
    gross = pf.get("gross_mean_bp", float("nan"))
    gs = pf.get("gross_sharpe", float("nan"))
    sh = pf.get("sharpe", float("nan"))
    reasons: list[str] = []

    def pooled(bins: list[str]) -> float:
        tot, n = 0.0, 0
        for d in diag.values():
            for b in bins:
                c = d["convergence_120m_by_abs_z"].get(b, {})
                if c.get("n"):
                    tot += c["mean_conv_bp"] * c["n"]
                    n += c["n"]
        return tot / n if n else float("nan")

    hi = pooled(["2.5-3.0", "3.0-inf"])
    lo = pooled(["1.0-1.5", "1.5-2.0", "2.0-2.5"])
    monotone = bool(hi > lo)
    rate_adds = bool(
        net > controls["TIME_SHIFTED"]["portfolio"].get("net_mean_bp", -math.inf)
        and net > controls["RANDOM_SIGN"]["portfolio"].get("net_mean_bp", -math.inf)
        and sh > controls["PRICE_ONLY_STANDALONE"]["portfolio"].get("sharpe", -math.inf)
    )
    facts = {
        "net_mean_bp": net,
        "gross_mean_bp": gross,
        "gross_sharpe": gs,
        "net_sharpe": sh,
        "conv_120m_high_bins_bp": round(hi, 4),
        "conv_120m_low_bins_bp": round(lo, 4),
        "monotone": monotone,
        "rate_information_adds_edge": rate_adds,
    }
    if not (net > 0):
        label = "RAC-E" if (gross > 0 and gs >= 0.3) else "RAC-F"
        reasons.append("net の期待値 ≤ 0")
        return {"classification": label, "facts": facts, "reasons": reasons}
    if not rate_adds:
        return {
            "classification": "RAC-D",
            "facts": facts,
            "reasons": ["金利の情報が増分の edge を持たない（§9）"],
        }
    pairs_pos = sum(1 for m in primary["by_pair"].values() if m.get("net_mean_bp", -1) > 0)
    kinds_pos = sum(
        1
        for m in primary["by_kind"].values()
        if m.get("trades", 0) and m.get("net_mean_bp", -1) > 0
    )
    loyo = all(v > 0 for v in primary["leave_one_year_out_net_mean_bp"].values())
    strong = (
        sh >= 1.0
        and pf["maxdd_pct_1x"] <= 15
        and pairs_pos >= 2
        and stress["C2"]["portfolio"].get("net_mean_bp", -1) > 0
        and loyo
        and hi > 0
    )
    facts.update(
        {
            "pairs_positive": pairs_pos,
            "kinds_positive": kinds_pos,
            "leave_one_year_out_all_positive": loyo,
        }
    )
    if strong:
        return {"classification": "RAC-A", "facts": facts, "reasons": reasons}
    if sh >= 0.5 and (pairs_pos >= 2 or kinds_pos >= 2) and monotone:
        return {"classification": "RAC-B", "facts": facts, "reasons": reasons}
    ci = primary["bootstrap"]["sharpe_ci90"]
    if sh >= 0.3 and ci[0] <= 0 <= ci[1] and monotone:
        return {"classification": "RAC-C", "facts": facts, "reasons": reasons}
    return {
        "classification": "RAC-E" if gs >= 0.3 else "RAC-F",
        "facts": facts,
        "reasons": ["net > 0 だが弱い（Sharpe < 0.3 か集中）"],
    }


def matched_price_only(
    primary_res: dict, pairs: dict[str, en.PairData], spec: en.Spec, fomc: set, ecb: set
) -> dict:
    df = primary_res["df"]
    a = df[df["kind"] == "A"]
    out = []
    for _, tr in a.iterrows():
        sig = primary_res["signals"][tr["pair"]].loc[tr["entry"]].copy()
        o_dfx = sig["res"] + sig["fair"]
        sig["res"] = o_dfx
        sig["fair"] = 0.0
        sig["fair_sigma"] = 0.0
        d = int(-np.sign(o_dfx))
        if d == 0:
            continue
        t = en.simulate(
            pairs[tr["pair"]], sig, ["RD"], spec, fomc, ecb, price_only=True, direction_override=d
        )
        if t is not None:
            out.append(t)
    m = en.trades_frame(out)
    return {
        "trades": int(len(m)),
        "net_mean_bp": round(float(m["net_bp"].mean()), 4) if len(m) else None,
        "gross_mean_bp": round(float(m["gross_bp"].mean()), 4) if len(m) else None,
        "primary_A_net_mean_bp": round(float(a["net_bp"].mean()), 4) if len(a) else None,
        "primary_A_gross_mean_bp": round(float(a["gross_bp"].mean()), 4) if len(a) else None,
        "same_direction_share": round(
            float((a["direction"].to_numpy() == np.array([t.direction for t in out])).mean()), 4
        )
        if len(out) == len(a) and len(a)
        else None,
    }


def main() -> int:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    if _git("status", "--porcelain", "--", "scripts", "docs", "tests"):
        raise SystemExit("dirty tree では走らせない")
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cal = json.loads(CALENDAR.read_text(encoding="utf-8"))["payload"]["dates"]
    fomc = {pd.Timestamp(d).date() for d in cal["USD"]}
    ecb = {pd.Timestamp(d).date() for d in cal["EUR"]}
    raw_fx = {p: guarded.load_pair(p) for p in UC_POOL}
    rates = {c: en.rate_mid(dr.load(c)) for c in ("USD", "EUR", "GBP")}
    base = build(False, raw_fx, rates)
    spec = en.Spec()
    primary_res = run(base, spec, fomc, ecb)
    primary = summarize(primary_res)
    stress = {
        name: summarize(run(base, en.with_spec(spec, cost_stress=k), fomc, ecb))
        for name, k in (("C1", 1.25), ("C2", 1.5), ("C3", 2.0))
    }
    controls = {
        "PRICE_ONLY_STANDALONE": summarize(run(base, spec, fomc, ecb, price_only=True)),
        "TIME_SHIFTED": summarize(run(build(False, raw_fx, rates, shift=True), spec, fomc, ecb)),
        "RANDOM_SIGN": summarize(run(base, spec, fomc, ecb, random_sign=True)),
    }
    controls["PRICE_ONLY_MATCHED"] = matched_price_only(primary_res, base, spec, fomc, ecb)
    sens_specs = {
        "z_2.0": {"z_entry": 2.0, "min_fair_z": 2.0},
        "z_3.0": {"z_entry": 3.0, "min_fair_z": 3.0},
        "lookback_60": {"lookback_days": 60},
        "lookback_120": {"lookback_days": 120},
        "hold_60": {"max_hold_min": 60},
        "hold_180": {"max_hold_min": 180},
        "cost_multiple_3": {"cost_multiple": 3.0},
        "cost_multiple_5": {"cost_multiple": 5.0},
        "capture_0.4": {"capture": 0.4},
        "capture_0.8": {"capture": 0.8},
        "slippage_0.25": {"slippage_bp": 0.25},
        "slippage_1.0": {"slippage_bp": 1.0},
        "sigma_sd": {"sigma_kind": "sd"},
    }
    sensitivity = {
        k: summarize(run(base, en.with_spec(spec, **v), fomc, ecb))["portfolio"]
        for k, v in sens_specs.items()
    }
    uc = build(True, raw_fx, rates)
    sensitivity["secondary_usd_common_factor"] = summarize(
        run(uc, en.with_spec(spec, use_usd_common=True), fomc, ecb)
    )["portfolio"]
    verdict = classify(primary, stress, controls, primary_res["diag"])
    trades = primary_res["df"].copy()
    trades["entry"] = trades["entry"].astype(str)
    trades["exit"] = trades["exit"].astype(str)
    trades["exit_day"] = trades["exit_day"].astype(str)
    payload = {
        "head": _git("rev-parse", "HEAD"),
        "dirty_path_count": 0,
        "prereg_sha256": _sha(PREREG),
        "command": "python -X utf8 -m scripts.research.rates_anchored_fx.run_backtest",
        "started_utc": started,
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
        "code_sha256": {
            p.name: _sha(p)
            for p in sorted((REPO / "scripts/research/rates_anchored_fx").glob("*.py"))
        },
        "input_sha256": {
            "fx": {p: guarded.content_hash(f) for p, f in raw_fx.items()},
            "rates_manifest": _sha(
                REPO / "artifacts/research/rates_anchored_fx/rates_acquisition.json"
            ),
            "calendar": _sha(CALENDAR),
        },
        "spec": spec.__dict__,
        "primary": primary,
        "diagnostics": primary_res["diag"],
        "cost_stress": {k: v["portfolio"] for k, v in stress.items()},
        "controls": {k: v.get("portfolio", v) for k, v in controls.items()},
        "sensitivity": sensitivity,
        "classification": verdict,
        "trades": trades.to_dict(orient="records"),
    }
    raw = (json.dumps(_clean(payload), ensure_ascii=False, indent=1, default=str) + "\n").encode(
        "utf-8"
    )
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())
    print(
        json.dumps(
            _clean({"classification": verdict, "portfolio": primary["portfolio"]}),
            ensure_ascii=False,
            indent=1,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
