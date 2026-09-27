# ruff: noqa -- provenance: read-only transcription script written by an extraction subagent (2026-09-28); output is artifacts/research/programme/parts/
import json, os

R = r"C:\Users\yukik\fx-ai-trading"
OUT = str(
    __import__("pathlib").Path(__file__).resolve().parents[4]
    / "artifacts/research/programme/parts/ledger_B.json"
)


def J(rel):
    with open(os.path.join(R, rel), encoding="utf-8") as f:
        return json.load(f)


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
    r = {k: None for k in FIELDS}
    for k, v in kw.items():
        assert k in FIELDS, k
        r[k] = v
    rows.append(r)


def rd(x, n=4):
    return None if x is None else round(x, n)


cf = J("artifacts/research/clock_flow/frontier.json")
YEARS = {p: cf["panels"][p]["years"] for p in cf["panels"]}
panels = J("artifacts/track_a_scratch/economic_edge/panels.json")["payload"]
SPAN = {p: "..".join(panels[p]["declared_span"]) for p in panels}
PSHORT = {
    "momentum_2021_2023": "p2123",
    "supplemental_2023_2025": "p2325",
    "development_2025": "dev25",
}
PLABEL = {
    "momentum_2021_2023": "momentum_2021_2023 (deciding)",
    "supplemental_2023_2025": "supplemental_2023_2025 (deciding)",
    "development_2025": "development_2025 (may contradict, may not decide)",
}
DEV_CAVEAT = (
    "development_2025 panel: ~1,200 configurations previously searched over it (plan §3: reported, decides nothing); "
    "Track A R1 decode incident (HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN) concerns this corpus"
)
SEEN = "EXPLORATORY_SEEN_DATA panels; fresh pool, historical OOS, dead window, forward epoch untouched (as recorded)"


def cyears(p):
    return YEARS.get(p)


YEARS_SRC = "calendar_years from artifacts/research/clock_flow/frontier.json panels.<panel>.years (same span)"

# ---------------- #471 carry ----------------
EE_DOC = "docs/research/m15_economic_edge_source_expansion_results.md"
CARRY_HYP = {
    "pair_level": "C-A pair-level carry: long the pair when rate(BASE) > rate(QUOTE) by more than a fixed dead-band, short when below (plan §7)",
    "cross_sectional_k2": "C-B cross-sectional currency carry: rank 8 currencies by policy rate, long top k=2 / short bottom k=2 at currency level via PAIRS_20 (plan §7)",
    "cross_sectional_k3": "C-B cross-sectional currency carry: rank 8 currencies by policy rate, long top k=3 / short bottom k=3 at currency level via PAIRS_20 (plan §7)",
    "carry_change": "C-C carry change: signal is the change in the rate differential over a fixed lookback matched to the rebalance (plan §7)",
}
BOOK = {
    "pair_level": "PAIR_LEVEL",
    "carry_change": "PAIR_LEVEL",
    "cross_sectional_k2": "CROSS_SECTIONAL",
    "cross_sectional_k3": "CROSS_SECTIONAL",
}
verdict = J("artifacts/track_a_scratch/economic_edge/s2_carry_verdict.json")["payload"]["per_cell"]


def carry_variant(fam, reb):
    if reb == "weekly":
        if fam == "cross_sectional_k2":
            return "MODEL_VARIANT", "EE_CARRY_cross_sectional_k3_weekly_p2123"
        return "DISTINCT_MECHANISM", None
    return "HORIZON_VARIANT", f"EE_CARRY_{fam}_weekly_p2123"


