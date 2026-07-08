"""dashkit.core — bootstrap + observability primitives for the dashboards.

Module map (ADR-0011 — one public callable per file):

    app_factory.py        make_dashboard_app(config) (+ DashkitConfig) — the
                          one entry every dashboard calls
    auth.py               get_user(authorization) — Caddy forward-auth username
    db.py                 get_db() (+ DB_URL) — ops-compartment connections
    constants.py          S3_BUCKET / S3_REGION env knobs
    inspector.py          run_checks(conn, checks) (+ HealthCheck)
    audit/                per-domain {domain}_activity log (package)
    sync/                 sync-status table + heartbeat router (package)
    identifiers.py        validate_table_name(name) — SQL table-name allowlist gate
    _frontend_static.py   /static/dashkit/* route (internal to app_factory)

Curated re-exports below cover the cross-package surface; the live
dashboards (notulen, lit) also import the submodules directly
(``dashkit.core.db``, ``dashkit.core.auth``, ...) — a sanctioned
pre-reset import style kept for compatibility.
"""
from __future__ import annotations

from dashkit.core.app_factory import (
    DashkitConfig,
    make_dashboard_app,
)
from dashkit.core.auth import get_user
from dashkit.core.db import get_db
from dashkit.core.identifiers import validate_table_name

__all__ = [
    "DashkitConfig",
    "get_db",
    "get_user",
    "make_dashboard_app",
    "validate_table_name",
]
