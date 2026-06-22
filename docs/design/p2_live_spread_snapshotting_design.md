# P2 Live Spread Snapshotting — Design (Doc-Only)

**Status:** DESIGN_ONLY — no implementation, no production change, no data collected under this PR.
**Scope key:** Production-Improvement Track **P2** of the post-audit roadmap
(`docs/design/research_development_roadmap_post_audit.md` §7.P2).
**Predecessor evidence binding:** P2 is **observational only**. Routing of any P1
(spread / cost-model replacement) decision against P2 output is **not** authorised by
this PR.
**Date authored:** 2026-06-22.
**Branch:** `docs/p2-root-logic-design`.

---

## 0. Binding constraints (apply to this PR and to the future implementation PR
chain seeded by this design)

This design PR introduces a **specification**. It does **not** authorise:

- order placement
- credentials access / env-var read
- broker write paths
- model execution
- Sharpe recomputation
- cost-model replacement (`P1` is a separate authorisation surface)
- production decision-loop modification
- artifact creation under the new path
- `.gitignore` change
- modification of `MEMORY.md`
- modification of prior verdict memos
- raw quote data commit

The future implementation PR chain (not opened by this PR) must observe the same
list, with the addition that quote-feed reads are read-only and never escalate to
order interaction.

---

## 1. Objective

Design an **observational** live spread snapshotting process that establishes a
durable empirical baseline for live bid/ask spread by pair, time-of-day, weekday,
and quote source. The output of P2 is the **observation surface only**; it does
**not** decide which cost model is used in production, and it does **not** by
itself unblock P1.

### 1.1 In-scope (for the future P2 implementation chain, not this PR)

- Read-only sampling of broker quote feed at a defined cadence.
- Storage of raw snapshots and aggregated profiles under a versioned artifact
  path.
- Generation of a human-readable spread profile report.
- A manifest that pins quote source, cadence, sampling window, and observation
  duration.

### 1.2 Out of scope (always, for this design surface)

- Order placement.
- Backtest replay of historical OANDA candles. (Candle close ≠ quoted spread;
  candle-derived spread is not P2 evidence.)
- Replacement of the existing fixed-pip cost assumption used by current paper
  evaluation.
- Modification of `run_paper_decision_loop.py` or `OandaQuoteFeed`.
- Any decision rule that consumes the spread profile.
- Any change to the Phase 9.16 v9 20p operational baseline behaviour.

---

## 2. What P2 observes (per snapshot row)

Each snapshot row is a single quote observation. The minimal field set is:

| Field | Type | Source | Notes |
| --- | --- | --- | --- |
| `pair` | string | quote feed | e.g. `EUR_USD`. PAIRS_20 universe per Gate P1 Amendment 1 pinning. |
| `ts_utc` | ISO-8601 string | local wall clock at sample | Always UTC. No local timezone. |
| `bid` | decimal | quote feed | Raw broker bid. |
| `ask` | decimal | quote feed | Raw broker ask. |
| `spread_pip` | decimal | computed | `(ask - bid) / pip_size(pair)`. `pip_size` table pinned at the implementation PR. |
| `quote_source` | string | configuration | `oanda_practice` / `oanda_live` / `replay_unavailable`. P2 forbids `replay_unavailable` as a primary source. |
| `session_bucket` | string | derived from `ts_utc` | One of `{tokyo, london, ny, overlap_london_ny, off_hours}`. Bucket boundaries pinned in the implementation PR. |
| `tod_bucket` | string | derived from `ts_utc` | UTC hour bucket (`H00..H23`). Coarser bucket for cross-day stability. |
| `weekday` | string | derived from `ts_utc` | `MON..SUN`. Excludes broker holiday gaps; weekend rows are still recorded but flagged. |

### 2.1 Optional context fields (allowed only if already available **without** new
model execution and **without** new data fetch)

These are **opt-in** for the implementation PR and **must not** introduce new
model invocations or fetches:

- `pair_volatility_proxy_pip_recent`: a rolling pip-range over the last `K`
  minutes if already maintained by `OandaBarFeed` or equivalent. P2 must not run
  a new model.
- `feed_latency_ms_observed`: only if the broker SDK exposes it as a side-effect
  of the read.
- `is_session_open_flag`: derived from a static calendar (no fetch).

Any other field is **deferred** to a follow-up design PR.

### 2.2 Fields explicitly excluded

- account balance / margin / positions: P2 is quote-only.
- order book depth: not assumed available; not in scope.
- inferred trade direction: out of scope.
- model output / score / signal: P2 is upstream of any model.

---

## 3. Output shape

### 3.1 Proposed future artifact path

```
artifacts/spread_profile/<profile_id>/
    raw/                       # raw per-snapshot JSONL files
        snapshots_YYYY-MM-DD.jsonl
    aggregated/
        profile.json           # per-(pair, session_bucket, weekday) aggregation
        profile_by_pair.json   # per-pair marginal aggregation
        profile_by_session.json
    report/
        report.md              # human-readable summary
        spread_distribution_<pair>.csv  # optional histogram dump
    manifest.json              # provenance + run parameters
```