for fam in ["pair_level", "cross_sectional_k2", "cross_sectional_k3", "carry_change"]:
    for reb in ["weekly", "fortnightly", "monthly"]:
        rel = f"artifacts/track_a_scratch/economic_edge/s2_carry_{fam}_{reb}.json"
        d = J(rel)["payload"]
        v = verdict[f"{fam}|{reb}"]
        vt, vo = carry_variant(fam, reb)
        for p in ["momentum_2021_2023", "supplemental_2023_2025", "development_2025"]:
            c = d[p]["x1.0"]
            dev = p == "development_2025"
            bl = c["bloc_decomposition"]
            notes = (
                f"units: pips per pair summed over the panel (not annualised). spot={c['spot_pips']}, carry={c['carry_pips']}, "
                f"gross(spot+carry)={c['gross_pips']}, cost={c['cost_pips']}, net={c['net_pips']} at cost C; "
                f"net at 2C={d[p]['x2.0']['net_pips']}. JPY bloc net {bl['JPY']['net_pips']} / non-JPY net {bl['non_JPY']['net_pips']}. "
                f"effective_independent_pairs={c['effective_independent_pairs']}; turnover = annualised_turnover; max_dd in pips; "
                f"concentration_top10 = top10_day_share of total. Cell verdict survives={v['survives']} (no uncertainty measure / null on carry layer, results §9.9). "
                + YEARS_SRC
            )
            add(
                track_id=f"EE_CARRY_{fam}_{reb}_{PSHORT[p]}",
                cycle="Economic Edge Source Expansion",
                pr="#471",
                family="carry",
                hypothesis=CARRY_HYP[fam] + f"; rebalance {reb}",
                mechanism="interest-rate differential earned as carry accrual on held FX positions (research carry from public policy rates)",
                information_source="BIS policy rates (WS_CBPOL) + FRED ECBDFR for EUR (amendment A-1)",
                price_only=False,
                book_type=BOOK[fam],
                span_label=PLABEL[p],
                span_dates=SPAN[p],
                calendar_years=cyears(p),
                financing_included="RESEARCH_CARRY_POLICY_RATES",
                financing_type="research carry accrual from public policy rates (calendar-day, 1-day lag); no broker markup, no cross-currency basis",
                turnover=c["annualised_turnover"],
                max_dd=c["max_drawdown_pips"],
                concentration_top10=c["top10_day_share"],
                stability=f"sub-period net {c['sub_period_net']}; pairs net+ {c['pairs_net_positive']}/{c['pairs']}",
                result_status="CARRY_EDGE_NOT_SUPPORTED"
                + ("" if dev else f" (cell survives={v['survives']})"),
                is_primary=not dev,
                preregistered=True,
                post_result_correction=False,
                invalid=False,
                variant_type="SECONDARY_SPAN" if dev else vt,
                variant_of=f"EE_CARRY_{fam}_{reb}_p2123" if dev else vo,
                protected_data_caveat=DEV_CAVEAT if dev else SEEN,
                closure_scope="CARRY_EDGE_NOT_SUPPORTED: research carry from public policy rates, 3 families x 3 rebalances on seen panels; broker financing, swap points, cross-currency basis referred",
                source=f"{rel} payload.{p}.x1.0 (+x2.0.net_pips); verdict artifacts/track_a_scratch/economic_edge/s2_carry_verdict.json payload.per_cell['{fam}|{reb}']; {EE_DOC} §4",
                notes=notes,
            )

