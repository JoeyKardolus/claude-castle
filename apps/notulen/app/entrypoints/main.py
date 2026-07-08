"""Notulen dashboard app assembly — notulen.{CASTLE_DOMAIN}.

Records audio in-browser via the MediaRecorder API, transcribes with
faster-whisper (medium, CPU) or the GPU notulen-worker pod, and generates
structured meeting minutes (notulen) with the Claude API following
the notulen template (language via MINUTES_LANGUAGE, default Dutch).

This file is the thin bootstrap only (apps/dashboards overlay convention):
build the ``DashkitConfig``, call ``make_dashboard_app``, attach the route
modules, register the startup hooks. Routes live beside it in
``entrypoints/``; domain logic lives in ``core/``.

FAILURE POLICY: startup hooks run threads that own their own policies
(see ``core/publish/git_writer_loop.py``, ``core/sessions/``); app
assembly itself fails loud — a bad config must kill the container.
"""
from __future__ import annotations

import threading

from dashkit.core.app_factory import (
    DashkitConfig,
    make_dashboard_app,
)

from apps.notulen.app.core.publish.retry.git_writer_loop import git_writer_loop
from apps.notulen.app.core.sessions.recovery import (
    recover_interrupted_jobs,
)
from apps.notulen.app.core.sessions.stale_cleanup import (
    cleanup_stale_recordings_loop,
)
from apps.notulen.app.entrypoints.health_routes import (
    router as health_router,
)
from apps.notulen.app.entrypoints.jobs_routes import (
    router as jobs_router,
)
from apps.notulen.app.entrypoints.spa_routes import (
    router as spa_router,
)
from apps.notulen.app.entrypoints.upload_routes import (
    router as upload_router,
)

config = DashkitConfig(
    domain="notulen",
    title="Castle Notulen",
    activity_table="notulen_activity",
    ai_calls_table="notulen_ai_calls",
    sync_status_table="notulen_sync_status",
    sync_token_env_var="NOTULEN_SYNC_TOKEN",
    health_checks=[],
)
app = make_dashboard_app(config)

app.include_router(spa_router)
app.include_router(upload_router)
app.include_router(jobs_router)
app.include_router(health_router)


@app.on_event("startup")
def _start_git_writer():
    """Start the background git writer thread (ADR-0020 commit catch-up)."""
    threading.Thread(target=git_writer_loop, daemon=True).start()


@app.on_event("startup")
def _start_stale_recording_cleanup():
    """Hourly auto-abort of forgotten recording sessions older than 6h."""
    threading.Thread(target=cleanup_stale_recordings_loop, daemon=True).start()


@app.on_event("startup")
def _recover_interrupted_jobs():
    """Reset jobs stuck in processing state (server crashed mid-job).

    GPU-path jobs are only failed when their K8s Job is gone — see
    ``core/sessions/recovery.py`` (2026-05-21 incident).
    """
    recover_interrupted_jobs()
