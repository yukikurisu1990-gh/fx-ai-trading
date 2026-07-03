# Runbook — T2_PRIMARY_R2 runtime client readiness

**Status:** `T2_PRIMARY_R2_RUNTIME_CLIENT_READY` /
`T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT` / `T2_PRIMARY_R2_CONFIG_INCOMPLETE` /
`T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED` /
`T2_PRIMARY_R2_DRY_RUN_READY_NO_OBJECTS_TOUCHED`.

This documents the runtime client-construction / dry-run readiness path added so
a **future, separately authorised** Phase C1 re-run can build a real R2 client
and inject it into `resolve_primary_destination(config=..., client=...)`.

**This PR does not:** execute T2, re-run Phase C1, deposit or restore real
bytes, perform a real checksum round-trip, approve byte-admissibility, adopt a
new epoch, authorise ML Step 4, or make PR #395 a T2 success. A real Phase C1
re-run requires **separate human + ChatGPT approval**
(`PHASE_C1_RERUN_NOT_AUTHORISED`; `REAL_T2_EXECUTION_NOT_PERFORMED`).

## What this PR adds

- `scripts/t2_r2_runtime.py` (OUTSIDE the env/network-free `foundation_t2`
  package):
  - `env_presence(env)` / `credentials_present(env)` / `required_config_present(env)`
    — env-var **NAME** presence only.
  - `config_from_env(env)` — builds the **non-secret** `R2DestinationConfig`
    (bucket, endpoint, region, prefix, retention) from env; **never** reads the
    access key or secret into config.
  - `build_runtime_client(env, config=, client_factory=)` — reads credential
    VALUES at the last moment and hands them straight to the client factory;
    returns `None` fail-closed on incomplete creds/config; scrubs any factory
    error (including the exact credential values) before raising.
  - `default_boto3_client_factory(...)` — lazily imports boto3 (NOT a hard
    dependency; fails closed with `T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED` if
    absent) and adapts a boto3 S3 client to the `R2Client` interface. boto3
    client construction does not touch the network; object I/O happens only in
    deposit/restore, which this PR never calls.
  - `resolve_phase_c1_destination(env, config=, client_factory=)` — the
    integration point: builds config + client and returns
    `resolve_primary_destination(config=, client=)`, fail-closed to
    `UnavailableR2Destination` when not ready. Performs NO object I/O.
  - `readiness_report(env, ...)` + `main()` CLI — **dry-run only**: reports
    readiness states, touches no objects, deposits/restores nothing, and never
    prints a credential value.
- `scripts/foundation_t2/constants.py` — three new readiness status constants.
- `tests/foundation_t2/test_r2_runtime.py` — 19 mocked tests (fakes only).

## Required operator configuration (env-var NAMES)

| Role | Env-var name | Required |
| --- | --- | --- |
| Access key ID | `T2_PRIMARY_R2_ACCESS_KEY_ID` | yes (secret) |
| Secret access key | `T2_PRIMARY_R2_SECRET_ACCESS_KEY` | yes (secret) |
| Endpoint URL | `T2_PRIMARY_R2_ENDPOINT` | yes |
| Bucket | `T2_PRIMARY_R2_BUCKET` | yes |
| Region | `T2_PRIMARY_R2_REGION` | optional |
| Object prefix | `T2_PRIMARY_R2_OBJECT_PREFIX` | optional (default `t2`) |
| Object-lock / retention expectation | `T2_PRIMARY_R2_RETENTION_EXPECTATION` | optional |

Values are never logged, printed, or serialised. Only NAME presence appears in
readiness output.

## Dry-run readiness command

```bash
python scripts/t2_r2_runtime.py --dry-run
```

In the current environment (no `T2_PRIMARY_R2` credentials) this reports
`T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT` and touches nothing. It never uploads,
downloads, lists raw data, deposits, restores, mutates objects, or claims
round-trip success.

## How a future authorised Phase C1 re-run wires this

Under explicit human + ChatGPT authorisation, with operator credentials
provisioned securely and boto3 available (or a custom factory injected):

1. `dest = resolve_phase_c1_destination(os.environ)` (default boto3 factory), or
   inject a custom `client_factory` — this returns a real `R2Destination` only
   when credentials + config are complete and the client constructs.
2. Run the existing Phase C harness (`scripts/foundation_t2/roundtrip.py`) for
   `365d_BA` **only**, verify object-lock, recompute + compare checksums against
   committed PR-B.1 inventory, and emit metadata-only evidence.

A clean real round-trip would then emit
`T2_C1_365D_BA_ROUND_TRIP_EVIDENCE_CREATED` — which this support PR did not and
must not claim.
