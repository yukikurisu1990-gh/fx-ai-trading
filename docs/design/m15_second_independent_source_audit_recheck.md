# Second independent source-audit re-check — B-1…B-5 / R-1…R-10 / D1…D6 (PR #440)

- **Document class:** doc-only Gate-decision record. Judges the technical state
  of the merged M15 gate-3a machinery. Executes nothing; authorises nothing.
- **Audit target:** master `9c36cb0c163df95a7abccbf43023df57883a7797`; the fix
  under review is PR #440 (merge commit `9c36cb0`), on base `facef30`.
- **Predecessors:** `docs/design/m15_aggregation_dataset_machinery_source_audit_fable5.md`
  (PR #433, F-1…F-5) → `docs/design/m15_aggregation_dataset_machinery_source_audit_recheck.md`
  (PR #439, B-1…B-5 + R-1…R-10) → `docs/design/m15_recheck_targeted_fixes_note.md`
  (PR #440's own fix record, treated here as a claim under test).
- **Risk tier:** Amber (`docs/governance/autonomous_development_policy.md` §3/§5).

## Statuses

- **Required final status (playbook §4, exactly one):**
  **`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`**
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_AGGREGATION_DATASET_MACHINERY_RECHECK_FIXES_PROPOSED`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** ·
  **`NO_EXECUTION_PERFORMED`**

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `PRODUCTION_READY`,
`READY_FOR_LIVE`, `M15_AUTHORISED`, `H1_AUTHORISED`, `H2_STARTED`,
`PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`,
`DEPLOYABLE` appear in this document only inside prohibition lists.

---

## 0. Independence limitation — read this first

`docs/governance/autonomous_development_policy.md` §12 requires an independent
audit to run in a **session separate** from the one that produced the work, and
states that self-review by the implementing session does not satisfy it.

**This re-check does not fully satisfy that requirement.** The lead session is
the same session that authored PR #440. What was done to compensate:

- Four audit roles ran as **fresh subagents** with no implementation context,
  each given only the source, the diff, the requirements document and an
  adversarial brief, and none given the others' conclusions.
- Every blocker below was **re-derived by the lead with its own probe** before
  being recorded; none is accepted on a subagent's word.
- The lead's compensating bias is disclosed rather than hidden: this audit
  finds **five blockers in the lead's own prior work**, which is the outcome
  the independence rule exists to make possible, but it is not a substitute for
  a genuinely separate session.

**Recommendation to the human + ChatGPT reviewers:** treat this document as a
*pre-audit* with high evidentiary content but deficient independence. Either
commission a re-check from a genuinely fresh session before acting on an
acceptance, or record an explicit waiver. Since the verdict here is BLOCKED,
the deficiency does not risk an unsafe acceptance in this instance.

## 1. Executive verdict

**B-1, B-2, B-3, B-4 and B-5 are genuinely closed**, and D1…D6 are closed
except where noted. Containment re-derives clean: the eager import closure of
`scripts/m15_gate3a/**` is stdlib-only, the reverse-caller set is
`tests/m15_gate3a/` only, and every forbidden route — real-data read, M15
derivation from bytes, validation, holdout, training, inference, execution,
broker/live/paper, external storage, model binary, CLI — is NOT REACHABLE. No
guard was loosened; the only new capability is filesystem **stat** metadata in
`guards.py`. All eight committed `artifacts/m15_gate3a/*.json` remain
scrub-clean under the tightened scrubber, including the legitimate
`"production_ready": false` negative declarations.

**Nevertheless this re-check BLOCKS**, on five defects — four of them inside
code PR #440 newly added, in the exact controls it set out to strengthen, and
all five biting the gate-3a continuation that acceptance would unlock:

| # | Defect | Why it blocks |
| --- | --- | --- |
| **BL-1** | `assert_per_file_bounds` still returns `PROVEN_NO_DEAD_WINDOW_OVERLAP` on zero evidence, and accepts 20 identical records for `expected_count=20` | This *is* the machine-checkable T-7 proof the continuation must emit; D2 is not closed |
| **BL-2** | `tzinfo is None` is not Python's awareness test — five sites silently reinterpret a timestamp in **host local time** | Reopens the F-5 class; produced a bucket 9 hours wrong, and makes the dead-window verdict host-dependent |
| **BL-3** | The protected-path guard is defeated two ways: `\\?\unc\` casing, and ancestor-walk exhaustion failing **open** | The continuation writes artifacts; both routes are in code added by PR #440 for R-3 |
| **BL-4** | Crossed-quote rows abort the whole pair, contradicting this repo's own committed drop-and-count treatment of that documented real-data anomaly | The continuation would halt on first contact with the archive |
| **BL-5** | The cost-table magnitude ceiling is blind for JPY pairs (a 100× pip-unit error validates) and has no lower bound (`0.0` and `1e-9` validate) | The continuation produces the cost tables; this is B-4's 100× class re-entering through the cost path |

Alongside these, **RF-8…RF-11 record four test-coverage gaps where the shipped
source is correct but a regression would go unnoticed** — most importantly, the
entire B-1 regression proof skips in a pandas-free interpreter, where every B-1
mutation survives.

No rewrite is warranted. The architecture is sound, the previously-blocked
defects are genuinely fixed, and every finding below is a small, precisely
scoped change.

## 2. Method and independence

- Four audit roles as fresh subagents, each with the source, diff, requirements
  and an adversarial brief, and **none** with the others' conclusions:
  contract / specification / data-boundary; adversarial / bypass; test adequacy
  and mutation; containment / import graph / dependency.
- PR #440's description, commit messages, docstrings and fix note were treated
  as **claims under test**. Two of its claims are refuted (§7).
- The lead ran **62 of its own probes** across B-1…B-5, D1…D6, R-2, R-6 and
  R-8 (all held), then independently reproduced **every** blocker below.
- Materials: master source and tests; `git diff facef30 9c36cb0`; the PR #439
  requirements document; the PR #440 fix note; the committed
  `effective_n_estimator_spec.json`, `design_m15_inventory.json`,
  `cost_table_plan_or_metadata.json` and `no_overlap_proof.json`; the frozen
  pre-registration contract; the playbook §4 checklist and §10 label list.
- Synthetic literals only. No real data read, no derivation, no checksum or
  spread computation, no validation, holdout, training, inference or execution.
  No repo file was modified (`git status --porcelain` empty throughout);
  `uv sync` was deliberately **not** run (it rewrites the venv against the
  known-stale lock). Probes and mutation copies lived only in a scratch
  directory; filesystem test objects were removed and removal verified.

## 3. B-1…B-5 — re-adjudication

### B-1 — pandas / datetime-subclass nanoseconds · **CLOSED**

`_plain_utc_minute` (`aggregation.py:62-92`) rebuilds a plain UTC `datetime`
from components and **returns that**, so bucket keys and the duplicate set
cannot carry subclass resolution into the pipeline. Lead probes, all rejected: a single
`pd.Timestamp` at `ns=500`; fifteen ns-bearing rows; the same fifteen minutes at
`ns=0` and `ns=500`; a subclass with an always-true `__eq__` and `second=30`; a
subclass exposing `nanosecond=500`; `pd.NaT`. An aligned pandas bucket is
accepted and its `ts` is a **plain** `datetime` on a 15-minute boundary; a
`+05:45` offset normalises correctly. The adversarial role added 19 further
attacks (`as_unit` variants, `numpy.datetime64`, `astimezone`-liars, zoneinfo
DST folds, `+00:00:30`) — all held. **No probe produced a non-aligned bucket
start or two eligible bars for one window.**

**One qualification, lead-verified.** The two guards are *not* universal over
subclasses. A stdlib subclass that stores extra resolution **outside** the
fields `datetime` comparison inspects and does **not** expose `.nanosecond` is
blind to both limbs and is accepted:

```
class PicoDatetime(datetime):  # holds `pico` in a private attribute
    ...
PicoDatetime(2025, 6, 2, tzinfo=UTC, pico=500) == datetime(2025, 6, 2, tzinfo=UTC)  -> True
aggregate_m15([row(that)], pair="EUR_USD")  -> ACCEPTED
```

Consequence is bounded and **not** the F-1 pathology: the emitted bucket key is
still a **plain `datetime`** at exactly `2025-06-02T00:00:00+00:00`, so the
extra resolution is discarded rather than propagated — no wrong bucket, no
duplicate eligible bar. The defect is that such a row is accepted where the
guard's stated contract says it should fail closed. `pandas.Timestamp` — the
only realistic carrier — is correctly handled by both limbs. This makes the
fix note's claim that the equality check "generalises … any subclass, known or
not" **false** (§7), and is recorded as RF-8.

### B-2 — reversed / insufficient spans · **CLOSED for reversal; see BL-1**

`_assert_ordered` runs in all three bound-checkers. Reversed spans, spans
containing the dead window, non-mapping entries, generators, `iter([])`, dicts,
sets and map objects are all rejected; a valid design file is still proven; an
`expected_count` mismatch is rejected. The *reversal* limb B-2 named is
genuinely fixed. The **proof-without-evidence** property is not (BL-1).

### B-3 — effective-N vs the APPROVED spec · **CLOSED**

The committed `effective_n_estimator_spec.json` formula is implemented
literally. The audited counter-example reproduces exactly: 50 events at overlap
0.0 plus 8000 at overlap 1.0, corr 0 → `N_eff = 383.3333`,
`INSUFFICIENT_SAMPLE`. Per-pair **and** portfolio granularity are both emitted.
Floors are unchanged and verdict-driving at the boundary (999/1000 raw;
399.96/400.00 N_eff). The horizon is frozen at 24 **for every role** — stricter
than R-1 required. Role handling fails closed. The test that previously
*entrenched* the divergent formula is gone.

### B-4 — pair authority · **CLOSED**

`pair_authority.PAIRS_20` is element- and order-identical to the three
committed canonical lists (`fetch_oanda_archive.py`,
`stage22_0a_scalp_label_design.py`, `stage23_0a_build_outcome_dataset.py`), and
a test binds it to two of them by AST — the fix note's claim on this point is
**true**. Normalisation is injective over the universe and across a
13-spelling family per pair (260 probes, no cross-pair mapping). All 20 pairs
resolve to the correct pip; every JPY spelling tried (`usd_jpy`, `USDJPY`,
`USD/JPY`, `usd-jpy`, `" USD_JPY "`, `Usd.Jpy`) gives `0.01` and
`to_pips(0.02, "usd_jpy") == 2.0`. Off-universe, non-string, fullwidth,
zero-width and homoglyph inputs fail closed. No un-normalised caller string
reaches `data_adapter.pip_size_for` from inside the package. The gap report now
emits the canonical label only.

### B-5 — validation floors · **CLOSED**

NaN, `inf`, `0`, negative, bool, string, non-integral and partial floors are
all rejected; unspecified floors give `NOT_EVALUATED_AT_THIS_ROLE`; the applied
floors are echoed in `floors_applied`. Zero events cannot reach
`SAMPLE_SUFFICIENT`.

## 4. D1…D6 — re-adjudication

| # | Verdict | Evidence |
| --- | --- | --- |
| **D1** path aliases | **CLOSED in substance, DEFEATED in two spellings** — see BL-3. Plain, `\\?\`, uppercase `\\?\UNC\`, plain UNC, `\\.\`, 8.3, junction, case, traversal, trailing dot/space and non-existent children are all refused |
| **D2** zero-evidence T-7 proof | **NOT CLOSED** — see BL-1 |
| **D3** forbidden status as a dict key | **CLOSED** — truthy keys and values refused at depth; `"production_ready": false` correctly still accepted; all 8 committed artifacts clean |
| **D4** pair aliases in effective-N | **CLOSED** — `usd_jpy`/`USD_JPY` now collide into one duplicate error; off-universe labels rejected |
| **D5** canonical stamping | **CLOSED** — five spellings of one pair all emit `USD_JPY` |
| **D6** non-finite in artifacts | **CLOSED** — NaN/±inf caught in every JSON-representable position; overflowing `N_eff` rejected; written artifacts re-parse under a strict reader |

## 5. R-1…R-10 — re-adjudication

| # | Verdict |
| --- | --- |
| R-1 horizon | **Closed, stricter than required** (frozen for every role, echoed) |
| R-2 row coherence | **Closed as written, but see BL-4** — the per-side checks are definitional and cannot over-reject; the cross-side check aborts on a documented anomaly |
| R-3 `\\?\` alias | **Closed for the named spelling; two new routes open** — BL-3 |
| R-4 status control | **Closed** — reachable on the write path; set matches playbook §10 exactly (14/14) |
| R-5 row-like heuristic | **Closed for the named evasion**; residual evasions remain (§8 NB-4) |
| R-6 derived finiteness | **Closed** — finite inputs overflowing to `inf` are rejected |
| R-7 gap report | **Closed on keys, undefined on semantics** — §8 RF-2 |
| R-8 cost schema | **Partly closed** — unit, formula and monotonicity pinned; magnitude ceiling defective (BL-5); coverage reported-not-enforced (accepted) |
| R-9 artifact name | **Closed** — separators, absolute, ADS, empty stem all refused; no stray directory on refusal |
| R-10 test gaps | **Closed** — see §6 |

## 6. Test and mutation adequacy

253/253 tests pass, with **0 skips** in a clean `pip install -e ".[dev]"`
environment; the eleven `@requires_pandas` B-1 proofs execute. The divergent
formula pin is gone and `N_EFF_HOLDOUT_FLOOR` is now verdict-driving.

Two independent batteries were run on scratch copies: **84 mutations / 76
killed** (contract role) and **138 mutations / 120 killed** (test role), each
self-designed. Everything the previous audit listed as MISSED is now caught:
the microsecond+equality combination, `isfinite` on all **eight** side keys
individually, `max`↔`min` on all four extrema, positional-vs-aggregation on all
eight OHLC fields, the `spread_close` sign, within-bucket `sorted()` removal,
`DEAD_START → 2026-03-15`, the `DESIGN_START`/`DESIGN_END` shifts,
`_assert_ordered` removal at each call site, `N_EFF_HOLDOUT_FLOOR 400→100`,
`v < 0` removal, the warm-up `astimezone`→`replace` mutation, and **PAIRS_20
member substitution with the length preserved**.

Every survivor was resolved by **differential probe**, not by argument. The
deliberately redundant guard pairs are real — removing **both** members of each
is caught in every case. But the fix note's claim that "no genuine test gap
remains from the battery" is **falsified**: six survivors are genuine coverage
gaps, and the lead reproduced each to establish whether the *source* is also
wrong. **In every case the shipped source is correct** — these are test gaps,
not defects:

| Survivor | Source behaviour, lead-verified | Gap |
| --- | --- | --- |
| bucket-**order** sort removed | correct: out-of-order buckets still emit `00:00, 00:30, 00:45` chronologically with `missing_whole_buckets = 1` | no test feeds buckets out of order (RF-9) |
| `h ≥ max(o,c)` / `l ≤ min(o,c)` limb removed | correct: a row with `bid_c=1.50` above `bid_h=1.1002` raises "OHLC incoherent" | the existing `bid_h=0/bid_l=9` test reaches only the `h < l` limb (RF-10) |
| NFKC folding removed | correct: `ＰＡＳＳ` and `ＰＲＯＤＵＣＴＩＯＮ_ＲＥＡＤＹ` normalise to `PASS` / `PRODUCTION_READY` and are refused | no test supplies a fullwidth form (RF-11) |
| `SESSIONS_UTC` retargeted | correct: matches the committed plan | unpinned (RF-1) |
| `except OSError: return True` → `False` | correct as written | direction unpinned (RF-5) |
| `_ROW_LIKE_MIN_NUMERIC_FIELDS 6→8` | correct as written | threshold unpinned |

**A coverage hole that matters more than any of those:** in a pandas-free
interpreter the suite runs `247 passed, 6 skipped`, and **all five B-1
mutations survive — including "every guard removed"**. The headline blocker's
entire regression proof sits behind an optional import. A pure-stdlib
`datetime` subclass exposing `.nanosecond` reproduces the same input class and
kills those mutants, so the pandas gate is not necessary for the proof. → RF-8.

Clean-install check: a fresh venv with `pip install -e ".[dev]"` runs
`253 passed`, **0 skipped**, with pandas 3.0.5 — so the declared dev dependency
does achieve its stated purpose in CI and in a clean developer install.

## 7. Three claims in the merged fix note are refuted

- `docs/design/m15_recheck_targeted_fixes_note.md` §4 states the mutation
  survivors "are all members of the deliberately redundant pairs" and that "no
  genuine test gap remains from the battery". Two wider independent batteries
  (84 and 138 mutations) find six survivors outside that set.
- The same note (§4) claims the plain-datetime equality check "generalises …
  Any subclass with resolution finer than a microsecond — known or not — fails
  the comparison." **False**, lead-verified: `datetime.__eq__` inspects only
  (y, m, d, h, min, s, µs, offset), so a subclass holding extra resolution
  elsewhere and lacking `.nanosecond` compares equal and is accepted (§3).
- The same note (§2, R-1 row) describes the horizon as frozen "for
  `role='holdout'`". The merged code freezes it for **every** role — the code
  is stricter than its own record.

Both are documentation defects in a committed record, not code defects. A third
staleness: `docs/governance/m15_audit_playbook.md:53` still records the Work PR
as "**OPEN, not merged**" although it merged as `9c36cb0`; the binding rows
("continuation **NOT authorised**", "second independent re-check **NOT
started**") are correct.

## 8. Findings

### BLOCKERS — must be fixed before the gate-3a continuation

**BL-1 — the T-7 proof still certifies on zero evidence, and does not require
distinct files.** `no_overlap.py:136-152`. `checked` is never reconciled with
`len(files)`, and `Sequence` guarantees nothing about the relationship between
`__len__` and iteration. Reproduced by the lead:

```
class LazyInventory(Sequence):
    def __len__(self): return 20
    def __getitem__(self, i): raise IndexError(i)

assert_per_file_bounds(LazyInventory(), role="design", expected_count=20)
-> {'role': 'design', 'files_checked': 0, 'result': 'PROVEN_NO_DEAD_WINDOW_OVERLAP'}
```

`expected_count=20` is reported satisfied while **zero** bounds were evaluated.
Separately, and needing no exotic input at all:

```
assert_per_file_bounds([one_file]*20, role="design", expected_count=20)
-> {'files_checked': 20, 'result': 'PROVEN_NO_DEAD_WINDOW_OVERLAP'}
```

— twenty copies of one record satisfy a twenty-file inventory. This is the
function the continuation must use to emit the machine-checkable T-7 proof, and
D2 was raised precisely against "proof without evidence". Fix: reconcile
`checked` with `len(files)`, and require the records to be distinct.

**BL-2 — `tzinfo is None` is not Python's awareness test; five sites reinterpret
in host local time.** `aggregation.py:74`, `no_overlap.py:49`, `no_overlap.py:54`,
`warmup.py:53`, `warmup.py:58`. A `tzinfo` whose `utcoffset()` returns `None`
makes the datetime **naive** by Python's definition while `tzinfo is None` is
`False`; `astimezone(UTC)` then reinterprets the value in the host's local
zone. Reproduced by the lead on this host (UTC+9):

```
intended 2026-04-24T20:00 (inside the dead window), tzinfo.utcoffset() -> None
  tzinfo is None      -> False        <- the check performed
  utcoffset() is None -> True         <- Python's awareness test
  astimezone(UTC)     -> 2026-04-24T11:00:00+00:00   (shifted by the host offset)

aggregate_m15 with the same tzinfo:
  ACCEPTED; bucket ts = 2025-06-01T15:00:00+00:00   (intended 2025-06-02T00:00Z)
```

The aggregation case is **not fail-closed** — it silently emits a bucket nine
hours wrong. On this host the three no-overlap/warm-up guards happened to still
reject (the shifted instant remained inside the dead window); the adversarial
role reproduced the opposite outcome under `TZ=XXX9`, where the same input is
**admitted as forward-epoch**. So the dead-window verdict depends on the host
clock, which falsifies the previous re-check's finding that F-5 made behaviour
"independent of host timezone and DST".

Realism, stated honestly: the realistic loader path is unaffected —
`pd.to_datetime(..., utc=True)` yields `datetime.timezone.utc` with a proper
offset. The defect needs a hand-rolled or exotic `tzinfo`. But the guard exists
to fail closed on anything not provably UTC, and here it fails **open and
silently**. Fix: use `ts.utcoffset() is None` at all five sites.

**BL-3 — the protected-path guard is defeated by two routes, both in code added
by PR #440.** `guards.py:77-130`.

*Route (a) — extended-UNC prefix casing.* `_strip_extended_prefix` matches
`\\?\UNC\` case-**sensitively**; Windows does not. Reproduced:

| spelling | guard | `os.path.samefile(spelling, protected)` |
| --- | --- | --- |
| `\\?\UNC\localhost\C$\…\365d_ba_v1` | REFUSED | True |
| `\\?\unc\…` | **ALLOWED** | **True** |
| `\\?\Unc\…` | **ALLOWED** | **True** |
| `\\?\uNc\…` | **ALLOWED** | **True** |

Root cause verified: only `\\?\` is stripped, leaving the **relative** string
`unc\localhost\C$\…`, which resolves under the cwd and is therefore not
protected — while `os.path.exists(raw)` is `True`, i.e. the OS resolves the raw
spelling to the real protected directory. `write_metadata_artifact` builds
`Path(out_dir)` from the raw string, so the write would land inside the
protected tree.

*Route (b) — ancestor-walk exhaustion fails open.* `guards.py:117` returns
`False` after `_MAX_ANCESTOR_WALK = 64` iterations. Reproduced on a UNC-aliased
path below the protected directory: depth 62 → REFUSED, depth 63 → REFUSED,
depth **64 → ALLOWED**, depth 70 → ALLOWED. Plain drive-letter paths at the
same depths remain refused (the name test covers those). Since the intermediate
directories do not exist, `mkdir(parents=True)` would create the chain inside
the protected tree and then write.

Fix: casefold the extended-prefix match, and `return True` on walk exhaustion.

**BL-4 — crossed-quote rows abort the whole pair, contradicting this repo's own
treatment of that anomaly.** `aggregation.py:135-140` raises on
`ask_* < bid_*`. The per-side checks are definitional and safe; the cross-side
check is the problem, and it is settled **without reading real data** by
committed in-repo evidence:

- `scripts/stage25_0a_build_path_quality_dataset.py:191` lists "rows with
  negative spread (**data anomaly**)" as an expected drop category;
- `:242-245` computes `spread_pip = (entry_ask − entry_bid)/pip` on real
  `load_m1_ba` rows and **drops** them into a dedicated
  `dropped_invalid_spread` counter;
- `:220`, `:417`, `:424` and `:612` initialise, report per pair, and document
  that counter.

So the established, exercised treatment of `ask < bid` on this repository's
real M1 BA archive is **drop-and-count**, and the category is expected enough to
warrant a reported per-pair counter. The gate-3a machinery instead raises,
aborting the entire pair with no quarantine, no counter and no partial
degradation — so the continuation would halt on first contact, and the
tempting field fix (relaxing the assertion) would discard the R-2 protection.
The policy must be decided **before** the continuation, not during it. Fix:
adopt drop-and-count with a counter in the gap report, matching
`stage25_0a`, or record an explicit decision to abort — and keep the
assertions either way. Frequency remains unquantified (real-data read
forbidden); this classification rests on the in-repo precedent, not on a guess.

**BL-5 — the cost-table magnitude ceiling is blind for JPY pairs and has no
lower bound.** `cost_schema.py:31-33, 118-126`. The ceiling is
`MAX_PLAUSIBLE_SPREAD_PIPS (100) × pip_size`, i.e. `0.01` for non-JPY and
`1.0` for JPY. Reproduced:

| table (declared `spread_unit="price"`) | result |
| --- | --- |
| `EUR_USD median=0.8` (pip units — a 10,000× error) | rejected: "8000.0 pips" |
| `USD_JPY median=0.9, p90=0.95, p95=1.0` (pip units — a 100× error) | **ACCEPTED** |
| `median=p90=p95=0.0` | **ACCEPTED** (no lower bound) |
| `median=p90=p95=1e-9` | **ACCEPTED** (no lower bound) |
| `GBP_AUD p95 = 0.0101` (101 pips) | rejected — possible over-rejection |

Real USD_JPY spreads sit in exactly the 0.9–1.0 *pip* range, so a unit mistake
on the six JPY crosses passes silently, and an understated spread is the
**fail-open** direction for a cost hurdle. This is the same 100× JPY class B-4
exists to prevent, re-entering through the cost path — and the continuation is
the step that produces these tables. Whether a real US-session p95 on a wide
cross exceeds 100 pips is **not determinable without real data**; that is
recorded as an explicit constraint, not assumed away. Fix: add a lower
plausibility floor and make the ceiling detect the unit error rather than
normalise it away.

### REQUIRED FIXES

- **RF-1 — `SESSIONS_UTC` is a frozen pin with no test.** `cost_schema.py:16-20`
  matches `cost_table_plan_or_metadata.json` exactly today, but a mutation
  retargeting `"asia": "00:00-07:59"` → `"00:00-09:59"` survives the suite, and
  no test in `tests/` references any session string. Value-pin it against the
  committed plan.
- **RF-2 — `missing_minute_count` semantics are undefined against the committed
  inventory.** `aggregation.py:248-256` counts holes only *between* observed
  minutes, so a partial trailing bucket reports `0` while
  `total_missing_source_minutes_within_emitted_buckets` reports a non-zero
  figure; and every absent minute counts, so weekend closure will dominate a
  real design-span file. The continuation writes this field into the committed
  inventory — decide and record whether closure and head/tail minutes count.
- **RF-3 — `_names_protected` skips the identity check when the protected tree
  is absent.** `guards.py:106` returns `False` if `protected.exists()` is
  `False`, so on a checkout without `artifacts/` only the string comparison
  applies, reopening the whole D1 alias surface.
- **RF-4 — a test aims a write at the real protected evidence tree.**
  `tests/m15_gate3a/test_recheck_fixes.py:758-761` calls
  `write_metadata_artifact(repo_root()/"artifacts"/"ml_step4"/"365d_ba_v1"/"nb1_probe", …)`
  on every run. The guard refuses today; if it regresses, the suite itself
  litters the protected tree. Use a synthetic protected prefix.
- **RF-5 — the `except OSError: return True` fail-closed direction is unpinned.**
  `guards.py:115-116`; a mutation to `return False` survives the suite.
- **RF-6 — exception-contract violations.** A NUL byte in a path escapes
  `refuse_real_path` as a bare `ValueError` rather than `RealDataRefusedError`
  (lead-reproduced); `a\x00b.json` behaves likewise in the writer. Fail-closed
  in effect, wrong type for a caller that catches the documented exception.
- **RF-7 — correct the three refuted claims in the merged fix note** (§7) and
  the stale playbook row recording PR #440 as open.
- **RF-8 — B-1's regression proof vanishes without pandas, and the guard is not
  universal over subclasses.** In a pandas-free interpreter the six B-1 tests
  skip and **all five B-1 mutations survive, including "every guard removed"**.
  Separately, a stdlib subclass holding resolution outside the compared fields
  and lacking `.nanosecond` is accepted (§3). Both are closed by the same
  change: add a **pure-stdlib** `datetime` subclass exposing `.nanosecond` as an
  ungated regression test, and either widen the guard (e.g. reject `datetime`
  subclasses outright, or compare `timestamp()` against the rebuilt minute) or
  narrow the docstring's claim to what it actually guarantees.
- **RF-9 — bucket-level ordering is unpinned.** The source sorts correctly
  (verified: out-of-order buckets emit `00:00, 00:30, 00:45` with
  `missing_whole_buckets = 1`), but removing `order = sorted(buckets)` survives
  the suite. Add a test feeding buckets out of order and asserting both the bar
  sequence and the gap count.
- **RF-10 — half of R-2 is unpinned.** The source correctly rejects a row whose
  close sits above its high (verified: "OHLC incoherent"), but the existing
  `bid_h=0.0 / bid_l=9.0` case reaches only the `h < l` limb, so removing the
  `h ≥ max(o,c)` / `l ≤ min(o,c)` limb survives. Add a close-above-high case.
- **RF-11 — the NFKC limb of `normalise_status` is unpinned.** The source
  correctly folds `ＰＡＳＳ` and `ＰＲＯＤＵＣＴＩＯＮ_ＲＥＡＤＹ` (verified
  refused), but removing NFKC survives the suite. Add a fullwidth variant.

### NON-BLOCKING OBSERVATIONS

- **NB-1** Effective-N overstatement by *lumping*: 20 pairs × 500 events at
  overlap 1.0, corr 0.5 → `N_eff = 39.68 INSUFFICIENT`; the same 10,000 events
  declared as **one** pair → `N_eff = 416.67 SAMPLE_SUFFICIENT`. Nothing binds
  P to a declared universe size. Visible in the emitted record (`n_pairs`,
  `per_pair`), hence non-blocking — but the continuation must assert `n_pairs`
  against the roster.
- **NB-2** Hardlink write-through: a pre-existing NTFS hardlink at
  `out_dir/name` pointing into the protected tree lets the writer overwrite
  protected content, because `_names_protected` compares against the protected
  *directory*, never against files inside it. Requires prior filesystem write
  access, so it grants an attacker nothing new.
- **NB-3** Protection scope remains narrow (carried N-5): `artifacts/m15_gate3a/`
  — the gate's own eight committed artifacts — plus stage24/stage25, `data/`,
  and the sibling `firstrun_3650d_ba` / `firstrun_730d_ba` /
  `firstrun_pr_b2_dependency_pipeline` evidence directories are all writable.
  `data/` risk is ≈ nil because the writer accepts only a bare `.json` name and
  the archive is `.jsonl`.
- **NB-4** Residual scrubber evasions, all previously known and outside R-5's
  scope: a single 8-numeric record; two records × 5 numeric fields;
  numeric-as-strings; renamed metrics (`sharpe_ratio`, `holdout_sharpe`,
  `pnl_by_pair`); zero-width and homoglyph status variants; substrings.
  `_ROW_LIKE_MIN_NUMERIC_FIELDS 6→8` survives mutation.
- **NB-5** Scrubber false positives, all fail-closed and affecting no committed
  artifact: `{"production_ready": "false"}` and `{"production_ready":
  "NOT_CLAIMED"}` are flagged because a *string* negative declaration is
  truthy.
- **NB-6** `pandas` is imported directly by ten `src/**` modules but is not in
  `[project].dependencies` — it arrives transitively via `streamlit`. The
  `[dev]` addition is correct for its stated purpose (the B-1 proofs run,
  0 skips) but slightly reduces the chance CI would ever surface the runtime
  gap. Pre-existing; recommend declaring pandas as a runtime dependency too.
  Separately, `>=2.0,<4.0` admits a major-version jump for a regression anchor
  that depends on `Timestamp.nanosecond` semantics.
- **NB-7** `uv.lock` drift re-confirmed read-only: five runtime distributions
  (lightgbm, scikit-learn, pyyaml, plotly, pyarrow-as-direct) plus
  pandas-as-direct are missing from `requires-dist`, and the ruff spec still
  reads `>=0.6,<1.0` against the pinned `==0.15.11`. **No impact on gate-3a** —
  the package's eager closure is stdlib-only and CI's authority is
  `pip install -e ".[dev]"`. Frozen-uv reproducibility remains unclaimed.
- **NB-8** Carried from the fix note and re-confirmed: N-2 (the `guards.py`
  module docstring still overstates its reach; the substantive control is now
  `is_forbidden_status`), N-6, N-7, N-8, N-9, N-10. `pair_authority.PAIRS_20`
  is a third hand-maintained copy of the universe, though the AST test makes
  drift detectable.
- **NB-9** A network path to an unreachable host stalled `refuse_real_path` for
  21 s, attributable to the pre-existing `Path().resolve()` rather than the new
  walk; the walk can nonetheless multiply per-stat latency by up to 128 on a
  slow mount. Bounded in iterations, unbounded in wall-clock.
- **NB-10** R-8's coverage limb is reported, not enforced — accepted, because
  the committed plan defers table production and `validate_cost_table` has no
  phase argument. The continuation must assert `full_20x3_coverage` before
  freezing the tables.

### ACCEPTED

- B-1, B-3, B-4, B-5 closed; D1 (in substance), D3, D4, D5, D6 closed;
  R-1, R-4, R-6, R-9, R-10 closed.
- Containment intact; no guard loosened; the only new capability is filesystem
  stat metadata, which fails closed on `OSError` and is bounded in iterations.
- The `_DEAD_END_EXCLUSIVE` treatment does **not** contradict the recorded
  refusal of O-3: no published constant moves, `DESIGN_END` is untouched,
  `_DEAD_END_EXCLUSIVE == FORWARD_FLOOR`, and the committed proof still holds.
- The five deliberately redundant guard pairs — verified equivalent by probe,
  not accepted on argument.

## 9. What could not be verified

1. Whether real OANDA BA candles in this archive violate `ask_* ≥ bid_*`, and
   at what rate. Real-data reads are forbidden. **Resolved in direction, not in
   magnitude**, by the committed in-repo precedent cited in BL-4.
2. Whether a real US-session p95 spread on a wide cross exceeds the 100-pip
   ceiling (BL-5). Recorded as an explicit constraint on the continuation, not
   assumed away.
3. The fix note's "44 mutations, 38 caught" figure — not reproducible as
   stated; an independent 84-mutation battery gives 76 caught with three
   survivors outside its stated redundancy set.
4. That the committed `artifacts/m15_gate3a/*.json` match their separately
   approved content — only that they are unmodified by this diff and
   scrub-clean.
5. Behaviour of `_names_protected` against real UNC shares and elevated
   symlinks; only extended-length aliases, junctions, 8.3 names and the
   absent-tree case were reachable synthetically.

## 10. Non-authorisation

This document authorises nothing. It does not accept the source audit, does not
adopt a dataset or forward epoch, does not permit any real data read or
derivation, and does not start the gate-3a continuation. No real data was read,
no M15 data derived, no checksum or spread computed, no validation or holdout
evaluated, no model trained, no prediction generated, nothing executed. No
source or test file was modified by this audit. `artifacts/m15_gate3a/`,
`artifacts/ml_step4/**` and the stage24/stage25 trees are unchanged.

Per policy §12 the auditing AI may not give the final ruling — acceptance or
rejection is a human + ChatGPT decision. See §0 for the independence
limitation that qualifies this record.

## 11. Recommendation for the next gate

1. **One targeted-fix Work PR** (policy §14 — code, tests, docs, internal audit
   and CI in a single PR) closing **BL-1…BL-5** and **RF-1…RF-7**, each with a
   failing-before / passing-after test. Minimum new coverage: a `Sequence`
   whose `__len__` and iteration disagree; non-distinct inventory records; a
   `tzinfo` whose `utcoffset()` returns `None` at all five sites; `\\?\unc\`
   casing; an ancestor depth beyond the walk limit; the crossed-quote policy
   whichever way it is decided; a JPY pip-unit cost table and a zero-spread
   table; the `SESSIONS_UTC` value pin; an **ungated stdlib** `datetime`
   subclass carrying `.nanosecond`, so B-1 keeps its proof without pandas;
   buckets fed out of order; a close-above-high row; and a fullwidth status
   form.
2. **One independent re-check** of that fix, performed in a **genuinely
   separate session** — and, given §0, ideally also a fresh-session re-check of
   *this* record.
3. Only if that re-check accepts may a **separately authorised gate-3a
   continuation** read or derive design-span data. It must additionally assert
   `n_pairs` against the roster (NB-1) and `full_20x3_coverage` before freezing
   the cost tables (NB-10).

Forward-epoch adoption remains
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`.
`PRODUCTION_READINESS_NOT_CLAIMED` and `NO_EXECUTION_PERFORMED` remain in force.
