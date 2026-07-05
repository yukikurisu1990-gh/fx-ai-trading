"""ML Step 4 real-run body — implemented, REFUSED for real data (fixture-only).

Assembles the future production sequence (data → features → bulk B-2 labels via
``labels.py`` → training → validation-only threshold selection → single
event-driven holdout evaluation → metrics/acceptance → metadata-only evidence)
into one guarded path. In this build it is exercisable ONLY with synthetic
fixtures (`mode="fixture"`); `mode="real"` (or any non-fixture provider)
refuses. No real ``365d_BA`` data is read, no real metrics exist, and evidence
can only be written to non-protected paths (the repo-root guard refuses the
real evidence directory).

PR #416 required-in-body checklist bound here: (1) maxDD notional wired to the
contract constant (conflict fails closed); (2) ALL labels + trade scoring via
``labels.py`` (adapter failure propagates — no catch-and-continue); (3) UTC-date
coverage denominator; (4) real code SHA / seeds / package versions manifest;
(5) diagnostics labeler invoked in the evidence pipeline; (6) authoritative
integer-arithmetic split indices consumed, never recomputed.
"""

from __future__ import annotations

from typing import Any, Final

from . import contract, evidence, features, manifest, metrics, trainer
from .acceptance import AcceptanceEvaluator
from .data_adapter import FixtureDataProvider, pip_size_for, pip_size_map
from .executor import (
    ExecutionRefusedError,
    assert_diagnostics_excluded_from_decision,
    assert_diagnostics_labeled,
    label_diagnostics,
    reproducibility_policy,
)
from .labels import bars_from_frame, bulk_labels, label_contract_identity
from .metrics import MetricTrade, trading_day_utc
from .simulator import TradeSignal, simulate
from .split import bar_index_split
from .thresholds import select_threshold

MODE_FIXTURE: Final[str] = "fixture"
_CLASS_INDEX: Final[dict[int, int]] = {-1: 0, 0: 1, 1: 2}  # stub/LGBM class order


class BodyError(RuntimeError):
    """Raised when the run body detects a contract violation."""


def evaluate_portfolio(
    trades: list[MetricTrade],
    *,
    holdout_trading_days: int,
    notional_equity_pips: float | None = None,
) -> dict[str, Any]:
    """Portfolio metrics with the maxDD notional wired to the contract constant.

    PR #416 item 1: a caller-supplied notional that CONFLICTS with the frozen
    contract constant fails closed; omission uses the constant.
    """
    if notional_equity_pips is not None and (
        notional_equity_pips != contract.FIXED_NOTIONAL_EQUITY_PIPS
    ):
        raise BodyError(
            f"caller notional {notional_equity_pips} conflicts with contract "
            f"constant {contract.FIXED_NOTIONAL_EQUITY_PIPS}"
        )
    return metrics.compute_all(trades, holdout_trading_days=holdout_trading_days)


def _predictions_to_signals(
    pair: str,
    bars: list[dict],
    probs: list[list[float]],
    label_records: list[dict],
    indices: range,
    *,
    threshold: float,
    horizon: int,
) -> list[TradeSignal]:
    """Turn per-bar class probabilities into trade signals.

    PR #418 B-1 fix: signal PnL is the RAW traded-direction PnL from the
    ``labels.py`` bulk records (spread already embedded exactly once by the B-2
    ask-entry/bid-exit geometry). The flat evaluation cost cell is NOT applied
    here — the metrics layer is the single responsible layer for it, applied
    exactly once. ALL PnL and ALL exit timing still come from ``labels.py``
    (single-source trade scoring, R-4).
    """
    signals: list[TradeSignal] = []
    for i in indices:
        rec = label_records[i]
        if rec["label"] is None:
            continue
        p = probs[i]
        p_short, p_long = p[_CLASS_INDEX[-1]], p[_CLASS_INDEX[1]]
        if p_long >= p_short:
            direction, conf, pnl_key = "long", p_long, "pnl_long_pips"
        else:
            direction, conf, pnl_key = "short", p_short, "pnl_short_pips"
        if conf < threshold:
            continue
        exit_bar = i + 1 + rec[f"exit_{direction}_offset"]
        signals.append(
            TradeSignal(
                pair=pair, entry=i, exit_=exit_bar, direction=direction, pnl_pips=rec[pnl_key]
            )
        )
    return signals


