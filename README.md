# Claude Castle

Your own castle on the internet, run by you and Claude.

This kit gives you, starting from zero, your own full stack:

- **Your own website** at your own domain, with automatic HTTPS.
- **Notulen**: record a meeting in the browser, get structured written minutes back.
- **Nextcloud**: your own private cloud storage (like Dropbox, but yours), with two-factor login enforced.
- **A Claude workday system**: Claude Code works inside this repo with skills, a memory that persists, and a fixed workflow (it interviews you first, writes a plan as a GitHub issue, builds it, then closes the session cleanly).

Everything runs on one small server you rent at Scaleway (a European cloud provider). You push changes to GitHub; the server picks them up and redeploys itself within about 2 minutes. **Push = deploy.**

## The one rule

You almost never type server commands yourself. You open Claude Code in this folder and paste a playbook from `prompts/`. Claude runs the commands, explains what it is doing, and asks before anything risky.

## Start here

1. Read [`guides/00-start-here.md`](guides/00-start-here.md). It walks you through everything in order.
2. Once the tools from guide 02 are installed, run:

```bash
./setup.sh
```

It checks your tools, asks a few questions (your domain, your GitHub name), and wires up Claude's memory.

## The map

| Folder | What it is |
|---|---|
| `guides/` | Step-by-step guides, start at 00 |
| `prompts/` | Playbooks you paste into Claude Code |
| `apps/website/` | Your website, edit and push |
| `apps/notulen/` | The meeting-minutes app |
| `infra/` | Server plumbing: Caddy, deploy loop, Nextcloud, systemd |
| `.claude/` | Claude's skills, voice (soul.md), and memory |
| `config/` | Your settings (`castle.env`), created by setup.sh |
| `docs/bible.md` | The single source of truth about your system |
| `CONTEXT.md` | Your glossary: what words mean here |

## What it costs

- Server: roughly 10 to 15 euro per month.
- Domain name: roughly 10 euro per year.
- Anthropic API key (used by notulen to write minutes): pay per use, typically cents per meeting. This is separate from your claude.ai subscription.

## Safety

Secrets (passwords, API keys) live only in `config/castle.env` on your laptop and `/opt/castle/castle.env` on the server. Both are ignored by git. Never paste a secret into a file that gets committed.
