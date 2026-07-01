# ML Accuracy Uplift — Experiment Contract / Design (Doc-Only)

**Status:** DESIGN-ONLY research contract. **No model is trained, no backtest /
sweep / replay is run, no feature or label is generated, no metric is
recomputed, no production or model or feature code is changed by this PR.**
**Scope key:** next research plan for improving model precision / expected
value on top of the Gate P1 PR-B.1 read-only evidence surface and the
post-audit roadmap (`docs/design/research_development_roadmap_post_audit.md`,
`docs/design/root_logic_reassessment_profit_logic_audit_design.md`).
**Date authored:** 2026-07-01.
**Branch:** `docs/ml-accuracy-uplift-experiment-contract`.
**Base:** master `4e90dd5` (post PR #381).

---

## 0. Binding constraints

This memo is a **contract for future work**. It authorises nothing executable.
It does not train models, run backtests / sweeps / replays, generate features
or labels, recompute any metric, or modify any source / script / test / data /
artifact / production / `.gitignore` / `MEMORY.md` / prior verdict memo. It does
not access broker / quote feed / credentials / env-vars / network / cloud /
OANDA API. It does not promote or demote any dataset, model, or strategy.

Every downstream research or production action named here remains gated behind
**separate explicit user authorisation** and, where applicable, behind the
§11B Root Logic Reassessment review
(`root_logic_reassessment_profit_logic_audit_design.md`).

---

## 1. Current evidence state

- **PR-B.1 candidate-span evidence is complete** for `365d_BA`, `730d_BA`, and
  `3650d_BA`, committed metadata-only under `artifacts/gate_p1_pr_b/firstrun_*`
  (PR #380 for 365d; PR #381 for 730d + 3650d).
- **All three spans:** `top_level_outcome = LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`.
- **All three spans:** retention `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`.
- **PR-B.2 is not implemented** (dependency inventory + pipeline feasibility not
  performed).
- **T2 (Gate P2 retention deposit + round-trip) is not authorised.**
- **No byte-admissibility approval exists.** No epoch is binding.
- **Consequence:** this memo is **design-only**. It **cannot** promote any
  dataset, model, or strategy. `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` is
  **not** a feasibility approval, **not** PASS, and **not** formal verification;
  it is a first-run read-only observation scoped to each candidate span, with a
  retention prerequisite still unresolved. Any experiment planned here that
  depends on a *durably retained* dataset epoch is blocked until T2 is
  separately authorised and passes; experiments that operate only on the
  existing (non-binding) local candidate data are still research-only and
  produce **no** routing authority.

---

## 2. Objective

The objective is **cost-adjusted profit quality**, not raw accuracy. Precisely,
future ML work aims to:

- improve **cost-adjusted expected value** per trade and per unit time,
- **reduce false positives** (trades taken that do not clear the cost hurdle),
- improve **pair ranking** (select the better trades across the universe),
- improve **robustness** across pairs, sessions, and regimes,
- **preserve low operational risk** (bounded turnover, bounded drawdown,
  stable execution behaviour).

### 2.1 The objective is NOT raw accuracy alone

Raw classification accuracy is explicitly insufficient and can be actively
misleading (a high-accuracy model that is right on non-monetisable moves and
wrong on the moves that matter loses money). The following are **distinct** and
must be reported and reasoned about separately:

| Quantity | What it measures | Why distinct |
| --- | --- | --- |
| Classification accuracy | fraction of correct class labels | ignores payoff asymmetry and cost |
| Directional accuracy | fraction of correct up/down calls | ignores magnitude and cost |
| Cost-adjusted expected value | net payoff after spread/slippage | the binding profit quantity |
| Trade quality | per-trade expectancy on *taken* trades | ties selection to payoff |
| Drawdown behaviour | downside path risk | operational survivability |
| Turnover / overtrading risk | trade rate vs edge | cost amplification + execution risk |

This decomposition mirrors the §11B objective-mismatch audit
(`root_logic_reassessment_profit_logic_audit_design.md` §2): a candidate that
raises a headline metric while net EV falls, or while trade rate explodes, is
**inadmissible**.

---

## 3. Baseline status

- **Phase 9.16 v9 20p remains Tier 2 `VALID_OPERATIONAL_BASELINE`.** It is
  **not** Tier 1, **not** promoted, **not** demoted by this memo.
- **No new model baseline is adopted here.** Any candidate must be compared
  against the operational baseline (and, once built, the new-epoch S-B / S-E
  comparators under Foundation T3/T4) under a committed contract — not against
  a self-selected favourable reference.
- **No archived / untrusted positive Sharpe result may be used as routing
  evidence.** Controlled-vocabulary labels (from the roadmap Appendix A) are
  preserved verbatim:
  - **+mtf v18 0.174 = `INVALID_LOOKAHEAD_NUMERIC`** (lookahead bug; not a
    number, not a threshold, not a comparator).
  - **+mtf v19 0.158 / Top-K 0.165 / C-3 0.177 =
    `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`** (Class U on
    run-provenance; admissible only as historical narrative, never as a
    pass/fail threshold or routing evidence).
  - Phase 28 §10 research baseline remains `BASELINE_NEGATIVE_OR_WEAK`; beating
    it is **not** sufficient for promotion (§8 below; §11B §7.2).

---

## 4. Candidate ML improvement families

Definitions only. **None is executed by this PR.** Each family, when
eventually run, must pass the §8 promotion gate and the §11B audit dimensions.

### A. Label / target redesign

- triple-barrier variants (upper/lower/vertical),
- ATR-normalised barrier distances (barriers scaled to local volatility),
- horizon variants (barrier vertical bound),
- **cost-adjusted labels** (a move counts as a positive only if it clears a
  spread/slippage hurdle),
- **no-trade / abstention label** (explicit third class),
- event-window exclusion labels (mask known event windows),
- **avoid labels that ignore spread/slippage** — mid-based barrier labels are
  disallowed as a primary route (repeats the Phase 9.10 cost-erasure lesson).

### B. Horizon / timeframe redesign

- M5 vs M15 as the primary bar,
- 15 / 30 / 60-minute target horizons,
- multi-horizon target stacking (predict several horizons, combine),
- separate models per horizon vs a shared model with horizon as a feature,
- **avoid returning to M1 scalping as the primary route unless separately
  justified** — M1 scalping historically loses the edge to spread first.

### C. Feature improvement

- multi-timeframe trend features (causal, shifted; no lookahead — the v18 bug),
- volatility regime features (ATR percentile, realised-vol clustering),
- session features (Asia / London / NY, overlap),
- spread / slippage features (once P2 supplies observed spread),
- distance-to-high / distance-to-low features,
- Donchian / breakout / mean-reversion features,
- pair-relative and currency-strength features (note: CSI as Layer-1 features
  was `NO ADOPT` at Phase 9.16 due to redundancy with `xp_*`; any revival must
  justify non-redundancy),
- regime-transition features.

### D. Model family comparison

- **LightGBM as the primary baseline** (continuity with the operational stack),
- CatBoost / XGBoost comparison **only under a controlled, identical
  data/label/cost contract** (no cherry-picking),
- a **calibration layer** (isotonic / Platt) so scores are probability-faithful,
- a **ranker model** for pair selection (learning-to-rank objective),
- a **meta-labeling model** (second-stage filter on first-stage signals).

### E. Selection / ranking improvement

- per-pair expected value estimation,
- cross-pair Top-K selection (with the Phase 9.19 rank-inversion caveat),
- correlation-aware selection (avoid concentrated correlated exposure),
- abstention threshold (decline low-confidence bars),
- trade-frequency cap (bound turnover),
- uncertainty filter (decline high-variance predictions).

### F. Regime / session filtering

- Asia / London / NY session filters,
- trend vs range classification,
- volatility percentile filter,
- spread percentile filter,
- **news / event windows as deterministic filters first** (calendar-driven,
  reproducible),
- **LLM features only as a later optional feature family (§9), not immediate
  execution.**

### G. Cost realism

- live spread snapshot integration **pending P2 / P1 gates** (P2 observes; P1
  changes the cost model — both separately authorised),
- spread-percentile-aware cost,
- slippage stress testing,
- commission / spread hurdle inside the evaluation,
- **reject any experiment whose edge disappears after conservative cost
  stress** (§8 kill criteria).

### H. Validation / leakage controls

- walk-forward validation,
- purged time-series split,
- embargo between train and test,
- pair-level robustness (no single-pair dependency),
- session-level robustness,
- **no training on future spread or future labels**,
- **no leakage through resampling or feature alignment** (all features causal /
  shifted; the v18 `_add_multi_tf_extended_features` missing-`shift(1)` bug is
  the canonical failure to prevent),
- **no same-period tuning/evaluation reuse** (tuning set ≠ evaluation set).

---

## 5. Metrics

Metric hierarchy. **No metric is computed in this PR.**

### 5.1 Primary

- **net expected pips after cost**,
- **trade-level expectancy** (per-trade EV on taken trades),
- **OOS robustness** (holdout / walk-forward consistency),
- **drawdown / downside risk**,
- **pair-ranking stability** (rank correlation across folds),
- **false-positive reduction** (cost-hurdle-failing trades avoided).

### 5.2 Secondary

- directional accuracy,
- AUC / logloss,
- calibration (reliability curve, Brier),
- precision at Top-K,
- trade count,
- turnover.

### 5.3 Bindings

- **Raw accuracy alone is insufficient** to promote anything (§2.1).
- **Sharpe-like metrics must be computed only under a committed contract**
  (§7): fixed data span, code SHA, feature-set hash, label-contract hash, cost
  contract, seed. An uncommitted or ad-hoc Sharpe number is **not** admissible
  (repeats the Class-U lesson).
- **No new metric is computed in this PR.**

---

## 6. Experiment sequencing

A safe, gated sequence. Each step requires **separate explicit authorisation**;
this memo authorises only that Step 1 (this doc) exists.

- **Step 0 — complete PR-B.2** (dependency inventory + pipeline feasibility),
  read-only, if/when separately authorised. Establishes what inputs each
  consumer needs and whether the pipeline is namespace-parameterisable for a
  new epoch. Not required to *author* this contract, but required before any
  real research run that depends on the pipeline.
- **Step 1 — doc-only experiment contract (THIS PR).**
- **Step 2 — implementation-only experiment harness, no model run.** Code +
  tests on synthetic fixtures; the harness can construct labels/features/metrics
  deterministically but is *not run on real data* and trains no model. Mirrors
  the PR-B.0/PR-B.1 "infra first, evidence later" discipline.
- **Step 3 — small dry-run on fixture / synthetic data only.** Proves the
  harness end-to-end without real data; produces committed synthetic-run
  evidence, no routing claim.
- **Step 4 — first real read-only research run on ONE approved candidate span
  only**, after explicit authorisation, with committed metadata/metrics
  artifacts (no temp-only, no oral-only). Subject to the §7 evidence contract
  and §11B review.
- **Step 5 — expand to all candidate spans** only after the Step-4
  evidence/provenance pattern is demonstrably clean.
- **Step 6 — compare ML-only vs ML+LLM feature families (§9)** later, only
  after an ML-only baseline is stabilised and committed.

Where a step depends on a durably retained epoch, it is additionally gated on
**T2** (retention) and, for cost-model changes, on **P1** (which is gated on
**P2** observation).

---

## 7. Required evidence for future experiment PRs

Every future experiment PR that claims a run must commit, per run:

- **exact data span** (e.g. `365d_BA`),
- **exact code SHA** used to generate the run,
- **exact feature-set hash**,
- **exact label-contract hash**,
- **exact cost contract** (spread/slippage/commission assumptions),
- **model config** (hyperparameters),
- **random seed**,
- **output artifacts** (predictions/selection summary as metadata, not raw
  rows),
- **metrics report**,
- and must contain **no uncommitted local-only result claims, no temp-only
  results, and no oral-only claims.**

**If a real run is claimed, committed metadata/report artifacts are required.**
This is the direct generalisation of the PR-B.1 lesson (a run without committed,
provenance-stamped evidence recreates the Class-U / missing-provenance pattern).
Committed reports must remain metadata-only: **no raw candle/quote rows, no full
raw payloads, no credentials/secrets/env values, no local absolute paths, no
model-weight dumps**, and must not assert PASS / `FORMALLY_VERIFIED` / Tier-1 /
`SENTINEL_VERIFICATION_COMPLETE` / byte-admissibility / T2 authorisation /
new-epoch adoption / production claims unless separately authorised.

---

## 8. Promotion / kill criteria

Conservative, aligned with §11B §4.2 / §10.

### 8.1 A promotion candidate REQUIRES all of

- OOS improvement vs the operational baseline (and vs new-epoch S-B/S-E once
  built),
- **positive cost-adjusted expectancy** under a conservative cost contract,
- robustness across pairs,
- robustness across sessions,
- **no single-pair dependency** (result survives removing the top contributor),
- acceptable drawdown,
- acceptable turnover,
- **no leakage finding**,
- reproducible committed artifacts (§7),
- **explicit human review before adoption.**

### 8.2 Kill criteria — a candidate is KILLED if any of

- improvement disappears after cost stress (`COST_ERASED_EDGE`),
- it works on only one pair or one session (`PAIR_CONCENTRATION` /
  `REGIME_INSTABILITY`),
- high turnover / overtrading (`TRADE_RATE_EXPLOSION`),
- unstable Top-K ranking (`RANKING_INVERSION`),
- poor calibration,
- evidence missing (`CLASS_U_RUN_PROVENANCE`),
- leakage suspicion (`LEAKAGE_OR_CAUSALITY_FAILURE`),
- reliance on archived / untrusted numeric results as routing evidence
  (`ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`).

Killed candidates are not retried under the same shape without a new design
memo.

---

## 9. LLM features (deferred)

- **LLM must not be used first as a direct predictor** of price/direction.
- If used later, use it as a **feature generator** for: event risk, news-shock
  risk, currency bias, regime classification, no-trade reason.
- LLM features must be **logged as immutable feature snapshots** (prompt +
  model id + timestamp + output), so a run is reproducible from the snapshot
  rather than a live call.
- LLM features must be **compared against the ML-only baseline** (they must earn
  their place; no free adoption).
- **LLM API calls and prompts require their own reproducibility / provenance
  contract** (analogous to §7), including immutable prompt/version pinning.
- **No LLM integration is authorised in this PR.**

---

## 10. Non-authorisations

This PR does **not** authorise:

- model training,
- backtests,
- feature implementation,
- label implementation,
- metric recomputation,
- production routing,
- live trading,
- paper trading,
- P1 / P2 / P3 implementation,
- T2 execution,
- T3 / T4,
- byte-admissibility approval,
- new-epoch adoption,
- Track A / B / C / D / E / F / G execution,
- LLM API integration.

---

## 11. Status carry-forward

- **Phase 9.16 v9 20p:** Tier 2 `VALID_OPERATIONAL_BASELINE`, preserved
  (neither promoted nor demoted).
- **PR-B.1 evidence surface:** complete (365d/730d/3650d, all PARTIAL,
  retention-probe-required); unchanged.
- **PR-B.2:** not implemented; unchanged.
- **T2 / T3 / T4:** not authorised; unchanged. `T2_PROPOSED_DESTINATION_PLAN`
  (PR #378) remains planning-layer only, pending explicit T2 execution
  authorisation.
- **P1 / P2 / P3:** not authorised. §11B / P2 designs remain design-only.
- **Controlled-vocabulary numeric labels** (INVALID_LOOKAHEAD_NUMERIC /
  ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING / BASELINE_NEGATIVE_OR_WEAK):
  unchanged.
- **A0-broad β halt; A0-narrow / A2-narrow FALSIFIED bindings; Phase 27 / 28 /
  29.0a / 9.10..9.X-O verdicts:** unchanged.
- **Routing authority granted by this PR:** none.

End of contract.
