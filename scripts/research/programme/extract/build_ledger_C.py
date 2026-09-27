# ruff: noqa -- provenance: read-only transcription script written by an extraction subagent (2026-09-28); output is artifacts/research/programme/parts/
import json, os

R = r"C:\Users\yukik\fx-ai-trading"
OUT = str(
    __import__("pathlib").Path(__file__).resolve().parents[4]
    / "artifacts/research/programme/parts/ledger_C.json"
)


def J(p):
    return json.load(open(os.path.join(R, p), encoding="utf-8"))


FIELDS = [
    "track_id",
    "cycle",
    "pr",
    "family",
    "hypothesis",
    "mechanism",
    "information_source",
    "price_only",
    "book_type",
    "span_label",
    "span_dates",
    "calendar_years",
    "effective_n",
    "event_count",
    "gross_annual_return",
    "gross_sharpe",
    "tc_adjusted_annual_return",
    "tc_adjusted_sharpe",
    "financing_included",
    "financing_type",
    "turnover",
    "annual_cost",
    "ic",
    "incremental_ic",
    "null_percentile",
    "p_value",
    "stability",
    "loo_worst",
    "concentration_top10",
    "max_dd",
    "result_status",
    "is_primary",
    "preregistered",
    "post_result_correction",
    "invalid",
    "variant_type",
    "variant_of",
    "protected_data_caveat",
    "closure_scope",
    "source",
    "notes",
]
rows = []


def add(**kw):
    r = {f: None for f in FIELDS}
    for k, v in kw.items():
        assert k in FIELDS, k
        r[k] = v
    rows.append(r)


def pos_blocks(blocks, key="net_sharpe"):
    return f"{sum(1 for b in blocks if b[key] > 0)}/{len(blocks)} blocks net-positive"


# ---------------- Track 1 continuous portfolio (#481/#482) ----------------
T1 = "artifacts/research/continuous_portfolio/development.json"
T1_DOC = "docs/research/m15_track1_continuous_portfolio_results.md"
d = J(T1)
t1_common = dict(
    cycle="Track 1 continuous currency portfolio",
    pr="#481 (prereg+impl), #482 (execution)",
    information_source="FX prices only (seen M15 corpus 2021-04-26..2025-12-28 via 3 guarded routes); BIS policy rates for carry diagnostic only",
    price_only=True,
    book_type="CROSS_SECTIONAL",
    span_label="out-of-fold decision days inside seen corpus",
    span_dates="2023-01-17..2025-12-26",
    calendar_years=d["primary"]["summary"]["years"],
    financing_included="NONE",
    financing_type="financing excluded from P&L; policy-rate carry accrual diagnostic for primary +0.000849/yr (carry_diagnostic_primary.annual_carry_accrual)",
    preregistered=True,
    post_result_correction=False,
    invalid=False,
    protected_data_caveat="EXPLORATORY_SEEN_DATA corpus; 'oos'/out-of-fold here is walk-forward inside the seen corpus, NOT the protected historical OOS slice (not used; corpus.load_pair row check); fresh pool / dead window / forward epoch unread",
    closure_scope="CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT (Case C) - this architecture on seen development data; explicitly not FX_HAS_NO_EDGE",
)


def t1_row(tid, key_path, s, **kw):
    base = dict(t1_common)
    base.update(
        dict(
            track_id=tid,
            gross_annual_return=s["gross_annual_return"],
            gross_sharpe=s["gross_sharpe"],
            tc_adjusted_annual_return=s["net_annual_return"],
            tc_adjusted_sharpe=s["net_sharpe"],
            turnover=s.get("turnover_round_trips_per_year_per_unit_gross"),
            annual_cost=s["cost_annual_drag"],
            max_dd=s["max_drawdown"],
            concentration_top10=s.get("top_10_day_share_of_net"),
            stability=(
                "per-fold net Sharpe "
                + "/".join(str(v) for v in s["per_fold_net_sharpe"].values())
                + f"; share_of_folds_positive={s['share_of_folds_positive']}"
            )
            if "per_fold_net_sharpe" in s
            else None,
            source=f"{T1} :: {key_path}.summary; {T1_DOC}",
        )
    )
    base.update(kw)
    add(**base)


