# Fable 5 source-contamination audit — PR #432 M15 aggregation/dataset machinery

- **Document class:** doc-only adversarial source audit of the merged gate-5
  machinery, required **before any real data read**. Not an implementation PR,
  not a gate-3a continuation, not a derivation/validation/execution PR.
  **No real data read; no real M15 derived; nothing trained or executed.** All
  probes in this audit ran on synthetic literals only.
- **Branch:** `docs/fable5-m15-machinery-source-audit`
- **Base:** master `2351c765c0a21607b91b84c4dd420f255af78a5f` (post PR #432 merge).
- **Audit target:** `scripts/m15_gate3a/` + `tests/m15_gate3a/` + the PR #432
  implementation note, against the gate-3a adoption record, the gate-4 design
  audit (T-1…T-7), and the frozen pre-registration contract.

## Statuses

- **Verdict:**
  **`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`**
  — five confirmed defects (F-1…F-5, §13), two of them **INV-1-class
  value-path bugs** in the exact function that would later produce real derived
  bytes. All are small, precisely-scoped, and fixable in one code-only PR;
  nothing requires a rewrite. **Gate-3a continuation must not start until the
  fixes land and are re-checked.**
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
  · `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_ACCEPTABLE_FOR_GATE3A_DATASET_EPOCH_ADOPTION`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `M15_AUTHORISED`, `H1_AUTHORISED`,
`H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, or
`MEETS`; those tokens appear only in this prohibition list.

---

## 1. Executive verdict

- **Is the PR #432 machinery acceptable for a future gate-3a continuation?**
  **Not yet.** The *containment* layer is sound — synthetic/fixture-only, no
  real-data read path, no derivation/validation/holdout/training/execution
  route, no forbidden claims — but the *value layer* of the aggregation and
  two helpers has five confirmed defects that would corrupt or mislabel real
  derived data if run as-is. Exactly the defect class (silent unit/value
  corruption) that invalidated PR #421 — which is why this audit exists before
  any real read.
- **Does it remain synthetic/fixture-only?** Yes (§2, §9): no CLI, no file
  readers, no `__main__`, no route to real archives; guards fail closed.
- **Real-data read paths?** None found. **Real M15 derivation paths enabled?**
  None — the pure function exists but nothing feeds it real rows, and the
  protected-path guards refuse the real trees.
- **Validation/holdout/training/execution paths?** None.
- **Byte-admissibility / epoch-adoption / production claims?** None — the
  forbidden labels appear only inside the refusal guard's blocklist.
- **Blockers before gate-3a continuation?** **Yes — F-1…F-5 (§13),** to be
  fixed in one code-only PR + re-check.

## 2. Audit scope

Read line-by-line: all 8 modules of `scripts/m15_gate3a/` and all 7 test
modules; the implementation note; the gate-3a adoption record and its 8
metadata artifacts; the gate-4 T-1…T-7 register; the frozen contract. Ran
**synthetic adversarial probes** (literal in-memory rows only — no file, no
real data) against every suspected weakness; every finding below is
**probe-confirmed**, not speculative.

## 3. Scope and import graph audit — CLEAN

- **Outbound imports (complete list):** stdlib (`datetime`, `pathlib`,
  `dataclasses`, `typing`, `json` via evidence) + exactly two audited internal
  modules: `scripts.ml_step4.data_adapter.pip_size_for` (the pip authority)
  and `scripts.ml_step4.evidence` (scrubber / `repo_root` / `serialise`).
  **No** trainer, broker, model, deployed-model, live/paper, stage/compare, or
  raw-loader import exists anywhere in the package.
- **Inbound imports:** grep over `scripts/`, `src/`, `tools/` finds **zero
  production or legacy callers** of `m15_gate3a` — only its own tests. No
  legacy path can invoke it unexpectedly; it can invoke no legacy evidence /
  model / broker / raw-data path.
- No hidden real-data route, training route, execution route,
  validation/holdout metric route, model-binary route, deployed-model reuse,
  or live/paper route. **CLEAN.**

## 4. Aggregation audit — TWO CONFIRMED DEFECTS (F-1, F-2)

Contract conformance verified: UTC 15-min bucket start (`minute // 15 * 15`;
boundary probes at :14/:15 split correctly); per-side bid/ask OHLC
(open=first, high=max, low=min, close=last); **no mid-price construction**
(asserted by test); `n_source_bars` recorded; eligibility iff `== 15`;
incomplete buckets diagnostics-only; no imputation; no synthetic weekend bars
(whole-bucket gaps counted, never fabricated); gap report; pip authority
reused (unknown/empty pair fails closed **before** any aggregation); JPY and
non-JPY value-pinned tests present; unsorted input handled (rows sorted within
bucket; buckets sorted); row schema validated; naive `ts` rejected; >15 rows
per bucket rejected.

