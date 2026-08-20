# Fourth independent source-audit re-check — M15 gate-3a machinery at `0e3b001`

- **Document class:** doc-only **Gate-decision** record (policy §14.2 — it
  formally judges a research state). Executes nothing; authorises nothing;
  changes no source, test or frozen contract.
- **Target:** `scripts/m15_gate3a/**` and `tests/m15_gate3a/**` at master
  `0e3b001` — the head produced by PR #446, whose parent `adcfd52` is PR #445
  (the fourth targeted-fix Work PR). Master CI green on both.
- **Risk tier:** **Amber** (policy §2–§3 — it judges a protected-path research
  contract). **Not self-mergeable.** Merging requires human + ChatGPT approval.
- **Verdict:**
  **`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`**

## Statuses

- Required: `M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`
- Carried: `M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN`
  · `M15_GATE3A_CONTRACT_AND_PROOF_DESIGN_DECISION_RULED`
  · `M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`
  · `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`
  · `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_ACCEPTABLE_FOR_GATE3A_DATASET_EPOCH_ADOPTION`
- Open pre-continuation item: **`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`**
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Gate-3a continuation: **NOT authorised.** No calendar artifact approved,
  generated or authored. No real data read; nothing derived, trained, validated
  or executed.

**Forbidden-label note.** This document asserts none of `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `READY_FOR_LIVE`, `M15_AUTHORISED`,
`H1_AUTHORISED`, `H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`,
`BYTE_ADMISSIBLE`, `MEETS`, `ROBUST`, `DEPLOYABLE`. Where such tokens appear
below they are **probe payloads quoted as evidence of a containment failure** —
a prohibition context under playbook §10, never a claim.

---

## 1. Executive verdict

The audit **BLOCKS**. **Ten blockers (FB-1…FB-10) and twenty-one required fixes
(FR-1…FR-21)** are recorded against master `0e3b001`.

This is not a repudiation of PR #445. That change closed a great deal, and §7
records the properties that re-derive **correct** under adversarial probing —
most of them properties that failed in an earlier round. The B-2 declaration-only
masquerade, the B-3 check-then-reparse, the B-4 crossed-quote re-disposition and
both B-7 coverage holes are genuinely dead, verified by re-running the original
exploits rather than by reading the fix note. Twenty-eight of the twenty-nine
required fixes are closed. The arithmetic, timestamp, aggregation, coverage and
epoch layers are, on plain values, sound.

What blocks is one recurring shape, and two new ones:

> **The package hardened each object family at the sites the previous audit
> named, and left the rest of the same family open — including in code the same
> PR wrote.**

`str`, `int`, `float`, `datetime`, `Path` and `Sequence` are pinned in dozens of
places, and seven specific sites are not, so the D-4 raw-source refusal, the D-11
promotion prohibition, W3 consumer freshness, verifier independence, the
forbidden-status predicate, the coverage epoch bind and the PAIRS_20 universe
check are each answerable by the caller's own object (**FB-5**). Frozen
dataclasses refuse `replace`, `copy`, `deepcopy` and `pickle` — and there is **no
`__init_subclass__` anywhere in the package**, so an ordinary subclass with a
no-op `__post_init__` mints any token-bearing record for free (**FB-1**). Every
module snapshots caller containers before reading them twice — except
`artifacts.write_metadata_artifact`, the one component that writes to disk
(**FB-2**).

Four blockers need **no hostile object at all**:

- a complete price dataset, and a strategy-metrics payload, both write clean by
  ordinary re-typing and re-spelling (**FB-3**);
- a protected root spelled with a trailing dot is allowed, and the *creating*
  write lands inside the real tree — `models/` is gitignored, so it is absent in
  every fresh clone (**FB-4**);
- `dataclasses.asdict` leaks the identity map that W3's whole enforcement rests
  on gating (**FB-6**);
- the confusable fold covers two scripts, and **every one of the 21 forbidden
  labels is defeated by a single codepoint from a third** (**FB-7**).

Two blockers are about what the suite does not hold: reader-freedom — the single
most load-bearing containment property of this package — is pinned by no test at
all (**FB-8**), and a clause of the contract marked "non-negotiable" was
re-interpreted by the Work PR and the re-interpretation pinned in a test
(**FB-9**).

And one is worse than the family it belongs to: `WarmupPolicy.validate()`
**swallows** the numeric authority's refusal under a `# pragma: no cover` that is
wrong, so the T-1 burn-in — the leakage boundary itself — reports valid while
being eligible from bar index 1 instead of 24 (**FB-10**).

Every blocker below was reproduced by the lead itself, from its own probe, before
being recorded, and each is stated with its precondition — "plain JSON" or
"requires an in-process hostile object". The two are not equally serious and
conflating them would misinform the decision-makers.

**The observation that matters most for process.** The suite is green — 1100
passed, 1 skipped — at every one of these defects, for the fifth round running.
Most of what is recorded here is an **absent** guard rather than a broken one,
and no mutation study can find an absent guard. A mutation score is evidence
about the guards that exist; it is not evidence of conformance.

---

## 2. Independence, and the limits of it

**Top-level independence holds.** This session did not implement PR #440, #442,
#445 or #446, and carries none of those sessions' conversation context, internal
reasoning or exploration history. It began from a cleared context with the
repository as its only starting point.

Two limitations are disclosed rather than claimed away:

1. The session's persistent memory index contains one-line summaries of earlier
   rounds. Those were treated exactly as the fix note was — as **unverified
   historical claims** — and no finding here rests on one. Every disposition in
   §8 and §9 was formed from an executed probe against current source *before*
   the implementer's own disposition was read.
2. The same model product performed earlier rounds. Policy §12 makes independence
   a property of the **session**, not the model, and requires the auditing
   session to re-read the source instead of trusting the implementer's
   conclusions. That is what was done.

**Method.** Ten specialised roles were run, none given another's conclusions and
none told what the others were examining: contract/specification/data-boundary ·
adversarial/bypass · tests/mutation · byte-integrity/proof-design ·
filesystem/containment · artifacts/status/scrubber · coverage/calendar-interface ·
time/epoch/pair/pip/cost/aggregation · B-1…B-7 / RF-1…RF-29 disposition ·
dependency-import-graph and test-safety boundary. Two were briefed adversarially:
one to argue the implementation is wrong, one to hunt the bypasses the tests do
not see.

The lead did not count votes. Every decisive claim was **re-executed by the lead
in its own sandbox**; claims that did not reproduce, or that rested on a
misreading of the contract, were rejected or downgraded — §13 records four.

**Verification boundary.** All execution ran against a clean `git archive` extract
of `0e3b001` in a scratch directory containing **no `.env`, no credentials and no
real research data**. The repository working tree was never modified; every
mutation was applied to a private copy and reverted, with `__pycache__` purged
between mutants. PR #446's test-safety default was used as the boundary that makes
this safe, and was verified sufficient for that purpose — with two residual routes
recorded in §12.

**Forbidden operations.** No real data read · no `.env` read · no DB connection or
write · no raw-source hashing · no real M15 derivation · no validation, holdout,
training, inference or execution · no broker, paper or live activity · no external
storage · no credential use · no calendar artifact generated and no market hours
invented · no D-5.8 threshold decided · `uv.lock` untouched · no source, test or
frozen-contract file changed · no gate-3a continuation · no PR merged.

**One deviation, disclosed.** While establishing §12's socket finding, the
dependency/test-safety role executed one DNS lookup of `example.com` and one
6-byte UDP datagram to `192.0.2.1` (TEST-NET-1, non-routable). That exceeded the
brief's no-network constraint. No credential, repository content or research data
was transmitted, and no further network probe was made. It is recorded here rather
than omitted, and the finding it supports (FR-15) is graded on the source, not on
that probe.

---

## 3. Scope, derived from current source

`scripts/m15_gate3a/**` is 15 modules / 7,266 lines at this head;
`tests/m15_gate3a/**` is 20 files / 11,192 lines and 1,101 collected tests. Three
modules are new since the last audit (`proof.py` 1,786 lines, `coverage.py` 709,
`calendar_authority.py` 460) and `artifacts.py` was substantially rewritten
(1,261 lines). The audit weighted the new and rewritten code most heavily, on the
ground that it has been exercised by exactly one round of review.

Authority read directly at this head: `CLAUDE.md`;
`docs/governance/autonomous_development_policy.md`;
`docs/governance/m15_audit_playbook.md`;
`docs/design/m15_contract_design_gate_decision.md` (the RULED contract, and the
normative authority for §10); `docs/design/m15_third_independent_source_audit_recheck.md`
(the historical B/RF definitions); all eight `artifacts/m15_gate3a/*.json`; and
`docs/design/m15_targeted_fix_b1_b7_rf1_rf29_note.md`, read **last**, as an
implementer's record whose every "Fixed" / "Closed" / "Conformant" claim started
at unverified.

---

## 4. Blockers

### FB-1 — subclassing defeats every construction token; a forged calendar reaches a satisfied coverage conjunction through public API alone

`coverage.py:125-224, 243-287` · `calendar_authority.py:114-202` · `proof.py:777-832`

The construction-token pattern is the sole mechanism preventing a hand-built
calendar or coverage record from satisfying the CV limb. It is spent in
`__post_init__` — an ordinary overridable method — and **there is no
`__init_subclass__` anywhere in `scripts/m15_gate3a/**`** (zero occurrences,
verified). Every consumer gates on `isinstance`, which a subclass satisfies.

Lead reproduction. No underscore-prefixed name is touched, `validate_calendar` is
never called, and no approval marker is ever presented:

```python
class ForgedCalendar(ValidatedCalendar):
    def __post_init__(self): pass
    def expected_slots(self, pair): return ONE
class ForgedMeasurement(PairSlotMeasurement):
    def __post_init__(self): pass
```
```
type(result): CoverageResult | genuine CoverageResult: True
calendar_digest: NO_CALENDAR_EVER_EXISTED | epoch: NO_EPOCH_WAS_EVER_APPROVED | pairs: 20
validate_calendar was NEVER called; no approval marker presented.
```

The returned `CoverageResult` is **genuine** — minted by `assert_full_coverage`
itself, bearing a real token — so every downstream "re-check rather than trust the
type" passes, and `proof._limb_cv` accepts it. The same route constructs the proof
records:

```
ProofResult          subclass with no-op __post_init__ -> CONSTRUCTED (token never spent)
MeasurementRecord    subclass with no-op __post_init__ -> CONSTRUCTED (token never spent)
ConsumptionApproval  subclass with no-op __post_init__ -> CONSTRUCTED (token never spent)
```

`authority="THE OBSERVED DATA ITSELF"` and `content_digest="NO_CALENDAR_EVER_EXISTED"`
are the exact fabricated values `calendar_authority.py:119-122` and
`coverage.py:131-135` name as the attack the token closed.

**Contract:** D-6.1/D-6.2 (§9.1–9.2 — an unapproved, ambiguous or
observation-derived calendar fails closed); D-5 (§8 — the conjunction is over
*measured* pairs); §13's acceptance bar ("no newly-introduced survivor").
**It also falsifies a stated guarantee in the source:** `coverage.py:154` —
"`dataclasses.replace` and subclassing were already refused". `replace`, `copy`,
`deepcopy` and `pickle` genuinely are refused; subclassing never was.

**Precondition:** in-process caller. **Why it is a blocker regardless:** this is
the fourth iteration of one family — hand-build → `replace` → `copy`/`pickle` →
subclass — and it is the only thing standing between a caller and a coverage
conjunction no calendar authorised. No mutation probe can find it, because there
is no guard to mutate.

### FB-2 — the writer validates one read of the payload and publishes a different one

`artifacts.py:1243-1244`

```python
validate_metadata_artifact(payload, artifact=text)   # reads the payload
serialised = evidence.serialise(payload)             # reads it again -> these bytes are written
```

`scan_gate3a` already calls `evidence.serialise(payload)` internally (RF-11); the
writer discards that result and re-derives the bytes from the caller's object.
Nothing snapshots the payload. Lead reproduction with a `dict` subclass returning a
clean face for the validating reads and the real payload on the fifth:

