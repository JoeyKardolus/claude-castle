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

## apps/documents

Business documents (invoices first, then quotes, letters, anything with the company's name on it) in the owner's house style, in `apps/documents/`.

- **In**: a document template (one directory per type), the design tokens (`design/tokens.css`, templates style only through `var(--...)`), the company profile (`design/company.yaml`), and a small data yaml with the content.
- **Out**: a PDF, via `uv run python -m documents <type> --data <file>.yaml --out <file>.pdf` (`--sample` renders with sample data).
- **Company profile intake**: the `business/` folder is where an existing company drops what it already has (old invoices, logo, registration extract); onboarding fills `design/company.yaml` and the brand colors from it, using only values literally found there. Official numbers are never guessed.
- **Sending is approval-then-send**: the owner sees the exact PDF and says yes before anything is emailed, every time. Mail goes out as transactional email through the Scaleway email API (`infra/email/send_document.py`); that needs the owner's real domain verified for sending, and free sslip.io names cannot send. The `make-document` skill (`.claude/skills/make-document/`) carries the whole flow.

## infra/platform

The VM and everything that keeps it serving, in `infra/`:

- **`infra/caddy/`**: the Caddyfile. One place maps subdomains to containers. The domain is not hard-coded; it comes from `CASTLE_DOMAIN` in the environment (`config/castle.env.example` documents every field).
- **`infra/secrets/`**: the vault. Secrets live in one Scaleway Secret Manager secret named `castle-env` holding the stack's full KEY=value environment; every change is a new version. `push-env.sh` (laptop) pushes a version; `pull-env.sh` (VM) fetches the latest with the scoped read-only key in `/opt/castle/scw-secrets.env` and atomically rewrites the cache at `/opt/castle/castle.env`, which compose reads via `--env-file`. The auto-deploy loop pulls every cycle and redeploys when the content changed, so rotation is push-a-version-and-wait, no ssh. On any fetch failure the pull keeps the existing cache and the stack keeps running. `config/castle.env` on the laptop keeps only non-secret settings (domain, region, repo, server IP, TEM sending settings).
- **`infra/auto-deploy/`**: the pull loop. A systemd timer runs a script that fetches `origin/main`, and if there are new commits or a new vault version, pulls and restarts the compose stack. Pushing to `main` IS the deploy; there is no separate release step.
- **`infra/systemd/`**: unit files for the timer and anything else that must survive a reboot.
- **`infra/docker/`**: shared container build bits.
- **`infra/watchdog/`**: hourly burn-and-health check on the VM (wedged GPU machines, stuck recordings, full disk, monthly spend past `CASTLE_BUDGET_EUR`). Alert-first: the server may read the bill, never change the account. Warnings: `journalctl -t castle-watchdog`, plus email when configured.
- The `onboard` skill (`.claude/skills/onboard/`) prepares a fresh VM once, driven by Claude: server creation, Docker, the env file, first start of the stack, the timer.

## infra/nextcloud

Nextcloud runs as a container in the compose stack (config in `infra/nextcloud/`), on its own subdomain. It is the file home of the stack: notulen output, shared documents, calendars.

- **2FA stance: required.** Every Nextcloud account has two-factor login enabled; no exceptions for admin accounts.
- Data lives in a named volume on the VM; back it up before risky changes.
- App store installs are kept minimal: fewer apps, fewer upgrade surprises.

**Cloud folder to GitHub sync** (`infra/nextcloud-sync/`, optional): anything a user drops in the "Sync" folder of their Nextcloud files also gets committed to the GitHub repo. Nextcloud's webhook_listeners app POSTs every file write/delete/rename to the internal `nextcloud-sync` container, which reads the file off the read-only Nextcloud data volume and commits it via the GitHub Contents API, authored as that Nextcloud user. Folder mapping: `/<user>/files/Sync/...` lands at `cloud-sync/<user>/...` on `main` (override with `NC_SYNC_FOLDER` / `SYNC_TARGET_DIR`). Secret model: one shared bearer token (`NEXTCLOUD_WEBHOOK_SECRET`) baked into the webhook registration, replayed by Nextcloud on every delivery, compared in constant time by the service; commits use a fine-grained GitHub token (`SYNC_GITHUB_PAT`, Contents read/write only). Register the listeners once with `infra/nextcloud-sync/register-webhooks.sh`; deliveries ride the Nextcloud cron container, so a sync lands within about ten minutes (live-tested: usually one or two cron cycles), not instantly.

## workflow/loop

How work happens in this repo, every conversation:

1. **grill**: Claude orients (soul, CLAUDE.md, CONTEXT.md, the relevant chapter here) and interviews the plan until it is sharp. Terms land in `CONTEXT.md`; decisions land here as short dated "Decision:" notes in the relevant chapter.
2. **to-prd**: the aligned plan becomes one GitHub issue with the `PRD` label (Goal, What, Status, Tasks, Done when, Owner).
3. **to-issues** (only if needed): a task someone can pick up independently gets its own linked sub-issue.
4. **code**: build it, minimal changes, reuse first.
5. **close**: ship (push to `main` = deploy), record where the PRD stands, park loose ends under a PRD, close the issue only when its Done-when list is genuinely met.

Commits are imperative and scoped: `module: description`. Memory (`.claude/memory/`) is auto-committed by a hook so nothing is lost between sessions.
