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
from .data_adapter import PIP_SIZE, FixtureDataProvider
from .executor import (
    ExecutionRefusedError,
    assert_diagnostics_excluded_from_decision,
    assert_diagnostics_labeled,
    label_diagnostics,
    reproducibility_policy,
)
from .labels import apply_cost_cell, bulk_labels, label_contract_identity
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
    cell_pips: float,
) -> list[TradeSignal]:
    """Turn per-bar class probabilities into trade signals.

    ALL PnL and ALL exit timing come from the ``labels.py`` bulk records
    (single-source trade scoring, R-4). Occupancy interval = entry bar index →
    resolved exit bar index (barrier or timeout per ``exit_window_offset``).
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
        pnl = apply_cost_cell(rec[pnl_key], cell_pips)
        signals.append(
            TradeSignal(pair=pair, entry=i, exit_=exit_bar, direction=direction, pnl_pips=pnl)
        )
    return signals


def _trades_from_accepted(
    accepted: list[dict], bars_by_pair: dict[str, list[dict]]
) -> list[MetricTrade]:
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
        recs = bulk_labels(
            bars,
            horizon=horizon,
            tp_mult=contract.TP_MULT_ATR14,
            sl_mult=contract.SL_MULT_ATR14,
            pip_size=PIP_SIZE,
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
                    cell_pips=cell_pips,
                )
            )
        sim = simulate(val_signals)
        trades = _trades_from_accepted(sim["accepted_trades"], bars_by_pair)
        series = [v for _, v in metrics.daily_portfolio_pnl(trades, 0.0)]
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
                cell_pips=cell_pips,
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
        },
        "ml_step4_cost_sensitivity_report.json": {
            **fixture_banner,
            "cost_sensitivity": bundle["cost_sensitivity"],
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
