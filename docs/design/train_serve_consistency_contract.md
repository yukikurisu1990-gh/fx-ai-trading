# F-5 / F-8 Remediation — Ingestion Provenance & Train/Serve Consistency Contract

- **Document class:** design note / contract record (accompanies the F-5/F-8
  remediation PR; changes no verdicts)
- **Audit source:** `docs/design/project_wide_logic_audit_fable5_findings.md`
  (§4 F-5, §4 F-8; status `AUDIT_BLOCKERS_FOUND`)
- **Base:** master after PR #390 (P1-A + F-2)

## 1. What this remediation is — and is not

- **F-5 ingestion-provenance hardening is implemented by code guards and
  synthetic tests only.** No real market data was refetched, read for new
  evidence, or regenerated (`F5_REAL_DATA_REFETCH_NOT_PERFORMED`,
  `REAL_DATA_RERUN_NOT_PERFORMED`).
- **F-8 train/serve consistency is improved by explicit contracts, targeted
  code alignment, and synthetic tests.** No real model was trained; no real
  inference was run (`ML_STEP4_NOT_AUTHORISED`; no model artifacts change).
- **F-2 historical numerics are NOT rehabilitated.** Committed Phase 9.10–9.X
  reports remain records of the old scorer and old contracts
  (`HISTORICAL_PHASE9_NUMERICS_NOT_REHABILITATED`); nothing here recomputes,
  revalidates, or re-legitimises them.
- **Phase 9.16 v9 20p remains Tier 2 `VALID_OPERATIONAL_BASELINE` strictly as
  a fenced comparator with the audit caveats
  (`PHASE916_REMAINS_TIER2_FENCED_COMPARATOR_WITH_CAVEATS`)** — neither
  promoted nor demoted by this work.
- **These fixes do NOT authorise ML Step 4.** T2 retention, byte-admissibility
  review, and new-epoch adoption remain separate, explicitly-gated steps
  (`T2_EXECUTION_NOT_PERFORMED`, `BYTE_ADMISSIBILITY_NOT_APPROVED`,
  `NEW_EPOCH_NOT_AUTHORISED`). No production readiness is claimed
  (`PRODUCTION_READINESS_NOT_CLAIMED`).

## 2. F-5 — ingestion provenance contract (statuses: `F5_INGESTION_PROVENANCE_HARDENED_BY_TESTS`)

- **Fetch truncation fails closed (F5-A/B):** candle/archive fetches write to
  a temporary `.incomplete` path and promote to the final filename only after
  fully-successful completion; any mid-stream failure leaves only the
  incomplete file and exits non-zero. A truncated file can no longer
  masquerade as a complete span.
- **Inventoried-span overwrite guard (F5-C,
  `F5_INVENTORIED_SPAN_OVERWRITE_GUARDED`):** fetch/retrain paths refuse to
  overwrite any candidate span file whose basename is referenced by committed
  Gate P1 PR-B.1 / Foundation T2 metadata, unless an explicit override flag is
  passed. Span identity can no longer be silently re-pointed at different
  bytes while committed SHA evidence refers to the old bytes.
- **Archive resume requires completion proof (F5-D):** a non-empty file is no
  longer treated as complete; resume skips a file only when its sidecar
  completion marker exists, parses, and matches the file. Otherwise the file
  is re-fetched via the atomic path or the run fails closed.
- **Model manifest provenance (F5-E,
  `F5_MODEL_MANIFEST_PROVENANCE_HARDENED`):** the training manifest now binds
  a model to its inputs: data logical IDs (basenames only — no personal
  absolute paths), per-input SHA-256, time bounds, row counts, price mode,
  feature version, label contract, cost contract, code SHA, and a config
  hash. Models trained before this change (the current `models/lgbm/`
  contents) predate the manifest contract and the F8-A tie-break alignment;
  any retrain is a separately-authorised real-data step.

## 3. F-8 — train/serve consistency contract (statuses: `F8_TRAIN_SERVE_CONTRACT_HARDENED_BY_TESTS`)

