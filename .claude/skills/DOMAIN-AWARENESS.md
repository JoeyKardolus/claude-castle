# Domain Awareness

Consumer rules for any skill that explores this codebase. Producer rules (writing to the glossary, recording decisions) live in the `grill` skill.

## Before exploring, read these

- **`CONTEXT.md`** (repo root): the shared glossary. It picks the canonical term for each concept and lists `_Avoid_:` aliases.
- **The relevant `docs/bible.md` chapter**: pick from the chapter map in root `CLAUDE.md`. Read only the chapter(s) the prompt touches, not the whole file.

If these have no content for your topic, **proceed silently**. Don't flag absence; don't suggest creating something upfront. The producer skill (`grill`) creates entries lazily when terms or decisions actually get resolved.

## One glossary, one bible

This repo uses one bible file (`docs/bible.md`) and one glossary (`CONTEXT.md` at the root). Decisions live as short dated "Decision:" notes inside the relevant bible chapter.

## Use the glossary's vocabulary

When your output names a domain concept (issue title, refactor proposal, hypothesis, test name, agent prompt), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids (the `_Avoid_:` line).

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it; the next `grill` session will fill it).

## Flag decision conflicts

If your output contradicts a recorded decision in the bible, surface it explicitly rather than silently overriding:

> _Contradicts the decision in `infra/platform` about X, but worth reopening because..._

Only surface a conflict when the friction is real enough to warrant revisiting the decision.

## Skills that obey this contract

- `grill` (producer + consumer)
- `to-prd`
- `to-issues`
- `improve-codebase-architecture`
- `zoom-out`
- `diagnose`
- `prototype`
- `handoff`
- `tdd`

If you're writing a new skill that explores code, link this file as the first reference.
