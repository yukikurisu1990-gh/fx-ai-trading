# Gate P2 retention destination evaluation — candidate options assessed against PR #361 §7 admissibility criteria

**Status:** Doc-only technical evaluation memo. Authored under the
contract of `docs/design/new_provenance_bound_dataset_epoch_design.md`
(PR #361, §7 binding) at `master @ 25ed0e0`. This memo **does not
pre-approve** any candidate destination. Per PR #361 §7, no specific
external service is admissible until its availability, access, and
immutability semantics are verified inside the Gate P1 PR. This memo
provides a structured comparison so that the Gate P1 PR-B inspection
and the Gate P2 verification PR can each operate against a documented
candidate set rather than an undocumented one.

**Base:** master `25ed0e0` (post PR #365 merge)
**Branch:** `docs/gate-p2-retention-destination-evaluation`
**File added:** `docs/design/gate_p2_retention_destination_evaluation_memo.md`

**Amendment history:** (none — initial draft.)

This memo is the **evaluation framework** for retention destinations.
PR #361 §7 locked the principle ("epoch cannot become binding until
the exact accepted raw bytes and the exact generated labels bytes are
stored in a retrievable immutable location, verified end-to-end at
Gate P2") and the **three admissibility criteria**. The present memo
maps a candidate set against those criteria and registers per-option
trade-offs so the eventual Gate P1 / Gate P2 selection is grounded.

---

## §1 Purpose / Scope / Non-scope

### Purpose

To produce a structured, criterion-by-criterion technical evaluation of
candidate retention destinations so that:

- the PR-B inspector (per PR #365 implementation plan, the
  `inspector.retention` submodule and the
  `retention_feasibility_<candidate_id>.json` artifact) has a
  documented candidate list to record under
  `candidate_retention_options_requiring_later_authorisation`
- the Gate P2 PR (eventual; not authored here) has a reviewer-ready
  comparison matrix to motivate destination selection
- the user can make an informed authorisation decision when picking
  the destination to verify

### Scope

The memo binds:

- the writeback of PR #361 §7 (§2 below)
- the three admissibility criteria (§3)
- the candidate destination set considered (§4)
- per-destination evaluation against the criteria + operational
  considerations (§5)
- a comparison matrix (§6)
- a recommended tier ordering (§7)
- the round-trip verification protocol design (§8)
- integration with the existing OANDA 2026-05-31 archive (§9)
- risk register (§10)
- open questions requiring user judgment (§11)

### Non-scope

The memo explicitly **does not**:

- pre-approve any destination (re-declares PR #361 §7 "not
  pre-approved" binding)
- select a destination for the eventual Gate P2 PR
- modify the PR #361 §7 admissibility criteria
- specify Gate P2 PR contents (only the inputs Gate P2 will reference)
- authorise PR-B.0 / PR-B.1 / PR-B.2 (per PR #365)
- modify any prior verdict (Phase 27 / 28 / 29.0a / V2-expanded
  Stage 2 / F-1 / PR #356)
- propose any change to `.gitignore`
- modify any existing source code
- expend or commit byte storage with any external service

---

## §2 PR #361 §7 binding — writeback

For convenience, the binding principle from PR #361 §7 is reproduced
here verbatim in essence (the doc itself remains the authoritative
referent):

> An epoch cannot become binding until the exact accepted raw bytes
> and the exact generated labels bytes are stored in a **retrievable
> immutable location**, verified end-to-end at Gate P2. A committed
> SHA-256 manifest **without** an accessible byte archive is
> **insufficient**.

The **three admissibility criteria** (every destination must satisfy
**all three**):

- **C1 — Byte-identity-restorable at acceptance time**: round-trip
  test passes under Gate P2.2 retained-bytes verification. The
  manifest's per-file SHA-256 must equal the SHA-256 recomputed from
  bytes restored from the destination.
- **C2 — Immutability or content-addressed addressing**: stored bytes
  are immutable after deposit, or the address used to retrieve the
  bytes is itself a function of their content (e.g., a content hash).
  This rules out destinations where a published address (URL, path,
  identifier) can point to mutated bytes without the address itself
  changing.
- **C3 — Documented, auditor-runnable restoration procedure**: an
  external auditor can, with only the documented procedure plus any
  named credentials, retrieve byte-identical copies of the deposited
  files. Restoration is not dependent on personnel-specific knowledge
  or one-off tooling.

The candidate destination **categories** declared by §7:

- **in-repo committed bytes** — admissible only if total epoch byte
  budget falls below a project-acceptable repository-size guard
  (guard value set inside the Gate P1 PR). The OANDA 2026-05-31
  archive (17.54 GB raw across 120 files, per `artifacts/
  oanda_archive_2026-05-31/candles_manifest.json`) exceeds any
  plausible in-repo guard; the §7 in-repo path is therefore not a
  candidate for the current epoch.
- **content-addressed immutable external archive** — admissible only
  if a specific archive is named, its access is verified, and its
  immutability semantics are documented.

Anti-pattern (§7): an unversioned, gitignored, locally-regenerated
parquet becoming a binding numeric authority. The new epoch contract
forbids this pattern at every layer.

---

## §3 Admissibility criteria framework

For evaluation purposes, each destination is scored against the three
criteria with one of:

- **SATISFIES** — the destination meets the criterion structurally
  (the storage system itself enforces it).
- **SATISFIES_BY_PROCEDURE** — the destination meets the criterion
  only when used with a specific procedure (e.g., a public service
  that requires explicit "object-lock" mode to satisfy C2).
- **PARTIAL** — the criterion is met for typical access patterns but
  has edge cases requiring operator awareness.
- **DOES_NOT_SATISFY** — the destination cannot meet the criterion
  without external instrumentation.

A destination becomes admissible at Gate P1 only after **all three**
criteria are at SATISFIES or SATISFIES_BY_PROCEDURE, **and** the
specific procedural setting is documented in the Gate P1 PR, **and**
the round-trip restoration (§8) succeeds at Gate P2.

This memo records scores. Final acceptance lives with Gate P1 / P2.

In addition to C1-C3 we evaluate operational factors that do not
appear in §7 but condition the practicality of meeting the criteria:

- **OF1 — One-shot setup cost**: time / approvals / billing to reach
  a first byte deposited
- **OF2 — Ongoing storage cost** at the epoch scale (17.54 GB raw +
  estimated 10-100 GB labels + small manifests, conservatively
  ~50-100 GB total per epoch)
- **OF3 — Egress / retrieval cost** under one full round-trip plus a
  modest number of auditor restorations
- **OF4 — Single-point-of-failure profile** (service shutdown,
  account suspension, key loss, geographic concentration)
- **OF5 — Single-file size limit** vs the largest individual file
  expected at the epoch (largest M1 3650d_BA BA file is ~915 MB per
  `candles_manifest.json` headers; with labels and split manifests
  some files may grow larger)
- **OF6 — Restoration procedure maintainability**: how stable the
  documented procedure is across years (CLI / API stability)
- **OF7 — Practical control plane** (who needs which credential, how
  rotation works, who can lock or delete)

---

## §4 Candidate destinations considered

The following options are evaluated. The list is **not exhaustive**;
omissions are an open question (§11.Q1).

- **D1 — GitHub release asset (free tier) + SHA-256 manifest committed in-repo**
- **D2 — GitHub release asset (paid LFS / pack support) + SHA-256 manifest committed in-repo**
- **D3 — Cloudflare R2 + bucket object-lock + SHA-256 manifest committed in-repo**
- **D4 — AWS S3 + bucket-level object-lock (compliance mode) + SHA-256 manifest committed in-repo**
- **D5 — Backblaze B2 + object-lock + SHA-256 manifest committed in-repo**
- **D6 — IPFS (pinning service e.g. Web3.Storage / Pinata) + CID-as-address**
- **D7 — Physical HDD offline duplicate(s) + SHA-256 manifest committed in-repo**
- **D8 — Internet Archive (archive.org) item-per-file + SHA-256 manifest committed in-repo**
- **D9 — git-annex special-remote pointing at any of the above**
- **D10 — Combination strategy**: primary external (e.g., R2 object-lock) + offline HDD backup + IPFS pinning of the manifest only

Excluded a priori (with reason):

- **In-repo committed bytes** (PR #361 §7 in-repo path) — excluded
  because the OANDA 2026-05-31 archive at 17.54 GB raw alone exceeds
  any plausible project-acceptable repository-size guard. (Re-eligible
  only if a future smaller-span epoch is considered.)
- **Google Drive / Dropbox / OneDrive (consumer cloud)** — excluded
  because none satisfies C2 structurally; mutation of stored content
  via a permanent URL is supported by these services (overwrite-in-
  place, web UI editing). Could be re-considered only as a derived
  copy with strict procedure.
- **Discord / Telegram file uploads** — excluded; not designed for
  durable retention, no immutability semantics.

---

## §5 Per-destination evaluation

### D1 — GitHub release asset (free tier) + SHA-256 manifest in-repo

- **C1 (round-trip restorable)**: SATISFIES. Release assets are
  downloadable via `gh release download` or direct URL; bytes are
  byte-identical to the upload.
- **C2 (immutability / content-addressed)**: SATISFIES_BY_PROCEDURE.
  Release tags are mutable by default (a release can be edited or
  assets replaced via API). Immutability is achieved by procedure:
  (a) protect the tag at branch-protection level, (b) delete-and-
  recreate is detectable (the published SHA-256 manifest catches any
  drift), (c) avoid editing the release post-publish. Not as strong
  as object-lock, but the in-repo manifest provides cryptographic
  detection of any drift.
- **C3 (documented restoration)**: SATISFIES. `gh release download
  <tag> --pattern '*.jsonl' --dir <out>` plus the in-repo manifest's
  SHA-256 verification step.
- **OF1 (setup)**: ~minutes (GitHub account already exists; create
  release in this repo).
- **OF2 (storage cost)**: Free for public repos up to 2 GB per file
  and 100 GB per release total (per GitHub docs; verify current
  limits at Gate P1). Free tier sufficient for raw at single-pair
  granularity (largest file ~915 MB < 2 GB) but **per-release total
  ~17.54 GB** exceeds the public-repo limit. Multiple releases
  required (e.g., one per pair); manageable but adds bookkeeping.
- **OF3 (egress cost)**: Free.
- **OF4 (SPOF)**: GitHub account suspension; repo deletion. Mitigable
  with org-level ownership + backup (see D10).
- **OF5 (per-file size limit)**: 2 GB per file (public repo;
  Pro/Team/Enterprise raises to 5 GB on some plans). Largest M1
  3650d_BA file ~915 MB → within limit. Labels per epoch could
  exceed for some pairs; per-pair sharding suffices.
- **OF6 (procedure stability)**: `gh` CLI is stable; GitHub release
  API is stable.
- **OF7 (control plane)**: repository owner controls all assets; no
  per-file ACL.

**Verdict (pre-Gate P1)**: Strong candidate for **Tier 1**.
Immutability is achieved by procedure + manifest cross-check rather
than by service-level object-lock; this trade-off is acceptable
because the manifest committed in-repo provides cryptographic
detection of mutation.

### D2 — GitHub release asset with LFS / large-file packs

Like D1 but with paid LFS or organisation-level large-file support.
Eligible if D1's per-release total limit becomes a friction point.

- **C1, C2, C3**: same as D1 (LFS preserves byte identity; same
  procedural immutability).
- **OF2 (cost)**: Paid (LFS data pack billing).
- **Verdict**: Tier 2 fallback for D1.

### D3 — Cloudflare R2 + bucket object-lock + manifest in-repo

- **C1**: SATISFIES. S3-API-compatible; download yields byte-
  identical files.
- **C2**: SATISFIES. R2 supports object-lock in compliance mode
  (verify exact capability at Gate P1). Bytes are immutable for the
  duration of the retention setting.
- **C3**: SATISFIES. S3 CLI (`aws s3 cp` against R2's S3 endpoint)
  or `rclone` are documented; restoration procedure is one command
  per file + checksum verification.
- **OF1**: Account creation + bucket creation + object-lock enabling
  (~hour).
- **OF2**: Cloudflare R2 storage cost (verify current rates; was
  $0.015/GB-month as of late 2024 — confirm at Gate P1). ~50-100 GB
  → ~$0.75-$1.50/month.
- **OF3**: **R2 has zero egress fees**. This is decisive for Gate P2
  round-trip + auditor restoration.
- **OF4 (SPOF)**: Cloudflare account suspension; key loss. Mitigable
  with D10.
- **OF5**: Effectively no per-file size limit relevant here.
- **OF6**: S3 API is industry-standard and stable.
- **OF7**: API tokens with scoped permissions; multiple tokens for
  separate roles (writer vs auditor-read-only) possible.

**Verdict (pre-Gate P1)**: Strong candidate for **Tier 1**. Object-
lock and zero egress are decisive against the criteria + operational
factors. Subject to Gate P1 access verification.

### D4 — AWS S3 + bucket-level object-lock (compliance mode) + manifest in-repo

- **C1**: SATISFIES.
- **C2**: SATISFIES. AWS S3 compliance-mode object-lock is the
  most-rigorous available service-level immutability (cannot be
  shortened or removed by anyone, including the root account).
- **C3**: SATISFIES. AWS CLI is documented; restoration is one
  command per file + checksum.
- **OF1**: Account + bucket + lock-config (~hour to a day depending
  on AWS familiarity).
- **OF2**: S3 standard storage cost (~$0.023/GB-month) — $1.15-$2.30
  for ~50-100 GB.
- **OF3**: AWS egress is $0.05-$0.09/GB (after free tier).
  ~$2.5-$9 for one full round-trip of 50-100 GB. Mitigable with
  S3 Transfer Acceleration off + same-region restoration.
- **OF4 (SPOF)**: AWS account suspension; root credential loss.
  Strong service reliability.
- **OF5**: 5 TB per object limit (irrelevant here).
- **OF6**: AWS CLI is stable.
- **OF7**: IAM policies offer fine-grained control.

**Verdict (pre-Gate P1)**: Strong candidate for **Tier 1** when
maximum service-level immutability is required. Trade-off is egress
cost vs R2.

### D5 — Backblaze B2 + object-lock + manifest in-repo

- **C1**: SATISFIES.
- **C2**: SATISFIES. B2 supports object-lock (verify governance vs
  compliance mode at Gate P1).
- **C3**: SATISFIES. B2 has native CLI + S3 API compatibility.
- **OF1**: Account + bucket creation (~hour).
- **OF2**: B2 storage $0.006/GB-month — $0.30-$0.60/month for
  50-100 GB.
- **OF3**: B2 egress is **free up to 3x stored bytes per month**
  (verify current policy at Gate P1), then $0.01/GB.
- **OF4 (SPOF)**: Backblaze account suspension; less well-known than
  AWS but operationally solid.
- **OF5**: 10 TB per file (irrelevant).
- **OF6**: B2 CLI / S3 API compat stable.
- **OF7**: Application keys with scoped permissions.

**Verdict (pre-Gate P1)**: Strong **Tier 1** alternative to D3 when
egress is anticipated to be high. Slightly less polished than R2 but
financially the lowest-cost option.

### D6 — IPFS (pinning service) + CID-as-address

- **C1**: SATISFIES. CID retrieval yields byte-identical content.
- **C2**: SATISFIES. CIDs are content-addressed by construction
  (CID = `sha256(content)` + multiformat envelope). This is the most
  rigorous match for §7 criterion 2.
- **C3**: SATISFIES_BY_PROCEDURE. Restoration requires (a) a working
  IPFS gateway, (b) the pinning service to still hold the pin (or a
  re-pin elsewhere). The procedure exists but operational
  dependencies are more delicate.
- **OF1**: Pinning-service account + first upload (~hour).
- **OF2**: Web3.Storage / Pinata / Filebase pricing varies; for
  50-100 GB, ~$5-$15/month at typical retail.
- **OF3**: Generally free egress from public IPFS gateways but with
  rate limits; private gateway via paid plan.
- **OF4 (SPOF)**: Pinning service shutdown; pin churn (content not
  re-pinned elsewhere). Mitigable with multi-pinning (pin same CID
  on 2+ services).
- **OF5**: No practical per-file size limit (large files are chunked
  into a DAG; chunk size standard).
- **OF6**: IPFS CLI is stable but the surrounding ecosystem (HTTP
  gateways, pinning APIs) is more volatile than S3 or GitHub.
- **OF7**: CID is the credential; anyone holding the CID can
  retrieve the bytes from a public gateway. This is fine for
  research bytes but is a different security model.

**Verdict (pre-Gate P1)**: Conceptually the **most aligned** with §7
criterion 2. Practical adoption is **Tier 2** because of the
ecosystem volatility (OF6). Best as an addressing layer **in
combination with** D3/D4/D5 (D10).

### D7 — Physical HDD offline duplicate(s) + manifest in-repo

- **C1**: SATISFIES (when the HDD is connected).
- **C2**: PARTIAL. The HDD itself is mutable; immutability is
  achieved by procedure (write-once-then-shelve discipline) +
  manifest verification. A read-only enclosure or LUKS in WORM mode
  can strengthen.
- **C3**: SATISFIES_BY_PROCEDURE. Requires the auditor to physically
  receive (or co-locate with) the HDD. Procedure must specify drive
  identity (serial, hash of a label) and connection method.
- **OF1**: Buying / preparing drive (~hours).
- **OF2**: One-shot hardware cost ($30-$60 per 1-2 TB drive); ~$0/month.
- **OF3**: ~$0/month; transit / shipping per auditor restoration.
- **OF4 (SPOF)**: Drive failure; theft; fire. Mitigable with 2+
  geographically separate drives.
- **OF5**: No practical per-file limit.
- **OF6**: Direct file copy via OS-native tools; procedure stable.
- **OF7**: Physical possession is the credential.

**Verdict (pre-Gate P1)**: **Tier 3** as primary destination (the
auditor-runnable requirement of C3 is awkward), but **Tier 1 as a
backup leg** in a D10 combination strategy.

### D8 — Internet Archive (archive.org)

- **C1**: SATISFIES.
- **C2**: PARTIAL. IA items are intended to be permanent but the
  service has historically reflowed items (e.g., the Wayback Machine
  has removed content). Bytes can be modified by IA administrators.
- **C3**: SATISFIES. IA provides `internetarchive` CLI and direct
  URLs.
- **OF1**: IA account + item creation (~hour).
- **OF2**: Free.
- **OF3**: Free.
- **OF4 (SPOF)**: IA is a single non-profit; its long-term
  sustainability is widely debated.
- **OF5**: Practical limits; very large items have historically
  required negotiation.
- **OF6**: CLI stable.
- **OF7**: Account credentials.

**Verdict (pre-Gate P1)**: **Tier 3**. Useful as a tertiary backup
or for public-facing research artifacts, but C2 partial-satisfaction
makes it inadmissible as primary.

### D9 — git-annex special-remote pointing at any of the above

- **Independent C1/C2/C3** scoring inherits from the underlying
  remote (D1..D8) that git-annex points at.
- **Adds**: tighter integration with the in-repo SHA-256 manifest
  (git-annex tracks per-file checksums in-repo).
- **Subtracts**: extra dependency on the `git-annex` toolchain at
  restoration time; auditor must install git-annex.

**Verdict (pre-Gate P1)**: **Tier 2** wrapper option. Improves
ergonomics for the maintainer but adds a tool dependency to the
restoration procedure (OF6 cost).

### D10 — Combination strategy

Examples:

- **D10.a**: D3 (R2 object-lock) primary + D7 (offline HDD) backup +
  D6 (IPFS) for manifest CID only.
- **D10.b**: D1 (GitHub release) primary + D7 (offline HDD) backup +
  D6 (IPFS) for manifest CID only.
- **D10.c**: D4 (S3 object-lock) primary + D5 (B2 object-lock)
  geographic / vendor diversity backup.

Combination strategies improve OF4 (SPOF) and the auditor-runnable
property of C3 by providing fallback paths. Each leg still scores
independently against C1/C2/C3.

**Verdict (pre-Gate P1)**: **Tier 1 conceptually** for production-
grade durability. Specific combination chosen at Gate P1.

---

## §6 Comparison matrix

| Option | C1 (round-trip) | C2 (immutable / CAS) | C3 (auditor-runnable) | OF2 cost/mo | OF3 egress | OF4 SPOF | OF6 stability | Tier (pre-Gate-P1) |
|---|---|---|---|---|---|---|---|---|
| D1 GitHub release (free) | SAT | SAT_PROC | SAT | $0 | $0 | Med | High | 1 |
| D2 GitHub release + LFS | SAT | SAT_PROC | SAT | $5-15 | $0 (limited) | Med | High | 2 |
| D3 Cloudflare R2 + object-lock | SAT | SAT | SAT | $0.75-$1.50 | $0 | Med | High | 1 |
| D4 AWS S3 + object-lock (compliance) | SAT | SAT (strongest) | SAT | $1.15-$2.30 | $2.5-$9 / round-trip | Low | High | 1 |
| D5 Backblaze B2 + object-lock | SAT | SAT | SAT | $0.30-$0.60 | Free up to 3x | Med | High | 1 |
| D6 IPFS pinning | SAT | SAT (CAS native) | SAT_PROC | $5-$15 | Free (gateway) | Med-High | Med | 2 |
| D7 Physical HDD offline | SAT | PARTIAL | SAT_PROC | $0 (one-off HW) | $0 | High alone, Low if 2+ | High | 3 (primary) / 1 (backup) |
| D8 Internet Archive | SAT | PARTIAL | SAT | $0 | $0 | High | Med | 3 |
| D9 git-annex wrapper | inherits | inherits | inherits + tool dep | inherits | inherits | inherits | Med | 2 |
| D10 Combination | mixed | strongest of legs | SAT (any leg) | sum of legs | min of legs | Lowest of legs | mixed | 1 conceptual |

(Costs above are estimates as of memo authoring date; all must be
re-verified inside the Gate P1 PR before any selection is finalised.)

---

## §7 Recommended tier ordering

**Tier 1 — primary candidates** (any one suffices to clear PR #361 §7
admissibility, pending Gate P1 verification of access and immutability
semantics):

1. **D3 — Cloudflare R2 + object-lock** — recommended default
   because (a) C2 satisfied structurally, (b) zero egress eliminates
   the round-trip cost concern, (c) S3 API stability, (d) lowest
   operational complexity per recommended-tier option.
2. **D5 — Backblaze B2 + object-lock** — closely tied with D3 on
   merits; lower storage cost but slightly less polished tooling.
   Excellent for cost-sensitive setup.
3. **D1 — GitHub release asset (free)** — recommended **only** when
   per-release size limits (~100 GB) are clearly above the epoch
   total. Immutability-by-procedure is weaker than D3/D4/D5 but the
   in-repo manifest closes the verification loop.
4. **D4 — AWS S3 + object-lock (compliance mode)** — recommended
   when maximum service-level immutability is required (e.g., for
   later compliance reasons). Egress cost is a meaningful trade-off
   vs D3.

**Tier 2 — secondary** (suitable as additional legs in D10, or as
fallbacks):

5. **D2 — GitHub release + LFS** — when D1 size limits become
   binding.
6. **D6 — IPFS pinning** — best as a manifest-CID-only leg or as
   a content-addressing layer over D3/D5.
7. **D9 — git-annex wrapper** — when tooling consistency is a
   priority.

**Tier 3 — tertiary / specialised**:

8. **D7 — Physical HDD offline** — best as a backup leg, not as
   primary.
9. **D8 — Internet Archive** — best as a public-facing supplemental
   backup; not primary.

**Recommended combination for current epoch** (subject to Gate P1
authorisation):

- **Primary**: D3 (Cloudflare R2 + object-lock) for raw + labels +
  split manifests
- **Backup**: D7 (offline HDD, one drive) for disaster recovery
- **Manifest sidecar**: D6 (IPFS CID published in a `manifest_cid`
  file committed in-repo) — content-addressed reference to the
  manifest itself, providing rigorous tamper-evidence

This combination satisfies all three criteria at SATISFIES level,
provides geographic / vendor diversity for OF4 SPOF, and minimises
ongoing cost.

The user may select any other Tier 1 or combination. The Gate P1 PR
records the choice; the Gate P2 PR verifies it.

---

## §8 Round-trip verification protocol design

This section drafts the verification protocol that Gate P2 will
execute, regardless of which destination is chosen. The protocol is
itself doc-only at the moment; implementation lives in the Gate P2 PR.

### Inputs to the verification

- the deposited byte set (whatever the destination)
- the manifest committed in-repo (per-file SHA-256, file path,
  expected size, expected row count, expected `time` min/max)
- the documented restoration procedure (per §5 entry for the chosen
  destination)
- a clean tracked worktree and a clean restoration directory
  (e.g., `artifacts/gate_p2_verification/<verification_id>/restored/`)

### Verification steps

1. **fetch** — execute the restoration procedure for every file
   listed in the manifest. The procedure writes bytes to the clean
   restoration directory.
2. **hash** — for each restored file, compute streaming SHA-256
   (same 8 MB block recipe as in Gate P1 PR-B; see PR #365 §6).
3. **size + path equality** — assert restored file count equals
   manifest entry count; assert each restored size matches the
   manifest's `size_bytes`.
4. **per-file SHA-256 equality** — assert restored SHA-256 equals
   manifest's `file_sha256` for every file.
5. **row count + ts boundary spot check** — for a deterministically-
   sampled subset (default: 5 files), re-derive row count and
   `time` min/max and compare against manifest.
6. **manifest authenticity** — recompute SHA-256 over the manifest
   file itself and assert it equals the value recorded in
   `epoch_freeze_manifest_hash` inside the Gate P2 frozen-epoch
   declaration (which lives elsewhere, outside this memo).
7. **report** — write `gate_p2_retention_verification_report.json`
   into `artifacts/gate_p2_verification/<verification_id>/` with
   per-file pass/fail, overall outcome, and timestamps. Failures
   HALT the Gate P2 acceptance; partial / mixed outcomes are
   classified per a verification ladder defined inside Gate P2 PR.

### Verification frequency

- **mandatory**: full verification on Gate P2 acceptance
- **mandatory**: re-verification on any retention destination change
  (e.g., re-pin, archive rotation, tag re-tag)
- **recommended**: annual sample verification (e.g., 10% random
  sampling) to detect silent bit-rot

### Independence requirements

- the verification must not modify the manifest or the deposited
  bytes
- the verification environment may **not** share keys with the
  deposit environment except for the documented restoration
  credentials (auditor-runnable property of C3)

This protocol is destination-agnostic; the only destination-specific
piece is the restoration command in step 1.

---

## §9 Integration with the existing OANDA 2026-05-31 archive

The OANDA 2026-05-31 archive (PR #364, master `ba80121`) is the
**leading raw-bytes candidate** for the new epoch. It currently sits
on local disk under `data/` (gitignored), with
`artifacts/oanda_archive_2026-05-31/candles_manifest.json` providing
per-file SHA-256 + size + row count + `time` boundaries.

For this archive to become binding under PR #361 §7, the deposit step
must:

1. transfer the 120 raw JSONL files to the selected destination
   (e.g., D3 R2 bucket)
2. apply the destination's immutability mechanism (e.g., R2 object-
   lock retention set to a sufficient horizon)
3. verify a first round-trip immediately after deposit:
   download → SHA-256 → equal `candles_manifest.json` entries
4. record the deposit outcome inside a follow-up doc-only PR that
   names the destination, the access procedure, and the
   immutability setting

Steps 1-3 are **execution steps** belonging to the Gate P2 PR (when
authored). Step 4's doc-only record could be authored before Gate P2
but cannot pre-approve the destination per §7.

The archive's `candles_manifest.json` already contains the per-file
SHA-256 needed for step 3 verification. No new manifest needs to be
generated for the raw bytes; the Gate P2 verification uses it
directly. (Labels and split manifests, generated later, will produce
their own manifests under separate Gate P2 sub-PRs.)

For the **manifest sidecar** strategy recommended in §7, the existing
`candles_manifest.json` can be pinned to IPFS to obtain a CID; the
CID is committed to a small file alongside the manifest in-repo. The
manifest file itself remains committed in-repo (small enough to not
trigger §7 in-repo size guard).

---

## §10 Risk register

- **R1 — Pre-approval drift**: an implementer reads this memo and
  treats the recommended Tier 1 set as approved. Mitigation: §0 and
  §1 re-declare "not pre-approved"; §7 ranking is labelled "subject
  to Gate P1 authorisation".
- **R2 — Immutability mode mis-set at deposit**: the destination
  supports object-lock but it was not enabled, or set to a too-short
  retention. Mitigation: Gate P2 verification step 4 must include a
  check that immutability mode is active and retention horizon is
  set to a configured minimum. The minimum value lives in the Gate
  P2 PR.
- **R3 — Manifest mutation after deposit**: the in-repo manifest is
  edited to match drifted destination bytes. Mitigation: the
  manifest's git commit SHA is recorded inside the epoch's frozen
  identity (separately, in a Gate P2 PR); git history immutability
  closes the loop.
- **R4 — Cost surprise**: egress fee from D4 (AWS) is larger than
  estimated under heavy auditor traffic. Mitigation: §5 D4 OF3
  records the cost order-of-magnitude; Gate P1 PR re-verifies
  current pricing and the user is offered an explicit choice.
- **R5 — Vendor lock-in by procedure**: restoration procedure
  references vendor-specific CLI flags that change. Mitigation:
  procedure cites a stable subset (S3 API for D3/D4/D5; `gh release
  download` for D1; `ipfs get` for D6); CLI version pinning is part
  of the documented procedure.
- **R6 — IPFS pin loss**: pinning service shutdown causes CID
  unfetchable. Mitigation: IPFS is recommended only as manifest-CID
  sidecar (small content easily re-pinned) and only in D10
  combination; never as sole leg.
- **R7 — Physical HDD failure undetected**: backup HDD bit-rot.
  Mitigation: §8 annual sample verification recommendation; never
  use D7 as sole leg.
- **R8 — Single-account suspension catastrophe**: GitHub / AWS /
  Cloudflare suspends the user's account. Mitigation: D10 multi-
  vendor recommended for combination.
- **R9 — Restoration procedure rots over years**: a 5-year-old
  procedure does not work today. Mitigation: the procedure document
  is itself committed in-repo + the SHA-256 manifest is committed
  in-repo; even if the destination becomes unreachable, the manifest
  preserves an authoritative referent for content identity.
- **R10 — In-repo manifest exceeds repo size guard over time**:
  many epochs each with their own manifest. Mitigation: manifests
  are small (per-pair entries × ~200 bytes; full archive
  `candles_manifest.json` is ~51 KB), within any plausible guard.

---

## §11 Open questions

- **Q1 — Candidate set completeness**: the §4 list is not
  exhaustive. Should the user nominate additional candidates
  (e.g., Wasabi Hot Cloud Storage, Storj, Filecoin, university-
  hosted object storage)? Recommendation: deferred to the Gate P1
  PR-B authoring step; this memo's set is a starting point.
- **Q2 — Tier 1 destination selection for the current epoch**: of
  the four Tier 1 options (D1, D3, D4, D5), which to verify at
  Gate P1? Recommendation: D3 (R2 + object-lock) as the proposed
  selection, pending user override.
- **Q3 — D10 combination chosen**: §7 recommends D3 + D7 + D6
  manifest-CID. Acceptable? Or simpler (single primary, no IPFS)?
  Recommendation: full D10 combination for production-grade
  durability; user may simplify if cost/operational complexity is
  prioritised over OF4 SPOF.
- **Q4 — Object-lock retention horizon**: how many years should
  object-lock be set to? Recommendation: minimum 5 years from
  deposit, extendable; final value chosen in the Gate P1 PR per
  research-time-horizon judgement.
- **Q5 — Egress budget for one Gate P2 verification + N auditor
  restorations per year**: how many auditor round-trips per year
  are expected? Recommendation: 1 verification + 0-1 auditor
  restorations/year, used to set the egress-cost estimate inside
  Gate P1 PR.
- **Q6 — Manifest-CID sidecar implementation**: where in the repo
  does the CID file live? Recommendation: `artifacts/oanda_archive_
  2026-05-31/candles_manifest_cid.txt` (single line CID + format
  comment).
- **Q7 — Labels / split manifests**: do they share the same
  destination as raw bytes, or sit in a separate bucket / release?
  Recommendation: same destination, separate prefix (e.g., R2 keys
  under `epochs/<manifest_id>/raw/...` vs `epochs/<manifest_id>/
  labels/...`). Decided in Gate P2 PR.
- **Q8 — Restoration procedure committed in-repo**: a standalone
  `RESTORATION_PROCEDURE.md` per epoch, or a section inside the
  Gate P2 PR? Recommendation: a standalone file under
  `docs/runbook/` per epoch.
- **Q9 — Auditor identity**: who counts as an auditor for the
  "auditor-runnable" requirement of C3? Recommendation: any
  external researcher with the documented credentials; the
  procedure is public, the credentials are not.
- **Q10 — Account-level access separation**: should the deposit
  account and the auditor-read account be separate (so that the
  auditor cannot accidentally modify deposited bytes)? Recommendation:
  yes, two roles with object-lock-strict permissions. Implemented
  in Gate P1 PR.
- **Q11 — Memo authority for re-evaluation**: when does the
  candidate set need re-evaluation? Recommendation: this memo is
  re-opened only when (a) a Tier 1 destination becomes unavailable,
  (b) a materially better candidate emerges, or (c) the user
  requests it.

---

## §12 Status carry-forward

Unchanged by this PR:

- V2-expanded Stage 2 = `HALTED_INPUT_UNAVAILABLE`
- F-1 = `UNEXECUTABLE_INPUT_UNAVAILABLE`
- PR #356 audit = `TARGETED_VERIFICATION_REQUIRED`
- Phase 27 / 28 / 29.0a verdicts preserved verbatim
- A0-broad β remains halted
- Gate P1 PR-B implementation plan (PR #365) locked; PR-B.0 / B.1 /
  B.2 each await independent explicit user authorisation
- No retention destination selected; PR #361 §7 "not pre-approved"
  binding intact

---

## Closing — what merging this memo PR does and does not do

Merging this PR locks the **evaluation framework** for Gate P2
retention destinations, **not** any destination selection. The
recommended Tier 1 ordering (§7) is reviewer-shorthand for "which
candidate set should the Gate P1 PR-B inspector prioritise documenting
under `candidate_retention_options_requiring_later_authorisation`". It
is **not** an approval of any specific destination.

Next step (post-merge): user authorisation decision for either

- **PR-B.0** (per PR #365 §11 stage split — Gate P1 inspector
  infrastructure), or
- **Gate P2 verification PR-A** (a forthcoming doc-only PR pinning
  the destination selection and round-trip protocol implementation
  plan, parallel to PR #365's role for PR-B), or
- both, in user-chosen order.

No auto-route. Either step requires independent explicit
authorisation.
