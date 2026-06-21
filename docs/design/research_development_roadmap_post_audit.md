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

- Amendment 7 (this PR): new section §11B "Root Logic
  Reassessment / Profit Logic Audit" added between §11A and
  §11. **§11B is not a Research Track**; it is a diagnostic
  layer to be authored / reviewed **before** running the next
  research track, to address why historical research-frame
  Sharpe / Spearman / phase-closure verdicts did not convert
  reliably to monetisable profit (Phase 28 §10 research
  baseline NEGATIVE; Phase 27.0d C-se Spearman PASS + Sharpe
  -0.483; Phase 9.19 Top-K rank-3 -0.054; Phase 9.X-C/M-1
  trade-rate explosion + per-trade EV collapse; Phase 9.X-J/L/M
  realism degradation; 9/9 val-selector C-sb-baseline pick).
  Subsections: §11B.1 Objective mismatch audit (train objective
  vs val selector vs rank metrics vs gross/net Sharpe vs
  per-trade EV vs production-realistic PnL); §11B.2 Label /
  target logic audit (direction vs trade/no-trade vs return
  magnitude vs exit-aware vs risk-adjusted; cost-hurdle inside
  label; entry/exit-mechanics coherence; class imbalance;
  selected-trade EV priority); §11B.3 Selection / ranking
  logic audit (rank monotonicity by decile; selected-trade EV
  by score bucket; per-pair overlap; calibration; score
  distribution stability; cost-adjusted selected-trade PnL by
  rank); §11B.4 Cost hurdle / execution realism audit (cost
  inside training target vs selector vs post-filter; edges
  smaller than spread; gross-vs-net mismatch; dynamic cost
  hurdle; spread/time-of-day/liquidity inside the selector);
  §11B.5 Trade unit / horizon audit (horizon too short for
  alpha after costs; feature-horizon alignment; TP/SL
  destroying signal; partial-exit / dynamic-SL/TP mismatch;
  direction vs path-aware outcome); §11B.6 Baseline and
  comparator audit (new-epoch S-B + S-E + cash/no-trade +
  production Phase 9.16 v9 20p + cost-adjusted hurdle baseline
  required; beating a negative research baseline insufficient;
  forbidden language list); §11B.7 Alpha upper-bound / oracle
  diagnostics (cost-free vs cost-adjusted oracle; per-pair /
  per-regime / perfect-rank oracle; label separability;
  IC/MI; score-to-PnL monotonicity; contribution
  decomposition); §11B.8 13-item root-cause taxonomy
  (NO_SIGNAL / SIGNAL_NON_MONETISABLE / COST_ERASED_EDGE /
  RANKING_INVERSION / TRADE_RATE_EXPLOSION /
  PER_TRADE_EV_COLLAPSE / REGIME_INSTABILITY /
  PAIR_CONCENTRATION / LEAKAGE_OR_CAUSALITY_FAILURE /
  CLASS_U_RUN_PROVENANCE / BASELINE_NEGATIVE_OR_WEAK /
  OVERFITTED_SELECTOR / EXECUTION_CONSTRAINT_FAILURE);
  §11B.9 Pre-registered kill criteria + escalation criteria
  (mandatory in every Research Track design memo); §11B.10
  Relationship to existing tracks (diagnostic layer; does not
  replace Foundation; sequenced between T0 and T1; may
  co-author with §7.P2 design). New Open Question Q12 added
  (Root Logic Reassessment authorisation timing recommendation
  yes / between T0 and T1 / co-author with §7.P2). All
  Amendment 1-6 bindings preserved.
- Amendment 6 (this PR): new section §11A "Profit Growth
  Hypothesis Matrix" added before §11 Open questions. The
  Foundation / Research / Production track sections (§5 / §6 /
  §7) define the **methodological** layer (how to verify; how to
  expand the research surface); §11A defines the
  **profit-mechanism** layer mapped explicitly to those tracks so
  the two layers cannot drift. §11A.1 matrix covers 8 profit
  levers (L1 cost reduction / spread realism; L2 execution /
  sizing efficiency; L3 new retained-data / new-epoch
  verification; L4 cheap signal-family ambiguity resolution; L5
  data-side expansion; L6 architecture / representation
  expansion; L7 target redesign; L8 ensemble / selection
  redesign) plus L-LEGACY for Phase 20-26 / M1-M5-M15 routes with
  controlled-vocabulary status `REQUIRES_SEPARATE_EVIDENCE_
  RECONCILIATION` (explicit binding; silent ignoring forbidden).
  Each lever row carries: candidate track(s), profit mechanism,
  why-admissible-after-evidence-reconciliation, required
  evaluation metrics, Foundation dependency, production risk,
  recommended priority, first authorisable PR / design memo.
  §11A.2 recommended profit-first sequencing (near-term
  pre-Foundation: P2 → P1 → PR-B.0/T1 → T2; post-Foundation T4:
  A.1 → D.1 → C.1 → A.2 → D.2/D.4/D.5 → B/E/F/G). §11A.3 explicit
  non-goals (do not optimise for gross Sharpe alone; do not use
  old numeric claims as thresholds; do not treat any track as
  production-ready without migration design; do not add external
  data without retention/provenance; do not run architecture work
  without marginal-information hypothesis; do not over-generalise
  Phase 28 negative research baseline; do not interpret absence of
  +mtf direct negative final Sharpe as positive evidence). §11A.4
  Phase 20-26 / M1-M5-M15 legacy route explicit handling
  (`REQUIRES_SEPARATE_EVIDENCE_RECONCILIATION`; not silently
  ignored; requires separately authorised legacy-route
  reconciliation memo before legacy phases can be promoted into
  §6 / §7). All Amendment 1-5 bindings preserved.
- Amendment 5 (this PR): cleanup of Amendment 4 residuals. (a) §3
  status table: stale duplicate `9.X-J / 9.X-L / 9.X-M / 9.X-N /
  9.X-O "(per log)"` rows (which preceded the detailed Amendment-4
  rows) **removed**; the new Amendment-4 rows above (citing
  `phase9_x_jlmno_series_closure_memo.md`) are now the sole
  authoritative entries for J / L / M / N / O. The stale rows
  conflicted with the new interpretation (9.X-J = PARTIAL GO not
  "TBD"; 9.X-N = PARTIAL GO not "NO ADOPT"; 9.X-O = GO at series
  closure proposed-only candidate, not blanket "NO ADOPT"). (b) §3
  `+all (vol+moments+mtf)` row's active comparator phrasing
  "< +mtf alone" rewritten as `NO ADOPT at phase scope` + archival
  closure-context note (the historical reference compared against
  the now-invalid / archived +mtf anchor; that comparison is no
  longer active); active reason recorded as multicollinearity /
  combined feature group did not produce an adoptable phase
  verdict. (c) Appendix A.11 aggregate finding extended with
  audit-proof binding: `Direct +mtf final negative Sharpe =
  SOURCE_NOT_FOUND_IN_REPO` explicitly recorded; absence of
  direct negative final Sharpe for +mtf may **not** be
  interpreted as positive evidence for +mtf; the four
  independent non-routing reasons (v18 invalidation; v19 class
  U; J/L/M realism degradation; N/O recovery being
  engineering-layer rather than signal-strength) bind. (d)
  Scoping re-confirmed: Phase 28 §10 immutable research baseline
  = `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` is research-baseline scope
  only; Phase 9.16 v9 20p production baseline remains
  `VALID_OPERATIONAL_BASELINE`; the Phase 28 negative-baseline
  finding does **not** invalidate the production baseline
  directly; over-generalisation forbidden. (e) All no-routing
  bindings from Amendments 1-4 preserved: 0.174 =
  `INVALID_LOOKAHEAD_NUMERIC`; 0.158 / 0.165 / 0.177 =
  `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`; 0.061 =
  `FALSIFIED_AT_SCOPE` (LSTM Mode A only); no old numeric may be
  used as routing evidence / pass-fail threshold / production
  migration trigger / H-B9 proof; Track A.1 remains from-scratch
  new-epoch re-evaluation only.
