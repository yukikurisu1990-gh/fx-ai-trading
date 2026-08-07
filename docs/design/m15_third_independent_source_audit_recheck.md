# Third independent source-audit re-check — M15 gate-3a machinery at `c3a0468`

- **Document class:** doc-only Gate-decision record. Judges the research state;
  executes nothing; authorises nothing; changes no source, test or contract.
- **Target:** `scripts/m15_gate3a/**` and `tests/m15_gate3a/**` at master
  `c3a0468` (the head produced by PR #442), master CI green.
- **Risk tier:** Amber (policy §2–§3 — it judges a protected-path research
  contract). **Not self-mergeable.** Merging requires human + ChatGPT approval.
- **Verdict:**
  **`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`**

## Statuses

- Required: `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
  · `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_ACCEPTABLE_FOR_GATE3A_DATASET_EPOCH_ADOPTION`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Gate-3a continuation: **NOT authorised.**

**Forbidden-label note.** This document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST` or `DEPLOYABLE`. Where such tokens appear
below they are **probe payloads quoted as evidence of a containment failure**,
i.e. a prohibition context under playbook §10 — never a claim.

---

## 1. Executive verdict

The audit **BLOCKS**. Seven blockers and twenty-nine required fixes are
recorded. The verdict is not a close call, but it is also not a condemnation of
the whole machinery: the arithmetic and boundary layers re-derive **correct**
against the frozen contract, and the defects cluster in four specific places —

1. the **artifact scrubber**, which does not contain what it claims to contain;
2. the **T-7 no-overlap proof**, which is a declaration-consistency check being
   asked to serve as the byte-level proof playbook §5 requires;
3. **contract questions the source decides for itself**, including one that
   re-disposes a finding recorded in a merged audit;
4. the **test layer**, which pins the defects that were found rather than the
   contract that was specified — leaving the design↔forward epoch boundary and
   the always-binding status constants unconstrained.

The strongest single result is that a 147 KB payload carrying a full bid/ask
price dataset, strategy metrics, predictions, model coefficients, a
production-readiness claim, a credential and an environment dump can be written
by `write_metadata_artifact` with the scrubber reporting **zero findings** — and
that this needs no adversarial object, only ordinary dict keys and ordinary
English. Conversely the machinery **refuses** to write the one construct
governance explicitly permits, a prohibition list.

Nothing here authorises anything. Even had the verdict been acceptable, three
contract referrals classified `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION` would
still stand between this machinery and a real derivation (§7).

**Prior verdict unchanged.** The official gate status was already
`…_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES` (merged PR #439). This re-check
does not lift it. PR #440 and PR #442 recorded fixes; neither granted
acceptance, and PR #441 was closed as non-independent.

---

## 2. Independence and method

**Top-level session independence.** This audit ran in a session that did not
implement PR #440 or PR #442 and inherited no conversation context from either.
It re-read the committed source, tests, contract and artifacts directly. The
three fix/audit notes (`m15_aggregation_dataset_machinery_source_audit_recheck.md`,
`m15_recheck_targeted_fixes_note.md`, `m15_second_recheck_targeted_fixes_note.md`)
were read as **history only**; every claim in them was treated as unverified and
re-derived from source. PR #441 was consulted as non-authoritative diagnostic
history. Policy §12 is satisfied.

**Roles (policy §13).** Six independent audit subagents, none given any other's
conclusions:

| Role | Charter |
| --- | --- |
| 1 | contract / specification / data-boundary |
| 2 | adversarial / bypass — briefed to argue the machinery is unsafe and prove it |
| 3 | tests / mutation resistance |
| 4 | filesystem containment / import graph / prohibited execution routes |
| 5 | artifacts / scrubber / status guards |
| 6 | contract-referral re-evaluation and silent-contract-decision hunting |

**Lead discipline.** The lead read all eleven source modules before assigning any
role, and **independently reproduced every blocker** rather than counting votes.
Where a role's evidence did not survive that check, the finding was downgraded —
see §5 (A-2) for the one case where a role's BLOCKER was demoted on the lead's
own control experiment. Disagreements were resolved on evidence (§10).

**What was and was not done.** No real data was read; no M15 was derived; no
real checksum or spread was computed; nothing was trained, validated, evaluated,
inferred or executed; no broker, paper, live, external-storage or credential
path was touched. `uv.lock` was not modified and `uv sync` was never run (the
lockfile is known-stale; running it would wipe the venv). No source or test file
was changed — `git status` is clean for tracked files at the audit head. All
probes used synthetic literals and wrote only to a scratchpad outside the repo.
Committed metadata JSON under `artifacts/**` was **read** (explicitly permitted:
"committed source / tests / docs / metadata"); no market data file was opened.

**Baseline.** `python -m pytest tests/m15_gate3a/ -q` → **356 passed, 1 skipped**
(the skip is a symlink test, not permitted on this host). `ruff check`,
`ruff format --check` and `python tools/lint/run_custom_checks.py` all clean.

---

## 3. Audit scope, derived from current source

Scope was rebuilt from the current source rather than from the prior blocker
lists. The eleven modules and the boundaries each owns:

| Module | Boundary audited |
| --- | --- |
| `timeutil.py` | timestamp awareness, UTC conversion, sub-microsecond policy, minute alignment |
| `aggregation.py` | bucket arithmetic, eligibility, duplicates, finiteness, OHLC coherence, crossed quotes, gap report, pip authority |
| `no_overlap.py` | design/forward/dead-window bounds, T-7 proof, evidence identity + roster |
| `pair_authority.py` | pair normalisation, PAIRS_20 universe, pip delegation |
| `path_authority.py` | Windows path aliasing, ancestor containment |
| `guards.py` | protected paths, forbidden operations, forbidden statuses, synthetic-only mode |
| `artifacts.py` | scrubber, metadata validation, artifact writing |
| `cost_schema.py` | frozen cost constants, sessions, quantile monotonicity, magnitude bound |
| `effective_n.py` | T-6 estimator, roles, floors |
| `warmup.py` | T-1 burn-in policy |
| `__init__.py` | status constants |

---

## 4. Blockers

Each was reproduced by the lead. Where exploitation has a precondition, it is
stated rather than glossed.

### B-1 — the gate-3a scrubber does not contain forbidden content

`artifacts.py:101-134` (`_scan_gate3a_keys`), `guards.py:109-121`

Three independent, mutually sufficient evasions, none needing a hostile object:

**(a) Container shape.** The row-like heuristic counts qualifying dicts only
inside `list`/`tuple`; the columnar heuristic counts numeric series only among
one dict's immediate values. Re-keying the identical data as a dict-of-dicts is
unchecked and unbounded. Lead reproduction:

```
CONTROL list of 300 rows x 6 numeric fields  -> REFUSED ['gate3a_row_like_numeric_records', ...]
A. SAME 300 rows re-keyed as dict-of-dicts   -> ACCEPTED (clean)
```

**(b) Claim phrasing.** `is_forbidden_status` matches the **whole** normalised
string, so any embedding evades it. Lead reproduction:

```
{"verdict": "PRODUCTION_READY"}                -> REFUSED
{"verdict": "PRODUCTION READY: yes"}           -> ACCEPTED (clean)
{"verdict": "status=PRODUCTION_READY"}         -> ACCEPTED (clean)
{"verdict": "PRODUCTION_READY_CLAIMED"}        -> ACCEPTED (clean)
{"verdict": "PRODUCTION_READY!"}               -> ACCEPTED (clean)
{"verdict": "This machinery is production ready and cleared for live."} -> ACCEPTED
```

**(c) Character-set.** NFKC folds fullwidth forms but not homoglyphs or
invisibles. Lead reproduction:

```
{"result": "PASS"}            (ASCII)            -> REFUSED
{"result": "PАSS"}            (U+0410 Cyrillic)  -> ACCEPTED (clean)
{"result": "PASS​"}      (zero-width space) -> ACCEPTED (clean)
{"result": "ＰＡＳＳ"}          (fullwidth)        -> REFUSED
```

Role 5 combined these into a single 147 KB payload — full 8-side BA series, 500
row records, Sharpe/PnL/drawdown, predictions, model coefficients, holdout
metrics, an `M15_AUTHORISED` claim, a live-format API key and an environment
dump — accepted with `findings: []` and **written to disk** by
`write_metadata_artifact`.

The mirror-image defect is equally disqualifying: the scrubber **refuses** the
one usage playbook §10 expressly permits.

```
{"forbidden_labels": ["PASS", "MEETS", "ROBUST"]}
   -> REFUSED ['gate3a_forbidden_status_value:MEETS', '...:PASS', '...:ROBUST']
{"pip_size": [0.0001]*20, "spread_floor_pips": [0.6]*20}   (20-pair roster)
   -> REFUSED ['gate3a_columnar_numeric_series']
```

So the machinery cannot write its own `scrub_report.json` naming what it
prohibits, nor a natural columnar 20-pair roster, while it *can* write a
complete price dataset. A pure tightening cannot fix this — the design needs a
per-artifact **allowlist** (declare the permitted schema and reject anything
outside it) instead of a denylist of shapes and literal spellings.

The repository already contains the control this needs and gate-3a does not use
it: `scripts/foundation_t2/scrub.py:37-43` scans serialised text for forbidden
labels and claim substrings. `artifacts.py:7` nonetheless states gate-3a is
"even stricter" than the ML Step 4 scrubber; on the claim axis it is strictly
weaker than the Foundation T2 scrubber already in-repo.

### B-2 — the T-7 proof is a declaration check, not the byte-level proof §5 requires

`no_overlap.py:277-351`

Playbook §5 binds the continuation to "Produce the **byte-level no-overlap
proof** (per-file `ts_max ≤ 2026-02-28T23:59:59Z`; zero dead-window bars)".
`assert_per_file_bounds` reads no bytes, opens no file, and never verifies that a
declared `sha256` matches anything. Lead control run — 20 plain ISO strings, no
file access whatsoever:

```
plain ISO strings, honest-looking bounds -> PROVEN_NO_DEAD_WINDOW_OVERLAP, files=20
```

The identity guards added by PR #442 are real and they hold (§6): they prevent
one *record* masquerading as twenty. They do not connect any record to a file.
The committed `design_m15_inventory.json:22` aggregate assertion
`dead_window_bars_present: 0` is emitted by **no code path** in the package.

The function honestly lists five schema keys it does not verify
(`schema_keys_not_verified`), but it does not declare the more important thing:
that its bounds are **declared, not measured**. A reader of
`no_overlap_proof.json` sees `PROVEN_NO_DEAD_WINDOW_OVERLAP` with no indication
that the proof's entire evidentiary basis is caller-supplied metadata.

This is not a request to make the package read data — containment forbids that,
correctly. It is that **nothing in the machinery can produce what §5 requires**,
and the gap must be closed by design (a separate checksum/derivation attestation
step) before a continuation can claim the proof.

### B-3 — the certified value is not the published value

`no_overlap.py:321` vs `:328-329`

`assert_per_file_bounds` bound-checks `ts_min`/`ts_max` at `:321`, then
**re-parses the same inputs** at `:328-329` to build `certified_spans`. The two
parses are independent; nothing reconciles them. Lead reproduction with a
CPython-legal drifting `tzinfo` (offset stable for the two calls the bound check
makes, then shifting):

```
result                 : PROVEN_NO_DEAD_WINDOW_OVERLAP
DESIGN_END             : 2026-02-28T23:59:59+00:00
PUBLISHED certified max: 2026-03-01T11:00:00+00:00
utcoffset() call count : 4
published > DESIGN_END : True
published inside dead window: True
```

The emitted proof artifact would contain a dead-window span **beside** the token
asserting there is none — an artifact that refutes itself.

*Precondition, stated honestly:* this requires evidence carrying a live hostile
`tzinfo`, not a JSON string. The reason it is a blocker regardless is structural:
certification and publication are decoupled, so the artifact's contents are not
what was checked. The fix is to reuse the already-parsed value.

### B-4 — crossed-quote disposition was decided against a merged audit finding

`aggregation.py:146-157`, `:200-206`; playbook §1 referral 3

Merged PR #439, `m15_aggregation_dataset_machinery_source_audit_recheck.md:411-412`,
prescribes verbatim: *"assert `h >= max(o, c)`, `l <= min(o, c)`, `h >= l` per
side, and **`ask_* >= bid_*` per row**."* The current source instead drops and
counts the row. Policy §14.2 reserves "formally changed or judged … an
independent source-audit verdict" to a **Gate-decision PR**; this was re-disposed
inside a Work PR.

The playbook row understates the blast radius. Lead reproduction — 15 genuine
distinct source minutes, three of them crossed:

```
eligible      : [False]        <- the bucket loses event eligibility
n_source_bars : [12]           <- 15 source bars existed
missing_minute_count : 0
total_missing_source_minutes_within_emitted_buckets : 3   <- no minute is absent
rows_ingested/retained : 15 / 12
```

So the disposition changes `eligible_event_count` — a committed per-file field
(`design_m15_inventory.json:12`) and the denominator of the family's effective-N.
It is not diagnostics-only, and the gate-3a continuation is the only gate at
which the design dataset is derived.

The `stage25_0a` precedent cited for the change does not carry the weight placed
on it: that script drops a *label row at signal-construction time*, computed from
the entry bar's open side, on data epochs (`730d_BA`, `3650d_BA`) the M15
pre-registration §3.2 expressly bans; and pre-registration §11's reuse taxonomy,
which is closed, does not list it. The implementing session's own note
(`m15_second_recheck_targeted_fixes_note.md:194-200`) already concedes it is
"evidence … **not a ruling**". This audit agrees and goes further: under §11 it
is not admissible authority for a design decision in this family.

### B-5 — the protected-path set omits the trees governance names

`guards.py:19-22`

`_PROTECTED_PREFIXES` covers two directories. Lead reproduction:

```
REFUSED : artifacts/ml_step4/365d_ba_v1
ALLOWED : artifacts/m15_gate3a
ALLOWED : artifacts/m15_gate3a/effective_n_estimator_spec.json
ALLOWED : artifacts/gate_p1_pr_b/firstrun_730d_ba
ALLOWED : data
ALLOWED : models
```

Playbook §9 requires `artifacts/m15_gate3a/*` **untouched**, and
`artifacts.py:48-57` documents `EXPECTED_ARTIFACT_FILES` as mirroring exactly
that directory — so the module's own documented purpose is to write into the one
tree governance says must not be touched, and the guard permits it. The frozen
`effective_n_estimator_spec.json` (`APPROVED_SPEC`) and `no_overlap_proof.json`
are overwritable. Also unprotected: `data/` (the real M1 candle store and the
default `data_root` of `Real365dBaProvider`), `models/` (20 model binaries), and
the 730d/3650d PR-B.1 evidence trees.

*Precondition:* latent, because `write_metadata_artifact` has no non-test caller
and the package contains no reader at all. It becomes live with the first caller
— which the continuation adds.

This also surfaces a governance contradiction the audit cannot resolve on its
own: **§9 says `artifacts/m15_gate3a/*` must be untouched while §5 requires the
continuation to populate `design_m15_inventory.json` inside it.** Recorded as a
new referral (§8, NR-A).

### B-6 — three contract referrals must resolve before any continuation

Referrals 2, 3 and 4 are classified `MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION` in
§7. They are grouped here because they block the same operation: each determines
an artifact field's meaning or the derived bytes the continuation exists to
produce, and no later gate re-derives the design dataset.

### B-7 — the suite does not pin the contamination boundary or the binding statuses

**The underlying source is correct in both cases.** This blocker is about what a
green suite may be cited as evidence for, which matters because a green run is
exactly what a merge approval looks at.

**(a) The design↔forward epoch boundary is unpinned.** Mutating
`no_overlap.py:81` (`if hi > DESIGN_END:` → `if False:`) and `:97`
(`if lo < FORWARD_FLOOR:` → `if False:`) each leaves the suite at
**356 passed, 1 skipped**. With the guard disabled, a 20-pair roster of
*forward-epoch* files earns `PROVEN_NO_DEAD_WINDOW_OVERLAP` as a **design**
inventory, and design-span files pass as forward artifacts.

Lead-verified by inspecting every committed call rather than by re-mutating: to
isolate the `DESIGN_END` limb a test needs `ts_max > DESIGN_END` while the span
*misses* the dead window. No committed test does. `test_recheck_fixes.py:419`
uses `DEAD_START_S`, which trips the dead-window predicate as well;
`test_second_recheck_fixes.py:610` raises from the **nanosecond** refusal, not
the bound; `test_b2_span_containing_dead_window_never_proven:412` uses
`match="dead window|DESIGN_END"`, an alternation that cannot tell which guard
fired. The forward limb is unpinned identically — every forward test picks a
`ts_min` inside the dead window.

A green `tests/m15_gate3a/` therefore **is not evidence that design and forward
data cannot be interchanged** — which is the single property this gate exists to
protect.

**(b) All three always-binding status constants are unpinned.**
`__init__.py:26-33` can be mutated to `PRODUCTION_READY`, `EXECUTION_PERFORMED`
and `NEW_EPOCH_ADOPTED` with the suite green. Lead-verified by grep: **no test
in the repository references `IMPLEMENTATION_STATUS`, `PRODUCTION_STATUS`,
`EXECUTION_STATUS` or `FORWARD_EPOCH_STATUS` of this package** (every hit is the
separate `scripts/ml_step4` package). Two of the three replacement values sit in
the module's own `FORBIDDEN_STATUSES`.

---

## 5. Required fixes

Land with the blockers; none is individually gate-stopping, all falsify a stated
guarantee or a committed contract.

| ID | Location | Defect |
| --- | --- | --- |
| RF-1 | `timeutil.py:30,115-120` | ISO **comma** decimal separator bypasses the fractional-digit check. Lead-verified: `"…23:59:59.0000005+00:00"` refused, `"…23:59:59,0000005+00:00"` **accepted and truncated**. The documented invariant "refused, never truncated" is false. Impact bounded to <1 µs. |
| RF-2 | `timeutil.py:67-70` | Docstring claims the `timestamp()` cross-check "catches [component lies] outright". It does not: a subclass lying consistently in both components and `timestamp()` passes (lead-verified). The guarantee must be restated, not the code necessarily changed. |
| RF-3 | `aggregation.py:265-277` | `_assert_bar_finite` documents itself as the last guard against a row mutating between validation and bar construction, then checks only finiteness and negative `spread_close`. Lead-verified: `eligible: True` bar with `bid_h=1.0 < bid_l=1.2`, `ask_h=0.9 < bid_h`, `dropped_crossed_quote_rows: 0`. |
| RF-4 | `aggregation.py:187-206` | No record-identity check on M1 rows. One dict presented 15× with a walking `ts` yields `eligible: True, n_source_bars: 15`. `no_overlap._materialise:170-174` added exactly this guard; aggregation did not. |
| RF-5 | `path_authority.py:128-129` | `str` character data is pinned against subclass lies; **`Path` subclasses are not**. Lead-verified: `refuse_real_path(LyingPath)` **ALLOWED** while `refuse_real_path(Path(LyingPath))` refused. |
| RF-6 | `artifacts.py:165-177` | `name` validation trusts a `str` subclass (`endswith`, `!=`, `in` all overridable), escaping `out_dir`. Bounded: `refuse_real_path(target)` still resolves the joined path. |
| RF-7 | `artifacts.py:21-45,107` | `_GATE3A_FORBIDDEN_KEYS` is exact-match: `sharpe_ratio`, `sharpeRatio`, `net_pnl`, `max_drawdown_pct`, `hit_rate`, `profit_factor`, `expectancy_per_trade`, `total_return` all pass. |
| RF-8 | `artifacts.py:113` | Truthiness is used as a proxy for assertion: `{"PRODUCTION_READY": "no"}` is **refused** while `{"PRODUCTION_READY": False}` passes. The rule cannot distinguish a claim from a disclaimer. |
| RF-9 | `artifacts.py:180-181` | A failure *at* `write_text` (e.g. over-long name) leaves `out_dir` created and raises a non-`ArtifactScrubError`. Validation-stage refusals correctly leave nothing. |
| RF-10 | `artifacts.py:91-98` | `_non_finite_finding` inspects values only; a non-finite **key** is unscanned and silently stringified to `"NaN"` by `json.dumps`. |
| RF-11 | `artifacts.py:150-154` vs `evidence.py:111-113` | Payloads declared clean that `serialise` cannot write (`Decimal('NaN')`, `set`, numpy scalars/arrays, mixed-type keys) die with a bare `TypeError`. Fails closed, but not as a scrub error. |
| RF-12 | `guards.py:101-121` | Playbook §10 declares "casing/whitespace variants … treated identically"; `tier1`, `productionready`, `BYTEADMISSIBLE` all pass. The listed near-synonyms ("validated", "proven profitable", "ready to deploy", "green-light", "cleared for live") have no representation at all. |
| RF-13 | `guards.py:124-127` | `assert_status_allowed` silently passes non-`str` (`b"PASS"`, `["PASS"]`, `None`) — fail-open on type. |
| RF-14 | `guards.py:92-98` | `assert_no_forbidden_operation` refuses unknown flags **only when truthy**; the likely caller typo `training=False` passes silently, as does an empty call. |
| RF-15 | `guards.py:2-6`, `artifacts.py:7-8` | Docstrings assert containment properties the code does not have ("Every entry point … routes through these guards"; "refuses to write under any protected real path"). `assert_synthetic_only`, `assert_no_forbidden_operation`, `assert_status_allowed` have **zero non-test callers**. |
| RF-16 | `cost_schema.py:80-87` | The committed plan's `stress_forms` (2× and p90 — "both mandatory") and `data_source_restriction` ("DESIGN span only … never validation/holdout") are neither required nor checked. A table omitting both returns `COST_TABLE_SCHEMA_VALID`. |
| RF-17 | `cost_schema.py:23,135-136` | `CLAIM_SCOPE = "quote_cost_validity"` is code-minted; the committed plan declares `"quote-cost-validity research claim; NOT a live-fill claim"`, which the validator **refuses**. |
| RF-18 | `aggregation.py:223-237` | Pre-registration §4 (`:163-164`) and `design_m15_derivation_manifest.json:30` both require the **open-side spread variant** be recorded. Only `spread_close` is emitted. |
| RF-19 | `cost_schema.py:214` | Merged-audit R-8's fourth limb ("A one-entry table validates, so 20 × 3 coverage is unenforced. Fix all four before the tables are produced") was re-disposed to a reported boolean with no raise — the same governance class as B-4, and **never referred**. |

Test-layer required fixes. In each the **source is correct**; the mutation
survives because nothing constrains it.

| ID | Location | Defect |
| --- | --- | --- |
| RF-20 | `timeutil.py:107` | The two-faced `str`-subclass defence (`str.__str__(ts)` → `str(ts)`) is unpinned; a subclass carrying `2025-06-02` but rendering `2026-12-25` parses differently under the mutant. The identical hardening in `path_authority.py:133` **is** covered — the fix was tested where it was found, not where it recurs. |
| RF-21 | `test_recheck_fixes.py:1134-1154` | `test_span_ordering_invariants_survive_optimised_mode` asserts that a `raise` **string literal** appears in the source, not that the invariant holds. Disabling the condition leaves the test passing. A regression test that cannot fail on a revert of its own fix. |
| RF-22 | `test_recheck_fixes.py:778-784` | Vacuous glob: `test_committed_gate3a_artifacts_remain_scrub_clean` passes in a tree with no artifacts at all. Its sibling asserts `len(files) >= 8`; this one does not. |
| RF-23 | `effective_n.py:207` | The validation-role floor conjunction (`or` → `and`) survives: raw 500 against floors (100 raw, 1000 N_eff) flips `INSUFFICIENT_SAMPLE` → `SAMPLE_SUFFICIENT`. Every existing validation test violates both floors or neither. The holdout equivalent **is** killed. |
| RF-24 | `aggregation.py:350` | One-minute gaps are unpinned (`hole > 0` → `hole > 1` survives): minutes 0,2,4,…,14 report `{7, 1}` pristine and `{0, 0}` mutated. Existing gap tests use 28-, 30-, 9- and 3-minute holes. |
| RF-25 | `aggregation.py:276` | The negative-`spread_close` guard — which PR #442 deliberately de-`pragma`'d as *reachable* — has **no test**. Deleting it leaves the suite green (see RF-3, its source-side twin). |
| RF-26 | `aggregation.py:175`, `effective_n.py:86` | The BL-1 "lazy evidence" lesson reached `no_overlap` only. A **generator** of 15 M1 rows, and a generator of per-pair records, are both rejected by correct source that no test pins. |
| RF-27 | `cost_schema.py:143`, `artifacts.py:152` | Vacuous-input rejection unpinned: `entries: []` → `COST_TABLE_SCHEMA_VALID` under the mutant; `validate_metadata_artifact("PASS"|42|None)` all accepted under the mutant. |
| RF-28 | `warmup.py:32-37` | A zero `longest_feature_lookback_bars` is unpinned (`<= 0` → `< 0` survives), yielding valid warm-up metadata for a zero lookback. |
| RF-29 | `aggregation.py:116`, `effective_n.py:96`, `cost_schema.py:126` | "Fails closed with the documented exception type" is unverified in three places: a missing side key raises bare `KeyError`, a missing `overlap_fraction` bare `KeyError`, a non-`dict` cost table bare `TypeError` under the mutants. RF-6 of the merged audit raised exactly this class and was never generalised. |

---

## 6. What re-derives CLEAN

Recorded because a false clean is as dangerous as a missed defect, and because
the blockers above should not be read as condemning the whole package.

- **Containment is CLEAN, proved not inherited.** Transitive module-level import
  closure is 17 repo modules and **zero** third-party packages; an audit-hooked
  subprocess import performs no file read, no directory creation, no network
  call, no environment access. An AST sweep over the whole closure finds **no
  read primitive at all** (`open`, `read_text`, `read_bytes`, `read_csv/json/
  parquet/pickle`, `glob`, `iterdir`, `walk`, `listdir`, `scandir`, `load`).
  The only two write primitives sit in one function with no production caller,
  behind refusals that fire before any filesystem mutation. No `__main__`, no
  CLI, no argparse, no entry point, no workflow reference. Nothing outside
  `tests/m15_gate3a/` imports the package. No training, validation, holdout,
  inference, execution, broker, model-binary, credential or external-storage
  route exists.
- **Path aliasing is comprehensively closed** against an existing protected
  root: 22 spellings whose `os.path.samefile` ground truth is `True` — plain,
  8.3 short name, `..` round-trip, trailing dot/space, `\\?\`, `\\?\UNC\` in
  three casings, `\\localhost\C$`, `\\127.0.0.1\C$`, `\\?\Volume{GUID}`, and all
  forward-slash forms — **all refused**. `\\.\` device refused outright.
- **PAIRS_20** is element-by-element **and in order** identical to the canonical
  `stage23_0a` universe (lead-verified by AST extraction).
- **Pip authority**: 20/20 exact against the frozen rule, 6 JPY → `0.01`, 14 →
  `0.0001`; aliases canonicalise; off-universe names refuse. No global pip size.
- **Effective-N** reproduces the approved spec's own counter-example to the last
  float bit (lead-verified: 50 @ overlap 0.0 + 8000 @ overlap 1.0 →
  `383.3333333333333` → `INSUFFICIENT_SAMPLE`). Floors enforced conjunctively;
  unknown roles refuse; validation never default-sufficient; horizon frozen at 24
  for every role.
- **Aggregation core**: open/close/high/low per side correct; **no mid price
  constructed**; eligibility = 15 distinct minute-aligned minutes; duplicates,
  sub-minute remainders, naive datetimes, NaN/inf/bool/str all fail closed;
  unsorted input yields identical bars; a 48 h closure emits exactly 2 bars with
  **no synthetic weekend bars** and no imputation.
- **T-7 boundary arithmetic**: `2026-02-28T23:59:59Z` accepted,
  `…23:59:59.000001Z` and `2026-03-01T00:00:00Z` refused; forward floor
  symmetric; the dead window's final second is covered; span constants
  byte-identical to `no_overlap_proof.json`; ordering and contiguity enforced
  with explicit `raise` (not stripped under `python -O`).
- **Evidence identity**: one physical file presenting as twenty is defeated three
  independent ways (record `id()`, duplicate `filename`, duplicate `sha256`);
  identity keys are mandatory; a `Mapping` whose `.get` cycles is defeated by the
  snapshot; lying `__len__`, unstable iteration and `__getitem__`/iteration
  disagreement all refuse.
- **Timestamp authority routing**: `astimezone`, `fromisoformat` and `utcnow`
  appear **only** in `timeutil.py`; no module reaches a bucket or bound decision
  around it. `utcoffset() → None` refused; `pandas.Timestamp` nanoseconds
  refused, not truncated; dot-spelled 7-digit fractions refused.
- **Forbidden-status set** equals playbook §10 exactly (14 tokens, set-equal).
- **Frozen cost constants** (`SESSIONS_UTC`, `0.3`, `0.5`, the formula string)
  are byte-identical to the committed plan; the session partition is proven at
  import time to tile the UTC day exactly once; p95 is mandatory; quantile
  monotonicity enforced.
- **All 8 committed `artifacts/m15_gate3a/*.json` pass `scan_gate3a`** — though,
  per B-1, that pass proves less than it appears to.
- **No invented numeric constant remains** in `scripts/m15_gate3a/**`. Every
  module-level number traces to committed authority. `MAX_PLAUSIBLE_SPREAD_PIPS`
  is genuinely gone.

---

## 7. Contract referrals — re-evaluation

Independently re-derived from committed authority. No threshold or rule was
invented by this audit; where no authority exists, that is the finding.

| # | Referral | Classification |
| --- | --- | --- |
| 1 | Spread magnitude bound | **`MAY_DEFER_BEYOND_GATE3A_CONTINUATION`** |
| 2 | `missing_minute_count` semantics | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** |
| 3 | Crossed-quote disposition | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** |
| 4 | Drop-ratio acceptance | **`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`** |
| 5 | Forward evidence shape | **`MAY_DEFER_BEYOND_GATE3A_CONTINUATION`** |

**1 — Spread magnitude bound → MAY_DEFER.** Confirmed: no committed authority
pins an absolute bound. All cost authority is *relative* (`median + 0.3 + 0.5`;
2×/p90 stress; barrier/cost ≥ 3.0). Playbook §5 makes cost tables optional and
separately authorised, and `max_spread_pips=None` records
`REQUIRES_SEPARATE_CONTRACT_GATE_DECISION` while still reporting observed pips.
Binds at latest at the pre-run authorisation gate (§6, "Cost tables fixed").
Two conditions on deferral: the continuation must pass `None` **explicitly**
(any number would re-mint the constant BL-5 removed), and it must be recorded
that `_check_magnitude_bound` accepts any finite positive value — `1e308`
satisfies "a bound was declared" while excluding nothing.

**2 — `missing_minute_count` semantics → MUST_RESOLVE.** The committed
`design_m15_inventory.json:15` `gap_report` schema is exactly
`{"missing_minute_count": "int", "max_gap_minutes": "int"}`. `_build_gap_report`
emits **17** keys (lead-verified). The continuation must populate that field and
cannot do so without deciding its meaning. Lead-verified, the divergence has
**three** causes, not the two the referral names:

```
15 present source minutes, 3 crossed:  missing_minute_count=0,
    total_missing_source_minutes_within_emitted_buckets=3   <- quality drops counted as missing
48h market closure:                    missing_minute_count=2865, max_gap_minutes=2865
```

The third cause — crossed-quote drops counted as missing source minutes —
directly contradicts the module's own docstring (`aggregation.py:305-309`: "the
gap metrics describe SOURCE coverage, the drop counters describe quality
rejection"). Evidence for the decision-maker, not a ruling: the M1 predecessor
inventory named as `source_checksum_authority` carries a `gap_profile` counting
closure gaps, so **in this lineage closure counts as a gap**. That is a different
key, unit and structure, so it informs the decision without settling it.

**3 — Crossed-quote disposition → MUST_RESOLVE.** See B-4.

**4 — Drop-ratio acceptance → MUST_RESOLVE** (derivative of 3). No committed
authority pins a ratio; the source correctly declines to invent one
(`aggregation.py:311-314`) and reports `all_rows_dropped` without raising. It
must resolve because the continuation **is** the adoption gate for the design
dataset and has no rule for deciding whether a file that lost an arbitrary
fraction of its minutes is admissible. A legitimate resolution may be "human
judgement recorded at the continuation approval" — but that is itself a
Gate-decision. If 3 resolves back to a hard assertion, 4 is moot; decide them
together.

**5 — Forward evidence shape → MAY_DEFER.** Deferral is itself committed:
`forward_epoch_adoption_manifest.json:23-28` marks the forward spans and
inventory checksum `PENDING … [FIXED-AT gate 3a continuation]`. Playbook §5 is
design-span only and states forward remains WAIT; the inventory is
`EMPTY__NO_FORWARD_DATA_EXISTS`, `file_count: 0`. The refusal at
`no_overlap.py:298-304` is correct, not merely conservative: the committed
forward schema's per-file `role: validation | holdout` split means two records
name one pair, which `_roster_report` must reject. Binds at the forward-epoch
adoption continuation (earliest ≈ 2026-10).

---

## 8. Contract questions the source is deciding silently

Not on the five-referral list; each is a semantic, default or disposition no
committed authority pins. Recommended for addition to playbook §1.

- **NR-A — is `artifacts/m15_gate3a/` protected-immutable or the continuation's
  output directory?** Playbook §9 requires it untouched; §5 requires the
  continuation to populate an artifact inside it; `guards.py` permits the write
  (B-5). Neither reading is supported over the other by any committed source.
- **NR-B — in what format must the continuation emit `ts_min_utc`/`ts_max_utc`?**
  `timeutil` refuses >6 fractional digits, and the committed M1 inventory named
  as `source_checksum_authority` writes **9**
  (`"2025-04-24T22:03:00.000000000Z"`, lead-verified). Refusing is fail-closed
  and therefore safe, but nothing decides whether the house format is to be
  normalised, re-emitted or accepted.
- **NR-C — who computes and attests the committed aggregate assertions?**
  `dead_window_bars_present: 0` is declared in `design_m15_inventory.json:22`
  and emitted by no code path (see B-2).
- **NR-D — duplicate source minutes abort the whole pair** (`aggregation.py:195`)
  while crossed quotes are a counted drop. Two opposite dispositions for two
  anomaly classes, neither pinned. Resolve with referral 3.
- **NR-E — the lower spread-magnitude limb is already decided** by the same
  disputed `stage25_0a` analogy (`cost_schema.py:181-186`, "no floor is
  imposed"). Referral 1 is scoped to the upper bound; if the analogy falls with
  referral 3, this falls with it.
- **NR-F — the frozen all-in-cost formula is dimensionally incoherent.**
  `SPREAD_UNIT = "price"` while the formula adds pip-unit constants
  (`cost_schema.py:56-59`). A conversion step is implied and nowhere stated. This
  was flagged in a merged fix note but **never reached the playbook referral
  table**, so it is invisible to a session reading only the playbook.
- **NR-G — validation-role sample floors are unpinned.** The committed spec says
  "below **the family's minimum**"; only holdout floors are frozen. The code
  correctly refuses to default, but the omission was never referred. Binds at the
  validation kill gate.
- **NR-H — the scrubber's four shape thresholds are invented numbers**
  (`artifacts.py:73-76`) and interact with referral 2: the natural shape for 20
  per-file gap reports is refused by a threshold nobody pinned.
- **NR-J — merged-audit R-8's fourth limb was re-disposed without referral**
  (RF-19). Same governance class as referral 3: an implementing session changed
  the remedy prescribed by a merged audit verdict, inside a Work PR.
- **NR-I — the rollover exclusion window has no representation.** Ruling 4
  freezes "rollover exclusion 21:55–22:15 UTC minimum — widen-only". `grep` over
  the package returns zero hits, and `_check_session_partition()` actively
  *requires* the three sessions to tile all 1440 minutes, so no carve-out is
  even expressible. Escalates to a required fix if cost-table production is
  authorised.

**Source/record contradiction.** `aggregation.py:36-38` still states "Aborting
the whole pair was this package's own invention." The merged PR #439 audit
prescribed it (`:411-412`), and the implementing session's own note already
retracted the claim — but the retraction never reached the source. The source
and the merged record now disagree.

---

## 9. Test adequacy and mutation resistance

356 tests pass and **every blocker and required fix above is invisible to them**.
That is the headline: the suite constrains the implementations it was written
alongside, not the contract.

**Measured mutation resistance.** 182 mutations applied to a scratchpad copy of
the repository, suite re-run for each, then a pristine-vs-mutated behavioural
probe run to separate genuine holes from equivalent mutants:

| | count |
| --- | --- |
| applied | 182 |
| killed | 154 |
| survived | 28 |
| survivors that are genuine coverage holes | **19** |
| survivors verified equivalent / redundant / unreachable | 9 |
| mutation score | 84.6 % (89.0 % of the 173 non-equivalent mutants) |

Per module, survivors fall as: `aggregation` 5, `no_overlap` 5, `timeutil` 4,
`effective_n` 4, `artifacts` 3, `warmup` 3, `__init__` 3, `cost_schema` 2. Three
modules are effectively airtight — **`guards` 12/12, `path_authority` 13/13,
`pair_authority` 7/7 mutants killed**.

**Where the suite is excellent.** Where a test was written against a *named*
defect it constrains tightly: the BL-1 evidence-binding family (9 guards, 9/9
killed) and the BL-3 path-aliasing family (13/13 killed) are exemplary, and the
cost-schema, guards, scrubber-shape and pair-authority families are solid.
Regression discipline is genuine: reverting the fix for F-1…F-5, B-1…B-5,
R-1…R-10 and BL-1…BL-5 makes at least one test fail in every case but two
(RF-21, RF-24).

**Where it fails, and the shape of the failure.** The gaps are not random. Every
one sits on a surface against which no blocker was ever filed — the two epoch
range limbs (B-7a), the always-binding status constants (B-7b), the
validation-role floors, vacuous inputs, the exception-type contract, the
one-minute gap. The suite tests the defects that were found, not the contract
that was specified. Three of those surfaces are precisely the
contamination-boundary and status-claim surfaces this gate exists to protect.

Concretely, no test would fail if: the scrubber's traversal stopped seeing
dict-keyed records (B-1a); a forbidden claim were embedded in a sentence or
spelled with a homoglyph (B-1b/c); the published span diverged from the checked
one (B-3); a bar were emitted with `high < low` (RF-3); a `Path` subclass lied to
`refuse_real_path` (RF-5); `artifacts/m15_gate3a/*` were written (B-5); or a
comma-spelled sub-microsecond timestamp were truncated (RF-1).

**Two tests measure host state rather than code.**
`test_d1_unc_and_extended_aliases_of_a_protected_path_refused`
(`test_recheck_fixes.py:909-925`) passes only because
`artifacts/ml_step4/365d_ba_v1` exists on disk; in a copy without it the test
**fails**. Both trees are git-tracked so CI is safe today, but the assertion is
environmental. Related and more serious as a *source* matter:
`test_bl3_a_genuinely_absent_protected_root_is_not_a_match`
(`test_second_recheck_fixes.py:801-804`) **freezes a fail-open as expected
behaviour** — with the protected root absent, `refuse_real_path` allows
`\\localhost\C$\…` and `\\?\UNC\…` spellings while refusing the plain ones,
i.e. containment degrades to name-only in exactly the case the source docstring
calls "the usual case for a write". Recorded against B-5.

**The skipped test is not a material gap.** `test_second_recheck_fixes.py:779`
(symlink creation not permitted on this host) calls `.resolve()` on the alias
before passing it, so the *name* limb answers before the identity limb runs — it
would not prove what it appears to. The identity limb is independently covered by
tests that do run and do kill their mutants, and the lead separately exercised 22
alias spellings that resolve on this host.

**Judgement.** The suite is **not adequate as standalone evidence for an Amber
research gate**, and a green run of `tests/m15_gate3a/` must not be cited as
evidence that design and forward data cannot be interchanged, nor that the
package's always-binding statuses are intact — it demonstrates neither.

---

**Non-blocking test observations.** Regex alternations that cannot identify which
guard fired (`match="high .* < low|OHLC incoherent"` at `test_recheck_fixes.py:272`,
`match="high|incoherent"` at `:205`, `match="dead window|DESIGN_END"` at `:412`) —
the last of these is what conceals B-7a. The host-zone source scan
(`test_second_recheck_fixes.py:530-545`) covers 4 of the 11 modules and is
fragile against docstring rewording. `EXPECTED_ARTIFACT_FILES`
(`artifacts.py:48-57`) has no consumer and no test. Excluding `bool` from
`_numeric_field_count` is unpinned, but the mutation makes the scrubber
*stricter*, so it is not a fail-open.

## 10. Disagreements and how they were resolved

- **A role's BLOCKER was demoted by the lead.** The adversarial role reported
  that a lying `datetime` subclass earns the T-7 token for wholly dead-window
  evidence, and graded it a blocker. The reproduction is real, but the lead's
  control experiment shows **20 plain ISO strings already earn the same token**,
  because the proof never reads bytes. The subclass therefore grants no
  capability ordinary declared metadata does not. The finding was demoted to
  RF-2 (a false documented guarantee) and its substance re-stated as the
  structural blocker B-2. Recorded because the difference matters: fixing the
  subclass check would not fix the proof.
- **Apparent conflict on the scrubber.** The contract role recorded the scrubber
  as clean against naive smuggling shapes; the artifact and adversarial roles
  found it bypassable. Both are correct and were reproduced: literal shapes trip,
  re-encodings do not. Resolved as B-1 without discounting either.
- **Apparent conflict on `assert_no_forbidden_operation`.** One role recorded it
  as correctly fail-closed on unknown flags; another found `training=False`
  silently allowed. Resolved: the unknown-flag rule holds **only for truthy**
  values, and the guard has no callers — both statements are true (RF-14, RF-15).
- **No unresolved material disagreement remains.**

---

## 11. Non-authorisation

This document authorises nothing. It does not permit a real data read, a real
M15 derivation, a real checksum or spread computation, validation, holdout,
training, inference, execution, or any broker/paper/live activity. It does not
adopt an epoch, does not lift the forward-epoch WAIT, and does not claim
production readiness or reproducibility under a frozen `uv` environment (the
lockfile remains known-stale; `uv sync --frozen` reproducibility is **not**
claimed). Per policy §12, the AI performing this audit may not give final
approval for this Amber gate — that is a human + ChatGPT decision.

---

## 12. Gates still required before a gate-3a continuation

In order. None may be self-granted, and none may be skipped because an internal
audit was run.

1. **One targeted-fix Work PR** closing B-1…B-7 and RF-1…RF-29 — code, tests,
   docs, internal audit and CI repair in a single PR (policy §14). The 19
   genuine mutation survivors in §9 are the minimum test-side acceptance bar.
2. **A fourth independent source-audit re-check** in a session separate from
   every fix author, accepting those fixes.
3. **A contract Gate-decision** resolving referrals 2, 3 and 4 — and, in the
   same decision, NR-A (is `artifacts/m15_gate3a/` writable by the
   continuation?), NR-C (who attests `dead_window_bars_present`), NR-D
   (duplicate-minute disposition) and NR-J (the re-disposed R-8 limb), which are
   inseparable from them. This is a **human + ChatGPT ruling**, not an audit
   output. Referrals 1 and 5 and the remaining NR items may defer, with the
   conditions in §7 and §8.
4. **A design decision for B-2** — how a byte-level no-overlap proof is produced
   at all, given that the package must not read data.
5. Only then a **separately-authorised gate-3a continuation** (playbook §5).

**Recommendation.** Do not merge this document as an acceptance of anything; it
is a record of a blocked re-check. Fix B-1…B-6 and RF-1…RF-19 in one Work PR,
and take referrals 2/3/4 + NR-A/NR-D to a human + ChatGPT contract Gate-decision
**before** that Work PR settles the crossed-quote and gap-report semantics —
otherwise the fix session will be deciding the same contract questions this audit
just found it may not decide.
