# Phase 28.0b-α — A4 Monetisation-Aware Selection Design Memo

**Type**: doc-only sub-phase α design memo
**Status**: pre-states Phase 28.0b-β scope; does NOT initiate the β-eval
**Branch**: `research/phase28-0b-alpha-a4-monetisation-aware-selection`
**Base**: master @ `156630c` (post-PR #340 / Phase 28 A4 non-quantile cell shapes scope amendment)
**Pattern**: analogous to PR #337 (Phase 28.0a-α A1) / PR #331 (Phase 27.0f-α R7-C) / PR #325 (Phase 27.0d-α S-E) sub-phase α design memos
**Date**: 2026-05-17

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28.0b-α design memo**. It pre-states the **closed 4-rule allowlist** (R1 / R2 / R3 / R4), the **fixed S-E score source**, the **6-cell structure** (4 rule variants + C-a4-top-q-control + C-sb-baseline), the **D10 single-score-artifact form** (1 S-E regressor + 1 C-sb multiclass head), the **formal H-C2 falsifiable hypothesis with 4-outcome ladder**, the **3 anti-collapse guards (NG#A4-1 / NG#A4-2 / NG#A4-3)**, and the **R-T1 formal absorption under A4 frame**. It does **NOT**:*
>
> - *initiate the β-eval (no `scripts/stage28_0b_*.py`, no `tests/unit/test_stage28_0b_*.py`, no `artifacts/stage28_0b/`);*
> - *create any additional scope amendment (PR #340 covers the Clause 2 update; no further amendment required);*
> - *elevate R-B / R-T3 (carry-forward register status preserved per PR #334);*
> - *modify the §10 baseline numeric or any prior verdict;*
> - *touch `src/` / `scripts/` / `tests/` / `artifacts/` / `.gitignore` / `MEMORY.md`.*
>
> *The β-eval implementation (PR `phase28-0b-beta-...`) is a **separate later PR**. The pre-stated parameters (c, [p_lo, p_hi], q_per_pair, K) and the closed 4-rule allowlist are fixed at α and cannot be changed at β; any change requires a memo amendment PR back to α.*

Same approval-then-defer pattern as PR #325 / PR #331 / PR #337.

---

## 1. A4 mission statement

The 6-eval evidence picture (Phase 27 5-eval + Phase 28.0a-β) consolidated at PR #339 §3.1 records the single most informative observation of the inheritance chain: **the val-selector picked the inherited C-sb-baseline cell in 6/6 sub-phases**. Every score-axis intervention (S-C / S-D / S-E / L1 / L2 / L3) and every feature-axis intervention (R7-C) and every selection-trim intervention (R-T2) produced a val-selected (cell\*, q\*) record that was bit-identical to the baseline. At the same time, the **score itself can produce strong ranking signals**: S-E (27.0d) test Spearman +0.4381, 28.0a L2 test Spearman +0.466, 28.0a L3 test Spearman +0.459.

The implication of these two facts is structural: **the score-half of monetisation is solved**, but the **selection-half** — the rule that turns score into trades — is **not**. The conventional top-quantile-on-score selection rule never produces a val-superior cell, no matter how the score is computed.

**Phase 28.0b-α exists** to pre-state the design of the **A4 sub-phase**: a **selection-rule redesign on a fixed S-E score** that tests 4 structurally distinct rule variants (R1 absolute-threshold / R2 middle-bulk / R3 per-pair quantile / R4 top-K per bar) against the inherited top-q-on-score rule. The mission is **NOT** to improve the score further; the mission is to **redesign how the score becomes trades**.

This is A4 per Phase 28 kickoff PR #335 §5.5, made primary by the post-28.0a routing review PR #339 §14.1 (prior 35-45 %), and unblocked at the cell-shape level by PR #340 (Clause 2 amendment admitting R1 / R4 non-quantile cells under A4 sub-phase scope). The β-eval will be implemented in a separate later PR (`phase28-0b-beta-...`).

---

## 2. Why A4 is NOT Phase 27 / 28 inertia (5 distinctions)

Phase 28 kickoff PR #335 §3 listed five Phase 27 inertia routes that are NOT admissible. 28.0a-α §2 added A1 single-loss-variant micro-redesign as a NOT-admissible extension. A4's design must be structurally distinct from each. Per axis:

### 2.1 A4 ≠ R-T2 quantile-family trim (27.0e-β)

- **R-T2 (27.0e)**: same top-q-on-score rule with a trimmed q grid {5, 7.5, 10}. The rule structure is unchanged; only the q values differ.
- **A4 (28.0b)**: rule structure itself is replaced. R1 is non-quantile (absolute inequality); R2 selects a percentile range (not a top tail); R3 is per-pair (not global); R4 is per-bar (not per-row).
- **Anti-collapse guard NG#A4-1** (§6) makes this enforceable: a top-q-on-score sweep with new q values is **NOT admissible** under A4. The 4 rules in §4 are the closed allowlist.

### 2.2 A4 ≠ score-only-sweep collapse (Phase 27 inertia §3 item 4)

- **Score-only sweep**: same C-sb-baseline cell with a different score input. Rule structure unchanged.
- **A4**: **score is fixed to S-E** (§5). 4 distinct rule structures are tested against the same S-E score.
- The 6-eval picture has already exhausted the score axis; A4 fixes the score and varies the rule.

### 2.3 A4 ≠ R7-C feature widening (27.0f-β)

- **R7-C (27.0f)**: same top-q rule, same score backbone, with 3 additive regime features.
- **A4 (28.0b)**: **feature surface unchanged** (R7-A only). Score backbone unchanged (S-E). Only the rule changes.

### 2.4 A4 ≠ A1 objective redesign (28.0a-β)

- **A1 (28.0a)**: same top-q rule, same R7-A feature surface, with 3 alternative loss functions (L1 / L2 / L3).
- **A4 (28.0b)**: **loss / objective unchanged** (S-E backbone = symmetric Huber α=0.9 on R7-A). Only the rule changes.

### 2.5 A4 ≠ C-sb-baseline-anchored sweep

- **C-sb-baseline-anchored sweep**: any sub-phase that only redefines q% / score on the inherited C-sb cell.
- **A4**: builds **new rule cells** (C-a4-R1 / C-a4-R2 / C-a4-R3 / C-a4-R4) with structurally distinct cell shapes (some non-quantile per PR #340). C-sb-baseline is preserved as the FAIL-FAST reproduction cell only.

The 5 distinctions are jointly enforced by NG#A4-1 / NG#A4-2 / NG#A4-3 (§6) and by the closed 4-rule allowlist (§4) with α-fixed numerics (no β grid sweep).

---

## 3. R-T1 formal absorption under A4 frame

### 3.1 Carry-forward register status before this PR

Per PR #334 §11 (Phase 27 closure memo) and PR #339 §3.4 / §13:

- **R-T1** (selection-rule redesign): deferred-not-foreclosed; prior 25-35 %; reframing under A4 admissible.
- **R-B** (different feature axis): deferred-not-foreclosed; prior 15-25 %; reframing under A3 / A0 / A2 admissible (+ scope amendment).
- **R-T3** (concentration formalisation): below-threshold; deferred; NOT a dissent.

### 3.2 R-T1 absorption declaration (effective on this PR merge)

**R-T1 is formally absorbed under A4 sub-phase scope** by this design memo merge. Specifically:

- **H-C2** (the falsifiable hypothesis pre-stated in §10) **= R-T1 elevation under A4 frame**. The four rules in §4 (R1 absolute-threshold / R2 middle-bulk / R3 per-pair quantile / R4 ranked-cutoff top-K) are exactly the four examples that PR #334 §11 R-T1 carry-forward register pre-stated as R-T1's H-C2 hypothesis space (PR #336 §6.3; PR #339 §6.3). Testing them inside A4's 4-rule closed allowlist tests R-T1's H-C2 directly.
- **No independent R-T1 elevation PR** is initiated. R-T1's carry-forward status transitions to "absorbed under A4 sub-phase scope" with this merge.
- **R-T1's outcome is resolved by A4's H-C2 outcome** (per-rule 4-row ladder; §10). PASS = R-T1 elevated and supported. PARTIAL_SUPPORT / FALSIFIED_RULE_INSUFFICIENT / PARTIAL_DRIFT_TOPQ_REPLICA at all 4 rules = R-T1 falsified at this architecture / feature / target setup.

### 3.3 What absorption does NOT change

- **R-B and R-T3 remain in PR #334 carry-forward status** (deferred-not-foreclosed / below-threshold). This absorption is R-T1-specific and does not affect R-B or R-T3.
- **PR #334 carry-forward register file is not retroactively edited.** The transition is recorded in the present design memo and inherited forward.
- **R-T1's H-C2 hypothesis threshold parameters** (val Sharpe lift ≥ +0.05, trade count ≥ 20,000) are inherited verbatim into A4's H-C2 (§10).
- **R-T3 below-threshold status is not affected.** R-T3 revival still requires its own routing decision + Clause 2 amendment (per PR #334 §12 / PR #339 §11).

### 3.4 What absorption requires of the β-eval

The β-eval PR (`stage28_0b_a4_monetisation_aware_selection_eval.py`) must:

- Implement the 4 rules in §4 exactly per the α-fixed numerics (NG#A4-1).
- Document in its eval_report §13 that "H-C2 outcome row binding = R-T1 elevation under A4 frame resolution" — language inherited from this design memo §3.
- Treat R-T1 carry-forward as resolved by H-C2's per-rule outcomes; do not separately re-test R-T1.

---

## 4. Closed 4-rule allowlist (formal pre-statement)

The four selection rules and their α-fixed numerics. PR #340 admissibility binding: R1 / R4 are non-quantile cell shapes under A4 sub-phase scope; R2 / R3 are quantile-based. **All numerics fixed at α; no β grid sweep (NG#A4-1).**

### 4.1 R1 — absolute-threshold (non-quantile; PR #340 admissible)

- **Cell definition**: `trade if S-E score > c` (per-row inequality test)
- **Threshold fit**: `c` = **per-pair val-median of S-E score** (computed as `np.percentile(val_score[pair], 50)` per pair; deterministic; ties broken by sort order)
- **Rationale**: per-pair median absorbs cross-pair score-level differences (e.g., EUR_USD and GBP_JPY have different S-E score distributions). The rule selects rows that are above-median *for their own pair*, which is structurally different from a global top-quantile rule.
- **Cell shape**: per-row inequality; not a quantile rank. Number of selected rows is approximately 50% of val/test per pair (since c is the median; varies on test due to fit-on-val drift).
- **NG#A4-1 enforcement**: c is val-fit deterministic median; no grid sweep over [25th, 50th, 75th] percentiles.

### 4.2 R2 — middle-bulk (quantile-based; global)

- **Cell definition**: `trade if percentile(S-E score) ∈ [p_lo, p_hi]`
- **Pre-stated cutoffs**: `[p_lo, p_hi] = [40, 60]` (global percentiles; fixed at α; no grid sweep over [30, 70] / [45, 55] etc.)
- **Rationale**: 27.0e R-T2 showed that the **top tail is monotonically adversarial** (Sharpe gets worse as q decreases from 40 → 10 → 5). The middle-bulk rule explicitly **avoids both tails** — trades the rows whose S-E score is in the 40th-60th global percentile range. If "top tail is adversarial AND bottom tail is also adversarial" is true (the simplest reading of 27.0e), middle-bulk should monetize.
- **Cell shape**: per-row range test on global val-rank percentile. Approximately 20% of val/test selected.
- **Cutoff fit**: `cutoffs = np.percentile(val_score_global, [40, 60])`; deterministic.
- **NG#A4-1 enforcement**: [40, 60] is α-fixed; no grid sweep.

### 4.3 R3 — per-pair quantile (quantile-based per pair)

- **Cell definition**: for each pair, trade rows whose S-E score is in the **top q_per_pair %** of that pair's val distribution
- **Pre-stated q_per_pair**: `q_per_pair = 5 %` (top 5% per pair; computed as `np.percentile(val_score_per_pair, 95)` per pair; trade if score ≥ per-pair 95th percentile)
- **Rationale**: 6-eval picture's baseline n_trades = 34,626 is suspected to be **USD_JPY-heavy concentrated** (per per-pair concentration audits at 27.0d / 27.0f / 28.0a). Per-pair top 5% spreads the selection across all 20 pairs by construction — directly attacks concentration as a confound.
- **Cell shape**: per-pair top-quantile. Approximately 5% × 20 pairs = matches global top 5% in count but is **distributed evenly across pairs**.
- **Cutoff fit**: `cutoff_per_pair = np.percentile(val_score[pair], 95)` per pair; deterministic.
- **NG#A4-1 enforcement**: q_per_pair = 5% is α-fixed; no per-pair grid sweep.

### 4.4 R4 — top-K per bar (non-quantile; PR #340 admissible)

- **Cell definition**: at each unique `signal_ts` (M5 bar boundary), select the **K highest-scoring** rows (all pairs compete for K slots per bar)
- **Pre-stated K**: `K = 1` (deterministic "best-of-bar" selection; α-fixed; no grid sweep over K=2/3/5)
- **Rationale**: 27.0e's "top-tail adversarial" pattern is consistent with "**multiple high-score signals cluster in the same bar and that bar is collectively adversarial**". K=1 enforces 1 trade per bar regardless of how many signals cluster — directly attacks bar-level adverse selection.
- **Cell shape**: per-bar selection (group by `signal_ts`, take `argmax(score)`); not per-row independent. Number of selected rows ≈ number of unique signal_ts (bars with any signal) ≈ a few tens of thousands across val/test.
- **Fit**: K=1 is deterministic; no fit needed. Just group by signal_ts and take argmax.
- **NG#A4-1 enforcement**: K=1 is α-fixed; no grid sweep over K=2/3/5.

### 4.5 Why 4 rules exactly (closed allowlist)

The 4 rules jointly span four orthogonal hypotheses about how the val-selector-picks-baseline pattern can be broken:

- **R1** (absolute-threshold per-pair median): "the issue is cross-pair score-level differences; relative-to-own-pair selection helps"
- **R2** (middle-bulk global): "both tails are adversarial; middle range monetizes"
- **R3** (per-pair top-quantile): "the issue is concentration; per-pair budget helps"
- **R4** (top-K=1 per bar): "the issue is bar-level adverse selection; one-trade-per-bar helps"

The 4 rules do **not** include cost-aware ranking, joint training of score+threshold, or position-conditional selection by design — these would expand the scope beyond a single sub-phase. **No 5th rule** is admissible at β without a memo amendment PR back to α (NG#A4-1).

### 4.6 No grid sweep within a rule

Within R1, `c` is per-pair val-median (deterministic; no grid over [25%, 50%, 75%]). Within R2, `[p_lo, p_hi]` is fixed `[40, 60]` (no grid over [30, 70] / [45, 55]). Within R3, `q_per_pair` is fixed at 5% (no grid over 3% / 5% / 10%). Within R4, `K` is fixed at 1 (no grid over K=2/3/5). **NG#A4-1** enforces all of these.

---

## 5. Fixed S-E score source (formal commitment)

### 5.1 Choice of S-E

A4 commits to a **single fixed score source** across all 4 rules: **S-E** (LightGBM regressor with symmetric Huber loss α=0.9 on R7-A features). Specifically:

- **Architecture**: `build_pipeline_lightgbm_regression_widened()` (PR #325 / 27.0d-α §4 / D-J1)
- **Loss**: symmetric Huber with `alpha = 0.9` (PR #325 inherited)
- **Features**: R7-A (4 features: `pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`)
- **Sample weight**: 1 (no sample weighting; symmetric Huber backbone — distinct from 28.0a L1 / L2 / L3 weighted variants)
- **Score extraction**: `compute_picker_score_s_e(regressor, X)` (PR #325 / 27.0d-α inherited)

### 5.2 Why S-E (not L2 / L3)

The 6-eval picture has produced three score variants with PASS-level Spearman:

- **S-E (27.0d)**: test Spearman +0.4381 — reproduced in 27.0f C-se-r7a-replica and 28.0a C-a1-se-r7a-replica
- **L2 (28.0a)**: test Spearman +0.466 — highest in inheritance chain
- **L3 (28.0a)**: test Spearman +0.459

**S-E is the most-reproduced score**: it has been used as the within-eval ablation control at both 27.0f and 28.0a, and bit-tight reproduces 27.0d's C-se cell within tolerance in both cases. L2 / L3 have stronger raw Spearman but **carry the 28.0a A1 objective-axis falsification** (all 3 closed loss variants FALSIFIED_OBJECTIVE_INSUFFICIENT). Using S-E in A4 keeps the score source clean of A1-axis contamination and isolates the rule-axis test.

### 5.3 No alternate score source admissible at β

The β-eval PR may not substitute L2 / L3 / a new score variant for S-E. Score-axis variation is **NG#A4-1 inertia collapse** (the A1 sub-phase already exhausted score variation). A future score-class redesign (e.g., A0 architecture change producing a structurally different score) requires a separate sub-phase under its own scope amendment.

---

## 6. Anti-collapse guards (NG#A4-1 / NG#A4-2 / NG#A4-3)

Three binding guards at α, enforced at β.

### 6.1 NG#A4-1 — closed 4-rule allowlist, no grid sweep, fixed score

The selection rule MUST be one of {R1, R2, R3, R4} as defined in §4 with the α-fixed numerics (`c = per-pair val-median`, `[p_lo, p_hi] = [40, 60]`, `q_per_pair = 5%`, `K = 1`).

- A scalar grid sweep over a rule's numeric (e.g., c at [25%, 50%, 75%] / K=2,3,5) is **NOT admissible**. (Would collapse to R-T2-style trim inertia.)
- Adding a 5th rule at β is **NOT admissible** without a memo amendment PR back to α.
- Substituting L2 / L3 / a new score variant for S-E is **NOT admissible**. Score is fixed.
- Top-q-on-score variants (other q values; the inherited Phase 27 / 28 rule) are tested **only inside C-a4-top-q-control**; not as additional rule variants.

### 6.2 NG#A4-2 — per-rule verdict required

Each rule {R1, R2, R3, R4} must produce its own outcome per the 4-row ladder (§10.2). Aggregate-only verdicts (e.g., "average of four rules is PARTIAL_SUPPORT") are **NOT admissible**.

- The eval_report must list one outcome per rule.
- The sub-phase aggregate verdict (§10.3) is derived from the four per-rule outcomes; it is NOT a substitute for the per-rule outcome.

### 6.3 NG#A4-3 — C-a4-top-q-control mandatory (rule-axis null)

The 6-cell structure (§7) MUST include **C-a4-top-q-control** — a vanilla top-q-on-S-E selection cell across the inherited quantile family {5, 10, 20, 30, 40}.

- C-a4-top-q-control is the **rule-axis null**: it tests the same S-E score with the same conventional top-q rule used by all 6 prior sub-phases. It must reproduce 27.0d C-se / 28.0a C-a1-se-r7a-replica within drift tolerance (§9).
- If any C-a4-Rx ≈ C-a4-top-q-control within tolerance at the val-selected configuration (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 %), that rule is recorded as **PARTIAL_DRIFT_TOPQ_REPLICA** (§10.2 row 4). The rule had zero effect on monetization regardless of structural difference. Analogous to 27.0f H-B6 FALSIFIED_R7C_INSUFFICIENT / 28.0a PARTIAL_DRIFT_R7A_REPLICA.
- Omitting C-a4-top-q-control is **NOT admissible** under NG#A4-3.

---

## 7. Cell structure (6 cells × variable quantile/non-quantile)

The β-eval evaluates **6 cells**. R1 / R2 / R3 / R4 are single-cell variants (one configuration each per α-fixed numerics; no quantile sweep). C-a4-top-q-control and C-sb-baseline retain the inherited quantile family {5, 10, 20, 30, 40} for cross-phase comparability.

| # | Cell ID | Picker / score | Cell shape | Configuration | Purpose |
|---|---|---|---|---|---|
| 1 | **C-a4-R1** | S-E (regressor_pred) | non-quantile (per-row inequality) | trade if S-E score > per-pair val-median | A4 rule 1 — absolute-threshold |
| 2 | **C-a4-R2** | S-E (regressor_pred) | quantile (range) | trade if percentile ∈ [40, 60] global | A4 rule 2 — middle-bulk |
| 3 | **C-a4-R3** | S-E (regressor_pred) | quantile (per-pair) | trade if score ≥ per-pair 95th percentile | A4 rule 3 — per-pair top 5% |
| 4 | **C-a4-R4** | S-E (regressor_pred) | non-quantile (per-bar) | argmax(score) per signal_ts (K=1) | A4 rule 4 — top-K per bar |
| 5 | **C-a4-top-q-control** | S-E (regressor_pred) | quantile (top-q, swept) | top-q over {5, 10, 20, 30, 40} | NG#A4-3 mandatory; rule-axis null; reproduces 27.0d / 28.0a control |
| 6 | **C-sb-baseline** | S-B raw (P(TP) − P(SL)) | quantile (top-q, swept) | top-q over {5, 10, 20, 30, 40} | §10 baseline reproduction FAIL-FAST |

Total records to evaluate: 4 single-cell rule variants (1 record each = 4) + C-a4-top-q-control (5 quantile points) + C-sb-baseline (5 quantile points) = **14 (cell, configuration) records**.

### 7.1 D10 single-score-artifact form

The β-eval fits **2 artifacts** (extension of 28.0a's 4-artifact form, scaled down because all rules share the same score):

- **1 S-E regressor** (symmetric Huber α=0.9 on R7-A; sample_weight=1; reproduces 27.0d C-se / 28.0a C-a1-se-r7a-replica): shared across C-a4-R1 / C-a4-R2 / C-a4-R3 / C-a4-R4 / C-a4-top-q-control as the score source. **Fit once on full R7-A-clean train.**
- **1 multiclass head** (C-sb-baseline; LightGBMClassifier multiclass; same as 27.0f / 28.0a): used only for C-sb-baseline FAIL-FAST reproduction. **Fit once.**

Selection rules R1 / R2 / R3 / R4 are **deterministic post-fit operations** on the S-E score: they do not require their own artifacts. The β-eval applies each rule's deterministic selection logic to the val/test S-E predictions and computes per-rule (cell, configuration) metrics.

### 7.2 Row-set policy (A4-specific; simpler than 27.0f-β)

All 6 cells share the **R7-A-clean parent row-set** (same as 28.0a-β; no R7-C row-drop in this sub-phase). Fix A row-set isolation contract is not exercised under A4. The structural simplicity is preserved by construction.

---

## 8. C-sb-baseline reproduction (FAIL-FAST; inherited)

The β-eval embeds the inherited **C-sb-baseline reproduction check** from 27.0c-α §7.3 / 27.0d / 27.0e / 27.0f / 28.0a. The check runs after all 6 cells have been evaluated and before any verdict is emitted.

| Metric | §10 baseline (immutable; PR #335 §10) | Tolerance |
|---|---|---|
| n_trades (test, val-selected q\*=5 on C-sb-baseline) | 34,626 | exact (±0) |
| Sharpe (test) | -0.1732 | ±1e-4 |
| ann_pnl (test, pip) | -204,664.4 | ±0.5 |

**Mismatch behaviour**: `BaselineMismatchError` HALT — the sub-phase β-eval terminates without emitting a verdict. **FAIL-FAST**. Inherited harness: `check_c_sb_baseline_match()` (verbatim from 28.0a-α / 27.0f-α).

---

## 9. C-a4-top-q-control drift check vs 27.0d C-se / 28.0a C-a1-se-r7a-replica

The C-a4-top-q-control cell reproduces 27.0d's C-se cell and 28.0a's C-a1-se-r7a-replica cell (all three use the same S-E regressor backbone with sample_weight=1). The β-eval embeds a **DIAGNOSTIC-ONLY WARN** drift check (NOT HALT):

- **Tolerance**: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 % of magnitude (verbatim from 27.0f D-AA10 / 28.0a-α §8)
- **Mismatch behaviour**: `UserWarning` emitted; eval_report records WARN flag; **NO HALT**. The negative-result interpretation depends on the control reproducing prior; if drift WARN fires, the routing review must consider whether the rule-axis test was valid against the same baseline as prior sub-phases.

---

## 10. H-C2 formal pre-statement (4-outcome ladder per rule)

PR #336 §6.3 placeholder H-C2 + PR #339 §6.3 routing review references → formal pre-statement.

### 10.1 H-C2 hypothesis (formal)

> **H-C2**: At least one of the four closed selection rules {R1 absolute-threshold, R2 middle-bulk, R3 per-pair quantile, R4 top-K per bar} will produce a val-selected configuration on the C-a4-Rx cell satisfying **all** of:
>
> 1. **H2 PASS**: val Sharpe ≥ §10 baseline val Sharpe + **+0.05 absolute** (i.e., val Sharpe ≥ -0.1363)
> 2. **H1m preserved**: val-selected cell Spearman ≥ **+0.30** (S-E backbone gives ~+0.438 baseline; modest discrimination loss tolerated)
> 3. **H3 PASS**: trade count ≥ **20,000** (avoid degenerate low-trade-count Sharpe lifts)
> 4. **C-sb-baseline reproduction PASS**: n_trades=34,626 exact / Sharpe Δ ≤ ±1e-4 / ann_pnl Δ ≤ ±0.5 pip
>
> **OR** H-C2 is FALSIFIED at the rule.

**H-C2 = R-T1 elevation under A4 frame resolution** (per §3.2). PASS at any rule = R-T1 elevated and supported. All-rules FALSIFIED = R-T1 falsified at this architecture / feature / target setup.

### 10.2 4-outcome ladder per rule (precedence: row 4 > 1 > 2 > 3)

The β-eval emits **one of four outcomes** for each rule {R1, R2, R3, R4}. Precedence is enforced (PARTIAL_DRIFT_TOPQ_REPLICA checked first per NG#A4-3).

| Row | Outcome | Per-rule condition | Aggregate implication |
|---|---|---|---|
| **4** | **PARTIAL_DRIFT_TOPQ_REPLICA** (checked first) | C-a4-Rx ≈ C-a4-top-q-control (val-selected q\*) within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 % magnitude) | Rule had zero effect on monetization regardless of structural difference; analogous to 27.0f H-B6 FALSIFIED / 28.0a PARTIAL_DRIFT_R7A_REPLICA. All-rules in this row strongly reinforces H-B9. |
| **1** | **PASS** | All 4 H-C2 conditions (§10.1) satisfied at the C-a4-Rx cell | If 1+ rule PASS and C-sb-baseline reproduction intact, sub-phase verdict = SPLIT_VERDICT_ROUTE_TO_REVIEW; PROMISING_BUT_NEEDS_OOS candidate (ADOPT_CANDIDATE wall preserved). |
| **2** | **PARTIAL_SUPPORT** | val Sharpe lift ∈ [+0.02, +0.05) AND H1m ≥ +0.30 AND H3 PASS AND C-sb-baseline reproduction intact | If 1+ rule PARTIAL_SUPPORT and 0 PASS, sub-phase verdict = REJECT_NON_DISCRIMINATIVE (sub-threshold). |
| **3** | **FALSIFIED_RULE_INSUFFICIENT** (default) | val Sharpe lift < +0.02 OR other H-C2 conditions fail | If all 4 rules FALSIFIED, sub-phase verdict = REJECT_NON_DISCRIMINATIVE; H-B7 strongly falsified at this architecture; H-B9 prior strengthened. |

### 10.3 Aggregate decision rule

- If **any rule** records PASS, sub-phase verdict = **SPLIT_VERDICT_ROUTE_TO_REVIEW** (val-selector may still pick C-sb-baseline; cross-cell aggregation per §11 decides). H2 PASS = PROMISING_BUT_NEEDS_OOS only per Clause 1 (ADOPT_CANDIDATE wall preserved).
- If **0 rules** PASS but **1+ rule** PARTIAL_SUPPORT, sub-phase verdict = **REJECT_NON_DISCRIMINATIVE** (sub-threshold).
- If **all 4 rules** FALSIFIED_RULE_INSUFFICIENT, sub-phase verdict = **REJECT_NON_DISCRIMINATIVE** (clean H-C2 falsification).
- If **all 4 rules** PARTIAL_DRIFT_TOPQ_REPLICA, sub-phase verdict = **REJECT_NON_DISCRIMINATIVE** with diagnostic note "rule change does not move score regardless of variant; strong H-B9 reinforcement; route to A0 architecture redesign or Phase 28 next routing review".

### 10.4 H-C2 falsification at all 4 rules — implications

If all 4 rules end at FALSIFIED_RULE_INSUFFICIENT or PARTIAL_DRIFT_TOPQ_REPLICA, H-C2 is falsified at this architecture / feature / target setup. **R-T1 carry-forward is resolved as falsified under A4 absorption.** The post-28.0b routing review would then update:

- H-B7 prior: STRENGTHENED → FALSIFIED-under-A4 (rule misspecification is not the binding constraint at this architecture)
- H-B9 prior: STRENGTHENED → further STRENGTHENED (seam exhausted at this architecture confirmed by 7th data point)
- A0 prior: 25-35 % → 35-45 % (becomes the most attractive Phase 28 next move)
- A2 prior: 15-25 % → 20-30 % (target adequacy concern slightly reinforced)
- A3 prior: 10-20 % → unchanged
- R-T1 carry-forward status: deferred-not-foreclosed (absorbed and falsified under A4) → not foreclosed (could be revived under a different architecture / target setup in Phase 29+) but no further Phase 28 revival expected

---

## 11. Selection-overfit guard (2-layer; verbatim inheritance)

The β-eval respects the 2-layer selection-overfit guard inherited from PR #325 / #328 / #332 / #338:

### 11.1 Layer 1 — validation-only configuration selection

The val-selected configuration per cell (cell\* alone for single-cell rules R1 / R2 / R3 / R4; (cell\*, q\*) for the C-a4-top-q-control and C-sb-baseline quantile sweeps) is the **only** record used for formal H-C2 verdict scoring. Other (cell, configuration) records are computed for diagnostic purposes (DIAGNOSTIC-ONLY label) and **not** used in the formal verdict ladder.

### 11.2 Layer 2 — cross-cell aggregation

After the val-selected per-cell is fixed, the aggregate verdict over all 6 cells follows the Phase 27 / 28 aggregation rule:

- All cells REJECT → REJECT_NON_DISCRIMINATIVE
- 1+ cell PASS, other cells REJECT → SPLIT_VERDICT_ROUTE_TO_REVIEW
- All cells PASS → would be ADOPT_CANDIDATE_PENDING_OOS, but **capped at PROMISING_BUT_NEEDS_OOS** by the ADOPT_CANDIDATE wall (§13; NG#10 / NG#11 not relaxed)

The cross-cell aggregation is computed on the 5 candidate cells (C-a4-R1 / R2 / R3 / R4 / top-q-control). C-sb-baseline is the **control** for §10 reproduction, not a candidate cell.

---

## 12. Validation-only selection; test touched once

Binding contract from Phase 27 / 28 carried verbatim into 28.0b:

- **R1**: `c` fit on val score percentile (per-pair median); test uses fit-from-val `c` once
- **R2**: `[40, 60]` global percentile cutoffs fit on val (`np.percentile(val_score_global, [40, 60])`); test uses fit-from-val cutoffs once
- **R3**: per-pair 95th percentile cutoffs fit on val; test uses fit-from-val cutoffs once
- **R4**: K=1 is deterministic (no fit needed); test uses K=1 directly via group-by-`signal_ts` argmax
- **C-a4-top-q-control / C-sb-baseline**: quantile cutoffs fit on val per existing 27.0d / 28.0a harness; test uses fit-from-val cutoffs once
- All non-val-selected test metrics labeled **DIAGNOSTIC-ONLY** in eval_report; excluded from H-C2 outcome row binding

Inherited harness functions: `evaluate_quantile_family_custom` (27.0e / 27.0f / 28.0a inheritance) for quantile cells; new deterministic-fit helpers for R1 / R2 / R3 / R4 per §12.

---

## 13. H1 / H2 / H3 / H4 verdict ladder preservation

Inheritance from 27.0f / 28.0a verbatim:

| Layer | Meaning | Pass condition for C-a4-Rx cell |
|---|---|---|
| **H1m** | Spearman(S-E score, realised_pnl) on val-selected (cell\*) | ≥ +0.30 (S-E backbone gives ~+0.438; modest discrimination loss tolerated for rule-axis filtering) |
| **H2** | Val Sharpe lift vs §10 baseline | ≥ +0.05 absolute (i.e., val Sharpe ≥ -0.1363) |
| **H3** | Trade count on val-selected | ≥ 20,000 (avoid degenerate low-trade Sharpe lifts) |
| **H4** | Formal test Spearman (DIAGNOSTIC-ONLY) | logged for test-touched-once consistency check |

### 13.1 ADOPT_CANDIDATE wall (binding constraint)

H2 PASS combined with H1m / H3 / H4 PASS produces verdict **PROMISING_BUT_NEEDS_OOS only** — **never** ADOPT_CANDIDATE. The ADOPT_CANDIDATE wall is preserved; NG#10 / NG#11 are not relaxed. Any future production deployment of a PROMISING_BUT_NEEDS_OOS result requires:

- X-v2 OOS gating (binding constraint §16)
- Phase 22 frozen-OOS contract preservation
- γ closure PR #279 not violated

### 13.2 What 28.0b-β can and cannot conclude

- **Can conclude**: H-C2 PASS / PARTIAL_SUPPORT / FALSIFIED_RULE_INSUFFICIENT / PARTIAL_DRIFT_TOPQ_REPLICA per rule; aggregate sub-phase verdict; R-T1 absorption resolution; routing implication for Phase 28 third-mover.
- **Cannot conclude**: ADOPT_CANDIDATE (capped at PROMISING_BUT_NEEDS_OOS); production deployment authorisation; modification of §10 baseline numeric; modification of any prior Phase 25 / 26 / 27 / 28.0a verdict; foreclosure of R-B / R-T3 (those remain carry-forward).

---

## 14. eval_report.md (25-section pattern inherited from 28.0a-α §11)

A4-specific adaptations:

| § | Section | Adaptation for A4 |
|---|---|---|
| 1 | Executive summary | 4-row outcome ladder per rule + aggregate verdict + C-sb-baseline reproduction status + C-a4-top-q-control drift status |
| 2 | Cells overview | 6 cells (C-a4-R1 / R2 / R3 / R4 / top-q-control / sb-baseline) |
| 3 | Row-set policy | R7-A-clean parent row-set; no R7-C drop; A4 sub-phase row-set policy declaration |
| 4 | Sanity probe results | Class priors / per-pair TIME-share / D-1 binding / R7-A NaN / R7-A positivity (inherited items 1-6 from 27.0f-α §10) |
| 5 | OOF correlation diagnostic | S-E score only (5-fold OOF; seed=42; inherited from 27.0d); per-rule OOF irrelevant |
| 6 | Regression diagnostic | S-E regressor only (control + baseline shared); rule cells share the same score |
| 7 | Quantile-family summary | C-a4-top-q-control (5 quantile points) + C-sb-baseline (5 quantile points). Rule cells R1 / R2 / R3 / R4 are single-cell (no quantile sweep). |
| 8 | Val-selection per cell | Per-cell val-selected record (cell\* alone for R1 / R2 / R3 / R4; (cell\*, q\*) for top-q-control and baseline) |
| 9 | Cross-cell aggregate verdict | per Layer 2 (§11.2) |
| 10 | §10 baseline reproduction | n_trades / Sharpe / ann_pnl deltas (inherited) |
| **11** | **Within-eval ablation drift (per rule vs C-a4-top-q-control)** | per-rule Δ test_sharpe / Δ test_n / Δ ann_pnl vs control; PARTIAL_DRIFT_TOPQ_REPLICA outcome flag per rule |
| **11b** | **C-a4-top-q-control drift vs 27.0d C-se / 28.0a C-a1-se-r7a-replica** | DIAGNOSTIC-ONLY WARN (NEW for 28.0b; control reproduction check) |
| 12 | Feature importance | S-E regressor `feature_importances_` (4-bucket; pair / direction / atr / spread) |
| **13** | **H-C2 outcome row binding per rule** (**= R-T1 elevation under A4 frame resolution**) | per-rule 4-outcome (PASS / PARTIAL_SUPPORT / FALSIFIED_RULE_INSUFFICIENT / PARTIAL_DRIFT_TOPQ_REPLICA); explicit R-T1 absorption reference per §3 |
| 14 | Trade-count budget audit | per rule on val (R1 / R4 non-quantile so n_trades is direct; R2 / R3 quantile so inflation factor reported) |
| 15 | Pair concentration | per rule (R3 expected to show lower concentration; R1 expected to also show reduced concentration due to per-pair fit) |
| 16 | Direction balance | per rule (long / short counts) |
| 17 | Per-pair Sharpe contribution | per rule (DIAGNOSTIC-ONLY) |
| 18 | Top-tail regime audit (DIAGNOSTIC-ONLY) | per rule on val at q ∈ {10, 20} for top-q-control; `spread_at_signal_pip` only (R7-C features out of scope per Clause 6) |
| 19 | R7-A new-feature NaN check | inherited from 27.0f-α / 28.0a-α |
| 20 | Realised-PnL distribution by class | TP / SL / TIME mean / p5 / p50 / p95 on train (sanity probe inheritance) |
| 21 | Timing breakdown | per-stage timer (label load, S-E regressor fit, multiclass head fit, predict, evaluate per-rule) |
| 22 | References | PR #325 (27.0d S-E) / PR #332 (27.0f within-eval ablation) / PR #334 (Phase 27 closure) / PR #335 #336 #339 #340 (Phase 28 routing + amendment) / PR #337 #338 (28.0a) / PR #279 (γ closure) |
| 23 | Caveats | DIAGNOSTIC-ONLY labels; ADOPT_CANDIDATE wall; H2 PASS = PROMISING_BUT_NEEDS_OOS only; R-T1 absorption language; S-E score fixed across all rules |
| 24 | Cross-validation re-fits diagnostic | 5-fold OOF on S-E (DIAGNOSTIC-ONLY; inherited from 27.0d / 27.0f / 28.0a) |
| 25 | Sub-phase verdict snapshot | per-rule outcome + aggregate verdict + R-T1 absorption resolution + routing implication for post-28.0b routing review |

---

## 15. Implementation notes declared at α (deferred to 28.0b-β)

The following items are pre-stated at α and resolved at β-eval implementation time. The β-eval PR must address each one without modifying the closed allowlist (§4) or the anti-collapse guards (§6).

### 15.1 R1 implementation

- Per-pair val-median computed via `np.percentile(val_score[pair_mask], 50)` per pair; ties broken by sort order.
- Test selection: `traded_mask_test = test_score > c_per_pair[test_df['pair']]`.
- No `c` grid sweep.

### 15.2 R2 implementation

- Global percentile cutoffs: `cutoffs = np.percentile(val_score_global, [40, 60])`.
- Test selection: `traded_mask_test = (test_score >= cutoffs[0]) & (test_score <= cutoffs[1])`.
- No `[p_lo, p_hi]` grid sweep.

### 15.3 R3 implementation

- Per-pair 95th percentile: `cutoff_per_pair = np.percentile(val_score[pair_mask], 95)` per pair.
- Test selection: `traded_mask_test = test_score >= cutoff_per_pair[test_df['pair']]`.
- No `q_per_pair` grid sweep.

### 15.4 R4 implementation

- Group by `signal_ts` on val and test independently; `argmax(score)` per group.
- Test selection: indices returned by per-bar argmax. No fit needed; K=1 is deterministic.
- No `K` grid sweep.

### 15.5 Shared implementation contracts

- All weights / cutoffs computed on the **R7-A-clean parent row-set** (no R7-C row-drop in this sub-phase).
- S-E regressor uses `build_pipeline_lightgbm_regression_widened()` with `sample_weight=1` (default symmetric Huber α=0.9).
- OOF fold assignment uses `seed = 42` (inherited from 27.0d / 27.0f / 28.0a).
- Sanity probe items inherited from 27.0f-α §10 / 28.0a-α §10 items 1-6 (class priors / per-pair TIME-share / D-1 binding / R7-A NaN / R7-A positivity / mid-to-mid PnL distribution per class).
- All implementation details deferred to 28.0b-β.

### 15.6 Items NOT to be decided at β (require memo amendment back to α)

- Changes to `c` definition / `[p_lo, p_hi]` / `q_per_pair` / `K` values
- Addition of a 5th rule
- Removal of any of R1 / R2 / R3 / R4
- Removal of the C-a4-top-q-control control cell
- Changes to the C-a4-top-q-control quantile family ({5, 10, 20, 30, 40})
- Score-axis variation (substituting L2 / L3 / new score variant for S-E)
- Changes to the OOF seed (42)
- Changes to the 6-cell structure (§7)

Any of these requires an **amendment PR** back to 28.0b-α before the β-eval implementation can proceed.

---

## 16. Binding constraints (verbatim)

This memo preserves every constraint binding at the end of Phase 28.0a and at PR #340 scope amendment. They remain binding throughout 28.0b-α / 28.0b-β:

- D-1 bid/ask executable harness preserved
- R7-A subset preserved
- R7-C closed allowlist preserved (no R7-C addition in this sub-phase)
- no R7-B / R7-D feature widening
- no target redesign (A2 remains dissent; not exercised here)
- no architecture change (A0 remains dissent; not exercised here)
- no non-A4 axes admitted by this design memo (PR #340 Clause 2 update is A4-specific)
- no alternate score source (S-E fixed; L2 / L3 / new score variant NOT admissible)
- no 5th rule (closed 4-rule allowlist; NG#A4-1)
- no grid sweep within a rule (α-fixed numerics; NG#A4-1)
- validation-only selection
- test touched once
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating remains required for any future production deployment
- Phase 22 frozen-OOS contract preserved
- production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) untouched
- §10 baseline immutable (no numeric change in this PR or in the future β-eval)
- MEMORY.md unchanged inside this PR
- doc-only
- no implementation in this PR
- no eval in this PR
- no production change in this PR
- no auto-route after merge
- no R-B / R-T3 elevation (R-T1 is absorbed by this PR's §3; R-B / R-T3 remain carry-forward)
- no additional scope amendment required (PR #340 Clause 2 update is sufficient)

The β-eval implementation PR will inherit all of these constraints unchanged.

---

## 17. What this PR is NOT

This PR is **NOT**:

1. The β-eval implementation (`scripts/stage28_0b_a4_monetisation_aware_selection_eval.py`). That is a **separate later PR**.
2. The β-eval results (`artifacts/stage28_0b/eval_report.md`, `aggregate_summary.json`, `sweep_results.parquet`, etc.). That is the **β-eval PR's output**.
3. The β-eval unit tests (`tests/unit/test_stage28_0b_a4_monetisation_aware_selection_eval.py`). Also β-eval PR.
4. An additional scope amendment (PR #340 Clause 2 update is sufficient for A4 non-quantile cells; no further amendment required).
5. An R-B / R-T3 elevation. (R-T1 is formally absorbed by this PR's §3; R-B / R-T3 remain in PR #334 carry-forward status.)
6. An A0 / A2 / A3 dissent elevation.
7. A modification to the §10 baseline numeric.
8. A modification to any prior Phase 25 / 26 / 27 / 28.0a verdict, evidence point, hypothesis status, or routing decision.
9. A modification of any Phase 28 kickoff / first-mover routing review / post-28.0a routing review / scope amendment admissibility decision.
10. An authorisation to touch `src/` / `scripts/` / `tests/` / `artifacts/` / `.gitignore` / `MEMORY.md`.
11. A production change. Production v9 20-pair untouched.
12. An auto-route trigger for any future action.

The next Phase 28 step (28.0b-β implementation PR) requires a **separate later user routing decision**.

---

## References

**Phase 28 (this sub-phase chain)**:
- PR #335 — Phase 28 kickoff (A4 admissible at §5.5; amendment policy §15)
- PR #336 — Phase 28 first-mover routing review (A4 primary placeholder at first-mover; A4 / A0 / A2 dissents)
- PR #337 — Phase 28.0a-α A1 objective redesign design memo (NG#A1-1/2/3 anti-collapse guard template; pre-stated-numerics pattern; D10 4-artifact form template; 25-section eval_report template)
- PR #338 — Phase 28.0a-β A1 objective redesign eval (FALSIFIED_OBJECTIVE_INSUFFICIENT result; H-B7 / H-B9 strengthening evidence; 6th data point in evidence picture)
- PR #339 — Phase 28 post-28.0a routing review (A4 primary; R-T1 reframing under A4 declared admissible; 6-eval evidence picture)
- PR #340 — Phase 28 scope amendment A4 non-quantile cell shapes (Clause 2 update; R1 / R4 admissibility binding)

**Phase 27 (inheritance / template)**:
- PR #316 — Phase 27 kickoff
- PR #325 — Phase 27.0d-β S-E regression (S-E score source; A4's score backbone)
- PR #328 — Phase 27.0e-β R-T2 quantile-family trim (top-tail adversarial finding; R2 / R4 motivation)
- PR #331 — Phase 27.0f-α S-E + R7-C design memo (within-eval ablation control + drift check template; 25-section eval_report origin)
- PR #332 — Phase 27.0f-β S-E + R7-C eval (PARTIAL_DRIFT_R7A_REPLICA outcome template; Fix A row-set isolation harness)
- PR #334 — Phase 27 closure memo (R-T1 / R-B / R-T3 carry-forward register; H-B7 / H-B8 / H-B9 hypothesis source)

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27, Phase 28 kickoff, Phase 28.0a, scope amendment, and this design memo)

---

*End of `docs/design/phase28_0b_alpha_a4_monetisation_aware_selection_design_memo.md`.*
