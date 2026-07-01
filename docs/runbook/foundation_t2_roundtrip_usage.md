# Foundation T2 — retention deposit + round-trip harness usage

**Stage:** Foundation **T2** (Gate P2 retention deposit + round-trip), governed
by `docs/design/foundation_t2_execution_readiness_contract.md`.
**Status in this repo:** harness implemented + validated synthetically; **real
cloud deposit NOT performed** (no configured destination / credentials in this
environment; the harness stops before deposit and never fakes success).

---

## What the harness does

- **manifest** (`scripts/foundation_t2/manifest.py`) — builds a metadata-only
  multi-span deposit manifest (`365d_BA` / `730d_BA` / `3650d_BA`) from
  **committed PR-B.1 raw-inventory metadata** (logical file IDs = basenames,
  byte sizes, SHA-256). No raw candle data is re-read.
- **checksums** (`checksums.py`) — bounded-memory streaming SHA-256 + size.
- **destination** (`destination.py`) — abstract `Destination`; `LocalMockDestination`
  (filesystem-backed, for CI / harness validation); `UnavailableR2Destination`
  (the real primary alias `T2_PRIMARY_R2` when NOT configured/credentialed —
  performs no env-var / network / cloud access and reports unavailable).
- **roundtrip** (`roundtrip.py`) — deposit → observe → restore → compare
  (size + SHA-256) through a `Destination`.
- **scrub** (`scrub.py`) — fail-closed cleanliness scanner (no local/personal
  paths, credentials, signed URLs, tokens, raw rows, forbidden labels, metric
  keys, or overclaims).
- **evidence** (`evidence.py`) — metadata-only evidence builder + writer
  (scrubs before writing).
- **CLI** (`scripts/run_foundation_t2_roundtrip.py`).

## Usage

```bash
python scripts/run_foundation_t2_roundtrip.py --run-id t2-all-spans-001 \
  --git-sha <sha> --base-master-sha <sha> --generated-at <iso> \
  --authorisation-ref "<operator authorisation reference>"
```

In this environment the primary destination is unavailable, so the run reports
`T2_EXECUTION_STOPPED_BEFORE_DEPOSIT` / `T2_CREDENTIALS_UNAVAILABLE` and writes
metadata-only evidence under `artifacts/foundation_t2/<run_id>/`
(`t2_manifest.json`, `t2_roundtrip_report.json`, `t2_roundtrip_report.md`,
`evidence_cleanliness_report.json`).

## Real cloud round-trip (operator only, future)

Only an operator with credentials **already available securely** may wire a
real R2 adapter into `resolve_primary_destination()` and run a real
deposit/restore, and only if: the destination alias + file set are
unambiguous, no env-var values are printed, no credentials are committed, and
the evidence scrubber passes. If any condition is uncertain, the run must stop
and report — never fake success. CI never requires real credentials (tests use
the local mock only).

## Non-scope / bindings

- No byte-admissibility approval; no new-epoch construction/adoption; no ML
  Step 4; no model / backtest / feature / label / trading metric; no production
  change; no LLM integration.
- Backup HDD deposit and IPFS sidecar publication are **not executed** here
  (deferred).
- PR-B.1 / PR-B.2 outcomes unchanged; Phase 9.16 v9 20p remains Tier 2
  `VALID_OPERATIONAL_BASELINE`.
