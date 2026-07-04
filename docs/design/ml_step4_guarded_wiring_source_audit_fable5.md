# Fable 5 guarded wiring source audit — PR #415 executor orchestration

- **Document class:** doc-only adversarial source audit of the PR #415 guarded
  `execute()` wiring layer. Not a real-run-body implementation; not an
  execution PR; changes no code.
- **Branch:** `docs/fable5-guarded-wiring-source-audit`
- **Base:** master `6df9d70` (post PR #415 merge)
- **Audited against:** PR #413 research framing (falsification/baseline frame),
  PR #414 re-check (expected residual closure), PR #415 wiring note, and the
  PR #407/#408 contracts.
- **Method:** source inspection of every `scripts/ml_step4/` module + tests,
  PLUS an executed adversarial probe battery on merged master (refusal
  combinations; hidden-route greps for ML imports / env vars / subprocess /
  dynamic exec / file-IO; a ~540-point R-1 boundary sweep; exploratory-junk
  injection into the acceptance evaluator; guard write probe; CLI exit codes).
  Probes used synthetic inline values and committed metadata only.

## Audit status

**`ML_STEP4_GUARDED_WIRING_ACCEPTABLE_FOR_REAL_RUN_BODY_IMPLEMENTATION_REVIEW`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## 1. Executive verdict

**The PR #415 wiring layer is fail-closed, internally consistent, and
acceptable as the base for a later code-only real-run-body implementation PR.
Zero blockers.** Real execution is impossible in this build: all three refusal
combinations raise; the package contains **no ML imports, no raw-data readers,
no environment-variable routes, no subprocess/dynamic-exec, and no run body to
reach**. Preflight touches committed inventory *metadata* only and cannot reach
the raw-file hasher. The seven PR #414 residuals are bound at the level a
wiring PR can bind them — four substantively enforced in code
(R-1, R-6, seed policy, maxDD constant recorded + fail-closed checks) and three
bound as machine-readable provenance whose *enforcement* necessarily lives in
the future run body (R-4 routing discipline, R-5 denominator computation,
diagnostics-labeler invocation) — each carried forward as an explicit
required-in-body item (§17). One honest R-1 observation (float-vs-integer floor
divergence on 7/540 sampled sizes; deterministic, non-ambiguous) is recorded
with a recommended body hardening. No author-and-run risk exists: the body is
absent, and implementing it requires a new, reviewable PR.

## 2. Audit scope

All ten `scripts/ml_step4/` modules (`executor`, `execute_365d_ba`, `contract`,
`split`, `labels`, `metrics`, `evidence`, `acceptance`, `thresholds`,
`inventory`, plus `run_365d_ba` and `__init__`), all twelve
`tests/ml_step4/` modules (158 tests), the PR #415 diff, and the PR
#413/#414/#415 documents. Out of scope: any real-run-body design (not yet
written) and the PR #413 research conclusions (context only).

## 3. Real execution refusal audit — **REFUSED EVERYWHERE**

Executed: `guarded_execute(dry_run=False)`, `(dry_run=True,
allow_real_execution=True)`, and `(dry_run=False, allow_real_execution=True)`
**all raise `ExecutionRefusedError`** — the `allow_real_execution` parameter is
future-signature only and unlocks nothing. CLI: `--preflight` → exit 0;
`--execute` → exit 2; no flag → exit 2 (verified). API refusal is a specific,
testable exception; CLI refusal prints `REFUSED: …` and returns nonzero.
Hidden-route hunt (grep, executed): **no** `lightgbm`/`lgb` import, `.fit(`,
`predict_proba` call (only descriptor strings in `contract.py`); **no**
`os.environ`/`getenv`, `subprocess`, `eval(`/`exec(`/`__import__` anywhere in
the package. The dry-run/preflight path is the only reachable behavior; there
is no run body to invoke by any import, flag, default, env var, or direct call.

## 4. Raw data access audit — **NONE**

File-IO inventory of the whole package (grep, executed): exactly four sites —
`evidence.write_text` ×2 (scrub+guard gated), `inventory.read_text` (committed
inventory JSON metadata), and `inventory.p.open("rb")` inside
`file_sha256_and_size`. **Executor references neither `verify_files` nor
`file_sha256_and_size`** (verified against source): preflight resolves count +
total bytes from committed metadata and reports `checksums_computed: false`,
`raw_files_read: false`. No pandas/csv/parquet/JSONL-row reader exists in the
package. The only path parameter (`inventory_path`) redirects which *metadata
JSON* is parsed — it cannot cause a raw-candle read because no candle-parsing
code exists. No `365d_BA` raw payload is touched.

