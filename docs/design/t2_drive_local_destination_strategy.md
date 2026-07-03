# T2 destination strategy amendment — R2 deferred; Google Drive / local-offline next

- **Document class:** doc-only strategy amendment (changes no code, executes nothing)
- **Base:** master `234a1dd` (post PR #398 merge)
- **Branch:** `docs/t2-drive-local-destination-strategy`
- **Amends:** `docs/design/t2_execution_plan.md` (Phase B, `T2_EXECUTION_PLAN_APPROVED`)
  and the destination assumption (`T2_PRIMARY_R2`) in
  `docs/design/gate_p2_retention_destination_evaluation_memo.md`. The Phase B plan's
  procedure, evidence schema, and stop conditions remain valid; only the immediate
  **destination** changes.

## Executive conclusion

- `T2_PRIMARY_R2_DEFERRED_BILLING_AND_OPERATIONAL_RISK`
- `T2_GOOGLE_DRIVE_OR_LOCAL_OFFLINE_SELECTED_FOR_NEXT_DESTINATION_PLAN`
- `T2_EXECUTION_NOT_PERFORMED`
- `BYTE_ADMISSIBILITY_NOT_APPROVED`
- `NEW_EPOCH_NOT_ADOPTED`
- `ML_STEP4_NOT_AUTHORISED`
- `PRODUCTION_READINESS_NOT_CLAIMED`

Forbidden-label note: no part of this memo asserts `BYTE_ADMISSIBLE`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, `PRODUCTION_READY`, `PASS`, `Tier 1`,
or `FORMALLY_VERIFIED`; where those tokens appear they are prohibited outputs.

## 1. Why R2 is deferred (not deleted)

- **The R2 path is technically prepared.** The adapter (PR #396) and runtime
  client-injection + dry-run readiness (PR #397) are merged, mock-tested, and
  fail-closed; a credentialed Phase C1 re-run could use them unchanged.
- **The operator is concerned about unnoticed billing / operational risk.**
  A metered cloud destination introduces the possibility of surprise charges,
  egress costs, or misconfiguration that goes unnoticed between sessions —
  risk the operator has chosen not to carry for the immediate retention probe.
- **R2 remains optional future infrastructure.** PRs #396/#397 stay valid and
  are not removed; R2 can be reinstated later by provisioning credentials and
  authorising a Phase C1 re-run. This amendment changes *which destination is
  immediate*, nothing else.
- **The two R2 stop records (PR #395, PR #398) remain valid** honest
  stop-before-deposit evidence and are not modified by this amendment.

## 2. Candidate destinations

| Alias | Type | Status after this amendment |
| --- | --- | --- |
| `T2_GOOGLE_DRIVE_PRIMARY` | Cloud storage (Google Drive) | Candidate — primary if storage sufficient + completion verifiable |
| `T2_LOCAL_OFFLINE_PRIMARY` | Local/offline external disk | Candidate — primary if zero cloud dependence wanted |
| `T2_LOCAL_OFFLINE_BACKUP` | Second local/offline disk | Candidate — backup copy if a second disk is available |
| `T2_PRIMARY_R2` | Cloudflare R2 | **Deferred** (`T2_PRIMARY_R2_DEFERRED_BILLING_AND_OPERATIONAL_RISK`) — optional future infra |

## 3. Recommended immediate strategy

The recommendation is **operator-selectable**, in this order of preference given
the stated billing/operational-risk concern:

1. **`T2_LOCAL_OFFLINE_PRIMARY` (+ `T2_LOCAL_OFFLINE_BACKUP` if a second disk
   exists) — recommended default.** Zero cloud dependence, zero billing risk,
   simplest to reason about, and a second disk gives immediate disaster-recovery
   redundancy. This most directly answers the operator's concern.
2. **`T2_GOOGLE_DRIVE_PRIMARY` — recommended only if** the operator wants an
   off-site copy **and** Drive storage is sufficient for the span **and**
   upload/download completion can be verified end-to-end (checksum after
   round-trip). Drive has no per-GB egress billing surprise like metered object
   storage, but it introduces API/quota and share-scope considerations.
3. **Both** — local/offline primary for the authoritative copy, Google Drive as
   an off-site secondary — is the strongest disaster-recovery posture and is a
   reasonable operator choice if Drive verification is solved.

This memo does not pick one on the operator's behalf; it recommends the ordering
and states the acceptance conditions. The Phase C1 execution-plan PR (see §9)
fixes the concrete choice.

## 4. Future Google Drive Phase C1 pilot procedure (`365d_BA`) — DEFINED, NOT EXECUTED

For the pilot span `365d_BA` only, a future authorised run would:

1. resolve local candidate bytes for `365d_BA` (by inventoried basename);
2. verify inventory references against committed PR-B.1 metadata
   (`artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json`);
3. **(archive mode only)** create a *deterministic* archive of the 20 files
   (sorted entries, pinned/zeroed mtimes, no host metadata) so the archive
   SHA-256 is reproducible;
4. compute SHA-256 + size **before** upload (per file in file-preserving mode;
   of the archive in archive mode);
5. upload to Drive under a deterministic, non-secret logical path;
6. download/restore to an **isolated temp folder** (never over the local
   candidate bytes, never under `data/` or `artifacts/`);
7. recompute SHA-256 + size of the restored bytes;
8. compare restored vs expected (per-file inventory, or archive SHA + inner
   manifest);
9. commit **metadata-only** evidence (schema §6) — no raw files, no Drive
   share link exposing private details.

Two modes:
- **File-preserving mode.** Each of the 20 files is uploaded and round-tripped
  individually; comparison is per-file against the PR-B.1 inventory SHA-256.
  Pro: directly checks the exact inventoried bytes; no archive-determinism
  concern. Con: 20 upload/download legs; more API calls.
- **Archive mode with inner manifest.** The 20 files are packed into one
  deterministic archive carrying an inner manifest (per-file logical id + size
  + SHA-256); the archive is round-tripped once and its SHA-256 compared, then
  the inner manifest is checked against the PR-B.1 inventory. Pro: one
  round-trip leg; atomic. Con: requires deterministic archiving (sorted order,
  fixed timestamps) or the archive SHA is not reproducible.

## 5. Future local/offline Phase C1 pilot procedure (`365d_BA`) — DEFINED, NOT EXECUTED

For the pilot span `365d_BA` only, a future authorised run would:

1. resolve local candidate bytes + verify inventory references (as §4.1–4.2);
2. compute expected SHA-256 + size (or archive SHA in archive mode);
3. copy to the external disk/folder (`T2_LOCAL_OFFLINE_PRIMARY`);
4. **(optional)** copy to the backup disk (`T2_LOCAL_OFFLINE_BACKUP`);
5. **eject/unmount** the disk(s) and record the unmount status (the local
   analogue of "upload completion");
6. re-mount and restore to an **isolated temp folder**;
7. recompute SHA-256 + size of the restored bytes;
8. compare restored vs expected;
9. commit **metadata-only** evidence (schema §6). No personal absolute paths —
   only a scrubbed destination logical id (e.g. `T2_LOCAL_OFFLINE_PRIMARY`),
   never a drive letter or user path.

## 6. Metadata-only evidence schema (future Drive/local Phase C1)

Per span, at minimum:

- destination alias (`T2_GOOGLE_DRIVE_PRIMARY` / `T2_LOCAL_OFFLINE_PRIMARY` / …);
- destination mode (`file_preserving` | `archive`);
- scrubbed destination logical id (never a drive letter, user path, or Drive
  share URL with private detail);
- span id (`365d_BA`);
- file count;
- expected sizes;
- expected SHA-256 references (from committed PR-B.1 inventory);
- archive SHA-256 (archive mode only) + inner-manifest reference;
- restored SHA-256 values;
- checksum comparison result (match / mismatch);
- backup copy status (`T2_LOCAL_OFFLINE_BACKUP` written / not written);
- Drive upload/download completion status **or** disk eject/unmount status;
- object-lock / immutability observation, or explicit "not applicable / not
  observed" for destinations without object lock;
- scrub/cleanliness result;
- non-authorisation statements.

Evidence must **not** include: raw files; raw data rows; personal absolute
paths; Google credentials; Drive share links exposing private details;
environment dumps.

## 7. Destination comparison (R2 vs Google Drive vs local/offline)

| Dimension | `T2_PRIMARY_R2` (deferred) | `T2_GOOGLE_DRIVE_PRIMARY` | `T2_LOCAL_OFFLINE_PRIMARY` |
| --- | --- | --- | --- |
| Billing risk | **Metered** — egress/storage surprise possible (the deferral driver) | Low/flat (quota-based; no per-GB egress bill) | **None** |
| Operator complexity | Bucket + keys + endpoint + object-lock config | Google account + API/OAuth + quota | Plug in a disk; copy/eject |
| Object-lock / immutability | **Supported** (compliance/retention) | Weak (version history, not true WORM) | None (relies on physical control / read-only media) |
| Restore verification | Strong (head + download + checksum) | Adequate (download + checksum) if completion verified | Strong (copy + checksum); depends on disk health |
| Disaster recovery | Off-site, durable | Off-site, durable | On-site unless a second/rotated disk is used |
| Accidental overwrite risk | Low (object-lock) | Medium (same-name overwrite; version history mitigates) | Medium (filesystem overwrite) — mitigate with read-only / write-once folders |
| Automation difficulty | Moderate (SDK/creds) | Moderate (OAuth/API) | Low (filesystem) but manual mount/eject steps |
| Privacy / credential risk | Access key + secret; leak risk | OAuth token / service account; share-scope risk | Minimal (no cloud creds); physical-custody risk instead |

Net: for the immediate probe under a billing/operational-risk constraint,
**local/offline scores best on billing and privacy**, Google Drive adds off-site
durability at the cost of API/quota/share complexity, and R2's main advantage
(true object-lock) is exactly the capability the operator has chosen to defer.

## 8. Gate implications

- Changing the destination strategy **does not undo PR #395 / PR #398** — they
  remain valid stop-before-deposit evidence for the R2 attempts.
- **PR #396 / PR #397 remain valid, optional future R2 infrastructure** — not
  deleted, reusable when/if R2 is reinstated.
- A Drive/local Phase C1 round-trip **can satisfy the immediate T2
  deposit/restore/checksum gate** *if and only if* human + ChatGPT reviews and
  accepts the metadata-only evidence.
- **Even a successful Drive/local T2 does not** approve byte-admissibility, does
  not adopt a new epoch, does not authorise ML Step 4, and does not claim
  production readiness. Those remain separate, later gates
  (roadmap Phases D → E → F → …). A destination that lacks true object-lock
  (Drive/local) may also constrain what the Phase D byte-admissibility review is
  willing to conclude about immutability — a point for that review, not this
  memo.

## 9. Recommended next PR sequence

1. **This destination-strategy amendment PR** (doc-only).
2. **Optional Fable 5 review** of this amendment.
3. **Phase C1 Drive/local execution-plan PR** (doc-only) — fixes the concrete
   destination choice (local primary ± Drive/backup), the mode
   (file-preserving vs archive), credential/mount handling, and stop conditions.
4. **Phase C1 `365d_BA` Drive/local pilot evidence PR** — credential/disk-enabled;
   runs the §4 or §5 procedure for `365d_BA` only; metadata-only evidence;
   requires explicit human + ChatGPT authorisation before execution.
5. **Human + ChatGPT review** of the pilot evidence.
6. **Then decide** whether to expand to `730d_BA` / `3650d_BA` (Phase C2) — not
   before a clean pilot review.

## 10. Non-authorisation statements

This amendment does **not**: execute T2; copy data; upload to Google Drive;
write to local/offline disk; run deposit/restore/checksum; approve
byte-admissibility; adopt a new epoch; authorise ML Step 4; run a real ML
experiment; claim production readiness; promote or demote Phase 9.16;
rehabilitate historical Phase 9.X numerics; or modify the PR #395 / PR #398 stop
evidence. It is a planning document only.
