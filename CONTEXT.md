# Castle glossary

The shared vocabulary for this project. One entry per concept: a tight definition (what it IS, one or two sentences) plus an `_Avoid_:` line listing words we do not use for it. Be opinionated: when several words exist for the same thing, pick one and park the rest under `_Avoid_`.

Add a term when a conversation sharpens one (the `grill` skill does this inline). Only project-specific concepts belong here; general programming words do not.

## Stack

**Castle**:
The whole self-hosted stack in this repo: the apps, the VM they run on, and the workflow around them.
_Avoid_: the system, the platform, the server (ambiguous)

**VM**:
The single cloud virtual machine (user `castle`, path `/opt/castle`) that runs everything. Its public name comes from the `CASTLE_DOMAIN` env variable.
_Avoid_: the box, the instance, the droplet

**Caddy**:
The web server on the VM that terminates HTTPS and routes each subdomain to the right container.
_Avoid_: the proxy, nginx

**Compose stack**:
The set of containers defined in the root `docker-compose.yml`: website, notulen, Nextcloud, postgres.
_Avoid_: the cluster, the services (unqualified)

**Auto-deploy**:
The pull loop on the VM (`infra/auto-deploy/`) that checks GitHub for new commits on `main` and restarts the compose stack. Pushing to `main` is the deploy.
_Avoid_: CI/CD, the pipeline, release process

**Nextcloud**:
The self-hosted file and calendar app in the compose stack; where uploads and shared files live.
_Avoid_: the drive, the cloud

**2FA**:
Two-factor login (password plus a code from your phone). Required on Nextcloud and GitHub accounts.
_Avoid_: MFA, two-step verification

## Apps

**Notulen**:
The meeting-notes app (`apps/notulen/`): upload a recording, get written meeting notes back.
_Avoid_: the transcriber, minutes app, meeting tool

**Worker**:
The background process inside notulen that takes an uploaded recording and turns it into notes. Not a person and not the VM.
_Avoid_: the job, the daemon, the processor

**Website**:
The public site (`apps/website/`) served at the root of `CASTLE_DOMAIN`.
_Avoid_: the frontend, the homepage (when you mean the whole app)

**Dashboard**:
A small status page built with dashkit (`lib/dashkit/`) that shows how a part of the stack is doing.
_Avoid_: admin panel, console

## Documents

**Design system**:
The one shared look for everything the castle produces (website, documents): colors, fonts, spacing, defined once under `design/`.
_Avoid_: branding, theme, style guide, house style (in code; fine in user-facing prose)

**Tokens**:
The named CSS custom properties in `design/tokens.css` (like `--color-primary`) that carry the design system. Templates style only through `var(--...)`; nothing hard-codes a color or font.
_Avoid_: CSS variables, theme values, style constants

**Company profile**:
The facts about the owner's company in `design/company.yaml`: name, address, registration and VAT numbers, IBAN, logo, colors. Documents pull from it; official numbers in it are never guessed, only copied from the owner's own papers or answers.
_Avoid_: company info, business details, company config

**Document template**:
The layout for one document type (invoice, quote, letter) under `apps/documents/`, combining the company profile, the tokens, and a data yaml into a PDF via `python -m documents`.
_Avoid_: form, layout file, invoice generator

**Transactional email**:
One-off mail the castle sends on the owner's behalf (an invoice to a client) through Scaleway's email API via `infra/email/send_document.py`. Needs a verified real domain; never sent without the owner approving the exact document.
_Avoid_: SMTP, mailer, newsletter, bulk mail

## Workflow

**Skill**:
A step-by-step method Claude can run, stored in `.claude/skills/<name>/SKILL.md`, invoked as `/<name>`.
_Avoid_: command, macro, plugin

**Hook**:
Automation in `.claude/settings.json` that fires on a harness event (session start, before a tool runs, on stop). Hooks run scripts; Claude cannot skip them.
_Avoid_: trigger, listener

**Overlay**:
A `CLAUDE.md` file inside a subdirectory; it loads automatically when files there are touched and adds area-specific instructions.
_Avoid_: local config, sub-CLAUDE

**Memory**:
Claude's notes that survive between conversations, stored in `.claude/memory/` and indexed one line per note in `MEMORY.md`.
_Avoid_: history, cache

**Grill**:
The interview-the-plan skill that starts every conversation: orient on the docs, then question the plan until it is sharp.
_Avoid_: intake, kickoff, discovery

**PRD**:
One GitHub issue with the `PRD` label that holds a unit of work: Goal, What, Status, Tasks, Done when, Owner. Tasks live inside it as a checklist.
_Avoid_: epic, ticket, story

**Onboard**:
The skill (`.claude/skills/onboard/`) that builds the castle from a fresh laptop: tools, server, deploy, Nextcloud, notulen, end to end. It runs automatically when `config/castle.env` is missing and resumes a half-finished setup by detecting state.
_Avoid_: setup script, installer, playbook, the wizard
