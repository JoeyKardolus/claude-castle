"""Recording-session lifecycle (``core/sessions/``).

Module map (one public callable per file, ADR-0011):
    files.py          — session_files(job_id) -> SessionFiles (tempdir store)
    upload_audio.py   — upload_assembled_to_s3(job_id) -> s3_key
    stale_cleanup.py  — cleanup_stale_recordings_loop() daemon (6 h retirement)
    recovery.py       — recover_interrupted_jobs() startup orphan sweep
"""
from __future__ import annotations

from apps.notulen.app.core.sessions.files import (
    SessionFiles,
    session_files,
)
from apps.notulen.app.core.sessions.recovery import (
    recover_interrupted_jobs,
)
from apps.notulen.app.core.sessions.stale_cleanup import (
    cleanup_stale_recordings_loop,
)
from apps.notulen.app.core.sessions.upload_audio import (
    upload_assembled_to_s3,
)

__all__ = [
    "SessionFiles",
    "cleanup_stale_recordings_loop",
    "recover_interrupted_jobs",
    "session_files",
    "upload_assembled_to_s3",
]