## 5. Evidence write audit — **NO UNEXPECTED WRITE POSSIBLE**

Executor **never calls** `evidence.write_report` (the single reference is the
`callable(...)` presence gate); CLI only prints. Executed probe: a direct write
into `artifacts/ml_step4/365d_ba_v1/` is refused by the repo-root-anchored
guard (probe file never created; directory still exactly the 8 PR #409 files,
git-clean before/after). PR #414's cwd-manipulation/traversal/nested/case-trick
results still hold (unchanged `evidence.py`). Scrubber still rejects Drive
links, R2 endpoints, credentials, env dumps, raw rows, and personal paths
(re-verified in the ml_step4 suite). Dry-run/preflight outputs are
`assert_clean`-gated before print. Future evidence writing requires the
explicit later implementation to call `write_report(...,
allow_execution_evidence=True)` — a flag set **nowhere** in the tree.

## 6. R-1 audit: bar-granularity boundary rule — **BOUND; one observation**

`split.bar_index_split` expresses segments as M1 **bar indices** with the
recorded rule `[start, end)` (end-exclusive; verified adjacent segments share
no bar); purge/embargo = horizon+1 = 21 (test-pinned as
`HORIZON_M1_BARS + 1`); small-n fails closed; `assert_m1_aligned` rejects
non-`:00`-second and sub-second timestamps; all inputs must be tz-aware UTC
(naive fails closed in `_parse`). **Executed sweep over ~540 sizes
(n=100…20,000): zero ordering/inversion/nondeterminism anomalies.**
Observation (non-blocking): `int(0.70 * n)` diverges from the exact-rational
floor `(70*n)//100` for **7 of 540** sampled sizes (float representation of
0.70). The result is still fully deterministic (IEEE-754), the emitted indices
are recorded in the split metadata, and no ambiguity exists — but the
real-run-body PR **should compute boundaries with integer arithmetic**
(e.g. `(70*n)//100`) or explicitly freeze the emitted indices as the
authoritative record (the design already emits them). Future holdout
evaluation can reuse the rule without reinterpretation.

## 7. R-4 audit: single-source label routing — **BOUND AT PROVENANCE LEVEL**

Exactly one label contract identity exists
(`LABEL_CONTRACT_ID = scripts.ml_step4.labels.v1`), recorded in
preflight/plan metadata. `labels.py` **delegates by identity** to the committed
F-2 helper (`labels.traded_direction_pnl_price is
scripts.traded_direction_pnl.traded_direction_pnl_price` — executed) and forks
no PnL logic. **No barrier/PnL math exists in `executor.py` or the CLI**
(verified: no `tp_idx`/`sl_idx`/`barrier_label(` in executor source); no legacy
fallback path is imported anywhere in the package. Adapter failure currently
stops everything structurally (an import failure kills the module). The
*routing discipline for real data* cannot be enforced until a body exists —
carried as required-in-body item §17(2): the body must route all label
generation AND all trade scoring through `labels.py`, must not catch-and-
continue on adapter failure, and its audit must re-verify this.

## 8. R-5 audit: trading-day definition — **BOUND; computation deferred**

`contract.TRADING_DAY_DEFINITION = "utc_calendar_date"` and
`DAILY_COVERAGE_DENOMINATOR = "distinct_utc_calendar_dates_in_holdout"` are
machine-recorded inside `contract_dict()["evaluation"]` (config-hash covered).
`metrics.trading_day_utc` converts tz-aware datetimes to the UTC date and
**fails closed on naive datetimes** (tested, incl. a UTC+2 → previous-UTC-day
boundary case). Days with no opportunities: under the recorded definition they
*count in the denominator* and cannot appear in the numerator — deterministic
and interpretable for first-run coverage. The actual denominator *computation*
over the real holdout window is a body task — required-in-body item §17(3).
No local/broker timezone can leak: the only day-key function refuses naive
input and hard-converts to UTC.

## 9. R-6 audit: threshold tie-rule provenance — **BOUND**

