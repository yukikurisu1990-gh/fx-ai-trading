"""Round A's pre-registration, its window semantics, and its prohibition.

Three things a test can protect that a document cannot.

* **The pre-registration.** The plan fixes 5 atlas horizons, 3 screen horizons,
  5 condition families with 13 levels, 39 cells and six numeric thresholds. If a
  later edit adds a level or moves a threshold, the family stops being the one
  that was registered and the multiplicity correction stops meaning anything.
* **The window.** T1's excursions and T2's contributions both have to line up
  with `engine.evaluate`'s hold semantics — decision at `t`, on risk from `t+1`,
  exit at `t+H+1`. Being off by one here is the same class of defect as same-bar
  leakage, and it is invisible in the output.
* **The prohibition.** MFE and MAE are computed from future bars deliberately.
  Nothing in Round A may turn one into a position.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.
"""

from __future__ import annotations

import ast
import inspect

import numpy as np
import pandas as pd
import pytest

from scripts.research.exploratory_m15 import engine, round2
from scripts.research.round_a import DECIDING_PANELS, PANELS, atlas, driver, ledger, panels, screen


def _frame(n: int = 900, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0, 0.05, n))
    span = 0.02 + np.abs(rng.normal(0, 0.04, n))
    ts = pd.date_range("2022-03-01", periods=n, freq="15min", tz="UTC")
    minute = ts.hour * 60 + ts.minute
    return pd.DataFrame(
        {
            "ts": ts,
            "mid_o": close,
            "mid_h": close + span,
            "mid_l": close - span,
            "mid_c": close,
            "spread_close_pips": 2.0,
            "pip_size": 0.01,
            "rollover": (minute < 22 * 60 + 15) & (minute + 15 > 21 * 60 + 55),
            "n_source_bars": 15,
            "complete_bucket": True,
            "session": "asia",
        }
    )


# --------------------------------------------------------------------------
# the pre-registration
# --------------------------------------------------------------------------


def test_the_atlas_dimensions_are_the_registered_ones():
    assert panels.ATLAS_HORIZONS == (16, 48, 96, 192, 480)
    assert set(panels.BLOCS) == {"ALL", "JPY", "non_JPY"}
    assert len(panels.JPY_PAIRS) == 6
    assert len(panels.NON_JPY_PAIRS) == 14


def test_the_screen_is_exactly_thirty_nine_cells():
    """13 levels x 3 horizons. The plan allows 48 and closes the family at 39."""
    levels = sum(len(levels) for _, levels, _ in screen.FAMILIES.values())
    assert levels == 13
    assert panels.SCREEN_HORIZONS == (48, 192, 480)
    assert levels * len(panels.SCREEN_HORIZONS) == 39


def test_the_condition_families_and_their_directions_are_fixed():
    assert set(screen.FAMILIES) == {"F1_atr", "F2_vol", "F3_d1_trend", "F4_range", "F5_extreme"}
    rules = {name: rule for name, (_, _, rule) in screen.FAMILIES.items()}
    assert rules["F1_atr"] == "fade_past_move"
    assert rules["F2_vol"] == "fade_past_move"
    assert rules["F5_extreme"] == "fade_past_move"
    assert rules["F3_d1_trend"] == "follow_d1"
    assert rules["F4_range"] == "fade_range_position"


def test_the_numeric_thresholds_are_the_registered_ones():
    assert atlas.RICH_MFE_OVER_COST == 3.0
    assert atlas.RICH_P_TWO_COST == 0.50
    assert atlas.MARGINAL_MFE_OVER_COST == 1.5
    assert screen.MIN_EFFECT_OVER_COST == 2.0
    assert screen.MIN_EFFECTIVE_OBSERVATIONS == 30
    assert screen.MIN_EFFECTIVE_PAIRS == 3.0
    assert screen.N_PHASES == round2.N_PHASES == 8


