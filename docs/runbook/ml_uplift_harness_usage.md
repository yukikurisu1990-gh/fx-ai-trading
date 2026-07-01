# ML uplift harness — usage (no-real-run / synthetic-only)

**Stage:** ML accuracy uplift contract **Step 2** — implementation-only harness
scaffolding (`docs/design/ml_accuracy_uplift_experiment_contract.md` §6).
**Status:** scaffolding merged; **no real ML experiment is run**.

---

## What the harness is

A deterministic, synthetic-only scaffold that lets future ML research be
specified and validated **before** any real run:

- **contracts** (`scripts/ml_uplift_harness/contracts.py`) — typed experiment /
  data-span / feature-set / label / cost / validation-split / model-config /
  output-report / non-authorisation specs.
- **validators** (`validators.py`) — fail-closed contract validation; any
  `real_data_authorised` or real-run / downstream-authorisation flag set `True`
  is rejected.
- **provenance** (`provenance.py`) — deterministic per-section config hashes +
  code SHA capture (SHA passed in; no subprocess/git/network).
- **artifacts** (`artifacts.py`) — deterministic report-path planning; rejects
  real `artifacts/` roots (unless clearly synthetic/test) and any raw-data /
  archive path; blocks path traversal.
- **reporting** / **synthetic_runner** — build + write a clearly-marked
  SYNTHETIC-ONLY report; validated free of forbidden success/promotion tokens
  and trading-metric values.

## What the harness is NOT

It reads **no** real market data, trains/runs **no** model, runs **no**
backtest / sweep / replay, generates **no** real features/labels, and computes
**no** trading metric (PnL / Sharpe / IC / MI / oracle / calibration / expected
value). It performs no network / broker / quote-feed / OANDA / credential
access and spawns no subprocess. It authorises no T2 / byte-admissibility /
new-epoch / production / LLM integration.

## Usage (synthetic smoke only)

```bash
# Writes a SYNTHETIC_ONLY smoke report under a system-temp dir by default:
python scripts/run_ml_uplift_harness.py --config <contract.json> \
  --output-root /tmp/ml_uplift_out
```

The runner **fails closed** if the contract is malformed or requests any
real-run / downstream authorisation. It writes only `synthetic_report.json` +
`report.md` under `<output-root>/<experiment_id>/`; those carry the markers
`SYNTHETIC_ONLY`, `NOT_REAL_EXPERIMENT_EVIDENCE`, `NO_MODEL_RUN`, `NO_BACKTEST`,
`NO_TRADING_METRICS` and the controlled statuses (e.g.
`HARNESS_CONTRACT_VALIDATED_SYNTHETIC_ONLY`, `REAL_EXPERIMENT_NOT_AUTHORISED`,
`MODEL_TRAINING_NOT_AUTHORISED`, `T2_NOT_AUTHORISED`, ...).

## Non-scope / bindings

- No real experiment artifacts are committed under `artifacts/`; tests write to
  `tmp_path` only.
- No PASS / Tier-1 / FORMALLY_VERIFIED / byte-admissibility / promotion labels.
- PR-B.1 / PR-B.2 Gate P1 outcomes unchanged; Phase 9.16 v9 20p remains Tier 2
  `VALID_OPERATIONAL_BASELINE`; archived/untrusted numerics remain prohibited
  from routing evidence; LLM integration remains deferred and unauthorised.