p = d["primary"]["summary"]
t1_row(
    "T1_primary",
    "primary",
    p,
    family="ML model (linear ridge currency expected-return portfolio)",
    hypothesis="A pooled ridge on 7 price features forecasting 5-day currency excess return, mapped to a capped sum-zero, factor-neutralised, banded (0.10), 10%-vol-targeted currency book, earns positive net Sharpe out of fold",
    mechanism="fitted multi-horizon price state (fit loaded -20d/-60d z, +5d z, +trend age: medium-term reversal + short-term momentum)",
    ic=d["information_diagnostics"]["raw_mu_rank_ic_5d"]["mean"],
    result_status="CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
    is_primary=True,
    variant_type="DISTINCT_MECHANISM",
    variant_of=None,
    notes="Returns/cost as fraction of capital at 10% vol target; turnover = round trips/yr/unit gross (109.729 RT/yr absolute). 7 of 9 kill clauses fired; economic band economically_weak. IC = raw mu 5d rank IC (t_non_overlapping 1.185), diagnostic only. top-10 share undefined (net negative). Ledger H-023. Model net worse than resembling unfitted reversal_20d (corr 0.6357). Folds = 6 expanding walk-forward folds inside seen corpus.",
)
b2 = d["baseline_2_linear_no_bundle"]["summary"]
t1_row(
    "T1_B2_linear_no_bundle",
    "baseline_2_linear_no_bundle",
    b2,
    family="ML model (linear ridge)",
    hypothesis="Baseline B2: same fitted mu, linear mapping, no neutralisation/cap/band/vol target (unlevered)",
    mechanism="fitted price-state model without execution bundle",
    result_status="BASELINE (primary verdict CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT)",
    is_primary=False,
    variant_type="BENCHMARK",
    variant_of="T1_primary",
    notes="Unlevered; returns as fraction of capital.",
)
for name, fam, mech in [
    ("persistence_60d", "momentum", "unfitted 60d currency-level persistence (B1)"),
    ("reversal_60d", "reversal", "unfitted 60d currency-level reversal (B1 sign flip)"),
    ("persistence_20d", "momentum", "unfitted 20d currency-level persistence"),
    ("reversal_20d", "reversal", "unfitted 20d currency-level reversal"),
    ("persistence_5d", "momentum", "unfitted 5d currency-level persistence"),
    ("reversal_5d", "reversal", "unfitted 5d currency-level reversal"),
]:
    s = d["unfitted_rules"][name]["summary"]
    corr = d["adjudication"]["unfitted_rules"][name]["pnl_correlation"]
    t1_row(
        f"T1_unfitted_{name}",
        f"unfitted_rules.{name}",
        s,
        family=fam,
        hypothesis=f"Pre-registered unfitted benchmark rule: {name.replace('_', ' ')} through the same execution layer",
        mechanism=mech,
        result_status="BENCHMARK_ONLY_POST_HOC_EXPLORATORY_NOT_A_CANDIDATE"
        if s["net_sharpe"] > 0
        else "BENCHMARK_ONLY",
        is_primary=False,
        variant_type="BENCHMARK",
        variant_of="T1_primary",
        notes=f"Daily net P&L correlation with primary {corr}. "
        + (
            "60d rules = baseline_1_unfitted_persistence/reversal (identical numbers, not duplicated). "
            if name.endswith("60d")
            else ""
        )
        + (
            "Positive reversal numbers are NOT candidates: sign-flip of closed C08 family; t~0.5-0.9; max of 6 rules; MULTI_DAY_REVERSAL_FAMILY_DROPPED_FROM_ACTIVE_EXPLORATORY_RESEARCH not reopened."
            if "reversal" in name
            else ""
        ),
    )
