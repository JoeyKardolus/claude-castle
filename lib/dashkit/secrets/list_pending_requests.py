"""Find rotations requested from the UI but not yet processed."""
from __future__ import annotations

from typing import Any


def list_pending_requests(conn) -> list[dict[str, Any]]:
    """Return secrets whose rotation has been requested but not yet
    processed by the sweep runner. Used by the sweep CronJob to find work."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, scaleway_id, rotation_kind, rotation_requested_at
            FROM ops_secrets
            WHERE rotation_requested_at IS NOT NULL
              AND suspended = false
            ORDER BY rotation_requested_at
            """
        )
        return [
            {
                "id": row[0],
                "name": row[1],
                "scaleway_id": row[2],
                "rotation_kind": row[3],
                "rotation_requested_at": row[4].isoformat() if row[4] else None,
            }
            for row in cur.fetchall()
        ]
