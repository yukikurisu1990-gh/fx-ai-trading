# ruff: noqa -- provenance: read-only transcription script written by an extraction subagent (2026-09-28); output is artifacts/research/programme/parts/
import json
from pathlib import Path

REPO = Path(r"C:\Users\yukik\fx-ai-trading")
OUT = Path(
    str(
        __import__("pathlib").Path(__file__).resolve().parents[4]
        / "artifacts/research/programme/parts/ledger_D.json"
    )
)


def load(p):
    return json.loads((REPO / p).read_text(encoding="utf-8"))


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


def row(**kw):
    r = {f: None for f in FIELDS}
    for k, v in kw.items():
        assert k in FIELDS, k
        r[k] = v
    return r


def r4(x):
    return None if x is None else round(float(x), 6)


PANEL_DATES = {"long": "1999-01-05..2016-06-01", "recent": "2021-04-27..2025-12-26"}
PANEL_NOTE = "span_dates = panel span (ECB ref rates long / guarded M15 caches recent); scored window may be shorter (see days)."
EXFIN = "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING (per usd_factor_financing financing audit)"


def loo_min(m):
    loo = m.get("leave_one_currency_out_net_sharpe")
    return r4(min(loo.values())) if loo else None


def ns_summary(v, key="net_sharpe"):
    ns = v.get("nuisance_sensitivity") or {}
    out = []
    for c, s in ns.items():
        grid = s.get("grid", {})
        vals = {g: x.get(key) for g, x in grid.items()}
        out.append(f"{c}={vals}")
    return "; ".join(out)


rows = []