def test_the_state_definitions_reuse_round2s_constants():
    """So the ATR state is the same object the earlier rounds conditioned on."""
    source = inspect.getsource(panels.derived)
    assert "round2.ATR_PERIOD" in source
    assert "round2.ATR_RANK_WINDOW" in source
    assert "round2.Z_WINDOW" in source
    assert panels.RANGE_WINDOW == 192
    assert panels.EXTREME_LOOKBACK == 96
    assert panels.EXTREME_Z == 2.0


def test_each_direction_rule_produces_the_direction_it_names():
    """Pinned by output. Pinning the rule-name string lets the rule invert.

    An audit flipped `fade_past_move` to `+sign(past)` and
    `fade_range_position` to follow the extreme, and every test passed because
    only the strings were checked.
    """
    frame = panels.derived(_frame(n=1200))
    horizon = 48
    past = frame["mid_c"] - frame["mid_c"].shift(horizon)
    fade = screen.context_direction(frame, "fade_past_move", horizon)
    live = past.notna() & (past != 0)
    assert (fade[live] == -np.sign(past[live])).all(), "fade_past_move must oppose the move"

    d1 = screen.context_direction(frame, "follow_d1", horizon)
    up = frame["d1_state"] == "up"
    assert (d1[up] == 1.0).all() and (d1[frame["d1_state"] == "down"] == -1.0).all()

    ranged = screen.context_direction(frame, "fade_range_position", horizon)
    high = frame["range_position"] > 0.5
    low = frame["range_position"] < 0.5
    assert (ranged[high] == -1.0).all(), "must short the top of the range"
    assert (ranged[low] == 1.0).all(), "must buy the bottom of the range"


def test_the_state_bin_edges_are_the_registered_ones():
    """Bin edges are literals inside `derived` and an audit widened one freely."""
    source = inspect.getsource(panels.derived)
    for edge in (
        '("Q1", -0.01, 0.25)',
        '("Q2", 0.25, 0.50)',
        '("Q3", 0.50, 0.75)',
        '("Q4", 0.75, 1.01)',
    ):
        assert edge in source, edge
    assert "rank <= 1 / 3" in source and "rank > 2 / 3" in source
    assert "ratio <= 1.0" in source
    #: and the extreme threshold at its use site, not only as a constant
    assert "extreme_z.abs() > EXTREME_Z" in source

    frame = panels.derived(_frame(n=1500))
    position = frame["range_position"]
    inside = position.between(0, 1) & position.notna()
    assert (frame.loc[inside & (position <= 0.25), "range_state"] == "Q1").all()
    assert (frame.loc[inside & (position > 0.75), "range_state"] == "Q4").all()


def test_the_adverse_leg_is_the_one_opposite_the_favourable_leg():
    """An audit swapped `mae_at_mfe` for the favourable leg and nothing noticed."""
    frame = panels.derived(_frame(n=900))
    rows = atlas.excursions(frame, 48)
    up, down = rows["up_excursion"], rows["down_excursion"]
    expected = np.where(up >= down, down, up)
    assert np.allclose(rows["mae_at_mfe"], expected)
    assert np.allclose(rows["mfe"], np.maximum(up, down))
    assert (rows["mfe"] >= rows["mae_at_mfe"] - 1e-9).all()


def test_the_panel_loaders_are_the_three_seen_routes():
    """`LOADERS` is a mutable module dict; an audit repointed it freely."""
    from scripts.research.exploratory_m15 import bars, momentum, supplemental

    assert set(panels.LOADERS) == set(PANELS)
    assert panels.LOADERS["momentum_2021_2023"][0] is momentum.load
    assert panels.LOADERS["supplemental_2023_2025"][0] is supplemental.load
    assert panels.LOADERS["development_2025"][0] is bars.load
    assert panels.panel_span("development_2025") == (
        bars.DEVELOPMENT_START_UTC,
        bars.DEVELOPMENT_END_UTC,
    )


