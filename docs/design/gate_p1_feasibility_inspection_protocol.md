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

**Amendment history:**

- **Amendment 1 (this revision):** corrects the protocol description to
  pin (a) the authoritative M1 BA raw schema to the existing
  `scripts/stage23_0a_build_outcome_dataset.py::load_m1_ba` reader
  contract (§3.1, no `volume` required), (b) the canonical PAIRS_20
  authority to `scripts/stage23_0a_build_outcome_dataset.py::PAIRS_20`
  with cross-confirmation against `scripts/stage22_0a_scalp_label_design.py::PAIRS_20`
  (new §3.2), (c) the default inspection mechanism as AST/source-text
  only with explicit prohibition of production-module imports
  (`importlib` / `__import__` / `exec` / `eval` / `compile` / `runpy`)
  in §4 and §7, (d) the development-slice parquet classification as
  the new `EXCLUDED_NONAUTHORITY_DEVELOPMENT_SLICE` class (separate
  from the four candidate-dependency classes; §4), (e) the in-repo
  retention size guard citation to
  `scripts/_verification_harness/tolerances.py::ARTIFACT_SIZE_GUARD_BYTES`
  (95 MB per-file ceiling only; no total in-repo budget exists; §6.1)
  and the first-PR-B-run restriction that `IN_REPO_*` and
  `EXISTING_LOCAL_*` retention statuses are not admissible (§6.2),
  (f) comprehensive primitive-coverage list for the no-side-effect
  guard plus the outer-launcher / inner-guard boundary (§8.1 / §8.2)
  and `.gitignore` non-modification (§8.3), (g) per-candidate
  evaluation and top-level aggregation precedence (§9.1 / §9.2). All
  prior section numbers are preserved; amendments are inlined under
  the relevant sections.

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

### §3.1 — Declared bid/ask OHLC schema (Amendment 1)

This section is amended to bind to the **actual authoritative reader
contract** already merged at master, not to an aspirational schema.

**Authoritative reader (cited):**
`scripts/stage23_0a_build_outcome_dataset.py::load_m1_ba` (already merged).

**Required M1 BA input fields per JSONL record (binding):**

| Field | Type / format |
|---|---|
| `time` | timestamp string; must parse as the authoritative OANDA/UTC timestamp representation accepted by the cited loader contract |
| `bid_o` | numeric, finite |
| `bid_h` | numeric, finite |
| `bid_l` | numeric, finite |
| `bid_c` | numeric, finite |
| `ask_o` | numeric, finite |
| `ask_h` | numeric, finite |
| `ask_l` | numeric, finite |
| `ask_c` | numeric, finite |

**Volume handling (binding):**

- `volume` is **not** a required authoritative field for Gate P1 M1 BA validity
- presence of additional non-required fields (e.g. `volume`) **may** be
  recorded as an informational `schema_extension_finding`
- presence of additional non-required fields **must not** by itself make
  an otherwise valid BA file invalid

**PR-B obligations under this amended schema:**

- PR-B must AST-extract the actual field set from the cited authority
  function source (no import of the production module)
- PR-B must compute and record the SHA-256 of the cited authority
  source file (the file containing `load_m1_ba`)
- PR-B HALTs if the implementation's `REQUIRED_FIELDS` disagrees with
  the amended protocol's field list above
- any deviation from the required field list in a JSONL record →
  per-pair field `schema_valid = false` and that pair cannot
  contribute to a `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW`
  outcome

**Scope of this amendment:**

- this amendment **corrects the protocol description** to match the
  already-existing authoritative reader
- it does **not** inspect any local raw data
- it does **not** select any candidate span
- the prior wording ("`bid_open, bid_high, … volume`") is superseded
  in full by the field list above

---

### §3.2 — PAIRS_20 authority resolution (Amendment 1)

This section is added to pin the previously under-specified pair-universe
authority.

**Canonical candidate pair-universe authority (binding):**

- `scripts/stage23_0a_build_outcome_dataset.py::PAIRS_20`

**Secondary cross-confirmation source (binding):**

- `scripts/stage22_0a_scalp_label_design.py::PAIRS_20`

**PR-B resolution rule (binding):**

- PR-B must inspect **both** sources by **AST/source-text only** (no
  import of either module)
- if the two literal pair lists are **identical** (element-by-element
  string equality), emit `pair_universe_hash` over the canonical sorted
  list and record both source SHAs in the Gate P1 report
- if the two literal pair lists **differ**:
  - PR-B must **not** silently select one
  - the candidate outcome is `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`
  - the reason is `PAIR_UNIVERSE_AUTHORITY_AMBIGUOUS`
- if the canonical authority source cannot be read or AST-parsed:
  - this is an **inspection-integrity HALT**
  - no Gate P1 report PASS / PARTIAL / INSUFFICIENT outcome is emitted
  - no PR-B evidence result is produced

