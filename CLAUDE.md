# Repository instructions for Claude

## Read first

Before any M15 / ML Step 4 / post-M1 research work, read:

- `docs/governance/autonomous_development_policy.md` — how much you decide on
  your own, the Green/Amber/Red risk tiers, and when to stop
- `docs/governance/m15_audit_playbook.md` — current research gate state and
  the audit checklists
- `docs/prompts/m15_claude_operating_prefix.md` — the five-field task contract
- `docs/prompts/m15_future_audit_templates.md` — optional prompt templates
- `docs/design/m15_minimum_research_gate.md` — **the Two-Track model**: §8.11
  (Exploratory / Formal Confirmation split), §8.12 (governance consistency),
  §8.13 (semantic cleanup). Read it before any Track A or Track B work; the
  playbook and prereg carry the split only as far as this propagation has taken
  it, and where they disagree with that packet **they govern until propagated**
- `docs/design/m15_track_a_execution_gate.md` — the **Minimum Research
  Execution Gate**: the apparatus that has to be in place before a Track A R1
  read may be authorised. Its §10 takes a **reporting obligation**, not an axis
  selection; the turnover axes are ruled in the pre-registration at **§9a**
  (`TURNOVER_CEILING_RULED_PER_DAY_CAP_ON_THE_ENTRY_DATE_MAXIMUM`)

For ordinary Green engineering (lint, CI, docs, tests, refactors) the
autonomous development policy alone is enough.

## The Two-Track model — read this before any M15 research task

M15 Family A research is split. Which track a task belongs to changes what is
permitted, and a task that does not say is **Track B** until someone rules
otherwise.

- **Track A — Exploratory.** May vary features, labels, models, hyperparameters,
  the training scheme, calibration, `ev_min`, thresholds, costs and entry/exit
  logic. Every output is **both** `NON_DECISION_BEARING_EXPLORATORY_ONLY` **and**
  `RESEARCH_SCRATCH_NON_AUTHORITATIVE`, and may never be cited for a formal GO,
  a Gate-3a pass, holdout evidence, novelty evidence, production readiness — or
  in any decision this programme records. Track A does **not** require the
  77-item statistical freeze and does **not** require the forward epoch to
  exist.
  **A surface being variable does not make its committed prohibitions
  negotiable** (§8.13.4): Track A may choose a feature list, but not one
  containing M1-derived features; the vary-freely list overlaps prereg Rulings
  5–9 almost exactly, and each row of §8.13.4 carries a "what still binds"
  column that this summary does not reproduce. Read it before varying anything,
  and read §8.12.10 first — two of the surfaces (the calibration split and the
  feature list) are **not** Track A free-vary items until their upstream
  blockers are ruled.
- **Track B — Formal Confirmation.** One declared candidate, frozen in every
  respect, run **once** on unseen forward data. Not a place to redesign.

**Track A R1 is implementation-ready; the two recorded grants were invalidated by
the PR #457 integrity fix and need re-issuing. No read has been performed.** Do
not read this as a snapshot — evaluate it:

0. **PR #451 approved and merged** — done, `4f45515` (2026-08-30). §8.11–§8.13
   are citable authority; `APPROVAL_IDENTIFIER_PENDING_UNTIL_MERGE` and
   `THE_TWO_TRACK_SECTIONS_ARE_RULED_AS_RECORDED_AND_NOT_YET_CITABLE_AS_AUTHORITY`
   are discharged.
1. `TRACK_A_EXECUTION_REQUIRES_GOVERNANCE_PROPAGATION_COMPLETE` — the
   **P-1 … P-15** predicate, true **on a named master SHA** (§8.12.13 C-10).
   **Discharged at PR #455, in the named files, and true on master `fc3e0f8`** —
   P-5 in the playbook's §1 gate table, **P-10** on all eight uppercase-`RULED`
   MRG sections (§8.9's heading spells it lowercase and carries no identifier;
   if C-9 is read case-insensitively that is a ninth section and the predicate
   is not yet true), **P-13** in the gate-4 design audit's §1a. The per-item
   table is
   `docs/design/m15_track_a_execution_gate.md` §12. It is a predicate on named
   files, never a self-assessment — **and on 2026-08-31 an execution command
   arrived while it was false and nobody had evaluated it, then a remediation PR
   claimed it discharged by writing the discharge into a different file.**
   Evaluate it against the named files.
