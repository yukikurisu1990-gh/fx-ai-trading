# Phase 25.0f-α — F5 Liquidity / Spread / Volume Design Memo

**Type**: doc-only design memo (binding contract for 25.0f-β)
**Status**: design-stage; NO implementation in this PR
**Branch**: `research/phase25-0f-alpha-f5-design`
**Base**: master @ c471356 (post-PR #294 merge)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Routing context (PR #294 → R1)

PR #294 (Phase 25 Routing Review Post-F3) consolidated four evidence points — three admissible F-classes (F1 #284, F2 #287, F3 #293) + one deployment-layer audit (25.0d-β #290) — and surfaced a five-option routing space (R1-R5). The user picked **R1 (F5 liquidity / spread / volume)** with explicit framing as **the LAST feature-axis attempt within Phase 25**.

The rationale (from the user's R1 selection):

- F1 / F2 / F3 covered price / volatility / cross-pair currency-strength axes; all hit the structural-gap signature.
- F4 (range compression) and F6 (higher-TF) overlap with F1/F2 per #291 §5.4 and have low expected payoff.
- F5 is the only remaining HIGH-orthogonality F-class, anchored on the spread / liquidity / cost-regime dimension that is fundamentally distinct from price-derived axes.
- If F5 ALSO confirms the structural-gap signature, the case for Phase 25 soft close (R5) becomes **strongly supported**, and the natural pivot becomes R2 (label redesign) as a new sub-phase.

This memo is the **design-stage** half of the 25.0f split (alpha = design, beta = eval), matching the F1 / F2 / F3 / 25.0d pattern.

---

## 1. PR scope

| Item | Value |
|---|---|
| PR type | doc-only |
| Files added | 1 (`docs/design/phase25_0f_alpha_f5_design.md`) |
| Files modified | 0 |
| `src/` touched | 0 |
| `scripts/` touched | 0 |
| `tests/` touched | 0 |
| `artifacts/` touched | 0 |
| DB schema touched | 0 |
| MEMORY.md touched | 0 |
| Stop after this PR merges | YES — 25.0f-β is a separate PR |

---

## 2. F5 feature class definition (binding for 25.0f-β)

**F5 = liquidity / spread / volume.** Per-bar features derived from the bid/ask spread series and the M1 volume column already present in the canonical 25.0a-β data path. Targets the **execution-cost / liquidity-regime** dimension that F1 (per-pair vol), F2 (per-pair regime), and F3 (cross-pair currency strength) cannot reach.

### 2.1 Admissible feature subgroups in 25.0f-β

| Subgroup | Description |
|---|---|
| **F5-a** | **Spread regime** (statistical) — z-score / quantile of M5 mid-spread over a rolling lookback. |
| **F5-b** | **Volume regime** (statistical) — z-score / quantile of M5 aggregated volume over a rolling lookback. |
| **F5-c** | **Spread-volume joint regime / interaction features** — predeclared interaction terms (e.g. `spread_z × volume_z`, `high_spread AND high_volume`, `high_spread AND low_volume`, `spread_regime × volume_regime`). **F5-c must not be target-aware and must not use future information.** |

### 2.2 F5-a + F5-b is concat; F5-c is interaction

This distinction is binding for the 25.0f-β implementation:

- **F5-a + F5-b** (a multi-cell sweep variant) is the **concatenation** of F5-a's spread-z column and F5-b's volume-z column. Each remains a marginal feature; no cross-product is taken.
- **F5-c** is the **interaction / joint-regime feature set**. F5-c's columns explicitly mix spread and volume into joint signals (cross-product, AND-flags, regime-pair indicators). F5-c is **NOT** the same as `F5-a + F5-b` concat.
- **F5-a + F5-b + F5-c** (a sweep cell) provides marginals AND joint terms together for the model to weight.

> The 25.0f-β implementation must enforce this distinction in `feature_columns_for_cell()`: F5-a + F5-b emits 2 columns (spread-z, volume-z); F5-c emits a separate set of joint-regime columns (predeclared, see §2.5); F5-a + F5-b + F5-c emits the union.

### 2.3 Subgroups DEFERRED (not in 25.0f-β scope)

| Subgroup | Description | Status |
|---|---|---|
| **F5-d** | Tick-level micro-imbalance | Deferred. F5-d would only be picked up if 25.0f-β passes H1; given Phase 25's Strong Soft Stop status, treat as a hard stop on F5 sub-extensions until a routing review explicitly re-opens them. |
| **F5-e** | Pair-level liquidity rank | Deferred — would need cross-pair coupling, which overlaps F3. |

### 2.4 F5-a (spread) construction rules

- **Source**: `spread_at_signal_pip` is already in `artifacts/stage25_0a/path_quality_dataset.parquet`. **No new data extension required.** Spread is direction-independent at the (`pair`, `signal_ts`) level.
- For each pair, build a per-pair time series of M5 spread keyed by `signal_ts`. (Take the unique `(pair, signal_ts)` pairs and their spread; drop the `direction` axis.)
- Compute `f5a_spread_z_<lb>` = `(spread − rolling_mean) / rolling_std` over `lookback ∈ {20, 50, 100}`.
- Optional supplementary form (selected via cell knob): `f5a_spread_pctile_<lb>` = quantile rank of spread within the same rolling window.
- **Causal**: spread series is `shift(1)` BEFORE rolling so feature(t) uses bars ≤ t-1.

### 2.5 F5-b (volume) construction rules

- **Source**: M1 BA jsonl `volume` column (already loaded by the eval pipeline; no new data extension required).
- Aggregate M1 volume to M5 (sum over the 5 M1 bars in each M5 bar; right-closed / right-labeled to match `aggregate_m1_to_tf` semantics in `stage23_0a`).
- For each pair, compute `f5b_volume_z_<lb>` = `(volume − rolling_mean) / rolling_std` over `lookback ∈ {20, 50, 100}`.
- Optional supplementary form (selected via cell knob): `f5b_volume_pctile_<lb>` = quantile rank of volume within the same rolling window.
- **Causal**: shift(1) before rolling.

#### 2.5.1 Pre-flight contract for volume (binding)

> *25.0f-β must pre-flight verify that **volume is present, non-null enough, and causally aligned** in the M1 / M5 data. If volume is absent or unusable, F5-b and F5-c must **halt-and-report**, not silently degrade.*

The 25.0f-β implementation must, before running the sweep:

1. Load a representative sample of pairs (e.g. all 20 pairs at least one M1 BA jsonl each).
2. Verify:
   - `volume` column is present in every loaded row.
   - Non-null fraction across the eval span is ≥ 0.99 per pair (configurable threshold; below this → halt).
   - M1 → M5 aggregation produces a strictly non-decreasing index aligned to the same M5 bar boundaries used by 25.0a-β (causality check).
   - Volume values are non-negative integers / floats (sanity check).
3. If any check fails, **halt the eval** with a non-zero exit code and an explicit error report; do NOT silently fall back to F5-a-only (this would change the sweep grid mid-run).

This pre-flight contract must be implemented as a function that the 25.0f-β eval calls **before** the sweep loop, and the failure path must be covered by a unit test (`test_f5_volume_preflight_halts_on_missing_volume`).

### 2.6 F5-c (spread-volume joint / interaction) construction rules

F5-c is the **joint / interaction** feature set. Predeclared columns (NOT target-aware; NOT future-info):

| Column | Construction |
|---|---|
| `f5c_spread_x_volume_<lb>` | `f5a_spread_z_<lb>` × `f5b_volume_z_<lb>` (sign-bearing joint product; bars ≤ t-1 because both inputs are causal) |
| `f5c_high_spread_high_vol_<lb>` | bool `(f5a_spread_z_<lb> > 1.0) AND (f5b_volume_z_<lb> > 1.0)` (both above 1σ) |
| `f5c_high_spread_low_vol_<lb>` | bool `(f5a_spread_z_<lb> > 1.0) AND (f5b_volume_z_<lb> < -1.0)` (illiquid stress) |
| `f5c_low_spread_high_vol_<lb>` | bool `(f5a_spread_z_<lb> < -1.0) AND (f5b_volume_z_<lb> > 1.0)` (deep liquidity) |
| `f5c_spread_regime_x_vol_regime_<lb>` | categorical product of spread tercile and volume tercile (9 buckets, encoded one-hot) |

> **F5-c must not be target-aware and must not use future information.** All inputs to F5-c columns are F5-a / F5-b columns (themselves shift(1)-causal); the interaction operations are pointwise so causality is preserved automatically.

If volume pre-flight fails (per §2.5.1), F5-c is also halted (since 4 of 5 F5-c columns depend on volume).

### 2.7 Strict-causal rule (signal_ts = t)

> **F5 features at signal_ts = t must use only bars strictly before t (bars ≤ t-1).**

All spread / volume / joint series go through `shift(1)` BEFORE any rolling aggregation. The 25.0f-β implementation must include **bar-t lookahead unit tests** for each subgroup:

- `test_bar_t_lookahead_invariance_f5a_spread`
- `test_bar_t_lookahead_invariance_f5b_volume`
- `test_bar_t_lookahead_invariance_f5c_joint`

Each test perturbs bar t in the input series, recomputes the feature, and asserts feature(t) is unchanged.

---

## 3. Sweep grid (binding for 25.0f-β)

| Knob | Values | Levels |
|---|---|---|
| Subgroup | {F5-a alone, F5-b alone, F5-c alone, F5-a+F5-b, F5-a+F5-c, F5-b+F5-c, F5-a+F5-b+F5-c} | 7 |
| Lookback | {20, 50, 100} | 3 |
| **Total cells** | | **21** |

> 21 cells stays within the Phase 25 18–33 cell budget (matches F2 = 18, F3 = 18, F1 = 24; comparable scale). One rolling-stat window per cell (z-score window equals lookback for simplicity, matching the F1 / F3 design philosophy).

> **F5-d (tick imbalance) and F5-e (pair liquidity rank) are NOT in this 21-cell grid** (deferred per §2.3).

---

## 4. Hypothesis chain

| H | Statement |
|---|---|
| **H1** | best F5 cell test AUC > 0.55 (admissibly discriminative) |
| **H2** | best F5 cell A1+A2 (Sharpe ≥ +0.082, ann_pnl ≥ +180 pip) on 8-gate harness |
| **H3** | best F5 cell test AUC ≥ best-of-{F1, F2, F3} + 0.01 (NOTE H3 baseline updated to include F3) |
| **H4** | best F5 cell realised Sharpe ≥ 0 at AUC ≈ structural-gap regime (escape test) |

### 4.1 H3 baseline update (vs 25.0e-α §4)

- 25.0e-α §4 used best-of-{F1, F2} = 0.5644.
- 25.0f-α uses best-of-{F1, F2, F3} = max(0.5644, 0.5613, 0.5480) = **0.5644** (F1 still leading).
- **H3 PASS threshold = 0.5744** (lift ≥ 0.01 over the running best across all admissible F-classes evaluated to date).
- Numerically identical to 25.0e-α's threshold; the conceptual update is that F3 has been evaluated and is below F1/F2 best, so the comparison set is broader.

### 4.2 H4 framing for "last feature-axis attempt"

Given Phase 25's Strong Soft Stop status (#294 §4) and F5 being the LAST high-orthogonality F-class within Phase 25:

| H4 outcome | Implication |
|---|---|
| **H4 FAIL** (best F5 realised Sharpe < 0 at AUC ≈ 0.56) | **Strongly supports definitive feature-axis stop within Phase 25.** The next recommended routing consideration becomes R5 (Phase 25 soft close) or R2 (label redesign), but the user still chooses. |
| H4 PASS (best F5 realised Sharpe ≥ 0 even at AUC ≈ 0.56) | Surprising but possible — would re-open the feature-axis case; F5 routing-decision PR follows. |

---

## 5. Eval harness (inherits 25.0a-β; NO new gates)

| Component | Spec |
|---|---|
| Universe | 20-pair canonical (M5 bars, 25.0a-β-spread dataset) |
| Label | LdP-style triple-barrier, K_FAV = 1.5 × ATR, K_ADV = 1.0 × ATR, same-bar SL-first |
| Classifier | Bidirectional logistic regression, `class_weight='balanced'` |
| Split | 70 / 15 / 15 strict chronological train / val / test |
| Realised PnL | M1 path re-traverse |
| LOW_BUCKET_N | flag at n < 100 |
| 8-gate | A0 ≥ 70 ann trades, A1 Sharpe ≥ +0.082, A2 ann_pnl ≥ +180 pip, A3 MaxDD ≤ 200, A4 ≥ 3/4 folds, A5 +0.5 pip stress > 0 |

### 5.1 Three production-misuse guards (inherited verbatim)

1. **research-not-production**: F5 features stay in `scripts/`; not auto-routed to `feature_service.py`.
2. **threshold-sweep-diagnostic**: any threshold sweep is diagnostic-only.
3. **directional-comparison-diagnostic**: any long/short decomposition is diagnostic-only.

---

## 6. Calibration diagnostics (per #291 §8 / #292 §6 pattern; diagnostic-only)

Decile reliability + per-bucket Brier + overall Brier on the best cell. Same pattern as F3 (PR #292 / #293).

> Diagnostic-only — does NOT change ADOPT criteria. NG#10 / NG#11 not relaxed. H2 + 8-gate combine to gate ADOPT (per §7).

---

## 7. Verdict tree

Per-cell verdict (mirrors F3 25.0e-α §7):

| Outcome | Verdict |
|---|---|
| H1 PASS, H2 PASS, all 8 gates A0–A5 pass | **ADOPT_CANDIDATE** |
| H1 PASS, H2 PASS, A3-A5 partial | PROMISING_BUT_NEEDS_OOS |
| H1 PASS, H2 PASS, A3-A5 fail | REJECT |
| H1 PASS, H2 FAIL, H3 PASS | REJECT_BUT_INFORMATIVE_ORTHOGONAL |
| H1 PASS, H2 FAIL, H3 FAIL | REJECT_BUT_INFORMATIVE_REDUNDANT |
| H1 FAIL | REJECT_NON_DISCRIMINATIVE |

> **H2 PASS alone does NOT imply ADOPT_CANDIDATE.** Full A0–A5 must pass.

> **H4 FAIL independently triggers PR #294 §10 routing recommendation — F5 H4 FAIL strongly supports definitive feature-axis stop within Phase 25, but the user still chooses.**

---

## 8. Stop conditions inherited from #291 §6 + #294 §10

| Trigger | Action |
|---|---|
| F5 H4 FAIL | **Strongly supports definitive feature-axis stop within Phase 25.** Next recommended routing consideration: R5 (soft close) or R2 (label redesign). User still chooses. |
| F5 H2 PASS + A0–A5 PASS → ADOPT_CANDIDATE | Pivot to production-wiring discussion (separate from any further sweep). |
| F5 H1 PASS, H3 PASS, H2 FAIL | F5 is orthogonal but unmonetisable — eligible for combined-feature future work in a NEW phase, not re-opening Phase 25. |
| F5 H1 FAIL | Final feature-axis evidence point added; routing reverts to PR #294 §10 — R2 / R5 most likely; user picks. |

---

## 9. Mandatory clauses (verbatim, 6 total — to be carried forward in 25.0f-β `eval_report.md`)

1. **Phase 25 framing** (inherited from #280) — *Phase 25 is the entry-side return on alternative admissible feature classes (F1-F6) layered on the 25.0a-β path-quality dataset. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.*
2. **Diagnostic columns prohibition** — *Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.*
3. **γ closure preservation** — *Phase 24 γ hard-close (PR #279) is unmodified.*
4. **Production-readiness preservation** — *X-v2 OOS gating remains required before any production deployment.*
5. **NG#10 / NG#11 not relaxed**.
6. **F5 verdict scoping** — *The 25.0f-β verdict applies only to the F5 best cell on the 25.0a-β-spread dataset. F5 is the LAST feature-axis attempt within Phase 25. F5 H4 FAIL strongly supports definitive feature-axis stop; next recommended routing consideration is R5 (soft close) or R2 (label redesign), but the user still chooses.*

---

## 10. PR chain reference

```
#280 (Phase 25 kickoff)
  → #281 / #282 (25.0a dataset)
  → #283 / #284 (F1) → #285 (review)
  → #286 / #287 (F2) → #288 (review)
  → #289 / #290 (25.0d audit) → #291 (review post-audit)
  → #292 / #293 (F3) → #294 (review post-F3)
  → THIS PR (25.0f-α F5 design memo)
  → 25.0f-β F5 eval (separate PR; NOT in scope here)
  → If F5 H4 FAIL: R5 closure memo OR R2 label redesign kickoff (next phase) — user picks
  → If F5 H4 PASS: F5 routing-decision PR
```

---

## 11. What this PR will NOT do

- ❌ Implement any F5 feature in `src/` or `scripts/`.
- ❌ Run any sweep, generate any artifact under `artifacts/stage25_0f/`.
- ❌ Modify F1 / F2 / 25.0d / F3 / routing-review verdicts (#284 / #287 / #290 / #293 / #294).
- ❌ Pre-approve production deployment of any F5 feature.
- ❌ Relax NG#10 / NG#11.
- ❌ Modify γ closure (PR #279).
- ❌ Touch existing artifacts (stage25_0a / 0b / 0c / 0d / 0e remain intact).
- ❌ Update `MEMORY.md` (closure memo deferred per established Phase 25 pattern).
- ❌ Auto-route to 25.0f-β implementation. The next PR opens only after explicit user instruction.
- ❌ Pre-approve R5 (soft close) or R2 (label redesign) on F5 H4 FAIL — those remain user-decision routing options.

---

## 12. Test plan (CI for this doc-only PR)

- [x] `python tools/lint/run_custom_checks.py` rc = 0 expected (doc-only)
- [x] `ruff format --check` no code changed
- [x] No tests added or modified (doc-only)
- [x] CI gates: `contract-tests` + `test` (no functional change → green expected)
- [x] Branch hygiene pre-push: `git diff --stat origin/master..HEAD` shows ONLY 1 expected file

---

## 13. Sign-off

This memo is the binding contract for 25.0f-β. The 25.0f-β implementation PR must:

- Implement F5-a (spread regime), F5-b (volume regime), F5-c (joint / interaction) strictly per §2.3 / §2.4 / §2.5 / §2.5.1 / §2.6 / §2.7.
- Honour the F5-a + F5-b vs F5-c distinction per §2.2 (concat vs interaction).
- Include the volume pre-flight contract per §2.5.1 (halt-and-report on missing / unusable volume; covered by a unit test).
- Run the 21-cell sweep per §3 (and only that 21-cell sweep — F5-d / F5-e deferred).
- Test the hypothesis chain per §4 against the eval harness per §5.
- Include calibration diagnostics per §6 (diagnostic-only).
- Apply the verdict tree per §7 — H2 PASS alone is **NOT** ADOPT_CANDIDATE.
- Honour all six mandatory clauses per §9 verbatim in `eval_report.md`.
- Honour the strict-causal rule per §2.7 with explicit bar-t lookahead unit tests for F5-a, F5-b, and F5-c.
- NOT relax NG#10 / NG#11; NOT modify γ closure; NOT touch stage25_0a / 0b / 0c / 0d / 0e artifacts.
- **Frame F5 as the LAST feature-axis attempt within Phase 25** in `eval_report.md` mandatory clause #6, and use the softened stop-condition wording per §8 ("strongly supports definitive feature-axis stop … but the user still chooses").