```
WROTE: scrub_report.json | reads: 5
{
  "artifact": "scrub_report",
  "gate": "3a",
  "net_pnl": 91234.5,
  "result": "PRODUCTION_READY",
  "sharpe_ratio": 2.31
}
```

**Contract:** B-3's own principle (the certified value must be the published
value) at the one component that writes to disk; playbook §9 and §10; §12.19;
and the module's own docstring, which says the payload "is validated against the
schema its filename declares".

**Precondition:** an in-process hostile `dict` subclass, not plain JSON — but this
*is* the package's declared threat model. `_pin`, `_snapshot_row`,
`no_overlap._materialise`, `coverage._materialise_bars` and
`calendar_authority._slots_from_mapping` all snapshot caller containers precisely
for this reason. `artifacts.py` is the one module that does not, and it is the one
that writes. **Fix shape:** serialise once, scan the parsed snapshot, write those
bytes.

### FB-3 — forbidden content reaches disk by ordinary re-typing and re-spelling, with plain JSON

`artifacts.py:990-995` and `:1084-1087` (string leaves) · `:319`, `:355`
(`_FORBIDDEN_KEY_TOKENS`, `_key_tokens`) · `:396` (per-numeric-key bound)

B-1 closed re-*keying*. Three adjacent encodings were not closed, and each ends
with `write_metadata_artifact` writing the file.

**(a) Re-typing.** A `str` leaf costs one leaf, zero numeric budget, and is only
claim- and timestamp-scanned; the docstring's "budgets a re-encoding cannot
evade" does not hold, because a serialised payload is one leaf. 2,000 full bid/ask
OHLC rows `json.dumps`'d into one string under a declared key:

```
declared-key JSON-string dataset: 349957 chars -> CLEAN
undeclared backstop {"note": blob}             -> CLEAN
WROTE dataset artifact: 328096 bytes -> design_m15_inventory.json
```

Base64 and data-in-keys reach the same result.

**(b) Re-spelling.** `_key_tokens` splits on snake/kebab/camel/space boundaries,
so a run-together metric name produces no token to match — and the camel rule
also breaks the standard finance spelling `PnL` into `('pn','l')`:

```
{"sharperatio":1.93,"netpnl":128345.6,"maxdrawdown":3.21,
 "informationratio":1.2,"alpha":0.07,"winrate":0.61}   -> CLEAN
WROTE: metrics.json | {"alpha":0.07,"informationratio":1.2,"maxdrawdown":3.21,
                       "netpnl":128345.6,"sharperatio":1.93, ...}
key PnL     tokens=('pn','l')      -> CLEAN     |  key pnl -> gate3a_forbidden_key:pnl
key netPnL  tokens=('net','pn','l')-> CLEAN     |  key MaxDD, ROI -> CLEAN
control snake_case -> ['gate3a_forbidden_key:net_pnl','gate3a_forbidden_key:sharpe_ratio']
```

**(c) Declared numeric keys.** The per-key bound is 21 values and
`design_m15_inventory` declares 16 numeric keys, so 336 numeric values are
licensed. Eight price columns re-keyed onto eight declared numeric names give 160:

```
20 pairs x 8 float price columns under DECLARED numeric keys -> CLEAN
WROTE: 8782 bytes | first record: {'absent_source_minute_count': 1.10001,
  'complete_bucket_count': 1.10011, 'cost_hurdle_eligible_bar_count': 1.10021, ...}
```

This falsifies the intent stated at `:396-401` — "A declared key is a licence to
hold *a* number, not a series": the F2-2 fix bounds one key, not the schema's
sixteen together.

(a) and (b) are additionally reachable because an unrecognised `*.json` stem
resolves to **no schema** and falls to the shape-agnostic backstop.

**Contract:** `artifacts.py`'s own opening line — gate-3a artifacts "carry NO
strategy metrics, predictions, model outputs, trade-level rows"; playbook §4
("raw rows, candles … all rejected") and §9. This is B-1's headline evidence — "a
complete price dataset … accepted with `findings: []` and **written to disk** by
`write_metadata_artifact`" — reproducing today through three different encodings.
**No hostile object; plain JSON.** A cheap partial measure would be to refuse an
artifact name that resolves to no schema; the durable one is to bound content by
what a schema *requires*, not only by what it permits.

### FB-4 — containment fails open on an absent protected root, and the *creating* write lands inside it

`path_authority.py:160-174` (`is_within`), `:216-264` (`resolve_candidate`) ·
`guards.py:160-181` · `artifacts.py:1239-1253`

Win32 strips a trailing dot when it opens a path. `Path.resolve(strict=False)` can
only canonicalise a component that **exists**; for an absent one it returns the
spelling verbatim. So `<root>/models.` survives resolution as `models.`, the name
test compares unequal to `models`, `_protected_stat` returns `None` (nothing to be
identical *to*), `is_within` returns `False` — and `mkdir`/`write_text` then go to
the real `models`. Lead reproduction in a clean HEAD extract:

```
'models'             -> REFUSE (refused real/protected path: models)
'models.'            -> ALLOW
'models '            -> ALLOW
'models.\weights'    -> ALLOW
'MODELS.'            -> ALLOW

executed write through the real writer, out_dir = models.
  WROTE -> ...\models.\scrub_report.json
  does the REAL protected models/ now exist?  True
  contents of models/ : ['scrub_report.json']
  direct refusal of the same real dir: REFUSE
```

**Live exposure.** `.gitignore:9` is `models/`, so `models/` is **absent in every
fresh clone and on CI** — it is exactly the model-binary tree playbook §4's "Model
binary routes — none" covers. The containment role reproduced the same result for
`data/`, `docs/` and both PR-B.1 trees by renaming each root away to simulate a
checkout in which it is absent; the `models/` case needs no simulation.