**F-1 (CONFIRMED — false eligibility on duplicate/sub-minute timestamps):**
`n_source_bars` counts **rows, not distinct source minutes**. Probe: 14
distinct minutes + 1 duplicated minute = 15 rows → `n_source_bars = 15`,
`eligible = True` — a bucket **missing a minute** becomes label/event-eligible.
Same result with two rows in the same minute at different seconds. The `> 15`
guard catches gross duplication but ≤ 15-with-duplicates passes silently. The
committed M1 inventory records `duplicate_timestamps` per file, so the risk on
the real archive may be zero — but the machinery itself violates the frozen
`n_source_bars == 15` semantics (15 **distinct** minutes) and must fail closed
on intra-bucket duplicate minutes. **Blocker.**

**F-2 (CONFIRMED — non-finite prices accepted and silently swallowed):**
`isinstance(row[k], (int, float))` accepts `NaN`/`inf`. Probe: a `NaN` in
`bid_h` produced a **normal-looking, wrong** bar high (Python `max()` skips or
returns NaN depending on operand order) with `eligible = True` — the worst
variant: not even a propagating NaN, but a plausible wrong value. The
committed inventory tracks `non_finite_fields_count`, but the machinery must
reject non-finite inputs itself. **Blocker.**

Other attacks — off-by-one boundaries, weekend/rollover partials, timezone
handling, pair parsing, pip scaling: correct (partials near boundaries can only
*lose* eligibility, fail-safe). Whether real usage could include the dead
window is governed by §5 utilities + T-7 artifacts, not by this function —
correctly separated.

## 5. No-overlap / dead-window audit — CLEAN with one precision note (F-5, O-3)

Constants exact: design ≤ `2026-02-28T23:59:59Z`; dead window
`2026-03-01T00:00:00Z`…`2026-04-24T23:59:59Z`; forward ≥
`2026-04-25T00:00:00Z`. Boundary probes: design ending exactly at
`23:59:59` passes; anything later (including fractional seconds) fails
closed; forward starting exactly at the floor passes; `2026-04-24T*` fails;
any role-span intersecting the dead window fails; per-file assertions fail
closed on missing bounds; the intersection predicate
(`not (ts_max < DEAD_START or ts_min > DEAD_END)`) is inclusive-correct.

**F-5 (CONFIRMED, minor):** `_parse` (and the warm-up parser) **assume UTC for
timezone-naive datetimes** instead of rejecting them. A naive local-time
datetime from future glue code would be silently reinterpreted as UTC.
Fail-closed discipline requires rejecting naive datetimes. **Fix with the
F-batch.**

**O-3 (observation):** boundary constants use second granularity, leaving a
sub-second sliver (e.g. `23:59:59.5`) between design-end and dead-start that
fails design bounds (conservative) but is not *dead-window-labelled*.
Irrelevant for minute-aligned bars; optional hardening: half-open
next-day-00:00 semantics.

H1/H4-context and cost/spread-table dead-window exposure are governed by the
T-1 warm-up policy + T-7 ts-bound artifacts; with F-5 fixed, no leakage path
remains at this layer.

## 6. Warm-up burn-in audit — SOUND (T-1 honoured at this layer)

`WarmupPolicy` validates: `w_bars ≤ 0` fails; `w_bars <
longest_feature_lookback_bars` fails (probe: W=0 and W<lookback both raise);
`assert_load_allowed` fails closed for **any** pre-forward timestamp (dead
window AND design span — correct: warm-up may never read *any* pre-forward
data). Metadata records `first_w_bars_event_eligible: false` and
`dead_window_loaded: false`. **Known deferred (not a defect):** the policy
object cannot itself force future feature code to *apply* W — that enforcement
belongs to the feature-implementation PR and its own source audit, as the
gate-4 T-1 ruling already states. Naive-datetime parsing shares F-5.

## 7. Effective-N audit — ONE CONFIRMED DEFECT (F-3)

