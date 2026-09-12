"""The corpus, the features, the fold geometry and the run that used them.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The test that matters most here is causality: every feature is rebuilt on a
corpus truncated at an earlier date, and the overlapping rows must be identical
to the bit. A feature that quietly uses the whole sample — a full-sample
standardisation, a median over everything, a centred rolling window — changes
when the future is removed, and nothing else in a research pipeline notices.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.research.model_learning import (
    PAIRS_20,
    SEEN_SPANS,
    corpus,
    features,
    prereg,
)
from scripts.research.model_learning import (
    walkforward as wf,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts/research/model_learning/development.json"


@pytest.fixture(scope="module")
def panel() -> dict[str, pd.DataFrame]:
    return corpus.currency_panel()


@pytest.fixture(scope="module")
def built(panel: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return features.build(panel)


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    if not ARTIFACT.exists():
        pytest.skip("run `python -m scripts.research.model_learning.driver develop`")
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


class TestTheCorpus:
    def test_it_is_the_union_of_the_three_declared_spans_and_nothing_else(self) -> None:
        frame = corpus.load_pair("EUR_USD")
        first = pd.Timestamp(SEEN_SPANS["momentum_2021_2023"]["start"], tz="UTC")
        last = pd.Timestamp(SEEN_SPANS["development_2025"]["end"], tz="UTC") + pd.Timedelta(days=1)
        assert frame["ts"].min() >= first
        assert frame["ts"].max() < last
        assert not frame["ts"].duplicated().any()
        assert frame["ts"].is_monotonic_increasing

    def test_it_reaches_data_only_through_the_three_guarded_routes(self) -> None:
        """⭐ The loader constructs no path, no bound and no file name of its own."""
        source = (ROOT / "scripts/research/model_learning/corpus.py").read_text(encoding="utf-8")
        for forbidden in ("read_parquet", "read_csv", "Path(", "open(", "glob", "urlopen"):
            assert forbidden not in source, forbidden
        assert set(corpus.ROUTES) == set(SEEN_SPANS)

    def test_a_row_outside_its_own_span_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """⭐ The check no real cache can trip, so nothing was exercising it.

        The three caches are correct, so the guard that each route returns only
        rows inside its own declared window never fires — and a mutation removing
        it survived. A route is made to hand back one row from the wrong year.
        """
        real = corpus.ROUTES["development_2025"].load

        def leaky(pair: str) -> pd.DataFrame:
            frame = real(pair).copy()
            frame.loc[frame.index[0], "ts"] = pd.Timestamp("2016-06-02", tz="UTC")
            return frame

        monkeypatch.setattr(corpus.ROUTES["development_2025"], "load", leaky)
        with pytest.raises(corpus.CorpusError, match="outside the declared span"):
            corpus.load_pair("EUR_USD")

    def test_an_unknown_pair_is_refused(self) -> None:
        with pytest.raises(corpus.CorpusError):
            corpus.load_pair("XAU_USD")

    def test_a_thin_day_is_dropped_rather_than_carried(self) -> None:
        """A Sunday reopen carries about a dozen bars and is not a tradable day."""
        daily = corpus.daily_pair_frame("EUR_USD")
        assert (daily["bars"] >= corpus.MIN_BARS_FOR_A_TRADING_DAY).all()

    def test_the_cross_section_sums_to_zero_every_day(self, panel: dict[str, pd.DataFrame]) -> None:
        excess = panel["currency_excess_return"]
        assert float(excess.sum(axis=1).abs().max()) < 1e-12
        assert int(excess.isna().sum().sum()) == 0

    def test_the_uneven_pair_coverage_is_reported_rather_than_hidden(
        self, panel: dict[str, pd.DataFrame]
    ) -> None:
        coverage = corpus.provenance(panel)["pairs_per_currency"]
        assert sum(coverage.values()) == 2 * len(PAIRS_20)
        assert min(coverage.values()) < max(coverage.values()), (
            "the coverage is claimed to be uneven; if it is even, the claim is wrong"
        )


class TestFeaturesAreCausal:
    def test_truncating_the_future_does_not_move_a_single_past_value(
        self, built: dict[str, pd.DataFrame]
    ) -> None:
        """⭐ The one test that would catch a full-sample statistic.

        Rebuild every feature on a corpus that stops a year early. Every row the
        two builds share must be identical — not close, identical — because a
        causal feature cannot know that the rest of the sample exists.

        One column is outside its reach and is covered separately, which the next
        test says out loud rather than leaving the coverage implied.
        """
        full = corpus.currency_panel()
        cut = pd.Timestamp("2024-06-30")
        truncated = {
            name: frame[frame.index <= cut] if isinstance(frame.index, pd.DatetimeIndex) else frame
            for name, frame in full.items()
        }
        early = features.build(truncated)
        for name, frame in early.items():
            late = built[name]
            shared = frame.index.intersection(late.index)
            #: The longest trailing window is 60 days; the first rows of any build
            #: are NaN and compare equal under `equals` anyway.
            left = frame.loc[shared].astype(float)
            right = late.loc[shared].astype(float)
            difference = (left - right).abs().max().max()
            assert pd.isna(difference) or difference < 1e-12, (
                f"{name} moved by {difference} when the future was removed"
            )

    def test_the_truncation_test_does_not_cover_the_alignment_feature(self) -> None:
        """⭐ Say where the strongest test does not reach, rather than implying it does.

        `multi_timeframe_alignment_h1_h4_d1` is built from `hourly_currency_excess()`,
        which reloads the whole corpus on its own rather than from the panel it is
        handed. The truncation test therefore compares that column against itself
        and proves nothing about it. Its causality is measured here instead, by
        truncating the hourly frame directly.
        """
        hourly = features.hourly_currency_excess()
        days = pd.DatetimeIndex(
            sorted({stamp.normalize().tz_localize(None) for stamp in hourly.index})
        )
        cut = pd.Timestamp("2024-06-30", tz="UTC")
        early_days = days[days <= cut.tz_localize(None)]
        full = features._alignment(hourly, days)
        early = features._alignment(hourly[hourly.index <= cut], early_days)
        shared = early.index.intersection(full.index)
        assert len(shared) > 500
        difference = (early.loc[shared] - full.loc[shared]).abs().max().max()
        assert pd.isna(difference) or difference < 1e-12

    def test_the_calendar_distances_are_forward_known_and_non_negative(
        self, built: dict[str, pd.DataFrame]
    ) -> None:
        to_next = built["days_to_next_scheduled_g4_decision"]
        since = built["days_since_last_scheduled_g4_decision"]
        assert (to_next.dropna() >= 0).all().all()
        assert (since.dropna() >= 0).all().all()
        #: Four banks meeting eight times a year each: no gap should be long.
        assert float(to_next.max().max()) <= 45

    def test_the_common_factor_beta_is_leave_one_out(self, panel: dict[str, pd.DataFrame]) -> None:
        """⭐ A currency regressed on an average containing it is regressed on itself."""
        level = panel["currency_return"]
        loo = features.leave_one_out_common_factor(level)
        naive = level.mean(axis=1)
        for currency in level.columns:
            assert not np.allclose(loo[currency].dropna(), naive.reindex(loo.index).dropna())
            rebuilt = level.drop(columns=[currency]).mean(axis=1)
            assert np.allclose(loo[currency].dropna(), rebuilt.reindex(loo.index).dropna())

    def test_every_built_feature_is_registered_by_some_track(
        self, built: dict[str, pd.DataFrame]
    ) -> None:
        registered = {name for track in prereg.TRACKS for name in track["features"]}
        assert registered <= set(built), sorted(registered - set(built))
        unused = set(built) - registered
        assert not unused, f"built but registered by no track: {sorted(unused)}"

    def test_a_cross_sectional_z_score_uses_only_its_own_day(
        self, built: dict[str, pd.DataFrame]
    ) -> None:
        frame = built["currency_excess_return_20d_z"].dropna()
        assert float(frame.mean(axis=1).abs().max()) < 1e-9
        assert float((frame.std(axis=1, ddof=0) - 1.0).abs().max()) < 1e-9


class TestTheFoldGeometry:
    def _days(self, n: int = 1200) -> pd.DatetimeIndex:
        return pd.bdate_range("2021-04-27", periods=n)

    def test_the_test_windows_partition_the_out_of_fold_span(self) -> None:
        days = self._days()
        folds = wf.make_folds(days, initial_train_years=1.5, step_years=0.5, horizon_days=1)
        assert folds
        for earlier, later in zip(folds, folds[1:], strict=False):
            assert earlier.test_end < later.test_start
        assert folds[-1].test_end == days[-1]

    def test_the_training_side_is_purged_and_embargoed(self) -> None:
        """⭐ A label spanning the boundary must belong to neither side."""
        days = self._days()
        for horizon in (1, 5, 20):
            folds = wf.make_folds(
                days, initial_train_years=1.5, step_years=0.5, horizon_days=horizon
            )
            for fold in folds:
                gap = (fold.test_start - fold.train_end).days
                assert gap > horizon, f"horizon {horizon} leaves a gap of {gap} days"

    def test_a_purge_that_eats_the_window_is_refused(self) -> None:
        with pytest.raises(wf.WalkForwardError):
            wf.make_folds(
                self._days(400), initial_train_years=0.01, step_years=0.5, horizon_days=500
            )

    def test_the_penalty_is_solved_to_the_declared_degrees_of_freedom(self) -> None:
        rng = np.random.default_rng(0)
        design = rng.normal(size=(2000, 7))
        for target in (1.0, 3.0, 4.2, 6.5):
            penalty, achieved = wf.solve_penalty(design, target)
            assert achieved == pytest.approx(target, abs=1e-6), target
            assert penalty > 0

    def test_a_target_at_or_above_the_rank_needs_no_penalty(self) -> None:
        rng = np.random.default_rng(1)
        design = rng.normal(size=(500, 4))
        penalty, achieved = wf.solve_penalty(design, 4.0)
        assert penalty == 0.0
        assert achieved == 4.0

    def test_standardisation_comes_from_the_training_rows_only(self) -> None:
        train = np.array([[0.0, 10.0], [2.0, 20.0]])
        centre, scale = wf.standardise(train)
        assert centre.tolist() == [1.0, 15.0]
        assert scale.tolist() == [1.0, 5.0]
        constant = np.array([[3.0], [3.0]])
        _, flat = wf.standardise(constant)
        assert flat.tolist() == [1.0], "a constant column must not divide by zero"

    def test_weights_are_demeaned_and_normalised(self) -> None:
        scores = pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 2.0], "C": [5.0, 2.0]})
        weights = wf.weights_from_scores(scores)
        assert float(weights.iloc[0].sum()) == pytest.approx(0.0)
        assert float(weights.iloc[0].abs().sum()) == pytest.approx(1.0)
        #: A day with no cross-sectional spread takes no position rather than
        #: dividing by zero.
        assert float(weights.iloc[1].abs().sum()) == 0.0

    def test_the_cost_is_one_round_trip_per_open_and_close(self) -> None:
        weights = pd.DataFrame(
            {"A": [0.5, 0.5, 0.0], "B": [-0.5, -0.5, 0.0]},
            index=pd.bdate_range("2024-01-01", periods=3),
        )
        forward = pd.DataFrame(0.0, index=weights.index, columns=weights.columns)
        result = wf.evaluate(weights, forward, roundtrip_bp=10.0)
        #: Open one unit of gross, hold, close it: two position changes, one round
        #: trip each way, so ten basis points in total.
        assert float(result["cost_daily_bp"].sum()) == pytest.approx(10.0)
        assert float(result["turnover_daily"].sum()) == pytest.approx(1.0)


class TestTheRunItself:
    def test_the_run_records_the_hash_it_was_authorised_under(self, record: dict[str, Any]) -> None:
        """⭐ The specification's coverage widened after the run; the record did not.

        The review found the hash blind to the span dates, the instrument list, the
        measured volatility, the frozen ceiling, the leakage controls and every
        feature definition. Fixing that moves the current hash — and the value the
        executed run was authorised under has to stay exactly where it was.
        """
        assert record["preregistration_frozen_hash"] == prereg.FROZEN_HASH_AT_EXECUTION
        assert prereg.FROZEN_HASH != prereg.FROZEN_HASH_AT_EXECUTION

    def test_the_widened_specification_notices_what_it_used_to_miss(self) -> None:
        import dataclasses  # noqa: PLC0415

        _ = dataclasses
        spec = prereg.specification()
        assert spec["corpus"]["spans"]["momentum_2021_2023"] == ("2021-04-26", "2023-04-25")
        assert len(spec["corpus"]["pairs"]) == 20
        assert spec["economics"]["measured_annual_vol_per_gross_bp"] < 500
        assert spec["leakage_controls"]
        assert spec["feature_module_sha256"] == prereg.feature_module_digest()

    def test_no_protected_span_was_read(self, record: dict[str, Any]) -> None:
        assert record["protected_spans_read"] is False
        assert record["corpus"]["protected_spans_read"] is False
        assert record["corpus"]["observed_first_day"] >= SEEN_SPANS["momentum_2021_2023"]["start"]
        assert record["corpus"]["observed_last_day"] <= SEEN_SPANS["development_2025"]["end"]

    def test_every_registered_track_ran_once(self, record: dict[str, Any]) -> None:
        assert set(record["tracks"]) == {track["candidate_id"] for track in prereg.TRACKS}
        for block in record["tracks"].values():
            assert block["fold_diagnostics"] or block["track"] == "C"

    def test_the_fitted_degrees_of_freedom_match_the_declared_budget(
        self, record: dict[str, Any]
    ) -> None:
        """The capacity budget is enforceable only if the fit honours it."""
        declared = {track["candidate_id"]: track for track in prereg.TRACKS}
        for name, block in record["tracks"].items():
            target = declared[name]["declared_effective_parameters"]
            for fold in block["fold_diagnostics"]:
                assert fold["effective_df"] <= target + 1e-6, (name, fold)

    def test_no_track_survives_and_each_says_which_clause_failed(
        self, record: dict[str, Any]
    ) -> None:
        for name, block in record["tracks"].items():
            verdict = block["verdict"]
            assert verdict["survives"] is False, name
            assert verdict["failed_clauses"], name

    def test_track_c_is_killed_by_its_own_base_expectancy_rule(
        self, record: dict[str, Any]
    ) -> None:
        """⭐ The pre-registered rule that fires before the filter's own numbers.

        Selecting inside a base population whose unconditional expectancy is
        negative cannot be evidence about selection, and the base here is
        negative. The filter's own metrics are reported and are not the reason.
        """
        block = record["tracks"]["M13_hurdle_clearing_probability_with_learned_threshold"]
        assert block["baseline_metrics"]["net_annualised_bp"] < 0
        assert "the base opportunity taken in full" in block["baseline"]


class TestTheRegimeTermIsANoOpUnderAConstantGrossBook:
    """⭐ The finding the run produced, pinned so it cannot be quietly lost.

    Track B fits a per-state multiplicative gain on a shared score vector, and the
    book normalises each day's scores to one unit of gross exposure. A positive
    scalar multiple survives neither operation: demeaning is linear and the
    normalisation divides it straight back out. So the regime term changes nothing
    at all — its incremental information ratio is not small, it is exactly zero —
    and the run measured the hypothesis not at all.
    """

    def test_a_positive_daily_gain_leaves_the_book_identical(self) -> None:
        rng = np.random.default_rng(7)
        index = pd.bdate_range("2024-01-01", periods=50)
        scores = pd.DataFrame(rng.normal(size=(50, 8)), index=index)
        gain = pd.Series(rng.uniform(0.5, 2.0, size=50), index=index)
        plain = wf.weights_from_scores(scores)
        scaled = wf.weights_from_scores(scores.mul(gain, axis=0))
        assert np.allclose(plain.to_numpy(), scaled.to_numpy())

    def test_the_run_recorded_exactly_zero_incremental_effect(self, record: dict[str, Any]) -> None:
        block = record["tracks"]["M03_regime_conditioned_level_multi_timeframe"]
        assert block["verdict"]["incremental_net_annualised_ir"] == 0.0
        assert block["model"]["net_annualised_ir"] == block["baseline_metrics"]["net_annualised_ir"]

    def test_the_fitted_gains_never_changed_sign(self, record: dict[str, Any]) -> None:
        """The one way the term could have mattered, and it did not happen."""
        block = record["tracks"]["M03_regime_conditioned_level_multi_timeframe"]
        for fold in block["fold_diagnostics"]:
            values = [float(v) for v in fold["regime_gains"].values()]
            assert all(value > 0 for value in values), fold


def test_the_development_run_claims_no_more_than_a_development_candidate(
    record: dict[str, Any],
) -> None:
    assert record["strongest_status_reachable"] == "DEVELOPMENT_MODEL_CANDIDATE"
    blob = json.dumps(record).upper()
    for forbidden in ("EDGE_CONFIRMED", "PRODUCTION_READY", "VALIDATED"):
        assert forbidden not in blob, forbidden


def test_the_development_module_cannot_reach_protected_data() -> None:
    source = (ROOT / "scripts/research/model_learning/development.py").read_text(encoding="utf-8")
    for forbidden in ("read_parquet", "read_csv", "urlopen", "open(", "2016-", "2026-"):
        assert forbidden not in source, forbidden
