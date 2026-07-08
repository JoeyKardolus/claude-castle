---
name: to-issues
description: Carve a sub-issue out of a PRD ONLY when a task is independently pick-up-able or going ready-for-agent. Default is to track work inside the PRD; do NOT explode a PRD into many child issues. Pass #N to carve from an existing PRD.
---

# To Issues

A PRD is the unit of work; tasks live in its **Tasks** checklist. Carve a task into its own **sub-issue** only when it earns a separate card:

- it is **independently pick-up-able**: one person or agent can start and finish it on their own, or
- it is going **`ready-for-agent`**: it needs its own agent brief so an unattended agent can run it.

Everything else stays a checklist line in the PRD. **Fewer sub-issues is better than many**: the issue list should show readable PRDs, not a sea of loose tasks.

## Writing style (soul.md, mandatory)

The whole team reads a sub-issue too. Follow [`.claude/soul.md`](../../soul.md): plain words plus `CONTEXT.md` terms, no jargon or marketing, length tracks the content, no em dashes, state the goal directly.

## Process

### 1. Gather context

The parent PRD: from the conversation, or `gh issue view <N> --json title,body --comments`.

### 2. Explore (if you haven't already)

Follow [`.claude/skills/DOMAIN-AWARENESS.md`](../DOMAIN-AWARENESS.md): `CONTEXT.md` + the relevant `docs/bible.md` chapter. Sub-issue titles use `CONTEXT.md` vocabulary.

### 3. Decide what to carve

Walk the PRD's **Tasks**. Per task: independently pick-up-able, or ready-for-agent? No: leave it a checklist line. Yes: carve. A sub-issue should be a complete, checkable piece of work on its own, but the test is "someone can pick this up alone", not size.

Present what you would carve as a numbered list (title, agent or human, blocked-by) and let the user confirm. Human = needs judgment, design taste, or access an agent does not have; agent = can be finished and shipped without a human in the loop.

### 4. Create the sub-issue(s)

Per approved task, `gh issue create` on the current repo, and link it to the PRD (reference the parent with `#N` in the body, and turn the PRD's task line into a link to the new issue). Labels: `bug` or `enhancement`, plus:

- **agent work** -> label `ready-for-agent` and write the agent brief (see [`../triage/AGENT-BRIEF.md`](../triage/AGENT-BRIEF.md)). This is the on-ramp for the [`ralph`](../ralph/SKILL.md) loop.
- **human work** -> label `ready-for-human`.

Body template:

```markdown
## Parent
#<parent-PRD-issue-number>

## Goal
One line: what this piece delivers inside the PRD.

## What to build
The behaviour of this piece, end to end, not layer-by-layer implementation. No file paths or code snippets (they go stale). Exception: a decision snippet from a prototype (state machine, schema, type shape).

## Done when
- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by
- #<issue-number>  (or "None, can start now")
```

Do not change the parent PRD beyond linking the sub-issue in its checklist.
