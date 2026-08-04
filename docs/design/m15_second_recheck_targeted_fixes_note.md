# M15 gate-3a machinery — targeted fixes for BL-1…BL-5 and RF-1…RF-11

**Status:** `M15_AGGREGATION_DATASET_MACHINERY_SECOND_RECHECK_FIXES_PROPOSED`
**Always-binding:** `PRODUCTION_READINESS_NOT_CLAIMED`, `NO_EXECUTION_PERFORMED`
**Forward epoch:** `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
**Risk tier:** Amber (source changes to gate-3a machinery) — **do not self-merge**
**Kind:** Work PR (policy §14) — code + tests + docs + internal audit, one objective

This PR does **not** grant source-audit acceptance to itself. The official gate
status remains the PR #439 verdict
`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
until a **genuinely independent** re-check — a separate session with no
implementation context — accepts these fixes.

## 0. What was and was not read

No real data was read. No M15 was derived. No real checksum or spread was
computed. Nothing was trained, validated, evaluated, inferred or executed. No
broker, paper, live, external-storage or credential path was touched. `uv.lock`
is unchanged. No frozen contract constant was altered — where a contract answer
was missing, the question is **referred**, not invented (§4, §7).

Two questions that looked like they needed real data were settled from
**committed in-repo evidence** instead:

* BL-4's crossed-quote policy, from `scripts/stage25_0a_build_path_quality_dataset.py`;
* BL-1's roster identity, from `artifacts/m15_gate3a/design_m15_inventory.json`.

## 1. Disposition of PR #441

PR #441 was **closed unmerged** as a non-independent diagnostic review. It was
authored in the same session as the PR #440 code it reviewed, so it does not
satisfy policy §12 and carries no gate authority. Its findings BL-1…BL-5 and
RF-1…RF-11 are treated here as **non-authoritative diagnostic input**: each was
re-derived from the source before being acted on, and two were reclassified on
that evidence (§7).

## 2. New modules

Two single-authority modules were added, because the defects were duplication
defects — the same decision made differently in five and two places.

| Module | Authority over | Replaces |
| --- | --- | --- |
| `scripts/m15_gate3a/timeutil.py` | Is this timestamp an exact UTC instant? | five independent `tzinfo is None` checks |
| `scripts/m15_gate3a/path_authority.py` | Does this path name a protected tree? | inline prefix-stripping + a capped ancestor walk |

## 3. BL-1 — the T-7 proof was returned on zero, duplicated or unbound evidence

**Defect.** `assert_per_file_bounds` returned `PROVEN_NO_DEAD_WINDOW_OVERLAP`
with `files_checked=0` when given a `Sequence` whose `__len__` and iteration
disagreed — and reported `expected_count=20` satisfied. `[one_file] * 20` also
satisfied a 20-file inventory. `checked` was never reconciled with
`len(files)`, and the proof said nothing about *which* files it saw.

**Fix.** The proof is now bound to real, distinct, canonical evidence:

* `_materialise` requires a concrete sequence, materialises it **twice**, and
  refuses unless `__len__`, both iteration passes and indexed access all agree;
* `_roster_report` canonicalises every record's `pair` through the pair
  authority, so alias spellings collapse (`eur/usd` duplicates `EUR_USD`), and
  requires the canonical roster to equal `PAIRS_20` **exactly** — no missing,
  duplicate or unknown pair;
* `filename` and `sha256`, the identity keys the committed
  `design_m15_inventory.json` declares, must be unique and well-formed when
  present;
* the returned record carries `expected_pairs`, `expected_pair_count`,
  `actual_pairs`, `actual_record_count`, `missing_pairs`, `duplicate_pairs` and
  `unknown_pairs`, and the same four figures appear in every refusal message;
* `expected_count` remains a caller cross-check — on its own it can no longer
  produce the token, because the roster binding runs regardless.

**Authority used.** `artifacts/m15_gate3a/design_m15_inventory.json` →
`required_schema_per_file` (`pair` = "one of PAIRS_20", `filename`, `sha256` =
"64-hex", `ts_min_utc`, `ts_max_utc`) and `required_aggregate_assertions`
(`file_count: 20`). Nothing was invented.

## 4. BL-2 — `tzinfo is None` is not Python's awareness test

