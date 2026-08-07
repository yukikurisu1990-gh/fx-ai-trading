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
  `design_m15_inventory.json` declares as **required**, are mandatory, unique
  and well-formed. (They were optional in the first draft, which meant the
  duplicate-evidence guards could be switched off simply by omitting them —
  found by the internal audit, A-6);
* each record is read **once** into a snapshot, and one record object appearing
  at two indices is refused: twenty files means twenty record objects, and a
  `Mapping` is otherwise free to answer differently on every call (A-7);
* the returned record carries `expected_pairs`, `expected_pair_count`,
  `actual_pairs`, `actual_record_count`, `missing_pairs`, `duplicate_pairs`,
  `unknown_pairs` and `non_canonical_pair_spellings`, and the same figures
  appear in every refusal message;
* it also carries `certified_spans` — the pair, digest and bounds actually
  certified, so the proof can be re-checked against the inventory it proves —
  and `schema_keys_not_verified`, naming the committed keys it does **not**
  check, so the token cannot be read as full inventory validation;
* `expected_count` remains a caller cross-check — on its own it can no longer
  produce the token, because the roster binding runs regardless;
* `role="forward"` is **refused** outright (A-5): the committed forward schema
  has no `pair` key, so applying this roster would invent its shape.

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
* **refuses, never truncates**, sub-microsecond resolution: the `.nanosecond`
  attribute (`pandas.Timestamp`), an ISO string with more than six fractional
  digits (`fromisoformat` silently truncates those), and a `timestamp()`
  round-trip that disagrees with the components;
* applies all of the above in `to_utc`, so the dead-window, `DESIGN_END` and
  forward-floor predicates get them too — not only the minute path.

The scope of those limbs is stated rather than overclaimed: a float64 second
count near 2026 resolves ~4e-7 s, so the `timestamp()` cross-check cannot see a
lone nanosecond — that is the `.nanosecond` limb's job — and neither limb is
claimed to be universal over subclasses that hide a sub-microsecond remainder
with no attribute to read. The internal audit found earlier drafts of both this
section and the code getting exactly this wrong in three ways (A-1, A-2, A-8).

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
folds the prefix case-insensitively, and refuses non-path types, empty strings,
embedded NUL bytes, the device namespace (`\\.\`), unresolvable spellings, and —
RF-3 — a protected root that exists but cannot be interrogated. Only
`FileNotFoundError` counts as "genuinely absent"; the previous
`protected.exists()` shortcut reported "absent" for a permission error too and
skipped the identity test entirely. The same fail-closed rule applies to the
probe side, not just the root.

> **CORRECTION (internal audit).** The first draft's fold was **itself a
> bypass** (A-3). It stripped `\\?\` unconditionally, but the Win32 namespace
> also admits `\\?\Volume{GUID}\…` and `\\?\GLOBALROOT\Device\HarddiskVolumeN\…`;
> stripping the prefix leaves a **relative** path that then resolves against the
> working directory, so a spelling naming the consumed-holdout tree was
> **ALLOWED** — proven end-to-end through `write_metadata_artifact`. The fold now
> applies only when a drive letter or `UNC\` follows. It was also verified
> *unnecessary*: with no fold at all, `resolve()` plus the identity test refuses
> all four spellings, including the plain `\\?\C:\` case the fold was written
> for. An earlier draft of this section claimed the module "refuses on every
> failure mode"; that wording is withdrawn — see §11 for what it missed.

The depth regression is tested through the **identity** limb, not the name
limb: `sibling/../protected/d0/.../leaf` is not textually under `protected`
(pathlib keeps the `..`), so the walk must climb the whole chain.

## 6. BL-4 — crossed quotes abort the pair; the repo already ruled otherwise

**Defect.** A crossed quote (`ask < bid`) raised `AggregationError` and
abandoned the whole pair. This repository's committed
`scripts/stage25_0a_build_path_quality_dataset.py` already treats negative
spread as an expected **"data anomaly"** and drops-and-counts it per pair
(`:191` docstring, `:242-245` predicate, counter at `:220`, reported at
`:417`/`:424`, documented at `:612`).

> **CORRECTION (internal audit).** An earlier version of this section called the
> abort "this package's own stricter invention". **That is false.** The merged
> PR #439 audit prescribed it verbatim at
> `m15_aggregation_dataset_machinery_source_audit_recheck.md:411-412`:
> *"Fix: assert `h >= max(o, c)`, `l <= min(o, c)`, `h >= l` per side, and
> `ask_* >= bid_*` per row."* PR #440 implemented exactly that. So this change
> **re-disposes a recorded audit finding**, which is not something an
> implementing session may do silently — see the referral below.

**Fix.** Adopt the precedent. `_is_crossed_quote` is checked in the aggregation
loop; the row is dropped and counted, and the gap report gains
`rows_ingested`, `rows_retained`, `dropped_crossed_quote_rows`,
`buckets_fully_dropped` and `all_rows_dropped` — the drop is never silent, and a
pair whose rows were mostly or entirely dropped is visible rather than
presenting as merely sparse.

The harm R-2 actually named — a negative `spread_close` reaching the cost model
— remains closed: a crossed row never reaches a bar, and `_assert_bar_finite`
still refuses a negative `spread_close` as a last line (that branch lost its
`# pragma: no cover`, since the premise "row coherence already forbids it" no
longer holds).