# ---------------- #471 stage 4 integration ----------------
s4 = J("artifacts/track_a_scratch/economic_edge/s4_integration.json")["payload"]
REPS = ["normalised_level", "rolling_percentile", "persistence", "shock", "change"]
for p in ["momentum_2021_2023", "supplemental_2023_2025", "development_2025"]:
    dev = p == "development_2025"
    q = s4[p]
    add(
        track_id=f"EE_INT_M1_{PSHORT[p]}",
        cycle="Economic Edge Source Expansion",
        pr="#471",
        family="carry",
        hypothesis="Stage 4 M1: expected-return source alone (cross_sectional_k3 weekly carry) as integration baseline",
        mechanism="carry accrual (research carry)",
        information_source="BIS policy rates + FRED ECBDFR",
        price_only=False,
        book_type="CROSS_SECTIONAL",
        span_label=PLABEL[p],
        span_dates=SPAN[p],
        calendar_years=cyears(p),
        financing_included="RESEARCH_CARRY_POLICY_RATES",
        financing_type="research carry from public policy rates",
        result_status="OPPORTUNITY_TIMING_ADDS_NO_INCREMENTAL_VALUE (M1 baseline)",
        is_primary=False,
        preregistered=True,
        post_result_correction=False,
        invalid=False,
        variant_type="BENCHMARK",
        variant_of="EE_CARRY_cross_sectional_k3_weekly_p2123",
        protected_data_caveat=DEV_CAVEAT if dev else SEEN,
        closure_scope="Stage 4 integration: volume-state timing adds no incremental value to carry",
        source=f"artifacts/track_a_scratch/economic_edge/s4_integration.json payload.{p}.M1_*; {EE_DOC} §6",
        notes=f"units: pips per pair over panel. M1 net={q['M1_expected_return_only']} (spot {q['M1_spot_pips']}, carry {q['M1_carry_pips']}); differs slightly from s2 cell value (integration population). "
        + YEARS_SRC,
    )
    for rep in REPS:
        add(
            track_id=f"EE_INT_M3_{rep}_{PSHORT[p]}",
            cycle="Economic Edge Source Expansion",
            pr="#471",
            family="carry",
            hypothesis=f"Stage 4 M3: cross_sectional_k3 weekly carry filtered by tick-volume opportunity state ({rep}) improves on M1 net on both deciding panels",
            mechanism="carry held only in high-opportunity (volume-state) periods",
            information_source="BIS policy rates + FRED ECBDFR + M15 tick volume",
            price_only=False,
            book_type="CROSS_SECTIONAL",
            span_label=PLABEL[p],
            span_dates=SPAN[p],
            calendar_years=cyears(p),
            financing_included="RESEARCH_CARRY_POLICY_RATES",
            financing_type="research carry from public policy rates",
            incremental_ic=None,
            result_status=f"OPPORTUNITY_TIMING_ADDS_NO_INCREMENTAL_VALUE (m3_beats_m1_on_both_deciding_panels={s4['m3_beats_m1_on_both_deciding_panels'][rep]})",
            is_primary=not dev,
            preregistered=True,
            post_result_correction=False,
            invalid=False,
            variant_type="SECONDARY_SPAN" if dev else "MODEL_VARIANT",
            variant_of=f"EE_INT_M3_{rep}_p2123"
            if dev
            else "EE_CARRY_cross_sectional_k3_weekly_p2123",
            protected_data_caveat=DEV_CAVEAT if dev else SEEN,
            closure_scope="Stage 4: M3 worse than M1 in 15/15 cells; ML_NOT_JUSTIFIED",
            source=f"artifacts/track_a_scratch/economic_edge/s4_integration.json payload.{p}.M3_combined.{rep}; {EE_DOC} §6",
            notes=(
                f"units: pips per pair over panel. M3 net={q['M3_combined'][rep]} vs M1 {q['M1_expected_return_only']}; removed carry {q['removed_carry'][rep]}, removed spot {q['removed_spot'][rep]}, "
                f"trades removed share {q['trades_removed_share'][rep]}. " + YEARS_SRC
            ),
        )
        add(
            track_id=f"EE_INT_M2_{rep}_{PSHORT[p]}",
            cycle="Economic Edge Source Expansion",
            pr="#471",
            family="liquidity",
            hypothesis=f"Stage 4 M2: opportunity timing alone ({rep} tick-volume state), no expected-return view; pre-registered as expected to fail",
            mechanism="volume-state timing without direction view",
            information_source="M15 tick volume (FX price data)",
            price_only=True,
            book_type="OTHER",
            span_label=PLABEL[p],
            span_dates=SPAN[p],
            calendar_years=cyears(p),
            financing_included="NONE",
            financing_type=None,
            result_status="OPPORTUNITY_TIMING_ADDS_NO_INCREMENTAL_VALUE (M2 noise)",
            is_primary=False,
            preregistered=True,
            post_result_correction=False,
            invalid=False,
            variant_type="BENCHMARK",
            variant_of=None,
            protected_data_caveat=DEV_CAVEAT if dev else SEEN,
            closure_scope="Stage 4: M2 timing alone is noise",
            source=f"artifacts/track_a_scratch/economic_edge/s4_integration.json payload.{p}.M2_timing_only.{rep}; {EE_DOC} §6",
            notes=f"units: pips per pair over panel. M2 net={q['M2_timing_only'][rep]}. financing treatment of M2 not stated in artifact. "
            + YEARS_SRC,
        )

