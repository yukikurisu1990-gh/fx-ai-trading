# Gate 3a — M15 dataset/epoch adoption record (Family-A M15-first)

- **Document class:** doc-only dataset/epoch adoption record + metadata
  artifacts. Not an implementation PR, not a model-training PR, not a
  validation/holdout evaluation PR, not an execution PR. **Nothing is trained,
  no strategy performance is computed, no raw candles are read or committed.**
- **Branch:** `docs/m15-gate3a-dataset-epoch-adoption`
- **Base:** master `2952ba80ac623e06618849624b6b4ae25443a9d7` (post PR #430 merge).
- **Code SHA:** `2952ba80ac623e06618849624b6b4ae25443a9d7`
- **As of:** 2026-07-07 (UTC).
- **Binding inputs:** the frozen PR #429 contract; the PR #430 design audit
  tightenings T-1…T-7.

## Statuses

- **`M15_GATE3A_DATASET_EPOCH_ADOPTION_PROPOSED`**
- Carried: `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_ACCEPTABLE_FOR_GATE3A_DATASET_EPOCH_ADOPTION`
  · `M15_FIRST_COST_HURDLE_AWARE_PREREGISTRATION_PROPOSED`
  · `POST_M1_RESEARCH_PROGRAM_ROADMAP_ACCEPTABLE_FOR_SELECTED_FAMILY_PREREGISTRATION`
  · `M1_FLAGSHIP_FIRST_RUN_QUESTION_CLOSED_FAILED_PREREGISTERED_CRITERIA`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** · **`NO_EXECUTION_PERFORMED`**
- Forward-epoch sub-status: **`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS`**

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `PRODUCTION_READY`, `M15_AUTHORISED`, `H1_AUTHORISED`,
`H2_STARTED`, `PHASE_C2_STARTED`, `NEW_EPOCH_ADOPTED`, `BYTE_ADMISSIBLE`, or
`MEETS`; those tokens appear only in this prohibition list.

---

## 1. Executive summary

Gate 3a establishes the dataset/epoch adoption record the frozen M15 contract
requires before any implementation may read or derive data. It produces
metadata-only artifacts under `artifacts/m15_gate3a/`.

**What is fixed now:** the M1→M15 **design-data derivation contract**; the
**effective-N estimator** (T-6 requires this at gate 3a); a machine-checkable
**source-level no-overlap proof** against the dead window (T-7); the
**cost-table production plan** (Option B — deferred to implementation, fully
specified); and the retention/provenance binding.

**What is explicitly NOT adopted — a disciplined WAIT:** the **forward epoch
(validation + holdout) cannot be adopted.** The forward epoch starts no earlier
than 2026-04-25 and needs validation ≥ 3 months **plus** holdout ≥ 2 months
(≈ 5 months). The committed `365d_BA` source **ends 2026-04-24T20:59Z** — it
contains **zero** forward-epoch bars — and as of 2026-07-07 only ~2.4 months
have elapsed since the forward floor. Per the frozen contract's own rule
("if insufficient forward data has accrued, adoption waits — `INSUFFICIENT_SAMPLE`
exists precisely so impatience cannot shrink the holdout"), **forward-epoch
adoption is blocked until the data accrues** (earliest ≈ 2026-10).

**What this does NOT authorise:** no implementation, training, validation,
holdout evaluation, strategy metrics, execution, epoch adoption of the forward
data, `730d_BA`, or `3650d_BA`. This satisfies PR #429/#430 by fixing every
gate-3a-owned item and honestly deferring what cannot yet exist.

**Next gate:** the code-only implementation PR (gate 5) may proceed for the
**design-data derivation + aggregation machinery** (it is data-touching but
produces the metadata artifacts + value-pinned tests) **only after** gate 3a is
accepted; the forward-epoch half of adoption resumes as a gate-3a continuation
once the data exists. Both remain doc/metadata + code with **no run**.

## 2. Scope and non-authorisation

No implementation; no training; no validation computation; no holdout
evaluation; no strategy performance metrics; no trade signals; no model
predictions; no execution; no execution evidence; no model binaries; no
production-readiness claim; no `730d_BA`; no `3650d_BA`; no Phase C2; no
H2/H3; no forward-epoch adoption (blocked). No raw candles, raw price rows,
or trade-level outputs are committed.

## 3. Design-data M15 derivation artifact

Artifact: `artifacts/m15_gate3a/design_m15_derivation_manifest.json`
(+ schema `design_m15_inventory.json`).

- **Input identity:** the 20 committed `365d_BA` M1 files by the PR-B.1
  inventory (SHA-256 + size + ts-bounds); fixed **PAIRS_20**; source epoch
  `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`.
- **Design span cut:** **2025-04-25 → 2026-02-28** (exploratory/design-only,
  never evidence), which is the committed epoch **minus** the dead window.
- **Aggregation contract (from the frozen contract):** UTC 15-min bucket
  start; per-side bid/ask OHLC; no mid construction; **`n_source_bars == 15`**
  event/label eligibility; incomplete buckets diagnostics-only; no imputation;
  no synthetic weekend bars; missing-minute gap report; quoted-spread field;
  per-pair `pip_size_for` authority.
- **Byte-level production deferred to gate 5:** the derived M15 files, their
  SHA-256 checksums, and the **value-pinned JPY + non-JPY aggregation tests**
  are produced by the code-only implementation PR (the aggregation code does
  not exist yet and must be created + audited before any real derivation).
  Fabricating checksums here is forbidden; `design_m15_inventory.json` is a
  fixed **schema + aggregate-assertion contract** (20 files; all `ts_max ≤
  2026-02-28T23:59:59Z`; zero dead-window bars) to be populated at gate 5.

## 4. Forward-epoch adoption artifact — BLOCKED (adoption waits)

Artifact: `artifacts/m15_gate3a/forward_epoch_adoption_manifest.json`
(+ empty `forward_epoch_inventory.json`).

- **Frozen requirement:** forward epoch start ≥ 2026-04-25; validation ≥ 3
  months; holdout ≥ 2 months; purge/embargo 25 M15 bars; disjoint,
  chronological; research-only.
- **Feasibility finding (decisive):** the committed source epoch's latest bar
  is **2026-04-24T20:59Z**, so the repository holds **zero** forward-epoch
  bars; there is no forward source to adopt. As of **2026-07-07**, only
  **~2.4 months** have elapsed since the 2026-04-25 floor — insufficient for
  the ≈ 5-month (validation + holdout) requirement.
- **Verdict:** **`INSUFFICIENT_SAMPLE` — adoption waits.** Earliest
  data-complete estimate ≈ **2026-09-25** (validation ~2026-04-25→2026-07-25 +
  purge + holdout ~2026-07-25→2026-09-25); earliest feasible forward adoption
  ≈ **2026-10** after accrual + a Gate-P2-style adoption + a byte-level
  no-overlap proof. The forward epoch is **not production-ready** and is
  research-only when eventually adopted.
- Exact validation/holdout boundaries, the forward inventory/checksums, and
  the retention binding remain **[FIXED-AT gate-3a continuation]** when the
  data exists.

## 5. No-overlap proof against the dead window

Artifact: `artifacts/m15_gate3a/no_overlap_proof.json`.

Boundary constants (UTC): design `2025-04-25 → 2026-02-28T23:59:59Z`; dead
window `2026-03-01T00:00:00Z → 2026-04-24T23:59:59Z`; forward floor
`2026-04-25T00:00:00Z`. Machine-checkable assertions, evaluated from committed
metadata:

- **A1** design_end < dead_window_start — **PROVEN_TRUE**.
- **A2** dead_window_end < forward_epoch_floor — **PROVEN_TRUE**.
- **A3** committed epoch ts_max (`2026-04-24T20:59Z`) < forward floor ⇒ the
  committed epoch contains **zero** forward bars ⇒ forward data must be a new
  source — **PROVEN_TRUE**.
- **A4** the dead window equals the consumed M1 holdout window and lies
  strictly between design and forward ⇒ R-2b exclusion is structural —
  **PROVEN_TRUE**.
- **A5** design-M15 artifacts must satisfy per-file `ts_max ≤ 2026-02-28T23:59:59Z`
  — **PENDING at implementation** (enforced by the inventory contract).
- **A6** forward artifacts must satisfy per-file `ts_min ≥ 2026-04-25T00:00:00Z`
  — **PENDING until forward data exists**.

**T-1 feature warm-up leakage (explicitly addressed):** dead-window data is
**never loaded**; all indicators/context (incl. H1/H4) initialise **only** from
forward-epoch bars; the first **W** forward bars are an event-ineligible
warm-up burn-in with **W ≥ the longest feature lookback including H1/H4
context**; exact W frozen at implementation and verified at the gate-6
source-contamination audit. No validation/holdout feature can read a
dead-window price via warm-up, aggregation context, or spread tables.

## 6. Effective-N estimator

Artifact: `artifacts/m15_gate3a/effective_n_estimator_spec.json` — **approved
here (T-6 places it at gate 3a)**. Specification only; no count computed.

- **Raw event count** `N_raw` per role.
- **Horizon overlap adjustment** for H = 24 M15 bars: `N_eff_pair =
  N_raw_pair / rho_h`, `rho_h = 1 + (H−1)·mean_overlap_fraction`
  (non-overlapping ⇒ rho_h→1).
- **Cross-pair dependence discount:** `rho_x = 1 + (P−1)·mean_abs_pairwise_corr`
  (correlation of per-pair daily PnL, estimated on **design data only**,
  frozen); `N_eff = (Σ N_eff_pair)/rho_x`.
- **Daily-aggregation dependence** noted; per-currency exposure is the monitor.
- **Reporting:** raw AND effective counts, per role (validation/holdout), at
  portfolio + per-pair granularity.
- **Failure handling:** holdout `N_eff < 400` ⇒ `INSUFFICIENT_SAMPLE` (no
  acceptance); insufficient validation sample ⇒ family closes or adoption
  waits; both `≥ 1,000 raw holdout trades` AND `N_eff ≥ 400` required. No
  strategy metrics are computed at gate 3a.

## 7. Cost-table plan (Option B — deferred, fully specified)

Artifact: `artifacts/m15_gate3a/cost_table_plan_or_metadata.json`.

Producing the tables requires reading design-span raw candles via the
non-existent aggregation code, so **Option B is selected**: production is
deferred to the implementation PR, from **design-span data only**,
human-approved **before any gate-7 execution authorisation**, with **no
ambiguity** about content: per-pair × session (Asia/Europe/US UTC) **median**
spread (primary), **p90** (mandatory stress), **p95** (mandatory diagnostic,
T-7); padding **0.3 pip**; cell **0.5 pip**; `cost = median + 0.3 + 0.5`;
stresses 2× and p90-substituted; `pip_size_for` conversion with value-pinned
JPY/non-JPY tests; quote-cost-validity scope. No raw data is read at gate 3a.

## 8. Retention and provenance binding

- **Source identity:** `RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1` M1 files,
  committed PR-B.1 inventory (SHA-256 lineage).
- **Retained artifacts:** `artifacts/m15_gate3a/*.json` (metadata-only,
  scrub-clean per `scrub_report.json`).
- **No exposure:** no personal/local paths, no secrets, no Google Drive / R2
  endpoints or keys.
- **Reproducibility:** boundary constants + committed-metadata assertions are
  deterministic; derived-data reproducibility (byte-identical from source) is
  a gate-5 requirement.
- **Code SHA:** `2952ba80…`; **branch:** `docs/m15-gate3a-dataset-epoch-adoption`;
  **base:** master `2952ba80…`.

## 9. T-1 … T-7 compliance

| Tightening | Handling at gate 3a |
| --- | --- |
| **T-1** dead-window warm-up | Made explicit in `no_overlap_proof.json` + §5: dead window never loaded; forward-only warm-up burn-in of W ≥ longest lookback; verified at gate 6. |
| **T-2** EV payoff semantics | Pointer carried forward (§9 of contract); EV not implemented here; recorded for gate 5. |
| **T-3** ratio < 3.0 blocker | Recorded as a **downstream gate-7 execution blocker** (median eligible barrier/cost ratio computed at implementation from design data; < 3.0 blocks execution pending new ruling). Not computed here. |
| **T-4** timeout share trigger | Pointer carried forward: timeout share mandatory future evidence; holdout > 60% ⇒ mandatory post-run-audit before citation. |
| **T-5** maxDD notional | Pointer carried forward: fixed notional = 10,000 pips unless a new explicit ruling. |
| **T-6** data-dependent deferrals | **Effective-N estimator approved here** (§6); **cost tables Option-B deferred** to implementation (§7); concurrency/exposure caps + holiday calendar deferred to implementation, approved before gate 7. |
| **T-7** no-overlap proof + p95 | Source-level proof produced (§5, A1–A4 PROVEN); byte-level A5/A6 pending; **p95 diagnostic** required in the cost-table plan (§7). |

## 10. Blockers and open questions

- **Before implementation (gate 5):** value-pinned JPY/non-JPY aggregation
  tests; byte-level design-M15 derivation + inventory/checksums; the design→
  M15 boundary/gap/weekend edge tests. (Gate 5 is code-only, no run.)
- **Before execution (gate 7):** cost tables (Option B) produced + approved;
  concurrency/exposure caps + holiday exclusion calendar fixed; the **T-3**
  median barrier/cost ratio computed (≥ 3.0 or a new ruling); the
  source-contamination audit (gate 6) verifying T-1 warm-up.
- **Before any forward run:** **forward-epoch data accrual** (≈ 5 months from
  2026-04-25) → gate-3a continuation adoption with the byte-level no-overlap
  proof; this is the **binding data-insufficiency risk** and is the reason
  the forward epoch is not adopted now.
- **Before any production claim:** disjoint replication + separate paper/live
  gates.

## 11. Recommendation for next gate

**Proceed to the code-only implementation PR (gate 5)** for the **design-data
M15 aggregation machinery** — it produces the deferred metadata (design-M15
inventory/checksums, aggregation identity) and the value-pinned tests, with
**no training, no validation/holdout computation, and no execution.** In
parallel, **the forward-epoch adoption remains a documented WAIT**
(`INSUFFICIENT_SAMPLE`) and resumes as a gate-3a continuation once ≥ 5 months
of forward data have accrued (earliest ≈ 2026-10). A Fable 5 / ChatGPT review
of this gate-3a record is appropriate before gate 5 given the forward-epoch
block is a material finding. Nothing is authorised to run.
