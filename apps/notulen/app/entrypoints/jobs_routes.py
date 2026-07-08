"""Job read/delete routes (GET/DELETE /api/jobs*).

Owns the JSON projection of ``notulen_jobs`` rows and the deletion policy.
Does NOT own row writes (``shared/update_job.py``) or the pipeline.

FAILURE POLICY: DB unavailability is 503 on detail routes; the list route
returns an empty list (fail-open read — the SPA shows "Nog geen opnames"
rather than an error page; sub-50ms polling makes a 5xx storm worse than a
blank list). Deletion is fail-closed: the S3 audio delete propagates, so we
never claim deleted while the (privacy-relevant) audio object remains.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from dashkit.core import audit as _audit
from dashkit.core.auth import get_user
from dashkit.core.db import get_db

from apps.notulen.app.shared.config import S3_BUCKET
from apps.notulen.app.shared.jobs_table import ensure_jobs_table
from apps.notulen.app.shared.s3 import get_s3
from apps.notulen.app.shared.slug import slugify

router = APIRouter()


@router.get("/api/jobs")
def _list_jobs(limit: int = 50):
    conn = get_db()
    if not conn:
        # Documented fail-open read: the SPA polls this every 5s; render an
        # empty list rather than an error storm. Detail routes 503 instead.
        return {"jobs": []}
    try:
        ensure_jobs_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status, title, meeting_date, attendees, duration_secs, "
                "error, created_by, created_at, completed_at "
                "FROM notulen_jobs ORDER BY created_at DESC LIMIT %s",
                (min(max(limit, 1), 200),),
            )
            return {
                "jobs": [
                    {
                        "id": str(row[0]),
                        "status": row[1],
                        "title": row[2],
                        "meeting_date": row[3].isoformat() if row[3] else None,
                        "attendees": row[4] or [],
                        "duration_secs": row[5],
                        "error": row[6],
                        "created_by": row[7],
                        "created_at": row[8].isoformat() if row[8] else None,
                        "completed_at": row[9].isoformat() if row[9] else None,
                    }
                    for row in cur.fetchall()
                ]
            }
    finally:
        conn.close()


@router.get("/api/jobs/{job_id}")
def _get_job(job_id: str):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        ensure_jobs_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status, title, meeting_date, attendees, duration_secs, "
                "transcript_text, output_markdown, error, created_by, created_at, completed_at "
                "FROM notulen_jobs WHERE id = %s",
                (job_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Job not found")
            return {
                "id": str(row[0]),
                "status": row[1],
                "title": row[2],
                "meeting_date": row[3].isoformat() if row[3] else None,
                "attendees": row[4] or [],
                "duration_secs": row[5],
                "transcript": row[6],
                "notulen": row[7],
                "error": row[8],
                "created_by": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
                "completed_at": row[11].isoformat() if row[11] else None,
            }
    finally:
        conn.close()


@router.delete("/api/jobs/{job_id}")
def _delete_job(job_id: str, request: Request):
    """Delete a recording and its notulen row + S3 audio.

    The committed markdown (if GitHub publishing is configured) stays in git
    ten-year retention audit trail (Article 10(8)); we drop the DB row + S3
    audio only. Issue #336 / parent #331.
    """
    user = get_user(request.headers.get("authorization"))
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        ensure_jobs_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT s3_audio_key, title, meeting_date FROM notulen_jobs WHERE id = %s",
                (job_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Job not found")
            s3_key, title, _meeting_date = row

            # Fail-closed: if the audio object can't be deleted, abort the
            # whole delete (500) so we never report success while the
            # recording still sits in S3. S3 deletes are idempotent, so the
            # user's retry converges. (Replaces a pre-2026-06-12 silent
            # swallow that could orphan audio.)
            if s3_key:
                get_s3().delete_object(Bucket=S3_BUCKET, Key=s3_key)

            cur.execute("DELETE FROM notulen_jobs WHERE id = %s", (job_id,))
        _audit.log_activity(
            conn, "notulen_activity",
            "notulen_deleted", user,
            detail={"job_id": job_id, "title": title},
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/api/jobs/{job_id}/download")
def _download_notulen(job_id: str):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        ensure_jobs_table(conn)
        with conn.cursor() as cur:
            # Markdown is downloadable as soon as it exists, even while the
            # job is still `committing` (awaiting its git commit, ADR-0020) —
            # the user shouldn't wait on git to grab their own minutes.
            cur.execute(
                "SELECT title, meeting_date, output_markdown FROM notulen_jobs "
                "WHERE id = %s AND output_markdown IS NOT NULL",
                (job_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Notulen not found or not ready")
            title, meeting_date, markdown = row
            month = meeting_date.isoformat()[:7]
            filename = f"{month}_{slugify(title)}.md"
            return Response(
                content=markdown,
                media_type="text/markdown; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
    finally:
        conn.close()