**On the precedent's weight.** The `stage25_0a` citations are accurate, but the
analogy is not exact and should not be overstated: that script drops a *label
row* at signal-construction time on the M5 cadence and inspects only the entry
bar's open side, whereas gate-3a drops a *source minute* from a bar that is
still emitted. It is evidence of how this repository treats a crossed quote —
not a ruling. The rulings in this program are the human + ChatGPT
pre-registration rulings 1–13 and the recorded audit verdicts.

> **REFERRAL — `Requires separate contract Gate-decision`.** Two questions this
> change surfaces but may not answer: (a) whether R-2's `ask_* >= bid_*` limb is
> correctly re-disposed from *abort* to *counted drop*; and (b) whether a drop
> ratio has an acceptance threshold — `all_rows_dropped` is reported, never
> raised on, because a ratio threshold would be an invented number. Recorded in
> the playbook referral table.

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

> **CORRECTION (internal audit).** An earlier version of this section framed the
> ceiling as mis-scaled for JPY. It was not: `value > 100 * pip_size` is
> algebraically a **uniform 100-pip ceiling for every pair**, and its error
> message already printed pips. The real defect is narrower — 100 pips is too
> loose to catch the JPY 100× class (`USD_JPY median=0.9` price units = 90 pips,
> under the ceiling) while catching the non-JPY 10,000× class (9,000 pips).
> Relatedly, "the conversion is pair-aware" is not a new property; it was
> pair-aware at base.

**Fix — no invented threshold, and no silent weakening either.** The constant is
**removed**, not re-tuned: this module may not mint a contract constant. But the
audit was right that plain removal made the non-JPY case — where the ceiling did
work — strictly weaker, since no caller supplied a bound. Both constraints are
satisfied by making `max_spread_pips` a **required keyword argument with no
default**:

* every caller must state a bound, or state `None` meaning "no bound is pinned,
  magnitude UNVALIDATED" — so the choice is always recorded and never inherited
  by accident;
* the summary reports `max_observed_spread_pips` / `min_observed_spread_pips`,
  so a 100× error is visible in the artifact rather than silently passing;
* the flag is named `magnitude_checked_against_declared_bound`, not
  "validated" — a caller may declare a bound so loose it excludes nothing, and
  `max_spread_pips_declared` alongside it is what makes that visible;
