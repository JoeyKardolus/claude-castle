"""FastAPI endpoint integration: Bearer + payload to commit call.

Wires the full request flow with the writer mocked. Verifies:
- Missing / wrong Authorization -> 401
- Valid Bearer + unparseable JSON -> 400
- Valid Bearer + known event type -> 200 + writer invoked once
- Valid Bearer + path outside the sync folder -> 200 + skip marker
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXTCLOUD_WEBHOOK_SECRET", "s3cret")
    monkeypatch.setenv("SYNC_GITHUB_PAT", "github_pat_test")
    monkeypatch.setenv("GITHUB_REPO", "alice/example-repo")
    monkeypatch.setenv("NC_DATA_ROOT", str(tmp_path))
    # Make sure the data volume path exists so the reader can be constructed
    # without complaining.
    (tmp_path / "alice" / "files" / "Sync").mkdir(parents=True, exist_ok=True)
    (tmp_path / "alice" / "files" / "Sync" / "scratch.md").write_text("hi", encoding="utf-8")

    from nextcloud_sync import app as app_module
    # Patch the writer so we don't talk to GitHub from a unit test.
    fake_writer = MagicMock(return_value="https://github.com/.../commit/fake")
    monkeypatch.setattr(app_module, "commit_event", fake_writer)
    return TestClient(app_module.app), fake_writer


WRITE_PAYLOAD = {
    "event": {
        "class": "OCP\\Files\\Events\\Node\\NodeWrittenEvent",
        "node": {"id": 1, "path": "/alice/files/Sync/scratch.md"},
    },
    "user": {"uid": "alice", "displayName": "Alice"},
    "time": 1717425671,
}


def test_healthz(client):
    c, _ = client
    r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_unauth_request_rejected(client):
    c, fake = client
    r = c.post("/nextcloud/file-event", json=WRITE_PAYLOAD)
    assert r.status_code == 401
    fake.assert_not_called()


def test_wrong_bearer_rejected(client):
    c, fake = client
    r = c.post(
        "/nextcloud/file-event",
        json=WRITE_PAYLOAD,
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401
    fake.assert_not_called()


def test_malformed_payload_400(client):
    c, fake = client
    r = c.post(
        "/nextcloud/file-event",
        json={"not": "an event"},
        headers={"Authorization": "Bearer s3cret"},
    )
    assert r.status_code == 400
    fake.assert_not_called()


def test_valid_event_invokes_writer_once(client):
    c, fake = client
    r = c.post(
        "/nextcloud/file-event",
        json=WRITE_PAYLOAD,
        headers={"Authorization": "Bearer s3cret"},
    )
    assert r.status_code == 200
    assert fake.call_count == 1


def test_path_outside_sync_folder_reports_skip(client):
    """Writer still gets called; it returns "" for outside-sync paths.
    That's the writer's responsibility, tested in
    test_writer_idempotent_commits.py.
    """
    c, fake = client
    payload = dict(WRITE_PAYLOAD)
    payload["event"] = dict(payload["event"])
    payload["event"]["node"] = {"id": 1, "path": "/alice/files/Personal/notes.md"}
    fake.return_value = ""  # simulate the writer returning the skip marker
    r = c.post(
        "/nextcloud/file-event",
        json=payload,
        headers={"Authorization": "Bearer s3cret"},
    )
    assert r.status_code == 200
    assert r.json()["skipped"] is True
