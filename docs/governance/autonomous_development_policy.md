# Autonomous development policy — risk tiers and approval boundaries

- **Document class:** doc-only governance policy. Binding on every AI session
  that works in this repository. Executes nothing; authorises no research gate
  by itself.
- **Status:** `AUTONOMOUS_DEVELOPMENT_POLICY_RECORDED`
- Always binding: **`PRODUCTION_READINESS_NOT_CLAIMED`** ·
  **`NO_EXECUTION_PERFORMED`**
- Companion files: `docs/governance/m15_audit_playbook.md` (research gate
  state and audit checklists), `docs/prompts/m15_claude_operating_prefix.md`
  (the short task contract), root `CLAUDE.md` (mandatory pointer).

**Why this document exists.** The earlier regime required a human decision for
almost every step, and told the session to stop on events that are just normal
engineering (a second reasonable design option, a CI failure, a pre-approval
head change). That produced approval traffic without producing safety: the
things that actually cannot be undone — reading real data the first time,
consuming a holdout, touching a broker — are a small, nameable set. This
policy makes autonomy the default and spends human attention only on that set.

**The classification is the safety mechanism.** Autonomy is granted per risk
tier, so a session that misclassifies its own work has bypassed the whole
policy. Classification therefore errs upward, is driven by *what the change
touches* rather than by how the task is described, and is never a judgement
call the session makes in its own favour (§2).

**Precedence.** Research-gate substance (what may be read, derived, trained,
evaluated, claimed) is governed by `m15_audit_playbook.md`. Process (how much
a session may decide on its own, when it must stop, what a prompt must
contain) is governed by this document. Where they overlap, the playbook's
research restrictions win. Where a task prompt disagrees with either, the
repository documents win and the session says so in its report.

---

## 1. Autonomy baseline

Inside an authorised task or gate, the AI decides and acts without asking:

- repository investigation; choosing the implementation approach; identifying
  the files to change
- changing code, tests and documentation; choosing and adding tests
- lint and format work; investigating and fixing CI failures
- opening a PR; updating the PR head; self-review within the same scope
- iterating until CI is green
- summarising results and reporting residual risk

Do not ask the human to arbitrate ordinary implementation choices. When
several reasonable approaches exist, take the most conservative and most
maintainable one and record **why** in the PR report. "Most conservative"
means: fails closed, adds no capability that the task did not require, and
keeps the diff reviewable.

Autonomy is granted **within a risk tier**, never over the tier itself. An AI
session may not expand its own authority: changing this policy, the playbook,
or any other rule about what AI may do is Amber (§3).

## 2. Risk classification — always upward

Every task is Green, Amber or Red. Classification is decided **before** the
work and re-checked against the final diff before opening the PR.

1. **No self-downgrade.** The AI may not, on its own judgement, reclassify a
   protected path or protected action (§3) as Green.
2. **Highest tier wins.** If a change falls into more than one tier, the whole
   task takes the highest one. One protected file in an otherwise trivial diff
   makes the PR Amber.
3. **Ambiguity resolves to Amber, not Green.** If it is unclear which tier
   applies, treat the task as Amber and say so in the report.
4. **The requester's label does not bind.** If a task is described as Green
   but the actual change meets Amber or Red, apply the higher tier, proceed
   under it, and state the discrepancy in the report. This is not a reason to
   stop (§11) — it is a reason to seek approval before merging.
5. **Convenience is never a reason.** Effort, turnaround time, diff size, "it
   is obviously safe", or the session's own workload may never justify a lower
   tier.
6. **Description does not determine tier.** "Synthetic-only", "bugfix",
   "refactor", "CI fix", "cleanup" and similar labels describe intent, not
   risk. What the change *touches* decides the tier.

The PR body must state the final risk classification and the reasoning, so a
reviewer can check the classification itself and not only the diff.

## 3. Protected paths and protected actions — Amber or higher

Any change touching the following is **Amber at minimum**, regardless of how
it is described, how small it is, or how it was verified:

**Research logic and data boundaries**

- M15 aggregation / dataset machinery
- features, labels, targets, cost model
- effective-N
- no-overlap, warm-up, epoch, split logic
- the validation kill gate
- training, inference, execution paths
- strategy or broker related code
- evidence schema, artifact schema, scrubber, guards
- any frozen research contract
- `scripts/m15_gate3a/**`
- any `src/**` or `scripts/**` carrying M15 research logic
- `artifacts/**` and any existing evidence

