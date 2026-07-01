# Foundation T2 retention deposit + round-trip report

- run_id: `t2-all-spans-20260702`
- destination_logical_alias: `T2_PRIMARY_R2`
- target_spans: 365d_BA, 730d_BA, 3650d_BA
- top_level_status: `T2_EXECUTION_STOPPED_BEFORE_DEPOSIT`
- real_cloud_deposit_status: `T2_EXECUTION_STOPPED_BEFORE_DEPOSIT`

## Per-span status

| span | deposit | restore | round-trip |
| --- | --- | --- | --- |
| 365d_BA | NOT_PERFORMED | NOT_PERFORMED | NOT_PERFORMED |
| 730d_BA | NOT_PERFORMED | NOT_PERFORMED | NOT_PERFORMED |
| 3650d_BA | NOT_PERFORMED | NOT_PERFORMED | NOT_PERFORMED |

## Non-scope

Metadata-only evidence. No raw rows, credentials, env values, signed URLs, tokens, or local absolute paths. No byte-admissibility approval, no new-epoch adoption, no ML Step 4, no production change, no model / backtest / trading metric. Backup HDD and IPFS sidecar NOT executed (deferred). Harness round-trip mechanics are validated synthetically in tests; no real cloud round-trip was performed here.
