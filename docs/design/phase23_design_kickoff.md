# Phase 23 Design Kickoff — M5/M15 Judgement + M1 Execution

**Date**: 2026-05-06
**Status**: ACTIVE — Phase 23 starting reference
**Predecessor (Phase 22 closing reference)**: `docs/design/phase22_final_synthesis.md`
**Reference list (read-only)**:
- `docs/design/phase22_main_design.md` (Phase 22 starting reference)
- `docs/design/phase22_alternatives_postmortem.md` (22.0z reject log)
- `docs/design/phase22_research_integrity_audit.md` (audit go-conditions)
- `docs/design/phase22_0a_scalp_label_design.md` (outcome dataset schema)
- `docs/design/phase22_0e_meta_labeling.md` (meta-labeling harness reference)

---

## §1 Phase 23 charter

> **Phase 23 is not a continuation of Phase 22's failed M1/M5 naive route.
> It is a timeframe-pivot study: judgement timeframe is raised to M5/M15,
> while M1 is demoted to execution support.**

The Phase 22 final synthesis closed the M1 / M5 *short-term* signal route on the 730-day OANDA M1 BA dataset (z-score MR, Donchian breakout, Donchian-immediate meta-labeling all REJECT or FAILED_OOS). Phase 23 explicitly **changes the judgement timeframe** rather than re-tuning within the closed surface. M5 / M15 spread/ATR is structurally lighter (M5 ≈ 50%, M15 expected ≈ 25-35%) than M1's 128%, giving a different cost regime in which to test the same 8-gate harness.

Phase 23's success criterion is binary at the harness level (ADOPT) and graded at the Phase level: (a) any single ADOPT cell, or (b) clear evidence that M5/M15 produces qualitatively different statistics than Phase 22's M1/M5 cells (e.g., positive realistic-exit Sharpe, even if A3 MaxDD or A4 fold-stability still fails).

If both M5 and M15 cells universally land in REJECT or FAILED_OOS, Phase 23 closes with the same kind of negative-but-bounded conclusion as Phase 22, and the next pivot becomes Phase 24 (Exit / Capture Study) per Phase 22 final synthesis §7.

---

## §2 Inheritance from Phase 22

### Inherited unchanged
- **Baseline**: B Rule unmodified Sharpe +0.0822, annual_pnl +180 pip/year, MaxDD 159 pip (`phase22_main_design.md` §2.3 / `phase22_alternatives_postmortem.md` §5).
- **8-gate verdict harness** (A0..A5 + S0 + S1) — see §7.
- **Audit-mandated feature allowlist policy**: `is_week_open_window` excluded entirely from main features; `hour_utc` / `dow` ablation-diagnostic only; no forward-looking outcome columns.
- **Per-trade Sharpe convention** (mean / std with ddof=0; no sqrt-of-N annualisation), matching `compare_multipair_v19_causal.py:_sharpe`.
- **Annualisation** uses fixed dataset span (in years).
- **20-pair canonical universe** (matches `compare_multipair_v19_causal.py:DEFAULT_PAIRS`).
- **Multiple-testing caveat** + **independent OOS validation** as a hard precondition before any production migration.
- **3-class verdict for OOS validation** (ADOPT / PROMISING_CONFIRMED / FAILED_OOS) as established in PR #260.

