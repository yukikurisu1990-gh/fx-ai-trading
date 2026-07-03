# Phase A — Post-remediation readiness audit

- **Document class:** doc/evidence memo (Phase A of the post-remediation gate
  roadmap; executes nothing)
- **Roadmap source-of-truth:** `docs/design/post_remediation_t2_ml_step4_roadmap.md`
  (§4 Phase A), merged as PR #392.
- **Base:** master `b23c718` (post PR #392 merge)
- **Branch:** `docs/phase-a-post-remediation-readiness-audit`
- **Audit model:** Opus 4.8 (per roadmap §9, Phase A is a Fable-5-preferred gate;
  this instance was human-directed on Opus and confines itself to a doc/evidence
  audit — no judgement call here promotes anything or authorises any next gate).

---

## 1. Executive conclusion

**`POST_REMEDIATION_READINESS_AUDIT_COMPLETE`**

The five audit findings scheduled for remediation before T2 planning — F-1, P1-A,
F-2, F-5, F-8 — are each closed by a merged PR whose supporting tests exist on
master and pass at this base. No code, data/provenance, train/serve, or artifact
hygiene blocker remains that must be fixed before Phase B (T2 execution planning).
The residuals carried from PR #391 are individually assessed in §5 and none is a
pre-Phase-B or pre-Phase-C blocker.

This conclusion authorises nothing beyond recommending Phase B as the next
doc-only step (§8). It does not start Phase B, does not execute T2, and makes no
performance or admissibility claim.

Forbidden-label note: no part of this memo asserts `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
or `PRODUCTION_READY`; where those tokens appear they are listed solely as
prohibited outputs.

## 2. Scope

This is **Phase A** from `docs/design/post_remediation_t2_ml_step4_roadmap.md`.

Confirmed properties of this PR:

- doc/evidence only — the only file added is this memo (plus, if useful, a
  pointer; see the header of the roadmap doc — not rewritten);
- no real-data run; no model training; no label/feature generation over real data;
- no T2 execution; no credential or cloud access;
- no byte-admissibility review or approval;
- no new epoch adoption;
- no ML Step 4 authorisation;
- no production-readiness claim;
- no promotion or demotion of Phase 9.16;
- no rehabilitation of historical Phase 9.X numerics.

The test/lint commands run for §6 are read-only over the repository at rest and
touch no real market data.

## 3. Current master and PR lineage

- **Current branch:** `docs/phase-a-post-remediation-readiness-audit`
- **Current master SHA:** `b23c718051b4c723db20c154055218c6cfc8298f`
- **PR #388** (Fable 5 audit memo) merge SHA: `27b81a94d7910870b94d1b76432223a54060dd76`
- **PR #389** (F-1 fix) merge SHA: `4b2875362252f00ac7fa4c706b20bb865268eb4f`
- **PR #390** (P1-A + F-2) merge SHA: `bd8722145466d3fcf99fb5f0302040b3ad9fbc86`
- **PR #391** (F-5 + F-8) merge SHA: `1c8f0f40e5708c2950eefb84a551f1caeeeb2bb9`
- **PR #392** (post-remediation roadmap) merge SHA: `b23c718051b4c723db20c154055218c6cfc8298f`

All six SHAs were resolved from the merged PR records (not inferred). Master tip
equals the PR #392 merge SHA, i.e. master carries the roadmap that authorises
this Phase A.

## 4. Remediation closure review

### F-1 — live entry `adopted_ev_after_cost` crash

- **Expected state:** fixed by PR #389.
- **On master:** `MetaCycleRunResult.adopted_ev_after_cost` exists and is populated
  from the adopted candidate; the live spread/EV gate reads it via
  `_evaluate_live_ev_gate`, which fails closed (no trade) on missing/non-finite EV
  rather than defaulting to 0.0 or crashing.
- **Tests:** `tests/unit/test_run_paper_decision_loop_live_ev_gate.py` +
  `tests/unit/test_meta_cycle_runner.py` → **35 passed** at this base.
- **Verdict:** closed.

### P1-A — stage24/stage25 tracked-artifact output isolation

- **Expected state:** fixed by PR #390.
- **On master:** stage-eval smoke tests pass `--out-dir tmp_path`; each asserts its
  tracked artifact bytes are unchanged; `tests/conftest.py` carries an autouse
  session guard `protect_tracked_artifacts` enumerating **8** protected paths
  (the six named in the instruction plus `stage25_0a/causality_audit.md` and
  `stage25_0d/eval_report.md`) and failing the session on any modification.
- **Cleanliness:** after the §6 checks, `git status --porcelain` shows the
  protected stage24/stage25 paths clean.
- **Verdict:** closed.

### F-2 — PnL-layer correction

- **Expected state:** corrected by invariant tests in PR #390.
- **On master:** `scripts/traded_direction_pnl.py` scores the traded direction's own
  barrier path (SL-first tie, TP exact, timeout mark-to-market), wired into the five
  evidence-relevant evaluators (v5/v9/v19/v23/v26); the 14 archived/superseded
  evaluators intentionally keep the old scorer under a static-guard allowlist.
- **Tests:** `tests/unit/test_f2_pnl_layer_invariants.py` → **37 passed**
  (helper truth table + per-script invariants × 5 + old-pattern static guard).
- **Historical numerics:** not rehabilitated — the correction adds outcome columns
  and re-scores prospectively; committed Phase 9.X reports remain records of the old
  scorer. No metric was recomputed by this audit.
- **Verdict:** closed; historical numerics remain un-rehabilitated.

### F-5 — ingestion provenance hardening

- **Expected state:** hardened by PR #391.
- **On master, confirmed present:**
  - truncation / partial-fetch fail-closed: `fetch_oanda_candles.py` streams to
    `.incomplete`, promotes atomically only on full success, exits non-zero on
    failure — tested;
  - inventoried-span overwrite guard: `scripts/provenance_guard.py` (read-only over
    Gate P1 PR-B, Foundation T2, and the 2026-05-31 archive manifest) with an
    explicit, non-silent override that disclaims byte-admissibility/epoch/Step 4;
  - model-manifest provenance: `train_lgbm_models.py` writes per-pair SHA-256, time
    bounds, logical IDs (basenames only), price mode, label/cost contracts, code
    SHA, config hash — tested to contain no personal absolute paths.
- **Tests:** `tests/unit/test_f5_ingestion_provenance.py` +
  `tests/unit/test_f5_model_manifest_provenance.py` → **43 passed**.
- **No real-data refetch** occurred in this audit (all fetch clients are mocked in
  the tests; no network access).
- **Verdict:** closed.

### F-8 — train/serve consistency hardening

- **Expected state:** hardened by PR #391.
- **On master, confirmed present:**
  - SL-first tie-break contract in the trainer (strict `<`), differential-tested
    against `compare_multipair_v9`;
  - ATR warmup guard (`min_periods=14`);
  - fill-anchored contract barriers with fail-closed behavior on missing fill/ATR
    (no silent decision-close mid re-anchor);
  - completed-bucket MTF fallback (drops the in-progress bucket);
  - `pips_post_cost` EV contract (`src/fx_ai_trading/domain/ev_contract.py`) with
    fail-closed rejection of non-comparable units before ranking;
  - `force_fallback` default `False` (production-like fail-closed);
  - residuals documented in `docs/design/train_serve_consistency_contract.md`.
- **Tests:** `tests/unit/test_f8_trainer_label_contract.py` +
  `test_f8_live_anchor_asof.py` + `test_f8_ev_contract.py` +
  `test_feature_service_mtf.py` → **110 passed**.
- **Verdict:** closed.

## 5. PR #391 residual review

Each residual is described, then assessed against three downstream gates plus
follow-up need. "Blocks Phase B" = must be fixed before authoring the T2 execution
plan; "Blocks Phase C" = before running the T2 round-trip; "Blocks Phase F" =
before writing the ML Step 4 pre-registration contract.

| Residual | Blocks Phase B? | Blocks Phase C (T2)? | Blocks Phase F (Step 4 design)? | Follow-up PR? |
| --- | --- | --- | --- | --- |
| R1. OANDA pre-fill protective proxy uses decision-close anchor | No | No | No | Eventually (pre live-money) |
| R2. TA strategies / ai_stub fail-closed on unvalidated EV unit | No | No | No | Optional |
| R3. `MetaDeciderService` ev_unit not enforced (tests-only path) | No | No | No | Only if wired to production |
| R4. Serve-side ATR warmup minor skew on very short histories | No | No | No | Optional |
| R5. Archive completion marker size-only | No | No | No | Optional (pre-scale) |
| R6. Deployed `models/lgbm/` predate F8-A / F5-E contracts | No | No | **Yes (must be honoured in the Step 4 design, not "fixed")** | Retrain PR (post-epoch, authorised) |

- **R1 — protective-proxy anchor.** OANDA `takeProfitOnFill`/`stopLossOnFill` are
  constructed pre-fill, so they use the decision-close as a labeled crash-protection
  proxy; the software exit path uses fill-anchored contract barriers. Not a data,
  provenance, or evaluation concern → does not block T2 or Step 4 *design*. It is a
  live-execution refinement (needs a broker trade-amend API) relevant only when a
  real-money live path is contemplated, which is far beyond the current gate.
- **R2 — TA/ai_stub fail-closed.** Intentional safety behavior: incomparable EV
  units are rejected before ranking, so `--use-ta-strategies` adopts zero trades.
  This is a fail-closed outcome, not a defect; the default runner (LGBM,
  `pips_post_cost`) is unaffected. No gate impact.
- **R3 — MetaDeciderService.** Imported only by its own module and tests; not on
  any production adoption path. A follow-up applies only if it is ever wired in —
  not a precondition for T2 or Step 4 design.
- **R4 — serve-side ATR warmup skew.** Affects only pathologically short live
  histories; the live loop requires a deep warmup buffer and `_barrier_prices`
  fail-closes on non-finite/non-positive ATR, so no silent trade path depends on it.
  Documented residual; no gate impact.
- **R5 — size-only completion marker.** A resume-hygiene heuristic (skip vs
  re-fetch); it never establishes identity or admissibility — those rest on the
  checksum-bearing inventory guard and, downstream, on the T2 round-trip and the
  Phase D byte-admissibility review. Acceptable as a pre-T2 hardening step.
- **R6 — deployed models predate the aligned contracts.** This is the one residual
  with real downstream weight, but it is **not a blocker to be "fixed" before T2**:
  the deployed `models/lgbm/` artifacts were trained under the old TP-first
  tie-break and without the F5-E provenance manifest. The correct handling is that
  the Phase F ML Step 4 pre-registration contract must specify a **contract-consistent
  retrain on the adopted epoch** and must not reuse the pre-alignment models as
  evidence. So R6 constrains Phase F's *design*, is honoured there rather than
  patched now, and requires a retrain PR only after an epoch is adopted and Step 4 is
  authorised. It does not block Phase B or Phase C.

**Residual verdict:** none of R1–R6 blocks Phase B or Phase C; only R6 imposes a
design constraint on Phase F, which the roadmap already anticipates (§4 Phase F
"contract-consistent retrain … must not reuse pre-alignment models as evidence").

## 6. Test and cleanliness evidence

Commands run at base `b23c718` (this branch, before adding this memo the tree was
clean; after adding it, the only tracked change is this file):

- `git diff --name-only master...HEAD` → `docs/design/post_remediation_readiness_audit.md` (this memo only)
- `git status --porcelain` → only the new memo (untracked local `artifacts/*.log`
  and similar predate this work and are not part of the diff)
- `python tools/lint/run_custom_checks.py` → **All checks passed!**
- `ruff check .` → **All checks passed!**
- `ruff format --check .` → **590 files already formatted**
- F-1 tests (`test_run_paper_decision_loop_live_ev_gate.py`, `test_meta_cycle_runner.py`) → **35 passed**
- F-2 invariant tests (`test_f2_pnl_layer_invariants.py`) → **37 passed**
- F-5 tests (`test_f5_ingestion_provenance.py`, `test_f5_model_manifest_provenance.py`) → **43 passed**
- F-8 tests (`test_f8_trainer_label_contract.py`, `test_f8_live_anchor_asof.py`, `test_f8_ev_contract.py`, `test_feature_service_mtf.py`) → **110 passed**
- P1-A protected-artifact guard: present in `tests/conftest.py` (8 protected paths);
  protected stage24/stage25 paths clean before and after the above runs
- `pytest tests/gate_p1_pr_b tests/ml_uplift_harness tests/foundation_t2` → **198 passed, 0 skipped**
  (the previously-seen launcher pre-flight skips did not occur because the tracked
  worktree is clean)

**Full local pytest:** not rerun for this doc/evidence PR. The last full run (at the
PR #391 base, same code surface) was **4152 passed, 3 failed, 5 skipped**, where the
3 failures are the pre-existing local-data failures `test_exit_flow`,
`test_replay_reproducibility`, and `test_stage25_0d` (dependent on locally
smoke-corrupted / absent data, unrelated to F-1/F-2/F-5/F-8/P1-A). This memo does
**not** claim full local pytest is green.

**Post-check cleanliness:** `git status --porcelain` re-run after the test battery
shows the protected stage24/stage25 artifacts and `data/` unmodified; the only
tracked change on this branch is this memo.

## 7. Blocker assessment before Phase B

1. **Are F-1, P1-A, F-2, F-5, F-8 closed enough to proceed to Phase B?** Yes — each
   is fixed by a merged PR with passing supporting tests on master (§4).
2. **Remaining code blocker before Phase B?** No. All targeted suites pass; the F-8
   contracts are in force; the F-1 live gate fails closed.
3. **Remaining data/provenance blocker before Phase B?** No. F-5 guards
   (atomic writes, inventoried-span guard incl. the archive manifest,
   marker-based resume, model-manifest provenance) are present and tested. Note:
   Phase B is doc-only planning; actual data retention is the *subject* of the
   T2 plan, not a blocker to writing it.
4. **Remaining train/serve consistency blocker before Phase B?** No. The F-8
   contract is aligned and tested; R6 (pre-alignment deployed models) is a Phase F
   design constraint, not a Phase B blocker.
5. **Remaining artifact hygiene blocker before Phase B?** No. The P1-A session guard
   is active and protected artifacts are clean.
6. **Any reason to revise the roadmap before Phase B?** No. The nine-gate structure
   in PR #392 remains appropriate; §5 confirms the residuals are already correctly
   located within it (notably R6 under Phase F).

**Phase B may be recommended as the next step. This memo does not approve or start
Phase B.**

## 8. Recommended next decision point

- **Next PR:** Phase B — T2 execution plan.
- **Type:** doc-only.
- **Requires:** no credentials, no cloud, no T2 execution, no byte-admissibility,
  no new epoch, no ML Step 4, no real-data run.
- **Content (per roadmap §4 Phase B / §5):** fix the execution shape
  (recommended: pilot-then-expand, `365d_BA` pilot), and document credential
  handling, destination alias, object-lock/retention requirement, deposit/restore/
  checksum process, metadata-only evidence format, and stop conditions.
- **Model:** Fable 5 strongly recommended (roadmap §9).

No blockers require a fix-PR before Phase B.

## 9. Non-authorisation confirmations

- This PR does **not** execute T2.
- This PR does **not** approve byte-admissibility.
- This PR does **not** adopt a new epoch.
- This PR does **not** authorise ML Step 4.
- This PR does **not** authorise a real-data run.
- This PR does **not** train a model.
- This PR does **not** generate real-data labels/features.
- This PR does **not** compute or claim new Sharpe/PnL/DD/win-rate/expectancy.
- This PR does **not** approve production readiness.
- This PR does **not** rehabilitate historical Phase 9.X numerics.
- This PR does **not** promote or demote Phase 9.16 (it remains Tier 2
  `VALID_OPERATIONAL_BASELINE`, fenced comparator with audit caveats).
- This PR does **not** start Phase B.