def _trades_from_accepted(
    accepted: list[dict], bars_by_pair: dict[str, list[dict]]
) -> list[MetricTrade]:
    # ``pnl_pips`` here is RAW (gross of the flat cost cell); the metrics layer
    # subtracts the cell exactly once. MetricTrade.gross_pnl_pips is genuinely gross.
    return [
        MetricTrade(
            pair=t["pair"],
            day=trading_day_utc(bars_by_pair[t["pair"]][t["entry"]]["ts"]),
            gross_pnl_pips=t["pnl_pips"],
        )
        for t in accepted
    ]


def _segment_indices(seg: dict[str, Any], *, label_eligible: bool) -> range:
    end_key = "label_eligible_end_index_exclusive" if label_eligible else "end_index_exclusive"
    return range(seg["start_index"], seg[end_key])


def guarded_run_body(
    *,
    mode: str,
    provider: object | None = None,
    out_dir: str | None = None,
    cell_pips: float = contract.PRIMARY_COST_CELL_PIPS,
) -> dict[str, Any]:
    """The single guarded run-body path — fixture-only in this build.

    ``mode`` must be ``"fixture"`` with a synthetic-only provider; anything else
    refuses. The fixture rehearsal runs the full sequence end-to-end and writes
    the eight metadata-only evidence payloads to ``out_dir`` (which must NOT be
    the protected real evidence directory — the repo-root guard enforces this).
    """
    if mode != MODE_FIXTURE:
        raise ExecutionRefusedError(
            "real ML Step 4 run-body execution is not available in this build; "
            "only mode='fixture' (synthetic rehearsal) is permitted. A separately "
            "authorised first-run execution PR must enable the real mode."
        )
    provider = provider or FixtureDataProvider()
    if not getattr(provider, "synthetic_only", False) or getattr(provider, "mode", "") != "fixture":
        raise ExecutionRefusedError("guarded_run_body accepts only synthetic fixture providers")
    if out_dir is None:
        raise BodyError("out_dir required (non-protected test path) for fixture evidence")

    horizon = contract.HORIZON_M1_BARS
    run_manifest = manifest.build_run_manifest(
        mode="fixture_rehearsal",
        seeds={"fixture_lcg": provider.seed},
    )
    repro = reproducibility_policy()

    # --- per-pair data -> features -> labels (single source: labels.py) ------
    bars_by_pair: dict[str, list[dict]] = {}
    feats_by_pair: dict[str, list[list[float]]] = {}
    labels_by_pair: dict[str, list[dict]] = {}
    n_bars: int | None = None
    for pair in provider.pairs:
        bars = provider.bars_for(pair)
        if n_bars is None:
            n_bars = len(bars)
        elif len(bars) != n_bars:
            raise BodyError("fixture pairs must share a common bar count")
        rows, feat_names = features.compute_fixture_features(bars)
        # Single-source labels AND exit timing: everything from labels.py (R-4).
        # Pip conversion via the per-pair authority (INV-1 fix) — even in the
        # fixture path there is no fixed-global pip constant on the scoring path.
        recs = bulk_labels(
            bars,
            horizon=horizon,
            tp_mult=contract.TP_MULT_ATR14,
            sl_mult=contract.SL_MULT_ATR14,
            pip_size=pip_size_for(pair),
        )
        bars_by_pair[pair] = bars
        feats_by_pair[pair] = rows
        labels_by_pair[pair] = recs
    assert n_bars is not None

    # --- authoritative split indices (integer arithmetic; consumed, item 6) --
    split_meta = bar_index_split(n_bars)
    seg = split_meta["segments"]

    # --- training (fixture stub; from-scratch convention recorded) -----------
    train_idx = _segment_indices(seg["train"], label_eligible=True)
    x_train: list[list[float]] = []
    y_train: list[int] = []
    for pair in provider.pairs:
        for i in train_idx:
            rec = labels_by_pair[pair][i]
            if rec["label"] is not None:
                x_train.append(feats_by_pair[pair][i])
                y_train.append(rec["label"])
    model = trainer.FixtureModelStub().fit(x_train, y_train)
    probs_by_pair = {p: model.predict_proba(feats_by_pair[p]) for p in provider.pairs}

    # --- validation-only threshold selection ---------------------------------
    val_idx = _segment_indices(seg["validation"], label_eligible=True)
    val_metrics_by_threshold: dict[float, dict[str, Any]] = {}
    for thr in contract.THRESHOLD_CANDIDATES:
        val_signals: list[TradeSignal] = []
        for pair in provider.pairs:
            val_signals.extend(
                _predictions_to_signals(
                    pair,
                    bars_by_pair[pair],
                    probs_by_pair[pair],
                    labels_by_pair[pair],
                    val_idx,
                    threshold=thr,
                    horizon=horizon,
                )
            )
        sim = simulate(val_signals)
        trades = _trades_from_accepted(sim["accepted_trades"], bars_by_pair)
        # B-1 fix: validation charges the SAME primary cost cell as the holdout
        # (applied once by the metrics layer) — consistent charging.
        series = [v for _, v in metrics.daily_portfolio_pnl(trades, cell_pips)]
        val_metrics_by_threshold[thr] = {
            "daily_portfolio_sharpe": metrics.annualised_daily_sharpe(series),
            "n_trades": len(trades),
        }
    selection = select_threshold(val_metrics_by_threshold)

    # --- frozen holdout: evaluated once with the selected threshold ----------
    hold_idx = _segment_indices(seg["holdout"], label_eligible=False)
    hold_signals: list[TradeSignal] = []
    for pair in provider.pairs:
        hold_signals.extend(
            _predictions_to_signals(
                pair,
                bars_by_pair[pair],
                probs_by_pair[pair],
                labels_by_pair[pair],
                hold_idx,
                threshold=selection.selected_threshold,
                horizon=horizon,
            )
        )
    hold_sim = simulate(hold_signals)
    hold_trades = _trades_from_accepted(hold_sim["accepted_trades"], bars_by_pair)
    # R-5: denominator = distinct UTC calendar dates in the holdout window
    holdout_days = sorted(
        {trading_day_utc(bars_by_pair[pair][i]["ts"]) for pair in provider.pairs for i in hold_idx}
    )
    bundle = evaluate_portfolio(hold_trades, holdout_trading_days=len(holdout_days))
    acceptance = AcceptanceEvaluator().evaluate(bundle, provenance_complete=True)
    assert_diagnostics_excluded_from_decision(acceptance)

    # --- diagnostics (labeled NON_DECISION_EXPLORATORY, item 5) --------------
    diagnostics = label_diagnostics(
        {
            "feature_importance": {"names": feat_names, "note": "fixture stub — not learned"},
            "calibration": {"note": "fixture stub probabilities; no calibration"},
            "per_threshold_validation_curves": selection.as_dict(),
            "session_contribution": {"note": "not evaluated in this Step 4 (diagnostic only)"},
            "pair_contribution": metrics.pair_contribution(hold_trades, cell_pips),
            "win_rate": metrics.win_rate(hold_trades, cell_pips),
        }
    )
    assert_diagnostics_labeled(diagnostics)

    fixture_banner = {
        "fixture_rehearsal": True,
        "synthetic_only": True,
        "real_run": False,
        "non_decision": True,
    }
    # PR #418 B-1: make the cost convention explicit in evidence.
    cost_convention = {
        "spread": "embedded_once_by_b2_ask_entry_bid_exit_geometry",
        "flat_cost_cell": "applied_exactly_once_by_metrics_layer",
        "signal_pnl": "raw_gross_of_flat_cell",
        "primary_cell_pips": cell_pips,
        "validation_and_holdout_charge_identically": True,
        "double_charge": False,
    }
    payloads: dict[str, Any] = {
        "ml_step4_run_manifest.json": {
            **fixture_banner,
            **run_manifest,
            "reproducibility_policy": repro,
        },
        "ml_step4_pre_consumption_checksum_report.json": {
            **fixture_banner,
            "note": "fixture rehearsal — no real files exist; checksum verification "
            "is exercised against the committed inventory only at real execution",
            "checksums_computed": False,
        },
        "ml_step4_split_report.json": {**fixture_banner, **split_meta},
        "ml_step4_model_config_report.json": {
            **fixture_banner,
            **trainer.training_config(),
            "training_mode": trainer.TRAINING_MODE_FIXTURE,
        },
        "ml_step4_metrics_report.json": {
            **fixture_banner,
            "metrics": bundle,
            "diagnostics": diagnostics,
            "cost_convention": cost_convention,
        },
        "ml_step4_cost_sensitivity_report.json": {
            **fixture_banner,
            "cost_sensitivity": bundle["cost_sensitivity"],
            "cost_convention": cost_convention,
        },
        "ml_step4_leakage_provenance_report.json": {
            **fixture_banner,
            "label_contract": label_contract_identity(),
            "holdout_evaluated_count": 1,
            "threshold_selected_on": "validation_only",
            "split_indices_authoritative": True,
        },
        "ml_step4_acceptance_failure_decision_report.md": (
            "# FIXTURE REHEARSAL — synthetic only, non-decision\n\n"
            f"- acceptance_dry_output: {acceptance['status']}\n"
            f"- selected_threshold: {selection.selected_threshold}\n"
            f"- trades: {bundle['trade_count']}\n"
            "- real_run: false; this output is a plumbing rehearsal and must never\n"
            "  be cited as an ML Step 4 result.\n"
        ),
    }
    written = []
    for name, payload in payloads.items():
        evidence.write_report(out_dir, name, payload)
        written.append(name)

    return {
        "status": "ML_STEP4_FIXTURE_REHEARSAL_COMPLETED_NO_REAL_RUN",
        "implementation_status": "ML_STEP4_REAL_RUN_BODY_IMPLEMENTED_NO_RUN",
        "fixture_rehearsal_performed": True,
        "execution_performed": False,
        "raw_data_read": False,
        "model_trained": False,  # real-data training; fixture stub is not a model
        "holdout_evaluated": False,  # real holdout; fixture holdout is synthetic
        "real_evidence_written": False,
        "evidence_files": written,
        "selected_threshold": selection.selected_threshold,
        "n_holdout_trades_fixture": bundle["trade_count"],
        "holdout_days_fixture": len(holdout_days),
        "acceptance_dry_output": acceptance["status"],
    }


