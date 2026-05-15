# Phase 28 Kickoff Memo — Architecture / Objective / Target Redesign

**Type**: doc-only formal kickoff memo
**Status**: opens Phase 28; declares **scope binding**; does NOT initiate any sub-phase
**Branch**: `research/phase28-kickoff`
**Base**: master @ `f56bba5` (post-PR #334 / Phase 27 closure memo)
**Pattern**: analogous to PR #299 (Phase 26 kickoff) / PR #316 (Phase 27 kickoff), with Phase 28-specific axes (architecture / objective / target redesign + regime-conditioned + monetisation-aware selection)
**Date**: 2026-05-16

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28 kickoff** and the canonical source of Phase 28's **scope binding**. It declares which axes are **admissible at kickoff**, which Phase 27 carry-forward routes are **deferred-not-foreclosed**, and which Phase 27 inertia routes are **NOT admissible**. It does **NOT** by itself authorise any 28.0a / 28.0b / ... design memo, sub-phase β-eval, scope amendment, implementation, eval, or production change. It does **NOT** select a first-mover axis. Each sub-phase and each elevation of an admissible-but-not-yet-authorised route requires an **explicit separate later user routing decision**. R-T1 / R-B / R-T3 do not auto-resume by merge of this PR.*

Same approval-then-defer pattern as PR #299 / PR #316 / PR #311 scope amendment.

---

## 1. Phase 28 mission statement

Phase 27 closed at PR #334 with three load-bearing findings consolidated into the **5-eval evidence picture** (27.0b S-C / 27.0c S-D / 27.0d S-E / 27.0e R-T2 trim / 27.0f R7-C):

1. **All five sub-phase β-evals returned REJECT.** No ADOPT_CANDIDATE; no PROMISING_BUT_NEEDS_OOS.
2. **Val-selector picked the inherited C-sb-baseline cell in 5/5 sub-phases.** The val-selected (cell\*, q\*) record is **bit-identical** across the five sub-phases. No candidate cell was val-superior.
3. **S-E (27.0d) unlocked a real ranking signal (Spearman +0.438) but monetisation conversion failed (Sharpe -0.483).** R-T2 trim (27.0e) did not recover Sharpe; R7-C regime/context features (27.0f) did not recover Sharpe; in both 27.0e and 27.0f the val-selector still picked the baseline.

The closure-time interpretation (PR #334 §6 + §9) is that the **selection→monetisation seam at this architecture has been saturated** by score-axis / selection-trim / regime-statistic-feature interventions. Continuing inside Phase 27 by inertia along the same hypothesis chain is **not** the cost-prior-favorable next move.

**Phase 28 exists** to **rebase** the research surface around three structurally different redesign axes: **architecture**, **objective**, and **target**. Phase 28 also opens two **selection / context** axes that are structurally distinct from the Phase 27 score-axis: **regime-conditioned / hierarchical modeling** and **monetisation-aware selection** (which together can re-frame the deferred R-B / R-T1 routes inside the new architecture rather than as standalone Phase 27 extensions).

The Phase 28 mission is explicitly **NOT** to continue Phase 27 by inertia. Phase 28 is a structural rebase, not a sub-phase chain extension.

---

## 2. What Phase 28 inherits from Phase 27

The following items are inherited verbatim and remain binding into Phase 28 unless explicitly re-scoped via a Phase 28 scope amendment:

### 2.1 Contracts / harness

- **D-1 bid/ask executable realised-PnL harness** (inherited from Phase 26 / earlier). Per-row barrier PnL is computed against bid_h / ask_l (for long) and ask_h / bid_l (for short). No mid-to-mid leakage, no spread_factor parameter on the cache.
- **Fix A row-set isolation contract** (developed mid-27.0f-β; PR #332). When an additive feature row-drop is introduced for a candidate cell, the drop must be scoped to that candidate cell only; baseline / replica cells stay on the un-dropped parent row-set. `drop_rows_with_missing_*_features` returns `(df, stats, keep_mask)` so PnL / labels / scores can be aligned without recomputation.
- **5-fold OOF (DIAGNOSTIC-ONLY; seed=42)** sub-procedure carried over for any sub-phase that fits a regressor / classifier on training data.
- **2-layer selection-overfit guard** (validation-only selection + test touched once).
- **R7-A closed allowlist** (4 features: `pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`). Touchable only as **inherited baseline reference**; broadening requires scope amendment.
- **R7-C closed allowlist** (3 features: `f5a_spread_z_50`, `f5b_volume_z_50`, `f5c_high_spread_low_vol_50`). Frozen as reference; any future regime-statistic widening requires a fresh scope amendment.

### 2.2 Phase 27 evidence — preserved as historical record (not as Phase 28 next step)

- **5-eval evidence picture** (PR #334 §4.1) — five sub-phase β-evals with bit-identical val-selected outcome. Cited as Phase 28's anchoring evidence for "the seam is saturated at this architecture."
- **C-sb-baseline numeric reference** — see §10 below (single source).
- **C-se-rcw ≈ C-se-r7a-replica equivalence at 27.0f** (max |Δ Sharpe| 0.0039 across 5 quantiles) — cited as evidence that the regime-statistic feature sub-axis is insufficient to lift Sharpe at the current architecture.

### 2.3 Hypothesis carry-forward

Three NEW closure-time hypotheses from PR #334 §9 are carried into Phase 28 as **UNRESOLVED**:

- **H-B7** — the val-selection rule itself is misspecified
- **H-B8** — the feature surface needs path / microstructure / multi-TF context features, not regime-statistic features
- **H-B9** — the selection→monetisation seam has been structurally exhausted at the current architecture

§4 below records the exact closure-time framing.

### 2.4 Carry-forward register (R-T1 / R-B / R-T3)

PR #334 §11 — §12:

- **R-T1** (selection-rule redesign): **deferred-not-foreclosed**; prior 25-35 %; auto-resume forbidden
- **R-B** (different feature axis): **deferred-not-foreclosed**; prior 15-25 %; auto-resume forbidden; scope amendment required at the point of resumption
- **R-T3** (concentration formalisation): **below-threshold; deferred; NOT a dissent**; prior 5-15 %; Clause 2 amendment required at the point of any resumption

Phase 28 preserves all three in their Phase 27 closure-time state. Phase 28 may **reframe** R-T1 or R-B inside one of its admissible axes (see §5 / §15), but the elevation itself requires an explicit user routing decision.

### 2.5 Production / hard gates

- **production v9 20-pair** (Phase 9.12 closure tip `79ed1e8`) — untouched throughout Phase 27; remains untouched at Phase 28 kickoff. No production change is in scope for Phase 28 kickoff.
- **γ closure** (PR #279) — preserved.
- **X-v2 OOS gating** — remains required for any future production deployment.
- **Phase 22 frozen-OOS contract** — preserved.
- **NG#10 / NG#11** — not relaxed.
- **ADOPT_CANDIDATE wall** — preserved. **H2 PASS = PROMISING_BUT_NEEDS_OOS only**.

---

## 3. What Phase 28 explicitly does NOT inherit

Phase 28 explicitly does **NOT** continue the Phase 27 hypothesis chain by inertia. The following Phase 27 directions are **NOT admissible at Phase 28 kickoff**:

1. **S-C / S-D / S-E score-axis micro-redesign**. Score formulations that modify a single weight / penalty / scaling / calibration term over the same R7-A baseline and the same realised-PnL target are NOT admissible. The score axis has been consumed in Channel B (PR #334 §5.1).
2. **R-T2-style quantile-family trim alone**. Selection interventions that only narrow or widen the quantile budget over the same regressor score are NOT admissible. The trim sub-axis has been consumed (PR #334 §5.2).
3. **R7-C-style regime-statistic-only feature widening as a default move**. Adding new closed-allowlist features that fit the same R7-C template (rolling z-scores of spread / volume / regime indicators) without a structurally new model class or new target is NOT admissible. The regime-statistic sub-axis has been consumed (PR #334 §5.3).
4. **C-sb-baseline–anchored score-only sweeps**. Any sub-phase that only redefines the score over C-sb-baseline cells, without changing the architecture / objective / target / selection-rule / feature class, is NOT admissible.
5. **Resumption of R-T1 / R-B / R-T3 as standalone Phase 27 extensions**. R-T1 and R-B remain deferred-not-foreclosed (§2.4) but their resumption must happen inside Phase 28's admissible-axis framework (§5 / §15), not as a Phase 27 sub-phase chain extension.

The exclusion list is not pejorative; the Phase 27 hypothesis chain was substantive and produced 5 formal verdicts plus a real H1m signal at S-E. The point is that the cost-prior ratio for continuing those axes inside the same architecture is unfavorable per the 5-eval picture, and Phase 28 explicitly opens a different surface.

---

## 4. Carry-forward hypotheses H-B7 / H-B8 / H-B9 (verbatim from PR #334 §9)

| ID | Closure-time framing | Phase 28 status | Notes |
|---|---|---|---|
| **H-B7** | The val-selection rule itself is misspecified (top-quantile on regressor score is the wrong rule). | **UNRESOLVED — carried into Phase 28** | Motivates A4 (monetisation-aware selection). Resumption of R-T1 as a Phase 27 extension is NOT admissible; reframing under A4 is admissible at kickoff (see §15). |
| **H-B8** | The feature surface needs path / microstructure / multi-TF context features, not regime-statistic features. | **UNRESOLVED — carried into Phase 28** | Motivates A3 (regime-conditioned modeling) or A0 (architecture) / A2 (target) if path/microstructure features are admitted as part of a structural redesign. Resumption of R-B as a Phase 27 extension is NOT admissible; reframing under A3 / A0 / A2 is admissible at kickoff (see §15). |
| **H-B9** | The selection→monetisation seam has been structurally exhausted at the current architecture. | **Phase 28 background premise** | H-B9 is the meta-hypothesis that justifies Phase 28's rebase choice. Phase 28 does not test H-B9 directly inside any single sub-phase; it tests it implicitly by exploring structurally different axes (A0 — A4) and observing whether any of them lifts val Sharpe above the §10 baseline. |

Each of H-B7 / H-B8 / H-B9 is **carried into Phase 28** as an open hypothesis. None of them is resolved by this kickoff PR.

---

## 5. Candidate axes A0 — A4 (admissible at kickoff)

The following five axes are **admissible at Phase 28 kickoff**. Each axis is declared at scope level only; no falsifiable hypothesis (H-Cx) is pre-stated at kickoff. Each axis requires a **separate design memo PR** (and, where indicated, a scope amendment PR) to be initiated. Kickoff opens the door; sub-phase design memos walk through it.

### 5.1 A0 — architecture redesign

Replace or augment the model class itself with a structurally different architecture. Examples (not exhaustive; sub-phase design memo pre-states the specific architecture):

- **Hierarchical two-stage candidate → confirm** — stage 1 generates trade candidates; stage 2 confirms / rejects with a different feature subset or model class.
- **Multi-task heads** — joint loss over TP-prob / SL-prob / TIME-prob / realised-PnL regression, with shared backbone.
- **Regime-conditioned heads** — model class is the same but the head is conditioned on a regime feature (overlap with A3; the architectural-vs-conditional split is decided at sub-phase scoping).
- **Sequence / structural models** — RNN / temporal CNN over recent bars rather than per-bar tabular features.

Reference inputs at kickoff: H-B9 (seam exhausted at this architecture); H-B7 implicitly (if the architecture decides selection, R-T1 reframing fits here).

### 5.2 A1 — objective redesign

Redefine the loss function used by the model, keeping the architecture and target broadly similar. Examples:

- **Realised-PnL re-weighted loss** — weight per-row loss by realised-PnL magnitude or by absolute spread cost.
- **Asymmetric loss** — penalise false-positives in expensive regimes more than false-negatives in cheap regimes (a structural answer to "top tail is adversarial," which Phase 27 R-T2 / R7-C tried to fix downstream).
- **Cost-aware loss** — incorporate spread cost or realised slippage directly into the loss signal during training.

Reference inputs at kickoff: H-B3 partial (ranking signal real, monetisation conversion failed) — A1 attacks the monetisation conversion at training time rather than at selection time.

### 5.3 A2 — target redesign

Replace or augment the realised-PnL target with a structurally different target. Examples:

- **Trade-quality target** — a continuous target combining path features (MFE / MAE / time-in-trade) rather than terminal barrier PnL.
- **Risk-adjusted target** — per-trade Sharpe-like target normalised by realised volatility over the bar window.
- **Cost-decomposed target** — separate the gross PnL component from the spread-cost component and target each separately.

Reference inputs at kickoff: PR #334 §13 directional hint; H-B3 partial (target may be too noisy at the per-trade level for confidence rankings to translate into monetisation).

### 5.4 A3 — regime-conditioned / hierarchical modeling

Decompose the model along a **regime axis** in a structural way (not merely as additive features as in 27.0f R7-C). Examples:

- **Gating network** — a learned gate decides which sub-model handles a given bar based on regime features.
- **Mixture-of-experts** — multiple specialised models, weighted per bar by regime.
- **Per-regime training** — fit separate models per regime cell (e.g., spread tertile × volume tertile) and combine at inference.

Reference inputs at kickoff: H-B8 (R7-C statistic-only widening was insufficient — regime information may need to enter the architecture, not the feature surface). R-B can be reframed under A3 with a scope amendment that admits the new feature class (if path / microstructure / multi-TF context features are part of the regime axis).

### 5.5 A4 — monetisation-aware selection

Redesign the selection rule jointly with the score, rather than applying top-quantile-on-score after the fact. Examples:

- **Joint training of score + selection threshold** — the selection threshold becomes a learned parameter, not a held-out quantile.
- **Cost-aware ranking** — rank trades by score-minus-expected-cost rather than by score alone.
- **Position-conditional selection** — selection decision depends on current portfolio / pair concentration / direction balance.

Reference inputs at kickoff: H-B7 (val-selection rule misspecified). R-T1 can be reframed under A4: an explicit user routing decision can elevate R-T1 inside A4's frame (e.g., absolute-threshold / middle-bulk / ranked-cutoff as instances of monetisation-aware selection rather than as Phase 27 extensions).

### 5.6 Axes overlap / orthogonality at kickoff

Axes A0 — A4 are **not strictly orthogonal**. A specific sub-phase may combine, for example, A0 (hierarchical architecture) with A4 (monetisation-aware selection) where the second stage performs the selection decision. Kickoff does **not** require axes to be exercised one-at-a-time; the design memo for any sub-phase pre-states which axes it combines and how.

---

## 6. Axis evaluation framework (skeleton; instantiated at each sub-phase design memo)

Each Phase 28 sub-phase design memo will instantiate the following evaluation skeleton. Kickoff declares the skeleton; it does **not** populate it.

| Field | Source |
|---|---|
| Axis (A0 / A1 / A2 / A3 / A4 or combination) | sub-phase design memo |
| Falsifiable hypothesis (H-Cx) | sub-phase design memo (pre-stated) |
| Implementation cost (days, sub-phases) | sub-phase design memo |
| Scope-amendment required? | sub-phase design memo (per §15 policy) |
| Risk surface / blast radius / rollback | sub-phase design memo |
| Prior P(GO) | sub-phase design memo (honest estimate with reasoning) |
| Baseline reproduction (§10 baseline) | sub-phase eval (FAIL-FAST gate) |
| Selection-overfit guard | sub-phase eval (2-layer; validation-only / test once) |
| Cell structure | sub-phase design memo (control + candidate cells) |
| Sanity probe items | sub-phase eval |

The skeleton mirrors Phase 27 sub-phase design memos (e.g., `phase27_0c_alpha_*` / `phase27_0d_alpha_*` / `phase27_0f_alpha_*`) and the routing-review evaluation columns (e.g., `phase27_post_27_0f_routing_review.md` §6 — §10).

---

## 7. Admissibility status table at kickoff

| Route | Status at kickoff | Notes |
|---|---|---|
| **A0** architecture redesign | **admissible at kickoff** | Separate design memo PR + (per §15) potential scope amendment |
| **A1** objective redesign | **admissible at kickoff** | Separate design memo PR; scope amendment may be required if the loss change touches Clause 2 |
| **A2** target redesign | **admissible at kickoff** | Separate design memo PR + scope amendment (label/target spec change) |
| **A3** regime-conditioned modeling | **admissible at kickoff** | Separate design memo PR + (per §15) potential scope amendment if feature surface broadens |
| **A4** monetisation-aware selection | **admissible at kickoff** | Separate design memo PR; scope amendment may be required if non-quantile selection cell shapes are introduced |
| **R-T1** (Phase 27 carry-forward) | **deferred-not-foreclosed** | Auto-resume forbidden; may be reframed under A4 with explicit user routing decision |
| **R-B** (Phase 27 carry-forward) | **deferred-not-foreclosed** | Auto-resume forbidden; may be reframed under A3 / A0 / A2 with explicit user routing decision + scope amendment |
| **R-T3** (Phase 27 carry-forward) | **below-threshold; deferred; NOT a dissent** | Resumption requires Clause 2 amendment + user routing decision |
| **Phase 27 inertia routes** (§3 items 1–5) | **NOT admissible at Phase 28 kickoff** | Score-only / quantile-trim-only / R7-C-template / C-sb-anchored-score-only / R-T1-R-B-as-Phase-27-extension |

---

## 8. First-mover priority — explicit no-auto-select

**Phase 28 kickoff does NOT select a first-mover axis.** A0 — A4 are simultaneously admissible at kickoff. The order in which they are exercised, the combinations chosen, and the first sub-phase to be initiated are all **separate later user routing decisions**.

This mirrors Phase 27 kickoff (PR #316), which opened the score-objective + feature-widening axes without selecting which sub-phase to run first. The actual order in Phase 27 turned out to be 27.0b → 27.0c → 27.0d → 27.0e → 27.0f; that order was not declared at kickoff. Phase 28 follows the same pattern.

**No auto-route after merge.** Squash-merging this PR does not initiate any sub-phase. The next action requires an explicit user instruction.

---

## 9. Phase 27 vs Phase 28 — explicit comparison

| Dimension | Phase 27 | Phase 28 |
|---|---|---|
| Hypothesis frame | "Selection → monetisation seam at this architecture is fixable by score / selection / regime-statistic feature interventions." | "The selection → monetisation seam at *this* architecture is saturated; the architecture / objective / target / selection-rule itself must be redesigned." |
| Channel B axes | S-C / S-D / S-E (consumed at this architecture) | Closed |
| Channel C axes | R-T2 quantile-family trim (consumed) | Closed; R-T1 redesign **reframed under A4** with explicit elevation |
| Channel A axes | R7-C regime-statistic widening (consumed) | Closed; R-B feature-class widening **reframed under A3 / A0 / A2** with explicit elevation + scope amendment |
| Architecture | LightGBM tabular classifier / regressor on R7-A (4 features) | **A0 axis admissible** — hierarchical / multi-task / regime-conditioned / sequence |
| Objective | Class CE loss (S-B) or Huber regression on realised PnL (S-E) | **A1 axis admissible** — re-weighted / asymmetric / cost-aware |
| Target | Triple-barrier event-time realised PnL at K_FAV=1.5×ATR / K_ADV=1.0×ATR / H_M1=60, bid/ask executable | **A2 axis admissible** — trade-quality / risk-adjusted / cost-decomposed |
| Selection rule | Top-quantile on regressor / classifier score | **A4 axis admissible** — joint score + selection / cost-aware ranking / position-conditional |
| Feature surface | R7-A (4) + R7-C (3) closed allowlists | R7-A / R7-C **frozen as reference**; new features admitted via per-sub-phase scope amendment |
| Universe / span / split / OOF | 20-pair / 730d / 70-15-15 chronological / 5-fold OOF (DIAGNOSTIC-ONLY, seed=42) | Inherited unless explicitly re-scoped under Phase 22 frozen-OOS / §15 |
| Baseline reference | C-sb-baseline (Phase 26 R6-new-A inheritance) | Same C-sb-baseline (see §10) |
| Closure pattern | Sub-phase β-evals + routing reviews + closure memo | TBD — Phase 28 closure pattern decided at Phase 28 closure time |

The shared ground (data / harness / baseline / OOF / split) ensures Phase 28 results can be compared back to the 5-eval picture using identical reference numbers. The divergence is the **hypothesis frame** and the **redesign axes**.

---

## 10. Closure-time baseline reference (single source of truth)

The Phase 28 baseline is the **C-sb-baseline** cell inherited from Phase 26 R6-new-A (PR #313) and confirmed bit-identical across all 5 Phase 27 sub-phases (PR #334 §4.1). Phase 28 records the numeric reference **once** here and refers to it as **"§10 baseline"** throughout the rest of the memo and across all Phase 28 sub-phase design memos:

| Metric | Value |
|---|---|
| Picker | S-B raw (P(TP) − P(SL)) |
| Cell | C-sb-baseline |
| Selected q\* | 5 % |
| Selected cutoff | +0.126233 |
| Val Sharpe | -0.1863 |
| Val n_trades | 25,881 |
| **Test Sharpe** | **-0.1732** |
| **Test n_trades** | **34,626** |
| **Test ann_pnl (pip)** | **-204,664.4** |
| Test formal Spearman(score, realised_pnl) | -0.1535 |
| Source PR | #313 (Phase 26 R6-new-A); reproduced in #318 / #321 / #325 / #328 / #332 |

This baseline is **immutable** for Phase 28 sub-phase comparisons. Any sub-phase eval that reports a candidate cell's val / test metrics references the §10 baseline as the inherited control. Sub-phase eval scripts continue to embed the FAIL-FAST baseline reproduction check inherited from 27.0c-α §7.3 / 27.0d-α / 27.0e-α / 27.0f-α (n_trades exact, Sharpe ±1e-4, ann_pnl ±0.5 pip tolerance).

If a Phase 28 sub-phase introduces a new target (A2) that makes the §10 baseline numbers structurally incomparable, the sub-phase scope amendment must explicitly declare the **new comparison baseline** and the rationale for replacing the §10 baseline for that sub-phase only. The §10 baseline itself is not modified by such an amendment; the sub-phase uses an auxiliary baseline alongside §10.

---

## 11. Decision-rule for sub-phase initiation (suggested, not binding)

Each Phase 28 sub-phase design memo is **suggested** to satisfy the following conditions before initiation. These are **suggested** screens to flag inertia / scope drift; they are **not** binding gates. Final initiation authority rests with the **user routing decision**.

| Suggested condition | Purpose |
|---|---|
| Sub-phase axis is one of A0 / A1 / A2 / A3 / A4 (or an explicit combination) | Ensures admissibility-at-kickoff (§7) |
| Sub-phase pre-states a falsifiable H-Cx hypothesis with quantitative criteria | Mirrors Phase 27 H-B5 / H-B6 pre-statement pattern |
| Sub-phase declares its inherited baseline (§10) and the FAIL-FAST reproduction check | Mirrors 27.0c-α §7.3 inheritance |
| Sub-phase declares its cell structure (control + candidate cells) | Mirrors 27.0f-α 3-cell structure |
| Sub-phase declares its scope-amendment requirement (per §15) | Ensures the amendment surface is visible before implementation |
| Sub-phase is NOT one of the §3 NOT-admissible Phase 27 inertia routes | Ensures Phase 28 does not regress to Phase 27 |
| Sub-phase preserves D-1 / NG#10 / NG#11 / γ closure PR #279 / X-v2 OOS / Phase 22 frozen-OOS / production v9 untouched | Ensures binding constraints (§13) are honoured |

A sub-phase design memo that fails any of these suggested conditions is **not** automatically blocked; it is flagged for user routing-decision attention. The user may choose to override any suggestion with explicit reasoning at routing time. Kickoff does not impose binding gates beyond §13.

---

## 12. Open questions / unknowns carried into Phase 28

Five open questions are carried into Phase 28 from the Phase 27 closure memo (PR #334 §12). They are not resolved by this kickoff PR; they are pre-stated so that Phase 28 sub-phase design memos can address them explicitly when relevant.

1. **Is C-sb-baseline still the right baseline under an architecture / objective / target redesign?** Under A0 (architecture change) or A2 (target change), the §10 baseline may become semantically misaligned with the new candidate cells. Sub-phase design memos must declare whether they keep §10 or introduce an auxiliary baseline (§10 itself is not modified).
2. **Is realised-PnL the right target to keep?** A2 explicitly opens target redesign. If A2 produces a better target, future Phase 28 sub-phases may inherit that target instead of realised-PnL.
3. **Is the 20-pair universe the right universe under Phase 22 frozen-OOS?** Phase 22 frozen-OOS contract preserves the 20-pair canonical universe for OOS-gated production deployment. Phase 28 research sub-phases may explore **subset / superset** universes for hypothesis testing, provided the Phase 22 frozen-OOS contract is preserved for any future production deployment. Sub-phase design memos must pre-state the universe choice and its compatibility with the frozen-OOS contract.
4. **Is the 730-day span / 70-15-15 chronological split the right split for Phase 28 architectures?** Some A0 architectures (e.g., sequence models) may require different windowing or different temporal split. Sub-phase design memos must pre-state the windowing.
5. **Should R-T1 / R-B elevation happen inside Phase 28's frame (under A4 / A3) or as a separate later sub-phase chain?** Kickoff records that reframing under A3 / A4 is admissible; the actual elevation decision is deferred.

---

## 13. Binding constraints (verbatim)

This kickoff preserves every constraint that was binding at the end of Phase 27. They remain binding throughout Phase 28 unless explicitly re-scoped via a Phase 28 scope amendment PR.

- D-1 bid/ask executable harness preserved
- validation-only selection
- test touched once
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating remains required
- Phase 22 frozen-OOS contract preserved
- production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) untouched
- MEMORY.md unchanged inside this PR (post-merge bookkeeping is a separate operation, not part of the PR diff)
- doc-only
- no implementation
- no eval
- no production change
- no auto-route after merge
- no first-mover axis selection
- no R-T1 / R-B / R-T3 elevation
- no Phase 28 sub-phase design memo
- no scope amendment
- no prior verdict modification

---

## 14. What this PR is NOT

This PR is **NOT**:

1. A Phase 28 sub-phase design memo (any `docs/design/phase28_0?_alpha_*_design_memo.md`).
2. A Phase 28 scope amendment (any `docs/design/phase28_scope_amendment_*.md`).
3. An R-T1 / R-B / R-T3 elevation.
4. A first-mover selection over A0 — A4.
5. A modification to the §10 C-baseline numeric reference.
6. A modification to any prior Phase 25 / Phase 26 / Phase 27 verdict, evidence point, hypothesis status, or routing decision.
7. An admission of any Phase 27 inertia route (§3 items 1–5).
8. An authorisation to touch `src/` / `scripts/` / `tests/` / `artifacts/` / `.gitignore` / `MEMORY.md` in this PR.
9. An authorisation to touch production v9 or any production deployment.
10. An auto-route trigger for any future action.

The next Phase 28 step (whether the first A0 / A1 / A2 / A3 / A4 sub-phase design memo, an R-T1 / R-B reframing under A4 / A3, an A2 target-redesign scope amendment, or any other action) requires a **separate later user routing decision**.

---

## 15. Phase 28 admissibility vs scope amendment policy

Phase 28 inherits Phase 27's admissibility / amendment policy and adds two clarifications specific to the Phase 28 axes.

### 15.1 Inherited policy (Phase 27 → Phase 28)

- Broadening the closed-allowlist features (R7-A / R7-C) **requires a scope amendment** PR analogous to PR #311 (Phase 26 R6-new-A allowlist) or PR #330 (Phase 27 R7-C allowlist).
- Changing Clause 2 (cell-shape closure) **requires a scope amendment** PR.
- Introducing a new closed allowlist (e.g., R7-D microstructure features under R-B reframing) **requires a scope amendment** PR.
- Sub-phase design memos for admissible-at-kickoff axes A0 — A4 do **not** by themselves require a scope amendment, **unless** the sub-phase touches one of the above surfaces.

### 15.2 Phase 28-specific clarifications

- **A0 (architecture redesign)** sub-phases that change the **target** in addition to the architecture trigger A2 amendment policy.
- **A2 (target redesign)** sub-phases **always** require a scope amendment PR (label / target spec change is a closed surface).
- **A4 (monetisation-aware selection)** sub-phases that introduce **non-quantile selection cell shapes** trigger a Clause 2 scope amendment.
- **R-T1 reframing under A4** does **not** by itself require a Phase 28 scope amendment if the cell shape remains quantile-based; if a non-quantile cell shape is introduced (per the R-T1 dissent's H-C2 examples: absolute-threshold / middle-bulk / ranked-cutoff), a Clause 2 amendment is required.
- **R-B reframing under A3 / A0 / A2** **always** requires a scope amendment PR to admit the new feature class, since R7-A subset is closed at Phase 27 closure and any non-regime feature class needs explicit admittance.

### 15.3 Why this matters at kickoff

The amendment policy is declared here so that sub-phase design memo authors (whether the current research stream or a future agent) know up-front which axes require an additional amendment PR before β-eval initiation. This avoids the mid-PR amendment surprise that triggered the 27.0f-β Fix A correction. Phase 27 generated two scope amendments (PR #324 S-E, PR #330 R7-C) over five sub-phases; Phase 28 may generate more given its broader admissibility surface.

---

## 16. References

**Phase 27 closure / routing**:
- PR #316 — Phase 27 kickoff (template for this PR's structure)
- PR #333 — Phase 27 post-27.0f routing review (R-E primary decision)
- PR #334 — Phase 27 closure memo (source of §2 inheritance, §4 carry-forward hypotheses, §10 baseline)

**Phase 27 β-evals (5-eval evidence picture)**:
- PR #318 — 27.0b-β S-C TIME penalty eval
- PR #321 — 27.0c-β S-D calibrated EV eval
- PR #325 — 27.0d-β S-E regression on realised PnL eval
- PR #328 — 27.0e-β S-E quantile-family trim eval
- PR #332 — 27.0f-β S-E + R7-C regime/context eval (Fix A row-set isolation introduced)

**Phase 27 scope amendments**:
- PR #324 — Phase 27 scope amendment S-E
- PR #330 — Phase 27 scope amendment R7-C

**Prior closure / kickoff memos (template / context)**:
- PR #298 — Phase 25 closure memo
- PR #299 — Phase 26 kickoff memo
- PR #311 — Phase 26 scope amendment R6-new-A allowlist
- PR #313 — Phase 26 R6-new-A feature-widening audit (source of §10 baseline)
- PR #315 — Phase 26 closure memo

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27)

---

*End of `docs/design/phase28_kickoff.md`.*
