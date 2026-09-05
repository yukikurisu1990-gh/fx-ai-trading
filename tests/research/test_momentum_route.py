"""The momentum route's guard, its mirror property, and its aggregator.

Three things have to hold and none of them is "the code runs".

* The archive is **partitioned** by three guards. Adding a third route must not
  have widened either of the two that existed, and no route may reach the
  `EXPLORATORY_OOS_SLICE`, the dead window or the forward epoch.
* `momentum.signal` is the **exact mirror** of `round2._signal`, not an
  approximate one. It is implemented as a negation precisely so this is
  provable, and the proof is worth having because "we inverted the rule" is the
  entire hypothesis.
* `momentum_replication.evaluate_config` is a second implementation of an
  aggregation that already exists in frozen code. Two implementations of one
  thing drift unless something ties them together.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `POST_HOC_EXPLORATORY_HYPOTHESIS`.
"""

from __future__ import annotations

import inspect
import json

import numpy as np
import pandas as pd
import pytest

from scripts.research.exploratory_m15 import (
    MalformedUtcDateError,
    bars,
    engine,
    momentum,
    momentum_replication,
    round2,
    supplemental,
)

MOMENTUM = ("2021-04-26", "2023-04-25")
SUPPLEMENTAL = ("2023-04-26", "2025-04-24")
DEVELOPMENT = ("2025-04-25", "2025-12-28")
OOS_SLICE = ("2025-12-29", "2026-02-28")
DEAD_WINDOW = ("2026-03-01", "2026-04-24")
FORWARD_EPOCH = ("2026-04-25", "2026-05-29")
BEFORE_MOMENTUM = ("2016-06-02", "2021-04-25")

GUARDS = (
    (momentum.assert_momentum_span, momentum.MomentumSpanError),
    (supplemental.assert_supplemental_span, supplemental.SupplementalSpanError),
    (bars._assert_span, bars.ExploratorySpanError),
)


def _accepts(guard, error, span) -> bool:
    try:
        guard(*span)
    except (error, MalformedUtcDateError):
        return False
    return True


@pytest.mark.parametrize(
    ("span", "expected_index"),
    [(MOMENTUM, 0), (SUPPLEMENTAL, 1), (DEVELOPMENT, 2)],
)
def test_each_window_is_admitted_by_exactly_one_route(span, expected_index):
    """A partition, not three overlapping opinions about where the edges are."""
    admitted = [i for i, (g, e) in enumerate(GUARDS) if _accepts(g, e, span)]
    assert admitted == [expected_index]


@pytest.mark.parametrize("span", [OOS_SLICE, DEAD_WINDOW, FORWARD_EPOCH, BEFORE_MOMENTUM])
def test_no_route_admits_anything_outside_the_three_windows(span):
    assert [i for i, (g, e) in enumerate(GUARDS) if _accepts(g, e, span)] == []


def test_the_momentum_guard_refuses_one_day_over_either_edge():
    with pytest.raises(momentum.MomentumSpanError):
        momentum.assert_momentum_span("2021-04-25", "2023-04-25")
    with pytest.raises(momentum.MomentumSpanError):
        momentum.assert_momentum_span("2021-04-26", "2023-04-26")


def test_the_momentum_window_is_adjacent_to_the_seen_one():
    """A day of slack and the partition becomes three opinions again."""
    assert momentum.FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC == supplemental.SUPPLEMENTAL_START_UTC
    gap = pd.Timestamp(momentum.FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC) - pd.Timestamp(
        momentum.MOMENTUM_END_UTC
    )
    assert gap == pd.Timedelta(days=1)


def test_the_two_older_guards_were_not_widened():
    """Whatever this branch added, those two must refuse what they refused."""
    for span in (MOMENTUM, OOS_SLICE, DEAD_WINDOW, FORWARD_EPOCH):
        with pytest.raises(supplemental.SupplementalSpanError):
            supplemental.assert_supplemental_span(*span)
        with pytest.raises(bars.ExploratorySpanError):
            bars._assert_span(*span)
    supplemental.assert_supplemental_span(*SUPPLEMENTAL)
    bars._assert_span(*DEVELOPMENT)


