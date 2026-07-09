# infra/secrets: the vault

Secrets do not live in files anymore. They live in **the vault**: one Scaleway Secret Manager secret named `castle-env` whose content is the stack's complete KEY=value environment, the exact text docker compose needs. Every change is a **new version** of that one secret; old versions stay available, so a bad change is one version away from undone. `config/castle.env` on the laptop keeps only non-secret settings (domain, region, repo, server IP).

## The two scripts

- **`push-env.sh <env-file>`** (laptop): creates the `castle-env` secret on first use, then pushes the file's content as a new version. Uses the scw CLI already configured on the laptop. Never prints the content.
- **`pull-env.sh`** (VM): fetches the latest version over the Secret Manager HTTPS API with the scoped key in `/opt/castle/scw-secrets.env` and atomically rewrites the cache at `/opt/castle/castle.env` (mode 600). On ANY fetch failure it keeps the existing cache and exits 0 with a warning: the cache is the resilience, and a Secret Manager blip never takes the stack down.

The auto-deploy loop (`infra/auto-deploy/steps/10-fetch.sh`) runs `pull-env.sh` every cycle and treats a changed cache as a reason to redeploy. So **rotation = push a new version and wait one deploy cycle**. No ssh needed.

## The scoped VM key

The powerful laptop key never lands on the VM. Onboard creates an IAM application named `castle-vm`, one policy granting `SecretManagerReadOnly` plus `SecretManagerSecretAccess` scoped to the project (both are needed; ReadOnly alone can list secrets but not read their values), and an API key for that application with a one-year expiry (some organizations require one; renewing it in a year is an ask-Claude job). That key and the vault's secret id go into `/opt/castle/scw-secrets.env`, mode 600.

Worst case if the VM is ever compromised: the attacker reads this project's secrets, which the VM could already read. They cannot create servers, delete data, or run up a bill.

## Cost

Cents per month. Scaleway bills Secret Manager per stored version and per batch of API calls; one secret with a handful of versions plus a pull every two minutes stays in the cents range (check the Scaleway pricing page for current numbers).

## Honest note: a future hardening

The env content itself still contains `S3_ACCESS_KEY` / `S3_SECRET_KEY` for Notulen's audio bucket, and those currently reuse the powerful laptop key (the GPU registry pull secret does too). Giving storage its own scoped key is a sensible future hardening; it is a separate concern from the vault and deliberately left as-is for now.
