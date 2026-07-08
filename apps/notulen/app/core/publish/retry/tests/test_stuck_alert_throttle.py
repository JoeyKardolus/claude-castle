"""Throttle + swallow invariants of the stuck-commit ops page (ADR-0020, #364).

What would break without these: the git-writer loop polls every 30s, so a
multi-day GITHUB_NOTULEN_PAT outage would page ~2880 times a day and drown
the signal; and a broken notifier (alerts stack down) raising out of the
page call would kill the commit loop — the exact loop whose job is to
retry the commit. Both behaviours are documented Tier-2 decisions in
``alert_stuck_committing.py`` (module-standard §5.2 load-bearing swallow,
pinned here).
"""
from __future__ import annotations

import pytest

import importlib

from apps.notulen.app.core.publish.retry.alert_stuck_committing import (
    alert_stuck_committing,
)

# The publish __init__ re-exports the callable under the same name as its
# module, so attribute-style module imports resolve to the function; go via
# importlib to monkeypatch the module's throttle state.
alert_mod = importlib.import_module(
    "apps.notulen.app.core.publish.retry.alert_stuck_committing"
)


@pytest.fixture(autouse=True)
def _reset_throttle(monkeypatch):
    """Module-global throttle state resets per test (own-module seam)."""
    monkeypatch.setattr(alert_mod, "_last_stuck_commit_alert_ts", 0.0)


def test_pages_once_then_throttles_within_the_hour():
    pages: list[str] = []
    clock = {"t": 1_000_000.0}

    def notifier(subject: str, body: str) -> None:
        pages.append(body)

    alert_stuck_committing(["job-1"], notifier=notifier, now=lambda: clock["t"])
    clock["t"] += 30  # next 30s loop tick
    alert_stuck_committing(["job-1"], notifier=notifier, now=lambda: clock["t"])
    assert len(pages) == 1, "second tick inside the hour must be throttled"

    clock["t"] += 3600  # past the throttle window
    alert_stuck_committing(["job-1"], notifier=notifier, now=lambda: clock["t"])
    assert len(pages) == 2, "a still-stuck job re-pages after an hour"


def test_page_names_the_stuck_jobs():
    pages: list[str] = []
    alert_stuck_committing(
        ["job-a", "job-b"],
        notifier=lambda subject, body: pages.append(body),
        now=lambda: 1_000_000.0,
    )
    assert "2 notulen job(s)" in pages[0]
    assert "job-a, job-b" in pages[0]


def test_broken_notifier_never_raises_into_the_commit_loop():
    def broken(subject: str, body: str) -> None:
        raise ConnectionError("alerts stack down")

    # Must not raise: the commit retry loop survives a dead alert path.
    alert_stuck_committing(["job-1"], notifier=broken, now=lambda: 1_000_000.0)
