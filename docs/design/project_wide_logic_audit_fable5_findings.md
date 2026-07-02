# Project-wide Read-only Logic Audit — Fable 5 Findings

- **Document class:** audit memo (doc-only; records findings, changes nothing)
- **Audit date:** 2026-07-03
- **Auditor:** Claude Fable 5 (lead reasoning auditor) + 8 specialist sub-agent auditors
  (data lineage / labels / features-leakage / validation-backtest / model-metrics /
  execution-risk / evidence-provenance / roadmap-consistency)
- **Repository state audited:** `master` @ `87f1c568dffb1ccc0b2fd615a20986a4f3540470`
- **This memo's own scope:** adds this one file only. No code, tests, artifacts, or data
  are changed by the PR that introduces this memo. No fixes are implemented here.

## 0. Nature and limits of the audit (read before citing)

- This was a **read-only** audit: repository source code, committed docs, committed
  metadata artifacts, and file metadata were inspected; static grep/search was used.
- **No code was changed** by the audit.
- **No new real-data backtests were run.** No model training was run. **No new metrics
  over real market data were computed** — every numeric quoted below is read from
  committed code, docs, or artifacts, not recomputed.
- Only **lint and the existing unit-test suite** were executed
  (`ruff check` / `ruff format --check` / `tools/lint/run_custom_checks.py` / `pytest`).
- Findings are based on inspection of repository code/docs/artifacts. Some findings may
  require future targeted proof or regression tests to quantify their magnitude; however,
  the blocker-class issues are serious enough that **real ML runs must halt until they
  are addressed**, independent of exact magnitudes.
- No credentials, env-var values, cloud, network, broker, or OANDA access occurred.
  No T2 execution, no deposit/restore/round-trip, no byte-admissibility approval,
  no new-epoch construction/adoption, no ML Step 4, no production change, no LLM
  integration.

## 1. Status

**AUDIT_BLOCKERS_FOUND**

