# Onboard phases

Each phase: **Already done?** check first, then the work, then the **Verify** check. Announce each phase to the user in one plain sentence before starting it.

## Phase 0: explain the plan

Tell the user, in four lines, roughly this:

> I am going to set up your castle: a small server at Scaleway running your website, your private cloud storage, and the meeting recorder. It takes about half an hour of my work and a few minutes of yours. I will need two things from you along the way: a Scaleway API key (I will tell you exactly where to click) and, optionally, an Anthropic API key for the meeting minutes. The server costs roughly 10 to 15 euros per month; everything else is free or costs cents.

Then start phase 1 without waiting, unless they object.

## Phase 1: laptop tools and GitHub

**Already done?** `gh auth status` succeeds, `~/.claude/projects/.../memory` is a symlink into this repo, and origin looks like theirs. Then skip.

1. Verify `git --version`, `uv --version`, `claude --version` all print. These were installed by hand before this conversation; if one is missing, install it (git via apt/xcode-select, uv via the astral.sh install script) and say what you did.
2. If `git config user.name` or `user.email` is empty, set them from the GitHub account after login (step 4), using `gh api user` for the name and the noreply email if none is public.
3. Install the GitHub CLI if missing. Ubuntu/WSL: the official apt repo (keyring plus `apt install gh`). Mac: `brew install gh`. Warn first: "your computer will ask for your password now; that is the normal way it approves installing software".
4. Log in: `gh auth login --hostname github.com --git-protocol ssh --web`. Tell the user: a code appears, the browser opens, they type the code and click approve. That is all they do.
5. Run `bash .claude/bootstrap.sh` from the repo root. Explain in one sentence: this makes my notes about your setup live inside the project, so they survive and get backed up with everything else.
6. Check `git remote get-url origin`. Compare the owner part with `gh api user --jq .login`. If they differ, this is **question 1 of the budget**: show both names and ask if this copy is really theirs. If it is the upstream template, stop and help them make their own copy first (GitHub page of the template, "Use this template", private repo, then re-clone).

**Verify**: `gh auth status` ok; `git remote get-url origin` owner matches their GitHub login (or they confirmed it).

## Phase 2: Scaleway CLI

**Already done?** `scw account project list` returns a project table. Then skip.

1. Install scw if missing: `curl -sL https://raw.githubusercontent.com/scaleway/scaleway-cli/master/scripts/get.sh | sh`
2. **Question 3 of the budget**, ask for the API key with this exact path: "Go to console.scaleway.com, log in, click IAM in the left menu (or your name, then API keys), then API keys, then Generate API key. It shows an Access key and a Secret key. Copy both and paste them here. The secret is shown only once, so copy it before closing." If they have no Scaleway account yet, send them to scaleway.com to sign up and add a payment card first (Billing section), then come back for the key.
3. Configure non-interactively, never through `scw init`:
   - `scw config set access-key=<ACCESS> secret-key=<SECRET>`
   - `scw account project list` to find the project and organization IDs, then `scw config set default-project-id=<id> default-organization-id=<id> default-region=fr-par default-zone=fr-par-1`
   - Region is your decision, not a question: `fr-par` unless the user already said where they live and another Scaleway region is clearly closer.

**Verify**: `scw account project list` shows at least one project.

## Phase 3: config/castle.env

**Already done?** `config/castle.env` exists with non-placeholder CASTLE_DOMAIN, CASTLE_REGION, GITHUB_REPO, and non-empty POSTGRES_PASSWORD, NEXTCLOUD_DB_PASSWORD, NEXTCLOUD_ADMIN_PASSWORD. Then skip.

1. Copy `config/castle.env.example` to `config/castle.env` if it does not exist.
2. **Question 2 of the budget**: "Do you own a domain name (a web address like example.com)?"
   - **Yes**: use it as CASTLE_DOMAIN.
   - **No**: the castle gets free names from sslip.io, derived from the server's address, like `1-2-3-4.sslip.io` with `notulen.` and `cloud.` in front. Explain: these work immediately, nothing to buy or configure; they are just less pretty. Leave CASTLE_DOMAIN for phase 4, when the server IP exists. If they want a real domain later, it is one variable, three DNS records, and one Nextcloud setting Claude updates (`occ config:system:set trusted_domains`); recommend that once they like the castle.
