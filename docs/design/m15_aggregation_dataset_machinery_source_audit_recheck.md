# Independent source-audit re-check — F-1…F-5 targeted fixes (PR #434)

- **Document class:** doc-only Gate-decision record. Judges the technical state
  of the merged M15 gate-3a machinery. Executes nothing; authorises nothing.
- **Audit target:** master `697a1cf399e7d44617f78c3300ce2d97bc74d4ce`; the fix
  under review is PR #434, merge commit
  `5701ce8e6c893a92efdc58f902c7345fe265b5b1`.
- **Predecessor:** `docs/design/m15_aggregation_dataset_machinery_source_audit_fable5.md`
  (PR #433) — verdict `..._SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`,
  blockers F-1…F-5, optional hardenings O-1/O-2/O-3.
- **Risk tier:** Amber (`docs/governance/autonomous_development_policy.md`
  §3/§5). This record merges nothing and grants no gate.

## Statuses

- **Required final status (playbook §4, exactly one):**
  **`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`**
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_AGGREGATION_DATASET_MACHINERY_TARGETED_FIXES_PROPOSED`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** ·
  **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `PRODUCTION_READY`,
`READY_FOR_LIVE`, `M15_AUTHORISED`, `H1_AUTHORISED`, `H2_STARTED`,
`PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`,
`DEPLOYABLE` appear in this document only inside prohibition lists.

---

## 1. Executive verdict

**Containment is intact and no guard was loosened.** The fix diff adds two
`import math` statements and otherwise consists solely of new `raise` paths and
tightened predicates. No route to real-data read, derivation, validation,
holdout, training, inference, execution, broker/live/paper, external storage,
model binaries, or a CLI entry point is reachable from the package. PR #433's
containment conclusion re-derives independently.

**F-2, F-3, F-4 and F-5 are correctly fixed** within their stated scope, each
confirmed by probes run against the merged source.

**F-1 is NOT fixed for the input type the real pipeline produces.** The
alignment guard reads `.second` and `.microsecond` only. A `pandas.Timestamp`
is a `datetime` **subclass** that stores nanoseconds outside both fields, and
`.replace(second=0, microsecond=0)` preserves them — so ns-bearing rows pass
the guard *and* carry the nanosecond into the bucket key. Reproduced: fifteen
such rows yield an `eligible=True` bar whose bucket start is not a 15-minute
boundary, and the same fifteen minutes supplied twice (ns=0 and ns=500) yield
**two eligible bars for one 15-minute window**. This is the original F-1 false
eligibility, reachable through the real loader path
(`train_lgbm_models.py:508` builds ns-resolution timestamps via
`pd.to_datetime(..., utc=True)`, surfaced by `Real365dBaProvider.pair_frame`).
No gate-3a test supplies a pandas timestamp.

Reading the machinery against the frozen contract and the **committed** gate-3a
artifact specs surfaced four further gate-critical defects that F-1…F-5 never
covered. This re-check therefore **blocks** the gate-3a continuation:

| # | Defect | Why it blocks |
| --- | --- | --- |
| **B-1** | F-1 defeated by `datetime` subclasses carrying sub-microsecond resolution (`pandas.Timestamp`) | Reinstates the original false eligibility on the realistic input type |
| **B-2** | `assert_per_file_bounds` certifies reversed ts bounds as `PROVEN_NO_DEAD_WINDOW_OVERLAP` | This *is* the machine-checkable T-7 no-overlap proof the continuation must emit |
| **B-3** | `effective_n` diverges, fail-open, from the committed **APPROVED** per-pair spec and crosses the frozen 400 floor | Governs holdout acceptance; the divergence is not conservative |
| **B-4** | Pip authority is case-sensitive and universe-unbound; the machinery documents a fail-closed guarantee it does not have | 100× scale error on non-canonical JPY spellings — the INV-1 class that invalidated the M1 lineage |
| **B-5** | Validation floors accepted unvalidated: `SAMPLE_SUFFICIENT` on **zero events** with a NaN or non-positive floor | Same NaN-comparison class F-4 was raised to fix, one function away |

Verdict:
**`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`**.
No rewrite is warranted — the architecture is sound, containment is clean, and
every blocker is a small, precisely scoped change.

## 2. Independence and method

- Performed in a session **separate from the one that authored the F-1…F-5
  fixes** (policy §12). This session merged PR #434 but did not write it.
- PR #434's description, commit message and fix report were **not** accepted as
  evidence. Every finding below rests on the merged source, a committed
  artifact, or a probe the lead reproduced itself.
- **Four independent audit roles** ran as subagents, each given the source, diff
  and contract and **not** the other roles' conclusions (policy §13.2):
  contract/data-boundary; adversarial/bypass (briefed to argue the fixes are
  incomplete); test adequacy and mutation sensitivity; import graph and
  forbidden routes.
- The lead re-derived **every blocker and every required fix** with its own
  probes before recording it. Nothing was accepted on a subagent's authority and
  no finding was settled by majority (policy §13.7). One subagent's severity
  call was overridden on the evidence: the pip-authority defect was raised from
  REQUIRED_FIX to a blocker (B-4), because this repository has already had a
  JPY pip-size error invalidate a completed run.
- Materials: all 8 modules under `scripts/m15_gate3a/`, all 8 test modules,
  `git show 5701ce8` including removed lines, the PR #433 audit, the frozen
  pre-registration contract, the gate-4 design audit, the gate-3a epoch record,
  the eight committed `artifacts/m15_gate3a/*.json` specs, and playbook §4.
- Synthetic literals only. No real data read, no derivation, no checksum, no
  spread computation, no validation, no holdout, no training, no inference, no
  execution. The working tree was unmodified throughout (`git status
  --porcelain` empty at every step); probes and mutation copies lived only in a
  scratch directory.

## 3. F-1…F-5 — individual verdicts

### F-1 — duplicate / sub-minute rows must not create eligibility · **PARTIALLY FIXED — see B-1**

Fixed for plain `datetime`. `aggregation.py:94-111` records the UTC-normalised
minute in `seen_minutes[bucket]` and raises on any repeat; `:69-70` rejects
`second != 0 or microsecond != 0`.

| Probe (plain `datetime`) | Result |
| --- | --- |
| 15 distinct minute-aligned rows | `eligible=True`, `n_source_bars=15` |
| 14 distinct rows | `eligible=False`, `n_source_bars=14` |
| 14 distinct + 1 duplicate (count = 15) | `AggregationError: duplicate source minute …` |
| duplicate re-expressed in `+09:00` | caught — normalisation precedes the set test |
| `second=30` / `microsecond=1` | `… is not minute-aligned` |
| unsorted 15 rows | eligible; OHLC taken in true time order |
| gap-report flags | `imputation=False`, `synthetic_weekend_bars=False`, `mid_price_constructed=False` |

**Defeated for `datetime` subclasses with finer resolution — see B-1.**

### F-2 — non-finite prices must fail closed before output · **FIXED (inputs)**

`aggregation.py:71-78` rejects `bool`, non-numeric types, and any value failing
`math.isfinite` before a bar is constructed. Probed exhaustively: all **8** side
keys × {`NaN`, `+inf`, `-inf`} → 24/24 rejected; `bool` and numeric strings also
rejected; `numpy.float64` NaN rejected. No non-finite input can reach
`max()`/`min()`/open/close.

The *output* side is unguarded: two finite inputs can produce a non-finite
result (`spread_close = inf` from `ask_c = 1.7e308`, `bid_c = -1.7e308`). → R-6.

### F-3 — effective-N role handling must fail closed · **FIXED (core)**

`effective_n.py:51-52` raises on any role outside `{holdout, validation}`
(probed: `"train"`, `""`, `"Holdout"`, `None`). `role="validation"` no longer
returns `SAMPLE_SUFFICIENT` by default — it returns `NOT_EVALUATED_AT_THIS_ROLE`
(probed at `raw=999999`). Holdout floors are unchanged and value-pinned:
`raw=999 → INSUFFICIENT_SAMPLE`, `raw=1000 → SAMPLE_SUFFICIENT`,
`raw=1000, overlap=1.0 → INSUFFICIENT_SAMPLE`. Raw count, `rho_h` and `rho_x`
are preserved in the record.

The prescribed fix is satisfied. Three *new* problems in the same function —
the formula divergence, the unvalidated floors, and the unauditable
`horizon_bars` override — are recorded as **B-3**, **B-5** and **R-1**.

### F-4 — non-finite spreads must fail closed · **FIXED**

`cost_schema.py:85-90` rejects `bool` and non-numerics, then anything failing
`math.isfinite` or `< 0`. Probed: {`median`, `p90`, `p95`} × {`NaN`, `+inf`,
`-inf`, negative, `bool`} → 15/15 rejected; finite non-negative accepted. p95
remains mandatory; padding `0.3` and cell `0.5` remain unloosenable; pip is
cross-checked against the authority (`USD_JPY` with `0.0001` rejected, `0.01`
accepted).

### F-5 — naive datetimes must fail closed · **FIXED**

Both parsers reject tz-naive datetimes and offset-less ISO strings and convert
explicit offsets deterministically — `no_overlap._parse` (`:32-41`) and
`warmup.assert_load_allowed` (`:49-59`). Probed in both: naive datetime,
offset-less ISO, empty string, `None`, int epoch all fail closed; `Z` and
`+00:00` accepted; `2026-04-25T08:00:00+09:00` (= `2026-04-24T23:00Z`) correctly
rejected as pre-forward while `2026-04-25T09:00:00+09:00` (= `00:00Z`) is
accepted. The same instant in two offsets yields the same decision, so
behaviour is independent of host timezone and DST.

**Required boundary instants — all correct:**

| Instant | `assert_design_bounds` (as ts_max) | `assert_forward_bounds` (as ts_min) |
| --- | --- | --- |
| `2026-02-28T23:59:59Z` | accept (inclusive) | reject (< floor) |
| `2026-03-01T00:00:00Z` | reject (> DESIGN_END) | reject |
| `2026-04-24T23:59:59Z` | reject | reject (< floor) |
| `2026-04-25T00:00:00Z` | reject | accept (inclusive) |

`DESIGN_START` is inclusive at `2025-04-25T00:00:00Z` and rejects one second
earlier. Constants match T-7 and the committed `no_overlap_proof.json`.

## 4. O-1 / O-2 / O-3 — individual verdicts

PR #433 classified all three as optional, not blockers. That framing is
retained: nothing in this section is a blocker on its own.

### O-1 — status normalisation · **APPLIED, PARTIAL, AND UNREACHABLE**

`guards.py:93-101` normalises with `strip().upper()`, so the casing and
trailing-whitespace variants PR #433 probed are now refused. Residual gaps, all
probed: separator variants pass (`"production ready"`, `"PRODUCTION-READY"`,
`"Tier  1"`, `"PASSED"`); zero-width, homoglyph and fullwidth variants pass;
non-`str` inputs are never inspected; and `FORBIDDEN_STATUSES` is **narrower
than playbook §10**, omitting `READY_FOR_LIVE`, `ROBUST` and `DEPLOYABLE`
(probed: each accepted). That set was not touched by PR #434 — it is inherited
from PR #432, and playbook §10 was recorded later in PR #435, so this is
governance-vs-code drift rather than a regression.

More significant than the normalisation quality: **`assert_status_allowed` has
zero non-test callers**, and the artifact scrubber inspects *keys*, not status
*values*. Probed: `assert_gate3a_clean({"result": "PASS", "tier": "Tier 1",
"readiness": "PRODUCTION_READY", "epoch": "NEW_EPOCH_ADOPTED", "byte":
"BYTE_ADMISSIBLE"})` passes clean. The forbidden-status control does not exist
on any reachable write path. → **R-4**.

### O-2 — row-like scrub heuristic · **APPLIED, WEAK**

`artifacts.py:63-89` flags a list holding ≥ 2 dicts that *all* carry ≥ 6 numeric
fields. It catches the committed test case and, via the base scrubber's key
names, real `bid_*`/`ask_*` rows. It is defeated by, all probed:

| Evasion | Result |
| --- | --- |
| `[row, row, {"label": "x"}]` — one benign dict | **passes** (`all()` short-circuits) |
| single 8-numeric record | passes (below the 2-record threshold) |
| ≥ 2 records × 5 numeric fields | passes (below the 6-field threshold) |
| numeric values as strings | passes (`_numeric_field_count` counts only `int`/`float`) |
| list-of-lists OHLC rows | passes (no dicts, heuristic never fires) |
| columnar parallel arrays under generic keys `o/h/l/c` | passes — unbounded raw-series smuggling |
| key `"sharpe "` (trailing space) | passes — the key matcher uses `.lower()` but not `.strip()`, inconsistent with O-1's own normalisation |
| renamed metrics (`sharpe_ratio`, `pnl_by_pair`, `holdout_sharpe`) | passes (exact-key denylist) |

Legitimate metadata correctly survives (cost entries, 20-file inventories), and
the base scrubber still rejects forbidden keys at depth, credential keys, env
dumps, local paths and known raw-row key names. PR #433's recorded mitigation —
"nothing in the package *produces* row-shaped data into artifacts" — still
holds. → **R-5**.

### O-3 — half-open boundary semantics · **NOT APPLIED — decision UPHELD, rationale CORRECTED**

Not applying O-3 was right: half-open next-day semantics would move `DESIGN_END`
and conflict with the committed `no_overlap_proof.json`. The *rationale*
recorded in PR #434 — that the current bounds "already fail closed
conservatively" — is **not accurate at the trailing edge**. Probed:
`assert_no_dead_window("2026-04-24T23:59:59.500000Z", …)` reports no
intersection, because `_intersects_dead_window` short-circuits on
`ts_min > DEAD_END`. Exposure is limited — `assert_design_bounds` and
`assert_forward_bounds` both close the hole via their own comparisons — but the
sliver stops being purely hypothetical once B-1 lets sub-second timestamps
reach a bar. → **N-1**.

## 5. Containment / import graph — CLEAN

Eager import closure is **stdlib only** (`__future__`, `collections.abc`,
`dataclasses`, `datetime`, `hashlib`, `json`, `math`, `pathlib`, `re`, `typing`)
plus exactly three internal symbols: `ml_step4.data_adapter.pip_size_for` and
`ml_step4.evidence.repo_root` / `scan_payload` / `serialise` (which reaches
`foundation_t2.constants`). A runtime probe importing all eight modules confirms
`pandas`, `numpy`, `lightgbm`, `sklearn`, `joblib`, `torch`, `pickle`,
`requests`, `httpx`, `socket`, `subprocess`, `boto3`, `oandapyV20`, `argparse`
and `pyarrow` are **not** loaded. Reverse callers: only `tests/m15_gate3a/`.

| Route | Verdict |
| --- | --- |
| real-data read · M15 derivation from bytes | NOT REACHABLE — no `open`/`read_*`/`glob`/`os.walk`; `aggregate_m15` takes an in-memory list |
| validation · holdout · training · inference | NOT REACHABLE — no model object, no metric computation; supplied scalars only |
| execution · subprocess · `exec`/`eval` | NOT REACHABLE |
| broker / live / paper · external storage | NOT REACHABLE — no `src.` import, no network, no env read |
| model binary | NOT REACHABLE — no pickle/joblib; the writer rejects any name not ending `.json` |
| CLI / `__main__` | NOT REACHABLE |
| file **write** | REACHABLE **by design** — `write_metadata_artifact`, `.json`-only, scrub-gated, zero non-test callers |

Protected-path refusal holds against `..` traversal (shallow and deep), mixed
separators, `.` segments, Windows case variants, trailing dot/space, and
relative paths from the repo root. It is defeated by one alias form → **R-3**.

## 6. Findings

### BLOCKERS — must be fixed before any gate-3a continuation

**B-1 — F-1 is defeated by `datetime` subclasses carrying sub-microsecond
resolution (`pandas.Timestamp`).**
`aggregation.py:69` tests only `ts.second` and `ts.microsecond`;
`_bucket_start` (`:49-51`) floors with `ts.replace(...)`, which on a subclass
returns that subclass and preserves nanoseconds. Reproduced by the lead:

```
pd.Timestamp("2025-06-02 00:00:00.000000500+0000")
  .second == 0, .microsecond == 0, .nanosecond == 500      # alignment check passes
  .replace(minute=0, second=0, microsecond=0)
      -> Timestamp('2025-06-02 00:00:00.000000500+0000')   # ns survives the floor
```

| Probe | Result |
| --- | --- |
| 15 rows all at `ns=500` | **one bar, `n_source_bars=15`, `eligible=True`, bucket ts `00:00:00.000000500` — not a 15-minute boundary** |
| the same 15 minutes twice (`ns=0` and `ns=500`) | **two `eligible=True` bars for one 15-minute window** (`n_buckets_emitted=2, n_eligible=2`) |
| 15 aligned rows + one at `00:05 + 1ns` | 2 buckets; minute `00:05` counted in both; no duplicate error |
| control: plain `datetime`, `microsecond=1` | correctly raises `… is not minute-aligned` |

Reachable, not theoretical: `scripts/train_lgbm_models.py:508` builds
timestamps with `pd.to_datetime(df["time"], utc=True)` (ns resolution) and
`Real365dBaProvider.pair_frame` surfaces that frame; any `df.to_dict("records")`
glue in the continuation feeds exactly this type. **No gate-3a test supplies a
pandas timestamp.** Fix: normalise to a plain `datetime` at the boundary (or
reject `datetime` subclasses whose resolution exceeds microseconds), assert the
bucket key is 15-minute aligned, and add regression tests using
`pandas.Timestamp` inputs.

**B-2 — `assert_per_file_bounds` certifies a dead-window file as proven-clean
when its ts bounds are reversed.**
`no_overlap.py:78` gives `assert_no_dead_window` a `hi < lo` check.
`assert_design_bounds` (`:48-60`) and `assert_forward_bounds` (`:63-71`) — the
two functions `assert_per_file_bounds` actually calls (`:97-100`) — do not.
Reproduced:

```
assert_per_file_bounds(
    [{"ts_min_utc": "2026-05-01T00:00:00Z", "ts_max_utc": "2026-03-15T00:00:00Z"}],
    role="forward")
-> {'role': 'forward', 'files_checked': 1, 'result': 'PROVEN_NO_DEAD_WINDOW_OVERLAP'}
```

The file's true span `2026-03-15 … 2026-05-01` lies inside the dead window for
40 days; `_intersects_dead_window` (`:45`) short-circuits on
`ts_min > DEAD_END`. The same inputs through `assert_no_dead_window` correctly
raise `ts_max < ts_min`, so the missing check is an oversight, not a design
choice. This function is the machine-checkable T-7 proof the continuation must
emit, and an inverted per-file bound is a plausible transcription error rather
than only an attack. **No test covers reversed bounds.** Fix: add `if hi < lo:
raise` to both bound-checkers, with a regression test.

**B-3 — `effective_n` diverges, fail-open, from the committed APPROVED
estimator spec and can cross the frozen 400 floor.**
`artifacts/m15_gate3a/effective_n_estimator_spec.json` (status `APPROVED_SPEC`)
fixes `N_eff_pair = N_raw_pair / rho_h_pair`, then
`N_eff = (Σ N_eff_pair) / rho_x`, and mandates
`granularity: [portfolio, per_pair]`. `effective_n.py:64-66` computes a single
portfolio scalar `raw / (rho_h · rho_x)` from one aggregate `overlap_fraction`.
These are not equivalent when overlap varies across pairs, and the difference
is not conservative. Re-derived by the lead:

| | pair A `N=50, overlap=0.0` · pair B `N=8000, overlap=1.0` |
| --- | --- |
| approved spec | `50/1 + 8000/24 = 383.33` → below 400 → `INSUFFICIENT_SAMPLE` |
| current code (`raw=8050, overlap=0.5, n_pairs=2`) | `N_eff = 644.00` → `SAMPLE_SUFFICIENT` |

Holdout acceptance would be granted exactly where the approved spec forbids it,
and the helper cannot emit the mandated `per_pair` granularity. Worse for
detection: `tests/m15_gate3a/test_effective_n.py:25` **pins the divergent
formula** (`5000 / (12.5 * 4.8)`), so the suite entrenches the defect rather
than catching it. Fix: implement the per-pair formula, report both
granularities, and re-pin the tests to the approved spec.

**B-4 — pip authority is case-sensitive and universe-unbound, and the machinery
documents a fail-closed guarantee it does not have.**
`data_adapter.py:55` is `pair.endswith("_JPY")`. Reproduced through the gate-3a
public API:

| input | pip size | consequence |
| --- | --- | --- |
| `USD_JPY` | `0.01` | correct |
| `usd_jpy`, `USDJPY`, `"USD_JPY "` | `0.0001` | **100× wrong** for a JPY cross |
| `XXX_YYY`, `NOT_A_PAIR` | `0.0001` | unknown pair silently scaled |

`aggregate_m15(rows, pair="usd_jpy")` stamps `pip_size = 0.0001` on every bar
and into the gap report; `to_pips(0.02, "usd_jpy")` returns `200.00` instead of
`2.00`; `validate_cost_table(pair="usd_jpy", pip_size=0.0001)` returns
`COST_TABLE_SCHEMA_VALID` — the cross-check cannot detect the error because both
sides consult the same function. Neither module binds `pair` to `PAIRS_20`,
although a canonical uppercase list exists in the repo.

`pip_size_for` itself behaves as *its own* docstring and
`tests/ml_step4/test_pip_size.py:80-81` specify (unknown → `0.0001`, the
convention's `else` branch). The defect is in the audited machinery's claims:
`aggregation.py:9` says "fail-closed on unknown pair" and `:90` says
"fail-closed FIRST (unknown pair -> PipSizeError)" — **both false**. PR #433 §4
and §8 repeated the same incorrect claim; this re-check corrects the record.
Given that a JPY pip-size error already invalidated the M1 `365d_BA` lineage,
this must close before real per-pair scaling. Fix: bind `pair` to canonical
`PAIRS_20` membership at the gate3a boundary and correct the two false
docstrings.

**B-5 — validation floors are accepted unvalidated; `SAMPLE_SUFFICIENT` on zero
events.**
`effective_n.py:74-82` uses any supplied floor verbatim and defaults the
unsupplied one to `0`/`0.0`. Reproduced:

```
effective_n(0, overlap_fraction=1.0, cross_pair_corr=1.0, n_pairs=20,
            role="validation", validation_raw_floor=float("nan"))
  -> verdict = SAMPLE_SUFFICIENT, effective_n = 0.0
effective_n(0, ..., validation_raw_floor=-1, validation_neff_floor=-1.0) -> SAMPLE_SUFFICIENT
effective_n(1000, overlap_fraction=1.0, cross_pair_corr=1.0, n_pairs=20,
            role="validation", validation_raw_floor=1000)
  -> N_eff = 2.083, SAMPLE_SUFFICIENT   # raw substitutes for N_eff
```

The NaN case works because `0 < nan` is `False` — the identical
comparison-with-NaN class F-4 was raised to fix, left unfixed one function away.
Supplying one floor silently zeroes the other, contradicting Ruling 11 and the
spec's `failure_handling` ("raw **or** effective below the minimum"). The
applied floors are not echoed in the record, so a validation
`SAMPLE_SUFFICIENT` is not self-describing. Fix: require both floors together,
reject non-finite and non-positive floors, and record the floors used.

### REQUIRED FIXES — land with the blockers, before the continuation

- **R-1 — `horizon_bars` override is unauditable and flips the verdict.**
  `HORIZON_M15_BARS = 24` is frozen by Ruling 6 but is an overridable kwarg.
  Reproduced: `effective_n(1000, overlap_fraction=1.0, cross_pair_corr=0.0,
  n_pairs=1)` → `INSUFFICIENT_SAMPLE` (`N_eff = 41.7`); adding
  `horizon_bars=1` → `SAMPLE_SUFFICIENT` (`N_eff = 1000.0`). The record carries
  `rho_h` but **not** `horizon_bars`, so an overridden horizon is
  indistinguishable in the emitted artifact from zero overlap. Pin the horizon
  to the frozen value for the holdout role, and echo it in the record.
- **R-2 — finite-but-impossible rows are absorbed into eligible bars.**
  `_validate_row` checks type and finiteness only. Reproduced on a complete
  15-row bucket: one row with `bid_h=0.0, bid_l=9.0` yields a normal-looking bar
  (`bid_h=1.1002`, `bid_l=1.0998`) with `eligible=True` — the corrupt row is
  swallowed by `max()`/`min()` leaving no trace. A crossed closing quote
  (`ask_c < bid_c`) yields `spread_close = -0.001000` with `eligible=True`,
  feeding a negative quoted spread into the §5 cost model. This is the F-2
  failure mode one step out. Fix: assert `h >= max(o, c)`, `l <= min(o, c)`,
  `h >= l` per side, and `ask_* >= bid_*` per row.
- **R-3 — `refuse_real_path` is defeated by the `\\?\` extended-length alias.**
  Reproduced: the plain protected path is refused; `\\?\` + the same path is
  **allowed**, while `os.path.samefile` confirms both name the same directory
  (`resolve()` retains the prefix, so equality and `.parents` both fail). Fix:
  strip a leading `\\?\` / `\\?\UNC\` before comparison, or compare by
  `os.stat` identity.
- **R-4 — the forbidden-status control is unreachable.**
  `assert_status_allowed`, `assert_synthetic_only` and
  `assert_no_forbidden_operation` have zero non-test callers, and the scrubber
  inspects keys, not status values. Reproduced: an artifact payload carrying
  `PASS` / `Tier 1` / `PRODUCTION_READY` / `NEW_EPOCH_ADOPTED` /
  `BYTE_ADMISSIBLE` as *values* passes clean and would be written. Also widen
  the set to match playbook §10 (`READY_FOR_LIVE`, `ROBUST`, `DEPLOYABLE`) and
  normalise separator variants. Wire the check into the write path.
- **R-5 — the O-2 heuristic is defeated by one extra dict.**
  `artifacts.py:84-87` uses `all(...)` over the dicts in a list, so
  `[row, row, {"label": "x"}]` passes — precisely the shape O-2 exists to catch.
  Fix: count qualifying records
  (`sum(1 for d in dict_items if _numeric_field_count(d) >= 6) >= 2`), add a
  columnar check, and apply `.strip()` in the key matcher for consistency with
  O-1.
- **R-6 — finite inputs can produce a non-finite output.** `aggregation.py:140`
  computes `spread_close = ask_c - bid_c` unguarded; reproduced
  `spread_close = inf` from two finite inputs. Apply `math.isfinite` to derived
  outputs, not only inputs.
- **R-7 — gap report is bucket-granular and does not match the committed
  inventory schema.** Reproduced: rows at `00:00Z` and `00:29Z` (a true
  28-minute hole) give `{total_missing_source_minutes_within_emitted_buckets:
  28, missing_whole_buckets: 0, max_gap_minutes: 0}`.
  `artifacts/m15_gate3a/design_m15_inventory.json` requires `gap_report:
  {missing_minute_count, max_gap_minutes}`; the code emits neither that key name
  nor a consistent value. Contract §4 requires count **and** max gap.
- **R-8 — cost-table schema cannot see units, and the formula field is
  unvalidated.** Reproduced: a price-unit table (`median_spread=0.00008`) and a
  pip-unit table (`median_spread=0.8`) both return `COST_TABLE_SCHEMA_VALID` — a
  10,000× difference the schema cannot detect, while padding and cell are
  explicitly pips. `all_in_cost_formula="median + 0.0 + 0.0"` alongside correct
  `0.3`/`0.5` pins also validates. Non-monotone quantiles
  (`median=0.0009 > p90=0.0002 > p95=0.0001`) validate, which would make the
  mandatory p90 stress *milder* than the base case. A one-entry table validates,
  so 20 × 3 coverage is unenforced. Fix all four before the tables are produced.
- **R-9 — artifact `name` escapes `out_dir`.** `write_metadata_artifact(base,
  "../escaped.json", …)` wrote outside the target directory (reproduced in the
  scratchpad); `out.mkdir(parents=True)` also runs before the target refusal, so
  a refused write can leave a stray directory. Protected targets remain refused.
  Fix: reject names containing a separator or `..`; move `mkdir` after both
  refusals.
- **R-10 — test gaps that would let the blockers regress silently.** See §7:
  the aggregation **value path** is unpinned (a high↔low swap and a spread-sign
  inversion both survive the full suite), `math.isfinite` is exercised on only
  4 of 8 side keys, the microsecond limb of the alignment guard is unpinned,
  the within-bucket sort is unpinned, `DEAD_START` can move two weeks
  undetected, and `N_EFF_HOLDOUT_FLOOR = 400` is not pinned by any
  verdict-driving test.

### NON-BLOCKING OBSERVATIONS

- **N-1 — O-3 sub-second sliver** at the dead window's trailing edge in
  `assert_no_dead_window` (§4). Both role-specific entry points close it; it
  becomes reachable only in combination with B-1.
- **N-2 — `guards.py:4-5` overstates its own role** ("every entry point …
  routes through these guards") — see R-4.
- **N-3 — `WarmupPolicy.assert_load_allowed` never calls `validate()`**, so an
  invalid policy (`w_bars=0` with a 50-bar lookback) still authorises loads.
- **N-4 — inconsistent `bool` strictness**: `effective_n` accepts
  `raw_event_count=True` as `1`, while aggregation and cost schema reject bools
  explicitly.
- **N-5 — protected-prefix set is only two entries.** `artifacts/m15_gate3a/`
  (named by playbook §9 as a prior evidence directory), stage24/stage25,
  `artifacts/oanda_archive_*`, `firstrun_730d_ba`, `firstrun_3650d_ba` and
  `data/` (the real M1 archive root) are all writable via
  `write_metadata_artifact`. An integrity, not a leakage, concern — there is no
  read counterpart.
- **N-6 — namespace adjacency to the trainer.** `aggregation` and `cost_schema`
  eagerly import `ml_step4.data_adapter` for a four-line function; that module
  also houses `Real365dBaProvider` and a lazy `train_lgbm_models` hook. Nothing
  is invoked and nothing heavy loads, so containment holds in the call-graph
  sense; moving `pip_size_for` to a leaf module would make it hold in the
  namespace sense too.
- **N-7 — two tests are cwd-dependent** (`test_guards.py:26-27`,
  `test_artifacts_scrub.py:75` pass relative protected paths). 91/91 pass from
  the repo root; two fail from an unrelated cwd.
- **N-8 — no automated containment test** freezes the clean import result
  against future drift.
- **N-9 — `RealDataRefusedError` is defined twice** (`guards.py:57` and in
  `data_adapter`) as unrelated classes; a cross-module `except` will not match.
- **N-10 — contract §4 asks for an open-side spread variant**; the bar records
  only `spread_close`. No information is lost (`bid_o`/`ask_o` are present).
- **N-11 — `horizon_bars`/`n_pairs` extremes raise `OverflowError`** rather than
  `EffectiveNError`. Still fail-closed, wrong exception type.
- **N-12 — the "+39 regression tests" count is inflated.** 30 of the 39
  genuinely fail against the pre-fix source; 9 pass pre-fix, and 6 of those are
  weaker restatements of pre-existing tests. The fixes are real; the count
  should be restated as 30 defect-proving tests.

## 7. Test adequacy

The suite is green (91/91 from the repo root) and every one of F-1…F-5 has at
least one test that provably fails against the pre-fix source — verified by
reverting each module to `5701ce8^` in a scratch copy and re-running. But
mutation testing (70 mutations against scratch copies; the repository was never
modified) shows the **guards are only half-pinned and the aggregation value
path is essentially unverified**:

| Mutation | Detected? | Consequence if it regressed |
| --- | --- | --- |
| `ts.microsecond` limb dropped from the alignment check | **MISSED** | recreates F-1 verbatim |
| `math.isfinite` skipped for `bid_l` / `bid_c` / `ask_o` / `ask_h` | **MISSED** (4 of 8 keys untested) | recreates F-2 on half the fields |
| `max()` ↔ `min()` on `bid_h` | **MISSED** | highs and lows silently swapped |
| `spread_close` sign inverted | **MISSED** | negative quoted spreads emitted |
| within-bucket `sorted(...)` removed | **MISSED** | open/close taken from input order |
| `DEAD_START` moved to `2026-03-15` | **MISSED** | two-week hole in the dead window |
| `DESIGN_START` check removed; `DEAD_END`/`FORWARD_FLOOR` shifted a day | **MISSED** | span floors unenforced |
| `if hi < lo` removed from `assert_no_dead_window` | **MISSED** | reversed spans accepted (cf. B-2) |
| `N_EFF_HOLDOUT_FLOOR 400 → 100` | **MISSED** | the frozen sample floor is weakenable |
| `v < 0` removed from the spread check; bool spread accepted | **MISSED** | negative/bool spreads validate |
| `astimezone(UTC)` → `replace(tzinfo=UTC)` in the `warmup` string path | **MISSED** | a pre-forward load admitted via a non-UTC offset |
| O-2 threshold `6 → 7` / `6 → 8`; `all()` → `any()` | **MISSED** | heuristic thresholds unpinned |

Caught, by contrast: distinct-minute removal, alignment-check removal,
whole-guard `isfinite` removal, `_SIDE_KEYS` truncation, bool prices,
`FULL_BUCKET_SOURCE_BARS 15→14`, `BUCKET_MINUTES 15→5`, unknown-role removal,
validation default → SUFFICIENT, raw floor `1000→500`, horizon `24→12`, dropping
`rho_x`, padding `0.3→0.4`, p95 removal, all four F-5 reverts, `strip()`/`upper()`
removal, O-2 removal and threshold widening, protected-prefix removal.

Two structural weaknesses matter most: **the suite entrenches B-3**
(`test_effective_n.py:25` pins the divergent formula) and **B-1/B-2 are
untested** — no test supplies a `pandas.Timestamp`, and none supplies reversed
ts bounds. Equivalent mutants (`n == 15` → `n >= 15`, removal of the residual
`n > 15` guard, the redundant naive check in `_bucket_start`) were correctly
identified as unreachable and are not counted as gaps.

## 8. Non-authorisation

This document authorises nothing. It does not adopt a dataset epoch, does not
adopt the forward epoch, does not permit any real data read or derivation, and
does not start the gate-3a continuation. No real data was read, no M15 data was
derived, no checksum or spread was computed, no validation or holdout was
evaluated, no model was trained, no prediction was generated, and nothing was
executed. `artifacts/m15_gate3a/` and all prior evidence directories are
unchanged; stage24/stage25 artifacts are clean; no source or test file was
modified by this audit.

Per policy §12, the AI that performed this audit may not give the final gate
ruling — acceptance or rejection is a human + ChatGPT decision.

## 9. Recommendation for the next gate

1. **One targeted-fix Work PR** (policy §14 — code, tests, docs, internal audit
   and CI in a single PR, not fragmented) closing **B-1…B-5** and
   **R-1…R-10**, each with a failing-before / passing-after regression test.
   Minimum new coverage: `pandas.Timestamp` inputs; reversed ts bounds; the
   per-pair effective-N formula re-pinned to the approved spec; non-canonical
   pair spellings; value-pinned OHLC and `spread_close`; `isfinite` on all
   eight side keys; the four span constants pinned independently;
   `N_EFF_HOLDOUT_FLOOR` pinned by a verdict-driving case.
2. **One independent source-audit re-check Gate-decision PR** on the merged
   result, performed in a session separate from the fix author.
3. Only if that re-check accepts may a **separately authorised gate-3a
   continuation** read or derive design-span data.

Forward-epoch adoption remains
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`.
`PRODUCTION_READINESS_NOT_CLAIMED` and `NO_EXECUTION_PERFORMED` remain in force.