# ---------------- #472 macro surprise ----------------
EX_DOC = "docs/research/m15_exogenous_directional_information_results.md"
ms = J("artifacts/track_a_scratch/exogenous/s5_macro_surprise.json")["payload"]
mv = J("artifacts/track_a_scratch/exogenous/s5_macro_verdict.json")["payload"]
for cell in ["cpi_1h", "cpi_4h", "cpi_1d", "core_cpi_1h", "core_cpi_4h", "core_cpi_1d"]:
    series, hz = cell.rsplit("_", 1)
    if cell == "cpi_1h":
        vt, vo = "DISTINCT_MECHANISM", None
    elif series == "cpi":
        vt, vo = "HORIZON_VARIANT", "EX_MACRO_cpi_1h_p2123"
    else:
        vt, vo = "SENSITIVITY", f"EX_MACRO_cpi_{hz}_p2123"
    reasons = [
        r
        for r in mv["drop_reasons"]
        if r.endswith(cell) and (series == "core_cpi" or not r.endswith("core_" + cell))
    ]
    for p in ["momentum_2021_2023", "supplemental_2023_2025", "development_2025"]:
        dev = p == "development_2025"
        c = ms["cells"][p][cell]
        add(
            track_id=f"EX_MACRO_{cell}_{PSHORT[p]}",
            cycle="Exogenous Directional Information",
            pr="#472",
            family="macro surprise",
            hypothesis=f"Higher-than-expected US {'core ' if series == 'core_cpi' else ''}CPI (vs Cleveland Fed nowcast) appreciates USD: long USD on positive standardised surprise in every USD pair, entry first M15 bar strictly after 08:30 NY, hold {hz}",
            mechanism="hawkish inflation surprise -> USD appreciation",
            information_source="ALFRED CPIAUCSL/CPILFESL vintages + Cleveland Fed inflation nowcast (MODEL_NOWCAST_SURPRISE_NOT_SURVEY_SURPRISE)",
            price_only=False,
            book_type="USD_FACTOR",
            span_label=PLABEL[p],
            span_dates=SPAN[p],
            calendar_years=cyears(p),
            event_count=c["events"],
            financing_included="NONE",
            ic=rd(c["directional_ic"]),
            p_value=rd(c["permutation_p"]),
            stability=f"pairs net+ {c['pairs_net_positive']}/{c['pairs']}; pairs gross+ {c['pairs_gross_positive']}/{c['pairs']}",
            concentration_top10=rd(c["tail_share_of_net"]),
            result_status="MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED"
            + (
                ""
                if dev
                else f"; cell drop reasons {reasons}; family reasons incl. SINGLE_CURRENCY_USD_ONLY, FEWER_THAN_30_EVENTS_PER_DECIDING_PANEL"
            ),
            is_primary=not dev,
            preregistered=True,
            post_result_correction=False,
            invalid=False,
            variant_type="SECONDARY_SPAN" if dev else vt,
            variant_of=f"EX_MACRO_{cell}_p2123" if dev else vo,
            protected_data_caveat=DEV_CAVEAT if dev else SEEN,
            closure_scope="US CPI model-nowcast surprise family dropped (sign not inverted); does not refute a survey-consensus hypothesis",
            source=f"artifacts/track_a_scratch/exogenous/s5_macro_surprise.json payload.cells.{p}.{cell} (+payload.family_max_p); s5_macro_verdict.json; {EX_DOC} §5",
            notes=(
                f"units: pips per pair-event. gross={rd(c['gross_mean_pips'], 3)}, net={rd(c['net_mean_pips'], 3)}, net@2C={rd(c['net_mean_pips_double_cost'], 3)}, cost={rd(c['cost_mean_pips'], 3)}; "
                f"pair_events={c['pair_events']}; hit_rate={rd(c['hit_rate'], 3)}; family_max_p={rd(ms['family_max_p'][p][cell])}; MDE80={rd(c['detectable_at_80pct_power_pips'], 2)}; "
                f"concentration_top10 = tail_share_of_net (top-10 events / net; sign-sensitive when net<0). "
                + YEARS_SRC
            ),
        )

