"""Stage 2 の再現層を固定する。

**この module が無かったことがレビューの指摘だった** — `stage2_t5.json` は手作業で
作られており、生成コードが repo に無かった。だから「artefact があること」ではなく、
**artefact を作る規則**を test で押さえる。

ここで押さえるのは 4 つ。

1. 適格判定が、凍結した 3 条件**そのもの**であること（1 つでも緩めたら落ちる）
2. 回帰が、凍結が許す**ただ 1 つ**の model であり、t が正しく計算されること
3. 帰無が **circular shift** であること — shuffle にすると turnover が壊れ、
   「回転が少ないから cost を払わない」という T5 の性質まで消えてしまう
4. 感度測定が、凍結した定数を**元へ戻す**こと
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.research.top_five import prereg, signals, stage2

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "artifacts/research/top_five/stage2_t5.json"


def _panel(days: int = 400, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2021-05-03", periods=days, freq="B")
    columns = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]
    excess = pd.DataFrame(
        rng.normal(0.0, 0.004, size=(days, len(columns))), index=index, columns=columns
    )
    scores = pd.DataFrame(
        rng.normal(0.0, 1.0, size=(days, len(columns))), index=index, columns=columns
    )
    return scores, excess


class TestTheEligibilityGateIsExactlyTheFrozenThree:
    @pytest.mark.parametrize(
        ("gross", "incremental", "net", "expected"),
        [
            (0.5, 0.01, 0.05, True),
            (-0.5, 0.01, 0.05, False),
            (0.5, -0.01, 0.05, False),
            (0.5, 0.01, -0.05, False),
            (0.0, 0.01, 0.05, False),
            (0.5, 0.0, 0.05, False),
            (0.5, 0.01, 0.0, False),
        ],
    )
    def test_every_condition_is_load_bearing(
        self, gross: float, incremental: float, net: float, expected: bool
    ) -> None:
        verdict = stage2._eligibility(
            {"gross_sharpe": gross, "incremental_ic": incremental, "net_annual_return": net}
        )
        assert verdict["eligible"] is expected

    def test_it_carries_the_frozen_rule_verbatim(self) -> None:
        verdict = stage2._eligibility(
            {"gross_sharpe": 1.0, "incremental_ic": 1.0, "net_annual_return": 1.0}
        )
        assert verdict["rule"] is prereg.STAGE_2_ELIGIBILITY

    def test_the_gate_names_all_three_conditions(self) -> None:
        verdict = stage2._eligibility(
            {"gross_sharpe": 1.0, "incremental_ic": 1.0, "net_annual_return": 1.0}
        )
        assert len(verdict["checks"]) == 3


class TestTheRegressionIsTheOneModelTheFreezeAllows:
    def test_it_recovers_a_planted_coefficient(self) -> None:
        scores, excess = _panel()
        control = excess.rolling(20).sum()
        #: forward return に signal を**既知の係数で**埋め込み、取り出せることを見る。
        planted = 0.002
        forward = pd.DataFrame(
            planted * scores.to_numpy() + excess.to_numpy() * 0.05,
            index=scores.index,
            columns=scores.columns,
        )
        shifted_back = forward.shift(1)
        out = stage2._regression(scores, control, shifted_back)
        assert out["status"] == "RAN"
        assert out["signal_beta"] == pytest.approx(planted, rel=0.15)
        assert out["signal_t"] > 10.0

    def test_pure_noise_gives_a_small_t(self) -> None:
        scores, excess = _panel()
        control = excess.rolling(20).sum()
        out = stage2._regression(scores, control, excess)
        assert abs(out["signal_t"]) < 4.0

    def test_it_refuses_a_tiny_sample_instead_of_reporting_a_t(self) -> None:
        scores, excess = _panel(days=8)
        out = stage2._regression(scores, excess.rolling(2).sum(), excess)
        assert out["status"] == "INSUFFICIENT_OBSERVATIONS"
        assert "signal_t" not in out

    def test_it_discloses_that_the_t_is_overstated(self) -> None:
        """**前方補完の重複を補正していない**ことを必ず添える。"""
        scores, excess = _panel()
        out = stage2._regression(scores, excess.rolling(20).sum(), excess)
        assert "過大" in out["caveat"]

    def test_the_model_has_exactly_two_regressors_plus_intercept(self) -> None:
        scores, excess = _panel()
        out = stage2._regression(scores, excess.rolling(20).sum(), excess)
        #: 自由度が n - 3 で計算されていること（切片 + signal + control）。
        assert "control_t" in out and "signal_t" in out
        assert out["r_squared"] < 0.05


class TestTheNullPreservesTheSignalStructure:
    def test_a_circular_shift_keeps_every_value(self) -> None:
        scores, _ = _panel(days=50)
        rolled = pd.DataFrame(
            np.roll(scores.to_numpy(), 11, axis=0), index=scores.index, columns=scores.columns
        )
        for column in scores.columns:
            assert sorted(rolled[column].round(9)) == sorted(scores[column].round(9))

    def test_a_circular_shift_keeps_the_row_order(self) -> None:
        """**shuffle ではない。** 行の並びが保たれるので turnover が変わらない。"""
        scores, _ = _panel(days=50)
        values = scores.to_numpy()
        rolled = np.roll(values, 11, axis=0)
        #: 11 だけずらした先で、元の連続性がそのまま現れる。
        assert np.allclose(rolled[11:], values[:-11])


class TestTheSensitivitySweepRestoresTheFrozenConstant:
    def test_the_grid_contains_the_frozen_value(self) -> None:
        assert prereg.SIGNAL_CONSTANTS["max_staleness_days"] in stage2.STALENESS_GRID

    def test_the_constant_is_restored_even_when_the_sweep_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """**途中で落ちても凍結値へ戻すこと。** 戻し損ねると以降の測定が別設計になる。"""
        original = prereg.SIGNAL_CONSTANTS["max_staleness_days"]

        def explode(_index: pd.DatetimeIndex) -> pd.DataFrame:
            raise RuntimeError("boom")

        monkeypatch.setattr(stage2, "_usable_scores", explode)
        _scores, excess = _panel()
        with pytest.raises(RuntimeError):
            stage2._staleness_sensitivity(excess)
        assert original == prereg.SIGNAL_CONSTANTS["max_staleness_days"]
        assert original == signals.MAX_STALENESS_DAYS


class TestTheModuleDoesNotInventVocabulary:
    def test_it_writes_to_the_committed_path(self) -> None:
        assert RECORD.name == "stage2_t5.json"
        assert RECORD.parent.name == "top_five"

    def test_it_only_ever_runs_t5_on_the_recent_span(self) -> None:
        """Stage 2 は **cost が実測された唯一の span** でのみ判定する（凍結規則）。"""
        assert stage2.TRACK == "T5"
        assert stage2.SPAN == "recent"
        assert "recent span のみ" in prereg.STAGE_2_ELIGIBILITY["judged_on"]


@pytest.mark.research_data
class TestTheCommittedArtefactSaysWhatWasFound:
    @pytest.fixture(scope="class")
    def record(self) -> dict:
        return json.loads(RECORD.read_text(encoding="utf-8"))

    def test_it_carries_the_current_digest(self, record: dict) -> None:
        assert record["freeze_digest"] == prereg.freeze_digest()
        assert record["digest_as_executed"] == prereg.DIGEST_AS_EXECUTED

    def test_it_records_that_the_run_was_corrected_after_results(self, record: dict) -> None:
        assert record["post_execution_corrections"].startswith("CORRECTED_AFTER_RESULTS_WERE_SEEN")

    def test_the_gate_was_passed_but_the_null_passes_it_too(self, record: dict) -> None:
        """**通過した事実に情報が薄い**ことが artefact に残っていること。"""
        assert record["eligibility"]["eligible"] is True
        rate = record["null_calibration"]["stage_2_gate_pass_rate_under_null"]
        assert rate > 0.2, "帰無通過率が低ければ gate に意味があったことになる"

    def test_the_signal_is_not_separable_from_the_null(self, record: dict) -> None:
        assert record["null_calibration"]["p_value_on_signal_t"] > 0.05
        assert abs(record["stage_2"]["signal_t"]) < 2.0

    def test_the_null_band_covers_the_measured_sharpe(self, record: dict) -> None:
        """零情報 null の 95 パーセンタイルが実測を覆っていること。"""
        frozen = str(record["staleness_sensitivity"]["frozen_value"])
        measured = record["staleness_sensitivity"]["grid"][frozen]["net_sharpe"]
        assert record["null_calibration"]["null_net_sharpe_p95"] > measured

    def test_it_discloses_where_the_frozen_constant_sits(self, record: dict) -> None:
        """**楽観側の端であることを隠さない。**"""
        sensitivity = record["staleness_sensitivity"]
        assert sensitivity["frozen_value_rank_among_net_sharpes"] <= 2
        low, high = sensitivity["net_sharpe_range"]
        assert high - low > 0.1, "幅が小さいなら開示の必要も無い"
        assert sensitivity["sign_is_positive_at_every_grid_point"] is True

    def test_the_conclusion_refuses_both_overclaims(self, record: dict) -> None:
        conclusion = record["conclusion"]
        assert "UNDERPOWERED_FOR_CONFIRMATORY_CLAIM" in conclusion
        assert "NOT_WORTH_DEVELOPING ではない" in conclusion

    def test_the_window_is_the_one_the_doc_reports(self, record: dict) -> None:
        window = record["window"]
        assert window["days"] == 555
        assert window["distinct_signal_states"] < 40, "独立な状態は日数ではない"


def _persistent_panel(days: int = 400, hold: int = 21, seed: int = 3):
    """T5 に似せた panel — score は月次値の前方補完なので**強く持続する**。"""
    rng = np.random.default_rng(seed)
    index = pd.date_range("2021-05-03", periods=days, freq="B")
    columns = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]
    excess = pd.DataFrame(
        rng.normal(0.0, 0.004, size=(days, len(columns))), index=index, columns=columns
    )
    steps = rng.normal(0.0, 1.0, size=(days // hold + 1, len(columns)))
    held = np.repeat(steps, hold, axis=0)[:days]
    scores = pd.DataFrame(held, index=index, columns=columns)
    return scores, excess


class TestTheRegressionUsesTheRightDegreesOfFreedom:
    def test_the_t_matches_an_independently_computed_reference(self) -> None:
        """**自由度は n − 3**（切片 + signal + control）。n − 2 では t が 0.4% ずれる。"""
        scores, excess = _panel(days=18)
        control = excess.shift(1)
        out = stage2._regression(scores, control, excess)
        assert out["status"] == "RAN"

        forward = excess.shift(-1)
        rows = []
        for day in scores.index:
            s, c, f = scores.loc[day], control.loc[day], forward.loc[day]
            usable = s.notna() & c.notna() & f.notna()
            if usable.sum() >= 3:
                for currency in s.index[usable]:
                    rows.append((s[currency], c[currency], f[currency]))
        frame = pd.DataFrame(rows, columns=["signal", "control", "forward"])
        design = np.column_stack(
            [np.ones(len(frame)), frame["signal"].to_numpy(), frame["control"].to_numpy()]
        )
        target = frame["forward"].to_numpy()
        beta, *_ = np.linalg.lstsq(design, target, rcond=None)
        residual = target - design @ beta

        def t_with(dof: int) -> float:
            variance = float(residual @ residual) / dof
            stderr = np.sqrt(np.diag(np.linalg.inv(design.T @ design) * variance))
            return float(beta[1] / stderr[1])

        correct = t_with(len(frame) - 3)
        wrong = t_with(len(frame) - 2)
        assert out["signal_t"] == pytest.approx(correct, rel=1e-9)
        #: 誤った自由度と**区別できる**標本規模で測っていること。
        assert abs(out["signal_t"] - wrong) > abs(correct) * 1e-4


class TestTheNullRefusesToDestroyThePersistence:
    def test_the_shift_preserves_the_lag_one_autocorrelation(self) -> None:
        scores, _ = _persistent_panel()
        before = stage2._lag_one_autocorrelation(scores)
        after = stage2._lag_one_autocorrelation(stage2._circular_shift(scores, 37))
        assert before > 0.8, "前方補完の panel なら強く持続するはず"
        assert after == pytest.approx(before, abs=0.05)

    def test_a_shuffle_is_caught_at_runtime(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """**shuffle に置き換えたら走り切らせない。** 測っているものが変わるからである。"""
        scores, excess = _persistent_panel()
        control = excess.rolling(20).sum()

        def shuffle(frame: pd.DataFrame, _shift: int) -> pd.DataFrame:
            rng = np.random.default_rng(0)
            return pd.DataFrame(
                rng.permutation(frame.to_numpy()), index=frame.index, columns=frame.columns
            )

        monkeypatch.setattr(stage2, "_circular_shift", shuffle)
        with pytest.raises(AssertionError, match="自己相関"):
            stage2._null_calibration(scores, excess, control, observed_t=0.5, draws=2)

    def test_the_real_shift_runs_without_tripping_the_guard(self) -> None:
        scores, excess = _persistent_panel()
        control = excess.rolling(20).sum()
        out = stage2._null_calibration(scores, excess, control, observed_t=0.5, draws=2)
        assert out["method"].startswith("CIRCULAR_SHIFT")
        assert out["draws"] == 2


class TestTheRankIsComputedNotAsserted:
    @pytest.mark.parametrize(
        ("value", "values", "expected"),
        [
            (0.9, [0.9, 0.5, 0.1], 1),
            (0.5, [0.9, 0.5, 0.1], 2),
            (0.1, [0.9, 0.5, 0.1], 3),
            (0.838, [0.738, 0.62, 0.838, 0.813], 1),
        ],
    )
    def test_it_ranks_from_the_top(self, value: float, values: list, expected: int) -> None:
        assert stage2._rank_descending(value, values) == expected


@pytest.mark.research_data
class TestTheSensitivityIsMeasuredLive:
    def test_the_reported_rank_matches_the_grid_it_reports(self) -> None:
        """**順位を固定値で書かない。** 実際に走らせて、自分の grid と一致することを見る。"""
        from scripts.research.top_five import panel

        excess = panel.build()["recent"]["currency_excess_return"]
        out = stage2._staleness_sensitivity(excess)
        grid = out["grid"]
        nets = [row["net_sharpe"] for row in grid.values() if "net_sharpe" in row]
        frozen = grid[str(out["frozen_value"])]["net_sharpe"]
        assert out["frozen_value_rank_among_net_sharpes"] == stage2._rank_descending(frozen, nets)
        assert out["net_sharpe_range"] == [min(nets), max(nets)]
        assert str(out["frozen_value_rank_among_net_sharpes"]) in out["finding"]
