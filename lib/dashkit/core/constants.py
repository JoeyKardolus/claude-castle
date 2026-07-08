"""Shared infra constants for the dashkit ecosystem.

S3_BUCKET / S3_REGION are defined here directly (plain env-var reads) so
dashkit stays self-contained — it ships in lean images that bundle
nothing else; keep it free of cross-package imports.

Model defaults live in the ``dashkit_ai_config`` table read by
``dashkit.ai``.
"""

from __future__ import annotations

import os

S3_BUCKET: str = os.environ.get("S3_BUCKET", "castle")
S3_REGION: str = os.environ.get("S3_REGION", "us-east-1")

__all__ = [
    "S3_BUCKET",
    "S3_REGION",
]