# ---------------- Top-Five (#490) ----------------
tf = load("artifacts/research/top_five/development.json")
st2 = load("artifacts/research/top_five/stage2_t5.json")
TF_SRC = "artifacts/research/top_five/development.json results.{k}.metrics; docs/research/m15_top_five_final_report_2026_09_21.md §6"
TF_META = {
    "T1": dict(
        family="risk-off",
        hypothesis="S05: equity volatility (z-scored VIX shock) projected on frozen betas (JPY/CHF +, AUD/NZD -) predicts G10 FX",
        mechanism="risk repricing spills into funding currencies (JPY/CHF)",
        information_source="CBOE VIX close (lag 2bd long / 1bd recent)",
        price_only=False,
        status="T1_S05_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        fc={"long": "COST_FAILURE", "recent": "COST_FAILURE"},
    ),
    "T2": dict(
        family="terms of trade",
        hypothesis="S06: crude-oil terms of trade predicts commodity currencies",
        mechanism="oil price shocks change commodity exporters' terms of trade",
        information_source="U.S. EIA WTI (weekly publication, lag 7bd)",
        price_only=False,
        status="T2_S06_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        fc={"long": "SIGNAL_FAILURE", "recent": "COST_FAILURE"},
    ),
    "T4": dict(
        family="network / lead-lag",
        hypothesis="S10: currency-network propagation predicts G10 FX",
        mechanism="shocks propagate across the currency network with a lag",
        information_source="FX prices only",
        price_only=True,
        status="T4_S10_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        fc={
            "long": "SIGNAL_FAILURE + COST_FAILURE (track)",
            "recent": "SIGNAL_FAILURE + COST_FAILURE (track)",
        },
    ),
    "T5": dict(
        family="flow",
        hypothesis="S26: cross-border portfolio flows (TIC S1) predict USD",
        mechanism="net foreign purchases of US securities drive USD demand",
        information_source="U.S. Treasury TIC S1 monthly (used from end of m+2), staleness cap 75 calendar days",
        price_only=False,
        status="T5_S26_POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE",
        fc={},
    ),
}
TF_CAVEAT = (
    "C-1: signals._two_year had read protected-pool/forward-epoch parquet rows (3 recent-span T3 scores affected) — closed before the reported numbers; "
    "cycle qualifier CORRECTED_AFTER_RESULTS_WERE_SEEN_NOT_A_CLEAN_PREREGISTERED_RUN"
)
TF_CLOSURE = (
    "2026-09-22 ruling: T1–T4 low-turnover redesign / horizon smoothing rescue forbidden; T5 not run further; "
    "TIC/capital-flow direction is NOT a family closure"
)
for k, v in tf["results"].items():
    track, span = v["track"], v["span"]
    m = v.get("metrics")
    if track == "T3":
        hyp = v.get("hypothesis") or k.split("_")[-1]
        h = "T3-H1" if "H1" in k else "T3-H2"
        meta = dict(
            family="rates repricing / yield curve",
            hypothesis=(
                "S02 "
                + h
                + ": sovereign curve steepening -> currency "
                + ("appreciation" if h == "T3-H1" else "depreciation")
            ),
            mechanism="sovereign curve shape (10y-2y) signals rate expectations; both signs pre-registered",
            information_source="10y/2y sovereign yields (UST, Bundesbank, BoE, BoC, SNB)",
            price_only=False,
        )
        tid = f"TOP5_T3_{h[-2:]}_{span}"
        if m is None:
            rows.append(
                row(
                    track_id=tid,
                    cycle="Top-Five",
                    pr="#490",
                    book_type="CROSS_SECTIONAL",
                    span_label=span,
                    span_dates=PANEL_DATES[span],
                    result_status="T3_S02_DATA_NOT_DECISION_GRADE",
                    is_primary=True,
                    preregistered=True,
                    post_result_correction=True,
                    invalid=False,
                    variant_type="DISTINCT_MECHANISM" if h == "T3-H1" else "SIGN_VARIANT",
                    variant_of=None if h == "T3-H1" else f"TOP5_T3_H1_{span}",
                    protected_data_caveat=TF_CAVEAT,
                    closure_scope=TF_CLOSURE,
                    source=f"artifacts/research/top_five/development.json results.{k} (verdict DATA_NOT_DECISION_GRADE, days 0); final report §6 T3",
                    notes="2y leg not available for enough currencies 1999–2016 (median cross-section width 3); no metrics recorded.",
                    **{
                        kk: meta[kk]
                        for kk in [
                            "family",
                            "hypothesis",
                            "mechanism",
                            "information_source",
                            "price_only",
                        ]
                    },
                )
            )
            continue
        status = "T3_S02_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        fc = "COST_FAILURE (both signs, recent)"
    else:
        meta = TF_META[track]
        tid = f"TOP5_{track}_{span}"
        status = meta["status"]
        fc = meta["fc"].get(span)
    notes = [
        f"Sharpe annualised; returns annual fraction; turnover = round trips/yr (levered), per-unit-gross {r4(m['turnover_per_unit_gross'])}; days {m['days']}.",
        "No primary/secondary span designated in Top-Five; both spans pre-registered (Stage-2 eligibility judged on recent only).",
        "net = NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING; panel spot-only, CARRY_LEG_ABSENT_ON_BOTH_SPANS_SPOT_ONLY.",
        f"cost_stress x1.5/x2 net Sharpe {v['cost_stress']['cost_x1.5']['net_sharpe']:.4f}/{v['cost_stress']['cost_x2.0']['net_sharpe']:.4f}.",
    ]
    if fc:
        notes.append(f"failure class: {fc}.")
    pval = None
    eff = None
    extra_src = ""
    caveat = TF_CAVEAT
    if track == "T5":
        notes.append(
            "book is USD-directional (mechanism redesign report: T5 was the only prior track not USD-neutralised)."
        )
        caveat += "; REVISION_CAVEAT TIC_PUBLISHED_FILE_CARRIES_CURRENT_REVISIONS_NOT_THE_VINTAGE_AVAILABLE_AT_DECISION_TIME; C-2 staleness constant 75 chosen after results"
        if span == "recent":
            nc = st2["null_calibration"]
            pval = nc["p_value_on_signal_t"]
            eff = st2["window"]["distinct_signal_states"]
            notes.append(
                f"scored window {st2['window']['first']}..{st2['window']['last']} ({st2['window']['years']}y); effective_n = distinct_signal_states (24)."
            )
            notes.append(
                f"p_value = circular-shift permutation p on Stage-2 signal t (t={st2['stage_2']['signal_t']:.3f}, overstated); null net Sharpe mean {nc['null_net_sharpe_mean']}, p95 {nc['null_net_sharpe_p95']}; Stage-2 gate null pass rate {nc['stage_2_gate_pass_rate_under_null']}; MDE95 1.321 > observed. Status UNDERPOWERED_FOR_CONFIRMATORY_CLAIM."
            )
            sg = st2["staleness_sensitivity"]
            notes.append(
                f"nuisance (max_staleness_days, 9 pts): net Sharpe range {sg['net_sharpe_range']}; frozen 75 ranks 1st."
            )
            extra_src = "; artifacts/research/top_five/stage2_t5.json null_calibration / window / staleness_sensitivity; final report §7"
        else:
            notes.append("scored window 1999-06-30..2016-06-01 per final report §6 T5.")
    if track == "T3":
        notes.append(
            f"H1/H2 are exact mirrors (PnL corr -0.993); rename gate vs (-Δ2y) book abs corr {v['rename_gate']['abs_corr']:.3f} DISTINCT; turnover 1.66x frozen assumption."
        )
    rows.append(
        row(
            track_id=tid,
            cycle="Top-Five",
            pr="#490",
            family=meta["family"],
            hypothesis=meta["hypothesis"],
            mechanism=meta["mechanism"],
            information_source=meta["information_source"],
            price_only=meta["price_only"],
            book_type="USD_FACTOR" if track == "T5" else "CROSS_SECTIONAL",
            span_label=span,
            span_dates=PANEL_DATES[span],
            calendar_years=m["years"],
            effective_n=eff,
            gross_annual_return=r4(m["gross_annual_return"]),
            gross_sharpe=r4(m["gross_sharpe"]),
            tc_adjusted_annual_return=r4(m["net_annual_return"]),
            tc_adjusted_sharpe=r4(m["net_sharpe"]),
            financing_included="NONE",
            financing_type=EXFIN,
            turnover=r4(m["turnover_round_trips_per_year"]),
            annual_cost=r4(m["annual_cost"]),
            ic=r4(m["ic"]),
            incremental_ic=r4(m["incremental_ic"]),
            null_percentile=None,
            p_value=pval,
            stability=m["positive_temporal_blocks"],
            loo_worst=loo_min(m),
            concentration_top10=r4(m["top_10_day_contribution"]),
            max_dd=r4(m["max_drawdown"]),
            result_status=status,
            is_primary=True,
            preregistered=True,
            post_result_correction=True,
            invalid=False,
            variant_type=("SIGN_VARIANT" if track == "T3" and "H2" in k else "DISTINCT_MECHANISM"),
            variant_of=(f"TOP5_T3_H1_{span}" if track == "T3" and "H2" in k else None),
            protected_data_caveat=caveat,
            closure_scope=TF_CLOSURE,
            source=TF_SRC.format(k=k) + extra_src,
            notes=" ".join(notes),
        )
    )

