# §11B Audit Application — Phase 9.16 v9 20p baseline (Doc-Only)

**Status:** First concrete §11B application against the **current production
operational baseline**. Doc-only. **No experiment is run, no model is invoked,
no Sharpe / IC / MI is recomputed, no raw data is read, no quote feed / broker
is accessed, no artifact is produced, no production state is changed.**
**Scope key:** Roadmap §11B framework as merged by PR #376 at
`docs/design/root_logic_reassessment_profit_logic_audit_design.md`
(master `b30699c`). Applied here to **Phase 9.16 v9 20p** baseline.
**Date authored:** 2026-06-23.
**Branch:** `docs/11b-audit-v9-20p-baseline`.
**Base:** master `b30699c` (post PR #376 merge).

---

## 0. Binding constraints

This memo:

- runs the §11B framework against **existing committed memo evidence only**,
- does **not** recompute any numeric (no Sharpe, no IC, no MI, no oracle,
  no decile analysis, no calibration curve, no per-pair / per-regime
  decomposition),
- does **not** read raw data, candle files, JSONL, parquet, or replayed quotes,
- does **not** access broker / quote feed / credentials / env-vars,
- does **not** execute any model (no `torch` / `lightgbm` invocation),
- does **not** run any backtest, sweep, or replay,
- does **not** authorise P1 / P2 / P3 implementation,
- does **not** authorise Foundation T1 / T2 / T3 / T4 stages,
- does **not** authorise Research Track A / B / C / D / E / F / G execution,
- does **not** authorise any production change,
- does **not** modify any prior verdict memo,
- does **not** modify `MEMORY.md`,
- does **not** modify `.gitignore`,
- does **not** promote Phase 9.16 v9 20p above Tier 2,
- does **not** demote Phase 9.16 v9 20p below Tier 2,
- does **not** treat the Phase 28 §10 negative research baseline as an
  invalidation event for the production operational baseline.

The audit's purpose is **clarification of what the production baseline
proves, what it does not prove, and what future P1 / P2 / Foundation /
Research decisions still require** under §11B.

---

## 1. Scope / non-scope

### 1.1 Scope

- Structural application of the §11B audit dimensions (§2 objective mismatch,
  §3 label/target, §4 selection/ranking, §5 cost hurdle, §6 trade unit/horizon,
  §7 baseline/comparator, §8 oracle, §9 taxonomy, §10 kill/escalation,
  §11 relationship-to-future-work) **against Phase 9.16 v9 20p**.
- Citation of existing committed memo evidence (`phase9_16_closure_memo.md`,
  `phase9_15_closure_memo.md`, `phase9_10_closure_memo.md`, the
  `research_development_roadmap_post_audit.md` §3 status table and Appendix A,
  the Phase 27 / 29 tabular validity audit
  `phase27_29_tabular_eval_validity_audit.md`).

### 1.2 Non-scope

- No implementation. No code path is exercised.
- No data read. No `data/candles_*.jsonl` file is opened.
- No model execution. No `lightgbm` or `torch` invocation.
- No backtest / sweep / replay.
- No Sharpe / IC / MI / oracle / calibration recomputation.
- No production change.
- No prior verdict memo modification.
- No promotion or demotion of Phase 9.16 v9 20p.
- No invalidation of Phase 9.16 v9 20p based on Phase 28 §10 evidence.
- No use of "archived positive numerics" (e.g. +mtf 0.174, Top-K 0.165,
  C-3 0.177, +9.X-B 0.158) as routing evidence — those remain Tier 3 +
  `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING` per roadmap
  Appendix A.

---

## 2. Baseline identity

**Phase 9.16 v9 20p** is:

- the **production operational anchor** as of master `b30699c`,
- pinned in `research_development_roadmap_post_audit.md` §3 (line 625) as
  **Tier 2 (production default)** with `VALID_OPERATIONAL_BASELINE`,
- the merge of Phase 9.15's `spread` feature bundle (10-pair v9) extended
  to a 20-pair universe at Phase 9.16,
- distinct from `v10` (10-pair `spread+RH`, opt-in only, Phase 9.15)
  and from `v11` (20-pair `spread+CSI`, REJECTED at Phase 9.16/G-2.5).

### 2.1 Tier classification per roadmap

Roadmap `research_development_roadmap_post_audit.md` §3 places Phase 9.16
v9 20p at:

| Field | Value |
| --- | --- |
| Tier | 2 (`CONTEMPORANEOUS_CONTRACT_PASS` / `VALID_OPERATIONAL_BASELINE`) |
| Static-code | clean at the merge SHA |
| Run-provenance | partial or absent |
| Admissibility | suitable as **operational** baseline; **not** Tier-1 verified evidence |

### 2.2 Distinction from Phase 28 §10 negative research baseline

The Phase 28 §10 immutable research baseline reads test Sharpe **−0.1732** /
val Sharpe **−0.1863** / ann_pnl **−204,664.4** (per
`phase27_closure_memo.md:34`). The §11B audit (roadmap §11B / §7.2) names
this `BASELINE_NEGATIVE_OR_WEAK` and binds: **beating Phase 28 §10 is not
sufficient** to promote a candidate.

This audit explicitly states:

- The Phase 28 §10 negative research baseline is a **research-axis**
  artefact bound to that audit's run contract and dataset epoch.
- It does **not** invalidate the **production operational** Phase 9.16
  v9 20p baseline.
- The two baselines live on different axes:
  - Phase 28 §10: a research evaluation contract on a specific candidate
    set, conditional on run-provenance discipline introduced after Phase 27
    audit U-1 / U-2.
  - Phase 9.16 v9 20p: contemporaneous-contract pass at its merge SHA,
    operational since adoption, **not** invalidated by an unrelated
    research-axis evaluation contract.

This separation is roadmap-binding (§3 line 145–146, §3 line 168–169) and
is preserved verbatim by this audit memo. **No promotion of v9 20p to
Tier 1 is performed. No demotion is performed.**

### 2.3 Baseline status preserved by this PR

After this audit memo merges:

- **Phase 9.16 v9 20p remains Tier 2 `VALID_OPERATIONAL_BASELINE`.**
- **No change** to its admissibility class.
- **No change** to its operational role.
- **No change** to whether it is "verified" — it is **not** Tier 1, and
  remains not Tier 1.

---

## 3. Audit dimension 1 — Objective mismatch audit

### 3.1 Known from existing committed memos

- **Train objective.** Per `phase9_15_closure_memo.md` and
  `phase9_16_closure_memo.md` §3 / §5, the model class through Phase 9.13 →
  9.16 is LightGBM with `predict_proba` outputs.
- **Selector.** `phase9_16_closure_memo.md` §4 names argmax-by-confidence
  per bar as the SELECTOR mechanism, with `confidence threshold = 0.50`.
- **Headline metric reported at closure.** SELECTOR Sharpe 0.160 (20-pair
  v9 vs 10-pair v9 0.152) per `phase9_16_closure_memo.md:36–40`.
- **PnL reported at closure.** PnL 8,157 pip (20-pair v9), +20.1% vs v5
  baseline 6,793 pip per `phase9_16_closure_memo.md:42`.
- **MaxDD / DD%PnL reported at closure.** MaxDD 203 pip, DD%PnL 2.5%.
- **Trade count reported at closure.** 12,461 trades (20-pair v9) vs
  11,958 (10-pair v9).
- **WinFold% reported at closure.** 90% (20-pair v9) vs 82% (10-pair v9).
- **Per-trade EV.** Not directly tabulated in the closure memo; can be
  inferred as `PnL / trades = 8,157 / 12,461 ≈ 0.65 pip/trade`
  **(inference from committed numerics; not a fresh computation)**.

### 3.2 Known unknowns (not recomputed in this PR)

- **Net vs gross at production cost.** Phase 9.10 documented that the
  same selector class loses ~0.42 Sharpe per 1 pip round-trip cost
  (`phase9_10_closure_memo.md:68`). The published 0.160 Sharpe at Phase
  9.16 is the **internal-sweep selector** evaluated under its merge-time
  cost convention; whether it survives a **separately observed live
  spread** (P2) is **not** answered by the closure evidence.
- **Run-provenance for the 0.160 / +20.1% numerics.** Roadmap §3 line
  407 places Phase 9.16 in Tier 2 because run-provenance is **partial or
  absent**. The Phase 27 audit (`phase27_29_tabular_eval_validity_audit.md`
  U-1 / U-2) flagged contemporaneous-tabular evaluation memos for absent
  sweep-results / sanity-probe artefacts. Phase 9.16's numerics share
  that risk class.
- **Selected-trade EV vs unselected EV.** Whether the +0.65 pip/trade
  inferred margin is monotonic in score, and whether it is stable across
  pairs / sessions / regimes, is not directly tabulated in the committed
  memo (§4.3 noted "internal-sweep code path doesn't surface the per-pair
  frequency table").

### 3.3 Verdict for dimension 1

**No live objective mismatch is shown by existing evidence**, but the
**linkage** between (train objective → selector → headline metric → net PnL
→ per-trade EV) is **partially documented**. Headline metric (Sharpe 0.160)
and PnL (+20.1%) are co-positive at the merge-time cost convention; per-trade
EV is inferable but not validated against live cost. The roadmap §11B
"objective-to-PnL linkage" reporting requirement is **partially satisfied at
the closure-memo level, fully satisfied only after P2 supplies the live cost
context**.

Status: **PARTIAL_LINKAGE_DOCUMENTED — LIVE_COST_NOT_OBSERVED**.

---

## 4. Audit dimension 2 — Label / target logic audit

### 4.1 Known from existing committed memos

- **Label class.** The bid/ask labels (introduced by Phase 9.12 B-2 cell)
  remain the labelling convention through Phase 9.13–9.16, per
  `phase9_16_closure_memo.md:122–127` cumulative path table. The labels
  reflect **triple-barrier outcomes evaluated against bid/ask price
  series**, replacing the earlier mid-based labels of Phase 9.10–9.11.
- **TP / SL geometry.** Phase 9.10 design memo and closure memo
  (`phase9_10_closure_memo.md:144`) used `TP=3pip / SL=2pip / horizon=20`.
  Phase 9.13's C-3 kill-switches and Phase 9.15 / 9.16's feature changes
  did **not** revise the TP/SL geometry; the production baseline inherits
  the same 3/2 ratio.
- **Cost hurdle inside the label.** The bid/ask label convention bakes a
  realistic-fill assumption into the **label**, but the **selector** is
  threshold-only (`conf ≥ 0.50`) — there is no explicit cost-hurdle gate
  at the selector layer.
- **Class balance.** Not directly tabulated in the closure memo; can be
  inferred from signal rate 99.9% at Phase 9.10 (every-bar selection),
  reduced through Phase 9.12 / 9.13 by the `conf ≥ 0.50` threshold.

### 4.2 Unresolved questions (deferred to T3 / T4 / Track E)

- **Direction vs trade/no-trade vs return-magnitude vs exit-aware profit**
  comparison: Phase 9.18 (asymmetric TP/SL) explored a related axis and
  closed NO ADOPT (roadmap §3); Track E (A2-broad target redesign) is
  named in the roadmap as the surface to revisit this question.
- **Cost hurdle inside the label vs selector vs post-filter.** Currently
  inside the label (bid/ask). Whether a **dynamic** per-(pair, session)
  hurdle at the selector or post-filter level would improve net PnL is a
  P1 question — strictly downstream of P2 observation per
  `p2_live_spread_snapshotting_design.md` §6.4.
- **False-positive cost under per-bar selection.** Trade count rose from
  11,958 → 12,461 with the universe expansion (+503 trades). Whether
  those marginal trades are positive-EV is not directly tabulated.

### 4.3 Verdict for dimension 4 (label / target)

**Labels are bid/ask aware (mid → BA upgrade landed at Phase 9.12),
cost-hurdle placement is at the label layer, dynamic-hurdle exploration is
deferred to P2 / P1.** Production label convention is documented and stable
since Phase 9.12.

Status: **LABEL_CONVENTION_DOCUMENTED — DYNAMIC_HURDLE_EXPLORATION_DEFERRED**.

---

## 5. Audit dimension 3 — Selection / ranking logic audit

### 5.1 Known from existing committed memos

- **Selector.** Argmax of LightGBM `predict_proba` across the pair universe,
  per bar, gated by `conf ≥ 0.50`.
- **Confidence threshold sensitivity.** Phase 9.10 A-6 grid
  (`phase9_10_closure_memo.md:114`) found that sweeping conf from 0.50 →
  0.65 moves Sharpe by ~0.01 at any spread row. "Conf-only filtering
  cannot rescue this strategy" (citation).
- **Pair concentration.** Phase 9.10 A-5 at 1 pip baseline: USD/JPY 27%,
  EUR/JPY 21%, GBP/JPY 15% (JPY total 64%); Phase 9.16 closure §4 reports
  USD/JPY 29%, EUR/USD 21%, AUD/USD 15% (~65% combined) under the v9 20p
  universe. Phase 9.10 closure §3 note 3 names this a **structural property
  of the EV-based picker plus the volatility/trend characteristics of JPY
  crosses**, not a cost-modelling artifact.

### 5.2 What existing evidence does **not** support

- **Rank monotonicity by decile.** Not directly evidenced in the committed
  memos.
- **Top-K rank EV curve.** Not directly evidenced for v9 20p. Phase 9.19
  closure (`phase9_19_closure_memo.md`) reports Top-K K=2 results, but
  Phase 9.19 closure is **Class U on run-provenance** and Top-K K=2's
  archived nominal Sharpe 0.165 carries `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`
  per roadmap Appendix A. **It cannot be used to promote a selector here.**
- **Calibration of `predict_proba`.** Not directly evidenced for v9 20p.
- **Score distribution stability across train / val / test folds.** Not
  directly evidenced.
- **Cost-adjusted selected-trade PnL by rank.** Not directly evidenced.

### 5.3 Roadmap §11B promotion gate against this dimension

§11B §4.2 binding (verbatim from `root_logic_reassessment_profit_logic_audit_design.md`):

> No selection mechanism (selector / ranker / Top-K rule / threshold filter)
> may be promoted to a production candidate unless rank monotonicity passes
> ... **and** selected-trade EV survives cost-adjusted validation against a
> baseline that itself is not negative.

Applied here:

- v9 20p's **existing** selector (argmax with `conf ≥ 0.50`) is the
  current production operational anchor — it is not a new "candidate
  for promotion". Its operational status precedes §11B.
- A **new** selector that aims to replace v9 20p's argmax must satisfy
  §11B §4.2 — including rank monotonicity, cost-adjusted EV, baseline
  comparator. **No such selector is proposed by this PR.**
- Phase 9.19 Top-K (K=2 archived Sharpe 0.165) is **not** admissible as
  promotion evidence — it is Tier 3 + `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`.

### 5.4 Verdict for dimension 5 (selection / ranking)

Status: **PRODUCTION_SELECTOR_OPERATIONAL — RANK_MONOTONICITY_NOT_EVIDENCED —
NO_PROMOTION_CANDIDATE_PROPOSED**.

---

## 6. Audit dimension 4 — Cost hurdle / execution realism audit

### 6.1 Cost-sensitivity evidence from Phase 9.10

`phase9_10_closure_memo.md:88–96` documents SELECTOR net Sharpe by spread
row (1-pip steps, 4 conf columns; at the **Phase 9.10 v3 selector**, **not**
v9 20p):

```
spread \ conf   0.50      0.55      0.60      0.65
0.00            +0.346    +0.347    +0.350    +0.356  (= v2 reproducer)
0.50            +0.135    +0.136    +0.140    +0.146
1.00            -0.076    -0.075    -0.071    -0.065
1.50            -0.286    -0.285    -0.281    -0.275
2.00            -0.497    -0.496    -0.492    -0.485
```

(`phase9_10_closure_memo.md` §3.2)

**Two facts directly entailed for the §11B audit of v9 20p:**

1. **Cost sensitivity is approximately linear** at this selector class:
   "Each 0.5 pip of spread costs ~0.21 net Sharpe" (citation
   `phase9_10_closure_memo.md:114`).
2. **At 1 pip spread the Phase 9.10 selector is `NO_GO`** with net Sharpe
   −0.076. The Phase 9.10–9.16 sequence transitioned to bid/ask labels
   (Phase 9.12 / v5), `spread` features (Phase 9.15 / v9), and the 20-pair
   universe (Phase 9.16) **specifically to recover net positivity**.

### 6.2 What this implies for v9 20p

- The published Phase 9.16 Sharpe 0.160 is reported at the merge-time
  cost convention pinned to the bid/ask-aware label and the internal-sweep
  selector. It is **not** evidenced against a **separately observed live
  bid/ask spread distribution** — that is the function of P2.
- Whether v9 20p's edge is **larger than** the live observed spread on
  each (pair, session) cell is **not** answered by committed evidence.
- The **per-pair** cost sensitivity from Phase 9.10 §3.1 (JPY 64% pair
  selection, EUR/USD 9.7% etc.) plus the v9 20p §4 distribution
  (USD/JPY 29%, EUR/USD 21%, AUD/USD 15%) indicates that the **bulk of
  v9 20p's trades fire on pairs whose live spread distribution is not yet
  observed under P2**.

### 6.3 Ties to P2 / P1 / P3

Per `p2_live_spread_snapshotting_design.md` §6 and §10:

- **P2 supplies the observational baseline** for live bid/ask spread by
  (pair, session, weekday).
- **P1 is the cost-model replacement** that, **only after P2 produces an
  admissible profile (≥1 full UTC week including weekend, all four
  session buckets, per-(pair, session_bucket) cell n ≥ pinned threshold),
  may** revise the cost convention used by the selector or post-filter.
- **P3 (cost-aware sizing)** is downstream of P1.

§11B §4 binding: if the cost-hurdle audit (this dimension) ever shows
`COST_ERASED_EDGE` (§9), the candidate must not be escalated regardless
of gross Sharpe.

### 6.4 Verdict for dimension 6 (cost hurdle / execution realism)

Status: **MERGE_TIME_COST_CONVENTION_DOCUMENTED — LIVE_COST_OBSERVATION_PENDING_P2 —
PER_PAIR_PER_SESSION_HURDLE_NOT_YET_EVIDENCED — P1_NOT_AUTHORISED**.

The §11B `COST_ERASED_EDGE` label is **not** assigned to v9 20p at this
time — the evidence to assign or refute it does not yet exist, and P2
is the only authorised path to obtain that evidence. **No P1 / P3
authorisation is implied by this audit.**

---

## 7. Audit dimension 5 — Trade unit / horizon audit

### 7.1 Known from existing committed memos

- **Timeframe.** M1 candles (`phase9_10_closure_memo.md` §2 names
  `--price BA` fetch of M1 candles; Phase 9.16 closure inherits the same).
- **Triple-barrier horizon.** 20 bars (`phase9_10_closure_memo.md:71`).
- **TP / SL.** Fixed `TP=3pip / SL=2pip` (Phase 9.10 baseline; Phase
  9.18's asymmetric TP/SL closed NO ADOPT and was not adopted by v9 20p
  per roadmap §3 row 9.18).
- **Feature horizon.** Mixed — `xp_*` cross-pair features look across
  the universe at the same bar (`phase9_16_closure_memo.md:84–87`),
  `spread` features (added Phase 9.15) use single-pair history; specific
  history depths are not tabulated in the closure memos.

### 7.2 Known unknowns

- **Distribution of realised holding period vs the 20-bar horizon.**
  Not tabulated.
- **Fraction of trades closed by TP vs SL vs horizon timeout.** Not
  tabulated.
- **Path-aware outcome vs end-of-window prediction mismatch.** Not
  diagnosed.
- **Whether `xp_*` cross-pair features carry implicit leakage at the
  triple-barrier resolution.** Not diagnosed.

### 7.3 Verdict for dimension 7 (trade unit / horizon)

Status: **CADENCE_AND_GEOMETRY_DOCUMENTED — REALISED_HORIZON_DISTRIBUTION_NOT_DIAGNOSED**.

This is a known incompleteness, not a falsification. The §11B framework
requires future tracks to **report** the (feature horizon, label horizon,
holding period, TP/SL geometry) tuple in design and closure memos; this
audit notes that for v9 20p the tuple is **(mixed feature horizon, 20-bar
label horizon, distribution-unknown holding period, fixed 3/2 TP/SL)**.

---

## 8. Audit dimension 6 — Baseline and comparator audit

### 8.1 Cash / no-trade baseline

- Existing committed evidence: **none directly tabulated as a "cash
  baseline" row** in the Phase 9.10–9.16 closure memos. Phase 9.16
  §3.1 compares 20-pair v9 vs 10-pair v9 vs v5, not vs cash.
- Status: **EVIDENCE_ABSENT** for cash baseline. (Per §11B §6.1, cash
  baseline is "always available" as a conceptual floor — but no
  committed numeric row exists.)

### 8.2 Phase 9.16 v9 20p — operational baseline only

- Per roadmap §3 line 625: Tier 2 `VALID_OPERATIONAL_BASELINE`.
- Suitable **as** the operational baseline.
- **Not** Tier 1, **not** "verified".
- **Not** the same axis as Phase 28 §10 negative research baseline.

### 8.3 New-epoch S-B / S-E

- Per roadmap §3 / §5 Foundation T4, the new-epoch S-B / S-E sentinel
  comparators are **not constructed yet**. Until Foundation T3 + T4
  produce them, they carry `NOT_AVAILABLE_FOR_ROUTING`.
- This audit confirms: **no S-B / S-E comparison is performed here**,
  because the comparators do not exist.

### 8.4 Cost-adjusted hurdle baseline

- A cost-adjusted hurdle baseline requires P2 observational output.
- Per `p2_live_spread_snapshotting_design.md`, P2 has been **designed**
  (PR #376) but not **implemented**.
- This baseline is therefore **EVIDENCE_ABSENT** today.

### 8.5 Binding — beating a negative research baseline is insufficient

Re-stated from `root_logic_reassessment_profit_logic_audit_design.md` §7.2.
This audit confirms it operationally:

- Phase 9.16 v9 20p is **not** considered "validated" because it
  out-performs Phase 28 §10's negative baseline.
- Phase 9.16 v9 20p's status as Tier 2 `VALID_OPERATIONAL_BASELINE`
  is **independent** of the Phase 28 §10 evaluation, on a different
  axis, and rests on its **contemporaneous-contract pass at merge SHA**.
- Any future candidate that aims to **replace** v9 20p must beat:
  - cost-adjusted hurdle baseline (once P2 produces it),
  - new-epoch S-B / S-E (once T3 + T4 produce them),
  - rank monotonicity gate (§5),
  - per-trade EV gate (§4.2 of §11B framework),
  - **and** v9 20p itself at the operational layer
    — **not** Phase 28 §10.

### 8.6 Verdict for dimension 8 (baseline / comparator)

Status: **OPERATIONAL_BASELINE_PRESERVED — RESEARCH_BASELINES_ABSENT_AWAITING_FOUNDATION_T3_T4 —
NEGATIVE_BASELINE_INSUFFICIENCY_BINDING_REASSERTED**.

---

## 9. Audit dimension 7 — Alpha upper-bound / oracle diagnostics

The §11B framework (§8 of `root_logic_reassessment_profit_logic_audit_design.md`)
lists nine oracle / diagnostic surfaces. Each is **NOT_COMPUTED_IN_THIS_PR**:

| Diagnostic | Status here |
| --- | --- |
| Cost-free oracle | `NOT_COMPUTED_IN_THIS_PR` |
| Cost-adjusted oracle | `NOT_COMPUTED_IN_THIS_PR` |
| Per-pair oracle | `NOT_COMPUTED_IN_THIS_PR` |
| Per-regime oracle | `NOT_COMPUTED_IN_THIS_PR` |
| Perfect-rank oracle | `NOT_COMPUTED_IN_THIS_PR` |
| Label separability | `NOT_COMPUTED_IN_THIS_PR` |
| IC / MI | `NOT_COMPUTED_IN_THIS_PR` |
| Score-to-PnL monotonicity (per decile) | `NOT_COMPUTED_IN_THIS_PR` |
| Per-pair / per-regime decomposition (formal) | `NOT_COMPUTED_IN_THIS_PR` |

Each of these would require **model invocation, raw data access, and
artifact generation** — all disallowed by this PR's constraints. The
roadmap pins these as **separate authorisation surfaces**.

The Phase 9.10 §3.2 grid (§6.1 above) is **not** an oracle diagnostic in
the §11B sense — it is a sweep over a fixed selector class with fixed
labels at a synthetic spread axis. It informs the cost-hurdle dimension
(§6) but does not stand in for a cost-free / cost-adjusted oracle.

Status: **ALL_ORACLE_DIAGNOSTICS_DEFERRED**.

---

## 10. Audit dimension 9 — Root-cause taxonomy application

Applying the §11B 13-label taxonomy conservatively against Phase 9.16
v9 20p. Labels are assigned **only** where existing committed evidence
positively supports them; otherwise `EVIDENCE_ABSENT` / `NOT_DETERMINED`
is used.

| Label | Verdict against v9 20p | Basis |
| --- | --- | --- |
| `NO_SIGNAL` | **Not applicable.** | Trade count, WinFold%, +20.1% PnL vs v5 indicate a non-zero edge at the merge-time cost convention. (`phase9_16_closure_memo.md:42`) |
| `SIGNAL_NON_MONETISABLE` | `EVIDENCE_ABSENT` at live cost. | Net positivity is shown at the internal-sweep cost convention; live-cost net positivity is `P2_OBSERVATION_PENDING`. |
| `COST_ERASED_EDGE` | `EVIDENCE_ABSENT`. | Phase 9.10 documents cost sensitivity but v9 20p has a different selector / labels / universe. No live-cost erasure is shown today. |
| `RANKING_INVERSION` | `EVIDENCE_ABSENT` for v9 20p. | Phase 9.19 documented rank-3 inversion under Top-K — that is **not** the v9 20p selector. v9 20p's rank monotonicity is **not evidenced** today (§5). |
| `TRADE_RATE_EXPLOSION` | **Not present.** | Phase 9.16: 11,958 → 12,461 trades (+4%). Bounded by argmax per bar; not the 15× explosion pattern of Phase 9.17. |
| `PER_TRADE_EV_COLLAPSE` | **Not present.** | Per-trade EV inferable ≈ 0.65 pip/trade is positive at the merge-time convention; live-cost value is pending P2. |
| `REGIME_INSTABILITY` | `EVIDENCE_ABSENT`. | Per-regime decomposition not tabulated in committed memos. |
| `PAIR_CONCENTRATION` | **Partial — documented but not falsifying.** | Top-3 pairs ≈ 65% (USD/JPY 29% + EUR/USD 21% + AUD/USD 15%) per `phase9_16_closure_memo.md:73`. Phase 9.10 closure §note 4 calls this **a structural property of the EV picker plus JPY-cross volatility**, **not** a defect. Recorded for future P1 / Track A audits but **does not** falsify v9 20p. |
| `LEAKAGE_OR_CAUSALITY_FAILURE` | `EVIDENCE_ABSENT`. | The v9 20p path does **not** carry the v18 lookahead defect documented for Phase 9.X-B (that was an independent fix branch). No `xp_*` causality probe is committed for v9 20p; not falsified, not verified. |
| `CLASS_U_RUN_PROVENANCE` | **Tier 2 binding applies.** | Roadmap §3 line 407 pins v9 20p in Tier 2 because run-provenance is partial or absent. **This is the binding constraint that prevents promotion to Tier 1**; it is also the reason §11B routing against new candidates cannot use v9 20p's numerics as a Tier-1 reference. |
| `BASELINE_NEGATIVE_OR_WEAK` | **Not v9 20p.** | The negative baseline is Phase 28 §10 (research-axis). v9 20p's relation to it is **independence**, not subsumption. |
| `OVERFITTED_SELECTOR` | `EVIDENCE_ABSENT`. | OOS rank stability not tabulated; no fold-level OOS diagnostic committed for v9 20p. |
| `EXECUTION_CONSTRAINT_FAILURE` | `EVIDENCE_ABSENT` (TP/SL geometry stable; partial-exit explored at 9.18 and NOT ADOPTED). | Whether the 3/2 TP/SL geometry erases edge at live cost is a P1 question downstream of P2. |

**No falsifying label is positively assigned to Phase 9.16 v9 20p by this
audit.** Two structural facts are documented:

- `PAIR_CONCENTRATION` is **observed** but classified as **structural,
  not defective** under existing committed analysis.
- `CLASS_U_RUN_PROVENANCE` is the **binding** that pins v9 20p at Tier 2
  rather than Tier 1 — this is a known constraint, not a fresh finding.

---

## 11. Kill / escalation criteria implications

### 11.1 What cannot be escalated **from this audit alone**

Per the §11B framework (§10 of the audit design):

- **No promotion of v9 20p to Tier 1.** Tier 1 requires `FORMALLY_VERIFIED`
  status — full run-provenance, sweep-results and sanity-probe artefacts,
  static-clean at merge SHA. v9 20p is class U on run-provenance.
- **No declaration that v9 20p has survived a §11B audit.** This memo is
  a **structural application of the framework against existing committed
  evidence**; it documents what is and is not evidenced. It does not
  produce new diagnostic numerics.
- **No use of v9 20p's archived numerics (0.160 / +20.1%) as Tier-1
  comparator for a new candidate.** Per the roadmap's controlled vocabulary,
  v9 20p numerics are `VALID_OPERATIONAL_BASELINE`-class — admissible **as
  operational reference**, not as Tier-1 verification ground truth.

### 11.2 What is **not** authorised by this audit

- **No Track A execution** (A.1 +mtf / A.2 Top-K / A.3 C-3 from-scratch
  re-evaluation under new-epoch contract).
- **No Track B execution** (Phase 9.X-C residual LSTM B-1/B-2/B-3/B-4).
- **No Track C execution** (A0-broad sequence-NN formal verification via
  PR #354 allowlist S1 / S2 / S3).
- **No Track D execution** (data-side expansion affecting cost / horizon).
- **No Track E execution** (A2-broad target redesign).
- **No Track F execution** (MoE / model-class change).
- **No Track G execution** (ensemble re-formulation).
- **No P1 execution** (cost-model replacement).
- **No P2 implementation** (the implementation PR chain seeded by
  `p2_live_spread_snapshotting_design.md` is not opened by this PR).
- **No P3 execution** (cost-aware sizing).
- **No Foundation T1 / T2 / T3 / T4 stage authorisation.**
- **No production change.**

### 11.3 What the audit **does** clarify

- The §11B "promotion gate" cannot be applied retroactively to v9 20p —
  v9 20p is the **incumbent operational baseline**, not a promotion
  candidate. Future selectors aiming to replace v9 20p must clear §11B
  against the comparator set in §8.5 above.
- The §11B `COST_ERASED_EDGE` and `OVERFITTED_SELECTOR` labels are
  **not assigned** to v9 20p today, but they are **not refuted** either —
  the evidence to falsify or confirm them lives in P2 + future oracle
  diagnostics.
- The §11B `BASELINE_NEGATIVE_OR_WEAK` label belongs to Phase 28 §10
  research baseline, **not** to v9 20p, and the two baselines do not
  subsume each other.

---

## 12. Final controlled verdict

Applying the controlled-vocabulary verdict labels named in the audit
prompt:

| Verdict label | Assigned |
| --- | --- |
| `BASELINE_STATUS_PRESERVED_AS_TIER2_OPERATIONAL_ANCHOR` | **YES** |
| `NOT_TIER1_VERIFIED` | **YES** |
| `INSUFFICIENT_FOR_NEW_ROUTING_DECISION` | **YES** |
| `REQUIRES_FOUNDATION_T3_T4_FOR_FORMAL_VERIFICATION` | **YES** |
| `P2_AND_P1_COST_REALISM_REMAINS_SEPARATELY_GATED` | **YES** |

### 12.1 Plain-language final reading

- **Phase 9.16 v9 20p remains the production operational baseline at
  Tier 2 (`CONTEMPORANEOUS_CONTRACT_PASS` / `VALID_OPERATIONAL_BASELINE`).**
  This audit **preserves** that status. It is **not promoted** and **not
  demoted**.
- **It is not Tier 1.** Class U on run-provenance is the binding
  constraint, not a fresh finding.
- **It is not invalidated by Phase 28 §10.** The two baselines live on
  different axes (operational vs research).
- **Archived positive numerics from neighbouring phases (+mtf 0.174,
  Top-K 0.165, C-3 0.177, +9.X-B 0.158) are not used as routing evidence
  by this audit** — they remain Tier 3 +
  `ARCHIVED_UNTRUSTED_NUMERIC_DO_NOT_USE_FOR_ROUTING`.
- **No falsifying §11B taxonomy label is positively assigned to v9 20p.**
  `PAIR_CONCENTRATION` is **observed but structural**;
  `CLASS_U_RUN_PROVENANCE` is the **known Tier-2 binding**.
- **P2 live spread observation, P1 cost-model replacement, P3
  cost-aware sizing, Foundation T1–T4, and Research Tracks A/B/C/D/E/F/G
  all remain separately gated.** None is authorised by this audit.
- **The next concrete step that would change Phase 9.16 v9 20p's
  evidentiary status is Foundation T3 + T4** (new-epoch S-B / S-E
  baseline + control construction), which is **separately authorised**
  and not opened by this PR.

---

## 13. Status carry-forward

- **Phase 9.16 v9 20p:** Tier 2 (`CONTEMPORANEOUS_CONTRACT_PASS` /
  `VALID_OPERATIONAL_BASELINE`), preserved.
- **Phase 9.10 / 9.12 / 9.13 / 9.15 / 9.16 / 9.17 / 9.17b / 9.18 / 9.19 /
  9.X-A / 9.X-B / 9.X-C M-1 / 9.X-D / 9.X-J / 9.X-L / 9.X-M / 9.X-N / 9.X-O
  verdicts:** unchanged.
- **Phase 27 / 28 / 29.0a verdicts:** unchanged.
- **A0-broad β halt:** unchanged.
- **A0-narrow / A2-narrow FALSIFIED bindings:** unchanged.
- **Foundation T0 / T1 / T2 / T3 / T4:** unchanged.
- **Research Tracks A / B / C / D / E / F / G:** unchanged.
- **P1 / P2 / P3:** unchanged.
- **§11B framework status:** still `DESIGNED_NOT_OPERATIONALISED_ON_CANDIDATES`
  at the broad framework level; this PR provides the **first concrete
  application against an existing baseline** but does not operationalise
  it against any **new** candidate.
- **Routing authority granted by this PR:** none.

End of audit.
