# M15 aggregation / dataset machinery — implementation note (gate 5, SYNTHETIC ONLY)

- **Document class:** code-only implementation note. The code is **synthetic /
  fixture-tested only** — it reads no real data, derives no real M15 bytes,
  computes no strategy metrics, trains nothing, and adopts no epoch.
- **Branch:** `code/m15-aggregation-dataset-machinery`
- **Base:** master `7e795d424c1c4bcf297de2a459a3c0a0ba3df0f7` (post PR #431 merge).

## Statuses

- **`M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`**
- Carried: `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED` ·
  `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` ·
  `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_ACCEPTABLE_FOR_GATE3A_DATASET_EPOCH_ADOPTION` ·
  `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_PROPOSED`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `M15_AUTHORISED`, `H1_AUTHORISED`,
`H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, or
`MEETS`; those tokens appear only in this prohibition list (and, in code, only
inside the refusal guard's `FORBIDDEN_STATUSES` set).

## Scope

Implements only the fixture-tested machinery required by the frozen PR #429
contract and the PR #430 T-1…T-7 tightenings, so that a **later**,
separately-authorised step can produce real derived-dataset metadata under the
value-pinned safety net. Nothing here touches production data.

## Files changed

**Code (new package `scripts/m15_gate3a/`):**
- `__init__.py` — status constants.
- `aggregation.py` — pure M1→M15 aggregation + gap report + `to_pips`.
- `no_overlap.py` — dead-window boundary constants + no-overlap assertions.
- `warmup.py` — T-1 warm-up burn-in policy (fail-closed on pre-forward loads).
- `effective_n.py` — effective-N estimator helper + `INSUFFICIENT_SAMPLE`.
- `cost_schema.py` — cost-table metadata schema validation (no real spreads).
- `artifacts.py` — gate-3a-strict scrubber + metadata artifact writer/validator.
- `guards.py` — refusal guards (real-data / train / evaluate / execute /
  forward-adopt / model-binary / forbidden-status).

**Tests (new `tests/m15_gate3a/`):** `test_aggregation.py`, `test_no_overlap.py`,
`test_warmup.py`, `test_effective_n.py`, `test_cost_schema.py`,
`test_artifacts_scrub.py`, `test_guards.py` (52 tests).

**Docs:** this note + a roadmap pointer.

## Implemented contract pieces

- **M1→M15 aggregation:** UTC 15-min bucket start; per-side bid/ask OHLC
  (open=first, high=max, low=min, close=last); **no mid construction**;
  `n_source_bars` recorded; eligibility iff `n_source_bars == 15`; incomplete
  buckets diagnostics-only; **no imputation**; **no synthetic weekend bars**
  (buckets emitted only where source minutes exist; whole-bucket gaps are
  *counted*, not fabricated); gap report; per-pair pip authority via
  `data_adapter.pip_size_for` (unknown/empty pair fails closed).
- **No-overlap utilities (T-7 / R-2b):** frozen constants (design ≤
  `2026-02-28T23:59:59Z`; dead window `2026-03-01`…`2026-04-24`; forward ≥
  `2026-04-25T00:00:00Z`) and per-file / per-role assertions; any dead-window
  intersection fails closed.
- **Warm-up burn-in policy (T-1):** `w_bars ≥ longest_feature_lookback` (incl.
  H1/H4); loading any timestamp before the forward floor fails closed; exact W
  frozen later at feature implementation.
- **Effective-N helper (T-6):** raw + `rho_h` (horizon-24 overlap) + `rho_x`
  (cross-pair) → `effective_n`; `< 400` (or raw `< 1000`) at holdout ⇒
  `INSUFFICIENT_SAMPLE`; invalid inputs fail closed; no strategy metric is
  computed.
- **Cost-table schema (T-7 p95):** validates pair/session (Asia/Europe/US UTC),
  median + p90 + **p95 diagnostic**, padding `0.3`, cell `0.5`, formula, pip
  mapping (checked against the authority), `claim_scope == quote_cost_validity`;
  real spreads are **not** computed.
- **Artifact scrubber:** the ML Step 4 base scrubber **plus** gate-3a
  prohibitions on prediction / model / trade-level / strategy-metric keys; the
  writer refuses to write under protected real paths.

## Refusal behavior

`guards.py` fails closed on: non-synthetic modes; protected real paths
(`artifacts/ml_step4/365d_ba_v1`, `artifacts/gate_p1_pr_b/firstrun_365d_ba`);
forbidden operations (read-real-data, derive-real-M15, compute-real-checksums /
spreads / labels, train, validate, evaluate-validation/holdout, execute,
write-model-binary, adopt-forward-epoch); and assertion of any forbidden status
(`NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, `PRODUCTION_READY`, `MEETS`, …).

## Tests

52 fixture tests: aggregation (15-row eligible, <15 incomplete, missing-minute
no-imputation, UTC boundary, weekend no-synthetic, JPY/non-JPY value-pinned
pips, unknown-pair fail-closed, naive-ts fail-closed, >15-bars fail-closed);
no-overlap (design/forward pass+fail, dead-window intersection, per-file bounds,
warm-up pre-forward fail); effective-N (raw preserved, adjustments, `<400` and
raw-floor `INSUFFICIENT_SAMPLE`, invalid inputs); cost schema (valid,
missing-p95, wrong-JPY-pip, missing/wrong scope, unsupported session,
wrong padding/cell); scrub (metadata passes; raw-row / candles / path / secret /
prediction / model / metric / trade payloads fail; writer clean-write + real-path
refusal); guards (synthetic-only, protected-path, forbidden-op, unknown-op,
forbidden-status).

## Non-authorisation statements

No real raw-data read; no real M15 derivation; no real checksums; no real spread
computation; no labels on real data; no model training; no validation
computation; no holdout evaluation; no predictions; no strategy metrics; no
execution evidence; no model binaries; no forward-epoch adoption; no epoch
adoption; no byte-admissibility claim; no `730d_BA`/`3650d_BA`; no Phase C2; no
H2/H3; no production-readiness claim.

## Recommendation for next gate

With the machinery synthetic-tested, the next step is a **separately-authorised
gate-3a continuation** that runs this aggregation over the **design-span** M1
data (design-data derivation only — still no forward run) to populate the
design-M15 inventory/checksums and derive the cost tables, under these
value-pinned tests and a source-contamination audit (gate 6). The
**forward-epoch adoption remains a documented WAIT** until ≥ 5 months of forward
data accrue (earliest ≈ 2026-10). Nothing runs, trains, or is adopted without
its own explicit authorisation.