def test_the_unconditioned_atlas_table_is_labelled_unregistered():
    """It is not one of the plan's 105 cells, and condition 4 consumes it.

    Renaming it once left the driver's lookup on the old name, the dict came out
    empty, and condition 4 silently failed for all 30 non-F1 cells because a
    missing key defaults to `insufficient_data`. The driver now raises instead,
    and this pins the name on both sides.
    """
    frame = panels.derived(_frame(n=1200))
    rows = atlas.atlas_for_panel(dict.fromkeys(panels.BLOCS["ALL"], frame), "test")
    tables = {row["table"] for row in rows}
    assert "overall_unregistered" in tables
    assert "overall" not in tables
    assert 'row["table"] == "overall_unregistered"' in inspect.getsource(driver)
    registered = sum(1 for row in rows if row["table"] in ("atr", "session"))
    #: 5 horizons x (3 ATR + 4 session states) x 3 blocs = the plan's 105
    assert registered == len(panels.ATLAS_HORIZONS) * (3 + 4) * len(panels.BLOCS) == 105


def test_2025_is_not_a_deciding_panel():
    """Roughly 1,200 configurations have been searched on it."""
    assert PANELS == ("momentum_2021_2023", "supplemental_2023_2025", "development_2025")
    assert DECIDING_PANELS == ("momentum_2021_2023", "supplemental_2023_2025")
    assert "development_2025" not in DECIDING_PANELS
    assert ledger.DEVELOPMENT_CONFIGURATIONS_APPROX >= 1000


# --------------------------------------------------------------------------
# the window
# --------------------------------------------------------------------------


@pytest.mark.parametrize("horizon", [16, 48, 192])
def test_the_excursion_window_matches_the_engines_hold_semantics(horizon):
    """Entry at `mid_c[t+1]`, path over `t+2 … t+H+1`, exit at `t+H+1`."""
    frame = panels.derived(_frame())
    rows = atlas.excursions(frame, horizon)
    close = frame["mid_c"].to_numpy()
    high = frame["mid_h"].to_numpy()
    low = frame["mid_l"].to_numpy()
    pip = frame["pip_size"].to_numpy()

    for t in (100, 250, 400):
        reference = close[t + 1]
        assert rows["up_excursion"].iloc[t] == pytest.approx(
            (high[t + 2 : t + horizon + 2].max() - reference) / pip[t]
        )
        assert rows["down_excursion"].iloc[t] == pytest.approx(
            (reference - low[t + 2 : t + horizon + 2].min()) / pip[t]
        )
        assert rows["terminal_move"].iloc[t] == pytest.approx(
            (close[t + horizon + 1] - reference) / pip[t]
        )


@pytest.mark.parametrize("horizon", [16, 48, 192])
def test_truncated_windows_are_dropped_rather_than_filled(horizon):
    """A short window understates every excursion, so it must not be reported."""
    frame = panels.derived(_frame())
    rows = atlas.excursions(frame, horizon)
    assert len(frame) - len(rows) == horizon + 1