* `magnitude_authority` is `REQUIRES_SEPARATE_CONTRACT_GATE_DECISION` whenever
  no bound was declared;
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
| RF-4 | a test aims a write at the real protected evidence tree | **Fixed** — the prefix is now synthetic (monkeypatched), and a new test scans the suite and fails if any test aims a write at a real protected prefix. That new test immediately found a **second** instance in `test_artifacts_scrub.py`, also fixed; the internal audit then found the scan itself passed vacuously from another cwd (A-13), now anchored and AST-based |
| RF-5 | fail-closed direction of `except OSError` unpinned | **Subsumed into BL-3** — mutation M20 (fail open) is killed |
| RF-6 | NUL byte escapes as a bare `ValueError` | **Fixed** — `PathAuthorityError` → `RealDataRefusedError` for both the guard and the writer, with a test |
| RF-7 | three refuted claims in the merged PR #440 note; stale playbook row | **Fixed** — all three corrected in place with an explicit CORRECTION block; playbook gate table brought current (PR #440 merged, PR #441 closed, PR #439 verdict named as the official status) |
| RF-8 | the B-1 proof skips without pandas; all five B-1 mutations survive there | **Fixed** — pure-stdlib subclass regressions (`NanoDatetime` exposing `.nanosecond`; `ShiftedDatetime` whose true instant differs; `LyingComponents` overriding a component) run everywhere, plus a test asserting pandas is present under the dev extra so the skip cannot hide again. The guard was also *widened* (§4), not just tested |
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

**44 mutations, 43 killed**, 0 inapplicable — each reverting one guard toward
the defect it closes, including one per audit fix in §11.

| Target | Mutations | Killed |
| --- | --- | --- |
| BL-1 evidence binding | M1…M9, M33, M34, M36, M38, M40, M41 | 15/15 |
| BL-2 timestamp authority | M10…M17, M31, M37, M42, M44 | 11/12 |
| BL-3 path authority | M18…M22, M32, M39 | 7/7 |
| BL-4 drop-and-count | M23…M26, M35, M43 | 6/6 |
| BL-5 / RF-1 cost schema | M27…M30 | 4/4 |

**The one survivor is empirically proven redundant, not a gap.** M15 (drop the
`isinstance(offset, timedelta)` check): CPython's own `datetime.utcoffset()`
raises `TypeError: tzinfo.utcoffset() must return None or timedelta, not 'int'`,
which the `except Exception` limb converts to `TimestampError` with a message
that still contains "timedelta". Unreachable defence-in-depth. The tests role's
independent 102-mutation battery reached the same verdict on the same guard.

**Nine mutations survived an intermediate run as genuine coverage gaps and were
closed by new tests before the final run** — reported as found rather than
folded into the tally: the duplicate and unknown roster limbs were only ever
reached *alongside* a missing pair (isolated now with a 21-record roster);
indexed access; the depth cap, which the name limb short-circuited before the
walk was reached; a cross on a limb other than the close; the microsecond limb
of minute alignment; the sha256 length boundary above 64; the magnitude-ceiling
comparison at its boundary; a duplicate `(pair, session)` cost cell; and the
`SESSIONS_UTC` pin, which needed an AST check that the guard is *invoked*, not
merely defined.

**M22** (drop the NUL-byte check) was a survivor in the first battery and is now
killed — the `str`-subclass fix (A-12) made the check load-bearing rather than
redundant with `resolve()`'s own `ValueError`.

## 10. Tests

`tests/m15_gate3a/test_second_recheck_fixes.py` (new, 60+ cases) plus
`tests/m15_gate3a/roster_fixtures.py` (shared PAIRS_20 evidence builders).
Existing tests were updated where the *behaviour* changed by design — the
crossed-quote test now asserts drop-and-count, and every `assert_per_file_bounds`
call site now supplies roster evidence.

