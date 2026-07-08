"""Read one secrets-registry row by name."""
from __future__ import annotations

from typing import Any, Optional

from dashkit.secrets.rows import (
    SECRET_COLUMNS,
    row_to_dict,
)


def get_secret(conn, name: str) -> Optional[dict[str, Any]]:
    """Return one secret row by name, with computed status. None if missing."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {SECRET_COLUMNS}
            FROM ops_secrets
            WHERE name = %s
            """,
            (name,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return row_to_dict(row)
