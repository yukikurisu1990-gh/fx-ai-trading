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
- **Classify the risk first, and always upward.** You may not downgrade a
  protected path or action to Green. If a change spans tiers, the highest one
  governs the whole task. If the tier is unclear, it is Amber, not Green. If
  the prompt says Green but the change is Amber or Red, apply the higher tier,
  keep working, and say so in the report — that is not a reason to stop. Never
  lower a tier for convenience, and never let a label like "synthetic-only",
  "bugfix", "refactor" or "CI fix" decide the tier: what the change *touches*
  decides it. State the classification and its reasoning in the PR body.
- **Protected paths are Amber at minimum** (policy §3): M15 aggregation and
  dataset machinery; features/labels/targets/cost model; effective-N;
  no-overlap, warm-up, epoch, split; the validation kill gate;
  training/inference/execution; strategy and broker code; evidence and
  artifact schemas, scrubber, guards; frozen research contracts;
  `scripts/m15_gate3a/**`; any `src/**` or `scripts/**` carrying M15 research
  logic; `artifacts/**` and existing evidence; governance docs; the scope of
  AI authority; `.github/workflows/**`; branch protection and required checks;
  security, credentials, external storage; runtime dependencies and
  lockfiles — `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`.
- **Risk tiers.** *Green* is an allowlist (policy §4), not "whatever is left":
  typos, links, doc wording, refreshing stale SHAs/PR numbers, capability-free
  prompt/template tweaks, comment-only edits, behaviour-preserving formatting,
  test-description or fixture-name changes, mechanical rebases, and
  non-functional changes — each only when it touches no protected path. You
  may merge a Green PR yourself only if every §4 condition holds; otherwise it
  is Amber. *Amber* (research design and data boundaries) — build and prepare
  the PR autonomously; merging and gate advancement need human + ChatGPT
  approval. *Red* (irreversible or externally visible: real-data reads,
  credentials, external storage, freezing splits, validation, holdout,
  training, execution, broker, production) — explicit human + ChatGPT approval
  **before** you run it.
- **Dependencies and CI are Amber.** Dependency version changes, lockfile
  changes and workflow changes are Amber; required checks and branch
  protection are Amber at minimum; a workflow touching credentials, secrets or
  external transmission is Red. Editing only a version description in README
  is Green.
- **"Synthetic-only" is not a tier.** A bugfix in research machinery or
  runtime code is Amber even if only synthetic tests verify it. Tests-only
  additions that change no production or research code are a Green candidate;
  a test that changes a frozen contract, acceptance criteria or evidence
  semantics is Amber.
- **One irreversible research gate per task.** Everything inside that gate is
  a single unit of work. Reversible incidental work does not count as a gate.
  Never chain distinct irreversible stages automatically — real-data read →
  training, and validation → holdout, are separate gates.
- **Head SHA.** Before merge approval, amend freely and push until CI is
  green; report the final green head. After merge approval, any head change or
  out-of-scope addition voids the approval — do not merge, request re-review.
- **Stop only** for the triggers in the autonomous development policy §11:
  exceeding your risk tier, newly touching real data / credentials / holdout /
  broker / production, changing a frozen contract, risking existing evidence,
  needing a human business or hypothesis decision, a significant security
  risk, or a self-contradictory objective. A CI failure, a design choice, a
  missing test, a pre-approval head change, or discovering the task is really
  Amber are not reasons to stop.
- **Independent review is model-agnostic** (policy §12). Required roles are
  "independent adversarial review", "independent source-audit re-check" and
  "independent post-run audit". Independent means a **separate session** that
  **re-reads the source and diff** instead of trusting the implementing
  session's conclusions; the same model product is fine; the implementer's own
  self-review never counts. An AI that performed an audit may not give final
  approval for an Amber or Red gate. Do not rewrite historical audit records.
- **After an autonomous Green merge**, record PR URL, merge commit, risk
  classification, touched files, CI result, which §4 allowlist entry applied,
  that no protected path was touched, and that no next gate was started. No
  prior approval is needed for that record.
- **If instructions conflict**, the repository documents win over the prompt,
  and the stricter reading of a research restriction wins. Say so in the
  report.
- **Always-binding statuses:** `PRODUCTION_READINESS_NOT_CLAIMED`,
  `NO_EXECUTION_PERFORMED`. The forward epoch stays
  `FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` until a
  recorded ruling changes it.
