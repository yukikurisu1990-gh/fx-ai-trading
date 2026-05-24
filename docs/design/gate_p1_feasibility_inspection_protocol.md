# Gate P1 — Read-only Local-data and Pipeline Feasibility Inspection Protocol

**Status:** Doc-only inspection-protocol design memo (PR-A of the two-PR
Gate P1 split). Authored under the new-epoch contract of PR #361
(Route E2 PRIMARY, `LOCAL_DATA_CANDIDATE_EPOCH_PENDING_FEASIBILITY`).
Locks the Gate P1 inspection contract; performs no inspection and
computes no hashes. PR-B (the separately authorised read-only
execution PR) will implement the inspection per this locked spec and
emit the Gate P1 report.

- branch: `research/gate-p1-feasibility-inspection-protocol-design`
- base: `master @ 2b24695` (PR #361 merge commit)
- file added: `docs/design/gate_p1_feasibility_inspection_protocol.md`
  (this file only)

---

## §1 — Carry-forward status

These statuses are binding inputs to this memo; none are modified by
this PR.

| Item | Status |
|---|---|
| master tip | `2b24695` (PR #361 merge) |
| Route E2 | PRIMARY — `LOCAL_DATA_CANDIDATE_EPOCH_PENDING_FEASIBILITY` |
| Route E1 | DISSENT / escalation — `BLOCKED_PENDING_DATA_ACCESS_FEASIBILITY` |
| Route E3 | fallback only if E2 Gate P1 HALTs and E1 remains blocked |
| V2-expanded Stage 2 | `HALTED_INPUT_UNAVAILABLE` |
| F-1 strict historic-anchor reproduction route | `UNEXECUTABLE_INPUT_UNAVAILABLE` |
| PR #356 audit outcome | `TARGETED_VERIFICATION_REQUIRED` preserved |
| Historic nine-eval picture | Class U / empirically unreconfirmed |
| Phase 27 / Phase 28 / Phase 29.0a verdicts | preserved verbatim |
| A0-broad β | remains halted |
| Stage 2 implementation branch (`research/tabular-targeted-verification-v2-expanded-stage2-preflight @ 0234ed3`) | retained locally only; unpushed; not formal evidence |

---

## §2 — Gate P1 purpose + mandatory distinction from Gate P2

**Purpose.** Determine, without side effects, whether locally-present
raw data is admissible as input to a new provenance-bound dataset
epoch. If E2 is not admissible, clarify the conditions under which
either E1 progresses or E3 is invoked.

**Gate P1 does NOT create an epoch.** It produces a report and a
candidate verdict only.

**Gate P1 does NOT execute** baseline, control, signal generation,
label generation, training, sweep, or A0-broad.

**Mandatory distinction between Gate P1 and Gate P2 (binding):**

| Item | Gate P1 | Gate P2 |
|---|---|---|
| Side effects on `data/` | none | none (writes go only to a new epoch namespace) |
| Network access | none | none |
| Credentials | not read | not read |
| Reads raw local files | yes (read-only) | yes (read-only) for input |
| Inspects code paths | yes (import + hash) | yes (executes the code paths) |
| Writes signals / labels / split / row-set | NO | YES (into a new epoch namespace) |
| Manifests | none authored | full set authored |
| Round-trip byte verification | NO (deferred; see §6) | YES (binding under PR #361 §5.P2.2) |
| Highest emissible outcome | `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW` | `NEW_EPOCH_DATASET_BUILT` |
| Authorises Gate P2? | NO (requires separate user decision) | n/a |
| Authorises baseline / control? | NO | NO |
| Authorises A0-broad? | NO | NO |

Restated as bindings:

- Gate P1 PASS = `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW` at most
- Gate P1 PASS is **not** `NEW_EPOCH_DATASET_BUILT`
- Gate P1 PASS is **not** baseline / control execution authorisation
- Gate P1 PASS is **not** A0-broad resumption authorisation

---

## §3 — Raw local-data inventory inspection contract (PR-B scope)

For **each candidate span** and **each pair in the frozen pair
universe**, PR-B will execute the inspection items below in
read-only mode. Candidate spans inspected:

- `730d_BA` candidate (local `data/candles_<PAIR>_M1_730d_BA.jsonl`)
- `365d_BA` candidate (local `data/candles_<PAIR>_M1_365d_BA.jsonl`)
- any other already-present complete BA span discovered during
  inspection (e.g. additional `*_BA.jsonl` siblings under `data/`)

PR-B writes one `raw_inventory_<candidate_id>.json` per candidate
into the Gate P1 report directory (path constrained per §8).

| Per-pair item | Spec |
|---|---|
| filename pattern | `data/candles_<PAIR>_M1_<spanlabel>_BA.jsonl` only |
| pair-universe source of truth | resolved PAIRS_20 list + `pair_universe_hash` (resolved once at inspection start; recorded in report) |
| presence | boolean; missing files recorded but never fetched |
| size (bytes) | recorded |
| SHA-256 | computed from existing local bytes (read-only) |
| row count | count of JSONL records |
| UTC timestamp min / max | parsed-UTC; recorded |
| timestamp monotonicity | strict ascending; non-monotonic positions counted; not corrected |
| duplicate timestamps | count per file |
| schema fingerprint | required column presence + dtypes vs the declared bid/ask OHLC schema (schema declared in §3.1) |
| required bid/ask OHLC validity | missing / null / non-finite checks per required field |
| gap profile | maximum gap, weekend / market-closure pattern, holiday gap density |
| irregularity findings | clock-shift, schema-version drift, mixed-pair contamination heuristics |

**Per-candidate aggregate item:**

- common observation interval across all in-universe pairs:
  `[max_i obs_start_i, min_i obs_end_i]`

**Bindings (restated):**

- read-only inspection of existing local files only
- no mutation, overwrite, rename, tmp-and-rename, or any other write
  under `data/`
- nominal filename depth (`_730d_BA`, `_365d_BA`) is recorded as a
  nominal label only and is **never** treated as the actual validated
  span without content validation
- SHA-256 hashing is permitted **only** in PR-B (which is read-only
  execution); this PR-A authors no hash

### §3.1 — Declared bid/ask OHLC schema

PR-B will declare and version the expected schema in code; PR-A
captures the conceptual contract:

- required field set per record: timestamp (UTC), bid_open, bid_high,
  bid_low, bid_close, ask_open, ask_high, ask_low, ask_close, volume
- exact field names, dtypes, and ordering are fixed by the PR-B
  implementation and recorded in the `schema_fingerprint` field of
  the per-pair inventory entry
- any deviation from the declared schema → per-pair field
  `schema_valid = false` and the candidate cannot reach
  `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW` for any
  pair that fails the schema check

---

## §4 — Required-input dependency inventory contract (PR-B scope)

PR-B will publish a per-consumer × per-dependency classification table
into `dependency_inventory_<candidate_id>.json`.

**Consumers (each must be inventoried):**

- signal generation
- ATR / volatility inputs
- R7-A feature construction
- D-1 executable PnL
- target / label generation
- train / val / test / frozen-OOS split creation
- S-B baseline
- S-E control
- future A0-broad temporal inputs (sequence windows)
- future A0-broad static R7-A context

**Classification (one per dependency × consumer cell):**

| Class | Meaning |
|---|---|
| `AVAILABLE_AS_RETAINED_RAW_LOCAL_INPUT` | the dependency is satisfied by an already-present, read-only-inspectable local raw input within the candidate span |
| `DETERMINISTICALLY_DERIVABLE_FROM_ACCEPTED_RAW` | the dependency is reconstructable from accepted raw input via a committed, code-hashed derivation function (exact function path + source SHA-256 recorded) |
| `MISSING` | no satisfactory raw input or derivation function is present |
| `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION` | code path exists but its applicability or output-emptiness cannot be assessed without running it |

**Bindings:**

- PR-B may inspect / import / hash code paths only; **no execution**
- PR-B may not run signal generation or label generation
- PR-B may not claim that non-empty labels will be produced (that
  claim is Gate P2's alone, per PR #361 §4)
- PR-B may not silently infer that M5 / H1 / D1 are derivable from
  M1 BA without locating and code-hashing the exact derivation
  function and inspecting its required semantics; absent that
  evidence, the dependency is `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION`
  at best
- the existing development-slice labels parquet
  (`artifacts/stage25_0a/path_quality_dataset.parquet`, currently a
  3-pair / 1-day / 1,306-row stub) **may not be reused** as the
  labels source; the inventory must require labels regeneration under
  the new epoch namespace (deferred to Gate P2)
- silent substitution of derived candles for independently-sourced
  higher-TF candles is prohibited (cross-reference to PR #361 §6)

---

## §5 — Candidate interval and epoch-identity candidate output spec (PR-B scope)

PR-B will report, for each feasible candidate, into
`coverage_<candidate_id>.json`:

- `candidate_id` (locally unique within the Gate P1 report)
- `nominal_span_label` (e.g. `730d_BA`; nominal only)
- proposed `observation_start_timestamp_utc` (UTC; from intersection)
- proposed `observation_end_timestamp_utc` (UTC; from intersection —
  actual common maximum, not nominal)
- `span_days_effective` (computed from the interval, not nominal)
- pair universe + `pair_universe_hash`
- raw schema version
- common-coverage quality findings (gap density, monotonicity
  violations, regime markers within the interval)
- scientific-adequacy flags requiring later review (cross-reference
  to PR #361 §10) — flags only; no adequacy verdict at Gate P1

**Will NOT be reported by Gate P1 (binding):**

- `epoch_freeze_timestamp_utc` as though an epoch exists (this is
  Gate P2 construction-time; Gate P1 does not freeze anything)
- canonical `manifest_id` of a built epoch
- baseline / control metrics
- A0-broad eligibility statement
- any historic-verdict modification

**The memo creation date and the inspection date are never used as
the observation cutoff.** Observation interval is computed strictly
from inspected file contents.

---

## §6 — Retention feasibility inspection contract (PR-B scope)

**Binding (corrected scope):** Gate P1 retention inspection is
**strictly read-only and local**. It contains **no** write / read /
delete probe against any storage destination, no network access, no
credentials usage, and no external service contact.

PR-B will report into `retention_feasibility_<candidate_id>.json`:

| Field | Definition |
|---|---|
| `expected_total_raw_bytes` | sum of inspected raw-file sizes for the candidate span × pair universe |
| `expected_labels_storage_estimate_bytes` | upper-bound estimate only (computed from documented schema × row-count projection); no labels generation |
| `expected_split_manifest_storage_estimate_bytes` | upper-bound estimate |
| `expected_total_retention_bytes` | sum of the three above |
| `in_repo_retention_size_guard_bytes` | the pre-stated maximum admissible in-repo retention budget (declared in §6.1) |
| `in_repo_retention_within_guard` | boolean: `expected_total_retention_bytes ≤ in_repo_retention_size_guard_bytes` |
| `existing_local_immutable_archive_visible_read_only` | true only if a locally-mounted, read-only, immutable archive location is visible at inspection time without any credentials and without any network call (e.g. an OS-mounted read-only filesystem path that the user has previously identified and that the inspection can `os.stat` without privilege) |
| `restoration_procedure_documented` | boolean per identified candidate destination |
| `candidate_retention_options_requiring_later_authorisation` | enumerated, descriptive only; no probe attempted |
| `retention_classification` | one of the four values defined in §6.2 |

### §6.1 — In-repo retention size guard

A pre-stated, documented byte budget that the new epoch's combined
raw + labels + split + manifest footprint must not exceed if the
intended retention path is in-repo bytes. PR-B will declare the exact
constant in its source; PR-A's binding is that the constant is
**explicit**, **documented**, and **referenced by hash** in the
retention-feasibility report. The exact byte value is a PR-B
implementation decision (it must be conservative enough not to bloat
the repository while admitting a realistic dataset epoch).

### §6.2 — Retention classification (binding)

Exactly one of the following classifications is assigned per
candidate:

| Classification | Condition |
|---|---|
| `IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2` | `in_repo_retention_within_guard = true`; no bytes are committed yet; Gate P2 will perform the actual commit + byte-round-trip verification |
| `EXISTING_LOCAL_IMMUTABLE_ARCHIVE_VISIBLE_READ_ONLY` | a locally-mounted, read-only, immutable archive is visible at inspection time without credentials or network; visibility alone does NOT prove Gate P2 retention success — it is a candidate input only |
| `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE` | an external / archive destination might be appropriate but requires a later write / read / delete or credential / network capability check that Gate P1 must not perform |
| `RETENTION_DESTINATION_UNRESOLVED` | no currently admissible retention path can be justified |

**Eligibility to emit `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW`
(binding):**

- raw inventory, dependency inventory, common coverage, and pipeline
  feasibility checks all pass for the candidate, **AND**
- retention classification is one of:
  - `IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2`, or
  - `EXISTING_LOCAL_IMMUTABLE_ARCHIVE_VISIBLE_READ_ONLY`

Otherwise:

- if the only viable retention path is
  `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`, Gate P1
  emits `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` with retention
  substatus `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`
- if classification is `RETENTION_DESTINATION_UNRESOLVED` and no
  in-repo or visible-immutable-archive option exists, Gate P1 emits
  the corresponding outcome (see §9)

**If a write / read / delete capability probe is later needed:**

- it is **not** part of Gate P1
- it must be either a separately user-authorised step after PR-A /
  PR-B review, **or** explicitly bound inside a later Gate P2
  authorisation

**Forbidden in Gate P1 (binding):**

- writing a test object to any destination (local, mounted, or
  external)
- reading back a test object from a storage service
- deleting a test object
- using credentials of any kind
- accessing a network endpoint of any kind
- accessing an external storage endpoint of any kind
- pre-approving named external destinations (S3 / release assets /
  S3 object-lock / IPFS / etc.); their admissibility is contingent on
  a later separately-authorised probe
- treating SHA manifests without retrievable bytes as sufficient
  (cross-reference to PR #361 §7)
- allowing gitignored local-only files to become binding authority
  again (cross-reference to PR #361 §7 anti-pattern)

---

## §7 — Pipeline feasibility inspection contract (PR-B scope)

PR-B may inspect **code paths and imports only**. It will write
`pipeline_feasibility.json` recording:

- which scripts / functions would generate signals
- which scripts / functions would generate labels
- which scripts / functions implement D-1 executable PnL
- which scripts / functions construct splits
- whether each path can be parameterised to write into a **new epoch
  namespace** (e.g. `artifacts/epoch-<manifest_id_preview>/…`)
  without overwriting historic / current local artifacts
- the SHA-256 of the source text of each identified function
- the enumerated work list of code changes required for Gate P2
  (design-level, not execution)

**Inspection mode (binding):**

- imports only; **no** `__main__` execution of any pipeline module
- function-signature + docstring + dependency-graph inspection
- code-hashing of identified functions (read-only; SHA-256 over
  source text only)
- **no labels parquet write**
- **no signal artifact write**
- **no baseline / control execution**
- **no LightGBM training**
- **no A0-broad execution**

**Prohibition restated:** Gate P1 must **not** claim that a labels
generator produces non-empty per-pair output. The most Gate P1 may
say is that the code path exists, imports cleanly, accepts new-epoch
namespace parameterisation, and that its source is hashed at value X.

---

## §8 — Data safety / no-side-effect enforcement contract (PR-B runtime guards)

PR-B will codify the following enforcement as runtime guards
(violations HALT the inspection with a structured violation report
and prevent any PASS outcome from being written).

**Write-path allow-list (binding):**

- only Gate P1 report artifacts may be written, and only under:
  `artifacts/gate_p1_report/<report_id>/`
- any attempt to write outside that prefix HALTs

**Explicit write prohibitions:**

- no writes under `data/`
- no writes under existing `artifacts/stage25_0a/` or any historical
  artifact directory
- no labels or signals writes
- no temporary mutation of existing datasets (no rename, no
  tmp-and-rename pattern over `data/` or `artifacts/`)

**Network prohibitions:**

- no network calls of any kind (URL fetch, socket, HTTP client,
  WebSocket, DNS-lookup-as-side-effect, etc.)
- no API or token handling

**Credentials prohibitions:**

- **no credentials reads, including no environment-variable
  presence-check**, unless a separately-authorised later step
  explicitly enables it
- no read of `OANDA_*`, `*_TOKEN`, `*_SECRET`, `*_API_KEY`, or any
  similar variable — neither for value nor for presence
- no output of any credential value to the report under any condition

**Stage 2 branch prohibitions:**

- no access to, push of, fetch of, checkout of, or modification of
  the Stage 2 implementation branch
  (`research/tabular-targeted-verification-v2-expanded-stage2-preflight`
  @ local `0234ed3`)

**Retention-probe prohibitions** (cross-reference §6):

- no test-object write / read / delete against any destination
- no external storage access
- no credential-based destination verification

---

## §9 — Gate P1 outcome ladder + retention substatus

PR-B emits exactly one primary outcome plus, where applicable, a
retention substatus. The full ladder:

| Primary outcome | Condition |
|---|---|
| `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW` | ≥1 candidate span passes raw inventory + dependency inventory + common-coverage + pipeline checks AND has retention classification `IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2` or `EXISTING_LOCAL_IMMUTABLE_ARCHIVE_VISIBLE_READ_ONLY` |
| `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` | raw files appear usable but retention destination, dependency reconstruction, or scientific-adequacy-review prerequisites remain unresolved for the strongest candidate |
| `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH` | no local candidate span satisfies required raw + dependency conditions |
| `RETENTION_DESTINATION_UNRESOLVED` | retention classification for every candidate is `RETENTION_DESTINATION_UNRESOLVED` (no admissible retention path) |

**Retention substatus** (attached to `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`
where applicable):

- `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`

**Outcomes Gate P1 must never emit (binding):**

- `NEW_EPOCH_DATASET_BUILT`
- any baseline / control verdict
- any A0-broad eligibility status
- any historic verdict modification (Phase 27 / 28 / 29.0a / PR #356
  / PR #360 / PR #361 unchanged)

---

## §10 — Relationship to E1 and E3

- **E1 remains blocked** unless a **separate** Data-Access Feasibility
  memo + execution PR is explicitly authorised by the user. Gate P1
  does not address E1.
- **Gate P1 must not access OANDA or any external provider** — no
  network, no credentials, no env-var presence-check
- **E3 is considered only** if E2 Gate P1 HALTs **and** E1 remains
  blocked **and** the user explicitly routes to E3
- **No auto-route after any Gate P1 outcome.** Whether outcome is
  PASS or HALT, the next step requires explicit user authorisation;
  this memo enumerates candidate next steps but selects none.

---

## §11 — PR-A vs PR-B execution shape

**PR-A** (this PR):

- doc-only inspection-protocol design memo
- locks the inspection contract, outcome ladder, report schema, and
  enforcement contract
- merges only after explicit user approval
- contains no inspection, no hashes, no manifests, no scripts, no
  tests, no artifacts

**PR-B** (separately authorised after PR-A merge):

- implements the inspection per the PR-A locked spec
- strictly read-only local-data + pipeline inspection
- may read local files and source code
- may compute hashes (SHA-256 over existing local file bytes; SHA-256
  over source-text of identified functions) and write artifacts under
  the Gate P1 report namespace only
- may not fetch
- may not generate labels
- may not train models
- may not create a dataset epoch
- emits exactly one primary outcome from §9 plus any required
  retention substatus

**Justification for the split (recorded here):**

- PR #360 hard-HALT was caused by implementation running ahead of a
  locked contract; the two-PR split codifies the lock-contract-first
  discipline
- inspection requires new code (manifesting, hashing,
  schema-fingerprinting, common-coverage computation,
  dependency-classification, read-only retention-feasibility
  analysis) — none of this is ready-made tooling
- PR-A allows the contract to be reviewed in isolation from any
  implementation; PR-B can be deferred without losing the contract
  decision

---

## §12 — Gate P1 report artifact schema (binding for PR-B)

PR-B writes the following artifacts under
`artifacts/gate_p1_report/<report_id>/`:

| Artifact | Content |
|---|---|
| `gate_p1_report.json` | top-level outcome + retention substatus + per-candidate summary table + PR-A spec version reference + PR-B implementation code-hash |
| `raw_inventory_<candidate_id>.json` | per-candidate raw inventory (per-pair presence / size / SHA-256 / row counts / timestamps / monotonicity / duplicates / schema fingerprint / OHLC validity / gap profile / irregularity findings + aggregate common interval) |
| `dependency_inventory_<candidate_id>.json` | per-candidate dependency × consumer classification table (per §4) |
| `coverage_<candidate_id>.json` | candidate observation interval + per-pair contribution + scientific-adequacy flags (per §5) |
| `retention_feasibility_<candidate_id>.json` | per-candidate retention classification + size projections + visibility findings (per §6); contains NO probe results |
| `pipeline_feasibility.json` | code-path inspection results + source hashes + Gate P2 work list (per §7) |
| `report.md` | human-readable summary referencing all of the above |

**Schema-level bindings:**

- all artifacts are doc-only in nature (JSON / Markdown); no parquet,
  no labels, no row-level data
- each JSON artifact carries:
  - `schema_version` (a string declared in PR-B and committed)
  - `pr_a_spec_version` (the PR-A spec version this report was
    produced against)
  - `pr_b_code_hash` (SHA-256 of the producing PR-B implementation
    bytes)
- per-artifact size guard (PR-B may set its own conservative byte
  limit; the constant must be explicit in PR-B source)
- no credential value ever appears in any artifact field
- no probe attempted / probe-result field exists in any artifact
  (cross-reference §6 prohibition)

---

## §13 — Constraints honoured by PR-A

- doc-only (1 file added; no source / no tests / no artifacts)
- no inspection executed
- no raw local-data reads beyond what has already been reported in
  PR #360
- no hashes / manifests generated by this PR
- no data fetch
- no credentials handling (not even presence-check)
- no labels or signal generation
- no model execution
- no Stage 2 branch push or modification
- no A0-broad β resumption
- no prior verdict modification
- no production change
- no `MEMORY.md` edit inside this PR
- no auto-route to PR-B / Gate P2 / baseline / A0-broad

---

## §14 — References

- PR #355 — Phase 29.0b-α A0-broad design memo AMENDMENT
- PR #356 — Phase 27-29 Tabular Evaluation Validity Audit
  (`TARGETED_VERIFICATION_REQUIRED` preserved)
- PR #357 — V2-expanded design memo
- PR #358 — V2-expanded amendment (F-1 strict tolerance binding)
- PR #359 — V2-expanded Stage 1 infrastructure
- PR #360 — Tabular Evidence Epoch Rebase routing memo
  (`HALTED_INPUT_UNAVAILABLE` / `UNEXECUTABLE_INPUT_UNAVAILABLE`)
- PR #361 — New Provenance-bound Dataset Epoch Design memo
  (Route E2 PRIMARY `LOCAL_DATA_CANDIDATE_EPOCH_PENDING_FEASIBILITY`;
  Gate P1 + Gate P2 separation)
- base commit for this PR: `master @ 2b24695` (PR #361 merge)