def _expected_phase_totals(frame, horizon: int, rule: str) -> dict[int, float]:
    """What `_entries` must produce per phase, computed from the definition."""
    direction = screen.context_direction(frame, rule, horizon).to_numpy()
    close = frame["mid_c"].to_numpy()
    pip = frame["pip_size"].to_numpy()
    last = len(frame) - horizon - 2
    out: dict[int, float] = {}
    for phase in range(0, horizon, max(1, horizon // screen.N_PHASES))[: screen.N_PHASES]:
        total = 0.0
        for t in range(phase, last + 1, horizon):
            if direction[t] == 0 or not np.isfinite(direction[t]):
                continue
            total += direction[t] * (close[t + horizon + 1] - close[t + 1]) / pip[t]
        out[phase] = total
    return out


def test_the_screen_contribution_is_the_engines_gross_for_a_held_position():
    """Calls `screen._entries`. The previous version did not.

    An audit moved the entry to `mid_c[t]` — the same bar whose close sets
    `fade_past_move`'s direction, i.e. textbook same-bar leakage — and all 24
    tests passed, because this test retyped the formula inside itself instead of
    exercising the module it names.
    """
    frame = panels.derived(_frame(n=2000))
    horizon = 48
    entries = screen._entries(frame, horizon, pd.Series(True, index=frame.index), "fade_past_move")
    assert len(entries) > 0

    produced = entries.groupby("phase")["pips"].sum().to_dict()
    expected = _expected_phase_totals(frame, horizon, "fade_past_move")
    assert set(produced) == set(expected)
    for phase, value in expected.items():
        assert produced[phase] == pytest.approx(value, abs=1e-9), phase

    #: and one entry reconciles against the engine holding that same position
    direction = screen.context_direction(frame, "fade_past_move", horizon)
    close, pip = frame["mid_c"].to_numpy(), frame["pip_size"].to_numpy()
    #: `np.nan` is truthy, so a bare `if direction.iloc[t]` selects a NaN
    #: direction and the engine then earns nothing — which is how a first version
    #: of this assertion compared 0.0 against a real number.
    t = next(
        t
        for t in range(0, len(frame) - horizon - 2, horizon)
        if np.isfinite(direction.iloc[t])
        and direction.iloc[t] != 0
        #: in pips, not price units -- the fixture trades near 100.0, so a
        #: threshold on the raw difference is a threshold on 100 pips
        and abs(close[t + horizon + 1] - close[t + 1]) / pip[t] > 1.0
    )
    held = pd.Series(0.0, index=frame.index)
    held.iloc[t : t + horizon] = float(direction.iloc[t])
    earned = engine.evaluate(
        frame, held, name="cell", pair="USD_JPY", cost_multiplier=0.0
    ).net.to_numpy()
    assert earned[t + 1 : t + horizon + 1].sum() == pytest.approx(
        float(direction.iloc[t]) * (close[t + horizon + 1] - close[t + 1]) / pip[t], abs=1e-9
    )


def test_an_entry_never_uses_the_bar_that_set_its_own_direction():
    """The leakage the previous test could not see.

    `fade_past_move` reads `mid_c[t]`, so an entry priced at `mid_c[t]` would be
    trading on a bar it has already observed. Checked on the **single entry**
    where the two definitions differ most: summing a phase lets the difference
    cancel, which is how a first version of this test failed to distinguish them
    at all.
    """
    frame = panels.derived(_frame(n=3000))
    horizon = 48
    entries = screen._entries(frame, horizon, pd.Series(True, index=frame.index), "fade_past_move")
    direction = screen.context_direction(frame, "fade_past_move", horizon).to_numpy()
    close, pip = frame["mid_c"].to_numpy(), frame["pip_size"].to_numpy()
    day = frame["day"].to_numpy()
    last = len(frame) - horizon - 2

    best = None
    for phase in sorted(entries["phase"].unique()):
        rows = entries[entries["phase"] == phase]
        counts = rows["day"].value_counts()
        for t in range(int(phase), last + 1, horizon):
            if not np.isfinite(direction[t]) or direction[t] == 0:
                continue
            if counts.get(day[t], 0) != 1:
                continue
            correct = direction[t] * (close[t + horizon + 1] - close[t + 1]) / pip[t]
            same_bar = direction[t] * (close[t + horizon] - close[t]) / pip[t]
            gap = abs(correct - same_bar)
            if best is None or gap > best[0]:
                best = (gap, phase, t, correct, same_bar)
    assert best is not None, "no isolable entry in the fixture"
    gap, phase, t, correct, same_bar = best
    assert gap > 1.0, "the fixture cannot distinguish the two entry points"

    produced = float(
        entries[(entries["phase"] == phase) & (entries["day"] == day[t])]["pips"].iloc[0]
    )
    assert produced == pytest.approx(correct, abs=1e-9)
    assert produced != pytest.approx(same_bar, abs=1e-6), (
        "the entry is priced on the bar that set its direction"
    )


def test_every_state_column_is_backward_looking():
    """Recomputing on a truncated prefix must reproduce the prefix exactly.

    `d1_state` in particular: `higher_timeframe` already broadcasts its value to
    every bar, so a first version used `.diff()` and populated 173 bars of 16,760
    because it was comparing adjacent bars rather than adjacent 96-bar blocks.
    """
    frame = panels.derived(_frame())
    cut = 700
    prefix = panels.derived(_frame().iloc[:cut].copy())
    for column in ("atr_state", "vol_state", "d1_state", "range_state", "extreme_state"):
        assert (
            prefix[column].fillna("_").to_numpy() == frame[column].iloc[:cut].fillna("_").to_numpy()
        ).all(), column


def test_d1_state_is_populated_rather_than_almost_empty():
    frame = panels.derived(_frame(n=2000))
    filled = frame["d1_state"].notna().mean()
    assert filled > 0.7, f"d1_state is only {filled:.1%} populated"


def test_the_screen_takes_non_overlapping_entries_within_a_phase():
    frame = panels.derived(_frame(n=4000))
    horizon = 48
    mask = pd.Series(True, index=frame.index)
    entries = screen._entries(frame, horizon, mask, "fade_past_move")
    for _, group in entries.groupby("phase"):
        positions = frame.index.get_indexer(frame.index[frame["day"].isin(group["day"])])
        assert len(positions) > 0
    #: every phase's entries are `horizon` apart by construction
    assert entries["phase"].nunique() == screen.N_PHASES


# --------------------------------------------------------------------------
# the prohibition
# --------------------------------------------------------------------------


def _calls(module) -> set[str]:
    """Every `a.b(...)` call name in a module, from the AST rather than the text.

    A first version of this grepped the source for `engine.evaluate` and failed
    on `atlas.py`, whose docstring *describes* the engine's hold semantics. A
    substring search cannot tell prose from a call; the AST can.
    """
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                names.add(f"{target.value.id}.{target.attr}")
            elif isinstance(target, ast.Name):
                names.add(target.id)
    return names


def test_nothing_in_round_a_evaluates_a_strategy():
    """MFE and MAE are oracles. No Round A module may score a position."""
    for module in (atlas, screen, panels, driver):
        called = _calls(module)
        assert "engine.evaluate" not in called, f"{module.__name__} evaluates a strategy"


def test_the_screen_never_touches_an_excursion():
    """T2 conditions on backward state only; the oracle lives in `atlas` alone."""
    source = inspect.getsource(screen)
    for forbidden in ("mfe", "mae", "excursion", "atlas"):
        assert forbidden not in source.lower(), forbidden


def test_the_atlas_prohibition_is_recorded_where_it_could_be_violated():
    """Whitespace-normalised: the sentence wraps across lines in the source."""
    text = " ".join((inspect.getdoc(atlas) or "").split())
    assert "may never be a feature, a filter, a conditioning variable or an entry rule" in text
    assert "upper bound on capturable movement" in text


def test_round_a_contains_no_reader_and_no_span_bound():
    """ "Performs no read" is a property of the code, not a promise in a document.

    The package must not be able to open an archive: no path template, no file
    open, no span constant of its own. It loads parquet through the three routes
    that each carry their own guard.
    """
    for module in (atlas, screen, driver):
        source = inspect.getsource(module)
        assert ".jsonl" not in source
        assert "open(" not in source.replace("path.open", "")
    source = inspect.getsource(panels)
    assert ".jsonl" not in source
    assert "SOURCE_TEMPLATE" not in source


def test_the_panels_spans_come_from_each_routes_own_constants():
    """A panel cannot drift from the window its guard enforces."""
    from scripts.research.exploratory_m15 import momentum, supplemental

    assert panels.panel_span("momentum_2021_2023") == (
        momentum.MOMENTUM_START_UTC,
        momentum.MOMENTUM_END_UTC,
    )
    assert panels.panel_span("supplemental_2023_2025") == (
        supplemental.SUPPLEMENTAL_START_UTC,
        supplemental.SUPPLEMENTAL_END_UTC,
    )


# --------------------------------------------------------------------------
# the classification logic
# --------------------------------------------------------------------------


def test_a_cell_rich_in_one_period_only_is_not_promoted():
    """The three-period requirement is part of the definition, not a footnote."""
    rows = [
        {
            "table": "overall",
            "horizon": 96,
            "bloc": "ALL",
            "state": "all",
            "panel": panel,
            "observations": 1000,
            "median_mfe_over_median_cost": ratio,
            "p_mfe_gt_2x_cost": reach,
            "median_mfe": 10.0,
        }
        for panel, ratio, reach in (
            ("momentum_2021_2023", 9.0, 0.9),
            ("supplemental_2023_2025", 9.0, 0.9),
            ("development_2025", 1.2, 0.2),
        )
    ]
    assert atlas.classify(rows)[0]["verdict"] == "structurally_unattractive"


def test_sign_agreement_alone_does_not_qualify_a_cell():
    """Behaviour, not a grep. An audit forced condition 3 true and nothing saw it.

    Two cells: one agrees in sign but has a tiny effect, one clears every
    condition. Only the second may qualify.
    """
    verdicts = [
        {
            "table": "overall_unregistered",
            "horizon": 192,
            "bloc": "ALL",
            "state": "all",
            "verdict": "opportunity_rich",
        }
    ]

    def cell(name, effect, per_pair=50.0):
        rows = []
        for panel, sign in zip(PANELS, (1.0, 1.0, 1.0), strict=True):
            daily = pd.Series(
                [effect * sign] * 40,
                index=pd.date_range("2022-01-01", periods=40, freq="D", tz="UTC"),
            )
            rows.append(
                {
                    "panel": panel,
                    "family": "F2_vol",
                    "level": name,
                    "horizon": 192,
                    "entries": 500,
                    "mean_pips_per_entry": effect,
                    "effect_over_cost": effect,
                    "effective_observations": 400,
                    "effective_observations_per_pair": per_pair,
                    "effective_independent_pairs": 5.0,
                    "tails": panels.tail_contributions(daily),
                    "_daily": daily,
                }
            )
        return rows

    weak = cell("compression", 0.5)
    strong = cell("expansion", 4.0)
    out = {c["cell"]: c for c in driver.structural_candidates(weak + strong, verdicts)}
    assert out["F2_vol:compression:h192"]["checks"]["1_two_periods_agree_in_sign"]
    assert not out["F2_vol:compression:h192"]["qualifies"], "a 0.5x-cost effect must not qualify"
    assert out["F2_vol:expansion:h192"]["qualifies"]

    #: and the per-pair sample condition must be able to fail
    thin = driver.structural_candidates(cell("expansion", 4.0, per_pair=5.0), verdicts)
    assert not thin[0]["checks"]["5_sample_adequate"]
    assert thin[0]["checks"]["5_sample_adequate_pooled_reading"], "the pooled reading is inert"


def test_condition_five_uses_the_per_pair_count_the_plan_quantifies():
    """§5.2's only "30" is "the non-overlapping count per pair"."""
    source = inspect.getsource(driver.structural_candidates)
    assert 'row["effective_observations_per_pair"] >= screen.MIN_EFFECTIVE_OBSERVATIONS' in source
    frame = panels.derived(_frame(n=4000))
    cell = screen.screen_cell({"USD_JPY": frame}, family="F1_atr", level="high", horizon=48)
    assert cell["effective_observations_per_pair"] <= cell["effective_observations"]


def test_condition_six_is_the_plans_literal_rule_with_the_stricter_one_beside_it():
    source = inspect.getsource(driver.structural_candidates)
    assert "survives_registered_tail" in source and "survives_both_tails" in source
    registered = source.index('checks["6_survives_top10_day_removal"]')
    assert "survives_registered_tail" in source[registered : registered + 120]


def test_the_ledger_records_every_closed_family():
    ids = {entry["id"] for entry in ledger.LEDGER}
    assert len(ids) == len(ledger.LEDGER)
    closed = [e for e in ledger.LEDGER if e["status"].startswith("CLOSED")]
    assert len(closed) >= 7
    assert any("REVERSAL_FAILED" in e["result"] for e in ledger.LEDGER)
    assert any("MOMENTUM_UNRESOLVED" in e["result"] for e in ledger.LEDGER)
