<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# lib/dashkit/core/CLAUDE.md

`dashkit.core` — bootstrap + observability primitives every dashboard calls. Seam exports `make_dashboard_app`, `get_user`, `get_db` plus the `audit/`, `sync/` submodules. One public callable per file. Self-contained: imports nothing outside dashkit.

Parent overlay: `lib/dashkit/CLAUDE.md`.

## File map

| File | Job |
|---|---|
| `app_factory.py` | `make_dashboard_app(config)` (+ `DashkitConfig`) — wires audit/AI/sync/inspector + static route onto a FastAPI app. Routes fail open per route. |
| `auth.py` | `get_user(authorization)` — Caddy forward-auth Basic header → username; fails open to `"anonymous"`. |
| `db.py` | `get_db()` (+ `DB_URL`) — ops-compartment connection. `DB_URL_OPS` with `DB_URL` migration fallback. Replicated (not imported) twin of `_conn.py`. |
| `constants.py` | `S3_BUCKET` / `S3_REGION` env knobs. Self-contained; do not re-couple to app code. |
| `inspector.py` | `run_checks(conn, checks)` (+ `HealthCheck`) — per-check error → `healthy: false` row, never 500. |
| `identifiers.py` | `validate_table_name(name)` — `[a-z_][a-z0-9_]*` allowlist gate before any table-name f-string. |
| `_frontend_static.py` | `/static/dashkit/*` route (internal to `app_factory`). |
| `audit/` | Per-domain `{domain}_activity` log (package — own overlay). |
| `sync/` | `{domain}_sync_status` table + heartbeat router factory (package — own overlay). |
| `tests/test_identifier_allowlist.py` | Pins the table-name allowlist. (Tests in `tests/` per ADR-0038.) |

## Gotchas

- `db.py` `DB_URL_OPS`→`DB_URL` fallback is the migration-window safety net — keep both until every container sets `DB_URL_OPS`.
- `constants.py` trimmed 2026-06-12: `ARCHIVE_BUCKET`/`FRONTEND_URL`/model-name defaults deleted (zero callers); model defaults now live in the `dashkit_ai_config` table read by `dashkit.ai`.
- Every `{domain}_*` table name flows through `identifiers.validate_table_name` before interpolation.
