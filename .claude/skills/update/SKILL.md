---
name: update
description: Bring an already-set-up castle up to date with the latest improvements from the upstream project. Use when the user says "update", "update the castle", "get the latest improvements", "update the server and everything on it", or during the monthly maintenance ask.
---

# Update

The castle came from a public upstream project that keeps improving. This skill takes those improvements into the owner's own castle without losing anything they changed.

Voice per `.claude/soul.md`: tell them what is new in plain words, one or two sentences per meaningful change, never a raw commit list.

## Flow

1. **Fetch and compare.** `git fetch upstream` (phase 1 of setup left the public project as the `upstream` remote; if it is missing, add `https://github.com/JoeyKardolus/claude-castle.git` as `upstream`). `git log --oneline main..upstream/main` tells you what is new. Nothing new: say so in one line and stop.
2. **Tell them what they get.** Translate the new commits into owner language: "the meeting recorder got faster", "a safety watchdog was added", "the setup got simpler". Ask nothing; updating is why they called.
3. **Merge, protecting their things.** `git merge upstream/main`. On conflicts, their content wins in the folders that are theirs: `apps/website/`, `design/`, `business/`, `config/`, `.claude/memory/`, and any document templates they changed; the kit's machinery (`infra/`, `apps/notulen/`, `lib/`, `.claude/skills/`) takes the upstream side unless they customized it deliberately (check git log for their own commits touching it; when genuinely unsure, keep theirs and say so). Never lose a file they created.
4. **New settings check, before anything deploys.** Diff `config/castle.env.example` between the old and new version. Any NEW variable: decide its value (generate secrets with `openssl rand -hex 24`; ask the owner only if it is truly theirs to give), then add it to the vault via the standard pattern (fetch temp, edit, `infra/secrets/push-env.sh`). A new `:?`-required compose variable that is missing would stop the whole stack at the next deploy; this step exists so that can never happen.
5. **Local update.** `uv sync` so the laptop side matches. If `.claude/` changed, mention that new abilities apply from their next conversation.
6. **Ship.** Push to `origin main`. The server picks it up within about two minutes; watch one deploy cycle (`ssh castle@<SERVER_IP> journalctl -u auto-deploy.service -n 20 --no-pager` or check the site) and confirm everything still answers: the website, `cloud.`, `notulen.` (401 counts as alive).
7. **Report.** Two or three sentences: what arrived, that the castle is healthy, and anything that needs them (a new optional feature they could turn on).

## Safety rules

- Never force-push, never rebase their main; merge only.
- If the merge goes badly wrong, `git merge --abort`, tell them plainly, and leave the castle exactly as it was; a broken update must never take the running castle down (the server keeps running the last good version regardless).
- After the deploy, verify the three addresses respond before calling it done; if one broke, fix or revert before reporting success.
