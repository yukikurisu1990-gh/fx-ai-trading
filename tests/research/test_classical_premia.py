"""FINAL_CLASSICAL_PREMIA の book・会計・null・ledger・判定を**合成入力だけで**確かめる。

実 data の return は一切読まない（alpha を計算しない）。
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts.research.classical_premia import book, execute, ledger, prereg

U = prereg.UNIVERSE


def _inputs(seed: int = 0, days: int = 900, rates: pd.DataFrame | None = None):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2001-01-01", periods=days)
    returns = pd.DataFrame(rng.normal(0, 0.006, (days, len(U))), index=index, columns=list(U))
    returns["USD"] = 0.0
    if rates is None:
        levels = np.linspace(0.5, 6.0, len(U))
        rates = pd.DataFrame(np.tile(levels, (days, 1)), index=index, columns=list(U))
    decision = book.monthly_decision_days(index, str(index[300].date()), str(index[-1].date()))
    span = index[(index >= decision[0]) & (index < index[-1])]
    inputs = book.Inputs(
        returns=returns,
        signal_rates=rates.shift(1),
        account_rates={"policy_contemporaneous": rates, "three_month_lagged": rates},
        decision_days=decision,
        span=span,
    )
    scores = {
        "carry": book.carry_scores(inputs.signal_rates),
        "momentum": book.momentum_scores(returns),
    }
    return inputs, scores


# ----------------------------------------------------------------------
# rank weight・score
# ----------------------------------------------------------------------
def test_rank_weights_are_sum_zero_unit_gross_and_monotone():
    w = book.rank_weights(np.array([3.0, 1.0, 2.0, 5.0, 4.0, 0.0, 7.0, 6.0]))
    assert abs(w.sum()) < 1e-12
    assert abs(np.abs(w).sum() - 1.0) < 1e-12
    assert np.all(np.diff(w[np.argsort([3, 1, 2, 5, 4, 0, 7, 6])]) > 0)


def test_rank_weights_ties_and_all_equal_and_nan():
    w = book.rank_weights(np.array([0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]))
    assert w[0] == w[1]
    assert np.all(book.rank_weights(np.ones(8)) == 0)
    with pytest.raises(ValueError):
        book.rank_weights(np.array([np.nan, 1, 2, 3, 4, 5, 6, 7.0]))


def test_momentum_is_12_minus_1_sum_of_past_returns():
    inputs, scores = _inputs()
    r = inputs.returns
    t = 400
    expected = r.iloc[t - 251 : t - 20].sum()
    got = scores["momentum"].iloc[t]
    assert np.allclose(got.to_numpy(), expected.to_numpy())
    assert scores["momentum"]["USD"].dropna().eq(0).all()


def test_momentum_score_does_not_see_the_last_21_days():
    inputs, scores = _inputs()
    t = 400
    bumped = inputs.returns.copy()
    bumped.iloc[t - 20 : t + 1] += 0.5
    assert np.allclose(book.momentum_scores(bumped).iloc[t], scores["momentum"].iloc[t])


# ----------------------------------------------------------------------
# risk
# ----------------------------------------------------------------------
def test_compose_is_exact_equal_risk_contribution_and_hits_target_vol():
    rng = np.random.default_rng(1)
    a = rng.normal(size=(500, 8))
    a[:, 7] = 0
    cov = np.cov(a * 0.01, rowvar=False) * 252
    wc = book.rank_weights(rng.normal(size=8))
    wm = book.rank_weights(rng.normal(size=8))
    x, parts, info = book.compose({"carry": wc, "momentum": wm}, cov)
    assert np.allclose(x, parts["carry"] + parts["momentum"])
    rc = {f: float(parts[f] @ cov @ x) for f in parts}
    assert abs(rc["carry"] - rc["momentum"]) < 1e-12
    if not info["capped"]:
        assert abs(np.sqrt(x @ cov @ x) - prereg.RISK["target_vol"]) < 1e-12


def test_compose_caps_currency_gross():
    cov = np.eye(8) * 1e-8
    cov[7, 7] = 0.0
    wc = book.rank_weights(np.arange(8.0))
    x, _, info = book.compose({"carry": wc, "momentum": -wc[::-1]}, cov)
    assert info["capped"]
    assert abs(np.abs(x).sum() - prereg.RISK["gross_cap"]) < 1e-9


def test_covariance_uses_only_rows_up_to_the_decision_day():
    inputs, _ = _inputs()
    day = inputs.decision_days[3]
    base = book.covariances(inputs.returns, pd.DatetimeIndex([day]), list(U))[day]
    future = inputs.returns.copy()
    future.loc[future.index > day] *= 50
    again = book.covariances(future, pd.DatetimeIndex([day]), list(U))[day]
    assert np.allclose(base, again)


# ----------------------------------------------------------------------
# book: 時点・会計
# ----------------------------------------------------------------------
def test_book_has_no_lookahead_in_returns():
    inputs, scores = _inputs()
    frame = book.run(inputs, scores)
    cut = inputs.span[len(inputs.span) // 2]
    changed = inputs.returns.copy()
    changed.loc[changed.index > cut] = -changed.loc[changed.index > cut] * 3
    inputs2 = book.Inputs(
        changed, inputs.signal_rates, inputs.account_rates, inputs.decision_days, inputs.span
    )
    scores2 = {"carry": scores["carry"], "momentum": book.momentum_scores(changed)}
    frame2 = book.run(inputs2, scores2)
    early = frame.index <= cut
    assert np.allclose(frame.loc[early, "spot"], frame2.loc[early, "spot"])
    assert np.allclose(frame.loc[early, "transaction_cost"], frame2.loc[early, "transaction_cost"])


def test_exposure_is_constant_between_decision_days_and_cost_only_on_them():
    inputs, scores = _inputs()
    frame = book.run(inputs, scores)
    x = frame[[f"x_{c}" for c in U]]
    moved = (x.diff().abs().sum(axis=1) > 0).to_numpy()
    assert set(frame["exposure_day"][moved]) <= set(inputs.decision_days)
    assert (frame.loc[~frame["is_decision_day"], "transaction_cost"] == 0).all()
    assert np.allclose(x.sum(axis=1), 0.0)


def test_pnl_is_next_day_return_times_held_exposure():
    inputs, scores = _inputs()
    frame = book.run(inputs, scores)
    row = frame.iloc[10]
    x = np.array([row[f"x_{c}"] for c in U])
    assert abs(row["spot"] - float(x @ inputs.returns.loc[frame.index[10]].to_numpy())) < 1e-15


def test_carry_accrual_is_rate_differential_times_calendar_days():
    inputs, scores = _inputs()
    frame = book.run(inputs, scores)
    row = frame.iloc[5]
    x = np.array([row[f"x_{c}"] for c in U])
    level = inputs.account_rates["policy_contemporaneous"].loc[row["exposure_day"]].to_numpy() / 100
    days = (frame.index[5] - row["exposure_day"]).days
    expected = float(x @ (level - level[U.index("USD")])) * days / 365
    assert abs(row["carry_policy_contemporaneous"] - expected) < 1e-15


def test_carry_family_goes_long_high_rate_currencies():
    inputs, scores = _inputs()
    target = book.targets(inputs, scores, families=("carry",))
    first = target["carry"].iloc[0]
    assert first.iloc[-1] > 0 and first.iloc[0] < 0


def test_attributions_sum_back_to_the_lines():
    inputs, scores = _inputs()
    frame = book.run(inputs, scores)
    judged = book.judged_net(frame, "policy_contemporaneous", 0.005)
    assert np.allclose(
        book.judged_by_currency(frame, "policy_contemporaneous", 0.005).sum(axis=1), judged
    )
    assert np.allclose(
        book.judged_by_family(frame, "policy_contemporaneous", 0.005).sum(axis=1), judged
    )
    assert np.allclose(book.tc_net_by_family(frame).sum(axis=1), book.tc_net(frame))


def test_markup_charges_pair_notional_and_scales_with_cost_stress():
    inputs, scores = _inputs()
    base = book.run(inputs, scores)
    stressed = book.run(inputs, scores, cost_multiple=2.0)
    assert np.allclose(book.markup_charge(stressed, 0.01), 2 * book.markup_charge(base, 0.01))
    assert np.allclose(stressed["transaction_cost"], 2 * base["transaction_cost"])


def test_leave_one_out_universe_holds_zero_in_the_dropped_currency():
    inputs, scores = _inputs()
    frame = book.run(inputs, scores, universe=tuple(c for c in U if c != "JPY"))
    assert (frame["x_JPY"] == 0).all()
    assert np.allclose(frame[[f"x_{c}" for c in U]].sum(axis=1), 0.0)


def test_missing_rate_fails_closed():
    inputs, scores = _inputs()
    rates = inputs.account_rates["policy_contemporaneous"].copy()
    rates.loc[inputs.span[20], "AUD"] = np.nan
    broken = book.Inputs(
        inputs.returns,
        inputs.signal_rates,
        {"policy_contemporaneous": rates},
        inputs.decision_days,
        inputs.span,
    )
    with pytest.raises(ValueError):
        book.run(broken, scores)


# ----------------------------------------------------------------------
# null
# ----------------------------------------------------------------------
def test_null_shift_is_joint_and_preserves_rows():
    inputs, scores = _inputs()
    span_scores = {k: v.reindex(inputs.span) for k, v in scores.items()}
    shifted = execute.shifted_scores(span_scores, 300)
    for name in span_scores:
        assert np.allclose(shifted[name].iloc[300].to_numpy(), span_scores[name].iloc[0].to_numpy())


def test_null_shifts_are_seeded_and_at_least_a_year():
    a = execute.null_shifts(4000)
    assert a == execute.null_shifts(4000)
    assert (
        len(a) == prereg.NULL["joint_circular_shift"]["draws"]
        and min(a) >= 252
        and max(a) <= 4000 - 252
    )


# ----------------------------------------------------------------------
# 判定
# ----------------------------------------------------------------------
def _result(
    tc=0.02, judged=0.03, spot=0.03, pct=0.9, fam=(0.02, 0.01), loo=8, sharpe=0.4, years=16.0
):
    return {
        "metrics": {
            "years": years,
            "gross_spot": {"annual": spot},
            "tc_net": {"annual_return": tc},
            "judged_net_central": {
                "annual_return": judged,
                "sharpe": sharpe,
                "top_10_day_contribution": 0.3,
                "realized_vol": 0.10,
                "max_drawdown": -0.15,
                "positive_calendar_year_share": 0.6,
            },
            "judged_net_cells": {
                f"{b}|{m:.4f}": {"annual": judged} for b in execute.BASES for m in execute.MARKUPS
            },
        },
        "null": {"judged_net_central": {"observed_percentile": pct, "p_value": 1 - pct}},
        "family_contribution": {
            "carry": {
                "judged_central_annual": fam[0],
                "share_of_composite_judged": fam[0] / judged,
            },
            "momentum": {
                "judged_central_annual": fam[1],
                "share_of_composite_judged": fam[1] / judged,
            },
        },
        "leave_one_out": {
            c: {"judged_central_annual": 0.01 if i < loo else -0.01} for i, c in enumerate(U)
        },
        "effective_n": {"effective_n": 20},
    }


def test_verdict_positive_and_failures():
    assert (
        execute.research_verdict(_result())["status"] == "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"
    )
    bad_tc = execute.research_verdict(_result(tc=-0.01))
    assert bad_tc["status"] == "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
    assert bad_tc["failure_class"] == "CARRY_ONLY_POSITIVE_SPOT_NET_NOT_POSITIVE"
    assert (
        execute.research_verdict(_result(pct=0.79))["status"] == "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
    )
    assert execute.research_verdict(_result(loo=5))["status"] == "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
    assert (
        execute.research_verdict(_result(fam=(0.05, -0.02)))["status"]
        == "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
    )


def test_verdict_caveats_and_business_gap():
    v = execute.research_verdict(_result(fam=(0.028, 0.002), loo=7))
    assert "FAMILY_CONCENTRATION_CAVEAT" in v["caveats"]
    assert "CURRENCY_CONCENTRATION_CAVEAT" in v["caveats"]
    assert execute.research_verdict(_result(sharpe=0.2, years=16))["required_sharpe_gap_large"]
    assert not execute.research_verdict(_result(sharpe=0.3, years=16))["required_sharpe_gap_large"]


def test_forward_eligibility_needs_everything():
    r = _result(pct=0.97)
    f = execute.forward_eligibility(r, execute.research_verdict(r))
    assert f["F2"] == "PASS" and f["F3"] == "PASS" and f["F4"] == "PASS"
    assert (
        f["F1"].startswith("PENDING")
        and f["F6"].startswith("PENDING")
        and f["F8"].startswith("PENDING")
    )
    r2 = _result(pct=0.9)
    assert execute.forward_eligibility(r2, execute.research_verdict(r2))["F2"] == "FAIL"


# ----------------------------------------------------------------------
# ledger
# ----------------------------------------------------------------------
def test_ledger_chain_order_and_tamper_detection(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger.append("INTENT", {"freeze_digest": "a"}, path)
    with pytest.raises(ValueError):
        ledger.append("COMPLETED", {}, path)
    ledger.append("STARTED", {"head": "h"}, path)
    ledger.append("COMPLETED", {"record_sha256": "r"}, path)
    with pytest.raises(ValueError):
        ledger.append("COMPLETED", {}, path)
    ledger.verify(ledger.read(path))
    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["freeze_digest"] = "b"
    lines[0] = json.dumps(first, sort_keys=True, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ledger.verify(ledger.read(path))


# ----------------------------------------------------------------------
# 凍結の整合
# ----------------------------------------------------------------------
def test_universe_and_financing_frameworks_are_the_existing_ones():
    from scripts.research.top_five import UNIVERSE
    from scripts.research.usd_factor_financing import prereg as previous

    assert tuple(sorted(U)) == tuple(sorted(UNIVERSE))
    assert tuple(prereg.CARRY["jpy_zero_periods"]) == tuple(
        previous.FINANCING["jpy_policy_zero_periods"]
    )
    assert tuple(prereg.FINANCING["markup_band"]) == tuple(previous.FINANCING["markup_band"])
    assert prereg.FINANCING["central_markup"] == previous.FINANCING["central_markup"]


def test_forbidden_programme_tokens_are_never_outputs():
    for row in prereg.DISPOSITION:
        for token in prereg.FORBIDDEN_TOKENS:
            assert token not in row["then"] or "ではない" in row["then"]


def test_closure_covers_the_package():
    closure = prereg.code_closure()
    for name in ("driver", "execute", "book", "data", "ledger", "prereg"):
        assert f"scripts/research/classical_premia/{name}.py" in closure


def test_account_and_signal_rate_placement(monkeypatch):
    from scripts.research.classical_premia import data

    stamps = pd.date_range("2003-01-01", periods=6, freq="MS")

    def fake(slot, currency, **_):
        return pd.Series(np.arange(len(stamps), dtype=float) + U.index(currency), index=stamps), "M"

    monkeypatch.setattr(data.signals, "_load_slot", fake)
    index = pd.bdate_range("2003-01-01", "2003-06-30")
    rates = data.policy_rates(index)
    #: 1 月の値（0）は 1 月末から。1 月 30 日にはまだ無い
    assert np.isnan(rates.loc["2003-01-30", "AUD"])
    assert rates.loc["2003-01-31", "AUD"] == 0.0
    assert rates.loc["2003-02-03", "AUD"] == 0.0
    assert rates.loc["2003-02-28", "AUD"] == 1.0
    signal = data.policy_rates(index, after_month_end_days=1)
    #: signal は月末の翌暦日から（会計は月末当日から）
    assert signal.loc["2003-02-28", "AUD"] == 0.0
    assert signal.loc["2003-03-03", "AUD"] == 1.0


# ----------------------------------------------------------------------
# pre-alpha review の修正（Role 1 R2〜R5、Role 2 R-1〜R-5・N-1〜N-8 と missing tests）
# ----------------------------------------------------------------------
def test_covariance_excludes_the_decision_day_itself():
    inputs, _ = _inputs()
    day = inputs.decision_days[3]
    base = book.covariances(inputs.returns, pd.DatetimeIndex([day]), list(U))[day]
    shocked = inputs.returns.copy()
    shocked.loc[day] += 0.5
    again = book.covariances(shocked, pd.DatetimeIndex([day]), list(U))[day]
    assert np.allclose(base, again)


def test_currency_attribution_is_numeraire_free():
    """全通貨の R と金利に同じ値を足しても（numeraire を替えても）通貨別の寄与は変わらない。"""
    inputs, scores = _inputs()
    frame = book.run(inputs, scores)
    shift = pd.Series(np.linspace(-0.01, 0.01, len(inputs.returns)), index=inputs.returns.index)
    returns2 = inputs.returns.add(shift, axis=0)
    rates2 = {k: v + 3.0 for k, v in inputs.account_rates.items()}
    inputs2 = book.Inputs(returns2, inputs.signal_rates, rates2, inputs.decision_days, inputs.span)
    cov = book.covariances(inputs.returns, inputs.decision_days, list(U))
    frame2 = book.run(inputs2, scores, cov=cov)
    frame1 = book.run(inputs, scores, cov=cov)
    a = book.judged_by_currency(frame1, "policy_contemporaneous", 0.005)
    b = book.judged_by_currency(frame2, "policy_contemporaneous", 0.005)
    assert np.allclose(a.to_numpy(), b.to_numpy())
    assert np.allclose(frame1["spot"], frame2["spot"])
    assert np.allclose(
        frame1["carry_policy_contemporaneous"], frame2["carry_policy_contemporaneous"]
    )
    assert frame is not None


def test_family_cost_is_split_by_what_each_family_trades():
    inputs, scores = _inputs()
    frame = book.run(inputs, scores)
    #: carry の score が一定なら carry の target は vol の変化でしか動かない
    decision = frame[frame["is_decision_day"]].iloc[1:]
    assert (decision["cost_share__carry"] + decision["cost_share__momentum"]).round(12).eq(1).all()
    assert decision["cost_share__carry"].mean() < decision["cost_share__momentum"].mean()


def test_usd_numeraire_signs_and_nan():
    pairs = pd.DataFrame({"EUR_USD": [0.01], "USD_JPY": [0.02]}, index=[pd.Timestamp("2001-01-02")])
    for c in U:
        if c not in ("EUR", "JPY", "USD"):
            pairs[f"{c}_USD"] = 0.0
    out = book.usd_numeraire_returns(pairs)
    assert out.loc[:, "EUR"].iloc[0] == 0.01 and out.loc[:, "JPY"].iloc[0] == -0.02
    assert out.loc[:, "USD"].iloc[0] == 0.0
    pairs.iloc[0, 0] = np.nan
    with pytest.raises(ValueError):
        book.usd_numeraire_returns(pairs)


def test_leave_usd_out_and_missing_usd_rate():
    inputs, scores = _inputs()
    universe = tuple(c for c in U if c != "USD")
    frame = book.run(inputs, scores, universe=universe)
    assert (frame["x_USD"] == 0).all()
    rates = inputs.account_rates["policy_contemporaneous"].copy()
    rates.loc[inputs.span[30], "USD"] = np.nan
    broken = book.Inputs(
        inputs.returns,
        inputs.signal_rates,
        {"policy_contemporaneous": rates},
        inputs.decision_days,
        inputs.span,
    )
    with pytest.raises(ValueError):
        book.run(broken, scores, universe=universe)


def test_gross_cap_binds_in_the_book():
    inputs, scores = _inputs()
    tiny = inputs.returns * 1e-5
    inputs2 = book.Inputs(
        tiny, inputs.signal_rates, inputs.account_rates, inputs.decision_days, inputs.span
    )
    frame = book.run(inputs2, {"carry": scores["carry"], "momentum": book.momentum_scores(tiny)})
    assert frame["currency_gross"].max() <= prereg.RISK["gross_cap"] + 1e-9
    assert np.isclose(frame["currency_gross"].max(), prereg.RISK["gross_cap"])


def test_cost_counts_the_usd_leg():
    inputs, scores = _inputs()
    frame = book.run(inputs, scores)
    first = frame.iloc[0]
    x = np.array([first[f"x_{c}"] for c in U])
    assert x[U.index("USD")] != 0
    from scripts.research.continuous_portfolio import construction

    expected = np.abs(x).sum() * construction.CHARGED_ONE_WAY_BP / 10_000
    assert np.isclose(first["transaction_cost"], expected)


def test_permutation_null_is_joint_seeded_and_never_identity():
    perms = execute.null_permutations()
    assert perms == execute.null_permutations()
    assert len(perms) == prereg.NULL["currency_label_permutation"]["draws"]
    assert tuple(range(len(U))) not in perms
    inputs, scores = _inputs()
    span_scores = {k: v.reindex(inputs.span) for k, v in scores.items()}
    p = perms[0]
    out = execute.permuted_scores(span_scores, p)
    for name in span_scores:
        for i in range(len(U)):
            assert np.allclose(out[name].iloc[:, i], span_scores[name].iloc[:, p[i]])


def test_null_is_identical_serial_and_parallel(monkeypatch):
    inputs, scores = _inputs(days=700)
    spec = dict(prereg.NULL["currency_label_permutation"], draws=4)
    monkeypatch.setitem(prereg.NULL, "currency_label_permutation", spec)
    observed = {"judged_net_central": 0.0, "tc_net": 0.0}
    a = execute.null_diagnostic(inputs, scores, observed, "currency_label_permutation", workers=1)
    b = execute.null_diagnostic(inputs, scores, observed, "currency_label_permutation", workers=2)
    assert a == b


def test_business_risk_rule():
    ok = _result(sharpe=0.5)
    assert not execute.business_risk(ok)["REQUIRED_RISK_INCONSISTENT"]
    weak = _result(sharpe=0.25)  # 年 5% に vol 20% が要る
    assert execute.business_risk(weak)["REQUIRED_RISK_INCONSISTENT"]
    deep = _result(sharpe=0.5)
    deep["metrics"]["judged_net_central"]["max_drawdown"] = -0.45
    assert execute.business_risk(deep)["REQUIRED_RISK_INCONSISTENT"]


def test_disposition_is_mechanical():
    r = _result(pct=0.97, sharpe=0.45)
    v = execute.research_verdict(r)
    e = execute.forward_eligibility(r, v)
    assert execute.disposition(v, e)["preliminary"] == "A_CONDITIONAL_PENDING_F1_F6_F8"
    assert execute.disposition(v, e)["fallback_if_a_conditions_fail"].startswith("B.")
    r2 = _result(pct=0.85, sharpe=0.45)
    v2 = execute.research_verdict(r2)
    assert execute.disposition(v2, execute.forward_eligibility(r2, v2))["preliminary"].startswith(
        "B."
    )
    r3 = _result(tc=-0.01)
    v3 = execute.research_verdict(r3)
    assert execute.disposition(v3, execute.forward_eligibility(r3, v3))["preliminary"].startswith(
        "C."
    )


def test_verdict_survives_missing_values():
    r = _result()
    r["metrics"]["judged_net_central"]["sharpe"] = None
    r["null"]["judged_net_central"]["observed_percentile"] = None
    v = execute.research_verdict(r)
    assert v["status"] == "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
    assert v["required_risk"]["REQUIRED_RISK_INCONSISTENT"]


def test_frozen_digest_excludes_exactly_one_exact_line(tmp_path, monkeypatch):
    from pathlib import Path

    root = tmp_path
    driver = root / prereg.CLOSURE_ROOT
    driver.parent.mkdir(parents=True)
    body = 'x = 1\nFROZEN_DIGEST: Final[str] = "UNFROZEN"\ny = 2\n'
    driver.write_text(body, encoding="utf-8")
    monkeypatch.setattr(prereg, "_REPO", Path(root))
    base = prereg._sha_text(prereg.CLOSURE_ROOT)
    driver.write_text(body.replace("UNFROZEN", "a" * 64), encoding="utf-8")
    assert prereg._sha_text(prereg.CLOSURE_ROOT) == base
    driver.write_text(body + "FROZEN_DIGEST_X = 3\n", encoding="utf-8")
    assert prereg._sha_text(prereg.CLOSURE_ROOT) != base
    driver.write_text(body + 'FROZEN_DIGEST: Final[str] = "UNFROZEN"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        prereg._sha_text(prereg.CLOSURE_ROOT)
    driver.write_text(body.replace("y = 2", "y = 3"), encoding="utf-8")
    assert prereg._sha_text(prereg.CLOSURE_ROOT) != base


def test_git_failures_fail_closed(monkeypatch):
    import subprocess

    class Done:
        returncode = 128
        stdout = ""
        stderr = "fatal"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Done())
    with pytest.raises(SystemExit):
        ledger.dirty_paths()
    with pytest.raises(SystemExit):
        ledger.head()


def test_sha_must_be_a_commit(monkeypatch):
    monkeypatch.setattr(ledger, "git", lambda *a: "")
    with pytest.raises(SystemExit):
        ledger.head()


def test_driver_refuses_without_the_right_ledger(tmp_path, monkeypatch):
    from scripts.research.classical_premia import driver

    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(ledger, "read", lambda path=None: [])
    with pytest.raises(SystemExit):
        driver._check_common(["INTENT"])
    monkeypatch.setattr(driver, "RECORD", tmp_path / "execution.json")
    (tmp_path / "execution.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        driver._check_common(["INTENT", "STARTED"])


def test_write_atomic_never_overwrites(tmp_path):
    target = tmp_path / "a.json"
    ledger.write_atomic(target, b"1")
    with pytest.raises(SystemExit):
        ledger.write_atomic(target, b"2")
    assert target.read_bytes() == b"1"
    assert not (tmp_path / "a.json.partial").exists()


def test_jpy_fill_only_replaces_missing_inside_the_windows(monkeypatch):
    from scripts.research.classical_premia import data

    stamps = pd.date_range("1999-01-01", "2007-12-01", freq="MS")

    def fake(slot, currency, **_):
        values = pd.Series(1.0, index=stamps)
        if currency == "JPY":
            values[(stamps >= "1999-03-01") & (stamps <= "2000-07-01")] = np.nan
            values[(stamps >= "2006-09-01") & (stamps <= "2007-06-01")] = np.nan
        return values.dropna(), "M"

    monkeypatch.setattr(data.signals, "_load_slot", fake)
    index = pd.bdate_range("1999-01-01", "2007-12-31")
    rates = data.policy_rates(index)
    assert rates.loc["2000-03-01", "JPY"] == 0.0
    assert rates.loc["2000-10-02", "JPY"] == 1.0
    #: 窓の外の欠損は埋めない（staleness 75 日を超えたら NaN のまま）
    assert np.isnan(rates.loc["2007-03-01", "JPY"])


def test_data_build_refuses_rows_after_the_protected_start(monkeypatch):
    from scripts.research.classical_premia import data

    index = pd.bdate_range("2015-01-01", "2016-06-10")
    pairs = pd.DataFrame(0.0, index=index, columns=[f"{c}_USD" for c in U if c != "USD"])
    monkeypatch.setattr(data.panel, "long_span_panel", lambda: {"pair_returns": pairs})
    with pytest.raises(AssertionError):
        data.build()


def test_future_rate_shock_does_not_move_earlier_carry_targets(monkeypatch):
    from scripts.research.classical_premia import data

    stamps = pd.date_range("2003-01-01", "2003-12-01", freq="MS")

    def fake(slot, currency, **_):
        values = pd.Series(float(U.index(currency)), index=stamps)
        if currency == "AUD":
            values.loc["2003-06-01"] = 99.0
        return values, "M"

    monkeypatch.setattr(data.signals, "_load_slot", fake)
    index = pd.bdate_range("2003-01-01", "2003-12-31")
    signal = data.policy_rates(index, after_month_end_days=1)
    #: 6 月の値は 7 月 1 日から。6 月末の営業日まではまだ見えない
    assert signal.loc["2003-06-30", "AUD"] == 0.0
    assert signal.loc["2003-07-01", "AUD"] == 99.0


def test_closure_raises_on_relative_imports(tmp_path, monkeypatch):
    from pathlib import Path

    root = tmp_path
    for rel in prereg.CLOSURE_ROOTS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("from . import x\n", encoding="utf-8")
    monkeypatch.setattr(prereg, "_REPO", Path(root))
    with pytest.raises(ValueError):
        prereg.code_closure()


def test_json_output_is_strict_and_nan_free():
    from scripts.research.classical_premia import driver

    raw = driver._json_bytes({"a": float("nan"), "b": np.float64(1.5), "c": [np.inf, 2]})
    assert json.loads(raw) == {"a": None, "b": 1.5, "c": [None, 2]}


def test_compute_refuses_after_an_attempt_marker(tmp_path, monkeypatch):
    from scripts.research.classical_premia import driver

    monkeypatch.setattr(driver, "ATTEMPT", tmp_path / "execution_attempt.json")
    (tmp_path / "execution_attempt.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        driver._check_common(["INTENT", "STARTED"])
