# Phase 27 — S-E Scope Amendment

**Type**: doc-only scope amendment
**Status**: tier-promotes S-E *requires scope amendment* → *admissible at 27.0d-α design memo*; does NOT trigger any 27.0d-α / 27.0d-β implementation
**Branch**: `research/phase27-scope-amendment-s-e`
**Base**: master @ 2bfd948 (post-PR #322 / post-27.0c routing review merge)
**Pattern**: analogous to PR #311 (Phase 26 R6-new feature widening scope amendment) under Phase 26
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal Phase 27 S-E scope amendment. On merge, S-E moves from kickoff §5 / clause 6 tier "requires a SEPARATE scope-amendment PR (model-class change)" → "admissible at sub-phase 27.0d-α design memo". It does NOT by itself authorise the 27.0d-α S-E design memo or the 27.0d-β S-E eval implementation. Each subsequent sub-phase PR requires its own separate later user instruction.*

Same approval-then-defer pattern as PR #311 (Phase 26 R6-new feature widening), #316 (Phase 27 kickoff), #320 (Phase 27.0c-α design memo).

This PR is doc-only. No `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md` is touched.

---

## 1. Why S-E exists

The post-27.0c routing review (PR #322, master 2bfd948) §4 enumerated 6 routing options after the two-evidence-point Channel B wrong-direction picture (27.0b-β S-C TIME penalty + 27.0c-β S-D calibrated EV both REJECT with the same Spearman↑ / Sharpe↓ pattern under R7-A). The user explicitly selected **R-S-E — S-E regression-on-realised-PnL** as the next move, with the routing rationale (verbatim):

> *27.0bと27.0cで、classification-head由来のscore加工は2回連続で wrong-direction pattern を示した。Spearmanは改善するがSharpeが悪化するため、classification probability head自体が realised PnL monetisation とズレている可能性が高い。S-D calibrated EVでも per-class scalar weighting ではズレを修正できなかった。したがって次は classification head を離れ、realised PnL を直接targetにする S-E regression-on-realised-PnL が最も直接的な検証になる。*

R-S-E targets the **H-B4 hypothesis** from #322 §3.4 (label/PnL coupling miscalibration not fixable by per-class scalar weights) directly. It implicitly also tests **H-B3** (structural mis-alignment under R7-A from #322 §3.1):
- If S-E aligns under R7-A (realised PnL improves directionally, not just Spearman) → H-B4 is supported and H-B3 is **falsified** as R7-A-conditioned
- If S-E also fails → H-B3 is **reinforced**; routing pivots toward R-B / R-C / R-D / R-E

**This scope amendment is narrow**: it admits S-E (regression on realised PnL) to formal Phase 27 evaluation. It does NOT specify model-class details, OOF protocol, calibration policy, cell structure, or BaselineMismatchError tolerances — those live in the subsequent 27.0d-α design memo.

---

## 2. What S-E IS / what it is NOT

| S-E IS | S-E is NOT |
|---|---|
| Model-class change: multiclass classifier on {TP, SL, TIME} → **regression on realised barrier PnL per row** | A relabelling of class targets (Phase 26 L-class space is closed; not reopened by this PR) |
| Direct target = inherited `_compute_realised_barrier_pnl` (D-1 binding; bid/ask executable) | Mid-to-mid PnL regression (D-1 binding remains; mid-to-mid is diagnostic-only) |
| Score at val/test time = predicted realised PnL per row | A per-class scoring scheme — the whole point is bypassing the class-prob × class-scalar factorisation that failed under S-D in 27.0c |
| Sub-phase named **27.0d** (next sequential letter after 27.0c) | Sub-phase 27.0e or 27.0f (kickoff §7's "27.0f = S-E" enumeration was candidate-only and is superseded) |
| Validation-only cutoff selection / test touched once / verdict ladder inherited unchanged | A relaxation of any verdict / NG / γ / X-v2 / Phase 22 binding |
| Comparison against 27.0b C-alpha0 / 26.0d R6-new-A / 26.0c L-1 baselines preserved | Free of inheritance-chain check (BaselineMismatchError pattern carries forward — specifics in 27.0d-α) |
| Feature set FIXED at R7-A (`pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`) | Combined with R7-B / R7-C in any joint cell (each remains behind its own scope amendment) |

---

## 3. Inheritance bindings (carried forward unchanged)

The following are FIXED for 27.0d-α / 27.0d-β and CANNOT be relaxed by this scope amendment:

| Binding | Source | 27.0d status |
|---|---|---|
| R7-A 4-feature allowlist | PR #311 / #313 | FIXED |
| 25.0a-β path-quality dataset | inherited | FIXED |
| 70/15/15 chronological split | inherited | FIXED |
| Triple-barrier inputs (K_FAV=1.5·ATR, K_ADV=1.0·ATR, H_M1=60) | inherited | FIXED |
| `_compute_realised_barrier_pnl` (bid/ask executable harness) | D-1 binding | FIXED — also the regression target |
| Verdict ladder H1-weak (>0.05) / H1-meaningful (≥0.10) / H2 (Sharpe ≥0.082 AND ann_pnl ≥180) / H3 (>−0.192) / H4 (≥0) | inherited | FIXED |
| Quantile-of-val 5/10/20/30/40 % cutoff family | inherited | FIXED |
| Validation-only cutoff selection / test touched once | inherited | FIXED |
| Cross-cell aggregation (26.0c-α §7.2) | inherited | FIXED |
| ADOPT_CANDIDATE 8-gate A0–A5 SEPARATE-PR wall | inherited | FIXED |
| Pair-concentration diagnostic + per-pair Sharpe contribution diagnostic | inherited | FIXED |
| L-1 ternary class encoding (TP/SL/TIME) | inherited | **PRESERVED for sanity probe + label diagnostics; NOT used as regression target** |
| Phase 22 frozen-OOS contract | inherited | FIXED |
| Production v9 20-pair tip 79ed1e8 | inherited | UNTOUCHED |

---

## 4. S-E target definition (high-level only; specifics deferred to 27.0d-α)

Authoritative form:

```
target(row) = _compute_realised_barrier_pnl(row)   # inherited bid/ask executable
```

Every train row's regression target is its realised barrier PnL under the inherited bid/ask executable harness — the **same value** used by the formal verdict harness across all prior Phase 26 / Phase 27 sub-phases. There is no new harness, no new target semantics, no mid-to-mid relaxation.

Score at val/test scoring time:

```
S-E(row) = regressor.predict(row)   # predicted realised PnL per row
```

Selection via quantile-of-val on `S-E(row)`, identically to the S-A / S-B / S-C / S-D inherited pattern.

The 27.0d-α design memo will specify:

- Concrete model class (LightGBMRegressor is the proposed default per D-V2; alternatives within the regression family remain admissible at design-memo discretion)
- Loss function (MSE / Huber / etc.)
- Hyperparameters
- OOF protocol (5-fold analogous to S-D, or alternative)
- Calibration policy (if any post-prediction calibration is needed)
- Cell structure (whether to include a S-B replica baseline-check cell; deferred per D-V5)
- BaselineMismatchError tolerances (if a baseline-replica cell is included; deferred per D-V7)
- Sanity probe extensions

None of the above is fixed by this scope amendment.

---

## 5. Model-class change (multiclass classification → regression for S-E only)

This is the *substantive scope change* in this PR:

- 27.0b / 27.0c bound `build_pipeline_lightgbm_multiclass_widened` as the FIXED model class
- 27.0d permits a **regression** model class (LightGBMRegressor default; alternatives within the regression family at design-memo discretion) for the score head **ONLY in S-E cells**
- The multiclass head is **NOT removed** from Phase 27 admissibility — S-A / S-B / S-C / S-D cells remain bound to the multiclass head; only S-E is permitted to use regression
- Per kickoff §5, this is the model-class change that explicitly required scope amendment; PR #316 §8 / clause 6 stated *"S-E (regression-on-realised-PnL) requires a SEPARATE scope-amendment PR (model-class change)"*

This scope amendment does **NOT** authorise:

- Other model-class changes for non-S-E score objectives (neural networks, quantile regression, ordinal regression, learn-to-rank for S-A/S-B/S-C/S-D — these remain bound to the FIXED multiclass head)
- S-Other score objectives (quantile regression / ordinal score / learn-to-rank — these remain NOT admissible per kickoff §8 clause 6)
- R7-D or R7-Other feature families (each remains NOT admissible)

---

## 6. Selection-overfit handling framework (high-level)

S-E presents the same selection-overfit risk profile as S-D — the regression head fits realised PnL per row on train, so val cannot be used to fit either the head or any downstream calibration. The high-level binding (analogous to 27.0c-α §13 verbatim, adapted to single-artifact form):

> *S-E's trainable artifact(s) are ALL fit on train-only data. Val data is used ONLY for cutoff selection (quantile-of-val q\* per cell). Test data is touched exactly once at the val-selected (cell\*, q\*). Any deviation is a NG#10 violation.*

Specifics (OOF protocol, post-prediction calibration if any, fold seed, OOF-vs-full-train divergence flags) live in the 27.0d-α design memo. This scope amendment binds only the high-level three-layer separation:

1. Estimator-fitting layer (train-only)
2. Calibration layer (if applicable; train-internal OOF only)
3. Selection layer (val-only quantile-of-val; test touched once)

---

## 7. Clause 6 update — S-E tier promotion (verbatim wording from this PR forward)

The 27.0c-α / 27.0c-β versions of clause 6 stated:

> *S-E (regression-on-realised-PnL) requires a SEPARATE scope-amendment PR (model-class change).*

After this PR merges, the 27.0d-α design memo + 27.0d-β eval (and all subsequent Phase 27 PRs referencing clause 6) must re-cite the S-E sentence as follows (NEW canonical wording):

> *S-E (regression-on-realised-PnL) was promoted from "requires scope amendment" to "admissible at 27.0d-α design memo" via Phase 27 S-E scope-amendment PR `<this-PR>`. S-E uses realised barrier PnL (inherited bid/ask executable, D-1 binding) as the per-row regression target under the FIXED R7-A feature family; LightGBM regression is the default model class but the 27.0d-α design memo may specify alternatives within the regression family. S-Other (quantile regression / ordinal / learn-to-rank) remains NOT admissible. R7-D and R7-Other remain NOT admissible. R7-B / R7-C remain admissible only after their own separate scope amendments.*

Other clause 6 sentences (Phase 27 scope axes; R7-A admissibility; R7-B / R7-C scope-amendment requirement; S-A / S-B / S-C formal admissibility; S-D's 27.0c-α tier promotion; Phase 26 deferred-not-foreclosed items) are PRESERVED VERBATIM.

This is the **canonical source-of-truth for clause 6 from this PR forward**. The 27.0d-α / 27.0d-β / any subsequent Phase 27 PRs re-quote it verbatim.

---

## 8. Phase 27 kickoff §7 sub-phase enumeration update (informational)

Kickoff §7 listed `27.0f` as the candidate slot for S-E. The user has selected sub-phases out of kickoff §7 order:
- Kickoff §7 listed 27.0a (replication) / 27.0b (S-C) / 27.0c (model-class or calibration under S-A/S-B) / 27.0d (R7-B) / 27.0e (R7-C) / 27.0f (S-E)
- Actual sequence: 27.0b (S-C, PR #318) → 27.0c (S-D, PR #321 — kickoff §7 had not pre-named this sub-phase since S-D was tier-promoted via PR #320 design memo) → 27.0d (S-E, this scope amendment + subsequent PRs)

Per the routing review pattern (PR #319 / #322), the actual sub-phase ordering is determined by user routing decisions, NOT by kickoff §7 enumeration. **Kickoff §7 is informational / candidate-only and is not binding.**

This scope amendment names the S-E sub-phase **27.0d** (next sequential letter after 27.0c). Kickoff §7's "27.0f = S-E" entry becomes informational / superseded. Future sub-phase letters (27.0e / 27.0f / ...) will be allocated by future routing decisions; not by kickoff §7 pre-enumeration.

---

## 9. ADOPT_CANDIDATE / production / NG / γ / X-v2 / Phase 22 preservation

This PR does **not** touch any of:

- γ closure (PR #279) — unmodified
- X-v2 OOS gating — remains required for any production deployment
- Production v9 20-pair (Phase 9.12 closure tip 79ed1e8) — untouched
- NG#10 / NG#11 — not relaxed
- Phase 22 frozen-OOS contract — required for any ADOPT_CANDIDATE → production transition
- ADOPT_CANDIDATE 8-gate A0–A5 harness — required in a SEPARATE PR; cannot be minted in 27.0d-β

S-E sub-phase β evals (27.0d-β) can produce at best **PROMISING_BUT_NEEDS_OOS** (H2 PASS branch). ADOPT_CANDIDATE requires the full 8-gate A0–A5 harness in a SEPARATE PR, same as Phase 26 family.

No production change of any kind is associated with this scope amendment.

---

## 10. What this PR will NOT do

- ❌ Authorise 27.0d-α S-E design memo (separate later user instruction)
- ❌ Authorise 27.0d-β S-E eval implementation
- ❌ Specify concrete model-class details (LightGBMRegressor config / loss / hyperparameters — 27.0d-α decides)
- ❌ Specify OOF protocol, fold seed, or post-prediction calibration policy (27.0d-α decides)
- ❌ Specify cell structure — whether to include an S-B baseline-replica cell (27.0d-α decides per D-V5)
- ❌ Specify BaselineMismatchError tolerances (27.0d-α decides per D-V7)
- ❌ Authorise S-Other (quantile regression / ordinal / learn-to-rank) — remains NOT admissible per kickoff §8
- ❌ Authorise R7-B / R7-C (each remains behind their own scope amendments)
- ❌ Authorise R7-D / R7-Other (NOT admissible per kickoff §8)
- ❌ Authorise model-class changes for non-S-E score objectives (S-A / S-B / S-C / S-D remain bound to the multiclass head)
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279) / X-v2 OOS gating / Phase 22 frozen-OOS contract / v9 20-pair production tip 79ed1e8
- ❌ Pre-approve any production deployment under any 27.0d-β outcome
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / 27.0b / 27.0c / post-27.0b routing / post-27.0c routing)
- ❌ Reopen Phase 26 L-class label-target redesign space
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md`
- ❌ Auto-route to 27.0d-α after merge

---

## 11. PR chain reference

```
Phase 27 S-E series (R-S-E route from PR #322 / master 2bfd948):
  THIS PR (Phase 27 S-E scope amendment, doc-only)
  → 27.0d-α S-E design memo PR (separate later user instruction)
  → 27.0d-β S-E eval PR (separate later user instruction)
  → post-27.0d routing review PR (separate later user instruction)
  → optionally: ADOPT_CANDIDATE → A0-A5 PR (separate; requires H2 PASS first)
  → eventual Phase 27 closure memo (R5 pattern) OR ADOPT_CANDIDATE → production
    (the latter only after X-v2 OOS gating + Phase 22 frozen-OOS contract)
```

R-B / R-C / R-D / R-E remain open routing options NOT closed by this PR. Future routing reviews (post-27.0d) may select any of them.

---

## 12. Sign-off

S-E moves from kickoff §5 / clause 6 tier *requires scope amendment* → *admissible at sub-phase 27.0d-α design memo* on merge. The 27.0d-α design memo PR is triggered by a separate later user instruction. No auto-route.

**This PR stops here.**
