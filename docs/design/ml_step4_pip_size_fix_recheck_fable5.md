# Fable 5 re-check — ML Step 4 INV-1 per-pair pip-size fix (PR #423)

- **Document class:** doc-only adversarial re-check (verifies a merged code fix;
  executes nothing). Not a rerun, not a corrected second first-run, not a
  training / holdout-evaluation PR, not H2/H3, not Phase C2.
- **Branch:** `docs/fable5-pip-size-fix-recheck`
- **Base:** master `3e3b22ff87074314dc17b48c773e64b415db0016` (post PR #423 merge).
- **Audited change:** PR #423 squash commit `3e3b22f` (6 files:
  `scripts/ml_step4/{data_adapter,body,manifest}.py`,
  `tests/ml_step4/test_pip_size.py`, fix note, roadmap pointer).
- **Method:** source reading on master + static metadata-only verification of
  the committed PR-B.1 inventory JSON (filenames only) + local test/lint runs.
  **No real raw data was read; no model was trained; no holdout was evaluated;
  no new real metrics were generated; no execution evidence was created.**

## Status

**`ML_STEP4_PIP_SIZE_FIX_ACCEPTABLE_FOR_CORRECTED_FIRST_RUN_DECISION`**

Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`**.

Forbidden-label note: this document does not assert `PASS`, `Tier 1`,
`FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `BYTE_ADMISSIBILITY_APPROVED`,
`NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; those tokens
appear only in this prohibition list.

---

## 1. Executive verdict

- **Is INV-1 fixed?** Yes. The fixed-global pip conversion is gone from every
  scoring path; per-pair conversion matches the committed research convention.
- **Is the fixed-global-pip-size bug eliminated?** Yes. `body.py` contains zero
  references to the fixed global; a source-guard test enforces this. The
  surviving `data_adapter.PIP_SIZE` is documented and used only as the fixture
  synthetic-price *generation* scale (candle amplitude/spread), never for pip
  conversion.
- **Is per-pair pip size now the single authority for label/scoring PnL
  conversion?** Yes — structurally. The ONLY price→pips division in the entire
  `scripts/ml_step4` package is `labels.traded_direction_pnl_pips`
  (`pnl_price / pip_size`), and its sole bulk entry point `bulk_labels` receives
  `pip_size` from `data_adapter.pip_size_for` at both call sites. Everything
  downstream (signals, simulator, metrics, evidence) operates on
  already-converted pips; grep confirms no second conversion site exists in
  `metrics.py`, `simulator.py`, `executor.py`, `execute_365d_ba.py`,
  `evidence.py`, `acceptance.py`, or `contract.py`.
- **Did PR #423 introduce any new blocker?** No. The diff touched exactly the
  six declared files; `labels.py`, `metrics.py`, `contract.py`,
  `acceptance.py`, `simulator.py`, `evidence.py`, and `execute_365d_ba.py` are
  byte-untouched, so the B-1 / B-2 / threshold / refusal machinery is
  structurally unchanged (and regression-tested).
- **Is the code acceptable for a governance decision on corrected second
  first-run admissibility?** Yes.
- **Remaining technical blockers before such a governance decision?** None.
  Three non-blocking residual observations are recorded in §9.

## 2. Audit scope

Reviewed on master `3e3b22f`: `scripts/ml_step4/data_adapter.py`, `body.py`,
`manifest.py`, `labels.py`, `metrics.py`, `evidence.py`, `execute_365d_ba.py`,
`contract.py`, `acceptance.py`, `simulator.py` (grep-level),
`tests/ml_step4/test_pip_size.py` (26 tests),
`docs/design/ml_step4_pip_size_fix_note.md`,
`docs/design/ml_step4_365d_ba_first_run_post_audit_fable5.md`, and the roadmap.
Static metadata check: the committed PR-B.1 inventory JSON (filenames only).

## 3. Per-pair pip-size authority — CONFIRMED

- `data_adapter.pip_size_for(pair)` is the single authority. Its two branches
  are the named constants `_PIP_JPY = 0.01` / `_PIP_NON_JPY = 0.0001`;
  behaviour is exactly `0.01 if pair.endswith("_JPY") else 0.0001`, and a
  parity test imports `scripts.compare_multipair_v9_orthogonal._pip_size` and
  asserts equality over 6 JPY + 3 non-JPY pairs (the research module is
  referenced by the test only — no unsafe runtime dependency).
- `body.py` **no longer imports or uses a fixed global pip size**
  (source-guard-tested: `"PIP_SIZE" not in body.py`).
- **Resolved before training:** `pip_size_by_pair = pip_size_map(provider.pairs)`
  executes at the top of `run_first_run_365d_ba`, before the per-pair loop and
  therefore before any `train_lgbm` call. A missing pip size aborts the run
  with nothing trained.
- **Fail-closed behaviour verified in source + tests:** missing/empty/
  non-string pair → `PipSizeError`; empty map → `PipSizeError`; duplicate pair
  → `PipSizeError`; non-positive resolved size → `PipSizeError` (defence in
  depth; the two constants are positive); `bulk_labels` independently rejects
  `pip_size <= 0` (`LabelContractError`); `build_run_manifest` rejects an
  empty or non-positive supplied map (`ManifestError`).
- **Unknown-pair behaviour:** a non-empty token not ending `_JPY` is handled
  conservatively as non-JPY `0.0001` — the committed convention's `else`
  branch — and this is documented in the docstring and pinned by a test.
  Residual risk and its mitigation are recorded as O-2 (§9); not a blocker for
  this epoch (see the static inventory verification in §3a).
- **No universal fixed pip size remains reachable for real execution.** The
  real path (`run_first_run_365d_ba`) has no access to a global constant; the
  only remaining `PIP_SIZE` uses are the four fixture price-generation lines in
  `FixtureDataProvider.bars_for`, which never convert PnL.

### 3a. Static inventory verification (metadata-only)

The real provider derives pair names from committed inventory filenames via
`_pair_name` (`candles_<PAIR>_M1_365d_BA.jsonl` → `<PAIR>`). Re-running that
exact parse over the committed PR-B.1 inventory JSON (filenames only — no raw
data): **20 files → 20 distinct well-formed `XXX_YYY` pairs; zero malformed
tokens; exactly six `_JPY` crosses** (`AUD_JPY, CHF_JPY, EUR_JPY, GBP_JPY,
NZD_JPY, USD_JPY`). So for the frozen `365d_BA` epoch, JPY detection is exact
and the conservative unknown-pair fallback is unreachable; the epoch's file set
cannot drift without failing the pre-consumption checksum gate.

## 4. Label / scoring consistency — CONFIRMED

- **Both** `bulk_labels` call sites route through the authority: the fixture
  rehearsal (`pip_size=pip_size_for(pair)`, body.py:183) and the real first-run
  path (`pip_size=pip` from the pre-resolved map, body.py:476–482). There is no
  third call site.
- Inside `bulk_labels`, ONE `pip_size` argument is threaded into
  `traded_direction_pnl_pips` for **both** directions, so label PnL, trade
  scoring, TP/SL barrier-distance conversion, and timeout mark-to-market all
  use the identical per-pair value — cross-layer inconsistency is structurally
  impossible, not merely tested-for.
- TP/SL distances are computed in **price units** from ATR14 and converted to
  pips only at the single division; correct for JPY and non-JPY alike.
- **Label class and exit offsets are pip-agnostic** (barrier geometry is
  price-unit / index-based). A test pins that classes + offsets are identical
  across pip scales while PnL scales exactly 100× — matching the PR #422
  finding that labels/training were unaffected and only PnL magnitude was
  corrupted.
- **B-1 intact:** `MetricTrade.gross_pnl_pips` stays raw gross; the flat cost
  cell is subtracted exactly once by `metrics.net_pnl` at metric time
  (`metrics.py` untouched by #423; comment + tests preserved).
- **B-2 intact:** eligibility `i + horizon + 1 >= n` (last eligible
  `n − horizon − 2`) unchanged in `labels.py` (untouched) and re-pinned across
  pip scales by a new test.
- **Validation/holdout cost convention unchanged:** both are scored through the
  same `_real_signals` → simulator → metrics path; threshold selection remains
  validation-only (`select_threshold` untouched).

No inconsistent pip usage found → not blocked.

## 5. Mixed-scale tests — CONFIRMED SUFFICIENT

`tests/ml_step4/test_pip_size.py` (26 tests, all passing):

- JPY-like + non-JPY pairs are both covered (mapping tests over 6 JPY + 3
  non-JPY names; end-to-end over `USD_JPY` + `EUR_USD`).
- **Value-pinned, not structural:** the same raw 0.10 price move is asserted to
  convert to exactly **10 pips** at 0.01 vs **1000 pips** at 0.0001
  (`pytest.approx` on concrete numbers), and the old fixed-global-0.0001
  behaviour is explicitly reproduced and shown to equal 100× the correct JPY
  value — i.e. the test encodes the precise PR #421 failure and asserts the
  fixed path diverges from it. Non-JPY output is asserted **equal** to the old
  path (behaviour unchanged).
- The bulk consistency test asserts per-record `pnl == pnl_at_0.0001 / 100`
  across a full `bulk_labels` run at both scales (TP/SL and timeout records
  alike).
- **Mixed-scale end-to-end** (tiny synthetic BA files through the REAL body
  path with LightGBM): asserts the run manifest AND the leakage/provenance
  report record `{"EUR_USD": 0.0001, "USD_JPY": 0.01}` with
  `global_pip_size_authoritative_for_all_pairs = false`, and per-pair
  diagnostics carry `pip_size` + `pip_size_kind` (`jpy_cross` / `non_jpy`);
  all payloads scrub-clean.
- **Would these tests have caught PR #421's bug?** Yes, three independent ways:
  (a) the source guard fails on any `PIP_SIZE` reference in `body.py`; (b) the
  end-to-end test fails because the old code recorded no per-pair mapping;
  (c) the value-pinned JPY assertions fail under any 100× mis-scale.

Coverage is sufficient → not blocked.

## 6. Evidence / manifest metadata — CONFIRMED

- The run manifest records `pip_size_by_pair`, `pip_size_convention`
  (`"0.01 if pair endswith _JPY else 0.0001"`), and
  `global_pip_size_authoritative_for_all_pairs = false`.
- The leakage/provenance report records the same three fields.
- Per-pair diagnostics carry `pip_size` + `pip_size_kind`.
- A supplied-but-invalid map (empty / non-positive) fails closed
  (`ManifestError`); scrub (`evidence.assert_clean`) passes on all payloads in
  the end-to-end test.
- **Could future evidence hide the mapping?** The only real execution path
  (`run_first_run_365d_ba`) unconditionally supplies the map to the manifest
  and writes it into the provenance report, and the end-to-end test pins its
  presence in both. The manifest *field* is optional at the
  `build_run_manifest` signature level (O-1, §9) — a hardening opportunity,
  not a reachable hiding path today → not blocked.
- **PR #421 invalid evidence not modified; PR #409 stop evidence not modified;
  no corrected execution evidence created** — the #423 diff contains no
  `artifacts/` path, and both evidence trees' last-touching commit remains
  `7a3e1e2` (#421).

## 7. Regression audit — NO REGRESSION FOUND

| Item | Finding |
| --- | --- |
| B-1 single cost-cell | intact (`metrics.py` untouched; gross-PnL comment + tests preserved) |
| B-2 eligibility range | intact (`labels.py` untouched; re-pinned across pip scales) |
| validation/holdout cost convention | unchanged (same signal→metrics path both windows) |
| threshold selection | validation-only, unchanged (`thresholds.py` untouched) |
| real-mode refusal | intact (bare CLI and `--execute` refuse; regression-tested) |
| rerun / training / holdout eval | none performed (code-only PR; this re-check is doc-only) |
| new corrected metrics / execution evidence | none created |
| raw data access | none (static filename metadata from the committed inventory JSON only) |
| epoch / feature / label / model / threshold / acceptance / split contracts | untouched (`contract.py`, `acceptance.py`, `split.py` not in the diff) |

## 8. Governance note

**This re-check does not authorise a corrected second first-run attempt.** It
answers only the technical question: the INV-1 fix is genuine, single-sourced,
fail-closed, evidence-recorded, and pinned by tests that would have caught the
original bug. The code is **acceptable input for the human + ChatGPT governance
decision** on corrected second first-run admissibility.

For that decision, the record is:

- **PR #421 was invalid, not a valid negative result** — its `DOES_NOT_MEET`
  must not be cited as negative evidence; the M1 flagship first-run question is
  still open.
- **No tuning or feedback loop occurred**: the invalid metrics never informed
  any threshold/feature/model/acceptance change; PR #423 changed only the unit
  conversion and its provenance recording. The frozen holdout was evaluated
  once, under a wrong unit, and nothing was fitted to it.
- **Same-holdout corrected re-measurement may therefore be defensible** (it is
  a re-measurement of an unread quantity, not a second draw), **but that is a
  governance call and must be explicitly authorised — it is not authorised
  here.**
- **Alternative:** close M1 on the archived honest evidence (the correctly
  scaled non-JPY portion of the invalid run, ≈−3.5 net pips/trade, already sits
  in the archived honest M1 band) without ever producing a valid first-run
  number.
- **No H2/H3 and no roadmap pivot should start until this governance decision
  is made.**
- **If a corrected second first-run is later authorised, it must use the same
  unchanged contract** — epoch, features (v4 base 39), labels, horizon, SL-first
  tie, timeout MTM, model family/params, threshold candidates/tie rule, split
  policy, acceptance criteria — with the pip-size bug fix as the sole delta.

## 9. Blockers / residual observations

**Blockers: NONE.**

Non-blocking residual observations (recorded for completeness):

- **O-1 (hardening):** `pip_size_by_pair` is optional in
  `build_run_manifest` and absent from `REQUIRED_MANIFEST_FIELDS`, so a
  *hypothetical future* real-mode caller that forgot to pass it would not fail
  closed at the manifest layer. Unreachable today: the sole real path supplies
  it unconditionally and an end-to-end test pins its presence in manifest AND
  provenance evidence. Optional hardening for a future code PR: require the
  field whenever `mode` starts with `real`.
- **O-2 (scope of the conservative fallback):** an unknown pair token silently
  resolves to `0.0001`; a mis-parsed JPY filename would therefore re-create the
  bug. Mitigated for the frozen epoch by §3a (all 20 committed filenames parse
  to well-formed pairs; exactly 6 `_JPY`; the file set is checksum-locked). Any
  **future epoch** must re-run the §3a static check as part of its own gate.
- **O-3 (out of scope):** the flat cost cell (0.0/0.5/1.0 pips) remains uniform
  across pairs. That is the frozen PR #407 contract's design (a flat pips
  cell), not an INV-1 defect; it was applied identically before and after the
  fix and is unchanged by #423.

## 10. Recommendation

1. Merge this re-check (records the technical acceptability finding).
2. Proceed to the **human + ChatGPT governance decision** on whether a
   corrected second first-run attempt is admissible (including explicitly
   ruling on same-holdout re-measurement) **or** whether M1 closes on archived
   honest evidence. Nothing runs until that decision.
3. If authorised, the corrected attempt is run-only on the unchanged contract
   (pip fix as sole delta), one shot, with the same evidence/scrub/one-shot
   discipline as PR #421 and a mandated post-run audit.
4. O-1's manifest hardening may ride along in any future authorised code PR;
   it is not required before the governance decision.

## 11. Non-authorisation statements

This document does **not**: authorise or perform a corrected second first-run
attempt; rerun ML Step 4; train models; evaluate holdout; generate new real
metrics; create or modify execution evidence; start H2/H3; start Phase C2; use
`730d_BA` or `3650d_BA`; change any contract; access Google Drive or R2; or
claim production readiness. PR #421 invalid evidence and PR #409 stop evidence
are untouched. `PRODUCTION_READINESS_NOT_CLAIMED` remains binding.
