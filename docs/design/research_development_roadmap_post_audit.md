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

- Amendment 1 (this PR): T3/T4 responsibility separation (sentinel
  verification moved entirely to T4); retracts the unapproved
  `SENTINEL_VERIFICATION_COMPLETE` label; tightens Tier 1 language to
  require the full applicable verification contract; reframes Track A
  outcome ladders to drop fixed numeric thresholds (illustrative only);
  T4 staged-verification wording: F-1..F-3-only stage is preflight /
  partial verification only and cannot emit Tier 1; H-B9 / Track C
  all-architecture-failure wording softened (strong evidence for
  current-data / current-contract seam-exhaustion hypothesis; strategic
  review required before declaring a production ceiling); Track D
  external-data sources gated by mini data-source feasibility +
  retention/provenance gate; Production P1/P2/P3 "progress-without-
  risk" wording replaced with "independent of research-signal
  verification contamination, but still subject to production
  engineering risk controls"; Track B conditional logic rewritten as a
  decision table; T1/T2 parallelism clarified to bind that T2 deposit
  ≠ epoch adoption; §12 carry-forward wording made precise (old F-1
  historic-anchor route remains UNEXECUTABLE_INPUT_UNAVAILABLE; new-
  epoch verification does not repair or reproduce it).

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
  pre-Phase-9.16 baselines (incl. C-3 0.177) remain at
  TARGETED_VERIFICATION_REQUIRED or worse.
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

- "cleared the F-1 / F-2 / F-3 foundation checks" (partial-stage
  verification alone is not Tier 1; see §11.Q3 wording binding)
- attributing Tier 1 to a result that passed only a staged subset of
  the verification contract

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

- +mtf K=3 (Phase 9.X-B v19 causal fix, nominal Sharpe 0.158) +
  +mtf K=2 (nominal Sharpe 0.157)
- Top-K K=2 (Phase 9.19, nominal Sharpe 0.165) and the entire
  Phase 9.19 J-series
- C-3 kill switches (Phase 9.13, nominal Sharpe 0.177) — pre-Phase-27
  predecessor of the spine but, by inheritance, subject to the same
  unverifiable run-provenance
- Phase 9.X-C M-1 LSTM Mode A (nominal Sharpe 0.061) — out of audit
  scope but same artifact-commitment pattern; presumed class-U risk
  until verified otherwise
