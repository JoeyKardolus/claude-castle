"""Schema bootstrap for the ``notulen_jobs`` table.

Owns: CREATE TABLE + idempotent live-table column additions + the ADR-0020
backfill. Does NOT own row updates (``shared/update_job.py``) or row reads
(route modules query through their own cursors).

FAILURE POLICY: Tier-1 — DDL errors propagate (ADR-0008). A dashboard that
cannot bootstrap its table must fail its request loudly, not render an
empty job list.
"""
from __future__ import annotations

_jobs_table_ready = False


def ensure_jobs_table(conn) -> None:
    """Create/upgrade ``notulen_jobs`` once per process. Caller owns ``conn``."""
    global _jobs_table_ready
    if _jobs_table_ready:
        return
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notulen_jobs (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                status          TEXT NOT NULL DEFAULT 'pending',
                title           TEXT NOT NULL,
                meeting_date    DATE NOT NULL,
                attendees       TEXT[],
                duration_secs   INTEGER,
                s3_audio_key    TEXT,
                transcript_text TEXT,
                output_markdown TEXT,
                error           TEXT,
                created_by      TEXT NOT NULL DEFAULT 'anonymous',
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                completed_at    TIMESTAMPTZ,
                last_chunk_seq  INTEGER,
                agenda          TEXT
            )
        """)
        # Live-table additions (idempotent): pre-existing deployments add the
        # columns on first boot after this change ships.
        cur.execute(
            "ALTER TABLE notulen_jobs ADD COLUMN IF NOT EXISTS last_chunk_seq INTEGER"
        )
        cur.execute(
            "ALTER TABLE notulen_jobs ADD COLUMN IF NOT EXISTS agenda TEXT"
        )
        cur.execute(
            "ALTER TABLE notulen_jobs ADD COLUMN IF NOT EXISTS output_commit_url TEXT"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS notulen_jobs_created_idx "
            "ON notulen_jobs (created_at DESC)"
        )
        # ADR-0020: `complete` now means committed to git. Backfill legacy
        # rows that were marked complete before the commit landed (markdown
        # generated, no commit URL) to `committing` so git_writer_loop picks
        # them up. Idempotent: once committed they carry output_commit_url and
        # never match again. This self-heals the #364 stuck notulen on deploy.
        cur.execute(
            "UPDATE notulen_jobs SET status = 'committing' "
            "WHERE status = 'complete' "
            "AND output_commit_url IS NULL "
            "AND output_markdown IS NOT NULL"
        )
    conn.commit()
    _jobs_table_ready = True