2. The **Minimum Research Execution Gate** passed on a named head.
3. The derivation route decided **in a diff** — done, and it now has a **body**
   (PR #455). `aggregate_m15` refuses real rows outside it.

**Both grants were recorded at PR #456** —
`docs/governance/m15_track_a_r1_dual_grants.md`: a `track_a_historical_read`
grant and a separate `track_a_m15_research_derivation` grant, over
`2025-04-25 … 2025-12-28`, `PAIRS_20`, `M1`, against approved head `fc3e0f8` and
measured fingerprint `e43583e0…`. The grant recorded in PR #454 is **invalid**
— the enablement work moved the fingerprint, by design — and is left that way.

**What is left is the run itself, and it is not a session's to start.** A
real-data read is **Red**: it needs explicit human + ChatGPT approval *before it
is run*, naming the operation, span, pairs, timeframe and approved head SHA.
That is an act, not a document state, and no recorded grant, passed gate or
fully-ticked checklist supplies it. The instruction that authorised these two
grants directed in the same breath that nothing be executed, so R1 stands
**authorised in scope and expressly withheld in execution**. Read
`docs/governance/m15_audit_playbook.md` §5a before treating 15 of 15 as
permission.

**The R1 orchestrator exists** (`scripts/m15_track_a/r1_orchestrator.py`, PR
#459): the formal entry point binding preflight → write-ahead seen declaration →
gated M1 read → authorised M15 derivation on the **same** `ReadRequest` → breadth
`K` → the committed survey → stop. It reaches no next stage by construction.
Adding it moved the fingerprint again, so the PR #458 grants are invalid and
re-issuing them on the new value is what is left. Calling the stages by hand is
not the formal route.

**Both weaknesses are fixed at PR #457, and fixing them invalidated both
grants** — which is the binding working, and was expected. `containment` now
resolves relative imports against the importing file's own package, so the
surface **is** the transitive closure (29 files then, 30 since the R1
orchestrator); and `derive_m15` validates
every input row against the grant-request intersection and pins both request
types. The PR #456 record is kept unedited as history.

**What is left is re-issuing the two grants against the new fingerprint**, which
is a human act and not a session's. Until then Track A R1 has an implementation
that is ready and no valid authorisation:
`TRACK_A_R1_IMPLEMENTATION_READY_PENDING_REISSUED_DUAL_GRANTS`.

The apparatus for 1–3 is `scripts/m15_track_a/` and
`docs/design/m15_track_a_execution_gate.md`; **building it is not passing the
gate**, which needs review, approval and merge on a named head.

**Settled by the human + ChatGPT Gate-decision round of 2026-08-30**
(`docs/design/m15_track_a_execution_gate.md` §15): the turnover axes
(prereg §9a), prereg §13a / P-7
(`P_7_DISCHARGED_AT_THIS_RULING`),
`TRACK_A_R1_BOUNDED_ASSURANCE_THREAT_MODEL_ACCEPTED`, and
`GENERAL_ADVERSARIAL_AUDIT_COMPLETE_FOR_TRACK_A_R1_BOUNDED_SCOPE`. **None of
those authorises a read.** From here, a blocker is a concrete, reproducible
defect inside the Track A R1 threat model — not a theoretical bypass and not
the absence of a sandbox. Inside
Track A, R1 (first read), R3 (training) and R4 (evaluation) remain **separate
Red gates**. §8.12.10 records that an execution-gate pass reaches **R1 only** —
a statement of **scope**, not of sufficiency: it makes R1 eligible to be
authorised, and the read still needs its own grant.

**A contract permission is not an execution authorisation.** The Two-Track
contract being approved does not authorise a read, and neither does a passed
execution gate; a read needs an explicit human + ChatGPT grant naming the
operation, span, pairs, timeframe and approved head SHA. `ReadGrant`
(`scripts/m15_track_a/authorization.py`) is where such an approval is
**recorded and enforced in-process** — the object does not verify that the
approval exists, so constructing one is never the act of granting it. It binds
to a **measured implementation fingerprint**, so any change on the declared
surface voids it with no human in the loop.

**A read grant does not authorise a derivation.** They are separate closed
operations with separate grants, and `derive_m15` refuses without its own.

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
- **Split the work and have it attacked** (policy §13). Where subagents are
  available, the lead agent assigns specialised roles sized to the change —
  implementation, contract/specification, tests and boundary conditions,
  security and forbidden routes, contamination and leakage, CI and
  dependencies, adversarial refutation, final integration. Give each audit
  role the source, diff and contract, **never the other roles' conclusions**;
  at least one role argues the change is wrong, and at least one hunts
  boundary conditions and bypass routes the tests miss. Then loop: implement →
  independent audit classifying findings as blocker / required fix /
  non-blocking observation / accepted → fix in scope → re-verify in a fresh
  audit context → run CI → repeat until every required fix is resolved and CI
  is green. Report only that final head. Amber needs at least three separated
  roles (author, contract/data-boundary audit, adversarial/bypass audit); a
  Green self-merge needs the §4 conditions confirmed in a review context other
  than the lead's. Disagreements are resolved on the evidence, never by
  majority vote; an unresolvable material disagreement is a blocker. **Running
  this loop is never a substitute for human + ChatGPT approval, and the number
  of agents used is never an argument that a change is safe.** If subagents
  are unavailable, run the perspectives sequentially, keep implementation /
  contract / adversarial review separate, and say so in the report.
- **One objective, one PR** (policy §14). A PR is a meaningful unit of change,
  not a work stage. While the work shares one objective, one risk tier and one
  revert unit, keep investigation, implementation, tests, docs, stale-state
  refreshes, lint/format, CI repair, rebases, the internal audit and its
  required fixes in the **same** PR, and keep amending that PR to the final
  green head. Never open a new PR because a subagent raised a fix, because CI
  failed, because docs or tests are "separate", because of a rebase, or
  because the head changed. PR count is not evidence of safety, and splitting
  must never be used to manufacture extra approval points. Split only when the
  risk tier changes, an irreversible operation sits between the parts, an
  independent audit needs the separation, a frozen contract or research state
  is being changed, the changes are unrelated, one part genuinely needs its
  own revert, or one PR would seriously damage reviewability (judged by
  cohesion, not line count). Three kinds: **Work PR** (ordinary change),
  **Gate-decision PR** (formally changes or judges a contract or research
  state — audits, adoptions, pre-registration, verdicts), **Execution-evidence
  PR** (post-approval irreversible run and its evidence only). The latter two
  are never Green. Do not open pointer-only or status-only PRs — fold them
  into the related PR.
- **The lead owns the outcome.** It is not a vote counter: it decomposes the
  task, picks the roles, checks the evidence behind each finding, merges
  duplicates, resolves contradictions, prevents scope creep, reviews the final
  diff and confirms the final classification. Do not adopt a subagent's error,
  omission or over-correction unexamined.
- **Record briefly** (PR body or final report): roles used, each role's main
  findings, blockers and required fixes, the post-fix re-audit result, any
  unresolved disagreement, and the substitute procedure if subagents were
  unavailable. Keep conclusions and evidence, not transcripts.
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