- All 9 Phase 27-29 β-evals (#318, #321, #325, #328, #332, #338,
  #342, #345, #351) — explicit aggregate
  `TARGETED_VERIFICATION_REQUIRED` per PR #356 §4

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
- Phase 9.X-C M-1 LSTM Mode A (NO ADOPT — Sharpe 0.061 << mtf
  0.174 / baseline 0.160; note Tier-3 caveat on Class-U risk above)
- Phase 9.X-D DXY synthetic (NO ADOPT — both +dxy alone and +dxy+mtf
  worse than mtf alone)
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
| 9.13 | C-3 kill switches | Sharpe 0.177 | Tier 3 | Predecessor of Phase 27 spine; Class-U risk by inheritance |
| 9.15 | spread bundle | PnL +13%, DD -17% | Tier 2 | Adopted into Phase 9.16 production default |
| 9.15 | spread+RH bundle | PnL +15.5%, train 2x | Tier 4 (in-sample leak) | Found to have in-sample leakage; partial-pair only |
| 9.16 | v9 20-pair universe expansion | PnL +20.1% vs v5, DD%PnL 2.5% | **Tier 2 (production default)** | Pair universe 10→20; current production baseline |
| 9.16 | CSI Layer-1 features | NO ADOPT | Tier 4 | -15% PnL on SELECTOR; redundant with xp_* |
| 9.17 | MR+BO ensemble (no threshold) | NO ADOPT | Tier 4 | Trade-rate 15x; Sharpe collapsed |
| 9.17b | confidence threshold post-filter | NO ADOPT | Tier 4 | +0.005 Sharpe; per-trade EV constraint binding |
| 9.18 | bucketed TP/SL (H-1) | NO ADOPT | Tier 4 | Low-bucket -19% EV drag |
| 9.18 | partial exit (H-2) | NO ADOPT | Tier 4 | 80% SL-before-partial rate |
| 9.19 | Top-K Naive K=2 | Sharpe 0.165 / PnL +25% | Tier 3 | PARTIAL GO at phase closure; Class U on run-provenance |
| 9.19 | Top-K Diversified K=2 | similar | Tier 3 | Same Class-U inheritance |
| 9.X-A | LGBMRegressor on label_return | NO ADOPT | Tier 4 | Best Sharpe 0.092; per-trade EV collapse |
| **9.X-B** | **+vol feature group** | worse than mtf alone | Tier 4 | Redundant with ATR / BB_width / multi-TF h1_volatility |
| **9.X-B** | **+moments feature group** | K=1 Sharpe 0.145 (< baseline) | Tier 4 | Noisy; skewness/kurtosis/autocorr |
| **9.X-B** | **+mtf K=3 (v18 reported)** | Sharpe 0.174 — **lookahead bug** | Tier 4 (the v18 number) | `shift(1)` missing in `_add_multi_tf_extended_features` |
| **9.X-B** | **+mtf K=3 (v19 causal fix)** | Sharpe 0.158 (-9.2% vs v18) | Tier 3 | Class U on run-provenance; PARTIAL GO+ rescinded under v19 |
| **9.X-B** | **+mtf K=2 (v19 causal fix)** | Sharpe ≈ 0.157 (estimate) | Tier 3 | Same status as K=3 |
| **9.X-B** | **+all (vol+moments+mtf)** | < +mtf alone | Tier 4 | Multicollinearity |
| **9.X-C** | **M-1 Mode A (Full LSTM replacement)** | Sharpe 0.061; 7.7× trade rate; 0.13× per-trade EV | Tier 4 (with Tier-3 Class-U risk caveat) | Class imbalance + no discrimination + information saturation |
| **9.X-C** | **Mode B-1 (Feature stacking, LSTM hidden → LGBM)** | **untried** | **Tier 5** | Tier-2 deprioritised at M-1 closure; not foreclosed |
| **9.X-C** | **Mode B-2 (Output averaging)** | **untried** | **Tier 5** | Tier-2 deprioritised; early-fail logic at M-1 closure (0.061 avg ≈ 0.118 < mtf 0.174); not foreclosed |
| **9.X-C** | **Mode B-3 (Regime gating)** | **untried** | **Tier 5** | Tier-2 deprioritised at M-1 closure; not foreclosed |
| **9.X-C** | **Mode B-4 (Specialisation)** | **untried** | **Tier 5** | Tier-2 deprioritised at M-1 closure; not foreclosed |
| 9.X-D | +dxy alone | NO ADOPT | Tier 4 | K=3 Sharpe 0.154 < mtf 0.174 |
| 9.X-D | +dxy+mtf | NO ADOPT | Tier 4 | K=3 Sharpe 0.168 < mtf 0.174 |
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

### §4.2 Extraction vs Expansion principle

Phase 9.x arc evidence (mtf was the single PARTIAL GO+; all other
extraction-tricks NO ADOPT): clever extraction from the same data
fails; expanding the data succeeds. Concretely:

- 5 NO ADOPT phases on extraction-tricks (Phase 9.17 ensemble,
  9.17b confidence threshold, 9.19 multi-pick SELECTOR Top-K, 9.X-A
  regression labels, 9.X-C M-1 LSTM model class)
- 1 PARTIAL GO+ on horizon expansion (9.X-B mtf at 4h / daily;
  v19 causal fix Sharpe 0.158)
- 1 NO ADOPT on cross-asset expansion (9.X-D DXY)

The 5/6 majority is "more clever extraction fails"; the 1/6 minority
(mtf) is "expanding the data succeeds". This biases future research:
**data-side expansion is preferred over architecture / extraction
expansion** at equal cost. Architecture-side expansion (LSTM Mode A,
A0-broad sequence-NN) is admissible only when (a) the data side is
also expanded, or (b) a structural reason makes the architecture
not subject to the extraction-trick pattern (e.g., calibrated
confidence ranking with explicit per-trade EV stability).

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
completion**, because a successful A0-broad rejects H-B9 (and lifts
the production ceiling); a failed A0-broad confirms H-B9 (and
narrows the candidate set further). Either outcome is informative.

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
- emit verification report with allowed success label
  `SENTINEL_VERIFICATION_PARTIAL_RECOVERY_MAJOR_AXES` (per PR #357)
  or stricter `SENTINEL_VERIFICATION_COMPLETE` if all sentinels
  pass

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

**Scope:** the Tier-3 entries from §3 receive a clean re-execution
under the V2-expanded contract on the new epoch. The purpose is to
discover whether they survive the elimination of Class U on
run-provenance and the new epoch's possibly-different market
regime.

**Old-epoch nominal Sharpe values are archived context only.** They
are not executable pass/fail gates for new-epoch evaluation. The
authoritative comparators are the new-epoch S-B baseline and S-E
control (built at T3). Exact thresholds and outcome ladders are
defined in each track-specific design memo authored after T3 / T4
completion, not in this roadmap.

- **A.1 — +mtf K=2 / K=3 v19 causal fix.** Re-execute on new epoch
  under V2-expanded contract. Old context: Phase 9.X-B v19 nominal
  Sharpe ≈ 0.158 (K=3) — archived only. New-epoch evaluation
  compares against new S-B baseline and S-E control; outcome
  ladder defined in the per-track design memo. **Illustrative only
  (not binding):** large positive delta vs S-B → candidate Tier 1
  on T4 completion; near-zero or negative delta → candidate Tier 3
  or Tier 4 depending on the track-specific ladder. No numeric
  thresholds are binding here.
- **A.2 — Top-K K=2 (Phase 9.19).** Re-execute on new epoch with
  Top-K execution gateway (per PR #216 follow-up requirement).
  Same evaluation framing as A.1 (S-B / S-E comparators; track-
  specific ladder).
- **A.3 — C-3 kill switches (Phase 9.13).** Re-execute on new
  epoch. Caveat: C-3 was a predecessor of Phase 27 spine; it is
  inheritable rather than directly re-implementable. The actual
  re-execution may need to map C-3 mechanism onto the new epoch's
  signal / state schema. Same evaluation framing as A.1.

**Production reflection.** A Tier 1 research result does **not**
automatically authorise production reflection. Any production
migration requires (a) a separate migration design memo, (b) live /
paper safety gates (per §7 P1..P3 and `phase9_x_e_live_deploy_plan
.md` G1 / G2 / G3 lineage), and (c) explicit user authorisation.

**Authoring shape:** one design memo + one implementing PR per
candidate (A.1, A.2, A.3 each); sentinel verification re-run under
T4 contract.

### §6.B Track B — Phase 9.X-C residual LSTM modes (B-1, B-2, B-3, B-4)

**Prerequisite:** Foundation T4 complete **and** Track A.1 (+mtf)
outcome known.

**Decision table (Amendment 1):**

| Track A.1 outcome on new epoch | B-1 / B-3 / B-4 eligibility | B-2 eligibility |
|---|---|---|
| **A.1 succeeds (Tier 1 under T4)** | **eligible** under original cost estimates (B-1 ≈ 2 days; B-3 ≈ 6 days; B-4 similar) | **low priority** (output-averaging with a verified mtf signal has limited upside) |
| **A.1 fails (Tier 4 at scope)** | **lower priority** than Track D / data-side expansion (extraction-vs-expansion bias §4.2) | **may be considered only by separate design memo** that re-justifies the formulation against the new baseline; not automatically revived |
| **A.1 ambiguous (Tier 3 or inconclusive ladder result)** | **defer** B-tracks until Track C.1 (A0-broad S1) or Track D.1 (time-axis) result clarifies the architecture-vs-data binding | **defer** under same condition |

In all three rows, Track D (data-side expansion) retains higher
priority than Track B (architecture / extraction tricks) per the
§4.2 extraction-vs-expansion principle. Track B candidates require
explicit user authorisation; the decision table above is a
recommendation, not an auto-route.

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
  is not authorised by an all-architecture FALSIFIED_A0_BROAD_NARROW
  result alone. Pivot priority shifts toward Track D (data
  expansion) and toward broader scope re-evaluation, but only
  through a separately authorised strategic-review memo.

**Scope discipline:** `FALSIFIED_A0_BROAD_NARROW` is **narrow**
even when emitted across all of S1 / S2 / S3. The label
`FALSIFIED_ALL_A0_BROAD` is **never** to be written under this
roadmap; it would require a separately authorised broader
saturation contract that defines what "all A0-broad" means
beyond the current 3-architecture allowlist.

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
information content materially, the track must explicitly define
whether it is being added as:

- **additive epoch extension** (same `manifest_id`, extended
  inputs declared in a new manifest section), or
- **a new epoch** (new `manifest_id`, full T3 / T4 cycle re-run)

The choice is recorded in the sub-track's design memo and binds
how the sub-track's results integrate with prior baseline /
control.

**Scope (in extraction-vs-expansion priority order per §4.2):**

- **D.1 — Time-axis features.** Session (Asia / Europe / NY),
  day-of-week, month, holiday distance, fed-meeting distance.
  Cheaper because timestamp-derived from existing OANDA bytes —
  no external source needed. Still requires (a) causality check
  (no future-bar timestamp leakage; e.g., distance-to-event
  must use only events whose timestamp is strictly past) and
  (b) split-leakage check (per-split distribution of
  session / month / holiday categories must not differ in a way
  that conflates structural label imbalance with predictor
  signal). ~3 days. Untried at depth.
- **D.2 — Economic calendar / event-distance.** Originally a
  Phase 9.X-D candidate; not yet tried. ~2-3 days using OANDA
  Labs API or self-built calendar. **Subject to the external-data
  provenance/retention gate above.** Mid-cost.
- **D.3 — Cross-asset re-evaluation.** Phase 9.X-D DXY synthetic
  NO ADOPT — re-evaluate at A0-broad sequence-NN architecture
  (Track C) if available, since DXY as orthogonal feature may
  behave differently under sequence-NN than under tabular
  LightGBM. DXY synthetic uses existing OANDA bytes (derived
  from PAIRS_20), so it does not require the external-data gate;
  however, additional cross-asset sources (e.g., true DXY
  futures, gold, VIX, indices not in OANDA Japan practice
  account) would.
- **D.4 — Interest rate spreads.** US 2y/10y, JP, EU, AU rate
  differentials. Requires non-OANDA data source (FRED / Bloomberg
  / other). **Subject to the external-data provenance/retention
  gate above.** ~3-5 days.
- **D.5 — Orderbook microstructure.** Most expensive (~5+ days,
  non-OANDA data). Most informative if successful. Conditional on
  Track C result and Track D.1-D.4 outcomes. **Subject to the
  external-data provenance/retention gate above.**
- **D.6 — Pair universe expansion (20 → 30).** Cheap if pair data
  available; new epoch construction (T3) may include a wider pair
  set as a parameter. Authorisation deferred to T3 construction
  decision. If additional pairs require an external data source
  (e.g., a pair not retained under the OANDA 2026-05-31 archive),
  the **external-data provenance/retention gate above applies**.

**Authoring shape:** per sub-track, one design memo + one
implementing PR. Each runs under V2-expanded contract; each
respects the extraction-vs-expansion principle (data-side first);
each external-data sub-track satisfies the mini data-source
feasibility + retention/provenance gate before model evaluation.

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
established 1pip → 0.5pip Sharpe sensitivity (Sharpe more than
doubles), so spread cost reduction is a verified P&L lever.

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
  before production use.** Replacing the fixed-pip spread with an
  empirical profile alters per-trade economics and re-routes
  marginal trade-pass / trade-block decisions; A / B
  paper-comparison required before any production switch.
- **P3 execution / sizing changes require production safety gates,
  rollback plan, and risk limits.** Margin accounting, per-pair
  max position, drawdown-aware sizing, and order-execution checks
  each affect live order flow; each requires an explicit
  rollback plan and a pre-stated risk limit (max position / max
  daily loss / max consecutive losses) that triggers automatic
  pause.

Each of P1 / P2 / P3 still requires **explicit user authorisation
plus a design memo before any production code changes**. Tracks
are eligible to be authorised **at any time** (independent of
Foundation status), but no track auto-routes to production.

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

- T2 may proceed with depositing the 3650d_BA bytes
  irrespective of which epoch span will eventually be selected
- T3 may still construct the epoch at 730d_BA / 365d_BA / 3650d_BA
  (or any other admissible span discovered at T1) regardless of
  what T2 deposited
- T2 deposit / adoption **must not bind a final epoch span unless
  the chosen span is consistent with Gate P1 PR-B findings** from
  T1 — i.e., T1 evidence is the gate for which spans are
  candidate, T2 deposit covers the retained input, and T3 makes
  the final epoch-span decision under combined evidence

T3 (new epoch construction) depends on T1 (the inspection
report's dependency / pipeline feasibility classifications inform
whether the epoch's required-input dependency inventory is
satisfied) and T2 (durable byte retention is binding under
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
  - it **cannot be combined with later S-1..S-6 artifacts** unless
    a separately designed and approved **staged-composition rule**
    explicitly defines how partial-stage artifacts compose into a
    full-contract verdict
  - the final formal claim requires **all required checks under
    the same accepted contract / provenance boundary** — i.e., a
    single accepted verification run, not a stitched composition
    of partial runs across PRs
  Recommendation: a single full-contract run is the cleanest path.
  If staging is preferred for review tractability, the staged-
  composition rule must be designed before the partial stage runs.
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
  Sharpe ≥ 0.158 on new epoch), what is the production migration
  cadence? Recommendation: a per-Track post-Tier-1 design memo
  authoring the migration plan (analogous to PR #365 for PR-B);
  the migration PR is independently authorised.
- **Q10 — H-B9 confirmation handling.** If Track C (A0-broad)
  produces FALSIFIED_A0_BROAD_NARROW across S1 / S2 / S3, H-B9
  is strongly supported. Strategic options: (a) accept Phase 9.16
  v9 20p as production ceiling and shift focus to P1..P3 cost
  reduction + market-regime / asset-class change discussion; (b)
  continue with Track F (A3 learned MoE) at higher complexity;
  (c) escalate to user as `STRUCTURAL_CEILING_HYPOTHESIS_CONFIRMED`
  for strategy-level decision. Recommendation: (c).
- **Q11 — Memo re-authoring trigger.** When does this roadmap
  itself need re-evaluation? Recommendation: (a) when Foundation
  T4 completes (re-state per-track conditions under verified
  surface), (b) when any Track outcome is Tier 1 (production
  migration design), (c) when H-B9 is confirmed or falsified
  (strategic direction), (d) at user request.

---

## §12 Status carry-forward

Unchanged by this PR:

- V2-expanded Stage 2 = `HALTED_INPUT_UNAVAILABLE` (PR #360); **may
  be superseded by new-epoch foundation / verification results
  after T3 / T4**, but the old historic-anchor Stage 2 route
  itself is not lifted by new-epoch work
- F-1 = `UNEXECUTABLE_INPUT_UNAVAILABLE` (PR #360); the **old F-1
  historic-anchor route remains `UNEXECUTABLE_INPUT_UNAVAILABLE`
  unless original historic inputs are restored** (Option 1 per
  PR #360); **new-epoch verification under T4 does not repair or
  reproduce the old F-1 historic-anchor route** — it establishes a
  new F-1 against the new-epoch baseline, which is a distinct
  reference under a distinct `manifest_id`
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