for name, desc in [
    ("diag_band_none", "no band"),
    ("diag_band_0_15", "band 0.15 (post-result band optimisation forbidden)"),
    ("diag_cost_1_5x", "cost x1.5 stress"),
    ("diag_cost_2x", "cost x2 stress"),
    ("diag_drawdown_governor", "drawdown governor (deployment diagnostic)"),
    ("diag_mapping_linear", "linear mapping"),
    ("diag_mapping_rank", "rank mapping"),
    ("diag_no_factor_neutralisation", "no factor neutralisation"),
    ("diag_unlevered", "unlevered"),
    ("diag_vol_target_0_08", "vol target 8%"),
    ("diag_vol_target_0_12", "vol target 12%"),
]:
    s = d["diagnostics"][name]["summary"]
    t1_row(
        f"T1_{name}",
        f"diagnostics.{name}",
        s,
        family="ML model (linear ridge currency expected-return portfolio)",
        hypothesis=f"Pre-registered one-change diagnostic of the primary book: {desc}",
        mechanism="same fitted model, one execution/cost parameter changed",
        result_status="DIAGNOSTIC_ONLY",
        is_primary=False,
        variant_type="SENSITIVITY",
        variant_of="T1_primary",
        notes=f"Diagnostic, not a candidate: {desc}.",
    )

# ---------------- Model learning (#479) ----------------
ML = "artifacts/research/model_learning/development.json"
ML_DOC = "docs/research/m15_model_learning_candidate_universe.md"
md = J(ML)
ml_meta = {
    "M01_currency_cross_sectional_ranking": (
        "A",
        "cost-adjusted next-day relative return of a currency against the basket (ranking_linear, shared coefficients)",
        "cross-sectional currency ranking on price-state features",
        True,
    ),
    "M03_regime_conditioned_level_multi_timeframe": (
        "B",
        "cost-adjusted next-day relative return with regime-conditioned gain (regime_scale_linear, multi-timeframe)",
        "regime gain on linear price-state model",
        True,
    ),
    "M13_hurdle_clearing_probability_with_learned_threshold": (
        "C",
        "P(|return| > round trip) per currency leg with in-fold learned threshold, filtering the base opportunity",
        "trade/skip filter on hurdle-clearing probability",
        False,
    ),
}
for cid, t in md["tracks"].items():
    letter, hyp, mech, po = ml_meta[cid]
    ver = t["verdict"]
    model_id = f"ML_{letter}_{cid[:3]}_model"
    common = dict(
        cycle="Model-learning candidate universe (development run)",
        pr="#479",
        family="ML model",
        mechanism=mech,
        information_source=(
            "FX prices only (seen M15 corpus)"
            if po
            else "FX prices + scheduled G4 central-bank decision calendar"
        ),
        price_only=po,
        book_type="CROSS_SECTIONAL",
        span_label="out-of-fold walk-forward inside seen corpus",
        span_dates="2023-01-18..2025-12-24",
        calendar_years=None,
        financing_included="NONE",
        financing_type="not modelled",
        preregistered=True,
        post_result_correction=False,
        invalid=False,
        protected_data_caveat="EXPLORATORY_SEEN_DATA corpus 2021-04-26..2025-12-28; historical OOS: 'one decoded row per pair; no value reached an output' (pristine claim withdrawn); fresh pool/dead window/forward epoch never read",
        closure_scope="MODEL_LEARNING_NOT_DECISION_GRADE_UNDER_CURRENT_DEVELOPMENT_GATE (Case C); run executed under the pre-correction gate - a record, not evidence",
    )
    for which, suffix, isprim, vt, vof, status in [
        (
            "model",
            "model",
            True,
            "MODEL_VARIANT",
            None,
            f"FAILED_PREREGISTERED_PASS_RULE (survives=false; failed: {', '.join(ver['failed_clauses'])}); programme status MODEL_LEARNING_NOT_DECISION_GRADE_UNDER_CURRENT_DEVELOPMENT_GATE",
        ),
        ("baseline_metrics", "baseline", False, "BENCHMARK", model_id, "BASELINE"),
        (
            "model_at_stressed_cost",
            "stressed_cost_2x",
            False,
            "SENSITIVITY",
            model_id,
            "SENSITIVITY_ONLY",
        ),
    ]:
        m = t[which]
        pf = m["per_fold_net_ir"]
        extra = ""
        if which == "model":
            extra = f" incremental_net_annualised_ir vs baseline {ver['incremental_net_annualised_ir']}."
            if letter == "B":
                extra += " Increment exactly 0.000: per-day positive regime gain is divided out by gross normalisation, so the run did not test the hypothesis (design flaw); model and baseline numbers identical."
            if letter == "C":
                extra += " Pre-registered kill: base opportunity unconditional expectation negative (-372.9 bp/yr), so a filter is not evidence; renormalisation raised turnover 49.5->142.5."
            if letter == "A":
                extra += " +1.217 over baseline only because baseline is -0.983, not edge evidence; top-10 days 3.05x net; JPY +493bp of +92bp total."
        if which == "baseline_metrics":
            h = f"Baseline ({t['baseline']}) for {cid}"
        elif which == "model_at_stressed_cost":
            h = f"{cid} model at stressed (2x) cost"
        else:
            h = hyp
        add(
            track_id=f"ML_{letter}_{cid[:3]}_{suffix}",
            **common,
            hypothesis=h,
            gross_annual_return=m["gross_annualised_bp"],
            gross_sharpe=m["gross_annualised_ir"],
            tc_adjusted_annual_return=m["net_annualised_bp"],
            tc_adjusted_sharpe=m["net_annualised_ir"],
            turnover=m["annualised_turnover"],
            annual_cost=m["cost_annualised_bp"],
            stability="per-fold net IR "
            + "/".join(str(v) for v in pf.values())
            + f"; share_of_folds_positive={m['share_of_folds_positive']}",
            concentration_top10=m["top_ten_day_share_of_net"],
            max_dd=m["maximum_drawdown_bp"],
            result_status=status,
            is_primary=isprim,
            variant_type=vt,
            variant_of=vof,
            source=f"{ML} :: tracks.{cid}.{which} (+ .verdict); {ML_DOC} §4",
            notes=(
                "UNITS: returns, cost, max_dd in bp/yr per unit gross (unlevered basket), NOT fractions; sharpe = annualised IR; turnover = annualised turnover. "
                f"days={m['days']}. Stress multiple 2.0 (design.json preregistration.cost_model.stress_multiple). calendar_years not recorded per track (prereg out_of_fold_years 3.174)."
                + extra
            ),
        )

