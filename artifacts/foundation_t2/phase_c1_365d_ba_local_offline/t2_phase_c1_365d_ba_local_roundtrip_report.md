# Foundation T2 — Phase C1 `365d_BA` local/offline round-trip evidence

**Status: `T2_C1_365D_BA_LOCAL_OFFLINE_ROUND_TRIP_EVIDENCE_CREATED`.**
A file-preserving local/offline copy → restore → checksum round-trip was
executed for span `365d_BA` only. All 20 files restored with SHA-256 + size
matching the committed PR-B.1 inventory. Metadata-only evidence; no raw bytes,
no personal absolute paths.

- run_id: `phase-c1-365d-ba-local-offline`
- plan document: `docs/design/phase_c1_365d_ba_local_offline_execution_plan.md`
- span_id: `365d_BA` (pilot only)
- destination alias: `T2_LOCAL_OFFLINE_PRIMARY` (the runtime path was used at
  execution time only and is **not** committed)
- destination mode: `local_offline_file_preserving`
- Google Drive: **not used** · R2: **not used** · backup destination: not used

## Result summary

| Metric | Value |
| --- | --- |
| file count | 20 |
| expected total bytes | 1,481,715,517 |
| restored total bytes | 1,481,715,517 |
| deposit (copy) | COPIED (20/20) |
| restore | RESTORED (20/20) |
| checksum comparison | **MATCH_ALL_20_FILES** (restored SHA-256 + size == expected inventory) |
| object-lock / retention | NOT_APPLICABLE_LOCAL_OFFLINE |
| restore root isolated | yes — separate local/offline volume, not inside the source data tree and not inside the destination tree (verified before copy) |

Per-file `logical_file_id`, expected/restored size, expected/restored SHA-256,
and per-file `checksum_match` are recorded in
`t2_phase_c1_365d_ba_local_roundtrip_report.json` and
`t2_phase_c1_365d_ba_local_manifest.json` (basenames + hashes only; no raw rows,
no paths).

## Procedure executed (file-preserving)

1. resolved `365d_BA` local candidate bytes (20 files) and verified the
   committed PR-B.1 inventory references;
2. confirmed destination + isolated restore root exist, D: free space ≫ 2×
   the 1.38 GB span, both target dirs empty;
3. verified each source file's SHA-256 equals the committed inventory value;
4. copied each file to `T2_LOCAL_OFFLINE_PRIMARY`;
5. restored each file from `T2_LOCAL_OFFLINE_PRIMARY` to the isolated restore
   folder;
6. recomputed restored SHA-256 + size and compared against the expected
   inventory values — 20/20 match.

## Non-scope / bindings

Metadata-only evidence. No raw candle rows, no raw files, no personal absolute
paths, no user-home directories, no environment dumps, no credentials/secrets,
no Google Drive links, no R2 object keys. Retention probe (in the R2 object-lock
sense) remains unresolved; a local/offline destination provides no true
object-lock / WORM immutability. `730d_BA` and `3650d_BA` were **not** executed;
Phase C2 not started; Google Drive and R2 not used. This evidence does **not**
approve byte-admissibility, does **not** adopt a new epoch, does **not**
authorise ML Step 4, and does **not** claim production readiness. PR #395 / PR
#398 stop evidence is unmodified.

## Recommended next decision point

A clean `365d_BA` local/offline round-trip now exists. Whether it **satisfies**
the immediate T2 deposit/restore/checksum evidence need is a human + ChatGPT
review decision (Phase C acceptance). Even if accepted, the Phase D
byte-admissibility review remains separate — and should weigh that this
destination has no object-lock. Expansion to `730d_BA` / `3650d_BA` (Phase C2)
must not begin before that review.
