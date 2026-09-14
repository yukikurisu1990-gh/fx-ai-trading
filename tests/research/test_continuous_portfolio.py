"""Track 1: construction, cost accounting, leakage and adjudication — on synthetic data.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Nothing in this file fits a model to market data or computes a real return. The
book, the model and the verdict are exercised on synthetic panels whose answer
is known, and the real corpus is touched only to check fold geometry.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.research.continuous_portfolio import (
    CASE_A,
    CASE_B,
    CASE_C,
    CHARGED_ONE_WAY_BP,
    CHARGED_ROUTING_RATIO,
    construction,
    economic_band,
    evaluation,
    model,
    prereg,
)
from scripts.research.feasibility.inventory import BASKET_ROUNDTRIP_BP
from scripts.research.model_learning import PAIRS_20, SEEN_SPANS

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scripts/research/continuous_portfolio"
C = list(construction.CURRENCIES)


def _synthetic_excess(days: int = 900, seed: int = 1, scale: float = 0.004) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    raw = rng.normal(0.0, scale, size=(days, len(C)))
    frame = pd.DataFrame(raw, index=pd.bdate_range("2021-05-03", periods=days), columns=C)
    return frame.sub(frame.mean(axis=1), axis=0)


# ------------------------------------------------------------------ units
class TestUnits:
    def test_the_charge_is_the_basket_round_trip_split_in_two(self) -> None:
        assert pytest.approx(1.32, abs=1e-3) == CHARGED_ROUTING_RATIO
        assert pytest.approx(BASKET_ROUNDTRIP_BP / 2) == CHARGED_ONE_WAY_BP

    def test_opening_and_closing_a_gross_one_book_costs_one_basket_round_trip(self) -> None:
        x = np.array([0.25, 0.25, -0.25, -0.25, 0, 0, 0, 0])
        opened = construction.charged_cost(x - 0)
        closed = construction.charged_cost(0 - x)
        assert (opened + closed) * 10_000 == pytest.approx(BASKET_ROUNDTRIP_BP)

    def test_a_small_target_change_is_charged_as_a_small_trade_not_a_round_trip(self) -> None:
        """⭐ The ruling's §6/§51: prediction frequency is not trading frequency."""
        yesterday = np.array([0.20, 0.10, -0.20, -0.10, 0, 0, 0, 0])
        today = np.array([0.23, 0.10, -0.23, -0.10, 0, 0, 0, 0])
        daily_update = construction.charged_cost(today - yesterday) * 10_000
        round_trip = (
            construction.charged_cost(yesterday) * 10_000 * 2
            + construction.charged_cost(today) * 10_000
        )
        assert daily_update == pytest.approx(0.06 * CHARGED_ONE_WAY_BP)
        assert daily_update < round_trip / 20

    def test_the_pnl_identity_between_currency_weights_and_the_pair_book(self) -> None:
        """`x . r_currency == (split_map @ x) . r_pair` when `sum x == 0`."""
        rng = np.random.default_rng(3)
        pair_returns = rng.normal(0, 0.005, size=len(PAIRS_20))
        matrix = construction.split_map()
        signed = np.zeros((len(C),))
        counts = np.zeros(len(C))
        for p, pair in enumerate(PAIRS_20):
            base, quote = pair.split("_")
            signed[C.index(base)] += pair_returns[p]
            signed[C.index(quote)] -= pair_returns[p]
            counts[C.index(base)] += 1
            counts[C.index(quote)] += 1
        currency_return = signed / counts
        excess = currency_return - currency_return.mean()
        x = rng.normal(size=len(C))
        x -= x.mean()
        assert x @ excess == pytest.approx((matrix @ x) @ pair_returns, abs=1e-12)

    def test_the_faithful_cost_is_below_the_charge_for_a_diversified_trade(self) -> None:
        rng = np.random.default_rng(4)
        matrix = construction.split_map()
        faithful, charged = 0.0, 0.0
        for _ in range(500):
            delta = rng.normal(size=len(C))
            delta -= delta.mean()
            faithful += construction.implementation_cost(delta, matrix)
            charged += construction.charged_cost(delta)
        assert faithful < charged

    def test_economic_bands(self) -> None:
        assert economic_band(-0.2) == "economically_weak"
        assert economic_band(0.29) == "economically_weak"
        assert economic_band(0.3) == "marginal"
        assert economic_band(0.5) == "potentially_useful"
        assert economic_band(0.81) == "strong_development_candidate"