**Defect.** Five sites (`aggregation.py:74`, `no_overlap.py:49,54`,
`warmup.py:53,58`) tested awareness with `ts.tzinfo is None`. A `tzinfo` whose
`utcoffset()` returns `None` leaves the datetime **naive** while
`tzinfo is None` is `False`; `astimezone(UTC)` then reinterprets the value in
the **host's local zone**. Reproduced: `aggregate_m15` *accepted* a bucket nine
hours wrong — not fail-closed — and the dead-window verdict became
host-dependent. This reopened the F-5 class.

**Fix.** All five sites route through `timeutil`, which:

* decides awareness by `utcoffset()`, the real test;
* refuses a `utcoffset()` that raises, returns a non-`timedelta`, or is not
  stable across two calls;
* converts by **subtracting the offset** from a component rebuild rather than
  calling `astimezone`, so the host zone cannot participate at all;
* always returns a plain `datetime` — a subclass cannot carry its own
  comparison semantics past the boundary;
* rejects sub-minute remainder held outside `.second`/`.microsecond`: the
  `.nanosecond` attribute (`pandas.Timestamp`) **and** a `timestamp()`
  round-trip that disagrees with the rebuilt minute.

That second limb is what the merged PR #440 note wrongly claimed the equality
check already gave (RF-7 / §7).

A structural test asserts no gate-3a timestamp module contains `astimezone(`,
`utcnow(`, `datetime.now(` or `time.localtime(`. An environment-variable probe
cannot prove absence — `TZ` needs `tzset`, which Windows lacks — but the
absence of the call can be checked directly.

## 5. BL-3 — the protected-path guard was defeated twice

**Defect.** (a) The extended-UNC prefix was matched as the literal
`"\\?\UNC\"`, but Windows treats it case-insensitively, so `\\?\unc\...`
reached `resolve()` unstripped and compared unequal to a directory
`os.path.samefile` called identical. (b) The ancestor walk was capped at a fixed
64 iterations and returned "allowed" on exhaustion — depth 63 REFUSED, depth 64
ALLOWED.