### New for Phase 23
- **Signal timeframe** is M5 or M15 (NOT M1).
- **Execution timeframe** is M1 (entry happens at the M1 bar that opens immediately after the M5 / M15 signal bar's close).
- **New outcome dataset** is required: `labels_M5_<pair>.parquet` and `labels_M15_<pair>.parquet`. The Phase 22 `labels_<pair>.parquet` (M1 horizons) is **read-only** in Phase 23 and is not modified.
- **Stage indexing**: 23.0a / 23.0b / 23.0c / 23.0d / 23.0e / 23.0e-v2 / 23.0f (7 stages, see §5).

---

## §3 Hypothesis

**Main hypothesis**: at M5 (and at M15) the per-trade EV of breakout / mean-reversion signals, after M1 execution-side cost, exceeds zero. Concretely, there exists a cell `(signal_TF, signal_type, signal_param, horizon, exit_rule)` that clears the Phase 22 8-gate harness on independent OOS.

**Sub-hypotheses** (verified diagnostically alongside the main verdict):

- **H1 — Cost-regime advantage**: per-pair `cost_ratio` (spread / ATR at signal time) is strictly lower at M5 than M1, and lower again at M15. Verified in 23.0a's outcome-dataset validation report.

- **H2 — Best-possible-vs-realistic gap shrinks**: as the signal TF rises, `best_possible_pnl - tb_pnl` and `best_possible_pnl - time_exit_pnl` shrink in absolute terms. If the gap remains as wide as Phase 22 (median 3.9 pip per row at M1), this PR cycle shifts toward Phase 24 (Exit / Capture).

- **H3 — Lower false-breakout rate**: the 22.0c finding of ~44% false breakouts (mid returning through break level within 5 M1 bars) decreases at M5/M15. Reported in 23.0b's eval doc per N/TF combination.

**Prior expectation**: tentatively positive on H1 (structural cost difference), tentatively neutral on H2 (gap may persist if exit rule is the binding constraint), tentatively positive on H3 (longer TF, fewer micro-noise breaks). Main hypothesis: ~30-40% probability of any ADOPT cell across 23.0b–e (informal estimate; not a gate).

---

## §4 NG list inheritance (8 items)

`phase22_alternatives_postmortem.md` §4 (5 items) + `phase22_final_synthesis.md` §8 (3 items) = 8-item NG list. **All are inherited unchanged**:

| # | NG | Phase 23 enforcement |
|---|---|---|
| 1 | Pair tier filter / single-pair concentration | All 20 pairs in train and OOS; per-pair contribution reported only |
| 2 | Train-side time-of-day filter (any time band) | Not applied; signals use all bars |
| 3 | Test-side filter improvement claim | Verdict on full OOS slice; no time-of-day cherry-pick |
| 4 | WeekOpen-aware sample weighting | None |
| 5 | Universe-restricted cross-pair feature engineering | None |
| 6 | **Phase 22's exact Donchian-immediate meta-labeling cell (N=50, conf=0.55, h=40, time_exit_pnl on M1) reuse / re-search on the 730d M1 BA dataset** | Phase 23 uses **M5 / M15** signal TFs, not M1; the Phase 22 cell exists in a different parameter space (different signal_TF, different horizon units, different outcome dataset). NG#6 prohibits re-using or re-searching the M1 cell, NOT the entire Donchian primary signal family. See §6 for the explicit policy clarification. |
| 7 | Production / paper-run of any in-sample-best cell from a multi-cell sweep without independent OOS | 23.0e-v2 mandatory whenever 23.0e finds a PROMISING cell |
| 8 | Re-fitting / re-searching alpha on the 730d M1 BA dataset used in 22.0a | **Phase 23 uses NEW outcome datasets** (`labels_M5_<pair>.parquet`, `labels_M15_<pair>.parquet`); the M1 dataset is read-only context. NG#8 does not block Phase 23. |

---

## §5 Stage roadmap (7 stages)

Each stage is a separate PR; this kickoff document does **NOT** authorise any of them. The order and conditional / mandatory status:

| Stage | Status | Goal | Deliverables |
|---|---|---|---|
| **23.0a** | mandatory | M5 + M15 outcome datasets (path-aware), separate parquet per timeframe | `scripts/stage23_0a_*.py`, `tests/`, `artifacts/stage23_0a/labels_M5/`, `artifacts/stage23_0a/labels_M15/`, validation reports |
| **23.0b** | mandatory | M5 Donchian breakout judgement + M1 immediate-entry — naive baseline (no meta-labeling) | research script + sweep + eval report |
| **23.0c** | mandatory | M5 z-score MR judgement + M1 immediate-entry — alternative naive baseline | research script + sweep + eval report |
| **23.0d** | **mandatory unless 23.0a M15 dataset generation fails or data quality is unusable** | M15 Donchian breakout judgement (variant of 0b on M15 TF) | research script + sweep + eval report |
| **23.0e** | conditional | Meta-labeling layer on best 23.0b/c/d cell (LightGBM + audit-mandated allowlist) | research script + sweep + eval report. Triggered only if 23.0b/c/d shows at least one cell with positive realistic-exit Sharpe (does not require ADOPT to trigger; does require non-trivial signal). |
| **23.0e-v2** | mandatory if 23.0e produces PROMISING_BUT_NEEDS_OOS | Strict 80/20 chronological hold-out, frozen cell, NO re-search | research script + verdict report (3-class: ADOPT / PROMISING_CONFIRMED / FAILED_OOS) |
| **23.0f** | mandatory at phase end | Phase 23 final synthesis (analogue of `phase22_final_synthesis.md`) | doc-only PR |

### Decision points
- 23.0a fails for M5 OR M15 → halt and produce closure note (this is the only path that can shorten the roadmap)
- 23.0b AND 23.0c AND 23.0d all REJECT → skip 23.0e (no signal to meta-label) → 23.0f and pivot to Phase 24
- 23.0e produces ADOPT directly (rare but possible in clean OOS) → still run 23.0e-v2 for independent confirmation; do not skip
- 23.0e-v2 PROMISING_CONFIRMED or FAILED_OOS → 23.0f closes the phase

---

## §6 23.0a outcome dataset preview (for next PR)

This kickoff does NOT implement 23.0a. The schema preview is recorded here so subsequent PRs cannot accidentally drift.

### 6.1 File layout (separated parquets)

```
artifacts/stage23_0a/
├── labels_M5/
│   ├── labels_M5_EUR_USD.parquet
│   ├── labels_M5_USD_JPY.parquet
│   └── ... (20 pairs)
├── labels_M15/
│   ├── labels_M15_EUR_USD.parquet
│   ├── labels_M15_USD_JPY.parquet
│   └── ... (20 pairs)
├── label_validation_report.md
└── label_schema.json
```

Separate files (one per timeframe) for read-isolation, responsibility separation, and to prevent timeframe mix-ups in downstream consumers.

### 6.2 Schema (per timeframe parquet)

Row key:
```
(entry_ts, pair, horizon_bars, direction)
```

`signal_timeframe` is **encoded by the file name** (`labels_M5_*.parquet` vs `labels_M15_*.parquet`), not as a row column. This is enforced by 23.0a's loader API.

`horizon_bars` units depend on the timeframe:
- M5 parquet: `horizon_bars ∈ {1, 2, 3}` = forward 5 / 10 / 15 minutes
- M15 parquet: `horizon_bars ∈ {1, 2, 4}` = forward 15 / 30 / 60 minutes

The M15 set is intentionally chosen as `{1, 2, 4}` (clean H1 sub-multiples: 1/4 H1, 1/2 H1, 1 H1), NOT a contiguous `{1, 2, 3}`. The 60-min horizon is essential for the Phase 23 timeframe-pivot study because the H1-equivalent horizon is the longest holding period at which an M15 signal can plausibly capture EV after M1 execution-side cost; dropping it would reduce the M15 surface to short-horizon-only and undermine the pivot hypothesis.

Deferred (NOT in initial 23.0a/d, may be added in a follow-up PR if the M15 surface motivates it):
- M15 horizon=3 (45 min) — skipped to keep H1-aligned discretisation
- M15 horizon ≥ 8 (≥ 2 H1) — out of Phase 23 scope; if needed, becomes a Phase 24 sub-stage

### 6.3 Entry / exit convention (consistency with 22.0a)

- entry_ts labels the **signal bar** (M5 or M15 boundary)
- entry happens at the **M1 bar** that opens immediately after the signal bar's close (i.e., M1 bar with timestamp > signal_ts)
- long entry uses ask, exit uses bid; short entry uses bid, exit uses ask (same bid/ask separation as 22.0a)
- TP/SL distances scaled by ATR at the signal_TF (NOT M1 ATR)
- All path metrics (`mfe_after_cost`, `mae_after_cost`, `best_possible_pnl`, `time_exit_pnl`, `tb_pnl`, etc.) inherit 22.0a definitions verbatim

### 6.4 Cost-ratio expectation (validation gate)

23.0a's validation report MUST verify:
- M5 per-pair `cost_ratio` median: cross-pair median should land near 0.50 (verifies H1)
- M15 per-pair `cost_ratio` median: cross-pair median should land near 0.25 - 0.35 (further verifies H1)
- M5 cost_ratio < M1 cost_ratio (per-pair) — strict inequality holds for the cleanest pair (USD_JPY); should hold across most pairs

If the cost_ratio expectation fails for the median pair, the H1 sub-hypothesis is invalidated and Phase 23's premise is shaken — that triggers a halt and review (note in §9 risk).

---

## §7 8-gate harness re-confirmation

Identical thresholds to Phase 22:

| # | Gate | Threshold | Note |
|---|---|---|---|
| **A0** | annual_trades ≥ 70 | unchanged | Even if M15 trade count is structurally lower, A0 stays at 70. Insufficient trade count is a valid REJECT reason — see §9 risk. |
| **A1** | OOS Sharpe ≥ +0.082 | unchanged | per-trade convention |
| **A2** | OOS annual_pnl ≥ +180 pip | unchanged |  |
| **A3** | OOS MaxDD ≤ 200 pip | unchanged |  |
| **A4** | OOS k-fold pos/neg ≥ 3/1 (4 OOS folds) | unchanged | from 22.0e-v2 boundary |
| **A5** | OOS spread +0.5 pip stress annual_pnl > 0 | unchanged |  |
| **S0** | \|shuffled_sharpe\| < 0.10 (hard); 0.05 reported as diagnostic | unchanged | from 22.0e/v2 |
| **S1** | mean(train_sharpe - OOS_sharpe) ≤ 0.30 | unchanged |  |

**Verdict classification (3-class, from PR #260)**:
- **ADOPT**: A0..A5 + S0 + S1 all pass
- **PROMISING_CONFIRMED**: A1, A2, S0, S1 pass; one of A3/A4/A5 fails
- **FAILED_OOS**: A1 OR A2 fail; OR A0 fail; OR S0 OR S1 fail

If M15 cells consistently fail A0 (insufficient trade count), the issue is opened in 23.0d's verdict report and considered for a separate threshold-review PR — **A0 is NOT lowered for Phase 23 unilaterally**.

---

## §8 23.0e meta-labeling — Donchian primary policy clarification

NG#6 (`phase22_final_synthesis.md` §8) is precisely worded:

> Donchian-immediate meta-labeling at the **exact frozen cell (N=50, conf=0.55, h=40, time_exit_pnl) on the 730d M1 BA dataset**

Phase 23 uses M5 / M15 signal timeframes against new outcome datasets. The cell space is therefore disjoint from Phase 22's:

> **Donchian is allowed only as a higher-timeframe signal family. Phase 22's exact Donchian-immediate meta-labeling cell must not be reused or re-searched.**

What this means in practice for 23.0e:

| Allowed | Forbidden |
|---|---|
| Donchian-immediate on M5 (N as a sweep dimension) with M1 execution | Re-running the Phase 22 (N=50, conf=0.55, h=40, time_exit_pnl) cell on the 730d M1 dataset |
| Donchian-immediate on M15 (N as a sweep dimension) | "Tweaking" a single param of the Phase 22 cell (e.g., conf=0.50 instead of 0.55, all other M1 settings unchanged) |
| Z-score MR primary on M5 / M15 | Re-applying any M1-level cell that scored highest in the 48-cell sweep without independent OOS |

23.0e's eval doc must include an explicit cell-comparison table showing the new cell space versus Phase 22's cell, demonstrating they share no parameter row.

---

## §9 Risk / known concerns

| Risk | Likelihood | Mitigation |
|---|---|---|
| M5/M15 path-EV-vs-realised-PnL gap reproduces Phase 22's pattern | Medium | 23.0b/c/d eval reports include a `best_possible_pnl - realistic_pnl` section per top cell; if gap remains > Phase 22's median, the Phase rolls into 23.0f early with a "TF pivot insufficient — pivot to Phase 24 Exit study" closure |
| M15 has too few signals → A0 fails systematically | Medium-high | 23.0a's per-pair signal-count report; per-cell minimum trade count for top-K ranking (already in 22.0b/c convention); A0 stays at 70 |
| 23.0e meta-labeling reproduces 22.0e walk-forward / strict-OOS divergence | Medium | 23.0e-v2 strict 80/20 OOS is mandatory whenever 23.0e finds PROMISING_BUT_NEEDS_OOS; drawdown attribution is mandatory (replicating 22.0e-v2 §7 analysis) |
| H1 cost-regime advantage doesn't materialise (M5 cost_ratio ≈ M1 cost_ratio) | Low | 23.0a validation report has a formal H1 check; if cross-pair median fails, halt and review |
| Schema drift between M5 and M15 parquets, or between either and 22.0a | Medium | Separate parquet files per TF + unit tests asserting schema identity within each TF, plus a schema_compat test against 22.0a (consumers can pivot between datasets without code changes) |
| Multiple-testing inflation as cell counts grow across 23.0b/c/d | Medium | Each stage's eval report includes the multiple-testing caveat; 23.0e mandatorily uses cross-pair model with OOS predictions; 23.0e-v2 strict hold-out catches in-sample artifacts |

---

## §10 Out-of-scope

- src/, scripts/run_*.py, DB schema (Phase 22 + Phase 23 invariant)
- Trailing stop / partial exit / dynamic SL — these are Phase 24 (Exit / Capture)
- ATR-Keltner / Bollinger / volatility-breakout signal styles — deferred from Phase 22
- Fresh OANDA fetch beyond the 730d pull — Phase 22 final synthesis Rank 3, separate effort
- Production / paper-run migration — gated behind any ADOPT cell + independent OOS + a separate paper-run PR cycle
- Z-score primary on M5/M15 in this kickoff (it is in the 23.0c stage scope, but no implementation in this PR)

---

## §11 Document role boundary

| Document | Role | Editable in Phase 23? |
|---|---|---|
| `phase22_main_design.md` | Phase 22 starting reference (read-only) | NO |
| `phase22_final_synthesis.md` | Phase 22 closing reference (read-only) | NO |
| `phase22_alternatives_postmortem.md` | 22.0z reject log (read-only) | NO |
| `phase22_research_integrity_audit.md` | Phase 22 audit (read-only) | NO |
| Phase 22 stage docs (`phase22_0a_*.md` etc.) | Phase 22 contracts (read-only) | NO |
| **`phase23_design_kickoff.md` (this file)** | **Phase 23 starting reference** | YES (only via subsequent doc PRs that explicitly amend it) |
| Future `phase23_0a_*.md`, `phase23_0b_*.md`, etc. | Per-stage contracts | (Created by 23.0a, 23.0b, ... PRs) |
| Future `phase23_final_synthesis.md` | Phase 23 closing reference | (Created by 23.0f PR) |

---

## §12 Estimated phase effort (informational, not committed here)

| Stage | Estimated effort | Notes |
|---|---|---|
| 23.0a | ~6-8 hours | Two parquets to generate; per-pair cost_ratio validation; schema tests |
| 23.0b | ~5-7 hours | Reuses 22.0c harness; M5 Donchian + M1 execution; sweep + report |
| 23.0c | ~5-7 hours | Reuses 22.0b harness; M5 z-score MR; sweep + report |
| 23.0d | ~5-7 hours | M15 variant of 23.0b; reuses 23.0b script with TF parameterisation |
| 23.0e | ~9-12 hours | LightGBM meta-labeling; reuses 22.0e harness; per-TF feature considerations |
| 23.0e-v2 | ~4-5 hours | Strict 80/20 OOS; reuses 22.0e-v2 script with frozen cell |
| 23.0f | ~3-4 hours | Final synthesis doc-only PR |

Total: **~37-50 hours** (rough; not a commitment).

---

**Phase 23 starts here.** Subsequent stage PRs reference this kickoff for inherited constraints (8-gate harness, NG list, audit-mandated allowlist, 3-class verdict, 20-pair universe). The first implementation PR is **23.0a — M5/M15 outcome dataset**.