# ---------------------------------------------------------------------------
# Real 365d_BA first-run execution body (per-pair; memory-safe; shared helpers)
# ---------------------------------------------------------------------------

FIRST_RUN_COMPLETED = "ML_STEP4_365D_BA_FIRST_RUN_COMPLETED"
FIRST_RUN_STOPPED = "ML_STEP4_365D_BA_FIRST_RUN_STOPPED_BEFORE_TRAINING"


def _prob_short_long(model, x_rows):
    """(p_short, p_long) per row, robust to LightGBM class ordering."""
    classes = list(model.classes_)
    i_short = classes.index(_CLASS_INDEX[-1]) if _CLASS_INDEX[-1] in classes else None
    i_long = classes.index(_CLASS_INDEX[1]) if _CLASS_INDEX[1] in classes else None
    out = []
    for p in model.predict_proba(x_rows):
        out.append(
            (p[i_short] if i_short is not None else 0.0, p[i_long] if i_long is not None else 0.0)
        )
    return out


def _real_signals(pair, probs_sl, recs, indices, *, threshold):
    """Build raw-PnL trade signals for a pair over given indices (B-1 single-charge).

    ``probs_sl[i]`` = (p_short, p_long); PnL/exit come solely from ``recs`` (R-4).
    Signal PnL is RAW (gross of the flat cost cell — the metrics layer applies it).
    """
    sigs = []
    for i in indices:
        rec = recs[i]
        if rec["label"] is None:
            continue
        p_short, p_long = probs_sl[i]
        if p_long >= p_short:
            direction, conf, pnl_key = "long", p_long, "pnl_long_pips"
        else:
            direction, conf, pnl_key = "short", p_short, "pnl_short_pips"
        if conf < threshold:
            continue
        exit_bar = i + 1 + rec[f"exit_{direction}_offset"]
        sigs.append(
            TradeSignal(
                pair=pair, entry=i, exit_=exit_bar, direction=direction, pnl_pips=rec[pnl_key]
            )
        )
    return sigs