- **Label tie-break (F8-A, `F8_LABEL_TIE_BREAK_CONTRACT_ALIGNED`):** the
  single contract for training, evaluation, and any barrier semantics is
  **conservative SL-first on a same-bar TP+SL touch** (strict `<` in the
  TP-clears test), matching the backtest lineage and the Stage22+ harnesses.
  The production trainer previously resolved ties TP-first; it is now
  aligned. No labels were regenerated over real data in this PR.
- **ATR warmup (F8-B, `F8_ATR_WARMUP_GUARDED`):** label/trainer ATR uses an
  explicit `min_periods = ATR period` warmup; rows without sufficient history
  produce no label instead of degenerate near-zero barrier widths.
- **Live barrier anchor (F8-C, `F8_LIVE_BARRIER_ANCHOR_ALIGNED`):** the
  contract TP/SL barriers consumed by the software exit path
  (`run_exit_gate` via the runner's barrier map) derive from the **actual
  recorded fill price** (the label contract's entry convention), never
  silently from the decision-bar mid close; a missing fill price fails
  closed — no price barriers are set, an explicit
  `barrier_anchor_unavailable` warning is logged, and the position is
  governed by the time stop. **Documented residual (deferred, not
  production-ready):** OANDA pre-fill protective orders
  (`takeProfitOnFill`/`stopLossOnFill`) are inherently constructed before
  the fill and therefore still use the decision-bar close as an
  explicitly-labeled PROTECTIVE proxy (server-side crash protection only,
  not the contract barriers); re-anchoring them post-fill requires a
  broker trade-amend API and remains a follow-up. Divergence is bounded by
  |fill − decision close|.
- **Feature as-of time (F8-D, `F8_FEATURE_ASOF_CONTRACT_ALIGNED`):** the live
  loop's feature as-of time is the decision bar's **close** time, so the
  just-completed decision bar is included — the same completed-bar snapshot
  training and backtests use. In-progress bars remain excluded at the feed
  layer.
- **MTF buckets (F8-E, `F8_MTF_COMPLETED_BUCKET_CONTRACT_ALIGNED`):** every
  multi-timeframe feature path — including the resample fallback — uses only
  **completed** higher-timeframe buckets, matching the training-time
  shift(1) definition. The stale docstring citing an invalidated lookahead
  numeric was corrected.
- **Post-cost EV (F8-F, `F8_POST_COST_EV_CONTRACT_HARDENED`):** the canonical
  EV unit across strategy families is **pips, post-cost**
  (`pips_post_cost`). Cost is accounted exactly once: LGBM's EV is post-cost
  by construction (spread embedded in B-2 bid/ask label geometry; the live
  spread gate additionally applies at entry), and other strategy families
  must either produce comparable pips-post-cost EV (with an SL term and
  explicit cost treatment) or be marked non-comparable. The Meta layer
  rejects candidates with missing or non-comparable EV units — it never ranks
  mixed units.
- **Force-fallback (F8-G, `F8_FORCE_FALLBACK_PRODUCTION_GUARDED`):**
  `force_fallback` defaults to **False**: when every candidate fails the
  EV/confidence filters, production-like runs adopt nothing. The Cycle 6.4
  "≥1 trade per cycle" guarantee is now an explicit opt-in for smoke/test
  runs only.

## 4. Boundary notes

- Committed historical result artifacts and old reports are untouched.
- No `data/` files, no new real `artifacts/` evidence, and no model outputs
  are part of this PR; all tests use tiny synthetic in-memory rows or
  tmp-path fixtures.
- The deployed `models/lgbm/` artifacts were trained under the pre-alignment
  contracts; consumers must treat backtest-vs-live comparability as improved
  **prospectively only** — a contract-consistent retrain (real-data,
  separately authorised) is required before any uplift claim, and any such
  claim additionally requires the T2 → byte-admissibility → new-epoch → ML
  Step 4 gate chain.