# ------------------------------------------------------------ construction
class TestConstruction:
    def test_neutralisation_is_orthogonal_and_sum_zero(self) -> None:
        rng = np.random.default_rng(5)
        window = rng.normal(size=(120, len(C)))
        factor = construction.leading_factor(window)
        scores = construction.neutralize(rng.normal(size=len(C)), factor)
        assert scores.sum() == pytest.approx(0, abs=1e-12)
        assert scores @ factor == pytest.approx(0, abs=1e-12)
        assert np.linalg.norm(factor) == pytest.approx(1.0)

    @pytest.mark.parametrize("seed", range(20))
    def test_capped_weights_respect_every_constraint(self, seed: int) -> None:
        rng = np.random.default_rng(seed)
        scores = rng.standard_t(2, size=len(C))
        w = construction.capped_weights(scores, 0.25)
        assert w.sum() == pytest.approx(0, abs=1e-12)
        assert np.abs(w).sum() <= 1 + 1e-12
        assert np.abs(w).max() <= 0.25 + 1e-12

    def test_uncapped_weights_are_proportional(self) -> None:
        scores = np.array([3, 1, 0, 0, 0, 0, -1, -3], dtype=float)
        w = construction.capped_weights(scores, 1.0)
        assert np.abs(w).sum() == pytest.approx(1.0)
        assert w[0] / w[1] == pytest.approx((3 - 0) / (1 - 0))

    def test_a_single_long_name_shrinks_both_sides_rather_than_breaking_sum_zero(self) -> None:
        scores = np.array([7, -1, -1, -1, -1, -1, -1, -1], dtype=float)
        w = construction.capped_weights(scores, 0.25)
        assert w.sum() == pytest.approx(0, abs=1e-12)
        assert w[0] == pytest.approx(0.25)
        assert np.abs(w).sum() == pytest.approx(0.5)

    def test_band_holds_inside_and_trades_outside(self) -> None:
        held = np.array([0.2, 0.1, -0.2, -0.1, 0, 0, 0, 0])
        near = held + np.array([0.05, -0.05, 0, 0, 0, 0, 0, 0])
        assert np.array_equal(construction.band_rebalance(near, held, 0.10), held)
        far = held + np.array([0.15, -0.15, 0, 0, 0, 0, 0, 0])
        moved = construction.band_rebalance(far, held, 0.10)
        assert moved.sum() == pytest.approx(0, abs=1e-12)
        assert moved == pytest.approx(far)

    def test_a_single_breach_trades_with_a_counter_leg(self) -> None:
        """⭐ Without the counter-leg the sum-zero restoration cancels the only trade."""
        held = np.zeros(len(C))
        target = np.array([0.2, -0.06, -0.05, -0.04, -0.05, 0, 0, 0])
        moved = construction.band_rebalance(target, held, 0.10)
        assert moved.sum() == pytest.approx(0, abs=1e-12)
        assert moved[0] > 0
        assert np.count_nonzero(moved) == 2

    def test_same_signed_breaches_trade_with_a_counter_leg(self) -> None:
        """Two positive breaches and no negative one must still move the book."""
        held = np.zeros(len(C))
        target = np.array([0.15, 0.15, -0.075, -0.075, -0.075, -0.075, 0, 0])
        moved = construction.band_rebalance(target, held, 0.10)
        assert moved.sum() == pytest.approx(0, abs=1e-12)
        assert moved[0] > 0 and moved[1] > 0
        assert np.count_nonzero(moved) == 3

    def test_band_zero_is_full_rebalance(self) -> None:
        target = np.array([0.2, 0.1, -0.2, -0.1, 0, 0, 0, 0])
        assert np.array_equal(construction.band_rebalance(target, np.zeros(8), 0.0), target)

    def test_the_primary_band_reproduces_the_redesign_operating_point(self) -> None:
        """Signal-free: band 0.10 captures ~0.958 of a 20-day-half-life target."""
        table = construction.band_calibration(bands=(0.0, 0.10), days=252 * 20)
        assert table["rows"]["band_0"]["alpha_capture"] == 1.0
        assert table["rows"]["band_0.1"]["alpha_capture"] == pytest.approx(0.958, abs=0.02)
        assert (
            table["rows"]["band_0.1"]["annual_turnover"]
            < 0.6 * table["rows"]["band_0"]["annual_turnover"]
        )

    def test_the_capped_calibration_is_measured_through_the_primary_weights(self) -> None:
        free = construction.band_calibration(bands=(0.10,), days=252 * 10)
        capped = construction.band_calibration(bands=(0.10,), days=252 * 10, weight_cap=0.25)
        assert capped["weight_cap"] == 0.25
        assert capped["rows"]["band_0.1"] != free["rows"]["band_0.1"]

    def test_vol_targeter_caps_and_holds_within_hysteresis(self) -> None:
        targeter = construction.VolTargeter(0.10, 5.0, 0.10)
        assert targeter.update(0.04) == pytest.approx(2.5)
        assert targeter.update(0.042) == pytest.approx(2.5)
        assert targeter.update(0.05) == pytest.approx(2.0)
        assert targeter.update(0.001) == pytest.approx(5.0)
        assert targeter.uncapped == pytest.approx(100.0)


