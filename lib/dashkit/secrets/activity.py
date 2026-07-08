"""ops_activity logging for secret-rotation events.

One helper wrapping ``dashkit.core.audit.log_activity`` with the
``ops_activity`` table ({domain}_activity pattern) so every caller in
this package uses the same action_type vocabulary:

    secret_rotate_start / secret_rotate_success / secret_rotate_failure /
    secret_alert_open

FAILURE POLICY: best-effort (Tier 2) — inherited from
``dashkit.core.audit.log_activity``, which swallows and logs by its own
declared policy. The structural rotation rows themselves are written by
the record_rotation_* modules and PROPAGATE.
"""
from __future__ import annotations

from typing import Optional

from dashkit.core import audit as _audit

_OPS_ACTIVITY_TABLE = "ops_activity"


def log_secret_activity(
    conn,
    *,
    action_type: str,
    user: Optional[str],
    detail: dict,
) -> None:
    _audit.log_activity(
        conn,
        _OPS_ACTIVITY_TABLE,
        action_type=action_type,
        user=user or "cronjob",
        detail=detail,
    )
