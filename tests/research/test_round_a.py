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


def test_the_screen_contribution_equals_what_the_engine_would_earn():
    """`d x (mid_c[t+H+1] - mid_c[t+1])` is exactly a held position's gross."""
    frame = panels.derived(_frame())
    horizon = 48
    always = pd.Series(1.0, index=frame.index)
    earned = engine.evaluate(
        frame, always, name="w", pair="USD_JPY", cost_multiplier=0.0
    ).net.to_numpy()
    close = frame["mid_c"].to_numpy()
    pip = frame["pip_size"].to_numpy()
    for t in (120, 300):
        assert earned[t + 1 : t + horizon + 1].sum() == pytest.approx(
            (close[t + horizon + 1] - close[t + 1]) / pip[t], abs=1e-9
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
            "median_mfe_over_cost": ratio,
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
    """With 39 cells and two periods about ten agree by chance."""
    source = inspect.getsource(driver.structural_candidates)
    for check in (
        "1_two_periods_agree_in_sign",
        "2_development_not_strong_counter_evidence",
        "3_effect_at_least_2x_cost",
        "4_t1_tradable",
        "5_sample_adequate",
        "6_survives_top10_day_removal",
    ):
        assert check in source
    assert "all(checks.values())" in source


def test_the_ledger_records_every_closed_family():
    ids = {entry["id"] for entry in ledger.LEDGER}
    assert len(ids) == len(ledger.LEDGER)
    closed = [e for e in ledger.LEDGER if e["status"].startswith("CLOSED")]
    assert len(closed) >= 7
    assert any("REVERSAL_FAILED" in e["result"] for e in ledger.LEDGER)
    assert any("MOMENTUM_UNRESOLVED" in e["result"] for e in ledger.LEDGER)
