# §11B Root Logic Reassessment / Profit Logic Audit — Design (Doc-Only)

**Status:** DESIGN_ONLY — operationalises roadmap §11B as a diagnostic framework
specification. **No experiment is run, no model is invoked, no Sharpe is
recomputed, no data is read, no production state is changed under this PR.**
**Scope key:** Roadmap §11B
(`docs/design/research_development_roadmap_post_audit.md`).
**Date authored:** 2026-06-22.
**Branch:** `docs/p2-root-logic-design`.

---

## 0. Binding constraints (apply to this PR and to any future audit
implementation chain seeded by this design)

This design PR introduces a **diagnostic framework specification**. It does
**not** authorise:

- experiment execution
- model invocation
- backtest re-runs
- Sharpe / IC / MI recomputation
- raw data read
- broker / quote feed access
- credentials / env-var read
- order placement
- production loop change
- artifact creation
- modification of `.gitignore`
- modification of `MEMORY.md`
- modification of prior verdict memos
- promotion or demotion of any phase verdict
- promotion or demotion of any production baseline
- A0-broad β unhalt
- A0-narrow / A2-narrow verdict change

§11B is **not** a research execution surface. It is the **gate** that future
non-observational research must pass through.

---

## 1. Objective

Operationalise the Root Logic Reassessment / Profit Logic Audit framework
named in roadmap §11B so that, **before any future non-observational research
execution, P1 selector/cost-model change, Track A / D / C execution, or
production-impacting change**, the operating logic of profit is **diagnostically
examined** — not by running a new model, but by structurally testing the chain:

```
train objective
  -> label / target choice
    -> selector / ranking mechanism
      -> cost hurdle / execution realism
        -> trade unit / horizon
          -> baseline comparator
            -> alpha upper bound / oracle
              -> root-cause taxonomy classification
                -> kill / escalation decision
```

If any link in this chain fails an admissibility check, downstream tracks **must
not** be authorised, regardless of how positive a candidate's headline metric
looks.

### 1.1 Why this exists

Roadmap §11B states the **historical failure pattern**: positive headline
metrics (Sharpe 0.158 / 0.165 / 0.174 / 0.177) repeatedly fell to one or more
of:

- lookahead bug (Phase 9.X-B v18 → v19)
- Class U on run-provenance (Phase 27 §10 audit U-1/U-2)
- cost-erased edge (Phase 9.10, Phase 9.X-J/L/M realism series)
- ranking inversion (Phase 9.19 Top-K rank-3)
- per-trade EV collapse with trade-rate rise (Phase 9.17, 9.17b, 9.X-A)
- negative immutable research baseline (Phase 28 §10 test −0.1732 / val −0.1863)

§11B exists to ensure these patterns are **examined before**, not discovered
after, the next round of expensive execution. It is a **structural** gate, not
an advisory commentary.

### 1.2 Scope discipline

§11B does **not** replace Foundation Track T1 / T2 / T3 / T4. Foundation T-stages
are sequencing constraints on **data, retention, and baseline construction**.
§11B is a diagnostic framework over the **logic of profit**.

§11B itself **authorises no experiment and no production change**. It is a
design surface that future tracks must satisfy.

---

## 2. Audit dimension 1 — Objective mismatch audit

### 2.1 What the audit examines

For any candidate (model / selector / strategy) under consideration:

- the **train objective** (e.g. binary classification of label sign, regression
  on `label_return`, ranking loss)
- the **validation selector** (e.g. argmax by score, Top-K, threshold-based)
- the **headline ranking metric** (e.g. AUC, IC, Spearman)
- the **gross Sharpe** of the selected trades
- the **net Sharpe** at a realistic cost assumption
- the **annualised PnL**
- the **per-trade EV**

### 2.2 What evidence would show objective mismatch

**Mismatch is positively shown** when:

- gross Sharpe rises while net Sharpe falls (cost-erased edge),
- headline ranking metric rises while selected-trade EV falls (ranking inversion),
- AUC / IC rises while annualised PnL falls (selector-level mismatch),
- the train objective optimises a quantity that the selector does not consume
  (e.g. regression MAE while selector uses argmax of a transformed score).

