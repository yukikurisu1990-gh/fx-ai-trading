# Foundation T2 — Phase C1 pilot (span `365d_BA`) — pre-deposit stop evidence

**Status: `T2_C1_STOPPED_BEFORE_DEPOSIT_CREDENTIALS_UNAVAILABLE_OR_UNSAFE`.**
The read-only preflight ran and stopped **before any deposit**. No deposit, no
restore/download, no checksum round-trip, and no object-lock observation were
performed. This is honest fail-closed stop evidence, not success evidence.

- run_id: `phase-c1-365d-ba-pilot`
- generated_at: `2026-07-03T16:37:26Z`
- code_sha: `24b08b3bfda36f3e3f08321f6f7cf3cfd8ea41d3`
- plan document: `docs/design/t2_execution_plan.md`
- span_id: `365d_BA` (pilot, one-span)
- destination_logical_alias: `T2_PRIMARY_R2` (Cloudflare R2 expected)

## Why the stop occurred (three independent fail-closed signals)

1. **Credentials unavailable.** A presence-only check over candidate credential
   env-var names (`T2_PRIMARY_R2_*`, `R2_*`, `AWS_*`, `CLOUDFLARE_R2_TOKEN`,
   `T2_PRIMARY_R2`) returned **all unset**. No values were read, printed, logged,
   or captured — only the boolean presence of each variable name.
2. **Harness fails closed.** `scripts/foundation_t2/destination.py`'s
   `resolve_primary_destination()` returns `UnavailableR2Destination`, which raises
   `DestinationUnavailableError(T2_CREDENTIALS_UNAVAILABLE)` on any deposit / observe
   / restore. No real R2 adapter is wired, so there is no code path that could
   deposit.
3. **Inventory not authorised.** The committed PR-B.1 inventory
   (`artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json`) records
   `t2_execution_authorised: false` for this candidate.

## Preflight results (read-only)

| Check | Result |
| --- | --- |
| master SHA | `24b08b3` (PR #394 merged) |
| plan doc `t2_execution_plan.md` present | yes |
| `T2_EXECUTION_PLAN_APPROVED` token on master | yes |
| working tree clean before start | yes |
| protected stage24/25 artifacts clean before start | yes |
| `365d_BA` inventory reference present | `raw_inventory_365d_BA.json` (20 file entries) |
| local `365d_BA` candidate bytes present | 20 files |
| expected size / SHA-256 | referenced from committed PR-B.1 inventory (not recomputed) |
| credentials present | **no** (presence-only; no values exposed) |
| destination alias resolvable | **no** (harness returns UnavailableR2Destination) |
| object-lock / retention observable | **no** (no destination access) |

## Per-span status

| span | deposit | restore | round-trip | object-lock |
| --- | --- | --- | --- | --- |
| `365d_BA` | NOT_PERFORMED | NOT_PERFORMED | NOT_PERFORMED | NOT_OBSERVED |

Reason: `T2_CREDENTIALS_UNAVAILABLE`.

## Non-scope / bindings

Metadata-only evidence. No raw candle rows, no credentials, no secret values, no
personal absolute paths, no environment dumps, no raw archive files. Retention
probe remains unresolved; byte-admissibility not approved; new epoch not
authorised; ML Step 4 not authorised; no real ML run; no production readiness
claim. `730d_BA` and `3650d_BA` were **not** executed (out of Phase C1 scope and
out of scope entirely here). Phase C2 not started. No cloud, network, or
credential access occurred beyond confirming credential absence by env-var name
presence.

## Recommended next decision point

This pilot cannot complete until **operator-provisioned credentials for
`T2_PRIMARY_R2` are made available securely** (an external, human-side action per
the plan §6 and roadmap §9) **and** a real R2 adapter is wired into
`resolve_primary_destination()` under those credentials. When both hold, re-run
Phase C1 for `365d_BA` only; a clean round-trip would then emit
`T2_C1_365D_BA_ROUND_TRIP_EVIDENCE_CREATED`, which this run did not and must not
claim.
