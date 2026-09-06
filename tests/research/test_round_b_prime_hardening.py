"""Round B′ — the tests that had to exist after two review roles read it.

An independent review role mutated the round's source 23 ways and **14 of the
mutations survived** the suite as it stood, including a null that flipped 5% of
bars instead of 50% — the round's single load-bearing object. The cause was
uniform: eight of the original tests assert on **source text or docstrings**,
and one imported `DECIDING_PANELS` from `round_a` rather than from the driver,
so it checked a different object than the code used.

Everything here asserts on behaviour, and each test names the mutation it kills.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.research.round_b_prime import (
    MONTH_BARS,
    TSMOM_HOLDS,
    TSMOM_LOOKBACKS,
    VR_HORIZONS,
    diagnostics,
    driver,
    monthly,
    nulls,
    retrace,
    variance_ratio,
    volume_inventory,
)


@pytest.fixture(scope="module")
def walk() -> pd.DataFrame:
    return nulls.random_walk_frame(30_000, np.random.default_rng(11))


def _spike(frame: pd.DataFrame, bar: int, size: float = 500.0) -> pd.DataFrame:
    """The same frame with every bar from `bar` onward displaced."""
    out = frame.copy()
    pip = float(out["pip_size"].iloc[0])
    shift = np.where(np.arange(len(out)) >= bar, size * pip, 0.0)
    for column in ("mid_o", "mid_h", "mid_l", "mid_c"):
        out[column] = out[column].to_numpy() + shift
    return out


# ----------------------------------------------------------------- causality


def test_the_sigma_normalisation_denominator_ignores_its_own_bar(walk: pd.DataFrame) -> None:
    """Kills a dropped `.shift(1)` in `sigma_normalised_returns`.

    Prefix stability cannot catch this — an unshifted `rolling().std()` is
    prefix-stable too, which is why the original test passes with the shift
    removed. Scaling one bar's return is the discriminator: with the shift, that
    bar's magnitude is absent from its own denominator, so the normalised value
    scales by **exactly** the same factor. Without it, the denominator grows too
    and the factor comes out smaller.
    """
    bar = 5_000
    scaled = walk.copy()
    pip = float(scaled["pip_size"].iloc[0])
    close = scaled["mid_c"].to_numpy().copy()
    extra = 9.0 * (close[bar] - close[bar - 1])
    close[bar:] += extra
    scaled["mid_c"] = close
    for column in ("mid_o", "mid_h", "mid_l"):
        scaled[column] = scaled[column].to_numpy() + np.where(
            np.arange(len(scaled)) >= bar, extra, 0.0
        )
    #: the probe must actually be a ten-fold change in that bar's return, and
    #: the reference value must be a usable number, or the ratio below is inert
    assert (scaled["mid_c"].to_numpy()[bar] - scaled["mid_c"].to_numpy()[bar - 1]) == pytest.approx(
        10.0 * (walk["mid_c"].to_numpy()[bar] - walk["mid_c"].to_numpy()[bar - 1]), rel=1e-9
    )
    assert pip > 0

    base = np.asarray(variance_ratio.sigma_normalised_returns(walk), dtype=float)
    after = np.asarray(variance_ratio.sigma_normalised_returns(scaled), dtype=float)
    assert after[bar] / base[bar] == pytest.approx(10.0, abs=1e-6), (
        "the bar's own magnitude entered its own denominator, so the "
        "normalisation is not strictly backward-looking"
    )


def test_trailing_sigma_cannot_see_its_own_bar(walk: pd.DataFrame) -> None:
    """Kills a dropped `.shift(1)` in `retrace.trailing_sigma`.

    With the shift, the estimate *at* a perturbed bar is built from returns up
    to the previous one and cannot move; the first index that moves is the one
    after it.
    """
    bar = 5_000
    base = np.asarray(retrace.trailing_sigma(walk), dtype=float)
    after = np.asarray(retrace.trailing_sigma(_spike(walk, bar)), dtype=float)
    assert np.allclose(base[bar - 3 : bar + 1], after[bar - 3 : bar + 1], equal_nan=True), (
        "trailing_sigma moved at the perturbed bar, so it is not strictly backward-looking"
    )
    assert not np.allclose(base[bar + 1 : bar + 40], after[bar + 1 : bar + 40], equal_nan=True), (
        "trailing_sigma did not react to the perturbation at all — the test is inert"
    )


def test_the_htf_range_cannot_see_its_own_bar(walk: pd.DataFrame) -> None:
    """Kills a dropped `.shift(1)` on the HTF rolling extremes.

    Tested on the numeric position rather than on the label. A bar that moves a
    rolling extreme is itself at that extreme, so `htf_location` buckets it
    "outer" whether or not the extreme includes it — the label cannot separate
    the two, and a probe written against it passes with the shift removed.
    """
    bar = 8_000
    base = np.asarray(retrace.htf_range_position(walk), dtype=float)
    #: probed in both directions: an upward spike only exercises the rolling
    #: max, and the shift on the rolling **min** survived a one-sided probe
    for size, bound, describe in ((5_000.0, 1.5, "above"), (-5_000.0, -0.5, "below")):
        after = np.asarray(retrace.htf_range_position(_spike(walk, bar, size=size)), dtype=float)
        assert np.allclose(base[bar - 3 : bar], after[bar - 3 : bar], equal_nan=True), (
            f"the HTF range moved before the bar perturbed {describe}"
        )
        #: with the shift, the denominator at `bar` is the range up to `bar − 1`,
        #: so the perturbed close divided by an untouched range lands far outside
        #: [0, 1]; without it, the close sets the extreme and the position is
        #: pinned to exactly 1 or 0
        outside = after[bar] > bound if size > 0 else after[bar] < bound
        assert outside, (
            f"the close perturbed {describe} entered its own trailing range "
            f"(position {after[bar]:.3f}), so the extremes are not strictly "
            "backward-looking"
        )


def test_the_anchor_scale_is_the_reference_bars_sigma(monkeypatch) -> None:
    """Plan §5.2: sigma is fixed at the reference bar and never re-estimated.

    Pinned with a sigma that ramps, so re-reading it even a few bars later
    changes the threshold and the recorded excursion by a measurable amount.
    """
    n = 6_000
    frame = nulls.random_walk_frame(n, np.random.default_rng(4))
    #: `trailing_sigma` is in **price** units, and the walk moves about one pip
    #: a bar, so the ramp has to live on that scale for anchors to form at all
    pip = float(frame["pip_size"].iloc[0])
    ramp = pd.Series(np.linspace(0.4 * pip, 1.6 * pip, n), index=frame.index)
    monkeypatch.setattr(retrace, "trailing_sigma", lambda _frame: ramp)

    anchors = retrace.find_anchors(frame, 1.5)
    assert len(anchors) >= 10, "the probe produced too few anchors — the test is inert"

    close = frame["mid_c"].to_numpy()
    for row in anchors.head(40).itertuples():
        anchor = int(row.anchor)
        reference = anchor - int(row.bars_to_anchor)
        expected = abs(close[anchor] - close[reference]) / float(ramp.iloc[reference])
        assert float(row.excursion_sigma) == pytest.approx(expected, rel=1e-6), (
            "the excursion was scaled by a sigma other than the reference bar's"
        )


def _sign_shape_coupling(frame: pd.DataFrame) -> float:
    steps = (frame["mid_c"].diff() / frame["pip_size"]).to_numpy()[1:]
    asym = ((frame["mid_h"] - frame["mid_c"]) - (frame["mid_c"] - frame["mid_l"])).to_numpy()[1:]
    keep = np.isfinite(steps) & np.isfinite(asym) & (steps != 0)
    return float(np.corrcoef(np.sign(steps[keep]), asym[keep])[0, 1])


def test_every_null_keeps_each_bars_shape_coherent_with_its_direction(
    walk: pd.DataFrame,
) -> None:
    """Kills a null that re-attaches a real bar's high and low to a flipped return.

    On real M15 data `corr(sign r_t, (h−c) − (c−l)) = −0.57`: an up bar closes
    near its high. A null that flips the sign and keeps the offsets builds bars
    that close **down** with the close pinned to the high, and `find_anchors`
    reads exactly those two columns for both the retrace depth and the
    continuation. The first version of this round did that, and its only
    surviving B′-2 cell reversed sign once it stopped.
    """
    real = _sign_shape_coupling(walk)
    assert real < -0.3, "the fixture has no sign/shape coupling, so this test is inert"
    real_range = np.sort((walk["mid_h"] - walk["mid_l"]).to_numpy()[1:])
    for name, null in nulls.NULLS.items():
        drawn = null(walk, np.random.default_rng(3))
        assert _sign_shape_coupling(drawn) == pytest.approx(real, abs=0.05), (
            f"{name} broke the coupling between a bar's sign and its own shape"
        )
        assert np.allclose(real_range, np.sort((drawn["mid_h"] - drawn["mid_l"]).to_numpy()[1:])), (
            f"{name} did not preserve the multiset of bar ranges"
        )


def test_the_shuffling_nulls_destroy_the_serial_dependence_of_the_bar_range(
    walk: pd.DataFrame,
) -> None:
    """N1 and N3 claim to destroy *all* serial dependence, the bar range included.

    They did not: `_rebuild` re-attached each bar's own offsets in place, so the
    intrabar range came through a shuffle byte-identical.
    """
    shaped = walk.copy()
    pip = float(shaped["pip_size"].iloc[0])
    span = (np.abs(np.sin(np.arange(len(shaped)) / 400.0)) + 0.2) * pip
    shaped["mid_h"] = shaped["mid_c"] + span
    shaped["mid_l"] = shaped["mid_c"] - span

    def autocorrelation(frame: pd.DataFrame) -> float:
        values = (frame["mid_h"] - frame["mid_l"]).to_numpy()[1:]
        return float(np.corrcoef(values[:-1], values[1:])[0, 1])

    assert autocorrelation(shaped) > 0.9, "the fixture range has no dependence to destroy"
    for name in ("N1_iid", "N3_weekday"):
        drawn = nulls.NULLS[name](shaped, np.random.default_rng(5))
        assert abs(autocorrelation(drawn)) < 0.3, (
            f"{name} left the bar range's serial dependence intact"
        )


# -------------------------------------------------------------- kill conditions


def _geometry(difference: float) -> dict[str, Any]:
    cell = {
        "real": {"anchors": 5000},
        "null": {
            "median_retrace_fraction": {
                "real_minus_null": difference,
                "studentized": -9.0,
            },
            "median_retrace_fraction_excluding_top_10_days": {
                "real_minus_null": difference,
                "studentized": -9.0,
            },
        },
    }
    return {panel: {"1.5": cell} for panel in driver.DECIDING_PANELS}


def test_the_retrace_verdict_kills_a_statistically_strong_but_tiny_difference() -> None:
    """Kills the removal of the economic floor, behaviourally rather than by grep."""
    assert driver._retrace_verdict(_geometry(-0.20))["surviving_thresholds"] == [1.5]
    tiny = driver._retrace_verdict(_geometry(-0.001))
    assert tiny["surviving_thresholds"] == []
    assert tiny["kill_condition_met"] is True


def test_the_retrace_verdict_kills_a_cell_carried_by_ten_days() -> None:
    """Plan §5.6 clause 3, which the first version of this round never ran.

    The day trim was applied to the real median alone and never to
    `real − null`, so it could not kill anything.
    """
    geometry = _geometry(-0.20)
    for panel in geometry:
        cell = geometry[panel]["1.5"]["null"]
        cell["median_retrace_fraction_excluding_top_10_days"] = {
            "real_minus_null": +0.11,
            "studentized": 1.4,
        }
    verdict = driver._retrace_verdict(geometry)
    assert verdict["per_threshold"][1.5]["clause_3_day_trim_holds"] is False
    assert verdict["surviving_thresholds"] == []


def test_the_retrace_verdict_kills_a_cell_confined_to_one_bloc() -> None:
    """Plan §5.6 clause 4. No JPY/non-JPY split existed for B′-2 at all."""
    blocs = {
        "1.5": {
            panel: {
                "JPY": {"median_retrace_fraction": {"real_minus_null": -0.30}},
                "non_JPY": {"median_retrace_fraction": {"real_minus_null": +0.02}},
            }
            for panel in driver.DECIDING_PANELS
        }
    }
    verdict = driver._retrace_verdict(_geometry(-0.20), blocs)
    assert verdict["per_threshold"][1.5]["clause_4_both_blocs_same_sign"] is False
    assert verdict["surviving_thresholds"] == []


def _vr_input(z: float) -> dict[str, Any]:
    return {
        panel: {
            "real": dict.fromkeys(VR_HORIZONS, 0.95),
            "N2_sign_flip": {
                "per_horizon": {
                    q: {"real_minus_null": -0.05, "studentized": z} for q in VR_HORIZONS
                }
            },
        }
        for panel in driver.DECIDING_PANELS
    }


def test_the_variance_ratio_verdict_requires_a_studentized_two() -> None:
    """Kills a loosened `|z|` threshold in B′-1's kill condition."""
    assert driver._vr_verdict(_vr_input(-9.0))["kill_condition_met"] is False
    assert driver._vr_verdict(_vr_input(-1.0))["kill_condition_met"] is True


