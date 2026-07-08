"""Git publication of generated notulen (``core/publish/``).

``complete`` means committed to git, not merely transcribed (ADR-0020).

Module map (one public callable per file, ADR-0011):
    github/target_path.py             — target_path(meeting_date, title) -> repo path
    github/github_writer.py           — commit_notulen_to_github(...) via Contents API (#336)
    retry/finalize_commit.py          — finalize_commit(...): commit then mark complete
    retry/stuck_commits.py            — stuck_committing_ids(rows, now): page-worthy strands
    retry/alert_stuck_committing.py   — alert_stuck_committing(job_ids): throttled ops page
    retry/git_writer_loop.py          — git_writer_loop() 30s daemon (GPU-path catch-up)
"""
from __future__ import annotations

from apps.notulen.app.core.publish.retry.alert_stuck_committing import (
    alert_stuck_committing,
)
from apps.notulen.app.core.publish.retry.finalize_commit import finalize_commit
from apps.notulen.app.core.publish.retry.git_writer_loop import git_writer_loop
from apps.notulen.app.core.publish.github.github_writer import (
    commit_notulen_to_github,
)
from apps.notulen.app.core.publish.retry.stuck_commits import (
    STUCK_COMMIT_THRESHOLD_SEC,
    stuck_committing_ids,
)
from apps.notulen.app.core.publish.github.target_path import target_path

__all__ = [
    "STUCK_COMMIT_THRESHOLD_SEC",
    "alert_stuck_committing",
    "commit_notulen_to_github",
    "finalize_commit",
    "git_writer_loop",
    "stuck_committing_ids",
    "target_path",
]