- Amendment 4 (this PR): realism / cost-adjusted / net-Sharpe
  final-status harvest from committed sources. New controlled
  vocabulary label `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` added for
  results whose committed final / net / realism / cost-adjusted
  numeric is negative or materially worse than baseline. Major
  findings (per Appendix A.4-extension citations):
  (i) **Phase 28 §10 immutable baseline carries NEGATIVE Sharpe**
  (test -0.1732 / val -0.1863, ann_pnl -204,664.4 pip per
  `phase27_closure_memo.md:34`); all 9 Phase 27-29 β-evals
  searched over this negative-PnL contract; none produced a
  val-selector-preferred positive-Sharpe candidate cell;
  classified `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` (research-baseline
  scope only — distinct from production baseline Phase 9.16 v9
  20p which remains `VALID_OPERATIONAL_BASELINE` at Sharpe
  0.160). (ii) **Phase 9.19 Top-K Rank-3 produced negative
  per-rank Sharpe** (rank-3 ≈ -0.054 per `phase9_19_closure_memo
  .md:102-127`); rank-1 / rank-2 also showed inversion patterns
  inconsistent with calibrated confidence. (iii) **Phase 27.0d
  C-se cell produced Sharpe -0.483** while H1m Spearman PASS
  (+0.438) — ranking signal does not monetise (per
  `phase27_closure_memo.md:34-35`). (iv) **+mtf v19 realism /
  cost-adjusted re-checks: NO negative final Sharpe was found**;
  however phases 9.X-J / 9.X-L / 9.X-M show material Sharpe
  degradation under realism mechanisms (K=3 0.155 → 0.144 →
  0.133; per `phase9_x_jlmno_series_closure_memo.md:30,58,84`);
  phases 9.X-N / 9.X-O recover to anchor-parity (K=3 0.158 with
  DD halved at 9.X-O; GO verdict at series closure per same memo
  line 158-170). (v) Phase 9.X-O `purge + clip` recorded as a
  proposed-only successor candidate to Phase 9.16 v9 20p, subject
  to from-scratch new-epoch re-evaluation (Track A.1 framing
  preserved). §3 status table extended with Phase 9.X-J / 9.X-L
  / 9.X-M / 9.X-N / 9.X-O rows. §4.2 extraction-vs-expansion
  hypothesis further weakened: the +mtf-based empirical-support
  argument is degraded by 9.X-J/L/M realism degradation in
  addition to the v18 invalidation + v19 class-U status; the
  hypothesis remains a research-track design lens, **not** a
  verdictable claim. §6.A Track A.1 sequencing rationale revised:
  A.1 may remain early **only** because it is cheap and resolves
  a major historical ambiguity, **not** because the prior +mtf
  evidence is favourable or promising. Appendix A.7 (Phase 27-29
  spine harvest) extended with negative-Sharpe baseline citation.
  Appendix A.11 (new) added for Phase 9.X-J / 9.X-L / 9.X-M /
  9.X-N / 9.X-O harvest with `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE`
  labels where applicable (none for +mtf series itself; applied
  to Phase 28 §10 baseline and Phase 27.0d C-se cell).
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
  `phase27_29_tabular_eval_validity_audit.md:525-534`). **Amendment
  4 additional binding (with `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE`
  composite label):** the Phase 28 §10 **immutable research
  baseline** used as the comparison anchor across all 9 β-evals
  carries committed-source-stated **NEGATIVE Sharpe** (test
  -0.1732 / val -0.1863) and **NEGATIVE ann_pnl** (-204,664.4
  pip over 9 months, n=34,626) per
  `phase27_closure_memo.md:34`. The val-selector picked
  C-sb-baseline (the negative-Sharpe cell) in 5/5 Phase 27
  sub-phases; none of the new candidate cells were val-superior.
  Phase 27.0d S-E (#325) cell C-se produced Sharpe **-0.483**
  while H1m Spearman PASS at +0.438 (ranking signal does not
  monetise; `phase27_closure_memo.md:34-35`). These negative
  numerics are **research-baseline scope only**, distinct from
  the production baseline Phase 9.16 v9 20p (Tier 2;
  `VALID_OPERATIONAL_BASELINE` at 0.160) which is **not affected**
  by the Phase 27-29 research-baseline status.

- **Phase 9.19 Top-K per-rank inversion harvest (Amendment 4):**
  Rank-3 per-trade Sharpe **≈ -0.054 (negative)** per
  `phase9_19_closure_memo.md:102-127`; rank-1 / rank-2 also show
  inversion patterns inconsistent with calibrated confidence
  (per-rank ordering not monotonic in trade quality). The
  composite Top-K K=2 Sharpe 0.165 number is the aggregate of
  ranks 1 + 2; the per-rank negative tail at rank-3 is a
  `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` finding for the
  multi-pick-from-correlated-pairs scope.

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
| **9.X-B** | **+all (vol+moments+mtf)** | NO ADOPT at phase scope | Tier 4 | Amendment 5 binding: historic closure comparison referenced the now-invalid / archived +mtf anchor; archival closure context only — not an active comparator. Active reason recorded: multicollinearity / combined feature group did not produce an adoptable phase verdict |
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
| 9.X-G | greedy decorrelation top-K | NO ADOPT | Tier 4 | ρ ∈ {0.4, 0.5}; PnL -18~-20%; closure comparison used the now-invalid mtf v18 anchor; archived closure context only |
| **9.X-J** | **realism pack (cost-aware + RiskManager)** | archived K=3 0.155 (-1.9% vs anchor) / K=1 0.146 (-7.6%) — net of realism mechanisms | Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` (Appendix A.11) | PARTIAL GO at series closure (`phase9_x_jlmno_series_closure_memo.md:28-42`); realism cost acceptable given DD improvement; numeric not admissible as routing evidence; built on the now-archived +mtf v19 anchor |
| **9.X-L** | **time-of-day filter** | archived K=3 0.144 (-8.9% vs anchor) | Tier 4 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` (Appendix A.11) | NO ADOPT at series closure (`phase9_x_jlmno_series_closure_memo.md:54-69`); 73% trade-rate reduction with Sharpe gain ~0.001 only; not admissible as routing evidence |
| **9.X-M** | **dynamic SL/TP per-pair tuning** | archived K=3 0.133 (-15.8% vs anchor) | Tier 4 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` (Appendix A.11) | NO ADOPT at series closure (`phase9_x_jlmno_series_closure_memo.md:82-95`); in-sample overfit; per-pair tuning reverts to global TP/SL for most pairs; not admissible as routing evidence |
| **9.X-N** | **margin-aware balance-proportional sizing** | archived K=3 0.158 (matches +mtf v19 anchor; DD%PnL 2.1% vs anchor ~5%) | Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` (Appendix A.11) | PARTIAL GO at series closure (`phase9_x_jlmno_series_closure_memo.md:107-130`); matches anchor Sharpe with about half DD; numeric still class-U on run-provenance and downstream of archived v19 anchor — not admissible as routing evidence; mechanism may be re-evaluated as a from-scratch sizing-engineering candidate under new epoch |
| **9.X-O** | **purge + 100 mini-lot clip cap** | archived K=3 0.158 / K=1 0.157 (matches +mtf v19 anchor; DD%PnL 2.8% vs anchor ~5%; trade count 13.8k vs 22k) | Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` (Appendix A.11) | **GO** at series closure (`phase9_x_jlmno_series_closure_memo.md:140-170`); best result in JLMNO series; proposed-only as a successor candidate to Phase 9.16 v9 20p **subject to from-scratch new-epoch re-evaluation under Foundation T4** — not admissible as routing evidence or as a production-migration anchor without that re-evaluation; mechanism eligibility per §6.A from-scratch framing |
| 9.X-H | calendar full | NO ADOPT (per log) | Tier 4 | Memo not in main project memory; verify at PR-time |
| 9.X-I | rank audit / risk sizing | NO ADOPT (per log) | Tier 4 | Same caveat |
<!-- Amendment 5: stale duplicate 9.X-J / 9.X-L / 9.X-M / 9.X-N / 9.X-O "(per log)" rows removed; the detailed Amendment-4 rows above (citing `phase9_x_jlmno_series_closure_memo.md`) are authoritative. The old rows conflicted with the new interpretation: 9.X-J = PARTIAL GO not "TBD"; 9.X-N = PARTIAL GO not "NO ADOPT"; 9.X-O = GO at series closure (proposed-only candidate, not "NO ADOPT"). -->


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

**Amendment 4 — further degradation of the historical evidence
basis:** Beyond the v18 invalidation and v19 class-U status, the
+mtf realism / cost-adjusted re-verification series (Phases
9.X-J / 9.X-L / 9.X-M / 9.X-N / 9.X-O per `phase9_x_jlmno_series_
closure_memo.md`) revealed material Sharpe degradation when
real-world cost and risk mechanisms were layered onto the +mtf
v19 baseline:

- 9.X-J realism pack: K=3 0.155 (-1.9% vs anchor) / K=1 0.146
  (-7.6%) — PARTIAL GO
- 9.X-L time-of-day filter: K=3 0.144 (-8.9%) — NO ADOPT
- 9.X-M dynamic SL/TP: K=3 0.133 (-15.8%) — NO ADOPT (in-sample
  overfit)
- 9.X-N margin-aware sizing: K=3 0.158 (anchor parity, DD ~halved)
  — PARTIAL GO
- 9.X-O purge + clip cap: K=3 0.158 (anchor parity, DD halved) —
  GO at series closure

(All five numerics are themselves `ARCHIVED_UNTRUSTED_NUMERIC_DO_
NOT_USE_FOR_ROUTING` — they are downstream of the now-archived
+mtf v19 anchor; class U on run-provenance applies; per §3 status
table extension.)

**Implication for the principle:** the pattern "data-side
expansion has a phase-closure record that is no worse than
extraction-tricks" is no longer well-supported by the historical
evidence on its own terms. When realism mechanisms (cost-aware
spread, time-of-day filtering, dynamic SL/TP) were stacked,
Sharpe degraded by up to 15.8% (9.X-M); the recovery in 9.X-N /
9.X-O came from sizing / clip-cap engineering rather than from
the underlying +mtf signal strengthening. The historical
horizon-expansion evidence is **degraded** in addition to being
class U.

**Admissible hypothesis (not a finding):** the falsification
surface, weakened by Amendment 4's realism harvest, is **still
consistent with** a working hypothesis that "clever extraction
from the same data tends to NO ADOPT at the existing
tabular-LightGBM-on-R7-A architecture"; the second clause about
data-side expansion is now **less supported** and should be
treated as **even more provisional**. This is a **research-
prioritisation heuristic** for sequencing Foundation-completion
Research Tracks, **not a verified principle** and **not a binding
constraint** on production decisions or pass/fail thresholds.

**What this hypothesis does NOT support:**

- it does NOT say "+mtf was verified"
- it does NOT say "data-side expansion is verified to succeed"
- it does NOT say "extraction approaches are verified to fail"
- it does NOT supply a pass/fail Sharpe threshold for new-epoch
  evaluations
- (Amendment 4) it does NOT say the historical horizon-expansion
  evidence survived realism / cost-adjusted re-verification —
  the 9.X-J/L/M sequence shows otherwise; the 9.X-N/O recovery
  came from engineering layers, not from the underlying signal

**What this hypothesis does support (heuristically only):**

- Track D (data-side expansion) may be sequenced earlier than
  later Tracks at equal cost, on the basis of the pattern shape
  above — but **only as a hypothesis-driven priority**, not
  because historical +mtf was successful (Amendment 4 binding)
- Track C (A0-broad sequence-NN) remains the explicit
  falsification path for the H-B9 seam-exhaustion hypothesis
  (§4.4) and is **independent** of the extraction-vs-expansion
  heuristic — sequence-NN under A0-broad is admissible
  regardless of whether the heuristic favours data-side
- Track B (Phase 9.X-C residual LSTM modes B-1..B-4) is **not
  foreclosed** by this heuristic; the heuristic does not
  override per-track design memos

**Bottom-line position after Amendment 4:** the current strategy
is **not** "data expansion succeeded historically and should be
prioritised on that basis." The current strategy is: **all
historical positive numerics (across both extraction and
expansion arms) are non-admissible as routing evidence; future
research must be from-scratch under the new-epoch contract;
data-side expansion may still be prioritised in research-track
sequencing, but only as a hypothesis-driven heuristic, not
because the historical +mtf evidence was successful.**

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

1. Track A.1 (+mtf feature-family re-evaluation **from scratch
   under new epoch**) — **Amendment 4 binding:** A.1 retains an
   early position **only** because it is cheap **and** because
   it resolves a major historical ambiguity (does the +mtf
   feature family produce admissible new-epoch evidence at all,
   or did the underlying signal not survive the lookahead-bug
   removal + realism / cost stack?). A.1 is **explicitly NOT** a
   reproduction, rescue, or continuation of the prior +mtf
   PARTIAL GO+ claim. The archived +mtf v19 0.158 is class U on
   run-provenance and the 9.X-J/L/M sequence showed material
   Sharpe degradation under realism mechanisms (Appendix A.11);
   A.1's early position is justified by ambiguity-resolution
   value, not by historical promise.
2. Track C.1 (S1 LSTM under A0-broad) — falsifies or partially
   confirms H-B9
3. Track D.1, D.2 (time-axis, economic calendar) in parallel with
   C.1 — data-side expansion under the (Amendment 4-weakened)
   extraction-vs-expansion hypothesis (heuristic only; not
   verified)
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

## §11A Profit Growth Hypothesis Matrix (Amendment 6)

This section answers a different question from the rest of the
roadmap: "given everything we have tried so far, what should we
test next to actually improve profit?" The Foundation Track
(§5), Research Tracks (§6), and Production-Improvement Tracks
(§7) above are the **methodological** layer (how to verify
claims; how to expand the research surface). §11A is the
**profit-mechanism** layer (which lever, in which sequence,
under which gates, against which metrics) — mapped explicitly
to the tracks above so the two layers cannot drift.

### §11A.1 — Profit lever matrix

| Profit lever | Candidate track(s) | Profit mechanism | Why still admissible after evidence reconciliation | Required evaluation metrics | Foundation dependency | Production risk | Recommended priority | First authorisable PR / design memo |
|---|---|---|---|---|---|---|---|---|
| **L1 — Cost reduction / spread realism** | §7.P2 (live spread snapshotting; observational) → §7.P1 (cost-model refinement) | Replace fixed-pip spread assumptions with empirical per-pair / per-time-of-day spread; reduce false-positive trades that only pass under unrealistic cost models | The Phase 9.10 cost-aware backtest is `ARCHIVED_UNTRUSTED` as a Sharpe ceiling claim, but the *direction* (lower cost → better net P&L) is independent of the suspended numerics; admissibility comes from real-world spread/slippage measurements, not from old Sharpe numbers | net Sharpe (per-trade, post-cost), ann_pnl, spread sensitivity (Δ Sharpe / Δ pip), per-time-of-day PnL distribution, blocked-trade per-trade EV (i.e., would-have-been P&L of trades the new cost model blocks), DD%PnL | Independent of Foundation T1-T4 (P2 / P1 can proceed while Foundation work parallels) | Low for P2 (observational); medium for P1 (paper A/B before any production switch); high for P3 sizing changes (rollback plan + risk limits required) | **Highest near-term** — P2 first because observational and safest | P2 snapshotting design memo (small; ~200-400 lines; under §7.P1 / §7.P2 framing) |
| **L2 — Execution / sizing efficiency** | §7.P3 (cost-aware sizing engineering); 9.X-N margin-aware-sizing **mechanism re-evaluation from scratch under new epoch** (NOT 9.X-N's old numeric); 9.X-O purge+clip **mechanism re-evaluation from scratch** | Reduce drawdown and avoid oversized / bad-liquidity execution while preserving net PnL; partial fills, margin accounting, per-pair max-position scaling | The Phase 9.13 C-1 Kelly / C-2 cap NO ADOPT was for **Layer-1 lever** Sharpe lift, which is a distinct question from production-layer engineering; the 9.X-N / 9.X-O mechanisms are `ARCHIVED_UNTRUSTED` as Sharpe claims but their mechanism-level rationale (sizing realism, clip cap discipline) is independent of those numerics; production-engineering admissibility comes from rollback + risk-limit discipline, not from old Sharpe numbers | ann_pnl, max DD, DD%PnL, margin usage histogram, rejected-order count, per-pair lot exposure, turnover, live/paper safety gate triggers, max-consecutive-losses count | Foundation-independent for the engineering portion; the mechanism-level re-evaluation of 9.X-N / 9.X-O Sharpe is Foundation-dependent (requires T4 + new-epoch S-B / S-E) | High (production order flow) — requires explicit rollback plan + pre-stated risk limits + safety gates per §7.P3 | High, but production-risk controlled | §7.P3 cost-aware sizing engineering design memo (mechanism-only; **no** Sharpe-lift claim) |
| **L3 — New retained-data / new-epoch verification** | §5 T1 (Gate P1 PR-B) → T2 (Gate P2 retention) → T3 (new epoch baseline + control) → T4 (V2-expanded sentinel) | **Not a direct profit lever.** Enables trustworthy profit tests for all subsequent levers; prevents Class-U recurrence; establishes the new S-B / S-E comparator baseline against which Research Tracks A-G evaluate | The PR #356 audit verdict `TARGETED_VERIFICATION_REQUIRED` and the V2-expanded Stage 2 `HALTED_INPUT_UNAVAILABLE` make this the only path under which new "verified" claims become admissible; this is the structural admissibility precondition for every other lever above L1 / L2 | manifest completeness, retention round-trip 100% per-file SHA-256 match (§5.3 T2 stage gate), committed run-provenance artifacts (sweep_results / aggregate / val_selected / sanity_probe), full V2-expanded sentinel verification verdict (F-1..F-7 + S-1..S-6 under same contract / provenance boundary; per §5.5 T4 stage gate) | self-defining (T1 → T2 → T3 → T4 sequence) | None (Foundation work itself does not change production) | **Mandatory before any new "verified" research claim**; L4..L8 below all depend on at least T4 completion | T1 PR-B.0 infrastructure (per PR #365 §11 3-PR split default) — requires explicit user authorisation |
| **L4 — Cheap signal-family ambiguity resolution** | §6.A A.1 (MTF from-scratch under new epoch); A.2 (Top-K from-scratch); A.3 (C-3 mechanism from-scratch) | Test whether historically important but untrusted feature families / mechanisms have any value under the new-epoch S-B / S-E comparators; not a reproduction or rescue of prior claims | The +mtf v18 0.174 (`INVALID_LOOKAHEAD_NUMERIC`) / v19 0.158 (`ARCHIVED_UNTRUSTED`) / Top-K 0.165 / C-3 0.177 numerics are non-routing per Amendment 1-5, but the underlying feature families / mechanisms are eligible for from-scratch re-evaluation under T4 (per §6.A from-scratch framing; Amendment 4 Track A.1 sequencing binding); A.1's value is **ambiguity resolution** (does the family produce admissible new-epoch evidence at all?), not historical promise | net Sharpe (post-cost) on new-epoch test split, ann_pnl, per-trade EV stability, rank monotonicity (no inversion à la Phase 9.19 rank-3 -0.054), per-pair contribution, regime contribution, cost sensitivity (Δ Sharpe / Δ spread bps) | Foundation T4 complete | None directly (research-layer; production reflection requires separate migration design memo per §6.A) | **Medium**; A.1 may be **early** post-T4 because it is cheap and resolves a major historical ambiguity, **not** because old MTF evidence is favourable | A.1 design memo (per-track design memo authored after T3 / T4 completion; thresholds defined against new-epoch S-B / S-E, not against any archived old-epoch numeric) |
| **L5 — Data-side expansion (information enlargement)** | §6.D D.1 (time-axis) → D.2 (economic calendar) → D.4 (interest rate spreads) / D.5 (orderbook microstructure) / D.6 (pair universe 20→30) | Add **genuinely new information** rather than more extraction from the same R7-A surface (the data-side leg of the §4.2 extraction-vs-expansion working hypothesis) | The historical +mtf evidence supporting "expansion ≥ extraction" is now degraded by Amendment 4's realism harvest (J/L/M -1.9% / -8.9% / -15.8% under realism mechanisms); however, the hypothesis is preserved as a heuristic, not a verdictable claim; D.1 is cheap (timestamp-derived from existing OANDA bytes), D.2 / D.4 / D.5 are subject to the §6.D external-data mini provenance / retention gate | incremental value vs new-epoch S-B (Δ Sharpe, Δ ann_pnl), leakage checks (causality test; split-leakage check per §6.D D.1 requirements), regime robustness (per-quarter / per-vol-regime breakdown), per-pair contribution, cost-adjusted net PnL | Foundation T4 complete; external-data sub-tracks (D.2 / D.4 / D.5) additionally require the mini retention / provenance gate per §6.D Amendment 1 binding | None directly; production reflection requires separate migration design memo | **D.1 high after Foundation** (cheap timestamp-derived); D.2 / D.4 / D.5 conditional on external-data mini gate completion | D.1 time-axis design memo (post-T4) |
| **L6 — Architecture / representation expansion** | §6.C C.1 (A0-broad S1 LSTM) → C.2 (S2 TCN) → C.3 (S3 Transformer); §6.B B-1 / B-3 / B-4 (Phase 9.X-C residual LSTM modes); §6.F A3 learned MoE | Test whether the current tabular-LightGBM + R7-A architecture stack is seam-saturated (H-B9 hypothesis falsification path); enable a fundamentally different representation if any single architecture beats the new-epoch baseline | The H-B9 hypothesis is conjectural (§4.4 working hypothesis); Phase 27-29 9/9 baseline-pick pattern is consistent with H-B9 but does not confirm it; A0-broad sequence-NN allowlist (PR #354) is the explicit falsification path; B and F tracks are not foreclosed | net Sharpe (post-cost) on new-epoch test split under the same accepted contract / provenance boundary, tabular arch-control (C-d2-arch-control 7th anchor per PR #354 §H-D2), train/val objective wall (val Huber loss training-time; val Sharpe verdict-time per PR #354), full run-provenance committed (sweep_results / sanity_probe / aggregate_summary; explicit U-1 prevention), H-D2 4-outcome ladder verdict | Foundation T4 complete + A0-broad preflight audit pass (per PR #353 / #355 amendment §0.A) | None directly (research-layer); GPU compute cost (2-4 weeks per architecture per §8.3 §6.C sequencing) | **C.1 important** for H-B9 ambiguity resolution; B / F **conditional on A / C / D outcomes** and lower-priority by themselves; the §6.B decision table over A.1 outcome binds B-track eligibility | C.1 (S1 LSTM under A0-broad) design memo (post-T4 + post-preflight); reuses Phase 9.X-C/M-1 PyTorch + CUDA infrastructure |
| **L7 — Target redesign** | §6.E A2-broad target redesign (e.g., E.1 multi-horizon weighted target; E.2 meta-labelling 2-stage; E.3 return-magnitude regression with per-pair quantile normalisation; E.4 risk-adjusted Sharpe-of-trade target) | Improve label / target alignment with monetisable trades; address the class-imbalance / label-noise sources that have repeatedly shown up (84% TB timeout per Phase 9.X-C closure; Phase 27.0d Spearman PASS but Sharpe -0.483 conversion failure) | A2-narrow is FALSIFIED at narrow scope (T1..T4); A2-broad is `DEFERRED_NOT_FORECLOSED` (§3 Tier 5; §6.E scope); not falsified by the narrow result | D-1 PnL identity, net Sharpe (post-cost), ann_pnl, per-trade EV, calibration (rank monotonicity; PIT histogram), class balance, regime robustness | Foundation T4 complete + Track A.1 outcome known (so the candidate targets can be evaluated against a baseline-defined reference) | None directly | **Conditional after Foundation and A.1 / C.1 outcomes**; lower-priority than L4 / L5 / L6 until L4-L6 results clarify which target structure is sensible | A2-broad target redesign design memo (post-T4 + post-A.1) |
| **L8 — Ensemble / selection redesign** | §6.G G.1 (calibrated confidence ranking ensemble) / G.2 (regime-conditional ensemble) / G.3 (sequence-NN + LightGBM ensemble) | Avoid trade-rate explosion and rank inversion through calibrated selection (the Phase 9.17 / 9.17b / 9.X-A / 9.X-C/M-1 5-phase pattern of "trade-rate explosion + per-trade EV collapse") | Phase 9.17 ensemble (MR+BO without threshold) is FALSIFIED at narrow scope; G.1 / G.2 / G.3 are scope-distinct (calibrated selection; regime-conditional; sequence-NN cooperation); not falsified by the narrow Phase 9.17 verdict | rank monotonicity, selected-trade EV (per rank), trade count, turnover, net Sharpe (post-cost), per-pair overlap (the correlated-pair concern from Phase 9.19 rank inversion), cost sensitivity | Foundation T4 complete + Track A.1 + at least one Track C architecture result | None directly | **Lower priority** unless A / C / D produce complementary signals that benefit from ensemble combination | G.1 / G.2 / G.3 design memo (post-T4 + post-A.1 + post-C-some-architecture) |
| **L-LEGACY — Pre-Phase-9 / Phase 20-26 / M1-M5-M15 routes** | (none currently in §6 Research Tracks; pending) | Scalp label design (Phase 22), outcome dataset (Phase 23), mean-reversion / breakout / Donchian / z-score / hybrid baselines, path-EV / trailing-stop / partial-exit (Phase 24), alpha L1-L3 layers and feature widening (Phase 25-26), M1 / M5 / M15 timeframe variants, exit study, fresh-fetch alt-signal work | **Status: `REQUIRES_SEPARATE_EVIDENCE_RECONCILIATION`** — the docs/design/ directory contains substantial committed memos (phase22_*, phase23_*, phase24_*, phase25_*, phase26_* series) that the current roadmap (Foundation T1-T4 + Research A-G + Production P1-P3) does not cover. These remain candidates for profit improvement but were not subjected to the Amendments 1-5 evidence reconciliation. Until a separately authorised legacy-route reconciliation memo establishes their controlled-vocabulary labels and admissibility, they cannot be promoted into §6 Research Tracks or §7 Production Tracks. | (to be defined in a separate legacy-route reconciliation memo) | None until reconciliation completes (Foundation T1-T4 status independent of legacy reconciliation) | Unknown until reconciliation completes | **Deferred until separate evidence-reconciliation memo authorised**; not silently ignored | A "Phase 20-26 / M1-M5-M15 legacy route evidence reconciliation memo" (separate from this roadmap; analogous in structure to Amendments 2 / 4 but scoped to the legacy phases) |

### §11A.2 — Recommended profit-first sequencing

**Near-term, before Foundation completes** (parallel to T1 / T2
planning):

1. **P2 live spread snapshotting design** — observational and
   safest; collects empirical spread data per pair per time-of-day;
   no production decision logic touched.
2. **P1 spread / slippage model design** — authored **after P2 has
   collected ≥ 4 weeks of empirical spread data** (per §11.Q8
   recommendation); paper A/B before any production switch.
3. **PR-B.0 / T1 infrastructure** — if user authorises the
   Foundation path; per PR #365 §11 3-PR split default.
4. **T2 retention destination discussion in parallel** with T1, but
   per §8.2 Amendment 1 binding, **T2 deposit ≠ epoch adoption**;
   no epoch span is bound until T1 / T2 evidence is reviewed at T3.

**After Foundation T4 completes:**

1. **A.1 only as cheap ambiguity resolution** — MTF feature-family
   from-scratch re-evaluation under new-epoch S-B / S-E (per
   Amendment 4 Track A.1 sequencing binding; **not** a reproduction
   of 0.158, **not** a continuation of prior PARTIAL GO+).
2. **D.1 time-axis features** — cheap and timestamp-derived from
   existing OANDA bytes; subject to causality + split-leakage
   checks per §6.D Amendment 1 binding.
3. **C.1 A0-broad S1 LSTM** — H-B9 falsification path; sequencing
   priority justified independently of L4 outcome.
4. **A.2 Top-K** only if the Top-K execution gateway (per PR #216
   follow-up requirement) is ready; otherwise deferred.
5. **D.2 / D.4 / D.5 external data** only after the §6.D mini
   data-source feasibility + retention/provenance gate completes
   for that specific external source.
6. **B / E / F / G** conditional on A / C / D results per the
   per-track decision logic (§6.B decision table; §6.E / F / G
   prerequisites).

### §11A.3 — Non-goals (explicit)

The following are **forbidden** as profit-improvement strategies
under this roadmap (Amendment 6 binding):

- **Do not optimise for gross Sharpe alone.** Net-of-cost Sharpe
  is the binding metric (per §11A.1 L1 / L4 / L5 metric columns);
  gross Sharpe is informational only.
- **Do not use old numeric claims as pass / fail thresholds.**
  v18 0.174 is `INVALID_LOOKAHEAD_NUMERIC`; v19 0.158 / Top-K 0.165
  / C-3 0.177 are `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_
  ROUTING`; LSTM Mode A 0.061 is `FALSIFIED_AT_SCOPE`. None may
  serve as a threshold (Amendment 1-5 bindings preserved).
- **Do not treat any track as production-ready without a
  production-migration design memo.** §6.A explicit binding: A.1
  Tier-1 verdict does NOT auto-authorise production reflection;
  migration requires separate design memo + live / paper safety
  gates + explicit user authorisation.
- **Do not add external data without the mini retention /
  provenance gate** (per §6.D Amendment 1 binding): raw-byte
  retention satisfying PR #361 §7; schema manifest; dependency
  manifest; documented restoration procedure. Unretained external
  data may NOT enter a verified evaluation.
- **Do not run architecture work just because prior signal work
  failed.** Track B (residual LSTM modes), Track C (A0-broad), and
  Track F (A3 MoE) each require a **stated marginal-information
  hypothesis** in their design memo explaining why the
  architecture might add value over the new-epoch baseline; the
  decision is not "extraction failed, so try architecture."
- **Do not over-generalise Phase 28 §10 research baseline
  negative Sharpe to the production baseline.** The Phase 28
  research baseline `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` is
  research-scope only; Phase 9.16 v9 20p production baseline
  remains `VALID_OPERATIONAL_BASELINE` (Amendment 4 / 5 scoping
  binding preserved).
- **Do not interpret the absence of a direct +mtf negative
  final Sharpe as positive evidence for +mtf.** Per Amendment 5
  Appendix A.11 binding: direct +mtf negative final Sharpe =
  `SOURCE_NOT_FOUND_IN_REPO`; absence is not positive evidence;
  four independent non-routing reasons bind regardless.

### §11A.4 — Phase 20-26 / M1-M5-M15 legacy route — explicit handling

The current roadmap (Foundation T1-T4 + Research A-G + Production
P1-P3) does **not** cover the substantial pre-Phase-9 / Phase 20-26
research line. The `docs/design/` directory contains committed
memos for:

- Phase 22 — scalp label design, mean-reversion baseline,
  M5-breakout-M1-entry hybrid, meta-labelling, alternatives
  postmortem, final synthesis, research integrity audit
- Phase 23 — outcome dataset, m5 Donchian baseline, m5 z-score
  MR baseline, signal quality rev1, m15 Donchian baseline, design
  kickoff, final synthesis
- Phase 24 — path-EV characterisation, trailing stop, partial
  exit, regime-conditional, design kickoff, NG10 envelope
  confirmation, NG10 relaxation review, final synthesis,
  gamma hard close
- Phase 25 — label design, F1 / F2 / F3 / F5 alpha designs,
  scope reviews post-F1 / F2 / F3 / F5, deployment audit design,
  routing reviews, closure memo
- Phase 26 — kickoff, first scope review, alpha L1 / L2 / L3
  designs, alpha rev1, routing reviews post-26.0a / 26.0b / 26.0c,
  scope amendment for feature widening, R6 new-A design memo
- Various M1 / M5 / M15 timeframe variants and exit-study /
  fresh-fetch / alt-signal work

**These are NOT intentionally out of scope.** They remain
potentially relevant to profit growth but were **not** subjected
to the Amendments 1-5 evidence reconciliation (which focused on
Phase 9.x / Phase 27-29 lineage).

**Amendment 6 binding for Phase 20-26 / M1-M5-M15 legacy:**

- **Status:** `REQUIRES_SEPARATE_EVIDENCE_RECONCILIATION`
- **Roadmap effect:** the L-LEGACY row in §11A.1 records this
  status; the legacy phases cannot be promoted into §6 Research
  Tracks or §7 Production Tracks under this roadmap.
- **Required next step (when user authorises):** a separately
  authorised "Phase 20-26 / M1-M5-M15 legacy route evidence
  reconciliation memo" analogous in structure to Amendments 2 / 4
  (controlled vocabulary labels per claim; SOURCE citations;
  per-numeric admissibility; per-mechanism eligibility). This
  memo is **not** part of the current roadmap PR sequence.
- **Until that memo lands:** the legacy phases are recorded as
  pending; **silent ignoring is forbidden** (Amendment 6 binding);
  future profit-growth decisions must either (a) explicitly
  defer to the pending reconciliation, or (b) trigger the
  reconciliation memo's authoring.

---

## §11B Root Logic Reassessment / Profit Logic Audit (Amendment 7)

**Status:** This section is **not a Research Track**. It does
**not** execute new models, features, or experiments. It is a
**diagnostic layer** to be authored / reviewed **before** running
the next research track, so that we do not repeat the historical
failure modes uncovered in Amendments 1-6:

- Phase 28 §10 research baseline = `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE`
  (test Sharpe -0.1732 / val -0.1863 / ann_pnl -204,664.4)
- Phase 27.0d C-se cell = Spearman H1m PASS (+0.438) but Sharpe
  **-0.483** (ranking signal does not monetise)
- Phase 9.19 Top-K rank-3 = per-trade Sharpe **-0.054** (rank
  inversion)
- Phase 9.X-C/M-1 LSTM Mode A = 7.7× trade-rate explosion +
  per-trade EV collapse to 0.13×
- Phase 9.X-J/L/M +mtf realism degradation (Sharpe -1.9% / -8.9%
  / -15.8% under cost / SL-TP / time-of-day mechanisms)
- 9 / 9 Phase 27-29 sub-phases picked C-sb-baseline at
  val-selector

The pattern across these results: research-frame Sharpe / Spearman
/ phase-closure verdicts did **not** convert reliably to
monetisable, cost-adjusted, regime-stable, rank-monotonic
profit. §11B asks **why**, **before** spending more compute on
the next architecture / feature / target try.

### §11B.1 — Objective mismatch audit

Historical failures suggest possible mismatch between:

- **train objective** (e.g., log-loss, MSE, Huber on a label that
  may not be the monetisable quantity)
- **validation selector** (e.g., val log-loss, val Sharpe at a
  selection rule that may pick val-superior cells that do not
  test-superior on net PnL)
- **rank / Spearman metrics** (PASS at H1m yet -0.483 at C-se)
- **gross Sharpe** (pre-cost; may be optimistic relative to
  net-PnL realism)
- **net Sharpe** (post-cost per-trade; the binding metric for
  §11A profit levers)
- **ann_pnl** (the production-relevant scale)
- **per-trade EV** (the collapse pattern in 9.17 / 9.17b / 9.19 /
  9.X-A / 9.X-C/M-1)
- **production-realistic PnL** (live execution incl. slippage,
  partial fills, rejected orders)

**Required diagnostic questions** (must be answered in any future
Track design memo before implementation):

- Did the selected train / val objective optimise **monetisable**
  trades, or only a proxy (rank order, classification accuracy,
  regression error) that may not monetise?
- Did the validation score (whatever it was) correlate with **net
  PnL** on the held-out test set across multiple folds?
- Did Spearman / ranking signal survive the addition of cost +
  selection rule + position sizing? Phase 27.0d C-se shows
  Spearman can PASS while Sharpe is -0.483; this is the
  reference negative case.
- Did better model score lead to better **selected-trade EV**,
  or did rank inversion creep in (Phase 9.19 rank-3 -0.054)?

**Binding (Amendment 7):** every future Research Track design
memo (A / B / C / D / E / F / G under §6) must include an
**objective-coherence statement** answering the four questions
above. Tracks that pass classification accuracy or rank
correlation as their headline metric but cannot answer (b) and
(d) affirmatively are **not eligible for promotion** to
production.

### §11B.2 — Label / target logic audit

The historical labels (TB 3-class with 84% timeout per Phase
9.X-C closure; the various A2-narrow T1..T4 targets per Phase
29.0a closure FALSIFIED_A2_NARROW) may not encode profitable
trading decisions structurally.

**Diagnostic questions** (must be answered before any future
Track E design memo or before reusing the current TB label for a
new Track A.1 / D / C re-evaluation):

- Is the label predicting **direction**, **trade / no-trade**,
  **return magnitude**, **exit-aware profit** (path-aware
  realised P&L net of TP / SL), or **risk-adjusted profit**?
- Does the label include **spread / slippage / cost hurdle** as
  part of its definition (so a "profitable" label requires
  return > round-trip-cost), or only gross return?
- Does the label reflect **entry / exit mechanics actually used
  by the strategy** (TP / SL distances, time-stop horizon,
  partial exit rules), or an idealised geometric move that the
  strategy cannot capture?
- Does the label produce **class imbalance** (TB 84% timeout
  per Phase 9.X-C) or excessive false positives?
- Should future target redesign **prioritise selected-trade EV
  and net PnL** rather than raw return or direction?

**Binding (Amendment 7):** Track E A2-broad design memo must
answer all five questions above as a structural prerequisite;
this expansion of §6.E is broader than "try more targets" — it
includes a **label-definition review** of what counts as
"profitable" in the label generator before listing candidate
targets.

### §11B.3 — Selection / ranking logic audit

Top-K rank inversion (Phase 9.19) and C-se Spearman-but-negative-
Sharpe (Phase 27.0d) are evidence that ranking can pass at the
distribution level while failing to monetise at the
top-of-distribution level (where selection actually operates).

**Required diagnostics** (must be reported in any future Track A.2
/ Track G selection-rule design memo):

- **rank monotonicity by decile** of model score on the val set
  and the test set (per-pair decomposition + global)
- **selected-trade EV by score bucket** (top decile, top quintile,
  top half, bottom half, bottom decile)
- **per-pair selected-trade overlap** (Phase 9.19 closure
  identified that simultaneous picks across USD-base pairs are
  not independent; same pattern may bite Track A.2 again unless
  explicitly diagnosed)
- **confidence calibration** (reliability diagram of predicted
  probability vs realised hit rate)
- **score distribution stability across train / val / test**
  (KS / Wasserstein distance per split; covariate-shift detection)
- **cost-adjusted selected-trade PnL by rank** (the binding
  metric — what would a rank-k strategy have earned after spread
  / slippage / sizing, by k?)

**Binding (Amendment 7):** no future selection / ranking
mechanism may be promoted to a new-epoch Research Track
production-migration design memo unless **rank monotonicity AND
cost-adjusted selected-trade EV survive** validation on the new
epoch's test split. Spearman PASS alone is **insufficient** (per
the C-se reference case).

### §11B.4 — Cost hurdle / execution realism audit

A diagnostic layer asking **where** cost should enter — training
target, selector, post-filter, or all three.

**Questions** (must be addressed in any future Track A / D / G /
P1 / P3 design memo where cost is a binding variable):

- Is the strategy trying to trade **edges smaller than
  spread / slippage**? If so, even a perfect rank order yields
  negative net P&L (the C-se reference case).
- Does the model score predict **gross return but not net
  return**? Train / val a parallel scorer on gross-return target
  vs net-return target and compare; if they pick different cells
  at val-selector, the gross / net mismatch is binding.
- Should the trade gate require **expected edge > dynamic cost
  hurdle** (per-pair, per-time-of-day, per-volatility-regime),
  rather than a fixed-pip / fixed-percentage threshold?
- Should **spread / time-of-day / liquidity enter the selector**
  rather than only the backtest cost model? If the selector
  cannot see cost, it cannot avoid picking cost-erased
  candidates.

**Binding (Amendment 7):** this is **root logic**, not just
production engineering. §7.P1 / §7.P2 / §7.P3 still hold for the
production-side improvements; §11B.4 asks the cost question
**inside the model training and selection logic** as well. A
future Track A.1 / D.1 / C.1 design memo must state how cost
enters its training / selection / post-filter / backtest chain,
or explain why cost is admissibly absent from each stage.

### §11B.5 — Trade unit / horizon audit

Review whether current entry / exit / horizon assumptions are
correct given the alpha-after-cost picture.

**Questions** (must be addressed before reusing the current TB
20-bar M5 horizon for any new Research Track A / D / C):

- Is the **current horizon too short** for the available alpha
  after costs (so 84% TB timeout per Phase 9.X-C is partly a
  horizon-mismatch finding, not just a class-imbalance finding)?
- Are M1 / M5 / M15 / H1 / D1 features **aligned with the trade
  holding period** the strategy actually executes, or is there a
  feature / horizon mismatch?
- Does **TP / SL logic destroy** otherwise predictive signal
  (e.g., does forcing TP=1.5 / SL=1.0 truncate profitable runners
  while letting losers run to SL)? Phase 9.X-M tested per-pair
  tuning and reverted to global; is this a horizon-coupling
  finding rather than a tuning finding?
- Are **partial exits / dynamic SL/TP failures** telling us that
  the **exit policy is mismatched** with the entry policy (Phase
  9.18 H-1 bucketed TP/SL + H-2 partial exit both FALSIFIED;
  80% SL-before-partial rate)?
- Should evaluation compare **direction prediction vs path-aware
  trade outcome** (Phase 24 path-EV characterisation) rather
  than only direction accuracy?

**Binding (Amendment 7):** any future Track A.1 / D / C design
memo must include a **horizon-coherence statement** answering at
least (a), (c), and (e); horizon-mismatch failure modes must be
explicitly checked before committing GPU / CPU time.

### §11B.6 — Baseline and comparator audit

Because the Phase 28 §10 research baseline is
`NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` (-0.1732 test Sharpe),
**beating a negative research baseline is not evidence of
profitability**. Future research must define its comparators
carefully.

**Required language (Amendment 7 binding):** future candidates
must be compared against **all** of the following, with explicit
results reported for each:

- **new-epoch S-B baseline** (the from-scratch new-epoch
  economic baseline built at T3 per §5.4)
- **new-epoch S-E control** (the from-scratch tabular control
  built at T3)
- **no-trade / cash baseline** (Sharpe 0; ann_pnl 0;
  trade-count 0; the structural floor)
- **production Phase 9.16 v9 20p operational baseline** where
  applicable (Tier 2 `VALID_OPERATIONAL_BASELINE` at Sharpe
  0.160; the production-decision floor)
- **cost-adjusted hurdle baseline** (a per-pair / per-time-of-day
  cost-only model that buys when expected edge > realistic cost,
  no signal added; the cost-floor)

**Comparator-choice binding:** the **set of comparators** for a
given Track must be defined **before** running that Track (in
its design memo). Post-hoc comparator selection (cherry-picking
the comparator that makes the candidate look best) is
**forbidden**.

**Forbidden language (Amendment 7):**

- "beat the baseline" (without specifying which baseline)
- "improvement over Phase 28 §10" alone (because Phase 28 §10
  is `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE`; beating it is
  insufficient)
- "Sharpe > 0" alone (because cash is also Sharpe 0; production
  baseline is Sharpe 0.160; a candidate at Sharpe 0.05 is worse
  than cash for a leveraged strategy after risk + tax)

### §11B.7 — Alpha upper-bound / oracle diagnostics

Before expensive architecture work (Track C A0-broad
sequence-NN; Track F A3 MoE), require **cheap diagnostic
upper-bound checks** to determine whether enough monetisable
signal exists to justify model complexity.

**Required diagnostics** (must be reported before any Track C /
F / B-3 / B-4 design memo authorises GPU compute):

- **cost-free oracle vs cost-adjusted oracle** — what Sharpe /
  ann_pnl would a perfect-foresight strategy earn (a) ignoring
  cost, and (b) after realistic per-pair / per-time-of-day cost?
  The gap is the cost-erasure ceiling; if (b) ≤ baseline, no
  signal can win.
- **per-pair oracle** — same as above per pair; identifies
  which pairs structurally have / lack alpha
- **regime oracle** — same as above per market-regime bucket
  (vol-regime / trend-regime / session-regime); identifies
  which regimes have / lack alpha
- **perfect-rank oracle** — what does a perfect rank order
  earn under realistic selection rules + cost? Phase 27.0d
  C-se PASS Spearman + Sharpe -0.483 is the reference case for
  why this is a binding diagnostic.
- **label separability check** — KL / Wasserstein distance
  between the feature distributions of TP / SL / timeout
  outcomes; if not separable, no model class can do better
  than random by this label.
- **feature information coefficient (IC) / mutual information**
  per-pair per-feature on the new-epoch data
- **score-to-PnL monotonicity check** — for whichever simple
  baseline model we have, does higher score → higher P&L
  monotonically? If not, the score is non-monetisable at the
  current selection rule.
- **per-pair and per-regime contribution decomposition** of any
  baseline candidate (to detect single-pair / single-regime
  reliance per Phase 9.19 USD-cluster finding)

**Binding (Amendment 7):** Track C (A0-broad) / Track F (A3
MoE) / Track B-3 / Track B-4 design memos must **first** present
the §11B.7 diagnostics on the new-epoch data; only if the
diagnostics show monetisable upper-bound headroom may the
architecture work be authorised. This is **prerequisite to GPU
compute**, not parallel to it.

### §11B.8 — Root-cause taxonomy for failed experiments

Future Research Track closure memos **must classify failures**
using the controlled taxonomy below, **instead of** just writing
"NO ADOPT" or "PARTIAL GO with caveats." Multiple labels per
closure are admissible.

| Label | Definition |
|---|---|
| `NO_SIGNAL` | The feature / target / mechanism does not predict the outcome at any rank; IC / MI ≈ 0; oracle diagnostics show no alpha headroom |
| `SIGNAL_NON_MONETISABLE` | The feature predicts the outcome with statistically significant rank correlation, but the rank does not survive cost + selection + sizing to net P&L (reference case: Phase 27.0d C-se Spearman PASS + Sharpe -0.483) |
| `COST_ERASED_EDGE` | The signal produces positive gross P&L but negative net P&L under realistic cost; cost-free oracle would adopt, cost-adjusted oracle would not |
| `RANKING_INVERSION` | Top-of-distribution ranks underperform middle / bottom ranks at net P&L (reference: Phase 9.19 rank-3 -0.054; LSTM Mode A rank-1 < rank-3) |
| `TRADE_RATE_EXPLOSION` | Trade rate increases materially without proportional EV scaling; reference Phase 9.17 (15× trade rate, Sharpe collapsed); Phase 9.X-C/M-1 (7.7× trade rate); Phase 9.X-A (4.5× trade rate) |
| `PER_TRADE_EV_COLLAPSE` | Per-trade EV drops below operational threshold even if total PnL increases; the binding metric for the 5-phase NO ADOPT pattern in §4.2 |
| `REGIME_INSTABILITY` | Signal works in some market regimes (trend / vol bucket / session) but reverses or vanishes in others; not robust to regime shift |
| `PAIR_CONCENTRATION` | PnL comes from a single pair or a single correlated-pair cluster (reference: Phase 9.19 USD cluster overlap); not robust to pair-universe expansion or contraction |
| `LEAKAGE_OR_CAUSALITY_FAILURE` | Future / same-bar information enters features or labels (reference: Phase 9.X-B v18 lookahead bug; v19 causal fix reduced 0.174 → 0.158); falsifies the prior numeric and requires re-evaluation |
| `CLASS_U_RUN_PROVENANCE` | sweep_results / sanity_probe / aggregate_summary / val_selected gitignored at merge SHA; numeric cannot be independently verified (reference: PR #356 audit U-1 finding across 9 β-evals) |
| `BASELINE_NEGATIVE_OR_WEAK` | The candidate beat the local research baseline but the local baseline itself was negative or weak (reference: Phase 28 §10 immutable research baseline -0.1732); the candidate's apparent improvement does not survive comparison against cash or production baseline |
| `OVERFITTED_SELECTOR` | The val-selector pick-pattern saturates on a single cell (reference: Phase 27-29 9 / 9 val-selector C-sb-baseline pick); the selector cannot distinguish new candidates from the local baseline; H-B9 hypothesis ground |
| `EXECUTION_CONSTRAINT_FAILURE` | The strategy assumes execution behaviour that does not match production (partial fills not modelled; SL-before-partial 80% per Phase 9.18 H-2; rejected orders not modelled); reference for §7.P3 production-safety-gate failures |

**Binding (Amendment 7):** every Research Track closure memo
(A / B / C / D / E / F / G under §6) must classify outcomes
using this taxonomy. Tracks that NO ADOPT without a taxonomy
label are **not closure-eligible**; the closure memo must be
revised to include the label(s) before merge. This is a
**process binding** on Research Track closure, not a
specification of which labels are correct for any given track.

### §11B.9 — Kill criteria / escalation criteria

Pre-registered stop conditions for future Tracks, to prevent
sunk-cost continuation of unprofitable explorations.

**Pre-registered kill criteria** (must appear in every Research
Track design memo before running):

- if **cost-adjusted selected-trade EV is negative** at any
  K (Top-K) or rank decile under realistic cost, **stop**
- if **rank monotonicity fails** (per §11B.3 diagnostic) on the
  new-epoch val set or test set, **do not promote** any
  selection-track candidate
- if **per-trade EV collapses while trade count rises**,
  **stop** the Track (per the 5-phase NO ADOPT pattern; this
  is the structural failure mode)
- if the candidate **only beats a negative research baseline**
  (e.g., Phase 28 §10) but **not** cash / no-trade or
  production Phase 9.16 v9 20p baseline, **do not promote**
- if a **feature family shows no incremental value over S-B /
  S-E** in §11B.7 oracle diagnostics, **do not proceed** to
  expensive model architecture work
- if a **neural model does not beat the tabular arch-control**
  (C-d2-arch-control 7th anchor per PR #354 §H-D2), **stop**
  architecture escalation (Track C → Track F gating)
- if source / run-provenance is `CLASS_U_RUN_PROVENANCE`, the
  result **does not enter routing evidence** regardless of
  numeric magnitude

**Escalation criteria** (must also appear in the design memo):

- if the candidate **passes all kill criteria above** + reaches
  a `STRONG_GO_UNDER_<contract>` outcome → escalate to
  production-migration design memo per §6.A binding (not
  auto-route to production)
- if the candidate **passes some kill criteria but is
  inconclusive on others** → escalate to a strategic-review
  memo (not auto-route to next-architecture work)
- if the candidate produces a `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE`
  outcome at the same scope as a prior negative result →
  escalate to user with the taxonomy label(s) explaining
  **why** the negative finding recurred

**Binding (Amendment 7):** Track design memos that omit
pre-registered kill criteria are **not authorisable**. This
removes the discretion to continue a Track past its kill
threshold based on post-hoc rationalisation.

### §11B.10 — Relationship to existing tracks

§11B is a **diagnostic layer**, not a Track:

- It does **not** replace Foundation T1-T4 (those remain the
  data / verification path)
- It **should** be done **before or alongside** the early
  Track A.1 / D.1 / C.1 design memos (per §11A.2 sequencing)
- It **informs** Track E (target redesign per §11B.2), Track
  G (selection redesign per §11B.3), Track C (architecture
  escalation per §11B.7 / §11B.9), and §7.P1 / §7.P3 (cost
  / execution per §11B.4)
- It can be **authored as a doc-only design memo after this
  roadmap merge**, before any expensive Research Track
  execution. The audit memo itself does not run experiments;
  it answers the §11B.1-§11B.7 diagnostic questions on the
  current state and pre-registers the §11B.8 taxonomy + §11B.9
  kill / escalation criteria for adoption by subsequent
  Research Track design memos.

**Sequencing recommendation:** the Root Logic Reassessment
memo (doc-only) is authored **between** Foundation Track T0
(continuous production keep-alive) and Foundation Track T1
(Gate P1 PR-B). It does not require T1-T4 completion. It
may also be co-authored in parallel with §7.P2 spread
snapshotting design (which is observational and therefore
non-conflicting).

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
- **Q12 — Root Logic Reassessment authorisation timing
  (Amendment 7).** Should the §11B Root Logic Reassessment
  diagnostic memo be authorised **before** Track A.1 / D.1 /
  C.1 design memos? **Recommendation: yes**, at least as a
  doc-only diagnostic design memo, because it may prevent
  repeating the historical failure modes documented in
  Amendments 1-6 (objective mismatch; label-cost coupling
  absent; ranking-vs-monetisation gap; horizon mismatch;
  baseline-comparator confusion; missing oracle-upper-bound
  diagnostics; taxonomy-less closure memos). The §11B memo
  itself runs no experiments; it answers the §11B.1-§11B.7
  diagnostic questions on the current state and pre-registers
  the §11B.8 taxonomy + §11B.9 kill / escalation criteria for
  adoption by subsequent Research Track design memos.
  Sequencing per §11B.10: the Root Logic Reassessment memo is
  authored **between** Foundation T0 (production keep-alive)
  and Foundation T1 (Gate P1 PR-B); may be co-authored in
  parallel with §7.P2 spread snapshotting design (both
  observational / non-conflicting).

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
| `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` (Amendment 4) | a committed source records that a later final / net / realism / cost-adjusted / per-rank result is **negative** or **materially worse than baseline** at the specific scope cited | not admissible for routing / threshold / migration; per-scope only (does not generalise outside the cited scope); the negative evidence binds future re-evaluations to use new-epoch S-B / S-E comparators, not the negative anchor |
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

#### A.7-extension — Phase 27-29 baseline negative-Sharpe harvest (Amendment 4)

This extension to A.7 records the negative-baseline finding from
the Phase 27 closure memo. It applies the new `NEGATIVE_FINAL_
EVIDENCE_AT_SCOPE` label to the Phase 28 §10 immutable
**research baseline**.

- **Immutable research-baseline citation (test):**
  `docs/design/phase27_closure_memo.md:34` — "test Sharpe **-0.1732**;
  test ann_pnl **-204,664.4**" over n=34,626 trades / ~9-month
  test window
- **Immutable research-baseline citation (val):** same memo —
  "val Sharpe **-0.1863**"
- **Val-selector behaviour citation:** `docs/design/phase27_closure_memo.md:34`
  — "The val-selected (cell*, q*) record is bit-identical across
  all five [Phase 27] sub-phases (q*=5; val Sharpe -0.1863; test
  Sharpe -0.1732..."; **all 5/5 sub-phases picked C-sb-baseline**
  (the negative-Sharpe cell) at val-selector; none of the new
  candidate cells were val-superior.
- **S-E cell (Phase 27.0d) citation:** `docs/design/phase27_closure_memo.md:34-35`
  — "S-E (27.0d) unlocked ranking signal but failed monetisation
  conversion: Spearman +0.438 (PASS at H1m level) but Sharpe
  **-0.483** at the C-se cell."
- **Composite labels:** `TARGETED_VERIFICATION_REQUIRED` (Tier 3,
  aggregate from PR #356) **+** `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE`
  (this extension): the Phase 27-29 spine searched **over a
  negative-Sharpe research-baseline contract**. This is the
  intended scope (architectural exploration under a fixed
  research baseline), not a regression from a positive baseline.
- **Critical scope binding (Amendment 4):** the Phase 28 §10
  negative research-baseline status is **separate from and does
  not affect** the production baseline Phase 9.16 v9 20p (Tier 2,
  `VALID_OPERATIONAL_BASELINE` at Sharpe 0.160). The production
  baseline is positive-Sharpe under contemporaneous contract;
  the Phase 27-29 research baseline is a distinct research-frame
  object. Mixing the two is **forbidden** under this Amendment.
- **Per-rank inversion harvest (Phase 9.19 Top-K):**
  `docs/design/phase9_19_closure_memo.md:102-127` — "When LGBM
  picks EUR/USD long with high confidence, it often picks
  GBP/USD long, AUD/USD long etc. simultaneously — all
  reflecting USD weakness... Per-rank Sharpe inversion: Rank-3
  (third family, low-conf trades) produces **-0.054** (negative)."
  Composite label: `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_
  ROUTING` (aggregate Top-K 0.165 per Appendix A.3) **+**
  `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` (per-rank tail at rank-3
  scope).
- **Admissibility of the negative numerics:**
  - May be used for routing? **No.**
  - May be used for pass/fail threshold? **No** (a future
    new-epoch evaluation may not adopt -0.1732 as a comparator
    threshold; new-epoch S-B / S-E comparators bind).
  - May be used for research prioritisation? Yes, as
    **architectural / scope-design context** (e.g., "the Phase
    27-29 spine searched over a negative-baseline research
    contract; any new evaluation under T4 must define its own
    positive baseline").
  - May be used as historical context? Yes.

#### A.11 — Phase 9.X-J / 9.X-L / 9.X-M / 9.X-N / 9.X-O harvest (Amendment 4)

The +mtf v19 realism / cost-adjusted / engineering-stack
re-verification series. None of these numerics are negative; all
sit at the same Tier-3 archived-untrusted level as the +mtf v19
0.158 anchor (downstream of class U on run-provenance and
downstream of the archived v19 anchor itself).

**A.11.J — Phase 9.X-J realism pack:**

- **Number citation:** `docs/design/phase9_x_jlmno_series_closure_memo.md:28-30`
  — "K=3 pip Sharpe **0.155** (-1.9% vs 0.158 anchor); K=1
  Sharpe 0.146 (-7.6%)"
- **Phase-closure verdict citation:** same memo line 35 —
  PARTIAL GO; realism cost acceptable given DD improvement
- **Final label:** `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_
  ROUTING` (Tier 3; downstream of archived +mtf v19 anchor)
- **Routing-evidence admissibility:** No

**A.11.L — Phase 9.X-L time-of-day filter:**

- **Number citation:** `docs/design/phase9_x_jlmno_series_closure_memo.md:54-58`
  — "K=3 pip Sharpe **0.144** (-8.9% vs anchor); 73% of trades
  removed; Sharpe gain ~0.001 only"
- **Phase-closure verdict citation:** same memo line 60-69 —
  NO ADOPT
- **Final label:** `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_
  ROUTING` (Tier 4 NO ADOPT)
- **Routing-evidence admissibility:** No

**A.11.M — Phase 9.X-M dynamic SL/TP per-pair tuning:**

- **Number citation:** `docs/design/phase9_x_jlmno_series_closure_memo.md:82-84`
  — "K=3 pip Sharpe **0.133** (-15.8% vs anchor); K=1 0.138
  (-12.7%); per-pair tuning reverts to global TP=1.5 / SL=1.0
  for most pairs (already optimal); in-sample overfit"
- **Phase-closure verdict citation:** same memo line 86-95 —
  NO ADOPT
- **Final label:** `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_
  ROUTING` (Tier 4 NO ADOPT)
- **Routing-evidence admissibility:** No

**A.11.N — Phase 9.X-N margin-aware balance-proportional sizing:**

- **Number citation:** `docs/design/phase9_x_jlmno_series_closure_memo.md:107-110`
  — "K=3 pip Sharpe **0.158** (matches anchor exactly); DD%PnL
  2.1% (vs anchor ~5%); JPY risk-based Sharpe 0.141 (variance
  imbalance across JPY / non-JPY)"
- **Phase-closure verdict citation:** same memo line 113-130 —
  PARTIAL GO; matches anchor Sharpe with about half DD
- **Final label:** `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_
  ROUTING` (Tier 3; the 0.158 here is anchor-parity but the
  anchor itself is class-U archived)
- **Routing-evidence admissibility:** No; the mechanism
  (margin-aware sizing) may be re-evaluated as a from-scratch
  P3-engineering candidate under §7.P3 production-side track
  (not a research signal)

**A.11.O — Phase 9.X-O purge + 100 mini-lot clip cap:**

- **Number citation:** `docs/design/phase9_x_jlmno_series_closure_memo.md:140-158`
  — "K=3 pip Sharpe **0.158** (matches anchor); K=1 0.157
  (-0.6%); DD%PnL 2.8% (vs ~5% anchor); trade count 13.8k
  (vs 22k anchor); compounding ¥300k → ¥61.2M (+20,315%);
  daily annualized Sharpe (√252): K=1 = 7.16, K=3 = 6.90"
- **Phase-closure verdict citation:** same memo line 158-170 —
  **GO** at series closure; recommended production
  configuration listed
- **Series summary citation:** same memo line 184-188 — "the
  production-optimal stack is v26 with purge+clip (Phase 9.X-O)
  at K=3, which matches the anchor pip Sharpe while halving
  DD%PnL... Recommended production configuration: v26
  purge+clip, lgbm_only K=3, margin-aware sizing (Phase
  9.X-N), initial balance ¥300k, risk 1% per trade."
- **Final label (Amendment 4 binding):** `ARCHIVED_UNTRUSTED_
  NUMERIC_DO_NOT_USE_FOR_ROUTING` (Tier 3). Despite the
  series-closure "GO" verdict, the 9.X-O numerics are
  downstream of the archived +mtf v19 0.158 anchor and carry
  class U on run-provenance; therefore they cannot serve as
  routing evidence under the controlled vocabulary. The
  **mechanism** (purge + clip cap + margin-aware sizing) is
  recorded as a proposed-only successor candidate to the
  Phase 9.16 v9 20p production baseline, subject to
  **from-scratch new-epoch re-evaluation under Foundation T4**
  before any production-migration decision.
- **Routing-evidence admissibility:** No (numeric); the
  **mechanism** is eligible for a future migration design
  memo per §7.P3 / §6.A from-scratch framing; that memo
  requires Foundation completion + explicit user
  authorisation.

**Aggregate finding (Amendment 4):** the +mtf v19 series did
**not** produce a negative final Sharpe at any of J / L / M / N /
O; the historical signal survived in 9.X-N / 9.X-O at anchor
parity. **However**, J / L / M show material Sharpe degradation
under realism mechanisms; the 9.X-N / 9.X-O recovery comes from
sizing / clip-cap engineering rather than from the +mtf signal
itself strengthening. The historical horizon-expansion evidence
is **degraded** (in addition to being class U on run-provenance
and downstream of an invalidated v18 anchor). This further
weakens §4.2's extraction-vs-expansion hypothesis support.

**Amendment 5 audit-proof binding (direct +mtf negative final
Sharpe):**

- **Direct +mtf final negative Sharpe:**
  `SOURCE_NOT_FOUND_IN_REPO`
- **Committed sources instead show:**
  - J / L / M realism degradation (-1.9% / -8.9% / -15.8% vs
    anchor) at phase scope
  - N / O anchor-parity recovery achieved via sizing /
    clip-cap engineering, **not** via underlying +mtf signal
    strengthening
- **Therefore no direct negative final Sharpe is asserted for
  +mtf itself** under this roadmap.
- **Nevertheless, +mtf numerics remain non-routing** because of:
  - v18 lookahead invalidation (Appendix A.1 →
    `INVALID_LOOKAHEAD_NUMERIC`)
  - v19 class-U on run-provenance + downstream of invalidated
    v18 anchor (Appendix A.2 →
    `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`)
  - J / L / M realism degradation
  - N / O recovery being engineering-layer (sizing /
    clip-cap), **not** signal-strength evidence

This binding ensures that future readers cannot interpret the
absence of a direct +mtf negative final Sharpe as positive
evidence for +mtf; the absence is `SOURCE_NOT_FOUND_IN_REPO`,
and the +mtf non-routing status stands on the four reasons
above independently.

### Roadmap section update summary (cross-reference)

| Roadmap section | Update applied |
|---|---|
| §0 Amendment history | Amendment 1 + 2 + 3 + 4 + 5 + 6 + 7 history entries added |
| §11B Root Logic Reassessment / Profit Logic Audit (new) | 10-subsection diagnostic layer (objective mismatch / label / selection / cost-realism / horizon / baseline-comparator / oracle / 13-item failure taxonomy / kill+escalation criteria / relationship to tracks); new Open Question Q12 (Root Logic Reassessment authorisation timing) (Amendment 7) |
| §11A Profit Growth Hypothesis Matrix (new) | 8 profit-lever matrix + L-LEGACY row for Phase 20-26 / M1-M5-M15; recommended profit-first sequencing (near-term + post-T4); explicit non-goals; legacy-route handling as `REQUIRES_SEPARATE_EVIDENCE_RECONCILIATION` (Amendment 6) |
| §3 status table (Amendment 5 cleanup) | stale duplicate "(per log)" rows for 9.X-J / 9.X-L / 9.X-M / 9.X-N / 9.X-O removed; the detailed Amendment-4 rows are now the sole authoritative entries; conflict with old interpretation (TBD / blanket NO ADOPT) resolved |
| §3 status table `+all (vol+moments+mtf)` row | active comparator phrasing "< +mtf alone" replaced with archival closure-context note + active reason "multicollinearity / combined feature group did not produce an adoptable phase verdict" (Amendment 5) |
| Appendix A.11 aggregate finding | extended with audit-proof binding `Direct +mtf final negative Sharpe = SOURCE_NOT_FOUND_IN_REPO`; absence may not be interpreted as positive evidence (Amendment 5) |
| Scoping re-confirmation | Phase 28 §10 research baseline `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` is research-baseline scope only and does NOT invalidate Phase 9.16 v9 20p production baseline `VALID_OPERATIONAL_BASELINE` (Amendment 5) |
| Appendix A controlled vocabulary | new label `NEGATIVE_FINAL_EVIDENCE_AT_SCOPE` added (Amendment 4) |
| Appendix A.7 extension | Phase 28 §10 immutable research baseline negative-Sharpe citations (test -0.1732 / val -0.1863 / ann_pnl -204,664.4); Phase 27.0d C-se cell Sharpe -0.483; Phase 9.19 Top-K rank-3 -0.054; composite labels (TARGETED_VERIFICATION_REQUIRED + NEGATIVE_FINAL_EVIDENCE_AT_SCOPE) (Amendment 4) |
| Appendix A.11 (new) | Phase 9.X-J / 9.X-L / 9.X-M / 9.X-N / 9.X-O per-series numerics + verdicts + citations (Amendment 4) |
| §2 Tier 3 currently-in-tier bullets | Phase 27-29 baseline negative-Sharpe binding + Phase 9.19 Top-K rank-3 negative per-rank binding added (Amendment 4) |
| §3 status table | Phase 9.X-J / 9.X-L / 9.X-M / 9.X-N / 9.X-O rows added (Amendment 4) |
| §4.2 extraction-vs-expansion | Amendment 4 binding: realism-degradation (9.X-J/L/M) weakens the historical horizon-expansion evidence further; the "data expansion ≥ extraction" pattern claim is no longer well-supported by the historical evidence on its own terms; bottom-line: all historical positive numerics are non-admissible as routing evidence; data-side expansion may still be prioritised, but only as a hypothesis-driven heuristic |
| §6.A cross-track sequencing | Amendment 4 binding: A.1's early position is justified by ambiguity-resolution value (does the +mtf family produce admissible new-epoch evidence?), NOT by historical promise; A.1 is explicitly NOT a reproduction / rescue / continuation of prior +mtf claims |
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
