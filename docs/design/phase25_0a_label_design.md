# Phase 25.0a-α — Path-Quality Label Design (binding contract for 25.0a-β implementation)

Doc-only PR that fixes the numerical thresholds, algorithm
specification, causality contract, parquet schema, and unit-test
contract for the path-quality label dataset that Phase 25.0a-β will
generate. **No code, no eval, no implementation in this PR.**

> **Mandatory framing inheritance** (from Phase 25 kickoff PR #280):
>
> *Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
> feature-class redesign phase.*
>
> The numerical thresholds in this doc are **design constants**. They
> are fixed before 25.0a-β implementation and **MUST NOT be tuned in
> response to observed label balance**. If 25.0a-β observes a
> pathological label distribution, it must stop and report — no
> in-place retuning.

## §1. Stage purpose

Phase 25 kickoff (PR #280) §11 mandated that the path-quality binary
label's exact numerical thresholds be fixed in 25.0a, before
implementation. This 25.0a-α doc fixes them.

This is the binding contract that 25.0a-β implementation must obey.
The same doc-first → implementation pattern was used in the NG#10
chain (PRs #275 review → #276 envelope confirmation → #277
implementation) and proved effective at preventing silent threshold
drift during coding.

## §2. Scope

**In scope**:
- Numerical thresholds for the four kickoff §11 invariants.
- Algorithm specification (signal cadence, horizon, traversal, fill
  semantics).
- Margin filter behavior.
- Same-bar resolution rule.
- Direction shape (2 rows per signal_ts).
- ATR basis (causal M5).
- Causality contract.
- Parquet schema for `path_quality_dataset.parquet`.
- Diagnostic columns + downstream-feature prohibition.
- Pathological-balance halt-and-report rule.
- Unit-test contract (≥ 13 tests).
- Runtime budget (smoke + full).

**Explicitly out of scope**:
- Implementation of any label generation script.
- Generation of any dataset.
- Any feature-class signal generation (deferred to 25.0b+).
- Modifying Phases 22-24 docs / artifacts.
- Modifying Phase 25 kickoff (PR #280).
- Relaxing NG#10 / NG#11.
- Reusing 24.0a artifacts as labels (per kickoff §7).

## §3. Design constants (FIXED)

These values are **binding** and **MUST NOT be tuned** in response
to 25.0a-β observed label balance.

| Constant | Value | Source / rationale |
|---|---|---|
| `K_FAV` | **1.5** | Favourable threshold multiplier on ATR; matches Phase 24 `TP_ATR_MULT` for cross-phase comparability |
| `K_ADV` | **1.0** | Adverse threshold multiplier on ATR; matches Phase 24 `SL_ATR_MULT` |
| `M_MARGIN` | **2.0** | Margin: favourable threshold (in pip) must be ≥ `M_MARGIN × spread_at_signal` |
| `H_M1_BARS` | **60** | Horizon = 60 M1 bars (= 4 M15 bars = 1 hour); single-horizon design (multi-horizon deferred per direction §3) |
| `SIGNAL_TF` | **`M5`** | Signal candidate cadence at every M5 bar boundary |
| `ATR_TF` | **`M5`** | ATR computed on M5 bars, causal `mid_c.shift(1).rolling(N)` |
| `ATR_N` | **20** | ATR rolling window length on M5 (consistent with Phase 23.0a) |
| `PAIRS` | canonical 20 | Phase 22-24 universe |
| `SPAN_DAYS` | **730** | Phase 22-24 span |

> Values may not be retuned by 25.0a-β. If 25.0a-β finds the dataset
> unsuitable (per §12 pathological-balance rule), the implementation
> halts and the user decides whether to open a follow-up PR with
> revised constants.

## §4. Algorithm specification

For each pair × every M5 bar boundary `t` × each direction
∈ {long, short}:

### §4.1 Pre-flight checks

1. The next M1 bar at `t + 1 minute` must exist.
2. The path window `[t+1, t+H_M1_BARS]` must lie within the M1
   index (no truncation; rows where path is short are dropped).
3. ATR at `t` must be finite (rolling window sufficiently warmed up).

If any pre-flight fails, the row is **dropped** (not labeled).

### §4.2 Threshold derivation

```
atr_pip   = atr_at_signal_M5_causal(pair, t)
spread_pip = ask_close[t] - bid_close[t], in pips
fav_thresh = K_FAV × atr_pip      # 1.5 × atr_pip
adv_thresh = K_ADV × atr_pip      # 1.0 × atr_pip
```

### §4.3 Margin filter (admissibility)

If `fav_thresh < M_MARGIN × spread_pip` (i.e., 1.5 × atr_pip
< 2.0 × spread_pip), the row is **DROPPED** as ineligible. It is
NOT labeled negative.

The dataset_summary.md must report `dropped_by_margin` count and
rate per pair.

### §4.4 Path traversal

Walk M1 bars `t+1, t+2, ..., t+H_M1_BARS` in chronological order.
For each bar `i ∈ [1, H_M1_BARS]`:

**For long direction**:
```
fav_excursion_i = bid_h[t+i] - entry_ask
adv_excursion_i = entry_ask - bid_l[t+i]
fav_hit_i = (fav_excursion_i >= fav_thresh)
adv_hit_i = (adv_excursion_i >= adv_thresh)
```

**For short direction**:
```
fav_excursion_i = entry_bid - ask_l[t+i]
adv_excursion_i = ask_h[t+i] - entry_bid
fav_hit_i = (fav_excursion_i >= fav_thresh)
adv_hit_i = (adv_excursion_i >= adv_thresh)
```

**Resolution at bar `i`** (priority order):
1. If `fav_hit_i AND adv_hit_i` (same-bar both-hit) → label = NEGATIVE; stop traversal. **SL-first invariant** (per kickoff §11.3 + PR #276 envelope §3.3).
2. Else if `adv_hit_i` → label = NEGATIVE; stop traversal.
3. Else if `fav_hit_i` → label = POSITIVE; stop traversal.
4. Else continue to bar `i+1`.

If the loop reaches `i = H_M1_BARS` without resolution → label =
NEGATIVE (no realised wave within horizon).

### §4.5 Cross-bar time ordering (clarification)

The same-bar SL-first invariant in §4.4 applies **only** when fav
and adv conditions both hit within the **same M1 bar**. Across
different bars, the **chronological order** wins:

- adv at bar `i`, fav at bar `i+1` → label = NEGATIVE (adv came first)
- fav at bar `i`, adv at bar `i+1` → label = POSITIVE (fav came first)

The §4.4 traversal naturally enforces this — once a non-ambiguous
trigger fires at bar `i`, traversal stops; later bars cannot
override.

## §5. Margin filter (§4.3 expanded)

### §5.1 Why drop, not label NEGATIVE

A signal where `1.5 × atr_pip < 2.0 × spread_pip` (equivalently
`atr_pip < 1.333 × spread_pip`) has a favourable threshold below
the cost floor. Labeling it NEGATIVE would conflate "no realised
wave" with "favourable threshold structurally below spread cost".
The latter is a property of the signal candidate (low volatility
relative to current spread), not a property of the realised path.

By **dropping** these rows, the labeled dataset answers the
question: *"given a signal where the favourable target is at least
2× spread, did the path realise the wave?"* — a cleaner downstream
target.

### §5.2 Reporting

The 25.0a-β `dataset_summary.md` MUST report:
- `dropped_by_margin_count` per pair
- `dropped_by_margin_rate` per pair (= `dropped / total_signal_candidates`)
- `dropped_by_margin_count` total
- `dropped_by_margin_rate` overall

If `dropped_by_margin_rate` > 80% on any pair, that pair's
distribution is flagged for the §12 pathological-balance review.

## §6. Same-bar resolution (§4.4 priority 1, expanded)

Same-bar both-hit: a single M1 bar `i` where both `bid_l[i] ≤
entry_ask − adv_thresh` AND `bid_h[i] ≥ entry_ask + fav_thresh`
(long; mirror for short).

**Resolution**: label = NEGATIVE. Justified by:
1. **Temporal ambiguity**: M1 OHLC does not record intra-bar tick
   ordering. We cannot know whether the touch order was fav-then-adv
   or adv-then-fav.
2. **Conservative inheritance**: PR #276 envelope §3.3 SL-first
   policy is the established research-execution-model standard
   across the NG#10 chain.
3. **Diagnostic transparency**: `same_bar_both_hit` is recorded as
   a boolean in the dataset; downstream readers can see exactly
   how many trades were resolved by this rule.

## §7. Direction shape (2 rows per signal_ts)

For every (pair, signal_ts) pair, 25.0a-β emits **TWO** rows:
- Row 1: `direction = long`, label computed under long fill
  semantics (entry_ask + thresholds against bid_h/bid_l).
- Row 2: `direction = short`, label computed under short fill
  semantics (entry_bid + thresholds against ask_l/ask_h).

This shape (2 rows per signal_ts, **NOT** single row with two label
columns) is mandated by kickoff §6.1 and:
- Permits row-level filtering by direction in downstream queries.
- Mirrors the parquet idiom used in 23.0a / 24.0a.
- Supports both directional and bidirectional candidate generation
  per kickoff §6.2.

## §8. ATR basis

`atr_at_signal_pip` is computed as a **causal M5 ATR**:

```
m5 = aggregate_m1_to_M5(m1)
m5_atr = m5["bid_c"].shift(1).rolling(ATR_N).apply(true_range)  # causal
atr_at_signal_pip[t] = m5_atr[t] / pip_size_for(pair)
```

`shift(1)` is essential — it ensures the M5 bar's own data is NOT
used in its own ATR (NG#11 causal invariant). Phase 23.0a's
`atr_at_entry_signal_tf` is the canonical implementation reference.

> **Higher-TF feature classes**: F2 (multi-TF vol regime) and F6
> (M30/H1/H4) may require ATRs at additional TFs. Those are the
> per-class PR's responsibility — 25.0a stores ONLY the M5 ATR
> used for label barriers. Mixing higher-TF ATRs into the label
> dataset itself would constitute label retuning post-design.

## §9. Causality contract (binding)

Mandatory invariants enforced by 25.0a-β tests:

1. **Labels at `t` use only future bars `[t+1, t+H_M1_BARS]`**. No
   bar at index `≤ t` may be used. No bar at index `> t+H_M1_BARS`
   may be used.
2. **`atr_at_signal_pip` at `t` uses only past bars (`shift(1)`
   pattern)**. The bar at `t` itself may NOT be used.
3. **`spread_at_signal_pip` at `t` uses bar `t`'s OHLC only**. (The
   spread at signal time is observable causally.)
4. **`entry_ask`, `entry_bid` at `t` are bar `t` close-of-bar
   values**. Standard entry-price convention.
5. **Same-bar SL-first** is enforced per §4.4 priority 1.
6. **Ineligible rows are dropped, not labeled**.

A 25.0a-β `causality_audit.md` doc must list each invariant and the
specific test that enforces it.

## §10. Diagnostic columns (NOT for downstream model features)

25.0a-β stores these diagnostic columns in `path_quality_dataset.parquet`:

| Column | Purpose |
|---|---|
| `max_fav_excursion_pip` | max favourable excursion observed within H bars (regardless of label resolution) |
| `max_adv_excursion_pip` | max adverse excursion observed within H bars |
| `time_to_fav_bar` | first bar index where fav threshold hit (-1 if never) |
| `time_to_adv_bar` | first bar index where adv threshold hit (-1 if never) |
| `same_bar_both_hit` | bool — was label resolved by §6 same-bar SL-first? |

> **PROHIBITION (binding)**: These five columns are **label-side
> diagnostic outputs**. Downstream feature-class evals (25.0b+) MUST
> NOT use them as model input features. Doing so constitutes
> **feature leakage** because they are computed from the same future
> bars as the label itself.
>
> Per-class PRs must include a unit test asserting that no
> diagnostic column from this list appears in the model's feature
> matrix.

## §11. Parquet schema

Output: `artifacts/stage25_0a/path_quality_dataset.parquet`
(gitignored).

| Column | Type | Note |
|---|---|---|
| `pair` | category(20) | one of canonical 20 pairs |
| `signal_ts` | timestamp[ns, UTC] | M5 bar boundary at signal time |
| `direction` | category(2) | `long` or `short` |
| `horizon_bars` | int8 | always 60 (single-horizon design) |
| `label` | int8 | 0 (negative) or 1 (positive) |
| `entry_ask` | float64 | for long entry; reference for short |
| `entry_bid` | float64 | for short entry; reference for long |
| `atr_at_signal_pip` | float32 | causal M5 ATR in pips |
| `spread_at_signal_pip` | float32 | bar `t` ask_c − bid_c in pips |
| `max_fav_excursion_pip` | float32 | DIAGNOSTIC (§10 prohibition) |
| `max_adv_excursion_pip` | float32 | DIAGNOSTIC (§10 prohibition) |
| `time_to_fav_bar` | int16 | DIAGNOSTIC (§10); -1 if never |
| `time_to_adv_bar` | int16 | DIAGNOSTIC (§10); -1 if never |
| `same_bar_both_hit` | bool | DIAGNOSTIC (§10) |

Storage rationale:
- ~80M rows × 2 directions = ~160M rows
- ~50 bytes/row uncompressed → ~8 GB; ~1-2 GB compressed
- Acceptable on local disk; gitignored.

## §12. Pathological label balance (halt-and-report)

If 25.0a-β observes any of:
- Overall positive rate < 5% or > 60%
- Per-pair positive rate < 2% on any pair
- `dropped_by_margin_rate` > 80% on any pair

— the implementation **MUST halt and report**. It must NOT retune
thresholds in-place. The user decides whether to:
- (a) accept the imbalance and proceed to 25.0b,
- (b) open a separate threshold-revision PR (NOT 25.0a-β edit),
- (c) reject Phase 25 entirely.

The `dataset_summary.md` must include a `pathological_balance_check`
section reporting these indicators with PASS / FAIL flags.

> Why halt-and-report rather than auto-retune: in-place retuning
> would invalidate the design-first contract. The point of 25.0a-α
> is to fix the design BEFORE seeing data. If the design produces
> a pathological dataset, that is itself a finding worth recording —
> not a problem to silently fix.

## §13. Test contract (≥ 13 tests)

25.0a-β `tests/unit/test_stage25_0a_path_quality_label.py` MUST
include at least these:

### §13.1 Algorithm correctness (4 tests)
1. `test_long_pure_favourable_path_labels_positive`
2. `test_long_pure_adverse_path_labels_negative`
3. `test_long_neither_threshold_hit_labels_negative` (horizon expiry)
4. `test_long_favourable_first_then_adverse_after_resolves_positive`

### §13.2 Same-bar SL-first invariant (2 tests; HARD)
5. `test_same_bar_both_hit_long_labels_negative_HARD`
6. `test_same_bar_both_hit_short_labels_negative_HARD`

### §13.3 Cross-bar ordering (1 test)
7. `test_adv_at_bar_i_then_fav_at_bar_i_plus_1_labels_negative`
   (chronological resolution per §4.5)

### §13.4 Symmetry (1 test)
8. `test_long_short_label_construction_is_symmetric`

### §13.5 Causality (2 tests)
9. `test_no_lookahead_uses_only_t_plus_1_through_t_plus_H`
10. `test_no_use_of_bars_at_or_before_signal_time_for_label`

### §13.6 Spread cost integration (2 tests)
11. `test_spread_cost_integrated_long_uses_entry_ask`
12. `test_spread_cost_integrated_short_uses_entry_bid`

### §13.7 Margin filter (1 test)
13. `test_low_volatility_signal_dropped_when_fav_threshold_below_margin`
    (verifies row is DROPPED, not labeled negative)

### §13.8 Horizon boundary (2 tests; per direction)
14. `test_favourable_hit_exactly_at_t_plus_H_counted_positive`
    (the H-th bar IS in scope)
15. `test_favourable_hit_at_t_plus_H_plus_1_not_counted_horizon_expired`
    (post-horizon must not influence)

**Minimum total: 15 tests** (kickoff direction §7 specified ≥ 13;
this contract over-delivers slightly with the 2 horizon-boundary
tests both included).

## §14. Runtime budget

- **Smoke run**: 3 pairs × 1 day, ~5-10 seconds, used for developer
  loop and CI smoke tests. Output is local-only; not committed.
- **Full run**: 20 pairs × 730 days, ~5-10 minutes wall time,
  produces the gitignored parquet + committed `dataset_summary.md`
  + committed `causality_audit.md` + committed `run.log`
  (gitignored).

25.0a-β commits:
- `causality_audit.md`
- `dataset_summary.md`

25.0a-β gitignores:
- `path_quality_dataset.parquet`
- `run.log`

## §15. Mandatory clauses (verbatim in 25.0a-β eval / docs)

These clauses must appear verbatim in `dataset_summary.md` and the
script's docstring:

### Clause 1 — Design constants are fixed

*The numerical thresholds K_FAV, K_ADV, M_MARGIN, H_M1_BARS were
fixed in 25.0a-α (`docs/design/phase25_0a_label_design.md`) before
implementation and MUST NOT be retuned in response to observed
label balance. If the dataset is pathological per §12, the
implementation halts and the user decides next steps.*

### Clause 2 — Causality

*Labels are computed from FUTURE bars `[t+1, t+H_M1_BARS]` only;
features and ATR are computed from PAST bars only. The boundary at
signal time `t` is hard. Same-bar SL-first invariant per PR #276
envelope §3.3.*

### Clause 3 — Diagnostic columns are not features

*The columns `max_fav_excursion_pip`, `max_adv_excursion_pip`,
`time_to_fav_bar`, `time_to_adv_bar`, `same_bar_both_hit` are
label-side diagnostic outputs computed from the same future bars
as the label. Downstream feature-class evals (25.0b+) MUST NOT use
them as model input features — doing so constitutes feature
leakage.*

### Clause 4 — γ closure preservation

*Phase 25.0a does not modify the γ closure declared in PR #279.
Phase 25 results, regardless of outcome, do not change Phase 24 /
NG#10 β-chain closure status.*

## §16. What 25.0a-α does NOT do

- Does not implement any code.
- Does not generate any dataset.
- Does not modify the kickoff (PR #280).
- Does not relax NG#10 / NG#11.
- Does not pre-approve threshold retuning.
- Does not pre-approve any production deployment.
- Does not update MEMORY.md.
- Does not modify Phases 22-24 docs / artifacts.

## §17. Routing to 25.0a-β

Once this 25.0a-α PR merges:
- 25.0a-β is the next PR, implementing the spec above.
- 25.0a-β must include the §13 test contract verbatim (no
  test-count reduction).
- 25.0a-β must commit `dataset_summary.md` and `causality_audit.md`
  with §11 outputs and §15 mandatory clauses.
- If 25.0a-β observes pathological balance per §12, it halts and
  reports — does not retune.
- After 25.0a-β merges, 25.0b feature-class selection awaits
  user direction.

## §18. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase25_0a_label_design.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x/23.x/24.x docs/artifacts:
unchanged. NG#10 / NG#11: not relaxed. γ closure (PR #279):
preserved.**

## §19. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 25.0a-α — design contract for path-quality label dataset locked. Implementation in 25.0a-β.**
