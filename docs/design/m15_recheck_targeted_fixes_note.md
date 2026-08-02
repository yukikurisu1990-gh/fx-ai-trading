# Targeted fixes for the re-check blockers B-1…B-5 and required fixes R-1…R-10

- **Document class:** doc-only implementation note accompanying the fix Work PR.
  Executes nothing; authorises no gate.
- **Fixes:** the blockers and required fixes recorded in
  `docs/design/m15_aggregation_dataset_machinery_source_audit_recheck.md`
  (merged as `facef30`), which is the **source of truth** for every item below.
- **Status:** `M15_AGGREGATION_DATASET_MACHINERY_RECHECK_FIXES_PROPOSED`
- Carried: `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED` ·
  `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** ·
  **`NO_EXECUTION_PERFORMED`**

Synthetic-only. No real data was read, no M15 data derived, no checksum or
spread computed, no validation, holdout, training, inference or execution
performed.

---

## 1. Blockers

### B-1 — `pandas.Timestamp` nanoseconds defeated the minute-alignment guard

`aggregation._plain_utc_minute` now rebuilds a **plain** UTC `datetime` from the
timestamp's components and requires the original instant to equal it, in
addition to the explicit `.second` / `.microsecond` checks and an explicit
`nanosecond` attribute check. Bucket keys, duplicate detection and the
within-bucket sort all use that plain minute, never the caller's object, so a
`datetime` subclass can no longer smuggle sub-microsecond resolution into the
bucket key.

Why the equality check and not just a nanosecond test: it generalises. Any
subclass with resolution finer than a microsecond — known or not — fails the
comparison. The two guards are deliberately redundant (§4).

Also: `_bucket_start` asserts its own result is 15-minute aligned, and
`aggregate_m15` sorts on the normalised minute rather than on `row["ts"]`.

### B-2 — reversed ts bounds produced a false `PROVEN_NO_DEAD_WINDOW_OVERLAP`

`_assert_ordered` is now called by `assert_design_bounds`,
`assert_forward_bounds` **and** `assert_no_dead_window`, i.e. by both functions
`assert_per_file_bounds` actually dispatches to. A reversed span raises before
the dead-window predicate can short-circuit on `ts_min > DEAD_END`.

The dead window is additionally treated as covering the whole of its final
second (`_DEAD_END_EXCLUSIVE = DEAD_END + 1s`), which closes the O-3 sliver in
the **conservative** direction. This does not contradict the recorded decision
not to apply O-3: no published boundary constant moves, `DESIGN_END` is
untouched, and the committed `no_overlap_proof.json` remains valid — the change
only widens what counts as dead. Import-time assertions pin the ordering of the
five span constants.

### B-3 — effective-N diverged from the committed APPROVED spec

`effective_n` now takes **per-pair records** and implements
`artifacts/m15_gate3a/effective_n_estimator_spec.json` literally:
`rho_h_pair = 1 + (H-1)·overlap_pair`, `N_eff_pair = raw_pair / rho_h_pair`,
`rho_x = 1 + (P-1)·corr`, `N_eff = Σ N_eff_pair / rho_x`. Both `portfolio` and
`per_pair` granularity are returned, as the spec's `reporting` block requires.

The audited counter-example is pinned as a regression test: 50 events at
overlap 0.0 plus 8000 at overlap 1.0 gives `383.33` → `INSUFFICIENT_SAMPLE`,
and the test additionally asserts the result is **not** the pre-fix `644.0`.
`tests/m15_gate3a/test_effective_n.py` was rewritten so it pins the approved
formula instead of the divergent one. Holdout floors (raw ≥ 1000, N_eff ≥ 400)
are unchanged and are now pinned by verdict-driving cases at and either side of
each floor.

### B-4 — pip authority was case-sensitive and universe-unbound

New `scripts/m15_gate3a/pair_authority.py` is the gate-3a boundary. It pins the
frozen `PAIRS_20` universe, normalises case / separators / compact spellings to
the canonical `XXX_YYY`, proves the normalisation is injective at import time,
and only then delegates to the single pip authority. `aggregation` and
`cost_schema` call it instead of `data_adapter.pip_size_for`, so `usd_jpy`,
`USDJPY` and `"USD_JPY "` all resolve to `0.01` and an off-universe name fails
closed. `cost_schema` additionally requires the entry to carry the canonical
spelling, so the cross-check can no longer agree with itself on a wrong scale.

The two false docstrings in `aggregation.py` ("fail-closed on unknown pair")
are now true statements about the new boundary.

### B-5 — validation floors were accepted unvalidated

Validation floors must now be supplied **together**, must be correctly typed
(`int` for the raw floor, `int|float` for the N_eff floor, never `bool`), and
must be finite and strictly positive. A NaN, infinite, zero or negative floor
raises instead of silently deciding. Zero events can no longer produce
`SAMPLE_SUFFICIENT`. The floors actually applied are echoed in the record
(`floors_applied`), so a validation verdict is self-describing.

## 2. Required fixes R-1…R-10

| # | Disposition | What was done |
| --- | --- | --- |
| **R-1** `horizon_bars` override unauditable | **Fixed** | The horizon is rejected if overridden for `role="holdout"` (frozen at 24 by Ruling 6) and is echoed in the record for every role. |
| **R-2** finite-but-impossible rows absorbed | **Fixed** | `_assert_row_coherent` requires `h ≥ max(o,c)`, `l ≤ min(o,c)`, `h ≥ l` per side and `ask_* ≥ bid_*` per row. |
| **R-3** `\\?\` alias defeats `refuse_real_path` | **Fixed** | `_strip_extended_prefix` removes `\\?\` and `\\?\UNC\` before resolution and comparison. |
| **R-4** forbidden-status control unreachable | **Fixed** | `FORBIDDEN_STATUSES` widened to the playbook §10 list (adds `READY_FOR_LIVE`, `ROBUST`, `DEPLOYABLE`); `normalise_status` folds case, NFKC and separator variants; and the scrubber now inspects status **values**, so a forbidden label cannot be written into an artifact. |
| **R-5** O-2 heuristic defeated by one extra dict | **Fixed** | Row-like detection **counts** qualifying records instead of `all(...)`; a columnar check rejects ≥ 2 equal-length numeric series; list-of-lists rows are rejected; the key matcher now strips whitespace, consistent with O-1. |
| **R-6** finite inputs → non-finite output | **Fixed** | `_assert_bar_finite` re-checks every emitted bar value and `spread_close`. |
| **R-7** gap report bucket-granular / wrong key | **Fixed** | `missing_minute_count` (the committed inventory's key) added and `max_gap_minutes` computed from consecutive missing **minutes**; whole-bucket counting retained alongside. |
| **R-8** cost schema blind to units | **Fixed** | Mandatory `spread_unit` pinned to `"price"` per the committed plan; `all_in_cost_formula` pinned verbatim; `median ≤ p90 ≤ p95` enforced; the summary now reports `pairs_covered` and a `full_20x3_coverage` flag. Coverage is **reported, not enforced** — the committed plan defers table production to the implementation gate, so a partial table must still validate. |
| **R-9** artifact `name` escapes `out_dir` | **Fixed** | `name` must be a bare filename; both refusals now run **before** `mkdir`, so a refused write leaves no stray directory. |
| **R-10** test gaps | **Fixed** | See §3. |

Also folded in (recorded as non-blocking observations by the re-check, closed
here because they sit in the same files and the same objective):

- **N-3** — `WarmupPolicy.assert_load_allowed` now calls `validate()` first, so
  an under-sized policy cannot authorise a load.
- **N-4** — `bool` is rejected wherever a count or fraction is expected in
  `effective_n`, matching the strictness aggregation and cost schema already had.

**Deliberately NOT changed in this PR** (out of this objective; recorded as
residual):

- **N-5** the protected-prefix set is still two entries. Widening it to
  `artifacts/m15_gate3a/`, stage24/stage25 and `data/` changes what the
  machinery may write and touches the evidence-protection contract — that is a
  governance-adjacent decision, not a defect fix.
- **N-6** `pip_size_for` still lives in `data_adapter` beside
  `Real365dBaProvider`. Moving it is a refactor of an ml_step4 module outside
  this fix's scope; containment already holds in the call-graph sense and the
  new `pair_authority` boundary is the mitigation.
- **N-7** cwd-dependent tests in `test_guards.py` / `test_artifacts_scrub.py`
  were left as-is; they pass from the repo root, and the new tests avoid the
  pattern.
- **N-8** no automated containment test was added; it belongs with the
  import-graph hardening in N-6.
- **N-9** the duplicate `RealDataRefusedError` name lives in `data_adapter`.
- **N-10** the open-side spread variant is a contract-schema addition, not a
  defect.
- **N-12** the "+39 tests" count in the PR #434 record is historical.

## 3. Test strengthening

`tests/m15_gate3a/test_recheck_fixes.py` is new; `test_effective_n.py`,
`test_aggregation.py`, `test_cost_schema.py` and `test_source_audit_fixes.py`
were updated to the corrected contract. Coverage added:

- `pandas.Timestamp` inputs: nanosecond rejection; all-15-rows sub-minute; one
  sub-minute row among aligned rows; ns=0 vs ns>0 for the same minute; an
  accepted aligned pandas bucket whose bar `ts` is asserted to be a **plain**
  `datetime` on a 15-minute boundary; a tz-aware pandas timestamp normalised to
  UTC.
- Value-pinned OHLC for **both** sides (`bid_o/h/l/c`, `ask_o/h/l/c`) plus
  `spread_close` sign and magnitude — a high↔low swap or a spread-sign
  inversion now fails.
- `math.isfinite` on all **eight** side keys × {NaN, +inf, −inf}, plus `bool`
  rejection on all eight.
- Reversed and dead-window-containing spans through `assert_per_file_bounds`
  and each bound-checker; the four span instants pinned from string constants
  restated in the test module, independently of the implementation.
- The approved effective-N formula, per-pair reporting, both holdout floors at
  and either side of the boundary, and eleven invalid validation-floor shapes.
- Pair normalisation across seven JPY spellings and four non-JPY spellings,
  universe rejection, and injectivity over `PAIRS_20`.
- Status refusal for the playbook §10 set and for separator/case variants;
  forbidden statuses as artifact **values**; scrubber evasions (extra benign
  dict, columnar arrays, list-of-lists, whitespace key); artifact-name escape.
- A regression asserting the eight committed `artifacts/m15_gate3a/*.json`
  files remain scrub-clean under the tightened scrubber.

## 4. Deliberate redundancy

Two pairs of guards overlap by design, so removing either one alone does not
change behaviour:

- B-1: the `nanosecond` attribute check and the plain-datetime equality check.
- F-2/R-6: the per-key input `math.isfinite` and the derived-output finite
  check.
- R-9: the bare-filename check and the separator check.

Single-guard mutations of these are therefore *equivalent mutants*, not test
gaps. Removing **both** members of a pair is caught by the suite in every case,
which is the property that matters — verified by probe, not by argument.

## 5. Non-authorisation

This note authorises nothing. It does not accept the source audit, does not
adopt a dataset or forward epoch, and does not start the gate-3a continuation.
The next step is an **independent re-check** of this fix, performed in a session
separate from the one that wrote it. Forward-epoch adoption remains
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`;
`PRODUCTION_READINESS_NOT_CLAIMED` and `NO_EXECUTION_PERFORMED` remain in force.