Verified: raw count preserved; horizon default 24; `rho_h`/`rho_x` semantics
match the approved gate-3a spec (independent inputs recover `N_eff = raw`);
holdout floors (raw < 1000 OR N_eff < 400 ⇒ `INSUFFICIENT_SAMPLE`) enforced;
out-of-range adjustments, negative counts, `n_pairs < 1`, bad horizon all fail
closed; no strategy metric computed; effective-N is a sample-size statistic,
not a performance number.

**F-3 (CONFIRMED — role handling not fail-closed):** for `role="validation"`
the helper returns **`SAMPLE_SUFFICIENT` unconditionally** (probe: raw=5 →
`SAMPLE_SUFFICIENT`), and an **unknown role** (`"bogus_role"`) does the same.
The gate-3a estimator spec requires `INSUFFICIENT_SAMPLE` to be *available at
validation*; a helper that answers "sufficient" for roles it does not evaluate
is misleading in the dangerous direction. Required fix: unknown roles fail
closed; `role="validation"` either applies an explicit caller-supplied floor
or returns a distinct `NOT_EVALUATED_AT_THIS_ROLE` verdict — never
`SAMPLE_SUFFICIENT` by default. **Blocker (moderate).**

## 8. Cost schema audit — ONE CONFIRMED DEFECT (F-4)

Verified: sessions exactly Asia/Europe/US with UTC ranges; median + p90 +
**p95 diagnostic** all required (missing p95 fails); padding pinned to 0.3 and
cell to 0.5 (any other value fails — no loosening path); all-in formula
required; pip mapping checked **against the authority** (wrong JPY pip fails;
correct 0.01 passes; unknown pair fails closed via `pip_size_for`); duplicate
(pair, session) fails; `claim_scope` must equal `quote_cost_validity`
(live-fill claim impossible); no spread computation exists in the module —
schema only.

**F-4 (CONFIRMED — non-finite spreads pass):** `NaN` passes the
`isinstance(...) or v < 0` check (`NaN < 0` is `False`). Probe: a `NaN`
median validated as `COST_TABLE_SCHEMA_VALID`. Also `inf` passes. Required
fix: `math.isfinite` on all three statistics. Same class as F-2. **Blocker
(moderate).**

## 9. Artifact schema / scrubber audit — SOUND, one documented limitation (O-2)

Verified: the gate-3a scrubber layers prediction / model / trade-level /
validation-holdout-metric / strategy-metric key prohibitions on top of the
audited base scrubber; raw-row keys (`bid_o`…, `candles`, `rows`), Windows
drive paths, POSIX `/home/` paths, secrets (`AKIA…` probe), Drive/R2 patterns,
and env dumps all rejected (probe-confirmed); URLs are caught (the
drive-letter pattern incidentally matches `s://` — overly broad in the SAFE
direction); the writer validates **before** writing, writes deterministic
sorted-key JSON, and **refuses protected real paths including `..` traversal**
(probe: `artifacts/m15_gate3a/../ml_step4/365d_ba_v1/x` refused — `resolve()`
neutralises traversal).

**O-2 (known limitation, documented — not a blocker):** key-based scrubbing
cannot catch raw rows smuggled under *alternate* keys (probe:
`{"data": [{"o":…,"h":…}]}` passes). This is inherent to the base scrubber
that passed three prior audits; the mitigations are exactly these source
audits plus the fact that nothing in the package *produces* row-shaped data
into artifacts. Record; optionally add a numeric-array heuristic later.

## 10. Refusal guard audit — SOUND, one hardening note (O-1)

Verified: synthetic/fixture modes only (`real`, `production`, `live`, `demo`,
empty string all refused); forbidden operations (read-real-data,
derive-real-m15, compute-real-checksums/spreads/labels, train,
evaluate-validation/holdout, execute, write-model-binary,
adopt-forward-epoch) all refuse; **unknown operation flags refuse (fail
closed)**; protected paths (`artifacts/ml_step4/365d_ba_v1`,
`artifacts/gate_p1_pr_b/firstrun_365d_ba`) refuse, including nested paths and
traversal; Windows path comparison is case-insensitive via pathlib semantics.

**O-1 (hardening, optional):** `assert_status_allowed` is exact-match —
casing/whitespace variants (`"new_epoch_adopted"`, `"NEW_EPOCH_ADOPTED "`)
pass (probe-confirmed). This guard is belt-and-suspenders (statuses are
asserted by governance documents, not by code), so not a blocker; normalising
(strip + upper) is a one-line hardening to include in the fix PR.

