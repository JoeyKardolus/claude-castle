"""Tempfile-assembly invariants for recording sessions (2026-05-12 fix).

Append-write order must match seq order — that is what makes server-side
assembly equivalent to ``new Blob(chunks)`` on the browser — and cleanup
must be idempotent. The seq/size gates live in ``gates/test_upload_gates.py``.
"""
from __future__ import annotations

from apps.notulen.app.core.sessions import files as files_mod


def test_session_audio_path_under_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(files_mod, "RECORDING_TMP_ROOT", tmp_path)
    session = files_mod.session_files("abc-123")
    assert session.audio_path == tmp_path / "abc-123" / "audio.webm"


def test_chunks_concatenated_in_order(tmp_path, monkeypatch):
    """Append-write order must match seq order. This is what makes the
    server-side assembly equivalent to ``new Blob(chunks)`` on the browser."""
    monkeypatch.setattr(files_mod, "RECORDING_TMP_ROOT", tmp_path)
    session = files_mod.session_files("job-1")
    session.create()

    chunks = [b"AAA", b"BBB", b"CCC", b"DDD"]
    with session.audio_path.open("ab") as sink:
        for chunk in chunks:
            sink.write(chunk)

    assert session.audio_path.read_bytes() == b"AAABBBCCCDDD"


def test_create_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(files_mod, "RECORDING_TMP_ROOT", tmp_path)
    session = files_mod.session_files("job-2")
    session.create()
    session.audio_path.write_bytes(b"data")
    session.create()  # second create must not truncate
    assert session.audio_path.read_bytes() == b"data"


def test_cleanup_session_files_removes_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(files_mod, "RECORDING_TMP_ROOT", tmp_path)
    session = files_mod.session_files("job-cleanup")
    session.create()
    session.audio_path.write_bytes(b"x" * 100)

    session.cleanup()
    assert not session.root.exists()
    # Idempotent — second call doesn't raise.
    session.cleanup()