# ---------------- T-R fast 5d (#485) ----------------
TR = "artifacts/research/market_yields/development.json"
TR_DOC = "docs/research/m15_track_r_market_yield_repricing.md"
tr = J(TR)
tr_common = dict(
    cycle="T-R market-yield repricing (fast 5d)",
    pr="#485",
    family="rates repricing",
    book_type="CROSS_SECTIONAL",
    span_label="seen development (5-currency universe CAD/EUR/GBP/JPY/USD)",
    span_dates="2021-04-27..2025-12-26",
    calendar_years=tr["feasibility_before_the_run"]["decision_years"],
    financing_included="NONE",
    financing_type="not modelled",
    preregistered=True,
    invalid=False,
    protected_data_caveat="EXPLORATORY_SEEN_DATA FX span; fresh pool, historical OOS, dead window, forward epoch not read",
    closure_scope="MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT - pre-registered fast 5d measure only, not the whole market-yield family",
)
YLD = "2Y government yields (US Treasury, Bundesbank, MoF Japan, BoE, BoC) + FX prices"
tr_meta = {
    "A_yield_repricing": (
        "TR_A",
        "5-day change in 2Y yield z-scored across 5 currencies, sign +1 (relatively rising yield -> currency rises)",
        "yield repricing shock alone",
        False,
        "DISTINCT_MECHANISM",
        None,
        YLD,
        False,
    ),
    "B_fx_momentum": (
        "TR_B",
        "FX momentum over same 5-day lookback (closed/underpowered price family) as control book",
        "FX momentum control",
        False,
        "BENCHMARK",
        "TR_C",
        "FX prices only",
        True,
    ),
    "C_residualised": (
        "TR_C",
        "Yield 5d repricing signal cross-sectionally residualised against 5d FX momentum carries incremental return (primary test)",
        "yield repricing beyond FX price information",
        True,
        "DISTINCT_MECHANISM",
        None,
        YLD,
        False,
    ),
}
loo = tr["leave_one_currency_out_net_sharpe"]
for b, (tid, hyp, mech, isprim, vt, vof, src, po) in tr_meta.items():
    x = tr["books"][b]
    s = x["summary"]
    add(
        track_id=tid,
        **tr_common,
        hypothesis=hyp,
        mechanism=mech,
        information_source=src,
        price_only=po,
        gross_annual_return=s["gross_annual_return"],
        gross_sharpe=s["gross_sharpe"],
        tc_adjusted_annual_return=s["net_annual_return"],
        tc_adjusted_sharpe=s["net_sharpe"],
        turnover=s["turnover_round_trips_per_year_per_unit_gross"],
        annual_cost=s["annual_cost"],
        ic=x["ic"]["5d"],
        stability=pos_blocks(x["blocks"]),
        loo_worst=(min(loo.values()) if tid == "TR_A" else None),
        concentration_top10=s["top_10_day_share_of_net"],
        max_dd=s["max_drawdown"],
        result_status="MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        is_primary=isprim,
        post_result_correction=False,
        variant_type=vt,
        variant_of=vof,
        source=f"{TR} :: books.{b}.summary/.ic/.blocks, leave_one_currency_out_net_sharpe, screen; {TR_DOC} §6-7",
        notes=(
            f"Turnover RT/yr/unit gross; returns fraction of capital at 10% vol, no leverage cap. IC 5d (20d={x['ic']['20d']}). "
            "Recorded on the original 8-currency layer (outside-universe exposure + 8-currency return definition); see *_repaired rows. "
            "Disclosed deviation: neutralisation moved inside 5-currency universe. "
            + (
                "Binding screen condition A net >= 0.3 failed; LOO all 5 negative (loo_worst from leave_one_currency_out_net_sharpe, attributed to A). "
                if tid == "TR_A"
                else ""
            )
            + (
                "C-B net increment +0.4345 satisfied its screen clause; C net itself negative. "
                if tid == "TR_C"
                else ""
            )
            + "Pre-run 80% power detectable net Sharpe 1.133."
        ),
    )
