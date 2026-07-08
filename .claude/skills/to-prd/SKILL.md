---
name: to-prd
description: Turn the aligned grill output into one readable, goal-first PRD issue on this repo's GitHub. Synthesises from conversation context; does not re-interview. Resumes an existing PRD if the first message had #N or a GitHub URL. Always the next step after grill.
---

# To PRD

Produce ONE readable, goal-first **PRD** as a GitHub issue. Do NOT re-interview; grill already did that. This skill only synthesises and publishes.

A PRD is the unit of work: one issue with the `PRD` label that holds the goal, the scope, and a task checklist. Even a small plan becomes a PRD; its tasks live inside it as checklist lines, not as separate issues. Carve a task into its own issue only via [`to-issues`](../to-issues/SKILL.md), and only when it is independently pick-up-able.

**Two fields are mandatory; do not publish without both:**

1. **Done when**: a clear, checkable list that says when the PRD is finished. No vague "works well"; every line can be verified (a command, a file, a decision made).
2. **Owner**: one named person, never "?" and never a team. The owner is responsible for getting the PRD finished.

## Writing style (soul.md, mandatory)

The whole team reads a PRD, not just agents. Follow [`.claude/soul.md`](../../soul.md): plain words plus `CONTEXT.md` terms, no invented jargon, no marketing voice, length tracks the content, no em dashes, state the goal and decisions directly.

## Process

### 1. Resume mode (if applicable)

First message had `#N` or a GitHub issue URL: run `gh issue view <N> --json title,body,state --comments`, load the body, re-align it against the grill output, and amend with `gh issue edit` only if it drifted. Do NOT create a new issue. Then move on to the code phase.

### 2. Explore (if you haven't already)

Follow [`.claude/skills/DOMAIN-AWARENESS.md`](../DOMAIN-AWARENESS.md): read `CONTEXT.md` and the relevant `docs/bible.md` chapter first. Use `CONTEXT.md` vocabulary throughout the PRD.

### 3. Pick the shape

One PRD = one coherent piece of work (a feature, a fix campaign, a setup task). If the work spans several unrelated pieces, that is several PRDs, or you are at the wrong altitude: re-grill.

Check with the user that the boundary is right before publishing.

### 4. Publish

Before publishing, check the two mandatory fields: a checkable **Done when** list and a named **Owner**. Missing one: fill it in or ask the user; do not publish without.

Create the issue on the current repo (find it with `gh repo view --json nameWithOwner -q .nameWithOwner` if needed):

```bash
gh issue create --label PRD --assignee @me --title "<short imperative title>" --body-file <body>
```

Title under 70 characters, imperative, no emoji. `--assignee @me` assigns the authenticated GitHub user; if the owner is someone else, use their GitHub login instead. If the `PRD` label does not exist yet, create it once: `gh label create PRD --description "Product requirement / unit of work" --color 5319e7`. Print the issue URL when done.

Body template:

```markdown
## Goal
Why this exists and what it delivers, 2-3 sentences, plain language, readable by anyone.

## What
Scope: what is included, and explicitly what is not.

## Status
One line: where things stand right now.

## Tasks
- [ ] Task; small ones stay as checkboxes here; independently pick-up-able ones become a linked sub-issue via `to-issues`
- [ ] ...

## Done when
- [ ] Checkable criterion
- [ ] Checkable criterion

## Owner
<named person>
```

The **Done when** list is the definition of done; [`close`](../close/SKILL.md) reads it to decide whether the PRD can be closed.

### 5. Track under the PRD

Work is tracked IN this PRD: tick the **Tasks** checklist, post progress as comments, and create sub-issues only for pieces that someone can pick up independently (via [`to-issues`](../to-issues/SKILL.md)). Do not explode a PRD into child issues up front.