def test_no_verdict_function_can_reach_the_post_hoc_diagnostics(monkeypatch) -> None:
    """Kills a verdict that consults `diagnostics`, including through an alias.

    The original test looks for the *name* in the source; this removes the
    module's callables outright, so any route to them — aliased import,
    attribute lookup, `getattr` — raises instead of quietly returning a number.
    """

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("a verdict function reached a POST_HOC_DIAGNOSTIC_ONLY statistic")

    for name in diagnostics.__all__:
        if callable(getattr(diagnostics, name, None)):
            monkeypatch.setattr(diagnostics, name, forbidden)

    assert driver._vr_verdict(_vr_input(-9.0))["kill_condition_met"] is False
    assert driver._retrace_verdict(_geometry(-0.20))["surviving_thresholds"] == [1.5]


def test_the_deciding_panels_are_read_from_the_driver_itself() -> None:
    """Kills a driver-local rebinding that lets 2025 decide.

    The original test imported `DECIDING_PANELS` from `round_a`, so a rebinding
    inside `driver` was invisible to it — the object the test checked was not
    the object the code used.
    """
    assert driver.DECIDING_PANELS == ("momentum_2021_2023", "supplemental_2023_2025")
    assert "development_2025" not in driver.DECIDING_PANELS
    assert "development_2025" in driver.PANELS


