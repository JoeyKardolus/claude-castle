"""Shared contracts and helpers for the notulen dashboard (``shared/`` layer).

Module map (one concern per file, ADR-0011):
    config.py      — env-var-derived constants (TEMPLATE_PATH, S3_BUCKET, ...)
    slug.py        — the one slug grammar for notulen filenames/paths
    s3.py          — lazy boto3 S3 client (S3_* env config)
    jobs_table.py  — notulen_jobs schema bootstrap (DDL, idempotent)
    update_job.py  — allowlisted UPDATE on notulen_jobs (Tier-1, propagates)

Constants in ``config.py`` are imported from their module directly; this
seam re-exports the callables.
"""
from __future__ import annotations

from apps.notulen.app.shared.jobs_table import ensure_jobs_table
from apps.notulen.app.shared.s3 import get_s3
from apps.notulen.app.shared.slug import slugify
from apps.notulen.app.shared.update_job import (
    UPDATABLE_JOB_COLUMNS,
    update_job,
)

__all__ = [
    "UPDATABLE_JOB_COLUMNS",
    "ensure_jobs_table",
    "get_s3",
    "slugify",
    "update_job",
]