FR = "artifacts/research/market_yields/fast_repaired.json"
fr = J(FR)
for b, (tid, hyp, mech, isprim, vt, vof, src, po) in tr_meta.items():
    x = fr["books"][b]
    s = x["summary"]
    add(
        track_id=tid + "_repaired",
        **{
            **tr_common,
            "pr": "#486 (T-R2 prereg branch; robustness re-run of #485)",
            "cycle": "T-R market-yield repricing (fast 5d) - universe-closed re-run",
        },
        hypothesis=hyp + " - re-run through universe-closed layer",
        mechanism=mech,
        information_source=src,
        price_only=po,
        gross_annual_return=s["gross_annual_return"],
        gross_sharpe=s["gross_sharpe"],
        tc_adjusted_annual_return=s["net_annual_return"],
        tc_adjusted_sharpe=s["net_sharpe"],
        turnover=s["turnover_round_trips_per_year_per_unit_gross"],
        annual_cost=s["annual_cost"],
        stability=pos_blocks(x["blocks"]),
        concentration_top10=s["top_10_day_share_of_net"],
        max_dd=s["max_drawdown"],
        result_status="MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT (verdict_unchanged)",
        is_primary=False,
        post_result_correction=True,
        variant_type="SENSITIVITY",
        variant_of=tid,
        source=f"{FR} :: books.{b}.summary/.blocks, against_the_recorded_run; {TR_DOC} §6 universe-closed re-run",
        notes="Same frozen signal on repaired universe-closed layer with 8-pair return definition; does not replace #485 verdict; only the binding condition (A net vs 0.3) re-verified; LOO/gap stress not re-run. Same numbers reused as T-R2 book A_fast_5d_reference (not duplicated). PR attribution from git history (file introduced on T-R2 branch).",
    )

