# Phase C1 — `365d_BA` local/offline execution plan (pilot)

- **Document class:** doc-only execution plan (defines the future pilot; executes nothing)
- **Base:** master `85c768e` (post PR #399 merge)
- **Branch:** `docs/phase-c1-local-offline-execution-plan`
- **Governing docs:** `docs/design/t2_drive_local_destination_strategy.md` (destination
  amendment, PR #399), `docs/design/t2_execution_plan.md` (Phase B,
  `T2_EXECUTION_PLAN_APPROVED`), `docs/design/post_remediation_t2_ml_step4_roadmap.md`
  (Phase C gate).

## Executive conclusion

- `PHASE_C1_LOCAL_OFFLINE_EXECUTION_PLAN_CREATED`
- `T2_LOCAL_OFFLINE_PRIMARY_SELECTED_FOR_365D_BA_PILOT`
- `T2_EXECUTION_NOT_PERFORMED`
- `BYTE_ADMISSIBILITY_NOT_APPROVED`
- `NEW_EPOCH_NOT_ADOPTED`
- `ML_STEP4_NOT_AUTHORISED`
- `PRODUCTION_READINESS_NOT_CLAIMED`

Forbidden-label note: no part of this memo asserts `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY`, `PASS`, `Tier 1`, or `FORMALLY_VERIFIED`; where those tokens
appear they are prohibited outputs.

## 1. Executive recommendation

The immediate Phase C1 pilot will use:

- **span:** `365d_BA` (pilot only);
- **primary destination alias:** `T2_LOCAL_OFFLINE_PRIMARY`;
- **optional backup destination alias:** `T2_LOCAL_OFFLINE_BACKUP`;
- **mode:** local/offline copy → restore → checksum round-trip;
- **Google Drive:** optional future off-site backup only — **not used** in this
  immediate plan;
- **R2:** deferred (`T2_PRIMARY_R2_DEFERRED_BILLING_AND_OPERATIONAL_RISK`).

**This plan does not execute T2.** It defines exactly how a later,
separately-authorised pilot will run.

## 2. Preconditions for future execution

Future human/operator prerequisites (all must hold before the pilot runs):

- an external SSD/HDD (or equivalent local/offline destination) is available;
- the destination has enough free space for the `365d_BA` file set;
- the destination path is provided as an **alias** (`T2_LOCAL_OFFLINE_PRIMARY`),
  never committed as a personal absolute path;
- (optional) a second disk/folder is available if using `T2_LOCAL_OFFLINE_BACKUP`;
- a restore temp directory exists **outside** the source data tree and outside
  the destination tree;
- the working tree is clean;
- protected stage24/stage25 artifacts are clean;
- `365d_BA` inventory references are available
  (`artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json`).

## 3. Destination alias policy

- `T2_LOCAL_OFFLINE_PRIMARY` — the authoritative local/offline copy target.
- `T2_LOCAL_OFFLINE_BACKUP` — optional second local/offline copy target.

Rules:

- evidence must use **aliases**, never personal absolute paths;
- a disk label / logical id may be recorded **only if scrubbed** (no username,
  no drive letter, no home path);
- no user-home paths in evidence;
- no raw data paths committed;
- no environment dumps.

## 4. File-preserving vs archive mode

### File-preserving mode
- Copies the original file tree (the 20 `candles_*_M1_365d_BA.jsonl` files).
- Verifies **per-file** SHA-256 + size against the committed PR-B.1 inventory.
- Better mirrors the source inventory — the exact inventoried bytes are checked
  one-to-one.
- More files to manage (20 copy + 20 restore legs).

### Archive mode
- Creates a **deterministic** archive of `365d_BA` (sorted entries, pinned/zeroed
  mtimes, no host metadata) with an inner manifest (per-file logical id + size +
  SHA-256).
- Easier to copy manually (one object).
- Requires archive SHA-256 **plus** inner-manifest verification against the
  PR-B.1 inventory.
- Slightly weaker unless extraction and the inner manifest are both checked; the
  archive SHA is only meaningful if archiving is byte-deterministic.

**Recommendation: file-preserving mode** for the immediate local/offline pilot —
the current inventory is per-file SHA-256, a plain filesystem copy handles 20
files cleanly, and per-file comparison directly checks the inventoried bytes
with no archive-determinism caveat. Fall back to **archive mode only if**
file-preserving copy becomes operationally awkward (e.g. many small files across
a slow removable medium), in which case deterministic archiving + inner-manifest
verification is mandatory.

## 5. Future execution procedure (defined, NOT executed)

For the pilot span `365d_BA` only, a future authorised run would:

1. resolve `365d_BA` local candidate bytes (by inventoried basename);
2. verify committed inventory references (PR-B.1 `raw_inventory_365d_BA.json`);
3. compute or verify expected file count (20), sizes, and SHA-256 references;
4. copy `365d_BA` bytes to `T2_LOCAL_OFFLINE_PRIMARY`;
5. (optional) copy the same bytes to `T2_LOCAL_OFFLINE_BACKUP`;
6. (optional) eject/unmount or otherwise mark the destination copy offline, and
   record the unmount status;
7. restore/copy back from `T2_LOCAL_OFFLINE_PRIMARY` to an **isolated temp
   restore folder** (outside the source tree and outside the destination tree);
8. recompute restored file sizes + SHA-256 values;
9. compare restored bytes against the expected inventory references;
10. produce **metadata-only** evidence (schema §6);
11. scrub evidence for personal paths, raw data rows, raw file contents, and
    environment dumps (fail-closed scanner);
12. confirm no raw data is committed;
13. confirm protected stage24/stage25 artifacts remain clean.

## 6. Evidence schema (metadata-only)

Future evidence directory: `artifacts/foundation_t2/phase_c1_365d_ba_local_offline/`

Expected files:
- `t2_phase_c1_365d_ba_local_manifest.json`
- `t2_phase_c1_365d_ba_local_roundtrip_report.json`
- `t2_phase_c1_365d_ba_local_roundtrip_report.md`
- `t2_phase_c1_365d_ba_local_cleanliness_report.json`

Evidence may include: execution timestamp; code SHA; plan document reference;
span id (`365d_BA`); destination alias (`T2_LOCAL_OFFLINE_PRIMARY`); optional
backup alias (`T2_LOCAL_OFFLINE_BACKUP`); destination mode (local/offline,
file-preserving); file count; expected sizes; expected SHA-256 references;
copied sizes; restored sizes; restored SHA-256 values; checksum comparison
result; backup copy status; disk eject/unmount/offline status if performed;
cleanliness/scrub status; non-authorisation statements.

Evidence must **not** include: raw data files; raw data rows; personal absolute
paths; user home directories; environment dumps; credentials or secrets; Google
Drive links; R2 object keys.

## 7. Stop conditions

Future execution must stop (fail closed, report honestly) if any of:

- `365d_BA` inventory references are missing or ambiguous;
- the destination path is not provided safely (would require committing a
  personal absolute path);
- destination free space is insufficient;
- copy fails;
- restore fails;
- checksum mismatch occurs;
- the restore temp directory is inside the source tree or the destination tree;
- evidence would contain personal paths or raw data;
- protected stage24/stage25 artifacts become dirty;
- `data/` or raw `artifacts/` would be committed;
- execution attempts `730d_BA` or `3650d_BA`;
- execution attempts Google Drive or R2;
- any status tries to approve byte-admissibility, new epoch, ML Step 4, or
  production readiness.

## 8. Future execution statuses

Allowed **success** status (only after a real copy → restore → checksum match on
scrubbed evidence): `T2_C1_365D_BA_LOCAL_OFFLINE_ROUND_TRIP_EVIDENCE_CREATED`.

Allowed **stop/failure** statuses:
- `T2_C1_LOCAL_OFFLINE_STOPPED_BEFORE_COPY_DESTINATION_UNAVAILABLE`
- `T2_C1_LOCAL_OFFLINE_STOPPED_BEFORE_COPY_INVENTORY_AMBIGUOUS`
- `T2_C1_LOCAL_OFFLINE_COPY_FAILED`
- `T2_C1_LOCAL_OFFLINE_RESTORE_FAILED`
- `T2_C1_LOCAL_OFFLINE_CHECKSUM_MISMATCH`
- `T2_C1_LOCAL_OFFLINE_EVIDENCE_SCRUB_FAILED`

Do not claim success if restore did not occur, checksum comparison did not
occur, or evidence scrub failed.

## 9. Gate implications

- A **successful** local/offline Phase C1 pilot **may satisfy the immediate T2
  deposit/restore/checksum evidence need for `365d_BA`** — only if human +
  ChatGPT review accepts the metadata-only evidence.
- It does **not** approve byte-admissibility.
- It does **not** adopt a new epoch.
- It does **not** authorise ML Step 4.
- It does **not** claim production readiness.
- It does **not** automatically authorise Phase C2 (`730d_BA` / `3650d_BA`).
- It does **not** invalidate the deferred R2 path (PRs #396/#397 remain valid
  optional infra; PRs #395/#398 remain valid R2 stop evidence).
- Note: a local/offline destination provides no true object-lock / WORM
  immutability; that limitation is a point for the later Phase D
  byte-admissibility review, not for this plan.

## 10. Recommended next decision point

If this plan is accepted and merged, the next PR is the **Phase C1 `365d_BA`
local/offline pilot evidence PR**:
- evidence-only;
- executes copy → restore → checksum for `365d_BA` **only**;
- no Google Drive; no R2; no `730d_BA`; no `3650d_BA`;
- **requires human + ChatGPT approval before execution.**

## 11. Non-authorisation statements

This PR does **not**: execute T2; copy data; write to local/offline disk; upload
to Google Drive; access R2; approve byte-admissibility; adopt a new epoch;
authorise ML Step 4; run real data; train a model; claim production readiness;
rehabilitate historical Phase 9.X numerics; or promote/demote Phase 9.16. It is
a planning document only.
