# Phase 25.0e-α — F3 Cross-Pair / Relative Currency Strength Design Memo

**Type**: doc-only design memo (binding contract for 25.0e-β)
**Status**: design-stage; NO implementation in this PR
**Branch**: `research/phase25-0e-alpha-f3-design`
**Base**: master @ 5d21bc8 (post-PR #291 merge)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Routing context (PR #291 origin)

PR #291 (routing review post-deployment-audit) consolidated three converging data points — F1 best cell (PR #284), F2 best cell (PR #287), and 25.0d-β deployment audit (PR #290) — and surfaced a 7-option routing space with a per-class prioritisation framework. The user selected **Option A (F3 cross-pair / relative currency strength)** because:

- F1 and F2 are both volatility-axis classes; deployment-layer fixes did not monetise either at AUC ≈ 0.56.
- F3 is the **most orthogonal** admissible feature class to F1/F2 in PR #291 §5.4.
- F3 is implementable on the canonical 20-pair feed without data-source extension (unlike F5 liquidity, which needs volume/spread loaders).
- F4 (range compression) and F6 (higher-TF) overlap with F1/F2 and risk reproducing the same AUC-PnL gap.

This memo is the **design-stage** half of the 25.0e split (alpha=design, beta=eval), matching the F1/F2/25.0d pattern.

---

## 1. PR scope

| Item | Value |
|---|---|
| PR type | doc-only |
| Files added | 1 (`docs/design/phase25_0e_alpha_f3_design.md`) |
| Files modified | 0 |
| `src/` touched | 0 |
| `scripts/` touched | 0 |
| `tests/` touched | 0 |
| `artifacts/` touched | 0 |
| DB schema touched | 0 |
| MEMORY.md touched | 0 |
| Stop after this PR merges | YES — 25.0e-β is a separate PR |

---

## 2. F3 feature class definition (binding for 25.0e-β)

**F3 = cross-pair / relative currency strength.** Per-bar features derived from synchronised multi-pair returns at the same M5 bar timestamp, targeting the **per-currency** dimension that F1 (per-pair vol) and F2 (per-pair regime) cannot reach.

### 2.1 Admissible feature subgroups in 25.0e-β

| Subgroup | Description | Example feature |
|---|---|---|
| **F3-a** | Per-currency synthetic strength index | `usd_strength_zscore_20` = z-score of mean signed log_return across canonical USD-quote/base pairs over a 20-bar lookback |
| **F3-b** | Cross-pair correlation regime | `corr_eu_gu_60` = rolling 60-bar Pearson correlation between EUR_USD and GBP_USD log_returns |

### 2.2 Subgroups DEFERRED to a potential 25.0e-γ (NOT in 25.0e-β scope)

| Subgroup | Description | Status |
|---|---|---|
| **F3-c** | Pair beta vs equal-weight basket | Admissible future extension; deferred. |
| **F3-d** | Currency-pair divergence | Admissible future extension; deferred. |

> **Rule**: F3-c and F3-d are picked up only if 25.0e-β passes H1 (i.e. F3-a/F3-b is admissibly discriminative). If 25.0e-β fails H1, F3-c/F3-d are not pursued.

### 2.3 Per-currency strength (F3-a) construction rules

For each base currency C ∈ {USD, EUR, JPY, GBP, AUD, CAD, CHF, NZD}:

- **Only canonical available pairs are used.** No unavailable synthetic pair is created. The canonical 20-pair universe is fixed by `_PIP_SIZE` in `lgbm_strategy.py` (AUD_CAD, AUD_JPY, AUD_NZD, AUD_USD, CHF_JPY, EUR_AUD, EUR_CAD, EUR_CHF, EUR_GBP, EUR_JPY, EUR_USD, GBP_AUD, GBP_CHF, GBP_JPY, GBP_USD, NZD_JPY, NZD_USD, USD_CAD, USD_CHF, USD_JPY).
- For each pair P containing C in the canonical universe:
  - **If C is base in P** (e.g. EUR_USD with C=EUR), use `+log_return(P)`.
  - **If C is quote in P** (e.g. EUR_GBP with C=GBP), use `-log_return(P)`.
- Take the equal-weight mean of these signed log_returns over the available pairs → `currency_strength_C(t)`.
- Take rolling z-score over `lookback ∈ {20, 50, 100}`.

**Concrete coverage example** for C=NZD: canonical pairs containing NZD are AUD_NZD (NZD is quote → −log_return), NZD_JPY (NZD is base → +log_return), NZD_USD (NZD is base → +log_return). Equal-weight mean over these 3 signed returns. No synthetic NZD-vs-CHF series is constructed.

### 2.4 Cross-pair correlation (F3-b) construction rules

- Select a small fixed pair-shortlist for the eval (e.g. {EUR_USD, GBP_USD, AUD_USD, USD_JPY, USD_CHF}).
- Compute pairwise rolling Pearson correlation between each pair's log_returns over `lookback ∈ {20, 50, 100}` bars.
- Optional aggregation: mean absolute correlation across all pairs (`mean_abs_corr_<lb>`) as a single regime feature.
- Pair-level outputs are alternative feature instances; the sweep cell (§3) controls which form is fed to the classifier.

### 2.5 Strict-causal rule (signal_ts = t)

**F3 features at signal_ts = t must use only bars strictly before t, i.e. bars ≤ t−1.**

This applies to **all** F3 derivations:
- cross-pair returns
- per-currency strength index
- rolling correlation (F3-b)
- rolling z-score windows
- (deferred) beta and divergence (F3-c/F3-d)

**Implementation contract**: every cross-pair series must be `shift(1)` before any rolling-window aggregation that produces a t-indexed feature. The 25.0e-β implementation must include a unit test that asserts `feature_value(t)` is invariant under perturbation of bar t (bar-t lookahead test).

---

## 3. Sweep grid (binding for 25.0e-β)

| Knob | Values | Levels |
|---|---|---|
| Subgroup | {F3-a alone, F3-b alone, F3-a+F3-b} | 3 |
| Lookback | {20, 50, 100} | 3 |
| Z-score window | {20, 50} | 2 |
| **Total cells** | | **18** |

> Capped at 18 to stay within the Phase 25 18–33 cell budget and to reflect the post-F1/F2 preference for smaller, higher-power grids.

F3-c / F3-d are **deferred** per §2.2 and not part of this 18-cell grid.

---

## 4. Hypothesis chain

| H | Statement |
|---|---|
| **H1** | Best F3 cell test AUC > 0.55 (admissibly discriminative). |
| **H2** | Best F3 cell realised Sharpe ≥ +0.082 AND ann_pnl ≥ +180 pip on the harness's A1/A2 segment. |
| **H3** | F3 is **orthogonal** to F1/F2: combining F3 with the best-of-{F1, F2} feature set lifts test AUC by ≥ 0.01 over the best-of-{F1, F2} alone. |
| **H4** | F3 escapes the AUC-PnL gap: realised Sharpe at F3 best cell with AUC ≈ 0.56 ≥ 0 (vs F1/F2 < 0). |

> **H2 covers A1/A2 only.** A3-A5 (frozen-OOS, multi-fold cross-section, +0.5 pip stress) are evaluated separately; see §7 verdict tree.

> **H4 is the structural-gap escape test.** If F3 also confirms the gap (negative realised Sharpe at AUC ≈ 0.56), this **strengthens the soft-stop condition** per PR #291 §6.4 — the user judges whether to continue F4-F6 or close Phase 25.

---

## 5. Eval harness (inherits 25.0a-β)

The 25.0e-β eval reuses the harness frozen at PR #281 (25.0a-α) / PR #282 (25.0a-β). NO new harness gates are added in 25.0e.

| Component | Spec |
|---|---|
| Universe | 20-pair canonical (M5 bars, 25.0a-β-spread dataset) |
| Label | LdP-style triple-barrier path-quality binary, K_FAV=1.5×ATR, K_ADV=1.0×ATR |
| Resolution | Same-bar SL-first conservative |
| Classifier | Bidirectional logistic regression, `class_weight='balanced'` |
| Split | 70 / 15 / 15 train / val / test, strict chronological order |
| PnL | Realised barrier PnL via M1 path re-traverse |
| LOW_BUCKET_N | flag at n < 100 (matches F1/F2/25.0d) |

### 5.1 Three production-misuse guards (inherited verbatim)

1. **research-not-production**: F3 features are NOT auto-routed into `feature_service.py` or `lgbm_strategy.py`. Production wiring is a separate post-ADOPT discussion.
2. **threshold-sweep-diagnostic**: any threshold sweep in 25.0e-β is diagnostic-only; ADOPT criteria do not depend on it.
3. **directional-comparison-diagnostic**: any "long-only vs short-only vs combined" decomposition is diagnostic-only; ADOPT criteria do not depend on it.

---

## 6. Calibration diagnostics (per PR #291 §8 suggestion)

PR #291 §8 *suggested* (NOT mandated) future F-class memos consider including calibration diagnostics from the start. **This memo adopts that suggestion for 25.0e-β** so that 25.0d-β's H-A finding (miscalibrated probabilities at AUC ≈ 0.56) is detected before the threshold sweep, not after.

| Diagnostic | Purpose | Output |
|---|---|---|
| Decile reliability table | Catch H-A miscalibration before threshold sweep | 10 buckets of P̂(win) vs realised win-rate |
| Brier score per bucket | Quantify miscalibration magnitude | one Brier score per decile + overall |

> **Diagnostic-only**: these tables do NOT change ADOPT criteria. NG#10/NG#11 are not relaxed; H2 + 8-gate combine to gate ADOPT (see §7).

---

## 7. Verdict tree

A1/A2 corresponds to the H2 segment (Sharpe + ann_pnl on the eval test set). A3-A5 are the standard 8-gate harness segments (frozen-OOS, multi-fold A4 ≥ 3/4, A5 +0.5 pip stress > 0).

| Outcome | Verdict |
|---|---|
| H1 PASS, H2 PASS, **AND all 8-gate requirements (A1-A5) pass** | **ADOPT_CANDIDATE** (production-wiring discussion separately) |
| H1 PASS, H2 PASS, **A3-A5 partial pass** (e.g. A4 ≥ 3/4 fails or A5 stress flips negative) | **PROMISING_BUT_NEEDS_OOS** — eligible for follow-up OOS extension; NOT ADOPT |
| H1 PASS, H2 PASS, **A3-A5 fail** | **REJECT** — A1/A2 lift not robust to OOS / cross-section / cost stress |
| H1 PASS, H2 FAIL, H3 PASS | **REJECT_BUT_INFORMATIVE_ORTHOGONAL** — orthogonal escape candidate for combined-feature future work |
| H1 PASS, H2 FAIL, H3 FAIL | **REJECT_BUT_INFORMATIVE_REDUNDANT** — admissibly discriminative but redundant with F1/F2 |
| H1 FAIL | **REJECT_NON_DISCRIMINATIVE** |

> **H2 PASS alone does not imply ADOPT_CANDIDATE.** H2 covers A1/A2 only; A3-A5 must also pass for ADOPT_CANDIDATE.

> **Independent of the verdict above, H4 FAIL** (i.e. structural gap reproduced at F3 best cell with AUC ≈ 0.56 and realised Sharpe < 0) **triggers PR #291 §6.4 strong soft-stop strengthening** — user judgement is required before F4/F5/F6 work.

---

## 8. Stop conditions inherited from PR #291 §6

| Trigger | Action |
|---|---|
| F3 H4 FAIL | Strong soft-stop strengthening per #291 §6.4 → user judgement required before continuing to F4/F5/F6. |
| F3 H2 PASS + A3-A5 PASS → ADOPT_CANDIDATE | Pivot to production-wiring discussion (SEPARATE from F4-F6 continuation). |
| F3 H1 PASS, H3 PASS, H2 FAIL | F3 is orthogonal but unmonetisable on its own → F3+F1 / F3+F2 combination test is eligible (would be a separate Phase 25.0f scope). |
| F3 H1 FAIL | F3 not discriminative; routing reverts to PR #291 §7 remaining options (F4 / F5 / F6 / E / F / G). |

---

## 9. Mandatory clauses (verbatim, 6 total — to be carried into 25.0e-β `eval_report.md`)

1. **Phase 25 framing** — *Phase 25 is the entry-side return on alternative admissible feature classes (F1-F6) layered on the 25.0a-β path-quality dataset. Each F-class is evaluated as an independent admissible-discriminative experiment. ADOPT requires both H2 PASS and the full 8-gate A1-A5 harness.*
2. **Diagnostic columns prohibition** — *Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. They exist to characterise the AUC-PnL gap, not to monetise it.*
3. **γ closure preservation** — *Phase 24 γ hard-close (PR #279) is unmodified. No 25.0e PR touches stage24 artifacts or stage24 verdict text.*
4. **Production-readiness preservation** — *X-v2 OOS gating remains required before any production deployment. No 25.0e PR pre-approves production wiring.*
5. **NG#10 / NG#11 not relaxed** — *25.0e PRs do not change the entry-side budget cap or the diagnostic-vs-routing separation rule.*
6. **F3 verdict scoping** — *The 25.0e-β verdict applies only to the F3 best cell on the 25.0a-β-spread dataset. Convergence with F4-F6 is a separate question; structural-gap inferences are jointly conditional on F3 H4 outcome.*

---

## 10. PR chain reference

```
#280 (Phase 25 kickoff)
  → #281 (25.0a-α path-quality dataset spec)
  → #282 (25.0a-β path-quality dataset)
  → #283 (25.0b-α F1 design memo)
  → #284 (25.0b-β F1 eval — REJECT_BUT_INFORMATIVE)
  → #285 (first scope review, post-F1)
  → #286 (25.0c-α F2 design memo)
  → #287 (25.0c-β F2 eval — REJECT_BUT_INFORMATIVE)
  → #288 (second scope review, post-F2)
  → #289 (25.0d-α deployment audit design memo)
  → #290 (25.0d-β deployment audit eval — H-A miscalibrated, H-B/H-D refuted, H-F structural gap CONFIRMED)
  → #291 (routing review post-deployment-audit)
  → THIS PR (25.0e-α F3 cross-pair / relative currency strength design memo)
  → 25.0e-β F3 eval (separate PR; NOT in scope here)
```

---

## 11. What this PR will NOT do

- ❌ Implement any F3 feature in `src/` or `scripts/`.
- ❌ Run any sweep, generate any artifact under `artifacts/stage25_0e/`.
- ❌ Modify F1 / F2 / 25.0d / 25.0e routing verdicts.
- ❌ Pre-approve production deployment of any F3 feature.
- ❌ Relax NG#10 / NG#11.
- ❌ Modify γ closure (PR #279).
- ❌ Touch existing artifacts (stage25_0a / 0b / 0c / 0d remain intact).
- ❌ Update `MEMORY.md` (closure memo deferred per established Phase 25 pattern).
- ❌ Auto-route to 25.0e-β implementation. The next PR opens only after explicit user instruction.

---

## 12. Test plan (CI for this doc-only PR)

- [x] `python tools/lint/run_custom_checks.py` (rc = 0 expected; doc-only change)
- [x] `ruff format --check` (no code changed)
- [x] No tests added or modified (doc-only PR)
- [x] CI gates: `contract-tests` + `test` (no functional change → green expected)

---

## 13. Sign-off

This memo is the binding contract for 25.0e-β. The 25.0e-β implementation PR must:

- Implement F3-a and F3-b strictly per §2.3, §2.4, §2.5.
- Run the 18-cell sweep per §3 (and only that 18-cell sweep — F3-c/F3-d deferred).
- Test the hypothesis chain per §4 against the eval harness per §5.
- Include calibration diagnostics per §6 (diagnostic-only).
- Apply the verdict tree per §7 — H2 PASS alone is **NOT** ADOPT_CANDIDATE.
- Honour all six mandatory clauses per §9 verbatim in `eval_report.md`.
- Honour the strict-causal rule per §2.5 with an explicit bar-t lookahead unit test.
- NOT relax NG#10 / NG#11; NOT modify γ closure; NOT touch stage25_0a/0b/0c/0d artifacts.
