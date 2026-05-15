# Phase 27 — Post-27.0f Routing Review

**Type**: doc-only routing review
**Status**: routes Phase 27 after 27.0f-β S-E + R7-C regime/context eval (PR #332); does NOT initiate any sub-phase
**Branch**: `research/phase27-post-27-0f-routing-review`
**Base**: master @ `ad673b4` (post-PR #332 / Phase 27.0f-β eval merge)
**Pattern**: analogous to PR #319 / #322 / #326 / #329 routing reviews under Phase 27
**Date**: 2026-05-16

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal post-27.0f routing review. It consolidates the **5-eval evidence picture** (27.0b / 27.0c / 27.0d / 27.0e / 27.0f β-evals), captures the substantively new finding that **R7-C regime/context features fail to lift Sharpe** (H-B6 outcome FALSIFIED_R7C_INSUFFICIENT), enumerates **4 routing branches** (R-B feature axis / R-T1 selection-rule redesign / R-T3 concentration formalisation / R-E Phase 27 soft close), and presents a recommendation with two dissents. It does **NOT** by itself authorise any R-B / R-T1 / R-T3 / R-E sub-phase. The next sub-phase choice (or the Phase 28 rebase) requires a separate later user instruction.*

Same approval-then-defer pattern as PR #319 / #322 / #326 / #329.

---

## 1. Executive summary — post-27.0f evidence picture

Phase 27 now has **five substantive sub-phase β-evals** since kickoff (PR #316), and the val-selected cell is **the inherited C-sb-baseline in every one**:

| sub-phase | Channel | Intervention | val-selected cell | H1m result | H-Bx outcome | Verdict |
|---|---|---|---|---|---|---|
| 27.0b-β | B | S-C TIME penalty α grid | C-alpha0 (S-B) | Spearman ≤ +0.023 | — | REJECT |
| 27.0c-β | B | S-D calibrated EV | C-sb-baseline (S-B) | Spearman -0.106 | — | REJECT |
| 27.0d-β | B | S-E regression on realised PnL | C-sb-baseline (S-B) | Spearman +0.438 (C-se cell PASS) | — | REJECT (split) |
| 27.0e-β | C | R-T2 quantile-family trim | C-sb-baseline (S-B) | Spearman preserved | H-B5 PARTIAL_SUPPORT (row 2) | REJECT (split) |
| 27.0f-β | A | R7-C regime/context features (3-feature additive) | C-sb-baseline (S-B) | Spearman preserved | **H-B6 FALSIFIED_R7C_INSUFFICIENT (row 3)** | REJECT (split) |

**Two load-bearing observations** from 27.0f-β:

1. **C-se-rcw ≈ C-se-r7a-replica across all 5 quantiles.** Adding 3 R7-C features (`f5a_spread_z_50`, `f5b_volume_z_50`, `f5c_high_spread_low_vol_50`) on top of R7-A produced a max |Δ Sharpe| of **0.0039** across q ∈ {5, 10, 20, 30, 40}. The regressor extracted essentially zero additional information from the regime axis.
2. **Val-selection picked baseline in every sub-phase.** The score/feature/selection-rule interventions that have been tried so far (S-C / S-D / S-E / R-T2 / R7-C) have **not produced a single cell whose val-Sharpe beats the simple S-B classifier baseline**, so val-selection never surfaced a new candidate. This pattern is the single most informative signal in the 5-eval picture.

**Recommendation (§13)**: **R-E — Phase 27 soft close**, with R-T1 and R-B preserved as dissents (deferred-not-foreclosed). Five sub-phases have systematically exhausted the **score axis (S-C / S-D / S-E)**, the **selection-rule trim axis (R-T2)**, and the **regime-feature axis (R7-C)**. The remaining axes inside Phase 27 (R-T1 selection redesign, R-B feature axis broader than R7-C, R-T3 concentration) either repeat axes already shown to be insufficient at coarse resolution, or require a scope amendment that is heavy relative to their prior P(GO). Phase 28 should rebase on architecture / objective / hierarchy rather than continue to drill the same selection→monetisation seam.

---

## 2. 27.0f-β formal acceptance — verbatim numbers

PR #332 squash-merged at master `ad673b4` (2026-05-16). Formal acceptance from user message (verbatim):

- Verdict = REJECT_NON_DISCRIMINATIVE
- H1_WEAK_FAIL
- H-B6 outcome = FALSIFIED_R7C_INSUFFICIENT, row 3
- no ADOPT_CANDIDATE
- no PROMISING_BUT_NEEDS_OOS

Fix A row-set isolation (approved mid-PR, 2026-05-16):

- R7-C drop applied only to C-se-rcw
- C-se-r7a-replica uses original R7-A-clean row-set
- C-sb-baseline uses original R7-A-clean row-set
- 5 new unit tests added (Group 18, row-set isolation contract)
- 76 total unit tests pass

Inheritance / sanity:

- C-sb-baseline reproduction PASS — n_trades=34,626 exact; Sharpe Δ=+3.55e-05; ann_pnl Δ=-0.022 (all within tolerance)
- C-se-r7a-replica drift vs 27.0d C-se within tolerance, no WARN
- inheritance chain confirmed intact across 5 sub-phases

Linked artifacts (committed at PR #332):

- `artifacts/stage27_0f/eval_report.md` — 25-section formal report
- `scripts/stage27_0f_s_e_r7_c_regime_eval.py` — eval harness
- `tests/unit/test_stage27_0f_s_e_r7_c_regime_eval.py` — 76 tests

---

## 3. Post-27.0f evidence picture — 5-eval table

**Selection rule**: val-selected (cell*, q*) only, one row per sub-phase. 27.0f supplemental row + footnote document the C-se-rcw ≈ C-se-r7a-replica equivalence that drives the H-B6 falsification.

### 3.1 5-eval table (val-selected cells across 27.0b — 27.0f)

| sub-phase | val-selected cell | q* | val Sharpe | val n | test Sharpe | test n | test ann_pnl | test Spearman | Verdict | route taken |
|---|---|---|---|---|---|---|---|---|---|---|
| 27.0b-β | C-alpha0 (S-B; α=0.0) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT | → 27.0c-β |
| 27.0c-β | C-sb-baseline (S-B) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT | → 27.0d-β |
| 27.0d-β | C-sb-baseline (S-B) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT (split) | → 27.0e-β |
| 27.0e-β | C-sb-baseline (S-B) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT (split) | → 27.0f-β |
| **27.0f-β** | **C-sb-baseline (S-B)** | **5** | **-0.1863** | **25,881** | **-0.1732** | **34,626** | **-204,664.4** | **-0.1535** | **REJECT (split)** | **→ THIS routing review** |

**Footnote (load-bearing)**: The val-selected row is **bit-identical** across all five sub-phases because the val-selector chose the inherited `C-sb-baseline` cell (or its equivalent `C-alpha0` at 27.0b) in every sub-phase. None of S-C (TIME penalty) / S-D (calibrated EV) / S-E (regression on realised PnL) / R-T2 (quantile-family trim) / R7-C (regime/context features) produced a val-superior cell. This is the strongest single piece of evidence for §13's primary recommendation.

### 3.2 27.0f supplemental — C-se-rcw vs C-se-r7a-replica (R7-C insufficiency)

The non-baseline cells inside 27.0f-β show that adding R7-C features on top of R7-A delivered **essentially no discriminative or monetisation lift**:

| q* | C-se-rcw test Sharpe | C-se-r7a-replica test Sharpe | Δ Sharpe (rcw − replica) | C-se-rcw test ann_pnl | C-se-r7a-replica test ann_pnl |
|---|---|---|---|---|---|
| 5 | -0.8389 | -0.8418 | +0.0029 | -68,508 | -70,046 |
| 10 | -0.7687 | -0.7667 | -0.0020 | -165,201 | -165,754 |
| 20 | -0.6639 | -0.6641 | +0.0002 | -377,337 | -381,009 |
| 30 | -0.5903 | -0.5906 | +0.0002 | -646,057 | -650,649 |
| 40 | -0.4869 | -0.4831 | -0.0039 | -993,008 | -999,830 |

**max |Δ Sharpe| = 0.0039** (sign-noisy, no systematic improvement). Cell Spearman for C-se-rcw is +0.43794, essentially identical to 27.0d's C-se +0.43813. R7-C did not move the regressor's discriminative power one decimal.

### 3.3 Top-tail audit at q=10 (27.0f §10.3)

Audited regime features on the q=10 top tail relative to the full universe:

| feature | top-tail mean | universe mean | Δ (top-tail − universe) |
|---|---|---|---|
| `f5a_spread_z_50` | -0.250 | +0.003 | -0.253 |
| `f5b_volume_z_50` | +0.030 | +0.192 | -0.162 |
| `f5c_high_spread_low_vol_50` (share) | 2.2 % | 2.6 % | -0.4 % |

The top tail of S-E confidence does correlate with **tighter spread** (lower `f5a`) and slightly elevated volume, but this directional regime signal does **not** translate into a Sharpe lift — the H-B6 falsification.

---

## 4. H-B6 falsification interpretation — three-layer reading

The H-B6 hypothesis (post-27.0e routing review, §3.2) read the 27.0d / 27.0e Sharpe collapse as a *top-tail adversarial-selection / regime-confound* problem: the high-confidence top tail of the regressor's predictions might be over-represented in expensive regimes (wide spread / thin liquidity) that the regressor cannot see because R7-A is too narrow. 27.0f-β's design memo proposed adding R7-C (3 regime features) as the minimal, falsifiable test of that reading.

The result falsifies H-B6 as a *feature-availability* problem, but the falsification needs three layers of interpretation:

### 4.1 Layer 1 — discrimination gap (R7-C did not move discrimination)

Cell Spearman: C-se-rcw +0.43794 vs C-se-r7a-replica +0.43813 vs 27.0d C-se +0.43813. Adding three regime features moved Spearman by less than 0.0002 in absolute value. The regressor either already extracts that information indirectly from R7-A, or the information is not predictive of the target at the bar level the regressor sees. Either way, **R7-C as written is not a marginal information source** for the realised-PnL regression.

### 4.2 Layer 2 — top-tail regime skew is real but small

Top-tail audit (§3.3) confirms the regime axis is **non-orthogonal** to the regressor's confidence ordering — top-tail rows do have tighter spread and elevated volume relative to the universe. So the H-B6 mechanism is **directionally correct** (top tail does live in a slightly different regime). The falsification is that the **magnitude is too small to lift Sharpe** once the regressor reweights its features in light of R7-C.

### 4.3 Layer 3 — the bottleneck is not in the feature surface

Most importantly, the C-sb-baseline cell still wins val-selection. That means even after R7-C was made available, **neither the rcw cell nor the r7a-replica cell produced val Sharpe above the simple S-B classifier at q=5**. The bottleneck is therefore not "regressor cannot see regime" but something deeper:

- the realised-PnL target itself may be too noisy at the per-trade level for confidence rankings to translate into monetisation
- the selection rule (top-quantile on regressor score) may be the wrong selection rule entirely, irrespective of feature surface
- the trade-mechanism itself (per-row barrier PnL with bid/ask execution) may have a hidden adverse-selection cost not captured by R7-A or R7-C

These deeper possibilities are what motivates §6 (R-B), §7 (R-T1), and §9 (R-E) below — and why §13 leans toward closure rather than another single-feature widening.

---

## 5. Hypothesis space update (post-27.0f)

| ID | Original framing | Status after 27.0f | Notes |
|---|---|---|---|
| H-B1 | TIME-label rows distort EV scoring; downweighting via S-C will help | FALSIFIED (27.0b) | α monotonic Spearman↑ Sharpe↓; downweighting hurts monetisation |
| H-B2 | EV-scoring needs calibrated probabilities; S-D will help | FALSIFIED (27.0c) | Calibrated EV slightly worse than raw S-B |
| H-B3 | Direct regression on realised PnL will beat classifier S-B in monetisation | PARTIAL (27.0d) | Spearman PASS (+0.438) but Sharpe FAIL (-0.483); discrimination ≠ monetisation |
| H-B4 | Multi-q widening expands trade count without adverse selection | (folded into H-B3) | Trade-count inflation observed; Sharpe degrades with q |
| H-B5 | Quantile-family trim {5, 7.5, 10} preserves Sharpe by cutting q-budget | PARTIAL_SUPPORT (27.0e row 2) | Trimming preserved Spearman but **worsened** Sharpe further; q-budget is not the binding lever |
| **H-B6** | Top-tail regime confound; R7-C will lift Sharpe back | **FALSIFIED_R7C_INSUFFICIENT (27.0f row 3)** | Regime features available but unused by regressor; max |Δ Sharpe| 0.0039 |
| H-B7 (NEW) | The val-selection rule itself is misspecified (top-quantile on regressor score is the wrong rule) | UNRESOLVED — motivates R-T1 | val-selector picked baseline in all 5 sub-phases |
| H-B8 (NEW) | The feature surface needs *path/microstructure*-class features, not regime-statistic features | UNRESOLVED — motivates R-B | R7-C is regime-statistic axis; not a path axis |
| H-B9 (NEW) | The Phase 27 hypothesis chain has structurally exhausted the selection→monetisation seam at this architecture | UNRESOLVED — motivates R-E | 5 consecutive REJECTs with bit-identical val-selection |

H-B7, H-B8, H-B9 are *not* tested in this memo — they are pre-stated to be tested either inside a future sub-phase (R-T1 / R-B) or implicitly by the act of soft-closing (R-E acknowledges H-B9 without formally validating it).

---

## 6. Routing branch R-B — different feature axis

### 6.1 Definition

Replace or augment the R7-A regressor input with a **different feature class** than R7-C's regime/context statistics. Candidates include path-shape features (e.g., MFE/MAE-style structural features), microstructure features (e.g., recent quote micro-changes), or longer-horizon context features (multi-TF). Strictly closed allowlist, ADDITIVE to R7-A (R7-C remains intact, not replaced).

### 6.2 Mechanism

The top-tail audit (§3.3) confirms the top tail is in a slightly different *regime* than the universe, but R7-C as a regime-statistic axis did not capture the *interaction* between regime and realised-PnL. A path-class or microstructure-class axis might encode a different sufficient statistic that does interact.

### 6.3 Falsifiable hypothesis (H-C1)

> Pre-state: adding closed-allowlist non-regime features to R7-A will lift C-se-rcw's val Sharpe above C-sb-baseline at q ≤ 20 by more than +0.05 absolute, OR else the H-C1 reading is falsified.

### 6.4 Implementation cost

- ~1.0 sub-phase (~3-4 days) for a 3-feature closed allowlist with shift(1)-before-rolling causality and SanityProbe coverage
- New scope-amendment doc (separate PR; analogous to `phase27_scope_amendment_r7_c.md`) — required because R7-A subset is closed
- 3-cell structure inherits from 27.0f directly; minimal new harness work
- ~25-section eval_report.md and ~70 unit tests by inheritance

### 6.5 Risk surface

- **Blast radius**: low — additive to R7-A; production v9 20-pair untouched; harness changes confined to one new sub-phase script
- **Rollback**: trivial — sub-phase eval lives entirely in `scripts/stage27_0g_*` and `artifacts/stage27_0g/`
- **前提崩しの可能性**: R7-A closed-allowlist contract requires a scope amendment first; user must approve the new feature class explicitly. NG#10 / NG#11 not relaxed.

### 6.6 Prior P(GO)

**15-25 %.**

Reasoning: 27.0d showed Spearman is achievable, but Sharpe collapsed even with the right discriminative signal. 27.0f showed adding a regime axis does not fix Sharpe. A different feature axis might fix it, but **the fact that C-sb-baseline still wins val-selection across 5 sub-phases means the feature-surface narrative may be the wrong frame entirely**. Adding more features without changing the selection rule, target, or model class has a relatively low prior of breaking the pattern. R-B is preserved as a dissent (§13) precisely because the prior is not zero — R-T1 dissenter argues R-B prior is overstated; R-E primary argues R-B prior is overstated.

### 6.7 Open issues / preconditions

- Which feature class? Path-shape, microstructure, or multi-TF context all admissible; user must pre-state. The choice itself is load-bearing for the prior.
- Scope amendment doc required before any implementation
- 5-eval evidence picture suggests the cost-benefit is unfavorable; this PR does not select R-B but does not foreclose it

---

## 7. Routing branch R-T1 — selection-rule redesign

### 7.1 Definition

Replace the top-quantile-on-regressor-score selection rule with a different selection rule: e.g., **absolute-threshold** ("trade only if `score > c`"), **middle-bulk** ("trade quantile 40-60 %, avoid both tails"), **per-pair calibrated cutoff**, or **ranked-cutoff** ("trade top-K per bar"). Strictly does not require new features.

### 7.2 Mechanism

27.0e R-T2 showed *trimming* the quantile family does not fix Sharpe — the top tail of S-E confidence is monotonically adversarial as q decreases. 27.0f confirmed adding regime features does not change that pattern. The selection rule itself ("trade the top quantile of regressor score") may be the wrong rule for this realised-PnL target, regardless of feature surface. R-T1 directly tests that.

### 7.3 Falsifiable hypothesis (H-C2)

> Pre-state: at least one of {absolute-threshold, middle-bulk, per-pair calibrated cutoff, ranked-cutoff} will lift val Sharpe above the C-sb-baseline by more than +0.05 absolute at a trade count ≥ 20,000, OR else H-C2 is falsified.

### 7.4 Implementation cost

- ~1.5 sub-phases (~4-5 days) — selection-rule changes affect cell construction, val-selection, and the quantile-family eval harness
- May require a scope amendment for "non-quantile selection cells" since prior sub-phases used quantile-family cells
- Inherits R7-A / R7-C row-set isolation logic from 27.0f
- Higher harness complexity than R-B

### 7.5 Risk surface

- **Blast radius**: medium — selection-rule changes touch val-selector, cell builder, eval-report writer
- **Rollback**: clean (per-sub-phase isolation)
- **前提崩しの可能性**: H2 PASS = PROMISING_BUT_NEEDS_OOS only; ADOPT_CANDIDATE wall preserved; test touched once. Selection-rule redesign does not threaten these gates.

### 7.6 Prior P(GO)

**25-35 %.**

Reasoning: R-T1 directly tests the most-load-bearing observation from the 5-eval picture (val-selector picked baseline in every sub-phase, which implies the rule is the issue, not the score). However, the same 5-eval picture also shows that **no scored signal has ever beat baseline at val-selection**, so even a smarter rule must extract signal that 5 different scores failed to surface. The prior is higher than R-B because R-T1 attacks the rule directly, but it is below R-E because the underlying signal scarcity is the more parsimonious explanation.

### 7.7 Open issues / preconditions

- Which rule? Pre-stating is mandatory — open-ended search violates the validation-only / test-once contract
- Scope-amendment doc may be required for non-quantile cell shapes
- Per-pair calibration interacts with 20-pair production v9; touchpoint must be audited

---

## 8. Routing branch R-T3 — concentration formalisation

### 8.1 Definition

Add **explicit concentration constraints** to the selection rule: per-pair budget caps, direction-balanced selection, max-share-per-bar, or formal trade-spacing rules. Strictly does not require new features or a new score.

### 8.2 Mechanism

27.0e §13 (trade-count budget audit) and 27.0f §3.3 (top-tail audit) suggested top-tail trades may concentrate in 1-2 pairs or in expensive regimes. Concentration formalisation aims to spread the trade selection across pairs/regimes and reduce adversarial exposure.

### 8.3 Falsifiable hypothesis (H-C3)

> Pre-state: a closed-form concentration constraint (e.g., max 10 % of trades per pair at q=5) will lift val Sharpe above the C-sb-baseline by more than +0.03 absolute, OR H-C3 is falsified.

### 8.4 Implementation cost

- **Scope-amendment doc REQUIRED** — concentration constraints sit outside the closed cell-construction contract
- ~2 sub-phases (~5-6 days)
- Constraints interact with val-selection and Clause 2 (cell-shape closure) in ways that need careful audit
- Higher complexity than R-B or R-T1

### 8.5 Risk surface

- **Blast radius**: medium-high — concentration constraints touch the cell-construction contract that has been stable since 26.0d
- **Rollback**: medium — clean per-sub-phase, but the scope amendment will leave a permanent surface even if rolled back
- **前提崩しの可能性**: Clause 2 implications must be analysed in the scope-amendment PR; risk of relaxing the closed-cell contract

### 8.6 Prior P(GO)

**5-15 %.**

Reasoning (verbatim from user):

> concentration formalisation はscope amendment が必要、clause 2 への影響が重い、27.0f で regime 軸が解けなかった後に pair/concentration だけで H2 に届く prior は低い。

The pair-concentration observation that motivates R-T3 is *real* but small. Conditioning on the fact that 5 sub-phases of broader interventions have not lifted Sharpe, expecting a pair-level constraint to do so is a low-prior bet. R-T3 stays on the routing tree because the closure memo should enumerate it, but it is not a dissent; it is a deferred option below the primary and the two dissents.

### 8.7 Open issues / preconditions

- Scope amendment must precede any implementation
- Clause 2 audit must accompany the amendment
- Per-pair concentration audit on 27.0f-β's C-se-rcw cell is *not* in artefact (would need re-run), so the magnitude prior is itself uncertain

---

## 9. Routing branch R-E — Phase 27 soft close

### 9.1 Definition

Soft-close Phase 27. Preserve all merged artifacts (PRs #316 → #332), all closure memos, the 5-eval evidence picture, and the hypothesis-status table. Do **not** initiate any further sub-phase under Phase 27. Open Phase 28 as a separate doc-only kickoff PR with a clean rebase on architecture / objective / hierarchy / target redesign.

### 9.2 Mechanism

The 5-eval picture (§3.1) shows the selection→monetisation seam has been attacked from three orthogonal axes (score, selection-rule trim, feature widening) without lifting val Sharpe above baseline in any sub-phase. Further single-axis interventions inside Phase 27 are likely to repeat the pattern at higher cost. A clean Phase 28 rebase on a structurally different surface (e.g., hierarchical architecture, multi-task objective, regime-conditioned model class, alternative target construction) has a better cost-prior ratio than continuing inside Phase 27.

### 9.3 Falsifiable hypothesis (H-C4)

H-C4 is *meta*: it is not falsified by a sub-phase. It is decided by the user reading the 5-eval picture and either accepting that the seam is exhausted (R-E) or asserting it is not (R-T1 / R-B / R-T3). R-E does not produce new data; it withdraws the search from a region that has produced 5 REJECTs.

### 9.4 Implementation cost

- **Phase 27 closure memo PR** (analogous to `docs/design/phase26_closure_memo.md` — see PR #315) — ~1 day, doc-only
- **Phase 28 kickoff PR** (analogous to `docs/design/phase27_kickoff.md`) — ~1-2 days, doc-only
- Total: ~2-3 days of doc-only work; no eval, no harness, no production change

### 9.5 Risk surface

- **Blast radius**: zero — doc-only; preserves all merged artifacts
- **Rollback**: trivial — Phase 27 sub-phases can be re-opened at any point if a future Phase 28 sub-phase suggests revisiting
- **前提崩しの可能性**: zero — γ closure PR #279, X-v2 OOS gating, Phase 22 frozen-OOS contract, ADOPT_CANDIDATE wall, NG#10 / NG#11, production v9 20-pair all preserved untouched

### 9.6 Prior P(GO)

**45-55 %.**

Reasoning: The single most informative fact in the 5-eval picture is that **the val-selector chose the inherited baseline cell in every sub-phase**. This is consistent with the hypothesis that the selection→monetisation seam at the current architecture has been thoroughly tested and the residual signal-to-noise is below what additional Phase 27 interventions can lift. R-E captures that pattern explicitly and reallocates effort to architecture/objective/target redesign in Phase 28. The prior is < 50 % because there is residual genuine uncertainty (R-T1 might surface a rule that the 5 prior cells did not test); the prior is ≥ 45 % because the pattern is strong and the alternative branches all have lower priors with higher cost.

### 9.7 Open issues / preconditions

- Phase 27 closure memo must enumerate which 27.0x sub-phases stay "deferred-not-foreclosed" (likely R-T1 / R-B; not-R-T3)
- Phase 28 kickoff scope must be defined separately; R-E does *not* itself decide Phase 28's content
- Production v9 untouched (binding constraint §11)

---

## 10. Cross-branch comparison matrix

| Branch | Primary lever | Cost (sub-phases) | Risk / blast radius | Scope amendment? | Rollback | Prior P(GO) | Verdict |
|---|---|---|---|---|---|---|---|
| **R-E** | Phase 27 soft close + Phase 28 rebase | ~2-3 days doc-only | zero | no | trivial | **45-55 %** | **Primary recommendation** |
| **R-T1** | Selection-rule redesign (absolute / middle-bulk / per-pair / ranked-cutoff) | 1.5 sub-phases (~4-5 days) | medium | maybe | clean per-sub-phase | **25-35 %** | **Dissent 1 — deferred-not-foreclosed** |
| **R-B** | Different feature axis (path / microstructure / multi-TF context) | 1.0 sub-phase (~3-4 days) | low | required (new closed allowlist) | trivial | **15-25 %** | **Dissent 2 — deferred-not-foreclosed** |
| R-T3 | Concentration formalisation (per-pair / direction / max-share) | 2 sub-phases (~5-6 days) | medium-high | required (Clause 2 audit) | medium | **5-15 %** | Below threshold; enumerated for completeness |

---

## 11. Binding constraints (verbatim)

These constraints are preserved by every branch in §6 — §9 and by this PR itself:

- D-1 bid/ask executable harness preserved
- R7-A subset preserved
- R7-C closed allowlist preserved (no broader F5-c / F5-d / F5-e)
- no R7-B
- no R-T1 / R-T3 choices smuggled in (this memo is comparison only)
- validation-only selection
- test touched once
- diagnostics not used for formal verdict
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- ADOPT_CANDIDATE wall preserved
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating remains required
- Phase 22 frozen-OOS contract preserved
- production v9 20-pair untouched
- MEMORY.md unchanged in this PR

This PR (the routing review) introduces:

- 1 new file: `docs/design/phase27_post_27_0f_routing_review.md`
- 0 changes to `src/` / `scripts/` / `tests/` / `artifacts/` / `.gitignore` / `MEMORY.md`
- 0 modifications to prior verdicts
- 0 production changes

---

## 12. Decision rule — pre-stated thresholds

Pre-state the numeric criteria under which each branch is selected, so the routing choice is mechanical rather than vibes-based:

| Condition | Selected branch |
|---|---|
| 5-eval picture shows val-selected = baseline in ≥ 4 of 5 sub-phases (**observed: 5/5**) AND R-T3 prior < 15 % AND no user override → | **R-E** |
| R-E preconditions hold AND user pre-states a specific selection-rule class (absolute / middle-bulk / per-pair / ranked-cutoff) AND prior P(R-T1 GO) is revised upward by ≥ 10 percentage points → | **R-T1 (overrides R-E)** |
| R-E preconditions hold AND user pre-states a specific non-regime feature class with a falsifiable H-C1 hypothesis AND prior P(R-B GO) is revised upward by ≥ 10 pp → | **R-B (overrides R-E)** |
| User authorises Clause 2 amendment AND R-T3 prior is revised above 20 % → | **R-T3** |

The observed condition (val-selector picked baseline in 5/5 sub-phases) **does** meet the R-E pre-state criterion. R-T1 and R-B remain as dissents that the user can elevate with an explicit override.

---

## 13. Recommendation — primary R-E, dissents R-T1 and R-B

### 13.1 Primary recommendation — R-E (Phase 27 soft close)

**Phase 27 should be soft-closed.** Five sub-phase β-evals (27.0b / 27.0c / 27.0d / 27.0e / 27.0f) have collectively tested:

- **score axis** (S-C TIME penalty, S-D calibrated EV, S-E regression on realised PnL)
- **selection-rule axis** (R-T2 quantile-family trim {5, 7.5, 10})
- **feature axis** (R7-C regime/context allowlist)

In every sub-phase, the val-selector picked the inherited C-sb-baseline cell over the new candidate. The new findings produced 1 PARTIAL H1m PASS (27.0d Spearman +0.438) and 0 H2 PASSes (no Sharpe lift). The pattern is consistent with the selection→monetisation seam at this architecture being saturated relative to the realised-PnL target's signal-to-noise.

**Action under R-E primary**:

1. Issue a `docs/design/phase27_closure_memo.md` PR (analogous to PR #315 for Phase 26) — soft-closes Phase 27 with the 5-eval picture, the hypothesis-status table, and R-T1 / R-B explicitly preserved as deferred-not-foreclosed
2. Issue a `docs/design/phase28_kickoff.md` PR with a clean rebase on architecture / objective / hierarchy / target redesign
3. Do not run any further 27.0x-β eval

### 13.2 Dissent 1 — R-T1 (selection-rule redesign; deferred-not-foreclosed)

The most-load-bearing observation against R-E is that **no Phase 27 sub-phase has yet directly tested the selection rule itself**. R-T2 was a *trim* of the quantile family, not a *redesign* of the rule. If the user reads the 5-eval picture as "the rule is wrong" rather than "the seam is exhausted," then R-T1 is the cheapest sharpest test of that reading. R-T1 stays on the routing tree as the primary dissent and can be elevated to primary at the user's discretion under §12 row 2.

### 13.3 Dissent 2 — R-B (different feature axis; deferred-not-foreclosed)

The second dissent is R-B. R7-C tested a narrow regime-statistic axis; R-B would test a *different feature class entirely* (path-shape, microstructure, or multi-TF context). The R-B prior is lower than R-T1's because the pattern of "no scored cell beats baseline" suggests the issue is rule, not features. R-B is preserved because the falsification of H-B6 specifically pointed to "the feature surface is not the bottleneck *for regime statistics*" — it did not rule out a path-class or microstructure-class lift. R-B can be elevated to primary at the user's discretion under §12 row 3.

### 13.4 Why R-T3 is not a dissent

R-T3 (concentration formalisation) requires a Clause 2 scope amendment that is heavy relative to its 5-15 % prior. The 5-eval picture's strongest signal is val-selection / monetisation, not pair concentration. R-T3 is enumerated in the matrix for completeness but is not preserved as a dissent.

---

## 14. Open questions / unknowns

Five open questions that this PR does **not** resolve. They are preserved so that a future Phase 28 kickoff (or an R-T1 / R-B sub-phase if a dissent is elevated) can revisit them:

1. **Is R-T1 absolute-threshold / middle-bulk / per-pair / ranked-cutoff selection worth testing despite the 5-eval picture?** Answering this requires the user to pre-state a specific rule class — open-ended search violates validation-only / test-once.
2. **Does any non-regime feature axis (path-shape, microstructure, multi-TF context) carry more information than R7-C did?** Falsifiable only by an R-B sub-phase with a pre-stated H-C1 hypothesis and a scope-amendment doc.
3. **Should Phase 28 rebase on hierarchical / multi-task / regime-conditioned architecture?** The 5-eval picture suggests yes, but the choice of architecture is itself a kickoff-PR decision, not a routing-review decision.
4. **Should the realised-PnL target itself be reconstructed?** 27.0d showed Spearman PASS / Sharpe FAIL — the target may be measuring something different from what the score should optimise. This is a Phase 28 scope question.
5. **How far can exploration continue before Phase 22 frozen-OOS / X-v2 OOS gating must be revisited?** The frozen-OOS contract is *not* threatened by any current branch, but a deeper Phase 28 rebase may require an OOS-gate review. Not in scope for this PR.

---

## 15. Next sub-phase — explicit no-auto-route

**This PR does not initiate any sub-phase.** Specifically:

- No `scripts/stage27_0g_*.py` or `scripts/stage28_*` is authored
- No `docs/design/phase28_kickoff.md` is created
- No `docs/design/phase27_closure_memo.md` is created
- No `docs/design/phase27_scope_amendment_*.md` is created
- No `tests/unit/test_stage27_0g_*` is authored
- No `MEMORY.md` update beyond what landed at PR #332 merge
- No production change

The next action — whether **R-E primary** (Phase 27 closure memo + Phase 28 kickoff), **R-T1 dissent elevation**, **R-B dissent elevation**, or any other route — requires an explicit later user instruction. No auto-route.

---

## 16. References

- PR #316 — Phase 27 kickoff (`docs/design/phase27_kickoff.md`)
- PR #318 — Phase 27.0b-β S-C TIME penalty eval
- PR #319 — Phase 27 post-27.0b routing review (`phase27_routing_review_post_27_0b.md`)
- PR #321 — Phase 27.0c-β S-D calibrated EV eval
- PR #322 — Phase 27 post-27.0c routing review (`phase27_routing_review_post_27_0c.md`)
- PR #325 — Phase 27.0d-β S-E regression on realised PnL eval
- PR #326 — Phase 27 post-27.0d routing review (`phase27_routing_review_post_27_0d.md`)
- PR #328 — Phase 27.0e-β S-E quantile-family trim eval
- PR #329 — Phase 27 post-27.0e routing review (`phase27_routing_review_post_27_0e.md`); introduced H-B6
- PR #330 — Phase 27 scope amendment R7-C (`phase27_scope_amendment_r7_c.md`)
- PR #331 — Phase 27.0f-α S-E + R7-C design memo (`phase27_0f_alpha_s_e_r7_c_regime_context_design_memo.md`)
- PR #332 — Phase 27.0f-β S-E + R7-C regime/context eval (this PR's antecedent)
- PR #279 — γ closure (binding constraint)
- PR #315 — Phase 26 closure memo (template for R-E primary path)

---

*End of `docs/design/phase27_post_27_0f_routing_review.md`.*