**Contract:** §12.18; playbook §4. It falsifies three stated guarantees in current
source: `artifacts.py:48-50` ("a path naming or sitting under a tree in that
module's protected set is refused"), `path_authority.py:21-22` ("every failure
mode refuses"), and `resolve_candidate:236` ("the verdict for every accepted input
is now a function of the input alone") — the verdict here is a function of
*filesystem state*. It is the same fail-open-on-the-creating-write shape that
`_reject_stream_suffix`'s own docstring declares unacceptable and closed for NTFS
streams; the sweep was not extended to Win32 name normalisation.

**Precondition:** none beyond the spelling. The *mechanism* is Windows-specific;
the invariant break is portable. **No test in `tests/m15_gate3a/**` exercises a
trailing dot or space in a path.** Note that junction aliases to an absent root
*are* refused (`resolve()` expands reparse points) — the two alias classes behave
differently, and §13 records that as a resolved disagreement.

### FB-5 — seven unpinned comparisons make the D-4, D-11, W3, verifier-independence, forbidden-status, epoch-bind and pair-universe guards answerable by the caller's own object

The package pins character data through `_pin` / `str.__str__` / `pin_int` /
`pin_float` / `Path.__str__` in dozens of places. These seven sites do not, and
each decides a contract rule. Every one has a **plain-value control that is
refused**.

| Site | Guard it decides | Lead-observed |
| --- | --- | --- |
| `proof.py:466-468` `Provenance.stream_id` — the one field of three not pinned | co-measurement roster de-dup `:1262`; verifier independence `:1332`; W3 consumer freshness `:1702` | two `Provenance` over one real pass (`THE-ONE-AND-ONLY-READ`) compare unequal and hash distinctly |
| `proof.py:552-558` `MeasurementRecord.subject` | **D-4** — the proof subject is the derived artifact | record accepted whose subject character data is `RAW_M1_SOURCE_BYTES` |
| `proof.py:1143-1149` `refuse_raw_source_rehash` | **D-4.1/4.7** — hashing is a byte read | **ALLOWED** for character data `RAW_M1_SOURCE_BYTES` |
| `proof.py:1119-1128` `assert_byte_level_claim` | **D-11 — promotion forbidden** | returned the declaration-only token as an accepted byte-level claim |
| `proof.py:546` `MeasurementRecord.role` | producer/verifier separation | one record accepted into **both** rosters |
| `guards.py:227` `normalise_status` | the forbidden-status predicate | `is_forbidden_status(S("PASS")) == False`; `assert_status_allowed(S("PASS"))` **ALLOWED** |
| `coverage.py:580` epoch match · `pair_authority.py:56-66` `_normalise_key` | the calendar/coverage epoch bind; the PAIRS_20 universe | a two-faced epoch string is accepted where the plain one raises; a `str` subclass whose char data is `XXX_YYY` is certified as `GBP_CHF`, with `pip_size 0.0001` and a `no_overlap` span reading `pair: GBP_CHF, filename: XXX_YYY.parquet` |

```
refuse_raw_source_rehash(RAW_M1_SOURCE_BYTES) -> ALLOWED   real char data: RAW_M1_SOURCE_BYTES
assert_byte_level_claim -> PROMOTED            returned: DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL
control plain RAW_M1_SOURCE_BYTES -> REFUSED ; control plain declaration token -> REFUSED
normalise_status(S('PASS')) = TOTALLY_CLEAN ; assert_status_allowed(S('PASS')) -> ALLOWED
canonical_pair(Impostor char-data 'XXX_YYY') -> 'GBP_CHF'
```

`unicodedata.normalize("NFKC", s)` **returns the same object** when the input is
already NFKC-normal, which is why `normalise_status` never sees plain character
data. `validate_calendar` pins the identical epoch comparison correctly
(`calendar_authority.py:406`), so the two sides of one contract disagree; and
`no_overlap._roster_report` pins `filename` and `sha256` of the *same record*
whose `pair` is left unpinned.

**Contract:** §12.11 / D-4; §12.13 / D-11 ("**Promotion … is forbidden. No code
path may derive one from the other**"); §12.12 / W3; §12.20 / R-2; playbook §10.
**Precondition:** in-process `str` subclass. **Blast radius, honestly:** the
scrubber refuses the claim *spelling* at the write boundary, and none of these
guards has a non-test caller today, so no artifact can carry a promoted token now.
What is false is the guarantee, at the guards named for it.

### FB-6 — W3 is not a precondition of use: the gated identity map is public API

`proof.py:766-768`, `:1611-1613`

Both docstrings state that the per-artifact identity is "reachable only through"
`open_for_consumption`, and gating `_identity` is this layer's **entire** W3
enforcement. `dataclasses.asdict` and `astuple` recurse over dataclass fields
themselves and never invoke `__copy__`/`__deepcopy__`/`__reduce__`, all three of
which are correctly refused (N-5). Lead reproduction:

```
open_for_consumption was NEVER called.
identity map leaked: dict | pairs: 20
EUR_USD -> {'artifact_id': 'a-EUR_USD', 'sha256': '0000…0000', 'size_bytes': 4096,
            'measured_stream_ids': frozenset({'prod-EUR_USD','ver-EUR_USD'})}
astuple also works: True
```

**Contract:** §11 W3 ("a consumer re-verifies identity and digest immediately
before use … a precondition of use, not a one-time proof"), §12.12.
**Precondition:** none — a stdlib call, no private name, no hostile object. This
is N-5's own lesson ("`deepcopy` **is** public API") one function further out.
`grep asdict|astuple tests/m15_gate3a/` returns no hits.

### FB-7 — the confusable fold is a two-script denylist; every forbidden label is defeated by one codepoint, and two table entries fold to the wrong letter

`artifacts.py:105-182` (`_CONFUSABLES`)

**(a) Coverage.** The table folds Cyrillic and Greek (plus nine assorted
lookalikes). A systematic single-codepoint sweep over the Cherokee syllabary,
lead-run:

```
forbidden labels with a single Cherokee substitution that scans CLEAN: 21/21
   BYTE_ADMISSIBLE      U+13A1  -> dense BYTADMISSIBLE
   CLEARED_FOR_LIVE     U+13A1  -> dense CLAREDFORLIVE
   DEPLOYABLE           U+13A1  -> dense DPLOYABLE
   FORMALLY_VERIFIED    U+13A3  -> dense FRMALLYVERIFIED
   ...
```

The disposition role wrote `{"result": "PᎪSS"}` (U+13AA) to disk through the real
writer as a legitimate `scrub_report.json`.

**(b) Two entries are actively wrong.** `:174` `"Ꭰ": "A"` (U+13A0 CHEROKEE LETTER
A — the glyph is a **D**) and `:176` `"ᑭ": "C"` (U+146D — the glyph is a **P**).
The comment above the table states the rule the table breaks: "Only visually
identical pairs are listed."

```
Cherokee A (U+13A0) in PRODUCTION_READY    dense=PROAUCTIONREADY  -> CLEAN
Canadian PA (U+146D) as P in PASS          dense=CASS             -> CLEAN
control PRODUCTION_READY / PASS            -> both REFUSED
```

A mis-map is worse than an omission: it rewrites the character into a
non-matching letter, so the fold *guarantees* the miss.

**Contract:** playbook §10. **Precondition:** none; plain JSON. This is B-1(c) —
"NFKC folds fullwidth forms but not homoglyphs" — reproducing across a script the
table does not cover. The source docstring honestly scopes itself to
"(Cyrillic/Greek) homoglyphs", so the *guarantee* is not false; the **prohibition**
is. A hand-maintained fold table cannot be completed by enumeration; the durable
fix is a scripted derivation from Unicode's confusables data, or a per-field
allowlist of permitted scripts.

### FB-8 — §12.14's mandated pins do not exist: reader-freedom and the reverse-caller set are held by no test

`tests/m15_gate3a/**` (absent tests) · contract §12.14

§12.14 requires: *"Keep `scripts/m15_gate3a/**` reader-free; P and V live outside
it; **pin the import direction and the reverse-caller set with tests**."* The
source is **correct today** — the lead's own AST sweep and a role's runtime
`sys.addaudithook` trace both find zero read primitives — and exactly one pin
exists (an intra-package direction test, whose mutation is killed). Reader-freedom
itself is pinned by nothing. Lead-run mutations, each against the full scoped
suite:

```
add a byte reader + socket import to proof.py        -> SURVIVED  1100 passed, 1 skipped
  (import-time Path(__file__).read_bytes(), a public leak_read_any(path), import socket)
import Real365dBaProvider into effective_n.py        -> SURVIVED  1100 passed, 1 skipped
```

So component C can acquire an import-time byte read, a public byte reader, a
socket import, and a binding to the repository's real-data reader, with the suite
unchanged. There is no outbound-import allowlist for `scripts/m15_gate3a/*.py`,
and a non-test reverse caller placed anywhere outside `scripts/ml_step4/` is
equally unpinned.

**Why this is a blocker and not a required fix.** Reader-freedom is the property
on which every "this package cannot touch real data" statement in the last four
audit records rests, and §15.4 places the byte-reading producer/verifier at the
*next* gate — the moment when this pin most needs to already exist. A property
that is true only by inspection, in a package that is about to grow a reader, is
not a property the gate can rely on.

### FB-9 — a Work PR re-interpreted a contract clause marked non-negotiable, and pinned the re-interpretation in a test

`artifacts.py:914-1008` (`_scan_declared` contains no shape heuristic) vs
`:1023-1032` (`_row_like_count`, `_is_numeric_series`, called only from
`_scan_undeclared`) · `tests/m15_gate3a/test_wp_artifacts_allowlist.py:54-58`

§12.25 reads: *"**Schema shape constraint (lead-verified, non-negotiable).** The
continuation's inventory is writable only if per-file records stay **nested** with
**≤5 immediate numeric fields**; six refuses, and flattening `gap_report`
refuses."* At HEAD, for any payload that resolves to a schema, none of it holds:

```
nested, 5 immediate numeric fields              -> findings: []
nested, 6 immediate numeric fields              -> findings: []
FLATTENED gap_report (6 immediate numeric)      -> findings: []
sweep N = 3…16 immediate numeric fields/record  -> findings: 0 at every N
UNDECLARED backstop, same bytes, 6 numeric/rec  -> ['gate3a_numeric_cardinality_exceeded',
                                                    'gate3a_row_like_numeric_records']
```

**Declaring a schema therefore buys strictly less shape scrutiny than declaring
none** — and the suite now pins that inversion, stating in its own docstring that
"the previous shape denylist refused this at six immediate numerics and refused it
again when the block was flattened (§12.25)".

**The reading, stated fairly.** §12.25's first sentence is grammatically
present-indicative and its last sentence points at B-1's allowlist redesign "not a
threshold to raise", so a permissive reading — the ≤5 clause described the defect
rather than the requirement — is available, and the implementer took it. Three
things weigh against accepting that as an implementing session's call: the clause
is headed **non-negotiable**; §12's preamble states an implementing session "may
not re-interpret a contract"; and `CLAUDE.md` makes the stricter reading of a
research restriction win. Policy §14.2 reserves formally changing or judging a
contract to a **Gate-decision PR** — which is precisely the governance class of
the merged B-4 finding.

**What is *not* wrong.** §12.25's operative last clause **is** satisfied: the lead
built a populated 20-record `design_m15_inventory` instance in the committed schema
shape and it scans clean in all three variants tested (committed two-key
`gap_report`; the D-3 six fields; both together). The residual leakage is bounded —
undeclared keys are refused and a declared numeric key is capped at 21 values.
**The blocker is the re-interpretation and its pinning, not a demonstrated leak,
and the remedy is a ruling rather than a further implementation choice.**

*(Recorded with it: §12.25's own diagnostic is still not discharged. The committed
M1 predecessor inventory `artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json`
carries 7 immediate numeric fields per record and is **still refused** —
`['gate3a_leaf_cardinality_exceeded','gate3a_numeric_cardinality_exceeded','gate3a_row_like_numeric_records']`.
Neither reading of §12.25 is currently fully discharged.)*

### FB-10 — `WarmupPolicy.validate()` swallows the numeric authority's refusal, and the T-1 burn-in is disarmed while reporting itself valid

`warmup.py:59-68`

The loop pins `w_bars` and `longest_feature_lookback_bars` through the single
numeric authority — and on refusal does `continue`, under a
`# pragma: no cover - guarded above`:

```python
except NumericAuthorityError:  # pragma: no cover - guarded above
    continue
```

The `isinstance`-based checks below cannot recover, because `isinstance` consults
the object's `__class__` and `<=` is answered by the object. Lead reproduction:

```
validate() -> PASSED, no refusal        <<< the policy reports itself valid
spoofed eligibility: {0: False, 1: True, 2: True, 23: True}
honest  eligibility: {0: False, 1: False, 2: False, 23: False}   (w_bars=24)
as_metadata w_bars: SPOOF | first_eligible_bar_index: SPOOF
control pin_int(SpoofInt()) -> NumericAuthorityError
```

The burn-in becomes eligible from bar index 1 instead of 24, and the published
metadata carries the spoof. **This is the T-1 leakage boundary itself** — the
mechanism that stops feature lookback reaching pre-forward data — not a claim
guard, which is why it is separated from FB-5.

**Contract:** T-1 (playbook §4, "warm-up W ≥ longest lookback; pre-forward loads
fail closed"); and two stated guarantees are false — `numeric_authority.py`'s
docstring ("the slot calls are guarded so that spoofing lands on
`NumericAuthorityError` … each caller wraps it in its own error class") and
`warmup.py:91-93` ("N-1: pinned before the bound test and before the eligibility
decision, so an `int` subclass cannot answer … 'past the burn-in'") — the *index*
is pinned, `self.w_bars` is not. Every other module in the package refuses the
identical object.

**Precondition:** a hostile Python object with a spoofed `__class__`; not
reachable from JSON. That object is nonetheless squarely inside the threat model
the N-1 / P-1…P-7 remediation established, and the same swallow-and-continue
pattern appears at six further sites (**FR-20**).

---

## 5. Required fixes

Real defects, each falsifying a stated guarantee or a committed contract clause;
none individually gate-stopping. They land with the blockers, in one Work PR.

| ID | Location | Defect |
| --- | --- | --- |
| FR-1 | `artifacts.py:942`, `:994` | The prohibition-list exemption is inherited by a whole **subtree** and is unbounded by shape, and the result **writes**. `{"forbidden_labels": {"result": "PASS", "content_kind": "PRODUCTION_READY"}}` → CLEAN and written to disk (a dict is not a prohibition list, yet inherits the exemption, and `_MAX_PROHIBITION_ITEMS` never applies to it); `{"forbidden_labels": ["GATE 3A RESULT IS PASS"]}` (22 chars) → CLEAN; `["READY_FOR_LIVE=TRUE"]` → CLEAN. At 23 characters it is caught. Playbook §10 permits a prohibition *list*, not an exempt subtree. |
| FR-2 | `artifacts.py` scan path; `foundation_t2/constants.py` `SECRET_VALUE_PATTERNS` | A live-format API key in a **string value under a permitted key** scans clean: `{"note": "OANDA_API_KEY=1a2b…"}` and, under a declared schema, `{"rationale": "api_key=sk-live-…"}`. Detection is credential-*key-name*-based plus two value patterns (Bearer, presigned URL). Playbook §4 requires secrets rejected; B-1's own reproduction listed "a live-format API key" among the content that got through, and that limb is not closed. |
| FR-3 | `proof.py:540` | `object.__new__` bypasses `MeasurementRecord.__post_init__` entirely. Twenty forged records with `subject='RAW_M1_SOURCE_BYTES'`, `size_bytes=-1`, a reversed span and `dead_window_bars_by_bucket_start=7` were **accepted** by `_measurement_roster`. The module discloses `object.__setattr__` on a real record as out of scope; `object.__new__` on a public class is the same family and is not named. |
| FR-4 | `proof.py:1438-1485` | CV is bound to BI/TC by **cardinality only**. Lead reproduction: coverage certified for `2025-05-01` (3 slots/pair) and a byte scan measured over `2025-12-01T00:00…00:30` satisfy the four-limb conjunction together. `PairCoverage` publishes only `(pair, expected_slot_count, certified_slot_count)`, so span containment is not checkable from what `CoverageResult` exposes. The docstring claims the count binding "is what makes the four limbs one proof rather than four unrelated checks". |
| FR-5 | `cost_schema.py:312`, `:315`, `:337`; `no_overlap.py:501-521` | R-1 is applied non-uniformly. On every returning path `validate_cost_table` emits `entries_validated == 60`, `pairs_covered == sorted(PAIRS_20)` and `result == "COST_TABLE_SCHEMA_VALID"` — three one-valued fields, in the same return dict from which `full_20x3_coverage` was deleted for exactly that reason. `no_overlap`'s `files_checked` is retained on the stated ground that deleting it "would desynchronise the emitted record from the artifact vocabulary a committed schema declares" — but the allowlist is a **permission** list: a `no_overlap_proof` payload with `files_checked` omitted scans clean. It is also labelled "RETAINED BY RULING"; no committed ruling retains it, and §8 of the contract cites `files_checked=20` as the *shape of non-evidence*. |
| FR-6 | `aggregation.py:607-622` vs `artifacts.py:_SCHEMAS`; `no_overlap.py:487-521` vs the committed `no_overlap_proof` schema | Producer and writer disagree about the schema, in both directions. The `gap_report` `aggregate_m15` actually emits is unwritable into `design_m15_inventory` — six `gate3a_undeclared_key` findings, including `minute_accounting`, the entire D-3 six-field block coverage consumes. And the honest disclosure keys the fix added to `assert_per_file_bounds` (`evidence_basis`, `files_opened`, `bytes_measured`, `declared_not_measured`, `certified_spans`) are all `gate3a_undeclared_key` under the committed `no_overlap_proof` schema. Publishing either record needs a committed-schema extension nobody has specified; dropping keys to fit reverts to the pre-B-2 shape. |
| FR-7 | `calendar_authority.py:395`; `proof.py:394-413`, `:1581` | `content_digest` is shape-checked only (non-empty, whitespace-free) and never bound to the content it claims to cover. Two structurally different calendars carrying the same digest string are indistinguishable, and the unverified value is copied verbatim into `ProofResult.calendar_digest`, leaving §12.12's "consumer re-verifies before use; disagreement is fail-closed" with nothing to re-verify on the calendar limb. D-6 fixes no digest algorithm, so the source is not literally contrary to §9's bullet list; what is missing is any binding at all — and this is the control that would otherwise substitute for FB-1. |
| FR-8 | `calendar_authority.py:331-359` | The `expected_m15_slot_rule` route accepts **any callable**. A closure over the observations is deterministic and therefore accepted, producing an expected slot set derived from the data — vacuous set equality, which is the failure D-5/D-6 exist to prevent. The lazy-`Mapping` variant reaches the same result through the slots route. D-6 makes the authority a **versioned, committed artifact**; an in-memory callable is not committable, diffable or digestible. The module's own guarantee ("has no access to any observation") is narrowly true of the module and not of the composite. |
| FR-9 | `coverage.py:363-364` | The docstring claims the six D-3 quantities are checked "self-consistent"; two of the six are in no relation at all. `observed_source_minute_count=999999` beside `usable=60`, `observed=0` beside `usable=60`, and `max_unavailable_gap_minutes=999999` beside `absent=rejected=0` all validate. Under D-3's definitions `observed ≥ usable + rejected`, and `max_unavailable_gap_minutes ≤ absent + rejected`. Both relations are free of any minted number, and the producer computes both correctly — the verifier, which D-8 makes the attesting party, re-checks neither. |
| FR-10 | `no_overlap.py:492-493` | `assert_per_file_bounds` leaks `TimestampError` instead of its documented `NoOverlapError` when a declared bound carries a non-zero microsecond: the value clears `_parse` and the bound checks, then fails inside `format_utc_z` at the publication step. Fail-closed, but not with the documented exception type — the RF-29 class. |
| FR-11 | `proof.py:346-350`, `:1296` | §11 requires a disagreement to be fail-closed **and terminal**. Fail-closed holds; terminality is a docstring property of a stateless layer. After a refutation, an amended re-run returns `BYTE_LEVEL_PROOF_PENDING` with nothing recording that a refutation occurred, and `BYTE_LEVEL_PROOF_REFUTED` reaches no record. A caller that catches and retries gets a clean result with no trace. |
| FR-12 | `artifacts/m15_gate3a/design_m15_inventory.json` `required_schema_per_file.gap_report` | The committed inventory still declares the superseded two-key `gap_report` (`missing_minute_count`, `max_gap_minutes`) that D-3 replaced and the code no longer emits. §5 states the schema change "is **approved by this Gate-decision**; implementation lands in the targeted-fix Work PR" — the code half landed, the committed-schema half did not, leaving two committed authorities for one quantity, which is R-2's own failure mode. (Tension recorded, not prescribed: D-7 makes committed artifacts changeable only by human-reviewed diff.) |
| FR-13 | `no_overlap.py:38-42` vs the committed artifacts | Four of the five frozen boundary constants are not test-bound to the committed evidence. All five currently agree with `no_overlap_proof.json`, `design_m15_derivation_manifest.json` and `forward_epoch_adoption_manifest.json`, but only `design_end` is pinned by a test; `DESIGN_START`, `DEAD_START`, `DEAD_END` and `FORWARD_FLOOR` can drift from the committed artifacts without a failure. |
| FR-14 | `no_overlap.py:102-110` | The dead window's **inclusive lower boundary is unpinned**. The source is correct (`DEAD_START <= instant < _DEAD_END_EXCLUSIVE`), but mutating `<=` to `<` **survives the whole suite** (lead-run: 1100 passed, 1 skipped) — no test anywhere uses `2026-03-01T00:00:00Z`; every dead-window test uses a mid-window or post-window instant. Reachability matters: `calendar_authority._normalise_slot` has **no** design-epoch limb, so this predicate is the only thing standing between an approved calendar and an expected slot at the dead window's first bucket. §13's acceptance bar requires "both epoch-range limbs pinned in isolation". |
| FR-15 | `artifacts.py:840-856` (`_scan_key_claims` / `_scan_value_claims`) | **The mirror defect recurs in the value direction: an honest denial is refused as a claim.** `_is_denial` is consulted only for dict *keys*; a *value* gets no denial logic. `{"note": "NOT_PRODUCTION_READY"}` → `gate3a_forbidden_status_value:PRODUCTIONREADY`; so do `"NOT_VALIDATED"`, `"no PASS is claimed"` and `"this gate is not production ready"`. The three always-binding statuses survive only incidentally, because their spellings happen to break the dense substring (`PRODUCTION_READINESS_NOT_CLAIMED` → CLEAN). This is B-1's mirror defect one axis over: the machinery cannot write the denials its own governance vocabulary is made of. |
| FR-16 | `artifacts.py:794` `_MAX_PROHIBITION_ENTRY_LEN = 22`, derived from `FORBIDDEN_STATUSES` | The package **cannot list its own byte-level claim tokens in a prohibition list**: `BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN` (40 chars), `MEASURED_FROM_DERIVED_ARTIFACT_BYTES` (36) and `DERIVATION_IDENTITY_BOUND` (25) all exceed the bound → `gate3a_prohibition_entry_too_long`, and the write is refused. `guards.py:61` states these "may appear only in prohibition lists"; for these three they may appear nowhere. The bound was deliberately kept at 22 to avoid widening the unscanned window — a defensible trade that nevertheless leaves a stated permission unusable. |
| FR-17 | `scripts/foundation_t2/constants.py:151`, reached via `scan_gate3a` → `evidence.scan_payload` | The mandatory scan path is **quadratic** on a long alphanumeric run: the pattern `[a-z0-9]+\.r2\.cloudflarestorage\.com` with `IGNORECASE` backtracks catastrophically. Lead-measured: 2 000 chars → 0.024 s, 8 000 → 0.355 s, 16 000 → 1.416 s (≈4× per doubling); a 306 KB base64 value did not finish in 110 s. There is no size bound and no timeout on the gatekeeper, so a large legitimate artifact makes the scrubber the thing that never returns. Inherited from the base scrubber, but on gate-3a's critical path. |
| FR-18 | `scripts/ml_step4/evidence.py:137-165`, imported wholesale at `artifacts.py:81` | A **second writer reaches the committed gate-3a tree and overwrites it.** `evidence.write_report` applies `assert_clean` only, calls no `refuse_real_path`, and overwrites unconditionally; it is re-exported into the gate-3a namespace by the module-level import. `artifacts.py:52-54` claims the overwrite refusal "is what keeps the human-reviewed committed artifacts out of reach of a code path" — false as stated, and inconsistent with `:60` in the same file, which withdraws the claim for unrouted callers. No in-package code reaches it; the fix is to import the two functions actually used. |
| FR-19 | `tests/conftest.py:214-227`, `:245-262` | Two test-safety residuals — for a **separate** Work PR, not the gate-3a fix. (a) The `.env` guard is route-dependent: the prefilter is a case-sensitive literal `endswith(".env")` and the comparison does not strip trailing dots or spaces, so `.ENV`, `.Env`, `.env.` and `.env ` each read the file in full during a guarded session (lead-verified against a **synthetic decoy**, never the real file). The contract test is named `test_the_repository_dotenv_cannot_be_opened_by_any_route`; the guarantee as stated is false. (b) The socket guard wraps only `connect`/`connect_ex`, so UDP `sendto` and DNS resolution are unguarded, while the contract suite's section heading is "nothing leaves the loopback interface". See §12. |
| FR-20 | `proof.py:428`, `:474`; `coverage.py:397`, `:441`; `cost_schema.py:161`; `warmup.py:65`, `:96` | **`# pragma: no cover - guarded above` sits on reachable code at seven sites.** The comment asserts the preceding `isinstance` makes the `except NumericAuthorityError` unreachable; it does not, because `isinstance` consults `__class__` while `int.__index__` / `float.__float__` then refuse. Every one of the seven branches was entered by an executed probe. §13's anti-pattern list names "`# pragma: no cover` on a reachable guard" explicitly, and here the suppression sits on the exact path that carries **FB-10**. (Eleven other pragmas in the package re-derive as genuinely unreachable and are correct.) |
| FR-21 | see §14's survivor table | **Nineteen genuine mutation survivors.** The source is correct in each case; nothing pins it. The material ones: a NaN under a *declared* numeric key scans clean if one guard is removed and nothing else catches it (`evidence.scan_payload` and `serialise` both pass NaN, so the writer would emit the non-standard `NaN` literal); the `absent` limb of coverage's `unusable` check; `complete_bucket` accepting a non-bool; the whole-string forbidden-status fallback, which is the only thing catching `"P A S S"` / `"M E E T S"` / `"R O B U S T"` / `"V A L I D A T E D"`; `pin_number(v)` → `float(v)` in `cost_schema` (the exact N-1 defect that module says it closed); `Path.resolve()` in the path authority; the producer/verifier agreement loop *inside* `evaluate_four_limbs`; the consumer's artifact-identity check; the CV roster's set equality; `is_declaration_only`, which has no test at all; and `is_event_eligible`'s validation call. |

---

## 6. Non-blocking observations

- **FO-1 — §12.17's "separate output directory" is a convention, not a
  mechanism.** No such concept exists in the package; `write_metadata_artifact`
  accepts any `out_dir`. Never-overwrite is enforced and holds for all eight
  committed artifacts, but *addition* is not: the lead wrote
  `artifacts/m15_gate3a/sub/scrub_report.json`, and new files into
  `artifacts/foundation_t2` and `artifacts/oanda_archive_2026-05-31` also succeed.
  Playbook §9's "prior evidence directories untouched" is enforced against
  overwrite only. Deliberate as far as the `artifacts/m15_gate3a` prefix goes —
  D-7's trap defers adding it until the output directory is adopted — but the
  other half of §12.17 was handed to this Work PR and is not started, so the
  trap's remedy sequence has neither step complete.
- **FO-2 — D-5.8 is unenforced against a degenerate calendar.** Lead-reproduced:
  a calendar declaring one slot per pair, with one certified bar per pair and a
  self-consistent 15-minute accounting block, returns a `CoverageResult` over 20
  pairs, and the same result satisfies `_limb_cv` against `bars_scanned=1`. Only
  the *empty* slot set fails closed. The source discloses this in its own
  docstring (`coverage.py:40-53`). Classified in §11.
- **FO-3 — three of R-1's own eleven attestations survive in the committed
  artifacts**, which §10's R-1 explicitly scopes: `scrub_report.json`
  `"result": "ALL_SCRUB_CLEAN"`, `cost_table_plan_or_metadata.json`
  `"no_raw_data_read_at_gate3a": true`, and `"imputation": false` /
  `"synthetic_weekend_bars": false` / `"mid_price_construction_at_aggregation": false` /
  `"no_strategy_metrics_computed_at_gate3a": true` in the committed manifests.
  All remain in the scrubber's `allowed_keys`, so a continuation may re-emit them.
  D-7 makes those artifacts changeable only by human-reviewed diff, so this is a
  tension to rule on, not an edit to prescribe. Separately, the fix note's
  "eleven attestations deleted" enumerates a **different** eleven from R-1's.
- **FO-4 — `rejected_source_minute_count` is structurally 0 in every returned
  aggregation report.** Every contract violation raises, so
  `rejected = |observed| − |usable| = 0` always, and §13's stated observable
  outcome ("a fixture containing a calendar-absent minute and a
  contract-rejected minute reports them in different fields") is unreachable at
  the producer — it is demonstrable only one layer up, over caller-supplied
  numbers. §12.5 mandates the field and R-1 deletes one-valued fields; the
  tension is resolved in §12.5's favour and disclosed in the source, which is the
  right call. One consequence: §13's identity `rows_ingested = rows_retained +
  rejected` is now unassertable, because `rows_retained` went with the
  drop-and-count disposition. The other four §13 identities hold (verified
  parametrically over 200 randomised scenarios).
- **FO-5 — R-2's twenty terms are pinned except three, and one is conflated.**
  Unpinned: `sha256` vs lineage `file_sha256` (the latter occurs zero times in
  the package and the distinction is never stated, while the M1 predecessor
  inventory uses it); `ts` vs the source's `time` key; and "certified", used in
  two incompatible senses (`no_overlap.certified_spans` = a declaration-only
  bound check; `coverage.certified_slots` = the CV limb). Conflated:
  `coverage.py:443` and `:666` decide a *source-minute count* against
  `calendar_authority.SLOT_MINUTES` (a bucket **duration in minutes**) rather
  than `aggregation.FULL_BUCKET_SOURCE_BARS`. Numerically identical today; it is
  exactly the "source bar"/"source minute" confusion R-2 lists.
- **FO-6 — NR-F's dimensional incoherence is unchanged and faithfully
  reproduced.** `SPREAD_UNIT = "price"` with pip-unit constants `0.3`/`0.5` in
  `ALL_IN_COST_FORMULA`, and no conversion stated. All seven global strings and
  numbers match the committed `cost_table_plan_or_metadata.json` verbatim, so this
  is the committed plan's incoherence, not code-minted. The playbook's `MAY_DEFER`
  classification stands; recorded as still open.
- **FO-7 — two failure modes share one refusal message.** A non-zero
  `absent_source_minute_count` and a non-zero `rejected_source_minute_count`
  reach *different schema fields* (correct, D-3.1/3.2) but produce an identical
  message at `coverage.py:647-655`. Similarly `calendar_authority._require_text`
  reports key-absent and explicit-`None` identically. Both correctly refuse; this
  is a testability defect, not a fail-open.
- **FO-8 — four further boundaries are unpinned, source correct in each case:**
  `timeutil.py:133` `drift != 0.0` → `> 1e-6` survives (a ~1 µs component lie);
  `effective_n.py:113` `pinned < 0` → `< -1` survives (`raw_event_count == -1`
  exactly); `effective_n.py:128` `<= 1.0` → `<= 1.1` survives; `no_overlap.py:322`
  whitespace-only `filename` guard survives. `aggregation.py:363`'s
  `# pragma: no cover` guard is genuinely unreachable (15 distinct minutes bound a
  15-minute bucket), so that pragma is correct.
- **FO-9 — a hardlink to a protected *file* is allowed by `refuse_real_path`**
  (`_same_file` compares only against protected root *directories*). Not
  exploitable through the writer — `_validate_name` forces `*.json` and an
  existing target is refused as an overwrite — and creating the hardlink is
  outside the package's reach.
- **FO-10 — one test is skipped on this host** ("symlink creation not
  permitted"). Directory junctions were substituted, and all five junction routes
  refuse. The property that remains **unverified** is a *dangling* symlink, whose
  target does not exist — squarely in FB-4's class, since `resolve()` cannot
  canonicalise a nonexistent target. It should be treated as open until symlink
  creation is available on some host.
- **FO-11 — a real-`data/` reader is loaded into every gate-3a process.**
  `pair_authority.py:21` imports `scripts.ml_step4.data_adapter` at module scope
  for two float constants; that module defines `Real365dBaProvider`, whose
  `verify()` hashes and `pair_frame()` loads the committed
  `data/candles_*_M1_365d_BA.jsonl` files. No gate-3a code path calls it and no
  third-party package is loaded eagerly, so reader-freedom in the AST sense holds
  — but the component the contract designates as "the one that never reads" drags
  the repository's real-data reader into `sys.modules` on any import, and
  `pair_authority`'s own rationale value-pins `PAIRS_20` locally "so gate-3a does
  not depend on a stage script's import side effects". Avoidable (two float
  constants); recorded rather than graded, since it is a deliberate B-4
  single-authority delegation.
- **FO-12 — the B-1 mirror defect is only partly closed** (see the correction in
  §7): the prohibition list writes, but B-1's columnar-roster example does not,
  and two further mirror failures are recorded as FR-15 and FR-16. Relatedly,
  `test_b1_a_natural_columnar_roster_is_accepted_once_declared` is vacuous — its
  payload is a single scalar, not a roster.
- **FO-13 — `WarmupPolicy.validate()` mutates a frozen dataclass**, changing its
  hash (`warmup.py:59-64`, `object.__setattr__` writing the pinned ints back). A
  policy placed in a `set` or `dict` before validation becomes unfindable. The pin
  itself is correct.
- **FO-14 — `ConsumptionApproval` omits `verifier_independence_limit` and
  `calendar_digest`**, so a consumer holding only an approval sees neither. Status,
  evidence basis and the zero counts are carried, so the core disclosure survives.
- **FO-15 — the historical B-2 token still scans clean.**
  `scan_gate3a({'result': 'PROVEN_NO_DEAD_WINDOW_OVERLAP'})` → `[]`, as do
  `NO_DEAD_WINDOW_OVERLAP_PROVEN` and `BYTE_LEVEL_PROOF_PROVEN`. No code path
  emits any of them. This is round 3's "the scrubber contains nothing" observation,
  unchanged in kind.
- **FO-16 — the fix note contradicts itself on referrals.** §7 item 7 states
  "Nothing was referred as `Requires separate contract Gate-decision`"; §7e states
  D-5.8's status **is** exactly that. §7e is the accurate one. Separately, §7d
  row 1 justifies downgrading the absent-protected-root case on the ground that
  "all protected roots are **git-tracked**" — `models/` is not
  (`.gitignore:9`), which is what FB-4 turns on.
- **FO-17 — the playbook's gate table is stale.**
  `docs/governance/m15_audit_playbook.md` §1 still reads "Last reconciled against
  master at `c3a0468`", records the fourth targeted-fix Work PR as "**NOT
  started**" and the contract Gate-decision as "awaiting merge". Both are false at
  `0e3b001`. Refreshed by this PR — the only file it changes besides adding this
  record.
- **FO-18 — four containment tests never run in CI.** CI is `ubuntu-latest`; the
  extended-drive and three UNC identity-limb tests are Windows-only and are
  therefore verified only on a developer machine. The symlink identity test is
  the mirror case: it runs on CI and skips here. Neither gap is a defect, but no
  single environment exercises the whole containment surface.
- **FO-19 — `uv.lock` remains stale** (`uv lock --check --offline` → exit 1; five
  declared dependencies absent from the lock). CI uses `pip install -e ".[dev]"`,
  so nothing is broken, but no reproducibility claim may cite the lockfile. Not
  repaired; `uv sync` not run.

---

## 7. What re-derives CLEAN

Recorded because a false clean is as dangerous as a missed defect, and because
several of these failed in an earlier round and genuinely hold now. Each was
executed, not read.

**Containment and capability.** Zero read primitives in `scripts/m15_gate3a/**`
— no `open`, `read_text`, `read_bytes`, `json.load`, `pickle`, `mmap`, `glob`,
`listdir`, `walk`, `subprocess`, `socket`, `urllib`, `ctypes`, `importlib`,
`eval`/`exec`, pandas or numpy (lead AST sweep of all 15 modules). The only
filesystem calls are `stat`, `samestat`, `resolve`, `exists`, `mkdir`,
`write_text`, `unlink`, `rmdir`. Dynamically confirmed: the full proof API under
`sys.addaudithook` produced **0** `open`/`socket`/`subprocess`/`exec` events, and
the whole 1100-test suite under an open-audit plugin opened **nothing** under
`data/`, no `.env` and no socket. Zero third-party packages are imported eagerly.
No `__main__`, no CLI, no console-script entry point; `scripts/` is not packaged.
No dynamic-import route. No non-test reverse caller anywhere in the repository.
No legacy stage/compare/model path reachable in either direction from package
source. PR #445 added no dependency of any kind.

**Protected paths** (all *present* roots): `data/`, `models/`, `docs/`,
`artifacts/ml_step4/365d_ba_v1` and both PR-B.1 trees refuse for the tree, a file
inside, and an 8-deep descendant. **cwd-independence holds** — seven absolute
`.`/`..`-bearing spellings from four working directories give identical verdicts,
and all twelve relative spellings refuse from all four. **No over-broad prefix
match**: `data_extra`, `models_old`, `docs_draft`, `365d_ba_v1_copy` and
`artifacts/m15_gate3a_continuation` all correctly ALLOW, so §12.17 has a writable
target. Junctions refuse in all five configurations; 8.3 short names, UNC, `\\?\`,
`\\?\UNC\` in both casings, `\\?\Volume{GUID}`, the device namespace, NTFS
alternate data streams, embedded NUL and illegal characters all refuse. `Path`
and `str` subclasses lying via `__str__`, `__fspath__`, `parents`, `resolve` or
`is_absolute` all refuse. **Failure atomicity (RF-9)** holds at eight distinct
refusal stages — residue NONE in every case. All eight committed artifacts refuse
re-writing, bytes unchanged.

**The B-2 defect is dead.** Twenty plain ISO strings with no file access yield
`DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL`, `files_opened: 0`,
`bytes_measured: 0`, `evidence_basis: CALLER_DECLARED_METADATA_ONLY__NO_FILE_OPENED__NO_BYTE_MEASURED`
and a named `declared_not_measured` list. Import-time guards (explicit `raise`,
not `assert`) enforce the `__NOT_BYTE_LEVEL` suffix, forbid `PROVEN` in a
declaration-only token, pin the two vocabularies disjoint, and pin
`BYTE_LEVEL_CLAIM_TOKENS ⊆ guards.UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS`. The best
outcome reachable from this reader-free layer is `BYTE_LEVEL_PROOF_PENDING`, even
with all four limbs satisfied.

**The B-3 defect is dead, proved hostilely.** A `tzinfo` returning +0 for the
first parse and −23 h afterwards (control: `to_utc` first → `2026-02-28T23:00Z`,
second → `2026-03-01T22:00Z`, inside the dead window) is consumed with **exactly
two `utcoffset()` calls** — one parse — and the published span is the certified
span.

**Crossed quotes and minute accounting.** Each of the four side pairs crossed in
isolation raises its own distinctly-worded refusal — and there is **no regex
alternation anywhere in the suite** (verified: zero `match=` patterns contain
`|`). A 15-row bucket with one crossed row yields **no bar**, not an ineligible
one. `ask == bid` is accepted (`spread_close = 0.0`). Duplicate and
alias-duplicate minutes abort, and the minute is claimed **before** the quality
disposition. One row object presented 15× is refused. `spread_open` is emitted and
sign-checked. Generators and lying-`__len__` containers are refused. Zero
tolerance verified **structurally by AST sweep**: the only module-level numeric
constants in the package are `15/15/15/6/2/2/4/0.3/0.5/24/400/1000/64/64/1/6`,
there are **zero `assert` statements and zero `os.environ` reads**, and no entry
point exposes a tolerance/lenient/allow/skip/force parameter.

**Numeric pinning (N-1) genuinely holds.** A lying `float` subclass on all
fifteen rows is refused; `pin_number(LyingFloat(-5.0)) == -5.0` where
`float(...) == 0.0`; a negative median spread and `raw_event_count = -100` are
both refused.

**Coverage** is genuine set equality: missing slot, extra slot, duplicate slot and
right-count-wrong-membership all refuse with distinct messages; reversed order is
correctly accepted. Nineteen pairs, twenty-one with a repeat, an alias duplicate,
a `None` measurement and a dict-of-counts all refuse. There is no report-only
mode, no `strict=`, no tolerance parameter and no success value meaning "coverage
was short". A bucket lost to a rejected minute is never covered. The §8.10
boundary instants behave exactly as committed on both sides.

**The calendar interface** fails closed on all sixteen malformation classes
tested — absent, empty, non-mapping, each of the nine required fields
missing/`None`/blank, wrong approval string, non-string approval, wrong epoch,
prose digest, both slot sources, neither, empty slot set, a repeated slot
including a `+02:00` alias, a non-deterministic rule, a rule that raises, and a
missing pair — each with its own exception type and message. **No market hours are
invented anywhere in the package**: the only `datetime` literals are the five
frozen constants in `no_overlap.py:38-42`, and neither module constructs a
`datetime`, imports `timedelta`, or uses `range()`.

**The proof layer, on plain values.** All five arguments keyword-only with no
defaults; `None` raises naming the limb; an interior dead-window bar with clean
endpoints is refused by full scan; the two dead-window definitions diverging is a
separate terminal error; two roster entries sharing a digest, an `artifact_id` or
a staging name refuse; `row_count ≠ bars_scanned` refuses; digest and span from
different passes refuse; `staged == published` refuses; `sha256 ≠ re_read_sha256`
refuses; and §11's *more alarming* case is separately reported ("agree on the
digest but disagree on `['size_bytes']` … a derivation is wrong — terminal").
`copy`, `deepcopy`, `pickle` and `dataclasses.replace` are refused on every
token-bearing record; a hand-built or `object.__setattr__`-tampered `ProofResult`
carrying a claim token is refused at `open_for_consumption`.

**The scrubber, on the B-1 evidence set.** 300 BA rows re-keyed as a
dict-of-dicts, a prose readiness claim, `status=PRODUCTION_READY`,
`PRODUCTION_READY_CLAIMED`, `PRODUCTION_READY!`, Cyrillic `PАSS`, zero-width
`PA​SS` and fullwidth `ＰＡＳＳ` are **all refused**; camelCase and qualified metric
keys (`sharpeRatio`, `net_pnl_total`, `max_drawdown_pct`) are refused; a
non-finite **key** is refused; `{"PRODUCTION_READY": False}` and
`{"PRODUCTION_READY": "no"}` are correctly **clean** as disclaimers *in the key
position*. Both byte-level claim tokens and the
`MEASURED_FROM_DERIVED_ARTIFACT_BYTES` root are refused as values and inside
prose. A `+00:00` timestamp is flagged at the writer; the committed
nine-zero-digit `…Z` form is accepted. Unserialisable payloads (`Decimal('NaN')`,
`set`, numpy scalars, mixed-type keys) fail as scrub findings, not bare
`TypeError`. Deeply nested, self-referential and 3,000-deep payloads are reported
rather than crashing. All 23 finding tokens the module can emit are reachable.
**All eight committed artifacts scan clean**, with and without the filename hint.

**Correction to a clean the lead initially recorded.** B-1's mirror defect is
**only partly** closed, and this document's earlier draft overstated it. A
governance prohibition list of `FORBIDDEN_STATUSES` entries does write. But B-1's
*other* mirror example — the natural columnar 20-pair roster
`{"pip_size": [...]*20, "spread_floor_pips": [...]*20}` — is still refused:
undeclared it trips `gate3a_columnar_numeric_series`, and under
`design_m15_inventory` it trips `gate3a_undeclared_key:spread_floor_pips`. Only a
roster whose every column name is already in a schema's vocabulary writes
(verified: one- and two-column declared rosters are clean). Two further mirror
failures are recorded as FR-15 (a denial in a *value* is refused as a claim) and
FR-16 (the byte-level claim tokens cannot be listed in a prohibition list at all).

**Timestamps.** RF-1 is closed on all three limbs: `.0000005`, `,0000005` and a
fraction in the **offset** are each refused, and nine zero digits are accepted.
`format_utc_z` refuses a non-zero microsecond rather than truncating, and is the
only timestamp-string producer in the package.

**Pair, pip and cost.** `PAIRS_20` matches the committed roster; canonicalisation
is injective over 220 plain-string spellings with zero mis-canonicalisations; the
six JPY crosses resolve to `0.01` and the fourteen others to `0.0001`,
exhaustively verified. `max_spread_pips` is required with no default and no
numeric bound is minted anywhere. Sessions tile the UTC day exactly once, proved
by import-time re-execution of three mutated partitions. Both stress forms and the
data-source restriction are mandatory and verbatim-matched to the committed plan;
`CLAIM_SCOPE` is the committed spelling and the old code-minted variant is
refused. The 60-cell coverage **raises** and names the missing cells.
`effective_n` reproduces the approved per-pair spec on the B-3 counter-example
(`50/1 + 8000/24 = 383.33 → INSUFFICIENT_SAMPLE`), the floor is a genuine
conjunction in both roles, and §12.20's `count_quantity` gate refuses both
confusable names by name — and even a `str` **subclass** of the correct literal.

**Statuses and epoch limbs.** All three reachable epoch limbs are pinned **in
isolation** — nulling `DESIGN_END`, `DESIGN_START` and `FORWARD_FLOOR` one at a
time each fails the suite. All four package status constants are pinned. Every
refusal tested survives `python -O` and `-OO`; the whole suite passes under `-O`.

**Test hygiene.** No test asserts on source text (the RF-21 class is gone — only
`inspect.signature` introspection remains). No `pytest.raises(match=...)` uses
alternation. `guards.py`'s docstring statement about which guards have callers is
**truthful**, re-derived by grep.

---

## 8. PR #443 B-1…B-7 — independent disposition

Formed from executed probes against current source, before the implementer's
dispositions were read.

| ID | Original defect | Disposition | Basis |
| --- | --- | --- | --- |
| **B-1** | Scrubber does not contain forbidden content: (a) container shape, (b) claim phrasing, (c) character set; plus the mirror defect of refusing a legitimate prohibition list | **CLOSED_BUT_NARROW** | (a) and (b) **CLOSED** — the re-keyed dict-of-dicts and all five claim phrasings behave correctly. (c) **re-opens** across a script the fold does not cover: 21/21 forbidden labels are defeated by one Cherokee codepoint, and two table entries fold to the wrong letter (**FB-7**). The **mirror defect is only partly closed**: a prohibition list writes, but B-1's own columnar-roster example still does not (§7 correction), a denial in a value is refused as a claim (**FR-15**), and the byte-level claim tokens cannot be listed at all (**FR-16**). B-1's evidence list also included "a complete price dataset" (**FB-3**, reproduces three ways) and "a live-format API key" (**FR-2**, still clean) |
| **B-2** | The T-7 proof is a declaration check, not the byte-level proof | **CLOSED** | The exact control — 20 plain ISO strings, no file access — now yields a declaration-only token naming its own basis, with `files_opened: 0`. Promotion is structurally impossible *from this module* (no import edge to `proof`), and `evaluate_four_limbs` mints `BYTE_LEVEL_PROOF_PENDING` even when all four limbs hold. The byte-reading producer/verifier is deferred by ruling (§15.4), not by omission. (The *promotion guard itself* is separately defeated by a two-faced `str` — **FB-5** — which is a different defect from B-2) |
| **B-3** | The certified value is not the published value (`:321` vs `:328-329`) | **CLOSED** | Parse-once verified with a drifting `tzinfo`: exactly two `utcoffset()` calls, published span == certified span. The same *shape* recurs at the writer and is recorded as its own finding (**FB-2**), not as B-3 re-opened |
| **B-4** | Crossed-quote disposition re-decided against a merged audit finding | **SUPERSEDED_BY_RULING; code matches the ruled behaviour** | Hard fail-closed per D-1; drop-and-count deleted; all four counters gone; `ask == bid` explicitly not crossed; refusal survives `-O`/`-OO`; no lenient mode, flag, kwarg or env var exists. The **governance** class of B-4 — a Work PR re-disposing a contract question — recurs at §12.25 and is recorded as **FB-9** |
| **B-5** | Protected-path set omits the trees governance names; `refuse_real_path` cwd-dependent | **CLOSED_BUT_NARROW** | `data/`, `models/`, `docs/` and both PR-B.1 trees are now protected, and cwd-independence holds for every spelling tested. But protection is **absent-root-dependent** (**FB-4**), and `models/` is gitignored, so the tree B-5 named is unprotected in every fresh clone. `artifacts/m15_gate3a` remains deliberately unprotected per D-7 (FO-1) |
| **B-6** | Three contract referrals must resolve before any continuation | **SUPERSEDED_BY_RULING** | Referrals 2/3/4 were RULED in PR #444 §3–§5 and the source implements the rulings (verified independently, §10). Referrals 1 and 5 remain `MAY_DEFER` as classified. Two items remain open: `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` and **D-5.8** (§11) |
| **B-7** | (a) design↔forward epoch boundary unpinned; (b) all three binding status constants unpinned | **CLOSED** | Verified by re-mutation, not by reading: nulling `DESIGN_END`, `DESIGN_START` and `FORWARD_FLOOR` **in isolation** each fails the suite (5 / 2 / 1 failures); `PRODUCTION_READY` (3), `EXECUTION_PERFORMED` (2), `NEW_EPOCH_ADOPTED` (3) and `IMPLEMENTATION_STATUS → "PASS"` (2) are all caught. Each guard now carries a unique message. **One adjacent limb is still unpinned** — the dead window's inclusive lower bound, **FR-14** |

---

## 9. PR #443 RF-1…RF-29 — independent disposition

**27 CLOSED · 2 CLOSED_BUT_NARROW · 0 OPEN · 0 UNVERIFIABLE.** Each was
reproduced against current source; the mutation-class items (RF-20…RF-29) were
re-mutated rather than assumed.

| ID | Disposition | Evidence |
| --- | --- | --- |
| RF-1 ISO comma separator | CLOSED | `.0000005`, `,0000005` and an offset fraction `+00:00:00.9999999` all refused; all-zero excess accepted per §12.23 |
| RF-2 docstring guarantee | CLOSED | Guarantee restated, not overclaimed: a consistently-lying subclass is still accepted and the docstring now says so; an inconsistent one is refused |
| RF-3 bar-level OHLC guard | CLOSED | `_assert_bar_coherent` refuses `bid high 1.0 < low 1.2` at the bar, and the negative-spread guard fires on both `spread_open` and `spread_close` |
| RF-4 record identity | CLOSED | One row object ×15 → "the same row object appears at indices 0 and 1" |
| RF-5 `Path` subclass | CLOSED | A `Path` subclass whose `__str__`/`__fspath__` lie is refused; `Path(obj)` also refused |
| RF-6 `str`-subclass artifact name | CLOSED | Checks read the pinned value; `../../escape.json` refused |
| RF-7 exact-match metric keys | **CLOSED_BUT_NARROW** | All eight named keys refused; **run-together spellings still clean** (`sharperatio`, `netpnl`, `maxdrawdown`, `informationratio`) and written to disk — see **FB-3(b)** |
| RF-8 truthiness as claim | CLOSED | Denial is an explicit closed vocabulary; `False` and `"no"` clean, `True`/`"yes"`/`0`/`None` refused |
| RF-9 write-stage residue | CLOSED | Refusals at eight stages leave residue NONE; the `out_dir` leak does not reproduce |
| RF-10 non-finite key | CLOSED | `{nan: 1}` → `['gate3a_non_finite_key','gate3a_non_string_key:nan']` |
| RF-11 unserialisable payload | CLOSED | `Decimal('NaN')`, `set`, numpy, mixed keys → `gate3a_unserialisable_payload:TypeError` as a scrub finding |
| RF-12 casing / near-synonyms | CLOSED | `tier1`, `productionready`, `BYTEADMISSIBLE` and all five near-synonyms are refused; `PASSED`, `COMPASS`, `BYPASS`, `ROBUSTNESS`, `NOT_PRODUCTION_READY` stay clean |
| RF-13 non-`str` status | CLOSED | `b"PASS"`, `["PASS"]`, `None`, `42` all refused unread |
| RF-14 unknown flag / empty call | CLOSED | `training=False`, `{}`, `train=0`, `train="no"` all refused |
| RF-15 docstring routing claims | CLOSED | Current docstrings match the current caller graph exactly, including the three guards with **zero** non-test callers |
| RF-16 stress forms / restriction | CLOSED | Both mandatory, verbatim-matched to the committed plan; omitting either raises |
| RF-17 `CLAIM_SCOPE` | CLOSED | Committed spelling validates; the code-minted variant is refused |
| RF-18 `spread_open` | CLOSED | Emitted, equals `ask_o − bid_o`, finiteness- and sign-checked |
| RF-19 20×3 coverage | CLOSED | Raises and names the missing cells; the boolean is deleted |
| RF-20 two-faced `str` pin | CLOSED | Mutating `str.__str__(ts)` → `str(ts)` fails 2 tests |
| RF-21 source-text assertion | CLOSED | Test is now behavioural (child interpreter under `-O`); nulling either import-time invariant fails it |
| RF-22 vacuous glob | CLOSED | Moving `artifacts/m15_gate3a/` aside fails the test |
| RF-23 floor conjunction | CLOSED | `or`→`and` fails 2 tests, in both the holdout and validation branches |
| RF-24 one-minute gaps | CLOSED | `hole > 0` → `hole > 1` fails `test_rf24_one_minute_gaps_are_counted` |
| RF-25 negative spread guard | CLOSED | Nulling it fails 2 tests — both `spread_close` and `spread_open` |
| RF-26 lazy evidence | CLOSED | Generators refused at both sites; nulling either guard fails |
| RF-27 vacuous input | CLOSED | `entries: []`, `"PASS"`, `42`, `None` all refused; three mutations fail 1/4/2 tests |
| RF-28 zero lookback | CLOSED | `<= 0` → `< 0` fails 3 tests |
| RF-29 documented exception types | CLOSED | Missing side key → `AggregationError`; missing `overlap_fraction` → `EffectiveNError`; non-dict table → `CostSchemaError`; the three mutations fail 2/3/8 tests. **One new instance of the same class is open** — `TimestampError` leaking from `assert_per_file_bounds` (**FR-10**) |

---

## 10. PR #444 §12 — contract conformance

| § | Verdict | Note |
| --- | --- | --- |
| 1 crossed quote refuses · 2 `ask == bid` not crossed | CONFORMANT | Four side pairs, four distinct messages, survives `-O` |
| 3 duplicate minute aborts | CONFORMANT | Canonicalise-then-detect; the minute is claimed before the quality disposition |
| 4 zero tolerance, structural | CONFORMANT | Established by AST sweep of every module-level constant and every default |
| 5 six-field schema + identity | CONFORMANT | Identity held over 200 randomised scenarios; `absent` and `rejected` reach different fields. See FO-4 on `rejected`'s reachability |
| 6 `missing_minute_count` not certifying | CONFORMANT | `coverage.MINUTE_ACCOUNTING_FIELDS` excludes it and unrecognised keys are refused. Meaning stated in a docstring, not in the emitted payload |
| 7 all required minutes usable | CONFORMANT | The bar's own `n_source_bars`/`complete_bucket` decide, not the totals |
| 8 coverage set equality | CONFORMANT | All five failure modes distinct; 20-pair conjunction |
| 9 calendar interface fails closed · 10 never infer / synthesise | CONFORMANT for the declared-artifact route; **PARTIAL** for the rule route (**FR-8**) | No market hours invented anywhere |
| 11 hashing is a byte read | **NOT CONFORMANT** | The dedicated guard is caller-answerable (**FB-5**) |
| 12 co-measurement / verifier / consumer | **PARTIAL** | Co-measurement and disagreement handling correct on plain values; the pass identity is unpinned (**FB-5**) and W3 is not a precondition (**FB-6**) |
| 13 token separation, promotion forbidden | **NOT CONFORMANT** | Public-API routes (constructor, `replace`, dict, `copy`, `deepcopy`, `pickle`, feeding a `DeclarationRecord` to the evaluator) all correctly refuse; the promotion guard itself is defeated by a two-faced `str` (**FB-5**) |
| 14 reader-free; pin the direction and the reverse-caller set | **PARTIAL** | Source correct and one direction pin exists; reader-freedom and the reverse-caller set are pinned by nothing (**FB-8**) |
| 15 measured conjunctions over 20 | CONFORMANT | 19, a `None`, and an empty map each raise |
| 16 cost-table 20×3 raises | CONFORMANT | Names each missing cell |
| 17 separate output directory / never overwrite | **PARTIAL** | Never-overwrite proven; the output directory has no mechanism (FO-1) |
| 18 protect the five trees; cwd-independent | **PARTIAL** | Correct for present roots; fails open for an absent one (**FB-4**) |
| 19 negative-control rule | **PARTIAL** | Eleven attestations deleted where the fix note says; three one-valued fields introduced in the same edit and three of R-1's own eleven survive in the committed artifacts (**FR-5**, FO-3) |
| 20 pinned terms / `effective_n` | CONFORMANT for the named renames; **PARTIAL** on R-2 overall (FO-5) | The `count_quantity` gate is genuinely mandatory and refuses both confusable names |
| 21 record-identity guard · 22 `spread_open` · 24 docstring retraction | CONFORMANT | Each verified behaviourally |
| 23 single formatter / `+00:00` / fractions | CONFORMANT | All three limbs, plus a writer-side backstop |
| 25 schema shape constraint | **NOT CONFORMANT** | See **FB-9** |

---

## 11. D-5.8 — classification

**`MUST_RESOLVE_BEFORE_GATE3A_CONTINUATION`.**

The behaviour is not in dispute and no threshold is proposed here. Lead-verified:
a calendar declaring **one slot per pair**, with one certified bar per pair and a
self-consistent 15-minute accounting block, returns a `CoverageResult` over all
twenty pairs, and that result satisfies the CV limb against `bars_scanned=1`. Only
an *empty* slot set fails closed. The single structural control is the arithmetic
bind `expected_source_minute_count == 15 × |expected slots|`, which a degenerate
calendar simply satisfies degenerately.

The classification follows from three facts and nothing else:

1. §8.8 is committed normative text and its "never" is absolute. It is not
   discharged by the current source, and the source says so itself.
2. The gate-3a continuation is the only gate at which the design dataset is
   derived; no later gate re-derives it.
3. The number cannot be minted by an implementer, and D-6 forbids this module to
   decide how many M15 buckets an epoch contains.

Together these mean it must be settled *before* the continuation, by an authority
that may set it — which is a contract Gate-decision, not an implementing session.

**How it may be discharged, without deciding it here.** The natural vehicle is the
already-required `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`: if the
approval of the concrete calendar artifact records the expected slot count per
pair, a degenerate calendar is excluded by that approval and §8.8 is satisfied in
substance. Two things must then be true and are not yet: the approval must
explicitly cover the slot **count**, not only the artifact's fields; and FB-1 and
FR-7 must be closed, because at HEAD the code cannot distinguish an approved
calendar from a forged one, so an approval it cannot enforce is not a control.

The alternative — a non-numeric structural criterion (span, continuity, or
coverage of the declared epoch) — is also available to the decision-makers and is
mentioned only so the choice is not presented as "pick a number or nothing".

*(For completeness, the classification the implementer's fix note recorded —
"whether it must resolve before the continuation, or may defer, is itself for the
next contract Gate-decision" — is not a classification; the prompt for this audit
requires exactly one of the four, and this document supplies it.)*

---

## 12. Test-safety verification boundary (PR #446)

Scoped as instructed: PR #446 is not re-audited here; it is assessed only as the
boundary that makes this audit safe to perform.

**Sufficient for that purpose.** With no opt-in granted, a default run cannot
reach a database, real research data, a broker or external storage. Verified by
execution: a non-sqlite engine URL is refused and the refusal echoes only the
dialect (the `str.split("://")[0]` leak is closed, including the no-`://` case,
which yields `<unparsable>`); an off-loopback TCP connect is refused while all
nine loopback spellings are allowed; the collection gate cannot be forced open by
`-m`, `-k`, a direct nodeid or a marker expression; opt-in parsing fails closed on
every typo; research-data helpers make **no filesystem probe at all** without the
opt-in, so a default run cannot even discover which files exist; and the guards
install at conftest import, before any test module body runs. The whole 1100-test
gate-3a suite, traced under an `open` audit hook, touched only the eight committed
`artifacts/m15_gate3a/*.json`, eight protected stage-evidence files hashed by the
session fixture, three source files, its own modules and `tmp_path` — **zero opens
under `data/`, zero `.env`, zero sockets, zero DB**.

**Two residual routes, recorded as FR-19 for a separate Work PR.**

1. **The `.env` guard is route-dependent.** `tests/conftest.py:253` prefilters
   with a case-sensitive literal `endswith(".env")` and `:255` compares
   `abspath(...).lower()`, which strips neither trailing dots nor spaces.
   Lead-verified against a **synthetic decoy** placed in a sandbox root (the real
   repository `.env` was never opened):

   ```
   absolute .env        REFUSED      case variant .ENV    READ_OK  'DECOY=1'
   relative .env        REFUSED      case variant .Env    READ_OK  'DECOY=1'
                                     trailing dot .env.   READ_OK  'DECOY=1'
                                     trailing space '.env ' READ_OK 'DECOY=1'
   ```

   The audit hook is armed on every route — the absolute cases prove that; it is
   the *matcher* that is route-dependent. The contract test is named
   `test_the_repository_dotenv_cannot_be_opened_by_any_route`, and that guarantee
   as stated is false. The fix shape is the one `path_authority` already uses:
   compare by filesystem identity (`os.stat`/`samestat`) rather than by string,
   and drop or case-fold the `endswith` fast path. Exposure is the developer
   machine — CI is Linux and case-sensitive — which is exactly where the original
   incident happened.
2. **The socket guard wraps only `connect`/`connect_ex`,** so UDP `sendto` and DNS
   resolution leave the machine while the contract suite's own section heading
   reads "nothing leaves the loopback interface". No in-tree test uses either
   route.

Two further scoping notes, neither a defect: child interpreters inherit no guard
except `PYTHON_DOTENV_DISABLED` (five spawns inside `tests/m15_gate3a/`, all tiny
inline probes over synthetic input); and a *loopback* database remains reachable
by construction — the engine guard is the only DB gate, and it holds only because
every DB path in this repository happens to route through
`sqlalchemy.create_engine`, which nothing pins.

---

## 13. Disagreements and how they were resolved

Resolved on the evidence, never by majority. Four are recorded because the
resolution changed a grade.

1. **§12.25's reading.** One role graded it a blocker on the strict reading; the
   implementer took the permissive reading and pinned it. The lead ruled **FB-9**:
   the technical impact is bounded and the operative last clause *is* satisfied,
   but a clause headed "non-negotiable" was re-interpreted inside a Work PR and
   frozen in a test, which is the governance class of the merged B-4 finding.
   Recorded as a blocker whose remedy is a **ruling**, not further implementation.
   The competing reading is stated in full inside FB-9 so the decision-makers can
   overrule it.
2. **Whether D-11 promotion is conformant.** The contract role tested the
   constructor, `dataclasses.replace`, dict round-trip, `copy`, `deepcopy`,
   `pickle` and the evaluator, found all refused, and graded CONFORMANT. Two other
   roles defeated `assert_byte_level_claim` with a two-faced `str`. Both are
   correct about what they tested; the union is that promotion **is** achievable,
   and the lead reproduced it. Graded NOT CONFORMANT inside **FB-5**, with the
   mitigation (the scrubber refuses the spelling at the write boundary; no
   non-test caller exists) recorded rather than used to dismiss it.
3. **Whether the absent-protected-root case is a real bypass.** The disposition
   role tested a *junction* alias to an absent `models/` and found it **refused**
   (`resolve()` expands reparse points), concluding the earlier "defence-in-depth
   only" grading survives. The containment role and the lead tested a
   *trailing-dot* spelling and found it **allowed**, with the creating write
   landing inside the real tree. No contradiction: the two alias classes behave
   differently, because `resolve()` cannot canonicalise a component that does not
   exist. **FB-4** stands on the trailing-dot evidence, and the junction result is
   recorded in §7 as a genuine clean.
4. **Grade of `Provenance.stream_id` and the `subject`/token pins.** One role
   graded them blockers, another flagged its own calibration as uncertain given
   that none of the guards has a non-test caller. The lead reproduced every one
   and graded them a single blocker (**FB-5**) rather than five, because they are
   one defect family with one remedy — and because §15.4 places the P/V packages,
   which will be the first real callers, at the *next* gate.

5. **Grade of FB-10.** The mutation role graded the `WarmupPolicy` swallow a
   blocker and flagged that the grade turns on whether a `__class__`-spoofing
   object is in scope. The lead kept it a blocker on two grounds: the package's
   own N-1 / P-1…P-7 remediation established that object as in scope, and every
   *other* module refuses the identical object — so the defect is an
   inconsistency within the package's own threat model, not a disagreement about
   where the model's edge lies. What it disarms — the T-1 burn-in — is also the
   most consequential thing in the module.

One further correction, not a disagreement between roles: the fix note's §7d
justification for downgrading the absent-protected-root case ("all protected roots
are git-tracked") is factually wrong — `models/` is gitignored. The premise is
false and the conclusion it supported does not hold (FB-4).

---

## 14. Test adequacy and mutation resistance

An independent battery was constructed from the current source rather than copied
from any previous round. Counting the lead's own and the roles' non-overlapping
mutants, **more than 500 single-edit mutations** were applied across all 15 modules, each
with `__pycache__` purged and the mutated text asserted present before the run.
The dedicated battery was **343 mutants → 310 killed, 33 survived**, of which 5
were deliberate calibration controls, leaving **28 real survivors → 19 genuine
coverage gaps, 8 redundant, 1 equivalent**. Every batch carried a calibration
pair (one mutant that must die, one comment-only edit that must survive) and all
four pairs behaved correctly, so the harness neither silently no-ops nor
spuriously kills. Alongside it: 103 mutants over the time/pair/cost/aggregation
surface (97 killed), 22 over coverage and the calendar interface (22 killed), 12
over the scrubber and status surface (12 killed), 5 over containment (5 killed),
and 15 lead-run mutants spanning every module (15 killed).

**The suite is strong against the guards that exist.** Every material guard the
lead mutated was killed: both epoch limbs and the forward floor in isolation, all
four status constants, the crossed-quote refusal and its `ask == bid` boundary,
coverage set equality, the missing-measurement raise, each of the four proof
limbs, the promotion guard, calendar approval, confusable folding, invisible-
character stripping, each protected prefix, the never-overwrite rule, the
canonical-timestamp emission path, the cost-table coverage raise, the effective-N
floor conjunction in both roles, the session partition, and the record-identity
guards in three modules.

**Survivors, classified by source behaviour rather than assumed.**

| Survivor | Class | Basis |
| --- | --- | --- |
| `artifacts.py:971-972` non-finite leaf under a **declared** numeric key | **genuine gap — worst survivor** | HEAD reports `gate3a_non_finite_value:pip_size`; mutated it scans `[]`, and neither `evidence.scan_payload` nor `serialise` catches NaN, so the writer would emit the non-standard `NaN` literal. The undeclared twin *is* pinned |
| `no_overlap.py:110` dead-window lower bound `<=` → `<` | **genuine gap** | `2026-03-01T00:00:00Z` is used by no test; end-to-end consequence measured — `validate_calendar` accepts a calendar declaring the first instant of the consumed holdout → **FR-14** |
| `no_overlap.py:110` upper bound → `<= DEAD_END` | genuine gap, unreachable via in-package callers | the deliberate "final second is dead" widening is unpinned; both `_normalise_slot`s run the grid check first, so no caller reaches the sub-second tail |
| add a byte reader / socket import to the package | **genuine gap** | §12.14's mandated pin does not exist → **FB-8** |
| import `Real365dBaProvider` into the package | **genuine gap** | no outbound-import allowlist → **FB-8** |
| `path_authority.py:262` `candidate.resolve()` → `candidate` | **genuine gap** | with a protected root absent, only the name limb runs; a `..`-bearing spelling of `firstrun_730d_ba` flips REFUSED → ALLOWED. The test that records this case asserts the degraded path is "not reachable in practice" because all roots are tracked — `models/` is not → **FB-4**, FO-16 |
| `proof.py:1562-1564` agreement loop → `pass` | **genuine gap** | inside `evaluate_four_limbs`, both a scalar disagreement and a digest disagreement become ACCEPTED; `assert_records_agree` is tested only as a unit, never through the evaluator |
| `proof.py:1694` consumer artifact-identity check | **genuine gap** | a consumer re-verifying a *different* artifact with the proof's digest is accepted; W3's "the re-verification is of the artifact about to be read" is unpinned |
| `proof.py:1470` CV roster set equality → superset / count | **genuine gap** | a 21st `PairCoverage` is absorbed; the count variant leaks a bare `KeyError` |
| `proof.py:919` `is_declaration_only` → `return False` | **genuine gap** | an exported predicate with zero references in the test suite |
| `proof.py:1323` role pairing | genuine gap (public entry point) | `assert_records_agree(verifier, producer)` accepted; redundant inside the evaluator, not at the public API |
| `coverage.py:647-650` `unusable` **absent** limb | **genuine gap** | `absent=1, rejected=0` with every slot certified becomes ACCEPTED; the mirror *rejected* limb is killed |
| `coverage.py:454-458` `complete_bucket` bool check | **genuine gap** | `1` and `"yes"` both accepted as the certifiability flag |
| `cost_schema.py:257` `pin_number(v)` → `float(v)` | **genuine gap** | a lying `float` subclass holding −50000.0 validates and reports `min_observed_spread_pips = 0.0` — the exact N-1 defect the module's own comment says it closed |
| `artifacts.py:305-306` whole-string forbidden-status fallback | **genuine gap** | `"P A S S"`, `"M E E T S"`, `"R O B U S T"`, `"V A L I D A T E D"` are caught **only** here |
| `artifacts.py:387` `_MAX_PROHIBITION_ITEMS` → 10000 | **genuine gap** | the 40-entry prohibition list is no longer reported |
| `warmup.py:88` `is_event_eligible` validation call | **genuine gap** | `WarmupPolicy(0, 0).is_event_eligible(5)` returns `True` instead of raising |
| `calendar_authority.py:229-232` non-string field | genuine gap (degraded error) | leaks a bare `TypeError` instead of `CalendarMalformedError`; same for `coverage.py`'s missing-`ts` path (bare `KeyError`) |
| `timeutil.py:133` drift `!= 0.0` → `> 1e-6`; `effective_n.py:113` `< 0` → `< -1`; `:128` `<= 1.0` → `<= 1.1`; `no_overlap.py:322` whitespace-only `filename` | genuine gaps | exact-boundary inputs untested → FO-8 |
| `artifacts.py:198` NFKC removal; `:996-997` undeclared value type; `:1240`/`:1242` the two `refuse_real_path` calls; `proof.py:205`/`:222` import guards; `proof.py:1470` count variant; `proof.py:1567` `_limb_bi(verifiers)` | **redundant** (8) | each is covered by a sibling guard on every distinguishing input tried; removing both members of each pair *is* killed |
| `cost_schema.py:303` 20×3 set equality → count equality | **equivalent** | `seen ⊆ PAIRS_20 × SESSIONS_UTC` upstream and duplicates raise, so `\|seen\| = 60 ⟹ seen = required_cells`; no distinguishing input exists |
| `aggregation.py:363` `n > FULL_BUCKET_SOURCE_BARS` | **unreachable** | fifteen distinct minutes bound a 15-minute bucket; the `pragma` is correct |
| both `_intersects_dead_window` limbs in the bound-checkers | **unreachable** | `DEAD_START == DESIGN_END + 1s` and `_DEAD_END_EXCLUSIVE == FORWARD_FLOOR`, both asserted at import with explicit `raise`; correctly `pragma`'d and documented |

**The limit of the method, stated plainly.** Twelve of the findings in §4 and §5 —
FB-1, FB-3, FB-6, FB-7, FB-8, FR-1, FR-2, FR-3, FR-4, FR-16, FR-17, FR-18 — are
**absent guards**, not broken ones, and FB-10 is a guard that exists and is
swallowed behind a wrong `pragma`, which mutation also cannot surface. No mutation of the existing code produces
them, and a mutation score of any value would have been consistent with all of
them. §13's acceptance bar asks for "no newly-introduced survivor"; that bar is
met for the code that was written, and it is the wrong instrument for the code
that was not. This is the fifth consecutive round in which a green suite preceded
real defects, and the pattern is now stable enough to name: **the fix closes the
instances the audit listed, the audit's next round finds the rest of each
family.** Breaking that cycle needs family-level remedies — seal the record types,
snapshot at the writer, derive the fold table, pin reader-freedom — not another
list of instances.

**Test-quality findings.** The suite is, on the whole, well built. The RF-21 class
(asserting on source text) is gone — the three AST-based tests check a property of
*committed artifacts or other scripts*, not of the module under test, and each
carries an explicit non-vacuity floor. Of 528 `pytest.raises` sites, **zero use
regex alternation**; 90 omit `match=`, all on module-specific exception classes,
and only three patterns are loose enough to be ambiguous (`match="numeric"`, and
`match="naive"` twice — both naive raise sites are independently pinned
elsewhere). All four `.glob()` sites carry a floor. Every loop-only assertion
iterates a literal tuple, so none is vacuous. `monkeypatch.chdir` is used
deliberately, to *prove* cwd-independence. No test freezes a fail-open as expected
behaviour, with the single exception recorded at FB-9.

Three qualifications. **`# pragma: no cover` does not appear only on unreachable
guards** — seven sites are reachable (FR-20), and one of them hides FB-10.
**Four Windows-only containment tests never run in CI** (`ubuntu-latest`), so the
extended-drive, UNC-localhost, UNC-loopback and extended-UNC identity limbs are
verified only on a developer machine, while the symlink identity test is the
mirror case that never runs *there*. And `tests/m15_gate3a/test_recheck_fixes.py:1081`
applies `pytest.mark.skipif` to a non-test **helper**, where it is inert — the
real gating is an inline `pytest.skip`, so behaviour is unaffected, but the
decorator reads as platform gating and is not.

---

## 15. Non-authorisation

This document authorises nothing. It permits no real data read, no real M15
derivation, no checksum execution, no spread computation, no validation, holdout,
training, inference, execution, or broker/paper/live activity. It adopts no epoch
and does not lift the forward-epoch WAIT. It generates and approves no calendar
artifact, and invents no market hours. It decides no D-5.8 threshold. It changes
no source, test or frozen contract, and starts no Work PR. It does not claim
reproducibility under a frozen `uv` environment — the lockfile remains
known-stale and `uv sync --frozen` reproducibility is **not** claimed.

`PRODUCTION_READINESS_NOT_CLAIMED` · `NO_EXECUTION_PERFORMED` ·
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`.

---

## 16. Gates still required before a gate-3a continuation

1. **This Gate-decision** — merged on human + ChatGPT approval; the BLOCKED
   verdict binds at that point. Merging records the verdict; it grants no
   acceptance.
2. **One targeted-fix Work PR** carrying FB-1…FB-10 and FR-1…FR-18, FR-20 and
   FR-21, plus a ruling on FB-9's reading of §12.25. FR-19 belongs to a
   **separate** test-safety Work PR — it is not gate-3a research machinery and must not be folded in.
3. **A fifth independent source-audit re-check**, in a session separate from every
   fix author.
4. **A contract Gate-decision on D-5.8** (§11), and on the §12.25 reading if the
   fix PR does not resolve it by adopting the strict one.
5. **The P/V reader design PR** — synthetic-only, with its own audit. §12.14's
   reader-freedom and reverse-caller pins should exist **before** it lands, not
   after.
6. **Calendar artifact approval** —
   `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`, human + ChatGPT,
   real-data-independent. Not discharged by anything in this document, and not
   discharged by an ACCEPTABLE source-audit verdict either.
7. Only then a **separately-authorised gate-3a continuation** (playbook §5) — Red,
   design-span only, metadata-only outputs.

**Recommendation.** Take the §12.25 ruling and the D-5.8 classification together,
in one contract Gate-decision, **before** the next fix PR starts — the same lesson
PR #444 recorded, for the same reason: otherwise the fix session decides the
contract questions it may not decide. Then one Work PR for FB-1…FB-10 / FR-1…FR-18, FR-20, FR-21.
The two highest-value structural changes it can make, because each closes a whole
family rather than an instance, are: **seal the record types** (`__init_subclass__`
plus a construction check, closing FB-1 and FR-3 together), and **snapshot the
payload once at the writer** (closing FB-2 and making the scrubber's verdict and
the written bytes the same object). Adding the §12.14 pins (FB-8) is cheap and
protects everything the next gate builds on.
