---
name: audit-dead-code
description: Hybrid mechanical+LLM dead-code audit. Runs vulture (Python), ts-prune (TS), shellcheck SC2034 (bash unused vars), then resolves false positives with an LLM pass over import sites. Use when user says "audit dead code" / "find unused code" / runs the skill mid-refactor; or after a deletion sweep to verify nothing leaked back. Read-only; emits a report, never deletes.
---

# Audit dead code

Three mechanical detectors plus one LLM resolver. Outputs a markdown report at `tmp/audit-dead-code-<sha>.md` with three sections: `## Dead`, `## Live`, `## Uncertain`.

The skill is read-only. Deletions are a separate step (the user reviews the `Dead` section, grep-confirms callers, and commits).

## Quick start

```bash
bash .claude/skills/audit-dead-code/scripts/run.sh
```

Output path is printed at the end. Re-runs on the same tree produce the same output (modulo `tmp/` filename SHA).

## Process

### 1. Mechanical pass

Three tools run; outputs land in `tmp/_audit-mechanical/`:

| Tool | Scope | Catches |
|---|---|---|
| `vulture` | `apps/**/*.py` + `lib/**/*.py` | unused functions, classes, vars, imports, attributes |
| `ts-prune` | any `apps/*` or `lib/*` package with a `package.json` | unused TypeScript exports |
| `shellcheck -i SC2034` | `infra/**/*.sh` | unused bash variables |

**Excluded by default**: `tests/`, generated code (migrations), `.venv/`, `node_modules/`, vendored code.

Vulture confidence threshold: `--min-confidence 80` (default). Below that is too noisy.

### 2. LLM resolve pass

For every flagged symbol, gather:

- The symbol's source file plus line range.
- `grep -rn` results across the repo (callers, string references, dynamic dispatch hints).
- Decorator context (`@register_*`, `@app.route`, `@pytest.fixture`).
- Framework registration signals (routes referenced by string, plugins registered by name, config-driven dispatch).

Prompt (per symbol): "is this dead, live, or uncertain?" with the gathered context. Verdict plus one-line reasoning per item.

Three buckets:
- **Dead**: confirmed no callers, no string refs, no framework dispatch. Safe to delete.
- **Live**: caller found (the mechanical tool was wrong). Don't delete.
- **Uncertain**: ambiguous (dynamic dispatch, runtime registration). Human eyeball needed.

### 3. Report

Output at `tmp/audit-dead-code-<HEAD-sha>.md`:

```markdown
# Dead-code audit, <SHA>, <date>

## Dead (N items, safe to delete)
- `apps/notulen/foo.py:42` -- `def _unused_helper()` -- no callers, no string refs.

## Live (N false positives, leave alone)
- `lib/dashkit/render.py:88` -- `register_renderer` -- flagged by vulture; called by name via the renderer registry.

## Uncertain (N items, human review)
- `apps/website/plugins.py:201` -- `LegacyExtractor` -- referenced in a `getattr` lookup; cannot prove dead or alive.
```

## Common false-positive patterns (LLM allow-list)

The resolver should NOT mark these as dead:
- Framework startup hooks invoked by app loading, not direct imports.
- Functions registered by string name in a registry.
- Pytest `conftest.py` fixtures, referenced by name in test signatures.
- Symbols re-exported in `__init__.py` for package consumers.
- Web route handlers referenced by decorator or URL config.
- Migrations, applied by name.

## Failure modes

- **Tool missing**: `vulture` / `ts-prune` not installed: script prints an install hint, exits non-zero.
- **No flagged items**: emits report with empty sections plus a `Nothing flagged, clean tree.` note.

## Out of scope

- Deletion. The skill never modifies code; it only reports.
- Test coverage gaps (use `pytest --cov` for that).
