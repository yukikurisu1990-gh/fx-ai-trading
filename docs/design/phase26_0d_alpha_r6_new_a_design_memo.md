# Phase 26.0d-α — R6-new-A Feature-Widening Audit Design Memo

**Type**: doc-only design memo (binding contract for the eventual 26.0d-β implementation)
**Branch**: `research/phase26-0d-alpha-r6-new-a-design`
**Base**: master @ 13419e4 (post-PR #311 merge)
**Pattern**: analogous to 26.0a-α (PR #301) / 26.0b-α (PR #305) / 26.0c-α (PR #308) with the new feature axis added under amended clause 6 from #311
**Status**: design memo only — does NOT initiate 26.0d-β eval
**Stop condition**: design memo merged → 26.0d-β implementation in a separate later instruction

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this design memo as the binding contract for the eventual Phase 26.0d-β R6-new-A feature-widening audit. It does NOT by itself authorise 26.0d-β implementation. The user explicitly authorises the 26.0d-β implementation PR in a separate later instruction.*

Same approval-then-defer pattern as #301 / #305 / #308 / #311.

---

## 1. Phase 26.0d framing

R6-new-A is a **feature-widening audit**, NOT a model-class comparison, NOT a label-class redesign, NOT a Phase 25 F-class sweep revival.

> *The intervention tested by R6-new-A is the **closed two-feature allowlist** (`atr_at_signal_pip`, `spread_at_signal_pip`) added on top of the Phase 26 minimum feature set (`pair + direction`). The model class is held fixed at the conservative LightGBM configuration inherited from prior Phase 26 sub-phases (#308 / #309). R6-new-A is NOT model selection; it is NOT calibration tuning; it is NOT hyperparameter search. The single axis under test is the feature set.*

R6-new-A directly tests the surviving load-bearing hypothesis from post-26.0c routing review (#310 §3 / §4): *the minimum feature set is the binding constraint* on the L-1 = L-2 = L-3 identical val-selected outcome.

**Phase 26 stays Phase 26.** The closed allowlist is narrow and minimal. F1 / F2 / F3 / F5 / F4 / F6 / F5-d / F5-e / multi-TF / calendar / external-data remain out of scope.

---

## 2. Closed feature allowlist (verbatim inheritance from scope amendment #311 §3)

### 2.1 Admitted (closed; exactly 2 features beyond the minimum set)

| Feature | Source column in 25.0a-β dataset | Inheritance status |
|---|---|---|
| `atr_at_signal_pip` | already in dataset | verbatim from #311 §3.1 |
| `spread_at_signal_pip` | already in dataset | verbatim from #311 §3.1 |

Combined with the Phase 26 minimum feature set, the full R6-new-A feature set is:

```
[pair (one-hot), direction (one-hot), atr_at_signal_pip (numeric), spread_at_signal_pip (numeric)]
```

### 2.2 NOT admitted (verbatim from #311 §3.2; out of scope)

❌ Phase 25 F1 / F2 / F3 / F5 full feature sets
❌ F4 / F6 / F5-d / F5-e (preserved as Phase 25 deferred-not-foreclosed)
❌ Multi-timeframe features (M5 / M15 / H1 aggregates)
❌ Calendar / time-of-day features
❌ External-data features (DXY, news, calendar events)
❌ Any feature not in §2.1 above

> *This memo cannot widen the allowlist. Widening requires a separate scope amendment per #311 §3.2.*

R6-new-B / R6-new-C / R6-new-D from #310 §6.1 are **NOT** authorised under this design memo (per #311 (g) binding).

---

## 3. Inherited label class (Decision A1)

R6-new-A adopts **L-1 ternary classification {TP=0, SL=1, TIME=2}** as the label class (Decision A1; recommended default per #311 §4).

### 3.1 Why L-1 (and not L-2 / L-3)

| Aspect | Rationale |
|---|---|
| Most recently characterised (PR #309) | clean inheritance; same picker/threshold wiring carries over |
| Multiclass picker scoring | `P(TP)` / `P(TP)−P(SL)` apply unchanged from #308 §3 |
| Verdict-tree wiring | inherits PROMISING_BUT_NEEDS_OOS wording from #308 §6.2 / #309 |
| Disjoint class structure | retains the cleanest comparison-table mapping vs #309 baseline |

### 3.2 Label construction

Re-use `build_l1_labels_for_dataframe` from `scripts/stage26_0c_l1_eval.py` (inherited; not re-implemented). Triple-barrier inputs unchanged: K_FAV=1.5×ATR, K_ADV=1.0×ATR, H_M1=60. Same canonical 20-pair universe, same 70/15/15 chronological split.

### 3.3 L-4 NOT admissible

Per #311 §4: L-4 (trinary-with-no-trade) is the deferred-not-foreclosed R3 route. Mixing R3 + R6-new would conflate two axes. **L-4 is NOT used here.**

---

## 4. Model class (Decision B; binding rationale for "audit, not comparison")

R6-new-A uses **fixed conservative LightGBM multiclass** inherited verbatim from #308 §4.1 / #309:

```python
LIGHTGBM_FIXED_CONFIG = dict(
    objective="multiclass",
    num_class=3,
    n_estimators=200,
    learning_rate=0.03,
    num_leaves=31,
    max_depth=4,
    min_child_samples=100,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    class_weight="balanced",
)
```

### 4.1 Binding clarification (per user correction on D-B)

> *R6-new-A is a feature-widening audit, NOT a model-class comparison. The tested intervention is the closed two-feature allowlist (§2.1) added to the Phase 26 minimum feature set. The model class is held fixed at the conservative LightGBM configuration; no model selection, no calibration tuning, no hyperparameter search is part of this audit.*
>
> *If R6-new-A produces a differentiated val-selected trade set, the conclusion is "the 2-feature widening changed the ranking signal under the fixed model class," NOT "LightGBM with these specific hyperparameters is the right model." If R6-new-A produces an identical val-selected trade set, the conclusion is "the 2-feature widening did not change the ranking signal at this model class," NOT "feature widening is irrelevant."*

This narrow framing is load-bearing for the §10 verdict interpretation.

---

## 5. Feature engineering + missingness policy (Decisions F + G)

### 5.1 Pipeline shape

```python
ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), ["pair", "direction"]),
    ("num", "passthrough", ["atr_at_signal_pip", "spread_at_signal_pip"]),
])
```

- `pair` and `direction` continue to be one-hot encoded (same as #308 / #309).
- `atr_at_signal_pip` and `spread_at_signal_pip` pass through as numeric.
- **No scaling / standardisation.** LightGBM is scale-invariant for tree splits.

### 5.2 Missingness policy (Decision F1: drop)

For each split (train / val / test):

- Drop rows where ANY of `atr_at_signal_pip` or `spread_at_signal_pip` is NaN or non-finite.
- Mirror the existing row-drop semantics from 26.0a-β / 26.0b-β / 26.0c-β label-NaN drop.
- Imputation is NOT used (introduces train-test leakage risk; rejected per Decision F).

### 5.3 Sanity probe threshold for new-feature missingness

If `NaN_rate > 0.05` per split for either new feature on full 20-pair dataset → HALT with `SanityProbeError`. (Tunable constant; default 5%.)

---

## 6. Picker / score function (Decision C; inherited B1+B2)

Re-use from `scripts/stage26_0c_l1_eval.py`:

| Picker | Score |
|---|---|
| **B1** | `P(TP)` |
| **B2** | `P(TP) − P(SL)` |

Both scores are **raw probabilities**. No isotonic calibration in formal grid (deferred per #308 §4.3 selection-overfit binding).

B3 argmax / B4 calibrated EV explicitly excluded at design (same as #308).

---

## 7. Threshold family (Decision D; inherited from #308)

### 7.1 PRIMARY formal verdict basis

Quantile-of-val cutoff family: **{5, 10, 20, 30, 40}%**. Top-q% of val score distribution is traded; val-fit scalar cutoff applied to test once.

### 7.2 SECONDARY DIAGNOSTIC family

Absolute probability thresholds: `{0.30, 0.40, 0.45, 0.50}` on `P(TP)`, `{0.0, 0.05, 0.10, 0.15}` on `P(TP)−P(SL)`. Reported per cell; NEVER used in formal verdict routing.

### 7.3 Quantile cutoff fitting (val-only)

`fit_quantile_cutoff_on_val(score_val, q_percent)` returns a scalar cutoff. Same scalar applied to test predictions. No full-sample qcut, no peeking at test.

---

## 8. Realised-PnL cache (D-1 binding from #309 preserved verbatim)

Re-use `precompute_realised_pnl_per_row` from `scripts/stage26_0b_l2_eval.py` (cell-independent; inherited harness). Uses `_compute_realised_barrier_pnl` from `scripts/stage25_0b_f1_volatility_expansion_eval.py` — bid/ask executable treatment via M1 path re-traverse.

> *D-1 BINDING: formal realised-PnL scoring uses the inherited `_compute_realised_barrier_pnl` (bid/ask executable). Mid-to-mid PnL may appear in the sanity probe / label diagnostic only; it is NEVER used as the formal realised-PnL metric.*

---

## 9. Hypothesis ladder (formal H1 binding; UNCHANGED from Phase 26 family)

| Hypothesis | Pass threshold (FORMAL) |
|---|---|
| **H1-weak** | val-selected cell **test Spearman(picker score, realised_pnl) > 0.05** |
| **H1-meaningful** | val-selected cell **test Spearman(picker score, realised_pnl) ≥ 0.10** |
| **H2** | test realised Sharpe ≥ +0.082 AND ann_pnl ≥ +180 |
| **H3** | test realised Sharpe > -0.192 (Phase 25 F1 best baseline; unchanged) |
| **H4** | test realised Sharpe ≥ 0 |

### 9.1 Formal H1 signal

Spearman(picker score, realised_pnl) — same as #308 §6.1 / #309. AUC / Cohen's κ / multiclass logloss / confusion matrix / per-class accuracy remain **diagnostic-only**.

### 9.2 Verdict tree (UNCHANGED from #308 §6.2 / #309)

| Branch | Trigger |
|---|---|
| REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL | not H1-weak |
| REJECT_WEAK_SIGNAL_ONLY / H1_WEAK_PASS_ONLY | H1-weak but not H1-meaningful |
| REJECT_BUT_INFORMATIVE_IMPROVED / H1m_PASS_H2_FAIL_H3_PASS | H1-meaningful + H2 FAIL + H3 PASS |
| REJECT_BUT_INFORMATIVE_FLAT / H1m_PASS_H2_FAIL_H3_FAIL | H1-meaningful + H2 FAIL + H3 FAIL |
| **PROMISING_BUT_NEEDS_OOS** / H2_PASS_AWAITS_A0_A5 | H2 PASS |

### 9.3 ADOPT_CANDIDATE wall preserved (per #311 (f))

> *26.0d-β cannot mint ADOPT_CANDIDATE. The H2 PASS path resolves to PROMISING_BUT_NEEDS_OOS pending the separate A0-A5 8-gate harness PR. This binding is preserved unchanged from #311 (f).*

---

## 10. Formal cell grid (Decision E; 2 cells × raw probability only)

| Cell ID | Picker | Calibration | Cutoff family (formal) |
|---|---|---|---|
| **C01** | P(TP) | raw | quantile-of-val 5/10/20/30/40% |
| **C02** | P(TP) − P(SL) | raw | quantile-of-val 5/10/20/30/40% |

Same A0-prefilter + tie-breaker chain from #308 §7.1 / #309. Cross-cell verdict aggregation per 26.0c-α §7.2 (agree → single verdict; disagree → split with no auto-resolution).

### 10.1 Why 2 cells (not more)

R6-new-A is intentionally narrow:
- Single label class fixed (L-1; per Decision A)
- Single model class fixed (LightGBM multiclass; per Decision B)
- No calibration variation (isotonic deferred per #308 §4.3)
- No absolute-threshold cell dimension (diagnostic-only per #308 §4.2)

The only axis the formal grid spans is the picker (P(TP) vs P(TP)−P(SL)). Two cells is the minimum grid that captures the picker axis without introducing additional confounding axes.

---

## 11. Diagnostic columns (binding: ALL diagnostic-only)

All items in this section are diagnostic-only. **ADOPT routing must not depend on any single one** (mandatory clause 2).

### 11.1 Pair concentration (CONCENTRATION_HIGH 80% flag; inherited from #308 / #309)

Re-use `compute_pair_concentration` from `scripts/stage26_0b_l2_eval.py`. Flag fires when val top-pair share ≥ 0.80. **NOT used in formal verdict / cell selection.**

Particularly important for R6-new-A: the L-1 / L-2 / L-3 identity outcome had 100% USD_JPY concentration on the val-selected (cell\*, q\*). Whether R6-new-A breaks this concentration is the **most informative diagnostic** of whether feature widening changed the ranking mechanism — but it is **still diagnostic-only** under clause 2 binding.

### 11.2 Classification-quality diagnostics

AUC of `P(TP)` one-vs-rest / Cohen's κ / multiclass logloss / confusion matrix / per-class accuracy on test. Inherited from #308 §9.3. **None enter formal verdict routing.**

### 11.3 Absolute-threshold sweep (per 11.0c-α §9.4 inheritance)

Reported per cell; NEVER enters formal verdict routing.

### 11.4 Feature importance (NEW R6-new-A diagnostic)

LightGBM gain importance on the val-selected fit. Reports per-feature contribution:
- `pair_*` one-hot importances (aggregated)
- `direction_*` one-hot importances (aggregated)
- `atr_at_signal_pip` importance
- `spread_at_signal_pip` importance

**Diagnostic-only.** Indicates how much weight the model placed on the new features vs the minimum-set features — informationally useful for the §13 verdict interpretation, but does NOT enter formal verdict.

### 11.5 Isotonic-calibration appendix — OMITTED per 26.0c-α §4.3 (preserved)

`compute_isotonic_diagnostic_appendix` stub raises `NotImplementedError` per #308 §4.3 / #309. Unchanged.

---

## 12. Sanity probe (mandatory before sweep; extends 26.0c-α §10)

Per #308 §10 plus 2 new R6-new-A-specific checks (per Decision F + G).

### 12.1 Inherited checks (from #309 §10)

1. Class priors (TP / SL / TIME) per split — HALT if any class < 1% of total rows
2. Per-pair TIME-class share — HALT if any pair > 99% TIME share
3. Realised-PnL cache basis check (inherited harness, bid/ask executable)
4. Mid-to-mid PnL distribution per class on TRAIN (diagnostic-only)

### 12.2 NEW R6-new-A-specific checks

5. **New-feature missingness check**: count NaN / non-finite for `atr_at_signal_pip` and `spread_at_signal_pip` per split. HALT if `NaN_rate > 0.05` per split for either feature.
6. **New-feature distribution snapshot**: print mean / p5 / p50 / p95 per pair for both new features. Sanity-check: `atr_at_signal_pip > 0` for all rows; `spread_at_signal_pip ≥ 0` for all rows. HALT if either assertion violates on ≥ 1% of rows.

### 12.3 Halt semantics

Halt raises `SanityProbeError` with the failing condition before the full sweep starts. Same pattern as #309.

---

## 13. Mandatory L-1 / L-2 / L-3 vs R6-new-A comparison section (per Decision H; binding for 26.0d-β eval_report.md)

26.0d-β `eval_report.md` MUST include a **4-column comparison table** + a **binding YES / NO / PARTIAL paragraph**.

### 13.1 4-column comparison table (mandatory)

| Aspect | L-3 (PR #303) | L-2 (PR #306) | L-1 (PR #309) | R6-new-A (this PR's eval) |
|---|---|---|---|---|
| Label class | continuous regression (spread-embedded) | continuous regression (mid-to-mid) | ternary classification | ternary classification (inherited from L-1) |
| Feature set | pair + direction | pair + direction | pair + direction | pair + direction + atr_at_signal_pip + spread_at_signal_pip |
| Val-selected cell signature | atr_normalised / Linear / q\*=5% | atr_normalised / Linear / q\*=5% | C01 P(TP) / q\*=5% | TBD |
| Val-selected test realised Sharpe | -0.2232 | -0.2232 | -0.2232 | TBD |
| Val-selected test ann_pnl (pip) | -237,310.8 | -237,310.8 | -237,310.8 | TBD |
| Val-selected test n_trades | 42,150 | 42,150 | 42,150 | TBD |
| Test Spearman (formal H1) | -0.1419 | -0.1139 | -0.0505 (C01) / -0.1077 (C02) | TBD |
| Pair concentration on test | 100% USD_JPY | 100% USD_JPY | 100% USD_JPY | TBD |
| Verdict | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | TBD |

### 13.2 Binding YES / NO / PARTIAL paragraph

26.0d-β `eval_report.md` MUST explicitly answer the following question with one of `YES` / `NO` / `PARTIAL`:

> *"Did the closed two-feature allowlist (`atr_at_signal_pip`, `spread_at_signal_pip`) change the val-selected trade set away from the L-1 / L-2 / L-3 identity outcome (n_trades=42,150 ; Sharpe=-0.2232 ; ann_pnl=-237,310.8 ; 100% USD_JPY)? **YES / NO / PARTIAL**."*

### 13.3 Verdict interpretation tree (per Decision H + user correction on NO interpretation)

| Answer | Trade-set change | Realised PnL improvement | Interpretation |
|---|---|---|---|
| **YES (improved)** | val-selected trade set differs from baseline | Sharpe / ann_pnl improved vs baseline | The 2-feature widening broke the identity and improved realised PnL. The minimum-feature-set hypothesis (post-26.0c §3 / §4) is **supported as binding at the closed allowlist**. Routes to H1/H2/H3 ladder per §9. |
| **YES (same/worse)** | val-selected trade set differs from baseline | Sharpe / ann_pnl same or worse | Feature widening changed selection but did NOT improve realised PnL. Supports the minimum-feature-set hypothesis being binding **even at this feature-widening allowlist** — the audit confirms feature widening at this allowlist is not the right lever. |
| **NO (identity persists)** | val-selected trade set IDENTICAL to L-1 / L-2 / L-3 baseline | (identical by construction) | **The closed two-feature allowlist did NOT break the identity.** This does **NOT** prove that feature widening cannot help. It says only that *this specific minimal allowlist* did not change the val-selected ranking at the fixed model class. Further feature widening (R6-new-B / R6-new-C / R6-new-D, multi-TF, calendar, external-data) would require a **separate scope amendment** per #311 §3.2 / amended clause 6. The minimum-feature-set hypothesis is **not rejected**; it is **not supported either** under this narrow allowlist. |
| **PARTIAL** | val-selected n_trades or pair concentration changes, but Sharpe / ann_pnl do not | mixed | The ranking mechanism is partially sensitive to the new features (selection changes), but realised PnL does not improve. Routes to post-26.0d routing review for next-step framing. |

### 13.4 Critical wording binding (per user correction)

> *Under outcome `NO (identity persists)`, the memo MUST state explicitly: "this does NOT prove feature widening cannot help; further feature widening would require a separate scope amendment per #311 §3.2."*
>
> *The memo MUST NOT state "minimum-feature-set hypothesis is rejected" in this case. The hypothesis remains the strongest current hypothesis (#310 §4), and a single narrow allowlist test does not refute it.*

---

## 14. Posterior expectations (subjective / heuristic; not statistically estimated)

| Outcome | Probability tag |
|---|---|
| Val-selected trade set changes (YES, either improved or same/worse) | medium-to-high |
| Realised Sharpe improves to ≥ -0.192 (H3 PASS) | medium |
| Realised Sharpe improves to ≥ +0.082 (H2 PASS Sharpe component) | low-to-medium |
| H2 PASS path triggered → PROMISING_BUT_NEEDS_OOS | low |
| NO (full identity persists; same val-selected trade set) | low-to-medium |
| PARTIAL (n_trades or concentration changes, Sharpe doesn't improve) | medium |

**All tags are subjective / heuristic / not statistically estimated.** They are discussion anchors only. The user reweights freely. Outcome reasoning is dominated by the surviving load-bearing hypothesis from #310 §3 / §4.

---

## 15. Implementation outline for 26.0d-β (NOT this PR)

| Item | Detail |
|---|---|
| Script | `scripts/stage26_0d_r6_new_a_eval.py` (~1900-2100 lines; closely modelled on `stage26_0c_l1_eval.py` with feature-pipeline wiring added) |
| Tests | `tests/unit/test_stage26_0d_r6_new_a_eval.py` (~40-45 tests; 5+ NEW R6-new-A-specific: closed-allowlist enforcement, new-feature missingness handling, feature-importance shape, comparison-table generator, YES/NO/PARTIAL outcome detector) |
| Sanity probe | per §12 above |
| Eval report | `artifacts/stage26_0d/eval_report.md` with the mandatory L-1/L-2/L-3 vs R6-new-A 4-column comparison (§13.1) + binding YES/NO/PARTIAL paragraph (§13.2-§13.4) |
| Runtime estimate | ~25-40 min (2 cells × 5 quantiles × multiclass LGBM with 4 features instead of 2) |
| `.gitignore` entries | `artifacts/stage26_0d/{run.log, sweep_results.parquet, sweep_results.json, aggregate_summary.json, val_selected_cell.json, sanity_probe.json}` |

---

## 16. Mandatory clauses (verbatim; clause 6 AMENDED per #311 §8)

1. **Phase 26 framing.** Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness. *[unchanged]*
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. *[unchanged]*
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified. *[unchanged]*
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched. *[unchanged]*
5. **NG#10 / NG#11 not relaxed.** *[unchanged]*
6. **Phase 26 scope (AMENDED).** Phase 26's primary axis is label / target redesign on the 20-pair canonical universe. Phase 26 is NOT a revival of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed under Phase 25 semantics. A narrow feature-widening audit (R6-new-A) is authorised under the scope amendment in PR #311 with a closed allowlist of two features (`atr_at_signal_pip`, `spread_at_signal_pip`); all other features are out of scope until a further scope amendment. R6-new-A is a Phase 26 audit of the minimum-feature-set hypothesis; it is NOT a Phase 25 continuation. *[AMENDED per #311 §8]*

Future PRs in the Phase 26 R6-new sub-stream will quote the amended clause 6 verbatim.

---

## 17. What this PR will NOT do

- ❌ Implement `scripts/stage26_0d_r6_new_a_eval.py`
- ❌ Implement `tests/unit/test_stage26_0d_r6_new_a_eval.py`
- ❌ Run any sweep or produce `artifacts/stage26_0d/*`
- ❌ Touch `.gitignore` for `artifacts/stage26_0d/*` (deferred to 26.0d-β PR)
- ❌ Modify `src/`, `scripts/` outside the design memo path, `tests/`, `artifacts/`
- ❌ Widen the closed allowlist (would require a separate scope amendment per #311 §3.2)
- ❌ Authorise R6-new-B / R6-new-C / R6-new-D
- ❌ Authorise L-4 (R3 route) — would conflate axes per #311 §4
- ❌ Modify any prior verdict (Phase 25 / Phase 26 #284..#311)
- ❌ Retroactively change L-1 / L-2 / L-3 verdict
- ❌ Modify γ closure (PR #279)
- ❌ Pre-approve production deployment
- ❌ Update MEMORY.md
- ❌ Foreclose R3 (L-4) — remains deferred-not-foreclosed
- ❌ Foreclose R5 (Phase 26 soft close) — remains admissible at any subsequent routing review
- ❌ Authorise the 26.0d-β implementation PR (separate later instruction)
- ❌ Auto-route to 26.0d-β implementation after merge

---

## 18. Sign-off

After this design memo merges:

- **26.0d-β implementation** is authorised only by a separate later user instruction.
- The 26.0d-β PR will implement `scripts/stage26_0d_r6_new_a_eval.py` + `tests/unit/test_stage26_0d_r6_new_a_eval.py` + `artifacts/stage26_0d/eval_report.md` (with mandatory L-1/L-2/L-3 vs R6-new-A 4-column comparison + binding YES/NO/PARTIAL paragraph per §13).
- After 26.0d-β closure, a post-26.0d routing review will follow the #304 / #307 / #310 pattern.

**This PR stops here.**
