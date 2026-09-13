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

    def test_vol_targeter_caps_and_holds_within_hysteresis(self) -> None:
        targeter = construction.VolTargeter(0.10, 5.0, 0.10)
        assert targeter.update(0.04) == pytest.approx(2.5)
        assert targeter.update(0.042) == pytest.approx(2.5)
        assert targeter.update(0.05) == pytest.approx(2.0)
        assert targeter.update(0.001) == pytest.approx(5.0)


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

    def test_the_book_never_sees_the_future(self) -> None:
        """⭐ Truncating returns after day k leaves every earlier decision unchanged."""
        excess = _synthetic_excess()
        mu = self._mu(excess)
        config = construction.BookConfig(name="t")
        full = construction.run_book(config, mu, excess, 252.0)["daily"]
        cut = excess.index[500]
        truncated = construction.run_book(
            config, mu[mu.index < cut], excess[excess.index <= cut], 252.0
        )["daily"]
        columns = [f"x_{c}" for c in C] + ["leverage", "cost"]
        shared = truncated.index
        assert len(shared) > 300
        pd.testing.assert_frame_equal(full.loc[shared, columns], truncated[columns])

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

    def test_training_rows_never_reach_the_test_window(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⭐ The label purge, measured on the rows the fit actually receives."""
        excess = _synthetic_excess(days=900)
        frames = _synthetic_frames(excess, 0.0)
        seen: list[int] = []
        real_fit = model.wf.fit_ridge

        def recording(design: np.ndarray, target: np.ndarray, df: float) -> Any:
            seen.append(len(target))
            return real_fit(design, target, df)

        monkeypatch.setattr(model.wf, "fit_ridge", recording)
        result = model.walk_forward(frames, excess, initial_train_years=1.5, step_years=0.5)
        days = result["usable_days"]
        for fold in result["folds"]:
            last_label_day = days[days.get_loc(fold.train_end) + model.HORIZON_DAYS]
            assert last_label_day < fold.test_start
        assert len(seen) == len(result["folds"])

    def test_each_test_day_is_predicted_exactly_once(self) -> None:
        excess = _synthetic_excess(days=900)
        result = model.walk_forward(
            _synthetic_frames(excess, 0.0), excess, initial_train_years=1.5, step_years=0.5
        )
        mu = result["mu"]
        assert not mu.index.duplicated().any()
        assert mu.index.min() == result["folds"][0].test_start

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
        "gross_pnl_without_best_currency": 0.05,
        "share_of_folds_positive": 0.7,
        "turnover_round_trips_per_year_per_unit_gross": 20.0,
        "mean_leverage": 2.7,
        "best_currency_share_of_positive_pnl": 0.3,
        "top_10_day_share_of_net": 0.3,
    }
    base.update(overrides)
    base["economic_band"] = economic_band(base["net_sharpe"])
    return base


def _adjudicate(primary: dict[str, Any], stressed: float = 0.4, momentum: float = 0.1) -> str:
    return evaluation.adjudicate(
        primary,
        stressed_1_5={"net_sharpe": stressed},
        baseline_momentum={"net_sharpe": momentum},
        rules=prereg.ADJUDICATION_RULES,
    )["case"]


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
            ("net_without_top_5_days", -0.01),
            ("gross_pnl_without_best_currency", -0.01),
            ("share_of_folds_positive", 0.4),
            ("turnover_round_trips_per_year_per_unit_gross", 60.0),
            ("mean_leverage", 6.0),
        ],
    )
    def test_every_kill_clause_fires_on_its_own(self, field: str, value: float) -> None:
        assert _adjudicate(_summary(**{field: value})) == CASE_C

    def test_a_primary_that_does_not_beat_the_persistence_rule_is_killed(self) -> None:
        """⭐ The C08 boundary as an executable clause."""
        assert _adjudicate(_summary(net_sharpe=0.6), momentum=0.6) == CASE_C

    def test_an_increment_over_a_negative_baseline_is_not_survival(self) -> None:
        """⭐ −0.983 → +0.234 is not an edge: the primary's own Sharpe decides."""
        assert _adjudicate(_summary(net_sharpe=0.234), momentum=-0.983) == CASE_C

    def test_vol_scenarios_scale_everything_but_sharpe(self) -> None:
        summary = {
            "net_annual_return": 0.05,
            "realized_annual_vol": 0.1,
            "max_drawdown": -0.12,
            "mean_leverage": 2.6,
            "p95_leverage": 3.1,
            "net_sharpe": 0.5,
        }
        rows = evaluation.vol_scenarios(summary, 0.10)
        assert rows["vol_0.08"]["annual_net_return"] == pytest.approx(0.04)
        assert rows["vol_0.12"]["mean_leverage"] == pytest.approx(3.12)
        assert {row["net_sharpe"] for row in rows.values()} == {0.5}

    def test_measured_days_per_year(self) -> None:
        days = pd.bdate_range("2023-01-02", periods=522)
        assert evaluation.measured_days_per_year(days) == pytest.approx(261, abs=1.5)


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
        moved["max_mean_leverage"] = 50.0
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

    def test_the_digest_ignores_line_endings(self, tmp_path: Path) -> None:
        text = "a\nb\n"
        normalised_lf = "".join(line + chr(10) for line in text.splitlines())
        normalised_crlf = "".join(
            line + chr(10) for line in text.replace("\n", "\r\n").splitlines()
        )
        assert normalised_lf == normalised_crlf

    def test_the_recorded_hash_is_the_measured_one(self) -> None:
        if prereg.FROZEN_HASH == "UNFROZEN":
            pytest.skip("frozen immediately before execution")
        assert prereg.assert_frozen() == prereg.FROZEN_HASH


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