# ---------------------------------------------------------------- the book
class TestTheBook:
    def _mu(self, excess: pd.DataFrame, start: int = 150) -> pd.DataFrame:
        rng = np.random.default_rng(9)
        days = excess.index[start:-1]
        return pd.DataFrame(rng.normal(size=(len(days), len(C))), index=days, columns=C)

    def test_net_is_gross_minus_the_charged_cost_of_the_delta(self) -> None:
        excess = _synthetic_excess()
        result = construction.run_book(
            construction.BookConfig(name="t"), self._mu(excess), excess, 252.0
        )
        daily = result["daily"]
        assert (daily["net"] - (daily["gross"] - daily["cost"])).abs().max() < 1e-15
        exposures = daily[[f"x_{c}" for c in C]]
        assert exposures.sum(axis=1).abs().max() < 1e-12
        delta = exposures.diff().fillna(exposures.iloc[0]).abs().sum(axis=1)
        charged = delta * CHARGED_ONE_WAY_BP / 10_000
        assert (charged - daily["cost"]).abs().max() < 1e-15

    def test_pnl_is_earned_on_the_next_day_only(self) -> None:
        excess = _synthetic_excess()
        result = construction.run_book(
            construction.BookConfig(name="t", band=0.0, vol_target=None),
            self._mu(excess),
            excess,
            252.0,
        )
        daily = result["daily"]
        for pnl_day, row in daily.head(30).iterrows():
            exposure = row[[f"x_{c}" for c in C]].to_numpy(dtype=float)
            assert row["gross"] == pytest.approx(exposure @ excess.loc[pnl_day].to_numpy())
            assert pnl_day > row["decision_day"]

    @pytest.mark.parametrize("governor", [False, True])
    @pytest.mark.parametrize("cut", [300, 520, 777])
    def test_the_book_never_sees_the_future(self, governor: bool, cut: int) -> None:
        """⭐ Replacing every return after decision day t leaves every decision <= t unchanged.

        Truncation cannot show a one-day look-ahead — the last decision's P&L day
        survives in both runs — so the future is replaced rather than cut.
        """
        excess = _synthetic_excess(scale=0.02)
        mu = self._mu(excess)
        config = construction.BookConfig(name="t", drawdown_governor=governor)
        full = construction.run_book(config, mu, excess, 252.0)["daily"]
        t = excess.index[cut]
        altered = excess.copy()
        rng = np.random.default_rng(99)
        after = altered.index > t
        altered.loc[after] = rng.normal(0.0, 0.05, size=(int(after.sum()), len(C)))
        replaced = construction.run_book(config, mu, altered, 252.0)["daily"]
        columns = [f"x_{c}" for c in C] + ["leverage", "cost", "held_max_weight"]
        mask = full["decision_day"] <= t
        assert mask.sum() > 100
        pd.testing.assert_frame_equal(full.loc[mask, columns], replaced.loc[mask, columns])
        later = full["decision_day"] > t
        assert not np.allclose(full.loc[later, "x_USD"], replaced.loc[later, "x_USD"])

    def test_the_held_book_is_reported_not_the_target(self) -> None:
        """The cap binds the target; the held book drifts past it and must show that."""
        excess = _synthetic_excess()
        rng = np.random.default_rng(13)
        days = excess.index[150:-1]
        state = rng.normal(size=len(C))
        rows = []
        for _ in days:
            state = 0.95 * state + np.sqrt(1 - 0.95**2) * rng.normal(size=len(C))
            rows.append(state.copy())
        mu = pd.DataFrame(rows, index=days, columns=C)
        config = construction.BookConfig(name="t", vol_target=None)
        daily = construction.run_book(config, mu, excess, 252.0)["daily"]
        held = daily[[f"x_{c}" for c in C]].abs()
        assert (daily["held_max_weight"] - held.max(axis=1)).abs().max() < 1e-15
        assert (daily["held_gross"] - held.sum(axis=1)).abs().max() < 1e-15
        assert daily["held_max_weight"].max() > config.weight_cap

    def test_a_gap_in_the_decision_days_is_refused(self) -> None:
        excess = _synthetic_excess(days=400)
        mu = self._mu(excess)
        holed = mu.drop(mu.index[100:130])
        with pytest.raises(ValueError, match="contiguous"):
            construction.run_book(construction.BookConfig(name="t"), holed, excess, 252.0)

    def test_neutralisation_lowers_the_held_book_factor_loading(self) -> None:
        rng = np.random.default_rng(12)
        common = rng.normal(0, 0.01, size=(900, 1)) * np.linspace(-1, 1, len(C))
        raw = common + rng.normal(0, 0.002, size=(900, len(C)))
        excess = pd.DataFrame(raw, index=pd.bdate_range("2021-05-03", periods=900), columns=C)
        excess = excess.sub(excess.mean(axis=1), axis=0)
        mu = excess.rolling(20).sum().iloc[150:-1]
        neutral = construction.run_book(construction.BookConfig(name="n"), mu, excess, 252.0)
        plain = construction.run_book(
            construction.BookConfig(name="p", neutralize_leading_factor=False), mu, excess, 252.0
        )
        assert (
            neutral["daily"]["factor_abs_cosine"].mean()
            < 0.5 * plain["daily"]["factor_abs_cosine"].mean()
        )
        for pnl_day, row in neutral["daily"].iloc[::97].iterrows():
            held = row[[f"x_{c}" for c in C]].to_numpy(dtype=float)
            window = excess.loc[: row["decision_day"]].to_numpy()[-120:]
            factor = construction.leading_factor(window)
            loading = held @ factor
            assert row["factor_abs_cosine"] == pytest.approx(abs(loading) / np.linalg.norm(held))
            assert row["factor_pnl"] == pytest.approx(
                loading * (factor @ excess.loc[pnl_day].to_numpy())
            )

    def test_cost_stress_changes_cost_and_nothing_else(self) -> None:
        excess = _synthetic_excess()
        mu = self._mu(excess)
        base = construction.run_book(construction.BookConfig(name="b"), mu, excess, 252.0)["daily"]
        stressed = construction.run_book(
            construction.BookConfig(name="s", cost_multiple=2.0), mu, excess, 252.0
        )["daily"]
        assert (stressed["gross"] - base["gross"]).abs().max() < 1e-15
        assert (stressed["cost"] - 2 * base["cost"]).abs().max() < 1e-15

    def test_a_persistent_target_trades_far_less_than_daily_round_trips(self) -> None:
        """⭐ Measured on a synthetic persistent forecast: turnover follows persistence."""
        excess = _synthetic_excess(days=1200)
        rng = np.random.default_rng(11)
        days = excess.index[150:-1]
        state = rng.normal(size=len(C))
        rows = []
        rho = 0.5 ** (1 / 20)
        for _ in days:
            state = rho * state + np.sqrt(1 - rho**2) * rng.normal(size=len(C))
            rows.append(state.copy())
        mu = pd.DataFrame(rows, index=days, columns=C)
        daily = construction.run_book(
            construction.BookConfig(name="t", vol_target=None, neutralize_leading_factor=False),
            mu,
            excess,
            252.0,
        )["daily"]
        round_trips = daily["one_way_traded"].sum() / 2 / (len(daily) / 252)
        assert round_trips < 40
        assert daily["traded"].mean() < 1.0

    def test_the_drawdown_governor_only_ever_reduces_exposure(self) -> None:
        excess = _synthetic_excess(scale=0.02)
        mu = self._mu(excess)
        plain = construction.run_book(construction.BookConfig(name="p"), mu, excess, 252.0)
        governed = construction.run_book(
            construction.BookConfig(name="g", drawdown_governor=True), mu, excess, 252.0
        )
        assert (governed["daily"]["leverage"] <= plain["daily"]["leverage"] + 1e-12).all()


# --------------------------------------------------------------- the model
def _synthetic_frames(excess: pd.DataFrame, strength: float) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(21)
    forward = model.forward_target(excess)
    frames = {}
    for i, name in enumerate(model.FEATURES):
        noise = pd.DataFrame(rng.normal(size=excess.shape), index=excess.index, columns=C)
        if i == 0:
            informative = forward.fillna(0.0) / forward.std().mean()
            noise = strength * informative + noise
        frames[name] = noise.sub(noise.mean(axis=1), axis=0)
    return frames


