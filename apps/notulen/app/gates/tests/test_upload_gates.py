"""Unit tests for the chunked-upload gates.

Covers what 2026-05-12 lost: the dashboard now streams every chunk to disk
during recording so iOS tab eviction cannot drop the blob. These tests pin
the gate invariants that make recovery possible. The tempfile-assembly half
lives with its implementation in ``core/sessions/test_session_files.py``;
the HTTP routes themselves are exercised end-to-end in the iOS smoke +
recovery scripts (issue #271).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from apps.notulen.app.gates import (
    check_assembled_size,
    check_chunk_seq,
    check_chunk_size,
)
from apps.notulen.app.gates.assembled_size import MIN_ASSEMBLED_BYTES
from apps.notulen.app.gates.chunk_size import MAX_CHUNK_BYTES


# ── chunk size gate ─────────────────────────────────────────────────────────

def test_chunk_size_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        check_chunk_size(0)
    assert exc.value.status_code == 400


def test_chunk_size_rejects_oversize():
    with pytest.raises(HTTPException) as exc:
        check_chunk_size(MAX_CHUNK_BYTES + 1)
    assert exc.value.status_code == 413


def test_chunk_size_accepts_typical_opus_chunk():
    # 5 sec @ 64kbps Opus ≈ 40KB
    check_chunk_size(40_000)


# ── chunk seq gate ──────────────────────────────────────────────────────────

def test_chunk_seq_first_chunk_is_next():
    assert check_chunk_seq(1, None) == "next"


def test_chunk_seq_consecutive_is_next():
    assert check_chunk_seq(5, 4) == "next"


def test_chunk_seq_replay_is_duplicate():
    # sendBeacon doubles fire pagehide. Idempotency keeps the server from
    # corrupting the assembled tempfile by re-appending the same bytes.
    assert check_chunk_seq(3, 5) == "duplicate"
    assert check_chunk_seq(5, 5) == "duplicate"


def test_chunk_seq_gap_rejects_409():
    # Browser missed an ack and skipped a seq. Server must reject so the
    # browser falls back to /api/upload/state and re-sends from last_seq+1.
    with pytest.raises(HTTPException) as exc:
        check_chunk_seq(7, 4)
    assert exc.value.status_code == 409
    assert "expected seq 5" in exc.value.detail


def test_chunk_seq_zero_or_negative_rejected():
    with pytest.raises(HTTPException) as exc:
        check_chunk_seq(0, None)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException):
        check_chunk_seq(-1, 4)


# ── assembled size gate ─────────────────────────────────────────────────────

def test_assembled_size_rejects_empty_session():
    # Finalize before any chunks arrived (e.g. browser crashed after /start).
    # Without this gate we'd push a 0-byte object to S3 and dispatch a GPU
    # job that transcribes silence.
    with pytest.raises(HTTPException) as exc:
        check_assembled_size(0)
    assert exc.value.status_code == 400


def test_assembled_size_rejects_below_min():
    with pytest.raises(HTTPException) as exc:
        check_assembled_size(MIN_ASSEMBLED_BYTES - 1)
    assert exc.value.status_code == 400


def test_assembled_size_accepts_real_meeting():
    # 5-min meeting at 64kbps ≈ 2.4 MB
    check_assembled_size(2_400_000)