# ---------------- T-R2 slow 20d (#486 prereg, #487 execution) ----------------
R2 = "artifacts/research/market_yields/development_r2.json"
R2_DOC = "docs/research/m15_track_r2_slow_repricing.md"
r2 = J(R2)
r2_meta = {
    "B_slow_rate_state": (
        "TR2_B",
        "20-day 2Y yield repricing state alone leads FX currency excess returns",
        "slow rate state (policy-path position) that FX follows with delay",
        False,
        "HORIZON_VARIANT",
        "TR_A",
    ),
    "C_fx_price_control": (
        "TR2_C",
        "FX momentum over same 20 days (own price history) as control book",
        "FX price control",
        False,
        "BENCHMARK",
        "TR2_D",
    ),
    "D_residualised": (
        "TR2_D",
        "20-day rate state residualised cross-sectionally against 20d FX price control carries positive net (primary test)",
        "slow rate state beyond FX price information",
        True,
        "HORIZON_VARIANT",
        "TR_C",
    ),
    "E_momentum_leg_of_D": (
        "TR2_E",
        "Momentum leg of D (-beta_t*C_t run standalone) for pre-registered decomposition",
        "decomposition leg (effectively sign of -beta on control)",
        False,
        "SENSITIVITY",
        "TR2_D",
    ),
}
loo2 = r2["leave_one_currency_out_net_sharpe"]
for b, (tid, hyp, mech, isprim, vt, vof) in r2_meta.items():
    x = r2["books"][b]
    s = x["summary"]
    add(
        track_id=tid,
        cycle="T-R2 market-yield slow repricing state (20d)",
        pr="#486 (prereg), #487 (execution)",
        family="rates repricing" if tid != "TR2_C" else "momentum",
        hypothesis=hyp,
        mechanism=mech,
        information_source=("FX prices only" if tid == "TR2_C" else YLD),
        price_only=(tid == "TR2_C"),
        book_type="CROSS_SECTIONAL",
        span_label="seen development (5-currency universe CAD/EUR/GBP/JPY/USD)",
        span_dates="2021-04-27..2025-12-26",
        calendar_years=r2["feasibility_before_the_run"]["decision_years"],
        gross_annual_return=s["gross_annual_return"],
        gross_sharpe=s["gross_sharpe"],
        tc_adjusted_annual_return=s["net_annual_return"],
        tc_adjusted_sharpe=s["net_sharpe"],
        financing_included="NONE",
        financing_type="not modelled",
        turnover=s["turnover_round_trips_per_year_per_unit_gross"],
        annual_cost=s["annual_cost"],
        ic=x["ic"]["20d"],
        stability=pos_blocks(x["blocks"]),
        loo_worst=(min(loo2.values()) if tid == "TR2_D" else None),
        concentration_top10=s["top_10_day_share_of_net"],
        max_dd=s["max_drawdown"],
        result_status="MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        is_primary=isprim,
        preregistered=True,
        post_result_correction=False,
        invalid=False,
        variant_type=vt,
        variant_of=vof,
        protected_data_caveat="EXPLORATORY_SEEN_DATA FX span; fresh pool, historical OOS, dead window, forward epoch not read",
        closure_scope="MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT (Case C) for the frozen 20d formulation; span separates only net Sharpe ~1.13 at 80% power",
        source=f"{R2} :: books.{b}.summary/.ic/.blocks/.extra/.cost_stress, leave_one_currency_out_net_sharpe, screen; {R2_DOC} §3",
        notes=(
            f"Turnover RT/yr/unit gross; returns fraction of capital at 10% vol, universe-closed layer. IC 20d (5d={x['ic']['5d']}). "
            f"gross t {x['extra']['gross_t_stat']}, net t {x['extra']['net_t_stat']}, break-even cost multiple {x['extra']['break_even_cost_multiple']}, "
            f"cost stress x1.5 {x['cost_stress']['x1.5']} / x2 {x['cost_stress']['x2']}. days={s['days']}. "
            + (
                "Screen: 4 of 9 conditions failed (LOO all 5 negative, turnover 59.8>45, cost stress, 5% annual unreachable in gap stress). Top-10 share 8.46x of small positive net. "
                if tid == "TR2_D"
                else ""
            )
            + (
                "Frozen 'rate leg share' (65.0%) is not a P&L share (non-additive books; disclosed deviation). "
                if tid in ("TR2_D", "TR2_E")
                else ""
            )
        ),
    )

