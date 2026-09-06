"""Round B′'s nulls, its detector, and its pre-registration.

The round's whole claim rests on the nulls being what they say they are, so most
of this file measures their **contracts** rather than their output: N2 must leave
`|r_t|` untouched at every bar, or a real-minus-N2 difference is not attributable
to direction. The rest pins the detector's window semantics and causality, and
the numbers the plan fixed before it ran.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.
"""

from __future__ import annotations

import ast
import inspect

import numpy as np
import pandas as pd
import pytest

from scripts.research.round_b_prime import (
    ANCHOR_TIMEOUT,
    EXCURSION_SIGMAS,
    MONTH_BARS,
    OBSERVATION_WINDOW,
    RV_WINDOW,
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


# --------------------------------------------------------------------------
# the null contracts
# --------------------------------------------------------------------------


def test_n2_leaves_every_bars_magnitude_untouched(walk):
    """The property the round's attribution depends on.

    If `|r_t|` moved, volatility clustering would differ between the real and
    null sides and `real − N2` would no longer be about direction.
    """
    rng = np.random.default_rng(1)
    before = (walk["mid_c"].diff() / walk["pip_size"]).to_numpy()[1:]
    after = (nulls.n2_sign_flip(walk, rng)["mid_c"].diff() / walk["pip_size"]).to_numpy()[1:]
    assert np.allclose(np.abs(before), np.abs(after))
    assert not np.allclose(before, after), "N2 must actually change something"


@pytest.mark.parametrize("name", ["N1_iid", "N3_weekday"])
def test_the_other_nulls_do_not_preserve_per_bar_magnitude(name, walk):
    """Only N2 does. N1 and N3 destroy clustering as well, which is their job."""
    rng = np.random.default_rng(2)
    before = (walk["mid_c"].diff() / walk["pip_size"]).to_numpy()[1:]
    after = (nulls.NULLS[name](walk, rng)["mid_c"].diff() / walk["pip_size"]).to_numpy()[1:]
    assert np.allclose(np.sort(np.abs(before)), np.sort(np.abs(after))), "the marginal must survive"
    assert not np.allclose(np.abs(before), np.abs(after))


def test_n2_is_a_per_bar_flip_not_a_block_flip(walk):
    """The amendment `ccafebc` made, and the reason it was needed.

    A 5-day block flip leaves every path inside a block untouched, so the
    variance of a `q`-bar sum below the block length is unchanged and the null
    returns the real statistic exactly — measured at 0.8959 against 0.8959 on a
    synthetic AR(1). A per-bar flip must break `VR` away from the real value.
    """
    rng = np.random.default_rng(3)
    values = variance_ratio.sigma_normalised_returns(walk)
    steps = (walk["mid_c"].diff() / walk["pip_size"]).to_numpy()[1:]
    block = np.arange(len(steps)) // (5 * 96)
    blocked = nulls._rebuild(walk, steps * rng.choice((-1.0, 1.0), size=block.max() + 1)[block])
    per_bar = nulls.n2_sign_flip(walk, rng)

    real_12 = variance_ratio.variance_ratio(values, 12)
    blocked_12 = variance_ratio.variance_ratio(variance_ratio.sigma_normalised_returns(blocked), 12)
    per_bar_12 = variance_ratio.variance_ratio(variance_ratio.sigma_normalised_returns(per_bar), 12)

    #: measured: the block flip moves VR(12) by ~3e-06 and the per-bar flip by
    #: ~2e-02, four orders apart. The block version cannot reject anything.
    block_shift = abs(blocked_12 - real_12)
    per_bar_shift = abs(per_bar_12 - real_12)
    assert block_shift < 1e-4, "a block flip must be degenerate at q below the block length"
    assert per_bar_shift > 100 * block_shift, (
        "the per-bar flip must actually move the statistic the block flip cannot"
    )


def test_the_null_contracts_are_documented_and_match_the_code(walk):
    assert set(nulls.CONTRACTS) == set(nulls.NULLS)
    for name, contract in nulls.CONTRACTS.items():
        assert {"preserves", "destroys", "detects"} <= set(contract), name
    assert "independently per bar" in nulls.CONTRACTS["N2_sign_flip"]["destroys"]


def test_every_null_recovers_the_known_answer_on_a_random_walk():
    """A null that cannot return `VR = 1` on a walk is measuring itself."""
    sanity = variance_ratio.null_sanity(draws=12)
    for name in nulls.NULLS:
        for q in VR_HORIZONS:
            row = sanity[name][f"VR_{q}"]
            band = 4 * row["null_sd"] + 0.03
            assert abs(row["null_mean"] - 1.0) <= band, (name, q, row)


# --------------------------------------------------------------------------
# the variance ratio
# --------------------------------------------------------------------------


def test_variance_ratio_is_one_on_a_random_walk_and_below_one_on_ar1():
    rng = np.random.default_rng(5)
    n = 200_000
    noise = rng.normal(0, 1, n)
    walk = noise
    ar1 = noise[1:] - 0.10 * noise[:-1]
    for q in (2, 12, 96):
        assert variance_ratio.variance_ratio(walk, q) == pytest.approx(1.0, abs=0.03)
        assert variance_ratio.variance_ratio(ar1, q) < 0.95


def test_the_variance_ratio_denominator_is_about_zero_not_the_mean():
    """So a drift estimate cannot leak in and inflate the ratio."""
    source = inspect.getsource(variance_ratio.variance_ratio)
    assert "clean[:usable] ** 2" in source
    assert ".var(" not in source and "np.var" not in source


def test_sigma_normalisation_is_backward_looking(walk):
    full = variance_ratio.sigma_normalised_returns(walk)
    prefix = variance_ratio.sigma_normalised_returns(walk.iloc[:8000])
    assert np.allclose(full[:8000], prefix, equal_nan=True)


# --------------------------------------------------------------------------
# the anchor detector
# --------------------------------------------------------------------------


def test_the_observation_window_is_scale_matched_to_the_excursion(walk):
    """The amendment `1b1a3ae`: a flat 480 is 37x a median 1.5-sigma excursion."""
    frame = retrace.find_anchors(walk, 1.5)
    assert len(frame) > 20
    expected = np.minimum(retrace.WINDOW_MULTIPLE * frame["bars_to_anchor"], OBSERVATION_WINDOW)
    assert (frame["observation_bars"] == expected).all()
    assert retrace.WINDOW_MULTIPLE == 4


def test_the_detector_is_causal(walk):
    """Perturbing the future must not move an earlier anchor or its geometry."""
    cut = 15_000
    perturbed = walk.copy()
    perturbed.loc[perturbed.index[cut] :, ["mid_c", "mid_h", "mid_l"]] += 5.0
    limit = cut - OBSERVATION_WINDOW - 2
    first = retrace.find_anchors(walk, 2.0)
    second = retrace.find_anchors(perturbed, 2.0)
    a = first[first["anchor"] < limit].reset_index(drop=True)
    b = second[second["anchor"] < limit].reset_index(drop=True)
    assert len(a) > 5
    assert a["anchor"].equals(b["anchor"])
    assert np.allclose(a["max_retrace_fraction"], b["max_retrace_fraction"])


def test_anchors_do_not_share_a_reference(walk):
    frame = retrace.find_anchors(walk, 1.5)
    assert frame["anchor"].is_monotonic_increasing
    assert frame["anchor"].is_unique


def test_the_retrace_measurement_starts_strictly_after_the_anchor(walk):
    """The window is `anchor+1 … anchor+span`, never the anchor bar itself."""
    source = inspect.getsource(retrace.find_anchors)
    assert "slice(anchor + 1, anchor + 1 + span)" in source


def test_trailing_sigma_is_backward_looking(walk):
    full = retrace.trailing_sigma(walk)
    prefix = retrace.trailing_sigma(walk.iloc[:9000])
    assert np.allclose(full[:9000], prefix, equal_nan=True)


def test_the_htf_context_is_two_variables_with_two_states_each(walk):
    context = retrace.htf_context(walk)
    assert set(context) == {"htf_trend", "htf_location"}
    assert set(np.unique(context["htf_trend"])) <= {"aligned", "mixed"}
    assert set(np.unique(context["htf_location"])) <= {"outer", "middle"}


# --------------------------------------------------------------------------
# the pre-registration
# --------------------------------------------------------------------------


def test_the_registered_constants_are_the_plans():
    assert VR_HORIZONS == (2, 4, 12, 48, 96, 192, 480)
    assert EXCURSION_SIGMAS == (1.5, 2.0, 3.0)
    assert RV_WINDOW == 480
    assert OBSERVATION_WINDOW == 480
    assert ANCHOR_TIMEOUT == 960
    assert MONTH_BARS == 21 * 96
    assert TSMOM_LOOKBACKS == (1, 2, 3)
    assert TSMOM_HOLDS == (1, 3)


def test_the_family_is_twenty_eight_cells():
    """7 variance-ratio horizons + 3 x 5 retrace cells + 6 monthly cells."""
    b1 = len(VR_HORIZONS)
    b2 = len(EXCURSION_SIGMAS) * (1 + 2 * 2)
    b4 = len(TSMOM_LOOKBACKS) * len(TSMOM_HOLDS)
    assert (b1, b2, b4) == (7, 15, 6)
    assert b1 + b2 + b4 == 28


def test_the_economic_floor_is_applied_to_the_retrace_verdict():
    from scripts.research.round_b_prime import RETRACE_DIFFERENCE_FLOOR

    assert RETRACE_DIFFERENCE_FLOOR == 0.05
    source = inspect.getsource(driver._retrace_verdict)
    assert "above_economic_floor" in source
    assert "RETRACE_DIFFERENCE_FLOOR" in source


def test_the_monthly_screen_is_six_cells_and_no_more(walk):
    cells = [(lookback, hold) for lookback in TSMOM_LOOKBACKS for hold in TSMOM_HOLDS]
    assert len(cells) == 6
    source = inspect.getsource(monthly.screen)
    assert "TSMOM_LOOKBACKS" in source and "TSMOM_HOLDS" in source


def test_the_monthly_signal_is_causal(walk):
    full = monthly.signal(walk, lookback=1, hold=1, phase=0)
    prefix = monthly.signal(walk.iloc[:9000], lookback=1, hold=1, phase=0)
    assert np.allclose(full.to_numpy()[:9000], prefix.to_numpy())


def test_2025_cannot_decide_anything():
    from scripts.research.round_a import DECIDING_PANELS

    assert "development_2025" not in DECIDING_PANELS
    for name in ("_vr_verdict", "_retrace_verdict", "_monthly_verdict"):
        source = inspect.getsource(getattr(driver, name))
        assert "DECIDING_PANELS" in source, name


# --------------------------------------------------------------------------
# the diagnostics, and what they may not do
# --------------------------------------------------------------------------


def test_the_post_hoc_module_is_labelled_and_kept_out_of_the_verdicts():
    assert diagnostics.CLASSIFICATION == "POST_HOC_DIAGNOSTIC_ONLY"
    for name in ("_vr_verdict", "_retrace_verdict", "_monthly_verdict", "_htf_diagnostic"):
        source = inspect.getsource(getattr(driver, name))
        assert "diagnostics" not in source, f"{name} must not consult a post-hoc statistic"


def test_the_coarse_variance_ratio_aggregates_before_it_measures(walk):
    """The test that separates a one-bar effect from a longer-range one."""
    rng = np.random.default_rng(7)
    steps = rng.normal(0, 1, 120_000)
    ma1 = steps[1:] - 0.15 * steps[:-1]
    close = np.concatenate([[100.0], 100.0 + np.cumsum(ma1 * 0.01)])
    frame = nulls.random_walk_frame(len(close), rng)
    frame["mid_c"] = close
    assert diagnostics.coarse_variance_ratio(frame, 1, 12) < 0.95
    assert diagnostics.coarse_variance_ratio(frame, 12, 12) == pytest.approx(1.0, abs=0.06)


def test_harvestability_reports_the_achievable_bound_beside_the_generous_one(walk):
    #: `roundtrip_cost` is added by `round_a.panels.derived`, not by the walk
    #: generator, so the fixture supplies it here rather than the module gaining
    #: a fallback that would hide a missing column on a real panel.
    frame = walk.copy()
    frame["roundtrip_cost"] = frame["spread_close_pips"] + 0.5
    result = diagnostics.harvestability({"A": frame}, horizons=(1, 12))
    for q in ("1", "12"):
        row = result[q]
        assert "generous_ic_upper_bound_sqrt_deficit" in row
        assert "ma1_block_autocorrelation" in row
        assert "break_even_ic" in row
    #: the MA(1) block figure must shrink with the horizon; the generous one need not
    assert abs(result["12"]["ma1_block_autocorrelation"]) < abs(
        result["1"]["ma1_block_autocorrelation"]
    )


# --------------------------------------------------------------------------
# the data boundary
# --------------------------------------------------------------------------


def _calls(module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                names.add(f"{target.value.id}.{target.attr}")
            elif isinstance(target, ast.Name):
                names.add(target.id)
    return names


@pytest.mark.parametrize("module", [variance_ratio, retrace, monthly, nulls, diagnostics])
def test_round_b_prime_contains_no_reader(module):
    """It loads parquet through `round_a.panels`; it cannot open an archive."""
    source = inspect.getsource(module)
    assert ".jsonl" not in source
    assert "read_m1" not in _calls(module)
    assert "build_cache" not in _calls(module)


def test_the_volume_inventory_performs_no_content_read():
    """It reads source files and the manifest. It may never open an archive."""
    #: The source-text half of this test was withdrawn. It asserted that the
    #: string ".jsonl" does not appear in the module, which stopped being a
    #: statement about behaviour the moment the module had to *name* the
    #: content suffixes in order to detect a read of one. The behavioural
    #: version, including a tripwire that opens a real archive file and checks
    #: the flag flips, is in `test_round_b_prime_hardening.py`.
    result = volume_inventory.inventory()
    assert result["content_read_performed"] is False
    assert result["reader"]["volume_in_price_keys"] is False
    assert result["recovery"]["requires_new_span"] is False
    assert result["recovery"]["requires_new_content_read"] is True