**Governance and control surfaces**

- governance documents
- the scope of AI authority
- `.github/workflows/**`
- branch protection and the set of required checks
- security, credentials, external storage

**Dependency surfaces**

- runtime dependencies and lockfiles
- `pyproject.toml`
- `uv.lock`
- `.pre-commit-config.yaml`

**Protected actions** — irrespective of which file they live in: reading real
data; using credentials; writing to external storage; freezing or altering a
split; running validation, holdout, training or inference; generating
evidence; adding a runtime capability; changing research semantics.

Some of these escalate past Amber — see §6 and §7.

## 4. Green — allowlist and self-merge conditions

Green is an **allowlist**, not a residual category. A change is Green only if
it is one of:

- typo fixes
- link fixes
- wording and explanation improvements in README or ordinary documentation
- refreshing stale PR numbers, SHAs or state descriptions
- minor improvements to prompts/templates that carry no execution capability
- comment-only changes
- formatting changes that do not alter code behaviour
- test-description or fixture-name changes that touch no protected path
- plainly mechanical rebases or conflict resolutions touching no protected
  path
- non-functional changes with no effect on runtime, research logic, security,
  CI permissions or dependencies

The AI may run the full loop on a Green change — investigate, implement, test,
open the PR, fix CI, self-review — **and merge it**, but only if **every** one
of these holds:

- [ ] touches no protected path (§3)
- [ ] contains no protected action (§3)
- [ ] all CI checks are green
- [ ] contains no secret or credential
- [ ] adds no runtime capability
- [ ] changes no research semantics
- [ ] changes no evidence and no contract
- [ ] the final diff and the risk classification are recorded in the PR body
- [ ] does not bypass the repository's normal branch protection

**If even one condition fails, the change is Amber or higher** — open the PR,
report, and wait for human + ChatGPT approval.

## 5. Amber — research design and data-boundary work

Examples: aggregation; labels; features; cost model; effective-N; no-overlap
logic; the validation kill gate; dataset/epoch design; evidence schema;
tooling that will derive real data; source audits; post-run audits — plus
everything in §3 that does not escalate to Red.

The AI autonomously investigates, implements, writes synthetic tests, probes
adversarially, opens the PR, fixes CI and prepares the final head.

**Merging an Amber PR, and advancing to the next research gate, requires
human + ChatGPT approval.**

## 6. Red — irreversible or externally visible operations

Examples: the first real-data read; using credentials; external storage
operations; freezing a validation or holdout split; running validation;
evaluating a holdout; a training run; a rerun; paper or live trading; broker
connection; production routing; any production-readiness claim.

**A Red operation requires explicit human + ChatGPT approval before it runs.**

Inside an approved Red task the AI may execute, produce the evidence and
prepare the PR autonomously. It must **not** roll on to the next Red gate —
approval covers exactly the operation it names.

## 7. Dependencies, lockfiles, workflows and CI

These are reversible in the ordinary sense but they determine whether every
future result is reproducible, and a drift here can invalidate work long after
it lands. PR #436 is the worked example: an unpinned Ruff floated to a new
minor version and broke master CI on a tree nobody had changed.

- changing a dependency version → **Amber**
- changing a lockfile → **Amber**
- changing a GitHub Actions workflow → **Amber**
- changing required checks or branch protection → **Amber at minimum**
- a workflow change involving credentials, secrets, or transmission to an
  external service → **Red**
- editing only a version description in README (no dependency actually
  changed) → **Green**

## 8. "Synthetic-only" is not a tier

"Synthetic-only" describes the test data, not the risk of the code change. It
never converts a code change into Green on its own.

- a bugfix in research machinery or runtime code is **Amber**, even when it is
  verified exclusively with synthetic tests
- adding tests only, with no change to production or research code, is a
  **Green candidate** — it still has to clear the §4 conditions
- a test change that alters a frozen contract, the acceptance criteria, or
  evidence semantics is **Amber**

## 9. One irreversible gate per task

The old rule ("never advance more than one gate in a single task") is replaced
by:

- At most **one irreversible research gate** per task.
- Within one gate, investigation, implementation, tests, CI repair and PR
  updates are a single unit of work and are done autonomously.
- Reversible incidental work — lint fixes, test fixes, conflict resolution,
  updating a stale document in the same scope — does not count as a gate.
