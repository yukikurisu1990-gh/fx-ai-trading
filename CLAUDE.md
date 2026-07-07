# Repository instructions for Claude

## M15 Research Governance — Mandatory

Before any M15 / ML Step 4 / post-M1 research work, read:

- `docs/governance/m15_audit_playbook.md`
- `docs/prompts/m15_future_audit_templates.md`
- `docs/prompts/m15_claude_operating_prefix.md`

Rules:

- Follow the current gate order (playbook §1/§3). Do not skip gates. Never
  advance more than one gate in a single task.
- Do not read real data, derive M15, train, validate, evaluate holdout,
  execute, or claim readiness unless the relevant gate has been explicitly
  approved by a human + ChatGPT decision recorded on master.
- If a PR head changes after review — even doc-only — stop and report the new
  SHA. Do not merge or proceed.
- If instructions conflict, choose the stricter / no-run interpretation and
  ask for human + ChatGPT review.
- Always-binding statuses: `PRODUCTION_READINESS_NOT_CLAIMED`,
  `NO_EXECUTION_PERFORMED`; the forward epoch remains
  `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` until a
  recorded ruling changes it.
