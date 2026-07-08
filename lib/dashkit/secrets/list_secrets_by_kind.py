"""Read all active secrets of one rotation_kind (for rotation CronJobs)."""
from __future__ import annotations

from typing import Any

from dashkit.secrets.rows import (
    SECRET_COLUMNS,
    row_to_dict,
)


def list_secrets_by_kind(conn, kind: str) -> list[dict[str, Any]]:
    """Return every secret with a given rotation_kind, excluding suspended.

    Used by scheduled rotation CronJobs to find the secrets they own
    without hardcoding names. For example, the postgres CronJob calls
    ``list_secrets_by_kind(conn, "postgres")`` and iterates the results.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {SECRET_COLUMNS}
            FROM ops_secrets
            WHERE rotation_kind = %s AND suspended = false
            ORDER BY name
            """,
            (kind,),
        )
        rows = cur.fetchall()
    return [row_to_dict(row) for row in rows]
