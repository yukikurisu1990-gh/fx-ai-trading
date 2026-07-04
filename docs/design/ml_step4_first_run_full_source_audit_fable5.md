# Fable 5 full first-run source-contamination & trading-logic source audit

- **Document class:** doc-only adversarial audit of **every source path that can
  affect the future ML Step 4 first-run number** — not limited to PR #417 or to
  `scripts/ml_step4/`. Changes no code; executes nothing.
- **Branch:** `docs/fable5-real-run-body-source-audit` (PR #418; this document
  supersedes-and-extends the narrower
  `ml_step4_real_run_body_source_audit_fable5.md`, which is retained as the
  body-level component containing the executed B-1/B-2 proofs).
- **Base:** master `b22fd9f` (post PR #417 merge).
- **Method:** repo-wide dependency-edge mapping (executed greps: all imports
  into/out of `ml_step4`; all writers of `artifacts/ml_step4`; all writers of
  candle data; all joblib/pickle/model routes); line-level inspection of every
  delegated helper (F-2 PnL helper; the trainer's `_add_features`,
  `_add_upper_tf_features`, `_FEATURE_COLS`, `_add_labels_bidask`, ATR);
  legacy-route classification across `scripts/`; plus the executed probe
  battery of the body-level audit (refusals, value-pinned cost flow, ATR and
  label-range comparisons, determinism, hidden routes).

## Audit status

**`ML_STEP4_FULL_SOURCE_AUDIT_BLOCKED_FOR_FIRST_RUN_EXECUTION_REVIEW`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## 1. Executive verdict

**The first-run source surface is structurally isolated and almost entirely
clean; two proven body-level defects (B-1, B-2) block first-run execution
until a small code-only fix PR lands. No new blockers were found by the
repo-wide sweep.** The decisive structural facts, all verified by executed
greps:

- `scripts/ml_step4/` imports exactly **two** things from outside the package:
  the committed F-2 PnL helper (`scripts/traded_direction_pnl.py`) and the
  Foundation T2 scrub constants — both previously audited. Nothing else in the
  repository imports `ml_step4`, and **nothing outside the package touches
  `artifacts/ml_step4/`**. The first-run number therefore flows through a
  closed, enumerable code path.
- First-run-critical logic that intentionally lives OUTSIDE `ml_step4`:
  (a) the F-2 helper (wrapped, identity-verified, audited); (b) the trainer's
  committed bulk feature builders, which the execution PR will invoke via the
  identity-bound seam — **inspected here and CLEARED for lookahead**
  (`_add_upper_tf_features` uses `shift(1)` completed-bucket alignment; an M1
  bar only ever sees the previous completed M5/M15/H1 bucket); (c) the
  committed PR-B.1 inventory JSON (metadata, not code).
- Legacy contamination: the ~25 `compare_multipair_v*` scripts (including the
  F-2-tainted optimistic eval layer and the F-10 lookahead v16/v18 MTF code),
  the stage22–29 harnesses, and the deployed-model machinery
  (`train_lgbm_models.py main()`, `retrain_production_models.py`,
  `models/lgbm/*.joblib`, `model_store.py`, `lgbm_strategy.py`) are **not
  imported, not reachable, and cannot write into the first-run's code or
  evidence path**. The only physical contamination vector — mutation of the
  `365d_BA` candle bytes by fetch/retrain scripts — is doubly neutralised:
  F-5 provenance guards are wired into every writer, and the mandatory
  pre-consumption checksum re-verification hard-stops the run on any byte
  change (`ML_STEP4_RUN_INVALID_CHECKSUM_MISMATCH`).
- Internal consistency of the decision path (labels ↔ scoring ↔ metrics ↔
  acceptance ↔ evidence) is sound EXCEPT the two proven defects: **B-1** (cost
  cell applied twice in the holdout metrics path — the "0.5-cell" metrics are
  actually 1.0-cell, sensitivity cells shifted +0.5, validation/holdout
  charging inconsistent) and **B-2** (`bulk_labels` labels one extra trailing
  decision bar vs the committed `range(n − horizon − 1)` convention). Both are
  first-run-critical and must be fixed code-only before execution.

## 2. Audit scope

**Scope A (new path):** all 17 `scripts/ml_step4/` modules + all 13
`tests/ml_step4/` modules (194 tests). **Scope B (delegated source):**
`scripts/traded_direction_pnl.py`; `scripts/train_lgbm_models.py` (feature
builders, `_FEATURE_COLS`, labeller, ATR, `_LGBM_PARAMS`/`_N_ESTIMATORS`);
`scripts/foundation_t2/constants.py`; `src/fx_ai_trading/services/
feature_service.py` (version authority); the committed PR-B.1 inventory.
**Scope C (legacy):** `compare_multipair_v3–v26`, stage22–29 harnesses,
`retrain_production_models.py`, `fetch_oanda_candles.py`/`_archive.py`,
`models/lgbm/`, `model_store.py`, `lgbm_strategy.py`, paper/live runners,
`ml_uplift_harness`, `gate_p1_pr_b`. Plus PR #413 framing and the PR #416
checklist.

## 3. First-run source dependency map

| Stage | Intended source | Delegated helper | In/out of `ml_step4` | State | Tests | Forbidden legacy | Failure mode if wrong |
| --- | --- | --- | --- | --- | --- | --- | --- |
| inventory/epoch/checksum | `inventory.py` | PR-B.1 JSON (metadata) | in (+ committed artifact) | implemented | yes (synthetic + metadata) | none | wrong bytes trained → invalid run (hard-stopped) |
| raw data provider | `data_adapter.py` (real: **absent**) | — | in | fixture-only; real refused | yes | any direct candle reader | uninventoried data → invalid |
| feature generation | `features.py` seam → trainer `_add_features` + `_add_upper_tf_features` / `_FEATURE_COLS` | **outside (trainer)** — inspected, causal | seam in; builders out | seam bound, not invoked | binding tests; **seam-invocation test missing** | FeatureService live path; v16/v18 MTF; opt-in groups | lookahead / wrong feature set |
| split/purge/embargo | `split.py` (integer `Fraction` boundaries) | — | in | implemented | yes (incl. divergent-n) | float recomputation | boundary leakage |
| label generation | `labels.bulk_labels` (single route) | F-2 helper (outside, audited) | wrapper in; helper out | implemented; **B-2 range drift** | yes; **range-pinning test missing** | v-script labellers; trainer labeller direct | label-set drift |
| training | `trainer.train_lgbm` | lightgbm (lazy) | in | implemented (stub in CI; real wrapper verified once) | yes | `train_lgbm_models` main/model-save; warm-start | contract drift |
| validation prediction | `body.py` | stub/LGBM `predict_proba` | in | implemented | yes | — | leakage |
| threshold selection | `thresholds.select_threshold` | — | in | implemented (full-sweep enforced) | yes | old per-phase argmax | multiplicity |
| holdout prediction | `body.py` (after selection only) | — | in | implemented | yes | — | holdout leakage |
| event-driven trade scoring | `simulator.py` + `labels` exits/PnL | F-2 helper | in | implemented; **B-1 double cost** | yes; **value-pinned test missing** | v-script eval layer (F-2 taint) | wrong PnL |
| daily aggregation | `metrics.daily_portfolio_pnl` + `trading_day_utc` | — | in | implemented | yes | per-trade Sharpe | wrong primary metric |
| metrics | `metrics.compute_all` (contract notional) | — | in | implemented; hit by B-1 | yes | DD%PnL, $1/pip | wrong decision values |
| acceptance | `acceptance.py` | — | in | implemented (fail-closed) | yes | any `PASS`-like label | wrong verdict |
| evidence payloads | `evidence.py` + `body.py` | scrub constants (outside, audited) | in | implemented (fixture) | yes | old artifact writers | leak / overwrite |
| manifest/provenance | `manifest.py` | git (read-only subprocess) | in | implemented | yes | — | unprovable run |
| CLI/API entry | `execute_365d_ba.py` / `executor.guarded_execute` | — | in | preflight+fixture only; real refused | yes | legacy runners | accidental execution |

## 4. Buy/sell decision source audit — **CLEAN**

The ONLY signal path is: 3-class `predict_proba` → confidence vs the
validation-selected threshold → argmax direction (`body._predictions_to_signals`).
Grep-verified: no rule-based fallback signal exists anywhere in the package;
the legacy Donchian/MR/breakout/session/pair-filter strategies live in
unimported `compare_multipair_*`/`src` strategy modules with zero routes into
`ml_step4`. Threshold selection is validation-only (no holdout parameter;
holdout signals built strictly after selection). One-position-per-pair is
enforced by the simulator with exits resolved from `labels.py`. Entry is
next-bar (`i+1` ask/bid open in the label geometry); features at bar *i* use
only bars ≤ *i* — no same-bar lookahead in either the fixture builder
(truncation-invariance test) or the production seam (shift(1) buckets).

## 5. Label / PnL / scoring source audit — **single route; B-1/B-2 carry over**

The F-2 corrected behavior is the only reachable route: traded-direction
replay via the committed helper (identity `is`-verified), bid/ask geometry,
SL-first tie, timeout MTM (probe-proven non-zero), no SL-as-zero and no
zero-cost-timeout fiction anywhere in the package. All label generation AND
all trade scoring/exit timing route through `labels.py`; no barrier/PnL math
exists in `body.py` (source test); no fallback exists. The old optimistic
eval layer (v5–v26 `compare_multipair` PnL mapping — audit finding F-2) is
**historical-only and unreachable** from the first-run path. **B-1** (double
cost application downstream of scoring) and **B-2** (one-bar eligibility
drift vs the committed `range(n − horizon − 1)`) remain the two blockers —
see the body-level audit document for the executed proofs and the required
fix shapes.

## 6. Feature source audit — **seam CLEARED; wiring still absent by design**

The first-run feature set is pinned to `FEATURE_VERSION v4` base only (frozen
contract descriptor + hash; opt-in groups excluded and fail-closed in
`contract.assert_feature_groups`). The production bulk builders the seam binds
to were inspected line-by-line: `_add_features` (EMA/MACD/RSI-Wilder/BB/SMA/
ATR-14 with `min_periods=14`, no prev-close fillna — the F8 warmup guard) and
`_add_upper_tf_features` — **causal**: upper-TF frames are resampled,
feature-computed, then `shift(1).reindex(ffill)`-aligned so each M1 row sees
only the previous COMPLETED bucket (the F-10 lookahead pattern is absent
here; the lookahead-prone code survives only in `compare_multipair_v16/v18`,
which are unreachable). `_FEATURE_COLS` is the authoritative column list and
must be recorded in the run manifest at execution. No old feature script can
silently substitute: nothing imports them into the path. The **wiring remains
an explicit first-run gap** (seam defined, never invoked) — correctly not
claimed as complete. Residual note (non-blocking, research-run scope): the
trainer's vectorised mirror vs `feature_service.py`'s live implementation is
an F-8 train/serve concern for any FUTURE serving, not for this
research-only first run.

## 7. Trainer / model source audit — **CLEAN**

`trainer.train_lgbm` is the only training route in the path: fresh
`LGBMClassifier(**{frozen params}, n_estimators=200)`; **no model_path
argument exists** (deployed reuse structurally impossible); no warm-start; no
search; no holdout training; no persistence (joblib/pickle absent from the
package — grep-verified). The stub is unmistakable
(`fixture_stub_synthetic_only`). The legacy model machinery
(`train_lgbm_models.py` `main()`/`_train`+joblib save,
`retrain_production_models.py`, `models/lgbm/*.joblib`, `model_store.py`,
`lgbm_strategy.py`) is classified **forbidden-for-first-run, unreachable from
the path**; the execution PR must import ONLY the three feature builders from
the trainer module and must not invoke its main/save paths (§14 guard note).
`model_config_hash` unchanged (`bc27cf…`).

## 8. Prediction / threshold source audit — **CLEAN**

Candidates exactly `{0.35, 0.40, 0.45}`; full sweep enforced fail-closed
(PR #412); validation-only; deterministic tie rule recorded in
config/threshold hashes; rejected variants recorded into evidence; holdout
built after selection; no old threshold selector (per-phase argmax lineage) is
importable into the path.

## 9. Split / purge / holdout source audit — **CLEAN**

Integer-`Fraction` bar-index boundaries `[start, end)`; purge = 21 =
horizon+1; emitted indices authoritative and consumed by the body;
M1-alignment and naive-timestamp inputs fail closed; holdout evaluated once,
after selection. No float recomputation anywhere in the path.

## 10. Backtest / holdout evaluation source audit — **structure CLEAN; B-1 blocks values**

Ask/bid entry-exit geometry, TP/SL/timeout behavior, and SL-first ordering all
come from the label contract (single source). Event-driven 1-position-per-pair
with barrier/timeout occupancy; deterministic daily aggregation via UTC dates;
turnover/maxDD (fixed 10,000-pip notional)/concentration/expectancy prepared
per §10. **B-1** makes the current cost-cell values wrong (double charge;
shifted sensitivity cells; validation/holdout inconsistency) — blocker until
fixed. The old per-trade-Sharpe / optimistic-backtest lineage cannot become
decision evidence: it is unreachable, and the acceptance evaluator only reads
its own fixed metric paths.

## 11. Metrics / acceptance source audit — **CLEAN (post-B-1-fix)**

Daily portfolio Sharpe primary (daily-series computation test-pinned); all
§10 criteria present; missing/None fail closed (PR #412 B-3); NaN falls
through to an honest DOES_NOT_MEET (conservative; finiteness check
recommended); diagnostics structurally cannot influence acceptance (executed
junk-injection proof); closed status vocabulary only; no legacy metric can
substitute (nothing imports one).

## 12. Evidence / manifest / provenance source audit — **CLEAN**

Eight metadata-only payloads; scrub-gated (raw rows, personal paths, env
dumps, credentials, Drive/R2 all rejected — test-pinned); fixture-bannered;
no binaries; manifest carries real code SHA (fail-closed), seeds, package
versions, all four hashes, label contract identity, split metadata, inventory
metadata, and execution flags; the repo-root guard refuses
`artifacts/ml_step4/365d_ba_v1/` (PR #409's 8 files verified untouched);
**nothing outside the package writes that directory** (repo-wide grep).

## 13. Hidden route / security audit — **CLEAN**

Repo-path-scoped greps: no env vars, no eval/exec/`__import__`, no
pickle/joblib in the package, the sole subprocess is the documented read-only
`git rev-parse` (fail-closed), no absolute paths, no Drive/R2 references, no
model-binary loads, no legacy backtest imports, no old artifact writers or raw
readers reachable. The `inventory_path` parameter can only redirect which
metadata JSON is parsed.

## 14. Legacy contamination classification

| Legacy source | Classification | Guard |
| --- | --- | --- |
| `scripts/traded_direction_pnl.py` | **required** (F-2 single source; audited) | must be used only via `labels.py` wrapper |
| trainer `_add_features`/`_add_upper_tf_features`/`_FEATURE_COLS` | **required via seam** (inspected, causal) | execution PR imports builders only |
| trainer `_add_labels_bidask` | historical-convention reference (range authority for B-2) | not called; `bulk_labels` is the route |
| trainer `main()` / joblib save; `retrain_production_models.py` | **forbidden for first-run** (writes `models/lgbm`; re-fetches inventoried spans) | unreachable from path; F-5 provenance guards wired; checksum hard gate detects any data mutation; process rule: do not run before first-run |
| `fetch_oanda_candles.py` / `_archive.py` | data-mutation vector | F-5 guards + checksum hard gate |
| `compare_multipair_v3–v26` (incl. F-2-tainted eval; F-10 v16/v18 MTF) | **historical-only / forbidden** | zero imports into path; cannot write `data/` or `artifacts/ml_step4`; numbers non-citable per roadmap tiers |
| stage22–29 harnesses | historical-only | unreachable |
| `models/lgbm/*.joblib`, `model_store.py`, `lgbm_strategy.py` | forbidden (deployed reuse) | no load path exists in `ml_step4` |
| paper/live runners (`run_paper_decision_loop`, `run_live_loop`) | not in path (serving-side) | unreachable |
| `ml_uplift_harness`, `gate_p1_pr_b` code | not in path (evidence infra) | n/a (PR-B.1 JSON is consumed as metadata) |
| `feature_service.py` | version authority only; live path not used in run 1 | mirror-drift noted as F-8 residual for future serving |

**Conclusion:** historical invalidated logic (optimistic PnL, timeout-zero,
SL-as-zero, per-trade Sharpe, argmax-of-many, MTF lookahead, deployed reuse)
**cannot affect the first-run** through any code route; the only physical
vector (candle-byte mutation) is provenance-guarded and hard-stopped by the
pre-consumption checksum gate.

## 15. Test adequacy audit

Existing 194 tests cover the path well (see §17 of the body-level audit).
**Mandatory additions before/with first-run:**
1. value-pinned end-to-end cost test (catches B-1; fix PR);
2. `bulk_labels` eligibility-range test vs `range(n − horizon − 1)` (B-2; fix PR);
3. numeric ATR cross-check vs a hand-computed TR series (fix PR, recommended);
4. production-seam invocation test on synthetic production-shaped bars
   (execution PR — proves `_add_features`/`_add_upper_tf_features` wiring and
   no-lookahead on a truncation probe);
5. checksum-verified real provider test with a tampered-fixture negative case
   (execution PR);
6. legacy-route non-use assertion (import-graph test: `ml_step4` imports only
   the two sanctioned externals) — cheap, fix PR;
7. NaN/infinity metric finiteness test (fix PR, recommended);
8. deployed-model-reuse refusal already covered; real-evidence-path guard
   already covered.

## 16. Remaining first-run implementation gaps

| Gap | Where |
| --- | --- |
| **Fix B-1** (single cost application; raw signal PnL; metrics own all cells) | **prior code-only fix PR** |
| **Fix B-2** (align label range or pre-register deviation) | **prior code-only fix PR** |
| tests §15(1–3, 6, 7) | fix PR |
| checksum-verified real `365d_BA` provider (+ schema mapping + provider-identity/checksum linkage in evidence) | first-run execution PR |
| production v4 bulk feature wiring (+ §15(4) seam test + `_FEATURE_COLS` in manifest) | first-run execution PR |
| real-mode enablement (minimal switch) + real evidence write | first-run execution PR |

## 17. Blockers

**B-1** and **B-2** (proven; carried from the body-level audit — full detail
and proofs in `ml_step4_real_run_body_source_audit_fable5.md` §19). No
additional blockers from the repo-wide sweep.

## 18. Recommendation for next gate

**Acceptable only after specific code-only fixes.** Sequence: merge this audit
→ **code-only fix PR** (B-1 + B-2 + tests §15(1–3, 6, 7)) → short Fable 5
re-check of the fixes → then the separately-authorised **first-run execution
PR** with exactly this allowed shape: minimal real-mode enablement;
checksum-verified `365d_BA` provider; production v4 bulk feature wiring
(builders only — never the trainer main/save paths); **no contract changes; no
threshold/feature/model search; no acceptance-criteria changes; execute
exactly once; metadata-only evidence; mandatory post-run human + ChatGPT
review (+ recommended Fable 5 adversarial post-run audit)** — under the PR
#413 falsification/baseline frame.

## 19. Non-authorisation statements

This audit did **not**: implement code or real-mode enablement; execute ML
Step 4; read real `365d_BA` raw data (all probes used inline synthetic values
and committed metadata); train on real data; run a real backtest; evaluate the
real holdout; generate real ML metrics; create real execution evidence; write
model binaries; access external disks, Google Drive, or R2; start Phase C2;
touch `730d_BA`/`3650d_BA`; claim production readiness.
