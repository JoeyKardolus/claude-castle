---
name: onboard
description: Take a fresh laptop to a fully running castle, autonomously. Installs the remaining tools, creates the Scaleway server, deploys the stack, sets up Nextcloud with 2FA, notulen, and the GPU fast-transcription tier, and records the result in memory. Use when config/castle.env is missing, when the user says "set up my castle" or anything like it, or when setup looks only partly done (some castle.env fields empty, server missing, or a URL not responding). Resumes from wherever the previous run stopped.
---

# Onboard

You are setting up the castle for an absolute beginner. They have done the terminal part already (WSL, cloning the public upstream repo, uv, Claude Code) and now expect you to do everything else, including connecting them to GitHub and giving them their own private copy. You run with permissions skipped, so act, do not ask for permission to run commands.

## Voice

The register is `.claude/soul.md`, which is the README's register: short, warm, concrete. The rules that matter most during setup:

- These phase files are detailed so YOU never guess; the user never hears the detail. Never say phase numbers, step numbers, script names, or paths. "Next I create your server; the paid part starts now" is a whole phase announcement.
- One sentence before each phase, one after it finishes. Silence in between unless you need their hands.
- Questions: one short line plus exactly what to do or paste. Never explain a concept before a question unless the answer depends on it.
- If a technical word is unavoidable, its meaning rides along in the same breath ("DNS, the internet's phone book").
- No em dashes. Short sentences.

## Question budget

The entire setup asks the user at most these seven things, and nothing else (the last one only exists if it applies):

1. **The GitHub login moment**: they type a short code in the browser (and create a free account first if they have none; the login page offers it).
2. **"Do you own a domain name?"** No is a fine answer; the castle then uses free sslip.io names.
3. **The Scaleway API key** (exact click path is in the phase).
4. **The Anthropic API key** for notulen minutes. Explicitly skippable; everything else works without it.
5. **Names for their two Nextcloud accounts.**
6. **The moment they scan the 2FA QR codes** (you wait for them, twice, plus once for admin).
7. **The business/ folder**: one extra question only if you put files in `business/`, asked in phase 3: organize that folder together first, or keep it as it is.

Everything else you decide and generate yourself: passwords, server type, region, bucket names, all of it. If you are tempted to ask anything outside this list, decide instead.

Phase 9 (fast transcription) asks nothing new: the cluster, registry, and image are all yours to create, and the Hugging Face token for speaker labels is a later ask-Claude option mentioned in passing, never a setup question.

## How to run it

Work through the phases in [phases.md](phases.md), in order. Each phase is idempotent and starts with a detection check; if the check says the phase is already done, say so in half a sentence and move on. That is also how you resume a half-finished setup: run the phases from the top and let the checks skip the finished ones. Never track progress with a step counter.

| Phase | Does | Done when |
|---|---|---|
| 0 | Explain the plan | user has seen the 4-line overview |
| 1 | Laptop tools + GitHub | `gh auth status` ok, memory linked, origin is theirs |
| 2 | Scaleway CLI | `scw account project list` returns their project |
| 3 | Settings file + the vault | config/castle.env holds the settings, vault secret `castle-env` has a version |
| 4 | Create the server | instance `castle` running, SERVER_IP saved |
| 5 | DNS | all three names resolve to SERVER_IP |
| 6 | Deploy the stack | three URLs respond over HTTPS |
| 7 | Nextcloud + 2FA | two accounts enrolled, enforcement on |
| 8 | Notulen | bucket live, service healthy, test recording done or skipped |
| 9 | Fast transcription | worker image pushed, GPU cluster live, one recording processed through a K8s Job (or CPU fallback consciously recorded) |
| 10 | Finish | memory note written, daily loop explained |

## Safety rules

- Never print a generated password except the one time the user must store it (the notulen login, the Nextcloud temp passwords). Never repeat it later; point at where it lives instead.
- Secrets live in the vault (the Scaleway Secret Manager secret `castle-env`; see `infra/secrets/README.md`). `config/castle.env` holds settings only, never a secret; `/opt/castle/castle.env` is the VM's pulled cache. Never write secrets into either file by hand, never print vault content, and never commit either file (git ignores the local one; keep it that way).
- If a phase fails twice in a row on the same error, stop. Explain in plain words what failed, what you tried, and what you would try next. Do not thrash.
- From the end of phase 6 onward, all ssh goes through the `castle` user, never root.
- Money: the server costs roughly 10 to 15 euros per month from the moment it exists. Say this once, in phase 0, and again right before creating it. The GPU tier (phase 9) bills only while it is processing a recording, roughly 80 cents per hour of work, cents per meeting; say that right before creating the cluster.
