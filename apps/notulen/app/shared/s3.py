"""S3 client for the notulen dashboard (cached at module level).

Owns: the boto3 client wiring (endpoint/region/creds from S3_* env vars,
retry config). Does NOT own which keys are written — callers build their own keys
(``core.sessions.upload_audio``). boto3 imports lazily so the package
imports without it (IEC 62304 gate import hygiene).

FAILURE POLICY: this module never swallows — boto3/botocore exceptions
propagate to the caller, which decides per seam (uploads are Tier-1:
a lost recording is the product).
"""
from __future__ import annotations

import os

_s3_client = None


def get_s3():
    """Lazy-initialised boto3 S3 client configured from S3_* env vars.

    ``S3_ENDPOINT`` (optional) points at a non-AWS S3 (MinIO, Scaleway,
    ...); ``S3_ACCESS_KEY``/``S3_SECRET_KEY`` (optional) override boto3's
    default credential chain.
    """
    global _s3_client
    if _s3_client is None:
        import boto3  # noqa: PLC0415 — keep package importable without boto3
        from botocore.config import Config  # noqa: PLC0415

        from apps.notulen.app.shared.config import S3_REGION  # noqa: PLC0415

        kwargs = {}
        if os.environ.get("S3_ENDPOINT"):
            kwargs["endpoint_url"] = os.environ["S3_ENDPOINT"]
        if os.environ.get("S3_ACCESS_KEY"):
            kwargs["aws_access_key_id"] = os.environ["S3_ACCESS_KEY"]
            kwargs["aws_secret_access_key"] = os.environ["S3_SECRET_KEY"]
        _s3_client = boto3.client(
            "s3",
            region_name=S3_REGION,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
            **kwargs,
        )
    return _s3_client
