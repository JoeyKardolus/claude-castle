"""Daily Job cost-ceiling accessor — read at CALL time.

Accessor, not a module constant (module-standard config doctrine): tests
monkeypatch ``MAX_DAILY_JOBS`` mid-run and the next call sees it.
Promoted out of ``_config.py`` when that grab-bag dissolved in the
de-slop campaign (ADR-0011: one public callable per file).

FAILURE POLICY: pure env read. A malformed ``MAX_DAILY_JOBS`` raises
ValueError at the call site (Tier 1 — a silently-applied default would
disable the cost ceiling).
"""

from __future__ import annotations

import os


def max_daily_jobs() -> int:
    """Cost circuit-breaker: max Jobs per 24h on app=castle-worker."""
    return int(os.environ.get("MAX_DAILY_JOBS", "50"))
