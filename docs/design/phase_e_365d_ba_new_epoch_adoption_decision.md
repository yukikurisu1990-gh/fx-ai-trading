# Phase E — `365d_BA` new-epoch adoption decision

- **Document class:** doc-only decision record (adopts a research-only epoch;
  authorises no experiment)
- **Base:** master `2dad38b` (post PR #405 merge)
- **Branch:** `docs/phase-e-365d-ba-new-epoch-adoption`
- **Predecessor gate:** Phase D acceptance
  (`docs/design/phase_d_365d_ba_byte_admissibility_acceptance_record.md`, PR #405,
  `PHASE_D_365D_BA_BYTE_ADMISSIBILITY_ACCEPTANCE_RECORDED_FOR_LATER_EXPERIMENT_PRE_REGISTRATION`).
- **Decision maker:** human + ChatGPT (recorded here under their instruction).

## Phase E status

**`PHASE_E_365D_BA_RESEARCH_FROZEN_HOLDOUT_EPOCH_ADOPTION_RECORDED`**

Also binding: `ML_STEP4_NOT_AUTHORISED` · `PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: this record does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `BYTE_ADMISSIBILITY_APPROVED`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; those tokens
appear only as prohibitions. (The adoption recorded here is a **research-only
frozen-holdout epoch**; it is deliberately named with the specific Phase E
status above rather than the bare `NEW_EPOCH_ADOPTED` label, which remains
prohibited.)

## 1. Executive adoption decision

- `365d_BA` is adopted as **`RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`**.
- This is a **research-only frozen-holdout epoch adoption record**.
- The adoption is based on the committed byte-admissibility chain through PR #405.
- This does **not** authorise ML Step 4.
- This does **not** authorise ML training or backtests.
- This does **not** include `730d_BA` or `3650d_BA`.
- This does **not** claim production readiness.

## 2. Adopted epoch identity

| Field | Value |
| --- | --- |
| epoch ID | `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1` |
| span | `365d_BA` |
| file count | 20 |
| total bytes | 1,481,715,517 |
| inventory reference | PR-B.1 committed inventory (`artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json`) |
| byte-admissibility acceptance | PR #405 (`...ACCEPTANCE_RECORDED_FOR_LATER_EXPERIMENT_PRE_REGISTRATION`) |
| storage / evidence mode | local/offline evidence chain (`T2_LOCAL_OFFLINE_PRIMARY` + `T2_LOCAL_OFFLINE_BACKUP`) |
| retention limitation | no object-lock / WORM immutability |
| purpose | epoch reference for later experiment pre-registration planning only |

## 3. Evidence basis

- **PR-B.1 committed inventory** — 20 files, per-file SHA-256 + size, committed
  before any Phase C evidence.
- **PR #401 local/offline round-trip evidence** — 20 files, 1,481,715,517 bytes,
  `MATCH_ALL_20_FILES`.
- **PR #402 Fable 5 Phase C1 acceptance audit** — no blockers.
- **PR #403 hardening** — `T2_LOCAL_OFFLINE_BACKUP` verified (`MATCH_ALL_20_FILES`);
  3-file spot-rehash matched inventory + PR #401.
- **PR #404 Fable 5 Phase D recommendation** — recommended acceptance; no blockers.
- **PR #405 final human + ChatGPT byte-admissibility acceptance** — recorded.

## 4. Binding contracts carried into the epoch

Any experiment that later consumes this epoch inherits the post-remediation
contracts and caveats:

### F-2 — PnL / label contract
- F-2 corrections are **required** (traded-direction barrier replay; timeout
  mark-to-market; SL-first tie-break) per
  `docs/design/train_serve_consistency_contract.md` and the F-2 invariant tests.
- **Historical Phase 9.X numerics are not rehabilitated.**
- Any future experiment **must not rely on pre-F-2 optimistic historical
  results**.

### F-5 — provenance contract
- Manifest / provenance discipline remains binding.
- Any future model/run evidence **must identify** the exact epoch, file hashes,
  code SHA, config hash, label/cost contracts, and train/serve assumptions.
- **Metadata-only evidence remains required** where raw data must not be
  committed.

### F-8 — train/serve consistency contract
- Train/serve consistency constraints remain binding.
- **EV unit comparability must be explicit** (canonical `pips_post_cost`).
- **Decision-time / completed-bar / MTF as-of assumptions must be declared.**
- **Unvalidated legacy strategy paths remain fail-closed** unless separately
  remediated.

### Local/offline storage limitation
- The epoch is adopted **despite** local/offline limitations.
- The limitation **must be disclosed** in downstream reports.
- The epoch **must not be described as backed by WORM / object-lock retention**.

## 5. Scope boundaries

**Accepted:** `365d_BA` only; `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`; use as
the epoch reference for later experiment pre-registration planning.

**Not accepted:** `730d_BA`; `3650d_BA`; all-span T2 completion; ML Step 4;
ML training/backtests; production readiness; historical Phase 9.X metric
rehabilitation; Phase 9.16 promotion/demotion.

## 6. Conditions before any experiment consumes the epoch

- checksums **must be re-verified** immediately before any experiment consumes
  `365d_BA`;
- the experiment **must reference** `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`;
- the experiment **must reference** the accepted file count (20) and total byte
  count (1,481,715,517);
- the experiment **must record** code SHA and config hash;
- the experiment **must pre-register**: training/validation/test boundaries;
  objective metrics; cost model; label contract; F-2/F-5/F-8 compliance
  assumptions; multiplicity control; acceptance/failure criteria; reporting
  schema;
- local/offline limitations **must be disclosed** in the experiment report.

## 7. Recommended next gate

- **Next gate: Phase F — ML Step 4 pre-registration PR.**
- **Phase F is not started by this PR** and requires **separate human + ChatGPT
  authorisation**.
- **ML Step 4 execution remains blocked** until Phase F is accepted.
- **No training or backtests may run from this PR.**
- **Phase C2** (`730d_BA` / `3650d_BA` local/offline round-trips) may proceed
  **independently later** to broaden retention evidence; it is not required for
  the `365d_BA`-only path and is not started here.

## 8. Non-authorisation statements

This PR does **not**: access raw data; access external disks; access Google
Drive; access R2; rerun copy/restore/checksum; start Phase C2; include
`730d_BA`; include `3650d_BA`; authorise ML Step 4; run ML training; run
backtests; claim production readiness; validate profitability; rehabilitate
historical Phase 9.X metrics; or promote/demote Phase 9.16. It is a decision
record only.
