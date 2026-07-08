"""GitHub Contents API writer: per-event commit with idempotency + 409 retry.

The writer takes a parsed Nextcloud event + a disk reader (so tests can mock
filesystem reads), and issues PUT / DELETE calls against the Contents API.

Behaviours pinned:
- Create / update: PUT with the new content (existing-sha when present).
- Idempotent: existing content == new content -> no PUT, returns the file's URL.
- Delete: DELETE with the existing-sha; 404 (file already gone) is OK.
- Rename: DELETE old + PUT new in one logical operation.
- 409 (sha drifted between read and write): refetch + retry once; second
  409 logs an error and raises.
- Commit author derived from the Nextcloud actor user.
- Repo target comes from the GITHUB_REPO env var (owner/name).
"""
from __future__ import annotations

import base64
import logging
from unittest.mock import MagicMock

import pytest

from nextcloud_sync.events import (
    NodeDeletedEvent,
    NodeRenamedEvent,
    NodeWrittenEvent,
)
from nextcloud_sync.writer import (
    RepoNotConfigured,
    SyncConflictUnresolved,
    commit_event,
)


@pytest.fixture(autouse=True)
def _repo_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPO", "alice/example-repo")


def _read(content: bytes):
    def reader(_path: str) -> bytes:
        return content
    return reader


def _write_event(path="/alice/files/Sync/notes.md", uid="alice"):
    return NodeWrittenEvent.model_validate({
        "event": {
            "class": "OCP\\Files\\Events\\Node\\NodeWrittenEvent",
            "node": {"id": 1, "path": path},
        },
        "user": {"uid": uid, "displayName": uid.title()},
        "time": 1717425671,
    })


def _delete_event(path="/alice/files/Sync/drafts/old.md", uid="alice"):
    return NodeDeletedEvent.model_validate({
        "event": {
            "class": "OCP\\Files\\Events\\Node\\NodeDeletedEvent",
            "node": {"id": 2, "path": path},
        },
        "user": {"uid": uid, "displayName": uid.title()},
        "time": 1717425700,
    })


def _rename_event(src, dst, uid="alice"):
    return NodeRenamedEvent.model_validate({
        "event": {
            "class": "OCP\\Files\\Events\\Node\\NodeRenamedEvent",
            "source": {"id": 3, "path": src},
            "target": {"id": 3, "path": dst},
        },
        "user": {"uid": uid, "displayName": uid.title()},
        "time": 1717425800,
    })


def _session(*, get_status=404, get_payload=None, put_status=201, put_payload=None, delete_status=200):
    s = MagicMock()
    get_resp = MagicMock(); get_resp.status_code = get_status; get_resp.json.return_value = get_payload or {}
    s.get.return_value = get_resp
    put_resp = MagicMock(); put_resp.status_code = put_status
    put_resp.json.return_value = put_payload or {
        "commit": {"html_url": "https://github.com/alice/example-repo/commit/abc"},
        "content": {"sha": "newblob"},
    }
    put_resp.raise_for_status = MagicMock()
    s.put.return_value = put_resp
    del_resp = MagicMock(); del_resp.status_code = delete_status
    del_resp.json.return_value = {"commit": {"html_url": "https://github.com/alice/example-repo/commit/del"}}
    del_resp.raise_for_status = MagicMock()
    s.delete.return_value = del_resp
    return s


# -- Create (file absent on GitHub) ------------------------------------------

def test_create_puts_without_sha():
    s = _session(get_status=404)
    url = commit_event(_write_event(), _read(b"hi"), token="t", session=s)
    assert url.endswith("/commit/abc")
    s.put.assert_called_once()
    args, kw = s.put.call_args
    assert "sha" not in kw["json"]
    assert base64.b64decode(kw["json"]["content"]) == b"hi"
    assert kw["json"]["author"]["name"] == "Alice"
    assert "alice@nextcloud.invalid" in kw["json"]["author"]["email"]
    # Repo slug from GITHUB_REPO, path from the sync-folder mapping.
    assert "/repos/alice/example-repo/contents/cloud-sync/alice/notes.md" in args[0]


# -- Update (file present, content changed) ----------------------------------

def test_update_puts_with_sha():
    s = _session(
        get_status=200,
        get_payload={"sha": "old", "content": base64.b64encode(b"old").decode(), "encoding": "base64"},
    )
    commit_event(_write_event(), _read(b"new"), token="t", session=s)
    _, kw = s.put.call_args
    assert kw["json"]["sha"] == "old"


# -- Idempotency: content identical ------------------------------------------

def test_idempotent_skips_put_when_content_identical():
    body = b"unchanged"
    s = _session(
        get_status=200,
        get_payload={
            "sha": "blob",
            "content": base64.b64encode(body).decode(),
            "encoding": "base64",
            "html_url": "https://github.com/alice/example-repo/blob/main/cloud-sync/alice/notes.md",
        },
    )
    url = commit_event(_write_event(), _read(body), token="t", session=s)
    s.put.assert_not_called()
    assert "notes.md" in url