# ---------------- #472 COT ----------------
cot = J("artifacts/track_a_scratch/exogenous/s6_cot_cells.json")["payload"]
cotv = J("artifacts/track_a_scratch/exogenous/s6_cot_verdict.json")["payload"]
SIGDESC = {
    "net_level": ("net long share of open interest (leveraged money)", "contrarian"),
    "net_change": ("week-on-week change in net long share", "momentum (order-flow continuation)"),
    "net_percentile": ("percentile of net_level in trailing 104 weeks", "contrarian"),
    "net_extreme": ("+/-1 when net_percentile > 0.90 or < 0.10, else 0", "contrarian"),
}
for cell in [
    "net_level_1w",
    "net_change_1w",
    "net_percentile_1w",
    "net_extreme_1w",
    "net_level_4w",
    "net_change_4w",
    "net_percentile_4w",
    "net_extreme_4w",
]:
    sig, hz = cell.rsplit("_", 1)
    desc, dirn = SIGDESC[sig]
    if hz == "1w":
        vt, vo = "DISTINCT_MECHANISM", None
    else:
        vt, vo = "HORIZON_VARIANT", f"EX_COT_{sig}_1w_p2123"
    cpa = cot["cross_panel_agreement"][cell]
    for p in ["momentum_2021_2023", "supplemental_2023_2025", "development_2025"]:
        dev = p == "development_2025"
        c = cot["cells"][p][cell]
        fmp = cot["family_max_p"].get(p, {}).get(cell)
        add(
            track_id=f"EX_COT_{cell}_{PSHORT[p]}",
            cycle="Exogenous Directional Information",
            pr="#472",
            family="positioning (COT)",
            hypothesis=f"CFTC TFF leveraged-money positioning signal {sig} ({desc}), {dirn} sign (pre-registered sign={c['sign']}), held {hz}; entry first bar after Monday 20:30 UTC (A-3)",
            mechanism="crowded speculative positioning reverses"
            if dirn == "contrarian"
            else "positioning change continues (order-flow continuation)",
            information_source="CFTC Commitments of Traders, Traders in Financial Futures (weekly, as-of Tuesday)",
            price_only=False,
            book_type="CROSS_SECTIONAL",
            span_label=PLABEL[p],
            span_dates=SPAN[p],
            calendar_years=cyears(p),
            event_count=c["events"],
            financing_included="NONE",
            p_value=rd(c["permutation_p"]),
            stability=(
                f"pairs net+ {c['pairs_net_positive']}/{c['pairs']}; cross-panel per-pair Spearman {rd(cpa['spearman'], 3)}, same-sign pairs {cpa['same_sign_pairs']}/{cpa['pairs']}"
            ),
            concentration_top10=rd(c["tail_share_of_net"]),
            result_status=f"COT_EDGE_NOT_SUPPORTED; dropped {cotv['dropped'][cell]}",
            is_primary=not dev,
            preregistered=True,
            post_result_correction=True,
            invalid=False,
            variant_type="SECONDARY_SPAN" if dev else vt,
            variant_of=f"EX_COT_{cell}_p2123" if dev else vo,
            protected_data_caveat=DEV_CAVEAT if dev else SEEN,
            closure_scope="COT_EDGE_NOT_SUPPORTED: all 8 cells dropped; net_extreme_4w referred as closed negative, not near-miss"
            if cell == "net_extreme_4w"
            else "COT_EDGE_NOT_SUPPORTED: all 8 cells dropped",
            source=f"artifacts/track_a_scratch/exogenous/s6_cot_cells.json payload.cells.{p}.{cell}, payload.family_max_p, payload.cross_panel_agreement.{cell}; s6_cot_verdict.json; {EX_DOC} §7",
            notes=(
                f"units: pips per pair-event. gross={rd(c['gross_mean_pips'], 3)}, net={rd(c['net_mean_pips'], 3)}, net@2C={rd(c['net_mean_pips_double_cost'], 3)}, cost={rd(c['cost_mean_pips'], 3)}; "
                f"pair_events={c['pair_events']}; event_count = weeks with events; gross 95% CI {[rd(x, 1) for x in c['gross_mean_ci95_pips']]}; MDE80={rd(c['detectable_at_80pct_power_pips'], 1)}; "
                f"family_max_p={rd(fmp) if fmp is not None else 'not computed'}; baseline unconditional long={rd(c['baseline_unconditional_long_pips'], 3)}; "
                f"p_value = circular-shift permutation (amendment A-4 adopted after independent review of first results; point estimates unaffected) -> post_result_correction=true. "
                f"concentration_top10 = tail_share_of_net (top-10 events / net). " + YEARS_SRC
            ),
        )