## 11. Test adequacy audit — GOOD COVERAGE, FOUR REQUIRED ADDITIONS

The 52 tests genuinely cover: aggregation completeness/boundaries/weekend,
JPY + non-JPY value-pinned scaling, unknown-pair/naive-ts/>15-rows fail-closed,
no-overlap boundary passes/fails + per-file assertions + warm-up pre-forward
refusal, warm-up validation, effective-N maths + holdout floors + invalid
inputs, cost schema (p95/JPY/scope/session/padding/cell), scrubber
accept/reject matrix + writer refusals, and all guard classes.

**Missing tests that must be added with the fix PR (they currently would
fail):** (1) duplicate-minute / sub-minute rows → must NOT be eligible (F-1);
(2) non-finite price rejection in aggregation (F-2); (3) effective-N unknown
role fails closed + validation role never returns `SAMPLE_SUFFICIENT` by
default (F-3); (4) non-finite spread rejection in the cost schema (F-4); plus
(5) naive-datetime rejection in `no_overlap`/`warmup` parsing (F-5).

## 12. Non-authorisation audit — CLEAN

Neither code nor docs authorise: real raw-data read; real M15 derivation; real
checksum generation; validation computation; holdout evaluation; strategy
metrics; model training; execution; execution evidence; model binaries;
`NEW_EPOCH_ADOPTED`; `BYTE_ADMISSIBLE`; `730d_BA`; `3650d_BA`; Phase C2;
H2/H3; production readiness. The PR #432 amended note states the corrected
gate order (audit before any real read) and that the gate-3a continuation is
not authorised; forbidden labels appear only in prohibition lists / the guard
blocklist. Nothing is phrased as an authorisation.

## 13. Blockers (fix in ONE code-only PR, then re-check)

| # | Defect (probe-confirmed) | Required fix |
| --- | --- | --- |
| **F-1** | Duplicate-minute / sub-minute rows inflate `n_source_bars` → **false eligibility** (14 distinct minutes + 1 dup = eligible) | Count **distinct source minutes**; fail closed on any intra-bucket duplicate minute (and on non-minute-aligned seconds, or normalise-and-detect); eligibility = 15 distinct minutes |
| **F-2** | Non-finite prices (`NaN`/`inf`) accepted; `max()` **silently swallows** NaN → plausible wrong OHLC, still eligible | Reject non-finite values in `_validate_row` (`math.isfinite` on all 8 side keys); fail closed |
| **F-3** | `effective_n` returns `SAMPLE_SUFFICIENT` for `role="validation"` and for **unknown roles** | Unknown role → raise; validation role → explicit caller floor or `NOT_EVALUATED_AT_THIS_ROLE`; never default-sufficient |
| **F-4** | Cost schema accepts `NaN`/`inf` spreads (`NaN < 0` is `False`) | `math.isfinite` on median/p90/p95; fail closed |
| **F-5** | `no_overlap._parse` / warm-up parser silently assume UTC for naive datetimes | Reject naive datetimes (fail closed); ISO strings with explicit offset only |

Optional hardenings to ride along: O-1 status-string normalisation; O-2
numeric-array scrub heuristic; O-3 half-open boundary semantics.

**Required tests:** the five listed in §11.

## 14. Recommendation for next gate

**Proceed only after targeted code/test fixes:**

1. **Code-only fix PR** implementing F-1…F-5 (+ the five tests; O-1…O-3
   optional), touching only `scripts/m15_gate3a/` + `tests/m15_gate3a/` —
   no real data, no new capabilities, no guard loosening.
2. **Short Fable 5 re-check** verifying the fixes by test + source (the
   #423→#424 pattern).
3. **Only then** the separately-authorised **gate-3a continuation** with this
   exact shape: real **design-span** M15 derivation only; produce design-M15
   inventory/checksums (and cost tables if separately authorised); preserve
   dead-window exclusion (T-7 ts-bound proofs per file); **no** forward-epoch
   adoption; **no** validation computation; **no** holdout evaluation; **no**
   strategy metrics; **no** training; **no** execution; metadata-only,
   scrub-clean; **no** byte-admissibility / new-epoch-adoption claim unless
   separately ruled.
4. Forward-epoch adoption remains **BLOCKED/WAIT** throughout (accrual
   ≈ 2026-10).

This audit authorises none of the above; each step needs its own approval.
