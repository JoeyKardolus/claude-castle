"""Commit-gating invariants for notulen jobs (ADR-0020, issue #364/#366).

What broke: a missing GITHUB_NOTULEN_PAT made every commit raise, the error
was swallowed, and the job was marked `complete` with no commit URL — the
dashboard reported success while nothing reached git or the cloud. These
tests pin the fix at the level of external behaviour:

- A job reaches `complete` ONLY when a commit URL exists. A failed commit
  leaves it `committing` for the retry loop, never `complete`.
- The git-writer retry has NO time window (the old 24h cutoff was shorter
  than the 48h alert-silence that hid #364).
- A job stuck `committing` past the threshold is flagged so ops gets paged;
  fresh jobs are not.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apps.notulen.app.core.publish.retry.finalize_commit import finalize_commit
from apps.notulen.app.core.publish.retry.git_writer_loop import (
    _COMMITTING_SELECT_SQL,
)
from apps.notulen.app.core.publish.retry.stuck_commits import (
    STUCK_COMMIT_THRESHOLD_SEC,
    stuck_committing_ids,
)


# ── finalize_commit: complete means committed ────────────────────────────────

def test_finalize_marks_complete_only_with_commit_url():
    updates: list[dict] = []
    url = finalize_commit(
        "job-1", "Standup", "2026-05-26", "# Notulen",
        committer=lambda *args: "https://github.com/x/commit/abc",
        updater=lambda job_id, **fields: updates.append({"job_id": job_id, **fields}),
    )
    assert url == "https://github.com/x/commit/abc"
    assert updates == [{
        "job_id": "job-1",
        "status": "complete",
        "output_commit_url": "https://github.com/x/commit/abc",
    }]


def test_finalize_failed_commit_stays_committing():
    """A swallowed commit failure (the #364 footgun) must NOT mark complete."""
    updates: list[dict] = []

    def boom(*_args):
        raise RuntimeError("401 Bad credentials (GITHUB_NOTULEN_PAT missing)")

    url = finalize_commit(
        "job-2", "Standup", "2026-05-26", "# Notulen",
        committer=boom,
        updater=lambda job_id, **fields: updates.append({"job_id": job_id, **fields}),
    )
    assert url is None
    # Never touched the row → it stays `committing` for git_writer_loop.
    assert updates == []


# ── stuck_committing_ids: page on a stranded job, ignore fresh ────────────────

def test_stuck_committing_flags_old_ignores_fresh():
    now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
    fresh = now - timedelta(seconds=STUCK_COMMIT_THRESHOLD_SEC - 60)
    stale = now - timedelta(seconds=STUCK_COMMIT_THRESHOLD_SEC + 60)
    rows = [("fresh-job", fresh), ("stuck-job", stale)]
    assert stuck_committing_ids(rows, now) == ["stuck-job"]


def test_stuck_committing_skips_null_timestamp():
    now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
    assert stuck_committing_ids([("no-ts", None)], now) == []


# ── retry window: regression guard for the dropped 24h cutoff ─────────────────

def test_git_writer_query_has_no_time_window():
    # ADR-0020: a credential outage can outlast any fixed window, so the loop
    # must select every uncommitted job regardless of age.
    assert "status = 'committing'" in _COMMITTING_SELECT_SQL
    assert "output_commit_url IS NULL" in _COMMITTING_SELECT_SQL
    assert "INTERVAL" not in _COMMITTING_SELECT_SQL.upper()
    assert "24 HOUR" not in _COMMITTING_SELECT_SQL.upper()
