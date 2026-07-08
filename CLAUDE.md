# CLAUDE.md

## Persona

Read [`.claude/soul.md`](.claude/soul.md) for voice and hard rules. Match it. The owner can edit that file to change Claude's voice.

## Workflow protocol, every conversation in this repo

**On the first user message in any conversation, invoke the [`grill`](.claude/skills/grill/) skill before generating any response.** No exceptions: debug questions, support requests, research, brainstorms, all go through grill. Grill itself decides whether to explore the codebase first, ask the user, or both.

The flow is fixed: **grill -> to-prd -> (to-issues if a task needs its own issue) -> code -> [`close`](.claude/skills/close/)** (end the session cleanly: ship, record where the PRD stands, close the issue only when its work is actually done). If the first message contains `#N` or a GitHub issue URL, `to-prd` runs in resume mode: re-align against the existing issue, amend if it drifted, then code.

Four mechanism types make this loop work, one job each:

- **skills** (`.claude/skills/`): step-by-step methods, invoked as `/<name>`;
- **hooks** (`.claude/settings.json`): automation that fires on harness events;
- **memory** (`.claude/memory/`): notes that survive between conversations;
- **GitHub issues**: the durable backlog (PRDs and sub-issues).

## Chapter map (use during grill orient phase)

Topic to bible chapter. Read the chapters the prompt touches before asking the user anything.

| Topic | Where |
|---|---|
| Big picture, what runs where | `docs/bible.md#architecturesystem-context` |
| Meeting-notes app | `docs/bible.md#appsnotulen` |
| Website | `docs/bible.md#appswebsite` |
| VM, Caddy, auto-deploy, systemd | `docs/bible.md#infraplatform` |
| Nextcloud (files, 2FA) | `docs/bible.md#infranextcloud` |
| How we work (this loop) | `docs/bible.md#workflowloop` |
| Step-by-step how-tos | `guides/` |
| Reusable prompts (playbooks) | `prompts/` |
| Glossary (canonical terms + `_Avoid_` aliases) | `CONTEXT.md` (repo root) |

**The glossary is the working surface.** Every term in `CONTEXT.md` has `_Avoid_:` aliases. When you reach for a project word in any output (issue title, plan, test name), use the canonical term. Skills that explore the codebase obey [`.claude/skills/DOMAIN-AWARENESS.md`](.claude/skills/DOMAIN-AWARENESS.md). The `grill` skill writes glossary updates to `CONTEXT.md` and decision notes to `docs/bible.md` as terms get sharpened or trade-offs get decided.

## Rules

- **Branch**: `main` only. Push directly to `origin/main`; no feature branches, no PRs.
- **No fake data**: if something doesn't work, say so. No mock or made-up output.
- **Minimal changes**: don't refactor, rename, or "improve" code beyond what was asked.
- **Search before building**: reuse what's in the repo and official docs first; ask before building something custom.
- **Commits**: imperative, scoped, format `module: description` (e.g. `notulen: fix upload timeout`).
- **One function, one purpose**: functions doing more than one thing get split.
- **Delete dead code**: stubs, unused exports, "we might need it" leftovers all go.
- **Documentation** lives in `docs/` (system truth) and `guides/` (how-tos). Don't create new `.md` files elsewhere, except `CLAUDE.md`, `CONTEXT.md`, `README.md`, and files under `.claude/` or `prompts/`.

## Deployment

- Pushing to `main` IS the deploy. A pull loop on the VM (see `infra/auto-deploy/`) picks up new commits within a few minutes and restarts the compose stack.
- The runtime domain comes from the `CASTLE_DOMAIN` variable in the env file (`config/castle.env.example` is the template). Docs use `castle.example.com` as the example.

## Autonomy boundaries

- Don't continue into adjacent work after the requested task is done. Stop and wait.
- When something fails repeatedly, propose stopping or investigating; don't passively retry.

## Where the rest lives

- **[`docs/bible.md`](docs/bible.md)**: single source of truth for the system. Read the relevant chapter, not the whole file.
- **[`guides/`](guides/)**: step-by-step how-tos for humans.
- **[`prompts/`](prompts/)**: playbooks, reusable prompts to paste into Claude.