**Full gate-3a suite: 356 passed, 1 skipped** (the symlink alias case, which
needs a host permitting symlink creation; it runs on Linux CI).
**Full repo suite: 4782 passed, 7 skipped.** Three pre-existing failures on
master are unrelated to this PR and were confirmed to fail identically with
these changes stashed:
`tests/unit/test_stage25_0d_deployment_audit.py::test_smoke_run_completes_with_data`,
`tests/integration/test_exit_flow.py::TestExitFlowEndToEnd::test_tp_hit_writes_close_event`,
`tests/integration/test_replay_reproducibility.py::TestReplayReproducibility::test_fixture_is_rich_enough_to_make_assertion_load_bearing`.

`ruff check`, `ruff format --check` and `tools/lint/run_custom_checks.py` all
pass.

## 11. Internal multi-agent audit (policy §13)

Five roles ran in **separated contexts**, each given the source, the diff and
the contract documents and **never the other roles' conclusions**:
implementation/correctness · contract & data boundary · adversarial/bypass (told
to argue the change is wrong) · tests & mutation (own independent battery) ·
containment, forbidden routes & CI.

**The first head, `a8a127d`, was CI-green and still BLOCKED by three of the five
roles.** Nine further defects were found, four of them **in the fix itself** —
including one where the fix re-opened the very class it was closing. Every
finding below was re-derived by the lead before being acted on.

### Blockers found in this PR's own new code

