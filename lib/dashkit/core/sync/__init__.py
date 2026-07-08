"""dashkit.core.sync — sync-status table + heartbeat endpoint factory.

Each domain dashboard tracks one external "did the sync run?" signal
(e.g. git-cloud-sync.sh). The schema is identical per domain; the
heartbeat endpoint is built per table by ``make_heartbeat_router``.

The endpoint is bearer-token authenticated AND wrapped behind Caddy's
``@internal_path 404`` block so it's unreachable from the public
internet regardless of the token.

Module map (ADR-0011 — one public callable per file):

    make_heartbeat_router.py  POST heartbeat router factory (+ SyncHeartbeat model)
    fetch_sync_status.py      read the single-row status payload
    table.py                  ensure_sync_status_table(conn, table_name) — lazy
                              single-row table bootstrap

FAILURE POLICY: heartbeat writes PROPAGATE as HTTP errors (503 on
missing token/DB) — a sync reporter must know its report was dropped.
Table bootstrap is best-effort (logged) because the read path degrades
to ``{"status": "stale"}`` anyway.
"""
from __future__ import annotations

from dashkit.core.sync.fetch_sync_status import (
    fetch_sync_status,
)
from dashkit.core.sync.make_heartbeat_router import (
    SyncHeartbeat,
    make_heartbeat_router,
)
from dashkit.core.sync.table import (
    ensure_sync_status_table,
)

__all__ = [
    "SyncHeartbeat",
    "ensure_sync_status_table",
    "fetch_sync_status",
    "make_heartbeat_router",
]
