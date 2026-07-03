# Phase C1 `365d_BA` local/offline evidence — adversarial acceptance audit (Fable 5)

- **Document class:** doc-only, read-only acceptance audit (changes nothing; approves
  only what its conclusion states)
- **Auditor:** Fable 5 (adversarial review; independent cross-checks against
  committed references, not restatement of PR #401's own claims)
- **Base:** master `49e3d6f` (post PR #401 merge)
- **Branch:** `docs/phase-c1-365d-ba-local-offline-acceptance-audit`
- **Audited evidence:** `artifacts/foundation_t2/phase_c1_365d_ba_local_offline/`
  (PR #401, merge `49e3d6f`)
- **Reviewed context:** PR #399 destination strategy
  (`t2_drive_local_destination_strategy.md`), PR #400 execution plan
  (`phase_c1_365d_ba_local_offline_execution_plan.md`), committed PR-B.1 inventory
  (`artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json`).
- **Method constraints honoured:** no raw data read or copied; no external disk,
  Google Drive, or R2 access; no copy/restore/checksum rerun; no ML training or
  backtests. All verification was over committed repository metadata.

## Audit conclusion

**`PHASE_C1_365D_BA_LOCAL_OFFLINE_EVIDENCE_ACCEPTABLE_FOR_C1_PILOT`**

Also binding: `BYTE_ADMISSIBILITY_NOT_APPROVED` · `NEW_EPOCH_NOT_ADOPTED` ·
`ML_STEP4_NOT_AUTHORISED` · `PRODUCTION_READINESS_NOT_CLAIMED`.

**Accepted (recommended for human + ChatGPT acceptance):** the `365d_BA`
local/offline copy → restore → checksum evidence, as satisfying the immediate
Phase C1 pilot evidence need.

**Not accepted / not authorised by this audit:** T2 all-span completion;
Phase C2 (`730d_BA`, `3650d_BA`); byte-admissibility; new epoch adoption;
ML Step 4; ML training/backtests; production readiness.

Forbidden-label note: this audit does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `BYTE_ADMISSIBILITY_APPROVED`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; those tokens
appear only as prohibitions.

## Answers to the required audit questions

1. **Metadata-only evidence directory?** Yes. The directory contains exactly the
   four expected files (manifest, roundtrip json, roundtrip md, cleanliness
   report) — 483 committed lines total, all metadata (basenames, sizes,
   SHA-256 values, statuses). No raw files, no payload data.
2. **File count of 20 supported?** Yes. Manifest `expected_file_count` = 20 with
   20 entries; roundtrip report `file_count` = 20 with 20 per-file records; the
   independently-committed PR-B.1 inventory also lists exactly 20 files, and the
   three sets of `logical_file_id`s coincide.
3. **Expected vs restored totals match?** Yes. Inventory-summed total =
   manifest `expected_total_bytes` = roundtrip `expected_total_bytes` =
   roundtrip `restored_total_bytes` = **1,481,715,517 bytes**, recomputed by this
   audit from the inventory rather than taken from PR #401's text.
4. **Per-file restored SHA-256 vs committed expected inventory?** Yes —
   **independently cross-checked**: for every one of the 20 files, the evidence's
   `expected_sha256`, `restored_sha256`, AND the manifest `sha256` all equal the
   PR-B.1 inventory `file_sha256` (case-normalised), and expected/restored sizes
   equal the inventory `size_bytes`. Zero mismatches; every `checksum_match` is
   `true`; `checksum_comparison_result` = `MATCH_ALL_20_FILES`. The inventory is
   the right independent reference: it was committed by Gate P1 PR-B.1 long
   before PR #401 existed.
5. **No raw data rows / raw files?** Confirmed. A scan for candle-row keys
   (`bid_o`…`ask_c`, `rows`, `candles` as data keys) over all four files found
   none; only hashes/sizes/basenames appear.
6. **No personal paths / drive letters / home paths / env dumps / credentials /
   Drive links / R2 keys?** Confirmed by two independent scans: this audit's
   regex scan (drive-letter, `/Users/`, `/home/`, `AppData`, username, `AKIA`,
   `Bearer`, `X-Amz-`, `drive.google`) found nothing, and the committed
   cleanliness report (Foundation T2 scrubber v1) records `clean: true`,
   `findings: []`.
7. **Alias, not runtime path?** Confirmed. `T2_LOCAL_OFFLINE_PRIMARY` appears 6
   times across the evidence; no runtime path appears anywhere.
8. **Restore-root isolation supported?** Supported as a recorded field
   (`restore_root_isolated: true`) plus an explanatory note stating the restore
   root was on a separate local/offline volume, outside both the source data
   tree and the destination tree, verified before copy. See §Residual R1 for the
   attestation caveat.
9. **PR #395 / PR #398 evidence untouched?** Yes. The last commit touching
   `phase_c1_365d_ba_pilot/` is `8e72806` (PR #395's own merge) and for
   `phase_c1_365d_ba_rerun/` is `234a1dd` (PR #398's own merge). PR #401 touched
   neither.
10. **Protected stage24/stage25 artifacts clean?** Yes — empty porcelain status
    across all protected paths (and `data/`) at audit time.
11. **No overclaim?** Confirmed. None of the forbidden claim tokens
    (`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
    `PRODUCTION_READY`) appears in the evidence; all four required
    non-authorisation statements are present; the report additionally states
    Phase C2 not started, Drive/R2 not used, and flags the object-lock
    limitation for Phase D itself.
12. **Residual risks specific to local/offline storage?** Yes — see below.
13. **Do the residual risks block Phase C1 acceptance?** No — rationale below.
14. **Should human + ChatGPT accept?** **Yes** — recommendation:
    accept PR #401's evidence as satisfying the immediate Phase C1 `365d_BA`
    local/offline copy → restore → checksum gate, with residuals R1–R5 recorded
    as Phase D inputs.

## Residual risks

- **R1 — attestation boundary (generic to metadata-only evidence, flagged
  adversarially).** The restored SHA-256 values are attestations by the
  executing session: this audit can verify they equal the independent inventory
  (they do, 20/20) and that the evidence is internally consistent, but a
  read-only audit cannot distinguish "recomputed from restored bytes" from
  "transcribed" without re-executing a hash. Mitigations: the execution ran in
  an audited, human-authorised session; the destination and restore copies still
  exist on the operator's disk, so the operator can independently spot-re-hash
  any file at will. *Recommended (optional): operator spot-re-hash of 2–3
  restored files before Phase D leans on this evidence.* Non-blocking for C1.
- **R2 — no true object-lock / WORM immutability.** A local filesystem cannot
  prove retention the way R2 object-lock could; the evidence correctly records
  `object_lock_status: NOT_APPLICABLE_LOCAL_OFFLINE`.
- **R3 — local admin can overwrite destination bytes.** Nothing prevents a
  privileged local process from silently modifying `T2_LOCAL_OFFLINE_PRIMARY`
  contents after the round-trip.
- **R4 — physical disk loss/damage/substitution.** A single disk can be lost,
  damaged, or silently replaced; there is no cryptographic binding between the
  physical medium and the evidence beyond the recorded hashes.
- **R5 — weaker disaster recovery; no backup copy was made.** The evidence
  records `backup_destination_used: false` — `T2_LOCAL_OFFLINE_BACKUP` was not
  exercised. Until a second offline copy (or off-site copy) exists, retention
  rests on one disk. *Recommended: make the backup copy (already authorised as
  optional by the PR #400 plan) before or alongside Phase C2/Phase D.*

**Do these block Phase C1 `365d_BA` acceptance? No.** The Phase C1 gate, as
defined by the PR #400 plan and the roadmap, asks for demonstrated
copy → restore → checksum capability with scrubbed metadata evidence — which
this evidence provides, verified against an independent committed reference.
**They are, however, material for the later Phase D byte-admissibility review**,
which must weigh R2–R5 (especially the absence of WORM immutability and the
single-copy exposure) when deciding whether these bytes are admissible
experiment inputs, and R1's optional spot-re-hash strengthens that review.

## Non-authorisation statements

This audit does **not**: approve Phase C2 or the `730d_BA`/`3650d_BA` spans;
approve byte-admissibility; adopt a new epoch; authorise ML Step 4; authorise
ML training/backtests; claim production readiness; modify PR #395/#398/#401
evidence; access raw data, external disks, Google Drive, or R2; or rerun any
copy/restore/checksum. It recommends acceptance of one thing only: the
`365d_BA` local/offline Phase C1 pilot evidence.

## Recommended next decision point

1. Human + ChatGPT record acceptance of PR #401's evidence (this audit
   recommends acceptance).
2. Decide ordering of the next two gates: **Phase D byte-admissibility review
   for `365d_BA`** (weighing R1–R5) versus **Phase C2 expansion**
   (`730d_BA`/`3650d_BA` local/offline round-trips). Suggested: make the
   `T2_LOCAL_OFFLINE_BACKUP` copy and the optional R1 spot-re-hash first (cheap,
   strengthens everything downstream), then Phase D for `365d_BA`.
3. Neither gate is started by this audit; each needs its own explicit
   authorisation.