# ---------------- T-V valuation (#488) ----------------
TV = "artifacts/research/valuation/development.json"
TV_DOC = "docs/research/m15_track_v_real_exchange_rate_valuation.md"
tv = J(TV)
fp = tv["forecasting_power"]
tv_common = dict(
    cycle="T-V real exchange rate valuation (pre-2016 public data)",
    pr="#488",
    family="valuation",
    book_type="CROSS_SECTIONAL",
    span_label="public pre-2016 history (ECB reference rates), positions from 2003-12-31",
    span_dates="1999-01-05..2016-06-01",
    calendar_years=tv["power"]["traded_years"],
    financing_included="NONE",
    financing_type="spot-only; ECB/BIS sources carry no rates; omitted carry measured as likely negative for C (omission overstates result)",
    preregistered=True,
    invalid=False,
    protected_data_caveat="Protected pool excluded at the request (endPeriod=2016-06-01 / 2016-05); span now EXPLORATORY_SEEN_DEVELOPMENT_DATA; CPI revised not vintage (optimistic bias); one pre-prereg BIS JPY/USD 2005-06 fetch disclosed (not analysed)",
    closure_scope="REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT (Case C); cause ruled signal content, not cost; carry-add rescue forbidden",
)
FXCPI = "ECB euro reference rates + BIS consumer prices (8 G10 currencies)"
tv_meta = {
    "A_valuation": (
        "TV_A",
        "Currencies cheap in real terms vs own expanding-mean history (CPI-adjusted) earn excess return over following months (3m horizon)",
        "real exchange rate valuation alone",
        False,
        FXCPI,
        False,
        "DISTINCT_MECHANISM",
        None,
    ),
    "B_nominal_control": (
        "TV_B",
        "Nominal deviation from expanding mean (nominal mean reversion) as control book",
        "nominal mean reversion control",
        False,
        "ECB euro reference rates (FX prices only)",
        True,
        "BENCHMARK",
        "TV_C",
    ),
    "C_residualised": (
        "TV_C",
        "Real valuation signal residualised against nominal-deviation control retains positive excess return (primary test)",
        "real valuation beyond nominal mean reversion",
        True,
        FXCPI,
        False,
        "DISTINCT_MECHANISM",
        None,
    ),
}
loo3 = tv["leave_one_currency_out_net_sharpe"]
for b, (tid, hyp, mech, isprim, src, po, vt, vof) in tv_meta.items():
    x = tv["books"][b]
    s = x["summary"]
    ex = x["extra"]
    add(
        track_id=tid,
        **tv_common,
        hypothesis=hyp,
        mechanism=mech,
        information_source=src,
        price_only=po,
        gross_annual_return=s["gross_annual_return"],
        gross_sharpe=s["gross_sharpe"],
        tc_adjusted_annual_return=s["net_annual_return"],
        tc_adjusted_sharpe=s["net_sharpe"],
        turnover=s["turnover_round_trips_per_year_per_unit_gross"],
        annual_cost=s["annual_cost"],
        ic=x["ic_at_the_primary_horizon"],
        incremental_ic=(
            fp["incremental_ic_of_valuation_beyond_the_nominal_control"]["mean"]
            if tid == "TV_A"
            else None
        ),
        stability=pos_blocks(x["blocks"])
        + f"; positive calendar years {x['concentration']['positive_calendar_years']}/{x['concentration']['calendar_years']}",
        loo_worst=(min(loo3.values()) if tid == "TV_C" else None),
        concentration_top10=s["top_10_day_share_of_net"],
        max_dd=s["max_drawdown"],
        result_status="REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT",
        is_primary=isprim,
        post_result_correction=False,
        variant_type=vt,
        variant_of=vof,
        source=f"{TV} :: books.{b}.summary/.blocks/.extra/.concentration/.cost_stress, forecasting_power, leave_one_currency_out_net_sharpe, screen; {TV_DOC} §3",
        notes=(
            f"Leak-removed (quarterly CPI look-ahead fixed) numbers. Turnover round trips/yr/unit gross; returns fraction of capital at 10% vol. "
            f"3m rank IC NW t {fp['ic'][b]['newey_west_t']}. gross t {ex['gross_t_stat']}, net t {ex['net_t_stat']}, break-even cost x{ex['break_even_cost_multiple']}, cost stress x2 {x['cost_stress']['x2']} / x3 {x['cost_stress']['x3']}. "
            f"share_of_turnover_from_the_signal {ex['share_of_turnover_from_the_signal']} (rest vol-targeter re-levering). 80% power detectable net Sharpe {tv['power']['detectable_net_sharpe_at_80pct_power']}. "
            + (
                "incremental_ic = IC(A)-IC(B) = -0.0557, NW t -3.34: valuation significantly worse than nominal control (pre-registered main question). "
                if tid == "TV_A"
                else ""
            )
            + (
                "Screen: 6 of 12 conditions failed; LOO 4 of 8 negative; CHF 153.9% of gross; top-5 days 124.9% of net (SNB 2015-01-15 = 41.1%); tercile order reversed; IC NW t -2.25. Doc §3.2 table says blocks 2/6 but artifact screen.positive_blocks=3 and block list has 3 positive (value used here from artifact). "
                if tid == "TV_C"
                else ""
            )
        ),
    )
