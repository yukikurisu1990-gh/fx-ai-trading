# Repository instructions for Claude

## Read first

Before any M15 / ML Step 4 / post-M1 research work, read:

- `docs/governance/autonomous_development_policy.md` — how much you decide on
  your own, the Green/Amber/Red risk tiers, and when to stop
- `docs/governance/m15_audit_playbook.md` — current research gate state and
  the audit checklists
- `docs/prompts/m15_claude_operating_prefix.md` — the five-field task contract
- `docs/prompts/m15_future_audit_templates.md` — optional prompt templates

For ordinary Green engineering (lint, CI, docs, tests, refactors) the
autonomous development policy alone is enough.

## Working rules

- **Work autonomously inside the task's risk tier.** Investigation,
  implementation, tests, lint/format, CI repair, PR creation and head updates
  are yours to decide. Pick the most conservative reasonable option and record
  why in the PR report — do not ask the human to arbitrate ordinary
  implementation choices.
- **Risk tiers.** Green (reversible engineering) — you may merge, except for
  changes to governance, AI authority, security/credentials, a frozen research
  contract, the evidence definition, or branch protection / required checks,
  which need human review first. Amber (research design and data boundaries) —
  you may build and prepare the PR; merging and gate advancement need human +
  ChatGPT approval. Red (irreversible or externally visible: real-data reads,
  credentials, validation, holdout, training, execution, broker, production)
  — explicit human + ChatGPT approval **before** you run it.
- **One irreversible research gate per task.** Everything inside that gate is
  a single unit of work. Reversible incidental work does not count as a gate.
  Never chain distinct irreversible stages automatically — real-data read →
  training, and validation → holdout, are separate gates.
- **Head SHA.** Before merge approval, amend freely and push until CI is
  green; report the final green head. After merge approval, any head change or
  out-of-scope addition voids the approval — do not merge, request re-review.
- **Stop only** for the triggers in the autonomous development policy §5:
  exceeding your risk tier, newly touching real data / credentials / holdout /
  broker / production, changing a frozen contract, risking existing evidence,
  needing a human business or hypothesis decision, a significant security
  risk, or a self-contradictory objective. A CI failure, a design choice, a
  missing test or a pre-approval head change are not reasons to stop.
- **Independent review is model-agnostic.** Required roles are "independent
  adversarial review", "independent source-audit re-check" and "independent
  post-run audit" — any sufficiently capable model may perform them. An AI
  that performed an audit may not give final approval for an Amber or Red
  gate. Do not rewrite historical audit records.
- **If instructions conflict**, the repository documents win over the prompt,
  and the stricter reading of a research restriction wins. Say so in the
  report.
- **Always-binding statuses:** `PRODUCTION_READINESS_NOT_CLAIMED`,
  `NO_EXECUTION_PERFORMED`. The forward epoch stays
  `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` until a
  recorded ruling changes it.
