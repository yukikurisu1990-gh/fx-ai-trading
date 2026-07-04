"""F-2 label / PnL adapter invariant tests (synthetic cases)."""

from __future__ import annotations

import pytest

from scripts.ml_step4 import labels
from scripts.ml_step4.labels import (
    LONG,
    SHORT,
    LabelContractError,
    apply_cost_cell,
    barrier_label,
    first_hit_index,
    traded_direction_pnl_pips,
)

PIP = 0.0001


def test_first_hit_index() -> None:
    assert first_hit_index([False, False, True, False]) == 2
    assert first_hit_index([False, False]) == -1


def test_same_bar_tp_sl_tie_chooses_sl() -> None:
    # TP and SL both fire at index 3 -> SL-first (conservative), negative PnL.
    pnl = traded_direction_pnl_pips(
        direction=LONG,
        tp_idx=3,
        sl_idx=3,
        tp_dist_price=1.5 * PIP,
        sl_dist_price=1.0 * PIP,
        mtm_exit_pnl_price=0.5 * PIP,
        pip_size=PIP,
    )
    assert pnl == pytest.approx(-1.0)


def test_sl_before_tp_is_negative() -> None:
    pnl = traded_direction_pnl_pips(
        direction=SHORT,
        tp_idx=5,
        sl_idx=2,
        tp_dist_price=1.5 * PIP,
        sl_dist_price=1.0 * PIP,
        mtm_exit_pnl_price=0.0,
        pip_size=PIP,
    )
    assert pnl == pytest.approx(-1.0)


def test_tp_before_sl_is_positive() -> None:
    pnl = traded_direction_pnl_pips(
        direction=LONG,
        tp_idx=2,
        sl_idx=7,
        tp_dist_price=1.5 * PIP,
        sl_dist_price=1.0 * PIP,
        mtm_exit_pnl_price=0.0,
        pip_size=PIP,
    )
    assert pnl == pytest.approx(1.5)


def test_timeout_mark_to_market_not_zeroed() -> None:
    # Neither barrier hit within horizon -> horizon-end MTM, NOT 0.
    pnl = traded_direction_pnl_pips(
        direction=LONG,
        tp_idx=-1,
        sl_idx=-1,
        tp_dist_price=1.5 * PIP,
        sl_dist_price=1.0 * PIP,
        mtm_exit_pnl_price=0.37 * PIP,
        pip_size=PIP,
    )
    assert pnl == pytest.approx(0.37)
    assert pnl != 0.0


def test_long_short_pnl_signs() -> None:
    # Long TP hit -> +tp; short SL hit -> -sl. Signs are direction-correct.
    long_tp = traded_direction_pnl_pips(
        direction=LONG,
        tp_idx=1,
        sl_idx=-1,
        tp_dist_price=1.5 * PIP,
        sl_dist_price=1.0 * PIP,
        mtm_exit_pnl_price=0.0,
        pip_size=PIP,
    )
    short_sl = traded_direction_pnl_pips(
        direction=SHORT,
        tp_idx=-1,
        sl_idx=1,
        tp_dist_price=1.5 * PIP,
        sl_dist_price=1.0 * PIP,
        mtm_exit_pnl_price=0.0,
        pip_size=PIP,
    )
    assert long_tp > 0 and short_sl < 0


def test_spread_not_double_counted() -> None:
    # Barrier PnL equals exactly +/- the geometry distance (spread embedded once);
    # only the flat slippage cell is additive, applied a single time.
    gross = traded_direction_pnl_pips(
        direction=LONG,
        tp_idx=1,
        sl_idx=-1,
        tp_dist_price=1.5 * PIP,
        sl_dist_price=1.0 * PIP,
        mtm_exit_pnl_price=0.0,
        pip_size=PIP,
    )
    assert gross == pytest.approx(1.5)  # no extra spread subtracted
    net = apply_cost_cell(gross, 0.5)
    assert net == pytest.approx(1.0)  # slippage applied exactly once


def test_barrier_label_rules() -> None:
    # long clears (tp before sl), short does not -> +1
    assert barrier_label(long_tp_idx=1, long_sl_idx=5, short_tp_idx=-1, short_sl_idx=2) == 1
    # short clears only -> -1
    assert barrier_label(long_tp_idx=-1, long_sl_idx=2, short_tp_idx=1, short_sl_idx=5) == -1
    # neither clears -> 0
    assert barrier_label(long_tp_idx=-1, long_sl_idx=1, short_tp_idx=-1, short_sl_idx=1) == 0
    # both clear -> earlier TP wins (long earlier)
    assert barrier_label(long_tp_idx=1, long_sl_idx=9, short_tp_idx=3, short_sl_idx=9) == 1


def test_fail_closed_on_bad_inputs() -> None:
    with pytest.raises(LabelContractError):
        traded_direction_pnl_pips(
            direction="sideways",
            tp_idx=1,
            sl_idx=2,
            tp_dist_price=1.0,
            sl_dist_price=1.0,
            mtm_exit_pnl_price=0.0,
            pip_size=PIP,
        )
    with pytest.raises(LabelContractError):
        traded_direction_pnl_pips(
            direction=LONG,
            tp_idx=1,
            sl_idx=2,
            tp_dist_price=-1.0,
            sl_dist_price=1.0,
            mtm_exit_pnl_price=0.0,
            pip_size=PIP,
        )
    with pytest.raises(LabelContractError):
        apply_cost_cell(1.0, -0.5)


def test_uses_committed_helper() -> None:
    # Confirms the adapter delegates to the committed F-2 helper.
    from scripts.traded_direction_pnl import traded_direction_pnl_price

    assert labels.traded_direction_pnl_price is traded_direction_pnl_price
