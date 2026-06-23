# Gate P1 PR-B.0 — usage and non-scope

**Stage:** Foundation **T1** / Gate P1 PR-B.0 (infrastructure only).
**Status:** infrastructure scaffold merged; performs **no** Gate P1 inspection.
**Plan:** `docs/design/gate_p1_pr_b_implementation_plan.md` (PR #365) §3-§5, §11.

---

## What PR-B.0 is

PR-B.0 is the **infrastructure / launcher skeleton** for the Gate P1 PR-B
read-only inspection. It provides:

- an outer launcher (`scripts/gate_p1_pr_b_launcher.py`) that builds an
  audited, side-effect-free execution envelope and spawns the inner guarded
  inspector;
- an inner bootstrap (`scripts/_gate_p1_inspector/bootstrap.py`) that installs
  five guard families in a fixed order before running anything;
- guard modules (`scripts/_gate_p1_inspector/guards/`) for bytecode, production
  imports, credentials / env-vars, network, subprocess, and a filesystem
  write-allowlist;
- a **stub inspector** that performs no inspection and emits a clearly-marked
  stub report.

PR-B.0 proves the inspector can be invoked **safely** in stub mode without
reading real data, credentials, broker state, quote feeds, or production
runtime state.

## What PR-B.0 is NOT

PR-B.0 performs **no** Gate P1 inspection. It does **not**:

- read any byte under `data/`, `artifacts/`, or any candle / JSONL / parquet /
  CSV file;
- open or hash the OANDA 2026-05-31 archive;
- run raw inventory, coverage, retention feasibility, dependency inventory, or
  pipeline feasibility;
- access credentials, environment variables, networks, brokers, quote feeds,
  or subprocesses from the inner inspector;
- decide any feasibility, retention, or byte-admissibility outcome;
- grant any T2 / T3 / T4 / epoch-adoption authorisation.

**PR-B.1** (authority + raw inventory + coverage + retention + resolver) and
**PR-B.2** (dependency + pipeline feasibility) are **not implemented** here and
each require independent explicit authorisation (plan §11).

## Usage (stub mode only)

```bash
# Default: a system-temp stub-only dir (<tmp>/gate_p1_pr_b0_stub/<id>/):
python scripts/gate_p1_pr_b_launcher.py --report-id my-stub-run-001 --first-run

# Explicit test-controlled report root (must be outside data/ and artifacts/):
python scripts/gate_p1_pr_b_launcher.py --report-id t --report-root /tmp/out
```

### Stub-output boundary (where PR-B.0 may write)

PR-B.0 stub output is **never** written to real-evidence or repo-tracked
locations. The launcher **fails closed** (exit 1) if `--report-root`:

- contains a reserved path component: `data`, `artifacts`, `oanda_archive`,
  `gate_p1_report`, or `gate_p2_verification`; **or**
- resolves anywhere inside the repository working tree (so stub output can
  never be accidentally committed or confused with real Gate P1 evidence).

The default root is a **system-temp** `gate_p1_pr_b0_stub` directory — outside
the repo, never committed. The REAL inspection (PR-B.1, separately authorised)
is what writes to `artifacts/gate_p1_report/`; the PR-B.0 stub does not.

The launcher also **fails closed** on: an unknown flag, `--mode` other than
`stub`, a dirty tracked worktree, or a report-id collision.

### Outputs (all under `<report-root>/<report-id>/`)

- `execution_envelope.json` — outer envelope + post-run audit.
- `gate_p1_report.json` — the stub report (`top_level_outcome =
  STUB_NO_INSPECTION_PERFORMED`, `stub_marker = PR_B0_STUB_ONLY`).
- `report.md` — human-readable stub summary.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | inner emitted the stub report and the post-run audit passed |
| 1 | outer pre-flight failed (bad args / unsafe path / dirty worktree / collision) |
| 2 | inner crashed or a guard tripped (no stub report emitted) |
| 3 | post-run audit failed (HEAD changed, or a diff escaped the report dir) |

## PR-B.1 (read-only first-run inspection)

PR-B.1 layers the first **real** read-only inspection on top of the PR-B.0
guarded envelope. It is invoked through the same launcher with `--mode b1`:

```bash
# Default b1 report root is the controlled artifacts/gate_p1_pr_b/<id>/:
python scripts/gate_p1_pr_b_launcher.py --mode b1 --report-id run-001 --first-run

# Explicit external (test-controlled) root + a single candidate span:
python scripts/gate_p1_pr_b_launcher.py --mode b1 --report-id t \
  --report-root /tmp/out --data-dir ./data --candidate-spans 365d --first-run
```

PR-B.1 scope: authority resolution (PAIRS_20 + M1 BA schema, AST/source-only),
raw inventory (existence / size / streaming SHA-256 / row count / timestamp
boundary / schema-key presence — bounded-memory streaming, read-only), coverage
derivation, retention feasibility (size metadata only), and resolver / first-run
report composition.

PR-B.1 emits derived-metadata artifacts under `<report-root>/<id>/`:
`gate_p1_report.json`, `raw_inventory_<candidate>.json`,
`coverage_<candidate>.json`, `retention_feasibility_<candidate>.json`,
`report.md`. No raw rows, credentials, or model outputs are written.

`top_level_outcome` is one of (first-run; PASS structurally unreachable):
`LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY`,
`LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH`, `RETENTION_DESTINATION_UNRESOLVED`.

### PR-B.1 non-scope

- Dependency inventory and pipeline feasibility (PR-B.2): NOT performed.
- No T2 execution, retention deposit, cloud configuration, upload / download /
  deposit / round-trip, or byte-admissibility approval.
- No new-epoch adoption; no T3/T4 formal verification.
- The b1 report root is rejected if it is under `data/`, an OANDA archive path,
  `gate_p1_report`, or `gate_p2_verification`, or anywhere in-repo other than
  the controlled `artifacts/gate_p1_pr_b` subtree.

## Status bindings preserved

- T1 = Gate P1 PR-B implementation / review; **PR-B.0 = infrastructure only**.
- PR-B.1 / PR-B.2 not authorised here.
- T2 = Gate P2 retention destination selection / deposit + round-trip; not
  authorised here. `T2_PROPOSED_DESTINATION_PLAN` (PR #378) remains
  planning-layer only, pending T1 Gate P1 PR-B review + explicit T2 execution
  authorisation.
- T3 / T4 / new-epoch adoption / P1 / P2 / P3 / Track A-G / production change:
  not authorised here.
- Phase 9.16 v9 20p remains Tier 2 `VALID_OPERATIONAL_BASELINE`.