lk = tv["as_the_frozen_text_described_the_source"]["summaries"]
for b in ["A_valuation", "C_residualised"]:
    s = lk[b]
    m = tv_meta[b]
    add(
        track_id=m[0] + "_leak_included",
        **{**tv_common, "invalid": True},
        hypothesis=m[1] + " - as the frozen text described the source (quarterly CPI look-ahead)",
        mechanism=m[2],
        information_source=m[4],
        price_only=False,
        gross_annual_return=s["gross_annual_return"],
        gross_sharpe=s["gross_sharpe"],
        tc_adjusted_annual_return=s["net_annual_return"],
        tc_adjusted_sharpe=s["net_sharpe"],
        turnover=s["turnover_round_trips_per_year_per_unit_gross"],
        annual_cost=s["annual_cost"],
        concentration_top10=s["top_10_day_share_of_net"],
        max_dd=s["max_drawdown"],
        result_status="SUPERSEDED_LEAKAGE (verdict REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT)",
        is_primary=False,
        post_result_correction=False,
        variant_type="SENSITIVITY",
        variant_of=m[0],
        source=f"{TV} :: as_the_frozen_text_described_the_source.summaries.{b}; {TV_DOC} §0.2",
        notes="Contains AU/NZ quarterly CPI look-ahead (51 of 151 decision months); superseded by the leak-removed row. B unchanged (no quarterly CPI) so not duplicated.",
    )
rm = tv["robustness_median_anchor"]
for b in ["A_valuation", "B_nominal_control", "C_residualised"]:
    s = rm[b]
    m = tv_meta[b]
    add(
        track_id=m[0] + "_median_anchor",
        **tv_common,
        hypothesis=m[1] + " - pre-declared robustness anchor (expanding median)",
        mechanism=m[2],
        information_source=m[4],
        price_only=m[5],
        gross_annual_return=s["gross_annual_return"],
        gross_sharpe=s["gross_sharpe"],
        tc_adjusted_annual_return=s["net_annual_return"],
        tc_adjusted_sharpe=s["net_sharpe"],
        turnover=s["turnover_round_trips_per_year_per_unit_gross"],
        annual_cost=s["annual_cost"],
        concentration_top10=s["top_10_day_share_of_net"],
        max_dd=s["max_drawdown"],
        result_status="REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT",
        is_primary=False,
        post_result_correction=False,
        variant_type="SENSITIVITY",
        variant_of=m[0],
        source=f"{TV} :: robustness_median_anchor.{b}; {TV_DOC} §3.2",
        notes="Pre-declared single robustness anchor; screen clause 'sign unchanged under anchor' satisfied for C.",
    )

for r in rows:
    assert list(r.keys()) == FIELDS
ids = [r["track_id"] for r in rows]
assert len(ids) == len(set(ids))
with open(OUT + ".tmp", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
os.replace(OUT + ".tmp", OUT)
print(len(rows))
print(ids)