@pytest.mark.parametrize("bound", ["2023", "2023-", "2023-04-2", "20230425", "2023-4-5", ""])
def test_no_malformed_bound_reaches_the_momentum_guard(bound):
    """String comparisons are sound only at fixed width; refuse the shape."""
    with pytest.raises((MalformedUtcDateError, momentum.MomentumSpanError)):
        momentum.assert_momentum_span("2021-04-26", bound)
    with pytest.raises((MalformedUtcDateError, momentum.MomentumSpanError)):
        momentum.assert_momentum_span(bound, "2023-04-25")


def test_the_momentum_guards_bounds_are_not_parameters():
    assert list(inspect.signature(momentum.assert_momentum_span).parameters) == ["start", "end"]


# --------------------------------------------------------------------------
# the scan
# --------------------------------------------------------------------------

ARCHIVE_DAYS = (
    "2016-06-02",
    "2021-04-25",
    "2021-04-26",
    "2022-05-10",
    "2023-04-25",
    "2023-04-26",
    "2025-04-25",
    "2025-12-29",
    "2026-04-25",
    "2026-05-29",
)
AUTHORISED = {"2021-04-26", "2022-05-10", "2023-04-25"}


@pytest.fixture
def spied_reader(tmp_path, monkeypatch):
    path = tmp_path / "candles_USD_JPY_M1_3650d_BA.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for day in ARCHIVE_DAYS:
            handle.write(
                json.dumps(
                    {
                        "time": f"{day}T00:00:00.000000000Z",
                        "bid_o": 1.0,
                        "bid_h": 1.0,
                        "bid_l": 1.0,
                        "bid_c": 1.0,
                        "ask_o": 1.1,
                        "ask_h": 1.1,
                        "ask_l": 1.1,
                        "ask_c": 1.1,
                    }
                )
                + "\n"
            )
    monkeypatch.setattr(momentum, "source_path", lambda pair: path)
    decoded: list[str] = []
    real = json.loads

    def spy(line, *args, **kwargs):
        row = real(line, *args, **kwargs)
        decoded.append(row["time"][:10])
        return row

    monkeypatch.setattr(momentum.json, "loads", spy)
    return decoded


def test_the_scan_decodes_only_authorised_days(spied_reader):
    """Decodes, not returns: under the standing ruling those are the same act."""
    frame = momentum.read_m1("USD_JPY")
    assert set(spied_reader) == AUTHORISED
    assert set(frame["ts"].dt.strftime("%Y-%m-%d")) == AUTHORISED


def test_a_narrower_request_narrows_the_scan(spied_reader):
    momentum.read_m1("USD_JPY", start="2022-01-01", end="2022-12-31")
    assert set(spied_reader) == {"2022-05-10"}


def test_the_reader_gates_before_it_opens_the_ten_year_archive():
    with pytest.raises(momentum.MomentumSpanError):
        momentum.read_m1("USD_JPY", start="2023-04-26", end="2025-04-24")
    with pytest.raises(momentum.MomentumSpanError):
        momentum.build_cache(["USD_JPY"], start="2021-04-26", end="2026-05-29")


def test_the_reader_refuses_a_pair_outside_the_registered_twenty():
    with pytest.raises(ValueError):
        momentum.source_path("EUR_TRY")


def _frame(days):
    return pd.DataFrame({"ts": pd.to_datetime([f"{d}T00:00:00Z" for d in days], utc=True)})


@pytest.mark.parametrize("day", ["2023-04-26", "2025-04-25", "2025-12-29", "2021-04-25"])
def test_a_cached_frame_carrying_a_forbidden_row_is_refused(day):
    with pytest.raises(momentum.MomentumSpanError):
        momentum.assert_rows_in_span(_frame(["2021-04-26", day]), pair="USD_JPY")


def test_load_itself_refuses_a_forbidden_cached_parquet(tmp_path, monkeypatch):
    monkeypatch.setattr(momentum, "CACHE_DIR", tmp_path)
    frame = pd.DataFrame(
        {
            "ts": pd.to_datetime(["2021-04-26T00:00:00Z", "2023-04-26T00:00:00Z"], utc=True),
            "mid_c": [1.0, 1.0],
        }
    )
    frame.to_parquet(tmp_path / "m15_USD_JPY.parquet", index=False)
    with pytest.raises(momentum.MomentumSpanError):
        momentum.load("USD_JPY")


# --------------------------------------------------------------------------
# the mirror
# --------------------------------------------------------------------------


