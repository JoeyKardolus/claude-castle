"""Ops page for notulen markdown stranded uncommitted in Postgres.

Owns the page copy and the in-process throttle. Does NOT own stuck
detection (``core/publish/stuck_commits.py``) or the retry itself
(``core/publish/git_writer_loop.py``). Split out of ``stuck_commits.py``
on 2026-06-12: the loop imported it as a cross-file ``_``-private, which
made it an undeclared second public callable (ADR-0011).

FAILURE POLICY: documented Tier-2 swallow — a broken alert path must
never break the commit loop (ADR-0020 / issue #364). Throttled in-process
to one page per hour, mirroring ``core/minutes/gpu_dispatch.py``; the
throttle resets on container restart, which is fine — a restart is itself
a recovery signal worth re-paging on. ``notifier`` is an injectable
collaborator; the standalone default logs at ERROR level — wire your own
paging stack in by injecting a notifier.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable

from apps.notulen.app.core.publish.retry.stuck_commits import (
    STUCK_COMMIT_THRESHOLD_SEC,
)

logger = logging.getLogger("notulen")

# Throttle the stuck-commit page to one per hour so a multi-day credential
# outage pages once an hour, not once per 30s poll.
_STUCK_COMMIT_ALERT_THROTTLE_SEC = 3600
_last_stuck_commit_alert_ts: float = 0.0


def _fan_out(subject: str, body: str) -> None:
    """Default notifier: log-only. Inject a ``notifier`` collaborator to
    wire this into a real paging/alerting stack."""
    logger.error("%s\n%s", subject, body)


def alert_stuck_committing(
    job_ids: list[str],
    *,
    notifier: Callable[[str, str], None] = _fan_out,
    now: Callable[[], float] = time.time,
) -> None:
    """Page ops when notulen markdown is stranded uncommitted in Postgres."""
    global _last_stuck_commit_alert_ts
    current = now()
    if current - _last_stuck_commit_alert_ts < _STUCK_COMMIT_ALERT_THROTTLE_SEC:
        return
    _last_stuck_commit_alert_ts = current
    try:
        notifier(
            "⚠️ notulen: minutes stuck uncommitted in Postgres",
            f"{len(job_ids)} notulen job(s) generated markdown but cannot commit "
            f"to the configured GitHub repo for >{STUCK_COMMIT_THRESHOLD_SEC // 60} min.\n"
            f"Jobs: {', '.join(job_ids[:10])}\n\n"
            "Almost always NOTULEN_GITHUB_PAT (missing/expired/unauthorised). "
            "The markdown is safe in notulen_jobs.output_markdown and commits "
            "automatically once the PAT is restored. Throttled to one page per hour.",
        )
    except Exception:
        # Documented Tier-2 swallow: a broken notifier must never break
        # the commit loop (see module FAILURE POLICY).
        logger.exception("Failed to page on stuck-committing notulen jobs")
