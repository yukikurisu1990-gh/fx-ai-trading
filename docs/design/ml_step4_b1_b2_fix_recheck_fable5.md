# Fable 5 re-check — PR #419 B-1/B-2 first-run source-blocker fixes

- **Document class:** doc-only adversarial re-check of the PR #419 fixes. Not an
  implementation PR; not an execution PR; changes no code.
- **Branch:** `docs/fable5-b1-b2-fix-recheck`
- **Base:** master `5c48764` (post PR #419 merge)
- **Re-checked against:** the PR #418 full source audit (blockers B-1/B-2 +
  mandatory test list), the body-level audit's executed proofs, and the
  PR #407/#408 contracts.
- **Method:** every fix re-verified **by execution on merged master** — a
  three-value cost-flow probe (+2.0 / +1.0 / −0.5 raw pips), a five-size B-2
  range probe (n = 20/21/22/100/300), a six-combination NaN/±inf acceptance
  probe, a full regression battery (fixture e2e ×2 for determinism, real-mode
  refusal, protected-dir refusal, notional-conflict fail-closed), plus source
  and import-graph inspection. Probes used synthetic inline values only.

## Audit status

**`ML_STEP4_B1_B2_FIXES_ACCEPTABLE_FOR_FIRST_RUN_EXECUTION_REVIEW`**

Also binding: `ML_STEP4_EXECUTION_NOT_PERFORMED` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Forbidden-label note: `PASS`, `Tier 1`, `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`,
`BYTE_ADMISSIBILITY_APPROVED`, `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`,
`PRODUCTION_READY` appear here only as prohibitions.

## 1. Executive verdict

**B-1 and B-2 are fixed, verified by execution; no PR #418 blocker remains; no
new blocker was introduced; zero regressions found.** The exact reproduction
cases that proved the blockers now produce the correct values, the mandatory
PR #418 test additions are all present and non-trivial, and the full fixture
rehearsal still runs deterministically with all guards intact. The source is
**acceptable for a separately-authorised first-run execution PR**, whose scope
is confirmed limited to exactly: checksum-verified `365d_BA` provider,
production v4 bulk feature wiring, minimal real-mode enablement, and the real
metadata-only evidence write.

## 2. Audit scope

