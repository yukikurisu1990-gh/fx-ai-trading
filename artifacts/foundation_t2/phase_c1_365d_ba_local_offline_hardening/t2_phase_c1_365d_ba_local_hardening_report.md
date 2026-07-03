# Foundation T2 — Phase C1 `365d_BA` local/offline hardening evidence

**Status: `T2_C1_365D_BA_LOCAL_OFFLINE_HARDENING_EVIDENCE_CREATED`.**
Cheap hardening for the accepted Phase C1 `365d_BA` pilot (PR #401 / PR #402):
a second `T2_LOCAL_OFFLINE_BACKUP` copy was created and verified, and a
spot-rehash of 3 restored files was performed against the committed inventory
and the PR #401 evidence. Metadata-only; aliases only; runtime paths not
committed.

- run_id: `phase-c1-365d-ba-local-offline-hardening`
- span_id: `365d_BA` (only)
- mode: `local_offline_file_preserving`
- backup destination alias: `T2_LOCAL_OFFLINE_BACKUP`
- restore root alias: `T2_LOCAL_OFFLINE_RESTORE_ROOT` (PR #401 restore root, still available)
- PR #401 evidence: `artifacts/foundation_t2/phase_c1_365d_ba_local_offline/`
- PR #402 audit: `docs/design/phase_c1_365d_ba_local_offline_acceptance_audit_fable5.md`
- Google Drive: not used · R2: not used

## Backup copy (R5 hardening)

| Metric | Value |
| --- | --- |
| backup file count | 20 |
| expected total bytes | 1,481,715,517 |
| backup total bytes | 1,481,715,517 |
| backup checksum comparison | **MATCH_ALL_20_FILES** (backup SHA-256 + size == committed PR-B.1 inventory) |

All 20 `365d_BA` files now exist on a second local/offline destination
(`T2_LOCAL_OFFLINE_BACKUP`), independently verified against the inventory. This
addresses residual **R5** (single-copy exposure) from the PR #402 audit — a
second offline copy now exists.

## Spot-rehash (R1 hardening)

| Metric | Value |
| --- | --- |
| restore root available | yes |
| selection method | deterministic sorted-index pick [0, 10, 19] of the 20-file inventory |
| selected file count | 3 |
| selected logical file IDs | `candles_AUD_CAD_M1_365d_BA.jsonl`, `candles_EUR_USD_M1_365d_BA.jsonl`, `candles_USD_JPY_M1_365d_BA.jsonl` |
| spot-rehash comparison | **MATCH_ALL_SELECTED_VS_INVENTORY_AND_PR401** |

The 3 selected restored files (from the PR #401 restore root, still present)
were re-hashed and matched **both** the committed inventory SHA-256/size **and**
the restored SHA-256 recorded in PR #401's evidence. This addresses residual
**R1** (metadata-only attestation boundary) for the sampled files: an
independent re-hash confirms the PR #401 restored values were real, not merely
transcribed. Full re-verification of all 20 was intentionally not re-run (no
new full round-trip).

## Non-scope / bindings

Metadata-only evidence. No raw candle rows, no raw files, no personal absolute
paths, no drive-letter paths, no user-home directories, no environment dumps, no
credentials/secrets, no Google Drive links, no R2 object keys. Only aliases,
basenames, sizes, and SHA-256 values appear. `730d_BA` and `3650d_BA` were
**not** executed; Phase C2 not started; Phase D not started; Google Drive and R2
not used. This evidence does **not** approve byte-admissibility, does **not**
adopt a new epoch, does **not** authorise ML Step 4, and does **not** claim
production readiness. PR #395 / PR #398 / PR #401 evidence is unmodified.

## Recommended next decision point

Residuals R1 (for the 3 sampled files) and R5 are now hardened. The remaining
audit residuals (R2 no object-lock/WORM, R3 local-admin overwrite, R4 physical
disk loss/substitution) are inherent to local/offline storage and remain
material for the **Phase D byte-admissibility review** for `365d_BA`. Phase C2
expansion (`730d_BA` / `3650d_BA`) remains a separate, unauthorised step. Each
next gate needs its own explicit authorisation.
