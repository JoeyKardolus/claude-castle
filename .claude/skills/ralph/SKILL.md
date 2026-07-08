---
name: ralph
description: Autonomously work through the ready-for-agent queue. Pick the top ready-for-agent issue, implement it from its agent brief, verify the acceptance criteria and tests, ship, close, repeat. Use when the user wants to run ralph, clear the agent backlog unattended, or "run the agent loop".
---

# Ralph

The unattended execution loop on top of [`triage`](../triage/SKILL.md). Ralph empties the **`ready-for-agent`** queue: each such issue already carries a durable **agent brief** (its contract). Ralph implements them one by one, runs the checks that replace human review, ships, and moves on.

Ralph only runs work that triage already declared agent-safe. It never invents scope.

## What ralph picks

`label:ready-for-agent`, oldest first (FIFO). Skip:

- anything the brief says needs a human (mislabeled: relabel to `ready-for-human` and move on),
- anything `blocked by` an open issue.

Empty queue: stop and report.

## Per issue

1. **Read the contract.** The agent brief is leading; the issue body and discussion are context. Brief missing or too thin: relabel to `needs-triage`, comment why, next.
2. **Isolate.** Work in a fresh worktree (one issue = one worktree) so parallel or aborted runs do not pollute `main`.
3. **Build** the behaviour from the brief. Reuse existing modules; use `CONTEXT.md` vocabulary. No scope beyond the Done-when criteria.
4. **Checks** (these replace the human in the loop):
   - every **Done when** line of the issue,
   - the project's test suite (all green),
   - the relevant `audit-*` skills on what you touched.
   A check red: fix it, or if genuinely stuck after a real attempt, relabel to `ready-for-human` with notes. Never fake green.
5. **Ship.** Commit (scoped, imperative) and push to `main` (push is the deploy).
6. **Close.** Run [`close`](../close/SKILL.md) against the Done-when list; close the issue, tick the parent PRD checklist. Next.

## Guardrails

- **`main` only**, push = deploy. One issue at a time.
- **Stop conditions:** queue empty, repeated check failure on the same issue (propose stopping or investigating; do not loop forever or passively wait), or budget spent.
- `ready-for-human` is for real cases: human judgment, design taste, access an agent does not have, or irreversible-without-recovery steps. Not "it touches production".
- One summary line per issue (shipped / handed to human / skipped), so the run is auditable.
