# Gate P1 PR-B Implementation Plan — read-only inspection execution

**Status:** Doc-only implementation plan for Gate P1 PR-B (read-only
inspection execution). Authored under PR-A protocol contract
(`docs/design/gate_p1_feasibility_inspection_protocol.md`,
PR #362 + Amendment 1 from PR #363), at `master @ ba80121`.

**Base:** master `ba80121` (post PR #364 OANDA archive provenance merge)
**Branch:** `docs/gate-p1-pr-b-implementation-plan`
**File added:** `docs/design/gate_p1_pr_b_implementation_plan.md`

**Amendment history:** (none — this is the initial draft of the PR-B
implementation plan.)

This document is the **implementation plan** for Gate P1 PR-B. It is
**not the implementation itself** and **contains no code**. PR-A
(protocol) locked the specification of what PR-B must do and must not
do. This document locks **how that specification is to be partitioned
into modules, responsibilities, report artifacts, tests, and stage
splits**, prior to authoring any PR-B code. Per protocol §11 (PR-A vs
PR-B execution shape), the boundary is preserved: PR-A locked the
contract; this PR locks the implementation plan; subsequent PR-B.0 /
PR-B.1 / PR-B.2 (proposed §11) implement against this plan.

---

## §1 Purpose / Scope / Non-scope

### Purpose

To translate the Gate P1 PR-A protocol contract (protocol §0..§14,
including Amendment 1) into a locked, reviewer-tractable implementation
plan, so that PR-B authoring proceeds with no remaining contract
ambiguity. The plan binds module names, file layout, ordering of guard
installation, per-item responsibility for inspection submodules, report
artifact schema, outcome aggregation decision tree, candidate span scope,
test strategy, and stage split. Implementation itself is deferred to
subsequent PRs (proposed §11).

### Scope

The following items are decided in this PR (binding once merged):

- outer launcher / inner inspector partitioning (§3..§5)
- submodule responsibility assignment for each protocol §3..§7 item
  (§6)
- report artifact schema at field level (§7)
- outcome aggregation decision tree (§8)
- candidate span inspection scope and order (§9)
- test strategy (§10)
- stage split proposal (§11)
- risk register (§12)
- open questions to be resolved before PR-B implementation authoring
  (§13)

### Non-scope

The following items are explicitly out of scope for this PR:

- no executable code added to the repo
- no inspection executed (no PR-B run, even on fixture data)
- no SHA-256 computed against any candidate raw file
- no read of any byte under `data/` (candidate raw bytes remain
  untouched)
- no modification of `.gitignore` (re-declares Amendment 1 §8.3)
- no retention probe of any kind (no write / read / delete to any
  destination); re-declares protocol §1.B and Amendment 1 §6.1
- no automatic acquisition of PR-B implementation authorisation. PR-B.0
  / PR-B.1 / PR-B.2 (§11) each require **independent** explicit user
  authorisation after this plan PR merges. Re-declares protocol §11.
- no claim that the OANDA 2026-05-31 archive (`artifacts/
  oanda_archive_2026-05-31/`, PR #364) is admissible as either a
  retention destination or as binding evidence for an epoch identity.
  Its status as a candidate raw input remains to be determined inside
  PR-B inspection itself.

### First-PR-B-run binding (re-declared)

Per protocol §6.2 (Amendment 1), the first execution of PR-B
**cannot emit** `IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2` or
`EXISTING_LOCAL_IMMUTABLE_ARCHIVE_VISIBLE_READ_ONLY` as retention
classifications. By precedence in §9.2, this means PR-B's first run
**cannot reach** the top-level outcome
`LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW`. This invariant
is enforced **structurally** by:

- the resolver carrying a `first_run_mode: bool` parameter, hard-set to
  `True` for the first PR-B execution (§8)
- the writer for `retention_feasibility_<candidate_id>.json` forcing
  the two restricted classifications to `false` (§7)
- the resolver `FEASIBLE_FOR_CONSTRUCTION_REVIEW` branch raising an
  inspection-integrity HALT when reached under `first_run_mode=True`
  (§8)

This invariant constrains §6 (no submodule decides a final outcome),
§7 (writer enums reject restricted classifications), §8 (decision tree
branches are reachable only under specific modes), and §10 (negative
tests verify HALT on first-run reach).

---

## §2 Reference contract resolution map

The table below maps every protocol section and amendment binding to
the implementation module that owns it, and to the inspection mode the
module is restricted to. This is the canonical lookup used by reviewers
to verify, for each protocol clause, that exactly one module is
responsible and that no module operates outside its assigned mode.

| Protocol § | Amendment 1 binding | Implementation owner | Inspection mode |
|---|---|---|---|
| §3 raw inventory | — | `inspector.raw_inventory` | streaming file read + JSONL parse |
| §3.1 M1 BA schema authority | bound to `scripts/stage23_0a_build_outcome_dataset.py::load_m1_ba`; `REQUIRED_FIELDS` extracted via AST; HALT on drift vs protocol §3.1 list | `authority.schema` | AST + source-text SHA-256 |
| §3.2 PAIRS_20 authority | canonical `stage23_0a::PAIRS_20`; secondary cross-confirm `stage22_0a::PAIRS_20`; AST/source-text only; ambiguity → PARTIAL; parse-fail → HALT | `authority.pair_universe` | AST + source-text SHA-256 |
| §4 dependency inventory | AST/source-only; `EXCLUDED_NONAUTHORITY_DEVELOPMENT_SLICE` reserved for `artifacts/stage25_0a/path_quality_dataset.parquet` only and does NOT count as MISSING for E2 | `inspector.dependency_inventory` | AST + source-text SHA-256 |
| §5 common observation interval | derived from §3 outputs; `[max_i obs_start_i, min_i obs_end_i]`; if any pair missing → interval is `null` | `inspector.coverage` | derivation only (no I/O of its own) |
| §6.1 per-file retention guard | cites `scripts/_verification_harness/tolerances.py::ARTIFACT_SIZE_GUARD_BYTES` (per-file 95 MB ceiling, **not** an aggregate budget) | `inspector.retention` | `os.stat` only (size metadata) |
| §6.2 first-PR-B-run retention restriction | `IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2` and `EXISTING_LOCAL_IMMUTABLE_ARCHIVE_VISIBLE_READ_ONLY` inadmissible in first run; only `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE` or `RETENTION_DESTINATION_UNRESOLVED` permitted | `inspector.retention` + `inspector.resolver` (first-run mode flag) | enum gating in writer |
| §7 pipeline feasibility | AST + source-text + source-text SHA-256 only; no `importlib.import_module`, `__import__`, `exec`, `eval`, `compile`, `runpy` against production | `inspector.pipeline_feasibility` | AST + source-text SHA-256 |
| §8 / §8.1 primitive guards | comprehensive primitive list (filesystem write / network / subprocess / credentials); bytecode disabled (`python -B` + `sys.dont_write_bytecode`) | `_gate_p1_inspector.guards.*` | runtime monkey-patch (own process only) |
| §8.2 outer-launcher / inner-guard boundary | single auditable Python launcher (not shell/PowerShell); outer minimal, inner installs guards then imports inspector submodules | `gate_p1_pr_b_launcher.py` (outer) + `_gate_p1_inspector.bootstrap` (inner) | outer: git + envelope; inner: guarded |
| §8.3 `.gitignore` non-modification | binding | every module (write-allowlist enforces it naturally) | n/a |
| §9.1 per-candidate outcome aggregation | order-fixed decision tree; all-sufficient + retention probe-required → PARTIAL + substatus; all-sufficient + retention unresolved → UNRESOLVED; authority ambiguous → PARTIAL with reason; insufficient → INSUFFICIENT | `inspector.resolver.resolve_candidate` | pure function |
| §9.2 top-level outcome precedence | PASS > PARTIAL > UNRESOLVED > INSUFFICIENT; PASS unreachable in first PR-B run | `inspector.resolver.resolve_top_level` | pure function |
| §12 report schema | `schema_version` / `pr_a_spec_version` / `pr_b_code_hash` mandatory in every JSON artifact; `.json` / `.md` only; report dir confined to `artifacts/gate_p1_report/<report_id>/` | `report.schema`, `report.writers`, `report.common_metadata` | JSON / Markdown emit through guard-allowed paths |
| §13 PR-A constraints honoured | binding | (this plan PR) | doc-only |

Each row above declares **one** owner. A reviewer who wants to verify
that a given protocol clause is implemented can use this table as a
unique index into the PR-B source tree.

---

## §3 Implementation topology

The proposed source layout mirrors the existing
`scripts/_verification_harness/` package (8 modules, introduced in
PR #359), preserving thematic consistency. PR-B's inspector lives in a
sibling `scripts/_gate_p1_inspector/` package and a single outer
launcher `scripts/gate_p1_pr_b_launcher.py`.

```
scripts/
  gate_p1_pr_b_launcher.py            # outer launcher (single Python file)
  _gate_p1_inspector/                 # inner inspector package
    __init__.py                       # MUST be empty of side-effects
    bootstrap.py                      # guard installer + entrypoint (-m target)
    guards/
      __init__.py
      filesystem.py                   # write-allowlist (§8.1 file primitives)
      network.py                      # network block (§8.1 network primitives)
      subprocess.py                   # subprocess block (§8.1 subprocess primitives)
      credentials.py                  # env-var block (§8.1 credential regex)
      bytecode.py                     # sys.dont_write_bytecode assertion
    authority/
      pair_universe.py                # §3.2
      schema.py                       # §3.1
    inspector/
      raw_inventory.py                # §3
      dependency_inventory.py         # §4
      coverage.py                     # §5
      retention.py                    # §6
      pipeline_feasibility.py         # §7
      resolver.py                     # §9.1 / §9.2
    report/
      schema.py                       # field definitions for §12 artifacts
      writers.py                      # JSON / MD emit (write-allowlist enforced)
      common_metadata.py              # schema_version / pr_a_spec_version / pr_b_code_hash
    tolerances.py                     # PR-B-local constants (mirror of harness values w/ source citation)
tests/
  gate_p1_pr_b/                       # PR-B tests
    test_outer_launcher_*.py
    test_guards_*.py
    test_authority_*.py
    test_inspector_*.py
    test_resolver_*.py
    test_report_schema_*.py
    fixtures/
      tiny_jsonl/                     # hand-authored synthetic JSONL (small)
      stub_source_modules/            # synthetic Python source for AST tests
```

### Library binding

PR-B implementation modules use **only the Python standard library**:

- `ast`, `pathlib`, `hashlib`, `json`, `os`, `sys`, `re`, `io`,
  `dataclasses`, `datetime`, `enum`, `typing`, `argparse`, `subprocess`
  (outer only, one invocation), `socket` (for guard wrapping),
  `urllib.request` / `http.client` (for guard wrapping), `multiprocessing`
  (for guard wrapping), `tempfile` (for guard wrapping), `shutil`
  (for guard wrapping).

PR-B implementation **does not depend on** `pandas`, `numpy`,
`pyarrow`, `requests`, `pyyaml`, `jsonschema`, or any other third-party
package. JSONL is parsed by streaming `json.loads` over an `open(...)`
loop; numeric finiteness is checked with `math.isfinite`.

### Inspector package import discipline

The inspector `__init__.py` is empty of side-effects (no imports, no
module-level statements). All imports of inspector submodules occur in
`bootstrap.py` **after** guards are installed. This pattern is enforced
by a `bootstrap.py` assertion that captures `sys.modules` before guard
installation and verifies that no `scripts._gate_p1_inspector.inspector.*`
module is present (open question §13.Q1 covers whether `tolerances`
constants may be imported pre-guard).

---

## §4 Outer launcher specification

The outer launcher (`scripts/gate_p1_pr_b_launcher.py`) is a single
Python file that executes the following **order-fixed 10 steps**.
Re-orderings, additions, or omissions are forbidden by this plan.

1. **arg parse** — `argparse` defines required flag `--report-id <id>`
   (string, ASCII letters/digits/`-`/`_` only, length 1..64). If
   omitted, an ISO-8601-derived value is synthesised by outer (binding:
   synthesis happens only in outer). A `--first-run` flag is required
   for the first PR-B execution and is propagated to inner.
2. **clean code SHA capture** — `subprocess.run(["git", "rev-parse",
   "HEAD"], check=True, capture_output=True)`. This is the **single
   subprocess invocation** in outer for git inspection.
3. **clean tracked worktree check** — `subprocess.run(["git", "status",
   "--porcelain"], check=True, capture_output=True)`. The output is
   asserted to be empty when restricted to tracked paths. (Untracked
   paths are tolerated only outside `artifacts/gate_p1_report/`.)
4. **report directory creation** — `Path("artifacts/gate_p1_report/")
   .joinpath(report_id).mkdir(parents=True, exist_ok=False)`. Existing
   collision → HALT with `outer_failure.json` emitted to the parent
   directory if creation succeeded, otherwise to stderr only.
5. **outer write-allowlist self-restriction** — outer establishes its
   own write-allowlist (absolute path set) containing exactly
   `<report_dir>/execution_envelope.json` and `<report_dir>/
   outer_failure.json`. All other writes from outer are explicitly
   prohibited and detected via wrapper calls.
6. **execution_envelope.json write** — fields:
   - `report_id`
   - `outer_launch_ts_utc` (ISO-8601 with `Z` suffix)
   - `clean_code_sha`
   - `python_version` (`sys.version_info` triplet + full string)
   - `platform` (`sys.platform`, `os.name`, `platform.platform()`)
   - `pr_a_spec_version` (object: `{path, sha256, amendment: "amendment_1"}`)
   - `pr_b_code_hash` (string, see §7 definition)
   - `first_run_mode` (bool, from `--first-run` flag)
7. **inner process start** — `subprocess.run([sys.executable, "-B",
   "-m", "scripts._gate_p1_inspector.bootstrap", "--report-dir",
   str(report_dir), "--envelope", str(envelope_path)], check=False,
   capture_output=True, env=<scrubbed>)`. The `env` argument is built
   from a single allowed set (default: empty dict + minimum required
   like `PATH`, `SYSTEMROOT` on Windows) — credential-pattern keys per
   §5 credentials guard are not present in inner's env.
8. **inner exit code capture** — outer records inner's stdout / stderr
   tail (first/last N lines, no full capture) into a sibling
   `inner_invocation.json` only if inner failed to write its own
   report. (When inner succeeds in writing `gate_p1_report.json`,
   outer does **not** emit a sibling — inner's report is canonical.)
9. **post-run audit** — outer re-runs `git status --porcelain` and
   `git rev-parse HEAD`. Any change to `HEAD` since step 2 → HALT.
   Any tracked or untracked diff outside `<report_dir>/` → HALT. The
   audit result is appended to `execution_envelope.json` under
   `post_run_audit: {head_unchanged: bool, diff_confined_to_report_dir:
   bool, audit_ts_utc}`.
10. **outer exit** — exit code:
    - `0` if inner emitted a valid `gate_p1_report.json` and audit
      passed
    - `1` if outer pre-flight failed (steps 1..6)
    - `2` if inner crashed
    - `3` if audit failed
    - `4` if outer's own write-allowlist was violated (self-audit)

### Outer bindings

- outer does **not** read any byte under `data/`, `artifacts/` (except
  the report dir it creates), or any production module path
- outer does **not** compute file SHA-256 (this is inner's
  responsibility; outer captures only the git commit SHA)
- outer uses `subprocess` exactly **three times**: `git rev-parse HEAD`
  (step 2), `git status --porcelain` (step 3 and step 9), inner spawn
  (step 7). All other subprocess calls from outer are prohibited and
  the guard-pattern wrapper detects them
- outer does **not** read or write `.gitignore`
- outer does **not** access env vars matching the credential regex
  (`(?i)(OANDA|TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL|AWS|GCP|AZURE).*`)
- outer enforces its own write-allowlist via a small wrapper around
  `builtins.open`, `Path.write_text`, `Path.write_bytes` (same
  monkey-patch pattern as inner, but with a 2-path allowlist)

### Outer self-audit

The post-run audit (step 9) is the **outer's own safety net**. It
verifies outer did not deviate from its plan. A unit test (§10) asserts
that outer artificially modifying a file outside the report dir is
detected by audit.

---

## §5 Inner guard specification

Inner (`scripts/_gate_p1_inspector/bootstrap.py`) installs guards in a
**fixed order** before importing any inspector submodule. Order
violations or omissions are forbidden by this plan.

### Install order

1. **bytecode guard** — `assert sys.dont_write_bytecode is True`
   (outer invoked `python -B`; this assertion verifies the invariant
   survived). HALT with `guard_violation.json` if false.
2. **credentials guard** — wrap `os.environ.get`,
   `os.environ.__getitem__`, `os.environ.__contains__` with a sentinel
   that consults regex
   `(?i)(OANDA|TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL|AWS|GCP|AZURE).*`
   over the lookup key. Match → HALT (no return value, including for
   `__contains__` — presence-check itself is blocked, per Amendment 1
   §3 corrected scope).
3. **network guard** — replace `socket.socket`,
   `socket.create_connection`, `urllib.request.urlopen`,
   `http.client.HTTPConnection`, `http.client.HTTPSConnection`,
   `ssl.SSLContext.wrap_socket`, and any importable `requests.*`
   attribute access with sentinels that HALT on invocation.
4. **subprocess guard** — replace `subprocess.run`, `subprocess.Popen`,
   `subprocess.call`, `subprocess.check_output`, `subprocess.check_call`,
   `os.system`, `os.popen`, every `os.spawn*` variant, and
   `multiprocessing.Process.start` with sentinels that HALT on
   invocation.
5. **filesystem guard** — install a write-allowlist:
   - **allow path**: `<report_dir>/` (resolved absolute path)
   - **allow extension**: `{.json, .md}` only
   - **wrapped primitives** (full list per Amendment 1 §8.1):
     - `builtins.open` write modes (`w`, `wb`, `a`, `ab`, `x`, `xb`,
       `r+`, `w+`, `a+`, etc.)
     - `io.open` write modes
     - `os.open` with `O_WRONLY` / `O_RDWR` / `O_CREAT` / `O_TRUNC` /
       `O_APPEND` flags
     - `pathlib.Path.write_text`, `pathlib.Path.write_bytes`,
       `pathlib.Path.touch`, `pathlib.Path.mkdir`
     - `os.rename`, `os.replace`, `os.remove`, `os.unlink`, `os.rmdir`
     - `shutil.copy`, `shutil.copy2`, `shutil.copyfile`,
       `shutil.copytree`, `shutil.move`, `shutil.rmtree`
     - `tempfile.NamedTemporaryFile`, `tempfile.TemporaryFile`,
       `tempfile.SpooledTemporaryFile`, `tempfile.mkstemp`,
       `tempfile.mkdtemp`

### Namespace allowlist (import gating)

A `sys.meta_path` finder is installed at the top of bootstrap (before
guards) that rejects imports of:

- `scripts.stage*` (production pipeline modules)
- `scripts.fetch_oanda_archive`, `scripts.fetch_oanda_candles`
- any `src.*` / `fx_ai_trading.*` production module

Permitted imports:

- Python standard library
- `scripts._gate_p1_inspector.*` (the inner package itself)

`scripts._verification_harness.tolerances` is **not** imported; its
value is mirrored in `_gate_p1_inspector/tolerances.py` with a
`source_of_truth_citation` comment (per open question §13.Q1).

### Inspector import discipline

After all five guards install successfully, `bootstrap.py` imports
inspector submodules in this order:

1. `_gate_p1_inspector.authority.pair_universe`
2. `_gate_p1_inspector.authority.schema`
3. `_gate_p1_inspector.inspector.raw_inventory`
4. `_gate_p1_inspector.inspector.coverage`
5. `_gate_p1_inspector.inspector.dependency_inventory`
6. `_gate_p1_inspector.inspector.pipeline_feasibility`
7. `_gate_p1_inspector.inspector.retention`
8. `_gate_p1_inspector.inspector.resolver`
9. `_gate_p1_inspector.report.common_metadata`
10. `_gate_p1_inspector.report.schema`
11. `_gate_p1_inspector.report.writers`

Each submodule's top-level must be import-side-effect-free (no
file I/O, no network access, no production-module references). A unit
test verifies this property by importing each module under a stricter
guard set that fails the test on any I/O attempt during import.

### Guard scope justification (AST/source-only mandate)

The guards monkey-patch **the inner process's own runtime**, not any
production module's source. The protocol §4 + Amendment 1 AST/source-only
mandate restricts how PR-B inspects production code; it does not
restrict how PR-B disciplines its own process. The guards exist
precisely to enforce that PR-B's inspection of production code remains
AST/source-only.

### HALT semantics

Any guard sentinel invocation triggers an inspection-integrity HALT:

- write `guard_violation.json` to the report dir
- do **not** write `gate_p1_report.json`
- inner exits with non-zero code
- outer captures this in audit (§4 step 8/9) and exits with code `2`

A `guard_violation.json` is the canonical signal that PR-B was
implemented or invoked incorrectly. It is **never** a permitted
inspection outcome.

---

## §6 Inspector submodule responsibility assignment

Each protocol §3..§7 item has exactly one owner submodule. The owner
performs only data collection; the **resolver** (§8) decides outcomes.
This separation prevents any one submodule from concluding a top-level
verdict.

### Filename pattern recognition

- **Owner**: `inspector.raw_inventory`
- **I/O**: `pathlib.Path("data").glob("candles_*_M1_*_BA.jsonl")`
- **Logic**: regex `^candles_(?P<pair>[A-Z]{3}_[A-Z]{3})_M1_
  (?P<span>\d+d)_BA\.jsonl$` against filename
- **Non-candidate files**: discovered but non-matching files (e.g.,
  `candles_*_M5_*_BA.jsonl`, `candles_*_S5_*_M.jsonl`) are listed in
  `raw_inventory_<candidate_id>.json` under
  `discovered_non_candidate_files` as informational record only; they
  do not enter any candidate's inspection

### PAIRS_20 authority resolution + `pair_universe_hash`

- **Owner**: `authority.pair_universe`
- **I/O**: `ast.parse(<source_text>)` on
  `scripts/stage23_0a_build_outcome_dataset.py` and
  `scripts/stage22_0a_scalp_label_design.py`
- **Logic**: locate `Assign(targets=[Name(id="PAIRS_20")], value=List(elts=[Constant(value=<str>), ...]))` at module top level
- **Hash**: `pair_universe_hash =
  sha256(json.dumps(sorted(pairs), separators=(",", ":")).encode()).hexdigest()`
- **Cross-confirm**: element-by-element string equality between the
  two sources
- **Outcomes** (passed to resolver, not decided here):
  - both parse & lists equal → `OK`
  - both parse & lists differ → `AMBIGUOUS`
  - canonical fails to parse → `INTEGRITY_HALT_CANONICAL_UNPARSEABLE`
  - secondary fails to parse but canonical OK → `OK_SECONDARY_UNAVAILABLE`
- Each source's path and content SHA-256 are recorded for report

### Schema authority resolution

- **Owner**: `authority.schema`
- **I/O**: `ast.parse(<source_text>)` on
  `scripts/stage23_0a_build_outcome_dataset.py`
- **Logic**: locate function `load_m1_ba`, extract its `REQUIRED_FIELDS`
  declaration (module-level constant or in-function set literal — exact
  AST shape determined at implementation time per source inspection)
- **Verification**: extracted set must equal protocol §3.1 list:
  `{"time", "bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h",
  "ask_l", "ask_c"}`. Mismatch → `INTEGRITY_HALT_SCHEMA_AUTHORITY_DRIFT`.
- `volume` is recorded as `informational_extension` if found; its
  presence or absence is not a HALT condition (Amendment 1 §3.1
  binding)

### Presence / size / SHA-256 / row count

- **Owner**: `inspector.raw_inventory`
- **I/O**: `Path.exists()`, `Path.stat().st_size`, streaming
  `hashlib.sha256` over 8 MB blocks, single-pass row count
- **Pass coupling**: hash and row count computed in the **same pass**
  over the file to halve I/O. The row counter increments only after the
  hasher consumes the block.
- **Output fields**: `present`, `size_bytes`, `file_sha256`,
  `row_count`

### UTC timestamp min/max / monotonicity / duplicates

- **Owner**: `inspector.raw_inventory`
- **I/O**: streaming `json.loads` per line, `time` field extracted, ISO-
  parsed to UTC `datetime` (re-using the same parser pattern as
  `scripts/fetch_oanda_candles.py::_parse_oanda_time` but with **no
  import** — re-implemented locally to honour the AST/source-only
  mandate)
- **Counters**: `monotonicity_violations` (count of `t_i <= t_{i-1}`
  positions, not the positions themselves), `duplicate_timestamps`
  (count of exact UTC-string duplicates)
- **No correction**: rows are not sorted, deduplicated, or normalised
  in any way. Protocol §3 binding: monotonicity / duplicate findings
  are recorded as-is.

### Schema fingerprint / bid-ask OHLC validity

- **Owner**: `inspector.raw_inventory` (consumes
  `authority.schema.REQUIRED_FIELDS`)
- **Logic**: per row, verify `set(record.keys()) >= REQUIRED_FIELDS`;
  per numeric field, verify `isinstance(value, (int, float))` and
  `math.isfinite(float(value))`
- **Counters**: `missing_fields_count`, `non_finite_fields_count`
- **Extension detection**: extra keys (e.g., `volume`) recorded in
  `schema_extension_findings` as `{field_name, occurrence_count}` —
  informational, never a HALT

### Gap profile

- **Owner**: `inspector.raw_inventory`
- **Logic**: consecutive timestamp delta histogram (binned at
  `[1m, 2m, 5m, 10m, 1h, 6h, 1d, 7d, >7d]` for M1; expectation: 1m
  modal + weekend 2.5d cluster + occasional holiday gaps)
- **Output fields**: `gap_profile.histogram[]`, `gap_profile.max_gap_seconds`
- **Interpretation deferred**: this submodule does not classify gaps
  as anomalous; the resolver may consult thresholds (§8)

### Common observation interval (per candidate)

- **Owner**: `inspector.coverage`
- **I/O**: none of its own; consumes per-file `(ts_min_utc, ts_max_utc)`
  from `raw_inventory`
- **Logic**: `obs_start = max_i(ts_min_utc_i)`,
  `obs_end = min_i(ts_max_utc_i)`. If `obs_end < obs_start`, interval is
  `null` (degenerate); otherwise compute `span_days_effective =
  (obs_end - obs_start).total_seconds() / 86400`.
- **Missing pair handling**: if any one of the 20 pairs is absent or
  has zero rows, `obs_start` / `obs_end` are `null` and
  `span_days_effective` is `null`. Per protocol §3 binding, missing is
  not "never fetched" — its absence is recorded explicitly in
  `raw_inventory_<candidate_id>.json`.

### Dependency inventory (§4)

- **Owner**: `inspector.dependency_inventory`
- **Consumer list** (from protocol §4): signal generators, ATR
  computation, R7-A static context, D-1 PnL, labels generators, split
  builders, S-B, S-E, A0-broad temporal cells, A0-broad static R7-A.
  The exact module path for each consumer is enumerated as a
  `CONSUMER_REGISTRY` constant in this module, frozen at PR-B
  implementation time and not changed without amendment.
- **I/O**: `ast.parse(<source_text>)` on each consumer module;
  traversal extracts `Import`, `ImportFrom`, and `Call(Attribute(...))`
  / `Call(Name(...))` chains to derive each consumer's required inputs.
- **Class assignment** (per (consumer, dependency) cell):
  - `AVAILABLE_AS_RETAINED_RAW_LOCAL_INPUT` — input is `data/candles_
    <PAIR>_M1_<spanlabel>_BA.jsonl` and the candidate inspection saw it
    valid
  - `DETERMINISTICALLY_DERIVABLE_FROM_ACCEPTED_RAW` — input is derived
    from M1 BA via a function whose AST and source-text SHA-256 are
    both recorded; derivation function is in production code
  - `MISSING` — input is neither retained locally nor derivable via an
    AST-evidenced function
  - `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION` — input's
    derivability is plausible from AST but the function's behaviour
    cannot be confirmed without execution
- **Excluded slice**: `artifacts/stage25_0a/path_quality_dataset.parquet`
  is recorded in a separate top-level field
  `excluded_nonauthority_development_slice` (per Amendment 1
  §4 / EXCLUDED_NONAUTHORITY_DEVELOPMENT_SLICE class). It is collected
  via `os.stat` only (size + mtime) and is **never** placed inside the
  `dependencies[]` list, and **never** counts as `MISSING` for E2.

### Pipeline feasibility (§7) — AST-only execution-shape modelling

- **Owner**: `inspector.pipeline_feasibility`
- **Targets** (frozen at implementation time as `ENTRYPOINT_REGISTRY`):
  signal generator entry function(s), label generator entry function(s),
  D-1 PnL computation entry function(s), split-builder entry function(s)
- **I/O**: `ast.parse(<source_text>)` on each target file
- **Per entrypoint extracted**: `function_qualname`, `source_path`,
  `source_sha256` (source-text SHA-256, **not** function-byte hash —
  whole-file hash is the authoritative referent), `signature`
  (`ast.get_source_segment` over `args` node), `docstring_excerpt`
  (first 200 chars of `ast.get_docstring`), `ast_evidence`:
  - `hard_coded_artifact_paths[]` — string literals containing
    `artifacts/`, `data/`, or pattern-matched path-like substrings
  - `parameterisable_for_new_epoch_namespace` — bool heuristic:
    `True` if any function arg name matches
    `(?i)(out_path|output_dir|root|namespace|artifacts_root|dataset_dir)`
    **and** path-typed string literals are absent or formatted via
    that arg; `False` otherwise
- **Gate P2 worklist**: each entrypoint adds notes about what Gate P2
  must execute to verify behaviour (e.g., "stage23_0a aggregate_m1_to_m5
  must be invoked under new namespace and output row count compared
  against expected interval-divided count")
- **PASS-claim prohibition**: this submodule does **not** assert that
  any entrypoint will produce non-empty per-pair output. The resolver
  ensures no such claim reaches `gate_p1_report.json`; the writer
  refuses any forbidden field (§7).

### Retention (§6.1 + §6.2)

- **Owner**: `inspector.retention`
- **I/O**: `Path.stat()` only (size metadata; no read)
- **Inputs to record**: per-candidate aggregate raw bytes (from
  `raw_inventory`), per-candidate expected labels storage estimate
  (heuristic from row counts × labels schema width — exact heuristic
  frozen in implementation), per-candidate expected split-manifest
  storage estimate
- **Guard reference**: `_gate_p1_inspector.tolerances.ARTIFACT_SIZE_GUARD_BYTES`
  (mirror of `_verification_harness.tolerances.ARTIFACT_SIZE_GUARD_BYTES
  = 99614720`; both modules carry a `source_of_truth` comment)
- **First-run mode**: if `first_run_mode=True`:
  - `in_repo_retention_within_guard` is forced to `false`
  - `existing_local_immutable_archive_visible_read_only` is forced to
    `false`
  - candidate retention classification is restricted to
    `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE` or
    `RETENTION_DESTINATION_UNRESOLVED`
- **Candidate retention options recording**: the OANDA 2026-05-31
  archive at `artifacts/oanda_archive_2026-05-31/` is recorded under
  `candidate_retention_options_requiring_later_authorisation` as a
  descriptive candidate input only; it is **not** declared a retention
  destination

### Universal binding

No submodule above imports any production pipeline module
(`stage*`, `fetch_oanda_*`, `src.*`, `fx_ai_trading.*`). All consumption
of production code is via `ast.parse` over `Path.read_text()`. The
`sys.meta_path` finder installed by `bootstrap.py` provides redundant
enforcement.

---

## §7 Report artifact schema (implementation-level)

Seven artifacts are emitted, all under `artifacts/gate_p1_report/
<report_id>/`. All file writes pass through `report.writers`, which
enforces extension allowlist (`.json` / `.md`) and per-artifact size
guard (1 MB per JSON, 256 KB per markdown — frozen here as PR-B-local
constants in `_gate_p1_inspector/tolerances.py`).

### Common metadata block (every JSON artifact)

Every JSON artifact carries:

```
"schema_version": "gate-p1-pr-b-1.0",
"pr_a_spec_version": {
  "path": "docs/design/gate_p1_feasibility_inspection_protocol.md",
  "sha256": "<SHA-256 of the current Amendment-1-inlined doc bytes>",
  "amendment": "amendment_1"
},
"pr_b_code_hash": "<SHA-256 of concat-by-sorted-path of all .py under scripts/_gate_p1_inspector/>"
```

The outer writes `pr_b_code_hash` to `execution_envelope.json`; inner
recomputes it independently and asserts equality (drift → HALT).

### `gate_p1_report.json`

```
{
  "report_id": "<str>",
  "outer_launch_ts_utc": "<ISO-8601 Z>",
  "clean_code_sha": "<git HEAD SHA>",
  "first_run_mode": true,
  "top_level_outcome": "<LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY | LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH | RETENTION_DESTINATION_UNRESOLVED>",
  "retention_substatus": "<RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE | RETENTION_DESTINATION_UNRESOLVED | null>",
  "per_candidate_summary": [
    {
      "candidate_id": "<str>",
      "nominal_span_label": "<str>",
      "candidate_status": "<...>",
      "retention_classification": "<...>",
      "reason_codes": ["<str>", ...]
    },
    ...
  ],
  "<common metadata block>"
}
```

`top_level_outcome` enum **excludes** `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW` when `first_run_mode=true` (writer validator).

### `raw_inventory_<candidate_id>.json`

```
{
  "candidate_id": "<str>",
  "nominal_span_label": "<str>",
  "pair_universe": ["EUR_USD", ...],
  "pair_universe_hash": "<sha256>",
  "pair_universe_source_a": {"path": "scripts/stage23_0a_build_outcome_dataset.py", "sha256": "<...>"},
  "pair_universe_source_b": {"path": "scripts/stage22_0a_scalp_label_design.py", "sha256": "<...>"},
  "schema_authority_source": {"path": "scripts/stage23_0a_build_outcome_dataset.py", "sha256": "<...>", "required_fields": [...]},
  "files": [
    {
      "pair": "EUR_USD",
      "path": "data/candles_EUR_USD_M1_730d_BA.jsonl",
      "present": true,
      "size_bytes": <int>,
      "file_sha256": "<...>",
      "row_count": <int>,
      "ts_min_utc": "<ISO-8601 Z>",
      "ts_max_utc": "<ISO-8601 Z>",
      "monotonicity_violations": <int>,
      "duplicate_timestamps": <int>,
      "missing_fields_count": <int>,
      "non_finite_fields_count": <int>,
      "schema_valid": <bool>,
      "schema_extension_findings": [{"field_name": "volume", "occurrence_count": <int>}, ...],
      "gap_profile": {"histogram": [...], "max_gap_seconds": <int>}
    },
    ...
  ],
  "aggregate_common_interval": {"obs_start_utc": "<...>", "obs_end_utc": "<...>"} | null,
  "discovered_non_candidate_files": ["data/candles_EUR_USD_M5_730d_BA.jsonl", ...],
  "<common metadata block>"
}
```

### `dependency_inventory_<candidate_id>.json`

```
{
  "candidate_id": "<str>",
  "consumers": [
    {
      "consumer": "<str>",
      "source_path": "scripts/...py",
      "source_sha256": "<...>",
      "dependencies": [
        {
          "dependency_label": "<str>",
          "class": "<AVAILABLE_AS_RETAINED_RAW_LOCAL_INPUT | DETERMINISTICALLY_DERIVABLE_FROM_ACCEPTED_RAW | MISSING | UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION>",
          "evidence_source_path": "scripts/...py | null",
          "evidence_source_sha256": "<...> | null",
          "ast_evidence_summary": "<short string>",
          "reason": "<short string>"
        },
        ...
      ]
    },
    ...
  ],
  "excluded_nonauthority_development_slice": {
    "path": "artifacts/stage25_0a/path_quality_dataset.parquet",
    "os_stat_size": <int>,
    "os_stat_mtime_utc": "<ISO-8601 Z>",
    "classification": "EXCLUDED_NONAUTHORITY_DEVELOPMENT_SLICE"
  },
  "<common metadata block>"
}
```

The `excluded_nonauthority_development_slice` is a **separate** field
from `dependencies[]` and is **never** counted as MISSING for E2 (per
Amendment 1 §4 binding).

### `coverage_<candidate_id>.json`

```
{
  "candidate_id": "<str>",
  "nominal_span_label": "<str>",
  "observation_start_timestamp_utc": "<ISO-8601 Z> | null",
  "observation_end_timestamp_utc": "<ISO-8601 Z> | null",
  "span_days_effective": <float> | null,
  "pair_universe": [...],
  "pair_universe_hash": "<...>",
  "raw_schema_version": "<str>",
  "common_coverage_findings": [
    {"finding_type": "gap_density", "value": <float>, "interpretation": null},
    ...
  ],
  "scientific_adequacy_flags": [
    {"flag_type": "regime_acknowledgement_required", "scope": "<...>"},
    ...
  ],
  "<common metadata block>"
}
```

**Forbidden fields** (writer schema-validator rejects any presence of
the below keys):

- `epoch_freeze_timestamp_utc`
- `manifest_id`
- `baseline_metric`, `baseline_passed`
- `a0_broad_eligibility_*`
- `pass_tabular_evidence_reconfirmed`
- `full_tabular_evidence_rebuilt`

### `retention_feasibility_<candidate_id>.json`

```
{
  "candidate_id": "<str>",
  "expected_total_raw_bytes": <int>,
  "expected_labels_storage_estimate_bytes": <int>,
  "expected_split_manifest_storage_estimate_bytes": <int>,
  "expected_total_retention_bytes": <int>,
  "in_repo_retention_size_guard_bytes": 99614720,
  "in_repo_retention_size_guard_source": "scripts/_verification_harness/tolerances.py::ARTIFACT_SIZE_GUARD_BYTES",
  "in_repo_retention_size_guard_semantics": "per-file ceiling, NOT aggregate budget",
  "in_repo_retention_within_guard": false,
  "existing_local_immutable_archive_visible_read_only": false,
  "restoration_procedure_documented": false,
  "candidate_retention_options_requiring_later_authorisation": [
    {"option_id": "oanda_archive_2026_05_31",
     "description": "10y OANDA practice archive captured 2026-05-31, retained locally only",
     "manifest_path": "artifacts/oanda_archive_2026-05-31/candles_manifest.json",
     "note": "Recorded as candidate input only. Not a retention destination."}
  ],
  "retention_classification": "<RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE | RETENTION_DESTINATION_UNRESOLVED>",
  "<common metadata block>"
}
```

Writer schema-validator enforces:

- `in_repo_retention_within_guard` is exactly `false`
- `existing_local_immutable_archive_visible_read_only` is exactly `false`
- `retention_classification` is one of the two permitted values only

(Both `in_repo_retention_within_guard=true` and
`existing_local_immutable_archive_visible_read_only=true` raise
writer-validation HALT, structurally enforcing Amendment 1 §6.2
first-PR-B-run restriction.)

### `pipeline_feasibility.json`

```
{
  "signal_generators": [
    {
      "function_qualname": "scripts.stage_signal_generator::generate_signal",
      "source_path": "scripts/stage_signal_generator.py",
      "source_sha256": "<...>",
      "signature": "<args text>",
      "docstring_excerpt": "<first 200 chars>",
      "ast_evidence": {
        "hard_coded_artifact_paths": ["artifacts/foo/...", ...],
        "parameterisable_for_new_epoch_namespace": <bool>
      },
      "gate_p2_worklist_notes": ["<str>", ...]
    },
    ...
  ],
  "label_generators": [...],
  "d1_pnl_implementations": [...],
  "split_builders": [...],
  "<common metadata block>"
}
```

**Forbidden fields**:

- `non_empty_output_claim`
- `expected_row_count`
- `verified_non_empty_per_pair`

### `report.md`

Plain markdown summary:

1. **Header** — report_id, outer_launch_ts_utc, clean_code_sha,
   first_run_mode (templated literal: "First-run binding: `PASS` is
   not reachable under this execution.")
2. **Top-level outcome** — outcome literal + 1-2 paragraphs explaining
   reason and next step (separately authorised retention decision
   required)
3. **Per-candidate summary table** — one row per candidate (
   nominal_span_label, candidate_status, retention_classification, top
   reason_code)
4. **Artifact index** — relative links to all 6 JSON artifacts
5. **Next steps** — bullet list referring to protocol §11 / this plan
   §11

Target length: 300-500 lines. The writer asserts `PASS` is never
written in `report.md` body via a simple grep over the rendered text.

### Per-artifact size guard

Each artifact carries a PR-B-local size ceiling (frozen in
`_gate_p1_inspector/tolerances.py`):

- JSON artifacts: 1 MB
- `report.md`: 256 KB

The writer raises `Gate P1 inspection-integrity HALT` if any single
artifact exceeds its ceiling (defends against accidental verbose
output).

---

## §8 Outcome aggregation logic — decision tree

### `inspector.resolver.resolve_candidate(candidate_report, first_run_mode: bool) -> CandidateOutcome`

The resolver is a **pure function**. It receives a candidate's full
inspection data (raw inventory, pair authority result, schema authority
result, dependency inventory, coverage, retention, pipeline feasibility)
and returns a `CandidateOutcome` dataclass.

Decision tree (order-fixed; evaluation halts at first matching branch
unless noted):

1. **Schema authority HALT** — if `authority.schema` returned
   `INTEGRITY_HALT_SCHEMA_AUTHORITY_DRIFT`, raise `Gate P1
   inspection-integrity HALT`. No outcome emitted.
2. **Pair authority HALT** — if `authority.pair_universe` returned
   `INTEGRITY_HALT_CANONICAL_UNPARSEABLE`, raise HALT. No outcome
   emitted.
3. **Pair authority ambiguous** — if `authority.pair_universe` returned
   `AMBIGUOUS`, candidate outcome = `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`,
   reason = `PAIR_UNIVERSE_AUTHORITY_AMBIGUOUS`. Continue to retention
   step 9 (record substatus).
4. **Raw inventory insufficient** — if any of the 20 pairs has
   `present=false` or `schema_valid=false`, candidate outcome =
   `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH`. Reason codes record which
   pairs failed and why. Continue to retention step 9 (record
   substatus, though not relevant for top-level).
5. **Dependency missing (critical)** — if any cell in
   `dependency_inventory` with class `MISSING` is in the resolver's
   critical-cell registry, candidate outcome = `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH`,
   reason = `DEPENDENCY_MISSING_CRITICAL_<consumer>_<dependency>`.
6. **Dependency uncertain (critical)** — if any critical cell has class
   `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION`, candidate outcome
   = `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`, reason =
   `DEPENDENCY_RECONSTRUCTION_UNCERTAIN`.
7. **Pipeline namespace parameterisation insufficient** — if any
   entrypoint in `pipeline_feasibility` has
   `parameterisable_for_new_epoch_namespace=false`, candidate outcome
   = `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`, reason =
   `PIPELINE_NAMESPACE_PARAMETERISATION_INSUFFICIENT`.
8. **All sufficient** — if none of the above triggered, candidate is
   "all sufficient". Proceed to retention classification:
9. **Retention classification** — from `inspector.retention`:
   - `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE` — if
     outcome was set in steps 3-7, retain that outcome with this
     substatus. If outcome unset (all sufficient), candidate outcome =
     `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`, substatus =
     `RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`.
   - `RETENTION_DESTINATION_UNRESOLVED` — if outcome was set, retain
     with this substatus. If outcome unset, candidate outcome =
     `RETENTION_DESTINATION_UNRESOLVED`.
   - `IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2` or
     `EXISTING_LOCAL_IMMUTABLE_ARCHIVE_VISIBLE_READ_ONLY` — these
     classifications imply the all-sufficient path leads to
     `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW`. Under
     `first_run_mode=True`, this is structurally impossible: the
     retention submodule forbids both classifications under
     first-run mode (§6). If somehow reached, the resolver raises
     `Gate P1 inspection-integrity HALT — first-run unreachable
     branch entered`.

### `inspector.resolver.resolve_top_level(candidates, first_run_mode: bool) -> TopLevelOutcome`

Top-level outcome by precedence (protocol §9.2):

1. Any candidate with `LOCAL_DATA_CANDIDATE_FEASIBLE_FOR_CONSTRUCTION_REVIEW`
   → top-level = same. (Under `first_run_mode=True`, this branch is
   unreachable; the resolver asserts so.)
2. Any candidate with `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY` →
   top-level = same, contributing candidates listed.
3. All candidates with `RETENTION_DESTINATION_UNRESOLVED` (and not all
   insufficient) → top-level = `RETENTION_DESTINATION_UNRESOLVED`.
4. Otherwise → top-level = `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH`.

### First-run mode wiring

- `bootstrap.py` reads `--first-run` from CLI and passes
  `first_run_mode=True` to all resolver calls.
- The resolver receives this as a required argument (no default).
- A negative unit test (§10) verifies that simulating retention
  classification `IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2`
  under `first_run_mode=True` raises HALT.

### Critical-cell registry

The resolver carries a `CRITICAL_CELL_REGISTRY` table mapping
`(consumer, dependency_label)` pairs to a `is_critical: bool`. The
registry is frozen at PR-B implementation time (in PR-B.2 per §11) and
listed exhaustively in the resolver source. Modification requires a
new design memo and PR. The registry must align with protocol §4's
enumerated consumer list (see open question §13.Q7).

---

## §9 Candidate spans — inspection scope and order

### Candidate spans

Protocol §3 enumerates `730d_BA`, `365d_BA`, and "any other already-
present complete BA span discovered read-only". Local observation
shows `data/` contains M1 BA files at multiple nominal spans:
`90d_BA`, `365d_BA`, `730d_BA`, `3650d_BA`.

PR-B candidate set, in order of inspection:

1. `90d_BA` — **excluded from candidate set**. Recorded in
   `raw_inventory.discovered_non_candidate_files` as informational only.
   (Nominal span is below the threshold for meaningful epoch
   construction per protocol §3 spirit. Open question §13.Q9 covers
   whether to lift this exclusion.)
2. `365d_BA` — **candidate** (lower-info epoch span; admissible per
   protocol §3 only after explicit user approval; PR-B records but
   does not request approval here).
3. `730d_BA` — **candidate** (default protocol §3 candidate).
4. `3650d_BA` — **candidate** ("any other already-present complete BA
   span discovered read-only" per protocol §3).

All candidates undergo the same §3-§7 inspection. No short-circuit
based on previous candidate's outcome.

### Higher-TF (M5 / M15 / H1 / H4 / D)

Protocol §3 filename pattern restricts candidate raw to M1 BA. Higher-
TF files (`candles_<PAIR>_<M5|M15|H1|H4|D>_<spanlabel>_BA.jsonl`) are
discovered but recorded in `discovered_non_candidate_files` only —
they do not enter raw_inventory's candidate files list.

In `dependency_inventory`, higher-TF inputs are classified per
Amendment 1 §4 binding ("silent substitution of derived candles for
independently-sourced higher-TF candles is prohibited"):

- if a known M1→{M5,M15} aggregation function exists in production
  source (e.g., `stage23_0a::aggregate_m1_to_tf`) and its AST + SHA-256
  can be recorded, class = `DETERMINISTICALLY_DERIVABLE_FROM_ACCEPTED_RAW`
  (with derivation evidence)
- if no aggregation function is found (e.g., D1 with bid/ask handling
  that production code does not implement), class =
  `UNCERTAIN_REQUIRES_GATE_P2_EXECUTION_VALIDATION`
- the presence of an independent `candles_<PAIR>_<TF>_<spanlabel>_BA.jsonl`
  file in `data/` is **never** used as silent evidence that the higher-TF
  input is sourced — it is recorded only in
  `discovered_non_candidate_files` and may be relevant to Gate P2 but
  is not a binding fact for Gate P1

### Per-candidate sequencing

Within a single candidate, the inspection proceeds:

1. authority resolution (pair + schema)
2. raw inventory (per file, sequential — no threading)
3. coverage derivation
4. dependency inventory
5. pipeline feasibility (frozen entrypoint registry)
6. retention classification
7. resolver invocation → candidate outcome
8. report writer for candidate's 4 JSON artifacts

After all candidates: top-level resolver invocation → emit
`gate_p1_report.json` + `pipeline_feasibility.json` (shared across
candidates) + `report.md`.

### Archive directory exclusion

`artifacts/oanda_archive_2026-05-31/` (PR #364) is **not** scanned for
candidate raw in PR-B's first execution. Its bytes live in `data/`
(gitignored); the archive directory contains only provenance
(manifest + log + inventory + README). The archive's `candles_manifest.json`
may be referenced as a candidate retention option (§7
`candidate_retention_options_requiring_later_authorisation`), but is
not itself a raw input. Open question §13.Q2 covers whether to widen
this scope in a later PR-B run.

---

## §10 Test strategy

PR-B tests live in `tests/gate_p1_pr_b/`. They use only the Python
standard library + `pytest` (open question §13.Q4: drop `pytest`
dependency if the repo's policy disallows it; design supports
`unittest` fallback).

### Unit tests

- **resolver** — all 9 decision-tree branches (§8) covered with
  synthesised `CandidateReport` fixtures. Includes a **negative test**
  that constructs a candidate with `retention_classification=IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2`
  and `first_run_mode=True` and asserts `Gate P1
  inspection-integrity HALT` is raised.
- **authority.pair_universe** — fixtures with stub source modules
  having identical / differing / unparseable PAIRS_20 lists. Verify
  hash determinism and ambiguity detection.
- **authority.schema** — fixtures with `load_m1_ba` having
  `REQUIRED_FIELDS` matching protocol §3.1, deviating from it, and
  parse-failing. Verify HALT semantics.
- **report writers** — verify extension-allowlist (`.json`/`.md`),
  per-artifact size guard, forbidden-field rejection (all forbidden
  fields per §7 individually tested).
- **inspector submodules** — each consumes a small synthetic JSONL
  (3-5 rows) and asserts output fields match expected values; verify
  no row correction occurs (monotonicity violations remain in count,
  not in re-ordering of input data).

### Integration tests (read-only fixture dataset)

- `tests/gate_p1_pr_b/fixtures/tiny_jsonl/` contains 1-3 hand-authored
  synthetic `candles_<PAIR>_M1_<NN>d_BA.jsonl` files (10-30 rows each,
  protocol §3.1 schema)
- `tests/gate_p1_pr_b/fixtures/stub_source_modules/` contains synthetic
  `stage23_0a_*.py`, `stage22_0a_*.py`, and entrypoint stubs
- End-to-end run: invoke outer launcher pointed at a tmp report dir
  with `--first-run` set, candidate root = fixtures dir
- Verify:
  - `gate_p1_report.json` emitted with `top_level_outcome` in the
    permitted-for-first-run set (not `FEASIBLE`)
  - all 6 sibling artifacts emitted
  - no entry in `sys.modules` matches `scripts.stage*`,
    `scripts.fetch_*`, `src.*`, `fx_ai_trading.*` after the run
  - no file modified outside the report dir
  - post-run audit passes

### Property-based tests (guard tripwires)

- **filesystem guard**: attempted writes to (a) path outside report dir
  with `.json` extension, (b) path inside report dir with `.txt`
  extension, (c) `Path.mkdir` outside report dir, (d) `tempfile.mkdtemp`
  anywhere — all raise HALT
- **network guard**: `socket.socket()`, `socket.create_connection(...)`,
  `urllib.request.urlopen("http://example.com")`,
  `http.client.HTTPConnection("example.com")` — all raise HALT
- **subprocess guard**: `subprocess.run(["ls"])`, `os.system("ls")`,
  `os.popen("ls")`, `os.spawnv(...)`, `multiprocessing.Process(...).start()`
  — all raise HALT
- **credentials guard**: `os.environ.get("OANDA_ACCESS_TOKEN")`,
  `os.environ["TOKEN"]`, `"SECRET_FOO" in os.environ`,
  `os.environ.get("aws_access_key_id")` (case-insensitive regex) — all
  raise HALT; including the presence-check via `__contains__` (per
  Amendment 1 §3)
- **bytecode guard**: launch inner with `sys.dont_write_bytecode = False`
  forced → bootstrap HALTs at assertion

### Outer launcher tests

- outer artificially modifying a file outside report dir → audit HALT
  (exit code 3)
- outer attempting to call `subprocess.run` other than the 3 allowed
  invocations → own write-allowlist wrapper detects → exit code 4
- outer cannot access `OANDA_*` env vars (verified by mock env with
  credential-pattern keys → outer must not crash, must not record any
  value, must not pass them to inner)
- inner's `sys.modules` at the moment guards complete must contain only
  stdlib modules + `_gate_p1_inspector.guards.*` — verified by an
  assertion inserted into `bootstrap.py` after guard install and re-
  exercised in test mode

### Schema tests

- For each of the 7 artifacts, a hand-authored JSON Schema (no
  `jsonschema` dependency — implemented as plain dict-walk validator in
  test code) verifies field presence, types, and the forbidden-field
  exclusion list (§7).

### Snapshot test

- A canonical fixture run emits all artifacts; a baseline snapshot of
  the **schema** (not values) is committed and compared. PR-B changes
  that intentionally alter the schema must update the snapshot in the
  same PR.

### Test discipline

- All tests run without any production module import. A `conftest.py`
  fixture asserts `sys.modules` is clean at session start.
- All tests use only synthetic fixtures. No production `data/` file is
  ever copied into fixtures (per risk R12, §12).

---

## §11 Stage split proposal

### Recommended: 3-PR split

**PR-B.0 (infrastructure)** — outer launcher + `bootstrap.py` + all 5
guard modules + write-allowlist + post-run audit + outer-launcher tests
+ guard tripwire tests. Inspector submodules are **stubs** that emit an
empty `gate_p1_report.json` with `top_level_outcome="STUB_NO_INSPECTION_PERFORMED"`
(a 7th outcome literal added in PR-B.0 only and removed by PR-B.1).
This PR exercises the side-effect-free execution envelope end-to-end
without performing any inspection. Estimated: 15-20 files, ~1500-2000
lines (including tests).

**PR-B.1 (authority + raw inventory + coverage + retention + resolver
+ first report subset)** — `authority/`, `inspector/raw_inventory.py`,
`inspector/coverage.py`, `inspector/retention.py`, `inspector/resolver.py`,
report writers for 5 artifacts (`gate_p1_report.json`,
`raw_inventory_<id>.json`, `coverage_<id>.json`,
`retention_feasibility_<id>.json`, `report.md`). **The first PR-B
inspection executes here**, emitting `LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`
/ `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH` / `RETENTION_DESTINATION_UNRESOLVED`
per resolver decision. PR-B.1 also removes the PR-B.0 stub outcome
literal. Estimated: 15-20 files, ~2500-3500 lines.

**PR-B.2 (dependency inventory + pipeline feasibility + remaining
report)** — `inspector/dependency_inventory.py`,
`inspector/pipeline_feasibility.py`, report writers for the remaining
2 artifacts (`dependency_inventory_<id>.json`, `pipeline_feasibility.json`),
critical-cell registry, frozen entrypoint registry. A second PR-B
inspection executes against the now-complete pipeline. Estimated:
10-15 files, ~2000-3000 lines.

### Alternative: 1-PR

PR-B everything in a single PR. Advantage: one-to-one mapping with
protocol §3-§9 visible at a glance. Disadvantage: review-intractable
(30-50 files, 5000-8500 lines). Not recommended.

### Alternative: 2-PR

PR-B.0 (infrastructure + minimal inspection covering §3 / §5 / §6 +
resolver + 5 artifacts; this would emit a first-run outcome) + PR-B.1
(dependency + pipeline expansion + 2 more artifacts). Trade-off:
shorter sequence but a larger PR-B.0.

### Default recommendation

This plan defaults to **3-PR split**. The user may select an alternative
when authorising PR-B.0; selection is recorded in PR-B.0's commit
message and propagated to subsequent PRs.

### Per-stage authorisation binding

Each of PR-B.0 / PR-B.1 / PR-B.2 requires **independent** explicit
user authorisation. Merging this plan PR does **not** authorise PR-B.0.
Merging PR-B.0 does **not** authorise PR-B.1. Re-declares protocol §11
"no auto-route".

---

## §12 Risk register

- **R1 — Unversioned-gitignored-parquet recurrence**: PR #361 §7 anti-
  pattern. Mitigation: every PR-B output is committed JSON/MD; no
  `.gitignore` modification (Amendment 1 §8.3); `EXCLUDED_NONAUTHORITY_DEVELOPMENT_SLICE`
  classification structurally separates the dev slice.
- **R2 — Production module side-effect import**: implementer writes
  `import scripts.stage23_0a_build_outcome_dataset` in inspector code.
  Mitigation: `sys.meta_path` finder rejects; bootstrap-time assertion
  on `sys.modules`; dedicated unit test.
- **R3 — Hash computation OOM**: 3650d_BA M1 files are multi-GB.
  Mitigation: streaming SHA-256 over 8 MB blocks, single-pass
  combined with row count (§6 binding).
- **R4 — Monotonicity "fix before recording" temptation**: implementer
  sorts rows before hashing. Mitigation: protocol §3 binding written
  into raw_inventory module docstring; row processing is fixed-order
  streaming (no buffering); unit test asserts ordering preserved.
- **R5 — Outer launcher subprocess sprawl**: outer needs more than git
  / inner spawn. Mitigation: outer subprocess invocations capped at 3
  (git rev-parse, git status × 2, inner spawn); guard-pattern wrapper
  detects anything else.
- **R6 — First-run unreachable PASS branch implementation**: resolver
  has a path to `FEASIBLE` that activates under first-run mode.
  Mitigation: resolver receives `first_run_mode` as required arg;
  retention submodule forbids the two PASS-enabling classifications
  under first-run; resolver `FEASIBLE` branch asserts unreachable
  under first-run; dedicated negative unit test.
- **R7 — Silent retention destination pre-approval**:
  `artifacts/oanda_archive_2026-05-31/` becomes a de-facto retention
  destination by inclusion in reports. Mitigation: archive recorded
  only under `candidate_retention_options_requiring_later_authorisation`
  with explicit "not a retention destination" wording; writer
  validator forbids `existing_local_immutable_archive_visible_read_only=true`
  under first-run.
- **R8 — `.gitignore` modification temptation**: implementer wants to
  bypass per-artifact size guard. Mitigation: Amendment 1 §8.3
  binding; outer post-run audit detects `.gitignore` diff; per-
  artifact size guard HALT instead.
- **R9 — Schema authority drift**: `stage23_0a::load_m1_ba` evolves
  with a new field; PR-B silently accepts. Mitigation: schema
  authority module compares extracted `REQUIRED_FIELDS` against
  protocol §3.1 list and HALTs on drift; schema field list lives as a
  PR-B-local constant, not imported.
- **R10 — Implementation outruns contract (PR #360 lesson)**:
  mitigation: this plan is a doc-only PR; PR-B.0 / B.1 / B.2 each
  separately authorised.
- **R11 — `pr_b_code_hash` outer/inner drift**: outer captures hash A,
  inner computes hash B, they differ. Mitigation: both use the same
  deterministic recipe (sorted-path concat → SHA-256); inner
  re-verifies and HALTs on mismatch.
- **R12 — Test fixtures leak production data**: implementer copies
  `data/candles_*_BA.jsonl` into fixtures for convenience. Mitigation:
  CI grep rejects any fixture file exceeding 64 KB or matching
  production naming; fixtures are version-controlled and reviewed.
- **R13 — Inner crash leaves report dir in a half-written state**:
  PR-B.0 audit detects, but the report dir already exists. Mitigation:
  inner writes each artifact atomically (temp file in report dir →
  rename); `gate_p1_report.json` is written last; outer audit checks
  for `gate_p1_report.json` presence and treats absence as inner
  failure (exit 2).

---

## §13 Open questions

The following items require user judgment before PR-B.0 authoring
begins. Each carries a recommendation; user may adopt or override.

- **Q1 — `_verification_harness/tolerances.py` import policy**: may the
  inspector import `ARTIFACT_SIZE_GUARD_BYTES` directly from this pure-
  constant module? **Recommendation**: no. Mirror the value in
  `_gate_p1_inspector/tolerances.py` with a `source_of_truth` comment
  citing `_verification_harness/tolerances.py::ARTIFACT_SIZE_GUARD_BYTES`.
  Rationale: keeps inspector independent of any non-stdlib module,
  honouring AST/source-only mandate at its strictest. The duplicate
  constant is checked by a unit test against the documented source.
- **Q2 — Archive directory scope**: should PR-B's first run inspect
  `artifacts/oanda_archive_2026-05-31/candles_manifest.json` and treat
  the bytes referenced therein (`data/candles_*_3650d_BA.jsonl`) as
  in-scope? **Recommendation**: no. The 3650d_BA candidate is already
  picked up by `data/` glob. Archive manifest reference is recorded in
  `retention_feasibility_<id>.json` only. Re-evaluate in a future
  PR-B run after retention destination is established.
- **Q3 — Stage split selection**: 1 / 2 / 3 PR? **Recommendation**:
  3-PR split (§11 default).
- **Q4 — `pytest` dependency**: may PR-B tests depend on `pytest`?
  **Recommendation**: yes if the repo already uses it (verify on
  PR-B.0 authoring); otherwise use `unittest`. Plan supports both.
- **Q5 — Candidate root path**: should the inspector accept candidate
  roots other than `data/`? **Recommendation**: no. `DATA_DIR =
  REPO_ROOT / "data"` is hard-coded.
- **Q6 — Empty `artifacts/gate_p1_report/` commit**: should the
  directory exist in-repo via a `.gitkeep`? **Recommendation**: no.
  PR-B.0 creates it at runtime; the dir is recorded as a write
  destination only.
- **Q7 — Critical-cell registry approval**: when does the
  `CRITICAL_CELL_REGISTRY` (which `(consumer, dependency)` cells block
  a candidate from PARTIAL/INSUFFICIENT) get user-approved? **Recommendation**:
  proposed in PR-B.2's commit message body; explicit user sign-off
  required before merge.
- **Q8 — Outer env scrub strictness**: pass empty env to inner, or
  filter only credential-pattern keys? **Recommendation**: pass a
  minimal allowlist (`PATH`, `SYSTEMROOT`, `TEMP`, `TMP`) and zero else.
  Credential-pattern keys are absent by construction.
- **Q9 — `90d_BA` exclusion**: keep `90d_BA` out of candidate set?
  **Recommendation**: yes for first PR-B run. Add to candidate set
  in a future run if needed (separately authorised).
- **Q10 — First-run mode toggle in code**: build PR-B with the
  off-switch (`--no-first-run` flag) ready, or leave it for a future
  PR? **Recommendation**: leave for a future PR (the eventual
  retention authorisation memo). PR-B.0 / B.1 / B.2 hardcode
  `first_run_mode=True`.
- **Q11 — Inner-process working directory**: should inner run from
  the report dir or from the repo root? **Recommendation**: repo
  root. Avoids `os.chdir` complications and keeps all `Path(...)`
  references explicit-relative-from-root.

---

## Closing — what merging this plan PR does and does not do

Merging this PR locks the **implementation plan**, not the
implementation. PR-B authoring (PR-B.0 / PR-B.1 / PR-B.2) does not
begin until separate user authorisation for PR-B.0 lands. This plan
itself does not modify any executable code, does not initiate any
inspection, does not modify any retention destination, and does not
change any prior verdict.

Status carry-forward, unchanged by this PR:

- V2-expanded Stage 2 = `HALTED_INPUT_UNAVAILABLE`
- F-1 = `UNEXECUTABLE_INPUT_UNAVAILABLE`
- PR #356 audit = `TARGETED_VERIFICATION_REQUIRED`
- Phase 27 / 28 / 29.0a verdicts preserved verbatim
- A0-broad β remains halted
- Stage 2 implementation branch
  `research/tabular-targeted-verification-v2-expanded-stage2-preflight`
  @ local `0234ed3` retained locally only

Next step (post-merge of this plan PR): user authorisation decision
for PR-B.0 (infrastructure) under the 3-PR split recommendation.