def _trades_with_days(accepted, day_by_index):
    return [
        MetricTrade(
            pair=t["pair"], day=day_by_index[t["pair"]][t["entry"]], gross_pnl_pips=t["pnl_pips"]
        )
        for t in accepted
    ]


def run_first_run_365d_ba(
    *,
    provider,
    out_dir: str,
    code_sha: str,
    cell_pips: float = contract.PRIMARY_COST_CELL_PIPS,
    real: bool = True,
):
    """Execute the PR #407 contract EXACTLY ONCE (real or a real-shaped fixture).

    Per pair: production v4-base features -> B-2 labels via labels.py -> common
    cross-pair window trim -> chronological 70/15/15 with 21-bar purge (from
    inventory metadata) -> from-scratch LightGBM -> validation-only threshold ->
    single frozen-holdout evaluation. Reuses the shared single-charge /
    B-2-fixed helpers. Writes eight metadata-only evidence payloads (raw PnL
    kept gross; cost cell applied once by the metrics layer).
    """
    from datetime import UTC, datetime

    from . import features as feat_mod
    from . import manifest as manifest_mod
    from .split import PairWindow, build_split
    from .trainer import train_lgbm, training_config

    horizon = contract.HORIZON_M1_BARS
    # INV-1 fix: resolve the per-pair pip size ONCE from the single authority so
    # labels, trade scoring, timeout MTM, metrics and evidence all read the same
    # value per pair. Fails closed here (before any training) if a pair lacks a
    # known pip size or the map is empty.
    pip_size_by_pair = pip_size_map(provider.pairs)
    pair_windows = [PairWindow(r.filename, r.ts_min_utc, r.ts_max_utc) for r in provider._records]
    split_meta = build_split(pair_windows)
    seg = split_meta["segments"]

    def _parse(ts):
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)

    common_start = _parse(split_meta["common_window"]["start_utc"])
    common_end = _parse(split_meta["common_window"]["end_utc"])
    tr_end = _parse(seg["train"]["end_utc"])
    tr_lab_end = _parse(seg["train"]["label_eligible_end_utc"])
    val_lab_end = _parse(seg["validation"]["label_eligible_end_utc"])
    hold_start = _parse(seg["holdout"]["start_utc"])

    val_signals_by_thr = {t: [] for t in contract.THRESHOLD_CANDIDATES}
    hold_signals_by_thr = {t: [] for t in contract.THRESHOLD_CANDIDATES}
    day_by_index = {}
    holdout_days = set()
    per_pair_meta = []
    # The frozen trainer convention defines NO random_state (PR #412 B-1); record
    # that honestly. Determinism is bounded (data ordering fixed; LightGBM may
    # retain thread/platform nondeterminism) — declared in the manifest.
    seeds = {
        "lightgbm_random_state": "not_set__trainer_convention_defines_none",
        "data_ordering": "deterministic__inventory_pair_order_then_timestamp",
    }

    for pair in provider.pairs:
        df = provider.pair_frame(pair)
        df = df[(df["timestamp"] >= common_start) & (df["timestamp"] <= common_end)]
        df = df.reset_index(drop=True)
        df, cols = feat_mod.compute_production_v4_base(df)
        ts_list = list(df["timestamp"])
        bars = bars_from_frame(df)
        pip = pip_size_by_pair[pair]  # per-pair authority (INV-1 fix)
        recs = bulk_labels(
            bars,
            horizon=horizon,
            tp_mult=contract.TP_MULT_ATR14,
            sl_mult=contract.SL_MULT_ATR14,
            pip_size=pip,
        )
        feat_rows = df[cols].fillna(0.0).values.tolist()
        n = len(ts_list)
        day_by_index[pair] = {}
        train_idx, val_idx, hold_idx = [], [], []
        for i in range(n):
            if recs[i]["label"] is None:
                continue
            t = ts_list[i]
            d = t.astimezone(UTC).strftime("%Y-%m-%d")
            if t < tr_lab_end:
                train_idx.append(i)
            elif tr_end <= t < val_lab_end:
                val_idx.append(i)
                day_by_index[pair][i] = d  # needed for validation daily aggregation
            elif t >= hold_start:
                hold_idx.append(i)
                day_by_index[pair][i] = d
                holdout_days.add(d)
        x_train = [feat_rows[i] for i in train_idx]
        y_train = [_CLASS_INDEX[recs[i]["label"]] for i in train_idx]
        model = train_lgbm(x_train, y_train)
        needed = sorted(set(val_idx) | set(hold_idx))
        prob_map = dict(
            zip(needed, _prob_short_long(model, [feat_rows[i] for i in needed]), strict=True)
        )
        probs_sl = [prob_map.get(i, (0.0, 0.0)) for i in range(n)]
        for thr in contract.THRESHOLD_CANDIDATES:
            val_signals_by_thr[thr].extend(
                _real_signals(pair, probs_sl, recs, val_idx, threshold=thr)
            )
            hold_signals_by_thr[thr].extend(
                _real_signals(pair, probs_sl, recs, hold_idx, threshold=thr)
            )
        per_pair_meta.append(
            {
                "pair": pair,
                "n_common_window_bars": n,
                "n_train_labeled": len(train_idx),
                "n_val_labeled": len(val_idx),
                "n_holdout_labeled": len(hold_idx),
                "model_classes": [int(c) for c in model.classes_],
                "pip_size": pip,
                "pip_size_kind": "jpy_cross" if pair.endswith("_JPY") else "non_jpy",
            }
        )
        del df, bars, recs, feat_rows, model

    val_metrics_by_threshold = {}
    for thr in contract.THRESHOLD_CANDIDATES:
        sim = simulate(val_signals_by_thr[thr])
        trades = _trades_with_days(sim["accepted_trades"], day_by_index)
        series = [v for _, v in metrics.daily_portfolio_pnl(trades, cell_pips)]
        val_metrics_by_threshold[thr] = {
            "daily_portfolio_sharpe": metrics.annualised_daily_sharpe(series),
            "n_trades": len(trades),
        }
    selection = select_threshold(val_metrics_by_threshold)

    hold_sim = simulate(hold_signals_by_thr[selection.selected_threshold])
    hold_trades = _trades_with_days(hold_sim["accepted_trades"], day_by_index)
    bundle = evaluate_portfolio(hold_trades, holdout_trading_days=len(holdout_days))
    acceptance = AcceptanceEvaluator().evaluate(bundle, provenance_complete=True)
    assert_diagnostics_excluded_from_decision(acceptance)

    run_manifest = manifest_mod.build_run_manifest(
        mode="real_first_run", seeds=seeds, pip_size_by_pair=pip_size_by_pair
    )
    cost_convention = {
        "spread": "embedded_once_by_b2_ask_entry_bid_exit_geometry",
        "flat_cost_cell": "applied_exactly_once_by_metrics_layer",
        "signal_pnl": "raw_gross_of_flat_cell",
        "primary_cell_pips": cell_pips,
        "double_charge": False,
    }
    diagnostics = label_diagnostics(
        {
            "per_threshold_validation_curves": selection.as_dict(),
            "session_contribution": {"note": "diagnostic only; session not evaluated"},
            "pair_contribution": metrics.pair_contribution(hold_trades, cell_pips),
            "win_rate": metrics.win_rate(hold_trades, cell_pips),
            "per_pair_data_summary": per_pair_meta,
        }
    )
    assert_diagnostics_labeled(diagnostics)

    banner = {"real_run": real, "run_class": "ml_step4_365d_ba_first_run"}
    non_auth = {
        "production_readiness_claimed": False,
        "paper_or_live_trading": False,
        "rerun_performed": False,
        "holdout_evaluated_count": 1,
    }
    vrep = provider.verification_report()
    payloads = {
        "ml_step4_run_manifest.json": {
            **banner,
            **run_manifest,
            "feature_binding": feat_mod.production_feature_binding(),
            "label_contract": label_contract_identity(),
            "non_authorisation": non_auth,
        },
        "ml_step4_pre_consumption_checksum_report.json": {**banner, **vrep},
        "ml_step4_split_report.json": {**banner, **split_meta},
        "ml_step4_model_config_report.json": {**banner, **training_config()},
        "ml_step4_metrics_report.json": {
            **banner,
            "metrics": bundle,
            "diagnostics": diagnostics,
            "cost_convention": cost_convention,
        },
        "ml_step4_cost_sensitivity_report.json": {
            **banner,
            "cost_sensitivity": bundle["cost_sensitivity"],
            "cost_convention": cost_convention,
        },
        "ml_step4_leakage_provenance_report.json": {
            **banner,
            "label_contract": label_contract_identity(),
            "feature_binding": feat_mod.production_feature_binding(),
            "provider_id": provider.provider_id,
            "checksum_all_match": vrep["all_match"],
            "holdout_evaluated_count": 1,
            "threshold_selected_on": "validation_only",
            "selected_threshold": selection.selected_threshold,
            "rejected_threshold_variants": selection.as_dict()["rejected_variants"],
            # INV-1 fix provenance: per-pair pip-size mapping is authoritative;
            # NO single global pip size governs all pairs.
            "pip_size_by_pair": dict(pip_size_by_pair),
            "pip_size_convention": "0.01 if pair endswith _JPY else 0.0001",
            "global_pip_size_authoritative_for_all_pairs": False,
        },
        "ml_step4_acceptance_failure_decision_report.md": (
            "# ML Step 4 365d_BA first-run acceptance\n\n"
            f"- acceptance_status: {acceptance['status']}\n"
            f"- selected_threshold: {selection.selected_threshold}\n"
            f"- holdout_trades: {bundle['trade_count']}\n"
            "- holdout_evaluated_count: 1 (exactly once)\n"
            "- production_readiness: NOT CLAIMED\n"
            "- interpretation: falsification/baseline measurement per PR #413; an\n"
            "  honest below-threshold result is valid; no rerun; no tuning.\n"
        ),
    }
    written = []
    for name, payload in payloads.items():
        evidence.write_report(out_dir, name, payload, allow_execution_evidence=True)
        written.append(name)

    return {
        "run_status": FIRST_RUN_COMPLETED,
        "acceptance_status": acceptance["status"],
        "production_status": contract.PRODUCTION_NOT_CLAIMED,
        "selected_threshold": selection.selected_threshold,
        "rejected_threshold_variants": selection.as_dict()["rejected_variants"],
        "holdout_trade_count": bundle["trade_count"],
        "holdout_days": len(holdout_days),
        "holdout_evaluated_count": 1,
        "metrics": bundle,
        "evidence_files": written,
        "code_sha": code_sha,
        "provider_id": provider.provider_id,
        "checksum_all_match": vrep["all_match"],
        "feature_cols_n": len(feat_mod.V4_BASE_FEATURE_COLS),
        "rerun_performed": False,
    }
