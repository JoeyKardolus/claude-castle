"""Shared fakes for the notulen entrypoints tests (ADR-0038 fixture extraction).

The /healthz handler pings the DB through a minimal cursor protocol —
cursor() → execute()/fetchone() → close(). The healthy-DB fake is
provided here as ``fake_healthz_db``.
"""
from __future__ import annotations

import pytest


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, *args, **kwargs):  # noqa: ARG002
        return None

    def fetchone(self):
        return (1,)


class _HealthyConn:
    def cursor(self):
        return _FakeCursor()

    def close(self):
        return None


@pytest.fixture
def fake_healthz_db():
    """A healthy-DB connection whose ping returns ``(1,)``."""
    return _HealthyConn()