**Fix.** `path_authority` decides containment over the **complete** ancestor
chain (`Path.parents` is finite by construction, so there is no cap to exhaust),
folds the prefix case-insensitively, and refuses on every failure mode:
non-path types, empty strings, embedded NUL bytes, the device namespace
(`\\.\`), unresolvable spellings, and — RF-3 — a protected root that exists but
cannot be interrogated. Only `FileNotFoundError` counts as "genuinely absent";
the previous `protected.exists()` shortcut reported "absent" for a permission
error too and skipped the identity test entirely.

The depth regression is tested through the **identity** limb, not the name
limb: `sibling/../protected/d0/.../leaf` is not textually under `protected`
(pathlib keeps the `..`), so the walk must climb the whole chain.

## 6. BL-4 — crossed quotes abort the pair; the repo already ruled otherwise

**Defect.** A crossed quote (`ask < bid`) raised `AggregationError` and
abandoned the whole pair. This repository's committed
`scripts/stage25_0a_build_path_quality_dataset.py` already treats negative
spread as an expected **"data anomaly"** and drops-and-counts it per pair
(`:191` docstring, `:242-245` predicate, counter at `:220`, reported at
`:417`/`:424`, documented at `:612`). Gate-3a's abort was this package's own
stricter invention, incompatible with the precedent.

**Fix.** Adopt the precedent. `_is_crossed_quote` is checked in the aggregation
loop; the row is dropped and counted, and the gap report gains
`rows_ingested`, `rows_retained` and `dropped_crossed_quote_rows` — the drop is
never silent, and a pair whose rows were mostly or entirely dropped is visible
rather than presenting as merely sparse.

Three properties are preserved deliberately:

* **the minute is claimed before the drop**, so a dropped anomaly cannot be
  quietly substituted by a second record for the same minute;
* the bucket loses eligibility (15 distinct minutes are no longer present) and
  is never imputed or back-filled;
* **intra-side incoherence remains fatal.** A high below its own low, or a
  high/low failing to bracket open and close, cannot be produced by a market —
  only by a broken writer. Only the bid/ask relation became a counted drop.

A zero spread is retained, matching stage25_0a's `spread_pip < 0` predicate
exactly; adding a floor here would contradict the same precedent this fix
adopts.

## 7. BL-5 — the magnitude ceiling was invented, and wrong

**Defect.** PR #440 introduced `MAX_PLAUSIBLE_SPREAD_PIPS = 100.0` and applied
it as `100 * pip_size`. For a JPY pair that ceiling is `1.0` **price units** =
100 pips, so `USD_JPY median=0.9` under `spread_unit="price"` — a 100× unit
error — validated. There was no lower bound either.

**Search for an authority.** `docs/design/m15_first_cost_hurdle_aware_preregistration_design.md`,
`artifacts/m15_gate3a/cost_table_plan_or_metadata.json` and the gate-4 design
audit were searched. **No committed authority pins an upper or lower bound on a
quoted spread.** The `100.0` was invented by PR #440.

**Fix — no invented threshold.** The constant is **removed**, not re-tuned:
this module may not mint a contract constant. What is done instead is
everything provable from existing authority:

* the conversion to pips is **pair-aware**, through the same pip authority the
  rest of the package uses;
* the summary reports `max_observed_spread_pips` / `min_observed_spread_pips`,
  so a 100× error is visible in the artifact rather than silently passing;
* `spread_magnitude_validated` is `False` and `magnitude_authority` is
  `REQUIRES_SEPARATE_CONTRACT_GATE_DECISION` unless a caller passes an explicit
  `max_spread_pips`, so schema validity can never be read as magnitude
  validity;
* a test asserts no module-level numeric constant other than the two frozen pip
  paddings survives, so the ceiling cannot quietly return.

> **REFERRAL — `Requires separate contract Gate-decision`.** The absolute
> spread-magnitude bound is a contract question. It is recorded in the playbook
> §1 referral table and is **not** decided here. A related ambiguity surfaced
> while looking: `ALL_IN_COST_FORMULA` adds `median_spread(pair, session)` to
> the pip-unit constants `0.3` and `0.5`, while `spread_unit` declares the
> stored values are **price** units. For the sum to be dimensionally coherent
> the formula's `median_spread` must be in pips, i.e. a conversion step is
> implied but nowhere stated. Flagged, not resolved — the frozen formula string
> is unchanged.

## 8. RF-1…RF-11 disposition

| # | Finding | Disposition |
| --- | --- | --- |
| RF-1 | `SESSIONS_UTC` frozen pin with no test | **Fixed** — import-time partition check (explicit `raise`, survives `python -O`) + a test asserting the check is *invoked* at module level and actually rejects overlaps, holes and out-of-range windows |
| RF-2 | `missing_minute_count` semantics undefined against the committed inventory | **Requires separate contract Gate-decision** — the two readings are now stated exactly in the docstring, both figures are emitted, and a test pins the case that separates them. Referred in the playbook |
| RF-3 | `_names_protected` skips identity when the protected tree is absent | **Subsumed into BL-3** — only `FileNotFoundError` is "absent"; any other error fails closed |
| RF-4 | a test aims a write at the real protected evidence tree | **Fixed** — the prefix is now synthetic (monkeypatched), and a new test scans the suite and fails if any test aims `write_metadata_artifact` at a real protected prefix. That new test immediately found a **second** instance in `test_artifacts_scrub.py`, also fixed |
| RF-5 | fail-closed direction of `except OSError` unpinned | **Subsumed into BL-3** — mutation M20 (fail open) is killed |
| RF-6 | NUL byte escapes as a bare `ValueError` | **Fixed** — `PathAuthorityError` → `RealDataRefusedError` for both the guard and the writer, with a test |
| RF-7 | three refuted claims in the merged PR #440 note; stale playbook row | **Fixed** — all three corrected in place with an explicit CORRECTION block; playbook gate table brought current (PR #440 merged, PR #441 closed, PR #439 verdict named as the official status) |
| RF-8 | the B-1 proof skips without pandas; all five B-1 mutations survive there | **Fixed** — pure-stdlib subclass regressions (`NanoDatetime` exposing `.nanosecond`; `ShiftedDatetime` whose true instant differs) run everywhere, plus a test asserting pandas is present under the dev extra so the skip cannot hide again. The guard was also *widened* (§4), not just tested |
| RF-9 | bucket ordering unpinned | **Fixed** — out-of-order input, chronological output, plain-`datetime` keys |
| RF-10 | the `h ≥ max(o,c)` / `l ≤ min(o,c)` limb unpinned | **Fixed** — close-above-high and open-above-high cases |
| RF-11 | NFKC limb of `normalise_status` unpinned | **Fixed** — fullwidth `ＰＡＳＳ`, `ＰＲＯＤＵＣＴＩＯＮ＿ＲＥＡＤＹ`, `Ｔｉｅｒ　１` |

**Two PR #441 findings were reclassified on re-derivation**, per policy §13.8
(lead responsibility, not majority vote):

* RF-8's "the guard is not universal over subclasses" was **confirmed** as
  stated, but its framing as bounded-and-acceptable was **not** accepted: the
  guard is widened rather than the docstring narrowed.
* RF-2 was recorded as a defect; it is a **contract gap**, not a source defect.
  The code is self-consistent; what is missing is a ruling. Referred.

## 9. Mutation battery

30 mutations, each reverting one guard toward the defect it closes.
**28 killed, 2 survived**, 0 inapplicable.

| Blocker | Mutations | Killed |
| --- | --- | --- |
| BL-1 | M1…M9 | 9/9 |
| BL-2 | M10…M17 | 7/8 |
| BL-3 | M18…M22 | 4/5 |
| BL-4 | M23…M26 | 4/4 |
| BL-5 / RF-1 | M27…M30 | 4/4 |

**Both survivors were empirically proven redundant, not gaps** — the property
is already enforced one layer down, so no test can distinguish:

* **M15** (drop the `isinstance(offset, timedelta)` check). CPython's own
  `datetime.utcoffset()` raises
  `TypeError: tzinfo.utcoffset() must return None or timedelta, not 'int'`,
  which the `except Exception` limb converts to `TimestampError` with a message
  that still contains "timedelta". The isinstance check is unreachable
  defence-in-depth.
* **M22** (drop the NUL-byte check). `Path("x\x00y").resolve()` raises
  `ValueError: stat: embedded null character in path`, caught by
  `resolve_candidate`'s `(OSError, ValueError, RuntimeError)` limb. Redundant,
  with a less precise message.

Three mutations survived on the first run as **genuine coverage gaps** and were
closed by new tests before the final run: M3/M4 (the duplicate and unknown
limbs were only ever reached alongside a missing pair — isolated now with a
21-record roster), M8 (indexed access), M19 (the depth cap was never reached
because the name limb short-circuited), M26 (only the close was probed for a
cross). These are reported as found, not quietly folded into the final tally.

## 10. Tests

`tests/m15_gate3a/test_second_recheck_fixes.py` (new, 60+ cases) plus
`tests/m15_gate3a/roster_fixtures.py` (shared PAIRS_20 evidence builders).
Existing tests were updated where the *behaviour* changed by design — the
crossed-quote test now asserts drop-and-count, and every `assert_per_file_bounds`
call site now supplies roster evidence.

**Full gate-3a suite: 328 passed, 1 skipped** (the symlink alias case, which
needs a host permitting symlink creation; it runs on Linux CI).
**Full repo suite: 4782 passed, 7 skipped.** Three pre-existing failures on
master are unrelated to this PR and were confirmed to fail identically with
these changes stashed:
`tests/unit/test_stage25_0d_deployment_audit.py::test_smoke_run_completes_with_data`,
`tests/integration/test_exit_flow.py::TestExitFlowEndToEnd::test_tp_hit_writes_close_event`,
`tests/integration/test_replay_reproducibility.py::TestReplayReproducibility::test_fixture_is_rich_enough_to_make_assertion_load_bearing`.

`ruff check`, `ruff format --check` and `tools/lint/run_custom_checks.py` all
pass.

## 11. Internal multi-agent audit

Recorded in §12 below after the loop ran.

## 12. What this PR does not claim

* It does **not** claim source-audit acceptance. Only an independent re-check
  can grant that, and it must run in a session with no implementation context.
* It does **not** claim the machinery is correct on real data — nothing here
  has seen any.
* It does **not** claim `uv sync --frozen` reproducibility; that remains
  unresolved from PR #440 and no Red operation presuming it is approved.
* It does **not** settle the two referred contract questions (BL-5 magnitude
  bound, RF-2 `missing_minute_count` semantics).
* It does **not** authorise gate-3a continuation, real M15 derivation,
  validation, holdout evaluation, training or execution.
