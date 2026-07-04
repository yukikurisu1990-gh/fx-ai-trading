# Phase D — `365d_BA` byte-admissibility acceptance record

- **Document class:** doc-only decision record (records a human + ChatGPT
  acceptance; authorises nothing beyond what it states)
- **Base:** master `816b431` (post PR #404 merge)
- **Branch:** `docs/phase-d-365d-ba-byte-admissibility-acceptance-record`
- **Records the acceptance of:** the Fable 5 Phase D recommendation
  (`docs/design/phase_d_365d_ba_byte_admissibility_review_fable5.md`, PR #404,
  `PHASE_D_365D_BA_BYTE_ADMISSIBILITY_RECOMMENDED_FOR_HUMAN_ACCEPTANCE`).
- **Decision maker:** human + ChatGPT (recorded here; this document is the
  durable record of that decision, authored under their instruction).

## Acceptance status

**`PHASE_D_365D_BA_BYTE_ADMISSIBILITY_ACCEPTANCE_RECORDED_FOR_LATER_EXPERIMENT_PRE_REGISTRATION`**

Also binding: `NEW_EPOCH_NOT_ADOPTED` · `ML_STEP4_NOT_AUTHORISED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: this record does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `BYTE_ADMISSIBILITY_APPROVED`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; those tokens
appear only as prohibitions.

## 1. Executive acceptance decision

- Human + ChatGPT acceptance **is recorded** for `365d_BA` byte-admissibility.
- This means the committed `365d_BA` bytes / checksums **may be used as
  admissible inputs for later experiment pre-registration**.
- This does **not** adopt a new epoch.
- This does **not** authorise ML Step 4.
- This does **not** authorise ML training or backtests.
- This does **not** include `730d_BA` or `3650d_BA`.

## 2. Accepted evidence basis

The acceptance rests on the evidence chain currently committed on master:

- **Independent PR-B.1 committed inventory**
  (`artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json`) — 20
  files with per-file SHA-256 + size, committed before any Phase C evidence.
- **PR #401 local/offline round-trip evidence** — 20 files, 1,481,715,517 bytes,
  `MATCH_ALL_20_FILES` (restored SHA-256 + size == inventory for all 20).
- **PR #402 Fable 5 Phase C1 acceptance audit** — no blockers for Phase C1
  acceptance.
- **PR #403 local/offline hardening** — `T2_LOCAL_OFFLINE_BACKUP` second copy
  verified (`MATCH_ALL_20_FILES`); 3-file spot-rehash matched both inventory and
  PR #401 evidence.
- **PR #404 Fable 5 Phase D recommendation review** — recommended human
  acceptance; blockers found: none.

## 3. Scope boundaries

**Accepted:**
- `365d_BA` **only**;
- the current committed bytes / checksums / inventory / evidence chain;
- use as a later-experiment pre-registration **input candidate**.

**Not accepted:**
- `730d_BA`; `3650d_BA`; all-span T2 completion;
- new epoch adoption; ML Step 4; ML training/backtests;
- production readiness;
- historical Phase 9.X metric rehabilitation;
- Phase 9.16 promotion/demotion.

## 4. Residual risks retained

The following local/offline limitations are carried forward and **accepted as
non-blocking for `365d_BA` byte-admissibility acceptance**, but **must remain
visible in downstream reports and later gates**:

- no true object-lock / WORM immutability (R2);
- local-admin overwrite possibility (R3);
- physical disk loss / damage / substitution risk (R4);
- local/offline is weaker than cloud object-lock for formal archival claims;
- all-span incompleteness (`730d_BA` / `3650d_BA` not yet retained/restored);
- the spot-rehash covered 3 of 20 restored files, not a full independent rehash.

## 5. Conditions attached to acceptance

- This acceptance applies **only to `365d_BA`**.
- `730d_BA` and `3650d_BA` require **separate Phase C evidence and later review**
  before inclusion.
- Any experiment consuming `365d_BA` should **re-verify checksums immediately
  before use** (mitigates R3).
- Local/offline limitations **must be disclosed in downstream experiment
  reports**.
- **New epoch adoption requires a separate Phase E decision.**
- **ML Step 4 requires a separate Phase F pre-registration gate.**
- This acceptance **does not validate profitability**.
- This acceptance **does not rehabilitate historical Phase 9.X metrics**.
- This acceptance **does not promote or demote Phase 9.16**.

## 6. Recommended next gate

- **Next gate: Phase E — `365d_BA` new-epoch adoption decision PR** (a
  research-only, frozen-holdout epoch record binding the accepted bytes together
  with the F-2/F-5/F-8 contracts and the local/offline limitation).
- **Phase E is not started by this PR** and must be **separately authorised**.
- **Phase F / ML Step 4 must remain blocked** until Phase E and a separate
  pre-registration gate are complete.
- **Phase C2** (`730d_BA` / `3650d_BA` local/offline round-trips) may proceed
  **independently later** if the operator wants to broaden retention evidence;
  it is not required for the `365d_BA`-only path and is not started here.

## 7. Non-authorisation statements

This PR does **not**: access raw data; access external disks; access Google
Drive; access R2; rerun copy/restore/checksum; start Phase C2; include
`730d_BA`; include `3650d_BA`; adopt a new epoch; authorise ML Step 4; run ML
training; run backtests; or claim production readiness. It is a decision record
only.
