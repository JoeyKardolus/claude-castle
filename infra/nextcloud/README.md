# Nextcloud — security stance

- Nextcloud (at `https://cloud.<your-domain>`) holds your private files, so it gets the strictest login: password **plus** a 6-digit code from an authenticator app (TOTP two-factor auth), enforced for **every** user, no exceptions.
- After first boot, log in as the admin, go to Settings → Security, and set up TOTP for yourself. Every new user does the same at their first login.
- Then flip enforcement on: `infra/nextcloud/nextcloud-2fa-enforce.sh` (run `--check` first to see who is enrolled). The script is fail-closed: it refuses to enforce while any user still lacks a second factor, so nobody can be locked out.
- Your data lives in the `nextcloud_data` docker volume (files + config) and the `postgres_data` volume (metadata, in its own `NEXTCLOUD_DB_NAME` database) — back those two up and you can rebuild everything else from this repo.
- `postgres-init.sh` runs automatically on the first boot of an empty postgres volume and creates Nextcloud's database + user; you never run it by hand.
- Background jobs (previews, reminders, cleanup) are handled by the `nextcloud-cron` container in docker-compose.yml — nothing to install on the VM.
- Nextcloud is reached only through Caddy over HTTPS; the container itself is never exposed to the internet.
