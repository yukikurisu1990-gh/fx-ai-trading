# Phase D — `365d_BA` byte-admissibility review (Fable 5)

- **Document class:** doc-only, read-only recommendation/review (recommends; approves nothing)
- **Reviewer:** Fable 5 (independent cross-checks against committed references)
- **Base:** master `937a37e` (post PR #403 merge)
- **Branch:** `docs/phase-d-365d-ba-byte-admissibility-review`
- **Reviewed (committed metadata only):** PR #399 destination strategy, PR #400
  execution plan, PR #401 round-trip evidence
  (`artifacts/foundation_t2/phase_c1_365d_ba_local_offline/`), PR #402 acceptance
  audit, PR #403 hardening evidence
  (`artifacts/foundation_t2/phase_c1_365d_ba_local_offline_hardening/`), the
  committed PR-B.1 `365d_BA` inventory
  (`artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json`), and the
  roadmap/gate documents.
- **Method constraints honoured:** no raw data read; no external disk, Google
  Drive, or R2 access; no copy/restore/checksum rerun; no ML training/backtests;
  no Phase C2; `730d_BA`/`3650d_BA` untouched.

## Central question

*Should `365d_BA` be recommended as byte-admissible for later experiment
pre-registration, based on the committed inventory, Phase C1 local/offline
round-trip evidence, acceptance audit, backup copy, and spot-rehash evidence?*

## Conclusion

**`PHASE_D_365D_BA_BYTE_ADMISSIBILITY_RECOMMENDED_FOR_HUMAN_ACCEPTANCE`**

Also binding: `NEW_EPOCH_NOT_ADOPTED` · `ML_STEP4_NOT_AUTHORISED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

**Recommended for human + ChatGPT acceptance:** the `365d_BA` bytes / checksums /
evidence chain as **admissible inputs for later experiment pre-registration**,
under the conditions in the final section. **No blockers were found.** Final
human + ChatGPT approval remains a separate act; this document recommends only.

**Not authorised by this review:** all-span T2 completion; `730d_BA`; `3650d_BA`;
new epoch adoption; ML Step 4; ML training/backtests; production readiness.

Forbidden-label note: this review does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBILITY_APPROVED`, `BYTE_ADMISSIBLE`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; those tokens
appear only as prohibitions.

## Answers to the required review questions

1. **Independent committed inventory reference for `365d_BA`?** Yes —
   `raw_inventory_365d_BA.json` (Gate P1 PR-B.1), committed long before the
   Phase C evidence; 20 files with per-file `file_sha256` + `size_bytes`. It is
   the independent reference used below.
2. **PR #401 evidence matches inventory for all 20 files?** Yes — independently
   re-checked in this review: 0 of 20 restored-SHA-256/size mismatches vs the
   inventory; `checksum_comparison_result = MATCH_ALL_20_FILES`.
3. **PR #402 independently accepts PR #401 for Phase C1?** Yes —
   `PHASE_C1_365D_BA_LOCAL_OFFLINE_EVIDENCE_ACCEPTABLE_FOR_C1_PILOT`, itself based
   on an independent 20-file cross-check, and human-accepted at merge.
4. **PR #403 creates a verified `T2_LOCAL_OFFLINE_BACKUP` copy?** Yes — a second
   local/offline copy of all 20 files; independently re-checked here: 0 of 20
   backup-SHA-256/size mismatches vs the inventory; `MATCH_ALL_20_FILES`.
5. **PR #403 spot-rehash strengthens the restored-hash attestation boundary?**
   Yes — 3 deterministically-selected restored files (`AUD_CAD`, `EUR_USD`,
   `USD_JPY`) re-hashed and matched **both** the inventory **and** PR #401's
   recorded restored SHA-256 (independently re-checked: 0 mismatches). This
   partially closes residual R1 for the sampled files (independent proof the
   PR #401 restored values were real, not transcribed).
6. **Total byte count consistent across inventory, round-trip, and backup?**
   Yes — inventory total = PR #401 expected = PR #401 restored = PR #403 expected
   = PR #403 backup = **1,481,715,517 bytes** (verified equal in this review).
7. **All evidence files metadata-only?** Yes — the two evidence directories hold
   only manifest/report/cleanliness JSON + markdown (basenames, sizes, SHA-256,
   statuses); no data payloads.
8. **Raw data / rows / files / personal paths / runtime paths / credentials /
   env dumps / Drive links / R2 keys absent?** Yes — both committed cleanliness
   reports record `clean: true` / `findings: []` (Foundation T2 scrubber v1), and
   this review's own scan found none; evidence uses aliases only
   (`T2_LOCAL_OFFLINE_PRIMARY`, `T2_LOCAL_OFFLINE_BACKUP`,
   `T2_LOCAL_OFFLINE_RESTORE_ROOT`).
9. **PR #395/#398 stop-before-deposit records preserved and not contradicted?**
   Yes — both remain unmodified (last-touch `8e72806` / `234a1dd`); the
   local/offline success evidence does not contradict them (they honestly
   recorded that the *R2* path stopped for want of credentials — a different
   destination). The R2 deferral (PR #399) reconciles the two.
10. **Does no object-lock/WORM (R2 residual) block `365d_BA` admissibility?** No
    — accepted limitation for a local/offline pilot; see residual analysis.
11. **Does local-admin overwrite (R3) block admissibility?** No — mitigated
    sufficiently for pilot scope by the checksum evidence + independent inventory
    + second backup copy + committed metadata record; not fully eliminated.
12. **Does physical disk loss/substitution (R4) block admissibility?** No —
    acceptable for local/offline pilot scope; mitigated by the second offline
    copy; a future off-site copy would strengthen it.
13. **Does absence of all-span retention evidence block `365d_BA`-only
    admissibility?** No — admissibility is being recommended for `365d_BA` only;
    `730d_BA`/`3650d_BA` are explicitly out of scope and require their own
    Phase C evidence.
14. **Recommend `365d_BA` for later experiment pre-registration, keeping
    `730d_BA`/`3650d_BA` out of scope?** Yes.
15. **Conditions before new epoch adoption or ML Step 4?** See the final section;
    in short: this is a byte-input recommendation only — the frozen-holdout epoch
    (Phase E) and the ML Step 4 pre-registration are separate gates, and the
    F-2/F-5/F-8 audit corrections plus the local/offline limitation must all
    carry forward into any experiment design.

## Residual-risk analysis

| Residual | Blocking for `365d_BA` admissibility recommendation? | Status |
| --- | --- | --- |
| R2 — no true object-lock / WORM immutability | **No** | Non-blocking; **material for later gates.** A local filesystem cannot cryptographically prove retention. Acceptable for a pilot byte-input recommendation because admissibility here means "these specific bytes/checksums are the inventoried bytes and round-trip cleanly", which the checksum chain establishes; it does not claim tamper-proof archival. Any downstream experiment report must keep this limitation visible. |
| R3 — local-admin overwrite possibility | **No** | Non-blocking; mitigated (checksum + independent inventory + second backup + metadata record) but not eliminated. **Follow-up condition:** re-verify checksums against the inventory immediately before an experiment consumes the bytes. |
| R4 — physical disk loss/damage/substitution | **No** | Non-blocking for pilot scope; mitigated by the second offline copy. **Follow-up condition (recommended):** add an off-site copy before treating `365d_BA` retention as durable long-term. |
| All-span incompleteness (`730d_BA`/`3650d_BA` not retained/restored) | **No** (for `365d_BA`-only scope) | Non-blocking; **material** — it bounds the recommendation to `365d_BA`. Those spans need their own Phase C evidence before inclusion. |
| Limited spot-rehash sample (3 of 20, not a full independent re-hash) | **No** | Non-blocking; R1 is closed only for the 3 sampled files. **Follow-up condition (cheap):** the operator may independently re-hash the remaining restored files if a stronger attestation is wanted before experiments rely on all 20. |
| Local/offline weaker than cloud object-lock for formal archival claims | **No** | Non-blocking for byte-input admissibility; **material** — do not represent this as a formal WORM archive; it is a verified local/offline retention pilot. |

None of the residuals is blocking for a **`365d_BA`-only byte-admissibility
recommendation**; several impose follow-up conditions or remain material for the
Phase E new-epoch and Phase F ML-Step-4 gates.

## Conditions attached to this recommendation

1. This recommendation applies **only to `365d_BA`**.
2. It relies on the **current committed inventory/evidence chain** (PR-B.1
   inventory + PR #401 + PR #402 + PR #403); if any is superseded, re-review.
3. **`730d_BA` and `3650d_BA` require separate Phase C evidence** before
   inclusion — they are not covered here.
4. **New epoch adoption requires a separate Phase E decision** (a named,
   frozen-holdout research epoch record — roadmap Phase E).
5. **ML Step 4 requires a separate pre-registration gate** (roadmap Phase F).
6. **No historical Phase 9.X metrics are rehabilitated** by this review.
7. **Phase 9.16 is not promoted or demoted.**
8. **The local/offline limitation (R2/R4, no WORM, single-site until an off-site
   copy exists) must remain visible in any downstream experiment report.**
9. Recommended (not blocking): re-verify `365d_BA` checksums against the
   inventory immediately before any experiment consumes the bytes (mitigates R3);
   optionally add an off-site copy (R4) and complete the full-set re-hash (R1).

## Recommended next decision point

Human + ChatGPT record acceptance of this `365d_BA` byte-admissibility
recommendation (this review recommends acceptance, no blockers). Then the two
downstream gates remain, each separately authorised: **Phase E — new-epoch
adoption for `365d_BA`** (a research-only epoch record carrying the F-2/F-5/F-8
contracts and the local/offline limitation), and, only after that, **Phase F —
ML Step 4 pre-registration**. Independently, **Phase C2** (`730d_BA`/`3650d_BA`
local/offline round-trips) may proceed to broaden retention. Nothing here is
started; each next gate needs its own explicit authorisation.