# -- Delete -------------------------------------------------------------------

def test_delete_passes_existing_sha():
    s = _session(
        get_status=200,
        get_payload={"sha": "blob", "content": "", "encoding": "base64"},
    )
    url = commit_event(_delete_event(), _read(b""), token="t", session=s)
    s.delete.assert_called_once()
    _, kw = s.delete.call_args
    assert kw["json"]["sha"] == "blob"
    assert "del" in url


def test_delete_404_is_noop():
    # File already gone on GitHub: no error, return the api url as result.
    s = _session(get_status=404)
    url = commit_event(_delete_event(), _read(b""), token="t", session=s)
    s.delete.assert_not_called()
    assert url  # non-empty


# -- Rename -------------------------------------------------------------------

def test_rename_creates_target_then_deletes_source():
    """First GET is for target (absent, 404 -> create), second GET is for
    source (present, 200 -> its sha goes into the DELETE call).
    """
    body = b"renamed content"
    s = MagicMock()
    target_absent = MagicMock(); target_absent.status_code = 404; target_absent.json.return_value = {}
    source_present = MagicMock(); source_present.status_code = 200
    source_present.json.return_value = {"sha": "srcblob", "content": base64.b64encode(body).decode(), "encoding": "base64"}
    s.get.side_effect = [target_absent, source_present]
    put_resp = MagicMock(); put_resp.status_code = 201
    put_resp.json.return_value = {"commit": {"html_url": "https://github.com/.../commit/put"}}
    put_resp.raise_for_status = MagicMock()
    s.put.return_value = put_resp
    del_resp = MagicMock(); del_resp.status_code = 200
    del_resp.json.return_value = {"commit": {"html_url": "https://github.com/.../commit/del"}}
    del_resp.raise_for_status = MagicMock()
    s.delete.return_value = del_resp

    commit_event(
        _rename_event(
            "/alice/files/Sync/drafts/draft.md",
            "/alice/files/Sync/final/draft.md",
        ),
        _read(body),
        token="t", session=s,
    )
    s.put.assert_called_once()
    s.delete.assert_called_once()
    _, del_kw = s.delete.call_args
    assert del_kw["json"]["sha"] == "srcblob"


# -- 409 conflict retry --------------------------------------------------------

def test_409_retries_once_then_succeeds():
    s = _session(get_status=404)
    conflict = MagicMock(); conflict.status_code = 409
    conflict.json.return_value = {"message": "sha mismatch"}
    conflict.raise_for_status = MagicMock()
    ok = MagicMock(); ok.status_code = 201
    ok.json.return_value = {"commit": {"html_url": "https://github.com/.../commit/retry-ok"}, "content": {"sha": "x"}}
    ok.raise_for_status = MagicMock()
    s.put.side_effect = [conflict, ok]
    url = commit_event(_write_event(), _read(b"body"), token="t", session=s)
    assert "retry-ok" in url
    assert s.put.call_count == 2


def test_409_twice_raises_and_logs_error(caplog):
    s = _session(get_status=404)
    conflict = MagicMock(); conflict.status_code = 409; conflict.json.return_value = {"message": "sha mismatch"}
    conflict.raise_for_status = MagicMock()
    s.put.side_effect = [conflict, conflict]
    with caplog.at_level(logging.ERROR, logger="nextcloud_sync.writer"):
        with pytest.raises(SyncConflictUnresolved):
            commit_event(_write_event(), _read(b"body"), token="t", session=s)
    assert any("conflict" in rec.message.lower() for rec in caplog.records)
    assert any("alice" in rec.getMessage().lower() for rec in caplog.records)


# -- Author derivation ---------------------------------------------------------

def test_author_email_uses_nextcloud_uid_when_no_email_known():
    s = _session(get_status=404)
    commit_event(_write_event(uid="test.user"), _read(b"x"), token="t", session=s)
    _, kw = s.put.call_args
    # Fallback domain when we don't have a real email map.
    assert kw["json"]["author"]["email"] == "test.user@nextcloud.invalid"
    assert kw["json"]["author"]["name"] == "Test.User"


# -- Path outside the sync folder is skipped -----------------------------------

def test_path_outside_sync_folder_returns_skip_marker():
    s = _session(get_status=404)
    bad_event = _write_event(path="/alice/files/Personal/notes.md")
    url = commit_event(bad_event, _read(b"x"), token="t", session=s)
    s.put.assert_not_called()
    s.delete.assert_not_called()
    assert url == ""  # sentinel: nothing happened


# -- Misconfiguration fails loud ------------------------------------------------

def test_missing_github_repo_raises(monkeypatch):
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    s = _session(get_status=404)
    with pytest.raises(RepoNotConfigured):
        commit_event(_write_event(), _read(b"x"), token="t", session=s)
