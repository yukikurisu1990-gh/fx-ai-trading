# Phase 27 — R7-C Scope Amendment

**Type**: doc-only scope amendment
**Status**: tier-promotes R7-C *requires SEPARATE Phase 27 scope-amendment PR* → *admissible at 27.0f-α design memo*; does NOT trigger any 27.0f-α / 27.0f-β implementation
**Branch**: `research/phase27-scope-amendment-r7-c`
**Base**: master @ e94337f (post-PR #329 / post-27.0e routing review merge)
**Pattern**: analogous to PR #311 (Phase 26 R6-new-A feature widening) and PR #323 (Phase 27 S-E scope amendment)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal Phase 27 R7-C scope amendment. On merge, R7-C moves from kickoff §8 / PR #323 §7 clause 6 tier "R7-C requires a SEPARATE Phase 27 scope-amendment PR" → "admissible at sub-phase 27.0f-α design memo". It does NOT by itself authorise the 27.0f-α S-E + R7-C design memo or the 27.0f-β eval implementation. Each subsequent sub-phase PR requires its own separate later user instruction.*

Same approval-then-defer pattern as PR #311 (Phase 26 R6-new feature widening), PR #316 (Phase 27 kickoff), PR #320 (Phase 27.0c-α S-D design memo), PR #323 (Phase 27 S-E scope amendment), PR #324 (Phase 27.0d-α S-E design memo), PR #327 (Phase 27.0e-α S-E quantile trim design memo).

This PR is doc-only. No `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md` is touched.

---

## 1. Why R-C exists

The post-27.0e routing review (PR #329, master e94337f) §4 enumerated 9 routing options after the 4-evidence-point Channel B picture + 27.0e Channel C surprise (R-T2 trim made Sharpe WORSE, not better — preserving Spearman +0.4381 while Sharpe dropped from -0.483 at q=40 to -0.767 at q=10). The user explicitly selected **R-C — R7-C regime/context feature widening** as the next move, with the routing rationale (verbatim):

> *R-T2で、単にtrade countを絞るだけではダメだと分かった。S-Eのtop-tail自体がadversarialで、危険なregimeを高く評価している可能性が高い。R-Cは、regime/context featuresによって high-vol high-EV と high-vol high-cost を分離できるかを直接検証できる。R-Bも候補だが、H-B6の本質がregime confoundならR-Cの方が直接的。R-T1は安いが、selection ruleで避けるだけで、regressorがなぜ危険top-tailを高く評価するかは分からない。R-T3はscope amendmentが必要で、pair/concentration formalisationに寄りすぎる。R-E soft closeは保守的だが、S-EでH1m signalが出た以上、まだ閉じるには少し早い。*

R-C is the **cleanest direct test of H-B6** from #329 §3.2:

> *The S-E regressor's monotonic Spearman ranking is approximately correct in the bulk but **non-monotonically inverted at the top tail**. The most-confident predictions correspond to feature configurations — high ATR, wide spread, specific pair/direction patterns — where the regressor over-predicts realised PnL because bid/ask executable cost in those high-vol regimes structurally dominates the predicted edge.*

R7-C adds spread / volume regime features that should let the regressor distinguish "high-vol high-EV" from "high-vol high-cost" rows. **Targeted predictions**:
- If R-C produces H2 PASS at some 27.0f-β cell → strong H-B6 support; routing pivots toward PROMISING_BUT_NEEDS_OOS branch
- If R-C also produces REJECT → H-B6 partially falsified; bottleneck is even deeper; route to R-T1 / R-B / R-T3 / R-E
- Implicit test of H-B2 (R7-A too narrow): R-C adds 3 new features; if monetisation recovers, R7-A's narrowness was load-bearing

**This scope amendment is narrow**: admits R7-C feature family. Does NOT specify cell structure / S-E vs S-D / quantile family choice — those live in the subsequent 27.0f-α design memo.

---

## 2. What R7-C IS / what R7-C is NOT

| R7-C IS | R7-C is NOT |
|---|---|
| Closed F5 allowlist: spread regime + volume regime + 1 joint interaction (3 features total; §3.1) | All of Phase 25 F5 (which had F5-a / F5-b / F5-c / F5-d / F5-e sub-extensions) |
| **Additive to R7-A** — R7-A 4 features remain FIXED; R7-C adds 3 more (R7-A + R7-C = 7 features total) | A replacement of R7-A |
| Source: Phase 25.0f-α design memo (PR #295) §2.4 / §2.5 / §2.6 / §2.7 construction rules inherited verbatim | A new feature engineering effort |
| Sub-phase numbered **27.0f** (next sequential letter after 27.0e) | Sub-phase 27.0g / 27.0h |
| **Causally constructed** (shift(1) before rolling, per Phase 25.0f-α §2.7 binding); no target-aware terms; no future info | Target-aware or future-info |
| Computable from existing `path_quality_dataset.parquet` (spread column) + M1 BA volume column — no new data extension required | Requiring new data sources / pair extensions / tick-level data |
| Pre-flight HALT if M1 volume missing/corrupt (Phase 25.0f-α §2.5.1 binding inherited) | Silent fallback on missing volume |
| Direct test of H-B6 (regime confound in regressor confidence) | A second-order ablation; this is the targeted test |

---

## 3. R7-C feature family definition (closed allowlist; D-Y1 + D-Y2 + D-Y10)

### 3.1 Closed allowlist — Option A (minimal; 3 features additive)

The R7-C closed allowlist for 27.0f-α / 27.0f-β is:

| Feature | Construction (verbatim from Phase 25.0f-α §2.4 / §2.5 / §2.6) | Causal |
|---|---|---|
| **`f5a_spread_z_50`** | `(spread − rolling_mean(spread, lb=50)) / rolling_std(spread, lb=50)`; source = M5 mid-spread from `path_quality_dataset.parquet`; per-pair time series keyed by `signal_ts`; spread series `shift(1)` BEFORE rolling | shift(1) ✓ |
| **`f5b_volume_z_50`** | `(volume − rolling_mean(volume, lb=50)) / rolling_std(volume, lb=50)`; source = M5-aggregated volume (right-closed / right-labeled aggregation of M1 BA volume per Phase 25.0f-α §2.5); per-pair time series; volume series `shift(1)` BEFORE rolling | shift(1) ✓ |
| **`f5c_high_spread_low_vol_50`** | bool `(f5a_spread_z_50 > 1.0) AND (f5b_volume_z_50 < -1.0)`; the illiquid-stress flag (high spread + low volume = executable cost dominates) | shift(1) ✓ (inputs are shift(1)) |

**Total: 3 features. R7-A + R7-C = 7 features total.**

### 3.2 Rationale for Option A

- **Direct H-B6 test**: each feature targets a distinct regime axis (spread / volume / joint illiquid-stress). The illiquid-stress flag directly captures H-B6's predicted adversarial regime
- **Lookback 50 = neutral middle**: Phase 25.0f-α admitted lookbacks ∈ {20, 50, 100}; 50 avoids both the noise floor (lb=20) and slow-drift saturation (lb=100); a single representative lookback per regime axis
- **Minimal additive widening**: 3 new features keep total feature count at 7 (vs 4 in R7-A); manageable model capacity; lower val-cutoff overfit risk
- **Avoids Phase 25 reopening**: R7-C is a closed subset of F5, NOT the full F5 family. F5-d (tick-level micro-imbalance), F5-e (pair-level liquidity rank), broader F5-c interactions, and other lookbacks are deferred (per Phase 25.0f-α §2.3 and §9 below)
- **Preserves interpretability**: 3 features with clear semantic meaning (spread regime / volume regime / illiquid-stress) allow targeted analysis if R-C produces a PROMISING outcome

### 3.3 Options NOT adopted (D-Y10)

- **Option B** (6 features: 3 spread regime lookbacks + 3 volume regime lookbacks): rejected by default; higher model capacity and overfit risk for marginal H-B6 information gain
- **Option C** (all F5-a + F5-b + F5-c per Phase 25.0f-α): rejected; approaches "Phase 25 reopening" territory; not admissible under current clause 6
- **Broader F5-c interaction set** (e.g., `f5c_spread_x_volume_50`, `f5c_high_spread_high_vol_50`, `f5c_spread_regime_x_vol_regime_50`): single illiquid-stress flag only in this scope; broader F5-c interactions admissible only via future scope amendment if R-C is REJECT

### 3.4 Pre-flight contract (inherited from Phase 25.0f-α §2.5.1)

The 27.0f-β implementation MUST, before fitting any model:

1. Verify `volume` column is present in every M1 BA jsonl row loaded
2. Verify non-null fraction ≥ 0.99 per pair across the eval span
3. Verify M1 → M5 aggregation produces a strictly non-decreasing index aligned to 25.0a-β bar boundaries
4. Verify volume values are non-negative

If any check fails: **HALT the eval with a non-zero exit code and an explicit error report**; do NOT silently fall back to F5-a-only. This binding is inherited from Phase 25.0f-α §2.5.1 verbatim.

---

## 4. Inheritance bindings (FIXED for 27.0f-α / 27.0f-β)

The following are FIXED for 27.0f and CANNOT be relaxed by this scope amendment:

| Binding | Source | Status |
|---|---|---|
| R7-A 4-feature allowlist (`pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`) | PR #311 / #313 / #323 | FIXED — R7-C is **ADDITIVE**; R7-A subset preserved unchanged |
| 25.0a-β path-quality dataset | inherited | FIXED — source for spread column |
| M1 BA jsonl `volume` column | Phase 25.0f-α §2.5 | FIXED — pre-flight HALT contract inherited |
| F5 causal construction rules (§2.4 / §2.5 / §2.6 / §2.7 from PR #295) | inherited verbatim | FIXED |
| 70/15/15 chronological split | inherited | FIXED |
| Triple-barrier inputs (K_FAV=1.5·ATR, K_ADV=1.0·ATR, H_M1=60) | inherited | FIXED |
| `_compute_realised_barrier_pnl` (bid/ask executable harness) | D-1 binding | FIXED — both formal verdict PnL and S-E regression target (if S-E used in 27.0f cells) |
| LightGBMRegressor + Huber (α=0.9) config (for S-E + R7-C cells if 27.0f-α picks S-E) | 27.0d-α §4 | FIXED |
| LightGBM multiclass head config (for C-sb-baseline replica) | 26.0d / 27.0d | FIXED |
| Verdict ladder H1/H2/H3/H4 thresholds | inherited | FIXED |
| Quantile-of-val family policy (per-cell per 27.0e-α D-X4 if S-E cells used; default {5, 10, 20, 30, 40} for C-sb-baseline) | inherited / 27.0e | FIXED |
| Validation-only cutoff selection; test touched once | inherited | FIXED |
| Cross-cell aggregation (26.0c-α §7.2) | inherited | FIXED |
| ADOPT_CANDIDATE 8-gate A0–A5 SEPARATE-PR wall | inherited | FIXED |
| BaselineMismatchError tolerances (n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip) | 27.0b-α §12.2 → 27.0d-α §7.3 → 27.0e-α §7.1 | FIXED — inherited verbatim |
| D10 2-artifact form (one regressor + one multiclass head; each fit ONCE on full train) | 27.0d-α §7.5 | FIXED |
| 2-layer selection-overfit guard (fitting layer train-only; selection layer val-only; test touched once) | 27.0d-α §13 | FIXED |
| Clause 2 diagnostic-only binding | kickoff §8 / PR #323 | **load-bearing; unchanged** |
| Phase 22 frozen-OOS contract | inherited | FIXED |
| Production v9 20-pair tip 79ed1e8 | inherited | UNTOUCHED |

---

## 5. Selection-overfit handling framework (high-level)

R7-C adds 3 features to R7-A's 4 features. The 2-layer selection-overfit guard (per 27.0d-α §13) applies unchanged:

> *S-E's (or S-D's, depending on 27.0f-α cell choice) trainable artifact(s) are ALL fit on train-only data. Val data is used ONLY for cutoff selection (quantile-of-val q\* per cell, with per-cell quantile family per 27.0e-α). Test data is touched exactly once at the val-selected (cell\*, q\*). 5-fold OOF (if computed) is DIAGNOSTIC-ONLY. Any deviation is a NG#10 violation.*

The 3 NEW R7-C features increase feature-space dimensionality from 4 → 7. The selection-overfit risk profile is preserved provided val-cutoff selection is held to the inherited rule (max val_sharpe across per-cell quantile family). 27.0f-α design memo will reaffirm this binding.

---

## 6. Clause 6 update — R7-C tier promotion (verbatim wording from this PR forward)

The PR #323 §7 / PR #324 §9 / PR #327 §9 versions of clause 6 stated:

> *R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR ... R7-B / R7-C remain admissible only after their own separate scope amendments.*

After this PR merges, the 27.0f-α design memo + 27.0f-β eval (and all subsequent Phase 27 PRs referencing clause 6) must re-cite the R7-C sentence verbatim as the NEW canonical wording:

> *R7-C (Phase 25 F5 regime/context closed allowlist) was promoted from "requires SEPARATE Phase 27 scope-amendment PR" to "admissible at 27.0f-α design memo" via Phase 27 R7-C scope-amendment PR `<this-PR>`. The R7-C closed allowlist is `[f5a_spread_z_50, f5b_volume_z_50, f5c_high_spread_low_vol_50]` (3 features; additive to R7-A; constructed per Phase 25.0f-α §2.4 / §2.5 / §2.6 causal rules; pre-flight HALT if M1 volume missing/corrupt). R7-B remains admissible only after its own separate scope amendment. R7-D and R7-Other remain NOT admissible.*

Other clause 6 sentences (Phase 27 axes; R7-A admissibility; S-A / S-B / S-C admissibility; S-D 27.0c-β tier promotion via PR #320; S-E 27.0d-β tier promotion via PR #323; S-Other / R7-D / R7-Other not admissible; Phase 26 deferred items) **preserved verbatim**.

This is the **canonical source-of-truth for clause 6 from this PR forward**. The 27.0f-α / 27.0f-β / any subsequent Phase 27 PRs re-quote it verbatim.

---

## 7. Sub-phase naming (D-Y4)

The next sub-phase after 27.0e is **27.0f**. R-C will be sub-phase 27.0f:

- **27.0f-α**: design memo. Decides:
  - Cell structure (S-E + R7-C cell composition; whether to include S-D cells; C-sb-baseline replica preservation)
  - Quantile family choice (inherited 27.0e trimmed {5, 7.5, 10}? Inherited 27.0d full {5, 10, 20, 30, 40}? Or a NEW choice?)
  - BaselineMismatchError tolerances (inherited; specifics deferred to design memo)
  - 5-fold OOF DIAGNOSTIC-ONLY policy
  - Sanity probe extensions (likely items: F5 feature distribution disclosure, R7-C feature importance)
- **27.0f-β**: eval implementation (per design memo)
- post-27.0f routing review (per established pattern after each sub-phase β)

Kickoff §7's enumeration is informational; actual sub-phase letters are allocated by user routing decisions, NOT by kickoff §7 pre-enumeration.

---

## 8. ADOPT_CANDIDATE / production / NG / γ / X-v2 / Phase 22 preservation

This PR does **NOT** touch any of:

- γ closure (PR #279) — unmodified
- X-v2 OOS gating — remains required for any production deployment
- Production v9 20-pair (Phase 9.12 closure tip 79ed1e8) — untouched
- NG#10 / NG#11 — not relaxed
- Phase 22 frozen-OOS contract — required for any ADOPT_CANDIDATE → production transition
- ADOPT_CANDIDATE 8-gate A0–A5 harness — required in a SEPARATE PR; cannot be minted in 27.0f-β

R7-C sub-phase β evals (27.0f-β) can produce at best **PROMISING_BUT_NEEDS_OOS** (H2 PASS branch). ADOPT_CANDIDATE requires the full 8-gate A0–A5 harness in a SEPARATE PR, same as Phase 26 family.

No production change of any kind is associated with this scope amendment.

---

## 9. What this PR will NOT do

- ❌ Authorise 27.0f-α S-E + R7-C design memo (separate later user instruction)
- ❌ Authorise 27.0f-β eval implementation
- ❌ Specify cell structure for 27.0f (S-E vs S-D vs both; quantile family choice; etc. — 27.0f-α decides)
- ❌ Specify OOF protocol / calibration policy / BaselineMismatchError tolerance adjustment (27.0f-α decides if any deviation from inherited)
- ❌ Authorise R7-B (still requires its own SEPARATE scope-amendment PR)
- ❌ Authorise R7-D / R7-Other (NOT admissible under any Phase 27 scope amendment currently on the table)
- ❌ Authorise broader F5-c interaction features beyond `f5c_high_spread_low_vol_50` (per §3.3; broader F5-c admissible only via future scope amendment if R-C is REJECT)
- ❌ Authorise F5-d (tick-level micro-imbalance) — explicitly deferred per Phase 25.0f-α §2.3
- ❌ Authorise F5-e (pair-level liquidity rank) — overlaps F3; deferred per Phase 25.0f-α §2.3
- ❌ Authorise R-T1 (S-E selection redesign — separate route from #329; would need its own design memo)
- ❌ Authorise R-T3 (pair-concentration formalisation — requires clause-2 modification scope amendment)
- ❌ Authorise alternative S-E regression-variant cells (MSE / L1 / Tweedie — deferred per 27.0d-α §7.6)
- ❌ Modify Phase 27 scope per kickoff §8 / PR #323 / PR #324 / PR #327 clause 6 (other than tier-promoting R7-C — the explicit purpose of this PR)
- ❌ Modify clause 2 diagnostic-only binding (load-bearing for R-T1 / R-T3 framings; not touched here)
- ❌ Reopen Phase 25 (R7-C is a closed subset of F5, NOT a Phase 25 reopening)
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b / 27.0c / 27.0d / 27.0e / routing reviews / scope amendments)
- ❌ Relax the ADOPT_CANDIDATE 8-gate A0-A5 wall
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279) / X-v2 OOS gating / Phase 22 frozen-OOS contract / production v9 20-pair tip 79ed1e8
- ❌ Pre-approve any production deployment under any 27.0f-β outcome
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md`
- ❌ Auto-route to 27.0f-α after merge

---

## 10. PR chain reference

```
Phase 27 R7-C series (R-C route from PR #329):
  THIS PR (Phase 27 R7-C scope amendment, doc-only)
  → 27.0f-α design memo PR (separate later user instruction)
  → 27.0f-β eval PR (separate later user instruction)
  → post-27.0f routing review PR (separate later user instruction)
  → optionally: ADOPT_CANDIDATE → A0-A5 PR (separate; requires H2 PASS first)
  → eventual Phase 27 closure memo (R5 pattern) OR ADOPT_CANDIDATE → production
    (the latter only after X-v2 OOS gating + Phase 22 frozen-OOS contract)
```

R-B / R-T1 / R-T3 / R-E remain open routing options NOT closed by this PR. Future routing reviews (post-27.0f) may select any of them.

---

## 11. Sign-off

R7-C moves from kickoff §8 / PR #323 §7 clause 6 tier *requires SEPARATE Phase 27 scope-amendment PR* → *admissible at sub-phase 27.0f-α design memo* on merge. The closed allowlist is the 3-feature minimal Option A: `[f5a_spread_z_50, f5b_volume_z_50, f5c_high_spread_low_vol_50]`. The 27.0f-α design memo PR is triggered by a separate later user instruction. No auto-route.

**This PR stops here.**
