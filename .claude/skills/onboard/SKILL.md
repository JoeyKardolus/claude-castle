---
name: onboard
description: Take a fresh laptop to a fully running castle, autonomously. Installs the remaining tools, creates the Scaleway server, deploys the stack, sets up Nextcloud with 2FA and notulen, and records the result in memory. Use when config/castle.env is missing, when the user says "set up my castle" or anything like it, or when setup looks only partly done (some castle.env fields empty, server missing, or a URL not responding). Resumes from wherever the previous run stopped.
---

# Onboard

You are setting up the castle for an absolute beginner. They have done the terminal part already (WSL, cloning the public upstream repo, uv, Claude Code) and now expect you to do everything else, including connecting them to GitHub and giving them their own private copy. You run with permissions skipped, so act, do not ask for permission to run commands.

## Voice

- Plain English. No jargon; if a technical word is unavoidable, explain it in the same breath ("DNS, the internet's phone book").
- Before each phase, one sentence saying what you are about to do and why. Then do it.
- No em dashes. Short sentences.

## Question budget

The entire setup asks the user at most these six things, and nothing else:

1. **The GitHub login moment**: they type a short code in the browser (and create a free account first if they have none; the login page offers it).
2. **"Do you own a domain name?"** No is a fine answer; the castle then uses free sslip.io names.
3. **The Scaleway API key** (exact click path is in the phase).
4. **The Anthropic API key** for notulen minutes. Explicitly skippable; everything else works without it.
5. **Names for their two Nextcloud accounts.**
6. **The moment they scan the 2FA QR codes** (you wait for them, twice, plus once for admin).

Everything else you decide and generate yourself: passwords, server type, region, bucket names, all of it. If you are tempted to ask anything outside this list, decide instead.

## How to run it

Work through the phases in [phases.md](phases.md), in order. Each phase is idempotent and starts with a detection check; if the check says the phase is already done, say so in half a sentence and move on. That is also how you resume a half-finished setup: run the phases from the top and let the checks skip the finished ones. Never track progress with a step counter.

| Phase | Does | Done when |
|---|---|---|
| 0 | Explain the plan | user has seen the 4-line overview |
| 1 | Laptop tools + GitHub | `gh auth status` ok, memory linked, origin is theirs |
| 2 | Scaleway CLI | `scw account project list` returns their project |
| 3 | config/castle.env | file exists, domain/region/repo/secrets filled |
| 4 | Create the server | instance `castle` running, SERVER_IP saved |
| 5 | DNS | all three names resolve to SERVER_IP |
| 6 | Deploy the stack | three URLs respond over HTTPS |
| 7 | Nextcloud + 2FA | two accounts enrolled, enforcement on |
| 8 | Notulen | bucket live, service healthy, test recording done or skipped |
| 9 | Finish | memory note written, daily loop explained |

## Safety rules

- Never print a generated password except the one time the user must store it (the notulen login, the Nextcloud temp passwords). Never repeat it later; point at where it lives instead.
- Never commit `config/castle.env` or `/opt/castle/castle.env`. Git ignores the local one; keep it that way.
- If a phase fails twice in a row on the same error, stop. Explain in plain words what failed, what you tried, and what you would try next. Do not thrash.
- From the end of phase 6 onward, all ssh goes through the `castle` user, never root.
- Money: the server costs roughly 10 to 15 euros per month from the moment it exists. Say this once, in phase 0, and again right before creating it.
