# Fable 5 source audit — PR #417 real-run body (fixture-only)

- **Document class:** doc-only adversarial source audit of the PR #417
  run-body implementation. Not a code PR; not an execution PR; changes no code.
- **Branch:** `docs/fable5-real-run-body-source-audit`
- **Base:** master `b22fd9f` (post PR #417 merge)
- **Audited against:** PR #413 falsification/baseline frame; PR #416 source-audit
  checklist (6 required-in-body items); PR #407/#408 contracts; the committed
  trainer convention (`scripts/train_lgbm_models.py`); the PR #417 diff.
- **Method:** source inspection of all 16 `scripts/ml_step4/` modules + all 13
  test modules (194 tests), PLUS an executed adversarial probe battery on merged
  master: refusal probes (3 mode strings, refused provider, spoofed-attribute
  provider); a **value-pinned cost-flow probe through the real body helpers**;
  a line-by-line ATR-convention comparison and label-range comparison against
  the committed trainer; hidden-route greps; production-seam invocation check;
  cross-process determinism (2 fresh interpreters). Probes used synthetic
  inline values only.

## Audit status

**`ML_STEP4_REAL_RUN_BODY_BLOCKED_FOR_FIRST_RUN_EXECUTION_REVIEW`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## 1. Executive verdict

The PR #417 body is **safe and fail-closed with respect to real data and real
execution** — every real-mode/provider/env route refuses, no hidden route
exists, evidence cannot reach protected paths, and the PR #413 frame is
preserved. However, the adversarial pass found **two metric/contract-correctness
blockers, both proven**, that MUST be fixed in a small code-only PR before any
first-run execution:

- **B-1 (proven by execution): the cost cell is applied TWICE in the holdout
  metrics path.** `_predictions_to_signals` subtracts the 0.5-pip cell from
  each trade's PnL, and `metrics.compute_all` subtracts it again — a raw
  +2.0-pip trade is reported as expectancy **1.0** at the "0.5 cell" (correct:
  1.5). Consequences: the primary "0.5-pip" metrics are actually 1.0-pip
  metrics; **every cost-sensitivity cell is shifted +0.5** (labelled
  0.0/0.5/1.0, actually 0.5/1.0/1.5); and the validation path (single charge:
  cell in signals, 0.0 in the daily series) is **inconsistent with the holdout
  path** (double charge) — corrupting threshold-selection-vs-holdout
  comparability. Carried into a real run this produces wrong (pessimistically
  biased and mislabelled) decision metrics.
- **B-2 (proven by source comparison): label-eligibility range drift in the
  single production label route.** The committed trainer and v9 labeller
  iterate `for i in range(n - horizon - 1)` (last labeled decision bar
  `n - horizon - 2`); `labels.bulk_labels` labels through `n - horizon - 1` —
  one extra trailing decision bar per segment. Magnitude is tiny, but
  `bulk_labels` is the R-4 single source for the real run, and a silent
  eligibility deviation from the committed convention is exactly the class of
  drift the F-8/label-contract discipline exists to prevent.

Everything else audited clean, including an important adversarial **clearance**:
`labels.atr14` was compared line-by-line against the trainer's committed ATR
(TR from mid H/L/prev-close with TR₀ = H−L; `rolling(14, min_periods=14).mean()`)
and **matches exactly** — the fixture and future real label geometry share the
pinned ATR flavor. There are no author-and-run risks (real mode has no body to
run without a further PR).

## 2. Audit scope

All `scripts/ml_step4/` modules (`body`, `data_adapter`, `features`, `trainer`,
`manifest`, `labels`, `split`, `metrics`, `evidence`, `thresholds`,
`acceptance`, `contract`, `executor`, `execute_365d_ba`, `inventory`,
`run_365d_ba`, `simulator`), all `tests/ml_step4/` modules, the implementation
note, the PR #417 diff, and the committed trainer as the convention authority.

## 3. Real-mode refusal audit — **REFUSED EVERYWHERE**

Executed: `mode="real"`, `mode="REAL"`, `mode=""` all raise
`ExecutionRefusedError`; `RealDataProviderRefused` under `mode="fixture"`
refuses; env vars (`ML_STEP4_REAL`, `ML_STEP4_DATA_DIR`,
`ALLOW_REAL_EXECUTION`) cannot enable anything (test-pinned); CLI `--execute`
and no-flag exit 2; `--preflight`/`--fixture-e2e` are the only rc-0 paths.
`RealDataProviderRefused` raises on **every** data access (`pairs`,
`bars_for`). No hidden flag/import/default/env route exists (§16). Status
names (`…_NO_RUN`, `…_FIXTURE_REHEARSAL_…`) cannot be mistaken for execution.
**Inherent limit (not a code defect):** the provider guard checks duck-typed
attributes, so a hypothetical provider *written with* fixture attributes but
reading real files would be accepted — writing such a provider IS authoring a
real-data provider, which the PR-review gate governs; a spoofed-attrs probe
without bars dies at the `n_bars` assertion. First-run binding: the execution
PR must record the **provider class identity + checksum-verification linkage**
in evidence so a wrong provider is provably visible (§18).

## 4. Raw data access audit — **NONE**

No real `365d_BA` file is opened anywhere; no checksum-verified real provider
exists (by design); file-IO in the package remains exactly: evidence writes
(guarded), inventory metadata JSON read, and `file_sha256_and_size` (unreached
by the body/preflight). No pandas/csv/parquet reader in any body module; the
fixture provider is in-memory, seeded, and file-free; no env var redirects
anything. Tests and CLI use synthetic/temporary data only (test-pinned).

## 5. Feature-generation audit — **SOUND, honestly labeled**

Fixture features are strictly causal (row *i* uses bars ≤ *i*; proven by the
truncation-invariance test) and deterministic; they are explicitly labeled NOT
production v4 (`fixture_builder_is_production_v4: False` in `feature_binding`,
plus the module docstring). The production seam
(`load_production_feature_builder`) is identity-bound to the committed trainer
builders (`_add_features` + `_add_upper_tf_features` / `_FEATURE_COLS`) and is
**never invoked** in this build (grep-verified: definition only). Feature
config stays v4 base only, opt-in groups excluded, contract hash recorded. No
lookahead found in either path. No false completeness claim — the
implementation note states the production wiring is absent.

## 6. Label and trade-scoring audit — **single-source; ONE drift (B-2)**

All label generation and ALL trade scoring/PnL/exit timing route through
`labels.py` (`bulk_labels` reuses the reviewed primitives and the committed
F-2 helper; `exit_window_offset` keeps SL-first exit timing in the adapter);
the monkeypatch adapter-failure test proves no catch-and-continue; the source
test proves no barrier/PnL math in `body.py`; no legacy fallback exists;
horizon 20 recorded; SL-first tie and timeout MTM preserved (probe-verified in
prior audits); `LABEL_CONTRACT_ID` recorded in the leakage/provenance payload.
**B-2:** eligibility-range drift vs the committed `range(n - horizon - 1)`
(§1) — must be aligned (skip when `i + horizon + 1 >= n`) or explicitly
pre-registered as a deviation, with a range-pinning test against the trainer
convention.

## 7. Trainer audit — **CLEAN**

`train_lgbm` builds params as exactly `{**contract.LGBM_PARAMS,
"n_estimators": contract.LGBM_N_ESTIMATORS}` — the PR #407/#412 convention;
no `model_path` argument exists (deployed reuse structurally impossible); no
persistence path (no joblib/pickle anywhere — grep-verified); trains only what
it is given, and nothing in this build gives it real data. The CI stub is
clearly separated (`fixture_stub_synthetic_only`, `synthetic_only=True`); the
optional heavy test is env-gated, uses 90 inline synthetic rows, and passed
when run explicitly. `model_config_hash` unchanged (`bc27cf…`).

## 8. Prediction and threshold audit — **CLEAN**

Candidates exactly `{0.35, 0.40, 0.45}`; the full-sweep requirement is
enforced by `select_threshold` (PR #412 B-2 fix — the body builds metrics for
all three); selection consumes validation-segment signals only, and the
holdout signals are constructed strictly AFTER selection with the selected
threshold (source-verified order); `select_threshold` still has no holdout
parameter (structural). Rejected variants recorded and carried into fixture
evidence (`per_threshold_validation_curves`, `holdout_inspected: false`); tie
rule matches `THRESHOLD_TIE_RULE`; the fixture prediction path is
deterministic (stub). One caveat folds into B-1: the validation selection
metric is computed on single-charged trades while the holdout metrics are
double-charged — fixed by the B-1 remedy.

## 9. Holdout evaluation audit — **structure CLEAN; numbers blocked by B-1**

Fixture holdout is built once per rehearsal, after selection, from the
selected threshold only; the future real holdout inherits the same guarded
order. Event-driven max-1-position-per-pair is real (simulator occupancy =
entry → resolved barrier/timeout exit from `labels.py`). Daily series
generation is deterministic. The metrics bundle prepares every §10 quantity
(expectancy, coverage, Sharpe, maxDD, turnover, concentration, 1.0-pip cell,
provenance flag) — but the **values are compromised by B-1** until fixed.
Fixture metrics are triple-bannered (`fixture_rehearsal/synthetic_only/
real_run=false`) and the acceptance output is a dry output in the closed
vocabulary. No real holdout evaluation occurs.

## 10. MaxDD and trading-day audit — **CLEAN**

`compute_all` defaults to `FIXED_NOTIONAL_EQUITY_PIPS = 10,000` and fails
closed on conflicting values (double-guarded in `body.evaluate_portfolio`);
missing/non-positive fails closed at preflight. UTC-date denominator used
(default rehearsal genuinely spans 2 dates); naive datetimes fail closed; no
local/broker timezone anywhere; manifest records the notional and both
day-rule strings.

## 11. Manifest / provenance audit — **CLEAN**

Real 40-char git SHA (subprocess `git rev-parse HEAD`, read-only, fail-closed
on any failure — test-pinned); Python version; package versions via
`importlib.metadata` for numpy/pandas/lightgbm/scikit-learn (names+versions
only — no env dump); actual seeds; `bounded_not_bitwise_guaranteed` (enforced
value); all four hashes; label contract identity; fixture-vs-real mode;
tie-rule/day-rule/notional. Completeness fail-closed
(`assert_manifest_complete`). Scrub-gated before write; no personal paths /
credentials / raw rows / Drive / R2 (leak-scan verified). No reproducibility
or execution overclaim.

## 12. Evidence assembly audit — **CLEAN**

Exactly eight payloads; each JSON payload scrub-asserted and fixture-bannered
(test-pinned per file); acceptance uses the closed vocabulary; writes go only
to caller-supplied non-protected paths — the repo-root guard refuses
`artifacts/ml_step4/365d_ba_v1/` (test-pinned; PR #409's 8 files verified
untouched before/after); no raw rows / personal paths / Drive / R2; diagnostics
labeled `NON_DECISION_EXPLORATORY` and separated from decision metrics; the
acceptance evaluator is structurally immune to exploratory keys (PR #416
proof still holds — unchanged module). The markdown decision report opens with
"FIXTURE REHEARSAL — synthetic only, non-decision".

## 13. CLI / API audit — **CLEAN**

`--preflight` exit 0; `--fixture-e2e` exit 0 with
`fixture_rehearsal_performed=true` and all real flags false; `--execute` and
no-flag exit 2; mutually-exclusive group prevents combined flags; stdout is
`assert_clean`-gated and path-free (test: no `Users`/drive-letter substrings);
no CLI default performs anything real.

## 14. Determinism audit — **CLEAN (one real bug already fixed in PR #417)**

Cross-process determinism re-verified on master (identical trades/threshold
across fresh interpreters). PR #417 itself caught and fixed a genuine
`hash()`-randomisation nondeterminism (PYTHONHASHSEED) by switching pair
mixing to SHA-256 — the fix is test-relevant and honest. Ordering is
deterministic (`provider.pairs` tuple; simulator sort key); seeds recorded;
LightGBM nondeterminism honestly bounded; seed policy does not alter
`model_config_hash` (test-pinned).

## 15. Synthetic fixture adequacy audit — **ADEQUATE, with B-1 lesson**

The default rehearsal covers: 2 pairs; 6,000 bars; long AND short signals
(stub emits both directions from signed returns); TP, SL, and timeout label
outcomes (random-walk barrier races produce all three); 2 UTC dates in the
holdout; all eight payloads; closed-vocabulary dry acceptance; stage-skip
detection (payload-count and flag assertions fail if a stage is skipped).
**Lesson from B-1:** the fixture was route-adequate but not *value-pinned* —
no test asserted an absolute expectancy against a hand-computed number through
the full body path, which is exactly where the double-charge hid. The fix PR
must add a **value-pinned end-to-end cost test** (known raw PnL in → exact
expectancy out at each cell).

## 16. Hidden route / security audit — **CLEAN**

Grep-verified across the new modules: no `os.environ`/`getenv`; no
`eval`/`exec`/`__import__`; no joblib/pickle; no `models/lgbm` load path (the
only mention is a prohibition docstring); the single `subprocess` use is the
documented read-only `git rev-parse` in `manifest.py` (fail-closed); no
absolute paths, symlink tricks, Drive/R2 references, or legacy backtest
imports; the production feature seam is defined but never invoked.

## 17. Test adequacy audit — **GOOD coverage; two required additions**

194 tests cover every checklist area (refusals, e2e, payloads, protected-dir,
adapter failure, integer boundaries, notional, UTC days, manifest, labeler,
validation-only selection, closed vocabulary, CLI). **Missed both blockers**,
which defines the additions required in the fix PR: (a) a value-pinned
end-to-end cost-flow test (catches B-1 and prevents regression); (b) a
label-eligibility-range test pinning `bulk_labels` against the committed
`range(n - horizon - 1)` convention (catches B-2). Recommended: also pin the
ATR equivalence with a small numeric cross-check against a hand-computed TR
series (currently verified only by this audit's inspection).

## 18. Remaining limitations and first-run prerequisites

**Absent (by design, to be implemented ONLY in the separately-authorised
first-run execution PR):**
1. **Real checksum-verified data provider** — must re-verify all 20 SHA-256 +
   sizes against the PR-B.1 inventory immediately before reading; must record
   the provider class identity AND the checksum-report linkage in evidence
   (anti-spoof binding from §3); must map real BA rows to the body bar schema.
2. **Production v4 bulk feature wiring** — invoke the identity-bound trainer
   builders (`_add_features` + `_add_upper_tf_features` / `_FEATURE_COLS`);
   record the feature-builder identity + column list in the manifest.
3. **Real-mode enablement** — a minimal, explicit switch in `guarded_run_body`
   gated on the execution authorisation; no other behavior change.

**Must NOT change in the first-run PR unless separately authorised:** epoch;
feature version (v4 base); model family + frozen hyperparameters; label
contract (incl. the B-2 geometry, SL-first, timeout MTM, ATR flavor);
threshold candidates + tie rule; split policy (integer indices, purge 21);
cost cells; §10 acceptance criteria; the eight-file evidence schema.

## 19. Blockers

| ID | Defect | Proof |
| --- | --- | --- |
| **B-1** | Cost cell applied twice in the holdout metrics path (signals net of cell → `compute_all` subtracts again); cost-sensitivity cells shifted +0.5; validation/holdout charging inconsistent | executed: raw +2.0 trade → expectancy 1.0 at "0.5 cell" (correct 1.5); 0.0-cell shows 1.5 (correct 2.0) |
| **B-2** | `bulk_labels` labels one extra trailing decision bar vs the committed trainer/v9 convention (`range(n - horizon - 1)`) — silent eligibility drift in the R-4 single production label route | source comparison: trainer line 213 vs `bulk_labels` skip condition |

**Required fixes (small code-only PR, no run):**
1. Apply the cost cell exactly once. Recommended shape: keep signal PnL RAW in
   `_predictions_to_signals` (drop `apply_cost_cell` there) so
   `MetricTrade.gross_pnl_pips` is genuinely gross and the metrics layer owns
   all cost application (validation daily series then uses the primary cell,
   not 0.0). Add the §17(a) value-pinned test.
2. Align `bulk_labels` eligibility to the committed convention (skip when
   `i + horizon + 1 >= n`), or pre-register the deviation explicitly; add the
   §17(b) range-pinning test.
3. (With the fix PR or the execution PR) bind provider identity + checksum
   linkage into evidence (§18 item 1).

## 20. Recommendation for next gate

**Fix PR #417's B-1/B-2 in a small code-only PR before any first-run
execution.** Sequence: merge this audit → code-only fix PR (+ the two
value/range-pinned tests) → short Fable 5 re-check of the two fixes → then the
separately-authorised **first-run execution PR** shaped as: minimal real-mode
enablement + checksum-verified `365d_BA` provider + production v4 bulk feature
wiring; **no contract changes; no threshold/feature/model search; execute
exactly once; metadata-only evidence; mandatory post-run human + ChatGPT review
(+ recommended Fable 5 adversarial post-run audit)** — all under the PR #413
falsification/baseline frame.

## 21. Non-authorisation statements

This audit did **not**: implement real-mode enablement; execute ML Step 4;
read real `365d_BA` raw data (probes used inline synthetic values); train on
real data; run a real backtest; evaluate the real holdout; generate real ML
metrics; create real execution evidence (guard probes refused; PR #409 dir
verified untouched); write model binaries; access external disks, Google
Drive, or R2; start Phase C2; touch `730d_BA`/`3650d_BA`; claim production
readiness.
