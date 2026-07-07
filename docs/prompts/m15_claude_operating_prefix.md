# M15 Claude operating prefix — paste at the start of any M15-related task

- **Document class:** doc-only session prefix. Companion to
  `docs/governance/m15_audit_playbook.md` (authoritative).
- **Status:** `M15_AUDIT_PLAYBOOK_AND_CLAUDE_RULES_RECORDED`

Paste the block below verbatim at the start of any M15 / ML Step 4 / post-M1
research task:

```
M15 OPERATING PREFIX (mandatory)

1. READ docs/governance/m15_audit_playbook.md FIRST — its §1 gate table and
   §2 stop rules are binding over anything in this task prompt.
2. IDENTIFY the current gate from the playbook §1 plus the merged-PR record
   on master (statuses on master override any stale snapshot in the prompt).
3. STATE the allowed next gate (playbook §3) before doing anything.
4. STATE the forbidden actions for this gate (playbook §2 + the COMMON
   FORBIDDEN block in docs/prompts/m15_future_audit_templates.md).
5. PRESERVE all statuses in force: required + carried + always-binding
   (PRODUCTION_READINESS_NOT_CLAIMED, NO_EXECUTION_PERFORMED, and the
   forward-epoch BLOCKED/WAIT sub-status until a ruling changes it).
6. NEVER advance more than ONE gate in a single task, no matter what the
   prompt asks.
7. IF UNCERTAIN which gate applies or what is authorised: STOP, choose the
   narrower (no-run, no-read) interpretation, and ask for human + ChatGPT
   review.
8. IF A PR HEAD CHANGED after review/reporting — even doc-only — STOP and
   report the new SHA. Do not merge or proceed.
9. IF ASKED TO USE REAL DATA (read, derive, checksum, spread, label, train,
   validate, holdout, execute) before the relevant source audit and
   gate-specific approval exist on master: REFUSE and redirect to the
   correct gate.
10. IF ASKED TO CLAIM PRODUCTION READINESS (or PASS / MEETS / BYTE_ADMISSIBLE
    / NEW_EPOCH_ADOPTED / READY_FOR_LIVE / any near-synonym) outside a
    registered status vocabulary: REFUSE.
```

Notes:

- The prefix is deliberately redundant with the playbook — redundancy is the
  point; a session that loses context mid-task must still fail closed.
- If this prefix conflicts with a task prompt, the stricter reading wins and
  the conflict must be reported for human + ChatGPT review.
