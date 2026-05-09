# Phase 25 Routing Review — Post-Deployment-Audit Mid-Stage Synthesis

Doc-only PR consolidating the F1 + F2 + 25.0d-β findings into a
framework for the remaining F-class decisions. **No code, no eval,
no implementation.** Single new file.

This is a **third mid-stage synthesis** (after PR #285 post-F1 and
PR #288 post-F2). Two of the six admissible F-classes have been
evaluated, plus a deployment-layer audit on both best cells, giving
three converging data points. F3-F6 remain admissible candidates;
this doc surfaces the prioritisation framework and stop conditions
that should govern their evaluation, but does NOT pick the next
F-class.

## §1. Purpose and framing

Phase 25 has produced three convergent data points on the AUC-PnL
gap question:

1. PR #284 — F1 (continuous vol-derivative): test AUC 0.564,
   realised Sharpe -0.192, REJECT_BUT_INFORMATIVE.
2. PR #287 — F2 (categorical multi-TF vol regime): test AUC 0.5613,
   realised Sharpe -0.317, REJECT_BUT_INFORMATIVE.
3. PR #290 — Deployment-layer audit on F1+F2 best cells: H-A
   miscalibrated, H-B threshold extension refuted, H-D directional
   argmax produces no convergent monetisation, H-F empirical /
   theoretical CONFIRMED on both cells.

This doc:
- Records the 25.0d-β finding (§3).
- Updates the evidence consolidation across the three data points
  (§4).
- Proposes a 3-axis prioritisation framework for F3/F4/F5/F6 (§5).
- Defines stop conditions for Phase 25 (§6).
- Lists 7 routing options strictly neutrally (§7).

It does not pre-approve any next step. The user picks based on the
framework + stop conditions.

## §2. Scope

**In scope**:
- 25.0d-β finding interpretation (§3).
- Updated evidence consolidation across F1+F2+25.0d (§4).
- Per-class prioritisation framework (§5).
- Stop conditions for Phase 25 (§6).
- Routing options (§7; strictly neutral).

**Explicitly out of scope**:
- Designing or implementing F3/F4/F5/F6.
- Modifying any prior Phase 25 PR's verdicts (#280-#290).
- Modifying 22.x/23.x/24.x docs/artifacts.
- Relaxing NG#10/NG#11.
- Modifying γ closure (PR #279).
- LightGBM design memo.
- Phase 25 closure declaration (premature; F3-F6 admissible
  candidates remain).
- Pre-approving any F-class as next.
- MEMORY.md update.

## §3. 25.0d-β finding (binding text)

Empirical results from PR #290:

| Aspect | F1 rank-1 | F2 rank-1 |
|---|---|---|
| n_test | 96 (low-power qualitative) | 591,004 (high-power) |
| test AUC | 0.5644 | 0.5613 |
| H-A calibration | MISCALIBRATED | MISCALIBRATED |
| H-B threshold extension | REFUTED | REFUTED |
| H-D directional argmax | REFUTED | PARTIAL_LIFT_BUT_STILL_NEG |
| H-F empirical | CONFIRMED | CONFIRMED |
| H-F theoretical | CONFIRMED | CONFIRMED |

### Binding interpretation

> *Even after H-A miscalibration is identified AND H-B threshold
> extension AND H-D directional comparison are tested, **no
> deployment-layer fix produces positive realised PnL on either F1
> or F2 best cell**. This pattern strongly supports **H-F
> (structural gap fundamental)** at the AUC ≈ 0.56 / K_FAV=1.5 /
> K_ADV=1.0 / 25.0a-β-spread setup.*
>
> *Per 25.0d-α §8 binding clause, the theoretical bound is
> diagnostic-only and the empirical findings drive the verdict. The
> structural-gap-confirmed verdict applies only to F1+F2 best
> cells; convergence with F3-F6 is a separate question.*

## §4. Updated evidence consolidation across F1+F2+25.0d

| Data point | Source | Finding |
|---|---|---|
| F1 best cell (continuous vol-derivative) | PR #284 | test AUC 0.564, realised Sharpe -0.192, REJECT_BUT_INFORMATIVE |
| F2 best cell (categorical multi-TF vol regime) | PR #287 | test AUC 0.5613, realised Sharpe -0.317, REJECT_BUT_INFORMATIVE |
| F1+F2 deployment audit | PR #290 | H-A miscalibrated; H-B/H-D refuted; H-F empirical+theoretical CONFIRMED on both |

### Binding observation

> *Three converging data points (F1 empirical, F2 empirical, F1+F2
> deployment audit) support the AUC-PnL gap on M5 path-quality
> binary labels under the K_FAV=1.5 / K_ADV=1.0 / OANDA-class spread
> setup as **fundamental at the AUC ≈ 0.56 ceiling within the tested
> feature classes**.*
>
> ***This is a stronger hypothesis than after PRs #285 / #288 (which
> had 1 and 2 data points respectively), but is still bounded to the
> tested feature classes (F1, F2). AUC-PnL gap is strongly supported
> for F1/F2, but is not proven for all remaining F-classes.***
>
> *F3, F4, F5, F6 may either:*
> - *(a) hit the same wall (further confirming the structural-gap
>   hypothesis),*
> - *(b) lift AUC above 0.56 (refuting the AUC-ceiling part of the
>   hypothesis),*
> - *(c) lift realised PnL despite same AUC (refuting the
>   deployment-pipeline part).*
>
> *Three data points is suggestive but not definitive across the
> entire admissible feature-class space; the framework in §5 helps
> the user prioritise which remaining class would most efficiently
> test the open hypotheses.*

## §5. Per-class prioritisation framework (informational; no pre-decided choice)

Three axes for evaluating each remaining admissible F-class. Each
axis is rated relative to F1+F2's mechanism and to the constraints
of the tested envelope (25.0a labels, 25.0b/0c pipeline).

### §5.1 Axis 1 — Mechanism distance from F1+F2 (orthogonality)

| F-class | Distance from F1 (continuous vol) | Distance from F2 (regime vol) | Composite |
|---|---|---|---|
| F3 cross-pair / currency strength | HIGH | HIGH | **HIGH** |
| F4 range compression then expansion | LOW-MED (overlap with f1_e) | MED | LOW-MED |
| F5 liquidity / spread / volume | HIGH | HIGH | **HIGH** |
| F6 higher-TF (M30/H1/H4) | LOW-MED (overlap with f1_a H1) | LOW (regime is multi-TF) | LOW-MED |

### §5.2 Axis 2 — Implementation complexity

| F-class | Data extension | Code complexity | Composite |
|---|---|---|---|
| F3 cross-pair | NONE (20 pairs already loaded) | HIGH (multi-pair time alignment) | MED-HIGH |
| F4 range comp | NONE | MED (Bollinger-band squeeze + breakout logic) | MED |
| F5 liquidity | YES (volume column extension to load_m1_ba) | MED-HIGH (volume + spread time series) | HIGH |
| F6 higher-TF | YES (TF aggregation extension; partly done in 25.0c) | LOW-MED (re-uses existing aggregation patterns) | MED |

### §5.3 Axis 3 — Risk of repeating AUC-PnL gap

The 25.0d-β audit confirmed the gap is fundamental for F1+F2.
Per-class risk that F3-F6 hit the same wall:

| F-class | Risk of same wall | Reasoning |
|---|---|---|
| F3 cross-pair | MED | Cross-pair info may push AUC > 0.56 (unlike pure vol). But spread cost still binds. |
| F4 range comp | HIGH | Mechanism overlaps F1's f1_e (range-score); likely same AUC ceiling |
| F5 liquidity | MED | Liquidity / spread features may correlate with the K_FAV/K_ADV/spread economics directly |
| F6 higher-TF | MED-HIGH | Higher-TF features test the same path-quality label; AUC may not lift, sample-size pressure on H1+ |

### §5.4 Composite priority (informational only; no pre-decided choice)

| F-class | Orthogonality | Complexity | Risk-of-same-wall | Composite priority |
|---|---|---|---|---|
| F3 | HIGH | MED-HIGH | MED | **highest by orthogonality** |
| F5 | HIGH | HIGH | MED | high orthogonality, but data extension cost |
| F4 | LOW-MED | MED | HIGH | lower-priority due to overlap with F1 |
| F6 | LOW-MED | MED | MED-HIGH | lower-priority due to overlap with F1/F2 |

> **This table is informational only. The user picks the next F-class
> (or option E/F/G) based on §6 stop conditions and §7 routing. No
> F-class is pre-decided as "the next step" by this doc.**

## §6. Stop conditions for Phase 25

The doc defines four categories of stop conditions, in increasing
order of evidence required:

### §6.1 Definitive stop (Phase 25 final synthesis)

- **All 6 admissible F-classes (F1-F6) tested AND no F-class achieves
  H2 PASS** → Phase 25 final synthesis required regardless of
  individual verdicts. The full search space is exhausted.

### §6.2 Strong soft stop (consider close)

- **4 of 6 F-classes tested AND all 4 show REJECT_BUT_INFORMATIVE
  with structural-gap signature** (test AUC ≈ 0.55-0.58, realised
  Sharpe negative, no deployment-layer fix monetises) → user
  judgement; structural-gap evidence is overwhelming and continuing
  the remaining 2 F-classes may be wasted effort. The natural call
  is Phase 25 close OR pivot to label redesign (Option F).

### §6.3 Soft stop (consider close)

- **3+ F-classes tested AND all 3+ show the same structural-gap
  signature** → user may invoke Phase 25 close at this point if
  evidence is judged sufficient. The case is suggestive but not
  conclusive; user judgement.

### §6.4 F3-specific stop strengthening

> *F3 is the most orthogonal of the remaining admissible candidates
> (HIGH on §5.1 axis vs F1+F2). **If F3 also shows the same AUC-PnL
> gap, the case for soft stop strengthens substantially** — F3's
> orthogonality means the gap is not a vol-feature artifact but a
> property of the M5 path-quality binary label + barrier + spread
> setup. After F3+F1+F2 = 3 cells with the same gap, the user has a
> strong case for either Phase 25 close (Option G) or label redesign
> (Option F).*

### §6.5 Pivot (continue research outside Phase 25)

- **Any F-class produces test AUC > 0.58 on full-sample baseline** →
  pivot to deployment-layer redesign for that specific F-class
  (still NOT label redesign). The AUC-ceiling part of the
  structural-gap hypothesis is refuted for that F-class; the rest
  of the pipeline may still need work.
- **Any F-class produces realised Sharpe ≥ +0.082 with frozen-OOS
  PR survival** → ADOPT_CANDIDATE; production-readiness path opens
  per Phase 22 contract.

### §6.6 Label redesign trigger

If F3-F6 ALL produce AUC ≈ 0.56 ceiling → label binarity may be
the binding constraint (per H-G from PR #288). Trinary / regression
label redesign becomes the natural next axis (Option F).

## §7. Routing options post-merge (strictly neutral; no ranking)

Seven options. The doc makes no recommendation; the user picks.

| Option | What | Mechanism / scope | Cost |
|---|---|---|---|
| **A** | Continue with F3 (cross-pair) | Most orthogonal; tests AUC-ceiling fundamentality | medium |
| **B** | Continue with F5 (liquidity) | Orthogonal but spread-correlated; data extension required | medium-high |
| **C** | Continue with F4 (range compression) | **Lower priority** due to overlap with F1's f1_e | medium |
| **D** | Continue with F6 (higher-TF) | **Lower priority** due to overlap with F1/F2 (H1 timeframe) | medium |
| **E** | Calibration-before-threshold PR | Tests whether H-A fix alone monetises despite H-B/H-D refuted | small |
| **F** | Label redesign (trinary / regression; H-G from #288) | Major redesign; would invalidate F1+F2 evals | large |
| **G** | Phase 25 close | Considers F1+F2+25.0d evidence sufficient; final synthesis doc | small |

C and D are flagged as **lower-priority due to overlap with F1/F2** —
the user can still pick them but should weigh that against the
overlap cost.

E (calibration-before-threshold) tests a deployment-layer fix that
PR #290 did not directly address. It is a small-cost single-cell
experiment; even if it doesn't monetise, the negative result
strengthens H-F.

F (label redesign) is the largest investment and would require
invalidating F1+F2 to re-run under new labels. It is the natural
fall-back if F3-F6 also confirm the AUC-PnL gap (per §6.6).

G (Phase 25 close) is available if the user judges F1+F2+25.0d
evidence sufficient.

## §8. Suggestion (not mandate) for future F-class implementations

> *Future F-class design memos should consider including calibration
> diagnostics (decile reliability + Brier score) from the start,
> especially if H1 passes. PR #290 found H-A miscalibrated on both
> F1 and F2 best cells — building calibration check into per-class
> design from the start would catch the miscalibration earlier and
> may inform per-class design choices (e.g., calibration method,
> threshold candidate range).*
>
> ***This review does not retroactively mandate a new harness*** —
> existing PRs #283 (F1 design) and #286 (F2 design) stand. Future
> F-class design memos may opt to include calibration; the choice
> is per-class.

## §9. Mandatory clauses (verbatim in this doc; six)

### Clause 1 — 25.0d-β finding (binding text from §3)

*Even after H-A miscalibration is identified AND H-B threshold
extension AND H-D directional comparison are tested, no
deployment-layer fix produces positive realised PnL on either F1 or
F2 best cell. This pattern strongly supports H-F (structural gap
fundamental) at the AUC ≈ 0.56 / K_FAV=1.5 / K_ADV=1.0 /
25.0a-β-spread setup. Theoretical bound is diagnostic-only; the
verdict applies only to F1+F2 best cells; convergence with F3-F6 is
a separate question.*

### Clause 2 — Updated evidence consolidation (binding observation from §4)

*Three converging data points (F1 empirical, F2 empirical, F1+F2
deployment audit) support the AUC-PnL gap as fundamental at the
AUC ≈ 0.56 ceiling within the tested feature classes. AUC-PnL gap
is strongly supported for F1/F2, but is not proven for all
remaining F-classes. Three data points is suggestive but not
definitive across the entire admissible feature-class space.*

### Clause 3 — Phase 25 framing (inherited from #280)

*Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
feature-class redesign phase.*

### Clause 4 — Diagnostic columns prohibition (inherited)

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

## §10. Phase 25 PR chain reference (#280 → #290)

| PR | Stage | Purpose | Verdict / output |
|---|---|---|---|
| #280 | Phase 25 kickoff | Doc-only contract; F1-F6 admissible; binary path-quality | merged |
| #281 | 25.0a-α label design | Doc-only binding contract for label dataset | merged |
| #282 | 25.0a-β label dataset | 4.06M-row path-quality dataset; PASS pathological balance | merged |
| #283 | 25.0b-α F1 design | Doc-only binding contract for F1 24-cell sweep | merged |
| #284 | 25.0b-β F1 implementation | F1 eval; 2/24 H1 PASS; verdict REJECT_BUT_INFORMATIVE | merged |
| #285 | first scope review (post-F1) | Mid-stage synthesis; routing handed to user | merged |
| #286 | 25.0c-α F2 design | Doc-only binding contract for F2 18-cell sweep | merged |
| #287 | 25.0c-β F2 implementation | F2 eval; 18/18 H1 PASS; verdict REJECT_BUT_INFORMATIVE | merged |
| #288 | second scope review (post-F2) | Mid-stage synthesis; structural AUC-PnL gap surfaced | merged |
| #289 | 25.0d-α deployment audit design | Doc-only binding contract for F1+F2 audit | merged |
| #290 | 25.0d-β deployment audit | H-A miscal; H-B/H-D refuted; H-F empirical+theoretical confirmed | merged |
| **this PR** | **routing review post-deployment-audit** | **Mid-stage synthesis; F3-F6 prioritisation framework + stop conditions** | **doc-only** |

## §11. What this doc does NOT do

- Does not declare any option chosen.
- Does not modify Phase 25 PRs #280-#290.
- Does not modify F1/F2/25.0d verdicts.
- Does not relax NG#10 / NG#11.
- Does not modify γ closure (PR #279).
- Does not pre-approve any future PR's design constants.
- Does not pre-approve any production deployment.
- Does not retroactively mandate a calibration harness for past
  F-class evaluations.
- Does not update MEMORY.md.

## §12. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase25_routing_review_post_deployment_audit.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x/23.x/24.x/25.x docs/artifacts:
unchanged. NG#10/NG#11: not relaxed. γ closure (PR #279):
preserved. Production deployment: not pre-approved.**

## §13. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 25 routing review post-deployment-audit — 3 data points converge on structural gap; F3-F6 prioritisation framework + stop conditions surfaced; routing handed to user.**
