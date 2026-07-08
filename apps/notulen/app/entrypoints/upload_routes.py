"""Chunked-upload routes (POST /api/upload/*).

The recorder streams audio chunks to the dashboard during recording rather
than POSTing one blob on stop. This survives iOS tab eviction (phone lock /
app switch), which was the 2026-05-12 lost-recording failure mode.

Lifecycle:
    POST /api/upload/start    → INSERT row (status=recording), return job_id
    POST /api/upload/chunk    → append-write chunk to /tmp/notulen/<id>/audio.webm
    POST /api/upload/finalize → upload assembled tempfile to S3, dispatch pipeline
    POST /api/upload/abort    → mark aborted, remove tempfile
    GET  /api/upload/state    → resume probe for the recovery banner

Validation lives in ``gates/``; session tempfiles + the pipeline live in
``core/``. FAILURE POLICY: DB unavailability is 503; gate violations are
4xx (validation per gates/); duplicate finalize/abort are idempotent acks
so the browser state machine stays simple.
"""
from __future__ import annotations

import threading
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from dashkit.core.auth import get_user
from dashkit.core.db import get_db

from apps.notulen.app.core.minutes.process_job import process_job
from apps.notulen.app.core.sessions.files import session_files
from apps.notulen.app.core.sessions.upload_audio import (
    upload_assembled_to_s3,
)
from apps.notulen.app.gates import (
    check_assembled_size,
    check_chunk_seq,
    check_chunk_size,
    check_queue_capacity,
    parse_meeting_date,
)
from apps.notulen.app.shared.jobs_table import ensure_jobs_table
from apps.notulen.app.shared.update_job import update_job

router = APIRouter()

# Per-job in-process lock serialises append-writes for one session. Different
# sessions write to different files so they don't contend.
_session_locks: dict[str, threading.Lock] = {}
_session_locks_guard = threading.Lock()


def _lock_for(job_id: str) -> threading.Lock:
    """Per-session append lock. Created lazily; never explicitly removed —
    map churn is bounded by the queue cap and the stale-cleanup loop."""
    with _session_locks_guard:
        lock = _session_locks.get(job_id)
        if lock is None:
            lock = threading.Lock()
            _session_locks[job_id] = lock
        return lock


def _row_for(conn, job_id: str) -> tuple[str, int | None, str, str, list[str], str]:
    """Fetch (status, last_chunk_seq, title, meeting_date, attendees, agenda)
    or raise 404. Caller is responsible for the connection lifecycle.

    Raises 404 for malformed UUIDs too — the recovery scan needs to be able
    to drop stale/corrupted IndexedDB entries based on a single 404 reply.
    """
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recording session not found")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, last_chunk_seq, title, meeting_date, attendees, agenda "
            "FROM notulen_jobs WHERE id = %s",
            (job_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Recording session not found")
    return row


@router.post("/api/upload/start")
def _upload_start(
    request: Request,
    title: str = Form(...),
    meeting_date: str = Form(...),
    attendees: str = Form(""),
    agenda: str = Form(""),
):
    """Open a new recording session and return its job_id."""
    parsed_date = parse_meeting_date(meeting_date)
    attendee_list = [name.strip() for name in attendees.split(",") if name.strip()]
    user = get_user(request.headers.get("authorization"))
    title_clean = title.strip()
    if not title_clean:
        raise HTTPException(status_code=400, detail="Onderwerp is verplicht")

    job_id = str(uuid.uuid4())
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        check_queue_capacity(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notulen_jobs "
                "(id, status, title, meeting_date, attendees, agenda, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (job_id, "recording", title_clean, parsed_date,
                 attendee_list, agenda, user),
            )
        conn.commit()
    finally:
        conn.close()

    session_files(job_id).create()

    return {"ok": True, "job_id": job_id}


