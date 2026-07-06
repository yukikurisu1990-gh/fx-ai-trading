# Post-remediation roadmap — T2 → byte-admissibility → new epoch → ML Step 4, as governance gates

- **Document class:** doc-only planning memo (durable roadmap record; executes nothing)
- **Base:** master `1c8f0f4` (post PR #391 merge)
- **Branch:** `docs/post-remediation-t2-ml-roadmap`
- **Supersession scope:** refines the simplified path "T2 → byte-admissibility →
  new epoch → ML Step 4" that prior memos treated as a linear precursor chain.
  It does NOT amend the binding classifications of
  `docs/design/research_development_roadmap_post_audit.md` (tiers, archived /
  invalid numerics, §7 destination non-approval, §11B bindings) — all of those
  remain in force verbatim.
- **Related contracts:** `docs/design/foundation_t2_execution_readiness_contract.md`,
  `docs/design/gate_p1_feasibility_inspection_protocol.md` (+ Amendment 1),
  `docs/design/gate_p2_retention_destination_evaluation_memo.md`,
  `docs/design/ml_accuracy_uplift_experiment_contract.md` (Steps 1–3),
  `docs/design/project_wide_logic_audit_fable5_findings.md` (audit memo),
  `docs/design/train_serve_consistency_contract.md` (F-5/F-8 record).

---

## 1. Executive recommendation

Recommended revised path — nine sequential governance gates, each with its own
explicit authorisation, evidence, and stop conditions:

1. **Phase A — Post-remediation readiness audit** (doc/evidence only)
2. **Phase B — T2 execution plan** (doc only; strategy = pilot-then-expand, §5)
3. **Phase C — T2 actual retention round-trip** (credential-enabled; evidence only)
4. **Phase D — Byte-admissibility review** (decision on specific bytes only)
5. **Phase E — New epoch adoption** (research-only epoch record)
6. **Phase F — ML Step 4 pre-registration contract** (design only)
7. **Phase G — First real ML run** (smallest safe run under the contract)
8. **Phase H — Post-run audit** (evidence trust decision)
9. **Next-experiment decision** (only after H accepts)

Binding non-implications (each gate authorises only itself):

- **T2 success does not imply byte-admissibility.** A clean round-trip proves
  retention capability for specific bytes; admissibility is a separate review.
- **Byte-admissibility does not imply new epoch adoption.** Admissible bytes
  become an epoch only through an explicit adoption record.
- **New epoch adoption does not imply ML Step 4 execution.** An adopted epoch
  is a substrate, not an experiment authorisation.
- **ML Step 4 design does not imply permission to run.** The pre-registration
  contract is a prerequisite for the run decision, not the decision itself.
- **No production readiness is claimed at any gate**, including after a
  successful first run and accepting post-run audit.

## 2. Current remediation closure state (post PR #391)

| Item | State | Evidence |
| --- | --- | --- |
| F-1 live-entry crash | **Fixed** (fail-closed live EV gate + regression tests) | PR #389 → `4b28753` |
| P1-A test-output isolation | **Fixed** (tmp_path redirection + session guard; full pytest leaves tracked artifacts clean) | PR #390 → `bd87221` |
| F-2 PnL layer | **Corrected by invariant tests** (traded-direction barrier replay + timeout mark-to-market in the 5 evidence-relevant evaluators; 14 archived scripts intentionally frozen) | PR #390 → `bd87221` |
| F-5 ingestion provenance | **Hardened by guards/tests** (atomic writes, non-zero exit on truncation, inventoried-span overwrite guard incl. the 2026-05-31 archive manifest, marker-based resume, model-manifest provenance) | PR #391 → `1c8f0f4` |
| F-8 train/serve consistency | **Hardened by contracts/tests** (SL-first tie-break, ATR warmup, fill-anchored contract barriers, decision-bar-close as-of, completed-bucket MTF, pips_post_cost EV contract, force_fallback=False) | PR #391 → `1c8f0f4` |
| Historical Phase 9.X numerics | **Not rehabilitated** — committed reports remain records of the old scorer/contracts | audit memo §5; PR #390/#391 statements |
| Phase 9.16 v9 20p | **Tier 2 `VALID_OPERATIONAL_BASELINE`, fenced comparator with audit caveats** — neither promoted nor demoted | audit memo §5 |
| T2 retention | **Not executed** (`RETENTION_PROBE_REMAINS_UNRESOLVED`; PR #387 = harness + pre-deposit stop evidence only) | `artifacts/foundation_t2/t2-all-spans-20260702/` |
| Byte-admissibility | **Not approved** | — |
| New epoch | **Not adopted** | — |
| ML Step 4 | **Not authorised** (Steps 1–3 synthetic-only) | ML uplift contract |
| Production readiness | **Not claimed** | — |

Known residuals carried from PR #391 (documented, non-blocking): OANDA
pre-fill protective orders use a labeled decision-close proxy pending a broker
trade-amend API; the 5 legacy TA strategies + ai/ai_stub are honestly
non-comparable (`--use-ta-strategies` adopts zero trades by design);
`MetaDeciderService` (tests-only) does not enforce ev_unit; serve-side ATR
warmup differs slightly from the trainer's on pathologically short histories;
archive completion markers are size-only (resume hygiene, not identity).
Deployed `models/lgbm/` artifacts predate the F8-A tie-break and F5-E manifest
contracts; a contract-consistent retrain is a separately-authorised real-data
step.

## 3. Why the plan is being revised

Before the Fable 5 audit, the working assumption was that completing T2 would
put the project one short step from real ML experimentation. The audit and the
remediation wave changed what we know:

- **The evaluation PnL layer was materially biased and has been corrected** —
  every historical headline number carries the F-2 caveat, so the first real
  run is not "resuming" prior research; it is the first experiment on a sound
  scoring layer, and must be designed as such (pre-registration, multiplicity
  control), not run opportunistically.
- **Ingestion provenance was hardened** — span identity is now guarded, which
  makes byte identity a *checkable* property; the checks still have to be run
  and reviewed (T2 round-trip, admissibility review) before any bytes are used.
- **The train/serve contract was hardened** — training, evaluation, and live
  paths now share explicit contracts, but the deployed models predate them and
  no real-data validation of the aligned contracts exists yet.
- **What remains open is not code**: actual data retention (T2), byte identity
  (admissibility), epoch adoption, and experiment design are *decisions* with
  distinct owners, evidence, and failure modes. Treating them as one slope
  invites exactly the silent scope-creep the audit was commissioned to stop.

Hence: gates, each fail-closed, each producing an explicit status, none
granting the next.

## 4. Revised phase roadmap

### Phase A — Post-remediation readiness audit

> Status pointer: executed in `docs/design/post_remediation_readiness_audit.md`.

- **Purpose:** confirm F-1/F-2/P1-A/F-5/F-8 are closed enough to proceed
  toward T2, and that no remaining blocker should be fixed first.
- **Evidence:** merged PR references (#388–#391 with merge SHAs), current test
  status (targeted suites + honest full-pytest status incl. the 3 known
  pre-existing local-data failures), protected-artifact cleanliness, the PR
  #391 residual list (§2), and a check that no new blocker-class finding has
  appeared since the audit.
- **Output:** `POST_REMEDIATION_READINESS_AUDIT_COMPLETE` or
  `POST_REMEDIATION_BLOCKERS_REMAIN` (with the blocker list).
- **Forbidden:** real-data runs, T2 execution, byte-admissibility, new epoch,
  ML Step 4.

### Phase B — T2 execution plan

> Status pointer: executed in `docs/design/t2_execution_plan.md`.

- **Purpose:** decide the execution shape — one-span pilot, all-span, or
  pilot-then-expand (§5 compares; recommendation: **pilot-then-expand**).
- **Documents:** credential handling (operator-provisioned, never in repo/env
  dumps/evidence; per `foundation_t2_execution_readiness_contract.md`),
  destination alias (`T2_PRIMARY_R2` per Gate P2 memo — still not
  pre-approved), object-lock / retention requirement for the destination,
  deposit → observe → restore → checksum process (existing
  `scripts/foundation_t2/` harness), metadata-only evidence format (the
  PR #387 evidence shape + real-execution statuses), and stop conditions
  (any credential/identity ambiguity → stop and report, never fake success).
- **Output:** `T2_EXECUTION_PLAN_APPROVED` or `T2_EXECUTION_PLAN_BLOCKED`.

### Phase C — T2 actual retention round-trip

> Destination-strategy note: the immediate destination is no longer
> `T2_PRIMARY_R2` (deferred, billing/operational risk). Google Drive /
> local-offline is the next destination plan — see
> `docs/design/t2_drive_local_destination_strategy.md`. Operator selected
> `T2_LOCAL_OFFLINE_PRIMARY` for the immediate `365d_BA` pilot; procedure in
> `docs/design/phase_c1_365d_ba_local_offline_execution_plan.md`. Gate structure
> below is unchanged; only the destination changes.
>
> Status pointer: `365d_BA` local/offline pilot evidence merged (PR #401,
> `T2_C1_365D_BA_LOCAL_OFFLINE_ROUND_TRIP_EVIDENCE_CREATED`); acceptance audit in
> `docs/design/phase_c1_365d_ba_local_offline_acceptance_audit_fable5.md`.

- **Purpose:** deposit bytes, restore bytes, verify checksum/identity,
  produce metadata-only evidence (per span: deposit status, restore status,
  recomputed SHA-256 vs PR-B.1 inventory, sizes, timestamps, scrubbed
  cleanliness report).
- **Must not claim:** byte-admissibility, new epoch adoption, ML Step 4
  authorisation. Success tokens only for what actually happened.
- **Output:** `T2_ROUND_TRIP_EVIDENCE_CREATED` or `T2_ROUND_TRIP_FAILED`.

### Phase D — Byte-admissibility review

> Status pointer: `365d_BA` byte-admissibility review authored
> (`docs/design/phase_d_365d_ba_byte_admissibility_review_fable5.md`,
> `PHASE_D_365D_BA_BYTE_ADMISSIBILITY_RECOMMENDED_FOR_HUMAN_ACCEPTANCE`,
> `365d_BA`-only). Human + ChatGPT acceptance **recorded**
> (`docs/design/phase_d_365d_ba_byte_admissibility_acceptance_record.md`,
> `PHASE_D_365D_BA_BYTE_ADMISSIBILITY_ACCEPTANCE_RECORDED_FOR_LATER_EXPERIMENT_PRE_REGISTRATION`).
> `730d_BA`/`3650d_BA` out of scope; next gate = Phase E (`365d_BA`), separately
> authorised.

- **Purpose:** review T2 evidence and decide whether specific deposited /
  restored bytes are admissible inputs for future experiments.
- **Definition (precise):** byte-admissibility approves **specific bytes /
  span IDs / checksums** as admissible experiment inputs. It does **not**
  approve experiment design, does **not** adopt an epoch, does **not**
  approve ML Step 4, and does **not** validate model performance.
- **Required evidence:** T2 manifest, restore checksums (recomputed, not
  copied), span IDs, time bounds, price mode, provenance references
  (PR-B.1 inventory + archive manifest lineage), cleanliness report.
- **Output:** `BYTE_ADMISSIBILITY_APPROVED_FOR_SPECIFIC_SPANS` (enumerated)
  or `BYTE_ADMISSIBILITY_REJECTED`.

### Phase E — New epoch adoption

> Status pointer: `365d_BA` adopted as research-only frozen-holdout epoch
> `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`
> (`docs/design/phase_e_365d_ba_new_epoch_adoption_decision.md`,
> `PHASE_E_365D_BA_RESEARCH_FROZEN_HOLDOUT_EPOCH_ADOPTION_RECORDED`,
> `365d_BA`-only). Carries F-2/F-5/F-8 contracts + local/offline limitation.
> Next gate = Phase F (ML Step 4 pre-registration), separately authorised;
> `730d_BA`/`3650d_BA` out of scope.

- **Purpose:** convert byte-admissible spans into a named research epoch.
- **Epoch record must include:** epoch ID; span IDs; data SHA-256/checksums;
  time bounds; price mode; candle type; feature contract version; label
  contract version (SL-first strict `<`, ATR min_periods=14 — per
  `train_serve_consistency_contract.md`); cost contract version; split /
  holdout policy (frozen holdout carved at adoption time, before any model
  sees data); accepted exclusions; known limitations; provenance reference;
  code SHA or minimum code baseline; and an explicit non-authorisation
  statement for production.
- **Output:** `NEW_EPOCH_ADOPTED_FOR_RESEARCH_ONLY` or `NEW_EPOCH_NOT_ADOPTED`.

### Phase F — ML Step 4 pre-registration contract

> Status pointer: pre-registration authored for
> `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`
> (`docs/design/phase_f_ml_step4_pre_registration.md`,
> `PHASE_F_ML_STEP4_PRE_REGISTRATION_CREATED`). §10 acceptance thresholds are
> placeholders requiring human + ChatGPT review; ML Step 4 execution remains
> separately gated (`ML_STEP4_EXECUTION_NOT_AUTHORISED`).

- **Purpose:** define the first real ML experiment completely before running
  anything. **Design only — no training, no real-data run in this phase.**
- **Contract must include:** one span (or explicitly minimal span set); one
  champion config (or an explicitly enumerated, small config set with
  multiplicity accounting); frozen holdout (untouched until the single final
  read); split policy (walk-forward windows, purge ≥ label horizon); model
  family; feature set (versioned); label contract; cost contract; acceptance
  criteria and failure criteria (pre-stated numerically); multiplicity
  control (config-count cap + correction method); **portfolio-level daily
  Sharpe definition** (daily-aggregated returns, stated annualisation — not
  per-trade Sharpe); **equity drawdown definition** (percent of equity under
  a stated sizing model — not DD%PnL); turnover / trade-count guard
  (execution-feasibility bound); report schema (machine-readable, code SHA +
  config hash + epoch ID embedded); stop conditions; and an explicit
  no-production-claim statement.
- **Output:** `ML_STEP4_PRE_REGISTRATION_CONTRACT_CREATED` or
  `ML_STEP4_DESIGN_BLOCKED`.

### Phase G — First real ML run

> Status pointer: execution-authorisation / execution plan authored for the
> PR #407 contract
> (`docs/design/ml_step4_365d_ba_execution_authorisation_plan.md`,
> `ML_STEP4_365D_BA_EXECUTION_AUTHORISATION_PLAN_CREATED`; §10 thresholds
> confirmed as binding lower bounds). Execution remains a separate gate
> (`ML_STEP4_EXECUTION_NOT_PERFORMED`).
>
> First-run attempt status pointer: execution go-ahead granted; pre-execution
> hard gates 1–10 + all-20-file checksum re-verification PASSED, but the run
> **stopped before training** at the F-5 provenance gate because no committed,
> reviewed execution harness implements the exact PR #407 contract
> (`ML_STEP4_RUN_INVALID_PROVENANCE_MISSING`; metadata-only stop evidence at
> `artifacts/ml_step4/365d_ba_v1/`). No model trained; no holdout evaluated.
> Next: author + review a contract-faithful executor before the first real run.
>
> Executor status pointer: the reviewed, code-only, no-run contract executor
> was implemented under `scripts/ml_step4/` (+ `tests/ml_step4/`,
> `docs/design/ml_step4_executor_implementation_note.md`,
> `ML_STEP4_CONTRACT_EXECUTOR_IMPLEMENTED_NO_RUN`). It trains nothing and reads
> no real raw data; a separate explicitly-authorised execution PR wires it into
> a guarded real run.
>
> Fable 5 adversarial harness review pointer: the PR #410 primitives were
> audited against PR #407/#408
> (`docs/design/ml_step4_executor_harness_review_fable5.md`,
> `ML_STEP4_EXECUTOR_PRIMITIVES_BLOCKED_FOR_GUARDED_WIRING_REVIEW`). Three
> proven blockers — B-1 hyperparameter drift vs the trainer's committed
> `_LGBM_PARAMS`/`_N_ESTIMATORS`; B-2 incomplete threshold sweep accepted
> silently; B-3 acceptance evaluator fail-open on missing metric keys — require
> a small code-only fix PR (+ tests) before any guarded `execute()` wiring PR.
> No execution occurred; no hashes were consumed by any run.
>
> Blocker-fix status pointer: B-1/B-2/B-3 + R-2 were fixed code-only
> (`ML_STEP4_EXECUTOR_BLOCKERS_B1_B3_FIXED_NO_RUN`): hyperparameters re-pinned
> to the trainer literals (lr 0.05 / num_leaves 31 / verbose −1,
> n_estimators 200; no invented seed — determinism deferred to the wiring PR);
> threshold selector requires the exact full {0.35, 0.40, 0.45} sweep;
> acceptance evaluator fails closed on missing/None required metrics
> (→ `ML_STEP4_RUN_INVALID_PROVENANCE_MISSING`); evidence guard repo-root
> anchored. config/model hashes changed (safe: never consumed by any run).
> Still no execution; guarded `execute()` wiring remains a separate gate.
>
> Root-level trading-logic audit pointer: a Fable 5 project-wide trading-logic
> & profitability research audit
> (`docs/design/trading_logic_profitability_research_audit_fable5.md`,
> `TRADING_LOGIC_PROFITABILITY_RESEARCH_AUDIT_ACCEPTABLE_FOR_GUARDED_WIRING_WITH_REQUIRED_RESEARCH_DISCIPLINE`)
> substantially discharges the roadmap §11B Root Logic Reassessment for the
> ML Step 4 path. Verdict: proceed to guarded wiring under the PR #407/#408
> contract, reframed as a falsification/baseline measurement of the M1
> flagship (likely DOES_NOT_MEET on honest priors); binding pivot afterwards
> to M15/H1 cost-hurdle-aware experiments + empirical spread work (P2);
> program-level kill criteria pre-registered (§17 of the audit).
>
> Re-check pointer: a narrow Fable 5 re-check verified the PR #412 fixes by
> execution (`docs/design/ml_step4_executor_recheck_fable5.md`,
> `ML_STEP4_EXECUTOR_PRIMITIVES_ACCEPTABLE_FOR_GUARDED_WIRING_REVIEW_AFTER_RECHECK`):
> B-1/B-2/B-3 fixed (exact PR #411 reproductions now fail closed; 0/9
> missing-metric probes fail open), R-2 hardened (cwd/traversal/nested/case
> probes refused; PR #409 evidence untouched). Zero blockers remain. Next gate:
> the code-only guarded `execute()` wiring PR, binding R-1/R-4/R-5/R-6 + seed
> decision + maxDD notional + NON_DECISION_EXPLORATORY labeling.
>
> Guarded wiring status pointer: the code-only guarded `execute()` orchestration
> was implemented (`scripts/ml_step4/executor.py` + `execute_365d_ba.py` CLI,
> `docs/design/ml_step4_guarded_execute_wiring_note.md`,
> `ML_STEP4_GUARDED_EXECUTE_WIRING_IMPLEMENTED_NO_RUN`). Real execution is
> refused (no run body); preflight verifies 16 hard gates on inventory metadata
> only. All seven residuals are bound (R-1 bar-index boundaries; R-4 single-
> source label routing; R-5 UTC trading-day; R-6 tie-rule in config/threshold
> hashes; reproducibility policy separate from the model contract; maxDD
> notional 10,000 pips; NON_DECISION_EXPLORATORY labeling). config/model/
> threshold hashes recomputed (safe: never consumed by any run). Next: the
> separately-authorised first-run execution PR implementing the guarded body.
>
> Wiring source-audit pointer: a Fable 5 adversarial source audit of the
> PR #415 wiring (`docs/design/ml_step4_guarded_wiring_source_audit_fable5.md`,
> `ML_STEP4_GUARDED_WIRING_ACCEPTABLE_FOR_REAL_RUN_BODY_IMPLEMENTATION_REVIEW`)
> found ZERO blockers: all refusal combinations verified; no hidden
> execution/data/env routes; residuals bound (4 substantive, 3 provenance-level
> with an explicit 6-item required-in-body checklist, incl. wiring compute_all
> to the notional constant and integer-arithmetic boundary hardening). Next
> gate: ONE code-only/no-run real-run-body implementation PR (synthetic-fixture
> end-to-end rehearsal), then a Fable 5 body audit, then the separately
> authorised first-run execution.
>
> Run-body status pointer: the guarded run body was implemented fixture-only
> (`scripts/ml_step4/body.py` + data_adapter/features/trainer/manifest,
> `docs/design/ml_step4_real_run_body_implementation_note.md`,
> `ML_STEP4_REAL_RUN_BODY_IMPLEMENTED_NO_RUN`). Real mode refuses; the
> synthetic rehearsal runs the full sequence end-to-end (deterministic, 8
> scrubbed evidence payloads to non-protected paths; PR #409 evidence
> untouched). All six PR #416 required-in-body items bound (notional wiring,
> single-source labels/scoring incl. exit timing, UTC coverage denominator,
> real code-SHA/seeds/versions manifest, diagnostics labeler in pipeline,
> integer-arithmetic split boundaries). Remaining for the execution PR: real
> checksum-verified data provider + production v4 bulk feature wiring + real
> mode enablement. Next: Fable 5 body source audit.
>
> Body source-audit pointer: the Fable 5 audit of the PR #417 run body
> (`docs/design/ml_step4_real_run_body_source_audit_fable5.md`,
> `ML_STEP4_REAL_RUN_BODY_BLOCKED_FOR_FIRST_RUN_EXECUTION_REVIEW`) found the
> body fail-closed for real data/execution but PROVED two blockers: B-1 the
> cost cell is applied twice in the holdout metrics path (0.5-cell metrics are
> actually 1.0-cell; sensitivity cells shifted +0.5; validation/holdout
> charging inconsistent); B-2 bulk_labels labels one extra trailing decision
> bar vs the committed trainer/v9 range(n−horizon−1) convention. ATR flavor
> CLEARED (matches trainer exactly). Required: small code-only fix PR (single
> cost application + range alignment + value/range-pinned tests) → re-check →
> only then the separately-authorised first-run execution PR.
>
> Full-source audit pointer: the audit was broadened repo-wide
> (`docs/design/ml_step4_first_run_full_source_audit_fable5.md`,
> `ML_STEP4_FULL_SOURCE_AUDIT_BLOCKED_FOR_FIRST_RUN_EXECUTION_REVIEW`): the
> first-run path is structurally isolated (ml_step4 imports only the audited
> F-2 helper + scrub constants; nothing external imports it or writes
> artifacts/ml_step4); the production feature seam target
> (trainer _add_features/_add_upper_tf_features) was inspected and CLEARED for
> lookahead (shift(1) completed buckets); all legacy routes (optimistic-PnL
> v-scripts, F-10 MTF code, deployed-model machinery, stage22-29) are
> classified unreachable/forbidden; the only physical vector (candle-byte
> mutation) is F-5-guarded and hard-stopped by the pre-consumption checksum
> gate. No new blockers; B-1/B-2 carry over as the sole blockers.
>
> B-1/B-2 fix status pointer: both blockers fixed code-only
> (`docs/design/ml_step4_b1_b2_fix_note.md`,
> `ML_STEP4_FULL_SOURCE_BLOCKERS_B1_B2_FIXED_NO_RUN`). B-1: the flat cost cell
> is applied exactly once by the metrics layer (signal PnL raw gross;
> validation and holdout charge identically; sensitivity cells 0.0/0.5/1.0
> unshifted; explicit cost_convention in evidence). B-2: bulk_labels
> eligibility aligned to the committed range(n−horizon−1) (last eligible
> n−horizon−2). Added the PR #418 mandatory tests (value-pinned cost,
> label-range pinning, ATR numeric cross-check, import-graph legacy-non-use,
> NaN/inf fail-closed, deployed-reuse-impossible). Next: short Fable 5 re-check
> → separately-authorised first-run execution PR.
>
> B-1/B-2 re-check pointer: the Fable 5 re-check verified both fixes by
> execution (`docs/design/ml_step4_b1_b2_fix_recheck_fable5.md`,
> `ML_STEP4_B1_B2_FIXES_ACCEPTABLE_FOR_FIRST_RUN_EXECUTION_REVIEW`): three-value
> cost probes single-charged with unshifted cells; range aligned to
> n−horizon−2 across five sizes; six NaN/±inf combinations never MEET; zero
> regressions (determinism, refusals, guards, notional all intact); legacy
> imports still limited to the two sanctioned externals. ZERO blockers remain.
> Next gate: the separately-authorised first-run execution PR (checksum-verified
> provider + production v4 wiring + minimal real-mode enablement; no contract
> changes; execute exactly once; mandatory post-run review) under the PR #413
> falsification/baseline frame.
>
> FIRST-RUN RESULT pointer: the single authorised ML Step 4 first run executed
> once (code SHA 181dc52f3a08; ML_STEP4_365D_BA_FIRST_RUN_COMPLETED;
> docs/design/ml_step4_365d_ba_first_run_execution_report.md; evidence at
> artifacts/ml_step4/365d_ba_v1/first_run_181dc52f3a08/). All 12 hard gates
> passed (20 files / 1,481,715,517 bytes verified); 20 per-pair LightGBM from
> scratch on v4-BASE 39 features (MTF excluded); labels via labels.py; holdout
> evaluated exactly once. Result: DOES_NOT_MEET_PREREGISTERED_CRITERIA (6/7
> criteria fail; daily Sharpe -13.7, expectancy -127.8 pips, win-rate 7.8%).
> Expected valid falsification outcome; no rerun/tuning; production readiness
> NOT claimed. Next: mandated human + ChatGPT post-run review + recommended
> Fable 5 adversarial post-run audit, then the PR #413 pivot (M15/H1/H4).
>
> POST-RUN AUDIT pointer: the Fable 5 post-run audit
> (docs/design/ml_step4_365d_ba_first_run_post_audit_fable5.md) found the run
> procedurally clean (one-shot, provenance complete, holdout once) but its
> decision metrics INVALID: ML_STEP4_365D_BA_FIRST_RUN_EVIDENCE_INVALID.
> Proven from committed evidence: fixed PIP_SIZE=0.0001 applied to all pairs
> misconverts the 6 JPY crosses (pip=0.01) by 100x — JPY per-trade mean
> -358.78 vs non-JPY -3.18 (ratio 112.8); JPY = 98.4% of total loss (CHF_JPY
> 91.5%). The DOES_NOT_MEET result must NOT be cited; the M1 first-run
> question is NOT closed. Non-decisional: the correctly-scaled non-JPY
> portion (~-3.5 net pips/trade) matches the archived honest M1 band. Next:
> human + ChatGPT decide whether the invalidation permits a corrected second
> first-run attempt (per-pair pip fix + mixed-scale tests + re-check) or M1
> closes on archived honest evidence. No rerun/tuning performed.
>
> INV-1 PIP-SIZE FIX pointer (code-only, NO RUN): the invalidator was fixed
> code-only in `docs/design/ml_step4_pip_size_fix_note.md` — a single per-pair
> pip-size authority `data_adapter.pip_size_for` (`0.01` if `*_JPY` else
> `0.0001`, matching `compare_multipair_v9_orthogonal._pip_size`) routed into
> every `bulk_labels` caller, with a per-pair pip-size map recorded in the
> manifest + leakage/provenance evidence, plus mixed-scale value-pinned tests
> proving the bug cannot recur. Status:
> `ML_STEP4_PIP_SIZE_INVALIDATOR_FIXED_NO_RUN` /
> `PRODUCTION_READINESS_NOT_CLAIMED`. This fix does NOT rerun ML Step 4, train,
> evaluate holdout, read real data, or generate corrected metrics/evidence. A
> corrected second first-run attempt remains **unauthorised**; it stays
> admissible only after a Fable 5 re-check of this fix AND a separate human +
> ChatGPT decision explicitly authorising it.
>
> PIP-SIZE FIX RE-CHECK pointer (Fable 5, doc-only): the adversarial re-check
> (docs/design/ml_step4_pip_size_fix_recheck_fable5.md) verified the PR #423
> fix — single per-pair authority (grep-confirmed sole price->pips division in
> the package), both bulk_labels call sites routed, map resolved fail-closed
> before training, evidence/manifest mapping recorded, 26 value-pinned tests
> that would have caught the PR #421 bug three independent ways, B-1/B-2/cost/
> threshold/refusal machinery byte-untouched, and a static metadata check that
> all 20 committed inventory filenames parse to well-formed pairs with exactly
> 6 _JPY crosses. Verdict:
> ML_STEP4_PIP_SIZE_FIX_ACCEPTABLE_FOR_CORRECTED_FIRST_RUN_DECISION /
> PRODUCTION_READINESS_NOT_CLAIMED. Zero blockers; 3 non-blocking residuals
> (manifest-field optionality hardening; unknown-pair fallback scope pinned to
> this epoch; flat cost cell = frozen contract design, out of scope). The
> re-check authorises NOTHING: a corrected second first-run attempt still
> requires the separate explicit human + ChatGPT decision (including the
> same-holdout re-measurement ruling).
>
> CORRECTED SECOND FIRST-RUN pointer: the human + ChatGPT decision explicitly
> approved exactly one corrected second first-run on the same frozen 365d_BA
> holdout (re-measurement, not re-optimisation). Executed once at code SHA
> 6fbb178280b4 (== master post-#424); all 12 gates PASS; 20/20 files &
> 1,481,715,517 bytes checksum-verified; per-pair pip map resolved before
> training (6 _JPY->0.01, 14 non-JPY->0.0001,
> global_pip_size_authoritative_for_all_pairs=false); v4-base 39 features;
> holdout evaluated once. VALID corrected result =
> ML_STEP4_365D_BA_CORRECTED_SECOND_RUN_COMPLETED /
> ML_STEP4_FIRST_RUN_EVIDENCE_CREATED_DOES_NOT_MEET_PREREGISTERED_CRITERIA:
> expectancy -3.49 pips/trade (was invalid -127.75), maxDD 2.82x notional (was
> 103.25x), Sharpe -18.91; JPY per-trade -4.45 vs non-JPY -3.04 (100x inflation
> gone); trade count/holdout/threshold identical to #421 (labels pip-agnostic).
> Evidence (metadata-only, scrub-clean) at
> artifacts/ml_step4/365d_ba_v1/corrected_second_run_6fbb178280b4/; #421 invalid
> evidence and #409 stop evidence untouched. Report:
> docs/design/ml_step4_365d_ba_corrected_second_run_execution_report.md.
> PRODUCTION_READINESS_NOT_CLAIMED. Next: human + ChatGPT post-run review +
> Fable 5 post-run audit; if it validates provenance, the M1 flagship first-run
> question can be closed on honest evidence. No rerun; no tuning; no pivot
> started.
>
> CORRECTED-RUN POST-AUDIT + DIAGNOSIS pointer (Fable 5, doc-only): the
> adversarial audit
> (docs/design/ml_step4_365d_ba_corrected_second_run_post_audit_and_diagnosis_fable5.md)
> found the PR #425 evidence VALID —
> ML_STEP4_365D_BA_CORRECTED_SECOND_RUN_EVIDENCE_VALID_DOES_NOT_MEET: one-shot
> clean, provenance complete, arithmetic identities airtight (cells exact 0.5
> steps; sum(pair net@0.5) = 8,082 x -3.4875 = maxDD pips exactly; win/loss
> identity exact), pip fix verified in-run (JPY/non-JPY per-trade ratio 1.47x
> vs 112.8x invalid; 20/20 pairs negative -> broad-based). Research diagnosis:
> M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA —
> negative GROSS edge (-2.99 pre-cell; not cost-killed), no validation edge at
> any threshold (-16.2 all), turnover 4.2x over gate, win rate 7.83% vs ~40%
> breakeven; M1 lineage closed
> (M1_FLAGSHIP_CLOSED_THIS_LINEAGE_FAILED; general M1 requires a new
> microstructure-grade hypothesis). Recommended next (NOT started, NOT
> authorised): pre-registration design PR for an M15-first (H1 secondary)
> cost-hurdle-aware family — spread-floored barrier labels, empirical per-pair/
> session cost model, turnover budget, EV-based gate, validation-first evidence
> gate before any new frozen holdout; the PR #425 holdout is consumed and is
> never a design set. PRODUCTION_READINESS_NOT_CLAIMED. Awaits human + ChatGPT
> post-run review countersignature.
>
> POST-M1 RESEARCH PROGRAM ROADMAP pointer (doc-only): with the M1 flagship
> closed, a program-level roadmap
> (docs/design/post_m1_research_program_roadmap_fable5.md) proposes the next
> research sequence — POST_M1_RESEARCH_PROGRAM_ROADMAP_PROPOSED /
> NO_EXECUTION_PERFORMED. Ranking: A M15-first cost-hurdle-aware family FIRST,
> B H1/H4 swing SECOND; session/vol + calendar as supporting layers only;
> carry + microstructure-M1 deferred (data); portfolio layer gated on a
> positive-edge family; risk-overlay-only forbidden as standalone. Ten-gate
> pipeline (thesis -> roadmap audit -> pre-registration -> design audit ->
> implementation -> source audit -> single run -> post-audit -> disjoint
> replication -> separate paper/live gates). Dataset strategy: consumed
> 365d_BA holdout permanently quarantined; new epochs need Gate-P2-style
> adoption; 730d/3650d unauthorised. Next gate: Fable 5 adversarial roadmap
> audit; nothing implemented/executed/authorised.
>
> ROADMAP AUDIT pointer (Fable 5, doc-only): the adversarial audit
> (docs/design/post_m1_research_program_roadmap_audit_fable5.md) found the
> PR #427 roadmap ACCEPTABLE —
> POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION
> — with 8 binding conditions (C-1..C-8) on the gate-3 pre-registration and
> 3 rulings: R-2a pre-holdout span = exploratory design only with FIXED
> PAIRS_20 + disjoint later validation/holdout; R-2b the consumed calendar
> window 2026-03-01..2026-04-24 is dead for ALL roles at ALL timeframes;
> ranking KEEP A-FIRST (M15; H1-first rejected on sample-size/epoch-friction;
> H1/H4 split if reached). Added gate 3a (Gate-P2-style epoch/dataset adoption
> artifact before gate-3 merge); acceptance floors made cost-relative +
> dual stressed-cost; evidence schema must add exit-type/timeout/concurrency;
> program budget = families A then B only, both failing => mandatory program
> review (stopping rule); 12 missing risks recorded (effective-N overlap,
> cross-pair dependence, quote-vs-fill gap, M1->M15 aggregation bugs, etc.).
> Zero blockers requiring roadmap rewrite. Allowed next PR: doc-only family-A
> (M15-first) pre-registration incorporating R-2a/R-2b + C-1..C-8. Nothing
> implemented/executed/authorised; NO_EXECUTION_PERFORMED /
> PRODUCTION_READINESS_NOT_CLAIMED.
>
> FAMILY-A PRE-REGISTRATION pointer (gate 3, doc-only): the M15-first
> cost-hurdle-aware pre-registration design
> (docs/design/m15_first_cost_hurdle_aware_preregistration_design.md) was
> proposed — M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_PROPOSED. Incorporates
> R-2a (design = 365d_BA pre-holdout span M15 aggregate, fixed PAIRS_20,
> never-evidence) + R-2b (dead window 2026-03-01..2026-04-24 excluded from
> every role) + C-1..C-8. Dataset plan: design 2025-04-25..2026-02-28;
> validation+frozen holdout from a NEW forward epoch starting 2026-04-25
> (gate 3a adoption required; spans [FIXED-AT gate 3a]). Label: spread-floored
> bid/ask triple-barrier + cost-hurdle eligibility (h_min x cost), horizon
> candidate {16,24,32} M15 bars, ONE frozen at merge. Decision: calibrated
> EV gate (raw probability threshold explicitly not permitted), ev_min from
> {0.0,0.25,0.5} pips on validation only. Acceptance: cost-relative floors
> (net>0 AND gross>=1.5x cost), dual stressed-cost (2x + p90), turnover<=40/d,
> effective-N gate + INSUFFICIENT_SAMPLE, validation-first kill gate (family
> closes without holdout touch on validation failure). AMENDED: human +
> ChatGPT rulings 1-13 applied in-document (new section 16) — all contract
> values FROZEN (horizon 24 M15 bars; TP/SL 1.5/1.0 x ATR14 with 3.0/2.0 x
> cost floors; hurdle 1.5xATR >= 2.0xcost; sessions frozen; rollover
> 21:55-22:15 minimum widen-only; padding 0.3 + cell 0.5 pip; LightGBM params
> frozen; no class weighting; isotonic calibration; ev_min {0.0,0.25,0.5};
> acceptance table frozen, design audit may only tighten). C-1 resolved by
> deferral: gate 3a = separate PR docs/m15-gate3a-dataset-epoch-adoption,
> required before any implementation data read. Remaining deferred items carry
> explicit [FIXED-AT gate 3a / design audit / implementation audit] markers.
> Merge of PR #429 accepts the frozen contract; nothing implemented/trained/
> executed/adopted; NO_EXECUTION_PERFORMED / PRODUCTION_READINESS_NOT_CLAIMED.
> Next gate: Fable 5 design audit.

- **Purpose:** execute the smallest safe real run under the pre-registered
  contract, exactly as registered.
- **Constraints:** minimal span; minimal config set; **no sweep explosion**;
  **no opportunistic best-of-many promotion** (the champion is the champion);
  no production routing; metadata-only evidence first (raw outputs retained
  per epoch policy, committed evidence scrubbed); no promotion of any result
  without Phase H.
- **Output:** `FIRST_REAL_ML_RUN_EVIDENCE_CREATED` or `FIRST_REAL_ML_RUN_FAILED`.

### Phase H — Post-run audit

- **Purpose:** decide whether the first run's evidence is trustworthy and
  whether a second experiment is allowed.
- **Must review:** data provenance (epoch ID + SHA match), code SHA, config
  hash, split integrity (holdout untouched until the registered final read),
  no leakage (feature/label audit on the actual run config), metric
  definitions as registered, multiplicity control adherence,
  acceptance/failure criteria applied as pre-stated, and whether the run
  stayed entirely within the pre-registration contract.
- **Output:** `POST_RUN_AUDIT_ACCEPTS_EVIDENCE` or
  `POST_RUN_AUDIT_REJECTS_EVIDENCE`.
- **Must not output** (forbidden-outcome list): production readiness, `Tier 1`
  membership, or automatic routing approval — these tokens appear here only
  as prohibitions.

## 5. T2 strategy recommendation

Candidate spans: `365d_BA`, `730d_BA`, `3650d_BA` (all
`LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`, retention unresolved).

1. **One-span pilot.** Pros: lowest risk; validates credentials, destination
   config, object-lock behaviour, deposit/restore mechanics, and evidence
   shape end-to-end; easy rollback; a failure burns one span's effort only.
   Cons: does not prove retention for the other spans; leaves the probe
   partially resolved.
2. **All-span execution.** Pros: fastest if everything works; completes
   retention evidence in one step. Cons: highest blast radius — a
   credential / bucket-policy / object-lock mistake affects all spans at
   once (~17.5 GB+ across the 3650d set); debugging a mid-stream failure is
   harder; partial completion produces a mixed evidence state that itself
   needs adjudication.
3. **Pilot-then-expand.** Pros: validates the whole process at low risk on
   one span, then completes the remaining spans with a proven procedure and
   identical evidence shape; each stage has a clean go/no-go. Cons: more
   PRs/steps and two credentialed sessions instead of one.

**Recommendation: pilot-then-expand, with `365d_BA` as the pilot span.**
Rationale: the smallest span (20 files, ~1.5 GB-class) exercises every
mechanism the larger spans need — credentials, alias resolution, object
lock, atomic deposit, restore, checksum recompute-and-compare against
PR-B.1 inventory, evidence scrubbing — at the lowest cost of failure. The
first credentialed execution in this project's history should not have an
all-span blast radius. Expansion to `730d_BA` + `3650d_BA` follows only
after the pilot's evidence is reviewed clean (`T2_ROUND_TRIP_EVIDENCE_CREATED`
for the pilot is a gate input to the expansion PR, not an auto-trigger).

## 6. Gate table

| Gate | Purpose | Required input | Required evidence | Allowed actions | Forbidden actions | Output status | Next gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. Post-remediation readiness audit | Confirm remediation closure; find pre-T2 blockers | Merged PRs #388–#391; test/cleanliness state | Audit doc w/ PR SHAs, suite results, residual list | Read code/docs; run existing tests/lint | Real-data runs; T2; admissibility; epoch; Step 4 | `POST_REMEDIATION_READINESS_AUDIT_COMPLETE` / `..._BLOCKERS_REMAIN` | B |
| B. T2 execution plan | Fix execution shape + procedure | Phase A complete; T2 readiness contract | Plan doc (strategy, credentials, alias, object lock, process, stop conditions) | Author/review docs | Any execution; credential access | `T2_EXECUTION_PLAN_APPROVED` / `..._BLOCKED` | C |
| C. T2 round-trip (pilot, then expand) | Deposit/restore/verify bytes | Approved plan; operator credentials (human) | Metadata-only manifest + recomputed checksums + cleanliness report | Deposit/restore/checksum per plan | Claiming admissibility/epoch/Step 4; committing raw data; faking success | `T2_ROUND_TRIP_EVIDENCE_CREATED` / `..._FAILED` | D |
| D. Byte-admissibility review | Approve specific bytes as admissible inputs | Phase C evidence | Review memo binding span IDs + checksums | Read/review evidence | Experiment design approval; epoch adoption; performance claims | `BYTE_ADMISSIBILITY_APPROVED_FOR_SPECIFIC_SPANS` / `..._REJECTED` | E |
| E. New epoch adoption | Name a research epoch over admissible spans | Phase D approval | Epoch record (full field list, §4-E) | Author epoch record; carve frozen holdout | Any model/feature/label run; production claims | `NEW_EPOCH_ADOPTED_FOR_RESEARCH_ONLY` / `NEW_EPOCH_NOT_ADOPTED` | F |
| F. ML Step 4 pre-registration | Fully specify the first experiment | Adopted epoch | Pre-registration contract (§4-F field list) | Design/author only | Training; inference; real-data reads beyond epoch metadata | `ML_STEP4_PRE_REGISTRATION_CONTRACT_CREATED` / `ML_STEP4_DESIGN_BLOCKED` | G |
| G. First real ML run | Smallest safe run, exactly as registered | Registered contract + explicit run authorisation (human) | Run evidence per report schema (code SHA, config hash, epoch ID) | Train/evaluate within contract only | Sweeps beyond registered set; best-of-many promotion; production routing | `FIRST_REAL_ML_RUN_EVIDENCE_CREATED` / `..._FAILED` | H |
| H. Post-run audit | Decide evidence trust; allow/deny next experiment | Phase G evidence | Audit memo over §4-H checklist | Read/review; re-verify hashes | Production readiness; `Tier 1`; auto-routing (prohibited outputs) | `POST_RUN_AUDIT_ACCEPTS_EVIDENCE` / `..._REJECTS_EVIDENCE` | Next-experiment decision |

## 7. Global stop conditions

Stop (fail closed, report, do not proceed) if at any phase:

- protected stage24/stage25 artifacts become dirty;
- `data/` or real `artifacts/` evidence would be committed outside the
  phase's explicitly-defined metadata-only evidence;
- credentials/cloud access is needed outside Phase C (T2) or Phase G's
  registered run environment;
- T2 evidence is incomplete (any span missing deposit, restore, or checksum
  legs);
- a checksum mismatch occurs anywhere (deposit-vs-inventory or
  restore-vs-deposit);
- byte identity is ambiguous (basename collisions, mixed price modes,
  overlapping span definitions, inventory-reference conflicts);
- epoch metadata is incomplete against the §4-E field list;
- Step 4 design requests broad sweeps or unenumerated config spaces;
- any phase attempts to produce a production claim;
- any phase attempts to rehabilitate archived/invalid Phase 9.X numerics as
  routing evidence;
- any phase attempts to promote Phase 9.16 beyond its Tier 2 fenced
  comparator status.

## 8. Recommended next PR sequence

| # | PR | Type | Real data? | Credentials/cloud? | Fable 5 review? | Opus sufficient? |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Post-remediation readiness audit (Phase A) | doc + evidence (test outputs) | No | No | **Yes — strongly recommended** | Authoring assist only |
| 2 | T2 execution plan (Phase B) | doc-only | No | No | **Yes** | Mechanical drafting only |
| 3 | T2 one-span pilot `365d_BA` (Phase C1) | evidence (metadata-only) + minimal tooling | Yes (deposit/restore of existing local bytes) | **Yes** (operator-provisioned) | Yes — evidence review | Tooling yes, if design fixed |
| 4 | T2 all-span expansion `730d_BA`+`3650d_BA` (Phase C2, only after clean pilot review) | evidence (metadata-only) | Yes | **Yes** | Yes — evidence review | Yes (procedure proven) |
| 5 | Byte-admissibility review (Phase D) | doc-only decision memo | No (reads evidence) | No | **Yes — strongly recommended** | No |
| 6 | New epoch adoption (Phase E) | doc + epoch record | No (metadata) | No | **Yes — strongly recommended** | No |
| 7 | ML Step 4 pre-registration contract (Phase F) | doc-only | No | No | **Yes — strongly recommended** | No |
| 8 | First real ML run (Phase G) | implementation + evidence | **Yes** | Possibly (compute env) | Yes — run-evidence review | Execution mechanics yes |
| 9 | Post-run audit (Phase H) | doc-only audit memo | No (reads evidence) | No | **Yes — strongly recommended** | No |

## 9. Model assignment recommendation

- **Fable 5 strongly recommended (judgement-heavy, adversarial-review
  phases):** post-remediation readiness audit (A); T2 roadmap/gate design
  refinements (B); byte-admissibility review (D); new epoch adoption (E);
  ML Step 4 pre-registration (F); post-run audit (H).
- **Opus acceptable (mechanical / already-designed work):** mechanical doc
  updates and pointer edits; implementation of already-approved guards and
  fixes; test maintenance; T2 tooling once the Phase B design is fixed;
  run-execution mechanics in Phase G under the registered contract.
- **Human + ChatGPT approval required (irreversible / authorisation
  decisions):** every merge; T2 execution (Phase C — credentialed);
  byte-admissibility approval (Phase D verdict); new epoch adoption
  (Phase E verdict); first real ML run authorisation (Phase G go/no-go).

## 10. Non-authorisation statements

- This roadmap does **not** execute T2.
- This roadmap does **not** approve byte-admissibility.
- This roadmap does **not** adopt a new epoch.
- This roadmap does **not** authorise ML Step 4.
- This roadmap does **not** authorise a real-data run.
- This roadmap does **not** approve production readiness.
- This roadmap does **not** rehabilitate historical Phase 9.X numerics.
- This roadmap does **not** promote or demote Phase 9.16 (it remains Tier 2
  `VALID_OPERATIONAL_BASELINE`, fenced comparator with audit caveats).

Forbidden-label note: no part of this document asserts `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `PRODUCTION_READY`, `MODEL_IMPROVED`,
or `EXPECTANCY_IMPROVED`; where such tokens appear above they are listed
solely as prohibited outputs.
