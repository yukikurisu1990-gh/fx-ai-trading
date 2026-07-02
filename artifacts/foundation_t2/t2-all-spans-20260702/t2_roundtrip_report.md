# Foundation T2 round-trip harness + pre-deposit stop evidence

**Execution stopped before deposit.** No deposit, no restore/download, and no round-trip verification were performed; the retention probe remains unresolved. This PR delivers the T2 harness and honest pre-deposit stop evidence only.

- run_id: `t2-all-spans-20260702`
- destination_logical_alias: `T2_PRIMARY_R2`
- target_spans: 365d_BA, 730d_BA, 3650d_BA
- top_level_status: `T2_EXECUTION_STOPPED_BEFORE_DEPOSIT`
- real_cloud_deposit_status: `T2_EXECUTION_STOPPED_BEFORE_DEPOSIT`
- retention_probe_status: `RETENTION_PROBE_REMAINS_UNRESOLVED`

## Per-span status

| span | deposit | restore | round-trip |
| --- | --- | --- | --- |
| 365d_BA | NOT_PERFORMED | NOT_PERFORMED | NOT_PERFORMED |
| 730d_BA | NOT_PERFORMED | NOT_PERFORMED | NOT_PERFORMED |
| 3650d_BA | NOT_PERFORMED | NOT_PERFORMED | NOT_PERFORMED |

## SHA-256 provenance

SHA-256 values in the manifest are copied verbatim from committed PR-B.1 metadata; they were not recomputed in this PR and no raw candidate bytes were read.

## Non-scope

Metadata-only evidence. No raw rows, credentials, env values, signed URLs, tokens, or local absolute paths. Retention probe remains unresolved; byte-admissibility not approved; new epoch not authorised; ML Step 4 not authorised. No production change, no model / backtest / trading metric. Backup HDD and IPFS sidecar NOT executed (deferred). Harness round-trip mechanics are validated synthetically in tests; no real cloud round-trip was performed here.