def _synthetic(n: int = 20_000, seed: int = 7) -> pd.DataFrame:
    """Long bars with a *varying* range, so neither gate is degenerate.

    Length matters as much as variation: at `hold = 480` a 4,000-bar frame has
    nine rebalance points, and once an entry threshold and an ATR tercile are
    both applied none of them survives. The mirror test then compared two
    all-zero series, which proves nothing about a mirror.

    A first version also used a constant high/low offset, so ATR was constant,
    every trailing percentile rank tied and the `low` bucket selected nothing.
    The `(reversal != 0).sum() > 0` guard below caught both mistakes.
    """
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0, 0.02, n))
    span = 0.01 + np.abs(rng.normal(0, 0.03, n))
    ts = pd.date_range("2021-05-03", periods=n, freq="15min", tz="UTC")
    minute = ts.hour * 60 + ts.minute
    return pd.DataFrame(
        {
            "ts": ts,
            "mid_o": close,
            "mid_h": close + span,
            "mid_l": close - span,
            "mid_c": close,
            "spread_close_pips": 1.5,
            "pip_size": 0.01,
            "rollover": (minute < 22 * 60 + 15) & (minute + 15 > 21 * 60 + 55),
            "n_source_bars": 15,
            "complete_bucket": True,
            "session": "asia",
        }
    )


@pytest.mark.parametrize(
    "lookback,hold,entry_z,phase,bucket",
    [
        (480, 480, 1.0, 0, "all"),
        (384, 576, 1.0, 3, "all"),
        (576, 384, 0.0, 7, "high"),
        (480, 480, 1.5, 5, "low"),
    ],
)
def test_the_momentum_signal_is_the_exact_negation_of_the_reversal_signal(
    lookback, hold, entry_z, phase, bucket
):
    """Not "approximately opposite" — equal to the negation, bar for bar.

    The whole hypothesis is "invert the failed rule", so an inversion that
    silently differs anywhere else would make the round measure something other
    than what it claims.
    """
    frame = _synthetic()
    reversal = round2._signal(
        frame, lookback=lookback, hold=hold, entry_z=entry_z, phase=phase, atr_bucket=bucket
    )
    forward = momentum.signal(
        frame, lookback=lookback, hold=hold, entry_z=entry_z, phase=phase, atr_bucket=bucket
    )
    assert forward.equals(-reversal)
    assert int((reversal != 0).sum()) > 0, "a mirror of nothing proves nothing"


def test_the_momentum_signal_is_long_after_a_relatively_large_rise():
    """The direction as a fact about prices, not as a sign relative to reversal.

    Two things a first version of this test got wrong, both worth stating because
    they are facts about the candidate rather than about the test.

    The comparison is on the **decision** bars. The position is chosen on the
    rebalance grid and then held, so at an arbitrary held bar it reflects the move
    measured at the last grid point, not at that bar. Rollover bars are excluded:
    a decision there is blocked and the previous position carries through.

    And the quantity is the move's **z-score against its own trailing
    distribution**, not the raw move. The candidate is standardised momentum — it
    goes long a rise that is large *relative to* how that pair has been moving
    lately — so a positive move during a period of larger positive moves scores
    below zero and is shorted. That is the mirror of the reversal rule, which is
    what was frozen, and it is what "relatively" means here.
    """
    frame = _synthetic()
    hold, phase, entry_z = 480, 0, 1.0
    move = (frame["mid_c"] - frame["mid_c"].shift(480)) / frame["pip_size"]
    score = engine.zscore(move, round2.Z_WINDOW)
    signal = momentum.signal(frame, lookback=480, hold=hold, entry_z=entry_z, phase=phase)

    on_grid = np.zeros(len(frame), dtype=bool)
    on_grid[phase::hold] = True
    decided = pd.Series(on_grid, index=frame.index) & ~frame["rollover"] & (signal != 0)
    taken = signal[decided]
    assert len(taken) > 0, "no decision bar was exercised"
    assert (np.sign(taken) == np.sign(score[decided])).all(), (
        "momentum must hold the direction of the standardised move"
    )
    assert (score[decided].abs() > entry_z).all(), "a position was opened below the threshold"