# ---------------- next-five (#491/#492 + execution PR) ----------------
NF_META = {
    "U1": dict(
        family="flow (trade balance)",
        hypothesis="S29: improving goods trade balance -> currency appreciation",
        mechanism="trade surplus improvement = real-economy home-currency buying",
        information_source="ALFRED / OECD MEI goods trade balance (8 ccy; used from end m+2)",
        primary="long",
    ),
    "U2": dict(
        family="central-bank balance sheet",
        hypothesis="S25: relatively faster central-bank balance-sheet expansion -> currency depreciation",
        mechanism="relative money-supply expansion oversupplies the currency",
        information_source="Fed H.4.1, ECB (ALFRED), BoJ, SNB, BoC total assets (5 ccy)",
        primary="long",
    ),
    "U3": dict(
        family="central-bank communication",
        hypothesis="S27: hawkish shift in policy-statement tone -> currency appreciation",
        mechanism="statement tone leads the next policy move",
        information_source="Fed/ECB/BoJ statement text, frozen lexicon (JPY whole-page, D-6)",
        primary="recent",
    ),
    "U4": dict(
        family="official flow (reserves)",
        hypothesis="S31: FX-reserve accumulation -> currency depreciation",
        mechanism="reserve accumulation = selling home currency / buying foreign",
        information_source="ALFRED / IMF reserves excluding gold (6 ccy, recent 5)",
        primary="long",
    ),
    "U5": dict(
        family="risk-off (credit)",
        hypothesis="S07: widening US HY credit spread -> safe-haven currency appreciation",
        mechanism="HY spread widening = funding stress, leads safe-haven (USD/JPY/CHF) demand",
        information_source="ALFRED / ICE BAMLH0A0HYM2 US HY OAS (recent only, license)",
        primary="recent",
    ),
}
NF_CAVEAT = (
    "D-5: bulk responses (H.4.1 zip, SNB cube, BoJ, Fed JSON) incl. protected-period rows parsed in memory then cut before save; "
    "C-4 monthly stamps 2016-06-01 / 2025-12-01 were saved (dropped on read in run4); FX fresh pool / OOS / dead / forward not read"
)
NF_CLOSURE = "NOT_SUPPORTED is for the frozen formulation and span; U1..U5 rescues (horizon/sign/subset/smoothing/staleness/threshold/lag/feature/low-turnover/leverage/nonlinear) forbidden (FORBIDDEN_U1_U5_RESCUES)"
for fname, invalid in [("development_run2.json", True), ("development_run4.json", False)]:
    d = load(f"artifacts/research/next_five/{fname}")
    tag = "run2" if invalid else "run4"
    for k, v in d["results"].items():
        track, span = v["track"], v["span"]
        meta = NF_META[track]
        tid = f"NF_{track}_{span}" + ("_run2_INVALID" if invalid else "")
        is_primary = span == meta["primary"]
        verdict = d["verdicts"][track]
        if invalid:
            status = (
                verdict["status"]
                + " [INVALID_ALL_TRACKS_SUPERSEDED_BY_POST_ALPHA_CORRECTIONS_C1_C5]"
            )
        else:
            status = verdict["status"]
        common = dict(
            track_id=tid,
            cycle="next-five",
            pr="#491/#492/next-five execution PR (branch research/m15-next-five-execution)",
            family=meta["family"],
            hypothesis=meta["hypothesis"],
            mechanism=meta["mechanism"],
            information_source=meta["information_source"],
            price_only=False,
            book_type="CROSS_SECTIONAL",
            span_label=span,
            span_dates=PANEL_DATES[span],
            preregistered=True,
            post_result_correction=not invalid,
            invalid=invalid,
            protected_data_caveat=NF_CAVEAT
            + (
                "; run2 recent spans of U1/U2/U4 and other_span_gross_sign contain protected-period content (C-2/C-4)"
                if invalid
                else ""
            ),
            closure_scope=NF_CLOSURE,
        )
        if "metrics" not in v:
            rows.append(
                row(
                    **common,
                    result_status=v["verdict"],
                    is_primary=is_primary,
                    variant_type="DISTINCT_MECHANISM" if is_primary else "SECONDARY_SPAN",
                    variant_of=None
                    if is_primary
                    else f"NF_{track}_{meta['primary']}" + ("_run2_INVALID" if invalid else ""),
                    source=f"artifacts/research/next_five/{fname} results.{k}",
                    notes=v.get("why"),
                )
            )
            continue
        m = v["metrics"]
        nd = v.get("null_diagnostic") or {}
        notes = [
            f"{tag}; days {m['days']}; MDE95 {m.get('detection_floor_mde95')}; turnover = round trips/yr (levered), per-unit-gross {r4(m['turnover_per_unit_gross'])}.",
            "net = NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING; spot-only panel.",
            f"failure class {verdict['failure_class']}; null_label {verdict['null_label']}; economics {verdict['economics_label']}.",
            f"distinct_signal_states {v.get('distinct_signal_states')} (not an effective-N).",
        ]
        if nd:
            notes.append(
                f"null: circular shift {nd['draws']} draws seed {nd['seed']}; null p05/p50/p95 {nd.get('null_net_sharpe_p05')}/{nd.get('null_net_sharpe_p50')}/{nd.get('null_net_sharpe_p95')}."
            )
        nss = ns_summary(v)
        if nss:
            notes.append("nuisance net Sharpe grid: " + nss)
        if invalid:
            notes.append(
                "INVALID first run (corrections.INVALIDATED_RECORDS); numbers kept as a record of what ran, not results."
            )
        else:
            notes.append(
                "qualifier POST_EXECUTION_SHARED_DEFECT_CORRECTED_EXPLORATORY_RESULT (mechanism_redesign/prior_cycle.py); second alpha measurement after C-1..C-6."
            )
        if track == "U2" and span == "recent" and not invalid:
            notes.append(
                "secondary span, not used for verdict; sign flipped vs run2 (-0.516) after C-2/C-4."
            )
        rows.append(
            row(
                **common,
                calendar_years=m["years"],
                effective_n=None,
                gross_annual_return=r4(m["gross_annual_return"]),
                gross_sharpe=r4(m["gross_sharpe"]),
                tc_adjusted_annual_return=r4(m["net_annual_return"]),
                tc_adjusted_sharpe=r4(m["net_sharpe"]),
                financing_included="NONE",
                financing_type=EXFIN,
                turnover=r4(m["turnover_round_trips_per_year"]),
                annual_cost=r4(m["annual_cost"]),
                ic=r4(m["ic"]),
                incremental_ic=r4(m["incremental_ic"]),
                null_percentile=nd.get("observed_percentile"),
                p_value=nd.get("p_value"),
                stability=m["positive_temporal_blocks"],
                loo_worst=loo_min(m),
                concentration_top10=r4(m["top_10_day_contribution"]),
                max_dd=r4(m["max_drawdown"]),
                result_status=status,
                is_primary=is_primary,
                variant_type="DISTINCT_MECHANISM" if is_primary else "SECONDARY_SPAN",
                variant_of=None
                if is_primary
                else f"NF_{track}_{meta['primary']}" + ("_run2_INVALID" if invalid else ""),
                source=f"artifacts/research/next_five/{fname} results.{k}.metrics / .null_diagnostic; verdicts.{track}"
                + (
                    "; scripts/research/next_five/corrections.py INVALIDATED_RECORDS"
                    if invalid
                    else "; docs/research/m15_next_five_final_report_2026_09_24.md"
                ),
                notes=" ".join(notes),
            )
        )