# ----------------------------------------------------------------- the driver


def _written_by_main() -> list[str]:
    tree = ast.parse(inspect.getsource(driver.main))
    return [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "write"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]


def test_the_null_sanity_check_is_the_first_thing_the_driver_writes() -> None:
    """Kills a reordering that lets a real comparison precede the sanity check."""
    written = _written_by_main()
    assert written[0] == "b1_null_sanity", f"the driver writes {written[0]} first"


def test_the_primary_retrace_null_is_n2_everywhere_it_decides() -> None:
    """Kills a silent swap of B′-2's primary null to the secondary one."""
    assert inspect.signature(retrace.against_null).parameters["null_name"].default == "N2_sign_flip"
    tree = ast.parse(inspect.getsource(driver.main))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "against_null"
    ]
    overrides = [
        keyword.value.value
        for node in calls
        for keyword in node.keywords
        if keyword.arg == "null_name" and isinstance(keyword.value, ast.Constant)
    ]
    #: exactly one call names a null — the registered secondary. Checking only
    #: the *set* of names was not enough: moving the override onto the primary
    #: call leaves the set unchanged, which is the swap this test exists to
    #: catch.
    assert overrides == ["N1_iid"], f"B′-2's null overrides are {overrides}"
    assert len(calls) > len(overrides), "every against_null call names a null; none is the primary"