| # | Defect | Roles |
| --- | --- | --- |
| A-1 | `to_utc` **truncated** sub-microsecond resolution instead of refusing it. `no_overlap` calls `to_utc`, not `to_utc_minute`, so a `ts_max` 500 ns **past** `DESIGN_END` rebuilt to exactly `DESIGN_END` and earned the T-7 token — where the base commit **refused** it. A fail-open at the frozen design boundary, introduced by the BL-2 fix | contract, containment |
| A-2 | `to_utc` rebuilt from `.year`/`.month`/… , which a subclass can override as properties. A two-line subclass reporting `month == 1` for a March instant walked a **dead-window** timestamp past the dead-window predicate and a pre-floor timestamp past the warm-up floor. The `timestamp()` cross-check existed but was applied only to the minute path | adversarial, implementation, containment |
| A-3 | `normalise_spelling` stripped `\\?\` **unconditionally**. The Win32 namespace also admits `\\?\Volume{GUID}\…` and `\\?\GLOBALROOT\Device\HarddiskVolumeN\…`; stripping the prefix leaves a **relative** path that resolves against the CWD, so a spelling naming the consumed-holdout tree was **ALLOWED** — proven end-to-end through `write_metadata_artifact`. The BL-3 fix created a new instance of the class it closed. Verified unnecessary as well as harmful: without the fold, `resolve()` + identity refuses all four spellings including the plain `\\?\C:\` case it was written for | adversarial, implementation, containment |
| A-4 | The BL-4 note's provenance claim was **false** — see §6 | contract |
| A-5 | The 20-pair roster binding was applied to `role="forward"`, whose committed schema has **no `pair` key** and a per-file `validation \| holdout` split — inventing the forward evidence shape, the same thing BL-5 refused to do | contract, containment |

### Required fixes found

| # | Defect | Resolution |
| --- | --- | --- |
| A-6 | `filename`/`sha256` were validated only *when present*, so the duplicate-evidence guards could be switched off by omitting them; 20 records naming 20 pairs while describing one file earned the token | Both made **mandatory** (the committed schema declares them required) |
| A-7 | A `Mapping` may answer `.get()` differently on every call; the roster pass and the bounds pass each re-read the record | Each record is **snapshotted** to a plain dict once; and the same object appearing at two indices is refused, since twenty files means twenty record objects |
| A-8 | `datetime.fromisoformat` **truncates** past 6 fractional digits, so the same instant was refused as a `pandas.Timestamp` and accepted as a string | ISO fractions beyond 6 digits refused; `aggregation` narrowed back to `datetime`-only (accepting `str` was an unrequested loosening) |
| A-9 | `rows_ingested` came from `len(m1_rows)` while retained/dropped were counted in the loop — a `list` **subclass** with a lying `__len__` falsified the report's own accounting identity. **BL-1's defect pattern, reintroduced in another module** | Counted from iteration |
| A-10 | A fully-dropped **leading or trailing** bucket vanished from the gap span, so a file that lost a third of its input reported `missing_minute_count=0, max_gap_minutes=0, missing_whole_buckets=0` — and those are the only two keys the committed `gap_report` carries | Gap metrics now describe **source coverage** (retained + dropped); `buckets_fully_dropped` and `all_rows_dropped` added |
| A-11 | `OverflowError` escaped `to_utc`, bypassing the documented exception type | Wrapped as `TimestampError` |
| A-12 | `resolve_candidate` re-entered `str(path)`, letting a `str` subclass show one string to the checks and another to `Path()` | Character data pinned once via `str.__str__` |
| A-13 | My own anti-litter test used a **cwd-relative glob**, so from another directory it globbed nothing and **passed vacuously**; it also scanned one file pattern and required a same-line match | Anchored to `__file__`, asserts a non-zero file count, AST-based so a wrapped call cannot evade it |
| A-14 | The regression module's docstring claimed *"every test here fails against the previous implementation"* — false for 4 of 17 spot-checked (RF-2/9/10/11 pin correct behaviour that was merely untested) | Docstring narrowed to distinguish BL-tagged regressions from RF-tagged coverage |

### Findings the lead did **not** adopt as stated

Policy §13.8 — the lead owns the outcome and checks the evidence behind each
finding rather than counting votes.

* **`to_utc_minute` "generalises to any subclass".** The adversarial role showed
  a genuine 1 ns remainder at the 2026 epoch measures `drift = 0.0`, because a
  float64 second count resolves only ~4e-7 s there. Correct — so the docstring
  now states the two limbs' actual reach and claims no universality.
* **Hardlink to a file inside a protected tree is allowed** (implementation N-3).
  Verified, but outside the guard's stated question ("does this path name, or
  sit under, a protected tree"), unchanged from base, and NTFS forbids directory
  hardlinks. Recorded as a non-blocking observation, not fixed here.
* **Bar-level `bid_h > ask_h` is unchecked** (adversarial N-5, implementation
  N-6). Pre-existing and unchanged by this PR; recorded, not fixed, because it
  is outside this PR's objective.
* **`_check_session_partition` guards a constant nothing in the package
  consumes** (implementation N-4). True — no gate-3a module maps a timestamp to
  a session. The check is still correct for what RF-1 asked (pinning the frozen
  values); the motivation wording was narrowed rather than the check removed.
* **An early "nondeterminism" observation** was withdrawn by the role itself
  after eight identical re-runs; not recorded as a finding.

### Harness hazard worth recording

Two roles independently hit **stale `.pyc` reuse**: CPython validates bytecode
on `(int(mtime_seconds), size)`, so a same-size edit inside one second silently
runs the *old* module. One role initially mis-attributed kills because of it.
The mutation battery now purges `__pycache__` and runs under `-B` with
`PYTHONDONTWRITEBYTECODE=1`. Anyone repeating mutation work in this repo must do
the same.

### Confirmed clean by the containment role

Eager import closure is **stdlib-only**; the two new modules add `datetime`,
`os`, `pathlib`, `re`, `typing` and **no new non-stdlib module**. No new
production or runtime caller — reverse callers are tests only. AST scan of the
whole `tests/` tree for a write naming a protected prefix: **0 hits**.
`FORBIDDEN_STATUSES` is set-equal to playbook §10, 14/14. All 8 committed
`artifacts/m15_gate3a/*.json` pass `assert_gate3a_clean`. `pyproject.toml`,
`uv.lock`, `.pre-commit-config.yaml` and `.github/**` untouched.

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
