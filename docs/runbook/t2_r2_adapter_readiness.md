# Runbook — T2_PRIMARY_R2 adapter readiness

**Status:** `T2_PRIMARY_R2_ADAPTER_WIRED_FOR_FUTURE_USE` /
`T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS` /
`T2_PRIMARY_R2_MOCK_ROUNDTRIP_TESTED`.

This runbook documents the support adapter added so a **future, separately
authorised** Phase C1 re-run can attempt the `365d_BA` deposit / restore /
checksum round-trip against `T2_PRIMARY_R2`. It does **not** execute T2.

## What this PR does

- Adds `scripts/foundation_t2/r2_adapter.py`:
  - `R2DestinationConfig` — non-secret config (bucket alias, endpoint, region,
    object prefix, retention expectation). Contains no access key / secret.
  - `credentials_present(env)` / `config_env_present(env)` — **presence-only**
    checks over env-var NAMES. The package never reads a value and never reads
    the process environment itself; the caller injects `env`.
  - `readiness_status(env, config, client)` — returns a precise, **non-success**
    status: `T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT`,
    `T2_PRIMARY_R2_CONFIG_INCOMPLETE`, or `T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS`
    (only when a fake/real client is injected alongside complete config).
  - `build_object_key(...)` — deterministic, prefix-confined object keys
    (`t2/phase_c1/365d_BA/<sanitised-basename>[/<sha-prefix>]`); rejects
    personal paths, secrets, path escape, and (for `phase_c1`) the expansion
    spans unless explicitly overridden.
  - `R2Destination(Destination)` — a real-shaped adapter driven by an
    **injected, duck-typed client**; all client errors are caught and re-raised
    as `DestinationUnavailableError` with **scrubbed** messages.
  - `scrub_error_text(...)` — redacts signed URLs / bearer tokens / local paths
    from any error string before it can surface.
- Adds `observe_object_lock(...)` to the `Destination` base (default:
  `T2_PRIMARY_R2_OBJECT_LOCK_NOT_OBSERVED`); the R2 adapter overrides it.
- Extends `resolve_primary_destination(config=..., client=...)`: fail-closed to
  `UnavailableR2Destination` unless **both** a complete config and a runtime
  client are explicitly injected. The no-argument call is unchanged
  (still returns `UnavailableR2Destination`).
- Adds `tests/foundation_t2/test_r2_adapter.py` — 30 mocked tests over a fake
  in-memory client (missing/partial creds → fail closed, config missing → fail
  closed, deposit/observe/restore/checksum match + mismatch, error scrubbing,
  object-lock observed/not-observed, deterministic keys, no-personal-path,
  no-secret-in-key/report, expansion-span rejection).

## Hard boundaries (what this PR does NOT do)

- **No real cloud access, no real deposit, no real restore, no real checksum
  round-trip.** No cloud SDK is imported; all I/O is through the injected client
  (a fake in tests).
- **No credential value is read, printed, logged, or serialised.** Credential
  checks are env-var NAME presence only, over a caller-injected mapping; the
  `foundation_t2` package remains env-free and network-free (enforced by the
  existing `test_harness_does_not_read_env_or_network` guard).
- **`REAL_T2_EXECUTION_NOT_PERFORMED`; `PHASE_C1_RERUN_NOT_AUTHORISED`.** PR #395
  remains stop-before-deposit evidence — it is **not** made a T2 success, and it
  is not modified.
- No byte-admissibility approval; no new-epoch adoption; no ML Step 4
  authorisation; no real ML run; no production-readiness claim; Phase 9.16
  neither promoted nor demoted; historical Phase 9.X numerics not rehabilitated.

## How a future authorised Phase C1 re-run would use this

Outside this package, under explicit human + ChatGPT authorisation and with
operator-provisioned credentials made available securely:

1. Build a real R2 client (S3/R2-compatible: `put_object`, `head_object`,
   `get_object`/download, `get_object_retention`) from the operator credentials
   — **in the runner, not in this package**.
2. Build an `R2DestinationConfig` (bucket alias, endpoint, region, object
   prefix `t2`, retention expectation).
3. Confirm `readiness_status(env=os.environ, config=cfg, client=real_client)`
   returns `T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS`-shaped readiness (real
   client), then obtain the destination via
   `resolve_primary_destination(config=cfg, client=real_client)`.
4. Run the Phase C harness round-trip for `365d_BA` **only**, verify object-lock
   via `observe_object_lock`, recompute + compare checksums against committed
   PR-B.1 inventory, and emit metadata-only evidence.

A clean real round-trip would then emit
`T2_C1_365D_BA_ROUND_TRIP_EVIDENCE_CREATED` — which this support PR did not and
must not claim.