def test_the_registered_secondary_null_is_actually_run() -> None:
    """Plan §5.4 registers an IID secondary null. It was registered and not run."""
    assert "b2_secondary_null" in _written_by_main()


def test_the_classification_follows_the_pre_registered_rule() -> None:
    """The case is derived from the four verdicts, not chosen in prose.

    The first version of this round recorded Case C — "all three empty" — while
    its own B′-1 and B′-2 kill conditions were both unmet. Two review roles
    found it independently. Economic materiality may govern the *consequence*;
    it may never choose the case.
    """

    def verdicts(b1_empty: bool, b2_empty: bool, b4_stable: bool) -> dict[str, Any]:
        return {
            "b1": {"kill_condition_met": b1_empty, "stable_horizons": []},
            "b2": {"kill_condition_met": b2_empty, "surviving_thresholds": []},
            "b4": {"kill_condition_met": not b4_stable},
        }

    assert driver._classification(verdicts(False, True, False))["case"] == "A"
    assert driver._classification(verdicts(True, False, False))["case"] == "A"
    assert driver._classification(verdicts(False, False, True))["case"] == "A"
    assert driver._classification(verdicts(True, True, True))["case"] == "B"
    empty = driver._classification(verdicts(True, True, False))
    assert empty["case"] == "C"
    assert empty["token"] == "PRICE_ONLY_PATH_STRUCTURE_SCREEN_NEGATIVE"
    assert empty["economic_materiality_is_not_an_input"] is True


