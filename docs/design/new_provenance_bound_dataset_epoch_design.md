# New Provenance-bound Dataset Epoch — Design Memo

**Status:** Doc-only design memo. Authoring under the routing decision of
PR #360 (Tabular Evidence Epoch Rebase Routing Memo). Option 2 is the
PRIMARY route adopted by user instruction; this memo defines the
provenance-bound dataset epoch contract that future tabular control,
sentinel verification, and A0-broad work will be evaluated under.

**This memo does NOT:**

- acquire data
- handle credentials
- regenerate labels
- execute any model
- resume A0-broad β
- push the local Stage 2 implementation branch
- modify Phase 27 / 28 / 29.0a verdicts
- modify production
- modify `MEMORY.md`
- auto-route to any downstream PR

**Branch / base:**

- branch: `research/new-provenance-bound-dataset-epoch-design`
- base commit: `master @ 26be900` (PR #360 merge commit)
- file added: `docs/design/new_provenance_bound_dataset_epoch_design.md` (this file only)

---

## §1 — Carry-forward status (from PR #360)

The following are recorded as binding inputs to this memo. None of these
statuses are modified by this PR.

| Item | Status |
|---|---|
| V2-expanded Stage 2 | `HALTED_INPUT_UNAVAILABLE` |
| F-1 strict historic-anchor reproduction route | `UNEXECUTABLE_INPUT_UNAVAILABLE` |
| F-2 / F-3 | not executed |
| F-4 / F-5 / F-6 / F-7 partial outputs | non-authoritative |
| Stage 3 | not eligible to begin |
| A0-broad β | remains halted |
| PR #356 audit outcome | `TARGETED_VERIFICATION_REQUIRED` preserved |
| Historic nine-eval picture | Class U / empirically unreconfirmed |
| Phase 27 / Phase 28 / Phase 29.0a verdicts | preserved verbatim |
| Stage 2 implementation branch `research/tabular-targeted-verification-v2-expanded-stage2-preflight @ 0234ed3` | retained locally only; unpushed; not formal evidence |

The old Phase 28 §10 numeric anchor (`n_trades=34,626 / Sharpe=-0.1732 /
ann_pnl=-204,664.4 / val Sharpe=-0.1863`) is archived historic context
only. It is **not** an executable FAIL-FAST gate in the new epoch.

---

## §2 — Routes E1 / E2 / E3 — ranking and PRIMARY recommendation

### Route E1 — Frozen new epoch with newly acquired raw data

- target scope: PAIRS_20, M1 BA, extended historical span (illustrative
  ≥1095d, span TBD by feasibility, NOT bound here)
- status: **`BLOCKED_PENDING_DATA_ACCESS_FEASIBILITY`**
- blockers on the present machine:
  - OANDA credentials not configured locally
  - fetch tooling capability not established for full PAIRS_20 × extended span
  - rate-limit / retry / resume budget for the full pull not characterised
  - durable raw-byte retention destination not yet selected or verified
- escalation path: admissible only after a separate Data-Access
  Feasibility memo declares credentials + fetch tooling + retention
  storage all present and acceptable

### Route E2 — Frozen new epoch from currently-available local data only

- target scope: built from already-present local raw inputs, with span,
  cutoff, pair completeness, and required dependent data **selected only
  after a later read-only feasibility step (Gate P1)**
- status: **`LOCAL_DATA_CANDIDATE_EPOCH_PENDING_FEASIBILITY`** = PRIMARY
- **important: this memo does NOT bind the new epoch to 730d, to 365d,
  or to any fixed span.** The locally observed `*_730d_BA.jsonl` and
  `*_365d_BA.jsonl` inventories are **candidate inputs only**.

**Selection rule for the later feasibility decision (binding):**

The new epoch span / coverage selection at Gate P1 MUST follow this rule:

> Choose the **longest common, schema-valid, dependency-complete,
> time-aligned local-data span** that can support the declared
> signal-generation, label-generation, baseline-control, and candidate
> contracts simultaneously across the full intended pair universe.

Sub-rules:

- **730d** may be selected only if all required inputs and coverage
  checks pass under that span for every pair in the intended universe
  and for every dependent data series
- **365d** may be considered only as a **distinct lower-information new
  epoch** and only after explicit user approval — it is not an
  automatic fallback from a failed 730d preflight
- neither 730d nor 365d may be treated as a Phase 28 §10 replacement,
  reproduction, or restoration
- mixing per-pair spans is **prohibited** (the epoch is per-universe
  monolithic; if one pair fails coverage at the chosen span, the span
  must shrink uniformly across pairs OR the pair must be excluded by
  explicit declaration in the manifest, never silently)

### Route E3 — Indefinite halt

- emitted as status **only if** Gate P1 HALTs **and** Route E1 remains
  blocked
- preserves epistemic cleanliness; blocks research progress
- not adopted in this memo as PRIMARY

### Ranking (PRIMARY first)

| Rank | Route | Reproducibility | Feasibility now | Fair comparison | Retention cost | Time-to-info | Risk of new unreproducible chain |
|---|---|---|---|---|---|---|---|
| **PRIMARY** | **E2** (pending Gate P1) | good (frozen local span) | feasible | yes | moderate | shortest | **low IF retention enforced day-0** |
| DISSENT / escalation | E1 (blocked) | highest (extended span) | blocked (creds + retention) | yes | high | longest | low IF retention enforced day-0 |
| FALLBACK | E3 | n/a | n/a | n/a | nil | n/a | nil |

Adopting E2 as PRIMARY does **not** commit to any specific span, cutoff,
or pair universe. Those selections are deferred to Gate P1 + explicit
user authorisation.

---

## §3 — Dataset epoch identity and terminology

A new epoch is uniquely identified by the tuple **(manifest_id,
epoch_freeze_timestamp_utc, observation_start_timestamp_utc,
observation_end_timestamp_utc, span_days_effective, pair_universe_hash,
granularities_hash)**.

**Distinct, non-overlapping fields:**

| Field | Definition |
|---|---|
| `manifest_id` | content-addressed hash over the full epoch manifest (raw + labels + split + row-set + environment); the canonical referent for the epoch |
| `epoch_freeze_timestamp_utc` | UTC timestamp at which the immutable manifest is created; **NOT** the data cutoff |
| `observation_start_timestamp_utc` | earliest observation across accepted raw inputs that contributes to the epoch |
| `observation_end_timestamp_utc` | latest common-coverage observation across accepted raw inputs (actual common maximum, not nominal) |
| `span_days_effective` | computed from `observation_end - observation_start`; may differ from any nominal "730d" / "365d" label on source files |
| `pair_universe_hash` | content-addressed hash over the sorted pair list (frozen at freeze) |
| `granularities_hash` | content-addressed hash over `{granularity: derivation_rule_or_independent_raw}` (see §6 / topic 4) |

**Epoch identity is encoded by manifest_id (preferred), or by the
quadruple `(observation_start_utc, observation_end_utc, pair_universe_hash, granularities_hash)`.**

Epoch identity **must not** be conflated with:

- the day the source files were adopted
- the day the memo was authored
- the day Gate P1 was run
- nominal labels on source filenames (e.g. `_730d_BA.jsonl` does NOT
  guarantee 730 days of data)

Proposed epoch ID display format (for human-readable references):

```
epoch-<obs_start_yyyymmdd>--<obs_end_yyyymmdd>-PAIRS<n>-<granularities_short>-<manifest_id_short8>
```

Example (illustrative, not authoritative):

```
epoch-20240514--20260520-PAIRS20-M1BA-a1b2c3d4
```

The example span and pair count above are **illustrative only**. The
authoritative values are emitted by Gate P1 and frozen at Gate P2.

---

## §4 — Gate P1 — Read-only local-data + pipeline feasibility contract

Gate P1 is a **read-only preflight** that emits one of:

- `GATE_P1_PASS` — proceed to user authorisation step before Gate P2
- `GATE_P1_HALT_<reason>` — do not proceed; route E2 fails for the
  evaluated span

**Gate P1 is authorised by a separate PR. This memo does not authorise
Gate P1 execution. Gate P1 does NOT generate labels.**

### P1.1 — Raw-file presence + integrity check (read-only)

For each (pair, granularity) required by the candidate span:

- file presence verified
- byte SHA-256 computed and recorded
- row count computed and recorded
- timestamp min/max recorded
- schema fingerprint (columns + dtypes + bid/ask schema where applicable) recorded
- gap profile recorded (max gap; weekend / market-closure pattern noted; not corrected)

### P1.2 — Common-coverage computation (read-only)

- compute per-pair `[obs_start_i, obs_end_i]`
- compute intersection across pair universe: `[max_i obs_start_i, min_i obs_end_i]`
- compute `span_days_effective` from the intersection
- record per-pair contribution to the intersection boundary

### P1.3 — Pair-universe completeness (read-only)

- intended pair universe declared by the candidate (full PAIRS_20 by default)
- per-pair feasibility flag: present + schema-valid + coverage-sufficient
- HALT if any pair fails and span shrinking does not recover it

### P1.4 — Generator-code-path existence inspection (read-only)

- for signal-generation, ATR computation, label generation, R7-A
  feature construction, baseline (S-B) computation, control (S-E)
  computation, and the D-1 PnL identity harness, verify that:
  - generator module imports successfully
  - input-signature contract matches the raw-file schema
  - declared dependencies (sub-helpers) exist
- no execution; no labels written

### P1.5 — Required-input dependency inventory (read-only)

- enumerate the **actual required inputs** for each of:
  - signal generation
  - ATR
  - label generation
  - R7-A feature construction
  - baseline / control execution
  - future A0-broad sequence inputs
- for each required input, classify as:
  - **independent retained raw** (must be a separately retained byte
    stream in the epoch manifest), OR
  - **deterministically derived from M1 BA under committed,
    code-hashed derivation** (must reference the exact derivation
    function + version)
- **HALT if any required granularity / series cannot be soundly
  classified as one of the above.**
- **Prohibited:** silent substitution of derived candles for
  independently sourced historical inputs. If the historical pipeline
  relied on independently sourced M5 / H1 / D1 candles, the new epoch
  **may not** assume that M1-derived aggregates are equivalent. The
  assumption "M5/H1/D1 are derivable from M1 BA" is a **candidate
  design** to be **verified at Gate P1**, not an accepted fact.

### P1.6 — Retention destination feasibility (read-only)

- verify that at least one of the acceptable retention destinations
  (see §7) is presently available and accessible
- record the maximum byte budget for in-repo committed raw / labels
- record the access procedure for any external immutable destination
- **HALT if no retention destination is available** — a content-hash
  manifest without an accessible byte archive is **insufficient**

### P1.7 — Gate P1 output

If all checks pass:

- emit `GATE_P1_PASS` with: candidate `manifest_id_preview`,
  `observation_start_utc`, `observation_end_utc`, `span_days_effective`,
  `pair_universe_hash`, dependency inventory, retention destination
- write a doc-only preflight-report artifact (no labels, no model
  outputs, no row-level data)

If any check HALTs:

- emit `GATE_P1_HALT_<reason>` with the failing check identifier and
  the structured reason
- no proceeding step is authorised

**Gate P1 cannot, and must not, claim that a labels generator
"produces non-empty per-pair output." That claim belongs exclusively to
Gate P2.**

---

## §5 — Gate P2 — Dataset-construction validation contract

Gate P2 is the **dataset construction + validation** stage. It is
authorised **only after** Gate P1 emits `GATE_P1_PASS` **and** the user
issues an explicit authorisation decision selecting route, span, and
retention destination.

### P2.1 — Construction scope

- execute the signal-generation and label-generation pipelines into a
  **new epoch namespace** (e.g. `artifacts/epoch-<manifest_id_short8>/`
  — directory layout TBD by Gate P2 PR)
- write per-pair signal artifacts, labels parquet(s), split manifests,
  row-set manifests, and dependency-source-hash manifest
- **NO model training**
- **NO baseline / control numeric emission** (those belong to a later
  PR)
- **NO A0-broad execution**

### P2.2 — Validation checks (post-construction; pre-acceptance)

- **non-empty per-pair output**: each pair's labels parquet has
  `n_rows > 0` and per-pair labels schema matches the generator
  contract
- **manifest construction**: raw-data manifest, labels-dataset manifest,
  split manifest, and row-set manifest all written and hash-verified
- **split-manifest consistency**: train / val / test row-counts sum to
  the parent row-set; no overlap between splits
- **D-1 PnL compatibility**: the D-1 executable-PnL harness can be
  applied to the constructed labels (dry-run; no actual PnL aggregation
  emitted)
- **retained-bytes verification**: every byte referenced by the
  manifest is present in the declared retention destination and
  retrievable end-to-end (round-trip restoration test)

### P2.3 — Acceptance outcome

If all P2.2 checks pass and the user explicitly accepts:

- emit `NEW_EPOCH_DATASET_BUILT` with manifest_id, retention
  destination, and validation report
- the epoch becomes the binding referent for all downstream baseline /
  control / candidate work

If any check fails:

- emit `GATE_P2_HALT_<reason>`; the epoch is not adopted; no downstream
  work is authorised under that manifest_id

### P2.4 — Prohibited combinations

- **Gate P2 must not combine** dataset construction with baseline /
  control / A0-broad / model evaluation in the same PR
- **No automatic move** from `NEW_EPOCH_DATASET_BUILT` to baseline /
  control / model PRs — each subsequent step requires explicit user
  authorisation

---

## §6 — Input dependency inventory requirement

The new epoch must publish a **complete dependency inventory** as part
of the Gate P1 output, and Gate P2 must retain it under the manifest.

For each consumer (signal generation, ATR, label generation, R7-A
feature construction, S-B baseline, S-E control, D-1 harness, future
A0-broad sequence inputs), the inventory must record:

| Field | Definition |
|---|---|
| `consumer_id` | stable name of the consuming generator / harness |
| `required_input_id` | identifier of the input (pair × granularity × schema) |
| `classification` | one of `INDEPENDENT_RETAINED_RAW` or `DERIVED_FROM_M1_BA` |
| `derivation_function` | if `DERIVED_FROM_M1_BA`: fully-qualified function path and version |
| `derivation_code_hash` | SHA-256 of the derivation function's source |
| `accepted_at_gate_p1` | boolean — whether Gate P1 verified the classification |

**Binding rules:**

- any consumer requiring an input not classified as one of the two
  permitted classes → Gate P1 HALT
- any `DERIVED_FROM_M1_BA` classification must reference a committed,
  code-hashed derivation function; the assumption that derived candles
  are interchangeable with independently sourced candles must be
  explicitly justified or rejected at Gate P1
- if the historical pipeline (Phase 27 / 28 / 29.0a) relied on
  independently sourced higher-timeframe candles, the new epoch may
  not silently swap to derived candles without that swap being
  explicit, manifested, and acknowledged as a regime change

---

## §7 — Raw-byte + labels-byte durable retention policy

**Binding principle:** an epoch cannot become binding until the exact
accepted raw bytes and the exact generated labels bytes are stored in a
**retrievable immutable location**, verified end-to-end at Gate P2.

A committed SHA-256 manifest **without** an accessible byte archive is
**insufficient**.

**Acceptable retention destinations** are defined as the set of
destinations that satisfy *all* of:

1. byte-identity-restorable at acceptance time (round-trip test passes
   under Gate P2.2 retained-bytes verification)
2. immutability or content-addressed addressing of the stored bytes
3. accessible by a documented, auditor-runnable restoration procedure

**Candidate destinations** (each subject to availability + access
verification at Gate P1 / P2 before being declared accepted):

- **in-repo committed bytes** — admissible only if the total epoch byte
  budget falls below a project-acceptable repository-size guard (the
  guard value is set by the Gate P1 PR)
- **content-addressed immutable external archive** — admissible only
  if a specific archive is named, its access is verified, and its
  immutability semantics are documented

**Not pre-approved destination names.** This memo deliberately does
**not** name S3, GitHub release assets, S3 object-lock, IPFS, or any
specific external service as accepted. Such destinations may be
proposed at Gate P1 and become accepted only after their availability,
access, and immutability semantics are verified within the Gate P1 PR.

**Retention feasibility is a Gate P1 requirement.** A candidate epoch
whose retention destination cannot be identified or accessed at Gate P1
HALTs at Gate P1.

**Anti-pattern (this is the specific failure mode that caused the
present HALT):**

> An unversioned, gitignored, locally-regenerated parquet becoming a
> binding numeric authority — with the binding survived only as far as
> the local filesystem retained the bytes.

The new epoch contract forbids this pattern at every layer (raw,
labels, split, row-set, results).

---

## §8 — Temporal split / selection / test-touched-once / frozen-OOS policy

The new epoch adopts the following split-policy contract:

- temporal boundaries `(train_end, val_end, test_end)` fixed at Gate P2
  and recorded in the split manifest
- **test-touched-once**: the test split may be touched **exactly once**
  for any given research artifact; touch events are logged in an
  event-log entry per artifact
- **selection-only-on-validation**: hyperparameter selection, sweep
  selection, and model selection all read **only** the validation
  split; no test access during selection
- **frozen-OOS quarantine**: a trailing block (proposed default: last
  N% of the test split, exact N% chosen at Gate P2) is reserved as
  never-selection-touched and never-iterated; admissibility of frozen-
  OOS quarantine is **a Gate P2 PR-level decision**, not bound here
- **aligned-row-set policy**: when sequence-window-valid masks are
  required (for any future A0-broad-style work), aligned rows are
  generated **once at Gate P2**, frozen, manifested, and re-used
  across all baseline / control / candidate comparisons within the
  epoch; per-architecture re-generation of aligned rows is
  **prohibited**
- **prohibition**: `aligned_test` test-touched-twice patterns are
  forbidden at every layer

---

## §9 — Baseline + control regeneration prerequisite

Under the new epoch, before **any** A0-broad-style work, the following
must exist as accepted artifacts emitted by separate explicit PRs:

- **new S-B economic baseline** computed and locked under the new
  epoch's raw + labels
- **new S-E tabular control** computed and locked under the same
  epoch
- **new D-1 PnL identity validation** executed on the epoch's labels
- **row-set + provenance manifests** linking baseline, control, and
  any candidate to the same `manifest_id`
- **any sentinel / major-axis verification** scope re-evaluated under
  the new dataset (S-1..S-6 are **not auto-imported** from the old
  contract; their applicability under the new epoch is a downstream
  PR-level decision)

**Phase 28 §10 numbers remain archived reference only and are not
FAIL-FAST gates in the new epoch.** Cross-epoch numeric comparisons
(old anchor vs new baseline) are **not** evidence of agreement or
disagreement at the binding-gate level.

This memo does **not** define numeric pass-thresholds. Threshold-level
policy is downstream of baseline / control acceptance.

---

## §10 — Scientific adequacy review requirement

Even if Gate P1 + Gate P2 pass, the new epoch may be **scientifically
weaker** than the historical chain because the available local span
may be shorter or cover a materially different market regime.

The memo binds: **before** any baseline / control execution under the
new epoch, a **dataset adequacy review** must be performed and
recorded.

**Adequacy-review record content (mandatory):**

- **span statement**: declared `span_days_effective` with explicit
  comparison to the historical Phase 28 §10 nominal span; statement
  that the new epoch is not a span-equivalent substitute
- **regime acknowledgement**: explicit acknowledgement of any
  shorter-horizon limitations and any visible market-regime shifts
  within the new epoch (e.g. carry-regime changes, central-bank
  policy regime, volatility regime shifts known to fall within
  `[observation_start_utc, observation_end_utc]`)
- **fairness statement**: confirmation that all comparisons **within**
  the new epoch (baseline, controls, candidates) share identical
  epoch data and identical split policy — and are therefore mutually
  fair
- **prohibited claim**: any claim that the new epoch **restores the
  evidence strength of the former 1095d historical chain** is
  forbidden. The new epoch is its own evidence chain; it does not
  inherit or restore the historical chain's strength.

**Wording prohibitions** (forbidden phrases that may **not** appear in
any new-epoch artifact, report, or claim):

- "new epoch reproduces Phase 28 §10"
- "Phase 28 §10 baseline confirmed by new epoch"
- "Phase 28 §10 baseline disproved by new epoch"
- "Phase 28 §10 baseline restored"
- "historical execution re-verified"
- "tabular evidence reconfirmed"
- "PASS_TABULAR_EVIDENCE_RECONFIRMED"
- "FULL_TABULAR_EVIDENCE_REBUILT"
- "1095d evidence strength restored"
- "Class U lifted"

---

## §11 — Artifact + provenance manifest requirements

Every formal artifact emitted under the new epoch (from Gate P2 onward)
must include the following manifests:

| Manifest | Definition |
|---|---|
| `contract_hash` | SHA-256 over the executed contract (scope, cells, thresholds, derivation rules) |
| `code_hash` | SHA-256 over the canonical formal-harness file topology snapshot for the executing PR |
| `raw_data_manifest_hash` | SHA-256 over per-file SHA-256s of the accepted raw inputs |
| `labels_dataset_manifest_hash` | SHA-256 over the labels artifact bytes + schema descriptor |
| `split_manifest_hash` | SHA-256 over the train / val / test row-index manifests |
| `row_set_manifest_hash` | SHA-256 over the parent + aligned row-set manifests |
| `environment_manifest` | python version, lib versions, seeds, OS marker |
| `result_artifact_manifest` | SHA-256s of all formal result artifacts emitted by the PR |
| `retention_locator` | identifier of the retention destination + restoration procedure reference |

**Binding rules:**

- **independent recomputation requirement**: every formal result must
  be derivable from the manifests alone — no implicit dependency on
  uncommitted artifacts is permitted
- **prohibition on unversioned ignored parquet becoming a binding
  authority again** (lesson from the present HALT, codified here)
- a result emitted **without** the full manifest set is non-evidence

---

## §12 — Routing + stopping rules

The new epoch advances through a **strict, non-overlapping PR sequence**.
Each step is gated by explicit user authorisation; no automatic step
transitions.

### Required PR sequence

1. **This PR** — doc-only epoch-design memo (no execution, no data,
   no code)
2. **Gate P1 PR** — read-only feasibility preflight under the contract
   in §4
3. **User authorisation decision** — selection of route (E1 / E2 /
   E3), span, pair universe, granularities, retention destination; no
   code in this step
4. **Gate P2 PR** — dataset construction + validation under the
   contract in §5
   - emits raw / labels / split / row-set / dependency-source-hash
     manifests
   - emits retained-bytes verification report
   - **no LightGBM, no sequence model, no A0-broad execution**
5. **Baseline + control PR(s)** — under the contract in §9
   - new S-B baseline
   - new S-E control
   - D-1 PnL identity validation
   - **no A0-broad until separately authorised**
6. **Post-control decision PR** — only after baseline + controls are
   accepted, decide whether to implement A0-broad or re-run selected
   tabular axes under the new epoch

### Status outcomes pre-stated

- credentials / fetch capability absent at Gate P1 (Route E1): emit
  `DATA_ACCESS_INFEASIBLE`; E1 remains blocked; if E2 is also infeasible
  at Gate P1, escalate to E3 status
- Route E2 Gate P1 HALT: emit `LOCAL_DATA_INSUFFICIENT_FOR_NEW_EPOCH`;
  no Gate P2 authorised under that candidate span; re-evaluation under
  a different candidate span requires a fresh Gate P1 PR
- Route E2 Gate P2 HALT: emit `NEW_EPOCH_CONSTRUCTION_FAILED` with the
  failing check identifier; no baseline / control work authorised under
  that manifest_id
- Baseline / control validity failure: emit `NEW_EPOCH_CONTROLS_INVALID`;
  do **not** proceed to A0-broad or candidate axes

### Explicit prohibitions on automatic transitions

- **no automatic move** from Gate P1 → Gate P2 (user decision in step 3)
- **no automatic move** from Gate P2 → baseline / control
- **no automatic move** from baseline / control → A0-broad
- **no automatic move** from baseline / control → historical-verdict
  re-litigation (see §13)

---

## §13 — Relationship to historic tabular evidence (preserved)

The following three classes of evidence remain **strictly separate**
under the new epoch:

1. **Historic verdicts** (Phase 27 / Phase 28 / Phase 29.0a / PR #356
   audit / PR #360 HALT record): unchanged, Class U, empirically
   unreconfirmed. None of these are modified by the new epoch.
2. **New-epoch baseline / control results**: new evidence only, not
   numerically comparable to historic Phase 28 §10 numerics at the
   binding-gate level.
3. **New-epoch A0-broad results**: evaluated only relative to
   **new-epoch controls**; never cross-compared with historic verdicts
   at the binding-gate level.

**Binding rules:**

- no new-epoch result may **reconfirm**, **falsify**, **overwrite**, or
  **repair** a historic verdict automatically
- any human-judgement claim that a new-epoch result "informs" a
  historic interpretation must be recorded as **observational
  commentary only** and must not be presented as a formal gate
- the local Stage 2 implementation branch
  `research/tabular-targeted-verification-v2-expanded-stage2-preflight @ 0234ed3`
  remains unpushed and unaccepted; it may not be used as formal
  evidence; it may not be merged under the obsolete historic-anchor
  route; reusable infrastructure concepts (test-access guard,
  event-log ordering, factory provenance, dataset_status
  classification, F-1 anchor event sequence) may be considered for
  the new epoch only **after** the new-epoch contract is approved and
  re-targeted explicitly; **this PR does not push or modify that
  branch**

---

## §14 — Prohibited interpretations + forbidden wordings

The following claims are **not** asserted by this memo and may **not**
be attached to it or to any derived artifact:

- this memo does NOT acquire data
- this memo does NOT regenerate labels
- this memo does NOT resume A0-broad β
- this memo does NOT validate LightGBM ceiling claims
- this memo does NOT invalidate LightGBM ceiling claims
- this memo does NOT modify Phase 27 / 28 / 29.0a verdicts
- this memo does NOT modify PR #356 audit outcome
- this memo does NOT modify PR #360 HALT outcome
- new-epoch construction does NOT imply historical research was wrong;
  it implies the historical input chain was not durably retained

Forbidden wordings (registry, restated from §10):

- "new epoch reproduces Phase 28 §10"
- "Phase 28 §10 baseline confirmed by new epoch"
- "Phase 28 §10 baseline disproved by new epoch"
- "Phase 28 §10 baseline restored"
- "historical execution re-verified"
- "tabular evidence reconfirmed"
- "PASS_TABULAR_EVIDENCE_RECONFIRMED"
- "FULL_TABULAR_EVIDENCE_REBUILT"
- "1095d evidence strength restored"
- "Class U lifted"
- any claim that route E2 is a Phase 28 §10 replacement, reproduction,
  or restoration

---

## §15 — Authoring constraints honoured by this PR

- ✅ doc-only PR (1 file added; no source / no tests / no artifacts)
- ✅ no data fetch
- ✅ no credentials handling
- ✅ no labels generation
- ✅ no model execution
- ✅ no Stage 2 code-branch push or modification
- ✅ no A0-broad β resumption
- ✅ no prior verdict modification
- ✅ no production change
- ✅ no MEMORY.md edit inside this PR
- ✅ no auto-route to Gate P1 / Gate P2 / baseline / A0-broad

---

## §16 — References

- PR #355 — Phase 29.0b-α A0-broad design memo AMENDMENT
- PR #356 — Phase 27-29 Tabular Evaluation Validity Audit
  (`TARGETED_VERIFICATION_REQUIRED` preserved)
- PR #357 — V2-expanded design memo
- PR #358 — V2-expanded amendment (F-1 strict tolerance binding)
- PR #359 — V2-expanded Stage 1 infrastructure
- PR #360 — Tabular Evidence Epoch Rebase routing memo
  (`HALTED_INPUT_UNAVAILABLE` / `UNEXECUTABLE_INPUT_UNAVAILABLE`,
  Option 2 PRIMARY route)
- base commit for this PR: `master @ 26be900` (PR #360 merge)
