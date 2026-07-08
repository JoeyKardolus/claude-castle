"""Walk the registry, open alerts for overdue secrets."""
from __future__ import annotations

from dashkit.secrets.list_secrets import list_secrets
from dashkit.secrets.open_alert import open_alert


def sweep_stale_secrets(conn) -> dict[str, int]:
    """Walk ops_secrets, open alerts for anything stale/overdue.
    Returns per-status counts observed during the sweep.

    Called by the rotate-sweep CronJob every 5 minutes
    (a scheduled sweep job). Resolution is
    handled by ``record_rotation_finish`` on the next successful
    rotation, not here.
    """
    secrets = list_secrets(conn)
    stats = {"fresh": 0, "warn": 0, "stale": 0, "overdue": 0, "unknown": 0}

    for secret in secrets:
        stats[secret["status"]] = stats.get(secret["status"], 0) + 1
        if secret["suspended"]:
            continue
        secret_id = secret["id"]
        age_days = secret["age_days"]
        max_age = secret["max_age_days"]

        # Warn: status 'stale' (age >= 100% of max_age)
        # Critical: status 'overdue' (age >= 150% of max_age)
        if secret["status"] == "stale" and age_days is not None:
            open_alert(
                conn,
                secret_id=secret_id,
                severity="warn",
                source="sweep",
                message=(
                    f"{secret['name']} is {age_days}d old; policy is {max_age}d. "
                    f"Rotate soon."
                ),
            )
        elif secret["status"] == "overdue" and age_days is not None:
            open_alert(
                conn,
                secret_id=secret_id,
                severity="critical",
                source="sweep",
                message=(
                    f"{secret['name']} is {age_days}d old; policy is {max_age}d "
                    f"({int(age_days * 100 / max_age)}% over). "
                    f"Rotation required immediately."
                ),
            )

    return stats
