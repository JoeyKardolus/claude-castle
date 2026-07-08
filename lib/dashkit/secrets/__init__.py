"""dashkit.secrets — registry + rotation-audit API for the ops secrets system.

This package is the single source of truth for secret rotation state:

    ops_secrets              — one row per managed credential.
    ops_secret_rotations     — append-only rotation audit trail.
    ops_secret_alerts        — standalone open-items for stale creds.
    ops_activity             — rotation events ({domain}_activity pattern,
                               written via dashkit.core.audit).

This package is the only WRITE path for these tables. Every rotation
runner and sweep job writes state through here,
so the audit trail has a single choke-point. Read-only SELECTs over
``ops_secret_rotations`` (e.g. a weekly verification job) are allowed.

Module map (ADR-0011 — one public callable per file):

    list_secrets.py           list_secrets(conn) — every row + computed age/status
    get_secret.py             get_secret(conn, name) — one row or None
    list_secrets_by_kind.py   list_secrets_by_kind(conn, kind) — for rotation CronJobs
    list_pending_requests.py  list_pending_requests(conn) — UI-requested rotations
    is_rotation_due.py        is_rotation_due(secret) — pure age-policy decision
    record_rotation_start.py  record_rotation_start(conn, ...) — open audit row
    record_rotation_finish.py record_rotation_finish(conn, ...) — close audit row
    open_alert.py             open_alert(conn, ...) — idempotent stale-cred alert
    sweep_stale_secrets.py    sweep_stale_secrets(conn) — walk registry, open alerts
    rows.py                   row_to_dict(row) (+ SECRET_COLUMNS) — shared SELECT
                              column list + row→dict shaping + status buckets
    activity.py               log_secret_activity(conn, ...) — ops_activity logging
                              (action_type vocabulary)

Conventions (unchanged since the original ops dashboard era):

- Caller owns the connection; all mutations run inside the caller's
  transaction so audit rows commit atomically with the triggering
  operation.
- Rotation events always go ``record_rotation_start`` → handler work →
  ``record_rotation_finish`` so every attempt lands in
  ``ops_secret_rotations`` even on failure.

FAILURE POLICY: registry reads/writes PROPAGATE (Tier 1 — rotation
state is structural; a silent drop would fake the NEN 7510 audit
trail). The ``ops_activity`` log rows ride on ``dashkit.core.audit``,
which is best-effort by its own declared policy (Tier 2).
"""
from __future__ import annotations

from dashkit.secrets.get_secret import get_secret
from dashkit.secrets.is_rotation_due import is_rotation_due
from dashkit.secrets.list_pending_requests import (
    list_pending_requests,
)
from dashkit.secrets.list_secrets import list_secrets
from dashkit.secrets.list_secrets_by_kind import (
    list_secrets_by_kind,
)
from dashkit.secrets.open_alert import open_alert
from dashkit.secrets.record_rotation_finish import (
    record_rotation_finish,
)
from dashkit.secrets.record_rotation_start import (
    record_rotation_start,
)
from dashkit.secrets.activity import log_secret_activity
from dashkit.secrets.rows import (
    SECRET_COLUMNS,
    row_to_dict,
)
from dashkit.secrets.sweep_stale_secrets import (
    sweep_stale_secrets,
)

__all__ = [
    "SECRET_COLUMNS",
    "get_secret",
    "is_rotation_due",
    "list_pending_requests",
    "list_secrets",
    "list_secrets_by_kind",
    "log_secret_activity",
    "open_alert",
    "record_rotation_finish",
    "record_rotation_start",
    "row_to_dict",
    "sweep_stale_secrets",
]
