# Onboard phases

Each phase: **Already done?** check first, then the work, then the **Verify** check. Announce each phase to the user in one plain sentence before starting it.

## The vault, and how to update it

Secrets never live in files the user keeps. They live in the vault: one Scaleway Secret Manager secret named `castle-env` whose content is the stack's full KEY=value environment; every change is a new version (`infra/secrets/README.md` explains the model). `config/castle.env` on the laptop holds only non-secret settings. The VM keeps a pulled cache at `/opt/castle/castle.env`; compose reads that cache.

Every phase that changes any environment value uses this one pattern:

1. Fetch the current content to a temp file, mode 600, never echoed: look up the secret id with `scw secret secret list name=castle-env -o json` (the `id` field), then `scw secret version access <secret-id> revision=latest raw=true > "$TEMP_ENV" && chmod 600 "$TEMP_ENV"`.
2. Edit the KEY=value lines in the temp file.
3. Push it back as a new version: `infra/secrets/push-env.sh "$TEMP_ENV"`, then `rm -f "$TEMP_ENV"`.
4. Apply on the VM: run `ssh castle@<SERVER_IP> /opt/castle/repo/infra/secrets/pull-env.sh` and restart the affected service, or just wait one auto-deploy cycle (it pulls the vault every run and redeploys when the env changed).

Batch related edits into one version; never print the content.

## Phase 0: explain the plan

Tell the user, in four lines, roughly this:

> I am going to set up your castle: a small server at Scaleway running your website, your private cloud storage, and Notulen (the meeting recorder), plus a fast transcription engine that only runs, and only costs cents, when a recording comes in. It takes about an hour of my work and a few minutes of yours. I will need two things from you along the way: a Scaleway API key (I will tell you exactly where to click) and, optionally, an Anthropic API key for the Notulen summaries. The server costs roughly 10 to 15 euros per month; everything else is free or costs cents.

Then start phase 1 without waiting, unless they object.

## Phase 1: laptop tools and GitHub

**Already done?** `gh auth status` succeeds, `~/.claude/projects/.../memory` is a symlink into this repo, and the origin owner equals `gh api user --jq .login`. Then skip.

1. Verify `git --version`, `uv --version`, `claude --version` all print. These were installed by hand before this conversation; if one is missing, install it (git via apt/xcode-select, uv via the astral.sh install script) and say what you did.
2. Install the GitHub CLI if missing, WITHOUT sudo (this session has no terminal for a password prompt, and the user must never have to run commands themselves). Download the latest release binary into `~/.local/bin`: resolve the version from `https://api.github.com/repos/cli/cli/releases/latest` (the `tag_name`, like v2.x.y), then fetch `https://github.com/cli/cli/releases/download/<tag>/gh_<version>_linux_amd64.tar.gz` (Mac: `_macOS_arm64.zip` or `_amd64` per `uname -m`), extract the single `gh` binary to `~/.local/bin/gh`, `chmod +x`, and make sure `~/.local/bin` is on PATH (it is on fresh WSL and via the uv installer). Verify `gh --version`.
3. Log in (**question 1 of the budget**): first ask "do you already have a GitHub account?"; if not, send them to github.com/signup (free, two minutes) and wait. Then `gh auth login --hostname github.com --git-protocol https --web` followed by `gh auth setup-git`. Tell the user: a code appears, the browser opens, they type the code and click approve. That is all they do. HTTPS plus `setup-git` means no ssh keys to manage on the GitHub side.
4. If `git config user.name` or `user.email` is empty, set them from the GitHub account, using `gh api user` for the name and the noreply email if none is public.
5. Give them their own private copy. They cloned the public upstream, so check `git remote get-url origin`: if the owner is not their login, run `gh repo create claude-castle --private` under their account, rename the current origin to `upstream`, add their new repo as `origin`, and `git push -u origin main`. Say in one sentence: your castle now has its own private home on GitHub; the original stays connected as upstream for future improvements.
6. Run `bash .claude/bootstrap.sh` from the repo root. Explain in one sentence: this makes my notes about your setup live inside the project, so they survive and get backed up with everything else.

