"""Gate P1 PR-B inner inspector package (PR-B.0 infrastructure stage).

This package MUST remain import-side-effect-free at the top level: no file
I/O, no network, no subprocess, no production-module imports occur at import
time. All guard installation and inspection work happens explicitly inside
``bootstrap`` when invoked as the inner process.

PR-B.0 scope: launcher / bootstrap / guards / stub inspector only. No real
inspection is performed. The real inspection submodules (raw inventory,
coverage, dependency inventory, pipeline feasibility, resolver) belong to the
separately-authorised PR-B.1 / PR-B.2 stages and are NOT present here.

See ``docs/design/gate_p1_pr_b_implementation_plan.md`` (PR #365) §3-§5, §11.
"""