### 2.3 Reporting requirement for future tracks

Any future track that proposes a model / selector change must, **in its design
memo and in its closure memo**, explicitly report:

- train objective formula,
- selector rule formula,
- the **link** between the two,
- gross vs net Sharpe,
- per-trade EV at the selected-trade subpopulation,
- annualised PnL.

A track that does not report this linkage is **inadmissible** under §11B,
regardless of headline metric.

### 2.4 Diagnostic-only

This subsection defines the audit. **No quantity is computed by this PR.**

---

## 3. Audit dimension 2 — Label / target logic audit

### 3.1 What the audit examines

For any candidate label / target:

- direction prediction vs trade / no-trade prediction vs return magnitude
  prediction vs exit-aware profit (TP/SL-conditioned) vs risk-adjusted profit
  (per-trade EV / variance),
- whether the **cost hurdle** is inside the label (e.g. `label_return ≥ cost_pip`)
  or applied at the selector or applied as post-filter,
- class imbalance (positive / negative / no-trade fractions),
- false-positive cost: a label that predicts "trade" too often will be
  cost-erased even with positive IC.

### 3.2 Audit checks

- class balance per pair and per regime,
- per-trade EV at the **labelled-as-trade** subpopulation (irrespective of model),
- whether the label leaks information beyond the candidate feature horizon,
- whether the label is path-dependent in a way the model architecture cannot
  consume (e.g. exit-conditioned label fed to a non-path-aware model).

### 3.3 Relation to Track E (A2-broad target redesign)

Track E (A2-broad target redesign) is a candidate target redesign track. §11B
does **not** authorise Track E. §11B requires that any Track E proposal
satisfy §3.2 audit checks in its design memo before execution authorisation is
considered.

### 3.4 Diagnostic-only

This subsection defines the audit. **No label is generated, no signal is
generated, by this PR.**

---

## 4. Audit dimension 3 — Selection / ranking logic audit

### 4.1 What the audit examines

- **rank monotonicity by decile**: is selected-trade EV monotonically increasing
  in score decile? (Phase 9.19 documented inverted rank-3 EV; this audit
  detects that pattern.)
- **Top-K rank EV curve**: for K=1,2,3,..., is per-trade EV stable, rising, or
  inverting?
- **calibration**: does the score correspond to a probability that matches
  realised outcome frequency?
- **per-pair overlap**: is the Top-K selection diversified across pairs, or
  concentrated on a small subset? (Phase 9.19 noted systemic pair correlation
  defeating sqrt(K) lift.)
- **score distribution stability** across train / val / test.
- **cost-adjusted selected-trade PnL by rank**: which rank tiers survive after
  cost is subtracted?

### 4.2 Promotion gate (binding)

No selection mechanism (selector / ranker / Top-K rule / threshold filter) may
be promoted to a production candidate unless:

- rank monotonicity passes a defined check (sign-consistent EV across deciles,
  threshold to be pinned in the future implementation chain), **and**
- selected-trade EV survives **cost-adjusted** validation against a baseline
  that itself is not negative.

This is a **structural promotion gate**. A candidate that fails either check
cannot be promoted by waving the headline metric.

### 4.3 Diagnostic-only

§11B specifies the gate. **No score is computed by this PR.**

---

## 5. Audit dimension 4 — Cost hurdle / execution realism audit

### 5.1 What the audit examines

- **edge vs cost**: is the per-trade edge smaller than the spread + slippage
  for the relevant pair / session?
- **where does cost live**: inside the label, inside the selector, or as a
  post-filter?
- **dynamic cost hurdle** by pair / session: does a single fixed-pip hurdle
  systematically over- or under-state cost for some pairs?
- **relationship to P2 / P1 / P3**:
  - **P2** (live spread snapshotting design,
    `p2_live_spread_snapshotting_design.md`) supplies the **observational
    baseline** that this audit consumes.
  - **P1** (cost-model replacement) is the **change** that this audit gates.
  - **P3** (cost-aware sizing) is the **downstream** action whose authorisation
    requires P1 first.