# superseded first-version statistics for net_extreme_4w
for p, pv, ts in [("momentum_2021_2023", 0.199, 0.086), ("supplemental_2023_2025", 0.149, 0.107)]:
    add(
        track_id=f"EX_COT_net_extreme_4w_{PSHORT[p]}_v1",
        cycle="Exogenous Directional Information",
        pr="#472",
        family="positioning (COT)",
        hypothesis="net_extreme_4w (contrarian, 4-week hold) — first-version statistics",
        mechanism="crowded speculative positioning reverses",
        information_source="CFTC COT TFF",
        price_only=False,
        book_type="CROSS_SECTIONAL",
        span_label=PLABEL[p],
        span_dates=SPAN[p],
        calendar_years=cyears(p),
        financing_included="NONE",
        p_value=pv,
        concentration_top10=ts,
        result_status="SUPERSEDED (first version of results document)",
        is_primary=False,
        preregistered=True,
        post_result_correction=False,
        invalid=True,
        variant_type="POST_HOC_DIAGNOSTIC",
        variant_of=f"EX_COT_net_extreme_4w_{PSHORT[p]}",
        protected_data_caveat=SEEN,
        closure_scope=None,
        source=f"{EX_DOC} §1a table",
        notes="First version used free week-label permutation (anti-conservative) and a positives-only tail statistic (top-10 over positive gross), both replaced; also claimed 'passes nine of ten criteria' (withdrawn). Point estimates not restated in §1a; left null.",
    )