@router.post("/api/upload/chunk")
async def _upload_chunk(
    job: str,
    seq: int,
    chunk: UploadFile = File(...),
):
    """Append a single audio chunk to the session tempfile.

    Idempotent on duplicate seq (sendBeacon may double-fire on pagehide).
    Out-of-order chunks return 409 — the browser is expected to re-send from
    the gap. Both the file write and the last_chunk_seq update happen under a
    per-session lock so concurrent in-flight POSTs can't interleave.
    """
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        ensure_jobs_table(conn)
        status, last_seq, _title, _date, _attendees, _agenda = _row_for(conn, job)
    finally:
        conn.close()
    if status != "recording":
        raise HTTPException(
            status_code=409,
            detail=f"Session not accepting chunks (status={status})",
        )

    chunk_bytes = await chunk.read()
    check_chunk_size(len(chunk_bytes))
    verdict = check_chunk_seq(seq, last_seq)
    if verdict == "duplicate":
        return {"ok": True, "ack": seq, "duplicate": True, "last_seq": last_seq}

    audio_path = session_files(job).audio_path
    if not audio_path.parent.exists():
        raise HTTPException(status_code=410, detail="Session tempdir missing")

    with _lock_for(job):
        # Double-check seq under the lock: a parallel POST may have advanced
        # last_seq between our earlier read and this write.
        conn = get_db()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        try:
            _status, last_seq_now, _title, _date, _attendees, _agenda = _row_for(conn, job)
        finally:
            conn.close()
        verdict_now = check_chunk_seq(seq, last_seq_now)
        if verdict_now == "duplicate":
            return {"ok": True, "ack": seq, "duplicate": True, "last_seq": last_seq_now}

        with audio_path.open("ab") as chunk_sink:
            chunk_sink.write(chunk_bytes)
        update_job(job, last_chunk_seq=seq)

    return {"ok": True, "ack": seq, "last_seq": seq}


@router.post("/api/upload/finalize")
def _upload_finalize(job: str):
    """Close the session, push the assembled audio to S3, dispatch the pipeline."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        ensure_jobs_table(conn)
        status, last_seq, title, meeting_date, attendees, agenda = _row_for(conn, job)
    finally:
        conn.close()

    if status in ("pending", "transcribing", "structuring"):
        # Idempotent: finalize was already called once — likely a sendBeacon
        # race with the explicit POST. Don't re-upload, just ack.
        return {"ok": True, "job_id": job, "already_finalized": True}
    if status != "recording":
        raise HTTPException(
            status_code=409,
            detail=f"Session cannot be finalized (status={status})",
        )

    files = session_files(job)
    if not files.audio_path.exists():
        raise HTTPException(status_code=410, detail="Session tempfile missing")

    with _lock_for(job):
        size = files.audio_path.stat().st_size
        try:
            check_assembled_size(size)
        except HTTPException:
            update_job(job, status="failed", error="Lege opname (geen chunks)")
            files.cleanup()
            raise

        s3_key = upload_assembled_to_s3(job)
        update_job(job, status="pending")

    attendee_list = list(attendees) if attendees else []
    date_str = meeting_date.isoformat() if meeting_date else ""
    thread = threading.Thread(
        target=process_job,
        args=(job, s3_key, title, date_str, attendee_list, agenda or ""),
        daemon=True,
    )
    thread.start()

    return {"ok": True, "job_id": job, "s3_key": s3_key, "size": size}


@router.post("/api/upload/abort")
def _upload_abort(job: str):
    """Discard an in-progress recording session."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        ensure_jobs_table(conn)
        status, *_rest = _row_for(conn, job)
    finally:
        conn.close()
    if status != "recording":
        # Aborting a non-recording session is a no-op (e.g. user hit abort
        # twice or after finalize completed); return ok to keep the client
        # state machine simple.
        return {"ok": True, "already_closed": True}

    update_job(job, status="aborted")
    session_files(job).cleanup()
    return {"ok": True}


@router.get("/api/upload/state")
def _upload_state(job: str):
    """Lightweight status probe for the recovery banner.

    Returns the seq the server last accepted so the browser knows where to
    resume from after a page reload. Returns 404 for unknown job_id so the
    recovery banner can drop stale IndexedDB sessions.
    """
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        ensure_jobs_table(conn)
        status, last_seq, *_rest = _row_for(conn, job)
    finally:
        conn.close()
    return {"ok": True, "status": status, "last_seq": last_seq}