Forbidden-label warning (these labels are listed ONLY to forbid them; nothing in this
memo asserts any of them): no part of this memo claims or implies `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `PRODUCTION_READY`, `MODEL_IMPROVED`, or
`EXPECTANCY_IMPROVED`.

## 2. Scope inspected

- **Branch/SHA:** `master` @ `87f1c56`. Observed repo state at audit time: **PR #387 was
  already merged** (merge commit `87f1c56` is the master tip), so the Foundation T2
  harness + pre-deposit stop evidence were **included** in the audited surface. The T2
  content is harness + stop evidence only: no deposit, no restore, no round-trip occurred
  and the retention probe remains unresolved.
- **Modules inspected:** `src/fx_ai_trading/` (services, adapters, domain, supervisor,
  labeling, strategies, meta layer), `scripts/` (fetch/archive, `compare_multipair_v3`–`v26`
  lineage, `train_lgbm_models.py`, `run_paper_decision_loop.py`, `run_live_loop.py`,
  `run_paper_evaluation.py`, stage22–29 harnesses, `gate_p1_pr_b`, `foundation_t2`,
  `ml_uplift_harness`), `tests/`, `tools/lint/`.
- **Docs/artifacts inspected:** `docs/design/` (roadmaps, closure memos, contracts,
  audits), `docs/runbook/`, the 92 committed files under `artifacts/`
  (gate_p1_pr_b, foundation_t2, oanda_archive_2026-05-31, stage22–29 eval reports,
  12 phase9 logs), `.gitignore` policy.
- **Tests/lint run (at audit time, master `87f1c56`):** `ruff check .` clean;
  `ruff format --check .` clean (579 files); `python tools/lint/run_custom_checks.py`
  clean; full `pytest`: **3977 passed, 3 failed, 5 skipped** — the 3 failures are the
  known pre-existing local-data failures (`test_exit_flow`, `test_replay_reproducibility`,
  `test_stage25_0d_deployment_audit`); the skips are the expected dirty-worktree launcher
  pre-flights and the console-dependent CTRL_BREAK test. CI on master is green.
- **Not run and why:** real-data backtests, model training, label/feature generation over
  real data, broker/network access — all prohibited for a read-only audit and not needed
  for its conclusions.

## 3. Blocker findings

### F-1 — BLOCKER — live-mode entry path crash; live spread/EV gate has never executed

- `scripts/run_paper_decision_loop.py:1668` reads
  `ev = meta_result.adopted_ev_after_cost or 0.0`, but `MetaCycleRunResult`
  (`src/fx_ai_trading/services/meta_cycle_runner.py:101-122`) has **no field
  `adopted_ev_after_cost`** — repo-wide search finds no definition, only this usage.
- In live mode the first adopted trade raises `AttributeError`; the enclosing `try`
  catches only `KeyboardInterrupt`, so the runner dies — potentially **after** the exit
  gate has been running, i.e. it can die with open positions left unmanaged.
- Consequence: the live "spread eats EV" gate has never actually executed in live mode.
- **Required before any live/paper evidence run.** Fix direction: add the field
  (populated from the adopted candidate's `ev_after_cost`) plus a test driving the
  live-quote branch. Not fixed in this memo.

### F-2 — BLOCKER (evidence validity) — historical backtest PnL layer is optimistically biased

- Under the B-2 tri-directional label semantics
  (`compare_multipair_v5_bidask.py:353-366`, byte-identical in v9/v13/v14/v19/v22–v26),
  label 0 includes paths where the **traded direction's SL fired** but the opposite TP
  did not (every adverse move in `[sl_mult, tp_mult)·ATR`). The eval layer maps traded
  label-0 rows to **0.0 pips** (`v5:707-716`; `compare_multipair_v9_orthogonal.py:794-804`)
  — real stop-loss outcomes scored as zero.
- Genuine **timeout exits are booked at zero cost** — no horizon mark-to-market and no
  spread (default `--slippage-pip 0.0`) — whereas the earlier v3 script explicitly
  charged them; the v4→v5 "decisive B-2 improvement" (Phase 9.12) therefore partly
  reflects a cost-accounting change, not only better labels.
- This affects **all Phase 9.10–9.X headline PnL/Sharpe/DD numbers, including the
  Phase 9.16 v9 20p operational baseline** (Sharpe 0.160 / PnL 8,157p). The magnitude of
  the bias has not been quantified (doing so would require a real-data rerun, which was
  not performed).
- The stage22+ new-epoch label stack already fixes both defects (per-direction outcome
  replay; horizon mark-to-market) — the fix was never backported to the v-script lineage.
- **Required before any real ML run or new verdict.**

## 4. High-risk findings

### F-3 — live containment issues

- **Account-type invariant is a tautology:** brokers call
  `_verify_account_type_or_raise(self._account_type)` — comparing the field to itself
  (`src/fx_ai_trading/domain/broker.py:145-156`, `adapters/broker/oanda.py:95` and
  `:136`, `adapters/broker/paper.py:142`); the AccountTypeMismatch SafeStop path is
  unreachable as wired.
- **Live env confirmation gap:** `scripts/run_live_loop.py` accepts
  `OANDA_ENVIRONMENT=live` with no confirmation flag and no cross-check against
  `account_type="demo"` (`:56, :254, :327-344`); with a live token it would send real
  orders. (Contrast: `run_volume_mode.py` enforces `--confirm-live-trading`;
  `run_paper_decision_loop.py:1024` pins `environment="practice"`.)
- **Leverage cap omits JPY conversion** for non-JPY-quoted pairs
  (`run_paper_decision_loop.py:944-960`): JPY balance divided by a USD-quoted price —
  for ¥300k at 25× this permits roughly 1,800× effective leverage on EUR_USD, so the
  regulatory backstop is broken exactly when the risk-% sizer misbehaves.

### F-4 — `force_fallback=True` unconditional adoption

- `src/fx_ai_trading/services/meta_cycle_runner.py:93, 246-251`: when every candidate
  fails the EV/confidence filters, the top candidate is adopted anyway (Cycle 6.4
  "≥1 trade per cycle" paper-smoke guarantee), and the production runner uses the
  default. Combined with F-1, production adoption is effectively unconditional whenever
  a signal exists; the research SELECTOR never traded this way.

### F-5 — data provenance holes (ingestion layer)

- **Fetch truncation exits 0:** `scripts/fetch_oanda_candles.py:198-270` — a mid-stream
  request failure prints to stderr, breaks, and returns success; a truncated file is
  shape-identical to a complete one.
- **In-place overwrite of SHA-inventoried spans:** `scripts/retrain_production_models.py:80`
  re-fetches over the exact `candles_*_M1_*d_BA.jsonl` filenames inventoried by Gate P1
  PR-B.1 and referenced (copied, not recomputed) by the T2 manifest — one run silently
  re-points span identity at different bytes while committed SHA evidence refers to the
  old bytes.
- **Archive resume treats any non-empty file as complete:**
  `scripts/fetch_oanda_archive.py:156-159` — truncations are never repaired on resume.
- **Model manifest lacks data SHA/time bounds:** `scripts/train_lgbm_models.py:536-546`
  — a trained model cannot be traced to the bytes it was trained on.

### F-6 — reused-OOS multiplicity; v26 selection-window overlap

- No validation split distinct from OOS exists anywhere in the v-script lineage
  (`_generate_folds`, e.g. `compare_multipair_v14_topk.py:585-617`); across Phases
  9.10→9.X-O, **≥ ~150 configuration cells** (counted from committed design memos) were
  scored on the **same ~39-fold weekly OOS grid** with the best cell adopted each phase.
  The surviving anchor (~0.158–0.160) is the argmax of that search — an optimistic upper
  bound; the true out-of-sample expectation is unknown.
- `compare_multipair_v26_dynamic_sltp.py:2420-2423`: the Stage-1 per-pair (tp, sl)
  selection window is sliced by **row count** (129,600 M1 rows ≈ ~126 calendar days of
  FX trading time) against a 90-calendar-day fold boundary — the "out-of-sample" comment
  is false; selection overlaps roughly the first 5 weeks of test folds whenever
  `--enable-dynamic-sltp` is on.

### F-7 — metric definition issues

- **Per-trade Sharpe:** `compare_multipair_v9_orthogonal.py:885-890` — per-trade pip
  mean/std (ddof=0), never time-aggregated or annualized; not comparable across variants
  with different trade rates (this alone explains the recurring "PnL up, Sharpe down"
  pattern across four phases).
- **Overlapping trades:** every labeled bar is an independent eval "trade" with a
  20-bar horizon → up to K×20 concurrent open positions; Sharpe is computed over
  serially correlated overlapping outcomes with no uniqueness/HAC correction; capital
  needs are understated; historical trade counts (~80/day) are execution-infeasible at
  retail.
- **DD%PnL:** max drawdown on the cumulative fixed-stake pip curve divided by whole-run
  total PnL (`v9:893-905, 929-934`) — shrinks mechanically with run length; not an
  equity drawdown percentage.
- **$1/pip translation:** monthly-% claims assume a fixed $10k account and $1/pip for
  all 20 pairs (`docs/design/phase9_12_closure_memo.md:116-123`) — wrong for JPY
  crosses; non-compounding.

### F-8 — train/serve consistency issues

- **Trainer TP-first vs backtest SL-first:** `scripts/train_lgbm_models.py:209-214`
  resolves same-bar TP+SL both-touch optimistically (`<=`) while every backtest uses
  strict `<` (SL-first) — deployed models are trained on labels that differ from the
  labels that validated the strategy; trainer ATR uses `min_periods=1` degenerate early
  widths the backtests never see.
- **Live barrier anchors:** live TP/SL anchor at the decision-bar **mid close**
  (`run_paper_decision_loop.py:1786-1792`) while the training label anchors at next-bar
  ask/bid open — per-trade barrier skew.
- **Live feature staleness:** the live loop passes `as_of_time = bar.time_utc` (bar
  OPEN timestamp) into a strict `<` filter (`run_paper_decision_loop.py:1600-1604`,
  `feature_service.py:127`), excluding the just-completed decision bar — production
  features are one full bar staler than every backtest.
- **MTF fallback mismatch:** `feature_service.py:496-531` (resample fallback) uses the
  in-progress higher-TF bucket while training uses shift(1) completed buckets — causal,
  but a different feature definition at serve time.
- **Raw uncalibrated thresholds:** production thresholds (0.40 in `lgbm_strategy.py:31`,
  0.50 in backtests) apply to raw `predict_proba`; isotonic calibration and
  `class_weight="balanced"` exist in stage25–27 research but were never ported to the
  production trainer.
- **EV unit/cost inconsistencies:** `ev_after_cost` is literally `ev_before_cost` for
  LGBM (pips) and `tp·confidence·0.5` in **price units** with no SL term for MR/BO —
  incommensurable units in the same meta argmax; **no live code path ever subtracts a
  cost from EV** (spread is used only as a tie-break, never subtracted).

### F-9 — working-tree evidence clobbering (six stage24/stage25 artifact files)

- At audit time (and still at this memo's creation) the working tree holds
  **uncommitted in-place modifications** of six committed verdict-evidence files:
  `artifacts/stage24_0b/eval_report.md`, `stage24_0c/eval_report.md`,
  `stage24_0d/eval_report.md`, `stage25_0a/dataset_summary.md`,
  `stage25_0b/eval_report.md`, `stage25_0c/eval_report.md` — a 2026-07-02 rerun on a
  shrunken universe (3 pairs / 3 cells vs the committed 20 pairs / 33 cells) with
  different numerics, leaving internally self-contradictory text.
- Committing them would retroactively modify prior verdict artifacts (the Class-A
  universal blocker per `phase27_29_tabular_eval_validity_audit.md`); a dirty tracked
  worktree is also an explicit T2 stop condition. The universe shrink independently
  corroborates that the pre-downgrade dataset is `HALTED_INPUT_UNAVAILABLE`.
- **These files must be restored or isolated before any evidence-bearing commit.**
  Note: restoring discards the uncommitted 2026-07-02 rerun outputs; isolating preserves
  them at a non-authoritative path — the choice is a separate user decision, not made by
  this memo. This memo's PR does not touch them (they remain dirty in the working tree;
  committing this memo stages only this document).

### F-10 — invalidated lookahead code/doc remnants

- The v16/v18 non-causal MTF code (resample-reindex-ffill **without** shift(1) — the
  confirmed ~14h lookahead) remains in-tree, unmarked and runnable
  (`compare_multipair_v16_features.py:642-659`).
- `src/fx_ai_trading/services/feature_service.py:24-25` still cites the **falsified**
  "Sharpe 0.174" figure (reclassified `INVALID_LOOKAHEAD_NUMERIC`) as justification for
  the mtf group.
- No test enforces the causal-MTF property (existing MTF tests cover determinism and the
  `as_of_time` filter — never the bug that actually happened).
- Two unbannered legacy docs present demoted numerics as production-current:
  `docs/design/sharpe_improvement_brief.md` and `docs/design/phase9_x_e_live_deploy_plan.md`
  (a DRAFT live-deploy GO matrix keyed to the invalid 0.174 anchor).

### F-11 — dataset fallback / mid-price fill risks

- **Silent BA→mid fallback:** `_pick_file` in ~20 compare scripts
  (`compare_multipair_v19_causal.py:225-232`) falls back per-pair to the mid-only
  dataset; v3/v4 fully accept it, so one run can mix bid/ask-labeled and mid-labeled
  pairs.
- **Mid fills in the flagship runner:** `run_paper_decision_loop.py:1545-1577` discards
  `bid_close`/`ask_close` and fills at mid via a bare callable — which also renders the
  M-3c stale-quote gate structurally inert (`age_seconds == 0` always) and makes paper
  PnL spread-free on both legs despite `FixedPipSpreadModel` existing unused.
- `CandleReplayQuoteFeed` serves data on instrument mismatch with only a warning
  (`candle_replay_quote_feed.py:101-110`).

### F-12 — claimed-but-unwired safety filters

- `MetaDeciderService` (Rule F1 calendar-stale, F3 near-event, F4 anomaly, F5 CSI,
  regime weighting) is imported **only by tests**; its currency/instrument resolution is
  a placeholder. The production meta stage (`run_meta_cycle`) has no event logic.
- `news_pause` / `session_close` exit rules can never fire — no caller sets the context
  flags; neither live runner has weekend logic.
- Correlation and currency-exposure caps (C2/C3/C4 in `risk_manager.py:122-162`) have
  zero production callers. Concurrency IS enforced (G2 max open positions, G1 duplicate
  instrument).
- The daily drawdown brake is fail-open on DB error and blind to unrealized losses; the
  G3 cooloff is hardcoded off (`recent_failure_count=0`).
- Live close uses an opposite-side `place_order` (wrong on hedging-mode practice
  accounts — would double exposure) although `OandaBroker.close_position` exists; the
  flagship runner bypasses the Supervisor SafeStop seam and keeps opening positions when
  the exit gate throws.

### F-13 — provenance gaps in results

- For every Phase 25–29 β-eval, machine-readable run outputs are gitignored by design;
  the committed prose reports carry **no code SHA and no config hash** (the project's own
  "Class U": statically consistent, run unprovable).
- The production baseline numeric (0.160 / +20.1%) has **zero committed run artifacts**,
  and its input span is `HALTED_INPUT_UNAVAILABLE` — honestly disclosed in the §11B
  baseline audit, but it means the strongest-labeled numeric in the repo is
  unreproducible.
- 25 older committed logs leak `C:\Users\<user>\...` local paths/username (no secrets,
  tokens, signed URLs, or raw candle rows anywhere in committed files).
- The shipped Gate P1 artifact layout deviates from the plan's 7-artifact schema
  (5+2 artifacts; `pr_a_spec_version` / `execution_envelope.json` absent) — needs a short
  reconciliation amendment; statuses themselves are consistent.

## 5. Result classification impact

- **Phase 9.16 v9 20p remains Tier 2 `VALID_OPERATIONAL_BASELINE` strictly as a fenced
  comparator** (i.e., the roadmap's production-default comparator baseline under the
  contemporaneous contract; admissible as baseline reference only, not as Tier-1
  evidence — see `research_development_roadmap_post_audit.md` Appendix A.5).
  It is **not promoted**. It is **not demoted by this memo.** It now
  carries explicit caveats that must accompany any future citation:
  - F-2 PnL-layer bias (label-0 SL masking; zero-cost timeouts),
  - F-6 reused-OOS multiplicity (argmax of a ~150-cell search on one OOS grid),
  - F-7 metric-definition caveats (per-trade Sharpe; overlapping trades; DD%PnL;
    $1/pip translation),
  - F-13 provenance limitations (no committed run artifacts; input span
    `HALTED_INPUT_UNAVAILABLE`).
- **+mtf v18 0.174 remains `INVALID_LOOKAHEAD_NUMERIC`.**
- **+mtf v19 0.158 / Top-K 0.165 / C-3 0.177 remain
  `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`.**
- **ML uplift Steps 1/2/3 remain synthetic-only** (verified by inspection: no
  data-loading code path exists in the harness; fail-closed flags; trading-metric keys
  blocked from reports).
- **Gate P1 PR-B.1/B.2 remain metadata/static evidence only**
  (`LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` per span;
  `GATE_P1_READONLY_SURFACE_STATICALLY_OBSERVED_RETENTION_PROBE_REQUIRED`).
- **T2 retention remains unresolved** (`RETENTION_PROBE_REMAINS_UNRESOLVED`) unless an
  actual deposit/restore/round-trip is later completed and separately verified; the
  merged PR #387 content is harness + pre-deposit stop evidence only.
- **No byte-admissibility approval. No new-epoch adoption. No ML Step 4. No production
  readiness** (see §1 forbidden-label warning).

## 6. Unsupported claims

The following must NOT be used as current decision evidence; each is unsupported at the
audited state:

- **Profitability** and **expected value** — all net-positive claims rest on the F-2
  PnL layer, F-6 multiplicity, F-7 metric definitions, and an unavailable input dataset.
- **Pair ranking quality** — measured under the same tainted PnL layer, plus a
  backtest-vs-production selection-rule mismatch (confidence vs ev_after_cost×confidence).
- **Production readiness** — never claimed; remains unsupported.
- **Live containment** — rests on a tautological account-type check (F-3).
- **Event/news filtering** — claimed in docstrings/design, not wired (F-12).
- **Correlation limits** — code exists, zero production callers (F-12).
- **Retention verification** — the retention probe remains unresolved.
- **Byte-admissibility** — not approved.
- **New epoch readiness** — not constructed, not adopted.
- **Model improvement** — no valid current evidence of uplift over the fenced baseline.

## 7. P0 remediation plan (must happen before any real ML run)

- **P0-1 — Evidence hygiene:** restore or isolate the six clobbered stage24/stage25
  artifact files (F-9). Must happen before any evidence-bearing commit. Evidence-only;
  no real data.
- **P0-2 — F-1 crash fix:** add `adopted_ev_after_cost` (or equivalent) to the meta
  result contract and fix `run_paper_decision_loop.py:1668`; add a test driving the
  live-quote branch. Implementation + test; no real data.
- **P0-3 — Backtest PnL-layer correction:** traded-direction barrier replay for label-0
  rows; horizon mark-to-market + spread for timeout exits (backport the stage22+
  treatment). Implementation; **no real-data rerun in that PR** — the eventual
  re-validation run is a separate, separately-authorised step.
- **P0-4 — Ingestion provenance hardening:** fail non-zero on truncation; prevent
  in-place overwrite of inventoried spans; SHA recompute/compare at training time; data
  SHA/time bounds in the model manifest (F-5). Implementation + tests; no real data
  required to write the code.
- **P0-5 — Label contract unification:** trainer tie-break aligned with backtest
  (SL-first strict `<`); ATR `min_periods=14`; live barrier anchor computed from the
  actual fill price (F-8). Implementation + tests; no real data.
- **P0-6 — Pre-register the next real experiment:** frozen never-touched holdout on the
  provenance-bound new epoch; a single pre-registered champion config;
  multiplicity-aware acceptance criteria; portfolio-level daily Sharpe and equity-DD
  metric definitions. Doc-only contract first; **execution requires the
  T2 → byte-admissibility → new-epoch path to complete beforehand.**

## 8. P1/P2/P3 remediation plan

- **P1 (before broader OOS experiments; none require real data):**
  leakage/label-contract regression test suite (test-only); MTF fallback
  completed-bucket fix; live `as_of_time` bar-close fix; calibration + class weights in
  the production trainer; a single post-cost EV contract across strategies;
  `force_fallback=False` in production paths; BA→mid hard-fail + bid/ask-aware paper
  fills + a real QuoteFeed into the flagship runner; fail-closed daily-DD brake;
  `close_position` close semantics; account-type/env containment fixes (F-3).
- **P2 (cleanup/clarity; doc/test-only):** supersession/void banners on
  `sharpe_improvement_brief.md`, `phase9_x_e_live_deploy_plan.md`, legacy
  `phase9_roadmap.md`; correct the `feature_service.py` 0.174 docstring; lookahead
  warning on `compare_multipair_v16_features.py`; Gate P1 artifact-schema reconciliation
  amendment; document bar-bucketing conventions and same-bar tie-breaks; mark
  `MetaDeciderService` / exit-policy filters as unwired; span-vocabulary unification
  (`365d` vs `365d_BA`).
- **P3 (optional):** ffill limits in cross-pair alignment; raise on replay instrument
  mismatch; EWMA adjust-mode alignment; hit-rate tie treatment; enforce the declared
  ml_uplift `FORBIDDEN_PATH_SEGMENTS` blacklist; scrub legacy committed logs' local
  paths.

## 9. Safe next steps (in order; none started by this PR)

1. Merge this doc-only audit memo.
2. Evidence hygiene PR: restore or isolate the six clobbered stage24/stage25 artifact
   files (P0-1).
3. Test-only leakage/label/backtest invariant suite (P1 lead item).
4. Small implementation PR for the F-1 live-entry crash (P0-2).
5. Backtest PnL-layer correction PR (P0-3; no real-data rerun in the PR).
6. Ingestion provenance hardening PR (P0-4).
7. Label contract unification PR (P0-5).
8. Only after those: design (doc-only) the first real ML Step 4 run (P0-6).
9. Any real run still requires the T2 / byte-admissibility / new-epoch path, each with
   its own explicit authorisation.

## 10. Non-authorisation confirmations

By the audit and by this memo's PR:

- no code changed
- no tests changed
- no artifacts changed
- no data changed
- no T2 execution
- no credentials / env-var values / cloud / network access
- no upload / deposit / download / restore
- no byte-admissibility approval
- no new-epoch adoption
- no ML Step 4
- no real model experiment
- no production change
- no LLM integration
