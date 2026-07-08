"""Open a rotation audit row (the start half of the start→finish pair).

FAILURE POLICY: propagates (Tier 1) — a rotation attempt that does not
land in ``ops_secret_rotations`` breaks the NEN 7510 §9.4.3 audit trail.
"""
from __future__ import annotations

from typing import Optional

from dashkit.secrets.activity import log_secret_activity


def record_rotation_start(
    conn,
    *,
    secret_id: int,
    trigger: str,
    triggered_by: str,
    run_id: str,
    runner_pod: Optional[str] = None,
) -> int:
    """Insert an in_progress rotation row, return its id.

    Caller is expected to call ``record_rotation_finish`` with the
    same rotation_id once the handler completes (or fails). Also
    writes a ``secret_rotate_start`` row to ``ops_activity``.
    """
    if trigger not in ("cron", "manual", "on_demand"):
        raise ValueError(f"invalid trigger: {trigger!r}")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ops_secret_rotations
                (secret_id, outcome, trigger, triggered_by, run_id, runner_pod)
            VALUES (%s, 'in_progress', %s, %s, %s, %s)
            RETURNING id
            """,
            (secret_id, trigger, triggered_by, run_id, runner_pod),
        )
        rotation_id = cur.fetchone()[0]

    log_secret_activity(
        conn,
        action_type="secret_rotate_start",
        user=triggered_by,
        detail={
            "rotation_id": rotation_id,
            "secret_id": secret_id,
            "trigger": trigger,
            "run_id": run_id,
            "runner_pod": runner_pod,
        },
    )
    return rotation_id