class TestTheModel:
    def test_forward_target_is_the_next_h_days(self) -> None:
        excess = _synthetic_excess(days=40)
        target = model.forward_target(excess, horizon=5)
        expected = excess.iloc[11:16].sum()
        assert target.iloc[10].to_numpy() == pytest.approx(expected.to_numpy())
        assert target.iloc[-5:].isna().all().all()

    @pytest.mark.parametrize("fold_number", [1, 2])
    def test_no_return_from_the_embargo_day_onward_reaches_a_fold(self, fold_number: int) -> None:
        """⭐ The label purge, by replacement: returns from the day before the test
        window onward are rewritten, and that fold's predictions do not move."""
        excess = _synthetic_excess(days=1100)
        frames = _synthetic_frames(excess, 0.5)
        kwargs = {"initial_train_years": 1.5, "step_years": 0.5}
        base = model.walk_forward(frames, excess, **kwargs)
        fold = base["folds"][fold_number]
        start = excess.index.get_loc(fold.test_start) - model.EMBARGO_DAYS
        altered = excess.copy()
        rng = np.random.default_rng(5)
        altered.iloc[start:] = rng.normal(0.0, 0.05, size=(len(excess) - start, len(C)))
        moved = model.walk_forward(frames, altered, **kwargs)
        window = (base["mu"].index >= fold.test_start) & (base["mu"].index <= fold.test_end)
        pd.testing.assert_frame_equal(base["mu"].loc[window], moved["mu"].loc[window])
        later = base["folds"][fold_number + 1]
        later_window = base["mu"].index >= later.test_start
        assert not np.allclose(base["mu"].loc[later_window], moved["mu"].loc[later_window])

    def test_the_standardisation_never_sees_the_test_window(self) -> None:
        """Rewriting a fold's features after its first test day leaves that day unchanged."""
        excess = _synthetic_excess(days=1100)
        frames = _synthetic_frames(excess, 0.5)
        kwargs = {"initial_train_years": 1.5, "step_years": 0.5}
        base = model.walk_forward(frames, excess, **kwargs)
        fold = base["folds"][1]
        altered = {name: frame.copy() for name, frame in frames.items()}
        for frame in altered.values():
            later = (frame.index > fold.test_start) & (frame.index <= fold.test_end)
            frame.loc[later] = frame.loc[later] * 25.0 + 3.0
        moved = model.walk_forward(altered, excess, **kwargs)
        assert base["mu"].loc[fold.test_start].to_numpy() == pytest.approx(
            moved["mu"].loc[fold.test_start].to_numpy(), abs=1e-15
        )

    def test_each_test_day_is_predicted_exactly_once(self) -> None:
        excess = _synthetic_excess(days=900)
        result = model.walk_forward(
            _synthetic_frames(excess, 0.0), excess, initial_train_years=1.5, step_years=0.5
        )
        mu = result["mu"]
        assert not mu.index.duplicated().any()
        assert mu.index.min() == result["folds"][0].test_start

    def test_the_unfitted_rules_are_each_horizon_in_both_signs(self) -> None:
        """⭐ Sign, horizon and timing of every benchmark proxy, pinned on the values."""
        excess = _synthetic_excess(days=400)
        frames = _synthetic_frames(excess, 0.0)
        days = excess.index[100:300]
        rules = model.unfitted_rules(frames, days, C)
        expected = {f"{s}_{h}d" for h in (5, 20, 60) for s in ("persistence", "reversal")}
        assert set(rules) == expected
        for horizon in model.UNFITTED_HORIZONS:
            source = frames[f"currency_excess_return_{horizon}d_z"].loc[days, C]
            pd.testing.assert_frame_equal(rules[f"persistence_{horizon}d"], source)
            pd.testing.assert_frame_equal(rules[f"reversal_{horizon}d"], -source)
        assert not np.allclose(rules["persistence_5d"], rules["persistence_60d"])

    def test_a_planted_signal_is_recovered_with_the_right_sign(self) -> None:
        excess = _synthetic_excess(days=900)
        result = model.walk_forward(
            _synthetic_frames(excess, 0.5), excess, initial_train_years=1.5, step_years=0.5
        )
        first = model.FEATURES[0]
        for fold in result["fold_diagnostics"]:
            coefficients = fold["coefficients"]
            assert coefficients[first] > 0
            assert abs(coefficients[first]) == max(abs(v) for v in coefficients.values())
            assert fold["effective_df"] == pytest.approx(model.TARGET_EFFECTIVE_DF, abs=1e-4)


# ------------------------------------------------------------ adjudication
def _summary(**overrides: Any) -> dict[str, Any]:
    base = {
        "net_sharpe": 0.6,
        "net_without_top_5_days": 0.05,
        "net_clipped_3_robust_sigma_annual": 0.04,
        "gross_pnl_without_best_currency": 0.05,
        "gross_pnl_without_best_two_currencies": 0.03,
        "gross_pnl_without_usd": 0.04,
        "share_of_folds_positive": 0.7,
        "turnover_round_trips_per_year_per_unit_gross": 20.0,
        "share_days_at_leverage_cap": 0.1,
        "best_currency_share_of_positive_pnl": 0.3,
        "top_10_day_share_of_net": 0.3,
    }
    base.update(overrides)
    base["economic_band"] = economic_band(base["net_sharpe"])
    return base


def _rules(
    momentum: float = 0.1, reversal: float = -0.3, **others: tuple[float, float | None]
) -> dict[str, dict[str, Any]]:
    rules: dict[str, dict[str, Any]] = {
        f"{sign}_{h}d": {"net_sharpe": -0.2, "pnl_correlation": 0.1}
        for h in model.UNFITTED_HORIZONS
        for sign in ("persistence", "reversal")
    }
    rules["persistence_60d"] = {"net_sharpe": momentum, "pnl_correlation": 0.2}
    rules["reversal_60d"] = {"net_sharpe": reversal, "pnl_correlation": -0.2}
    for name, (sharpe, corr) in others.items():
        rules[name] = {"net_sharpe": sharpe, "pnl_correlation": corr}
    return rules


def _verdict(
    primary: dict[str, Any],
    stressed: float = 0.4,
    momentum: float = 0.1,
    reversal: float = -0.3,
    **others: tuple[float, float | None],
) -> dict[str, Any]:
    return evaluation.adjudicate(
        primary,
        stressed_1_5={"net_sharpe": stressed},
        unfitted_rules=_rules(momentum, reversal, **others),
        rules=prereg.ADJUDICATION_RULES,
    )


def _adjudicate(
    primary: dict[str, Any],
    stressed: float = 0.4,
    momentum: float = 0.1,
    reversal: float = -0.3,
    **others: tuple[float, float | None],
) -> str:
    return _verdict(primary, stressed, momentum, reversal, **others)["case"]


