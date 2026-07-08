---
name: write-a-skill
description: Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new skill for this repo.
---

# Writing Skills

## Process

1. **Gather requirements** - ask user about:
   - What task/domain does the skill cover?
   - What specific use cases should it handle?
   - Does it need executable scripts or just instructions?
   - Any reference materials to include?
   - Should it be model-invocable, or `disable-model-invocation: true` (user-only)?

2. **Draft the skill** - create:
   - `SKILL.md` with concise instructions (≤100 lines)
   - Additional reference files if content exceeds 100 lines
   - Utility scripts if deterministic operations needed

3. **Review with user** - present draft and ask:
   - Does this cover your use cases?
   - Anything missing or unclear?
   - Should any section be more/less detailed?

## Skill Structure

```
.claude/skills/<skill-name>/
├── SKILL.md           # Main instructions (required)
├── REFERENCE.md       # Detailed docs (if needed)
├── EXAMPLES.md        # Usage examples (if needed)
└── scripts/           # Utility scripts (if needed)
    └── helper.sh
```

## SKILL.md Template

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
---

# Skill Name

[Quick start: minimal working example]

## Workflows

[Step-by-step processes with checklists for complex tasks]

## Advanced features

[Link to separate files: See REFERENCE.md]
```

## Description Requirements

The description is **the only thing the agent sees** when deciding which skill to load. It's surfaced in the system prompt alongside all other installed skills. The agent reads these descriptions and picks the relevant skill based on the user's request.

**Goal**: Give the agent just enough info to know:

1. What capability this skill provides
2. When/why to trigger it (specific keywords, contexts, file types)

**Format**:

- Max 1024 chars
- Write in third person
- First sentence: what it does
- Second sentence: "Use when [specific triggers]"

**Good example**:

```
Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test. Use when user says "diagnose this" / "debug this", reports a bug, says something is broken/throwing/failing, or describes a performance regression.
```

**Bad example**:

```
Helps with debugging.
```

## Repo-specific rules

- All exploration skills must reference [`../DOMAIN-AWARENESS.md`](../DOMAIN-AWARENESS.md) before exploring code.
- Skill bodies should not duplicate bible content; link to bible chapters via the chapter map in root `CLAUDE.md`.
- For producer skills (writing to the bible or glossary), follow the inline-write triggers in the `grill` skill.

## When to Add Scripts

Add utility scripts when:

- Operation is deterministic (validation, formatting)
- Same code would be generated repeatedly
- Errors need explicit handling

Scripts save tokens and improve reliability vs generated code.

## When to Split Files

Split into separate files when:

- `SKILL.md` exceeds 100 lines
- Content has distinct domains
- Advanced features are rarely needed

## Review Checklist

After drafting, verify:

- [ ] Description includes triggers ("Use when...")
- [ ] `SKILL.md` under 100 lines
- [ ] No time-sensitive info
- [ ] Consistent terminology (use CONTEXT.md vocabulary if domain-related)
- [ ] Concrete examples included
- [ ] References one level deep