# ---------------- #473 expectation benchmark ----------------
EB_DOC = "docs/research/m15_expectation_benchmark_results.md (NOT on this branch; read via git show bbbcdfc — PR #473 unmerged)"
em = J("artifacts/track_a_scratch/expectation/s2_macro.json")["payload"]
for cell, vt in [
    ("pooled_1h", "DISTINCT_MECHANISM"),
    ("pooled_ex_flagged_signals_1h", "SENSITIVITY"),
]:
    for p in ["momentum_2021_2023", "supplemental_2023_2025"]:
        c = em["cells"][p][cell]
        add(
            track_id=f"EB_{cell}_{PSHORT[p]}",
            cycle="Expectation Benchmark",
            pr="#473",
            family="macro surprise",
            hypothesis=(
                "Survey-consensus surprise (actual - Forex Factory forecast) composite across US high-impact releases predicts USD direction over 1h after release; pre-registered sign fixed"
                + (
                    ""
                    if cell == "pooled_1h"
                    else " — robustness: flagged families (gdp, pce) dropped at signal level and composites rebuilt"
                )
            ),
            mechanism="macro surprise vs survey consensus -> USD repricing",
            information_source="Forex Factory calendar archive (HF Ehsanrs2/Forex_Factory_Calendar) consensus + ALFRED release dates",
            price_only=False,
            book_type="USD_FACTOR",
            span_label=PLABEL[p],
            span_dates=SPAN[p],
            calendar_years=cyears(p),
            event_count=c["events"],
            financing_included="NONE",
            ic=rd(c["directional_ic"]),
            p_value=rd(c["permutation_p"]),
            stability=f"pairs gross+ {c['pairs_gross_positive']}/{c['pairs']}",
            concentration_top10=rd(c["tail_share_of_net"]),
            result_status="SURVEY_CONSENSUS_MACRO_EDGE_NOT_SUPPORTED_ON_USD_AT_DECISION_GRADE_POWER"
            + (
                " (primary cell; drop reasons FAMILYWISE_NULL, NEGATIVE_AFTER_COST, PANEL_SIGN_REVERSAL)"
                if cell == "pooled_1h"
                else " (robustness; changes nothing)"
            ),
            is_primary=cell == "pooled_1h",
            preregistered=True,
            post_result_correction=False,
            invalid=False,
            variant_type=vt,
            variant_of=None if cell == "pooled_1h" else f"EB_pooled_1h_{PSHORT[p]}",
            protected_data_caveat=SEEN
            + "; forecast pre-release integrity rule fired (FORECAST_BEHAVIOUR_INCONSISTENT_WITH_A_PRE_RELEASE_SURVEY, Advance GDP)",
            closure_scope="Family 1 (USD survey-consensus macro surprise, 1h) closed as powered null; not a multi-currency result",
            source=f"artifacts/track_a_scratch/expectation/s2_macro.json payload.cells.{p}.{cell}, payload.family_max_p; s2_macro_verdict.json; {EB_DOC} §1/§5",
            notes=(
                f"units: pips per pair-event. gross={rd(c['gross_mean_pips'], 3)} (95% CI {[rd(x, 2) for x in c['gross_mean_ci95_pips']]}), net={rd(c['net_mean_pips'], 3)}, net@2C={rd(c['net_mean_pips_double_cost'], 3)}, cost={rd(c['cost_mean_pips'], 3)}; "
                f"MDE80={rd(c['mde_80pct_power_pips'], 2)}; IC permutation p={rd(c['directional_ic_permutation_p'])}; family_max_p={rd(em['family_max_p'][p][cell])}; pair_events={c['pair_events']}; "
                f"pooled cell ~44% jobless claims. development_2025 has no events (archive ends 2025-04-07). "
                + YEARS_SRC
            ),
        )

