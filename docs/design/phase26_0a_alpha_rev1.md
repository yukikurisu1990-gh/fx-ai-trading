# Phase 26.0a-α-rev1 — Threshold-Selection Design Revision

**Type**: doc-only revision (addendum on top of PR #301 26.0a-α)
**Status**: revises §5.2 threshold candidates ONLY; all other 26.0a-α resolutions remain binding
**Branch**: `research/phase26-0a-alpha-rev1`
**Base**: master @ aa11429 (post-PR #301 merge — 26.0a-α L-3 design memo)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Context and approval semantics

This memo is an **addendum** to the original 26.0a-α design memo (PR #301 at `docs/design/phase26_0a_alpha_l3_design.md`). The original memo remains in place unmodified for audit-trail discipline. Rev1 amends ONLY the threshold-candidate spec in original §5.2, and the supporting unit-test / sign-off references in original §10 / §14.

**Squash-merge approval of this PR binds the rev1 threshold-selection redesign (§3–§7), the quantile-fit rule (§4), the eval-report contrast requirement (§7), and the six additional unit tests (§10). The rev1 26.0a-β re-implementation PR opens only on the user's separate explicit authorisation.** No implementation work is associated with this PR.

---

## 1. Why rev1 (contract-spec gap, NOT a bug)

The in-progress 26.0a-β implementation (local branch `research/phase26-0a-beta-l3-eval`; NOT pushed) ran the binding 24-cell sweep cleanly and surfaced a structural gap in the original §5.2 threshold candidates.

| Diagnostic finding (from the NOT-yet-pushed 26.0a-β run) | Detail |
|---|---|
| L-3 label construction | Compliant with original §3 / §3.1 (mid-to-mid base PnL; spread subtracted exactly once; D-5 scale applied last). Code is correct. |
| Regression ranking signal | **Exists**: best test Spearman = +0.3836 (entry_only / raw_pip / no-clip / LightGBM). The model DOES rank rows by realised PnL. |
| Validation trade count | **Zero across all 24 cells.** Regression target mean is structurally negative (FX scalping ≈ 73% SL × −K_ADV·atr + 20% TP × +K_FAV·atr + 6% TIME ≈ −4 pip per row, raw; ≈ −0.4 ATR-multiple). Predictions concentrate on the negative side. Original candidates `{0.0, 1.0, 2.0, 3.0, 4.0}` raw pip / `{0.0, 0.1, 0.2, 0.3, 0.4}` ATR never fire. |
| Verdict under original §5.3 rule | `REJECT_NON_DISCRIMINATIVE / NO_VALID_CELL` — but this conflates "L-3 has no signal" (false, given Spearman +0.38) with "thresholds don't fire" (true, but a contract-spec property, not an L-3 property). |

**This is not a bug.** The implementation honoured the binding 26.0a-α contract exactly. The gap is in the threshold-candidate axis of the contract itself: §5.2 implicitly assumed regression predictions could span both signs.

Rev1 redesigns this single axis. No other contract element changes.

---

## 2. Existing absolute thresholds ≥ 0 are insufficient (binding statement)

> *Absolute threshold candidates `{0.0, 1.0, 2.0, 3.0, 4.0}` pip and `{0.0, 0.1, 0.2, 0.3, 0.4}` ATR-multiple specified in PR #301 §5.2 were valid under the implicit assumption that regression predictions could span both signs. Under L-3 (where ~73% of rows are SL outcomes), the regression target mean is structurally negative, and predictions concentrate on the negative side. The original ≥ 0 candidates therefore never fire, regardless of cell. This is a contract-spec gap, NOT a label or implementation failure. The L-3 label construction (§3 / §3.1 of the original 26.0a-α) is correct and is NOT amended by this rev1.*

---

## 3. Quantile-based threshold family (primary; binding from rev1)

> *Quantile-based candidates become the **primary** threshold family in rev1. Each candidate q selects the **top q% by predicted EV on validation**. The cutoff value is fit on the validation prediction distribution and applied to the test prediction distribution. Full-sample qcut (fitting on train + val + test combined, or on test alone) is PROHIBITED.*

| ID | Candidate | Description |
|---|---|---|
| Q-5  | top 5%  | trade the top 5 percent of val predictions by predicted EV |
| Q-10 | top 10% | trade the top 10 percent |
| Q-20 | top 20% | trade the top 20 percent |
| Q-30 | top 30% | trade the top 30 percent |
| Q-40 | top 40% | trade the top 40 percent |

### 3.1 Why quantile (binding rationale)

- **Scale-invariant**: works identically for raw_pip and ATR-normalised target scales without per-scale candidate sets.
- **Robust to prediction-distribution location**: no need to anticipate where the regression mean lands; the quantile finds it.
- **Natural deployment interpretation**: maps cleanly to "trade the top-K% of conviction", which is operationally how a real-time deployment would gate trades.
- **Compatible with original §5.3 selection rule**: the (cell, q) pair is selected exactly like the (cell, threshold) pair was — same priority order, same A0-equivalent pre-filter, same deterministic tie-breakers.

---

## 4. Quantile-fit rule (binding for rev1 26.0a-β re-implementation)

> *For each cell, the quantile cutoff is fit on the **validation prediction distribution only**. The fitted scalar cutoff is then applied to the test prediction distribution. NO full-sample qcut. NO peeking at test predictions for cutoff fitting.*

**Implementation pattern (binding):**

```
For each cell c:
    pred_val  = model_c.predict(val_features)
    pred_test = model_c.predict(test_features)

    For each candidate q in {Q-5, Q-10, Q-20, Q-30, Q-40}:
        # Fit cutoff on val ONLY
        cutoff_q = np.quantile(pred_val, 1.0 - q/100.0)

        # Trade on val: rows where pred_val >= cutoff_q
        val_traded = (pred_val >= cutoff_q)
        # Compute val realised barrier PnL via M1 path re-traverse on val_traded rows
        # Compute val realised Sharpe, annual_pnl, n_trades, MaxDD

    # Original §5.3 selection rule applies to (cell, q) pairs:
    # A0-equivalent pre-filter -> max val realised Sharpe -> tie-breakers

# After (cell*, q*) is selected on val, lock cutoff_q* and apply to test:
test_traded = (pred_test_for_cell_star >= cutoff_q_star)
# Test set is touched exactly once on this val-selected (cell*, q*, cutoff_q*) tuple.
```

The cutoff is a single scalar fit on validation. Applying it to test means "test rows with predicted EV ≥ val-fit cutoff are traded". This is strict-causal: the test cutoff is determined entirely by val predictions. No test prediction is consulted to set the cutoff.

---

## 5. Optional negative absolute thresholds (secondary; informational-only)

> *Negative absolute thresholds remain admissible as a **secondary, informational-only** family. They are NOT the formal verdict basis. The quantile family per §3 is the formal verdict basis.*

| Family | Candidates |
|---|---|
| Raw pip | `{-5, -3, -1, 0, +1}` |
| ATR-normalised | `{-0.5, -0.3, -0.1, 0.0, +0.1}` |

These provide an alternative diagnostic lens. The quantile family is primary for the four reasons in §3.1. The absolute family is reported in eval_report (§7 row 5) explicitly labelled "diagnostic-only secondary informational family; not used for verdict".

---

## 6. Cell + threshold selection (validation-only; binding inherited unchanged)

> *Original 26.0a-α §5.3 remains binding. The validation-only cell-and-threshold selection rule applies to the quantile family in rev1. The selection space is now 24 cells × 5 quantile candidates = 120 (cell, q) pairs.*

Priority order (unchanged from original §5.3):

1. **Pre-filter**: cells with `val_n_trades >= A0-equivalent` (under the candidate q's val cutoff) are eligible. If no candidate satisfies A0-equivalent, the LOW_VAL_TRADES flag is set and selection falls back to all valid candidates.
2. **Primary**: max validation realised Sharpe (via M1 path re-traverse on val_traded rows).
3. **Tie-breakers** (in order): max val annual_pnl → lower val MaxDD → simpler model class (LinearRegression > Ridge > LightGBM; deterministic final tie-breaker only, NOT a model preference).

Test set is touched exactly once on the val-selected (cell*, q*) pair with the val-fit cutoff_q*.

---

## 7. Eval report requirements (binding for rev1 26.0a-β)

The rev1 eval_report.md must present these sections (in addition to the inherited mandatory clauses, production-misuse guards, and split-dates blocks):

| # | Section | Purpose | Verdict-coupling |
|---|---|---|---|
| 1 | **All 24 × 5 = 120 (cell, quantile) sweep summary** (sorted by val realised Sharpe desc) | Primary verdict source | **Formal** |
| 2 | **Val-selected (cell*, q*)** with test 8-gate metrics (touched once) | Formal verdict source | **Formal** |
| 3 | Best by test Spearman | Ranking-signal diagnostic | Diagnostic-only |
| 4 | Best by test realised Sharpe | Realised-Sharpe ceiling diagnostic | Diagnostic-only |
| 5 | **Absolute-threshold family results across the 24 cells** using `{-5, -3, -1, 0, +1}` (raw pip) / `{-0.5, -0.3, -0.1, 0.0, +0.1}` (ATR) | Secondary informational family | Diagnostic-only |
| 6 | **Selected threshold family declaration** — explicit "the formal verdict basis is the quantile-family val-selected (cell, q) pair" | Verdict scoping | Verbatim |
| 7 | `val_n_trades` + `test_n_trades` for the selected pair | A0-eligibility sanity | Formal |
| 8 | **Whether ranking signal monetises in top predicted-EV buckets** narrative | Connects test Spearman to realised PnL across q candidates | Required text section |
| 9 | Aggregate H1-weak / H1-meaningful / H2 / H3 / H4 outcome | Hypothesis chain (inherited from original §6) | Formal |
| 10 | Verdict per original §7 verdict tree | H2 PASS alone still NOT ADOPT_CANDIDATE | Formal |

> Diagnostic-only sections (rows 3, 4, 5) MUST be labelled in the eval_report: *"diagnostic; not used for verdict"*.

---

## 8. What stays binding from the original 26.0a-α (NOT changed by rev1)

| Element | Source in original | Status in rev1 |
|---|---|---|
| L-3 label construction (D-1..D-6) | §3 + §3.1 | unchanged |
| Mid-to-mid base PnL; no double-counting | §3.1 | unchanged |
| 24-cell sweep grid | §4 | unchanged |
| LightGBM fixed conservative config | §4.1 | unchanged |
| Eval harness inheritance | §5 + §5.1 | unchanged (minimum feature set = `pair` + `direction` only) |
| Validation-only cell-and-threshold selection rule | §5.3 | unchanged (priority order, A0-equivalent prefilter, deterministic tie-breakers) |
| H1 two-tier hypothesis (weak ρ > 0.05; meaningful ρ ≥ 0.10) | §6 | unchanged |
| Verdict tree (incl. REJECT_WEAK_SIGNAL_ONLY band) | §7 | unchanged |
| H3 reference Sharpe = -0.192 | §6 | unchanged |
| Six mandatory clauses | §9 | unchanged |
| Strict-causal stance | §3.2 | unchanged |
| Realised PnL via M1 path re-traverse for 8-gate scoring | §5 | unchanged |
| Winsorisation scope (training y only; harness PnL never touched) | §3 D-6 | unchanged |
| Test set touched once on val-selected pair | §5.3 | unchanged (now applies to (cell, q) pair instead of (cell, abs-threshold)) |

---

## 9. What rev1 amends in the original 26.0a-α (single-axis change)

Only §5.2 and supporting unit-test / sign-off references:

| Element | Before (original 26.0a-α) | After (rev1) |
|---|---|---|
| §5.2 threshold candidates | `{0.0, 1.0, 2.0, 3.0, 4.0}` raw / `{0.0, 0.1, 0.2, 0.3, 0.4}` ATR | **Primary**: `{Q-5, Q-10, Q-20, Q-30, Q-40}` quantile-of-val. **Secondary informational**: negative absolute candidates per §5. |
| Threshold-fit rule | (implicit; absolute thresholds need no fit) | Validation-only cutoff fit (§4 binding); full-sample qcut PROHIBITED. |
| Cell-and-threshold selection space size | 24 cells × 5 absolute thresholds = 120 pairs | 24 cells × 5 quantile candidates = 120 pairs (size unchanged; semantics shifted to quantile cutoffs). |
| eval_report contrast section | (not required) | **Required** (§7 rows 5, 6, 8): absolute vs. quantile family side-by-side; selected family declaration; ranking-monetisation narrative. |
| §10 unit tests | 24 tests | 24 + 6 = 30 tests (six new tests per §10 below). |

---

## 10. New unit tests required for rev1 26.0a-β re-implementation

In addition to the 24 unit tests from the original 26.0a-α §10 (all of which remain required), the rev1 26.0a-β re-implementation must add:

| # | Test name | Purpose |
|---|---|---|
| 25 | `test_quantile_cutoff_fits_on_val_only` | Cutoff for top q% is fit on val predictions; perturbing test predictions does NOT change the cutoff |
| 26 | `test_quantile_cutoff_applied_to_test_uses_val_fit_value` | The exact val-fit cutoff scalar is applied to test (test rows traded iff `pred_test ≥ val_fit_cutoff`) |
| 27 | `test_no_full_sample_qcut_in_quantile_path` | The quantile path does NOT call `np.quantile`/`pd.qcut` on `train + val + test` combined or on test alone |
| 28 | `test_quantile_threshold_family_has_5_candidates` | `{5, 10, 20, 30, 40}` percent exactly |
| 29 | `test_negative_absolute_thresholds_secondary_informational` | Absolute-family results are computed and reported but the selection priority order (§6) does NOT consider them; only quantile-family pairs feed verdict selection |
| 30 | `test_selected_threshold_family_is_quantile` | The val-selected pair is a (cell, q) — `q ∈ {5, 10, 20, 30, 40}` — and is the formal verdict source |

**Total: 30 unit tests for the rev1 26.0a-β implementation.**

---

## 11. Mandatory clauses (verbatim, 6 total — inherited from PR #299 §7 / 26.0a-α §9 unchanged)

1. **Phase 26 framing** — *Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.*
2. **Diagnostic columns prohibition** — *Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.*
3. **γ closure preservation** — *Phase 24 γ hard-close (PR #279) is unmodified.*
4. **Production-readiness preservation** — *X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.*
5. **NG#10 / NG#11 not relaxed**.
6. **Phase 26 scope** — *Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed; primary research lever is label / target design, NOT feature class.*

---

## 12. Status of the in-progress 26.0a-β branch

| Item | Disposition |
|---|---|
| Local branch `research/phase26-0a-beta-l3-eval` | NOT pushed. Stays local as a working starting point for rev1 26.0a-β. |
| Local `scripts/stage26_0a_l3_eval.py` (~750 lines) | Most of it survives the rev1 redesign. Only the threshold-selection logic (currently using absolute candidates) needs revision. NOT pushed. |
| Local `tests/unit/test_stage26_0a_l3_eval.py` (27 tests) | Survives. The six new tests per §10 are additions, not replacements. NOT pushed. |
| Local `artifacts/stage26_0a/eval_report.md` (130 lines; NO_VALID_CELL verdict) | Diagnostic reference only. Will be regenerated under rev1 with the quantile family. NOT pushed. |
| Local `.gitignore` stanza for `artifacts/stage26_0a/` | Survives. NOT pushed (will be pushed as part of the rev1 26.0a-β PR). |

After rev1 merges, the rev1 26.0a-β PR opens a **new branch from the rev1-merged master**, brings in the local implementation as a starting point, revises the threshold-selection logic per §3 / §4, adds the six new unit tests per §10, runs a fresh sweep, and writes the rev1-conformant eval_report.

---

## 13. PR chain reference

```
Phase 26 begin:
  #299 (Phase 26 kickoff)
  → #300 (Phase 26 first-scope review — recommends L-3)
  → [user confirms L-3 + authorises 26.0a-α]
  → #301 (26.0a-α L-3 design memo — original; preserved unmodified)
  → [in-progress 26.0a-β implementation surfaces contract-spec gap]
  → THIS PR (26.0a-α-rev1 threshold-selection design revision)
  → [user authorises rev1 26.0a-β implementation]
  → rev1 26.0a-β L-3 eval (separate PR; binding contract = original #301 + THIS PR)
```

---

## 14. What this PR will NOT do

- ❌ Modify or delete the original 26.0a-α memo at `docs/design/phase26_0a_alpha_l3_design.md` (audit-trail discipline).
- ❌ Push or commit the in-progress 26.0a-β local branch (`research/phase26-0a-beta-l3-eval`).
- ❌ Push the local in-progress `scripts/stage26_0a_l3_eval.py` / `tests/unit/test_stage26_0a_l3_eval.py` / `artifacts/stage26_0a/eval_report.md`.
- ❌ Modify L-3 label construction (§3 / §3.1 of the original 26.0a-α binding).
- ❌ Change the 24-cell sweep grid (§4 of the original binding).
- ❌ Change the H1 two-tier thresholds (§6 of the original binding).
- ❌ Change the verdict tree (§7 of the original binding).
- ❌ Change K_FAV / K_ADV barrier geometry (inherited at 1.5 / 1.0).
- ❌ Modify γ closure (PR #279).
- ❌ Relax NG#10 / NG#11.
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md.
- ❌ Auto-route to rev1 26.0a-β implementation. The next PR opens only on the user's separate explicit authorisation.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 15. Sign-off / rev1 26.0a-β binding requirements

This memo is the binding addendum to the original 26.0a-α (PR #301). The rev1 26.0a-β implementation PR must:

- Inherit L-3 label construction strictly per the original 26.0a-α §3 / §3.1 (D-1..D-6 unchanged).
- Inherit the 24-cell sweep grid strictly per the original 26.0a-α §4.
- **Use the quantile threshold family per §3 of this rev1 as the formal verdict basis.**
- Apply the val-only quantile-fit rule per §4 strictly. No full-sample qcut. No test-prediction peeking.
- Report the absolute-threshold family as secondary informational per §5 / §7 row 5, explicitly labelled "diagnostic-only; not used for verdict".
- Implement the rev1 eval_report sections per §7 (10 rows).
- Apply the validation-only cell-and-threshold selection rule per §6 (binding inherited from original §5.3) to (cell, q) pairs.
- Test the four hypotheses per the original §6 (H1-weak / H1-meaningful / H2 / H3 / H4) on the val-selected (cell*, q*, cutoff_q*) test evaluation.
- Apply the verdict tree per the original §7 (H2 PASS alone is NOT ADOPT_CANDIDATE; REJECT_WEAK_SIGNAL_ONLY band preserved).
- Honour all six mandatory clauses per §11 verbatim in `eval_report.md`.
- Include all 30 unit tests (24 inherited + 6 new per §10).
- NOT relax NG#10 / NG#11; NOT modify γ closure; NOT touch stage25_0a/0b/0c/0d/0e/0f artifacts; NOT add new dependencies (LightGBM remains the only third-party regression model; if unavailable, the original 16-cell defer path applies).

This addendum PR stops here. The rev1 26.0a-β implementation PR opens only on the user's separate explicit authorisation.