def test_the_reversal_takes_the_opposite_side_of_the_same_decision():
    """The pair of rules must disagree everywhere, not merely on average."""
    frame = _synthetic()
    forward = momentum.signal(frame, lookback=480, hold=480, entry_z=1.0, phase=0)
    reversal = round2._signal(frame, lookback=480, hold=480, entry_z=1.0, phase=0)
    both_open = (forward != 0) & (reversal != 0)
    assert int(both_open.sum()) > 0
    assert (forward[both_open] == -reversal[both_open]).all()
    assert ((forward == 0) == (reversal == 0)).all(), "they must be flat at the same bars"


def test_the_frozen_candidate_is_read_from_round_2_not_restated():
    assert momentum.FROZEN_LOOKBACK == round2.CENTRE[0] == 480
    assert momentum.FROZEN_HOLD == round2.CENTRE[1] == 480
    assert momentum.FROZEN_ENTRY_Z == 1.0
    assert momentum_replication.FROZEN == {
        "lookback": momentum.FROZEN_LOOKBACK,
        "hold": momentum.FROZEN_HOLD,
        "entry_z": momentum.FROZEN_ENTRY_Z,
    }
    assert momentum.NEIGHBOURHOOD == (384, 480, 576)


def test_the_evaluation_is_still_causal_and_the_cost_model_unchanged():
    from scripts.research.exploratory_m15 import engine

    assert "position.shift(1)" in inspect.getsource(engine.evaluate)
    assert round2.ATR_RANK_WINDOW == 960
    assert round2.N_PHASES == 8
    assert engine.SLIPPAGE_PAD_PIPS == 0.5
    assert momentum_replication.COST_MULTIPLIERS == (1.0, 1.25, 1.5, 2.0, 3.0)


# --------------------------------------------------------------------------
# the aggregator
# --------------------------------------------------------------------------


def test_the_generic_aggregator_reproduces_the_frozen_one():
    """Hand it `round2._signal` and it must equal `round2.evaluate_config`.

    `momentum_replication.evaluate_config` exists only because the frozen one
    hard-wires its signal. That makes it a second copy of an aggregation, and a
    second copy drifts unless something pins it to the first.
    """
    frames = {n: _synthetic(n=6000, seed=i) for i, n in enumerate("ABC", start=1)}
    expected = round2.evaluate_config(frames, lookback=480, hold=480, entry_z=1.0)
    actual = momentum_replication.evaluate_config(
        frames, round2._signal, lookback=480, hold=480, entry_z=1.0
    )
    for key, value in expected.items():
        if key in ("daily_net", "pair_net_series"):
            continue
        assert actual[key] == value, key
    assert actual["daily_net"].equals(expected["daily_net"])


def test_the_mirror_identity_holds_on_the_aggregate():
    """Gross negates and cost does not, which is why a mirror is not a free win.

    Both directions hold positions of the same size and turn over at the same
    times, so they pay the same spread. `net_momentum = -gross_reversal - cost`,
    never `-net_reversal`.
    """
    frames = {"A": _synthetic(n=6000, seed=11), "B": _synthetic(n=6000, seed=12)}
    reversal = round2.evaluate_config(frames, lookback=480, hold=480, entry_z=1.0)
    forward = momentum_replication.evaluate_config(
        frames, momentum.signal, lookback=480, hold=480, entry_z=1.0
    )
    assert forward["gross_pips_per_pair"] == pytest.approx(
        -reversal["gross_pips_per_pair"], abs=0.05
    )
    assert forward["cost_pips_per_pair"] == pytest.approx(reversal["cost_pips_per_pair"], abs=0.05)
    assert forward["net_pips_per_pair"] == pytest.approx(
        -reversal["gross_pips_per_pair"] - reversal["cost_pips_per_pair"], abs=0.15
    )


def test_the_recorded_span_matches_the_pre_read_plan():
    assert momentum.MOMENTUM_START_UTC == "2021-04-26"
    assert momentum.MOMENTUM_END_UTC == "2023-04-25"
    assert momentum.SPAN_LABEL == "MOMENTUM_SUPPLEMENTAL_REPLICATION_B"
    assert momentum.SCOPE == "MOMENTUM_SUPPLEMENTAL_EXPLORATORY_HISTORY"
    assert momentum.OPERATION_READ == "track_a_momentum_historical_read"
    assert momentum.OPERATION_DERIVATION == "track_a_momentum_m15_derivation"
