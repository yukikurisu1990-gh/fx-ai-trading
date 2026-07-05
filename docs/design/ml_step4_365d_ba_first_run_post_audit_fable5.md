# Fable 5 post-run audit — ML Step 4 `365d_BA` first run (PR #421)

- **Document class:** doc-only adversarial post-run audit of the first-run
  evidence. Not a rerun; not a fix; not a new experiment. Changes no code;
  executes nothing; generates no new metrics (every number below is read from
  committed evidence or committed source).
- **Branch:** `docs/fable5-ml-step4-first-run-post-audit`
- **Base:** master `7a3e1e2` (post PR #421 merge)
- **Audited evidence:** `artifacts/ml_step4/365d_ba_v1/first_run_181dc52f3a08/`
  (8 payloads), `docs/design/ml_step4_365d_ba_first_run_execution_report.md`,
  the PR #421 implementation diff, and the pre-execution gate docs
  (PR #407/#408/#418/#419/#420).

## Audit status

**`ML_STEP4_365D_BA_FIRST_RUN_EVIDENCE_INVALID`**

Always binding: `PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## 1. Executive verdict

**The run was procedurally clean — executed exactly once, no rerun, no tuning,
holdout evaluated once, provenance complete — but its decision metrics are
INVALID due to a proven implementation bug: a fixed `PIP_SIZE = 0.0001` was
applied to all 20 pairs, misconverting the six JPY crosses (pip = 0.01) by
100×.** The proof comes from the committed evidence itself: per-pair
contribution shows JPY crosses at **−167…−577 "pips"/trade (mean −358.78)**
vs non-JPY at **−1.07…−8.14 (mean −3.18)** — a **112.8× magnitude ratio**
matching the 100× pip-scale factor — with **JPY crosses carrying 98.4% of the
total loss (CHF_JPY alone 91.5%)**. The extreme headline numbers (expectancy
−127.75, Sharpe −13.69, maxDD 103×) are artifacts of this scaling, not
measurements. The `DOES_NOT_MEET` conclusion therefore **cannot be accepted as
valid negative evidence**; the M1 flagship first-run question is **NOT closed**
by this run. Strikingly, the correctly-scaled portion of the run (the 14
non-JPY pairs: 5,515 trades, ≈ −3.0 gross / −3.5 net pips/trade) lands exactly
in the archived honest M1 rejection band (−1…−3 pips), which corroborates both
the bug diagnosis and — informally, non-decisionally — the expectation that a
corrected measurement would still be negative. **No rerun occurs in this
audit; whether the invalidation permits a new first-run attempt is a human +
ChatGPT decision (§13).**

## 2. Audit scope

The 8 committed evidence payloads; the execution report; the PR #421
implementation diff (data_adapter/features/body/execute_365d_ba/inventory/
labels + tests); recorded SHAs (execution `181dc52f3a08…`, PR head
`6b811f79…`, merged master `7a3e1e2d…`); the PR #407/#408 contracts and the
PR #418/#419/#420 audit chain; the committed research pip convention
(`compare_multipair_v9_orthogonal._pip_size`).

## 3. One-shot discipline — **CLEAN**

Exact command `python -m scripts.ml_step4.execute_365d_ba
--execute-first-run-365d-ba`, preceded by `--first-run-preflight`. Executed
exactly once (single background invocation; single evidence directory; the
run summary and manifest record `rerun_performed: false`,
`holdout_evaluated_count: 1`). No rerun, no post-result tuning, no
threshold/feature/model/acceptance change after results, no H2/H3, no
Phase C2, no new experiment. The one-shot discipline held — including after
the extreme result was seen (the §18 observation was recorded, not patched).

## 4. Provenance and evidence integrity — **CLEAN**

Execution code SHA `181dc52f3a08fa350420450cb51a3571ef150ac3` (manifest +
directory name); PR head `6b811f79dab239dc1f9d4837b201d9f6071145ff`; merged
master `7a3e1e2d5822519f01e091e289948495c0537e28`. Exactly 8 metadata-only
payloads; scrub-clean (re-verified in this audit against the ml_step4
scrubber); no raw rows / raw files / model binaries / personal paths / env
dumps / credentials / Drive / R2 anywhere in the evidence; PR #409 stop
evidence untouched and coexisting (8 parent-dir files intact). Manifest
carries seeds (honestly `not_set__trainer_convention_defines_none`), package
versions, all four hashes (`config 4b9a5970…`, `model bc27cf…` unchanged from
PR #412, `feature bff146…`, `threshold fd6877…`), label + feature identity,
and non-authorisation flags.

## 5. Inventory verification — **CLEAN**

Provider `scripts.ml_step4.data_adapter.Real365dBaProvider.v1`; expected =
observed **20 files**; expected = observed **1,481,715,517 bytes**;
`all_match = true`; per-file SHA-256 + size re-verified immediately before
consumption (gate 5 of 12, all PASS); `pair_frame` structurally requires
`verify()` first, so no partial training before verification was possible; no
extra/unknown dataset (the provider can only resolve inventory filenames).

## 6. Contract compliance — **compliant EXCEPT the pips unit semantics**

Epoch unchanged; common window `2025-04-25T17:09:00Z → 2026-04-24T20:58:00Z`
(== §5 bounds, derived from inventory metadata); 70/15/15 with purge 21,
holdout final 15%; v4 base only, 39 columns, no MTF group,
`_add_mtf_features` never called; label route `scripts.ml_step4.labels.v1`
(B-2, SL-first, timeout MTM, F-2 replay, horizon 20); LightGBM 3-class from
scratch, params `{lr 0.05, num_leaves 31, verbose −1, n_estimators 200}`, no
reuse, no binary; candidates `{0.35, 0.40, 0.45}` validation-only; acceptance
criteria unchanged; no search of any kind. **The single deviation is an
implementation defect against the contract's unit semantics:** PR #407 §4
pins evaluation PnL as **pips** (`pips_post_cost`), and the committed research
convention converts per pair (`_pip_size = 0.01 if _JPY else 0.0001` —
`compare_multipair_v9_orthogonal.py:103`), but the run body passed a fixed
`PIP_SIZE = 0.0001` to `labels.bulk_labels` for every pair
(`data_adapter.py:19`, `body.py` real path). This is not a contract *change*;
it is a defect that invalidates the run's metrics (§8).

## 7. Feature / label / prediction alignment — **CLEAN**

39 v4-base columns used (manifest `feature_binding.n_features = 39`,
`mtf_excluded: true`); no old feature script (import graph unchanged); labels
and all trade scoring through `labels.py`; predictions generated only for
validation/holdout eligible rows; threshold selected before any holdout
signal was built; holdout evaluated once. **Class-direction inversion ruled
out by source:** training encodes {−1,0,1}→{0,1,2}; `_prob_short_long`
resolves indices via `model.classes_` (recorded `[0,1,2]` for all 20 pairs);
short=class 0, long=class 2 — mapping consistent end-to-end. Corroborating:
the non-JPY per-trade outcome matches the honest archived band rather than an
inverted (worse-than-random) pattern.

## 8. PnL / pip / cost sanity audit — **BUG PROVEN (pip-unit)**

- **Long/short mapping:** correct (§7). **Bid/ask signs:** correct (unchanged
  audited geometry). **Cost cell:** applied exactly once — cells 0.0/0.5/1.0 =
  −127.25/−127.75/−128.25, exactly 0.5-pip steps, unshifted (PR #418 B-1 fix
  intact).
- **Pip conversion: WRONG for JPY crosses.** `bulk_labels` divides price-unit
  PnL by a caller-supplied `pip_size`; the body supplied 0.0001 for all pairs;
  the six JPY crosses (USD/EUR/GBP/AUD/NZD/CHF_JPY; pip = 0.01) are therefore
  reported at **100× their true pip magnitude**. Committed-evidence proof:
  per-pair per-trade PnL (pair_contribution diagnostic) — JPY mean −358.78 vs
  non-JPY mean −3.18 (ratio 112.8, i.e. ~100× scale × JPY crosses' somewhat
  larger price-unit ATR); JPY share of total loss 98.4%; CHF_JPY alone 91.5%
  (2,332 trades × −405.1).
- **Internal consistency:** Σ per-pair PnL = −1,032,499 over 8,082 trades →
  mean −127.75, matching the reported expectancy exactly; maxDD 103.25× ×
  10,000 = 1,032,500 pips ≈ the cumulative loss (drawdown ≈ monotone loss) —
  the numbers are internally coherent *given the wrong scale*.
- **Plausibility:** −127.75 pips/trade is **not** numerically plausible under
  a correct pip convention for M1 barrier trades (TP 1.5×ATR ≈ 1–3 real pips);
  it is exactly what a 100× JPY misscale produces. The scale-free quantities
  (win rate 7.8%, turnover 168/day, trade counts) are unaffected by the bug
  and consistent with a no-skill classifier at threshold 0.45 — informative
  context, but non-decisional inside an invalid run.
- **Verdict per the decision rule:** a pip-unit bug is proven → **evidence
  INVALID**. Additional contamination: the validation threshold-selection
  channel used the same mis-scaled PnL, so even the threshold choice cannot be
  certified (all three candidates were negative in either scale, but the
  selection is formally tainted).

## 9. Metrics / acceptance audit — **arithmetically correct on invalid inputs**

Selected 0.45; rejected 0.35 (val Sharpe −14.26, n=9,475) and 0.40 (−13.41,
n=7,209) — recorded as required. Holdout once; 8,082 trades / 48 UTC days.
Reported metrics match the evidence exactly (expectancy −127.75; Sharpe
−13.69; maxDD 103.25×; turnover 168.4; concentrations 0.289 / 0.550; 1.0-pip
−128.25; win rate 7.8%); 6/7 gating criteria fail; the evaluator emitted the
closed-vocabulary `DOES_NOT_MEET`; no diagnostic influenced acceptance; no
unregistered metric softened anything. The acceptance *machinery* worked
correctly — on inputs invalidated upstream by §8.

## 10. Extreme negative magnitude investigation

Classification: **`EXTREME_NEGATIVE_INVALID_IMPLEMENTATION_BUG`** (proven).

- −127.75 pips/trade: implausible under correct pips; exact under 100× JPY
  misscale (§8 decomposition).
- 7.8% win rate: scale-free; plausible for fired trades under B-2 raw-PnL
  accounting (wins ≈ TP hits + positive-drift timeouts; ask-entry/bid-exit
  makes typical timeouts slightly negative) with a no-skill classifier.
- Sharpe −13.69: consistent with a daily series whose drift and volatility are
  both dominated by 100×-scaled JPY losses.
- maxDD 103.25×: equals the cumulative loss — consistent.
- Losses concentrated: yes — 98.4% JPY; 91.5% CHF_JPY alone; the pair-level
  evidence was sufficient to prove the cause.
- Long/short swap: ruled out (§7). Raw-price-vs-pips mixing: ruled out for
  non-JPY (band-consistent); the defect is specifically the fixed pip size.
  Timeout-MTM alignment: no defect found (audited geometry unchanged).
- Requires: **code invalidation** (this verdict) — not merely future research
  diagnosis, and **not a rerun as remedy** within this audit.

## 11. Interpretation audit

- This is **not** production-ready (and claims none).
- This does **not** justify a rerun inside this audit, nor tuning, nor any
  threshold/feature/model search on this epoch.
- Because the evidence is **invalid**, the `DOES_NOT_MEET` result must NOT be
  cited as valid negative evidence, and the M1 flagship first-run question is
  **NOT closed** — it remains unanswered at the level of pre-registered
  evidence.
- Non-decisional observation (for the human review only): the correctly-scaled
  non-JPY portion (−3.0 gross / ≈−3.5 net pips/trade across 5,515 trades)
  matches the archived honest M1 rejection band, and the scale-free
  diagnostics look no-skill — consistent with the PR #413 prior that a valid
  measurement would likely also be `DOES_NOT_MEET`. This observation carries
  no evidentiary weight.
- The PR #413 pivot (M15/H1/H4, cost-hurdle targets, empirical spread) should
  proceed only from a decision-grade record: either a corrected, separately
  authorised first-run attempt, or an explicit human decision to close M1 on
  the strength of the archived honest evidence without a rerun.
- No next experiment starts inside this PR.

## 12. Blockers / invalidators

**INV-1 (proven): fixed pip size.** `data_adapter.PIP_SIZE = 0.0001` passed to
`labels.bulk_labels` for all pairs; JPY crosses require 0.01. Invalidates
expectancy, Sharpe, maxDD, pair-PnL concentration, cost-cell interplay, and
the validation-selection channel. Root cause of escape: every fixture, probe,
and test in PRs #417–#420 used 0.0001-scale synthetic prices only — **no
mixed-pip-scale (JPY-like) pair ever entered a test**. Test-adequacy lesson:
any future attempt must add a mixed-scale value-pinned fixture (a JPY-like
pair alongside a standard pair) proving per-pair pip conversion.

## 13. Recommendation

**Evidence invalid; do not interpret the result; a source-fix decision is
required.** Specifically:

1. Merge this post-run audit (records the invalidation).
2. **No rerun now.** Whether the invalidation permits a **new first-run
   attempt** is a human + ChatGPT decision. Material for that decision:
   (a) the fix is small and unambiguous — per-pair pip size
   (`0.01 if pair.endswith("_JPY") else 0.0001`, exactly the committed
   `_pip_size` convention) supplied to `bulk_labels` per pair, plus the
   mixed-scale test of §12; (b) labels/training were NOT affected by the bug
   (barrier geometry is in price units), but the frozen holdout has now been
   traversed once by this invalid run — the decision must explicitly address
   re-run admissibility on the same holdout (the model saw no feedback loop —
   no tuning occurred — so a corrected re-measurement is defensible, but that
   is a governance call, not this audit's); (c) the alternative is closing M1
   on the archived honest evidence without a valid first-run number.
3. If a new attempt is authorised: code-only pip fix PR (+ mixed-scale tests)
   → short Fable 5 re-check → a separately authorised second first-run
   attempt under the same unchanged contract.
4. No tuning; no H2/H3 or roadmap pivot until the M1 record is settled by the
   human + ChatGPT review.

## 14. Non-authorisation statements

This audit did **not**: rerun or execute ML Step 4; train any model; evaluate
any holdout; generate new metrics (all numbers are read from committed
evidence/source); read raw data (only committed evidence metadata); start any
experiment, H2/H3, or Phase C2; touch `730d_BA`/`3650d_BA`; access Google
Drive or R2; modify prior evidence; or claim production readiness.