### 5.2 Specific check forms

- compare gross Sharpe at 0 cost vs net Sharpe at 0.5 pip and 1.0 pip slippage
  (Phase 9.10 documented gross 0.35 → net −0.076 at 1.0 pip),
- per-pair cost-erasure check: which pairs have edges smaller than spread?
- per-session cost-erasure check: which sessions have edges smaller than
  spread?

### 5.3 Binding

If the audit identifies `COST_ERASED_EDGE` (§8), the candidate **must not** be
escalated to production change irrespective of gross Sharpe.

### 5.4 Diagnostic-only

§11B specifies the audit. **No backtest is run by this PR. No raw quote is
read by this PR.**

---

## 6. Audit dimension 5 — Trade unit / horizon audit

### 6.1 What the audit examines

- **timeframe alignment**: does the candidate operate at M1 / M5 / M15 / H1 / D1,
  and is its label horizon consistent with the feature horizon?
- **holding period vs feature horizon**: a model trained on M15 features but
  intended to fire trades at M1 cadence is mismatched.
- **TP / SL and partial exit consistency**: does the TP / SL geometry match the
  realised holding period distribution?
- **direction prediction vs path-aware trade outcome**: is the model predicting
  end-of-window sign while the trade actually exits via path-dependent TP / SL?
  (Phase 9.18 documented 80% SL-before-partial rate under H-2.)

### 6.2 Reporting requirement for future tracks

Any future track must explicitly state the (feature horizon, label horizon,
holding period, TP/SL geometry) tuple, and any inconsistency must be flagged
in the track design memo.

### 6.3 Diagnostic-only

§11B specifies the requirement. **No trade is simulated by this PR.**

---

## 7. Audit dimension 6 — Baseline and comparator audit

### 7.1 Baselines

- **new-epoch S-B**: the V2-expanded `S-B` sentinel comparator — to be
  constructed under Foundation T3 (new epoch baseline + control) per roadmap §5.
  Until T3 produces it, S-B is `NOT_AVAILABLE_FOR_ROUTING`.
- **new-epoch S-E**: the V2-expanded `S-E` sentinel — same condition as S-B.
- **cash / no-trade baseline**: always available; admissibility floor.
- **production Phase 9.16 v9 20p operational baseline**: VALID_OPERATIONAL_BASELINE
  (Tier 2), retained per roadmap §3. Used **where applicable** for production
  comparisons.
- **cost-adjusted hurdle baseline**: a candidate must beat the cost hurdle
  baseline, not merely the gross baseline.

### 7.2 Explicit binding

**Beating a negative research baseline is not sufficient.** Phase 28 §10
research baseline is NEGATIVE (test −0.1732 / val −0.1863 / ann_pnl
−204,664.4 per `phase27_closure_memo.md:34`). A candidate that "beats" Phase 28
§10 is not, by that fact alone, admissible. It must additionally:

- beat cost-adjusted hurdle baseline,
- pass selection / ranking gate (§4.2),
- pass cost-hurdle audit (§5.3),
- not be Class U on run-provenance (§8 `CLASS_U_RUN_PROVENANCE`).

### 7.3 Diagnostic-only

§11B pins the binding. **No baseline is computed by this PR.**

---

## 8. Audit dimension 7 — Alpha upper-bound / oracle diagnostics

### 8.1 Diagnostic surfaces (designs only)

Each surface is **defined here**, not computed here:

- **cost-free oracle**: ideal selector that picks the best trade per bar
  ignoring cost. Upper bound on possible PnL.
- **cost-adjusted oracle**: ideal selector that picks only trades whose
  realised payoff exceeds cost. Upper bound on realistic PnL.
- **per-pair oracle**: per-pair upper bound; isolates per-pair monetisability.
- **per-regime oracle**: per-regime upper bound; isolates regime-specific
  monetisability.
- **perfect-rank oracle**: assumes perfect score ranking with a fixed selector;
  isolates whether failure is from selection or from prediction.
- **label separability**: are positive and negative labels separable in the
  feature space? Diagnostic for `NO_SIGNAL` (§8 taxonomy).