`<profile_id>` is a content-addressed or time-stamped slug pinned in the
implementation PR. Format candidates (decision deferred to the implementation
PR):

- `profile_YYYY-MM-DD_to_YYYY-MM-DD_<source>`
- `profile_<short-hash-of-manifest>`

The path is **proposed**; no directory or file is created by this PR.

### 3.2 Snapshot raw file schema (`snapshots_YYYY-MM-DD.jsonl`)

One JSON object per line, exactly the fields in §2 plus `profile_id`.
No nested objects. UTC string timestamps only. No floats stringified.

### 3.3 Aggregated profile schema (`profile.json`)

```jsonc
{
  "profile_id": "...",
  "schema_version": "p2.v1",
  "generated_ts_utc": "...",
  "observation_window_utc": { "start": "...", "end": "..." },
  "pairs": [
    {
      "pair": "EUR_USD",
      "buckets": [
        {
          "session_bucket": "london",
          "weekday": "MON",
          "n_observations": 12345,
          "spread_pip": {
            "mean": 0.0, "median": 0.0, "p25": 0.0, "p75": 0.0,
            "p90": 0.0, "p95": 0.0, "p99": 0.0, "stdev": 0.0,
            "max_observed": 0.0
          },
          "missing_fraction": 0.0,
          "flags": []
        }
      ]
    }
  ],
  "global_summary": {
    "n_observations_total": 0,
    "n_pairs_observed": 0,
    "weekend_observations_excluded_from_summary": true
  }
}
```

### 3.4 Report schema (`report.md`)

A short, human-readable doc with:

- Header: `profile_id`, window, quote source, total observations, missing
  fraction.
- Per-pair table: median / p95 / p99 spread in pip, vs the **current fixed-pip
  assumption** used by paper evaluation. The "fixed-pip" reference is included
  for **observational comparison only**. It is **not** a routing claim that the
  fixed-pip assumption should be replaced — that is a P1 decision.
- Per-session table: median spread by `session_bucket`.
- Outlier listing: top-N highest-spread minutes per pair (for sanity inspection
  only).

### 3.5 Manifest requirements

```jsonc
{
  "profile_id": "...",
  "schema_version": "p2.v1",
  "quote_source": "oanda_practice",
  "broker_endpoint_class": "rest_polling",
  "sampling_cadence_seconds": 5,
  "observation_window_utc": { "start": "...", "end": "..." },
  "duration_hours_observed": 0.0,
  "pairs_covered": ["..."],
  "pip_size_table_version": "...",
  "session_bucket_definition_version": "...",
  "git_commit": "...",
  "implementation_pr_number": null,
  "operator_signoff_required": true
}
```

`git_commit` is the head of the implementation PR commit at run start.
`operator_signoff_required` enforces that a profile cannot be promoted to P1
input without a human signoff line in a later docs PR.

---

## 4. Safety constraints (for the future implementation PR chain)

These constraints govern the **future** implementation PR. They are stated here
so the design surface is bound:

1. Read-only broker quote interaction. No order, no margin, no position read.
2. No credentials, no env-var values, no account IDs in any logged line. Logs
   must redact at the line formatter.
3. No raw quote data committed to git unless a retention policy is **separately**
   authorised under Gate P2 retention destination evaluation
   (`docs/design/gate_p2_retention_destination_evaluation_memo.md`). Until then,
   raw is local only and `.gitignore`-respecting.
4. No modification of the production paper decision loop, the live loop runner,
   or any `Supervisor` / `run_exit_gate` path.
5. No replacement of the fixed-pip backtest assumption. The fixed-pip assumption
   is **decision-binding** until P1 is **separately** authorised.
6. No fetch of historical OANDA candles is performed by P2. The 2026-05-31 10y
   archive is **not** re-fetched.
7. The implementation PR must include a kill-switch CLI flag that stops sampling
   on signal. The kill-switch must be the default exit path.
8. The implementation PR must include a dry-run mode that produces a manifest
   and zero rows, for plumbing validation, before any real sampling is
   authorised.

---

## 5. Retention and provenance

### 5.1 Retention destination

Raw snapshot files are **local-first**. They are not committed to git, and they
are not pushed to any retention destination by the implementation PR. Retention
destination selection is owned by Gate P2 retention evaluation
(memo `gate_p2_retention_destination_evaluation_memo.md`), which lists D1..D10
candidates and pins no default at this PR. P2 spread snapshots inherit that
"not pre-approved" binding.

### 5.2 Manifest fields (binding)

The manifest in §3.5 is the **only** artifact eligible for git commit at the
implementation PR. Commit eligibility for `aggregated/` and `report/` is
**deferred** to a later docs PR and depends on retention destination.

### 5.3 Minimum observation duration before P1 can consume P2 output

The implementation PR must record at least:

- one full UTC week, including a weekend boundary, **and**
- coverage of `tokyo`, `london`, `ny`, and `overlap_london_ny` session buckets,
  **and**
