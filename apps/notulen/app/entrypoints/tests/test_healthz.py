"""External-behaviour tests for the notulen /healthz carve-out
(PRD #255 / slice #256, ADR-0013 amendment 2026-05-07).

Asserts the schema fixed by the ADR and the behaviour blackbox-exporter
relies on:

- Body shape: ``{"ok": bool, "checks": [{"name": str, "ok": bool, "ms": int}]}``.
- ``ok`` is True on a healthy DB; False on DB outage — no exception escapes.
- No leak: per-check keys are exactly ``{name, ok, ms}``; no ``error``
  field, no DB rows, no secret material.
- Sub-50 ms ceiling on a healthy DB ping (the cluster probe times out
  at 5 s; the spec budget is 50 ms; we test a looser 200 ms ceiling
  for CI jitter headroom).

We don't probe the live DB or load the full FastAPI app (``startup``
events touch real tables). The tested handler is this module's own route
function — co-located test, internal seam allowed (module-standard §4).
It returns a dict from a fake ``get_db``: no Postgres, no network, no
FastAPI TestClient — IEC-62304-gate-friendly.
"""
from __future__ import annotations

import time

import pytest

from apps.notulen.app.entrypoints import health_routes


@pytest.fixture
def healthz(monkeypatch, fake_healthz_db):
    """The /healthz handler with get_db patched to a healthy fake."""
    monkeypatch.setattr(health_routes, "get_db", lambda: fake_healthz_db)
    return health_routes._healthz


def test_healthz_shape_on_healthy_db(healthz) -> None:
    started = time.monotonic()
    body = healthz()
    elapsed_ms = int((time.monotonic() - started) * 1000)

    assert set(body.keys()) == {"ok", "checks"}
    assert body["ok"] is True
    assert isinstance(body["checks"], list) and len(body["checks"]) == 1
    check = body["checks"][0]
    assert set(check.keys()) == {"name", "ok", "ms"}
    assert check["name"] == "database"
    assert check["ok"] is True
    assert isinstance(check["ms"], int) and check["ms"] >= 0
    assert elapsed_ms < 200, f"/healthz took {elapsed_ms}ms (spec: <50ms)"


def test_healthz_carries_bad_news_without_raising(monkeypatch) -> None:
    """When DB ping fails, ok=False. No exception escapes."""
    def _broken_get_db():
        raise RuntimeError("simulated DB outage")

    monkeypatch.setattr(health_routes, "get_db", _broken_get_db)
    body = health_routes._healthz()

    assert body["ok"] is False
    assert body["checks"][0]["name"] == "database"
    assert body["checks"][0]["ok"] is False
    # ADR-0013 carve-out forbids leaking exception text or any field
    # beyond {name, ok, ms}.
    assert set(body["checks"][0].keys()) == {"name", "ok", "ms"}


def test_healthz_schema_locked(healthz) -> None:
    """ADR-0013 carve-out spec — bool-only, no DB rows, no secrets."""
    body = healthz()
    assert set(body.keys()) == {"ok", "checks"}
    for check in body["checks"]:
        assert set(check.keys()) == {"name", "ok", "ms"}
