"""Read the full secrets registry with computed age + status."""
from __future__ import annotations

from typing import Any

from dashkit.secrets.rows import (
    SECRET_COLUMNS,
    row_to_dict,
)


def list_secrets(conn) -> list[dict[str, Any]]:
    """Return every ops_secrets row with computed age_days + status.

    Ordered by computed next_due_at ascending (most urgent first),
    then by name. Suspended rows are included (caller decides how
    to render them).
    """
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {SECRET_COLUMNS}
            FROM ops_secrets
            ORDER BY (last_rotated_at + make_interval(days => max_age_days)) NULLS FIRST, name
            """
        )
        rows = cur.fetchall()
    return [row_to_dict(row) for row in rows]
