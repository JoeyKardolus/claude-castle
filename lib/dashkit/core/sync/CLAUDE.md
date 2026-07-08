<!-- Per-area overlay. Loaded automatically when Claude Code opens a file in this directory tree. Read the closest overlay first. -->

# lib/dashkit/core/sync/CLAUDE.md

`dashkit.core.sync` — per-domain `{domain}_sync_status` single-row table + the bearer-token heartbeat endpoint factory. Each dashboard tracks one external "did the sync run?" signal. One callable per file (ADR-0011).

Parent overlay: `lib/dashkit/CLAUDE.md`.

## File map

| File | Job |
|---|---|
| `make_heartbeat_router.py` | POST heartbeat router factory (+ `SyncHeartbeat` pydantic body). Bearer-token authed AND behind Caddy's `@internal_path 404`. |
| `fetch_sync_status.py` | Read the single-row status payload. |
| `table.py` | `ensure_sync_status_table(conn, table_name)` — lazy single-row bootstrap; name gated through `core.identifiers.validate_table_name`. |

## Gotchas

- Heartbeat **writes propagate** as HTTP errors (503 on failure); the table bootstrap is the one Tier-2 swallow (read returns `stale`, write surfaces its own UPDATE error).
- The endpoint is double-gated: bearer token + Caddy internal-path 404 (unreachable from the public internet regardless of token).
