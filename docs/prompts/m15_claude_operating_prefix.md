# Task contract — the short prefix for any M15 / research task

- **Document class:** doc-only session prefix. Companion to
  `docs/governance/autonomous_development_policy.md` (process authority) and
  `docs/governance/m15_audit_playbook.md` (research authority).
- **Status:** `M15_AUDIT_PLAYBOOK_AND_CLAUDE_RULES_RECORDED`

The rules live in the repository, not in the prompt. A task prompt only has to
say where we are and what this task is; the session reads `CLAUDE.md`, the
autonomous development policy and the playbook, and selects the checks the
task warrants. Prompts do **not** need to re-list tests, forbidden labels,
status vocabularies or file inventories — those apply whether or not they are
quoted.

Paste this block, filled in, at the start of a task:

```
TASK CONTRACT

1. CURRENT POSITION — master SHA; what just landed; anything in flight.
2. OBJECTIVE — what this task should achieve.
3. RISK TIER — the requester's expectation; the session re-derives it from
   autonomous_development_policy.md §2-§8 and applies the higher of the two.
4. HARD BOUNDARIES — what must not be crossed in this task.
5. COMPLETION CRITERIA — what "done" means, and whether to merge or stop.
6. TRACK — Track A (exploratory) or Track B (formal confirmation), for any
   M15 Family A research task.
```

**Field 6 — the track, and its default.** M15 Family A research is split
(`docs/design/m15_minimum_research_gate.md` §8.11–§8.13). Which track a task
belongs to changes what is permitted, so a prompt that does not say is
**Track B** — the stricter side, currently blocked on the forward epoch. That
default is this repository's addition, recorded in `CLAUDE.md`; it is not a
clause of the contract packet.

A Track A task is **Red** and needs, in order: PR #451 approved and merged; the
P-1…P-15 propagation predicate true on a named master SHA; the **Minimum
Research Execution Gate** passed on a named head
(`docs/design/m15_track_a_execution_gate.md`); and then a separate explicit
human + ChatGPT read grant. Naming Track A in field 6 authorises none of them,
and R1 / R3 / R4 are three separate Red gates.

What the session does with it:

1. Read `CLAUDE.md`, the autonomous development policy, and the playbook §1
   gate table. **Master is the source of truth** — if the prompt's "current
   position" disagrees with master, master wins; say so in the report.
2. State the gate this task sits in, the risk tier, and what is out of bounds.
3. Work autonomously inside that tier: investigate, implement, test, fix lint
   and CI, open and amend the PR until CI is green. Pick the most conservative
   reasonable option where several exist and record why.
4. Run the internal audit loop (policy §13): split the work across specialised
   roles where subagents exist — Amber needs at least author, contract/
   data-boundary audit and adversarial/bypass audit — give each audit role the
   source and diff rather than the other roles' conclusions, fix blockers and
   required fixes in scope, re-verify in a fresh audit context, and iterate to
   CI green. Sequential separated passes are the fallback when subagents are
   unavailable; say so in the report.
5. Keep it to **one PR** while the work shares one objective, one risk tier
   and one revert unit (policy §14) — implementation, tests, docs, stale-state
   refreshes, CI repair and the internal audit's required fixes all belong in
   the same PR, amended to the final green head. Open a Gate-decision PR only
   when a contract or the research state is formally changed or judged, and an
   Execution-evidence PR only for a post-approval irreversible run.
6. Stop only for a policy §11 trigger or a playbook §2 research boundary — not
   for a design choice, a CI failure, or a pre-approval head change.
7. Report the final green head SHA, the roles used and their main findings,
   what was decided and why, and the residual risk. Merge only if the tier and
   the completion criteria allow it.

Notes:

- If the prompt and the repository documents conflict, the documents win and
  the stricter reading of a research restriction wins; report the conflict.
- Statuses in force apply without being quoted: always-binding
  `PRODUCTION_READINESS_NOT_CLAIMED`, plus the forward-epoch
  `..._BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS` sub-status until a recorded
  ruling changes it. `NO_EXECUTION_PERFORMED` and `NO_REAL_DATA_READ_PERFORMED`
  were discharged **for Track A R1's authorised scope only** on 2026-09-05
  (`docs/governance/m15_track_a_r1_execution_record.md`) and bind for every other
  read, stage and span.
- Never claim `PASS`, `MEETS`, `BYTE_ADMISSIBLE`, `NEW_EPOCH_ADOPTED`,
  `READY_FOR_LIVE`, production readiness or a near-synonym outside a
  registered status vocabulary.
