# Phase 25 Second Scope Review — Post-F2 Mid-Stage Synthesis

Doc-only PR that records the F2 finding alongside F1 (PR #285) and
surfaces the **structural AUC-PnL gap** observed across both feature
classes. **No code, no eval, no implementation.** Single new file.

This is a **second mid-stage synthesis**, NOT a closure declaration.
Two of the six admissible F-classes (F1, F2) have been evaluated; the
deployment-layer hypothesis surfaced here has not yet been
investigated. Closing Phase 25 here would be premature. This doc
lays out the next-step options strictly neutrally and hands the
routing decision to the user.

## §1. Purpose and framing

Phase 25 kickoff (PR #280) opened path α from the γ closure (#279)
with six admissible feature classes (F1-F6) on a binary path-quality
label dataset (#281, #282). PR #285 recorded the F1 finding ("learnable
but not monetisable") and laid out routing options. The user picked
F2 next; PR #283 (25.0c-α) and PR #287 (25.0c-β) tested it.

**The empirical result**: F2 also produces partial learnability
(test AUC 0.5613) but does not monetise (best realised Sharpe
-0.317), with monetisability worse than F1.

This doc:
1. Records F2's finding as a binding observation alongside F1.
2. Names and frames the **structural AUC-PnL gap** observed across
   both F1 and F2.
3. Enumerates hypotheses (H-A through H-G) for why the gap exists.
4. Updates the routing decision tree with new evidence.
5. Lists next-step options including **deployment-layer
   investigations** (calibration / threshold / structural gap audit)
   as alternatives to feature redesign.
6. Stays strictly neutral — the user picks. No autonomous routing.

## §2. Scope

**In scope**:
- F2 finding interpretation alongside F1 (§3).
- "Structural AUC-PnL gap" framing as a binding observation across
  F1+F2 (§4).
- Hypotheses about why the gap exists (§5; no ranking).
- Per-option assessment of next steps (§6; no ranking).
- Updated decision tree (§7).

**Explicitly out of scope**:
- Implementing or designing F3-F6 in detail (separate per-class PRs).
- Implementing or designing deployment-layer experiments
  (calibration / position sizing / threshold). Those are separate
  downstream PRs if pursued.
- Modifying any prior Phase 25 PR's verdicts (#280-#287).
- Modifying 22.x/23.x/24.x docs/artifacts.
- Relaxing NG#10/NG#11.
- Modifying γ closure (PR #279).
- LightGBM design memo (mentioned only as supplementary downstream
  option in §6).
- Phase 25 closure declaration (premature; deployment-layer
  hypothesis not yet investigated).
- MEMORY.md update.

## §3. F2 finding (binding text)

Empirical results from PR #287 (full 20-pair × 730d sweep):

| Aspect | Value |
|---|---|
| Best full-sweep test AUC | 0.5613 |
| H1 PASS cells | 18 / 18 |
| Selected threshold (val only) | 0.40 |
| Best realised Sharpe | -0.317 |
| Best realised ann_pnl | -770,116.6 pip (~93k trades) |
| H2 PASS cells | 0 / 18 |
| Verdict | REJECT_BUT_INFORMATIVE |

### Binding interpretation

> *F2 multi-TF categorical volatility regime features achieve test
> AUC 0.5613 (vs 0.50 random; below F1's 0.564), demonstrating
> partial learnability of the path-quality binary label across a
> wider range of admissibility filters than F1. However, the
> predictive signal does NOT monetise — best realised Sharpe is
> -0.317 (worse than F1's -0.192). All three admissibility filters
> (none / high_alignment / transition) produce negative Sharpe;
> high_alignment is least-bad but still negative. F2 is recorded as
> **"learnable but not monetisable, monetisability worse than F1"**
> within the tested envelope.*

## §4. The structural AUC-PnL gap (the load-bearing new finding)

### §4.1 Convergent pattern across F1 + F2

| Metric | F1 (continuous vol-derivative) | F2 (categorical regime) |
|---|---|---|
| Best test AUC | 0.564 | 0.5613 |
| Best realised Sharpe | -0.192 | -0.317 |
| H1 PASS rate | 2 / 24 (8%) | 18 / 18 (100%) |
| H2 PASS rate | 0 / 24 | 0 / 18 |
| Verdict | REJECT_BUT_INFORMATIVE | REJECT_BUT_INFORMATIVE |

Two materially different feature classes — one continuous magnitudes,
one categorical regime tags — produce essentially the same AUC
ceiling (~0.56) and both fail H2 with negative realised Sharpe.

### §4.2 Binding observation

> *F1 (continuous vol-derivative magnitudes) and F2 (categorical
> multi-TF volatility regime tags) — two materially different feature
> classes — produce convergent ceilings under the Phase 25
> deployment pipeline:*
>
> - *Both achieve test AUC ≈ 0.56 (modest learnability; well above
>   0.50 chance);*
> - *Both produce realised Sharpe in the range [−0.32, −0.19] (no
>   monetisation);*
> - *Both verdict REJECT_BUT_INFORMATIVE under the same H1/H2 routing
>   logic.*
>
> *This convergence suggests the binding constraint may not be the
> feature class. Two distinct feature inputs hit the same wall,
> indicating the wall may be located DOWNSTREAM of the feature
> engineering step — at the deployment layer (path-quality binary
> label semantic, bidirectional logistic + L2 + class_weight=
> 'balanced', threshold candidates {0.20-0.40}, val-only Sharpe-proxy
> threshold selection, K_FAV=1.5 / K_ADV=1.0 barrier asymmetry,
> realised barrier PnL accounting).*
>
> ***This is a hypothesis to be tested in subsequent PRs, NOT a
> conclusion.*** *Two data points is suggestive but not definitive;
> F3-F6 may produce different patterns. The deployment-layer wall is
> a candidate explanation; the candidate options in §6 are designed
> to test it.*

## §5. Hypotheses about the gap (no ranking)

The doc enumerates seven hypotheses for why partial learnability
fails to monetise. **None is endorsed; all are testable.** They are
listed alphabetically, not by priority.

### H-A — Calibration mismatch

Model's predicted P(positive) ≥ 0.40 doesn't actually correspond to
>50% realised positive rate (which would be needed for trade-decision
logic to break even). The model is informative (AUC > 0.55) but
mis-calibrated.

**What would test it**: reliability diagram on F1 / F2 best cell at
the selected threshold. If predicted ≥ 0.40 bucket has actual
positive rate ≪ 0.50, calibration is the issue.

### H-B — Threshold range too low

Threshold candidates {0.20, 0.25, 0.30, 0.35, 0.40} cap below
break-even. Higher thresholds {0.50, 0.60, 0.70} might produce
positive realised EV by trading less frequently but at higher
predicted-confidence buckets.

**What would test it**: re-run F1 / F2 best cell with extended
threshold sweep on validation only; check if any extended threshold
yields positive val Sharpe proxy that survives test.

### H-C — Class-weight bias

`class_weight='balanced'` over-weights the minority positive class
(positive rate ~0.187), skewing predicted P(positive) upward away
from realistic positive rate.

**What would test it**: re-run without `class_weight='balanced'` (or
with sample_weight inverse-frequency) and compare AUC + realised
Sharpe.

### H-D — Bidirectional argmax flaw

`max(P_long, P_short) ≥ threshold` picks the noisier of two
predictions. The argmax operation may be biased toward whichever
direction has higher noise-induced predicted probability.

**What would test it**: run directional candidate generation
(per-direction model + per-direction threshold) instead of
bidirectional argmax. Compare per-direction Sharpe to the
bidirectional argmax Sharpe.

### H-E — K_FAV / K_ADV asymmetry too tight

K_FAV=1.5 ATR favorable target vs K_ADV=1.0 ATR adverse gives
expected per-trade pnl = P(pos) × 1.5 ATR − P(neg) × 1.0 ATR. With
P(pos | predicted high) ≈ 0.55 (AUC 0.56 ceiling), expected pnl ≈
0.55 × 1.5 − 0.45 × 1.0 = 0.375 ATR ≈ 3-5 pip. Spread cost on FX
scalping typically exceeds this margin.

**What would test it**: re-run 25.0a label generation with
K_FAV ≥ 2.0 (separate redesign PR; would invalidate F1+F2 by
re-labeling).

### H-F — Per-trade EV after spread cost is structurally negative

AUC 0.56 is insufficient to overcome typical FX scalping spread cost
regardless of pipeline. The bound is fundamental to the noise level
of M5/M15 path-quality, not a deployment-layer artifact.

**What would test it**: direct calculation per cell — at the
selected threshold, compute P(pos | predicted ≥ threshold) ×
K_FAV×ATR − P(neg | predicted ≥ threshold) × K_ADV×ATR vs
spread_at_signal. If the difference is negative for ALL cells,
the structural gap is fundamental.

### H-G — Binary label collapses too much signal

Binary path-quality (positive / negative) collapses the path-shape
information that trinary or regression labels would expose.
F1+F2's AUC ceiling at 0.56 may reflect the binary label's
information-theoretic limit, not the feature class.

**What would test it**: re-run 25.0a with trinary (clear-pos /
neutral / clear-neg) or regression (continuous path-EV) labels;
re-run F1 / F2 evaluation. (Deferred per 25.0a-α §5 — major
redesign.)

## §6. Next-step options (strictly neutral; no ranking)

The doc enumerates five routing options. **No recommendation.** Each
option lists what hypothesis it tests, cost, and risk.

### Option A — Deployment-layer investigation

A focused PR that takes F1 or F2 best cell and:
1. Plots reliability diagram (P(predicted) bucketed vs realised
   positive rate).
2. Computes per-bucket expected PnL after spread cost.
3. Identifies whether ANY threshold produces positive realised EV.

If no threshold produces positive EV, the structural gap is
confirmed at the deployment layer; feature redesign won't help. If
some threshold does, the answer is "extend threshold range"
(addresses H-B) or "calibrate before threshold" (addresses H-A).

**Tests**: H-A, H-B, H-D (partially), H-F.
**Cost**: ~1 small PR. Most informative per unit cost.
**Risk**: low; doc-only or small-script analysis.

### Option B — Threshold extension experiment

Extend threshold candidates from {0.20-0.40} to {0.20, 0.30, 0.40,
0.50, 0.60, 0.70} on F1 or F2 best cell. If higher thresholds
produce positive Sharpe, the original range was binding.

**Tests**: H-B specifically.
**Cost**: ~1 small implementation PR.
**Risk**: low; same data, same model, different threshold sweep.

### Option C — Pivot to F3 / F4 / F5 / F6

Continue the originally-planned F-class iteration. F3 cross-pair /
F5 liquidity are the most-orthogonal to F1+F2's vol focus. F4 range
compression and F6 higher-TF have partial overlap with F1's
mechanism.

**Tests**: implicitly — if F3-F6 also produce learnable-but-not-
monetisable, the structural-gap hypothesis is reinforced. If one
produces monetisable signal, the gap was feature-class-specific.
**Cost**: ~2 PRs per F-class (design + implementation). Per
direction §11 cell-count budget 18-33.
**Risk**: if F1+F2's wall is structural at the deployment layer,
F3-F6 will hit the same wall; this option may not lift it.

### Option D — Label redesign (trinary / regression)

Redesign 25.0a labels from binary to trinary or regression. Major
redesign with implications for all downstream feature classes (F1
and F2 evaluations would need to be re-run if this proceeds; their
current verdicts would still stand on the binary label).

**Tests**: H-G specifically.
**Cost**: 25.0a-α-rev1 (doc-only) → 25.0a-β-v2 (impl) → re-run F1+F2
under new labels → second post-F2 review. Largest investment.
**Risk**: post-hoc label retuning after seeing F1+F2 binary results
trends toward p-hacking unless justified by an explicit
information-theoretic hypothesis (e.g., direct measurement of binary
label entropy vs trinary entropy).

### Option E — Phase 25 close

Documented for completeness; **likely premature after only two of
six admissible feature classes, but available if the user chooses
to stop**. F1 and F2's REJECT_BUT_INFORMATIVE results alone do not
establish that all admissible feature classes will fail; the
deployment-layer hypothesis (§4.2, §5) has not yet been tested.

If chosen, this option triggers a Phase 25 final synthesis doc
(analogous to PR #274 for Phase 24).

### Supplementary downstream note — LightGBM

LightGBM is a model-class change (tree non-linearity) NOT a
deployment-layer or feature-class change. It does not directly test
any of H-A through H-G. LightGBM remains available as a follow-up
within Option C or as a sub-experiment within Option B, but is not
a primary scope-review option here.

## §7. Updated decision tree

After this doc merges, the user routes to ONE of:

```
Phase 25 second scope review post-F2
├── Option A — Deployment-layer investigation (H-A, H-B, H-D, H-F)
│   → next PR: phase25_deployment_audit.md OR phase25_calibration_audit_eval (impl)
├── Option B — Threshold extension experiment (H-B)
│   → next PR: phase25_threshold_extension_eval (impl)
├── Option C — Pivot to F-class (F3 / F4 / F5 / F6)
│   → next PR: phase25_0d_<f-class>_design.md (doc-only)
├── Option D — Label redesign (trinary / regression; H-G)
│   → next PR: phase25_0a_alpha_rev1.md (doc-only)
└── Option E — Phase 25 close
    → next PR: phase25_final_synthesis.md (doc-only)
```

This doc presents NO ranking among options. The user picks.

## §8. Mandatory clauses (verbatim in this doc; six)

### Clause 1 — F2 finding (binding text from §3)

*F2 multi-TF categorical volatility regime features achieve test
AUC 0.5613 (below F1's 0.564), demonstrating partial learnability
of the path-quality binary label. However, the predictive signal
does NOT monetise — best realised Sharpe is -0.317 (worse than F1's
-0.192). All three admissibility filters produce negative Sharpe;
high_alignment is least-bad but still negative. F2 is recorded as
"learnable but not monetisable, monetisability worse than F1"
within the tested envelope.*

### Clause 2 — Structural AUC-PnL gap (binding observation from §4.2)

*F1 and F2 — two materially different feature classes — produce
convergent ceilings (test AUC ≈ 0.56; realised Sharpe in
[−0.32, −0.19]; both REJECT_BUT_INFORMATIVE). This convergence
suggests the binding constraint may be at the deployment layer
rather than the feature class. **This is a hypothesis to be tested,
NOT a conclusion** — two data points is suggestive but not
definitive.*

### Clause 3 — Phase 25 framing (inherited from #280)

*Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
feature-class redesign phase. Novelty must come from input feature
class and label design.*

### Clause 4 — Diagnostic-columns prohibition (inherited)

*The 25.0a-β diagnostic columns (max_fav_excursion_pip,
max_adv_excursion_pip, time_to_fav_bar, time_to_adv_bar,
same_bar_both_hit) MUST NOT appear in any model's feature matrix.*

### Clause 5 — γ closure preservation

*Phase 25 (any sub-stage) does not modify the γ closure (PR #279).
Phase 25 results, regardless of outcome, do not change Phase 24 /
NG#10 β-chain closure status.*

### Clause 6 — Production-readiness preservation

*Any future Phase 25 PROMISING_BUT_NEEDS_OOS or ADOPT_CANDIDATE
verdict is hypothesis-generating only. Production-readiness requires
an X-v2-equivalent frozen-OOS PR per Phase 22 contract. No
production deployment is pre-approved by this doc.*

## §9. Phase 25 PR chain reference (#280 onward)

| PR | Stage | Purpose | Verdict / output |
|---|---|---|---|
| #280 | Phase 25 kickoff | Doc-only contract; F1-F6 admissible; binary path-quality | merged |
| #281 | 25.0a-α label design | Doc-only binding contract for label dataset | merged |
| #282 | 25.0a-β label dataset | 4.06M-row path-quality dataset; PASS pathological balance | merged |
| #283 | 25.0b-α F1 design | Doc-only binding contract for F1 24-cell sweep | merged |
| #284 | 25.0b-β F1 implementation | F1 eval; 2/24 cells H1 PASS; verdict REJECT_BUT_INFORMATIVE | merged |
| #285 | Phase 25 first scope review (post-F1) | Mid-stage synthesis; routing handed to user | merged |
| #286 | 25.0c-α F2 design | Doc-only binding contract for F2 18-cell sweep | merged |
| #287 | 25.0c-β F2 implementation | F2 eval; 18/18 cells H1 PASS; verdict REJECT_BUT_INFORMATIVE | merged |
| **this PR** | **Phase 25 second scope review (post-F2)** | **Mid-stage synthesis; structural AUC-PnL gap surfaced; routing handed to user** | **doc-only** |

## §10. What this doc does NOT do

- Does not declare any option chosen.
- Does not modify Phase 25 kickoff (#280) / 25.0a-α (#281) / 25.0a-β
  (#282) / 25.0b-α (#283) / 25.0b-β (#284) / first scope review
  (#285) / 25.0c-α (#286) / 25.0c-β (#287) — all stand as recorded.
- Does not relax NG#10 / NG#11.
- Does not modify γ closure (PR #279).
- Does not pre-approve any future PR's design constants.
- Does not pre-approve any production deployment.
- Does not update MEMORY.md.

## §11. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase25_second_scope_review_post_f2.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x / 23.x / 24.x / 25.x docs/artifacts:
unchanged. NG#10 / NG#11: not relaxed. γ closure (PR #279):
preserved. Production deployment: not pre-approved.**

## §12. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 25 second scope review — F1 + F2 hit same AUC-PnL ceiling; deployment-layer hypothesis surfaced; routing handed to user.**
