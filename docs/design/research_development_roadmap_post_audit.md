# Research and development roadmap — post Phase 27-29 audit and V2-expanded HALT

**Status:** Doc-only development roadmap memo. Authored under the
contract of `docs/design/phase27_29_tabular_eval_validity_audit.md`
(PR #356), `docs/design/tabular_evidence_epoch_rebase_routing_memo.md`
(PR #360), `docs/design/new_provenance_bound_dataset_epoch_design.md`
(PR #361), `docs/design/gate_p1_feasibility_inspection_protocol.md`
(PR #362 + Amendment 1 from PR #363),
`docs/design/gate_p1_pr_b_implementation_plan.md` (PR #365), and
`docs/design/gate_p2_retention_destination_evaluation_memo.md`
(PR #366). At `master @ e78f051`.

**Base:** master `e78f051` (post PR #366 merge)
**Branch:** `docs/research-development-roadmap-post-audit`
**File added:** `docs/design/research_development_roadmap_post_audit.md`

**Amendment history:**

- Amendment 3 (this PR): residual-contradiction cleanup of
  Amendments 1 + 2. (a) §5.5 T4 Scope had retained "or stricter
  `SENTINEL_VERIFICATION_COMPLETE` if all sentinels pass" which
  contradicted the Exit-criteria binding immediately below; the
  Scope wording is now aligned with the Exit-criteria binding.
  (b) §11.Q9 retained "e.g., A.1 Sharpe ≥ 0.158 on new epoch" as
  a Tier-1 success example; the numeric example is removed and
  replaced with "produces a Tier-1 verdict against the new-epoch
  S-B baseline and S-E control". (c) §3 status-table entries
  Phase 9.X-C Mode B-2, Phase 9.X-D +dxy alone, Phase 9.X-D
  +dxy+mtf had retained archival comparisons against the
  now-INVALID v18 mtf anchor (0.174); these are restated as
  archival phase-closure context only, with no active-comparator
  role. (d) §4.4 H-B9 Track-C outcome wording softened: success
  "would materially weaken H-B9 under the tested scope"; failure
  "would strongly support H-B9 under the current-data /
  current-contract scope"; neither outcome alone declares an
  absolute production ceiling; production-ceiling or
  structural-ceiling conclusions require separate strategic
  review. (e) §7 P1 Phase 9.10 cost-sensitivity wording revised:
  Phase 9.10 evidence is historical / operational
  cost-sensitivity context (Tier 3); it is not Tier-1 verified
  research evidence; P1/P2/P3 remain production-engineering
  priorities subject to design memo, backtest/paper, and safety
  gates. (f) Full numeric-reference audit completed (0.174 /
  0.158 / 0.165 / 0.177 / 0.061 / 0.154 / 0.168 / PARTIAL GO+ /
  verified / production ceiling / SENTINEL_VERIFICATION_COMPLETE);
  each remaining occurrence is either removed, demoted to
  archival / invalid / untrusted / non-routing context, or
  authorised under controlled vocabulary.
- Amendment 1 + 2 (this PR): combined application of (a) the 11
  structural fixes earlier requested by user review (T3/T4
  separation, retraction of unapproved `SENTINEL_VERIFICATION_COMPLETE`
  label, Tier 1 language tightening, Track A outcome ladders
  reframed as illustrative-only, T4 staged-verification binding,
  H-B9 wording softening, Track D external-data provenance gate,
  Production P1/P2/P3 risk wording, Track B decision table,
  T1/T2 parallelism clarification with T2 deposit ≠ epoch adoption,
  §12 carry-forward precision), and (b) the evidence reconciliation
  appendix and corresponding numeric-claim demotion: +mtf v18 Sharpe
  0.174 reclassified as `INVALID_LOOKAHEAD_NUMERIC` per
  `sharpe_improvement_brief.md` lookahead bug citation; +mtf v19
  Sharpe 0.158 reclassified as `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_
  USE_FOR_ROUTING` (class U + numeric reduced from a now-invalid v18
  anchor); Top-K K=2 Sharpe 0.165 reclassified as
  `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`; C-3 Sharpe
  0.177 reclassified as `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_
  ROUTING`; LSTM Mode A Sharpe 0.061 remains `FALSIFIED_AT_SCOPE`
  but explicitly does not falsify B-1..B-4 nor the A0-broad
  sequence-NN allowlist; Phase 9.16 v9 20p Sharpe 0.160 remains
  `VALID_OPERATIONAL_BASELINE`. Track A.1 / A.2 / A.3 reframed as
  **from-scratch feature-family re-evaluations under new epoch**
  (old numerics archived context only; no production reflection
  auto-authorised). §4.2 extraction-vs-expansion principle demoted
  from "verified success" wording to "working hypothesis with
  empirical falsification surface support; not a binding verdictable
  claim". §12 explicitly states that old +mtf / Top-K / C-3 numerics
  are not admissible routing evidence and that no prior Phase
  9.X-B PARTIAL GO / PARTIAL GO+ survives as verified or production-
  relevant evidence unless re-executed under the new foundation
  contract. Appendix A added (evidence-status table with controlled
  vocabulary + per-numeric source citations).

This document is a **doc-only research and development roadmap**. It
does not authorise the execution of any track listed within it. Per
the §1.B and §11 bindings of PR #361 / PR #362 / PR #365, every named
research track and every named Foundation stage requires **separate
explicit user authorisation** before its implementing PR is authored.

The memo exists because the prior roadmap implicit in conversation
("verified-but-not-shipped: +mtf, Top-K, C-3") was discovered to be
incorrect: Phase 27-29 audit (PR #356) found the run-provenance
artifacts for those evaluations gitignored uniformly, the V2-expanded
Stage 2 preflight halted at `HALTED_INPUT_UNAVAILABLE` (PR #360), and
the lookahead bug in `_add_multi_tf_extended_features` v18 reduced the
Phase 9.X-B Sharpe claim from 0.174 to 0.158 under v19 causal fix. The
practical implication is that **no PARTIAL GO / PARTIAL GO+ verdict
from Phase 9.13 onward is "verified" in the strict sense the next
production-deployment decision requires**.

The roadmap below restores a single shared map of (a) what is
actually verified to which depth, (b) what Foundation work is required
before any further verification can be claimed, (c) what Research
tracks are eligible to be revived under that Foundation, and (d) what
Production-side improvements are independent of the verification
layer and can be progressed in parallel without contamination.

---

## §1 Purpose / Scope / Non-scope

### Purpose

To produce a single, locked, reviewer-tractable roadmap that:

- writes back the **five-tier verified surface** that emerged from
  PR #356 audit (FORMALLY_VERIFIED / CONTEMPORANEOUS_CONTRACT_PASS /
  TARGETED_VERIFICATION_REQUIRED / FALSIFIED / DEFERRED_NOT_FORECLOSED)
- enumerates **every research line that has been attempted** in Phase
  9.x and Phase 27-29 with its current status (tried-and-falsified vs
  tried-but-class-U vs untried) so that future decisions are not
  re-discovering known dead ends or claiming "verified" for class-U
  results
- defines a **Foundation Track** (T0..T4) that must complete before
  any new "verified" claim is admissible
- defines **Research Tracks** (A..G) eligible under Foundation
  completion, including the previously-deprioritised Phase 9.X-C LSTM
  modes (B-1, B-2, B-3, B-4) and the A0-broad sequence-NN allowlist
  (S1 LSTM / S2 Temporal CNN / S3 Transformer) per PR #354
- defines **Production-Improvement Tracks** (P1..P3) that are
  independent of the verification layer and can progress without
  introducing class-U contamination into production
- enumerates **risks, stage gates, and open questions** that must be
  resolved before each track is authorised

### Scope

The memo binds:

- §2: the five-tier verified surface and per-tier admissible language
- §3: a comprehensive per-phase per-mode status table covering
  Phase 9.x and Phase 27-29
- §4: development philosophy (extraction vs expansion principle,
  H-B9 seam-exhaustion hypothesis, foundation-first sequencing,
  class-U recurrence prevention)
- §5: Foundation Track T0..T4 with stage gates
- §6: Research Tracks A..G with per-track scope, prerequisites,
  authoring-PR shape, and pass/fail criteria
- §7: Production-Improvement Tracks P1..P3
- §8: Cross-track resource accounting and sequencing constraints
- §9: Risk register
- §10: Stage gates (mandatory exit criteria per Foundation stage)
- §11: Open questions requiring user judgment before track
  authorisation

### Non-scope

The memo explicitly **does not**:

- authorise any track. Every Foundation stage and every Research
  track listed below requires explicit user instruction before its
  implementing PR is authored. Merging this memo PR does not
  authorise anything.
- modify any prior verdict. Phase 27 / 28 / 29.0a verdicts remain as
  recorded. A0-broad β remains halted (PR #356). A0-narrow remains
  FALSIFIED_A0_NARROW. A2-narrow remains FALSIFIED_A2_NARROW. Phase
  9.13..9.X-D PARTIAL / NO ADOPT verdicts as captured in their
  closure memos remain in their then-recorded class.
- claim any new "verified" status for any Phase 9.x result. The
  +mtf v19 causal Sharpe 0.158, Top-K K=2 Sharpe 0.165, and any
  pre-Phase-9.16 baselines (incl. C-3 0.177) are at
  TARGETED_VERIFICATION_REQUIRED at minimum; per the Appendix A
  evidence reconciliation, they are demoted to
  `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` for the
  specific purpose of admissibility as production-routing /
  pass-fail-threshold evidence. The +mtf v18 Sharpe 0.174 is
  reclassified as `INVALID_LOOKAHEAD_NUMERIC`.
- select a Gate P2 retention destination. PR #366 evaluation memo's
  default recommendation (D3 R2 + D7 backup + D6 manifest-CID) is
  not pre-approved here.
- claim that the H-B9 seam-exhaustion hypothesis is confirmed.
  H-B9 remains the strongest unfalsified hypothesis at this point
  but the design memo for A0-broad (PR #354) is explicit that
  FALSIFIED_A0_BROAD_NARROW is distinct from FALSIFIED_ALL_A0_BROAD;
  the latter is reserved for a multi-architecture saturation
  finding.
- modify `.gitignore`, source code, or any executable artifact.

---

## §2 Five-tier verified surface — admissible language per tier

Before §3 lists per-phase statuses, this section binds the **language
allowed for each tier**. Future decisions, commit messages, and
follow-on memos must respect these boundaries.

### Tier 1 — FORMALLY_VERIFIED

**Definition:** static-code clean, run-provenance complete (committed
artifacts: sweep_results / aggregate_summary / val_selected_cell /
sanity_probe), artifact-code bit-tight match verified, sentinel
verification passed under the V2-expanded contract or its successor.

**Currently in this tier:** **None** in fx-ai-trading.

**Admissible language:**

- "formally verified at PR #<n>"
- "carries V2-expanded sentinel evidence"
- "cleared the full applicable foundation + sentinel verification
  contract, with committed run-provenance artifacts"

**Forbidden:**

- "cleared the F-1 / F-2 / F-3 foundation checks" alone (partial-
  stage clearance is not Tier 1; see §11.Q3 binding)
- attributing Tier 1 to a result that passed only a staged subset
  of the verification contract

### Tier 2 — CONTEMPORANEOUS_CONTRACT_PASS

**Definition:** merge-time memo contract satisfied, static inspection
clean at merge SHA, run-provenance is partial or absent. Suitable as
operational baseline; **not** admissible as "verified evidence" for a
new routing decision.

**Currently in this tier:** Phase 9.16 v9 20p baseline (Sharpe 0.160
nominal; F-1 re-check PASS in static inspection at PR #338, #342,
#345, #351; sweep_results artifact absent at all four merge SHAs).

**Admissible language:**

- "production baseline"
- "operational anchor at PR <n>"
- "contemporaneous contract pass"
- "Phase 28 §10 immutable baseline reproduction (static check only)"

**Forbidden:**

- "verified at PR <n>" without "contemporaneous-contract" qualifier
- "Phase 28 §10 numbers reproduced" (the parquet is absent)
- "tabular ceiling trusted" (deferred to user decision per PR #356)

### Tier 3 — TARGETED_VERIFICATION_REQUIRED

**Definition:** static inspection clean, run-provenance class U
(artifacts gitignored / absent), or material class B finding.
Requires a separately authorised targeted-verification step before
any "verified" claim is admissible.

**Currently in this tier:**

- All 9 Phase 27-29 β-evals (#318, #321, #325, #328, #332, #338,
  #342, #345, #351) — explicit aggregate
  `TARGETED_VERIFICATION_REQUIRED` per PR #356 §4 (citation:
  `phase27_29_tabular_eval_validity_audit.md:525-534`)

**Demoted out of this tier into `ARCHIVED_UNTRUSTED_NUMERIC_DO_
NOT_USE_FOR_ROUTING` per Appendix A (Amendment 2)** — these
remain `TARGETED_VERIFICATION_REQUIRED` for the narrow purpose of
"the underlying feature family or mechanism may be revisited
under a from-scratch new-epoch evaluation", but the **numeric
claims themselves** are not admissible as routing evidence,
pass/fail thresholds, or production-migration anchors:

- +mtf K=3 (Phase 9.X-B v19 causal, archived nominal Sharpe
  0.158): the numeric is downstream of the now-invalidated v18
  0.174 and carries class U on run-provenance; admissible only
  as historical context (citation:
  `sharpe_improvement_brief.md:2,36-37`, `phase9_x_jlmno_series_
  closure_memo.md:5`)
- +mtf K=2 (Phase 9.X-B v19 causal, archived nominal Sharpe
  ≈ 0.157): same status as K=3
- Top-K K=2 (Phase 9.19, archived nominal Sharpe 0.165) and the
  entire Phase 9.19 J-series: phase-closure PARTIAL GO under
  class U on run-provenance (citation:
  `phase9_19_closure_memo.md:3,40,89,100`)
- C-3 kill switches (Phase 9.13, archived nominal Sharpe 0.177):
  predecessor of Phase 27 spine; class U by inheritance
  (citation: `phase9_13_closure_memo.md:3,40,48`)
- Phase 9.X-C M-1 LSTM Mode A (nominal Sharpe 0.061): out of
  PR #356 audit scope but same artifact-commitment pattern;
  presumed class-U risk on run-provenance. Note: Mode A is
  `FALSIFIED_AT_SCOPE` (Tier 4) for the Full-Replacement
  formulation; the 0.061 numeric is archived; modes B-1..B-4 and
  A0-broad sequence-NN remain Tier 5 (citation:
  `sharpe_improvement_brief.md:89,154-161`)

**Demoted out of this tier into `INVALID_LOOKAHEAD_NUMERIC` per
Appendix A (Amendment 2)** — formally invalid; not admissible
for any purpose other than archive context on how the bug was
detected:

- +mtf v18 K=3 Sharpe 0.174 (Phase 9.X-B initial claim): inflated
  by `_add_multi_tf_extended_features` `shift(1)` missing (~14h
  lookahead); v19 causal fix reduced to 0.158 (citation:
  `sharpe_improvement_brief.md:37,182-183`,
  `phase9_x_e_live_deploy_plan.md:30-31,37`)

**Admissible language:**

- "preliminary nominal Sharpe <x> (TARGETED_VERIFICATION_REQUIRED)"
- "Class U on run-provenance"
- "subject to V2-expanded contract re-execution"
- "phase closure verdict at <PR>" (note: phase closure verdict is
  a separate category from "verified result")

**Forbidden:**

- "verified" / "shipped-ready"
- "ready for production"
- "Sharpe lift X verified"
- silent omission of the Tier-3 qualifier when citing a number

### Tier 4 — FALSIFIED

**Definition:** verdict was emitted and not subject to revisit
absent scope amendment. The verdict label binds.

**Currently in this tier:**

- Phase 27.0b / 0c / 0d / 0e / 0f (5 sub-phases; all C-sb-baseline
  picked by val-selector)
- Phase 28.0a / 0b / 0c (3 sub-phases; A0-narrow AR1..AR4 included
  as FALSIFIED_A0_NARROW)
- Phase 29.0a (A2-narrow T1..T4 as FALSIFIED_A2_NARROW; R-T3
  absorbed under FALSIFIED_under_T3)
- Phase 9.17 ensemble (NO ADOPT — trade-rate explosion + per-trade
  EV collapse)
- Phase 9.17b confidence threshold post-filter (NO ADOPT — +0.005
  Sharpe lift)
- Phase 9.18 bucketed TP/SL (NO ADOPT — low-bucket -19% EV drag,
  80% SL-before-partial rate)
- Phase 9.X-A regression LGBMRegressor (NO ADOPT — Sharpe 0.092
  vs baseline 0.160)
- Phase 9.X-C M-1 LSTM Mode A (NO ADOPT — archived closure
  comparison referenced the now-invalid mtf v18 0.174 anchor as
  a secondary reference; retained here as archival closure
  context only. The active falsification is at Mode A
  full-replacement scope; the 0.061 numeric carries Tier-3
  Class-U risk per Appendix A)
- Phase 9.X-D DXY synthetic (NO ADOPT — archived closure
  comparison referenced the now-invalid mtf v18 0.174 anchor;
  retained as archival closure context only)
- Phase 9.X-G greedy decorrelation top-K (NO ADOPT — PnL -18-20%)

**Admissible language:**

- "FALSIFIED_A0_NARROW" / "FALSIFIED_A2_NARROW" (the explicit narrow
  scope label)
- "NO ADOPT at <PR>"
- "phase verdict at <PR>"

**Forbidden:**

- "FALSIFIED_ALL_A0_BROAD" (only NARROW is falsified; PR #354 §H-D2
  ladder binding)
- "LSTM falsified" (only M-1 Mode A is falsified; modes B-1..B-4
  remain DEFERRED_NOT_FORECLOSED)
- "ensemble approach falsified" (only the specific MR/BO ensemble
  variant tested in Phase 9.17 is falsified; alternative ensemble
  formulations are out of that verdict's scope)

### Tier 5 — DEFERRED_NOT_FORECLOSED

**Definition:** explicitly preserved for future Phase routing;
neither falsified nor tested; design memo (where present) locks
admissibility conditions.

**Currently in this tier:**

- A0-broad sequence-NN 3-architecture allowlist (PR #354): S1 LSTM,
  S2 Temporal CNN, S3 Transformer
- R-B feature class beyond R7-A (defined open: not enumerated yet)
- A3 learned MoE (penalised but not closed per PR #354)
- Phase 9.X-C modes B-1 (feature stacking), B-2 (output averaging),
  B-3 (regime gating), B-4 (specialisation) — Tier 2 deprioritised
  at Phase 9.X-C/M-1 closure but not foreclosed
- A2 target redesign broad variants (A2-broad as distinct from
  A2-narrow which is FALSIFIED)
- Phase 9.X-D residual data sources not yet tried: economic calendar
  / event-distance, orderbook microstructure (non-OANDA), interest
  rate spreads, VIX, additional cross-asset
- pair universe expansion beyond 20 (Phase 9.16 v9 20p)
- post-Phase-9.17 ensemble re-formulation with structural
  confidence calibration

**Admissible language:**

- "DEFERRED_NOT_FORECLOSED"
- "untried under current contract"
- "eligible upon <stated prerequisite> completion"

**Forbidden:**

- "abandoned"
- "ruled out" (without the narrow-scope falsification document)

---

## §3 Per-phase per-mode status table

This section is the canonical lookup for "what has been tried" and
"to what depth". When deciding routing or estimating effort, consult
this table. Entries marked TIER are in the corresponding §2 tier.

### Phase 9.x classical era

| Phase / sub | Mode / variant | Nominal claim | Tier | Notes |
|---|---|---|---|---|
| 9.10 | Cost-aware backtest | gross Sharpe 0.35 → 1pip net -0.076 / 0.5pip 0.146 | Tier 3 | Cost-gate condition; baseline for spread-aware design |
| 9.11 | 3+ yr robustness gate | requires Sharpe ≥ 0.20 | (gate definition) | Currently BLOCKED; no candidate meets the gate at Tier-1 quality |
| 9.12 | B-2 bid/ask labels | SELECTOR Sharpe 0.160 | Tier 2 (baseline) | Foundation of current production Phase 9.16 v9 20p |
| 9.13 | C-1 Kelly sizing | NO ADOPT | Tier 4 | Layer-1-only lever; rejected |
| 9.13 | C-2 cap sizing | NO ADOPT | Tier 4 | Layer-1-only lever; rejected |
| 9.13 | C-3 kill switches | archived nominal Sharpe 0.177 | Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` (Appendix A) | Predecessor of Phase 27 spine; Class-U risk by inheritance; numeric not admissible as routing evidence |
| 9.15 | spread bundle | PnL +13%, DD -17% | Tier 2 | Adopted into Phase 9.16 production default |
| 9.15 | spread+RH bundle | PnL +15.5%, train 2x | Tier 4 (in-sample leak) | Found to have in-sample leakage; partial-pair only |
| 9.16 | v9 20-pair universe expansion | PnL +20.1% vs v5, DD%PnL 2.5% | **Tier 2 (production default)** | Pair universe 10→20; current production baseline |
| 9.16 | CSI Layer-1 features | NO ADOPT | Tier 4 | -15% PnL on SELECTOR; redundant with xp_* |
| 9.17 | MR+BO ensemble (no threshold) | NO ADOPT | Tier 4 | Trade-rate 15x; Sharpe collapsed |
| 9.17b | confidence threshold post-filter | NO ADOPT | Tier 4 | +0.005 Sharpe; per-trade EV constraint binding |
| 9.18 | bucketed TP/SL (H-1) | NO ADOPT | Tier 4 | Low-bucket -19% EV drag |
| 9.18 | partial exit (H-2) | NO ADOPT | Tier 4 | 80% SL-before-partial rate |
| 9.19 | Top-K Naive K=2 | archived nominal Sharpe 0.165 / PnL +25% | Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` (Appendix A) | PARTIAL GO at phase closure; Class U on run-provenance; numeric not admissible as routing evidence |
| 9.19 | Top-K Diversified K=2 | similar | Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` | Same Class-U inheritance; numeric not admissible as routing evidence |
| 9.X-A | LGBMRegressor on label_return | NO ADOPT | Tier 4 | Best Sharpe 0.092; per-trade EV collapse |
| **9.X-B** | **+vol feature group** | Tier 4 NO ADOPT at phase scope | Tier 4 | Archived closure comparison referenced the now-invalid mtf v18 anchor; archival closure context only. Active reason recorded: redundant with ATR / BB_width / multi-TF h1_volatility |
| **9.X-B** | **+moments feature group** | K=1 Sharpe 0.145 (< baseline) | Tier 4 | Noisy; skewness/kurtosis/autocorr |
| **9.X-B** | **+mtf K=3 (v18 reported)** | Sharpe 0.174 — **lookahead bug** | Tier 4 + `INVALID_LOOKAHEAD_NUMERIC` (Appendix A) | `shift(1)` missing in `_add_multi_tf_extended_features` (`sharpe_improvement_brief.md:182-183`); not admissible for any routing purpose |
| **9.X-B** | **+mtf K=3 (v19 causal fix)** | archived nominal Sharpe 0.158 (-9.2% vs v18) | Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` (Appendix A) | Class U on run-provenance; PARTIAL GO+ rescinded under v19; numeric is a reduction of a now-invalid v18 anchor and not admissible as routing evidence or pass/fail threshold |
| **9.X-B** | **+mtf K=2 (v19 causal fix)** | archived nominal Sharpe ≈ 0.157 (estimate) | Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` | Same status as K=3 |
| **9.X-B** | **+all (vol+moments+mtf)** | < +mtf alone | Tier 4 | Multicollinearity |
| **9.X-C** | **M-1 Mode A (Full LSTM replacement)** | archived nominal Sharpe 0.061; 7.7× trade rate; 0.13× per-trade EV | Tier 4 `FALSIFIED_AT_SCOPE` (Mode A only; B-1..B-4 untouched; A0-broad sequence-NN untouched) + Tier-3 Class-U risk on the numeric | Class imbalance + no discrimination + information saturation; falsification is **narrow** to Mode A full-replacement formulation |
| **9.X-C** | **Mode B-1 (Feature stacking, LSTM hidden → LGBM)** | **untried** | **Tier 5** | Tier-2 deprioritised at M-1 closure; not foreclosed |
| **9.X-C** | **Mode B-2 (Output averaging)** | **untried** | **Tier 5** | Tier-2 deprioritised at M-1 closure (historic comparison used the now-invalid mtf v18 0.174 anchor; retained only as archival closure context — not a current active comparator). Eligibility under new-epoch contract per §6.B decision table; not foreclosed |
| **9.X-C** | **Mode B-3 (Regime gating)** | **untried** | **Tier 5** | Tier-2 deprioritised at M-1 closure; not foreclosed |
| **9.X-C** | **Mode B-4 (Specialisation)** | **untried** | **Tier 5** | Tier-2 deprioritised at M-1 closure; not foreclosed |
| 9.X-D | +dxy alone | NO ADOPT | Tier 4 | Historic phase-closure comparison used the now-invalid mtf v18 0.174 anchor (archived closure context only — not an active comparator). NO ADOPT verdict at phase scope; any future re-evaluation under the new-epoch contract compares against S-B baseline / S-E control, not against the old anchor. |
| 9.X-D | +dxy+mtf | NO ADOPT | Tier 4 | Same as +dxy alone: historic comparison used the now-invalid mtf v18 anchor; archived closure context only. |
| 9.X-D | Economic calendar / event-distance | **untried** | **Tier 5** | Originally listed as Phase 9.X-D candidate |
| 9.X-D | Orderbook microstructure | **untried** | **Tier 5** | Requires non-OANDA data source |
| 9.X-E | mtf v19 causal live deploy plan | doc-only memo | (planning) | G1/G2/G3 gates defined but not yet executed |
| 9.X-G | greedy decorrelation top-K | NO ADOPT | Tier 4 | ρ ∈ {0.4, 0.5}; PnL -18~-20% |
| 9.X-H | calendar full | NO ADOPT (per log) | Tier 4 | Memo not in main project memory; verify at PR-time |
| 9.X-I | rank audit / risk sizing | NO ADOPT (per log) | Tier 4 | Same caveat |
| 9.X-J | realism (all combined) | (log present) | TBD | Verify at PR-time |
| 9.X-L | filter | NO ADOPT (per log) | Tier 4 | Same caveat |
| 9.X-M | dynamic SL/TP | NO ADOPT (per log) | Tier 4 | Same caveat |
| 9.X-N | margin-aware | NO ADOPT (per log) | Tier 4 | Same caveat |
| 9.X-O | purge / clip | NO ADOPT (per log) | Tier 4 | Same caveat |

**Reading guide:**

- Tier 5 (untried) entries are the **explicit untried surface**.
  They are the legitimate candidates for the Research Tracks §6.
- Tier 3 entries are the **re-evaluation surface** that needs to
  pass new epoch + V2-expanded contract before any production
  consideration.
- Tier 4 (FALSIFIED) entries should not be re-attempted **at the
  same scope**. Scope amendment (different formulation, different
  data, different label structure) is admissible but requires its
  own design memo.

### Phase 27 / 28 / 29 formal-verification era

| Phase | Sub | Verdict label | Tier |
|---|---|---|---|
| 27.0b | TIME penalty score channel | FALSIFIED (val-selector C-sb-baseline) | Tier 4 |
| 27.0c | Calibrated EV channel | FALSIFIED (val-selector C-sb-baseline) | Tier 4 |
| 27.0d | Regression channel | FALSIFIED (val-selector C-sb-baseline) | Tier 4 |
| 27.0e | Quantile-family trim selection rule | FALSIFIED | Tier 4 |
| 27.0f | R7-C regime/context | FALSIFIED | Tier 4 |
| 28.0a | Asymmetric Huber loss / L3 regime weighting | FALSIFIED | Tier 4 |
| 28.0b | Selection rules R1/R2/R3/R4 (R-T1 absorbed) | FALSIFIED | Tier 4 |
| 28.0c | A0-narrow tabular LightGBM AR1..AR4 | FALSIFIED_A0_NARROW | Tier 4 (narrow scope) |
| 29.0a | A2-narrow T1..T4 | FALSIFIED_A2_NARROW (R-T3 absorbed) | Tier 4 (narrow scope) |
| 29.0b-α | A0-broad sequence-NN WIP | INVALID_FOR_FORMAL_VERDICT (PR #355) | (out of formal verdict surface) |

**The audit (PR #356) aggregate verdict over the 9 β-evals (#318,
#321, #325, #328, #332, #338, #342, #345, #351):
`TARGETED_VERIFICATION_REQUIRED`.** This means the negative-finding
ceiling that Phase 27-29 established is preserved as a verdict but
the run-provenance evidence (sweep_results, sanity_probe) is not
independently verifiable from the committed artifacts. The H-B9
seam-exhaustion hypothesis is informed by these verdicts but the
data layer beneath them is class U.

---

## §4 Development philosophy

### §4.1 Foundation first

Any new "verified" claim requires the V2-expanded contract or its
successor to be in place. PR #357 / #358 designed it; PR #360 routed
to a new epoch; PR #361 / #362 / #363 / #365 / #366 defined the
admissibility framework. Until Foundation T1..T4 (§5) complete, no
new evaluation produces a Tier-1 result.

This means **two things every research-track decision must respect**:

1. Any Tier-3 result re-evaluated outside the V2-expanded contract
   continues to be Tier 3 (re-running a Phase 9.x experiment without
   committing sweep_results does not lift Class U).
2. New experiments started before Foundation completion are not in
   the verdict surface; they live in an exploratory log and require
   re-execution under V2-expanded before becoming verdict material.

### §4.2 Extraction vs Expansion — working hypothesis (Amendment 2)

**Status: working hypothesis, not a verified finding.** This
section was originally framed in the initial draft as "mtf was
the single PARTIAL GO+ (extraction vs expansion principle)";
Appendix A's evidence reconciliation demotes the +mtf v18 0.174
to `INVALID_LOOKAHEAD_NUMERIC` and +mtf v19 0.158 to
`ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`. The original
formulation "mtf was the single verified PARTIAL GO+ success"
**is not admissible**.

The empirical falsification surface (committed source citations
in Appendix A) does still show this pattern:

- 5 NO ADOPT verdicts on extraction-tricks at phase closure
  (Phase 9.17 ensemble, 9.17b confidence threshold, 9.19 multi-
  pick SELECTOR Top-K, 9.X-A regression labels, 9.X-C M-1 LSTM
  Mode A) — citations in Appendix A
- 1 PARTIAL GO+ verdict on horizon expansion at phase closure
  (Phase 9.X-B +mtf), but the numerics under that PARTIAL GO+
  are now demoted per Appendix A (v18 INVALID; v19 ARCHIVED
  UNTRUSTED). The verdict label "PARTIAL GO+" survives as a
  phase-closure record; the **numbers do not survive as routing
  evidence**.
- 1 NO ADOPT verdict on cross-asset expansion at phase closure
  (Phase 9.X-D DXY)

**Admissible hypothesis (not a finding):** the falsification
surface above is **consistent with** a working hypothesis that
"clever extraction from the same data tends to NO ADOPT at the
existing tabular-LightGBM-on-R7-A architecture; data-side
expansion has a phase-closure record that is no worse than
extraction-tricks". This is a **research-prioritisation heuristic**
for sequencing Foundation-completion Research Tracks, **not a
verified principle** and **not a binding constraint** on
production decisions or pass/fail thresholds.

**What this hypothesis does NOT support:**

- it does NOT say "+mtf was verified"
- it does NOT say "data-side expansion is verified to succeed"
- it does NOT say "extraction approaches are verified to fail"
- it does NOT supply a pass/fail Sharpe threshold for new-epoch
  evaluations

**What this hypothesis does support (heuristically only):**

- Track D (data-side expansion) may be sequenced earlier than
  later Tracks at equal cost, on the basis of the pattern shape
  above
- Track C (A0-broad sequence-NN) remains the explicit
  falsification path for the H-B9 seam-exhaustion hypothesis
  (§4.4) and is **independent** of the extraction-vs-expansion
  heuristic — sequence-NN under A0-broad is admissible
  regardless of whether the heuristic favours data-side
- Track B (Phase 9.X-C residual LSTM modes B-1..B-4) is **not
  foreclosed** by this heuristic; the heuristic does not
  override per-track design memos

### §4.3 Class-U recurrence prevention

PR #356 audit's U-1 finding (sweep_results / sweep_results.json /
aggregate_summary.json / val_selected_cell.json / sanity_probe.json
gitignored across 9 β-evals) is the most actionable lesson. Future
β-evals must commit these artifacts. The V2-expanded contract makes
this an obligation; this roadmap binds: **every Research Track PR
authored under Foundation T4 commits all run-provenance artifacts
under the V2-expanded sentinel registry**.

### §4.4 H-B9 seam-exhaustion as working hypothesis, not finding

8 + 1 sub-phases of Phase 27-29 (Channel B score, Channel C
selection, Channel A regime, Channel D tabular topology, Channel E
target) all picked C-sb-baseline at val-selector. The H-B9
hypothesis ("the LightGBM + R7-A feature stack is seam-saturated at
this architecture stack") is the strongest unfalsified hypothesis
explaining this 9/9 picking pattern. **It is not a finding.** A
multi-architecture (sequence-NN) test (A0-broad per PR #354) is the
explicit falsification path; A0-broad β remains halted, so H-B9
remains conjectural.

This roadmap accordingly treats A0-broad as the highest-priority
Research Track (Track C below) **conditional on Foundation
completion** (Amendment 3 binding, scoped language):

- a successful A0-broad result (any of S1 / S2 / S3 producing
  `STRONG_GO_UNDER_A0_BROAD`) **would materially weaken H-B9
  under the tested scope** (single-architecture exception)
- all S1 / S2 / S3 failure (FALSIFIED_A0_BROAD_NARROW across the
  allowlist) **would strongly support H-B9 under the
  current-data / current-contract scope**
- **neither outcome alone declares an absolute production
  ceiling**
- **production-ceiling or structural-ceiling conclusions
  require separate strategic review** (memo authored separately
  from Track C closure)

H-B9 remains a hypothesis, not a finding. FALSIFIED_A0_BROAD_NARROW
remains narrow even when emitted across all of S1 / S2 / S3; the
label `FALSIFIED_ALL_A0_BROAD` is **never** to be written under
this roadmap. Either Track-C outcome is informative for
research-track sequencing; neither is sufficient to declare a
strategic ceiling without separate review.

### §4.5 Production keep-alive discipline

Phase 9.16 v9 20p baseline is Tier 2 (CONTEMPORANEOUS_CONTRACT_PASS),
suitable as production default. Foundation completion will take
months. During those months, **production must keep running** at
Phase 9.16 baseline; no new signal is shipped until it passes
Tier-1 admissibility, and the baseline itself must not regress.
Track P3 (production keep-alive engineering) covers this.

---

## §5 Foundation Track (T0..T4)

Foundation work has no expected P&L lift on its own. Its purpose is
to enable subsequent Research Tracks to produce Tier-1 results.
Every Foundation stage requires explicit user authorisation; merging
this roadmap memo authorises nothing.

### §5.1 T0 — Production keep-alive

**Status:** in progress (Phase 9.16 v9 20p baseline shipped).

**Scope:**

- run Phase 9.16 v9 20p as production default
- monitor for material drift (DD%PnL, trade rate, regime
  indicators); record observations in an event log
- do **not** ship any new signal (+mtf, Top-K, ensemble, regression,
  LSTM, etc.) during Foundation T1..T4

**Exit criteria:** continuous through Foundation; no stage gate.

**Authoring shape:** no PR; operational. Observations recorded in
existing event log.

### §5.2 T1 — Gate P1 PR-B implementation

**Status:** plan locked at PR #365; implementation PR not authorised.

**Scope:** 3-PR split per PR #365 §11 default:

- **PR-B.0 — infrastructure**: `scripts/gate_p1_pr_b_launcher.py`
  (outer launcher), `scripts/_gate_p1_inspector/bootstrap.py`,
  guards/* (5 modules: bytecode / credentials / network /
  subprocess / filesystem), outer-launcher tests, guard tripwire
  tests, stub inspector emitting empty report. ~15-20 files,
  ~1500-2000 lines including tests.
- **PR-B.1 — authority + raw inventory + coverage + retention**:
  `authority/pair_universe.py`, `authority/schema.py`,
  `inspector/raw_inventory.py`, `inspector/coverage.py`,
  `inspector/retention.py`, `inspector/resolver.py`, report writers
  for 5 artifacts (gate_p1_report, raw_inventory_<id>,
  coverage_<id>, retention_feasibility_<id>, report.md). First PR-B
  inspection executes. ~15-20 files, ~2500-3500 lines.
- **PR-B.2 — dependency + pipeline feasibility**:
  `inspector/dependency_inventory.py`,
  `inspector/pipeline_feasibility.py`, report writers for
  dependency_inventory_<id> and pipeline_feasibility, critical-cell
  registry, frozen entrypoint registry. Second PR-B inspection
  executes. ~10-15 files, ~2000-3000 lines.

**Exit criteria (T1):**

- PR-B.0, B.1, B.2 all merged
- first inspection report emitted with `top_level_outcome` ∈
  {`LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`,
  `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH`,
  `RETENTION_DESTINATION_UNRESOLVED`} (first-run PASS is
  structurally unreachable per PR #365 §6.2)
- per-candidate dependency_inventory and pipeline_feasibility
  classifications recorded

**Stage gate:** review of first-execution `gate_p1_report.json`
sufficiency for proceeding to T2 retention deposit step.

### §5.3 T2 — Gate P2 retention deposit + round-trip verification

**Status:** evaluation memo locked at PR #366; destination
selection not authorised; deposit not begun.

**Scope:**

- user selection of destination from PR #366 §7 Tier-1 recommendation
  set (D1 GitHub release / D3 Cloudflare R2 + object-lock / D4 AWS
  S3 + object-lock / D5 Backblaze B2 + object-lock) or a justified
  alternative
- destination account setup + bucket / release creation
- deposit of OANDA 2026-05-31 archive raw JSONL files (120 files,
  17.54 GB) to selected destination with immutability mode active
- round-trip verification per PR #366 §8 protocol (download all
  files → recompute SHA-256 → assert equal `candles_manifest.json`
  entries; size + row count + ts boundary spot check on
  deterministically-sampled subset)
- emit `artifacts/gate_p2_verification/<verification_id>/
  gate_p2_retention_verification_report.json` with per-file pass /
  fail
- if D10 combination strategy selected (recommended): repeat for
  backup leg (D7 offline HDD) and manifest-CID sidecar (D6 IPFS)

**Exit criteria (T2):**

- round-trip report shows 100% per-file SHA-256 match
- restoration procedure committed under `docs/runbook/` per epoch
- immutability mode verified active (object-lock retention horizon
  ≥ 5 years recommended per PR #366 §11.Q4)

**Stage gate:** retention deposit is binding evidence that the
OANDA 2026-05-31 archive bytes are durably retrievable per PR #361
§7; T3 may begin.

### §5.4 T3 — New epoch baseline + control construction

**Status:** designed at PR #361 (epoch identity, dependency
inventory, scientific adequacy review); construction not begun.

**Scope:**

- declare epoch identity: `manifest_id`,
  `epoch_freeze_timestamp_utc`, `observation_start_timestamp_utc`,
  `observation_end_timestamp_utc`, `span_days_effective`,
  `pair_universe_hash`, `granularities_hash`
- per PR #361 §3, select span: 730d / 365d / 3650d_BA (T1's
  candidate spans). PR #361 §2 binds: "longest common,
  schema-valid, dependency-complete, time-aligned local-data span".
  The 3650d_BA candidate spans 2016-06-02 to 2026-05-29 UTC (per
  PR #364 archive); admissibility decided at T1 dependency-
  inventory step.
- construct dataset under the V2-expanded contract:
  - signal generators
  - label generators (M1 BA + label structure decided at T3
    construction; per PR #361 §6, M5/H1/D1 derivability from M1 BA
    must be verified by AST-evidenced functions, not silently
    inferred)
  - D-1 PnL identity validation
  - split manifest (temporal boundaries per PR #361 §8;
    test-touched-once + selection-only-on-validation + frozen-OOS
    quarantine)
  - aligned-row-set under PR #361 §8 (generated once at Gate P2,
    frozen, manifested, re-used across all subsequent comparisons)
- compute **new S-B economic baseline** under the new epoch's raw +
  labels (replaces Phase 9.12 B-2 bid/ask SELECTOR as the
  immutable §10 reference)
- compute **new S-E tabular control** (equivalent role of Phase
  28's S-E anchor under the new epoch)
- run **D-1 PnL identity validation** on the epoch's labels
- compute aligned row-set + provenance manifests linking baseline,
  control, and any candidate to the same `manifest_id`
- emit scientific adequacy review (per PR #361 §10) recording
  span statement, regime acknowledgement, intra-epoch fairness
  statement; **prohibited claim**: "E2 restores 1095d historical
  evidence strength"

**Exit criteria (T3):**

- new epoch dataset (raw / labels / split / row-set / provenance
  manifests) constructed and committed
- new S-B economic baseline computed and committed
- new S-E tabular control computed and committed
- D-1 PnL identity validation executed and committed
- scientific adequacy review document committed
- run-provenance artifacts committed (sweep_results / aggregate /
  val_selected / sanity_probe equivalents required by the
  construction harness — **not** gitignored; explicit U-1 prevention)

**Exit label proposed for T3 (Amendment 1):**

- `NEW_EPOCH_BASELINE_CONTROL_BUILT` /
  `NOT_FORMALLY_VERIFIED_YET`

These labels are **proposed-only** at this roadmap level; if a
later T3-specific design memo adopts a different label, that memo
binds. T3 explicitly **does not** require:

- F-1..F-7 + S-1..S-6 sentinel verification PASS
- a Tier 1 (FORMALLY_VERIFIED) claim
- a V2-expanded aggregate verification verdict

All sentinel verification responsibilities are exclusive to T4.

**Stage gate:** the new-epoch baseline reaches `NEW_EPOCH_BASELINE_
CONTROL_BUILT` / `NOT_FORMALLY_VERIFIED_YET` (proposed label;
subject to T3-specific design memo). It is **not** Tier 1; future
elevation to Tier 1 depends on T4 sentinel verification under the
applicable contract. Production baseline can be considered for
migration **only after** T4 completes for the relevant comparison
contract; default policy is **continue Phase 9.16 v9 20p in
production** through T3 and T4.

### §5.5 T4 — V2-expanded sentinel verification implementation

**Status:** Stage 1 infrastructure-only complete at PR #359
(6 contract snapshots + 8 harness modules + 81 unit tests; NO
formal run); Stage 2 = HALTED_INPUT_UNAVAILABLE (PR #360); design
locked at PR #357 + Amendment 2026-05-24 (PR #358).

**Scope (post-T3 — when input is now available via the new epoch):**

- implement F-1..F-7 foundation checks against the new epoch
  baseline + control
- implement S-1..S-6 sentinel checks against #325 / #332 / #338 /
  #342 / #345 / #351 equivalent anchors recomputed on the new
  epoch (note: prior PRs are historic anchors and not re-executed;
  the "equivalent anchors" are computed once on the new epoch and
  serve as the V2-expanded sentinel reference)
- emit verification report only at a **previously authorised**
  success label (e.g., `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES`
  if applicable under PR #357). Any stricter label requires a
  separate design memo and explicit user approval before being
  added to the V2-expanded contract (Amendment 1 binding,
  re-stated; aligns with the Exit-criteria binding below).

**Exit criteria (T4):**

- F-1..F-7 + S-1..S-6 all executed under the same accepted
  contract / provenance boundary, with run-provenance committed
- verification report under
  `artifacts/v2_expanded_verification/<verification_id>/`
- aggregate verdict at a **previously authorised** success label
  (e.g., `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES` per
  PR #357)

**No new success label is minted by this roadmap.** Specifically,
`SENTINEL_VERIFICATION_COMPLETE` is **not** introduced here; any
stricter label requires a separate design memo and explicit user
approval before being added to the V2-expanded contract.

**Stage gate:** Foundation complete for the applicable contract.
Tier 1 (FORMALLY_VERIFIED) claims become admissible for results
that pass the **full** V2-expanded contract under T4 (not a partial
staged subset). Research Tracks A..G become eligible (each
requiring separate authorisation).

---

## §6 Research Tracks (A..G)

Each Research Track is eligible only after Foundation T4 completes
unless explicitly noted otherwise. Each track requires its own
design memo + implementation PR(s) + sentinel verification. Each
requires explicit user authorisation; merging this roadmap memo
authorises nothing.

### §6.A Track A — Re-evaluate Tier-3 prior PARTIAL / NO-ADOPT under new epoch

**Prerequisite:** Foundation T4 complete.

**Scope (Amendment 1 + 2):** the **feature families** and
**mechanisms** behind the Tier-3 entries from §3 receive
**from-scratch re-evaluation** under the V2-expanded contract on
the new epoch. The purpose is to determine whether each feature
family / mechanism is structurally informative under the new
foundation, **not** to reproduce or confirm any old-epoch nominal
Sharpe. Old-epoch numerics are archived context only (per
Appendix A `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`).

**Critical bindings (Amendment 2):**

- old-epoch nominal Sharpe values (0.158, 0.165, 0.177, etc.) are
  **NOT** executable pass/fail gates for new-epoch evaluation
- the authoritative comparators are the new-epoch S-B baseline
  and S-E control (built at T3)
- exact thresholds and outcome ladders are defined in each
  track-specific design memo authored after T3 / T4 completion,
  not in this roadmap
- A Tier 1 research result does **not** automatically authorise
  production reflection. Any production migration requires
  (a) a separate migration design memo, (b) live / paper safety
  gates (per §7 P1..P3 and `phase9_x_e_live_deploy_plan.md`
  G1 / G2 / G3 lineage), and (c) explicit user authorisation.

**Sub-tracks:**

- **A.1 — `MTF feature-family re-evaluation from scratch under
  new epoch`.** The mtf feature class (multi-timeframe context
  features at 4h / daily) is re-implemented and re-evaluated
  from scratch on the new epoch under the V2-expanded contract,
  using whatever causality-correct implementation the new
  contract requires. This sub-track:
  - **does NOT** attempt to reproduce the archived nominal
    Sharpe 0.158
  - **does NOT** treat the +mtf v19 PARTIAL GO+ phase verdict
    as evidence that this feature family will succeed at new
    epoch
  - **does NOT** use 0.158 as a pass/fail threshold
  - **does NOT** use 0.174 (now `INVALID_LOOKAHEAD_NUMERIC`)
    in any capacity
  - **compares** the resulting numbers against the new-epoch
    S-B baseline and S-E control, with thresholds defined in
    the A.1 design memo authored after T3 / T4 completion
- **A.2 — `Top-K K=2 mechanism re-evaluation from scratch under
  new epoch`.** Re-implemented under V2-expanded contract. The
  archived 0.165 is not a threshold; comparators are the new-
  epoch S-B and S-E. A.2 requires the Top-K execution gateway
  (per PR #216 follow-up requirement) to be implemented before
  the sub-track can begin.
- **A.3 — `C-3 kill switches mechanism re-evaluation from
  scratch under new epoch`.** C-3 was a predecessor of the
  Phase 27 spine; it is mapped onto the new epoch's signal /
  state schema. The archived 0.177 is not a threshold;
  comparators are the new-epoch S-B and S-E.

**Authoring shape:** one design memo + one implementing PR per
sub-track (A.1, A.2, A.3 each), authored after T3 / T4 completion;
sentinel verification re-run under T4 contract.

### §6.B Track B — Phase 9.X-C residual LSTM modes (B-1, B-2, B-3, B-4)

**Prerequisite:** Foundation T4 complete **and** Track A.1 (+mtf
feature-family re-evaluation) outcome known.

**Amendment 2 binding:** old-epoch arithmetic ("B-2 = 0.061
averaged with 0.174 ≈ 0.118 < 0.174" from Phase 9.X-C/M-1 closure)
is **NOT** used as a B-track priority justification under this
roadmap. The 0.174 is `INVALID_LOOKAHEAD_NUMERIC`; the 0.061 is an
old-epoch archived numeric from a Mode-A-only falsification. New
B-track priority logic is defined by **future new-epoch A.1 /
C.1 outcomes** plus **explicit marginal-information hypotheses**
in per-mode design memos.

**Decision table (Amendment 1):**

| Track A.1 outcome on new epoch | B-1 / B-3 / B-4 eligibility | B-2 eligibility |
|---|---|---|
| **A.1 succeeds (Tier 1 under T4)** | **eligible** for design-memo authoring; each mode requires its own marginal-information hypothesis explaining why hidden-state stacking / regime gating / specialisation might add to a working mtf | **low priority**: output-averaging on top of a working mtf has limited upside; admissible only via separate design memo with marginal-information argument |
| **A.1 fails (Tier 4 at scope)** | **lower priority** than Track D / data-side expansion (extraction-vs-expansion heuristic §4.2). Each mode admissible only by separate design memo that justifies its marginal-information hypothesis against the new baseline; not automatically revived | same as left: only by separate design memo |
| **A.1 ambiguous (Tier 3 or inconclusive ladder result)** | **defer** B-tracks until Track C.1 (A0-broad S1 LSTM) or Track D.1 (time-axis) outcome clarifies the architecture-vs-data binding | **defer** under same condition |

In all three rows, Track D (data-side expansion) retains higher
priority than Track B (architecture / extraction tricks) per the
§4.2 working hypothesis. Track B candidates require **explicit
user authorisation + marginal-information hypothesis per design
memo**; the decision table above is a recommendation, not an
auto-route.

**Scope:**

- **B.1 — Mode B-1 (Feature stacking).** LSTM hidden state →
  LightGBM input feature. Re-uses M-1 LSTM training; estimated
  ~2 days. Outcome: tests whether LSTM hidden state has marginal
  information value over R7-A features.
- **B.2 — Mode B-2 (Output averaging).** P_lstm × α + P_lgbm ×
  (1-α). Estimated ~1 day if M-1 LSTM training is preserved.
  Conditional on A.1.
- **B.3 — Mode B-3 (Regime gating).** LSTM regime filter.
  Estimated ~6 days (most expensive Tier 2). Requires explicit
  user authorisation given cost.
- **B.4 — Mode B-4 (Specialisation).** LSTM long horizon + LGBM
  short horizon. Cost similar to B-3; same authorisation gate.

**Authoring shape:** per mode, one design memo + one implementing
PR. Each runs under V2-expanded contract on the new epoch.

### §6.C Track C — A0-broad sequence-NN formal verification

**Prerequisite:** Foundation T4 complete **and** A0-broad preflight
audit pass (per PR #353 nine-dimension feasibility review and
PR #355 amendment §0.A).

**Scope:** the 3-architecture allowlist locked at PR #354:

- **C.1 — S1 LSTM under A0-broad contract.** Windowed N=32×8 input
  on R7-A (new epoch). Train-time objective = val Huber loss;
  verdict-time objective = val Sharpe (objective wall per PR #354
  §H-D2). Outcome ladder per H-D2 4-outcome:
  `STRONG_GO_UNDER_A0_BROAD` / `MODERATE_GO_UNDER_A0_BROAD` /
  `INCONCLUSIVE_UNDER_A0_BROAD` / `FALSIFIED_A0_BROAD_NARROW`.
  Note: even FALSIFIED_A0_BROAD_NARROW is **narrow** — it does
  not imply FALSIFIED_ALL_A0_BROAD; S2 and S3 remain eligible.
- **C.2 — S2 Temporal CNN under A0-broad contract.** Same input
  + objective + outcome ladder.
- **C.3 — S3 Transformer under A0-broad contract.** Same input +
  objective + outcome ladder.
- **C.d2-arch-control 7th anchor.** Per PR #354, tabular LightGBM
  control inside the sequence-cell harness — required to verify
  the harness itself is operating correctly. Without this control,
  S1/S2/S3 results are uninterpretable.

**Architecture sequencing recommendation:** S1 first (lowest setup
cost; reuses Phase 9.X-C/M-1 PyTorch + CUDA infrastructure), then
S2, then S3 — total estimated 2-4 weeks per architecture under
V2-expanded contract.

**Falsification path for H-B9:**

- if any of S1, S2, S3 → STRONG_GO_UNDER_A0_BROAD: H-B9 is
  falsified at narrow scope (single-architecture exception); a
  successful architecture warrants integration design memo
- if all three → FALSIFIED_A0_BROAD_NARROW: this is **strong
  evidence for the current-data / current-contract seam-
  exhaustion hypothesis**. **Strategic review is required before
  declaring a production ceiling**; production-ceiling language
  is not authorised by an all-architecture
  FALSIFIED_A0_BROAD_NARROW result alone. Pivot priority shifts
  toward Track D (data expansion) and toward broader scope
  re-evaluation, but only through a separately authorised
  strategic-review memo.

**Scope discipline (Amendment 1):** `FALSIFIED_A0_BROAD_NARROW`
remains **narrow** even when emitted across all of S1 / S2 / S3.
The label `FALSIFIED_ALL_A0_BROAD` is **never** to be written
under this roadmap; it would require a separately authorised
broader saturation contract that defines what "all A0-broad"
means beyond the current 3-architecture allowlist.

**Authoring shape:** per architecture, one design memo + one
implementing PR (training script + eval + report). All commit
sweep_results + sanity_probe + aggregate_summary (Class-U
prevention).

### §6.D Track D — R-B feature class expansion (data-side)

**Prerequisite:** Foundation T4 complete. Each sub-track requires
its own data source plan.

**External-data provenance/retention gate (Amendment 1):**

For any sub-track that introduces data from outside the OANDA
2026-05-31 archive (D.2, D.4, D.5 below, and any other external
or non-OANDA source), a **mini data-source feasibility +
retention/provenance gate** must complete **before** any model
evaluation begins. The mini-gate requires:

- raw-byte retention of the external source under a destination
  satisfying PR #361 §7 admissibility criteria (round-trip
  restorable / immutability or content-addressed / auditor-
  runnable restoration), independently of the primary epoch's
  retention destination
- schema manifest of the external source (per-field types, units,
  timestamp semantics, sampling cadence)
- dependency manifest declaring which consumer functions depend
  on the external source and how
- documented restoration procedure committed under
  `docs/runbook/`

No external calendar / interest-rate / orderbook / other side
input may enter a verified evaluation as an **unretained side
input**. If the external data source changes the epoch's
information content materially, the track must explicitly
define whether it is being added as:

- **additive epoch extension** (same `manifest_id`, extended
  inputs declared in a new manifest section), or
- **a new epoch** (new `manifest_id`, full T3 / T4 cycle re-run)

The choice is recorded in the sub-track's design memo and binds
how the sub-track's results integrate with prior baseline /
control.

**Scope (in extraction-vs-expansion-heuristic priority order per §4.2;
heuristic only, not binding):**

- **D.1 — Time-axis features.** Session (Asia / Europe / NY),
  day-of-week, month, holiday distance, fed-meeting distance.
  Cheaper because timestamp-derived from existing OANDA bytes
  — no external source needed. Still requires (a) causality
  check (no future-bar timestamp leakage; e.g., distance-to-
  event must use only events whose timestamp is strictly past)
  and (b) split-leakage check (per-split distribution of
  session / month / holiday categories must not differ in a
  way that conflates structural label imbalance with predictor
  signal). ~3 days. Untried at depth.
- **D.2 — Economic calendar / event-distance.** Originally a
  Phase 9.X-D candidate; not yet tried. ~2-3 days using OANDA
  Labs API or self-built calendar. **Subject to the external-
  data provenance/retention gate above.** Mid-cost.
- **D.3 — Cross-asset re-evaluation.** Phase 9.X-D DXY synthetic
  NO ADOPT — re-evaluate at A0-broad sequence-NN architecture
  (Track C) if available, since DXY as orthogonal feature may
  behave differently under sequence-NN than under tabular
  LightGBM. DXY synthetic uses existing OANDA bytes (derived
  from PAIRS_20), so it does not require the external-data
  gate; however, additional cross-asset sources (e.g., true DXY
  futures, gold, VIX, indices not in OANDA Japan practice
  account) would.
- **D.4 — Interest rate spreads.** US 2y/10y, JP, EU, AU rate
  differentials. Requires non-OANDA data source (FRED /
  Bloomberg / other). **Subject to the external-data provenance/
  retention gate above.** ~3-5 days.
- **D.5 — Orderbook microstructure.** Most expensive (~5+ days,
  non-OANDA data). Most informative if successful. Conditional
  on Track C result and Track D.1-D.4 outcomes. **Subject to
  the external-data provenance/retention gate above.**
- **D.6 — Pair universe expansion (20 → 30).** Cheap if pair
  data available; new epoch construction (T3) may include a
  wider pair set as a parameter. Authorisation deferred to T3
  construction decision. If additional pairs require an
  external data source (e.g., a pair not retained under the
  OANDA 2026-05-31 archive), the **external-data provenance/
  retention gate above applies**.

**Authoring shape:** per sub-track, one design memo + one
implementing PR. Each runs under V2-expanded contract; each
respects the extraction-vs-expansion principle (data-side first).

### §6.E Track E — A2-broad target redesign

**Prerequisite:** Foundation T4 complete + Track A.1 outcome
known.

**Scope:** Phase 29.0a's A2-narrow T1..T4 are FALSIFIED. A2-broad
extensions (target redesign at a wider scope than the closed
4-target allowlist) are DEFERRED_NOT_FORECLOSED. Examples:

- E.1 — multi-horizon weighted target (T3 generalised)
- E.2 — meta-labelling: 2-stage classifier (decide-trade vs
  not-trade first, then direction) — addresses class-imbalance
  insight from Phase 9.X-C/M-1
- E.3 — return-magnitude regression with per-pair quantile
  normalisation
- E.4 — risk-adjusted target (Sharpe-of-trade rather than return)

Each candidate requires its own design memo enumerating the
target's relation to the A2 scope and to D-1 PnL identity.

### §6.F Track F — A3 learned MoE

**Prerequisite:** Foundation T4 complete + at least one Track C
architecture's H-D2 outcome known.

**Scope:** A3 (learned mixture-of-experts) was penalised but not
foreclosed at PR #354. The penalty reflects A3's higher complexity
+ higher overfitting risk. If Track C's S1 / S2 / S3 produces a
STRONG_GO under A0-broad, the additional complexity of A3 may be
inadmissible; if all S1 / S2 / S3 fail (FALSIFIED_A0_BROAD_NARROW
across the allowlist), A3 becomes the next admissible architecture
class.

**Authoring shape:** one design memo (A0-broad style; full ladder),
one or more implementing PRs.

### §6.G Track G — Phase 9.17 ensemble re-formulation

**Prerequisite:** Foundation T4 complete + Track A.1 + at least
one Track C architecture result.

**Scope:** Phase 9.17 ensemble (MR + BO + LGBM) NO ADOPT because
of trade-rate explosion + per-trade EV collapse without
confidence threshold. Phase 9.17b's threshold post-filter delivered
only +0.005 Sharpe. The Phase 9.17 verdict is **narrow** — it
applies to the specific ensemble formulation tested. Open
alternatives:

- G.1 — calibrated confidence ranking ensemble (each ensemble
  member emits calibrated probability; selector picks at
  threshold informed by per-trade-EV target rather than
  fixed-confidence)
- G.2 — regime-conditional ensemble (LGBM in trend regime;
  MeanReversion in range regime; explicit regime classifier as
  gate)
- G.3 — sequence-NN + LightGBM ensemble (after Track C produces
  a viable sequence-NN architecture)

### Cross-track sequencing recommendation

Given Foundation T4 completion is gating, the **recommended
research-side sequencing under Foundation T4 completion** is:

1. Track A.1 (+mtf) first — cheapest re-evaluation; sets context
   for B / D
2. Track C.1 (S1 LSTM under A0-broad) — falsifies or partially
   confirms H-B9
3. Track D.1, D.2 (time-axis, economic calendar) in parallel with
   C.1 — data-side expansion under extraction-vs-expansion bias
4. Track A.2 (Top-K) after T4
5. Track C.2, C.3 (S2, S3) after C.1
6. Tracks B, E, F, G conditional on (1)-(5) outcomes

This sequencing maximises information per unit cost (A.1 cheapest
re-evaluation, C.1 informative regardless of outcome, D.1-D.2
cheap data-side expansion).

---

## §7 Production-Improvement Tracks (P1..P3)

These tracks are **independent of the verification layer**. They
can be progressed in parallel with Foundation without contaminating
production baseline.

### §7.P1 — Spread / slippage modelling refinement

**Status:** broker-time-aware spread snapshotting not implemented
at the modelled depth required. Phase 9.10 cost-aware backtest
recorded a 1pip → 0.5pip Sharpe-sensitivity pattern (Sharpe more
than doubled in the closure-memo summary). **Amendment 3
binding:** this Phase 9.10 evidence is **historical / operational
cost-sensitivity context** at Tier 3 (per §3 status table); it
is **not Tier-1 verified research evidence** for a current
routing decision. P1 / P2 / P3 remain production-engineering
priorities; each requires a design memo, backtest / paper
evaluation, and the production safety gates specified below
before any production-code change.

**Scope:**

- broker-time-aware spread profile (Tokyo / London / NY / off-hours
  per pair); empirical histogram from OandaQuoteFeed live polling
- slippage estimate per market condition (volatility regime, time
  of day, position size)
- update production cost model with per-time-of-day spread
- A/B over a backtest window: old fixed-pip spread vs new
  empirical profile

**Authoring shape:** design memo (small; ~200-400 lines) + one or
two implementing PRs. Independent of Foundation.

### §7.P2 — Live spread snapshotting + profile validation

**Status:** OandaQuoteFeed currently used in M9 paper loop;
historic spread profile not retained as authoritative reference.

**Scope:**

- snapshot spread per pair per minute for N weeks
- compute empirical spread distribution per pair
- ship reference profile under `artifacts/spread_profile/<epoch_id>/`
- replace fixed-pip default in backtest with this profile

**Authoring shape:** design memo + implementing PR (snapshot
collector + profile builder + backtest integration).

### §7.P3 — Cost-aware position sizing engineering

**Status:** Phase 9.13 C-1 Kelly and C-2 cap NO ADOPT for
research-layer Sharpe lift. Production-layer cost-aware sizing
(margin / spread / per-pair max-position) is distinct from the
research-layer Layer-1 lever Phase 9.13 tested.

**Scope:**

- bid/ask × position-size margin accounting
- per-pair max position scaling by current spread
- drawdown-aware position scaling (engineering, not Layer-2
  research)
- production order-execution checks (rejected orders, partial
  fills, retry policy)

**Authoring shape:** design memo + one or two implementing PRs.
Engineering-flavour; explicitly **not** a Sharpe-lift attempt.

### Production-layer keep-alive

P1, P2, P3 are **independent of research-signal verification
contamination, but still subject to production engineering risk
controls**. They improve effective net P&L without claiming a
"new verified signal", but each carries its own production-side
risk that must be managed explicitly:

- **P2 snapshotting is observational and safest first.** It only
  records live spread data; it does not change any production
  decision logic. Recommended as the entry sub-track.
- **P1 cost-model changes must be evaluated in backtest / paper
  before production use.** Replacing the fixed-pip spread with
  an empirical profile alters per-trade economics and re-routes
  marginal trade-pass / trade-block decisions; A / B
  paper-comparison required before any production switch.
- **P3 execution / sizing changes require production safety
  gates, rollback plan, and risk limits.** Margin accounting,
  per-pair max position, drawdown-aware sizing, and
  order-execution checks each affect live order flow; each
  requires an explicit rollback plan and a pre-stated risk
  limit (max position / max daily loss / max consecutive losses)
  that triggers automatic pause.

Each of P1 / P2 / P3 still requires **explicit user
authorisation plus a design memo before any production code
changes**. Tracks are eligible to be authorised **at any time**
(independent of Foundation status), but no track auto-routes
to production.

Recommended priority within production-side: **P2 (data) → P1
(model, paper A/B first) → P3 (engineering, safety gates)**,
because P2 provides the empirical evidence for P1, and P1
provides the cost-model for P3.

---

## §8 Cross-track resource accounting and sequencing constraints

### §8.1 Resource pool

- one user (research direction + final authorisation)
- one Claude assistant (research + doc authorship + implementation
  execution)
- one consumer-grade GPU (RTX 3060 Ti / 8 GB) for any LSTM / NN
  training (Phase 9.X-C confirmed reusable; A0-broad sequence-NN
  candidates run on this)
- ~50 min per 20-pair × 39-fold × 3-retrain × 10-epoch LSTM eval
  (Phase 9.X-C reference); A0-broad sequence-NN per architecture
  likely 2-4 weeks calendar time
- existing CI capacity (per repo-level workflow)

### §8.2 Foundation-track parallelism

Foundation T1 (PR-B implementation) and T2 (retention deposit)
**planning** can proceed in **parallel** because:

- T1 produces a software artifact (the inspector); T2 produces a
  storage artifact (the deposit)
- they share only the candidate raw bytes which are read-only
- a contract-level integration is required between them — the
  Gate P1 PR-B inspection report's
  `candidate_retention_options_requiring_later_authorisation` is
  the input to the T2 destination selection — but this can be
  reflected after both complete

**Critical binding (Amendment 1): T2 deposit is NOT epoch
adoption.** If T2 deposits a broad archive (e.g., the entire
OANDA 2026-05-31 10y archive), the deposit only establishes
**retained input availability**; it does **not** automatically
adopt that archive as the new epoch's data envelope. The choice
of which span / pair universe / granularity set defines the new
epoch is **made at T3** after the user reviews the combined
evidence from the T1 Gate P1 inspection report and the T2
retention deposit verification.

Concretely:

- T2 may proceed with depositing the 3650d_BA bytes irrespective
  of which epoch span will eventually be selected
- T3 may still construct the epoch at 730d_BA / 365d_BA /
  3650d_BA (or any other admissible span discovered at T1)
  regardless of what T2 deposited
- T2 deposit / adoption **must not bind a final epoch span
  unless the chosen span is consistent with Gate P1 PR-B
  findings** from T1 — i.e., T1 evidence is the gate for which
  spans are candidate, T2 deposit covers the retained input,
  and T3 makes the final epoch-span decision under combined
  evidence

T3 (new epoch construction) depends on T1 (the inspection
report's dependency / pipeline feasibility classifications
inform whether the epoch's required-input dependency inventory
is satisfied) and T2 (durable byte retention is binding under
PR #361 §7) **both being reviewed by the user before T3 epoch
selection**.

T4 (V2-expanded sentinel implementation) depends on T3 (the new
epoch's baseline + control are the input the sentinel checks
verify).

### §8.3 Research-track parallelism

Research Tracks A, B, C, D, E, F, G can run in parallel under
Foundation T4 completion **subject to GPU contention** (Track C
sequence-NN training competes with Track B residual LSTM modes
for GPU time). A reasonable parallelism is:

- one A-track candidate (CPU-based, LightGBM)
- one C-track or one B-track architecture (GPU-based)
- one D-track candidate (CPU-based, LightGBM)
- in any given week

P1, P2, P3 are CPU-only + IO-bound; they parallelise with research
tracks freely.

### §8.4 Authorisation cadence

Each track / stage requires explicit user authorisation per the
no-auto-route binding (PR #361 §11, PR #362 §11, PR #365 §11).
This roadmap binds: **at most one Foundation stage authorisation
per session** to allow review of prior-stage results to inform
next-stage decision. Research-track authorisations may be batched
(e.g., A.1 + C.1 + D.1 authorised together) after Foundation T4
completion.

---

## §9 Risk register

- **R1 — Class-U recurrence.** Phase 27-29 audit's U-1 finding is
  the most actionable lesson. Mitigation: V2-expanded sentinel
  registry binds run-provenance artifact commitment; every Research
  Track PR commits sweep_results + sanity_probe + aggregate_summary.
- **R2 — Lookahead bug recurrence (Phase 9.X-B v18 lesson).**
  Mitigation: every feature-engineering function adds an
  AST-checkable causality test (`raw.shift(1)` pattern verified
  by automated check); per-function golden test asserts no
  same-bar or future-bar information enters the feature.
- **R3 — H-B9 over-confidence.** H-B9 is hypothesis, not finding.
  Mitigation: Track C (A0-broad) is explicit falsification test;
  decisions assume H-B9 conjectural until C result.
- **R4 — New-epoch span insufficiency.** 3650d_BA OANDA archive
  spans 2016-06-02 to 2026-05-29 UTC (~10 years); regime coverage
  is partial (no pre-2016 cycle). Mitigation: scientific adequacy
  review at T3 (PR #361 §10) explicitly records limitation.
- **R5 — Production drift during Foundation.** Phase 9.16 v9 20p
  baseline may degrade in live regime over Foundation months.
  Mitigation: T0 keep-alive monitoring; if production Sharpe
  drops ≥ X% over month-over-month rolling window, escalate to
  user (DECISION_POINT_PRODUCTION_DRIFT).
- **R6 — GPU compute cost.** Track C sequence-NN training is the
  most expensive compute; ~2-4 weeks per architecture. Mitigation:
  serial C.1 → C.2 → C.3 sequencing; checkpoint reuse across
  architectures where possible.
- **R7 — Multi-track resource contention.** Foundation + Research
  + Production simultaneous progression risks cognitive load.
  Mitigation: §8.4 authorisation cadence; one Foundation stage at
  a time; research-track authorisations batched.
- **R8 — Cross-track contract drift.** V2-expanded contract amendments
  may invalidate in-progress track work. Mitigation: each track's
  design memo cites the V2-expanded contract version (PR SHA) at
  authoring time; amendments require all in-progress tracks to
  re-align.
- **R9 — Authorisation queue blockage.** Foundation T1..T4 take
  months; if user is unable to authorise next stage on a regular
  cadence, Foundation stalls; in turn, all Research Tracks stall.
  Mitigation: P1..P3 production-side tracks always remain
  authorisable independent of Foundation; T0 keep-alive runs
  regardless.
- **R10 — Selection bias in Research Track A re-evaluation.**
  Re-running +mtf / Top-K under new epoch may discover that the
  prior Sharpe was driven by regime-specific dynamics that the
  new epoch's span no longer covers. The outcome ladder in §6.A
  must accept this as a legitimate Tier 4 outcome, not as evidence
  of methodology error.
- **R11 — Backtest realism gap.** Even after V2-expanded sentinel
  verification, backtest Sharpe may not survive live execution
  realism (P1 P2 P3 production-side work attenuates this). The
  G1 / G2 / G3 gates in `phase9_x_e_live_deploy_plan.md` capture
  this; future production-deployment PRs honour them.
- **R12 — Cross-architecture overfitting in Track C.** Running
  S1 / S2 / S3 sequentially with shared hyperparameter search may
  introduce data dredging across architectures. Mitigation: per
  PR #354 §H-D2, the harness's tabular control (C-d2-arch-control
  7th anchor) is mandatory each architecture run; cross-
  architecture decision uses pre-stated verdict ladder, not
  optimiser-selected best.

---

## §10 Stage gates (mandatory exit criteria per Foundation stage)

| Stage | Mandatory exit criterion | Authoritative artifact |
|---|---|---|
| T0 | continuous; no closure | event-log (operational) |
| T1 | first inspection report emitted; per-candidate dependency inventory + pipeline feasibility classifications recorded | `artifacts/gate_p1_report/<report_id>/gate_p1_report.json` |
| T2 | round-trip report 100% per-file SHA-256 match against `candles_manifest.json` | `artifacts/gate_p2_verification/<verification_id>/gate_p2_retention_verification_report.json` |
| T3 | new epoch dataset (raw / labels / split / row-set / provenance manifests) + new S-B baseline + new S-E control + D-1 PnL validation + scientific adequacy review committed (run-provenance NOT gitignored); exit label `NEW_EPOCH_BASELINE_CONTROL_BUILT` / `NOT_FORMALLY_VERIFIED_YET` (proposed; T3-specific design memo may bind a different label) | `artifacts/v2_expanded_baselines/<manifest_id>/` (new epoch's baseline + control); `docs/design/<manifest_id>_scientific_adequacy_review.md` |
| T4 | F-1..F-7 + S-1..S-6 all executed under the **same accepted contract / provenance boundary**, with run-provenance committed; aggregate verification verdict at a **previously authorised** success label (e.g., `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES` per PR #357); **no new success label minted by this roadmap** | `artifacts/v2_expanded_verification/<verification_id>/v2_expanded_verification_report.json` |

For each Research Track A..G, the per-track design memo (authored
at track-authorisation time) re-states the track's stage gates per
that track's outcome ladder.

---

## §11 Open questions

These items require user judgment before the corresponding track /
stage is authorised.

- **Q1 — Foundation T1 vs T2 parallelism in practice.** Authorise
  PR-B.0 (T1 start) and T2 destination selection simultaneously?
  Recommendation: yes; they share read-only inputs and produce
  distinct artifacts.
- **Q2 — T3 new-epoch span selection.** 730d_BA / 365d_BA /
  3650d_BA? Recommendation: 3650d_BA conditional on Gate P1 PR-B
  inspection report classifying the 3650d candidate as
  `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` or better; else fall
  back to 730d. The 3650d candidate is recommended because it
  spans the largest available trade-history horizon and is the
  least-information-loss epoch construction.
- **Q3 — T4 sentinel verification scope.** Run all F-1..F-7 +
  S-1..S-6 (full), or staged (F-1..F-3 first, then S-1..S-6
  separately)? **Amendment 1 binding (precedence over the prior
  recommendation):** if T4 is staged for review tractability:
  - the F-1..F-3-only stage is **preflight / partial verification
    only**
  - it **cannot emit Tier 1 (FORMALLY_VERIFIED)**
  - it **cannot be combined with later S-1..S-6 artifacts**
    unless a separately designed and approved **staged-
    composition rule** explicitly defines how partial-stage
    artifacts compose into a full-contract verdict
  - the final formal claim requires **all required checks under
    the same accepted contract / provenance boundary** — i.e., a
    single accepted verification run, not a stitched composition
    of partial runs across PRs
  Recommendation: a single full-contract run is the cleanest path.
  If staging is preferred for review tractability, the staged-
  composition rule must be designed before the partial stage
  runs.
- **Q4 — Research Track A.1 (+mtf) authorisation timing.**
  Authorise immediately after T4, or wait for explicit user
  consideration of bear-case scenario (mtf Sharpe drops below
  0.10 on new epoch)? Recommendation: immediate post-T4; A.1 is
  the cheapest re-evaluation, and its outcome conditions Track B.
- **Q5 — Track C architecture order.** S1 LSTM first vs S2 TCN
  first vs S3 Transformer first? Recommendation: S1 first because
  Phase 9.X-C/M-1 already validated the PyTorch + CUDA harness
  infrastructure; S1 setup cost is lowest.
- **Q6 — Track B (Phase 9.X-C residual modes) revival logic.**
  If A.1 NO ADOPT on new epoch, are B-1 / B-2 / B-3 / B-4 still
  worth attempting? Recommendation: B-2 only (cheapest); B-1 / B-3
  / B-4 deferred until Track C result clarifies whether sequence-NN
  architectures have any value on new epoch.
- **Q7 — Track D priority within data-side expansion.** D.1 time
  axis first, vs D.2 economic calendar, vs D.4 interest rate
  spreads? Recommendation: D.1 first (cheapest and orthogonal to
  every other lever); then D.2; then D.4 after Foundation user
  capacity for non-OANDA data integration is confirmed.
- **Q8 — P1..P3 progression independently of Foundation.** Spread
  / slippage / sizing engineering work — authorise during
  Foundation, or hold until Research Tracks begin? Recommendation:
  P2 (snapshotting) immediately authorisable; P1 (model) after P2
  has collected ≥ 4 weeks of empirical spread data; P3
  (engineering) anytime.
- **Q9 — Production migration policy after a Tier-1 verdict.**
  When a Research Track produces a Tier-1 verdict (e.g., A.1
  produces a Tier-1 verdict against the new-epoch S-B baseline
  and S-E control), what is the production migration cadence?
  Recommendation: a per-Track post-Tier-1 design memo authoring
  the migration plan (analogous to PR #365 for PR-B); the
  migration PR is independently authorised. **Amendment 3
  binding:** old-epoch numerics (e.g., 0.158) are **not**
  admissible as Tier-1 success examples; the Tier-1 criterion
  for any Research Track is defined per-track against the
  new-epoch comparators (S-B baseline and S-E control), not
  against any archived old-epoch Sharpe.
- **Q10 — H-B9 confirmation handling.** If Track C (A0-broad)
  produces FALSIFIED_A0_BROAD_NARROW across S1 / S2 / S3, H-B9
  is strongly supported **under the current-data /
  current-contract scope only**. This does **not** declare an
  absolute production ceiling. Strategic options for the
  separate strategic-review memo: (a) continue running Phase
  9.16 v9 20p as the current operational baseline while
  shifting research focus to P1..P3 cost reduction +
  market-regime / asset-class change discussion; (b) continue
  with Track F (A3 learned MoE) at higher complexity; (c)
  escalate to user for strategy-level decision; the label
  `STRUCTURAL_CEILING_HYPOTHESIS_CONFIRMED` is proposed-only at
  this roadmap level and requires a separate strategic-review
  memo to authorise. Recommendation: (c).
- **Q11 — Memo re-authoring trigger.** When does this roadmap
  itself need re-evaluation? Recommendation: (a) when Foundation
  T4 completes (re-state per-track conditions under verified
  surface), (b) when any Track outcome is Tier 1 (production
  migration design), (c) when H-B9 is confirmed or falsified
  (strategic direction), (d) at user request.

---

## §12 Status carry-forward

Unchanged by this PR:

- V2-expanded Stage 2 = `HALTED_INPUT_UNAVAILABLE` (PR #360);
  **may be superseded by new-epoch foundation / verification
  results after T3 / T4**, but the old historic-anchor Stage 2
  route itself is not lifted by new-epoch work
- F-1 = `UNEXECUTABLE_INPUT_UNAVAILABLE` (PR #360); the **old
  F-1 historic-anchor route remains
  `UNEXECUTABLE_INPUT_UNAVAILABLE` unless original historic
  inputs are restored** (Option 1 per PR #360); **new-epoch
  verification under T4 does not repair or reproduce the old
  F-1 historic-anchor route** — it establishes a new F-1
  against the new-epoch baseline, which is a distinct reference
  under a distinct `manifest_id`
- PR #356 audit = `TARGETED_VERIFICATION_REQUIRED`; **may be
  superseded per-PR by future targeted-verification work**, but
  the old eval evidence at #318 / #321 / #325 / #328 / #332 /
  #338 / #342 / #345 / #351 remains at its currently-recorded
  class regardless of new-epoch work
- Phase 27 / 28 / 29.0a verdicts preserved verbatim
- A0-broad β remains halted; eligible to resume under Track C
  upon Foundation T4 completion + A0-broad preflight audit pass
- production baseline = Phase 9.16 v9 20p, Tier 2
  (CONTEMPORANEOUS_CONTRACT_PASS)
- no retention destination selected
- no PR-B.0 authorisation issued; no PR-B.1, B.2 authorisation
  issued
- no Track A..G authorisation issued
- no P1..P3 authorisation issued
- `.gitignore` unmodified; no source code change; no executable
  artifact deposited

**Explicit bindings from Amendment 2 (evidence reconciliation):**

- **Old +mtf numeric claims (v18 Sharpe 0.174; v19 Sharpe
  0.158) are NOT admissible routing evidence** under this
  roadmap. v18 is `INVALID_LOOKAHEAD_NUMERIC`; v19 is
  `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`. See
  Appendix A for citations.
- **Top-K K=2 Sharpe 0.165 (Phase 9.19) and C-3 Sharpe 0.177
  (Phase 9.13) are NOT admissible routing evidence** under
  this roadmap; both are `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_
  USE_FOR_ROUTING`.
- **LSTM Mode A Sharpe 0.061 (Phase 9.X-C/M-1) is
  `FALSIFIED_AT_SCOPE` for Mode A only**; modes B-1 / B-2 /
  B-3 / B-4 and the A0-broad sequence-NN allowlist (S1 LSTM /
  S2 TCN / S3 Transformer per PR #354) remain Tier 5
  (DEFERRED_NOT_FORECLOSED) and are not falsified by the
  Mode A result.
- **New-epoch Track A.1 (+mtf feature-family re-evaluation) is
  a from-scratch evaluation**; it does **not** attempt to
  reproduce 0.158 / 0.174 / 0.165 / 0.177, does **not** use
  any old-epoch numeric as a pass/fail threshold, and does
  **not** auto-authorise production reflection on success.
- **No prior Phase 9.X-B PARTIAL GO / PARTIAL GO+ verdict
  survives as verified or production-relevant evidence unless
  it is re-executed under the new foundation contract**
  (T3 + T4) and the new-epoch evaluation produces an
  independent Tier-1 result under that contract.
- Phase 9.16 v9 20p baseline (Sharpe 0.160) retains
  `VALID_OPERATIONAL_BASELINE` status (Tier 2
  CONTEMPORANEOUS_CONTRACT_PASS) for production-default use
  only; it is **not** admissible as Tier-1 evidence for new
  routing claims.

---

## Closing — what merging this roadmap memo does and does not do

Merging this PR locks the **roadmap structure** — the five-tier
verified surface (§2), the per-phase per-mode status table (§3),
the development philosophy (§4), the Foundation Track shape (§5),
the Research Track shape (§6), the Production-Improvement Track
shape (§7), the sequencing constraints (§8), the risk register
(§9), the stage gates (§10), and the open questions (§11). It
authorises **no** track, no stage, no destination, no architecture.
It modifies **no** prior verdict and changes **no** production
state.

Next step (post-merge): user decides which of the open questions
(§11) to answer first, and authorises the first Foundation stage
(typically T1 PR-B.0). Subsequent stages and Research Tracks each
require their own explicit authorisation per the no-auto-route
binding.

---

## Appendix A — Evidence reconciliation (Amendment 2)

This appendix is the source-of-truth-based reconciliation of past
Phase 9.x / Phase 27-29 numeric claims and verdicts against the
controlled vocabulary defined below. Every entry cites a committed
source document (path + line range) or marks `SOURCE_NOT_FOUND_IN_
REPO`. The roadmap body (§2 / §3 / §4 / §6.A / §6.B / §12) is
updated to reference this appendix.

### Controlled vocabulary

| Label | Meaning | Admissibility for routing / pass-fail / production migration |
|---|---|---|
| `VALID_OPERATIONAL_BASELINE` | static-inspection clean, used as production default under contemporaneous contract; run-provenance may be partial or absent | admissible as production-default baseline only; **not** Tier 1 evidence |
| `FALSIFIED_AT_SCOPE` | NO ADOPT verdict at phase closure for the **specific tested formulation**; narrow scope explicitly recorded | not admissible for the falsified formulation; does not falsify related but distinct formulations |
| `INVALID_LOOKAHEAD_NUMERIC` | numeric was produced under a documented look-ahead / causality bug; numeric is formally invalid | not admissible for any purpose other than archive context on the bug detection itself |
| `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` | numeric exists in a committed source but carries class U on run-provenance or is downstream of an invalidated anchor; phase-closure context only | **not** admissible as routing evidence, pass/fail threshold, or production-migration anchor; may be referenced as historical phase-closure context only |
| `TARGETED_REEVALUATION_REQUIRED_FROM_SCRATCH` | feature family / mechanism is potentially re-evaluable but must be re-implemented and re-evaluated from scratch under the new foundation contract; old numerics are not admissible as anchors | admissible only as a research-track candidate; the re-evaluation is independent of any old-epoch number |
| `DEFERRED_NOT_FORECLOSED` | explicitly preserved for future Phase routing; neither falsified nor tested; design memo binds admissibility conditions where present | admissible as research-track candidate under stated prerequisites |
| `SOURCE_NOT_FOUND_IN_REPO` | citation could not be located in committed sources | informational only; not admissible until citation is established |

### Per-numeric harvest (with committed-source citations)

#### A.1 — +mtf v18 K=3 Sharpe 0.174 (Phase 9.X-B initial claim)

- **Original claim citation:** `docs/design/phase9_x_b_closure_memo.md:3,52` — "PARTIAL GO+ for +mtf alone (Sharpe 0.173 K=2, 0.174 K=3)"
- **Lookahead bug citation:** `docs/design/sharpe_improvement_brief.md:37` — "v19 backtest (`compare_multipair_v19_causal.py`) fixed a `_add_multi_tf_extended_features` lookahead bug that had inflated Phase 9.X-B's claimed +mtf Sharpe from a true 0.158 to 0.174 (~9% inflation)."
- **Specific bug location citation:** `docs/design/sharpe_improvement_brief.md:182-183` — "`_add_multi_tf_extended_features` (v18) used `df.resample(...).reindex(idx, method='ffill')` without a `shift(1)`. Daily bar labelled 2026-01-15 contains the 23:55 close; ffill at m5 10:00 leaked the future close (~14h lookahead). Fixed in v19 (`raw.shift(1).reindex(...)`, matching the same-script `_add_upper_tf` pattern)"
- **Final label:** `INVALID_LOOKAHEAD_NUMERIC`
- **May be used for routing?** No
- **May be used for pass/fail threshold?** No
- **May be used for production migration?** No
- **May be used as historical context?** Yes (archive note on how lookahead was detected)

#### A.2 — +mtf v19 K=3 Sharpe 0.158 / K=2 ≈ 0.157 (Phase 9.X-B causal fix)

- **Citation:** `docs/design/sharpe_improvement_brief.md:2` — "What is the most likely path to push the backtest's per-trade SELECTOR Sharpe from 0.158 to ≥ 0.20"
- **Anchor citation:** `docs/design/phase9_x_jlmno_series_closure_memo.md:5` — "Anchor: Phase 9.X-E v19 causal +mtf K=1 — pip Sharpe 0.158"
- **Causal-fix module citation:** `docs/design/phase9_x_e_live_deploy_plan.md:30-31` — "Production `_compute_mtf_features` is causal by construction (operates on candles already filtered to `timestamp < as_of_time` by `FeatureService.build`)"
- **Class U on run-provenance:** Phase 9.X-B is out of PR #356 audit scope but the same gitignore pattern applies (sweep_results not committed). The numeric is downstream of v18 (`INVALID_LOOKAHEAD_NUMERIC`) and is thus a reduction of a now-invalid anchor.
- **Final label:** `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`
- **May be used for routing?** No
- **May be used for pass/fail threshold?** No
- **May be used for production migration?** No
- **May be used for research prioritisation?** Yes, but only as part of the §4.2 working-hypothesis pattern (not as evidence that the +mtf feature family will succeed)
- **May be used as historical context?** Yes (anchor for understanding Phase 9.X-B closure intent)

#### A.3 — Top-K K=2 Sharpe 0.165 (Phase 9.19)

- **Phase-closure citation:** `docs/design/phase9_19_closure_memo.md:3` — "Closed — PARTIAL GO at K=2 lgbm_only (modest +25% PnL, +0.005 Sharpe over baseline)"
- **Per-cell number citation:** `docs/design/phase9_19_closure_memo.md:40` — "lgbm_only | 2 | 0.165 | 10,219.8 | 2.6% | 1.25x"
- **Verdict qualification citation:** `docs/design/phase9_19_closure_memo.md:89,100` — "Verdict: PARTIAL GO — Naive K=2 lgbm_only achieves PnL +25% with Sharpe +0.005 over baseline, DD%PnL within bounds. However: the lift is modest, not the breakthrough we hoped for."
- **Class U citation:** `docs/design/phase27_29_tabular_eval_validity_audit.md:309` — "Per-PR outcome: PR_TARGETED_VERIFICATION_REQUIRED (no Class A; static-code clean throughout; structural Class U on run-provenance)" — Phase 27.0d S-E anchor PR #325 is in audit scope.
- **Final label:** `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`
- **May be used for routing?** No
- **May be used for pass/fail threshold?** No
- **May be used for production migration?** No
- **May be used for research prioritisation?** Yes (Top-K mechanism remains a research-track candidate)
- **May be used as historical context?** Yes (phase closure verdict)

#### A.4 — C-3 kill switches Sharpe 0.177 (Phase 9.13)

- **Phase-closure citation:** `docs/design/phase9_13_closure_memo.md:3` — "Closed — SOFT GO+ at SELECTOR net Sharpe 0.177 (C-3 only)"
- **Number citation:** `docs/design/phase9_13_closure_memo.md:40` — "C-3 only (kill switches) | 0.177 | 6,275 | −7%"
- **Closure rationale citation:** `docs/design/phase9_13_closure_memo.md:48` — "Phase 9.13 closes at SOFT GO+ via C-3 only. SELECTOR net Sharpe 0.177 is up from v5's 0.160 (+0.017) at the cost of just 7% of total profit."
- **Class U inheritance:** C-3 is a predecessor of Phase 27 spine; the same sweep_results gitignore pattern applies; the per-PR audit anchors that inherit C-3 are class U on run-provenance per `docs/design/phase27_29_tabular_eval_validity_audit.md:214-235` (U-1 finding).
- **Final label:** `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`
- **May be used for routing?** No (not as a verified ceiling)
- **May be used for pass/fail threshold?** No
- **May be used for production migration?** Production-operational (kill-switches mechanism already shipped as a risk control); however, the 0.177 numeric is not an admissible "verified ceiling" for future routing
- **May be used as historical context?** Yes (SOFT GO+ phase closure; risk-control evidence)

#### A.5 — LSTM Mode A Sharpe 0.061 (Phase 9.X-C/M-1)

- **Number citation:** `docs/design/sharpe_improvement_brief.md:89` — "| 9.X-C | LSTM Mode A | LSTM replaces LGBM | 7.7× | 0.13× | 0.061 |"
- **NO ADOPT rationale citation:** `docs/design/sharpe_improvement_brief.md:154-161` — "Result: per-trade Sharpe 0.061 vs LGBM baseline 0.149. Why it failed: Class weights overshot: LSTM produced 7.7× too many trades, per-trade EV collapsed. Per-rank Sharpe inversion: rank-1 worse than rank-3 → confidence ranking is poorly calibrated. LSTM has no prior advantage on m5 FX bars; not enough sequence signal beyond what LGBM already extracts."
- **Scope binding (Mode A only):** Phase 9.X-C/M-1 closure memo confirms B-1..B-4 deprioritised but not foreclosed; A0-broad sequence-NN allowlist (PR #354 S1 LSTM / S2 TCN / S3 Transformer) is an entirely separate formal framework. The Mode A falsification does not falsify B-1..B-4 or A0-broad.
- **Class U on run-provenance:** Phase 9.X-C is out of PR #356 audit scope but the same artifact-commitment pattern likely applies (presumed Class U risk on the 0.061 numeric).
- **Final label:** `FALSIFIED_AT_SCOPE` (Mode A full-replacement formulation only; numeric carries Tier-3 Class-U risk)
- **May be used for routing?** No (Mode A falsification does not authorise Mode A production reflection; the 0.061 numeric is not admissible as a ceiling)
- **May be used for pass/fail threshold?** No
- **May be used for production migration?** No
- **May be used as historical context?** Yes (Mode A falsification for exclusion logic; B-1..B-4 and A0-broad untouched)
- **Does this falsify B-1 / B-2 / B-3 / B-4?** No — they remain `DEFERRED_NOT_FORECLOSED` (Tier 5)
- **Does this falsify A0-broad sequence-NN allowlist (S1 / S2 / S3)?** No — A0-broad remains `DEFERRED_NOT_FORECLOSED` (Tier 5)

#### A.6 — Phase 9.16 v9 20p baseline Sharpe 0.160 (production default)

- **Citation:** `docs/design/phase9_16_closure_memo.md:38` — "10-pair v9 spread (base) | 0.152 ... 20-pair v9 spread | 0.160"
- **Production default citation:** `docs/design/phase9_16_closure_memo.md:102` — "Production default: 20-pair v9 spread bundle, no CSI features."
- **Tier 2 basis:** static inspection clean at PR #338 / #342 / #345 / #351; sweep_results artifact absent at all four merge SHAs (Class U on run-provenance, but not contested for production-operational use under the contemporaneous contract).
- **Final label:** `VALID_OPERATIONAL_BASELINE`
- **May be used for routing?** Yes, as the production-default baseline reference (Tier 2 / CONTEMPORANEOUS_CONTRACT_PASS); **not** as Tier-1 evidence for new claims
- **May be used for pass/fail threshold?** Yes, as the **comparator baseline** for backtest / paper / live comparisons under the contemporaneous contract; **not** as a Tier-1 ceiling
- **May be used for production migration?** Already in production; admissible as the migration reference until a Tier-1 alternative is established under the new foundation contract
- **May be used as historical context?** Yes

#### A.7 — Phase 27-29 tabular spine (9 β-evals: #318 / #321 / #325 / #328 / #332 / #338 / #342 / #345 / #351)

- **Aggregate verdict citation:** `docs/design/phase27_29_tabular_eval_validity_audit.md:525-534` — "Aggregate outcome: `TARGETED_VERIFICATION_REQUIRED`. The Phase 27-29 tabular β-eval spine ... is static-code clean at each PR's own merge-time snapshot, under each PR's own merged design memo. No formal validity blocker (Class A) was identified..."
- **U-1 finding citation:** `docs/design/phase27_29_tabular_eval_validity_audit.md:214-235` — "U-1 — Machine-readable artifact run-provenance is gitignored across all 9 PRs ... artifacts/stageXX_Xy/sweep_results.parquet / sweep_results.json / aggregate_summary.json / val_selected_cell.json / sanity_probe.json [all] gitignored ... Consequence: the eval_report.md numerics cannot be independently cross-checked"
- **U-2 finding citation:** `docs/design/phase27_29_tabular_eval_validity_audit.md:237-243` — "U-2 — Sanity-probe HALT outcome cannot be independently verified"
- **Final label (aggregate):** `TARGETED_VERIFICATION_REQUIRED` (Tier 3); the sub-phase narrow verdicts (FALSIFIED_A0_NARROW etc.) preserve their stated narrow scope; the spine as a whole is **not** formally verified.

#### A.8 — A0-narrow (Phase 28.0c AR1..AR4)

- **Verdict citation:** `docs/design/phase27_29_tabular_eval_validity_audit.md:395,408` — "Verdict: all 4 FALSIFIED_ARCH_INSUFFICIENT; aggregate FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0). NARROW vs ALL distinction explicit in PR #344 design memo §12.2."
- **Scope binding:** A0-narrow tabular topology axis is falsified; A0-broad sequence/NN remains deferred-not-foreclosed.
- **Final label:** `FALSIFIED_AT_SCOPE` (narrow tabular only)
- **Does this falsify A0-broad?** No — A0-broad remains `DEFERRED_NOT_FORECLOSED`.

#### A.9 — A2-narrow (Phase 29.0a T1..T4)

- **Verdict citation:** `docs/design/phase27_29_tabular_eval_validity_audit.md:415,427` — "Verdict: all 4 FALSIFIED_TARGET_INSUFFICIENT; aggregate FALSIFIED_A2_NARROW (NEVER FALSIFIED_ALL_A2); R-T3 = FALSIFIED_under_T3"
- **Final label:** `FALSIFIED_AT_SCOPE` (narrow targets only)
- **Does this falsify A2-broad?** No — A2-broad remains `DEFERRED_NOT_FORECLOSED`.

#### A.10 — A0-broad WIP (Phase 29.0b-α)

- **Halted-state citation:** `docs/design/phase27_29_tabular_eval_validity_audit.md:586` — "A0-broad formal β remains halted. Existing WIP branch `research/phase29-0b-beta-a0-broad-sequence-eval` (tip `9ac8fda`) remains INVALID_FOR_FORMAL_VERDICT on the remote."
- **Final label:** `DEFERRED_NOT_FORECLOSED`

### Roadmap section update summary (cross-reference)

| Roadmap section | Update applied |
|---|---|
| §0 Amendment history | Amendment 1 + 2 + 3 history entries added |
| §2 Tier 3 demoted bullets | Mode A bullet updated (0.061 << mtf 0.174 archival-only); §3 Phase 9.X-D DXY synthetic NO ADOPT description updated (archived comparison) — Amendment 3 |
| §3 status table | Mode B-2 / +dxy alone / +dxy+mtf rows updated: historic comparisons against now-invalid mtf v18 0.174 anchor restated as archival closure context only (Amendment 3) |
| §4.4 H-B9 / Track C outcome wording | softened to "would materially weaken H-B9 under the tested scope" / "would strongly support H-B9 under the current-data / current-contract scope"; neither outcome alone declares an absolute production ceiling; strategic review required (Amendment 3) |
| §5.5 T4 Scope | "or stricter `SENTINEL_VERIFICATION_COMPLETE` if all sentinels pass" removed; Scope wording aligned with Exit-criteria binding (Amendment 3) |
| §7.P1 | "verified P&L lever" wording removed; Phase 9.10 cost-sensitivity classified as historical / operational context (Tier 3), not Tier-1 verified research evidence (Amendment 3) |
| §11.Q9 | "e.g., A.1 Sharpe ≥ 0.158 on new epoch" example removed; replaced with "Tier-1 verdict against the new-epoch S-B baseline and S-E control" (Amendment 3) |
| §11.Q10 | "accept Phase 9.16 v9 20p as production ceiling" reframed to "continue running Phase 9.16 v9 20p as the current operational baseline" plus separate strategic-review memo binding; `STRUCTURAL_CEILING_HYPOTHESIS_CONFIRMED` label proposed-only at roadmap level (Amendment 3) |
| §1 Non-scope | +mtf / Top-K / C-3 numerics demoted to `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`; v18 reclassified as `INVALID_LOOKAHEAD_NUMERIC` |
| §2 Tier 1 admissible language | "cleared F-1 / F-2 / F-3 alone" forbidden; full applicable contract required |
| §2 Tier 3 currently-in-tier | numerics demoted with citation pointers to Appendix A |
| §3 status table | per-row controlled-vocabulary labels applied to v18 / v19 / Top-K / C-3 / Mode A |
| §4.2 extraction-vs-expansion | reframed as working hypothesis (not verified principle); does not supply pass/fail thresholds |
| §5.4 T3 | exit criteria restricted to dataset / baseline / control / D-1 / scientific adequacy / run-provenance committed; sentinel verification moved entirely to T4; exit label proposed `NEW_EPOCH_BASELINE_CONTROL_BUILT` / `NOT_FORMALLY_VERIFIED_YET` |
| §5.5 T4 | `SENTINEL_VERIFICATION_COMPLETE` retracted; no new success label minted by this roadmap |
| §6.A | A.1 / A.2 / A.3 reframed as from-scratch feature-family / mechanism re-evaluations; old numerics archived context only; no production reflection auto-authorised |
| §6.B | decision table over A.1 outcome; old 0.174 / 0.158 / 0.061 arithmetic removed |
| §6.C | H-B9 all-architecture failure wording softened; strategic review required before declaring a production ceiling |
| §6.D | external-data provenance / retention gate added |
| §7 | P1 / P2 / P3 risk wording corrected; production safety gates explicit |
| §8.2 | T1 / T2 parallelism clarified; T2 deposit ≠ epoch adoption |
| §10 | stage gate table T3 / T4 rows updated |
| §11.Q3 | T4 staged-verification binding (preflight only) |
| §12 | carry-forward precision (old historic-anchor F-1 not repaired by new-epoch work); explicit bindings from Amendment 2 |
| Appendix A (this) | controlled vocabulary + per-numeric harvest |

### Confirmations

This appendix and the roadmap body updates are doc-only. **No
experiment was re-run.** **No raw data was read.** **No model
was executed.** **No SHA was computed.** **No production code
or configuration was changed.** **No prior verdict file was
modified.** **No auto-route was created.** No source code, test,
artifact, hash, fetch, credential, label, or model execution
occurred. Source-of-truth citations come from committed
documents under `docs/design/` listed above; no out-of-repo
data was consulted.
