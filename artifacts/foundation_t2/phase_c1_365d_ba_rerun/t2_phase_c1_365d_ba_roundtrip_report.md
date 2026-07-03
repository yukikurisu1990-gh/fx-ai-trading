# Foundation T2 — Phase C1 re-run (span `365d_BA`) — pre-deposit stop evidence

**Status: `T2_C1_RERUN_STOPPED_BEFORE_DEPOSIT_CREDENTIALS_NOT_PRESENT`.**
The authorised Phase C1 re-run ran the read-only preflight and the runtime
readiness **dry-run**, then stopped **before any deposit**. No deposit, no
restore/download, no checksum round-trip, and no object-lock observation were
performed. This is honest fail-closed stop evidence, not success evidence.

- run_id: `phase-c1-365d-ba-rerun`
- generated_at: `2026-07-03T17:31:23Z`
- code_sha: `6ae9655fb36811307a28d9d5b81a202b3da34b2a`
- plan document: `docs/design/t2_execution_plan.md`
- runtime readiness doc: `docs/runbook/t2_r2_runtime_client_readiness.md`
- span_id: `365d_BA` (pilot re-run, one span)
- destination_logical_alias: `T2_PRIMARY_R2` (Cloudflare R2 expected)

## Dry-run result (authoritative stop cause)

Command (as documented): `python scripts/t2_r2_runtime.py --dry-run`

Reported status: **`T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT`** — every required
`T2_PRIMARY_R2_*` env-var **name** is absent (presence-only check; no values
were read, printed, logged, or serialised). The dry-run touched no objects,
deposited nothing, restored nothing, and claimed no round-trip.

Secondary blocker (not reached because credentials short-circuit first):
**boto3 is absent** in this environment, so a real client could not be
constructed even if credentials were present.

## Required runtime configuration (env-var NAMES only)

- Required credentials: `T2_PRIMARY_R2_ACCESS_KEY_ID`,
  `T2_PRIMARY_R2_SECRET_ACCESS_KEY`
- Required config: `T2_PRIMARY_R2_ENDPOINT`, `T2_PRIMARY_R2_BUCKET`
- Optional: `T2_PRIMARY_R2_REGION`, `T2_PRIMARY_R2_OBJECT_PREFIX`,
  `T2_PRIMARY_R2_RETENTION_EXPECTATION`

## Preflight results (read-only)

| Check | Result |
| --- | --- |
| master SHA | `6ae9655` (PR #397 merged) |
| working tree clean before start | yes |
| protected stage24/25 artifacts clean before start | yes |
| `365d_BA` inventory reference present | `raw_inventory_365d_BA.json` (20 file entries) |
| local `365d_BA` candidate bytes present | 20 files |
| expected size / SHA-256 | referenced from committed PR-B.1 inventory (not recomputed) |
| credentials present | **no** (presence-only; no values exposed) |
| boto3 available | **no** |

## Per-span status

| span | deposit | restore | round-trip | object-lock |
| --- | --- | --- | --- | --- |
| `365d_BA` | NOT_PERFORMED | NOT_PERFORMED | NOT_PERFORMED | NOT_OBSERVED |

Reason: `T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT`.

## Non-scope / bindings

Metadata-only evidence. No raw candle rows, no credentials, no secret values, no
personal absolute paths, no environment dumps, no raw archive files. Retention
probe remains unresolved; byte-admissibility not approved; new epoch not
authorised; ML Step 4 not authorised; no real ML run; no production readiness
claim. `730d_BA` and `3650d_BA` were **not** executed. Phase C2 not started. PR
#395 stop evidence under `artifacts/foundation_t2/phase_c1_365d_ba_pilot/` is
unmodified.

## Recommended next decision point

This re-run cannot complete until, in the execution environment: (1) the
required `T2_PRIMARY_R2_*` credentials + config are provisioned securely
(operator, human-side), **and** (2) `boto3` is available (or a custom client
factory is injected). Both are external prerequisites the runtime path already
supports (PRs #396/#397). When both hold, a further explicitly-authorised
Phase C1 re-run can attempt the `365d_BA` deposit → restore → checksum
round-trip; a clean round-trip would then emit
`T2_C1_365D_BA_ROUND_TRIP_EVIDENCE_CREATED`, which this run did not and must
not claim.
