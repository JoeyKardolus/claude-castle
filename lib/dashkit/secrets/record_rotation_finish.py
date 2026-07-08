"""Close a rotation audit row (the finish half of the start→finish pair).

FAILURE POLICY: propagates (Tier 1) — same audit-trail reasoning as
``record_rotation_start``.
"""
from __future__ import annotations

from typing import Optional

from dashkit.secrets.activity import log_secret_activity


def record_rotation_finish(
    conn,
    *,
    rotation_id: int,
    secret_id: int,
    outcome: str,
    old_revision: Optional[int] = None,
    new_revision: Optional[int] = None,
    duration_ms: Optional[int] = None,
    error: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> None:
    """Finalize a rotation row and, on success, bump ops_secrets.last_rotated_at.

    outcome must be 'success' or 'failure'. On success, also clears any
    pending rotation_requested_at for the secret (so the UI sees "no
    pending request" as soon as the rotation completes) and resolves
    any open ops_secret_alerts rows for that secret.
    """
    if outcome not in ("success", "failure"):
        raise ValueError(f"invalid outcome: {outcome!r}")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ops_secret_rotations
            SET finished_at = NOW(),
                outcome = %s,
                old_revision = COALESCE(%s, old_revision),
                new_revision = COALESCE(%s, new_revision),
                duration_ms = COALESCE(%s, duration_ms),
                error = %s
            WHERE id = %s
            """,
            (outcome, old_revision, new_revision, duration_ms, error, rotation_id),
        )

        if outcome == "success":
            cur.execute(
                """
                UPDATE ops_secrets
                SET last_rotated_at = NOW(),
                    rotation_requested_at = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (secret_id,),
            )
            # Resolve any open alerts for this secret — a successful
            # rotation is the remedy they were requesting.
            cur.execute(
                """
                UPDATE ops_secret_alerts
                SET resolved = true,
                    resolved_at = NOW(),
                    resolved_by = 'rotation_runner',
                    resolve_note = %s
                WHERE secret_id = %s AND resolved = false
                """,
                (f"auto-resolved by rotation {rotation_id}", secret_id),
            )

    log_secret_activity(
        conn,
        action_type=f"secret_rotate_{outcome}",
        user=triggered_by,
        detail={
            "rotation_id": rotation_id,
            "secret_id": secret_id,
            "old_revision": old_revision,
            "new_revision": new_revision,
            "duration_ms": duration_ms,
            "error": error,
        },
    )
