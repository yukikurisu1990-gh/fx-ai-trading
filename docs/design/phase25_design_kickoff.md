# Phase 25 Design Kickoff — Entry-Side Return via Different Feature Class

Doc-only kickoff PR for Phase 25, opened under Option C from PR #279
(γ hard close routing). Phase 25 is an entry-side return search **on
different feature classes**, explicitly NOT a Phase 23 redo. **No
code, no eval, no implementation in this PR.**

> **Mandatory framing** (binding for all Phase 25 PRs):
>
> *Phase 25 is not a hyperparameter-tuning phase. It is a
> label-and-feature-class redesign phase.*
>
> Novelty must come from (a) the input feature class and (b) the
> label design — NOT from a different ML model class on the same
> Phase 23 feature space, NOT from threshold sweeps on rejected rule
> classes, NOT from filter layering on Phase 22-24 NG'd routes.

## §1. Purpose and framing

Phases 22-24 closed the rule-based / classifier-based exit-side and
NG#10-relaxation routes. PR #279 declared γ hard close under current
data/execution assumptions and enumerated three pointers (Option B
audit / Option C path α / NG#11 review). The user has chosen
**Option C — path α**, with the explicit constraint that Phase 25
must NOT redo Phase 23.

This kickoff doc establishes the binding contract for Phase 25:
- §3 NG list (carries from 22-24 + 2 new entries).
- §4 admissible feature classes F1-F6 (no pre-ranking).
- §5 path-quality binary label semantic (with §11 minimum requirements).
- §6 direction handling.
- §7 validation discipline.
- §8 hypotheses H1 / H2 / H3.
- §9 stage architecture (25.0a mandatory + flexible expansion).
- §10 sweep size discipline.
- §11 mandatory clauses.

## §2. Scope

**In scope**:
- Doc-only contract that all subsequent Phase 25 PRs must obey.
- NG list, feature-class candidates, label semantic, validation
  discipline, hypothesis statements, stage architecture.

**Explicitly out of scope**:
- Implementation of any feature class (F1-F6).
- Generation of any label dataset.
- Writing any eval script.
- Pre-ranking F1-F6 — all six are admissible candidates equally.
- Modifying Phases 22 / 23 / 24 docs / artifacts.
- Relaxing NG#10 / NG#11.
- Pre-approving any production deployment.
- Updating MEMORY.md.

## §3. NG list (12 items)

Phase 25 inherits all NG items from Phases 22-24 verbatim and adds 2
new items derived from the γ closure:

### §3.A — Rule classes already REJECTed (no Phase 25 revival)
1. **M1 / M5 / M15 naive Donchian breakout** (Phase 22.0c, 23.0b, 23.0d).
2. **Rolling z-score mean-reversion** on close (Phase 23.0c, 23.0c-rev1).
3. **Signal-quality controls** as filters layered on Donchian / z-score (Phase 23.0c-rev1).

### §3.B — Exit-side mechanisms already REJECTed
4. **NG#10 strict close-only trailing-stop** variants (Phase 24.0b).
5. **Partial-exit policies** — atr / mfe / time-based partial triggers (Phase 24.0c).
6. **Regime-conditional exit policies** — ATR / session / trend regime variants (Phase 24.0d).
7. **NG#10 C2 both-side touch envelope** with SL-first same-bar policy (Phase 24.1a, PR #277).

### §3.C — Filter routes already REJECTed (Phase 22)
8. **Pair filter as primary edge** (e.g., JPY-only).
9. **Time-of-day / session filter as primary edge**.
10. **WeekOpen exclusion** as a primary edge.

### §3.D — Phase 25-specific NG items (new)
11. **LSTM / sequence model alone as primary edge**. ML model class is
    NOT an admissible feature class. Phase 25 admissibility requires
    the input feature class itself to be novel relative to §3.A — a
    new model class on Phase 23's input space is NOT Phase 25 work.
    LSTM may appear as a *modeling choice* on top of an admissible
    feature class but cannot be the source of edge.
12. **Calibration-only / probability-smoothing-only signal**. Probability
    calibration on a Phase 23-rejected rule class does NOT produce a
    Phase 25-admissible signal. Calibration may be a layer inside an
    admissible model but cannot be the binding source of edge.

These NG items remain prohibited in Phase 25. They may appear as
**secondary controls** (e.g., as covariates inside a model) but must
NOT be the binding source of edge.

## §4. Admissible feature classes (F1-F6; no pre-ranking)

The kickoff doc enumerates 6 candidate classes equally. **Order is
presentation order, not priority.** All six are admissible. The
implementation order is decided post-25.0a per §9.

### F1 — Volatility expansion / compression breakout

Operational input: realised vol over M5-M15-H1 windows; vol-of-vol;
expansion ratio (current vol / trailing baseline). Mechanism
hypothesis: markets transitioning from compression to expansion
produce trending bars more likely to clear path-quality.

### F2 — Multi-timeframe volatility regime

Operational input: M5 + M15 + H1 vol regime tags (low / med / high)
combined into a multi-axis regime vector. Mechanism hypothesis:
regime alignment across TFs (e.g., M15 expansion + H1 expansion)
produces stronger setups than single-TF regimes. Distinct from F1
in that F2 is a *regime tag* feature, F1 is a *continuous expansion*
feature.

### F3 — Cross-pair / relative currency strength + basket drift

Operational input: relative currency strength index computed within
the **20-pair canonical universe** (NOT a DXY proxy alone — that was
Phase 9.X-D and was REJECTed). Synthetic basket drift (directional
bias of one currency vs the rest of the universe). Mechanism
hypothesis: when a base currency is uniformly strong vs a basket of
others, single-pair entries in that direction may have higher
conditional realised EV.

> **F3 admissibility note**: F3 is admissible ONLY if the feature
> design materially differs from Phase 9.X-D's "DXY-from-synthetic-
> feed alone". Acceptable forms: relative strength matrix, basket
> drift detector, multi-currency directional alignment score.
> NOT acceptable: DXY proxy as a single covariate.

### F4 — Range compression then expansion

Operational input: Bollinger band squeeze + breakout pattern;
range-percentile feature on multi-TF. Mechanism hypothesis: the
classic "tight range, then break" setup — distinct from Donchian
(which only fires on band touch with no compression precondition).

> **F4 admissibility note**: F4 must require a **compression
> precondition** before the breakout. A pure breakout on band
> touch (no compression) is Phase 23 Donchian and prohibited.

### F5 — Liquidity-shock / spread-pattern proxy

Operational input: spread time series anomalies; M1 bar volume
relative to recent baseline; "thin book" indicator. Mechanism
hypothesis: liquidity shocks may produce realised EV asymmetrically
(e.g., post-shock mean reversion at predictable horizons).

### F6 — Higher-TF route (M30 / H1 / H4 entries)

Operational input: M30 / H1 / H4 OHLC features. Mechanism
hypothesis: higher TFs have different spread/ATR ratios and may
have different EV profiles than M5/M15.

> **F6 admissibility note (binding)**: F6 is admissible **ONLY** if
> combined with Phase 25's path-quality label design. **Naive
> Donchian / z-score rerun on higher bars is PROHIBITED** — that is
> a Phase 23 redo on a different bar size and is NG'd. F6's edge
> must come from path-quality label conditioning, not from the
> higher-TF rule itself. F6 was lightly explored in Phases 9 / 10
> (Stages 8.0 / 8.1 / 10.0a) but never under the post-bug-fix Phase
> 22-23 protocol; F6 is NOT a revival of those earlier results.

## §5. Path-quality label (binary)

Phase 25 abandons direction-prediction labels in favor of
**path-quality binary labels**: predict whether the next H bars
contain a realised path that **clears spread cost + sufficient EV
margin**, NOT whether the price goes up or down.

### §5.1 Label semantic

- **Positive**: future path has sufficient favourable excursion after
  cost, before unacceptable adverse excursion.
- **Negative**: otherwise.

Trinary / regression labels are **deferred**. They may be considered
in a future PR after binary label diagnostics are complete; this
kickoff fixes binary as the Phase 25 baseline.

### §5.2 Why binary

- Trinary adds a "neutral" class which is rarely actionable in
  trading and complicates calibration metrics.
- Regression to continuous path-EV is closer to 24.0a's
  `best_possible_pnl` and risks cross-talk with the `still_overtrading`
  mechanism that 24.0b/0c/0d/1a all hit.
- Binary aligns with the meta-labeling literature (López de Prado
  triple-barrier-style) and produces a natural P(positive) gate.

## §6. Direction handling

### §6.1 Label generation (25.0a, mandatory)

25.0a generates **BOTH long and short path-quality labels** for every
candidate signal time. Long-label positive ↔ "long entry at this time
would clear path-quality"; short-label positive ↔ "short entry at
this time would clear path-quality". Labels are symmetric in
construction (same H, same margin thresholds, mirrored long/short
fill semantics).

### §6.2 Per-class signal generation

Each feature-class PR (25.0b onward) may produce either:
- **Directional candidates**: features that directly imply a long-or-
  short bias (e.g., F3 currency strength favors long the strong
  currency); use the matching directional label.
- **Bidirectional candidates**: features that imply a setup but not
  direction (e.g., F1 vol expansion is direction-agnostic); use
  both long and short labels and let the model learn directional
  selection.

Either choice is admissible; **labels must remain symmetric and
predeclared**. The choice is fixed in each per-class design memo
before implementation.

## §7. Validation discipline (locked)

1. **Strict chronological OOS** — train / val / test splits by
   calendar date, not random sampling.
2. **Frozen-cell OOS** — any cell verdicting `PROMISING_BUT_NEEDS_OOS`
   or `ADOPT_CANDIDATE` mandates an X-v2-equivalent frozen-OOS PR
   before any production discussion. Phase 22 contract carried
   verbatim.
3. **20-pair canonical universe** — same as Phases 22-24. No subset
   filtering as primary edge.
4. **No pair / time / WeekOpen filter as primary edge** — these may
   appear as model covariates but must NOT be the binding source of
   lift.
5. **Phase 22 8-gate harness inherited verbatim** — Sharpe ≥ +0.082
   (A1), ann_pnl ≥ +180 pip/yr (A2), MaxDD ≤ 200 (A3), A4 ≥ 3/4
   folds positive, A5 +0.5 pip stress > 0.
6. **Multiple-testing caveat** — soft caveat + frozen-OOS approach
   (option (b) per direction):
   - A1 threshold remains **+0.082** for cross-phase comparability.
   - **PROMISING / ADOPT_CANDIDATE verdicts in any Phase 25 cell are
     hypothesis-generating only** — they do NOT confer
     production-readiness.
   - Mandatory X-v2-equivalent frozen-OOS PR before any production
     discussion.

## §8. Hypotheses (locked)

### H1 — Path-quality label is learnable

> At least one feature class achieves held-out **AUC ≥ 0.55** on the
> path-quality binary label, AND calibration is **directionally
> sensible** (predicted P(positive) is monotonically related to
> realised positive rate; reliability diagram does not invert).

If H1 fails for all 6 feature classes after their respective
sub-stages, the path-quality label is not informative under any
admissible Phase 25 input — Phase 25 closes negative.

### H2 — Learned path-quality selection realises into PnL

> At least one cell (feature-class × variant × threshold) clears
> **A1 (Sharpe ≥ +0.082) AND A2 (ann_pnl ≥ +180 pip/yr)** under the
> 8-gate harness.

H2 is the necessary-but-not-sufficient strategy gate. H2 PASS does
NOT confer production-readiness — H3 is still required.

### H3 — Frozen-OOS holds

> Any **PROMISING_BUT_NEEDS_OOS** or **ADOPT_CANDIDATE** cell from H2
> survives an X-v2-equivalent frozen-OOS PR (chronologically frozen
> held-out span; no re-tuning permitted; gate thresholds applied
> verbatim).

H3 is the production-readiness gate. Only H3 PASS opens production
discussion (Phase 22 contract).

## §9. Stage architecture (25.0a mandatory + flexible expansion)

| Stage | Status | Purpose | Output |
|---|---|---|---|
| **Phase 25 kickoff** (this PR) | doc-only | Binding contract: NG list, F1-F6, label spec, validation, hypotheses | this file |
| **25.0a — Path-quality label dataset** | mandatory next | Build path-quality dataset analogous to 23.0a outcome dataset; long+short labels per signal candidate | `artifacts/stage25_0a/path_quality_dataset.parquet` (gitignored), causality + spread audit, label-design memo with §11 numerical thresholds |
| **25.0b — first selected feature-class eval** | post-25.0a; user picks F-class | First feature-class evaluation under 25.0a labels | per-class eval_report |
| **25.0c onward** | open; opened by prior-stage result or user decision | Additional F-classes, refinements, or closure | TBD |
| **Phase 25 final synthesis** | TBD | Roll-up + verdict | path-α closure (positive or negative) |

**Critical**: 25.0a label generation **must precede** any feature-
class eval. A leakage / spread-cost bug at 25.0a would invalidate
everything downstream. **Phase 25 does NOT pre-commit to all 6
feature classes.** F1-F6 are admissible candidates; the
implementation order and which classes get evaluated is a user
decision after 25.0a, OR is opened by the result of a prior stage.

This is the **(c) intermediate** stage architecture per direction §5
— 25.0a + F1-F6 admissibility is fixed in this kickoff; per-class
order is flexible post-25.0a.

## §10. Sweep size discipline

Per feature-class PR should target **18-33 cells** (consistent with
Phase 24 cell count discipline; multiple-testing penalty bounded).

Any expansion beyond 33 cells **requires explicit multiple-testing
justification in the per-class design doc**. Justifications must
cover: (a) why the additional dimensions are necessary, (b) what
the corrected gate threshold becomes under the expansion, (c) why
the X-v2 frozen-OOS PR is still feasible at the larger cell count.

## §11. Path-quality label minimum requirements (kickoff-fixed)

A path-quality **positive** label requires ALL of:

1. **Favourable excursion after spread/cost**: future path produces
   a directionally favourable move that exceeds spread + slippage
   cost.
2. **Adverse excursion does not breach risk limit first**: the
   adverse-side excursion within the same horizon does NOT hit the
   adverse threshold before the favourable excursion clears.
3. **No same-bar ambiguity unless conservative SL-first resolution
   is applied**: if a same M1 bar contains both favourable and
   adverse excursions exceeding their respective thresholds, the
   bar resolves SL-first (consistent with PR #276 envelope). Such
   bars produce a NEGATIVE label.
4. **Minimum expected net move exceeds spread by fixed margin**:
   the threshold for the favourable excursion includes a margin
   above raw spread (specific numerical margin fixed in 25.0a
   before implementation).

**Exact numerical thresholds are fixed in 25.0a before
implementation**, not in this kickoff. The kickoff fixes the
*shape* of the label; 25.0a's design memo fixes the *numbers*.

This list is the binding minimum requirement set for the 25.0a
label design. The 25.0a memo may add additional invariants but
cannot relax any of §11.1-§11.4.

## §12. Mandatory clauses (verbatim in kickoff and inherited
downstream)

These four mandatory clauses are the binding invariants for all
Phase 25 PRs:

### Clause 1 — Mandatory framing

*Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
feature-class redesign phase. Novelty must come from (a) the input
feature class and (b) the label design — NOT from a different ML
model class on the same Phase 23 feature space, NOT from threshold
sweeps on rejected rule classes, NOT from filter layering on Phase
22-24 NG'd routes.*

### Clause 2 — NG list inheritance

*Phase 25 inherits all 12 NG items in §3 verbatim. NG'd routes may
appear as secondary covariates inside a model but must NOT be the
binding source of edge. Per-class design memos must justify why the
proposed feature class is NOT a re-encoding of any §3 NG'd route.*

### Clause 3 — Path-quality label causality

*Path-quality labels must be computed from FUTURE bars only;
features must be computed from PAST bars only; the boundary at
signal time `t` is hard. Strict NG#10 / NG#11 inheritance applies:
all M1 path triggers use close-only OR the PR #276 envelope
verbatim; all regime / volatility tags use shift(1) causal series.*

### Clause 4 — Production-readiness preservation

*PROMISING_BUT_NEEDS_OOS and ADOPT_CANDIDATE verdicts in Phase 25
are hypothesis-generating only. Production-readiness requires an
X-v2-equivalent frozen-OOS PR per Phase 22 contract. γ closure
status (PR #279) is not modified by Phase 25 — γ remains the
verdict for the closed Phase 22-24 + NG#10 β chain regardless of
Phase 25's outcome.*

## §13. What this kickoff PR does NOT do

- Does not implement any feature class.
- Does not generate any label dataset.
- Does not write any eval script.
- Does not pre-rank feature classes — F1-F6 are admissible equally.
- Does not modify Phases 22-24 docs / artifacts.
- Does not relax NG#10 / NG#11.
- Does not modify the γ closure (PR #279).
- Does not pre-approve any production deployment.
- Does not update MEMORY.md.

## §14. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase25_design_kickoff.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x / 23.x / 24.x docs / artifacts:
unchanged. NG#10 / NG#11: not relaxed. γ closure: preserved.**

## §15. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 25 kickoff — opens path α under the binding contract above. No implementation in this PR.**
