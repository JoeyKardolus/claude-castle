"""Shared ops_secrets row machinery: column list, status buckets, row→dict.

Single source of truth for the SELECT column order and the dict shape
returned by ``list_secrets`` / ``get_secret`` / ``list_secrets_by_kind``
(the pre-split module carried three verbatim copies of the shaping
block — a drift hazard this file removes). Shared by the
read modules above; surfaced on the package seam.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

# Status buckets keyed off age vs max_age_days.
#  fresh    = age / max < 0.80
#  warn     = 0.80 <= age / max < 1.00
#  stale    = 1.00 <= age / max < 1.50
#  overdue  = age / max >= 1.50   (also fires SecretCritical in Prometheus)
#  unknown  = last_rotated_at IS NULL (never rotated yet — seed state)
_STATUS_WARN_RATIO = 0.80
_STATUS_STALE_RATIO = 1.00
_STATUS_OVERDUE_RATIO = 1.50

# Column order matters: row_to_dict indexes into it positionally.
SECRET_COLUMNS = """id, name, scaleway_id, description, category, rotation_kind,
       max_age_days, last_rotated_at,
       last_rotated_at + make_interval(days => max_age_days) AS next_due_at,
       consumers, runbook_url, rotation_requested_at, suspended,
       created_at, updated_at"""


def _compute_status(
    last_rotated_at: Optional[datetime],
    max_age_days: int,
) -> tuple[str, Optional[int]]:
    """Return (status_label, age_days_or_None)."""
    if last_rotated_at is None:
        return ("unknown", None)
    now = datetime.now(timezone.utc)
    # last_rotated_at should already be tz-aware from Postgres TIMESTAMPTZ
    if last_rotated_at.tzinfo is None:
        last_rotated_at = last_rotated_at.replace(tzinfo=timezone.utc)
    age_seconds = (now - last_rotated_at).total_seconds()
    age_days = max(0, int(age_seconds // 86400))
    ratio = (age_seconds / 86400) / max_age_days
    if ratio < _STATUS_WARN_RATIO:
        status = "fresh"
    elif ratio < _STATUS_STALE_RATIO:
        status = "warn"
    elif ratio < _STATUS_OVERDUE_RATIO:
        status = "stale"
    else:
        status = "overdue"
    return (status, age_days)


def row_to_dict(row: tuple) -> dict[str, Any]:
    """Shape one ``SECRET_COLUMNS`` row into the public dict contract."""
    status, age_days = _compute_status(row[7], row[6])
    consumers = row[9] if isinstance(row[9], list) else (
        json.loads(row[9]) if row[9] else []
    )
    return {
        "id": row[0],
        "name": row[1],
        "scaleway_id": row[2],
        "description": row[3],
        "category": row[4],
        "rotation_kind": row[5],
        "max_age_days": row[6],
        "last_rotated_at": row[7].isoformat() if row[7] else None,
        "next_due_at": row[8].isoformat() if row[8] else None,
        "consumers": consumers,
        "runbook_url": row[10],
        "rotation_requested_at": row[11].isoformat() if row[11] else None,
        "suspended": row[12],
        "created_at": row[13].isoformat() if row[13] else None,
        "updated_at": row[14].isoformat() if row[14] else None,
        "age_days": age_days,
        "status": status,
    }