class TestAdjudication:
    def test_case_a(self) -> None:
        assert _adjudicate(_summary()) == CASE_A

    def test_case_b_band(self) -> None:
        assert _adjudicate(_summary(net_sharpe=0.4)) == CASE_B

    def test_a_good_sharpe_that_collapses_at_1_5x_cost_is_at_most_marginal(self) -> None:
        assert _adjudicate(_summary(), stressed=-0.1) == CASE_B

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("net_sharpe", 0.0),
            ("net_sharpe", 0.15),
            ("net_clipped_3_robust_sigma_annual", 0.0),
            ("net_clipped_3_robust_sigma_annual", None),
            ("gross_pnl_without_best_currency", -0.01),
            ("share_of_folds_positive", 0.4),
            ("turnover_round_trips_per_year_per_unit_gross", 60.0),
            ("share_days_at_leverage_cap", 0.6),
        ],
    )
    def test_every_kill_clause_fires_on_its_own(self, field: str, value: float) -> None:
        assert _adjudicate(_summary(**{field: value})) == CASE_C

    def test_a_primary_that_does_not_beat_the_persistence_rule_is_killed(self) -> None:
        """⭐ The C08 boundary as an executable clause."""
        assert _adjudicate(_summary(net_sharpe=0.6), momentum=0.6) == CASE_C

    def test_a_primary_that_does_not_beat_the_inverted_rule_is_killed(self) -> None:
        """⭐ A fitted reversal book cannot survive on the persistence rule having lost."""
        assert _adjudicate(_summary(net_sharpe=1.46), momentum=-2.87, reversal=2.32) == CASE_C

    @pytest.mark.parametrize(
        "field", ["gross_pnl_without_best_two_currencies", "gross_pnl_without_usd"]
    )
    def test_a_one_pair_or_usd_only_book_is_not_a_candidate(self, field: str) -> None:
        assert _adjudicate(_summary(**{field: -0.001})) == CASE_C
        assert _adjudicate(_summary(net_sharpe=0.4, **{field: 0.0})) == CASE_C

    def test_a_resembling_unfitted_rule_at_another_horizon_kills(self) -> None:
        """⭐ A fitted 5-day reversal book is not saved by the 60-day benchmark."""
        primary = _summary(net_sharpe=1.48)
        assert _adjudicate(primary, momentum=-0.16, reversal=-0.29) == CASE_A
        assert _adjudicate(primary, reversal_5d=(1.48, 0.9)) == CASE_C
        assert _adjudicate(primary, reversal_5d=(1.47, 0.9)) == CASE_A
        assert _adjudicate(primary, persistence_20d=(2.0, 0.49)) == CASE_A
        assert _adjudicate(primary, persistence_20d=(2.0, 0.5)) == CASE_C
        assert _adjudicate(primary, persistence_20d=(2.0, None)) == CASE_A

    def test_resemblance_is_flagged_whatever_the_case(self) -> None:
        verdict = _verdict(_summary(net_sharpe=1.48), reversal_5d=(0.4, 0.71))
        assert verdict["case"] == CASE_A
        assert verdict["resembles_an_unfitted_rule"]
        assert verdict["max_pnl_correlation_with_an_unfitted_rule"] == 0.71
        assert not _verdict(_summary(), reversal_5d=(0.4, 0.69))["resembles_an_unfitted_rule"]
        assert _verdict(_summary(), reversal_5d=(0.4, 0.7))["resembles_an_unfitted_rule"]

    def test_top_day_shares_do_not_gate(self) -> None:
        """⭐ ~850 days: ten ordinary days hold ~26 deviations; the clause demanded Sharpe ~1."""
        assert _adjudicate(_summary(net_sharpe=0.6, top_10_day_share_of_net=0.9)) == CASE_A
        verdict = _verdict(_summary(net_sharpe=0.4, top_10_day_share_of_net=0.9))
        assert verdict["case"] == CASE_B
        assert verdict["top_day_shares_reported_not_gated"]["top_10"] == 0.9

    def test_the_tail_kill_reads_extreme_days_not_fat_tails(self) -> None:
        """⭐ Symmetric fat tails survive; a book living on outsized up-days does not.

        Net-without-the-top-five-days killed about half of fat-tailed books at
        Sharpe 0.3-0.4; a 1% winsorised mean could not see a lottery of more
        than about 8 days. Clipping at 3 robust sigmas does neither.
        """
        days = pd.bdate_range("2022-01-03", periods=850)
        rng = np.random.default_rng(17)
        drift = 0.35 / np.sqrt(261) * 0.005
        fat = rng.standard_t(4, size=850) / np.sqrt(2) * 0.005
        fat = fat - fat.mean() + drift
        labels = pd.Series(0.0, index=days)

        def summary(series: np.ndarray) -> dict[str, Any]:
            return evaluation.summarise(
                _daily_frame(days, series), days_per_year=261.0, fold_labels=labels
            )

        fat_summary = summary(fat)
        assert fat_summary["net_without_top_5_days"] <= 0
        assert fat_summary["net_clipped_3_robust_sigma_annual"] > 0
        for outliers in (6, 13, 25):
            lottery = rng.normal(-0.001, 0.005, size=850)
            lottery[rng.choice(850, size=outliers, replace=False)] += 1.2 / outliers
            lottery_summary = summary(lottery)
            assert lottery_summary["net_annual_return"] > 0, outliers
            assert lottery_summary["net_clipped_3_robust_sigma_annual"] <= 0, outliers
        median = np.median(fat)
        scale = 1.4826 * np.median(np.abs(fat - median))
        expected = np.clip(fat, median - 3 * scale, median + 3 * scale).mean() * 261.0
        assert fat_summary["net_clipped_3_robust_sigma_annual"] == pytest.approx(expected, abs=1e-6)

    def test_an_unmeasurable_tail_counts_as_dependent(self) -> None:
        days = pd.bdate_range("2022-01-03", periods=100)
        constant = pd.Series(0.001, index=days)
        assert np.isnan(evaluation.clipped_mean(constant))
        assert np.isnan(evaluation.clipped_mean(pd.Series(dtype=float)))

    def test_measured_days_per_year(self) -> None:
        days = pd.bdate_range("2023-01-02", periods=522)
        assert evaluation.measured_days_per_year(days) == pytest.approx(261, abs=1.5)

    def test_pnl_correlation(self) -> None:
        index = pd.bdate_range("2023-01-02", periods=50)
        a = pd.Series(np.random.default_rng(1).normal(size=50), index=index)
        assert evaluation.pnl_correlation(a, 2 * a) == pytest.approx(1.0)
        assert evaluation.pnl_correlation(a, -a.iloc[10:]) == pytest.approx(-1.0)
        assert evaluation.pnl_correlation(a, a * 0) is None

    def test_an_increment_over_a_negative_baseline_is_not_survival(self) -> None:
        """⭐ −0.983 → +0.234 is not an edge: the primary's own Sharpe decides."""
        assert _adjudicate(_summary(net_sharpe=0.234), momentum=-0.983) == CASE_C

    def test_vol_scenarios_report_the_books_that_were_run(self) -> None:
        def run(target: float, ret: float, lev: float, cap: float) -> dict[str, Any]:
            return {
                "net_annual_return": ret,
                "realized_annual_vol": target * 0.8,
                "realized_vol_over_target": 0.8,
                "max_drawdown": -0.1,
                "mean_leverage": lev,
                "p95_leverage": lev,
                "share_days_at_leverage_cap": cap,
                "cost_annual_drag": 0.01,
                "net_sharpe": 0.4,
            }

        books = {0.08: run(0.08, 0.03, 4.0, 0.2), 0.10: run(0.10, 0.04, 4.8, 0.6)}
        books[0.12] = run(0.12, 0.041, 5.0, 0.97)
        rows = evaluation.vol_scenarios(books)
        assert rows["vol_0.12"]["mean_leverage"] == 5.0
        assert rows["vol_0.12"]["annual_net_return"] == 0.041
        assert rows["vol_0.12"]["share_days_at_leverage_cap"] == 0.97

    def test_a_short_tail_fold_does_not_count_toward_the_fold_share(self) -> None:
        days = pd.bdate_range("2023-01-02", periods=205)
        rng = np.random.default_rng(3)
        net = rng.normal(0.001, 0.001, size=len(days))
        net[200:] = [-0.01, -0.02, -0.01, -0.03, -0.01]
        daily = _daily_frame(days, net)
        labels = pd.Series([0] * 100 + [1] * 100 + [2] * 5, index=days, dtype=float)
        summary = evaluation.summarise(daily, days_per_year=252.0, fold_labels=labels)
        assert summary["per_fold_days"] == {"0": 100, "1": 100, "2": 5}
        assert summary["per_fold_net_sharpe"]["2"] < 0
        assert summary["share_of_folds_positive"] == 1.0

    def test_a_usd_jpy_bet_has_no_breadth(self) -> None:
        """⭐ Sum-zero one-pair book: dropping one currency leaves the other leg's P&L."""
        days = pd.bdate_range("2023-01-02", periods=120)
        rng = np.random.default_rng(4)
        usd = rng.normal(0.0006, 0.001, size=len(days))
        jpy = rng.normal(0.0005, 0.001, size=len(days))
        daily = _daily_frame(days, usd + jpy, pnl={"USD": usd, "JPY": jpy})
        labels = pd.Series(0.0, index=days)
        summary = evaluation.summarise(daily, days_per_year=252.0, fold_labels=labels)
        assert summary["gross_pnl_without_best_currency"] > 0
        assert summary["gross_pnl_without_best_two_currencies"] == pytest.approx(0.0, abs=1e-9)
        assert summary["gross_pnl_without_usd"] == pytest.approx(float(jpy.sum()), abs=1e-6)

    def test_the_leverage_cap_share_is_measured(self) -> None:
        excess = _synthetic_excess(days=500, scale=0.0002)
        mu = TestTheBook()._mu(excess)
        daily = construction.run_book(construction.BookConfig(name="t"), mu, excess, 252.0)["daily"]
        summary = evaluation.summarise(
            daily,
            days_per_year=252.0,
            fold_labels=pd.Series(0.0, index=excess.index),
            vol_target=0.10,
        )
        assert summary["share_days_at_leverage_cap"] > 0.9
        assert summary["mean_uncapped_leverage"] > 5.0
        assert summary["realized_vol_over_target"] < 0.5

    def test_the_cap_counts_demand_so_hysteresis_cannot_hide_it(self) -> None:
        """⭐ Held leverage can sit at 4.55 for months while the target asks for 25."""
        rng = np.random.default_rng(5)
        n = 1200
        scale = np.concatenate([np.full(300, 0.0040), np.geomspace(0.0040, 0.0006, 900)])
        raw = rng.normal(size=(n, len(C))) * scale[:, None]
        excess = pd.DataFrame(raw, index=pd.bdate_range("2020-01-06", periods=n), columns=C)
        excess = excess.sub(excess.mean(axis=1), axis=0)
        mu = TestTheBook()._mu(excess)
        daily = construction.run_book(construction.BookConfig(name="t"), mu, excess, 252.0)["daily"]
        demand = daily["uncapped_leverage"] >= 5.0
        assert (daily["at_leverage_cap"] == demand).all()
        hidden = demand & (daily["leverage"] < 5.0 - 1e-12)
        assert hidden.sum() >= 10
        assert daily.loc[hidden, "at_leverage_cap"].all()


