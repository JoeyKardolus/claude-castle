# infra/ — how the castle runs

## The deploy contract

There is no deploy button and no CI service. **Pushing to `main` on GitHub IS the deploy.**

1. You push to `main`.
2. On the VM, a systemd timer (`auto-deploy.timer`, every 2 minutes) runs `infra/auto-deploy/auto-deploy.sh`.
3. It fetches `origin/main`; if nothing changed, it exits. If something changed, it fast-forwards the clone at `/opt/castle/repo`, rebuilds the images, restarts the containers, and rolls back any service whose healthcheck fails.
4. If `infra/caddy/Caddyfile` changed, Caddy validates the new config and reloads it (an invalid config is skipped — the live sites stay up).

One-time VM setup: create the `castle` user (in the `docker` group), clone the repo to `/opt/castle/repo`, write `/opt/castle/castle.env`, then run `sudo /opt/castle/repo/infra/systemd/install.sh`.

## Service map

| Service | Container | What it is | Reachable at |
|---|---|---|---|
| caddy | castle-caddy | HTTPS front door, routes all traffic | ports 80/443 |
| website | castle-website | public static page | `https://<domain>` |
| notulen | castle-notulen | meeting-minutes dashboard | `https://notulen.<domain>` (basic auth) |
| postgres | castle-postgres | database for notulen + Nextcloud | internal only |
| nextcloud | castle-nextcloud | private files/calendar/contacts | `https://cloud.<domain>` (own login + 2FA) |
| nextcloud-cron | castle-nextcloud-cron | Nextcloud background jobs | internal only |

## Where the secrets live

Everything secret is in **`/opt/castle/castle.env` on the VM** — never in git. Every variable it must define:

| Variable | What it is |
|---|---|
| `CASTLE_DOMAIN` | your domain, e.g. `castle.example.com` |
| `NOTULEN_BASIC_AUTH_USER` | login name for the notulen dashboard |
| `NOTULEN_BASIC_AUTH_HASH` | bcrypt hash of its password — generate with `docker compose exec caddy caddy hash-password`, and wrap it in single quotes in the env file (it contains `$` characters) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | the notulen database (also builds notulen's `DB_URL`) |
| `NEXTCLOUD_DB_NAME` / `NEXTCLOUD_DB_USER` / `NEXTCLOUD_DB_PASSWORD` | Nextcloud's own database in the same postgres |
| `NEXTCLOUD_ADMIN_USER` / `NEXTCLOUD_ADMIN_PASSWORD` | Nextcloud's first admin account (created on first boot) |
| `S3_ENDPOINT` / `S3_BUCKET` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | object storage for notulen uploads (any S3-compatible provider) |
| `S3_REGION` | optional, defaults to `fr-par` |
| `ANTHROPIC_API_KEY` | Claude API key, used by notulen to write the minutes |
| `MINUTES_LANGUAGE` | optional, language of the minutes, `nl` or `en`, defaults to `nl` |

Compose reads that file via `--env-file` (the deploy scripts pass it automatically). Running compose by hand:

```
docker compose --env-file /opt/castle/castle.env up -d
```

## Seeing what is going on

- App logs: `docker compose --env-file /opt/castle/castle.env logs -f notulen` (or any other service name)
- Deploy log: `/tmp/castle-deploy.log` on the VM, or `journalctl -u auto-deploy.service`
- Deploy state: `/var/lib/castle/last-deployed-sha` (and `last-failed-sha` when something broke)
