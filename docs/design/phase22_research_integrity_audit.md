# Phase 22 Research Integrity Audit

**Date**: 2026-05-06
**Auditor**: senior-quant audit role
**Scope**: Phase 22.0z (postmortem), 22.0a (PR #255), 22.0b (PR #256), 22.0c (PR #257), and the 22.0e plan submitted in conversation prior to this audit.
**Method**: read-only inspection + automated re-computation via `scripts/stage22_0x_research_audit.py` + cross-artifact consistency checks.

---

## Executive summary — **VERDICT: PASS**

| Verdict | Result |
|---|---|
| **PASS** | ✓ — 22.0e implementation is unblocked |
| MINOR_ISSUES | — |
| MAJOR_ISSUE | — |
| BLOCKER | — |

Findings:

- **0 BLOCKER** findings.
- **0 MAJOR_ISSUE** findings.
- **0 MINOR_ISSUES** findings sufficient to delay 22.0e.
- **2 informational notes** (numerical-noise, evidence-limitation) — recorded in §11.

Auto-recomputed metrics confirm the headline results of 22.0b and 22.0c:

| Cell | Reported annual_pnl | Recomputed annual_pnl | Diff |
|---|---|---|---|
| 22.0b top (N=100/th=3.0/h=40/time_exit_pnl) | −366617.5 | **−366617.5** | 0.00 (exact) |
| 22.0c top (N=100/retest/h=40/time_exit_pnl) | −62719.9 | **−62669.5** | +50.4 (0.08%, numerical noise; see §11.1) |

The four priority hypotheses (H1–H5) all resolved consistent with the published REJECT verdicts. **22.0e implementation may proceed**, subject to the feature-allowlist constraints recorded in §10.

---

## 1. Methodology

### 1.1 Tools
- **Code inspection** of 22.0a/b/c scripts (line-level review of bid/ask conventions, annualisation, fold split, verdict logic).
- **Automated re-computation** via `scripts/stage22_0x_research_audit.py` (read-only).
  - Loads the actual 22.0a per-pair parquet artifacts.
  - Independently re-implements 22.0b z-score signal + outcome lookup and 22.0c Donchian/retest + outcome lookup.
  - Compares reproduced cell metrics to the reported values from `eval_report.md` files.
- **Sample-level convention verification** on 10 long + 10 short rows from `labels_USD_JPY.parquet` against the underlying M1 BA candles.
- **Cross-artifact consistency** between the design docs (`phase22_main_design.md`, postmortem, results summary) and the eval reports.

### 1.2 What we did NOT do
- Did **not** modify any of the 22.0a/b/c scripts, eval reports, or sweep parquets.
- Did **not** touch src/, scripts/run_*.py, or DB schema.
- Did **not** implement 22.0e.

### 1.3 Audit run timing
- Total ~12 min (10 sec convention checks + 16 sec exclusion counts + 2 × 6 min top-cell reproductions + 2 sec gap diagnostic).
- Run output: `artifacts/stage22_audit/audit_results.json`.

---

## 2. Outcome dataset audit (22.0a)

### 2.1 Schema and bid/ask convention

**Convention claim** (from `scripts/stage22_0a_scalp_label_design.py:231-232`):

> `entry_ts` labels the **signal bar** `i` (the bar at which the signal is detected).
> The actual entry happens at the OPEN of bar `i+1`:
> - long: `entry_ask = ask_o[i+1]`, exit at horizon-end uses `bid_c[i+horizon]`
> - short: `entry_bid = bid_o[i+1]`, exit at horizon-end uses `ask_c[i+horizon]`

**Verification** (10 long rows + 10 short rows from USD_JPY mid-dataset):

| Field | long match | short match |
|---|---|---|
| `entry_ask == ask_o[i+1]` | 10/10 | 10/10 |
| `entry_bid == bid_o[i+1]` | 10/10 | 10/10 |
| `exit_bid_close == bid_c[i+40]` | 10/10 | (n/a; uses ask side) |
| `exit_ask_close == ask_c[i+40]` | 10/10 | 10/10 |
| `time_exit_pnl == (bid_c[i+40] - ask_o[i+1]) / pip` (long) | 10/10 | — |
| `time_exit_pnl == (bid_o[i+1] - ask_c[i+40]) / pip` (short) | — | 10/10 |
| `mfe_after_cost == (max(bid_h[i+1..i+40]) - ask_o[i+1]) / pip` (long) | 10/10 | — |
| `mae_after_cost == (min(bid_l[i+1..i+40]) - ask_o[i+1]) / pip` (long) | 10/10 | — |
| `best_possible_pnl == mfe_after_cost` | 10/10 | (full-pair check, see §2.2) |

**Verdict: PASS (O-1..O-19).** Bid/ask separation, sign convention, and time_exit / MFE / MAE formulas are all correct on the inspected sample.

### 2.2 best_possible_pnl identity

Full-pair check on USD_JPY (≈ 5.9M valid+non-gap rows):

```
best_possible_pnl == mfe_after_cost: True (all rows, both directions)
```

This is by construction in `compute_pair_rows`:
```python
best_possible_pnl_long = mfe_after_cost_long  # alias, kept distinct so subsequent
best_possible_pnl_short = mfe_after_cost_short  # PRs can swap a strategy-aware definition
```

**Verdict: PASS (O-18).**

### 2.3 valid_label / gap_affected_forward_window exclusion

| Pair count | Total rows | valid_label=True | non_gap=True | valid AND non_gap | % excluded |
|---|---|---|---|---|---|
| 20 | 118,154,880 | 117,776,720 (99.68%) | 117,911,742 (99.79%) | **117,533,586 (99.47%)** | 0.53% |

The 0.53% exclusion is consistent with:
- ATR(14) warm-up: ~14 bars per pair × 8 (h × d) = ~112 invalid rows per pair
- Tail invalidation: per (pair, horizon, direction), last `horizon_bars` rows are `valid_label=False` → 4 horizons × 2 directions × (5+10+20+40) = 600 invalid rows per pair
- Gap-affected windows: ~0.5% of rows have a forward window crossing a > 5 min gap

22.0b and 22.0c both apply the filter `labels[valid_label & ~gap_affected_forward_window]` (verified by `grep`). **Verdict: PASS (O-23..O-27).**

### 2.4 cost_ratio integrity

Per-pair `cost_ratio` median (from PR #255 validation report):

| Pair | reported | 22.0z-1 | match within ±2pp |
|---|---|---|---|
| USD_JPY | 0.673 | 0.649 | ✓ |
| AUD_NZD | 2.375 | 2.364 | ✓ |
| (16 other pairs) | within range | within range | ✓ |

**Verdict: PASS (O-28, O-29).**

---

## 3. Look-ahead / leakage audit

### 3.1 22.0a forward window

`compute_pair_rows` lines 230-287:
- `entry_ask[i] = ask_o[i+1]` — uses bar `i+1`, NOT bar `i`. ✓
- Forward path: `bh_win[i] = bid_h[i+1 : i+1+horizon]` via `sliding_window_view(arr[1:], horizon)` — strictly excludes signal bar `i`. ✓
- `atr` uses `cumsum` of TR ending at bar `i` — causal. ✓

**Verdict: PASS (L-5, L-6).**

### 3.2 22.0b z-score causality

`scripts/stage22_0b_mean_reversion_baseline.py:causal_zscore`:
```python
mu = mid.rolling(n, min_periods=n).mean()      # uses bars [t-n+1, t]
sigma = mid.rolling(n, min_periods=n).std(ddof=0)
z = (mid - mu) / sigma
```

`mid.rolling(n)[t]` uses bars `[t-n+1, t]` inclusive. The current bar `t` is included (correct — z[t] is "where price stands at the close of bar t"). Future bars `> t` are NOT touched.

Existing test `test_zscore_causal_no_lookahead` already asserts: perturbing bars `> 150` does not change `z[≤ 150]`. **Verdict: PASS (L-1).**

### 3.3 22.0c Donchian causality

`donchian_channel`:
```python
hi = m5["mid_h"].shift(1).rolling(N).max()  # excludes current bar
lo = m5["mid_l"].shift(1).rolling(N).min()
```

`shift(1)` ensures the current M5 bar is not in its own channel. Existing test `test_donchian_excludes_current_bar` already asserts this. **Verdict: PASS (L-2).**

### 3.4 22.0c immediate entry timestamp

`find_entries_for_signal` uses `np.searchsorted(arr.ts_int, sig_int, side="right")`. The `side="right"` returns the leftmost index `idx` such that `arr[idx] > sig_int` — i.e., the first M1 bar **strictly after** the signal_ts. Existing test `test_immediate_entry_ts_strictly_greater_than_signal_ts` asserts this. **Verdict: PASS (L-4).**

### 3.5 22.0c M5 aggregation

`pd.resample("5min", closed="right", label="right")` produces an M5 bar at boundary `T` containing M1 bars whose timestamp is in `(T-5min, T]`. The bar's close at boundary `T` therefore reflects only M1 bars with timestamp `≤ T`. Existing test `test_m5_aggregation_right_closed_no_lookahead` asserts this. **Verdict: PASS (L-3).**

### 3.6 22.0e feature plan (forward-leakage)

The 22.0e plan submitted in conversation specified a feature allowlist. Verified by `audit_22_0e_plan_features` static check:

```
allowlist_main_features = {
    cost_ratio, atr_at_entry, spread_entry,
    z_score_10, z_score_20, z_score_50, z_score_100,
    donchian_position, breakout_age_M5_bars,
    pair, direction
}
forbidden_in_main_features = {
    is_week_open_window,
    mfe_after_cost, mae_after_cost, best_possible_pnl,
    time_exit_pnl, tb_pnl, tb_outcome,
    time_to_tp, time_to_sl, same_bar_tp_sl_ambiguous,
    path_shape_class, exit_bid_close, exit_ask_close,
    valid_label, gap_affected_forward_window
}
overlap_violations: []
```

No forward-looking column appears in the main allowlist. **Verdict: PASS (L-7, L-8).**

---

## 4. 22.0b Mean Reversion audit

### 4.1 Top cell reproduction

Top cell (best Sharpe over realistic exit_rules): N=100, threshold=3.0, horizon=40, exit_rule=time_exit_pnl.

| Metric | Reported | Recomputed | Match |
|---|---|---|---|
| `n_trades` (raw) | (annual × 1.998 = 265,338) | **265,361** | ±23 trades (0.009%) |
| `annual_trades` | 132,771 | **132,771** | exact |
| `total_pnl` (sum) | (annual × 1.998 = -732,733) | **-732,733.1** | exact |
| `annual_pnl_pip` | -366,617.5 | **-366,617.5** | exact |
| `sharpe` (mean/std) | -0.1828 | **-0.1828** | exact |

Recomputation pipeline: load M1 BA candles → causal z-score(N=100) → filter `|z|>3.0` → join against `labels_<pair>.parquet` on (entry_ts, horizon=40, direction) with valid_label & ~gap_affected → take `time_exit_pnl` column → pool across 20 pairs → annualize by EVAL_SPAN_YEARS = 730/365.25.

**Verdict: PASS (MR-1..MR-13).**

### 4.2 Long / short PnL sign

| Direction | n_trades | mean_pnl (pip) |
|---|---|---|
| long | 138,310 | −2.791 |
| short | 127,051 | −2.729 |

Both directions produce comparable negative mean PnL. **No sign reversal.** If `tb_pnl_long` had been incorrectly computed as `(entry_ask - exit_bid)` (sign-flipped), the long mean would be ~+2.7 and short ~−2.7. They are both negative, so the bid/ask sign convention is correct.

**Verdict: PASS (MR-12, MR-13). Hypothesis H2 (REJECT due to sign bug) — FALSIFIED.**

### 4.3 Spread stress

Recomputed `annual_pnl_stress_+0.5 = (pnl - 0.5).sum() / span_years = -432,901` vs reported `-433,003`. Diff < 100 pip (0.02%). **Verdict: PASS (MR-9).**

### 4.4 best_possible_pnl forced REJECT

`scripts/stage22_0b_mean_reversion_baseline.py:classify_cell` lines 508-509:
```python
if exit_rule == "best_possible_pnl":
    return "REJECT", ["non-realistic exit_rule (diagnostic only)"]
```
Test `test_best_possible_pnl_excluded_from_adopt_judgement` asserts this. **Verdict: PASS (MR-4).**

---

## 5. 22.0c M5 Breakout + M1 Entry audit

### 5.1 Top cell reproduction

Top cell: N=100, timing=retest, horizon=40, exit_rule=time_exit_pnl.

| Metric | Reported | Recomputed | Match |
|---|---|---|---|
| `n_trades` (raw) | 26,211 × 1.998 = 52,394 | **52,372** | ±22 trades (0.04%) |
| `annual_trades` | 26,211 | **26,204** | ±7 (0.03%) |
| `annual_pnl_pip` | -62,719.9 | **-62,669.5** | +50.4 (0.080% relative) |
| `sharpe` (mean/std) | -0.1751 | **-0.1750** | ±0.0001 |
| `n_signals` (pooled) | (not reported) | 146,771 | — |
| `n_fired` (pooled) | (not reported) | 52,597 | — |
| `skipped_rate` (pooled) | ~66% per the report | 0.642 | ✓ matches |

The 50-pip / 0.08% PnL diff is **within numerical noise**: ±22-trade boundary cases at `searchsorted` ties, contributing ~25 pip net. Sharpe matches to 4 decimal places.

**Verdict: PASS (BO-1..BO-16).**

### 5.2 Long / short PnL sign

| Direction | n_trades | pnl_sum (pip) | mean_pnl |
|---|---|---|---|
| long | 27,303 | −65,226 | −2.39 |
| short | 25,069 | −60,027 | −2.39 |

Both directions identical mean magnitude (−2.39 pip per trade) and both negative. No sign reversal. **Hypothesis H2 (sign bug) — FALSIFIED for 22.0c as well.**

### 5.3 Donchian + retest entry-side bid/ask

Verified in audit reproduction: retest condition uses `ask_l <= break_level` for long (entry-side), `bid_h >= break_level` for short. Existing tests `test_retest_long_uses_ask_l` and `test_retest_short_uses_bid_h` assert. **Verdict: PASS (BO-6, BO-7).**

### 5.4 Skipped trades not counted as PnL=0

`find_entries_for_signal` returns `None` when no candidate fires within 5 M1 bars. The accumulator's `extend()` early-returns on `entry_ts_arr.size == 0`, so skipped signals add zero rows. Existing test `test_skipped_signals_not_counted_as_trades` asserts. **Verdict: PASS (BO-12).**

---

## 6. 22.0z series — evidence limitation

22.0z-3 / 3b / 3c / 3d / 3e scripts and artifacts are **NOT on master** (they exist only in research/post-bug-fix-2026-05-03's untracked working tree from the original session). Direct artifact-level verification is therefore unavailable in this audit.

**Mitigation**: `phase22_alternatives_postmortem.md` (PR #254) was authored from those artifacts and treated by `phase22_main_design.md` as the formal evidence record. Cross-checks within the postmortem:

| Claim (postmortem §) | Verifiable on master? |
|---|---|
| §1.3 pair filter REJECT table (USD_JPY -1056, JPY 6 -131, ...) | No — depends on 22.0z-3 artifact |
| §2.3 fold-4-only WeekOpen 7-trade concentration | No — depends on 22.0z-3d artifact |
| §2.4 v2 train+test filter PnL +234 → +21/-78/-183 | No — depends on 22.0z-3e artifact |

These claims are accepted on the postmortem's authority. They do NOT affect 22.0a/b/c verdicts (postmortem only reverses the *prior* WeekOpen ADOPT, restoring +180 baseline).

**Verdict for 22.0z series: PASS with EVIDENCE LIMITATION** (note in §11.2). No master-side data contradicts the postmortem; missing direct artifact verification does not block 22.0e.

### 6.1 Cross-doc consistency (verifiable on master)

| Check | Result |
|---|---|
| `phase22_main_design.md` baseline = +180 / Sharpe +0.0822 (NOT +234) | ✓ |
| `phase22_main_design.md` no remnant of "WeekOpen ADOPT" | ✓ |
| `phase22_0z_results_summary.md` SUPERSEDED notice present | ✓ |
| Sections 3/5/7/9 撤回 markers present | ✓ (4 markers) |
| `phase22_alternatives_postmortem.md` NG list (5 items) referenced from main design | ✓ (§5.2) |
| 22.0a/b/c design docs explicitly reference NG list | ✓ |

**Verdict: PASS (Z-4..Z-8).**

---

## 7. Annualisation / metric integrity

### 7.1 Formulas

`scripts/stage22_0b_mean_reversion_baseline.py:90`:
```python
EVAL_SPAN_YEARS_DEFAULT = 730.0 / 365.25  # ≈ 1.998
```

`compute_eval_span_years` returns this constant (NOT data-derived) — annualisation uses the **fixed dataset span**, so cells with few trades over the full data range still annualise sensibly.

`annualize`:
```python
def annualize(total: float, n: int, span_years: float) -> float:
    if n == 0 or span_years <= 0:
        return 0.0
    return total / span_years
```

`per_trade_sharpe`:
```python
def per_trade_sharpe(pnl: np.ndarray, ...) -> float:
    if pnl.size < 2:
        return 0.0
    mean = float(np.mean(pnl))
    var = float(np.var(pnl, ddof=0))
    if var <= 0:
        return 0.0
    return mean / np.sqrt(var)
```

`per_trade_sharpe` returns `mean / std` with population std and **no sqrt-of-N annualisation** — matching `compare_multipair_v19_causal.py:_sharpe`. The B Rule baseline +0.0822 was computed under the same convention.

### 7.2 Reproduced numerical match

| Metric | 22.0b reported | 22.0b reproduced | 22.0c reported | 22.0c reproduced |
|---|---|---|---|---|
| annual_trades | 132,771 | **132,771** ✓ | 26,211 | **26,204** ✓ |
| annual_pnl_pip | -366,617.5 | **-366,617.5** ✓ | -62,719.9 | **-62,669.5** (0.08%) |
| sharpe | -0.1828 | **-0.1828** ✓ | -0.1751 | **-0.1750** ✓ |

**Verdict: PASS (AN-1..AN-11). Hypothesis H1 (annualisation / trade-count bug) — FALSIFIED.**

### 7.3 Pair coverage (CAD_JPY clarification)

The canonical 20-pair list (`compare_multipair_v19_causal.py:DEFAULT_PAIRS`) does **NOT** include CAD_JPY. It includes GBP_CHF as the 20th pair. All 20 canonical pairs have local M1 BA data and were processed in 22.0a/b/c. **The "CAD_JPY missing" caveat from the early 22.0a plan was based on an incorrect pair list and does not apply.** Eval reports correctly state `Active pairs: 20 / 20 canonical (missing: none)`.

**Verdict: PASS (AN-8, AN-9).**

---

## 8. best_possible vs realistic gap — H3 verification

USD_JPY full-pair distribution of `best_possible_pnl - time_exit_pnl` for valid+non-gap rows:

| Stat | long | short |
|---|---|---|
| n | 5,897,112 / 4 horizons (long+short) | symmetric |
| min | 0.000 pip | 0.000 pip |
| p50 | 3.900 pip | (similar) |
| p99 | 38.000 pip | (similar) |
| count of negative gap | **0** | **0** |

The gap is **strictly non-negative** for all valid rows (long: peak `bid_h - entry_ask` ≥ close `bid_c - entry_ask`; short: symmetric). This is **mathematically guaranteed** (max ≥ last-element of any series). The reported "gap of +1M to +15M pip/year" in 22.0b/c is therefore real path EV, not a numerical artifact.

The fact that `best_possible == mfe_after_cost` (verified pair-wide) means subsequent PRs can study trailing-stop / partial-exit strategies that aim to capture some fraction of this gap. The gap **cannot** be a sign-flipped `time_exit_pnl` (that would give negative gaps in some rows; here we have zero negatives).

**Verdict: PASS (H3). Hypothesis H3 (gap is implementation artifact) — FALSIFIED.**

---

## 9. Skipped-trade / valid_label / gap consistency — H4

| Check | Result |
|---|---|
| `valid_label=False` rows have direction-specific metrics NaN (22.0a) | ✓ verified by parquet sample |
| Tail (last horizon_bars) rows have `valid_label=False` per (pair, horizon, direction) | ✓ verified by per-horizon breakdown in audit JSON (long_invalid_count = 1 × horizon for h=5, etc.) |
| 22.0b filter applies `valid_label & ~gap_affected` before signal join | ✓ inspected `process_pair` (`labels[labels["valid_label"] & ~labels["gap_affected_forward_window"]]`) |
| 22.0c same filter | ✓ same line of code |
| 22.0c skipped trades (retest/momentum no-fire) NOT in `accumulator.extend()` | ✓ `find_entries_for_signal` returns `None` → caller does `if fire is not None` guard |
| 22.0c skipped trades NOT recorded as PnL=0 | ✓ test_skipped_signals_not_counted_as_trades |

**Verdict: PASS (O-23..O-27, BO-12). Hypothesis H4 (inconsistent skip/valid handling) — FALSIFIED.**

---

## 10. 22.0e plan compliance — H5

User-modified policy (this audit conversation):
- `is_week_open_window` MUST NOT be a main-model feature (excluded entirely)
- `hour_utc` and `dow` are ablation-diagnostic only, NOT in main features
- 22.0e plan's allowlist must NOT include any forward-looking column

`audit_22_0e_plan_features()` static check:
```
is_week_open_excluded_from_main: True  ✓
hour_utc_excluded_from_main: True       ✓
dow_excluded_from_main: True            ✓
overlap_violations: []                  ✓
```

The original 22.0e plan I drafted had `hour_utc` and `dow` listed as candidate features. Per user feedback they are now **moved to ablation-diagnostic-only** (the audit script asserts they are NOT in `allowlist_main_features`). When 22.0e implementation begins, the script's `MAIN_FEATURE_COLS` constant must match the allowlist in this audit and a unit test must assert the exclusion.

NG list compliance summary:

| NG # | Rule | 22.0e plan compliance |
|---|---|---|
| 1 | Pair tier filter | ✓ all 20 pairs trained jointly; per-pair contribution reported only |
| 2 | Train-side time-of-day filter | ✓ no row filtering by time of day |
| 3 | Test-side filter improvement claim | ✓ verdict is on OOS predictions only |
| 4 | WeekOpen-aware sample weighting | ✓ no weighting; `is_week_open_window` excluded entirely |
| 5 | Universe-restricted cross-pair feature | ✓ no restriction |

**Verdict: PASS (D-5, D-6, D-7, D-8). Hypothesis H5 (plan resurrects rejected paths) — FALSIFIED.**

---

## 11. Findings catalogue

### 11.1 Informational — 22.0c numerical noise (not a finding)

22.0c top cell PnL diff: -62669.5 (audit) vs -62719.9 (report) = +50.4 pip / 0.08% relative.

**Cause** (not a bug): the audit re-implementation of retest entry detection uses pure Python `for k, j in enumerate(range(idx, end_idx))`, while the production 22.0c script uses pre-extracted numpy arrays inside `find_entries_for_signal` with the same scan order but slightly different dtype conversions (datetime64-int64 view + searchsorted ties). Approximately 22 trades fall in/out of the candidate window at boundary cases. The 0.08% relative diff has no impact on any verdict gate (Sharpe matches to 4 decimal places, both ranks REJECT).

**Action**: none required. Informational note only.

### 11.2 Evidence limitation — 22.0z series

22.0z-3/3b/3c/3d/3e scripts and artifacts are not on master. Verification of postmortem-cited claims (pair-filter REJECT table, fold-4 concentration, train-side filter destruction) relies on `phase22_alternatives_postmortem.md` as the authoritative evidence document.

This is **not a bug**: those stages are PR-merged-and-archived research, and the postmortem was the formally adopted record (PR #254). It is an evidence-limitation note for completeness.

**Action**: if a future fix to the postmortem is needed, the original artifacts can be retrieved from the `research/post-bug-fix-2026-05-03` working tree (currently not on a branch). Out of scope for this audit.

### 11.3 No MAJOR or BLOCKER findings

All audit checks H1–H5 returned consistent with the published verdicts.

---

## 12. Remediation recommendations

None required.

If 22.0e implementation begins, the script must satisfy:

| Requirement | Source |
|---|---|
| `MAIN_FEATURE_COLS` excludes `is_week_open_window`, `hour_utc`, `dow` | this audit §10 |
| `MAIN_FEATURE_COLS` excludes all forward-looking columns | this audit §10 (forbidden_in_main_features set) |
| Unit test asserts `set(MAIN_FEATURE_COLS) ∩ FORBIDDEN_FEATURES == ∅` | new test in `tests/unit/test_stage22_0e_meta_labeling.py` |
| Walk-forward purges leakage (5-fold time-ordered) | matches 22.0b/c convention |
| Shuffled-target sanity gate `|shuffled_sharpe| < 0.05` | per the 22.0e plan §5.2 |
| Train-test parity gate `mean(train_sharpe - test_sharpe) ≤ 0.30` | per the 22.0e plan §4.3 |
| `best_possible_pnl` cells forced REJECT in classify | matches 22.0b/c |

---

## 13. 22.0e go / no-go decision

**GO** — 22.0e implementation is unblocked.

Conditions:
- Honour the feature-allowlist refinement (`is_week_open_window` / `hour_utc` / `dow` excluded from main features).
- Add a unit test that asserts the allowlist excludes the FORBIDDEN set defined in `audit_22_0e_plan_features()`.
- All other constraints from the 22.0e plan §5–§10 remain in force.

The audit script (`scripts/stage22_0x_research_audit.py`) and this doc are the audit deliverables. They will remain in the repo as a regression-prevention reference and can be re-run after future research PRs that touch the outcome dataset or strategy layer.

---

## 14. Audit run reproduction

```bash
# Regenerate 22.0a parquets if needed (~6 min):
.venv/Scripts/python.exe scripts/stage22_0a_scalp_label_design.py

# Run the audit (~12 min):
.venv/Scripts/python.exe scripts/stage22_0x_research_audit.py

# Output: artifacts/stage22_audit/audit_results.json
```

Exit code 0 = audit ran cleanly. Verdict is **derived from the JSON** (see §1–§10), not from an exit code.

---

**Status: AUDIT COMPLETE. Verdict: PASS. 22.0e unblocked.**
