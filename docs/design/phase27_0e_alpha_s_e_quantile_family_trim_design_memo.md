# Phase 27.0e-α — S-E Quantile Family Trim Design Memo

**Type**: doc-only design memo
**Status**: tier-promotes R-T2 (trimmed quantile-of-val family for S-E) *admissible under existing clause 6 + clause 2* → *formal at 27.0e-β*; does NOT trigger 27.0e-β implementation
**Branch**: `research/phase27-0e-alpha-s-e-quantile-trim-design-memo`
**Base**: master @ b4078b9 (post-PR #326 / Phase 27 post-27.0d routing review merge)
**Pattern**: analogous to PR #312 / #317 / #320 / #324 design memos under Phase 27
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the **canonical 27.0e-α design memo**. On merge, the trimmed-quantile policy specified here becomes *formal at sub-phase 27.0e-β*, meaning a future 27.0e-β eval PR may evaluate the trimmed family under the policies bound here without further scope amendment. It does NOT by itself authorise the 27.0e-β eval implementation — that requires a separate later user instruction.*

Same approval-then-defer pattern as PR #320 (27.0c-α) / PR #324 (27.0d-α).

This PR is doc-only. No `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md` is touched.

### 0.1 Clause-2 admissibility position (load-bearing)

Per post-27.0d routing review (PR #326) §4.2, **R-T2 is admissible under existing clause 6 + clause 2**:

- The quantile-of-val family is a *per-cell quantile-family choice*, not a new diagnostic-to-formal promotion
- Trimming the val-quantile family for C-se from {5, 10, 20, 30, 40} to {5, 7.5, 10} does NOT modify clause 2 (per-pair-Sharpe-contribution / threshold-sweep / classification-quality / feature-importance / etc. remain diagnostic-only)
- No scope amendment is requested by this PR

This PR strictly stays inside the clause 6 / clause 2 envelope already established by PR #316 + PR #323. Any drift toward "use per-pair-Sharpe-contribution as a filter" / "use trade-count as a verdict input" would push toward R-T1 / R-T3 territory and require separate scope amendment — this PR **does not** propose any such drift.

---

## 1. Why 27.0e-α exists

The post-27.0d routing review (PR #326, master b4078b9) §4 enumerated 8 routing options after 27.0d-β's split-verdict outcome (first H1-meaningful PASS in Phase 27, Spearman +0.4381 on C-se, but H2 FAIL via Sharpe -0.483 + trade-rate explosion to n=184,703). The user explicitly selected **R-T2 — trade-rate-capped quantile-of-val family for S-E** as the next move, with the routing rationale (verbatim):

> *27.0d S-Eで初めてH1-meaningful ranking signalが出た。失敗はscore不在ではなく、top-q selectionが広すぎてtrade-rate explosionを起こしたことにある。R-T2はS-E scoreを維持しつつ、quantile familyを絞ってtrade-rateを制御する最小介入。R-T1はabsolute threshold / confidence ruleでclause 2整理が重い。R-T3はpair-concentration formalisationなのでscope amendmentが必要。R-B / R-C feature wideningも候補だが、まずはS-Eのselection ruleを小さく修正する方が低コストで情報価値が高い。*

R-T2 targets the **H-B5 hypothesis** from #326 §3.2 (monetisation-transformation bottleneck): the wrong-direction Sharpe pattern is mechanistically dominated by the inherited quantile-of-val cell-selection's response to a wider-spread score function, not by the score-objective per se. A discriminative ranking + top-q val-selection + unconstrained trade count = trade-rate explosion + per-trade EV collapse.

If R-T2 produces H2 PASS at some q ∈ {5, 7.5, 10}, H-B5 is strongly supported and Phase 27 reaches its first PROMISING_BUT_NEEDS_OOS branch. If R-T2 produces wrong-direction Sharpe at all 3 q values, H-B5 is falsified and routing pivots to R-B / R-C / R-E.

**27.0e-α scope is narrow**: trim the val-quantile family for C-se only; preserve the inherited family for C-sb-baseline (inheritance-chain check). No other changes.

---

## 2. Inheritance bindings (FIXED for 27.0e-β)

The following are FIXED for 27.0e-β and CANNOT be relaxed by this design memo:

| Binding | Source | Inheritance status |
|---|---|---|
| R7-A 4-feature allowlist (`pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`) | PR #311 / #313 / #323 | FIXED |
| 25.0a-β path-quality dataset | inherited | FIXED |
| 70/15/15 chronological split | inherited | FIXED |
| Triple-barrier inputs (K_FAV=1.5·ATR, K_ADV=1.0·ATR, H_M1=60) | inherited | FIXED |
| `_compute_realised_barrier_pnl` (bid/ask executable harness) | D-1 binding | FIXED — both formal verdict PnL and S-E regression target |
| L-1 ternary class encoding (TP/SL/TIME) | inherited | PRESERVED for sanity probe + C-sb-baseline only; NOT used as S-E target |
| LightGBMRegressor + Huber loss config (`build_pipeline_lightgbm_regression_widened`) | PR #325 / 27.0d-α §4 | FIXED — α=0.9; inherited multiclass-shape hyperparameters; per D-X2 |
| LightGBM multiclass head config (`build_pipeline_lightgbm_multiclass_widened`) | inherited from 26.0d | FIXED — used ONLY for C-sb-baseline replica cell |
| 5-fold OOF protocol (DIAGNOSTIC-ONLY) | 27.0d-α §6.2 | FIXED — seed=42; same fold assignment; same diagnostic outputs |
| 8-gate metrics + `gate_matrix` | inherited | FIXED |
| Verdict ladder H1/H2/H3/H4 thresholds (0.05 / 0.10 / Sharpe ≥0.082 ∧ ann_pnl ≥180 / >−0.192 / ≥0) | inherited | FIXED |
| Validation-only cutoff selection; test touched once | inherited | FIXED |
| Cross-cell verdict aggregation (26.0c-α §7.2) | inherited | FIXED — SPLIT_VERDICT_ROUTE_TO_REVIEW branch demonstrated at 27.0d |
| ADOPT_CANDIDATE 8-gate A0–A5 SEPARATE-PR wall | inherited | FIXED |
| Pair-concentration diagnostic + per-pair Sharpe contribution diagnostic | inherited | FIXED — DIAGNOSTIC-ONLY per clause 2 |
| BaselineMismatchError tolerances (n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip) | inherited | FIXED — per D-X7 |
| D10 amendment 2-artifact form (one regressor + one multiclass head) | 27.0d-α §7.5 | FIXED |
| 2-layer selection-overfit guard | 27.0d-α §13 | FIXED |
| Clause 2 diagnostic-only binding | kickoff §8 / PR #323 §7 | **load-bearing; unchanged** |
| Phase 22 frozen-OOS contract | inherited | FIXED |
| Production v9 20-pair tip 79ed1e8 | inherited | UNTOUCHED |

The substantive scope change in 27.0e is the **per-cell quantile-of-val family** (§4 below). All other bindings carry forward unchanged.

---

## 3. S-E score (unchanged from 27.0d-α)

The score function for C-se is **inherited verbatim** from 27.0d-α §3:

```
target(row) = _compute_realised_barrier_pnl(row)   # D-1 binding; bid/ask executable
S-E(row)    = regressor.predict(row)               # predicted realised PnL per row
```

The regressor (LightGBMRegressor + Huber + α=0.9, R7-A features) is unchanged. The score is unchanged. The sign convention is unchanged (higher predicted PnL = better; quantile-of-val picks top-(q/100) val rows).

Algebraic comparison vs S-A / S-B / S-C / S-D is preserved verbatim from 27.0d-α §3.2.

The **only** delta vs 27.0d-β is the quantile-of-val family used to materialise (cell, q) pairs for the formal verdict (§4 below).

---

## 4. Quantile family policy (D-X1 + D-X4)

### 4.1 Per-cell quantile family (D-X4)

| Cell | Quantile family | Rationale |
|---|---|---|
| **C-se-trimmed** | **{5, 7.5, 10}** (trimmed) | Cap at q=10% to enforce trade-count budget. 27.0d C-se's val-selected q*=40% picked 184,703 val trades = ~8× val-baseline (25,881). This trim prevents trade-rate explosion |
| **C-sb-baseline** | **{5, 10, 20, 30, 40}** (inherited / unchanged) | Required to reproduce 27.0b C-alpha0 / R6-new-A C02 baseline exactly. Val-selected q=5% inherits unchanged from 27.0c/27.0d/27.0b |

### 4.2 D-X1 — Trimmed family rationale

Trimmed family = **{5, 7.5, 10}**. Three quantile points; cap at 10% (1/4 of 27.0d's 40%); minimum 5% inherited. The 7.5% midpoint is novel (not in original 5-point family); it provides fine granularity below the 10% cap to expose any selection sweet spot. Lower cap (e.g., {2.5, 5}) is **not** proposed because the inherited 5% has matched the baseline exactly for 26.0d / 27.0b / 27.0c / 27.0d — going below 5% would change the inheritance-chain check structure.

The trim is **per-cell** for C-se only. C-sb-baseline retains the inherited 5-point family so its q=5% val-selected outcome continues to match 27.0b C-alpha0 row-for-row.

### 4.3 Clause-2 framing (per §0.1 load-bearing)

This per-cell quantile-family choice is admissible under existing clause 2:

- It is **NOT** a new diagnostic-to-formal promotion. Per-pair-Sharpe-contribution / threshold-sweep / classification-quality / feature-importance columns remain diagnostic-only (unchanged)
- It is **NOT** a new formal verdict input beyond the val-quantile cutoff that already exists in the verdict path
- It is **NOT** a clause 6 modification (R7-A FIXED; S-E formal at 27.0d-β; no scope change)

Drift checks: the design memo §4 will explicitly state that no cell uses per-pair-Sharpe-contribution as a filter, no cell uses trade-count as a verdict input, no cell uses concentration as a verdict input. The val-selection rule remains "max val_sharpe across the (cell, q) pairs in the cell's quantile family" — the same rule as 26.0d / 27.0b / 27.0c / 27.0d.

---

## 5. Cell structure (D-X3)

Two formal cells (mirrors 27.0d-α §7.1 form):

| Cell ID | Score | Model | Quantile family | Purpose |
|---|---|---|---|---|
| **C-se-trimmed** | regressor.predict (S-E) | LightGBMRegressor (Huber, α=0.9) | {5, 7.5, 10} | substantive — tests H-B5 |
| **C-sb-baseline** | raw P(TP) − P(SL) | multiclass head | {5, 10, 20, 30, 40} | inheritance-chain check (must reproduce 27.0b C-alpha0) |

**No separate "C-se-original" cell** (per D-X3). Comparison against the 27.0d C-se outcome (q=40, n=184,703, Sharpe -0.483, Spearman +0.4381) is done via the eval-report §22 cross-reference to PR #325 artifacts (sweep_results.json + eval_report.md), not by re-running the original quantile family in 27.0e-β.

Sweep grid: 1 cell × 3 q-values + 1 cell × 5 q-values = **8 (cell, q) pairs** (down from 10 in 27.0d).

Per-cell val-selection: max val_sharpe per cell across that cell's quantile family. Cross-cell aggregation per 26.0c-α §7.2 (agree → single verdict; disagree → SPLIT_VERDICT_ROUTE_TO_REVIEW). Both branches admissible by 27.0d-β precedent.

### 5.1 D10 amendment for 27.0e (inherited 2-artifact form)

"Single model fit" in 27.0e-β means:
- **one** LightGBMRegressor (production S-E head; same as 27.0d-β)
- **one** LightGBM multiclass head (for C-sb-baseline only; same as 27.0d-β)

Both artifacts fit ONCE each; neither is re-fit per cell or per quantile. The train-only realised PnL precomputation is shared. **No additional artifacts** are introduced by the trimmed quantile family — only the cell-level evaluation grid changes.

---

## 6. Implementation strategy (D-X5 + D-X6; 27.0e-β contract preview)

### 6.1 D-X5 — `evaluate_quantile_family_custom`

Add a new helper:

```
evaluate_quantile_family_custom(
    score_val: np.ndarray,
    pnl_val: np.ndarray,
    score_test: np.ndarray,
    pnl_test: np.ndarray,
    span_years_val: float,
    span_years_test: float,
    quantile_percents: tuple[float, ...] | list[float],
) -> list[dict]
```

Accepts a list / tuple of quantile percents (e.g., `(5.0, 7.5, 10.0)`). Returns the same list-of-dicts shape as inherited `evaluate_quantile_family`. The inherited `evaluate_quantile_family` (which uses the module constant `THRESHOLDS_QUANTILE_PERCENTS`) is **unchanged** for backward compatibility (existing 27.0d-β / 27.0c-β behavior preserved).

### 6.2 D-X6 — Per-cell quantile-percents in cell dict

Each cell dict gains a `quantile_percents: tuple[float, ...]` field:

```python
{
    "id": "C-se-trimmed",
    "picker": "S-E(regressor_pred)",
    "score_type": "s_e",
    "quantile_percents": (5.0, 7.5, 10.0),
},
{
    "id": "C-sb-baseline",
    "picker": "S-B(raw_p_tp_minus_p_sl)",
    "score_type": "s_b_raw",
    "quantile_percents": (5.0, 10.0, 20.0, 30.0, 40.0),
},
```

`evaluate_cell_27_0e` reads `cell["quantile_percents"]` and calls `evaluate_quantile_family_custom` with that list. Default fallback if the field is missing = `THRESHOLDS_QUANTILE_PERCENTS` (preserves 27.0d behavior for legacy cell-dict shapes; defensive, not used in practice in 27.0e-β).

---

## 7. BaselineMismatchError + 5-fold OOF (D-X7 + D-X8)

### 7.1 D-X7 — BaselineMismatchError tolerances (inherited verbatim)

C-sb-baseline must reproduce the 27.0b C-alpha0 / R6-new-A C02 baseline within tolerances **identical** to 27.0d-α §7.3:

| Metric | Reference value (PR #318 §10) | Tolerance |
|---|---|---|
| n_trades | 34,626 | exact (= 0 tolerance) |
| Sharpe | -0.1732 | ±1e-4 |
| ann_pnl | -204,664.4 | ±0.5 pip |

HALT pattern: if C-sb-baseline q*=5 test outcome deviates beyond tolerance, the 27.0e-β eval HALTs with `BaselineMismatchError` **before** C-se-trimmed verdict assignment (fail-fast, inherited from 27.0c-α §7.3 / 27.0d-α §7.3).

The trimmed quantile family does **NOT** change C-sb-baseline's behavior — its family is unchanged ({5, 10, 20, 30, 40}). With same train data + same multiclass config + same `random_state=42`, the C-sb-baseline outcome is deterministically identical to 27.0d-β.

### 7.2 D-X8 — 5-fold OOF DIAGNOSTIC-ONLY (inherited verbatim)

5-fold OOF on train, seed=42, **DIAGNOSTIC-ONLY** per 27.0d-α §6.2 / D-W4. The production scoring path uses a single train-fit regressor (same as 27.0d-β); OOF outputs feed only predicted-vs-realised correlation / MAE / R² diagnostics in the sanity probe + eval report.

Fold assignment is the same `make_oof_fold_assignment(n_train, n_folds=5, seed=42)` helper inherited from 27.0c-α. Determinism preserved across 27.0d-β / 27.0e-β.

---

## 8. Verdict tree (inherited unchanged)

Inherited verbatim from 27.0d-α §8 / 26.0c-α / 26.0d-α / 27.0b-α / 27.0c-α:

- H1-weak: Spearman > 0.05
- H1-meaningful: Spearman ≥ 0.10
- H2: Sharpe ≥ 0.082 AND ann_pnl ≥ 180
- H3: Sharpe > −0.192
- H4: Sharpe ≥ 0
- Cross-cell aggregation per 26.0c-α §7.2 (agree → single; disagree → SPLIT_VERDICT_ROUTE_TO_REVIEW)
- H2 PASS → **PROMISING_BUT_NEEDS_OOS only**
- ADOPT_CANDIDATE requires SEPARATE A0-A5 8-gate PR
- NG#10 / NG#11 not relaxed

---

## 9. Mandatory clauses (clauses 1–5 verbatim; clause 6 = PR #323 §7 verbatim)

Clauses 1–5 inherited verbatim. Clause 2 **load-bearing for R-T2 admissibility** (per §0.1 / §4.3).

**Clause 6 verbatim from PR #323 §7** (canonical source-of-truth from PR #323 forward):

> *6. Phase 27 scope. Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR; R7-D and R7-Other are NOT admissible under any Phase 27 scope amendment currently on the table. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D (calibrated EV) was promoted from admissible-but-deferred to formal at sub-phase 27.0c-β via PR #320. S-E (regression-on-realised-PnL) was promoted from "requires scope amendment" to "admissible at 27.0d-α design memo" via Phase 27 S-E scope-amendment PR #323. S-E uses realised barrier PnL (inherited bid/ask executable, D-1 binding) as the per-row regression target under the FIXED R7-A feature family; LightGBM regression is the default model class but the 27.0d-α design memo may specify alternatives within the regression family. S-Other (quantile regression / ordinal / learn-to-rank) remains NOT admissible. R7-D and R7-Other remain NOT admissible. R7-B / R7-C remain admissible only after their own separate scope amendments. Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.*

This design memo IS the 27.0e-α "design memo" required for R-T2's tier promotion to formal evaluation. On merge, the trimmed-quantile policy becomes *formal at sub-phase 27.0e-β*. The 27.0e-β eval PR will re-cite clause 6 verbatim from this PR (which is verbatim from PR #323 §7).

---

## 10. Sanity probe (inherited from 27.0d-α §10; D-X10 additions)

Inherited verbatim from 27.0d-α §10 (items 1–11):

1. Class priors per split — HALT < 1%
2. Per-pair TIME share — HALT > 99%
3. Realised-PnL cache basis (D-1 binding)
4. Mid-to-mid PnL distribution per class (DIAGNOSTIC-ONLY)
5. R7-A new-feature NaN rate per split — HALT > 5%
6. R7-A positivity assertions — HALT > 1% violation
7. Target (realised PnL) distribution on train (DIAGNOSTIC-ONLY)
8. Predicted PnL distribution on val/test (DIAGNOSTIC-ONLY)
9. OOF predicted-vs-realised correlation (DIAGNOSTIC-ONLY)
10. Regressor MAE + R² per split (DIAGNOSTIC-ONLY)
11. Regressor feature importance (DIAGNOSTIC-ONLY)

**NEW for 27.0e** (DIAGNOSTIC-ONLY per D-X10; WARN-only; no HALT):

12. **Quantile-family disclosure per cell** — confirms C-se uses {5, 7.5, 10} and C-sb-baseline uses {5, 10, 20, 30, 40}. Defensive log; sanity check that the cell dict matches the design memo binding.
13. **Trade-count budget audit** — for each (cell, q) pair in C-se, report `n_trades_val` and `n_trades_val / 25,881` (the C-sb-baseline q=5 val baseline count). DIAGNOSTIC-ONLY WARN if any C-se (cell, q) pair has `n_trades_val / 25,881 > 2.0` (i.e., trade-rate inflation factor over 2×). H-B5 itself is the hypothesis under test, so NO HALT is admitted here.

---

## 11. Eval report (27.0e-β) mandatory sections

Inherits the 21-section pattern from 27.0d-α §11. Key changes:

| § | Content | Source |
|---|---|---|
| 1 | Mandatory clauses 1–6 verbatim (clause 6 = PR #323 §7 verbatim) | INHERITED |
| 2 | D-1 binding restated (formal PnL = bid/ask harness; S-E target = same) | INHERITED |
| 3 | R7-A feature set restated (FIXED) | INHERITED |
| 4 | C-se-trimmed + C-sb-baseline cell definitions (per §5; per-cell quantile family) | NEW form (per §5) |
| 5 | Sanity probe (incl. NEW items 12–13) | NEW + INHERITED |
| 6 | Pre-flight diagnostics + row-drop + split dates | INHERITED |
| 7 | All formal cells primary table (val + test for both cells across each cell's quantile family) | INHERITED form |
| 8 | Val-selected cell\* + q\* — FORMAL verdict source | INHERITED |
| 9 | Aggregate H1/H2/H3/H4 outcome + verdict | INHERITED |
| 10 | Cross-cell aggregation (26.0c-α §7.2) | INHERITED |
| 11 | **MANDATORY** 5-column baseline comparison: 26.0d / 27.0b / 27.0c / **27.0d C-se / S-E (q=40)** / 27.0e val-selected | NEW (D-X9: adds 27.0d C-se column) |
| 12 | **MANDATORY** C-sb-baseline reproduction check (n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip) | INHERITED form |
| 13 | **MANDATORY** per-pair Sharpe contribution table (val-selected; D4 sort) | INHERITED form |
| 14 | **MANDATORY** pair concentration per cell | INHERITED form |
| 15 | Classification-quality diagnostics on multiclass head (C-sb-baseline only) | INHERITED (DIAGNOSTIC-ONLY) |
| 16 | Regressor feature importance (4-bucket; DIAGNOSTIC-ONLY) | INHERITED |
| 17 | Predicted-PnL distribution train/val/test (DIAGNOSTIC-ONLY) | INHERITED |
| 18 | Predicted-vs-realised correlation diagnostic (OOF + per-split Pearson + Spearman; DIAGNOSTIC-ONLY) | INHERITED |
| 19 | Regressor MAE + R² on train/val/test (DIAGNOSTIC-ONLY) | INHERITED |
| 20 | Multiple-testing caveat (2 cells × custom-per-cell quantile counts = **3 + 5 = 8 (cell, q) pairs**, down from 10 in 27.0d) | UPDATED |
| 21 | Verdict statement (also picks one of the 4 H-B5 outcome rows from §14) | INHERITED + NEW |
| **22 (NEW)** | **Trimmed vs original quantile family comparison** — DIAGNOSTIC-ONLY side-by-side: 27.0d C-se metrics across original {5,10,20,30,40} (re-cited from PR #325 sweep_results.json) vs 27.0e C-se-trimmed metrics across {5,7.5,10}. Quantifies what the trim actually buys (or doesn't) | NEW (D-X9) |

---

## 12. 27.0e-β implementation contract (high-level only; no code)

The 27.0e-β implementation PR (separate later instruction) will:

- Author `scripts/stage27_0e_s_e_quantile_trim_eval.py` inheriting from `scripts/stage27_0d_s_e_regression_eval.py`
- Author `tests/unit/test_stage27_0e_s_e_quantile_trim_eval.py`
- Implement `evaluate_quantile_family_custom` accepting a list parameter (per §6.1 / D-X5)
- Build cells with `quantile_percents` field (per §6.2 / D-X6)
- Run sanity probe FIRST (incl. NEW items 12–13), then full sweep
- BaselineMismatchError HALT on C-sb-baseline non-match (§7.1; inherited tolerances)
- Emit `artifacts/stage27_0e/eval_report.md` with all 22 sections (incl. NEW §22)
- Add `.gitignore` entries for `artifacts/stage27_0e/*` intermediates analogous to `artifacts/stage27_0d/*`
- Lint via `run_custom_checks.py` + `ruff check` + `ruff format --check` before push
- CI green before merge

None of the above is authorised by THIS PR.

---

## 13. Selection-overfit handling (inherited verbatim from 27.0d-α §13)

> *S-E's two trainable artifacts (LightGBMRegressor for C-se-trimmed; LightGBM multiclass head for C-sb-baseline) are BOTH fit on train-only data. Val data is used ONLY for cutoff selection (quantile-of-val q\* per cell, where the family is per-cell per §4). Test data is touched exactly once at the val-selected (cell\*, q\*). 5-fold OOF is DIAGNOSTIC-ONLY and does NOT enter formal verdict routing. Any deviation is a NG#10 violation.*

The trimmed quantile family does NOT change the selection-overfit risk profile — val-only selection on a smaller q-grid (3 candidates for C-se instead of 5) produces *less* multiple-testing exposure, making the selection-overfit guarantee *stronger* under R-T2.

---

## 14. H-B5 falsification criteria (D-X11; design-memo binding to prevent post-hoc rationalisation)

Pre-stated outcome table. The 27.0e-β eval_report §21 verdict statement MUST pick the matching row and announce the H-B5 routing implication. No re-interpretation of the rows after the fact.

| Outcome | H-B5 status | Routing implication |
|---|---|---|
| C-se-trimmed at some q ∈ {5, 7.5, 10} passes H2 (Sharpe ≥ 0.082 AND ann_pnl ≥ 180) | **STRONG SUPPORT** | PROMISING_BUT_NEEDS_OOS branch triggered → separate A0-A5 8-gate PR. H-B5 elevated to load-bearing. Phase 27's first PROMISING outcome |
| C-se-trimmed at some q passes H1-meaningful (≥ 0.10) but NOT H2 | **PARTIAL SUPPORT** | route to R-T1 (further selection-rule revision; e.g., absolute-threshold / minimum-confidence cells) OR R-T3 (concentration formalisation; requires scope amendment) |
| C-se-trimmed at all 3 q values produces wrong-direction Sharpe (Spearman > 0.05 but Sharpe < H3 = −0.192) | **FALSIFIED** | bottleneck is deeper than selection-rule; route to R-B / R-C / R-E |
| C-se-trimmed at all 3 q values FAILS H1-weak (Spearman ≤ 0.05) | **PARTIALLY FALSIFIED + new question** | trim destroyed the discriminative signal; sub-question whether q=40 in 27.0d was load-bearing for ranking too. Route to R-T1 (preserve quantile-of-val but add absolute-threshold cells) OR R-E |

This 4-row table is **binding** under this design memo. The 27.0e-β eval_report §21 statement names exactly one row.

---

## 15. What this PR will NOT do

- ❌ Authorise 27.0e-β eval implementation (separate later user instruction)
- ❌ Authorise post-27.0e routing review
- ❌ Authorise any other Phase 27 sub-phase (27.0f / 27.0g / ...)
- ❌ Authorise R-T1 (absolute-threshold / minimum-confidence design memo)
- ❌ Authorise R-T3 (per-pair-concentration formalisation scope amendment)
- ❌ Authorise R7-B / R7-C scope amendment
- ❌ Authorise alternative S-E regression-variant cells (MSE / L1 / Tweedie still deferred per 27.0d-α §7.6)
- ❌ Authorise model-class changes for non-S-E score objectives
- ❌ Modify Phase 27 scope per kickoff §8 / PR #323 clause 6
- ❌ Modify clause 2 diagnostic-only binding (load-bearing for R-T2 framing)
- ❌ Promote per-pair-Sharpe-contribution / threshold-sweep / concentration / trade-count to formal verdict inputs
- ❌ Relax the ADOPT_CANDIDATE 8-gate A0-A5 wall
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279) / X-v2 OOS gating / Phase 22 frozen-OOS contract / production v9 20-pair tip 79ed1e8
- ❌ Pre-approve any production deployment under any 27.0e-β outcome
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b / 27.0c / 27.0d / routing reviews / scope amendments)
- ❌ Reopen Phase 26 L-class label-target redesign space
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md`
- ❌ Auto-route to 27.0e-β implementation after merge

---

## 16. Sign-off

Phase 27 produces its fifth design memo (after kickoff #316 + 27.0b-α #317 + 27.0c-α #320 + 27.0d-α #324). The R-T2 trimmed-quantile policy moves from *admissible under existing clause 6 + clause 2* (per PR #326 §4.2) → *formal at sub-phase 27.0e-β* on merge of this design memo. The 27.0e-β implementation PR is triggered by a separate later user instruction. No auto-route.

**This PR stops here.**