**Verify**: `gh auth status` ok; `git remote get-url origin` owner equals their GitHub login; `git push` works (the bootstrap memory commit or an empty push proves it).

## Phase 2: Scaleway CLI

**Already done?** `scw account project list` returns a project table. Then skip.

1. Install scw if missing, WITHOUT sudo (the official install script wants root; skip it). Download the release binary straight into the user's own folder: resolve the latest version from `https://api.github.com/repos/scaleway/scaleway-cli/releases/latest`, fetch the matching `scaleway-cli_<version>_linux_amd64` (or darwin/arm64 per OS and `uname -m`) from that release's assets, save as `~/.local/bin/scw`, `chmod +x`, verify `scw version`.
2. **Question 3 of the budget**, ask for the API key with this exact path: "Go to https://console.scaleway.com, log in, click IAM in the left menu (or your name, then API keys), then API keys, then Generate API key. It shows an Access key and a Secret key. Copy both and paste them here. The secret is shown only once, so copy it before closing." If they have no Scaleway account yet, send them to https://www.scaleway.com (say: check the address bar, that exact address) and tell them to pick "Continue with GitHub" with the account from phase 1: no new password to invent. Then add a payment card (Billing section); warn BEFORE they type a number: Scaleway refuses prepaid-style cards, which includes Revolut and most virtual cards; a normal bank card works, debit or credit. If they have no usable card, the same Billing page offers a SEPA mandate (payment straight from their bank account); walk them through adding that instead. Then come back for the key.
3. Spending protection, one sentence, no user action: "I watch your spending myself: the castle checks its own bill every hour and warns you past 30 euro a month." (The watchdog does this; Scaleway offers no API for its console budget alerts, so Claude cannot set those. Mention once that Scaleway's own extra alert email exists at https://console.scaleway.com/billing/alerts if they ever want a second net; optional, never blocking.)
4. Configure non-interactively, never through `scw init`:
   - `scw config set access-key=<ACCESS> secret-key=<SECRET>`
   - `scw account project list` to find the project and organization IDs, then `scw config set default-project-id=<id> default-organization-id=<id> default-region=fr-par default-zone=fr-par-1`
   - Region is your decision, not a question: `fr-par` unless the user already said where they live and another Scaleway region is clearly closer.

**Verify**: `scw account project list` shows at least one project.

## Phase 3: settings file + the vault

**Already done?** `config/castle.env` exists with non-placeholder CASTLE_DOMAIN, CASTLE_REGION, GITHUB_REPO, AND the vault has content: `scw secret secret list name=castle-env -o json` finds the secret and `scw secret version list <secret-id>` shows at least one enabled version. Then skip.

1. Write `config/castle.env` if it does not exist: copy ONLY the settings block from `config/castle.env.example` (CASTLE_DOMAIN, CASTLE_REGION, GITHUB_REPO, SERVER_IP, and the TEM_* lines). No secrets go into this file, ever; the loud header in the example says the same.
2. **Question 2 of the budget**: "Do you own a domain name (a web address like example.com)?"
   - **Yes**: use it as CASTLE_DOMAIN.
   - **No**: the castle gets free names from sslip.io, derived from the server's address, like `1-2-3-4.sslip.io` with `notulen.` and `cloud.` in front. Explain: these work immediately, nothing to buy or configure; they are just less pretty. Leave CASTLE_DOMAIN for phase 4, when the server IP exists. If they want a real domain later, it is one variable, three DNS records, and one Nextcloud setting Claude updates (`occ config:system:set trusted_domains`); recommend that once they like the castle.
3. Fill CASTLE_REGION (from phase 2), GITHUB_REPO (owner/name from `git remote get-url origin`) in config/castle.env.
4. Assemble the FULL environment in a temp file (mode 600), never in config/castle.env:
   - Start from a copy of `config/castle.env.example` (all fields, both blocks) and fill the settings values from config/castle.env. If the vault already has a version (resuming a half-finished setup), start from that instead (fetch it, step 1 of the update pattern) and only fill fields that are still empty; never regenerate one that already has a value.
   - Generate secrets locally, one `openssl rand -hex 24` each, for POSTGRES_PASSWORD, NEXTCLOUD_DB_PASSWORD, NEXTCLOUD_ADMIN_PASSWORD, NEXTCLOUD_WEBHOOK_SECRET (the last one is the internal webhook secret for the cloud sync; the stack refuses to start without it, even if the sync stays unused). Do not print them. (Hex, not base64: these end up inside a database URL, where base64's `/` characters break parsing.)
   - Write the literal value `pending-phase-8` for S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, ANTHROPIC_API_KEY (compose refuses empty values; phase 8 replaces them). Set S3_ENDPOINT and S3_REGION for the region from phase 2.
5. Push it to the vault: `infra/secrets/push-env.sh <temp file>`, then delete the temp file. Tell the user one plain sentence: "Your passwords now live in Scaleway's secret vault, not in files; config/castle.env on this laptop keeps only harmless settings."
6. Business intake, **question 7 of the budget, only if it applies**: if `business/` contains anything beyond `README.md`, ask: "I see you put files in business/. Want to organize that folder together first, or keep it as it is? Either way I fill your company profile from what I find there." If `business/` holds only the README, skip this step without saying anything.
   - **Organize together**: propose a simple folder layout (for example `contracts/`, `invoices/`, `brand/`, `registration/`) and move the files with them watching, one sentence per move.
   - **Either way**: extract into `design/company.yaml` only values literally present in their documents: company name, address, registration and VAT numbers, IBAN, email, phone. If a logo image is found, copy it into `design/` and set `logo:`. If brand colors are obvious (the fill of an SVG logo, a letterhead color), set the colors in `design/company.yaml` and `design/tokens.css` to match. Say one sentence per thing found. Never invent; anything not found stays empty until they provide it.
   - Close with: "your castle can now produce documents in your house style; ask me for an invoice and see."

**Verify**: config/castle.env holds the settings (CASTLE_DOMAIN may still be empty only on the sslip path) and nothing secret; the vault has at least one version. If the business intake ran, `design/company.yaml` holds the extracted values and nothing invented.

## Phase 4: create the server

**Already done?** An instance named `castle` exists and SERVER_IP in config/castle.env matches its public IP. Then skip.

1. Make sure the laptop has an ssh key and Scaleway knows it: if `~/.ssh/id_ed25519` does not exist, create it with `ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519` (one sentence to the user: this is the key that lets me reach your server securely). If `scw iam ssh-key list` does not contain the content of `~/.ssh/id_ed25519.pub`, add it with `scw iam ssh-key create name=castle-laptop public-key="$(cat ~/.ssh/id_ed25519.pub)"`.
2. Check `scw instance server list name=castle`. If one exists, reuse it and say so.
3. Otherwise tell the user in one line that the paid part starts now (10 to 15 euros per month, deletable any time), then create it: `scw instance server create type=DEV1-M zone=<zone> image=ubuntu_noble root-volume=local:40GB name=castle ip=new`. The `root-volume=local:40GB` part is not optional: without it the disk defaults to the image minimum (8 GB) and the stack does not fit; 40 GB is included in the DEV1-M price. If DEV1-M is unavailable in the zone, pick the closest current small type and say which. Use the latest Ubuntu LTS image available. After first ssh, confirm `df -h /` shows roughly 40 GB.
4. Wait until the state is running and it has a public IP (poll `scw instance server get`). Fresh servers take a minute or two to accept ssh; retry `ssh -o StrictHostKeyChecking=accept-new root@<IP> true` for a couple of minutes.
5. Write `SERVER_IP=<IP>` into config/castle.env. If on the sslip path, also set `CASTLE_DOMAIN=<IP with dots replaced by dashes>.sslip.io` now, in config/castle.env AND in the vault (update pattern; the stack cannot start in phase 6 while the vault's CASTLE_DOMAIN is a placeholder). On the real-domain path the vault already has the right domain from phase 3.

**Verify**: `ssh root@<IP> true` succeeds; SERVER_IP saved; CASTLE_DOMAIN filled in config/castle.env and in the vault.

## Phase 5: DNS

**Already done?** All three names resolve to SERVER_IP. Check without installing anything: `python3 -c "import socket; print(socket.gethostbyname('<name>'))"` for `<domain>`, `notulen.<domain>` and `cloud.<domain>` (python3 is always present; no dig, no sudo).

- **Real domain**: print exactly this table with their real domain and IP, and explain in one sentence that an A record points a name at a server address, added at the website where they bought the domain (look for "DNS", "DNS records", or "Zone"):

  | Type | Name | Value |
  |---|---|---|
  | A | `@` | SERVER_IP |
  | A | `notulen` | SERVER_IP |
  | A | `cloud` | SERVER_IP |

  TTL defaults are fine. Then poll the three python3 resolution checks (the Already-done line above) every 30 seconds or so. If it drags on, explain DNS spread can take minutes to hours, and offer to continue waiting; do not proceed to phase 6 until all three resolve.
- **sslip**: nothing to do; the names `<ip-dashes>.sslip.io`, `notulen.<ip-dashes>.sslip.io` and `cloud.<ip-dashes>.sslip.io` resolve by construction. Run the three resolution checks once to prove it.

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
7. Give the VM its own scoped way into the vault, then materialize the env cache. **Skip the IAM creation if `/opt/castle/scw-secrets.env` already exists on the VM.**
   - From the laptop, create the VM's own identity: `scw iam application create name=castle-vm -o json` (reuse it if `scw iam application list name=castle-vm -o json` finds one).
   - One policy that lets it read secret values and the bill in this project, nothing else: `scw iam policy create name=castle-vm-secrets application-id=<app-id> rules.0.permission-set-names.0=SecretManagerReadOnly rules.0.permission-set-names.1=SecretManagerSecretAccess rules.0.permission-set-names.2=BillingReadOnly rules.0.project-ids.0=<project-id from phase 2>`. The first two are both required: ReadOnly alone can list secrets but not read their values (live-tested; the pull gets permissions_denied without SecretManagerSecretAccess). BillingReadOnly lets the hourly watchdog read the bill for the spending warning; the server can never change the account.
   - An API key for that application, with an expiry about one year out (some organizations refuse keys without one): `scw iam api-key create application-id=<app-id> expires-at=<ISO 8601 date one year from today> -o json`. Note the renewal in the phase 10 memory note; "renew the castle-vm key" is an ask-Claude job in a year.
   - Look up the vault's secret id: `scw secret secret list name=castle-env -o json`.
   - Write `/opt/castle/scw-secrets.env` on the VM, owned by castle, mode 600, with exactly: `SCW_ACCESS_KEY=<the new key's access key>`, `SCW_SECRET_KEY=<its secret key>`, `SCW_DEFAULT_PROJECT_ID=<project id>`, `SCW_DEFAULT_REGION=<region>`, `CASTLE_ENV_SECRET_ID=<secret id>`. The powerful laptop key never lands on the VM; this scoped key can only read this project's secrets.
   - Notulen login, **only if the vault has no NOTULEN_BASIC_AUTH_HASH yet** (the user saved that password; never regenerate it): generate a password, hash it on the VM with `docker run --rm caddy:2 caddy hash-password --plaintext '<password>'`, and put the hash into the vault (update pattern) **wrapped in single quotes** as NOTULEN_BASIC_AUTH_HASH (it contains `$` characters that must not expand). Tell the user exactly once: "Your Notulen login is user `castle` with this password: <password>. Save it in your password manager now; I will not show it again." NOTULEN_BASIC_AUTH_USER stays `castle`.
   - Materialize the cache: as castle on the VM, run `/opt/castle/repo/infra/secrets/pull-env.sh` (a freshly created key can take a few seconds to start working; the script retries once by itself). Check `/opt/castle/castle.env` now exists, mode 600, with the real CASTLE_DOMAIN in it. Never write that file by hand; the vault is the only source and the only permitted vault changes later are replacing literal `pending-phase-8` placeholders.
   - Be honest: Notulen will start but cannot store recordings until phase 8 replaces the S3 placeholders. Explain the model in one sentence: "your passwords live in Scaleway's secret vault; the server keeps a private copy only the castle user can read."
8. Start everything: in `/opt/castle/repo`, `docker compose --env-file /opt/castle/castle.env up -d --build`. Explain: each service runs in its own container, and Caddy fetches the HTTPS certificates automatically, which can take a minute or two.
9. Install auto-deploy and the watchdog: `sudo /opt/castle/repo/infra/systemd/install.sh`. Also put kubectl on the VM for the watchdog's node check, no sudo: download the release binary to /home/castle/.local/bin/kubectl as the castle user (same no-sudo pattern as the laptop tools) and make sure that dir is on castle's PATH. Explain both in one sentence each: every push to GitHub goes live within about 2 minutes, and an hourly watchdog warns about stuck machines, stuck recordings, a filling disk, and spending past the 30 euro line (CASTLE_BUDGET_EUR in the settings changes the line; add CASTLE_OWNER_EMAIL to the vault so warnings reach their inbox once email is set up).
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
2. The scw API key from phase 2 doubles as the storage credentials. Replace the placeholders in the vault (update pattern; batch step 3's key into the same version): S3_BUCKET, S3_ACCESS_KEY (the access key), S3_SECRET_KEY (the secret key). This reuses the powerful laptop key as storage credentials; a scoped storage key is a noted future hardening (`infra/secrets/README.md`), not today's problem.
3. **Question 4 of the budget**, the Anthropic key: "Notulen uses Claude to turn the transcript into the written summary, through an API key with its own billing, separate from the Claude subscription. It costs a few cents per meeting. Get one at console.anthropic.com: Billing (add a card, set a monthly limit like 5 euros), then API keys, Create key, copy the `sk-ant-...` value. Or say skip: everything else works without it, and you can add it later by just asking me."
   - Key given: put it in the vault as ANTHROPIC_API_KEY (same new version as step 2).
   - Skipped: leave the placeholder and say honestly what they will see: the recording is transcribed and saved, but the job then shows as **failed** with a missing-key error; the transcript is not lost, and adding a key later (just ask Claude) makes new recordings produce minutes.
   - **In the same optional-keys conversation** (no extra question against the budget), offer the cloud sync: "One more optional token: anything you drop in a folder called Sync in your cloud files can also land in your GitHub repo automatically, so it is versioned and backed up. That needs one GitHub token; want it, or skip?" If yes, walk them through it: go to github.com/settings/personal-access-tokens, Generate new token (fine-grained), pick your castle repo as the only repository, under Repository permissions set Contents to Read and write, create, copy the token. If skip, skip phase 8b entirely; it can be turned on later by just asking Claude.
4. Apply: run `/opt/castle/repo/infra/secrets/pull-env.sh` on the VM, then restart the service: `docker compose --env-file /opt/castle/castle.env up -d notulen` in /opt/castle/repo.
5. Health check: the container is healthy in `docker compose ps`, `https://notulen.<domain>` answers (with the basic auth login from phase 6), and the logs start clean.
6. If the key was given, one live test recording: they open `https://notulen.<domain>`, log in, allow the microphone, record about a minute of talk ("we decided to test Notulen"), stop, and wait. Transcription runs on the server itself, so the summary can take a few minutes; watch the logs and narrate. If nothing arrives, investigate the logs before asking them to retry.

**Verify**: bucket exists, no `pending-phase-8` left except possibly ANTHROPIC_API_KEY, service healthy, test done or consciously skipped.

## Phase 8b: cloud folder to GitHub sync (optional, fully skippable)

**Already done?** SYNC_GITHUB_PAT is filled in /opt/castle/castle.env and `occ webhook_listeners:list` shows three listeners pointing at `http://nextcloud-sync:8000/nextcloud/file-event`. Then skip.

**Skipped?** If they said skip to the sync token in phase 8, skip this whole phase. NEXTCLOUD_WEBHOOK_SECRET is already set (phase 3), so the container runs but stays dormant: no listeners registered, nothing fires, nothing syncs. Turning it on later is just re-running this phase.

The PAT question already happened in phase 8; this phase asks nothing new.

1. Make sure NEXTCLOUD_WEBHOOK_SECRET is set in the vault (phase 3 generates it; vault content from before the sync existed may lack it, then generate with `openssl rand -hex 24` and add it). Put the PAT from phase 8 into the vault as SYNC_GITHUB_PAT (same update pattern, one new version for both), then run `/opt/castle/repo/infra/secrets/pull-env.sh` on the VM.
2. Restart the service so it picks up the env: in /opt/castle/repo, `docker compose --env-file /opt/castle/castle.env up -d --build nextcloud-sync`; wait until `docker compose ps` shows it healthy.
3. Register the webhook listeners: `infra/nextcloud-sync/register-webhooks.sh` (idempotent; it enables the webhook_listeners app, mints and removes a temporary admin app password, and registers the three file events via the OCS API).
4. Have one of them create a folder named exactly `Sync` at the top of their Nextcloud files (web or mobile app). Explain in one sentence: anything in this folder also lands in your GitHub repo, so it is versioned and backed up.
5. Verify end to end: put a test file in that user's Sync folder via occ, `printf 'castle sync test\n' | docker compose --env-file /opt/castle/castle.env exec -T -u www-data nextcloud php occ files:put - <username>/files/Sync/castle-sync-test.md`, then watch the repo from the laptop: `gh api repos/<owner>/<name>/contents/cloud-sync/<username>/castle-sync-test.md` until it appears. Deliveries ride Nextcloud's cron container, so this can take up to five minutes; say so instead of going quiet. When it lands, show them the commit (authored by their Nextcloud name) and clean up the test file.
6. If nothing arrives after ten minutes, check `docker compose logs nextcloud-sync` and Nextcloud's webhook run logs before asking them to retry.

**Verify**: three listeners registered, test file visible in the repo under `cloud-sync/<username>/`, test file cleaned up.

## Phase 9: fast transcription

**Already done?** KUBECONFIG_DATA is non-empty in /opt/castle/castle.env on the server, `scw k8s cluster list name=castle` shows a cluster, and `bash infra/gpu/build-worker.sh` reports the image already pushed (it checks the registry first and exits without building). Then skip.

This phase gives Notulen a GPU, so a one-hour meeting is transcribed in minutes instead of hours. Before creating anything, tell the user the money story in two sentences: the GPU bills only while it is actually working on a recording, roughly 80 cents per hour of processing, which comes to cents per meeting; the rest of the cluster is free.

1. Start the image build first, because it is the longest step (20 to 40 minutes). From the repo root: `bash infra/gpu/build-worker.sh v1 > /tmp/castle-gpu-build.log 2>&1 &` and let it run in the background while you do steps 2 to 6. It creates the `castle` registry namespace if needed, boots a temporary build instance, builds the worker image, pushes it to `rg.<region>.scw.cloud/castle/notulen-worker:v1`, and deletes the instance (a few cents total). On success the log's last line is the pushed image reference. If you planned ahead, this build can already be started in the background at the end of phase 6; if backgrounding feels risky, just run it here in the foreground and wait. No Hugging Face token is needed; without one the image transcribes fine but does not label who said what (speaker labels are a later ask-Claude option, see `infra/gpu/README.md`, never a setup question).
2. Create the cluster. Pick the latest stable version from `scw k8s version list`, then:

   ```
   scw k8s cluster create name=castle version=<latest stable> cni=cilium region=<region> \
     pools.0.name=gpu pools.0.node-type=L4-1-24G pools.0.size=1 \
     pools.0.min-size=0 pools.0.max-size=1 \
     pools.0.autoscaling=true pools.0.autohealing=true pools.0.zone=<zone>
   ```

   Pick the node type and zone with `infra/gpu/pick-gpu.sh`: it walks a cheapest-first ladder ACROSS the region's zones (GPU stock has bad nights per zone) and prints `<zone> <node-type>`; use those in the pool arguments. Exit code 3 means no GPU stock anywhere on the ladder: stop here, stay on CPU transcription, tell the user honestly what that means (recordings still work, a one-hour meeting just takes hours to process instead of minutes), record the skip in the phase 10 memory note, and skip the rest of this phase; "turn on fast transcription" any other day retries against fresh stock. A pricier card from the ladder is fine: a transcription job runs minutes, so even the top of the ladder is cents per meeting. Explain the shape once: the control plane is free; a GPU node exists, and bills, only while a transcription job runs; the autoscaler adds one when a job appears and removes it about 10 minutes after it goes idle.

   Node health contingency (live-tested; GPU capacity has bad nights): if a node lands as `creation_error`, goes NotReady within minutes, or `kubectl get nodes -o jsonpath='{.items[*].status.allocatable.nvidia\.com/gpu}'` stays empty ~10 minutes after the node is Ready, replace it once (`scw k8s node replace <node-id> region=<region>`). Still sick: try the other L4 size as a second pool. Still sick or out of stock: leave the cluster and image in place, stay on CPU, and tell the user in one sentence that saying "turn on fast transcription" any other day retries this phase against fresh stock. Never burn more than two node attempts in one sitting.
3. Wait until `scw k8s cluster get <cluster-id>` shows status ready (a few minutes). Then fetch the ADMIN kubeconfig for your own kubectl use: `scw k8s kubeconfig get <cluster-id> region=<region>` (save to a temp file). Do NOT put that one in KUBECONFIG_DATA: it authenticates through the scw command, which does not exist inside the dashboard container, so the cluster would treat the dashboard as anonymous and refuse it (live-test finding). Instead, after step 5 creates the namespace, run `KUBECONFIG=<admin temp file> infra/gpu/make-dashboard-kubeconfig.sh > <temp>/dashboard-kubeconfig.yaml`; it mints a service account that can only manage transcription Jobs in the castle namespace and prints a self-contained kubeconfig with a static token. KUBECONFIG_DATA is the base64 of THAT file: `base64 -w0 <temp>/dashboard-kubeconfig.yaml` (on a Mac, plain `base64`). Keep it for step 6; never print it to the user.
4. Install kubectl if missing (Mac: `brew install kubectl`; Ubuntu/WSL: download the release binary from `https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl`, `chmod +x`, move into `~/.local/bin`). Save the kubeconfig YAML from step 3 to a temp file and `export KUBECONFIG=<that file>` for the kubectl commands below.
5. Prepare the namespace and its two secrets. Values come from the vault (read them from /opt/castle/castle.env, the pulled cache, on the VM); the scw secret key is the same one from phase 2:

   ```
   kubectl create namespace castle
   kubectl -n castle create secret docker-registry castle-registry \
     --docker-server=rg.<region>.scw.cloud --docker-username=nologin \
     --docker-password=<scw secret key>
   kubectl -n castle create secret generic castle-worker-secrets \
     --from-literal=DB_URL='postgresql://castle:<POSTGRES_PASSWORD>@<SERVER_IP>:5432/castle' \
     --from-literal=S3_ENDPOINT=<value> --from-literal=S3_REGION=<value> \
     --from-literal=S3_BUCKET=<value> --from-literal=S3_ACCESS_KEY=<value> \
     --from-literal=S3_SECRET_KEY=<value> --from-literal=ANTHROPIC_API_KEY=<value> \
     --from-literal=MINUTES_LANGUAGE=<value>
   ```

   DB_URL is the external form on purpose: the GPU worker connects to the postgres on the castle server over the internet, on port 5432, which the stack publishes. About locking that port down: Scaleway security-group rules only accept fixed addresses, and the GPU nodes get a fresh address every time one boots, so there is no clean single rule that scopes 5432 to the cluster. Leave 5432 open and say one honest sentence to the user: the database port is reachable from the internet, protected by the long random password that never leaves the env files; a tighter lock is possible later with a private network if they ever want it.
6. Add the GPU settings to the vault (update pattern, one new version), pull on the VM (`/opt/castle/repo/infra/secrets/pull-env.sh`), then restart the dashboard:

   ```
   KUBECONFIG_DATA=<base64 from step 3>
   CASTLE_K8S_NAMESPACE=castle
   NOTULEN_WORKER_IMAGE=rg.<region>.scw.cloud/castle/notulen-worker:v1
   CASTLE_IMAGE_PULL_SECRET=castle-registry
   DB_URL_OPS=postgresql://castle:<POSTGRES_PASSWORD>@<SERVER_IP>:5432/castle
   ```

   In /opt/castle/repo: `docker compose --env-file /opt/castle/castle.env up -d notulen`.
7. Wait for the step 1 build to finish (`tail /tmp/castle-gpu-build.log`; the last line on success is the pushed image reference). Do not start the end-to-end test before the image is in the registry.
8. End-to-end verify with a short test recording. Tell the user plainly first: the first GPU meeting takes a few minutes extra while the machine boots; after that, recordings that arrive while the node is still warm start right away. They record about a minute of talk in the dashboard and stop. You watch `kubectl get jobs -n castle -w`: a Job named `notulen-<first 20 characters of the job id>` appears (it requests one GPU), `kubectl get nodes` shows a node booting (3 to 5 minutes the first time), the Job completes, and the recording's row in the dashboard finishes. If dispatch fails, the recording still lands through the CPU path automatically; nothing is lost, but investigate before calling this phase done.

If any step fails twice on the same error: stop, stay on CPU transcription, tell the user what that means (recordings still work, a one-hour meeting just takes hours instead of minutes), and record the skip in the phase 10 memory note. The GPU tier can be added later by just asking Claude.

**Verify**: image in the registry, cluster ready, KUBECONFIG_DATA set on the server, notulen restarted, one test recording processed through a K8s Job and finished in the dashboard (or the CPU fallback consciously chosen and recorded).

## Phase 10: finish

1. Write a memory note in `.claude/memory/` (a short file plus one index line in MEMORY.md): domain, server IP, region, instance type, bucket name, cluster and registry if the GPU tier ran, which phases ran, what was skipped (for example the Anthropic key, or the GPU tier and why), the expiry date of the castle-vm API key (renewing it is an ask-Claude job), and the date. No passwords in memory, ever.
2. Print the three addresses on their own lines: the website, `cloud.` and `notulen.`.
3. Explain the daily loop in four lines: open a terminal, run `claude agents --dangerously-skip-permissions` in this folder, say what you want in plain words, and after I push, the change is live in about 2 minutes.
4. Explain how bigger work goes, in three lines: for anything beyond a tiny change I first ask questions, then write the plan down as an issue on their GitHub page where they can read it and follow progress, then build it. Show them the issues page address once (github.com/<owner>/claude-castle/issues).
5. Tell them: if anything ever looks broken, just say "something is broken" and I will investigate (the troubleshoot skill).