- per-pair `n_observations` ≥ a threshold pinned in the implementation PR
  (recommendation: ≥ 1,000 per (pair, session_bucket) cell for the pairs that
  P1 may later reference).

**Recommended initial duration: 2–4 weeks of continuous sampling.**
This is a recommendation, **not a binding minimum**. The exact initial duration
is a **user decision** at the implementation PR.

A profile that does not meet the duration / coverage gate is labelled
`P2_PROFILE_INSUFFICIENT_FOR_P1_ROUTING` in its manifest. P1 must refuse routing
against such a profile.

### 5.4 Provenance binding

A profile is admissible as P1 input only if:

- the manifest declares `quote_source` from a live broker endpoint (not replay),
- the `git_commit` of the sampling code passes a separate review,
- coverage gate in §5.3 passes,
- a docs PR records operator signoff.

This binding is **structural**, not advisory: P1 design (when separately
authorised) must reject any profile that fails any of these checks.

---

## 6. Evaluation questions that P2 enables for future P1

P2 itself answers **none** of these. It provides the data on which P1 can later
answer them, **only if** P1 is separately authorised. These questions are
stated here so the P2 schema is sufficient to address them:

1. **Fixed-pip vs observed spread divergence.**
   By pair and session, how much does the observed median / p75 / p95 spread
   differ from the fixed-pip cost assumption currently used in paper
   evaluation? Is the divergence stable across weekdays?
2. **Pair / session drag concentration.**
   Which (pair, session) cells exhibit spread above a candidate cost hurdle? Is
   the drag concentrated in `off_hours` and `overlap_london_ny`?
3. **Spread filtering vs trade-rate trade-off.**
   If a spread filter were applied at the selector or post-filter layer, what
   fraction of trades would be filtered, and how does that compare to the
   per-trade EV gain? (Routing of this trade-off is a §11B audit and a P1
   decision, not a P2 decision.)
4. **Dynamic vs static cost hurdle.**
   Is a per-(pair, session) dynamic hurdle materially different from a single
   global pip hurdle? P2 enables the comparison; P1 owns the choice.
5. **Liquidity-window stability.**
   Are spread distributions stable across weeks? If they drift, the cost hurdle
   must be refreshed periodically — schedule TBD by P1.

---

## 7. Exit criteria for this design PR

- This design doc is merged.
- The shape of the future implementation PR is **pinned**, including:
  - field set (§2),
  - artifact path layout (§3),
  - safety constraints (§4),
  - retention binding (§5),
  - evaluation surface (§6).
- **No code is implemented under this PR.**
- **No production change occurs.**
- No track or downstream stage is authorised by this PR.

The implementation PR is **not** auto-routed. It requires explicit user
instruction before it is opened.

---

## 8. Relationship to other roadmap surfaces

- **P1 (spread / cost-model replacement):** Strictly downstream of P2. P1 must
  not begin until P2 has produced an admissible profile per §5. P2 produces no
  routing claim by itself.
- **§11B Root Logic Reassessment / Profit Logic Audit:** P2 is the **observational
  baseline** referenced by §11B "Cost hurdle / execution realism audit"
  (§11B §4 in `root_logic_reassessment_profit_logic_audit_design.md`).
  §11B may be co-authored with P2 because both are observational / diagnostic
  surfaces.
- **P3 (cost-aware sizing engineering):** Downstream of P1, not of P2 directly.
- **Phase 9.16 v9 20p production baseline:** Untouched by P2.
- **Phase 27 / 28 / 29 / 9.13..9.X-O verdicts:** Untouched by P2.
- **Foundation T1 / T2 / T3 / T4 stages:** P2 is independent of these. P2 does
  not promote, demote, or unblock any T-stage.
- **A0-broad halt, A0-narrow / A2-narrow FALSIFIED bindings:** Untouched.

---

## 9. Open questions deferred to the implementation PR

1. Sampling cadence default: 1s / 5s / 30s? (Default candidate: 5s.)
2. Pip-size table source-of-truth file path.
3. Session bucket boundary definitions (UTC ranges per session).
4. Operator signoff schema for promotion to P1 input.
5. Whether the implementation PR ships a single-pair smoke first or PAIRS_20 at
   once.
6. Whether `report.md` is committed at all, or only `manifest.json`.
7. Retention destination selection — owned by Gate P2 retention evaluation, not
   resolved here.
8. Exact `P2_PROFILE_INSUFFICIENT_FOR_P1_ROUTING` threshold values.
9. How long an admissible profile remains admissible before P1 must re-sample.
10. Whether multiple concurrent quote sources are sampled simultaneously
    (`oanda_practice` + a secondary feed) for cross-verification, or one source
    only.
11. Whether weekend rows are kept in raw but excluded from aggregation, or
    excluded at the sampler.

These are open. None of them is resolved by this PR.

---

## 10. Status carry-forward

- **P2 status after this PR merges:** `DESIGNED_NOT_IMPLEMENTED`.
- **P1 status after this PR merges:** `BLOCKED_ON_P2_OBSERVATION` (unchanged
  from roadmap).
- **Routing authority:** none granted by this PR.

End of design.