def _daily_frame(
    days: pd.DatetimeIndex, net: np.ndarray, pnl: dict[str, np.ndarray] | None = None
) -> pd.DataFrame:
    columns: dict[str, Any] = {
        "decision_day": days,
        "net": net,
        "gross": net,
        "cost": 0.0,
        "implementation_cost": 0.0,
        "currency_gross": 1.0,
        "pair_gross": 1.0,
        "one_way_traded": 0.1,
        "traded": True,
        "leverage": 1.0,
        "uncapped_leverage": np.nan,
        "at_leverage_cap": False,
        "held_max_weight": 0.25,
        "held_gross": 1.0,
        "factor_abs_cosine": 0.1,
        "factor_pnl": 0.0,
        "raw_target_corr": 1.0,
    }
    for c in C:
        columns[f"pnl_{c}"] = (pnl or {}).get(c, np.zeros(len(days)))
    return pd.DataFrame(columns, index=days + pd.Timedelta(days=1))


# ----------------------------------------------------------------- prereg
class TestPreregistration:
    def test_the_primary_is_the_declared_architecture(self) -> None:
        primary = prereg.PRIMARY
        assert primary.mapping == "vol_normalized"
        assert primary.neutralize_leading_factor
        assert primary.band == 0.10
        assert primary.vol_target == 0.10
        assert primary.cost_multiple == 1.0
        assert not primary.drawdown_governor

    def test_each_diagnostic_changes_exactly_one_choice(self) -> None:
        base = dataclasses.asdict(prereg.PRIMARY)
        for config in prereg.DIAGNOSTICS:
            changed = {
                key
                for key, value in dataclasses.asdict(config).items()
                if key != "name" and value != base[key]
            }
            assert len(changed) == 1, (config.name, changed)

    def test_the_search_budget_matches_the_declared_books(self) -> None:
        assert prereg.SEARCH_BUDGET["diagnostic_books"] == len(prereg.DIAGNOSTICS)
        assert prereg.SEARCH_BUDGET["features"] == len(model.FEATURES) == 7
        assert prereg.SEARCH_BUDGET["horizons"] == 1

    def test_the_novelty_boundary_is_written_down(self) -> None:
        text = prereg.__doc__ or ""
        for needle in ("H-003", "C08", "Baseline 1", "does_not_beat_the_unfitted_benchmark"):
            assert needle in text

    def test_every_hashed_source_exists(self) -> None:
        for relative in prereg.HASHED_SOURCES:
            assert (ROOT / relative).is_file(), relative

    def test_the_hash_moves_when_a_threshold_moves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        before = prereg.freeze_hash()
        moved = dict(prereg.ADJUDICATION_RULES)
        moved["max_share_days_at_leverage_cap"] = 0.99
        monkeypatch.setattr(prereg, "ADJUDICATION_RULES", moved)
        assert prereg.freeze_hash() != before

    def test_the_hash_moves_when_a_source_moves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        before = prereg.freeze_hash()
        real = prereg.source_digests

        def edited() -> dict[str, str]:
            out = real()
            out["scripts/research/continuous_portfolio/construction.py"] = "0" * 64
            return out

        monkeypatch.setattr(prereg, "source_digests", edited)
        assert prereg.freeze_hash() != before

    def test_the_digest_ignores_line_endings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`source_digests` itself, over an LF and a CRLF copy of every hashed source."""
        for relative in prereg.HASHED_SOURCES:
            text = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
            for flavour, content in (("lf", text), ("crlf", text.replace(b"\n", b"\r\n"))):
                target = tmp_path / flavour / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        monkeypatch.setattr(prereg, "_ROOT", tmp_path / "lf")
        lf = prereg.source_digests()
        monkeypatch.setattr(prereg, "_ROOT", tmp_path / "crlf")
        assert prereg.source_digests() == lf
        edited = tmp_path / "crlf" / prereg.HASHED_SOURCES[1]
        edited.write_bytes(edited.read_bytes() + b"# edit\r\n")
        assert prereg.source_digests() != lf

    def test_the_recorded_hash_is_the_measured_one(self) -> None:
        if prereg.FROZEN_HASH == "UNFROZEN":
            pytest.skip("frozen immediately before execution")
        assert prereg.assert_frozen() == prereg.FROZEN_HASH


# ------------------------------------------------------ development helpers
class TestDevelopmentHelpers:
    def test_the_regime_threshold_is_past_only(self) -> None:
        from scripts.research.continuous_portfolio import development

        excess = _synthetic_excess(days=600)
        t = excess.index[400]
        altered = excess.copy()
        after = altered.index > t
        altered.loc[after] = altered.loc[after] * 40.0
        base_dispersion, base_threshold = development._dispersion_and_threshold(excess)
        new_dispersion, new_threshold = development._dispersion_and_threshold(altered)
        upto = excess.index <= t
        pd.testing.assert_series_equal(base_threshold[upto], new_threshold[upto])
        pd.testing.assert_series_equal(base_dispersion[upto], new_dispersion[upto])

    def test_eur_is_on_the_deposit_facility_throughout(self) -> None:
        from scripts.research.continuous_portfolio import development

        dates = pd.to_datetime(
            ["2021-04-26", "2022-01-03", "2023-01-02", "2024-09-17", "2024-09-18"], utc=True
        )
        frame = pd.DataFrame(
            {
                "date": list(dates) * 2,
                "currency": ["EUR"] * 5 + ["USD"] * 5,
                "rate_pct": [0.0, 0.0, 2.50, 4.25, 3.50, 0.25, 0.25, 4.5, 5.5, 5.0],
            }
        )
        rates = development._policy_rates(frame)
        assert rates["EUR"].tolist() == pytest.approx([-0.5, -0.5, 2.00, 3.75, 3.50])
        assert rates["USD"].tolist() == pytest.approx([0.25, 0.25, 4.5, 5.5, 5.0])

    def test_the_non_overlapping_ic_t_uses_every_horizon_th_day(self) -> None:
        from scripts.research.continuous_portfolio import development

        excess = _synthetic_excess(days=300)
        noise = _synthetic_excess(days=300, seed=8)
        scores = (excess.shift(-1) + noise).iloc[:-5]
        one = development._rank_ic(scores, excess.shift(-1), 1)
        five = development._rank_ic(scores, excess.shift(-1), 5)
        assert one["mean"] == five["mean"]
        assert five["t_non_overlapping"] < one["t_non_overlapping"]


# --------------------------------------------------- the run, end to end
def test_the_development_run_end_to_end_on_a_synthetic_corpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every book the run assembles, wired as declared — no market data anywhere.

    The corpus, the features, the freeze check and the carry read are replaced
    by synthetic stand-ins; everything between them is the real run.
    """
    from scripts.research.continuous_portfolio import development

    excess = _synthetic_excess(days=1100, seed=31)
    frames = _synthetic_frames(excess, 0.5)
    monkeypatch.setattr(prereg, "assert_frozen", lambda: "synthetic")
    monkeypatch.setattr(
        development.corpus_module,
        "currency_panel",
        lambda: {"currency_excess_return": excess},
    )
    monkeypatch.setattr(development.corpus_module, "provenance", lambda panel: {"synthetic": True})
    monkeypatch.setattr(development.feature_module, "build", lambda panel: frames)
    monkeypatch.setattr(development, "_carry_accrual", lambda daily, start, end: {})
    record = development.run()

    assert record["adjudication"]["case"] in (CASE_A, CASE_B, CASE_C)
    assert set(record["unfitted_rules"]) == {
        f"{s}_{h}d" for h in (5, 20, 60) for s in ("persistence", "reversal")
    }
    rules = record["unfitted_rules"]
    for horizon in (5, 20, 60):
        up = rules[f"persistence_{horizon}d"]["summary"]
        down = rules[f"reversal_{horizon}d"]["summary"]
        assert up["gross_annual_return"] == pytest.approx(-down["gross_annual_return"], abs=1e-9)
        assert up["cost_annual_drag"] == pytest.approx(down["cost_annual_drag"], abs=1e-9)
    assert (
        rules["persistence_5d"]["summary"]["gross_annual_return"]
        != rules["persistence_60d"]["summary"]["gross_annual_return"]
    )
    primary = record["primary"]["summary"]
    assert (
        primary["gross_annual_return"] != rules["persistence_60d"]["summary"]["gross_annual_return"]
    )
    assert record["baseline_1_unfitted_persistence"] == rules["persistence_60d"]
    adjudicated = record["adjudication"]["unfitted_rules"]
    assert adjudicated["reversal_5d"]["net_sharpe"] == rules["reversal_5d"]["summary"]["net_sharpe"]
    #: the planted signal sits in the 5-day z-score with a positive sign, so the
    #: label "persistence" must be the book that earns it
    assert rules["persistence_5d"]["summary"]["gross_annual_return"] > 0
    assert rules["reversal_5d"]["summary"]["gross_annual_return"] < 0
    targets = [row["vol_target"] for row in record["vol_scenarios"].values()]
    assert targets == [0.08, 0.10, 0.12]
    for key, diagnostic in (
        ("vol_0.08", "diag_vol_target_0_08"),
        ("vol_0.12", "diag_vol_target_0_12"),
    ):
        assert (
            record["vol_scenarios"][key]["annual_net_return"]
            == record["diagnostics"][diagnostic]["summary"]["net_annual_return"]
        )
    assert record["vol_scenarios"]["vol_0.1"]["net_sharpe"] == primary["net_sharpe"]
    assert set(record["diagnostics"]) == {config.name for config in prereg.DIAGNOSTICS}


