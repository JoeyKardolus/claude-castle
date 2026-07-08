"""Per-upload pipeline state machine.

``process_job`` expects the audio already in S3 (the finalize route uploads
the assembled tempfile before kicking the background thread), prefers the
GPU notulen-worker pod, and falls back to local CPU whisper + Claude when
GPU is unavailable. Does NOT own the git commit retry — the markdown is
persisted ``committing`` first and ``core/publish`` takes it from there
(ADR-0020).

FAILURE POLICY: Tier-1 spine — any pipeline error marks the job ``failed``
with the error text (and that status write itself propagates if the DB is
down, killing the worker thread loudly). The activity-log INSERT is a
best-effort side-effect via dashkit. Session tempfiles are always cleaned
up.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from dashkit.core import audit as _audit
from dashkit.core.db import get_db

from apps.notulen.app.core.minutes.gpu_dispatch import try_dispatch_gpu
from apps.notulen.app.core.minutes.notulen_writer import generate_notulen
from apps.notulen.app.core.minutes.transcribe import transcribe_cpu
from apps.notulen.app.core.publish.retry.finalize_commit import finalize_commit
from apps.notulen.app.core.publish.github.target_path import target_path
from apps.notulen.app.core.sessions.files import session_files
from apps.notulen.app.shared.config import S3_BUCKET
from apps.notulen.app.shared.s3 import get_s3
from apps.notulen.app.shared.update_job import update_job

logger = logging.getLogger("notulen")

# Semaphore: only one CPU transcription at a time (VM memory constraint).
_transcription_lock = threading.Semaphore(1)


def process_job(
    job_id: str,
    s3_key: str,
    title: str,
    meeting_date: str,
    attendees: list[str],
    agenda: str = "",
) -> None:
    """Run the pipeline from an audio file already uploaded to S3."""
    try:
        # Prefer GPU worker if available; downloads audio from S3 in-cluster.
        if try_dispatch_gpu(job_id, s3_key, title, meeting_date, attendees, agenda):
            update_job(job_id, status="transcribing")
            session_files(job_id).cleanup()
            return  # GPU worker takes it from here, it'll update the DB itself
    except Exception:
        logger.exception("Failed to dispatch GPU job %s", job_id)
        update_job(job_id, status="failed", error="GPU dispatch failed")
        return

    # Local CPU fallback (dev environments, or when K8s is down). Pulls the
    # assembled audio from S3 to a fresh tempfile, runs the same pipeline.
    with _transcription_lock:
        try:
            update_job(job_id, status="transcribing")
            with tempfile.TemporaryDirectory() as tmpdir:
                raw_path = Path(tmpdir) / "audio.webm"
                get_s3().download_file(S3_BUCKET, s3_key, str(raw_path))
                wav_path = Path(tmpdir) / "audio.wav"
                result = subprocess.run(
                    ["ffmpeg", "-i", str(raw_path),
                     "-ar", "16000", "-ac", "1",
                     "-f", "wav", str(wav_path),
                     "-y", "-loglevel", "error"],
                    capture_output=True, text=True, timeout=300,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"ffmpeg failed: {result.stderr}")

                logger.info("Transcribing job %s...", job_id)
                transcript, duration = transcribe_cpu(wav_path)

            if not transcript.strip():
                raise RuntimeError("Transcription produced no text")

            update_job(
                job_id,
                status="structuring",
                transcript_text=transcript,
                duration_secs=int(duration),
            )

            logger.info("Generating notulen for job %s...", job_id)
            notulen_md = generate_notulen(
                transcript, title, meeting_date, attendees, job_id, agenda
            )

            git_path = target_path(meeting_date, title)
            # Persist markdown as `committing` first: it must survive a commit
            # failure. The status flips to `complete` only once the commit
            # lands (ADR-0020); git_writer_loop retries if it fails here.
            update_job(
                job_id,
                status="committing",
                output_markdown=notulen_md,
                completed_at=datetime.now(timezone.utc),
            )
            commit_url = finalize_commit(job_id, title, meeting_date, notulen_md)
            if commit_url:
                logger.info("Committed notulen for job %s: %s", job_id, commit_url)

            conn = get_db()
            if conn:
                try:
                    _audit.log_activity(
                        conn, "notulen_activity",
                        "notulen_generated", "system",
                        doc_path=git_path,
                        detail={
                            "job_id": job_id,
                            "title": title,
                            "duration_secs": int(duration),
                            "transcript_words": len(transcript.split()),
                        },
                    )
                    conn.commit()
                finally:
                    conn.close()

            logger.info("Job %s notulen ready (%s): %s", job_id,
                        "committed" if commit_url else "awaiting commit", git_path)

        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id, exc)
            update_job(job_id, status="failed", error=str(exc)[:2000])
        finally:
            session_files(job_id).cleanup()