**This amendment does not claim any source SHA.** PR-B will compute and
report source hashes after implementation authorisation.

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
| `DETERMINISTICALLY_DERIVABLE_FROM_ACCEPTED_RAW` | the dependency is reconstructable from accepted raw input via a committed, source-hashed derivation function (exact function path + source SHA-256 recorded; AST/source-only evidence per Amendment 1) |
| `MISSING` | no satisfactory raw input or derivation function is present |
| `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION` | code path exists but its applicability or output-emptiness cannot be assessed without running it |

**Separate classification (Amendment 1) — not one of the four
candidate-dependency classes:**

| Class | Meaning |
|---|---|
| `EXCLUDED_NONAUTHORITY_DEVELOPMENT_SLICE` | applied **only** to the existing development-slice labels parquet (`artifacts/stage25_0a/path_quality_dataset.parquet`). Recorded for documentation; not a candidate epoch input; **does not count as `MISSING`** for E2 feasibility |

**Bindings (Amendment 1 strengthens correction 3):**

- PR-B may inspect code paths by **AST / source-text reads + source-text
  SHA-256 only**; **no execution**; **no import of production pipeline
  modules**
- PR-B must not use `importlib.import_module`, `__import__`, `exec`,
  `eval`, `compile`, or `runpy` against production modules
