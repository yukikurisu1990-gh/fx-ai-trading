# ML Step 4 — INV-1 per-pair pip-size fix (code-only, NO RUN)

- **Document class:** code-fix note (records a source correction; executes
  nothing). Doc companion to a code-only PR.
- **Branch:** `fix/ml-step4-per-pair-pip-size`
- **Base:** master after PR #422 merge.
- **Implementation status:** `ML_STEP4_PIP_SIZE_INVALIDATOR_FIXED_NO_RUN`
- **Always binding:** `PRODUCTION_READINESS_NOT_CLAIMED`
- **Forbidden-label note:** this document does not assert `PASS`, `Tier 1`,
  `FORMALLY_VERIFIED`, `BYTE_ADMISSIBLE`, `BYTE_ADMISSIBILITY_APPROVED`,
  `NEW_EPOCH_ADOPTED`, `ML_STEP4_AUTHORISED`, or `PRODUCTION_READY`; where such
  tokens appear they are listed solely as prohibited outputs.

## 1. What was broken (INV-1)

The PR #422 Fable 5 post-run audit proved the PR #421 first-run decision metrics
`INVALID`: a **fixed `PIP_SIZE = 0.0001` was applied to all 20 pairs** for pip
conversion. The six JPY-quote crosses (whose pip is `0.01`) were therefore
converted at 100× their true pip magnitude (JPY per-trade mean −358.78 vs
non-JPY −3.18; JPY = 98.4% of total loss). The `DOES_NOT_MEET` result must not
be cited as valid negative evidence, and the M1 flagship first-run question is
not closed.

## 2. The fix (single per-pair authority)

- New authority `scripts/ml_step4/data_adapter.py :: pip_size_for(pair)` returns
  `0.01` for instruments ending `_JPY`, `0.0001` otherwise — matching the
  committed research convention
  `scripts.compare_multipair_v9_orthogonal._pip_size`. It **fails closed**
  (`PipSizeError`) on a missing / empty / non-string pair; non-JPY tokens are
  handled conservatively at `0.0001` (the convention's `else` branch).
- `pip_size_map(pairs)` builds `{pair: pip_size_for(pair)}` **once per real
  run**, failing closed on empty / duplicate / non-positive, so every downstream
  consumer reads the same per-pair value from one source (structurally
  preventing cross-layer inconsistency).
- `scripts/ml_step4/body.py` no longer imports or uses the fixed-global
  `PIP_SIZE`. Both `bulk_labels` call sites (the fixture rehearsal path and the
  real first-run path) now pass the per-pair pip size. In the real path the map
  is resolved **before any training** (fail-closed) and read per pair inside the
  loop.
- Because `bulk_labels` threads one `pip_size` argument into
  `traded_direction_pnl_pips` for both directions, the correct per-pair value
  reaches **label PnL, trade scoring, TP/SL distances, and timeout
  mark-to-market** identically. The label *class* and exit offsets are
  price-unit / index-based and therefore pip-agnostic — labels and training are
  unaffected; only PnL magnitude is corrected, exactly as the audit predicted.
- `PIP_SIZE` survives in `data_adapter.py` **only** as the fixture
  synthetic-price generation scale (spread / candle amplitude), explicitly
  documented as *not* a pip-conversion authority.

## 3. Evidence / manifest metadata

The real-run manifest and the leakage/provenance evidence now record the
per-pair `pip_size_by_pair` mapping, a `pip_size_convention` string, and an
explicit `global_pip_size_authoritative_for_all_pairs = false` flag. Each
per-pair diagnostic summary carries its `pip_size` and `pip_size_kind`
(`jpy_cross` / `non_jpy`). `manifest.build_run_manifest` fails closed if a
supplied mapping is empty or contains a non-positive pip size.

## 4. Tests (proving the bug cannot recur)

`tests/ml_step4/test_pip_size.py` adds: the per-pair mapping (six `_JPY` → 0.01,
non-JPY → 0.0001) and parity with the research convention; a **mixed-scale
value-pinned** check (same raw 0.10 move → 10 pips at 0.01 vs 1000 pips at
0.0001; the old global-0.0001 path is shown to 100×-misscale a JPY pair);
label/scoring consistency (label class + eligibility invariant across pip
scales while PnL scales exactly 100×; B-2 eligibility fix preserved);
evidence/manifest metadata (map recorded, global flag false, bad map fails
closed, mixed-scale end-to-end records `USD_JPY → 0.01` / `EUR_USD → 0.0001`,
scrub-clean); real-mode-still-refused regression; and a source guard (body has
no fixed-global pip constant; pip literals confined to the named authority
branches).

## 5. What this fix explicitly does NOT do

No rerun of ML Step 4; no model training; no holdout evaluation; no real raw
data access; no corrected first-run metrics or execution evidence; no threshold
/ feature / model / acceptance / label / split / epoch changes; no H2/H3; no
Phase C2; no `730d_BA` / `3650d_BA`; no production-readiness claim. PR #421
invalid evidence and PR #409 stop evidence are untouched.

## 6. Remaining decision before a corrected second first-run attempt

A corrected second first-run attempt is **not authorised**. It remains
admissible only after **(1)** this code-only per-pair pip-size fix (here);
**(2)** the mixed-scale value-pinned tests (here); **(3)** a Fable 5 re-check of
this fix; and **(4)** a separate human + ChatGPT decision explicitly authorising
or rejecting a corrected second first-run attempt (including whether re-using the
same frozen holdout is admissible). Until then, no rerun.