- Distinct irreversible research stages must never be chained automatically.
  In particular: real-data read → training, and validation → holdout, are
  separate gates and each needs its own approval.

## 10. Head SHA changes

**Before merge approval.** The AI may amend the PR freely within the approved
scope and push new heads until CI is green. It does **not** stop and report on
every head change. It reports the final green head SHA as the review target.

**After merge approval.** If the head SHA changes after approval was given,
the approval is void: do not merge, and request re-review of the new head. The
approval is likewise void if the AI added changes beyond the approved scope,
whatever the head SHA says.

## 11. When to stop

Stop and ask for a human + ChatGPT decision only when:

1. the work requires an operation above the task's authorised risk tier;
2. it requires newly touching real data, credentials, a holdout, a broker, or
   production;
3. it requires changing a frozen contract;
4. it could invalidate or overwrite existing evidence;
5. it needs a human business decision or a change of research hypothesis;
6. there is a significant security risk;
7. the objective is self-contradictory and no reasonable conservative reading
   makes it actionable.

**Do not stop merely because:** several ordinary implementation options exist;
a minor dependency judgement is needed; more tests are needed; CI failed; the
PR head changed before approval; a stale document in the same scope needs
fixing; or a small inconsistency exists in the surrounding code. Resolve these
autonomously and record what was decided.

Discovering that a task is Amber or Red when it was described as Green is also
**not** a stop: do the work, then hold at "PR open, awaiting approval" and
report the reclassification.

When stopping, state the specific trigger from the list above, report what was
completed, and leave the tree in a clean state.

## 12. Independent audit

Audits are defined by their function, not by which model performs them. The
required roles are:

- **independent adversarial review**
- **independent source-audit re-check**
- **independent post-run audit**

"Independent" means:

- performed in a **session separate** from the one that produced the work;
- the auditor **re-reads the source and the diff** rather than reasoning from
  the implementing session's conclusions or its fix report;
- the **same model product may be used** — independence is about the session
  and the reading, not the vendor;
- **self-review by the implementing session does not satisfy it**, however
  thorough that self-review was.

**An AI that performed an audit may not itself give final approval for an
Amber or Red gate.** Final approval is a human + ChatGPT decision.

Historical audit records — their document names, PR numbers, statuses, and the
model that actually performed them — are facts and must not be rewritten.

## 13. Multi-agent internal audit loop

A session that implements a change and then reviews its own work checks it
with the same assumptions that produced it. Where the environment offers
subagents, the lead agent therefore splits the work across specialised roles
and has the result attacked before reporting it.

**This does not replace human + ChatGPT approval for Amber or Red.** Running
an internal audit loop is evidence that the work was scrutinised; it is not an
authorisation, and the number of agents used is never an argument that a
change is safe or that a gate may advance.

### 13.1 Roles

The lead agent may create specialised subagents sized to the work and its
risk. Typical roles:

- implementation / change author
- specification and contract consistency
- tests and boundary conditions
- security and forbidden routes
- data contamination and leakage
- CI and dependencies
- adversarial review / refutation
- final integration

Not every task needs every role. The lead selects the roles the change
actually warrants.

### 13.2 Independence of audit subagents

- Give each audit subagent the target source, diff and contract — **not** the
  other subagents' conclusions.
- Never adopt the implementer's own explanation or self-assessment as fact.
- At least one subagent must work **from the position that the change is
  wrong**, hunting for blockers.
- At least one subagent must hunt for **boundary conditions and bypass routes
  the tests do not cover**.
- When subagents disagree, the lead does **not** take a majority vote: it
  compares the reasoning and resolves the disagreement on the evidence.
- A material disagreement that cannot be resolved is reported as a blocker.

### 13.3 The loop

1. The lead confirms the current position, objective, risk tier and hard
   boundaries.
2. The lead splits the work across the appropriate specialised roles.
3. The implementation role produces the change.
4. Independent audit roles re-read the source, diff, tests and contract.
5. Audit roles classify each finding as **blocker**, **required fix**,
   **non-blocking observation**, or **accepted**.
6. Blockers and required fixes are fixed by the implementation role, within
   the same scope.
7. After the fix, re-verify with a **different** audit subagent, or in a fresh
   audit context that does not inherit the first conclusions.
8. Run CI and the tests the change warrants.
9. While CI failures or unresolved audit findings remain, iterate — fix and
   re-audit — inside the authorised gate.
10. Report only the final head, once every required fix is resolved and CI is
    green.