`THRESHOLD_TIE_RULE = "prefer_production_default_0.40_else_smallest"` is
machine-readable provenance: present in `threshold_config()` (covered by the
dedicated `threshold_config_hash`, determinism verified) AND inside
`contract_dict()` (covered by `config_hash`); changing it changes the hash
(tested). Behavior matches the record: `select_threshold` prefers 0.40 among
tied best, else the smallest (re-executed in PR #414 and covered by tests).
Candidates remain exactly `{0.35, 0.40, 0.45}` inside `threshold_config`
(executed check).

## 10. Seed / determinism audit — **BOUND, HONESTLY SCOPED**

`model_config()` still contains **no** `random_state`; **`model_config_hash`
is byte-identical to the PR #412 value (`bc27cfa39ea3…`) — executed**, so the
PR #407 trainer binding is untouched. `executor.reproducibility_policy()` is a
separate execution-layer record: deterministic data ordering; fixed validation
selection; bar-index split determinism; runtime seeds (python/numpy/
lightgbm-if-supported) and package versions to be captured in future evidence;
level honestly declared `bounded_not_bitwise_guaranteed` with the LightGBM
thread/platform limitation stated. `assert_reproducibility_recorded` fails
closed on a missing/incomplete policy or on any policy that claims to alter the
model hash. No determinism overclaim found. Sufficient for a later body
implementation, whose evidence must record the seeds/versions actually used —
required-in-body item §17(4).

## 11. MaxDD fixed-notional audit — **BOUND; default-wiring deferred**

`FIXED_NOTIONAL_EQUITY_PIPS = 10_000.0` is pinned and recorded in
`contract_dict()["evaluation"]` together with the deterministic formula
(`peak_to_trough_pips / fixed_notional_equity_pips`); changing it changes
`config_hash` (tested); `assert_maxdd_notional` fails closed on
missing/non-positive values. This **resolves the PR #413 material
metric-definition gap** (the ≤15% criterion is now falsifiable: 15% of 10,000
pips = 1,500 pips peak-to-trough). Residual: `metrics.compute_all` still takes
`notional_equity_pips` as a caller argument — the body PR must wire it to the
contract constant (or assert equality) so the recorded constant is the one
actually used — required-in-body item §17(1).

## 12. NON_DECISION_EXPLORATORY audit — **BOUND + STRUCTURALLY IMMUNE**

`label_diagnostics` tags every diagnostic; `assert_diagnostics_labeled` fails
closed on unlabeled diagnostics AND on a decision-metric leaf presented as
exploratory; `assert_diagnostics_excluded_from_decision` rejects exploratory
keys inside an acceptance criteria table. **Stronger, structural proof
(executed):** exploratory junk (`feature_importance`, `session_contribution`)
injected directly into the metrics dict does **not** appear in the acceptance
criteria and does not change the status — the evaluator reads only its fixed
`REQUIRED_METRIC_PATHS`, so diagnostics *cannot* influence acceptance even if
mislabeled. The named diagnostics (feature importance, calibration,
per-threshold curves, session contribution, win rate, payoff, concurrency,
pair contribution) are enumerated in `EXPLORATORY_DIAGNOSTIC_KEYS`. Invoking
the labeler in the real evidence pipeline is a body task — required-in-body
item §17(5).

## 13. Preflight hard-gate audit — per-gate classification

| Gate | Classification |
| --- | --- |
| config / feature / model / threshold hashes | **substantively bound** (computed live each preflight) |
| threshold tie-rule provenance | **substantively bound** (read from config; hash-covered) |
| maxDD fixed-notional | **substantively bound** (value + positivity checked) |
| reproducibility policy | **substantively bound** (required fields validated fail-closed) |
| label contract identity | **substantively bound** (function evaluated) |
| inventory resolver + expected count/bytes | **substantively bound** (committed metadata resolved and compared; refusal on unresolvable path tested) |
| evidence directory policy | **substantively bound** (constants present; guard behavior separately probe-verified §5) |
| split policy / metrics evaluator / acceptance evaluator / evidence writer / diagnostic labeling | **partially bound — presence-level by design** (callability/constant checks; the components' correctness is enforced by their own 158-test suite, not by the gate) |
| code SHA recordable | **deferred-to-runtime, honestly named** (`RECORDABLE_AT_RUNTIME`; the body must record the actual SHA — §17(4)) |

**No gate is placeholder-only in a false-safety sense:** every presence-level
gate names precisely what it checks, and the substantive correctness of each
component is carried by its own tests. Missing components flip the report to
`PREFLIGHT_REFUSED_INCOMPLETE` (tested via unresolvable inventory).

## 14. Hash / contract audit — **CONSISTENT**

The `threshold_candidates` → `threshold_config` swap in `contract_dict` is the
intentional R-6 binding; candidates are preserved inside it as
`[0.35, 0.40, 0.45]` (executed). `model_config_hash` is **unchanged** from
PR #412 (`bc27cfa39ea3…` — the PR #407 trainer convention holds). Feature
config remains v4 base only (empty enabled groups — executed).
`threshold_config_hash` is deterministic. `config_hash` now covers the newly
bound residuals (tie rule, trading-day definition, coverage denominator, maxDD
constant, DD formula). No consumed hash is invalidated: **PR #409 stopped
pre-training with null hashes**, so no run has ever consumed any prior value.

## 15. CLI / API surface audit — **CLEAN**

One safe path (`--preflight`, exit 0), two refusal paths (`--execute`, no flag;
both exit 2 — executed) in a mutually-exclusive argument group. Output is
`assert_clean`-gated before print (personal paths/env dumps would raise before
emission); status names (`…_IMPLEMENTED_NO_RUN`, `PREFLIGHT_WIRING_COMPLETE_
NO_RUN`, `…_NOT_PERFORMED`) cannot be mistaken for execution or readiness;
every plan carries `execution_performed/raw_data_read/model_trained/
holdout_evaluated/evidence_written = false`. API exceptions are specific
(`ExecutionRefusedError`, `PreflightError`, `DiagnosticLabelingError`) and
test-pinned.

## 16. Test adequacy audit — **ADEQUATE FOR WIRING; gaps listed for the body**

158 synthetic-only tests; refusal paths (3 API combos + 2 CLI), dry-run/
preflight structure, all seven residual bindings, no-evidence-write,
no-raw-read (structural), CLI behavior, hash/provenance change-detection, and
failure cases (not only happy paths) are all covered. **Gaps to close in/with
the body PR:** (a) a test pinning `compute_all`'s notional to the contract
constant once wired; (b) a label-adapter-failure-stops-run test against the
real body; (c) an end-to-end synthetic-fixture rehearsal of the full guarded
body (fixture-in → 8 evidence files out) before any real run; (d) optional
integer-boundary property test if §6's hardening is adopted; (e) a runtime
code-SHA/seed-capture test.

## 17. Remaining limitations (NOT implemented in PR #415)

Real raw read; v4-base feature generation over real data; bulk B-2 labels
through `labels.py`; from-scratch LightGBM training; prediction; validation-
only threshold selection on real outputs; single event-driven holdout
evaluation; real daily-portfolio-Sharpe / maxDD / turnover / concentration /
cost-cell metrics; the eight metadata-only evidence files with F-5 provenance;
actual seed/version/code-SHA capture from a real runtime.

**Required-in-body checklist (carried forward):**
1. wire `metrics.compute_all` notional to `contract.FIXED_NOTIONAL_EQUITY_PIPS`;
2. route ALL label generation + trade scoring through `labels.py`; no
   catch-and-continue on adapter failure;
3. compute the holdout coverage denominator per the recorded UTC-date rule;
4. record actual code SHA, seeds, package versions in the run manifest;
5. invoke the diagnostics labeler in the evidence pipeline;
6. recommended: integer-arithmetic split boundaries (or freeze emitted indices
   as authoritative).

**Recommended shape:** ONE code-only / no-run real-run-body implementation PR
(the body + synthetic-fixture end-to-end rehearsal; no real data in CI), then a
Fable 5 source audit of the body, then the separately-authorised first-run
execution PR. Splitting the body further is not necessary — the primitives are
already reviewed; the body is orchestration glue plus the feature/label bulk
paths, which are best audited as one coherent unit.

## 18. Blockers

**None.**

## 19. Recommendation for next gate

Merge this source audit → **code-only / no-run real-run-body implementation
PR** (per §17's checklist and shape; synthetic fixtures only; no execution;
no raw data in CI) → **Fable 5 source audit of the body** → only then the
separately-authorised first-run execution PR under the PR #413
falsification/baseline frame → mandated post-run review.

## 20. Non-authorisation statements

This audit did **not**: implement the real run body; execute ML Step 4; read
real `365d_BA` raw data (probes used committed metadata + inline literals);
train a model; run a backtest; generate real ML metrics; create real execution
evidence (the guard probe was refused before any write; PR #409 dir verified 8
files, git-clean); write model binaries; access external disks, Google Drive,
or R2; start Phase C2; touch `730d_BA`/`3650d_BA`; claim production readiness.
