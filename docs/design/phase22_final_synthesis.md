# Phase 22 Final Synthesis

**Date**: 2026-05-06
**Status**: Phase 22 closes. **VERDICT: NO ADOPT.**
**Scope**: Final synthesis of PRs #254 — #260 (2026-05-04 — 2026-05-06)
**Predecessor (Phase 22 starting reference)**: `docs/design/phase22_main_design.md`
**Companion**: `docs/design/phase22_alternatives_postmortem.md`

> **Document role**:
> - `phase22_main_design.md` — the design reference at the **start** of Phase 22
>   (active source of truth for goals and constraints during the phase)
> - **`phase22_final_synthesis.md` (this file)** — the closing reference at the
>   **end** of Phase 22 (canonical post-phase summary, NG-list extension, and
>   next-phase recommendation)

---

## §1 Executive summary

Phase 22 ran 7 PRs (#254 — #260) over 730 days of M1 BA OANDA data covering
20 canonical pairs, between 2026-05-04 and 2026-05-06. Goals were set in
`phase22_main_design.md`: build a path-aware scalp outcome dataset, then
search for a strategy candidate that beats baseline (B Rule unmodified
Sharpe +0.0822, annual PnL +180 pip/year) on the 8-gate verdict harness
(A0–A5 + S0 + S1).

**Verdict: Phase 22 closes WITHOUT an ADOPT. Zero strategy candidates met
the eight-gate threshold under independent OOS validation.**

| Stage | Verdict |
|---|---|
| 22.0a path-aware outcome dataset | (foundation, not graded) |
| 22.0b z-score mean reversion baseline | **REJECT** |
| 22.0c M5 Donchian breakout + M1 entry hybrid | **REJECT** |
| Research integrity audit (PR #258) | **PASS** (no implementation bugs) |
| 22.0e Donchian-immediate meta-labeling (in-sample sweep) | PROMISING_BUT_NEEDS_OOS |
| 22.0e-v2 strict chronological OOS validation | **FAILED_OOS** |

The single PROMISING result (22.0e walk-forward Sharpe 0.1377, annual PnL
+276.8 pip) did **not** survive the strict 80%-train / 20%-OOS hold-out
(22.0e-v2 OOS Sharpe -0.0191, annual PnL -58.5 pip). The audit (PR #258)
confirmed that bid/ask convention, sign of PnL, annualisation, and
look-ahead avoidance are all correct — the REJECTs are real research
findings, not implementation bugs.

The naive M1 / M5 short-term signal route — z-score mean reversion,
Donchian breakout, and Donchian-immediate meta-labeling — is **closed**
on this dataset.

---

## §2 PR list (#254 — #260)

| PR | Branch | Stage / topic | Verdict | Squash commit |
|---|---|---|---|---|
| #254 | `docs/phase22-pr3-design-consolidation` | 22.0z PR3 design consolidation | (doc-only) | `c51dfd7` |
| #255 | `research/phase22-0a-scalp-label-design` | 22.0a path-aware outcome dataset | (foundation) | `d6c20b6` |
| #256 | `research/phase22-0b-mean-reversion-baseline` | 22.0b z-score MR | **REJECT** | `34a26ed` |
| #257 | `research/phase22-0c-m5-breakout-m1-entry-hybrid` | 22.0c M5 Donchian breakout + M1 entry | **REJECT** | `fc41bcc` |
| #258 | `audit/phase22-research-integrity` | Research integrity audit | **PASS** | `fa7c0dd` |
| #259 | `research/phase22-0e-meta-labeling` | 22.0e Donchian-immediate meta-labeling | PROMISING_BUT_NEEDS_OOS | `69b1a4a` |
| #260 | `research/phase22-0e-v2-independent-oos` | 22.0e-v2 strict OOS validation | **FAILED_OOS** | `5fc0520` |

All 7 PRs squash-merged onto master. None touched src/, scripts/run_*.py,
or DB schema. NG-list (postmortem §4) honoured throughout.

---

## §3 Per-stage results

### §3.1 PR #254 — 22.0z PR3 design consolidation

- **Goal**: close out 22.0z prerequisite work and remove the `weekopen_excluded`
  baseline from the Phase 22 active design after 22.0z-3c/3d/3e showed it was
  a fold-4-fragile, train-side-destructive artifact (postmortem §2).
- **Result**: doc-only PR. `phase22_0z_results_summary.md` marked SUPERSEDED;
  `phase22_alternatives_postmortem.md` and `phase22_main_design.md` published
  as the active references.
- **Verdict**: doc-only (no metric grade). Restored baseline = B Rule
  unmodified +180 pip/year / Sharpe +0.0822.

### §3.2 PR #255 — 22.0a path-aware scalp outcome dataset

- **Goal**: produce a true-long format dataset of `(entry_ts, pair, horizon_bars, direction)` rows containing path-aware metrics (mfe_after_cost, mae_after_cost, best_possible_pnl, time_exit_pnl, tb_pnl, tb_outcome, time_to_tp/sl, same_bar_tp_sl_ambiguous) plus context flags (cost_ratio, atr_at_entry, spread_entry, hour_utc, dow, is_week_open_window).
- **Method**: 20 canonical pairs × 730 days × 4 horizons {5, 10, 20, 40} × 2 directions = ~118.2M rows total; ~117.5M valid+non-gap.
- **Output**: `artifacts/stage22_0a/labels/labels_<pair>.parquet` (20 files), `label_validation_report.md`, `label_schema.json`. Hard ADOPT criteria H1–H8 all PASS.
- **Cost-ratio re-confirmation**: per-pair `spread_entry / atr_at_entry` median range 0.673 (USD_JPY) — 2.375 (AUD_NZD); cross-pair median 1.385 (vs 22.0z-1's claimed ~1.28; within 0.15 band). Confirms M1 spread/ATR ≈ 128% structural finding.
- **Verdict**: foundation accepted; consumed by 22.0b / 22.0c / 22.0e / 22.0e-v2.

### §3.3 PR #256 — 22.0b z-score Mean Reversion baseline

- **Goal**: test whether a causal z-score mean-reversion signal on M1 mid_close yields per-trade EV that survives spread cost.
- **Method**: 192-cell sweep — N (rolling) ∈ {10, 20, 50, 100} × z-threshold ∈ {1.5, 2.0, 2.5, 3.0} × horizon ∈ {5, 10, 20, 40} × exit_rule ∈ {tb_pnl, time_exit_pnl, best_possible_pnl}. Pooled per-trade PnL across 20 pairs. 5-fold walk-forward, +0.2/+0.5 pip spread stress.
- **Best realistic-exit cell**: N=100, threshold=3.0, horizon=40, exit=time_exit_pnl.
  - annual_trades = 132,771
  - **Sharpe = -0.1828** (vs baseline +0.0822) → **A1 FAIL**
  - **annual_pnl = -366,617.5** pip (vs baseline +180) → **A2 FAIL**
  - MaxDD = 733,344.4 pip → A3 FAIL
  - All cells across the realistic exit_rule space land in REJECT.
- **Failure-mode insight**: top cells show large `best_possible_pnl - tb_pnl` gap (path EV exists, exit destroys it). Documented for 22.0c follow-up.
- **Verdict**: **REJECT**. `artifacts/stage22_0b/eval_report.md`.

### §3.4 PR #257 — 22.0c M5 Donchian Breakout + M1 Entry Hybrid

- **Goal**: test whether multi-TF (M5 signal + M1 entry-timing) closes the path-EV-vs-realised-PnL gap from 22.0b.
- **Method**: 144-cell sweep — Donchian N (M5 bars) ∈ {10, 20, 50, 100} × entry timing ∈ {immediate, retest, momentum} × horizon ∈ {5, 10, 20, 40} × exit_rule ∈ {tb_pnl, time_exit_pnl, best_possible_pnl}. M1→M5 right-closed/right-labeled aggregation. retest/momentum entry-side bid/ask convention (long: ask_l for retest, ask_h for momentum; short: bid_h, bid_l).
- **Best realistic-exit cell**: N=100, timing=retest, horizon=40, exit=time_exit_pnl.
  - annual_trades = 26,211 (n_signals/fired/skipped_rate diagnostics: retest ~66% skipped; momentum <1%; immediate 0%)
  - **Sharpe = -0.1751** → **A1 FAIL**
  - **annual_pnl = -62,719.9** pip → **A2 FAIL**
  - MaxDD = 127,643.7 → A3 FAIL
  - false-breakout rate ~44% across all N (mid returns through break level within 5 M1 bars)
- **Failure-mode insight**: best_possible vs realistic gap remains large; entry timing alone does NOT close it. Path EV is there, but exit + signal + timing combination cannot capture it.
- **Verdict**: **REJECT**. `artifacts/stage22_0c/eval_report.md`.

### §3.5 PR #258 — Research integrity audit

- **Goal**: independently verify that the REJECTs from 22.0b/c are not implementation bugs (annualisation, bid/ask sign, look-ahead, sample-filter consistency).
- **Method**: read-only audit script (`scripts/stage22_0x_research_audit.py`) re-computes 22.0b/c top-cell metrics from the 22.0a parquet, samples 22.0a rows for bid/ask convention spot-checks, and verifies the 22.0e plan feature allowlist.
- **Findings**:
  - 22.0b top cell: recomputed annual_pnl = -366,617.5 (matches reported exactly).
  - 22.0c top cell: recomputed annual_pnl = -62,669.5 vs reported -62,719.9 (0.08% relative diff, numerical noise).
  - 22.0a long+short conventions: 10/10 + 10/10 sample rows match.
  - best_possible_pnl gap is a real path quantity: gap_min=0.000, no negative gaps, p99=38.0 pip.
  - All NG-list invariants honoured by 22.0a/b/c scripts.
- **Verdict**: **PASS** — 0 BLOCKER, 0 MAJOR, 0 MINOR. The REJECTs are real findings.
- The audit also formalised the feature-allowlist policy that 22.0e/v2 inherited: `is_week_open_window` excluded entirely; `hour_utc`/`dow` ablation-diagnostic only; no forward-looking columns.

### §3.6 PR #259 — 22.0e Donchian-immediate meta-labeling

- **Goal**: test whether a LightGBM binary classifier on causal context features ranks Donchian-immediate breakout signals well enough that high-confidence trades clear the eight-gate harness.
- **Method**: 48-cell sweep — Donchian N ∈ {20, 50} × confidence threshold ∈ {0.50, 0.55, 0.60, 0.65} × horizon ∈ {10, 20, 40} × exit_rule ∈ {tb_pnl, time_exit_pnl}. Walk-forward 4-fold OOS (k=1..4 of 5 chronological quintiles, k=0 dropped). Mandatory shuffled-target sanity (S0) and train-test parity (S1) gates added.
- **Best main cell**: N=50, conf=0.55, horizon=40, exit=time_exit_pnl.
  - annual_trades = 80 → A0 PASS
  - **Sharpe = 0.1377** (vs baseline +0.0822) → **A1 PASS**
  - **annual_pnl = +276.8** pip (vs baseline +180) → **A2 PASS**
  - **MaxDD = 355.7** → **A3 FAIL** (only failing realistic gate)
  - A4 OOS fold pos/neg = 3/1 → A4 PASS
  - A5 stress +0.5 pip annual_pnl = +237.0 → A5 PASS
  - **S0 |shuffled_sharpe| = 0.0000** → S0 PASS (also clears 0.05 diagnostic)
  - **S1 train_test_gap = 0.1745** → S1 PASS
- **Ablation diagnostics** (DIAGNOSTIC ONLY, not entered into headline verdict):
  - Ablation-A (main + hour_utc): best Sharpe 0.2289 (lift +0.0911)
  - Ablation-B (main + hour_utc + dow): best Sharpe 0.1909 (worse than A)
  - hour_utc helps; dow degrades. Neither enters the headline verdict per audit policy.
- **Verdict**: **PROMISING_BUT_NEEDS_OOS** — first non-REJECT in Phase 22, but A3 MaxDD failure required strict OOS verification before any production migration.
- `artifacts/stage22_0e/eval_report.md`.

### §3.7 PR #260 — 22.0e-v2 Independent OOS validation

- **Goal**: verify whether PR #259's PROMISING cell survives a strict chronological hold-out without re-tuning.
- **Method**: train = first 80% of 730d data; OOS = last 20% (~146 days). Single LightGBM model. Same frozen cell (N=50, conf=0.55, h=40, time_exit_pnl). Time-ordered last-20% within-train as ES validation. 4 OOS sub-folds for diagnostic stability only (NOT for training).
- **Result**: OOS Sharpe = -0.0191 (vs PR #259's +0.1377 walk-forward); OOS annual_pnl = -58.5 (vs +276.8).
  - **A1 FAIL**: OOS Sharpe -0.0191 < +0.082
  - **A2 FAIL**: OOS annual_pnl -58.5 < +180
  - **A3 FAIL**: OOS MaxDD 312.1 > 200
  - A4, A5 also fail; S1 fails (train-OOS gap > 0.30)
  - **S0 PASSES** (shuffled_sharpe = 0.0000) — the failure is *not* contamination; it is a generalisation failure
- **Drawdown attribution**: SINGLE_PAIR_CONCENTRATION (worst pair = 46.1% of MaxDD) + SINGLE_PERIOD_CONCENTRATION (worst OOS sub-fold = 76.3% of negative PnL). The PR #259 alpha was effectively concentrated in one pair × one window.
- **Verdict**: **FAILED_OOS**. `artifacts/stage22_0e_v2/eval_report.md`.

---

## §4 Key findings (8 items)

| # | Finding | Evidence (artifact pointer) |
|---|---|---|
| 1 | **M1 spread/ATR median = 128%** (cross-pair; per-pair range 65-236%, USD_JPY 0.673 cleanest, AUD_NZD 2.375 worst). Spread cost ≈ ATR — signal must beat ATR to net positive. | 22.0z-1 (postmortem §1.2); audit §2.4; 22.0a `label_validation_report.md` |
| 2 | **M5 spread/ATR ≈ 50% is real**, not aggregation artifact (USD_JPY native 39.1% vs aggregated 41.0%; EUR_USD 53.4 vs 54.1; GBP_JPY 63.0 vs 65.1; all within 2 pp). M1→M5 aggregation is methodologically sound. | 22.0z-2 (postmortem §3) |
| 3 | **Pair tier filter universally REJECT**: USD_JPY only PnL -1056, JPY 6 -131, JPY 4 -296, cleanest_top5 -319; all baselines worse. Multipair LGBM structure depends on cross-pair training; universe restriction destroys it. | 22.0z-3/3b (postmortem §1) |
| 4 | **Time-of-day gate REJECT**: test-only filter improvement was fold-4 fragile and based on 7 trades (postmortem §2.3); train+test filter destroyed PnL (+234 → +21/-78/-183 across configs, postmortem §2.4). Train-side time filter is destructive. | 22.0z-3c/3d/3e (postmortem §2) |
| 5 | **M1 z-score mean reversion REJECT**: best Sharpe -0.1828, annual_pnl -366,617.5 pip across 192 cells × 20 pairs. The 128% spread/ATR ratio prevents naive mean-reversion targets from netting positive after cost. | 22.0b `eval_report.md` |
| 6 | **M5 Donchian breakout REJECT**: best Sharpe -0.1751, annual_pnl -62,719.9 pip across 144 cells × 3 entry timings × 20 pairs. False-breakout rate ~44% on naive Donchian. **Entry timing alone does NOT close the path-EV-vs-realised-PnL gap.** | 22.0c `eval_report.md` |
| 7 | **Meta-labeling on Donchian primary: walk-forward PROMISING_BUT_NEEDS_OOS, strict OOS FAILED**. PR #259 walk-forward: Sharpe 0.1377, annual_pnl +276.8. PR #260 strict 80/20 OOS: Sharpe -0.0191, annual_pnl -58.5. The walk-forward result was a multiple-testing artifact concentrated in one pair × one window (46.1% pair share + 76.3% period share of the loss). | 22.0e + 22.0e-v2 `eval_report.md` |
| 8 | **Audit PASS confirms REJECTs are real**: bid/ask convention 10/10 + 10/10 sample matches, annualisation exact match (22.0b annual_pnl reproduced -366,617.5 == reported), best_possible_pnl is a real path quantity (gap_min=0, p99=38 pip), no NG-list violations. The negative results are research findings, not implementation bugs. | PR #258 audit doc + `audit_results.json` |

---

## §5 Final conclusion

**Phase 22 closes WITHOUT an ADOPT verdict.** Across 22.0a's foundation
through 22.0e-v2's strict OOS validation, no strategy candidate cleared
the eight-gate harness on the 730-day OANDA M1 BA dataset.

The closed routes:
- M1 z-score mean reversion at any (N, threshold, horizon, exit_rule) combination tested
- M5 Donchian breakout with `immediate` / `retest` / `momentum` M1 entry timing
- LightGBM meta-labeling on Donchian-immediate primary with the audit-mandated causal feature allowlist

The diagnostic that emerged repeatedly: `best_possible_pnl` (path peak) is meaningfully positive on selected entries, but realistic exits (TP/SL/time) consistently fail to capture it. Three entry-timing variants in 22.0c and a model-based filter in 22.0e/v2 did not solve this; the cost regime (M1 spread/ATR = 128%) is the binding structural constraint.

**Important scope qualifier — what was NOT proven**:

> Phase 22 does NOT prove that FX scalping is impossible. What was rejected
> is **the specific combination** of:
> 1. Current OANDA-class spread cost regime (M1 spread/ATR ≈ 128%)
> 2. The 730-day historical M1 BA dataset used in this phase
> 3. The set of M1 / M5 short-term signals tested here (z-score MR, Donchian breakout, Donchian-immediate meta-labeling)
>
> Other timeframes (M5/M15-only judgement, with M1 used purely for execution
> timing), other exit designs (trailing stop, partial exit, dynamic SL), other
> data ranges (fresh OANDA pulls, longer history), and other primary signal
> sources have NOT been exhausted by this phase. They remain open hypotheses
> for future research.

The audit (PR #258) PASS adds confidence that this conclusion rests on
correct calculation, not on an implementation defect. The 22.0e/v2 contrast
(walk-forward Sharpe 0.14 → strict-OOS Sharpe -0.02 with S0 sanity
preserved) is a clean demonstration of the multiple-testing risk in
high-cell-count sweeps and validates the audit-mandated independent-OOS
go-condition.

---

## §6 Remaining hypotheses (open)

These were not invalidated by Phase 22; they are the **next research surface**:

### §6.1 M5 / M15-only fallback (`phase22_main_design.md` §4 Stage 22.0g)

- M5 spread/ATR ≈ 50% is structurally lighter than M1's 128%
- Decision happens on M5 / M15; M1 is used for execution timing only
- Outcome dataset extension required: M5 horizons {1, 2, 3} bars (5/10/15 min) — schema-compatible with 22.0a per `phase22_0a_scalp_label_design.md` §3.3
- Untested in the 730d window and would be the most natural Phase 23 starting point

### §6.2 Exit / Capture study

- The recurring failure-mode (best_possible >> realistic) suggests the exit rule, not the signal, is the binding constraint at the 22.0c/22.0e level
- Trailing stop, partial exit, dynamic SL, or multi-level take-profit cannot be evaluated on the current 22.0a outcome parquet — needs path bar data per row, not just summary statistics
- A foundational PR (22.0a equivalent for path-detail) would be required before strategy comparison can begin

### §6.3 Fresh OANDA fetch validation

- The 730-day M1 BA dataset may be unrepresentative of forward conditions
- Independent OANDA fetch covering bars **after 2026-04-29** (the end of the current pull) would let a frozen cell (e.g., the 22.0e-v2 cell) be tested on truly out-of-sample data, not a chronological hold-out of the same pull
- Live-demo OANDA token required; fetch + frozen-cell evaluation = 1 PR pair

### §6.4 Alternative primary signal source

- Trend / momentum hybrid (instead of Donchian breakout)
- Bias-from-CSI context features (subject to NG-list scrutiny — `is_week_open_window` excluded; hour/dow only as ablation)
- Calendar-event-aware signal (subject to NG-list scrutiny — must NOT degenerate into a time-of-day filter)
- Cross-pair correlation regime detection
- These would each require a fresh meta-labeling sweep with a separately defined feature allowlist; would not reuse the 22.0e cell

---

## §7 Recommended next phase

Three candidates ranked:

### Rank 1 — **Phase 23: M5/M15 judgement + M1 execution**

Hypothesis: at M5 (spread/ATR ≈ 50%) or M15 (lighter still) the signal is informative enough that even imperfect M1 execution leaves positive net PnL after cost.

Recommended PR sequence:
1. `phase23_design_kickoff.md` (doc-only)
2. 23.0a M5/M15 outcome dataset extension (schema reuses 22.0a parquet keys)
3. 23.0b M5 Donchian breakout judgement + M1 immediate-entry execution (no meta-labeling first; reuses 22.0c harness)
4. 23.0c M5 z-score MR judgement + M1 execution
5. 23.0d (conditional) meta-labeling on the strongest 23.0b/c cell — only if 23.0b/c shows a positive realistic-exit cell

This route reuses the most existing infrastructure (22.0a parquet,
22.0b/c sweep harness, 22.0e LightGBM training pipeline) while attacking
the question on a friendlier cost regime.

### Rank 2 — **Phase 24: Exit / Capture Study**

Hypothesis: signal quality is sufficient at M1, but the exit rule is the
binding constraint. Trailing stop / partial exit / dynamic SL can capture
some fraction of the best_possible_pnl gap.

Recommended PR sequence:
1. `phase24_design_kickoff.md` (doc-only)
2. 24.0a outcome dataset extension with **path bars per row** (significant change — 22.0a parquet is summary-only)
3. 24.0b trailing-stop sweep
4. 24.0c partial-exit sweep
5. 24.0d combined exit + 22.0e signal re-evaluation

Higher infrastructure cost (path-bar storage) but addresses the recurring
22.0b/c/e failure-mode directly.

### Rank 3 — Fresh OANDA fetch validation (lower priority)

A targeted, smaller PR pair:
1. `phase22_z_fresh_fetch_validation.md` (doc) + fetch script
2. Frozen 22.0e-v2 cell re-evaluated on bars **after 2026-04-29**

If the 22.0e-v2 cell suddenly works on the new window, that's a strong
indication the 730d data was unrepresentative; if it still fails, we can
permanently retire the cell.

This is rank 3 because the 22.0e-v2 strict-OOS already shows the cell
fails on the chronological tail of the same pull; a fresh fetch is more
likely to confirm the negative than reverse it. Useful for completeness
but not the most informative next experiment.

---

## §8 NG list / 再試行禁止 (formal extension)

`phase22_alternatives_postmortem.md` §4 NG list (5 items) inherits unchanged.
**The following are added as a result of Phase 22 closure**:

| # | NG path | Reason | Source |
|---|---|---|---|
| 1 (existing) | Pair tier filter / single-pair concentration | All variants REJECT in 22.0z-3/3b | postmortem §1 |
| 2 (existing) | Train-side time-of-day filter (any time band) | 22.0z-3e v2/v3 all configs PnL collapse | postmortem §2.4 |
| 3 (existing) | Test-side filter improvement claim | 22.0z-3c/3d fold-4 fragile, 7-trade artifact | postmortem §2.5 |
| 4 (existing) | WeekOpen-aware sample weighting | Same root cause as #2 | postmortem §2 |
| 5 (existing) | Universe-restricted cross-pair feature engineering | Closed by #1 | postmortem §1 |
| **6 (new)** | **Donchian-immediate meta-labeling at the exact frozen cell (N=50, conf=0.55, horizon=40, exit=time_exit_pnl) on the 730d dataset** | 22.0e-v2 strict-OOS FAILED with drawdown attribution to single-pair + single-period concentration. This specific cell is closed; alternative N / conf / horizon must be a NEW sweep with NEW OOS, not a re-evaluation of this one. | this doc §3.7 |
| **7 (new)** | **Production / paper-run of any in-sample-best cell from a multi-cell sweep without independent OOS** | 22.0e Sharpe 0.1377 → 22.0e-v2 Sharpe -0.0191 demonstrates that walk-forward "OOS" (from rolling folds within the same dataset) is not an adequate substitute for a strictly held-out chronological tail. | audit §13 + this doc §3.7 |
| **8 (new)** | **Re-fitting / re-searching alpha on the 730d M1 BA dataset used in 22.0a** | The cells available on this dataset have been exhaustively searched (192 + 144 + 48 = 384 cells × 20 pairs). New strategy candidates require a new outcome dataset (M5/M15 horizons, path-bar exit study, or fresh OANDA fetch). | this doc §5 + §6 |

These NG entries apply to **future Phase 23 / 24 / Z research**. They do
NOT modify the existing `phase22_alternatives_postmortem.md` file (which
remains the read-only record of 22.0z-only rejections).

---

## §9 Next-PR candidates

In recommended order:

1. **Phase 23 kickoff** — `docs/design/phase23_design_kickoff.md`. Doc-only PR. Establishes M5/M15 judgement + M1 execution as the active research direction. References this synthesis as the closing reference for Phase 22.

2. **Phase 24 kickoff** — `docs/design/phase24_design_kickoff.md`. Doc-only PR. Establishes Exit / Capture study as an alternative path. Should be considered if Phase 23 hits the same path-EV-vs-realised-PnL pattern.

3. **Phase 22.Z fresh-fetch validation** — `docs/design/phase22_z_fresh_fetch_validation.md` + fetch script. Lower priority. Decisive negative result more likely than positive; useful for permanently retiring the 22.0e-v2 cell.

Each candidate is a separate PR; this synthesis does not authorise any of
them. The next-step decision is up to the user.

---

## §10 Document role boundary (clarification)

| Document | Role | Editable? |
|---|---|---|
| `docs/design/phase22_main_design.md` | Phase 22 starting reference (active source of truth **during** the phase) | Already touched by PR #254; **do not modify further** in Phase 22 closure |
| `docs/design/phase22_alternatives_postmortem.md` | 22.0z-only rejection record | Read-only; do not modify |
| `docs/design/phase22_0a_scalp_label_design.md` | 22.0a contract | Read-only |
| `docs/design/phase22_0b_mean_reversion_baseline.md` | 22.0b contract | Read-only |
| `docs/design/phase22_0c_m5_breakout_m1_entry_hybrid.md` | 22.0c contract | Read-only |
| `docs/design/phase22_research_integrity_audit.md` | Audit record | Read-only |
| `docs/design/phase22_0e_meta_labeling.md` | 22.0e contract | Read-only |
| `docs/design/phase22_0e_v2_independent_oos.md` | 22.0e-v2 contract | Read-only |
| **`docs/design/phase22_final_synthesis.md`** (this file) | **Phase 22 closing reference (canonical post-phase summary)** | This is the only document this PR creates; subsequent PRs should reference this for Phase 22 context |

---

**Phase 22 closes here.** Subsequent research lives in Phase 23 / 24 /
later phases, each of which should open with its own kickoff design doc
and reference this synthesis for the established constraints (NG list 1–8,
baseline +180 / Sharpe +0.0822, M1 spread/ATR = 128% premise, audit-
mandated feature allowlist, 8-gate verdict harness, multiple-testing
caveat).
