"""ML Step 4 contract executor / harness (code-only, no-run).

Implements a reviewed, deterministic, fail-closed executor able to LATER run
exactly the PR #407 pre-registration contract
(``docs/design/phase_f_ml_step4_pre_registration.md``) as constrained by the
PR #408 execution-authorisation plan
(``docs/design/ml_step4_365d_ba_execution_authorisation_plan.md``), for the
epoch ``RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1`` (span ``365d_BA``).

Implementation status (this package / PR):
  ML_STEP4_CONTRACT_EXECUTOR_IMPLEMENTED_NO_RUN
Also binding:
  ML_STEP4_EXECUTION_NOT_PERFORMED
  PRODUCTION_READINESS_NOT_CLAIMED

This package DOES NOT execute the real run: it does not read real ``365d_BA``
raw data, does not train a real model, does not evaluate the real holdout, does
not generate real ML metrics, and does not write real execution evidence under
``artifacts/ml_step4/365d_ba_v1/``. The heavy execution primitives (raw read /
feature generation / model training / holdout evaluation) are represented as
guarded seams that fail closed unless a future, separately-authorised execution
PR explicitly enables them.

Forbidden-label note: the tokens ``PASS``, ``Tier 1``, ``FORMALLY_VERIFIED``,
``BYTE_ADMISSIBLE``, ``BYTE_ADMISSIBILITY_APPROVED``, ``NEW_EPOCH_ADOPTED``,
``ML_STEP4_AUTHORISED``, ``PRODUCTION_READY`` appear in this package only as
prohibitions, never as asserted statuses.
"""

from __future__ import annotations

IMPLEMENTATION_STATUS = "ML_STEP4_CONTRACT_EXECUTOR_IMPLEMENTED_NO_RUN"
EXECUTION_STATUS = "ML_STEP4_EXECUTION_NOT_PERFORMED"
PRODUCTION_STATUS = "PRODUCTION_READINESS_NOT_CLAIMED"

__all__ = [
    "IMPLEMENTATION_STATUS",
    "EXECUTION_STATUS",
    "PRODUCTION_STATUS",
]
