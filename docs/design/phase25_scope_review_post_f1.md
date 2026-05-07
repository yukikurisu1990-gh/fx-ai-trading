# Phase 25 Scope Review — Post-F1 Mid-Stage Synthesis

Doc-only PR that records the F1 (volatility expansion / compression)
finding from PR #284 and updates the Phase 25 routing decision tree
with the new empirical evidence. **No code, no eval, no
implementation.** Single new file.

This is a **mid-stage synthesis**, NOT a closure declaration. Only
one of the six admissible F-classes (F1) has been evaluated; closing
Phase 25 here would be premature. This doc lays out the next-step
options strictly neutrally and hands the routing decision to the
user.

## §1. Purpose and framing

Phase 25 kickoff (PR #280) opened path α from PR #279 with six
admissible feature classes (F1-F6) and a binary path-quality label
dataset (PR #281 → PR #282). 25.0b-α (PR #283) locked the F1
volatility-expansion design contract; 25.0b-β (PR #284) implemented
and evaluated 24 cells.

The empirical result: F1 is partially predictive (best test AUC =
0.564, H1 PASS) but does not monetise (best realised Sharpe = -0.192,
H2 FAIL). The verdict is REJECT_BUT_INFORMATIVE.

This doc consolidates that finding into a binding observation and
enumerates the routing options. **It does NOT pre-approve any next
step.** That is the user's decision after this doc merges.

## §2. Scope

**In scope**:
- F1 finding interpretation (§3).
- Implications for Phase 25 design assumptions (§4).
- Routing options (§5; α / β / γ / δ; strictly neutral, no ranking).
- Updated decision tree (§6).

**Explicitly out of scope**:
- Implementing or designing F2-F6 in detail (separate per-class PRs).
- Modifying any prior Phase 25 PR's verdicts (#280 / #281 / #282 /
  #283 / #284).
- Modifying 22.x / 23.x / 24.x docs / artifacts.
- Relaxing NG#10 / NG#11.
- Modifying γ closure (PR #279).
- LightGBM design memo (would be 25.0c-α if pursued).
- Phase 25 closure declaration (premature with only one F-class
  evaluated).
- MEMORY.md update.

## §3. F1 finding (binding interpretation)

Empirical results from PR #284 (full 20-pair × 730d sweep):

| Aspect | Value |
|---|---|
| Best test AUC | 0.564 |
| H1 PASS cells | 2 / 24 (both M5 q=0.20 e=1.25) |
| Selected threshold (val only) | 0.40 |
| n_test trades (best cell) | 96 |
| Best realised Sharpe | -0.192 |
| Best realised ann_pnl | -107.6 pip |
| H2 (A1 + A2) | FAIL |
| Verdict | REJECT_BUT_INFORMATIVE |

### Binding interpretation

> *F1 is not pure noise. The volatility-derivative feature class
> achieves test AUC 0.564 (vs 0.50 random), demonstrating partial
> learnability of the path-quality binary label. However, the
> predictive signal does NOT monetise under the bidirectional +
> threshold + class-weight='balanced' logistic-regression pipeline at
> the locked 25.0b-α envelope: realised Sharpe is -0.192 and realised
> ann_pnl is -107.6 pip. F1 is recorded as **"learnable but not
> monetisable"** within the tested envelope.*

### Distinction (load-bearing)

- **Learnability** (test AUC > 0.55) is a model-class question — does
  logistic regression find structure in F1 features?
- **Monetisability** (realised Sharpe / ann_pnl) is a
  strategy-deployment question — does the structure translate into
  trade-decision value?

These are coupled but distinct. F1's result decouples them: the
structure exists; the strategy doesn't capture value.

## §4. Implications for Phase 25 design assumptions

### §4.1 Path-quality binary label IS partially predictable

Phase 25's choice of binary path-quality (vs trinary / regression
deferred at 25.0a-α §5) is at least partially validated — the label
is not unlearnable.

### §4.2 Logistic regression hits a ceiling on F1 features

Whether LightGBM would meaningfully lift AUC above 0.564 is
empirically open. 25.0b-α §6 deferred LightGBM "unless logistic AUC
≥ 0.55" — that condition is now met. LightGBM-on-F1 becomes an
admissible follow-up if pursued.

### §4.3 Trade-decision threshold + bidirectional logic doesn't capture the partial signal

Selected threshold 0.40 with `max(P_long, P_short) ≥ threshold` may
be a poor decision rule given AUC 0.564. Possible alternatives (NOT
in this PR):
- Probability calibration before threshold
- Fixed-threshold-per-direction with separate selection
- Top-K by confidence within a window
- Position sizing proportional to predicted probability

These are model-deployment refinements outside 25.0b-α's locked
envelope.

### §4.4 Per-cell admissibility filter is binding (sample-size pressure)

In the 25.0b-β sweep, most cells failed for `n_test < 100` (or 0 for
H1 cells). The 24-cell grid (3 TF × 2 lookback × 2 quantile × 2
expansion) over-explores at the cost of statistical power per cell.

For F2-F6, this suggests that per-class design memos may want to
consider:
- Cell counts closer to 18 (kickoff §10's lower bound) rather than 24.
- Wider admissibility thresholds (e.g., quantile up to 0.30 or
  expansion thresholds that retain more samples).

These are **soft suggestions only** — binding cell counts and
admissibility thresholds remain per-class design decisions fixed in
each F-class's design memo.

### §4.5 25.0a label dataset is sound (not the bottleneck)

The 25.0a-β labels passed pathological balance (overall positive rate
0.187, all per-pair rates ≥ 2%) and produced learnable signal in F1.
25.0a is a stable foundation for any subsequent feature class; no
direct evidence motivates revisiting 25.0a's threshold design.

## §5. Routing options (strictly neutral; no ranking)

### Option α — Pivot to next F-class (F2 / F3 / F4 / F5 / F6)

The Phase 25 kickoff (#280) admitted six F-classes; F1 has been
tested. The remaining five are admissible candidates. Each has
different cost / mechanism / orthogonality vs F1:

| F | Cost relative to F1 | Mechanism overlap with F1 | Admissibility risk |
|---|---|---|---|
| F2 (multi-TF vol regime) | Medium (extends F1 vol features with regime tags) | High (vol-derivative) | Likely similar AUC ~0.55 |
| F3 (cross-pair / basket) | High (multi-pair time alignment) | Low (orthogonal feature space) | Phase 9.X-D rejected DXY-alone — F3 must materially differ |
| F4 (range comp + breakout) | Medium | Medium (compression overlaps F1's f1_e) | Compression precondition mandatory per kickoff §4 |
| F5 (liquidity / spread) | High (volume column extension) | Low (orthogonal feature space) | Volume column not in current `load_m1_ba` |
| F6 (higher-TF M30/H1/H4) | Medium (TF aggregation extension) | Medium (overlaps F1's H1 timeframe) | F1's H1 cells had n_test=0 — F6 must address sample size |

Picking among F2-F6 is a strategic decision the user makes based on
which mechanism / feature axis is most informative to test next.

### Option β — LightGBM on F1 features

25.0b-α §6 deferred LightGBM until logistic showed AUC ≥ 0.55. That
condition is now met (AUC 0.564). LightGBM-on-F1 would re-use the
existing F1 feature engineering and trade-decision logic; the only
change is the model class.

Cost: ~1 sub-PR (25.0c-α design memo + 25.0c-β implementation; can
re-use most of 25.0b's code path). Expected lift: AUC 0.564 → 0.57-
0.59 with tree non-linearity is plausible but uncertain. Risk: tree
models with class_weight='balanced' on small admissible cells may
overfit; the multi-test penalty would stack on the already-evaluated
24 cells.

### Option γ — F1 envelope redesign

The 25.0b-α design constants are locked. A redesign requires a new
"25.0b-α-rev1" doc-only PR with explicit hypothesis BEFORE seeing
redesigned data (to avoid p-hacking). Examples of admissible
redesigns:
- Wider compression quantiles (e.g., {0.20, 0.30, 0.50}) to retain
  more samples.
- Lower expansion thresholds (e.g., {1.10, 1.20, 1.35}) to retain
  more samples.
- Smaller cell grid (e.g., 12 cells) to reduce multi-test penalty.
- Per-pair threshold instead of pooled.

Risk: post-hoc retuning of a single F-class's envelope after seeing
its results trends toward p-hacking. The user must decide whether the
redesign is justified by a falsifiable hypothesis or is fishing.

### Option δ — Phase 25 close

Documented for completeness; likely premature after only one
F-class, but available if the user chooses to stop. F1's
REJECT_BUT_INFORMATIVE result alone does not establish that all
admissible F-classes will fail; the framework demonstrably produces
partially-learnable signal. If chosen, this option triggers a Phase
25 final synthesis doc (analogous to PR #274 for Phase 24).

## §6. Updated decision tree

After this doc merges, the user routes to ONE of:

```
Phase 25 scope review post-F1
├── Option α — pivot to F-class (one of F2 / F3 / F4 / F5 / F6)
│   → next PR: phase25_0c_<f-class>_design.md (doc-only, 25.0c-α)
├── Option β — LightGBM on F1 features
│   → next PR: phase25_0c_alpha_lightgbm_f1.md (doc-only, 25.0c-α)
├── Option γ — F1 envelope redesign
│   → next PR: phase25_0b_alpha_rev1.md (doc-only, with explicit hypothesis)
└── Option δ — Phase 25 close
    → next PR: phase25_final_synthesis.md (doc-only)
```

This doc presents NO ranking among options. The user picks.

## §7. What this doc does NOT do

- Does not declare any option chosen.
- Does not modify Phase 25 kickoff (#280) / 25.0a-α (#281) / 25.0a-β
  (#282) / 25.0b-α (#283) / 25.0b-β (#284) — all stand as recorded.
- Does not relax NG#10 / NG#11.
- Does not modify γ closure (PR #279).
- Does not pre-approve any future PR's design constants.
- Does not pre-approve any production deployment.
- Does not update MEMORY.md.

## §8. Mandatory clauses (verbatim)

### Clause 1 — F1 finding (binding text from §3)

*F1 is not pure noise. The volatility-derivative feature class
achieves test AUC 0.564 (vs 0.50 random), demonstrating partial
learnability of the path-quality binary label. However, the
predictive signal does NOT monetise under the bidirectional +
threshold + class-weight='balanced' logistic-regression pipeline at
the locked 25.0b-α envelope: realised Sharpe is -0.192 and realised
ann_pnl is -107.6 pip. F1 is recorded as "learnable but not
monetisable" within the tested envelope.*

### Clause 2 — Phase 25 framing (inherited from #280)

*Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
feature-class redesign phase. Novelty must come from input feature
class and label design.*

### Clause 3 — Diagnostic-columns prohibition (inherited)

*The 25.0a-β diagnostic columns (max_fav_excursion_pip,
max_adv_excursion_pip, time_to_fav_bar, time_to_adv_bar,
same_bar_both_hit) MUST NOT appear in any model's feature matrix.*

### Clause 4 — γ closure preservation

*Phase 25.0b-β and this scope review do not modify the γ closure
(PR #279). Phase 25 results, regardless of outcome, do not change
Phase 24 / NG#10 β-chain closure status.*

### Clause 5 — Production-readiness preservation

*Any future Phase 25 PROMISING_BUT_NEEDS_OOS or ADOPT_CANDIDATE
verdict is hypothesis-generating only. Production-readiness requires
an X-v2-equivalent frozen-OOS PR per Phase 22 contract. No production
deployment is pre-approved by this doc.*

## §9. Phase 25 PR chain reference (#280 onward)

| PR | Stage | Purpose | Verdict / output |
|---|---|---|---|
| #280 | Phase 25 kickoff | Doc-only contract; F1-F6 admissible; binary path-quality | merged |
| #281 | 25.0a-α label design | Doc-only binding contract for label dataset | merged |
| #282 | 25.0a-β label dataset | 4.06M-row path-quality dataset; PASS pathological balance | merged |
| #283 | 25.0b-α F1 design | Doc-only binding contract for F1 24-cell sweep | merged |
| #284 | 25.0b-β F1 implementation | F1 eval; 2/24 cells H1 PASS; verdict REJECT_BUT_INFORMATIVE | merged |
| **this PR** | **Phase 25 scope review post-F1** | **Mid-stage synthesis; routing handed to user** | **doc-only** |

## §10. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase25_scope_review_post_f1.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x / 23.x / 24.x / 25.x docs/artifacts:
unchanged. NG#10 / NG#11: not relaxed. γ closure (PR #279):
preserved. Production deployment: not pre-approved.**

## §11. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 25 mid-stage synthesis — F1 = learnable, not monetisable; routing options handed to user.**
