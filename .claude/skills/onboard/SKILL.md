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

Work through the phases in [phases.md](phases.md). Each phase is idempotent and starts with a detection check; if the check says the phase is already done, say so in half a sentence and move on. That is also how you resume a half-finished setup: run the phases from the top and let the checks skip the finished ones. Never track progress with a step counter.

## Orchestration: front-load the human, then build in parallel

The user's part ends early; the build is yours alone. Run it in three blocks:

1. **The human block, phases 0 to 4 in order.** This holds every question except the phone QR codes: GitHub login, the domain question, the Scaleway key and card. While asking for the Scaleway key, also mention the one optional errand they can run in the meantime: getting the Anthropic key for meeting summaries (console.anthropic.com, skippable as always). After phase 4 the vault is filled and the server exists; tell them in one sentence: "I have everything I need; the next twenty minutes or so are all mine, I will call you when your cloud login is ready."
2. **The parallel block, zero user input.** Spread the independent work over subagents (the Agent tool, general-purpose) and run them CONCURRENTLY:
   - worker A: the fast-transcription engine's long pole, phase 9 steps: registry, worker image build on the temp instance, cluster creation;
   - worker B: the server stack, phases 5 and 6 end to end (DNS or sslip, provisioning, scoped key, deploy, watchdog, kubectl);
   - worker C: the recording storage, phase 8 storage steps (bucket, vault update for S3 values).
   Each worker gets the exact phase section as its instructions plus the shared facts (server IP, domain, region, vault pattern). You collect their results, then finish the GPU wiring (phase 9 remaining steps) yourself. If a worker fails twice, apply that phase's own fallback (CPU fallback for GPU, and so on) and keep the rest moving; one broken module never stalls the others.
3. **The closing human block.** Only now interrupt them again, once, with everything that needs their hands in one sitting: Nextcloud accounts and the QR codes (phase 7), the Anthropic key if they fetched it (phase 8 rest, with the live test recording), then finish (phase 10).

Between blocks, one sentence of progress. During the parallel block, at most one short update if something takes unusually long.

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

## Hands-free rule

The user NEVER runs a command. Every laptop tool installs without sudo into `~/.local/bin` (the phases say how); this session has no terminal for a password prompt, so any instruction that needs sudo on the laptop is a design bug, not something to hand to the user. If you genuinely hit a wall that only the user's password can pass: stop, say in one sentence what is needed and why, give exactly ONE copy-paste line, and say "paste this in your Ubuntu window (the black one from step 1), then tell me done". Never mention the `!` prefix or any terminal mechanics beyond paste-and-Enter.

## Safety rules

- Never print a generated password except the one time the user must store it (the notulen login, the Nextcloud temp passwords). Never repeat it later; point at where it lives instead.
- Secrets live in the vault (the Scaleway Secret Manager secret `castle-env`; see `infra/secrets/README.md`). `config/castle.env` holds settings only, never a secret; `/opt/castle/castle.env` is the VM's pulled cache. Never write secrets into either file by hand, never print vault content, and never commit either file (git ignores the local one; keep it that way).
- If a phase fails twice in a row on the same error, stop. Explain in plain words what failed, what you tried, and what you would try next. Do not thrash.
- From the end of phase 6 onward, all ssh goes through the `castle` user, never root.
- Money: the server costs roughly 10 to 15 euros per month from the moment it exists. Say this once, in phase 0, and again right before creating it. The GPU tier (phase 9) bills only while it is processing a recording, roughly 80 cents per hour of work, cents per meeting; say that right before creating the cluster.
