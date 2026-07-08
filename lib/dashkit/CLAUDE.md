# lib/dashkit/CLAUDE.md

Shared FastAPI library powering the operator dashboards. **Library, not application.**

## Declared shape

**Exception: consumed library** — no entrypoints, no gates; three
subpackages, each a deep module with a sealed `__init__.py` (docstring
module map + curated re-exports + `__all__`, one public callable per
file):

| Subpackage | Seam | One job |
|---|---|---|
| `dashkit.core` | `make_dashboard_app`, `get_user`, `get_db` (+ `audit/`, `sync/`, `constants`, `inspector` submodules) | dashboard bootstrap: SSO header auth, DB connections, activity log, sync-status, health checks, `/static/dashkit/*` |
| `dashkit.ai` | `call_claude`, `ensure_ai_calls_table` | THE single LLM metering seam — every Claude call lands in `{domain}_ai_calls` (cost accounting) |
| `dashkit.secrets` | `list_secrets`, `get_secret`, `record_rotation_start/finish`, `sweep_stale_secrets`, … | the only WRITE path for `ops_secrets` / `ops_secret_rotations` / `ops_secret_alerts` |
| `frontend/` | static assets | served by `app_factory` at `/static/dashkit/*` |

## Consumers

In this repo, dashkit is consumed by the **notulen** dashboard
(`apps/notulen/`), which imports it as `dashkit` (installed as a uv
workspace member from `lib/dashkit/`).

Worker images **exclude dashkit by design**: `import dashkit` from the
GPU worker (`apps/notulen/entrypoints/worker.py`) is a boundary
violation — the worker is a self-contained twin. If a worker suddenly
needs dashkit, you've crossed an architectural boundary — route the
metric through a dashboard endpoint instead.

**dashkit is deliberately self-contained**: it imports nothing outside
its own package tree, so lean images can copy just this directory. Do
not re-couple it to app code.

## FAILURE POLICY (library doctrine)

Observability writes (activity log, AI-call accounting) are Tier-2
best-effort — fail open, logged at WARNING, never break the feature.
Secrets rotation state is Tier-1 — propagate. `get_user` fails open to
`"anonymous"` (the reverse proxy already authenticated upstream; the
audit row records the anonymous fact). Inspector checks convert
per-check exceptions to `healthy: false` rows — a broken check must
render as red, not 500 the dashboard.

## Schema

`DB_URL_OPS` (fallback `DB_URL`) is the one DSN dashkit connects with.
Feature modules own their table DDL (`audit/table.py`, `sync/table.py`,
`ai/ensure_ai_calls_table.py`) and create idempotently at first use.

## Tests

Tests live in each subpackage's `tests/` dir. They need no live DB —
`DB_URL` just has to be set to any placeholder before import.

## Don't

- Don't import dashkit from worker code (the worker image doesn't ship it).
- Don't hard-code dashboard-specific tables here (they belong in the dashboard's app code).
- Don't bypass `dashkit.ai.call_claude`; every Claude call must land in `{domain}_ai_calls`.
- Don't import app code from inside dashkit (self-containment).