Head changes during this loop are **not** a reason to stop, as long as merge
approval has not yet been given (§10).

### 13.4 Loop exit conditions

The lead may not call a task complete until all of these hold:

- [ ] the implementation or document change matches the objective
- [ ] the change stays inside its risk tier
- [ ] protected path / protected action classification is settled (§2–§3)
- [ ] the tests the change warrants pass
- [ ] CI is green
- [ ] an independent adversarial review has been completed
- [ ] no blocker remains — or the remaining blockers are stated explicitly and
      the task stops
- [ ] disagreements between implementation and audit roles are resolved
- [ ] the final diff contains nothing unrelated to the objective
- [ ] no automatic advance to the next irreversible gate

### 13.5 Per-tier application

**Green.** Subagents are not mandatory for a small change. Use at least one
independent review role when the change: touches several files; fixed a CI
failure; might indirectly affect dependencies or tooling; involved a rebase or
conflict resolution; will be self-merged; or grew beyond the diff originally
expected. **Before any Green self-merge, confirm the §4 allowlist conditions
and protected-path non-contact in a review context separate from the lead.**

**Amber.** Where subagents are available, separate at least three roles:
implementation / authoring; contract, specification and data-boundary audit;
adversarial test and bypass-route audit. For a source audit or a post-run
audit, the auditing session or subagent must be different from the one that
implemented the target (§12). An Amber PR is **never** self-merged, however
complete the internal loop was — submit the final green head for human +
ChatGPT approval.

**Red.** Explicit approval before execution remains mandatory. After approval,
separate where possible: execution; evidence verification; contract-deviation
monitoring. Never treat the existence of multiple agents as a substitute for
the execution approval or as validation of the result. No automatic advance to
the next Red gate.

### 13.6 When subagents are unavailable

Do not stop. Instead:

- run the independent review perspectives **sequentially**;
- in each pass, re-read the source and diff, staying off the previous pass's
  conclusions as far as possible;
- keep implementation review, contract review and adversarial review clearly
  separate;
- state in the final report that subagents were unavailable and describe the
  substitute procedure.

The two mandatory perspectives of §13.2 do **not** become optional here: one
pass must still argue the change is wrong, and one must still hunt boundary
conditions and bypass routes the tests do not cover. Unavailable subagents
change how the perspectives are run, never whether they are run.

### 13.7 The lead agent's responsibility

The lead is not a vote counter for its subagents. It is responsible for: task
decomposition; choosing the roles; checking the evidence behind each finding;
merging duplicate findings; resolving contradictory ones; prioritising fixes;
preventing scope creep; reviewing the final diff; confirming the final risk
classification; and the final report.

The lead must not adopt a subagent's error, omission or over-correction
unexamined. A finding is acted on because its reasoning holds, not because a
subagent raised it.

### 13.8 What to record

State briefly, in the PR body or the final report:

- the roles used
- each role's main findings
- blockers and required fixes
- the result of re-auditing after the fixes
- any unresolved disagreement
- the substitute review procedure, if subagents were unavailable

Do not archive long internal transcripts or chains of reasoning — keep the
conclusions, the evidence for them, and what was changed.

## 14. Task prompt contract

A task prompt needs only these five fields:

1. **Current position** — master SHA and what has just landed
2. **Objective** — what this task should achieve
3. **Risk tier** — the requester's expectation; the AI re-derives it from §2–§8
   and applies the higher of the two
4. **Hard boundaries** — what must not be crossed
5. **Completion criteria** — what "done" means

Prompts do not need to repeat test lists, forbidden-label lists, full status
vocabularies or file inventories. The AI reads `CLAUDE.md`, this policy and
the playbook, and selects the checks the task actually warrants. When a prompt
omits something these documents specify, the documents apply anyway.

## 15. Recording an autonomous Green merge

When the AI merges a Green PR on its own authority, it records — after the
fact, with no prior approval needed:

- PR URL
- merge commit SHA
- risk classification (and why it is Green)
- touched files
- CI result
- which §4 allowlist entry the change matched
- confirmation that no protected path was touched
- confirmation that no next gate was started

## 16. Always-binding statuses

`PRODUCTION_READINESS_NOT_CLAIMED` and `NO_EXECUTION_PERFORMED` hold in every
task and every report. The forward epoch remains
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` until a
recorded human + ChatGPT ruling changes it. No session grants itself any of
these.
