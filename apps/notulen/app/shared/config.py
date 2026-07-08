"""Env-var-derived constants shared across notulen dashboard layers.

Owns: the template path and the S3 bucket/region aliases. Does NOT own
the S3 client (``shared/s3.py``) or any DB access (``shared/update_job.py``).
``S3_BUCKET``/``S3_REGION`` are re-exported from dashkit's constants —
dashkit is the single source of truth for platform-wide S3 config; this
module only narrows the import surface for notulen code.
"""
from __future__ import annotations

import os
from pathlib import Path

from dashkit.core.constants import (
    S3_BUCKET as _S3_BUCKET,
    S3_REGION as _S3_REGION,
)

# Notulen markdown template. Default: the copy shipped in this repo at
# apps/notulen/inputs/notulen_template.md; override with NOTULEN_TEMPLATE
# to point at your own (e.g. a bind-mounted file).
_DEFAULT_TEMPLATE = Path(__file__).resolve().parents[2] / "inputs" / "notulen_template.md"
TEMPLATE_PATH = Path(os.environ.get("NOTULEN_TEMPLATE", str(_DEFAULT_TEMPLATE)))

# S3 config (same bucket as the rest of the stack).
S3_BUCKET = _S3_BUCKET
S3_REGION = _S3_REGION
