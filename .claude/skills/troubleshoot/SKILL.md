---
name: troubleshoot
description: Investigate and fix a misbehaving castle. Gathers the facts from the server (running services, logs, auto-deploy state, disk, certificates), explains the finding in plain words, and fixes it after a yes. Use when anything sounds broken: the website is down, minutes never arrived, a login fails, an error appeared, "something is broken", or the user describes any behavior that does not match what they expected.
---

# Troubleshoot

The user may not be able to describe the problem technically. Ask them exactly one question: "What were you trying to do, and what did you see instead?" Then investigate yourself; never ask them to run anything.

## Gather the facts

Server address and domain are in `config/castle.env`; run remote commands over ssh as the `castle` user. Announce each step in one plain sentence before running it.

1. Is the server reachable at all? (`ping`, `ssh`). If not, check the instance state with `scw instance server list` before anything else.
2. On the server, in `/opt/castle/repo`: `docker compose --env-file /opt/castle/castle.env ps` to see which services are up, restarting, or gone.
3. For every service that is not healthy: `docker compose --env-file /opt/castle/castle.env logs --tail 50 <service>`.
4. Auto-deploy: `journalctl -u auto-deploy.service -n 30`, the log at `/tmp/castle-deploy.log`, and whether `/opt/castle/repo` matches the latest commit on GitHub (`/var/lib/castle/last-deployed-sha` holds the bookmark, `last-failed-sha` appears when a deploy broke).
5. Disk space (`df -h /`) and memory (`free -h`). A full disk is the most common silent killer.
6. HTTPS: does `https://<domain>` respond, and what do Caddy's recent logs say (`docker logs castle-caddy --tail 50`)?
7. Anything the user's description points at specifically. Notulen minutes missing: check the S3 bucket is reachable and the Anthropic key is valid.

## Report, then fix

- Explain what you found in plain words, two or three sentences, no jargon without a one-line explanation. If several things are wrong, name the root cause first.
- Propose the fix and what it will do, in one or two sentences, including whether anything will restart or be briefly offline.
- Apply the fix only after they say yes. Verify afterwards with the same check that first showed the problem, and show them it now passes.
- If you cannot find the cause, say so honestly, state what you ruled out, and suggest the next diagnostic step rather than guessing at fixes.

## Hard rules

- Never delete data as a fix without explicit, separate confirmation.
- Never print secrets from castle.env into the chat.
- End with a plain-words summary: what was broken, why, what changed, and how they can tell it is healthy now.