# ---------------- mechanism redesign (#494) ----------------
mr = load("artifacts/research/mechanism_redesign/development.json")
MR_META = {
    "M15": dict(
        family="carry",
        hypothesis="M15 dollar carry: while average foreign rates exceed US rates the dollar factor pays a carry premium (Lustig–Roussanov–Verdelhan)",
        mechanism="risk premium on the dollar factor",
        information_source="ALFRED OECD MEI 3m interbank rates (8 ccy), BIS policy-rate fill",
        book="USD_FACTOR",
        status="INVALID_IMPLEMENTATION_BOOK_MISMATCH",
        hist="M15_M15_POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE",
        invalid=True,
    ),
    "M11": dict(
        family="macro momentum",
        hypothesis="M11 macro data momentum: currencies of countries with relatively larger inflation acceleration and unemployment decline appreciate (Dahlquist–Hasseltoft)",
        mechanism="gradual monthly macro arrival + limited attention -> under-reaction",
        information_source="OECD CPI YoY (EUR from HICP) + harmonised unemployment (ALFRED)",
        book="CROSS_SECTIONAL",
        status="POSITIVE_EXPLORATORY_NOT_DECISION_GRADE",
        hist="M11_M11_POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE",
        invalid=False,
    ),
    "M16": dict(
        family="macro momentum",
        hypothesis="M16 US vs rest-of-world macro momentum -> dollar: faster US macro improvement lifts the dollar factor (USD component of M11 score)",
        mechanism="USD component of macro momentum that the XS book neutralised",
        information_source="OECD CPI YoY + unemployment (ALFRED), same inputs as M11",
        book="USD_FACTOR",
        status="INVALID_IMPLEMENTATION_BOOK_MISMATCH",
        hist="M16_M16_MARGINAL_DEVELOPMENT_CANDIDATE",
        invalid=True,
    ),
    "M01": dict(
        family="rates / policy gap",
        hypothesis="M01 Taylor gap: gap between fundamentals-implied and actual policy rate predicts FX",
        mechanism="market anchors on observed rate differentials; lags fundamentals-implied path",
        information_source="CPI, unemployment (ALFRED), BIS policy rates (SDMX)",
        book="CROSS_SECTIONAL",
        status="POSITIVE_EXPLORATORY_NOT_DECISION_GRADE",
        hist="M01_M01_POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE",
        invalid=False,
    ),
    "M10": dict(
        family="liquidity",
        hypothesis="M10 liquidity premium: currencies with deteriorating liquidity (bid/ask) earn a premium",
        mechanism="liquidity risk premium",
        information_source="bid/ask from seen M15 caches (FX quotes)",
        book="CROSS_SECTIONAL",
        status="NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        hist="M10_M10_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        invalid=False,
    ),
}
MR_CAVEAT = (
    "D-M1 ALFRED metadata pages parsed with 2026 latest obs; D-M2 EPU responses parsed/rejected; D-M3 lead read 2026 BoJ policy decision "
    "(JPY_RATE_RELATED_FORWARD_CONFIRMATION_CONTAMINATED_BY_EXTERNAL_INFORMATION_EXPOSURE); CPI YoY denominators in fresh pool saved; FX protected spans not read"
)
for k, v in mr["results"].items():
    track, span = v["track"], v["span"]
    meta = MR_META[track]
    closure = mr["verdicts"][track]["closure_scope"]
    tid = f"MR_{track}_{span}"
    base = dict(
        track_id=tid,
        cycle="mechanism redesign",
        pr="#494",
        family=meta["family"],
        hypothesis=meta["hypothesis"],
        mechanism=meta["mechanism"],
        information_source=meta["information_source"],
        price_only=(track == "M10"),
        book_type=meta["book"],
        span_label=span,
        span_dates=PANEL_DATES[span],
        preregistered=True,
        post_result_correction=False,
        invalid=meta["invalid"],
        protected_data_caveat=MR_CAVEAT,
        closure_scope=closure,
    )
    if "metrics" not in v:
        rows.append(
            row(
                **base,
                result_status=v["verdict"],
                is_primary=False,
                variant_type="SECONDARY_SPAN",
                variant_of=f"MR_{track}_recent",
                source=f"artifacts/research/mechanism_redesign/development.json results.{k}",
                notes=v.get("why"),
            )
        )
        continue
    m = v["metrics"]
    p = v["pnl_decomposition"]
    nd = v.get("null_diagnostic") or {}
    tc = round(p["annual_spot_gross"] - p["annual_spread_cost"], 5)
    notes = [
        f"tc_adjusted = annual_spot_gross ({p['annual_spot_gross']}) - annual_spread_cost ({p['annual_spread_cost']}); tc_adjusted_sharpe = pnl_decomposition.spot_only_net_sharpe; gross = spot-only.",
        f"RECORDED judged net (NET_INCLUDING_APPROXIMATE_INTEREST_DIFFERENTIAL_AND_ASSUMED_MARKUP): net_annual_return {r4(m['net_annual_return'])}, net Sharpe {r4(m['net_sharpe'])}, gross incl carry {r4(m['gross_annual_return'])} / Sharpe {r4(m['gross_sharpe'])}; carry {p['annual_carry']}/yr, assumed markup financing {p['annual_financing']}/yr (0.25%/yr markup); total annual_cost {r4(m['annual_cost'])}.",
        "null percentile/p, stability, LOO, concentration, maxDD are on the judged (carry+markup) P&L, not the spot-only P&L.",
        f"days {m['days']}; MDE95 {m.get('detection_floor_mde95')}; turnover round trips/yr, per-unit-gross {r4(m['turnover_per_unit_gross'])}.",
    ]
    nss = ns_summary(v)
    if nss:
        notes.append("nuisance net Sharpe grid: " + nss)
    if meta["invalid"]:
        notes.append(
            f"recorded verdict kept as history: {meta['hist']}; book ran as USD vs AUD/CAD/CHF (EUR/GBP/JPY/NZD always 0) instead of USD vs 7-ccy basket; band 0.05 sensitivity row = as-designed book, POST_HOC_EXPLORATORY."
        )
    else:
        notes.append(
            f"recorded run status {mr['verdicts'][track]['status']}; failure class {mr['verdicts'][track]['failure_class']}."
        )
    rows.append(
        row(
            **base,
            calendar_years=m["years"],
            effective_n=m.get("effective_independent_observations"),
            gross_annual_return=p["annual_spot_gross"],
            gross_sharpe=p["spot_only_gross_sharpe"],
            tc_adjusted_annual_return=tc,
            tc_adjusted_sharpe=p["spot_only_net_sharpe"],
            financing_included="NONE",
            financing_type="spot - spread only (recorded judged net incl. approximate carry + assumed 0.25% markup given in notes)",
            turnover=r4(m["turnover_round_trips_per_year"]),
            annual_cost=p["annual_spread_cost"],
            ic=r4(m["ic"]),
            incremental_ic=r4(m["incremental_ic"]),
            null_percentile=nd.get("observed_percentile"),
            p_value=nd.get("p_value"),
            stability=m["positive_temporal_blocks"],
            loo_worst=loo_min(m),
            concentration_top10=r4(m["top_10_day_contribution"]),
            max_dd=r4(m["max_drawdown"]),
            result_status=meta["status"],
            is_primary=v["is_primary_span"],
            variant_type="DISTINCT_MECHANISM" if v["is_primary_span"] else "SECONDARY_SPAN",
            variant_of=None if v["is_primary_span"] else f"MR_{track}_long",
            source=(
                f"artifacts/research/mechanism_redesign/development.json results.{k}.pnl_decomposition / .metrics / .null_diagnostic; "
                "scripts/research/mechanism_redesign/post_run.py INVALIDATED / VALID_TRACK_STATUS; docs/research/m15_mechanism_redesign_final_report_2026_09_24.md"
            ),
            notes=" ".join(notes),
        )
    )

