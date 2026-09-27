# ruff: noqa -- provenance: read-only transcription script written by an extraction subagent (2026-09-28); output is artifacts/research/programme/parts/
import json

KEYS = [
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
M = "C:/Users/yukik/.claude/projects/C--Users-yukik-fx-ai-trading/memory/"
D = "docs/design/"
rows = []


def r(**k):
    d = {x: None for x in KEYS}
    d.update(
        financing_included="NONE",
        price_only=True,
        book_type="PAIR_LEVEL",
        is_primary=True,
        preregistered=False,
        post_result_correction=False,
        invalid=False,
        variant_type="DISTINCT_MECHANISM",
    )
    d.update(k)
    rows.append(d)


P9INV = "Invalidated 2026-05-03: all Phase 9 closure verdicts (9.10..9.X-O) treated as suspect/invalid - measured on a buggy pipeline (M1+C1+C2+C3 leakage/pipeline bugs); positive Sharpes regarded as leakage artefacts (memory project_phase9_invalidation_2026_05_03.md)."
P9SRC_INV = M + "project_phase9_invalidation_2026_05_03.md"
P9 = "Phase 9 (pre-invalidation)"
ML = "ML model"
fx = "FX prices only (OANDA bars)"
r(
    track_id="P9_10_SELECTOR_cost_gate",
    cycle=P9,
    family=ML,
    hypothesis="Multi-pair ML SELECTOR keeps net Sharpe >= 0.20 and net PnL > 0 after realistic spread",
    mechanism="LightGBM direction model + argmax pair SELECTOR, mid labels",
    information_source=fx,
    gross_sharpe=0.343,
    tc_adjusted_sharpe=-0.076,
    result_status="NO-GO",
    invalid=True,
    source=D
    + "phase9_10_closure_memo.md (status line; line ~66 gross 0.343/0.346); "
    + D
    + "phase9_15_closure_memo.md verdict table (v3 mid label 1pip: -0.076 NO-GO); "
    + P9SRC_INV,
    notes="Gross 0.343 (EUR/USD) / 0.346 (SELECTOR); net -0.076 is the v3 (1pip spread) row cited in phase9_15 memo; gross-to-net gap ~-0.42. Sharpe unit per v-series backtest. "
    + P9INV,
)
r(
    track_id="P9_12_bidask_labels",
    cycle=P9,
    family=ML,
    hypothesis="Bid/ask-aware labels (B-2) lift SELECTOR above cost gate",
    mechanism="LightGBM SELECTOR with bid/ask labels (v5)",
    information_source=fx,
    tc_adjusted_sharpe=0.160,
    result_status="SOFT GO",
    invalid=True,
    variant_type="MODEL_VARIANT",
    variant_of="P9_10_SELECTOR_cost_gate",
    source=D + "phase9_12_closure_memo.md status line; " + P9SRC_INV,
    notes="ATR scaling (B-1) wash; meta-labeling (B-3) 0.157 (memory). " + P9INV,
)
r(
    track_id="P9_13_risk_levers",
    cycle=P9,
    family=ML,
    hypothesis="Risk levers (C-1 Kelly / C-2 cap / C-3 kill switches) lift SELECTOR Sharpe to 0.18-0.22",
    mechanism="Risk overlays on v5 SELECTOR",
    information_source=fx,
    tc_adjusted_sharpe=0.177,
    result_status="SOFT GO+",
    invalid=True,
    variant_type="SENSITIVITY",
    variant_of="P9_12_bidask_labels",
    source=D + "phase9_13_closure_memo.md status/verdict; " + P9SRC_INV,
    notes="C-3 only adopted; C-1/C-2 rejected. " + P9INV,
)
r(
    track_id="P9_15_spread_bundle",
    cycle=P9,
    family=ML,
    hypothesis="Spread feature bundle improves PnL/DD as production default",
    mechanism="LightGBM SELECTOR + spread features",
    information_source=fx,
    result_status="closed: spread bundle production default (PnL-priority frame); legacy Sharpe>=0.20 NOT MET",
    invalid=True,
    variant_type="MODEL_VARIANT",
    variant_of="P9_12_bidask_labels",
    source=M
    + "project_phase9_15_closure.md (description); "
    + D
    + "phase9_15_closure_memo.md section 4; "
    + P9SRC_INV,
    notes="Recorded PnL +13%, DD -17% (memory description). Stage-1 clean re-run found +spread gives only +0.003 Sharpe, explicitly invalidating this verdict. "
    + P9INV,
)
r(
    track_id="P9_16_20pair_v9",
    cycle=P9,
    family=ML,
    hypothesis="20-pair universe expansion (v9 spread) lifts PnL",
    mechanism="LightGBM SELECTOR over 20 pairs",
    information_source=fx,
    tc_adjusted_sharpe=0.160,
    result_status="SOFT GO",
    invalid=True,
    variant_type="UNIVERSE_VARIANT",
    variant_of="P9_15_spread_bundle",
    source=D
    + "phase9_16_closure_memo.md section 6; "
    + M
    + "project_phase9_16_closure.md; "
    + P9SRC_INV,
    notes="PnL +20.1% vs v5, DD%PnL 2.5%; CSI Layer-1 features rejected (-15% PnL). Became 'production v9'. "
    + P9INV,
)
r(
    track_id="P9_17_ensemble",
    cycle=P9,
    family=ML,
    hypothesis="LGBM + MR/BO multi-strategy ensemble lifts PnL +10-20% and Sharpe +0.02-0.04",
    mechanism="Ensemble of LightGBM with mean-reversion/breakout TA strategies",
    information_source=fx,
    tc_adjusted_sharpe=0.036,
    result_status="NO ADOPT",
    invalid=True,
    source=D + "phase9_17_closure_memo.md section 4 table (lgbm+mr+bo row); " + P9SRC_INV,
    notes="0.036 is lgbm+mr+bo cell; trade rate exploded ~15x; baseline 0.160. " + P9INV,
)
r(
    track_id="P9_17b_conf_threshold",
    cycle=P9,
    family=ML,
    hypothesis="Confidence threshold on MR/BO fixes ensemble trade-rate explosion",
    mechanism="Threshold filter {0.0,0.3,0.5} on MR/BO",
    information_source=fx,
    tc_adjusted_sharpe=0.058,
    result_status="NO ADOPT",
    invalid=True,
    variant_type="SENSITIVITY",
    variant_of="P9_17_ensemble",
    source=D + "phase9_17b_closure_memo.md section 4; " + P9SRC_INV,
    notes="Sharpe lift across sweep +0.005. " + P9INV,
)
r(
    track_id="P9_18_bucketed_exits",
    cycle=P9,
    family=ML,
    hypothesis="Confidence-bucketed TP/SL (H-1) and partial exit (H-2) lift per-trade EV",
    mechanism="Exit policy variants on v9 SELECTOR",
    information_source=fx,
    tc_adjusted_sharpe=0.160,
    result_status="NO ADOPT",
    invalid=True,
    variant_type="SENSITIVITY",
    variant_of="P9_16_20pair_v9",
    source=D + "phase9_18_closure_memo.md section 4; " + P9SRC_INV,
    notes="Best cell 0.160 = symmetric baseline; variants 0.127 / -0.025; bucketed PnL 0.81x baseline. "
    + P9INV,
)
r(
    track_id="P9_19_topK_selector",
    cycle=P9,
    family=ML,
    hypothesis="Top-K SELECTOR scales Sharpe by sqrt(K)",
    mechanism="Top-K picks instead of argmax",
    information_source=fx,
    tc_adjusted_sharpe=0.165,
    result_status="PARTIAL GO",
    invalid=True,
    variant_type="SENSITIVITY",
    variant_of="P9_16_20pair_v9",
    source=D
    + "phase9_19_closure_memo.md; "
    + D
    + "phase9_x_a_closure_memo.md table (K=2 naive 0.165); "
    + P9SRC_INV,
    notes="K=2 lgbm_only: PnL +25%, Sharpe +0.005 vs baseline. " + P9INV,
)
r(
    track_id="P9_XA_regressor",
    cycle=P9,
    family=ML,
    hypothesis="LGBMRegressor on raw return labels beats classifier",
    mechanism="Regression labels",
    information_source=fx,
    tc_adjusted_sharpe=0.092,
    result_status="NO ADOPT",
    invalid=True,
    variant_type="MODEL_VARIANT",
    variant_of="P9_16_20pair_v9",
    source=D + "phase9_x_a_closure_memo.md section 4; " + P9SRC_INV,
    notes="Best of 16 cells (pct=50 K=5). " + P9INV,
)
r(
    track_id="P9_XB_mtf_features",
    cycle=P9,
    family=ML,
    hypothesis="OHLC-only feature groups (vol/moments/multi-TF) lift SELECTOR",
    mechanism="+mtf multi-timeframe features, K=3 lgbm_only",
    information_source=fx,
    tc_adjusted_sharpe=0.174,
    result_status="PARTIAL GO+",
    invalid=True,
    variant_type="MODEL_VARIANT",
    variant_of="P9_16_20pair_v9",
    source=D
    + "phase9_x_b_closure_memo.md status line; "
    + D
    + "phase9_x_b_amendment_memo.md; "
    + P9SRC_INV,
    notes="0.174 later found inflated ~9% by multi-TF lookahead (9.X-E); causal re-run +mtf 0.158 / +vol 0.160 (memory project_phase9_x_b_amendment.md). "
    + P9INV,
)
r(
    track_id="P9_XB_mtf_causal_amend",
    cycle=P9,
    family=ML,
    hypothesis="Re-rank 9.X-B cells after multi-TF lookahead fix",
    mechanism="Causal +mtf vs +vol",
    information_source=fx,
    tc_adjusted_sharpe=0.158,
    result_status="+mtf retained (PnL-priority); +vol wins Sharpe-priority by +0.002",
    invalid=True,
    post_result_correction=True,
    variant_type="POST_HOC_DIAGNOSTIC",
    variant_of="P9_XB_mtf_features",
    source=M
    + "project_phase9_x_b_amendment.md; "
    + D
    + "phase9_x_b_amendment_memo.md; "
    + D
    + "phase9_x_jlmno_series_closure_memo.md (anchor 0.158, 22,054 trades)",
    notes="Causal +mtf K=1 anchor 0.158 (22,054 trades); +vol K=3 0.160 (memory). " + P9INV,
)
r(
    track_id="P9_XC_LSTM_modeA",
    cycle=P9,
    family=ML,
    hypothesis="LSTM replacement model (Mode A) reaches STRETCH GO",
    mechanism="2-layer LSTM 64-hidden",
    information_source=fx,
    tc_adjusted_sharpe=0.061,
    result_status="NO ADOPT",
    invalid=True,
    variant_type="MODEL_VARIANT",
    variant_of="P9_XB_mtf_features",
    source=M + "project_phase9_x_c_m1_closure.md (no docs closure memo found)",
    notes="K=5, 95,945 trades, per-trade EV 0.110 pip. Numbers exist only in memory. " + P9INV,
)
r(
    track_id="P9_XD_synthetic_DXY",
    cycle=P9,
    family=ML,
    hypothesis="Synthetic DXY cross-asset features lift +mtf",
    mechanism="8 DXY-derived features from 20-pair feed",
    information_source=fx,
    result_status="NO ADOPT",
    invalid=True,
    variant_type="MODEL_VARIANT",
    variant_of="P9_XB_mtf_features",
    source=D + "phase9_x_d_closure_memo.md; " + M + "project_phase9_x_d_closure.md",
    notes="Both +dxy and +dxy+mtf failed to beat +mtf 0.174 anchor; per-cell values not extracted. "
    + P9INV,
)
r(
    track_id="P9_XJLMNO_series",
    cycle=P9,
    family=ML,
    hypothesis="v23-v26 backtest series variants on causal +mtf anchor",
    mechanism="Filtering/K variants (9.X-J/L/M/N/O)",
    information_source=fx,
    tc_adjusted_sharpe=0.158,
    result_status="best 9.X-O GO (Sharpe 0.157-0.158); others PARTIAL GO / NO ADOPT",
    invalid=True,
    variant_type="SENSITIVITY",
    variant_of="P9_XB_mtf_causal_amend",
    source=D
    + "phase9_x_jlmno_series_closure_memo.md; "
    + M
    + "project_phase9_xjlmno_series_closure.md",
    notes="SUMMARY row; 0.158 = upper of recorded 0.157-0.158. " + P9INV,
)
CAV = "Figures not committed to repo (untracked artifacts/stage1_ablation_clean.log + unmerged branch research/post-bug-fix-2026-05-03, labelled M1_V2); docs/design/m15_minimum_research_gate.md (~line 1544) withdrew citing -0.189 and C-8 (Ruling 13) fences it from M15 design justification."
for tid, cell, sh, n, pnl, dd, hit, mode in [
    (
        "P9_STAGE1_C_wf365_base",
        "C_wf365_base (no spread, per-pair)",
        -0.304,
        1880,
        -4118,
        -4232,
        "23.9%",
        "per-pair",
    ),
    (
        "P9_STAGE1_E_wf365_full",
        "E_wf365_full (+spread, per-pair)",
        -0.301,
        1383,
        -3081,
        -3141,
        "26.1%",
        "per-pair",
    ),
    (
        "P9_STAGE1_G_mp_wf365",
        "G_mp_wf365 (+spread, multipair)",
        -0.189,
        112,
        -293,
        -347,
        "26.8%",
        "multipair",
    ),
]:
    r(
        track_id=tid,
        cycle="Phase 9 post-bug-fix re-validation Stage 1 (2026-05-03)",
        family=ML,
        hypothesis="Re-validate Phase 9 ablation chain on clean pipeline (V2 settings)",
        mechanism="LightGBM " + mode + " wf365, " + cell,
        information_source=fx,
        span_label="wf365",
        tc_adjusted_sharpe=sh,
        max_dd=dd,
        result_status="negative (invalidates Phase 9 verdicts)",
        is_primary=tid.endswith("G_mp_wf365"),
        variant_type="REPLICATION",
        protected_data_caveat=CAV,
        closure_scope="All Phase 9 closure verdicts suspect; Phase 9.15 spread-bundle verdict invalidated",
        source=M + "project_phase9_invalidation_2026_05_03.md table",
        notes="n=%d trades, hit %s, PnL %d pip, MaxDD %d pip. Numbers exist only in memory (and an untracked log). G = the 'clean V2 baseline Sharpe -0.189'; multipair lift came from a 92%% trade-count cut."
        % (n, hit, pnl, dd),
    )
r(
    track_id="M1_BRule_baseline",
    cycle="Post-bug-fix M1 stages 0-20 (2026-05)",
    family=ML,
    hypothesis="B Rule: M1 17-feature LGBM + H1 23-feature agreement filter, conf=0.40, TP=1.5xATR/SL=1.0xATR",
    mechanism="M1 classifier with H1 agreement filter",
    information_source=fx,
    span_label="730d M1 BA, 20 pairs",
    tc_adjusted_annual_return=180,
    tc_adjusted_sharpe=0.0822,
    turnover=141,
    max_dd=159,
    result_status="Production baseline (final) - sole comparison axis for Phase 22",
    variant_type="BENCHMARK",
    source=D + "phase22_main_design.md section 2.3",
    notes="annual return +180 pip/year; turnover 141 trades/year; MaxDD 159 pip; +0.5 pip spread stress +110 pip/year. Memory project_m1_spread_ceiling cites ~+260 pip/year (older figure superseded by +180 in Phase 22 PR3).",
)
r(
    track_id="M1_stages_0_20_summary",
    cycle="Post-bug-fix M1 stages 0-20 (2026-05)",
    family=ML,
    hypothesis="M1 scalping classifiers/regime/label variants find positive EV after spread",
    mechanism="40+ stages: regime experts, barrier swaps, 5-class shape classifier, label boundary, feature ablation",
    information_source=fx,
    result_status="M1 spread-tax structural ceiling confirmed (no strategy found)",
    is_primary=False,
    variant_type="POST_HOC_DIAGNOSTIC",
    closure_scope="M1 daily strong-trend scalping; listed approaches marked do-not-retry",
    source=M
    + "project_m1_spread_ceiling_2026_05_05.md; "
    + M
    + "project_m1_spread_atr_recalibration_2026_05_05.md; "
    + D
    + "phase22_final_synthesis.md section 3.2",
    notes="SUMMARY row, numbers only in memory: TP/SL/TO hit 12%/87%/0.3%; classifier effect sizes <0.05; 19.0e trade Sharpe -0.16. Assumed spread/ATR 25% later recalibrated to measured median ~128% (22.0z-1; 22.0a cross-pair median 1.385 in repo).",
)
r(
    track_id="P21_timeframe_scaling",
    cycle="Phase 21 timeframe scaling",
    family=ML,
    hypothesis="21.0a M5 classifier / 21.0b M1 5-bar horizon / 21.0c M1 breakout rule beat M1 baseline",
    mechanism="Timeframe scale-up and short-horizon/breakout variants",
    information_source=fx,
    result_status=None,
    variant_type="HORIZON_VARIANT",
    source=M
    + "project_phase21_roadmap.md; "
    + D
    + "phase22_0z_results_summary.md (21.0a M5 spread/ATR 50.5% confirmed real)",
    notes="SUMMARY row. No recorded verdict or Sharpe found in docs or memory (only untracked logs artifacts/stage21_0*.log, not read per scope). Phase 22 followed.",
)
P22 = "Phase 22 (M1/M5 scalp, 8-gate harness)"
P22S = D + "phase22_final_synthesis.md"
r(
    track_id="P22_0b_zscore_MR",
    cycle=P22,
    pr="#256",
    family="reversal",
    hypothesis="Causal z-score mean reversion on M1 mid_close yields per-trade EV surviving spread",
    mechanism="z-score MR, 192-cell sweep",
    information_source=fx,
    span_label="730d M1 BA, 20 pairs",
    tc_adjusted_sharpe=-0.1828,
    tc_adjusted_annual_return=-366617.5,
    max_dd=733344.4,
    turnover=132771,
    result_status="REJECT",
    source=P22S + " section 3.3",
    notes="Best realistic-exit cell N=100,z=3.0,h=40,time_exit. annual return pooled pip/year; turnover = annual_trades; MaxDD pip. Sharpe per 8-gate harness definition.",
)
r(
    track_id="P22_0c_M5_donchian_M1_entry",
    cycle=P22,
    pr="#257",
    family="momentum",
    hypothesis="M5 Donchian breakout with M1 entry timing closes path-EV/realised gap",
    mechanism="Donchian breakout, 144-cell sweep",
    information_source=fx,
    span_label="730d M1 BA, 20 pairs",
    tc_adjusted_sharpe=-0.1751,
    tc_adjusted_annual_return=-62719.9,
    max_dd=127643.7,
    turnover=26211,
    result_status="REJECT",
    source=P22S + " section 3.4",
    notes="Best cell N=100 retest h=40 time_exit; pip/year; turnover = annual_trades.",
)
r(
    track_id="P22_0e_meta_labeling",
    cycle=P22,
    pr="#259",
    family=ML,
    hypothesis="Meta-labeling Donchian-immediate signals lifts realised Sharpe",
    mechanism="Meta-label classifier on Donchian entries, 48-cell walk-forward sweep",
    information_source=fx,
    span_label="walk-forward 4-fold (in-sample sweep)",
    tc_adjusted_sharpe=0.1377,
    tc_adjusted_annual_return=276.8,
    stability="A4 OOS fold pos/neg 3/1",
    result_status="PROMISING_BUT_NEEDS_OOS",
    is_primary=False,
    variant_type="MODEL_VARIANT",
    variant_of="P22_0c_M5_donchian_M1_entry",
    source=P22S + " sections 1, 3.6",
    notes="pip/year. Superseded by 22.0e-v2 FAILED_OOS.",
)
r(
    track_id="P22_0e_v2_OOS",
    cycle=P22,
    pr="#260",
    family=ML,
    hypothesis="22.0e selection survives strict 80/20 chronological OOS",
    mechanism="Same as 22.0e, independent OOS",
    information_source=fx,
    span_label="final 20% chronological OOS",
    tc_adjusted_sharpe=-0.0191,
    tc_adjusted_annual_return=-58.5,
    result_status="FAILED_OOS",
    preregistered=True,
    variant_type="REPLICATION",
    variant_of="P22_0e_meta_labeling",
    closure_scope="Naive M1/M5 short-term signal route (z-MR, Donchian, Donchian meta-labeling) closed on this dataset",
    source=P22S + " section 1",
    notes="pip/year. Phase 22 VERDICT: NO ADOPT. Research integrity audit PR #258 PASS.",
)
P23 = "Phase 23 (M5/M15 timeframe pivot)"
P23S = D + "phase23_final_synthesis.md section 3"
for tid, pr, fam, hyp, cells, sh, st, tv in [
    (
        "P23_0b_M5_cont_donchian",
        "#264",
        "momentum",
        "M5 continuous-trigger Donchian breakout",
        18,
        -0.318,
        "REJECT (overtrading)",
        "105k-250k",
    ),
    (
        "P23_0c_M5_firsttouch_zMR",
        "#265",
        "reversal",
        "M5 first-touch z-score mean reversion",
        36,
        -0.283,
        "REJECT (still_overtrading)",
        "43k-157k",
    ),
    (
        "P23_0d_M15_firsttouch_donchian",
        "#266",
        "momentum",
        "M15 first-touch Donchian breakout",
        18,
        -0.162,
        "REJECT (still_overtrading)",
        "22k-53k",
    ),
    (
        "P23_0c_rev1_4filter",
        "#267",
        "reversal",
        "M5 first-touch z-MR with 4 signal-quality filters",
        144,
        -0.195,
        "REJECT - closure path A",
        "8k-80k",
    ),
]:
    rev = "rev1" in tid
    r(
        track_id=tid,
        cycle=P23,
        pr=pr,
        family=fam,
        hypothesis=hyp + " clears 8-gate harness (Sharpe>=+0.082, annual_pnl>=+180)",
        mechanism=hyp,
        information_source=fx,
        span_label="730d OANDA M1 BA, 20 pairs",
        tc_adjusted_sharpe=sh,
        result_status=st,
        variant_type=("SENSITIVITY" if rev else "DISTINCT_MECHANISM"),
        variant_of=("P23_0c_M5_firsttouch_zMR" if rev else None),
        closure_scope=(
            "Tested M5/M15 rule-based entry families on 730d dataset (Phase 23 REJECT, closure path A)"
            if rev
            else None
        ),
        source=P23S + " table",
        notes="%d cells; best Sharpe (F4 filter for rev1); annual trades %s." % (cells, tv),
    )
P24 = "Phase 24 (exit/capture study)"
for tid, pr, var, sh, pnl, cap, st in [
    (
        "P24_0b_trailing",
        "#271",
        "T1_ATR_K=2.5",
        -0.177,
        -62937,
        -0.350,
        "REJECT (33/33 still_overtrading)",
    ),
    (
        "P24_0c_partial_exit",
        "#272",
        "P3_mfe_K=1.5_frac=0.5",
        -0.229,
        -60252,
        -0.335,
        "REJECT (27/27 still_overtrading)",
    ),
    (
        "P24_0d_regime_conditional",
        "#273",
        "R1_v2 (K_low=1.5/K_high=2.5)",
        -0.180,
        -62995,
        -0.350,
        "REJECT (27/27 still_overtrading)",
    ),
]:
    r(
        track_id=tid,
        cycle=P24,
        pr=pr,
        family="momentum",
        hypothesis="H2: causal exit logic converts 24.0a path-EV (frozen 23.0d M15 Donchian h=4 streams) into realised PnL clearing 8-gate harness",
        mechanism="Exit rule variant " + var,
        information_source=fx,
        span_label="730d OANDA M1 BA, 20 pairs",
        tc_adjusted_sharpe=sh,
        tc_adjusted_annual_return=pnl,
        result_status=st,
        variant_type="SENSITIVITY",
        variant_of="P23_0d_M15_firsttouch_donchian",
        closure_scope=(
            "Exit-side route (trailing/partial/regime) exhausted under NG#10/NG#11"
            if tid.endswith("regime_conditional")
            else None
        ),
        source=D + "phase24_final_synthesis.md sections 3, 5",
        notes="Best cell rank1 (N=50,h=4,exit=tb); ann_pnl pip/year; capture %s. 24.0a H1 PASS (116/216 path-EV eligible) is not a realised-PnL row."
        % cap,
    )
P25 = "Phase 25 (feature-axis sweep, path-quality label)"
for tid, pr, f, auc, sh, note in [
    ("P25_F1_vol_expansion", "#284", "F1 volatility expansion/compression", "0.5644", -0.192, ""),
    ("P25_F2_multiTF_vol", "#287", "F2 multi-TF volatility regime", "0.5613", -0.317, ""),
    (
        "P25_0d_deploy_audit",
        "#290",
        "25.0d-beta deployment-layer audit (re-fit F1+F2 best)",
        "re-fit",
        -0.21,
        "Recorded -0.21 / -0.36 (two re-fits); H-A miscalibrated, H-B/H-D refuted, H-F CONFIRMED.",
    ),
    (
        "P25_F3_cross_pair_strength",
        "#293",
        "F3 cross-pair / relative currency strength",
        "0.5480 (H1 FAIL)",
        -0.363,
        "",
    ),
    (
        "P25_F5_liquidity",
        "#296",
        "F5 liquidity / spread / volume",
        "0.5672 (H1 PASS)",
        -0.367,
        "AUC past F1 ceiling but no Sharpe improvement (load-bearing closure observation).",
    ),
]:
    dep = "deploy" in tid
    r(
        track_id=tid,
        cycle=P25,
        pr=pr,
        family=ML,
        hypothesis=f
        + " features on 25.0a-beta path-quality dataset produce ADOPT_CANDIDATE on 8-gate harness",
        mechanism="LightGBM binary path-quality classifier + " + f,
        information_source=fx,
        tc_adjusted_sharpe=sh,
        result_status="gap signature CONFIRMED; Phase 25 closes WITHOUT ADOPT_CANDIDATE",
        variant_type=("POST_HOC_DIAGNOSTIC" if dep else "MODEL_VARIANT"),
        is_primary=not dep,
        closure_scope=(
            "Phase 25 feature-axis sweep closed (F4/F6/F5-d/F5-e deferred-not-foreclosed)"
            if tid.endswith("liquidity")
            else None
        ),
        source=D + "phase25_closure_memo.md section 1 table",
        notes=("best test AUC %s; realised Sharpe. %s" % (auc, note)).strip(),
    )
P26 = "Phase 26 (label/target redesign)"
for tid, pr, f, sh, n, st, note in [
    (
        "P26_L3_EV_regression",
        "#303",
        "L-3 EV regression (spread-embedded)",
        -0.2232,
        42150,
        "REJECT_NON_DISCRIMINATIVE",
        "100% USD_JPY concentration",
    ),
    (
        "P26_L2_midmid_regression",
        "#306",
        "L-2 mid-to-mid regression",
        -0.2232,
        42150,
        "REJECT_NON_DISCRIMINATIVE",
        "100% USD_JPY; identical to L-3",
    ),
    (
        "P26_L1_ternary",
        "#309",
        "L-1 ternary {TP,SL,TIME}",
        -0.2232,
        42150,
        "REJECT_NON_DISCRIMINATIVE",
        "100% USD_JPY; identical to L-3",
    ),
    (
        "P26_R6newA_feature_widening",
        "#313",
        "R6-new-A closed 2-feature allowlist (atr+spread)",
        -0.1732,
        34626,
        "REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL) + YES_IMPROVED identity-break",
        "ann_pnl -204,664.4 pip; test Spearman -0.1535; multi-pair",
    ),
]:
    r(
        track_id=tid,
        cycle=P26,
        pr=pr,
        family=ML,
        hypothesis=f + " label/target produces ADOPT_CANDIDATE",
        mechanism="LightGBM, triple-barrier K_FAV=1.5/K_ADV=1.0 ATR, H_M1=60, 70/15/15 split",
        information_source=fx,
        span_label="test (70/15/15 chronological)",
        tc_adjusted_sharpe=sh,
        result_status=st,
        variant_type="MODEL_VARIANT",
        closure_scope=("Phase 26 closed without ADOPT_CANDIDATE" if "R6" in tid else None),
        source=D + "phase26_closure_memo.md sections 1, 2",
        notes="val-selected test Sharpe; n_trades %d; %s." % (n, note),
    )
AUD = "Phase 27-29 tabular validity audit (PR #356): TARGETED_VERIFICATION_REQUIRED; run-provenance Class U on all 9 evals (U-1 gitignored sweep outputs, U-2 sanity probe) - eval_report numerics not cross-checkable from committed evidence."
r(
    track_id="P27_5beta_summary",
    cycle="Phase 27 (score/selection/regime)",
    pr="#318,#321,#325,#328,#332",
    family=ML,
    hypothesis="Score (S-C/S-D/S-E), selection trim (R-T2) or regime features (R7-C) lift monetisation over C-sb-baseline",
    mechanism="LightGBM tabular, R7-A features, top-q selection",
    information_source=fx,
    span_label="test",
    tc_adjusted_sharpe=-0.1732,
    tc_adjusted_annual_return=-204664.4,
    ic=-0.1535,
    result_status="REJECT (all five); H-B1/H-B2 FALSIFIED, H-B3 PARTIAL, H-B5 PARTIAL_SUPPORT, H-B6 FALSIFIED_R7C_INSUFFICIENT",
    variant_type="MODEL_VARIANT",
    protected_data_caveat=AUD,
    closure_scope="Phase 27 closed; R-T1/R-B deferred-not-foreclosed",
    source=D
    + "phase27_closure_memo.md section 4.1 table, section 9; "
    + D
    + "phase27_29_tabular_eval_validity_audit.md",
    notes="SUMMARY row: val-selector picked C-sb-baseline in 5/5 (bit-identical: val Sharpe -0.1863, test Sharpe -0.1732, n=34,626, ann_pnl pip/year). ic = test Spearman(score, realised PnL). Phase 28 memo cites #311/#319/#327 for some evals; audit says actual merges #318/#321/#328.",
)
r(
    track_id="P27_0d_SE_Cse_cell",
    cycle="Phase 27 (score/selection/regime)",
    pr="#325",
    family=ML,
    hypothesis="H-B3: direct regression on realised PnL beats classifier in monetisation",
    mechanism="S-E symmetric Huber regression, C-se cell",
    information_source=fx,
    span_label="test q=40",
    tc_adjusted_sharpe=-0.483,
    ic=0.438,
    turnover=184703,
    result_status="H-B3 PARTIAL (Spearman PASS, Sharpe FAIL)",
    is_primary=False,
    variant_type="POST_HOC_DIAGNOSTIC",
    variant_of="P27_5beta_summary",
    protected_data_caveat=AUD,
    source=D + "phase27_closure_memo.md sections 5-7",
    notes="ic = Spearman +0.438; turnover = n trades at q=40. 27.0e trim: -0.767 (q=10), -0.842 (q=5).",
)
r(
    track_id="P28_3beta_summary",
    cycle="Phase 28 (objective/selection/architecture)",
    pr="#338,#342,#345",
    family=ML,
    hypothesis="A1 objective, A4 monetisation-aware selection, or A0-narrow tabular architecture lifts over C-sb-baseline",
    mechanism="L1-L3 losses; R1-R4 selection rules; AR1-AR4 architectures",
    information_source=fx,
    span_label="test",
    tc_adjusted_sharpe=-0.1732,
    tc_adjusted_annual_return=-204664.4,
    result_status="REJECT_NON_DISCRIMINATIVE (A1 FALSIFIED; A4 FALSIFIED, R-T1 FALSIFIED_under_A4; FALSIFIED_A0_NARROW)",
    variant_type="MODEL_VARIANT",
    protected_data_caveat=AUD,
    closure_scope="A1/A4/A0-narrow exhausted; A0-broad/A2/R-B/A3 deferred-not-foreclosed; NOT FALSIFIED_ALL_A0",
    source=D + "phase28_closure_memo.md sections 4-9; " + M + "project_phase28_closure_merged.md",
    notes="SUMMARY row: val-selector picked C-sb-baseline 8/8 (Phase 27+28); section 10 baseline n=34,626, Sharpe -0.1732, ann_pnl pip/year immutable. AR4 val Sharpe lift -0.4053 (worst).",
)
r(
    track_id="P29_0a_A2_targets",
    cycle="Phase 29 (stack rebase)",
    pr="#351",
    family=ML,
    hypothesis="A2 target redesign (T1-T4) lifts val Sharpe over per-target baseline",
    mechanism="T1 fixed-horizon close PnL / T2 time-weighted / T3 multi-horizon / T4 asymmetric barrier",
    information_source=fx,
    span_label="val (lift) / test (baselines)",
    result_status="REJECT_NON_DISCRIMINATIVE; FALSIFIED_A2_NARROW; R-T3 FALSIFIED_under_T3",
    variant_type="MODEL_VARIANT",
    protected_data_caveat=AUD,
    closure_scope="A2-narrow exhausted; A0-broad beta subsequently HALTED pending targeted verification (never run); WIP 9ac8fda INVALID_FOR_FORMAL_VERDICT",
    source=M
    + "project_phase29_0a_beta_merged.md; "
    + M
    + "project_phase27_29_tabular_audit_merged.md",
    notes="SUMMARY row, numbers from memory only: val Sharpe lift T1 -0.0736, T2 -0.4161, T3 -0.1320, T4 -1.3248; per-target baseline Sharpe T1 -0.0951, T2 -0.2869, T3 -0.1789, T4 -0.2284.",
)
MLS = "ML Step 4 365d_BA M1 flagship"
r(
    track_id="MLS4_first_run",
    cycle=MLS,
    pr="#421",
    family=ML,
    hypothesis="Pre-registered M1 flagship classifier meets 7 gating criteria on frozen 365d_BA holdout",
    mechanism="M1 ML classifier, threshold 0.45 (val-selected)",
    information_source=fx,
    span_label="365d_BA holdout (final 15%)",
    span_dates="2026-03-01..2026-04-24",
    tc_adjusted_sharpe=-13.69,
    result_status="ML_STEP4_365D_BA_FIRST_RUN_EVIDENCE_INVALID",
    preregistered=True,
    invalid=True,
    source=D
    + "ml_step4_365d_ba_first_run_execution_report.md metrics table; "
    + D
    + "ml_step4_365d_ba_first_run_post_audit_fable5.md; "
    + M
    + "project_ml_step4_365d_ba_m1_flagship_closed.md",
    notes="Invalid: PIP_SIZE=0.0001 applied to JPY crosses (~100x inflation). Expectancy -127.75 pips/trade (invalid). Sharpe = daily portfolio annualised.",
)
r(
    track_id="MLS4_corrected_second_run",
    cycle=MLS,
    pr="#425",
    family=ML,
    hypothesis="Pre-registered M1 flagship classifier meets 7 gating criteria on frozen 365d_BA holdout",
    mechanism="M1 ML classifier, threshold 0.45; per-pair pip fix",
    information_source=fx,
    span_label="365d_BA holdout (final 15%)",
    span_dates="2026-03-01..2026-04-24",
    tc_adjusted_sharpe=-18.91,
    turnover=168.4,
    max_dd=2.82,
    result_status="ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_DOES_NOT_MEET_PREREGISTERED_CRITERIA (M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA)",
    preregistered=True,
    post_result_correction=True,
    variant_type="REPLICATION",
    variant_of="MLS4_first_run",
    protected_data_caveat="365d_BA holdout CONSUMED (evaluated in #421 invalid run and in governance-approved corrected re-measurement #425); full data span 2025-04-25..2026-04-24.",
    closure_scope="M1 flagship lineage closed (M1_FLAGSHIP_CLOSED_THIS_LINEAGE_FAILED)",
    source=D
    + "ml_step4_365d_ba_corrected_second_run_execution_report.md sections 16-17; "
    + M
    + "project_ml_step4_365d_ba_m1_flagship_closed.md",
    notes="Expectancy -3.49 pips/trade at 0.5 pip cost (0.0 cost -2.99, i.e. negative before cost; 1.0 pip -3.99); 8,082 trades / 48 days; turnover trades/day; max_dd in x notional; win rate 7.83%; 20/20 pairs negative (memory); Sharpe daily portfolio annualised.",
)
out = str(
    __import__("pathlib").Path(__file__).resolve().parents[4]
    / "artifacts/research/programme/parts/ledger_E.json"
)
with open(out, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False, indent=1)
print(
    len(rows),
    all(set(x) == set(KEYS) for x in rows),
    len({x["track_id"] for x in rows}),
    sum(x["invalid"] for x in rows),
)