- PR-B may not run signal generation or label generation
- PR-B may not claim that non-empty labels will be produced (that
  claim is Gate P2's alone, per PR #361 §4)
- PR-B may not silently infer that M5 / H1 / D1 are derivable from
  M1 BA without locating and source-hashing the exact derivation
  function and inspecting its required semantics through AST evidence;
  absent that evidence, the dependency is
  `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION` at best
- code-path existence claims and `DETERMINISTICALLY_DERIVABLE_FROM_ACCEPTED_RAW`
  classifications are admissible only when supported by **bounded
  AST/source evidence and recorded source hashes**; any dependency
  whose applicability cannot be established without executing code
  remains `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION`
- the existing development-slice labels parquet
  (`artifacts/stage25_0a/path_quality_dataset.parquet`, currently a
  3-pair / 1-day / 1,306-row stub) **is not a candidate epoch input**
  and is classified as `EXCLUDED_NONAUTHORITY_DEVELOPMENT_SLICE`
  (separate from the four candidate-dependency classes above); Gate P1
  may inspect only already-established exclusion metadata or later
  permitted metadata-only filesystem facts (`os.stat()` only)
- new labels generation remains
  `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION` because Gate P1
  cannot execute or validate labels generation
- the dev-slice exclusion **does not** count as a `MISSING` dependency
  for E2 feasibility
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

### §6.1 — In-repo retention size guard (Amendment 1)

This section is amended to cite the existing repository policy rather
than leaving the constant to PR-B implementation discretion.

**Cited per-file ceiling (binding):**

- `scripts/_verification_harness/tolerances.py::ARTIFACT_SIZE_GUARD_BYTES`
  = `95 * 1024 * 1024` bytes (95 MB)
- this constant is the authoritative per-file artifact-size ceiling for
  any artifact ever committed under the project's V2-expanded harness
  policy (merged in PR #359)
- PR-B may cite this constant **only as a per-file artifact-size
  ceiling**; it is not an aggregate retention budget

**Total in-repo retention budget (binding):**

- **no binding repository policy currently exists** at master `d718c6f`
  declaring a total in-repo aggregate retention budget for a future
  epoch's raw + labels + split + manifests
- consequently, PR-B may **not** declare in-repo total retention
  feasible in the first run; see §6.2 first-run restrictions

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
(general protocol; first-run restriction below):**

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

**First-PR-B-run restrictions (Amendment 1, binding for the first
PR-B execution):**

- per §6.1, no binding total in-repo retention budget exists at master
  `d718c6f`, **and** no local immutable archive path has been approved
  or identified
- therefore, in the first PR-B execution:
  - `IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2` is **not
    admissible** as an emitted retention result
  - `EXISTING_LOCAL_IMMUTABLE_ARCHIVE_VISIBLE_READ_ONLY` is **not
    admissible** as an emitted retention result
- the first-PR-B-run resolver is therefore restricted to emitting
  retention as one of:
  - `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`
  - `RETENTION_DESTINATION_UNRESOLVED`
- PR-B may **calculate and report**:
  - raw candidate byte totals
  - estimated labels / split / manifest byte requirements
  - per-file 95 MB ceiling references (citing
    `tolerances.py::ARTIFACT_SIZE_GUARD_BYTES`)
- this is **not** a failure of Gate P1; it means a later separately
  authorised retention decision is needed before any subsequent
  PR-B-style execution could pass

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

PR-B may inspect **source text and AST only** (Amendment 1
strengthens the prior "imports only" wording). It will write
`pipeline_feasibility.json` recording:

- which scripts / functions would generate signals
- which scripts / functions would generate labels
- which scripts / functions implement D-1 executable PnL
- which scripts / functions construct splits
- whether each path can be parameterised to write into a **new epoch
  namespace** (e.g. `artifacts/epoch-<manifest_id_preview>/…`)
  without overwriting historic / current local artifacts (detected by
  AST inspection only)
- the SHA-256 of the source text of each identified function
- the enumerated work list of code changes required for Gate P2
  (design-level, not execution)

**Inspection mode (binding; Amendment 1):**

- **AST + source-text reads + source-text SHA-256 only**
- no `import` of production pipeline modules
- no `importlib.import_module`, `__import__`, `exec`, `eval`,
  `compile`, or `runpy` against production code
- no `__main__` execution of any pipeline module
- no invocation of any pipeline function
- function-signature + docstring inspection is performed by AST
  traversal, not by importing the function
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

- only Gate P1 report artifacts may be written, and only under
  `artifacts/gate_p1_report/<report_id>/`
- any attempt to write outside that prefix HALTs

**Categories of prohibition (overview; see §8.1 for comprehensive
primitive coverage, §8.2 for the outer-launcher / inner-guard
boundary, §8.3 for `.gitignore` non-modification):**

- file-write, network, subprocess, credentials, and bytecode-writing
  primitives are blocked per §8.1
- the inner guarded process must not invoke `git` or any other
  subprocess (§8.1); code-commit provenance is captured by the
  narrow outer launcher per §8.2
- no credential value ever appears in any Gate P1 report artifact
  (per §12 artifact-schema binding; consistent with §8.1 credential-
  read block)
- no access to, push of, fetch of, checkout of, or modification of
  the Stage 2 implementation branch
  (`research/tabular-targeted-verification-v2-expanded-stage2-preflight`
  @ local `0234ed3`)
- retention-probe prohibitions (no test-object write / read / delete
  against any destination; no external storage access; no
  credential-based destination verification) — see §6 for the
  authoritative retention-feasibility contract

### §8.1 — Comprehensive primitive coverage (Amendment 1)

The earlier `open`-and-`socket`-only patch list is insufficient. The
write-allow-list guard, network guard, credentials guard, subprocess
guard, and bytecode guard together must, at minimum, cover the
following primitives. Violation outside the report-namespace
allow-list (`artifacts/gate_p1_report/<report_id>/`, `.json` / `.md`
only) is an **inspection-integrity HALT** and prevents PR-B from being
opened.

**Bytecode (Amendment 1, binding):**

- the inner guarded inspection process runs with **bytecode writing
  disabled** (`python -B`; guard asserts `sys.dont_write_bytecode is
  True`)
- no `__pycache__` is written anywhere during the inspection run

**File-write primitives blocked outside the report-namespace
allow-list:**

- `builtins.open` (write modes)
- `io.open` (write modes)
- `os.open` (with any write/create/truncate flag combination)
- `pathlib.Path.write_text`
- `pathlib.Path.write_bytes`
- `pathlib.Path.touch`
- `pathlib.Path.mkdir` (only the report directory itself may be
  created by the outer launcher; no other mkdir from the inner
  process)
- `os.rename`
- `os.replace`
- `os.remove` / `os.unlink` (denied entirely — no deletion is required
  or permitted during Gate P1)
- `os.rmdir` (denied entirely)
- `shutil.copy` / `copy2` / `copyfile` / `copytree`
- `shutil.move`
- `shutil.rmtree`
- `tempfile.NamedTemporaryFile` / `TemporaryFile` / `SpooledTemporaryFile`
- `tempfile.mkstemp` / `mkdtemp`

**Extension allow-list** (additional to path allow-list):

- only `.json` and `.md` writes succeed even inside the
  report-namespace directory
- attempts to write `.parquet` / `.csv` / `.pkl` / arbitrary binary
  blobs HALT

**Network primitives blocked (no allow-list — all banned):**

- `socket.socket` (constructor)
- `socket.create_connection`
- `urllib.request.urlopen`
- `http.client.HTTPConnection`
- `http.client.HTTPSConnection`
- `ssl.wrap_socket` / `ssl.SSLContext.wrap_socket`
- any `requests.*` invocation (sentinel raises on attribute access)

**Subprocess primitives blocked (no allow-list — all banned inside
the guarded inner process):**

- `subprocess.run` / `Popen` / `call` / `check_output` / `check_call`
- `os.system`
- `os.popen`
- `os.spawn*` family
- `multiprocessing.Process` start

**Credential reads blocked (no opt-out in the first PR-B run):**

- `os.environ.get/__getitem__/__contains__` for any key matching
  `r"(?i)(OANDA|TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL|AWS|GCP|AZURE).*"`
  — read of value **and** presence-check (`in`) both HALT

**Stage 2 branch prohibitions:**

- the inner guarded process must not invoke `git`, `subprocess`, or
  any tool that could shell out; this also covers any indirect
  access to the Stage 2 implementation branch (cross-reference §8
  overview)

### §8.2 — Outer launcher vs guarded inner process boundary (Amendment 1)

Because the inner guarded process cannot invoke `git`, code-commit
provenance is captured by a **narrow outer launcher**. The boundary
is binding.

**Outer launcher (binding):**

- implemented as a **single auditable Python launcher module** (not
  separate shell and PowerShell scripts; cross-platform Python only)
- runs **before** any inner-process guard is installed (separate
  process)
- may perform **only** the following operations:
  - obtain the clean code commit SHA (`git rev-parse HEAD`)
  - verify clean tracked worktree (`git status --porcelain` empty)
  - create the **one** Gate P1 report directory
    (`artifacts/gate_p1_report/<report_id>/`)
  - write `execution_envelope.json` inside that report directory
  - start the guarded inner process with `python -B`
  - after inner completion, verify code SHA unchanged and no
    unexpected tracked / untracked changes outside the report
    directory
- must contain its own **path restriction** allowing writes only to:
  - `artifacts/gate_p1_report/<report_id>/execution_envelope.json`
  - and creation of its containing report directory
- must **not** read local candidate raw files
- must **not** compute raw-data hashes
- must **not** use network
- must **not** access credentials
- must **not** modify any existing file
- must **not** delete anything

**Inner guarded inspection process (binding):**

- must install all runtime guards (§8 + §8.1) **before** importing
  any inspector submodule
- must run with bytecode writing disabled (`python -B`)
- must prohibit all subprocess / git / network / credential access
- must restrict all writes to `.json` and `.md` files inside the
  pre-created report-namespace directory

**Required PR-B tests** (to be implemented in PR-B; recorded here
under Amendment 1 so the implementation is constrained):

- outer launcher cannot write outside its envelope / report-directory
  allowance
- outer launcher cannot read candidate raw input or
  network / credential sources
- inner process imports only minimal bootstrap / guards before guard
  installation
- post-run audit accepts only new files beneath the one report
  directory

### §8.3 — `.gitignore` non-modification (Amendment 1)

PR-B **must not modify `.gitignore`**. If Gate P1 report artifacts
cannot be committed under existing repository policy, PR-B must
**stop and request approval** rather than changing ignore rules.

At master `d718c6f`, the `.gitignore` file uses per-stage entries
under `artifacts/`; there is no blanket `artifacts/` ignore. The
Gate P1 report namespace `artifacts/gate_p1_report/` is therefore
trackable by default and no `.gitignore` change is anticipated.

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

### §9.1 — Per-candidate evaluation (Amendment 1)

Per candidate, the outcome is assigned as follows:

- **all sufficient + retention `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`:**
  - candidate status = `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`
  - substatus = `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`
  - "all sufficient" = raw inventory + pair/schema authority +
    dependency inventory + pipeline feasibility all pass
- **all sufficient + retention `RETENTION_DESTINATION_UNRESOLVED`:**
  - candidate status = `RETENTION_DESTINATION_UNRESOLVED`
- **pair-universe or schema authority is ambiguous:**
  - candidate status = `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`
  - reason recorded explicitly as one of:
    - `PAIR_UNIVERSE_AUTHORITY_AMBIGUOUS`
    - `SCHEMA_AUTHORITY_AMBIGUOUS`
- **raw or required dependency / pipeline feasibility is insufficient:**
  - candidate status = `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH`

### §9.2 — Top-level aggregation across candidate spans (Amendment 1)

Top-level outcome is selected by the following precedence:

1. **if any candidate would be
   `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW`**, emit that
   outcome
   - this outcome remains part of the general protocol but, per
     §6.2 first-PR-B-run restrictions, is **unreachable** in the
     first PR-B execution because the retention-ready statuses
     (`IN_REPO_*` / `EXISTING_LOCAL_*`) are not admissible there
2. **else if any candidate is
   `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`**, emit
   `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` and list **all**
   contributing candidates and their per-candidate reasons (substatus
   or ambiguity reason) in the Gate P1 report
3. **else if one or more candidates satisfy raw / dependency /
   pipeline sufficiency but all are blocked solely by unresolved
   retention**, emit `RETENTION_DESTINATION_UNRESOLVED`
4. **else** emit `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH`

PR-B must not implement unreachable or contradictory branches of the
resolver. The resolver source must be statically verifiable against
this precedence.

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