# ------------------------------------------------------------------ B′-4, B′-VOL


def _monthly_panel(walk: pd.DataFrame) -> dict[str, pd.DataFrame]:
    frame = walk.iloc[: MONTH_BARS * 8].copy()
    frame["roundtrip_cost"] = 2.5
    return {"EUR_USD": frame, "USD_CHF": frame}


def test_the_monthly_family_is_six_cells_when_it_runs(walk: pd.DataFrame) -> None:
    """Kills a seventh cell added to the screen, behaviourally."""
    rows = monthly.screen(_monthly_panel(walk))
    assert len(rows) == 6
    assert {(row["lookback_months"], row["hold_months"]) for row in rows} == {
        (lookback, hold) for lookback in TSMOM_LOOKBACKS for hold in TSMOM_HOLDS
    }


def test_the_monthly_evaluation_charges_a_cost(walk: pd.DataFrame) -> None:
    """Kills a zeroed cost multiplier."""
    row = monthly.evaluate_cell(_monthly_panel(walk), lookback=1, hold=1)
    assert row["cost_pips_per_pair"] > 0
    assert row["net_pips_per_pair"] < row["gross_pips_per_pair"]


def test_the_volume_inventory_detects_a_content_read(monkeypatch) -> None:
    """Kills a hard-coded `content_read_performed: False`.

    A review role mutated the module to open an archive `.jsonl` and read a line
    from it, and every test still passed, because the field was a literal. It is
    now a measurement of the call, so the tripwire has to fire.
    """
    clean = volume_inventory.inventory()
    assert clean["content_read_performed"] is False
    assert clean["market_content_paths_opened"] == []

    target = next(iter(sorted(Path("data").glob("*.jsonl"))), None)
    if target is None:  # pragma: no cover - the archive is not always present
        pytest.skip("no local market-data file to probe with")
    inner = volume_inventory._inventory

    def leaks() -> dict[str, Any]:
        result = inner()
        with open(target) as handle:
            handle.readline()
        return result

    monkeypatch.setattr(volume_inventory, "_inventory", leaks)
    assert volume_inventory.inventory()["content_read_performed"] is True