3. Fill CASTLE_REGION (from phase 2), GITHUB_REPO (owner/name from `git remote get-url origin`).
4. Generate secrets locally, one `openssl rand -hex 24` each, for POSTGRES_PASSWORD, NEXTCLOUD_DB_PASSWORD, NEXTCLOUD_ADMIN_PASSWORD. Only fill fields that are still empty; never regenerate one that already has a value. Do not print them. (Hex, not base64: these end up inside a database URL, where base64's `/` characters break parsing.) Tell the user once: "Your passwords live in config/castle.env on this laptop and in /opt/castle/castle.env on the server. Git ignores both; they are never uploaded to GitHub."

**Verify**: read the file back; every field above is filled (CASTLE_DOMAIN may still be empty only on the sslip path).

## Phase 4: create the server

**Already done?** An instance named `castle` exists and SERVER_IP in config/castle.env matches its public IP. Then skip.

1. Make sure the laptop's ssh key is at Scaleway: if `scw iam ssh-key list` does not contain the content of `~/.ssh/id_ed25519.pub`, add it with `scw iam ssh-key create name=castle-laptop public-key="$(cat ~/.ssh/id_ed25519.pub)"`.
2. Check `scw instance server list name=castle`. If one exists, reuse it and say so.
3. Otherwise tell the user in one line that the paid part starts now (10 to 15 euros per month, deletable any time), then create it: `scw instance server create type=DEV1-M zone=<zone> image=ubuntu_noble name=castle ip=new`. If DEV1-M is unavailable in the zone, pick the closest current small type and say which. Use the latest Ubuntu LTS image available.
4. Wait until the state is running and it has a public IP (poll `scw instance server get`). Fresh servers take a minute or two to accept ssh; retry `ssh -o StrictHostKeyChecking=accept-new root@<IP> true` for a couple of minutes.
5. Write `SERVER_IP=<IP>` into config/castle.env. If on the sslip path, also set `CASTLE_DOMAIN=<IP with dots replaced by dashes>.sslip.io` now.

**Verify**: `ssh root@<IP> true` succeeds; SERVER_IP saved; CASTLE_DOMAIN filled.

## Phase 5: DNS

**Already done?** `dig +short <domain>`, `dig +short notulen.<domain>`, `dig +short cloud.<domain>` all return SERVER_IP. Then skip. (`dig` is not preinstalled on fresh WSL Ubuntu; install it with `sudo apt-get install -y dnsutils` if missing.)

- **Real domain**: print exactly this table with their real domain and IP, and explain in one sentence that an A record points a name at a server address, added at the website where they bought the domain (look for "DNS", "DNS records", or "Zone"):

  | Type | Name | Value |
  |---|---|---|
  | A | `@` | SERVER_IP |
  | A | `notulen` | SERVER_IP |
  | A | `cloud` | SERVER_IP |

  TTL defaults are fine. Then poll the three `dig +short` checks every 30 seconds or so. If it drags on, explain DNS spread can take minutes to hours, and offer to continue waiting; do not proceed to phase 6 until all three resolve.
- **sslip**: nothing to do; the names `<ip-dashes>.sslip.io`, `notulen.<ip-dashes>.sslip.io` and `cloud.<ip-dashes>.sslip.io` resolve by construction. Run the three `dig` checks once to prove it.

**Verify**: all three names resolve to SERVER_IP.

## Phase 6: deploy the stack

**Already done?** All three URLs respond over HTTPS: 2xx/3xx for the website and `cloud.`, and 2xx/3xx **or 401** for `notulen.` (it sits behind a login; 401 means alive). Then skip. Partially done pieces (user exists, docker installed, repo cloned) are all safe to re-run past.

Work over ssh as root for steps 1 to 4, then switch to the `castle` user forever after.

1. `apt-get update && apt-get upgrade -y` on the server.
2. Create the `castle` user if missing, copy root's `~/.ssh/authorized_keys` to it (owned by castle, mode 600), and give it passwordless sudo: write `castle ALL=(ALL) NOPASSWD:ALL` to `/etc/sudoers.d/castle`, mode 440 (the user has no password, so sudo would otherwise dead-end over ssh). Explain: day to day the server runs as this ordinary user, not as the all-powerful root.
3. Install Docker Engine plus the compose plugin using Docker's official install path (their apt repository, or `curl -fsSL https://get.docker.com | sh`). Add castle to the `docker` group. Verify `docker --version` and `docker compose version`.
4. Add a 4 GB swap file if none exists (`swapon --show` empty): `fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`, plus a `/swapfile none swap sw 0 0` line in /etc/fstab. Explain in one sentence: transcription briefly needs more memory than the small server has, and the swap file is the cheap safety margin.
5. Deploy key, so the server can read their private repo: as castle on the VM, `ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C castle-vm-deploy` (skip if it exists), `ssh-keyscan github.com >> ~/.ssh/known_hosts`. Copy the public key back to the laptop and register it read-only: `gh repo deploy-key add <pubkey-file> --repo <owner>/<name> --title "castle vm (read-only)"`. Skip if a deploy key with that title already exists.
6. `sudo mkdir -p /opt/castle && sudo chown castle:castle /opt/castle`, then as castle `git clone git@github.com:<owner>/<name>.git /opt/castle/repo` (or `git -C /opt/castle/repo pull --ff-only` if it exists).
7. Write `/opt/castle/castle.env`, mode 600. **Only if the file does not exist yet.** If it already exists, never overwrite filled-in values: the only permitted change is replacing a literal `pending-phase-8` placeholder, and never regenerate the notulen password when a NOTULEN_BASIC_AUTH_HASH is already present (the user saved that password). For a fresh file, start from the laptop's config/castle.env plus:
   - A generated notulen password. Hash it with `docker run --rm caddy:2 caddy hash-password --plaintext '<password>'` and store the hash **wrapped in single quotes** as NOTULEN_BASIC_AUTH_HASH (it contains `$` characters that must not expand). Tell the user exactly once: "Your meeting recorder login is user `castle` with this password: <password>. Save it in your password manager now; I will not show it again." NOTULEN_BASIC_AUTH_USER stays `castle`.
   - S3_ENDPOINT and S3_REGION for their region. S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, ANTHROPIC_API_KEY are not known yet; write the literal value `pending-phase-8` for each (compose refuses empty values). Be honest: the meeting recorder will start but cannot store recordings until phase 8 replaces these.
   - Explain mode 600 in one sentence: only the castle user can read the file.
8. Start everything: in `/opt/castle/repo`, `docker compose --env-file /opt/castle/castle.env up -d --build`. Explain: each service runs in its own container, and Caddy fetches the HTTPS certificates automatically, which can take a minute or two.
9. Install auto-deploy: `sudo /opt/castle/repo/infra/systemd/install.sh`. Explain: from now on, every push to GitHub goes live within about 2 minutes; pushing is the deploy button.
10. Verify with retries while certificates settle (up to ~5 minutes): `curl -fsSL -o /dev/null -w '%{http_code}' https://<domain>` and the same for `notulen.` (expect 401 without login, that counts as alive) and `cloud.`. Also `docker compose --env-file /opt/castle/castle.env ps` shows everything up.
11. **sslip certificate fallback**: sslip.io names usually get real Let's Encrypt certificates, but the sslip.io domain has a shared rate limit that sometimes bites. If Caddy's logs (`docker logs castle-caddy`) show a rate-limit error after several minutes, switch to Caddy's own internal certificates: add a global block at the top of `infra/caddy/Caddyfile` containing `local_certs`, commit, push, wait for auto-deploy, and re-verify with `curl -k`. Tell the user plainly: the sites work and traffic is still encrypted, but the browser will show a warning it cannot verify the certificate; buying a real domain later removes the warning, and swapping it in is one variable, three DNS records, and one Nextcloud setting Claude updates.

**Verify**: three URLs respond over HTTPS; `docker compose ps` healthy. From here on, all ssh as `castle`, never root.

## Phase 7: Nextcloud accounts and 2FA

**Already done?** Both everyday accounts exist (`occ user:list`) and `infra/nextcloud/nextcloud-2fa-enforce.sh --check` reports everyone enrolled AND `enforcement: ON`. The check prints both; enrolled-but-not-enforced means phase 7 is NOT done, run step 5.

`occ` is Nextcloud's admin tool; run it on the VM as `docker compose --env-file /opt/castle/castle.env exec -T -u www-data nextcloud php occ ...` from /opt/castle/repo.

1. Wait until `https://cloud.<domain>` serves the Nextcloud login page (first boot installs itself; this can take a few minutes). The admin account comes from castle.env automatically.
2. **Question 5 of the budget**: ask for the two account names (one per person, a short lowercase username each; display names can be their real names).
3. Create each account with a generated temporary password. `docker compose exec` does not pass host variables through, so set it explicitly: `docker compose --env-file /opt/castle/castle.env exec -T -e OC_PASS='<temp password>' -u www-data nextcloud php occ user:add --password-from-env --display-name "<Name>" <username>`. Give each person their username and temporary password once, and tell them to change it after first login (personal settings, Security).
4. TOTP enrolment, one person at a time, live (**question 6 of the budget**). First make sure the TOTP app is enabled: `... occ app:enable twofactor_totp`. Then for each person, and once for the admin account (one of them scans that too):
   - Have them install any authenticator app on their phone (Google Authenticator, Microsoft Authenticator, any TOTP app, all free).
   - They log in at `https://cloud.<domain>`, open Settings then Security, choose the TOTP option, scan the QR code with the app, type the 6-digit code.
   - Have them generate and save the backup codes on the same page, and say why in one sentence: phone lost means a backup code is the only way back in.
5. Only after every account (both users AND admin) is enrolled, enforce: `infra/nextcloud/nextcloud-2fa-enforce.sh --check` first, then without `--check`. The script refuses to enforce while anyone is unenrolled, so an abort means someone skipped step 4; finish that first.
6. Point them at the Nextcloud mobile app (App Store / Play Store), server address `https://cloud.<domain>`, and mention automatic photo upload as a nice option.

**Verify**: `--check` reports all enrolled, enforcement on; both of them reached their files screen.

## Phase 8: notulen

**Already done?** S3_BUCKET in /opt/castle/castle.env is a real bucket name (not `pending-phase-8`) and `https://notulen.<domain>` is healthy. Then only revisit the Anthropic key if it is still the placeholder.

1. Create a private Object Storage bucket: `scw object bucket create name=castle-notulen-<something unique, e.g. the domain with dots as dashes> region=<region>`. Explain: a bucket is a private cloud folder where the audio recordings live. Reuse it if it already exists.
2. The scw API key from phase 2 doubles as the storage credentials. On the server, replace the placeholders in /opt/castle/castle.env: S3_BUCKET, S3_ACCESS_KEY (the access key), S3_SECRET_KEY (the secret key). Keep the file at mode 600.
3. **Question 4 of the budget**, the Anthropic key: "The meeting recorder uses Claude to write the minutes, through an API key with its own billing, separate from the Claude subscription. It costs a few cents per meeting. Get one at console.anthropic.com: Billing (add a card, set a monthly limit like 5 euros), then API keys, Create key, copy the `sk-ant-...` value. Or say skip: everything else works without it, and you can add it later by just asking me."
   - Key given: put it in /opt/castle/castle.env as ANTHROPIC_API_KEY.
   - Skipped: leave the placeholder and say honestly what they will see: the recording is transcribed and saved, but the job then shows as **failed** with a missing-key error; the transcript is not lost, and adding a key later (just ask Claude) makes new recordings produce minutes.
4. Restart the service: `docker compose --env-file /opt/castle/castle.env up -d notulen` in /opt/castle/repo.
5. Health check: the container is healthy in `docker compose ps`, `https://notulen.<domain>` answers (with the basic auth login from phase 6), and the logs start clean.
6. If the key was given, one live test recording: they open `https://notulen.<domain>`, log in, allow the microphone, record about a minute of talk ("we decided to test the meeting recorder"), stop, and wait. Transcription runs on the server's own processor, so minutes can take a few minutes; watch the logs and narrate. If nothing arrives, investigate the logs before asking them to retry.

**Verify**: bucket exists, no `pending-phase-8` left except possibly ANTHROPIC_API_KEY, service healthy, test done or consciously skipped.

## Phase 9: finish

1. Write a memory note in `.claude/memory/` (a short file plus one index line in MEMORY.md): domain, server IP, region, instance type, bucket name, which phases ran, what was skipped (for example the Anthropic key), and the date. No passwords in memory, ever.
2. Print the three addresses on their own lines: the website, `cloud.` and `notulen.`.
3. Explain the daily loop in four lines: open a terminal, run `claude --dangerously-skip-permissions` in this folder, say what you want in plain words, and after I push, the change is live in about 2 minutes.
4. Tell them: if anything ever looks broken, just say "something is broken" and I will investigate (the troubleshoot skill).
