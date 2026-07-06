"""M15 aggregation / dataset machinery (Family-A M15-first, gate 5 — SYNTHETIC ONLY).

Pure, fixture-tested machinery implementing the frozen PR #429 contract and the
PR #430 T-1..T-7 tightenings at the code level:

* M1->M15 aggregation (UTC 15-min buckets, per-side bid/ask OHLC, no mid
  construction, ``n_source_bars == 15`` eligibility, no imputation, no synthetic
  weekend bars, gap report, per-pair pip authority);
* no-overlap proof utilities against the consumed dead window (T-7);
* warm-up burn-in policy (T-1);
* effective-N estimator helper (T-6);
* cost-table metadata schema validation (no real spread computation);
* metadata artifact validation + gate-3a-strict scrubber integration;
* refusal guards that fail closed on any real-data / train / validate / holdout /
  execute / forward-adopt / model-binary request.

This package reads NO real data, derives NO real M15 bytes, computes NO strategy
metrics, trains NOTHING, and adopts NO epoch. Every capability is exercised only
with synthetic fixtures.
"""

from __future__ import annotations

from typing import Final

IMPLEMENTATION_STATUS: Final[str] = (
    "M15_AGGREGATION_DATASET_MACHINERY_IMPLEMENTED_SYNTHETIC_ONLY_NO_RUN"
)
PRODUCTION_STATUS: Final[str] = "PRODUCTION_READINESS_NOT_CLAIMED"
EXECUTION_STATUS: Final[str] = "NO_EXECUTION_PERFORMED"
FORWARD_EPOCH_STATUS: Final[str] = (
    "FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS"
)
