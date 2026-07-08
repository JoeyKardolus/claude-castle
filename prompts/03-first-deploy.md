You are helping a beginner put their services live on their new server for the first time. `config/castle.env` has their domain, region, GitHub username and `SERVER_IP`; DNS for `@`, `notulen` and `cloud` already resolves to that IP (verify with `dig +short` first; if not, stop and send them back to `prompts/02-create-my-server.md`). Announce every phase in one plain sentence before running it. Run remote steps over ssh.

1. Connect as root: `ssh root@$SERVER_IP`. Update packages (`apt-get update && apt-get upgrade -y`).
2. Create a user `castle` with sudo rights, copy root's authorized SSH key to it, and explain: day-to-day the server runs things as this user, not as the all-powerful root.
3. Install Docker Engine and the compose plugin from Docker's official apt repository. Verify with `docker --version` and `docker compose version`. Add `castle` to the `docker` group.
4. Clone THEIR repo (from the GitHub username in castle.env) to `/opt/castle/repo`, owned by `castle`. If the repo is private, set up access with a fine-grained deploy token via `gh`, read-only, and explain where it is stored on the server.
5. Create `/opt/castle/castle.env` from `config/castle.env.example` in the repo. Go through it value by value: copy the known values (domain, email for HTTPS certificates), ask the user in plain words for anything personal, and GENERATE strong random secrets (e.g. `openssl rand -base64 24`) for the database password, Nextcloud admin password, and the notulen basic-auth password. Tell the user clearly: all secrets live in `/opt/castle/castle.env` on the server, show them how to view it later (`ssh castle@IP cat /opt/castle/castle.env`), and suggest saving the notulen login in their password manager or a note.
6. Set file permissions on castle.env to 600 (only the owner can read it) and say why in one sentence.
7. Start everything: in `/opt/castle/repo`, run `docker compose --env-file /opt/castle/castle.env up -d --build`. Explain: each service (website, notulen, Nextcloud, database, Caddy) runs in its own container, and Caddy fetches HTTPS certificates automatically, which can take a minute.
8. Install the auto-deploy units from `infra/systemd/` in the repo (copy, `systemctl enable --now`). Explain: from now on, every push to GitHub is picked up within about 2 minutes and redeployed, so push = deploy.
9. Verify, with retries while certificates settle: `curl -fsSL -o /dev/null -w '%{http_code}' https://{domain}` and the same for `notulen.{domain}` and `cloud.{domain}`. All three should return a 2xx/3xx status. Also `docker compose ps` should show all services up/healthy.
10. Tell the user to open `https://{their-domain}` in their browser and confirm they see the starter page with a padlock.

If any phase fails, stop, explain what happened in plain words, and fix it before moving on. Never paste secret values into the chat; refer to them by name.

At the end, report what you did in plain words: what now runs on the server, the three working addresses, where the secrets live, and that pushing to GitHub now deploys automatically.
