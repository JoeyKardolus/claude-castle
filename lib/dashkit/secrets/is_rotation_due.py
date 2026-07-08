"""Pure age-policy decision: should this secret rotate now?"""
from __future__ import annotations

from typing import Any


def is_rotation_due(secret: dict[str, Any]) -> bool:
    """Return True if the secret should be rotated now based on age policy.

    Scheduled CronJobs use this instead of just rotating every run, so
    a weekly cron doesn't actually rotate a 30-day credential more than
    once per month. We rotate at 80% of max_age_days (e.g. day 24 for
    a 30-day policy), giving a 6-day cushion before the PrometheusRule
    fires SecretOverdue.
    """
    age_days = secret.get("age_days")
    max_age_days = secret.get("max_age_days", 0)
    if age_days is None:
        # Unknown state (never rotated) counts as due.
        return True
    return age_days >= int(max_age_days * 0.80)
