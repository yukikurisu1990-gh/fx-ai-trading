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