# ---------------- #477 Track 2 ----------------
T2_DOC = "docs/research/m15_track_2_non_usd_surprise_results.md"
t2 = J("artifacts/research/track2/stage1.json")
T2SIGN = {
    "inflation": "+1 (higher inflation hawkish -> currency up)",
    "employment": "+1 (unemployment rate / claims -1)",
    "policy_rate": "+1 (higher-than-expected rate hawkish -> currency up)",
}
for fam in ["inflation", "employment", "policy_rate"]:
    for p in ["momentum_2021_2023", "supplemental_2023_2025"]:
        c = t2["panels"][p]["families"][fam]
        g = t2["gate_v2"][fam]
        add(
            track_id=f"T2_{fam}_{PSHORT[p]}",
            cycle="Track 2 non-USD surprise",
            pr="#477",
            family="macro surprise",
            hypothesis=f"Non-USD {fam} surprise (first-release actual - pre-release consensus, z-scored) predicts the event currency's forward 1-day return vs the G10 basket; sign {T2SIGN[fam]}; entry next UTC day open",
            mechanism="hawkish surprise -> event currency appreciates vs basket (forward, day after announcement)",
            information_source="Forex Factory calendar archive (non-USD consensus/actual), date offset +5h from Stage 0",
            price_only=False,
            book_type="OTHER",
            span_label=PLABEL[p],
            span_dates=SPAN[p],
            calendar_years=cyears(p),
            effective_n=c["effective_n"],
            event_count=c["n_events"],
            financing_included="NONE",
            p_value=c["p_value_on_gross"],
            stability=f"currency breadth {c['currency_breadth']}/{c['n_currencies']}",
            concentration_top10=c["tail_share"],
            result_status=f"NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP (statistical gate pass={g['statistical'][p]['pass']}; research_feasible={g['research_feasible']})",
            is_primary=True,
            preregistered=True,
            post_result_correction=True,
            invalid=False,
            variant_type="DISTINCT_MECHANISM" if fam == "inflation" else "UNIVERSE_VARIANT",
            variant_of=None if fam == "inflation" else f"T2_inflation_{PSHORT[p]}",
            protected_data_caveat=SEEN
            + "; forecast pre-release falsification fails on the Stage-1 population (0.3621 > 0.25); no non-USD vintage archive",
            closure_scope="Not decision-grade (power); NON_USD_SURPRISE_RELATIVE_CLOSED explicitly NOT claimed",
            source=f"artifacts/research/track2/stage1.json panels.{p}.families.{fam}, gate_v2.{fam}; {T2_DOC} §3.1",
            notes=(
                f"units: bp of mid per event. gross={c['gross_bp']} (CI {c['gross_confidence_interval_bp']}), cost={c['cost_bp']}, net={c['net_bp']}; MDE={c['mde_bp']}; events/yr={c['events_per_year']}; "
                f"measured sign opposite to hypothesis (family dropped, not inverted). Second draft: B1 (+1 day offset) and B2 (Sunday sessions) fixed after review -> post_result_correction=true. "
                f"variant_type for employment/policy_rate = other primary family (UNIVERSE_VARIANT label is approximate). calendar_years 1.996 also stated in {T2_DOC} §3.3."
            ),
        )
add(
    track_id="T2_first_draft_SUMMARY",
    cycle="Track 2 non-USD surprise",
    pr="#477",
    family="macro surprise",
    hypothesis="Track 2 Stage 1 first draft (same 3 families x 2 panels)",
    mechanism=None,
    information_source="Forex Factory calendar archive",
    price_only=False,
    book_type="OTHER",
    span_label="both deciding panels",
    span_dates="2021-04-26..2025-04-24",
    financing_included="NONE",
    result_status="INVALID (all Stage 1 numbers of first draft invalid: B1 +1-day offset, B2 Sunday sessions counted)",
    is_primary=False,
    preregistered=True,
    post_result_correction=False,
    invalid=True,
    variant_type="POST_HOC_DIAGNOSTIC",
    variant_of="T2_inflation_p2123",
    protected_data_caveat=SEEN,
    closure_scope=None,
    source=f"{T2_DOC} §1, §3.2",
    notes="SUMMARY row; first-draft per-cell numbers not recorded in repo (artifact overwritten); only first-draft 1-pair round trip 3.83-7.39 bp recorded (§3.2).",
)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
ids = [r["track_id"] for r in rows]
assert len(ids) == len(set(ids))
print(len(rows))
from collections import Counter

print(Counter(r["pr"] for r in rows))
