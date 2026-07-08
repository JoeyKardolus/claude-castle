"""Assembled-recording size gate for POST /api/upload/finalize.

FAILURE POLICY: raises ``HTTPException`` (400/413) with Dutch user copy;
nothing is swallowed. Without the lower bound we would push a 0-byte
object to S3 and dispatch a GPU job that transcribes silence.
"""
from __future__ import annotations

from fastapi import HTTPException

MIN_ASSEMBLED_BYTES = 10_000
MAX_ASSEMBLED_BYTES = 100_000_000  # ≈ 3 hours of opus


def check_assembled_size(num_bytes: int) -> None:
    """Reject assembled tempfiles that are obviously empty or oversize."""
    if num_bytes < MIN_ASSEMBLED_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Geen opname ontvangen (te klein om te verwerken)",
        )
    if num_bytes > MAX_ASSEMBLED_BYTES:
        raise HTTPException(status_code=413, detail="Opname te groot (max 100MB)")
