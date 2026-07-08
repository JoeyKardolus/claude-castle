"""Open an idempotent stale-credential alert row."""
from __future__ import annotations

from dashkit.secrets.activity import log_secret_activity


def open_alert(
    conn,
    *,
    secret_id: int,
    severity: str,
    message: str,
    source: str,
) -> int:
    """Open an alert on a secret, or no-op if an equivalent open alert
    already exists.

    Equivalence is (secret_id, severity, source) — the unique index in
    the migration enforces "at most one open alert per triple". Returns
    the alert row id (new or existing). Alerts are auto-resolved by
    ``record_rotation_finish`` on the next successful rotation.
    """
    if severity not in ("info", "warn", "critical"):
        raise ValueError(f"invalid severity: {severity!r}")
    if source not in ("sweep", "prometheus", "manual"):
        raise ValueError(f"invalid source: {source!r}")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ops_secret_alerts
                (secret_id, severity, message, source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (secret_id, severity, source) WHERE resolved = false
                DO NOTHING
            RETURNING id
            """,
            (secret_id, severity, message, source),
        )
        row = cur.fetchone()
        if row:
            alert_id = row[0]
            log_secret_activity(
                conn,
                action_type="secret_alert_open",
                user=source,
                detail={
                    "alert_id": alert_id,
                    "secret_id": secret_id,
                    "severity": severity,
                    "source": source,
                    "message": message[:500],
                },
            )
            return alert_id

        # No insert happened → existing open alert. Fetch its id.
        cur.execute(
            """
            SELECT id FROM ops_secret_alerts
            WHERE secret_id = %s AND severity = %s AND source = %s
              AND resolved = false
            """,
            (secret_id, severity, source),
        )
        existing = cur.fetchone()
        return existing[0] if existing else -1