- **IC / MI**: information coefficient and mutual information between score
  and outcome. Diagnostic for `SIGNAL_NON_MONETISABLE`.
- **score-to-PnL monotonicity**: per-decile selected-trade PnL after cost.
- **per-pair contribution decomposition**: which pairs contribute the realised
  PnL? Concentration test for `PAIR_CONCENTRATION` (§8).
- **per-regime contribution decomposition**: which regimes contribute the
  realised PnL? Stability test for `REGIME_INSTABILITY` (§8).

### 8.2 Binding

- **Designs only.** **Do not compute any of these in this PR.**
- A future track may not be escalated to neural architecture (or any
  expensive class change) if the diagnostic surface — once an
  authorised computation chain produces it — shows no monetisable
  alpha (see §9 kill criteria).

### 8.3 Output shape (when these are eventually computed under separate
authorisation)

Each diagnostic produces a small table per (pair, regime, decile) cell, plus a
summary line per dimension. No model is trained by this audit; the oracles
operate on the **label / cost** structure, not on a model fit.

---

## 9. Audit dimension 8 — Root-cause taxonomy

A candidate failure must be classified into one or more of the following
labels (mirrors roadmap §11B taxonomy):

| Label | Meaning |
| --- | --- |
| `NO_SIGNAL` | Score has no information about outcome (IC ≈ 0, MI ≈ 0). |
| `SIGNAL_NON_MONETISABLE` | Score has information but cannot convert to net PnL after cost. |
| `COST_ERASED_EDGE` | Gross edge exists but is smaller than spread / slippage. |
| `RANKING_INVERSION` | Top-K rank EV is non-monotonic or inverted (e.g. Phase 9.19 rank-3 −0.054). |
| `TRADE_RATE_EXPLOSION` | Trade count rises sharply, headline metric collapses (Phase 9.17 / 9.17b / 9.X-A). |
| `PER_TRADE_EV_COLLAPSE` | Per-trade EV falls below cost hurdle while trade rate is non-trivial. |
| `REGIME_INSTABILITY` | Edge survives only in one regime; out-of-regime performance is negative or flat. |
| `PAIR_CONCENTRATION` | PnL is concentrated in 1–2 pairs; portfolio claim does not survive removing them. |
| `LEAKAGE_OR_CAUSALITY_FAILURE` | Lookahead or feature causality bug (Phase 9.X-B v18). |
| `CLASS_U_RUN_PROVENANCE` | Run provenance fails admissibility (Phase 27 §10 U-1/U-2). |
| `BASELINE_NEGATIVE_OR_WEAK` | Candidate only beats a negative or weak baseline. |
| `OVERFITTED_SELECTOR` | Selector is fit to in-sample particulars; OOS rank monotonicity breaks. |
| `EXECUTION_CONSTRAINT_FAILURE` | TP/SL geometry, partial exit, or order placement constraint defeats expected payoff. |

A future track's closure memo must classify any negative result into one or
more of these labels.

---

## 10. Kill criteria and escalation criteria

### 10.1 Kill criteria (binding)

The candidate is **killed** (not promoted, not retried under the same shape)
if any of the following holds, once a separately authorised computation chain
produces the relevant diagnostic:

- cost-adjusted selected-trade EV is negative,
- rank monotonicity fails (§4.2),
- per-trade EV collapses while trade count rises (`PER_TRADE_EV_COLLAPSE` +
  `TRADE_RATE_EXPLOSION`),
- candidate only beats a negative research baseline (§7.2),
- run provenance is Class U (`CLASS_U_RUN_PROVENANCE`).

### 10.2 Escalation criteria (binding)

The candidate **must not** be escalated to a heavier model class (e.g. neural
architecture, LSTM Mode B-1/B-2/B-3/B-4, MoE under Track F) if:

- the alpha upper-bound / oracle diagnostic (§8), once produced under separate
  authorisation, shows no monetisable alpha at the current label / cost
  configuration,
- the cost hurdle audit (§5) shows `COST_ERASED_EDGE` at the relevant pair /
  session set,
