"""Pins the 80%-of-max-age rotation trigger.

A weekly cron must not rotate a 30-day credential more than once per
month, and the trigger must fire BEFORE the SecretOverdue PromRule
(100% of max age) so rotation always wins the race against the page.
"""
from __future__ import annotations

from dashkit.secrets import is_rotation_due


def test_due_at_80_percent_of_max_age() -> None:
    assert is_rotation_due({"age_days": 24, "max_age_days": 30}) is True


def test_not_due_below_threshold() -> None:
    assert is_rotation_due({"age_days": 23, "max_age_days": 30}) is False


def test_never_rotated_counts_as_due() -> None:
    """age_days=None is the never-rotated state — must rotate now."""
    assert is_rotation_due({"age_days": None, "max_age_days": 30}) is True