`scripts/ml_step4/{body,labels,acceptance}.py` (the PR #419 diff),
`tests/ml_step4/test_b1_b2_fixes.py` (23 tests), the fix note, the PR #418
audit documents, the roadmap; dependent functions in
`metrics.py` / `simulator.py` / `thresholds.py` / `contract.py` /
`evidence.py` (unchanged by PR #419 — verified via the diff and re-probed).

## 3. B-1 cost-cell re-check — **FIXED**

Executed with three raw PnLs (+2.0 / +1.0 / −0.5 pips) through the real body
helpers on merged master:

| raw | exp@0.5 | 0.0-cell | 0.5-cell | 1.0-cell | single charge |
| --- | --- | --- | --- | --- | --- |
| +2.0 | **+1.50** | +2.00 | +1.50 | +1.00 | ✓ |
| +1.0 | **+0.50** | +1.00 | +0.50 | 0.00 | ✓ |
| −0.5 | **−1.00** | −0.50 | −1.00 | −1.50 | ✓ |

- Signal PnL is raw gross (`s.pnl_pips == raw` asserted in the probe);
  `cell_pips` is **gone from the signal-layer signature** (inspected).
- Spread remains embedded once by the label geometry (unchanged
  `traded_direction_pnl_pips` path); `MetricTrade.gross_pnl_pips` genuinely
  gross.
- The metrics layer applies the flat cell exactly once; **sensitivity cells
  are unshifted** (0.0-cell returns raw).
- Validation and holdout charge identically: source inspection confirms the
  validation series uses `daily_portfolio_pnl(trades, cell_pips)` and the old
  `(trades, 0.0)` call no longer exists anywhere in `body.py`.
- **Old double-charge behavior is impossible** through the body helpers
  (test-pinned: raw +1.0 → 0.5, not 0.0).
- Fixture evidence carries the explicit `cost_convention` block
  (`applied_exactly_once_by_metrics_layer`, `signal_pnl:
  raw_gross_of_flat_cell`, `double_charge: false`) — test-pinned.
- Acceptance still evaluates the intended cells: the primary bundle at 0.5 pip
  and the `cost_sensitivity.1.0pip` guard; **no PR #407/#408 criterion, value,
  or threshold-candidate changed** (probe: the 1.0-pip criterion constant is
  intact; the ACCEPTANCE_CRITERIA dict is untouched by the PR #419 diff).

## 4. B-2 label eligibility re-check — **FIXED**

Executed over n = 20, 21, 22, 100, 300 (horizon 20):

- last eligible index **= n − horizon − 2** wherever any bar is eligible
  (78 at n=100; 278 at n=300) — exactly the committed
  `range(n − horizon − 1)` convention;
- n = 20/21/22 label nothing (ATR-warmup dominates at tiny n; bound respected);
- no trailing decision bar lacking a full future horizon carries a label, PnL,
  or exit offset (test-pinned);
- horizon remains 20 (`contract.HORIZON_M1_BARS`, test-pinned); bid/ask
  geometry, SL-first tie, timeout MTM, and the F-2 traded-direction replay are
  untouched by the diff (only the skip condition changed:
  `i + horizon >= n` → `i + horizon + 1 >= n`);
- labels and trade-scoring eligibility remain consistent by construction (one
  `bulk_labels` output feeds both);
- **no new range convention was introduced** — this is pure alignment to the
  committed one; no contract text or hash changed for labels.

## 5. Regression re-check — **ZERO REGRESSIONS**

Re-executed on merged master: fixture e2e completes
(`ML_STEP4_FIXTURE_REHEARSAL_COMPLETED_NO_REAL_RUN`, 8 payloads) and is
**deterministic across two runs**; all real flags false; validation-only
threshold selection and holdout-after-selection order unchanged (source);
one-position-per-pair simulator unchanged (module not in the diff); daily
aggregation unchanged; **maxDD fixed-notional intact** (default 10,000;
conflicting caller value still fails closed — executed); missing/None
fail-closed intact (PR #412 tests still pass); diagnostics exclusion intact;
evidence scrub intact; **protected PR #409 evidence guard intact** (write
refused; directory still exactly 8 files, git-clean before/after probes);
real-mode refusal intact (executed). Full suite: **455 passed, 5 skipped**.

## 6. NaN / infinity handling — **FAIL-CLOSED**

Executed six combinations (NaN, +inf, −inf × two metric paths incl. a nested
one): **none produces MEETS** — every combination yields
`ML_STEP4_RUN_INVALID_PROVENANCE_MISSING` via
`acceptance.non_finite_required_metrics`, with the offending path recorded in
`missing_metrics` (clear provenance). The finite baseline still MEETS
(no over-tightening). Implementation is additive to the PR #412 B-3 machinery
and does not alter any criterion.

## 7. Legacy non-use / contamination re-check — **CLEAN**

Grep + AST re-verified on merged master: `scripts/ml_step4` imports exactly the
two sanctioned externals (F-2 helper; foundation_t2 scrub constants — the
trainer feature-builder module remains a lazy seam, not a top-level import);
no `compare_multipair`/backtest/optimistic-PnL/deployed-model route imported;
`models/lgbm` appears only inside the prohibition check in `contract.py`;
no joblib/pickle load anywhere in the package. PR #419 created **no new
route**; its import-graph test locks this in (and its AST helper was verified
in PR #419 to catch a planted legacy import).

## 8. ATR cross-check review — **SOUND**

The new test is genuinely numeric: it hand-computes the mid true-range series
(TR₀ = H−L; TRᵢ = max(H−L, |H−C₋₁|, |L−C₋₁|)) and asserts element-by-element
equality of `labels.atr14` with the SMA-14 of the last 14 TRs, plus `None` for
all warmup rows (i < 13 — fewer than `min_periods=14` TRs). This matches the
committed trainer convention (`tr.rolling(14, min_periods=14).mean()`)
verified line-by-line in the PR #418 audit. **No feature-contract change**:
`feature_config`/hashes untouched.

## 9. Test adequacy — **SUFFICIENT FOR THIS GATE**

All eleven required areas are covered by the 23 new tests (single-charge cost
× cells; validation/holdout consistency; range pinning + four boundary sizes;
adapter-failure stop; numeric ATR; import-graph; NaN/inf ×3; old-PnL non-use;
deployed-reuse impossibility; post-fix determinism), and none is merely
structural where a value assertion was required. **Remaining test obligations
belong to the execution PR** (unchanged from PR #418 §15): the
production-seam invocation test on synthetic production-shaped bars with a
truncation no-lookahead probe, and the checksum-verified provider test with a
tampered-fixture negative case. No additional pre-first-run test is required
beyond those.

## 10. Remaining first-run gaps — **CONFIRMED, EXECUTION-PR SCOPE**

Exactly four, unchanged: (1) checksum-verified `365d_BA` provider (immediate
PR-B.1 re-verification + bar-schema mapping + provider-identity/checksum
linkage in evidence); (2) production v4 bulk feature wiring (trainer builders
only — never main/save paths; `_FEATURE_COLS` into the manifest); (3) minimal
real-mode enablement; (4) the real metadata-only evidence write. **All four
are acceptable to handle in the separately-authorised first-run execution
PR** — no further code-only PR is required first.

## 11. Blockers

**None.**

## 12. Recommendation for next gate

**Acceptable for the separately-authorised first-run execution PR**, with
exactly this allowed shape: minimal real-mode enablement only;
checksum-verified `365d_BA` provider; production v4 bulk feature wiring; **no
contract changes; no threshold search; no feature search; no model-family
changes; no acceptance-criteria changes; execute exactly once; metadata-only
evidence; mandatory post-run human + ChatGPT review; recommended Fable 5
post-run adversarial audit** — all under the PR #413 falsification/baseline
frame (likely `DOES_NOT_MEET`; an honest negative closes the M1 flagship
question; no rerun-into-search).

## 13. Non-authorisation statements

This re-check did **not**: implement code or real-mode enablement; execute ML
Step 4; read real `365d_BA` raw data (probes used inline synthetic values);
train on real data; run a real backtest; evaluate the real holdout; generate
real ML metrics; create real execution evidence (guard probes refused; PR #409
dir verified 8 files, git-clean); write model binaries; access external disks,
Google Drive, or R2; start Phase C2; touch `730d_BA`/`3650d_BA`; claim
production readiness.