- the baseline audit (§7) shows the candidate beats no admissible baseline.

### 10.3 Routing evidence binding

A Class U result is **inadmissible** as routing evidence. This restates the
roadmap §3 binding for `CLASS_U_RUN_PROVENANCE`. §11B does not lift it.

### 10.4 Diagnostic-only

§11B specifies the criteria. **No kill / escalation decision is taken by this PR.**

---

## 11. Relationship to future work

### 11.1 §11B does not replace Foundation T1–T4

- **T1**: production keep-alive — independent of §11B.
- **T2**: Gate P1 PR-B authority anchor — independent of §11B.
- **T3**: Gate P2 retention — independent of §11B.
- **T4**: new-epoch baseline + control (S-B / S-E construction) — feeds §7.1
  baseline list but is owned by T-stages, not §11B.

§11B operates **on top of** Foundation. Foundation pins data / retention /
baseline construction. §11B pins **profit logic admissibility**.

### 11.2 §11B must be reviewed before:

- any P1 selector / cost-model change is authorised,
- any Track A re-evaluation execution (PR #354 allowlist S1+S2+S3) is
  authorised,
- any Track D data-side expansion that affects the cost / horizon surface is
  authorised,
- any Track C residual LSTM execution (B-1 / B-2 / B-3 / B-4) is authorised,
- any production-impacting change is authorised.

Review means: the track's design memo must explicitly map onto §11B audit
dimensions §2–§9, and the track's closure memo must explicitly classify
results under §8 taxonomy and apply §10 kill / escalation rules.

### 11.3 §11B may be co-authored with P2

P2 (live spread snapshotting) is **observational**. §11B is **diagnostic /
specification**. Co-authoring them in this single PR is consistent with the
no-execution binding of both surfaces.

### 11.4 §11B itself authorises no experiment and no production change

This is the **strongest binding** of this document. §11B is a gate, not a
gate-opener.

---

## 12. Open questions deferred

1. Decile / Top-K cutoff thresholds for the rank monotonicity check.
2. Cost-adjusted hurdle pip values per pair (decision depends on P2 output).
3. Exact form of the operator signoff / promotion docs PR for any candidate.
4. Whether §11B audit results are themselves committed as artifacts, or live
   only in closure memos.
5. Whether the oracle diagnostics (§8) are produced once per epoch, or per
   candidate.
6. Whether per-regime decomposition uses the existing regime classifier
   (ATRRegimeClassifier, etc.) or a new one introduced by Track G.
7. Cadence of §11B re-review when production baseline updates.
8. Whether §11B audit is required for purely observational / measurement
   changes (default: no — observational changes do not need §11B; only
   non-observational research and production-impacting change do).
9. How §11B interacts with H-B9 seam-exhaustion working hypothesis from
   roadmap §4.4.
10. Whether §11B failure of an existing production component triggers a
    rollback proposal (default: §11B does not own production rollback; it
    raises a finding that a separate PR may act on).

---

## 13. Status carry-forward

- **§11B framework status after this PR merges:** `DESIGNED_NOT_OPERATIONALISED_ON_CANDIDATES`.
- **P1 status after this PR merges:** unchanged, gated on P2 observation **and**
  §11B review.
- **Track A / C / D status after this PR merges:** unchanged, gated on §11B
  review at design memo time.
- **Foundation T1 / T2 / T3 / T4 status after this PR merges:** unchanged.
- **Phase 9.16 v9 20p production baseline status:** unchanged, Tier 2
  `VALID_OPERATIONAL_BASELINE` preserved.
- **A0-broad β halt:** unchanged.
- **A0-narrow / A2-narrow FALSIFIED bindings:** unchanged.
- **Phase 27 / 28 / 29.0a verdicts:** unchanged.
- **Phase 9.13 / 9.15 / 9.16 / 9.17 / 9.17b / 9.18 / 9.19 / 9.X-A / 9.X-B / 9.X-C
  M-1 / 9.X-D / 9.X-J / 9.X-L / 9.X-M / 9.X-N / 9.X-O verdicts:** unchanged.
- **Routing authority granted by this PR:** none.

End of design.
