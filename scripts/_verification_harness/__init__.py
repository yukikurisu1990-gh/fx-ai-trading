"""Tabular Targeted Verification V2-expanded — verification harness package.

Stage 1 (this commit): infrastructure-only.
No orchestrator. No sentinel_runner. No reporting. No adapters. No formal run.

Per the binding contract pre-stated by PR #357 + PR #358 amendment, the formal
20-file harness topology is:

  scripts/tabular_targeted_verification_v2_expanded.py        (Stage 2)
  scripts/_verification_harness/__init__.py                   (Stage 1)
  scripts/_verification_harness/manifests.py                  (Stage 1)
  scripts/_verification_harness/event_log.py                  (Stage 1)
  scripts/_verification_harness/pnl_identity.py               (Stage 1)
  scripts/_verification_harness/row_set.py                    (Stage 1)
  scripts/_verification_harness/sentinel_runner.py            (Stage 2)
  scripts/_verification_harness/reporting.py                  (Stage 3)
  scripts/_verification_harness/contract_snapshots.py         (Stage 1)
  scripts/_verification_harness/forbidden_inputs.py           (Stage 1)
  scripts/_verification_harness/tolerances.py                 (Stage 1)
  scripts/_verification_harness/sentinel_adapters/__init__.py        (Stage 3)
  scripts/_verification_harness/sentinel_adapters/_pinned_s_b_factory.py  (Stage 3)
  scripts/_verification_harness/sentinel_adapters/_pinned_s_e_factory.py  (Stage 3)
  scripts/_verification_harness/sentinel_adapters/s1_pr325.py        (Stage 3)
  scripts/_verification_harness/sentinel_adapters/s2_pr332.py        (Stage 3)
  scripts/_verification_harness/sentinel_adapters/s3_pr338.py        (Stage 3)
  scripts/_verification_harness/sentinel_adapters/s4_pr342.py        (Stage 3)
  scripts/_verification_harness/sentinel_adapters/s5_pr345.py        (Stage 3)
  scripts/_verification_harness/sentinel_adapters/s6_pr351.py        (Stage 3)

Stage 1 modules emit NO formal outcome label, NO baseline reproduction
assertion, and NO V2-expanded PASS/HALT. They provide infrastructure
primitives only.
"""

from __future__ import annotations

STAGE = 1
STAGE_DECLARATIONS: tuple[str, ...] = (
    "NO FORMAL VERIFICATION EXECUTED",
    "NO FOUNDATION RESULT GENERATED",
    "NO SENTINEL RESULT GENERATED",
    "NO V2-EXPANDED OUTCOME LABEL EMITTED",
    "A0-BROAD BETA REMAINS HALTED",
)
