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

An AI session may not expand its own authority. Changing this policy, the
playbook, or any other rule about what AI may do is itself an Amber change
(§3).

## 2. Risk tiers

Every task is Green, Amber or Red. If a task spans tiers, the highest tier
governs the whole task.

### Green — ordinary reversible development

Examples: lint, format, dependency pinning; CI repair; documentation updates;
adding tests; synthetic-only bug fixes; implementing behaviour that an
existing, already-agreed specification defines; rebases and conflict
resolution; prompt/template improvements; README updates; non-functional
refactoring.

The AI runs the whole loop autonomously — investigate, implement, test, open
the PR, fix CI, self-review at the final head — **and may merge**.

**Green work that still requires human review before merge** (open the PR,
report, do not merge):

- governance documents themselves, including this one
- the scope of AI authority
- security or credential handling
- a protected research contract (a frozen pre-registration, frozen thresholds,
  frozen acceptance criteria)
- the definition of what counts as evidence
- branch protection or the set of required CI checks

### Amber — research design and data-boundary work

Examples: aggregation; labels; features; cost model; effective-N; no-overlap
logic; the validation kill gate; dataset/epoch design; evidence schema;
tooling that will derive real data; source audits; post-run audits.

The AI autonomously investigates, implements, writes synthetic tests, probes
adversarially, opens the PR, fixes CI and prepares the final head.

**Merging an Amber PR, and advancing to the next research gate, requires
human + ChatGPT approval.**

### Red — irreversible or externally visible operations

Examples: the first real-data read; using credentials; external storage
operations; freezing a validation or holdout split; running validation;
evaluating a holdout; a training run; a rerun; paper or live trading; broker
connection; production routing; any production-readiness claim.

**A Red operation requires explicit human + ChatGPT approval before it runs.**

Inside an approved Red task the AI may execute, produce the evidence and
prepare the PR autonomously. It must **not** roll on to the next Red gate —
approval covers exactly the operation it names.

## 3. One irreversible gate per task

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

## 4. Head SHA changes

**Before merge approval.** The AI may amend the PR freely within the approved
scope and push new heads until CI is green. It does **not** stop and report on
every head change. It reports the final green head SHA as the review target.

**After merge approval.** If the head SHA changes after approval was given,
the approval is void: do not merge, and request re-review of the new head. The
approval is likewise void if the AI added changes beyond the approved scope,
whatever the head SHA says.

## 5. When to stop

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

When stopping, state the specific trigger from the list above, report what was
completed, and leave the tree in a clean state.

## 6. Model independence

Audits are defined by their function, not by which model performs them. The
required roles are:

- **independent adversarial review**
- **independent source-audit re-check**
- **independent post-run audit**

Any model with sufficient source-analysis capability — Claude Opus among them
— may perform them. "Independent" means the reviewing session is separate from
the session that produced the work under review, with its own reading of the
source; it does not name a vendor.

**An AI that performed an audit may not itself give final approval for an
Amber or Red gate.** Final approval is a human + ChatGPT decision.

Historical audit records — their document names, PR numbers, statuses, and the
model that actually performed them — are facts and must not be rewritten.

## 7. Task prompt contract

A task prompt needs only these five fields:

1. **Current position** — master SHA and what has just landed
2. **Objective** — what this task should achieve
3. **Risk tier** — Green, Amber or Red
4. **Hard boundaries** — what must not be crossed
5. **Completion criteria** — what "done" means

Prompts do not need to repeat test lists, forbidden-label lists, full status
vocabularies or file inventories. The AI reads `CLAUDE.md`, this policy and
the playbook, and selects the checks the task actually warrants. When a prompt
omits something these documents specify, the documents apply anyway.

## 8. Always-binding statuses

`PRODUCTION_READINESS_NOT_CLAIMED` and `NO_EXECUTION_PERFORMED` hold in every
task and every report. The forward epoch remains
`FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` until a
recorded human + ChatGPT ruling changes it. No session grants itself any of
these.
