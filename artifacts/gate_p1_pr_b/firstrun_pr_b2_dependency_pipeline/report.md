# Gate P1 PR-B.2 static inspection report

- report_id: `firstrun_pr_b2_dependency_pipeline`
- pr_b_stage: PR-B.2 (dependency inventory + pipeline feasibility)
- top_level_outcome: `GATE_P1_READONLY_SURFACE_STATICALLY_OBSERVED_RETENTION_PROBE_REQUIRED`

## Method

Static, AST/source-only + committed PR-B.1 metadata only. No pipeline execution, no raw data read, no model / backtest / sweep / replay, no labels / features / trades / trading metrics. No byte-admissibility approval, no T2 retention execution, no new-epoch construction, no production routing decision.

## Scope disclaimers

- REPRESENTATIVE_STATIC_DEPENDENCY_INVENTORY_ONLY (NOT_FULL_REPOSITORY_DEPENDENCY_CERTIFICATION).
- STATIC_PIPELINE_PATH_OBSERVED_NOT_EXECUTED.
- NOT_ML_HARNESS_READY.
- RETENTION_PROBE_REQUIRED_BEFORE_BYTE_ADMISSIBILITY (binding blocker).

## Dependency inventory (summary)

- consumers inspected: 2
- distinct labels: STATIC_DEPENDENCY_OBSERVED
- forbidden-to-execute-in-Gate-P1 deps: 0
- inspector free of production imports: True

## Pipeline feasibility (summary)

- static references found: 4 / 4
- PR-B.1 evidence all present: True
- static_path_label: `STATIC_PIPELINE_PATH_OBSERVED`

## PR-B.1 span outcomes (unchanged by PR-B.2)

- 365d_BA = LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY / RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE
- 730d_BA = LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY / RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE
- 3650d_BA = LOCAL_DATA_CANDIDATE_PARTIAL_FEASIBILITY / RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE

First-run feasible-for-construction remains structurally unreachable; PR-B.2 makes no byte-admissibility, T2, new-epoch, Tier-1, or production claim.
