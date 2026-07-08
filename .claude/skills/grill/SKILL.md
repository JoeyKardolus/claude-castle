---
name: grill
description: Interview-the-plan session. You are on the team but remember nothing at conversation start. Orient first (the prompt, .claude/soul.md, CLAUDE.md, CONTEXT.md, the relevant docs/bible.md chapters, guides/), then interview the plan against the shared vocabulary, sharpening terms into CONTEXT.md and recording decisions in the bible as they crystallise. MUST be invoked on the first user message in any conversation in this repo.
---

# Grill

The default first step of every conversation. Interview the plan against what the project already knows, sharpen terminology into `CONTEXT.md`, and record real decisions in `docs/bible.md`, all inline as the conversation crystallises.

## Before asking anything (orient)

1. Read the user's prompt.
2. Read `.claude/soul.md` (voice + hard rules).
3. Read root `CLAUDE.md`.
4. Read `CONTEXT.md` (the shared glossary, repo root).
5. Decide which `docs/bible.md` chapters apply (chapter map in root `CLAUDE.md`). Read them.
6. Skim `guides/` for any guide that covers the topic.

If a question can be answered by exploring the codebase, explore instead of asking. Consume-rule in [`.claude/skills/DOMAIN-AWARENESS.md`](../DOMAIN-AWARENESS.md): read `CONTEXT.md` + the relevant bible chapter first.

## During the session

Interview the user about every aspect of the plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies one by one. For each question, give your recommended answer. **Ask one question at a time, waiting for the answer before the next.**

Keep it proportional: a small, clear request may need zero questions. Do not interrogate someone who just asked to fix a typo.

### Challenge against the glossary

When the user uses a term that conflicts with `CONTEXT.md`, call it out immediately. "CONTEXT.md defines _worker_ as X, but you seem to mean Y, which is it?"

### Sharpen fuzzy language

When the user uses a vague or overloaded term, propose a precise one. "You said _the server_: the VM itself, the Caddy proxy, or one of the compose containers? Those are different things."

### Discuss concrete scenarios

Stress-test the plan with specific scenarios. Invent edge cases that force precision about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. On a contradiction, surface it plainly and ask which is right.

## Inline writes (as you grill, not batched)

1. **A term gets sharpened**: edit `CONTEXT.md` to add or refine it, in the CONTEXT format (definition + `_Avoid_:` aliases), per [CONTEXT-FORMAT.md](CONTEXT-FORMAT.md). `CONTEXT.md` is glossary only; no implementation detail leaks in.
2. **A load-bearing fact is confirmed** ("uploads always land in Nextcloud first"): edit the relevant `docs/bible.md` chapter to state it.
3. **A real trade-off is decided** (hard to reverse, surprising, a genuine choice between options): add a short dated "Decision:" note to the relevant `docs/bible.md` chapter, 1-3 sentences.

Otherwise no write. Insight from conversation flows through grill; drift found in code gets fixed by hand.

## Routing on completion

When shared understanding is reached, invoke the next skill:

- **First message contained `#N` or a GitHub issue URL**: `to-prd` in resume mode (re-align against the existing issue body; amend if it drifted).
- **Otherwise**: `to-prd` (writes the aligned plan as a PRD issue), then `to-issues` only if a task truly needs its own issue.

The flow is always `grill -> to-prd -> (to-issues) -> code -> close`.