# ---------------- USD-factor corrected (#495) ----------------
uf = load("artifacts/research/usd_factor_financing/development.json")
UF_STATUS = {
    "M15": "M15_CORRECTED_FINANCING_NOT_DECISION_GRADE",
    "M16": "M16_CORRECTED_POSITIVE_EXPLORATORY_NOT_DECISION_GRADE",
}
UF_CAVEAT = (
    "D-M3 applies more directly (JPY policy rate in primary carry accounting): JPY_RATE_RELATED_FORWARD_CONFIRMATION_CONTAMINATED_BY_EXTERNAL_INFORMATION_EXPOSURE; "
    "M16 inherits mechanism-redesign disclosures (CPI YoY denominators, HICP 2025=100, SA coefficients, GBP lag); FX protected spans not read"
)
for k, v in uf["results"].items():
    track, span = v["track"], v["span"]
    meta = MR_META[track]
    prim = v["is_primary_span"]
    p = v["pnl_decomposition"]
    nd = v.get("null_diagnostic") or {}
    cells = {c: (x["annual"], x["sharpe"]) for c, x in p["total_economic"].items()}
    ns_ex = ns_summary(v, "ex_financing_sharpe")
    ns_tot = ns_summary(v, "total_central_sharpe")
    common_notes = [
        f"qualifier {uf['qualifier']} (run after M16's prior results were seen; long central values known pre-run).",
        f"8-cell total economic (annual, Sharpe) by carry basis|markup per pair notional: {cells}; sign consistent across cells: {p['total_sign_consistent_across_all_cells']}; breakeven markup {p['breakeven_markup_per_pair_notional']}; pnl_source {p['pnl_source']['label']}.",
        f"carry/yr {p['annual_carry']}; spread cost/yr {p['annual_spread_cost']}.",
    ]
    if track == "M15" and span == "recent":
        common_notes.append(
            "recent span is always long USD and identical to constant_long_usd benchmark — not evidence for M15 (post_run FINAL_STATUS)."
        )
    for view in ["exfin", "total"]:
        mk = "metrics_ex_financing" if view == "exfin" else "metrics_total_central"
        m = v[mk]
        mt = v["metrics_total_central"]
        nv = nd.get("ex_financing" if view == "exfin" else "total_central") or {}
        notes = list(common_notes)
        notes.append(
            f"days {m['days']}; turnover round trips/yr, per-unit-gross {r4(m['turnover_per_unit_gross'])}; MDE95 {mt.get('detection_floor_mde95')}."
        )
        if nv:
            notes.append(
                f"null ({view}): circular shift 1000 draws seed 20260925, p05/p50/p95 {nv['null_p05']}/{nv['null_p50']}/{nv['null_p95']}."
            )
        nss = ns_ex if view == "exfin" else ns_tot
        if nss:
            notes.append("nuisance grid: " + nss)
        if view == "total" and "development_economics" in v:
            notes.append(
                f"development_economics (central) {v['development_economics']['checks']}; adverse endpoint core_satisfied {v['development_economics_adverse_endpoint']['core_satisfied']}."
            )
        is_p = prim and view == "total"
        if is_p:
            vt, vo = "REPLICATION", f"MR_{track}_long"
            notes.append(
                "variant_type REPLICATION here = post-result implementation-corrected re-run on the SAME seen data (basket-unit rebalance, USD-numeraire routing, new carry/markup accounting), not new data."
            )
        elif view == "exfin":
            vt, vo = "SENSITIVITY", f"USDF_{track}_{span}_total"
            notes.append(
                "ex-financing accounting view (pre-registered second null statistic), not the judged total."
            )
        else:
            vt, vo = "SECONDARY_SPAN", f"USDF_{track}_long_total"
        rows.append(
            row(
                track_id=f"USDF_{track}_{span}_{view}",
                cycle="USD-factor financing (corrected M15/M16)",
                pr="#495",
                family=meta["family"],
                hypothesis=meta["hypothesis"],
                mechanism=meta["mechanism"],
                information_source=meta["information_source"]
                + ("; BIS policy rates (carry accounting)" if view == "total" else ""),
                price_only=False,
                book_type="USD_FACTOR",
                span_label=span,
                span_dates=PANEL_DATES[span],
                calendar_years=m["years"],
                effective_n=mt.get("effective_independent_observations"),
                gross_annual_return=r4(m["gross_annual_return"]),
                gross_sharpe=r4(m["gross_sharpe"]),
                tc_adjusted_annual_return=r4(m["net_annual_return"]),
                tc_adjusted_sharpe=r4(m["net_sharpe"]),
                financing_included="NONE" if view == "exfin" else "OTHER",
                financing_type=(
                    EXFIN
                    if view == "exfin"
                    else "APPROXIMATE_RESEARCH_FINANCING central cell: contemporaneous policy-rate carry - 0.5%/yr markup per pair notional (not actual OANDA financing)"
                ),
                turnover=r4(m["turnover_round_trips_per_year"]),
                annual_cost=r4(m["annual_cost"]),
                ic=r4(m["ic"]),
                incremental_ic=r4(
                    m.get("incremental_ic") if m.get("incremental_ic") is not None else None
                ),
                null_percentile=nv.get("observed_percentile"),
                p_value=nv.get("p_value"),
                stability=m["positive_temporal_blocks"],
                loo_worst=loo_min(m),
                concentration_top10=r4(m["top_10_day_contribution"]),
                max_dd=r4(m["max_drawdown"]),
                result_status=UF_STATUS[track],
                is_primary=is_p,
                preregistered=True,
                post_result_correction=True,
                invalid=False,
                variant_type=vt,
                variant_of=vo,
                protected_data_caveat=UF_CAVEAT,
                closure_scope="report recommends closing both; no same-family variants on seen data; never CONFIRMED, no forward/fresh (§30)",
                source=(
                    f"artifacts/research/usd_factor_financing/development.json results.{k}.{mk} / .pnl_decomposition / .null_diagnostic; "
                    "scripts/research/usd_factor_financing/post_run.py FINAL_STATUS; docs/research/m15_usd_factor_financing_final_report_2026_09_24.md"
                ),
                notes=" ".join(notes),
            )
        )

OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(rows))
from collections import Counter

print(Counter(r["cycle"] for r in rows))
