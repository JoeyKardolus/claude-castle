# Castle bible

**This file is the single source of truth for the castle stack.** It grows with the system: when something load-bearing changes or gets decided, the relevant chapter here gets updated (the `grill` skill does this inline). Read the chapter you need, not the whole file. Chapter headings are stable slugs; link to them as `docs/bible.md#<slug-without-slashes>`.

## architecture/system-context

One picture in words, left to right:

**Your laptop** is where you work: you talk to Claude Code in this repo, and changes are pushed to **GitHub** on the `main` branch. GitHub is the hand-off point; nothing deploys from your laptop directly.

The **VM** (one cloud virtual machine, user `castle`, everything under `/opt/castle`) watches GitHub: an auto-deploy pull loop fetches new commits on `main` every few minutes and restarts what changed. On the VM, **Caddy** terminates HTTPS for `CASTLE_DOMAIN` (docs use `castle.example.com`) and routes each subdomain into the **compose stack**: the website, the notulen app, Nextcloud, and postgres, all containers defined in the root `docker-compose.yml`.

The VM itself runs at **Scaleway** (the cloud provider). Heavier GPU work, when needed, runs as separate Scaleway jobs (see `infra/gpu-jobs/`), not on the VM.

So: laptop -> GitHub -> VM (Caddy -> compose: website, notulen, nextcloud, postgres) -> Scaleway underneath.

## apps/notulen

The meeting-notes app, in `apps/notulen/`. You upload a meeting recording; a background worker turns it into written meeting notes; the notes land where you can read and share them (Nextcloud).

- The web part handles upload and status; the **worker** does the slow processing.
- State lives in postgres; files live in Nextcloud.
- It is one container in the compose stack, reachable on its own subdomain via Caddy.
- Failures must be visible: a job that dies shows an error state, never silently disappears.

## apps/website

The public website, in `apps/website/`. Served at the root of `CASTLE_DOMAIN` via Caddy. Static-first and boring on purpose: it should never be the reason the VM is busy. It is one container in the compose stack and redeploys automatically when `main` changes.

## infra/platform

The VM and everything that keeps it serving, in `infra/`:

- **`infra/caddy/`**: the Caddyfile. One place maps subdomains to containers. The domain is not hard-coded; it comes from `CASTLE_DOMAIN` in the env file (`config/castle.env.example` is the template).
- **`infra/auto-deploy/`**: the pull loop. A systemd timer runs a script that fetches `origin/main`, and if there are new commits, pulls and restarts the compose stack. Pushing to `main` IS the deploy; there is no separate release step.
- **`infra/systemd/`**: unit files for the timer and anything else that must survive a reboot.
- **`infra/docker/`**: shared container build bits.
- `setup.sh` at the repo root prepares a fresh VM once: Docker, Caddy, the timer, first start of the stack.

## infra/nextcloud

Nextcloud runs as a container in the compose stack (config in `infra/nextcloud/`), on its own subdomain. It is the file home of the stack: notulen output, shared documents, calendars.

- **2FA stance: required.** Every Nextcloud account has two-factor login enabled; no exceptions for admin accounts.
- Data lives in a named volume on the VM; back it up before risky changes.
- App store installs are kept minimal: fewer apps, fewer upgrade surprises.

## workflow/loop

How work happens in this repo, every conversation:

1. **grill**: Claude orients (soul, CLAUDE.md, CONTEXT.md, the relevant chapter here, guides/) and interviews the plan until it is sharp. Terms land in `CONTEXT.md`; decisions land here as short dated "Decision:" notes in the relevant chapter.
2. **to-prd**: the aligned plan becomes one GitHub issue with the `PRD` label (Goal, What, Status, Tasks, Done when, Owner).
3. **to-issues** (only if needed): a task someone can pick up independently gets its own linked sub-issue.
4. **code**: build it, minimal changes, reuse first.
5. **close**: ship (push to `main` = deploy), record where the PRD stands, park loose ends under a PRD, close the issue only when its Done-when list is genuinely met.

Commits are imperative and scoped: `module: description`. Memory (`.claude/memory/`) is auto-committed by a hook so nothing is lost between sessions.