# ------------------------------------------------------------------ driver
class TestDriver:
    def _no_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.research.continuous_portfolio import development

        def refuse() -> None:
            raise AssertionError("development.run must not be reached")

        monkeypatch.setattr(development, "run", refuse)

    @pytest.mark.parametrize("existing", ["development.started.json", "development.json"])
    def test_the_run_happens_once(
        self, existing: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scripts.research.continuous_portfolio import driver

        self._no_run(monkeypatch)
        monkeypatch.setattr(driver, "ARTIFACTS", tmp_path)
        (tmp_path / existing).write_text("{}", encoding="utf-8")
        with pytest.raises(SystemExit, match="happens once"):
            driver.develop()

    def test_a_source_differing_from_head_refuses_before_the_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scripts.research.continuous_portfolio import driver

        self._no_run(monkeypatch)
        monkeypatch.setattr(driver, "ARTIFACTS", tmp_path)
        monkeypatch.setattr(
            driver, "checkout", lambda paths: {"head": "x", "sources_differing_from_head": ["a"]}
        )
        with pytest.raises(SystemExit, match="differ from HEAD"):
            driver.develop()
        assert not (tmp_path / driver.STARTED).exists()

    def test_the_start_marker_is_written_before_anything_is_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from scripts.research.continuous_portfolio import development, driver

        monkeypatch.setattr(driver, "ARTIFACTS", tmp_path)
        monkeypatch.setattr(
            driver, "checkout", lambda paths: {"head": "abc", "sources_differing_from_head": []}
        )
        monkeypatch.setattr(prereg, "assert_frozen", lambda: "frozen")

        def run() -> None:
            marker = json.loads((tmp_path / driver.STARTED).read_text(encoding="utf-8"))
            assert marker["checkout"]["head"] == "abc"
            assert marker["preregistration_frozen_hash"] == "frozen"
            raise RuntimeError("stop after the marker check")

        monkeypatch.setattr(development, "run", run)
        with pytest.raises(RuntimeError, match="stop after the marker check"):
            driver.develop()
        with pytest.raises(SystemExit, match="happens once"):
            driver.develop()

    def test_a_marker_created_after_the_check_still_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A second launch racing past the existence check loses at the exclusive create."""
        from scripts.research.continuous_portfolio import driver

        self._no_run(monkeypatch)
        monkeypatch.setattr(driver, "ARTIFACTS", tmp_path)
        monkeypatch.setattr(prereg, "assert_frozen", lambda: "frozen")

        def racing_checkout(paths: tuple[str, ...]) -> dict[str, Any]:
            (tmp_path / driver.STARTED).write_text('{"other": true}', encoding="utf-8")
            return {"head": "abc", "sources_differing_from_head": []}

        monkeypatch.setattr(driver, "checkout", racing_checkout)
        with pytest.raises(SystemExit, match="happens once"):
            driver.develop()
        assert json.loads((tmp_path / driver.STARTED).read_text(encoding="utf-8")) == {
            "other": True
        }

    def test_checkout_compares_content_not_the_index(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An `assume-unchanged` flag hides an edit from `git status`, not from this."""
        import subprocess

        from scripts.research.continuous_portfolio import driver

        def git(*args: str) -> None:
            subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

        git("init", "-q")
        git("config", "user.email", "t@example.invalid")
        git("config", "user.name", "t")
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("y = 1\n", encoding="utf-8")
        git("add", "a.py", "b.py")
        git("commit", "-q", "-m", "c")
        monkeypatch.setattr(driver, "ROOT", tmp_path)
        assert driver.checkout(("a.py", "b.py"))["sources_differing_from_head"] == []
        (tmp_path / "a.py").write_bytes(b"x = 1\r\n")
        assert driver.checkout(("a.py",))["sources_differing_from_head"] == []
        (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")
        git("update-index", "--assume-unchanged", "b.py")
        assert driver.checkout(("a.py", "b.py", "c.py"))["sources_differing_from_head"] == [
            "b.py",
            "c.py",
        ]

    def test_paths_are_anchored_at_the_repository_root(self) -> None:
        from scripts.research.continuous_portfolio import driver

        assert driver.ROOT == ROOT
        assert driver.ARTIFACTS.is_absolute()


# --------------------------------------------------------------- boundary
class TestBoundary:
    def test_no_computation_module_reads_a_file(self) -> None:
        for name in ("__init__.py", "construction.py", "model.py", "evaluation.py"):
            source = (PACKAGE / name).read_text(encoding="utf-8")
            for forbidden in ("read_parquet", "read_csv", "open(", "urlopen", "load_pair"):
                assert forbidden not in source, f"{name}: {forbidden}"

    def test_development_reaches_data_only_through_the_guarded_corpus_and_a_bounded_rate_read(
        self,
    ) -> None:
        source = (PACKAGE / "development.py").read_text(encoding="utf-8")
        assert source.count("read_parquet") == 1
        assert "filters=" in source
        assert "assert_not_protected(start, end)" in source
        for forbidden in ("read_csv", "urlopen", "open(", "2016-", "2026-"):
            assert forbidden not in source, forbidden
        assert "prereg_module.assert_frozen()" in source.split("def run")[1].split("\n")[1]

    def test_no_broker_or_order_code_is_reachable(self) -> None:
        for path in PACKAGE.glob("*.py"):
            source = path.read_text(encoding="utf-8").lower()
            for forbidden in ("oanda", "order", "requests", "http"):
                if forbidden == "order" and "order" in source:
                    assert "place_order" not in source and "submit_order" not in source
                    continue
                assert forbidden not in source, f"{path.name}: {forbidden}"


# ------------------------------------------------------- real-corpus geometry
_CACHES = [ROOT / b["cache"] / "m15_AUD_CAD.parquet" for b in SEEN_SPANS.values()]
needs_bars = pytest.mark.skipif(
    not all(path.is_file() for path in _CACHES),
    reason="the M15 caches are untracked local artefacts",
)


@needs_bars
def test_the_real_corpus_supports_the_declared_geometry_without_fitting_anything() -> None:
    """Fold geometry and feature completeness only — no model is fitted here."""
    from scripts.research.model_learning import corpus, features

    panel = corpus.currency_panel()
    excess = panel["currency_excess_return"][C]
    frames = features.build(panel)
    days = model.usable_days(frames, excess)
    start = excess.index.get_loc(days[0])
    assert list(excess.index[start:]) == list(days), "usable days must be contiguous"
    folds = model.wf.make_folds(
        days,
        initial_train_years=prereg.WALK_FORWARD["initial_train_years"],
        step_years=prereg.WALK_FORWARD["step_years"],
        horizon_days=model.HORIZON_DAYS,
        embargo_days=model.EMBARGO_DAYS,
    )
    assert 5 <= len(folds) <= 8
    assert folds[0].test_start > days[0]


def test_the_prereg_artifact_matches_the_code_if_written() -> None:
    path = ROOT / "artifacts/research/continuous_portfolio/prereg.json"
    if not path.exists():
        pytest.skip("run the prereg stage")
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed["frozen_hash"] == prereg.freeze_hash()
